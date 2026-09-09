# LLM Semantics

Canonical serialization uses snake_case.

```text
TextBlock{text,text_signature?}
ThinkingBlock{thinking,thinking_signature?,redacted=false}
ImageBlock{mime_type,data|reference}
ToolCall{id,name,arguments,thought_signature?,namespace?}

UserMessage{role=user,content:string|[TextBlock|ImageBlock],timestamp}

AssistantMessage{
  role=assistant,content:[TextBlock|ThinkingBlock|ToolCall],api,provider,model,response_model?,
  response_id?,diagnostics?,usage,stop_reason,deferred?,error_message?,raw_stop_reason?,end_turn?,
  timestamp
}

ToolResultMessage{
  role=tool_result,tool_call_id,tool_name,content:[TextBlock|ImageBlock],details?,usage?,
  added_tool_names?,is_error,timestamp
}

DeferredHandle{provider,model_id,api,id,expires_at?,poll_after_ms?,data?}
DiagnosticError{message,name?,stack?,code?}
AssistantMessageDiagnostic{type,timestamp,error?,details?}
```

`StopReason = pending|stop|length|tool_use|error|aborted|deferred`.

`Usage` contains input/output/cache_read/cache_write/cache_write_1h?/reasoning?/total_tokens and
cost input/output/cache_read/cache_write/total.

Model compatibility identity is exactly `provider + api + model_id`.

Once a provider stream exists, expected provider/network/model/cancellation/runtime streaming
failures settle in-band. Public shape is `non-terminal* -> exactly one terminal -> EOF`; premature
raw EOF synthesizes one error terminal preserving partial assistant state; the public stream is then fused.

Responses replay uses content-owned opaque strings: retained same-model `thinking_signature` replays;
same-model unsigned thinking emits no reasoning replay item. `text_signature` preserves response
message identity/phase where supported.

The request carried into `stream()` gains one optional, additive field: the active run's own
cancellation signal (`AI-027`, Layer 09 -- `runtime/signal.py::RunSignal`, absent for every
request outside an Agent-driven run). This project has no real network transport yet, so `stream()`
itself never inspects or acts on it -- it is carried through to the adapter unexamined, exactly like
every other request field, and an adapter MAY poll it to represent `StopReason.ABORTED` in its own
returned stream, cooperatively, matching pinned Pi's own `streamFunction(model, context, {...config,
signal})`. Actual transport cancellation remains deferred to `PROV-004`. See `spec/agent.md`'s own
"Active abort propagation" section for the complete consumer/settlement matrix this signal serves.

## Provider abstraction (Layer 10)

This section formalizes a contract already implemented and already Pi-parity-audited under Layer
02's own pass (`LLM-018`, `assurance/layers/02-llm.md`) but never previously given its own
normative section here -- Layer 10's own pass closes that documentary gap. It covers the GENERIC
seam between the Agent/tool layers and a concrete model provider; it does NOT cover any real
provider's own wire-protocol encoding (Responses/Completions/etc.), which is Layer 11's own
territory (`PROV-###`).

**The implementation-module contract (`AI-028`).** Pinned Pi's own `ProviderStreams` interface
(`packages/ai/src/types.ts:272-281`) is the uniform shape every API implementation module under
`packages/ai/src/api/` satisfies: `stream(model, context, options?) -> AssistantMessageEventStream`
(Pi also allows optional `streamSimple`/`fetchDeferred`/`cancelDeferred`, not yet needed here).
`StreamFunction` (`types.ts:324-336`) is the same call shape a caller actually invokes once one is
resolved, with its own doc comment stating the never-raises contract explicitly (already certified
above, `AI-012`). Minion's `Adapter` protocol is the direct, faithful mapping: `provider: str`,
`api: str`, `models: frozenset[str]` (identity/capability fields folded onto the implementation
object itself, since Minion has no separate `Provider` type the way Pi does -- see below) plus
`stream(request: Request) -> AssistantStream`, matching `ProviderStreams.stream`'s own
`(model, context, options?)` shape collapsed into Minion's own single `Request` value. The
reference implementation of this contract is `MockAdapter`/`ScriptedResponse` -- a real adapter,
not a test double: it deliberately exercises the contract's edge cases (a truncated raw stream, a
misbehaving provider emitting chunks after its own terminal) rather than only the happy path, and
every canonical scenario exercising the never-raises contract drives it through this exact
implementation.

**Registration and model resolution (`AI-029`).** Pinned Pi's own resolution mechanism
(`packages/ai/src/models.ts:735-812`) is two-level: a `Provider` is built once via
`createProvider({..., api})`, where `api` is either a single `ProviderStreams` (every model this
provider serves uses the one implementation) or a map keyed by `model.api` (a provider whose own
models span more than one wire protocol); `apiFor(model)` resolves which implementation a given
model uses, and a model whose own api has no matching entry produces an IN-BAND stream error
(Pi's own `dispatch()` returns a `lazyStream` that throws only once actually consumed), not an
eager exception -- Pi represents "this provider has no implementation for this model's own api" as
a never-raises-contract failure. A separate, earlier step outside `packages/ai/src/types.ts`/
`models.ts` -- the CLI/config layer that builds a `Models` collection from `models.json`/built-in
catalogs -- is what rejects a genuinely unknown model id before any `Provider`/`stream` call
happens at all; Minion has no equivalent config-driven catalog of its own.

Minion's own `LlmService` collapses this into ONE flat, global registry: `_adapters: dict[ModelId,
Adapter]`, keyed by the full `provider + model + api` triple rather than Pi's two-level `Provider`
object (itself keyed by `model.api` only, since `provider`/`model` are already fixed once a
`Provider` is selected). `register(adapter)` populates one entry per model the adapter declares,
returning a withdrawal handle scoped to exactly that adapter's own registrations; a later adapter
registering the same key intentionally replaces the earlier one in place. `LlmService.stream()`
looks the full triple up and raises `UnknownModelError` EAGERLY when absent -- collapsing what Pi
splits into "no Provider selected for this model at all" (a config-layer question Minion does not
have) and "this Provider has no implementation for this model's own api" (Pi's own in-band case)
into one eager check. This is an intentional, disclosed Minion architectural SIMPLIFICATION, not a
literal port of Pi's own two-level structure: the eager/lazy boundary already stated above already
authorizes it (an unresolvable model is a caller bug, discoverable immediately) and it is already
exercised by canonical evidence (`eager-invalid-model-fails-before-stream`). `LlmService.models()`
(every currently resolvable model) has no direct Pi analogue -- Pi's own `Provider`/`Models`
collection exposes richer catalog/refresh semantics (dynamic model overlays, credential-scoped
filtering) this project does not need yet, since Minion has no config-driven provider catalog of
its own; it is Minion's own minimal introspection surface, intentional and disclosed.

`ModelId.api` currently defaults to `"mock"` -- correct for every caller today, since the mock
adapter is the sole registered adapter; every real construction site in production code already
passes an explicit `api` value, so the default is reachable only from test-fixture convenience
construction, never a path that could collide two distinct API identities. The default becomes
actively wrong once a second API exists (Layer 11) and must be removed then, so every caller must
say which API it means.
