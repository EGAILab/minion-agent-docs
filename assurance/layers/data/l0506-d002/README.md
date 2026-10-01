# L0506-D002 evidence: prepared runtime JavaScript string domain

This is the evidence for `spec/tools.md` Layer 06, "Prepared runtime string domain (`TOOL-041`, post-certification delta `L0506-D002`)" (`minion-agent#99`). Every Pi-derived expectation comes from pinned Pi, executed unmodified. Neither binding is an authority.

All files here are byte-exact (`.gitattributes`: `-text`).

## Pins

| Pin | Value |
|---|---|
| Pi | `b7bb00b936dbe21b8e160b3e89efdec361846699`. `agent/src/agent-loop.ts`, `ai/src/utils/validation.ts` and `coding-agent/src/core/tools/edit.ts` are checked against `harness/pi_sources.sha256` |
| Runtime | `node:22.15.1-alpine` |
| `typebox` | 1.3.7, fetched with `npm pack`. Its SHA-512 must equal the integrity in pinned Pi's `package-lock.json` |
| Cases | `cases.json` (189 cases), regenerated deterministically by `harness/make_cases.py`. Its sha256 is `cases.sha256` |

## Reproduce

```sh
docker run --rm -v <pi>:/pi:ro -v <this directory>:/evid:ro -v <out>:/out node:22.15.1-alpine sh /evid/harness/run_authority.sh
python harness/make_scenarios.py cases.json <out>/authority.json <minion-agent>/conformance/agent/prepared-runtime-string
```

- `authority.json` must be byte-identical to `out/authority.json` (sha256 `664662eb89bfdc9ddd6ad381bdbd89b852ed6720802218c63f4dad2188e3fead`).
- The regenerated scenarios must be byte-identical to the code repository's.

## What the authority runs

Unlike the L0506-D001 authority, the agent-loop steps are not paraphrased. `harness/authority.mjs` slices these functions from pinned `agent-loop.ts` at run time and strips only the erasable TypeScript annotations (`node:module` `stripTypeScriptTypes`):
- `prepareToolCallArguments`
- `prepareToolCall`
- `executePreparedToolCall`
- `finalizeExecutedToolCall`
- `createErrorToolResult`

It runs them with Pi's unmodified `validateToolArguments`. For each case:
1. **Preparation.** Either:
   - a custom `prepareArguments` that sets strings (`{"utf16": units}`) and single-key objects (`{"$key": units, "value": v}`) at top-level pointers, against one of 8 plain JSON Schemas; or
   - the real `edit` path: `prepareEditArguments` and `editSchema`, sliced from pinned `edit.ts`, over a string `edits` written with `\uXXXX` escapes.
2. **Validation, hook, execute, after-hook**, through Pi's own functions, with `beforeToolCall`, `execute` and `afterToolCall` recording what they receive.
3. **Observation.**
   - The UTF-16 code units at each `observe` pointer and the keys at each `observe_keys` pointer, for each observer, and whether the three observers received the same object.
   - **Separately**, the projections: UTF-8 (`Buffer.from(s, "utf8")`, which is what `fs.writeFile(path, s, "utf-8")` does) and `JSON.stringify`.
   - On a failure: Pi's diagnostic text and the untouched prepared values.

## Results

| Cases | Result |
|---|---|
| 20 neighborhood members × `open` / `string` | all kept, exact code units, at the hook, execute and after-hook (one object) |
| × `min-length-2` / `max-length-1` | code-point counts: a pair is 1, each unpaired surrogate is 1 |
| × `pattern-one-char` / `pattern-two-chars` | Unicode mode: `.` matches a pair or an unpaired surrogate as one character |
| × `const-pair` / `enum-lone` | exact code-unit equality |
| `position/*` (3) | nested value, array element, a lone high and a lone low together: kept |
| `key/*` (5) | lone high, lone low, pair, reversed pair and empty keys: kept |
| `diagnostic/lone-surrogates` | rejected. The diagnostic escapes `\ud800\ud800`, `A\udc00` and `\u0000`, and emits the pair literally. Runtime values are unchanged, and no hook or execute runs |
| `edit/*` (20) | every member prepared. The hook observes the exact code units. The raw arguments are mutated in place by Pi (Minion's certified rule gives `prepare_arguments` a fresh copy instead). UTF-8 projection: unpaired surrogate → `EF BF BD` |

All 180 cells shared with characterization pass 1 (`../l0506-d002-characterization/`) agree in verdict, code units and projections.
