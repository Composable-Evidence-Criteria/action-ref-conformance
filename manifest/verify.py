#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reference verifier + coverage check for the action-ref-v1-jcs-sha256 portable
conformance manifest. Python stdlib only, zero deps, no network.

    python3 verify.py                 # verify committed vectors against MANIFEST.json

A conformant verifier in ANY language can implement the same three rules and
reproduce this table:

  1. positive vector -> recompute SHA-256(JCS(preimage)), MUST equal action_ref.
  2. negative vector whose invocation_payload.timestamp is not a string ->
     MUST reject before hashing (reason=grammar_reject).
  3. negative vector otherwise -> recompute SHA-256(JCS(invocation_payload)),
     MUST NOT equal claimed_action_ref (reason=recompute_mismatch).

The run is only valid if it observes both verdicts (PASS and REJECT) and
exercises every reason code declared in MANIFEST.json["reject_reasons"] --
this is the same meta-assertion jsuich/x402-action-receipt uses.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PASS, REJECT = "PASS", "REJECT"


def jcs_encode(d: dict) -> bytes:
    return json.dumps(dict(sorted(d.items())), separators=(",", ":"), ensure_ascii=False).encode("utf-8")


import hashlib


def compute_action_ref(preimage: dict) -> str:
    return hashlib.sha256(jcs_encode(preimage)).hexdigest()


def verify_vector(v: dict) -> tuple[str, str | None]:
    """Returns (verdict, reason). Never raises on hostile input."""
    if v["expect"] == PASS:
        try:
            got = compute_action_ref(v["preimage"])
        except Exception:
            return REJECT, "malformed_vector"
        return (PASS, None) if got == v["action_ref"] else (REJECT, "unexpected_mismatch")

    payload = v["invocation_payload"]
    ts = payload.get("timestamp")
    if not isinstance(ts, str):
        return REJECT, "grammar_reject"
    got = compute_action_ref(payload)
    if got == v["claimed_action_ref"]:
        return PASS, None  # conformance bug: verifier matched a forbidden drifted digest
    return REJECT, "recompute_mismatch"


def main() -> int:
    manifest = json.loads((HERE / "MANIFEST.json").read_text())
    declared_reasons = set(manifest["reject_reasons"].keys())

    print(f"profile={manifest['profile']}  spec={manifest['spec']}")
    print("-" * 88)

    failures = 0
    observed_verdicts = set()
    covered_reasons = set()

    for entry in manifest["vectors"]:
        vpath = HERE / "vectors" / entry["file"]
        vector = json.loads(vpath.read_text())
        got_verdict, got_reason = verify_vector({**entry, **vector})
        observed_verdicts.add(got_verdict)
        if got_verdict == REJECT and got_reason in declared_reasons:
            covered_reasons.add(got_reason)

        expect_reason = entry["reason"]
        ok = got_verdict == entry["expect"] and (entry["expect"] == PASS or got_reason == expect_reason)
        failures += not ok
        print(f"[{' ok ' if ok else 'FAIL'}] {entry['file']:40s} want {entry['expect']:7s}/{str(expect_reason):20s} "
              f"got {got_verdict:7s}/{got_reason}")

    print("-" * 88)

    if observed_verdicts != {PASS, REJECT}:
        print(f"SUITE INVALID: verifier never produced both verdicts (saw {observed_verdicts})")
        return 2

    missing = declared_reasons - covered_reasons
    if missing:
        print(f"SUITE INVALID: reject reason codes never exercised: {sorted(missing)}")
        return 2

    if failures:
        print(f"{failures} conformance failure(s)")
        return 1

    n_neg = sum(1 for e in manifest["vectors"] if e["expect"] == REJECT)
    print(f"all {len(manifest['vectors'])} vectors pass; both verdicts observed; "
          f"every one of {len(declared_reasons)} reject reason codes exercised "
          f"(across {n_neg} negative vectors)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
