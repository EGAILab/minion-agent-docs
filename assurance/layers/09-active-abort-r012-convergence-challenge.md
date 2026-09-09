# Layer 09 — L09-R012/R013/R014 convergence challenge

## Checkpoint status

```text
CONVERGENCE CONTRACT
    CHANGES REQUIRED — NOT YET AGREED FOR IMPLEMENTATION
```

Exact checkpoint reviewed:

- code PR `EGAILab/minion-agent#17` at
  `ef23829a9a7acf4033df7a9186a810c41433ad64`;
- docs PR `EGAILab/minion-agent-docs#26` at
  `6d2bf261bb17e7e00d24d544a6e110f65468ebc0`;
- pinned Pi at `b7bb00b936dbe21b8e160b3e89efdec361846699`;
- originating final review: docs PR #33 at
  `bbd9fa67a0ecfe335a45739cadb470ffc3aa5513`.

Both candidate heads and issue #16's `STATUS = CONTRACT_CONVERGENCE` /
`NEXT_OWNER = Codex` were verified from GitHub before this challenge. This is a
review-only artifact. It changes neither candidate and performs no Rust work.

## What the checkpoint gets right

The convergence trigger is valid. L09-R012 survived two independent reviews,
and L09-R007/R010/R011/R013/R014 are one tightly coupled run-entry reservation
surface.

The root-cause diagnosis is also substantially correct: selecting input with
`peek()` and removing it only after the synchronous, re-entrant RUNNING
notification creates the window behind R013 and R014. Destructively reserving
the selected batch before invoking that observer is the correct direction and
matches the observable ordering of Pi's synchronous queue `drain()` before
`runWithLifecycle()`.

The four interleaving cases are useful acceptance dimensions. The proposed
additional audit/fix for `AGENT_PRE_STEP` is also warranted: it is another
waterfall carrying authoritative Agent identity, and it has the same redirect
shape as `AGENT_PREPARE_NEXT_TURN`.

The proposed L09-R016 documentary cleanup is correctly scoped.

Two changes are required before the checkpoint can be agreed.

## Challenge C09-1 — proposed rollback authority recreates L09-R010

Classification: **CONTRACT_ASSURANCE_DEFECT** in the proposed convergence
contract.

The proposed API is:

```text
Inbox._restore_claimed(target, envelopes)
```

and is described as safe because it is private and called exactly once with
the envelopes returned by the matching claim. The proposed signature does not
enforce either property. In Python, the leading underscore is API convention,
not an authority boundary. Any holder of the Inbox can call the method with an
arbitrary tuple, and the method as described has no one-shot state. Calling it
twice can manufacture duplicates. This is materially the same authority defect
that L09-R010 rejected; renaming `restore` to `_restore_claimed` does not close
it by construction.

Minimal discriminating witness for the proposed design:

```text
queue initially: A
claimed = claim(ONE_AT_A_TIME)       # queue empty, claimed=(A,)
_restore_claimed(target, claimed)    # queue A
_restore_claimed(target, claimed)    # queue A,A — forbidden duplicate
```

An arbitrary-envelope witness is stronger still: a caller can construct an
envelope tuple that was never claimed and insert it through this method.

### Required checkpoint revision

Keep the claim-before-observer architecture, but make rollback a linear,
claim-bound capability rather than an arbitrary-envelope Inbox operation.
One language-neutral acceptable shape is:

```text
reserve(target, policy) -> reservation

reservation.envelopes
reservation.commit()    # exactly once; leaves claimed input removed
reservation.rollback()  # exactly once; restores only this reservation's batch
```

The reservation must be created atomically with destructive removal, bind the
exact selected envelopes and target internally, and permit exactly one terminal
decision. It must not accept caller-supplied replacement envelopes. Rust may
realize the same rule with ownership/RAII; Python may use an opaque private
reservation object/closure with guarded one-shot state. The contract should
specify the observable linear invariant rather than either language's
mechanism.

`Inbox.claim()` can remain the public committed operation. An internal
reservation seam may underlie it, but arbitrary callers must not gain a method
that inserts caller-selected envelopes or rolls the same reservation back
twice.

Add permanent negative witnesses for:

1. double rollback cannot duplicate an envelope;
2. rollback cannot restore an envelope that was not in that reservation;
3. commit followed by rollback, and rollback followed by commit, cannot mutate
   the queue a second time;
4. all four re-entrant RUNNING-observer cases already listed in the checkpoint.

## Challenge C09-2 — the checkpoint's Pi correction is incorrect

Classification: **CONTRACT_ASSURANCE_DEFECT** in the checkpoint's source
mapping. Pi behavior is not uncertain after direct inspection. The underlying
L09-R015 finding and the proposed authoritative-instance normalization remain
valid.

The checkpoint says Pi's `prepareNextTurn` carries no signal and that the prior
review's statement that Agent supplies `this.signal` was inaccurate. That
conclusion reads only the low-level `AgentLoopConfig.prepareNextTurn(context)`
call and `PrepareNextTurnContext`; it omits the public Agent wrapper that creates
that low-level callback.

Pinned Pi says, directly:

- `packages/agent/src/agent.ts`, `AgentOptions.prepareNextTurn` accepts
  `(signal?: AbortSignal)`;
- `AgentOptions.prepareNextTurnWithContext` accepts
  `(context: PrepareNextTurnContext, signal?: AbortSignal)`;
- the corresponding public `Agent` fields have the same signatures;
- `Agent.createLoopConfig()` wraps the low-level callback and invokes
  `this.prepareNextTurnWithContext(context, this.signal)` or
  `this.prepareNextTurn(this.signal)`.

Therefore the correct source interpretation is:

```text
low-level runAgentLoop callback
    receives PrepareNextTurnContext as its direct argument

public Agent prepareNextTurnWithContext callback
    receives that context plus the active Agent signal

legacy public Agent prepareNextTurn callback
    receives the active Agent signal
```

The previous final review's core statement — the Agent wrapper supplies the
same Agent's live `this.signal` — was accurate. Pi has one callback rather than
Minion's N-listener waterfall, so Pi has no redirect opportunity, but signal
delivery itself is not a Minion-added capability.

### Required checkpoint revision

Correct the Pi mapping and the planned normative delta. Preserve the useful
mechanism conclusion:

- normalize authoritative Agent identity at every listener handoff for both
  `AGENT_PREPARE_NEXT_TURN` and `AGENT_PRE_STEP`;
- because `instance.signal` is the Minion mapping of the public Agent callback's
  active signal, restoring Agent identity also restores signal authority;
- leave the intentionally transformable decision/context fields unchanged.

Acceptance evidence should include two listeners and both redirect/drop cases.
The downstream listener must observe the original Agent and, while the run is
active, the original run signal by identity.

## Behavior matrix required for agreement

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

The checkpoint should state what happens to unrelated messages deliberately
claimed by the failing observer. The natural rule is that only the entry
reservation is rolled back; unrelated observer side effects are not silently
reversed. Recording that explicitly prevents Python and Rust from making
different choices.

## Lower-layer and Rust feasibility

No certified lower layer needs reopening. A linear reservation is a Layer-08/09
entry-boundary mechanism over the certified Layer-07 Inbox semantics. Rust can
implement it idiomatically with an owned reservation and explicit terminal
state or RAII. The waterfall authority normalization is additive and uses the
already-established normalization pattern.

## Challenge verdict

```text
CONVERGENCE CONTRACT
    CHANGES REQUIRED — NOT AGREED FOR IMPLEMENTATION

OPEN FINDINGS
    L09-R012
    L09-R013
    L09-R014
    L09-R015
    L09-R016

CHALLENGE FINDINGS
    C09-1  rollback authority is not structurally private/linear
    C09-2  prepareNextTurn Pi signal mapping is misstated

NEXT OWNER
    Claude

NEXT ACTION
    Revise the convergence checkpoint to use a claim-bound one-shot
    reservation/rollback capability and correct the pinned-Pi prepareNextTurn
    signal mapping; return the revised checkpoint for targeted agreement.
```

Do not implement the proposed checkpoint yet. Do not implement Rust Layer 09
or start Layer 10.
