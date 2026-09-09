# Layer 09 — L09-R012/R013/R014 contract convergence (run-entry input reservation)

**Revision 2, NOT yet approved.** Revision 1 (this same file) was independently challenged
(`assurance/layers/09-active-abort-r012-convergence-challenge.md`, docs PR #34, review commit
`190cf12c32d58314f607e69b8d789703683eee06`): **CONVERGENCE CONTRACT — CHANGES REQUIRED**. The
reviewer accepted the trigger determination, the peek-then-commit root-cause diagnosis, the
claim-before-observer direction, all four interleaving scenarios, the `AGENT_PRE_STEP` expansion,
and the `L09-R016` cleanup -- but found two challenge findings:

- **C09-1**: revision 1's own `_restore_claimed(target, envelopes)` still took `envelopes` as a
  caller-supplied PARAMETER and had no one-shot guard -- a leading underscore does not
  structurally prevent an arbitrary caller from invoking it with a foreign envelope tuple, or
  calling it twice to manufacture a duplicate. This is materially the same authority defect
  `L09-R010` rejected, not closed by renaming alone. Revision 2 replaces it with a genuine
  claim-bound, one-shot reservation object -- see "Proposed design" below.
- **C09-2**: revision 1's own correction to the `L09-R015` Pi citation was itself wrong -- it read
  only the LOW-LEVEL `agent-loop.ts::AgentLoopConfig.prepareNextTurn(context)` shape and missed
  the PUBLIC `Agent.createLoopConfig()`'s own wrapping, which explicitly supplies `this.signal`
  to the application-facing `AgentOptions.prepareNextTurn(signal)`/`prepareNextTurnWithContext
  (context, signal)` callbacks. Re-verified directly against pinned Pi below -- the reviewer's
  correction is right, and revision 1's own "correction" is retracted.

**Trigger check (mandatory, `process/agent-workflow.md` §11.8):**

- `L09-R012` (AG-011's own manifest rule contradicts the implemented commit mechanism): found by
  the PASS-6 targeted review, "fixed" in PASS 7 (the `python:` pointer only -- the `rule:` prose
  itself was never actually corrected, an oversight this convergence corrects), found STILL OPEN
  by this final §11.8.8 review. **Two independent reviews on this exact finding ID -> the "same
  material finding survives two independent reviews" trigger is MET.**
- `L09-R013`/`L09-R014`: new finding IDs, one rejection each so far -- below the per-ID threshold
  in isolation. However, both are the LATEST entries in a single continuous lineage on the exact
  same mechanism: `L09-R007` (status/signal entry-failure atomicity, PASS 4/5) -> `L09-R010`
  (the PASS-5 mechanism's own unrestricted public authority) -> `L09-R011` (the PASS-6
  replacement mechanism's own count-only over-deletion) -> `L09-R013`/`L09-R014` (the PASS-7
  replacement mechanism's own loss-on-throw and partial-prefix duplication). Four consecutive
  implementation passes on the SAME "how does a run-entry attempt reserve `Inbox` input across a
  synchronous, re-entrant RUNNING-notification observer" question, each closing the exact prior
  witness while leaving (or introducing) an adjacent gap in the same mechanism. This is precisely
  "a tightly-coupled semantic surface" `§11.8`'s own text names as grounds to enter convergence
  even before a strict two-repeat trigger fires on one specific ID -- and here `L09-R012`'s own
  independent two-repeat trigger has ALSO already fired, on a row describing this exact mechanism.

**Determination:** enter `CONTRACT_CONVERGENCE` for the combined run-entry input reservation
surface (`L09-R012`/`L09-R013`/`L09-R014`). This is a `§11.8.3` characterization pass building
directly on the final review's own rich characterization (exact witnesses, required language-
neutral invariants already stated in `assurance/layers/09-active-abort-rust-final-contract-
review-pass7.md`), followed by my own `§11.8.4`-equivalent challenge/design pass, proposed here
for Codex's own independent agreement. No implementation in this artifact.

`L09-R015`/`L09-R016` are bundled into this SAME checkpoint for coordination efficiency -- they do
not independently meet either convergence trigger and their own remediations are narrow and
already well-specified (matching an established, twice-accepted pattern for `L09-R015`; purely
documentary for `L09-R016`) -- but per `§11.8.1`'s own "freeze unrelated implementation work"
during convergence, no code changes are made until this WHOLE checkpoint is agreed, so all five
findings are implemented together in one coherent pass afterward.

## Exact state under convergence

- code PR: `EGAILab/minion-agent#17`, exact head: `ef23829a9a7acf4033df7a9186a810c41433ad64`
- docs PR: `EGAILab/minion-agent-docs#26`, exact head: `633f6a82822e82705a5fe956dad28bd4c0ce4acb`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- `L09-C001`-`C003`, `L09-R001`-`R009`: `CLOSED`, unaffected, not reopened by this convergence.

## Challenge pass over the final review's own findings

**Is the Pi source mapping correct?**

For `L09-R012`/`R013`/`R014`: re-confirmed (again) directly against pinned Pi (`ref-repos/pi` @
`b7bb00b`, `agent.ts:361-388`, `agent-loop.ts` steering-queue drain call sites, `agent.ts:125-159`
`PendingMessageQueue`). Pi has NO reentrancy hazard of this kind at all: `PendingMessageQueue.
drain()` is called ONCE, synchronously, with no notification point between selection and removal
that application code could hook into -- Pi's own equivalent of "claim, then maybe fail" is a
single atomic JS statement. This remains a purely Minion-owned architectural-integrity question,
not a Pi-parity question, exactly as established for the original `L09-R007` convergence.

For `L09-R015` (revised under C09-2 -- revision 1's own "correction" here was itself wrong, and
is retracted): re-audited pinned Pi a second time, this time including the layer revision 1
missed. `agent-loop.ts`'s own low-level `AgentLoopConfig.prepareNextTurn(context)` shape indeed
carries no `signal` parameter at its OWN level -- that part of revision 1's reading was accurate
as far as it went. But that low-level shape is not what an application actually supplies: pinned
Pi's own PUBLIC `Agent` class (`agent.ts`) defines its own, higher-level `AgentOptions.
prepareNextTurn?: (signal?: AbortSignal) => ...` and `AgentOptions.prepareNextTurnWithContext?:
(context: PrepareNextTurnContext, signal?: AbortSignal) => ...` (`agent.ts:109-115`, mirrored as
public `Agent` fields at `agent.ts:197-200`, assigned from `runtimeOptions` in the constructor at
`agent.ts:229-230`) -- BOTH of which explicitly accept `signal` as their own parameter. `Agent.
createLoopConfig()` (`agent.ts:445-471`) is what actually WRAPS these into the low-level shape
`agent-loop.ts` consumes:

```text
prepareNextTurn:
    this.prepareNextTurnWithContext || this.prepareNextTurn
        ? async (context) => {
                if (this.prepareNextTurnWithContext) {
                    return await this.prepareNextTurnWithContext(context, this.signal);
                }
                return await this.prepareNextTurn?.(this.signal);
            }
        : undefined,
```

`this.signal` -- the SAME live Agent signal every other consumer receives -- is threaded explicitly
into the wrapped callback at exactly this point. (The identical pattern, confirmed at the same
read, also applies to `shouldStopAfterTurn`: `AgentOptions.shouldStopAfterTurn?: (context, signal?)
=> ...`, wrapped at `agent.ts:460-462` as `async (context) => await shouldStopAfterTurn(context,
this.signal)` -- reinforcing, not merely paralleling, that `AGENT_TURN_STOPPING`'s own existing
`instance.signal` consumer-matrix entry is correct today and needs no revision, independent of its
own separate immunity to redirection via `.serial()`'s own non-delegating dispatch, established
below.)

So the ORIGINAL final review's own citation was accurate, and revision 1's own attempted
correction was wrong because it inspected only the internal `agent-loop.ts` layer and never
followed the wrapping up to the public `Agent` class that actually supplies these callbacks to
application code. Pi genuinely DOES supply `this.signal` explicitly to `prepareNextTurn`/
`prepareNextTurnWithContext` (and `shouldStopAfterTurn`) -- `instance.signal` is Minion's own
faithful mapping of that same capability (through `instance`, the established convention for
these listeners, rather than a bespoke explicit parameter), not a Minion-added extension beyond
Pi. Pi has exactly ONE such callback (no listener chain), so Pi itself has no "one listener
redirects a later one" hazard to violate -- but the VALUE Pi threads there (the Agent's own live,
stable signal) is unambiguously a genuine Pi-parity guarantee, and Minion's own N-listener
waterfall extension of that single callback (an intentional, disclosed Minion architectural
choice, unchanged by this correction) must preserve it at every listener handoff. The
classification (`PI_PARITY_DEFECT`) stands, now on the CORRECT citation.

**Is `AGENT_TURN_STOPPING` also vulnerable?** No -- re-confirmed by inspecting its own dispatch
(`driver.py::_should_stop`, `ctx.events.serial(...)`) against `EventBus.serial`'s own
implementation (`runtime/events.py`): `serial` is a plain fan-out (`for callback in chain: ...`)
with NO `next`/delegation concept at all -- every listener receives the IDENTICAL arguments the
caller originally supplied, structurally incapable of the redirect this finding describes. Only
`.waterfall()`-dispatched events, where a listener can call `next(*replacement)`, have this hazard
at all.

**Is the audit of every waterfall dispatch complete?** The review's own witness covered only
`AGENT_PREPARE_NEXT_TURN`. A full audit of every `.waterfall()` call site in the codebase (five
total: `grep -rn "\.waterfall(" src/`) found ONE MORE with the identical unprotected-`instance`
shape the review did not test: `driver.py::_pre_step`, dispatching `AGENT_PRE_STEP` with
`(self.instance, reason, messages, next_)` and no `normalize_step` at all. Left unfixed, this
would be exactly the kind of "adjacent surface of the same mechanism" this project's own PASS-7
retrospective note already named as a recurring failure mode. It is included in this convergence's
own remediation, not left for a future review to separately discover.

The other two waterfall dispatches (`AGENT_TRANSFORM_CONTEXT`, `TOOLS_PRE_EXECUTE`/
`TOOLS_POST_EXECUTE`) already carry `normalize_step` protection for `instance`/identity fields
from the `L09-R006` remediation and are unaffected by this convergence.

**Does any proposed fix silently reopen a lower certified layer?** No. `AG-011`'s own certified
`InputEnvelope` identity/FIFO-ordering rules and `AG-012`'s own certified `ClaimPolicy` selection
semantics are read and preserved exactly by the proposed design below, not rewritten. `AG-008`'s
own certified `set_status`/`streaming_message`/`error_message`/`pending_tool_calls` write order is
untouched.

## Root-cause reassessment: peek-then-commit was the wrong turn

PASS 6 replaced PASS 5's "claim eagerly, restore on failure" design with "peek (read-only), commit
destructively only once `set_status(RUNNING)` succeeds" -- motivated entirely by `L09-R010`'s own
finding that PASS 5's own `restore()` was an unrestricted PUBLIC method. But `L09-R010`'s own
required remediation never actually demanded abandoning claim-then-rollback; it demanded fixing
`restore()`'s own AUTHORITY (`"An internal claim-plus-private-rollback design... is acceptable"`,
the L09-R010 review's own words). Choosing peek-then-commit instead introduced a NEW hazard
claim-then-rollback never had: a real, synchronous re-entrancy WINDOW between selection (`peek`)
and removal (`commit`), during which the observer has full, undefended access to the exact
envelopes this run had already decided to use. Two more passes (`L09-R011`, then `L09-R013`/
`L09-R014`) each closed one shape of exploit through that window while leaving or creating another
-- because the window itself, not any specific check within it, is the actual defect.

**Reverting to claim-then-private-rollback removes the window entirely** (verified against all
four required scenarios below, including the two the final review's own witnesses target):

- entering input is claimed (destructively, immediately, unconditionally) BEFORE `set_status
  (RUNNING)` is ever called -- exactly matching pinned Pi's own pre-drain-then-`runWithLifecycle`
  shape, with NO gap between selection and removal for anything to observe or race;
- a re-entrant observer's own `Inbox.claim()`/`clear()`/`send()`-family calls therefore operate on
  the ALREADY-REDUCED queue (the entering batch is already gone, held by the pending run-entry
  attempt) -- the observer literally cannot see or touch the entering batch at all, eliminating
  the entire "partial-prefix"/"unrelated deletion" class of defect by construction, not by
  case-by-case checking;
- on a RUNNING-notification failure, a private, linear `_Reservation.rollback()` -- bound 1:1 at
  construction to the exact envelopes THIS SAME `_reserve()` call's own `claim()` produced, never
  independently constructible or invokable with arbitrary envelopes by an arbitrary caller, and
  callable at most once (closing `L09-R010` AND `C09-1` by construction: no parameter through
  which to substitute envelopes, no way to invoke it twice) -- puts them back at the front, ahead
  of anything the observer itself enqueued in the meantime (preserving the original `L09-R007`
  FIFO-precedence requirement).

### Verification against all four required scenarios

```text
1. RUNNING observer does nothing, returns normally
   -> claimed batch already removed; run proceeds with it; nothing further needed. PASS.

2. RUNNING observer itself claims the SAME batch (or part of it) and returns normally
   -> IMPOSSIBLE by construction: the batch is already gone from the queue before the observer
      runs, so its own claim() call can only ever see genuinely different, unrelated input.

3. RUNNING observer claims some of the batch and THEN THROWS (`L09-R013`'s own witness)
   -> IMPOSSIBLE by construction, same reason: there is nothing left in the queue for the
      observer's own claim() to find that belongs to this run's own entering batch. Rollback
      restores the WHOLE original batch, in order, regardless of what the observer did or didn't
      do to the (already-reduced) queue -- A is retained, matching the review's own required
      "A_retained = true."

4. RUNNING observer clears the target and enqueues new input, then throws or returns
   -> the clear() is a no-op against the (already-empty, for the claimed portion) queue; new
      input the observer enqueues is untouched either way. On success, the run proceeds with its
      own original entering batch and the observer's new input remains queued, unconfused with
      it. On failure, rollback prepends the original batch ahead of the observer's own new input
      -- exactly the `L09-R007`-established FIFO-precedence rule.
```

### Behavior matrix required for agreement (the reviewer's own table, adopted verbatim)

| Surface | Observer behavior | Entry outcome | Required queue result |
|---|---|---|---|
| Reserved A,B | no mutation, returns | success | A,B admitted once; absent from queue |
| Reserved A,B | claims same target, returns | success | observer can see only later/unrelated input; A,B admitted once |
| Reserved A,B | claims same target, throws | failure | A,B restored once in original order; observer-consumed unrelated input is not fabricated |
| Reserved A,B | clear + enqueue C, returns | success | A,B admitted once; C remains according to observer mutation |
| Reserved A,B | clear + enqueue C, throws | failure | A,B restored once ahead of C; no duplicate |
| Any reservation | rollback invoked twice | failure path | second terminal action is inert/rejected; no duplicate |
| Any reservation | caller offers foreign envelope | any | foreign envelope cannot enter through rollback |
| Prepare/pre-step waterfall | first listener redirects/drops instance | success | later listener sees original Agent and authoritative run signal |

Scenario 2 is the exact shape `L09-R013`'s own witness constructs (queue `A,B`; `ALL` claims both
immediately; the observer's own subsequent `claim(ONE_AT_A_TIME)` on the now-empty relevant
portion of the queue cannot obtain `A` at all) and `L09-R014`'s own witness (there is no partial-
prefix state to be in at all, since the ENTIRE batch is removed atomically in one operation before
the observer ever runs) -- both are closed by the SAME structural change, not by two separate
patches.

## Proposed design (revised under C09-1)

Revision 1's own `_restore_claimed(target, envelopes)` took `envelopes` as a caller-supplied
parameter and had no one-shot guard -- structurally the SAME shape of authority defect as the
removed public `restore()` (`L09-R010`), merely renamed and made conventionally-private, not
actually closed. Revision 2 makes rollback a genuine linear, claim-bound CAPABILITY rather than a
general-purpose Inbox operation, matching the reviewer's own required shape exactly:

**`Inbox` (`agent/inbox.py`):** remove `peek()` and `_commit_claim` (PASS 6's own now-superseded
methods). Add a private reservation type and a private constructor for it:

```text
Inbox._reserve(target, policy) -> _Reservation   [PRIVATE, Layer 08 only]
    Atomically claim()s the entering batch and returns a fresh, single-use _Reservation bound to
    it. Not part of the public API.

_Reservation   [PRIVATE class -- never independently constructible by external code; the ONLY
                way to obtain one is Inbox._reserve()]
    .envelopes -> tuple[InputEnvelope, ...]   [read-only; exactly what _reserve()'s own claim()
                                                call removed -- never caller-suppliable]
    .commit() -> None      [terminal; may be called AT MOST ONCE, and only if .rollback() has not
                             already been called; leaves the claimed envelopes removed (a no-op,
                             since claim() already removed them) and marks the reservation settled]
    .rollback() -> None    [terminal; may be called AT MOST ONCE, and only if .commit() has not
                             already been called; prepends `.envelopes` back to `target`, ahead of
                             whatever is queued there now, and marks the reservation settled]
```

Neither `.commit()` nor `.rollback()` accepts ANY argument -- there is no parameter through which
a caller could substitute foreign envelopes, closing that half of C09-1 by the absence of a
parameter, not by convention. A private `_settled` flag, checked and set at the START of both
methods, raises if either is called after the OTHER has already run, or a second time on itself --
closing the double-terminal-action half of C09-1 structurally, not by trusting callers to behave.
`_Reservation` itself is a private class (leading underscore, not exported from any public
surface); its sole constructor path is `Inbox._reserve()`, itself private -- an external caller
cannot obtain one AT ALL except by going through the one code path that binds it to a real,
just-executed `claim()` call.

`Inbox.claim()`/`Inbox.pending()`/every other already-certified public `Inbox` method: UNCHANGED
-- `claim()` remains the sole PUBLIC removal operation, exactly as the reviewer's own required
shape specifies.

**`AgentLoop` (`agent_loop/driver.py`):**

- `continue_()`'s steering/follow-up branches and `run_until_idle()`'s follow-up claim: call
  `Inbox._reserve()` (not `claim()`/`peek()` directly) and pass the resulting `_Reservation` to
  `_run_wrapped` via a new keyword-only `entry_reservation` parameter.
- `_run_wrapped`: on a RUNNING-notification failure, calls `entry_reservation.rollback()` (if an
  `entry_reservation` was supplied); on success, calls `entry_reservation.commit()` immediately
  after `set_status(RUNNING)` returns without raising, before proceeding to `_execute_run`. Exactly
  one of `.commit()`/`.rollback()` is ever called, on exactly one code path each, matching the
  reservation's own one-shot contract by construction (there is no third path through
  `_run_wrapped` that could call either twice or omit both).
- `_pre_step`: `AGENT_PRE_STEP`'s own waterfall dispatch gains a `normalize_step` closure
  restoring `self.instance` (only -- `reason`/`messages` remain intentionally listener-
  transformable, matching this event's own documented purpose and matching the narrow scope of
  this finding; no review has flagged either as needing protection, and expanding scope beyond
  the two authority-bearing fields this convergence actually examined is deliberately avoided).
- `_prepare_next_turn`: `AGENT_PREPARE_NEXT_TURN`'s own waterfall dispatch gains the identical
  `normalize_step` closure restoring `self.instance`.

**Explicit disposition of unrelated observer side effects (the reviewer's own required
clarification, stated normatively so Python and Rust cannot diverge):** only the entry
reservation's OWN claimed batch is ever rolled back on failure. Anything else a RUNNING observer
did to `Inbox` -- claiming genuinely different, unrelated input; clearing a target; enqueuing new
input -- is NOT reversed, regardless of whether the run-entry attempt itself succeeds or fails.
The reservation mechanism protects exactly one thing: that ITS OWN selected batch is never lost or
duplicated. It is not a general transaction over the whole `Inbox`.

**`spec/agent.md`/`spec/tools.md` (`L09-R016`):**

- `spec/tools.md`'s own Layer-05 prose ("the cancellation signal half remains open... Python has
  no AbortSignal-equivalent") is present-tense text describing a gap Layer 09 has since closed.
  Corrected to explicitly state the historical deferral and that Layer 09 (`RunSignal`) has since
  realized it -- preserving the historical statement's own accuracy AT THE TIME Layer 05 was
  certified, per this project's history-preservation convention, while making current status
  unambiguous, matching the same "CURRENT RULE/STATUS" pattern already used for `AG-007`/
  `TOOL-024` under `L09-R009`.
- `TOOL-009`'s own manifest wording: same correction.
- `tools/execute.py::_execute_and_finalize`'s own docstring still describes signal delivery only
  for a tool declaring "a fourth parameter," contradicting the already-implemented, already-
  certified `wants_signal`-based four-combination dispatch (`L09-R003`). Corrected to describe the
  actual current dispatch table.

## Required acceptance witnesses

Existing `L09-R007`/`L09-R010` witnesses (status/signal atomicity, no-public-restore, no-duplicate-
id): re-run unchanged against the new design; all must remain green, since the new design's own
happy-path and status/signal behavior is identical to PASS 5/6/7's own already-agreed contract --
only the queue-mutation mechanism changes.

New/replacing witnesses:

1. `L09-R013`'s own exact scenario, reproduced through the real driver: `ALL` claims `A,B`
   immediately; a RUNNING observer calls `claim(ONE_AT_A_TIME)` on the SAME target and then
   raises; assert `A` AND `B` are both retained (pending, in order) after rollback, and a later
   `continue_()` (observer removed) consumes them exactly once.
2. `L09-R014`'s own exact scenario: `ALL` claims `A,B` immediately; a RUNNING observer calls
   `claim(ONE_AT_A_TIME)` and returns normally (no throw); assert the run itself still proceeds
   with entering `(A, B)` (the batch it claimed, unaffected by the observer's own unrelated claim
   attempt finding nothing); assert the observer's own claim returned empty (nothing left for it
   to claim); a real-driver terminal-response witness (matching the review's own explicit request)
   so an ordinary post-turn poll cannot mask the result.
3. The existing PASS-6/7 `ONE_AT_A_TIME`-observer-claims / `ALL`-observer-clears-and-enqueues
   witnesses: re-verified under the new design (expected to hold trivially, per the "impossible by
   construction" analysis above, but re-run as permanent regression evidence, not merely asserted).
4. `AGENT_PRE_STEP`/`AGENT_PREPARE_NEXT_TURN` redirect/drop witnesses, matching the established
   `L09-R006` pattern exactly: a listener delegates with a forged `instance`-like replacement (or
   omits it); a later listener must observe the ORIGINAL instance, not the forgery.
5. `spec/tools.md`/`TOOL-009`/`_execute_and_finalize` docstring corrections: documentary only, no
   new witness required, matching `L09-R009`'s own precedent.

New in revision 2, per `C09-1`'s own required negative evidence (`Inbox`-level, direct):

6. Double rollback cannot duplicate an envelope: `reservation = inbox._reserve(...)`;
   `reservation.rollback()`; a second `reservation.rollback()` call raises (does not re-insert).
7. Rollback cannot restore a foreign envelope: confirm `_Reservation.rollback()`/`.commit()` accept
   no arguments at all (a structural, not merely behavioral, guarantee -- attempting to call either
   with an argument is a `TypeError` from Python's own function-signature enforcement, not a
   defect this project's own test suite needs to separately assert).
8. Commit-then-rollback and rollback-then-commit cannot mutate the queue a second time: for each
   ordering, call the first terminal method, then assert the second raises and the queue is
   unchanged by the second (rejected) call.

## Normative deltas required

- `minion-agent-docs/spec/agent.md`: correct the "Preclaimed inbox input" section's own mechanism
  description (claim-then-reservation-rollback, not peek-then-commit); add a citation note that
  pinned Pi's own `Agent.createLoopConfig()` wraps `prepareNextTurn`/`prepareNextTurnWithContext`/
  `shouldStopAfterTurn` with the Agent's own live `this.signal` (`agent.ts:445-471`), so `instance.
  signal` for `AGENT_PREPARE_NEXT_TURN`/`AGENT_TURN_STOPPING` is a faithful mapping of an existing
  Pi capability, not a Minion-added one (revision 1's own contrary claim here is retracted); add
  the `AGENT_PRE_STEP`/`AGENT_PREPARE_NEXT_TURN` authoritative-instance rule.
- `minion-agent-docs/spec/tools.md`: correct the stale Layer-05 signal-capability prose
  (`L09-R016`).
- `minion-agent/pi-parity-manifest.yaml`, `AG-007`: a PASS-8 paragraph recording this
  convergence's own decided design, superseding PASS 5/6/7's own peek/commit mechanism
  descriptions (preserved as historical record, not deleted).
- `minion-agent/pi-parity-manifest.yaml`, `AG-011`: `rule:` prose corrected to describe
  claim-then-private-rollback accurately (closing `L09-R012` for real -- this is the field the
  final review found still contradictory after PASS 7 only touched the `python:` pointer).
- `minion-agent/pi-parity-manifest.yaml`, `TOOL-009`: current-status correction (`L09-R016`).

## Rust implementability

Confirmed idiomatic, matching the final review's own "Existing Rust architecture feasibility"
section and the challenge's own C09-1 guidance: an owned `Reservation` value with `commit(self)`/
`rollback(self)` consuming methods (`self`, by value -- not `&self`) is a NATURAL fit for Rust's
own ownership model, and structurally STRONGER than Python's own guard-flag approach: Rust's own
move semantics make calling either method a SECOND time a compile-time error, not a runtime check
at all, since the value no longer exists after its first consuming call. No interior mutability or
lock is needed, since Rust's own borrow checker already prevents a re-entrant observer from
touching envelopes this attempt already owns. `AGENT_PRE_STEP`/`AGENT_PREPARE_NEXT_TURN`
instance-authority restoration uses the identical typed-middleware pattern already established and
accepted for `L09-R006`.

## Out of scope / deferred

- `reason` (`AGENT_PRE_STEP`) and `message`/`tool_results`/`context`/`new_messages`
  (`AGENT_PREPARE_NEXT_TURN`) remain intentionally listener-transformable -- not examined or
  restricted by this convergence, which is scoped to instance/signal authority only.
- Forced task cancellation, provider transport abort (`PROV-004`), tool batch/preflight changes,
  Layer 10, Rust implementation -- unchanged scope boundary from every prior Layer-09 pass.
- Async/awaitable `on_status_change` callbacks -- unchanged, out of scope (established under the
  original `L09-R007` convergence).

```text
CONVERGENCE CONTRACT
    PROPOSED -- AWAITING INDEPENDENT AGREEMENT (revision 2)

OPEN FINDINGS
    L09-R012
    L09-R013
    L09-R014
    L09-R015 (bundled, non-blocking -- narrow, already-specified fix)
    L09-R016 (bundled, non-blocking -- documentary only)

CHALLENGE FINDINGS ADDRESSED
    C09-1  rollback authority: replaced Inbox._restore_claimed(target, envelopes) with a private,
           linear _Reservation type (.commit()/.rollback(), no-argument, one-shot, obtainable
           only via private Inbox._reserve()) -- see "Proposed design"
    C09-2  L09-R015 Pi citation: retracted revision 1's own claim that prepareNextTurn carries no
           signal in Pi; Agent.createLoopConfig() wraps it (and shouldStopAfterTurn) with the
           Agent's own live this.signal -- see the revised L09-R015 section

ACCEPTANCE WITNESSES
    tests/agent/test_inbox.py (Inbox._reserve/_Reservation unit coverage -- claim binding,
      commit/rollback one-shot enforcement, double-terminal-action rejection -- replacing the
      removed peek/_commit_claim tests)
    tests/agent_loop/test_active_abort.py (L09-R013/R014 real-driver scenarios; AGENT_PRE_STEP/
      AGENT_PREPARE_NEXT_TURN redirect/drop witnesses)
    -- none yet written; this is a contract/evidence checkpoint, not an implementation pass

NORMATIVE DELTAS
    minion-agent-docs/spec/agent.md ("Preclaimed inbox input" mechanism correction to claim-then-
      reservation-rollback; corrected Pi citation for AGENT_PREPARE_NEXT_TURN/AGENT_TURN_STOPPING
      signal delivery; AGENT_PRE_STEP/AGENT_PREPARE_NEXT_TURN authority rule; explicit "unrelated
      observer side effects are not reversed" statement)
    minion-agent-docs/spec/tools.md (stale Layer-05 signal-capability prose, L09-R016)
    minion-agent/pi-parity-manifest.yaml, AG-007 (PASS-8 paragraph)
    minion-agent/pi-parity-manifest.yaml, AG-011 (rule: prose corrected -- closes L09-R012)
    minion-agent/pi-parity-manifest.yaml, TOOL-009 (current-status correction, L09-R016)

NEXT_OWNER
    Codex
```
