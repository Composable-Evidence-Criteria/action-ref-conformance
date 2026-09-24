# manifest-v2/ — portable action-ref-v2 (domain-separated) conformance set

A language-neutral packaging of the `action-ref-v2-domain-separated` conformance vectors, in
the same shape as [`../manifest/`](../manifest/) (the v1 portable set) and
[jsuich/x402-action-receipt](https://github.com/jsuich/x402-action-receipt)'s
`vectors/MANIFEST.json` + `vectors/*.json`: one file per vector, a manifest declaring the
expected verdict and reject reason for each, and a reference verifier that fails the run
unless it observes both verdicts and exercises every declared reason code.

**v2 is additive, not a replacement.** The four-field preimage (`action_type`, `agent_id`,
`scope`, `timestamp`) and JCS canonicalization are unchanged from v1 — the only difference is
a fixed domain tag, `mycelium.action-ref:v2:`, prepended to the canonical JSON bytes before
hashing, with the resulting hex digest prefixed `v2:`. v1 hashes remain permanently valid and
are never retroactively invalidated; see
[`docs/spec/action-ref.md#version-negotiation`](https://github.com/giskard09/argentum-core/blob/main/docs/spec/action-ref.md)
and [RFC 002](https://github.com/giskard09/argentum-core/blob/main/docs/rfcs/002-action-ref-v2-domain-separation.md)
for the full design rationale and per-adopter impact.

## Why domain separation, concretely

`action_ref = SHA-256(JCS(preimage))` is a pure function of four field values. Any other
protocol that independently arrives at the same four-field JCS shape produces byte-identical
output for the same underlying real-world event, with nothing in the hash itself to say which
spec's rules were applied. This is not hypothetical: a public mapping of the evidence-record
landscape circulating in the x402 Foundation TSC's Identity working group flagged that
multiple `action_ref`-shaped variants already circulate under related names. A domain tag
closes that ambiguity by scoping the hash to a specific spec, not just a version number — see
`neg_neg-v2b-wrong-domain-tag.json` below for why the tag has to name the spec, not just say
"v2".

## Layout

```
manifest-v2/
  MANIFEST.json    profile + reject_reasons taxonomy + per-vector expect/reason
  vectors/
    pos_*.json      preimage + expected action_ref_v1 + action_ref_v2 (3)
    neg_*.json      preimage + claimed (forbidden) action_ref_v2 + failure_mode (3)
  verify.py         reference verifier, Python stdlib only, zero deps
```

## Running it

```
python3 manifest-v2/verify.py
```

Exits 0 only if every vector's verdict matches `MANIFEST.json`, both PASS and REJECT were
observed at least once, and every reason code in `reject_reasons` was exercised by at least
one negative vector. Exit 2 means the *suite itself* is broken; exit 1 means a real
conformance failure.

## The four rules a verifier in any language implements

1. **Positive** — recompute `action_ref_v1 = SHA-256(JCS(preimage))` (unchanged v1 rule) and
   `action_ref_v2 = "v2:" + SHA-256("mycelium.action-ref:v2:" + JCS(preimage))`. Both MUST
   equal the vector's stored values, byte-identical, and MUST NOT collide with each other.
2. **Negative, `cross_protocol_collision_risk`** — a bare, untagged 64-hex digest (the exact
   shape a domain-less implementation, ours or anyone else's, would produce for the same four
   field values) is presented as if it satisfied the v2 profile. MUST reject: the real v2
   value is never a bare 64-hex string, it is always `"v2:"` + 64 hex chars derived from the
   tagged preimage.
3. **Negative, `wrong_domain_tag`** — the claimed value was computed under a domain tag other
   than `mycelium.action-ref:v2:` (e.g. the generic, spec-unnamed `"action-ref:v2:"` prefix
   RFC 002 explicitly considered and rejected). MUST recompute independently with the correct
   tag and reject on mismatch — a version-only tag does not close cross-protocol collision, it
   just moves the collision surface into the tag namespace itself.
4. **Negative, `tag_applied_post_hash`** — the claimed value hashes the domain tag together
   with an already-computed v1 digest's hex string, instead of prepending the tag to the raw
   preimage bytes before hashing once. MUST reject: this bug leaves a bare, undomain-separated
   hash one layer underneath, silently defeating the entire point of domain separation while
   still producing a value that superficially looks like a valid v2 output.

Full spec: [`docs/spec/action-ref.md`](https://github.com/giskard09/argentum-core/blob/main/docs/spec/action-ref.md).
Full RFC: [`docs/rfcs/002-action-ref-v2-domain-separation.md`](https://github.com/giskard09/argentum-core/blob/main/docs/rfcs/002-action-ref-v2-domain-separation.md).

## Provenance

The three positive vectors are copied verbatim (same `preimage`, `action_ref_v1`,
`action_ref_v2` values) from
[`argentum-core/examples/conformance/action-ref-v2/action-ref-v2.fixture.json`](https://github.com/giskard09/argentum-core/blob/main/examples/conformance/action-ref-v2/action-ref-v2.fixture.json) —
nothing here is regenerated or reinterpreted, `verify.py` just reshapes them one-vector-per-file
and adds the three negative collision-class vectors that argentum-core's internal fixture does
not yet carry.

## License

Apache-2.0 (same as the rest of this repo).
