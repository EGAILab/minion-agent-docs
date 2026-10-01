# L0506-D003: tool-result runtime value domain, characterization

**Work package:** `minion-agent#112`, opened by the Owner decision on `WP132-RUST-C002-Q001`, Option 1 (`minion-agent#49` comment `5937380474`).
**Finding:** `WP132-RUST-C002`, `CONTRACT_ASSURANCE_DEFECT` (Codex; `minion-agent#49` comment `5933146445`).
**Status:** characterization, by Claude as shared-contract owner. Not yet a contract.

## 1. Question

What values can pinned Pi (`b7bb00b936dbe21b8e160b3e89efdec361846699`) carry in a tool result? What does it do with them at each boundary? Can certified Python and Rust represent them?

The decision fixes the boundaries (§1, §7–§10). The probe below observes all of them:

```text
tool returns AgentToolResult {content, details}      (or throws)
  -> afterToolCall hook                             what it receives; what it may replace
  -> tool_execution_end                             event payload
  -> ToolResultMessage                              createToolResultMessage
  -> message_start / message_end
  -> session file line                              session-manager.ts:1021  `${JSON.stringify(entry)}\n`
  -> reload                                         session-manager.ts parseSessionEntries -> JSON.parse(line)
```

## 2. Evidence

All of it is under `assurance/layers/data/l0506-d003-characterization/`.

| Artifact | What |
|---|---|
| `harness/make_cases.py` → `cases.json` (sha256 `bfbc4e6d…`) | 145 cases plus the edit witness (§5), in the probe's tagged value form |
| `harness/result_probe.mjs`, `harness/run.sh` | pinned-Pi authority |
| `out/result.json` (sha256 `97fa2ae9af4582533914c6a7b0007eab3edb85ac6f141a0c50dda537ba0212df`) | 146 Pi results |
| `harness/py_probe.py` → `out/py.json` (sha256 `d7f6ff4d…`) | certified Python, main `e83ba6aa`, through its real seams |
| `harness/compare.py` | Python vs Pi, boundary by boundary |

**Authority.**
- **Runtime and dependencies:** Node v22.15.1. typebox 1.3.7 and diff 8.0.4 are each verified against pinned Pi's committed lockfile via `acquire_npm_pinned.sh` (`process/authority-dependencies.md`).
- **Pi sources:** the five Pi files are hash-pinned in `harness/pi_sources.sha256`. The pipeline is Pi's own `executeToolCalls` → `executeToolCallsSequential` → … → `emitToolResultMessage`, sliced from `agent-loop.ts` and run unmodified. The probe only supplies a custom tool and an `afterToolCall` hook.
- **Determinism:** `Date.now` is fixed to 0 because `createToolResultMessage` stamps a timestamp. No characterized value depends on it. Identity observations use `Object.is`, so a top-level `NaN` (never `===` itself) is not misreported as a different value.
- **Replays:** the output is byte-identical (`97fa2ae9…`) across two host-offline runs and one `node:22.15.1-alpine` container run with network acquisition.

**Case families:**
- **Strings:** 16 code-unit sequences: ASCII, BMP, a valid pair, lone high and low surrogates at start/middle/end, adjacent highs, low-then-high, pair+lone and lone+pair, empty, NUL, and U+FFFD as a control. Each appears as:
  - a details leaf;
  - an array element;
  - a nested-object value;
  - an **object key**;
  - the result **text**;
  - the whole top-level `details`.
- **Numbers:** 9 tokens: `0`, `-0`, `1.5`, `+Infinity`, `-Infinity`, `NaN`, max finite, min subnormal, 2^53. Each appears as a leaf, an array element, and top-level details.
- **Other scalars:** `null`, `true`, `false`, as a leaf and as top-level details. Plus undefined (top-level, nested, in an array), an empty object or array, and integer-like key order.
- **Hook and failure paths:**
  - after-hook modes: observe, return the same values, return `{details: null}`, replace details, replace text, replace with a non-finite number, throw;
  - a tool that throws.
- **Which cases have an after-hook:** every string, key and number case runs with an *observing* after-hook. So the hook boundary is observed across the whole domain, not only in the hook family (decision §7). The scalar-shape and failure cases keep the no-hook path.
- **Revision:** characterization revision 1 (`0369abf9`, output `febfc4fc…`) ran the domain families without a hook. Revision 2 adds the observing hook. The Pi observations at every other boundary are unchanged.

## 3. Pinned Pi: results

### 3.1 In memory: tool return → hook → `tool_execution_end` → ToolResultMessage

Every value is carried **unchanged** through all four in-memory boundaries, in every case:
- strings of any code units, as text, as details leaves at any depth, and as **object keys**;
- `-0`, `+Infinity`, `-Infinity`, `NaN`;
- `null`, booleans, and `undefined` (top-level, nested, in arrays).

Specifically:
- The event sequence is always `tool_execution_start, tool_execution_end, message_start, message_end`.
- The hook receives **the same object** the tool returned (`same_object_as_returned: true`).
- `message.details` **is** `tool_execution_end`'s `result.details`, the same object. `message_end` carries the same message object.
- **Hook replacement** (`finalizeExecutedToolCall`: `afterResult.details ?? result.details`, and likewise for content): a replacement holding lone surrogates, `-0`, `NaN` or `+Infinity` is carried through unchanged. `{details: null}` keeps the tool's own details (`??`), the existing TOOL-005 rule.
- **Failure conversion** (`createErrorToolResult(error.message)`): a thrown message holding a lone surrogate, from the tool or from the hook, becomes the result text with its code units unchanged, and `details: {}`, `isError: true`.
- The single in-memory "difference" is the `details-key-order` case: integer-like keys (`"2"`, `"1"`) enumerate first. That is ECMAScript's own object order (hazard family F6). It comes from constructing the object, not from any boundary. Its owner is K1, `L0206-D001` (`minion-agent#100`); see §6.

### 3.2 Session file and reload: a projection, not the runtime value

| Value | Persisted line (`JSON.stringify`) | Reloaded (`JSON.parse`) |
|---|---|---|
| string or key with a lone surrogate | `\ud800`-style escape (ASCII); a valid pair is written as UTF-8 | **identical code units** |
| `-0` | `0` | `0` |
| `+Infinity`, `-Infinity`, `NaN` | `null` | `null` |
| top-level `details: undefined` | key omitted | no `details` key |
| nested `{value: undefined}` | key omitted | key absent |
| `[undefined, …]` | `null` | `null` |

So for strings, Pi's persistence is an exact semantic round-trip (decision §10). For non-finite numbers, `-0` and `undefined`, Pi's own file projection is lossy.

## 4. Certified Python (main `e83ba6aa`)

`py_probe.py` drives the real seams:
- a registered `ToolDefinition`;
- `register_after_tool_call_hook` / `AfterToolCallOverride`;
- the `tools/execution-end` payload;
- `ToolResult.to_message()`;
- `SessionLog.append(EventKind.TOOL_RESULT, {"message": encode_message(message)})` and `decode_message` (the agent-loop driver's own append path).

`compare.py` against Pi:

- **Identical at the hook, `tool_execution_end` and ToolResultMessage for 141 of the 142 representable cases.** The one exception is `details-key-order` (K1, §6). The 141 cover every string, key, number (including `NaN`, ±Infinity and `-0`), top-level non-object details, `null`, and every hook and failure case.
- **Session replay** returns the value exactly as it was in memory. Python's Layer-03 log is not a byte form. This is the certified `MINION-002` / `spec/session.md` rule: "the log is not a byte serialization, so no JSON text projection applies to it". It matches Pi's in-memory value, not Pi's reloaded file (§3.2). The same mapping was certified for raw arguments under `L0206-D002`.
- **3 cases unrepresentable** (`details-top-undefined`, `details-nested-undefined`, `details-array-undefined`): Python has no `undefined`. See §6, ADJ-2.

Python therefore already conforms for the decision's string domain and for the numeric neighborhood, with no production change (decision §15). Contract certification will still require Python's canonical runner and negative controls (§16).

## 5. The discriminating WP-13.2 witness (decision §3)

`f.txt = "a\n"`, with the edits string `[{"oldText":"a","newText":"\ud800"}]`, through `prepareEditArguments` and `edit-diff.ts`. The result has `edit.ts:377-383`'s literal shape and goes through the same pipeline with an observing hook.

| Boundary | Value |
|---|---|
| filesystem UTF-8 projection | `efbfbd0a` |
| `details.diff` | `-1 a\n+1 ` followed by code unit **D800** |
| `details.patch` | `--- f.txt\n+++ f.txt\n@@ -1,1 +1,1 @@\n-a\n+` followed by **D800** and `\n` |
| hook / `tool_execution_end` / message | same code units |
| session line | `"diff":"-1 a\n+1 \ud800"`; reload restores D800 |

Runtime result value ≠ filesystem encoding, exactly as decision §3 requires.

## 6. Scope classification (decision §5–§6)

| Item | Reachable in Pi tool results | Preserved through the same boundaries | Same Rust representation failure | Classification |
|---|---|---|---|---|
| lone/paired surrogate strings in text and details, at any depth | yes (`edit`; error text with `path`; any tool) | yes; the file round-trips exactly | yes: Rust `String` / `serde_json::Value` (Codex C002) | **IN SCOPE** (decision §2–§4) |
| surrogate-bearing details **keys** | yes (custom tool, hook) | yes; the file round-trips exactly | yes: `serde_json` keys are `String` | **IN SCOPE**: folded under §6, also named in §5 |
| `+Infinity`, `-Infinity`, `NaN` in details | yes (custom tool; hook replacement) | yes in memory; Pi's file writes `null` | yes: `serde_json::Number` cannot hold them | **IN SCOPE**: folded under §6 |
| `-0` in details | yes | yes in memory; Pi's file writes `0` | to be verified by Rust review: `serde_json` keeps an `f64` `-0.0`, but no gate asserts it | **IN SCOPE as a required witness** (a negative control kills `-0 → 0`) |
| integer-like key order (`"2"`, `"1"` first) | yes | yes | ordering, not representation | **NOT folded**: hazard family F6 / K1. Recorded as an additional K1 surface for `L0206-D001` (`minion-agent#100`) |
| `undefined` (top-level, nested, array) | yes: Pi's `write` returns `details: undefined` | yes in memory; the file drops it or writes `null` | Python and Rust have no `undefined` | **NOT folded: ADJ-2** below |

**ADJ-2: absent, `undefined` and `null` details (flagged for the Owner, not folded).**
- Pinned Pi distinguishes three cases in memory:
  - `details: undefined`, which `write` returns;
  - `details: null`;
  - `details: {}`, which `createErrorToolResult` returns.
- The persisted file omits the key for the first.
- Certified Layer 06 (`spec/tools.md`, `IR-L06-004` / `CA-L06-007`) already decided this as a host API choice. A tool returning no details of its own may be defaulted by the host result type, and canonical evidence must not assert otherwise. WP-13.2's `write` spec records "`details` is Pi's `undefined`, projected as `{}`".
- Python's `write` returns `{}`. Top-level `null` and absent both read back as `None` (the encoder omits `None`).
- Changing that would reverse a certified host-API mapping. It is a different semantic question (presence, not representation), and a policy choice, so decision §6 does not authorize folding it. It is recorded here and raised separately.
- It does not block D003: no D003 rule depends on it.

**Out of scope** (decision §11–§12):
- **Provider-facing projection** of result text: a future-boundary obligation of the provider-owning layer (Layer 11).
- **Pi's file projection** (§3.2): Minion has no session file today. Following the `L0206-D002` precedent (`spec/llm.md`, "Projections are separate boundaries"), a future persisted form MUST reproduce Pi's projection there and only there:
  - strings escaped and exact;
  - `-0` → `0`;
  - non-finite → `null`;
  - `undefined` → omitted, or `null` in arrays.

## 7. Rust (feasibility only, not an oracle)

From Codex's C002 handoff: `AgentToolResult.details` is `serde_json::Value`, and the text content is a Rust `String`. Neither can hold an unpaired surrogate, a surrogate key or a non-finite number. The certified primitives that may be reusable (decision §14) are:
- `PreparedString` (L0506-D002);
- `RawValue` / `RawNumber` / `RawString` (L0206-D002), where note that `RawNumber` rejects `NaN`, which the result domain needs;
- `JsString` (`javascript.rs`).

The type design is Rust-owned.

## 8. Next

Contract draft for `L0506-D003`:
- a `spec/tools.md` Layer 05/06 section, with every boundary above and the projections kept separate;
- language-neutral canonical scenarios generated from this authority;
- a scenario schema;
- a Python canonical runner;
- the decision §16 negative controls, extended with NaN/±Infinity/key/`-0` mutants;
- manifest rows AI-006, TOOL-005, TOOL-017 and MINION-002.
