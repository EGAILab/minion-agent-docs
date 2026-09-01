# Layer 08 final independent Rust contract review — PASS 9

## Review target and mode

This is the final complete review required by `process/agent-workflow.md` §11.8.8 after the targeted convergence review. It is review evidence only; no Rust, Python, shared-contract, or canonical candidate file was modified.

- code PR #13: `a5a0fdc1a95d7e8f7f347de4bf9569d07abb426a`
- docs PR #3: `eb4965d5344c14aeb5da030341602a60ef2f0386`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- targeted PASS-9 review: docs PR #11 at `a5aac42b3e16182fa4f646edae60a5170649fb11`
- prior rejected evidence: docs PRs #4 through #10, as recorded in coordination issue #12

The PR heads were fetched and verified remote-reachable, open, non-draft, and equal to issue #12 before review. The verdict applies only to these exact candidate SHAs.

## Authority and source audit

Reviewed in the required order: pinned Pi, normative spec, manifest, canonical schema/scenarios, certified Rust architecture, assurance, then Python as secondary evidence.

Pinned Pi symbols re-read:

- `packages/agent/src/agent.ts`: `createContextSnapshot`, `createLoopConfig`, `prompt`, `continue`, `runWithLifecycle`, `handleRunFailure`, `processEvents`.
- `packages/agent/src/agent-loop.ts`: `runAgentLoop`, `continueAgentLoop`, `runLoop`, `streamAssistantResponse`, `executePreparedToolCall`.
- `packages/agent/src/types.ts`: `AgentState`, `AgentEvent`, `AgentLoopTurnUpdate`, `AgentToolResult`, `AgentToolUpdateCallback`.

The targeted PASS-9 finding pair remains provisionally closed: the opt-in per-listener yield reproduces Pi's awaited serial listener boundary without changing other `EventBus.serial` callers, and current normative prose describes that convergence mechanism. The final whole-contract audit nevertheless found new blocking defects outside that checkpoint.

## AG-001..AG-010 and AG-021 ledger

| ID | Pi rule / surface | Spec and evidence result | Rust ownership | Verdict |
|---|---|---|---|---|
| AG-001 | `agent_start`, `turn_start`, prompt admission before loop body | Rule and executable evidence agree, but the Python pointer names `_run_step`; initial prompt admission is implemented in `_execute_run` / `_run_inner` / `_admit_messages` | Layer-08 driver | Evidence pointer defective |
| AG-002 | initial steering poll after prompt lifecycle | Spec, scenarios, and source agree | Layer-08 driver/inbox | PASS |
| AG-003 | prompt/continue branching and initial drains | Exact errors and branches agree with Pi | Layer-08 entry points | PASS |
| AG-004 | post-turn hooks and whole run-local update | Current rule is coherent; no active stale “unimplemented” claim | Layer-08 driver | PASS |
| AG-005 | invocation-local `agent_end.messages` | Fresh prompt, continuation, and independent-run evidence are discriminating | Layer-08 run state | PASS |
| AG-006 | terminate only suppresses tool-driven continuation | Hook/queue order remains eligible as Pi requires | Layer-08 driver | PASS |
| AG-007 | active abort propagation | Correctly deferred to Layer 09; no Layer-08 boundary-stop surrogate remains | Layer 09 | PASS / deferred parity |
| AG-008 | runtime-field transition timing | `streaming_message` rule is internally contradictory and contradicts Pi for admitted non-provider messages | Layer-08 reducer/state | BLOCKING |
| AG-009 | listener-bearing live lifecycle | Targeted convergence timing is correct; however its tool-update payload inherits the structured-partial contract defect | Runtime seam + Layer-08 projection | BLOCKING via L08-R011 |
| AG-010 | run-local snapshots, configuration, messages/tools | Snapshot, run-local updates, dynamic tool extension, and no persistent leakage are coherent | Layer-08 driver | PASS |
| AG-021 | represented error/aborted terminal behavior | Immediate terminal handling and non-consumption of hooks/queues agree with Pi | Layer-08 driver | PASS |

No cited AG-row canonical scenario is a `TO_BE_FILLED_FROM_PINNED_PI_BEHAVIOR` placeholder. The remaining explicit placeholders are not counted as satisfying these adopted rows.

## Whole-state-machine audit

- Fresh typed prompt, message sequence, text convenience, and text-plus-images normalize and admit in Pi order.
- Plain continuation and assistant-last steering/follow-up pre-drain branches match Pi, including single suppression of the initial steering poll.
- The first-turn ordering is `agent_start -> turn_start -> prompt lifecycle -> steering claim/lifecycle -> provider` with one provider-visible first-turn context.
- Tool-, steering-, and follow-up-driven continuation preserve Pi's post-turn order.
- `prepareNextTurn` replaces whole run-local context/model/thinking state without persistent Agent leakage.
- `added_tool_names` extends only the run-local tool context for a subsequent turn.
- `terminate` does not suppress prepare/stop/steering/follow-up eligibility.
- Represented `error` and `aborted` replies are immediately terminal and do not consume later hooks/queues.
- Unexpected run failure emits no invented `turn_start`; reducer/listener failure boundaries and outer status settlement otherwise match Pi.
- No `max_steps`, cancel, or boundary-stop mechanism truncates a Pi-equivalent run.
- `agent_end.messages` remains invocation-local over multiple turns and independent runs.
- Context snapshots, status, pending calls, and persistent `error_message` timing are otherwise coherent.

## Canonical and runner audit

The executable agent scenarios use the real `AgentLoop`, inbox, session, tool executor, and registry. The runner parses, dispatches, and normalizes; it does not implement the state machine, FIFO, snapshotting, continuation choice, or event ordering. The 20-tool-turn no-cap case is discriminating against the removed limit, and dynamic-tool evidence distinguishes a frozen start snapshot from approved run-local extension.

One language-neutral schema boundary is not faithful: `expect_updates[].partial` requires a JSON string. A structured Pi `AgentToolResult` object therefore fails schema validation before either runner can exercise it.

## Contract-quality findings

### L08-R011 — structured tool-update partial is narrowed to string

**Classification:** `PI_PARITY_DEFECT` and `CONTRACT_ASSURANCE_DEFECT`.

Pinned Pi defines `AgentToolUpdateCallback<T> = (partialResult: AgentToolResult<T>) => void`; `tool_execution_update.partialResult` therefore carries a structured tool result, not merely text. The reviewed shared/Python surface narrows it:

- Python `ToolUpdate = Callable[[str], None]`;
- Python `ToolExecutionUpdate.partial_result: str`;
- Layer-06/08 callbacks type the partial as `str`;
- canonical `expect_updates[].partial` has `type: string`.

A direct schema witness replacing `"live"` with a structured result object is rejected as “not of type string”. Certified Rust Layer 06 already uses `AgentToolResult` for `ToolUpdateCallback` and `ToolExecutionUpdate.update`, so copying the candidate into Rust would either regress certified Rust or create cross-language divergence.

Required narrow remediation:

1. Perform the post-certification delta audit for the shared/Python Layer-05/06 update callback and event payload.
2. Adopt the structured `AgentToolResult` partial through Python Layer 06 and Layer-08 projection.
3. Make schema/canonical evidence accept and discriminate structured content/details while retaining id/name/original-arguments and late-update rules.
4. Preserve the already-faithful Rust Layer-06 typed shape.

### L08-R012 — `streaming_message` normative timing is contradictory

**Classification:** `CONTRACT_ASSURANCE_DEFECT`.

The Layer-08 spec and AG-008 first state that `streaming_message` is non-null “for exactly the duration of one provider request”, then state that Pi sets it for every admitted prompt, steering, follow-up, and tool-result message from `message_start` through `message_end`. Pinned Pi's `processEvents` confirms the latter. A candidate runtime witness records `streaming_message` as populated at both initial `UserMessage` and streamed `AssistantMessage` `message_start` events.

Two independent Rust implementations could therefore conform to different sentences. Required remediation: replace the provider-request-only statement in both spec and AG-008 with the complete Pi rule, retaining full stream-partial fidelity for assistant updates. Also remove or qualify stale prose saying no new listener-dispatch primitive was needed now that PASS 9 intentionally added an opt-in scheduling control.

### L08-R013 — AG-001 implementation evidence pointer is inaccurate

**Classification:** `CONTRACT_ASSURANCE_DEFECT`.

AG-001 cites `AgentLoop._run_step`, but that method owns subsequent provider/tool turns; initial prompt lifecycle ordering is implemented by `_execute_run` / `_run_inner` / `_admit_messages`. The semantic rule and tests are correct, but the manifest's implementation evidence is not. Correct the evidence pointer without changing semantics.

## Lower-layer delta

- Layers 01, 02, 03, 04, 05: no Rust semantic delta identified.
- Layer 06: no Rust delta; current Rust is already faithful. Shared/Python Layer-06 assurance must be narrowly reopened for L08-R011 because the public update callback/schema were certified too narrowly.
- Layer 07: no delta.
- Layer 09: not started; AG-007 remains correctly deferred.

## Verification observations

- Python: `1042 passed, 19 xfailed`; configured coverage `100.00%`.
- Ruff: PASS.
- mypy: PASS, 57 source files.
- Existing Rust workspace through Layer 07: full `cargo test --workspace --all-features` PASS, including typed `AgentToolResult` update evidence.
- Candidate PR heads and issue coordination were re-fetched immediately before evidence publication.

Green implementation gates do not override the source/contract defects above.

## Verdict

```text
shared Layer-08 contract
    REJECTED

Python Layer 08
    REOPENED

Rust Layer 08
    BLOCKED / NOT_IMPLEMENTED

Layer 08 cross-language
    NOT CLOSED

Layer 09
    NOT STARTED
```

Active blockers:

- `PI_PARITY_DEFECT`: L08-R011.
- `CONTRACT_ASSURANCE_DEFECT`: L08-R011, L08-R012, L08-R013.
- `PI_BEHAVIOR_UNCERTAIN`: none.
- unapproved observable divergence: none beyond the defects explicitly reported above.

STOP. Return the narrow remediation to the shared/Python owner. Any candidate SHA change requires another exact-SHA final complete review. Do not implement Rust Layer 08 or start Layer 09.
