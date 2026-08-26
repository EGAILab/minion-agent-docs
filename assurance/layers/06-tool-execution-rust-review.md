# Layer 06 Rust independent contract review — Tool execution pipeline

**Review date:** 2026-08-26  
**Code candidate:** `minion-agent@ee563ffad65f1c8624536cbf8cc65dc395efe39a`  
**Docs candidate:** `minion-agent-docs@e96c154ac760ff4e1f06bcec4c14be588e470a18`  
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`  
**Rust implementation modified:** NO

## Verdict

```text
Layer-06 shared contract
    REJECTED

Python Layer 06
    IN_REMEDIATION

Rust Layer 06
    NOT_IMPLEMENTED

Rust current certified position
    Layer 05

Layer 07
    NOT STARTED
```

The stage order, batch scheduler, length-stop rule, late-update cutoff, source/completion order
split, terminate fold, namespace rule, and later-layer boundaries are independently implementable.
Six active defects prevent Rust implementation from beginning.

## Pi audit and traceability matrix

Pinned Pi was read directly at the revision above:

- `packages/agent/src/agent-loop.ts`: `failToolCallsFromTruncatedMessage`, `executeToolCalls`,
  `executeToolCallsSequential`, `executeToolCallsParallel`, `prepareToolCallArguments`,
  `prepareToolCall`, `executePreparedToolCall`, `finalizeExecutedToolCall`,
  `createErrorToolResult`, `createToolResultMessage`;
- `packages/agent/src/types.ts`: `ToolExecutionMode`, `BeforeToolCallResult`,
  `AfterToolCallResult`, `AgentToolResult`, `AgentToolUpdateCallback`, `AgentTool`, and the three
  tool-execution `AgentEvent` variants;
- `packages/ai/src/utils/validation.ts::validateToolArguments`;
- `packages/ai/src/types.ts`: `ToolCall` and `ToolResultMessage` vocabulary.

| Concern | Pi source | Requirement | Evidence | Rust feasible | Verdict |
|---|---|---|---|---:|---|
| Resolution/stage order | `prepareToolCall` | TOOL-003/004/017/018 | prepare/before/execute scenarios | YES | PASS |
| Validation | `validateToolArguments` | TOOL-003 | schema-validation scenario | YES | **R001** |
| Before hook | `prepareToolCall` | TOOL-004 | before-hook failure + language tests | YES | **R006** |
| Execute/failure | `executePreparedToolCall` | TOOL-004 | execute-failure scenario | YES | **R002** |
| After hook | `finalizeExecutedToolCall` | TOOL-005 | after-hook scenario/tests | YES | **R003/R006** |
| Updates | `executePreparedToolCall` | TOOL-019 | late-update scenario/tests | YES | PASS |
| Mode/contagion | `executeToolCalls` | TOOL-001/020 | parallel + contagion scenarios | YES | PASS |
| Result/end ordering | `executeToolCallsParallel` | TOOL-006/017 | completion-vs-message scenario | YES | PASS |
| Length stop | `failToolCallsFromTruncatedMessage` | TOOL-002 | length-stop scenario | YES | PASS |
| Result metadata | `createToolResultMessage` | TOOL-005/021 | language tests | YES | **R003** |
| Namespace | lookup by `name` | TOOL-021 | language tests | YES | PASS |
| Signal | hook/execute signal parameters | TOOL-018 + AI-003 defer | no Layer-06 scenario | YES | **R005 evidence repair** |

## Confirmed contract behavior

### Per-call stages

```text
resolve -> prepare_arguments -> validate -> before hook -> execute/updates -> after hook
```

Unknown-tool, prepare, validation, before-hook exception, and structured before-hook block are
immediate outcomes: they skip execute and the after hook. Execute failure is an executed outcome
and therefore reaches the after hook. An after-hook exception replaces the prior executed outcome.

`prepare_arguments` is before validation and uses execution-local arguments. The source ToolCall
does not need to be mutated.

### Batch scheduling

The run default is parallel. A sequential run default or any resolvable tool with an explicit
sequential override serializes the entire batch in source order. Unknown tools do not spread
sequential contagion. Failure is isolated in both modes.

Parallel start events are emitted in source/preflight order, end events in actual finalized
completion order, and final ToolResultMessages in source order. Rust can reproduce this with
indexed result slots plus a completion-driven future set; no Python scheduler behavior is
normative.

### Updates and length stop

The update cutoff is settlement of the tool's own execute future, before the after hook. Calls to
the retained update callback after that settlement are inert. The product executor, not the
runner, owns the cutoff.

Length-stop calls do not resolve or invoke any tool-stage callback. Each call still receives one
start and one end event and the exact Pi-authored truncation error result; batch terminate is
false.

## Active findings

### L06-R001 — PI_PARITY_DEFECT — raw object-valued schemas bypass validation

**Pi evidence:** `validateToolArguments` validates every `Tool.parameters: TSchema`, including raw
JSON-schema objects. It clones/coerces and checks the schema; it does not exempt a raw schema
representation.

**Current shared/Python rule:** `spec/tools.md`, TOOL-003, `_validate`, the canonical schema, and
the runner explicitly say a raw JSON-schema dictionary receives no validation. The canonical
fixture uses the Python-specific shorthand `parameters: {requires: [...]}` to construct a
Pydantic model instead of passing the approved Layer-05 schema representation to the production
validator.

**Why blocking:** Rust cannot implement one shared validation contract: matching Pi would diverge
from certified Python; matching Python would knowingly preserve a Pi parity defect. The canonical
schema also embeds a Python implementation choice rather than the language-neutral Layer-05
parameter value.

**Minimal repair:** define validation for the full approved object-valued parameter-schema domain;
make Python validate raw object schemas; express canonical parameters as real JSON schema; keep
validator-library prose normalized rather than exact. Reopen Python certification.

### L06-R002 — PI_PARITY_DEFECT — canonical error content includes Python exception class names

**Pi evidence:** every caught failure uses `error.message` (or `String(error)` for non-Error) as
the error-result text. A JavaScript `Error("disk on fire")` produces `disk on fire`, not
`Error: disk on fire`.

**Current evidence:** canonical prepare/before/execute/after failure scenarios assert strings such
as `RuntimeError: disk on fire` and `RuntimeError: annotation service unavailable` because Python
formats `type(error).__name__` into the model-visible result.

**Why blocking:** Rust has no truthful `RuntimeError` class name to emit. The fixtures require a
Python-specific observable and contradict pinned Pi.

**Minimal repair:** normalize caught callback failures to the exception message only, update the
affected canonical expectations, and state which Minion-authored error strings are exact. Also pin
the unknown-tool result text or explicitly approve a divergence. Reopen Python certification.

### L06-R003 — CONTRACT_ASSURANCE_DEFECT — after-hook field contract and production seam conflict

**Pi evidence:** `AfterToolCallResult` is a partial override limited to `content`, `details`,
`isError`, `usage`, and `terminate`; `addedToolNames` and call identity are not overridable.

**Current contract:** spec/tools.md and TOOL-005 state the Pi field-limited merge and explicitly
say `added_tool_names` is not overridable.

**Current implementation seam:** `tools/post-execute` is a waterfall over the entire frozen
`ToolResult`; a listener can return an arbitrary replacement ToolResult. That allows observable
replacement of `added_tool_names`, `tool_call_id`, and `tool_name`, contrary to the normative rule.
The cited `test_a_listener_may_own_the_result_outright` reinforces whole-result ownership rather
than constraining a Pi-shaped override.

**Why blocking:** a Rust hook cannot know whether to implement the documented partial override or
the Python whole-result replacement capability.

**Minimal repair:** make post-hook output a Pi-shaped partial override and merge it in the executor,
or explicitly adopt and specify a Minion extension while protecting immutable call identity and
resolving `added_tool_names` semantics. Add direct evidence. Reopen Python certification.

### L06-R004 — CONTRACT_ASSURANCE_DEFECT — canonical inventory is arithmetically inconsistent

The candidate changes exactly ten Layer-06 placeholder fixtures and the assurance inventory lists
ten names, but the assurance prose, freeze gate, handoff, and reported result say nine/9. Repository
truth for this delta is ten:

1. `after-hook-failure-replaces-result-with-tool-error`
2. `before-hook-failure-becomes-tool-error`
3. `execute-failure-becomes-tool-error`
4. `late-tool-update-ignored`
5. `length-stop-executes-no-tools`
6. `parallel-tool-completion-vs-message-order`
7. `prepare-arguments-failure-becomes-tool-error`
8. `schema-validation-failure-becomes-tool-error`
9. `tool-batch-parallel`
10. `tool-batch-sequential-contagion`

`pending-tool-calls-state` remains a Layer-07+ placeholder and is not one of these ten.

**Minimal repair:** make every current Layer-06 inventory and gate statement say ten/10 and retain
truthful historical counts only where explicitly historical. This is evidence bookkeeping; it
does not require a semantic implementation change.

### L06-R005 — CONTRACT_ASSURANCE_DEFECT — signal-defer evidence is factually stale

The defer itself is acceptable, but its stated basis is false for Rust. Certified Layer 05 already
contains `ToolExecutionSignal`, `ToolExecutionRequest.signal`, and a signal-capable execute request
in `minion-agent-rust/crates/minion-agent/src/tools/definition.rs`.

```text
SIGNAL DEFER
    ACCEPTED
```

Layer 09 can add cancellation behavior without changing the non-cancelled stage, ordering, result,
or event rules. Rust Layer 06 can retain the existing capability seam without exercising
cancellation yet.

**Minimal repair:** replace the false “no equivalent type exists in either language” statements
in spec/assurance/manifest/handoff with the actual asymmetry: Python lacks a signal abstraction;
Rust already reserves one; cancellation behavior remains deferred to Layer 09. No Layer-05 or
Runtime reopening is required.

### L06-R006 — CONTRACT_ASSURANCE_DEFECT — Minion hook augmentation classification is inconsistent

Pinned Pi has one before callback and one after callback. Minion has ordered N-listener waterfalls,
argument replacement in pre-hooks, and whole-result transformation in post-hooks. These are
observable ordinary plugin-composition semantics, not merely an internal hardening.

The spec calls them deliberate Minion additions/generalizations, the assurance calls them
`PARITY_NEUTRAL_HARDENING`, while TOOL-004/005 retain `adopted` disposition without a separate
requirement that defines listener chaining/replacement.

**Minimal repair:** classify the multi-listener behavior consistently as an intentional Minion
architectural extension, add traceability for registration order, delegation/replacement, and
mid-chain failure, and preserve exact single-listener Pi behavior. Resolve this together with
L06-R003's post-hook type boundary.

## Canonical and runner review

Focused evidence was reproduced:

```text
uv run pytest --no-cov tests/conformance/test_agent_conformance.py tests/tools -q
    PASS (all selected tests; existing later-layer placeholders xfailed)

manifest parse / unique IDs
    65 / 65
```

The runner calls the production ToolRegistry/executor/agent-loop seams and does not implement
mode selection, failure conversion, stage ordering, update suppression, or result ordering.
Scripted delay ticks use cooperative scheduler yields and make the demonstrated two-call order
deterministic. Scripted callbacks are acceptable external behavior.

The validation fixture is not acceptable as the shared semantic input boundary for the reasons in
L06-R001, and Python exception-class strings are not language-neutral for the reasons in L06-R002.

`projected-execution-ends-follow-completion-order` is a separate Agent log/projection scenario;
it is not part of the ten placeholder fixtures activated by this Layer-06 delta.

## Rust feasibility

Layer-05 `ToolDefinition`, `ToolRegistry`, Runtime scopes, and owned callback objects are reusable.
Rust can implement scheduling, live updates, and source/completion ordering without a Runtime or
Layer-05 redesign. A JSON-schema validation dependency may be needed; that is an implementation
choice, not a contract defect. The existing signal-bearing request is future-compatible with
Layer 09.

```text
Layer-05 redesign required    NO
Runtime redesign required     NO
second registry required      NO
Rust production modified      NO
```

## Required questions

| Q | Answer |
|---:|---|
| 1 | YES, except the validation-domain defect R001. |
| 2 | YES. |
| 3 | YES. |
| 4 | YES. |
| 5 | YES. |
| 6 | YES. |
| 7 | YES. |
| 8 | YES structurally; current error text is non-Pi (R002). |
| 9 | NO; the documented merge conflicts with the whole-result waterfall (R003). |
| 10 | YES. |
| 11 | YES, parallel. |
| 12 | YES. |
| 13 | YES. |
| 14 | YES. |
| 15 | YES; later calls still execute. |
| 16 | YES. |
| 17 | YES. |
| 18 | YES. |
| 19 | YES, with deterministic cooperative coordination. |
| 20 | YES. |
| 21 | YES: settlement of execute's own future, before after-hook finalization. |
| 22 | YES. |
| 23 | YES. |
| 24 | YES. |
| 25 | YES; Pi's length-stop literal is exact. |
| 26 | YES. |
| 27 | YES, subject to R003 replacement repair. |
| 28 | YES, subject to R003. |
| 29 | NO; contract and whole-result hook disagree (R003). |
| 30 | YES. |
| 31 | YES. |
| 32 | YES, as batch terminate metadata. |
| 33 | YES. |
| 34 | YES, Layer 07+. |
| 35 | YES. |
| 36 | YES. |
| 37 | YES, except the Python-specific validation fixture boundary (R001). |
| 38 | YES. |
| 39 | YES. |
| 40 | YES. |
| 41 | YES. |
| 42 | YES. |
| 43 | NO. |
| 44 | NO; classification/traceability is inconsistent (R006). |
| 45 | Intended YES, but the post-hook output boundary must be repaired (R003). |
| 46 | YES — SIGNAL DEFER ACCEPTED, with stale evidence repair R005. |
| 47 | YES. |
| 48 | NO; R001/R003/R005/R006 and the inventory defect remain. |
| 49 | YES: R001 and R002 are active. |
| 50 | YES: R003–R006 are active. |
| 51 | NO. |
| 52 | NO blocking risk beyond the classified defects. |
| 53 | NO, not unambiguously until R001–R006 are repaired. |
| 54 | YES after those repairs; the proposed execution seam is otherwise sufficient. |
| 55 | NO. |

## Next action

Return L06-R001 through L06-R006 to the shared/Python owner. Do not implement Rust Layer 06 and
do not start Layer 07 until the repaired candidate receives a fresh independent verdict.
