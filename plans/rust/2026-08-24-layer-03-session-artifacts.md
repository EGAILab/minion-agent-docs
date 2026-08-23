# Rust Layer 03 Session + Artifacts Implementation Plan

> **Execution:** Use the `executing-plans` and `test-driven-development` skills. Complete each task with a failing test first, then the minimum implementation, then focused and workspace verification.

**Goal:** Implement the approved Layer 03 Session + Artifacts contract as an idiomatic typed Rust module and execute all 16 current-layer canonical Session scenarios through a thin runner over the real Rust API.

**Authority:** `spec/session.md`, `conformance/schema/session-scenario.schema.json`, `conformance/session/*.yaml`, and `MINION-003` at `minion-agent@cda6b5042e678974a43b8dc0fc6ce1c8ade73d88`. Python is supporting evidence, not semantic authority.

**Boundary:** Session owns persistence, reconstruction, surface projection, fork/reset/compaction, request headers, and artifacts. It does not implement Agent lifecycle events or target-model transformation. `request-reconstruction-after-target-transform.yaml` remains Layer 04 deferred.

## Task 1: Establish typed Session identity, events, and atomic append

**Files:**

- Create `minion-agent-rust/crates/minion-agent/src/session/mod.rs`
- Create `minion-agent-rust/crates/minion-agent/src/session/event.rs`
- Create `minion-agent-rust/crates/minion-agent/src/session/log.rs`
- Modify `minion-agent-rust/crates/minion-agent/src/lib.rs`
- Test in the new modules and `minion-agent-rust/crates/minion-agent/tests/session.rs`

Implement an open, by-value `EventKind` string identity, core event constants, `SessionEvent`, and an append-only synchronized log. Validation and sequence allocation must occur in one serialized append operation so sequence order equals commit order. Unknown well-formed event names are loggable; registration is not identity creation.

Prove invalid names are rejected, equality is by string value, concurrent committed sequences are unique/strictly increasing, and raw serde input crosses the same validation boundary as typed helpers.

## Task 2: Preserve the complete Layer 02 message vocabulary

**Files:**

- Create `minion-agent-rust/crates/minion-agent/src/session/message.rs`
- Modify `minion-agent-rust/crates/minion-agent/src/session/event.rs`
- Test in `minion-agent-rust/crates/minion-agent/tests/session.rs`

Add typed append/decode helpers for user, assistant, and tool-result messages using the real `llm` vocabulary. Preserve all frozen fields and strict discriminated content blocks. Serde is the persistence boundary, not the internal model.

Prove rich assistant messages round-trip by value, optional values remain distinct from zero/false/empty values, tool results retain identity/content/error state, and malformed role/content combinations fail before append.

## Task 3: Implement surface derivation, reset, and compaction

**Files:**

- Create `minion-agent-rust/crates/minion-agent/src/session/derive.rs`
- Create `minion-agent-rust/crates/minion-agent/src/session/operation.rs`
- Modify `minion-agent-rust/crates/minion-agent/src/session/mod.rs`
- Test focused derivation cases in `minion-agent-rust/crates/minion-agent/tests/session.rs`

Fold immutable log events in order. Core message events are surface-visible; other events remain log-only unless an explicit projection is registered. Reset establishes a surface boundary. Compaction explicitly replaces its superseded effective range, preserves retained-tail provenance, and handles repeated, nested, overlapping, and fork-local replacements without double emission.

Prove plugin-defined event logging is independent of surface admission, projection removal affects future derivation, reset boundaries work, and every applicable compaction scenario has a direct Rust test before canonical execution.

## Task 4: Implement immutable fork ancestry

**Files:**

- Create `minion-agent-rust/crates/minion-agent/src/session/session.rs`
- Modify `minion-agent-rust/crates/minion-agent/src/session/mod.rs`
- Test fork behavior in `minion-agent-rust/crates/minion-agent/tests/session.rs`

Implement a typed `Session` whose fork records immutable ancestry and a fixed source boundary. Later parent appends do not leak into the child; child operations remain fork-local. Keep ownership in Session rather than the conformance runner.

## Task 5: Implement content-addressed artifacts and request headers

**Files:**

- Add only required `sha2` dependency entries to `minion-agent-rust/Cargo.toml` and crate `Cargo.toml`
- Create `minion-agent-rust/crates/minion-agent/src/session/artifact.rs`
- Create `minion-agent-rust/crates/minion-agent/src/session/request.rs`
- Modify `minion-agent-rust/crates/minion-agent/src/session/mod.rs`
- Test in `minion-agent-rust/crates/minion-agent/tests/session.rs`

Store immutable bytes by SHA-256 identity, expose no deletion in Layer 03, and retain enough metadata for canonical observation. Persist sorted component-name to artifact-hash request headers. Dispatch assembly and reconstruction must call the same canonical composition function.

Prove hash stability, deduplication, resolution, record/header observation, component-order determinism, and exact request reconstruction.

## Task 6: Execute the canonical Session suite through a thin Rust runner

**Files:**

- Create `minion-agent-rust/crates/minion-agent/tests/session_conformance.rs`
- Create supporting conversion-only code under `minion-agent-rust/crates/minion-agent/tests/support/` if needed
- Modify test dependencies only as required

Deserialize the shared schema/scenarios, translate steps into public typed Rust calls, and normalize real results. The adapter may parse, arrange fixtures, convert values, and project observations; it must not derive history, implement compaction, calculate artifact identities, or simulate Agent/XFORM behavior.

Run all 17 files. Require 16 Layer-03 scenarios to execute and pass. Classify only `request-reconstruction-after-target-transform.yaml` as the explicit Layer-04 deferment; reject any additional placeholder or unknown operation.

## Task 7: Properties, documentation, layering, and assurance evidence

**Files:**

- Add property tests to `minion-agent-rust/crates/minion-agent/tests/session.rs`
- Update Rust public documentation where Session is exported
- Update `minion-agent-docs/assurance/layers/03-session-artifacts.md` with produced evidence

Add properties for sequence/commit ordering, serialization round trips, fork boundary immutability, derivation idempotence, compaction non-duplication, and artifact content identity. Every public Layer-03 API must be exercised by canonical or Rust tests; add no speculative Agent/XFORM API.

Run:

```powershell
cargo fmt --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace --all-features
$env:RUSTDOCFLAGS='-D warnings'; cargo doc --workspace --no-deps
cargo run -p xtask -- conformance verify
```

Record exact results, scenario disposition, changed paths, and any remaining hardening findings. Layer certification remains with the shared assurance owner.

## Completion criteria

- The approved shared contract remains unchanged.
- The real typed Rust Session + Artifacts implementation exists.
- All 16 current-layer canonical scenarios pass through the thin Rust runner.
- The one XFORM scenario is explicitly deferred without simulation.
- No Agent, XFORM, or provider behavior is introduced.
- All Rust gates are green.
- Rust evidence is recorded in the shared Layer 03 assurance record.
