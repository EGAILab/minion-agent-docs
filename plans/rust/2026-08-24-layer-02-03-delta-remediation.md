# Rust Layer 02/03 Delta Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Align the typed Rust Layer-02/03 implementation with the approved post-certification delta contracts and execute all current Session scenarios through the real Rust seam.

**Architecture:** Preserve the typed LLM and Session APIs. Change vocabulary/validation at their owning boundaries, extend the existing thin Session conformance adapter only to invoke and observe real APIs, and retain the existing single-mutex compaction linearization. No Agent or XFORM behavior is added.

**Tech Stack:** Rust 2024, serde, serde_yaml, parking_lot, Cargo workspace tests.

**Spec:** `spec/llm.md`, `spec/session.md`, `assurance/layers/03-session-artifacts-delta-rust-review-ses-f007.md`

## Global constraints

- `ToolResultMessage.tool_name` is a required `String`; no empty/default synthesis.
- Event names follow `^[a-z][a-z0-9_]*(?:/[a-z][a-z0-9_-]*)*$`.
- Compaction remains `session/compaction` and snapshot plus marker stay under one serialization boundary.
- Discover 19 Session scenarios, execute 18, and defer only the Layer-04 target-transform scenario.
- The runner parses/translates/normalizes only; semantic validation and operations remain in the typed library.
- No Python, Agent, XFORM, provider, or Phase-5 implementation changes.

---

### Task 1: Required tool-result name

**Files:**
- Modify: `minion-agent-rust/crates/minion-agent/tests/llm_vocabulary.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/llm/vocabulary.rs`
- Modify: `minion-agent-rust/crates/minion-agent/tests/session_conformance.rs`

- [ ] Add a compile/serde-facing test proving a constructed tool result serializes a required, non-default name and deserialization without `tool_name` fails.
- [ ] Run the focused test and verify it fails because the current optional field accepts absence.
- [ ] Change `tool_name: Option<String>` to `tool_name: String`; keep the constructor as the sole direct value source.
- [ ] Remove runner fallback and optional post-construction overwrite; require the scenario value.
- [ ] Run LLM vocabulary and Session conformance tests.

### Task 2: Canonical event-name validation

**Files:**
- Modify: `minion-agent-rust/crates/minion-agent/tests/session.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/session/mod.rs`

- [ ] Add the nine-value canonical accept/reject matrix to the real `EventKind::new` test.
- [ ] Run the focused test and verify `plugin-name/foo` is incorrectly accepted.
- [ ] Validate the first namespace segment without hyphens while retaining hyphens in later segments.
- [ ] Run the focused Session tests.

### Task 3: Thin canonical runner delta operations

**Files:**
- Modify: `minion-agent-rust/crates/minion-agent/tests/session_conformance.rs`

- [ ] Update count assertions to 19 discovered, 18 executed, one explicitly deferred.
- [ ] Add real `expect_event_kinds` observation from `Session::events()`.
- [ ] Add `expect_error` handling by invoking real typed operations and mapping `SessionError::InvalidForkBoundary` to the canonical category; do not prevalidate.
- [ ] Require role-specific typed deserialization and required `tool_name` with no dropped invalid blocks.
- [ ] Run the canonical Session test and verify all 18 applicable scenarios pass.

### Task 4: SES-F007 Rust regression evidence

**Files:**
- Modify: `minion-agent-rust/crates/minion-agent/tests/session.rs`
- Retain: `minion-agent-rust/crates/minion-agent/src/session/mod.rs`

- [ ] Add a concurrent append/reset/compact stress test that inspects committed marker provenance through real Session events.
- [ ] Verify the test passes with the existing single mutex spanning snapshot and marker; no semantic code change is expected.
- [ ] Re-read `Session::compact()` to confirm every mutation uses the same event-log mutex.

### Task 5: Verification and integration

**Files:**
- Modify only if needed for non-semantic evidence: Rust tests/runner.

- [ ] Run `cargo fmt --check`.
- [ ] Run `cargo clippy --workspace --all-targets --all-features -- -D warnings`.
- [ ] Run `cargo test --workspace --all-features` and record exact counts.
- [ ] Run `RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps`.
- [ ] Run `cargo run -p xtask -- conformance verify`.
- [ ] Inspect the final diff for runner semantic leakage and confirm no Python/Agent/XFORM changes.
- [ ] Commit, push the fresh remediation branch, open a new PR, request review, and merge only after final green verification.
- [ ] Return the merge SHA and evidence to the shared assurance owner; do not self-certify either layer.
