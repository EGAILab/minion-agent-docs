# Proposed amendment to §4 — Real providers

**Date:** 2026-08-20
**Status:** PROPOSED. Not merged into `2026-08-18-minion-agent-design.md`. Not frozen. Pending the
same review this project applies to cross-language design changes (Rust-side + design reviewer) —
see the precedent of `840d414`, which promoted language-neutral rules into the master design after
review, the pattern this proposal follows. Revised 2026-08-20 (five times) to apply corrections
from five rounds of design review, including three Rust-side passes (see the sibling
`-review-feedback.md` file and its appended counter-reviews). The remaining open item on
`codex-responses` continuation splits into two pieces that should not be conflated:
**(A) the language-neutral Minion data-flow contract** — how continuation moves from decoder
output through an atomic logical-settlement point (distinct from the retry-commitment boundary),
into content-addressed request reconstruction, effective-session-lineage eligibility (fork, reset,
and compaction treated as one rule per §7's existing derivation principles), and API-mismatch
handling — **is now fully pinned below** (see the `codex-responses` reasoning subsection); **(B) the
empirical Codex replay contract** — the exact provider item(s), compatibility key,
replacement-vs-accumulation semantics, and which terminal outcomes yield reusable continuation —
**remains genuinely open** and requires live verification against a real Codex multi-turn
tool-call exchange before that subsection's specific payload details can freeze. (A) does not
depend on (B)'s outcome; the
generic facility is proposed regardless of what the experiment finds. Every other reviewed item
below reflects the resolved, corrected wording, including a newly-pinned malformed-fragmented-
tool-call settlement rule and a fixture-wording self-contradiction fixed in an earlier revision.
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

**`encrypted_content` continuation state — the facility is specified below; its exact wire payload
and compatibility key are pending live verification before this section freezes.** The agent loop
already performs `request → tool call → tool result → second model request`, and Phase 5 is where
that loop first contacts a real provider — so this is not an optional future "multi-turn reasoning"
feature; it determines whether a Codex agent's second turn works at all once a tool call is
involved. OpenAI's own reasoning-items guidance states that reasoning items should be replayed in
the input of subsequent Responses requests when manually managing context, and real reports of
turn-2 400s when this is omitted exist in the wild (`openai/openai-python#3008`,
`openai/codex#3841`). A provider-hosted `previous_response_id` is not an adequate substitute for
Minion's own reconstruction, since it makes request reconstruction depend on mutable, expiring,
remote state Minion doesn't control — the frozen design already requires anything reaching a model
request to be reconstructable from Minion's own log (§8), not from provider-side session state.

The working hypothesis is therefore **Case B**: `encrypted_content` is required provider-opaque
continuation state, not discardable telemetry — but it still must never become `ThinkingBlock`, and
the architecture should reserve the facility now rather than retrofit it later:

> **`ProviderContinuation`** — log-only, content-addressed, associated with the response/turn that
> produced it:
> - carries an API identity and a compatibility/version identity, so continuation is never replayed
>   to a mismatched API or an incompatible provider version;
> - retains the complete replayable provider item required for replay, not a bare detached
>   `encrypted_content` scalar;
> - is reconstructable from Minion's own log/artifact store (§8), independent of provider-side
>   session state;
> - is selected only from the same **effective session lineage** used to reconstruct the rest of
>   the request — durable retention in the append-only log and replay *eligibility* are different
>   questions, and this facility is governed by the latter;
> - fails eagerly when continuation is required but missing or incompatible, rather than being
>   silently omitted from the next request;
> - the opaque payload bytes are never serialized into ordinary telemetry or diagnostics — only
>   explicitly sanitized non-payload metadata (present/missing, API identity, a
>   compatibility-mismatch category) may cross the existing telemetry sanitization boundary.

Reserving the facility's *properties* is not the same as pinning its *data flow*, and the latter is
the part the frozen request-reconstruction invariant (§8) actually depends on: the exact state
reaching a later request must be derivable from committed Minion state, not merely exist somewhere
in an artifact store. So this proposal also pins the behavioral path:

> ```text
> physical provider attempt
>     ↓
> decoder observes provider continuation item(s)          (attempt-local, not yet durable)
>     ↓
> logical response settlement                              (see rule 2 below — distinct from the
>     ↓                                                      retry commitment boundary above)
> content-addressed artifact + committed log reference, atomically with the assistant response
>     ↓
> request reconstruction selects applicable continuation deterministically
>     ↓
> request/header references the exact selected provider state
>     ↓
> matching adapter receives and replays that reconstructed state
> ```
>
> Exact event names, structs, artifact layout, and language-specific storage types remain
> implementation detail; the path above and the rules below are the language-neutral contract. Note
> that **"retry commitment" and "logical response settlement" are two distinct boundaries, not one**:
> the retry-commitment boundary (first public `StreamChunk`) only fixes that the physical attempt can
> no longer be transparently retried — it does not make any continuation observed by that point
> durable. Continuation stays attempt-local until the later, separate logical-settlement point below.
>
> 1. **No ghost continuation from discarded attempts.** A pre-commit attempt retried under the
>    retry-commitment rule above, or any abandoned attempt, must never publish durable continuation
>    state — only the selected/committed physical attempt may.
> 2. **Logical response settlement is explicit, and atomic with the assistant response.**
>    Continuation may be observed incrementally by the decoder, but stays attempt-local until a
>    defined logical-settlement point commits it to the session. At that point, the settled
>    assistant response and every continuation reference derived from the same physical attempt
>    become reachable as one atomic logical settlement: artifact bytes may be persisted earlier, but
>    no committed session state may expose the terminal assistant response without the continuation
>    references required to reconstruct it, nor may a continuation reference from a response that
>    did not itself commit become independently reachable. This is behavioral, not a storage
>    prescription — a transactional append, a composite event, or another mechanism may satisfy it,
>    provided concurrent readers, fork reconstruction, and process-recovery logic can never observe
>    a half-settled response. The rule applies only to continuation actually selected as replayable
>    for that response; a response with no continuation requirement settles normally. (The live
>    experiment below determines which terminal outcomes yield replayable continuation at all; this
>    rule fixes that whatever is reachable is reachable atomically, not where the line falls.)
> 3. **Continuation is part of request reconstruction, not adapter-private memory.** The
>    content-addressed request-header composition (§8) gets an explicit provider-state/continuation
>    component (the exact component name is not normative) referencing the committed artifact, so
>    the invariant `reconstructed continuation == continuation actually supplied to dispatch` is
>    provable the same way the rest of request reconstruction already is.
> 4. **Selection order is deterministic.** Absent live evidence otherwise, the facility preserves
>    deterministic production order rather than assuming later state silently replaces earlier
>    state; the live experiment determines whether Codex replay is latest-only, replacement-based,
>    or an ordered accumulated sequence.
> 5. **Selection follows effective session lineage — one rule, three instances.** Continuation
>    selection is derived from the same effective lineage already used to reconstruct the rest of
>    the request (§7's derivation rules), not merely from what is durably present in the append-only
>    log:
>    - *Fork:* a fork reaches exactly the continuation committed at or before its ancestry boundary;
>      continuation produced after that boundary cannot leak into it.
>    - *Reset floors eligibility:* `session/reset` does not delete historical `ProviderContinuation`
>      records — they remain auditable, exactly as reset excludes prior surface entries from
>      derivation without deleting them (§7) — but continuation originating at or before the reset
>      boundary is ineligible for requests reconstructed after that reset, unless a later committed
>      event explicitly establishes a new continuation lineage. Pre-reset opaque provider state is
>      never replayed merely because it is still physically present in the log.
>    - *Compaction follows superseded/retained-tail status:* consistent with §7's "compaction
>      changes provider context, not storage," a continuation item stays replay-eligible only while
>      the assistant response that produced it remains part of the effective reconstructed
>      history — including an explicitly retained tail. If compaction supersedes that originating
>      response, its continuation stays durable for audit and historical reconstruction but becomes
>      ineligible for new dispatch; continuation attached to a response preserved in the retained
>      tail stays eligible, subject to the ordinary compatibility rules below.
> 6. **API/provider mismatch is disambiguated, not conflated.** An API switch to an API that does
>    not consume Codex continuation leaves the historical continuation logged but not selected or
>    replayed — not a failure, and not a deletion. The selected API/provider requiring continuation
>    while only missing or incompatible continuation exists (whether by provider mismatch or by rule
>    5's lineage-eligibility rules making the only available continuation ineligible) is an eager
>    preparation failure before the stream is returned (same boundary as `ThinkingBlock` rejection
>    above). The eligibility predicate is therefore always two-part: provider/API compatibility
>    **and** effective-lineage compatibility — never provider compatibility alone.
> 7. **Never model-visible.** `ProviderContinuation` remains request state — never a `ThinkingBlock`,
>    `AssistantMessage`, or any other surface message type, regardless of how the flow above is
>    implemented.

**Before this section is frozen**, a live experiment against a real Codex multi-turn tool-call
sequence must answer four concrete questions the data-flow rules above deliberately leave open:

1. What complete provider item(s) must be replayed?
2. What compatibility key determines whether replay is legal?
3. Is replay replacement-based, latest-only, or an ordered accumulated sequence?
4. Which terminal outcomes produce reusable continuation state at all — does continuation from,
   say, a completed tool-use response differ in reusability from continuation attached to a
   failed or incomplete one?

using a real exchange (`request 1 → reasoning/tool call + continuation → tool result → request 2`,
verifying both the success path and the omission/incompatibility failure path). That experiment
does not determine whether the architecture needs a continuation facility at all, or how it fits
into request reconstruction — those are pinned above as language-neutral regardless of outcome,
since even a Case-A finding (ordinary semantic history alone turns out to suffice) just means the
facility stays unused for `codex-responses` until a provider that needs it arrives. Record the
verified answers here — the same treatment already given to the `auth.json` schema and OAuth
endpoints elsewhere in this proposal.

**Conformance coverage** (no new `conformance/` family needed — extends existing `session/` and
`agent/` families once the mechanism above is implemented): continuation present in a committed
response is reachable in the next reconstructed request; a discarded pre-commit retry attempt's
continuation is absent from reconstruction; a fork at sequence N reaches only continuation at or
before N; an API switch to one that does not consume Codex continuation leaves the historical
continuation logged but not selected or replayed, without failing solely because ineligible
continuation exists; an API that requires continuation with only incompatible continuation
available fails eagerly before the stream is returned; continuation from before a `session/reset`
remains auditable but is absent from post-reset reconstructed dispatch; continuation from a
compaction-superseded response remains auditable but is ineligible for future dispatch, while
continuation from a response preserved in compaction's retained tail stays eligible; and the
terminal assistant response together with its continuation references becomes observable as one
atomic logical settlement — never a half-settled state where one is reachable without the other.
These scenarios assert semantic reconstruction and selection, not artifact layout or provider wire
bytes, consistent with how wire fixtures are excluded from semantic conformance elsewhere in this
proposal.

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
   `encrypted_content` is treated separately (item 13 below) — reviewed evidence suggests it is
   likely required continuation state, not discardable telemetry, pending empirical verification.
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
13. `codex-responses` continuation state splits into a resolved piece and an open piece. Resolved:
    the `ProviderContinuation` facility's properties (API/compatibility identity,
    log-reconstructable, session-ancestry-aware, eager-fails when required-but-missing, sanitized
    non-payload metadata only in diagnostics) and its full production→logical-settlement→
    log-reference→request-reconstruction→replay data flow (no ghost continuation from discarded
    attempts; an explicit, atomic logical-settlement point distinct from the retry-commitment
    boundary — the assistant response and its continuation references become reachable together or
    not at all; continuation as an explicit component of content-addressed request reconstruction,
    not adapter-private memory; deterministic selection order; selection scoped to effective session
    lineage — one rule covering fork-ancestry scoping, reset-floored eligibility, and
    compaction-superseded-vs-retained-tail eligibility, matching §7's existing "compaction changes
    provider context, not storage" and reset-excludes-prior-surface principles rather than inventing
    new ones; API-mismatch disambiguation (now a two-part predicate: provider/API compatibility AND
    effective-lineage compatibility); never model-visible) are pinned as language-neutral regardless
    of outcome. A provider-hosted `previous_response_id` alone is explicitly rejected as a
    substitute, since it depends on remote state outside Minion's log. Open: the working hypothesis,
    backed by OpenAI's
    own reasoning-items guidance and observed turn-2 failure reports, is that `encrypted_content` is
    required opaque continuation state — but the exact provider item(s), compatibility key,
    replacement-vs-accumulated-sequence semantics, and which terminal outcomes produce reusable
    continuation at all await live verification against a real Codex multi-turn tool-call exchange
    before the `codex-responses` mapping section's payload details fully freeze.
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
17. Continuation conformance coverage is scoped to extend the existing `session/` and `agent/`
    families (no new `conformance/` family needed) once the mechanism is implemented: committed
    continuation reachable in reconstruction; discarded pre-commit-retry continuation absent;
    fork-boundary scoping; an ineligible-API-switch leaving continuation logged but unselected
    (not "dropped" — the log is append-only, nothing is deleted); incompatible-continuation eager
    failure; reset-floored eligibility (auditable, absent from post-reset dispatch); compaction
    lineage eligibility (superseded response's continuation ineligible but auditable, retained-tail
    response's continuation still eligible); atomic settlement of the terminal assistant response
    with its continuation references (never observable half-settled). Asserts semantic
    reconstruction/selection, not artifact layout or wire bytes.
