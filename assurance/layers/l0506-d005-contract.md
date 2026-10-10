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

## 8. Contract review 1, Owner decision L0506D005-Q001 and remediation 1

**Review 1** (Codex; #190 issuecomment-6090443463; verdict sha256 `66bca062cabc73b506b9e22e785ab544ec3cee8af2fff5150d08f81be8d3c41a`).
It reviewed code `2bc2dd7c` and docs `9ed90e56`. Verdict: **CHANGES REQUESTED**.
- **`L0506D005-C001`** (medium, `CONTRACT_ASSURANCE_DEFECT`): the §4.1.1 Cross-Language Feasibility Matrix was missing.
- **`L0506D005-C002`** (high, `PI_PARITY_DEFECT`): the Rust cycle reaches a validation projection that is not graph-aware.
  - Rust's clone keeps the self-cycle, but preflight's `validate_runtime_schema` calls `value.try_to_json()` (`tools/prepared_validation.rs:370`), which has no cycle guard.
  - Pi's reachable open-schema cycle case therefore overflows the stack (Codex's probe through the real `execute_tool_calls`).
  - The §7 suggestion that Rust conforms was premature.
- **`L0506D005-C003`** (medium, `CONTRACT_ASSURANCE_DEFECT`): the runner's numbers were not `JSON.parse` binary64 / `Number::toString`. There were three pinned-Pi neighbours:
  - raw `9007199254740993`;
  - inserted `1000000000000000100`;
  - inserted `1e+300`.

**Owner decision `L0506D005-Q001`** (#190 issuecomment-6091246259, sha256 `3fa425f2d9d645e9f5305b4220c51ac22d5ca705403493a009e439d78ef056b3`): **defer cyclic validation**.
- This delta's certified domain is **acyclic** prepared graphs, and aliases stay in scope.
- No Rust validation change is authorized.
- The Pi cycle evidence is kept as characterization-only.
- The uncovered surface is recorded as a separate out-of-scope finding: **#193**, with reproduction, versions, scope, consequence, alternatives and triggers.

**Remediation 1:**
- **C001.** New `l0506-d005-feasibility-matrix.md`, from the process template. Every row is `AUDITED`, `NOT_APPLICABLE` or `DEFERRED_WITH_REASON`, and the verdict is READY for the acyclic domain. It distinguishes the clone **capability** (cycles kept in both bindings) from the validation **capability** (Rust is not cycle-safe; DEFERRED_WITH_REASON under `L0506D005-Q001` / #193).
- **C002, under the Owner decision:**
  - `prepared-cycle-survives-clone` is marked `characterization_only` in `gen/cases.json`. The oracle still runs it and `out/pi-oracle.json` keeps its pinned-Pi observation, but the generator no longer emits it into the certifying corpus.
  - The spec's rule 4 now states the acyclic certified domain and #193.
  - Codex's Rust probe is preserved in `data/l0506-d005/rust-cycle-probe/` as #193's reproduction. It builds against the candidate's Rust crate with the repository's pinned ICU flags.
  - No claim is made that the Rust pipeline supports cyclic prepared arguments.
- **C003:**
  - The runner now constructs numbers with the certified binary64 decoder (`raw_arguments_runner.number`, also used by `parse_raw`'s `parse_int`/`parse_float`) and observes them with the certified prepared-runtime token (`prepared_runtime_runner.render`). An integer that is not binary64 observes as the strict `{non_binary64_int}` marker and can never match a token.
  - Infinity is now spelled `+Infinity`, as that authority does. The oracle, schema pattern and corpus were regenerated to match.
  - Three new pinned-Pi cases: `raw-integer-beyond-2p53-is-binary64`, `hook-inserts-integer-spelled-by-number-tostring`, `hook-inserts-exponent-spelled-number`.
  - New runner number tests (`test_arg_isolation_runner_numbers.py`).
  - New control `json-round-trip-clone`, the design the Owner forbids.
- **Corpus:** 16 certifying documents. At the contract stage there are 12 strict xfails and 4 passes.
- **Controls on the planned-fix overlay:** baseline 5 intended witnesses PASS, **5/5 KILLED** (`shallow-copy-restored`, `clone-forgets-aliases`, `clone-keeps-pipeline-containers`, `json-round-trip-clone`, `clone-per-listener`).
- **§7 Rust plan, corrected:** confirm the acyclic corpus through the real preflight and Rust controls. No Rust validation change is authorized. The cyclic validation surface is #193's, not this delta's.
