#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reference verifier + coverage check for the action-ref-v2-domain-separated portable
conformance manifest. Python stdlib only, zero deps, no network.

    python3 verify.py

v2 is ADDITIVE to v1 (see ../manifest/) -- same four-field preimage and JCS
canonicalization, only a fixed domain tag ('mycelium.action-ref:v2:') is prepended to the
canonical JSON bytes before hashing, with the resulting hex digest prefixed 'v2:'. A
conformant verifier in ANY language implements:

  1. positive vector -> recompute action_ref_v1 = SHA-256(JCS(preimage)) (unchanged) AND
     action_ref_v2 = 'v2:' + SHA-256(domain_tag + JCS(preimage)), MUST equal both stored
     values, and the two MUST NOT collide.
  2. negative, cross_protocol_collision_risk -> a bare (untagged, no 'v2:' marker) 64-hex
     digest is claimed to satisfy the v2 profile. MUST reject: recomputing the real v2
     value from the same preimage never produces a bare digest.
  3. negative, wrong_domain_tag -> the claimed v2 value was computed with a domain tag
     other than 'mycelium.action-ref:v2:'. MUST recompute independently with the correct
     tag and reject on mismatch.
  4. negative, tag_applied_post_hash -> the claimed v2 value hashes the domain tag together
     with an already-computed v1 digest instead of the raw preimage bytes. MUST recompute
     the correct derivation and reject on mismatch.

The run is only valid if it observes both verdicts (PASS and REJECT) and exercises every
reason code declared in MANIFEST.json["reject_reasons"] -- same meta-assertion as
../manifest/verify.py.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PASS, REJECT = "PASS", "REJECT"
DOMAIN_TAG = "mycelium.action-ref:v2:"


def jcs_encode(d: dict) -> bytes:
    return json.dumps(dict(sorted(d.items())), separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_v1(preimage: dict) -> str:
    return hashlib.sha256(jcs_encode(preimage)).hexdigest()


def compute_v2(preimage: dict, tag: str = DOMAIN_TAG) -> str:
    return "v2:" + hashlib.sha256(tag.encode("utf-8") + jcs_encode(preimage)).hexdigest()


def verify_positive(v: dict) -> tuple[str, str | None]:
    got_v1 = compute_v1(v["preimage"])
    got_v2 = compute_v2(v["preimage"])
    if got_v1 != v["action_ref_v1"]:
        return REJECT, "v1_digest_mismatch"
    if got_v2 != v["action_ref_v2"]:
        return REJECT, "v2_digest_mismatch"
    if got_v1 == got_v2:
        return REJECT, "v1_v2_collision"
    return PASS, None


def verify_negative(entry: dict, v: dict) -> tuple[str, str | None]:
    reason = entry["reason"]
    correct_v2 = compute_v2(v["preimage"])

    if reason == "cross_protocol_collision_risk":
        claimed = v["claimed_action_ref_v2"]
        if claimed == correct_v2:
            return PASS, None  # conformance bug: bare hash accepted as v2
        return REJECT, "cross_protocol_collision_risk"

    if reason == "wrong_domain_tag":
        claimed = v["claimed_action_ref_v2"]
        if claimed == correct_v2:
            return PASS, None  # conformance bug: wrong-tag hash accepted as canonical v2
        return REJECT, "wrong_domain_tag"

    if reason == "tag_applied_post_hash":
        claimed = v["claimed_action_ref_v2"]
        if claimed == correct_v2:
            return PASS, None  # conformance bug: post-hash-tagged value accepted as canonical v2
        return REJECT, "tag_applied_post_hash"

    return REJECT, "unknown_reason"


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

        if entry["expect"] == PASS:
            got_verdict, got_reason = verify_positive(vector)
        else:
            got_verdict, got_reason = verify_negative(entry, vector)

        observed_verdicts.add(got_verdict)
        if got_verdict == REJECT and got_reason in declared_reasons:
            covered_reasons.add(got_reason)

        expect_reason = entry["reason"]
        ok = got_verdict == entry["expect"] and (entry["expect"] == PASS or got_reason == expect_reason)
        failures += not ok
        print(f"[{' ok ' if ok else 'FAIL'}] {entry['file']:52s} want {entry['expect']:7s}/{str(expect_reason):28s} "
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
