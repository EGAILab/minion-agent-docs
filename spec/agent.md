# Agent Semantics

This document spans two assurance layers over one master-phase surface (pinned Pi's
`packages/agent/src/agent.ts` + `agent-loop.ts` + `types.ts`): **Layer 07 — Agent public state and
inbox/queues** (below) and **Layer 08 — the run/turn state machine** (the rest of this document,
not yet certified as its own layer). The split exists because Layer 07's primitives must be stable
enough for Layer 08 to consume without redesign, and because "agent state and queues behave like
Pi" is too coarse a requirement to test independently (`AG-011`..`AG-016`; `AG-001`..`AG-010`
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

Pi's own two `isStreaming` transition points, recorded here as a reference for whoever implements
Layer 08 (not implemented by this layer): a call to `prompt()`/`continue()` sets it `true` before
anything else happens (`runWithLifecycle`), and `finishRun()` -- reached from a `finally` block, so
it runs whether the run succeeded, threw, or was aborted -- unconditionally sets it back to `false`
as its very first statement. No other code path in pinned Pi ever assigns `isStreaming`. Layer 08
must reproduce both write points exactly (entry: unconditional; exit: unconditional-via-`finally`,
never skipped by an error) using the `AgentStatus` vocabulary and `AgentInstance.set_status`
primitive this layer already provides; it does not need a different mechanism.

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
"what tools are visible from this scope" directly, and that is the Agent's public tools projection.
Wholesale replacement the way `state.tools = [...]` performs it is not reproduced; visibility
changes happen through the already-certified `ToolRegistry` register/withdraw API instead, an
already-settled Layer-05 divergence this layer does not revisit.

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
preserved. One sub-piece is deliberately **not** reproduced, and is disclosed rather than silently
dropped: clearing `messages`. Pi's own transcript is a plain in-memory array with no separate
persisted log; Minion's `SessionLog` (Layer 03, already certified) is append-only by design, with no
truncate/clear primitive, and teaching its projection to respect a "reset boundary" would itself be
a Layer-03 semantic change -- outside this layer's mandate to make unilaterally. `reset()` therefore
clears every Pi-cleared field it can safely reach (runtime state, both queues) and leaves the
message-clearing decision as an explicit, tracked cross-layer dependency, not an unexamined gap.

---

A run is one high-level prompt/continue invocation. A turn is one assistant response plus tool
calls/results caused by it.

Prompt-run order:

```text
agent_start
turn_start
initial prompt message lifecycle
initial steering poll + claimed-message lifecycle
first provider request
assistant/tool lifecycle
turn_end
```

`prompt()` while active is rejected. `continue()` while active or with no transcript is rejected.
When the last message is assistant, `continue()` drains eligible steering, else follow-up, else
rejects; if it pre-drained steering, the run suppresses duplicate initial steering polling.

After a normally completed turn:

```text
turn_end -> prepareNextTurn -> shouldStopAfterTurn -> steering poll
```

Follow-up is polled only when the run would otherwise stop.

`agent_end.messages` is invocation-local. Prompt runs include initial prompt + newly produced/consumed
queue messages; continuation runs exclude pre-existing context.

Abort actively signals the running provider/tools/hooks. Idle is reached only after terminal run
settlement and awaited `agent_end` listeners.

Unexpected high-level transform/queue callback failure produces terminal assistant failure lifecycle,
then `turn_end`, `agent_end`, then idle, subject to listener-failure behavior.
