# Cross-Language Feasibility Matrix — `L0506-D003`: tool-result runtime value domain

**Required by:** `process/agent-workflow.md` §4.1.1 and Owner decision `WP132-RUST-C002-Q001` §18 (`minion-agent#49` comment `5937380474`). Written in remediation of `L0506-D003-R004`.
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`. **Author:** Claude (shared-contract owner). **Independent checkpoint reviewer:** Codex.
**Candidate:** the remediated heads recorded on `minion-agent#112`.
**Evidence:**
- characterization `l0506-d003-characterization.md`, authority `97fa2ae9…`;
- contract `l0506-d003-contract.md`;
- `spec/tools.md` "Tool-result runtime value domain";
- `spec/session.md` event-data domain.

Rust is inspected here **for feasibility only**, never as a semantic oracle. Its type design stays Rust-owned.

---

## 1. Runtime value-domain matrix

One row per observable value that crosses a boundary of the tool-result carrier. "Pi runtime" is the in-memory value pinned Pi's `agent-loop.ts` carries unchanged through every boundary (characterization §3.1).

| Observable value / field | Pi wire/source repr | Pi runtime repr | Python repr | Rust repr today | Canonical serialization | Lossless across all? | Risk / witness |
|---|---|---|---|---|---|---|---|
| result `content[].text` | JS String from the tool, or `error.message` | JS String (UTF-16) | `str` (pairs combined, lone surrogates kept) | `TextBlock.text: String` | `{"utf16": units}` | **NO (Rust)** | `text/*` (16) and `tool-throws/*` (3); negative controls `message-text-only-normalized`, `tool-return-fffd` |
| `details` string leaf, any depth | JS value from the tool or hook | JS String | `str` | `serde_json::Value::String` | `{"utf16": units}` | **NO (Rust)** | `details-leaf/array/nested/top-string/*` (64); `message-nested-details-normalized` |
| `details` object **key** | JS property name | JS String | `str` dict key | `serde_json::Map<String, _>` | `{"$keys": …}` | **NO (Rust)** | `details-key/*` (16); `message-keys-replaced` |
| `details` number `-0` | JS number | binary64 `-0` | `float -0.0` | `serde_json::Number` (keeps `f64 -0.0`; no gate today) | `{"number": "-0"}` | AUDITED for Python; Rust **to be shown** | `details-*-number/-0` (3); `message-json-number-projection` |
| `details` number ±Infinity, `NaN` | JS number | binary64 | `float` | `serde_json::Number` **cannot** hold them | `{"number": "+Infinity"/"-Infinity"/"NaN"}` | **NO (Rust)** | `details-*-number/±Infinity,NaN` (9); `hook-replace/details-number` |
| finite `details` numbers | JS number | binary64 | `int`/`float` | `serde_json::Number` | canonical `Number::toString` token | YES | `details-*-number/{0,1.5,max,min,2^53}` |
| `details` `null`, booleans, arrays, objects (nested) | JS values | as JS | `None`/`bool`/`list`/`dict` | `Value` | grammar | YES | `details-scalar/*`, `details-empty-*` |
| top-level `details` `null` / absent / `undefined` | JS `null`/`undefined` | distinct | `None` = absent | `Option<Value>` | — | **DEFERRED_WITH_REASON**: ADJ-2, the certified `IR-L06-004` host mapping, raised with the Owner | excluded from the gate (4 cases) |
| hook replacement `content`/`details` | JS value from the hook | carried on (`?? current`) | `AfterToolCallOverride` | `AfterToolCallResult`: `String`/`Option<Value>` | grammar | **NO (Rust)** for strings/keys/non-finite | `hook-replace/*` (3) |

Members of the JavaScript-derived list:
- **Applicable and AUDITED:** finite binary64, `+0`, `-0`, the 2^53 boundary, the largest finite value, ±Infinity, `NaN`, `null`, `false`/empty (`""`, `[]`, `{}`), UTF-16 code units, valid pairs, lone high and low surrogates. `JSON.stringify` projection is the session-file row in §1.1.
- **`undefined` / missing:** DEFERRED_WITH_REASON (ADJ-2).
- **Large-integer rounding:** NOT_APPLICABLE. A tool result is a runtime value, not decoded text, so no rounding occurs on this carrier.
- **Numeric-looking strings:** NOT_APPLICABLE. No coercion occurs on this carrier; they are ordinary strings.
- **Unicode normalization/version:** NOT_APPLICABLE. No operation on this carrier normalizes or compares text.

### 1.1 Value-domain carriers (Owner §18)

| Carrier | Pi repr | Python repr | Rust repr | Owning seam | Lossless across all? |
|---|---|---|---|---|---|
| RAW INPUT VALUE DOMAIN | JS value from `JSON.parse` | `str`/`int`/`float` | `RawValue` (`L0206-D002`) | Layer 02 | YES. CERTIFIED_CLOSED (`#103`); NOT_APPLICABLE to this carrier except as the source of a `path` that error text interpolates |
| PREPARED VALUE DOMAIN | JS value from `prepareArguments` | as above | `PreparedValue` (`L0506-D001`/`D002`) | Layers 05/06 | YES. CERTIFIED_CLOSED (`#88`, `#99`); the source of `edit`'s `newText` |
| SCHEMA VALUE DOMAIN | JS schema object | `dict` | `RuntimeSchemaObject` (`L05-D001`) | Layer 05 | YES. CERTIFIED_CLOSED (`#104`); NOT_APPLICABLE to the result carrier |
| **TOOL RESULT VALUE DOMAIN** | JS value: text + recursive `details` | `ToolResult` / `ToolResultMessage` | `AgentToolResult.details: Value`, `ToolResultMessage.details: Option<Value>`, `AfterToolCallResult.details: Option<Value>`, `TextBlock.text: String` | Layers 05/06 (+ Layer 02 vocabulary) | **NO (Rust)**: this delta |
| PERSISTENCE PROJECTION | Pi file: `JSON.stringify` line, `JSON.parse` reload (escape `\udXXX` and round-trip; `-0`→`0`; non-finite→`null`; `undefined` omitted) | log keeps the live value (`MINION-002`) | typed `SessionField::Message(Box<Message>)` (live, `L0206-D002`) | Layer 03 | Minion log: YES for Python; Rust once `Message` carries the domain. Pi file projection: DEFERRED_WITH_REASON, no Minion session file exists (obligation recorded per case as `pi_session_file`) |
| PROVIDER PROJECTION | `sanitizeSurrogates` deletes lone surrogates from outbound text; `details` not sent | — | — | Layer 11 | DEFERRED_WITH_REASON: decision §12, a future-boundary obligation of the provider layer |

**The Owner's six questions, for the TOOL RESULT carrier:**
1. **What can Pi produce?** Every member of §1. Reachable through `edit` (prepared `newText` into diff/patch), error text (raw `path`), custom tools and hook replacement.
2. **Can Python represent it?** Yes, except `undefined` (ADJ-2). Python's live boundaries conform. One replay defect (`R001`) is fixed in this remediation.
3. **Can Rust represent it?** Not today. `String` and `serde_json::Value` cannot hold lone surrogates, surrogate keys or non-finite numbers. A lossless result value is required (§2).
4. **What do hooks/events see?** The tool's own values (the hook receives the very object); replacements are carried on; `tool_execution_end` and the message carry the same values.
5. **How are they serialized?** Minion's log: not serialized (live value). Pi's file: `JSON.stringify`, which is a projection. The provider: not this delta.
6. **Where is lossy projection allowed?**
   - only at the filesystem UTF-8 boundary (WP-13.2 `write`/`edit`: `EF BF BD`);
   - in a future persisted file, reproducing Pi's projection there only;
   - at the provider boundary (Layer 11).

   Never earlier.

## 2. Lower-layer capability matrix

| Required semantic operation | Owning lower layer | Existing certified seam/API | Exact Pi semantics? | Python sufficient? | Rust sufficient? | New additive extension? | Non-additive reopen? |
|---|---|---|---|---|---|---|---|
| a tool returns `{content, details}` in the domain | 05 (tool model) | Py `ToolResult`; Rs `AgentToolResult` | yes | YES | **NO** (`String`, `Value`) | YES: this delta (a lossless result value; Rust-owned type design, reuse of `JsString`/`PreparedString`/`RawValue` primitives encouraged, decision §14). Note that `NaN` is needed, which `RawNumber` rejects | no |
| after-hook observes and replaces | 06 (`TOOL-005`) | Py `register_after_tool_call_hook`/`AfterToolCallOverride`; Rs `AfterToolCallResult` | yes (`??`) | YES | **NO** | YES: same value type in the override | no |
| failure conversion keeps the message's code units | 06 (`IR-L06-004`) | Py `text_result(str(error))`; Rs error text `String` | yes | YES | **NO** (lone surrogate in a Rust error message) | YES: result text in the lossless string | no |
| live `tool_execution_end` carries the final values | 06 (`TOOL-017`) | Py `tools/execution-end`; Rs `ToolExecutionEnd { result: AfterToolCallResult }` | yes | YES | **NO** | YES: follows the result type | no |
| `ToolResultMessage` carries them | 02 vocabulary (`AI-006`) | Py `ToolResultMessage`; Rs `ToolResultMessage { content, details: Option<Value> }` | yes | YES | **NO** | YES | no |
| session append + committed-history replay | 03 (`MINION-002`) | Py `SessionLog.append` + `derive_messages`; Rs `Session` typed `Message` field + `derive_messages` | yes (live) | YES (`float` NaN admitted) | YES once `Message` is lossless; the session domain must admit `NaN` for the tool-result carrier (`R003`, `spec/session.md` reconciled) | no new seam | no |
| event replay from the log (where a binding has one) | 08 (Python `project`) | Py `agent/projection.py`; Rs: none (live events only) | yes | YES after `R001` (falsy `details` kept) | NOT_APPLICABLE (no such surface; none required) | no | no |

No non-additive reopen is required, and none is requested. Every Rust gap is additive and falls inside the authorized delta.

## 3. Cross-runtime hazard checklist

| Hazard | State | Evidence / reason |
|---|---|---|
| `JSON.parse` | NOT_APPLICABLE | No decode on this carrier at runtime. The Pi file's reload is recorded as `pi_session_file`, as evidence only |
| `JSON.stringify` | AUDITED | Pi file projection characterized (§1.1). It is excluded from the runtime value; the `session-stores-pi-file-projection` control kills a log that applies it |
| `Number` conversion / coercion | NOT_APPLICABLE | No coercion; values are carried, not computed |
| `Math` semantics | NOT_APPLICABLE | No arithmetic on the carrier |
| negative zero | AUDITED | 3 cases; `message-json-number-projection` |
| non-finite values | AUDITED | 9 cases plus a hook replacement; folded under decision §6 |
| `String.length` / UTF-16 | AUDITED | Strings are observed as code units at every boundary |
| `RegExp` | NOT_APPLICABLE | No pattern matching on the carrier |
| Unicode / ICU version | NOT_APPLICABLE | No normalization, case mapping or collation. The WP-13.2 gate's `edit` uses certified ICU only through the edit tool's own contract |
| Array ordering | AUDITED | Arrays carried in order (`details-array*`) |
| Object property ordering | DEFERRED_WITH_REASON | K1, `L0206-D001` (`#100`); `details-key-order` recorded; objects compare as key sets |
| Promise scheduling | NOT_APPLICABLE | One sequential call per case; certified Layer-06 event ordering (`TOOL-017`) is unchanged |
| `AbortSignal` | NOT_APPLICABLE | No abort on this carrier; certified Layer 09 |
| timers | NOT_APPLICABLE | none |
| Node/libuv error mapping | NOT_APPLICABLE | Thrown messages are carried verbatim; error-code mapping is unchanged |
| filesystem access | NOT_APPLICABLE to the gate | the WP-13.2 gate's file bytes are WP-13.2's (`write`/`edit` contract) |
| platform path handling | NOT_APPLICABLE | none |
| external package / runtime versions | AUDITED | Node 22.15.1, typebox 1.3.7, diff 8.0.4, verified against the pinned lockfile (`process/authority-dependencies.md`); runner witness PASS/FAIL |

## 4. Concurrency / order matrix

NOT_APPLICABLE. This delta changes no operation, lock, await point or ordering. It widens the value a certified, unchanged pipeline carries. The certified `tool_execution_end`/message ordering (`TOOL-017`, Layer 08) is observed unchanged by the full-stack runner: one call per case, with `execution_end` and `message` each observed exactly once.

| Ordering guarantee | Realistic wrong implementation | Witness that kills it |
|---|---|---|
| hook, end event, message, log and replay all see the SAME values (no per-boundary re-encoding) | normalize at one seam only | the per-boundary negative controls (contract §5): hook-only, end-only, message-only, storage-only, history-replay-only, event-replay-only, each failing at its own boundary |

## 5. Neighborhood expansion record

| Family | Members probed | Pi observation source | New rows / findings |
|---|---|---|---|
| F7 value domains (TOOL RESULT row) | strings (16 sequences) × 6 positions; keys; numbers (9 tokens) × 3 positions; scalars; empty containers; `undefined` × 3 | `result_probe.mjs` (Pi `executeToolCalls` … `emitToolResultMessage`, `parseSessionEntries`) | keys and `NaN`/±Infinity folded (§6); `-0` a witness; ADJ-2 deferred; top-level `null` deferred with ADJ-2 (`R001` re-scope) |
| F6 object order | integer-like keys | same | K1 surface recorded for `#100` |
| replay boundaries (contract review 1) | falsy `details` (`0`, `-0`, `false`, `""`, `[]`) through event replay | Pi live `tool_execution_end` | `R001` (Python fix); witness: 5 cases fail on the old projection |

## 6. Verdict

```text
FEASIBILITY
    READY for the contract checkpoint: every row AUDITED / NOT_APPLICABLE / DEFERRED_WITH_REASON.
    Rust gaps (section 2) are additive, inside the authorized delta, and are the implementation work of
    L0506-D003's Rust phase -- not open contract findings. Deferred: ADJ-2 (Owner), K1 (#100),
    persistence-file and provider projections (future owning layers).
```
