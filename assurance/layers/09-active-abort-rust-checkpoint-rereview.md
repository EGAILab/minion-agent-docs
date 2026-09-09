# Layer 09 — targeted independent Rust re-review of the active-abort checkpoint

**Verdict:** CONVERGENCE CONTRACT AGREED FOR PYTHON IMPLEMENTATION. The three revision-1
`CONTRACT_ASSURANCE_DEFECT` findings are provisionally closed at the exact revision-2 baseline
below. This checkpoint is not final shared-contract approval, does not certify either language,
and does not authorize Rust Layer-09 implementation.

## Exact review state

- code baseline: `minion-agent@main` `3ec1a386c86a93a13344ed38d796fbb74e9817bd`
- docs/checkpoint baseline: `minion-agent-docs@master`
  `ecb809798b7437045e1325683306c3f15f46571e`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- coordination: `EGAILab/minion-agent#16`, received as `CONTRACT_CHECKPOINT`,
  `NEXT_OWNER = Codex`
- revision-1 review: `minion-agent-docs#23` at
  `3787ceda5ef90fe03a9115649e7b9d92e0101530`
- checkpoint reviewed: `assurance/layers/09-active-abort-contract-checkpoint.md` revision 2

Both baselines and the checkpoint SHA were fetched and verified on their remote default branches.
The review was performed against pinned Pi first: `packages/agent/src/agent.ts`,
`packages/agent/src/agent-loop.ts`, `packages/agent/src/types.ts`, and the relevant abort behavior
in the pinned tests. The revision-1 review was then compared with revision 2. No Python or Rust
Layer-09 implementation exists or was reviewed as an oracle.

## Targeted closure ledger

### L09-C001 — sequential and parallel tool-batch abort algorithms

**Revision-1 finding:** `CONTRACT_ASSURANCE_DEFECT`. The draft incorrectly described the
parallel batch poll as if it occurred after complete call finalization, losing Pi's sequential
preflight / deferred parallel-execution boundary.

**Independent source result:** pinned `executeToolCallsSequential` completes a call before its
between-call abort poll. Pinned `executeToolCallsParallel` instead awaits each source call's
preflight sequentially, retains prepared closures, polls after each immediate outcome or retained
closure, and starts all retained closures only after the preflight loop via `Promise.all`.

**Revision-2 result:** the algorithms are now specified separately. The contract states that an
abort observed during parallel preflight truncates only later, not-yet-preflighted calls; retained
closures still start with the aborted signal; an abort during retained execution does not cancel
siblings; and returned outcomes retain source order.

The included A/B/C witness is discriminating and matches Pi:

```text
A retained as prepared
B before hook requests abort and returns
B finalizes inline as Operation aborted
C never starts
A still executes/finalizes with aborted=true
returned results: A, B in source order
```

**Status:** `PROVISIONALLY CLOSED @ ecb809798b7437045e1325683306c3f15f46571e`.

### L09-C002 — preflight abort/error priority

**Revision-1 finding:** `CONTRACT_ASSURANCE_DEFECT`. “Abort short-circuits preflight” did not
define priority against unknown-tool, validation/prepare failure, throwing hooks, and returned
blocking decisions.

**Independent source result:** pinned `prepareToolCall` resolves the tool before its guarded
prepare/validate/hook sequence. Unknown tool, prepare/validation throws, and a throwing before
hook preserve their own errors. After a returning before hook, abort wins over its `block:true`
result. With no earlier failure/block, the later abort check produces `Operation aborted`; only
then can the call be retained as prepared.

**Revision-2 result:** the numbered priority sequence now captures all immediate outcomes plus
the prepared-success outcome and identifies the discriminating `block:true + abort` witness.
Two independent implementations no longer need to guess whether abort masks an earlier error.

Editorial note only: the heading calls this “six mutually-exclusive outcomes” while the numbered
list contains six immediate/error cases plus a seventh prepared-success outcome. The numbered
semantics are unambiguous; this is `PARITY_NEUTRAL_HARDENING`, not a checkpoint blocker.

**Status:** `PROVISIONALLY CLOSED @ ecb809798b7437045e1325683306c3f15f46571e`.

### L09-C003 — signal consumers, lifetime, and settlement

**Revision-1 finding:** `CONTRACT_ASSURANCE_DEFECT`. The draft omitted `prepareNextTurn`, did not
state the all-consumers-ignore-abort case, and did not distinguish represented abort, an exception
after abort, cooperative tool behavior, and abort during `agent_end` settlement.

**Independent source result:** one per-run signal is exposed through the active run and reaches
lifecycle listeners, transform context, provider streaming, before/execute/after tool seams,
`prepareNextTurn`, and `shouldStopAfterTurn`. Queue-drain callbacks receive no signal. Except for
the explicit tool preflight/between-call polls, consumers decide cooperatively whether to react.
The signal remains the same through recovery and `agent_end` listener settlement; idle settlement
then removes the active signal.

**Revision-2 result:** one complete matrix now identifies every consumer and forced-poll boundary,
states that all consumers may ignore abort and allow normal completion, defines per-run identity
and lifetime, and distinguishes:

1. a provider-represented `aborted` terminal result;
2. any escaping exception observed while the signal is aborted, classified by recovery as aborted
   without requiring causal linkage;
3. a cooperative tool's normal/throwing outcome followed by ordinary Layer-06 finalization and
   unconditional after-hook processing;
4. abort during `agent_end`, which does not bypass already-running listener settlement.

**Status:** `PROVISIONALLY CLOSED @ ecb809798b7437045e1325683306c3f15f46571e`.

## Lower-layer and implementation-boundary decision

The revision-1 lower-layer conclusion remains approved:

```text
optional signal capability at the generic LLM request/adapter seam
    additive Layer-09-owned post-certification delta

Layer-02 semantic reopen
    no

owner escalation
    no

real provider/network transport cancellation
    deferred to PROV-004 unless explicitly scoped later
```

The same reasoning applies to the already-reserved Rust `ToolExecutionSignal` seam and the Python
tool-call shape: Layer 09 realizes cooperative propagation without replacing certified
non-cancelled Layer-02 or Layer-06 semantics. Implementation must rerun those lower-layer gates and
must not use forced task cancellation as a substitute for the pollable signal contract.

## Required implementation evidence

The checkpoint is sufficiently precise to resume the Python/shared implementation pass. That pass
must turn the checkpoint witnesses into permanent canonical or explicit language tests, including:

- sequential and parallel batch witnesses, especially A/B/C;
- the complete preflight priority matrix, including `block:true + abort`;
- same-signal propagation to every listed consumer;
- all-consumers-ignore-abort normal completion;
- represented abort versus exception-after-abort;
- cooperative tool and unconditional after-hook behavior;
- abort during `agent_end` settlement;
- reset remaining illegal until the aborted run actually settles;
- Layer-02 and Layer-06 non-cancelled regression evidence.

The later implementation-readiness review must assess the exact remote Python/shared candidate and
the resulting normative spec, manifest, canonical evidence, and runner thinness. These provisional
closures do not waive that review or the final exact-SHA approval gate.

## Findings and checkpoint verdict

```text
PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    none — implementation has not begun

CONTRACT_ASSURANCE_DEFECT
    none active within the targeted checkpoint surface

PARITY_NEUTRAL_HARDENING
    wording only: “six outcomes” heading versus six immediate cases plus prepared success

LOWER_LAYER_REOPEN
    not required

L09-C001
    PROVISIONALLY CLOSED @ ecb809798b7437045e1325683306c3f15f46571e

L09-C002
    PROVISIONALLY CLOSED @ ecb809798b7437045e1325683306c3f15f46571e

L09-C003
    PROVISIONALLY CLOSED @ ecb809798b7437045e1325683306c3f15f46571e

CONVERGENCE CONTRACT
    AGREED FOR PYTHON IMPLEMENTATION

Python Layer 09
    NOT_IMPLEMENTED

Rust Layer 09
    NOT_IMPLEMENTED

Layer 09 cross-language
    NOT CLOSED

Layer 10
    NOT STARTED
```

Next owner: Claude. Implement the Python/shared Layer-09 candidate against this checkpoint and its
discriminating witnesses, then return exact remote candidate SHA(s) for independent Rust contract
review. Do not implement Rust Layer 09 or start Layer 10.
