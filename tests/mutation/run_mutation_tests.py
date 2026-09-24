#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Mutation testing for src/run.py — the shared grading logic every downstream CI
(ours and third parties') trusts to tell conformant from non-conformant.

Not line coverage. Each mutant flips one real domain failure the spec affirms
(case-sensitivity of hex digests, positive vs negative vector logic, exit-code
handling) into the grader itself, then runs the exact suite tests.yml runs — all
7 jobs (own/agentoracle/uppercase-hex implementations, broken-implementation and
crash-after-print must-fail, vendored-fixtures good and drifted-must-fail).

KILLED  = some job in the suite now fails/behaves differently -> mutant caught.
SURVIVED = suite stays green -> the suite has a blind spot at that line.

Curated first set — no blind sweep, no arbitrary text swaps. Each mutant is a
plausible off-by-one an implementer of this checker could actually make.
"""
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(REPO, "src", "run.py")
VECTORS = os.path.join(REPO, "vectors", "action-ref-v1-jcs-sha256.json")
DOGFOOD = os.path.join(REPO, "tests", "dogfood")

MUTANTS = [
    {
        "id": "M1-drop-lowercase-positive",
        "desc": "positive-vector compare stops lowercasing before ==, so a conformant "
                "impl that emits uppercase hex (spec doesn't forbid it) would wrongly FAIL.",
        "find": 'got.lower() == expected.lower()',
        "replace": 'got == expected',
    },
    {
        "id": "M2-invert-positive-passed",
        "desc": "positive-vector pass condition inverted (== -> !=): a correct impl "
                "would be graded non-conformant and a wrong one conformant.",
        "find": 'passed = (code == 0) and (got.lower() == expected.lower())',
        "replace": 'passed = (code == 0) and (got.lower() != expected.lower())',
    },
    {
        "id": "M3-drop-exitcode-check-positive",
        "desc": "positive-vector pass condition drops the exit-code gate: an impl that "
                "crashes but happens to print the right digest to stdout before crashing "
                "would still be graded conformant.",
        "find": 'passed = (code == 0) and (got.lower() == expected.lower())',
        "replace": 'passed = (got.lower() == expected.lower())',
    },
    {
        "id": "M4-invert-negative-reject-gate",
        "desc": "negative-vector auto-pass-on-reject condition inverted: an impl that "
                "correctly rejects a malformed/forgeable input (non-zero exit) is now "
                "graded as failing that vector.",
        "find": 'if code != 0 or not got:',
        "replace": 'if code == 0 or not got:',
    },
    {
        "id": "M5-invert-negative-forbidden-check",
        "desc": "negative-vector forbidden-hash comparison inverted (!= -> ==): an impl "
                "that silently reproduces the forbidden/forgeable hash (the exact bug "
                "this vector exists to catch) would be graded conformant.",
        "find": 'passed = got.lower() != forbidden.lower()',
        "replace": 'passed = got.lower() == forbidden.lower()',
    },
    {
        "id": "M6-drop-lowercase-vendored",
        "desc": "verify-vendored compare stops lowercasing before ==, same class as M1 "
                "but on the vendored-fixture path (not exercised by tests.yml at all).",
        "find": '"passed": got.lower() == expected.lower()}',
        "replace": '"passed": got == expected}',
    },
]


def apply_mutant(mutant, dest_path):
    with open(SRC) as f:
        src = f.read()
    if mutant["find"] not in src:
        return False, f"anchor text not found in src/run.py: {mutant['find']!r}"
    mutated = src.replace(mutant["find"], mutant["replace"], 1)
    with open(dest_path, "w") as f:
        f.write(mutated)
    return True, None


VACUOUS_PARSE = "VACUOUS-parse"
VACUOUS_COLLECT = "VACUOUS-collect"


def mutant_is_vacuous_parse(dest_path):
    """Phase 1: does the mutated file even parse/compile?

    A mutant that fails here (SyntaxError from a careless find/replace,
    e.g. one that injects an unescaped control char into a string
    literal) never reaches the property it was supposed to violate.
    Every downstream subprocess call would then die with a
    SyntaxError/IndentationError traceback and a non-zero exit code
    indistinguishable, at the outcome-dict level, from a real reject —
    counting it as KILLED would credit the mutant for exercising a
    property it never touched. Returns (vacuous: bool, reason: str|None).
    """
    try:
        py_compile.compile(dest_path, doraise=True, quiet=2)
    except py_compile.PyCompileError as e:
        return True, str(e.exc_value)
    return False, None


def _run_report(run_py, mode_args, report):
    """Runs run_py, returns (returncode, crashed). crashed=True means the process died with an
    unhandled traceback before ever writing a well-formed report — the run.py equivalent of a
    pytest collection/setup error, not a controlled reject via sys.exit().

    Distinguishing crash from controlled reject matters because a mutant that raises early (e.g.
    a NameError from a careless find/replace landing on the wrong reference) makes every job fail
    identically for a reason that has nothing to do with the property the mutant targets. Scoring
    that as KILLED would credit it for exercising a check it never reached — same shape of bug as
    the py_compile-only gap, one runtime layer later.
    """
    proc = subprocess.run(
        [sys.executable, run_py] + mode_args + ["--report", report],
        capture_output=True, text=True,
    )
    if "Traceback (most recent call last)" in proc.stderr:
        return proc.returncode, True
    if not os.path.exists(report):
        return proc.returncode, True
    try:
        with open(report) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return proc.returncode, True
    if "passed" not in data:
        return proc.returncode, True
    return proc.returncode, False


def run_dogfood_job(run_py, command):
    """Mirrors one own-implementation / agentoracle-v1-implementation job in tests.yml."""
    with tempfile.TemporaryDirectory() as td:
        report = os.path.join(td, "report.json")
        return _run_report(
            run_py,
            ["--mode", "verify-impl", "--command", command, "--vectors", VECTORS],
            report,
        )


def run_broken_job(run_py):
    """Mirrors broken-implementation-must-fail: asserts the Action step FAILS."""
    code, crashed = run_dogfood_job(run_py, f"python3 {os.path.join(DOGFOOD, 'verify_broken.py')}")
    return (code != 0), crashed  # True = job assertion holds (broken correctly caught)


def run_vendored_job(run_py, fixtures_dir, expect_pass):
    """Mirrors vendored-fixtures / vendored-fixtures-broken-must-fail in tests.yml."""
    with tempfile.TemporaryDirectory() as td:
        report = os.path.join(td, "report.json")
        code, crashed = _run_report(
            run_py,
            ["--mode", "verify-vendored", "--fixtures-path", fixtures_dir, "--vectors", VECTORS],
            report,
        )
        ok = (code == 0) if expect_pass else (code != 0)
        return ok, crashed


def suite_result(run_py):
    own_code, own_crash = run_dogfood_job(run_py, f"python3 {os.path.join(DOGFOOD, 'verify_own.py')}")
    oracle_code, oracle_crash = run_dogfood_job(run_py, f"python3 {os.path.join(DOGFOOD, 'verify_agentoracle.py')}")
    uppercase_code, uppercase_crash = run_dogfood_job(run_py, f"python3 {os.path.join(DOGFOOD, 'verify_uppercase.py')}")
    broken_ok, broken_crash = run_broken_job(run_py)
    crash_code, crash_after_print_crash = run_dogfood_job(run_py, f"python3 {os.path.join(DOGFOOD, 'verify_crash_after_print.py')}")
    vendored_good_ok, vendored_good_crash = run_vendored_job(
        run_py, os.path.join(DOGFOOD, "vendored-fixtures-good"), expect_pass=True)
    vendored_broken_ok, vendored_broken_crash = run_vendored_job(
        run_py, os.path.join(DOGFOOD, "vendored-fixtures-broken"), expect_pass=False)
    crashed = any([own_crash, oracle_crash, uppercase_crash, broken_crash,
                   crash_after_print_crash, vendored_good_crash, vendored_broken_crash])
    outcome = {
        "own_conformant": own_code == 0,
        "agentoracle_conformant": oracle_code == 0,
        "uppercase_conformant": uppercase_code == 0,
        "broken_correctly_rejected": broken_ok,
        "crash_after_print_correctly_rejected": crash_code != 0,
        "vendored_good_passes": vendored_good_ok,
        "vendored_broken_correctly_rejected": vendored_broken_ok,
    }
    return outcome, crashed


def main():
    baseline, baseline_crashed = suite_result(SRC)
    print("Baseline (unmutated src/run.py):")
    print(json.dumps(baseline, indent=2))
    if baseline_crashed or not all(baseline.values()):
        print("::error::baseline suite is not green on unmutated code — fix before mutation testing")
        sys.exit(2)

    results = []
    with tempfile.TemporaryDirectory() as td:
        for m in MUTANTS:
            dest = os.path.join(td, f"{m['id']}.py")
            ok, err = apply_mutant(m, dest)
            if not ok:
                results.append({**m, "status": "NOT_APPLIED", "reason": err})
                continue
            vacuous, reason = mutant_is_vacuous_parse(dest)
            if vacuous:
                results.append({**m, "status": VACUOUS_PARSE, "reason": reason})
                continue
            mutated, crashed = suite_result(dest)
            if crashed:
                results.append({
                    **m, "status": VACUOUS_COLLECT,
                    "reason": "mutated run.py died with an unhandled traceback before "
                              "producing a well-formed report in at least one job — never "
                              "reached the property under test in a controlled way",
                    "outcome": mutated,
                })
                continue
            killed = mutated != baseline
            results.append({**m, "status": "KILLED" if killed else "SURVIVED", "outcome": mutated})

    print("\n=== Mutation results ===")
    for r in results:
        print(f"{r['status']:15s} {r['id']:35s} {r['desc'][:70]}")

    killed = sum(1 for r in results if r["status"] == "KILLED")
    survived = [r for r in results if r["status"] == "SURVIVED"]
    vacuous = [r for r in results if r["status"] in (VACUOUS_PARSE, VACUOUS_COLLECT)]
    not_applied = [r for r in results if r["status"] == "NOT_APPLIED"]
    total = sum(1 for r in results if r["status"] in ("KILLED", "SURVIVED"))
    print(f"\n{killed}/{total} mutants killed by the current CI suite (tests.yml).")
    if vacuous:
        print(f"{len(vacuous)} VACUOUS — never reached the property, excluded from the ratio:")
        for r in vacuous:
            print(f"  - {r['id']} [{r['status']}]: {r['reason']}")
    if not_applied:
        print(f"{len(not_applied)} NOT_APPLIED — anchor text missing, excluded from the ratio:")
        for r in not_applied:
            print(f"  - {r['id']}: {r['reason']}")
    if survived:
        print(f"{len(survived)} SURVIVED — real blind spot(s):")
        for r in survived:
            print(f"  - {r['id']}: {r['desc']}")

    report_path = os.path.join(HERE, "mutation-report.json")
    with open(report_path, "w") as f:
        json.dump({"baseline": baseline, "mutants": results}, f, indent=2)
    print(f"\nFull report: {report_path}")


if __name__ == "__main__":
    main()
