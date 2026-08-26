# Agent Semantics

This document spans two assurance layers over one master-phase surface (pinned Pi's
`packages/agent/src/agent.ts` + `agent-loop.ts` + `types.ts`): **Layer 07 — Agent public state and
inbox/queues** (below) and **Layer 08 — the run/turn state machine** (the rest of this document,
not yet certified as its own layer). The split exists because Layer 07's primitives must be stable
enough for Layer 08 to consume without redesign, and because "agent state and queues behave like
Pi" is too coarse a requirement to test independently (`AG-011`..`AG-013`; `AG-001`..`AG-010`
remain Layer-08/09-owned, unimplemented, and untouched by the Layer-07 pass that added this
section).

## Layer 07 — Agent public state and inbox/queues

### Ownership

Layer 07 defines:

- the Agent's public processing-status vocabulary (idle/running) and its initial value;
- steering-inbox and follow-up-inbox storage, independent of each other;
- the enqueue operations and the primitive claim (drain) operation, including both of pinned Pi's
  claim policies;
- queue-clearing operations;
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
  run.

Deferred to Layer 09: abort/cancellation propagation into an active run, its providers, tools, and
hooks. Layer 07 does not define or touch any cancellation primitive.

Session (Layer 03, certified) remains the sole authority for conversation history: the Agent layer
never stores messages itself. What a caller sees as "the transcript" is `derive_messages` projected
from the instance's own `SessionLog`; Layer 07's public state vocabulary is exactly the fields Pi's
`AgentState` defines *beyond* `messages`/`tools` (both of which are already owned elsewhere --
`tools` by the certified Layer-05 `ToolRegistry`, addressed by scope, not by Agent state at all).

### Public processing status

Pinned Pi's `AgentState.isStreaming: boolean` -- true from the moment a run starts until its
`agent_end` listeners have all settled -- is represented as a two-value status (idle/running), not
a boolean, matching Pi's own two reachable values exactly; a third value would give the status
more than one meaning. A live instance starts idle. The precise moments a run flips this to running
and back are Layer-08 territory (transitions are driven by turn/step lifecycle timing this document
does not yet certify); Layer 07 owns only the vocabulary and its initial value.

Pinned Pi's remaining `AgentState` fields -- `streamingMessage` (the current partial assistant
message), `pendingToolCalls` (tool-call ids currently executing), and `errorMessage` (the most
recent failed/aborted turn's error) -- are **not yet implemented**. Their meaningful values only
exist mid-run, so certifying them now would mean fabricating transitions no certified layer
produces yet (`PI_BEHAVIOR` implemented only in the sense that pinned Pi's own semantics are
understood; the Minion-side vocabulary/wiring is Layer 08's obligation, tracked, not invented,
here).

### Steering and follow-up inboxes

Pinned Pi keeps exactly two per-instance queues -- a steering queue and a follow-up queue -- each
holding messages in enqueue order. Minion generalizes the same two queues under one storage
primitive addressed by a two-valued target (a design already established independent of this
layer): the steering queue is the target claimed at a **step** boundary; the follow-up queue is the
target claimed when a **turn** opens. `steer()` and `follow-up()` are exactly pinned Pi's two
enqueue operations under this vocabulary. A third operation, silent injection, enqueues to the same
step-boundary target as steering but never signals that new work has arrived -- an **intentional
Minion architectural extension** pinned Pi does not define, for ambient context that should ride
along with whatever else wakes a step but must not itself start one.

Enqueuing never normalizes, rejects, reorders, or otherwise interprets the message; it is stored
exactly as given, tagged with an opaque, JSON-safe provenance value the runtime never inspects.

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
true exactly when at least one of the two targets still holds unclaimed input. Clearing a target
that already has nothing queued is a harmless no-op. Clearing is orthogonal to whatever wake/settle
signal a host driver uses to decide when to poll a target at all -- Layer 07 defines only the
queue-content effect, not any interaction with that signal.

Pinned Pi's `Agent.reset()` additionally clears the transcript and the mid-run state fields
(`messages`, `isStreaming`, `streamingMessage`, `pendingToolCalls`, `errorMessage`) alongside both
queues, and rejects outright while a run is active. Minion does not reproduce an in-place instance
reset: Session's log is an authoritative, append-only record (an already-settled Layer-03 property,
not something this layer may relax), so there is no operation that "clears" a live instance's
transcript in place. The Minion-architecture equivalent of "start over" is creating a fresh
instance through the agent registry rather than resetting an existing one -- an **intentional
Minion architectural divergence** from Pi's single-instance reset, not a gap: the queue-clearing
half of Pi's `reset()` is exactly this layer's `clear`/`clear_all`, and the transcript/mid-run-state
half is superseded by instance replacement.

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
