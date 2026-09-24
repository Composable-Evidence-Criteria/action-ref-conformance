# action-ref-conformance

A GitHub Action that verifies an implementation — or a set of vendored fixtures — against the
frozen **`action-ref-v1-jcs-sha256`** conformance profile from
[argentum-core](https://github.com/giskard09/argentum-core/blob/main/docs/spec/action-ref.md).

Zero dependencies. Python stdlib only. No network calls in the trust path — the vectors are
vendored inside this Action and pinned by git tag. Nothing here fetches anything at run time.

## The claim

**The claim is the green run with the pinned action, not the badge.**

A badge in a README is a screenshot. It proves nothing by itself — anyone can paste an SVG.
What proves conformance is a CI run, on a pinned tag of this Action, against vectors that
implementer did not write themselves, producing byte-identical digests. That run is public,
timestamped, and reproducible by anyone who clones the repo and re-runs the workflow.

Because of that:

- Vectors are frozen per tag (`v1` = `action-ref-v1-jcs-sha256`, never modified in place — a
  new profile version ships as a new tag, not an edit to `v1`).
- A row in [PROVIDERS.md](https://github.com/giskard09/argentum-core/blob/main/PROVIDERS.md)
  is added only after manual verification of the actual green run — not on request, not from a
  badge screenshot, not from a self-reported claim.
- `verify-vendored` exists so an implementer can vendor the fixtures into their own repo
  (the pattern established by [babyblueviper1](https://github.com/babyblueviper1)) and prove in
  their own CI that the vendored copy still matches the canonical hashes — a stronger claim than
  a one-time run, because it re-verifies on every commit.

## Modes

> The organization name for this repository is provisional and may change. The examples
> below use `<lab-org>` as a placeholder: replace it with the organization that hosts this
> repository when you use the Action.

### `verify-impl`

You provide a `command` — any executable that reads a preimage JSON object on stdin and writes
the resulting `action_ref` (hex SHA-256 digest) to stdout. The Action runs it against 8 frozen
vectors:

- **4 positives** — your command must reproduce the canonical `action_ref` **byte-identical**.
- **4 negatives** — drifted preimages (non-canonical timestamp forms: epoch-integer,
  second-precision, microsecond-precision; non-canonical field order). Your command must either
  **reject** the input, or its output must **diverge** from the forbidden canonical hash. A
  command that silently normalizes a drifted form to match the canonical digest has a
  conformance bug — it means an attacker could construct a colliding claim from a
  non-canonical byte form.

```yaml
- uses: <lab-org>/action-ref-conformance@v1
  with:
    mode: verify-impl
    command: python3 my_action_ref.py
```

Where `my_action_ref.py` reads one JSON object from stdin and prints the digest:

```python
import sys, json, hashlib

preimage = json.load(sys.stdin)
canonical = json.dumps(preimage, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
print(hashlib.sha256(canonical.encode()).hexdigest())
```

### `verify-vendored`

You provide `fixtures-path` — a JSON file (or directory of JSON files) you vendored into your
own repo. The Action checks that every canonical positive vector is present and byte-identical
in your vendored copy.

```yaml
- uses: <lab-org>/action-ref-conformance@v1
  with:
    mode: verify-vendored
    fixtures-path: ./fixtures/action-ref-v1
```

## Full workflow example

```yaml
name: action-ref conformance
on: [push, pull_request]
jobs:
  conformance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: <lab-org>/action-ref-conformance@v1
        with:
          mode: verify-impl
          command: python3 my_action_ref.py
```

That's the whole thing — 10 lines, no other setup.

## Outputs

- `report` — path to a JSON report with a per-vector `passed` boolean, also written to the
  step summary as a PASS/FAIL table.
- `passed` — `"true"` / `"false"`.

The Action exits non-zero if any vector fails, so it fails the workflow by default.

## Profile

`action-ref-v1-jcs-sha256` — `SHA-256(JCS(preimage))` where `preimage` is the 4-field object
`{action_type, agent_id, scope, timestamp}` canonicalized per RFC 8785 (JCS). Full spec:
[docs/spec/action-ref.md](https://github.com/giskard09/argentum-core/blob/action-ref-v1.0/docs/spec/action-ref.md).

Vectors are sourced from `argentum-core/examples/conformance/action-ref-v1-baseline.fixture.json`
(positives) and `.../recompute-drift-v1/recompute-drift-v1-negative.fixture.json` (negatives).
See [`vectors/action-ref-v1-jcs-sha256.json`](./vectors/action-ref-v1-jcs-sha256.json) for the
exact frozen set.

## Portable conformance manifest

[`manifest/`](./manifest/) packages the same frozen vectors (plus the full 9-vector negative
set, not just the 4 curated for the Action) as one-file-per-vector + `MANIFEST.json` +
a stdlib-only `verify.py` — no GitHub Actions runtime required, runnable from any language that
implements the three rules in [`manifest/README.md`](./manifest/README.md). Same shape as
[jsuich/x402-action-receipt](https://github.com/jsuich/x402-action-receipt)'s conformance set,
built in reciprocity after running theirs (36/36 PASS, verified independently).

## Portable conformance manifest — v2 (domain-separated)

[`manifest-v2/`](./manifest-v2/) packages the **additive** `action-ref-v2-domain-separated`
profile in the same one-file-per-vector shape: 3 positives (v1 and v2 digest for the same
preimage, non-colliding) plus 3 negative vectors that each demonstrate a distinct way the
cross-protocol collision risk motivating the v1→v2 split (any protocol that independently
arrives at the same four-field JCS shape and bare SHA-256 produces byte-identical output for
the same event) can resurface even under a naive "v2": a bare untagged hash passed off as v2,
a wrong/generic domain tag, and a tag applied after hashing instead of before. v1 is never
replaced or narrowed — see [`manifest-v2/README.md`](./manifest-v2/README.md) and
[argentum-core's RFC 002](https://github.com/giskard09/argentum-core/blob/main/docs/rfcs/002-action-ref-v2-domain-separation.md)
for the full design rationale.

## License

Apache-2.0. Relicensed from MIT on 2026-07-29 (single-contributor, 0 forks — see commit for details).
