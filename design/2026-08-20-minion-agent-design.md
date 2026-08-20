# Minion Agent — Design

**Date:** 2026-08-20  
**Status:** Revised frozen design candidate. Supersedes the 2026-08-18 design after a Pi-fidelity audit against current Pi source. Implementation may proceed only against the semantics in this revision and its conformance/spec updates.

Minion Agent reproduces Pi's observable agent and provider semantics as closely as practical while rebuilding ownership, lifecycle, registration, and composition around the Minion plugin/runtime architecture.

Python is the first implementation. The behavioral specification and conformance suite are language-neutral so a Rust implementation can be validated against the same semantic contract.

## Mandatory project goal — Pi semantic fidelity

> **MANDATORY / NORMATIVE:** Minion Agent MUST reproduce Pi's observable behavior and semantics as closely as practical. Pi source is the default behavioral compatibility oracle for agent-loop, LLM/provider, message-transformation, tool, session, harness, and related behavior. The primary intentional architectural divergence is Minion Agent's plugin/runtime architecture.
>
> Do not replace Pi behavior with a cleaner, more generalized, or more abstract semantic design merely for extensibility. When behavior is uncertain, inspect the relevant adopted Pi source before designing from first principles. Any intentional behavioral divergence from Pi MUST be explicit, justified, named in this document or the normative spec, and covered by language-neutral conformance wherever observable across implementations.
>
> Plugin architecture may change ownership, registration, lifecycle, composition, and implementation boundaries. It does not by itself justify changing Pi-visible behavior.

This rule changes the design method:

```text
Pi source at adopted revision
    -> enumerate observable semantics
    -> freeze those semantics
    -> express them through Minion runtime/plugin ownership
    -> add Minion-only architecture only where externally equivalent
```

The inverse workflow — designing an idealized abstraction first and checking Pi approximately afterward — is prohibited for Pi-derived behavior.

## Reference material

Studied at these revisions:

| Project | Revision | Used for |
|---|---|---|
| `earendil-works/pi` | `b7bb00b936dbe21b8e160b3e89efdec361846699`, 2026-08-20 | Normative behavioral oracle for `packages/ai`, `packages/agent`, and `packages/agent/src/harness`; model-backed eval patterns |
| `deepseek-ai/deepseek-harness` | checkout of 2026-08-18 | Cordis architecture at scale; loop driver; capability seams; invariants; test strategy |
| `cordiverse/cordis` | checkout of 2026-08-18 | Plugin runtime semantics: context, fiber, service, registry, events, effects |
| `cordiverse/paper` | Draft of 2026-08-13 | Revertible effects and reactive coeffects, the theory behind Cordis |

Statements about these projects in this document are source-grounded. For Pi-derived behavior, the adopted Pi revision above is the compatibility baseline.

### Pi compatibility baseline and drift governance

Every frozen Minion Agent design records the exact Pi revision against which its observable semantics were audited.

Before implementing or freezing each phase, compare the Pi source paths relevant to that phase between the recorded baseline and the current candidate Pi revision. Every observable semantic change discovered by that comparison receives exactly one disposition:

1. **Adopted** — update the Minion design/spec/conformance to match Pi.
2. **Deferred Pi parity** — record the missing behavior and the phase/trigger that will add it.
3. **Intentional behavioral divergence** — justify why Minion differs and pin that difference explicitly.

Silence is not a valid disposition for a discovered Pi semantic change.

Purely architectural differences that preserve Pi-visible behavior — for example append-only storage instead of Pi's in-memory transcript, or plugin-owned registration instead of direct object fields — do not require a behavioral-divergence label.

The reference revision is not a permanent fork point. It is an audit checkpoint. Updating Pi parity is an explicit source-diff exercise, never a broad speculative redesign.


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

**Stratum C — Pi AgentHarness durable operation parity.** Current Pi has a substantial durable harness: lane-scoped runs, compaction and navigation operations, suspended/deferred operations, durable program state, pending writes, replay policy, crash/deferred resume, manual/automatic drive, and operation outcomes. Minion does not implement that state machine in the initial phases, but under the mandatory Pi-fidelity goal this is a **known deferred parity phase**, not an optional future abstraction.

The initial session interface is therefore designed so durable operation state can be added behind/alongside it without replacing the already-frozen message, provider, tool, and session semantics. Until the parity phase lands, Minion MUST NOT claim complete Pi AgentHarness parity.

Also deferred, with the trigger for each recorded in §9: Cordis's declarative YAML loader, hot module replacement, isolation realms (service shadowing — not to be confused with scoped registration in §3, which is in scope), and a `ctx.jobs` scheduling service.

This scope was validated against a real long-lived multi-agent application before implementation; see `2026-08-18-foundation-validation.md`. That exercise remains valid as a workload test, but it does not override Pi parity. A real application may not exercise every Pi behavior; missing workload demand is not evidence that a Pi semantic may be silently dropped.


---

## 2. Repository layout

```
minion-agent-python/
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
  design/            # this document — language-neutral
  spec/              # normative semantic rules — language-neutral
  plans/
    python/          # implementation plans for this implementation
```

The split follows the same line as the repository name. `design/`, `spec/`,
and `conformance/` describe the project and are shared by any implementation;
an implementation plan is a sequence of tasks against one language's
libraries, tooling, and idioms, so it lives under that language.

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

The lifecycle is normative:

```text
Pending
  ├─ dependencies satisfied → Loading
  └─ dispose → Disposed

Loading
  ├─ successful valid commit → Active
  ├─ dependency invalidation → unwind → Pending
  ├─ initialization failure → unwind → Failed
  └─ dispose → unwind → Disposed

Active
  ├─ dependency loss → Unloading → unwind → Pending
  └─ dispose → Unloading → unwind → Disposed

Failed
  └─ dispose → Disposed

Disposed
  └─ dispose → no-op
```

`Failed` is stable: dependency changes do not retry a failed plugin. This phase
has no restart operation, so recovery is disposal followed by a fresh mount.
`Failed` represents a legitimate, reported plugin-initialization failure. An
impossible runtime state or broken state-machine invariant remains a framework
failure; it does not become an ordinary failed fiber.

Loading is a transaction over owned effects. A fiber becomes `ACTIVE` only
after plugin initialization succeeds and every dependency is still actively
visible. Dependency loss or explicit disposal invalidates the attempt. An
invalidated loading attempt cannot continue creating owned effects while its
existing effects are being unwound: the attempt must first be stopped, settled,
or otherwise prevented from registering another effect, and only then may
reverse sequential unwind begin. The cancellation, generation, or transition-
serialization mechanism is implementation-specific; the no-race result is not.

### Service resolution

`ctx.tools` and `ctx.require(ToolService)` are two views over one canonical
mechanism. These rules follow Cordis's `reflect.ts` and are normative.

**Identity is the name, not the type.** A service is keyed by `(name, realm)`.
Cordis allocates one symbol per name on the root context and resolves through
a single slot. `ctx.require(ToolService)` resolves by the name the Protocol
declares; it is a typed view, never a second key space.

**Normative names compare by string value.** Language object identity, enum
singleton identity, allocation or pointer identity, and a language's type
identity never participate in semantic identity. This rule applies to service
names, event names, session event kinds, and future named extension points.

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
- **Every waterfall event declares a terminal continuation** — the value
  produced when the innermost listener delegates, and the result of an empty
  chain. It is never implicitly `None`.

That last rule is load-bearing for transformation chains. If delegating past the
last listener yielded `None`, a chain in which every listener cooperatively
delegates would discard the very value it spent the chain transforming.
Terminals per event:

| Event | Terminal continuation |
|---|---|
| `agent/pre-request` | The current request context/messages unchanged |
| `tools/pre-execute` | `Proceed(args)` with the validated arguments unchanged |
| `tools/post-execute` | The tool result as currently transformed |

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

The provider-neutral vocabulary mirrors current Pi semantics first. Provider plugins may use language-specific types internally, but session serialization and cross-language conformance preserve the same observable information.

Core content:

```text
TextBlock
    text: string
    text_signature?: string

ThinkingBlock
    thinking: string
    thinking_signature?: string
    redacted: bool = false

ImageBlock
    mime_type: string
    data | reference

ToolCall
    id: string
    name: string
    arguments: object
    thought_signature?: string
    namespace?: string
```

The three signature fields are deliberately opaque strings, matching Pi rather than introducing a generalized provider-metadata envelope. Provider-neutral core code persists them but does not assign provider-independent meaning to their payload.

`AssistantMessage` carries the Pi-visible response identity/state needed by provider replay and caller behavior:

```text
AssistantMessage
    content: [TextBlock | ThinkingBlock | ToolCall, ...]
    api
    provider
    model
    response_model?
    response_id?
    diagnostics?
    usage
    stop_reason
    deferred?
    error_message?
    raw_stop_reason?
    end_turn?
    timestamp
```

`ToolResultMessage` carries `tool_call_id`, `tool_name`, text/image content, structured `details`, optional tool-execution `usage`, `added_tool_names`, `is_error`, and timestamp.

`StopReason` is:

```text
pending | stop | length | tool_use | error | aborted | deferred
```

`Usage` mirrors Pi's accounting surface:

```text
Usage
    input
    output
    cache_read
    cache_write
    cache_write_1h?
    reasoning?
    total_tokens
    cost:
        input
        output
        cache_read
        cache_write
        total
```

The exact numeric representation of cost is language-specific until the shared serialization schema pins it; semantic fields and arithmetic meaning are not.

Stream chunks/events mirror Pi's event protocol:

```text
start
text_start / text_delta / text_end
thinking_start / thinking_delta / thinking_end
tool_call_start / tool_call_delta / tool_call_end
done
error
```

Partial-update events carry the current partial assistant message so a UI can render any prefix. Signatures are finalized block metadata; they need not be emitted incrementally in deltas.

**Image content** is part of the provider-neutral vocabulary. Minion's logged representation is stronger than Pi's in-memory base64 form but must preserve identical model-visible bytes. A model-visible reference is immutable: a mutable filesystem path or remote URL is resolved before logging/dispatch into content-addressed identity. Provider upload handles, signed URLs, and base64 wire encodings remain adapter details.

### Pi-compatible target-model message transformation

Pi has a distinct semantic stage between application/session projection and provider wire encoding. Minion MUST preserve it:

```text
session/log derivation
    -> application AgentMessage -> Message projection
    -> target-model message transformation
    -> API/provider wire encoder
```

This stage is not an optional convenience hook. The implementation may be owned by the relevant LLM/plugin service, but its observable behavior is normative.

For the adopted Pi baseline, transformation includes:

**Unsupported images.** If the target model does not accept images:

- user images become the text placeholder `(image omitted: model does not support images)`;
- tool-result images become `(tool image omitted: model does not support images)`;
- adjacent equivalent placeholders are not duplicated.

**Thinking compatibility.**

```text
same provider/api/model + signed thinking
    -> retain thinking and signature, including empty visible thinking

same provider/api/model + unsigned non-empty thinking
    -> retain visible thinking

same provider/api/model + empty unsigned thinking
    -> remove

different target model + non-redacted thinking
    -> convert visible thinking to ordinary text
    -> provider replay signature does not survive

different target model + redacted thinking
    -> omit
```

**Other provider replay metadata.**

- Cross-model text remains text but loses `text_signature`.
- Cross-model tool calls lose `thought_signature`.
- Provider/API/model compatibility is decided from the source assistant message identity and target model, matching Pi; Minion does not invent a second signature-provenance registry.

**Tool-call ID normalization.** The target API may normalize foreign tool-call identifiers. Any matching `ToolResultMessage.tool_call_id` is rewritten consistently.

**Orphaned tool calls.** Before a later user/assistant message, and at end of reconstructed history, unresolved assistant tool calls receive synthetic error tool results:

```text
content = "No result provided"
is_error = true
```

This closes provider-required call/result pairs.

**Errored/aborted historical assistants.** Assistant messages with `stop_reason = error | aborted` are excluded from provider replay. They remain in Minion's audit log but are not sent back as valid conversational history.

These transformations operate on the effective derived history. They therefore naturally respect fork/reset/compaction because those operations determine which messages reach this stage.

Provider-specific adapters may add API-specific normalization after this shared Pi-compatible stage, but may not undo its semantics without an explicit divergence.

### Responses-family replay signatures

For Responses-style APIs, Minion follows Pi's content-owned replay model.

- `ThinkingBlock.thinking_signature` stores the opaque complete provider reasoning item needed for replay.
- A retained same-model signed thinking block is replayed by the compatible adapter.
- The adapter does not synthesize a provider reasoning item from visible thinking text alone.
- A same-model unsigned thinking block contributes no replay item at Responses encoding even though its visible text may remain in provider-neutral history.
- Signature parse/conversion failures follow the ordinary provider-stream error path; Minion core does not introduce a generalized signature-validation subsystem.

`TextBlock.text_signature` preserves provider message item identity/phase for Responses-family replay. The adapter matches Pi's current V1/legacy behavior: V1 carries message id plus optional `commentary | final_answer` phase; an older plain string is treated as the legacy message id.

Responses reasoning presentation also follows Pi: streamed reasoning-summary text and reasoning-text both contribute to visible `ThinkingBlock.thinking`. On item finalization, visible thinking prefers provider summary text when present, otherwise reasoning-content text, otherwise the accumulated streamed thinking. The full replayable reasoning item remains separate in `thinking_signature`.

`ToolCall.thought_signature` is similarly provider-specific opaque replay metadata used by APIs that need it; cross-model transformation strips it.

### The never-raises contract

Pi's stream contract is load-bearing, but the boundary must be stated at the right abstraction.

**Service/model lookup and provider selection happen before provider-stream invocation.** Invalid Minion API arguments, unresolved service names, unknown model identifiers, and caller misuse may fail normally at that outer layer.

Once an adapter/provider stream function is invoked with a resolved model/context, expected request/provider/network/runtime failures are represented in the returned `AssistantStream`, not raised to its consumer.

```text
outer llm service resolution
    invalid caller/config/model selection
    -> ordinary failure before provider stream invocation

provider stream(model, context, options)
    -> returns AssistantStream
    -> expected request/provider/network/model/cancellation failures
       settle through terminal error/aborted message
```

Programming/invariant failures remain programming failures; this rule does not require swallowing impossible internal states.

The public stream is terminal/fused:

```text
non-terminal* -> exactly one terminal -> EOF
```

Premature raw EOF without a terminal response is normalized to an in-band adapter/protocol error carrying the accumulated partial message. The wrapper does not secretly drain after terminal delivery.

Cancellation after stream creation remains in-band as `aborted`. Releasing/closing a stream cancels owned pending provider work and exits transport resources; if the consumer itself stops consuming, no synthetic extra terminal must be delivered to that departed consumer.

### API and provider split

Pi separates wire protocol (`api`) from endpoint/auth/model (`provider`). Minion preserves that split while registering providers through plugins.

The initial implementation set remains:

| API | Providers |
|---|---|
| `openai-completions` | OpenRouter, Ollama, LM Studio, generic OpenAI-compatible |
| `codex-responses` | OpenAI Codex |
| `mock` | scripted provider for conformance |

This table is build order, not the limit of the vocabulary. Provider-neutral types retain Pi semantics needed for later Pi-compatible APIs.

Real-provider implementation is parity-driven: each adapter is audited against the corresponding current Pi adapter and compatibility helpers before freeze. Provider compatibility options that affect observable requests — role choice, finish-reason handling, reasoning format, strict/constrained tools, cache retention, session affinity, tool-result shape, routing, deferred tools, and related options — are adopted or explicitly deferred rather than silently ignored.

### Model and request options

Pi exposes provider-neutral/request-level controls such as `tool_choice`, reasoning level/budgets, max output tokens, retry-delay cap, transport preference, cache retention, `session_id`, sampling parameters, deferred execution request, metadata, and provider-specific option extensions.

Minion need not place every provider knob in the generic core type, but every Pi-observable option used by an implemented API must have an equivalent path through configuration/plugin registration to the provider adapter. Omitting an option is a parity decision, not an accidental absence.

### Authentication

Authentication remains a seam rather than a file path. Provider plugins consume a resolved credential source/login/store composition.

For Codex, Minion matches the applicable Pi/Codex OAuth behavior while preserving credential ownership:

- an external credential source may be read according to its supported interop contract;
- externally owned refresh state is not independently mutated unless that owner explicitly grants mutation authority;
- Minion-owned interactive/device login credentials may be refreshed and atomically persisted by Minion;
- provider-specific environment/file fallback chains are not invented implicitly.


---

## 5. The session log (`ctx.sessions`)

Append-only, sequence-numbered, and JSON-validated at append time.

**Model-visible means logged.** Anything reaching a model request must be
reconstructable from the log, and an invariant asserts it (§8).

### Two tiers of event

The **surface** subset — `user/message`, `assistant/message`, `tool/result` —
is what `derive_messages()` projects into model history.

Everything else is **log-only**: `run/start`, `run/end`, `turn/start`, `turn/end`,
`assistant/chunk` (token-level replay fidelity), `tool/call`, and `request/header`.

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

### Relationship to Pi's message projection

Minion intentionally changes storage/extension architecture without changing Pi-visible projection behavior.

Pi's application-facing `convertToLlm` maps extensible `AgentMessage[]` into provider-neutral `Message[]`. Minion derives the effective session surface from the log and applies explicit surface projections for plugin-defined events/messages. This replaces Pi's in-memory extension mechanism structurally.

After that application/session projection, Minion still runs the **Pi-compatible target-model transformation defined in §4** before provider encoding. The two stages are distinct:

```text
log/session surface projection
    ~= Pi AgentMessage -> Message conversion

target-model transformation
    ~= Pi transformMessages(messages, targetModel)
```

`agent/pre-request` may still provide policy/context rewriting, but it is not a substitute for the mandatory target-model transformation rules. Plugins cannot opt out of those rules for an implemented Pi-compatible API unless the deployment explicitly selects a documented behavioral divergence.

Precisely: filtering/projection extension mechanics differ; target-model and provider-visible behavior are kept equivalent and conformance-pinned.


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

Two consequences of an open namespace are normative, and neither is
self-evident — both were re-derived the hard way during cross-language
alignment.

**The event name is the identity, and is compared by value.** A language may
offer constants for the core names — an enum, a set of `const`s — but those are
ergonomics. `"session/reset"` and whatever constant a language uses for it are
the *same event*. An implementation that compares by identity rather than value
will silently ignore the literal spelling: a reset appended as a plain string
would not floor derivation, and two implementations would disagree about the
same log. Every lookup that matches an event by kind — reset, compaction, and
any future operation — matches on the string.

**An open namespace is not an open surface.** Declaring an event name does not
admit it to model history. A plugin event is log-only until the deployment
declares it as surface, exactly as `turn/start` is. Conflating the two would
let any plugin inject into what the model sees merely by choosing a name, which
is the opposite of the two-tier contract above.

The logging namespace is truly open: the session log accepts any well-formed
event-name string without requiring prior registration. Extension registration
may attach additional validation and/or a surface projection; it does not
create the underlying identity. Merely appending or recognizing a plugin event
therefore never makes it model-visible. Surface admission requires an explicit
deployment projection or a projection standardized by this specification.

The first rule has no executable backstop for the *operations* path: the
session scenario format constructs reset and compaction through the API, so it
cannot express a raw-named operation event. Scenarios pin the surface path;
the operations path rests on this text plus each implementation's own tests.

---

## 6. The agent loop (`ctx.agent_loop`)

### Definitions, instances, and runs

Two things are routinely called "the agent" and remain separate:

| Term | Meaning |
|---|---|
| **AgentDefinition** | Reusable configuration: persona, capability composition, policy. Holds no conversation state. |
| **AgentInstance** | One live execution identity: one inbox, one session/log view, one lifecycle owner, and at most one active run. |

One definition may have many concurrent instances. `ctx.agents` creates/resumes instances and returns an owning handle.

Pi terminology is normative for the observable loop:

```text
Run / invocation
    bounded by agent_start ... agent_end
    may contain multiple turns

Turn
    exactly one assistant response
    + the tool calls/results caused by that assistant response
```

An implementation may use a private "step" object internally, but MUST NOT redefine observable `turn` to mean a whole multi-request run. Pi event projection, session events, and conformance use the Pi meaning.

Scopes follow Minion architecture: definition scope -> instance scope -> optional run/turn child scopes. A scope that owns an executing tool remains alive until that tool settles.

### Observable Agent state

An `AgentInstance` handle exposes Pi-equivalent observable state, whether stored directly or projected from Minion's log/runtime:

```text
system_prompt
model
thinking_level
tools
messages
is_streaming
streaming_message?
pending_tool_calls
error_message?
signal?
```

Assignments/replacements of tool/message collections must not create aliasing that lets external mutation silently mutate internal state; copy-on-assignment semantics equivalent to Pi are sufficient.

`is_streaming` becomes true for an active prompt/continuation run and stays true until the final `agent_end` listeners/projections that participate in settlement have completed. `wait_for_idle()` resolves only after that settlement. `streaming_message` exposes the current partial assistant response. `pending_tool_calls` is the current set of executing call ids. `error_message` reflects the most recent failed/aborted assistant turn according to Pi behavior.

### Run and turn lifecycle

A run has this observable shape:

```text
agent_start
    [initial input message lifecycle]

    turn_start
        target-model request
        assistant message streaming lifecycle
        tool calls/results caused by that assistant response
    turn_end

    prepare-next-turn phase
    should-stop phase
    steering poll

    ... zero or more further turns ...

    follow-up poll only when the run would otherwise stop
    ... possibly more turns ...

agent_end
```

The package-internal driver remains imperative. Minion's session/log is semantic truth; Pi's `AgentEvent` stream is a projection whose trace is conformance-pinned.

One Pi turn corresponds to one provider assistant response plus its tool batch. Tool results that cause another provider request end the current turn first; the next provider request starts a new turn.

### Prompt and continue behavior

`prompt()` starts a new run only when the instance is idle. Calling it while active is a caller error; callers use `steer()` or `followup()` to queue additional messages.

`continue()` is also idle-only.

- Empty transcript -> caller error.
- Last message user/tool-result -> continue from the existing transcript.
- Last message assistant -> first drain eligible steering according to steering mode; if none, drain eligible follow-up according to follow-up mode; if neither exists, caller error.

`reset()` is idle-only and clears the active public transcript projection/runtime queues as defined by the higher-level Agent API. Durable Minion session reset remains the log operation in §5; the implementation must not conflate an active-run reset with an unsafe concurrent mutation.

### Inbox and queue policies

Pi exposes two queues and two independent policies:

```text
steering
    injected after the current turn/tool batch
    before the next provider request
    mode = all | one-at-a-time

follow-up
    polled only when the run would otherwise finish
    mode = all | one-at-a-time
```

Both default to `one-at-a-time`.

Minion may additionally expose `inject()` as a plugin/runtime convenience for silent context input, but it is a Minion extension and MUST NOT change Pi's `steer`/`followup` ordering.

For Pi-compatible runs, ordering after a turn is:

```text
turn_end
-> prepareNextTurn-equivalent
-> shouldStopAfterTurn-equivalent
-> steering queue poll
-> if continuation still required: next turn
-> otherwise follow-up queue poll
```

Hard termination from the finalized tool batch takes precedence before optional continuation policy.

Queue clear/introspection operations are part of the Agent handle surface: clear steering, clear follow-up, clear all, and whether queued messages remain.

### Input provenance and delivery

Minion retains its general-purpose provenance extension:

```text
InputEnvelope { id, message, origin }
Run/turn causal references
```

`origin` is opaque JSON-safe data. Delivery remains an application concern. This is a Minion extension over Pi and is acceptable because it does not alter Pi-visible provider/loop semantics when unused.

### Message/context preparation

Before every provider request:

```text
effective session history
-> optional application/plugin context transform
-> AgentMessage -> Message projection
-> mandatory target-model transformation (§4)
-> system prompt + visible tool schemas
-> provider request
```

Pi's `transformContext` and `convertToLlm` contracts are failure-sensitive: application conversion/transform hooks should return safe fallback data rather than throw for ordinary application failure. Minion plugin equivalents may use the runtime event model, but a plugin bug remains a programming failure.

`prepareNextTurn` semantics are distinct from per-request context transformation. It runs only between completed turns and may replace the model, context, and thinking level for the next turn.

### Decision algebra

Minion still expresses single-valued Pi hooks through plugin events, but plugin composition may not change the resulting Pi behavior.

**`agent/pre-request` / context transformation.** A waterfall/transformation event may rewrite the next request context. Its default terminal continuation is the unchanged context. Where Minion exposes a request-reason discriminator, the reasons reflect actual Pi call sites rather than redefining turns:

```text
initial | tool_results | steering | follow_up | continuation
```

**`agent/turn-stopping`.** Represents Pi's `shouldStopAfterTurn`. It executes after `prepareNextTurn` and before steering polling, unless hard tool-batch termination already ended the run. Default is continue.

**`tools/pre-execute`.** Represents Pi's `beforeToolCall`: after argument preparation/validation, may block execution with a reason and optional terminate hint.

**`tools/post-execute`.** Represents Pi's `afterToolCall`: field-by-field replacement; supplied `content`, `details`, `is_error`, `usage`, and `terminate` replace those fields, omitted fields remain unchanged, and there is no deep merge.

Waterfall mechanics remain those in §3: fixed admitted-listener snapshot, explicit terminal continuation, `next()` at most once.

### Active abort/cancellation

Current Pi supports active run abort through one run-scoped cancellation signal.

Minion MUST expose equivalent behavior:

```text
AgentInstance.abort()
    -> abort the active run signal

signal propagates to:
    provider stream / pending provider attempt
    before/after tool hooks
    tool execution
    context transforms/listeners that accept cancellation
```

A provider stream that is already returned settles expected cancellation in-band as `aborted`. Tool/hook code receives the signal and is responsible for honoring it according to its contract.

Abort does not mean "wait until the next provider-request boundary." It is an active cancellation request. Exact cleanup may be cooperative at lower layers, but the signal is propagated immediately.

`agent_end` remains the final run event, and idle settlement waits for awaited final listeners.

### Agent progress isolation

Awaiting anything inside one AgentInstance must not occupy a runtime-global critical section or block another instance's progress. Human approval, remote tools, MCP, provider I/O, subagents, event listeners, and cancellation settlement may all suspend independently.

### Tool batch execution

Minion preserves current Pi tool behavior.

**Execution mode.**

- Global default is parallel.
- A tool may override its `execution_mode`.
- If any call in a parallel batch requires sequential execution, Pi's batch-contagion behavior is preserved: the affected batch executes sequentially rather than inventing DSH grouping semantics.

**Argument preparation.**

```text
raw tool-call arguments
-> optional tool.prepare_arguments compatibility shim
-> schema validation
-> beforeToolCall / tools-pre-execute
-> execute
```

Argument preparation is part of the tool's compatibility contract and occurs before validation.

**Length-stop safety.** If an assistant response terminates with `stop_reason = length`, none of its emitted tool calls execute. Every call receives an error tool result because arguments may be truncated. This is a Pi safety semantic, not a provider-specific optimization.

**Parallel preflight and ordering.** In parallel mode, calls are prepared/preflighted in assistant source order, allowed calls execute concurrently, `tool_execution_end` emits in completion order, and durable/model-visible tool-result messages are appended/emitted in assistant source order.

**Streaming updates.** Tool partial updates may produce `tool_execution_update`. Updates arriving after the tool's execution promise/result has settled are ignored.

**Tool result fields.** Final/partial tool results may carry text/images, structured details, optional tool execution `usage`, `added_tool_names`, and `terminate`.

**Terminate folding.** Early hard termination fires only when every finalized result in the assistant's tool batch has `terminate = true`. Blocked calls participate according to their finalized blocked result. When this rule fires, it precedes optional `shouldStopAfterTurn`/turn-stopping logic.

**Error conversion.** Expected tool execution failure becomes an error tool result visible to the model. Programming/invariant failure remains a programming failure.

### Tool selection and constrained sampling

The provider-neutral tool definition includes name, description, parameter schema, and the Pi-compatible constrained-sampling seam needed by implemented providers:

```text
constrained_sampling =
    false
    | json_schema(strict = prefer | require)
    | grammar(variants by provider grammar format)
```

Adapters may fall back according to Pi compatibility rules when a target API cannot honor a constrained form. The plugin registry remains the authoritative owner of executable tools and schemas.

### Pi event projection

The projection plugin exposes Pi-equivalent observable agent events:

```text
agent_start
agent_end(messages)

turn_start
turn_end(message, tool_results)

message_start(message)
message_update(message, assistant_stream_event)
message_end(message)

tool_execution_start(id, name, args)
tool_execution_update(id, name, args, partial_result)
tool_execution_end(id, name, result, is_error)
```

`agent_end` is the final emitted event, but awaited listeners are part of run settlement.


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

Stated as one rule: **an execution seam normalizes operational and environmental
failures into typed `Result` errors; framework and provider invariant violations
and programming errors remain exceptions.**

Normalization is the provider's obligation, not the caller's. A bare `OSError`,
a transport error, or a vendor SDK exception is translated into the capability's
error vocabulary before it crosses the seam. An unmapped backend exception
escaping a seam is itself a provider bug — the seam's contract is that its
callers never write `except` around ordinary I/O.

This is deliberately un-Pythonic and deliberately confined. It keeps "tool
failed" (becomes an error tool result the model sees) structurally distinct
from "harness bug" (crashes loudly), and it maps directly onto Rust.

`FileSystem` covers path resolution without symlink following, `canonical_path`
for explicit resolution, text / binary / line-limited reads, write, append,
atomic rename, `file_info` and `list_dir` (never following symlinks), temporary
directories and files, and `cleanup`. `Shell.exec` takes cwd, env with
`inherit_env`, timeout, abort signal, and stdout/stderr streaming callbacks.

### Tools (`ctx.tools`)

Registration is an effect, so unloading a plugin withdraws its tools and the next request's visible schemas change accordingly. `ctx.tools` remains the authoritative source of executable tools and their model-facing schemas.

The tool contract mirrors Pi semantics:

```text
Tool
    name
    description
    parameters
    constrained_sampling?
    prepare_arguments?
    execution_mode?
    execute(..., signal, on_update)

ToolResult
    content[text|image]
    details
    usage?
    added_tool_names?
    terminate?
```

The execution pipeline and ordering are specified in §6. `added_tool_names` means those tools become available from that transcript point forward; provider adapters that support deferred/dynamic tool loading may encode that fact natively, while others simply observe the expanded visible registry on the next request.

Built-in tools, each plugin-owned: **bash**, **read**, **write**, **edit**, **glob**, **grep**.

Two pieces of Pi behavior should be ported rather than redesigned: its edit match-and-replace semantics/failure modes and serialization of concurrent mutations to the same file identity.

Approval and sandboxing remain plugins around `tools/pre-execute`, preserving Pi-visible allow/block behavior without hard-coding application policy into the generic registry.


### System prompt and skills

**Single ownership of tool schemas.** `ctx.tools` owns executable tools and their schemas. `ctx.system_prompt` owns textual prompt sections only.

System-prompt and skill behavior tracks current Pi where implemented.

**Skill discovery.**

- recursively load declared `SKILL.md` files;
- load direct root `.md` files with valid skill frontmatter where Pi does;
- missing input directories are skipped rather than failing the whole load;
- honor `.gitignore`, `.ignore`, and `.fdignore`;
- deterministic traversal/order;
- `SKILL.md` may derive the skill name from its parent directory;
- direct root `.md` skill candidates require a usable description;
- validate Pi-compatible name/description constraints;
- malformed declared skills produce structured diagnostics rather than failing all discovery;
- `disable-model-invocation: true` keeps the skill available to explicit application invocation but excludes it from model-facing available-skills prompt content.

**Model-facing skill block.** Minion reproduces Pi's current available-skills XML shape and escaping:

```xml
<available_skills>
  <skill>
    <name>...</name>
    <description>...</description>
    <location>...</location>
  </skill>
</available_skills>
```

The surrounding instructional text preserves Pi semantics: read the full matching skill file, and resolve relative references against the skill file's directory.

Explicit skill invocation renders the complete skill with its location and relative-path instruction in the Pi-compatible invocation format.

Plugins may contribute prompt sections, but the final assembled request is content-addressed/log-reconstructable (§5).


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

Pi's default settings and trigger are preserved:

```text
enabled = true
reserve_tokens = 16384
keep_recent_tokens = 20000

compact when:
    estimated_context_tokens > model.context_window - reserve_tokens
```

The **estimator** is part of the behavior, not an implementation detail.

For the adopted Pi baseline:

1. search backward for the most recent assistant message with valid non-zero usage;
2. ignore usage from assistant messages whose stop reason is `error` or `aborted`;
3. prefer `usage.total_tokens` when non-zero, otherwise use the component sum;
4. estimate only messages after that usage-bearing assistant message with the Pi-compatible message heuristic;
5. if no usable assistant usage exists, estimate the whole effective history;
6. image/token heuristics and supported message roles are deterministic and conformance/Tier-2 tested.

This prevents two implementations with identical thresholds from compacting at different turns.

Cut-point selection preserves Pi's valid-boundary/split-turn behavior. `retained_tail` keeps approximately the configured recent context and carries the exact recent messages Pi would retain.

Compaction summary model calls are standalone requests. They disable reusable prompt-cache retention and use a fresh session/routing identity so a one-off summary request does not contaminate the primary conversation's cache/session affinity. Retry behavior follows the provider retry contract.

Minion's append-only log remains an architectural improvement that preserves Pi-visible history semantics: compaction appends a compaction event rather than deleting historical entries.

A compaction event identifies:

- superseded effective surface range;
- replacement summary;
- retained-tail messages/provenance;
- Pi-equivalent `tokens_before`;
- optional usage and implementation details such as file-operation summaries when that harness feature is implemented.

`derive_messages()` applies repeated/nested replacements deterministically and never emits both an original message and its retained-tail copy.

Compaction/branch summaries are projected to provider history using the Pi-compatible wrapper strings defined by the harness message projection below.

### Pi harness message projections

Minion's open session-event namespace replaces Pi's TypeScript declaration-merging mechanism structurally, but built-in Pi harness messages retain their model-visible projections.

At minimum the parity surface includes:

**Bash execution.** A `bashExecution`-equivalent record may be display/audit-only when `exclude_from_context` is set. Otherwise it projects to a user message with Pi-compatible command/output/cancelled/non-zero-exit/truncation formatting.

**Custom message.** A Pi-compatible custom message projects to a user message carrying its text/image content; UI display metadata remains non-model-visible.

**Branch summary.**

```text
The following is a summary of a branch that this conversation came back from:

<summary>
{summary}
</summary>
```

**Compaction summary.**

```text
The conversation history before this point was compacted into the following summary:

<summary>
{summary}
</summary>
```

The exact wrappers are normative because they reach the model. Storage/event representation may differ.


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
              waterfall-terminal-continuation · waterfall-empty-chain-terminal

  agent/      run-lifecycle · pi-turn-lifecycle · steering · follow-up · cancellation
              prompt-while-running-rejected · continue-ordering
              agent-idle-after-end-listeners
              concurrent-agents-isolated-logs · blocked-agent-does-not-stall-peers
              origin-survives-one-at-a-time · causes-preserved-under-claim-all
              proactive-turn-carries-provenance · turn-completes-undelivered
              turn-scope-awaits-inflight-tool
              post-execute-multi-listener-order · post-execute-field-replacement
              post-execute-omitted-fields-preserved · post-execute-no-deep-merge
              stream-error-rides-the-stream · service-bad-model-fails-before-provider-stream
              terminate-precedes-turn-stopping · terminate-not-overridable
              length-stop-executes-no-tools
              tool-end-completion-order-result-source-order
              late-tool-update-ignored
              same-model-thinking-signature-replayed
              same-model-unsigned-thinking-not-replayed
              cross-model-thinking-converts-to-text
              cross-model-redacted-thinking-omitted
              responses-text-signature-replayed
              target-model-orphan-tool-result-synthesized
              target-model-error-assistant-not-replayed
              nonvision-user-image-placeholder
              nonvision-tool-image-placeholder

  session/    fork-ancestry-derivation · reset-excludes-prior-surface
              compact-now-then-derive · compaction-repeated-and-nested
              retained-tail-no-duplicate
              request-header-component-reuse
              content-signatures-round-trip
              pi-harness-message-projections
              compaction-estimator-last-valid-usage
              compaction-estimator-zero-usage-fallback
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

Canonical additions cover two legitimate cases. An **alignment scenario**
exposes an existing implementation that contradicts a frozen rule; a
**coverage scenario** makes already-correct behavior executable. Both follow
one workflow:

1. Add or extend the canonical schema and scenario.
2. Run it against every existing implementation capable of executing it.
3. If an implementation contradicts the frozen rule, demonstrate the
   divergence, apply the minimum correction, and restore it to green.
4. If existing implementations already conform, retain the scenario as added
   compatibility coverage without manufacturing a failure.
5. Sync or vendor the canonical case into implementations that carry a copy.
6. Implement or verify each implementation against the same case.
7. Keep every applicable implementation green.

An implementation need not fail before a canonical scenario is valuable. The
scenario's role is to pin compatibility, not to prove that a bug once existed.

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

Each phase ends with green conformance scenarios for the Pi-visible behavior it adds. Before a phase freezes, run the Pi drift check in §Reference material for the source paths owned by that phase.

**Phase 0 — conformance scenario formats and Pi baseline.** Schema-fix `runtime/`, `agent/`, and `session/` scenario families; record the adopted Pi revision and a machine/checklist-friendly mapping from Pi source areas to Minion semantic surfaces.

1. **Plugin runtime.** Context, fiber, service resolution, registry, events, effects, reactive load/unload. This is the primary intentional architectural divergence and is tested independently from Pi behavior.
2. **LLM vocabulary, target-model transformation, mock adapter, session log, telemetry vocabulary.** Land the current Pi-equivalent content/message/usage/stop-reason vocabulary, signatures, target-model transformation, session derivation, never-raises provider-stream contract, and recording telemetry seam.
3. **Agent loop.** Pi run/turn lifecycle, public Agent state projection, prompt/continue behavior, steering/follow-up order and modes, active abort signal, event projection, and mock provider/tool continuation.
4. **Tools.** Real registry, prepare-arguments, constrained-sampling metadata, before/after pipelines, batching/contagion, `length` safety rule, streaming updates, ordering, usage, `added_tool_names`, terminate folding.
5. **Real providers.** `openai-completions` and `codex-responses`, implemented by auditing the corresponding current Pi adapters/helper modules field-by-field. Wire fixtures and live/manual checks supplement but do not replace source parity.
6. **Execution seams and built-in tools.** `ctx.fs`, `ctx.shell`, `ctx.subprocess`, execution-world compatibility, then bash/read/write/edit/glob/grep with Pi-equivalent observable behavior.
7. **Prompt, skills, compaction, harness message projections, telemetry sinks.** Exact skill discovery/prompt format, Pi compaction estimator/cut points/summary requests, built-in harness message projections, production telemetry sinks.
8. **Model-backed evals.**
9. **Deferred Pi AgentHarness parity.** Lanes, durable operation program state, run/compaction/navigation outcomes, suspended/deferred operations, pending writes, replay policy, crash/deferred resume, manual/automatic drive, and related harness hooks/events. This phase may be split, but it is a parity commitment rather than a hypothetical trigger.

Phases 1–4 produce a Pi-compatible agent driven entirely by a mock. Phase 5 adds real provider behavior. Phase 9 closes the known durable-harness parity gap.

### Deferred, with triggers

| Deferred | Introduce when |
|---|---|
| Isolation realms (service shadowing) | An application needs a different implementation of a service per agent rather than scoped registrations within one shared service. This is a Minion architecture concern, not Pi parity. |
| `ctx.jobs` | A second independent consumer needs shared scheduling semantics. Fiber-owned work remains sufficient until then. |
| Declarative loader, HMR | Configuration-driven runtime composition becomes a user-facing requirement. |
| Additional Pi providers/APIs | Add according to project priority, but when an API/provider is implemented its observable behavior is audited against the adopted/current Pi source rather than approximated from another adapter. |

`ctx.subprocess` remains Phase 6 because protocol-over-stdio integrations require argv/raw-stream lifecycle rather than shell command execution.


---

## 10. Open questions and decision log

No unresolved architectural question blocks the plugin runtime, but implementation planning MUST account for the explicit Pi parity work in this revision. The durable AgentHarness is a known deferred parity phase, not a closed omission. Items resolved during design and
recorded here for traceability:


Resolved by Pi-fidelity audit (2026-08-20):

- **Project goal tightened** — Pi is the default behavioral oracle; plugin/runtime architecture is the primary intentional divergence. Cleaner generalized semantics do not override Pi behavior.
- **Pi drift governance** — every phase records/audits an adopted Pi revision and disposes changed observable behavior as adopted, deferred parity, or intentional divergence.
- **LLM vocabulary refreshed** — text/thinking replay signatures, redacted thinking, tool thought signature/namespace, richer assistant response metadata, `deferred` stop reason, and Pi usage accounting are part of the shared semantic surface.
- **Target-model transformation is first-class** — image downgrade placeholders, cross-model thinking conversion/removal, signature stripping, tool-call-id rewriting, synthetic orphan tool results, and removal of errored/aborted historical assistant responses match Pi's transformation stage.
- **Run/turn terminology corrected** — Pi turn means one assistant response plus its tool batch; an overall prompt/continuation invocation is a run.
- **Active abort restored** — one run-scoped cancellation signal propagates to provider, hooks, and tools; cancellation is not only a between-request flag.
- **Public Agent state restored** — streaming/partial-message/pending-tool/error and idle-after-final-listener semantics are observable parity requirements.
- **Queue ordering pinned** — prepare-next-turn, stop decision, steering, then follow-up-when-otherwise-idle.
- **Tool parity expanded** — `prepareArguments`, `length`-stop no-execution rule, tool usage, late-update ignoring, constrained-sampling seam, and ordering rules.
- **Compaction estimator pinned** — last valid provider usage plus deterministic trailing estimation; summary calls isolate cache/session routing.
- **Harness message and skill projections tightened** — Pi model-visible wrappers/discovery behavior are copied while Minion keeps plugin/session-event ownership.
- **Durable AgentHarness reclassified** — still deferred from initial phases, but explicitly a Pi-parity phase rather than optional future work.

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

Resolved during cross-language alignment (2026-08-18), while a second
implementation was being built against this spec:

- **Event identity is the name string, compared by value** (§5). Constants are
  ergonomics; an identity comparison silently ignores the literal spelling and
  makes two implementations disagree about the same log.
- **An open event namespace is not an open surface** (§5). A plugin event is
  log-only until a deployment declares it as surface.
- **Event registration is not identity creation** (§5). Any well-formed event
  name may be logged; registration attaches validation or projection, while
  explicit surface admission remains separate.
- **Fiber loading and unwind cannot race** (§3). Invalidating a loading attempt
  prevents further owned-effect creation before unwind begins; a stale attempt
  cannot commit `ACTIVE`. `Failed` is stable until disposal/remount and denotes
  plugin initialization failure rather than a framework invariant violation.
- **Canonical additions may align or cover** (§8). A new scenario either
  exposes a divergence or pins behavior implementations already satisfy; the
  workflow never manufactures a failure merely to justify coverage.

The event-identity and surface rules were divergences found in the first
implementation. The lifecycle and workflow rules were ambiguities found while
designing the second. All are clarifications of existing contracts rather than
new subsystem features.

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

Resolved at design freeze (2026-08-18):

- **Every waterfall event declares a terminal continuation** (§3). An implicit
  `None` terminal would have let a fully cooperative transformation chain
  discard the value it had just transformed.
- **Hard termination precedes `agent/turn-stopping`** (§6). The `terminate`
  batch rule is a loop invariant inherited from pi, where no hook could force
  continuation; an explicit `Continue` decision must not override it.
- **Model-visible image references resolve to immutable identity before
  dispatch** (§4), reusing §5's content-addressed artifacts. A mutable path or
  URL would break request reconstruction silently.
- **Execution seams normalize operational failures into typed `Result` errors**
  (§7); invariant violations and programming errors stay exceptions.
- **Service resolution** — name-keyed identity, exclusive registration, no
  fallback stack, `ACTIVE`-gated visibility; shadowing deferred with realms (§3).
- **Execution world** — declared world identity with activation-time
  validation, exceeding both references (§7).
- **Decision algebra** — `pre-request` carries a request-reason discriminator;
  `turn-stopping` is first-non-`NoOpinion`-wins with short-circuit;
  `post-execute` composes by field replacement without deep merge (§6).
- **Normativity** — prose spec defines general rules, conformance is the oracle
  for behavior it covers (§8).
