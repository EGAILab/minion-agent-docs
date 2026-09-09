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

This section covers the GENERIC seam between the Agent/tool layers and a concrete model provider;
it does NOT cover any real provider's own wire-protocol encoding (Responses/Completions/etc.),
which is Layer 11's own territory (`PROV-###`). PASS 1 of this section misstated part of the
required Pi shape and mischaracterized current Rust as already satisfying it; an independent Rust
contract review (`assurance/layers/10-provider-abstraction-rust-contract-review.md`,
`L10-R001`-`R004`) corrected both, and this is that corrected text.

**The implementation-module contract (`AI-028`).** Pinned Pi's own `ProviderStreams` interface
(`packages/ai/src/types.ts:272-281`) requires BOTH `stream(model, context, options?)` AND
`streamSimple(model, context, options?)` (neither carries a `?`); only `fetchDeferred?`/
`cancelDeferred?` are truly optional. `streamSimple` is not a distinct stream operation: every
implementation (e.g. `packages/ai/src/api/openai-completions.ts:683-702`) is a thin, PER-API
wrapper translating the provider-neutral `SimpleStreamOptions` into that API's own specific options
shape, then delegating to that SAME module's own `stream()`. Its own content is therefore
inherently wire-protocol-specific, with nothing generic to specify until a real provider exists;
Minion's own generic `Adapter` protocol at Layer 10 maps only to `stream`, and `streamSimple`'s own
translation responsibility is explicitly DEFERRED to Layer 11 (`PROV-###`) -- disclosed, not
silently declared optional and not silently omitted.

`StreamFunction` (`types.ts:324-336`) is the call shape a caller actually invokes once resolved,
with its own doc comment stating the never-raises contract explicitly (already certified above,
`AI-012`): once invoked, expected request/model/runtime failures settle IN the returned stream --
there is no separate error-return channel in Pi's own type at all, for ANY reason, including an
implementation detecting a problem synchronously before it would otherwise start streaming (an
invalid configuration, an unusable request). Minion's `Adapter` protocol is the direct, faithful
mapping for `stream`: `provider: str`, `api: str`, `models: frozenset[str]` (identity/capability
fields folded onto the implementation object itself, since Minion has no separate `Provider` type
the way Pi does -- see below) plus `stream(request: Request) -> AssistantStream`, matching
`ProviderStreams.stream`'s own `(model, context, options?)` shape collapsed into Minion's own
single `Request` value -- Python's own `Adapter.stream` has no error-return channel either,
correctly matching Pi. The reference implementation of this contract is `MockAdapter`/
`ScriptedResponse` -- a real adapter, not a test double: it deliberately exercises the contract's
edge cases (a truncated raw stream, a misbehaving provider emitting chunks after its own terminal,
an adapter-detected failure settling as an in-band error terminal) rather than only the happy path.

Current Rust does NOT yet satisfy this row: `LlmAdapter::start(&self, request) -> Result<
RawAssistantStream, AdapterStartError>` grants an eager, typed failure channel usable even after a
model has already resolved and the adapter's own code has already run -- exactly the case Pi's own
contract forbids. The permanent Rust test `adapter_start_failure_remains_eager_and_typed` locks
this in as current behavior (an "invalid provider configuration" failure -- an ordinary expected
case, not a programming bug -- surfaces as an eager `Err(LlmStartError::AdapterStart(_))`, never
reaching a returned stream); Rust's own `ScriptedAdapter` diverges from Python's `MockAdapter` the
same way for an exhausted script. This is a genuine, OPEN, disclosed `PI_PARITY_DEFECT` in current
Rust production -- not something this pass claims already satisfied -- with its remediation left to
a future Rust implementation pass.

**Model resolution and the unresolvable-identity boundary (`AI-029`).** Pinned Pi's own resolution
mechanism (`packages/ai/src/models.ts:735-812`) is two-level: a `Provider` is built once via
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

`LlmService.stream()` looks a full `provider + model + api` triple up in its own registry (`AI-030`
owns how entries get there) and raises `UnknownModelError` EAGERLY when absent -- collapsing what
Pi splits into "no Provider selected for this model at all" (a config-layer question Minion does
not have) and "this Provider has no implementation for this model's own api" (Pi's own in-band
case) into one eager check. This is an intentional, disclosed Minion architectural SIMPLIFICATION,
not a literal port of Pi's own two-level structure: the eager/lazy boundary already stated above
already authorizes it (an unresolvable model is a caller bug, discoverable immediately) and it is
exercised by canonical evidence (`eager-invalid-model-fails-before-stream`,
`llm-service-registration-and-replacement.yaml`'s own unresolvable-identity query). Current Rust
correctly performs this exact eager rejection (`LlmService::stream`'s own `LlmStartError::
UnknownModel` case, confirmed against source) -- this row's own resolution/unresolvable-identity
behavior IS already satisfied; `AdapterStart` handling (a DIFFERENT, resolved-identity case) is
`AI-028`'s own separate, currently open concern.

**Registration, replacement, withdrawal, and introspection (`AI-030`).** Pi has NO adapter-
registration concept at all -- every model a Pi caller can stream from is either statically listed
or fetched into a `Provider`'s own catalog at construction time, never dynamically registered or
withdrawn by arbitrary calling code the way this surface works. `LlmService.register(adapter)`
populates one registry entry per model the adapter declares in its own `adapter.models`, keyed by
the full `provider + model + api` triple, and returns a withdrawal handle scoped to EXACTLY the
entries that call added. A later `register()` call for the same key intentionally REPLACES the
earlier entry in place (not an accidental collision). Calling an earlier registration's own
withdrawal handle after a later `register()` call has already replaced that same key is a SAFE
NO-OP -- the handle only ever removes an entry it can verify it still owns, so a stale withdrawal
can never remove a different registrant's own later entry. `LlmService.models()` returns every
currently resolvable identity -- Minion's own minimal introspection surface, with no Pi analogue
(Pi's own `Provider`/`Models` collection exposes richer catalog/refresh semantics -- dynamic model
overlays, credential-scoped filtering -- this project does not need yet, since Minion has no
config-driven provider catalog of its own).

Current Rust only PARTIALLY satisfies this row: `LlmService::register` takes one
`(ModelIdentity, Arc<dyn LlmAdapter>)` pair per call (not an adapter-declared model set) and
performs last-write replacement via a plain map insert, correctly satisfying the replacement half;
it has NO withdrawal handle, NO stale-withdrawal protection, and NO `models()` introspection at
all. Those are OPEN, disclosed gaps -- whether and how a future Rust implementation pass closes
them is that pass's own decision, not asserted here.

`ModelId.api` currently defaults to `"mock"` in Python's own type -- a PYTHON-SPECIFIC temporary
compromise (`LLM-F006`, Layer 02), correct for every caller today since the mock adapter is the
sole registered adapter, not a cross-language Minion contract this section mandates: certified Rust
already requires an explicit, strict three-part `ModelIdentity` with no equivalent default, and
that stricter shape -- not Python's own temporary convenience -- is Layer 10's own actual
normative target. Python's default becomes actively wrong once a second API exists (Layer 11) and
must be removed then, so every caller must say which API it means; this is a disclosed, tracked
Python-side follow-up, not something Rust needs to match.
