# Runtime Kernel — Fidelity Assurance & Certification

**Layer ID:** `01`  
**Status:** `IN_AUDIT`  
**Audit date:** 2026-08-22 (Steps 0-2 complete; canonical conformance now covers all 23 RT-*
requirements — 22 canonical, RT-010 by Python unit-test evidence; Steps 3-6 not started — see §17)  
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

Python inventory is identified but not yet deep-audited:

| File/module | Responsibility | Decision | Evidence |
|---|---|---|---|
| `context.py` | Context/service access/extend | pending deep audit | RT-004, RT-007, RT-008 |
| `disposable.py` | disposer collection and unwind | pending | RT-013..RT-015 |
| `errors.py` | runtime errors | pending | — |
| `events.py` | dispatch modes/waterfall/scope admission | pending | RT-016..RT-022 |
| `fiber.py` | Fiber lifecycle | pending | RT-001..RT-003 |
| `plugin.py` | plugin mount/reconciliation | pending | RT-001, RT-023 |
| `registry.py` | service registry | pending | RT-004..RT-006 |
| `scope.py` | scope mechanics | pending | RT-009, RT-012 |
| `scoped_registry.py` | scoped registration table | pending | RT-009, RT-010 |
| `service.py` | service resolution | pending | RT-004..RT-008 |

Rust equivalents are present and must receive an independent inventory/audit after the Python-driven
pass. Neither implementation is an oracle for the other.

---

## 6. Existing-test audit

Not started. Python `tests/runtime/` and related composition tests, and Rust `runtime_*.rs` tests,
must each be mapped to RT-* requirements and classified:

```text
KEEP
STRENGTHEN
MOVE TO CONFORMANCE
REWRITE
DELETE
```

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

Not yet assessed; these depend on the existing-test and module-level audits.

---

## 8-14. Failure model / security / reliability / observability / performance / API / documentation

**Not started.** These remain substantial certification work.

Starting audit targets already identified:

- Security: exclusive registration authority, disposed-owner misuse, scope isolation.
- Reliability: loading/unwind races, dependency disappearance, disposer failures.
- Observability: lifecycle/dependency transitions and cleanup failures.
- Performance: service lookup, event dispatch, reactive reconciliation, scoped lookup.
- API/docs: public runtime surface and documentation accuracy.

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
Python tests where implemented           [ ]  not audited
Rust tests where implemented             [ ]  not audited
Property/invariant tests                 [ ]  not audited
Concurrency tests where applicable       [ ]  not audited
Fault-injection tests where applicable   [ ]  not audited
Security review                          [ ]  not started
Reliability review                       [ ]  not started
Observability review                     [ ]  not started
Performance review                       [ ]  not started
Public API review                        [ ]  not started
Documentation                            [ ]  not started
All findings classified                  [x]
No unresolved Pi uncertainty             [x]
No unresolved parity defect              [x]
No unresolved contract-assurance defect  [~]  RT-F001-007 resolved; DSL/schema changes await Rust's shared-contract review
Deferred risks recorded                  [x]  none currently require risk-register entry
```

## 17. Certification result

**Result:** `NOT YET ELIGIBLE`

`spec/runtime.md` exists and every RT-001..RT-023 requirement now has an explicit disposition:
canonical `conformance/runtime/*.yaml` evidence, direct unit-test evidence (RT-010), or an explicit
scope-exclusion (RT-004, RT-023). RT-F001-RT-F007 are all resolved. What remains before
certification is no longer contract/evidence work — it is implementation/test deep audit,
security/reliability/observability/performance/API/docs review, and the independent Rust check.

**Follow-up dependencies:**

1. Send the three schema/runner changes from this pass (`provides: {name, visible}`, `attempt_effect`
   step, `echo_args` action) to Rust for shared-contract review before they're treated as canonical
   per `process/implementation-conformance-workflow.md`'s reviewer rule.
2. Perform Python module/test deep audit (§5, §6) and remediation.
3. Perform the independent Rust audit against the same RT-* contract, including a `ScopedRegistry`-
   equivalent unit test for RT-010.
4. Complete security/reliability/observability/performance/public-API/documentation review (§8-14).
5. Complete the full assurance gate before certification.
