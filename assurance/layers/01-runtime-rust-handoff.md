# Runtime Kernel — Rust Handoff Package

**Layer:** `01` (Runtime Kernel)
**Purpose:** Freeze the current Python-side runtime evidence, package the shared contract, and hand
it to Rust for independent validation, without moving the contract while Rust audits it.
**Prepared:** 2026-08-23, from the committed state of `assurance/layers/01-runtime.md` as of commit
`dcee6f3` (docs) / `8704fc6` (code). This handoff package does not itself change the contract, the
taxonomy, or any already-resolved Python finding.
**Status this pass sets:** No change to `01-runtime.md`'s `Rust status` field. Rust updates that
field itself once its own audit produces a result (see §8 below).

---

## 1. The shared contract Rust must independently validate

Python's evidence is not the target Rust reproduces — the contract below is. Rust validates its own
implementation against these artifacts directly:

- **`RT-001` through `RT-023`** — the full requirement set in `assurance/layers/01-runtime.md` §4.
  Every requirement there is Minion-owned (not Pi-derived); Rust's implementation is checked against
  the requirement text and against `spec/runtime.md`, not against Python's source.
- **`spec/runtime.md`** — the normative prose. This is the binding authority for behavior; if
  Python's implementation and this spec ever disagree, the spec wins and Python has a bug, not the
  other way around.
- **`/pi-parity-manifest.yaml`, entry `MINION-001`** — `disposition: intentional divergence`. The
  runtime kernel is Minion's own architecture, not a Pi reproduction; `MINION-001`'s rule is "must
  preserve Pi-visible behavior at higher layers," which is a constraint on layers built *on* this
  kernel, not on the kernel's own internal design.
- **`conformance/runtime/*.yaml`** — the canonical scenario set. All 23 requirements currently have a
  disposition against this set (21 direct canonical scenarios, RT-010 by unit-test evidence, RT-004/
  RT-023 disposed out of scope — see §3 below).
- **`conformance/schema/runtime-scenario.schema.json`** — the DSL/schema Rust's runner must consume.
  Three extensions landed during this work and need Rust's explicit review before they're canonical
  (§7).

## 2. Python is not the behavioral oracle

This is a hard rule for this handoff, not a courtesy:

- Python's findings (§4 of this document) are **risk hints** — places to look, not verdicts to
  inherit. A Python finding does not imply Rust has the same issue; a clean Python category does not
  imply Rust is clean there either.
- Rust validates its own implementation against the shared contract (§1) directly — reading
  `RT-001`..`RT-023` and `spec/runtime.md`, then checking Rust's own source and tests, the same way
  Python's audit checked Python's source against the same contract.
- **Do not port Python's fixes.** Where Python found and fixed a bug (`RT-F009`, `RT-F010`,
  `RT-F011`, `RT-F014`), the fix described is the Python-specific shape of a Python-specific
  implementation (e.g. `try`/`finally` around `_unwind()` calls in a Python `Fiber` class). Rust's
  equivalent structure may not have the same bug, may have a different bug in the same area, or may
  need an entirely different fix shape idiomatic to Rust (`Result`/`?`, `Drop`, RAII guards, etc.).
  What transfers is the *requirement being violated*, not the patch.

## 3. Python-side assurance status (verbatim from `01-runtime.md`)

Quoted, not paraphrased, from the current committed file:

> Python's side of this layer's certification work is now essentially complete. What remains: the
> independent Rust cross-check, and optionally closing the three open low/medium findings in a
> future pass.

**Complete:**

- §4 Requirement traceability — all 23 `RT-*` requirements dispositioned (21 canonical, RT-010 by
  Python unit test, RT-004/RT-023 disposed out of scope).
- §5 Implementation inventory — all 10 Python runtime modules deep-audited against their traced
  requirements.
- §6 Existing-test audit — all 15 `tests/runtime/*.py` files (133 tests) read, run, and classified;
  all `KEEP`.
- §8-14 review — failure model, security, reliability, observability, performance, public API, and
  documentation, all reviewed against real source, not a checklist restatement.

**Security review: clean.** Verbatim from §9: *"No security finding. This category is solid."* —
exclusivity in `ServiceRegistry.provide()` is unbypassable, disposed/inactive-fiber misuse is fully
rejected everywhere (not only at `effect()`), and scope isolation is bounded to registration
visibility by design, matching what `spec/runtime.md` claims and nothing more.

**Performance review: clean.** Verbatim from §12: *"No performance finding. This category is solid
at the scales this runtime is designed for."* — no accidentally-quadratic pattern found;
`reconcile()`'s pass count is bounded by dependency-chain depth (inherent to the algorithm's
correctness, not a scaling defect), not benchmarked (no perf harness exists, none was built).

**Resolved findings (Python, this layer):** `RT-F001` through `RT-F007`, `RT-F009`, `RT-F010`,
`RT-F011`, `RT-F014`. Verbatim descriptions/dispositions for the three this handoff specifically
calls out:

| ID | Severity | Classification | Description | Disposition |
|---|---|---|---|---|
| `RT-F010` | LOW | `PARITY_NEUTRAL_HARDENING` — RESOLVED | `context.py`'s `ctx.effect()`/`ctx.provide()` "called outside a fiber" guards raised the bare builtin `RuntimeError`, the same defect class as `RT-F009` in a different file — reachable directly by calling either on a root/unscoped context | Fixed: both now raise `RuntimeError_`. `test_edges.py`'s two tests pinning the old builtin type updated to match. Full suite clean |
| `RT-F011` | MEDIUM | `PARITY_NEUTRAL_HARDENING` — RESOLVED | `Fiber.load()`/`unload()`/`dispose()` transitioned to their terminal/settled state only on the line *after* calling `_unwind()` (via `dispose_all()`); if a disposer raised, the `ExceptionGroup` propagated before the state transition ran, leaving the fiber permanently stuck at `LOADING` (a failing load whose own failure-unwind also fails), `UNLOADING`, or mid-`dispose()` — reproduced directly with a throwaway script before fixing | Fixed: all three methods (and `_unwind()` itself) now use `try`/`finally` so the state always settles; the `ExceptionGroup` still propagates to the caller afterward, surfaced rather than swallowed — same principle `disposable.py` already applies to individual disposers, extended to the fiber's own state. Three new regression tests added to `test_fiber.py`. Full suite clean |
| `RT-F014` | LOW | `PARITY_NEUTRAL_HARDENING` — RESOLVED | `PluginRegistry` — the return type of the widely-used `ctx.plugins` property — was not exported from `minion_agent.runtime`, unlike its siblings `ServiceRegistry`/`EventBus` which are exported despite being reachable the same way via `ctx.registry`/`ctx.events`. `test_public_surface.py`'s mechanical check only pins whatever `__all__` already contains, so it couldn't have caught an omission from day one | Fixed: `PluginRegistry` added to `__init__.py`'s imports and `__all__`, and to `test_public_surface.py`'s `EXPECTED` set. Full suite clean |

`RT-F010` and `RT-F014` are Python-source/Python-export-surface specifics — read them as risk hints
for "does Rust have an analogous class of bug," not as findings Rust needs to independently resolve
in its own right (there is no Rust equivalent of a Python `__all__` list or a Python builtin
`RuntimeError` vs. project hierarchy distinction). `RT-F011` is different — see §5, it names a real
runtime-semantics probe, not a Python-specific detail.

## 4. Two Python findings carried forward, deliberately not fixed

Both remain open in `01-runtime.md` exactly as recorded. Not fixed in this handoff-preparation pass,
per instruction. Quoted verbatim:

**`RT-F012`** (LOW-MEDIUM, `PARITY_NEUTRAL_HARDENING`, open):

> `PluginRegistry.reconcile()`'s two-pass loop aborts entirely if any one fiber's `load()`/`unload()`
> raises — even after `RT-F011`'s fix, sibling fibers still awaiting action in the same pass are left
> unprocessed until a later mount/unmount triggers another `reconcile()` call. Only manifests when a
> disposer itself fails during a multi-fiber reconciliation pass.
>
> Not fixed — the correct shape mirrors `disposable.py`'s own aggregate-and-continue pattern one
> level up (per-fiber try/except, collect failures, keep processing the pass, raise an aggregated
> `ExceptionGroup` at the end), which is a larger, riskier change than this pass's other fixes.
> Recorded for a future pass.

**`RT-F013`** (MEDIUM, `PARITY_NEUTRAL_HARDENING`, open):

> `ctx.plugin()` — the mount API actually used throughout `tests/conformance/agent_runner.py` and
> most of `tests/runtime/`'s own suite — mounts and calls `reconcile()` before returning the fiber,
> so a caller has no opportunity to attach `on_state_change`/`on_effect` before the fiber's first
> transitions (`LOADING`, possibly straight to `ACTIVE` or `FAILED`) have already fired unobserved.
> The lower-level two-step (`ctx.plugins.mount()`, attach hooks, `await ctx.plugins.reconcile()`) —
> what the conformance runner itself uses — is the only way to observe from `PENDING` onward.
>
> Not fixed — closing this is an API design decision (hook parameters on `ctx.plugin()`, or
> documenting the two-step contract as the observability-sensitive path), not a small isolated
> change. Recorded for whoever next touches the `Context` mount API.

**What Rust must do with each:** assess and classify — do not inherit Python's disposition by
default. For each of `RT-F012` and `RT-F013`, determine which of three applies to Rust:

1. **Rust-local issue** — Rust's own reconciliation loop / mount API has the same class of gap, in
   its own idiomatic shape. Record a new Rust-side finding using the adopted taxonomy; do not reuse
   the `RT-F012`/`RT-F013` IDs (those are Python-scoped in the finding ledger).
2. **Shared runtime-contract concern** — the underlying requirement (`RT-001`/`RT-008` for
   `RT-F012`'s reconciliation-abort case; observability generally for `RT-F013`) turns out to be
   under-specified in `spec/runtime.md` itself, such that neither implementation is actually wrong
   but the contract doesn't say what "correct" looks like here. If so, that's a
   `CONTRACT_ASSURANCE_DEFECT` against the spec, not an implementation finding against either
   language — flag it, do not silently resolve it by picking one behavior.
3. **No corresponding issue** — Rust's reconciliation loop and mount API are structured such that
   this class of problem cannot arise (e.g., a different aggregation strategy, or a mount API that
   structurally cannot return control before hooks attach). State plainly why, the same way Python's
   §9/§12 stated why security and performance were clean.

## 5. `RT-F011` as a specific Rust audit probe

Do not assume Python's `try`/`finally` implementation is the required Rust implementation. The
requirement is behavioral, not structural:

- Inspect Rust's Fiber-equivalent `load`/`unload`/`dispose` (or whatever they're named in the Rust
  runtime) state-transition logic specifically for the failure path: what happens when the
  teardown/disposer logic itself fails during unwind, on top of (or instead of) an ordinary
  load/unload/dispose failure.
- **Verify the state always settles correctly** — no path where a disposer/teardown failure leaves
  the fiber-equivalent permanently in a non-terminal, in-between state. What "settles correctly"
  means is defined by `spec/runtime.md`'s Fiber lifecycle section and the `RT-001`/`RT-002`/`RT-003`
  requirements, not by mirroring Python's specific `LOADING`→`FAILED`, `UNLOADING`→`PENDING`,
  `(ACTIVE→)UNLOADING`→`DISPOSED` transitions line-for-line — though those ARE the required end
  states per the spec, so Rust's equivalent end states should match those, even if the mechanism
  differs.
- **Verify the original error still propagates** — a teardown/disposer failure must still surface to
  the caller (aggregated with the triggering failure where more than one exists), not be silently
  swallowed by whatever mechanism settles the state. Rust's idiomatic shape for this might be a
  `Result` that carries a combined error, a panic-safety guard, an RAII `Drop` that can't itself fail
  and instead logs-and-continues, or something else entirely — the requirement is "surfaced, not
  swallowed," not "matches Python's `ExceptionGroup` shape."
- If Rust already handles this correctly (by construction, by a different mechanism, or because
  Rust's ownership/`Drop` model makes the Python failure mode structurally impossible), say so
  explicitly with the specific reasoning, the way Python's §9 said why security was clean rather than
  just checking a box.

## 6. Rust-owned certification work (remaining, this layer)

Mirrors what Python's audit did (§5/§6/§8-14 of `01-runtime.md`), performed independently against
the shared contract in §1 — not by reading Python's audit and agreeing with it:

1. **Module-by-module Rust runtime audit** — read Rust's runtime kernel source in full, module by
   module, and check actual behavior against `RT-001`..`RT-023` and `spec/runtime.md`, the same way
   Python's §5 did (which found and corrected a wrong RT-004/005/006-to-file pairing along the way —
   expect to find your own version of "the traceability table's claim doesn't quite match the code,"
   not to confirm it cleanly on the first pass).
2. **Existing Rust runtime-test classification** — every `runtime_*.rs` test (or equivalent), read,
   run, and classified `KEEP` / `STRENGTHEN` / `MOVE TO CONFORMANCE` / `REWRITE` / `DELETE`, mapped to
   `RT-*` IDs where applicable, the same legend Python's §6 used.
3. **`ScopedRegistry`-equivalent unit test for `RT-010`** — Rust's kernel almost certainly has its own
   inherit-down scoped-visibility primitive (whatever it's named). Add or verify a direct unit test
   proving the same three properties Python's `tests/runtime/test_scoped_registry.py` proves: a
   descendant sees its own scope then ancestors nearest-first then untagged; an ancestor never sees a
   descendant's entries; siblings are invisible to each other. This is unit-test evidence, not
   canonical conformance, for the same reason it is on the Python side — no concrete registry wires
   this primitive to the plugin-mount surface yet in either language.
4. **Rust §8-14 review**, against the same seven categories Python covered, each independently
   assessed against Rust's own source:
   - **Failure model** — every raised error type, does it carry enough to act on, any path that
     swallows a failure instead of surfacing it.
   - **Security** — registration exclusivity, disposed/inactive-owner misuse rejection, scope
     isolation boundaries.
   - **Reliability/operations** — mid-transition failure windows (see `RT-F011` probe, §5), what a
     failing disposer/teardown does to in-flight reconciliation (see `RT-F012` assessment, §4).
   - **Observability** — is every state transition and failure actually observable from outside; does
     the primary mount API give a caller the chance to attach observation before anything fires (see
     `RT-F013` assessment, §4).
   - **Performance** — any accidentally-quadratic pattern in the registry/event-dispatch/
     reconciliation primitives; design-level review, not benchmarking, matching Python's scope.
   - **Public API** — does every exported name have accurate documentation; does the exported surface
     match what's actually used across the test suite (Python's `RT-F014` was exactly this class of
     gap — check for Rust's own version, don't assume it's absent).
   - **Documentation** — does `spec/runtime.md` match Rust's actual behavior; flag any drift found,
     the same way Python's §13-14 explicitly checked for drift and found none.
5. **Classify every new finding using the adopted taxonomy** — `CONTRACT_ASSURANCE_DEFECT` for
   spec/conformance/traceability/evidence gaps, `PARITY_NEUTRAL_HARDENING` for a real but
   non-Pi-parity-related implementation improvement, or the other project-wide classes
   (`PI_PARITY_DEFECT`, `PARITY_CONSTRAINED_RISK`, `PI_BEHAVIOR_UNCERTAIN`) only where an actual Pi
   comparison is meaningful — which, per `01-runtime.md` §3, it structurally is not for this
   Pi-less kernel layer. Use the next available finding ID after whatever the ledger holds at audit
   time (do not renumber or reuse Python's `RT-F0xx` IDs; Rust findings get their own next number in
   the same sequence, continuing from wherever this handoff leaves it).

## 7. Shared-contract review: the three DSL/schema extensions

Landed during the Python-side conformance work (`RT-F006`'s resolution and `RT-F007`'s fix), all
under `conformance/schema/runtime-scenario.schema.json` and
`minion-agent-python/tests/conformance/runner.py`. **Not yet canonical** — this is exactly the
review the shared-contract reviewer rule exists for (§8 below). Three changes, each needs explicit
sign-off against the checklist that follows:

1. **`provides: {name, visible}`** — the plugin `provides` field may now be an object with a
   `visible: false` flag instead of a bare service-name string, which registers the service with a
   `check` predicate that always returns false (closes `RT-007`'s check-narrowing half).
2. **`attempt_effect` step** — a new scenario step type that calls the runtime's effect-creation
   entry point against an already-mounted plugin's context from outside that plugin's own apply/init
   body, reaching whatever state the fiber is currently in (closes `RT-015`).
3. **`echo_args` listener action** — a new waterfall-listener action that returns the positional
   arguments the listener actually received (minus the trailing `next`/continuation), so a downstream
   listener can prove what it was called with (closes `RT-019`).

**Rust must explicitly verify, for each of the three:**

- [ ] **Language-neutral.** Nothing in the field/step/action's *meaning* depends on a Python
  mechanism. (`visible: false` describes a check-predicate outcome, not a Python callable; the step
  and action describe an observable interaction with the runtime's public surface, not a Python call
  signature.)
- [ ] **No Python-specific assumptions encoded.** In particular: does `attempt_effect` assume
  anything about Python's synchronous-vs-async execution model that wouldn't translate to Rust's
  async runtime? Does `echo_args`'s "positional arguments minus the trailing continuation" framing
  assume Python's `*args`-style variadic calling convention in a way that doesn't map cleanly onto
  Rust's typed listener signature?
- [ ] **Rust can consume each through a thin runner.** Per the runner-purity rule already adopted in
  `process/implementation-conformance-workflow.md`: *"A runner MUST NOT implement semantic behavior
  that belongs in the library... If a runner can make an incorrect implementation pass by supplying
  missing semantics itself, the runner is invalid."* Confirm Rust's runner can implement all three by
  calling Rust's own real public runtime API (mount/effect/dispatch equivalents) and normalizing
  output — not by hand-computing what the "correct" check-predicate result, effect-rejection error,
  or received-arguments value should be.
- [ ] **The mock/backend seam stays distinct from semantic logic in the runner.** Per the same
  workflow doc: *"A mock provider/tool swapped in through the library's own real plugin/service seam
  is not covered by this rule... The dividing line: if a real provider, unmodified, would exercise
  the same code path as the mock, it's a seam. If the runner's own code decides the 'correct' outcome
  instead of asking the library, that's the library's job leaking into the runner."* Apply that
  dividing line to all three extensions specifically — e.g., `attempt_effect`'s "attempt an effect
  from outside apply()" must exercise Rust's real inactive-owner rejection path, not a runner-side
  guess at what that rejection should look like.

If any of the three fails one of these checks for Rust, that is itself a finding against the DSL
extension (`CONTRACT_ASSURANCE_DEFECT`, since it's a shared-contract/schema defect, not an
implementation defect in either language) — raise it rather than silently reworking the schema
unilaterally, since `conformance/**` and `spec/**` changes require the same shared-contract review
process this section is asking Rust to perform.

## 8. Reviewer-rule requirement

Per the adopted shared-contract reviewer rule
(`process/implementation-conformance-workflow.md` §"Shared-contract reviewer rule", quoted verbatim):

> Changes under `conformance/**`, `spec/**`, or `/pi-parity-manifest.yaml` MUST receive explicit
> semantic-owner approval before merge. Where independent Python and Rust implementation maintainers
> exist, such changes SHOULD also receive review from the affected implementation owners.

The three DSL/schema extensions in §7 are exactly this class of change. **Rust review of these three
extensions is required before Runtime Layer certification** — not optional, not deferrable to a
later layer. This is separate from (and in addition to) Rust's own independent implementation audit
in §6.

## 9. Expected result of this handoff

Rust's audit is complete, for this layer, when it produces:

1. **Rust findings, if any** — new finding IDs continuing the ledger, each classified per the adopted
   taxonomy (§6.5), each with the same evidence-grounded rigor Python's findings carry (concrete file/
   line references, reproduction where applicable, not assertions).
2. **Rust test/conformance changes, if any** — new or strengthened Rust unit tests (including the
   `RT-010` `ScopedRegistry`-equivalent test, §6.3), and/or new canonical `conformance/runtime/*.yaml`
   scenarios if Rust's audit surfaces a gap Python's canonical set didn't — routed through the
   shared-contract reviewer rule (§8) like any other `conformance/**` change.
3. **A shared-contract review result for the three DSL/schema extensions** (§7) — pass, or specific
   findings against one or more of them, filed as `CONTRACT_ASSURANCE_DEFECT`.
4. **An updated `Rust status` field in `assurance/layers/01-runtime.md`'s header** (currently
   `IMPLEMENTED`), reflecting the outcome of Rust's own audit — not just left as-is by default.
5. **An explicit statement of whether Runtime Layer can move to `CERTIFIED`**, or, if not, exactly
   what specifically still blocks it — enumerated the same way `01-runtime.md` §17 currently
   enumerates Python's remaining follow-up dependencies, not a general "more work needed."

This handoff package itself does not move `01-runtime.md`'s status, gate, or `Rust status` field —
those change only once Rust's own audit produces the result described above.
