#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Deliberately broken implementation: prints the CORRECT action_ref digest to stdout,
then exits non-zero (simulating a crash after the write — e.g. a process that segfaults
in cleanup, or is OOM-killed right after flushing stdout).

Exists to prove the grader's positive-vector check actually requires exit code 0, not
just a matching digest on stdout (mutation M3-drop-exitcode-check-positive in
tests/mutation/run_mutation_tests.py found this was previously unexercised — no dogfood
implementation crashed with correct stdout, so a grader that dropped the exit-code gate
would still pass every job here).
"""
import sys, json, re, hashlib

TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def main() -> int:
    preimage = json.load(sys.stdin)
    ts = preimage.get("timestamp")
    if not isinstance(ts, str) or not TIMESTAMP_RE.match(ts):
        print(f"reject: timestamp is not RFC3339 UTC with 3 fractional digits: {ts!r}", file=sys.stderr)
        return 1
    canonical = json.dumps(preimage, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    print(hashlib.sha256(canonical.encode()).hexdigest())
    return 1  # correct digest already flushed to stdout; simulated crash right after


if __name__ == "__main__":
    sys.exit(main())
