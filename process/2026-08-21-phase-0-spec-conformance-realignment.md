# Minion Agent — Phase 0 Spec and Conformance Realignment

**Date:** 2026-08-21  
**Authority:** frozen `2026-08-20-minion-agent-design.md`  
**Pi baseline:** `b7bb00b936dbe21b8e160b3e89efdec361846699`  
**Status:** executable realignment plan

## Goal

Convert the frozen master design into the two normative artifacts it defines:

1. `minion-agent-docs/spec/` — general language-neutral semantic rules.
2. `conformance/` — finite executable compatibility cases.

For covered examples, canonical conformance is the executable oracle. The spec governs the general rule outside finite examples. A contradiction is a release-blocking spec defect, not a precedence choice.

## Phase 0 outputs

```text
pi-parity-manifest.yaml
minion-agent-docs/spec/
    authority.md
    llm.md
    target-model-transformation.md
    session.md
    agent.md
    tools.md
    harness.md
conformance/
    schema/
    runtime/
    session/
    agent/
```

Do **not** create `conformance/llm/`; LLM-visible behavior belongs in the existing `agent/` and `session/` families unless the frozen master is deliberately revised.

## 1. Spec realignment

### `spec/authority.md`

Pin:

- Pi revision `b7bb00b936dbe21b8e160b3e89efdec361846699`.
- mandatory Pi-fidelity method;
- adopted / deferred parity / intentional divergence dispositions;
- spec-vs-conformance authority split;
- drift procedure;
- parity-manifest obligation;
- normative string identity compared by value.

### `spec/llm.md`

Pin the complete cross-language serialized vocabulary:

- `TextBlock`, `ThinkingBlock`, `ImageBlock`, `ToolCall`;
- `UserMessage`, `AssistantMessage`, `ToolResultMessage`;
- `Usage`, `StopReason`, `DeferredHandle`;
- diagnostics;
- `LlmContext`;
- model identity `provider + api + model_id`;
- provider request/stream option semantic fields;
- terminal/fused stream contract;
- Responses text/thinking signature behavior.

Canonical serialization is snake_case. Provider/Pi wire casing is adapter-owned.

### `spec/target-model-transformation.md`

Normatively copy the pinned Pi `transformMessages()` behavior:

1. null/legacy content normalization;
2. unsupported-image placeholders and dedupe;
3. thinking compatibility matrix;
4. cross-model replay metadata stripping;
5. tool-call ID normalization + tool-result rewrite;
6. orphan tool-result synthesis;
7. error/aborted assistant history exclusion.

No implementation may move these rules into a conformance runner or adapter-specific fake.

### `spec/session.md`

Retain intentional Minion architecture while pinning equivalent model-visible results:

- append-only committed log;
- model-visible means logged;
- surface vs log-only events;
- fork/reset/compaction derivation;
- content-addressed request state;
- request reconstruction;
- plugin event identity/projection rules.

### `spec/agent.md`

Pin Pi run semantics:

- run vs turn;
- prompt/continue caller rules;
- `agent_start -> turn_start -> initial message lifecycle`;
- initial steering poll;
- `continue()` no-double-drain;
- invocation-local `agent_end.messages`;
- `prepareNextTurn -> shouldStopAfterTurn -> steering -> follow-up`;
- active abort;
- observable Agent state;
- high-level callback-failure settlement;
- progress isolation.

### `spec/tools.md`

Pin:

- tool definition + constrained sampling;
- `prepareArguments -> validate -> before -> execute -> after`;
- every thrown/rejected extension-boundary value -> error tool result;
- after-hook failure replaces prior result;
- length-stop executes no tools;
- batch sequential contagion;
- completion-order execution events vs source-order result messages;
- late update suppression;
- all-results `terminate` fold semantics.

### `spec/harness.md`

For phases 6–7 pin:

- execution capability `Result` boundaries;
- built-in tools;
- system prompt and exact skill projection;
- skill discovery/diagnostics;
- compaction estimator + summary request settings;
- harness message projections.

For Phase 9, explicitly mark AgentHarness durable operations as `deferred parity`, not unspecified.

## 2. Canonical conformance realignment

### Preserve first

Keep existing `runtime/` cases that remain green against the frozen plugin-runtime contract. Runtime is the principal intentional architectural divergence, not a Pi-copy exercise.

### Replace/rewrite agent cases that encode superseded semantics

Delete or supersede any scenario that assumes:

```text
Minion "turn" = multiple provider steps
tool terminate = hard run stop
cooperative-only cancellation
initial prompt lifecycle before turn_start
tool/hook exceptions may escape the Pi extension boundary
old narrow LLM vocabulary
```

### Required `agent/` cases

```text
initial-prompt-order-after-turn-start
initial-steering-before-first-request
continue-steering-no-double-drain
agent-end-messages-prompt-vs-continuation

turn-lifecycle-order
followup-only-when-otherwise-idle
prompt-while-running-rejected
continue-ordering

active-abort-provider
active-abort-tool
abort-settles-before-idle
agent-state-streaming-projection
pending-tool-calls-state
idle-after-agent-end-listeners
high-level-callback-failure-settlement

length-stop-executes-no-tools
tool-batch-sequential-contagion
tool-batch-parallel
parallel-tool-completion-vs-message-order
late-tool-update-ignored

prepare-arguments-failure-becomes-tool-error
schema-validation-failure-becomes-tool-error
before-hook-failure-becomes-tool-error
execute-failure-becomes-tool-error
after-hook-failure-replaces-result-with-tool-error

terminate-suppresses-tool-driven-continuation
terminate-still-runs-prepare-and-stop-policy
terminate-does-not-discard-steering
terminate-allows-follow-up-when-otherwise-idle

same-model-thinking-signature-replayed
same-model-unsigned-thinking-not-replayed
cross-model-thinking-converts-to-text
cross-model-redacted-thinking-omitted
cross-model-signatures-stripped
nonvision-user-image-placeholder
nonvision-tool-image-placeholder
null-content-normalizes-empty
tool-call-id-normalization
orphan-tool-result-synthesized
errored-assistant-excluded-from-replay
aborted-assistant-excluded-from-replay
public-llm-vocabulary-schema
```

### Required `session/` cases

Retain valid existing fork/reset/compaction/reconstruction cases, and add:

```text
content-signatures-round-trip
rich-assistant-message-round-trip
deferred-handle-round-trip
diagnostic-round-trip
request-reconstruction-after-target-transform
request-reconstruction-with-artifacts
```

Provider wire-level parser/encoder tests remain Tier 2 adapter tests, not language-neutral conformance.

## 3. Scenario schema changes

The canonical JSON/YAML schemas need to represent:

```text
content:
    text_signature
    thinking_signature
    redacted
    thought_signature
    namespace

assistant:
    api
    provider
    model
    response_model
    response_id
    diagnostics
    usage
    stop_reason
    deferred
    error_message
    raw_stop_reason
    end_turn
    timestamp

tool_result:
    details
    usage
    added_tool_names
    is_error

events:
    agent_start
    turn_start
    message_start
    message_update
    message_end
    tool_execution_start/update/end
    turn_end
    agent_end
```

Add a schema-level rule that canonical identity strings are compared by value.

## 4. Runner rule

Conformance runners may:

- construct typed public inputs;
- invoke real library APIs;
- translate returned typed values to canonical JSON.

They may **not** implement:

- `transformMessages` compatibility;
- tool termination decisions;
- queue ordering;
- stream fusion;
- session derivation;
- failure settlement.

If the runner contains behavior that can make a wrong library pass a scenario, the scenario is invalid.

## 5. Python realignment gate

Before Phase 5 is considered complete, Python must pass the revised Phase 0–4 suite.

Preferred rewrite boundary from the frozen design:

```text
retain:
    runtime/
    session primitives/
    artifact store/
    deterministic testkit/

rewrite:
    llm vocabulary + target-model transform
    Agent state + queues
    run/turn driver
    tool prepare/execute/finalize
    active abort propagation
```

Do not preserve a shipped behavior merely because an old conformance case expected it.

## 6. Rust gate

Retain Rust Phase 1 runtime if revised `runtime/` scenarios remain green.

Before implementing semantic Phase 2+, rewrite the old executable plans against:

1. frozen master;
2. normative spec;
3. `pi-parity-manifest.yaml`;
4. revised canonical conformance.

The Rust conformance adapter must exercise the real typed runtime and semantic services; no parallel JSON semantics.

## 7. Completion checklist

Phase 0 realignment is complete when:

- [ ] `pi-parity-manifest.yaml` is checked in and every row has a disposition.
- [ ] every adopted manifest row has a spec rule.
- [ ] every observable row has a canonical case or explicitly justified language-specific test.
- [ ] old contradictory agent/session scenarios are deleted or rewritten.
- [ ] scenario schemas encode the frozen vocabulary.
- [ ] Python runtime cases remain green.
- [ ] revised agent/session cases demonstrably fail against known superseded Python behavior where applicable.
- [ ] the new Python vertical slice restores all applicable cases to green.
- [ ] Rust Phase 1 stays green.
- [ ] Rust Phase 2+ plans reference manifest IDs rather than superseded design assumptions.
- [ ] no runner duplicates Pi/Minion semantic logic.
- [ ] Pi revision remains exactly `b7bb00b936dbe21b8e160b3e89efdec361846699` for this baseline pass.

## 8. Next after Phase 0

Once these artifacts are checked in and the revised Python/Rust gates are explicit:

```text
Phase 5 amendment
    -> rewrite against frozen vocabulary, transform semantics, and active abort

Python
    -> implement the fresh agent-facing vertical slice

Rust
    -> rewrite Phase 2+ plans, then implement

Pi drift
    -> only after baseline alignment is green, compare the pinned revision to a newer candidate
```
