# Minion Agent — Phase 5: Real Providers

**Date:** 2026-08-20
**Status:** Frozen for implementation. Reviewed section-by-section; see §7 for the decision log.
**Builds on:** `2026-08-18-minion-agent-design.md` (frozen master design), §4 (the LLM seam) in
particular. Where this document and the master design disagree, the master design wins; this
document only elaborates §4 for two concrete APIs.

Phases 1–4 produced a correct agent driven entirely by a mock adapter. This phase makes first
contact with real models: `openai-completions` (OpenRouter, Ollama, LM Studio, generic
OpenAI-compatible endpoints) and `codex-responses` (OpenAI Codex, OAuth-authenticated). Real
providers are the first place this codebase crosses a live network boundary, so this document is
more operational than the master design — it pins wire formats, retry semantics, and an OAuth
credential-ownership model that the master design's §4 states as a seam but does not elaborate.

---

## 1. Scope

**In scope:** two adapters (`openai_completions`, `codex_responses`), the shared HTTP/SSE
transport and retry policy they use, the Codex OAuth credential seam with three loader mechanisms
(CLI-credential read, interactive PKCE login, device-code login), and the wire-fixture testing
architecture that lets both adapters be tested deterministically without live network access.

**Out of scope, deferred:**

- Per-model cost computation (`Usage`'s cost field). Needs a pricing-table source that is
  genuinely open-ended for OpenRouter's model catalog; explicit follow-up.
- OS-keyring credential storage for Codex (`cli_auth_credentials_store: keyring`). File-mode
  interop only for V1.
- Live mid-stream cancellation (`AgentLoop` interrupting an in-flight provider request). The
  current agent loop's cancellation is cooperative, checked between steps — nothing today closes
  a live stream mid-flight. The `aborted` stop reason and its stream semantics remain fully
  intact; only the *mechanism* to trigger it live is deferred, until the loop itself gains
  interrupt-based cancellation and the two can be designed together (loop → request handle →
  transport → stream settlement, one coherent feature, not half of it slipped in here).
- Reasoning *summary* events and `encrypted_content` continuation blobs from the Responses API.
  Recognized, never corrupt mapped state, but have no V1 provider-neutral projection.

---

## 2. Vocabulary & wire mapping

Both adapters translate in two directions — our vocabulary → wire format (encode) and wire
events → `StreamChunk` (decode) — as pure functions with no I/O, independently testable from any
transport.

The two APIs are genuinely different wire protocols (`openai-completions` is OpenAI's older Chat
Completions shape; `codex-responses` is the newer, event-oriented Responses API) and share almost
nothing at the wire level, including how tool results encode. They remain **two independent
adapters**, not one format-parameterized abstraction — unifying them would be premature
generalization against a difference that is real, not incidental.

### 2.1 `openai-completions`

**Encode — role-aware, not mechanical.** The encoder validates which `ContentBlock` types are
legal for a given message role rather than converting every block into every role indiscriminately
(e.g. images are a user-input concern).

| Semantic | Wire |
|---|---|
| `UserMessage` | `role: user` |
| `AssistantMessage` | `role: assistant` |
| `ToolResultMessage` | `role: tool`, `tool_call_id` set explicitly |
| `TextBlock` | text content part |
| `ImageBlock` (inline `data`) | base64 data URL |
| `ImageBlock` (`reference`) | the reference is an immutable content-addressed identity, never a mutable URL. If the wire format needs a URL, materializing the artifact into a provider-fetchable one is a transport concern producing a *wire representation* — the semantic reference itself is never rewritten as though the URL were the source of truth. |
| `ThinkingBlock` | **explicit unsupported-content error on encode.** `thinking` is frozen provider-neutral vocabulary; a request that silently loses content between "semantic" and "dispatched" is exactly the kind of drift the log-reconstruction invariant (master design §8) exists to catch. No silent drop. |
| `ToolSchema` | OpenAI function-tool shape (`{type:"function", function:{name, description, parameters}}`). `strict` mode is provider config, not part of the common schema. |

**Decode:**

- `delta.content` → `TextDelta`.
- `delta.tool_calls[index]` → accumulated **per array index**, independently for `id`,
  `function.name`, and `function.arguments` fragments — fields do not all arrive on the same
  delta. Finalized only when the stream indicates completion.
- `finish_reason`: `stop→stop`, `length→length`, `tool_calls→tool_use`. An **unknown** finish
  reason is preserved diagnostically, never silently coerced to `stop`.

### 2.2 `codex-responses`

**Decode is an item-state machine keyed by `item_id`**, with `output_index`/`content_index` for
ordering — not independent per-event handlers. `response.output_text.delta/done`,
`response.reasoning_text.delta/done`, and `response.function_call_arguments.delta/done` all stream
incrementally, accumulating the same way Chat Completions tool-calls do, just keyed differently.
`response.output_item.done` finalizes an item.

| Semantic | Wire |
|---|---|
| `ToolResultMessage` | `function_call_output(call_id, output)` — Responses has no `role: tool` shape at all, confirming message encoding cannot be shared between the two adapters even generically. |
| `response.output_text.delta/done` | `TextDelta` / finalized text |
| `response.reasoning_text.delta/done` | `ThinkingDelta` / finalized `ThinkingBlock` |
| `response.function_call_arguments.delta/done` | per-`item_id` argument accumulator → finalized tool call |
| reasoning *summary* events | **not modeled in V1** — recognized and discarded, never merged into `ThinkingBlock`, never corrupts `reasoning_text` accumulation for the same item |
| `encrypted_content` | **not modeled in V1** — same treatment: recognized, opaque, never mutates mapped semantic state |

**Stop reason comes from response-level completion state**, not the last content event —
`completed`/`incomplete`/`cancelled`/`failed` are Responses' own outcome states:

- `completed`, no pending tool call requiring execution → `stop`
- `completed`, with a finalized function call requiring execution → `tool_use`
- `incomplete` → `length`
- `cancelled` → `aborted`
- `failed` → `error`

---

## 3. Transport, retry, and the never-raises boundary

### 3.1 Where the boundary actually lives

`llm/service.py`'s `_settled()` — added in Plan 2 — already wraps every adapter's raw stream at
the `LlmService.stream()` call site: it synthesizes a terminal on premature clean EOF (preserving
`partial`, `stop_reason=ERROR`) and enforces first-terminal-wins fusion. This **is** the public
never-raises boundary; it is not duplicated per adapter.

It has exactly one gap for real adapters, closed by this phase: it only catches clean EOF (the
raw generator's `async for` completing without a terminal). It does not catch an exception raised
*during* iteration — which the mock adapter structurally cannot produce (pure Python, no I/O) but
real adapters will (a dropped connection, malformed JSON).

**New vocabulary**, in `llm/errors.py`, distinct from the existing `AdapterProtocolError` (which
means the opposite — "the adapter violated the contract, this is a bug, let it raise"):

```python
class AdapterOperationalError(LlmError):
    """A represented failure in a real provider adapter — network, protocol,
    or retry-exhaustion failure. Adapters raise this for conditions the
    never-raises contract requires settling in-band; `_settled()` converts it
    to a terminal `StreamError`. Anything else an adapter's raw generator
    raises is a genuine bug and must propagate — `_settled()` catches this
    type only, never a bare `Exception`."""
```

`_settled()`'s `async for` loop is wrapped in `except AdapterOperationalError`, nothing broader.
A `TypeError` from an actual decoder bug still raises straight through, visibly — exactly the
"programming errors remain exceptions" half of the master design's boundary table, preserved.
Adapters never let a raw `httpx` exception escape their own code; `llm/service.py` never learns
`httpx` exists.

### 3.2 Retry commitment boundary

> A provider attempt may be retried only while it has yielded **zero** public `StreamChunk`s. The
> first yielded chunk of any kind — including `StreamStart` — commits the attempt. Thereafter no
> transparent retry occurs.

This is stricter than "no retry after semantic content" and deliberately so: if a retried attempt
had already yielded `StreamStart`, a fresh attempt would need to either yield a second
`StreamStart` (undefined for consumers) or invent cross-attempt continuity for `content_index`,
tool-call indices, item identity, and partial-message state that all belong to one physical
provider response. Cutting off before *any* yield makes a retried attempt genuinely invisible —
nothing was ever handed to the consumer from the failed one.

Retry additionally requires a **failure-class gate**, not just the timing gate:

- **Retryable:** connection establishment failure, connection reset, timeout, HTTP 429, retryable
  5xx (per provider policy — not "all 5xx forever" as an architectural constant).
- **Never retryable, regardless of timing:** malformed JSON, malformed SSE semantics, an
  impossible provider event sequence, invalid tool-call state — these are protocol/adapter
  failures, not transient transport conditions, and could in principle occur before the first
  chunk (e.g. `HTTP 200` followed immediately by malformed JSON). The retry predicate is
  `no chunk yielded AND failure classified as transient transport/status`, both conditions
  required.

A keepalive, comment, or provider-bookkeeping SSE frame that produces no `StreamChunk` does not
end retry eligibility — the adapter consumes it while still inside the retryable phase.

Backoff: exponential with jitter, honoring `Retry-After` on 429, bounded attempt count (default 3,
config-overridable). When retries exhaust, the adapter raises `AdapterOperationalError` — it does
not synthesize a `StreamChunk` itself; `_settled()` does that centrally.

### 3.3 SSE framing

One shared, wire-format-agnostic utility (`transport/sse.py`). It knows only:

```
bytes → SSE framing → SseEvent(event: str | None, data: str)
```

It knows nothing about `StreamChunk`, `StopReason`, tool calls, thinking, or `[DONE]` — that last
one is a **Chat Completions decoder concern**, not an SSE-parser concern; the parser just yields
`data == "[DONE]"` as an ordinary event.

Contract: LF and CRLF line endings; blank-line event termination; multiple `data:` lines in one
event joined with `\n`; optional `event:` field; `:`-prefixed comment/keepalive lines ignored;
buffering across arbitrary network chunk boundaries; EOF with an unterminated buffered event
handled explicitly. `id:`/`retry:` fields are ignored in V1, deliberately, not by omission.

### 3.4 Transport module split

`transport/http.py` (httpx request/response lifecycle), `transport/retry.py` (classification,
backoff, `Retry-After`), `transport/sse.py` (byte framing only) — three independently testable
responsibilities, not one growing `transport.py`.

### 3.5 Cancellation

Two cases, deliberately distinguished:

- **Consumer closes the stream** (`GeneratorExit` from `.aclose()`/an early `break`): the raw HTTP
  request runs inside `async with client.stream(...) as response:`, so closing the generator
  releases the connection cleanly. No synthetic terminal chunk — nobody is listening for one.
- **Live mid-stream interruption**: out of scope for this phase (§1). `StopReason.ABORTED` and the
  stream's ability to represent an aborted terminal are unchanged and fully intact; this phase
  adds no new mechanism that *triggers* it, because nothing in the current agent loop can.

### 3.6 Retry testing

Deterministic — no real wall-clock sleeps. The backoff delay function is injected/abstracted so
tests assert exact attempt counts and backoff decisions against a fake clock, the same pattern
Plan 4's conformance suite already uses (`delay_ticks` as `asyncio.sleep(0)` scheduler yields, not
real time).

---

## 4. The Codex OAuth auth seam

### 4.1 Three roles, not one "loader"

```python
class CodexCredentialSource(Protocol):
    async def load(self) -> CodexCredentials: ...

class CodexLoginFlow(Protocol):
    async def login(self) -> CodexCredentials: ...

class CodexCredentialStore(Protocol):
    async def load(self) -> CodexCredentials | None: ...
    async def save(self, creds: CodexCredentials) -> None: ...
    async def clear(self) -> None: ...
```

- **`CodexCliCredentialSource`** — reads `~/.codex/auth.json` (`$CODEX_HOME/auth.json`),
  read-only. Schema follows `AuthDotJson` in `openai/codex`'s own source
  (`codex-rs/login/src/token_data.rs`, `codex-rs/login/src/auth/manager.rs` — real, open-source,
  confirmed by inspection), file-mode storage only (`cli_auth_credentials_store: file`, the
  default; `keyring`/`auto`/`ephemeral` deferred, §1). Parsing is tolerant: extracts only the
  token material this seam needs, ignores unrecognized fields, and is verified against
  representative real credentials at implementation time. If Codex is configured for a backend
  this reader can't parse (e.g. keyring), the diagnostic is **"Codex credentials exist in an
  unsupported backend,"** distinct from **"not logged in"** — different situations, different
  messages.
- **`PkceLoginFlow`**, **`DeviceCodeLoginFlow`** — produce fresh credentials; neither touches
  external storage. Endpoints (`AUTH_BASE_URL`, `TOKEN_URL`, device-code endpoints, `CLIENT_ID`,
  `SCOPE`, the `:1455` loopback callback port) are seeded from pi's known-working implementation
  as a starting reference, then verified against current OpenAI/Codex behavior at implementation
  time — not assumed correct by analogy. The callback port is an implementation detail of
  `PkceLoginFlow`, pinned for protocol compatibility, not part of what `CodexLoginFlow` means as an
  abstraction.
- **`MinionCredentialStore`** — the only writable implementation. `0o600` permissions on Unix,
  matching Codex's own posture; equivalent non-world-readable protection on Windows.

### 4.2 The ownership rule

> **Credential ownership follows persistence ownership.** A credential read from `~/.codex/auth.json`
> remains Codex's. Minion Agent may use a currently-valid access token from it, but never
> independently refreshes it and never writes back to that file — refreshing mutates remote OAuth
> state (rotating refresh tokens), and only the owning application may safely do that. Credentials
> Minion Agent's own login flows produce are Minion-owned end to end: Minion refreshes them and
> atomically persists every replacement to `MinionCredentialStore`.

Concretely: refresh is **not** a bare function applicable to any `CodexCredentials` value
regardless of where it came from. It is a capability that operates only on
`MinionCredentialStore`-owned credentials — one shared OAuth token-refresh implementation, since
`PkceLoginFlow` and `DeviceCodeLoginFlow` have no reason to duplicate that HTTP call between them —
and it is never applied to a `CodexCliCredentialSource` result.

If `cli-credentials` mode holds an expired access token with no independently-refreshable path
(because Minion doesn't own that refresh), the diagnostic is explicit —
external-auth-required/Codex-refresh-required — not a silent failure or an unauthorized refresh
attempt.

### 4.3 Config

```python
auth_method: Literal["cli-credentials", "interactive", "device-code"] = "cli-credentials"
```

No fallback chain — matching the same explicit-selection principle §5 uses for provider
authentication generally. `cli-credentials` and no usable external credential exists → fail
clearly; it does not silently launch a browser login.

---

## 5. Config, provider plugins, and file structure

### 5.1 Provider plugins

Follows the established pydantic-config pattern (`mock_adapter_plugin`, Plan 2). One
`openai_completions_plugin` takes `base_url: str`, `api_key: str | None`, `models: list[str]`,
`headers: dict[str, str] = {}`. `codex_plugin` takes the `auth_method` above and composes the
§4 roles internally.

**Provider authentication is explicit — no discovery chain.**

> Provider authentication values come from the provider plugin's resolved configuration. Minion
> Agent does not implement a second, provider-specific API-key discovery or fallback order in V1.
> A configuration framework may populate those fields from environment variables or another
> application-level source — that is config loading, not provider authentication policy. If a
> future application wants environment variables, a vault, an OS keyring, or a secrets manager, it
> constructs the same provider config without the adapter changing.

**Presets are configuration, not adapter identity.**

> OpenRouter, Ollama, LM Studio, and generic OpenAI-compatible endpoints use the same
> `openai-completions` adapter unless their wire semantics materially diverge. Presets
> (`OpenAICompletionsConfig.openrouter(...)`, `.ollama(...)`, `.lm_studio(...)`) are documented
> config conveniences. The adapter never infers provider identity by sniffing `base_url` — no
> `if "openrouter.ai" in base_url` branching. If a provider genuinely needs different wire
> behavior, that becomes explicit config/capability, not URL detection.

**Secrets stay out of diagnostics.** `api_key` and `headers` (which may itself carry
`Authorization`/`X-API-Key`) are both treated as sensitive — neither may leak through model dumps,
exception strings, or debug telemetry. Ties directly into the existing telemetry sanitize
boundary (master design §7).

**`models: list[str]` stays a plain list for V1** — the immediate need is registration/membership,
matching the existing `Adapter.models: frozenset[str]` protocol field. Nothing in this phase
assumes model identity is *forever* a bare string; the registration boundary is free to grow model
metadata (pricing, context window, capabilities) later without this phase inventing a
`ModelDescriptor` it doesn't yet need.

### 5.2 File structure

```
llm/
  adapters/
    openai_completions/
      __init__.py
      codec.py        # encode_request(), decode: TextDelta/tool-call accumulator/finish_reason
      adapter.py       # Adapter impl; transport/retry orchestration
    codex_responses/
      __init__.py
      codec.py         # encode_request(), the item_id-keyed decode state machine
      adapter.py        # Adapter impl; transport/auth/retry orchestration
    transport/
      __init__.py
      http.py          # httpx request/response lifecycle
      retry.py         # classification, backoff, Retry-After
      sse.py           # bytes -> SseEvent, wire-format-agnostic
    codex_auth/
      __init__.py
      source.py        # CodexCredentialSource, CodexCliCredentialSource
      login.py         # CodexLoginFlow, PkceLoginFlow, DeviceCodeLoginFlow
      store.py         # CodexCredentialStore, MinionCredentialStore
  errors.py             # + AdapterOperationalError
  service.py            # _settled() gains `except AdapterOperationalError`
```

Each real adapter splits `codec.py` (pure, no I/O — the encode/decode/state-machine logic) from
`adapter.py` (the `Adapter` protocol implementation, orchestrating transport/retry/SSE
consumption). This split is locked upfront rather than left to grow organically, because §2
already demonstrates enough pure-translation complexity — a tool-call accumulator for Chat
Completions, an item-state machine for Responses — to justify it from the first commit; letting
transport orchestration and pure codec logic intertwine in one module would need undoing later.

---

## 6. Testing & fixture architecture

Three layers, all exercising the **same production code** — no layer invents its own encode/decode
logic:

1. **Pure codec tests** — hand-authored edge cases, no I/O. Exhaustive by construction.
2. **Recorded wire fixtures** — real captures from real providers, sanitized, replayed through a
   deterministic test transport into the real `adapter.py` code. Realism a hand-authored fixture
   can't provide (actual SSE framing, omitted-vs-null fields, real event ordering).
3. **Optional live verification** — manual, credentialed, non-gating. Used to refresh fixtures or
   detect provider drift, never required for the automated suite.

**Deliberately kept distinct**, despite all sharing the word "replay": the existing
`mock/scripted` provider (deterministic semantic model behavior, described directly by
tests/conformance), a possible future `mock/replay` (replaying recorded *semantic* sessions), and
provider wire fixtures (replaying captured HTTP/SSE *protocol* material). Collapsing these because
they're all "replay" would blur what each one actually verifies.

**Recorded fixtures preserve raw wire structure**, not just parsed logical events — line endings,
multi-line `data:` framing, blank-line termination, comments/keepalives, chunk boundaries where
relevant. A fixture that stores only `{"event": "...", "data": "..."}` bypasses the SSE parser
entirely and tests the decoder alone; a *wire* fixture and a *decoder* fixture are both useful, but
only the raw one exercises the framing layer.

**Sanitization removes secrets, not protocol structure.** Strip `Authorization`, cookies, tokens,
account identifiers, irrelevant timestamps/IDs, signed URLs. Do **not** normalize away tool-call
index, `item_id` relationships, `output_index`/`content_index`, `finish_reason`, response status,
or event ordering — those are exactly what the fixture exists to test. Where an ID must remain
internally consistent for event correlation, replace it deterministically (`resp_abc123` →
`resp_fixture_1`) and rewrite every reference to match, rather than deleting it.

**Fixture provenance is recorded** (provider, API family, model, capture date, capture
tool/version, sanitizer version, purpose) — a sidecar manifest, not embedded in the wire payload.
Provider APIs drift; provenance is what lets a later failure be diagnosed as "adapter regression"
versus "provider changed since this was captured," instead of guessed at.

**Provider wire fixtures are implementation-level, not shared cross-language conformance.** The
master design's three conformance families (`runtime/`, `agent/`, `session/`) stay semantic and
language-neutral. Raw OpenAI/OpenRouter/Codex wire payloads are Python-adapter-specific (a Rust
implementation will have its own HTTP client, its own equivalent fixtures) and do not belong in
the shared suite merely because both implementations eventually talk to similar APIs. If Python and
Rust later deliberately want a shared wire-fixture corpus, that is an explicit decision to make
then, not an automatic consequence of this phase.

### 6.1 Fixture matrix

**`openai-completions`** — encode (role-aware messages, `ToolResultMessage`→`role:tool`+
`tool_call_id`, inline-image→data-URL, illegal role/block combinations rejected,
`ThinkingBlock`→unsupported error *(encoder-only test — nothing to record; the adapter must reject
before a request is ever sent)*, `ToolSchema`→function shape); decode (simple text; one tool call
with fragmented id/name/arguments; multiple interleaved parallel tool calls;
`stop`/`length`/`tool_calls`; unknown finish reason preserved; malformed JSON; `[DONE]`; premature
EOF); transport (keepalive before first chunk → still retryable; `StreamStart` yielded then
failure → retry forbidden).

**`codex-responses`** — encode (`function_call_output(call_id, output)` round-trip; only
explicitly-modeled reasoning input, if any); decode (`output_text`/`reasoning_text`/
`function_call_arguments` delta+done; `output_item.done` finalization; multiple interleaved
`item_id` values; `output_index`/`content_index` ordering; `completed`+no-tool-call→`stop`;
`completed`+finalized-tool-call→`tool_use`; `incomplete`→`length`; `cancelled`→`aborted`;
`failed`→`error`; reasoning-summary and `encrypted_content` events recognized but produce no
`ThinkingBlock` and do not corrupt `reasoning_text` accumulation for the same item).

Recorded fixtures prioritize realism per materially-different shape (simple text, one tool call,
parallel tool calls, each response-level terminal state where practically obtainable) over forcing
every synthetic edge case into a live recording — the harder correctness cases above belong in
pure codec tests, not the recorded set.

---

## 7. Decision log

Recorded during section-by-section review, each correcting an earlier draft of this document:

1. **`ThinkingBlock` on Chat Completions encode is an explicit error, not a silent drop.** An
   initial draft dropped it silently; `thinking` is frozen provider-neutral vocabulary, and a
   request that loses content between semantic and dispatched forms violates the spirit of
   log-reconstruction even before logging is involved.
2. **Responses function calls stream incrementally too**, via `function_call_arguments.delta`,
   not only as complete `function_call` output items as an initial draft assumed — confirmed
   against the real Responses streaming event set.
3. **Responses reasoning is a structured mapping, not a blind funnel.** `reasoning_text` maps to
   `ThinkingBlock`; reasoning *summary* and `encrypted_content` are recognized-but-unmodeled in
   V1, not merged indiscriminately into one undifferentiated block.
4. **`codex-responses`'s `completed` state is not automatically `stop`.** A completed response
   carrying a finalized function call requiring execution is `tool_use`; only a completed response
   with no pending tool call is `stop`. Preserves the provider-neutral distinction between handing
   control back with text versus handing control to tools.
5. **The never-raises boundary already exists** (`_settled()` in `llm/service.py`, Plan 2) and is
   not duplicated per adapter — it needs exactly one extension (catching
   `AdapterOperationalError`, a new, narrowly-scoped type, not a bare `Exception`) rather than a
   new `AssistantStream` class as an initial draft proposed.
6. **Retry commitment boundary is before the first yielded chunk of any kind**, including
   `StreamStart` — tighter than an initial "first semantic content" framing, because retrying
   after `StreamStart` had already been yielded would require either a second `StreamStart`
   (undefined) or inventing cross-attempt continuity for state that belongs to one physical
   response.
7. **Retry requires two independent gates**: no chunk yet yielded, *and* the failure is classified
   as transient transport/status. Malformed protocol data is never retryable regardless of timing.
8. **Live mid-stream cancellation is deferred**, not built ahead of a caller. The current agent
   loop's cancellation is cooperative and checked only between steps; nothing today closes a
   stream mid-flight. Building the interrupt mechanism now, unused, is exactly the kind of
   anticipatory subsystem the project avoids. The `aborted` vocabulary is unweakened and stays
   ready for when the loop gains real interrupt capability.
9. **Codex credential ownership follows persistence ownership.** An initial draft had Minion
   independently refresh CLI-sourced credentials (attractive because refresh looks
   provenance-independent) — corrected because refresh mutates remote OAuth state via rotating
   refresh tokens, and only the owning application (the actual `codex` CLI) may safely do that.
   Minion never writes to `~/.codex/auth.json`; it never refreshes credentials read from it either.
10. **"Loader" was conflating three responsibilities** (reading existing credentials, running a
    login flow, persisting results) that needed separating: `CodexCredentialSource`,
    `CodexLoginFlow`, `CodexCredentialStore`.
11. **The `~/.codex/auth.json` schema is not unknowable** — `openai/codex`'s own open-source Rust
    implementation defines `AuthDotJson` (`codex-rs/login/src/token_data.rs`,
    `codex-rs/login/src/auth/manager.rs`), confirmed by inspection. The CLI-compatibility reader
    follows that schema, tolerantly, rather than reverse-engineering one empirically from a single
    captured file.
12. **API-key resolution stays flatly explicit for V1** — config carries the key directly, no
    provider-specific discovery/fallback chain — mirroring the same explicit-selection choice §4
    makes for `auth_method`, applied consistently to ordinary provider auth as well.
13. **Provider presets never sniff `base_url`.** OpenRouter/Ollama/LM Studio identity comes from
    which config constructor was called, never from inspecting the configured URL — avoids a
    brittle, implicit behavioral branch.
14. **`transport.py` and each adapter split into packages upfront**, not left to grow organically —
    §2's pure-translation complexity (a tool-call accumulator, an item-state machine) already
    justifies separating codec from orchestration and HTTP from retry from SSE framing before any
    code exists, rather than un-intertwining them later.
