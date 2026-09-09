# Layer 09 — L09-R012/R013/R014 contract convergence (run-entry input reservation)

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

For `L09-R015`: **the review's own stated Pi-source justification is imprecise, corrected here.**
The review says "Pinned Pi wraps `prepareNextTurn` for one Agent and supplies that Agent's `this.
signal`." Re-audited directly against pinned Pi (`agent-loop.ts:226-232`, `types.ts:124-147`):
`prepareNextTurn`'s own context type, `PrepareNextTurnContext`, extends `ShouldStopAfterTurnContext`
-- `{ message, toolResults, context, newMessages }` -- and carries **NO `signal` field at all**.
`config.prepareNextTurn` is also a SINGLE, nullable, directly-invoked callback (`await config.
prepareNextTurn?.(nextTurnContext)`), not a listener chain of any kind -- Pi has no "one listener
redirects a later one" hazard here because Pi has no LATER listener to redirect: there is exactly
one callback, called once. Contrast pinned Pi's own `Agent.subscribe(listener: (event, signal) =>
...)` (`agent.ts:250`), which DOES thread `signal` explicitly as an argument -- confirming the
distinction spec/agent.md itself should have drawn (see "Required deltas" below): Pi threads
`signal` explicitly to `subscribe`-style listeners, but NOT to `prepareNextTurn`/
`shouldStopAfterTurn` at all. Minion's own choice to give `AGENT_PREPARE_NEXT_TURN`/`AGENT_
TURN_STOPPING` listeners `instance.signal` access (since they already receive `instance` as their
own first argument, an established Minion convention) is therefore a Minion-added CAPABILITY
beyond what Pi's own `prepareNextTurn`/`shouldStopAfterTurn` hooks receive, not a "mapping" of an
existing Pi capability to a different mechanism.

Despite that correction, the underlying integrity concern is independently valid on Minion's own
terms, and the classification (`PI_PARITY_DEFECT`) remains defensible under this project's own
established precedent: `L09-R006` classified the identical shape of defect (a Minion-only
waterfall extension of a Pi single-callback design failing to preserve a value's own required
single-identity-per-run guarantee) as `PI_PARITY_DEFECT`, reasoning that the VALUE under threat
(the same per-run signal reaching every consumer with stable identity) is a genuine Pi-parity
guarantee even where the SPECIFIC mechanism putting it at risk (an N-listener waterfall) is
Minion's own addition. `spec/agent.md`'s own already-certified consumer/settlement matrix already
LISTS `AGENT_PREPARE_NEXT_TURN`/`AGENT_TURN_STOPPING` listeners as signal consumers (via `instance.
signal`) -- having made that listing, Pi-parity requires the SAME stable identity every other
listed consumer receives. The classification stands; the stated Pi citation is corrected.

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
- on a RUNNING-notification failure, a PRIVATE rollback closure -- bound 1:1 to the exact
  envelopes THIS SAME claim() call returned, never independently constructible by an arbitrary
  caller with arbitrary envelopes (closing `L09-R010` the same way PASS 6 did: by construction, not
  convention alone) -- puts them back at the front, ahead of anything the observer itself enqueued
  in the meantime (preserving the original `L09-R007` FIFO-precedence requirement).

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

Scenario 2 is the exact shape `L09-R013`'s own witness constructs (queue `A,B`; `ALL` claims both
immediately; the observer's own subsequent `claim(ONE_AT_A_TIME)` on the now-empty relevant
portion of the queue cannot obtain `A` at all) and `L09-R014`'s own witness (there is no partial-
prefix state to be in at all, since the ENTIRE batch is removed atomically in one operation before
the observer ever runs) -- both are closed by the SAME structural change, not by two separate
patches.

## Proposed design

**`Inbox` (`agent/inbox.py`):** remove `peek()` (PASS 6's own now-superseded public method -- no
longer serves any purpose once destructive removal moves back to claim time) and `_commit_claim`
(same). Add:

```text
_restore_claimed(target, envelopes) -> None   [PRIVATE, Layer 08 only]
    prepend envelopes to target, ahead of whatever is queued there now.
    Not part of the public API. Called exactly once per failed run-entry attempt, with exactly
    the envelopes that SAME attempt's own prior claim() call returned -- never independently
    constructible or callable with arbitrary envelopes by an arbitrary caller (closes L09-R010
    the same way the removed peek/_commit_claim pair did: by construction).
```

`Inbox.claim()`/`Inbox.pending()`/every other already-certified `Inbox` method: UNCHANGED.

**`AgentLoop` (`agent_loop/driver.py`):**

- `continue_()`'s steering/follow-up branches and `run_until_idle()`'s follow-up claim: call
  `Inbox.claim()` (not `peek()`) as they did before PASS 6, and pass a NEW `rollback_entry_claim:
  Callable[[], None]` closure to `_run_wrapped` (replacing PASS 6/7's own `commit_entry_claim`),
  each closing over the exact claimed envelopes and calling `Inbox._restore_claimed` with them.
- `_run_wrapped`: the RUNNING-notification `except` branch calls `rollback_entry_claim()` (if
  supplied) instead of PASS 6/7's own `commit_entry_claim()` on the SUCCESS path -- there is no
  longer a separate "commit" step at all, since `claim()` already removed the input unconditionally
  before `set_status(RUNNING)` runs; success needs no further action.
- `_pre_step`: `AGENT_PRE_STEP`'s own waterfall dispatch gains a `normalize_step` closure
  restoring `self.instance` (only -- `reason`/`messages` remain intentionally listener-
  transformable, matching this event's own documented purpose and matching the narrow scope of
  this finding; no review has flagged either as needing protection, and expanding scope beyond
  the two authority-bearing fields this convergence actually examined is deliberately avoided).
- `_prepare_next_turn`: `AGENT_PREPARE_NEXT_TURN`'s own waterfall dispatch gains the identical
  `normalize_step` closure restoring `self.instance`.

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

## Normative deltas required

- `minion-agent-docs/spec/agent.md`: correct the "Preclaimed inbox input" section's own mechanism
  description (claim-then-rollback, not peek-then-commit); correct the `AGENT_LIFECYCLE_EVENT`/
  `AGENT_PREPARE_NEXT_TURN`/`AGENT_TURN_STOPPING` grouping to note only `subscribe`
  (`AGENT_LIFECYCLE_EVENT`) receives `signal` explicitly in Pi; add the `AGENT_PRE_STEP`/
  `AGENT_PREPARE_NEXT_TURN` authoritative-instance rule.
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
section: an owned, claimed batch with a `Drop`-based or explicit rollback method (no interior
mutability or lock needed, since Rust's own ownership model already prevents a re-entrant observer
from touching envelopes this attempt already owns) is a natural fit -- arguably MORE natural in
Rust than the Python peek/commit design ever was, since Rust's own borrow checker would have made
the reentrancy window this whole cluster is about considerably harder to introduce by accident in
the first place. `AGENT_PRE_STEP`/`AGENT_PREPARE_NEXT_TURN` instance-authority restoration uses the
identical typed-middleware pattern already established and accepted for `L09-R006`.

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
    PROPOSED -- AWAITING INDEPENDENT AGREEMENT

OPEN FINDINGS
    L09-R012
    L09-R013
    L09-R014
    L09-R015 (bundled, non-blocking -- narrow, already-specified fix)
    L09-R016 (bundled, non-blocking -- documentary only)

ACCEPTANCE WITNESSES
    tests/agent/test_inbox.py (Inbox.claim/_restore_claimed unit coverage, replacing the removed
      peek/_commit_claim tests)
    tests/agent_loop/test_active_abort.py (L09-R013/R014 real-driver scenarios; AGENT_PRE_STEP/
      AGENT_PREPARE_NEXT_TURN redirect/drop witnesses)
    -- none yet written; this is a contract/evidence checkpoint, not an implementation pass

NORMATIVE DELTAS
    minion-agent-docs/spec/agent.md ("Preclaimed inbox input" mechanism correction; consumer-
      matrix Pi-citation correction; AGENT_PRE_STEP/AGENT_PREPARE_NEXT_TURN authority rule)
    minion-agent-docs/spec/tools.md (stale Layer-05 signal-capability prose, L09-R016)
    minion-agent/pi-parity-manifest.yaml, AG-007 (PASS-8 paragraph)
    minion-agent/pi-parity-manifest.yaml, AG-011 (rule: prose corrected -- closes L09-R012)
    minion-agent/pi-parity-manifest.yaml, TOOL-009 (current-status correction, L09-R016)

NEXT_OWNER
    Codex
```
