# Session + Artifacts — Fidelity Assurance & Certification

**Layer ID:** `03`  
**Status:** `IN_AUDIT`  
**Audit date:** 2026-08-23 (first pass: §1-7 complete with real grounding against the frozen master
design §5/§6/§8, `spec/session.md`, `pi-parity-manifest.yaml`'s `MINION-002`/`MINION-003` rows, the
pinned Pi session source (`ref-repos/pi/packages/agent/src/harness/session/`), all 8 Python session
modules, all 11 Python session test files, and all 15 `conformance/session/*.yaml` scenarios. §8-14
category reviews, remediation, and certification are pending a follow-up pass — not started this pass,
per the standing one-layer-at-a-time sequencing rule.)  
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
| `SES-002` | Model-visible means logged: request history reconstructable from committed state | design §5, `MINION-002` | `derive.py::derive_messages` + `request_header.py` | not implemented | `test_derive.py`, `conformance/session/*` (partial — see `SES-F001`) | `PARTIAL` |
| `SES-003` | Two-tier event vocabulary: surface (`user/message`/`assistant/message`/`tool/result`) vs log-only; open namespace, name is the identity | design §5, `spec/session.md` | `events.py::EventKind`/`CORE_SURFACE_KINDS`/`is_surface`/`validate_event_name` | not implemented | `test_events.py`, `plugin-defined-event-kind.yaml`, `plugin-event-stays-log-only-by-default.yaml` | `PASS` |
| `SES-004` | Log-only lifecycle/fidelity/operations kinds are fully and correctly enumerated | design §5 (explicit list) | `events.py::EventKind` (partial — see `SES-F002`) | not implemented | none dedicated | `GAP — SES-F002` |
| `SES-005` | Append pipeline: validate → atomic seq allocation → committed publication | `spec/session.md`, design §5 (implicit in log.py) | `log.py::append` | not implemented | `test_log.py::test_sequence_numbers_start_at_one_and_increase` + rejection tests | `PASS` |
| `SES-006` | `fork(source, at)`: references not copies, boundary fixed at fork time, later writes on either side stay private | design §5 table, `spec/session.md`, `MINION-002` | `operations.py::fork`, `derive.py::_derive`'s ancestry walk | not implemented | `test_fork.py` (11 tests), `fork-ancestry-derivation.yaml`, `fork-local-compaction.yaml` | `PASS` |
| `SES-007` | `reset()`: identity preserved, excludes all surface at-or-before, history stays readable | design §5 table, `spec/session.md` | `operations.py::reset`, `derive.py::effective_surface`/`_derive` | not implemented | `test_reset.py` (6 tests), `reset-excludes-prior-surface.yaml` | `PASS` |
| `SES-008` | Compaction: supersedes an effective range with summary + retained-tail provenance; no double-inclusion under repeated/overlapping/nested/fork-local compaction | design §5 table, `operations.py` docstring, `spec/session.md` | `operations.py::compact`, `derive.py::_derive`'s compaction branch | not implemented | `test_compaction.py` (8 tests), `compact-now-then-derive.yaml`, `compaction-repeated-and-nested.yaml`, `overlapping-compaction.yaml`, `fork-local-compaction.yaml` | `PASS` |
| `SES-009` | Content-addressed request header: components stored by hash, composition logged as references, dispatch and reconstruction use the same canonical join | design §5, `spec/session.md` | `request_header.py::assemble_system`/`record_header`/`reconstruct_header`/`reconstruct_tools` | not implemented | `test_request_header.py` (7 tests), `test_request_header_tools.py` (5 tests) | `PARTIAL — SES-F001` |
| `SES-010` | Artifacts holding model-visible content are never deleted; no removal API exists | design §5, `artifacts.py` docstring, `MINION-003` | `artifacts.py::ArtifactStore` (no delete method) | not implemented | `test_artifacts.py` (7 tests, incl. `test_the_store_has_no_delete`) | `PASS` |
| `SES-011` | Event name is the identity, compared by value — not by enum/object identity | design §5 "two consequences" | `events.py` (`EventName = str`; `is_surface` compares `event.kind in surface`) | not implemented | `event-name-identity-is-by-value.yaml`, `test_plugin_events.py::test_a_raw_string_kind_is_the_same_event_as_its_constant` | `PASS` |
| `SES-012` | An open logging namespace is not an open surface: declaring/appending a plugin event name does not by itself admit it to model history | design §5 | `log.py`/`events.py` (`surface_kinds` parameter, defaults to `CORE_SURFACE_KINDS`) | not implemented | `plugin-event-stays-log-only-by-default.yaml`, `test_plugin_events.py` (multiple) | `PASS` |
| `SES-013` | Session/log projection approximates Pi's `AgentMessage -> Message` conversion; target-model transformation is a distinct, later stage | design §5 "Relationship to Pi's message projection" | `derive.py` (scope boundary only) | N/A | none dedicated — a boundary statement, not independently testable within Layer 03 | `DOCUMENTED` |
| `SES-014` | Session log-only naming must track Pi's Run/Turn vocabulary; observable `turn` MUST NOT mean a multi-request run | design §6 (explicit prohibition), cross-referenced by §5 | `events.py::EventKind.TURN_START`/`TURN_END`/`STEP_START`/`STEP_END`; emitted by `agent_loop/driver.py` | not implemented | none dedicated; driver.py inspection contradicts the rule — see `SES-F002` | `GAP — SES-F002` |
| `SES-015` | `MINION-003`: content-addressed artifacts are a permitted storage divergence only when model-visible bytes stay equivalent to what was dispatched | `MINION-003`, design §5 | `request_header.py` + `artifacts.py` | not implemented | `request-reconstruction-with-artifacts.yaml` — **unfilled placeholder**, see `SES-F001` | `GAP — SES-F001` |

15 distinct `SES-###` requirements drafted. 10 `PASS`, 1 `DOCUMENTED` (boundary statement, not
independently testable), 4 `GAP` (2 requirements behind `SES-F001`, 2 behind `SES-F002`; no requirement
is `PI_BEHAVIOR_UNCERTAIN` — nothing above needed a Pi-source read to resolve, only the frozen design's
own text).

---

## 5. Implementation inventory

| File/module | Responsibility | Decision | Evidence |
|---|---|---|---|
| `session/log.py` | Append-only, sequence-numbered, JSON-validated event storage | `RETAIN` | `test_log.py`, matches `SES-001`/`SES-005` exactly |
| `session/events.py` | Event-name vocabulary, surface/log-only split, open-namespace validation | `RETAIN + HARDEN` | `test_events.py`, `test_plugin_events.py`; hardening needed for `SES-F002` (missing/misapplied log-only kinds) |
| `session/derive.py` | Projects log surface into model history; encodes/decodes the LLM vocabulary for storage; walks fork ancestry; applies reset/compaction | `RETAIN` | `test_derive.py` (16 tests), `test_properties.py` (7 Hypothesis property tests). **The charter's own migration hypothesis (§6) flagged this file as a "realignment candidate" — not borne out by this pass's evidence.** Every reset/compaction/fork rule in design §5 is implemented exactly as specified; the only gap found is cross-language canonical *coverage* of the newer LLM-vocabulary round-trips (`SES-F001`), not a defect in `derive.py`'s own logic. |
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

All 11 Python session test files were inventoried by function name (172 test functions across the
suite); `test_derive.py` and `test_properties.py` were additionally read in full given they carry the
LLM-vocabulary round-trip and Hypothesis-property coverage most likely to interact with Layer 02's
recent changes. Deeper line-by-line reading of the remaining 9 files' bodies is **pending the next
pass** — the method's own audit questions (obsolete implementation detail? duplicates canonical
conformance? exercises the real path? deterministic?) are answered provisionally below from function
names, docstrings, and the one-level-deeper read already done on `derive.py`/`properties.py`; nothing
here should be read as a final `KEEP` verdict until each file gets the same full read Layer 01/02 gave
their own suites.

| Test file | Requirement(s) | Current validity (provisional) | Disposition | Reason |
|---|---|---|---|---|
| `test_artifacts.py` | `SES-010` | Names match `ArtifactStore`'s real public API exactly | `KEEP` (provisional) | — |
| `test_compaction.py` | `SES-008` | Names cover supersession, double-projection, empty-log, post-reset — matches design table | `KEEP` (provisional) | — |
| `test_derive.py` | `SES-002`, `SES-006`, `SES-007`, `SES-008` | Read in full this pass; every LLM-vocabulary round-trip (signatures, usage/cost, diagnostics, deferred) has a dedicated test | `KEEP` | — |
| `test_events.py` | `SES-003` | 4 tests confirm the surface is exactly 3 kinds and lifecycle events are excluded | `KEEP` (provisional) | — |
| `test_fork.py` | `SES-006` | 11 tests, including nested-fork-of-fork and fork-local compaction | `KEEP` (provisional) | — |
| `test_log.py` | `SES-001`, `SES-005` | 10 tests, thorough JSON-safety rejection coverage | `KEEP` (provisional) | — |
| `test_plugin_events.py` | `SES-003`, `SES-011`, `SES-012` | 11 tests, covers open-namespace validation and value-identity | `KEEP` (provisional) | — |
| `test_properties.py` | `SES-002`, `SES-006`, `SES-007`, `SES-008` | Read in full this pass; 7 Hypothesis property tests (order preservation, reset-yields-empty, compaction bound, monotonic growth, fork-chain-of-any-depth) | `KEEP` | Real property tests per the method's §7 — a genuine strength, not just unit-test padding |
| `test_request_header.py` | `SES-009` | 7 tests, includes component-reuse (`test_a_stable_component_is_stored_once_across_many_steps`) | `KEEP` (provisional) | Covers the `SES-F001`-flagged canonical gap at the Python-unit level |
| `test_request_header_tools.py` | `SES-009` | 5 tests, includes tool-schema reuse addressing to the same reference | `KEEP` (provisional) | Same note as above |
| `test_reset.py` | `SES-007` | 6 tests, matches design table exactly | `KEEP` (provisional) | — |

No test in this inventory appeared to assert an obsolete implementation detail, duplicate canonical
conformance, or encode a superseded contract — but that conclusion rests on names/docstrings for 9 of
11 files and should be treated as provisional pending the full read.

Python already enforces 100% line coverage for currently-covered core packages (per the method's own
floor); `minion_agent/session/` is inside that covered set (confirmed: all 8 files appear in `src/`
under the package tree exercised by the existing suite runs in Layers 01/02's own gate re-runs).

---

## 7. Missing test / conformance coverage

### Canonical conformance — inventory of all 15 `conformance/session/*.yaml`

| Scenario | Status | Maps to |
|---|---|---|
| `compact-now-then-derive.yaml` | real, passing | `SES-008` |
| `compaction-repeated-and-nested.yaml` | real, passing | `SES-008` |
| `content-signatures-round-trip.yaml` | **unfilled placeholder** | `SES-002`/`SES-009` |
| `deferred-handle-round-trip.yaml` | **unfilled placeholder** | `SES-002` |
| `diagnostic-round-trip.yaml` | **unfilled placeholder** | `SES-002` |
| `event-name-identity-is-by-value.yaml` | real, passing | `SES-011` |
| `fork-ancestry-derivation.yaml` | real, passing | `SES-006` |
| `fork-local-compaction.yaml` | real, passing | `SES-006`/`SES-008` |
| `overlapping-compaction.yaml` | real, passing | `SES-008` |
| `plugin-defined-event-kind.yaml` | real, passing | `SES-003`/`SES-012` |
| `plugin-event-stays-log-only-by-default.yaml` | real, passing | `SES-012` |
| `request-reconstruction-after-target-transform.yaml` | **unfilled placeholder** | `SES-009`/`SES-013` |
| `request-reconstruction-with-artifacts.yaml` | **unfilled placeholder** | `SES-009`/`SES-015` |
| `reset-excludes-prior-surface.yaml` | real, passing | `SES-007` |
| `rich-assistant-message-round-trip.yaml` | **unfilled placeholder** | `SES-002` |

**5 of 15 are unfilled placeholders** (`TO_BE_FILLED`/`TO_BE_BOUND_TO_REAL_PUBLIC_API`/
`TO_BE_PINNED_EXACTLY` markers, confirmed by direct read of each file) despite two of them
(`request-reconstruction-with-artifacts`) being the exact scenario `MINION-003`'s own manifest row
cites as its `tests:` evidence. This is `SES-F001` below. All 5 have real, passing Python-unit-level
coverage already (`test_derive.py`'s round-trip tests, `test_request_header.py`'s reconstruction
tests) — the gap is specifically the missing cross-language canonical evidence, not unverified Python
behavior.

Cross-checked against the frozen design's own originally-planned `session/` scenario list (§8): two
named scenarios (`retained-tail-no-duplicate`, `request-header-component-reuse`) do not appear under
those names in the current directory. `retained-tail-no-duplicate`'s property appears exercised
implicitly by `compaction-repeated-and-nested.yaml`'s `keep: 1` case; `request-header-component-reuse`
has no obvious canonical equivalent, only the Python-unit-level
`test_a_stable_component_is_stored_once_across_many_steps`. Neither is committed as a hard finding
this pass — the design's §8 list is a plan, not an inventory, and scenario consolidation/renaming
during implementation is legitimate — but both are flagged here for a definitive check before this
layer certifies, per the same discipline applied to the two Layer-02 replay scenarios (verify before
concluding, don't assume Outcome A).

Two other planned-list names (`pi-harness-message-projections`, `compaction-estimator-last-valid-usage`,
`compaction-estimator-zero-usage-fallback`) map to `HAR-003`/`HAR-005` — phase 7, out of Layer 03's
scope per §1 — their absence here is expected, not a gap.

### Language-specific tests

- [x] Covered — see §6.

### Property/invariant tests

- [x] `test_properties.py` — 7 Hypothesis tests already exist, matching the method's own suggested
  examples (order preservation, no-shrink, fork-chain-of-any-depth).

### State-machine tests

- [ ] Not evaluated this pass — session log state (lane/leaf tracking) is minimal in Minion's
  architecture; whether a dedicated state-machine test is warranted is deferred to the next pass.

### Concurrency tests

- [ ] Not evaluated this pass. `SessionLog`/`ArtifactStore` are plain Python objects with no internal
  locking — whether concurrent session operations need dedicated coverage (per the method's §7
  suggested list) is an open question for §10 (reliability/operations), not yet reviewed.

### Fuzz tests

- [ ] Not evaluated this pass. Session log decoding (`decode_message`) is a method-suggested fuzz
  target; none exists yet.

### Fault-injection tests

- [ ] Not evaluated this pass.

**§8-14 category reviews (failure model, security, reliability/operations, observability, performance,
public API/serialization, documentation) are not started this pass** — deferred to a follow-up turn,
consistent with how Layer 02 paced its own first pass before remediation.

---

## 15. Findings

| ID | Severity | Classification | Description | Disposition / action |
|---|---|---|---|---|
| `SES-F001` | MEDIUM | `CONTRACT_ASSURANCE_DEFECT` | 5 of 15 `conformance/session/*.yaml` scenarios are unfilled placeholders (`content-signatures-round-trip`, `deferred-handle-round-trip`, `diagnostic-round-trip`, `request-reconstruction-after-target-transform`, `request-reconstruction-with-artifacts`), confirmed by direct read of each file's `TO_BE_FILLED`/`TO_BE_BOUND_TO_REAL_PUBLIC_API`/`TO_BE_PINNED_EXACTLY` markers. `MINION-003`'s own manifest row cites `request-reconstruction-with-artifacts` as its `tests:` evidence — a normative rule currently backed by a placeholder, not a real scenario, exactly the situation the charter's own `CONTRACT_ASSURANCE_DEFECT` definition names ("a normative rule with no executable evidence"). **Not as severe as it could be:** every one of the 5 has real, passing Python-unit-level coverage already (`test_derive.py`'s `test_assistant_message_response_identity_and_diagnostics_round_trip`, `test_replay_signature_fields_round_trip`, `test_usage_cost_and_total_tokens_round_trip`; `test_request_header.py`'s reconstruction tests) — the underlying behavior is verified in Python, only the cross-language canonical evidence is missing. | Open, not fixed this pass. Filling these follows the same pattern that resolved `LLM-F010`: build/extend the `conformance/session` DSL/runner as needed, fill each placeholder from the real object shapes `derive.py`/`request_header.py` already produce, verify thin-runner compliance (no simulated semantics), and submit for the same shared-contract review process before treating any as canonical. Must be repaired before Layer 03 certification per the charter — not risk-register debt. |
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
Parity manifest                          [x]  MINION-002/003 both present, both dispositioned, both cite real (if partly unfilled) test evidence
Canonical conformance                    [ ]  SES-F001 — 5 of 15 session scenarios are unfilled placeholders
Python tests where implemented           [~]  172 test functions inventoried; 2 of 11 files read in full (KEEP); 9 files' dispositions provisional pending full read next pass
Rust tests where implemented             [x]  N/A — Rust session/ not implemented (Phase 2), consistent with the manifest
Property/invariant tests                 [x]  test_properties.py — 7 Hypothesis tests already exist
Concurrency tests where applicable       [ ]  not evaluated this pass
Fault-injection tests where applicable   [ ]  not evaluated this pass
Security review                          [ ]  §9 not started this pass
Reliability review                       [ ]  §10 not started this pass
Observability review                     [ ]  §11 not started this pass
Performance review                       [ ]  §12 not started this pass
Public API review                        [ ]  §13 not started this pass
Documentation                            [ ]  §14 not started this pass; SES-F003 already found under §2/§15
All findings classified                  [x]  SES-F001..F003 classified
No unresolved Pi uncertainty             [x]  none raised this pass
No unresolved parity defect              [x]  none raised this pass (SES-F002 classified CONTRACT_ASSURANCE_DEFECT pending Layer 08)
No unresolved contract-assurance defect  [ ]  SES-F001, SES-F002, SES-F003 all open
Deferred risks recorded                  [ ]  none recorded yet — §10 reliability review, not started, is where session-log deferrals (if any) would surface
```

---

## 17. Certification result

**Result:** `IN_AUDIT`

This is a first-pass survey, not a remediation or certification pass — consistent with the standing
sequencing rule (one assurance layer at a time; Phase 5/XFORM/next-layer work does not start ahead of
its turn) and with how Layer 02 itself began. §1-7 are complete with real grounding: the frozen design
§5/§6/§8 was read directly, `spec/session.md` was checked against it and found incomplete (`SES-F003`),
`MINION-002`/`MINION-003` were traced to their manifest rows, pinned Pi session source was read to
confirm the storage-architecture divergence is intentional and scoped correctly, all 8 Python modules
were read and inventoried, all 11 test files were inventoried (2 read in full), and all 15 canonical
session scenarios were read and classified real-vs-placeholder.

Three real findings resulted, all `CONTRACT_ASSURANCE_DEFECT`, none `PI_PARITY_DEFECT` or
`PI_BEHAVIOR_UNCERTAIN`:

- **`SES-F001`** (MEDIUM): a third of the canonical session scenarios are unfilled placeholders,
  including the exact one `MINION-003`'s manifest row cites as evidence. Lower-risk than it could be —
  Python-unit-level coverage of the same behavior already exists for all 5.
- **`SES-F002`** (HIGH): the frozen design's own log-only event vocabulary (`run/*`/`turn/*`) doesn't
  match what `session/events.py` declares (`turn/*`/`step/*`, no `run/*`), and direct inspection of
  `agent_loop/driver.py` shows the mismatch isn't cosmetic — the event literally named `turn/start` is
  emitted around a multi-request loop, which is exactly the Run/Turn conflation design §6 explicitly
  prohibits by name. This is the most significant finding of the pass and sits right at the Layer
  03/Layer 08 boundary; flagged here because the vocabulary itself is Layer-03-owned, with an explicit
  note that a full behavioral verdict (is `_run_turn`'s actual control flow Pi-correct, independent of
  its event names?) belongs to Layer 08's own audit.
- **`SES-F003`** (LOW): `spec/session.md` doesn't restate the frozen design's log-only kind list or
  its by-value event-identity rule, both of which conformance already depends on (or will, once
  `SES-F002` is resolved).

**Migration hypothesis correction:** the charter's own §6 flagged "session derive/reconstruction" as a
"realignment candidate." This pass's actual read of `derive.py` (and its 16+7 dedicated tests) found no
defect in its logic — every reset/compaction/fork rule is implemented exactly as design §5 specifies.
The hypothesis is recorded as **not borne out by evidence** rather than silently dropped, per the
charter's own instruction that a starting hypothesis is not a substitute for audit evidence.

**Not started this pass, by design:** §8-14 category reviews, remediation of any of the three
findings, and the certification decision itself. Also not started: Layer 04 (XFORM), Rust
implementation for this layer (Phase 2, not yet due), and any Phase-5 work.

**Follow-up dependencies:**

1. Resolve `SES-F001`: build/extend `conformance/session`'s DSL/runner as needed and fill the 5
   placeholder scenarios from real object shapes, following the same review discipline that closed
   `LLM-F010` (thin-runner verification, language-neutrality check, shared-contract review).
2. Resolve `SES-F002`: determine the correct log-only event vocabulary (add `run/*`? rename
   `turn/*`↔`step/*`? something else the design doesn't yet state precisely enough to decide alone) —
   likely needs coordination with whoever picks up Layer 08, since the emission logic lives in
   `agent_loop/driver.py`. Do not silently rename without confirming the actual control-flow semantics
   are Pi-correct first; a naming fix over incorrect behavior would hide the real defect.
3. Resolve `SES-F003` once `SES-F002` settles the correct vocabulary — extending `spec/session.md`
   with a vocabulary this pass just found to be wrong would create more contract-assurance debt, not
   less.
4. Verify (don't assume) whether `retained-tail-no-duplicate` and `request-header-component-reuse`
   (named in the design's original §8 scenario list, not present as separate files today) are
   genuinely covered by existing scenarios/tests or represent real additional gaps.
5. Complete §6's full per-file test read (9 of 11 files still provisional), then §8-14's category
   reviews, before this layer is eligible for a certification decision.
