# Rust implementation-owner review — Layer 04 target-model transformation

Date: 2026-08-24

## Reviewed state

- `minion-agent`: `84c6ba2a3a1db844f0ea4ad12f5b9aa98c3213fd`
- `minion-agent-docs`: `a4eef91c998ab7c1a4b128ac6b50c32cc3f696a8`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- dependency baseline: `minion-agent@e9e45ed`, `minion-agent-docs@869a338`

No later candidate commits existed. The unrelated dirty Phase-5 feedback document was preserved and
excluded. No Rust implementation was changed because the shared contract is rejected below.

## Pinned Pi audit

Read in full:

- `packages/ai/src/api/transform-messages.ts`
- the message/content/model declarations in `packages/ai/src/types.ts`
- all six real call sites in `anthropic-messages.ts`, `bedrock-converse-stream.ts`,
  `google-shared.ts`, `mistral-conversations.ts`, `openai-completions.ts`, and
  `openai-responses-shared.ts`, including their normalizer ownership.

Independent Pi pipeline:

1. Normalize every `content == null` to `[]`.
2. If the target lacks image input, downgrade user-array and tool-result images with exact
   role-specific placeholders. A user string is not an array and passes unchanged.
3. In one forward pass, transform assistant content, invoke the optional cross-model ID callback,
   record changed call IDs, and rewrite later matching results by original ID.
4. In a second forward pass, flush prior pending calls before each assistant/user boundary, exclude
   error/aborted assistants after the prior flush but before tracking their own calls, and flush at
   end of history.

Pi placeholder state is per message. Consecutive raw images collapse; any non-image resets the
state except literal text equal to that role's placeholder, which suppresses the following image.
User and tool-result placeholders are distinct.

Pi supplies no generic ID algorithm. The optional callback is invoked for every cross-model call in
transcript order. The map is recorded only when the returned ID differs; same-model and unmapped
results remain unchanged. Pi defines no additional collision policy beyond ordinary map overwrite.

No Pi behavior was uncertain.

## Four advertised repairs

- Same-model redacted thinking: **correct**. Pi checks redaction first; same-model retains the exact
  block regardless of text/signature and cross-model drops it.
- Placeholder mechanics: **correct** and matches the state machine above.
- Image capability gate: **correct semantic repair**. Pi reads target model input capability once;
  it does not use model-name heuristics or per-message policy.
- ID-normalization callback ownership: **correct**. Generic XFORM owns orchestration; provider/API
  code owns the concrete policy.

The assurance bookkeeping is inconsistent. Section 4 explicitly classifies all four as repaired
`CONTRACT_ASSURANCE_DEFECT`s, while section 15 lists only three and omits the image capability-gate
finding. The gate was not merely cosmetic: the prior rule allowed always-downgrade and per-message
interpretations, so it is the fourth contract-assurance defect. The final history must record four.

## Thinking matrix

For same `provider + api + model_id`:

- redacted, any text/signature: retained unchanged;
- non-redacted, truthy signature, any text including empty/blank: retained unchanged;
- non-redacted, absent/empty signature, non-blank text: retained unchanged;
- non-redacted, absent/empty signature, empty/blank text: omitted.

Cross-model (any one identity component differs):

- redacted, any text/signature: omitted;
- non-redacted, non-blank text, signed or unsigned: converted to fresh `TextBlock{text}`;
- non-redacted, empty/blank text, signed or unsigned: omitted.

Cross-model conversion carries no thinking signature and generates no text signature. Ordinary text
loses `text_signature`. A tool call loses a truthy `thought_signature` but preserves an empty-string
signature because Pi uses a truthy check; `id`, `name`, `arguments`, and `namespace` otherwise
survive.

The spec's identity triple and thinking decision tree are complete and Pi-compatible.

## Manifest review

- `AI-020`: Pi citation accurate, but the rule/evidence is incomplete because the valid
  string-content user branch is absent from spec/schema/tests and broken in Python.
- `AI-021`: accurate and sufficiently traced.
- `AI-022`: accurate; namespace and the empty-signature truthiness behavior are stated.
- `AI-023`: accurate generic orchestration/provider-policy ownership split.
- `AI-024`: semantic rule is accurate, but canonical output cannot prove complete preservation of
  real tool-result fields; see schema findings.
- `AI-025`: accurate, including the excluded assistant's own calls.
- `AI-026`: accurate for null/undefined compatibility and library ownership.

### Mandatory AI-013 cross-row result

`AI-013` still cites `same-model-thinking-signature-replayed` as evidence for
“Responses-family thinking/text signature replay.” The scenario now explicitly invokes only XFORM
and proves only Question A (block survival). It does not invoke a Responses encoder or prove
provider-wire replay (Question B). The manifest therefore contains stale/misleading evidence.

The Phase-5 replay obligation remains in prose and its target fields, but the `tests:` list falsely
presents prerequisite XFORM evidence as provider replay evidence. `AI-013` must separate:

- XFORM prerequisite retention evidence; and
- provider-wire replay evidence, explicitly deferred until Phase 5.

## Canonical schema and negative probes

The candidate has 12 XFORM scenarios under the existing `agent` family and activates one Session
composition scenario. No fourth canonical family was introduced. The runners are structurally
thin: parsing, typed construction, callback-policy construction, real library invocation, and
normalization only. The Session runner composes real Session derivation with real XFORM and does not
persist the transformed view.

However, `agent-transform-scenario.schema.json` is not a complete language-neutral contract:

1. **Valid user string content is rejected.** `inputMessage/user/content` permits only array or
   null, contradicting frozen `UserMessage.content: string | [...]` and pinned Pi.
2. **Certified rich fields are rejected under `additionalProperties:false`.** Assistant input and
   output omit `response_model`, `response_id`, `diagnostics`, `usage`, `deferred`, `error_message`,
   `raw_stop_reason`, and `end_turn`. Tool-result shapes omit `details`, `usage`, and
   `added_tool_names`; output also omits every tool-result timestamp, including timestamps that
   existed on real input. This prevents canonical proof that XFORM preserves untouched Layer-02
   state.
3. **Invalid empty target identity is accepted.** `provider`, `api`, and `model_id` lack the
   non-empty constraint already required by the frozen identity contract and typed Rust API.
4. **An empty `expect` object is accepted.** The schema requires neither `messages` nor `error` and
   does not require exactly one, allowing a scenario with no observable assertion.

Independent schema probes produced:

```text
valid user string       REJECTED (defect)
user block array        ACCEPTED
legacy user null        ACCEPTED
empty target triple     ACCEPTED (defect)
rich AssistantMessage   REJECTED (defect)
empty expect            ACCEPTED (defect)
assistant + image       REJECTED (correct)
```

The legacy-null exception is otherwise suitable for idiomatic Rust through a narrow compatibility
input enum; normal typed messages need not become nullable.

## Reproduced Python parity defect

Pinned Pi preserves string-valued `UserMessage.content` unchanged for both capable and incapable
targets because image downgrade is guarded by `Array.isArray(msg.content)`.

The candidate Python vocabulary is typed as tuple-only, despite the frozen Layer-02 string-or-block
contract. Directly constructing the Pi-valid value and calling the real XFORM seam gives:

```text
supports_images = true
    "hello" remains "hello"

supports_images = false
    "hello" becomes ("h", "e", "l", "l", "o")
```

The non-vision branch iterates the string as though its characters were content blocks. The schema
hides this production defect by rejecting the valid input. This is a `PI_PARITY_DEFECT` and also
exposes an incomplete XFORM shared contract/evidence surface.

## Ordering and other reviewed semantics

- Null normalization precedes downgrade, so null cannot be iterated.
- Content/ID transformation precedes error/aborted exclusion. Consequently, an excluded
  assistant can affect first-pass ID mapping for a later result; the normative pipeline order pins
  this Pi behavior even though the existing canonical scenario does not isolate it.
- Prior pending calls flush before an interrupting errored/aborted assistant; that assistant's own
  calls are never tracked or synthesized.
- Normalized tool-call IDs flow into pending calls and synthetic results; source order is retained.
- Synthetic results use the transformed call ID, the real call name, `No result provided`,
  `is_error=true`, and wall-clock timestamp.
- Python uses frozen dataclass replacement and does not mutate source objects. Unchanged values may
  be reused; the spec should not imply fresh allocation/object identity is normative when only
  source-value immutability is cross-language observable.

## Session and Phase-5 boundaries

`request-reconstruction-after-target-transform.yaml` is correctly active and thin:

```text
real Session persistence/derive
    -> real transform_messages
    -> ephemeral transformed observation
```

The original Session log retains the image and unresolved tool call. No Agent simulation or XFORM
logic exists in the Session runner.

Only the mock adapter exists today. Certifying a standalone transformation library before a real
provider is architecturally valid, provided Phase 5 must call this exact seam before provider
encoding and must not duplicate generic XFORM. The assurance prose states that obligation.

“Phase-5 deferred: 0” is safe only as “zero Layer-04-owned scenarios blocked on Phase 5.” It must
not be used to imply zero provider-wire replay obligations; `AI-013` still requires real Phase-5
evidence.

## Findings

### `PI_PARITY_DEFECT`

1. `XFORM-R001`: valid Pi/frozen user string content is absent from the XFORM spec/schema evidence
   and is corrupted by the Python non-vision transform path.

### `CONTRACT_ASSURANCE_DEFECT`

1. `XFORM-R002`: `agent-transform-scenario.schema.json` rejects valid frozen string/rich message
   states, accepts invalid empty target identity, and permits assertion-free `expect` objects.
2. `XFORM-R003`: `AI-013` cites Question-A XFORM retention as evidence for Question-B Responses
   provider-wire replay.
3. `XFORM-R004`: the assurance history says four contract repairs but records only three findings;
   the image capability gate is the omitted fourth finding.

### Other categories

- `PI_BEHAVIOR_UNCERTAIN`: none.
- `PARITY_NEUTRAL_HARDENING`: none required for this verdict.
- `PARITY_CONSTRAINED_RISK`: none.

Focused candidate tests remain green (70 focused XFORM/Session conformance and language tests), but
the missing valid input and schema/evidence gaps explain why green tests do not support approval.

## Formal verdict

```text
LAYER 04 XFORM SHARED CONTRACT
    REJECTED — PI_PARITY_DEFECT
```

The shared contract/evidence must be narrowly repaired and returned with a new candidate SHA.

## Rust disposition

```text
Rust Layer-04 implementation
    NOT STARTED — contract gate rejected

Rust implementation remediation
    BLOCKED

next owner
    Python/shared assurance

Layer 04 status
    IN_AUDIT

Layer 05 started
    NO
```

Because approval failed, Rust implementation timing was not adjudicated and no Rust code, runner,
test, branch, or PR was created.
