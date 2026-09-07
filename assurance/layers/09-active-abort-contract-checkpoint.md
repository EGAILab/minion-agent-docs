# Layer 09 — Active abort/cancellation: contract-first checkpoint (revision 2, NOT yet approved)

**Status:** DRAFT, revision 2. This is a `process/agent-workflow.md` section 4.1 contract-first
checkpoint artifact, produced BEFORE any Python implementation. It exists to move semantic
discovery earlier, following the Layer-08 retrospective's own first lesson
(`assurance/process-history.md`): the convergence-trigger and checkpoint mechanisms exist because
Layer 08 discovered scheduler/ordering semantics one implementation pass at a time. Cancellation is
explicitly named in §4.1 as a high-risk surface warranting this checkpoint before a large
implementation pass.

**This artifact does not authorize implementation.** Per §4.1: Claude Pi-audit/draft → Codex
independent Pi audit of the same slice → resolve contract/evidence findings → CONTRACT CHECKPOINT →
Python implementation → independent implementation-readiness review.

**Revision 2 remediates the independent Rust review of revision 1**
(`minion-agent-docs#23`, review commit `3787ceda5ef90fe03a9115649e7b9d92e0101530`,
`assurance/layers/09-active-abort-rust-checkpoint-review.md`): **REVISION REQUIRED**, three
`CONTRACT_ASSURANCE_DEFECT` findings (`L09-C001` parallel-batch polling timing, `L09-C002`
incomplete preflight abort/error priority, `L09-C003` missing complete signal-consumer/settlement
matrix). The review independently re-confirmed every Pi rule revision 1 stated and found none of
them wrong -- the defects were incompleteness/imprecision, not incorrect claims. The review also
resolved the revision-1 open design question: the Layer-02 signal capability is a Layer-09-owned
ADDITIVE delta, NOT a semantic reopen, and does NOT require owner escalation under §11.7 -- see
"Lower-layer decision" below. Each finding is addressed in its own section, marked accordingly.

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

### Preflight abort/error priority (`prepareToolCall`, `agent-loop.ts:600-668`) — `L09-C002`

Six mutually-exclusive outcomes, in EXACT priority order (earlier wins; later checks are only
reached if nothing earlier already returned):

```text
1. tool not in currentContext.tools
       -> "Tool <name> not found"
       -- checked BEFORE the try block and BEFORE any signal read; wins unconditionally,
          even if the signal is already aborted when the call starts.

2. prepareArguments/validateToolArguments throws
       -> the exception's own message, via the outer catch
       -- runs BEFORE beforeToolCall is even invoked; not affected by abort state.

3. beforeToolCall is configured AND it throws
       -> the exception's own message, via the SAME outer catch
       -- a thrown hook error is caught before any abort check is reached; abort does NOT
          override a hook's own thrown error.

4. beforeToolCall is configured, RETURNS (does not throw), and signal.aborted is true
   at that point
       -> "Operation aborted"
       -- wins over the hook's OWN block:true/reason/terminate decision. The discriminating
          case is block:true + aborted, not block:false + aborted (block:false would have
          proceeded to step 5 anyway, so it is not distinguishing).

5. beforeToolCall configured, returns, NOT aborted, beforeResult.block === true
       -> the hook's own block reason/terminate

6. no beforeToolCall configured, OR one ran without throwing/aborting/blocking, AND
   signal.aborted is true at this point
       -> "Operation aborted"
       -- the ONLY abort check reached when no before-hook exists at all; for a hook that
          already passed step 4 without aborting, this is not independently reachable in the
          same synchronous stretch (no further `await` happens between step 4's check and
          this one when a hook is configured), so this step's own practical effect is the
          no-hook path.

7. none of the above
       -> kind: "prepared" (proceeds to execute())
```

A generic "abort short-circuits preflight" rule is WRONG: an unknown tool, a validation failure,
and a throwing before-hook all keep their own specific error even when the signal is already
aborted -- only a RETURNING (non-throwing) hook, or no hook at all, yields to "Operation aborted".

### Tool-batch abort algorithms — SEQUENTIAL vs PARALLEL are genuinely different — `L09-C001`

Both share the SAME `prepareToolCall` priority matrix above for each individual call's own
preflight. They differ in how abort interacts with the BATCH as a whole.

**Sequential (`executeToolCallsSequential`, `agent-loop.ts:433-487`):** one call at a time, fully
awaited end to end (preflight, then execute+finalize if prepared) before the next call even starts.
`if (signal?.aborted) break;` runs AFTER each call's own full finalization, before starting the
NEXT call. A call already started always completes (preflight -> execute -> finalize -> end) before
the abort check is even consulted; only calls not yet reached are skipped. `messages.length` can be
shorter than `toolCalls.length`.

**Parallel (`executeToolCallsParallel`, `agent-loop.ts:489-554`): preflight is still SEQUENTIAL, only
execution is deferred and parallel.** The `for` loop iterates `toolCalls` in source order and
AWAITS `prepareToolCall` for each one, one at a time -- preflight itself is never concurrent. For
each call:

- an `"immediate"` preflight outcome (steps 1/2/3/4/5 above) finalizes and is EMITted inline, then
  `if (signal?.aborted) break;` decides whether to preflight the NEXT source call;
- a `"prepared"` outcome (step 7) is NOT executed yet -- it is stored as a lazy async closure
  (`() => { execute -> finalize -> emit end }`), and the SAME `if (signal?.aborted) break;` check
  runs immediately after storing it, before preflighting the next source call.

Only once the `for` loop exits does `Promise.all` run every RETAINED closure concurrently. This
means:

1. abort observed during preflight truncates only LATER, not-yet-preflighted source calls; every
   closure already retained before the poll STILL STARTS afterward via `Promise.all`, and receives
   the already-aborted signal as its own `execute()`/`afterToolCall` parameter (cooperative, not
   forced);
2. abort arising DURING one prepared call's own execution/finalization cannot stop a prepared
   sibling -- by the time `Promise.all` runs, every retained closure is already committed to
   running; there is no further per-closure abort poll inside `Promise.all` itself;
3. immediate (inline-finalized) outcomes and prepared (closure) outcomes are interleaved in the
   final `orderedFinalizedCalls`/returned `messages` in RETAINED SOURCE ORDER, not start/finish
   order -- `finalizedCalls.map((entry) => typeof entry === "function" ? entry() : ...)` preserves
   array position regardless of which finished first.

Minimal discriminating witness (from the independent review, reproduced here as the required
regression basis):

```text
parallel source: A, B, C
A preflight: prepared (no before hook)
B before hook: calls abort() itself, then returns normally (not blocking)
(C is source-order after B)

expected Pi trace:
    tool_execution_start A
    tool_execution_start B
    B's beforeToolCall runs, calls abort(), returns
    B preflight step 4 fires: signal now aborted -> immediate "Operation aborted", tool_execution_end B
    for-loop poll: signal.aborted -> break -- C's own tool_execution_start never fires
    Promise.all runs A's retained closure: A's own execute()/afterToolCall receive the
        now-aborted signal cooperatively (A does not know to stop unless it checks the signal)
    tool_execution_end A (after A's own execute()/afterToolCall complete normally)
    returned toolResults/messages: [A, B] in that source order -- C is entirely absent
```

An implementation that (a) executes A before starting B's own preflight, (b) skips A once aborted,
or (c) starts C's own preflight/execution at all, is observably wrong against this witness.

### `afterToolCall` runs unconditionally regardless of abort state

`finalizeExecutedToolCall` has NO `signal?.aborted` short-circuit at all -- an already-executed call
is ALWAYS finalized and its `afterToolCall` hook ALWAYS runs to completion, whether or not the
signal became aborted during or after `execute()`. Abort never causes an executed call's own result
to be discarded or its after-hook to be skipped.

### `execute()`'s own third parameter

`signal` is passed to the tool author's own `execute(toolCallId, params, signal, onUpdate)`
DIRECTLY (`executePreparedToolCall`, `agent-loop.ts:670-711`). Whether execution actually stops is
entirely the tool's own cooperative choice -- Pi does not force-interrupt it.

**Critically: aborting mid-tool-batch does NOT end the run.** After the batch (truncated or not),
`turn_end` fires normally, then `prepareNextTurn`/`shouldStopAfterTurn`/steering-poll all run
exactly as they would for a non-aborted turn -- see the complete consumer matrix below.

### `transformContext`

Also receives `signal` (`agent.ts:101`, `agent-loop.ts:291`) -- cooperative, no forced check by the
loop itself, same pattern as `afterToolCall`.

### Complete signal-consumer and settlement matrix — `L09-C003`

Every consumer of the active run's signal, and whether the LOOP ITSELF (as opposed to the consumer
choosing to react) forces a stop there. "Same signal" means the identical `AbortController.signal`
object created once at `runWithLifecycle`'s own start, threaded or closure-captured unchanged for
the whole run's own lifetime (see "Signal lifetime and identity" below).

| Surface | Receives the run's signal | Loop forces a stop there? |
|---|---:|---:|
| lifecycle listener (`subscribe`) | yes, as its own 2nd callback parameter | no -- a listener may itself call `abort()` or react, but nothing forces it to |
| `transformContext` | yes | no |
| provider stream (`streamFunction` options) | yes | no -- the PROVIDER chooses whether to honor it and represent `stopReason: "aborted"`; if it does not, the run proceeds normally with whatever the provider actually returned |
| `beforeToolCall` | yes | only via the two explicit preflight polls (steps 4 and 6 above) -- NOT during the hook's own execution |
| tool `execute()` | yes, as its 3rd positional parameter | no -- the tool's own cooperative choice entirely; Pi does not interrupt it |
| `afterToolCall` | yes | no -- always runs to completion regardless of abort state |
| per-batch (sequential/parallel) | n/a (batch-level, not per-consumer) | yes, but only between calls -- see the split algorithms above; never mid-call |
| `prepareNextTurn` | yes, via `agent.ts`'s own wrapping closure (`this.signal`, read live at call time, not snapshotted) | no |
| `shouldStopAfterTurn` | yes, via the SAME wrapping-closure pattern | no -- the callback MAY itself return `true` to stop the run, but the loop does not force this from the signal alone |
| `getSteeringMessages`/`getFollowUpMessages` | NO -- these are plain queue-drain closures with no signal parameter at all | n/a |
| `agent_end` listeners | yes (same as any lifecycle listener) | no -- listener settlement completes normally; `waitForIdle()` still resolves only after they finish |

**The load-bearing rule the revision-1 draft never stated explicitly: every consumer above may
IGNORE the signal, and if every one of them does, the run completes exactly as if `abort()` had
never been called.** Abort is a REQUEST/hint threaded everywhere, not a guarantee of any particular
outcome by itself. Two DISTINCT provider-facing observable outcomes must be kept separate:

```text
(a) represented provider "aborted" terminal (already Layer-08-owned):
    the underlying stream honors the signal and its OWN `response.result()` carries
    stopReason: "aborted" -- runLoop's existing represented-error/aborted short-circuit
    (agent-loop.ts:196) handles this; no new Layer-09 code needed for this path itself.

(b) exception-after-abort (Layer-08 `handleRunFailure` shape, Layer-09-classified):
    if ANY exception escapes ordinary run execution (a listener throwing, an adapter
    breaking its own streaming contract, or any other unforeseen failure) while
    abortController.signal.aborted happens to be true AT THE MOMENT `runWithLifecycle`'s
    own catch runs (agent.ts:504-505), the synthesized failure message is classified
    stopReason: "aborted" instead of "error" -- purely from the signal's CURRENT state at
    catch time, with NO causal requirement that the exception was actually caused by the
    abort. An unrelated exception that happens to race after a bystander abort() call is
    still classified "aborted", not "error". This is Pi's own actual behavior, not
    something Layer 09 gets to redesign for tidiness.
```

Also distinguish, for completeness of the matrix:

- a cooperative tool that itself throws or returns normally after observing the signal is
  ordinary, already-certified Layer-06 execute/finalize semantics -- `afterToolCall` still runs
  (see above);
- abort requested WHILE `agent_end` listeners are still being awaited: the signal is already
  aborted (or becomes aborted mid-dispatch), but listener settlement for that already-in-flight
  `agent_end` dispatch still completes normally before the Agent becomes idle.

### Signal lifetime and identity

One `AbortController` (and therefore one `.signal` object) per run, created at the very start of
`runWithLifecycle` (`agent.ts:491`) and used, unchanged, for that run's ENTIRE lifetime -- including
through `handleRunFailure`'s own recovery dispatch and `agent_end` listener settlement. `Agent.signal`
(the public getter) returns `undefined` once `finishRun()` clears `activeRun`, which happens in a
`finally` block AFTER the run's own promise resolves -- i.e., after `agent_end` listeners have
settled, matching `waitForIdle()`'s own resolution point exactly. A caller cannot observe a "stale"
signal from a PRIOR run: `Agent.signal` either reflects the CURRENT active run or is absent.

## Ownership matrix (proposed, for review)

| Layer | Owns | Change needed |
|---|---|---|
| 07 (Agent state/inbox, CLOSED) | N/A, explicitly deferred | none -- `AgentInstance` gains a NEW per-run signal/controller pair, additive |
| 08 (Agent Loop, CLOSED) | run/turn orchestration | ADDITIVE: thread a real per-run signal object through `_execute_run`/`_run_inner`/`_run_step`, matching every `signal` parameter position `agent-loop.ts` has; wire the batch-truncation checkpoints into `_run_step`'s own tool-batch call |
| 06 (Tool execution, CLOSED) | `execute_call`/hooks/batch | ADDITIVE: Rust already reserved the seam (`ToolExecutionSignal`); Python needs the equivalent -- a new `ToolFn` third positional parameter, matching `execute.py`'s existing arity-detection convention for `on_update` |
| 02 (LLM, CLOSED) | provider streaming | ADDITIVE, RESOLVED (see below): `LlmService.stream()`/`Adapter.stream()` gain an optional cancellation-signal capability, owned by Layer 09 as a post-certification delta, NOT a Layer-02 semantic reopen. |
| 05 (Tools model/registry, CLOSED) | `ToolDefinition` | none directly -- the `ToolFn` type alias lives in `tools/definition.py` (Layer 05-owned module) but the signal parameter is Layer 06/09 BEHAVIOR, matching the existing `on_update` precedent (Layer 05 owns the shape's existence, Layer 06/09 owns whether/when it's realized) |

### Lower-layer decision — Layer-02 signal capability: additive delta, no reopen, no escalation (RESOLVED)

Independently reviewed and settled, not merely Claude's own reading:

```text
optional LLM cancellation-signal capability
    ADDITIVE POST-CERTIFICATION DELTA, OWNED BY LAYER 09

Layer-02 semantic contract reopen
    NO

owner escalation under process/agent-workflow.md §11.7
    NO
```

Reasoning (from the independent review, adopted here as the governing rule): `AG-007` already
explicitly defers active propagation to Layer 09; `PROV-004` already records adopted
transport-abort parity for the later real-provider phase; the certified Layer-02 contract governs
NON-CANCELLED stream vocabulary/settlement and does not prohibit an optional signal capability;
omitting the new capability preserves every existing caller and every existing non-cancelled
behavior exactly, the same "default preserves certified behavior" shape Layer 08 PASS 6 already
used for `on_execution_start`/`on_execution_end`.

The shared contract specifies the LANGUAGE-NEUTRAL rule -- one optional active-run signal reaches
the generic LLM request/adapter seam -- not Python's exact method signature. Rust may add an
optional signal to its typed `LlmRequest`/adapter boundary; Python may use an optional keyword
argument or an optional `Request` field; either satisfies the contract. Both require Layer-02
REGRESSION evidence (existing Layer-02 tests/canonical scenarios re-run green, confirming the new
optional capability changes nothing when absent) and manifest traceability, but NOT a Layer-02
semantic re-certification.

**Scope boundary: ACTUAL transport cancellation remains deferred to `PROV-004`** (or an explicitly
later real-provider phase) unless a concrete provider adapter is explicitly brought into THIS
layer's own scope. Layer 09 may certify generic signal PROPAGATION (the signal reaches the
adapter-call boundary, correctly, for every already-certified scripted/mock adapter) using a
discriminating scripted adapter that observes/records whether it received an aborted signal --
but must not claim that any real network transport was actually cancelled, since no real transport
exists in this project yet.

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

## Findings

```text
PI_BEHAVIOR_UNCERTAIN   none -- pinned Pi source read directly and fully for every signal
                        checkpoint in agent.ts/agent-loop.ts, independently re-confirmed by the
                        revision-1 review; no ambiguity found in Pi's own behavior itself

CONTRACT_ASSURANCE_DEFECT (revision 1, remediated this revision)
    L09-C001   parallel tool-batch abort polling/truncation timing was described identically to
               sequential, losing the preflight-sequential/execution-parallel distinction and the
               "retained closures still start after the poll" rule -- remediated: split algorithm
               sections above, plus the A/B/C discriminating witness reproduced verbatim from the
               review as the required regression basis
    L09-C002   preflight abort/error priority was stated as a single rule ("abort short-circuits
               preflight") without the full six-outcome priority order -- remediated: complete
               ordered priority matrix above (unknown tool / prepare-validate throw / hook throw
               all beat abort; only a returning hook or no hook yields to "Operation aborted")
    L09-C003   no single complete signal-consumer/settlement matrix existed; `prepareNextTurn` was
               omitted from the concrete table, the "every consumer may ignore abort and the run
               completes normally" rule was never stated, and represented-aborted vs.
               exception-after-abort vs. cooperative-tool-after-abort vs.
               abort-during-agent_end-settlement were not distinguished -- remediated: complete
               matrix, explicit ignore-abort rule, and the four-way distinction, above

LOWER-LAYER REOPEN     not required -- Layer-02 signal capability is an additive Layer-09-owned
                        delta (see "Lower-layer decision" above), independently confirmed, no
                        owner escalation needed

OPEN DESIGN QUESTION    none remaining from revision 1
```

## Next action

Return this exact remote candidate (this revision) for a TARGETED checkpoint re-review against
`L09-C001`/`L09-C002`/`L09-C003` specifically, per `process/agent-workflow.md` §4.1's own checkpoint
flow. Do not begin Python implementation until that re-review closes the three findings above. This
is still a checkpoint, not cross-language certification, and does not authorize Rust implementation
either. Per the review's own required remediation item 6: the discriminating witnesses in this
revision (the parallel A/B/C trace, the six-outcome preflight priority matrix, the consumer-matrix
distinctions) must become planned canonical scenarios or explicit language tests during Python
implementation, not only prose -- noted here for the implementation pass, not attempted in this
checkpoint revision.
