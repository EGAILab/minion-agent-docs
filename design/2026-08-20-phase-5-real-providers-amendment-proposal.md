# Proposed amendment to §4 — Real providers

**Date:** 2026-08-20 (reconciled 2026-08-21)
**Status:** RECONCILED against `2026-08-20-minion-agent-design.md`, now FROZEN. That master
revision's own "Supersession and normative authority" section names two conflicts with the version
of this proposal it superseded — the cooperative-only cancellation deferral, and the generic
`ThinkingBlock.signature` vocabulary proposal — and states both are decided in the master's favor.
This revision applies that reconciliation: the master's mandatory active-cancellation requirement
and its `thinking_signature`/`redacted`/`text_signature`/`thought_signature`/`namespace` vocabulary
are adopted here rather than re-litigated, per the project owner's explicit priority that Pi
fidelity is non-negotiable and the frozen master is retroactively authoritative. Still pending: the
one open empirical item this proposal was never able to resolve at the design layer — the exact
Codex `encrypted_content` replay payload/compatibility-key/state-evolution contract, which requires
a live credentialed Codex session (see the `codex-responses` reasoning subsection).
**Target:** `2026-08-20-minion-agent-design.md`, §4 "The LLM seam" — now frozen, and now containing
substantially more of this material directly than when this proposal was first drafted against the
2026-08-18 design. The master's own §4 now specifies the provider-neutral replay-signature
vocabulary, the mandatory target-model transformation stage, and the mandatory active-cancellation
requirement (§6). This proposal's remaining job has narrowed to what the master leaves API-specific:
the `codex-responses`/`openai-completions` wire-level encode/decode mapping, retry/never-raises
composition (including its required interaction with the now-mandatory abort signal), and
credential ownership — normative *runtime semantic rules* a Rust implementation is equally bound
by. The wire-fixture testing section remains *shared project verification policy*, not a runtime
semantic rule, targeted at §8 rather than §4 for that reason.

**Scope note:** this document intentionally excludes everything that is Python-specific
implementation (file layout, concrete config classes, references to existing Python functions).
That material belongs in a `plans/python/` implementation plan once this proposal is settled, not
in `design/`.

---

## Proposed addition to §4: wire vocabulary mapping

Real adapters translate in two directions — provider-neutral vocabulary → wire format (encode),
wire events → `StreamChunk` (decode). The structural encode/decode mappings themselves are
deterministic and independently testable from transport; any provider-specific preparation that
requires I/O (see the `ImageBlock` row below) occurs before or around structural encoding and never
mutates the semantic reference it prepares. `openai-completions` and `codex-responses` are
genuinely different wire protocols (older Chat Completions shape vs. a newer event-oriented
Responses shape) sharing almost nothing at the wire level, including how tool results encode — this
is a property of the two real APIs, not a Python implementation choice. `openai-completions` and
`codex-responses` therefore have independently specified wire mappings because their observable
protocols differ materially, including tool-result representation and streaming event structure; no
behavior may be inferred for one API from the mapping of the other. This is a constraint on
observable behavior, not on internal code structure — implementations may share internal helpers
(generic state-machine components, serialization infrastructure) across the two adapters, but
sharing must never introduce semantic coupling between the two mappings.

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
| `ImageBlock` (`reference`) | The reference is an immutable content-addressed identity (§5). If the wire format needs a URL, materializing the artifact into a provider-fetchable one is provider-specific preparation that may perform I/O (artifact read, upload, signed-URL generation) — it happens before structural encoding and produces a *wire representation* only; the semantic reference is never rewritten as though a mutable URL were the source of truth. |
| `ThinkingBlock` | **Should never reach this encoder unconverted — §4's mandatory target-model transformation runs first.** An earlier draft of this proposal specified an eager unsupported-content error here; that conflicted with §4's now-frozen thinking-compatibility rule, which is unconditional on model identity, not on target-API capability: since `openai-completions` decode has no reasoning/thinking wire shape (below), any `ThinkingBlock` reaching this adapter is necessarily a *different-model* case, and §4 mandates that case convert non-redacted thinking to ordinary text (signature dropped) or omit redacted thinking — never error. A `ThinkingBlock` still reaching this encoder unconverted indicates §4's transformation stage was skipped or violated, which is an internal consistency failure to fix at that stage, not a provider-compatibility condition for this adapter to invent its own error path for. |
| `ToolSchema` | OpenAI function-tool shape. `strict` mode is provider-specific, not part of the common schema. |

Decode: `delta.tool_calls[index]` accumulates per array index — `id`, `function.name`, and
`function.arguments` fragments arrive independently, not necessarily together, finalized only when
the stream signals completion. `finish_reason` maps `stop→stop`, `length→length`,
`tool_calls→tool_use`. `StopReason` is a closed vocabulary — `pending | stop | length | tool_use |
error | aborted | deferred` (§4) — so "preserved diagnostically" is not by itself a complete rule —
an **unknown** finish reason must still resolve to one of those values: it maps to `StopReason.error`,
with the raw provider value preserved in diagnostic detail, never silently coerced to `stop`. Chat
Completions has no `deferred` outcome for an implemented API, so that value is not reachable through
this adapter; it is listed for completeness against the shared vocabulary, not because this section
introduces it.

### `codex-responses`

Decode is an **item-state machine keyed by `item_id`** (with `output_index`/`content_index` for
ordering), not independent per-event handlers — `output_text`, `reasoning_text`, and
`function_call_arguments` all stream incrementally and accumulate the same way, just keyed
differently; `output_item.done` finalizes an item.

`ToolResultMessage` encodes to `function_call_output(call_id, output)` — Responses has no
`role: tool` shape at all, which is itself evidence the two adapters cannot share even a generic
message encoder.

Reasoning: `reasoning_text.delta/done` maps to `ThinkingDelta`/`ThinkingBlock.thinking`. Per §4's
"Responses reasoning presentation" rule, `reasoning_summary_text` deltas also contribute to that
same visible `thinking`: on item finalization, visible thinking prefers provider summary text when
present, otherwise reasoning-content text, otherwise the accumulated streamed thinking — summary is
not a discarded, unprojected event as an earlier draft of this proposal stated. The full replayable
reasoning item is tracked separately (see below) and is never conflated with the visible-text
preference order.

**`encrypted_content` continuation and `ThinkingBlock.thinking_signature`: the vocabulary and
architecture are now specified directly by the frozen master (§4 "Responses-family replay
signatures"), not proposed here.** An earlier revision of this proposal spent five review rounds
building a `ProviderContinuation` facility for this, then replaced it with a generic
`ThinkingBlock.signature` field after checking pi's real `openai-codex-responses` adapter — that
generic field is itself now superseded: the master's frozen vocabulary is `thinking_signature`
(plus `redacted: bool`), matching Pi's actual field name exactly, and the master already states the
governing rules generically for all Responses-family APIs: a retained same-model signed thinking
block is replayed by the compatible adapter; the adapter never synthesizes a provider reasoning item
from visible thinking text alone; a same-model unsigned thinking block contributes no replay item.
This section's remaining job is only the `codex-responses`-specific realization of that already-
frozen rule:

> On decode, `codex-responses` requests `include: ["reasoning.encrypted_content"]` on every
> request and captures the complete `reasoning` item (including `encrypted_content`) as
> `ThinkingBlock.thinking_signature`. On encode, if a same-model `ThinkingBlock` being replayed
> carries a `thinking_signature`, `codex-responses` parses it back into the request as that same
> reasoning item, unconditionally — no compatibility check, no replace-vs-accumulate decision, no
> separate continuation-state machine, matching pi's actual behavior exactly. A provider-hosted
> `previous_response_id` alone is not used for this in pi's default (SSE) transport either — it
> resends full history each request, exactly as Minion already does.

`ToolCall.thought_signature` and `TextBlock.text_signature` are likewise now master vocabulary
(§4), not proposed here. For `codex-responses` specifically: `text_signature` follows the V1/legacy
wire format the master names (`{v: 1, id, phase?}` JSON, phase constrained to
`commentary | final_answer`, falling back to treating any non-JSON or malformed-JSON string as a
bare legacy message id) — this proposal's earlier draft flagged `TextBlock` signature continuity as
"related but out of scope"; the master has since closed that gap directly, so it is in scope and
already specified, not a follow-up.

**What remains genuinely open — not resolvable at the design layer, requires a live Codex
session:** the exact complete provider item(s) that must round-trip through `thinking_signature`
for a real multi-turn Codex tool-call exchange, and whether any provider-specific edge case (a
malformed or expired `thinking_signature` on replay, for instance) needs handling beyond "signature
parse/conversion failures follow the ordinary provider-stream error path" (already stated in §4).
This is empirical verification work against a real Codex account, not a further design question.

**Conformance coverage:** already covered by the master's own §8 conformance families —
`same-model-thinking-signature-replayed`, `same-model-unsigned-thinking-not-replayed`,
`cross-model-thinking-converts-to-text`, `cross-model-redacted-thinking-omitted`, and
`responses-text-signature-replayed` are already checked in as canonical `agent/` scenarios. No new
scenario category or family is proposed by this section.

Stop reason comes from **response-level completion state**, keyed by the specific completion
reason rather than the outer state alone, since not every form of incompleteness means
token/output-length exhaustion:

- `completed`, no pending tool call requiring execution → `stop`
- `completed`, with a finalized function call requiring execution → `tool_use`
- `incomplete`, reason is output/token-limit exhaustion → `length`
- `incomplete`, reason is `content_filter` or another recognized non-length operational reason →
  `error`, with the specific reason preserved in diagnostic detail
- `incomplete`, unknown/unrepresentable reason → `error`, with the raw reason preserved
  diagnostically
- `cancelled` → `aborted`
- `failed` → `error`

The `completed→stop` vs. `completed→tool_use` split preserves the provider-neutral distinction
between a response that hands control back with text and one that hands control to tools — losing
it would mean an implementation cannot tell those apart from `StopReason` alone.

### Malformed fragmented tool-call settlement (both APIs)

Both decoders above accumulate a tool call from independently-arriving fragments (`delta.tool_calls[index]`
for `openai-completions`, `item_id`-keyed items for `codex-responses`) — untrusted provider wire
input, not internal state. This is externally observable and must settle identically regardless of
implementation:

- Conflicting IDs or function names on what should be the same fragment, impossible index/`item_id`
  reuse, or incomplete finalization are protocol errors.
- Finalized `arguments` must parse as JSON and satisfy the provider-neutral tool-call argument
  shape (currently a JSON object); anything else is a protocol error.
- No partial or malformed wire item is ever surfaced as an executable semantic tool call.
- These are provider-sent malformed data, not an adapter bug — they settle the same way any other
  operational stream failure does under the never-raises boundary: in-band, as `StopReason.error`
  with the raw diagnostic preserved, never by raising out of iteration.

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
>
> Retry count, backoff, jitter, and the exact provider-specific classification of retryable server
> statuses are implementation/provider policy unless separately standardized — the language-neutral
> rule fixes the commitment boundary and the failure-class distinction above, not identical retry
> schedules across Python and Rust.

**Live mid-stream cancellation is now mandatory, reversing this section's earlier deferral.** §6
"Active abort/cancellation" (frozen master) states plainly: "Minion MUST expose equivalent
[Pi] behavior... Abort does not mean 'wait until the next provider-request boundary.' It is an
active cancellation request," with the signal required to propagate to "provider stream / pending
provider attempt." §9's Phase 5 build-order entry makes the scope explicit for this proposal
specifically: "This phase MUST consume the master vocabulary above and propagate the run-scoped
abort signal through pending attempts, retry/backoff, provider streaming, and transport
cancellation as Pi does." This proposal's earlier justification — citing `AgentLoop.cancel()`'s
cooperative, boundary-only implementation as evidence the frozen design's position was
cooperative-only — was accurate about the *implementation at the time*, but the master's
subsequent Pi-fidelity audit found that implementation itself was the gap, not the design's actual
requirement (Pi's own `Agent.abort()` genuinely calls `AbortController.abort()`, and that signal is
threaded into the provider `fetch()` call). This proposal now pins how the mandatory abort signal
composes with retry and the never-raises boundary, matching pi's actual behavior
(`sleep(delayMs, signal)` in pi's retry loop rejects immediately on abort rather than waiting out
the backoff; each retry attempt checks `signal?.aborted` before starting):

> **Cancellation always takes precedence over retry, at any point in the retry-commitment
> lifecycle.** An abort signal received while a pre-commitment attempt is in flight, or during its
> retry backoff wait, cancels that attempt and the retry loop immediately — it is not queued behind
> the current attempt's natural completion, and the two-gate retry-eligibility rule above (no chunk
> yet yielded, transient-failure-classified) never overrides an abort: cancellation is a distinct
> signal from retry-worthiness, not a third gate to satisfy alongside them.
>
> **After the retry-commitment boundary (first public chunk), cancellation settles exactly as §4's
> never-raises contract already states**: in-band, as `aborted`, through the returned
> `AssistantStream` — this proposal adds no new mechanism here, since the master's "Cancellation
> after stream creation remains in-band as `aborted`" rule already covers it directly.
>
> **Releasing/closing a stream cancels owned pending provider work**, per §4's never-raises
> section — for a real adapter, that means the transport's in-flight request/connection is actually
> torn down (an aborted `fetch()`/HTTP request), not merely stopped being read from.

The retry commitment boundary, the two-gate eligibility rule, and retry-exhaustion-settles-in-band
above are unaffected by this change — cancellation is layered on top of them, not a replacement for
any of them.

---

## Proposed addition to §4: authentication ownership

§4's Authentication subsection states the seam ("auth is a seam, not a file path") and names the
Codex CLI credential file as the first loader, chosen for immediate compatibility with existing
Codex CLI users. It does not yet state what happens when that external credential expires — this
proposal closes that gap with a rule that is genuinely normative (any implementation reading
another application's credential store is bound by it, not a Python-specific concern):

> **Credential ownership follows persistence ownership.** A credential read from another
> application's credential store remains owned by that application. An implementation may use a
> currently-valid access token from it, but does not independently refresh or mutate
> externally-owned credentials **unless the owner exposes an explicit supported interoperability
> contract granting that authority** — refreshing mutates remote OAuth state (rotating refresh
> tokens), and only an application holding that granted authority can safely do so without risking
> the *other* application's next use of its own credential. Credentials an implementation's own
> login flow produces are owned by it end to end: it refreshes them and persists every replacement
> to its own storage.
>
> For Codex CLI's current file-based interop, no such contract exists — reading `auth.json` is
> reverse-engineered from open-source Codex, not a supported interoperability API — so the outcome
> is unchanged: read-only, no independent refresh. The qualifier exists to keep the general rule
> correct if a future provider ever offers a supported shared-credential service, not to change
> Codex's behavior today.
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
automated suite. This is shared verification policy, not runtime semantics: implementations may
keep separate fixture corpora or deliberately share provider-wire fixtures — fixture representation
remains test infrastructure, not Minion semantic conformance, either way.

> **Three layers, all exercising the same production translation code**: pure codec tests
> (hand-authored edge cases, no I/O); recorded wire fixtures (sanitized captures from real
> providers, replayed through a deterministic test transport into the real encode/decode code);
> optional live verification (manual, credentialed, non-gating, used only to refresh fixtures or
> detect provider drift).
>
> **Provider wire fixtures are not part of shared cross-language semantic conformance.** The
> existing `runtime/`/`agent/`/`session/` conformance families stay semantic and language-neutral.
> This exclusion is not because raw wire payloads are inherently tied to one implementation's HTTP
> client — a sanitized SSE/HTTP wire corpus is provider protocol data, not Python-httpx- or
> Rust-reqwest-specific data, and could in principle be consumed by both implementations. The actual
> reason is that fixture representation is test infrastructure, not part of the Minion behavioral
> specification: implementations may maintain separate fixture corpora, or may deliberately share a
> provider-wire corpus; either choice is a testing decision, not a semantic one. A shared
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
> fixture is what actually exercises framing. Raw bytes are the fixture's content; the exact chunk
> segmentation observed during recording (which TCP/HTTP-client boundary a byte happened to fall on)
> is not itself provider semantics — SSE parsing must be correct under arbitrary transport chunking,
> so fixture infrastructure should replay the same raw bytes under varied segmentation (one large
> chunk; one byte at a time; boundaries falling inside UTF-8 sequences, JSON tokens, and SSE lines),
> not treat the recorded segmentation as normative.
>
> **This does not close the gap between "the fixture was captured from a real provider" and "the
> provider still behaves this way."** Fixture provenance (provider, API family, model, capture
> date, tooling/sanitizer version, purpose) is recorded so a later failure can be diagnosed as
> adapter regression versus provider drift, rather than guessed at.

---

## Proposed addition to §4: deferred topics, recorded explicitly

Two decisions this proposal touches on but does not resolve, recorded so a reader does not
reasonably assume they were settled by omission:

> **Cost computation remains deferred.** Phase 5 preserves the provider-neutral `Usage.cost` field
> and all token categories required for future computation, but does not standardize a pricing
> catalog or local cost-computation policy. Pricing source, provider/model precedence, historical
> price versioning, and unknown-model behavior remain deferred.
>
> **API-key resolution has no fallback chain in V1.** Real-provider plugins consume
> already-resolved authentication configuration; V1 does not define an additional
> provider-specific environment-variable or credential fallback chain. (Concrete config classes and
> file structure implementing this remain Python-plan material, not design content.)

---

## Decision log for this proposal

1. **REVERSED.** `ThinkingBlock` on `openai-completions` encode is never an eager error — an
   earlier draft's "explicit error, not a silent drop" rule conflicted with the frozen master's
   unconditional (model-identity-based, not API-capability-based) cross-model thinking-compatibility
   rule: since this adapter's decode side has no reasoning/thinking wire shape, any `ThinkingBlock`
   it encounters is necessarily a different-model case, which §4 mandates converting to plain text
   (or omitting if redacted) upstream in the mandatory transformation stage, before this adapter's
   encoder ever runs. An unconverted `ThinkingBlock` reaching this encoder is now a transformation-
   stage bug to fix, not a condition this adapter manufactures its own error path for.
2. `codex-responses` function calls stream incrementally (`function_call_arguments.delta`), not
   only as complete finalized items — verified against the real Responses streaming event set, not
   assumed.
3. `codex-responses` reasoning *summary* text contributes to visible `ThinkingBlock.thinking`
   (preferring summary text, then reasoning-content text, then accumulated streamed thinking on
   finalization) — corrected from an earlier draft's "no V1 projection" claim, which was wrong: the
   frozen master's "Responses reasoning presentation" rule states summary text is projected. The
   full replayable reasoning item is tracked separately in `thinking_signature` (item 19 below),
   never conflated with this visible-text preference order.
4. `completed` is not automatically `stop` — splits on whether a finalized tool call is pending.
   `incomplete` is keyed by its specific reason rather than blanket-mapped to `length` — only
   output/token-limit exhaustion maps to `length`; `content_filter` and other non-length reasons
   map to `error` with the reason preserved diagnostically.
5. Retry commits at the first yielded chunk of any kind, not merely "first semantic content" —
   the stricter cutoff avoids needing cross-attempt continuity for state that belongs to one
   physical response.
6. Retry requires two independent gates (no chunk yet yielded, AND transient-failure-classified) —
   timing alone would let a malformed-data failure before the first chunk qualify for retry, which
   it must never do. Retry count, backoff, jitter, and provider-specific retryable-status
   classification are implementation/provider policy, not part of this language-neutral rule.
7. **REVERSED.** Live mid-stream cancellation is mandatory, not deferred — the frozen master's §6
   requires the run-scoped abort signal to reach "provider stream / pending provider attempt," and
   §9's Phase 5 entry requires it to propagate "through pending attempts, retry/backoff, provider
   streaming, and transport cancellation." Cancellation always takes precedence over retry at any
   point in the retry-commitment lifecycle; after the retry-commitment boundary it settles exactly
   as the existing never-raises `aborted` rule already states — no new mechanism needed there. This
   proposal's earlier deferral correctly read the *implementation at the time* (`AgentLoop.cancel()`
   was genuinely cooperative-only, verified against `agent_loop/driver.py`), but the master's
   Pi-fidelity audit found the implementation, not the design's actual intent, was the gap — Pi's
   own `Agent.abort()` genuinely calls `AbortController.abort()`, threaded into the provider
   `fetch()` call itself.
8. Credential ownership follows persistence ownership, generalized around granted authority rather
   than a blanket prohibition: an implementation does not independently refresh or mutate
   externally-owned credentials unless the owner exposes an explicit supported interoperability
   contract granting that authority. For Codex CLI's current file-based interop no such contract
   exists, so the outcome is unchanged (read-only, no independent refresh); the generalization only
   future-proofs the rule.
9. Provider wire fixtures are excluded from the shared cross-language *semantic* conformance suite
   by design, not by oversight — not because raw wire bytes are inherently tied to one
   implementation's HTTP client (a sanitized wire corpus could in principle be shared), but because
   fixture representation is test infrastructure, a project verification-policy decision, not part
   of the runtime behavioral specification.
10. Fixture infrastructure should replay recorded raw bytes under varied transport-chunk
    segmentation (single chunk, byte-at-a-time, boundaries inside UTF-8/JSON/SSE-line structure) —
    SSE parsing must be correct under arbitrary chunking, and the segmentation observed during
    recording is not itself provider semantics worth pinning as normative.
11. Cost computation deferral is recorded explicitly rather than left to be inferred by omission:
    `Usage.cost` and its token categories are preserved, but pricing catalog, source, and
    versioning policy remain out of scope for this proposal.
12. API-key resolution has no fallback chain in V1 — recorded as the one language-neutral policy
    sentence from the excluded Python config material, since it is behavioral policy rather than
    file/config structure.
13. **SUPERSEDED, twice over — see item 19 below.** `codex-responses` continuation was originally addressed with a
    `ProviderContinuation` facility (API/compatibility identity, log-reconstructable,
    session-ancestry-aware, eager-fails when required-but-missing, sanitized non-payload metadata
    only in diagnostics; a production→logical-settlement→log-reference→request-reconstruction→replay
    data flow; atomic settlement of the assistant response with continuation references; selection
    scoped to effective session lineage covering fork/reset/compaction as one rule; two-part
    API-and-lineage compatibility), built across five review rounds against an open empirical
    question (Case A vs. Case B). Retained here for the historical record of what was reasoned
    through, not because it remains the design — see item 19 for what is actually in force now.
14. Malformed fragmented tool-call settlement is pinned identically for both APIs: conflicting
    IDs/names, impossible index/`item_id` reuse, non-JSON or non-object finalized arguments, and
    incomplete finalization are protocol errors that settle in-band as `StopReason.error` — never
    raised out of iteration, and never surfaced as an executable semantic tool call. This closes an
    externally-observable gap the original mapping left unaddressed.
15. The fixture-testing section's introductory paragraph previously stated fixtures are
    "necessarily per-implementation artifacts," directly contradicting its own later paragraph
    permitting a shared sanitized wire corpus. Corrected to state the shared-verification-policy
    framing consistently throughout the section.
16. `Usage.cost`'s concrete representation (optional-while-uncomputed; exact decimal vs. float) is
    a real open question, but predates this proposal — `Usage.cost` was already frozen provider-
    neutral vocabulary before Phase 5 (see master design's LLM vocabulary). It is tracked as a
    follow-up against that earlier decision, not folded into this amendment, since resolving it is
    not specific to real-provider wire behavior.
17. **SUPERSEDED — see item 19 below.** The conformance coverage note built for the
    `ProviderContinuation` facility (committed-continuation reachability, discarded-retry absence,
    fork-boundary scoping, ineligible-API-switch handling, incompatible-continuation eager failure,
    reset/compaction lineage eligibility, atomic settlement) is no longer needed — see item 19.
18. **SUPERSEDED by item 19 below.** This proposal's own prior resolution — a generic
    `ThinkingBlock.signature` field, adopted after checking pi's real adapter directly — is itself
    superseded by the frozen master's vocabulary, which uses different naming (`thinking_signature`)
    and is broader in scope (also pins `redacted`, `TextBlock.text_signature`, and
    `ToolCall.thought_signature`, none of which this item covered). Retained for the historical
    record of the reasoning that led to checking pi's source in the first place — a real
    methodological improvement over the five rounds before it — not because its specific field name
    or scope remains current. See item 19.
19. **Master vocabulary adopted directly, not re-specified here.** `ThinkingBlock.thinking_signature`
    and `redacted`, `TextBlock.text_signature`, and `ToolCall.thought_signature` are frozen master
    §4 vocabulary (`2026-08-20-minion-agent-design.md`), independently verified there against Pi's
    real `types.ts` field-for-field (see that document's own review feedback). This proposal's
    remaining contribution is only the `codex-responses`-specific wire realization of that
    already-frozen vocabulary: the `include: ["reasoning.encrypted_content"]` request flag,
    unconditional same-model replay with no compatibility check or accumulation logic (Case B,
    confirmed against pi's real adapter behavior — not a hypothesis), and the V1/legacy
    `text_signature` wire format. `TextBlock` signature continuity — flagged by an earlier draft of
    this item as "related, out of scope" — is closed by the master directly, not deferred. The one
    item genuinely still open is empirical: the exact complete provider item(s), compatibility
    identity, and state-evolution behavior for a real multi-turn Codex tool-call exchange, which
    needs a live credentialed Codex session to verify and is not resolvable by further design work.
