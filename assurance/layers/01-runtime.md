# Runtime Kernel — Fidelity Assurance & Certification

**Layer ID:** `01`  
**Status:** `IN_AUDIT`  
**Audit date:** 2026-08-23 (Python side of the audit essentially complete: canonical conformance
covers all 23 RT-* requirements, §5/§6 deep audit and §8-14 review both done, 3 real implementation
defects found and fixed; independent Rust cross-check still outstanding — see §17)  
**Auditor:** Claude (Python-driven, per adopted workflow)  
**Python status:** `IMPLEMENTED`  
**Rust status:** `IMPLEMENTED` — both implementations have reached this layer, so final
certification requires both.

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
| RT-012 | Disposing a scope removes its own + descendants' registrations, not ancestors/siblings, in reverse creation order | Frozen §3 Scoped registration | `nested-scope-disposal` | COVERED |
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

All 23 RT-* requirements now have a disposition: 21 COVERED by canonical `conformance/runtime/`
scenarios, 1 (RT-010) COVERED by direct Python unit-test evidence pending a plugin-facing DSL
surface, 2 (RT-004, RT-023) DISPOSED as out of current scope by construction/deferral. Zero
requirements remain GAP.

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
but it is Python-only: Rust needs an equivalent direct unit test of its own `ScopedRegistry`
equivalent as part of the independent cross-check (§17), and true canonical cross-language
conformance should be added once a real registry wires this primitive to the plugin surface.

Two runner changes landed alongside this batch of scenarios, beyond new `.yaml` files: (1) the
`provides` plugin field now optionally takes `{name, visible}` instead of a bare string, so a
scenario can register a service whose `check` predicate always fails — closing RT-007's `check`
half. (2) A new `attempt_effect` step lets a scenario call `ctx.effect()` against an already-mounted
plugin's context from outside its own `apply()` body, which is the only way to reach a fiber in a
state its own load-time code can't observe — closing RT-015. (3) A new `echo_args` listener action
returns the positional arguments a listener actually received (minus the trailing `next`), so a
downstream listener can prove what it was called with — closing RT-019. All three are
`conformance/**`/schema changes and fall under the shared-contract reviewer rule: they need Rust's
review before they're canonical, and are flagged for that in §17.

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
| `scope.py` | `ScopeKey`/`Scope` mechanics | audited, matches RT-* as traced | RT-009, RT-012 |
| `scoped_registry.py` | `ScopedRegistry`: inherit-down visibility query | audited, matches RT-010 exactly (own scope, then ancestors nearest-first, then untagged) — still has no plugin-facing wiring, per RT-010's disposition in §4 | RT-010 |
| `service.py` | `ServiceRegistry`/`Impl`: exclusive registration, ACTIVE+check visibility | audited, matches RT-* as traced | RT-004..RT-007 |

The original inventory paired RT-004/RT-005/RT-006 evidence with `registry.py`; that was wrong —
`registry.py` is the *plugin* registry (mount/reconcile, RT-001/RT-008), and `service.py` is the
*service* registry (RT-004..RT-007). Corrected above.

Rust equivalents are present and must receive an independent inventory/audit after the Python-driven
pass. Neither implementation is an oracle for the other.

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
| `test_scope.py` | KEEP | RT-009, RT-012, RT-015 | Scope nesting/ownership/disposal; `test_effect_on_a_disposed_scope_raises` is RT-015's *scope*-owner evidence, complementing the canonical scenario's fiber-owner case (see `RT-F008`) |
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

Rust's `runtime_*.rs` equivalent audit is still open — part of the independent Rust cross-check
in §17.

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

## 15. Findings

| ID | Severity | Classification | Description | Disposition / action |
|---|---|---|---|---|
| RT-F001 | MEDIUM | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | 6/23 RT requirements had zero direct canonical evidence (RT-001, RT-004, RT-007, RT-010, RT-015, RT-019); RT-016's per-mode matrix was separately partial | All 23 requirements now dispositioned: 21 canonical scenarios, RT-010 by Python unit test, RT-004/RT-023 disposed as out of current scope (see §4) |
| RT-F002 | LOW | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | Full scenario-body review narrowed RT-021/RT-022 from ambiguous gaps to precise missing sub-cases | Both sub-cases closed: `empty-waterfall-chain-yields-terminal`, `unscoped-dispatch-admits-only-untagged` |
| RT-F003 | LOW | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | Frozen §8 names separate scoped-registration visibility/ownership scenarios while current conformance consolidates them | Kept consolidated; frozen §8 wording treated as descriptive, not a scenario-count requirement (see §4 Coverage notes) |
| RT-F004 | MEDIUM | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | RT-023 lacked an explicit evidence/disposition decision | Disposed via `spec/runtime.md` RT-023: Python-specific mechanism, outside the language-neutral runtime contract, no canonical conformance evidence required |
| RT-F005 | HIGH | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | No `spec/runtime.md` existed for the first certification layer; frozen §3 was the only normative prose | Created `spec/runtime.md`, promoting RT-001..RT-023 into stable normative headings |
| RT-F006 | MEDIUM | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | RT-015 (effect creation on a disposed/inactive fiber) and RT-019 (waterfall replacement-argument propagation) were not expressible with the `runtime-scenario.schema.json` vocabulary as it stood: no step type let a plugin attempt `ctx.effect()` from outside its own `apply()` body at a later point, and no listener action let a listener assert on the arguments it actually received | Extended the DSL: `provides: {name, visible}` (also closes RT-007), a new `attempt_effect` step, and a new `echo_args` listener action. Scenarios written and passing. These are `conformance/**`/schema changes — need Rust's shared-contract review before they're canonical (§17) |
| RT-F007 | LOW | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | The conformance runner built every listener callback as `async def`, but `EventBus.emit()` invokes listeners with a plain synchronous call and never awaits — so any listener registered under `emit` silently never ran its body (an unawaited coroutine, discarded). Only surfaced once a real `emit` scenario was written; RT-016 had no functioning `emit` coverage before this | Fixed in `runner.py`: non-delegating listener actions (`raise`, `echo_args`, `short_circuit`, `observe`) are now plain synchronous functions; only `delegate`/`transform`/`delegate_twice` (waterfall-only, need to await `next`) stay `async def`. Runtime implementation itself (`EventBus.emit()`) was already correct — this was a conformance-runner defect, not a `PI_PARITY_DEFECT` or implementation bug |
| RT-F008 | LOW | `CONTRACT_ASSURANCE_DEFECT` | RT-015 ("creating an effect on an already-disposed owner raises") covers both fiber-owned and scope-owned effects — `context.py`'s `_scoped_effect()` has its own `InactiveFiberError` guard for a disposed scope, distinct from `Fiber.effect()`'s. The canonical scenario (`effect-after-fiber-disposed-raises`) only covers the fiber case; the scope case has unit-test evidence only (`test_scope.py::test_effect_on_a_disposed_scope_raises`). The current `attempt_effect` DSL step operates on a mounted plugin's fiber `ctx`; there is no equivalent hook for a scope's `ctx`, and `ScopeTable.dispose()` pops a disposed scope out of `live`, so no reference survives to attempt an effect against it through the current DSL even if a step existed | Not urgent — RT-015's substance is covered (canonical fiber case + unit-tested scope case). A future DSL extension (e.g. a runner-side side-table retaining disposed scopes' `ctx`, plus an `attempt_effect` variant addressing a scope by name) would close this fully; low priority, noted for whoever next touches the runtime scenario DSL |
| RT-F009 | LOW | `PARITY_NEUTRAL_HARDENING` — RESOLVED | `registry.py`'s reconciliation cycle-guard (`_MAX_PASSES` exceeded) raised a bare builtin `RuntimeError`, not the project's own `RuntimeError_` hierarchy (`errors.py`) that every other runtime error derives from. Code that catches `RuntimeError_` — including the conformance runner's own `except RuntimeError_` clause — would NOT have caught a genuine plugin-dependency cycle; it would have propagated uncaught. Marked `# pragma: no cover` in source, so unreached by any test; a genuine implementation inconsistency, not a Pi-parity issue (no Pi equivalent for this kernel) | Fixed: `registry.py` now raises `RuntimeError_` directly (no existing subclass fits the "reconciliation didn't stabilize" case semantically). Full suite re-run clean after the change |
| RT-F010 | LOW | `PARITY_NEUTRAL_HARDENING` — RESOLVED | `context.py`'s `ctx.effect()`/`ctx.provide()` "called outside a fiber" guards raised the bare builtin `RuntimeError`, the same defect class as `RT-F009` in a different file — reachable directly by calling either on a root/unscoped context | Fixed: both now raise `RuntimeError_`. `test_edges.py`'s two tests pinning the old builtin type updated to match. Full suite clean |
| RT-F011 | MEDIUM | `PARITY_NEUTRAL_HARDENING` — RESOLVED | `Fiber.load()`/`unload()`/`dispose()` transitioned to their terminal/settled state only on the line *after* calling `_unwind()` (via `dispose_all()`); if a disposer raised, the `ExceptionGroup` propagated before the state transition ran, leaving the fiber permanently stuck at `LOADING` (a failing load whose own failure-unwind also fails), `UNLOADING`, or mid-`dispose()` — reproduced directly with a throwaway script before fixing | Fixed: all three methods (and `_unwind()` itself) now use `try`/`finally` so the state always settles; the `ExceptionGroup` still propagates to the caller afterward, surfaced rather than swallowed — same principle `disposable.py` already applies to individual disposers, extended to the fiber's own state. Three new regression tests added to `test_fiber.py` (`test_unload_still_reaches_pending_when_a_disposer_raises`, `test_dispose_still_reaches_disposed_when_a_disposer_raises`, `test_load_failure_still_reaches_failed_when_the_unwind_also_raises`). Full suite clean |
| RT-F012 | LOW-MEDIUM | `PARITY_NEUTRAL_HARDENING` | `PluginRegistry.reconcile()`'s two-pass loop aborts entirely if any one fiber's `load()`/`unload()` raises — even after `RT-F011`'s fix, sibling fibers still awaiting action in the same pass are left unprocessed until a later mount/unmount triggers another `reconcile()` call. Only manifests when a disposer itself fails during a multi-fiber reconciliation pass | Not fixed — the correct shape mirrors `disposable.py`'s own aggregate-and-continue pattern one level up (per-fiber try/except, collect failures, keep processing the pass, raise an aggregated `ExceptionGroup` at the end), which is a larger, riskier change than this pass's other fixes. Recorded for a future pass |
| RT-F013 | MEDIUM | `PARITY_NEUTRAL_HARDENING` | `ctx.plugin()` — the mount API actually used throughout `tests/conformance/agent_runner.py` and most of `tests/runtime/`'s own suite — mounts and calls `reconcile()` before returning the fiber, so a caller has no opportunity to attach `on_state_change`/`on_effect` before the fiber's first transitions (`LOADING`, possibly straight to `ACTIVE` or `FAILED`) have already fired unobserved. The lower-level two-step (`ctx.plugins.mount()`, attach hooks, `await ctx.plugins.reconcile()`) — what the conformance runner itself uses — is the only way to observe from `PENDING` onward | Not fixed — closing this is an API design decision (hook parameters on `ctx.plugin()`, or documenting the two-step contract as the observability-sensitive path), not a small isolated change. Recorded for whoever next touches the `Context` mount API |
| RT-F014 | LOW | `PARITY_NEUTRAL_HARDENING` — RESOLVED | `PluginRegistry` — the return type of the widely-used `ctx.plugins` property — was not exported from `minion_agent.runtime`, unlike its siblings `ServiceRegistry`/`EventBus` which are exported despite being reachable the same way via `ctx.registry`/`ctx.events`. `test_public_surface.py`'s mechanical check only pins whatever `__all__` already contains, so it couldn't have caught an omission from day one | Fixed: `PluginRegistry` added to `__init__.py`'s imports and `__all__`, and to `test_public_surface.py`'s `EXPECTED` set. Full suite clean |

No `PARITY_CONSTRAINED_RISK`, `PI_PARITY_DEFECT`, or `PI_BEHAVIOR_UNCERTAIN` findings are currently
recorded.

---

## 16. Certification gate

```text
Design alignment                         [x]  requirements traced to frozen §3
Pi parity                                [~]  not directly applicable; MINION-001 intentional divergence
Normative spec                           [x]  RT-F005 resolved — spec/runtime.md
Parity manifest                          [x]  MINION-001
Canonical conformance                    [x]  RT-F001 resolved — all 23 RT-* requirements dispositioned
Python tests where implemented           [x]  15 files/133 tests audited (§6), all KEEP, all passing
Rust tests where implemented             [ ]  not audited
Property/invariant tests                 [x]  test_properties.py (Hypothesis) covers disposal/mount-churn/scope-depth/admission-depth
Concurrency tests where applicable       [x]  test_events_async.py proves genuine concurrent parallel-listener interleaving
Fault-injection tests where applicable   [x]  disposer-raises-mid-teardown covered (test_disposable.py, test_fiber.py)
Security review                          [x]  §9 — exclusivity unbypassable, disposed-fiber misuse fully rejected, scope isolation bounded by design; no finding
Reliability review                       [x]  §10 — RT-F011 (stuck-state bug) fixed; RT-F012 (reconcile abort-on-failure) recorded, not fixed
Observability review                     [x]  §11 — RT-F013 (ctx.plugin() hook-timing gap) recorded, not fixed
Performance review                       [x]  §12 — no accidentally-quadratic pattern found; no finding
Public API review                        [x]  §13-14 — RT-F014 (PluginRegistry export) fixed
Documentation                            [x]  §13-14 — spec/runtime.md checked against actual behavior, no drift found
All findings classified                  [x]
No unresolved Pi uncertainty             [x]
No unresolved parity defect              [x]
No unresolved contract-assurance defect  [~]  RT-F001-007, RT-F009-011, RT-F014 resolved; RT-F008/012/013 (LOW-MEDIUM, non-blocking) open; DSL/schema Rust review still open
Deferred risks recorded                  [x]  none currently require risk-register entry
```

## 17. Certification result

**Result:** `NOT YET ELIGIBLE`

`spec/runtime.md` exists and every RT-001..RT-023 requirement now has an explicit disposition:
canonical `conformance/runtime/*.yaml` evidence, direct unit-test evidence (RT-010), or an explicit
scope-exclusion (RT-004, RT-023). The Python module deep audit (§5), existing-test audit (§6), and
the failure-model/security/reliability/observability/performance/API/documentation review (§8-14) are
all complete. Two real implementation defects were found and fixed during this pass: `RT-F011`, a
genuine reliability bug where a disposer raising during `unload()`/`dispose()`/a failed `load()`'s
unwind left the fiber permanently stuck in a non-terminal state; and two more instances of `RT-F009`'s
wrong-exception-type pattern (`RT-F010`), plus a public-API export gap (`RT-F014`). RT-F001-RT-F007,
RT-F009, RT-F010, RT-F011, and RT-F014 are resolved. RT-F008 (scope-owned RT-015 canonical coverage),
RT-F012 (`reconcile()` aborts a whole pass on one fiber's failure), and RT-F013 (`ctx.plugin()`'s
observability hook-timing gap) remain open — all low-to-medium severity, all non-blocking, all
requiring either a DSL extension or an API design decision bigger than this pass's scope. Python's
side of this layer's certification work is now essentially complete. What remains: the independent
Rust cross-check, and optionally closing the three open low/medium findings in a future pass.

**Follow-up dependencies:**

1. Send the three schema/runner changes from an earlier pass (`provides: {name, visible}`,
   `attempt_effect` step, `echo_args` action) to Rust for shared-contract review before they're
   treated as canonical per `process/implementation-conformance-workflow.md`'s reviewer rule.
2. Perform the independent Rust audit against the same RT-* contract: module deep audit, existing-test
   classification, a `ScopedRegistry`-equivalent unit test for RT-010, and its own §8-14 review —
   including checking whether Rust's fiber-equivalent has `RT-F011`'s stuck-state bug (or already
   avoids it) and whether `RT-F012`/`RT-F013` apply there too.
3. Optionally close `RT-F008` (scope-owner RT-015 canonical coverage), `RT-F012` (`reconcile()`
   per-fiber failure isolation), and `RT-F013` (`ctx.plugin()` hook-timing) in a future pass — none is
   large enough to justify a dedicated one on its own.
4. Complete the full assurance gate before certification.
