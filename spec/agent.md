# Agent Semantics

This document spans two assurance layers over one master-phase surface (pinned Pi's
`packages/agent/src/agent.ts` + `agent-loop.ts` + `types.ts`): **Layer 07 — Agent public state and
inbox/queues** (below) and **Layer 08 — the run/turn state machine** (the rest of this document,
not yet certified as its own layer). The split exists because Layer 07's primitives must be stable
enough for Layer 08 to consume without redesign, and because "agent state and queues behave like
Pi" is too coarse a requirement to test independently (`AG-011`..`AG-019`; `AG-001`..`AG-010`
remain Layer-08/09-owned, unimplemented, and untouched by the Layer-07 pass that added this
section).

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

Deferred to Layer 08:

- the run/turn/step state machine itself (`agent_start`/`turn_start`/`turn_end`/`agent_end`
  ordering, already described below in this same document, pre-dating the Layer-07/08 split and
  not re-scoped by it);
- *when* the loop calls the claim primitive for steering vs. follow-up (before the first request,
  after a turn's tool calls, only when otherwise stopping, etc.);
- `prompt()`/`continue()` caller-rejection rules while a run is active;
- `shouldStopAfterTurn`/`prepareNextTurn` orchestration and steering-vs-follow-up priority during a
  run;
- exactly when/how `is_streaming`/`streaming_message`/`pending_tool_calls`/`error_message`
  transition during a run (Layer 07 owns their vocabulary and initial values only -- see below).

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
streaming_message    AgentInstance (vocabulary only)   L08 (not yet wired)
pending_tool_calls   AgentInstance (vocabulary only)   L08 (not yet wired)
error_message        AgentInstance (vocabulary only)   L08 (not yet wired)
```

This table exists so Layer 08 does not reopen state ownership later: every field above already has
a home and a type: Layer 08's job is to decide *when* to write to the ones it transitions, using the
primitives this layer already defines, not to redesign where they live.

### Mutable per-instance current configuration

Pinned Pi's `AgentState.systemPrompt`/`model`/`thinkingLevel` are directly assignable properties on
the live state object `Agent.state` returns -- `agent.state.systemPrompt = "..."` immediately
mutates that one Agent's own current value, read by every subsequent run, distinct from whatever
default the Agent was constructed with. This is genuinely owned by Layer 07, not deferred to a
later provider/orchestration layer: pinned Pi mutations are observable and take effect for
subsequent runs regardless of whether anything has consumed them yet, so the state and its mutation
surface must exist now, independent of when Layer 08 starts reading it.

Minion keeps the existing frozen, shared `AgentDefinition` (definition defaults, `AG-009`) and adds
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
starts idle. The precise moments a run flips this to running and back are Layer-08 territory
(transitions are driven by turn/step lifecycle timing this document does not yet certify); Layer 07
owns the vocabulary and its initial value.

Pinned Pi's remaining runtime-state fields -- `streamingMessage` (the current partial assistant
message), `pendingToolCalls` (tool-call ids currently executing), and `errorMessage` (the most
recent failed/aborted turn's error) -- have their vocabulary and initial values represented now:
`None`/empty/`None` respectively, matching pinned Pi's own `undefined`/empty-`Set`/`undefined`
initial state exactly. Their *transitions* remain deferred to Layer 08: populating them meaningfully
requires step/turn timing this layer does not implement, and no fake transition is manufactured to
close this layer early.

Pi's own two *active-run-lifecycle* `isStreaming` transition points, recorded here as a reference
for whoever implements Layer 08 (not implemented by this layer): a call to `prompt()`/`continue()`
sets it `true` before anything else happens (`runWithLifecycle`), and `finishRun()` -- reached from
a `finally` block, so it runs whether the run succeeded, threw, or was aborted -- unconditionally
sets it back to `false` as its very first statement. Layer 08 must reproduce both write points
exactly (entry: unconditional; exit: unconditional-via-`finally`, never skipped by an error) using
the `AgentStatus` vocabulary and `AgentInstance.set_status` primitive this layer already provides;
it does not need a different mechanism.

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

## Layer 08 — the run/turn state machine (PASS 2)

Not yet certified as its own layer, but substantially complete after PASS 2: every item PASS 1 left
open is now implemented and verified, with one disclosed content-fidelity simplification (see
"Runtime-state transition timing" below). This section records what is verified against pinned Pi
(`agent-loop.ts`/`agent.ts`/`types.ts`) and implemented -- the informal prose this section replaces
predates the Layer-07/08 split and was already textually correct about run/turn vocabulary; the
*implementation* was not, until PASS 1/PASS 2.

### Run/turn vocabulary and event boundaries (PASS 1, verified and implemented)

A run is one high-level prompt/continue invocation, bracketed by `agent_start`/`agent_end`. A turn
is one assistant response plus the tool calls/results it triggers -- never more than one provider
request -- bracketed by `turn_start`/`turn_end`. Confirmed directly against `runAgentLoop`/`runLoop`
(agent-loop.ts): `turn_start`/`turn_end` never span more than one provider request in pinned Pi.

An earlier revision of Minion's own driver let one internal helper call another (what is now
`_run_step`, one provider request) several times inside a single `TURN_START`/`TURN_END` bracket --
observably incompatible with pi once a turn produced more than one provider request, since Minion's
own `turn_start`/`turn_end` are what the public projection turns into pi's `turn_start`/`turn_end`
events. That prior bracket was actually pi's own **run**, not a turn. This pass corrected the
boundary, not the helper's own name: `_run_once` (renamed from `_run_turn`) now owns
`AGENT_START`/`AGENT_END`; `_run_step` (kept, since the observable boundary is what matters) owns
`TURN_START`/`TURN_END` around exactly one provider request. `AGENT_START`/`TURN_START` fire in that
order, before the messages entering the run/turn are logged -- matching pi's own
`runAgentLoop`/`runLoop` order exactly, confirmed by reverting the append order and observing the
canonical scenarios fail before restoring it.

`agent_end.messages` is pi's own invocation-local field, reconstructed by the projection as a
run-scoped accumulator (every message produced/consumed since the matching `AGENT_START`, reset at
each one) rather than synthesized from the whole log -- a log holding several runs now projects
several independently-scoped `AgentStart`/`AgentEnd` brackets. `turn_end{message, toolResults}` is
likewise reconstructed per turn from that turn's own `MessageStart`/`MessageEnd` pairs, never a
second, independently-logged copy of the same content. `causes` (which queued input triggered
processing) is a disclosed Minion enrichment scoped to the run (`AgentStart`/`AgentEnd`), not each
turn within it -- pinned pi's own bare `turn_start`/`agent_start` carry no fields at all.

After a completed turn, three of the four ordering stages pi documents are implemented and verified:
`turn_end` fires, then the stop decision is asked (`shouldStopAfterTurn`'s Minion realization,
`agent/turn-stopping`) before steering is polled for the next turn:

```text
turn_end -> shouldStopAfterTurn -> steering poll
```

`prepareNextTurn` -- the fourth stage, between `turn_end` and the stop decision -- is implemented
this pass (`agent/prepare-next-turn`, waterfall, terminal a no-op `RunConfigUpdate()`): a listener
may return `system_prompt`/`model`/`thinking_level` overrides applying to the *next* provider
request only, applied to a per-run mutable snapshot (below), never persisted back to
`AgentInstance`. Dispatched after every turn, including one a tool batch's `terminate` verdict
ended (see "Terminate does not skip the decision machinery" below) -- confirmed directly against
`runLoop`, which calls `prepareNextTurn` unconditionally after every `turn_end`, before the stop
decision.

### `prompt()`/`continue_()`: the public run entry points

`AgentLoop.prompt(message)` and `AgentLoop.continue_()` (`continue` is a Python keyword) reproduce
pinned Pi's `Agent.prompt()`/`Agent.continue()` exactly, confirmed directly against source
(agent.ts:348-407):

- `prompt()` rejects with pinned Pi's exact text ("Agent is already processing a prompt. Use
  steer() or followUp() to queue messages, or wait for completion.") while a run is active;
  otherwise starts a new run with the given message(s) as its own entering prompt.
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

### Run-start snapshot

Pinned Pi's `Agent.createContextSnapshot()`: `system_prompt`/`model`/`thinking_level` are read ONCE
at run start into a mutable per-run snapshot, not re-read from the certified Layer-07
`AgentInstance` on every turn. A caller mutating the instance mid-run does not retroactively alter
a run already in progress; `prepareNextTurn` may still update the snapshot run-locally (above), and
those updates are likewise never written back to `AgentInstance`.

### Mid-run follow-up continuation

Pinned Pi's outer `runLoop` loop polls the follow-up queue only once the inner loop (turns within
one continuation) would otherwise exit -- no more tool calls, nothing steered -- and, if follow-up
is found, continues the *same* run (`agent_start`/`agent_end` still bracket it) rather than ending.
Minion's driver reproduces this exactly: `AgentLoop._run_inner` is a genuine outer/inner nested
loop, with the outer loop claiming follow-up and extending the run's own `causes` when it does.
Minion's own `run_until_idle()` pump (no pi equivalent) is now a thin caller over this: it still
claims one batch and starts one run per claim, but because a run now drains follow-up internally
while open, a single pump iteration typically consumes every queued batch in one run. The pump's
own outer loop remains a safety net for the one case pinned Pi does not auto-continue either (a
`shouldStopAfterTurn` listener stopping the run early while follow-up is still queued) -- pinned Pi
would leave that for an explicit `continue()` call; Minion's pump substitutes for that
automatically, an already-disclosed, intentional Minion extension (`AG-019`'s own wake note).

### Terminate does not skip the decision machinery

An earlier revision of this driver -- and of the `agent/turn-stopping` event's own docstring --
treated a tool batch's unanimous `terminate` verdict as skipping `prepareNextTurn`/
`shouldStopAfterTurn`/the steering poll entirely ("hard termination precedes the decision"). Checked
directly against `runLoop`: this was never actually true of pinned Pi. `terminate` only ever affects
`hasMoreToolCalls` -- whether the tool-driven inner loop has more work -- and pinned Pi still
dispatches `prepareNextTurn`/`shouldStopAfterTurn`/polls steering for that same turn regardless.
Corrected this pass: both are now dispatched unconditionally after every turn. The observable
end-of-run outcome is usually unchanged in the common case (a listener answering "continue" cannot
manufacture a new tool-driven request on its own -- the inner loop's own `hasMoreToolCalls ||
pendingMessages` condition still governs), but listeners now genuinely observe every turn, matching
pinned Pi. Minion's own `"terminated"` vs. `"completed"` end-reason label (a disclosed Minion
enrichment pi has no equivalent field for) still distinguishes the two cases where the run
ultimately does end via natural exhaustion.

### Runtime-state transition timing

`is_streaming`: flips per pi-equivalent run (`AgentLoop._run_wrapped`), matching pinned Pi's own
`runWithLifecycle`/`finishRun` write points exactly -- including a correction to Minion's own prior
pump behavior: `run_until_idle()` previously wrapped its whole multi-batch pump in one shared
RUNNING/IDLE bracket; it now calls `_run_wrapped` once per claimed batch, so status genuinely
toggles per run even when the pump drains several in sequence.

`streaming_message`: non-`None` for exactly the duration of one provider request, matching pinned
Pi's own `message_start`/`message_update` -> partial, `message_end` -> `None` write points.
Content-level fidelity is a disclosed, deliberate simplification: text-only, accumulated from
`TextDelta` chunks. Minion's certified Layer-02/04 `collect()` exposes only raw stream deltas, not
a live partial-message object to build a richer reconstruction from, and reproducing pinned Pi's
own opaque partial representation is out of this layer's scope to invent. The transition timing
itself -- the part of the contract this layer actually certifies -- is exact; only mid-stream
content fidelity for thinking/tool-call blocks is not attempted.

`pending_tool_calls`: real per-call tracking (add on start, remove on end) through the
already-certified Layer-06 `tools/execution-start`/`tools/execution-end` events -- an existing
seam, not a new one -- matching pinned Pi's own `processEvents` reducer exactly.

`error_message`: set from a turn's own failed/aborted assistant message (`error_message`, when
truthy) and, distinctly, NOT cleared at that same run's own `agent_end` -- it persists across an
idle period after a failed run, cleared only at the *next* run's start or via the already-certified
Layer-07 `reset()`, exactly matching pinned Pi (`finishRun` never touches `errorMessage`; only the
next `runWithLifecycle` entry does).

### `handleRunFailure`

Pinned Pi's defensive fallback for an unexpected exception from run-loop callback/listener code
(not a normal model/tool failure, both of which already settle as ordinary assistant/tool-result
content): synthesizes a minimal failure assistant message, logs a matched `turn_start`/
`assistant_message`/`turn_end` (a small, disclosed simplification of pinned Pi's own bare
`turn_end`, no preceding `turn_start` at all -- chosen so the log's turn-scoped projection
accumulator never special-cases an unmatched `turn_end`), then `agent_end` with `reason: "failed"`
-- never an unhandled exception escaping `prompt()`/`continue_()`/`run_until_idle()`.

Deliberately narrow, matching pinned Pi's own boundary exactly: only `agent/pre-step`/
`agent/turn-stopping`/`agent/prepare-next-turn` listener dispatch is wrapped. Model/provider/
tool-execution failures are NOT "unexpected loop callback failure" in pinned Pi's own sense and
must not be smuggled into a settled failure turn -- an unresolvable model still raises eagerly,
uncaught, exactly as the already-certified `eager-invalid-model-fails-before-stream.yaml` requires.

### Active abort propagation (explicitly out of scope)

Abort actively signals the running provider/tools/hooks. Idle is reached only after terminal run
settlement and awaited `agent_end` listeners -- Layer 09's territory, per the already-certified
Layer-07 contract's own deferral. Not attempted by Layer 08 at all; this layer's `handleRunFailure`
above settles an aborted/failed turn correctly once it arrives, without itself implementing any
signal propagation.

### Manifest correction

Manifest rows `AG-001`..`AG-010` previously carried `disposition: adopted` while several cited only
still-unfilled placeholder canonical scenarios (`TO_BE_FILLED_FROM_PINNED_PI_BEHAVIOR`) as their
evidence -- a false certification claim predating PASS 1. `AG-001`/`AG-004` were corrected in PASS 1
with real evidence for the run/turn boundary. This pass corrects the remaining seven: `AG-002`,
`AG-003`, `AG-005`, `AG-006`, `AG-008`, `AG-009`, `AG-010` are now genuinely `adopted`, each with
real language-test and/or language-neutral canonical evidence for behavior this pass actually
implemented and verified (not merely re-labeled). `AG-007` (active abort propagation) is corrected
to `deferred parity` -- it was never Layer 08's own target at all, and claiming otherwise was wrong
on its face, not merely under-evidenced.
