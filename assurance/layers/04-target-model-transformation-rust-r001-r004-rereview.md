# Rust implementation-owner re-review — Layer 04 XFORM R001-R004

Date: 2026-08-24

## Reviewed state

- `minion-agent`: `42ef135921e64bc847cc43c9fa47bc45c936c879`
- `minion-agent-docs`: `d8ebcbe6b6b88b7d7c58568725049a47c4268f16`
- first rejected candidate: `minion-agent@84c6ba2`, `minion-agent-docs@a4eef91`
- first Rust rejection: `minion-agent-docs@0f3d4191722b29f9bf81fc70352648ae93cdd716`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`

Both repositories exactly matched the requested remediation candidate. No later semantic commit was
included. The unrelated dirty Phase-5 review-feedback file was preserved and excluded.

## XFORM-R001 re-review

The runtime corruption is fixed in
`minion-agent-python/src/minion_agent/llm/transform_messages.py::_downgrade_unsupported_images`:
the implementation now checks `isinstance(message.content, str)` before block traversal. Direct
calls through the real seam produced:

```text
input                                            vision       nonvision    cross-target
"hello"                                          "hello"      "hello"      "hello"
""                                               ""           ""           ""
"   "                                            "   "        "   "        "   "
"(image omitted: model does not support images)" unchanged    unchanged    unchanged
```

The source value remained a string. Block-array image downgrade remained active. The new canonical
scenario `string-user-content-survives-transformation.yaml` invokes the real XFORM seam against a
non-vision target, and the runner does not contain the string-preservation semantic branch.

However, the certified public Python vocabulary remains wrong:

```python
class UserMessage:
    content: tuple[ContentBlock, ...]
```

It still excludes the frozen/Pi-valid `string | block-array` variant. A direct static probe reports:

```text
Argument "content" to "UserMessage" has incompatible type "str";
expected "tuple[TextBlock | ThinkingBlock | ImageBlock | ToolCallBlock, ...]"
```

The conformance runner returns `str | tuple[...] | None` from `_user_content()` and passes that into
the tuple-only dataclass constructor. Python accepts this only because annotations are not enforced
at runtime; it is not a typed modern input path. The candidate therefore fixes runtime output but
does not finish the public vocabulary part of the original parity finding.

```text
XFORM-R001
    REJECTED — PI_PARITY_DEFECT remains
```

Required narrow repair: make the real `UserMessage.content` type express the already-frozen
`str | tuple[UserContentBlock, ...]` contract, update affected typed helpers, and remove the runner's
need to pass a statically invalid modern value. Legacy `None` should remain isolated at the
compatibility boundary.

## XFORM-R002 re-review

Independent Draft 2020-12 schema probes against
`conformance/schema/agent-transform-scenario.schema.json` produced:

```text
valid user string             ACCEPT
valid user block array        ACCEPT
legacy user null              ACCEPT
empty target.provider         REJECT
empty target.api              REJECT
empty target.model_id         REJECT
rich AssistantMessage         ACCEPT
minimal valid Assistant       ACCEPT
Assistant + ImageBlock        REJECT
rich ToolResultMessage        ACCEPT
ToolResult missing tool_name  REJECT
ToolResult tool_name=null     REJECT
expect: {}                    REJECT
unknown message property      REJECT
user + ThinkingBlock          REJECT
user + ToolCall               REJECT
tool_result + ThinkingBlock   REJECT
tool_result + ToolCall        REJECT
```

Those advertised repairs are real. But a requiredness probe not present in the remediation matrix
also produced:

```text
AssistantMessage without usage    ACCEPT
```

This contradicts the certified Layer-02 shape in `spec/llm.md`, where `AssistantMessage.usage` is
required (no optional marker). The schema declares `usage` as a property but omits it from both the
input and output assistant `required` lists. The nested `Usage` and `Cost` definitions likewise do
not require their non-optional fields.

The thin-runner boundary then masks the gap: `_message()` calls `_usage(raw.get("usage"))`, and
`_usage(None)` manufactures `Usage()` defaults. Legacy compatibility is specified only for null or
undefined **content**, not for absent usage. Supplying required semantic state in the runner means a
schema-valid scenario does not necessarily traverse the real typed API represented by its data.

The richer field set is otherwise language-neutral and naturally representable in Rust. Role
discrimination, non-empty target identity, required non-null `tool_name`, unknown-field rejection,
and non-empty observation are correct.

```text
XFORM-R002
    REJECTED — CONTRACT_ASSURANCE_DEFECT remains
```

Required narrow repair: align assistant `usage` requiredness (including the non-optional Usage/Cost
members) with the certified Layer-02 serialization shape and stop the runner from inventing missing
required usage. Preserve the separate, explicit legacy-null-content boundary.

## XFORM-R003 re-review

`AI-013` now explicitly separates:

- Question A: Layer-04 message-level signature survival/stripping; and
- Question B: Phase-5 Responses-family provider-wire replay, not yet evidenced.

The row still lists the XFORM scenarios, but now labels them prerequisite Question-A evidence only
and explicitly states they do not prove a Responses payload. The Python and Rust targets remain
Phase-5 replay. `AI-021` correctly owns the generic XFORM thinking evidence.

The assurance wording also says “0 Layer-04-owned scenarios deferred to Phase 5,” while explicitly
preserving the separate Phase-5 provider-wire obligation.

```text
XFORM-R003
    APPROVED
```

## XFORM-R004 re-review

The primary history correction is substantively accurate. It records the first-pass four as:

1. same-model redacted-thinking retention;
2. placeholder deduplication mechanics;
3. explicit image-capability gate; and
4. injected ID-normalization ownership.

It separately preserves the first rejected candidate, Rust rejection commit, and later R001-R004
set. The image gate is correctly classified as a `CONTRACT_ASSURANCE_DEFECT` rather than cosmetic
clarification.

But the assurance document remains internally inconsistent after claiming the bookkeeping repair:

- section 2 still says `12 XFORM scenarios`;
- the implementation inventory still says the runner drives `all 12` and `12/12 passing`;
- the freeze gate still says `12/12 filled`;
- the second-pass gate narrative says the move from 12 to 13 represents “2 net-new canonical
  scenarios,” although exactly one XFORM scenario was added;
- other sections correctly say 13.

The requirement-table wording `XFORM-001..012` may legitimately remain twelve original numbered
requirements plus R001, but scenario inventory claims must consistently say thirteen.

```text
XFORM-R004
    REJECTED — CONTRACT_ASSURANCE_DEFECT remains
```

Required narrow repair: update every stale inventory/gate count and correct the test-count
explanation without erasing either audit pass.

## Canonical and regression evidence

Fresh enumeration found exactly 13 transform-keyed scenarios:

1. `aborted-assistant-excluded-from-replay.yaml`
2. `cross-model-redacted-thinking-omitted.yaml`
3. `cross-model-signatures-stripped.yaml`
4. `cross-model-thinking-converts-to-text.yaml`
5. `errored-assistant-excluded-from-replay.yaml`
6. `nonvision-tool-image-placeholder.yaml`
7. `nonvision-user-image-placeholder.yaml`
8. `null-content-normalizes-empty.yaml`
9. `orphan-tool-result-synthesized.yaml`
10. `same-model-thinking-signature-replayed.yaml`
11. `same-model-unsigned-thinking-not-replayed.yaml`
12. `string-user-content-survives-transformation.yaml`
13. `tool-call-id-normalization.yaml`

All remain Layer-04-owned and execute through the one real
`minion_agent.llm.transform_messages.transform_messages` seam. Neither scenario runner performs
provider-wire replay.

Focused XFORM language tests, all XFORM canonical tests, and Session conformance tests were run
together and passed (78 collected tests, 0 failures). Regression inspection and focused execution
confirmed that the previously approved semantics remain unchanged:

- same-model redacted thinking retained;
- thinking compatibility matrix unchanged;
- image capability and placeholder dedup unchanged;
- full target identity triple unchanged;
- ID normalization remains an injected policy;
- cross-model signatures strip correctly;
- orphan synthesis uses the real source tool name;
- error/aborted exclusion ordering unchanged;
- source values are not mutated;
- retained rich fields are preserved through dataclass replacement;
- Session composes real reconstruction with real XFORM and does not persist the transformed view;
- no real provider path exists, and the Phase-5 wiring/replay obligation remains explicit.

## Active findings and verdict

```text
PI_PARITY_DEFECT
    XFORM-R001 remains open (public UserMessage type excludes string)

CONTRACT_ASSURANCE_DEFECT
    XFORM-R002 remains open (required usage accepted as absent and invented by runner)
    XFORM-R004 remains open (stale/inconsistent assurance inventory arithmetic)

PI_BEHAVIOR_UNCERTAIN
    none

XFORM-R003
    resolved
```

Formal verdict:

```text
LAYER 04 XFORM SHARED CONTRACT
    REJECTED — PI_PARITY_DEFECT
```

## Rust disposition

Per the required review gate, Rust implementation timing was not adjudicated and no Rust code,
runner, test, branch, or PR was created.

```text
Rust Layer-04 implementation
    BLOCKED

next owner
    Python/shared assurance

Layer 04 status
    IN_AUDIT

Layer 05 started
    NO
```
