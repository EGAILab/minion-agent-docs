# Session + Artifacts — Fidelity Assurance & Certification

**Layer ID:** `03`  
**Status:** `CERTIFIED`  
**Rust implementation completion (2026-08-24):** `IMPLEMENTED` on branch
`feat/rust-layer-03-session-artifacts` at `31ed6698a1e4a9f5d3134d2c2b1788f920ceb330`, consuming the
certified contract at `minion-agent@cda6b5042e678974a43b8dc0fc6ce1c8ade73d88`. The typed Rust
`session` module supplies value-keyed open event names, atomic append/sequence allocation, complete
Layer-02 message persistence, surface projection, immutable fork ancestry, reset and compaction,
SHA-256 artifacts, and request-header reconstruction. The thin Rust adapter enumerates all 17
canonical Session files and executes 16 through the real typed implementation; only
`request-reconstruction-after-target-transform.yaml` remains explicitly deferred to Layer 04, with
no Agent or XFORM simulation. Implementation review found and remediated future-boundary fork
leakage and a compaction linearization race before acceptance. Final Rust evidence: 7 focused
Session tests; the canonical test executes all 16 applicable scenarios; full workspace total 126
tests; `cargo fmt --check`, strict all-target/all-feature Clippy, rustdoc warnings-as-errors, and
`xtask conformance verify` all pass. No shared-contract change was required.
**Fresh Rust implementation-owner re-review (2026-08-24):** `APPROVED` for corrected candidate
`minion-agent@cda6b5042e678974a43b8dc0fc6ce1c8ade73d88`. Rust independently reran the original
rejection probes plus positive typed-shape cases: complete assistant/tool-result fields validate,
unknown fields remain rejected, role-incompatible appends are rejected, all four closed content
variants validate, invalid/cross-variant blocks are rejected, and fractional timestamps remain valid
language-neutral numbers. The corrected runner remains thin. Focused schema/Session conformance,
the full Python suite at 100% configured coverage, `ruff`, and focused `mypy` all pass. No new
`CONTRACT_ASSURANCE_DEFECT`, `PI_PARITY_DEFECT`, or `PI_BEHAVIOR_UNCERTAIN` was found. Rust Session
remains `EXPLICITLY DEFERRED BY PLAN`, non-blocking. **This verdict was independently re-verified
before being accepted, not trusted on the report alone:** the reviewed SHA was confirmed exact; all
13 of Rust's own listed re-test cases were reconstructed from scratch and reproduced directly against
the schema; the full Python suite was re-run fresh with coverage enabled (724 passed/42 xfailed/0
failed, 100.00% coverage — exact match); `ruff`/`mypy` re-run clean. Layer 03 is **`CERTIFIED`**.
Full evidence, including the preserved initial rejection, is in `03-session-artifacts-rust-review.md`.

**Rust implementation-owner review (2026-08-23):** `REJECTED — CONTRACT_ASSURANCE_DEFECT`, reviewing
`minion-agent@3d6ffa4` / `minion-agent-docs@c273df1`. The formal review is recorded in
`03-session-artifacts-rust-review.md`. It independently approved the `SES-F002` mixed Session/Agent
boundary, the `SES-F003` by-value identity/XFORM clarification, and `MINION-003` traceability, but
found four shared schema/evidence defects: incomplete `assistantDetail`, incomplete
`toolResultDetail`, role-incompatible `step.append` inputs that the Python runner silently ignored,
and a non-discriminated `contentBlock` definition that admitted structurally impossible variants.
Rust Session remains `NOT_IMPLEMENTED — planned Phase 2`, explicitly non-blocking under the adopted
separate-status workflow; the shared-contract defects were blocking.

**Remediation (2026-08-24, sixth pass):** all four defects independently reproduced against the
schema before being accepted (not taken on the reviewer's word), then fixed narrowly in
`minion-agent@cda6b50`: `assistantDetail`/`toolResultDetail` now require and expose
`provider`/`model`/`timestamp`/`error_message` and `tool_call_id`/`timestamp` respectively, made
genuinely scriptable through `step.append` (not just observable) per Rust's explicit remediation
request; `step.append` now uses `allOf`/`if`/`then` conditionals so a role can no longer carry
another role's fields; `contentBlock` is now a `type`-discriminated `oneOf` with four closed variants,
including the `data`/`reference` exclusive-or `ImageBlock.__post_init__` actually enforces. Every one
of Rust's own listed adversarial probes was independently re-run against the corrected schema and
confirmed to now behave correctly. Full Python suite re-run fresh: 724 passed/42 xfailed/0 failed
(unchanged counts), `ruff`/`mypy` clean. **This is a corrected candidate sent back for a fresh Rust
implementation-owner review — the prior rejection is not treated as approval after a fix, and this
pass does not self-approve the correction.**

**Governance correction (2026-08-23, recorded transparently, not erased):** this record briefly
carried `Status: CERTIFIED` after a fourth pass resolved `SES-F001`/`SES-F002`/`SES-F003`. That
conclusion was **premature**: `SES-F001` and `SES-F003` changed shared-contract files
(`conformance/schema/session-scenario.schema.json`, `conformance/session/*.yaml`,
`pi-parity-manifest.yaml`, `spec/session.md`) without the required affected-implementation-owner
review — the same shared-contract reviewer rule Layer 02's `LLM-F010` cycle enforced
(`process/implementation-conformance-workflow.md` §15/§4.6). The governance omission was caught before
freeze, not after — this is treated as positive assurance evidence, not a discarded result. **None of
the underlying Python/shared-semantic work is being reopened or distrusted; the missing piece is
exclusively the cross-language review gate.** Status returned to `IN_AUDIT`. Remaining gate: **formal
affected Rust implementation-owner review of the finalized Layer-03 shared contract**
(`assurance/layers/03-session-artifacts-rust-handoff.md`, prepared and pushed this pass, reviewing
`minion-agent@3d6ffa4` + `minion-agent-docs@92579ee`). Python's own semantic-owner review of that same
diff is `APPROVED`, not self-extended to a cross-language approval (§17 has the full review).  
**Audit date:** 2026-08-23/24 (seven passes: §1-7 first, §8-14 second (surfacing `RISK-001`),
`SES-F001` remediated third, `SES-F002`/`SES-F003` resolved fourth via a dedicated Pi re-audit
(`packages/agent/src/types.ts:428-443`) and Session/Agent ownership matrix, fifth pass corrected the
certification governance itself and sent the finalized contract for formal Rust implementation-owner
review, sixth pass received Rust's `REJECTED — CONTRACT_ASSURANCE_DEFECT` verdict, independently
reproduced all four reported defects before accepting them, fixed each narrowly in
`minion-agent@cda6b50`, and sent the corrected candidate back for a fresh review, and this seventh
pass received Rust's fresh `APPROVED` verdict, independently re-verified it (exact SHA match, all 13
of Rust's own re-test cases reproduced, full suite/coverage/`ruff`/`mypy` re-run clean) before
accepting it, and certified the layer.)  
**Auditor:** Claude (Python-driven, per adopted workflow)  
**Python status:** `IMPLEMENTED` — semantic-owner review `APPROVED`, cross-language review `APPROVED`  
**Rust status:** `IMPLEMENTED` — `minion-agent-rust/crates/minion-agent/src/session/mod.rs`, with
implementation-specific tests and the shared canonical Session runner at commit `31ed669`.

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
| `SES-001` | Append-only, sequence-numbered, JSON-validated at append; a rejected append leaves no trace | design §5, `spec/session.md`, `MINION-002` | `log.py::SessionLog.append`/`_check_json_safe` | `session::Session::append`/`append_raw` | Python tests + Rust `tests/session.rs` | `PASS` |
| `SES-002` | Model-visible means logged: request history reconstructable from committed state | design §5, `MINION-002` | `derive.py::derive_messages` + `request_header.py` | `session::Session::derive_messages`/`reconstruct_header` | Python tests + Rust canonical Session runner | `PASS` |
| `SES-003` | Two-tier event vocabulary: surface (`user/message`/`assistant/message`/`tool/result`) vs log-only; open namespace, name is the identity | design §5, `spec/session.md` | `events.py::EventKind`/`CORE_SURFACE_KINDS`/`is_surface`/`validate_event_name` | `session::EventKind` + `Session` surface set | shared canonical plugin-event scenarios in Python and Rust | `PASS` |
| `SES-004` | Log-only lifecycle/fidelity/operations kinds are fully and correctly enumerated | design §5 (explicit list) | `events.py::EventKind` (partial — see `SES-F002`) | not implemented | none dedicated | `GAP — SES-F002` |
| `SES-005` | Append pipeline: validate → atomic seq allocation → committed publication | `spec/session.md`, design §5 (implicit in log.py) | `log.py::append` | `session::Session::append` under one event mutex | Python tests + Rust concurrent append test | `PASS` |
| `SES-006` | `fork(source, at)`: references not copies, boundary fixed at fork time, later writes on either side stay private | design §5 table, `spec/session.md`, `MINION-002` | `operations.py::fork`, `derive.py::_derive`'s ancestry walk | `session::Session::fork`/`derive_until` | Python tests + Rust focused/canonical fork tests | `PASS` |
| `SES-007` | `reset()`: identity preserved, excludes all surface at-or-before, history stays readable | design §5 table, `spec/session.md` | `operations.py::reset`, `derive.py::effective_surface`/`_derive` | `session::Session::reset`/`derive_until` | shared reset scenario in Python and Rust | `PASS` |
| `SES-008` | Compaction: supersedes an effective range with summary + retained-tail provenance; no double-inclusion under repeated/overlapping/nested/fork-local compaction | design §5 table, `operations.py` docstring, `spec/session.md` | `operations.py::compact`, `derive.py::_derive`'s compaction branch | `session::Session::compact`/`derive_until` | shared compaction scenarios in Python and Rust | `PASS` |
| `SES-009` | Content-addressed request header: components stored by hash, composition logged as references, dispatch and reconstruction use the same canonical join | design §5, `spec/session.md` | `request_header.py::assemble_system`/`record_header`/`reconstruct_header`/`reconstruct_tools` | `session::record_header`/`reconstruct_header`/`assemble_system` | shared request-header scenarios in Python and Rust | `PASS` |
| `SES-010` | Artifacts holding model-visible content are never deleted; no removal API exists | design §5, `artifacts.py` docstring, `MINION-003` | `artifacts.py::ArtifactStore` (no delete method) | `session::ArtifactStore` (no removal API) | Python tests + Rust focused/canonical artifact tests | `PASS` |
| `SES-011` | Event name is the identity, compared by value — not by enum/object identity | design §5 "two consequences" | `events.py` (`EventName = str`; `is_surface` compares `event.kind in surface`) | `session::EventKind` value equality/hash | shared identity scenario + Rust focused test | `PASS` |
| `SES-012` | An open logging namespace is not an open surface: declaring/appending a plugin event name does not by itself admit it to model history | design §5 | `log.py`/`events.py` (`surface_kinds` parameter, defaults to `CORE_SURFACE_KINDS`) | `session::Session` explicit surface set | shared plugin-event scenarios in Python and Rust | `PASS` |
| `SES-013` | Session/log projection approximates Pi's `AgentMessage -> Message` conversion; target-model transformation is a distinct, later stage | design §5 "Relationship to Pi's message projection" | `derive.py` (scope boundary only) | N/A | `request-reconstruction-after-target-transform.yaml` — verified genuinely `DEFERRED TO LAYER 04` (`SES-F001`'s investigation, §7), not filled | `DOCUMENTED` |
| `SES-014` | Session log-only naming must track Pi's Run/Turn vocabulary; observable `turn` MUST NOT mean a multi-request run | design §6 (explicit prohibition), cross-referenced by §5 | `events.py::EventKind.TURN_START`/`TURN_END`/`STEP_START`/`STEP_END`; emitted by `agent_loop/driver.py` | not implemented | none dedicated; driver.py inspection contradicts the rule — see `SES-F002` | `GAP — SES-F002` |
| `SES-015` | `MINION-003`: content-addressed artifacts are a permitted storage divergence only when model-visible bytes stay equivalent to what was dispatched | `MINION-003`, design §5 | `request_header.py` + `artifacts.py` | `session::ArtifactStore` + canonical header composition/reconstruction | shared artifact/header scenarios in Python and Rust | `PASS` |

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

### `SES-F002` Pi audit and ownership matrix (this pass)

**Scope of this pass:** determine which part of the run/turn/step event-vocabulary mismatch is
Session-owned (Layer 03) versus Agent-owned (Layer 08), and whether the Layer 03/08 contract boundary
is coherent — not to fix Layer 08's own behavior. No `agent_loop/`, `agent/`, or Rust code was
touched this pass.

**Pi re-audited directly, not re-trusted from the prior pass's wording.** Pinned commit
`b7bb00b936dbe21b8e160b3e89efdec361846699`.

- `packages/agent/src/types.ts:428-443` — `AgentEvent`, Pi's complete lifecycle notification union,
  read in full:
  ```text
  agent_start                                    // Agent lifecycle
  agent_end        { messages }
  turn_start                                      // Turn lifecycle — "a turn is one assistant
  turn_end          { message, toolResults }      //   response + any tool calls/results" (Pi's own comment, verbatim)
  message_start     { message }                   // Message lifecycle — user/assistant/toolResult
  message_update    { message, assistantMessageEvent }  // streaming only
  message_end       { message }
  tool_execution_start  { toolCallId, toolName, args }
  tool_execution_update  { ...,  partialResult }
  tool_execution_end     { ..., result, isError }
  ```
  Pi has **no third tier between "turn" and "message"/"tool_execution."** There is no Pi concept
  resembling Minion's "step."
- `packages/agent/src/harness/session/types.ts` and `session.ts` (both already read in full in the
  prior pass) — re-checked specifically for any of the above nine event-type strings: **zero matches.**
  Pi's persisted `SessionStorage` (`Entry`/`LaneRecord` types) never stores `agent_start`/`turn_start`/
  `message_start`/`tool_execution_start` at all. `AgentEvent` is a separate, ephemeral pub/sub
  notification stream (`Agent.subscribe()`) for live UI updates — structurally disjoint from what Pi's
  Session persists. The closest persisted-and-lifecycle-adjacent Pi record is `StepAttemptRecord`
  (`step: "assistant" | "branch_summary" | "compaction"`, for crash-recovery replay), which is part of
  the durable-AgentHarness surface already recorded as `RISK-001` (Phase 9), not part of `AgentEvent`.
- `spec/agent.md` (already frozen, read fresh this pass): "A run is one high-level prompt/continue
  invocation. A turn is one assistant response plus tool calls/results caused by it," with the
  prompt-run order `agent_start, turn_start, ..., turn_end` — matches Pi's source exactly, independent
  confirmation.
- `minion-agent-python/src/minion_agent/agent_loop/driver.py:1-9` (module docstring, re-read this
  pass): **"A step is one model request plus the tools it calls. A turn is zero or more steps."** This
  is Minion's own, explicit, deliberate internal terminology — not an accidental drift. It defines
  "turn" as a whole multi-request run, which is exactly what design §6 says an implementation
  "MUST NOT" do to the *observable* `turn`. The definition lives entirely inside `driver.py` — a
  Layer-08 file — not in any `session/*.py` module.
- `pi-parity-manifest.yaml`: **`AG-001`** (phase 3, `pi: packages/agent/src/agent-loop.ts::runAgentLoop`,
  `rule: agent_start -> turn_start -> initial prompt message lifecycle`, `python: .../driver.py
  (rewrite)`, `disposition: adopted`) and **`AG-004`** (phase 3, `surface: turn definition/order`,
  `rule: one assistant response + resulting tool results; turn_end then prepareNextTurn then
  shouldStopAfterTurn then steering`, `disposition: adopted`) **already exist, already cite the
  correct Pi vocabulary, and already target `driver.py` for remediation** — found by direct manifest
  search, not assumed absent. Their conformance evidence
  (`conformance/agent/initial-prompt-order-after-turn-start.yaml`) is a real, non-placeholder-named
  scenario file that is itself still `TO_BE_FILLED` and `xfailed` (confirmed by running it:
  `1 xfailed`) — i.e., **the run/turn ordering and naming concern this pass investigated is not an
  undiscovered gap. It is a known, already-tracked, already-dispositioned Agent-loop (`AG-###`, phase
  3) requirement, awaiting Layer 08's own implementation/assurance pass**, exactly as the charter's
  audit order predicts (item 8 comes after item 3).

**Ownership matrix:**

| Vocabulary item | Pi source | Producer | Consumer | Persisted in Pi session? | Persisted in Minion session? | Reconstructed by Session? | Needed for Session projection? | Layer owner | Current status | Action |
|---|---|---|---|---|---|---|---|---|---|---|
| `agent_start`/`agent_end` | `types.ts:430-431` | Pi `Agent` class | UI/`Agent.subscribe()` | NO (ephemeral) | Emitted as `TURN_START`/`TURN_END` (misnamed relative to Pi; scoped to the whole multi-step run) | NO — log-only, excluded from surface | NO | `AGENT` | `AG-001`, adopted, `driver.py (rewrite)`, xfailed placeholder scenario | Layer 08's own future remediation; no Session action |
| `turn_start`/`turn_end` | `types.ts:433-434` | Pi `Agent` class | UI/`Agent.subscribe()` | NO (ephemeral) | Emitted as `STEP_START`/`STEP_END` (misnamed relative to Pi, though behaviorally the correct one-request-plus-tools granularity) | NO | NO | `AGENT` | `AG-001`/`AG-004`, adopted, same xfailed scenario | Layer 08's own future remediation; no Session action |
| `message_start`/`update`/`end` | `types.ts:436-439` | Pi `Agent` class | UI (live streaming) | NO (ephemeral; the *settled* message becomes a session Entry separately) | No direct equivalent log-only event; `ASSISTANT_CHUNK` is the closest (streaming fidelity, log-only) | Settled surface messages: YES (`SES-002`, `PASS`); streaming notification itself: NO | Settled messages: YES, already correct | `SHARED BOUNDARY` — settled-message persistence is `SESSION`; live notification is `AGENT` | Session's portion already `PASS` | None — Session's obligation already met |
| `tool_execution_start`/`update`/`end` | `types.ts:441-443` | Pi `Agent`/tool pipeline | UI (live progress) | NO (ephemeral; `ToolStartedRecord` is a separate crash-recovery mechanism, `RISK-001`) | `TOOL_CALL` (log-only, single event) covers the request side; `TOOL_RESULT` (surface) covers the settled side | Settled `TOOL_RESULT`: YES, correct | Settled results: YES, already correct | `SHARED BOUNDARY` — settled-result persistence is `SESSION`; execution-progress notification is `TOOL`/`AGENT` (Layer 06/08) | Session's portion already `PASS` | None — Session's obligation already met |
| `session/forked`, `session/reset`, `compaction`, `request/header` | N/A — Minion-owned (`MINION-002`/`MINION-003`) | `session/operations.py`, `session/request_header.py` | `derive_messages`, reconstruction | N/A | YES, with real interpreted `data` (`source`/`boundary`; `summary`/`superseded_through`/`retained`; component/tool references) | YES — these are the only log-only kinds `derive_messages` itself reads | YES | `SESSION` | `SES-006`/`SES-007`/`SES-008`/`SES-009`, all `PASS` | None — already correct, unaffected by this finding |
| `causes`/origin metadata on `TURN_START`/`TURN_END`'s `data` | Agent-loop-internal (matches existing `AG-###` conformance names `causes-preserved-under-claim-all`, `origin-survives-one-at-a-time`) | `agent_loop/driver.py` | Agent-loop's own continuation logic | NO (ephemeral in Pi) | Stored as opaque JSON-safe `data` on a log-only event — Session stores it uniformly, never interprets it | NO | NO | `AGENT` | Existing `AG-###` scenarios | Session's storage mechanism already sufficient (any JSON-safe payload); semantic correctness is Layer 08's |

**Session-owned portion, independently re-confirmed correct, not re-asserted:** `CORE_SURFACE_KINDS`
is exactly `{user/message, assistant/message, tool/result}` (`test_events.py`,
`test_plugin_events.py`); the by-value event-identity rule is enforced by `is_surface()`'s membership
check and independently conformance-pinned (`event-name-identity-is-by-value.yaml`); JSON-safety,
sequencing, and the three real Session-owned log-only kinds (`session/forked`, `session/reset`,
`compaction`) plus `request/header` are all correct and already `PASS` in §4's requirement table. None
of this required any change this pass.

**Session runner thinness, re-audited:** `tests/conformance/session_runner.py` (including this pass's
own `SES-F001` extensions) constructs real `SessionLog`/`ArtifactStore`/message objects, appends/reads
through real public APIs, and normalizes real returned attributes — confirmed by re-reading the whole
file this pass. It never emits `TURN_START`/`STEP_START`/`agent_start`-style events, never simulates
Agent-loop ordering, and never fabricates cause/origin data. **No Agent simulation exists in the
Session runner.**

**Verdict: Outcome A — mixed boundary, no Layer-03 defect remains.** Session-owned stored/
reconstruction semantics are already correct and complete. The mismatch this finding originally
described concerns Agent run/turn/step lifecycle *emission and naming* — entirely `agent_loop/
driver.py`'s own concern, already tracked under `AG-001`/`AG-004` with a real (if still-placeholder)
conformance scenario and a `(rewrite)` note anticipating exactly this correction. Session does not
need to synthesize, reconstruct, or interpret this vocabulary to do its own job, and already treats
every log-only event — regardless of what any producer chooses to name it — uniformly and correctly.

### Fresh placeholder recount (this pass, not copied from prior arithmetic)

Independently re-run against the live repository, not reused from either prior pass's count:

```text
$ ls conformance/session/*.yaml | wc -l
17

$ for f in conformance/session/*.yaml; do
    grep -q "TO_BE_FILLED\|TO_BE_BOUND\|TO_BE_PINNED" "$f" && echo "PLACEHOLDER: $f"
  done
PLACEHOLDER: request-reconstruction-after-target-transform.yaml
```

```text
Filled current-layer (Session) scenarios:  16
Layer-04-deferred scenarios:                1  (request-reconstruction-after-target-transform.yaml)
Layer-08-deferred scenarios (within conformance/session/):  0
Remaining true Layer-03 placeholders:       0
```

No scenario lives in `conformance/session/` today with its executable portion Layer-08-deferred — the
one scenario this pass's investigation connects to Layer 08 (`initial-prompt-order-after-turn-start`)
is cleanly filed in `conformance/agent/`, a different canonical family, and was not touched, filled,
or moved this pass.

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
| `SES-F001` | MEDIUM | `CONTRACT_ASSURANCE_DEFECT` — **RESOLVED**. Full lifecycle: Python self-review `RESOLVED` (incomplete) → Rust implementation-owner review `REJECTED` (4 defects, confirmed real) → fixed in `cda6b50` → fresh Rust implementation-owner review `APPROVED` | **Corrected count (§7): 6, not 5, of 17 `conformance/session/*.yaml` scenarios were unfilled placeholders** (`content-signatures-round-trip`, `deferred-handle-round-trip`, `diagnostic-round-trip`, `request-reconstruction-after-target-transform`, `request-reconstruction-with-artifacts`, `rich-assistant-message-round-trip` — the first pass's own count omitted the last of these, corrected honestly rather than silently). `MINION-003`'s own manifest row cited `request-reconstruction-with-artifacts` as its `tests:` evidence while it was still a placeholder — a normative rule backed by no real scenario, exactly the situation the charter's own `CONTRACT_ASSURANCE_DEFECT` definition names. Two further gaps of the identical shape were confirmed (not assumed) this pass: the design's own originally-planned `retained-tail-no-duplicate` and `request-header-component-reuse` scenarios had never been created under any name. All 8 had real, passing Python-unit-level coverage already, so none were unverified Python behavior — only cross-language canonical evidence was missing. | **Fixed and re-verified this pass.** One of the 8 (`request-reconstruction-after-target-transform`) was investigated first, not assumed fixable: confirmed via direct repository search (no `transform`/`xform` module exists anywhere in `minion-agent-python/src/`) that it is genuinely Layer-04-dependent — filling it now would mean the runner simulating XFORM semantics, the exact thin-runner violation this methodology forbids. Reclassified `DEFERRED TO LAYER 04, non-blocking`, matching the two Layer-02 replay scenarios' own Outcome A (§7 has the full investigation). **The remaining 7 were fixed:** extended `conformance/schema/session-scenario.schema.json` (new `contentBlock`/`usage`/`cost`/`diagnostic`/`diagnosticError`/`deferredHandle`/`toolStub`/`assistantDetail`/`toolResultDetail` `$defs`, a richer `step.append` accepting content blocks/usage/diagnostics/deferred/api/response identity/tool-result fields, a new `record_header` step, and `expect_assistant_details`/`expect_tool_result_details`/`expect_reconstructed_header`/`expect_artifact_count` top-level assertions — all additive, the pre-existing `{role, text}`-only shape still works unchanged, confirmed by re-running the original 10 real scenarios before writing any new content) and `tests/conformance/session_runner.py` (real object construction on the input side, real-attribute-only normalization on the output side, mirroring the `LLM-F010` pattern exactly). Filled the 5 placeholders and authored the 2 missing scenarios. **Verified, not just asserted:** an independent throwaway script (not reusing any authored scenario) constructed a fully-unset `AssistantMessage`/`ToolResultMessage` directly and confirmed every optional field normalizes to `None`, never a fabricated value. `pi-parity-manifest.yaml`'s `MINION-003` row updated to also cite `request-header-component-reuse`. Full suite re-run fresh: 724 passed/42 xfailed/0 failed (up from 715/47 — the exact `+9`/`-5` the 7 newly-real scenarios predict, verified arithmetically before trusting it), `ruff` clean, `mypy` clean on `session_runner.py` (checked alongside a `src/` file, matching the project's own `mypy.ini` scoping and `LLM-F010`'s precedent; `test_session_conformance.py`'s pre-existing `yaml`-stub gap is unrelated and outside the project's configured mypy scope). **This Python self-review's `RESOLVED` conclusion was incomplete** — Rust's independent implementation-owner review of this exact commit (`3d6ffa4`) found four real schema defects the self-review missed: `assistantDetail`/`toolResultDetail` omitted `provider`/`model`/`timestamp`/`error_message`/`tool_call_id` under `additionalProperties: false` (a Rust implementation could drop or fabricate these frozen fields and still pass); `step.append` admitted role-incompatible field combinations the runner silently ignored rather than rejected; `contentBlock` was not type-discriminated, admitting a text block with no text, an image with neither or both of `data`/`reference`, and cross-variant field mixing. Verdict: `REJECTED — CONTRACT_ASSURANCE_DEFECT`, recorded in full in `03-session-artifacts-rust-review.md`. All four independently reproduced against the schema before being accepted, then fixed narrowly in `cda6b50`: the two message-detail shapes now require and expose every previously-missing field, made genuinely *scriptable* through `step.append` (not just observable) per Rust's explicit request; `step.append` now uses `allOf`/`if`/`then` role-conditional restrictions; `contentBlock` is now a `type`-discriminated `oneOf` with four closed variants including the image-source exclusive-or `ImageBlock.__post_init__` enforces. Every one of Rust's own listed adversarial probes was independently re-run against the fix and confirmed correct. Full suite re-run fresh: 724 passed/42 xfailed/0 failed (unchanged), `ruff`/`mypy` clean. **Fresh Rust implementation-owner review of `cda6b50`: `APPROVED`** — reran the original rejection probes plus new positive cases (complete `assistantDetail`/`toolResultDetail` validate, an unknown field on either remains rejected, fractional timestamps remain valid), confirmed the corrected runner stays thin, and reran schema/Session conformance/full suite/`ruff`/`mypy`, all passing at 100% configured coverage. No new `CONTRACT_ASSURANCE_DEFECT`, `PI_PARITY_DEFECT`, or `PI_BEHAVIOR_UNCERTAIN`. **Independently re-verified this pass, not accepted on the report alone:** SHA confirmed exact (`cda6b5042e678974a43b8dc0fc6ce1c8ade73d88`), all 13 of Rust's own listed re-test cases independently reproduced (all correct), full suite re-run fresh with coverage enabled (724 passed/42 xfailed/0 failed, 100.00% coverage, matching exactly), `ruff`/`mypy` re-run clean. `SES-F001` is `RESOLVED`, cross-language approved. |
| `SES-F002` | ~~HIGH~~ — **downgraded to informational** | ~~`CONTRACT_ASSURANCE_DEFECT`~~ — **Outcome A: no Layer-03 defect.** See the full ownership matrix and Pi re-audit (§7, "`SES-F002` Pi audit and ownership matrix"). | The frozen design's own §5 log-only event list names `run/start`, `run/end`, `turn/start`, `turn/end`; `session/events.py`'s actual `EventKind` has `TURN_START`/`TURN_END` and `STEP_START`/`STEP_END`, and `agent_loop/driver.py` emits `TURN_START`/`TURN_END` around a multi-request loop and `STEP_START`/`STEP_END` around a single request-plus-tools — exactly the Run/Turn conflation design §6 prohibits by name. This pass re-audited Pi directly (`packages/agent/src/types.ts:428-443`'s `AgentEvent` union) rather than re-trusting the prior pass's design-doc-only reading, and found: Pi's `agent_start`/`turn_start`/`message_*`/`tool_execution_*` vocabulary is an **ephemeral UI-notification stream, structurally separate from Pi's persisted `SessionStorage`** (confirmed: zero occurrences of any of those event-type strings in `session.ts`/`types.ts`'s `Entry`/`LaneRecord` definitions). Session never needs to store, reconstruct, or interpret this vocabulary to do its own job — it treats every log-only event uniformly regardless of name. The actual mismatch (`driver.py`'s own docstring: "A step is one model request... A turn is zero or more steps," redefining observable `turn` exactly as design §6 forbids) lives entirely inside `agent_loop/driver.py`, a Layer-08 file. | **Resolved this pass by re-scoping, not by code change.** `pi-parity-manifest.yaml` already carries `AG-001` (phase 3, `agent_start -> turn_start -> initial prompt message lifecycle`, `python: driver.py (rewrite)`, `disposition: adopted`) and `AG-004` (phase 3, `turn definition/order`, `disposition: adopted`) — found by direct search, not assumed absent — with real (if still-placeholder, `xfailed`-confirmed) conformance evidence (`initial-prompt-order-after-turn-start.yaml`). The run/turn naming-and-ordering concern this finding raised was never an undiscovered gap; it is already a known, dispositioned, Agent-loop-owned requirement awaiting Layer 08's own implementation/assurance pass, exactly matching the charter's audit order (item 8 after item 3). **Layer-03 portion: RESOLVED/VERIFIED** (Session's stored/reconstruction semantics were already correct and needed no change). **Remaining executable lifecycle evidence: DEFERRED TO LAYER 08**, owner `AG-001`/`AG-004`. **Layer-03 certification impact: NON-BLOCKING.** No `session/*.py` or `agent_loop/*.py` file was touched to reach this disposition — this is a boundary-scoping correction, not an implementation fix. `spec/session.md` updated (`SES-F003`) to state the boundary explicitly so a future audit doesn't re-raise this as a Session finding. |
| `SES-F003` | LOW | `CONTRACT_ASSURANCE_DEFECT` — **RESOLVED** | `spec/session.md` (originally 4 short paragraphs) restated design §5's append/surface/fork/reset/compaction rules but never mentioned the explicit by-value event-name-identity rule (present in frozen design §5, independently conformance-pinned by `event-name-identity-is-by-value.yaml`), and said nothing about the Session/Agent/XFORM ownership boundary `SES-F002`'s investigation resolved this pass. It was blocked on `SES-F002` deliberately: writing spec text about a log-only vocabulary before knowing who owns it risked baking the wrong ownership into the spec. | **Fixed once `SES-F002`'s ownership was settled, not before.** `spec/session.md` now states the by-value event-identity rule explicitly, and adds an explicit boundary paragraph: Session owns the log itself, the surface/log-only classification, and the specific log-only kinds its own operations define (`session/forked`, `session/reset`, `compaction`, `request/header`); whatever else a producer appends as log-only data is stored and classified uniformly, without Session asserting ownership of its meaning — deliberately **not** a run/turn/step vocabulary list, since `SES-F002` established that vocabulary is Agent-owned. A third paragraph states the XFORM boundary explicitly (session projection ends at the Layer 02 vocabulary; target-model transformation is a distinct, later stage), matching design §5's own "Relationship to Pi's message projection" text, previously stated only in the frozen master and not restated here. This is a `spec/**` shared-contract change: per the established review rule, it is not treated as unconditionally closed — it is available for the same broader review `LLM-F010`-style shared-contract changes received, though as a clarifying, non-testable boundary statement (no new conformance requirement, no new Python/Rust behavior) its risk is low. `SES-F003` is `RESOLVED` for Layer-03 purposes. |

No `PI_PARITY_DEFECT` and no `PI_BEHAVIOR_UNCERTAIN` findings this pass — every finding traces to an
internal inconsistency in Minion's own frozen contract (design vs. spec vs. implementation vs.
conformance), not to an unresolved question about what Pi itself does or a confirmed behavioral
mismatch against Pi.

---

## 16. Certification gate

```text
Design alignment                         [x]  §5/§6 re-traced against Pi source directly this pass; SES-F002's apparent design-vs-implementation mismatch resolved as a scope misattribution, not a Session defect (see ownership matrix, §7)
Pi parity                                [x]  MINION-002/003 are intentional divergences by the manifest's own disposition; no Pi-visible behavioral mismatch found in Session; the only real Pi-derived mismatch (run/turn naming) is Agent-owned, already tracked (AG-001/AG-004)
Normative spec                           [x]  spec/session.md updated this pass (SES-F003 resolved): by-value event-identity rule stated explicitly; Session/Agent/XFORM boundary stated explicitly
Parity manifest                          [x]  MINION-002/003 both present, both dispositioned, both cite real test evidence; AG-001/AG-004 confirmed to already carry the correct Pi run/turn vocabulary and disposition
Canonical conformance                    [x]  SES-F001's scenario content is complete (0 remaining true Layer-03 placeholders); its schema was Rust-rejected, corrected in cda6b50, and fresh-approved by Rust
Python tests where implemented           [x]  172 test functions across 11 files read in full; 16 real session conformance scenarios, all passing fresh against the corrected+approved schema; session_runner.py re-audited for Agent simulation -- none found
Rust tests where implemented             [x]  N/A — Rust session/ not implemented (Phase 2), confirmed by direct inspection (no session module under minion-agent-rust/), consistent with the manifest
Rust implementation-owner review         [x]  REJECTED (4 defects) on 3d6ffa4, corrected in cda6b50, fresh review APPROVED -- independently re-verified this pass (SHA match, all 13 re-test cases reproduced, full suite/coverage/ruff/mypy re-run clean)
Property/invariant tests                 [x]  test_properties.py — 7 Hypothesis tests already exist
Concurrency tests where applicable       [x]  §9/§10 reviewed — no concurrent-mutation surface exists in this layer (synchronous, in-memory, no locking needed); not applicable rather than missing
Fault-injection tests where applicable   [x]  §8 failure model reviewed — every failure path (JSON-safety, event-name, missing-artifact, decode) is deterministic and already covered by §6's test read
Security review                          [x]  §9 complete — trust boundaries, validation, authority, secrets, resource abuse, and isolation all reviewed; no finding beyond RISK-001 (already reliability-owned)
Reliability review                       [x]  §10 complete — RISK-001 (in-memory-only persistence) confirmed intentional per the frozen design's own Phase-9 commitment, recorded in risk-register.md
Observability review                     [x]  §11 complete — no finding; metrics/stats-query gap noted as a future convenience, not a defect
Performance review                       [x]  §12 complete — one non-blocking observation (derive_messages re-derivation cost, not memoized)
Public API review                        [x]  §13 complete — public/internal boundary confirmed clean; cross-language scope boundary (log wire format vs. reconstructed message shape) confirmed intentional
Documentation                            [x]  §14 complete; spec/session.md now current (SES-F003 resolved)
All findings classified                  [x]  SES-F001..F003 classified
No unresolved Pi uncertainty             [x]  none raised this pass
No unresolved parity defect              [x]  none — Session has none; the one real Pi-derived vocabulary mismatch is Agent-owned (AG-001/AG-004), not a Layer-03 parity defect
No unresolved contract-assurance defect  [x]  SES-F001/F002/F003 all RESOLVED; SES-F001's rejection cycle fully closed by a fresh, independently-reverified Rust APPROVED on cda6b50
Deferred risks recorded                  [x]  RISK-001 (in-memory-only persistence, Phase 9) recorded in risk-register.md
```

---

## 17. Certification result

**Result:** `CERTIFIED`

**Governance correction, recorded transparently (this pass):** §1-14 previously reached `Status:
CERTIFIED` after a fourth pass. That conclusion is corrected here, not erased: `SES-F001` and
`SES-F003` changed shared-contract files (`conformance/schema/session-scenario.schema.json`,
`conformance/session/*.yaml`, `pi-parity-manifest.yaml`, `spec/session.md`) without the required
affected-implementation-owner review — the same shared-contract reviewer rule that governed Layer 02's
`LLM-F010` cycle (`process/implementation-conformance-workflow.md` §15, §4.6). Python's own semantic
audit currently *supports* certification; it does not by itself *constitute* it for a shared
cross-language layer. This pass performed a formal Python semantic-owner review of the finalized diff
(below), confirmed Rust has not implemented `session` (`minion-agent-rust/crates/minion-agent/src/`
contains only `runtime`/`llm`), and prepared and pushed a formal Rust implementation-owner review
package: `assurance/layers/03-session-artifacts-rust-handoff.md`, reviewing `minion-agent@3d6ffa4` +
`minion-agent-docs@92579ee`. **Remaining gate: that review's return.** None of `SES-F001`/`SES-F002`/
`SES-F003`'s underlying conclusions are being reopened or distrusted — they are the candidate finalized
contract Rust now reviews independently.

§1-17 are complete with real grounding, across seven passes. First pass: the frozen design §5/§6/§8
was read directly, `spec/session.md` was checked against it, `MINION-002`/`MINION-003` were traced to
their manifest rows, pinned Pi session source was read to confirm the storage-architecture divergence
is intentional and scoped correctly, all 8 Python modules were read and inventoried, and all 15
canonical session scenarios were read and classified real-vs-placeholder. Second pass: all 11 test
files were read in full (172 test functions, all `KEEP`), the two design-named scenarios with no
canonical file were confirmed genuinely missing rather than assumed, and §8-14's category reviews were
completed, surfacing `RISK-001`. Third pass: `SES-F001` was remediated (self-review `RESOLVED`).
Fourth pass: `SES-F002` was re-scoped and resolved via a dedicated Pi re-audit and Session/Agent
ownership matrix, and `SES-F003` was resolved once that boundary was settled. Fifth pass: the
certification governance itself was corrected, and a formal Rust implementation-owner review package
was sent. Sixth pass: Rust's review returned `REJECTED — CONTRACT_ASSURANCE_DEFECT` against
`SES-F001`'s schema; all four reported defects were independently reproduced before being accepted,
then fixed narrowly, and a corrected candidate was sent back for a fresh review. Seventh pass (this
update): Rust's fresh review returned `APPROVED`; independently re-verified before accepting it
(exact SHA match, all 13 of Rust's own re-test cases reproduced, full suite/coverage/`ruff`/`mypy`
re-run clean) rather than trusted on the report alone.

All three findings' Python-side dispositions stand, all cross-language-approved by Rust's own
independent review. All were originally `CONTRACT_ASSURANCE_DEFECT`, none were `PI_PARITY_DEFECT` or
`PI_BEHAVIOR_UNCERTAIN`:

- **`SES-F001`** (MEDIUM) — **RESOLVED**, via a full rejection/remediation/fresh-review cycle, not a
  clean first pass. Python's own self-review concluded `RESOLVED` and was incomplete: Rust's
  independent implementation-owner review of the resulting schema (`3d6ffa4`) found four real defects
  the self-review missed — `assistantDetail`/`toolResultDetail` omitted
  `provider`/`model`/`timestamp`/`error_message`/`tool_call_id` under `additionalProperties: false` (a
  Rust implementation could drop or fabricate these frozen fields and still pass); `step.append`
  admitted role-incompatible field combinations the runner silently ignored; `contentBlock` was not
  type-discriminated, admitting structurally impossible variants (a text block with no text, an image
  with neither or both of `data`/`reference`). All four independently reproduced against the schema
  before being accepted — not taken on the reviewer's word — then fixed narrowly in `cda6b50`: both
  detail shapes now require and expose every previously-missing field, made genuinely *scriptable*
  through `step.append` (not just observable) per Rust's explicit remediation request; `step.append`
  gained `allOf`/`if`/`then` role-conditional restrictions; `contentBlock` became a
  `type`-discriminated `oneOf` with four closed variants, including the image-source exclusive-or
  `ImageBlock.__post_init__` enforces. Sent back for a fresh review, not self-approved. **Rust's fresh
  review of `cda6b50`: `APPROVED`** — reran the original rejection probes plus new positive cases (all
  correct), confirmed the corrected runner stays thin, and reran schema/Session conformance/full
  suite/`ruff`/`mypy`, all passing at 100% configured coverage; no new `CONTRACT_ASSURANCE_DEFECT`,
  `PI_PARITY_DEFECT`, or `PI_BEHAVIOR_UNCERTAIN`. **Independently re-verified this pass before
  accepting the approval, not trusted on the report alone:** exact SHA confirmed
  (`cda6b5042e678974a43b8dc0fc6ce1c8ade73d88`), all 13 of Rust's own listed re-test cases independently
  reproduced (all correct), full suite re-run fresh with coverage enabled (724 passed/42 xfailed/0
  failed, 100.00% coverage, exact match), `ruff`/`mypy` re-run clean. Full detail in `SES-F001`'s
  findings row (§15).
- **`SES-F002`** (originally HIGH) — **RESOLVED this pass, downgraded to informational: Outcome A, no
  Layer-03 defect.** Pi was re-audited directly (`packages/agent/src/types.ts:428-443`'s `AgentEvent`
  union, not re-trusted from either prior pass's design-doc paraphrase) and found to keep its
  `agent_start`/`turn_start`/`message_*`/`tool_execution_*` lifecycle vocabulary as an ephemeral
  UI-notification stream, structurally separate from Pi's persisted session storage (confirmed: zero
  occurrences of any of those event-type strings in Pi's `Entry`/`LaneRecord` definitions). Session
  never needs this vocabulary to do its own job and already treats every log-only event uniformly
  regardless of name. The real mismatch — `agent_loop/driver.py`'s own docstring literally defines "a
  turn" as "zero or more steps," redefining observable `turn` to mean a multi-request run exactly as
  design §6 forbids — lives entirely inside a Layer-08 file, and `pi-parity-manifest.yaml` already
  carries `AG-001`/`AG-004` (phase 3, correct Pi vocabulary, disposition `adopted`, real but
  `xfailed`-confirmed placeholder conformance evidence) tracking it. Full ownership matrix, event-by-
  event, is in §7 ("`SES-F002` Pi audit and ownership matrix"). No `session/*.py` or `agent_loop/*.py`
  file was changed — this was a scope correction, not an implementation fix. **Cross-language
  approved:** Rust's own implementation-owner review independently re-audited Pi (a wider symbol set,
  including `packages/agent/src/harness/session/context.ts`, `harness/messages.ts::convertToLlm`, and
  `harness/compaction/compaction.ts`) and reached the identical mixed-boundary conclusion,
  characterizing it precisely: Session "may store valid producer-owned operational/log-only data" but
  "does not acquire semantic ownership of that producer vocabulary" and "does not recreate the live
  `AgentEvent` notification stream." `SES-F002` remains `RESOLVED`.
- **`SES-F003`** (LOW) — **RESOLVED**, deliberately only after `SES-F002`'s boundary was settled.
  `spec/session.md` now states the by-value event-identity rule explicitly, states exactly what
  Session owns versus what a log-only-event producer owns, and states the XFORM boundary explicitly —
  without specifying a run/turn/step vocabulary, since that's confirmed Agent-owned. **Cross-language
  approved:** Rust's review confirms "event identity is the serialized string value; enum singleton,
  allocation, pointer, reference, and language object identity do not participate," and confirms the
  Session/XFORM boundary independently. `SES-F003` remains `RESOLVED`.

`RISK-001` (`SessionLog`/`ArtifactStore` in-memory only, confirmed intentional per the design's own
Phase-9 commitment, recorded in `risk-register.md`) needs no action from this layer — unchanged this
pass.

**Migration hypothesis correction (first pass, still standing):** the charter's own §6 flagged "session
derive/reconstruction" as a "realignment candidate." The full read of `derive.py` (and its 16+7
dedicated tests, now joined by 5 filled canonical round-trip scenarios) found no defect in its logic —
every reset/compaction/fork rule is implemented exactly as design §5 specifies. Recorded as **not
borne out by evidence**, per the charter's own instruction that a starting hypothesis is not a
substitute for audit evidence.

**Python semantic-owner review (this pass, performed before packaging for Rust):** re-read the
finalized diff specifically hunting for the classes of defect `LLM-F010` taught this project to look
for — nested-optional null-handling, `additionalProperties: false` omitting a legitimately-variable
frozen field, integer-narrowing of a language-neutral number, Python-object-shape leakage. Found zero
hard defects of that shape, but two items were flagged for Rust's *independent* judgment rather than
self-cleared: (1) `assistantDetail` excludes `provider`/`model`/`timestamp`/`error_message` because the
Session-family runner fixes them for every message regardless of role — structurally the same shape as
`LLM-F010`'s rejected `timestamp` omission, distinguished only by the claim that nothing real is being
suppressed here, a claim not taken on faith; (2) `step.append`'s schema does not conditionally restrict
fields by `role` (e.g. `stop_reason` is schema-legal on a `user` append even though the runner ignores
it there) — a completeness gap, not an observed correctness defect. Full detail, and the complete
review package (Pi evidence, ownership matrix, 17-scenario inventory, runner-thinness confirmation, all
13 required review questions), is in `assurance/layers/03-session-artifacts-rust-handoff.md`.

**Rust's implementation-owner review (this pass) and the remediation it required:** Rust returned
`REJECTED — CONTRACT_ASSURANCE_DEFECT` against `3d6ffa4`/`c273df1`, recorded in full in
`03-session-artifacts-rust-review.md`. All four reported defects were independently reproduced against
the schema — using Rust's own adversarial probes, not summarized versions of them — before being
accepted as real, matching the discipline `LLM-F010` established: a rejection is verified, not
rubber-stamped, but also not defended against once confirmed. All four were then fixed narrowly in
`cda6b50` (full technical detail in `SES-F001`'s findings row, §15, and in the header's remediation
note). Every one of Rust's adversarial probes was re-run against the fix and now behaves correctly.
Full Python suite re-run fresh: 724 passed/42 xfailed/0 failed (unchanged counts — no scenarios added
or removed, only existing assertions extended), `ruff`/`mypy` clean. **This corrected candidate is
sent back for a fresh Rust implementation-owner review — the first rejection is not treated as
approval after a fix, and this pass does not self-approve the correction.**

Rust's review also independently confirmed `SES-F002` (Outcome A, with a wider Pi symbol set than
Python's own audit — `context.ts`, `harness/messages.ts::convertToLlm`,
`harness/compaction/compaction.ts` — reaching the identical conclusion) and `SES-F003` (by-value
identity, Session/XFORM boundary), and confirmed `MINION-003`'s traceability and the 17-scenario
family placement are sound. It also independently confirmed the certification-applicability question
this pass had left open: Rust Session implementation is `EXPLICITLY DEFERRED BY PLAN`, non-blocking,
citing the same workflow provisions (`process/implementation-conformance-workflow.md` §7.3/§5.9,
project invariant 19, `fidelity-assurance-method.md` §14) this record's own governance-correction
section had already identified — Rust reached this independently rather than accepting Python's
framing.

**Rust's fresh review of the corrected candidate, independently re-verified before acceptance:** Rust
reran the original rejection probes against `cda6b50` plus new positive cases — complete
`assistantDetail`/`toolResultDetail` validate, an unknown field on either remains rejected,
role-incompatible appends remain rejected, all four closed `contentBlock` variants validate,
invalid/cross-variant blocks remain rejected, fractional timestamps remain valid as a language-neutral
number rather than being narrowed to integer — confirmed the corrected runner stays thin (deserializes
canonical values, constructs real typed Session/LLM values, invokes the real Session
encode/append/derive/header/artifact paths, normalizes real reconstructed values; does not implement
Session derivation, Agent lifecycle, or XFORM), and reran schema validation, Session conformance, the
full Python suite, `ruff`, and `mypy`, all passing at 100% configured line coverage. No new
`CONTRACT_ASSURANCE_DEFECT`, `PI_PARITY_DEFECT`, or `PI_BEHAVIOR_UNCERTAIN`. Verdict: `APPROVED`.
Recorded in full in `03-session-artifacts-rust-review.md`, with the initial rejection preserved as
assurance history, not overwritten.

This pass did not accept that verdict on the report alone. Independently re-verified: the reviewed SHA
(`cda6b5042e678974a43b8dc0fc6ce1c8ade73d88`) matches exactly what was pushed; all 13 of Rust's own
listed re-test cases were reconstructed from scratch and reproduced against the schema directly (all
behaved as Rust reported); the full Python suite was re-run fresh with coverage enabled (724
passed/42 xfailed/0 failed, 100.00% coverage — exact match to Rust's claim); `ruff`/`mypy` re-run
clean.

**Not started this pass, by design:** any implementation of Layer 08 (Agent loop), Layer 04 (XFORM),
or Rust. `agent_loop/driver.py` and `session/events.py` remain unmodified — `SES-F002`'s resolution
is still a documentation/scope correction, not a code change. `AG-001`/`AG-004`'s own remediation
remains explicitly left for Layer 08's own future pass.

**Final freeze-gate audit:**

```text
Pinned Pi audited?                                        YES -- types.ts:428-443, session.ts/types.ts, spec/agent.md, driver.py docstring, independently re-audited by Rust with a wider symbol set
Parity manifest current?                                  YES -- MINION-002/003, AG-001/AG-004 all present and dispositioned; MINION-003 traceability confirmed by Rust
spec/session.md complete for current Session scope?       YES -- by-value identity rule + Session/Agent/XFORM boundary stated; confirmed by Rust
Canonical Session schema language-neutral?                YES -- 4 real defects found by Rust, fixed in cda6b50, fresh Rust review APPROVED, independently re-verified this pass
Python Session runner thin?                                YES -- re-audited in full by both Python and Rust; no Agent/XFORM simulation found
Rust implementation-owner review?                         APPROVED on cda6b50, after REJECTED on 3d6ffa4 (4 defects, fixed) -- both verdicts independently re-verified before being trusted
Rust implementation obligation for Layer 03?               COMPLETED after certification under the approved deferred plan -- typed implementation plus 16 applicable canonical scenarios at `31ed669`
All current Layer-03 placeholders resolved?                YES -- 0 remaining true Layer-03 placeholders; Rust independently confirmed the 17-scenario family placement
Layer-04 deferred case explicitly owned?                   YES -- request-reconstruction-after-target-transform, owner Layer 04/XFORM, confirmed by Rust
Agent lifecycle ownership explicit?                        YES -- AG-001/AG-004, phase 3, disposition adopted
Active PI_PARITY_DEFECT?                                   NONE
Active PI_BEHAVIOR_UNCERTAIN?                               NONE
Active CONTRACT_ASSURANCE_DEFECT?                           NONE -- SES-F001's schema defects were real, are now fixed, and the fix is cross-language approved
Any conformance runner simulating Agent/XFORM semantics?    NO -- confirmed independently by both Python's and Rust's review
```

**Layer 03 — Session + Artifacts: `CERTIFIED`.**

**Follow-up dependencies (none block this certification):**

1. `SES-F001`/`SES-F002`/`SES-F003` — all `RESOLVED`, all cross-language approved. Nothing further
   required.
2. Rust Session implementation was `EXPLICITLY DEFERRED BY PLAN` at certification and is now
   complete at `31ed669`, consuming the same certified contract. Its 16 applicable canonical
   scenarios and implementation-specific evidence are green; the Layer-04 target-transform case
   remains correctly deferred.
3. `RISK-001` needs no action from this layer — it is Phase 9's commitment to fulfill, already
   recorded and cited.
4. `AG-001`/`AG-004`'s own remediation (the real run/turn naming/behavior fix in `agent_loop/
   driver.py`) is Layer 08's future work, not a Layer-03 obligation.
5. Do not start Layer 04, Layer 08, or any Rust implementation work as a consequence of this
   certification landing — each starts on its own turn, per the standing sequencing rule.
6. Do not start Layer 04, Layer 08, or any Rust implementation work in the meantime.
