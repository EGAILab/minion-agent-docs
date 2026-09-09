# Agent Semantics

This document spans two assurance layers over one master-phase surface (pinned Pi's
`packages/agent/src/agent.ts` + `agent-loop.ts` + `types.ts`): **Layer 07 — Agent public state and
inbox/queues** (below) and **Layer 08 — the run/turn state machine** (the rest of this document,
self-certified pending independent Rust contract review). The split exists because Layer 07's
primitives had to be stable enough for Layer 08 to consume without redesign, and because "agent
state and queues behave like Pi" was too coarse a requirement to test independently
(`AG-011`..`AG-019`; `AG-001`..`AG-010` and `AG-021` are Layer-08-owned, specified in that
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

Normative, current-state contract (last rewritten PASS 11). This section describes ONE coherent
Layer-08 semantic contract as it stands today, verified directly against pinned Pi
(`agent-loop.ts`/`agent.ts`/`types.ts`). It does not narrate how the implementation evolved across
passes; that history -- including nine independent Rust review rejections, their remediation, and
the contract-convergence cycle entered after PASS-8's own rejection -- lives in
`assurance/layers/08-agent-loop-python.md` and `assurance/layers/08-agent-loop-contract-
convergence.md`, not here. A normative section and an assurance
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
plus `tool_execution_start`/`tool_execution_update`/`tool_execution_end`) LIVE, during the run,
through one seam -- `processEvents(event)` -- that first reduces `Agent`'s own internal state for
that event, then
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

The synthesized failure's own `api`/`provider`/`model` identity (`L08-R014`) comes from the
Agent's PERSISTENT model -- `this._state.model`, read LIVE at the moment `handleRunFailure`
constructs the failure message (agent.ts:515-517) -- NOT a value captured once and frozen when the
Agent was constructed. This is the Agent's CURRENT persistent model at settlement time, the exact
same value the already-certified Layer-07 "Mutable per-instance current configuration" section
above describes: pinned Pi's own `Agent.state` getter returns the live `AgentState` object, and a
caller may reassign `agent.state.model = "..."` directly at any time, including while a run is
active (`agent.ts` itself never performs this reassignment internally -- there is no
`this._state.model = ...` statement in the file -- but an external caller reaching through the
public `state` getter can and does, and that mutation is exactly what Layer 07 already adopts as
observable). `handleRunFailure` has no snapshot, cache, or construction-time capture of its own; it
simply reads whatever `this._state.model` currently holds when it runs.

This is a DIFFERENT value from the run-local model a `prepareNextTurn`/`AGENT_PREPARE_NEXT_TURN`
listener may have already replaced for the run currently in flight -- pinned Pi's own
`prepareNextTurn` return value only ever reassigns the LOCAL `config` a single `run()` call keeps
(agent-loop.ts:230-238, `config = {...config, model: nextTurnSnapshot.model ?? config.model}`, a
plain local variable reassignment), never `this._state.model` itself. A caller's own direct
mutation of the persistent model (Layer 07's own adopted surface) is a THIRD, independent source,
and IS visible to failure settlement, since `handleRunFailure` reads `this._state.model` live.

Concretely, three sources, two of which reach `handleRunFailure` and one of which does not:

- a run starting with persistent model A, whose `prepareNextTurn` replaces the RUN-LOCAL model
  with B for a later turn, and which then fails (any listener throwing, an adapter breaking its
  streaming contract, or any other unforeseen run-executor error) after that replacement has
  already landed, still reports failure identity A, not B -- the run-local override never reaches
  `handleRunFailure`'s own source of truth;
- the SAME run, if a caller/listener additionally reassigns the Agent's own PERSISTENT model to C
  (via the adopted Layer-07 mutation surface) at any point before the failure settles, reports
  failure identity C, not A and not B -- the persistent mutation DOES reach `handleRunFailure`,
  because it changed the very value `this._state.model` reads live, unlike the run-local override,
  which changed a different (local) variable entirely.

An implementation that threads the run-local, possibly-already-replaced model into the failure
path is a `PI_PARITY_DEFECT` (reads the wrong source). An implementation that instead snapshots or
caches the persistent model at run start, rather than reading it live at settlement, is ALSO a
`PI_PARITY_DEFECT` -- it would report A instead of C in the second case above, contradicting pinned
Pi's own live read. Only "read `self.instance.model` live, at the moment of settlement, with no
intervening snapshot" matches pinned Pi in both cases.

Minion reproduces this via `AGENT_LIFECYCLE_EVENT` (`agent/events.py`, `SERIAL` dispatch mode --
sequential await with no catch around the loop, matching pinned Pi's raw listener loop) -- the
single seam every lifecycle event -- ordinary turn/run progress and `handleRunFailure` recovery
alike -- passes through via `AgentLoop._dispatch_agent_event`, carrying the COMPLETE `AgentEvent`
union, not a partial one. `SERIAL` dispatch alone was NOT sufficient, discovered in the Layer-08
contract-convergence cycle (`L08-R002`, PASS 9): pinned Pi's own `for (const listener of listeners)
{ await listener(event, signal); }` suspends between EVERY listener, even a fully synchronous one,
because a JS `await` always defers its own continuation by at least one microtask turn regardless
of whether its operand performed real async work -- a property Python's own `await` does not share
when the awaited coroutine never itself genuinely suspends. `AgentLoop._dispatch_agent_event`
therefore passes `EventBus.serial`'s own additive, opt-in `yield_after_each=True` (`runtime/
events.py`, Layer 05 -- see `spec/runtime.md` RT-016), an explicit new per-listener scheduling
boundary, not merely a reuse of the existing `SERIAL` mode's own base semantics:

- every admission point (`_admit_messages`, for the prompt, steering, tool-result, and follow-up
  admission cases above) dispatches its own `MessageStart`/`MessageEnd`;
- the assistant reply's OWN streamed lifecycle is live too: `_run_step` iterates
  `self.llm.stream(request)` directly rather than through the certified Layer-02/04 `collect()`
  convenience wrapper (whose own `on_chunk` callback is synchronous by design and cannot itself
  `await` a dispatch) -- this does not reopen or modify `collect()` itself, still certified, still
  used everywhere else; it reproduces `collect()`'s own trivial drain loop at the one call site that
  needs an async per-chunk dispatch, dispatching `MessageStart`/`MessageUpdate`/`MessageEnd` for
  every chunk;
- `ToolExecutionStart`/`ToolExecutionEnd` are genuinely LIVE, at real execution points, matching
  pinned Pi's own blocking dispatch exactly (Layer 08, PASS 6, closing a gap PASS 5 left open):
  Layer 06's own `tools/execute.py`/`tools/batch.py` gained additive, optional
  `on_execution_start`/`on_execution_end` async hooks, awaited at the EXACT points the existing,
  still-certified `tools/execution-start`/`tools/execution-end` EMIT events already fire --
  `None` (every other caller) preserves Layer 06's own certified behavior exactly, no lower-layer
  contract reopened. A listener failure here genuinely prevents that call's own `execute()` from
  proceeding, and sequential-mode ordering is the real `start A, end A, start B, end B`, not a
  batch-wide capture-and-replay;
- `ToolExecutionUpdate` reaches the same seam too (previously missing from the union entirely),
  genuinely live, correctly non-blocking, and correctly interleaved ACROSS EVERY REGISTERED
  LISTENER (Layer 08, PASS 9, contract convergence -- closing a scheduling-timing gap PASS 7 and
  PASS 8 each narrowed but did not fully close): a tool's own `execute()` calls its
  `update(partial)` callback SYNCHRONOUSLY, an established SDK-level calling convention
  (`_wants_update`, `tools/execute.py`) no Layer-06 caller may redesign out from under every
  existing tool definition -- but pinned Pi's own `tool_execution_update` dispatch is ITSELF not
  awaited inline either: its `update` callback calls `emit(...)`, which -- because JS runs an
  `async function`'s body SYNCHRONOUSLY up to its own first genuine suspension point before
  returning control to its caller at all -- begins listener delivery IMMEDIATELY, at callback time,
  before `update()`'s own caller (the tool) resumes; only once `execute()` itself settles does
  pinned Pi join every one of a call's own pending updates, before
  `finalizeExecutedToolCall`/`tool_execution_end` ever runs (`agent-loop.ts:670-711`).
  `asyncio.ensure_future`/`asyncio.create_task` cannot reproduce the synchronous-start half of this:
  a Python `Task` always schedules its own first step through `loop.call_soon`, DEFERRED to the next
  event-loop iteration (tried in PASS 7). `_execute_and_finalize` instead uses
  `asyncio.eager_task_factory` (stdlib since Python 3.12), which drives the hook's own coroutine
  SYNCHRONOUSLY, in the same call stack, up to its own first real suspension before `update()`
  itself returns.

  That alone is still not sufficient once TWO OR MORE listeners are subscribed to
  `AGENT_LIFECYCLE_EVENT`, discovered in PASS 8's own independent re-review: pinned Pi's own serial
  listener loop (`for (const listener of this.listeners) { await listener(event, signal); }`,
  `agent.ts:544-591`) suspends after EVERY listener, even a fully synchronous one, because a JS
  `await` always defers its own continuation by at least one microtask turn regardless of whether
  its operand performed real async work -- but Python's `await` on a coroutine that itself never
  genuinely suspends completes with ZERO scheduler turns, so `eager_task_factory` alone drove
  PASS 8's own multi-listener dispatch straight through the WHOLE chain before `update()` returned
  (`listener-1, listener-2, tool-continued`, not pinned Pi's own
  `listener-1, tool-continued, listener-2`). `EventBus.serial` (`runtime/events.py`, Layer 05 --
  see `spec/runtime.md` RT-016) gained an additive, keyword-only `yield_after_each: bool = False`
  parameter -- default `False` so every OTHER `serial()` caller's own certified behavior is
  unchanged -- that awaits a single-tick scheduler yield after EVERY listener, unconditionally.
  `AgentLoop._dispatch_agent_event` is the one caller that passes `yield_after_each=True`, for
  `AGENT_LIFECYCLE_EVENT` specifically -- verified empirically, standalone, before integrating it,
  to reproduce pinned Pi's exact multi-listener interleaving for two and three listeners alike.

  Every one of a call's own started update dispatches is still joined (`asyncio.gather`, unwrapped
  by any try/except) immediately after `execute()` settles, before `_finalize`/`tool_execution_end`.
  A listener failure here propagates straight out, uncaught, the SAME causal category as a
  `tool_execution_start`/`tool_execution_end` failure -- `_finalize`/`tool_execution_end` never run
  for that call at all, matching pinned Pi exactly. Two different concurrent calls' own update
  dispatches interleave according to real execution order, and a call stays marked pending
  (`AgentInstance.pending_tool_calls`) for the whole time its own updates are still in flight, since
  `OnExecutionEnd` (which clears it) fires only once they have all resolved;
- `ToolExecutionUpdate.partial_result` is a STRUCTURED `ToolPartialResult`, not a bare string and
  NOT the pipeline-level `ToolResult` either (Layer 08, PASS 11, contract-convergence final review,
  `L08-R011`): pinned Pi's own `AgentToolUpdateCallback<T> = (partialResult: AgentToolResult<T>) =>
  void` (`packages/agent/src/types.ts:361-383`) carries `AgentToolResult<T>` -- `content`/`details`
  required, `usage`/`addedToolNames`/`terminate` genuinely optional, with NO `toolCallId`,
  `toolName`, or `isError` field of its own; call identity already lives on the enclosing
  `tool_execution_update` event (`ToolExecutionUpdate.tool_call_id`/`.tool_name`), and Pi's own
  `execute()` throws on failure rather than encoding an error inside its returned/reported value.
  An earlier revision narrowed `tools/definition.py::ToolUpdate` to `Callable[[str], None]` (a real
  payload reduction pinned Pi does not have), then over-corrected to
  `Callable[[ToolResult], None]` -- reusing the pipeline-level FINALIZED-outcome type and
  normalizing spoofed `tool_call_id`/`tool_name` onto it, observably LARGER than Pi's own type (an
  independent Rust re-review caught this; certified Rust Layer 06 already used the correct,
  narrower shape throughout, so Python was the side needing correction, not Rust).
  `ToolUpdate = Callable[[ToolPartialResult], None]` (`tools/result.py`); `update()`'s own closure
  needs NO normalization at all now, since the type has no identity/error field to normalize away;
- `AgentStart`/`TurnStart`/`TurnEnd`/`AgentEnd` are dispatched at their own points as before, and
  `AgentStart`'s own dispatch plus a successful run's own `AgentEnd` dispatch both live inside
  `_execute_run`'s own exception boundary (Layer 08, PASS 6): a listener failure at either point is
  caught and settled via `_settle_run_failure` the same as any other run-executor failure, not left
  to escape uncaught past `_run_wrapped`'s own `finally`.

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
eager boundary. The failure `AssistantMessage`'s own `model`/`provider` (`L08-R014`) come from
`self.instance.model`, read LIVE at settlement -- `AgentInstance`'s own CURRENT persistent model,
matching pinned Pi's own live read of `this._state.model` -- never from the run-local `RunConfig` a
`AGENT_PREPARE_NEXT_TURN` listener may already have replaced for the run currently failing;
`_settle_run_failure` takes no `RunConfig` parameter at all, since the run-local config has no
legitimate use in this method. A caller mutating `self.instance.model` directly (Layer 07's own
adopted mutation surface, above) IS visible here, since there is no snapshot in between -- see the
`handleRunFailure` seam section above for the full three-source witness.

### Active abort propagation (Layer 09)

Pinned Pi's `abort()` actively signals the running provider/tools/hooks -- cooperatively, never a
forced interrupt. Full audit and discriminating witnesses:
`assurance/layers/09-active-abort-contract-checkpoint.md`.

**Authority split (`L09-R004`):** `RunSignal`/`RunAbortController` (`runtime/signal.py`, RT-024)
reproduce pinned Pi's own `AbortSignal`/`AbortController` split exactly. `RunAbortController` is
PRIVATE -- held only by `AgentInstance` (as `_active_controller`, no public accessor) and never
handed to a tool, hook, adapter, or lifecycle listener; only `AgentInstance.abort()` may call its
`.abort()`. Every consumer instead receives a `RunSignal` -- pinned Pi's own `AbortSignal` --
which has NO `.abort()` of its own at all: observing the signal never grants authority to trigger
cancellation. An earlier revision handed every consumer the SAME mutable object (so a tool or
adapter could call `.abort()` itself, authority Pi's own type system forbids) and made
`AgentInstance.signal` a plain public attribute any listener could reassign mid-run, redirecting
later requests to a caller-supplied replacement -- an independent Rust review caught both as
observable divergences from Pi (`L09-R004`).

**Public surface:** `AgentInstance.signal: RunSignal | None` -- a READ-ONLY property with no
setter at all, `None` while idle, matching pinned Pi's own `Agent.signal` getter returning
`undefined` with no active run, and returning the SAME `RunSignal` object for a run's entire
duration (never a fresh wrapper per access -- pinned Pi's own "stable per-run identity").
`AgentInstance.abort() -> None` -- a no-op, never raising, when idle; when a run is active, flips
that run's own PRIVATE controller. One NEW `RunAbortController()` per run, created via internal
`_start_run_signal`/`_end_run_signal` methods Layer 08 alone calls (matching pinned Pi's own `new
AbortController()` inside `runWithLifecycle`) -- live for the run's ENTIRE duration, including
`_settle_run_failure`'s own recovery dispatch and `agent_end` listener settlement. `abort()` does
not itself change `status`; `reset()` still rejects until the run has actually settled, exactly as
for a non-aborted active run.

**Signal/status transition ordering (`L09-R007`):** `AgentInstance.set_status` emits `agent/
status` and calls `on_status_change` SYNCHRONOUSLY, so a status-transition observer runs INSIDE
the same synchronous call that publishes `RUNNING`/`IDLE`. `_start_run_signal()` is therefore
called BEFORE `set_status(AgentStatus.RUNNING)`, and `_end_run_signal()` BEFORE
`set_status(AgentStatus.IDLE)` -- the controller must exist before a RUNNING observer could read
`instance.signal` or call `instance.abort()`, and must be cleared before an IDLE observer could
read it, or the observer sees the wrong run's signal state (`None` during RUNNING, or the
just-finished run's stale live signal during IDLE) despite the rule above holding once the
callback returns. An earlier revision installed/cleared the controller AFTER each status publish
instead, which an independent Rust review's own executable witness caught: a RUNNING observer's
own `abort()` call was a no-op, and an IDLE observer saw the previous run's still-live signal.
Entry-side relative order (`_start_run_signal`, `set_status(RUNNING)`, `streaming_message`,
`error_message`) is unchanged from `AG-008`'s own certified sequence. Exit-side order changed
further, as part of the failure-atomicity rule below: `set_status(AgentStatus.IDLE)` moved to be
the LAST write in `_run_wrapped`'s own `finally` block, after `_end_run_signal()`/
`streaming_message`/`pending_tool_calls`, not before them. This has NO observable effect on the
success path -- `streaming_message`/`pending_tool_calls` already hold their final values by that
point regardless of the write's own position, since the run's own normal completion (or a settled
failure via `_settle_run_failure`) already set them -- so `AG-008`'s own certified rule (the four
fields' final values match pinned Pi's own `runWithLifecycle`/`finishRun` write order once the
whole sequence completes) is not reopened, only extended below to define the FAILURE case `AG-008`
never addressed at all.

**Status-observer failure atomicity (`L09-R007`, convergence-agreed contract):** Pi has no
synchronous, listener-driven status-notification extension point at all -- `isStreaming = true`
and `finishRun()`'s own writes are plain, non-throwing property assignments in Pi, made
unconditionally outside Pi's own run-lifecycle `try`/executor boundary, so Pi never has an
"entry/exit notification observer throws" case to define. This is therefore a genuinely
Minion-owned architectural-mapping decision, derived from the ONE structural fact Pi's own design
does establish: `isStreaming = true` (RUNNING's own Pi analogue) is written BEFORE ANY of the run's
own observable event stream (including `agent_start`) exists, while `finishRun()` (IDLE's own Pi
analogue) runs AFTER the run's own observable outcome has already been fully committed and
dispatched. The two transitions are therefore governed asymmetrically, not by one uniform rule:

- **A RUNNING-notification failure** (an `AGENT_STATUS` EMIT listener or `on_status_change`
  raising) means the run never validly began, matching Pi's own "nothing observable exists yet at
  this point" structure: the freshly-created signal is discarded; `status` is forced back to
  `AgentStatus.IDLE` directly, WITHOUT calling `set_status` again (which would re-invoke the SAME
  failing listener chain, an infinite-rollback hazard); no `agent_start`, no `_settle_run_failure`-
  synthesized turn, and no `message_start`/`message_end`/`turn_end`/`agent_end` sequence is
  produced (`_settle_run_failure` is Pi's own `handleRunFailure`, invoked only once a run has
  genuinely begun); entering input a caller already inspected from `Inbox` before entering this
  method (see "Preclaimed inbox input" below) was never actually removed, so nothing needs
  restoring; and the observer's own original exception propagates DIRECTLY out of `prompt()`/
  `continue_()`/`run_until_idle()`, unconverted. A subsequent `prompt()`/`continue_()` call then
  succeeds normally, exactly as if the failed attempt had never been made.
- **An IDLE-notification failure** does NOT retroactively hide or duplicate the run's own
  already-committed outcome (success, or a `_settle_run_failure`-settled failure/abort): every
  other exit-time write (`_end_run_signal()`, `streaming_message`, `pending_tool_calls`) completes
  UNCONDITIONALLY before the possibly-throwing `set_status(AgentStatus.IDLE)` call, which is
  therefore LAST, not first. `set_status`'s own internal write to `self._status` happens before its
  own emit/callback (unchanged, already true today), so `status` is ALSO already `IDLE` internally
  by the time a throwing listener's exception propagates -- meaning `signal`/`streaming_message`/
  `pending_tool_calls`/`status` are all already fully consistent with a normally-settled idle
  instance the instant the exception is observed by a caller. That exception then propagates OUT of
  `_run_wrapped`/`prompt()`/`continue_()` UNCAUGHT, matching pinned Pi's own precedent that a
  listener failure during settlement is never silently absorbed (`_settle_run_failure`'s own
  "a listener invoked during this very recovery sequence itself throws... the exception propagates
  uncaught" rule, above).
- **Ordering/short-circuit across `AGENT_STATUS` listeners and `on_status_change`** needs no
  separate rule: `EventBus.emit`'s own existing fail-fast semantics (a throwing listener propagates
  immediately, so no later listener in the same dispatch -- including `on_status_change`, called
  only after `emit` returns without raising -- ever runs) already governs both transitions
  identically, the same as every other `EMIT` event in this codebase.

**Preclaimed inbox input (`L09-R007`, convergence-agreed contract; mechanism corrected under
`L09-R010`, then again under the `L09-R012`/`R013`/`R014` convergence -- current mechanism is
claim-then-reservation-rollback, NOT peek-then-commit):** `continue_()`'s own steering and follow-up
branches, and `run_until_idle()`'s own follow-up claim, need to know their entering input BEFORE
`_run_wrapped`'s own RUNNING notification runs, and must not leave it lost from `Inbox` (`AG-011`)
if that notification then fails -- pinned Pi's own `Agent.continue()` has the identical
pre-drain-then-`runWithLifecycle` shape (`PendingMessageQueue.drain()` is equally destructive, with
no rollback of its own; Pi simply never observes this gap because nothing between its own drain and
`finishRun` can throw). The observable rule:

```text
RUNNING notification fails after a caller has already reserved entering envelopes from Inbox
    -> no reserved envelope is lost or duplicated
    -> each envelope's own id/message/origin are exactly the values a subsequent claim observes
    -> input the failing observer itself enqueues at the same target during its own (failing)
       execution never precedes the restored envelopes at a later claim
    -> a subsequent claim at the same target observes the reserved envelope(s) exactly once
```

Applies to `continue_()`'s steering and follow-up branches and `run_until_idle()`'s follow-up
claim, under both `ClaimPolicy.ONE_AT_A_TIME` and `ClaimPolicy.ALL`. `prompt()` is unaffected: it
never reads from `Inbox` at all.

Two earlier mechanisms were tried and rejected before the current design. The first satisfied the
rule by claiming (destructively removing) eagerly and exposing a PUBLIC `Inbox.restore(target,
envelopes)` to reverse a failed claim; an independent Rust review found that method callable by ANY
caller with ANY envelope tuple -- including one still queued and never claimed, or the same envelope
repeatedly -- manufacturing duplicate queue entries that shared an id, contradicting `AG-011`'s own
exactly-once invariant (`L09-R010`, `CONTRACT_ASSURANCE_DEFECT`). The second removed the
restoration surface but introduced a peek-then-commit split instead: `Inbox.peek(target, policy)`
(public, read-only) let a caller inspect entering input without removing it, deferring the actual
removal to an internal-only `_commit_claim`, performed only once the RUNNING notification had
already succeeded. This closed the duplicate-id defect but opened a WINDOW between `peek()` and the
later commit during which a re-entrant observer on the same target -- the very listener
`_run_wrapped` awaits synchronously in between -- could itself claim the peeked envelopes, clear the
target, or enqueue more input; a commit that then removed by COUNT alone could silently delete
input the observer never touched (`L09-R011`), and even an identity-checked commit left a claiming-
and-THEN-throwing observer's own claimed batch unrestored (`L09-R013`), or a partial re-entrant
`ONE_AT_A_TIME` claim leaving a stale prefix eligible for duplicate admission (`L09-R014`) --
every one of these was a different exploit shape through the SAME window, not an independent defect.

The current mechanism removes the window entirely rather than adding a further case-by-case check:
`Inbox._reserve(target, policy)` (private, Layer-08-only) atomically `claim()`s the selected batch
IMMEDIATELY -- removing it from `Inbox` the instant it is selected, before the RUNNING notification
ever runs -- and returns a private, one-shot `_Reservation` bound to exactly that batch
(`.envelopes`, read-only, bound at construction). Exactly one of `.commit()` (settles the removal
permanently) or `.rollback()` (restores the exact reserved batch, verbatim and in the same order,
ahead of whatever the target holds by then) may ever be called, and each takes NO argument at all --
closing the "foreign/duplicate envelope" authority gap `L09-R010` found by the absence of a
parameter, not by convention; a second call to either, after the first, raises `RuntimeError` --
closing the "double action" half structurally. `AgentLoop._run_wrapped` calls `.rollback()` on a
RUNNING-notification failure and `.commit()` on success. Because removal happens at RESERVE time,
not commit time, a re-entrant observer on the same target during the RUNNING notification can never
see or act on the reserved batch at all -- whether it throws, returns normally, or performs its own
unrelated claim/clear/enqueue on that target -- closing `L09-R011`/`L09-R013`/`L09-R014` by
construction. Only the reservation's own claimed batch is ever rolled back: a genuinely different,
unrelated claim the observer itself performs, a `clear()`, or new input the observer enqueues are
never reversed or treated as though they did not happen -- rollback restores exactly what THIS
reservation removed, nothing more. `AG-011`'s own already-certified `InputEnvelope` identity/
FIFO-ordering rules are read, not rewritten, by any of this -- no lower-layer reopen. `Inbox.restore`
(the first mechanism) and `Inbox.peek`/`_commit_claim` (the second) are both removed entirely, not
merely superseded in place -- `Inbox.claim()` remains the only OTHER removal path, unchanged.

**Consumer/settlement matrix** (every place the SAME per-run `RunSignal` reaches, and whether the
loop itself forces a stop there — none do, except the two explicit tool-preflight polls below):

| Surface | Receives the signal | Loop forces a stop there? |
|---|---:|---:|
| `AGENT_LIFECYCLE_EVENT` listeners (`subscribe`-equivalent) | via `instance.signal` (already the listener's own first argument) | no |
| `AGENT_TRANSFORM_CONTEXT` listeners (`L09-R005`, new) | yes, explicit 3rd payload argument | no |
| provider request (`llm/service.py::Request.signal`, `AI-027`) | yes | no -- the adapter chooses whether to honor it and represent `StopReason.ABORTED` |
| tool `before`-hook (`TOOLS_PRE_EXECUTE` waterfall, `L09-R001`) | yes, threaded explicitly as a payload argument (no `instance` access at Layer 06) | only at the two explicit preflight polls -- see `spec/tools.md` |
| tool `execute()` | yes, when the tool declares `ToolDefinition.wants_signal=True` (`L09-R003`) -- its own cooperative 3rd/4th positional parameter | no -- the tool's own choice; never forcibly interrupted |
| tool after-hook (`TOOLS_POST_EXECUTE` waterfall, `L09-R001`) | yes, threaded explicitly as a payload argument | no -- runs unconditionally regardless of abort state |
| per-batch (sequential/parallel) | n/a, batch-level | yes, but only BETWEEN calls -- see `spec/tools.md`'s own split algorithms |
| `AGENT_PREPARE_NEXT_TURN`/`AGENT_TURN_STOPPING` listeners | via `instance.signal` (already the listener's own first argument) | no |
| steering/follow-up queue drains | not applicable -- plain queue-drain operations, no signal parameter, matching pinned Pi exactly |

`AGENT_TRANSFORM_CONTEXT` (`L09-R005`): pinned Pi's own `config.transformContext(messages, signal)`
(`agent-loop.ts:290-292`), an OPTIONAL per-request projection of the outgoing message history,
invoked immediately before every provider request -- omitted entirely from an earlier revision of
this matrix, a `CONTRACT_ASSURANCE_DEFECT` an independent Rust review named explicitly. Genuinely
NEW to Minion: no prior layer had an equivalent extensibility point at this exact seam.
`AGENT_PRE_STEP` is NOT equivalent -- it runs once, at INPUT ADMISSION boundaries, and changes
what gets durably admitted into the run's own transcript; `AGENT_TRANSFORM_CONTEXT` runs on every
REQUEST and never mutates the persistent/run-local transcript itself, matching pinned Pi's own
`streamAssistantResponse` reassigning only its own LOCAL `messages` variable, never
`currentContext.messages` -- a transform's own output is provider-local for that one request only,
never carried into a later turn's own request. Zero listeners (the default, matching every caller
before this event existed) preserves prior behavior exactly. `instance`/`signal` are BOTH
AUTHORITATIVE event metadata at this waterfall (`L09-R006`, extended by `L09-R018`): the payload
is `(instance, messages, signal)`, sandwiching its ONE transformable field (`messages`) between
its two authoritative fields -- a listener no longer needs to re-supply EITHER authoritative field
when delegating with a replacement.

The full delegation grammar (`L09-R018`, convergence-agreed, `assurance/layers/09-active-abort-
contract-checkpoint-r018-convergence.md`): legal delegation lengths are exactly `{0, 1, 3}`.
`next_()` (length 0) is a true no-op forward. `next_(new_messages)` (length 1) supplies ONLY the
transformable field -- both `instance` and `signal` are restored to their original values
regardless of what (if anything) the listener says about them. `next_(instance, messages, signal)`
(length 3, full explicit) restores both authoritative positions from their original values
regardless of content, taking only the middle position as `messages`. ANY OTHER delegation length
-- in practice, exactly length 2 -- is REJECTED directly at this authority boundary (a
`WaterfallError`, per `runtime/errors.py`) before the malformed tuple is ever forwarded to a later
listener: a two-element replacement is inherently AMBIGUOUS between "the leading `instance` was
omitted" (`next_(messages, signal)`) and "the trailing `signal` was omitted" (`next_(instance,
messages)`) -- both produce an identical length-2 tuple, and neither a bare tuple's own length nor
its content (inspecting whether a value happens to be a `RunSignal` instance -- explicitly rejected
as "type/position guessing") can safely disambiguate them. An earlier revision instead committed to
ONE interpretation unconditionally, which silently corrupted the request when the OTHER
interpretation was the listener's actual intent (`L09-R018`, `PI_PARITY_DEFECT`): a genuine
leading-`instance` omission had its real `messages` discarded as though it were a forged `instance`,
and the live `signal` object forwarded downstream, and eventually to the real provider request, AS
IF it were `messages`.

Because `AGENT_TRANSFORM_CONTEXT` is dispatched from inside `AgentLoop._execute_run`'s own
`try`/`except Exception` boundary (`L08-R002`, unchanged), a rejected delegation's `WaterfallError`
is caught there and routed to `_settle_run_failure` exactly like any other run-executor failure:
`prompt()`/`continue_()` itself completes normally, with a synthesized terminal `error` assistant
message -- never a bare exception escaping the run. The malformed delegation never reaches a later
listener or the real provider request.

This is the SAME `normalize_step` mechanism `spec/tools.md` describes for `TOOLS_PRE_EXECUTE`/
`TOOLS_POST_EXECUTE`, generalized here to a payload with authoritative fields on BOTH sides of its
transformable field rather than only one -- the other authoritative-metadata waterfalls in this
codebase (`AGENT_PRE_STEP`, `AGENT_PREPARE_NEXT_TURN`, `TOOLS_PRE_EXECUTE`, `TOOLS_POST_EXECUTE`)
each have exactly ONE authoritative field, always at a fixed end, and so have no equivalent
two-length-2-readings ambiguity to resolve.

Tool-side signal capability is EXPLICIT, not inferred from arity alone (`L09-R003`):
`ToolDefinition.wants_signal: bool = False` (Layer 05). Pinned Pi's own `execute(toolCallId,
params, signal?, onUpdate?)` treats `signal`/`onUpdate` as independent optional parameters -- a
tool may want either, both, or neither. Python's own pre-existing arity-based `update` detection
(3 parameters means `update`, unchanged since before this layer) cannot by itself also distinguish
"this 3rd parameter is `signal`" without breaking that established meaning; an earlier revision
tried arity alone and could not represent a tool wanting `signal` without ALSO being forced to
declare an unused `update` parameter it did not want -- a `PI_PARITY_DEFECT` an independent Rust
review caught (`L09-R003`): Pi's own signal-only tool has no Python equivalent under that design.
`wants_signal=False` (every pre-Layer-09 tool) preserves the existing arity dispatch exactly;
`wants_signal=True` shifts `execute`'s own 3rd-parameter meaning to `signal`, with a 4th parameter
(if declared) receiving `update` -- all four Pi-equivalent combinations (neither, update-only,
signal-only, both) are representable. See `spec/tools.md` for the complete dispatch table.

Minion's own architectural mapping, not an observable divergence: pinned Pi threads `signal` as an
EXPLICIT parameter to every one of `agent-loop.ts`'s own consumers, including its own lifecycle
listeners (`subscribe(listener)`'s own second parameter) and `prepareNextTurn`/`shouldStopAfterTurn`
(via `agent.ts`'s own PUBLIC `Agent.createLoopConfig()`, `agent.ts:445-471`, which wraps the
application-facing `AgentOptions.prepareNextTurn(signal)`/`prepareNextTurnWithContext(context,
signal)`/`shouldStopAfterTurn(context, signal)` callbacks with the SAME Agent's own live
`this.signal` before handing them down to the low-level loop). `instance.signal` for
`AGENT_PREPARE_NEXT_TURN`/`AGENT_TURN_STOPPING` is therefore a FAITHFUL MAPPING of an existing Pi
capability -- Pi genuinely supplies `signal` explicitly at this exact point -- not a Minion-added
one (an earlier revision of this section claimed pinned Pi's `prepareNextTurn` carries no `signal`
at all; that claim was itself wrong, having read only `agent-loop.ts`'s own low-level
`AgentLoopConfig.prepareNextTurn(context)` shape and missed `agent.ts`'s own public wrapper --
corrected here, `L09-R015` convergence, `C09-2`). Minion's own established convention already
passes `instance` as the first argument to every `AGENT_LIFECYCLE_EVENT`/`AGENT_PREPARE_NEXT_TURN`/
`AGENT_TURN_STOPPING` listener, so those listeners already have a way to reach `instance.signal`
without a new parameter -- only the tool-execution seam (Layer 06, which has no `instance` access at
all, being architecturally below Layer 07) needs the signal threaded explicitly, and does. The
OBSERVABLE fact -- every one of these consumers CAN read the current run's signal -- is identical
either way; only the mechanism differs.

**`instance` is authoritative event metadata at the `AGENT_PRE_STEP`/`AGENT_PREPARE_NEXT_TURN`
waterfalls (`L09-R015`):** both dispatches pass `instance` as the first payload argument, and (like
`signal` at `AGENT_TRANSFORM_CONTEXT`, `L09-R006`, and `tool_call_id`/`tool_name` at
`TOOLS_PRE_EXECUTE`/`TOOLS_POST_EXECUTE`, `L06-R003`) it is identity/authority a listener has no
business redirecting for a listener downstream of it -- unlike `reason` (`AGENT_PRE_STEP`) or
`message`/`tool_results`/`context`/`new_messages` (`AGENT_PREPARE_NEXT_TURN`), which remain
genuinely listener-transformable, intentionally out of this rule's scope. Both dispatches supply a
`normalize_step` closure (`_restore_instance`) that forces the payload tuple's own `instance` slot
back to the closure-captured ORIGINAL value at every listener-to-listener handoff, regardless of
what a delegating listener passes -- a listener can no longer redirect a later listener to a
fabricated replacement `instance`, or drop it by omitting it when delegating, even though it remains
free to transform every other payload field. `AGENT_PRE_STEP`'s own exposure was found during a full
audit of every `.waterfall()` dispatch in this codebase alongside the reviewed
`AGENT_PREPARE_NEXT_TURN` finding -- the identical unprotected shape, not itself separately reported
by any review.

**The load-bearing rule:** every consumer above may IGNORE the signal, and if every one of them
does, the run completes exactly as if `abort()` had never been called. Four distinct
abort-adjacent outcomes must be kept separate:

1. a represented provider `StopReason.ABORTED` terminal (already Layer-08-owned -- the existing
   represented-error/aborted short-circuit handles it; Layer 09 adds no new code for this path
   itself, only the signal propagation that lets a real/scripted adapter choose to produce it);
2. an exception escaping ordinary run execution while `instance.signal.aborted` happens to be
   true AT THE MOMENT `_settle_run_failure` reads it -- classified `stopReason: aborted` instead
   of `error`, purely from the signal's CURRENT state at that moment, with NO causal requirement
   that the exception was actually caused by the abort (pinned Pi's own `abortController.signal.
   aborted` read at `handleRunFailure` catch time has the identical property);
3. a cooperative tool's own normal/throwing outcome after observing the signal -- ordinary,
   already-certified Layer-06 execute/finalize semantics; the after-hook still runs unconditionally;
4. abort requested while `agent_end` listeners are still being awaited -- the signal is already
   aborted (or becomes aborted mid-dispatch), but that already-in-flight `agent_end` dispatch's own
   listener settlement still completes normally before the Agent becomes idle.

**Not in this layer's scope:** actual network-transport cancellation remains deferred to `PROV-004`
(or an explicitly later real-provider phase) -- this project has no real provider transport yet.
Layer 09 certifies generic signal PROPAGATION to the adapter-call boundary through the existing
scripted/mock adapter, not that any real transport was cancelled. Layer 08's own prior removal of
`request_boundary_stop()`/`cancel()` (below) remains correctly removed and is UNRELATED to this
section: that was a Minion-only host-safety mechanism with no Pi basis and no owner approval;
`abort()`/`signal` here are pinned Pi's own feature, implemented faithfully, not a revival of the
removed one. Layer 08 itself still has no local cancel/boundary-stop mechanism of its own kind: a
prior revision of this section documented one (`request_boundary_stop()`, renamed from `cancel()`),
but it was removed entirely rather than kept and approved -- a public method that could alter a
Pi-equivalent run's own observable outcome had no owner governance approval for that divergence, and
no demonstrated product need justified keeping it, the same default this project already applied to
`max_steps` (above). If a host-only safety mechanism is ever needed, it must sit entirely outside a
single Pi-equivalent run's own semantic behavior -- limiting a HOST's own repeated scheduling/
invocation policy across independent runs, never truncating or altering one run's own outcome
internally.

### Runtime-state transition timing

`is_streaming`: flips per pi-equivalent run (`AgentLoop._run_wrapped`), matching pinned Pi's own
`runWithLifecycle`/`finishRun` write points exactly -- once per `prompt()`/`continue()` invocation,
not once per `run_until_idle()` pump iteration.

`streaming_message`: non-`None` for exactly the duration of one MESSAGE's own `message_start` ->
`message_end` window, matching pinned Pi's own `message_start`/`message_update` -> partial,
`message_end` -> `None` write points -- NOT scoped to "one provider request" (`L08-R012`,
contract-convergence final review: an earlier revision of this paragraph opened with "non-`None`
for exactly the duration of one provider request," directly contradicted by its own very next
sentence, below, which correctly states the complete rule; only the complete rule is normative).
Pinned Pi's own reducer does not distinguish the assistant's own streamed reply from any other
admitted message: `streaming_message` is set (briefly, non-streamed, for a message that was never
itself streamed) to EVERY message at its own `message_start` and cleared at its own `message_end`,
whether that message is the assistant reply, an admitted prompt/steering message, a follow-up, or a
tool result -- reproduced uniformly at every admission point ("Initial-turn admission" above) and
every message emitted by `_run_step`. For the assistant's own genuinely-streamed reply specifically,
`streaming_message` additionally carries FULL content fidelity -- text, thinking, and tool-call
construction alike -- across every intermediate `message_update` between that message's own
`message_start` and `message_end`, set directly from each stream chunk's own already-complete
`partial` (the certified Layer-02/04 `StreamChunk` carries a complete `partial: AssistantMessage` on
every variant; no independent reconstruction from raw deltas is attempted); a non-streamed admitted
message has no intervening `message_update` at all, only its own `message_start`/`message_end` pair.

`pending_tool_calls`: real per-call tracking (add on start, remove on end) through the
already-certified Layer-06 `tools/execution-start`/`tools/execution-end` events -- an existing
seam, not a new one -- matching pinned Pi's own `processEvents` reducer exactly.

`error_message`: set from a turn's own failed/aborted assistant message (`error_message`, when
truthy) and, distinctly, NOT cleared at that same run's own `agent_end` -- it persists across an
idle period after a failed run, cleared only at the *next* run's start or via the already-certified
Layer-07 `reset()`, exactly matching pinned Pi (`finishRun` never touches `errorMessage`; only the
next `runWithLifecycle` entry does).
