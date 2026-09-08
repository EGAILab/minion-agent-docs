# Layer 09 — L09-R007 contract convergence (residual status/signal failure-atomicity surface)

**Revision 2, NOT yet approved.** Revision 1 (this same file) was independently challenged
(`assurance/layers/09-active-abort-rust-r007-convergence-challenge.md`, docs PR #32, review commit
`17cdfb61b4996206a75baececb3c50d0dcf5130b`): **CONVERGENCE CONTRACT — REVISION REQUIRED**. The
reviewer accepted revision 1's own status/signal policy in full (see "Decided policy" below,
unchanged from revision 1 except one documentary correction, marked) but found it incomplete: it
never addressed already-claimed inbox input (steering/follow-up drained from `Inbox` before
`_run_wrapped` is even called) that a RUNNING-notification failure then silently discards. Revision
2 adds that missing surface -- see "Preclaimed inbox input" below, a new section, not present in
revision 1.

**Trigger:** `L09-R007` survived two independent reviews (the mandatory `§11.8.8` final complete
review of the PASS-3 candidate, and the PASS-4 targeted finding-closure review of the PASS-4
candidate) -- `process/agent-workflow.md` §11.8's convergence trigger is met on this exact finding.
This is a `§11.8.4` challenge pass over the PASS-4 reviewer's own `§11.8.3` characterization
(`assurance/layers/09-active-abort-rust-targeted-rereview-pass4.md`, docs PR #31, review commit
`054de61af0632c1ca9ddc84b4dcdfb2ddf0fe063`), not an implementation pass.

## Exact state under convergence

- code PR: `EGAILab/minion-agent#17`, exact head: `f13ee17404aa0c1a65b3a8c1c1d622340713f929`
- docs PR: `EGAILab/minion-agent-docs#26`, exact head (revision 1 of this checkpoint):
  `eb844759470e98a8781c5a55d85734187e5957d5`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- `L09-R008`/`L09-R009`: `PROVISIONALLY CLOSED` -- unaffected by this convergence, not reopened,
  not re-touched by the policy below.

## Challenge pass (`§11.8.4`)

**Is the Pi source mapping correct?** Re-audited directly against pinned Pi (`ref-repos/pi` @
`b7bb00b`, `packages/agent/src/agent.ts:486-535`). Confirmed independently:

```text
private async runWithLifecycle(executor): Promise<void> {
  if (this.activeRun) throw ...;
  const abortController = new AbortController();
  ...
  this.activeRun = { promise, resolve, abortController };   // <- controller installed
  this._state.isStreaming = true;                             // <- plain property write
  this._state.streamingMessage = undefined;
  this._state.errorMessage = undefined;
  try {
    await executor(abortController.signal);
  } catch (error) {
    await this.handleRunFailure(error, abortController.signal.aborted);
  } finally {
    this.finishRun();                                          // <- also plain property writes
  }
}
```

Two structural facts the PASS-4 review's own conclusion rests on, confirmed:

1. `this.activeRun = ...`/`this._state.isStreaming = true` (Pi's own analogue of `_start_run_
   signal()`/`set_status(RUNNING)`) are PLAIN, synchronous property assignments -- not calls, not
   listener dispatches, structurally INCAPABLE of throwing in JS. They sit entirely OUTSIDE Pi's
   own `try`, which begins only at `executor(...)`.
2. `finishRun()` (Pi's own analogue of `_end_run_signal()`/`set_status(IDLE)`) is likewise four
   plain property writes plus a promise resolve -- also structurally incapable of throwing --
   inside `finally`.

Pi therefore has NO possible "entry/exit notification observer throws" scenario at all: it has no
synchronous, listener-driven status-notification extension point analogous to Minion's `agent/
status` EMIT event / `on_status_change` callback. The PASS-4 review's own conclusion --
"the precise observer-failure policy cannot be inferred from Pi" -- is CONFIRMED, not merely
asserted. This is a genuinely Minion-owned architectural-mapping decision, `PI_BEHAVIOR_UNCERTAIN`
does not apply (Pi is not uncertain; Pi is silent because the surface does not exist in Pi at all).

**Is the behavior matrix complete enough to distinguish realistic wrong implementations?** The
PASS-4 review's own seven-row matrix is accepted as complete for the entry/exit x throws/returns
space, with one refinement: it does not yet distinguish "a listener throws" from "a listener
returns an awaitable that later rejects" for `on_status_change` -- but `on_status_change`'s own
declared type (`Callable[[AgentStatus], None]`, `agent/instance.py:48`) is synchronous-only, so
that distinction does not exist as a real case; the matrix's synchronous-throw rows already cover
the full space this callable's own type permits.

**Are any cases implementation mechanics rather than observable semantics?** No. "What does
`instance.status`/`instance.signal` read as, and does a subsequent `prompt()` succeed or reject"
are all externally observable through the public `AgentInstance` surface -- none of this is an
internal-mechanics question.

**Does any proposed fix silently reopen a lower certified layer?** No, PROVIDED the resolution
below preserves `AG-008`'s own certified relative write order among `set_status`/`streaming_
message`/`error_message`/`pending_tool_calls` for the NON-throwing path exactly as PASS 4 already
fixed it. `AG-008` never specified any write order for a THROWING observer at all (a fresh gap it
is silent on, not a rule this convergence would contradict), so defining that behavior is additive,
not a reopen.

**Can both Python and Rust implement the rule idiomatically?** Yes -- see "Rust implementability"
below.

**Are all previous review findings represented by an executable or documentary acceptance
criterion?** Yes for `L09-C001`-`C003`/`L09-R001`-`R006`/`L09-R008`/`L09-R009` (all already have
dedicated tests, unaffected here). `L09-R007`'s own happy-path witness already exists
(`test_the_running_status_observer_sees_a_live_signal_and_the_idle_observer_sees_none`); its
failure-path witnesses do not yet exist -- see "Minimal executable witnesses" below.

**Revision-2 addition: is the pre-drain shape correctly mapped from Pi?** Re-verified directly
against pinned Pi (`ref-repos/pi` @ `b7bb00b`, `agent.ts:361-388`, `agent.ts:125-159`). `Agent.
continue()`, when the transcript ends in an assistant message, calls `this.steeringQueue.drain()`
(or, failing that, `this.followUpQueue.drain()`) and only THEN calls `runPromptMessages(...)` ->
`runWithLifecycle(...)`. `PendingMessageQueue.drain()` is itself destructive (splices/replaces its
own backing array) with no rollback path of its own. `AgentInstance.continue_()` (`agent_loop/
driver.py:236-271`) already mirrors this exact pre-drain-then-enter-lifecycle shape via `Inbox.
claim()`. The reviewer's own characterization is confirmed correct: Pi drains BEFORE its own
run-lifecycle begins, exactly like Minion, and Pi's OWN drain is equally irrecoverable in principle
-- Pi simply never observes this in practice because nothing between its own drain and `finishRun`
can throw. Minion's addition of a synchronous, fallible status-notification hook at exactly that
gap is what turns a theoretical Pi non-issue into a real, observable Minion defect. `run_until_
idle()` (`AG-019`, no Pi equivalent at all -- Minion's own pump) has the identical shape: `Inbox.
claim()` then `_run_wrapped(...)`, so it inherits the same gap and the same required fix.

## Decided policy (status/signal half -- accepted by the revision-1 challenge review, unchanged)

Two Minion-only extension points are involved: the `AGENT_STATUS` EMIT event and the `on_status_
change` callback, both invoked synchronously from inside `AgentInstance.set_status`. Pi gives no
guidance on what should happen if either throws, because Pi has no equivalent hook. The policy
below is derived from the ONE thing Pi's own structure DOES establish unambiguously: `isStreaming
= true` (RUNNING's own Pi analogue) is written BEFORE Pi's own try/executor begins -- i.e., before
ANY of the run's own observable event stream, including `agent_start`, exists at all -- while
`finishRun()` (IDLE's own Pi analogue) runs AFTER the run's own observable outcome (success,
`error`, or `aborted`) has already been fully committed and dispatched. The two transitions are
NOT symmetric in Pi's own architecture, and the policy below treats them accordingly, rather than
picking one uniform rule for both.

**RUNNING-transition observer failure: the run never validly started.** If `set_status(AgentStatus
.RUNNING)` raises (an `AGENT_STATUS` EMIT listener or `on_status_change` throwing), NO run has
observably begun in Pi's own terms -- Pi's own `isStreaming=true` equivalent write is exactly the
first thing Pi does, unconditionally, before anything else; a Minion-only hook failing at that
SAME point means the closest Pi-faithful interpretation is "this attempt to enter a run failed
before entering one," not "a run started and then failed." Concretely:

- the newly-created `RunAbortController` is discarded (the signal that was briefly live is never
  observed by any consumer other than the failing notification itself);
- `status` is forced back to `AgentStatus.IDLE` directly -- NOT by calling `set_status` again
  (which would re-invoke the SAME listener chain that just failed, and could fail identically a
  second time, an infinite-rollback hazard the PASS-4 review's own "how rollback itself avoids
  recursively failing transition notification" question names explicitly) -- via a NEW internal-
  only method, `AgentInstance._force_idle_after_failed_entry_notification()`, that sets `self.
  _status = AgentStatus.IDLE` directly with NO `AGENT_STATUS` emit and NO `on_status_change` call;
  callable only from `AgentLoop._run_wrapped`'s own rollback path, the same "Layer 07 owns
  vocabulary, Layer 08 owns per-run lifecycle" split `_start_run_signal`/`_end_run_signal` already
  established (`AG-007`);
- NO `agent_start`, NO synthesized failure turn, NO `message_start`/`message_end`/`turn_end`/
  `agent_end` sequence is produced -- `_settle_run_failure` is Pi's own `handleRunFailure`, which
  Pi invokes only from INSIDE its own try/executor, i.e., only once a run has genuinely begun;
  calling it here would fabricate a run that, per the reasoning above, never began;
- the observer's own original exception propagates DIRECTLY out of `prompt()`/`continue_()`/
  `run_until_idle()` to the caller, unconverted and unswallowed -- the caller's own attempt to
  start a run failed with the caller's own extension's own exception, exactly as it would if the
  caller's own code had thrown synchronously before calling `prompt()` at all;
- a subsequent `prompt()`/`continue_()` call succeeds normally (the guard sees `status is IDLE`),
  matching pinned Pi's own "a run that never touched `activeRun` leaves no trace" -- the PASS-4
  review's own observed defect ("second prompt = `AgentActiveError`" forever) is the exact
  regression this closes.

**IDLE-transition observer failure: the run's own already-committed outcome stands; only the
notification itself fails, separately.** By the time `set_status(AgentStatus.IDLE)` runs (in
`_run_wrapped`'s `finally`), the run's own observable outcome -- success or a `_settle_run_
failure`-settled failure/abort -- has ALREADY been fully dispatched and appended to the log; Pi's
own `finishRun()` runs in exactly this position too, after `handleRunFailure` has already
completed if it ran at all. That committed outcome must not be retroactively undone or hidden by a
LATER, unrelated notification failure. Concretely, every other exit-time state write is completed
UNCONDITIONALLY before the (possibly-throwing) IDLE publish, by making it the LAST statement in
`finally` rather than the first:

```text
finally:
    self.instance._end_run_signal()              # signal cleared -- unconditional
    self.instance.streaming_message = None        # unconditional
    self.instance.pending_tool_calls = frozenset()  # unconditional
    self.instance.set_status(AgentStatus.IDLE)     # LAST -- may raise
```

`set_status`'s own existing internal order (`self._status = status` BEFORE the `AGENT_STATUS`
emit/`on_status_change` call, already true today, unchanged) means `status` itself is ALSO already
internally `IDLE` by the time a throwing listener's exception propagates. So if the IDLE
notification throws, `signal`/`streaming_message`/`pending_tool_calls`/`status` are ALL already
fully consistent with a normally-settled idle instance the instant the exception is observed by a
caller -- only the notification's own side effect (whatever the failing listener was trying to do)
did not complete. The exception then propagates OUT of `_run_wrapped`/`prompt()`/`continue_()`
uncaught -- it is NOT swallowed, and it is NOT converted into a second, synthetic failure turn
(the run's own real outcome was already committed through its own correct path; fabricating a
second one would misrepresent what actually happened). This matches Pi's own precedent that a
listener failure DURING settlement propagates uncaught rather than being silently absorbed
(`_settle_run_failure`'s own docstring, `L08-R002`: "a listener invoked during this very recovery
sequence itself throws... the exception propagates uncaught").

**Ordering/short-circuit across `AGENT_STATUS` listeners and `on_status_change`:** unchanged,
already correct, no new code needed. `EventBus.emit` (`runtime/events.py:122-125`) is a plain `for
callback in chain: callback(*args)` loop with no internal try/except -- a throwing listener
propagates immediately, so (a) any LATER `AGENT_STATUS` listener in registration order never runs,
and (b) `on_status_change` (called by `set_status` only after `emit` returns without raising) never
runs either. This is the SAME fail-fast semantics every other `EMIT` event in this codebase already
has; Layer 09 does not need to special-case it.

## Preclaimed inbox input (RUNNING-failure entry rollback) -- new in revision 2

**Finding this section closes:** the revision-1 challenge review's own blocking finding --
`CONTRACT_ASSURANCE_DEFECT` within `L09-R007` -- "RUNNING-entry rollback omits already-claimed
inbox inputs." Revision 1's own RUNNING-failure policy above correctly restores `status`/`signal`,
but says nothing about the entering messages `continue_()`/`run_until_idle()` already destructively
removed from `Inbox` before ever calling `_run_wrapped`. The reviewer's own executable witness
(steer one envelope, install a throwing `on_status_change`, call `continue_()`) confirmed the
current candidate loses it: `NEXT_STEP pending 0`, `claimed ID present false`, no run occurred at
all. This directly contradicts revision 1's OWN "the run never validly started" framing: a caller's
queued input silently vanishing is an externally observable effect no less real than a stuck
`RUNNING` status or a leaked signal, and revision 1 left it entirely ungoverned.

**Observable rule.** Consistent with, and a direct consequence of, "the run never validly started"
(if no run began, `continue_()`/`run_until_idle()` must leave the world as if they had never been
called, for every piece of state they touch, not only `status`/`signal`):

```text
RUNNING notification fails after Inbox.claim() has already removed entering envelopes
    -> no claimed envelope is lost or duplicated
    -> each restored envelope's own id/message/origin are exactly the values that were claimed
    -> restored envelopes precede any input the failing observer itself enqueued at the same
       target during its own (failing) execution -- FIFO order is preserved as if the failed
       claim had never happened
    -> the inbox's own wake/pending state is coherent for a later caller (unaffected beyond the
       restoration itself -- claim() never touches wake, so restoration does not need to either)
    -> a subsequent claim at the same target observes the restored envelope(s) exactly once,
       with the same identity, not a copy
```

This rule applies to every call site that claims before entering `_run_wrapped`: `continue_()`'s
own steering branch, `continue_()`'s own follow-up branch, and `run_until_idle()`'s own follow-up
claim -- under BOTH `ClaimPolicy.ONE_AT_A_TIME` and `ClaimPolicy.ALL`. `prompt()` is NOT affected:
it never claims from `Inbox` at all (its entering message is the caller's own direct argument), so
it has nothing to restore.

**Mechanism is deliberately unspecified here**, per the reviewer's own instruction: the shared
contract states the observable result, not the implementation. Two mechanisms were confirmed
viable during this challenge (neither prescribed): (a) delay the destructive claim until AFTER the
RUNNING notification has succeeded, or (b) claim as today but retain the exact claimed envelopes
and prepend them back to the front of the target queue on rollback. Both satisfy the rule above
identically from an external caller's own point of view; the Python implementation pass chooses
one.

**Rust implementability confirmed**, matching the reviewer's own note: Rust can equally delay
ownership transfer of the claimed batch until run entry commits, or retain an owned batch and
restore it on entry failure. The `Inbox`/queue remains the sole authority over ordering either way;
no lower-layer semantic reopen is indicated (`AG-011`'s own already-certified queue-identity/
storage/ordering rules are read, not rewritten, by this addition).

## Behavior matrix (refined, supersedes the PASS-4 review's own table for the two `fail` rows)

| Transition observer behavior | Required observable outcome |
|---|---|
| no observer | one fresh signal for the whole run; `None` afterward (unchanged, already passing) |
| RUNNING observer returns | sees live signal (unchanged, already passing) |
| RUNNING observer calls `abort()` and returns | same request's signal is aborted (unchanged, already passing) |
| IDLE observer returns | sees `None` (unchanged, already passing) |
| RUNNING `on_status_change` throws | signal discarded, `status` forced to `IDLE` directly (no re-emit), no `agent_start`/no settled turn, the observer's own exception propagates out of `prompt()`, a subsequent `prompt()` succeeds |
| RUNNING `AGENT_STATUS` emit listener throws | identical outcome to the row above -- `on_status_change` never reached, matching `EventBus.emit`'s own existing fail-fast rule |
| IDLE `on_status_change` throws | the run's own already-committed outcome (success or settled failure/abort) is unaffected; `signal`/`streaming_message`/`pending_tool_calls`/`status` are already fully IDLE-consistent; the observer's own exception propagates out of `prompt()`/`continue_()` uncaught |
| IDLE `AGENT_STATUS` emit listener throws | identical outcome to the row above |

## Minimal executable witnesses (new, in addition to the already-passing happy-path witness)

1. `on_status_change` raises on RUNNING: assert the raised exception propagates from `prompt()`;
   assert `instance.status is AgentStatus.IDLE` and `instance.signal is None` immediately after;
   assert a SECOND `prompt()` call succeeds normally (does not raise `AgentActiveError`).
2. A synchronous `AGENT_STATUS` EMIT listener raises on RUNNING (registered via `ctx.events.on
   (AGENT_STATUS, ...)`, not `on_status_change`): same three assertions as (1), plus assert a
   SEPARATE `on_status_change` callback registered on the same instance was never invoked (proving
   the emit-listener failure short-circuited before reaching it).
3. `on_status_change` raises on IDLE, for a run that otherwise completed successfully: assert the
   raised exception propagates from `prompt()`; assert `instance.signal is None`, `instance.
   streaming_message is None`, `instance.pending_tool_calls == frozenset()`, and `instance.status
   is AgentStatus.IDLE` all hold DESPITE the propagating exception; assert the run's own successful
   assistant message IS present in `instance.messages` (the committed outcome was not undone).
4. `on_status_change` raises on IDLE, for a run that settled as a failure via `_settle_run_
   failure`: same state assertions as (3), plus assert the settled failure message IS present in
   `instance.messages` (proving a real run failure and a subsequent notification failure are not
   conflated or duplicated).

**New in revision 2 -- preclaimed-input restoration:**

5. `continue_()` on an assistant-last transcript with one queued steering envelope `A`
   (`ClaimPolicy.ONE_AT_A_TIME`); `on_status_change` raises on RUNNING. Afterward: assert `A`'s own
   `id`/`message`/`origin` are all still present, unchanged, in `inbox.pending(InboxTarget.
   NEXT_STEP)`; assert no lifecycle/provider work occurred (matching witness 1's own assertions);
   assert a SECOND `continue_()` call consumes `A` exactly once (not duplicated, not lost).
6. Identical to (5) but for the follow-up queue (`InboxTarget.NEXT_TURN`) -- `continue_()`'s own
   second branch.
7. `ClaimPolicy.ALL`, queue already holds `A, B`; `on_status_change` itself enqueues `C` (via
   `instance.inbox.steer(...)`/`.followup(...)`, matching the same target) and THEN raises.
   Afterward: assert the target queue reads exactly `A, B, C`, in that order -- proving restoration
   PREPENDS the claimed batch ahead of anything the failing observer itself added, rather than
   appending behind it or losing `C`.
8. `run_until_idle()` with one queued follow-up `A`; `on_status_change` raises on RUNNING during
   the pump's own first (and only) claimed batch. Afterward: assert `A` is still pending at
   `InboxTarget.NEXT_TURN` with its own original identity; assert the raised exception propagates
   out of `run_until_idle()` itself (the pump's own `while` loop must not swallow it or silently
   retry); assert a LATER, separate `run_until_idle()` call successfully drains and processes `A`.

Each witness must be verified genuinely discriminating via this project's own established
revert-and-confirm discipline before being trusted.

## Normative deltas required

- `spec/agent.md`: a new "Status-observer failure atomicity" subsection (near the existing
  "Signal/status transition ordering (`L09-R007`)" note this convergence refines), stating the
  RUNNING-rollback / IDLE-propagate-after-commit policy above AND the preclaimed-inbox-input
  observable rule (new in revision 2) as the normative rule.
- `pi-parity-manifest.yaml`, `AG-007`: a PASS-5 paragraph recording this convergence's own decided
  policy, all eight witnesses, and closing `L09-R007` for real this time -- superseding, not
  deleting, the PASS-3/PASS-4 paragraphs' own incomplete attempts (this project's established
  preserve-history convention).
- `pi-parity-manifest.yaml`, `AG-011` (queue identity/storage/ordering, new in revision 2): a
  cross-reference note only -- the preclaimed-input restoration rule reads `AG-011`'s own already-
  certified `InputEnvelope` identity/FIFO-ordering rules, it does not change them; whatever `Inbox`
  method the implementation pass adds must preserve them exactly.
- No `TOOL-024`/`AG-023`/`AI-027` changes -- this finding is entirely within `AG-007`'s/`AG-011`'s
  own territory, untouched elsewhere.
- No canonical scenario -- matching every other Layer-09 finding this cycle, the existing canonical
  placeholders remain unfilled and undisclosed-as-evidence; Python-level explicit-language
  regression tests are the load-bearing acceptance evidence, the same standard already accepted
  throughout this layer.

## Rust implementability

Confirmed idiomatic for both the entry-rollback and exit-propagate-after-commit halves. Revision-2
correction (documentary precision only, per the revision-1 challenge review): the failing RUNNING
observer IS explicitly allowed to observe and even abort the live signal before it throws -- the
signal is not hidden from the type system during entry. The actual guarantee is narrower and
correct as stated: the signal is DISCARDED (not retained, not handed to any consumer other than the
failing notification itself) before control returns to the caller of `prompt()`/`continue_()`. A
scoped RAII guard can install the run's signal/controller on construction and, on an early
`Result::Err`/panic-unwind from a synchronous status-notification callback during entry, drop the
guard on that unwind path -- Rust's own ownership model makes "this attempt never became a
real, observable run" a natural fit, not a workaround, PROVIDED the guard's own `Drop` correctly
discards rather than leaks the controller it held. For exit, completing every other state write
before the (possibly-fallible) notification call, then propagating that notification's own
`Result::Err`/panic after the fact, is equally idiomatic and requires no lower-layer reopen. The
preclaimed-input restoration rule is likewise Rust-idiomatic -- see "Preclaimed inbox input" above.

## Out of scope / deferred

- forced task cancellation, provider transport abort (`PROV-004`), tool batch/preflight changes,
  Layer 10, Rust implementation -- unchanged from the PASS-4 review's own scope statement.
- `L09-R008`/`L09-R009` -- `PROVISIONALLY CLOSED`, not reopened, not re-touched.
- Async/awaitable `on_status_change` callbacks -- out of scope because the callable's own declared
  type (`Callable[[AgentStatus], None]`) is synchronous-only; broadening it to `Awaitable` would be
  a separate, unrelated API change this convergence does not propose.
- An observer that enqueues a NEW message at a DIFFERENT target than the one being restored (e.g.
  the RUNNING observer that failed a steering-claim restore instead calls `.followup(...)`) --
  witness 7 above covers only the same-target case the reviewer's own required list named;
  different-target ordering is unconstrained by this convergence (the two targets already have
  independent FIFOs with no cross-target ordering rule anywhere in this layer).
- IDLE-transition preclaimed-input interaction -- N/A: by the time IDLE publishes, any claimed
  input for THAT run has already been consumed by the run's own turns (or the run never claimed
  input its own IDLE-time state depends on); this section's rollback rule is RUNNING-only, matching
  where the reviewer's own witness and required semantic decision were both scoped.

```text
CONVERGENCE CONTRACT
    PROPOSED -- AWAITING INDEPENDENT AGREEMENT (revision 2)

OPEN FINDINGS
    L09-R007

ACCEPTANCE WITNESSES
    tests/agent_loop/test_active_abort.py (eight new tests total -- four status/signal witnesses
    unchanged from revision 1, plus four new preclaimed-inbox-input witnesses above; none yet
    written -- this is a contract/evidence checkpoint, not an implementation pass)

NORMATIVE DELTAS
    minion-agent-docs/spec/agent.md (new "Status-observer failure atomicity" subsection, covering
      both the status/signal policy and the preclaimed-inbox-input rule)
    minion-agent/pi-parity-manifest.yaml, AG-007 (PASS-5 paragraph)
    minion-agent/pi-parity-manifest.yaml, AG-011 (cross-reference note only, new in revision 2)

NEXT_OWNER
    Codex
```
