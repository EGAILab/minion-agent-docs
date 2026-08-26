# Rust Layer 05 Tool Model + Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement and certify Rust Layer 05 through a typed tool model, one Runtime-owned scoped registry, all nine canonical scenarios, and complete Rust assurance evidence.

**Architecture:** Add model-facing schema types under `llm` and callback-bearing agent tools under a new `tools` module. `Runtime` owns one `ToolRegistry` backed only by its certified `ScopeTree` and `ScopedRegistry`; the same registry is injected into every coordinated `Context`. Scoped registrations use `ScopedRegistry`'s scope effect ownership, while unscoped registrations attach the returned idempotent handle to the registering fiber's effect store.

**Tech Stack:** Rust 2024 workspace, serde/serde_json, futures boxed futures, tokio test runtime, existing Minion Runtime primitives, serde_yaml canonical adapter.

**Spec:** `spec/tools.md`; approved closure evidence: `assurance/layers/05-tool-model-registry-rust-r005-closure.md`.

## Global Constraints

- Pinned Pi is `b7bb00b936dbe21b8e160b3e89efdec361846699`.
- Shared candidate baseline is `minion-agent@89865c05933f4e6081da4ef776e34464a8c5a523` and `minion-agent-docs@76c57584f3fcaf1ecf32e40af8939e67703312fc`.
- Do not implement Layer-06 callback invocation, validation ordering, scheduling, result conversion, cancellation behavior, provider behavior, or built-in tools.
- Do not modify Python or normative shared semantics.
- `ToolRegistry` must not cache a scope graph or own scope lifecycle state; it delegates to the existing `ScopeTree`, `ScopedRegistry`, `EffectStore`, and `RegistrationHandle`.
- Canonical Layer-05 scenarios stay in the `agent` family and are discovered dynamically.
- Every production behavior follows RED → GREEN → REFACTOR with the focused test observed failing for the intended reason before implementation.

---

### Task 1: Typed model-facing tool schema

**Files:**
- Modify: `minion-agent-rust/crates/minion-agent/src/llm/vocabulary.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/llm/mod.rs`
- Test: `minion-agent-rust/crates/minion-agent/tests/tool_model.rs`

**Interfaces:**
- Produces: `JsonSchemaObject`, `ConstrainedSampling`, `JsonSchemaStrictness`, `GrammarVariants`, and `ToolSchema`.
- `JsonSchemaObject` wraps `serde_json::Map<String, Value>` and only deserializes JSON objects.
- `ConstrainedSampling` serializes as `false`, `{type: json_schema, strict: ...}`, or `{type: grammar, variants: ...}`; `Option<ConstrainedSampling>` represents absence.
- `ToolSchema` fields are `name`, `description`, required `parameters`, and output-visible optional `constrained_sampling`.

- [ ] **Step 1: Write failing schema-container and constrained-sampling tests**

Add literal serde probes covering object-instance, string-instance, top-level `oneOf`, arbitrary members, null/bools/array/scalars, absent versus false, both strictness values, grammar `{}`/lark/regex/both, unknown grammar keys, and explicit input null.

- [ ] **Step 2: Verify RED**

Run: `cargo test -p minion-agent --test tool_model --all-features`

Expected: compile failure because the Layer-05 schema types do not exist.

- [ ] **Step 3: Implement the minimal typed schema boundary**

Use a transparent owned object newtype with `TryFrom<Value>` and serde validation. Use a custom or helper serde representation for the explicit `false` variant so `true` is rejected. Put `#[serde(deny_unknown_fields)]` on grammar variant input and retain both optional named fields.

- [ ] **Step 4: Verify GREEN and existing LLM tests**

Run:

```text
cargo test -p minion-agent --test tool_model --all-features
cargo test -p minion-agent --test llm_vocabulary --all-features
```

- [ ] **Step 5: Commit**

Commit: `feat(rust): add typed Layer 05 tool schema model`

### Task 2: Callback-bearing agent ToolDefinition

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/tools/mod.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/tools/definition.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/lib.rs`
- Extend test: `minion-agent-rust/crates/minion-agent/tests/tool_model.rs`

**Interfaces:**
- Produces: `tools::ToolDefinition`, `ExecutionMode`, `PrepareArguments`, `ExecuteTool`, `ToolExecutionRequest`, `ToolExecutionSignal`, `ToolUpdateCallback`, `AgentToolResult`, and `ToolCapabilityError`.
- `ToolDefinition` owns `name`, `description`, `JsonSchemaObject`, optional constrained sampling, required `label`, optional prepare callback, required execute callback, and optional execution mode.
- Callbacks are `Arc`-owned, `Send + Sync + 'static`; execute returns a boxed future. Layer 05 stores but never invokes either callback.
- Produces `ToolDefinition::schema() -> llm::ToolSchema` without losing schema or constrained-sampling state.

- [ ] **Step 1: Write failing public-model tests**

Test required construction, `None` versus explicit `Parallel`, projection of every metadata field, clone-safe owned callbacks, and that model/registry tests never invoke either callback (callbacks panic if invoked).

- [ ] **Step 2: Verify RED**

Run: `cargo test -p minion-agent --test tool_model --all-features`

Expected: compile failure because `minion_agent::tools` does not exist.

- [ ] **Step 3: Implement the minimal callback-bearing model**

Keep callback internals private behind public constructor/builder methods. Implement a manual `Debug` that reports metadata and capability presence without requiring callback debug support.

- [ ] **Step 4: Verify GREEN**

Run: `cargo test -p minion-agent --test tool_model --all-features`

- [ ] **Step 5: Commit**

Commit: `feat(rust): add callback-bearing agent tool definitions`

### Task 3: Runtime-backed ToolRegistry core

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/tools/registry.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/tools/mod.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/runtime/scoped_registry.rs`
- Test: `minion-agent-rust/crates/minion-agent/tests/tool_registry.rs`

**Interfaces:**
- Produces: cloneable `ToolRegistry`, `register_scoped`, `visible`, `resolve`, and `schemas`.
- Extends `ScopedRegistry` only with an untagged/global observation path and cloneable idempotent `RegistrationHandle`; existing `visible_from(ScopeId)` behavior remains unchanged.
- `visible(None)` returns global registrations in insertion order. `visible(Some(scope))` delegates liveness/ancestry/order to `ScopedRegistry` and then performs stable first-name composition.

- [ ] **Step 1: Write failing direct registry tests**

Use a real `ScopeTree` and real scopes. Cover ancestor visibility, descendant exclusion, sibling isolation, nearest shadowing, same-scope earliest-wins, fallback after withdrawal, unknown resolve, deterministic ordering, and disposed requester returning empty/absent.

- [ ] **Step 2: Verify RED**

Run: `cargo test -p minion-agent --test tool_registry --all-features`

Expected: compile failure because `ToolRegistry` does not exist.

- [ ] **Step 3: Implement minimal registry composition**

Store only `Arc<ScopedRegistry<ToolDefinition>>`. Do not add scope IDs, parent maps, activity flags, or winner caches to `ToolRegistry`. Stable deduplication happens over the already ordered visible entries; do not sort.

- [ ] **Step 4: Verify GREEN plus Runtime scope regression**

Run:

```text
cargo test -p minion-agent --test tool_registry --all-features
cargo test -p minion-agent --test runtime_scope --all-features
```

- [ ] **Step 5: Commit**

Commit: `feat(rust): add Runtime-backed tool registry semantics`

### Task 4: Authoritative Context.tools and ownership integration

**Files:**
- Modify: `minion-agent-rust/crates/minion-agent/src/runtime/coordinator.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/runtime/fiber.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/tools/registry.rs`
- Extend test: `minion-agent-rust/crates/minion-agent/tests/tool_registry.rs`
- Test: `minion-agent-rust/crates/minion-agent/tests/tool_registry_lifecycle.rs`

**Interfaces:**
- `Runtime` constructs exactly one `ToolRegistry` from its existing `ScopeTree`.
- Coordinated `FiberInitContext::tools() -> Result<&ToolRegistry, RuntimeError>` returns that registry.
- `ToolRegistry::register(&Context, ToolDefinition)` selects ownership from `context.scope()`:
  - scoped: register directly with `ScopedRegistry`; its scope effect owns removal;
  - unscoped: register globally, then attach a clone of the idempotent removal handle to the fiber effect store.

- [ ] **Step 1: Write failing real-lifecycle tests**

Use `Runtime`, real `PluginSpec`, real fibers, scopes, registration handles, `Runtime::unmount`, and `ScopeHandle::dispose`. Cover unscoped unmount withdrawal; scoped unmount survival; scoped disposal withdrawal; explicit withdrawal twice; withdrawal then scope disposal; scope disposal then plugin unmount.

- [ ] **Step 2: Verify RED**

Run: `cargo test -p minion-agent --test tool_registry_lifecycle --all-features`

Expected: compile failure because coordinated contexts have no tools surface.

- [ ] **Step 3: Add minimal Runtime plumbing and ownership logic**

Inject the existing registry clone into coordinated contexts and runtime read views. Keep standalone/uncoordinated plugin mounting explicit: `tools()` returns `RuntimeError::UncoordinatedContext`. Do not change scope or fiber disposal semantics.

- [ ] **Step 4: Verify GREEN and Runtime regressions**

Run:

```text
cargo test -p minion-agent --test tool_registry_lifecycle --all-features
cargo test -p minion-agent --test runtime_fiber --test runtime_scope --test runtime_coordinator --all-features
```

- [ ] **Step 5: Commit**

Commit: `feat(rust): expose scope-aware tools through Runtime context`

### Task 5: Thin Layer-05 canonical adapter

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/tests/tool_registry_conformance.rs`
- No shared schema/scenario changes.

**Interfaces:**
- Dynamically discovers `conformance/agent/tool-registry-*.yaml`.
- Prevalidates all fixture references before constructing `Runtime`.
- Uses real `Runtime`, `PluginSpec`, `Context::tools`, scopes, fibers, handles, resolution, enumeration, and schema projection.
- Dummy callbacks panic if invoked, proving the Layer-05 runner never executes tools.

- [ ] **Step 1: Write the canonical adapter with a discovery assertion and no semantic branches**

Define serde boundary structs matching the approved schema. Reference validation checks declaration integrity only. Expected observations are literal YAML values; do not sort or calculate winners in the adapter.

- [ ] **Step 2: Verify RED**

Run: `cargo test -p minion-agent --test tool_registry_conformance --all-features`

Expected: at least one canonical failure until all adapter construction/normalization paths call the real ToolRegistry correctly.

- [ ] **Step 3: Complete only parsing, Runtime orchestration, and observation normalization**

Do not add disposed-scope, shadowing, ordering, duplicate, or lifecycle outcome branches. The only branches permitted are scenario operation dispatch and structural reference rejection.

- [ ] **Step 4: Verify GREEN**

Run: `cargo test -p minion-agent --test tool_registry_conformance --all-features -- --nocapture`

Expected: 9 scenarios discovered, executed, and passed; zero deferred.

- [ ] **Step 5: Add/verify malformed-reference tests**

Add focused unit tests in the adapter file or a separate `tool_registry_conformance_validation.rs` for unknown parent/query/plugin/disposal/withdrawal references and cycles. Confirm validation runs before any Runtime construction helper.

- [ ] **Step 6: Commit**

Commit: `test(rust): run Layer 05 canonical tools through real Runtime`

### Task 6: Cross-language evidence and assurance

**Files:**
- Modify: `pi-parity-manifest.yaml` (Rust pointers/status only)
- Modify: `minion-agent-docs/assurance/layers/05-tool-model-registry.md`
- Create: `minion-agent-docs/assurance/layers/05-tool-model-registry-rust-implementation.md`

**Interfaces:**
- Updates TOOL-008 through TOOL-016 with actual Rust implementation/test pointers without changing approved rules or dispositions.
- Records contract approval as prior evidence and Rust implementation certification as this pass.

- [ ] **Step 1: Audit final implementation and runner thinness**

Inspect for any second scope graph, cached lifecycle state, callback invocation, runner-side ancestry/winner/sorting/removal logic, provider code, or Python changes. Any occurrence blocks certification.

- [ ] **Step 2: Update manifest Rust pointers only**

Point model rows to `llm/vocabulary.rs`, `tools/definition.rs`, and `tests/tool_model.rs`; registry/lifecycle rows to `tools/registry.rs`, Runtime context plumbing, direct registry/lifecycle tests, and canonical adapter.

- [ ] **Step 3: Write implementation assurance**

Record exact baseline, modules, API ownership, TDD evidence, nine canonical names/results, test inventory, Layer-01..04 regressions, full gates, findings, and explicit Layer-06/provider exclusions.

- [ ] **Step 4: Commit evidence separately**

Code repository commit: `docs(parity): record Rust Layer 05 evidence pointers`.

Docs repository commit: `docs(assurance): certify Rust Layer 05 implementation`.

### Task 7: Full verification and independent review

**Files:**
- Review all changed files; modify only to fix verified defects.

**Interfaces:**
- Produces the final certification evidence and integration-ready branches.

- [ ] **Step 1: Run formatting**

Run: `cargo fmt --check`

- [ ] **Step 2: Run strict linting**

Run: `cargo clippy --workspace --all-targets --all-features -- -D warnings`

- [ ] **Step 3: Run full tests**

Run: `cargo test --workspace --all-features`

- [ ] **Step 4: Run rustdoc**

Run: `$env:RUSTDOCFLAGS='-D warnings'; cargo doc --workspace --no-deps`

- [ ] **Step 5: Run canonical layout verification**

Run: `cargo run -p xtask -- conformance verify`

- [ ] **Step 6: Run schema and manifest validation using established repository commands**

Discover the current Python/shared validation entry points; execute them without modifying Python.

- [ ] **Step 7: Request independent code review**

Provide the reviewer the implementation baseline, approved contract paths, changed-file list, and explicit review matrix: schema boundary, constrained sampling, callbacks not invoked, registry ordering/shadowing, ownership split, disposed scopes, runner thinness, and Layer-06 exclusions.

- [ ] **Step 8: Address every Critical/Important review finding with a new RED/GREEN cycle**

- [ ] **Step 9: Re-run every full gate after the last change**

- [ ] **Step 10: Present branch integration options**

Do not merge or open a PR without the user's selected branch-finishing option.
