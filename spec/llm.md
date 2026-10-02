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

## Raw tool-call argument value domain (`AI-003`, cross-layer delta `L0206-D002`)

**Status (`minion-agent#103`):** CERTIFIED_CLOSED. Contract code #105 → `c9b6e910`, docs #210 → `2ef3828b`. Python: no production change, implementation review APPROVED (docs #210). Rust: code #110 → `2ec46f4b`, docs #215 → `e6bcd2cc`, closure review on `minion-agent-docs#215`.

- **Authorization.** Owner decision on `L0506-D002-Q001`, Option 1 (`minion-agent#99` comment `5926162818`). This is a separate cross-layer post-certification delta. It is not part of `L0506-D002` (prepared strings) or `L0206-D001` (key order, K1). No intentional divergence; deferring to Layer 11 was rejected; no whole-layer reopen.
- **The rule.** `ToolCall.arguments` is not constrained to what a host JSON library or native string type can hold. It holds the value pinned Pi's `JSON.parse` produces from a provider's argument text (`parseStreamingJson` → `parseJsonWithRepair`). That is a JavaScript value:

```text
string   a JavaScript String: any sequence of UTF-16 code units -- BMP values, valid surrogate
         pairs, unpaired high or low surrogates at any position, empty, NUL -- in values and keys
number   a binary64 value as JSON.parse yields it: -0 (sign kept, also from a negative underflow),
         +Infinity / -Infinity (from an overflowing literal), correctly rounded otherwise
         (9007199254740993 -> 9007199254740992)
object / array / true / false / null   as JSON
```

Object key **enumeration order** is `L0206-D001`'s (K1): see "Tool-argument object key order" below.

**Boundaries.** The exact value MUST survive, unchanged, through every certified boundary:

| Boundary | Owner | Rule |
|---|---|---|
| construction of a `ToolCall` (and of the `AssistantMessage` holding it) | Layer 02 | accepted as given; no validation, replacement or normalization of strings or numbers |
| session append | Layer 03 | the log accepts it (the "JSON-safe" check admits the domain above) |
| session replay / projection | Layer 03 | returns the identical value |
| `tool_execution_start` / `tool_execution_update` arguments | Layer 06 | the raw value (`IR-L06-005`) |
| `tool_execution_end` | Layer 06 | carries no arguments: N/A |
| Layer-06 input | Layer 06 | for a tool **without** `prepare_arguments`, the `tools/pre-execute` listener and `execute` observe exactly the raw value |

**Projections are separate boundaries.**
- **Pinned Pi's persisted session file** (`coding-agent` `session-manager.ts`, `JSON.stringify` per line):
  - it escapes an unpaired surrogate as `\udXXX` and round-trips strings exactly;
  - it writes `-0` as `0` and ±Infinity as `null`, so a reloaded file holds `0`/`null`.

  No Minion layer maps that file today. Minion's certified Layer-03 log is not a byte form: it keeps and replays the live value. A future persisted form MUST reproduce Pi's projection there, and only there.
- No U+FFFD replacement occurs anywhere on the raw path. Replacement belongs to UTF-8 file encoding (`spec/tools.md` String semantics).

**Decoder requirement** (for the first raw decoder, e.g. Layer 11 providers, which consume this contract):
- Decoding provider argument text MUST be `JSON.parse`-equivalent: binary64 rounding, `-0`, overflow to ±Infinity, and unpaired escaped surrogates kept.
- A general-purpose decoder that keeps exact big integers, decodes `-0` as integer `0`, or rejects or replaces lone surrogates does not satisfy it. Python's `json.loads` does the first two.

**Representation.** The contract fixes values, not types.
- **Python.** A `str` (valid pairs combined, unpaired surrogates as surrogate code points). An `int` for an integral finite value decoded as an integer; a `float` for every other number, including `-0.0` and ±`inf`.
- **Rust.** It needs a raw argument value able to hold this domain in `ToolCall.arguments`, the session log and the event payloads. `serde_json::Value` is not the semantic authority: it cannot hold an unpaired surrogate or ±Infinity. The type design is delegated to contract and implementation review (decision §7). Host JSON library limitations are not semantic authority.

**Evidence.**
- **Authority:** `minion-agent-docs` `assurance/layers/data/l0206-raw-boundaries/` (characterization `l0206-d002-characterization.md`).
- **Canonical scenarios:** `minion-agent` `conformance/agent/raw-arguments/` (shape `raw-arguments-scenario.schema.json`), 38 cases: 22 string, 15 number, 1 key. The runner observes the value at every boundary above. The tool reports exactly one partial result, so the `tools/update` payload and the `on_execution_update` delivery are observed too (`L0206-D002-R001`).
- **Number tokens in canonical cases** (`L0206-D002-R002`). A number is a named `+Infinity`, `-Infinity` or `-0`, or a finite literal that is exactly its binary64 value's ECMAScript `Number::toString`. A language-neutral preflight enforces this before dispatch, so no binding rounds or widens a fixture. `NaN` is outside the raw domain, because `JSON.parse` cannot produce it.
  - **Convergence `CE-L0206-D002-01`, agreed.**
    - **N1/N2.** A token names the **binary64 value** it parses to, not its spelled digits. For example `1000000000000000100` is the value `1000000000000000128`, which is what `JSON.parse` yields. A binding decodes a fixture through binary64, and an integral spelling becomes that value's exact integer.
    - **N3'.** Observation is strict and total. A runtime integer that is not exactly a binary64 value is reported as a controlled out-of-domain marker, never rounded and never raising.
    - **N4.** The expected observation is computed from the scenario text, never through the fixture decoder.
- **Negative controls** (decision §11):
  - the raw lone surrogate rejected;
  - replaced with U+FFFD at decode;
  - the session's encoding unable to hold it (a strict-JSON log);
  - session decode normalizing it;
  - the event payload seeing a normalized value;
  - correct until persistence but lost on replay (Pi's JSON projection applied to the log).

**WP-13.2** (decision §10): non-blocking. Its rules are total for any string a binding receives, and its `unpaired_surrogate_arguments` cases already defer raw decoding to this hazard.

## Tool-argument object key order (`AI-003`, `TOOL-003`, cross-layer delta `L0206-D001`, K1)

**Status (`minion-agent#100`):** CONTRACT_DRAFT. Python: NOT_IMPLEMENTED. Rust: NOT_IMPLEMENTED.

- **Authorization.** Owner K1 decision, Option 1 (`minion-agent#99` comment `5924847773`).
  - This is a separate cross-layer post-certification delta (Layers 02/03, 05, 06). It is not part of `L0206-D002` (values) or `L0506-D002` (prepared strings).
  - There is no intentional divergence.
  - Revalidation is targeted (decision §9); no whole-layer reopen.
- **Evidence.**
  - Characterization: `assurance/layers/l0206-d001-characterization.md`.
  - Feasibility: `l0206-d001-feasibility-matrix.md`.
  - Authority: `assurance/layers/data/l0206-d001-k1/` (`out/k1-boundaries.json`, `out/k1.json`) and `data/l0206-raw-boundaries/`.

**The rule.** At every boundary below, a tool-argument object, and every object nested in it at any depth (inside arrays too), enumerates its own keys in **ECMAScript `OrdinaryOwnPropertyKeys` order**:

```text
1. array-index keys, ascending numerically
     an array index is the canonical decimal string of an integer 0 .. 4294967294:
     "0", "7", "10", "4294967294" are indices;
     "4294967295", "00", "01", "007", "-0", "-1", "+1", "1.0", "1e3", " 1", "0x1" and
     "9007199254740993" are not
2. every other key, in insertion order
```

- The order is a property of the object's **construction and mutation history**.
  - **Duplicate keys** (decoding): a duplicate keeps its **first** position and takes the **last** value.
  - **A key assigned later** (a hook's in-place mutation) joins by the same rule. A new index key goes to its ascending position among the indices; a new ordinary key goes last; an existing key keeps its position.
  - **`__proto__` from decoding** is an ordinary own key.
- **Nothing reorders**: no sorting, no schema order, no canonicalization, no coercion side effect.

**Boundaries.**

| Boundary | Owner | Rule |
|---|---|---|
| construction of `ToolCall.arguments` (decoding, adapters, any constructor) | Layer 02/03 | enumerates by the rule |
| session append, replay and projection | Layer 03 | the replayed object enumerates as the appended one did |
| `tool_execution_start` / `tool_execution_update` `args` | Layer 06 | the raw object's order |
| `prepare_arguments` result (for example `edit`'s re-parse of `edits`) | Layer 05/06, the tool | the rule applies to the shim's object, including objects it decodes |
| validation | Layer 06 | **does not reorder**: the validated object enumerates as its input did (pinned Pi `structuredClone` + `Value.Convert`). A declared property order is **not** imposed, and coercion (`"5"` → `5`) does not move a key |
| `tools/pre-execute` listener (Pi `beforeToolCall`) | Layer 06 | sees the validated object's order. An **in-place mutation** is visible downstream, ordered by the rule |
| a listener's **replacement** arguments (`Proceed(arguments=...)`, a Minion mapping: Pi's hook cannot replace) | Layer 06 | the replacement object enumerates by the rule applied to its own construction |
| `execute` | Layer 06 | the object the hook saw, after any mutation, or the replacement |
| every serialization of an argument object (a persisted session form, a provider payload) | Layer 03 / Layer 11 | emits keys in that order, as `JSON.stringify` does |

**Typed-model parameters (K1-F1; the Minion `TOOL-003` pydantic mapping).** A tool whose parameters are a typed model receives the model's validated values, keyed and ordered as follows:
- the keys present in the validated input, in the input's order (by the rule);
- then any keys the model fills by default, in declared order, each placed by the rule.

Declared field order is never imposed on keys the input supplied. (Pinned Pi has no defaulting step, so the defaulted keys are the mapping's own. Their placement follows the rule, as if assigned after the input's keys.)

**Not in scope.**
- **The validation-failure diagnostic text** (K1-F2). Minion's certified `TOOL-003` text is its validator's message, not Pi's `JSON.stringify(arguments, null, 2)` text (`spec/tools.md`). That text parity is not reopened, and its key order follows from it.
- **Tool-result `details` key order**, the `L0506-D003` observation. The carrier is a tool result, not a tool-argument object (decision §1).
- **Provider projection** is Layer 11's, the first binding to serialize arguments to a provider. It consumes this rule (row above).

**Representation.** The contract fixes observable enumeration order, not types (decision §4).
- **Python.** A `dict` iterates in insertion order. A binding must therefore keep every argument object it hands to an observer in the rule's order, **after** every construction and mutation. Insertion order alone is insufficient (decision §8), because a mutation appends.
- **Rust.** The raw `IndexMap` (insertion) and the prepared `BTreeMap` (sorted) are both insufficient. The type design is Rust's.

**Evidence and controls.**
- **Canonical scenarios:** `minion-agent` `conformance/agent/key-order/` (`key-order-scenario.schema.json`), generated from `out/k1-boundaries.json`. There are 29 cases, and each observes the recursive enumeration at every boundary above that the case reaches.
- **Negative controls.** Each MUST fail the corpus, while the conforming implementation passes:
  - insertion order (Python today);
  - sorted order (Rust prepared today);
  - declared-schema order;
  - reordering at the top level only;
  - a non-canonical numeral treated as an index (`"01"`, `"4294967295"`);
  - ordering applied at decode but lost after a hook mutation;
  - ordering lost on replay.

**WP-13.2** (decision §6) remains non-blocking. Its key-order independence witness exists on both sides, and WP-13.2 is CERTIFIED_CLOSED with K1 outside its owned surface.

## Provider abstraction (Layer 10)

This section covers the GENERIC seam between the Agent/tool layers and a concrete model provider;
it does NOT cover any real provider's own wire-protocol encoding (Responses/Completions/etc.),
which is Layer 11's own territory (`PROV-###`). PASS 1 of this section misstated part of the
required Pi shape and mischaracterized current Rust as already satisfying it; an independent Rust
contract review (`assurance/layers/10-provider-abstraction-rust-contract-review.md`,
`L10-R001`-`R004`) corrected both, and this is that corrected text.

**The implementation-module contract (`AI-028`, `stream` only -- see `AI-031` for `streamSimple`).**
Pinned Pi's own `ProviderStreams` interface (`packages/ai/src/types.ts:272-281`) requires BOTH
`stream(model, context, options?)` AND `streamSimple(model, context, options?)` (neither carries a
`?`); only `fetchDeferred?`/`cancelDeferred?` are truly optional. An earlier revision of this
section bundled both operations under one `adopted` characterization despite `streamSimple` having
no Layer-10 surface built at all; a repeated independent review (`L10-R001`/`L10-R002`) and the
resulting convergence (`C10-C001`) found the bundling itself defective, since one disposition cannot
honestly cover one operation that is satisfied and one that is not yet built. `AI-028` now covers
only `stream`; `streamSimple`'s own content, disposition, and closure criterion live at `AI-031`
below.

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

**`streamSimple` (`AI-031`, deferred parity).** Pinned Pi's own `streamSimple` is required, not
optional. Every implementation (e.g. `packages/ai/src/api/openai-completions.ts:683-702`) is a
thin, PER-API wrapper translating the provider-neutral `SimpleStreamOptions` (`toolChoice`,
`reasoning`, `thinkingBudgets`, `deferred`) into that API's own specific options shape, then
delegating to that SAME module's own `stream()`. Its own content is therefore inherently
wire-protocol-specific, with nothing generic to specify at Layer 10's own abstraction level until a
real provider (Layer 11) exists to receive a translated request. Minion's own generic `Adapter`
protocol at Layer 10 maps only to `stream` (`AI-028`); `streamSimple` has no Layer-10 surface of its
own to build yet, and any future per-provider "simple options" translation is that provider's own
adapter-construction concern, not a Layer-10 `Adapter` protocol method. Disposition: `deferred
parity`, not `adopted` and not silently omitted.

Closure criterion, binding on whichever future pass closes this row: the obligation Layer 11 owes is
an EXTERNALLY INVOCABLE operation matching Pi's own `streamSimple(model, context, options) ->
AssistantMessageEventStream` shape (the exact language-specific shape may differ) -- not merely
internal per-provider option-translation plumbing with no caller-facing entry point. A future
revision marked "complete" by building some internal translation helper without ever exposing a
callable would not satisfy this row; it must be re-opened, not silently accepted.

**Model resolution and the unresolvable-identity boundary (`AI-029`, intentional divergence).** Pinned Pi's own resolution
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
authorizes the collapse (an unresolvable model is a caller bug, discoverable immediately), but
authorization is a separate claim from "matches Pi's own observable behavior" -- Pi observably
settles the "wrong api for this provider" sub-case IN-BAND, Minion observably rejects it eagerly, so
this row's own disposition is `intentional divergence`, not `adopted` (`L10-R002`/`C10-C001`; an
earlier revision reasoned through the divergence correctly but left its own `disposition:` field
uncorrected). It is exercised by canonical evidence (`eager-invalid-model-fails-before-stream`,
`llm-service-registration-and-replacement.yaml`'s own unresolvable-identity query). Current Rust
correctly performs this exact eager rejection (`LlmService::stream`'s own `LlmStartError::
UnknownModel` case, confirmed against source) -- this row's own resolution/unresolvable-identity
behavior IS already satisfied; `AdapterStart` handling (a DIFFERENT, resolved-identity case) is
`AI-028`'s own separate, currently open concern.

**Registration, replacement, withdrawal, and introspection (`AI-030`, intentional divergence).**
Pinned Pi exposes THREE real, currently-live registration surfaces (`L10-R005`, corrected from an
earlier revision's false "Pi has no adapter-registration concept at all" claim), none of which
Minion's own registry directly adopts:

1. `models.ts::MutableModels.setProvider(provider)` -- keyed by `provider.id` alone (no model/api
component); a WHOLE-PROVIDER upsert, the new `Provider`'s own `getModels()` entirely REPLACES
whatever that provider id previously exposed, with no per-model merge. `deleteProvider(id)`/
`clearProviders()` remove at the same whole-provider granularity; `getProviders`/`getProvider`/
`getModels`/`getModel` are the introspection surface. Current, forward Pi architecture.

2. `compat.ts`'s generic `registerApiProvider(provider, sourceId?)`/`unregisterApiProviders
(sourceId)` -- keyed by `provider.api` (a single api string, one module-level `Map`), also
last-write-wins; `unregisterApiProviders(sourceId)` removes EVERY entry whose own recorded
`sourceId` matches the given tag, a bulk, tag-scoped removal at this generic-primitive level. This
module is Pi's own explicitly TEMPORARY compatibility surface (its own docstring: "deleted with the
coding-agent ModelManager migration") -- live in the pinned revision, not Pi's forward direction.

3. `compat.ts::registerFauxProvider(options)`, built on top of (2): generates a fresh, pseudo-random
`sourceId` on EVERY call -- NOT collision-checked, so this text does not claim mathematically
guaranteed uniqueness, only that each call's own tag is freshly generated and normally distinct --
registers through `registerApiProvider(..., sourceId)`, and returns a `FauxProviderRegistration`
(`providers/faux.ts:132-141`) whose own public `unregister()` method closes over THAT call's own tag
and calls `unregisterApiProviders(sourceId)` with it. For the observed distinct-tag case (the normal
case, since tags are freshly generated per call), this IS a live, direct per-registration-call
unregistration precedent on Pi's OWN faux/mock provider surface -- the exact scope this section
concerns itself with -- even though it is a thin per-call convention layered over (2)'s
bulk-tag-scoped primitive, not a separate registry mechanism.

Stale/superseded removal for (2)/(3) depends on TAG IDENTITY, not call order alone: registering
`api=x` under `source=A` then `source=B`, then unregistering `source=A`, leaves B's own entry
untouched (the current entry's tag no longer matches A) -- the SAME safe outcome Minion's own rule
gives, for the observed distinct-tag case (3) normally is; registering `api=x` under the SAME
`source=S` twice, then unregistering `source=S`, removes the current entry (tags coincide) -- a
deliberate bulk/current-entry removal, the outcome IF a caller ever reused one tag across calls at
the generic-primitive level (2), which `registerFauxProvider` itself never does.

Minion's own `LlmService` matches NONE of the three: it keys per FULL `(provider, model, api)`
identity (finer-grained than any of the three, which key on a single string), replaces per KEY
rather than per whole provider/api (two Minion adapters sharing a `provider` id but declaring
different models COEXIST, unlike (1)'s wholesale swap), and makes per-call ownership the GENERIC
registration rule -- EVERY `register()` call gets its own handle unconditionally -- rather than a
faux-specific convention layered over a bulk-tag-scoped primitive the way (3) achieves its own
per-call safety. (3) is a genuine, narrower Pi precedent for per-call safety specifically on Pi's
OWN mock-provider surface; it does not by itself justify Minion's own broader, generic
granularity/composition/introspection differences from (1)/(2), each of which remains a deliberate,
disclosed divergence.

Governance (`§11.7`, DECIDED): the repository owner APPROVED continuing Minion's existing registry
semantics as an intentional divergence, explicitly scoped to this section's own registration/
replacement/withdrawal/introspection granularity, against exactly the three-surface comparison
above. Redesign toward any of the three Pi surfaces is NOT required. `LlmService.register
(adapter)` populates one registry entry per model the adapter declares in its own `adapter.models`,
keyed by the full `provider + model + api` triple, and returns a withdrawal handle scoped to EXACTLY
the entries that specific `register()` CALL added. A later `register()` call for the same key
intentionally REPLACES the earlier entry in place (not an accidental collision). Calling an earlier
registration's own withdrawal handle after a later `register()` call has already replaced that same
key is a SAFE NO-OP.

Ownership is per REGISTRATION CALL, not per adapter OBJECT (`C10-C005`): each `register()` call
stores a fresh, opaque per-call token alongside its adapter, and the returned handle's own
withdrawal closure checks that TOKEN, not adapter-object identity, before deleting an entry -- an
earlier revision checked adapter-object identity alone, which conflates "adapter object identity"
with "registration call identity" and is correct only when a given adapter object is registered at
most once. Registering the IDENTICAL adapter object twice under two separate `register()` calls
gives each call independent ownership of its own entry; the token-based design is what makes this
correct (an earlier revision's identity-only check let the FIRST call's own handle incorrectly
remove the SECOND call's own live entry).

Withdrawal is IDEMPOTENT and safely repeat-callable, whether a caller invokes the same handle twice
or a handle has since been superseded by a later registration: the first successful call to a
handle deletes the entry it still owns; every later call to that SAME handle finds no matching token
and does nothing. This is a binding, non-negotiable observable rule: any future implementation
(Rust included) may choose its own mechanism to enforce per-call ownership, but a consuming,
move-only handle type that turns a second call to an already-withdrawn handle into a compile error
rather than a runtime no-op would not satisfy this row -- it would make the idempotent-repeat-
withdrawal observation impossible to express at all.

The canonical scenario grammar (`conformance/agent/llm-service-*.yaml`) addresses registration by
HANDLE id, not fixture id: a `register` step is `{adapter: <fixture id>, as: <handle id>}`, and a
`withdraw` step names the `as` handle a prior `register` step declared, never an adapter fixture
directly -- this mirrors the production API's own handle-returning shape and lets a scenario express
two independent handles for the same adapter fixture.

`LlmService.models()` returns every currently resolvable identity -- Minion's own minimal
introspection surface, at the SAME full-identity granularity as the rest of this row (not any of
the three Pi surfaces' own coarser keys above). Pi's own `MutableModels.getProviders`/`getProvider`/
`getModels`/`getModel` and `compat.ts`'s own `getApiProvider`/`getApiProviders` are real,
directly-comparable introspection surfaces (not "no analogue"), but each exposes richer
catalog/refresh semantics at ITS OWN coarser key -- dynamic model overlays, credential-scoped
filtering -- this project does not need yet, since Minion has no config-driven provider catalog of
its own.

`models()`'s own RETURN order is not part of the observable contract -- any implementation may
return currently-resolvable identities in any order it finds convenient, deterministic or not, and
no caller may depend on a specific order. This is deliberate: nothing about `models()`'s own
purpose (introspection) makes a particular order semantically meaningful. The CANONICAL EVIDENCE
FORMAT is narrower, for tooling reasons only: an `introspect: models` query's own observation, once
collected by a conformance runner in ANY language, MUST be reported sorted by `(provider, model,
api)` before comparison against a scenario's own `expect.models` list -- this is the ONE shared,
required canonicalization step every conformance runner performs, precisely so that two runners
producing the SAME underlying set in DIFFERENT raw orders still compare equal against the SAME
`expect.models` list (`L10-C001`, an independent Rust closure review's own finding: a prior Rust
conformance runner reported `models()`'s own raw return order directly, sorted internally by
`(provider, api, model)` -- a DIFFERENT key from the one every current canonical scenario's own
`expect.models` list is written against -- which the seven current scenarios never exposed only
because none happens to declare more than one entry whose `api`/`model` cross under the two keys).

Current Rust only PARTIALLY satisfies this row: `LlmService::register` takes one
`(ModelIdentity, Arc<dyn LlmAdapter>)` pair per call (not an adapter-declared model set) and
performs last-write replacement via a plain map insert, correctly satisfying the replacement half;
it has NO withdrawal handle, NO stale-withdrawal protection, and NO `models()` introspection at
all. Those are OPEN, disclosed gaps -- whether and how a future Rust implementation pass closes
them is that pass's own decision, not asserted here.

**`fetchDeferred`/`cancelDeferred` (`AI-032`, deferred parity).** Pi-required-when-present,
capability-gated, per-wire-protocol-module operations -- the SAME status class as `streamSimple`
(`AI-031`): nothing generic to specify at Layer 10's own provider-agnostic abstraction level until a
real provider (Layer 11) exists to implement one. Pinned Pi keeps FOUR distinct observable layers
separate, and a future Layer-11 implementation must preserve all four, not collapse them:

1. Low-level, per-API-module (`types.ts::ProviderStreams.fetchDeferred?`/`cancelDeferred?`):
`fetchDeferred`, when present, returns a NEW `AssistantMessageEventStream` (the SAME never-raises
boundary `stream` already has, `AI-012`). `cancelDeferred`, when present, returns `Promise<void>` --
not stream-shaped at all.

2. High-level, caller-facing (`models.ts::ModelsImpl.fetchDeferred`/`cancelDeferred`): NOT
symmetric. `fetchDeferred` wraps provider lookup, capability lookup, auth, and delegation ENTIRELY
inside `lazyStream(...).result()` -- an unknown provider, a missing capability, or a delegated
failure all settle as a REPRESENTED (resolved, in-band) `AssistantMessage` with an error
`stopReason`, never a rejected promise. `cancelDeferred` performs the SAME provider/capability
lookup EAGERLY, outside any `lazyStream` wrapper -- an unknown provider or a missing capability
THROWS (a rejected promise), not a represented error. This is a genuine, deliberate ASYMMETRY
between the two operations at the high-level boundary, not an oversight to smooth over.

3. Provider-level, mixed-API capability selection (`models.ts::createProvider`): a provider built
from an api-map synthesizes `provider.fetchDeferred`/`cancelDeferred` only if AT LEAST ONE api entry
supports it -- but a caller may still pick a model whose OWN specific api entry lacks it. That
per-model mismatch inherits the IDENTICAL fetch-vs-cancel asymmetry as (2): the synthesized
`fetchDeferred` wraps its own capability check in `lazyStream` (in-band settlement); the synthesized
`cancelDeferred` is a plain function with a direct throw for the same mismatch (eager rejection).

4. Reference (faux/mock) implementation's own concrete unknown/cancelled-handle behavior
(`providers/faux.ts`): for a SUPPORTED capability, an unknown or already-cancelled `DeferredHandle`
is NOT the same case as (2)/(3)'s missing-provider/missing-capability case above -- `fetchDeferred`'s
own unknown/cancelled-handle failure settles as an in-band error event on the returned stream (never
throwing out of `fetchDeferred` itself); `cancelDeferred`'s own unknown handle is a SILENT NO-OP --
not an error, not a throw. This "best-effort, idempotent for unknown handles" behavior applies ONLY
to a supported capability's own handle-resolution outcome, not to a missing provider/capability at
all -- conflating the two would let cancel appear "always idempotent" when in fact only its
handle-resolution failure mode is.

Disposition: `deferred parity`, not `adopted` and not silently omitted. Minion's own generic
`Adapter` protocol at Layer 10 maps only to `stream` (`AI-028`); `fetchDeferred`/`cancelDeferred`
have no Layer-10 surface of their own to build yet -- Minion has no `fetch_deferred`/
`cancel_deferred` method anywhere (`Adapter`/`LlmService`), and this section does not propose adding
speculative plumbing for an operation with no Layer-11 provider to exercise it. Both operations
still build on `AI-009`'s own already-certified `DeferredHandle` vocabulary -- this is a NEW section
for the BEHAVIOR these two operations require, not a change to `AI-009` itself.

Closure criterion, binding on whichever future pass closes this row: a future Layer-11
implementation must expose an externally invocable operation preserving ALL FOUR distinctions above
-- it must NOT make `cancel_deferred` globally never-raising (collapsing (2) into (1)'s shape), and
it must NOT make `fetch_deferred` throw eagerly on a missing/unsupported capability (collapsing (2)
into (3)'s cancel-side behavior). Executable provider witnesses remain deferred to Layer 11 (Layer
10 has no concrete wire-protocol implementation to test against); this section commits only to the
observable closure criteria stated here. A future revision marked "complete" by satisfying only some
of the four layers, or by building internal translation code with no caller-facing entry point,
would not satisfy this row; it must be re-opened, not silently accepted.

`ModelId.api` currently defaults to `"mock"` in Python's own type -- a PYTHON-SPECIFIC temporary
compromise (`LLM-F006`, Layer 02), correct for every caller today since the mock adapter is the
sole registered adapter, not a cross-language Minion contract this section mandates: certified Rust
already requires an explicit, strict three-part `ModelIdentity` with no equivalent default, and
that stricter shape -- not Python's own temporary convenience -- is Layer 10's own actual
normative target. Python's default becomes actively wrong once a second API exists (Layer 11) and
must be removed then, so every caller must say which API it means; this is a disclosed, tracked
Python-side follow-up, not something Rust needs to match.
