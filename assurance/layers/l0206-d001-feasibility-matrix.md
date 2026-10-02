# Cross-Language Feasibility Matrix — `L0206-D001` (K1): ECMAScript object key enumeration order

**Required by:** `process/agent-workflow.md` §4.1.1.
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699` (Node v22.15.1, typebox 1.3.7). **Author:** Claude. **Independent checkpoint reviewer:** Codex.
**Work package:** `minion-agent#100`. **Authorization:** Owner K1 decision, Option 1 (`minion-agent#99` comment `5924847773`).
**Characterization:** `l0206-d001-characterization.md` (evidence `data/l0206-raw-boundaries/`, `data/l0206-d001-k1/`).
**Candidate:** docs = this branch; code = none yet.

**Scope** (decision §1): ECMAScript own-property enumeration order of **tool-argument objects** across the raw, prepared, hook-visible and execute-visible boundaries, and every serialization or projection that exposes it.

**The rule under audit** (characterization §2), applied recursively to every object at every boundary:
1. array-index keys (canonical decimal `0 … 4294967294`) first, in ascending numeric order;
2. then every other string key, in insertion order.

A duplicate key keeps its first position and takes its last value.

## 1. Runtime value-domain matrix

The observable value throughout is **the key enumeration order of an argument object, and of every object nested in it**.

| Observable | Pi wire/source repr | Pi runtime repr | Python repr (today) | Rust repr (today) | Serialization | Lossless across all? | Risk / witness needed |
|---|---|---|---|---|---|---|---|
| raw `ToolCall.arguments` (L02/03): decode from provider text | JSON text | JS object, ES order (`JSON.parse` / `parseJsonWithRepair`) | `dict`, insertion order | `RawValue` object, `IndexMap` insertion order | — | **NO**: both bindings keep insertion order, so an index key inserted late differs | K1 itself: raw neighborhood cases (§5) |
| raw arguments built in code (mock adapter, tests, other constructors) | — | JS object literal: ES order | `dict` insertion | `IndexMap` insertion | — | **NO** | the same cases, through each binding's constructor |
| session persistence and replay | `JSON.stringify` → ES order text; replay `JSON.parse` → ES order | ES | in-memory `dict` (`session/log.py`), replayed as the same `dict`: insertion | serde (insertion order) | ES order text | **NO** (inherits raw) | the persist/replay boundary, observed after replay |
| `tool_execution_start` / `tools/update` event `args` | — | the raw object (ES) | `call.arguments` (insertion) | raw (insertion) | — | **NO** | event boundary cases |
| prepared arguments: `prepareArguments` shim (for example `edit`'s re-parse of `edits`) | — | the shim's own object, nested `JSON.parse` → ES | the shim's `dict`; `json.loads` → insertion | prepared value, `BTreeMap` (**sorted**) | — | **NO** (Python insertion, Rust sorted) | the `edit` nested case (characterization: `1, newText, oldText`) |
| validated arguments (`structuredClone` + `Value.Convert`) | — | a new object, the same ES order; no schema order; coercion does not reorder | raw-schema path: `dict(arguments)` (insertion); **pydantic path: `model_dump()`, the model's declared order** | `BTreeMap` (sorted) | — | **NO** (three different orders) | declared-schema cases `{z, a}`; the pydantic row is a §2 finding |
| hook-visible arguments (`beforeToolCall`) | — | the validated object itself (ES); a hook may **mutate** it (added keys follow ES order) | the validated `dict`; mutation appends (insertion) | `BTreeMap` | — | **NO** | the hook-mutation case (`{1,2,b}` + `c`, `"0"` → `0,1,2,b,c`) |
| hook **replacement** (Minion `Proceed(arguments=...)`) | — | NOT_APPLICABLE in Pi (`BeforeToolCallResult` has no `args`); Pi's equivalent is in-place mutation | the replacement `dict` (insertion) | replacement value (sorted) | — | a Minion mapping: the rule must still hold for the object `execute` receives | a replacement whose key order is non-ES |
| execute-visible arguments | — | the same object the hook saw (ES) | `decision.arguments` (insertion) | prepared value (sorted) | — | **NO** | every case, observed at `execute` |
| validation-failure diagnostic text | — | `JSON.stringify(arguments, null, 2)`: ES, recursive | `jsonschema` / pydantic message: not Pi's text | — | text | AUDITED as a separate surface (§2 row 6) | the diagnostic case: `{"1":3,"2":2,"b":1,"z":{"0":2,"q":1}}` |
| provider projection (outbound tool-call arguments) | `JSON.stringify(tc.arguments)` (openai-completions:1301, openai-responses-shared:286, mistral:833), or the object passed to the SDK (anthropic:1257, google-shared:208, bedrock:986) → ES | ES | no real provider yet (Layer 11); mock only | — | ES order text | DEFERRED_WITH_REASON: no binding provider serializes arguments yet; Layer 11 consumes this rule | stated in the contract as the rule for Layer 11 |

**Value classes checklist.** finite binary64, `+0`/`-0`, large integers, ±Infinity, NaN, `undefined`, `null`, `false`/empty, UTF-16, valid pairs, lone surrogates, Unicode normalization and numeric-looking strings are **NOT_APPLICABLE** to K1. K1 concerns key **order** only; key and value domains belong to `L0206-D002` and `L0506-D002`. The one overlap is **numeric-looking strings as keys**, which K1 owns (§5).

### 1.1 Value-domain carriers (F7)

| Carrier | Pi repr | Python repr | Rust repr | Owning seam | Lossless across all? |
|---|---|---|---|---|---|
| RAW INPUT VALUE DOMAIN | ES-ordered object | insertion `dict` | `IndexMap` insertion | Layer 02/03 | **NO** (K1) |
| PREPARED VALUE DOMAIN | ES-ordered object | insertion `dict`, or pydantic declared order | `BTreeMap` sorted | Layer 05/06 | **NO** (K1) |
| SCHEMA VALUE DOMAIN | declared property order: not imposed on the instance | — | — | Layer 05 | AUDITED: schema order is **not** an argument order (characterization `declared-z-a`) |
| TOOL RESULT VALUE DOMAIN | `details` objects: ES order (`L0506-D003` observation) | — | — | Layer 06 | DEFERRED_WITH_REASON: outside "tool-argument objects" (decision §1); a scope question at the contract (§6) |
| PERSISTENCE PROJECTION | `JSON.stringify` (ES) | in-memory `dict` | serde | Layer 03 | **NO** (inherits raw) |
| PROVIDER PROJECTION | `JSON.stringify` / SDK (ES) | none yet | none yet | Layer 11 | DEFERRED_WITH_REASON (Layer 11) |

## 2. Lower-layer capability matrix

| Required semantic operation | Owning lower layer | Existing certified seam | Exact Pi semantics? | Python repr sufficient? | Rust repr sufficient? | Additive extension? | Non-additive reopen? |
|---|---|---|---|---|---|---|---|
| 1. an ES-ordered object value (construction and recursive mutation) | Layer 02/03 value model | `dict` / `IndexMap` / `BTreeMap` | no | **NO**: `dict` orders by insertion, and a mutation appends | **NO** | **YES**: an ES-ordered object representation, or ES enumeration at every observation point (decision §4: the design is each binding's) | no: decision §9 authorizes targeted revalidation |
| 2. raw decode / construction producing ES order | Layer 02/03 | the raw constructors | no | NO | NO | part of 1 | no |
| 3. preparation shims (`edit`) re-parsing nested JSON | Layer 13 tool (`edit`), Layer 06 seam | `prepare_edit_arguments` (`json.loads`) | no | NO | NO | uses 1 | no (WP-13.2 owned outputs are proven order-independent: decision §6 witness) |
| 4. validation: no reordering (raw-schema path) | Layer 06 | `_validate`: `dict(arguments)` | yes, if the input is ES | yes, given 1 | **NO** (`BTreeMap`) | uses 1 | no |
| 5. validation: the **pydantic-model path** (Minion mapping) | Layer 05/06 | `model_validate` + `model_dump()` | **no**: declared order, defaults inserted | NO | n/a | **finding (K1-F1)**: decide the order delivered by a typed-model tool, keeping no intentional divergence (decision §8) | no |
| 6. hook mutation and replacement keep ES order at `execute` | Layer 06 | `Proceed(arguments=...)` | mutation: no; replacement: Minion mapping | NO | NO | uses 1 | no |
| 7. ES-order serialization (`JSON.stringify` order) | Layer 03 (persistence), Layer 11 (providers) | `json.dumps` follows `dict` order | yes, given 1 | yes, given 1 | serde follows the map | uses 1 | no |
| 8. validation-failure diagnostic text | Layer 06 | `invalid arguments: {error}` | not Pi's `JSON.stringify(args, null, 2)` text | — | — | **finding (K1-F2)**: is the diagnostic text Pi parity (already disclosed as a validator divergence)? Order is moot unless the text is parity | no |

## 3. Cross-runtime hazard checklist

| Hazard | State | Evidence / reason |
|---|---|---|
| `JSON.parse` (precision, duplicate keys, `__proto__`) | AUDITED | a duplicate keeps its first position with the last value; `__proto__` is an own key (raw probe) |
| `JSON.stringify` (key order) | AUDITED | ES order recursively (session text, diagnostic) |
| `Number` conversion | NOT_APPLICABLE | keys are strings; numeric-looking keys are a K1 neighborhood (§5), not conversion |
| `Math` semantics | NOT_APPLICABLE | none |
| negative zero | AUDITED | the key `"-0"` is not an array index |
| non-finite values | NOT_APPLICABLE | values are not reordered |
| `String.length` / UTF-16 | AUDITED | index recognition is on the canonical decimal string; non-ASCII keys are ordinary |
| `RegExp` | NOT_APPLICABLE | none |
| Unicode / ICU | NOT_APPLICABLE | no collation: ordinary keys keep insertion order, never sorted |
| Array ordering | NOT_APPLICABLE | array elements keep their order; only object keys are at issue |
| Object property ordering | AUDITED | the subject (characterization §2) |
| Promise scheduling | NOT_APPLICABLE | no async ordering |
| `AbortSignal` | NOT_APPLICABLE | none |
| timers | NOT_APPLICABLE | none |
| Node/libuv error mapping | NOT_APPLICABLE | none |
| filesystem access | NOT_APPLICABLE | none |
| platform paths | NOT_APPLICABLE | none |
| external package / runtime versions | AUDITED | Node v22.15.1; typebox 1.3.7, lockfile-verified (`acquire_npm_pinned.sh`) |

## 4. Concurrency / order matrix

NOT_APPLICABLE for async ordering. The material ordering guarantees are key-enumeration guarantees:

| Ordering guarantee | Realistic wrong implementation | Witness that kills it |
|---|---|---|
| index keys first, ascending | insertion order (Python today) | `mixed-index-first`: `{"b":1,"2":2,"1":3}` → `1,2,b` |
| other keys in insertion order | sorted order (Rust prepared today) | `{"z":1,"a":2}` → `z,a` |
| instance order, not schema order | declared-schema order (pydantic `model_dump`) | `declared-z-a` with input `a,z` → `a,z` |
| recursive | top-level-only reordering | nested `{"o":{"a":1,"2":2}}` → `o:{2,a}` |
| canonical index boundary | treating `"4294967295"`, `"01"` or `"-0"` as indices, or `"4294967294"` as not one | `index-boundaries`, `non-canonical-numerals` |
| ES order survives a hook mutation | ordering applied once at decode only | the hook adds `"0"` → `0` first at `execute` |
| ES order survives persistence and replay | ordering at decode, insertion after replay | the persist/replay boundary |

## 5. Neighborhood expansion record

| Family | Members probed | Source | Rows / findings |
|---|---|---|---|
| F6 `ECMASCRIPT_OBJECT_ORDER` | insertion only; index keys only; mixed; reverse insertion; `0`, `00`, `01`, `1`, `2`, `10`, `4294967294`, `4294967295`, `-0`, `-1`, `1.0`, `+1`; large numeric-looking strings; nested objects; duplicate key; hook-added keys; schema-declared order; coercion; `edit` nested; diagnostic | `data/l0206-raw-boundaries/` (raw, persist/replay, events, hook, execute) and `data/l0206-d001-k1/` (validation, mutation, nested, `edit`, diagnostic) | one rule at every boundary; findings K1-F1 and K1-F2 |
| F6 question set (`hazard-families.md`) | 1. order matters: yes (hooks, `execute`, serialization). 2. serialization exposes it: yes. 3. bindings preserve it: no. 4. index-like keys possible: yes. 5. nested affected: yes | — | — |

## 6. Verdict

```text
FEASIBILITY
    NOT YET READY for the contract checkpoint. Two rows need a decision first:

    K1-F1  the pydantic-model validation path (a Minion mapping) delivers the model's DECLARED
           order and inserts defaults. Proposed: deliver the instance's ES order (the model's
           values, keyed as the validated input enumerates, with any defaulted key appended in
           ES position), so a typed-model tool observes Pi's order. Contract-level (no Owner
           decision) unless it is judged an intentional divergence.
    K1-F2  the validation-failure diagnostic text. Pi's text is JSON.stringify(args, null, 2);
           Minion's is the validator's message (the disclosed L06 validator divergence). Proposed:
           NOT_APPLICABLE for K1 (the text itself is not parity), recorded with that reason.

    Scope note: tool-result details key order (L0506-D003 observation) is outside the decision's
    "tool-argument objects". Treated as out of scope unless the Owner extends K1.

    Every other row is AUDITED, NOT_APPLICABLE or DEFERRED_WITH_REASON (provider projection:
    Layer 11 consumes the rule). The binding gap (row 1 of section 2) is the delta's own subject:
    additive, authorized by decision section 9.
```
