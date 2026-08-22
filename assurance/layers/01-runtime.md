# Runtime Kernel — Fidelity Assurance & Certification

**Layer ID:** `01`  
**Status:** `CERTIFIED`
**Audit date:** 2026-08-23 (Python RT-F015 and Rust RT-F017 remediation complete; both
implementations execute the stable Runtime contract through their real runtime paths)
**Auditors:** Claude (Python-driven pass) and Codex (independent Rust pass)
**Python status:** `IMPLEMENTED`  
**Rust status:** `IMPLEMENTED` — the typed runtime primitives are coordinated by the real
`Runtime`/`Context` path, including provider-driven RT-008 reconciliation, and the canonical
Runtime suite executes against that path through a thin Rust adapter.

---

## 1. Scope

### Owns

Context, Fiber lifecycle, service resolution/registry, scoped registration, reactive dependency,
effects/disposal, the four event dispatch modes (`emit`/`parallel`/`serial`/`waterfall`), and
plugin config validation.

### Does not own

Application-level session/agent/tool/LLM semantics. Realms/isolation and the declarative plugin
loader are explicitly deferred by the frozen master and are out of scope for this layer.

### Depends on

No Minion layer below it. Python depends on Pydantic for config validation.

### Depended on by

Every later layer mounts against this kernel.

### Runtime-specific certification note

Runtime is Minion's primary intentional architectural divergence from Pi (`MINION-001`). It is not
a Pi runtime being reproduced. Its normative authority is the frozen Minion design, the normative
runtime spec once created, and canonical `conformance/runtime/`.

This does **not** require a runtime-only finding taxonomy. Missing or inconsistent Minion
spec/conformance/traceability/evidence is classified using the project-wide
`CONTRACT_ASSURANCE_DEFECT` class. Ordinary implementation quality findings continue to use the
other project-wide classes.

Python drives the audit/remediation sequence, but Rust must be independently checked against the
same RT-* contract before this layer can certify.

---

## 2. Normative sources

- Frozen design: `design/2026-08-20-minion-agent-design.md` §3, "The plugin runtime".
- Spec: `spec/runtime.md` — created; closes `RT-F005`.
- `/pi-parity-manifest.yaml`: `MINION-001`, disposition `intentional divergence`.
- Canonical conformance: `conformance/runtime/*.yaml`.
- Pinned Pi source: not directly applicable to this Minion-owned runtime architecture.
- Requirement-ID convention: `process/requirement-id-convention.md` (`ADOPTED`).

---

## 3. Pi behavior summary

Not applicable in the normal sense. Pi has no equivalent plugin/fiber/service runtime kernel.
Runtime-specific behavior must not leak into later Pi-visible Agent/LLM/tool/session semantics;
those surfaces are certified by their own later conformance.

---

## 4. Requirement traceability

| ID | Requirement | Source | Canonical scenario | Status |
|---|---|---|---|---|
| RT-001 | Fiber lifecycle `Pending -> Loading -> Active`, with disposal/dependency-loss/init-failure transitions matching the frozen state diagram | Frozen §3 Fiber | `failed-remains-failed`, `dependency-loss-during-loading-never-activates`, `no-fallback-stack-after-provider-disposes`, `double-unmount-disposes-effects-once`, `pending-fiber-disposes-directly-without-unloading` | COVERED |
| RT-002 | `Failed` is stable; dependency changes never auto-retry a failed plugin | Frozen §3 Fiber | `failed-remains-failed` | COVERED |
| RT-003 | Loading is transactional; invalidated load cannot commit ACTIVE or race owned effects against unwind | Frozen §3 Fiber | `dependency-loss-during-loading-never-activates` | COVERED/PARTIAL MECHANISM |
| RT-004 | Service identity is `(name, realm)` and compares name by string value | Frozen §3 Service resolution | `service-exclusivity`, `reactive-dependency`, `no-fallback-stack-after-provider-disposes` | **DISPOSED — COVERED BY CONSTRUCTION** (see `spec/runtime.md` RT-004: realm is deferred, and every string-name comparison in this runtime is already value-based by construction) |
| RT-005 | Registration is exclusive; duplicate provider raises, with no last-wins/priority behavior | Frozen §3 Service resolution | `service-exclusivity` | COVERED |
| RT-006 | No fallback stack; disposing a provider does not resurrect an older provider | Frozen §3 Service resolution | `no-fallback-stack-after-provider-disposes` | COVERED |
| RT-007 | Service visibility is ACTIVE-gated; `check` may narrow visibility | Frozen §3 Service resolution | `reactive-dependency` (ACTIVE-gating), `check-predicate-narrows-visibility-beyond-active` (check) | COVERED |
| RT-008 | Dependents reconcile when a resolved provider appears/disappears | Frozen §3 reactive dependency | `reactive-dependency` | COVERED |
| RT-009 | Scoped registration context owns both visibility and teardown | Frozen §3 Scoped registration | `scoped-registration-visibility` | COVERED |
| RT-010 | Scoped registration visibility inherits down to descendants, never up | Frozen §3 Scoped registration | `tests/runtime/test_scoped_registry.py` (Python unit test, not canonical YAML conformance — see §4 Coverage notes) | COVERED |
| RT-011 | Scoped event admission extends up; ancestor listeners see descendant dispatch, never reverse; untagged participates everywhere | Frozen §3 Scoped registration | `scoped-event-admission` | COVERED |
| RT-012 | Disposing a scope removes its own + descendants' registrations, not ancestors/siblings, in reverse creation order | Frozen §3 Scoped registration | `nested-scope-disposal`, `disposing-a-scope-cascades-to-a-still-live-descendant` | COVERED |
| RT-013 | `ctx.effect(fn)` runs immediately and disposers unwind in reverse order | Frozen §3 Effects | `effect-reversal` | COVERED |
| RT-014 | Double disposal is a no-op | Frozen §3 Effects | `double-unmount-disposes-effects-once` | COVERED |
| RT-015 | Creating an effect on an already-disposed owner raises | Frozen §3 Effects | `effect-after-fiber-disposed-raises` | COVERED |
| RT-016 | `emit`/`parallel`/`serial`/`waterfall` obey the frozen awaited/order/return matrix; mode mismatch is a startup error | Frozen §3 Events | `dispatch-mode-mismatch-is-startup-error` (mismatch), `emit-dispatch-is-synchronous-registration-order`, `parallel-dispatch-is-awaited-with-no-return`, `serial-dispatch-returns-last-listener-value` (per-mode matrix) | COVERED |
| RT-017 | Waterfall short-circuit: listener not calling `next` terminates the chain with its own return | Frozen §3 Waterfall | `waterfall-short-circuit` | COVERED |
| RT-018 | Waterfall delegation: `next()` runs downstream and returns downstream result unless transformed | Frozen §3 Waterfall | `waterfall-baseline-delegation` | COVERED |
| RT-019 | Waterfall replacement args propagate through `next(*replacement)` | Frozen §3 Waterfall | `waterfall-replacement-args-reach-downstream-listener` | COVERED |
| RT-020 | Waterfall `next` may be called at most once | Frozen §3 Waterfall | `waterfall-next-called-twice` | COVERED |
| RT-021 | Waterfall declares explicit terminal continuation, including zero-listener empty chain | Frozen §3 Waterfall | `waterfall-terminal-continuation`, `computed-waterfall-terminal`, `empty-waterfall-chain-yields-terminal` | COVERED |
| RT-022 | Scope filtering is additive; no-scope dispatch admits only untagged listeners | Frozen §3 Waterfall | `scoped-event-admission`, `unscoped-dispatch-admits-only-untagged` | COVERED |
| RT-023 | Plugin config validates through Pydantic; JSON Schema export is available where required | Frozen §3 Config | none | **DISPOSED** — `spec/runtime.md` RT-023: Python-specific mechanism, outside the language-neutral runtime contract, no canonical conformance evidence required |

All 23 RT-* requirements have a specification disposition and applicable cross-language evidence.
Rust's coordinated `Runtime`/`Context` path now proves RT-008, and its thin adapter executes all 26
canonical Runtime scenarios against the typed library (RT-F017 resolved). Python's RT-012 evidence
defect is also resolved: descendant traversal runs through the real `minion_agent.runtime`
`ScopeTree`/`Scope.dispose()`, not the conformance runner (RT-F015).

### Coverage notes

Existing scenarios that are valuable but not named one-for-one in the frozen §8 list remain valid
coverage. Requirement IDs and scenario filenames are not required to be 1:1.

The current consolidated `scoped-registration-visibility` scenario appears to cover both visibility
and ownership semantics even though frozen §8 names visibility and ownership separately.
**Resolved (`RT-F003`):** kept consolidated — one scenario already exercises both properties
without artificial duplication. Frozen §8's separate naming is descriptive prose, not a
scenario-count requirement; splitting it would not add coverage. The frozen master file is edited
only by its owner, so this disposition is recorded here rather than as an edit to §8 itself.

RT-010's evidence is a Python unit test (`tests/runtime/test_scoped_registry.py`), not a canonical
`conformance/runtime/*.yaml` scenario. `ScopedRegistry.visible_from()` is the kernel primitive that
implements inherit-down visibility, but it has no plugin/mount-facing surface in `Context` yet — no
concrete registry (tools, prompt sections) wires it in until a later phase builds one, and the
runtime scenario DSL only exercises what a mounted plugin can reach through `ctx`. Inventing
synthetic DSL surface just to poke at an unwired primitive was rejected in favor of testing it
directly, which is both cheaper and more precise. This is accepted as sufficient evidence for now,
but it was initially Python-only. Rust now has equivalent direct evidence in
`runtime_scope.rs::scoped_entries_are_visible_nearest_first_without_sibling_or_descendant_leaks`;
true canonical cross-language
conformance should be added once a real registry wires this primitive to the plugin surface.

Two runner changes landed alongside this batch of scenarios, beyond new `.yaml` files: (1) the
`provides` plugin field now optionally takes `{name, visible}` instead of a bare string, so a
scenario can register a service whose `check` predicate always fails — closing RT-007's `check`
half. (2) A new `attempt_effect` step lets a scenario call `ctx.effect()` against an already-mounted
plugin's context from outside its own `apply()` body, which is the only way to reach a fiber in a
state its own load-time code can't observe — closing RT-015. (3) A new `echo_args` listener action
returns the positional arguments a listener actually received (minus the trailing `next`), so a
downstream listener can prove what it was called with — closing RT-019. All three are
`conformance/**`/schema changes and fall under the shared-contract reviewer rule. The independent
Rust review approved all three; see the shared-contract verdict below.

**RT-F015 fix — real implementation path and runner-purity evidence.** `ScopeTable.dispose()` in
`tests/conformance/runner.py` used to compute the set of live descendant scopes itself (walking
`ScopeKey.chain()` against every tracked name) and call `.dispose()` on each, deepest first — the
runner was supplying RT-012's ownership/traversal semantics rather than exercising them. The real
`minion_agent.runtime` package had no equivalent capability at all: `Scope` carried no reference to
its children, and `Context.scope()` minted a bare, disconnected `Scope` per call. Fixed by adding a
new real primitive, `ScopeTree` (`scope.py`, exported from `minion_agent.runtime`), shared by a
`Context` and everything `extend()`d from it the same way `_registry`/`_events`/`_plugins` are
shared. `Context.scope()` now registers every minted `Scope` into that tree, and `Scope.dispose()`
itself — the same method any real application calls, not a special test-only entry point — looks up
its own live children through the tree and disposes them first, deepest first, before unwinding its
own registrations. A new `on_disposed` hook (mirroring `Fiber.on_state_change`) lets an observer see
every actual disposal, direct or cascaded, without computing the scope graph itself.
`ScopeTable.dispose()` is now exactly `await self.live[name].dispose()` — lookup and invocation, no
traversal. Verified with a throwaway repro script before writing anything down (disposing an
ancestor scope while a descendant was still live, with no `dispose()` call on the descendant at all,
correctly cascaded in the right order), then made permanent as a new canonical scenario,
`disposing-a-scope-cascades-to-a-still-live-descendant`, plus three new `test_scope.py` unit tests.
The existing `nested-scope-disposal` scenario never actually exercised multi-level cascade in one
step (it disposes each scope explicitly, bottom-up) — the new scenario is the first canonical
evidence that a single `dispose_scope` step correctly sweeps a still-live descendant through the
real runtime. No schema/DSL change was needed or made.

Writing `emit-dispatch-is-synchronous-registration-order.yaml` also surfaced a real runner bug: every
listener the runner built was an `async def`, but `EventBus.emit()` calls listeners with a plain
`callback(*args)` and never awaits the result. An async listener under `emit` therefore returned an
unawaited, never-run coroutine — the listener's body silently never executed. Fixed in `runner.py`
by building non-delegating actions (`raise`, `echo_args`, `short_circuit`, `observe`) as plain
synchronous functions; only the three actions that must await `next` (`delegate`, `transform`,
`delegate_twice`) stay `async def`, and those are only ever exercised under `waterfall`, whose
`_call()` helper already unwraps a returned awaitable. This is a conformance-runner fix, not a
runtime-implementation change: `EventBus.emit()`'s behavior was already correct per RT-016; the
runner's listener factory just couldn't observe it.

---

## 5. Implementation inventory

Python inventory, deep-audited against the RT-* table in §4 by reading every module in full and
checking its actual behavior against the traced requirements (not just the requirement prose):

| File/module | Responsibility | Decision | Evidence |
|---|---|---|---|
| `context.py` | Context/service access/extend, `ctx.effect`/`ctx.on`/`ctx.provide` routing to fiber or scope ownership | audited, matches RT-* as traced | RT-004, RT-007, RT-008, RT-009, RT-013, RT-015 |
| `disposable.py` | disposer collection and unwind | audited, matches RT-* as traced — `dispose_all()` is idempotent at the list level, reverse-order, and collects all failures into one `ExceptionGroup` rather than stranding later disposers | RT-013, RT-014 |
| `errors.py` | runtime error hierarchy (`RuntimeError_` base) | audited — see `RT-F009`: `registry.py`'s cycle guard raises a bare builtin `RuntimeError`, not this hierarchy | — |
| `events.py` | dispatch modes/waterfall/scope admission | audited, matches RT-* as traced | RT-016..RT-022 |
| `fiber.py` | Fiber lifecycle | audited, matches RT-* as traced — `_LIVE_STATES` gates `effect()` for every non-live state, not only `DISPOSED`; `dispose()` only announces `UNLOADING` when leaving `ACTIVE` | RT-001..RT-003, RT-015 |
| `plugin.py` | `PluginSpec`, the `@plugin` decorator, `spec_of()` resolution | audited, matches RT-* as traced — no reconciliation logic lives here despite the file inventory's original RT-001 pairing; that belongs to `registry.py` | RT-023 (config model attachment only) |
| `registry.py` | `PluginRegistry`: mount/unmount/reconcile | audited — reconciliation loop matches RT-001/RT-008 (loads satisfied PENDING fibers, unloads unsatisfied ACTIVE fibers, repeats to a fixed point); see `RT-F009` for the cycle-guard exception-type inconsistency | RT-001, RT-008 |
| `scope.py` | `ScopeKey`/`Scope` mechanics, `ScopeTree` (added this pass, RT-F015) | `Scope.dispose()` now settles live descendants itself via a shared `ScopeTree`, deepest first, before its own registrations — real RT-012 cascading ownership, not runner-computed | RT-009, RT-012 |
| `scoped_registry.py` | `ScopedRegistry`: inherit-down visibility query | audited, matches RT-010 exactly (own scope, then ancestors nearest-first, then untagged) — still has no plugin-facing wiring, per RT-010's disposition in §4 | RT-010 |
| `service.py` | `ServiceRegistry`/`Impl`: exclusive registration, ACTIVE+check visibility | audited, matches RT-* as traced | RT-004..RT-007 |

The original inventory paired RT-004/RT-005/RT-006 evidence with `registry.py`; that was wrong —
`registry.py` is the *plugin* registry (mount/reconcile, RT-001/RT-008), and `service.py` is the
*service* registry (RT-004..RT-007). Corrected above.

### Rust inventory and disposition

The independent Rust pass read every module under
`minion-agent-rust/crates/minion-agent/src/runtime/` in full and assessed it against RT-001..RT-023.
Python was used only as a risk hint and runner-boundary check, not as semantic authority.

| Rust module | Disposition | RT-* evidence and action |
|---|---|---|
| `identity.rs` | RETAIN | Value-based service names and owner identity support RT-004; Rust `TypeId` is not a semantic key. |
| `error.rs` | RETAIN | Concrete runtime errors preserve expected-failure boundaries. |
| `disposable.rs` | RETAIN | Reverse sequential, attempt-all, idempotent disposal supports RT-013/RT-014. |
| `fiber.rs` | RETAIN + HARDEN | Strong RT-001..RT-003/RT-013..RT-015 implementation. RT-F016 fixed the panic-plus-cleanup diagnostic loss; coordinated dependency notification remains outside this module. |
| `plugin.rs` | RETAIN | Typed config/mount construction remains the Fiber factory; the coordinator supplies its dependency predicate, typed initialization context, and state observer without duplicating lifecycle semantics. |
| `service.rs` | RETAIN + HARDEN | Correct exclusivity, retained name/type contract, ACTIVE/check visibility and no fallback (RT-004..RT-007). Provider-registration disposal now notifies the coordinator without holding the registry lock across reconciliation (RT-008). |
| `scope.rs` | RETAIN + HARDEN | Real `ScopeTree::dispose` recursively settles descendants before the parent and preserves sibling/ancestor isolation (RT-009/RT-012); disposed nodes are retained indefinitely (RT-F018). |
| `scoped_registry.rs` | RETAIN + HARDEN | Correct inherit-down admission (RT-010); removed entries leave permanent tombstones (RT-F018). |
| `event.rs` | RETAIN | Real event path provides fixed snapshot admission, ordering/concurrency, waterfall delegation/replacement/single-next/terminal semantics (RT-011, RT-016..RT-022). |
| `mod.rs` and crate exports | RETAIN + HARDEN | Public surface is coherent but largely undocumented (RT-F019). |
| `coordinator.rs` (`RuntimeCore`, `Runtime`, coordinated `Context`) | RETAIN | Thin composition layer over the existing service/event/scope/Fiber primitives. It owns stable mount order and dependency reconciliation; provider appearance and revocation drive dependents through the real Fiber path (RT-008). |
| `tests/support/runtime_scenario.rs` + `tests/runtime_conformance.rs` | RETAIN as conformance adapter | Deserializes canonical scenarios, builds scripted fixtures through typed public seams, records synchronous runtime observations, and normalizes results. It contains no Fiber, service, scope, event, or waterfall semantics. All 26 scenarios pass. |

The remediation preserved the audited primitives and added only coordination and conformance
surfaces around them. Bounded retention and public documentation remain separately recorded
hardening work (RT-F018/RT-F019).

---

## 6. Existing-test audit

Python `tests/runtime/`'s 15 files (133 tests, all passing) read in full and each run individually
to confirm current pass state before classifying:

```text
KEEP                 solid unit-level test, stays as implementation-detail coverage
STRENGTHEN           real gap or weak assertion worth fixing
MOVE TO CONFORMANCE  tests cross-language-relevant behavior that duplicates/should replace a scenario
REWRITE              tests something real but is structured badly (asserts internals, not behavior)
DELETE               redundant with canonical conformance, adds nothing as a unit test
```

| File | Verdict | RT-* | Reason |
|---|---|---|---|
| `test_context_access.py` | KEEP | RT-004 | `ctx.tools`/`ctx.require()` two-views-one-mechanism, layering (child can't shadow parent) |
| `test_disposable.py` | KEEP | RT-013, RT-014 | Reverse order, idempotency, async disposers, `ExceptionGroup` aggregation at the `DisposableList` primitive |
| `test_edges.py` | KEEP | RT-001, RT-015 | Deliberate misuse-guard/edge-branch coverage (effect/provide/on outside a plugin, unloading a pending fiber, disposed-scope effect variants) |
| `test_events_async.py` | KEEP | RT-016 | Proves genuine *concurrent* interleaving for `parallel` (via `asyncio.Event` timing), not just registration order — stronger evidence for the "concurrent" column than the canonical scenario, which only proves awaited+no-return |
| `test_events_emit.py` | KEEP | RT-016 | `emit` registration order, prepend, disposer removal, argument passing, mode rules, at the `EventBus` primitive |
| `test_events_scoped.py` | KEEP | RT-011, RT-022 | Admission-direction unit coverage; `test_unscoped_dispatch_admits_only_untagged_listeners` already proved RT-022's no-key case at the `EventBus` level before the canonical scenario existed — complementary, not redundant, since it isolates the primitive from plugin-mount machinery |
| `test_events_waterfall.py` | KEEP | RT-017..RT-021 | Core waterfall mechanics; `test_replacement_arguments_reach_downstream_listeners` already proved RT-019 at the `EventBus` level before the canonical scenario existed — same complementary relationship |
| `test_events_waterfall_terminal.py` | KEEP | RT-021 | Computed-terminal cases: constant, empty-chain, lone-transform-not-discarded, async-computed, callable-escape-hatch |
| `test_fiber.py` | KEEP | RT-001..RT-003, RT-013..RT-015 | The core `Fiber` lifecycle unit suite — every state transition, idempotent dispose, effect ordering, FAILED path |
| `test_plugin.py` | KEEP | none | Pure `PluginSpec`/decorator/`spec_of()` API-shape tests; Python-specific ergonomics, not a cross-language behavioral contract |
| `test_properties.py` | KEEP | RT-001, RT-008, RT-009, RT-011..RT-014 | Hypothesis property tests generalizing what fixed-example scenarios pin (arbitrary scope depth, arbitrary mount/unmount cycles) — strengthens confidence beyond the canonical examples' fixed sizes |
| `test_public_surface.py` | KEEP | none (§8-14 material) | Public `__all__` surface, no-Cordis-in-identifiers, layering purity (runtime doesn't import higher layers) — relevant to the still-unstarted Public API review, not requirement traceability |
| `test_reactive.py` | KEEP | RT-001, RT-008, RT-013, RT-023 | Dependent pending/active/reload cycle, config validation timing, one-reconcile cascade through a dependency chain |
| `test_scope.py` | KEEP | RT-009, RT-012, RT-015 | Scope nesting/ownership/disposal; `test_effect_on_a_disposed_scope_raises` is RT-015's *scope*-owner evidence, complementing the canonical scenario's fiber-owner case (see `RT-F008`). Three tests added this pass (RT-F015): `test_disposing_a_parent_scope_disposes_a_still_live_child_first`, `test_disposing_a_child_scope_leaves_the_parent_live`, `test_on_disposed_fires_once_for_direct_and_cascaded_disposal` — direct `ScopeTree`/`Scope.dispose()` cascade evidence |
| `test_scoped_registry.py` | KEEP | RT-010 | Already RT-010's evidence of record in §4 |
| `test_service.py` | KEEP | RT-004..RT-007 | Exclusive registration, no-fallback, ACTIVE-gating, and `test_check_predicate_narrows_visibility` proving RT-007's check half at the `ServiceRegistry` level, predating the canonical scenario |

No file merits `STRENGTHEN`/`REWRITE`/`DELETE`/`MOVE TO CONFORMANCE`. The suite is uniformly
well-scoped: unit tests exercise primitives directly (`EventBus`, `ServiceRegistry`, `DisposableList`,
`Fiber`) with fake owners and no plugin-mount machinery, while canonical `conformance/runtime/*.yaml`
scenarios exercise the same behavior through the real plugin/mount/dispatch surface a second
implementation must reproduce. Several unit tests independently reached the same conclusion the new
canonical scenarios pin (RT-007, RT-019, RT-022) before those scenarios existed — cross-corroborating
rather than duplicating, since each operates at a different level.

`tests/test_composition.py` and `tests/test_agent_composition.py` were checked and excluded: both
mount `llm_plugin`/`session_plugin`/`agent_loop_plugin`/etc. and assert on LLM/session/agent-loop
behavior. They exercise the runtime kernel only incidentally as the mounting mechanism; their
assertions are about those higher layers, not this one, so they belong to those layers' own
existing-test audits, not this one.

### Rust existing-test classification

All 72 pre-audit Rust runtime tests were read and run through the real runtime primitives. The
RT-F011/RT-F016 probe added three focused lifecycle tests. RT-F017 then added ten coordinator
tests, four synchronous-observer tests, and one canonical harness test that executes all 26 shared
scenarios.

| Rust test target | Verdict | RT-* | Reason |
|---|---|---|---|
| `runtime_disposable.rs` | KEEP | RT-013, RT-014 | Direct reverse-order, attempt-all, idempotence, concurrent-join, and cancellation-safety evidence. |
| `runtime_fiber.rs` | STRENGTHEN (done) | RT-001..RT-003, RT-013..RT-015 | Real lifecycle path. Added represented init+cleanup failure, dependency-loss cleanup failure, and panic+cleanup failure probes; RT-F016 fixed. |
| `runtime_service.rs` | KEEP | RT-004..RT-008 | Direct typed service identity, exclusivity, ACTIVE/check visibility, retained type contract and no-fallback evidence; the coordinator tests now prove its real revocation seam drives RT-008. |
| `runtime_scope.rs` | KEEP | RT-009, RT-010, RT-012, RT-015 | Includes the required Rust-specific RT-010 proof: `scoped_entries_are_visible_nearest_first_without_sibling_or_descendant_leaks` exercises the real `ScopedRegistry`. |
| `runtime_event.rs` | KEEP, one REWRITE | RT-011, RT-016..RT-022 | Real event path, including deterministic parallel and deep waterfall tests. `the_first_terminal_is_retained_when_a_contract_is_redeclared` should be rewritten as an implementation-hardening test because first-terminal-wins redeclaration is not a specified shared behavior. |
| internal `event.rs` unit test | KEEP | RT-021 | Stack-safety evidence for a deep waterfall through the real dispatcher. |
| `runtime_coordinator.rs` | KEEP | RT-001..RT-003, RT-008 | Proves absent-provider pending state, provider-driven activation/revocation, multiple dependents, settled failure state, RT-008 reaction before an unrelated first error, loading invalidation without self-join, settlement of every affected dependent when one cleanup fails, and the public coordinated `Runtime::context()` read view. |
| `runtime_observer.rs` | KEEP | RT-001, RT-009, RT-012, RT-013 | Proves observations occur synchronously at real state/effect/scope boundaries, never drive semantics, and may re-enter Fiber state inspection without deadlocking. |
| `runtime_conformance.rs` | KEEP as canonical evidence | RT-001..RT-022 as dispositioned in §4 | Iterates all 26 shared scenarios through `tests/support/runtime_scenario.rs`, which performs parsing, typed fixture setup, invocation, and projection only. |
| `xtask` tests | KEEP as tooling tests | none | Validate command parsing/layout only; they are not Runtime semantic or canonical evidence. |

The new canonical harness is separate from primitive tests and traverses a thin adapter into the
same real typed APIs; no test-only lifecycle, service, scope, or event implementation was added.

---

## 7. Missing test / conformance coverage

### Canonical conformance

All previously-missing canonical scenarios are now written and passing:

- [x] RT-001 Pending-direct-to-Disposed edge — `pending-fiber-disposes-directly-without-unloading`
- [x] RT-006 no fallback stack — `no-fallback-stack-after-provider-disposes`
- [x] RT-007 check-predicate narrowing — `check-predicate-narrows-visibility-beyond-active`
- [x] RT-014 double disposal — `double-unmount-disposes-effects-once`
- [x] RT-015 effect after disposed owner — `effect-after-fiber-disposed-raises`
- [x] RT-016 mode-mismatch startup error — `dispatch-mode-mismatch-is-startup-error`
- [x] RT-016 per-mode matrix — `emit-dispatch-is-synchronous-registration-order`,
  `parallel-dispatch-is-awaited-with-no-return`, `serial-dispatch-returns-last-listener-value`
- [x] RT-017 waterfall short-circuit — `waterfall-short-circuit`
- [x] RT-018 waterfall baseline delegation — `waterfall-baseline-delegation`
- [x] RT-019 replacement-argument propagation — `waterfall-replacement-args-reach-downstream-listener`
- [x] RT-021 zero-listener terminal — `empty-waterfall-chain-yields-terminal`
- [x] RT-022 dispatch with no scope key — `unscoped-dispatch-admits-only-untagged`
- [x] RT-012 descendant-scope disposal through the real runtime, not the runner —
  `disposing-a-scope-cascades-to-a-still-live-descendant` (RT-F015)

RT-004 and RT-010 have non-canonical-scenario evidence instead (COVERED-BY-CONSTRUCTION and
Python-unit-test respectively — see §4). RT-023 is DISPOSED, no evidence required.

### Language-specific / property / concurrency / fault tests

Assessed as part of §6: `tests/runtime/test_properties.py` already provides Hypothesis property
coverage for disposal-order/idempotency, mount/unmount churn, arbitrary scope depth, and arbitrary
admission-chain depth. `test_events_async.py::test_parallel_runs_listeners_concurrently` is a genuine
concurrency test (timing-ordered via `asyncio.Event`), and `test_disposable.py`/`test_fiber.py` cover
the fault-injection case of a disposer raising mid-teardown. Rust's equivalent property/concurrency/
fault coverage is unassessed — part of the independent Rust cross-check in §17.

---

## 8. Failure model

Every raised exception across the 10 modules was checked for type, message content, and whether any
path swallows a failure instead of surfacing it.

`ServiceConflictError` names the fiber already holding the service (`service.py:62`, `<{holder}>`).
`InactiveFiberError` names the fiber and its current state (`fiber.py`) or carries the effect label
for a disposed scope (`context.py`'s `_scoped_effect`). `ServiceNotFoundError` names the missing
service (`context.py`, both `__getattr__` and `require()`). `EventModeError` names the event and both
modes in conflict. `WaterfallError` names the event and listener index. All five carry enough to act
on; none is under-informative.

`disposable.py`'s `dispose_all()` is the one place a failure could be swallowed, and it isn't: every
disposer runs regardless of an earlier one failing, failures are collected, and a non-empty list is
re-raised as one `ExceptionGroup` rather than dropped.

Two raise sites used the bare builtin `RuntimeError` instead of the project's own `RuntimeError_`
hierarchy — `context.py`'s `ctx.effect()`/`ctx.provide()` guards for "called outside a fiber",
reachable by calling either directly on a root/unscoped context. This is the same defect class as
`RT-F009` (found in a different file). See `RT-F010` — fixed.

## 9. Security

Reviewed: `ServiceRegistry.provide()`'s exclusivity, `InactiveFiberError` coverage after disposal, and
whether scope isolation extends past registration visibility.

**Exclusivity is unbypassable.** `_impls` is a private dict touched only through `provide()` (checks
`existing is not None` before writing) and the closure `revoke()` returns (deletes only `if
self._impls.get(name) is impl`, so a stale revoke from a superseded registration can't delete a
newer one under the same name). No code path writes to `_impls` any other way.

**Disposed/inactive-fiber misuse is fully rejected, not just at `effect()`.** `ctx.provide()` and
`ctx.on()` (when fiber-owned) both route through `self.effect(...)` → `Fiber.effect()`, which checks
`_LIVE_STATES` (`LOADING`/`ACTIVE` only) on every call — not cached, so a stale `ctx` reference used
after the fiber has moved to `FAILED`/`UNLOADING`/`PENDING`/`DISPOSED` is rejected every time, not
just once. A scope-owned effect gets the equivalent guard in `_scoped_effect()`. No use-after-dispose
path was found.

**Scope isolation is bounded to registration visibility, by design, not by accident.** A child
context's `extend()` shares the same `_registry`/`_events`/`_plugins` objects as its parent (this is
intentional — scoping varies registrations within one shared service, per `spec/runtime.md`'s scoped
registration section, not object-level isolation). There is no separate "private state per scope"
concept for a descendant to reach into; the only isolation the design claims is over registration
visibility (RT-009/010), and that claim holds.

No security finding. This category is solid.

## 10. Reliability

Walked `Fiber.load()`/`unload()`/`dispose()` and `PluginRegistry.reconcile()` for any window where a
mid-transition exception could leave state inconsistent, and checked what a disposer raising during
teardown actually does — reproduced with a throwaway script before writing anything down, per this
project's standing verification discipline.

**Confirmed and fixed: a disposer raising during `unload()`/`dispose()`/`load()`'s failure-unwind
left the fiber permanently stuck in a non-terminal state.** All three methods called
`self._disposables.dispose_all()` (via `_unwind()`) and only transitioned to the terminal/settled
state on the *next* line — so when `dispose_all()` raised its aggregated `ExceptionGroup`, the state
transition never ran. Reproduced directly: a fiber with one effect whose disposer raises, `unload()`d,
ends up stuck at `unloading` forever. See `RT-F011` — fixed with `try`/`finally` in `fiber.py`, three
new regression tests in `test_fiber.py`.

**Open, not fixed: `PluginRegistry.reconcile()`'s two-pass loop aborts entirely if any one fiber's
`load()`/`unload()` raises**, even after `RT-F011`'s fix (each individual fiber now reaches a valid
state before the exception propagates, but sibling fibers still awaiting action in the same
reconcile pass are left unprocessed until some later mount/unmount call triggers another pass). See
`RT-F012` — recorded, not fixed; the correct shape mirrors `disposable.py`'s own aggregate-and-continue
pattern one level up, which is a larger, riskier change than this pass's other fixes.

## 11. Observability

Checked whether every state transition and effect is actually observable from outside via the
`on_state_change`/`on_effect` hooks, and whether the primary mount API gives a caller the chance to
attach them before anything happens.

**Confirmed real gap: `ctx.plugin()` — the API actually used throughout `tests/conformance/
agent_runner.py` and most of `tests/runtime/`'s own test suite — mounts and reconciles before
returning the fiber.** `Context.plugin()` calls `self._plugins.mount(...)` then immediately `await
self._plugins.reconcile()`, and only then returns the fiber. A caller receiving that fiber has missed
every transition through the first `reconcile()` call — `LOADING`, and possibly straight to `ACTIVE`
or `FAILED` — with no way to have attached `on_state_change`/`on_effect` in time to observe them. The
only way to observe from `PENDING` onward is the lower-level two-step
(`ctx.plugins.mount(...)`; attach hooks; `await ctx.plugins.reconcile()`) that the conformance
runner's own `execute_step()` uses — which works, but isn't what the ergonomic, documented `ctx.plugin()`
entry point offers. See `RT-F013` — recorded, not fixed (closing it means an API decision: hook
parameters on `ctx.plugin()`, or a documented two-step contract — not a small isolated change).

Everything reachable once hooks are attached in time is fully observable: every `_transition()` call
fires `on_state_change`, every effect creation/disposal fires `on_effect`, and nothing in the 10
modules changes state or disposes an effect without going through one of those two choke points.

## 12. Performance

Reviewed for accidentally-quadratic patterns, not benchmarked (no perf harness exists and building
one is out of scope for this review).

`ServiceRegistry`/`ScopedRegistry`/`EventBus` are all dict/list-based with `O(1)`/`O(n)` operations
appropriate to their size. `PluginRegistry.reconcile()`'s two-pass-per-iteration loop, bounded by
`_MAX_PASSES = 100`, costs `O(fibers × passes)`; the pass count is bounded by dependency-chain depth,
not fiber count squared — a chain of depth *D* genuinely needs *D* passes to cascade-activate, which
is inherent to the reconciliation algorithm's correctness, not a scaling defect. `EventBus._chain()`
recomputes its admitted-listener list fresh on every dispatch with no caching, which is fine at
realistic listener counts (tens, not thousands) and keeps admission correct if listeners change
between dispatches — caching would need invalidation logic to stay correct, trading simplicity for
performance nobody currently needs.

No performance finding. This category is solid at the scales this runtime is designed for.

## 13-14. Public API and documentation

Read `src/minion_agent/runtime/__init__.py`'s exports and `tests/runtime/test_public_surface.py`
(which pins `__all__` to a literal expected set, checks every exported name resolves, checks no
`cordis` leaks into public identifiers, and checks the runtime package imports no higher layer — all
mechanical regression guards, not a completeness check against what *should* be exported).

**Confirmed and fixed: `PluginRegistry` was not exported**, despite being the return type of the
widely-used `ctx.plugins` property (`ctx.plugins.mount()`/`.unmount()`/`.reconcile()` appear
throughout the test suite and the conformance runner) and despite its siblings `ServiceRegistry` and
`EventBus` — accessible the same way via `ctx.registry`/`ctx.events` — both being exported. The
mechanical `test_all_matches_expected_surface` check couldn't have caught this on its own: it only
pins whatever `__all__` already contains, so an omission from day one stays invisible to it forever.
See `RT-F014` — fixed.

Checked `spec/runtime.md` against the actual public surface and behavior for drift: none found. The
dispatch-mode matrix, waterfall mechanics, fiber lifecycle diagram, and service-resolution rules all
match what the source does. (Not touching `spec/runtime.md` itself — shared-contract file, outside
this task's scope even to note a typo in.)

---

### Rust §8-14 assurance review

- **Failure model:** expected initialization and cleanup failures use typed `Result` errors; invariant
  panics remain panics. Every represented cleanup-failure path examined settles `Failed`, `Pending`,
  or `Disposed` before returning the error. RT-F016 closed the sole diagnostic-loss path found when
  an initializer panic coincided with cleanup failure.
- **Security:** service ownership is exclusive, scope admission does not leak across siblings or up
  from descendants, inactive providers are not visible, and effect registration closes before
  invalidated-generation unwind. No Rust-local security finding.
- **Reliability/operations:** transitions for one fiber are serialized; no runtime-global lock is
  held across an awaited plugin callback or disposer; event listener snapshots are fixed before
  callbacks run; double disposal is safe. RT-008 now runs end-to-end through the coordinator,
  including active and in-flight-loading dependents. Registry/scope tombstones remain a long-lived
  retention risk (RT-F018).
- **Observability:** callers receive a pending `FiberHandle` from `mount` and can subscribe before
  reconciliation, so the Python RT-F013 hook-timing issue has no Rust equivalent. Complete trace
  retention is useful but unbounded and belongs to RT-F018's retention review.
- **Performance/complexity:** event admission and scope ancestry are linear in admitted/ancestor
  counts as expected. `ScopedRegistry` scans permanent tombstones and `ScopeTree` retains disposed
  nodes, so churn can grow memory and query cost without bound (RT-F018).
- **Public API:** exports are typed and do not expose `anyhow`; `Runtime` and coordinated `Context`
  operations compose the audited primitives without speculative Phase-3 API.
- **Documentation:** public runtime types and methods are largely undocumented; `cargo doc` can be
  warning-clean without proving API accuracy or completeness (RT-F019).

### Rust decisions on Python risk hints

- **RT-F012:** the new Rust coordinator exposed a narrower Rust analogue during remediation
  (RT-F020): aborting a provider-revocation traversal on the first cleanup failure could leave a
  later affected dependent `Active` after its provider disappeared. That violated existing RT-008
  and was fixed by invalidating and settling every affected dependent while retaining the first
  error. The general pass-wide question remains unchanged: aggregation, continuation across
  unrelated fibers, ordering, and serialized error shape are unspecified and were not made
  canonical. No shared-contract concern was introduced.
- **RT-F013:** no corresponding Rust issue. `DynPluginSpec::mount` returns the `Pending` fiber before
  reconciliation, allowing trace subscription first. No shared-contract change is indicated.

### Shared-contract reviewer verdict

| Extension | Verdict | Reason |
|---|---|---|
| `provides: {name, visible}` | **APPROVED** | Language-neutral fixture notation for RT-007. `visible` selects a scripted provider predicate through the real service seam; it does not decide service resolution in the runner and maps directly to a typed Rust closure. |
| `attempt_effect` | **APPROVED** | Language-neutral operation needed to observe RT-015 after mount. A thin runner retains the real plugin context and calls its actual effect API; all owner-state admission remains in the runtime. |
| `echo_args` | **APPROVED** | Language-neutral scripted-listener behavior needed for RT-019. The mock listener returns the arguments it actually receives (excluding the explicit waterfall continuation); the real event dispatcher remains solely responsible for replacement propagation, order, and continuation semantics. |

All three preserve the mock-backend-versus-runner boundary and can be translated into typed Rust
fixtures without embedding Fiber, service, scope, or event decisions in the adapter. This approval
does not approve the Python runner's unrelated descendant-scope traversal (RT-F015).

## 15. Findings

| ID | Severity | Classification | Description | Disposition / action |
|---|---|---|---|---|
| RT-F001 | MEDIUM | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | 6/23 RT requirements had zero direct canonical evidence (RT-001, RT-004, RT-007, RT-010, RT-015, RT-019); RT-016's per-mode matrix was separately partial | All 23 requirements now dispositioned: 21 canonical scenarios, RT-010 by Python unit test, RT-004/RT-023 disposed as out of current scope (see §4) |
| RT-F002 | LOW | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | Full scenario-body review narrowed RT-021/RT-022 from ambiguous gaps to precise missing sub-cases | Both sub-cases closed: `empty-waterfall-chain-yields-terminal`, `unscoped-dispatch-admits-only-untagged` |
| RT-F003 | LOW | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | Frozen §8 names separate scoped-registration visibility/ownership scenarios while current conformance consolidates them | Kept consolidated; frozen §8 wording treated as descriptive, not a scenario-count requirement (see §4 Coverage notes) |
| RT-F004 | MEDIUM | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | RT-023 lacked an explicit evidence/disposition decision | Disposed via `spec/runtime.md` RT-023: Python-specific mechanism, outside the language-neutral runtime contract, no canonical conformance evidence required |
| RT-F005 | HIGH | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | No `spec/runtime.md` existed for the first certification layer; frozen §3 was the only normative prose | Created `spec/runtime.md`, promoting RT-001..RT-023 into stable normative headings |
| RT-F006 | MEDIUM | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | RT-015 (effect creation on a disposed/inactive fiber) and RT-019 (waterfall replacement-argument propagation) were not expressible with the `runtime-scenario.schema.json` vocabulary as it stood: no step type let a plugin attempt `ctx.effect()` from outside its own `apply()` body at a later point, and no listener action let a listener assert on the arguments it actually received | Extended the DSL: `provides: {name, visible}` (also closes RT-007), a new `attempt_effect` step, and a new `echo_args` listener action. Scenarios written and passing. Rust's independent shared-contract review approved all three extensions. |
| RT-F007 | LOW | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | The conformance runner built every listener callback as `async def`, but `EventBus.emit()` invokes listeners with a plain synchronous call and never awaits — so any listener registered under `emit` silently never ran its body (an unawaited coroutine, discarded). Only surfaced once a real `emit` scenario was written; RT-016 had no functioning `emit` coverage before this | Fixed in `runner.py`: non-delegating listener actions (`raise`, `echo_args`, `short_circuit`, `observe`) are now plain synchronous functions; only `delegate`/`transform`/`delegate_twice` (waterfall-only, need to await `next`) stay `async def`. Runtime implementation itself (`EventBus.emit()`) was already correct — this was a conformance-runner defect, not a `PI_PARITY_DEFECT` or implementation bug |
| RT-F008 | LOW | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED BY EVIDENCE DISPOSITION | RT-015 covers both fiber-owned and scope-owned effects. The canonical `effect-after-fiber-disposed-raises` scenario covers the fiber case; the distinct scope-owner branch is directly covered by `test_scope.py::test_effect_on_a_disposed_scope_raises`. | Accepted as mixed canonical plus implementation-specific evidence under the same policy used for RT-010. Expanding the shared DSL solely to address a retained disposed-scope fixture would add test plumbing without a requirement gap; no semantic or schema change is required. |
| RT-F009 | LOW | `PARITY_NEUTRAL_HARDENING` — RESOLVED | `registry.py`'s reconciliation cycle-guard (`_MAX_PASSES` exceeded) raised a bare builtin `RuntimeError`, not the project's own `RuntimeError_` hierarchy (`errors.py`) that every other runtime error derives from. Code that catches `RuntimeError_` — including the conformance runner's own `except RuntimeError_` clause — would NOT have caught a genuine plugin-dependency cycle; it would have propagated uncaught. Marked `# pragma: no cover` in source, so unreached by any test; a genuine implementation inconsistency, not a Pi-parity issue (no Pi equivalent for this kernel) | Fixed: `registry.py` now raises `RuntimeError_` directly (no existing subclass fits the "reconciliation didn't stabilize" case semantically). Full suite re-run clean after the change |
| RT-F010 | LOW | `PARITY_NEUTRAL_HARDENING` — RESOLVED | `context.py`'s `ctx.effect()`/`ctx.provide()` "called outside a fiber" guards raised the bare builtin `RuntimeError`, the same defect class as `RT-F009` in a different file — reachable directly by calling either on a root/unscoped context | Fixed: both now raise `RuntimeError_`. `test_edges.py`'s two tests pinning the old builtin type updated to match. Full suite clean |
| RT-F011 | MEDIUM | `PARITY_NEUTRAL_HARDENING` — RESOLVED | `Fiber.load()`/`unload()`/`dispose()` transitioned to their terminal/settled state only on the line *after* calling `_unwind()` (via `dispose_all()`); if a disposer raised, the `ExceptionGroup` propagated before the state transition ran, leaving the fiber permanently stuck at `LOADING` (a failing load whose own failure-unwind also fails), `UNLOADING`, or mid-`dispose()` — reproduced directly with a throwaway script before fixing | Fixed: all three methods (and `_unwind()` itself) now use `try`/`finally` so the state always settles; the `ExceptionGroup` still propagates to the caller afterward, surfaced rather than swallowed — same principle `disposable.py` already applies to individual disposers, extended to the fiber's own state. Three new regression tests added to `test_fiber.py` (`test_unload_still_reaches_pending_when_a_disposer_raises`, `test_dispose_still_reaches_disposed_when_a_disposer_raises`, `test_load_failure_still_reaches_failed_when_the_unwind_also_raises`). Full suite clean |
| RT-F012 | LOW-MEDIUM | `PARITY_NEUTRAL_HARDENING` | `PluginRegistry.reconcile()`'s two-pass loop aborts entirely if any one fiber's `load()`/`unload()` raises — even after `RT-F011`'s fix, sibling fibers still awaiting action in the same pass are left unprocessed until a later mount/unmount triggers another `reconcile()` call. Only manifests when a disposer itself fails during a multi-fiber reconciliation pass | Not fixed — the correct shape mirrors `disposable.py`'s own aggregate-and-continue pattern one level up (per-fiber try/except, collect failures, keep processing the pass, raise an aggregated `ExceptionGroup` at the end), which is a larger, riskier change than this pass's other fixes. Recorded for a future pass |
| RT-F013 | MEDIUM | `PARITY_NEUTRAL_HARDENING` | `ctx.plugin()` — the mount API actually used throughout `tests/conformance/agent_runner.py` and most of `tests/runtime/`'s own suite — mounts and calls `reconcile()` before returning the fiber, so a caller has no opportunity to attach `on_state_change`/`on_effect` before the fiber's first transitions (`LOADING`, possibly straight to `ACTIVE` or `FAILED`) have already fired unobserved. The lower-level two-step (`ctx.plugins.mount()`, attach hooks, `await ctx.plugins.reconcile()`) — what the conformance runner itself uses — is the only way to observe from `PENDING` onward | Not fixed — closing this is an API design decision (hook parameters on `ctx.plugin()`, or documenting the two-step contract as the observability-sensitive path), not a small isolated change. Recorded for whoever next touches the `Context` mount API |
| RT-F014 | LOW | `PARITY_NEUTRAL_HARDENING` — RESOLVED | `PluginRegistry` — the return type of the widely-used `ctx.plugins` property — was not exported from `minion_agent.runtime`, unlike its siblings `ServiceRegistry`/`EventBus` which are exported despite being reachable the same way via `ctx.registry`/`ctx.events`. `test_public_surface.py`'s mechanical check only pins whatever `__all__` already contains, so it couldn't have caught an omission from day one | Fixed: `PluginRegistry` added to `__init__.py`'s imports and `__all__`, and to `test_public_surface.py`'s `EXPECTED` set. Full suite clean |
| RT-F015 | HIGH | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | The Python canonical runner's `ScopeTable.dispose()` computed and disposed descendant scopes itself, while the real Python `Scope.dispose()` only disposed that one scope and did not own descendant traversal. Consequently `nested-scope-disposal` could pass because the runner supplied RT-012 rather than proving the real runtime. | Fixed: added `ScopeTree` (`scope.py`), a real shared-per-`Context` primitive tracking every minted scope by key; `Scope.dispose()` now disposes its own live children (via the tree) deepest-first before its own registrations, and fires a new `on_disposed` hook. `ScopeTable.dispose()` in the runner is now lookup + invocation only (`await self.live[name].dispose()`), no traversal. New canonical scenario `disposing-a-scope-cascades-to-a-still-live-descendant` proves single-step ancestor-disposal cascade through the real runtime (the pre-existing `nested-scope-disposal` never exercised this — it disposes bottom-up explicitly). Three new `test_scope.py` unit tests. Full suite + `ruff` clean. No schema/DSL change. |
| RT-F016 | MEDIUM | `PARITY_NEUTRAL_HARDENING` — RESOLVED | Rust correctly settled all represented initializer/disposer failures, but both initializer-panic branches discarded an error returned by reverse cleanup before resuming the original panic. Cleanup was attempted and state reached `Disposed`, yet the cleanup failure was silently lost. | Fixed Rust-idiomatically: a common panic cleanup path settles state, resumes the original panic when cleanup succeeds, and reports both panic and cleanup failure when cleanup fails. Three focused lifecycle tests prove represented init+cleanup, dependency-loss cleanup, and panic+cleanup cases. |
| RT-F017 | HIGH | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | Rust had correct standalone Fiber/service/event/scope primitives but no coordinated runtime owning dependency notifications/reconciliation, and no Runtime canonical runner. | Fixed with `runtime/coordinator.rs`: `RuntimeCore` composes the existing registries/scopes/events/Fibers, returns a pending handle before reconciliation, exposes `Runtime::context()`, and reacts to provider appearance/revocation through real service-registration disposal. `tests/support/runtime_scenario.rs` is a thin adapter and `tests/runtime_conformance.rs` executes all 26 shared scenarios against the typed library. Ten focused coordinator tests cover RT-008, multiple dependents, valid failure settlement, loading invalidation, failure isolation, and the public Context view. No shared artifact changed. |
| RT-F018 | MEDIUM | `PARITY_NEUTRAL_HARDENING` | Rust `ScopedRegistry` permanently retains removal tombstones, `ScopeTree` retains disposed nodes/effect stores, and Fiber trace history is unbounded. Long-lived registration/scope/transition churn can therefore grow resident memory and registry scan cost without bound. | Open. Define bounded reclamation/compaction that preserves ownership, stable handles, and observability; add churn tests before claiming operational readiness. |
| RT-F019 | MEDIUM | `PARITY_NEUTRAL_HARDENING` | Rust's exported Runtime API is largely missing rustdoc. A warning-clean `cargo doc` build does not verify that public lifecycle/error/concurrency contracts are documented. | Open. Document every public Phase-1 runtime surface actually supported, especially error and lifecycle behavior; verify documentation against the shared spec and real implementation. |
| RT-F020 | HIGH | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | The initial Rust targeted coordinator stopped on the first affected-dependent error and could also discard later deferred service names. A failing dependent could therefore prevent later dependents from following provider appearance or disappearance. This was a Rust-local RT-008 violation, not a need for pass-wide aggregation semantics. | Targeted appearance/revocation and deferred-name traversals now attempt every affected item while retaining the first failure. `provider_appearance_reconciles_every_affected_dependent_before_returning_first_error` and `revocation_settles_all_affected_dependents_when_one_cleanup_fails` prove valid affected states and preserved diagnostics. Unrelated-pass aggregation/order remains unspecified and non-canonical. |
| RT-F021 | HIGH | `PARITY_NEUTRAL_HARDENING` — RESOLVED | Rust invoked synchronous `RuntimeObserver` callbacks while holding the Fiber lifecycle mutex. A re-entrant observer inspecting the same `FiberHandle` could deadlock the transition. | State and trace mutate atomically under the lifecycle lock; observer notification now occurs immediately after releasing it. `state_observer_may_reenter_the_fiber_without_deadlocking` proves the real coordinator path. No observable ordering rule changed. |

No `PARITY_CONSTRAINED_RISK`, `PI_PARITY_DEFECT`, or `PI_BEHAVIOR_UNCERTAIN` findings are recorded;
Runtime remains Minion-owned under `MINION-001`.

---

## 16. Certification gate

```text
Design alignment                         [x]  requirements traced to frozen §3
Pi parity                                [~]  not directly applicable; MINION-001 intentional divergence
Normative spec                           [x]  RT-F005 resolved — spec/runtime.md
Parity manifest                          [x]  MINION-001
Canonical conformance                    [x]  Python RT-F015 and Rust RT-F017 resolved; both real runtime paths pass all 26 scenarios
Python tests where implemented           [x]  15 files/133 tests audited (§6), all KEEP, all passing
Rust tests where implemented             [x]  full workspace green; RT-F011/016 probes and RT-F017 focused tests passing
Property/invariant tests                 [x]  test_properties.py (Hypothesis) covers disposal/mount-churn/scope-depth/admission-depth
Concurrency tests where applicable       [x]  test_events_async.py proves genuine concurrent parallel-listener interleaving
Fault-injection tests where applicable   [x]  both languages cover disposer failures; Rust also covers panic+cleanup failure
Security review                          [x]  §9 — exclusivity unbypassable, disposed-fiber misuse fully rejected, scope isolation bounded by design; no finding
Reliability review                       [x]  RT-F011/016/017/020/021 fixed; RT-F012 and RT-F018 remain recorded non-blocking risks
Observability review                     [x]  Python RT-F013 recorded; no Rust equivalent; unbounded trace noted RT-F018
Performance review                       [x]  Python clean; Rust retention/scan growth recorded RT-F018
Public API review                        [x]  Python RT-F014 fixed; Rust coordinated Runtime/Context surface exercised
Documentation                            [~]  reviewed and rustdoc warning-clean; completeness deferred to release gate as RT-F019
All findings classified                  [x]
No unresolved Pi uncertainty             [x]
No unresolved parity defect              [x]
No unresolved contract-assurance defect  [x]  RT-F008 disposition accepted; RT-F015 and RT-F017 resolved
Shared-contract reviewer approval        [x]  provides:{name,visible}, attempt_effect, echo_args approved
Deferred risks recorded                  [x]  RT-F012/013/018/019 remain explicitly recorded
```

## 17. Certification result

**Result:** `CERTIFIED`

The independent Rust module, existing-test, RT-010, RT-F011-class, RT-F012/RT-F013, shared-DSL, and
§8-14 reviews are complete. The three DSL/schema extensions are approved. Rust's real
`ScopedRegistry` has direct RT-010 evidence. Represented teardown failures already settled the
fiber correctly; the one Rust-local panic-plus-cleanup diagnostic defect was fixed and regression
tested as RT-F016.

**RT-F015 is now resolved** (this pass): `ScopeTree`, a real primitive in `minion_agent.runtime`,
gives `Scope.dispose()` itself — not the conformance runner — ownership of descendant-scope
disposal. `ScopeTable.dispose()` in `tests/conformance/runner.py` is now lookup + invocation only.
`disposing-a-scope-cascades-to-a-still-live-descendant`, a new canonical scenario, proves a
single-step ancestor disposal correctly cascades to a still-live descendant through the real
runtime — the pre-existing `nested-scope-disposal` scenario never actually exercised that path,
since it disposes bottom-up explicitly. Full Python suite and `ruff` clean; no schema/DSL change was
needed or made; no shared-contract extension was reopened.

**RT-F017 is now resolved:** Rust's `RuntimeCore` coordinates the existing typed service, Fiber,
event, and scope primitives; provider appearance and real registration revocation drive dependent
reconciliation through the public `Runtime`/`Context` path. The conformance harness parses and
normalizes only; all lifecycle, visibility, scope, dispatch, and waterfall decisions remain in the
library. All 26 canonical Runtime scenarios pass in Rust, including RT-008 and the Python-landed
single-step descendant-scope cascade.

The RT-F012 checkpoint exposed and resolved RT-F020: one affected-dependent failure can no longer
strand later affected dependents or discard later deferred service names. Rust attempts the whole
targeted set and then returns the first failure. This is RT-008 state preservation, not a canonical
commitment to pass-wide aggregation, unrelated-fiber continuation, ordering, or error shape.
Review also resolved RT-F021 by moving synchronous observation immediately outside the Fiber
lifecycle lock; re-entrant state inspection is covered directly.

The Rust quality gates are green: `cargo fmt --all -- --check`; Clippy across the workspace, all
targets, and all features with warnings denied; full workspace tests; canonical Runtime
conformance; and rustdoc with warnings denied. The RT-F011/RT-F016 lifecycle matrix was rerun after
coordination and remains green: initialization, cleanup, combined represented failures,
panic-plus-cleanup, and dependency-loss cleanup all settle without leaving transient states.

With the independently recorded Python RT-F015 evidence and this Rust RT-F017 evidence, the
Runtime Layer is certified against the stable shared contract. No shared specification, schema,
scenario, or parity-manifest change was required by the Rust remediation.

RT-F018 (bounded retention) and RT-F019 (Rust API documentation) remain open hardening work and
must be dispositioned by the foundation release gate. RT-F012 and RT-F013 remain the previously
recorded non-blocking items. Rust coordination exposed no shared RT-F012 semantic gap:
pass-wide aggregation/continuation remains unspecified and was not made canonical.
