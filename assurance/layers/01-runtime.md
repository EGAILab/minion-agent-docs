# Runtime Kernel — Fidelity Assurance & Certification

**Layer ID:** `01`
**Status:** `IN_AUDIT`
**Audit date:** 2026-08-22 (Step 0-2 complete; Steps 3-6 not started — see §17)
**Auditor:** Claude (Python-driven, per adopted workflow)
**Python status:** `IMPLEMENTED`
**Rust status:** `IMPLEMENTED` — per the workflow's runtime-specific rule, both implementations
have already reached this layer, so final certification requires both, not Python alone (see §1).

---

## 1. Scope

### Owns

Context, Fiber lifecycle, service resolution/registry, scoped registration, reactive dependency,
effects/disposal, the four event dispatch modes (`emit`/`parallel`/`serial`/`waterfall`), and
plugin config validation.

### Does not own

Application-level session/agent/tool/LLM semantics — those consume the runtime, they don't define
it. Realms/isolation and the declarative plugin loader are explicitly deferred (frozen master §9),
out of scope for this layer's certification.

### Depends on

Nothing inside Minion — this is the foundation layer. Depends on Pydantic (Python) for config
validation per §3's "Config" subsection.

### Depended on by

Every later layer (LLM, session, tools, agent loop) mounts as a plugin against this kernel.

### Runtime-specific certification note

Runtime is **the primary intentional architectural divergence** from Pi (frozen master §3 opening:
"Cordis-semantic, not a Cordis port"). It is not Pi-derived behavior being reproduced — it's
Minion's own design, whose primary authority is the frozen master text itself plus canonical
`conformance/runtime/`, not pinned Pi source. This changes how §4's finding classification applies
here specifically: most findings in this layer will not be `PI_PARITY_DEFECT` (there is no Pi
runtime to diverge from) but rather **design/conformance completeness defects** — cases where the
frozen master states a rule and no executable evidence proves it — or `PARITY_NEUTRAL_HARDENING`.
Treated as its own explicit classification below rather than force-fit into the Pi-specific four.

Both Python and Rust have already reached this layer (confirmed: `minion-agent-python/src/
minion_agent/runtime/` and `minion-agent-rust/crates/minion-agent/src/runtime/` both contain a full
implementation — verified directly, not assumed). Per the adopted workflow, Python drives the audit
and remediation sequence, but this layer's certification table (§16-17) must record both languages'
status, unlike a not-yet-reached layer where Rust may legitimately remain `NOT_IMPLEMENTED`.

---

## 2. Normative sources

- Frozen design: `design/2026-08-20-minion-agent-design.md` §3 "The plugin runtime" (lines 179-436)
- Spec: no dedicated `spec/runtime.md` exists yet — `spec/*.md` currently covers Phases 2-4 only
  (llm/session/agent/tools/target-model-transformation/harness/authority). **Gap noted in §15.**
- `/pi-parity-manifest.yaml` rows: `MINION-001` (plugin runtime/context/fiber/services/events/
  effects — disposition `intentional divergence`)
- Canonical conformance: `conformance/runtime/*.yaml` (11 files, enumerated in §4)
- Pinned Pi source paths/symbols: not applicable in the usual sense — see the certification note
  above. Cordis is the credited design lineage (not Pi itself); no specific pinned Pi source paths
  govern this layer.
- Approved divergences: the entire layer is itself the approved, named intentional divergence
  (`MINION-001`).

---

## 3. Pi behavior summary

Not applicable in the normal sense this template expects. Runtime is not reproducing Pi-visible
behavior — Pi has no plugin/fiber/service-runtime kernel at all; Minion's runtime exists to host the
higher layers (LLM, session, agent, tools) that *do* reproduce Pi-visible behavior. The relevant
"Pi relevance" is negative: nothing in this layer should leak Minion-runtime-specific behavior into
what a later layer exposes as Pi-visible (e.g., a plugin-loading race must never become an
observable difference in agent/turn/tool semantics). That property is exercised by later layers'
own conformance, not this layer's.

---

## 4. Requirement traceability

Requirement IDs follow `process/requirement-id-convention.md` (`RT-###` prefix). Derived directly
from the frozen master §3 text (not from code, not from memory — read fresh for this audit) and
cross-referenced against the master's own §8 enumeration of intended `conformance/runtime/` scenario
names, which itself functions as a second, independent requirement list.

| ID | Requirement | Source | Canonical scenario | Status |
|---|---|---|---|---|
| RT-001 | Fiber lifecycle: `Pending → Loading → Active`, with `dispose`/dependency-loss/init-failure transitions exactly as the state diagram specifies | §3 "Fiber" | *(none — no scenario exercises the full transition diagram end-to-end)* | **GAP** |
| RT-002 | `Failed` is stable — dependency changes never retry a failed plugin; recovery is disposal + fresh mount only | §3 "Fiber" | `failed-remains-failed` | COVERED |
| RT-003 | Loading is a transaction: a loading attempt invalidated by dependency loss or disposal cannot register further owned effects, and existing effects unwind only after the attempt is stopped (no-race commit) | §3 "Fiber" | `dependency-loss-during-loading-never-activates` | COVERED (transition-outcome tested; the no-race *mechanism* itself — that no effect registration can race the unwind — is not independently verified; see §15) |
| RT-004 | Service identity is `(name, realm)`, compared by string value — never object/enum/pointer/type identity | §3 "Service resolution" | *(none directly — `service-exclusivity` exercises identity indirectly but doesn't assert value-vs-identity comparison directly)* | **GAP** |
| RT-005 | Registration is exclusive: a second `provide()` for the same service in one realm raises, naming the fiber that already holds it — no last-wins, no priority | §3 "Service resolution" | `service-exclusivity` | COVERED (the "names the fiber that already holds it" error-content detail not independently confirmed — flag for §9 deep-dive) |
| RT-006 | No fallback stack: disposing a provider does not resurrect an earlier one | §3 "Service resolution" | *(none — `service-exclusivity` tests rejection, not what happens to visibility after the winning provider disposes)* | **GAP** |
| RT-007 | Visibility is narrower than registration: a service resolves only while its providing fiber is `ACTIVE`; a `check` predicate may narrow visibility further; a registered-but-inactive provider is invisible to injection | §3 "Service resolution" | *(none of the 11 files test ACTIVE-gating or a `check` predicate explicitly)* | **GAP** |
| RT-008 | Dependents react to the resolved provider: every fiber injecting a service is rechecked/refreshed when that service appears or disappears | §3 "Service resolution" (reactive-dependency mechanism) | `reactive-dependency` | COVERED |
| RT-009 | A scope is a tagged context; the registration context determines both visibility and ownership (a registration can never be visible in one scope but disposed via another) | §3 "Scoped registration" | `scoped-registration-visibility` | COVERED |
| RT-010 | Scoped registration visibility inherits *down* — a child scope sees its own and ancestors' registrations; an ancestor never sees a descendant's | §3 "Scoped registration" table | *(none — `scoped-registration-visibility`'s own description covers ownership/disposal scoping, not the down-inheritance direction specifically; `nested-scope-disposal` covers the disposal-cascade direction, not visibility-inheritance)* | **GAP** |
| RT-011 | Event admission extends *up* — a listener tagged with an ancestor receives a descendant's dispatch, never the reverse; untagged listeners/registrations participate everywhere | §3 "Scoped registration" table | `scoped-event-admission` | COVERED |
| RT-012 | Disposing a scope removes exactly its own and its descendants' registrations, leaving ancestors and siblings intact, in reverse creation order | §3 "Scoped registration" | `nested-scope-disposal` | COVERED |
| RT-013 | `ctx.effect(fn)` runs `fn` immediately and collects its disposer; disposers run in reverse order on disposal or unload, whichever first | §3 "Effects" | `effect-reversal` | COVERED |
| RT-014 | Double-disposal is a no-op | §3 "Effects" | *(none)* | **GAP** — also independently flagged by `fidelity-assurance-method.md` §6's own example property list ("no effect survives owner disposal", "double dispose is safe") |
| RT-015 | Creating an effect on an already-disposed fiber raises | §3 "Effects" | *(none)* | **GAP** |
| RT-016 | Four dispatch modes (`emit`/`parallel`/`serial`/`waterfall`) with the exact awaited/order/returns matrix in §3's table; a mismatch between an event's declared mode and its dispatch-site mode is a startup error | §3 "Events" | *(none of the 11 directly test `emit`/`parallel`/`serial` in isolation, or the declaration-mismatch startup error — all existing scenarios exercise `waterfall`)* | **GAP** (three of four dispatch modes, plus the declaration-mismatch rule, have zero direct scenario coverage) |
| RT-017 | Waterfall decision pattern: not calling `next` stops the chain and that listener's return value is the chain's result | §3 "Waterfall" | *(none — no scenario's primary subject is short-circuit)* | **GAP** |
| RT-018 | Waterfall delegation: calling `next()` runs the downstream chain with current args and returns its result unchanged unless the caller transforms it | §3 "Waterfall" | *(none directly — exercised incidentally by other scenarios' dispatch plumbing, but no scenario's primary subject is baseline delegation)* | **GAP** (as an explicit, primary-subject scenario) |
| RT-019 | Waterfall transformation: `next(*replacement)` runs downstream with replacement args instead of the original, and the transform composes down the chain | §3 "Waterfall" | *(none directly — `computed-waterfall-terminal` is adjacent but its own description scopes it to the terminal value on full delegation, not mid-chain replacement propagation)* | **GAP** |
| RT-020 | `next` may be called at most once; a second call raises | §3 "Waterfall" | `waterfall-next-called-twice` | COVERED |
| RT-021 | Every waterfall event declares a terminal continuation (never implicitly `None`), returned when the innermost listener delegates or the chain is empty | §3 "Waterfall" | `waterfall-terminal-continuation`, `computed-waterfall-terminal` | **VERIFIED PARTIAL** — read `waterfall-terminal-continuation.yaml`'s full body: it mounts two listeners, both delegating/transforming, so it's the non-empty fully-delegating case only. No scenario dispatches a waterfall event with **zero** mounted listeners to confirm the terminal returns directly with an empty chain. Confirmed gap, not just a naming ambiguity. |
| RT-022 | Scope filtering on dispatch is additive: an untagged listener is always admitted; a dispatch with no key admits only untagged listeners; adding scope filtering changes no unscoped behavior | §3 "Waterfall" ("Scope filtering is additive") | `scoped-event-admission` | **VERIFIED PARTIAL** — read the full body: it genuinely well-covers the tagged-admission rules (two dispatches, one at an ancestor scope and one at a descendant scope, with a full expected trace confirming ancestor+untagged fire for the ancestor-scoped dispatch while descendant does not — real, solid evidence for RT-011's "never the reverse" direction). But every dispatch step in this scenario specifies an explicit `scope:` key; **no scenario dispatches with no scope key at all** to confirm the "no-key dispatch admits only untagged listeners" sub-rule specifically. Narrower, more precise gap than originally flagged. |
| RT-023 | Plugin config validates through Pydantic; JSON Schema export is available for the conformance layer | §3 "Config" | *(none in `conformance/runtime/` — likely Tier-2 Python-specific, not a cross-language conformance concern; needs an explicit disposition, not silence)* | **UNDISPOSED** — needs an explicit `deferred to Tier 2` or equivalent call, not left blank |

### Coverage beyond the master's own §8 enumeration

Three scenarios exist with real, valuable content the frozen master's §8 list doesn't name by
these titles, but which do assert genuine §3 normative rules (RT-002, RT-003 above): `failed-
remains-failed` and `dependency-loss-during-loading-never-activates`. Recorded as legitimate
additional coverage, not a naming defect — §8's list predates some of this content and should be
treated as informative, not the sole enumeration authority (consistent with the frozen master's own
normativity rule: "the executable result is the compatibility oracle... behavior is not
'unspecified' merely because no YAML file encodes it yet" — that cuts both ways, for coverage that
exists beyond the enumerated list too).

### Master's §8 names not directly mapped above

`service-visibility`, `double-dispose` → RT-007, RT-014 (gaps, listed above under different RT
numbering since the master's scenario-name list and this audit's derived requirement list aren't
required to be 1:1, per `requirement-id-convention.md` §6).
`waterfall-short-circuit`, `waterfall-delegation`, `waterfall-result-propagation`,
`waterfall-result-replacement`, `waterfall-replacement-arguments`, `waterfall-empty-chain-terminal`
→ RT-017, RT-018, RT-019, RT-021 above.
`scoped-registration-ownership` → folded into RT-009's coverage (the existing
`scoped-registration-visibility.yaml` scenario's own description already asserts both visibility
*and* ownership/disposal-scoping in one file — the master's §8 list names these as two separate
scenarios; current reality is one consolidated scenario covering both properties). Not a gap, a
naming-granularity difference — worth deciding explicitly whether to keep consolidated or split,
not something to silently leave ambiguous.

---

## 5. Implementation inventory

| File/module | Responsibility | Decision | Evidence |
|---|---|---|---|
| `context.py` (238 lines) | `Context`: service repository, `__getattr__`/`require()` dual resolution, `extend()` | *(pending §9-12 deep audit — see §17)* | RT-004, RT-007, RT-008 |
| `disposable.py` (67 lines) | Disposer collection/reverse-order execution | *(pending)* | RT-013, RT-014, RT-015 |
| `errors.py` (33 lines) | Runtime error types | *(pending)* | — |
| `events.py` (219 lines) | Four dispatch modes, waterfall mechanics, scope-filtered admission | *(pending)* | RT-016 through RT-022 |
| `fiber.py` (196 lines) | Fiber lifecycle state machine | *(pending)* | RT-001, RT-002, RT-003 |
| `plugin.py` (89 lines) | Plugin mounting/reconciliation | *(pending)* | RT-001, RT-023 |
| `registry.py` (75 lines) | Service registry | *(pending)* | RT-004, RT-005, RT-006 |
| `scope.py` (69 lines) | Scope/`ScopeKey` mechanics | *(pending)* | RT-009, RT-012 |
| `scoped_registry.py` (51 lines) | Scoped registration table | *(pending)* | RT-009, RT-010 |
| `service.py` (97 lines) | Service resolution mechanics | *(pending)* | RT-004 through RT-008 |

Module-to-requirement mapping above is a starting hypothesis from responsibility names and sizes,
not yet verified by reading each module — that verification is the deep-dive audit in §9-12, not
yet performed (see §17).

Rust equivalents (`minion-agent-rust/crates/minion-agent/src/runtime/{disposable,error,event,
fiber,identity,plugin,scope,scoped_registry,service}.rs` — confirmed present, not yet audited) need
the same inventory pass before this layer can certify. Not started.

---

## 6. Existing-test audit

Not started. This requires reading the Python `tests/runtime/` and `tests/test_composition.py`
(seen referenced in earlier session mypy output) suites and classifying each existing test, plus
the Rust `tests/runtime_*.rs` suite (5 files observed: `runtime_disposable.rs`, `runtime_event.rs`,
`runtime_fiber.rs`, `runtime_scope.rs`, `runtime_service.rs`) the same way. Deferred to a follow-up
pass — see §17.

---

## 7. Missing test / conformance coverage

### Canonical conformance

- [ ] RT-001: full Fiber lifecycle transition diagram, end-to-end
- [ ] RT-004: service identity is string-value comparison, not object/type identity
- [ ] RT-006: no fallback stack after a provider disposes
- [ ] RT-007: ACTIVE-gated visibility + `check` predicate narrowing
- [ ] RT-010: scoped registration visibility inherits down (distinct from disposal-cascade)
- [ ] RT-014: double-disposal is a no-op
- [ ] RT-015: effect creation on a disposed fiber raises
- [ ] RT-016: `emit`/`parallel`/`serial` dispatch modes directly; declared-vs-dispatched mode
      mismatch is a startup error
- [ ] RT-017: waterfall short-circuit (decision pattern)
- [ ] RT-018: waterfall baseline delegation as an explicit primary-subject scenario
- [ ] RT-019: waterfall mid-chain replacement-argument propagation
- [ ] RT-021 (verified gap): the zero-listener empty-chain terminal case — confirmed absent, not
      just ambiguous; see §4's verified-partial note
- [ ] RT-022 (verified narrower gap): a dispatch with no `scope:` key at all admits only untagged
      listeners — confirmed absent specifically; the tagged-admission rules themselves are already
      well covered by `scoped-event-admission`

### Language-specific tests

Not assessed yet — depends on §6.

### Property/invariant tests

`fidelity-assurance-method.md` §6 explicitly names "no effect survives owner disposal" and "double
dispose is safe" as expected Hypothesis-style property tests for this layer — cross-check against
RT-014/RT-015 once §6 (existing-test audit) is done.

### State-machine, concurrency, fuzz, fault-injection tests

Not assessed yet.

---

## 8-14. Failure model / security / reliability / observability / performance / public API / documentation

**Not started.** These require the module-level deep-dive (§5-6) as a prerequisite and are real,
substantial audit work — not filled in here to avoid the failure mode this whole assurance program
exists to prevent (certifying on "conformance all green" without doing the rest). Concrete starting
points already visible from this pass, to seed that work rather than start from nothing:

- **Security (§9):** plugin registration trust (`registration is exclusive` — RT-005 — is itself a
  security-relevant property: it prevents a plugin from silently hijacking another's service slot);
  disposed-fiber-creates-effect misuse (RT-015 gap is also a hardening-relevant finding, not just a
  correctness gap).
- **Reliability (§10):** the "no-race" loading/unwind guarantee (RT-003) explicitly calls out that
  its exact mechanism is implementation-specific — that's exactly where a concurrency test belongs,
  not covered yet.
- **Observability (§11):** no lifecycle/dependency-transition telemetry reviewed yet.
- **Performance (§12):** service lookup / event dispatch / reactive reconciliation complexity not
  reviewed yet — `fidelity-assurance-method.md` §10 names these explicitly as audit targets.

---

## 15. Findings

| ID | Severity | Classification | Description | Disposition / action |
|---|---|---|---|---|
| RT-F001 | MEDIUM | Design/conformance completeness defect (runtime is intentional Minion architecture, not Pi-derived — see §1's certification note; not `PI_PARITY_DEFECT`) | 11 of 23 derived RT requirements (RT-001, RT-004, RT-006, RT-007, RT-010, RT-014, RT-015, RT-016, RT-017, RT-018, RT-019) have zero direct canonical-conformance evidence, despite being clearly stated normative rules in frozen master §3. Two more (RT-021, RT-022) have real partial coverage with a specific, verified missing sub-case each (§4) — a distinct, narrower category from zero evidence, not double-counted here | Write the missing `conformance/runtime/*.yaml` scenarios (11 new + 2 narrow additions) before this layer certifies |
| RT-F002 | LOW | Design/conformance completeness defect — **resolved during this audit pass, not just flagged** | Read both scenario files' full bodies directly. `waterfall-terminal-continuation.yaml` mounts two delegating listeners — confirmed non-empty-chain only, zero-listener case is a genuine gap. `scoped-event-admission.yaml` genuinely well-covers tagged-admission (both directions, confirmed via its expected trace), but every dispatch step specifies an explicit `scope:` key — the no-key-dispatch sub-rule is a real, narrower gap than originally suspected | Folded into RT-F001's missing-scenario list (RT-021, RT-022) with the now-precise scope of what's actually missing |
| RT-F003 | LOW | Naming/documentation drift | Frozen master §8 names `scoped-registration-visibility` and `scoped-registration-ownership` as two separate scenarios; only one consolidated scenario exists covering both properties | Decide explicitly: keep consolidated (update §8's list to match) or split into two files. Either is fine; leaving it undecided is not |
| RT-F004 | MEDIUM | Design/conformance completeness defect | RT-023 (plugin config validates via Pydantic) has no explicit disposition — not in canonical conformance, not confirmed as an intentional Tier-2-only concern | Give it one of `adopted (Tier 2 only) / deferred / needs conformance` explicitly rather than leaving it silently undisposed |
| RT-F005 | HIGH | Process gap, not a runtime defect | No `spec/runtime.md` exists. `spec/*.md` currently covers only Phases 2-4 (llm/session/agent/tools/target-model-transformation/harness/authority) — runtime, the very first layer being audited, has no normative spec document of its own, only the frozen master's §3 prose | Write `spec/runtime.md` extracting §3's rules in the same terse normative style as the other six `spec/*.md` files, before or during this layer's certification |

No `PARITY_CONSTRAINED_RISK` or `PI_BEHAVIOR_UNCERTAIN` findings — expected, since this layer isn't
Pi-derived behavior in the usual sense (see §1, §3).

---

## 16. Certification gate

```text
Design alignment                         [x]  -- requirements traced to frozen master §3 directly
Pi parity                                [~]  -- not applicable in the usual sense; see certification note
Normative spec                           [ ]  -- RT-F005: spec/runtime.md does not exist yet
Parity manifest                          [x]  -- MINION-001, correctly dispositioned intentional divergence
Canonical conformance                    [ ]  -- RT-F001: 11/23 requirements have zero direct evidence, 2 more have a verified partial gap
Python tests where implemented           [ ]  -- not audited yet (SS6)
Rust tests where implemented             [ ]  -- not audited yet (SS6)
Property/invariant tests                 [ ]  -- not audited yet
Concurrency tests where applicable       [ ]  -- not audited yet (RT-003's no-race guarantee needs one)
Fault-injection tests where applicable   [ ]  -- not audited yet
Security review                          [ ]  -- not started (SS9)
Reliability review                       [ ]  -- not started (SS10)
Observability review                     [ ]  -- not started (SS11)
Performance review                       [ ]  -- not started (SS12)
Public API review                        [ ]  -- not started (SS13)
Documentation                            [ ]  -- not started (SS14)
All findings classified                  [x]  -- 5 findings above, each classified
No unresolved Pi uncertainty             [x]  -- N/A, no PI_BEHAVIOR_UNCERTAIN findings
No unresolved parity defect              [x]  -- N/A, no PI_PARITY_DEFECT findings
Deferred risks recorded                  [x]  -- none needed deferral to risk-register.md yet
```

## 17. Certification result

**Result:** `NOT YET ELIGIBLE`

**Rationale:** Steps 0-2 of `fidelity-assurance-method.md`'s per-layer workflow (identify normative
sources, audit Pi/master source, enumerate requirements, map requirement → canonical conformance)
are complete and produced real, actionable findings — 11 requirement gaps plus 2 verified narrower
partial gaps in canonical conformance, one missing spec document, one naming-consistency question,
one undisposed requirement. Steps 3-13
(implementation inventory verification, existing-test audit, failure-model/security/reliability/
observability/performance/public-API/documentation review, and the independent Rust cross-check
this layer specifically requires per §1) have not been performed. Marking this `CERTIFIED` now would
be exactly the "passing tests without evidence" failure mode the assurance program exists to
prevent.

**Follow-up dependencies:**

1. Close RT-F005 (write `spec/runtime.md`) — arguably should happen before or alongside filling the
   conformance gaps, since new scenarios should cite a stable spec section, not just master §3 prose
   directly.
2. Write the 11 missing conformance scenarios identified in §7 (RT-F001), plus the 2 narrower
   additions for RT-021/RT-022's now-precise, verified gaps (RT-F002 is already resolved, folded in
   here).
3. Resolve RT-F003 (naming decision) — cheap, should close alongside #2.
4. Dispose RT-F004 (RT-023's Tier-2-only status) explicitly.
5. Perform §5-14's deep-dive: module-by-module Python audit, then independent Rust audit against
   the same RT-* requirements (not a copy of Python's answer — per this project's standing rule that
   neither implementation is a behavioral oracle for the other), then the full assurance checklist
   (security/reliability/observability/performance/public-API/documentation).
6. Only then complete §16's gate and move this document's status to `CERTIFIED`.
