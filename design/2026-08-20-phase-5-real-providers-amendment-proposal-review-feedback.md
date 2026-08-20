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