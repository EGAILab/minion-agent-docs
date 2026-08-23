# Layer 03 Session + Artifacts — Rust Implementation-Owner Contract Review

**Review date:** 2026-08-23

**Reviewer role:** Rust implementation owner

**Reviewed `minion-agent`:** `3d6ffa41c3bb8c418fbe0fd2a2d34de58556896e`

**Reviewed `minion-agent-docs`:** `c273df128c4c9d3570925b594d1c438e6ee81fee`

**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`

## Decision

```text
shared-contract review
    REJECTED — CONTRACT_ASSURANCE_DEFECT

Rust Session implementation before shared/Python Layer-03 certification
    EXPLICITLY DEFERRED BY PLAN

Layer 03
    IN_AUDIT
```

No Python implementation or shared semantic artifact was modified during this review.

## Contract defects

### 1. `assistantDetail` is not a complete persisted `AssistantMessage`

`conformance/schema/session-scenario.schema.json` sets
`additionalProperties: false` on `assistantDetail` but omits:

```text
provider
model
timestamp
error_message
```

All four belong to the frozen Layer-02 `AssistantMessage` vocabulary in `spec/llm.md`. Pinned Pi
persists the complete `AgentMessage` value in
`packages/agent/src/harness/session/types.ts::MessageEntry.message`; Pi's
`packages/ai/src/types.ts::AssistantMessage` includes those fields.

Fixing constant values inside a conformance runner is not a Session semantic limitation. A Rust
Session implementation could drop or fabricate these fields and still satisfy the current
`rich-assistant-message-round-trip.yaml` assertions. The scenario therefore does not prove the
complete Session round trip required by `spec/session.md`.

Required remediation: make the values scriptable through the canonical append input and observable
through the canonical reconstructed assistant detail. `timestamp` uses the normative numeric time
representation; `error_message` must preserve absence/null separately from a concrete string.

### 2. `toolResultDetail` is not a complete persisted `ToolResultMessage`

The closed `toolResultDetail` definition omits at least:

```text
tool_call_id
timestamp
```

Pinned Pi persists both through `MessageEntry.message`; the frozen Layer-02 vocabulary includes both.
The Python runner currently fixes these values rather than allowing the scenario to prove their
round trip. A conforming runner must observe them from the real reconstructed message.

### 3. `step.append` admits role-incompatible fields

The schema accepts combinations including:

```text
role=user with stop_reason
role=assistant with tool_name/details
role=tool_result without a tool-call identity
```

The Python runner reads fields conditionally and silently ignores incompatible accepted fields. An
idiomatic Rust tagged enum would naturally reject these inputs, so the current DSL permits divergent
runner behavior.

Required remediation: use role-discriminated append variants, or define and enforce one equivalent
language-neutral downstream validation rule. The runner must not silently discard schema-valid
fields.

### 4. `contentBlock` is not a discriminated union

The schema requires only `type` and places every variant field in one broad object. Adversarial
validation confirmed that it accepts:

```text
text without text
thinking without thinking
image with neither data nor reference
image with both data and reference
text carrying tool-call-only fields
tool_call carrying text-only fields
```

This is incompatible with the frozen typed content vocabulary and cannot map naturally to a Rust
enum without runner-local policy. Required remediation: define closed variants discriminated by
`type`, including the exclusive image-source rule.

## Independently reproduced schema behavior

Using the repository's Draft 2020-12 schema validator:

```text
user + assistant stop_reason              VALID (incorrect)
tool_result without tool-call identity    VALID (incorrect)
assistant + tool-result-only fields       VALID (incorrect)

assistantDetail.provider                  INVALID (omitted closed field)
assistantDetail.model                     INVALID (omitted closed field)
assistantDetail.timestamp                 INVALID (omitted closed field)
assistantDetail.error_message             INVALID (omitted closed field)

text block without text                   VALID (incorrect)
thinking block without thinking           VALID (incorrect)
image without a source                    VALID (incorrect)
image with data and reference             VALID (incorrect)
cross-variant block fields                 VALID (incorrect)
```

## Pi ownership audit

Sources independently inspected at the pinned revision:

```text
packages/ai/src/types.ts
    UserMessage
    AssistantMessage
    ToolResultMessage

packages/agent/src/types.ts
    AgentEvent

packages/agent/src/harness/session/types.ts
    Entry / MessageEntry
    LaneRecord
    OperationStartedRecord
    StepAttemptRecord
    ToolStartedRecord
    UsageRecord
    SessionStorage / SessionTree

packages/agent/src/harness/session/session.ts
    Session
    appendMessage / appendEntry
    commitEntry / commitRecord

packages/agent/src/harness/session/context.ts
    deriveSessionContextState
    defaultContextEntryTransform
    sessionEntryToContextMessages
    buildSessionContext

packages/agent/src/harness/messages.ts
    convertToLlm

packages/agent/src/agent-loop.ts
    provider-neutral message conversion boundary

packages/agent/src/harness/compaction/compaction.ts
    compaction preparation, retained history, and summaries
```

### `SES-F002`

Rust approves **Outcome A**, with this precise boundary:

```text
Agent
    owns live lifecycle notification identity, meaning, and timing

Session
    owns settled persistent state
    may store valid producer-owned operational/log-only data
    does not acquire semantic ownership of that producer vocabulary
    does not recreate the live AgentEvent notification stream
```

Pi does not persist its `AgentEvent` union as Session entries. It does persist separate
operation/step/tool recovery records. This supports the mixed boundary and does not create a
Layer-03 lifecycle-vocabulary defect.

### `SES-F003`

Rust approves the by-value event-name and Session/Agent/XFORM boundary clarification. Event identity
is the serialized string value; enum singleton, allocation, pointer, reference, and language object
identity do not participate.

## Session/XFORM boundary

Confirmed:

```text
Session projection
    persisted/reconstructed provider-neutral message vocabulary

XFORM
    target-model compatibility transformation after Session projection
```

`request-reconstruction-after-target-transform.yaml` is correctly deferred to Layer 04. Neither a
Python nor Rust Session runner may implement target-model transformation to make it pass.

## Scenario inventory

```text
17 total
16 current Session scenarios
 1 Layer-04 deferred scenario
 0 Agent-family scenarios misplaced under session/
 0 otherwise invalid family classifications
```

The family placement is sound. The rejection concerns schema and observation completeness.

## Headers, artifacts, and `MINION-003`

`record_header` drives real Session state, and the Python runner observes real reconstruction rather
than rebuilding it. Artifact count is read from the real store. The canonical cases prove component
reuse and reconstructed request equality without freezing the hash algorithm or physical layout.

`MINION-003` traceability is approved: its intentional-divergence disposition is honest, both cited
canonical scenarios are real, Python paths are current, and Rust is accurately recorded as planned
Phase-2 work rather than fabricated evidence.

## Certification applicability

Rust currently has no Session implementation. This does not by itself block shared/Python Layer-03
certification because the adopted process explicitly permits separate implementation status:

- `process/implementation-conformance-workflow.md` §7.3 defines shared/Python certification with
  Rust `NOT_IMPLEMENTED — planned Phase 2` as valid.
- §5.9 does not require a later, not-yet-implemented language layer merely for the current
  implementation to certify.
- Project invariant 19 permits one language to remain `NOT_IMPLEMENTED` while another certifies.
- `assurance/fidelity-assurance-method.md` §14 states the same rule explicitly.
- `pi-parity-manifest.yaml` assigns `MINION-002` and `MINION-003` to Rust Phase 2.

Therefore:

```text
Rust Session implementation
    EXPLICITLY DEFERRED BY PLAN

future owner
    Rust implementation owner

future phase
    Rust Phase 2 Session + Artifacts

trigger
    corrected shared Layer-03 contract approved
    plus a current executable Rust plan rewritten against the 2026-08-20 authority

certification impact of Rust NOT_IMPLEMENTED
    NON-BLOCKING
```

The current Layer-03 certification blocker is the rejected shared contract, not the absence of Rust
Session code.

## Required next action

The shared/Python owner should narrowly repair the four defects above, rerun schema and Python
evidence, publish a corrected candidate SHA, and request a fresh Rust implementation-owner review.
The prior rejection does not become approval merely because the candidate is amended.
