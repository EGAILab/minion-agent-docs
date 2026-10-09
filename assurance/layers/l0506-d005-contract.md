# L0506-D005: validated-argument isolation (structured clone)

Layer 06 post-certification delta. Coordination: minion-agent#190. Finding provenance: minion-agent#129 (`L06-VALIDATION-SHALLOW-COPY`). Requirement: `TOOL-003`. Normative text: `spec/tools.md`, "Validated-argument isolation".

**Governance.** The Owner decision on #129 is recorded verbatim there (sha256 `8f175020…eb446`). It chose Option 1, "deep-copy like pinned Pi", as a narrowly scoped, contract-first Layer 06 correction:
- the validation pipeline works on an independent structured clone of the prepared arguments;
- hooks and `execute` cannot reach the raw `ToolCall.arguments` through retained nested aliases;
- aliases, cycles, key order and the prepared runtime values survive;
- there is no JSON round trip, no per-hook re-cloning, no reopening of K1, TypeBox coercion or the pydantic mappings, and no widening at the `prepare_arguments` boundary;
- witnesses A–J, plus controls that restore shallow copying, are required.

## 1. Pinned Pi authority (`b7bb00b936dbe21b8e160b3e89efdec361846699`)

| Symbol | What it does |
|---|---|
| `ai/src/utils/validation.ts` `validateToolArguments` (317–320) | `const args = structuredClone(toolCall.arguments)`, then `Value.Convert` and the check; returns `args` |
| `agent/src/agent-loop.ts` `prepareToolCallArguments` (586–598) | `tool.prepareArguments(toolCall.arguments)`: the shim receives the **raw object itself** |
| `agent-loop.ts` `prepareToolCall` (600–668) | `validatedArgs` goes to `beforeToolCall({args})` and is returned as `prepared.args`; the returned `toolCall` is the **original** call |
| `agent-loop.ts` `executePreparedToolCall` (673–700) | `execute(…, prepared.args, …)`; `tool_execution_update.args = prepared.toolCall.arguments` (raw) |

## 2. Characterization (`data/l0506-d005/`)

**Harness.** `harness/run.sh` runs in Docker `node:22.15.1-alpine`, with Pi mounted read-only and fixtures on tmpfs.
- It slices pinned Pi's `agent-loop.ts` and `validation.ts` unmodified onto the K1 staging. Sources are checked against `l0206-d001-k1/harness/pi_sources.sha256`, and typebox 1.3.7 is verified against the pinned lock (sha512).
- `harness/pi_isolation.mjs` is the free-form characterization (`out/pi-isolation.json`).
- `gen/pi_oracle.mjs` is the canonical oracle (`out/pi-oracle.json`).
- `harness/py_isolation.py` runs the same ten characterization cases through Minion's real `execute_call` (`out/py-isolation-raw.json` and `out/py-isolation-pydantic.json`; Python 3.13.5 at `main` `50186ab6`).

**Results.** `≠` marks a difference from pinned Pi.

| Case | Pi | Python raw-schema | Python pydantic |
|---|---|---|---|
| hook sets into a nested object | raw unchanged; update raw; execute sees change | **≠** raw and update show the change | = |
| hook pushes an object into a nested array | same | **≠** | = |
| nested object gains an index key | same | **≠** | = |
| nested replace, delete and push | same | **≠** | = |
| shim alias `{p: x, q: x}` | `p === q` in the clone; not the shim's object | = | **≠** split (`model_dump`) |
| shim self-cycle | `self === args` | **≠** top-level split: `self` is the shim's object | **≠** recursion error (cannot validate) |
| `-0`, lone surrogates, NaN/±Infinity via shim | survive | = | = |
| validation failure | immediate error; raw unchanged | = | = |
| blocked after a nested mutation | raw unchanged | **≠** raw changed | = |
| shim mutates raw (`raw.o.shim = 1; raw.t = 2`) | raw shows both | top level `t` **not** shown (§6 nonmutation mapping); nested shown | same as raw-schema |

**Identity facts (Pi).**
- The hook's `args` is never the raw object, nor any raw child.
- The hook's `toolCall.arguments` *is* the raw object, so raw-listener access is unchanged.
- `execute` receives the hook's object.

**Classification:**
- **Raw-schema path:** `PI_PARITY_DEFECT`. It is the nested leak, plus the top-level cycle split, which the same shallow copy causes. Corrected by this delta.
- **Pydantic path:**
  - isolation: **AUDITED — NO CHANGE**;
  - alias split and cycle failure: recorded properties of the certified pydantic mapping (`model_dump` re-serializes), outside this delta (Owner scope 10).
- **`prepare_arguments` boundary:** recorded characterization only. Pi gives the shim the raw object; Minion gives it a fresh top-level `dict` (the certified design-spec §6 mapping). Not changed (Owner: "do not silently widen").

## 3. Contract

`spec/tools.md` "Validated-argument isolation" is normative. It covers:
- the two graphs;
- rules 1–5 (clone point; isolation; one logical graph; structure and values survive; unchanged surfaces);
- the K1 interaction;
- the binding audit table and the adjacent boundary.

`spec/llm.md` R007 gains a correction note. R4-C001's aliasing stands; its identity-with-raw reading is superseded for observers.

**K1 evidence consequences (implementation stage; disclosed now).**
- `tests/tools/test_key_order_container_provenance.py::test_a_reference_crossing_the_frontier_stays_one_object` asserts `kept`: the hook's container *is* the raw child. Under rule 2 that becomes `False`, while `equal` (one container) and `through_old` stay. The assertion is updated accordingly.
- `test_control_ordering_the_shim_graph_without_adopting_fails_the_prepare_witness` mutates `adopt` at the prepare boundary. Once observers receive the clone's `JsObject`/`JsArray`, that mutant is equivalent at every observer (it survived on the planned-fix overlay).
  - It is re-pointed at the point that now carries R007's seams: a clone producing plain containers.
  - `adopt` itself stays: it is the certified prepare-boundary provenance and is harmless.
  - The R007 *witnesses* pass unchanged.

## 4. Canonical evidence

`conformance/agent/arg-isolation/` holds 14 documents (`arg-isolation-scenario.schema.json`). They are generated by `gen/gen_canonical.py` from `gen/cases.json` and the pinned-Pi oracle.
- **Language-neutral fixtures:** raw JSON text, named shims (`alias`, `cycle`, `non-finite`, `reuse-raw-child`), path-based listener programs (`set`, `push`, `delete`), identity facts (`same`, `distinct_from_raw`) and `block`.
- **Observed:** outcome, each listener's entry, facts, `execute`, the `tools/update` payloads and the final raw arguments.
- **Runner:** `tests/conformance/arg_isolation_runner.py` builds one call and registers one `tools/pre-execute` listener per program over the real `execute_call`. It never copies or orders anything itself.

**Contract-stage Python** (unchanged code):
- 10 cases are `xfail(strict=True)`: every nested-leak case, the cycle case, the reused-raw-child case and the two-listener case.
- 4 pass: top-level set, shim alias, shim non-finite values, validation failure. With the completeness test, 5 pytest passes.

**Schema tests:** well-formedness, all 14 documents validating, and 8 malformed shapes rejected. One found and fixed a too-permissive `execute` branch, which accepted a non-object.

## 5. Contract-stage discrimination (`data/l0506-d005/controls.py`)

**Recipe:**
1. Copy the candidate's `minion-agent-python/`, `conformance/` and manifest to an E: scratch directory.
2. Apply `gen/planned_fix.py` there, and change nothing else.
3. Run `python controls.py <python> <copy>/minion-agent-python <logs>`.

The script runs with `--runxfail` and a cleared `PYTEST_ADDOPTS`. The baseline must select every intended witness and see it pass. A kill requires exactly the intended witnesses to fail, at a canonical assertion.

**Fresh results** (Windows, Python 3.13.5): baseline **5 intended witnesses selected and PASS**, and **4/4 KILLED**:

| Control | Mutant | Killed by |
|---|---|---|
| `shallow-copy-restored` | Owner's required control: `JsObject(arguments)` again | nested set; nested push |
| `clone-forgets-aliases` | a non-root container reached twice gets a fresh copy | shim alias |
| `clone-keeps-pipeline-containers` | `JsObject`/`JsArray` reached through the graph are kept, not copied | reused raw child; nested set |
| `clone-per-listener` | each listener gets a new clone | two listeners |

On the unchanged candidate, the baseline is **INVALID** (4 intended witnesses not green), so no kill can be reported against the defective binding.

**Planned fix on the overlay, full Python suite:** every test passes except the two K1 consequences in §3, plus one load-sensitive `bash` pipe-release test. That bash test passes alone, three runs out of three, and it is unrelated.

## 6. Python implementation plan (after contract approval)

- **New function** `llm/js_object.py::structured_clone`:
  - iterative and identity-memoized;
  - produces `JsObject`/`JsArray`, ordered;
  - carries non-container values as they are.
- **`tools/execute.py::_validate`, raw-schema path:**
  - `validated = structured_clone(arguments)`, then validated against the schema;
  - replaces `order_in_place(JsObject(arguments))`.
- **Pydantic path:** unchanged.
- **K1 test updates** as in §3.
- **Binding witnesses:**
  - the same validated object reaches every listener and `execute` (F);
  - a pydantic-path nested-mutation isolation witness (audit evidence).
- **Regression:** K1, `L0206-D002` raw-arguments, the `L0506-D001` and `D002` prepared-runtime corpora, and the full suite.

## 7. Rust (Rust owner, after contract approval)

`tools/execution.rs` preflight calls `params.structured_clone()` after prepare, and hooks and `execute` share the result. `PreparedValue::structured_clone` (`tools/prepared.rs`) memoizes by container identity. A read-only audit suggests the binding is conformant.

The Rust owner is required to:
- confirm conformance through the canonical corpus and permanent witnesses (Owner scope 3);
- run Rust-side controls, including restored shallow copying;
- change production code only if the corpus shows non-conformance.
