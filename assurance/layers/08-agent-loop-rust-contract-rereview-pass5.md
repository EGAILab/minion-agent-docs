# Layer 08 — Independent Rust Contract Re-review (PASS 5)

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

The PASS-5 candidate closes the turn-count cap and boundary-stop findings, but it does not close
`L08-R002`. The candidate still differs observably from pinned Pi's single, live,
reduce-before-listener `AgentEvent` seam, and the normative contract explicitly accepts part of that
difference while labeling the row `adopted`. No intentional divergence has been approved.

## Exact review target

| Item | Exact remote state reviewed |
|---|---|
| Code PR | `EGAILab/minion-agent#13` @ `c5c95663d3734a9bfbd742b73f274ec0ac979832` |
| Docs PR | `EGAILab/minion-agent-docs#3` @ `0301f4159ef98c2c58f4bfeb08572c0c91e55238` |
| Pinned Pi | `b7bb00b936dbe21b8e160b3e89efdec361846699` |
| PASS-2 rejection | docs PR #4 @ `88a6aa6c1c1994026001c60045d4c55c00331a52` |
| PASS-3 rejection | docs PR #5 @ `a64b78ad2507b142ca7cda911b8968aa61af6a20` |
| PASS-4 rejection | docs PR #6 @ `65e665f28e29ebe6cf8deb792b206c108d32b1a6` |

At review start issue `EGAILab/minion-agent#12` recorded the same candidate SHAs,
`STATUS = RUST_CONTRACT_REVIEW`, and `NEXT_OWNER = Codex`. Both candidate PRs were open, Ready for
Review, and unmerged. Detached candidate worktrees and this separate review branch were clean; the
unrelated Phase-5 docs modification in the main checkout was not touched.

## Authority and source audit

Reviewed independently in the required order:

1. pinned Pi `packages/agent/src/agent.ts`, especially `runWithLifecycle`, `handleRunFailure`, and
   `processEvents`;
2. pinned Pi `packages/agent/src/agent-loop.ts`, especially `runAgentLoop`, `runLoop`,
   `streamAssistantResponse`, `executeToolCallsSequential`, `executeToolCallsParallel`,
   `executePreparedToolCall`, and tool-result emission;
3. pinned Pi `packages/agent/src/types.ts`, especially `AgentEvent`, `AgentState`,
   `AgentLoopTurnUpdate`, and `AgentLoopConfig`;
4. candidate `spec/agent.md`, manifest rows `AG-001`..`AG-010` and `AG-021`, canonical schema and
   scenarios;
5. certified Rust Runtime/LLM/Session/Tool architecture through Layer 07;
6. PASS-5 assurance and Python implementation only as secondary evidence.

Pi's relevant rule is unambiguous: every `AgentEvent` is sent to `Agent.processEvents`; that method
first reduces Agent state for the event and then awaits listeners serially. Tool start and end
events are awaited at their actual execution positions. Tool updates also traverse this event sink;
their promises are joined before the tool execution settles. Any ordinary run-executor listener
failure, including `agent_start` or successful `agent_end`, reaches `runWithLifecycle`'s catch and
therefore invokes `handleRunFailure`; only a failure in recovery itself escapes that recovery chain.

## Previous finding closure ledger

| Finding | PASS-5 result | Current status |
|---|---|---|
| `L08-R001` complete run snapshot / `prepareNextTurn` | Shallow messages/tools snapshot, complete run-local context replacement, model/thinking replacement, isolation between runs, and targeted `added_tool_names` extension remain coherent. | **CLOSED** |
| `L08-R002` listener-bearing lifecycle / recovery | Assistant stream events are now dispatched live and several reducer timings were repaired. Tool events, fallback stream handling, event payloads, and the outer failure catch remain non-Pi. | **STILL OPEN — BLOCKING** |
| `L08-R003` streaming partial fidelity | Normal streams continue to use full `chunk.partial`; text/thinking/tool-call partial state and start/update/end order remain covered. | **CLOSED**, subject to `L08-R002`'s fallback/catch defects |
| `L08-R004` normative coherence | Most stale Layer-07 claims were repaired. Current spec still cites removed `AG-020`..`AG-022` and normatively accepts a narrower-than-Pi tool-listener seam under an `adopted` row. | **STILL OPEN — BLOCKING** |
| `L08-R005` `max_steps` | Production cap, schema setting, and manifest row are removed. The replacement scenario now drives 20 tool turns plus a final stopping turn, exceeding the former default of 16. | **CLOSED** |
| `L08-R006` initial prompt before steering | Prompt lifecycle completes before the real steering claim; both feed the same first request; continuation pre-drain still suppresses one initial claim. | **CLOSED** |
| `L08-R007` prompt convenience API | Typed message/sequence input and text-plus-images normalization remain coherent. | **CLOSED** |
| `L08-R008` represented error/aborted | Both remain immediately terminal before prepare/stop/steering/follow-up. | **CLOSED** |
| `L08-R009` boundary-stop ownership | Public `request_boundary_stop()` and its latch were removed. | **CLOSED** |
| `L08-R010` boundary-stop/follow-up contradiction | Superseded by removal of the mechanism and `AG-022`. | **CLOSED** |

## Blocking evidence — L08-R002

### 1. Tool lifecycle is replayed after execution, not delivered live

Pinned Pi awaits `tool_execution_start` before preflight/execution and awaits
`tool_execution_end` at finalization. In sequential mode its observable order is naturally
`start A, end A, start B, end B`; a throwing start listener prevents that tool's execution and is
handled as a run failure.

PASS 5 instead subscribes synchronous callbacks to Layer-06 `TOOLS_EXECUTION_START`/`END`, executes
the entire batch, disposes the callbacks, then dispatches all captured starts followed by all
captured ends (`driver.py:891-937`). Consequences include:

- Agent listeners cannot delay or prevent the corresponding tool execution;
- listener failure occurs after the tool batch's side effects already happened;
- sequential batches are reordered from `start A, end A, start B, end B` to
  `start A, start B, end A, end B`;
- recovery begins at a different causal point than Pi.

The candidate spec explicitly discloses this narrower fidelity (`spec/agent.md:423-430`) and AG-009
does the same (`pi-parity-manifest.yaml:724-731`) while retaining `disposition: adopted`. A disclosed
known mismatch is still a `PI_PARITY_DEFECT` absent approved intentional divergence.

### 2. `tool_execution_update` is missing from the Agent event seam

Pinned Pi's `AgentEvent` union includes `tool_execution_update {toolCallId, toolName, args,
partialResult}` and `executePreparedToolCall` sends it through the same event sink. PASS 5 captures
only `TOOLS_EXECUTION_START` and `TOOLS_EXECUTION_END`; its public `AgentEvent` union has no
`ToolExecutionUpdate` variant. The spec's purported complete union likewise lists only tool start
and end. A Layer-06 `TOOLS_UPDATE` event exists, but it is not bridged to Agent listeners.

### 3. Tool-end and assistant-update payloads are incomplete

Pinned Pi's tool-end event exposes `toolName`, the finalized `result`, and `isError`. Candidate
`ToolExecutionEnd` exposes only `tool_call_id` and `is_error`. Pinned Pi's `message_update` exposes
the complete `assistantMessageEvent` as well as the partial message; candidate `MessageUpdate`
exposes only normalized `kind`, `content_index`, and `message`. The shared contract does not approve
these observable payload reductions.

### 4. No-start stream fallback still violates reduce-before-listener

For a stream with no start chunk, pinned Pi emits fallback `message_start` first; `processEvents`
sets `streamingMessage` to the final message, and only the following `message_end` clears it and
pushes it to the transcript.

Candidate `_run_step` instead clears `streaming_message` and appends the finalized assistant log
entry before dispatching fallback `MessageStart` (`driver.py:831-839`). That listener therefore sees
the message already in `AgentInstance.messages` and `streaming_message is None`, the exact timing
error PASS 5 fixed for ordinary admission but missed on this branch.

### 5. `agent_start` and successful `agent_end` listener failures miss recovery

Pinned Pi's `runWithLifecycle` catch surrounds the whole loop executor, including both events.
Candidate `_execute_run` dispatches `AgentStart` before its `try` (`driver.py:401-412`) and dispatches
successful `AgentEnd` after that `try`/`except` has ended (`driver.py:430-441`). A listener failure at
either point escapes directly to `_run_wrapped`'s `finally` instead of invoking
`_settle_run_failure`. The docstring claims successful `agent_end` is inside the catch boundary, but
the control flow proves otherwise.

## L08-R004 — normative coherence

`spec/agent.md` is improved, but not coherent enough for independent implementation:

- line 9 still identifies removed `AG-020`..`AG-022` as current Layer-08 requirements;
- lines 391-412 call the Agent event union and seam complete while omitting
  `tool_execution_update`;
- lines 423-430 explicitly standardize a known causal difference from Pi while the manifest calls
  the rule `adopted`;
- AG-009 similarly says every ordinary event uses the same seam, omits tool updates from that list,
  then documents post-batch replay as acceptable.

Two independent Rust implementations could reasonably choose actual live tool delivery or the
candidate's delayed replay and still find support in different parts of the written artifacts.
That is a blocking `CONTRACT_ASSURANCE_DEFECT` in addition to the current Python parity defect.

## Manifest ledger

| Row | Result |
|---|---|
| AG-001 | Rule/evidence coherent; Python pointer still names removed `_run_once` and should be refreshed as evidence hygiene. |
| AG-002 | PASS; initial steering timing remains Pi-compatible. Rust status prose still calls PASS 4 the awaiting candidate. |
| AG-003 | PASS. |
| AG-004 | PASS for snapshot/post-turn ordering; overall spec coherence remains blocked by `L08-R004`. |
| AG-005 | PASS. |
| AG-006 | PASS. |
| AG-007 | PASS; active propagation remains genuinely Layer-09 deferred parity. |
| AG-008 | PASS for ordinary full-partial state; fallback timing is blocked under `L08-R002`. |
| AG-009 | **FAIL**; rule asserts adoption while documenting incomplete/delayed tool delivery and omitting update/payload fidelity. |
| AG-010 | PASS for invocation-local message sets. |
| AG-021 | PASS for represented terminal results. |
| AG-020 | Removed from manifest. |
| AG-022 | Removed from manifest. |

Manifest structure parses as 76 rows with 76 unique IDs. No placeholder scenario was counted as
satisfying a Layer-08 rule.

## Whole-state-machine regression audit

The following remain coherent with pinned Pi and the current contract outside the active findings:

- fresh typed prompt, message sequence, text, and text-plus-images;
- plain continuation and assistant-last steering/follow-up pre-drain branches;
- first-turn prompt then steering admission into one provider request;
- tool-, steering-, and follow-up-driven continuation;
- complete run-local context/model/thinking replacement and non-persistence;
- dynamic tools added by `added_tool_names` only;
- `terminate` suppressing only tool-driven continuation;
- represented error/aborted immediate terminal behavior;
- invocation-local `agent_end.messages` over multiple turns and independent runs;
- ordinary streaming partial fidelity and runtime-field settlement;
- absence of `max_steps` and local boundary-stop control from the Pi-equivalent run path.

Unexpected run failure and listener-failure behavior is not approved because the catch boundary and
tool-event causal timing remain wrong as detailed above.

## Canonical and runner audit

The agent directory contains 79 YAML scenarios: 60 executable and 19 explicit
`TO_BE_FILLED_FROM_PINNED_PI_BEHAVIOR` placeholders. The Python agent runner executes 35 and defers
19 placeholders; other scenario families are owned by their dedicated runners.

The rewritten no-cap scenario is now discriminating: 20 tool-result continuations occur before the
21st assistant response stops, exceeding the removed default cap of 16. Its targeted run passes.

No reviewed runner implements FIFO, run scheduling, context replacement, no-cap behavior, or
listener ordering itself. The remaining lifecycle defects are production/spec defects, not runner
simulation.

## Fresh gates

Run against the exact code candidate:

```text
uv run pytest -q
    PASS — 1046 collected; 1027 passed, 19 xfailed; 100.00% coverage

uv run ruff check .
    PASS

uv run mypy src
    PASS — 57 source files

uv run pytest -q -o addopts='' tests/conformance/test_schema_validation.py
    PASS — 185 passed

uv run pytest -q -o addopts='' tests/conformance/test_agent_conformance.py
    PASS — 35 passed, 19 xfailed

uv run pytest -q -o addopts='' tests/conformance/test_agent_conformance.py -k no_turn_count_cap
    PASS — 1 passed, 53 deselected

manifest parse / unique-ID audit
    PASS — 76 rows / 76 unique IDs
```

An initial isolated schema-only invocation inherited the repository-wide 100% coverage gate and
therefore exited nonzero despite all 185 schema tests passing; rerunning with the established
`-o addopts=''` schema command produced the clean result above. The full suite independently proves
the configured coverage gate.

Green tests do not override the source-level parity and assurance defects because the missing
listener/payload/timing cases are not discriminated by current evidence.

## Rust implementability and lower-layer impact

Rust's certified architecture has asynchronous streams and an EventBus and can represent the full
Agent event payloads idiomatically. It should not copy Python's post-batch replay mechanism.

The shared/Python owner must perform a narrow Layer-06 post-certification delta audit for the live
tool-event bridge. The certified synchronous Layer-06 EMIT mechanism is an implementation seam, not
authority to reduce Pi-visible Layer-08 behavior. An additive observer/callback integration may be
possible without changing Layer-06 observable outcomes; if not, the exact lower-layer contract
conflict must be formally reopened. This review does not prescribe the mechanism and does not
modify Layer 06.

## Findings

```text
PI_PARITY_DEFECT
    L08-R002 STILL OPEN
        delayed/reordered/non-blocking tool start/end delivery
        missing Agent-level tool_execution_update
        incomplete tool-end and assistant-update payloads
        incorrect no-start fallback reduce timing
        agent_start/success-agent_end listener failures outside recovery catch

CONTRACT_ASSURANCE_DEFECT
    L08-R004 STILL OPEN
        spec/manifest call a knowingly narrower seam adopted and complete
        removed AG-020/AG-022 remain in current requirement inventory prose

PI_BEHAVIOR_UNCERTAIN
    none

PARITY_CONSTRAINED_RISK
    none

PARITY_NEUTRAL_HARDENING
    refresh stale AG-001/AG-002/AG-004 Rust-review status and `_run_once` evidence pointers
```

## Narrow remediation required

1. Define and implement the complete Pi-observable Agent event union, including
   `tool_execution_update` and complete `message_update`/tool-end payloads.
2. Deliver tool start/update/end through the Agent listener seam at their real execution points,
   preserving Pi ordering, awaiting semantics, listener-failure causality, and state reduction.
   Perform the required Layer-06 post-certification delta audit rather than standardizing delayed
   replay as adopted parity.
3. Fix the no-start stream fallback so `message_start` reduces streaming state before its listener,
   and transcript append occurs only at `message_end` reduction.
4. Put ordinary `agent_start` and successful `agent_end` listener dispatch inside the same run
   failure catch as every other executor event; add discriminating recovery tests for both.
5. Remove the normative narrower-fidelity carve-out, restore one coherent complete seam, remove
   dangling AG-020/AG-022 inventory references, and add language/canonical evidence where the schema
   can express the behavior.

Any updated candidate SHA requires another complete independent Rust contract review.

## Scope confirmation

```text
Rust Layer 08 implementation modified
    NO

Python/shared candidate branches modified
    NO

Layer 09 started
    NO
```
