# Review Feedback — `minion-agent` Foundation Validation Against `minion-assist`

**Date:** 2026-08-18  
**Purpose:** Review feedback on the foundation validation report for rebuilding `minion-assist` on top of `minion-agent`.

## Overall assessment

The validation report's overall verdict is sound:

> **SAFE WITH MINOR DESIGN CHANGES.**

The current `minion-assist` implementation supports that conclusion. The application exercises a much broader workload than a coding CLI: long-lived Matrix conversations, multiple concurrent agent sessions, proactive heartbeat turns, cross-channel human approval, MCP stdio subprocesses, memory injection, background workers, multimodal input, and voice interaction.

Nothing in that workload exposes a foundational contradiction in the proposed `minion-agent` architecture. The important gaps are additive rather than requiring a redesign.

However, three proposed fixes in the report should be refined before the `minion-agent` design is frozen:

1. Scoped registration should be explicitly **hierarchical**, not just per-agent.
2. Turn provenance should support **multiple causal inputs**, not one singular `origin`.
3. Request-header reconstruction should use **component-level/content-addressed state**, not whole-header changed-or-hash deduplication.

The remaining BLOCKER/HIGH findings are well supported by the current codebase.

---

## 1. BLOCKER-1 is correct, but scope should be hierarchical

The report correctly identifies scoped registration and multi-agent lifecycle as foundational requirements.

The current application does not simply have one global agent session. Matrix assigns a durable session to each `(room_id, agent_id)` pair, and the handler keeps one long-lived `AgentSession` per `(agent_id, room_id)` while sharing reusable per-agent resources such as provider, tools, and memory.

The workload therefore reveals at least three useful registration lifetimes:

```text
runtime/root
│
├── named-agent scope
│     provider selection
│     normal tools
│     persona/prompt registrations
│     agent policy
│
├──── live agent-instance / conversation scope
│       conversation-specific registrations
│       session-specific context
│
└────── transient turn scope
          ReactToMessageTool
          heartbeat-only tools
          turn-specific policy/context
```

The bottom level already exists conceptually in `minion-assist`: `ReactToMessageTool` is created for a particular Matrix room/event and injected only into that turn, while heartbeat turns similarly construct temporary tools.

### Recommended refinement

Change the design from:

> one scope per live agent

to:

> **Scoped registration supports nested scopes with inherited visibility and ownership-bound disposal.**

Conceptually:

```text
root scope
   ↓
agent-definition scope
   ↓
agent-instance/session scope
   ↓
turn scope
```

A child scope should inherit registrations visible from ancestors while owning its own additional registrations. Disposal removes only registrations owned by that scope and descendants.

This remains completely generic and can later represent tenants, subagents, eval variants, request-local capabilities, or other scoped compositions.

### Also clarify agent terminology

The current application clearly distinguishes two concepts even though they are often both called "agent":

```text
AgentDefinition / AgentSpec
    reusable configuration/persona/capability composition

AgentHandle / AgentInstance
    one live execution identity
    one inbox
    one active-turn state
    one session/log
    one lifecycle owner
```

For example:

```text
AgentDefinition "Ada"
       │
       ├── AgentInstance room-A
       ├── AgentInstance room-B
       └── AgentInstance room-C
```

This distinction should be explicit before defining an agents registry, otherwise phrases such as "one scope per agent" become ambiguous immediately.

**Assessment:** Keep as **BLOCKER** because scope semantics affect Phase-0/Phase-1 conformance.

---

## 2. BLOCKER-2 is real, but one singular `origin` is insufficient

The report correctly identifies that agent execution and output delivery must be separate concerns.

`minion-assist` can initiate work without a user message. A heartbeat turn may produce no delivered output, send general output to a configured notification target, or route a commitment-specific response to a different channel stored with that commitment. The runtime therefore cannot assume:

```text
prompt source == response destination
```

The report proposes carrying an opaque caller-supplied `origin` from inbox entry to `turn/end`. That is directionally right but insufficient when the agent loop supports Pi-style claim policies such as:

```text
claim = all | one-at-a-time
```

With `claim=all`, one turn may consume:

```text
message A, origin X
message B, origin Y
message C, origin Z
```

There is no single correct `turn.origin`.

### Recommended refinement

Represent each queued input as an envelope:

```text
InputEnvelope
    id
    message
    origin
```

where `origin` is opaque to the runtime but **JSON-safe** so it remains compatible with the language-neutral log and future Rust implementation.

A turn then records the set of claimed causes:

```text
Turn
    causes: [input-envelope-id, ...]
```

and `turn/end` can expose the corresponding causal metadata:

```text
TurnEnd
    causes:
      - id: ...
        origin: ...
      - id: ...
        origin: ...
```

This naturally handles:

- Matrix messages
- scheduled/heartbeat work
- webhooks
- API-triggered work
- eval cases
- future schedulers
- batched inbox claims

Delivery remains entirely outside `minion-agent`.

### General principle

> **Inputs carry provenance; turns carry their causal inputs; delivery is an application concern.**

This is more general and more robust than a channel/reply-to abstraction.

**Assessment:** Keep as **BLOCKER**, but replace singular `origin` with causal input envelopes.

---

## 3. HIGH-1 observability is strongly supported

The report is correct that observability is a missing first-class seam.

The current `minion-assist` logging path records:

- complete LLM request bodies,
- complete responses,
- turn markers,
- tool calls,
- tool results,
- worker liveness,

and performs known-value secret redaction against configured credentials.

This is especially important because memory content injected into prompts may itself contain pasted credentials.

### Recommended refinement

A general capability such as:

```text
ctx.telemetry
```

is appropriate for runtime-owned operations including:

```text
agent turn
agent step
LLM request
tool execution
```

However, the redaction boundary must be explicit.

Avoid:

```text
raw telemetry
    ↓
listeners/sinks
    ↓
redaction somewhere later
```

because a sink with the wrong ordering could observe secrets.

Prefer:

```text
core/provider data
       ↓
sanitize/redact boundary
       ↓
safe structured telemetry
       ↓
sinks
   ├── OpenTelemetry
   ├── JSON/file logger
   └── debug sink
```

or a typed sensitive-field mechanism that requires policy before serialization.

### Keep telemetry observational

Telemetry should not become another semantic source of truth.

The intended hierarchy should remain:

```text
session log    = semantic truth
runtime events = extension/control surface
telemetry      = observational projection
```

A small language-neutral span vocabulary is useful, but correctness should remain defined by session/runtime semantics and conformance scenarios rather than telemetry implementation details.

**Assessment:** Keep as **HIGH**.

---

## 4. HIGH-2 identifies the right problem, but its proposed solution is insufficient

The report correctly identifies a long-lived-session logging problem.

`minion-assist` rebuilds model-visible request context every turn. That can include:

- a very large bootstrap block,
- skills,
- tool schemas,
- relevant memories,
- task state,
- budget state,
- other prompt/context sections.

Relevant memory is recomputed for each turn and deliberately stays outside ordinary conversation history.

The report proposes:

```text
header changed
→ log full header

header unchanged
→ log only a hash
```

This does not solve the workload well because a small dynamic component may change nearly every turn.

For example:

```text
bootstrap         15,000 tokens  unchanged
skills             1,000         unchanged
tool schemas        3,000         unchanged
memory recall         500         changed
budget context          30         changed
```

The whole assembled header changes, causing another ~19K-token full header to be stored even though only a few hundred tokens are new.

### Recommended refinement: component-level content addressing

Represent the reconstructable request header as references to components:

```text
RequestHeader
    model_config_ref
    system_base_ref
    skills_ref
    tools_ref
    memory_context_ref
    task_context_ref
    budget_context_ref
```

Store large model-visible components by content hash:

```text
ContentArtifact
    hash
    content
```

Only a previously unseen component must be stored in full.

A request header then becomes a small composition record:

```text
request/header
    bootstrap: sha256:abc
    tools: sha256:def
    memory: sha256:ghi
    ...
```

Exact reconstruction remains possible:

```text
log
 ↓
resolve content hashes
 ↓
reconstruct exact request
 ↓
compare with dispatched request
```

The stable 15K bootstrap block is therefore stored once even if a 500-token memory section changes on every turn.

The exact API/storage design can differ, but the semantic rule should be:

> **Reconstruct request state from content-addressed components, not repeated monolithic snapshots.**

**Assessment:** Keep the **HIGH** severity, but replace the proposed whole-header deduplication mechanism.

---

## 5. HIGH-3 `ctx.subprocess` is definitely justified

The report is correct that `ctx.subprocess` should no longer be deferred.

The current MCP implementation uses stdio transports that require a long-lived spawned child process with direct stdin/stdout protocol framing. That is fundamentally different from shell execution.

Conceptually:

```text
ctx.shell
    "execute this shell command and return its result"

ctx.subprocess
    "spawn argv directly and expose process/stdin/stdout/stderr lifecycle"
```

MCP needs the second category.

The same seam is also naturally useful for:

- LSP integrations,
- browser/worker processes,
- remote execution adapters,
- future process-based subagents.

It also fits the already-decided execution-world model:

```text
ctx.fs
ctx.shell
ctx.subprocess
```

can declare an execution-world identity, and integrations that require compatible execution worlds can validate them at activation time.

**Assessment:** Keep as **HIGH** and move `ctx.subprocess` into the execution-seam phase.

---

## 6. MEDIUM-1 session operations need append-only semantics

The report correctly identifies session-level operations such as:

```text
fork
reset
compact-now
```

as runtime/session concerns rather than command-surface concerns.

However, because `minion-agent` uses an append-only log as truth, these cannot be specified only as method names.

For example, `reset()` cannot simply mean:

```text
history.clear()
```

Possible append-only semantics include:

```text
session/reset
    previous surface is no longer included in future derivation
```

or treating reset as creation of a new session identity.

Likewise:

```text
fork(source_session, at_seq)
```

needs explicit ancestry and derivation semantics.

### Recommended refinement

Before session conformance freezes, define:

- what log event represents reset,
- whether reset preserves the same session identity,
- how fork records ancestry,
- whether fork copies or references prior log state,
- how compaction affects branches,
- how derived model-visible history is computed after each operation.

**Assessment:** Keep as **MEDIUM**, but resolve semantics before the session package becomes normative.

---

## 7. MEDIUM-2 should be generalized beyond one hook

The report correctly notes that `tools/pre-execute` may await external human approval for a long time.

The Matrix approval flow waits asynchronously for a reaction from another conversation while unrelated rooms continue operating.

The broader runtime guarantee should be:

> **Awaiting one agent's hook, policy, tool, or external input must not occupy a runtime-global critical section or prevent unrelated agents from progressing.**

This covers more than human approval:

```text
human approval
ask-user interaction
remote tool call
MCP request
slow network service
subagent result
```

A strong conformance scenario is:

```text
agent A blocks in a policy/tool await
agent B completes a full turn normally
```

**Assessment:** Keep as **MEDIUM**, with the guarantee phrased at the agent-isolation level rather than just the pre-execute hook.

---

## 8. MEDIUM-3 background work lifecycle is correct

The report's treatment of background workers is appropriate.

The current workload contains many long-running schedulers/workers, but the immediate foundational requirement is lifetime ownership rather than a generalized job scheduler.

Reversible effects already provide the right primitive:

```text
plugin/fiber activates
    ↓
background task starts as owned effect

plugin/fiber disposes
    ↓
task is cancelled/stopped/unwound
```

A future `ctx.jobs` service should remain deferred until multiple independent consumers require shared scheduling semantics rather than mere owned background lifetime.

**Assessment:** Keep as **MEDIUM**.

---

## 9. MEDIUM-4 per-step overrides are naturally supported

The current application varies several things per invocation, including:

```text
system_suffix
max_history_turns
skip_bootstrap
temporary tools
```

The proposed `agent/pre-step` entry/decision structure can naturally carry prompt and history-window overrides.

Temporary tools should be handled through the scoped-registration hierarchy, especially the transient turn scope, rather than by preserving the current `extra_tools` mechanism.

**Assessment:** Keep as **MEDIUM**, mainly a specification clarification.

---

## 10. Voice is missing from the inventory, but it is not a new core gap

The repository has a substantial voice subsystem:

```text
microphone
   ↓
VAD
   ↓
STT
   ↓
agent
   ↓
TTS
   ↓
speaker
```

It also supports barge-in during TTS playback and changes prompt/history behavior for latency.

This is useful validation because it proves `minion-assist` is not merely a Matrix/text chatbot.

However, voice does not currently require a new `minion-agent` core seam.

The correct layering remains:

```text
voice/channel frontend
       ↓
minion-agent
       ↓
streamed agent events
```

Future voice UX may want interruption to cancel the active LLM/tool turn and immediately steer the agent with new speech. The planned cancellation + steering semantics are already the appropriate general mechanism.

### Recommended report change

Add voice to the capability inventory and stress-test discussion, but explicitly classify it as:

> **NOT A GAP — a separate frontend/channel validating that agent input/output semantics remain channel-neutral.**

---

## 11. Persistence and durable-operation conclusions remain sound

The report's persistence analysis should remain unchanged.

The current workload requires:

- durable conversation history,
- durable conversation identity,
- durable product-level queues and commitments,
- restart continuity.

It does **not** require:

- restoration of an in-flight LLM request,
- restoration of a partially executed tool turn,
- exactly-once turn processing,
- crash-safe outbound delivery.

Therefore the durable operation state machine remains correctly deferred.

The trigger for introducing it should stay narrowly defined:

> **An in-flight turn's side effects must survive process death.**

Until that becomes a real requirement, durable application-level scheduling/queues above the agent loop are sufficient.

---

## 12. Revised severity assessment

| Finding | Review assessment |
|---|---|
| BLOCKER-1 scoped registration / multi-agent | **Correct**, but specify nested scopes and AgentDefinition vs AgentInstance |
| BLOCKER-2 provenance | **Correct**, but use causal InputEnvelopes rather than one singular `origin` |
| HIGH-1 telemetry | **Correct**, with redaction before sinks |
| HIGH-2 request-header volume | **Problem correct; proposed fix insufficient** — use component/content-addressed reconstruction |
| HIGH-3 subprocess | **Correct and strongly supported** |
| MEDIUM-1 session operations | **Correct**, but define append-only semantics |
| MEDIUM-2 blocking hooks | **Correct; generalize to per-agent progress isolation** |
| MEDIUM-3 background lifecycle | **Correct** |
| MEDIUM-4 per-step override | **Correct** |
| LOW image content | **Correct** |
| Isolation realms deferred | **Correct for current workload** |
| Durable operation state machine deferred | **Correct** |
| Voice | **Missing from inventory, but NOT a core gap** |

---

## 13. Recommended design changes before implementation

Before implementation resumes, update the `minion-agent` design in this order:

### 1. Scoped registration and agent lifecycle

Specify nested scope semantics:

```text
root
  ↓
agent-definition
  ↓
agent-instance/session
  ↓
turn
```

Define visibility, ownership, descendant admission, disposal, and agent-instance lifecycle.

Add conformance cases for:

- scoped registration visibility,
- scoped registration ownership,
- scoped event admission,
- nested scope inheritance,
- turn-scope disposal,
- concurrent agents with isolated logs.

### 2. Causal input provenance

Replace singular turn `origin` with:

```text
InputEnvelope(id, message, origin)
Turn.causes[]
```

Require `origin` to be opaque to the runtime but language-neutral / JSON-safe.

Add conformance cases for:

- one-at-a-time claim preserving origin,
- claim-all preserving multiple causes,
- proactive turn with caller-supplied provenance,
- turn completion with no delivered output.

### 3. Telemetry seam

Add a narrow `ctx.telemetry` capability with typed runtime operations and a mandatory sanitize/redact boundary before sinks.

Keep telemetry observational rather than normative.

### 4. Request reconstruction storage

Replace whole-header change detection with component-level/content-addressed request state.

Conformance should verify exact reconstructed model input, not a particular storage implementation.

### 5. `ctx.subprocess`

Move the subprocess seam into the execution phase alongside `ctx.fs` and `ctx.shell`.

Reuse the execution-world compatibility rule across all three.

### 6. Session lifecycle semantics

Specify append-only behavior for:

- reset,
- fork,
- compact-now,
- ancestry/branching.

### 7. Concurrency guarantee

State explicitly that a blocked agent/hook/tool does not prevent unrelated agents from progressing.

---

## Final verdict

The report's overall conclusion should remain:

> **SAFE WITH MINOR DESIGN CHANGES.**

The existing `minion-assist` workload does not expose a hidden architectural contradiction in `minion-agent`.

Even the application's unusual workloads — long-lived Matrix rooms, multiple live conversation instances of one named agent, proactive heartbeat turns, cross-channel approval waits, raw MCP subprocess transports, large dynamic prompt context, background workers, multimodal input, and voice interaction — fit through general-purpose lifecycle, capability, scope, provenance, and execution seams.

The three refinements that materially change the report are:

```text
1. Scoped registration
   → nested:
      root → definition → instance → turn

2. Turn provenance
   → InputEnvelope + causal set
      instead of one turn.origin

3. Request/header storage
   → content-addressed/component-level reconstruction
      instead of whole-header changed-or-hash
```

With those changes incorporated before Phase-0/Phase-1 conformance freezes, the current design remains a credible foundation for rebuilding `minion-assist` and for future agent applications beyond the current chatbot workload.
