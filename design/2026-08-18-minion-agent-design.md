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
YAML loader, hot module replacement, isolation realms (service shadowing — not
to be confused with scoped registration in §3, which is in scope), and a
`ctx.jobs` scheduling service.

This scope was validated against a real long-lived multi-agent application
before implementation; see `2026-08-18-foundation-validation.md`. That exercise
added scoped registration, input provenance, telemetry, content-addressed
request state, and `ctx.subprocess` to the design, and confirmed that the
durable operation state machine and isolation realms are correctly deferred.

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
    subprocess/      # argv spawning + stdio lifecycle seam + local provider
    builtin_tools/   # bash, read, write, edit, glob, grep
    skills/
    compaction/
    telemetry/       # span vocabulary + sanitize boundary; sinks are plugins
    invariants/      # central registry service only; checks are package-owned
    testkit/
  conformance/       # language-neutral executable compatibility cases
    runtime/         #   plugin-kernel semantics (lifecycle, effects, events, services)
    agent/           #   agent-loop semantics
    session/         #   log operations, derivation, request reconstruction
    schema/          #   JSON Schema per scenario format + runner contract
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

**Service shadowing is deferred, because shadowing _is_ isolation realms.** In
Cordis a child context shadows a parent *service* via `ctx.isolate(name)`, which
allocates a fresh symbol for that name in a child realm. Service shadowing and
realms are one mechanism, not two. Realms are deferred (§9), so **child contexts
cannot shadow parent services in this phase.** That is a consequence of the
deferral, not a separate limitation.

Scoped registration (below) is a **different mechanism** and is not deferred.
Realms replace a whole service implementation; scopes vary the *registrations
within* a shared service. Applications overwhelmingly need the latter.

### Scoped registration

A runtime that hosts more than one agent needs registrations — tools, prompt
sections, event listeners — that are visible to some agents and not others.
Service resolution above cannot express this: there is one `tools` service and
one `ctx.llm` for the process, which is correct. Variation belongs *inside* a
service's registration table, not in which service you resolve.

**A scope is a tagged context whose backing fiber owns every registration made
through it.** `ctx.scope(key)` mints one. Its governing contract:

> The registration context determines both visibility and ownership.

A registration can therefore never be visible in one scope but disposed with
another — the failure mode that makes ad-hoc capability filtering unsafe.

**Scopes nest arbitrarily**, and the two directions differ:

| Direction | Rule |
|---|---|
| **Registration visibility inherits _down_** | A child scope sees registrations owned by itself and its ancestors. An ancestor never sees a descendant's. |
| **Event admission extends _up_** | A listener tagged with an ancestor receives a descendant's events. Never the reverse. |
| **Untagged** | An untagged listener is admitted for every dispatch; an untagged registration is visible everywhere. |

Disposing a scope removes exactly its own and its descendants' registrations,
leaving ancestors and siblings intact.

**The runtime decides eligibility; each registry decides composition.** Scoping
answers only *which registrations are visible here*. What to do when several are
visible is the owning service's business, and the right answer differs by
registry:

| Registry | Composition |
|---|---|
| Tools | Keyed by name; a nearer same-name registration shadows a farther one |
| Prompt sections | Additive |
| Event listeners | All admitted listeners participate |
| Telemetry sinks | Additive |

Putting a shadowing rule in the generic layer would impose keyed-collision
semantics on registries that are additive by nature.

**Nesting depth is the application's choice.** The runtime guarantees arbitrary
nesting and key-agnostic tags; it does not define a hierarchy. A chat
application may use definition → instance → turn; an eval harness may scope by
variant; a simple tool may use none. Hardcoding a level structure here would
bind the runtime to one application's shape.

The runtime contract stops here: nested visibility, ownership, descendant
disposal, and deterministic effect reversal. Subsystems that need disposal to
wait on their own in-flight work state that in their own layer (§6), because a
generic "active-use lease" with one consumer would be an imagined extension
rather than an extension point.

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

Dispatch mode is part of an event's public contract and is declared where the
event is declared; a mismatch between declaration and dispatch site is a startup
error.

**Waterfall, defined once and normatively.** A listener is invoked as
`listener(*args, next)`:

- **Not calling `next`** — downstream listeners do not run, and this listener's
  return value is the chain's result.
- **Calling `next()`** — the downstream chain runs with the current arguments.
  **Calling `next(*replacement)`** runs it with replacements instead. Either way
  the downstream result is returned to this listener, which may return it
  unchanged, replace it, or transform it.
- **`next` may be called at most once.** A second call raises. (An earlier draft
  memoized `next` so repeat calls were harmless; that is incoherent once `next`
  accepts replacement arguments, and a single-use contract is simpler to reason
  about than a cached one.)
- **An empty chain** returns `None`.

Every waterfall event in this design is specified in exactly these terms (§6).
Two distinct usage patterns fall out of the one mechanism, and neither is a
separate dispatch mode:

| Pattern | Shape |
|---|---|
| **Decision** | A listener with no opinion delegates; a listener that owns the decision returns without delegating. "First decision wins" is the consequence, not a second mechanism. |
| **Transformation** | A listener transforms the payload and delegates with the replacement, so registration order equals application order. |

**Scope filtering is additive.** A dispatch may carry a scope key. Admission
follows §3's admit-up rule: an untagged listener is always admitted; a tagged
listener is admitted only when its key is the dispatch's key or an ancestor of
it. A dispatch with no key admits untagged listeners only. Because untagged
listeners are always admitted, adding scope filtering changes no unscoped
behavior.

### Config

Plugin config validates through pydantic, the natural counterpart to Cordis's
Standard Schema. JSON Schema export comes free and the conformance layer uses
it.

---

## 4. The LLM seam (`ctx.llm`)

### Vocabulary

Our own types, mirroring pi's semantics:

- Content blocks: `text`, `thinking`, `image`, `tool_call`
- `StopReason`: `pending | stop | length | tool_use | error | aborted`
- `Usage`: input, output, cache read, cache write, reasoning; plus computed cost
- Stream chunks: `start`, `{text,thinking,tool_call}_{start,delta,end}`, `done`,
  `error` — each carrying the partial message, so a UI can render any prefix

**Image content** is part of the provider-neutral vocabulary, not an adapter
detail. The `read` tool returns images (§7) and applications accept them as
input, so without a normative block there is no defined way to send image
content to a multimodal model. The V1 contract carries only what an adapter
needs to translate it:

```
Image { mime_type, data | reference }
```

Whether bytes travel inline or by reference is an implementation choice; the
`mime_type` and the model-visible presence of an image are not. Images do not
stream — they have no delta chunks — which is why the stream-chunk list above
covers only `text`, `thinking`, and `tool_call`.

### The never-raises contract

Copied from pi and load-bearing: **the stream never raises.** The boundary is
the moment the stream object is returned, and both sides of it are normative:

| Phase | Behavior |
|---|---|
| **Before a stream is returned** | Ordinary exceptions. Programming errors, invalid arguments, service-resolution failures, configuration errors, and unsupported model or provider selections raise normally — these are caller bugs, discoverable immediately. |
| **After a stream is returned** | Nothing escapes iteration. Provider failures, network failures, model failures, cancellation, and runtime streaming failures terminate the stream with a final message carrying `stop_reason` of `error` or `aborted` plus an error message. |

Stating the boundary matters: "never raises" read absolutely would force a
mistyped model name to be reported as a streamed error message, burying a caller
bug in the transcript. Read as above, it removes error-path branching from the
loop for exactly the failures the loop must handle in-band, and is directly
assertable by conformance on both sides.

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

### Session operations

Three operations mutate a session. Under an append-only log none of them can be
specified as a method name alone — each needs a log event and a stated effect on
derivation, or implementations will diverge on behavior the conformance suite
cannot see.

| Operation | Log event | Effect on `derive_messages()` |
|---|---|---|
| `fork(source, at)` | `session/forked` on the new session, recording `source` and the boundary sequence | The fork **references** its ancestor's surface up to the boundary; nothing is copied. Derivation walks the ancestry chain, then the fork's own entries. |
| `reset()` | `session/reset` appended to the same session | Session identity is **preserved**. Derivation excludes all surface entries at or before the reset event. History remains readable for search and audit. |
| `compact_now()` | The ordinary compaction event (§7) | Identical to automatic compaction, bypassing only the trigger check. |

Reset preserves identity rather than minting a new session because a session id
is a durable external handle: an application binds conversations to it, and
silently changing it under a clear-history operation would break those bindings.
"Start over" is a derivation change, not a new conversation.

Fork references rather than copies for the same reason the log never deletes:
copying would duplicate model-visible content and create two places for one
truth. Compaction inside a fork affects only that branch.

### Content-addressed request state

The assembled system prompt is model-visible and must be reconstructable from
the log. Logging it whole on every step does not scale: a resident agent's
prompt is large, mostly stable, and partly dynamic, so a small change forces a
large snapshot. Change detection on the whole header does not help, because in
practice *something* changes nearly every step.

`request/header` therefore records a **composition of content-addressed
components** rather than a snapshot:

```
request/header
    system_base:  sha256:…
    skills:       sha256:…
    tools:        sha256:…
    memory:       sha256:…
    task:         sha256:…
```

Each distinct component is stored once, keyed by its hash. A stable block is
stored once for the life of the session however often its neighbours change.

The rule, stated normatively:

> Reconstruct request state from content-addressed components, never from
> repeated monolithic snapshots.

Two consequences follow and are binding:

- **Artifacts holding model-visible content are never deleted**, inheriting the
  discipline that already governs entries. No artifact may be reclaimed while
  any header references it.
- **Conformance asserts the reconstruction, never the storage.** Scenarios verify
  that the reconstructed model input matches what was dispatched. Hashing scheme
  and artifact layout are implementation choices, which keeps a second-language
  implementation free to store differently while proving the same property.

The §8 invariant is unchanged in force: it resolves the references and compares
the reconstruction against the dispatched request.

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

### Definitions and instances

Two things are routinely called "the agent" and must be separated before
anything else in this section is unambiguous:

| Term | Meaning |
|---|---|
| **AgentDefinition** | Reusable configuration: persona, capability composition, policy. Holds no conversation state. |
| **AgentInstance** | One live execution identity: one inbox, one active-turn state, one session log, one lifecycle owner. |

One definition has many instances. A named assistant answering in three
different conversations is one definition and three instances.

`ctx.agents` is the registry. It creates and resumes instances, and each
creation returns a **handle** that owns that instance's teardown. Every
`agent/*` event identifies the instance it concerns. Instances are concurrent
and independent: §8's progress guarantee applies between them.

Scopes (§3) follow the same structure. A definition's registrations are mounted
in a parent scope; each instance mints a child; each turn may mint a child of
that for registrations valid only while the turn runs. The runtime imposes none
of this — it is the arrangement an application with definitions and instances
naturally builds from arbitrary nesting.

**A turn-owned scope is not disposed until every tool execution started under
that turn has settled.** A running tool therefore never loses a registration
mid-execution. This rule belongs here rather than in §3: the runtime's scope
contract knows nothing about tools, and inverting that dependency to serve one
consumer would put an agent concept inside the generic layer.

### The loop

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

### Input provenance and delivery

A turn is not always requested by a user, and its output does not always have a
destination. A scheduler may start a turn nobody asked for; a turn may complete
having decided to say nothing; a result may belong to a conversation other than
the one that triggered the work.

The runtime therefore carries provenance on **inputs**, and records which inputs
each turn consumed:

```
InputEnvelope { id, message, origin }
Turn          { causes: [envelope_id, …] }
turn/end      { causes: [{ id, origin }, …] }
```

`origin` is **opaque to the runtime** — it is never inspected, matched, or
interpreted — and must be **JSON-safe**, because it travels in the log (§5) and
must survive a reimplementation in another language.

Provenance attaches to inputs rather than to turns because **a turn can have
more than one cause**. Under the `all` claim policy below, one turn may consume
several queued inputs with different origins; a single `turn.origin` would not
be well defined.

Two rules complete the model:

- **A turn may complete without producing delivered output.** Delivery is not a
  loop guarantee.
- **Delivery is an application concern.** The runtime reports causes; deciding
  where a result goes, or that it goes nowhere, belongs above it.

Stated as one sentence: *inputs carry provenance; turns carry their causal
inputs; delivery is an application concern.* This is deliberately smaller than a
channel or reply-to concept — the runtime never learns what a room, user, or
channel is, and the same seam serves webhooks, schedulers, API calls, and eval
harnesses correlating turns to cases.

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

**`agent/pre-step`** — waterfall, **decision** pattern. Returns
`Reject | Enter(messages)`. A listener with no opinion calls `next()`; a
listener that owns the decision returns one without delegating, which ends the
chain. If every listener delegates, the loop's default decision applies. "First
decision wins" is the consequence of §3's short-circuit rule, not a separate
mechanism.

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

**`tools/pre-execute`** — waterfall, **decision** pattern, identical in shape to
`agent/pre-step`. Returns `Block(reason, terminate) | Proceed(args)`. Delegate
to abstain; return a decision to own it.

**`tools/post-execute`** — waterfall, **transformation** pattern. A listener
transforms the result and delegates with the replacement:

```python
async def audit(result, next_):
    return await next_(replace(result, details={**result.details, "audited": True}))
```

Because each listener transforms *before* delegating, **registration order
equals application order**, and the chain's result is the fully transformed
value. A listener may also inspect what `next_` returns, but transformation on
the delegating edge is the documented pattern — transforming on the return edge
instead would reverse application order relative to registration, which is a
trap rather than a feature.

Merge semantics per listener are unchanged from pi's `afterToolCall`: **fields
the listener supplies replace those fields; omitted fields remain unchanged; no
deep merge occurs at any level.**

### Agent progress isolation

> Awaiting anything within one agent instance must not occupy a runtime-global
> critical section or block another instance's progress.

This is normative and covers every await inside a turn, not only policy hooks:
human approval, an interactive question to a user, a remote tool call, a slow
MCP server, a subagent awaited by its parent, or any network-bound tool.

A listener or tool may legitimately await external input for an unbounded time.
An implementation that introduces a shared lock, a global timeout, or serialized
cross-agent dispatch would break this while every single-agent scenario
continued to pass — which is why the guarantee is stated here and pinned by a
conformance scenario (§8) rather than left to be inferred.

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

Three seams: `ctx.fs`, `ctx.shell`, and `ctx.subprocess`.

`ctx.subprocess` spawns argv directly and exposes process and stdio lifecycle;
it **never shell-interprets** its arguments — a consumer wanting a shell passes
one explicitly. `ctx.shell` runs shell commands and, in its local provider,
spawns through `ctx.subprocess`.

The distinction is load-bearing rather than decorative. Tool integrations that
speak a protocol over a child process's pipes — MCP over stdio, language servers
over JSON-RPC, browser automation — need raw streams and process lifetime, not
command execution. Routing them through a shell would mean shell-interpreting
argv for a structured transport, wrong on correctness and safety alike.

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

The governing rule:

> Execution-capability providers declare an opaque **execution-world identity**.
> A component that requires multiple execution capabilities to address the same
> resources validates their execution-world identities during activation.
> Merely mounting capabilities from different worlds is not itself invalid.
> Cross-world resource transfer requires an explicit bridge capability.

**Validation is the consumer's, not the runtime's.** Mixed worlds are a
legitimate deployment: local `ctx.fs` for configuration alongside a remote
`ctx.shell`, or local MCP servers over `ctx.subprocess` beside a sandboxed
shell. Nothing is wrong until something tries to carry a resource across.
Requirements are therefore declared where they exist:

| Consumer | Requires |
|---|---|
| `read`, `glob`, `grep` | `fs` only |
| MCP over stdio | `subprocess` only |
| `bash` | `fs` + `shell`, **same world** |
| edit-via-process | `fs` + `subprocess`, **same world** |

A same-world consumer fails at activation with a diagnostic naming the
providers; an unrelated consumer mounts happily beside it.

This still exceeds the references. DSH states the constraint — "a deployment
must mount filesystem and subprocess providers for the same execution world;
split-world composition is invalid" — but enforces nothing, so an incompatible
pairing surfaces at first use. Checking at activation turns a confusing runtime
error into a boot-time one, while a global rule would have banned compositions
that are perfectly sound.

**Error style.** Pi's contract holds and is current: execution-seam operations
**never raise**; every failure, including unexpected backend failures, returns a
typed error value. In Python that means `Result[T, E]` at these three seams and
ordinary exceptions everywhere above them.

Separate error domains per seam, as pi has (`FileError` and `ExecutionError`
are distinct types with distinct code enums):

```
Result[T, FsError]          # ctx.fs
Result[T, ShellError]       # ctx.shell
Result[T, SubprocessError]  # ctx.subprocess
```

A spawn failure, a vanished child, and a broken pipe are operational conditions
a caller must handle, not programming errors — so `ctx.subprocess` follows the
same discipline as its siblings.

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

### Telemetry (`ctx.telemetry`)

A runtime that issues provider requests and executes tools must be observable,
and must not leak credentials while being observed. Both references treat this
as first-class: pi ships a generated span schema; DSH exposes `telemetry/*` as a
capability seam.

A typed span vocabulary covers the operations the runtime already owns — turn,
step, provider request, tool execution — with declared start and end attributes.
The vocabulary is language-neutral, so a second implementation emits the same
spans.

**Sanitization is a mandatory boundary, not a listener.**

```
core / provider data
   ↓
sanitize + redact          ← single mandatory boundary
   ↓
safe structured telemetry
   ↓
sinks   (OpenTelemetry · file · debug · none)
```

Ordering is the whole point. If redaction were a listener among listeners, a
sink registered earlier would observe raw secrets and the guarantee would depend
silently on registration order. Redaction is known-value: the runtime scrubs
credentials it has been told about, wherever they appear — including inside
prompt content, which may carry secrets the runtime never issued. An equivalent
formulation, typed sensitive fields that cannot serialize without a policy, is
acceptable; what is not acceptable is redaction downstream of an extension point.

**Telemetry is observational and never normative:**

| Layer | Role |
|---|---|
| Session log | Semantic truth |
| Runtime events | Extension and control surface |
| Telemetry | Observational projection |

Correctness is defined by session and runtime semantics and pinned by
conformance scenarios. No invariant, no conformance case, and no runtime
behavior may depend on telemetry contents. Sinks are plugins; a deployment may
mount none.

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
Declarative YAML in three families, because the plugin kernel's and the session
layer's semantics matter to a second-language implementation exactly as much as
the agent loop's:

```
conformance/
  runtime/    reactive-dependency · effect-reversal
              service-exclusivity · service-visibility · double-dispose
              scoped-registration-visibility · scoped-registration-ownership
              scoped-event-admission · nested-scope-inheritance
              nested-scope-disposal
              waterfall-short-circuit · waterfall-delegation
              waterfall-result-propagation · waterfall-result-replacement
              waterfall-replacement-arguments · waterfall-next-called-twice
  agent/      turn-lifecycle · steering · tools · cancellation
              concurrent-agents-isolated-logs · blocked-agent-does-not-stall-peers
              origin-survives-one-at-a-time · causes-preserved-under-claim-all
              proactive-turn-carries-provenance · turn-completes-undelivered
              turn-scope-disposed-at-turn-end · turn-scope-awaits-inflight-tool
              request-header-component-reuse
              post-execute-multi-listener-order · post-execute-field-replacement
              post-execute-omitted-fields-preserved · post-execute-no-deep-merge
              stream-error-rides-the-stream · stream-bad-model-raises-eagerly
  session/    fork-ancestry-derivation · reset-excludes-prior-surface
              compact-now-then-derive · compaction-repeated-and-nested
```

The `session/` family is new: §5's operations and content-addressed request
state are behavior a second-language implementation must reproduce exactly, and
several of its cases (derivation after fork, after reset, and after repeated
compaction) are precisely where independent implementations would otherwise
diverge unnoticed.

`agent/` scenarios assert the log projection and the derived pi event stream.
`session/` scenarios assert derivation after log operations, driving the log
directly with no model in play. `runtime/` scenarios assert a generic lifecycle
and effect trace instead — mount and unmount operations in, ordered lifecycle
transitions and effect disposals out.

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

**Phase 0 — conformance scenario formats.** Design and schema-fix all three
scenario vocabularies before Phase 1: the `agent/` format (provider script, tool
stubs, config, expected trace), the `runtime/` format (declarative plugin
descriptions and expected lifecycle/effect traces), and the `session/` format
(log operations in, derived messages out). Phase 1 has conformance
coverage from its first commit rather than acquiring it retroactively, and the
kernel's semantics get pinned while they are still cheap to change.

1. **Plugin runtime.** Context, fiber, service resolution, registry, events,
   effects, reactive load and unload. Covered by `conformance/runtime/` plus
   Tier 2 for the Python-specific surface.
2. **LLM vocabulary, mock adapter, session log, telemetry vocabulary.**
   `derive_messages()`, surface versus log-only events, the never-raises stream
   contract. Also the telemetry span vocabulary, the sanitize contract, and a
   recording no-op `ctx.telemetry` — defined here because every later subsystem
   emits into it, and retrofitting instrumentation across four phases is how
   observability ends up inconsistent. Production sinks come in Phase 7. First
   conformance scenarios land here.
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
6. **Execution seams and built-in tools.** `ctx.fs`, `ctx.shell`, and
   `ctx.subprocess` under one execution-world rule, then bash, read, write,
   edit, glob, grep.
7. **Prompt, skills, compaction, telemetry sinks.** OpenTelemetry, file, and
   debug sinks behind the vocabulary established in Phase 2.
8. **Model-backed evals.**

Phases 1–4 produce a correct agent driven entirely by a mock. Phase 5 is the
first contact with a real model. This ordering keeps semantics work from being
blocked on, or contaminated by, provider quirks.

### Deferred, with triggers

| Deferred | Introduce when |
|---|---|
| Isolation realms (service shadowing) | An application needs a *different implementation* of a service per agent, rather than different registrations within a shared one. Scoped registration (§3) covers the latter and is not deferred; validation against a real multi-agent workload found no demand for the former. |
| `ctx.jobs` | A second independent consumer needs shared scheduling semantics. Fiber effects already give background work owned lifetime (§3), which is what a single consumer actually needs; a scheduling service now would be an imagined extension rather than an extension point. |
| Declarative loader, HMR | Configuration-driven composition becomes a user-facing requirement. |
| Durable operation state machine | **An in-flight turn's side effects must survive process death.** Stated this narrowly on purpose: durable conversation history, durable session identity, and durable application-level queues are all achievable without it, and a validated real workload needed none of the stronger guarantees. Added behind the existing session interface. |

`ctx.subprocess` was previously deferred here and has been promoted into Phase 6
(§9, above): protocol-over-stdio integrations such as MCP need argv spawning
with raw stream access, which `ctx.shell` cannot correctly provide.

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
- **Error style** — `Result` is confined to the filesystem, shell, and
  subprocess capability seams, using `FsError`, `ShellError`, and
  `SubprocessError` respectively, with an explicit operational-value versus
  programming-exception boundary (§7).

Resolved in design review (2026-08-18):

- **Kernel conformance** — `conformance/` splits into `runtime/` and `agent/`
  families; a declarative plugin vocabulary is Phase 0 work (§8, §9).
- **Naming** — the plugin runtime package is `minion_agent.runtime`; Cordis is
  credited as design lineage in prose ("Cordis-inspired", "Cordis-semantic")
  but kept out of API and package names (§3).

Resolved by validation against a real workload (2026-08-18), documented in
`2026-08-18-foundation-validation.md`:

- **Scoped registration** — arbitrarily nested, inherit-down for visibility and
  admit-up for events, with visibility and ownership bound to the same context.
  Distinct from isolation realms, which stay deferred (§3).
- **AgentDefinition vs AgentInstance** — one definition, many concurrent live
  instances; `ctx.agents` registers instances and hands out owning handles (§6).
- **Input provenance** — `InputEnvelope{id, message, origin}` with turns
  recording a causal set. Attached to inputs rather than turns because the `all`
  claim policy lets one turn have several causes (§6).
- **Delivery** — not a loop guarantee; a turn may complete undelivered (§6).
- **Agent progress isolation** — an await inside one instance never blocks
  another (§6).
- **Session operations** — fork, reset, and compact-now specified by log event
  and effect on derivation; reset preserves session identity; fork references
  rather than copies (§5).
- **Content-addressed request state** — `request/header` composes component
  hashes; conformance asserts reconstruction, never storage (§5).
- **Telemetry** — `ctx.telemetry` with a mandatory sanitize boundary ahead of
  sinks; observational, never normative (§7).
- **`ctx.subprocess`** — promoted out of deferral into Phase 6 (§7, §9).

Resolved by design review of the revised spec (2026-08-18):

- **Execution-world validation is consumer-side.** Mixed-world mounts are legal;
  a component requiring several execution capabilities to address the same
  resources validates their worlds at activation. A global rejection rule would
  have banned sound compositions such as local `fs` beside a sandboxed `shell`
  (§7).
- **Runtime scopes stay tool-agnostic.** The "disposal waits on in-flight work"
  rule moved from §3 to §6, where the concept of a tool exists. The runtime
  contract is nested visibility, ownership, descendant disposal, and
  deterministic reversal — nothing more.
- **Waterfall has one normative definition** (§3), with `next` accepting
  optional replacement arguments and callable at most once. `pre-step` and
  `pre-execute` are its *decision* pattern; `post-execute` is its
  *transformation* pattern, transforming on the delegating edge so registration
  order equals application order. An earlier draft memoized `next`; that is
  incoherent once `next` takes arguments.
- **Scope decides eligibility; each registry decides composition** (§3).
  Shadowing is right for keyed registries such as tools and wrong for additive
  ones such as prompt sections, so the generic layer no longer mandates it.
- **`image` is part of the LLM vocabulary** (§4), not an adapter detail.
- **The never-raises boundary is the stream's return** (§4): caller bugs raise
  eagerly, in-band failures ride the stream.
- **Telemetry vocabulary lands in Phase 2**, production sinks in Phase 7 (§9),
  so subsystems instrument as they are built rather than retroactively.
- **Service resolution** — name-keyed identity, exclusive registration, no
  fallback stack, `ACTIVE`-gated visibility; shadowing deferred with realms (§3).
- **Execution world** — declared world identity with activation-time
  validation, exceeding both references (§7).
- **Decision algebra** — `pre-step` carries a `PreStepReason`;
  `turn-stopping` is first-non-`NoOpinion`-wins with short-circuit;
  `post-execute` composes by field replacement without deep merge (§6).
- **Normativity** — prose spec defines general rules, conformance is the oracle
  for behavior it covers (§8).
