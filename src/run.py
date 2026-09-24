#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""action-ref-conformance runner. Python stdlib only, zero deps."""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VECTORS = os.path.join(os.path.dirname(HERE), "vectors", "action-ref-v1-jcs-sha256.json")


def run_command(command, preimage):
    """Feed preimage JSON via stdin, capture stdout. Returns (exit_code, stdout_stripped)."""
    try:
        proc = subprocess.run(
            command,
            shell=True,
            input=json.dumps(preimage, separators=(",", ":"), ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return 124, ""
    return proc.returncode, proc.stdout.strip()


def verify_impl(command, vectors):
    results = []
    for v in vectors["positives"]:
        code, got = run_command(command, v["preimage"])
        expected = v["action_ref"]
        passed = (code == 0) and (got.lower() == expected.lower())
        results.append({
            "id": v["id"],
            "kind": "positive",
            "expected": expected,
            "got": got,
            "exit_code": code,
            "passed": passed,
        })
    for v in vectors["negatives"]:
        code, got = run_command(command, v["invocation_payload"])
        forbidden = v["claimed_action_ref"]
        # Acceptable: command rejects (non-zero exit / empty output), or its output diverges
        # from the forbidden/claimed hash (the digest a forgeable verifier would reproduce by
        # normalizing or reordering the drifted form). Forbidden: silently matching that hash.
        if code != 0 or not got:
            passed = True
        else:
            passed = got.lower() != forbidden.lower()
        results.append({
            "id": v["id"],
            "kind": "negative",
            "failure_mode": v["failure_mode"],
            "forbidden_action_ref": forbidden,
            "got": got,
            "exit_code": code,
            "passed": passed,
        })
    return results


def verify_vendored(fixtures_path, vectors):
    canonical = {v["id"]: v["action_ref"] for v in vectors["positives"]}

    def load_json_files(path):
        if os.path.isdir(path):
            for name in sorted(os.listdir(path)):
                if name.endswith(".json"):
                    yield os.path.join(path, name)
        else:
            yield path

    vendored = {}
    for fp in load_json_files(fixtures_path):
        with open(fp) as f:
            data = json.load(f)
        candidates = data.get("vectors", data.get("positives", [data]))
        for item in candidates:
            if isinstance(item, dict) and "id" in item and "action_ref" in item:
                vendored[item["id"]] = item["action_ref"]

    results = []
    for vid, expected in canonical.items():
        got = vendored.get(vid)
        if got is None:
            results.append({"id": vid, "kind": "vendored", "expected": expected, "got": None,
                             "passed": False, "reason": "missing from vendored fixtures"})
        else:
            results.append({"id": vid, "kind": "vendored", "expected": expected, "got": got,
                             "passed": got.lower() == expected.lower()})
    return results


def write_step_summary(results, profile):
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    lines = [f"## action-ref-conformance — `{profile}`", "", "| Vector | Kind | Result |", "|---|---|---|"]
    for r in results:
        mark = "PASS" if r["passed"] else "FAIL"
        lines.append(f"| `{r['id']}` | {r['kind']} | {mark} |")
    passed = sum(1 for r in results if r["passed"])
    lines.append("")
    lines.append(f"**{passed}/{len(results)} vectors passed.**")
    text = "\n".join(lines) + "\n"
    print(text)
    if summary_path:
        with open(summary_path, "a") as f:
            f.write(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["verify-impl", "verify-vendored"], required=True)
    ap.add_argument("--command", default=None)
    ap.add_argument("--fixtures-path", default=None)
    ap.add_argument("--vectors", default=DEFAULT_VECTORS)
    ap.add_argument("--report", default="action-ref-conformance-report.json")
    args = ap.parse_args()

    with open(args.vectors) as f:
        vectors = json.load(f)

    if args.mode == "verify-impl":
        if not args.command:
            print("::error::--command is required for verify-impl mode", file=sys.stderr)
            sys.exit(2)
        results = verify_impl(args.command, vectors)
    else:
        if not args.fixtures_path:
            print("::error::--fixtures-path is required for verify-vendored mode", file=sys.stderr)
            sys.exit(2)
        results = verify_vendored(args.fixtures_path, vectors)

    write_step_summary(results, vectors["profile"])

    report = {
        "profile": vectors["profile"],
        "profile_version": vectors["profile_version"],
        "mode": args.mode,
        "results": results,
        "passed": all(r["passed"] for r in results),
    }
    with open(args.report, "w") as f:
        json.dump(report, f, indent=2)

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"report={args.report}\n")
            f.write(f"passed={'true' if report['passed'] else 'false'}\n")

    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
