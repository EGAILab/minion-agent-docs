# L0206-D001 (K1): ECMAScript object key enumeration order — characterization

**Work package:** `minion-agent#100` (SCOPING). **Authorization:** Owner K1 decision, Option 1 (`minion-agent#99` comment `5924847773`).
**Author:** Claude. This is characterization, not a contract.
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`, Node v22.15.1, typebox 1.3.7 (lockfile-verified).

## 1. Evidence

| Source | Covers |
|---|---|
| `assurance/layers/data/l0206-raw-boundaries/` (`out/raw.json` `a1713f0a…`; record `l0206-d002-characterization.md`, "Observations for L0206-D001") | raw decode (`parseJsonWithRepair` / `JSON.parse`), session persist (`JSON.stringify`) and replay, the update event, and hook and `execute` with an **open** schema, over the decision §2 key neighborhood |
| `assurance/layers/data/l0206-d001-k1/` (`harness/k1_probe.mjs`, `run.sh`; `out/k1.json` `7d3d0e42…`) | this pass: **declared-property schemas** (typebox `Value.Convert`), validation's `structuredClone`, a hook that **mutates** the argument object, nested objects, `edit`'s nested `edits` re-parsed from a string, and the validation-failure **diagnostic** |

The new probe runs Pi's own `validateToolArguments`, `prepareToolCall`/`executePreparedToolCall` and `prepareEditArguments`, sliced unmodified and pinned by `pi_sources.sha256`.

## 2. Pinned Pi's rule

At every boundary observed, the order is **ECMAScript's `OrdinaryOwnPropertyKeys`**, recursively:
1. **array-index keys first, ascending.** An array index is the canonical decimal string of an integer `0 … 4294967294`: `4294967294` is an index, while `4294967295`, `"-0"`, `"-1"`, `"00"` and `"01"` are not;
2. **then every other string key, in insertion order.**

Further facts:
- A duplicate key keeps its **first** position with the **last** value.
- `__proto__` is an ordinary own property (raw probe).

| Boundary | Observation |
|---|---|
| raw decode | ES order |
| session persist / replay | `JSON.stringify` emits ES order; replay is ES order |
| update event, hook, `execute` (open schema) | ES order (the same object) |
| validation (`structuredClone` + `Value.Convert`) | **a new object, the same ES order.** A declared-property schema does **not** impose schema order: `{z, a}` declared, input `a, z` stays `a, z`. Coercion (`"5"` → `5`) does not reorder |
| hook mutation (keys added by the hook) | the rule applies to the mutated object: adding `c` and `"0"` to `{1, 2, b}` gives `0, 1, 2, b, c` at `execute` |
| nested objects (declared or not) | the same rule, recursively |
| `edit` preparation (`JSON.parse` of the `edits` string) | nested objects in ES order: `1, newText, oldText` |
| validation-failure diagnostic (`JSON.stringify(arguments, null, 2)`) | ES order, recursively: `{"1":3,"2":2,"b":1,"z":{"0":2,"q":1}}` |

**Conclusion.** No Pi boundary orders keys by anything other than the ECMAScript rule applied to the object's construction and mutation history. There is no schema order, no sorting, and no canonicalization.

## 3. Minion today

- **Python:** `dict` insertion order at every seam. It differs from Pi whenever an index-like key is not inserted first (the raw probe's `mixed-index-first`, `index-boundaries`, `non-canonical-numerals` and `nested` cases), and for hook-added index keys.
- **Rust:** the raw `RawValue` object is insertion-ordered (`IndexMap`). The prepared and result representations use sorted maps (`BTreeMap`). Both differ from Pi.

## 4. WP-13.2 relationship (decision §6)

The focused independence witness exists on both sides:
- **Python:** `tests/tools/builtin/test_wp132_key_order_independence.py`.
- **Rust:** WP-13.2's K1 witness, four distinct raw enumerations plus an order-leak control (Codex, `13-wp132-rust-d003-integration.md`).

WP-13.2 is CERTIFIED_CLOSED with K1 recorded as outside its owned surface.

## 5. Related surface recorded for scope

`L0506-D003` recorded that tool-result `details` key order follows the same ECMAScript rule in Pi and is not asserted by D003. Its carrier, the tool result rather than tool arguments, is outside this decision's stated scope ("tool-argument objects"). Inclusion is a scope question for the contract stage.

## 6. Next

- The feasibility matrix with the F6 `ECMASCRIPT_OBJECT_ORDER` family (decision §11).
- The contract:
  - the ES order rule at the raw, prepared, hook, hook-replacement, `execute` and serialization boundaries;
  - an ES-order object representation per binding (decision §4);
  - canonical cases over the §2/§10 neighborhood;
  - negative controls: insertion order, sorted order, schema order, and the rule applied only at the top level.
