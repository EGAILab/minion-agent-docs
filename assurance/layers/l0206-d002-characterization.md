# L0206-D002: raw `ToolCall.arguments` JavaScript value domain (characterization, pass 1)

- **Coordination:** `minion-agent#103` (SCOPING).
- **Governance:** the Owner decision on `L0506-D002-Q001`, Option 1 (`minion-agent#99` comment `5926162818`).
- **Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`.
- **Python measured at:** `minion-agent` main `365ea754`.

This is characterization evidence, not a contract. The same raw-boundary observations also feed `L0206-D001` (K1, `#100`). They are recorded below and are not folded in.

## Method (`data/l0206-raw-boundaries/`)

`harness/raw_probe.mjs` runs under `node:22.15.1-alpine`, with source hashes checked by `harness/pi_sources.sha256` and `typebox` 1.3.7 SRI-checked. Each of the 39 cases is a provider's final tool-call argument **text**. The probe follows its value through pinned Pi's own boundaries:

| Boundary | Pinned Pi operation |
|---|---|
| decode | `ai/src/utils/json-parse.ts` `parseJsonWithRepair` (the first thing `parseStreamingJson` tries), sliced from source. The only change is dropping the `export` keyword, which `new Function` cannot hold |
| ToolCall / AssistantMessage | the decoded object is `toolCall.arguments` |
| persist | `coding-agent` `session-manager.ts:1021` `` `${JSON.stringify(entry)}\n` `` for a message entry holding the call |
| replay | `session-manager.ts:306` `JSON.parse(line)` |
| `tool_execution_start` / `_update` | `agent-loop.ts:388-391, 446-449, 501-504` and the `executePreparedToolCall` update callback carry `toolCall.arguments` (the raw object). `tool_execution_end` carries no arguments: N/A |
| Layer-06 input, **no `prepareArguments`** | `agent-loop.ts` `prepareToolCall` / `executePreparedToolCall` / `finalizeExecutedToolCall`, sliced from source, for a tool with no `prepareArguments` and an open schema: what `beforeToolCall` and `execute` observe |

Values are rendered as UTF-16 code units, number tokens, and per-object key enumeration order.

**Python** is measured by `harness/py_probe.py`, compared by `harness/compare.py`. It uses certified seams:
- `ToolCallBlock` construction;
- `SessionLog.append` with `encode_message`, then replay via `decode_message`;
- the `tools/execution-start` payload;
- `execute_call` with the pre-execute hook and `execute`.

Minion has no raw JSON decoder yet (Layer 11 owns provider decoding). Python's `json.loads` is recorded as a **reference** for what a decoder built on it would do, not as a Minion seam.

**Hashes (SHA-256):**
- `cases.json`: `b63354b9c6bf5270a0ba3b2774936455b5e44541a83eaed6a26630c42292b415`
- `out/raw.json`: `239f777ee4f6569dd613ded648ff989184ba56dc0cbcf772d9cfa71a4e937b23`
- `out/python.json`: `6848eedb1a67fa9d7084a4ed086aeca93888fd835d79491b6b0bd23b72f34d1f`

## Findings: strings (Q001 proper)

**R-S1. Pi's raw domain is the JavaScript String.**
- All 19 members of the decision's §6 string neighborhood keep their exact UTF-16 code units when decoded from escaped JSON text. So do a nested object string, an array string and an unescaped astral literal. Unpaired highs and lows are kept at every position.
- They reach `tool_execution_start`, `beforeToolCall` and `execute` unchanged, **with no `prepareArguments`**.

**R-S2. Pi's JSON projection round-trips strings exactly.**
- `JSON.stringify` (the persisted session line) escapes each unpaired surrogate as `\udXXX`, which is ASCII, so the file's UTF-8 encoding cannot replace it. It writes a valid pair as its UTF-8 character and NUL as `\u0000`.
- `JSON.parse` replay restores the identical code units for all 22 string cases.
- So, unlike the D002 `edit` file-bytes boundary, **no U+FFFD appears anywhere on the raw path** (decision §5: characterized, not assumed).

**R-S3. Python carries every string case exactly** through every certified seam: construction, session append and replay, the event payload, the hook and `execute`. The Owner's §8 requires permanent witnesses for this; they will come with the contract.

**R-S4. Rust (feasibility).** Its raw `ToolCall.arguments` is a `serde_json::Value`, and a `serde_json` string cannot hold an unpaired surrogate. The 14 lone-surrogate cases, the nested and array cases, and the surrogate-key case are not representable. This is the `Q001` defect (decision §3, §7).

## Findings: numbers (decision §6, "other already-known mismatches")

**R-N1. Pi's raw domain carries JavaScript runtime numbers.**
- `JSON.parse` gives:
  - `-0` → `-0`;
  - `1e999` and a 400-digit integer → `+Infinity`, and `-1e999` → `-Infinity`;
  - `9007199254740993` → `9007199254740992` (binary64 rounding);
  - `-1e-400` → `-0`, `1e-400` → `0`;
  - `5e-324` and `1.7976931348623157e308` kept.
- `beforeToolCall` and `execute` observe these **live**, with no `prepareArguments`. This is the D001 numeric domain reaching the raw path.

**R-N2. Pi's persisted projection loses them.** `JSON.stringify` writes `-0` as `0` and ±Infinity as `null`, so replay yields `0` and `null`. The live and replayed values differ in pinned Pi itself.

**R-N3. Minion has no persisted byte form at the certified Layer 03.**
- Minion's session log is in memory and "JSON-validated", and replays exactly what was appended. Pi's JSONL persistence lives in `coding-agent` `session-manager.ts`, which no manifest row maps today.
- So the persisted-form boundary (§4) is **`NOT_APPLICABLE` at the certified layers**, with the projection characterized here for whichever layer later maps Pi's session file.
- **Contract consequence for this delta:** Minion's log must **accept** the raw values Pi carries live (strings exactly; ±Infinity, `-0`), and its replay must return them unchanged, as Python's does today. Any future byte-level persistence must reproduce R-N2's projection.

**R-N4. A raw JSON decoder must be `JSON.parse`-equivalent.** Python's `json.loads` (the reference) differs from Pi in three ways:
- it keeps `9007199254740993` as an exact `int`;
- it decodes `-0` as `int 0`, losing the sign;
- it decodes a 400-digit integer as an exact big `int`, not `+Infinity`.

No certified Minion seam decodes raw JSON today, so this is **not a current defect**. It becomes a requirement on the first raw decoder: Layer 11 providers, which per the decision §12 consume this contract.

**R-N5. Rust (feasibility).** `serde_json::Value` cannot hold ±Infinity. It can hold `-0.0`, depending on its number handling, which the contract review should verify. So the numeric half has the same root cause and the same type as R-S4.

### Scope decision (§6: "decide whether it belongs in the same coherent raw-value delta")

Raw numbers **are folded into L0206-D002**. The delta becomes the raw `ToolCall.arguments` **JavaScript value** domain: strings and numbers. Reasons:
- **Same root.** The raw domain is `JSON.parse`'s runtime value, not the JSON document.
- **Same boundaries.** Decode, ToolCall, session append and replay, events, Layer-06 input.
- **Same Rust type.** One representation change in `serde_json::Value`'s place, not two.

Splitting them would schedule two rewrites of the same Rust type. K1 (key order) stays in `L0206-D001`, as the decision requires.

This is recorded under the authorization for a "targeted Layer 02/03/05/06 audit" and "no intentional divergence". It is flagged for Owner override.

## Findings: WP-13.2 independence (decision §10)

**Question:** does any TOOL-029..033 owned observable require lossless **raw** surrogate preservation before `prepare_arguments`?

**Answer: no.** `spec/tools.md` WP-13.2 already makes its rules "total for any string a binding does receive". Its corpus flags `unpaired_surrogate_arguments` cases:
- a binding whose decoding carries them MUST pass them;
- a binding that cannot MUST show the argument is rejected before the tool runs, recorded as the Layer 02/05 hazard, not as a pass;
- "Lone-surrogate argument decoding (Layer 02/05)" is listed as not certified by WP-13.2.

So WP-13.2's owned outputs do not depend on raw preservation. **L0206-D002 is non-blocking for WP-13.2.** When it lands, those flagged cases become ordinary passes in Rust.

## Observations for `L0206-D001` (K1), not decided here

The same probe shows Pi's raw key order is ECMAScript order at every boundary:
- decode: array-index keys first, ascending; `4294967294` is an index and `4294967295` is not; non-canonical numerals keep insertion order; nested levels follow the same rule;
- persist (`JSON.stringify` emits enumeration order);
- replay;
- the hook and `execute`.

A duplicate key keeps its first position with the last value. `__proto__` is an own property.

Python preserves insertion order at every seam: KEY-ORDER differences on `mixed-index-first`, `index-boundaries`, `non-canonical-numerals` and `nested`. These are inputs to #100's characterization.

## Next

- Fill the feasibility matrix.
- Draft the contract:
  - the raw value domain;
  - each §4 boundary, or N/A with its reason;
  - the decoder requirement R-N4;
  - permanent Python witnesses (§8);
  - the §11 negative controls;
  - canonical cases using a no-`prepare_arguments` tool.
- Hand the contract to Codex for independent review.
