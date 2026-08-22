# Rust Runtime RT-F017 Remediation Design

**Date:** 2026-08-23
**Status:** APPROVED
**Authority:** `spec/runtime.md`, `spec/authority.md`, canonical `conformance/runtime/`, and `MINION-001`
**Scope:** Rust-owned Runtime Layer blocker `RT-F017` only

## 1. Goal and boundary

Resolve both halves of `RT-F017`:

1. provide a real coordinated Rust `Runtime`/`Context` path that implements RT-008 reactive
   dependency behavior using the existing typed primitives; and
2. execute every applicable canonical Runtime scenario through a thin Rust adapter into that real
   public path.

The shared contract remains unchanged. Python remediation, later assurance layers, RT-F018 resource
hardening, and RT-F019 documentation completion are outside this pass except where the new public
surface needs accurate documentation.

## 2. Architecture

```text
typed PluginSpec / Context calls
             |
             v
Runtime / Context ---------> RuntimeObserver
             |
             v
        Arc<RuntimeCore>
          /   |    \
         /    |     \
 ServiceRegistry EventBus ScopeTree
         \    |     /
          real FiberHandle primitives
```

`RuntimeCore` composes the existing primitives. It does not reimplement their rules:

- `FiberHandle` remains the lifecycle authority;
- `ServiceRegistry` remains the registration, type-contract, exclusivity, and visibility authority;
- `EventBus` remains the dispatch and waterfall authority;
- `ScopeTree` and `ScopedRegistry` remain the scope authority;
- `RuntimeCore` owns mounted-fiber indexing, dependency-to-fiber indexing, and reconciliation
  scheduling only.

`Context` is a lightweight view containing the shared core, the current fiber ownership when used
during plugin initialization, and an optional scope. Its methods route registrations to the
appropriate existing primitive and ownership store. A scoped context routes effects and listeners
to the scope owner; an unscoped plugin context routes them to its fiber generation.

## 3. Mount and reconciliation

`Runtime::mount` validates configuration and creates a `Pending` `FiberHandle`, records it in stable
mount order, and returns it before reconciliation. `Runtime::reconcile` is explicit for initial
mount progress; provider revocation is not caller-driven.

Each fiber's dependency predicate calls the real `ServiceRegistry::require`/visibility path for all
normative injected names. Reconciliation snapshots mounted fibers in mount order, releases the
index lock, signals dependency changes, and drives their real `FiberHandle::reconcile` methods.
It repeats only while real fiber/service state changed, so provider activation in one pass can
activate dependents in the same operation without holding a runtime-global lock across awaits.

Service appearance is observed after the provider commits `Active`; the coordinator then revisits
dependent fibers. Service revocation occurs in the real service-registration disposer. That
disposer removes the service, then invokes targeted dependent reconciliation before returning, so
the dependent reaches its contract state during provider unwind and before provider disposal
settles.

No coordinator lock is held while awaiting a fiber, plugin, listener, or disposer.

## 4. Reconciliation-failure guardrail

The stable contract requires affected fibers to be re-evaluated and state to remain valid. It does
not currently define whether one failed reconciliation aborts siblings, whether multiple failures
are aggregated, or the ordering/shape of such an aggregate.

Therefore this pass does **not** make aggregate-and-continue behavior canonical. Before adding any
observable multi-failure policy, implementation pauses at a checkpoint:

1. test the minimum contract property that a failed fiber itself settles correctly and the Runtime
   remains usable;
2. inspect whether RT-008 can be satisfied without choosing pass-level failure semantics;
3. if a choice becomes externally observable or necessary, record an RT-F012-equivalent finding
   and route it through shared-contract review rather than encoding it in canonical expectations.

The initial coordinator may return the first encountered typed reconciliation error. No canonical
scenario will assert sibling continuation, aggregation, ordering, or error shape absent shared
approval.

## 5. Observation

`RuntimeObserver` receives synchronous notifications at actual library boundaries:

- fiber state transition;
- effect creation/disposal;
- service provide/revoke;
- scope disposal.

Hooks are observational only. They neither schedule reconciliation nor cause transitions. The
default observer is a no-op. The canonical adapter installs a recording observer and appends
listener-entry records from scripted listeners at their real invocation point. It never reconstructs
global ordering after execution.

## 6. Canonical adapter

The adapter lives with Rust integration tests and reads repository-root
`conformance/runtime/*.yaml` using `serde_yaml`. It defines only scenario DTOs and scripted fixtures.

Allowed responsibilities:

- parse canonical data;
- predeclare typed `EventSpec<Vec<Value>, Value>` contracts;
- create scopes and typed scripted plugins;
- mount/unmount through `Runtime`;
- call `Context` effect/service/listener APIs;
- dispatch through the real `EventBus` public path;
- collect observer/listener output and normalize typed errors to canonical labels;
- compare exact trace/result/error data.

It does not determine dependency satisfaction, reconcile fibers, filter service/event visibility,
walk descendant scopes, unwind effects, order listeners, or implement waterfall continuation.
`provides:{name,visible}`, `attempt_effect`, and `echo_args` map directly to real typed seams already
approved by Rust review.

The executing adapter remains separate from `xtask conformance verify`, whose job is repository
layout/schema provenance checking.

## 7. Testing and completion

Development follows deterministic TDD without sleeps:

1. absent provider keeps dependent pending;
2. provider activation reconciles the dependent;
3. provider revocation unloads the dependent inline;
4. independent dependents react through the same real coordinator;
5. failure checkpoint proves state validity without standardizing aggregation;
6. canonical adapter starts with `reactive-dependency`, then expands to the full Runtime family;
7. all prior RT-F011/RT-F016 fiber tests rerun unchanged.

`RT-F017` is resolved only when RT-008 passes through `Runtime`/`Context`, every applicable Runtime
scenario passes through the thin adapter, and the full Rust quality gates are green.

