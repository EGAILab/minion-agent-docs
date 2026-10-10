# Cross-Language Feasibility Matrix — `L0506-D005`: validated tool arguments are a structured clone

**Required by:** `process/agent-workflow.md` §4.1.1 (`L0506D005-C001`, contract review 1).
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`. **Author:** Claude (shared-contract owner). **Independent checkpoint reviewer:** Codex.
**Candidate:** contract remediation 1 on code #191 / docs #278. Exact SHAs are on #190.
**Scope:** the Owner decision on #129, clarified by `L0506D005-Q001` (#190 issuecomment-6091246259). The certified domain is **acyclic** prepared argument graphs, and aliases within them are in scope. Cyclic graphs passing through validation are out of scope (finding #193).

**Transitive path audited** (pinned Pi):

```text
provider JSON.parse
  -> raw toolCall.arguments
  -> prepareArguments(raw)
  -> validateToolArguments: structuredClone, normalizeOptionalNulls, Value.Convert, (coerce), Check
  -> beforeToolCall({args})
  -> execute(args)
tool_execution_start/update/end carry the raw arguments; persistence carries JSON.stringify(raw).
```

Sources: `agent-loop.ts` `prepareToolCallArguments` / `prepareToolCall` / `executePreparedToolCall` and `validation.ts` `validateToolArguments` (pin table `l0206-d001-k1/harness/pi_sources.sha256`); the characterization in `data/l0506-d005/`.

---

## 1. Runtime value-domain matrix

The clone carries every leaf **by value, unchanged**. Containers are copied once each.

| Observable value / field | Pi wire/source repr | Pi runtime repr | Python repr | Rust repr | Canonical/wire serialization | Lossless across all? | Risk / witness needed |
|---|---|---|---|---|---|---|---|
| object (identity, key order) | JSON object | own keys in ECMAScript order (K1) | `JsObject` (ordered; K1 seams) | `ArgumentObjectRef` (ordered, identity) | `{o:[[k,v]…]}` | YES | Canonical: index-key reorder, nested set, nested gains index |
| array (identity, order) | JSON array | Array | `JsArray` | `ArgumentArray` | `{a:[…]}` | YES | Canonical: nested push, nested replace/delete |
| finite binary64, including a large integer past 2^53 | JSON number | Number | int (an exact binary64 integer) / float | prepared number variant | `{n: Number::toString}` | YES | Canonical: `raw-integer-beyond-2p53-is-binary64`, `hook-inserts-integer-spelled-by-number-tostring`, `hook-inserts-exponent-spelled-number`, `1e300`; runner number tests (C003) |
| `-0` | `-0` | -0 | `-0.0` | -0 | `{n:"-0"}` | YES | Canonical: `nested-runtime-values-survive-the-clone`, `prepared-non-finite-values-survive-clone` |
| ±Infinity, NaN (prepared only) | — (shim) | Number | float | prepared number variant (`L0506-D001`) | `{n:"+Infinity"/"-Infinity"/"NaN"}` | YES | Canonical: `prepared-non-finite-values-survive-clone` |
| string, including lone surrogates | JSON string (`\ud800` escapes) | UTF-16 string | `str` (surrogatepass) | `PreparedString` (UTF-16) | `{u:[units]}` | YES | Canonical: both values cases (`D800`, `DC00`) |
| `null` / `true` / `false` | JSON | null / boolean | None / bool | prepared scalar | literal | YES | Carried by value; the fixture includes none. No clone-specific risk |
| `undefined` / missing key | — | absent key | absent key | absent key | absent | NOT_APPLICABLE | The clone copies own keys only, and absence is unaffected |
| alias (one container reached twice), **acyclic** | — (shim only; JSON has none) | one object | one container (memo) | one container (memo) | `same` fact | YES | Canonical: `prepared-alias-stays-shared-in-clone`; control `clone-forgets-aliases`; `json-round-trip-clone` killed |
| container shared between raw and prepared (shim reuses a raw child) | raw child | the clone's own copy | the clone's own copy (after the fix) | the clone's own copy | `distinct_from_raw` fact | YES | Canonical: `prepared-reused-raw-child-is-isolated`; control `clone-keeps-pipeline-containers` |
| **cycle** in the prepared graph | — (shim only) | cycle preserved by `structuredClone`, and `Check` passes on an open schema | clone preserves it (unit witness); raw-schema validation handles the open-schema case | clone preserves it; **certified validation is not cycle-safe** (stack overflow) | `{cycle:k}` | **DEFERRED_WITH_REASON** | Outside the certified (acyclic) domain, per Owner `L0506D005-Q001`. Kept as characterization-only Pi evidence (`gen/cases.json` `prepared-cycle-survives-clone`). Finding #193 holds the reproduction and the reconsideration triggers. Not a Pi divergence, and the stack overflow is not accepted behaviour |

Members of the JS-number family not listed above are covered or excluded in §3.

### 1.1 Value-domain carriers

| Carrier | Pi repr | Python repr | Rust repr | Owning seam | Lossless across all? |
|---|---|---|---|---|---|
| RAW INPUT (`L0206-D002`) | `JSON.parse` value | `JsObject`/`JsArray` graph (adopted at construction) | `serde_json::Value` + raw argument graph | Layer 02/05 construction | YES. **Unchanged by this delta.** The raw object is never cloned, frozen or reserialized |
| PREPARED (`L0506-D001`/`D002`) | runtime graph | dict/list graph (shim output, adopted) | `PreparedValue` | Layer 05 `prepare_arguments` | YES for acyclic graphs. The cycle row is DEFERRED_WITH_REASON (#193) |
| **VALIDATED** (this delta) | `structuredClone(prepared)` | `structured_clone(prepared)`: new `JsObject`/`JsArray`, memoized | `PreparedValue::structured_clone()` (identity memo) | Layer 06 `_validate` / preflight | YES, acyclic. The clone **capability** supports cycles in both bindings; validation **capability** does not in Rust (#193) |
| SCHEMA (`L05-D001`) | TSchema | dict / pydantic model | `ToolSchema` | Layer 05 | NOT_APPLICABLE. Schemas are not cloned or changed |
| TOOL RESULT (`L0506-D003`) | result | `ToolResult` | `AgentToolResult` | Layer 06 | NOT_APPLICABLE. This delta does not touch results |
| PERSISTENCE (session log) | `JSON.stringify(raw)` | raw encoding (K1, D002) | raw encoding | Layer 03 | NOT_APPLICABLE. It carries the raw graph, which this delta leaves unchanged; the update/raw immutability witness covers it |
| PROVIDER PROJECTION | raw | raw | raw | Layer 02 | NOT_APPLICABLE. Same reason |

**The Owner's six questions, for the VALIDATED carrier:**
1. **What Pi produces:** the clone of the prepared graph. Every container is fresh, aliases and cycles are kept, and leaves are unchanged.
2. **Python:** yes. `structured_clone` is iterative, so it is not bounded by stack depth (a 100,000-deep witness).
3. **Rust:** yes for the clone. Rust validation of a cyclic graph is the deferred row (#193).
4. **What hooks and events see:**
   - hooks and `execute` see the clone, the same object across listeners;
   - the start, update and end events see the raw graph (Pi `prepared.toolCall` is the original call).
5. **Serialization:** none. The validated graph is never serialized; only the raw graph is.
6. **Lossy projection allowed:** nowhere. A JSON round trip is forbidden by the Owner (control `json-round-trip-clone`).

**Canonical-case audit:** every canonical case schema is either the open object schema or `{required:["missing"]}`. No schema value lies outside the scalar/JSON domain, so the SCHEMA row is NOT_APPLICABLE.

## 2. Lower-layer capability matrix

| Required semantic operation | Owning lower layer | Existing certified seam/API | Expresses exact Pi semantics? | Python repr sufficient? | Rust repr sufficient? | New additive extension required? | Non-additive reopen required? |
|---|---|---|---|---|---|---|---|
| Structured clone of the prepared graph | Layer 06 (this delta) / K1 graph types | Python: none (new `js_object.structured_clone`). Rust: `PreparedValue::structured_clone` | YES (identity memo; leaves by value; order kept) | YES | YES (audited; Codex's acyclic probe reaches `execute`) | Python: the new function, inside this delta | NO |
| Validation of the cloned graph (acyclic) | Layer 05/06 validation | Python `PreparedArgumentsValidator` (jsonschema); Rust `validate_runtime_schema` | YES within the certified mappings (TypeBox coercion is a disclosed divergence, unchanged) | YES | YES (it projects to JSON; acyclic graphs only) | NO | NO |
| Validation of a **cyclic** cloned graph | Layer 05/06 validation | the same | Pi validates it (open schema) | handles the open-schema case | **NO** (stack overflow) | — | **DEFERRED_WITH_REASON.** Owner `L0506D005-Q001` declined to widen this delta into graph-aware validation. Finding #193 records the alternatives and triggers |
| One graph through the listener waterfall and `execute` | Layer 06 waterfall | `TOOLS_PRE_EXECUTE` waterfall, `Proceed(arguments)` | YES (Minion's listener chain is a mapping of Pi's single `beforeToolCall`, labeled in the spec) | YES | YES (shared graph handles; Codex review 1) | NO | NO |
| The raw object still reachable by raw listeners and updates | Layer 06 events | `call.arguments` / `toolCall.arguments` | YES | YES | YES | NO | NO |
| Shim boundary (Pi gives the shim the raw object) | Layer 05 prepare | design-spec §6 nonmutation mapping (fresh top-level dict) | NO, a certified mapping (characterized) | — | — | NO | NOT_APPLICABLE. Unchanged by Owner direction ("do not silently widen") |

## 3. Cross-runtime hazard checklist

| Hazard | State | Evidence / reason |
|---|---|---|
| `JSON.parse` (number precision, duplicate keys, `__proto__`) | AUDITED | Precision: the binary64 decoding cases and runner tests (C003). Duplicate keys and `__proto__` are raw-construction behaviour (`L0206-D002`), unchanged here; the clone copies own keys as given |
| `JSON.stringify` (non-finite → null, -0 → 0, undefined, key order) | AUDITED | The validated graph is never stringified. A JSON round-trip clone is forbidden, and its control is killed |
| `Number` conversion / numeric coercion | NOT_APPLICABLE | The clone carries numbers by value. Validation coercion dispositions are unchanged (Owner scope 10) |
| `Math` semantics | NOT_APPLICABLE | No arithmetic on the path |
| negative zero | AUDITED | Canonical values cases |
| non-finite values | AUDITED | `prepared-non-finite-values-survive-clone` |
| `String.length` / UTF-16 code units | AUDITED | Lone-surrogate canonical cases. Strings are carried by value |
| `RegExp` | NOT_APPLICABLE | None on the path |
| Unicode / ICU version | NOT_APPLICABLE | No normalization, case mapping or collation on the path |
| Array ordering | AUDITED | Arrays are copied element by element in order (nested push / replace cases) |
| Object property ordering (integer-like keys first) | AUDITED | `hook-reorders-nested-by-index-key`; K1 suites as regression |
| Promise scheduling | NOT_APPLICABLE | The clone is synchronous at validation; waterfall ordering is unchanged |
| `AbortSignal` | AUDITED | Ordering is unchanged. Abort after the waterfall still wins over Proceed or Block (§ per-call pipeline), and the clone happens before it |
| `setTimeout` / timers | NOT_APPLICABLE | None |
| Node/libuv error mapping | NOT_APPLICABLE | No filesystem or OS calls |
| filesystem access semantics | NOT_APPLICABLE | None |
| platform-specific path handling | NOT_APPLICABLE | None. The corpus is identical across platforms |
| external package / runtime versions | AUDITED | Node v22.15.1; typebox 1.3.7 verified against the pinned lock SRI; Pi sources against the K1 pin table |
| **cyclic graph through validation** (added) | DEFERRED_WITH_REASON | Owner `L0506D005-Q001`; finding #193 |

## 4. Concurrency / order matrix

| Operation | Start | Registration point | Lock acquisition | Await points | Abort checkpoints | Failure points | Settle point | Cleanup / release | Observable completion ordering |
|---|---|---|---|---|---|---|---|---|---|
| preflight (prepare → clone → validate → waterfall) | `tools/execution-start` emitted | — | — | each listener; `on_execution_start` | after the waterfall (existing) | prepare throw, validation error, listener throw/Block | `_Prepared` or immediate result | — | unchanged: the clone is synchronous inside validation, between prepare and the first listener |

| Ordering guarantee | Realistic wrong implementation | Witness that kills it |
|---|---|---|
| Clone once, before the first listener; one graph thereafter | clone again per listener | `two-hooks-share-the-validated-graph` (control `clone-per-listener`); binding identity witness |
| Clone of the *prepared* value, not the raw | clone the raw arguments, losing the shim's result | `prepared-alias-stays-shared-in-clone`, `prepared-non-finite-values-survive-clone` (the shim output appears) |
| Validation sees the clone | validate the prepared graph, then clone | not observable: validation does not mutate. A pydantic default-fill is exercised by the existing TOOL-003 tests |
| Raw updates carry the original | emit validated args on `tools/update` | every executed canonical case's `updates` equals the raw text's value after the hook's mutation |

## 5. Neighborhood expansion record

| Family | Members probed | Pi observation source | New rows / findings |
|---|---|---|---|
| JS Number | finite, 2^53 boundary, large integer spelling, exponent spelling, -0, ±Infinity, NaN | `gen/pi_oracle.mjs` (17 cases) | Three canonical cases from contract review 1 (C003) |
| JS String/UTF-16 | lone high, lone low, mixed | the same | none |
| ECMAScript object order | index key inserted into a nested object | the same | none |
| Schema runtime domain | open schema; `required` failure | the same | none |
| (graph identity) | alias, cycle, reused raw child | the same, plus Codex's Rust probe | cycle → #193 (DEFERRED_WITH_REASON) |

## 6. Verdict

```text
FEASIBILITY
    READY  -- every row AUDITED / NOT_APPLICABLE / DEFERRED_WITH_REASON within the Owner-scoped acyclic domain.
              The one gap (Rust cyclic validation) is DEFERRED_WITH_REASON by Owner decision L0506D005-Q001,
              tracked as finding #193. No open finding blocks the acyclic contract.
```
