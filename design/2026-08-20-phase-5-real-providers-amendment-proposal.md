# Proposed amendment to §4 — Real providers

**Date:** 2026-08-20
**Status:** PROPOSED. Not merged into `2026-08-18-minion-agent-design.md`. Not frozen. Pending the
same review this project applies to cross-language design changes (Rust-side + design reviewer) —
see the precedent of `840d414`, which promoted language-neutral rules into the master design after
review, the pattern this proposal follows.
**Target:** `2026-08-18-minion-agent-design.md`, §4 "The LLM seam." §4 currently states the
never-raises contract, the API/provider split table, and the auth-seam principle at a level that
doesn't yet commit to how two concrete APIs (`openai-completions`, `codex-responses`) actually
satisfy them. This proposal is that elaboration — normative content a Rust implementation is
equally bound by, not implementation detail.

**Scope note:** this document intentionally excludes everything that is Python-specific
implementation (file layout, concrete config classes, references to existing Python functions).
That material belongs in a `plans/python/` implementation plan once this proposal is settled, not
in `design/`.

---

## Proposed addition to §4: wire vocabulary mapping

Real adapters translate in two directions — provider-neutral vocabulary → wire format (encode),
wire events → `StreamChunk` (decode) — as pure, I/O-free translations. `openai-completions` and
`codex-responses` are genuinely different wire protocols (older Chat Completions shape vs. a newer
event-oriented Responses shape) sharing almost nothing at the wire level, including how tool
results encode — this is a property of the two real APIs, not a Python implementation choice, and
any implementation should treat them as two independent translations rather than one
format-parameterized abstraction.

### `openai-completions`

Encoding is **role-aware**: which `ContentBlock` types are legal is validated per message role,
not mechanically converted regardless of role.

| Semantic | Wire |
|---|---|
| `UserMessage` | `role: user` |
| `AssistantMessage` | `role: assistant` |
| `ToolResultMessage` | `role: tool`, explicit `tool_call_id` |
| `TextBlock` | text content part |
| `ImageBlock` (inline `data`) | base64 data URL |
| `ImageBlock` (`reference`) | The reference is an immutable content-addressed identity (§5). If the wire format needs a URL, materializing the artifact into a provider-fetchable one produces a *wire representation* only — the semantic reference is never rewritten as though a mutable URL were the source of truth. |
| `ThinkingBlock` | **Explicit unsupported-content error on encode, never a silent drop.** `thinking` is frozen provider-neutral vocabulary (§4); silently losing it between the semantic request and what's dispatched is exactly the drift §8's log-reconstruction invariant exists to catch. |
| `ToolSchema` | OpenAI function-tool shape. `strict` mode is provider-specific, not part of the common schema. |

Decode: `delta.tool_calls[index]` accumulates per array index — `id`, `function.name`, and
`function.arguments` fragments arrive independently, not necessarily together, finalized only when
the stream signals completion. `finish_reason` maps `stop→stop`, `length→length`,
`tool_calls→tool_use`; an **unknown** finish reason is preserved diagnostically, never silently
coerced to `stop`.

### `codex-responses`

Decode is an **item-state machine keyed by `item_id`** (with `output_index`/`content_index` for
ordering), not independent per-event handlers — `output_text`, `reasoning_text`, and
`function_call_arguments` all stream incrementally and accumulate the same way, just keyed
differently; `output_item.done` finalizes an item.

`ToolResultMessage` encodes to `function_call_output(call_id, output)` — Responses has no
`role: tool` shape at all, which is itself evidence the two adapters cannot share even a generic
message encoder.

Reasoning: `reasoning_text.delta/done` maps to `ThinkingDelta`/`ThinkingBlock`. Reasoning
**summary** events and `encrypted_content` continuation blobs are recognized but have **no V1
projection** — not merged into `ThinkingBlock`, not allowed to corrupt `reasoning_text`
accumulation for the same item. If a later phase needs multi-turn reasoning continuation, that is
a vocabulary extension to propose then, not something to retrofit into `ThinkingBlock` now.

Stop reason comes from **response-level completion state**, not the last content event:

- `completed`, no pending tool call requiring execution → `stop`
- `completed`, with a finalized function call requiring execution → `tool_use`
- `incomplete` → `length`
- `cancelled` → `aborted`
- `failed` → `error`

The `completed→stop` vs. `completed→tool_use` split preserves the provider-neutral distinction
between a response that hands control back with text and one that hands control to tools — losing
it would mean an implementation cannot tell those apart from `StopReason` alone.

---

## Proposed addition to §4: the never-raises boundary applied to real providers

§4 already states the never-raises boundary as a two-phase table (raise before a stream is
returned; nothing escapes iteration after). This proposal pins how retry composes with it, since a
real adapter retries transiently-failed requests and the composition is not obvious from the
existing table alone.

> **Retry commitment boundary.** A provider attempt may be retried only while it has produced zero
> public `StreamChunk`s. The first yielded chunk of any kind — including a stream-start chunk —
> commits the attempt; no transparent retry occurs after it. Retrying past that point would require
> either yielding a second stream-start (undefined for consumers) or inventing continuity across two
> unrelated provider responses for state that belongs to one — content indices, tool-call indices,
> item identity, partial-message state. Cutting off before any output makes a retried attempt
> genuinely invisible to the consumer.
>
> Retry additionally requires the failure to be **classified as transient transport/status
> failure** — connection failure, timeout, rate limiting, retryable server error. Protocol or
> semantic failures (malformed data, an impossible event sequence) are never retryable regardless
> of timing, because they are not evidence the same request would succeed on a second attempt.
>
> **Both conditions are required — timing alone is not sufficient.** A malformed provider event
> in principle can occur before the first chunk (e.g. a `200` response immediately followed by
> invalid JSON); that failure is still never retried, because it fails the failure-class gate.
>
> Retry exhaustion is itself an ordinary post-return failure: it settles the stream in-band, per
> the existing never-raises table. It does not raise.

**Live mid-stream cancellation is out of scope for this proposal.** It requires the agent loop
itself to gain an interrupt capability it does not currently have (§6's loop is cooperative,
checked between steps) — designing the transport half of cancellation ahead of the loop half would
solve a problem in isolation that needs to be solved as one cross-layer feature. The existing
`aborted` stop-reason semantics are unaffected and remain ready for whenever that capability
exists.

---

## Proposed addition to §4: authentication ownership

§4's Authentication subsection states the seam ("auth is a seam, not a file path") and names the
Codex CLI credential file as the first loader, chosen for immediate compatibility with existing
Codex CLI users. It does not yet state what happens when that external credential expires — this
proposal closes that gap with a rule that is genuinely normative (any implementation reading
another application's credential store is bound by it, not a Python-specific concern):

> **Credential ownership follows persistence ownership.** A credential read from another
> application's credential store remains owned by that application. An implementation may use a
> currently-valid access token from it, but never independently refreshes it and never writes back
> to that store — refreshing mutates remote OAuth state (rotating refresh tokens), and only the
> owning application can safely do that without risking the *other* application's next use of its
> own credential. Credentials an implementation's own login flow produces are owned by it end to
> end: it refreshes them and persists every replacement to its own storage.
>
> This means "read an external credential" and "refresh a credential" are not the same capability
> applicable uniformly to any credential value — refresh applies only to self-owned credentials. If
> a mode that depends on an external credential holds one that has expired with no
> independently-refreshable path, the failure is diagnosed explicitly as such (distinct from "not
> authenticated at all"), not silently attempted anyway.

This rule generalizes beyond Codex — any future provider whose auth loader can read another
application's stored credential (the seam pattern §4 already establishes) is bound by the same
ownership boundary.

---

## Proposed addition to §8 (or new subsection): provider wire-fixture testing philosophy

Real providers introduce a testing concern the mock-only phases didn't have: verifying wire-format
translation against protocols this codebase doesn't control, without live network access in the
automated suite. This is a testing *philosophy* both implementations should share, even though the
fixtures themselves are necessarily per-implementation artifacts (different HTTP clients, no
shared wire bytes format implied).

> **Three layers, all exercising the same production translation code**: pure codec tests
> (hand-authored edge cases, no I/O); recorded wire fixtures (sanitized captures from real
> providers, replayed through a deterministic test transport into the real encode/decode code);
> optional live verification (manual, credentialed, non-gating, used only to refresh fixtures or
> detect provider drift).
>
> **Provider wire fixtures are implementation-level, not shared cross-language conformance.** The
> existing `runtime/`/`agent/`/`session/` conformance families stay semantic and language-neutral.
> Raw provider wire payloads are specific to one implementation's HTTP client and do not belong in
> the shared suite merely because both implementations eventually talk to similar APIs. A shared
> wire-fixture corpus between Python and Rust, if ever wanted, is a separate explicit decision, not
> an automatic consequence of both implementing real providers.
>
> **Sanitization removes secrets, never protocol structure.** Authorization headers, cookies,
> account identifiers, and irrelevant timestamps/IDs are stripped or replaced with deterministic
> placeholders (rewritten consistently everywhere they're referenced, not simply deleted, where an
> ID is needed for event correlation within one recorded exchange). Ordering, indices, item
> identity, finish/completion state, and response status are never normalized away — they are what
> the fixture exists to test.
>
> **Recorded fixtures preserve raw wire bytes, not only parsed logical events** — a fixture storing
> only `{event, data}` pairs bypasses the transport-framing layer and tests the decoder alone; a raw
> fixture is what actually exercises framing.
>
> **This does not close the gap between "the fixture was captured from a real provider" and "the
> provider still behaves this way."** Fixture provenance (provider, API family, model, capture
> date, tooling/sanitizer version, purpose) is recorded so a later failure can be diagnosed as
> adapter regression versus provider drift, rather than guessed at.

---

## Decision log for this proposal

1. `ThinkingBlock` on `openai-completions` encode is an explicit error, not a silent drop —
   consistent with §4's existing framing that the block is frozen vocabulary.
2. `codex-responses` function calls stream incrementally (`function_call_arguments.delta`), not
   only as complete finalized items — verified against the real Responses streaming event set, not
   assumed.
3. `codex-responses` reasoning *summary* and `encrypted_content` are recognized-but-unprojected in
   V1, kept distinct from `reasoning_text`, rather than collapsed into one undifferentiated
   `ThinkingBlock`.
4. `completed` is not automatically `stop` — splits on whether a finalized tool call is pending.
5. Retry commits at the first yielded chunk of any kind, not merely "first semantic content" —
   the stricter cutoff avoids needing cross-attempt continuity for state that belongs to one
   physical response.
6. Retry requires two independent gates (no chunk yet yielded, AND transient-failure-classified) —
   timing alone would let a malformed-data failure before the first chunk qualify for retry, which
   it must never do.
7. Live mid-stream cancellation is deferred pending the agent loop gaining a real interrupt
   capability — building only the transport half now would solve part of a cross-layer feature in
   isolation.
8. Credential ownership follows persistence ownership: an implementation must never refresh or
   write into a credential store it does not own, because refresh mutates remote OAuth state via
   rotating refresh tokens that the owning application depends on.
9. Provider wire fixtures are excluded from the shared cross-language conformance suite by design,
   not by oversight — they are implementation-specific by nature (tied to one HTTP client), unlike
   the semantic conformance families.
