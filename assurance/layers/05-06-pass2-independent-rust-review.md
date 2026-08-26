# PASS 2 — Independent Rust Review of Corrected Layer-06 Contract

Date: 2026-08-26

## Starting state and scope

```text
minion-agent       036c124f26a1e354e9405b46478cde96310048c5
minion-agent-docs  6b382997a3b4ffbaa892bbe929c50c8f6dccc3fc
pinned Pi          b7bb00b936dbe21b8e160b3e89efdec361846699
Rust baseline      5683fd9de82c0bf7fdb4462e241c687cd26afcb6
```

This was a review-only pass. Rust production, Rust tests, the Rust canonical adapter, Python,
shared specifications, and canonical fixtures were not modified. The unrelated Phase-5 working
tree change was not inspected or touched.

## Pinned Pi re-audit

Pinned `packages/agent/src/agent-loop.ts::executeToolCallsParallel` establishes a sequential
preflight barrier. Its source-order loop emits one start event, awaits `prepareToolCall` completely,
then advances to the next call. Prepared calls are stored as deferred closures. Only after that
loop does `Promise.all` invoke the closures concurrently. Immediate results emit their end event
inside the preflight loop. Consequently start(B) waits for preflight(A), and execute(A) cannot
begin until the whole batch's preflight has settled.

The same source confirms:

- `AfterToolCallResult` has five single-level optional fields. `finalizeExecutedToolCall` merges
  them with `??`; nullish input preserves the current value and does not create a clear state.
- an unknown tool produces exactly `Tool <name> not found`;
- `createErrorToolResult` always supplies `details: {}`;
- `tool_execution_update` carries call id, tool name, original `toolCall.arguments`, and the
  partial result. Execute receives the separately prepared/validated arguments.

## Shared contract and canonical review

The two-phase parallel rule in `spec/tools.md` and `TOOL-023` matches Pi. `TOOL-001`, `TOOL-006`,
and `TOOL-023` remain coherent: sequential batches execute complete pipelines one at a time,
whereas parallel batches preflight sequentially and execute prepared calls concurrently;
completion-order end events and source-order messages remain distinct.

`parallel-preflight-settles-sequentially-before-execute` is language-neutral and discriminating.
Its runner listeners only observe start/before/execute/end at real production seams. They neither
create the barrier nor delay/reorder execution. The pre-correction Rust structure cannot satisfy
the trace: Rust emits both starts before any preflight and schedules the complete `execute_one`
pipeline concurrently.

The revised `late-tool-update-ignored` fixture distinguishes raw `{raw: 1}` from prepared
`{raw: 1, prepared: true}` arguments and requires the complete adopted Pi payload. The exact
unknown-tool text and error `details: {}` are also represented without host exception syntax.

### Blocking shared-evidence defect: successful-result details

The corrected unknown-tool scenario also expects `details: {}` on the two successful results, but
its tool declarations specify only `result.text`. `agent-scenario.schema.json::$defs.toolStub.result`
does not define a `details` member or an omitted-details default. Pinned Pi does not supply such a
success default: `AgentToolResult<T>.details` is required, and a successful result preserves the
value returned by the tool. Python reaches `{}` only through its host `ToolResult.details`
dataclass default; current Rust's scripted tool reaches null/absence instead.

Therefore the success expectations are not presently derived from language-neutral fixture input
or from Pi. A runner must invent a host default to satisfy them. This is a
`CONTRACT_ASSURANCE_DEFECT` (`CA-L06-007`) and blocks approval for Rust remediation.

Minimal correction:

1. narrow the Pi-derived rule to error helpers (`createErrorToolResult`) and to preservation of a
   success tool's actually supplied details; and
2. either remove `{}` assertions from the two successful results, or extend the canonical tool
   result schema and explicitly declare `details: {}` on those scripted successes.

The unknown-tool error's exact `details: {}` assertion should remain.

## Current Rust findings

### IR-L06-001 — OPEN — PI_PARITY_DEFECT

`execute_tool_calls` emits all source start events up front. In parallel mode it pushes
`execute_one` directly into `FuturesUnordered`; `execute_one` contains prepare, validation,
before-hook, execute, and after-hook. Thus one call can execute before another call has completed
preflight. A source-order `PreflightOutcome::{Immediate, Prepared}` phase followed by concurrent
prepared execution is feasible without Layer-05 or Runtime redesign.

### IR-L06-002 — OPEN — PI_PARITY_DEFECT

Rust's helper override exposes `Option<Option<Value>>` for details and
`Option<Option<Usage>>` for usage through builders accepting `None`, creating an observable clear
state Pi's nullish merge does not have. Content and `is_error` have the correct omit/replace
states. The helper does not publicly expose a terminate-clear builder, but the raw whole-result
waterfall can clear details, usage, or terminate; its allowed-field merge therefore also needs to
honor nullish preservation. A typed single-level override and allowed-field merge can repair this
without changing protected-field normalization.

### IR-L06-003 — RESOLVED / ALREADY CONFORMANT

Rust emits exactly `Tool nonexistent not found`, matching Pi.

### IR-L06-004 — OPEN — PI_PARITY_DEFECT

`immediate_error` uses `details: None`. This affects unknown-tool, prepare, validation, and
before-hook failures, length-stop results, execute failures as observed by after hooks, helper/raw
after-hook failure replacement, and their final messages. Pi uses `{}` for every generated error
result. Rust must preserve an empty object as present, not collapse it to absence.

### IR-L06-005 — OPEN — PI_PARITY_DEFECT

`ToolExecutionUpdate` contains call id, tool name, and the partial `AgentToolResult`, but no
original arguments. Production must add the original arguments while execute continues receiving
prepared arguments. No Runtime redesign is required.

### IR-L05/06-006 — RESOLVED

Python `definition.py`, `TOOL-009`, and `spec/tools.md` correctly describe current tool-call-id and
update wiring, Rust's structural `ToolExecutionSignal`/`ToolExecutionRequest.signal`, Python's
lack of a cancellation abstraction, and Layer-09 ownership of behavioral cancellation.

## Rust adapter feasibility and thinness

PASS 3 would require:

| Corrected evidence | Production change | Adapter change |
|---|---:|---:|
| sequential preflight trace | yes | observe/serialize trace |
| full update payload | yes | serialize name/original args/partial |
| error details `{}` | yes | assert structured details |
| exact unknown text | no | assert exact text (already production-correct) |

The adapter must not implement the barrier, normalize error text, inject details, or reconstruct
missing update arguments. All must originate in production. Existing Rust canonical execution is
not current evidence: it selects ten old scenario names, omits the new preflight fixture, ignores
message details, and fails the corrected update expectation.

## Layer-05 and prior Layer-06 feasibility

No redesign is required for `ToolDefinition`, `ToolRegistry`, `JsonSchemaObject`, `ScopeTree`,
Runtime lifecycle, or the signal seam. The existing normalized waterfall still protects
`tool_call_id`, `tool_name`, and `added_tool_names` at every listener boundary. The 16 existing
Rust execution tests pass, including protected final/intermediate fields, raw/helper authority,
N-listener order, stage reachability, length-stop isolation, and sequential-mode behavior.

## Fresh observations

```text
Python corrected Layer-06 canonical subset  11 passed
Rust Layer-06 language tests                16 passed
Rust corrected canonical adapter           FAILED
  observed old update pair ["t1", "live"]
  expected full update object
  new preflight fixture not selected by the 10-name adapter inventory
schema validation                          166 passed
manifest structural/unique-ID validation   66 / 66
```

## Verdict

```text
shared corrected Layer-06 contract  REJECTED
Python Layer 06                     CERTIFIED
Rust Layer 06                       IN_REMEDIATION
Layer 06 cross-language             NOT CLOSED
Layer 07                            NOT STARTED
```

The Pi correction itself is sound and Rust remediation is architecturally feasible, but PASS 3
must wait for the narrow successful-details fixture/contract correction above. No further broad
Layer-06 redesign or re-audit is requested.
