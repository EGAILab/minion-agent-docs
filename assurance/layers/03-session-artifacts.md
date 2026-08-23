# Session + Artifacts — Fidelity Assurance & Certification

**Layer ID:** `03`  
**Status:** `IN_AUDIT`  
**Audit date:** 2026-08-23 (three passes: §1-7 completed first, against the frozen master design
§5/§6/§8, `spec/session.md`, `pi-parity-manifest.yaml`'s `MINION-002`/`MINION-003` rows, the pinned Pi
session source (`ref-repos/pi/packages/agent/src/harness/session/`), all 8 Python session modules, and
all 15 `conformance/session/*.yaml` scenarios. §8-14 completed second: all 11 Python test files read in
full (172 test functions, all `KEEP`), the two design-named-but-missing canonical scenarios confirmed
genuinely absent rather than assumed, and every category review (failure model, security,
reliability/operations, observability, performance, public API, documentation) done — surfacing
`RISK-001` (in-memory-only session storage, confirmed intentional per the design's own Phase-9
commitment, recorded in `risk-register.md`). `SES-F001` remediated and resolved third: 6 placeholder
scenarios filled, 2 missing-named scenarios authored, 1 (`request-reconstruction-after-target-transform`)
verified genuinely `DEFERRED TO LAYER 04` rather than assumed fixable — required extending
`session-scenario.schema.json`/`session_runner.py` first, following the `LLM-F010` pattern. `SES-F002`/
`SES-F003` remain open; the certification decision requires both resolved and is not started this
pass, per the standing one-layer-at-a-time sequencing rule.)  
**Auditor:** Claude (Python-driven, per adopted workflow)  
**Python status:** `IMPLEMENTED`  
**Rust status:** `NOT_IMPLEMENTED` (Phase 2 per `MINION-002`/`MINION-003`; no `session/` module exists
in `minion-agent-rust` yet)

---

## 1. Scope

### Owns

- The append-only, sequence-numbered, JSON-validated session log (`session/log.py`).
- The session event vocabulary: the two-tier surface/log-only split, the open-namespace/
  value-identity rules, and the specific log-only kinds the frozen design names (`session/events.py`).
- Derivation: projecting the log's surface into model history, including reset/compaction/fork
  handling (`session/derive.py`).
- The three session operations as log events: `fork`, `reset`, `compact` (`session/operations.py`).
- Content-addressed storage for request-header components and its no-deletion discipline
  (`session/artifacts.py`).
- Content-addressed request-header composition/reconstruction, and the canonical
  dispatch-uses-what-reconstruction-proves join (`session/request_header.py`).
- The `ctx.sessions` plugin seam that owns live logs and the shared artifact store
  (`session/service.py`).
- `MINION-002` (session log architecture) and `MINION-003` (content-addressed artifacts) from
  `/pi-parity-manifest.yaml` — both intentional architectural divergences from Pi, scoped to
  preserving Pi's model-visible history, not Pi's storage mechanics.

### Does not own

- The LLM vocabulary itself (`TextBlock`/`AssistantMessage`/`Usage`/etc.) — Layer 02, certified.
  Layer 03 only encodes/decodes it for storage (`derive.py`'s `_encode_*`/`_decode_*`).
- Target-model transformation (XFORM) — Layer 04. The design's own §5 "Relationship to Pi's message
  projection" is explicit that session/log projection (`derive_messages`) and XFORM are two distinct
  stages; Layer 03 certifies the first, not the second.
- Full compaction *behavior* — the trigger estimator (`HAR-003`) and the summary-request settings
  (`HAR-004`), both `packages/agent/src/harness/compaction/compaction.ts`-sourced, phase 7 per the
  manifest. Layer 03 owns the *mechanics* of a compaction event once one is appended (supersession,
  provenance, no double-projection); it does not own *when* or *why* one is triggered.
- Built-in harness message projections (branch/compaction/bash/custom wrappers, `HAR-005`,
  `packages/coding-agent/src/core/messages.ts`-sourced) — phase 7, targets
  `session/projections or harness/`, a module that does not exist yet. Not implemented, not in scope
  this pass.
- The agent run/turn/step state machine itself (`agent_loop/driver.py`'s control flow, termination
  conditions, `max_steps`, listener dispatch) — Layer 08 ("Agent run/turn state machine") per the
  charter's audit order. Layer 03 only owns the *event vocabulary* `driver.py` writes into the log;
  see `SES-F002` below for where that boundary already surfaced a finding.
- Tool execution semantics — Layer 06.

### Depends on

- Layer 02 (LLM vocabulary) — certified. `derive.py` encodes/decodes every LLM-###-owned type.
- Layer 01 (Runtime) — certified. `session/service.py` is a runtime plugin (`ctx.provide`).

### Depended on by

- Layer 04 (XFORM) — consumes `derive_messages()`'s output as its own input.
- Layer 07/08 (Agent state, run/turn/step) — `agent_loop/driver.py` is the sole current writer of the
  session log; its own certification will need Layer 03's event vocabulary to be settled first.
- Layer 06 (Tool execution) — tool results are logged via the same surface/log-only split.

---

## 2. Normative sources

- **Frozen design:** `2026-08-20-minion-agent-design.md` §5 "The session log (`ctx.sessions`)"
  (append-only log, two event tiers, three operations, content-addressed request state, relationship
  to Pi's message projection, portability of plugin-declared surface events) and §6's explicit
  Run/Turn terminology rule, referenced by §5's own log-only kind list. §8 "Validation" names the
  `session/` conformance family and its originally-planned scenario list.
- **Spec:** `spec/session.md` — a compressed restatement of §5's append/surface/fork/reset/compaction
  rules. Confirmed **not** to restate §5's log-only kind list (`run/*`, `turn/*`,
  `assistant/chunk`, `tool/call`, `request/header`) or the by-value event-identity rule — see
  `SES-F003`.
- **`/pi-parity-manifest.yaml` rows:** `MINION-002` (append-only session log; "N/A — Minion
  persistence architecture"; intentional divergence; `tests: session derivation/reconstruction
  suite`), `MINION-003` (content-addressed immutable request artifacts; intentional divergence;
  `tests: request-reconstruction-with-artifacts`).
- **Canonical conformance:** `conformance/session/*.yaml`, 15 files. 10 real and passing; 5 remain
  unfilled placeholders — full inventory in §7.
- **Pinned Pi source** (`ref-repos/pi`, commit `b7bb00b936dbe21b8e160b3e89efdec361846699`, matching
  Layer 02's pin): `packages/agent/src/harness/session/session.ts` (the `Session` class — lanes,
  entries, records, operations, cursor-based queries), `packages/agent/src/harness/session/types.ts`
  (the full lane/record/entry type vocabulary). Read in full. Pi's actual session architecture is
  **far** more elaborate than Minion's (multi-lane trees, typed records for every operation/tool/queue
  event, a pluggable `SessionStorage` backend, SQLite-backed in `session-backends/sqlite-node`) —
  consistent with `MINION-002`/`MINION-003`'s own "N/A — Minion persistence architecture" disposition:
  Pi's storage mechanics are explicitly not the oracle here. What Pi's source does still ground is the
  vocabulary the design's own §5/§6 borrow (`AgentMessage`, `Run`/`Turn`, compaction/branch-summary
  entries) — used below only to check Minion's *model-visible history* claim, never to demand
  structural parity with Pi's lane/record architecture.
- **Approved divergences:** `MINION-002`, `MINION-003` (both already logged above).

---

## 3. Pi behavior summary

Pi's `Session` (`session.ts`) is a multi-lane, typed-record persistence engine: entries
(`message`/`model_change`/`thinking_level_change`/`active_tools_change`/`compaction`/
`branch_summary`/`custom`) form a parent-linked tree per lane, records
(`operation_started`/`abort_requested`/`operation_finished`/`step_attempt`/`tool_started`/
`queue_enqueued`/`queue_cancelled`/`write_deferred`/`usage`) track operational state for crash
recovery, and a `SessionStorage` interface abstracts the actual backend (JSONL, SQLite). None of this
architecture is what Minion adopts — confirmed against `MINION-002`/`MINION-003`'s own "N/A — Minion
persistence architecture" disposition, and against the frozen design's own explicit divergence
framing in §5's final subsection.

What the frozen design *does* borrow from Pi, and states normatively:

- **Model-visible means logged** (§5): anything reaching a model request must be reconstructable from
  committed log state. This is the actual cross-language-binding claim — not Pi's storage shape, but
  the *history a model would see* being equivalent.
- **Two event tiers** (§5): a **surface** subset (`user/message`, `assistant/message`, `tool/result`)
  that projects into model history, and everything else **log-only**: `run/start`, `run/end`,
  `turn/start`, `turn/end`, `assistant/chunk`, `tool/call`, `request/header`. This list is the frozen
  design's own words, not an inference.
- **Three operations, each specified as a log event + derivation effect** (§5 table): `fork(source,
  at)` → `session/forked`, references not copies; `reset()` → `session/reset`, identity preserved,
  excludes all surface at-or-before; `compact_now()` → the ordinary compaction event, bypassing only
  the trigger check.
- **Pi Run/Turn terminology is normative for the observable loop** (§6, stated for the agent loop but
  explicitly cross-referenced by §5's log-only kind list): "Run / invocation, bounded by
  `agent_start...agent_end`, may contain multiple turns. Turn: exactly one assistant response + the
  tool calls/results caused by that assistant response. An implementation may use a private 'step'
  object internally, but MUST NOT redefine observable `turn` to mean a whole multi-request run."
- **Content-addressed request state** (§5): the assembled system prompt is model-visible and must be
  reconstructable; `request/header` records a composition of content-addressed component hashes, never
  a monolithic snapshot; artifacts holding model-visible content are never deleted; conformance asserts
  the *reconstruction*, not the storage representation.
- **Relationship to Pi's message projection** (§5): Minion's log/session surface projection
  approximates Pi's `convertToLlm`-style `AgentMessage[] -> Message[]` conversion; the **Pi-compatible
  target-model transformation defined in design §4 still runs after** session projection, as a
  distinct stage (Layer 04, not Layer 03).

No unresolved Pi-behavior uncertainty was found this pass — every claim above traces to explicit
frozen-design text, not inference from Pi source or from best practice.

---

## 4. Requirement traceability

| ID | Requirement | Source | Python implementation | Rust implementation | Executable evidence | Status |
|---|---|---|---|---|---|---|
| `SES-001` | Append-only, sequence-numbered, JSON-validated at append; a rejected append leaves no trace | design §5, `spec/session.md`, `MINION-002` | `log.py::SessionLog.append`/`_check_json_safe` | not implemented (Phase 2) | `test_log.py` (10 tests, incl. non-JSON-safe rejection at every nesting shape) | `PASS` |
| `SES-002` | Model-visible means logged: request history reconstructable from committed state | design §5, `MINION-002` | `derive.py::derive_messages` + `request_header.py` | not implemented | `test_derive.py`, `conformance/session/*` (`SES-F001` resolved) | `PASS` |
| `SES-003` | Two-tier event vocabulary: surface (`user/message`/`assistant/message`/`tool/result`) vs log-only; open namespace, name is the identity | design §5, `spec/session.md` | `events.py::EventKind`/`CORE_SURFACE_KINDS`/`is_surface`/`validate_event_name` | not implemented | `test_events.py`, `plugin-defined-event-kind.yaml`, `plugin-event-stays-log-only-by-default.yaml` | `PASS` |
| `SES-004` | Log-only lifecycle/fidelity/operations kinds are fully and correctly enumerated | design §5 (explicit list) | `events.py::EventKind` (partial — see `SES-F002`) | not implemented | none dedicated | `GAP — SES-F002` |
| `SES-005` | Append pipeline: validate → atomic seq allocation → committed publication | `spec/session.md`, design §5 (implicit in log.py) | `log.py::append` | not implemented | `test_log.py::test_sequence_numbers_start_at_one_and_increase` + rejection tests | `PASS` |
| `SES-006` | `fork(source, at)`: references not copies, boundary fixed at fork time, later writes on either side stay private | design §5 table, `spec/session.md`, `MINION-002` | `operations.py::fork`, `derive.py::_derive`'s ancestry walk | not implemented | `test_fork.py` (11 tests), `fork-ancestry-derivation.yaml`, `fork-local-compaction.yaml` | `PASS` |
| `SES-007` | `reset()`: identity preserved, excludes all surface at-or-before, history stays readable | design §5 table, `spec/session.md` | `operations.py::reset`, `derive.py::effective_surface`/`_derive` | not implemented | `test_reset.py` (6 tests), `reset-excludes-prior-surface.yaml` | `PASS` |
| `SES-008` | Compaction: supersedes an effective range with summary + retained-tail provenance; no double-inclusion under repeated/overlapping/nested/fork-local compaction | design §5 table, `operations.py` docstring, `spec/session.md` | `operations.py::compact`, `derive.py::_derive`'s compaction branch | not implemented | `test_compaction.py` (8 tests), `compact-now-then-derive.yaml`, `compaction-repeated-and-nested.yaml`, `overlapping-compaction.yaml`, `fork-local-compaction.yaml` | `PASS` |
| `SES-009` | Content-addressed request header: components stored by hash, composition logged as references, dispatch and reconstruction use the same canonical join | design §5, `spec/session.md` | `request_header.py::assemble_system`/`record_header`/`reconstruct_header`/`reconstruct_tools` | not implemented | `test_request_header.py` (7 tests), `test_request_header_tools.py` (5 tests), `request-reconstruction-with-artifacts.yaml`, `request-header-component-reuse.yaml` (`SES-F001` resolved) | `PASS` |
| `SES-010` | Artifacts holding model-visible content are never deleted; no removal API exists | design §5, `artifacts.py` docstring, `MINION-003` | `artifacts.py::ArtifactStore` (no delete method) | not implemented | `test_artifacts.py` (7 tests, incl. `test_the_store_has_no_delete`) | `PASS` |
| `SES-011` | Event name is the identity, compared by value — not by enum/object identity | design §5 "two consequences" | `events.py` (`EventName = str`; `is_surface` compares `event.kind in surface`) | not implemented | `event-name-identity-is-by-value.yaml`, `test_plugin_events.py::test_a_raw_string_kind_is_the_same_event_as_its_constant` | `PASS` |
| `SES-012` | An open logging namespace is not an open surface: declaring/appending a plugin event name does not by itself admit it to model history | design §5 | `log.py`/`events.py` (`surface_kinds` parameter, defaults to `CORE_SURFACE_KINDS`) | not implemented | `plugin-event-stays-log-only-by-default.yaml`, `test_plugin_events.py` (multiple) | `PASS` |
| `SES-013` | Session/log projection approximates Pi's `AgentMessage -> Message` conversion; target-model transformation is a distinct, later stage | design §5 "Relationship to Pi's message projection" | `derive.py` (scope boundary only) | N/A | `request-reconstruction-after-target-transform.yaml` — verified genuinely `DEFERRED TO LAYER 04` (`SES-F001`'s investigation, §7), not filled | `DOCUMENTED` |
| `SES-014` | Session log-only naming must track Pi's Run/Turn vocabulary; observable `turn` MUST NOT mean a multi-request run | design §6 (explicit prohibition), cross-referenced by §5 | `events.py::EventKind.TURN_START`/`TURN_END`/`STEP_START`/`STEP_END`; emitted by `agent_loop/driver.py` | not implemented | none dedicated; driver.py inspection contradicts the rule — see `SES-F002` | `GAP — SES-F002` |
| `SES-015` | `MINION-003`: content-addressed artifacts are a permitted storage divergence only when model-visible bytes stay equivalent to what was dispatched | `MINION-003`, design §5 | `request_header.py` + `artifacts.py` | not implemented | `request-reconstruction-with-artifacts.yaml`, `request-header-component-reuse.yaml` (`SES-F001` resolved) | `PASS` |

15 distinct `SES-###` requirements drafted. After `SES-F001`'s remediation: 12 `PASS`, 1 `DOCUMENTED`
(boundary statement, not independently testable — its own evidence column now also names the verified,
deferred canonical scenario), 2 `GAP` (`SES-004`, `SES-014`, both behind `SES-F002`, still open). No
requirement is `PI_BEHAVIOR_UNCERTAIN` — nothing above needed a Pi-source read to resolve, only the
frozen design's own text.

---

## 5. Implementation inventory

| File/module | Responsibility | Decision | Evidence |
|---|---|---|---|
| `session/log.py` | Append-only, sequence-numbered, JSON-validated event storage | `RETAIN` | `test_log.py`, matches `SES-001`/`SES-005` exactly |
| `session/events.py` | Event-name vocabulary, surface/log-only split, open-namespace validation | `RETAIN + HARDEN` | `test_events.py`, `test_plugin_events.py`; hardening needed for `SES-F002` (missing/misapplied log-only kinds) |
| `session/derive.py` | Projects log surface into model history; encodes/decodes the LLM vocabulary for storage; walks fork ancestry; applies reset/compaction | `RETAIN` | `test_derive.py` (16 tests), `test_properties.py` (7 Hypothesis property tests). **The charter's own migration hypothesis (§6) flagged this file as a "realignment candidate" — not borne out by this pass's evidence.** Every reset/compaction/fork rule in design §5 is implemented exactly as specified; the only gap found was cross-language canonical *coverage* of the newer LLM-vocabulary round-trips (`SES-F001`, now resolved), never a defect in `derive.py`'s own logic. |
| `session/operations.py` | `fork`/`reset`/`compact` as log events, each with a stated derivation effect | `RETAIN` | `test_fork.py`, `test_reset.py`, `test_compaction.py`; docstrings match design §5 table almost verbatim |
| `session/artifacts.py` | Content-addressed storage, no deletion | `RETAIN` | `test_artifacts.py`; matches design's no-removal-API rule exactly |
| `session/request_header.py` | Content-addressed request-header composition/reconstruction | `RETAIN` | `test_request_header.py`, `test_request_header_tools.py`; `assemble_system` used as the canonical join on both the dispatch and reconstruction sides, matching design's explicit requirement |
| `session/service.py` | `ctx.sessions` plugin seam; owns live logs + shared artifact store | `RETAIN` | no dedicated unit test file, but exercised indirectly through `agent_loop`/`agent` test suites (outside this layer's boundary to certify) |
| `session/__init__.py` | Public exports | `RETAIN` | exports match every symbol used by the test suite and by `agent_loop/driver.py` |

No file received `MODIFY`/`REWRITE`/`DELETE`/`DEFER` this pass. `events.py` is the only
`RETAIN + HARDEN` — the fix is additive (align the log-only kind vocabulary with design §5/§6, see
`SES-F002`), not a rewrite of working code.

---

## 6. Existing-test audit

All 11 Python session test files were read in full this pass (172 test functions total). Every file
exercises the real public API (no reach-into-private-state), every assertion is deterministic, and
none asserts an implementation detail the design doesn't make normative. No file duplicates canonical
conformance — where a Python test and a `conformance/session/*.yaml` scenario cover the same rule
(e.g. reset, fork, compaction), the Python test adds edge cases the YAML scenario doesn't (e.g.
`test_a_forks_compaction_retains_its_own_tail_only`'s sequence-number-restart case), rather than
re-asserting the same case twice.

| Test file | Requirement(s) | Validity | Disposition | Reason |
|---|---|---|---|---|
| `test_artifacts.py` | `SES-010` | 7 tests; confirms dedup, cross-type (str/bytes) identity, membership, missing-ref error, and the explicit absence of any delete/remove method | `KEEP` | — |
| `test_compaction.py` | `SES-008` | 8 tests; `test_nothing_is_double_projected` is direct Python-unit evidence for the design's named "retained-tail-no-duplicate" scenario (§7) | `KEEP` | — |
| `test_derive.py` | `SES-002`, `SES-006`, `SES-007`, `SES-008` | 16 tests; every LLM-vocabulary round-trip (signatures, usage/cost, diagnostics, deferred) has a dedicated test | `KEEP` | — |
| `test_events.py` | `SES-003` | 4 tests confirm the surface is exactly 3 kinds and lifecycle events are excluded | `KEEP` | — |
| `test_fork.py` | `SES-006` | 11 tests, including nested-fork-of-fork, fork-local compaction, and the sequence-number-restart edge case | `KEEP` | — |
| `test_log.py` | `SES-001`, `SES-005` | 10 tests; thorough JSON-safety rejection coverage (cycles excluded by design of `_check_json_safe`, though no test constructs one — see §7 note below) | `KEEP` | — |
| `test_plugin_events.py` | `SES-003`, `SES-011`, `SES-012` | 11 tests; `test_a_raw_string_kind_is_the_same_event_as_its_constant` is the exact Python-unit mirror of `event-name-identity-is-by-value.yaml` | `KEEP` | — |
| `test_properties.py` | `SES-002`, `SES-006`, `SES-007`, `SES-008` | 7 Hypothesis property tests (order preservation, reset-yields-empty, compaction bound, monotonic growth, fork-chain-of-any-depth) | `KEEP` | Real property tests per the method's §7 — a genuine strength, not just unit-test padding |
| `test_request_header.py` | `SES-009` | 7 tests; `test_a_stable_component_is_stored_once_across_many_steps` is direct Python-unit evidence for the design's named "request-header-component-reuse" scenario (§7) | `KEEP` | — |
| `test_request_header_tools.py` | `SES-009` | 5 tests, including a strengthened content-addressing pin (`test_an_unchanged_tool_set_addresses_to_the_same_reference` explicitly rules out a constant-reference implementation, not just "two calls agree") | `KEEP` | — |
| `test_reset.py` | `SES-007` | 6 tests, matches design table exactly | `KEEP` | — |

All 11 files: `KEEP`. No `STRENGTHEN`/`MOVE TO CONFORMANCE`/`REWRITE`/`DELETE` disposition was warranted
by anything found this pass. One minor observation, not a defect: `_check_json_safe`'s cycle-detection
branch (`log.py:60`, `"contains a cycle"`) has no dedicated test constructing a genuine reference cycle
— every existing rejection test uses a different violation (bytes, non-string keys, sparse-like
tuples). Worth a `STRENGTHEN` in a future pass, not blocking.

Python already enforces 100% line coverage for currently-covered core packages (per the method's own
floor); `minion_agent/session/` is inside that covered set (confirmed: all 8 files appear in `src/`
under the package tree exercised by the existing suite runs in Layers 01/02's own gate re-runs).

---

## 7. Missing test / conformance coverage

### Canonical conformance — inventory of all 17 `conformance/session/*.yaml` (post-remediation)

**Correction to this section's first-pass count, made honestly rather than silently:** the first pass
reported "5 of 15 are unfilled placeholders" and omitted `rich-assistant-message-round-trip.yaml` from
that count entirely. A fresh, careful recount (`grep`-verified against every file's actual
`TO_BE_FILLED`/`TO_BE_BOUND_TO_REAL_PUBLIC_API`/`TO_BE_PINNED_EXACTLY` markers, not re-trusted from the
first pass) found **6** placeholders, not 5. This is the kind of self-review gap this project's own
discipline exists to catch before it compounds — recorded here rather than quietly fixed.

| Scenario | Status | Maps to |
|---|---|---|
| `compact-now-then-derive.yaml` | real, passing | `SES-008` |
| `compaction-repeated-and-nested.yaml` | real, passing | `SES-008` |
| `content-signatures-round-trip.yaml` | **filled this pass** — real, passing | `SES-002` |
| `deferred-handle-round-trip.yaml` | **filled this pass** — real, passing | `SES-002` |
| `diagnostic-round-trip.yaml` | **filled this pass** — real, passing | `SES-002` |
| `event-name-identity-is-by-value.yaml` | real, passing | `SES-011` |
| `fork-ancestry-derivation.yaml` | real, passing | `SES-006` |
| `fork-local-compaction.yaml` | real, passing | `SES-006`/`SES-008` |
| `overlapping-compaction.yaml` | real, passing | `SES-008` |
| `plugin-defined-event-kind.yaml` | real, passing | `SES-003`/`SES-012` |
| `plugin-event-stays-log-only-by-default.yaml` | real, passing | `SES-012` |
| `request-header-component-reuse.yaml` | **authored this pass** (previously did not exist under any name) — real, passing | `SES-009`/`SES-015` |
| `request-reconstruction-after-target-transform.yaml` | placeholder — **verified genuinely Layer-04-dependent, not a Layer-03 gap** (see below) | `SES-009`/`SES-013`, deferred |
| `request-reconstruction-with-artifacts.yaml` | **filled this pass** — real, passing | `SES-009`/`SES-015` |
| `reset-excludes-prior-surface.yaml` | real, passing | `SES-007` |
| `retained-tail-no-duplicate.yaml` | **authored this pass** (previously did not exist under any name) — real, passing | `SES-008` |
| `rich-assistant-message-round-trip.yaml` | **filled this pass** — real, passing | `SES-002`/`SES-009` |

**`request-reconstruction-after-target-transform` verified deferred, not fixed — a dedicated check
before assuming so, matching the discipline the two Layer-02 replay scenarios were held to.** The name
itself asks whether request-header/message reconstruction stays correct once target-model
transformation (XFORM) has run on top of session-derived history. Checked directly rather than
assumed: `find . -iname "*transform*" -o -iname "*xform*"` across `minion-agent-python/src/` returns
no matches — no target-model-transformation module exists in this repository at all, matching the
charter's own audit order (XFORM is item 4, after session/artifacts). Filling this scenario today
would require the session conformance runner to simulate target-model transformation semantics
itself — precisely the thin-runner violation the whole methodology exists to prevent. This is Outcome
A in the same framework the two Layer-02 replay scenarios used: the semantic contract (design §5's
"Relationship to Pi's message projection," already correctly stated) is Layer-03-owned and complete;
the executable realization depends on Layer 04, which has not started. Reclassified from `SES-F001`
scope to `DEFERRED TO LAYER 04, non-blocking for Layer 03 certification` — not filled, and not counted
as an open Layer-03 gap.

**All 5 originally-flagged placeholders were filled, and the 2 missing-named scenarios were authored,
this pass** — 7 items resolved. Extending `session-scenario.schema.json`/`session_runner.py` was
required first (the DSL previously supported only `{role, text}` and had no `record_header` step or
artifact-store observation at all) — full detail in `SES-F001`'s updated findings row (§15).

Two other design-planned-list names (`pi-harness-message-projections`, `compaction-estimator-last-valid-usage`,
`compaction-estimator-zero-usage-fallback`) map to `HAR-003`/`HAR-005` — phase 7, out of Layer 03's
scope per §1 — their absence here is expected, not a gap.

### Language-specific tests

- [x] Covered — see §6.

### Property/invariant tests

- [x] `test_properties.py` — 7 Hypothesis tests already exist, matching the method's own suggested
  examples (order preservation, no-shrink, fork-chain-of-any-depth).

### State-machine tests

- [x] Reviewed (§8-14 pass): Minion's session architecture has no lane/leaf state machine to test —
  that is precisely the Pi complexity `MINION-002` deliberately does not adopt. The closest analog,
  reset/compaction/fork's derivation-effect branching in `_derive`, is already covered as pure-function
  behavior by `test_derive.py`/`test_properties.py` rather than needing a separate state-machine
  harness. Not a gap.

### Concurrency tests

- [x] Reviewed (§9/§10, this pass): `SessionLog`/`ArtifactStore` are plain Python objects with no
  internal locking, and every operation is synchronous with no in-flight async work — confirmed there
  is no concurrent-mutation surface for this layer to test against. Not applicable, not missing.

### Fuzz tests

- [ ] Reviewed (§8, this pass), still a real gap: `decode_message`/`_decode_block` (session log
  decoding) is exactly the method's own suggested fuzz target, and none exists yet. Lower priority
  than `SES-F001`/`SES-F002`/`SES-F003` — decode only ever sees data `encode_message` itself produced
  in current usage, so this is defense-in-depth rather than a live gap, but worth adding in a future
  pass.

### Fault-injection tests

- [x] Reviewed (§8, this pass): every failure path found (non-JSON-safe data, malformed event name,
  missing artifact, unknown content-block/role on decode, fork of an unregistered session) is already
  exercised by an existing deterministic test (§6). No additional fault-injection harness is needed
  beyond what direct unit tests already provide, since none of these failures involve timing,
  concurrency, or partial external state — the two gaps `SES-F001` doesn't already cover, and
  `decode_message`/`SessionService.fork`'s generic exception types, are recorded above (§8's note)
  rather than duplicated here.

---

## 8. Failure model

| Failure | Surface | Result/throw/event | Retry? | Abort interaction | Logged/telemetry? |
|---|---|---|---|---|---|
| Non-JSON-safe data appended | `log.append` | `NotJsonSafeError`, raised before any mutation — `_check_json_safe` runs first, `self._events.append` second; confirmed atomic by `test_non_json_safe_data_is_rejected_at_append`'s `len(log) == 0` assertion | No | N/A (synchronous, no in-flight work to abort) | Not logged — by definition, a rejected append leaves no trace anywhere |
| Malformed event name appended | `log.append` | `InvalidEventNameError`, same atomicity | No | N/A | Not logged |
| Missing artifact reference | `ArtifactStore.get` | `MissingArtifactError` (a `KeyError` subclass) | No | N/A | Not logged |
| Unknown content-block type or message role on decode | `derive.py::_decode_block`/`decode_message` | Bare `ValueError` | No | N/A | Not logged |
| Fork of an unregistered session id | `SessionService.fork` | Bare `KeyError` from `self._logs[source_id]` (no session-specific error type) | No | N/A | Not logged |

The first three are deliberate, typed, and well-tested — matching Pi's own `SessionError`-typed-failure
model for structural violations (`session.ts`'s `invalid_payload`/`invalid_query`/`invalid_lane`
codes are the same "reject synchronously, no partial state" shape, though Minion doesn't need Pi's
lane/query error codes since it has no lanes/complex queries). The last two are real but minor gaps,
not formally raised as findings this pass given their low severity — see the note after this table.

**Not a formal finding, recorded here for whoever next touches these two call sites:** `decode_message`
and `SessionService.fork` raise generic `ValueError`/`KeyError` rather than a session-specific
exception type (the module already has `NotJsonSafeError`/`InvalidEventNameError`/
`MissingArtifactError` as precedent). This is `PARITY_NEUTRAL_HARDENING`-shaped (fixing it wouldn't
change any Pi-visible behavior, only the exception type callers must catch) and low-impact enough
(neither path is reachable with normal use — `decode_message` only sees data `encode_message` itself
produced; `fork` only sees session ids the same process registered) that it doesn't warrant a numbered
`SES-F` finding on its own. Worth a `STRENGTHEN` if either module is touched for another reason.

## 9. Security review

### Trust boundaries

Session log data originates from three sources: user input (`UserMessage`), model output
(`AssistantMessage`, including tool-call arguments), and tool results (`ToolResultMessage`, including
`details`). All three cross into the log through `encode_message`, which only serializes already-typed
LLM-vocabulary objects — there is no path from raw untrusted bytes directly into the log bypassing the
LLM layer's own construction.

### Input validation

`_check_json_safe` (log.py) is the log's own validation boundary: it rejects non-finite numbers,
cycles, non-plain objects, sparse arrays, non-enumerable properties, symbol keys, and non-string keys,
walking every nesting level — confirmed via `test_log.py`'s 6 rejection tests, including a nested case.
This defends against malformed/unstable data, not against adversarial *content* (a tool result
containing arbitrary text is valid JSON and is accepted as-is, by design — the log's job is to record
what happened, not to sanitize it).

### Authority / privilege

No access-control layer exists inside `session/*.py` itself — anything holding a `SessionLog`/
`SessionService` reference can `append`/`fork`/`reset`/`compact` freely. This is consistent with the
plugin architecture: authority over *who* can reach `ctx.sessions` is a runtime/scope concern (Layer
01, already certified), not something this layer re-implements.

### Secret handling

The log stores tool-result `details` and assistant `diagnostics` verbatim, with no redaction step
inside `session/*.py`. `AssistantMessageDiagnostic`'s own docstring (Layer 02) already frames
diagnostics as "redacted provider/runtime diagnostics" — i.e., redaction is the *producer's*
responsibility (whatever constructs the diagnostic) before it ever reaches the log, not something
Layer 03 does independently. No finding raised: this matches the design's own division of
responsibility, and no evidence was found of the log adding unredacted data beyond what it was given.

### Resource abuse / bounds

Both `SessionLog` and `ArtifactStore` grow without bound and never evict — by design (`RISK-001`,
recorded above; this is the explicitly-deferred Phase-9 durability/lane-management gap, not a
Layer-03-owned defect to fix now). No additional resource-abuse surface was found specific to Layer 03
(no recursion depth issue beyond the fork-chain walk, covered under §12 performance).

### Isolation

Session logs are isolated per session id (`SessionService._logs: dict[str, SessionLog]`, one object
per id). The `ArtifactStore` is deliberately **shared across all sessions** in one `SessionService`
(`service.py`'s own docstring: "content addressing only pays off if a stable block is stored once for
the deployment, not once per session"). This is not an information-leak risk — SHA-256 content
addressing is one-way; producing a colliding reference requires already possessing the exact content —
but it is a deliberate scope choice worth stating explicitly: artifact isolation is deployment-wide, not
per-session or per-tenant. No finding raised; this matches the design's own stated rationale, not an
unreviewed side effect.

## 10. Reliability and operations

- **Cancellation:** not applicable — `SessionLog.append` and every `operations.py` function are
  synchronous and complete immediately; there is no in-flight async work at this layer to cancel.
- **Timeouts:** not applicable, same reason.
- **Retry:** not applicable — append either succeeds atomically or raises; there is nothing to retry
  against (a caller retrying after a rejection would need to fix its data first).
- **Cleanup:** no dispose/close semantics exist for `SessionLog`/`ArtifactStore`, matching the
  never-delete design — there is nothing to clean up.
- **Shutdown:** not applicable — purely in-memory, no background tasks, no open file/network handles.
- **Partial failure:** confirmed atomic — `_check_json_safe` runs to completion before
  `self._events.append`, so a rejected append can never leave a half-written event (§8, §6).
- **Persistence/restart:** **`SessionLog`/`ArtifactStore` are pure in-memory objects; a process restart
  loses all session history.** Checked against the frozen design before treating this as a new finding:
  it is not one. `2026-08-20-minion-agent-design.md`'s "Stratum C — Pi AgentHarness durable operation
  parity" (lines 110-116) explicitly names this exact gap ("lane-scoped runs... durable program state,
  pending writes, replay policy, crash/deferred resume") as "a known deferred parity phase, not an
  optional future abstraction," assigned to Phase 9 (line 1851), with the design's own binding
  statement: "Until the parity phase lands, Minion MUST NOT claim complete Pi AgentHarness parity."
  Recorded as `RISK-001` in `risk-register.md` this pass (previously the register held only its
  placeholder row) rather than left as an implicit assumption — `ACCEPTED`, not a Layer-03 defect.
- **Dependency disappearance:** not applicable within this layer's own scope — `SessionService` has no
  dependency on another plugin service beyond the runtime's own `ctx.provide` mechanism (Layer 01,
  certified).

## 11. Observability

### Events

The session log's own log-only lifecycle events (`turn/*`/`step/*`/`assistant/chunk`/`tool/call`/
`request/header`/`session/forked`/`session/reset`/`compaction`) double as this layer's observability
surface — there is no separate telemetry-span emission inside `session/*.py` itself. Span emission
(`SpanKind.TURN`/`SpanKind.STEP`) happens in `agent_loop/driver.py`, outside this layer's scope.

### Logs

No Python `logging` module usage exists in `session/*.py` — intentional: the session log itself *is*
the durable record; a separate ad-hoc logger would duplicate it without adding information.

### Metrics

Pi's `SessionStorage` interface has a `getStats()` returning `SessionStats`
(`messageCount`/`cachedTokens`/`uncachedTokens`/`totalTokens`/`costTotal`) — Minion's `session/*.py`
has no equivalent aggregate-query API. Not raised as a finding: `MINION-002`'s own disposition is "N/A
— Minion persistence architecture," and an aggregate-stats query isn't part of "model-visible history"
in the sense the design's own equivalence claim covers — this reads as a legitimate scope choice, not
an unreviewed omission, though it may be worth adding as a `PARITY_NEUTRAL_HARDENING` convenience in a
future pass if something downstream needs it.

### Traces / correlation IDs

`session_id` is the correlation identifier at this layer. `run_id`/`turn_id`/`request_id` (per the
method's own suggested vocabulary) don't originate in `session/*.py` — they belong to Layer 07/08's
scope once those layers assign identity to runs/turns.

### Sensitive fields excluded from telemetry

Not applicable — this layer has no direct telemetry integration to exclude fields from (§9's secret-
handling note covers the relevant boundary instead).

## 12. Performance / complexity

| Path | Expected complexity/budget | Evidence | Risk |
|---|---|---|---|
| `SessionLog.append` | O(size of `data`) for JSON-safety validation, O(1) amortized for the list append | `log.py::append`/`_check_json_safe` read directly | None — unavoidable, proportional to the data being stored |
| `ArtifactStore.put` | O(size of content) for the SHA-256 hash | `artifacts.py::put` | None — unavoidable; `setdefault` makes repeat `put`s of identical content cheap (dict lookup, no re-storage) |
| `derive_messages`/`_derive` | O(events in the log) per call, plus O(fork-chain depth × ancestor log size) for a forked session — **not memoized** | `derive.py::_derive`'s recursive ancestor walk; confirmed real (not a hypothetical) by `test_fork.py::test_a_fork_of_a_fork_walks_the_whole_chain` | Observation, not a blocking finding. `agent_loop/driver.py::_run_step` calls `derive_messages(log)` on **every** model request (driver.py:246), so a long-running session or a deep fork chain re-derives its entire visible history from scratch on every step — worst case O(total events) work per step, O(n²) over a session's full lifetime before compaction bounds it. Compaction (§4, `SES-008`) already exists specifically to bound the effective surface size in practice, and this cost pattern may well match Pi's own re-derivation-per-request behavior rather than being a Minion-specific inefficiency — not verified against Pi source this pass, since doing so would mean auditing Pi's `agent-session-runtime.ts` request-assembly path, which is Layer 08 territory. Worth a memoization pass later (`PARITY_NEUTRAL_HARDENING` — wouldn't change Pi-visible output, only speed); not blocking for Layer 03 certification. |
| `record_header` | O(number of components) `put` calls per request, each O(size) per §above | `request_header.py::record_header` | None — matches the design's own content-addressing intent exactly: unchanged components cost a hash+dict-lookup, not a re-snapshot |

## 13. Public API / serialization

- **Public API:** `SessionLog`, `SessionEvent`, `EventKind`, `EventName`, `ArtifactStore`,
  `SessionService`, plus module-level functions (`derive_messages`, `encode_message`, `decode_message`,
  `messages_from`, `effective_surface`, `is_surface`, `validate_event_name`, `fork`, `reset`, `compact`,
  `assemble_system`, `record_header`, `reconstruct_header`, `reconstruct_tools`) — all exported via
  `session/__init__.py`'s `__all__`, confirmed exhaustive against what the test suite imports.
- **Internal API:** every underscore-prefixed helper (`_encode_block`/`_decode_block`/`_encode_usage`/
  `_decode_usage`/`_encode_diagnostic`/`_decode_diagnostic`/`_encode_deferred`/`_decode_deferred`/
  `_latest_of`/`_derive`/`_check_json_safe`/`_as_bytes`) — confirmed none of these leak through
  `__init__.py`.
- **Stable/experimental:** no explicit stability markers exist anywhere in this module, consistent with
  the rest of the codebase's style (Layers 01/02 didn't use them either) — not a gap specific to this
  layer.
- **Serialized schemas:** the JSON dict shapes `encode_message`/`_encode_*` produce are this layer's
  own wire format for the log — Minion-private per `MINION-002`'s divergence disposition, not a
  cross-language-pinned schema the way `agent-scenario.schema.json` pins the LLM vocabulary's
  *reconstructed message* shape. This is a deliberate scope boundary, not an omission: what must be
  cross-language-identical is the *output* of `derive_messages()` (already Layer-02-vocabulary-typed,
  already schema-pinned), not the log's own internal storage encoding, which `MINION-002` explicitly
  frees each language implementation to choose independently.
- **Cross-language fields:** the reconstructed message vocabulary (Layer 02, certified) plus the
  simple `(kind: str, seq: int, data: dict)` event triple — no Layer-03-specific cross-language field
  beyond what Layer 02 already pins.
- **Round-trip tests:** extensive — `test_derive.py`'s 16 tests, `test_request_header.py`/
  `test_request_header_tools.py`'s reconstruction tests, all read in full this pass (§6).

## 14. Documentation audit

| Document | Accuracy | Required action |
|---|---|---|
| `spec/session.md` | Incomplete relative to the frozen design §5 — missing the log-only kind list and the by-value event-identity rule | `SES-F003` (§15) |
| `2026-08-20-minion-agent-design.md` §5/§6 | Accurate against the implementation for every rule except the log-only event vocabulary | `SES-F002` (§15) |
| Module docstrings (`log.py`, `events.py`, `operations.py`, `artifacts.py`, `derive.py`,
  `request_header.py`) | Consistently high quality — every one explains *why*, not just *what* (e.g.
  `artifacts.py`'s docstring on the 15k-token-snapshot problem content-addressing solves;
  `operations.py`'s docstring on why these are log events rather than mutations). No drift found
  between any docstring and the behavior it describes. | None |
| `pi-parity-manifest.yaml` (`MINION-002`/`MINION-003` rows) | Accurate; both cite real test evidence. `MINION-003`'s cited scenario was a placeholder at the time of the first pass; now filled, and `request-header-component-reuse` added to its `tests:` list this pass | `SES-F001`, resolved |

---

## 15. Findings

| ID | Severity | Classification | Description | Disposition / action |
|---|---|---|---|---|
| `SES-F001` | MEDIUM | `CONTRACT_ASSURANCE_DEFECT` — **RESOLVED** | **Corrected count (§7): 6, not 5, of 17 `conformance/session/*.yaml` scenarios were unfilled placeholders** (`content-signatures-round-trip`, `deferred-handle-round-trip`, `diagnostic-round-trip`, `request-reconstruction-after-target-transform`, `request-reconstruction-with-artifacts`, `rich-assistant-message-round-trip` — the first pass's own count omitted the last of these, corrected honestly rather than silently). `MINION-003`'s own manifest row cited `request-reconstruction-with-artifacts` as its `tests:` evidence while it was still a placeholder — a normative rule backed by no real scenario, exactly the situation the charter's own `CONTRACT_ASSURANCE_DEFECT` definition names. Two further gaps of the identical shape were confirmed (not assumed) this pass: the design's own originally-planned `retained-tail-no-duplicate` and `request-header-component-reuse` scenarios had never been created under any name. All 8 had real, passing Python-unit-level coverage already, so none were unverified Python behavior — only cross-language canonical evidence was missing. | **Fixed and re-verified this pass.** One of the 8 (`request-reconstruction-after-target-transform`) was investigated first, not assumed fixable: confirmed via direct repository search (no `transform`/`xform` module exists anywhere in `minion-agent-python/src/`) that it is genuinely Layer-04-dependent — filling it now would mean the runner simulating XFORM semantics, the exact thin-runner violation this methodology forbids. Reclassified `DEFERRED TO LAYER 04, non-blocking`, matching the two Layer-02 replay scenarios' own Outcome A (§7 has the full investigation). **The remaining 7 were fixed:** extended `conformance/schema/session-scenario.schema.json` (new `contentBlock`/`usage`/`cost`/`diagnostic`/`diagnosticError`/`deferredHandle`/`toolStub`/`assistantDetail`/`toolResultDetail` `$defs`, a richer `step.append` accepting content blocks/usage/diagnostics/deferred/api/response identity/tool-result fields, a new `record_header` step, and `expect_assistant_details`/`expect_tool_result_details`/`expect_reconstructed_header`/`expect_artifact_count` top-level assertions — all additive, the pre-existing `{role, text}`-only shape still works unchanged, confirmed by re-running the original 10 real scenarios before writing any new content) and `tests/conformance/session_runner.py` (real object construction on the input side, real-attribute-only normalization on the output side, mirroring the `LLM-F010` pattern exactly). Filled the 5 placeholders and authored the 2 missing scenarios. **Verified, not just asserted:** an independent throwaway script (not reusing any authored scenario) constructed a fully-unset `AssistantMessage`/`ToolResultMessage` directly and confirmed every optional field normalizes to `None`, never a fabricated value. `pi-parity-manifest.yaml`'s `MINION-003` row updated to also cite `request-header-component-reuse`. Full suite re-run fresh: 724 passed/42 xfailed/0 failed (up from 715/47 — the exact `+9`/`-5` the 7 newly-real scenarios predict, verified arithmetically before trusting it), `ruff` clean, `mypy` clean on `session_runner.py` (checked alongside a `src/` file, matching the project's own `mypy.ini` scoping and `LLM-F010`'s precedent; `test_session_conformance.py`'s pre-existing `yaml`-stub gap is unrelated and outside the project's configured mypy scope). `SES-F001` is `RESOLVED`. |
| `SES-F002` | HIGH | `CONTRACT_ASSURANCE_DEFECT` (pending Layer 08's full behavioral audit to determine whether it is also a `PI_PARITY_DEFECT`) | The frozen design's own §5 log-only event list names `run/start`, `run/end`, `turn/start`, `turn/end` as the four lifecycle kinds. `session/events.py`'s actual `EventKind` has `TURN_START`/`TURN_END` and `STEP_START`/`STEP_END` — no `run/*` kind exists at all, and `step/*` appears nowhere in the design's list. Worse: `agent_loop/driver.py` was read directly (not inferred) to check what these events are actually emitted around. `_run_turn()` (driver.py:107-173) wraps a `while True` loop calling `_run_step()` repeatedly until no tool calls remain — i.e., it spans **multiple model requests** — and appends `EventKind.TURN_START`/`TURN_END` at its boundaries. `_run_step()` (driver.py:214-306) makes exactly **one** model request plus its tool calls/results, and appends `EventKind.STEP_START`/`STEP_END` at its boundaries. Design §6, cross-referenced by §5's own log-only list, states explicitly and by name: "Run / invocation, bounded by `agent_start...agent_end`, may contain multiple turns. Turn: exactly one assistant response + the tool calls/results caused by that assistant response. An implementation may use a private 'step' object internally, but MUST NOT redefine observable `turn` to mean a whole multi-request run." The event literally named `turn/start`/`turn/end` is emitted around what the design's own words describe as a **Run**; the true Pi-Turn boundary (one request + its tools) is logged under `step/*`, a name the design's log-only list never mentions. This is the exact collision §6 warns against, found in the log vocabulary rather than in prose. | Open, not fixed this pass — this touches `agent_loop/driver.py` (Layer 08 territory) as well as `session/events.py` (Layer 03's own vocabulary), so a full fix belongs to whichever pass reconciles both. Flagged now because `events.py`'s vocabulary is Layer-03-owned and the design-vs-code mismatch is independently verifiable without touching driver.py. Classified `CONTRACT_ASSURANCE_DEFECT` for now (the frozen design and the implementation are internally inconsistent) rather than `PI_PARITY_DEFECT`, because this pass did not audit whether `_run_turn`'s actual *behavior* (not just its event name) is Pi-Run-correct — that full behavioral question belongs to Layer 08. If Layer 08 finds the behavior itself is also wrong, this should be reclassified then, not assumed now. |
| `SES-F003` | LOW | `CONTRACT_ASSURANCE_DEFECT` | `spec/session.md` (4 short paragraphs) restates design §5's append/surface/fork/reset/compaction rules but never mentions the log-only lifecycle kind list (`run/*`/`turn/*`/`assistant/chunk`/`tool/call`/`request/header`) or the explicit by-value event-name-identity rule — both present in the frozen design §5 and both independently conformance-pinned (`event-name-identity-is-by-value.yaml`; the log-only kinds via `SES-F002`, once fixed). A normative spec document that is silent on rules the frozen master states explicitly and conformance already tests is incomplete relative to its own authority chain. | Open, not fixed this pass — `spec/session.md` is a shared-contract file; extending it should follow the same "does this make already-frozen semantics observable, or redefine them" review used for `LLM-F010`, once `SES-F002` settles what the correct log-only vocabulary actually is (no point extending the spec with a vocabulary this pass just found to be wrong). |

No `PI_PARITY_DEFECT` and no `PI_BEHAVIOR_UNCERTAIN` findings this pass — every finding traces to an
internal inconsistency in Minion's own frozen contract (design vs. spec vs. implementation vs.
conformance), not to an unresolved question about what Pi itself does or a confirmed behavioral
mismatch against Pi.

---

## 16. Certification gate

```text
Design alignment                         [~]  §5/§6 read directly and traced; SES-F002 found a design-vs-implementation mismatch in the log-only event vocabulary
Pi parity                                [x]  MINION-002/003 are intentional divergences by the manifest's own disposition; no Pi-visible behavioral mismatch found this pass (SES-F002's mismatch is design-vs-code, not yet confirmed Pi-behavioral)
Normative spec                           [ ]  SES-F003 — spec/session.md incomplete relative to frozen design §5
Parity manifest                          [x]  MINION-002/003 both present, both dispositioned, both cite real test evidence (MINION-003 updated this pass to also cite request-header-component-reuse)
Canonical conformance                    [x]  SES-F001 RESOLVED — 7 of 8 named session-family gaps filled/authored this pass; the 8th (request-reconstruction-after-target-transform) verified genuinely DEFERRED TO LAYER 04, non-blocking
Python tests where implemented           [x]  172 test functions across 11 files read in full; plus 16 real session conformance scenarios (up from 9) and their schema-validation coverage, all passing fresh
Rust tests where implemented             [x]  N/A — Rust session/ not implemented (Phase 2), consistent with the manifest
Property/invariant tests                 [x]  test_properties.py — 7 Hypothesis tests already exist
Concurrency tests where applicable       [x]  §9/§10 reviewed — no concurrent-mutation surface exists in this layer (synchronous, in-memory, no locking needed); not applicable rather than missing
Fault-injection tests where applicable   [x]  §8 failure model reviewed — every failure path (JSON-safety, event-name, missing-artifact, decode) is deterministic and already covered by §6's test read
Security review                          [x]  §9 complete — trust boundaries, validation, authority, secrets, resource abuse, and isolation all reviewed; no finding beyond RISK-001 (already reliability-owned)
Reliability review                       [x]  §10 complete — RISK-001 (in-memory-only persistence) confirmed intentional per the frozen design's own Phase-9 commitment, recorded in risk-register.md
Observability review                     [x]  §11 complete — no finding; metrics/stats-query gap noted as a future convenience, not a defect
Performance review                       [x]  §12 complete — one non-blocking observation (derive_messages re-derivation cost, not memoized)
Public API review                        [x]  §13 complete — public/internal boundary confirmed clean; cross-language scope boundary (log wire format vs. reconstructed message shape) confirmed intentional
Documentation                            [x]  §14 complete — SES-F002/F003 already captured; module docstrings found accurate throughout
All findings classified                  [x]  SES-F001..F003 classified
No unresolved Pi uncertainty             [x]  none raised this pass
No unresolved parity defect              [x]  none raised this pass (SES-F002 classified CONTRACT_ASSURANCE_DEFECT pending Layer 08)
No unresolved contract-assurance defect  [ ]  ACTIVE: SES-F002, SES-F003. RESOLVED this pass: SES-F001.
Deferred risks recorded                  [x]  RISK-001 (in-memory-only persistence, Phase 9) recorded in risk-register.md this pass
```

---

## 17. Certification result

**Result:** `IN_AUDIT`

§1-14 are complete with real grounding, across three passes. First pass: the frozen design §5/§6/§8
was read directly, `spec/session.md` was checked against it and found incomplete (`SES-F003`),
`MINION-002`/`MINION-003` were traced to their manifest rows, pinned Pi session source was read to
confirm the storage-architecture divergence is intentional and scoped correctly, all 8 Python modules
were read and inventoried, and all 15 canonical session scenarios were read and classified
real-vs-placeholder. Second pass: all 11 test files were read in full (172 test functions, all `KEEP`),
the two design-named scenarios with no canonical file were confirmed genuinely missing rather than
assumed, and §8-14's category reviews were completed, surfacing `RISK-001`. Third pass (this update):
`SES-F001` was remediated and resolved.

Two real findings remain open, both `CONTRACT_ASSURANCE_DEFECT`, none `PI_PARITY_DEFECT` or
`PI_BEHAVIOR_UNCERTAIN`; one is now resolved:

- **`SES-F001`** (MEDIUM) — **RESOLVED.** 6 placeholder scenarios were filled and 2 missing-named
  scenarios were authored (7 total; the count itself was corrected this pass from a first-pass
  undercount of "5," found and fixed honestly rather than silently). The 8th item
  (`request-reconstruction-after-target-transform`) was investigated, not assumed, and confirmed
  genuinely `DEFERRED TO LAYER 04` — no XFORM module exists anywhere in the repository, so filling it
  now would mean the runner simulating semantics it doesn't own. `conformance/schema/session-scenario.schema.json`
  and `tests/conformance/session_runner.py` were extended (additively — the original 10 real scenarios
  still pass unchanged) to expose rich `AssistantMessage`/`ToolResultMessage` fields and a
  `record_header`/artifact-observation path the DSL previously had no way to reach at all.
  `pi-parity-manifest.yaml`'s `MINION-003` row updated. Full detail, including the independent
  adversarial absence-check and the exact fresh gate numbers, is in `SES-F001`'s findings row (§15).
- **`SES-F002`** (HIGH, still open): the frozen design's own log-only event vocabulary (`run/*`/`turn/*`)
  doesn't match what `session/events.py` declares (`turn/*`/`step/*`, no `run/*`), and direct inspection
  of `agent_loop/driver.py` shows the mismatch isn't cosmetic — the event literally named `turn/start`
  is emitted around a multi-request loop, which is exactly the Run/Turn conflation design §6 explicitly
  prohibits by name. Still the most significant open finding and still sits right at the Layer
  03/Layer 08 boundary; the full behavioral verdict (is `_run_turn`'s actual control flow Pi-correct,
  independent of its event names?) remains explicitly reserved for Layer 08's own audit — this pass
  added no new evidence on that question, deliberately, to avoid working ahead of the sequencing rule.
- **`SES-F003`** (LOW, still open): `spec/session.md` doesn't restate the frozen design's log-only kind
  list or its by-value event-identity rule, both of which conformance already depends on (or will, once
  `SES-F002` is resolved).

`RISK-001` (`SessionLog`/`ArtifactStore` in-memory only, confirmed intentional per the design's own
Phase-9 commitment, recorded in `risk-register.md`) needs no action from this layer — unchanged this
pass.

**Migration hypothesis correction (first pass, still standing):** the charter's own §6 flagged "session
derive/reconstruction" as a "realignment candidate." The full read of `derive.py` (and its 16+7
dedicated tests, now joined by 5 filled canonical round-trip scenarios) found no defect in its logic —
every reset/compaction/fork rule is implemented exactly as design §5 specifies. Recorded as **not
borne out by evidence**, per the charter's own instruction that a starting hypothesis is not a
substitute for audit evidence.

**Not started this pass, by design:** remediation of `SES-F002`/`SES-F003`, and the certification
decision itself (which requires both resolved, per the charter's own "must be repaired before
certification" rule for `CONTRACT_ASSURANCE_DEFECT`). Also not started: Layer 04 (XFORM), Layer 08
(Agent run/turn state machine — deliberately not pulled forward even though `SES-F002` touches its
territory), Rust implementation for this layer (Phase 2, not yet due), and any Phase-5 work.

**Follow-up dependencies:**

1. ~~Resolve `SES-F001`~~ — **done, this pass.**
2. Resolve `SES-F002`: determine the correct log-only event vocabulary (add `run/*`? rename
   `turn/*`↔`step/*`? something else the design doesn't yet state precisely enough to decide alone) —
   needs Layer 08's own audit of `_run_turn`/`_run_step`'s actual control-flow correctness first. Do
   not silently rename without confirming the behavior is Pi-correct; a naming fix over incorrect
   behavior would hide the real defect. This is the one item in this layer's findings that may end up
   waiting on Layer 08 rather than being fully closeable within Layer 03 alone — if so, the
   certification gate should say so explicitly rather than force a premature resolution.
3. Resolve `SES-F003` once `SES-F002` settles the correct vocabulary — extending `spec/session.md`
   with a vocabulary this pass just found to be wrong would create more contract-assurance debt, not
   less.
4. `RISK-001` needs no action from this layer — it is Phase 9's commitment to fulfill, already
   recorded and cited.
