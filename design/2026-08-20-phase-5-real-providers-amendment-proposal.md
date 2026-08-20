# Proposed amendment to §4 — Real providers

**Date:** 2026-08-20
**Status:** PROPOSED. Not merged into `2026-08-18-minion-agent-design.md`. Not frozen. Pending the
same review this project applies to cross-language design changes (Rust-side + design reviewer) —
see the precedent of `840d414`, which promoted language-neutral rules into the master design after
review, the pattern this proposal follows. Revised 2026-08-20 (six times) to apply corrections
from five rounds of design review plus one research-driven architectural revision (see the sibling
`-review-feedback.md` file and its appended counter-reviews). **The `codex-responses` continuation
question that drove five review rounds is now resolved**, not by further design-layer elaboration
but by checking a real production implementation: pi's actual `openai-codex-responses` adapter
confirms `encrypted_content` continuation is genuinely required (Case B, confirmed as fact) and
handles it far more simply than this proposal previously did — as an opaque `signature` field
carried directly on `ThinkingBlock`, not a separate `ProviderContinuation` facility with its own
commit point and lineage rules. This proposal now amends §4's `ThinkingBlock` vocabulary
accordingly (see the `codex-responses` reasoning subsection) and retires the more elaborate
five-round design in favor of it. Every other reviewed item below reflects the resolved, corrected
wording from the five prior review rounds, including the malformed-fragmented-tool-call settlement
rule and the fixture-wording fix.
**Target:** `2026-08-18-minion-agent-design.md`, §4 "The LLM seam." §4 currently states the
never-raises contract, the API/provider split table, and the auth-seam principle at a level that
doesn't yet commit to how two concrete APIs (`openai-completions`, `codex-responses`) actually
satisfy them. This proposal is that elaboration, in two distinct categories: the wire-vocabulary
mapping, retry/never-raises composition, and credential-ownership sections are language-neutral
*runtime semantic rules* — normative content a Rust implementation is equally bound by, targeted at
§4. The wire-fixture testing section is *shared project verification policy*, not a runtime
semantic rule — both implementations should verify the same classes of behavior, but how a fixture
stores bytes is test infrastructure, not part of the behavioral contract; it is proposed as an
addition to §8 for that reason, kept separate from §4 rather than folded into it.

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
| `ThinkingBlock` | **Explicit unsupported-content error, raised eagerly before the stream is returned — never a silent drop, and never encoded as an in-band stream failure.** `thinking` is frozen provider-neutral vocabulary (§4); silently losing it between the semantic request and what's dispatched is exactly the drift §8's log-reconstruction invariant exists to catch. A request containing content the selected API cannot represent is a deterministic request-compatibility error, not a provider/network runtime failure — it therefore falls on the "before stream returned" side of §4's never-raises boundary table, alongside `UnknownModelError`, unless the selected provider explicitly declares a compatible mapping. |
| `ToolSchema` | OpenAI function-tool shape. `strict` mode is provider-specific, not part of the common schema. |

Decode: `delta.tool_calls[index]` accumulates per array index — `id`, `function.name`, and
`function.arguments` fragments arrive independently, not necessarily together, finalized only when
the stream signals completion. `finish_reason` maps `stop→stop`, `length→length`,
`tool_calls→tool_use`. `StopReason` is a closed six-value enum (`pending | stop | length | tool_use
| error | aborted`), so "preserved diagnostically" is not by itself a complete rule — an
**unknown** finish reason must still resolve to one of the six: it maps to `StopReason.error`, with
the raw provider value preserved in diagnostic detail, never silently coerced to `stop`.

### `codex-responses`

Decode is an **item-state machine keyed by `item_id`** (with `output_index`/`content_index` for
ordering), not independent per-event handlers — `output_text`, `reasoning_text`, and
`function_call_arguments` all stream incrementally and accumulate the same way, just keyed
differently; `output_item.done` finalizes an item.

`ToolResultMessage` encodes to `function_call_output(call_id, output)` — Responses has no
`role: tool` shape at all, which is itself evidence the two adapters cannot share even a generic
message encoder.

Reasoning: `reasoning_text.delta/done` maps to `ThinkingDelta`/`ThinkingBlock`. Reasoning
**summary** events are recognized but have **no V1 projection** — not merged into `ThinkingBlock`,
not allowed to corrupt `reasoning_text` accumulation for the same item.

**`encrypted_content` continuation — resolved, verified against a real production implementation
rather than left as a hypothesis.** The agent loop already performs `request → tool call → tool
result → second model request`, and Phase 5 is where that loop first contacts a real provider — so
this was never an optional future "multi-turn reasoning" feature. Checked directly against pi's
actual `openai-codex-responses` adapter (`ref-repos/pi/packages/ai/src/api/openai-codex-responses.ts`
and `openai-responses-shared.ts`) rather than continuing to speculate: every Codex request sets
`include: ["reasoning.encrypted_content"]`, and on every subsequent request, whatever reasoning item
was captured is unconditionally replayed — no compatibility check, no replace-vs-accumulate
decision, no separate continuation-state machine. **Case B is confirmed as fact.** A
provider-hosted `previous_response_id` alone is not used for this in pi's default (SSE) transport
either — it resends full history each request, exactly as Minion already does.

**Resolution: add an opaque `signature` field to `ThinkingBlock` (§4 vocabulary), not a separate
continuation-state facility.** Pi's actual mechanism is structurally simpler than the
`ProviderContinuation` design explored across this proposal's first five review rounds (see the
decision log below): it stores the complete opaque reasoning item as a string carried directly on
the content block it belongs to, rather than as a parallel structure with its own commit point,
lineage rules, and settlement semantics. This proposal adopts that mechanism. `ThinkingBlock`
(currently `thinking` text only) gains one additional field:

> `signature` — optional, opaque, provider-specific round-trip data, never interpreted, validated,
> or displayed outside the adapter that produced it. On decode, `codex-responses` captures the
> complete `reasoning` item (including `encrypted_content`) as the block's `signature`. On encode,
> if a `ThinkingBlock` being replayed carries a `signature`, `codex-responses` parses it back into
> the request as that same reasoning item, unconditionally. An adapter encoding a `ThinkingBlock`
> whose `signature` it does not recognize — produced by a different API/provider than the one now
> being dispatched to — drops the signature and encodes only the visible `thinking` text; the
> signature is optional round-trip metadata, not model-visible content, so dropping it is not
> subject to the `ThinkingBlock`-rejection rule above (that rule concerns an API with no concept of
> `thinking` content at all, e.g. Chat Completions, which still eagerly rejects the whole block
> exactly as already specified — a signature never changes whether the block itself is
> representable).

This needs **no new architecture**. No separate commit point: a `ThinkingBlock` and its `signature`
are one field of one content block inside one `AssistantMessage`, which already settles as a single
log entry — nothing new to make atomic. No lineage-eligibility rule: a signature inside a message
already excluded from derivation by fork, reset, or compaction is excluded the same way the rest of
that message already is, under §7's existing rules, unmodified. No separate telemetry carve-out:
`signature` is treated like any other potentially-sensitive field, excluded from telemetry by
default, consistent with how the design already treats provider response bodies generally.

**Related, not fixed by this proposal:** pi uses the identical opaque-signature pattern on
`TextBlock` too (`textSignature`, carrying the Responses API message `id`/`phase` needed for
correct message-ID reuse across turns) — a related gap in the same already-frozen vocabulary, out
of scope here since it was never part of the reasoning-continuation blocker this section resolves.
Worth its own follow-up if `codex-responses` text-message continuity turns out to need it.

The `ProviderContinuation` facility, its production→settlement→reconstruction→replay data flow, its
atomic-settlement rule, and its fork/reset/compaction lineage-eligibility rules — built across this
proposal's first five review rounds — are **superseded** by the resolution above, not silently
dropped: recorded as superseded in the decision log, since the review thread reasoned about them in
good faith, across genuine uncertainty, before this simpler answer was found by checking a real
reference implementation instead of continuing to reason from first principles.

**Conformance coverage:** none proposed beyond what already exists. A `ThinkingBlock.signature`,
once added to the vocabulary, is covered by whatever `session`/`agent` conformance already asserts
round-trip fidelity for ordinary message content — content blocks already survive log/reconstruct
unchanged, and fork/reset/compaction already govern message inclusion. No new scenario category,
no new conformance family.

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

**Live mid-stream cancellation is out of scope for this proposal, and the existing cancellation
contract is boundary-only, not being relaxed here.** The frozen design's `agent/cancellation`
conformance scenario, and the never-raises table's cancellation entry (in-band `aborted` once a
stream is active), describe the consequence of cancelling an active stream — they do not assert
that active mid-stream interruption exists as a required capability. The actual mechanism, verified
directly against the implementation: `AgentLoop.cancel()` sets a flag checked cooperatively between
turn-loop steps (`agent_loop/driver.py`); there is no code path today that closes a live provider
stream mid-flight. Stated explicitly as the language-neutral rule this section relies on: **agent
cancellation currently prevents subsequent work at cooperative loop boundaries; V1 does not require
asynchronous interruption of an already-running provider stream.** Given that, deferring the
transport half of live cancellation is sound — building it ahead of the loop half would solve a
problem in isolation that needs to be solved as one cross-layer feature. The existing `aborted`
stop-reason semantics are unaffected and remain ready for whenever that capability exists.

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

1. `ThinkingBlock` on `openai-completions` encode is an explicit error, not a silent drop —
   consistent with §4's existing framing that the block is frozen vocabulary.
2. `codex-responses` function calls stream incrementally (`function_call_arguments.delta`), not
   only as complete finalized items — verified against the real Responses streaming event set, not
   assumed.
3. `codex-responses` reasoning *summary* is recognized-but-unprojected in V1, kept distinct from
   `reasoning_text`, rather than collapsed into one undifferentiated `ThinkingBlock`.
   `encrypted_content` is treated separately (item 18 below) — confirmed required continuation
   state, resolved via a `ThinkingBlock.signature` field rather than a separate facility.
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
7. Live mid-stream cancellation is deferred, consistent with (not a relaxation of) the existing
   frozen cancellation contract: verified directly against `AgentLoop.cancel()` in
   `agent_loop/driver.py`, cancellation today is cooperative and boundary-only (a flag checked
   between turn-loop steps), with no code path that interrupts a live provider stream. Building
   the transport half of active cancellation ahead of the loop half would solve part of a
   cross-layer feature in isolation.
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
13. **SUPERSEDED by item 18 below.** `codex-responses` continuation was originally addressed with a
    `ProviderContinuation` facility (API/compatibility identity, log-reconstructable,
    session-ancestry-aware, eager-fails when required-but-missing, sanitized non-payload metadata
    only in diagnostics; a production→logical-settlement→log-reference→request-reconstruction→replay
    data flow; atomic settlement of the assistant response with continuation references; selection
    scoped to effective session lineage covering fork/reset/compaction as one rule; two-part
    API-and-lineage compatibility), built across five review rounds against an open empirical
    question (Case A vs. Case B). Retained here for the historical record of what was reasoned
    through, not because it remains the design — see item 18 for the resolution that replaces it.
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
17. **SUPERSEDED by item 18 below.** The conformance coverage note built for the
    `ProviderContinuation` facility (committed-continuation reachability, discarded-retry absence,
    fork-boundary scoping, ineligible-API-switch handling, incompatible-continuation eager failure,
    reset/compaction lineage eligibility, atomic settlement) is no longer needed — see item 18.
18. **Resolution, verified against pi's real `openai-codex-responses` adapter rather than continued
    speculation:** `encrypted_content` continuation is confirmed required (Case B, confirmed as
    fact — every request includes `reasoning.encrypted_content`, every subsequent request
    unconditionally replays it, no compatibility check or accumulation logic). Pi's actual
    mechanism is an opaque `signature` field carried directly on `ThinkingBlock`, not a separate
    continuation-state facility — this proposal adopts that mechanism instead of items 13/17's
    `ProviderContinuation` design. This needs no new architecture: no separate commit point (a
    signature is one field of one content block inside one `AssistantMessage`, which already
    settles as a single log entry), no lineage-eligibility rule (a signature inside an
    excluded-by-derivation message is already excluded the same way the rest of that message is,
    under §7's existing rules), no new telemetry carve-out (treated like any other sensitive field,
    excluded from telemetry by default), and no new conformance coverage (already covered by
    existing round-trip and derivation conformance for ordinary message content). Related but
    explicitly out of scope: pi uses the identical pattern on `TextBlock` (`textSignature`, for
    Responses API message-ID/phase reuse) — a separate gap in the same vocabulary, not addressed
    here since it was never part of the reasoning-continuation blocker this item resolves.
