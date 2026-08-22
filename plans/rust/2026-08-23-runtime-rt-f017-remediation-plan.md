# Rust Runtime RT-F017 Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve RT-F017 by adding the minimum coordinated typed Rust Runtime/Context path for RT-008 and running canonical Runtime scenarios through a thin Rust adapter.

**Architecture:** `RuntimeCore` composes the existing `FiberHandle`, `ServiceRegistry`, `EventBus`, and `ScopeTree` primitives. `Runtime`/`Context` expose coordination and ownership routing; canonical fixtures use those APIs and observe real transitions without supplying semantics.

**Tech Stack:** Rust 2024, Tokio, futures, parking_lot, serde/serde_json, serde_yaml for integration tests.

**Spec:** `plans/rust/2026-08-23-runtime-rt-f017-remediation-design.md`

## Global Constraints

- Authority is `spec/runtime.md`, canonical `conformance/runtime/`, and `MINION-001`; Python is not the oracle.
- Do not modify Python or shared semantic artifacts.
- Preserve existing Fiber/service/event/scope semantics and reuse their public paths.
- No runtime-global lock may be held across plugin, listener, fiber-transition, or disposer awaits.
- Mount returns a `Pending` fiber before reconciliation.
- Provider revocation reconciles affected dependents from the real registration disposer.
- Do not canonicalize reconciliation aggregation, continuation, ordering, or error shape.
- Every production behavior change uses a witnessed red/green test cycle.
- Wall-clock sleeps never establish correctness.

---

### Task 1: Preserve the completed RT-F016 fix as the remediation baseline

**Files:**
- Modify: `minion-agent-rust/crates/minion-agent/src/runtime/fiber.rs`
- Modify: `minion-agent-rust/crates/minion-agent/tests/runtime_fiber.rs`

**Interfaces:**
- Consumes: existing `FiberHandle::reconcile`, `FiberHandle::dispose`, and `FiberError`.
- Produces: panic cleanup path that preserves the initializer panic and cleanup diagnostic while settling `Disposed`.

- [ ] **Step 1: Confirm the existing RT-F016 regression test fails on the committed baseline**

Add/retain a test whose assertions include:

```rust
assert!(message.contains("initializer invariant failed"));
assert!(message.contains("failing-cleanup"));
assert_eq!(fiber.state(), FiberState::Disposed);
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```text
cargo test -p minion-agent --test runtime_fiber initializer_panic_does_not_swallow_a_cleanup_failure -- --exact
```

Expected: failure because the cleanup diagnostic is discarded.

- [ ] **Step 3: Restore the audited minimal implementation**

Use one helper called from both synchronous and asynchronous initializer-panic branches. It must
call `finish_loading_cleanup`, resume the original panic if cleanup succeeds, and emit a combined
panic diagnostic containing the cleanup aggregate if cleanup fails.

- [ ] **Step 4: Run all Fiber tests**

Run `cargo test -p minion-agent --test runtime_fiber`.
Expected: 24 passing tests, including represented init+cleanup, dependency-loss cleanup, and
panic+cleanup settlement.

- [ ] **Step 5: Commit**

```text
git add minion-agent-rust/crates/minion-agent/src/runtime/fiber.rs minion-agent-rust/crates/minion-agent/tests/runtime_fiber.rs
git commit -m "runtime: preserve cleanup failures after initializer panic"
```

---

### Task 2: Add typed Runtime/Context coordination with provider appearance

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/runtime/coordinator.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/runtime/mod.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/runtime/plugin.rs`
- Test: `minion-agent-rust/crates/minion-agent/tests/runtime_coordinator.rs`

**Interfaces:**
- Consumes: `DynPluginSpec`, `FiberHandle`, `ServiceRegistry`, `EventBus`, `ScopeTree`.
- Produces:
  - `Runtime::new() -> Runtime`
  - `Runtime::with_observer(Arc<dyn RuntimeObserver>) -> Runtime`
  - `Runtime::context() -> Context`
  - `Runtime::mount(&self, DynPluginSpec, Value) -> Result<FiberHandle, PluginConfigError>`
  - `Runtime::reconcile(&self) -> Result<(), RuntimeCoordinationError>`
  - `Context::effect`, typed `provide`/`require`, listener registration, and scoped child views.
  - `FiberInitContext` remains a compatibility alias/view of the new `Context` effect surface for
    standalone primitive mounting; existing plugin initializers do not acquire a second API.

- [ ] **Step 1: Write the absent-provider test**

```rust
#[test]
fn provider_absence_keeps_a_real_runtime_dependent_pending() {
    run(async {
        let runtime = Runtime::new();
        let dependent = runtime.mount(dependent_spec(), json!({})).unwrap();
        runtime.reconcile().await.unwrap();
        assert_eq!(dependent.state(), FiberState::Pending);
    });
}
```

- [ ] **Step 2: Run it and verify RED**

Run the exact test. Expected: compile failure because `Runtime` does not exist.

- [ ] **Step 3: Implement the minimum coordinator skeleton**

Store fibers in stable mount order and evaluate each fiber's injected service names through the real
`ServiceRegistry`. Do not add service or lifecycle rules to `RuntimeCore`.

- [ ] **Step 4: Write provider-appearance activation test**

Mount dependent first, reconcile, mount a provider whose initializer calls `Context::provide`, then
reconcile and assert provider and dependent are both `Active`.

- [ ] **Step 5: Run it and verify RED**

Expected: dependent remains `Pending` until fixed-point coordination exists.

- [ ] **Step 6: Implement fixed-point appearance reconciliation**

Snapshot fibers without holding the index lock across await. Reconcile real fibers in stable mount
order until no state changes. Use real service visibility for dependency predicates.

- [ ] **Step 7: Run coordinator and existing runtime tests**

Run:

```text
cargo test -p minion-agent --test runtime_coordinator
cargo test -p minion-agent --tests
```

- [ ] **Step 8: Commit**

```text
git add minion-agent-rust/crates/minion-agent/src/runtime/coordinator.rs minion-agent-rust/crates/minion-agent/src/runtime/mod.rs minion-agent-rust/crates/minion-agent/src/runtime/plugin.rs minion-agent-rust/crates/minion-agent/tests/runtime_coordinator.rs
git commit -m "runtime: coordinate provider appearance and dependents"
```

---

### Task 3: Reconcile provider revocation inline through the real disposer

**Files:**
- Modify: `minion-agent-rust/crates/minion-agent/src/runtime/service.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/runtime/coordinator.rs`
- Test: `minion-agent-rust/crates/minion-agent/tests/runtime_coordinator.rs`

**Interfaces:**
- Consumes: `ServiceRegistration` disposal and `RuntimeCore` dependency index.
- Produces: optional registry revocation callback used by coordinated Runtime; standalone registry behavior remains unchanged.

- [ ] **Step 1: Write the inline revocation test**

Use an observer trace and assert this relative order:

```text
provider Unloading
dependent Unloading
dependent Pending
provider Disposed
```

The test must call only `runtime.unmount(provider)`; it must not call reconciliation afterward.

- [ ] **Step 2: Run it and verify RED**

Expected: dependent remains `Active` or reacts only after an explicit reconcile.

- [ ] **Step 3: Add the real revocation hook**

After `ServiceRegistry` removes the active registration, its coordinated disposer invokes the
Runtime's targeted dependent reconciler and awaits completion. The callback is absent/no-op for
standalone registries. Never hold the registry mutex while invoking it.

- [ ] **Step 4: Add two-independent-dependents coverage**

Mount two dependents of one provider and assert both activate on appearance and both return to
`Pending` during one provider unmount. Do not assert failure aggregation behavior.

- [ ] **Step 5: Run coordinator, service, and Fiber suites**

Run exact targets `runtime_coordinator`, `runtime_service`, and `runtime_fiber`.

- [ ] **Step 6: Commit**

```text
git add minion-agent-rust/crates/minion-agent/src/runtime/service.rs minion-agent-rust/crates/minion-agent/src/runtime/coordinator.rs minion-agent-rust/crates/minion-agent/tests/runtime_coordinator.rs
git commit -m "runtime: reconcile dependents during service revocation"
```

---

### Task 4: Failure-isolation semantic checkpoint

**Files:**
- Modify: `minion-agent-rust/crates/minion-agent/src/runtime/coordinator.rs`
- Test: `minion-agent-rust/crates/minion-agent/tests/runtime_coordinator.rs`
- Modify if a finding is exposed: `minion-agent-docs/assurance/layers/01-runtime.md`

**Interfaces:**
- Consumes: `Runtime::reconcile` typed error result and real fiber settled states.
- Produces: evidence about state validity; no canonical aggregation contract.

- [ ] **Step 1: Write a state-validity failure test**

Mount a plugin that returns `PluginInitError`, invoke `Runtime::reconcile`, assert the error surfaces,
and assert the failed fiber is `Failed` rather than `Loading`. Then call another safe Runtime
operation to prove the coordinator is not poisoned.

- [ ] **Step 2: Run it and verify RED or existing GREEN for the narrow invariant**

If it is already green, record that this is characterization of existing Fiber settlement, not a
new production change. Do not weaken the assertion to manufacture RED.

- [ ] **Step 3: Stop before defining sibling continuation or aggregation**

Compare the needed implementation with `spec/runtime.md`. If RT-008 can be met without specifying
sibling continuation, return the first typed error and leave aggregation unspecified. If correct
coordination necessarily exposes a choice, record a new `CONTRACT_ASSURANCE_DEFECT` or promote
RT-F012 for shared review; do not change canonical data.

- [ ] **Step 4: Run all coordinator and Fiber tests**

Expected: valid settled states and no stuck transition, regardless of returned error.

- [ ] **Step 5: Commit the characterization and any required state-safety change**

Use commit message `runtime: preserve coordinator state after reconciliation failure`.

---

### Task 5: Add synchronous runtime observation at real boundaries

**Files:**
- Modify: `minion-agent-rust/crates/minion-agent/src/runtime/coordinator.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/runtime/fiber.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/runtime/scope.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/runtime/service.rs`
- Test: `minion-agent-rust/crates/minion-agent/tests/runtime_observer.rs`

**Interfaces:**
- Produces `RuntimeObserver` callbacks carrying typed observation values.
- Default behavior is no-op; callbacks are synchronous and never control correctness.

- [ ] **Step 1: Write a global-order observer test**

Install a recording observer, activate a provider/dependent, unmount the provider, and assert the
recorded ordering comes directly from callbacks at state/service/effect boundaries.

- [ ] **Step 2: Run it and verify RED**

Expected: observer API absent.

- [ ] **Step 3: Implement no-op and recording-compatible observer plumbing**

Invoke observers after the real state mutation at each boundary and without holding runtime-global
locks. Observation failure must not alter runtime semantics; use a non-fallible callback.

- [ ] **Step 4: Prove hooks are observational**

Run the same lifecycle once with no observer and once with a recording observer; assert identical
fiber states and service resolution.

- [ ] **Step 5: Run all Runtime tests and commit**

Commit message: `runtime: expose synchronous semantic observations`.

---

### Task 6: Build the thin canonical Runtime adapter

**Files:**
- Modify: `minion-agent-rust/Cargo.toml`
- Modify: `minion-agent-rust/crates/minion-agent/Cargo.toml`
- Create: `minion-agent-rust/crates/minion-agent/tests/runtime_conformance.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/support/runtime_scenario.rs`

**Interfaces:**
- Consumes: repository-root `conformance/runtime/*.yaml`, `Runtime`, `Context`, typed events, scopes, and observer records.
- Produces: one executable integration-test runner over the complete Runtime family.

- [ ] **Step 1: Add `serde_yaml` as a dev-only dependency and parse one scenario**

Start with `reactive-dependency.yaml`. Deserialize with `deny_unknown_fields` DTOs mirroring the
shared schema. Resolve the monorepo root from `CARGO_MANIFEST_DIR`, never from a vendored copy.

- [ ] **Step 2: Run and verify RED**

Expected: trace mismatch until the adapter maps scripted plugins through `Runtime`.

- [ ] **Step 3: Implement the reactive-dependency fixture through real APIs**

Scripted plugin initializers call `Context::effect` and `Context::provide`; mount/unmount calls
`Runtime`; dependency behavior is never calculated in the adapter.

- [ ] **Step 4: Expand DTO/action coverage by semantic group**

Add groups in this order, running after each:

```text
lifecycle/effects
services including provides:{name,visible} and attempt_effect
scopes including one-step descendant cascade
emit/parallel/serial
waterfall including echo_args
expected typed errors
```

Event contracts use one real typed vocabulary:

```rust
EventSpec<Vec<serde_json::Value>, serde_json::Value>
```

Scripted listeners are mocks at the real `EventBus` seam. They may append `listener_entered` and
return/delegate scripted values; they must not filter, order, or invoke downstream listeners.

- [ ] **Step 5: Prove runner thinness by negative mutation tests**

Temporarily disable one real Runtime operation locally (for example provider-change reconciliation)
and verify `reactive-dependency` fails; restore it immediately. Likewise verify a real waterfall
behavior mutation fails its canonical scenario. Do not commit mutations.

- [ ] **Step 6: Run the full Runtime family**

Run:

```text
cargo test -p minion-agent --test runtime_conformance -- --nocapture
```

Expected: every repository-root Runtime scenario passes with exact trace/result/error comparison.

- [ ] **Step 7: Commit**

```text
git add minion-agent-rust/Cargo.toml minion-agent-rust/crates/minion-agent/Cargo.toml minion-agent-rust/crates/minion-agent/tests/runtime_conformance.rs minion-agent-rust/crates/minion-agent/tests/support/runtime_scenario.rs
git commit -m "test(runtime): execute canonical scenarios through typed runtime"
```

---

### Task 7: Verify RT-F017 and update assurance evidence

**Files:**
- Modify: `minion-agent-docs/assurance/layers/01-runtime.md`

**Interfaces:**
- Consumes: fresh command output and committed Rust paths.
- Produces: RT-F017 disposition and current overall Runtime certification status.

- [ ] **Step 1: Run formatting and lint gates**

```text
cargo fmt --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
```

- [ ] **Step 2: Run all tests and canonical Runtime conformance**

```text
cargo test --workspace --all-features
cargo test -p minion-agent --test runtime_conformance -- --nocapture
```

- [ ] **Step 3: Rerun lifecycle regression targets explicitly**

```text
cargo test -p minion-agent --test runtime_fiber
cargo test -p minion-agent --test runtime_coordinator
```

- [ ] **Step 4: Run documentation gate**

```text
RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps
```

- [ ] **Step 5: Update only Rust-produced assurance evidence**

Record coordinator/runner paths, focused test names, scenario count/result, quality-gate results,
failure-checkpoint disposition, and any new finding. Mark RT-F017 resolved only if RT-008 and every
applicable Runtime scenario traverse the real public Runtime.

- [ ] **Step 6: Re-evaluate overall layer status from present evidence**

If the shared record contains completed RT-F015 evidence, evaluate the complete gate. Otherwise
state `Rust READY; overall BLOCKED by RT-F015`. Do not infer Python completion from working-tree
files alone.

- [ ] **Step 7: Commit Rust evidence without absorbing parallel docs changes**

Stage only `assurance/layers/01-runtime.md` and the Rust code commits. Preserve every unrelated or
Python-owned working-tree change.
