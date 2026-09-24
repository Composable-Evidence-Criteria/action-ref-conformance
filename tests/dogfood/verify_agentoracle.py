#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Second dogfood implementation — vendored from AgentOracle's independent
action-ref-v1 verifier (argentum-core/examples/conformance/agentoracle-v1/verify.py),
adapted to the stdin-preimage / stdout-digest contract this Action expects.

Kept intentionally as a second, independently-written canonicalizer (not a call
into the reference implementation in verify_own.py) so the dogfood run in
tests.yml proves the Action validates a real third-party-style implementation,
not just its own reference.
"""
import hashlib
import json
import re
import sys

TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
PREIMAGE_KEYS = ("action_type", "agent_id", "scope", "timestamp")


def jcs_string(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def jcs_canonicalize_flat_strings(obj: dict) -> str:
    for k, v in obj.items():
        if not isinstance(v, str):
            raise TypeError(f"preimage value for {k!r} must be a string, got {type(v).__name__}")
    keys = sorted(obj.keys())
    pairs = [f"{jcs_string(k)}:{jcs_string(obj[k])}" for k in keys]
    return "{" + ",".join(pairs) + "}"


def compute_action_ref_v1(preimage: dict) -> str:
    ts = preimage["timestamp"]
    if not TIMESTAMP_RE.match(ts):
        raise ValueError(f"non-canonical timestamp grammar: {ts!r}")
    canonical = jcs_canonicalize_flat_strings(preimage)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def main() -> int:
    raw = json.load(sys.stdin)
    preimage = {k: raw[k] for k in PREIMAGE_KEYS}
    print(compute_action_ref_v1(preimage))
    return 0


if __name__ == "__main__":
    sys.exit(main())
