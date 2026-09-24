#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reference implementation of action_ref — used to dogfood this Action against itself.

Validates the timestamp grammar (RFC 3339 UTC, exactly three fractional digits, Z suffix)
before hashing. A non-conformant timestamp is rejected (non-zero exit), never coerced.
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
