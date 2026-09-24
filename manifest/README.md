# manifest/ — portable action-ref-v1 conformance set

A language-neutral packaging of the `action-ref-v1-jcs-sha256` conformance vectors, in the
same shape as [jsuich/x402-action-receipt](https://github.com/jsuich/x402-action-receipt)'s
`vectors/MANIFEST.json` + `vectors/*.json`: one file per vector, a manifest that declares the
expected verdict and reject reason for each, and a reference verifier that fails the run unless
it observes both verdicts and exercises every declared reason code.

This is a reciprocal package, not a new profile — the vectors themselves are the same frozen
fixtures already used by the [`action-ref-conformance` GitHub Action](../README.md)
(`vectors/action-ref-v1-jcs-sha256.json`, 4 positives) plus the full 9-vector negative set from
[`argentum-core/examples/conformance/recompute-drift-v1`](https://github.com/giskard09/argentum-core/blob/main/examples/conformance/recompute-drift-v1)
(the Action's own vector file only curates a subset). Nothing here is regenerated or
reinterpreted — every `preimage` / `invocation_payload` / `action_ref` / `claimed_action_ref`
byte is copied verbatim from those sources; `build_manifest.py`-equivalent logic just reshapes
them one-vector-per-file.

## Layout

```
manifest/
  MANIFEST.json    profile + reject_reasons taxonomy + per-vector expect/reason
  vectors/
    pos_*.json      preimage + expected action_ref (4)
    neg_*.json      invocation_payload + claimed (forbidden) action_ref + failure_mode (9)
  verify.py         reference verifier, Python stdlib only, zero deps
```

## Running it

```
python3 manifest/verify.py
```

Exits 0 only if every vector's verdict matches `MANIFEST.json`, both PASS and REJECT were
observed at least once, and every reason code in `reject_reasons` was exercised by at least one
negative vector. Exit 2 means the *suite itself* is broken (e.g. a reason code with no vector
covering it); exit 1 means a real conformance failure.

## The three rules a verifier in any language implements

1. **Positive** — recompute `action_ref = SHA-256(JCS(preimage))` over the 4-field tuple
   `{action_type, agent_id, scope, timestamp}`. MUST equal the vector's `action_ref`,
   byte-identical.
2. **Negative, `grammar_reject`** — `invocation_payload.timestamp` is not a canonical RFC 3339
   UTC string with 3-digit ms precision (e.g. it's a JSON integer). MUST reject before hashing
   is even attempted — never coerce to the canonical string form to retry.
3. **Negative, `recompute_mismatch`** — the payload is well-formed but a tuple field (field
   order, timestamp precision, agent_id casing, scope, or action_type) drifted from what the
   claimed `action_ref` was actually computed over. MUST recompute independently and reject on
   mismatch — never retry alternative preimages, reorder, or normalize to force a match.

Full spec: [`docs/spec/action-ref.md`](https://github.com/giskard09/argentum-core/blob/action-ref-v1.0/docs/spec/action-ref.md).

## License

MIT (same as the rest of this repo).
