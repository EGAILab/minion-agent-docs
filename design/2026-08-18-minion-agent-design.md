# Minion Agent — Design

**Date:** 2026-08-18
**Status:** Approved design; implementation plan pending.

Minion Agent preserves the functional scope and semantics of Pi `agent-core`
(`packages/agent`) while rebuilding the architecture on Cordis principles:
plugin lifecycle, service dependency, typed events, and reversible effects.

Python is the first implementation. The behavioral specification and the
conformance suite are language-neutral so a Rust implementation can be
validated against the same files.

## Reference material

Studied at these revisions:

| Project | Revision | Used for |
|---|---|---|
| `earendil-works/pi` | `209bc7b`, 2026-08-17 | Behavioral semantics of `agent-core`; `packages/ai` provider vocabulary; `packages/evals` model-backed tier |
| `deepseek-ai/deepseek-harness` | checkout of 2026-08-18 | Cordis architecture at scale; loop driver; capability seams; invariants; test strategy |
| `cordiverse/cordis` | checkout of 2026-08-18 | Plugin runtime semantics: context, fiber, service, registry, events, effects |
| `cordiverse/paper` | Draft of 2026-08-13 | Revertible effects and reactive coeffects, the theory behind Cordis |

Statements about these projects in this document were verified against the
checked-out source, not from memory.

---

## 1. Scope

### In scope

Pi `agent-core` divides into three strata. This design covers the first two.

**Stratum A — the agent loop.** `types.ts`, `agent-loop.ts`, `agent.ts`. The
message/tool/state vocabulary, the event stream, tool execution modes, the
hook points, queue handling, abort and settlement semantics. This is the
densest behavioral surface and the primary conformance target.

**Stratum B — harness essentials.** Execution capability seams, built-in tools
(bash, read, write, edit, glob, grep), system-prompt and skill assembly,
compaction, and session persistence.

### Deferred

**Stratum C — the durable operation state machine** described in pi's
`docs/harness.md`: three stores, atomic transactions, the durable program
counter, the effect sandwich, per-tool replay policy, lanes, and crash
recovery. This is a substantial project on its own. The session service is
designed so a durable backend is added behind its existing interface rather
than by restructuring.

Also deferred, with the trigger for each recorded in §9: Cordis's declarative
YAML loader, hot module replacement, isolation realms, and the
`ctx.subprocess` seam.

---

## 2. Repository layout

```
minion-agent/
  pyproject.toml
  src/minion_agent/
    runtime/         # plugin runtime: context, fiber, service, registry, events, effects
    llm/             # message vocabulary + adapter seam
      adapters/      #   openai_completions, codex_responses, mock
    session/         # event log, derive_messages(), persistence
    agent/           # Agent interface, registry, agent/* events, Inbox
    agent_loop/      # the concrete driver (package-internal)
    tools/           # registry + guarded execution pipeline
    system_prompt/   # section and schema assembly
    fs/              # filesystem capability seam + local provider
    shell/           # shell capability seam + local provider
    builtin_tools/   # bash, read, write, edit, glob, grep
    skills/
    compaction/
    invariants/      # central registry service only; checks are package-owned
    testkit/
  conformance/       # language-neutral executable compatibility cases
    runtime/         #   plugin-kernel semantics (lifecycle, effects, events, services)
    agent/           #   agent and session semantics
    schema/          #   JSON Schema for both scenario formats + runner contract
  tests/             # Python unit and property tests
  evals/             # model-backed tier
minion-agent-docs/
  design/            # this document
  spec/              # normative semantic rules
```

One distribution, not one per plugin. DSH's package-per-plugin split buys
independent npm versioning that a single-language project does not need. The
structural property that matters — every capability is a plugin mounted beside
the others, with no privileged core — is preserved by module boundaries plus an
entry-point group (`minion_agent.plugins`) so out-of-tree plugins mount exactly
as in-tree ones do.

`conformance/` sits at the repository root as pure data, so a Rust
implementation can vendor or submodule it without depending on Python.

---

## 3. The plugin runtime (`minion_agent.runtime`)

Cordis-semantic, not a Cordis port: faithful to its semantics, not its
mechanics. Proxies, symbols, and declaration merging have no Python
counterpart worth forcing.

**Naming.** Cordis is credited as the design lineage throughout this document,
but the name stays out of the API and package namespace. The package is
`minion_agent.runtime`; the concepts it implements are described as
Cordis-inspired or Cordis-semantic. This keeps the implementation free to
diverge where Python warrants without the name implying a compatibility
promise we have not made.

```python
class BashConfig(BaseModel):
    timeout_ms: int = 120_000

@plugin(name="tool-bash", inject=["tools", "shell"], config=BashConfig)
async def bash_tool(ctx: Context, config: BashConfig) -> None:
    ctx.effect(lambda: ctx.tools.register(BashTool(ctx, config)))
    ctx.on("tools/pre-execute", guard)
```

### Context

A repository of services. `ctx.tools` resolves through `__getattr__` against
the registry, bound to the accessing context. Python has no declaration
merging, so statically-checked code has a second door: `ctx.require(ToolService)`,
a plain typed lookup. Both are supported; attribute access is the ergonomic
default and `require` is the type-checked one.

`Context.extend()` produces the child context a fiber runs in.

### Fiber

One loaded plugin instance: lifecycle state, validated config, and its
disposable list.

### Service resolution

`ctx.tools` and `ctx.require(ToolService)` are two views over one canonical
mechanism. These rules follow Cordis's `reflect.ts` and are normative.

**Identity is the name, not the type.** A service is keyed by `(name, realm)`.
Cordis allocates one symbol per name on the root context and resolves through
a single slot. `ctx.require(ToolService)` resolves by the name the Protocol
declares; it is a typed view, never a second key space.

**Registration is exclusive.** Two plugins cannot provide the same service in
one realm. The second `provide()` raises, naming the fiber that already holds
it. There is no last-wins, no priority, and no registration-order rule —
because there is never more than one provider to choose between.

**There is no fallback stack.** Disposal removes the slot and notifies
dependents. An earlier provider does not become visible again; it was never
retained.

**Dependents react to the resolved provider.** When a service appears or
disappears, every fiber whose `inject` names it, in a matching realm, is
rechecked and refreshed. This is the mechanism behind reactive dependency
below.

**Visibility is narrower than registration.** A service resolves only while
its providing fiber is `ACTIVE`, and a provider may attach a `check` predicate
narrowing visibility further. A registered-but-inactive provider is invisible
to injection.

**Shadowing is deferred, because shadowing _is_ isolation realms.** In Cordis a
child context shadows a parent service via `ctx.isolate(name)`, which allocates
a fresh symbol for that name in a child realm. Shadowing and realms are one
mechanism, not two. Realms are deferred (§9), so **child contexts cannot shadow
parent services in this phase.** That is a consequence of the deferral, not a
separate limitation.

### Reactive dependency

This is what makes the runtime Cordis-semantic rather than a
dependency-injection container. A fiber loads when every injected service
exists and unloads when
any of them disappears, unwinding its effects in reverse order. Services
appearing and vanishing at runtime is a normal condition, not an error path.

### Effects

`ctx.effect(fn)` runs `fn` immediately, collects the disposer it returns, and
runs collected disposers in reverse order on explicit disposal or fiber
unload, whichever comes first. Double-disposal is a no-op. Creating an effect
on a disposed fiber raises. A `@contextmanager`-style generator is also
accepted as the idiomatic Python spelling.

### Events

Four dispatch modes, matching Cordis:

| Mode | Awaited | Order | Returns |
|---|---|---|---|
| `emit` | no | registration order | no |
| `parallel` | yes | concurrent | no (errors aggregated) |
| `serial` | yes | registration order | yes |
| `waterfall` | yes | registration order | yes |

`waterfall` is around-middleware: a listener receives `next` and either
delegates or short-circuits by returning without calling it. Dispatch mode is
part of an event's public contract and is declared where the event is
declared; a mismatch between declaration and dispatch site is a startup error.

### Config

Plugin config validates through pydantic, the natural counterpart to Cordis's
Standard Schema. JSON Schema export comes free and the conformance layer uses
it.

---

## 4. The LLM seam (`ctx.llm`)

### Vocabulary

Our own types, mirroring pi's semantics:

- Content blocks: `text`, `thinking`, `tool_call`
- `StopReason`: `pending | stop | length | tool_use | error | aborted`
- `Usage`: input, output, cache read, cache write, reasoning; plus computed cost
- Stream chunks: `start`, `{text,thinking,tool_call}_{start,delta,end}`, `done`,
  `error` — each carrying the partial message, so a UI can render any prefix

### The never-raises contract

Copied verbatim from pi and load-bearing: **the stream never raises.**
Request, model, and runtime failures are encoded *in* the stream as a final
message with `stop_reason` of `error` or `aborted` plus an error message.

This removes most error-path branching from the loop and is directly
assertable by conformance.

### API and provider split

Pi separates the wire protocol (API) from the endpoint, auth, and model list
(provider). We adopt that split.

| API | Providers |
|---|---|
| `openai-completions` | OpenRouter, Ollama, LM Studio, generic OpenAI-compatible |
| `codex-responses` | OpenAI Codex |
| `mock` | scripted provider for conformance; replay provider for recorded sessions |

Each provider is a plugin registering onto `ctx.llm` through `ctx.effect`, so
unloading it withdraws its models.

### Authentication

Auth is a seam, not a file path. The contract is: **the Codex provider
authenticates through the Codex OAuth mechanism.** Pi models this the same way
— its `openaiCodexProvider()` declares a pluggable `lazyOAuth({ load: ... })`
loader rather than a hard-coded location.

Reading the Codex CLI's on-disk credentials is the *first loader
implementation*, chosen because it works immediately for users who already run
Codex CLI. A full interactive PKCE login is a second loader behind the same
seam. Neither location nor file format is part of the contract.

---

## 5. The session log (`ctx.sessions`)

Append-only, sequence-numbered, and JSON-validated at append time.

**Model-visible means logged.** Anything reaching a model request must be
reconstructable from the log, and an invariant asserts it (§8).

### Two tiers of event

The **surface** subset — `user/message`, `assistant/message`, `tool/result` —
is what `derive_messages()` projects into model history.

Everything else is **log-only**: `turn/start`, `turn/end`, `step/start`,
`step/end`, `assistant/chunk` (token-level replay fidelity), `tool/call`,
`request/header`.

### Relationship to pi's `convertToLlm`

This replaces pi's `convertToLlm` structurally. Pi filters an in-memory
`AgentMessage[]` through a user-supplied function; we derive from the log's
surface subset. Pi's custom message types become plugin-declared session events
that either join the surface or do not.

Precisely: **filtering and projection behavior is equivalent and more
inspectable; rewrite behavior moves to `agent/pre-step` and is pinned
separately by compatibility conformance.** This is not full structural
equivalence — the extension mechanism intentionally differs for the rewrite
case — and the spec should not claim otherwise.

### Portability of plugin-declared surface events

Plugins may declare session events that join the model-visible surface. Two
tiers of contract apply:

| | Contract |
|---|---|
| **Core surface event semantics** | Language-neutral and normative. A Rust implementation must reproduce them. |
| **Plugin-defined surface projections** | Plugin-scoped. Not automatically cross-language. |

A Rust implementation cannot reproduce an arbitrary Python projection
function, and nothing in this design asks it to. If cross-language third-party
plugins later become a requirement, their projection format needs its own
portable schema; that is out of scope here.

---

## 6. The agent loop (`ctx.agent_loop`)

A **step** is one model request plus the tools it calls. A **turn** is zero or
more steps.

```
turn/start
  claim next-step inbox + queued prompts (per the two claim policies below)
  agent/pre-step  ->  Reject | Enter(messages)        [waterfall, closed union]
     rejection or empty first claim -> close a durable turn with no step
     step/start
       append entered messages · derive history · assemble prompt + tool schemas
       request/header -> llm/stream -> assistant/chunk* -> assistant/message
       tool/call* -> tools/pre-execute -> execute -> tools/post-execute -> tool/result*
     step/end
     tools owe another request, or next-step input arrived -> next step
  agent/turn-stopping                                  [serial]
turn/end
```

The driver is imperative and package-internal, following DSH's `ReactLoopAgent`
(a stateful class with an explicit `idle | maintenance | running` phase union).
Neither pi nor DSH factors the live loop as a pure reducer, and this design does
not invent one.

`agent/status` transitions `idle -> running -> idle` and is the settle signal.
Callers and tests await it; they never sleep.

### Inbox

DSH's `send(message, target, wakeup)` generalizes pi's two queues:

| Alias | Target | Wakes driver |
|---|---|---|
| `followup` | next-turn FIFO | yes |
| `steer` | next-step inbox | yes |
| `inject` | next-step inbox | no |

Pi's `steeringMode` and `followUpMode` survive as **two independent claim
policies**, each `all` or `one-at-a-time`:

- The **next-step** policy governs how many inbox messages a step boundary
  claims (pi's `steeringMode`).
- The **next-turn** policy governs how many queued prompts a turn boundary
  claims (pi's `followUpMode`).

Both default to `one-at-a-time`, matching pi.

### Preserving pi's semantics

| pi `agent-core` | Minion Agent |
|---|---|
| `prompt()` / `continue()` | `followup()` then await idle; continue is a claim with no new message |
| `steer()` / `followUp()` | `steer()` / `followup()`, plus `inject()` for silent context |
| `transformContext` | `agent/pre-step` waterfall |
| `convertToLlm` | `derive_messages()` over the log surface |
| `beforeToolCall` | `tools/pre-execute` -> `Block(reason, terminate) \| Proceed(args)` |
| `afterToolCall` | `tools/post-execute` -> field-by-field replace, **no deep merge** |
| `shouldStopAfterTurn` | `agent/turn-stopping`, serial |
| `prepareNextTurn` | `agent/pre-step` returning replacement model / thinking / context |
| `terminate` batch rule | stop only when **every** finalized result sets it |
| `AgentEvent` stream | a projection plugin rebuilding pi's ten-event union from log plus live events |

Two decisions in that table deserve emphasis.

**Single-valued hooks become closed decision unions.** Pi's callbacks are
single-valued with precise semantics. Multi-listener dispatch would diffuse
them. DSH's answer — which we adopt — is to type the decision payload as a
closed union (`Reject | Enter(messages)`) and document short-circuiting as the
design for policy events. Pi's `terminate` rule is unaffected: it folds over
tool *results*, not over listeners.

### Decision algebra

Dispatch mode fixes execution order but not semantic combination. Every
decision event declares both. These rules are normative and conformance-tested.

**`agent/pre-step`** — waterfall. Returns `Reject | Enter(messages)`. A
listener either delegates via `next` or short-circuits by returning a
decision. The first returned decision wins.

**`agent/pre-step` carries a reason.** Pi's `transformContext` and
`prepareNextTurn` fire at different lifecycle points — `transformContext`
before every request including the first, `prepareNextTurn` only between
turns. Collapsing both into one undifferentiated event would make
`prepareNextTurn` impossible to replicate, so the event carries a
`PreStepReason`:

```
PreStepReason = initial | tool_results | steering | next_turn | continuation
```

The enumeration is derived from pi's actual call sites and pinned by
compatibility conformance; it is not open for plugins to extend.

**`agent/turn-stopping`** — serial. Listeners return
`NoOpinion | Continue | Stop`. **The first non-`NoOpinion` decision wins and
short-circuits**; later listeners do not run. If every listener returns
`NoOpinion`, the result is `Continue`, matching pi's boolean default of
`false`.

This is consistent with the short-circuit pattern used by the other decision
events. The trade-off is recorded deliberately: the outcome depends on
registration order. An order-independent "any `Stop` wins" rule was considered
and rejected because it collapses `Continue` into `NoOpinion` and diverges
from the pattern used everywhere else.

**`tools/pre-execute`** — waterfall. Returns
`Block(reason, terminate) | Proceed(args)`. First decision wins.

**`tools/post-execute`** — waterfall, composing rather than deciding. **Each
listener receives the finalized output of the previous listener. Fields the
listener explicitly returns replace those fields; omitted fields remain
unchanged. No deep merge occurs at any level.** This preserves pi's
`afterToolCall` merge semantics across a listener chain.

**Pi's event stream becomes a derived projection.** The log is the source of
truth; a projection plugin rebuilds pi's `AgentEvent` union from it.
Conformance asserts that projection, so pi's observable semantics stay pinned
while internals follow DSH.

### Tool batch execution

Pi and DSH genuinely differ here, and we take pi's rule:

- **Batch contagion (pi).** If any call in a batch targets a tool declared
  `sequential`, the entire batch executes sequentially.
- DSH instead groups calls, letting parallel-safe calls overlap around
  exclusive barriers. This is arguably the better design, but it produces
  different traces, and preserving pi's semantics is the stated goal.

Emission order is pi's: `tool_execution_end` in **completion** order,
tool-result messages in **assistant source** order.

---

## 7. Harness

### Capability seams

Two seams: `ctx.fs` and `ctx.shell`.

Pi defines `FileSystem` and `Shell` as separate interfaces but also defines
`ExecutionEnv extends FileSystem, Shell`, and every consumer depends on the
intersection (`ExecutionToolContext.env: ExecutionEnv`; no consumer takes
`FileSystem` or `Shell` alone). So pi split the interfaces but not the
dependency: a local filesystem cannot be paired with a remote shell.

We split the dependency. Consumers take the capability they use.

**The fs/shell bridge.** DSH's `ctx.fs` is not pi's shape, and its difference
is the mechanism that makes separate seams coherent:

- `resolve(path) -> FsTarget` returns an opaque `target_key`. The same file
  reached by different paths yields the same key.
- `process_path(target)` returns the canonical path *a subprocess in this
  provider's execution world can open*.

That indirection is how filesystem and shell stay independently swappable while
still describing one execution world. It also gives read-before-edit checks and
version-guarded writes a natural key, subsuming pi's `file-mutation-queue`
keying.

**Execution-world compatibility.** Independent swappability does not make
arbitrary combinations coherent. A local Windows `ctx.fs` paired with a remote
Linux `ctx.shell` composes without complaint and then fails at the first
`process_path` — the path one seam produces is meaningless to the other.

The governing invariant:

> A shell may consume an FS-backed target only when the two providers share an
> execution world.

We enforce it. Each `ctx.fs` and `ctx.shell` provider declares an
**execution-world identity**, and mounting an incompatible pair fails at
activation with a diagnostic naming both providers.

This deliberately exceeds the references. DSH states the same constraint —
"a deployment must mount filesystem and subprocess providers for the same
execution world; split-world composition is invalid" — but enforces nothing,
so an incompatible pairing is only discovered at first use. Failing at mount is
cheap and turns a confusing runtime error into a boot-time one.

**Error style.** Pi's contract holds and is current: filesystem and shell
operations **never raise**; every failure, including unexpected backend
failures, returns a typed error value. In Python that means `Result[T, E]` at
these two seams and ordinary exceptions everywhere above them.

Separate error domains per seam, as pi has (`FileError` and `ExecutionError`
are distinct types with distinct code enums):

```
Result[T, FsError]        # ctx.fs
Result[T, ShellError]     # ctx.shell
```

The boundary between the two mechanisms is normative:

| | |
|---|---|
| **Values** — expected operational and environmental failures | not found · permission denied · invalid path · stale version · timeout · abort · non-zero process exit · I/O failure · remote unavailable |
| **Exceptions** — framework and provider invariant violations | invalid internal state · impossible state transition · broken provider implementation · assertion failure · programming error |

Generic backend errors — a bare `OSError`, for instance — are mapped into the
capability error vocabulary rather than escaping as exceptions. An unmapped
backend exception escaping a seam is itself a provider bug.

This is deliberately un-Pythonic and deliberately confined. It keeps "tool
failed" (becomes an error tool result the model sees) structurally distinct
from "harness bug" (crashes loudly), and it maps directly onto Rust.

`FileSystem` covers path resolution without symlink following, `canonical_path`
for explicit resolution, text / binary / line-limited reads, write, append,
atomic rename, `file_info` and `list_dir` (never following symlinks), temporary
directories and files, and `cleanup`. `Shell.exec` takes cwd, env with
`inherit_env`, timeout, abort signal, and stdout/stderr streaming callbacks.

### Tools (`ctx.tools`)

Registration is an effect, so unloading a plugin withdraws its tools mid-session
and the next request's schemas omit them. Parameters are pydantic models
exported as JSON Schema, keeping the model-facing contract language-neutral.

The pipeline is `tools/pre-execute` -> execute -> `tools/post-execute`, both
waterfalls with closed decision unions. Tools stream partial results (pi's
`on_update`), and a result may carry `added_tool_names`: tools introduced by
that result and available from that transcript point onward.

Built-in tools, each its own plugin: **bash**, **read** (line windows,
truncation, image support), **write**, **edit**, **glob**, **grep**.

Two pieces of pi's harness should be ported rather than reinvented: its
edit match-and-replace logic (~500 lines, with its specific failure modes) and
the file-mutation queue that serializes concurrent writes to one path.

Approval and sandboxing policy are **not** built in. They are plugins on
`tools/pre-execute`, which is where pi places them too.

### System prompt and skills

**Single ownership of tool schemas.** `ctx.tools` is the authoritative registry
of executable tools *and* their schemas. Request assembly obtains the
currently-visible tool schemas from `ctx.tools`. `ctx.system_prompt` owns
textual prompt sections only and never registers a tool schema. There is one
source of truth; DSH draws the same line ("register on `ctx.tools`; its schema
joins prompt assembly").

Plugins register prompt sections as effects; assembly happens per step.

Skills load from `SKILL.md` files with YAML frontmatter (`name`, `description`,
`disable-model-invocation`), traversing recursively while honoring
`.gitignore`, `.ignore`, and `.fdignore`, emitting diagnostics for malformed
files rather than failing the load. They render as the agentskills.io XML block,
matching pi's format so skills are portable between the two.

### Compaction

Pi's settings and trigger unchanged: `{enabled, reserve_tokens: 16384,
keep_recent_tokens: 20000}`, compacting when
`context_tokens > context_window - reserve_tokens`. Cut-point search walks
backward to a valid boundary with pi's split-turn handling, and `retained_tail`
copies recent messages forward.

The log model simplifies this. Compaction appends an event; it never deletes.
History stays intact and replay stays exact, making pi's own rule —
"compaction changes provider context, not storage" — structurally enforced
rather than conventional.

**Replacement semantics are explicit**, because repeated and nested compaction
otherwise has no deterministic projection. A compaction event identifies:

- the **superseded surface range** it replaces,
- the **replacement content** (the summary), and
- the **retained-tail provenance** — which surface entries were copied forward.

`derive_messages()` applies replacements deterministically, including for
repeated and nested compactions.

The critical invariant: **the projection must never emit both an original
entry and a copy of it carried forward in a retained tail.** Because
`retained_tail` copies messages into the compaction event, a naive projection
double-counts them. Provenance exists precisely so it cannot.

This gets a dedicated conformance family covering single, repeated, and nested
compaction, and retained-tail overlap.

---

## 8. Validation

### Three tiers

**Tier 1 — conformance scenarios** (`conformance/`, language-neutral).
Declarative YAML in two families, because the plugin kernel's semantics matter
to a Rust implementation exactly as much as the agent loop's:

```
conformance/
  runtime/    reactive-dependency · effect-reversal · waterfall-short-circuit
              service-exclusivity · service-visibility · double-dispose
  agent/      turn-lifecycle · steering · tools · cancellation · compaction
```

`agent/` scenarios assert the log projection and the derived pi event stream.
`runtime/` scenarios assert a generic lifecycle and effect trace instead —
mount and unmount operations in, ordered lifecycle transitions and effect
disposals out.

The `runtime/` family needs something the `agent/` family gets for free. In
agent scenarios the "program" is already data: a provider script and tool
stubs. In kernel scenarios the plugin *behavior* is the thing under test, so
the format needs a small declarative vocabulary — plugins described by their
`inject` set, the effects they create (with labels), the services they provide,
and listeners with declared actions such as `delegate` or `short-circuit`.
**Designing that vocabulary is a prerequisite for Phase 1**, not a side effect
of it (§9).

**Tier 2 — Python tests** (`tests/`). Everything genuinely language-specific:
`Context.__getattr__`, `ctx.require(...)`, pydantic integration,
`@contextmanager` effect syntax, asyncio cancellation details, and adapter wire
formats. Following DSH's approach: compose a real `Context`, `ctx.plugin(...)`
each service, register a mock adapter, settle on `agent/status`, and never
sleep. Plus `hypothesis` property tests mirroring DSH's `fast-check` suite —
every sent message appears exactly once, turn numbers strictly increase, status
transitions are well-formed.

**The dividing rule:** any semantic behavior intended to be shared by Python
and Rust belongs in language-neutral conformance. Tier 2 covers what is true of
*this* implementation rather than of the design.

**Tier 3 — model-backed evals** (`evals/`). Pi's `packages/evals` design: real
provider runs in temporary workspaces, judges, and comparative harness tables
with baseline/candidate pass-rate lift and `judge_threshold=None` so a low
score is an observation rather than a build failure. This tier answers "is the
agent good," not "is it correct."

Tiers 1 and 2 are contract tests, not evals. Only tier 3 is non-deterministic,
judged, and costly.

### Invariants

`ctx.invariants` exists from day one as a **central registry service only**.
Checks are **package-owned**: each subsystem ships its own companion
registering via `ctx.invariants.register(PACKAGE_NAME, install)`.

- `session` — log and surface invariants
- `agent_loop` — request/log reconstruction
- `tools` — tool execution invariants

This mirrors DSH, which has 30+ package-owned `invariant.ts` companions against
one `runtime-diagnostics/invariants` registry. No single module owns all
correctness rules.

The agent-loop companion re-derives each request from the log at dispatch time
and fails on divergence. Invariants run in tests always and are switchable in
production.

### The development cycle

```
identify behavior
   |
classify:
  runtime contract -> conformance scenario / Python test
  model behavior   -> model-backed eval
   |
implement
   |
validate
   |
refine
```

**The conformance rule:** every externally meaningful runtime behavior change
must be represented in `conformance/`. Sometimes that means extending or
parameterizing an existing scenario rather than adding a file.

**Normativity.** Finite example scenarios cannot exhaustively define the
behavior of a reactive plugin runtime, so the two artifacts divide the work:

| Artifact | Role |
|---|---|
| `minion-agent-docs/spec/` | Normative semantic **rules** — the general statement, including behavior that cannot be exhaustively enumerated |
| `conformance/` | Normative executable **compatibility cases** |

For behavior a conformance scenario covers, the executable result is the
compatibility oracle and wins over prose. The prose spec defines the general
rule everywhere else. Neither is a subordinate commentary on the other, and
behavior is not "unspecified" merely because no YAML file encodes it yet.

**Coverage:** core runtime packages target 100% per-file coverage; exceptions
require explicit written justification. This is DSH's actual practice — their
config carries a long exclude list with debt markers, platform-conditional
exclusions, and a documented exemption contract — and it avoids forcing
artificial tests around provider-adapter defensive branches to protect a number.

---

## 9. Build order

Each phase ends with green conformance scenarios for the behavior it adds.

**Phase 0 — conformance scenario formats.** Design and schema-fix both scenario
vocabularies before Phase 1: the `agent/` format (provider script, tool stubs,
config, expected trace) and the `runtime/` format (declarative plugin
descriptions and expected lifecycle/effect traces). Phase 1 has conformance
coverage from its first commit rather than acquiring it retroactively, and the
kernel's semantics get pinned while they are still cheap to change.

1. **Plugin runtime.** Context, fiber, service resolution, registry, events,
   effects, reactive load and unload. Covered by `conformance/runtime/` plus
   Tier 2 for the Python-specific surface.
2. **LLM vocabulary, mock adapter, session log.** `derive_messages()`, surface
   versus log-only events, the never-raises stream contract. First conformance
   scenarios land here.
3. **Agent loop.** Turn and step lifecycle, inbox and claim policies, `agent/*`
   events, the pi event-stream projection, cancellation. Includes the
   tool-call/result vocabulary and a trivial mock tool service, so that by the
   end of this phase the following works end to end:

   ```
   mock LLM -> tool_call -> agent loop -> mock tool result -> second LLM request
   ```

   Turn continuation is the loop's defining behavior and cannot be exercised
   without a tool result closing a step.
4. **Tools.** The real registry, `tools/*` waterfalls, batching, execution modes
   and batch contagion, streaming results, `terminate` folding.
5. **Real providers.** `openai-completions` (OpenRouter, Ollama, LM Studio),
   then `codex-responses`.
6. **Execution seams and built-in tools.** `ctx.fs` and `ctx.shell`, then bash,
   read, write, edit, glob, grep.
7. **Prompt, skills, compaction.**
8. **Model-backed evals.**

Phases 1–4 produce a correct agent driven entirely by a mock. Phase 5 is the
first contact with a real model. This ordering keeps semantics work from being
blocked on, or contaminated by, provider quirks.

### Deferred, with triggers

| Deferred | Introduce when |
|---|---|
| `ctx.subprocess` | First consumer needing argv spawning that is not shell-interpreted: a PTY terminal tool, an LSP integration, or a subagent over a spawned process. DSH's split is real — `subprocess` never shell-interprets argv and owns PTY allocation and tree-scoped termination — but with only the bash tool in scope it would be a seam with one consumer that immediately delegates. |
| Isolation realms | Subagents, or per-session capability presets. The service registry is designed so realms slot in without rework. |
| Declarative loader, HMR | Configuration-driven composition becomes a user-facing requirement. |
| Durable operation state machine | Crash recovery becomes a requirement. Added behind the existing session interface. |

---

## 10. Open questions

None blocking implementation planning. Items resolved during design and
recorded here for traceability:

- **Scope** — stratum A plus harness essentials; durable state machine deferred.
- **Eval expression** — language-neutral scenario files with thin per-language
  runners, rather than idiomatic Python tests extracted later.
- **Cordis fidelity** — core semantics including reactive dependency; loader,
  HMR, and isolation realms excluded.
- **Provider set** — OpenAI-compatible first (OpenRouter, Ollama, LM Studio)
  plus Codex, rather than Anthropic.
- **Architecture** — imperative driver plugin with log-as-truth and invariants,
  matching what both references actually run, rather than a pure step machine.
- **Error style** — `Result` at the fs and shell seams only, split into
  `FsError` and `ShellError`, with an explicit operational-value versus
  programming-exception boundary (§7).

Resolved in design review (2026-08-18):

- **Kernel conformance** — `conformance/` splits into `runtime/` and `agent/`
  families; a declarative plugin vocabulary is Phase 0 work (§8, §9).
- **Naming** — the plugin runtime package is `minion_agent.runtime`; Cordis is
  credited as design lineage in prose ("Cordis-inspired", "Cordis-semantic")
  but kept out of API and package names (§3).
- **Service resolution** — name-keyed identity, exclusive registration, no
  fallback stack, `ACTIVE`-gated visibility; shadowing deferred with realms (§3).
- **Execution world** — declared world identity with activation-time
  validation, exceeding both references (§7).
- **Decision algebra** — `pre-step` carries a `PreStepReason`;
  `turn-stopping` is first-non-`NoOpinion`-wins with short-circuit;
  `post-execute` composes by field replacement without deep merge (§6).
- **Normativity** — prose spec defines general rules, conformance is the oracle
  for behavior it covers (§8).
