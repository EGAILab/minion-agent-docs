# Validating the `minion-agent` design against `minion-assist`

**Date:** 2026-08-18
**Status:** Validation report. Blocks freezing the `minion-agent` design.
**Validates:** `minion-agent-docs/design/2026-08-18-minion-agent-design.md`
**Workload:** `E:\AI\Projects\OpenMinds\Minions\Minion-Assist\minion-assist` (~42,400 lines Python)

`minion-assist` is a live personal assistant with Matrix support. It is used
here as a design-validation workload: a real application that the proposed
`minion-agent` foundation must be able to carry once `minion-assist` is rebuilt
on top of it.

**Rebuild strategy assumed** (confirmed, not inferred): a genuine rewrite —
tools become async and register on `ctx.tools`, background workers become
plugins, and history moves to the session log as the source of truth. No
sync-to-async bridging seam is required in `minion-agent` core, so every
finding below is judged on architecture rather than migration convenience.

---

## 1. What `minion-assist` actually is

Read from source, following runtime paths rather than documentation.

### Execution model

`AgentSession` (`agents/session.py`, 1,461 lines) is the agent. Its entry point
`send()` is **synchronous** and serialized by a `threading.Lock`; `_send_locked`
does the work. Matrix runs `matrix-nio` in its own thread and event loop
(`matrix/channel.py::_run_loop`) and crosses into the agent with
`loop.run_in_executor(None, _run_sync)` (`matrix/handler.py:596`).

Concurrency is **per-room, not global**. `minion.py` builds a per-agent session
*factory*; the Matrix handler lazily constructs and caches one `AgentSession`
per `(agent_id, room_id)` for process life (`_get_or_build_session`). Each has
its own `session_id` and history but shares that agent's provider, tools,
memory service, and compactor. Turns within a room serialize on the lock; turns
in different rooms run concurrently in the thread pool.

Session identity is durable: `MatrixRoomSessionManager` persists
`(room_id, agent_id) -> session_id` in SQLite so a room's conversation survives
restart, with `rebind()` for `/session` switching.

### Per-turn variation

`send()` takes six parameters that vary per call:

| Parameter | Purpose |
|---|---|
| `extra_tools` | Tools injected for this turn only, via a temporary registry shadowing the permanent one |
| `system_suffix` | Text appended to the system prompt for this turn only |
| `max_history_turns` | Limit provider context without truncating persisted history |
| `skip_bootstrap` | Omit the ~15k-token workspace block (voice mode) |
| `channel` | Room identity, for scoping extracted commitments |
| `verify_fn` | Post-turn callback whose result is injected as the next turn's user message |

`extra_tools` is the sharpest case. `ReactToMessageTool` is constructed per turn
bound to a specific `room_id`, `event_id`, **and the running event loop**, and is
offered only in rooms whose `reaction_level != "off"`. Per-room `system_prompt`
comes from room config. So two concurrent turns for the same agent legitimately
see different tool sets and different system prompts.

### Background and unsolicited work

Roughly ten scheduler/worker threads start in `minion.py`: heartbeat, dreaming,
memory consolidation, knowledge digest, retention, reconciliation, capture,
commitment, message-embedding, image-caption, plus a filesystem watcher.

`HeartbeatScheduler` is the important one. On each tick it runs a full agent turn
that **nobody asked for**, injecting `HeartbeatRespondTool` and — when
commitments are due — `RespondToCommitmentTool`/`DismissCommitmentTool`. Its
output is then routed conditionally:

- `HEARTBEAT_OK` → suppressed entirely; nothing is delivered anywhere.
- Otherwise → `_deliver()` to the configured notification room, **or**
  `_deliver_to_channel()` to the room stored on the specific commitment being
  answered, looked up from the database rather than inferred from the turn.

### Human-in-the-loop across channels

`MatrixExecApprovalHandler` sends a DM to an approver and waits up to 60 seconds
for a ✅/❌ reaction, bridging back to the blocking tool via
`asyncio.run_coroutine_threadsafe`. A tool call in room A can therefore block on
a human reacting in room B while other rooms keep running.

### Prompt construction

`build_prompt_section()` searches memory and renders a `<relevant_memories>`
block into the system prompt, under a token budget, with citations. Its docstring
is explicit and the behavior is deliberate:

> Rebuilt fresh every turn — the injected block lives only in this turn's system
> prompt (**never written into `AgentSession._history`**), so a past turn's
> injection is never visible to the model on a later turn.

Bootstrap context (`AGENTS.md`, `SOUL.md`) is likewise a per-turn closure so file
edits take effect without restart. Task context and budget context are also
assembled per turn.

### Other surfaces

- **Slash commands** are intercepted before the model (`dispatch_command`) and
  can mutate session state: `switch_session`, `compact_now`, `reset`, `fork`,
  plus rebinding the room's persisted session.
- **Subagents** spawn a fresh `AgentSession` in a daemon thread with a
  parent/child chain, depth ≤ 4 and ≤ 5 children (`spawn_registry.py`).
- **MCP** spawns stdio server subprocesses and frames JSON-RPC over their pipes
  (`mcp/client.py`); the browser tool launches Playwright Chromium.
- **Persistence** spans JSONL short-term history per `(agent, session)`,
  PostgreSQL (sessions, messages, mirrors, capture/commitment/embedding job
  queues, commitments, tombstones, captions), and Markdown memory files that
  ADR-0001 makes canonical with every index derived.
- **Plugins** load from a `plugins.json` manifest contributing tools, before/after
  tool hooks, skills, and commands.

---

## 2. Findings

Severity is judged against the question "must this change before `minion-agent`
Phase 1 is implemented?" — because Phase 1 fixes the service-resolution
semantics that several findings depend on.

### BLOCKER-1 — Isolation realms are required on day one, not deferred

**Evidence.** Three independent capability-variation requirements exist in
`minion-assist` today:

1. Per-room tool sets — `ReactToMessageTool` is offered only where
   `reaction_level != "off"`, constructed per turn bound to `room_id`/`event_id`.
2. Per-room system prompts — `room_cfg.system_prompt` becomes `system_suffix`.
3. Subagents — `spawn_registry.py` enforces a parent/child chain with depth and
   fan-out limits; children get their own provider, tools, workspace, and
   `enable_memory_extraction=False`.

**Design.** §9's deferral table reads:

> | Isolation realms | Subagents, or per-session capability presets. The service registry is designed so realms slot in without rework. |

Both stated triggers are met by the validation workload before a line of
`minion-assist` is rewritten. §3 further states, normatively, that **child
contexts cannot shadow parent services in this phase**, and that registration is
exclusive per `(name, realm)`.

**Why it matters.** With one realm and exclusive registration there is exactly
one `tools` service for the whole process. Two concurrent agents — or the same
agent in two rooms — cannot see different tool sets. The current design's answer
would be either a second, non-service tool path (bypassing the framework) or
per-request filtering bolted onto request assembly, which puts capability scoping
somewhere other than the service layer that owns it.

The claim "the service registry is designed so realms slot in without rework" is
**asserted, not demonstrated**. Phase 1 is precisely where service resolution is
built and pinned by conformance scenarios. Building it, freezing its scenarios,
and then discovering realms need different resolution semantics is the expensive
ordering.

**Where the fix belongs.** `minion-agent`.

**Smallest change that resolves it.** Do not necessarily *implement* realms in
Phase 1 — but *specify* them in §3 now, and extend the Phase 0 `runtime/`
conformance family with realm scenarios (a child realm resolving a different
provider for the same name; a dependent in one realm unaffected by another
realm's revocation). If those scenarios can be written against the current
resolution rules, the slot-in claim is demonstrated and implementation can wait.
If they cannot, the resolution design changes now, at zero cost, instead of after
Phase 1's scenarios are normative.

### BLOCKER-2 — No seam for turns that no one requested, or output no one receives

**Evidence.** `HeartbeatScheduler._run_heartbeat()` calls
`session.send(heartbeat_prompt, extra_tools=[...])` on a timer. The result is
suppressed when it equals the `HEARTBEAT_OK` sentinel, and otherwise routed
either to a configured notification room or — per commitment — to the room read
from the commitment row. Dreaming and consolidation follow the same shape.
The Matrix handler independently drops replies that are heartbeat
acknowledgements (`is_heartbeat_ok(reply_text)`).

**Design.** §6's loop is prompt-driven. The inbox has `followup`, `steer`, and
`inject`, all of which describe *input*. `turn/end` carries a reason. Nothing in
the design describes **where a turn's output goes** or **whether it goes
anywhere**; the implicit assumption, inherited from a coding agent, is that
whoever prompted the agent receives the result.

**Why it matters.** A persistent assistant generates output on its own schedule
and must decide, per turn, whether to speak and to whom. If the loop has no
notion of turn provenance and delivery, `minion-assist` must maintain that
mapping outside the framework, keyed by session id — a second state model, which
the brief explicitly flags as a smell. Worse, "should this be delivered" is
decided by inspecting the assistant's *text* for a sentinel token, which is a
protocol living in the wrong layer.

**Where the fix belongs.** `minion-agent`. Output routing itself belongs in the
channel plugin, but the *provenance* a router needs is loop state.

**Smallest change that resolves it.** Two additions, both small:
1. Inbox messages carry an opaque, caller-supplied `origin` that survives into
   `turn/end`, so a channel plugin can route a turn's outcome without keeping its
   own side table.
2. State explicitly in §6 that a turn may complete with no delivery, and that
   delivery is a channel-plugin concern rather than a loop guarantee.

Neither requires changing the turn/step machinery.

### HIGH-1 — Multi-agent concurrency is unspecified

**Evidence.** `minion-assist` runs one `AgentSession` per `(agent_id, room_id)`,
all concurrent, all sharing per-agent provider/tools/memory/compactor instances.
A working deployment has several agents across many rooms.

**Design.** §2's layout lists `agent/` as "Agent interface, registry, `agent/*`
events, Inbox", but §6 describes "the agent loop" in the singular throughout.
`agent/status` is described as "the settle signal" without saying whose. Nothing
specifies how N concurrent agents coexist over one context tree, how services are
shared versus per-agent, or what `ctx.agent_loop.create()` returns and owns.

DSH — the reference this design follows — is explicit here: `ctx.agents` with
`create`/`resume`, an `AgentHandle` owning exact teardown, per-agent scoped
contexts via `core/scope`, and documented co-ownership between the caller fiber
and the loop provider.

**Why it matters.** Multi-agent concurrency is not an extension of single-agent;
it determines the shape of the agent service, teardown ownership, and what
`agent/*` events carry. Retrofitting it after Phase 3 means rewriting the loop's
public surface.

**Where the fix belongs.** `minion-agent`.

**Smallest change.** Add a subsection to §6 specifying the agents registry:
creation and resume, the handle and its teardown, per-agent scoped context, and
that every `agent/*` event identifies its agent. Interacts with BLOCKER-1 — the
per-agent scoped context is the natural home for per-agent capability variation.

### HIGH-2 — `ctx.subprocess` is required, not deferred

**Evidence.** `mcp/client.py` spawns stdio MCP servers and frames JSON-RPC over
their pipes (`StdioServerParameters`, `stdio_client`); shutdown "releases stdio
subprocesses". `tools/browser.py` launches Playwright Chromium or attaches over
CDP.

**Design.** §9 defers `ctx.subprocess` until "a PTY terminal tool, an LSP
integration, or a subagent over a spawned process", reasoning that with only the
bash tool in scope it would be "a seam with one consumer that immediately
delegates".

**Why it matters.** The deferral was correct for the scope it was written
against and is invalidated by this workload. MCP stdio is exactly the case DSH's
`ctx.subprocess` README names — `'pipe'` handing the caller raw streams for its
own protocol framing. Routing MCP through `ctx.shell` would mean shell-
interpreting argv for a JSON-RPC transport, which is wrong on both correctness
and safety grounds.

**Where the fix belongs.** `minion-agent`.

**Smallest change.** Move `ctx.subprocess` out of the deferral table and into
Phase 6 beside `ctx.fs` and `ctx.shell`, with `ctx.shell`'s local provider
spawning through it as DSH does. No architectural change — the seam was already
designed, just postponed.

### HIGH-3 — Scheduled and background work has no home

**Evidence.** Ten scheduler/worker threads, each with start/stop lifecycle,
liveness tracking (`WorkerHealth`), and degraded modes defined by ADR-0004.
Several enqueue durable jobs into PostgreSQL tables and resume after restart.

**Design.** No mention of scheduled or background work anywhere. DSH has
`ctx.jobs` as a first-class service with `job_*` tools.

**Why it matters.** These are not incidental. A persistent assistant is mostly
*not* in a turn; background work is its steady state. Every worker needs
lifecycle tied to plugin load/unload, and reversible effects are exactly the
right primitive — but only if the design says background work is a thing plugins
do, and how a worker's lifetime binds to its fiber.

**Where the fix belongs.** Mostly `minion-assist` (the individual workers are
product logic). The *seam* belongs in `minion-agent`.

**Smallest change.** State in §7 that long-running background work is registered
as a fiber effect and unwinds with its plugin, and note `ctx.jobs` as a deferred
seam with a trigger. This mostly formalizes what effects already give you; the
value is in saying it, so ten plugins do not each invent thread management.

### MEDIUM-1 — `request/header` growth under a long-lived assistant

**Evidence.** Every turn assembles a system prompt containing a ~15k-token
bootstrap block (`skip_bootstrap` exists specifically to skip it for latency),
a freshly-rendered `<relevant_memories>` block, task context, and budget
context. A room's session lives for months.

**Design.** §5 makes "model-visible means logged" a runtime invariant, and §8's
agent-loop invariant re-derives each request from the log and fails on
divergence. Since the memory block is deliberately not a message, the only place
it can be logged is `request/header`.

**Why it matters.** Logging a fully assembled 15k+-token system prompt on every
step is correct and unaffordable at this lifetime. The alternative — logging a
digest — weakens the invariant to "the header we recorded matches", which no
longer proves the model saw what the log says.

This is not a conflict with the deliberate non-logging of memory injection: that
design is sound and compatible, because the system prompt is header state rather
than surface state. The problem is purely volume.

**Where the fix belongs.** `minion-agent`.

**Smallest change.** Specify `request/header` as **change-triggered rather than
per-step**: log the full assembled header when it differs from the last logged
one, and a content hash otherwise. DSH already hints at this shape ("the latest
snapshot reconstructs the request header"; `request/context` is "logged only
when the route or capacity changes"). The invariant then checks the hash against
the reconstruction, preserving its force at constant cost.

### MEDIUM-2 — Non-model command surface

**Evidence.** `dispatch_command` intercepts slash commands before any LLM call
and mutates session state: `switch_session()`, `compact_now()`, `reset()`,
`fork()`, plus persisted rebinding. It runs identically from the CLI and from
Matrix.

**Design.** No command seam. DSH has `ctx.commands` ("register on `ctx.commands`;
it dispatches without a model turn").

**Why it matters.** The command *vocabulary* is product-level and belongs in
`minion-assist`. But the *operations* commands perform are session-service
operations, and if the session service does not expose them, `minion-assist`
reaches around the framework to manipulate session state.

**Where the fix belongs.** Split. Vocabulary and dispatch: `minion-assist`.
The operations: `minion-agent`'s session service must expose switch, fork, reset,
and compact-now as first-class API.

**Smallest change.** Enumerate those four operations in §5 as part of the session
service surface. No command seam needed in core.

### MEDIUM-3 — Live session rebinding

**Evidence.** `/session <id>` switches a room's live `AgentSession` to a
different session in place (`switch_session()`), and the handler then persists
the rebinding so it survives restart.

**Design.** §6 creates an agent bound to a session id. Nothing describes swapping
a live agent's underlying session, and the log-as-truth model makes it
non-obvious — history is derived from *a* log, so switching logs mid-life needs
defined semantics for in-flight turns.

**Where the fix belongs.** `minion-agent`.

**Smallest change.** State that session rebinding is only legal while the agent
is idle, and that it is a session-service operation (see MEDIUM-2). Rejecting it
during a running turn is a one-line rule that removes the entire question.

### MEDIUM-4 — Tool execution may block on a human in another channel

**Evidence.** `MatrixExecApprovalHandler.request_approval()` waits up to 60
seconds for a reaction in a DM while the tool call, and its turn, are suspended.
Other rooms continue running.

**Design.** `tools/pre-execute` is an async waterfall, which handles this
naturally — better than the current thread-bridged implementation.

**Why it matters.** Only because it must be *stated*. A pre-execute listener that
awaits human input for a minute is a legitimate, intended use, and an
implementation that assumes hooks are fast (a shared lock, a global timeout, a
serialized dispatch) would break it silently.

**Where the fix belongs.** `minion-agent`, as a documented guarantee.

**Smallest change.** One sentence in §6's decision-algebra section: `tools/*`
listeners may await indefinitely and must not block other agents' progress; add
a conformance scenario with a pre-execute listener that blocks while a second
agent completes a turn.

### MEDIUM-5 — Per-turn request overrides

**Evidence.** `system_suffix`, `max_history_turns`, `skip_bootstrap`,
`extra_tools` all vary per call.

**Design.** §6's `agent/pre-step` returns `Reject | Enter(messages)` and can
supply replacement model/thinking/context, carrying a `PreStepReason`. That
covers the prompt and history cases. It does **not** obviously cover
`extra_tools`, which is capability scoping and therefore folds into BLOCKER-1.

**Where the fix belongs.** `minion-agent`.

**Smallest change.** Confirm in §6 that `Enter` may carry system-prompt and
history-window overrides for that step. Tool-set variation is resolved by
BLOCKER-1, not here.

### LOW-1 — Image and attachment vocabulary

Matrix images are downloaded and staged through the same path as the REPL's
`/attach`, then passed to `send(attachments=[...])`. §4's content blocks cover
text/thinking/tool_call. Image content blocks exist in pi's vocabulary and are
implied by §7's read tool, but §4 does not list them.

**Fix:** `minion-agent`. Add image content blocks to §4's vocabulary explicitly.

### LOW-2 — Matrix affordances need no core support

Dedupe, allowlist, mention gating, bot-loop suppression, ack reactions, typing
indicators, thread-reply cosmetics, and E2EE's absence (ADR-0005) are all pure
channel-plugin concerns with no core impact. Recorded to confirm they were
examined, not overlooked.

### LOW-3 — Streaming

`minion-assist` supports token streaming in the CLI and explicitly defers it for
Matrix ("Streaming draft-preview is deferred (TODO)"). §4's chunk vocabulary
covers what is needed. No gap.

---

## 3. Responsibility mapping

| `minion-assist` component | Becomes |
|---|---|
| `agents/session.py::AgentSession` | `ctx.agent_loop` driver + `ctx.sessions` log; per-turn overrides via `agent/pre-step` |
| `agents/runner.py::run_turn` | The loop's step machinery (core) |
| `agents/events.py` | `agent/*` and session events; the pi event-stream projection |
| `context.py::Compactor` | `ctx.compaction` |
| `tools/registry.py` + `tools/base.py` | `ctx.tools` |
| `tools/policy.py::PermissionPolicy` | A policy plugin on `tools/pre-execute` |
| `matrix/exec_approvals.py` | An approval plugin on `tools/pre-execute` |
| `plugins.py` manifest loader | Entry-point plugin discovery; hooks become `tools/*` listeners |
| `providers/*` | `ctx.llm` adapters (`openai-completions`, `codex-responses`) |
| `session/db.py`, `memory/short_term.py` | Session log backend + `minion-assist`-owned product tables |
| `matrix/*` | A channel plugin (`minion-assist`) |
| `heartbeat.py`, `dreaming.py`, `memory/*_scheduler.py`, `*_worker.py` | Background plugins registering effects (`minion-assist`) |
| `memory/*` (service, files, knowledge, consolidation, commitments) | `minion-assist` product layer; injects via `agent/pre-step` |
| `commands.py` | `minion-assist` dispatch over core session operations |
| `spawn_registry.py`, `tools/task.py` | `minion-assist` policy over core subagent support |
| `mcp/client.py` | An MCP plugin over `ctx.subprocess` |
| `config.py`, `auth/codex_auth.py` | `minion-assist` config; auth via `ctx.llm`'s credential seam |

## 4. Concepts that must NOT move into `minion-agent`

- Matrix vocabulary of any kind: rooms, threads, reactions, typing, dedupe,
  allowlists, mention gating, bot-loop suppression.
- The `HEARTBEAT_OK` sentinel protocol. Whether a turn produces user-facing
  output is a routing decision (BLOCKER-2), not a string convention in core.
- The entire memory system — canonical Markdown, PostgreSQL index,
  consolidation, dreaming, commitments, digests, forgetting. This is the
  product.
- `PermissionPolicy`'s workspace containment and SSRF specifics.
- Agent personas and their bootstrap files (`SOUL.md`, `AGENTS.md`, `USER.md`).
- Spawn depth and fan-out limits — policy over a core capability.
- The slash-command vocabulary.
- `config.json`'s schema.

## 5. Deferred features this workload actually requires

| Deferred in §9 | Required? | Basis |
|---|---|---|
| Isolation realms | **Yes, day one** | Per-room tool sets, per-room prompts, subagents (BLOCKER-1) |
| `ctx.subprocess` | **Yes** | MCP stdio servers, Playwright (HIGH-2) |
| Durable operation state machine | **No** | `minion-assist` drops in-flight turns on restart today and this is acceptable; what must survive is *job queues*, which are product tables, not agent-loop state |
| Declarative loader / HMR | **No** | `config.json` plus code-level composition is sufficient |

The durable-state-machine conclusion is worth emphasizing, since it is the
largest deferred item: this workload does **not** justify it. Restart-safety in
`minion-assist` comes from durable job queues and persisted room→session
bindings, both of which sit above the agent loop.

## 6. Verdict

**Safe to implement after resolving two blockers and three HIGH findings.** The
architecture is sound: log-as-truth, the imperative driver, reversible effects,
package-owned invariants, and the capability-seam split all survive contact with
a real long-lived assistant without strain. Nothing found requires rethinking the
foundation.

What the workload exposes is that the design was scoped against a **coding
agent** — one user, one workspace, one conversation at a time, output returned to
whoever asked. A persistent assistant breaks four of those assumptions at once:
many concurrent conversations with different capabilities, work it starts
itself, output that may go nowhere or somewhere unrelated, and a lifetime
measured in months rather than a session.

Two of the resulting gaps are blockers specifically because Phase 1 pins
service-resolution semantics with normative conformance scenarios, and both
touch that layer. Resolving them costs design time now and rework later.

**Recommended order before implementation resumes:**

1. **BLOCKER-1** — specify realms in §3 and write realm conformance scenarios in
   Phase 0. This validates the "slot in without rework" claim while it is still
   free to be wrong.
2. **BLOCKER-2** — add inbox `origin` provenance surviving to `turn/end`, and
   state that turns may complete undelivered.
3. **HIGH-1** — specify the agents registry, handles, and per-agent scoped
   context in §6.
4. **HIGH-2** — move `ctx.subprocess` into Phase 6.
5. **HIGH-3** — state that background work is a fiber effect; note `ctx.jobs` as
   a deferred seam.

The MEDIUM findings are seam additions and wording that can be folded into the
spec during the same pass. The LOW findings can wait.

Plan 1 (Phases 0–1) needs revision before execution: Phase 0's conformance
families gain realm scenarios, and Phase 1's service-resolution tasks change if
BLOCKER-1's scenarios cannot be satisfied by the current rules.
