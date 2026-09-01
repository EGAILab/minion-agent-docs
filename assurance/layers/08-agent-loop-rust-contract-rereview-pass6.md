# Layer 08 — Independent Rust Contract Re-review (PASS 6)

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

PASS 6 correctly repairs live tool start/end delivery, complete event payloads, the no-start
fallback reducer, and the outer recovery catch. One Pi-visible part of `L08-R002` remains open:
`tool_execution_update` is still buffered and grouped by call until that call ends instead of being
sent into the Agent event seam when the tool invokes its update callback. The normative spec and
AG-009 explicitly standardize the remaining difference as an unavoidable constraint while retaining
`disposition: adopted`; therefore `L08-R004` also remains open.

## Exact review target

| Item | Exact remote state reviewed |
|---|---|
| Code PR | `EGAILab/minion-agent#13` @ `fc277cc7e136f244fafc0301ee9264bb3c190ba6` |
| Docs PR | `EGAILab/minion-agent-docs#3` @ `d8ca72fbd8d3129d6fdacf01a0835d765b33297e` |
| Pinned Pi | `b7bb00b936dbe21b8e160b3e89efdec361846699` |
| PASS-2 rejection | docs PR #4 @ `88a6aa6c1c1994026001c60045d4c55c00331a52` |
| PASS-3 rejection | docs PR #5 @ `a64b78ad2507b142ca7cda911b8968aa61af6a20` |
| PASS-4 rejection | docs PR #6 @ `65e665f28e29ebe6cf8deb792b206c108d32b1a6` |
| PASS-5 rejection | docs PR #7 @ `8875ebce5b20b8c67d6d86350464fb71107d1204` |

Issue `EGAILab/minion-agent#12` recorded the same candidate SHAs, `STATUS =
RUST_CONTRACT_REVIEW`, and `NEXT_OWNER = Codex`. Both candidate PRs were open, Ready for Review,
and unmerged. Detached candidate worktrees and this review branch were clean. The unrelated Phase-5
docs modification in the main checkout was preserved untouched.

## Independent Pi audit

Reviewed pinned Pi directly:

- `packages/agent/src/types.ts`: `AgentEvent`, `AgentState`, `AgentLoopTurnUpdate`, tool update
  payloads;
- `packages/agent/src/agent.ts`: `runWithLifecycle`, `handleRunFailure`, `finishRun`,
  `processEvents`, prompt/continue entry points;
- `packages/agent/src/agent-loop.ts`: run/turn state machine, assistant streaming, sequential and
  parallel tool execution, `executePreparedToolCall`, tool result emission, `prepareNextTurn`, stop
  and queue ordering.

The decisive update behavior is explicit at pinned `agent-loop.ts:670-711`:

1. the tool calls synchronous `onUpdate(partialResult)`;
2. that callback immediately calls `emit(tool_execution_update)` and stores the returned promise in
   `updateEvents`, preserving invocation order;
3. when tool execution settles, Pi sets `acceptingUpdates = false` and awaits
   `Promise.all(updateEvents)` before returning the executed outcome;
4. only later does finalization and `tool_execution_end` occur.

Thus Pi's update dispatch is fire-and-forget relative to the synchronous tool callback, but it is
not deferred until tool end and not regrouped by call completion. Listener work is initiated in
actual callback order and drained before finalization/end.

## Previous finding ledger

| Finding | PASS-6 result | Current status |
|---|---|---|
| `L08-R001` complete snapshot / `prepareNextTurn` | Run-local context/model/thinking replacement, isolation, and targeted dynamic tool growth remain coherent. | **CLOSED** |
| `L08-R002` unified lifecycle/recovery | Start/end, payload, fallback, and catch-boundary repairs pass. Update timing/order/state/failure behavior remains non-Pi. | **STILL OPEN — BLOCKING** |
| `L08-R003` streaming fidelity | Full partials and raw assistant event payloads remain coherent. | **CLOSED** |
| `L08-R004` normative coherence | Removed-row inventory is fixed, but spec/AG-009 still normalize the known update mismatch as adopted. | **STILL OPEN — BLOCKING** |
| `L08-R005` no turn cap | Removed; 20-tool-turn canonical remains discriminating. | **CLOSED** |
| `L08-R006` prompt before steering | No regression. | **CLOSED** |
| `L08-R007` prompt forms | No regression. | **CLOSED** |
| `L08-R008` represented terminal results | No regression. | **CLOSED** |
| `L08-R009` boundary-stop ownership | Mechanism remains absent. | **CLOSED** |
| `L08-R010` boundary-stop/follow-up contradiction | Superseded by removal. | **CLOSED** |

## PASS-6 repairs independently verified

### Live tool start/end

The optional `OnExecutionStart`/`OnExecutionEnd` hooks in `tools/execute.py` and `tools/batch.py` are
additive and awaited at the existing Layer-06 event points. With hooks absent, prior Layer-06
behavior is unchanged. With Agent hooks present:

- a start-listener failure prevents that call's later pipeline work;
- sequential order is genuinely `start A, end A, start B, end B`;
- parallel start/preflight and completion-order end behavior remains compatible;
- length-stop and immediate-result paths also invoke the hooks at the correct boundaries.

This part of `L08-R002` is closed without reopening Layer-06 semantics.

### Payload completeness

`MessageUpdate` now carries the concrete Layer-02/04 stream event plus the complete partial message.
`ToolExecutionEnd` now carries call id, tool name, finalized `ToolResult`, and error flag.
`ToolExecutionUpdate` exists with call id/name/original arguments/partial result. Offline projection
stores the otherwise non-derivable delta and terminate fields. These are independently implementable
in Rust.

### Reduce/catch fixes

The no-start stream branch now dispatches `MessageStart` with `streaming_message` set before the
assistant transcript entry is appended at `MessageEnd`. Ordinary `agent_start` and successful
`agent_end` dispatches now sit inside `_execute_run`'s recovery catch, including Pi's possible
successful-then-failed double `agent_end` reduction when the successful event's listener throws.

## Blocking evidence — tool updates remain delayed and regrouped

Candidate `_run_step` registers a synchronous `TOOLS_UPDATE` listener which only appends tuples to
one list (`driver.py:946-951`). No Agent listener is invoked at update time. When a call reaches
`on_execution_end`, the candidate first removes its id from `pending_tool_calls`, then filters every
stored update for that call and serially dispatches them, and only afterward dispatches
`ToolExecutionEnd` (`driver.py:961-981`).

This differs observably from Pi in four ways:

1. **Cross-call order.** If parallel calls emit `A1, B1, A2` and B completes first, Pi starts Agent
   update delivery in `A1, B1, A2` callback order. Candidate delivers `B1`, then end B, then
   `A1, A2`, then end A.
2. **Listener timing.** Pi invokes the Agent event sink at each update callback and stores its
   promise. Candidate invokes no Agent listener until execution and finalization have already
   completed.
3. **State visibility.** Pi removes a call from `pendingToolCalls` only when processing
   `tool_execution_end`, after its updates. Candidate removes the id before dispatching its updates,
   so update listeners observe the call as no longer pending.
4. **Failure semantics.** In Pi, rejection of an update listener promise is observed by
   `await Promise.all(updateEvents)` inside `executePreparedToolCall`'s `try`; the catch converts the
   call into an error result, which still proceeds through finalization/end. Candidate update
   listener failure occurs inside `on_execution_end`, after Layer-06 finalization and its own end
   EMIT; it propagates as a batch/run failure and prevents the Agent `ToolExecutionEnd` event.

The new test `test_tool_execution_update_reaches_the_lifecycle_seam` proves only that one update
event eventually appears before that call's Agent end event. It does not discriminate callback-time
delivery, global parallel order, pending-state visibility, or listener failure conversion.

The stated SDK limitation does not force this result. The synchronous update callback can enqueue or
schedule the Agent dispatch at callback time and retain the resulting awaitable/task, while the
execution seam drains those tasks before finalization/end—the same structural adaptation Pi uses.
A global ordered update queue/cursor also preserves cross-call emission order without changing the
tool authoring signature. Rust can implement the language-neutral rule with futures/tasks rather
than copying the Python mechanism.

Therefore the remaining behavior is a `PI_PARITY_DEFECT`, not a parity-neutral implementation
constraint or approved divergence.

## Normative coherence — L08-R004

The current requirement inventory now correctly names only `AG-001`..`AG-010` and `AG-021`, and the
old start/end narrower-fidelity carve-out is gone. However:

- `spec/agent.md` calls the Agent event seam complete and adopted while declaring cross-call update
  interleaving “unreproducible” and specifying per-call replay immediately before end;
- AG-009 repeats the same claim and keeps `disposition: adopted`;
- both conflict with pinned Pi's actual callback-time `emit` plus promise-drain algorithm;
- the evidence does not discriminate the difference.

A Rust implementer following Pi would initiate updates in global callback order; one following the
candidate prose would group them at call completion. Both choices are observably different. The
contract is therefore still incomplete/incorrect for independent implementation.

## Manifest row audit

| Row | Result |
|---|---|
| AG-001 | PASS; implementation evidence pointer still names removed `_run_once` and should be refreshed. |
| AG-002 | PASS; first-turn steering and pre-drain behavior coherent. |
| AG-003 | PASS. |
| AG-004 | PASS for turn/snapshot rules. |
| AG-005 | PASS. |
| AG-006 | PASS. |
| AG-007 | PASS; active abort propagation remains Layer-09 deferred parity. |
| AG-008 | PASS. |
| AG-009 | **FAIL** for update timing/order/state/failure semantics; other PASS-6 repairs pass. |
| AG-010 | PASS. |
| AG-021 | PASS. |
| AG-020 / AG-022 | Correctly absent. |

Manifest structure parses as 76 rows with 76 unique IDs. Placeholders are not cited as satisfying
implemented Layer-08 rules.

## Whole-state-machine and contract-quality audit

No regression was found in:

- typed prompt, prompt sequence, text, and text-plus-images normalization;
- plain continuation and assistant-last steering/follow-up pre-drain;
- first-turn prompt/steering admission into one provider request;
- tool-, steering-, and follow-up-driven continuation;
- full run-local context/model/thinking replacement and independent-run isolation;
- targeted `added_tool_names` growth;
- terminate behavior;
- represented error/aborted immediate termination;
- unexpected run failure and recovery listener interruption outside the update-specific defect;
- invocation-local `agent_end.messages`;
- runtime state settlement;
- removal of `max_steps` and boundary stop;
- Layer-09 boundary.

The canonical runner remains a thin fixture/dispatch/normalization bridge and does not simulate the
remaining update semantics. The defect is in production and normative prose, not the runner.

## Fresh evidence and gates

```text
uv run pytest -q
    PASS — 1052 collected; 1033 passed, 19 xfailed; 100.00% coverage

uv run ruff check .
    PASS

uv run mypy src
    PASS — 57 source files

uv run pytest -q -o addopts='' tests/conformance/test_schema_validation.py
    PASS — 185 passed

uv run pytest -q -o addopts='' tests/conformance/test_agent_conformance.py
    PASS — 35 passed, 19 xfailed

manifest parse / unique-ID audit
    PASS — 76 rows / 76 unique IDs
```

Green gates do not override the undetected source-level parity defect.

## Findings

```text
PI_PARITY_DEFECT
    L08-R002 STILL OPEN
        tool_execution_update is dispatched at call end, not callback time
        parallel updates are regrouped by call completion
        update listeners observe pending state too late
        update-listener failures become run failures rather than tool error outcomes

CONTRACT_ASSURANCE_DEFECT
    L08-R004 STILL OPEN
        spec/AG-009 standardize the known update mismatch as adopted/complete
        evidence does not discriminate Pi's update semantics

PI_BEHAVIOR_UNCERTAIN
    none

PARITY_CONSTRAINED_RISK
    none

PARITY_NEUTRAL_HARDENING
    refresh stale implementation/review-status pointers in unaffected AG rows
```

## Narrow remediation required

1. Initiate Agent `tool_execution_update` delivery when the Layer-06 update callback fires, preserve
   global callback order across concurrent calls, and drain the resulting dispatch tasks before
   that call finalizes/ends.
2. Preserve Pi's pending-call visibility during update delivery and Pi's update-listener failure
   conversion path.
3. Add discriminating tests for parallel cross-call update order, update listener observation of
   pending state, and update-listener rejection behavior.
4. Remove the “unreproducible” carve-out and specify one Pi-faithful language-neutral update rule in
   spec and AG-009. If an additive Layer-06 observer hook is used, perform the same narrow
   post-certification delta audit already applied successfully to start/end.

Any candidate SHA change requires another complete independent Rust contract review.

## Scope confirmation

```text
Rust Layer 08 implementation modified
    NO

Python/shared candidate branches modified
    NO

Layer 09 started
    NO
```
