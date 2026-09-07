# Layer 09 — Active abort/cancellation: contract-first checkpoint (draft, NOT yet approved)

**Status:** DRAFT. This is a `process/agent-workflow.md` section 4.1 contract-first checkpoint
artifact, produced BEFORE any Python implementation. It exists to move semantic discovery earlier,
following the Layer-08 retrospective's own first lesson (`assurance/process-history.md`): the
convergence-trigger and checkpoint mechanisms exist because Layer 08 discovered scheduler/ordering
semantics one implementation pass at a time. Cancellation is explicitly named in §4.1 as a
high-risk surface warranting this checkpoint before a large implementation pass.

**This artifact does not authorize implementation.** Per §4.1: Claude Pi-audit/draft (this
document) → Codex independent Pi audit of the same slice → resolve contract/evidence findings →
CONTRACT CHECKPOINT → Python implementation → independent implementation-readiness review.

## Starting state

- accepted code baseline: `minion-agent@main` `3ec1a386c86a93a13344ed38d796fbb74e9817bd`
- accepted docs baseline: `minion-agent-docs@master` `8dfe5f71c72ef8af16c956dead1b2a5d531ad001`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Layer 08: CROSS-LANGUAGE CERTIFIED / CLOSED (`assurance/layers/08-agent-loop-rust-implementation.md`)
- Layer 09 was explicitly deferred by both Layer 07 (`spec/agent.md`: "Layer 07 does not define or
  touch any cancellation primitive") and Layer 08 (`spec/agent.md`'s own "Active abort propagation
  (explicitly out of scope)" section, `AG-007`)

## Why this is a genuine, not merely mechanical, contract question

Layer 05/06's own `tools/definition.py::ToolFn` docstring already anticipated this layer directly:
"The `signal` (cancellation) parameter remains behaviorally unrealized in Python -- but the
cross-language state is asymmetric, not uniformly absent (`IR-L05/06-006`): certified Rust Layer 05
already reserves a structural signal seam (`ToolExecutionSignal`, `ToolExecutionRequest.signal` in
`minion-agent-rust/crates/minion-agent/src/tools/definition.rs`) without exercising cancellation
behavior. Python has no `AbortSignal`-equivalent abstraction at all yet." Rust's own reserved trait:

```rust
pub trait ToolExecutionSignal: Send + Sync + 'static {
    fn is_cancelled(&self) -> bool;
}
```

A poll-based, cooperative check -- not a push/interrupt mechanism. This matches pinned Pi's own
usage pattern exactly (see below): every `signal` reference in `agent-loop.ts` is a `signal?.aborted`
poll or a pass-through to a hook/tool that may poll it itself. Pi's own code never treats an abort
as a forcible interrupt of in-flight synchronous work.

This directly rules out the most "Pythonic-looking" shortcut: driving cancellation purely through
`asyncio.Task.cancel()` and letting `CancelledError` unwind the call stack. That would be a
GENUINELY DIFFERENT, more aggressive semantic than Pi's own cooperative-poll model -- it would
forcibly interrupt a tool's `execute()` body at whatever `await` point it happens to be at, where
Pi's own design lets that same tool run to completion unless the tool itself chooses to check
`signal.aborted`. Adopting task-cancellation instead of an explicit, threaded, poll-based signal
would be an unapproved observable divergence from Pi, not a value-neutral implementation detail.

## Pi behavior matrix (`ref-repos/pi` @ `b7bb00b`, `agent.ts` + `agent-loop.ts`)

### Public surface (`agent.ts`)

| Surface | Behavior |
|---|---|
| `Agent.signal` (getter) | `this.activeRun?.abortController.signal` -- `undefined` when no run is active. A NEW signal/`AbortController` is created per run (`runWithLifecycle`, `agent.ts:491`), not reused across runs. |
| `Agent.abort()` | `this.activeRun?.abortController.abort()` -- a no-op, does not throw, when no run is active. |
| `subscribe(listener)` | Listener receives `(event, signal)` -- every lifecycle-event listener ALSO receives the active run's signal as its own second parameter, not only tool/hook callbacks. |
| `waitForIdle()` | Resolves after `agent_end` listeners settle, same as ordinary completion -- abort does not create a separate idle-reached signal; the run still runs its full recovery/settlement sequence, just typically reaching a represented-`aborted` terminal sooner. |
| `reset()` | Throws `"Agent is already processing..."` if `activeRun` is still set -- calling `abort()` then immediately `reset()` before the run has actually settled still throws; the caller must await idle (or the run's own completion) first, exactly as for a non-aborted active run. |

### Represented-terminal path (already Layer-08-owned, NOT new to Layer 09)

If the underlying provider stream itself honors the signal and settles with
`stopReason: "aborted"` (a `pi-ai`-level concern, one layer below this project's own Layer 02 LLM
seam), `runLoop` (`agent-loop.ts:196`) immediately emits `turn_end` (empty `toolResults`) then
`agent_end` and returns -- the SAME represented-terminal short-circuit Layer 08 already
certifies for `stopReason: "error"`. **Layer 09 does not need to add or change this path.** Its
only job here is making sure a real signal reaches the stream call in the first place (see Layer 02
below) so a real provider adapter has something to honor.

### Tool-execution signal checkpoints (`agent-loop.ts`, all NEW to Layer 09)

| Checkpoint | Function | Effect |
|---|---|---|
| After `beforeToolCall` returns | `prepareToolCall` | If `signal?.aborted`, IMMEDIATELY returns an `"Operation aborted"` error result -- checked BEFORE the hook's own `block` decision is even consulted. Takes priority over a `block: false` the hook itself returned. |
| Before returning "prepared" (hook absent or hook did nothing) | `prepareToolCall` | A second, independent `signal?.aborted` check right after the `beforeToolCall` conditional -- covers "no before-hook configured" and "hook ran but the abort raced in after its own check." |
| `execute()`'s own third parameter | `executePreparedToolCall` | `signal` is passed to the tool author's own `execute(toolCallId, params, signal, onUpdate)` DIRECTLY. Whether execution actually stops is entirely the tool's own cooperative choice -- Pi does not force-interrupt it. |
| `afterToolCall` | `finalizeExecutedToolCall` | Runs to completion UNCONDITIONALLY, regardless of abort state -- no `signal?.aborted` short-circuit here at all. An already-executed call is always finalized normally. |
| After each call in a batch finalizes | `executeToolCallsSequential`/`executeToolCallsParallel` | `if (signal?.aborted) break;` -- stops STARTING further calls in the SAME batch. Sequential: calls already started/finalized keep their results; remaining un-started calls are simply never attempted (batch `messages` is SHORTER than `toolCalls`). Parallel: calls already dispatched (as queued async closures) still run via `Promise.all`; only calls not yet reached in the `for` loop are skipped. |

**Batch truncation is a real, observable divergence from a full batch.** `messages.length` can be
less than `toolCalls.length`. `shouldTerminateToolBatch` is evaluated only over the calls that WERE
finalized -- an aborted, truncated batch can still set `terminate: true` if every call that DID run
set it.

**Critically: aborting mid-tool-batch does NOT end the run.** After the batch (truncated or not),
`turn_end` fires normally, then `prepareNextTurn`/`shouldStopAfterTurn`/steering-poll all run
exactly as they would for a non-aborted turn. `shouldStopAfterTurn`'s own signature already accepts
`signal` (`agent.ts:108`) -- a LISTENER may choose to stop the run because it sees the signal is
aborted, but the LOOP itself does not force this. If nothing reacts to the abort at this level, the
NEXT `streamAssistantResponse` call passes the SAME signal to the provider, which is where an
abort-during-a-later-turn's-own-request most likely produces the represented-`aborted` terminal.

### `transformContext`

Also receives `signal` (`agent.ts:101`, `agent-loop.ts:291`) -- cooperative, no forced check by the
loop itself, same pattern as `afterToolCall`.

## Ownership matrix (proposed, for review)

| Layer | Owns | Change needed |
|---|---|---|
| 07 (Agent state/inbox, CLOSED) | N/A, explicitly deferred | none -- `AgentInstance` gains a NEW per-run signal/controller pair, additive |
| 08 (Agent Loop, CLOSED) | run/turn orchestration | ADDITIVE: thread a real per-run signal object through `_execute_run`/`_run_inner`/`_run_step`, matching every `signal` parameter position `agent-loop.ts` has; wire the batch-truncation checkpoints into `_run_step`'s own tool-batch call |
| 06 (Tool execution, CLOSED) | `execute_call`/hooks/batch | ADDITIVE: Rust already reserved the seam (`ToolExecutionSignal`); Python needs the equivalent -- a new `ToolFn` third positional parameter, matching `execute.py`'s existing arity-detection convention for `on_update` |
| 02 (LLM, CLOSED) | provider streaming | ADDITIVE, but a GENUINE new surface: `LlmService.stream()`/`Adapter.stream()` currently have no signal parameter at all (unlike Layer 06, nothing was pre-reserved here). This is the one seam where "additive" still means widening an already-certified public method's own signature. |
| 05 (Tools model/registry, CLOSED) | `ToolDefinition` | none directly -- the `ToolFn` type alias lives in `tools/definition.py` (Layer 05-owned module) but the signal parameter is Layer 06/09 BEHAVIOR, matching the existing `on_update` precedent (Layer 05 owns the shape's existence, Layer 06/09 owns whether/when it's realized) |

**Open question for Codex's own independent audit and/or owner input:** is widening
`LlmService.stream()`'s signature a "genuine lower-layer reopen" requiring `process/agent-
workflow.md` §11.7 owner escalation, or does it qualify as the same kind of purely-additive,
default-`None`-preserves-existing-behavior extension Layer 08 PASS 6 already used to add
`on_execution_start`/`on_execution_end` hooks to certified Layer 06 without owner escalation? My
own reading is the latter (no existing caller's behavior changes when the new parameter is
omitted/`None`, mirroring the PASS-6 precedent exactly), but this is exactly the kind of judgment
call §4.1 exists to catch BEFORE a full implementation pass, not after.

## Proposed Python signal abstraction (draft, for review -- not yet implemented)

`asyncio.Event`-based, matching Rust's own poll-based `ToolExecutionSignal` trait shape:

```python
class RunSignal:
    """Layer 09's own AbortSignal-equivalent: a per-run cancellation flag, poll-based
    (matches Rust's ToolExecutionSignal.is_cancelled() and pinned Pi's signal.aborted --
    NOT asyncio task cancellation, which would forcibly interrupt cooperative code Pi's
    own design lets run to completion unless the code itself checks the signal)."""

    def __init__(self) -> None:
        self._event = asyncio.Event()

    @property
    def aborted(self) -> bool:
        return self._event.is_set()

    def abort(self) -> None:
        self._event.set()
```

A NEW `RunSignal()` is constructed per run (matching `new AbortController()` per `runWithLifecycle`
call), exposed as `AgentInstance.signal: RunSignal | None` (only set while a run is active,
matching pinned Pi's own getter returning `undefined` when idle) and `AgentInstance.abort() -> None`
(no-op if idle).

## Findings requiring resolution before implementation

```text
PI_BEHAVIOR_UNCERTAIN   none -- pinned Pi source read directly and fully for every signal
                        checkpoint in agent.ts/agent-loop.ts; no ambiguity found in Pi's own
                        behavior itself

CONTRACT_ASSURANCE_DEFECT   none yet classified -- this checkpoint exists specifically to surface
                        any before implementation locks in an unreviewed design

OPEN DESIGN QUESTION    Layer-02 LlmService.stream() signature widening: additive extension
                        (Claude's own read) vs. genuine lower-layer reopen requiring owner
                        escalation (process/agent-workflow.md §11.7) -- requires Codex's own
                        independent judgment and/or owner confirmation before Python
                        implementation begins
```

## Next action

Per `process/agent-workflow.md` §4.1: hand this checkpoint to Codex for an independent Pi audit of
the SAME slice (signal checkpoints, batch-truncation semantics, the Layer-02 widening question
above). Do not begin Python implementation until that audit lands and any findings are resolved.
This is a checkpoint, not cross-language certification, and does not authorize Rust implementation
either.
