# Foundation validation: `minion-agent` against the `minion-assist` workload

**Date:** 2026-08-18
**Status:** Validation report. Blocks freezing the `minion-agent` design.
**Validates:** `minion-agent-docs/design/2026-08-18-minion-agent-design.md`
**Workload:** `Minion-Assist\minion-assist` (~42,400 lines Python)
**Supersedes:** `2026-08-18-minion-assist-design-validation.md`, which was written
to a narrower standard and contains one finding now known to be wrong (see
§11.1).

## The standard

Not "can the existing code migrate" — a substantial rewrite is expected and
preferred. Not even "can every current capability be rebuilt." The standard is:

> Can we rebuild a substantially better `minion-assist` naturally on top of
> `minion-agent`, while leaving `minion-agent` a clean, general foundation for
> future agent applications we have not designed yet?

`minion-assist` is treated as a **workload inventory**, not a target
architecture. Its abstractions, package boundaries, and implementation choices
carry no authority. Evidence from it establishes *requirements*; it never
establishes *designs*.

Two failure modes are guarded against throughout:

- **False gaps** — calling something missing because current classes do not map.
- **Overfitting** — adding a seam shaped like this product rather than the
  general class of requirement behind it.

Every proposed change below is checked against: is this a general
agent-runtime concern? Would it make sense for a different application? Does it
preserve composability, reactive service replacement, language-neutral
conformance, and Python/Rust portability?

---

## 1. What the workload actually does

Read from source, following runtime paths.

**Execution.** `AgentSession.send()` is synchronous, serialized by a
`threading.Lock`. Matrix runs `matrix-nio` in its own thread and event loop,
crossing into the agent via `run_in_executor`. Concurrency is per-room: one
`AgentSession` per `(agent_id, room_id)`, lazily built and cached for process
life, each owning its own `session_id` and history while sharing that agent's
provider, tools, memory service, and compactor. `MatrixRoomSessionManager`
persists `(room_id, agent_id) -> session_id` in SQLite so a room's conversation
survives restart.

**Per-turn variation.** `send()` accepts `extra_tools` (a temporary registry
shadowing the permanent one), `system_suffix`, `max_history_turns`,
`skip_bootstrap`, `channel`, and `verify_fn`. `ReactToMessageTool` is built per
turn bound to a specific `room_id`, `event_id`, and event loop, and offered only
where `reaction_level != "off"`.

**Unsolicited work.** Ten scheduler/worker threads. `HeartbeatScheduler` runs a
full agent turn on a timer with injected tools; its output is suppressed
entirely when it equals a `HEARTBEAT_OK` sentinel, otherwise delivered either to
a configured notification room or — per commitment — to the room read from the
commitment row, "never something inferred from what room this turn is about."

**Human-in-the-loop across channels.** `MatrixExecApprovalHandler` DMs an
approver and waits up to 60s for a ✅/❌ reaction while the tool call and its
turn stay suspended, bridging back via `run_coroutine_threadsafe`.

**Prompt construction.** `build_prompt_section()` renders a budgeted
`<relevant_memories>` block into the system prompt and is explicit that it is
"never written into `AgentSession._history`", so a past turn's recall cannot
leak forward. Bootstrap (~15k tokens), task context, and budget context are also
assembled per turn.

**Observability.** `llm_logger` writes full request/response bodies with
**known-value secret redaction** against every configured credential.
`WorkerHealth` tracks per-worker liveness; `/status deep` reports it.

**Notably absent.** There is **no cancellation anywhere** in the agent core — a
turn runs to completion. The proposed design is strictly better here.

**Other surfaces.** Slash commands dispatch without a model turn and mutate
session state (`switch_session`, `compact_now`, `reset`, `fork`). Subagents are
fresh sessions in daemon threads with a depth-4 parent chain. MCP spawns stdio
servers and frames JSON-RPC over their pipes; the browser tool launches
Playwright. Persistence spans JSONL history, PostgreSQL (sessions, messages, job
queues, commitments, embeddings, tombstones), and canonical Markdown memory.

---

## 2. Capability inventory

### A — Product behavior (preserve)

Persistent per-conversation history; multiple named agents; concurrent
independent conversations; proactive/scheduled agent activity; commitments
delivered to the conversation they came from; memory recall injected per turn;
compaction; tool use with human approval for dangerous operations; multimodal
input; streaming; slash commands; subagent delegation; skills.

### B — Operational/runtime requirements

Long-lived daemon; many concurrent sessions in one process; background workers
with lifecycle and liveness; provider retry with backoff and jitter; degraded
modes for every dependency (ADR-0004); secret redaction in logs; restart
continuity for conversation identity; per-agent resource sharing.

### C — Integration requirements

Matrix sync lifecycle, inbound events (text and image), outbound send, reactions,
typing, threads (cosmetic only), dedupe, allowlist, mention gating, bot-loop
suppression; MCP stdio servers; OAuth (Codex) and API-key providers; PostgreSQL;
Playwright.

### D — Persistent state requirements

Conversation history; conversation identity across restart; durable job queues
(capture, commitment, embedding); commitments with due times and target
channels; memory artifacts; session metadata and parent chains.

### E — Implementation details to discard

Sync-with-lock execution; thread-per-worker; `AgentSession` as a 1,461-line
god-object; the temporary-registry `extra_tools` mechanism; `plugins.json` as a
manifest format; the `HEARTBEAT_OK` sentinel protocol; JSONL-plus-PostgreSQL
dual history; `dispatch_command`'s shape; the room-session SQLite sidecar; the
`run_in_executor` bridge.

---

## 3. Findings

### BLOCKER-1 — The multi-agent runtime is unspecified, and per-agent scoped registration is missing

**Evidence.** One `AgentSession` per `(agent_id, room_id)`, all concurrent,
sharing per-agent provider/tools/memory/compactor. `ReactToMessageTool` exists
only for the turn and room that created it. Room config supplies a per-room
system prompt. Subagents get their own tools and workspace.

**Requirement extracted.** *N agent instances run concurrently in one process
over one service graph. Most services are shared. Some registrations — tools,
prompt sections, event listeners — must be visible to exactly one agent and must
be disposed with it.*

**Design.** §2 lists an `agent/` package with a "registry", but §6 says "the
agent loop" in the singular throughout and never specifies how N agents coexist,
what creation returns, or who owns teardown. Separately, §3 makes registration
exclusive per `(name, realm)` and every registration a fiber effect — there is
no notion of a registration visible to one agent among many.

**Why it is not naturally supported.** With one realm and exclusive
registration there is exactly one `tools` service process-wide. Two concurrent
agents cannot present different tool sets. The available workarounds are all
bad: a second non-service tool path (bypassing the framework), or filtering
bolted onto request assembly (capability scoping living somewhere other than the
layer that owns capabilities).

**The correction to my earlier analysis.** I previously called this "isolation
realms are required on day one." That was wrong. DSH separates two mechanisms:

- `core/scope` — *scoped registration*. "`createScope(ctx, key)` creates a
  tagged Cordis context whose backing fiber owns every registration made
  through it… **The agent loop creates one scope per live agent**… the mechanism
  is key-agnostic so lower-level packages can use it without depending on
  either."
- `isolate` realms — *replacing a whole service implementation* per realm.

This workload needs the **former** and never the latter: agents share one
`ctx.llm` and select models per request; they need different *registrations*,
not different *services*. So realms can and should stay deferred.

**Where the fix belongs.** `minion-agent`.

**Smallest change.** Three additions to the design:
1. §6 gains an agents-registry subsection: creation and resume, a handle owning
   teardown, and every `agent/*` event identifying its agent.
2. §3 gains scoped registration, with DSH's contract adopted verbatim because it
   is the load-bearing part: *the registration context determines both
   visibility and ownership*, so a registration can never be visible in one
   scope but disposed with another.
3. Event dispatch gains scope filtering with the additive rule — an untagged
   listener is always admitted; a tagged one only for its own key or a
   descendant.

**Why this is general.** Scoping is key-agnostic and mentions no channel,
conversation, or product concept. Any runtime hosting more than one agent needs
it: subagents with restricted tools, per-tenant capability sets, evaluation
harnesses running variants side by side. Point (3) is purely additive, so it
does not disturb Phase 1's event semantics — but it must be *specified* before
Phase 1's conformance scenarios become normative, because visibility-and-
ownership coupling is a contract, not an implementation detail.

### BLOCKER-2 — No provenance or delivery model for a turn

**Evidence.** The heartbeat runs a turn nobody requested. Its result is either
suppressed entirely or routed to a room resolved from a database row, explicitly
"never something inferred from what room this turn is about." The Matrix handler
separately drops replies by sniffing the assistant's text for a sentinel.

**Requirement extracted.** *A turn may be initiated by an actor other than a
user, and its output has no implicit destination. The runtime must let the
initiator's identity travel with the work so a delivery layer can route the
result — including routing it nowhere.*

**Design.** §6's inbox has `followup`, `steer`, and `inject` — all input.
`turn/end` carries a reason. Nothing describes where a turn's output goes or
whether it goes anywhere. The implicit assumption, inherited from a coding
agent, is that whoever prompted receives the result.

**Why it is not naturally supported.** Without provenance, the rebuilt
application must maintain its own session-id-keyed side table mapping turns to
destinations — a second state model tracking something the loop already knows.
And "should this be delivered" ends up decided by inspecting model output for a
magic string, which is a protocol in the wrong layer.

**Where the fix belongs.** `minion-agent` for provenance; the application for
routing.

**Smallest change.** Inbox entries carry an **opaque, caller-supplied `origin`**
that the runtime never interprets and that survives into `turn/end`. Plus one
sentence in §6: a turn may complete without producing any delivered output;
delivery is not a loop guarantee.

**Why this is general.** `origin` is an opaque token — core never learns what a
room, channel, or user is. The same seam serves a webhook-triggered agent, a
cron-triggered agent, a multi-channel deployment, or an eval harness correlating
turns to cases. This is the smallest abstraction that solves the class; a
"channel" or "reply-to" concept in core would be the overfitted version.

### HIGH-1 — No observability seam exists in the design at all

**Evidence.** `llm_logger` records full request/response bodies with
known-value secret redaction against every configured credential (a deliberate
requirement: users read these logs to debug, and memory content may contain
pasted secrets). `WorkerHealth` tracks per-worker liveness surfaced by
`/status deep`. `config_report` enumerates configured secrets.

**Requirement extracted.** *Requests, tool executions, and background work must
be observable with structured, correlatable records, and the runtime must not
leak configured credentials into them.*

**Design.** The word telemetry does not appear. Neither does observability,
tracing, or metrics. This is not a deferral — it is an omission.

Both references treat it as first-class: Pi ships `packages/telemetry` plus a
**generated schema document** with typed spans (`pi.ai.request` with declared
start and end attributes, cardinality notes, and a schema version); DSH lists
`telemetry/*` alongside `fs/*` and `tools/*` as a capability seam attaching
"policy and adapters… without importing the loop."

**Why it matters here specifically.** The design's own validation strategy leans
on log-derived invariants, and its conformance suite asserts traces. An
observability seam is adjacent to both and was simply not written down. It is
also the natural home for redaction: a runtime that logs provider requests must
have a defined place to scrub known secrets, or every application reinvents it.

**Where the fix belongs.** `minion-agent`.

**Smallest change.** Add a section defining `ctx.telemetry` as a capability seam
with a typed span vocabulary for the operations core already owns — provider
request, tool execution, turn, step — plus a redaction hook applied before
emission. Providers are plugins, so a deployment can mount OpenTelemetry, a file
logger, or nothing.

**Why this is general.** It mirrors what both references independently
converged on, mentions no product concept, and is a seam rather than an
implementation. The span vocabulary is also language-neutral, so a Rust
implementation emits the same spans — which the conformance suite can assert.

### HIGH-2 — `request/header` volume under a months-long session

**Evidence.** Every turn assembles a system prompt containing a ~15k-token
bootstrap block (`skip_bootstrap` exists purely to skip it for latency), a
freshly-rendered memory block, task context, and budget context. A room's
session lives as long as the room.

**Requirement extracted.** *A session may run for months across tens of
thousands of steps, with a large, mostly-stable, partly-per-step system prompt.
The log must remain both complete enough to reconstruct requests and bounded
enough to keep.*

**Design.** §5 makes "model-visible means logged" a runtime invariant, and §8's
agent-loop companion re-derives each request from the log and fails on
divergence. Since the memory block is deliberately not a message, its only
logging home is `request/header`.

**Why it is not naturally supported.** Logging a fully assembled 15k+ token
header every step is correct and unaffordable at this lifetime. Logging a digest
instead weakens the invariant from "the model saw what the log says" to "the
header we recorded matches what we recorded."

Note this is *not* a conflict with `minion-assist`'s deliberate non-logging of
recalled memory. That design is sound and compatible: the system prompt is
header state, not surface state. The problem is purely volume.

**Where the fix belongs.** `minion-agent`.

**Smallest change.** Specify `request/header` as **change-triggered rather than
per-step**: log the full header when it differs from the last logged one, and a
content hash otherwise. The invariant then compares the hash against its
reconstruction, preserving full force at constant cost. DSH already gestures at
this shape — "the latest snapshot reconstructs the request header", and
`request/context` is "logged only when the route or capacity changes."

**Why this is general.** Long-lived sessions are a property of assistants,
monitors, and any resident agent — not of chatbots specifically. The change is
a logging-granularity rule, adds no concepts, and strengthens the design against
a class of workload it had not considered.

### HIGH-3 — `ctx.subprocess` is required, not deferrable

**Evidence.** `mcp/client.py` spawns stdio MCP servers and frames JSON-RPC over
their pipes; shutdown "releases stdio subprocesses". `tools/browser.py` launches
Playwright Chromium or attaches over CDP.

**Requirement extracted.** *Spawning a process and speaking a protocol over its
pipes, without shell interpretation.*

**Design.** §9 defers `ctx.subprocess` until "a PTY terminal tool, an LSP
integration, or a subagent over a spawned process", reasoning it would otherwise
be "a seam with one consumer that immediately delegates."

**Why it is not naturally supported.** The reasoning was sound for its scope and
is invalidated by evidence. MCP stdio is exactly the case DSH's subprocess seam
names — raw streams for caller-owned protocol framing. Routing it through
`ctx.shell` would mean shell-interpreting argv for a JSON-RPC transport, wrong
on both correctness and safety.

**Where the fix belongs.** `minion-agent`.

**Smallest change.** Move `ctx.subprocess` from the deferral table into Phase 6
beside `ctx.fs` and `ctx.shell`, with the local shell provider spawning through
it. No architectural change — the seam was already designed, only postponed.

**Why this is general.** MCP is a general tool-integration protocol, not a
personal-assistant feature. Any runtime supporting MCP, LSP, sandboxed
execution, or remote workers needs this seam.

### MEDIUM-1 — Session lifecycle operations are not part of the session surface

**Evidence.** Commands mutate session state directly: `switch_session()`,
`compact_now()`, `reset()`, `fork()`.

**Requirement extracted.** *Forking a conversation, clearing it, and forcing
compaction are operations on a session, invocable without a model turn.*

**Design.** §5 describes the log and derivation but not its mutating operations.

**Where the fix belongs.** `minion-agent` for the operations; the application
owns command vocabulary and dispatch (no `ctx.commands` seam is needed in core).

**Smallest change.** Enumerate fork, reset, and compact-now in §5 as
session-service API.

**Why this is general.** Fork and reset are conversation primitives any agent
application needs; they are already implied by the design's own compaction and
branch-summary discussion.

### MEDIUM-2 — Tool hooks may block indefinitely; the design must guarantee it

**Evidence.** Exec approval suspends a tool call for up to 60 seconds awaiting a
human reaction **in a different conversation**, while other rooms keep running.

**Requirement extracted.** *A pre-execute policy hook may await external input
for an unbounded time without stalling unrelated agents.*

**Design.** `tools/pre-execute` is an async waterfall, which handles this
naturally — better than the current thread-bridged implementation. The gap is
that nothing *states* it, so an implementation could reasonably introduce a
shared lock, a global timeout, or serialized dispatch and break it silently.

**Where the fix belongs.** `minion-agent`, as a documented guarantee plus a
conformance scenario.

**Smallest change.** One sentence in §6's decision-algebra section, and the
scenario in §9 below.

**Why this is general.** Human-in-the-loop approval is a core agent-safety
pattern, not a chat feature.

### MEDIUM-3 — Background work has no stated lifetime contract

**Evidence.** Ten workers with start/stop lifecycle and liveness tracking.

**Requirement extracted.** *A plugin may own long-running background work whose
lifetime is bound to the plugin's.*

**Design.** Silent on background work. Reversible effects already provide
exactly the right primitive.

**Where the fix belongs.** `minion-agent`, as one paragraph — **not** a new
service. `ctx.jobs` would be premature: this workload needs worker lifetime, not
a job-scheduling API, and inventing one now would be designing an imagined
extension rather than an extension point.

**Smallest change.** State in §3 that long-running background work is registered
as a fiber effect and unwinds with its plugin. Note `ctx.jobs` as a deferred seam
whose trigger is a second consumer needing shared scheduling semantics.

### MEDIUM-4 — Per-step prompt and history overrides

**Evidence.** `system_suffix`, `max_history_turns`, `skip_bootstrap` vary per
call.

**Design.** `agent/pre-step` returns `Reject | Enter(messages)` and may supply
replacement model/thinking/context.

**Where the fix belongs.** `minion-agent`, as clarification only.

**Smallest change.** Confirm in §6 that `Enter` may carry system-prompt and
history-window overrides for that step. Tool-set variation is resolved by
BLOCKER-1, not here.

### LOW-1 — Image content blocks absent from §4's vocabulary

§4 lists text, thinking, and tool_call. Images are implied by §7's read tool and
present in Pi's vocabulary, but not stated. Add them.

### NOT A GAP

Recorded explicitly so the rewrite is not slowed by re-litigating them: the
sync-to-async rewrite of tools and providers; `AgentSession`'s class shape; the
dual JSONL/PostgreSQL history model; the Matrix handler's structure; the
`plugins.json` manifest; the `HEARTBEAT_OK` sentinel; live session rebinding (a
rewrite creates a new agent rather than rebinding a running one); thread-based
workers; `PermissionPolicy`'s internal shape; `dispatch_command`'s dispatch
mechanics; the room-session SQLite sidecar; the temporary-registry `extra_tools`
mechanism. Every one of these is replaced by a normal use of the new
architecture.

---

## 4. Concurrency evaluation

The target shape:

```
one long-lived process
  ├── Matrix sync / channel plugin
  ├── room A → agent A (own session, own log)
  ├── room B → agent B
  ├── room C → agent C
  └── shared: ctx.llm, ctx.tools, ctx.fs, memory plugins, schedulers
```

**`Context` and fibers: sufficient.** Services are shared by construction, and
`extend()` gives each agent its own context. Reactive dependency means a
provider swap propagates to every live agent without per-agent bookkeeping.

**Service lifetime versus conversation lifetime: sufficient, and a strength.**
Services live with their plugin fiber; conversations live in the log. The
separation is already correct — a provider can be swapped mid-conversation.

**Session ownership: under-specified.** See BLOCKER-1. Who creates an agent, who
owns teardown, and what happens to a running turn when its owner unloads are
undefined.

**Per-agent capability variation: missing.** See BLOCKER-1. This is the one
foundational concept absent.

**One-active-turn-at-a-time: correct, and should stay.** Per *agent*, serialized
turns are right, and `minion-assist` independently arrived at the same rule with
its per-session lock. Concurrency lives across agents, not within one. No change
needed — worth recording, since the brief flags it as a suspect assumption and
the evidence exonerates it.

**Verdict:** the model is sound; one concept (scoped registration) is missing and
one contract (agent lifecycle) is unwritten.

---

## 5. Persistence and restart evaluation

Assessed against the deferred durable operation state machine.

| Requirement | Needed? | Evidence |
|---|---|---|
| Durable conversation history | **Yes** | Rooms are months-long topics; history survives restart today |
| Durable conversation identity | **Yes** | `room_sessions.db` maps rooms to sessions across restart |
| Durable work queues | **Yes, above the loop** | Capture/commitment/embedding job tables, product-owned |
| Scheduled-job persistence | **Yes, above the loop** | Commitments carry due times and target channels |
| Restoring interrupted model/tool operations | **No** | An in-flight turn is lost on restart today; acceptable |
| Exactly-once processing | **No** | Matrix dedupe is best-effort by event id; nothing requires it |
| Crash-safe outbound delivery | **No** | A reply lost to a crash is not recovered today and no requirement asks for it |

**Conclusion: the durable operation state machine is correctly deferred.** This
is the largest deferred item and this workload does not justify it. Restart
safety comes from durable history, durable identity, and durable *product* job
queues — all of which sit above the agent loop and need nothing from it beyond a
session log that survives.

The deferral's stated trigger ("crash recovery becomes a requirement") should be
sharpened to: *an in-flight turn's side effects must survive process death* —
which is what the machinery actually buys, and what this workload does not need.

---

## 6. Proposed layering

```
minion-agent
  runtime         context, fibers, services, scoped registration, events, effects
  llm             message vocabulary, adapter seam, providers
  sessions        append-only log, derivation, compaction, fork/reset
  agent           agent registry, handles, inbox with origin, agent/* events
  agent_loop      the driver
  tools           registry (scope-aware), execution pipeline
  fs/shell/subprocess   execution seams
  telemetry       span vocabulary, redaction hook
  invariants      registry; checks package-owned

minion-assist
  matrix          channel plugin: sync, inbound events, outbound, reactions,
                  typing, dedupe, allowlist, mention gating, media
  routing         room/user → agent mapping; delivery of turn results by origin
  persona         prompt sections, skills, bootstrap files
  memory          recall injection via agent/pre-step; capture; consolidation
  scheduling      heartbeat, dreaming, digests as plugins owning effects
  policy          approval and permission plugins on tools/pre-execute
  commands        non-model command surface over session operations
  config          product configuration, secrets, provider selection
```

Nothing in the Matrix column needs a concept in the left column. Rooms, threads,
reactions, and device state never cross the boundary. The only thing that must
cross is the opaque `origin` token of BLOCKER-2 — and core never interprets it.

---

## 7. Capabilities that stay exclusively in `minion-assist`

Matrix vocabulary of every kind; the personal-assistant persona and its
bootstrap files; the entire memory system (canonical Markdown, PostgreSQL
index, consolidation, dreaming, commitments, digests, forgetting); permission
policy specifics such as workspace containment and SSRF markers; spawn depth
and fan-out limits; the slash-command vocabulary; product configuration schema;
heartbeat cadence and its suppression protocol; room/user-to-agent routing.

## 8. Deferred features the rebuild actually needs

| Deferred | Needed? | Justification |
|---|---|---|
| Scoped registration *(not currently in the design at all)* | **Yes** | BLOCKER-1 |
| `ctx.subprocess` | **Yes** | MCP stdio, Playwright (HIGH-3) |
| Isolation realms | **No** | Agents need different *registrations*, not different *services*; scoped registration covers it. Correcting my earlier report |
| Durable operation state machine | **No** | §5 |
| Declarative loader / HMR | **No** | Code-level composition plus product config suffices |
| `ctx.jobs` | **No** | Effects give worker lifetime; a scheduling API would be premature |

## 9. Conformance scenarios this validation reveals

New cases the suite should carry, all language-neutral:

**`runtime/`**
- `scoped-registration-visibility` — a registration made through scope A is
  invisible to scope B; an unscoped registration is visible to both.
- `scoped-registration-ownership` — disposing scope A removes exactly its
  registrations and leaves B's intact.
- `scoped-event-admission` — an untagged listener receives every dispatch; a
  tagged listener receives only its own key's.

**`agent/`**
- `concurrent-agents-isolated-logs` — two agents run turns concurrently; neither
  log contains the other's entries.
- `origin-survives-to-turn-end` — an inbox entry's opaque origin is reported at
  `turn/end` unchanged.
- `turn-completes-undelivered` — a turn completes normally with no delivered
  output.
- `blocking-pre-execute-does-not-stall-peers` — a pre-execute listener blocks
  while a second agent completes a turn.
- `request-header-change-triggered` — an unchanged header logs a hash; a changed
  one logs in full; the invariant passes in both cases.

---

## 10. Foundation stress-test

### Evidence-backed: where the design is overfitted to a coding agent

1. **"The agent loop", singular.** §6 never contemplates N agents. A coding
   agent has one user, one workspace, one conversation.
2. **Implicit delivery.** Prompt in, response out, to whoever asked. A resident
   agent produces output on its own schedule, to destinations chosen per turn.
3. **Session lifetime ≈ process lifetime.** `request/header` per step is fine for
   a session of hundreds of steps and untenable for tens of thousands.
4. **No observability.** A CLI tool shows you the terminal. A daemon needs
   structured, correlatable records — and both references have them.

### Reasonable extrapolation (stated, not designed)

Scoped registration generalizes beyond agents to any multi-tenant registration —
eval harnesses running variants, per-request policy overlays. The `origin` token
generalizes to any non-user initiator. Neither should be built beyond what
BLOCKER-1 and BLOCKER-2 specify.

### Speculative — explicitly not influencing the design

Distributed services, alternative persistence backends, remote sandboxes,
multi-node agents, richer multimodal I/O, new provider protocols. Each has a
plausible path through the existing seams (`ctx.fs`/`ctx.shell` for remote
execution, `ctx.llm` for protocols, the session backend for persistence). None
justifies design work now. Recorded so a future reader can see they were
considered and deliberately excluded.

### Where the design holds up well

Worth stating, since a validation that only finds faults is not a validation:
log-as-truth survives a long-lived multi-session application unchanged;
reversible effects are exactly right for background workers and dynamic
capability; reactive service replacement handles provider swaps that
`minion-assist` currently cannot do at all; per-agent turn serialization is
independently confirmed correct; and the design's cancellation model is
strictly better than the workload's, which has none.

---

## 11. Corrections to the superseded report

**11.1** The earlier report called isolation realms a day-one blocker. That was
wrong: it conflated realms with scoped registration. Realms replace a whole
service per realm; this workload needs per-agent *registrations* over shared
services. Realms remain correctly deferred; scoped registration — a mechanism the
design does not currently contain in any form — is the actual gap.

**11.2** The earlier report missed the absence of any observability seam
entirely (now HIGH-1).

**11.3** The earlier report rated background work HIGH and implied `ctx.jobs`.
Downgraded to MEDIUM and reframed as a documentation contract, because effects
already provide the mechanism and a scheduling service would be premature.

---

## 12. Verdict

**SAFE WITH MINOR DESIGN CHANGES.**

No foundational revision is required. The architecture — log-as-truth, imperative
driver, reversible effects, package-owned invariants, capability seams — survives
contact with a long-lived, multi-conversation, self-scheduling application
without strain. Several of its choices are validated rather than merely
tolerated.

What the workload exposes is that the design was scoped against **one agent,
one conversation, one requester, one sitting**. Relaxing those four assumptions
requires one genuinely missing concept (scoped registration), one small
provenance addition, one absent seam (telemetry), one logging-granularity rule,
and one un-deferral (`subprocess`). All five are additive; none rewrites an
existing contract.

The two blockers are blockers by *timing* rather than magnitude: both touch
contracts that Phase 0 and Phase 1 turn into normative conformance scenarios.
Resolving them costs design time now; deferring them costs rework of frozen
semantics.

**Order before implementation resumes:**

1. BLOCKER-1 — specify the agents registry (§6) and scoped registration (§3),
   with the visibility-equals-ownership contract; add the three `runtime/`
   scenarios to Phase 0.
2. BLOCKER-2 — add opaque `origin` to inbox entries, surfacing at `turn/end`;
   state that turns may complete undelivered.
3. HIGH-1 — add a `ctx.telemetry` section with a span vocabulary and redaction
   hook.
4. HIGH-2 — make `request/header` change-triggered.
5. HIGH-3 — move `ctx.subprocess` into Phase 6.

The MEDIUMs are wording and can ride along in the same pass. Plan 1 then needs a
revision: Phase 0 gains the runtime scenarios above, and Phase 1's service and
event tasks gain scope-awareness.
