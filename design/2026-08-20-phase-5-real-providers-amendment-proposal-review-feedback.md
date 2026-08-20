<!--
TRACKING NOTE — 2026-08-20 — LATEST
Latest disposition after reviewing the third revision of the Phase 5 amendment and the full review/counter-review chain:
- The ProviderContinuation data-flow gap is now resolved in the proposal: attempt-local observation, durable commit, content-addressed log/reference state, deterministic reconstruction, fork boundaries, compatibility filtering, and matching replay are pinned.
- Two amendment-level items remain before freeze: (1) add atomic logical settlement of the terminal assistant response with any continuation references derived from the same physical attempt; and (2) complete live Codex verification of exact replay item(s), compatibility key, terminal-outcome reuse rules, and replacement/latest/accumulation semantics.
- Distinguish two different "commit" boundaries in the text: first-public-chunk commits a physical attempt against retry; terminal logical settlement makes assistant response + continuation references durably reachable. The former must not imply durable continuation publication.
- Rust Phase 2 still needs a pre-implementation seam revision for restartable pre-commit attempts and extensible reconstructed provider state, but this review does NOT endorse making operational provider I/O an eager pre-stream failure. The frozen never-raises contract still requires expected provider/network failures after AssistantStream exists to settle in-band.
- Usage.cost representation remains a separate pre-publication Rust vocabulary decision, not a blocker on this amendment.
-->

## Review verdict — Phase 5 real-provider design amendment

**Verdict: approve the direction, but do not merge the amendment into the frozen design exactly as written yet.**

The proposal follows the right cross-language amendment process and correctly treats these provider decisions as changes that need review before becoming binding on Python and Rust. fileciteturn30file0L3-L12 The current design is explicitly language-neutral across implementations, so promoting genuinely observable provider semantics is appropriate. fileciteturn32file0L6-L12

Most of the amendment is strong and consistent with the frozen design. I see:

```text
2 issues to resolve before merge
4 substantive wording/semantic corrections
several smaller taxonomy clarifications
```

No architectural rewrite is needed.

---

# 1. BLOCKER — `codex-responses` reasoning continuation is not sufficiently resolved

The proposal says:

```text
reasoning_text
    → ThinkingDelta / ThinkingBlock

reasoning summary
encrypted_content
    → recognized but no V1 projection

multi-turn reasoning continuation
    → later vocabulary extension
```

fileciteturn30file0L64-L68

The distinction between visible reasoning text and provider-specific continuation data is correct.

The unresolved question is whether `encrypted_content` or another opaque reasoning item is required to make the **next Responses request semantically equivalent to the previous provider interaction**.

That matters immediately because Phase 5 is not just a one-shot model demo. The existing agent loop already performs:

```text
request
    → tool call
    → tool result
    → second model request
```

and Phase 5 is explicitly where that working mock-driven loop first contacts real providers. fileciteturn31file0L21-L45

Therefore this cannot simply be deferred on the assumption that it is an optional future "multi-turn reasoning" feature.

Before merging, establish one of these:

### Case A — continuation metadata is not required

If a second Codex/Responses request can reconstruct equivalent continuation solely from Minion's ordinary semantic message/tool history, then the current V1 deferral is valid.

State that explicitly:

> V1 has verified that `codex-responses` can execute ordinary multi-step agent/tool turns without replaying reasoning-summary or encrypted continuation data. Those fields therefore have no V1 semantic projection.

### Case B — continuation metadata is required

Then it cannot simply be discarded.

But it still should **not** become `ThinkingBlock`.

Instead introduce something like provider-opaque continuation state:

```text
provider continuation artifact
    log-only
    immutable
    associated with the response/request
    replayed only to the same provider API
    never projected as user/model-visible ThinkingBlock
```

That actually fits the existing architecture well: Minion already distinguishes semantic surface from log-only state and requires anything sent back to the model to be reconstructable from the log. The frozen design says anything reaching a model request must be reconstructable. fileciteturn33file3L113-L118

So the question is not:

> Should encrypted reasoning become ThinkingBlock?

Definitely not.

The question is:

> Is opaque provider continuation required request state?

That must be answered before freezing the Codex mapping.

---

# 2. BLOCKER / required reconciliation — cancellation wording currently overclaims the frozen design

The amendment says:

> Live mid-stream cancellation is out of scope ... §6's loop is cooperative, checked between steps.

fileciteturn30file0L111-L116

The implementation observation may be true, but the **current frozen design does not clearly establish that language-neutral rule**.

In fact the frozen design currently says:

```text
after stream return:
    cancellation → terminal error/aborted in-band
```

fileciteturn33file2L73-L87

and it also lists:

```text
agent/cancellation
```

as canonical language-neutral conformance coverage, while Phase 3 explicitly includes cancellation. fileciteturn33file0L28-L39 fileciteturn33file0L51-L58

So before merging the new statement, reconcile what the existing canonical `cancellation` behavior actually means.

There are two possibilities:

### If existing cancellation really is boundary-only/cooperative

Then promote that explicitly:

> Agent cancellation currently prevents subsequent work at cooperative loop boundaries; V1 does not require asynchronous interruption of an already-running provider stream.

Then the Phase 5 deferral is sound.

### If existing conformance means an active model stream may be cancelled

Then the amendment cannot defer that behavior without changing an already-frozen semantic rule.

In that case either:

```text
implement active provider cancellation now
```

or:

```text
deliberately amend the existing cancellation contract + scenario
```

Do not rely on the current Python implementation as proof of the language-neutral contract.

This is exactly the sort of Python-vs-spec distinction the project has been careful about elsewhere.

---

# 3. SUBSTANTIVE — wire mappings can be normative; internal adapter structure should not be

The opening currently says:

> any implementation should treat them as two independent translations rather than one format-parameterized abstraction.

fileciteturn30file0L23-L29

The first half is correct:

```text
Chat Completions semantics
    ≠
Responses semantics
```

The second half unnecessarily constrains implementation architecture.

A Rust implementation could legitimately share:

```text
generic helpers
state-machine components
serialization infrastructure
```

while still producing exactly the correct behavior for each API.

The language-neutral design should specify:

> The two APIs have independently specified mappings. No behavior may be inferred for one API from the mapping of the other.

Not:

> Implementations must internally build two independent translation abstractions.

Recommended replacement:

> `openai-completions` and `codex-responses` have independently specified wire mappings because their observable protocols differ materially, including tool-result representation and streaming event structure. Implementations may share internal helpers, but sharing must not introduce semantic coupling between the two mappings.

That preserves implementation freedom.

---

# 4. SUBSTANTIVE — "pure, I/O-free translation" conflicts with artifact materialization

The proposal opens with:

> provider-neutral vocabulary → wire format and wire events → StreamChunk are pure, I/O-free translations.

fileciteturn30file0L23-L25

But the image mapping later says an immutable artifact may need to be materialized into a provider-fetchable URL. fileciteturn30file0L41-L44

Materialization may involve:

```text
artifact read
upload
signed URL generation
provider file creation
```

which is not pure translation.

The frozen design already gets the abstraction right:

```text
semantic reference
    = immutable identity

provider upload handle / signed URL / base64
    = wire-level detail
```

fileciteturn32file0L407-L420

So split the language more carefully.

Recommended:

> The structural encode/decode mappings are deterministic and independently testable from transport. Any provider-specific preparation that requires I/O — for example materializing an immutable artifact into a provider upload handle or fetchable URL — occurs before or around structural encoding and does not mutate the semantic `ImageBlock.reference`.

Then implementations can have:

```text
semantic Request
    ↓
provider preparation          ← may perform I/O
    ↓
prepared provider values
    ↓
pure structural encoder
    ↓
wire request
```

This also keeps Section D's codec tests meaningful.

---

# 5. SUBSTANTIVE — unsupported `ThinkingBlock` needs an explicit side of the never-raises boundary

The amendment correctly changes Chat Completions from silent dropping to explicit failure:

```text
ThinkingBlock
    → unsupported-content error
```

fileciteturn30file0L36-L45

But "error on encode" is not enough for a cross-language semantic rule.

The frozen design has a very explicit boundary:

```text
before stream returned
    → invalid request/caller/config errors raise

after stream returned
    → operational failures ride the stream
```

fileciteturn33file2L75-L87

A request containing content that the selected API cannot represent is a deterministic request-compatibility error, not a provider/network runtime failure.

So pin it:

> Unsupported provider-neutral content is validated before the stream is returned. Attempting to send a `ThinkingBlock` through `openai-completions` therefore fails eagerly as an unsupported-request/content error unless the selected provider explicitly declares a compatible mapping.

That avoids:

```text
Python → eager error
Rust   → streamed error
```

while both claim compliance.

---

# 6. SUBSTANTIVE — unknown `finish_reason` has no actual StopReason mapping yet

The proposal says:

> unknown finish reason is preserved diagnostically, never silently coerced to `stop`.

fileciteturn30file0L47-L51

Correct principle, incomplete semantic rule.

`StopReason` is a closed provider-neutral vocabulary:

```text
pending | stop | length | tool_use | error | aborted
```

fileciteturn32file0L382-L390

So when an unknown provider finish reason arrives, an implementation must still select a semantic terminal state.

Otherwise:

```text
Python:
    unknown → error

Rust:
    unknown → stop + diagnostic

```

could both claim they "preserved it diagnostically."

I recommend:

```text
unknown provider finish reason
    → StopReason.error
    → provider reason preserved in diagnostic
```

unless there is a strong reason for another mapping.

Likewise specify unknown Responses completion states.

"Preserve diagnostically" should supplement the semantic result, not replace it.

---

# 7. SUBSTANTIVE — `incomplete → length` is too broad as currently stated

The Responses mapping currently states:

```text
incomplete → length
```

fileciteturn30file0L70-L76

The proposal does not establish that every form of provider-level incompleteness semantically means token/output-length exhaustion.

That mapping should be based on the **incomplete reason**, not merely the outer state.

Safer normative rule:

```text
completed + pending function call
    → tool_use

completed otherwise
    → stop

incomplete because output/token limit
    → length

incomplete for another recognized operational reason
    → explicitly mapped according to that reason

unknown/unrepresentable incomplete reason
    → error + diagnostic

cancelled
    → aborted

failed
    → error
```

If real API verification establishes that V1 can only observe token-limit incompleteness for the supported Codex flow, state that verified restriction explicitly.

Do not encode the broader equivalence:

```text
incomplete == length
```

without evidence.

---

# 8. APPROVE — retry commitment rule

This section is good and should be promoted.

The two-gate rule is particularly strong:

```text
retry iff:

    zero public StreamChunks emitted
    AND
    failure classified transient
```

fileciteturn30file0L91-L108

This is better than vague "retry before content" semantics because:

```text
zero chunks
    → failed attempt completely invisible

first StreamStart
    → physical attempt committed
```

and it prevents retrying malformed protocol data merely because it happened early.

I would keep this essentially unchanged.

One small addition:

> Retry count, backoff, jitter, and the exact provider-specific classification of retryable server statuses are implementation/provider policy unless separately standardized.

The language-neutral rule needs the commitment boundary and failure-class distinction, not necessarily identical sleep schedules across Python and Rust.

---

# 9. APPROVE WITH SMALL GENERALIZATION FIX — credential ownership

The ownership principle is strong:

```text
external credential
    → read/use current access token
    → don't mutate external store
    → don't independently rotate its OAuth state

self-owned credential
    → refresh
    → persist every replacement
```

fileciteturn30file0L120-L143

This closes a genuine hole in the frozen auth seam, which currently only says that Codex CLI credentials and interactive PKCE are loaders behind one auth abstraction. fileciteturn33file3L99-L109

I would change only the universal wording.

Instead of:

> never independently refreshes it and never writes back to that store

use:

> does not independently refresh or mutate externally-owned credentials **unless the owner exposes an explicit supported interoperability contract granting that authority**.

Why?

Because the useful general rule is:

```text
ownership / authority determines mutation rights
```

not:

```text
credentials originating anywhere external can never be refreshed by Minion under any future supported protocol
```

For Codex CLI's current file-based interop, the outcome remains exactly the same:

```text
read-only
no independent refresh
```

The exception simply keeps the generalized design correct if a future application provides a supported shared credential service.

---

# 10. Testing philosophy is good, but classify it as verification policy, not runtime semantics

The fixture section is well designed:

```text
pure codec tests
recorded wire fixtures
optional live verification
```

and correctly keeps provider-wire fixtures outside the existing three semantic conformance families. fileciteturn30file0L148-L183

That aligns with the frozen design's existing split: adapter wire-format details are Tier-2 implementation tests, whereas shared externally meaningful semantics belong in language-neutral conformance. fileciteturn33file0L40-L50

However, the proposal's introductory text says the entire amendment is "normative content a Rust implementation is equally bound by." fileciteturn30file0L8-L16

I would distinguish:

```text
wire mapping / retry / auth ownership
    → language-neutral behavioral rules

fixture methodology
    → shared project verification policy

Python/Rust fixture representation
    → implementation-specific
```

All implementations should verify the same classes of behavior, but "store raw bytes in this fixture style" is not part of the runtime's semantic contract.

That taxonomy matters because your project already distinguishes normative semantic rules from executable compatibility cases. fileciteturn31file5L388-L402

---

# 11. The claim that wire fixtures are "implementation-specific by nature" is too strong

The proposal says raw payloads are implementation-specific because they are tied to one implementation's HTTP client. fileciteturn30file0L162-L167

I agree with the conclusion:

> Do not put them into canonical Minion semantic conformance.

But not with the stated reason.

A raw SSE/HTTP body such as:

```text
event: response.output_text.delta
data: {...}
```

is provider protocol data, not inherently Python-httpx or Rust-reqwest data.

A single sanitized wire corpus **could** be consumed by both implementations.

So change:

> necessarily per-implementation / tied to one HTTP client

to:

> not part of shared semantic conformance. Implementations may maintain separate fixture corpora, or may deliberately share a provider-wire corpus; either choice is test infrastructure and does not make provider wire bytes part of the Minion behavioral specification.

This matches the proposal's own better statement later:

> a shared wire-fixture corpus ... is a separate explicit decision.

Keep that part.

---

# 12. Raw bytes fixture rule is good, but avoid making network chunk boundaries normative

The amendment correctly says storing only parsed `{event,data}` pairs bypasses SSE framing. fileciteturn30file0L169-L183

Keep that.

But distinguish:

```text
raw protocol bytes
```

from:

```text
exact TCP/httpx/reqwest chunk segmentation
```

SSE semantics must survive arbitrary transport chunking.

So fixture infrastructure should ideally test the same raw bytes under varied segmentation:

```text
one large chunk
one byte at a time
boundaries inside UTF-8 / JSON / SSE lines
```

rather than treating the segmentation observed during recording as provider semantics.

That's implementation-test detail, but worth adding to the testing guidance.

---

# 13. One missing amendment topic: cost is deliberately still unresolved

The frozen `Usage` vocabulary explicitly includes computed cost. fileciteturn32file0L382-L390

The proposal does not discuss it.

That is okay **only if the amendment records the deferral explicitly**, because Phase 5 is now elaborating real-provider semantics and someone reading it could reasonably assume `Usage.cost` is part of the provider work.

Add a short statement:

> Phase 5 preserves the provider-neutral `Usage.cost` field and all token categories required for future computation, but does not standardize a pricing catalog or local cost-computation policy. Pricing source, provider/model precedence, historical price versioning, and unknown-model behavior remain deferred.

This is not a blocker, but it closes a known design decision from the Phase 5 review instead of letting it disappear.

---

# 14. One missing amendment topic: API/provider config policy

The proposal intentionally excludes Python config classes, which is correct.

But one language-neutral policy from Section E is worth promoting:

```text
OpenRouter
Ollama
LM Studio
generic OpenAI-compatible

    → one openai-completions API mapping
    → endpoint/auth/model configuration differs
```

The frozen design already says this at the API/provider split level. fileciteturn32file0L439-L450

No need to duplicate file/config structure.

If you want to close the V1 auth resolution decision language-neutrally, a single sentence is enough:

> Real-provider plugins consume already-resolved authentication configuration; V1 does not define an additional provider-specific environment-variable or credential fallback chain.

But this can also remain implementation-plan material because it is configuration policy rather than wire semantics.

I would **not block the amendment on it**.

---

# Proposed merge disposition

## Approve essentially unchanged

```text
ThinkingBlock must not silently disappear
role-aware Chat Completions encoding
tool-call fragmented accumulation
Responses item-state decoding
function_call_output tool results
reasoning_text distinct from summaries/encrypted state
first-public-chunk retry commitment
two-gate retry eligibility
retry exhaustion stays in-band
credential ownership principle
three-tier provider verification strategy
wire fixtures excluded from semantic conformance
sanitization preserves protocol structure
fixture provenance
```

## Change before merge

```text
1. Verify/resolve whether Codex opaque reasoning continuation is required
   for ordinary Phase-5 multi-step/tool continuation.

2. Reconcile live-stream cancellation deferral with the existing frozen
   cancellation contract and canonical cancellation scenario.

3. Make unsupported ThinkingBlock an explicitly eager request-validation error.

4. Define actual StopReason for unknown Chat Completions finish reasons
   (recommend error + diagnostic).

5. Map Responses incomplete by reason, not blindly incomplete→length.

6. Remove implementation-architecture requirement that the two adapters
   must internally be independent abstractions.

7. Separate pure structural encoding from potentially-I/O-bearing artifact
   materialization.

8. Generalize credential ownership around explicit mutation authority.

9. Reword provider fixtures as non-semantic-conformance rather than
   inherently HTTP-client-specific.

10. Explicitly record cost-computation deferral.
```

---

# Final verdict

**The amendment is good enough to continue, but I would not mark it reviewed/frozen yet.**

The two items I would require answers for before merge are:

### A. Codex continuation

```text
Can a normal multi-step Codex agent/tool turn be reconstructed correctly
without reasoning-summary/encrypted continuation state?
```

If yes, document the verified boundary.

If no, model the required opaque continuation as provider-specific logged request state rather than `ThinkingBlock`.

### B. Cancellation

```text
What exactly does the already-frozen agent/cancellation semantic scenario mean?
```

If it is cooperative boundary cancellation, explicitly say so and the Phase-5 deferral is valid.

If it includes active LLM interruption, Phase 5 cannot defer that without a deliberate amendment of the existing rule.

Once those two are resolved and the six smaller semantic wording changes above are applied, I would **approve promotion into the frozen language-neutral design** and then have both Python and Rust implementation plans reference the promoted rules rather than independently restating them.

---

# Response — verified against the codebase and against OpenAI's actual API behavior

I did not accept this at face value. Where the review makes a checkable factual claim, I checked
it — against the real `minion-agent-python` code (I built the cancellation mechanism myself,
earlier in this session, executing Plan 3) or against OpenAI's published API behavior (two
targeted searches). Verdicts below; agree means independently confirmed, not just plausible.

## Blocker 1 — Codex reasoning continuation: agree, and the evidence is stronger than the review states

I initially leaned toward thinking this was overstated — minion-agent already resends full message
history every request (stateless by construction), which is exactly the "manually managing
context" mode a reasoning-continuation requirement would live inside, so I assumed it would degrade
gracefully rather than break. I checked rather than assumed. It does not degrade gracefully:

- OpenAI's own reasoning-items guide states plainly that these items should be included in the
  input to the Responses API for subsequent turns of a conversation when manually managing
  context. `encrypted_content` exists specifically so a stateless caller can replay reasoning
  across turns without server-side session storage — it is not incidental telemetry.
- Real-world evidence of the failure mode exists: `openai/openai-python#3008`, "Responses API:
  multi-turn conversations 400 on turn 2 when passing response.output back as input," and
  `openai/codex#3841`, "Missing previous_response_id support breaks multi-turn conversations."

So this is not a hypothetical quality concern — it is plausibly a request failure, not merely
degraded reasoning, for a Codex agent's second turn once tool calls are involved. Agree this blocks
merge. I would go further than the review's even-handed Case A/Case B framing: given what I found,
I would bet on Case B (opaque, log-only, replayed-only-to-Codex continuation state) being the
actual answer, not Case A. The amendment should say so as a working hypothesis, with empirical
verification against a real Codex multi-turn tool-call sequence as the implementation-time task
that confirms or overturns it — the same treatment already given to the `auth.json` schema and the
OAuth endpoints elsewhere in this proposal, not a new category of uncertainty.

## Blocker 2 — cancellation wording: the substance is already resolved; this is a citation fix, not an open question

I have direct, first-hand knowledge here the reviewer did not have access to: I built and reviewed
`AgentLoop.cancel()` myself, executing Plan 3 earlier in this session. Checked again just now
against the live code:

```
src/minion_agent/agent_loop/driver.py
  self._cancelled = False        # line 69
  def cancel(self) -> None:      # line 98
      self._cancelled = True     # line 105
  ...
  if self._cancelled:            # line 149, checked between steps in the turn loop
```

This is unambiguously cooperative, boundary-only cancellation — a flag checked between steps, never
an interrupt of an in-flight request. There is no code path in this codebase, today, that closes a
live provider stream mid-flight. The master design's line 431 (the never-raises table's
"cancellation... terminates the stream in-band" entry) describes the consequence if a stream is
cancelled while active — it does not assert that an active-interruption mechanism exists or is
required. Line 1112's `agent/ ... cancellation` is the conformance family name for exactly the
mechanism above (`tests/agent_loop/test_cancellation.py`, which I wrote), not evidence of a
different, active-interruption contract.

So: Case A, confirmed, not merely asserted. This does not need "either implement active
cancellation or amend the existing rule" as the review frames it — the existing rule already is
cooperative, and the fix is exactly the review's own suggested sentence, backed by a citation to
the real mechanism rather than left as an unsourced claim. Downgrading this from BLOCKER to an
immediate, resolvable-now wording fix — the review was right to demand it be stated explicitly,
wrong to treat it as still open.

## Point 7 — `incomplete → length` too broad: agree, verified

Checked directly: `incomplete_details.reason` on the Responses API really does carry at least two
distinct values, `max_output_tokens` and `content_filter` (OpenAI's own API reference). Collapsing
both into `length` would misclassify a content-filtered response as a token-limit issue — a
different failure a caller would want to handle differently. Agree with the reason-keyed mapping;
`content_filter` and any other non-length reason should map to `error`, not `length`.

## Point 6 — unknown `finish_reason` needs an actual `StopReason`: agree, verified

Checked against `llm/messages.py`: `StopReason` is exactly the closed six-value enum the review
describes, and `AssistantMessage.stop_reason` is a mandatory field of that type — there is no slot
for unrecognized. "Preserved diagnostically" was never sufficient as a complete rule; it has to
name which of the six values an implementation lands on. Agree with `error` as the default, message
preserved as diagnostic detail.

## Point 4 — "pure, I/O-free" contradicts materialization: agree, verified against my own text

Checked the committed file: line 24 does say "pure, I/O-free translations" as an unqualified
blanket statement, three paragraphs before the image row admits materialization may need I/O. Real
internal inconsistency in my own draft, not a misreading. Accepting the review's split (structural
encode/decode is pure; provider-specific artifact preparation is a separate, I/O-bearing step that
occurs before structural encoding and never mutates the semantic reference).

## Points 8, 12, 13, 14 — confirmed absent from the committed file, not just under-emphasized

Grepped directly rather than trusting recollection:

- Point 8 (retry policy is implementation-specific, not identical schedules) — the qualifier is
  genuinely missing from the committed retry section.
- Point 12 (fixture testing must cover varied chunk segmentation, not just raw bytes) — this was in
  the chat discussion that produced this proposal and did not survive the trim into the committed
  file. Real loss, should be restored.
- Point 13 (cost deferral) — no mention of `Usage.cost` anywhere in the committed file. Silently
  absent, not explicitly deferred, exactly the risk the review names.
- Point 14 (API-key resolution has no fallback chain) — also discussed in chat, also dropped in the
  trim. Agree the one-line policy statement is language-neutral and belongs here; the rest (actual
  config classes) correctly stays out as Python-plan material.

All four: agree, will restore/add.

## Points 3, 5, 9, 10, 11 — wording/taxonomy corrections, agree

No factual claim to independently verify beyond internal consistency, which holds in each case:

- Point 3 (do not mandate two internally-independent implementation abstractions) — fair; the
  normative content is behavioral independence between the two mappings, not a constraint on how
  Rust structures its own code.
- Point 5 (`ThinkingBlock` rejection belongs explicitly on the eager side) — agree; it is
  structurally a caller-bug condition (unrepresentable content cannot be dispatched), so it belongs
  with `UnknownModelError` on the pre-stream-return side of the existing boundary table, and the
  draft never said so explicitly.
- Point 9 (generalize credential ownership around explicit granted authority rather than a blanket
  never) — agree this is a real generalization, not scope creep: it changes nothing about Codex's
  current behavior (still read-only, still no independent refresh), since reverse-engineering
  `AuthDotJson` from open source is not an explicit supported interoperability contract — it only
  future-proofs the rule if one is ever offered.
- Point 10 (separate runtime semantic rule from shared verification policy) — agree; the intro line
  calling everything in the proposal normative content Rust is equally bound by conflated the two,
  and fixture methodology and runtime behavior are genuinely different categories.
- Point 11 (wire fixtures are not inherently HTTP-client-specific; the real reason to exclude them
  is they are test infrastructure, not spec) — agree, and this correction also fixes an internal
  contradiction the review caught accurately: the document's own later sentence about a possible
  shared Python/Rust fixture corpus already contradicted the earlier "necessarily tied to one HTTP
  client" framing.

## Disposition

Accepting all fourteen numbered points. Blocker 1 (Codex continuation) is a real blocker requiring
resolution before merge, and the resolution should be biased toward opaque continuation state over
not required, given the search evidence above. Blocker 2 (cancellation) is downgraded to a
same-session wording fix, backed by a direct citation to `driver.py`, since there is first-hand
confirmation the underlying rule was never actually in question. The six substantive corrections
(3 through 7, plus the pure-I/O-free split) and the four confirmed-absent items (8, 12, 13, 14) all
get applied. Proceeding to revise `2026-08-20-phase-5-real-providers-amendment-proposal.md` next,
pending confirmation.

---

# Rust-side review of the revised proposal

## Verdict

The revision at `528971c` incorporates nearly all earlier review corrections correctly. From the
Rust side, do not freeze it yet: the Responses continuation model remains under-specified, and that
decision changes both session/request reconstruction and the Rust adapter interface.

This is the right time to make those changes. The Rust repository has no LLM/provider module yet,
so the Phase 2 contracts can still be revised without migrating a published API.

## Corrections now resolved

The revised proposal now correctly pins:

- independently specified Chat Completions and Responses behavior without forbidding shared Rust
  helpers;
- deterministic structural codecs separated from potentially I/O-bearing artifact preparation;
- eager rejection of unsupported `ThinkingBlock` content;
- unknown Chat Completions finish reasons as `StopReason.error` plus diagnostics;
- Responses incompleteness by specific reason rather than blanket `incomplete → length`;
- first-public-chunk retry commitment plus transient-failure classification;
- implementation-specific retry schedules;
- cooperative step-boundary cancellation as the current V1 capability;
- credential mutation by explicit ownership/authority;
- provider fixtures as verification policy rather than semantic conformance;
- arbitrary raw-byte segmentation tests;
- explicit cost-policy and API-key-fallback deferrals.

Those items no longer need further Rust-side changes in the amendment.

## 1. Responses continuation should be specified as Case B

The revised text still treats Case A versus Case B as open pending a live experiment. The live
multi-step tool-call verification is worthwhile, but the normative model should now be biased more
strongly than a working hypothesis. OpenAI's Responses documentation says reasoning items should
be included in later inputs when an application manually manages context and exposes
`encrypted_content` for stateless replay. A provider-hosted `previous_response_id` alone is not an
adequate Minion source of truth because request reconstruction must not depend solely on mutable,
expiring, or unavailable remote state.

Recommended language-neutral shape:

```text
ProviderContinuation
    API identity
    compatibility/version identity
    immutable artifact reference
    originating response/turn association
    deterministic replay order
```

Required rules:

- continuation is log-only and never a `ThinkingBlock`;
- its complete replay payload is reconstructable from Minion's artifact store;
- only a matching API/compatibility identity may consume it;
- required-but-missing or incompatible continuation fails eagerly rather than being silently
  omitted;
- it follows session ancestry and fork boundaries independently of model-visible surface
  projection;
- reset or compaction of the visible surface cannot remove continuation still needed to
  reconstruct a later request;
- opaque continuation is sensitive provider state and is excluded from ordinary telemetry and
  diagnostics;
- the artifact stores the complete provider item required for replay, not merely a detached
  `encrypted_content` scalar.

The exact bytes and Rust storage type are implementation details. Rust must not represent this as
`Any` or as a provider-specific `ContentBlock`: it has to remain serde/log reconstructable while
staying outside the model-visible vocabulary.

The live verification should determine the exact replay payload and compatibility key, not whether
the architecture needs a continuation slot at all.

Reference: OpenAI Responses streaming/reference documentation describes reasoning-item replay and
`encrypted_content`:
<https://platform.openai.com/docs/api-reference/responses-streaming/response/refusal/delta>.

## 2. The Rust Phase 2 adapter contract must change

The current Rust plan defines a synchronous, one-attempt adapter:

```rust
fn stream(&self, request: Request)
    -> Result<RawAssistantStream, LlmStartError>;
```

That shape cannot cleanly support the revised design's:

- asynchronous credential loading or self-owned credential refresh;
- I/O-bearing artifact materialization/provider upload;
- provider-continuation preparation;
- transparent creation of a replacement physical attempt after a transient pre-commit failure.

Rust should use an asynchronous eager phase and a restartable internal attempt abstraction:

```text
validate semantic request
    ↓
asynchronous provider preparation/start
    ↓
Result<AssistantStream, LlmStartError>
    ↓
AssistantStream owns retryable attempt state
```

The public outcome remains unchanged: once returned, `AssistantStream` yields only `StreamChunk`
values. Internally, however, a one-shot `source: RawAssistantStream` cannot centrally enforce the
retry rule. The wrapper needs a typed attempt factory and typed failure classification rather than
string matching.

Commitment occurs when `poll_next` exposes the first public chunk, including `start`. Dropping or
fusing the stream must cancel pending retry timers/requests; no retry work may continue in the
background after fusion. Backoff tests should use injected deterministic time/randomness rather
than wall-clock sleeps.

This is a Rust implementation-plan correction, not an additional language-neutral runtime rule.

## 3. Keep typed semantic APIs without closing provider wire vocabularies

The Rust public API should remain strongly typed, but provider event discriminators should not be
a closed serde enum that rejects every newly introduced provider event.

Decode the outer wire envelope first as:

```text
event-name string
raw JSON payload
```

Then let the API-specific state machine classify it as projected, recognized-but-unprojected,
diagnostic/ignorable, or a terminal protocol violation. Chat Completions and Responses should have
separately specified private state machines, while sharing framing, JSON, artifact, and diagnostic
helpers where useful.

## 4. Pin malformed fragmented tool-call behavior

Tool-call fragments are untrusted provider input. Rust should accumulate them in checked maps keyed
by call index or `item_id`, not resize sparse vectors from provider-controlled indices.

At finalization:

- argument fragments must parse as JSON;
- the result must satisfy the provider-neutral tool-call argument shape (currently a JSON object);
- conflicting IDs/names, impossible index reuse, incomplete finalization, invalid JSON, or a
  non-object argument value settle as protocol errors;
- no partial wire item becomes an executable semantic tool call.

This behavior is externally observable and should be pinned sufficiently for Python and Rust to
settle malformed streams the same way.

## 5. Encode credential authority in Rust types

Rust should not hand an external token and optional refresh token to a generic refresher. The auth
boundary should carry an explicit capability:

```text
external/read-only
self-owned/refreshable + owned persistence capability
explicit interoperability authority
```

This makes independent refresh of Codex CLI credentials structurally unavailable. Secret-bearing
types should not derive ordinary `Debug` or `Serialize`.

Expiry discovered during asynchronous credential preparation is an eager start error. An
authentication failure received after a public stream exists settles in-band. Both may share a
diagnostic category without crossing the never-raises boundary.

The revised rule that plugins consume already-resolved authentication is particularly appropriate
for Rust: the library should not read process-global environment variables implicitly.

## 6. One fixture wording contradiction remains

The revised fixture body correctly says a sanitized provider-wire corpus can be shared and is not
inherently tied to Python's or Rust's HTTP client. The introductory paragraph still says fixtures
are "necessarily per-implementation artifacts (different HTTP clients, no shared wire bytes format
implied)." Those statements conflict.

Replace that introductory sentence with:

> This is shared verification policy. Implementations may keep separate fixture corpora or
> deliberately share provider-wire fixtures; fixture representation remains test infrastructure,
> not Minion semantic conformance.

For Rust, a replay transport should preserve status, relevant headers, and raw body bytes, then
feed those bytes through the production framing and decoding stack under varied segmentation.

## 7. Cost-policy deferral still requires a Rust representation decision

Deferring pricing catalogs and computation is correct, but Rust needs a stable public `Usage.cost`
representation before publishing the type. Cost should be optional while uncomputed, and its
eventual monetary representation should be exact rather than `f64` (for example exact decimal or
amount-plus-currency).

This does not block the amendment, but it must be settled before the Rust provider-neutral
vocabulary becomes a public compatibility commitment.

## Rust merge disposition

Approve promotion after:

1. provider continuation is pinned as log-only, content-addressed, compatibility-keyed request
   state, with live verification determining its exact wire payload;
2. the remaining fixture-introduction contradiction is corrected;
3. the Rust Phase 2 plan is revised to use asynchronous eager start and restartable pre-commit
   attempts;
4. malformed fragmented tool-call settlement and open wire-event decoding are accounted for in
   the Rust provider plan;
5. `Usage.cost` representation is settled before the Rust public type is implemented.

No change is required to the approved provider-neutral stream outcome: consumers observe zero or
more non-terminal chunks, exactly one terminal chunk, and no iteration errors.
# Latest review of the revised proposal — 2026-08-20

## Verdict

Do not freeze the amendment yet.

The latest proposal successfully incorporates nearly all objections from the original review and
counter-review. One primary language-neutral semantic blocker remains — Responses continuation
state — together with one required fixture-wording correction and a newly identified gap in the
settlement of malformed fragmented tool calls.

## Original objections now resolved

The revised proposal now correctly specifies:

- independently specified Chat Completions and Responses behavior without prohibiting shared implementation helpers;
- deterministic structural codecs separated from I/O-bearing artifact preparation;
- eager, pre-stream rejection of an unsupported `ThinkingBlock`;
- unknown Chat Completions `finish_reason` as `StopReason.error` plus diagnostics;
- Responses `incomplete` mapping according to its specific reason rather than blanket conversion to `length`;
- `completed` as `tool_use` when a finalized function call awaits execution;
- retry only before the first public chunk and only for transient transport/status failures;
- retry schedules and exact retryable-status classification as provider/implementation policy;
- cooperative step-boundary agent cancellation while preserving existing `aborted` semantics;
- credential mutation according to ownership or explicitly granted authority;
- fixture methodology as verification policy rather than runtime semantics;
- raw-wire replay under varied transport segmentation;
- explicit deferral of cost computation; and
- no provider-specific API-key fallback chain in V1.

The original cancellation objection is therefore resolved and is no longer a blocker.

## Remaining blocker — Responses continuation state

The proposal correctly recognizes that opaque continuation data is distinct from `ThinkingBlock`,
must be immutable and log-reconstructable, and may be required for real multi-step tool-call
continuation. It still leaves Case A versus Case B open and models Case B only at a high level.

The design should reserve a provider-opaque continuation facility now, while live verification
determines its exact wire contents. The minimum language-neutral shape should cover:

```text
ProviderContinuation
    API identity
    compatibility/version identity
    originating response/turn association
    immutable artifact reference
    deterministic replay order
```

Required rules:

- retain the complete replayable provider item, not merely a detached `encrypted_content` scalar;
- missing required or incompatible continuation fails eagerly;
- continuation follows session ancestry and fork boundaries;
- visible-history reset or compaction cannot remove continuation still needed to reconstruct a later request;
- continuation cannot be projected into a different provider/API mapping;
- sensitive opaque payloads are excluded from ordinary diagnostics and telemetry; and
- provider-held `previous_response_id` is not the sole reconstructable source of truth.

The live tool-call experiment should determine the minimum replay payload and compatibility key,
not whether the architecture has a place to retain provider continuation state.

## Required editorial correction — fixture wording

The fixture introduction still calls fixtures "necessarily per-implementation artifacts," while
the body correctly says a sanitized provider-wire corpus may be shared. Replace the introductory
claim with wording such as:

> Implementations may maintain separate fixture corpora or deliberately share provider-wire
> fixtures; fixture representation remains test infrastructure rather than Minion semantic
> conformance.

## New substantive issue — malformed fragmented tool calls

The proposal describes fragment accumulation but does not fully pin how invalid or contradictory
accumulated state settles. This is externally observable and must not diverge between Python and
Rust. Specify that:

- conflicting IDs or function names are protocol errors;
- impossible index or `item_id` reuse is a protocol error;
- finalized arguments must parse as JSON;
- arguments must satisfy the provider-neutral tool argument shape, currently a JSON object;
- incomplete finalization is a protocol error;
- no partial or malformed provider item becomes an executable semantic tool call; and
- once a stream exists, these failures settle in-band as `StopReason.error` with safe diagnostics.

Using checked maps rather than blindly resizing sparse arrays from provider-controlled indices is
appropriate implementation guidance, rather than an additional language-neutral structure rule.

## Rust-plan follow-ups

The Rust implementation plan still needs:

- asynchronous eager preparation/start;
- restartable pre-commit attempt construction;
- typed retry/failure classification;
- open provider wire-event envelopes rather than closed enums that reject every new event;
- credential authority represented explicitly in types; and
- an optional, exact monetary representation for `Usage.cost` rather than `f64`.

These plan changes do not alter the approved public stream outcome, but should be completed before
the corresponding Rust public contracts are implemented.

## Latest disposition

```text
BLOCKING
1. Pin the provider-opaque continuation model and verify its exact replay payload.
2. Specify malformed fragmented tool-call settlement consistently across languages.

REQUIRED EDITORIAL FIX
3. Remove the fixture-corpus contradiction.

RESOLVED
All original mapping, retry, cancellation, authentication, fixture-policy,
cost-deferral, and API-key-resolution objections.
```

After those items and the Rust plan revision, the amendment is ready for promotion into the frozen
design.

---

# Response — second pass, verified against the codebase and the current proposal text

Checked rather than accepted. Verdicts below.

## Editorial fix — fixture-corpus contradiction: CONFIRMED, real bug in my own prior edit

Grepped the committed proposal directly: line 217 (pre-fix) did still read "necessarily
per-implementation artifacts (different HTTP clients, no shared wire bytes format implied)," three
paragraphs before the body paragraph I *had* already corrected to say the opposite. My earlier
revision fixed Point 11's body paragraph but missed the section's own introductory sentence — an
incomplete application of a correction I'd already agreed to, not a new disagreement. Fixed now:
the intro sentence states the shared-verification-policy framing directly instead of repeating the
retracted claim.

## New issue — malformed fragmented tool-call settlement: AGREE, genuine gap

Checked the proposal's decode paragraphs for both APIs: neither said anything about conflicting
IDs, impossible index/`item_id` reuse, non-JSON arguments, or incomplete finalization. This is
externally observable (a caller sees either a clean tool call or a settled error, nothing else) and
was silently unaddressed. It also fits the existing error taxonomy cleanly rather than requiring a
new category: this is provider-sent malformed wire data, not an adapter bug, so it belongs with the
`AdapterOperationalError`-settles-in-band path already established for real adapters, not with
`AdapterProtocolError` (reserved for the adapter's own code violating the internal stream
contract — a bug in *our* code, which correctly still raises). Added as a new subsection pinning
this identically for both APIs.

## Continuation state: AGREE with reserving the facility now, still Case-A/B-agnostic

The push to specify `ProviderContinuation`'s shape now rather than leave it fully open is a
reasonable middle ground — it doesn't prejudge whether Codex actually needs it (that's still the
live-verification question), but it stops the architecture from having no place to put the answer
if verification comes back Case B. I agree specifically with rejecting `previous_response_id` alone
as a substitute: it would make request reconstruction depend on remote, mutable, expiring
provider-side state, which conflicts with the frozen design's log-reconstruction invariant (§8) —
this isn't a new principle, it's the same one already cited earlier in this review thread. Folded
the full field list (API/compatibility identity, log-reconstructable, session-ancestry-aware,
diagnostics-excluded, eager-fail-if-missing) into the `codex-responses` reasoning subsection,
framed explicitly as proposed-regardless-of-outcome, with the live experiment scoped to determining
payload and compatibility key rather than whether the facility exists at all.

## Rust Phase 2 adapter contract, wire-envelope decoding, credential-capability types, checked-map guidance: agree these do NOT belong in this design doc

The reviewer's own text self-classifies section 2 as "a Rust implementation-plan correction, not an
additional language-neutral runtime rule" — correct, and the same reasoning applies to sections 3
and 5 (open wire-event decoding, credential-authority Rust types) and the checked-map guidance in
section 4. This document's own scope note excludes Python-specific implementation detail
(file layout, config classes) from `design/`; the symmetric exclusion holds for Rust-specific
implementation detail (async adapter signatures, serde representations, `Debug`/`Serialize`
derives). None of that belongs promoted into §4 — it's implementation-plan material for whoever
writes the Rust Phase 5 plan. No change made to the design doc for these; noting them here so
they aren't lost, since there's no Rust plan file yet to carry them forward into.

## `Usage.cost` representation: agree it's a real question, disagree it belongs in this amendment

Checked the master design directly: `Usage.cost` ("computed cost") is already frozen provider-
neutral vocabulary from before Phase 5 — it's not something this real-providers proposal introduces
or is positioned to resolve. Its type representation (optional-while-uncomputed, exact decimal vs.
float) is a legitimate open question, but it isn't specific to real-provider wire behavior; it would
apply equally if Phase 5 never happened. Recorded as decision-log item 16, explicitly scoped as a
follow-up against the earlier Usage-vocabulary decision rather than a blocker on this amendment —
agree it should be settled before either implementation treats `Usage` as a stable public type, just
not as a condition of merging this proposal.

## Disposition

Both blocking items from this round applied to the design doc: the fixture-wording contradiction is
fixed, and malformed-fragmented-tool-call settlement is now pinned identically for both APIs. The
continuation-state facility is now specified in shape (not merely gestured at), with the live
Codex-verification question narrowed to payload/compatibility-key rather than left fully open. The
Rust-implementation-plan-scoped items (adapter async contract, wire-envelope decode strategy,
credential-capability types, checked-map fragment storage) are correctly out of this document's
scope and are not applied here — they need to land wherever the Rust Phase 5 plan gets written.
`Usage.cost` representation is logged as a tracked follow-up, explicitly not a blocker on this
amendment. The one remaining blocker, as before both review rounds: empirical verification of Case
A vs. Case B for `codex-responses` continuation, which is implementation-time work against a real
Codex OAuth session, not resolvable at the design layer alone.

---

# Latest Rust verdict after `fa2bbf9`

## Verdict

The second-round revision resolves the previous mapping, cancellation, fixture, and malformed-
tool-call findings. Do not freeze it yet: continuation payload verification remains open, and one
important continuation data-flow rule is still missing.

## Resolved in the latest proposal

The proposal now correctly includes:

- a concrete, log-only, content-addressed `ProviderContinuation` facility;
- rejection of provider-held `previous_response_id` as the sole reconstruction source;
- continuation compatibility identity, ancestry, sensitivity, and eager missing/incompatible
  behavior;
- malformed fragmented tool calls settling in-band as `StopReason.error` rather than becoming
  executable semantic calls;
- consistent shared-or-separate provider fixture wording;
- the earlier wire mapping, retry, cancellation, authentication, and deferral corrections.

Those findings are closed.

## Remaining language-neutral gap: continuation data flow

The proposal specifies continuation storage properties but not the complete semantic path:

```text
provider response decoder
    -> continuation artifact created
    -> committed log event/request-header reference
    -> session ancestry/reset/compaction handling
    -> next request reconstruction
    -> matching adapter replay
```

The design should pin behaviorally:

- how continuation produced during streaming reaches the committed session log;
- whether it is committed only with a terminal response or may be published incrementally;
- which request-header component references it, so Section 8 reconstruction includes it;
- whether a new continuation replaces earlier state or appends an ordered sequence;
- how a fork selects the exact continuation prefix at its ancestry boundary;
- what happens when the next request changes API/provider compatibility identity;
- that a failed, abandoned, or retried pre-commit physical attempt cannot publish continuation;
- how reconstruction proves the exact continuation selected for dispatch was log-derived.

These are observable cross-language rules, even if event names, structs, and artifact layouts remain
implementation-specific. The existing `StreamChunk`/`AssistantMessage` vocabulary contains only
model-visible assistant state, so the design cannot rely on continuation implicitly riding inside
those types.

Add canonical coverage, under an existing family, for at least:

```text
response produces continuation
tool result is appended
next request reconstructs and replays matching continuation
provider/API mismatch follows the pinned compatibility rule
```

The live Codex experiment should determine the exact replay payload, compatibility key, and
replacement-versus-accumulation rule. It should not leave the production/logging path unspecified.

## Required Rust sequencing correction

The second-pass response correctly excludes Rust signatures and storage structures from the
language-neutral amendment, but it is too late to defer every Rust change to a future Phase 5 plan.

The existing Rust Phase 2 plan publishes:

```rust
fn stream(&self, request: Request)
    -> Result<RawAssistantStream, LlmStartError>;
```

and a closed `Request` struct containing model, system, messages, and output limit. Those are public
contracts. Implementing them unchanged and waiting until Phase 5 would require a breaking change to
support:

- asynchronous credential/artifact/continuation preparation;
- restartable physical attempts before first-public-chunk commitment;
- typed retry classification;
- reconstructable provider state carried into dispatch.

Therefore the Rust Phase 2 plan must be revised before its LLM tasks execute. It should reserve:

- asynchronous eager preparation/start;
- a restartable internal attempt factory or equivalent;
- a dispatch envelope or extensible request-component context separate from provider-neutral
  messages;
- cancellation of pending retry/start work when the public stream is dropped or fused.

The mock adapter can implement the richer interface without introducing real-provider semantics
early. Open wire-event decoding, credential-capability types, checked-map fragment storage, HTTP
transport, and fixture details may still wait for the Rust Phase 5 implementation plan because
they do not otherwise freeze an earlier public API.

## `Usage.cost`

`Usage.cost` remains outside this amendment, as the second-pass response states. Nevertheless, its
Rust representation must be settled before the Rust Phase 2 vocabulary task publishes `Usage`.
It should be optional while uncomputed and use an exact monetary representation rather than
`f64`.

## Final disposition

Do not freeze yet. Require:

1. live verification of the continuation payload, compatibility key, and replacement/accumulation
   behavior;
2. a language-neutral continuation production, logging, request-header, reconstruction, and replay
   flow;
3. canonical coverage for continuation across a tool-call round trip;
4. revision of Rust Phase 2 before its public LLM interfaces are implemented;
5. settlement of the Rust `Usage.cost` representation before that public type is introduced.

After items 1-3, the amendment is ready for promotion. Items 4-5 are Rust implementation-plan
gates and do not need to be inserted into the language-neutral Section 4 text.
---

# Latest design-review comment on the twice-revised proposal — 2026-08-20

## Verdict

The current amendment has closed the earlier review findings around wire mapping, retry, cancellation,
authentication, malformed fragmented tool calls, fixture policy, cost deferral, and API-key resolution.

**Do not freeze it yet.** The remaining issue is now narrower: the proposal defines the
`ProviderContinuation` abstraction, but it still does not pin the complete language-neutral path by
which continuation observed in a provider response becomes committed Minion request state and is
reconstructed for the next dispatch.

The amendment currently says continuation is log-only, content-addressed, ancestry-aware,
compatibility-keyed, and reconstructable, while its status text says only the exact wire payload and
compatibility key remain open. That is not quite enough. The frozen request-reconstruction invariant
requires the exact provider state supplied on a later request to be derivable from committed Minion
state, not merely to exist somewhere in an artifact store.

## 1. Remaining amendment blocker — pin continuation data flow

Add a language-neutral behavioral path equivalent to:

```text
physical provider attempt
    ↓
decoder observes provider continuation item(s)
    ↓
attempt-local pending continuation
    ↓
only the selected/committed physical attempt may publish continuation
    ↓
content-addressed artifact + committed log reference
    ↓
request reconstruction selects applicable continuation deterministically
    ↓
request/header references the exact selected provider state
    ↓
matching adapter receives/replays that reconstructed state
```

Exact event names, structs, artifact layout, and language-specific storage types remain implementation
details.

Required rules:

1. **No ghost continuation from discarded attempts.** A transiently failed pre-commit attempt that is
   retried before the first public `StreamChunk`, or any abandoned attempt, must not publish durable
   continuation state.

2. **Define the commit point.** Continuation may be observed incrementally by the decoder, but it stays
   attempt-local until a defined response-settlement point commits it to the session. The live Codex
   experiment may determine which terminal outcomes yield replayable continuation, but the commitment
   rule itself must be explicit.

3. **Make continuation part of request reconstruction.** Extend the content-addressed request-header
   composition with an explicit provider-state/continuation component (the exact component name is not
   normative), rather than letting an adapter fetch opaque state from private mutable memory.

   The invariant must be able to establish:

   ```text
   reconstructed continuation == continuation actually supplied to dispatch
   ```

4. **Pin deterministic selection/order.** The live experiment should determine whether Codex needs one
   latest item, an ordered sequence, or another replay shape. Until then the generic facility should
   preserve deterministic production order rather than assume replacement.

5. **Pin fork behavior.** A fork sees exactly the continuation prefix reachable at its ancestry
   boundary. Continuation produced after that boundary cannot leak into the fork.

6. **Disambiguate API mismatch.**

   ```text
   switch from codex-responses to an API that does not consume Codex continuation
       -> old Codex continuation is ineligible; no failure

   selected API/provider requires continuation but only missing/incompatible state exists
       -> eager preparation failure before stream return
   ```

7. **Keep it outside model-visible vocabulary.** `ProviderContinuation` remains request state, not a
   `ThinkingBlock`, `AssistantMessage`, or surface message type.

## 2. Live verification should answer three concrete questions

The proposal currently names payload and compatibility key. Add a third question:

```text
1. What complete provider item(s) must be replayed?
2. What compatibility key determines whether replay is legal?
3. Is replay replacement-based, latest-only, or an ordered accumulated sequence?
```

Use a real multi-step tool-call exchange:

```text
request 1
    -> reasoning/tool call + continuation

tool result

request 2
    -> succeeds using Minion-reconstructed continuation
```

Also verify omission/incompatibility behavior so the eager-failure rule is grounded in observed
provider requirements.

The architecture should no longer wait on the experiment: the continuation slot is already justified.
The experiment determines Codex's concrete replay contract.

## 3. Add canonical coverage under existing families

No new `conformance/llm/` family is needed.

Suggested language-neutral cases:

```text
session/
    provider-continuation-request-reconstruction
    provider-continuation-fork-boundary

agent/
    provider-continuation-tool-round-trip
    provider-continuation-api-mismatch
```

Pin at least:

```text
retry-before-first-public-chunk
    -> abandoned-attempt continuation absent

committed response continuation
    -> present in next reconstructed request

fork at seq N
    -> only continuation at/before N reachable

different API that does not consume continuation
    -> continuation not projected

same API requiring incompatible continuation
    -> eager failure before stream return
```

These scenarios assert semantic reconstruction and selection, not artifact layout or provider wire
bytes.

## 4. Small wording correction — continuation sensitivity

The proposal currently says continuation is excluded from ordinary telemetry and diagnostics. The
**opaque payload** should indeed never be serialized there, but the wording should not forbid all
sanitized metadata.

Recommended rule:

> Provider-continuation payload bytes are sensitive opaque provider state and are never serialized
> into ordinary telemetry or diagnostics. Only explicitly sanitized non-payload metadata may be
> emitted through the existing telemetry sanitization boundary.

That still allows useful safe diagnostics such as continuation present/missing, API identity, or a
compatibility-mismatch category.

## 5. Update the proposal status text

The top status currently frames the one remaining open item as empirical verification of
`encrypted_content`, payload, and compatibility key.

Update it to distinguish two pieces:

```text
A. empirical Codex contract:
   exact payload + compatibility key + replacement/accumulation semantics

B. language-neutral Minion contract:
   production + commit + log/reference + request reconstruction + replay path
```

Once B is pinned, only A depends on live provider verification.

## 6. Rust sequencing — agree with the latest Rust review, but keep it out of §4

The latest Rust review correctly identifies a separate implementation sequencing risk: if Rust Phase 2
publishes a synchronous one-shot adapter and a closed request shape first, Phase 5 will immediately
need to break those contracts.

This is **not another language-neutral amendment blocker**, but it is a pre-implementation gate.

Revise the Rust Phase 2 plan before its public LLM tasks execute so the seam can accommodate:

```text
asynchronous eager preparation/start
restartable pre-commit physical attempts
typed retry/failure classification
extensible/log-reconstructable provider request state
drop/fusion cancellation of pending start/retry work
```

The mock adapter can implement the richer seam without pulling real-provider behavior into Phase 2.
Open provider-event decoding, credential-capability Rust types, checked-map fragment storage, HTTP
transport, and fixture machinery may still remain Phase 5 implementation details.

## 7. Usage.cost

Keep the current disposition:

```text
pricing/catalog/computation policy
    -> explicitly deferred by this amendment

concrete Rust Usage.cost representation
    -> settle before Rust publishes the provider-neutral Usage type
    -> not a blocker on this Phase 5 language-neutral amendment
```

Do not pull exact-decimal/currency representation into this amendment unless the earlier frozen Usage
vocabulary is deliberately reopened.

## Final disposition

```text
AMENDMENT-LEVEL BLOCKING
1. Pin ProviderContinuation production -> commit -> log/reference ->
   request reconstruction -> matching replay semantics.
2. Live-verify Codex payload, compatibility key, and replacement/accumulation behavior.

ADD CANONICAL COVERAGE
3. Continuation request reconstruction and fork-boundary behavior.
4. Tool-call round trip, API mismatch, and discarded-retry-attempt behavior.

SMALL WORDING FIXES
5. Exclude opaque continuation payload from telemetry/diagnostics while allowing
   explicitly sanitized non-payload metadata.
6. Update the proposal status text to name both the Minion data-flow contract and
   the empirical Codex replay contract.

SEPARATE IMPLEMENTATION-PLAN GATES
7. Revise Rust Phase 2 LLM/request seams before implementing their public contracts.
8. Settle Rust Usage.cost representation before publishing that type.

RESOLVED
All earlier mapping, retry, cancellation, authentication, malformed-tool-call,
fixture-policy, cost-deferral, and API-key-resolution findings.
```

After items 1–6, the language-neutral amendment is ready for promotion into the frozen design.
Items 7–8 remain implementation sequencing gates and should be tracked in the Rust plan rather than
inserted into §4.

---

# Response — third pass, verified against the current proposal text

Both new review threads (the Rust-side follow-up and the design-review comment) converge
independently on the same finding, which is stronger evidence than either alone: reserving
`ProviderContinuation`'s *properties* is not the same as pinning its *data flow*, and the frozen
request-reconstruction invariant genuinely needs the latter, not just the former.

## Continuation data-flow gap: CONFIRMED, applied

Checked the proposal text directly rather than trusting the review's characterization: the
`ProviderContinuation` block I'd written listed only static properties (identity, reconstructable,
ancestry-aware, eager-fail) with no path from "decoder observes an item mid-stream" to "a later
request legally replays it." That's a real gap, not a restatement of an earlier point — the earlier
rounds asked "does this need to exist," this round asks "how does it actually move through the
system," and the second question wasn't answered by the first. Added the full production →
attempt-local → commit point → content-addressed artifact/log-reference → request-reconstruction
selection → matching-adapter-replay path, plus the seven numbered rules (no ghost continuation from
discarded attempts, explicit commit point, continuation as an explicit request-reconstruction
component rather than adapter-private memory with the `reconstructed == dispatched` invariant
stated explicitly, deterministic selection order, fork-boundary scoping, API-mismatch
disambiguation, never model-visible).

## Live-verification scope narrowed to three questions: agree, applied

The addition of "is replay replacement-based, latest-only, or an ordered accumulated sequence?" as
a third question alongside payload and compatibility key is a real gap in what I'd scoped the
experiment to determine — my prior text only asked for payload and compatibility key. Applied
verbatim as the three-question scope, with the concrete request-1/tool-result/request-2 exchange
shape and the omission/incompatibility failure path folded in as what the experiment needs to walk
through.

## Telemetry wording: agree, narrower fix than a full rewrite

My prior "excluded from ordinary telemetry and diagnostics" was a blanket statement the reviewer
correctly read as forbidding even safe metadata like presence/absence or a mismatch category. Fixed
to scope the exclusion to opaque payload bytes specifically, with an explicit carve-out for
sanitized non-payload metadata through the existing telemetry sanitization boundary.

## Conformance coverage suggestion: agree, added as a coverage note rather than as scenario files

The suggested `session/`/`agent/` scenario list (continuation-request-reconstruction,
fork-boundary, tool-round-trip, API-mismatch) is exactly the kind of thing this project's
contract-driven process wants pinned before implementation. I added it as a decision-log item and a
short paragraph naming what needs coverage, not as actual conformance YAML — writing the scenarios
themselves is Plan-writing-phase work (per this project's established Phase 0 pattern: conformance
scenarios precede implementation, but they're authored when a plan is written against a settled
design, not invented ad hoc inside a still-open design amendment). The design doc's job here is to
make sure the coverage isn't forgotten when that plan gets written, which the note now does.

## Status-text split into piece A (empirical) / piece B (language-neutral): agree, applied

This is the right frame and matches what the edits above actually did: the data-flow contract (B)
is now fully pinned regardless of outcome, and only the empirical Codex payload contract (A) stays
open. Updated the Status line to state this explicitly instead of the previous single "one item
remains open" framing, which undersold how much of this got resolved in this pass.

## Rust sequencing (both reviews' point on Rust Phase 2's public contract shape): agree with the
## finding, still correctly out of this document

Both new review threads independently flag the same real risk — a synchronous one-shot Rust
adapter signature and a closed `Request` struct, if implemented as currently planned before Phase 5
lands, would force a breaking change. That's a legitimate pre-implementation sequencing gate. But
it is a Rust Phase 2 *plan* correction, not a language-neutral design rule — nothing about it is
observable behavior a Python implementation is bound by, which is exactly this document's own scope
test (see the scope note). No change made to this design doc for it. Flagging again, as I did last
round, that this needs to land in whichever plan governs Rust Phase 2, since there's still no Rust
Phase 5 (or revised Phase 2) plan file to carry it forward into — it isn't tracked anywhere yet
outside this feedback thread.

## `Usage.cost`: no change — both reviews confirm the prior disposition was correct

Both new threads restate rather than dispute the second-pass response's judgment call (real
question, predates this amendment, not a blocker here, needs settling before Rust publishes the
public `Usage` type). No design-doc change needed; disposition stands as recorded in decision-log
item 16.

## Disposition

Applied: the full continuation data-flow path and its seven rules, the three-question live-
verification scope, the narrower telemetry wording, the conformance-coverage note, and the
split status-text framing (piece A open, piece B now resolved). Confirmed correctly out of scope
and left unapplied: Rust Phase 2 sequencing (both reviews agree it's a plan gate, not a §4 rule)
and `Usage.cost`'s Rust representation (predates this amendment). If the next review pass finds the
data-flow rules sufficient, this amendment has no known remaining language-neutral blocker other
than the live Codex experiment itself — which is genuinely implementation-time work requiring a
real Codex OAuth session, not something further design-review iteration can resolve.

---

# Fourth Rust review — action register after proposal `b3410d3`

## Verdict

The latest proposal resolves the previously open language-neutral `ProviderContinuation` data-flow
architecture. From a Rust perspective, one semantic clarification and one empirical verification
remain before the amendment freezes. Several implementation and conformance follow-ups must also be
assigned now so they are not mistaken for optional Phase 5 cleanup.

## Required before amendment freeze

### 1. Pin atomic logical settlement

The proposal correctly makes continuation data attempt-local until the physical attempt commits, but
it does not yet explicitly require the terminal assistant response and the continuation references
derived from that attempt to become reachable atomically.

Add this language-neutral rule:

> The settled assistant response and every continuation reference derived from the same physical
> attempt become reachable as one atomic logical settlement. Artifact bytes may be stored earlier,
> but no committed log state exposes the terminal response without its required continuation, or a
> continuation from a response that did not commit.

This does not require one particular event encoding or storage transaction API. An implementation
may use a composite event, transactional append, or another mechanism, provided concurrent readers,
reconstruction, and recovery cannot observe a half-settled response. Without this rule, Python could
append the assistant response and continuation as independently visible operations while Rust uses a
single logical commit, producing a cross-language difference after cancellation, persistence failure,
or concurrent observation.

**Owner:** language-neutral amendment/design owner.

### 2. Complete the live Codex verification

The real Codex OAuth experiment still must determine:

- the exact provider item or item sequence that must be replayed;
- the API/version/model compatibility identity that admits replay;
- whether successful turns replace, extend, or otherwise transform the prior continuation sequence;
- which terminal outcomes produce reusable continuation state and which discard it.

Record sanitized evidence and update the proposal's open fields and decision log before freeze. This
work requires a real credentialed multi-turn tool-call exchange and cannot be resolved by further
static review.

**Owner:** Phase 5 provider implementation/design owner with access to a real Codex OAuth session.

## Required shared canonical-conformance work

After the live contract is pinned, add language-neutral cases through the existing canonical
families. At minimum, cover:

- a committed continuation being selected for the next compatible request;
- continuation from a discarded/retried physical attempt not entering committed state;
- fork reconstruction observing only continuation state within the fixed ancestry boundary;
- API or compatibility mismatch preventing replay;
- a deterministically incompatible request failing eagerly before stream return;
- the terminal assistant response and its continuation references becoming observable as one
  logical settlement.

The adapters may arrange fixtures and project results, but continuation selection, settlement,
reconstruction, and compatibility decisions must execute in the real Python and Rust libraries.

**Owner:** shared canonical-conformance maintainers, coordinated with both implementation owners.

## Required Python Phase 5 plan changes

The Python Phase 5 implementation must not bolt continuation replay onto the provider after request
history has already been committed. Its agent-loop flow must:

1. resolve the target provider/API compatibility identity;
2. reconstruct and select eligible continuation state;
3. include the selected continuation identity in the request header before dispatch;
4. keep decoder output attempt-local across retries;
5. atomically settle the terminal assistant response with continuation references only for the
   winning physical attempt.

The current Python flow records a request header before `llm.stream(request)` and later appends the
assistant response. The Phase 5 plan therefore needs an explicit integration change at that boundary,
not only adapter-local decoding logic.

**Owner:** Python Phase 5 plan/implementation owner.

## Required Rust Phase 2 plan changes

This is the most time-sensitive Rust action. The current Phase 2 plan publishes a synchronous,
one-shot adapter start shape:

```rust
fn stream(&self, request: Request) -> Result<RawAssistantStream, LlmStartError>;
```

That contract should be revised before Phase 2 implementation freezes. The public and internal
boundaries must reserve room for:

- asynchronous eager preparation before `AssistantStream` is returned;
- restartable physical attempts before logical commit;
- typed classification of retryable and non-retryable start/stream outcomes;
- reconstructed provider request state through an extensible dispatch context or separate provider
  envelope rather than continually expanding the closed provider-neutral `Request` vocabulary;
- cancellation/release of a pending physical attempt when the public stream is dropped or fuses.

The provider-neutral request/message vocabulary should remain stable. Provider continuation is
reconstructed request state, not a model-visible message and not an invitation to add provider wire
types to the semantic `Request` structure.

**Owner:** Rust Phase 2 plan and LLM API owner. This action is required before implementing the
published Phase 2 adapter surface; it must not be deferred until the Rust Phase 5 plan.

## Required Rust Phase 5 plan items

The later Rust Phase 5 plan should explicitly cover the amendment's provider-specific realization:

- open provider wire-event envelopes and tolerant decoding;
- checked tool-call correlation and response-ID maps;
- credential-source capability reporting without secret exposure;
- Codex continuation extraction, artifact persistence, compatibility checks, and replay translation;
- transport cancellation and retry-attempt ownership;
- sanitized fixture capture plus offline deterministic replay.

These do not require further language-neutral amendment text unless implementation discovers a new
observable semantic difference.

**Owner:** future Rust Phase 5 plan owner.

## Separate pre-publication Rust vocabulary gate

`Usage.cost` still needs an exact optional representation before Rust publishes its provider-neutral
`Usage` API. It should not default to binary floating point merely for convenience. This issue
predates the amendment and does not block amendment freeze, but it must be resolved before the Rust
Phase 2 public vocabulary becomes a compatibility commitment.

**Owner:** Rust Phase 2 vocabulary/API owner.

## Final disposition

Do not request another broad architectural redesign. Close the atomic-settlement sentence and the
live provider experiment, then freeze the amendment. In parallel, update the Rust Phase 2 plan before
its LLM surface is implemented. Once the empirical contract is known, add the shared canonical cases
and apply the corresponding Python Phase 5 and later Rust Phase 5 implementation work.
---

# Fifth design review — after third proposal revision — 2026-08-20

## Verdict

The third revision resolves the previously identified language-neutral continuation **data-flow**
gap. The proposal now explicitly carries continuation from decoder observation through attempt-local
state, a durable commit, content-addressed reconstruction, fork scoping, compatibility filtering,
and matching replay; it also adds the requested conformance-coverage obligations.

Do not freeze yet, but the remaining amendment work is now small and concrete:

1. pin **atomic logical settlement** of the terminal assistant response and continuation references
   from the same physical attempt; and
2. complete the live Codex experiment that fixes the concrete replay payload/compatibility contract.

I agree with the fourth Rust review that atomic settlement is a real cross-language semantic rule.
I do **not** agree that the Rust public `stream()` API necessarily has to become asynchronous merely
because provider preparation may perform I/O; that recommendation needs to be constrained by the
already-frozen never-raises boundary.

## 1. ProviderContinuation data flow — resolved

The proposal now correctly pins:

```text
physical attempt
    -> decoder observes continuation attempt-locally
    -> defined response-settlement point
    -> content-addressed artifact + committed log reference
    -> deterministic request reconstruction
    -> request/header references exact selected provider state
    -> compatible adapter replay
```

It also correctly specifies:

- no durable continuation from discarded/retried attempts;
- explicit request-reconstruction participation rather than adapter-private memory;
- deterministic ordering pending the live contract;
- fork ancestry boundaries;
- API mismatch as ineligibility rather than automatic failure;
- eager failure only when the selected API/provider actually requires compatible continuation;
- continuation never becoming `ThinkingBlock` or other surface content; and
- opaque payload exclusion from diagnostics/telemetry while allowing sanitized metadata.

Those earlier findings are closed.

## 2. Required amendment fix — atomic logical response settlement

The fourth Rust review identifies the remaining semantic hole correctly.

Today the text says continuation remains attempt-local until a response-settlement point and then
becomes committed, but it does not explicitly require the **terminal assistant response** and the
continuation references derived from that same physical attempt to become visible as one logical
settlement.

Add a rule equivalent to:

> **Atomic logical settlement.** The settled assistant response and every continuation reference
> selected from the same physical provider attempt become reachable as one atomic logical
> settlement. Artifact bytes may be persisted earlier, but no committed session state may expose
> the terminal assistant response without the continuation references required to reconstruct it,
> and no continuation reference from an uncommitted response may become reachable independently.

This is behavioral, not a storage prescription. Python may use a transactional append/composite
operation and Rust may use a different mechanism; both must make half-settled state unobservable to:

```text
concurrent readers
fork/reconstruction
process-recovery logic
the next request
```

The rule should apply only to continuation actually selected as replayable for that response.
A provider response with no continuation requirement continues to settle normally.

Add canonical coverage for the half-settlement case once the concrete continuation contract is
pinned.

## 3. Clarify that there are two different commitment boundaries

The current amendment uses "commit" in two nearby but different senses:

```text
A. retry commitment
   first public StreamChunk
   -> physical attempt can no longer be transparently retried

B. durable logical settlement
   terminal response settlement
   -> assistant response + replayable continuation become committed session state
```

These must not be conflated.

The first-public-chunk rule does **not** mean provider continuation observed by that point becomes
durable. Continuation remains attempt-local until the response reaches the separate logical
settlement point.

Recommended terminology:

```text
retry commitment boundary
logical response settlement
```

rather than calling both simply "commit point."

This is especially important for a stream that has emitted `StreamStart` or partial text and later
fails: retry is already forbidden, but whether any continuation from that response is reusable is a
separate terminal-outcome rule determined by the Codex contract.

## 4. Live Codex verification — expand the recorded answer by one item

The proposal already asks:

```text
1. exact provider item(s) to replay
2. compatibility key
3. replacement/latest/ordered accumulation behavior
```

The fourth Rust review correctly adds:

```text
4. which terminal outcomes produce reusable continuation state?
```

That fourth question is necessary because the generic logical-settlement rule needs to know whether,
for example, continuation from a completed tool-use response is replayable while continuation from a
failed/incomplete response is discarded.

The live exchange should therefore pin:

```text
payload/item sequence
compatibility identity
ordering/replacement semantics
terminal-outcome reuse semantics
```

and then update the proposal's open fields and decision log.

## 5. Request-header integration — current direction is correct

The proposal now makes provider continuation an explicit component of content-addressed request
reconstruction and requires:

```text
reconstructed continuation == continuation supplied to dispatch
```

That is the right language-neutral rule.

One implementation consequence should remain explicit in the Python Phase 5 plan:

```text
select compatible continuation
    -> include its identity in the logical request/header
    -> dispatch that reconstructed request
```

The adapter must not reach back into mutable session state after the request header is fixed and pick
a different continuation.

No additional §4 abstraction is needed beyond the rule already present.

## 6. Correction to the Rust sequencing advice — do not move operational I/O across the never-raises boundary

The Rust reviews are right that the Phase 2 **one-shot raw stream** shape is too narrow for
transparent pre-first-chunk retry and reconstructed provider state.

However, this proposed Rust change:

```text
asynchronous provider preparation/start
    -> Result<AssistantStream, LlmStartError>
```

must not be interpreted as permission to perform arbitrary operational provider I/O before the
public stream exists and raise those failures eagerly.

The frozen semantic boundary remains:

```text
before AssistantStream exists
    deterministic caller/config/request/model-selection failures may raise

after AssistantStream exists
    expected provider/network/model/streaming operational failures settle in-band
```

Therefore:

- deterministic unsupported-content validation may remain eager;
- resolved-model/provider/config validation may remain eager;
- **network-bound credential refresh, provider upload/materialization, HTTP start, and other expected
  operational I/O should not escape as eager exceptions merely because an implementation chooses an
  async public method**;
- such operational work can live behind `AssistantStream` in a lazy async attempt factory/future and
  settle through the existing stream contract.

A synchronous public Rust shape is therefore still viable in principle:

```rust
fn stream(&self, request: Request)
    -> Result<AssistantStream, LlmStartError>
```

provided `AssistantStream` owns a restartable/lazy async attempt factory rather than a one-shot
`RawAssistantStream`.

The required Rust Phase 2 correction is the **capability**, not necessarily `async fn` at the public
boundary:

```text
restartable pre-first-chunk attempt construction
typed transient/non-transient failure classification
extensible reconstructed provider request state
cancellation of pending attempt/backoff work on drop/fusion
```

If Rust still chooses an asynchronous public start API, its eager-error classification must preserve
the same language-neutral boundary; operational network failures must not become caller-visible
exceptions just because they occurred during an awaited preparation phase.

This should replace the tracking language that treats "asynchronous eager preparation/start" as
already decided.

## 7. Python Phase 5 implication

The same boundary applies symmetrically to Python.

Do not implement provider auth refresh/artifact upload/continuation preparation as arbitrary code
that can throw out of iteration after `AssistantStream` has already been returned.

The Python Phase 5 plan should separate:

```text
eager deterministic validation
    -> may raise before stream return

operational provider preparation / physical attempts
    -> owned by the raw stream/attempt controller
    -> normalized by AssistantStream
    -> retryable only before first public chunk when transient
```

This follows the frozen design rather than introducing a provider-specific exception path.

## 8. Canonical conformance disposition

The proposal's new coverage note is now sufficient as design intent. When the concrete contract is
pinned, scenarios should cover at least:

```text
committed continuation -> selected in next compatible request
discarded/retried attempt -> continuation absent
fork boundary -> only reachable prefix selected
API not consuming continuation -> state ineligible without failure
required incompatible continuation -> eager request error
terminal assistant response + continuation refs -> one logical settlement
```

No new `conformance/llm/` family is needed; keep these in existing `session/` and `agent/` families.

## 9. Usage.cost

No change to the previous disposition.

`Usage.cost` representation is a real Rust pre-publication vocabulary decision, but it predates this
amendment and does not block Phase 5 amendment freeze.

## Final disposition

```text
AMENDMENT-LEVEL REQUIRED BEFORE FREEZE
1. Add atomic logical settlement of terminal assistant response + continuation references.
2. Distinguish retry commitment from durable logical response settlement in wording.
3. Live-verify Codex:
     - exact replay item(s)
     - compatibility key
     - replacement/latest/accumulation behavior
     - terminal-outcome reuse behavior
4. Update the proposal/decision log with those empirical results.

CANONICAL FOLLOW-UP
5. Add continuation reconstruction/fork/tool-round-trip/API-mismatch/discarded-attempt cases.
6. Add atomic-settlement coverage.

IMPLEMENTATION-PLAN GATES
7. Python Phase 5: integrate continuation selection into request-header construction and keep
   provider I/O behind the never-raises stream boundary.
8. Rust Phase 2: replace the one-shot attempt seam before implementation, but do not assume the
   public API must become async; preserve the never-raises classification across whichever API
   shape is chosen.
9. Rust Usage.cost representation: settle before public vocabulary publication.

RESOLVED
All earlier mapping, retry, cancellation, authentication, malformed-tool-call,
fixture-policy, continuation-data-flow, cost-deferral, and API-key-resolution findings.
```

After items 1–4, there is no remaining known design-review blocker. The amendment can freeze and the
canonical/implementation work can proceed from the pinned contract.

---

# Response — fourth pass, verified against the current proposal text

Two more independent review threads (a fourth Rust review, and a fifth design review that
explicitly checks the fourth Rust review's own recommendations rather than rubber-stamping them).
The fact that the fifth review pushes back on part of the fourth is itself useful signal — I should
apply that same scrutiny rather than average the two.

## Atomic logical settlement: CONFIRMED gap, applied

Checked my own rule 2 text from the last pass: it said continuation "stays attempt-local until a
defined response-settlement point commits it to the session" — that establishes *a* commit point
exists, but never says the assistant response and its continuation references become reachable
*together*. Both reviews independently caught the same hole, and it's real: without atomicity, nothing
stops an implementation from appending the assistant response and its continuation as two
independently-visible log operations, which is exactly the kind of cross-language divergence (one
implementation observes a half-settled response after a crash/cancel, the other doesn't) this
project's process exists to catch before it's discovered in two divergent implementations. Applied
the atomic-settlement rule into rule 2 directly, plus added it to the conformance-coverage note and
decision-log item 17.

## Two distinct commitment boundaries: agree, real terminology bug

Grepped my own text: "commit point" was used for the pre-existing retry-commitment boundary
(first public chunk) *and*, unqualified, for the new continuation-settlement point — genuinely
ambiguous, and worse, conflatable in a way that matters: someone could misread "commits the
attempt" (retry boundary) as also meaning "commits the continuation" (settlement boundary), which
are different points in the same stream's lifecycle. Renamed the continuation-specific term to
"logical response settlement" throughout and added an explicit disambiguating note distinguishing
it from the retry-commitment boundary, per both reviews' recommended terminology.

## Fourth live-verification question: agree, applied

"Which terminal outcomes produce reusable continuation state" is a real fourth question the prior
three (payload, compatibility key, replacement semantics) don't cover — a completed tool-use
response and a failed one could plausibly differ in whether their continuation is reusable at all,
and the atomic-settlement rule specifically needs to know this to decide what "whatever is reachable
is reachable atomically" is being applied to. Added as question 4.

## Rust-sequencing correction (design review point 6, correcting the fourth Rust review): agree with the correction, no design-doc change needed either way

This is the one place the two new reviews disagree with each other, and I checked which is right
rather than deferring to whichever arrived first. The fourth Rust review recommended Rust's public
`stream()` become `async fn` to accommodate I/O-bearing preparation. The fifth design review
correctly pushes back: the frozen never-raises boundary is about *when* a failure category may
raise (before vs. after the stream exists), not about whether the public method signature is sync
or async — collapsing "needs restartable pre-commit attempts and typed failure classification" into
"needs an async public function" would let operational I/O failures (credential refresh, upload,
HTTP start) raise as eager exceptions merely because they happened during an awaited phase, which is
exactly the boundary violation the never-raises contract exists to prevent. I agree with the
correction. Neither version changes anything in this design doc either way — both explicitly frame
themselves as Rust Phase 2 plan content, and the actual language-neutral rule (the two-phase
never-raises boundary itself) is already stated in the existing "never-raises boundary applied to
real providers" section, unchanged by either review. Flagging the disagreement and its resolution
here for whoever eventually writes the Rust Phase 2 plan revision, since — as in the last two
passes — there's still no Rust plan file to carry it forward into.

## Python Phase 5 integration note (design review §5, §7): agree, correctly scoped as plan content, no design-doc change

The design review itself says "No additional §4 abstraction is needed beyond the rule already
present" — I agree; the `reconstructed continuation == continuation supplied to dispatch` invariant
is already stated in rule 3, and the sequencing detail (resolve compatibility → select continuation
→ fix it in the request header → dispatch, adapter must not reach back into mutable session state
afterward) is an implementation-plan constraint on how Python's agent loop integrates with a rule
already pinned, not a new rule itself.

## Canonical conformance, Usage.cost: no change, confirmed correct as previously disposed

The design review's coverage list matches what's already in the conformance-coverage note (now
including atomic settlement); no new family needed, consistent with the prior round. `Usage.cost`
disposition is restated unchanged by both reviews — no action.

## Disposition

Applied: the atomic-settlement rule (folded into rule 2, not a separate rule 8, since it's the same
commit point gaining a completeness property rather than a new phase in the flow), the
retry-commitment/logical-settlement terminology split, and the fourth live-verification question —
all reflected in the data-flow block, the verification-questions list, the conformance-coverage
note, and decision-log items 13 and 17. The one substantive disagreement between the two new
reviews (Rust async-vs-sync sequencing) is resolved in favor of the fifth review's more precise
reading of the never-raises boundary, but doesn't touch this document regardless, since both framed
it as Rust Phase 2 plan content. If this satisfies the fifth review's stated bar — "after items 1-4,
there is no remaining known design-review blocker" — the only thing left before this amendment can
actually freeze is the live Codex experiment itself, which no further review pass can substitute
for.
