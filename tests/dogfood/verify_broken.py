#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Deliberately broken implementation — no timestamp grammar gate. It canonicalizes and
hashes whatever it receives verbatim, including a JSON-integer timestamp. That reproduces
the exact forbidden hash for the epoch-integer negative vector (neg-b01), which a
conformant verifier must reject instead of hashing. Used to prove this Action's
verify-impl mode actually catches a conformance bug (FAIL) instead of giving a false
green."""
import sys, json, hashlib

preimage = json.load(sys.stdin)
canonical = json.dumps(preimage, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
print(hashlib.sha256(canonical.encode()).hexdigest())
