# L08-D002 — Request header per provider request (Layer 08 delta)

**Status:** contract APPROVED and merged (section 7, then #172 → `d461f812`, #266 → `0834a937`).
Python: CERTIFIED (#181 -> `3de4b75d`, #271 -> `52945167`; review #171 issuecomment-6073237153).
Header presence and timing were pre-existing; the R003 schema value snapshot was not.
Rust: IMPLEMENTATION CANDIDATE, independent closure review pending (section 9).

> Sections 2 to 6 are the first contract candidate as reviewed. Where they say Python "conforms",
> read it as header presence, count and timing only. Contract review 1 found the schema-snapshot gap
> (`L08D002-R003`), which section 8 corrects.

**Coordination:** `minion-agent#171`.

**Governance:** Owner decision on `L08D001-RUST-C001`, Option 1, recorded verbatim at
`minion-agent#166` issuecomment-6068630928. It authorizes a targeted correction to certified
Layer 08 in both bindings, including the observable change to the session event log.

**Normative text:** `spec/agent.md`, Layer 08, "Request header per provider request". Manifest row
`AG-025`.

## 1. Origin

- **The finding.** Codex's Rust `L08-D001` checkpoint found `L08D001-RUST-C001`: the certified Rust
  driver never calls `Session::record_header`. A real run sends a provider request and records no
  `request/header` event.
- **The executed witness:** `l08d001_baseline_header_gap_characterization`, on draft code `#169` @
  `d8c1658b`, record `assurance/layers/08-l08-d001-rust-blocker.md` on draft docs `#264`.
- **Why it matters:** `L08-D001`'s contract had assumed header recording was existing behaviour in
  both bindings.
- **The cause:** no certified spec required the driver to record a header. Python's driver did; the
  Rust driver did not.

## 2. Characterization

### Python

- **How it was run:** `data/08-l08-d002/probe_python.py`, through the real `AgentLoop`, Session log,
  artifact store and mock provider, at code main `db63adcf`. Output: `data/08-l08-d002/python.json`.
- **Order inside a request build:** TURN_START (or the run's first turn) → the entering messages are
  admitted → system text (override, else `L08-D001` assembler, else the stored prompt) → tool
  schemas → **`record_header`** → `transformContext` → `llm.stream`.

| Scenario | Requests sent | Headers | Observation |
|---|---|---|---|
| single request | 1 | 1 | `user, header, assistant` |
| tool call (two requests) | 2 | 2 | a header per request, after its entering messages |
| provider error stop | 1 | 1 | header kept |
| `transformContext` raises (first request) | 0 | **1** | header published, then the failure; the run settles failed |
| `transformContext` raises (second request) | 1 | 2 | the first request and header intact; the second header without a request |
| assembler raises (`L08-D001`) | 0 | 0 | the failure happens before publication |
| pre-step `Reject` | 0 | 0 | no request is built |
| per-step override | 1 | 1 | the header records the override literally |
| unknown model | 0 | **1** | header published; the eager `UnknownModelError` propagates (certified behaviour) |
| abort during a tool | 2 | 2 | one header per request built |

**Not every failure before the provider send means zero headers.** The `transformContext` and
unknown-model failures happen after publication and keep the header. The Owner asked for exactly
this to be characterized (item 5). The contract codifies Python's existing timing rather than
changing it, so no Python behaviour changes.

### Rust

Inspected read-only at code main `db63adcf` (`minion-agent-rust/crates/minion-agent/src/agent_loop/driver.rs`,
`run_provider_turn_with_decision`):
- **Order:** `transform_context` runs first, then the request is built with fallible schema
  computation, then `llm.stream(request)?`.
- **Headers:** there is no `record_header` call anywhere outside Session tests.
- **What already exists:** `Session::record_header(components, model, tools)` has the Layer 03
  shape. Rust can therefore conform using only existing APIs, by placing the call after schema
  computation and before `transform_context`.

## 3. Contract decisions

All of these follow from the characterization. Each is within the Owner's scope.

| Item | Rule | Why |
|---|---|---|
| Header content | `{system_base: system text}`, `ModelId.model`, the request's schemas | Python's existing content; the Layer 03 format, unchanged |
| Publication point | after entering messages and the final system, model and schemas; before `transformContext` and the provider | Python's existing timing (item 4: preserve Python) |
| Failure before the point | no header (assembler, schema computation, `Reject`) | matches Python and `L08-D001` |
| Failure after the point | header kept (`transformContext`, unknown model, provider error or abort) | matches Python; one header per build |
| Duplicates | exactly one per request build | no retry path inside a build |
| Log-only | `request/header` is never surface data | Layer 03 classification, unchanged |
| History | historical logs are untouched | Owner item 6 |
| `L08-D001` | its no-assembler guarantee is relative to the corrected baseline; AG-024 unchanged | Owner "L08-D001 relationship" |

## 4. Evidence

**Canonical cases** (`conformance/agent/request-header-*.yaml`, 7 documents). Two keys are added to
`agent-scenario.schema.json`:
- `expect_request_log`: surface messages interleaved with headers;
- `expect_headers`: the reconstructed system text, component names, model and tool names.

Two additive listener kinds are added to the vocabulary: `agent/pre-step` with `system_override`,
and `agent/transform-context` with `raise` plus `on_request`. The cases are:

| Case | Covers |
|---|---|
| `single-request` | the basic header |
| `one-per-request-in-order` | multi-request order and tool snapshot |
| `provider-error-keeps-the-header` | a provider failure after publication |
| `unknown-model-recorded-before-eager-failure` | eager failure after publication; `expect_error` |
| `records-the-literal-override` | the per-step override |
| `transform-failure-first-request` | first-turn failure after publication |
| `transform-failure-later-request` | later-turn failure; earlier records intact |

**Python runner:** `tests/conformance/agent_runner.py` observes the log and headers through the real
Session; it adds no behaviour. All 7 pass with the **unchanged** Python driver.

**Kill controls** (`data/08-l08-d002/controls.py`, disposable copy of the Python driver). All 5 are
valid kills, exit 0:

| Mutant | Killed by |
|---|---|
| Header after `transformContext` | exactly the two transform-failure cases (this pins the timing) |
| No header | all 7 |
| Duplicate header | all 7 |
| Stored prompt instead of the override | the override case |
| Provider-qualified model | all 7 |

**Gates (code PR head):**

| Platform | Result |
|---|---|
| Windows, pinned ICU | **5,332 passed, 48 skipped, 21 xfailed**; coverage **100%**; ruff and mypy clean |
| Linux | **5,285 passed, 0 failed, 97 skipped, 19 xfailed** |

## 5. Implementation scope after approval

- **Python:** none beyond the runner support already here. Its witnesses are these canonical
  cases.
- **Rust:**
  - the driver calls `Session::record_header` at the defined point;
  - the Rust agent-loop conformance runner gains `expect_request_log`, `expect_headers` and the two
    listener kinds;
  - the regressions the Owner requires: projection, fork, compaction and the certified Layer 08
    suites.
- **Serialization:** the Rust `L08-D001` branch (`#169`) must not change the same driver code
  concurrently. Integrate `L08-D002` first, then rebase `L08-D001` (Owner).

## 6. Requested review

An independent contract-delta review covering:
1. the publication point and its failure split, against the Python characterization;
2. whether the canonical observable (surface messages interleaved with headers, plus reconstructed
   headers) is language-neutral and sufficient;
3. Rust feasibility with the existing `Session::record_header`, including the fallible schema
   computation coming before publication;
4. the `L08-D001` dependency clarification.

## 7. Contract review 1, Owner decisions and remediation 1

**Review.** Codex, independent contract review 1, at code #172 @ `9190f305` / docs #266 @ `267128e3`. Recorded
verbatim at minion-agent#171 issuecomment-6070941439. Verdict CHANGES REQUESTED, with three findings, all
`CONTRACT_ASSURANCE_DEFECT`, all high. Accepted as written: the timing split, component and model spelling, the
log-only classification, historical logs, and the `L08-D001` note. Rust is feasible through its existing Session.

- **`L08D002-R001`.** Headers were observed by tool **names** only. A header-only corruption control passed all 7
  cases: a wrong description, with `parameters: {type: null}`.
- **`L08D002-R002`.** Certified Python `reconstruct_tools` drops `constrained_sampling`: the field is stored but
  not reconstructed.
- **`L08D002-R003`.** Python's derived schema shares the application's `parameters` mapping. A `transformContext`
  listener mutating it makes the provider request differ from the stored header.

**Owner decisions**, recorded verbatim at #171 issuecomment-6071887505:
- **R002, Option 1.** A separate Layer 03 delta, `L03-D001` (#174). It must be merged and certified before this
  delta claims complete request-schema reconstruction. After that, these witnesses compare full schemas,
  `constrained_sampling` included.
- **R003, Option 1: snapshot at publication.**
  - Per request, an independent value snapshot of every model-facing schema field is recorded in the header and
    passed to the provider.
  - A shallow copy is not enough.
  - Later mutation changes neither that request's header nor its provider-visible schemas, though a later request
    may see it.
  - The run-start shallow snapshot and the Layer 05/07/03, assembler and failure semantics stay unchanged.
  - The narrow Python driver correction lands inside this delta, after the revised contract is reviewed.

**Remediation 1, contract:**
- **Spec** (`spec/agent.md`):
  - the `tools` row now names the schema value snapshot;
  - a new **Schema value snapshot** rule, the Owner's items 1–9;
  - the bindings paragraph covers Python's needed correction and Rust's owned values;
  - a dependency paragraph for `L03-D001`;
  - canonical evidence: complete schemas in both `expect_headers` and the new `expect_request_schemas`.
- **Canonical:**
  - `expect_headers.tools` is now the complete reconstructed schemas: name, description, parameters and any
    `constrained_sampling`, with absent sampling omitted (the `L05-R006` input form);
  - new `expect_request_schemas` gives the complete schemas each provider request carried, observed at the
    provider boundary;
  - the agent `toolStub` gains `description` and `constrained_sampling`;
  - the 7 cases are regenerated with complete schemas;
  - new `request-header-full-schema-identity`: two ordered tools with distinct descriptions, nested parameters,
    a `json_schema` require config and a `grammar` config with both formats.
- **Python runner:** it builds the real tool with its description and sampling, and reports each schema's own
  `as_json()`, from the reconstructed header and from the adapter's received request. It derives nothing.
- **R003 witness** (Python binding; Rust holds no application-shared mutable alias, so it cannot express one):
  - `tests/agent_loop/test_request_schema_snapshot.py`;
  - (a) **two tools:** the stored header equals what each request sent, with complete schemas in order;
  - (b) **transform-time mutation:** a real `transformContext` listener changes a nested value and appends to a
    nested list of the application's own mapping after the first publication. The first header and the first
    request both keep the pre-mutation values and the sampling metadata. The second request sees the change, and
    its header matches it;
  - (b) is `xfail(strict=True)` until the driver correction lands.
  - Checked against the unchanged driver: (b) fails, because the first request carries the mutated schema. With a
    value-copying capture, tried in place and reverted, both pass.
  - The header is read from the stored artifact bytes, so these witnesses do not depend on `L03-D001`.
- **Controls** (`data/08-l08-d002/controls.py`):
  - **Three mutants added:** header-only schema corruption (Codex's R001 control), header drops
    `constrained_sampling`, and request tools reordered.
  - **Validity gates**, carrying over the `L03D001-R001` lesson: the request-header cases must all pass
    unmutated (positive baseline), and each mutant has a declared set of intended cases. KILLED needs pytest exit
    1, no ERROR or XPASS, and every intended case among the failures. Otherwise the result is INVALID.
  - **Fresh run on this rebased candidate** (`L03-D001` is now merged, so no overlay is needed): baseline green,
    and **8/8 KILLED**.
    - The corruption control is killed by `full-schema-identity`, `one-per-request-in-order` and
      `transform-failure-later-request`.
    - The sampling and reorder controls are killed by `full-schema-identity`.
  - An R003 "no value snapshot" control, killed by witness (b), is added with the driver correction.
- **Dependency met.** `L03-D001` Python is merged and certified: code #178 → `9b91dad8`, docs #270 → `09c8c499`,
  minion-agent#174. So `full-schema-identity` passes on this candidate. `L03-D001`'s Rust closure, a test-only
  count change, is tracked in #174.

## 8. Contract approval, merge and Python implementation

**Contract.** Codex's contract re-review 1 APPROVED code #172 @ `1ef1f093` / docs #266 @ `8bbe052e`. Recorded
verbatim at #171 issuecomment-6073014973. R001 and R003 are closed at the contract stage, and R002 through
`L03-D001`, which is closed (#174). Both PRs were merged by guarded exact-head squash merges, in the Owner's order
of contract, review, then merge: #172 → `d461f812`, #266 → `0834a937`.

**Editorial note from that review.** Older summaries said Python "already conforms". This record now qualifies
them: the status header, the note above section 2, AG-025's rule and Python field, and the spec's
observable-changes list. Python's header presence and timing were pre-existing. Its schema value snapshot was
not.

**Python correction**, the narrow Layer 08 driver change the Owner authorized:
- `agent_loop/driver.py` gains `_schema_snapshot(schema)`, which is `replace(schema, parameters=copy.deepcopy(...))`.
- `name`, `description` and `constrained_sampling` are immutable values already; the nested `parameters` mapping
  is the only possible alias of application state.
- Each request build computes one snapshot tuple. The header records it, and the provider request carries that
  same tuple.
- Unchanged: the run-start shallow `RunContext.tools` snapshot, `ToolDefinition`, registry membership and
  identity, Layer 07 state, the artifact format, assembler semantics, and the failure and lifecycle rules.

**Witnesses** (`tests/agent_loop/test_request_schema_snapshot.py`; the strict xfail is removed):
- the full-schema identity of header and request, two ordered tools with sampling metadata (G, F);
- the transform-time mutation witness (A–E).
  - The first header and request keep the pre-mutation nested value and list.
  - The second request takes its own snapshot and sees the change.
  - Its header matches it.

**Controls** (`data/08-l08-d002/controls.py`):
- one implementation-stage mutant is added, **"no value snapshot"**, restoring the aliasing derivation;
- its intended witness is the mutation witness;
- the witness module is now selected alongside the request-header cases (`-k "request-header or
  request_schema_snapshot"`).

**A survivor caught by the baseline.** The first run of the new control *survived*. The `-k request-header` filter
had deselected the snapshot witness entirely, so the mutant never met its witness. That was a selection mistake,
not a weak witness. The baseline gate now also requires every mutant's intended case to appear among the PASSED
nodes, using `-rA`. A copy of the script with the old filter reproduces the mistake, and the baseline refuses it:
`INVALID baseline: ... intended witnesses not selected: [test_a_transform_time_mutation_...]`.

**Fresh run on the implementation candidate:** baseline `10 passed; every intended witness selected and green`,
then **9/9 KILLED**:
- the 8 contract-stage mutants;
- `no value snapshot`, killed by `test_a_transform_time_mutation_reaches_neither_the_published_header_nor_its_request`.

Fresh gate counts are in the implementation PR and the coordination issue. Rust L08-D002 remains NOT_IMPLEMENTED,
and cross-language L08-D002 is NOT CLOSED.

## 9. Rust implementation candidate

Section 8's Rust disposition is the historical Python handoff. The Rust delta
now captures one owned ordered schema vector, publishes through the existing
Session header operation before transformation, and sends the same schema
snapshot to the provider. Its real agent-loop adapter drives all eight shared
request-header documents and observes complete headers and request schemas.
Additional binding witnesses and intended-witness negative controls are recorded
in `08-l08-d002-rust-implementation.md`, with the fresh G3 gates and recipe.

The exact paired remote heads are recorded on #171. Rust remains NOT CERTIFIED;
cross-language L08-D002 is NOT CLOSED. Next owner is Claude for independent
exact-SHA Rust closure review. The L08-D001 #169 driver work is not changed by
this candidate and remains sequenced after this delta's certification.
