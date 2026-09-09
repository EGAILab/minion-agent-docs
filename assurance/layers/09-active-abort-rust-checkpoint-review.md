# Layer 09 — independent Rust review of the active-abort contract checkpoint

**Verdict:** REVISION REQUIRED. The Layer-09 convergence contract is not yet agreed for
implementation. Neither Python nor Rust implementation is authorized by this review.

## Exact review state

- code baseline: `3ec1a386c86a93a13344ed38d796fbb74e9817bd`
- docs/checkpoint baseline: `0a9880042334dee0378fd24ef8f27828c1d13e28`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- coordination: `EGAILab/minion-agent#16`, received as `CONTRACT_CHECKPOINT`, `NEXT_OWNER = Codex`
- checkpoint reviewed: `assurance/layers/09-active-abort-contract-checkpoint.md`

The review read pinned Pi before treating the checkpoint as evidence: `packages/agent/src/agent.ts`,
`agent-loop.ts`, `types.ts`, and the relevant `packages/agent/test/agent.test.ts`/`e2e.test.ts`
abort witnesses. It then checked the frozen design, AG-007/PROV-004, the normative Agent/LLM/Tool
specs, and the certified Rust Layer-02/06 interfaces.

## Independently confirmed Pi rules

- `Agent.signal` is absent while idle. `runWithLifecycle` creates a new `AbortController` per run;
  every callback in that run observes the same signal object.
- `Agent.abort()` is an idempotent/no-throw idle no-op and only flips the active signal. It does not
  forcibly interrupt the JavaScript task, tool body, hook, listener, or loop.
- The signal remains active through lifecycle/recovery dispatch and `agent_end` listeners. The Agent
  becomes idle and drops the active signal only in final settlement.
- A provider that honors the signal may produce a represented `stopReason: "aborted"`; the existing
  Layer-08 represented-terminal path then handles it. If every consumer ignores the signal, abort
  alone does not force a terminal result: the run may complete normally.
- The same signal reaches lifecycle listeners, `transformContext`, the provider stream options,
  `beforeToolCall`, tool `execute`, `afterToolCall`, `prepareNextTurn`, and `shouldStopAfterTurn`.
  These are cooperative consumers; receiving a signal is not equivalent to being interrupted.
- If ordinary run execution throws after the signal has become aborted, `handleRunFailure` receives
  `aborted=true` and synthesizes an aborted failure. That is distinct from the provider returning a
  represented aborted assistant message.
- Reset remains illegal until the active run has actually settled; requesting abort does not make
  reset immediately legal.

The checkpoint is correct to reject `asyncio.Task.cancel()` as the primary semantic mechanism.
Forced task cancellation would interrupt code at arbitrary suspension points where pinned Pi merely
offers a flag to poll.

## L09-C001 — parallel tool-batch checkpoint is inaccurate

Classification: `CONTRACT_ASSURANCE_DEFECT`.

The checkpoint groups sequential and parallel execution under “after each call in a batch finalizes,
if aborted break.” That is exact for sequential execution (`agent-loop.ts:444-480`), but not for a
prepared call in parallel execution (`agent-loop.ts:499-542`). Parallel mode performs source-order
preflight first and stores lazy execution closures. Its abort poll occurs immediately after each
preflight/closure insertion, before any prepared closure begins. Only after that loop finishes does
`Promise.all` start every retained prepared closure.

Consequences that the contract must state explicitly:

1. Abort during parallel preflight truncates later source calls, but every prepared closure retained
   before the poll still starts afterward and receives the already-aborted signal.
2. Abort arising during one prepared execution/finalization cannot stop a prepared sibling: all
   retained closures are already running under `Promise.all`.
3. Immediate preflight outcomes finalize inline and are included beside retained prepared outcomes;
   returned messages remain in retained source order.

Minimal discriminating witness:

```text
parallel source: A, B, C
A preflight: prepared
B before hook: requests abort, then returns normally

Pi trace:
    start/preflight A
    start/preflight B
    immediate "Operation aborted" end B
    C is never started
    execute/finalize/end A still occurs and sees aborted=true
    returned results are retained source order A, B
```

An implementation using the checkpoint's current “after finalization” description could execute A
too early, skip A, or start C, all observably wrong.

## L09-C002 — preflight abort/error priority is incomplete

Classification: `CONTRACT_ASSURANCE_DEFECT`.

The checkpoint identifies the post-before-hook and pre-prepared polls, but it does not define their
priority relative to earlier immediate outcomes. Pinned Pi's ordering is exact:

```text
resolve tool
prepare arguments
validate arguments
await before hook, if present
    if it returned: aborted check wins over returned block
    if it threw: catch converts the hook error before any abort check
post-hook/no-hook aborted check
prepared result
```

Therefore an already-aborted signal does not globally override every preflight error:

- unknown tool remains `Tool <name> not found`;
- prepare/validation failure remains that failure;
- a throwing before hook remains its thrown message;
- a returning before hook that also requests abort produces `Operation aborted`, not its block
  reason/terminate result;
- a known valid tool with no failing earlier stage produces `Operation aborted` before execute.

These cases need a language-neutral priority matrix and discriminating evidence. A generic “abort
short-circuits preflight” rule permits incompatible Python and Rust results.

The checkpoint sentence saying abort takes priority over a hook's `block: false` is also not the
useful distinction: `block: false` would proceed anyway. The required witness is `block: true` plus
abort, where Pi chooses `Operation aborted`.

## L09-C003 — complete propagation/settlement matrix is missing

Classification: `CONTRACT_ASSURANCE_DEFECT`.

The rules are distributed across the draft, but the implementation checkpoint needs one explicit
matrix covering every consumer and what abort does there:

| Surface | Receives same run signal | Loop forces stop there? |
|---|---:|---:|
| lifecycle listener | yes | no |
| transformContext | yes | no |
| provider stream | yes | no; provider chooses |
| beforeToolCall | yes | only the explicit post-hook polls |
| tool execute | yes | no; tool chooses |
| afterToolCall | yes | no; executed calls finalize |
| prepareNextTurn | yes | no |
| shouldStopAfterTurn | yes | no; callback may return true |

The current draft omits `prepareNextTurn` from its concrete behavior matrix and does not normatively
state the important “all consumers may ignore abort and the run can finish normally” case. It also
needs to distinguish:

- represented provider `aborted` (existing Layer 08 terminal path);
- an exception after abort (Layer-08 recovery shape, but Layer-09 chooses aborted classification);
- a cooperative tool throwing/returning after observing abort (ordinary Layer-06 execute/finalize
  semantics; after hook still runs);
- abort requested during `agent_end` listener (signal changes, listener settlement still completes).

Without this matrix, two conforming implementations could treat abort as a global stop or only as a
provider hint.

## Lower-layer decision — additive delta, no reopen/escalation

The open Layer-02 question is resolved as follows:

```text
LlmService/adapter request gains an optional cancellation-signal capability
    ADDITIVE POST-CERTIFICATION DELTA OWNED BY LAYER 09

Layer-02 semantic contract reopen
    NO

owner escalation under workflow §11.7
    NO
```

Reasons:

- AG-007 already explicitly defers active propagation to Layer 09.
- PROV-004 already records adopted transport-abort parity for the later real-provider phase.
- The certified Layer-02 contract governs non-cancelled stream vocabulary/settlement and does not
  prohibit an optional signal capability.
- Omitting the new capability preserves every existing caller and non-cancelled behavior.

The contract must specify the language-neutral rule—one optional active-run signal reaches the
generic LLM request/adapter seam—not mandate Python's exact method signature. Rust can add an
optional signal to its typed `LlmRequest`/adapter boundary; Python may use an optional keyword or
request field. Both require Layer-02 regression tests and traceability evidence, but not a Layer-02
semantic recertification.

Actual network-transport cancellation remains PROV-004/provider-phase work unless a real adapter is
in the current Layer-09 scope. Layer 09 may certify generic propagation with a discriminating
scripted adapter, but must not claim that an unimplemented real transport was aborted.

## Required checkpoint remediation

Before implementation:

1. Split the sequential and parallel tool-batch abort algorithms and add the parallel-preflight
   witnesses above.
2. Add the complete preflight error/abort priority matrix and witnesses.
3. Add one complete signal-consumer/settlement matrix, including `prepareNextTurn`, ignored abort,
   exception-after-abort, and signal lifetime/identity across a run.
4. Express the LLM change as a language-neutral optional request/adapter capability and record it as
   a Layer-09-owned additive Layer-02 delta with mandatory Layer-02 regression evidence.
5. Keep actual provider-transport cancellation scoped to PROV-004 unless a concrete provider is
   explicitly brought into this layer.
6. Convert these witnesses into planned canonical scenarios or explicit language tests before the
   convergence contract is marked agreed.

## Finding state and verdict

```text
PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    none — implementation has not begun

CONTRACT_ASSURANCE_DEFECT
    L09-C001 parallel batch polling/truncation timing
    L09-C002 preflight abort/error priority
    L09-C003 complete propagation and settlement matrix

LOWER-LAYER REOPEN
    not required

CONVERGENCE CONTRACT
    REVISION REQUIRED

Python Layer 09
    NOT IMPLEMENTED

Rust Layer 09
    NOT IMPLEMENTED

Layer 09 cross-language
    NOT CLOSED
```

Next owner: Claude. Revise the contract checkpoint/evidence only; do not implement Python yet. Return
the exact remote candidate for a targeted checkpoint re-review.
