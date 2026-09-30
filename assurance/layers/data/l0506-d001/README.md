# L0506-D001 evidence: prepared runtime numeric domain

This is the evidence for `spec/tools.md` Layer 06, "Prepared runtime numeric domain (`TOOL-041`)" (`minion-agent#88`). Every expectation comes from pinned Pi, executed unmodified. Neither binding is an authority.

All files here are byte-exact (`.gitattributes`: `-text`).

## Pins

| Pin | Value |
|---|---|
| Pi | `b7bb00b936dbe21b8e160b3e89efdec361846699`. `ai/src/utils/validation.ts` and `coding-agent/src/core/tools/edit.ts` are checked against `harness/pi_sources.sha256` |
| Runtime | `node:22.15.1-alpine` |
| `typebox` | 1.3.7, fetched with `npm pack`. Its SHA-512 must equal the integrity in pinned Pi's `package-lock.json`: `sha512-meKuifc33Pccx0O6PdIzYMq3Og8zvP4TIi/a+Bw3AEMZMxOD0+RHGQvpglEe6Zdy3wZ8nqn/j95h8LUZLk/6Hg==` |
| Cases | `cases.json`, regenerated deterministically by `harness/make_cases.py`. Its sha256 is `cases.sha256` |

## Reproduce

```sh
docker run --rm -v <pi>:/pi:ro -v <this directory>:/evid:ro -v <out>:/out node:22.15.1-alpine sh /evid/harness/run_authority.sh
python harness/make_scenarios.py cases.json <out>/authority.json <minion-agent>/conformance/agent/prepared-runtime
```

- `authority.json` must be byte-identical to `out/authority.json`.
- The regenerated scenarios must be byte-identical to the code repository's.

## What the authority runs

For each of the 27 cases, `harness/authority.mjs` runs Pi's own steps:
1. **Preparation**, `agent-loop.ts`'s `prepareToolCallArguments`. Either:
   - `edit`'s `prepareEditArguments`, the same verbatim copy the WP-13.2 authority uses; or
   - a custom `prepareArguments` that sets a runtime number.
2. **Validation**, Pi's unmodified `validateToolArguments`. The `edit` cases use `edit.ts`'s `editSchema`, sliced from the pinned source; the custom cases use a plain JSON Schema with a declared `number`, a declared `integer`, or no declared properties.
3. **Observation.** The observed value is what Pi passes to `beforeToolCall` as `args` and then, unchanged, to `execute`.

## Results

| Cases | Result |
|---|---|
| `edit`, `JSON.parse` path | `1e999` and a 400-digit integer give `+Infinity`, and their negatives give `-Infinity`. `-0` gives `-0`, `0` gives `0`, `1.7976931348623157e308` stays finite, and `9007199254740993` gives `9007199254740992`. All pass validation (an undeclared key of an edit item) and reach the hook |
| declared `number` | ±Infinity and NaN are **rejected** (`must be number`). `-0`, `1e308` and `0` pass; `-0` keeps its sign |
| declared `integer` | ±Infinity and NaN are **rejected** (`must be integer`). `-0`, `1e308` and `0` pass |
| undeclared key | every value is kept: ±Infinity, NaN, -0, 1e308, 0 |
| `declared-number-diagnostic-projection` (`L0506-D001-R001`) | rejected. Pi's failure diagnostic serializes the prepared arguments as `{"limit": null, "extra": null, "negativeZero": 0}`, while the runtime values stay +Infinity, NaN and -0 (`diagnostic_arguments` and `runtime_after_failure` in `out/authority.json`) |

## `characterization/`

These are the first-pass probes posted on `#88` (comment `5912236809`):
- `probe.mjs`/`run.sh`: Pi's validator over TypeBox and plain JSON Schema, including `Type.Integer()`, and what `JSON.parse` can produce.
- `py_probe.py`: certified Python Layer 06 on main `97d7c6bd`. It shows finding `L0506-D001-C001`: a declared `number` field accepts non-finite values.
