# L0206-D002 contract draft: raw `ToolCall.arguments` JavaScript value domain (`AI-003`)

- **Coordination:** `minion-agent#103`.
- **Governance:** Owner decision `L0506-D002-Q001`, Option 1 (`minion-agent#99` comment `5926162818`); `standing_delegation: minion-agent#75`.
- **State:** SCOPING → CONTRACT_DRAFT → CONTRACT_REVIEW.
- **Characterization:** `l0206-d002-characterization.md` (pass 1, 39 cases, Pi and Python).

## What this delivers

| Deliverable | Where |
|---|---|
| contract text | `spec/llm.md`, "Raw tool-call argument value domain (`AI-003`, cross-layer delta `L0206-D002`)". Also `spec/session.md` (event data domain) and a correction note on `spec/tools.md`'s L0506-D001 "two domains" line |
| manifest | `minion-agent` `pi-parity-manifest.yaml` `AI-003` (rule, tests, Python, Rust) and `MINION-002` (log domain). `TOOL-041`'s raw-domain sentence is corrected only after `L0506-D002` merges, to avoid concurrent edits of one row (`agent-workflow.md` §11.15) |
| canonical witnesses | `minion-agent` `conformance/agent/raw-arguments/`: 3 JSON documents, 33 cases, shape `raw-arguments-scenario.schema.json` |
| Python evidence | `tests/conformance/raw_arguments_runner.py`, `test_raw_arguments_conformance.py` (33), `tests/session/test_raw_arguments_negative_controls.py` (decision §11), schema tests. No production change |
| authority | `data/l0206-raw-boundaries/` (`harness/make_scenarios.py` generates the scenarios) |

## Cross-Language Feasibility Matrix (`process/templates/cross-language-feasibility-matrix.md`)

**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`. **Author:** Claude. **Independent checkpoint reviewer:** Codex.

### 1. Runtime value-domain matrix

| Observable value / field | Pi wire/source | Pi runtime | Python | Rust (certified) | Canonical | Lossless across all? | Witness |
|---|---|---|---|---|---|---|---|
| raw string leaf, scalar (ASCII, BMP, pair) | JSON text | UTF-16 code units | `str` | `serde_json` string | `{"utf16": units}` | YES | 5 cases |
| raw string leaf with an unpaired surrogate (any position, adjacent, reversed, mixed) | escaped `\udXXX` | UTF-16, lone kept | `str` (surrogate code points) | **cannot hold** | `{"utf16": units}` | **NO (Rust): Q001** | 14 cases + nested + array |
| raw string empty / NUL | `""`, `\u0000` | as given | `str` | `String` | units | YES | 3 cases |
| raw object key with an unpaired surrogate | escaped key | UTF-16 key | `str` key | **cannot hold** | `{"$keys": …}` | **NO (Rust)** | `keys/surrogate-keys` |
| raw number `-0` (also from `-1e-400`) | `-0` | `-0` | `float -0.0` | `f64 -0.0`, if the number path keeps it (to verify) | `{"number": "-0"}` | Python YES; Rust TO VERIFY | 2 cases |
| raw number ±Infinity (overflow literal) | `1e999`, 400 digits | ±Infinity | `float ±inf` | **cannot hold** | `{"number": "+Infinity"}` | **NO (Rust)** | 3 cases |
| raw number binary64 rounding | `9007199254740993` | `9007199254740992` | `int` (value as decoded) | `serde_json` number | token | YES for the decoded value; decoder requirement below | 1 case |
| raw key enumeration order | JSON object | ECMAScript order | insertion order | sorted | not asserted | NO (both) | **`L0206-D001`** (#100), outside this delta |
| Pi persisted session line | — | `JSON.stringify`: `-0`→`0`, ±Inf→`null`, lone→`\udXXX` | no persisted byte form (Layer 03 is in memory) | none | n/a | N/A at certified layers | characterized (R-N2/R-N3) |

**Four value domains** (template §1.1):

| Domain | Status |
|---|---|
| INSTANCE | prepared values are `L0506-D002`; the raw instance is this delta |
| SCHEMA | `L05-D001`; here only the open schema `{type: object, properties: {}}` is used, which is scalar |
| RAW/WIRE | this delta; the decoder requirement R-N4 is stated |
| SERIALIZED/PROJECTED | Pi's persisted JSON line is characterized (no Minion counterpart yet); provider-outbound (`sanitizeSurrogates`) is Layer 11's |

### 2. Lower-layer capability matrix

| Operation | Layer | Certified seam | Exact Pi semantics? | Python | Rust | Additive extension? | Non-additive reopen? |
|---|---|---|---|---|---|---|---|
| construct a `ToolCall`/`AssistantMessage` holding the domain | 02 | `ToolCallBlock.arguments: dict` / `llm/vocabulary.rs` | Python yes | YES | **NO** | **YES:** a raw runtime value type (decision §7) | NO |
| session append + replay | 03 | `SessionLog.append` + `encode_message`/`decode_message` | Python yes | YES | **NO** (event data is `serde_json`) | **YES:** the same value type in event data | NO |
| `tool_execution_start`/`_update` payload | 06 | event emission | Python yes | YES | NO until the above lands | rides on the above | NO |
| Layer-06 input, no `prepare_arguments` | 06 | `execute_call` | Python yes | YES | NO until the above lands | rides on the above (meets L0506-D002's prepared type) | NO |
| raw decoder (provider text → value) | 11 (future) | none certified | — | `json.loads` is **not** `JSON.parse`-equivalent (2^53+1, `-0`, overflow) | — | the R-N4 requirement on Layer 11 | NO |

### 3. Cross-runtime hazard checklist

| Hazard | State | Evidence / reason |
|---|---|---|
| `JSON.parse` | AUDITED | strings, numbers, keys, duplicates (last value, first position), `__proto__` own property |
| `JSON.stringify` | AUDITED | the persisted-line projection (R-N2); not a Minion boundary today |
| `Number` conversion | AUDITED | binary64 rounding, `-0`, overflow, underflow |
| `Math` semantics | NOT_APPLICABLE | none on this path |
| negative zero | AUDITED | live `-0` through every Pi boundary; Python carries it |
| non-finite values | AUDITED | live ±Infinity; Python carries it; Rust cannot |
| `String.length` / UTF-16 | AUDITED | code units at every boundary |
| `RegExp` | NOT_APPLICABLE | the open schema has no `pattern` |
| Unicode / ICU | NOT_APPLICABLE | no normalization on this path |
| array ordering | AUDITED | array string case keeps order |
| object property ordering | DEFERRED_WITH_REASON | `L0206-D001` (#100), by Owner decision K1 |
| Promise scheduling, `AbortSignal`, timers | NOT_APPLICABLE | unchanged certified behavior |
| Node errors, filesystem, paths | NOT_APPLICABLE | none |
| package versions | AUDITED | Node 22.15.1, typebox 1.3.7 (SRI), `pi_sources.sha256` |

### 4. Concurrency / order

`NOT_APPLICABLE`: no new async behavior.

### 5. Neighborhood expansion record

| Family | Members probed | Source | Rows / findings |
|---|---|---|---|
| F2 String/UTF-16 | the decision §6 list: 19 members, nested, array, literal pair | `raw_probe.mjs` | string rows |
| F1 Number | large finite, 2^53+1, `-0`, 0, ±overflow, 400 digits, ±underflow, subnormal | `raw_probe.mjs` | number rows; numbers folded in (characterization scope decision) |
| F6 Object order | the K1 neighborhood | `raw_probe.mjs` | deferred to `L0206-D001` |
| F7 Schema domain | the open schema only | — | `L05-D001` owns the schema domain |

### 6. Verdict

```text
FEASIBILITY
    READY for the L0206-D002 scope: every row AUDITED / NOT_APPLICABLE / DEFERRED_WITH_REASON.
    The Rust "NO" rows are Q001 itself, resolved by the raw runtime value type the Owner decision authorizes (§7).
    Rust -0 handling is flagged TO VERIFY for the contract review.
    Outside the scope, with owners: L0206-D001 (key order), L05-D001 (schema domain), Layer 11 (decoder, R-N4).
```

## Decisions made in the draft (for the independent review)

1. **Numbers are folded in.** Raw ±Infinity and `-0` share the root, the boundaries and the Rust type with the strings (characterization, scope decision). This is flagged for Owner override.
2. **Persisted form is N/A at the certified layers.** Minion's Layer-03 log is in memory and replays the live value. Pi's persisted-line projection is characterized for whichever layer later maps `session-manager.ts`.
3. **The decoder is a requirement, not a seam.** There is no certified Minion raw decoder. R-N4 binds the first one, Layer 11. `provider_text` is carried in each case as evidence.
4. **The event payload is observed by value.** Pi hands the hook a `structuredClone` (`validateToolArguments`), so object identity is not part of the contract.
5. **`TOOL-041`'s raw sentence is corrected later.** `spec/tools.md` gets a correction note now. The `TOOL-041` manifest row is edited after `L0506-D002` merges, since that delta is editing the row.

## Reviewer checklist

1. Reproduce `data/l0206-raw-boundaries/out/raw.json` and the scenario directory (README-equivalent commands in `harness/`).
2. Check every boundary in the decision §4 table, and the N/A reasons.
3. Check decisions 1-5, especially the numeric fold-in and the persisted-form N/A.
4. Check the §11 negative controls kill their mutants (`test_raw_arguments_negative_controls.py`).
5. Check Rust feasibility: a raw runtime value type for `ToolCall.arguments`, session event data and event payloads; `-0` handling.

## Status

- `L0206-D002` contract: READY FOR INDEPENDENT CONTRACT REVIEW.
- Python: conforms with no production change (33 cases, all six boundaries; §11 negative controls), PENDING contract review.
- Rust: NOT_IMPLEMENTED.
- WP-13.2: non-blocking (characterization §10 check).
