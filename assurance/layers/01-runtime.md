# Runtime Kernel — Fidelity Assurance & Certification

**Layer ID:** `01`  
**Status:** `IN_AUDIT`  
**Audit date:** 2026-08-22 (Steps 0-2 complete; canonical-conformance gap-filling in progress; Steps
3-6 not started — see §17)  
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
| RT-001 | Fiber lifecycle `Pending -> Loading -> Active`, with disposal/dependency-loss/init-failure transitions matching the frozen state diagram | Frozen §3 Fiber | none | **GAP** |
| RT-002 | `Failed` is stable; dependency changes never auto-retry a failed plugin | Frozen §3 Fiber | `failed-remains-failed` | COVERED |
| RT-003 | Loading is transactional; invalidated load cannot commit ACTIVE or race owned effects against unwind | Frozen §3 Fiber | `dependency-loss-during-loading-never-activates` | COVERED/PARTIAL MECHANISM |
| RT-004 | Service identity is `(name, realm)` and compares name by string value | Frozen §3 Service resolution | none direct | **GAP** |
| RT-005 | Registration is exclusive; duplicate provider raises, with no last-wins/priority behavior | Frozen §3 Service resolution | `service-exclusivity` | COVERED |
| RT-006 | No fallback stack; disposing a provider does not resurrect an older provider | Frozen §3 Service resolution | `no-fallback-stack-after-provider-disposes` | COVERED |
| RT-007 | Service visibility is ACTIVE-gated; `check` may narrow visibility | Frozen §3 Service resolution | none | **GAP** |
| RT-008 | Dependents reconcile when a resolved provider appears/disappears | Frozen §3 reactive dependency | `reactive-dependency` | COVERED |
| RT-009 | Scoped registration context owns both visibility and teardown | Frozen §3 Scoped registration | `scoped-registration-visibility` | COVERED |
| RT-010 | Scoped registration visibility inherits down to descendants, never up | Frozen §3 Scoped registration | none direct | **GAP** |
| RT-011 | Scoped event admission extends up; ancestor listeners see descendant dispatch, never reverse; untagged participates everywhere | Frozen §3 Scoped registration | `scoped-event-admission` | COVERED |
| RT-012 | Disposing a scope removes its own + descendants' registrations, not ancestors/siblings, in reverse creation order | Frozen §3 Scoped registration | `nested-scope-disposal` | COVERED |
| RT-013 | `ctx.effect(fn)` runs immediately and disposers unwind in reverse order | Frozen §3 Effects | `effect-reversal` | COVERED |
| RT-014 | Double disposal is a no-op | Frozen §3 Effects | `double-unmount-disposes-effects-once` | COVERED |
| RT-015 | Creating an effect on an already-disposed owner raises | Frozen §3 Effects | none | **GAP** — not expressible via current scenario DSL, see `RT-F006` |
| RT-016 | `emit`/`parallel`/`serial`/`waterfall` obey the frozen awaited/order/return matrix; mode mismatch is a startup error | Frozen §3 Events | `dispatch-mode-mismatch-is-startup-error` | **VERIFIED PARTIAL** — mode-mismatch startup error covered; per-mode awaited/order/return matrix for `emit`/`parallel`/`serial` not yet directly scenario-verified |
| RT-017 | Waterfall short-circuit: listener not calling `next` terminates the chain with its own return | Frozen §3 Waterfall | `waterfall-short-circuit` | COVERED |
| RT-018 | Waterfall delegation: `next()` runs downstream and returns downstream result unless transformed | Frozen §3 Waterfall | `waterfall-baseline-delegation` | COVERED |
| RT-019 | Waterfall replacement args propagate through `next(*replacement)` | Frozen §3 Waterfall | none | **GAP** — not expressible via current scenario DSL, see `RT-F006` |
| RT-020 | Waterfall `next` may be called at most once | Frozen §3 Waterfall | `waterfall-next-called-twice` | COVERED |
| RT-021 | Waterfall declares explicit terminal continuation, including zero-listener empty chain | Frozen §3 Waterfall | `waterfall-terminal-continuation`, `computed-waterfall-terminal`, `empty-waterfall-chain-yields-terminal` | COVERED |
| RT-022 | Scope filtering is additive; no-scope dispatch admits only untagged listeners | Frozen §3 Waterfall | `scoped-event-admission`, `unscoped-dispatch-admits-only-untagged` | COVERED |
| RT-023 | Plugin config validates through Pydantic; JSON Schema export is available where required | Frozen §3 Config | none | **DISPOSED** — `spec/runtime.md` RT-023: Python-specific mechanism, outside the language-neutral runtime contract, no canonical conformance evidence required |

### Coverage notes

Existing scenarios that are valuable but not named one-for-one in the frozen §8 list remain valid
coverage. Requirement IDs and scenario filenames are not required to be 1:1.

The current consolidated `scoped-registration-visibility` scenario appears to cover both visibility
and ownership semantics even though frozen §8 names visibility and ownership separately.
**Resolved (`RT-F003`):** kept consolidated — one scenario already exercises both properties
without artificial duplication. Frozen §8's separate naming is descriptive prose, not a
scenario-count requirement; splitting it would not add coverage. The frozen master file is edited
only by its owner, so this disposition is recorded here rather than as an edit to §8 itself.

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

- [x] RT-006 no fallback stack — `no-fallback-stack-after-provider-disposes`
- [x] RT-014 double disposal — `double-unmount-disposes-effects-once`
- [x] RT-016 mode-mismatch startup error — `dispatch-mode-mismatch-is-startup-error`
- [x] RT-017 waterfall short-circuit — `waterfall-short-circuit`
- [x] RT-018 waterfall baseline delegation — `waterfall-baseline-delegation`
- [x] RT-021 zero-listener terminal — `empty-waterfall-chain-yields-terminal`
- [x] RT-022 dispatch with no scope key — `unscoped-dispatch-admits-only-untagged`
- [ ] RT-001 full Fiber lifecycle
- [ ] RT-004 string-value service identity
- [ ] RT-007 ACTIVE-gated visibility + `check`
- [ ] RT-010 inherit-down scoped visibility
- [ ] RT-015 effect after disposed owner — blocked, see `RT-F006`
- [ ] RT-016 per-mode `emit`/`parallel`/`serial` awaited/order/return matrix (mismatch sub-case now covered)
- [ ] RT-019 replacement-argument propagation — blocked, see `RT-F006`

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
| RT-F001 | MEDIUM | `CONTRACT_ASSURANCE_DEFECT` | 6/23 RT requirements have zero direct canonical evidence (RT-001, RT-004, RT-007, RT-010, RT-015, RT-019); RT-016's per-mode matrix is separately partial | Add remaining canonical scenarios; RT-015/RT-019 blocked on DSL work tracked as `RT-F006` |
| RT-F002 | LOW | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | Full scenario-body review narrowed RT-021/RT-022 from ambiguous gaps to precise missing sub-cases | Both sub-cases closed: `empty-waterfall-chain-yields-terminal`, `unscoped-dispatch-admits-only-untagged` |
| RT-F003 | LOW | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | Frozen §8 names separate scoped-registration visibility/ownership scenarios while current conformance consolidates them | Kept consolidated; frozen §8 wording treated as descriptive, not a scenario-count requirement (see §4 Coverage notes) |
| RT-F004 | MEDIUM | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | RT-023 lacked an explicit evidence/disposition decision | Disposed via `spec/runtime.md` RT-023: Python-specific mechanism, outside the language-neutral runtime contract, no canonical conformance evidence required |
| RT-F005 | HIGH | `CONTRACT_ASSURANCE_DEFECT` — RESOLVED | No `spec/runtime.md` existed for the first certification layer; frozen §3 was the only normative prose | Created `spec/runtime.md`, promoting RT-001..RT-023 into stable normative headings |
| RT-F006 | MEDIUM | `CONTRACT_ASSURANCE_DEFECT` | RT-015 (effect creation on a disposed/inactive fiber) and RT-019 (waterfall replacement-argument propagation) are not expressible with the current `runtime-scenario.schema.json` vocabulary: no step type lets a plugin attempt `ctx.effect()` from outside its own `apply()` body at a later point, and no listener action lets a listener assert on the arguments it actually received | Extend the scenario DSL (new step/listener-action kinds) before RT-015/RT-019 can get canonical evidence; until then these two requirements stay GAP, not silently dropped |

No `PARITY_CONSTRAINED_RISK`, `PI_PARITY_DEFECT`, or `PI_BEHAVIOR_UNCERTAIN` findings are currently
recorded.

---

## 16. Certification gate

```text
Design alignment                         [x]  requirements traced to frozen §3
Pi parity                                [~]  not directly applicable; MINION-001 intentional divergence
Normative spec                           [x]  RT-F005 resolved — spec/runtime.md
Parity manifest                          [x]  MINION-001
Canonical conformance                    [ ]  RT-F001 — 6 requirements still GAP (2 blocked on RT-F006)
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
No unresolved contract-assurance defect  [ ]  RT-F001/RT-F006 remain open
Deferred risks recorded                  [x]  none currently require risk-register entry
```

## 17. Certification result

**Result:** `NOT YET ELIGIBLE`

`spec/runtime.md` now exists and RT-F002/RT-F003/RT-F004/RT-F005 are resolved; 6 of the 7 requirements
that were `GAP` at audit start now have canonical evidence. Implementation/test deep audit,
security/reliability/observability/performance/API/docs review, and independent Rust cross-check are
still outstanding, and RT-001/RT-004/RT-007/RT-010/RT-015/RT-019/RT-016(matrix) remain open.

**Follow-up dependencies:**

1. Add canonical scenarios for RT-001, RT-004, RT-007, RT-010, and the RT-016 per-mode matrix.
2. Extend the scenario DSL to make RT-015 and RT-019 expressible (`RT-F006`), then add their scenarios.
3. Perform Python module/test deep audit and remediation.
4. Perform the independent Rust audit against the same RT-* contract.
5. Complete the full assurance gate before certification.
