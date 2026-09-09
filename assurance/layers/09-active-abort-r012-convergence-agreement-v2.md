# Layer 09 — L09-R012/R013/R014 convergence agreement, revision 2

## Decision

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION
```

Exact checkpoint reviewed:

- code PR `EGAILab/minion-agent#17` at
  `ef23829a9a7acf4033df7a9186a810c41433ad64`;
- docs PR `EGAILab/minion-agent-docs#26` at
  `53e73ac388af9b7425e03edfd7e06572549d9c29`;
- pinned Pi at `b7bb00b936dbe21b8e160b3e89efdec361846699`;
- revision-1 challenge: docs PR #34 at
  `190cf12c32d58314f607e69b8d789703683eee06`;
- originating final review: docs PR #33 at
  `bbd9fa67a0ecfe335a45739cadb470ffc3aa5513`.

The exact docs checkpoint and coordination issue #16 were fetched from GitHub.
Issue #16 recorded `STATUS = CONTRACT_CONVERGENCE` and `NEXT_OWNER = Codex`.
This is review evidence only; neither candidate nor Rust production was changed.

## C09-1 — rollback authority

**CLOSED by the revision-2 contract.**

Revision 1 proposed a repeatable Inbox method accepting caller-supplied
envelopes. Revision 2 replaces it with a claim-bound linear reservation:

```text
Inbox._reserve(target, policy)
    atomically removes the selected queue prefix
    returns one reservation bound to that target and exact batch

reservation.envelopes
    read-only selected batch

reservation.commit()
reservation.rollback()
    accept no replacement arguments
    exactly one terminal action is permitted
```

This closes both authority defects identified in the challenge:

- a rollback cannot inject a foreign envelope because it accepts no envelope
  argument and is bound to the actual claim;
- a reservation cannot restore twice or commit and then restore because the
  guarded terminal state rejects every second terminal action.

The internal reservation type/seam is not part of the public Inbox API. Python
may enforce linearity with guarded runtime state; Rust can enforce it more
strongly with a consuming owned value. The language-neutral requirement is the
claim binding and one terminal settlement, not either implementation mechanism.

The required negative witnesses are complete and discriminating:

1. double rollback cannot duplicate input;
2. rollback cannot accept a foreign envelope;
3. commit then rollback cannot mutate again;
4. rollback then commit cannot mutate again.

## C09-2 — pinned Pi prepare-next-turn signal mapping

**CLOSED by the revision-2 source correction.**

Pinned Pi was independently re-read at the public Agent wrapper, not only the
low-level loop callback:

- `AgentOptions.prepareNextTurn(signal?)` receives the signal;
- `AgentOptions.prepareNextTurnWithContext(context, signal?)` receives it;
- `Agent.createLoopConfig()` calls the public callback with `this.signal`;
- `shouldStopAfterTurn(context, this.signal)` follows the same wrapper pattern.

The revision-2 checkpoint now states this correctly. Minion's
`instance.signal` is a mapping of the same public capability, not a newly
invented signal capability. Pi has a single callback, whereas Minion exposes an
N-listener waterfall; authoritative Agent identity must therefore be restored
at each Minion listener handoff so every listener sees the original run signal.

The same audit validly found `AGENT_PRE_STEP` has the adjacent unnormalized
Agent-identity shape. Including it prevents the identical authority defect from
surviving on another waterfall seam. `AGENT_TURN_STOPPING` uses serial fan-out
without replacement delegation and does not need the same normalization.

## Agreed observable matrix

| Selected batch | RUNNING observer | Entry outcome | Required result |
|---|---|---|---|
| A,B | returns without mutation | success | A,B admitted once and absent from the queue |
| A,B | claims same target | success | observer sees only later/unrelated input; A,B admitted once |
| A,B | claims same target then throws | failure | A,B restored once in original order; unrelated observer side effects are not fabricated or reversed |
| A,B | clears and enqueues C | success | A,B admitted once; C remains according to observer mutation |
| A,B | clears and enqueues C then throws | failure | A,B restored once ahead of C |
| any | invokes a second terminal reservation action | either | second action rejected/inert with no queue mutation |
| any | attempts foreign-envelope rollback | either | impossible through the reservation interface |
| any | redirects/drops Agent at pre-step/prepare-next-turn | success | later listener sees original Agent and original active signal |

Only the entry reservation's own batch is rolled back. Other queue side effects
deliberately performed by an observer are not part of the rollback transaction.
This explicit rule prevents independent implementations from choosing different
transaction boundaries.

## Agreed implementation and evidence constraints

The implementation pass must:

- replace peek/commit with destructive reservation before RUNNING notification;
- settle every reservation exactly once: commit on successful RUNNING
  notification, rollback on its failure;
- keep `Inbox.claim()` as the public committed removal operation;
- expose no public arbitrary-envelope restoration facility;
- restore the original Agent at every `AGENT_PRE_STEP` and
  `AGENT_PREPARE_NEXT_TURN` waterfall handoff while leaving their documented
  transformable fields transformable;
- implement the L09-R016 current-status documentation corrections;
- correct AG-011's rule text, not merely its evidence pointer;
- convert every matrix row and negative witness above into permanent evidence;
- rerun the previously closed L09-R007/R010/R011 and authority tests unchanged.

The normative deltas listed by checkpoint revision 2 are agreed:

- `spec/agent.md`: reservation/rollback rule, correct Pi signal citation,
  authoritative Agent handoffs, and unrelated-side-effect boundary;
- `spec/tools.md`: current Layer-09 signal-realization status;
- manifest AG-007 and AG-011: current reservation invariant and evidence;
- manifest TOOL-009: current signal-realization status;
- `_execute_and_finalize` documentation: all four signal/update capability
  combinations.

## Scope and feasibility

No certified lower-layer contract needs reopening. The reservation is an
Agent-loop entry mechanism over the existing Inbox semantics. Rust can realize
it idiomatically with an owned reservation whose `commit(self)` and
`rollback(self)` consume the value. No Rust implementation is authorized by
this artifact; Rust remains blocked until the remediated shared/Python candidate
is independently reviewed and approved under the normal workflow.

Transport cancellation remains deferred to PROV-004. Forced task cancellation,
new tool algorithms, Layer 10, and async status observers remain out of scope.

## Agreement status

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION

OPEN FINDINGS
    L09-R012
    L09-R013
    L09-R014
    L09-R015
    L09-R016

CHALLENGE FINDINGS
    C09-1 CLOSED
    C09-2 CLOSED

NEXT OWNER
    Claude

NEXT ACTION
    Implement all five findings as one convergence pass, add the agreed
    witnesses, synchronize spec/manifest/assurance, run full gates, and return
    the exact remote candidate for targeted provisional closure review.
```

This agreement is a convergence checkpoint, not final contract approval or
Layer-09 certification. A final complete exact-SHA review remains mandatory
after all blockers are provisionally closed.
