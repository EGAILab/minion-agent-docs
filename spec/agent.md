# Agent Semantics

This document spans two assurance layers over one master-phase surface (pinned Pi's
`packages/agent/src/agent.ts` + `agent-loop.ts` + `types.ts`): **Layer 07 — Agent public state and
inbox/queues** (below) and **Layer 08 — the run/turn state machine** (the rest of this document,
self-certified pending independent Rust contract review). The split exists because Layer 07's
primitives had to be stable enough for Layer 08 to consume without redesign, and because "agent
state and queues behave like Pi" was too coarse a requirement to test independently
(`AG-011`..`AG-019`; `AG-001`..`AG-010`/`AG-020`..`AG-022` are Layer-08-owned, specified in that
section below -- `AG-007` alone remains Layer-09-owned and deferred). The Layer-07 section below
predates Layer 08's own implementation and still describes some Layer-08 state ownership as future
work for historical/scope-boundary reasons (which layer owns WHICH field never changed); where it
does, a forward reference to the Layer 08 section's own current description resolves it -- Layer 07
itself does not re-certify Layer 08's behavior, and this document's Layer 08 section is the sole
normative source for that layer's own current state.

## Layer 07 — Agent public state and inbox/queues

### Ownership

Layer 07 defines:

- the complete `AgentState` public-field disposition (below), including the Agent's public
  processing-status vocabulary and mutable per-instance current configuration;
- steering-inbox and follow-up-inbox storage, independent of each other, accepting pinned Pi's
  whole message domain;
- the enqueue operations and the primitive claim (drain) operation, including both of pinned Pi's
  claim policies, exposed at the Agent-instance level as well as the underlying `Inbox`;
- queue-clearing operations, also exposed at the Agent-instance level;
- in-place instance reset;
- the local invariants those primitives guarantee (order, independence, no invented or duplicated
  input).

Owned by Layer 08, not Layer 07 (specified in the Layer 08 section below, not here):

- the run/turn/step state machine itself (`agent_start`/`turn_start`/`turn_end`/`agent_end`
  ordering, already described below in this same document, pre-dating the Layer-07/08 split and
  not re-scoped by it);
- *when* the loop calls the claim primitive for steering vs. follow-up (before the first request,
  after a turn's tool calls, only when otherwise stopping, etc.);
- `prompt()`/`continue()` caller-rejection rules while a run is active;
- `shouldStopAfterTurn`/`prepareNextTurn` orchestration and steering-vs-follow-up priority during a
  run;
- exactly when/how `is_streaming`/`streaming_message`/`pending_tool_calls`/`error_message`
  transition during a run (Layer 07 owns their vocabulary and initial values only -- see below; the
  Layer 08 section's own "Runtime-state transition timing" describes their current transitions).

Deferred to Layer 09: abort/cancellation propagation into an active run, its providers, tools, and
hooks. Layer 07 does not define or touch any cancellation primitive.

### Authority map

Every pinned Pi `AgentState` field, with its current owner and its transition owner:

```text
Field               Current-value authority          Transition owner
system_prompt       AgentInstance (mutable)           L07 (caller-driven, no run needed)
model               AgentInstance (mutable)           L07 (caller-driven, no run needed)
thinking_level       AgentInstance (mutable)           L07 (caller-driven, no run needed)
messages             SessionLog (L03) via projection   L03 append / L07 public view
tools                ToolRegistry (L05) via projection L05 register/withdraw / L07 public view
is_streaming         AgentInstance.status              L08 (run/turn lifecycle timing)
streaming_message    AgentInstance (vocabulary only)   L08 (see Layer 08 section below)
pending_tool_calls   AgentInstance (vocabulary only)   L08 (see Layer 08 section below)
error_message        AgentInstance (vocabulary only)   L08 (see Layer 08 section below)
```

This table exists so Layer 08 does not reopen state ownership later: every field above already has
a home and a type; Layer 08's own job was to decide *when* to write to the ones it transitions,
using the primitives this layer already defines, not to redesign where they live -- the Layer 08
section below is the normative source for those current write points.

### Mutable per-instance current configuration

Pinned Pi's `AgentState.systemPrompt`/`model`/`thinkingLevel` are directly assignable properties on
the live state object `Agent.state` returns -- `agent.state.systemPrompt = "..."` immediately
mutates that one Agent's own current value, read by every subsequent run, distinct from whatever
default the Agent was constructed with. This is genuinely owned by Layer 07, not deferred to a
later provider/orchestration layer: pinned Pi mutations are observable and take effect for
subsequent runs regardless of whether anything has consumed them yet, so the state and its mutation
surface exists independent of Layer 08's own timing for reading it (Layer 08 now does, per its own
"Run-start snapshot" section below).

Minion keeps the existing frozen, shared `AgentDefinition` (definition defaults, `AG-014`) and adds
a mutable *current* value per instance: `system_prompt`, `model`, and `thinking_level` (pinned Pi's
own seven-value `ThinkingLevel` union, adopted verbatim), each initialized from the definition's own
default and freely reassignable afterward. Mutating one instance's current configuration never
affects a sibling instance created from the same definition, nor the definition itself -- the
definition remains the shared, immutable default; only the instance's own current value changes.

### Public processing status

Pinned Pi's `AgentState.isStreaming: boolean` -- true from the moment a run starts until its
`agent_end` listeners have all settled -- is represented as a two-value status (idle/running), not
a boolean. This is `adopted`, not an architectural adaptation that changes the observable semantic:
it is a lossless, direct representation of the same two-value fact (`running` <-> `true`, `idle` <->
`false`), and a third status value would give the signal more than one meaning. A live instance
starts idle. Layer 07 owns the vocabulary and its initial value; the precise moments a run flips
this to running and back are Layer-08 territory, driven by turn/step lifecycle timing the Layer 08
section's own "Runtime-state transition timing" now specifies.

Pinned Pi's remaining runtime-state fields -- `streamingMessage` (the current partial assistant
message), `pendingToolCalls` (tool-call ids currently executing), and `errorMessage` (the most
recent failed/aborted turn's error) -- have their vocabulary and initial values represented here:
`None`/empty/`None` respectively, matching pinned Pi's own `undefined`/empty-`Set`/`undefined`
initial state exactly. Their *transitions* are Layer 08's own -- see that section's own
"Runtime-state transition timing" below for the current, normative write points.

Pi's own two *active-run-lifecycle* `isStreaming` transition points, recorded here as a reference
for Layer 08 (which reproduces both exactly, not owned by Layer 07): a call to `prompt()`/
`continue()` sets it `true` before anything else happens (`runWithLifecycle`), and `finishRun()` --
reached from a `finally` block, so it runs whether the run succeeded, threw, or was aborted --
unconditionally sets it back to `false` as its very first statement. Layer 08 reproduces both write
points exactly (entry: unconditional; exit: unconditional-via-`finally`, never skipped by an error)
using the `AgentStatus` vocabulary and `AgentInstance.set_status` primitive this layer already
provides -- no different mechanism was needed.

Two other, non-run-lifecycle code paths also assign `isStreaming` in pinned Pi, and Layer 07 (not
Layer 08) already owns both: construction (`createMutableAgentState`'s own initial value is
`false`, matched here by a live instance starting `AgentStatus.IDLE`) and `reset()` (which sets it
back to `false` unconditionally when idle, matched here by `AgentInstance.reset()` -- see "Reset"
below). A second independent Rust review correctly caught an earlier draft of this section
overclaiming "no other code path ever assigns `isStreaming`," which was true only of the
active-run lifecycle specifically, not of pinned Pi's `AgentState` as a whole.

### Messages and tools: public projections, not duplicate stores

Session (Layer 03, certified) remains the sole authority for conversation history, and the
certified Layer-05 `ToolRegistry` remains the sole authority for tool visibility; Layer 07 never
stores either itself.

Pinned Pi's `state.messages` getter returns the *live* backing array (mutable in place by a caller
holding the reference); assignment (`state.messages = [...]`) shallow-copies. Minion's Agent
`messages` is instead a fresh projection (`derive_messages` over the instance's own `SessionLog`) on
every read, never a live mutable reference -- an intentional, disclosed divergence from Pi's own
live-read semantics: `SessionLog` is append-only by design (an already-certified Layer-03 property),
and a live, externally-mutable array would let a caller corrupt history outside the log's own
controlled append path, which Layer 03 does not permit.

Pinned Pi's `state.tools` getter/setter follows the same live-read/copy-on-assign pattern. Minion
does not build a parallel tools store to mirror it: the certified `ToolRegistry` already answers
"what tools are visible from this scope" directly, and `AgentInstance.tools` is a concrete,
Agent-level accessor for exactly that query -- a fresh `ToolRegistry.visible_from(self.scope.key)`
projection on every read, mirroring `messages` above (a second independent Rust review caught an
earlier draft claiming this projection was the Agent's public tools surface without any such
accessor actually existing on `AgentInstance` itself). Wholesale replacement the way
`state.tools = [...]` performs it is still not reproduced; visibility changes happen through the
already-certified `ToolRegistry` register/withdraw API instead, an already-settled Layer-05
divergence this layer does not revisit.

`AgentInstance.tools` is total: a valid, freshly constructed instance always answers this query,
even when no `tools` service has been mounted in its context at all. It returns `()` in that case
rather than raising -- pinned Pi's own `AgentState.tools` starts as an observable empty array
unconditionally, and a third independent Rust review correctly caught an earlier draft treating
"no tool source has been wired up yet" the same as an outright resolution failure, which no other
`AgentState` field does either.

### Steering and follow-up inboxes

Pinned Pi keeps exactly two per-instance queues -- a steering queue and a follow-up queue -- each
holding messages in enqueue order. Minion generalizes the same two queues under one storage
primitive addressed by a two-valued target (a design already established independent of this
layer): the steering queue is the target claimed at a **step** boundary; the follow-up queue is the
target claimed when a **turn** opens. `steer()` and `follow_up()` are exactly pinned Pi's two
enqueue operations under this vocabulary, exposed at the Agent-instance level
(`AgentInstance.steer`/`.follow_up`), not only on the underlying `Inbox` -- pinned Pi's own public
surface is `Agent.steer()`, and Minion's equivalent public surface must be the Agent, not an
internal storage detail. A third operation, silent injection (`AgentInstance.inject`), enqueues to
the same step-boundary target as steering but never signals that new work has arrived -- an
**intentional Minion architectural extension** pinned Pi does not define, for ambient context that
should ride along with whatever else wakes a step but must not itself start one.

Accepted message domain: pinned Pi's `steer`/`followUp` each accept the whole `AgentMessage` union.
`CustomAgentMessages` (the union's app-extensible half) is empty in pinned Pi itself, so the actual,
complete domain is exactly `Message` (`UserMessage | AssistantMessage | ToolResultMessage`, the
already-certified Layer-02 vocabulary) -- adopted verbatim, not narrowed to any one role. Enqueuing
never normalizes, rejects, reorders, or otherwise interprets the message; it is stored exactly as
given, tagged with an opaque, JSON-safe provenance value the runtime never inspects.

This same `AgentMessage` domain is the one accepted boundary-wide, not a coincidence specific to
the two queues: pinned Pi's `Agent.prompt(message: AgentMessage | AgentMessage[])` (its typed
overload, distinct from the convenience `prompt(text: string)` overload) accepts it too. The
queues, `prompt()`'s typed overload, and the certified Layer-02 `Message` union are the same one
type, not three coincidentally-compatible ones; Layer 07 does not invent a fourth, broader
"Agent-level message" type above `Message` for this. Conversion to the wire-level LLM request
(`convertToLlm`, folding `AgentMessage[]` down to provider-ready `Message[]`) is unrelated,
already-certified Layer-02/Layer-04 territory this layer does not touch or duplicate.

### Claim (drain) semantics

Pinned Pi's `QueueMode` is exactly two values -- `"all"` (drain and return every queued message at
once) and `"one-at-a-time"` (drain and return only the oldest, leaving the remainder queued for a
future claim) -- one independently configurable mode per queue, defaulting to `"one-at-a-time"`.
Minion's claim primitive reproduces this exactly: a claim under the "drain everything" policy
empties the target and returns every message that was queued, in enqueue order; a claim under the
"one at a time" policy removes and returns only the single oldest message, leaving the rest queued
for whatever claims that target next. Claiming an empty target returns nothing and is not an error.
A claim never invents input that was not queued, and claiming from one target never observes or
disturbs the other.

*When* a claim happens, and which policy governs a particular boundary at runtime, is Layer 08's
decision; Layer 07 guarantees only that the primitive itself behaves exactly as described above,
whichever policy and whichever boundary Layer 08 chooses to invoke it for.

### Clearing

Pinned Pi's `clearSteeringQueue()`/`clearFollowUpQueue()` each discard everything queued at their
own target, leaving the other untouched; `clearAllQueues()` discards both. `hasQueuedMessages()` is
true exactly when at least one of the two targets still holds unclaimed input. All four are exposed
at the Agent-instance level (`AgentInstance.clear_steering_queue`/`.clear_follow_up_queue`/
`.clear_all_queues`/`.has_queued_messages`), delegating to the underlying `Inbox`, for the same
public-surface reason `steer`/`follow_up` are. Clearing a target that already has nothing queued is
a harmless no-op. Clearing is orthogonal to the wake/settle signal (below) a host driver uses to
decide when to poll a target at all -- Layer 07 defines only the queue-content effect, not any
interaction with that signal.

`wake_requested`/`take_wake` (on `Inbox`) are an **intentional Minion architectural extension** with
no Pi counterpart at all -- kept explicitly separate from every adopted rule above, not folded into
one of them, since pinned Pi has nothing for it to be parity *with*.

### Reset

Pinned Pi's `Agent.reset()` is a public, **in-place** operation: it rejects outright
(`"Agent is already processing. Wait for completion before resetting."`, exact text) while a run is
active, with no partial mutation on rejection. When idle, it clears `messages`, `isStreaming`,
`streamingMessage`, `pendingToolCalls`, and `errorMessage`, and both queues -- and retains
`systemPrompt`, `model`, `thinkingLevel`, `tools`, queue modes, listeners, and Agent object
identity. It mutates the existing object; it never constructs a replacement.

Minion's `AgentInstance.reset()` reproduces this in place: the same `Inbox`/`SessionLog`/scope
objects survive reset, only their content changes, and the exact rejection text/atomicity are
preserved, including clearing `messages`. An earlier pass concluded `SessionLog`'s append-only
design (no truncate/clear primitive) made `messages`-clearing an unresolvable Layer-03 dependency
and left it unreproduced; a second independent Rust review correctly rejected that conclusion by
pointing at an already-certified mechanism that pass had overlooked:
`session/operations.py::reset(log)` appends a `session/reset` marker event rather than truncating
anything, and `derive_messages` already treats the latest such marker as an exclusive floor. Calling
this existing, certified Layer-03 operation from `AgentInstance.reset()` clears the projection
exactly as Pi does, without adding any new primitive to `SessionLog` and without altering Layer 03's
own certified semantics at all -- the full event history remains intact underneath for audit, only
the model-facing projection changes.

Reset's relationship to the wake signal is specified normatively, not left implicit: a pending
`Inbox.wake_requested`, if any, is **not** cleared by `reset()`. Wake and queued content are
orthogonal concerns (see "Clearing" above), and pinned Pi has no wake concept to constrain this
choice either way; a wake that arrived before a caller reset an idle instance still describes a
real, unconsumed signal, so it is preserved rather than silently discarded as an incidental
consequence of delegating to `clear_all()`.

## Layer 08 — the run/turn state machine

Normative, current-state contract (last rewritten PASS 4). This section describes ONE coherent
Layer-08 semantic contract as it stands today, verified directly against pinned Pi
(`agent-loop.ts`/`agent.ts`/`types.ts`). It does not narrate how the implementation evolved across
passes; that history -- including two independent Rust review rejections and their remediation --
lives in `assurance/layers/08-agent-loop-python.md`, not here. A normative section and an assurance
history section serving different readers with different needs is deliberate: Rust review must be
able to trust this section alone as the target to implement against, without cross-referencing which
claims are current and which are historical narrative.

### Run/turn vocabulary and event boundaries

A run is one high-level `prompt()`/`continue()` invocation, bracketed by `agent_start`/`agent_end`.
A turn is one assistant response plus the tool calls/results it triggers -- never more than one
provider request -- bracketed by `turn_start`/`turn_end`. Confirmed directly against
`runAgentLoop`/`runLoop` (agent-loop.ts): `turn_start`/`turn_end` never span more than one provider
request in pinned Pi. `AGENT_START`/`TURN_START` fire in that order, before any message entering the
run/turn is logged, matching pinned Pi's own `runAgentLoop`/`runLoop` order.

`agent_end.messages` is pinned Pi's own invocation-local field: every message this run itself
produced or consumed, in order, reset at each `AGENT_START` -- never the whole transcript. `turn_end
{message, toolResults}` is likewise scoped to that one turn's own messages, never a second,
independently-logged copy of the same content. `causes` (which queued input triggered processing)
is a disclosed Minion enrichment scoped to the run, not each turn within it -- pinned Pi's own bare
`turn_start`/`agent_start` carry no fields at all.

The complete post-turn ordering, confirmed directly against `runLoop`'s own body
(agent-loop.ts:161-245):

```text
turn_end -> prepareNextTurn -> shouldStopAfterTurn -> steering poll -> follow-up poll (only if
otherwise stopping)
```

`prepareNextTurn` (`agent/prepare-next-turn`, waterfall, terminal a no-op `RunConfigUpdate()`) may
return a WHOLE replacement `context` (pinned Pi's own `AgentLoopTurnUpdate.context: AgentContext`,
`currentContext = nextTurnSnapshot.context ?? currentContext` -- a whole-object swap via `??`, never
a per-field merge) plus independently optional `model`/`thinking_level` replacements (the same
`"off"`-vs-`undefined` special case already certified at `AG-014`), applying to the *next* provider
request only, on a run-local snapshot (below) -- never persisted back to `AgentInstance`. Both
`prepareNextTurn` and `shouldStopAfterTurn` listener signatures mirror pinned Pi's own
`PrepareNextTurnContext`/`ShouldStopAfterTurnContext` exactly: `(message, tool_results, context,
new_messages)`. Both are dispatched after every turn, including one a tool batch's unanimous
`terminate` verdict ended -- `terminate` only ever affects `hasMoreToolCalls` (whether the
tool-driven inner loop has more work), never this ordering, confirmed directly against `runLoop`.

A represented `error`/`aborted` assistant message is the one turn-ending case this ordering does NOT
apply to: pinned Pi checks `stopReason` immediately after `streamAssistantResponse` returns and, for
`"error"`/`"aborted"`, emits that turn's own `turn_end` with empty `toolResults` and returns
immediately -- running none of `prepareNextTurn`/`shouldStopAfterTurn`/the steering or follow-up
poll for that turn, and inspecting/executing no tool calls even if the response happened to include
tool-call content (agent-loop.ts:196-200). `agent_end.messages` for this case still uses the run's
own ordinary invocation-local accumulator (`newMessages`) -- this is a normally-produced message,
distinct from `handleRunFailure`'s own synthesized failure (below).

No turn-count cap exists on this ordering or on how many turns one run may take: pinned Layer 08 has
no `max_steps`-equivalent stop rule, and Minion has none either -- a `prompt()`/`continue()` run
continues for as many turns as the model actually requests.

### `prompt()`/`continue_()`: the public run entry points

`AgentLoop.prompt(message)` and `AgentLoop.continue_()` (`continue` is a Python keyword) reproduce
pinned Pi's `Agent.prompt()`/`Agent.continue()` exactly, confirmed directly against source
(agent.ts:348-407):

- `prompt()` rejects with pinned Pi's exact text ("Agent is already processing a prompt. Use
  steer() or followUp() to queue messages, or wait for completion.") while a run is active;
  otherwise starts a new run with the given message(s) as its own entering prompt. Accepts either
  the typed `Message | tuple[Message, ...]` boundary, or pinned Pi's own convenience overload -- a
  plain `str`, optionally with `images` -- normalized into exactly one `UserMessage` whose content
  is `[{type:"text",...}, ...images]`, text first then the supplied images in order. The convenience
  form is an ADDITIONAL accepted form, never a narrowing of the typed one; both coexist.
- `continue_()` rejects with its own, different exact text ("Agent is already processing. Wait for
  completion before continuing.") while active, and "No messages to continue from" on an empty
  transcript. When the transcript's last message is assistant: drains eligible steering (skipping
  this run's own initial steering poll, so the same batch is never claimed twice -- pinned Pi's
  one-shot `skipInitialSteeringPoll`), else eligible follow-up, else rejects with "Cannot continue
  from message role: assistant". Both the steering-drain and follow-up-drain sub-cases route
  through the *pre-seeded* path (pinned Pi's own `runPromptMessages`, not `runAgentLoopContinue`),
  confirmed directly against source -- a real, easy-to-miss distinction from the third case.
  Otherwise (last message not assistant): a plain continuation, no entering messages, full history
  still sent to the model (pinned Pi's `runAgentLoopContinue`, empty-seeded `newMessages`).

A third, distinct "already processing" string (pinned Pi's own `runWithLifecycle` internal guard,
"Agent is already processing.") guards run entry itself, defensive against a caller bypassing
`prompt()`/`continue_()`'s own public checks -- normally unreachable under ordinary single-caller
use, kept for the same reason pinned Pi keeps it. All four "already processing" strings across the
certified surface (`prompt()`'s, `continue_()`'s, this internal guard's, and the already-certified
Layer-07 `reset()`'s) are distinct, never consolidated into one shared message.

### Run-start snapshot and whole-context replacement

Pinned Pi's `Agent.createContextSnapshot()`/`createLoopConfig()`: at run start, `RunContext
{system_prompt, messages, tools}` and `RunConfig{model, thinking_level}` are each taken ONCE -- a
shallow top-level copy (`messages`/`tools` are each a fresh top-level list/tuple, never a deep
clone) -- into a run-local snapshot, never re-read from the certified Layer-07 `AgentInstance`,
Session, or `ToolRegistry` for the rest of that run. A caller mutating the instance mid-run, or an
unrelated external tool registration reaching the live `ToolRegistry` while this run is in flight,
does not retroactively alter a run already in progress. `RunContext.messages`/`.tools` ARE extended
in place as the run's own turns produce them (admitted messages, and tool results naming
`added_tool_names` the run's own execution just registered -- resolved only for those specific
names, through the real registry, never a general live reread) -- this is the run's own local
growth, not a leak from outside it. `prepareNextTurn` may still replace the whole snapshot
run-locally (above); neither ordinary growth nor a `prepareNextTurn` replacement is ever written
back to `AgentInstance`, and a second, independent run always starts from a fresh snapshot again.

### Initial-turn admission: prompt lifecycle before the steering claim

Pinned Pi's exact first-turn order: `agent_start`, `turn_start`, the initial prompt messages' own
COMPLETE message lifecycle, and only THEN the initial steering poll (`runLoop`'s own first
statement, called only after `runAgentLoop` has already emitted `turn_start` and the prompt
messages' lifecycle) -- confirmed directly against source (agent-loop.ts:95-118, 161).

Minion reproduces this as two explicit, sequential admission stages in `AgentLoop._run_inner`, both
using the same `_admit_messages` helper every other admission point in this layer uses: (1) a
`PreStepReason.INITIAL` decision governs the caller's own entering prompt ALONE, admitted (logged,
dispatched, and accumulated into the run-local snapshot) immediately; (2) only then is the steering
queue claimed, and if non-empty, a SECOND, independent `PreStepReason.STEERING` decision governs the
claimed batch, admitted the same way. Both stages' messages feed the SAME first provider request --
pinned Pi never splits them into separate turns; only their own admission/lifecycle timing is
staged. `continue_()`'s own pre-drain (`skipInitialSteeringPoll`) skips stage (2) entirely, so the
pre-drained batch is admitted once, under stage (1), never claimed a second time.

### Mid-run follow-up continuation

Pinned Pi's outer `runLoop` loop polls the follow-up queue only once the inner loop (turns within
one continuation) would otherwise exit -- no more tool calls, nothing steered -- and, if follow-up
is found, continues the *same* run (`agent_start`/`agent_end` still bracket it) rather than ending.
`AgentLoop._run_inner` is a genuine outer/inner nested loop reproducing this exactly, with the outer
loop claiming follow-up (admitted via the same `_admit_messages` helper) and extending the run's own
`causes` when it does. Minion's own `run_until_idle()` pump (no pi equivalent, `AG-019`) is a thin
caller over this: it still claims one batch and starts one run per claim, but because a run now
drains follow-up internally while open, a single pump iteration typically consumes every queued
batch in one run. The pump's own outer loop remains a safety net for the one case pinned Pi does not
auto-continue either (a `shouldStopAfterTurn` listener stopping the run early while follow-up is
still queued) -- pinned Pi would leave that for an explicit `continue()` call; Minion's pump
substitutes for that automatically, an intentional Minion extension.

### The live Agent-event seam, and `handleRunFailure` through it

Pinned Pi's `Agent.subscribe(listener)` is a public surface delivering the `AgentEvent` union
(`agent_start`/`turn_start`/`message_start`/`message_update`/`message_end`/`turn_end`/`agent_end`,
plus `tool_execution_start`/`tool_execution_end`) LIVE, during the run, through one seam --
`processEvents(event)` -- that first reduces `Agent`'s own internal state for that event, then
awaits every subscribed listener in registration order with no catch around the loop: a listener
that throws aborts the remaining listeners for that event and propagates out of `processEvents`
itself (agent.ts:544-591). `runWithLifecycle`'s own `catch` calls `handleRunFailure` for any
exception the run executor produces -- including one a normal-path listener itself threw --
and `handleRunFailure` delivers its own four-event failure sequence through the SAME
`processEvents` seam (agent.ts:511-527): `message_start(failure)`, `message_end(failure)`,
`turn_end(failure, [])` (no preceding `turn_start`), `agent_end(messages=[failure])`. A listener
throwing during THIS sequence has no further catch around it at all -- the exception propagates all
the way out to the caller of `prompt()`/`continue()`, while `finally { finishRun() }` still settles
`isStreaming`/`pendingToolCalls`/status regardless. `handleRunFailure` explicitly excludes eager,
pre-stream failures (an unresolvable model is a caller/config bug, not a run-executor failure, and
raises immediately, uncaught).

Minion reproduces this via `AGENT_LIFECYCLE_EVENT` (`agent/events.py`, `SERIAL` dispatch mode --
sequential await with no catch around the loop, matching pinned Pi's raw listener loop with no new
primitive needed), the single seam every lifecycle event -- ordinary turn/run progress and
`handleRunFailure` recovery alike -- passes through via `AgentLoop._dispatch_agent_event`, carrying
the COMPLETE `AgentEvent` union, not a partial one:

- every admission point (`_admit_messages`, for the prompt, steering, tool-result, and follow-up
  admission cases above) dispatches its own `MessageStart`/`MessageEnd`;
- the assistant reply's OWN streamed lifecycle is live too: `_run_step` iterates
  `self.llm.stream(request)` directly rather than through the certified Layer-02/04 `collect()`
  convenience wrapper (whose own `on_chunk` callback is synchronous by design and cannot itself
  `await` a dispatch) -- this does not reopen or modify `collect()` itself, still certified, still
  used everywhere else; it reproduces `collect()`'s own trivial drain loop at the one call site that
  needs an async per-chunk dispatch, dispatching `MessageStart`/`MessageUpdate`/`MessageEnd` for
  every chunk;
- Layer-06's own `tools/execution-start`/`tools/execution-end` events (synchronous EMIT dispatch, by
  certified Layer-06 design) are captured in real time -- the moment each one actually fires -- and
  redelivered through this same seam once a tool batch settles, in the exact order Layer 06 emitted
  them (every call's own start always precedes any call's own end, per Layer 06's own certified
  batch structure). This is a disclosed, narrower fidelity than pinned Pi's own live blocking
  dispatch for this one event pair specifically: a slow Minion listener cannot causally delay a
  specific tool call's own further progress the way a slow pinned Pi listener could, since
  Layer-06's EMIT dispatch mode is certified and this section does not reopen it;
- `AgentStart`/`TurnStart`/`TurnEnd`/`AgentEnd` are dispatched at their own points as before.

`_settle_run_failure` (pinned Pi's `handleRunFailure`) is `async` and dispatches its own four-event
sequence through this SAME seam, in the same order, letting a thrown listener propagate uncaught
exactly as pinned Pi does. Reduce, THEN dispatch, per event -- matching pinned Pi's own
`processEvents` order exactly, for every event, not only the assistant's own streamed one:
`streaming_message` is set to the message at `message_start` and cleared at `message_end` (pinned
Pi's own reducer does not distinguish a streamed reply from a plain admitted message); the durable
transcript entry for a message is appended at `message_end` time, not before `message_start`'s own
dispatch; `error_message` is set as part of `turn_end`'s own reduce, before that event's own
dispatch. An interrupted sequence therefore durably records exactly what pinned Pi's own reducer
would have committed up to and including the event whose listener threw, and nothing after it.
`AgentLoop._run_wrapped` mirrors pinned Pi's own `runWithLifecycle`/`finishRun` unconditional state
writes exactly: `streaming_message`/`error_message` reset at entry; `streaming_message`/
`pending_tool_calls` reset at exit, via `finally`, regardless of success or failure.
`UnknownModelError` remains explicitly excluded and re-raised uncaught, matching pinned Pi's own
eager boundary.

### Active abort propagation (explicitly out of scope)

Pinned Pi's `abort()` actively signals the running provider/tools/hooks. Idle is reached only after
terminal run settlement and awaited `agent_end` listeners -- Layer 09's territory, per the
already-certified Layer-07 contract's own deferral. Not attempted by Layer 08 at all:
`handleRunFailure` above settles an aborted/failed turn correctly once it arrives, without itself
implementing any provider, stream, tool, hook, or transport abort-signal propagation. Layer 08 has
no local cancel/boundary-stop mechanism of any kind: a prior revision of this section documented one
(`request_boundary_stop()`, renamed from `cancel()`), but it was removed entirely rather than kept
and approved -- a public method that could alter a Pi-equivalent run's own observable outcome had no
owner governance approval for that divergence, and no demonstrated product need justified keeping
it, the same default this project already applied to `max_steps` (above). If a host-only safety
mechanism is ever needed, it must sit entirely outside a single Pi-equivalent run's own semantic
behavior -- limiting a HOST's own repeated scheduling/invocation policy across independent runs,
never truncating or altering one run's own outcome internally.

### Runtime-state transition timing

`is_streaming`: flips per pi-equivalent run (`AgentLoop._run_wrapped`), matching pinned Pi's own
`runWithLifecycle`/`finishRun` write points exactly -- once per `prompt()`/`continue()` invocation,
not once per `run_until_idle()` pump iteration.

`streaming_message`: non-`None` for exactly the duration of one provider request, matching pinned
Pi's own `message_start`/`message_update` -> partial, `message_end` -> `None` write points, with
FULL content fidelity -- text, thinking, and tool-call construction alike -- set directly from each
stream chunk's own already-complete `partial` (the certified Layer-02/04 `StreamChunk` carries a
complete `partial: AssistantMessage` on every variant; no independent reconstruction from raw deltas
is attempted). Pinned Pi's own reducer does not distinguish the assistant's own streamed reply from
any other admitted message: `streaming_message` is set (briefly, non-streamed) to EVERY message at
its own `message_start` and cleared at its own `message_end`, whether that message is the assistant
reply, an admitted prompt/steering message, a follow-up, or a tool result -- reproduced uniformly at
every admission point ("Initial-turn admission" above) and every message emitted by `_run_step`.

`pending_tool_calls`: real per-call tracking (add on start, remove on end) through the
already-certified Layer-06 `tools/execution-start`/`tools/execution-end` events -- an existing
seam, not a new one -- matching pinned Pi's own `processEvents` reducer exactly.

`error_message`: set from a turn's own failed/aborted assistant message (`error_message`, when
truthy) and, distinctly, NOT cleared at that same run's own `agent_end` -- it persists across an
idle period after a failed run, cleared only at the *next* run's start or via the already-certified
Layer-07 `reset()`, exactly matching pinned Pi (`finishRun` never touches `errorMessage`; only the
next `runWithLifecycle` entry does).
