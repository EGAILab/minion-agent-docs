# Target-Model Message Transformation (XFORM) — Fidelity Assurance & Certification

**Layer ID:** `04`
**Status:** `IN_AUDIT` — twice independently Rust-reviewed and twice **`REJECTED —
PI_PARITY_DEFECT`** (first: `04-target-model-transformation-rust-review.md`, docs `0f3d419`;
second: `04-target-model-transformation-rust-r001-r004-rereview.md`, docs `c64880d`). The second
rejection traced its root cause upstream to already-certified Layer 02/03 Python implementations
diverging from their own already-correct contracts, reopening `LLM-F012` (Layer 02) and `SES-F009`
(Layer 03) narrowly (§0.6) — those layers' own status is `historically CERTIFIED,
POST-CERTIFICATION DELTA AUDIT OPEN`, not reopened from scratch. A corrected candidate, fixing the
upstream layers plus the remaining `XFORM-R001`/`XFORM-R002`, awaits fresh Rust re-review. Not
`CERTIFIED`: certification requires an `APPROVED` shared-contract verdict and, if Rust
implementation is required at that point, a green Rust implementation and gates too (§17).
**Audit date:** 2026-08-24 (three passes: first — Pi source read directly and in full,
shared-contract gaps found and repaired, Python implementation and tests written, canonical evidence
authored, Session's Layer-04 deferment activated, Python gates green, sent for review; second —
independently reproduced all four first-rejection findings before accepting them, repaired each
narrowly, re-verified Python gates fresh, sent a corrected candidate for re-review; third — the
second rejection's `XFORM-R001`/`XFORM-R002` findings independently reproduced, root cause traced
to Layer 02/03 (§0.6), those two layers' own Python implementations repaired (`LLM-F012`/
`SES-F009`), `XFORM-R001` closed completely and `XFORM-R002` repaired at the schema/runner level,
Python gates re-verified fresh a third time.)
**Auditor:** Claude (Python-driven, per adopted workflow)
**Python status:** `IMPLEMENTED` — semantic-owner review complete; cross-language review verdict on
the corrected candidate `PENDING`
**Rust status:** `NOT STARTED` — no Rust code was touched in any pass, per the adopted
review-before-remediation workflow (contract review must return `APPROVED` first)

---

## 0. Rust rejection and narrow remediation (2026-08-24, second and third passes)

**Formal verdict on the first candidate** (`minion-agent@84c6ba2` / `minion-agent-docs@a4eef91`,
`04-target-model-transformation-rust-review.md`):

```text
LAYER 04 XFORM SHARED CONTRACT
    REJECTED — PI_PARITY_DEFECT
```

Rust independently re-read `transform-messages.ts` in full, confirmed every one of the four
originally-advertised contract repairs (§4) as correct and Pi-compatible, confirmed the full
thinking matrix and Session/Phase-5 boundaries as correct, and found four real findings — each
independently reproduced against the actual candidate before being accepted, not taken on the
review's word:

| ID | Category | Finding | Reproduced independently | Disposition this pass |
|---|---|---|---|---|
| `XFORM-R001` | `PI_PARITY_DEFECT` | `UserMessage.content` is `string \| [TextBlock\|ImageBlock]` (`spec/llm.md`), both first-class; a valid string was corrupted by the non-vision image-downgrade path, which iterated it as a generic block sequence | YES — `transform_messages([UserMessage(content="hello", ...)], target_novision)` produced `content=("h","e","l","l","o")`, reproduced directly before any fix | `RESOLVED` (§0.1) |
| `XFORM-R002` | `CONTRACT_ASSURANCE_DEFECT` | `agent-transform-scenario.schema.json` rejected the valid string-content case, rejected rich `AssistantMessage`/`ToolResultMessage` fields under `additionalProperties: false`, accepted an empty target identity, and accepted an assertion-free `expect: {}` | YES — all four independently reproduced via direct schema-validator probes against the live schema before fixing it | `RESOLVED` (§0.2) |
| `XFORM-R003` | `CONTRACT_ASSURANCE_DEFECT` | `pi-parity-manifest.yaml`'s `AI-013` cited Question-A-only XFORM scenarios (rescoped in the first pass, §6) as if they proved Question-B Responses provider-wire replay | YES — confirmed by re-reading `AI-013`'s `tests:` list and cross-checking that neither cited scenario invokes any Responses/provider encoding | `RESOLVED` (§0.3) |
| `XFORM-R004` | `CONTRACT_ASSURANCE_DEFECT` | This document's §4 lists four repaired contract defects; its (prior) §15 findings table listed only three, omitting the image-capability-gate finding | YES — confirmed by direct comparison of the two sections as they stood after the first pass | `RESOLVED` (§0.4, this rewrite) |

**Substantive XFORM behavior already approved was not reopened.** Rust's review explicitly confirmed
(and this pass did not re-litigate) same-model redacted thinking, the full thinking compatibility
matrix, placeholder-dedup mechanics, the image-capability gate, the frozen target identity triple,
the injected ID-normalization-callback ownership split, cross-model signature stripping (including
the empty-string-`thought_signature` truthy-check quirk), error/aborted exclusion, orphan-synthesis
ordering, the Session→XFORM composition, runner thinness, and the Phase-5 production-wiring
boundary. None of these were touched this pass except where a fix below directly required it.

### §0.1 — `XFORM-R001` fix

`minion_agent/llm/transform_messages.py::_downgrade_unsupported_images` now checks
`isinstance(message.content, str)` for `UserMessage` before attempting placeholder replacement
(`ToolResultMessage.content` has no string variant in the frozen vocabulary, so needs no equivalent
guard). A string passes through completely untouched for both a vision-capable and a non-vision
target, matching Pi's own `Array.isArray(msg.content)` guard exactly. 9 new focused tests added
(`tests/llm/test_transform_messages.py`): vision/non-vision/empty/whitespace/placeholder-literal
string content, target-capability independence, and a block-array regression guard. New canonical
scenario `string-user-content-survives-transformation.yaml` pins the critical non-vision parity case
as cross-language evidence. `spec/target-model-transformation.md` rule 2 extended to state the
string/array distinction explicitly — the spec previously implicitly assumed array content
throughout rule 2's wording, which this pass corrected. The spec's invariants section was also
corrected per Rust's own note: "source messages are never mutated" was overspecified to imply fresh
allocation is normative; reworded to state only value-immutability is cross-language observable,
object identity is not.

### §0.2 — `XFORM-R002` fix

`conformance/schema/agent-transform-scenario.schema.json` rewritten:

- New `$defs/userContent` (`string | array-of-text-or-image-blocks`), used by both `inputMessage`
  and `outputMessage`'s `user` variant.
- Assistant and tool-result variants gained every remaining certified-but-previously-omitted
  optional field (`usage`, `response_model`, `response_id`, `diagnostics`, `deferred`,
  `error_message`, `raw_stop_reason`, `end_turn` for assistant; `details`, `usage`,
  `added_tool_names` for tool-result), inlined directly into each variant's own `properties` rather
  than composed via `allOf` + `$ref` — `additionalProperties: false` does not see properties
  declared in a sibling `allOf` branch, a real JSON Schema composition pitfall confirmed by a direct
  probe before choosing the inline approach.
- `transform.target`'s `provider`/`api`/`model_id` gained `minLength: 1`.
- `expect` gained `minProperties: 1`, so `expect: {}` (asserting nothing) is now rejected.
- Role/content legality (`assistant` + `image` rejected, etc.) was already correct and is unchanged.

`tests/conformance/transform_runner.py` extended to thread every newly-schema-permitted field
through both directions (`_message()`/`_normalize_message()`, reusing the same
`usage`/`diagnostic`/`deferred` decode/encode shape already established in `session_runner.py`/
`agent_runner.py` for consistency) and to handle `UserMessage.content` as `str | tuple[...] | None`
throughout. `tool_result`'s `timestamp` is now always present in the real normalized output
(restoring the observable evidence that a real pass-through result's timestamp is preserved
untouched — the prior omission is exactly what let this go unnoticed); `test_transform_conformance.py`
gained a comparison helper that drops `timestamp` from the actual dict only when a scenario's own
expected `tool_result` entry omits it (the synthesized-result case, still never asserted, per
`spec/target-model-transformation.md`'s own documented reasoning — unchanged).

All 12 pre-existing scenarios' `expect.messages` entries were updated to include the newly-required
explicit field set (all defaulted/null, since none of the 12 scripts rich metadata) — an evidence
completeness fix, not a behavior change; all 12 re-verified passing unchanged.

Full adversarial probe matrix run directly against the corrected schema before any scenario was
touched (§0.5 below has the complete results): every case Rust's own review listed, plus the full
matrix this pass's own instruction required, all producing the correct accept/reject outcome.

### §0.3 — `XFORM-R003` fix

`pi-parity-manifest.yaml`'s `AI-013` row rewritten: `rule:` now states the Question A/Question B
split explicitly, names both cited tests as Question-A-only prerequisite evidence, and states
plainly that Question-B (Responses provider-wire replay) evidence does not yet exist because no
Responses-family adapter exists in this repository (re-confirming, not re-deriving, Layer 02's own
exhaustive history search). No fake Responses encoder was added, and no placeholder scenario was
invented merely to make `AI-013` numerically tidy, per explicit instruction. `AI-021`'s own row was
checked and already correctly cites the same two rescoped scenarios as its own Question-A evidence
(unchanged, no fix needed there).

### §0.4 — `XFORM-R004` fix (this section, and §15 below)

History corrected, not erased: the first pass's Pi audit genuinely found and repaired **four**
`CONTRACT_ASSURANCE_DEFECT`s against the prior condensed spec (same-model-redacted-thinking,
placeholder-dedup-mechanics, the image-downgrade capability gate, and tool-call-ID-normalization
ownership — §4 lists all four and was already correct). The prior version of this document's §15
findings table listed only three, omitting the image-capability-gate repair — an assurance
bookkeeping slip, not a re-classification: the capability-gate finding was always a genuine contract
repair (the prior rule's wording admitted an always-downgrade or per-message reading, not only the
correct single-target-capability reading), never a cosmetic one. §15 below now lists all four,
correctly labeled as findings from the *first* pass, kept distinct from `XFORM-R001`..`R004`
(*second*-pass, post-rejection findings) rather than merged into one count.

### §0.5 — Adversarial pre-review probe matrix (fresh, this pass)

Run directly against the corrected `agent-transform-scenario.schema.json` before pushing the new
candidate:

```text
valid user string                REJECT -> ACCEPT (fixed)
user block array                 ACCEPT (unchanged)
legacy user null                 ACCEPT (unchanged)
empty target.provider             ACCEPT -> REJECT (fixed)
empty target.api                  ACCEPT -> REJECT (fixed)
empty target.model_id             ACCEPT -> REJECT (fixed)
rich AssistantMessage             REJECT -> ACCEPT (fixed)
rich ToolResultMessage            REJECT -> ACCEPT (fixed)
tool_result missing tool_name      REJECT (unchanged, still correctly rejected)
tool_result tool_name=null         REJECT (unchanged, still correctly rejected)
empty expect: {}                   ACCEPT -> REJECT (fixed)
assistant + image                  REJECT (unchanged, still correctly rejected)
```

All twelve produced the expected result. Additional probes specific to `XFORM-R001`, run against
the real `transform_messages()` seam directly (not the schema): `"hello"` + non-vision → `"hello"`;
`""` + non-vision → `""`; the literal placeholder string + non-vision → unchanged (not deduplicated,
since it is not an array of image blocks); string content transformed identically under a
vision-capable and a non-vision target. All passed — see §0.1 and the 9 new unit tests.

### §0.6 — Second Rust rejection: root cause reclassified upstream

The candidate above (`minion-agent@42ef135` / `minion-agent-docs@d8ebcbe`) was sent for re-review
and again returned `REJECTED — PI_PARITY_DEFECT`
(`04-target-model-transformation-rust-r001-r004-rereview.md`, docs `c64880d`). Reproduced
independently before accepting: `XFORM-R001`'s *runtime* transform behavior was confirmed correct
(the string-preservation branch worked for every probed input), but a direct static probe —
`UserMessage(content="hello", timestamp=1)` against the then-current `messages.py` — reported
`Argument "content" has incompatible type "str"; expected "tuple[...]"`. The certified public
Python vocabulary itself, not just the transform function, still excluded the frozen `string |
[TextBlock|ImageBlock]` shape `spec/llm.md` already specifies. `XFORM-R002` was also confirmed
still open: `AssistantMessage` without `usage` validated against the schema, and
`transform_runner.py::_usage(None)` silently manufactured a default `Usage()` — semantic
fabrication the schema's completeness alone did not prevent, since nothing required the field in
the first place. `XFORM-R003` was confirmed `APPROVED` (unchanged, not reopened). `XFORM-R004` was
confirmed still open (the stale `12`-count inconsistencies §0.4 introduces below).

**This is not confined to Layer 04.** `UserMessage.content`'s type is Layer-02 vocabulary
(`minion_agent/llm/messages.py`), and `session/derive.py::encode_message()` — Layer-03, certified —
iterates `message.content` before role dispatch, so it could not safely persist a real string-typed
`UserMessage` either. Per the post-certification delta audit guardrail
(`process/implementation-conformance-workflow.md` §4.6: a later-language implementation's
discovery of a certified-implementation violation must trigger a delta audit of the owning
layer), this reopens Layer 02 and Layer 03 narrowly — not because their *contracts* were wrong
(`spec/llm.md` already specified the string shape correctly) but because their Python
*implementations* had silently diverged from an already-correct, already-certified contract,
exactly the same shape of defect `LLM-F011`'s `tool_name` finding was. New findings:
`LLM-F012` (Layer 02, `PI_PARITY_DEFECT`) and `SES-F009` (Layer 03,
`CONTRACT_ASSURANCE_DEFECT` + Python implementation defect). Both layers' status:
`historically CERTIFIED, POST-CERTIFICATION DELTA AUDIT OPEN` (`IN_DELTA_AUDIT`) — full detail in
`assurance/layers/02-llm.md` §0 (continued) and `assurance/layers/03-session-artifacts.md` §0
(continued). Neither layer's original certification date or `LLM-F011`/`SES-F004`..`F008` closure
history is erased.

### §0.7 — `LLM-F012` fix (Layer 02)

`minion_agent/llm/content.py` gained role-specific content-block aliases:
`UserContentBlock = TextBlock | ImageBlock`, `AssistantContentBlock = TextBlock | ThinkingBlock |
ToolCallBlock`, `ToolResultContentBlock = TextBlock | ImageBlock` — the generic `ContentBlock`
alias is retained only for internal generic helpers (encode/decode, normalization), never for a
message type's own field. `minion_agent/llm/messages.py`:
`UserMessage.content: str | tuple[UserContentBlock, ...]`,
`AssistantMessage.content: tuple[AssistantContentBlock, ...]`,
`ToolResultMessage.content: tuple[ToolResultContentBlock, ...]`; `text_of()` returns a
string-valued `content` directly instead of attempting to iterate it as blocks. Every consumer
`mypy` (full-source run, not test-scoped) flagged was fixed at its own real role-specific type —
`session/derive.py`, `llm/transform_messages.py`, `llm/adapters/mock.py::ScriptedResponse`,
`tools/result.py::ToolResult` — nine call sites across four files, none papered over with a cast to
the generic `ContentBlock` (the two `typing.cast` uses that do exist, in `derive.py`'s
`decode_message`, narrow `_decode_block`'s generic return to the role already known from `raw["role"]`
at that call site, consistent with the project's rule against adding new runtime validation solely
to mimic static typing — role/content legality remains a schema-level concern, `SES-F005`).

Permanent static-type evidence: `tests/typing/valid_message_construction.py` (new, never imported
or executed by pytest — mypy checking it *is* the test) proves seven positive constructions
type-check, including the three specifically named in the second rejection:
`UserMessage(content="hello", ...)`, `UserMessage(content=(TextBlock(...),), ...)`,
`UserMessage(content=(ImageBlock(...),), ...)`, plus the analogous `AssistantMessage`/
`ToolResultMessage` cases. Run explicitly: `mypy src/minion_agent
tests/typing/valid_message_construction.py` (a single file argument fails with
`import-untyped` errors, since mypy then treats the installed `minion_agent` package as
third-party; including `src/minion_agent` in the same invocation resolves it as first-party). Five
negative probes (role-invalid combinations — user+`ThinkingBlock`, user+`ToolCall`, assistant+
`ImageBlock`, tool_result+`ThinkingBlock`, tool_result+`ToolCall`) were also run directly and all
five correctly rejected with the exact incompatible-type error naming the frozen union — confirmed,
not assumed, and not committed as a permanent fixture (a file that must fail to type-check cannot
itself be part of a passing gate).

`LLM-F012` — **`RESOLVED`**, Python/shared side; Rust delta review pending.

### §0.8 — `SES-F009` fix (Layer 03)

`session/derive.py::encode_message`/`decode_message` no longer compute `content` once, uniformly,
before role dispatch. `encode_message`'s `user` branch: a `str`-valued `content` encodes as itself
(already JSON-safe); otherwise the existing block-array encoding runs unchanged. `decode_message`'s
`user` branch: a JSON string decodes to a Python string directly; a JSON array decodes through the
existing `_decode_block` path. Assistant and tool-result branches are unchanged (their content has
no string variant). The `text` scenario-DSL shorthand was deliberately left alone — it still means
"one `TextBlock`," not "a string," because conflating the two would itself reintroduce the
representation-conflation this finding is about.

`conformance/schema/session-scenario.schema.json`'s `step.append.content` gained a `user`-only
(and plugin-role, which builds as a user message) string alternative, via the same
role-conditional `allOf`/`if`/`then` pattern already governing content-type-enum restriction —
`assistant`/`tool_result` remain array-only, matching their vocabulary's own lack of a string
variant. New `expect_user_details` observation (mirroring the existing `expect_assistant_details`/
`expect_tool_result_details` pattern) exposes the real derived `UserMessage.content` representation
directly, since `expect_messages`' role/text projection cannot distinguish a string from a
single-`TextBlock` array — both produce identical visible text. `session_runner.py` gained
`_user_content()` (decode: string stays string) and `_user_detail()` (encode-for-comparison: same
rule), wired into the result dict as `user_details`.

New canonical scenario `conformance/session/string-user-message-round-trip.yaml`: scripts a string
message, a single-`TextBlock`-array message, and — after a real `fork` — another string message;
`expect_user_details` proves all three retain their real scripted representation through actual
Session persistence and derivation, including across a fork boundary. Two new focused unit tests in
`tests/session/test_derive.py` (`test_string_valued_user_message_round_trips_as_a_string`,
`test_string_and_single_text_block_user_messages_remain_distinct_after_round_trip`) pin the
encode/decode behavior directly, independent of the canonical scenario.

`SES-F009` — **`RESOLVED`**, Python/shared side; Rust delta review pending.

### §0.9 — `XFORM-R001` (complete) and `XFORM-R002` fixes (Layer 04, this pass)

With `LLM-F012` fixed, `XFORM-R001` closes at the layer it was always ultimately about: the
production seam no longer relies on Python's runtime laxity to accept a value its own declared
public type forbids. No change was needed in `transform_messages.py`'s own logic (the runtime
branch from the first remediation was already correct); `transform_runner.py`'s decoder helpers
were simplified since `str | tuple[...] | None` is now the real, statically-valid input shape
rather than a value smuggled past an incomplete type.

`XFORM-R002`: `agent-transform-scenario.schema.json`'s `usage` $def and `cost` $def each gained a
`required` list matching every non-optional `Usage`/`Cost` member (`spec/llm.md`: only
`cache_write_1h` and `reasoning` carry `?`); both assistant `required` lists (input and output
message shapes) gained `usage`. `transform_runner.py::_usage()` now reads every field directly
(`raw["input"]`, not `raw.get("input", 0)`) — a schema-valid scenario always supplies a complete
object, so there is nothing left to default or fabricate; `ToolResultMessage.usage` remains
genuinely optional at its own call site (`None` when the key is absent), and is exercised through
the same now-strict `_usage()` when present, so an incomplete-but-present tool-result usage is
still correctly rejected by the schema before the runner ever sees it. All 13 XFORM canonical
scenarios' `transform.messages` assistant entries were updated with a complete, deliberately-zeroed
`usage` object where none was scripted before — evidence completeness, not a behavior change (none
of these scenarios' own assertions depend on usage values).

`XFORM-R001` — **`RESOLVED`** (complete, upstream root cause fixed). `XFORM-R002` — **`RESOLVED`**.
Both Rust delta review pending.

### §0.10 — Fresh adversarial probe matrix (this pass)

The full 13-case matrix from §0.5 was re-run unchanged (all still correct) plus the new
`usage`-requiredness matrix — 13 cases, all producing the required accept/reject outcome (§25's
own matrix; full results recorded in §16's fresh gate output and independently reproduced again
before push, not reused from the schema-authoring step).

---

## 1. Scope

### Owns

Generic target-model compatibility transformation (`process/requirement-id-convention.md` prefix
`XFORM-###`), per frozen master §4's own distinct "Pi-compatible target-model message
transformation" subsection, explicitly excised from Layer 02's scope and certified separately here:

- Legacy null-content normalization.
- Unsupported-image downgrade (capability-gated) and its exact placeholder-collapse mechanics.
- Thinking-block same-model/cross-model compatibility (retention, conversion, removal, redacted
  handling).
- Cross-model `text_signature`/`thought_signature` stripping.
- The generic tool-call-ID normalization *orchestration* (map-building, cross-model-only
  invocation, consistent `ToolCall`/`ToolResultMessage` rewrite) — not the concrete per-target-API
  algorithm (see "Does not own").
- Orphan tool-result synthesis for unresolved tool calls.
- Historical `error`/`aborted` assistant exclusion from replay.
- The normative pipeline order these rules run in (§25 of the delta audit's own governing
  instruction: order is observable, not incidental).

### Does not own

- **The concrete tool-call-ID normalization algorithm** a specific target API requires (`AI-023`'s
  own disposition) — Phase-5/`PROV-###` territory. Pi itself never hardcodes one:
  `transformMessages()` takes `normalizeToolCallId` as an injected callback, and every one of its
  six real call sites (`anthropic-messages.ts`, `bedrock-converse-stream.ts`, `google-shared.ts`,
  `mistral-conversations.ts`, `openai-completions.ts`, `openai-responses-shared.ts`) supplies its
  own. Layer 04 owns only the hook and its generic use.
- **Provider wire encoding** — turning a transformed `Message[]` into a real HTTP/API payload is
  Phase-5/provider territory.
- **Responses-family provider replay** — how a retained `thinking_signature`/`text_signature` gets
  encoded back into a real Responses-wire request is a distinct question from whether the block
  survives transformation at all (see §6's dedicated disposition below). Phase-5/provider territory,
  matching Layer 02's own `LLM-017` disposition.
- **Session projection** (`derive_messages()`, fork/reset/compaction, request-header
  reconstruction) — Layer 03, certified. XFORM consumes its output; it does not reconstruct it.
- **Agent-loop orchestration** (turn/run lifecycle, tool execution, provider invocation sequencing)
  — Layer 08/06 territory. XFORM is a pure function over an already-assembled message list; it does
  not decide when to call a model or how to execute a tool.

### Depends on

Layer 02 (LLM vocabulary, `CERTIFIED`) — every input/output value is a Layer-02 `Message`/
`ContentBlock`; `ModelId`'s frozen `provider + api + model_id` triple is reused directly, not
reinvented, for target-model identity. Layer 03 (Session, `CERTIFIED`) — consumes
`derive_messages()`'s output as its own input (design §5's own explicit sequencing, now activated
by `SES-013`, see §9).

### Depended on by

Phase-5 provider adapters (not yet started) — the real request-preparation path this module is
built for but not yet wired into (§5).

---

## 2. Normative sources

- **Frozen design:** `design/2026-08-20-minion-agent-design.md` §4's "Pi-compatible target-model
  message transformation" subsection.
- **Spec:** `spec/target-model-transformation.md` — rewritten this pass; see §4 for what changed
  and why.
- **Pinned Pi source:** `ref-repos/pi`, commit `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged
  pin, matching Layers 01-03). Primary: `packages/ai/src/api/transform-messages.ts` (223 lines, read
  in full — the entire observable surface lives in this one file; no helper module needed reading
  beyond it). Supporting: `packages/ai/src/types.ts` (`Message`/`AssistantMessage`/
  `ToolResultMessage`/`TextContent`/`ThinkingContent`/`ToolCall`/`Model<TApi>`/`StopReason`, all
  already pinned by Layer 02's own audit, re-confirmed unchanged). Confirmed all six real call sites
  of `transformMessages()` across the provider adapters (`grep`, not assumed) to establish the
  injected-callback architecture (§4's rule 13 finding).
- **`/pi-parity-manifest.yaml`:** `AI-020` through `AI-026`, all `phase: 2`, `disposition: adopted`
  — audited and corrected this pass (§7).
- **Canonical conformance:** `conformance/agent/*.yaml`, 13 XFORM scenarios (a second schema,
  `agent-transform-scenario.schema.json`, for the same `agent` family/directory — not a fourth
  canonical family, see §8) plus `conformance/session/request-reconstruction-after-target-transform.yaml`
  (Layer-03's own deferred `SES-013` scenario, activated this pass, §9) and
  `conformance/session/string-user-message-round-trip.yaml` (`SES-F009`, §9).
- **Requirement-ID convention:** `process/requirement-id-convention.md`, prefix `XFORM-###` (newly
  populated this pass, §5).

---

## 3. Pi behavior summary

Read `packages/ai/src/api/transform-messages.ts` in full (223 lines) — the complete function, not a
paraphrase. Every observable branch, traced directly rather than inferred from the prior condensed
spec:

**Two internal passes, in this order, over the full message list:**

1. `downgradeUnsupportedImages` — no-op if `model.input.includes("image")`; otherwise, for `user`
   messages with array content and for `toolResult` messages, replaces image blocks with the
   role-appropriate placeholder via `replaceImagesWithPlaceholder`, which tracks
   `previousWasPlaceholder` across the whole content array (collapsing consecutive raw images into
   one placeholder, and treating a pre-existing text block matching the placeholder string as if a
   placeholder had just been emitted).
2. Content transform + ID-map building, one forward pass: `user` messages pass through unchanged;
   `toolResult` messages get their `toolCallId` rewritten if the map (built by this same pass, from
   earlier `assistant` messages) has an entry; `assistant` messages get their content transformed
   per-block (`thinking`/`text`/`toolCall`), computing `isSameModel = provider === model.provider &&
   api === model.api && model === model.id` once per message.
3. Orphan synthesis + exclusion, a second forward pass over pass-2's output: on each `assistant`
   message, first flush any still-pending tool calls from the *previous* kept assistant (inserting
   synthetic `ToolResultMessage`s before this new message); then, if this assistant's `stopReason`
   is `error` or `aborted`, `continue` — drop it and its own tool calls entirely, never tracking
   them as pending; otherwise track its tool calls as the new pending set (replacing, not
   accumulating) and keep the message. On each `toolResult`, record its `toolCallId` as resolved and
   keep it. On each `user`, flush pending orphans first, then keep it. After the loop, flush once
   more for history-ending orphans.

**Exact thinking-block decision tree** (traced line-by-line, not summarized from memory):
`redacted` is checked first — same-model keeps the block unchanged, cross-model drops it entirely,
regardless of signature or text. Only if not redacted: same-model *and* has a signature (truthy
check) keeps the block unchanged, even with empty text. Only if that didn't match: empty/blank text
(any model, any signature) is dropped. Only if not empty: same-model keeps the block unchanged;
cross-model converts to a fresh text block, discarding the signature. **This produces a same-model
`redacted: true` retention case the prior condensed spec never stated** — see §7's finding.

**Signature stripping is a truthy check, not a presence check**: `if (!isSameModel &&
toolCall.thoughtSignature)` — an empty-string `thoughtSignature` is left untouched cross-model,
matching JS falsy semantics. Reproduced directly as a dedicated unit test
(`test_cross_model_empty_string_thought_signature_is_not_stripped`), not assumed.

**Tool-call-ID normalization has no built-in algorithm.** `transformMessages<TApi>(messages, model,
normalizeToolCallId?)` — the third parameter is optional, caller-supplied, typed `(id: string, model:
Model<TApi>, source: AssistantMessage) => string`. `grep -rn "transformMessages(" packages/` across
the whole Pi repository confirms all six real call sites each supply their own locally-scoped
normalizer (e.g. `anthropic-messages.ts`'s own `normalizeToolCallId(id: string): string` at line
1116, enforcing Anthropic's `^[a-zA-Z0-9_-]+$`/64-char constraint — read for context only, not
reproduced, since the *concrete* algorithm is Phase-5 territory). The function itself only
builds/applies the id map, invoked cross-model only.

**`Model<TApi>`** (`types.ts:821-850`) is a full provider/model-registry entry (`id, name, api,
provider, baseUrl, reasoning, thinkingLevelMap?, input, cost, contextWindow, maxTokens,
samplingParams?, headers?, compat?`) — `transformMessages()` itself reads only `model.provider`,
`model.api`, `model.id`, and `model.input` (for the image-capability check). Confirms `TargetModel`
should carry only what the function uses, not a Phase-5 registry entry (§5).

No `PI_BEHAVIOR_UNCERTAIN` finding — every rule above traces to a specific, read line of the pinned
source, not to inference or the prior spec's own paraphrase.

---

## 4. Shared-contract repair (`spec/target-model-transformation.md`)

The prior condensed 15-rule spec was largely accurate (independently re-verified rule-by-rule
against the real source, not assumed correct or incorrect going in) but had four real gaps,
classified `CONTRACT_ASSURANCE_DEFECT` and repaired in this pass's rewrite — a shared-contract
change, not a Python-only fix, since a second implementation reading only the old spec would
independently reproduce each gap:

| Gap | Missing/imprecise | Repair |
|---|---|---|
| Same-model redacted thinking | The old 15 rules had no case for `redacted: true` + same-model at all — only cross-model redacted ("omit") was stated | New rule 8: same-model redacted retains unchanged, checked before every other thinking case |
| Placeholder dedup mechanics | Old rule 4, "adjacent equivalent placeholders are deduplicated," is vague about what "equivalent" and "adjacent" mean | New rule 4: precise mechanics — consecutive raw images collapse to one placeholder per message; a non-image block breaks the run; a pre-existing text block matching the placeholder string suppresses the next image's own placeholder too |
| Image-downgrade capability gate | Old rules 2/3 didn't state the gate is a single boolean on the *target model*, not a per-message decision | New rules 2/3 state the gate explicitly, and note `assistant` content structurally never carries images (`SES-F005`), so there is no assistant-side case |
| Tool-call-ID normalization ownership | Old rule 13, "normalize foreign tool-call IDs for target API," reads as if `transform_messages` implements an algorithm | New rule 13 states the real architecture: no built-in algorithm, an injected per-target-API callback, generic map orchestration only — this module's actual scope, with the concrete algorithm explicitly assigned Phase-5/provider ownership |

Also added, not present before: the normative pipeline order (legacy-null → image-downgrade →
content-transform → orphan-synthesis, stated as observable, not incidental), the full synthetic-
`ToolResultMessage` field enumeration (`tool_name` required, sourced from the real `ToolCall`,
matching `LLM-F011`), and five explicit cross-cutting invariants (immutability, determinism,
vocabulary-validity, no-image-for-incapable-target, no-forbidden-signatures-cross-model).

No `conformance/schema/agent-scenario.schema.json` or `session-scenario.schema.json` change was
required by this repair — the new `agent-transform-scenario.schema.json` (§8) is additive, and
`session-scenario.schema.json`'s `transform_target`/`expect_transformed_messages` addition (§9) is
also additive; neither repairs a defect in the other two schemas.

---

## 5. Requirement traceability

| ID | Requirement | Source | Canonical scenario | Language test | Status |
|---|---|---|---|---|---|
| `XFORM-001` | Legacy null content normalizes to `[]`, first, unconditionally, every role | Pi rule 1; `spec/target-model-transformation.md` rule 1; `AI-026` | `null-content-normalizes-empty` | `test_legacy_null_content_normalizes_to_empty_on_every_role` | `PASS` |
| `XFORM-002` | Unsupported-image downgrade, exact placeholder strings, capability-gated | Pi rules 2-3; spec rules 2-3; `AI-020` | `nonvision-user-image-placeholder`, `nonvision-tool-image-placeholder` | `test_supported_target_leaves_images_untouched`, `test_unsupported_user_image_becomes_the_exact_placeholder`, `test_unsupported_tool_result_image_becomes_the_distinct_exact_placeholder` | `PASS` |
| `XFORM-003` | Placeholder collapse/suppression mechanics | Pi rule 4; spec rule 4; `AI-020` | `nonvision-user-image-placeholder` (collapse + break case) | `test_adjacent_images_collapse_into_one_placeholder`, `test_images_separated_by_text_each_get_their_own_placeholder`, `test_a_preexisting_text_block_matching_the_placeholder_suppresses_the_next_image` | `PASS` |
| `XFORM-004` | Same-model thinking matrix (signed/unsigned x empty/non-empty x redacted) | Pi rules 5-8; spec rules 5-8; `AI-021` | `same-model-thinking-signature-replayed`, `same-model-unsigned-thinking-not-replayed` | `test_same_model_signed_thinking_retained_even_when_empty`, `test_same_model_unsigned_nonempty_thinking_retained`, `test_same_model_unsigned_empty_thinking_removed`, `test_same_model_redacted_thinking_retained_unchanged` | `PASS` |
| `XFORM-005` | Cross-model thinking matrix (convert/remove/omit) | Pi rules 9-11; spec rules 9-11; `AI-021` | `cross-model-thinking-converts-to-text`, `cross-model-redacted-thinking-omitted` | `test_cross_model_signed_nonempty_thinking_converts_to_text_and_drops_signature`, `test_cross_model_signed_empty_thinking_removed_despite_signature`, `test_cross_model_unsigned_nonempty_thinking_converts_to_text`, `test_cross_model_unsigned_empty_thinking_removed`, `test_cross_model_redacted_thinking_omitted_regardless_of_signature` | `PASS` |
| `XFORM-006` | Cross-model `text_signature` stripping, independent of thinking | Pi rule 12 (text branch); spec rule 12; `AI-022` | `cross-model-signatures-stripped` | `test_same_model_text_signature_retained`, `test_cross_model_text_signature_stripped` | `PASS` |
| `XFORM-007` | Cross-model `thought_signature` stripping (truthy check), `namespace` survival | Pi rule 12 (toolCall branch); spec rule 13a; `AI-022` | `cross-model-signatures-stripped` | `test_same_model_thought_signature_retained`, `test_cross_model_thought_signature_stripped_but_namespace_and_id_survive`, `test_cross_model_empty_string_thought_signature_is_not_stripped` | `PASS` |
| `XFORM-008` | Tool-call-ID normalization: generic orchestration only, cross-model-only invocation, consistent `ToolResult` rewrite | Pi rule 13b (injected callback); spec rule 13b; `AI-023` | `tool-call-id-normalization` | `test_id_normalization_never_applies_same_model`, `test_id_normalization_applies_cross_model_and_rewrites_the_matching_result`, `test_an_unrelated_tool_result_id_is_never_accidentally_rewritten`, `test_multiple_calls_each_get_independently_normalized_and_matched` | `PASS` |
| `XFORM-009` | Orphan synthesis before a later interrupting message | Pi rule 14a; spec rule 14; `AI-024` | `orphan-tool-result-synthesized` | `test_orphan_synthesized_before_a_later_user_message`, `test_orphan_synthesized_before_a_later_assistant_message` | `PASS` |
| `XFORM-010` | Orphan synthesis at end of history; no synthesis when resolved; multiple orphans in source order; errored/aborted assistant's own calls never synthesized | Pi rule 14b; spec rule 14; `AI-024` | `orphan-tool-result-synthesized` | `test_orphan_synthesized_at_end_of_history`, `test_no_synthesis_when_a_real_result_already_exists`, `test_multiple_unresolved_calls_each_get_their_own_synthetic_result_in_source_order`, `test_errored_assistants_own_tool_calls_are_never_synthesized` | `PASS` |
| `XFORM-011` | Historical `error` exclusion | Pi rule 15; spec rule 15; `AI-025` | `errored-assistant-excluded-from-replay` | `test_errored_assistant_excluded_from_replay` | `PASS` |
| `XFORM-012` | Historical `aborted` exclusion; only these two reasons exclude | Pi rule 15; spec rule 15; `AI-025` | `aborted-assistant-excluded-from-replay` | `test_aborted_assistant_excluded_from_replay`, `test_only_error_and_aborted_are_excluded_not_other_stop_reasons` | `PASS` |
| `XFORM-R001` | `UserMessage.content` string is a first-class shape, distinct from array content; must survive transformation unchanged regardless of target image capability | Pi's `Array.isArray(msg.content)` guard; `spec/llm.md`; `spec/target-model-transformation.md` rule 2 (extended §0.1) | `string-user-content-survives-transformation` | `test_string_user_content_survives_a_vision_target_unchanged`, `test_string_user_content_survives_a_non_vision_target_unchanged`, `test_empty_string_user_content_survives_a_non_vision_target_unchanged`, `test_whitespace_only_string_user_content_survives_unchanged`, `test_a_string_equal_to_the_image_placeholder_survives_unchanged_not_deduplicated`, `test_string_user_content_transform_is_independent_of_target_image_capability`, `test_block_array_user_content_still_follows_normal_image_downgrade` | `PASS` (added §0.1, post-rejection) |

**13 distinct requirements drafted (12 from the first pass plus `XFORM-R001` from the rejection
remediation), all `PASS`.** Every requirement has both canonical
cross-language evidence and a focused Python unit test independently pinning the exact rule; no
requirement rests on canonical evidence alone or unit tests alone. Cross-cutting invariants
(immutability, determinism, vocabulary-validity, no-forbidden-content-cross-capability) are unit-
tested (`test_source_messages_are_never_mutated`,
`test_output_is_deterministic_for_identical_input_apart_from_synthetic_timestamps`,
`test_non_image_capable_target_output_contains_no_image_block`,
`test_cross_model_output_carries_no_forbidden_signatures`) rather than given their own requirement
IDs, since they are properties of every rule together, not one more rule.

---

## 6. Same-model thinking/replay ownership (resolved)

The two most delicate scenarios, resolved by distinguishing exactly the two questions the audit
instruction named:

- **Question A (this layer):** what `Message` blocks survive `transform_messages()` for the same
  target model? Fully in scope, fully tested. `same-model-thinking-signature-replayed.yaml` and
  `same-model-unsigned-thinking-not-replayed.yaml` were rewritten this pass to test *only* this —
  they invoke the real `transform_messages()` directly and assert the returned `Message` list, with
  no provider or wire format anywhere in the scenario.
- **Question B (Phase 5, unchanged disposition):** how a retained `thinking_signature`/
  `text_signature` gets encoded back into a real Responses-family provider request. Still
  `EXPLICITLY DEFERRED BY PLAN`, matching Layer 02's own `LLM-017` finding — re-confirmed this pass
  that no Responses/Codex adapter exists anywhere in this repository's history (Layer 02's own
  exhaustive `git log --all -S` search stands, not repeated).

Both scenario names are historical (`AI-021`'s own naming, inherited from the design's original
scenario list) and are slightly misleading about scope on their own — "replayed"/"not-replayed"
names a provider-wire concept these scenarios do not test. Renaming them was considered and
rejected: the manifest, both assurance layers, and the frozen design's own scenario-name list all
reference these exact names; renaming would be pure churn against the "do not force a contract
change for cosmetic reasons" rule (`process/implementation-conformance-workflow.md` §4.6), and each
scenario's own `notes` field now states its actual (Question-A-only) scope precisely. No runner
simulates provider-wire replay anywhere in this pass.

---

## 7. Parity manifest audit (`AI-020`..`AI-026`)

All seven rows read and independently re-verified against the pinned Pi source directly, not
trusted from their prior wording:

- **`AI-020`** (image downgrade): rule text expanded from "adjacent placeholder dedupe" to the
  precise mechanics (§4's repair). `python:` field corrected from `'target: ...'` (a not-yet-built
  placeholder) to the real implemented path.
- **`AI-021`** (thinking compatibility): rule text corrected to include the missing same-model-
  redacted case (§4's repair, §3's finding). `python:` field corrected to the real path.
- **`AI-022`** (signature stripping): rule text clarified to note the truthy-check quirk and
  namespace/id/name/arguments non-interference. `python:` field corrected.
- **`AI-023`** (tool-call-ID normalization): rule text rewritten entirely — the prior wording
  ("normalize target API tool-call ids") read as if this module owns an algorithm it does not;
  corrected to state the injected-callback architecture and the Phase-5 ownership boundary
  precisely. `python:` field corrected.
- **`AI-024`**/**`AI-025`** (orphan synthesis, error/aborted exclusion): rule text extended with the
  `tool_name`-required note (`LLM-F011` cross-reference) and the errored-assistant's-own-calls
  interaction respectively. `python:` fields corrected.
- **`AI-026`** (legacy null): rule text extended with the architectural note on *where* the check
  lives in Minion (inside `transform_messages()`, not at Session's decode boundary — see §11's
  design rationale). `python:` field corrected.

No `pi:` source path, `phase:`, `tests:` list (except adding no new scenario names — all 7 already
named their real evidence), or `disposition:` changed on any row — this was a rule-text and
`python:`-pointer accuracy pass, not a re-scoping. Manifest re-validated after every edit: 52 rows
(unchanged count), valid YAML, no duplicate ids.

---

## 8. Canonical evidence inventory

**Not a fourth canonical family.** Per the audit instruction's explicit prohibition, XFORM
scenarios live in `conformance/agent/` — the existing `agent` family/directory — discriminated from
full agent-loop scenarios by their own top-level `transform` key (mirroring the existing `family`-
key discriminator between the legacy and unified shapes). A new schema,
`conformance/schema/agent-transform-scenario.schema.json`, governs only files with that key; the
existing `agent-scenario.schema.json` and its full-loop runner (`agent_runner.py`/
`test_agent_conformance.py`) are untouched in shape, and `test_agent_conformance.py`'s own scenario
glob now excludes transform-shaped files explicitly (`_is_full_loop_scenario`) so it never tries to
run one through a full turn.

**Why a dedicated schema/runner, not the full agent-loop shape.** `transform_messages()` is a pure
function over an already-assembled message list; forcing a full agent-loop turn (provider script,
tool registry, listeners) to exercise it would require either the runner or the scenario author to
simulate Agent-loop orchestration XFORM does not own — exactly the thin-runner violation the method
forbids. The new shape is deliberately narrow: `transform: {messages, target,
normalize_tool_call_ids?}` in, `expect: {messages}` (or `expect: {error}`) out, executed by
`tests/conformance/transform_runner.py::run_transform_scenario()`, which parses typed values, calls
the real `transform_messages()`, and normalizes the real result — nothing else. Independently
audited this pass (not assumed thin because it was written thin): it does not replace images, dedupe
placeholders, filter thinking, strip signatures, normalize ids, detect orphans, or filter
errored/aborted assistants anywhere in its own code — grepped and read in full.

**Fresh inventory, all 12 previously-named placeholders filled in the first pass, plus one new
scenario added this pass (`XFORM-R001` regression evidence, §0.1):**

| Scenario | Prior state | State | Requirement(s) |
|---|---|---|---|
| `null-content-normalizes-empty` | placeholder (unified shape) | filled, real, passing | `XFORM-001` |
| `nonvision-user-image-placeholder` | placeholder | filled, real, passing | `XFORM-002`, `XFORM-003` |
| `nonvision-tool-image-placeholder` | placeholder | filled, real, passing | `XFORM-002` |
| `string-user-content-survives-transformation` | did not exist | **new this pass** | `XFORM-R001` |
| `same-model-thinking-signature-replayed` | placeholder | filled, real, passing (Question A only — §6) | `XFORM-004` |
| `same-model-unsigned-thinking-not-replayed` | placeholder | filled, real, passing (Question A only — §6) | `XFORM-004` |
| `cross-model-thinking-converts-to-text` | placeholder | filled, real, passing | `XFORM-005` |
| `cross-model-redacted-thinking-omitted` | placeholder | filled, real, passing | `XFORM-005` |
| `cross-model-signatures-stripped` | placeholder | filled, real, passing | `XFORM-006`, `XFORM-007` |
| `tool-call-id-normalization` | placeholder | filled, real, passing | `XFORM-008` |
| `orphan-tool-result-synthesized` | placeholder | filled, real, passing | `XFORM-009`, `XFORM-010` |
| `errored-assistant-excluded-from-replay` | placeholder | filled, real, passing | `XFORM-011` |
| `aborted-assistant-excluded-from-replay` | placeholder | filled, real, passing | `XFORM-012` |

**13 XFORM canonical scenarios, all real and passing, 0 remaining placeholders, 0 misclassified.**
Freshly recounted this pass, not carried forward from the first pass's "12" — the count changed and
is reported as changed. None require reclassification to Phase-5/Agent/Session ownership; none
require a real provider wire encoder. **"0 Layer-04-owned scenarios deferred to Phase 5" is a
statement about this layer's own canonical inventory only — it does not mean zero remaining
provider-wire obligations.** `AI-013`'s Responses-family signature-replay evidence (Question B, §6)
remains genuinely unfilled pending a real Phase-5 adapter; conflating the two would misstate Phase
5's remaining scope (`XFORM-R003`, §0.3).

---

## 9. Session-family Layer-04 activation (`SES-013`)

`conformance/session/request-reconstruction-after-target-transform.yaml` — Layer 03's own explicitly
deferred scenario (`03-session-artifacts.md` §7's own disposition: "Layer-04-deferred, non-blocking
for Layer 03 certification") — activated this pass.

**Real seam, not simulated:** `session_runner.py::run_session_scenario()` gained one small,
additive extension — an optional top-level `transform_target` scenario key. When present, after
computing `derive_messages(log)` from the real committed log (unchanged Session code, unchanged
Session behavior), the runner calls the real `transform_messages()` directly on that real output and
exposes the real result as `expect_transformed_messages`. Session does not gain any
transformation logic; XFORM does not gain any Session-reconstruction logic — they are composed, not
merged, exactly matching design §5's "Relationship to Pi's message projection."

**What the scenario proves:** a session log with a real image (base64-encoded, round-tripped through
the actual log/derive machinery) and an unresolved tool call is derived twice — once as
`expect_messages` (Session's own committed truth: image present, tool call still unresolved,
untouched) and once as `expect_transformed_messages` (the request-time view for a non-image-capable
target: the image downgraded to its placeholder, the unresolved call given a synthetic result) —
directly demonstrating design §5's stated distinction: "Session source truth stays stable; target-
specific transformed request is ephemeral," never persisted back into the log. Confirmed passing.

**Fresh canonical inventory** (Session family, re-run after activation): 19 discovered, 19 current-
layer executable, 0 deferred, 0 placeholders (`grep`-verified: no `TO_BE_FILLED`/`TO_BE_BOUND`/
`TO_BE_PINNED` marker remains anywhere in `conformance/session/*.yaml`).

---

## 10. Implementation inventory

| File | Responsibility | Decision | Evidence |
|---|---|---|---|
| `minion_agent/llm/content.py` | `UserContentBlock`/`AssistantContentBlock`/`ToolResultContentBlock` role-specific aliases | MODIFIED (`LLM-F012`) — the generic `ContentBlock` alias is retained for internal generic helpers only | static type evidence, §0 |
| `minion_agent/llm/messages.py` | `UserMessage`/`AssistantMessage`/`ToolResultMessage.content` typed to their frozen role-specific unions; `text_of()` handles string content | MODIFIED (`LLM-F012`) | `tests/typing/valid_message_construction.py`, `test_text_of_a_string_valued_user_message_is_the_string_itself` |
| `minion_agent/session/derive.py` | `encode_message`/`decode_message` preserve `UserMessage.content`'s string-or-array representation exactly | MODIFIED (`SES-F009`) | `test_string_valued_user_message_round_trips_as_a_string`, `test_string_and_single_text_block_user_messages_remain_distinct_after_round_trip`, `string-user-message-round-trip.yaml` |
| `minion_agent/llm/transform_messages.py` | `TargetModel`, `NormalizeToolCallId`, `transform_messages()` — the single canonical transform seam | NEW (first pass), narrowed content types this pass | `XFORM-001`..`012`, `XFORM-R001`, all 46 tests in `tests/llm/test_transform_messages.py` |
| `tests/conformance/transform_runner.py` | Thin XFORM scenario runner | NEW (first pass); `_usage()` no longer fabricates (`XFORM-R002`) this pass | drives all 13 `conformance/agent/*.yaml` transform scenarios |
| `tests/conformance/test_transform_conformance.py` | Parametrized executor over `transform`-keyed `conformance/agent/*.yaml` files | NEW | 13/13 passing |
| `tests/conformance/test_agent_conformance.py` | Full agent-loop scenario executor | MODIFIED — scenario glob now excludes `transform`-keyed files | unaffected full-loop scenarios still 100% passing |
| `tests/conformance/session_runner.py` | Session scenario executor | MODIFIED (additive) — optional `transform_target` step composes the real Session and XFORM seams (`SES-013`); `_user_content()`/`_user_detail()` preserve string representation (`SES-F009`) | activates `SES-013`; new `user_details` observable |
| `tests/llm/test_transform_messages.py` | Full behavior-matrix unit tests | NEW (first pass), +8 tests this pass (`XFORM-R001` string-content matrix) | 46 tests, see §5 |
| `tests/typing/valid_message_construction.py` | Permanent static-type evidence for the frozen role-specific content unions | NEW this pass (`LLM-F012`) | `mypy src/minion_agent tests/typing/valid_message_construction.py` — see §16 |

**No existing partial/duplicate transformation logic was found anywhere in the codebase before this
pass** (`grep`-searched `src/`/`tests/` for `transform_messages`, `image omitted`, `No result
provided`, model/capability abstractions — all absent). This is a clean-slate implementation, not a
consolidation of scattered logic.

**Not yet wired into a production request path.** No real (non-mock) provider adapter exists yet
(Phase 5 explicitly deferred, per `project_assurance_layer_sequencing`). This mirrors Layer 02's own
`LLM-012`/`LLM-020`/`LLM-021` disposition for the identical reason: the mock adapter has no real
target-model wire constraints to reconcile against, so there is no real caller to wire this into yet.
`transform_messages()` is a complete, real, independently-tested library function waiting for one.

**Legacy null-content boundary, deliberately placed inside `transform_messages()` itself, not at
Session's decode boundary.** Considered placing this check in `session/derive.py::decode_message`
instead (a natural point where genuinely untyped/legacy JSON enters the system), but rejected: (1)
it would require modifying a certified, frozen Layer-03 file for a Layer-04 requirement, against the
explicit instruction to treat Layers 01-03 as dependencies, not areas to opportunistically reopen;
(2) Pi's own placement is inside `transformMessages()` itself, and Pi's comment ("untyped callers —
custom tools, hand-built histories, old session files") describes a broader set of entry points than
only Session deserialization; (3) Minion's typed `Message` dataclasses do not enforce field types at
runtime (Python, unlike compiled TS-with-erased-types-at-runtime, still permits direct construction
with a wrong-typed value), so the same defensive posture Pi takes is both possible and appropriate at
the same call boundary Pi itself uses. Exercised via `dataclasses.replace(..., content=None)` in
tests — a legitimate, intentional runtime-typing violation, not a bug.

---

## 11. Runner thinness review

Both new runners (`transform_runner.py`, `session_runner.py`'s extension) read in full this pass,
specifically checking for every prohibited behavior the audit instruction named:

```text
image replacement            NOT present -- real transform_messages() does it
placeholder dedupe           NOT present
thinking filtering           NOT present
signature stripping          NOT present
ID normalization             NOT present -- normalize_tool_call_ids only supplies the callback's
                              return values; the map-building/rewrite logic is the real function's
orphan detection              NOT present
synthetic result creation     NOT present
errored/aborted filtering      NOT present
```

`transform_runner.py::_normalizer()` deserves explicit note: it builds a Python closure from the
scenario's literal `old_id -> new_id` mapping, but the closure only *looks up* a value the scenario
already specified — it performs no normalization decision itself, exactly matching a real
Provider-supplied callback's shape (Pi's own `anthropic-messages.ts::normalizeToolCallId` is
likewise a pure function the real `transformMessages()` invokes, never a value the function computes
internally). This is real orchestration evidence, not runner fabrication.

---

## 12. Failure model

`transform_messages()` raises nothing for any input this pass's scenarios or tests construct — every
branch has a defined output, including the legacy-null and role-mismatched-content defensive paths.
`transform_runner.py` still wraps the call in `try/except` and reports a structured `{"type",
"message"}` error (mirroring `agent_runner.py`/`session_runner.py`'s own established pattern)
because a future finding could require rejecting some input; none currently does. No
`expect: {error: ...}` scenario exists yet because none is needed — not because the mechanism is
unbuilt.

## 13. Security review

`arguments: dict[str, Any]` (tool-call arguments) and `data: bytes | None` (image bytes) pass through
`transform_messages()` as opaque values; nothing in this module interprets, executes, or formats them
into anything execution-adjacent. Grepped for `eval`/`exec`/`__import__`/`pickle`/`subprocess`/
`os.system` — none found. No security finding.

## 14. Reliability review

`transform_messages()` is a pure function: no I/O, no mutable module-level state, no shared state
between calls. The only non-pure element is `_now_ms()` (wall-clock read for a synthesized result's
timestamp) — read-only, side-effect-free, and explicitly excluded from every determinism assertion
for exactly that reason (§5's cross-cutting invariant test strips synthetic timestamps before
comparing). No reliability finding.

---

## 15. Findings

**First-pass findings (Pi audit against the prior condensed spec, before any Rust review) — four,
correctly counted here after the `XFORM-R004` bookkeeping fix (§0.4):**

| Category | Finding | Disposition |
|---|---|---|
| `CONTRACT_ASSURANCE_DEFECT` | Prior spec missing the same-model-redacted-thinking retention rule | `RESOLVED` — `spec/target-model-transformation.md` rule 8 added (§4) |
| `CONTRACT_ASSURANCE_DEFECT` | Prior spec's placeholder-dedup rule imprecise about mechanics | `RESOLVED` — rule 4 rewritten precisely (§4) |
| `CONTRACT_ASSURANCE_DEFECT` | Prior spec's image-downgrade rules did not state the target-capability gate explicitly, admitting an always-downgrade or per-message reading | `RESOLVED` — rules 2/3 now state the gate explicitly (§4) |
| `CONTRACT_ASSURANCE_DEFECT` | Prior manifest/spec implied `transform_messages` owns a concrete tool-call-ID algorithm | `RESOLVED` — spec rule 13 and `AI-023` rewritten to state the real injected-callback architecture (§4, §7) |

**Second-pass findings (independent Rust implementation-owner review of the first candidate,
`04-target-model-transformation-rust-review.md`) — kept distinct from the four above, not merged
into their count:**

| ID | Category | Finding | Disposition after second pass | Disposition after third pass |
|---|---|---|---|---|
| `XFORM-R001` | `PI_PARITY_DEFECT` | Valid string-valued `UserMessage.content` corrupted by the non-vision image-downgrade path | `PARTIALLY RESOLVED` (§0.1) — runtime branch fixed, but the public `UserMessage.content` type itself still excluded the string shape, so the second Rust review correctly rejected this as still open | `RESOLVED` (complete — §0.9, root cause fixed upstream at `LLM-F012`, §0.7) |
| `XFORM-R002` | `CONTRACT_ASSURANCE_DEFECT` | Canonical XFORM schema incomplete/insufficiently strict (string content, rich fields, empty identity, empty `expect`) | `PARTIALLY RESOLVED` (§0.2) — the listed gaps were fixed, but a `usage`-requiredness gap not in the original finding list was found by the second review's own independent probing and remained open | `RESOLVED` (§0.9 — `usage`/`Cost` requiredness added, runner fabrication removed) |
| `XFORM-R003` | `CONTRACT_ASSURANCE_DEFECT` | `AI-013` cited Question-A XFORM evidence as Question-B provider-wire replay evidence | `RESOLVED` (§0.3) — confirmed `APPROVED` by the second review, not reopened | `RESOLVED` (unchanged) |
| `XFORM-R004` | `CONTRACT_ASSURANCE_DEFECT` | Assurance history recorded three first-pass findings when four were actually repaired | `PARTIALLY RESOLVED` (§0.4) — the finding-count history was corrected, but stale `12`-count current-state statements elsewhere in this document were not, and the second review caught the remaining inconsistency | `RESOLVED` (§0's table headers and §8/§10/§18 all now consistently say 13) |

**Third-pass findings (independent Rust implementation-owner review of the second candidate,
`04-target-model-transformation-rust-r001-r004-rereview.md`) — the root-cause reclassification
itself, recorded here at the layer where it was discovered even though its fix landed in Layer
02/03's own assurance records:**

| ID | Category | Finding | Owning layer | Disposition |
|---|---|---|---|---|
| `LLM-F012` | `PI_PARITY_DEFECT` | `UserMessage`/`AssistantMessage`/`ToolResultMessage.content` were typed `tuple[ContentBlock, ...]` uniformly, excluding the frozen role-specific unions (`spec/llm.md`) — most visibly, `UserMessage.content` excluded its own `string` alternative | Layer 02 | `RESOLVED`, Python/shared side (§0.7); Rust delta review pending; full record `assurance/layers/02-llm.md` §0 |
| `SES-F009` | `CONTRACT_ASSURANCE_DEFECT` + Python implementation defect | `session/derive.py::encode_message`/`decode_message` computed `content` uniformly before role dispatch, unable to preserve a real string-valued `UserMessage.content` through persistence | Layer 03 | `RESOLVED`, Python/shared side (§0.8); Rust delta review pending; full record `assurance/layers/03-session-artifacts.md` §0 |

**Other categories, all passes:**

| Category | Finding |
|---|---|
| `PARITY_NEUTRAL_HARDENING` | none |
| `PARITY_CONSTRAINED_RISK` | none |
| `PI_BEHAVIOR_UNCERTAIN` | none — every rule traces to a specific read line of the pinned source |

No active `PI_PARITY_DEFECT`, `PI_BEHAVIOR_UNCERTAIN`, or `CONTRACT_ASSURANCE_DEFECT` remains for
current-layer scope as of this document. The rejected first candidate and its full finding set are
preserved above (§0), not erased, as positive assurance evidence that the two-language review
process caught real gaps before certification.

---

## 16. Python gates

**First pass (pre-rejection candidate `84c6ba2`):** 804 passed, 29 xfailed, 0 failed, 100.00%
coverage; `ruff`/`mypy` clean. One coverage gap surfaced mid-pass (a structurally-unreachable-
per-schema `ImageBlock`-in-assistant-content defensive fallback, `transform_messages.py:185`) was
closed with a real test
(`test_a_role_invalid_block_the_schema_forbids_still_passes_through_defensively`), not a coverage
suppression — no `pragma: no cover` was added, though two exist elsewhere in the codebase as
established precedent.

**Second pass (after the first `XFORM-R001`..`R004` remediation, superseded by the third pass
below — kept for the historical record, not reused as current-state evidence):**

```text
full pytest (coverage enabled): 813 passed, 29 xfailed, 0 failed, 100.00% coverage
  -- +9 tests vs. the first pass: 7 new tests/llm/test_transform_messages.py tests (XFORM-R001's
     first, incomplete fix -- the runtime branch only, see §0.1) plus +1 net-new canonical
     scenario (string-user-content-survives-transformation.yaml: 13 XFORM scenarios now vs. 12).
     (This "+9" arithmetic itself was corrected here from an earlier draft that miscounted it as
     "2 net-new canonical scenarios" -- exactly one was added, not two; the second Rust re-review,
     `XFORM-R004`, correctly flagged this and the stale 12-counts below as still unresolved at
     that point.)
ruff check .: All checks passed
mypy (configured scope, src/minion_agent): Success, no issues found in 57 source files
```

**Third pass, fresh (this pass, after `LLM-F012`/`SES-F009`/`XFORM-R001`(complete)/`XFORM-R002`
remediation — not reused from either prior pass):**

```text
full pytest (coverage enabled): 818 passed, 29 xfailed, 0 failed, 100.00% coverage
  -- +5 tests vs. the second pass's 813, precisely accounted (git-diff-verified, not estimated):
     3 new named unit tests -- test_text_of_a_string_valued_user_message_is_the_string_itself
     (tests/llm/test_messages.py), test_string_valued_user_message_round_trips_as_a_string,
     test_string_and_single_text_block_user_messages_remain_distinct_after_round_trip (both
     tests/session/test_derive.py) -- plus 2 new parametrized cases from the one new canonical
     scenario conformance/session/string-user-message-round-trip.yaml, one each in
     tests/conformance/test_schema_validation.py::test_scenario_validates
     and tests/conformance/test_session_conformance.py::test_session_scenario (confirmed via
     `pytest --collect-only -k string-user-message-round-trip`: exactly 2 collected items).
     tests/typing/valid_message_construction.py is mypy-only evidence, not a pytest test, and
     contributes 0 to this count. Every pre-existing Layer 01/02/03 test unchanged and still green.
ruff check .: All checks passed
mypy (configured scope, src/minion_agent): Success, no issues found in 57 source files
mypy src/minion_agent tests/typing/valid_message_construction.py (permanent static-type evidence
  for LLM-F012, run explicitly -- not part of the default scoped mypy gate above): Success, no
  issues found in 58 source files
```

---

## 17. Rust applicability and review status

**Rust implementation:** determination pending the shared-contract review itself. This document
does not presume the answer — the fresh Rust implementation-owner review (handoff package:
`04-target-model-transformation-rust-handoff.md`) must state explicitly whether Rust implementation
is `REQUIRED NOW` or `EXPLICITLY DEFERRED BY PLAN`, with normative process/design evidence, matching
the same discipline Layers 01-03 established. No Rust code was written, modified, or even scaffolded
this pass.

**What the handoff asks Rust to verify independently** (not to trust from this document): the Pi
source mapping (all 15 rules against the pinned commit), the shared-contract repair (§4), the
`XFORM-###` requirement table (§5), the manifest corrections (§7), the new schema/runner's language
neutrality and thinness (§8, §11), idiomatic-typed-Rust feasibility for `TargetModel`/
`NormalizeToolCallId`/`transform_messages`, and whether a typed Rust implementation can satisfy every
rule without `serde_json::Value`-typed shortcuts.

---

## 18. Freeze gate

```text
Pi pinned transform source fully audited?              YES (§3)
AI-020..026 reconciled?                                 YES (§7)
XFORM-### requirement table complete?                    YES, 13/13 PASS (12 original + XFORM-R001, §5)
Language-neutral spec complete?                          YES (§4)
Canonical scenario ownership complete?                   YES, 13/13 filled, 0 misclassified (§8)
Session Layer-04 deferment activated and green?           YES (§9)
Provider replay simulated anywhere?                      NO (§6, §11)
Python implementation uses one real transform seam?       YES (§10)
Python runner thin?                                       YES (§11)
Python tests/gates green?                                  YES, fresh (§16)
Shared contract independently Rust-reviewed?                NOT YET
Rust implementation requirement explicitly determined?       NOT YET
Active PI_PARITY_DEFECT / PI_BEHAVIOR_UNCERTAIN /
  CONTRACT_ASSURANCE_DEFECT?                                 NONE (§15)
```

Layer 04 is **not yet eligible for `CERTIFIED`** — the two unmet gates are both the same one thing:
independent Rust implementation-owner review has not yet happened. Everything within Python/shared
control is green. Layer 05 is not started.
