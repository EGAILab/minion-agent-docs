# Rust Layer 02 LLM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the complete Rust-owned Layer 02 LLM vocabulary, adapter seam, coordinating service, and contract-enforcing `AssistantStream` against the frozen Minion/Pi-derived observable contract.

**Architecture:** Typed Rust vocabulary flows through a typed `LlmAdapter` returning a raw `Stream<Item = Result<StreamChunk, AdapterStreamError>>`. `AssistantStream` alone owns provider-neutral accumulation, terminal settlement, premature-EOF normalization, and fusion; adapters decode provider behavior but never reproduce those Minion semantics. `LlmService` performs strict target identity and adapter lookup before returning the public stream.

**Tech Stack:** Rust 2024, `serde`, `serde_json`, `schemars`, `futures`, `thiserror`, `parking_lot`, `proptest`, Tokio tests.

**Spec:** `minion-agent-docs/spec/llm.md`, frozen design `minion-agent-docs/design/2026-08-20-minion-agent-design.md` §4, assurance handoff `minion-agent-docs/assurance/layers/02-llm-rust-handoff.md`.

## Global Constraints

- Semantic authority is the frozen design/spec plus adopted pinned-Pi rows in `/pi-parity-manifest.yaml`; Python is a peer implementation, not the oracle.
- Target-model compatibility identity is exactly non-empty `provider + api + model_id`; Rust does not add Python's temporary `api = "mock"` fallback.
- Before the raw provider stream exists, invalid caller input, model lookup, and adapter-start failures return typed eager errors.
- After `AssistantStream` exists, expected operational failures are values: public shape is `non-terminal* -> exactly one terminal -> EOF`.
- Premature raw EOF produces an in-band adapter/protocol error terminal, preserves the accumulated partial assistant message, and fuses. Exact diagnostic text is not standardized and must not be asserted canonically.
- Rust panics are programming/invariant failures and are not converted into assistant output.
- The raw adapter knows provider protocol; it must not own public terminal fusion, premature-EOF policy, or Minion settlement invariants.
- The settlement wrapper knows Minion stream semantics; it must not know provider wire mechanics.
- `serde_json::Value` is restricted to explicitly dynamic vocabulary fields and serialization/conformance boundaries.
- Do not modify Python-owned files or concurrent uncommitted shared-contract/assurance work.
- Do not implement target-model transformation, agent-loop behavior, sessions, telemetry, real providers, or Phase 3+ semantics in this plan.
- If a required observable decision is not determined by the current contract, record `CONTRACT_ASSURANCE_DEFECT` and stop that behavior rather than silently defining Rust semantics.

---

## File Map

- `crates/minion-agent/src/llm/mod.rs`: public module boundary and re-exports.
- `crates/minion-agent/src/llm/vocabulary.rs`: typed content, messages, usage, diagnostics, deferred handles, request/context, stream chunks, and serde/schema forms.
- `crates/minion-agent/src/llm/model.rs`: validated provider/API/model identity.
- `crates/minion-agent/src/llm/adapter.rs`: raw adapter trait, raw stream aliases, typed start/stream errors.
- `crates/minion-agent/src/llm/assistant_stream.rs`: provider-neutral accumulation, settlement, and fusion.
- `crates/minion-agent/src/llm/service.rs`: adapter registry, eager validation/lookup, and public stream creation.
- `crates/minion-agent/src/llm/scripted.rs`: deterministic real-trait adapter; it scripts raw output only.
- `crates/minion-agent/tests/llm_vocabulary.rs`: public shape, validation, serde, and schema evidence.
- `crates/minion-agent/tests/llm_adapter.rs`: adapter/service boundary evidence.
- `crates/minion-agent/tests/llm_assistant_stream.rs`: never-raises and adversarial stream evidence.
- `crates/minion-agent/tests/llm_conformance.rs`: thin canonical adapter only when shared Layer-02-owned cases are executable.
- `crates/minion-agent/src/lib.rs`: public `llm` module and intentional exports.
- `crates/minion-agent/Cargo.toml`, workspace `Cargo.toml`: only dependencies proven necessary by the implementation.
- `minion-agent-docs/assurance/layers/02-llm.md`: Rust evidence and disposition updates after parallel shared edits are committed.

### Task 1: Validated model identity and public vocabulary

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/llm/model.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/llm/vocabulary.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/llm/mod.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/lib.rs`
- Modify: `minion-agent-rust/crates/minion-agent/Cargo.toml`
- Modify: `minion-agent-rust/Cargo.toml`
- Test: `minion-agent-rust/crates/minion-agent/tests/llm_vocabulary.rs`

**Interfaces:**
- Produces: `ModelIdentity::new(provider, api, model_id) -> Result<ModelIdentity, ModelIdentityError>` and getters `provider()`, `api()`, `model_id()`.
- Produces: typed `TextBlock`, `ThinkingBlock`, `ImageBlock`, `ToolCall`, `UserMessage`, `AssistantMessage`, `ToolResultMessage`, `Usage`, `Cost`, `DeferredHandle`, `DiagnosticError`, `AssistantMessageDiagnostic`, `StopReason`, `LlmContext`, `LlmRequest`, and `StreamChunk`.
- Produces: `AssistantMessage::pending(ModelIdentity, timestamp)`, `StreamChunk::partial()`, and `StreamChunk::is_terminal()` for the settlement layer.

- [ ] **Step 1: Write focused failing identity tests**

```rust
#[test]
fn model_identity_requires_all_three_non_empty_components() {
    assert!(ModelIdentity::new("openai", "responses", "gpt-5").is_ok());
    assert_eq!(ModelIdentity::new("", "responses", "gpt-5").unwrap_err().field(), "provider");
    assert_eq!(ModelIdentity::new("openai", "", "gpt-5").unwrap_err().field(), "api");
    assert_eq!(ModelIdentity::new("openai", "responses", "").unwrap_err().field(), "model_id");
}

#[test]
fn model_identity_has_value_equality_and_round_trips() {
    let identity = ModelIdentity::new("openai", "responses", "gpt-5").unwrap();
    let json = serde_json::to_value(&identity).unwrap();
    assert_eq!(json, serde_json::json!({
        "provider": "openai", "api": "responses", "model_id": "gpt-5"
    }));
    assert_eq!(serde_json::from_value::<ModelIdentity>(json).unwrap(), identity);
}
```

- [ ] **Step 2: Run the identity tests and verify RED**

Run: `cargo test -p minion-agent --test llm_vocabulary model_identity -- --nocapture`

Expected: compilation fails because `minion_agent::llm` does not exist.

- [ ] **Step 3: Implement the minimal validated identity**

Use owned non-empty strings, value-derived `Eq`/`Hash`, `TryFrom`-based deserialization validation, `JsonSchema`, and a concrete `thiserror` error whose `field()` identifies the missing component. Do not supply defaults.

- [ ] **Step 4: Run the identity tests and verify GREEN**

Run: `cargo test -p minion-agent --test llm_vocabulary model_identity -- --nocapture`

Expected: both tests pass.

- [ ] **Step 5: Add failing vocabulary shape tests**

The tests must construct every public content/message/diagnostic/usage variant, serialize it, assert canonical snake_case tags and optional-field omission, deserialize it, and compare typed equality. Include these contract-sensitive assertions:

```rust
assert_eq!(serde_json::to_value(StopReason::ToolUse).unwrap(), "tool_use");
assert_eq!(serde_json::to_value(StopReason::Deferred).unwrap(), "deferred");
assert!(assistant_json.get("response_id").is_none());
assert_eq!(assistant_json["usage"]["total_tokens"], 3);
assert_eq!(tool_call_json["type"], "tool_call");
assert_eq!(thinking_json["redacted"], false);
```

Also derive/check `schemars::JsonSchema` for the public vocabulary so the Rust shape is mechanically inspectable without making a Rust-only schema normative.

- [ ] **Step 6: Run vocabulary tests and verify RED**

Run: `cargo test -p minion-agent --test llm_vocabulary -- --nocapture`

Expected: missing vocabulary types and methods fail compilation.

- [ ] **Step 7: Implement the typed vocabulary minimally**

Use specialized typed content enums so invalid role/content combinations cannot be constructed:

```rust
pub enum UserContent { Text(String), Blocks(Vec<UserContentBlock>) }
pub enum UserContentBlock { Text(TextBlock), Image(ImageBlock) }
pub enum AssistantContentBlock { Text(TextBlock), Thinking(ThinkingBlock), ToolCall(ToolCall) }
pub enum ToolResultContentBlock { Text(TextBlock), Image(ImageBlock) }
```

Use `serde_json::Value` only for dynamic fields such as tool arguments, diagnostic details, deferred data, and tool-result details. Represent diagnostic codes with a typed untagged string-or-number enum. Stream chunk variants carry the current complete partial `AssistantMessage`; the wrapper therefore replaces its accumulator from real adapter observations instead of reconstructing provider deltas.

- [ ] **Step 8: Run vocabulary and workspace tests**

Run: `cargo test -p minion-agent --test llm_vocabulary -- --nocapture`

Run: `cargo test --workspace --all-features`

Expected: all pass.

- [ ] **Step 9: Commit Task 1**

```powershell
git add minion-agent-rust/Cargo.toml minion-agent-rust/crates/minion-agent/Cargo.toml minion-agent-rust/crates/minion-agent/src/lib.rs minion-agent-rust/crates/minion-agent/src/llm minion-agent-rust/crates/minion-agent/tests/llm_vocabulary.rs
git commit -m "feat(rust): add typed LLM vocabulary"
```

### Task 2: Typed raw adapter seam and eager service boundary

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/llm/adapter.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/llm/service.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/llm/mod.rs`
- Test: `minion-agent-rust/crates/minion-agent/tests/llm_adapter.rs`

**Interfaces:**
- Consumes: `ModelIdentity`, `LlmRequest`, `StreamChunk`.
- Produces: `RawAssistantStream = Pin<Box<dyn Stream<Item = Result<StreamChunk, AdapterStreamError>> + Send>>`.
- Produces: `LlmAdapter::start(&self, request: LlmRequest) -> Result<RawAssistantStream, AdapterStartError>`.
- Produces: `LlmService::register(identity, Arc<dyn LlmAdapter>)`, `LlmService::stream(request) -> Result<AssistantStream, LlmStartError>`.

- [ ] **Step 1: Write failing adapter/service tests**

Create a tiny test-only adapter that records requests and can fail before returning a stream. Prove:

```rust
assert!(matches!(service.stream(unknown_request), Err(LlmStartError::UnknownModel { .. })));
assert!(matches!(service.stream(known_but_rejected), Err(LlmStartError::AdapterStart(_))));
assert_eq!(recorded_requests, vec![known_request]);
```

Also prove registration replacement uses the current adapter for the exact three-part identity, matching the adopted Pi registry behavior without changing the semantic identity.

- [ ] **Step 2: Run adapter tests and verify RED**

Run: `cargo test -p minion-agent --test llm_adapter -- --nocapture`

Expected: missing adapter/service symbols fail compilation.

- [ ] **Step 3: Implement typed adapter errors and service lookup**

`AdapterStartError` represents failure before a raw stream exists. `AdapterStreamError` represents expected operational failure after stream creation and includes a typed kind (`Provider`, `Network`, `Model`, `Cancelled`, `Protocol`, `Runtime`) plus a non-empty diagnostic message. `LlmStartError` wraps unknown identity/caller/start failures without `anyhow`.

The service registry is synchronized narrowly and clones the selected `Arc` before invoking it; no lock is held across adapter code. Do not use `catch_unwind`.

- [ ] **Step 4: Run adapter and workspace tests**

Run: `cargo test -p minion-agent --test llm_adapter -- --nocapture`

Run: `cargo test --workspace --all-features`

Expected: all pass.

- [ ] **Step 5: Commit Task 2**

```powershell
git add minion-agent-rust/crates/minion-agent/src/llm minion-agent-rust/crates/minion-agent/tests/llm_adapter.rs
git commit -m "feat(rust): add typed LLM adapter seam"
```

### Task 3: Contract-enforcing AssistantStream

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/llm/assistant_stream.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/llm/service.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/llm/mod.rs`
- Test: `minion-agent-rust/crates/minion-agent/tests/llm_assistant_stream.rs`

**Interfaces:**
- Consumes: raw adapter stream and initial pending `AssistantMessage`.
- Produces: `AssistantStream: Stream<Item = StreamChunk> + FusedStream`.
- Produces no public `Result` items and does not catch panics.

- [ ] **Step 1: Write the normal terminal/fusion RED tests**

Script two non-terminals, one valid terminal, and extra raw output. Assert the exact public sequence is the first three chunks, `is_terminated()` is true after the terminal, and another `next()` returns `None` without polling the raw source again.

- [ ] **Step 2: Run the focused stream test and verify RED**

Run: `cargo test -p minion-agent --test llm_assistant_stream normal_terminal_fuses_without_hidden_drain -- --nocapture`

Expected: missing `AssistantStream` implementation fails compilation.

- [ ] **Step 3: Implement normal fusion minimally**

Poll the raw source until the first terminal. Update accumulated partial from every observed chunk, emit the chunk, then mark fused and drop/release the raw stream. Once fused, always return `Poll::Ready(None)` and never poll raw input again.

- [ ] **Step 4: Verify GREEN**

Run: `cargo test -p minion-agent --test llm_assistant_stream normal_terminal_fuses_without_hidden_drain -- --nocapture`

Expected: pass.

- [ ] **Step 5: Write RED tests for operational errors**

Test provider/network/model/runtime errors map to one `StreamChunk::Error` with `stop_reason = Error`, preserve the latest complete partial, expose a non-empty error message, then EOF. Test cancellation separately and require `stop_reason = Aborted`.

- [ ] **Step 6: Run operational-error tests and verify RED**

Run: `cargo test -p minion-agent --test llm_assistant_stream adapter_error -- --nocapture`

Expected: raw `Err` is not yet mapped to the public terminal shape.

- [ ] **Step 7: Implement operational settlement minimally**

On raw `Err`, clone the accumulated assistant message, set the specified terminal stop reason, set `error_message` from the adapter diagnostic, emit exactly one terminal error chunk, and fuse. Preserve all other accumulated partial fields verbatim.

- [ ] **Step 8: Write and run premature-EOF RED tests**

Assert only normative observables:

```rust
assert_eq!(terminal.partial(), &last_partial);
assert_eq!(terminal.partial().stop_reason, StopReason::Error);
assert!(terminal.partial().error_message.as_deref().is_some_and(|s| !s.is_empty()));
assert!(stream.next().await.is_none());
```

The comparison helper must ignore only the two fields intentionally changed for settlement (`stop_reason`, `error_message`). Do not assert exact message text or invent a canonical diagnostic type.

Run: `cargo test -p minion-agent --test llm_assistant_stream premature_eof -- --nocapture`

Expected: raw EOF currently returns public EOF without a terminal.

- [ ] **Step 9: Implement premature-EOF settlement and verify GREEN**

On raw EOF before any terminal, create an adapter/protocol error terminal from the accumulated partial, set `stop_reason = Error`, attach a non-empty implementation diagnostic, emit it once, and fuse. The diagnostic string remains an implementation detail.

Run: `cargo test -p minion-agent --test llm_assistant_stream -- --nocapture`

Expected: all stream tests pass.

- [ ] **Step 10: Add adversarial property and panic-boundary tests**

Use `proptest` to generate raw sequences containing non-terminals, errors, terminals, and trailing items. Assert the public observable sequence always matches `non-terminal* -> terminal -> EOF` and never requires detecting raw items after fusion. Add a `#[should_panic]` adapter-stream test proving a raw poll panic is not converted into assistant output.

- [ ] **Step 11: Run full Task 3 verification**

Run: `cargo test -p minion-agent --test llm_assistant_stream -- --nocapture`

Run: `cargo test --workspace --all-features`

Expected: all pass.

- [ ] **Step 12: Commit Task 3**

```powershell
git add minion-agent-rust/crates/minion-agent/src/llm minion-agent-rust/crates/minion-agent/tests/llm_assistant_stream.rs
git commit -m "feat(rust): enforce settled assistant streams"
```

### Task 4: Scripted adapter through the real trait

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/llm/scripted.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/llm/mod.rs`
- Test: `minion-agent-rust/crates/minion-agent/tests/llm_adapter.rs`
- Test: `minion-agent-rust/crates/minion-agent/tests/llm_assistant_stream.rs`

**Interfaces:**
- Produces: `ScriptedAdapter`, `Script`, and `ScriptItem::{Chunk, Error}` implementing the real `LlmAdapter` seam.
- Records typed requests for assertions but performs no settlement or lifecycle interpretation.

- [ ] **Step 1: Write failing real-seam tests**

Register `ScriptedAdapter` in `LlmService`, invoke `service.stream`, and prove scripts for success, raw operational error, implicit EOF, and extra post-terminal chunks all traverse the real service and `AssistantStream` path. Assert recorded request equality.

- [ ] **Step 2: Run scripted tests and verify RED**

Run: `cargo test -p minion-agent --test llm_adapter scripted -- --nocapture`

Expected: missing scripted adapter symbols fail compilation.

- [ ] **Step 3: Implement the dumb scripted adapter**

Each invocation removes one queued `Script`; the raw stream yields its `ScriptItem`s exactly and then ends. An exhausted adapter returns an eager `AdapterStartError`. It must not synthesize terminals, normalize EOF, suppress post-terminal chunks, or inspect message state.

- [ ] **Step 4: Verify the real seam and full workspace**

Run: `cargo test -p minion-agent --test llm_adapter scripted -- --nocapture`

Run: `cargo test -p minion-agent --test llm_assistant_stream -- --nocapture`

Run: `cargo test --workspace --all-features`

Expected: all pass.

- [ ] **Step 5: Commit Task 4**

```powershell
git add minion-agent-rust/crates/minion-agent/src/llm minion-agent-rust/crates/minion-agent/tests
git commit -m "test(rust): add scripted LLM adapter"
```

### Task 5: Canonical-case checkpoint and thin adapter

**Files:**
- Inspect: `conformance/agent/*.yaml`
- Inspect: `conformance/schema/*.json`
- Create only if executable Layer-02-owned cases exist: `minion-agent-rust/crates/minion-agent/tests/llm_conformance.rs`

**Interfaces:**
- Consumes shared canonical scenarios without Rust-specific schema variants.
- May parse, construct typed requests/scripts, invoke `LlmService`, and normalize actual observations.
- Must not synthesize settlement, transform target-model history, or implement an agent loop.

- [ ] **Step 1: Re-read the committed canonical state at this checkpoint**

Classify each relevant scenario:

```text
Layer-02-owned and executable -> run through typed Rust LLM seam now
target-model transformation  -> defer to XFORM
agent-loop dependent         -> defer to Agent
placeholder                  -> retain LLM-F001 shared-contract blocker; do not invent expected values
```

- [ ] **Step 2: If a filled Layer-02 case exists, write a failing thin-runner test**

The test must load the shared YAML by repository-relative path, translate its scripted raw items into `ScriptedAdapter`, invoke `LlmService::stream`, and compare normalized public observations. Settlement remains exclusively in `AssistantStream`.

- [ ] **Step 3: Run the canonical test and verify RED for a library/adapter reason**

Run: `cargo test -p minion-agent --test llm_conformance -- --nocapture`

Expected: failure must identify missing real-library behavior or conversion, never runner-supplied semantics.

- [ ] **Step 4: Make the minimal adapter conversion pass**

Add only parsing/value conversion/result projection. If passing requires runner-side semantic logic, stop and record the relevant contract or library defect.

- [ ] **Step 5: If no case is executable, record the evidence instead of creating an empty runner**

Record exact scenario names and dispositions in `02-llm.md`. Absence of an agent runner is not a waiver for future Layer-02-owned canonical cases.

- [ ] **Step 6: Commit only if code changed**

```powershell
git add minion-agent-rust/crates/minion-agent/tests/llm_conformance.rs
git commit -m "test(rust): run canonical LLM cases"
```

### Task 6: Assurance review, documentation, and quality gates

**Files:**
- Modify: `minion-agent-rust/crates/minion-agent/src/llm/*.rs`
- Modify after parallel edits land: `minion-agent-docs/assurance/layers/02-llm.md`

**Interfaces:**
- Produces requirement-by-requirement Rust evidence for `LLM-001..LLM-021`.
- Produces independent Rust dispositions for `LLM-F006`, `LLM-F007`, `LLM-F001`, and `LLM-F002`.

- [ ] **Step 1: Perform the Rust §8-14 review**

Inspect failure model, security, reliability/operations, observability, performance/complexity, public API, and documentation. Explicitly probe adapter start failure, operational stream failure, premature EOF, double terminal, post-terminal data, raw panic, empty script, lock re-entry, request retention, and drop/cancellation behavior.

- [ ] **Step 2: Add a failing regression test for every discovered defect**

Classify findings only as `PI_PARITY_DEFECT`, `CONTRACT_ASSURANCE_DEFECT`, `PARITY_NEUTRAL_HARDENING`, `PARITY_CONSTRAINED_RISK`, or `PI_BEHAVIOR_UNCERTAIN`. Use red/green before fixes. Do not change shared semantic artifacts unilaterally.

- [ ] **Step 3: Document the public ownership boundary**

Rustdoc on `LlmAdapter`, `RawAssistantStream`, `AssistantStream`, and `LlmService` must state eager versus in-band failure, panic boundary, settlement ownership, and no-hidden-drain fusion.

- [ ] **Step 4: Run formatting and Clippy gates**

Run: `cargo fmt --check`

Run: `cargo clippy --workspace --all-targets --all-features -- -D warnings`

Expected: both exit 0.

- [ ] **Step 5: Run full tests and docs**

Run: `cargo test --workspace --all-features`

Run: `$env:RUSTDOCFLAGS='-D warnings'; cargo doc --workspace --no-deps; Remove-Item Env:RUSTDOCFLAGS`

Expected: all exit 0.

- [ ] **Step 6: Run coverage evidence if the repository command is available**

Run: `cargo xtask coverage verify`

If the command remains scaffold-only, record that factual tooling state and run `cargo llvm-cov --workspace --all-features --json --output-path target/llvm-cov.json` when installed; do not falsely claim the scoped 100% gate ran.

- [ ] **Step 7: Update the shared assurance record after parallel edits are committed**

Record Rust module/test paths, exact gate outputs, requirement dispositions, canonical scenario dispositions, new findings, and:

```text
LLM-F006: Rust requires explicit provider + api + model_id; no mock fallback.
LLM-F007: expected raw operational errors are typed values settled centrally; panics remain invariant failures.
LLM-F001: shared-contract status plus Rust-local executable/deferred scenario evidence.
LLM-F002: shared-contract status; Rust neither owns nor silently ignores manifest gaps.
```

- [ ] **Step 8: Commit code documentation and, separately, local docs evidence**

Code repository:

```powershell
git add minion-agent-rust/crates/minion-agent/src/llm
git commit -m "docs(rust): document LLM stream contracts"
```

Local docs repository, after excluding unrelated dirty files:

```powershell
git add assurance/layers/02-llm.md
git commit -m "assurance: record Rust LLM layer evidence"
```

## Final Self-Review Checklist

- [ ] Every `LLM-001..LLM-021` row maps to Rust code/tests or an explicit correct defer/N/A disposition.
- [ ] No adapter contains Minion settlement/fusion logic.
- [ ] No runner contains settlement, target-model transformation, or agent-loop semantics.
- [ ] Strict three-part model identity is tested and has no default API.
- [ ] Expected raw failures settle; panics propagate.
- [ ] Premature EOF preserves the partial, produces error settlement, and exact message text is not canonicalized.
- [ ] The first public terminal fuses without hidden drain.
- [ ] Canonical placeholders are classified by owning layer at the final committed state.
- [ ] Shared dirty files from the parallel Python/governance process were not modified.
- [ ] All verification claims cite fresh command output.
