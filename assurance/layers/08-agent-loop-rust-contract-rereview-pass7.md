# Layer 08 — Independent Rust Contract Re-review (PASS 7)

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

PASS 7 removes PASS 6's inert capture-and-replay design and correctly joins update dispatches before
finalization. It also preserves pending-call visibility and makes update-listener rejection a run
failure. One callback-timing property remains different from pinned Pi: `asyncio.ensure_future`
does not execute the Agent listener coroutine until the event loop next cycles, whereas calling
Pi's async `processEvents()` starts its body immediately and invokes the first listener's
synchronous prefix before the tool's `update()` callback returns. The normative contract says
listener dispatch starts immediately at callback time, but the implementation and evidence do not
satisfy or discriminate that statement.

## Exact review target

| Item | Exact remote state reviewed |
|---|---|
| Code PR | `EGAILab/minion-agent#13` @ `2564f5b36cae27004f04ff74e08e6ab0277cc708` |
| Docs PR | `EGAILab/minion-agent-docs#3` @ `0af62da58562bb4968932b9f340b206fa0d50c17` |
| Pinned Pi | `b7bb00b936dbe21b8e160b3e89efdec361846699` |
| PASS-2 rejection | docs PR #4 @ `88a6aa6c1c1994026001c60045d4c55c00331a52` |
| PASS-3 rejection | docs PR #5 @ `a64b78ad2507b142ca7cda911b8968aa61af6a20` |
| PASS-4 rejection | docs PR #6 @ `65e665f28e29ebe6cf8deb792b206c108d32b1a6` |
| PASS-5 rejection | docs PR #7 @ `8875ebce5b20b8c67d6d86350464fb71107d1204` |
| PASS-6 rejection | docs PR #8 @ `752754ade96fc9c2c84eaafd61e671840373e82e` |

Issue `EGAILab/minion-agent#12` recorded the same candidate SHAs, `STATUS =
RUST_CONTRACT_REVIEW`, and `NEXT_OWNER = Codex`. Both candidate PRs were open, Ready for Review,
and unmerged. Detached candidate worktrees and this review branch were isolated from the unrelated
Phase-5 docs modification in the main checkout.

## Authority and source audit

Reviewed pinned Pi before the candidate:

- `packages/agent/src/types.ts`: `AgentEvent` and tool update payload;
- `packages/agent/src/agent.ts`: `runWithLifecycle`, `handleRunFailure`, `processEvents`, state
  reduction, listener iteration;
- `packages/agent/src/agent-loop.ts`: `executePreparedToolCall`, update callback, promise drain,
  finalization, and tool end.

Pinned `agent-loop.ts:670-711` calls `emit(tool_execution_update)` inside the synchronous tool
update callback and stores its returned promise. JavaScript begins an async function body when it
is called: pinned `processEvents()` performs its state switch and calls the first listener before
its first `await` yields. The tool callback itself does not await listener completion, but listener
delivery has already begun. Pi joins every stored promise after `execute()` settles and before
finalization/end. A rejected update listener propagates out of the second `Promise.all` in the
catch branch, so finalization/end do not run for that call.

## Finding closure ledger

| Finding | PASS-7 result | Status |
|---|---|---|
| `L08-R001` context snapshot / next-turn replacement | No regression. | **CLOSED** |
| `L08-R002` listener-bearing lifecycle | Capture/replay removed; join, pending state, and failure boundary fixed. Listener start remains deferred one event-loop turn. | **STILL OPEN — BLOCKING** |
| `L08-R003` streaming fidelity | No regression. | **CLOSED** |
| `L08-R004` normative coherence/evidence | Contract promises immediate listener start and cross-call interleaving; evidence does not prove either. | **STILL OPEN — BLOCKING** |
| `L08-R005` no turn cap | No regression. | **CLOSED** |
| `L08-R006` prompt/steering order | No regression. | **CLOSED** |
| `L08-R007` prompt forms | No regression. | **CLOSED** |
| `L08-R008` represented terminal results | No regression. | **CLOSED** |
| `L08-R009`/`L08-R010` boundary stop | Mechanism remains absent. | **CLOSED** |

## PASS-7 repairs independently verified

The additive `OnExecutionUpdate` hook is now threaded through the real Layer-06 execution seam.
Each update creates a task, tasks are retained per call, and `asyncio.gather` joins them after tool
execution settles but before `_finalize` and `tools/execution-end`. The PASS-6 tuple capture and
per-call replay from `on_execution_end` are gone.

Consequently:

- update listeners observe the call still present in `pending_tool_calls`;
- a rejected update listener prevents finalization/tool end and enters run failure settlement;
- the tool is not blocked waiting for the listener to finish;
- late updates remain suppressed;
- start/end live dispatch remains unchanged.

These are material and correct repairs.

## Remaining L08-R002 defect — callback-time listener start

The candidate's update callback does this:

```python
pending_updates.append(asyncio.ensure_future(on_execution_update(...)))
```

Creating the task schedules the coroutine but does not execute its body inline. A focused probe
against the exact candidate used a listener whose first statement records `listener-entered`, then
awaits once. The synchronous tool called `update()` and immediately recorded `tool-continued`.
Observed candidate order:

```text
tool-continued
listener-entered
listener-resumed
```

The direct JavaScript structural probe matching pinned `emit -> processEvents -> listener` yields:

```text
listener-entered
tool-continued
listener-resumed
```

This follows directly from pinned source: calling `processEvents()` runs its reducer and invokes
the first listener before the first `await` yields. A synchronous first listener can therefore
change state visible to the tool immediately after `update()` returns. PASS 7 delays that effect
until the Python event loop next runs the scheduled task.

This is not merely a memory-layout or Rust implementation preference. It is observable callback
and listener timing, a hazard the shared workflow explicitly requires reviewers to audit. An
independent Rust implementation could either invoke the listener chain to its first suspension at
the callback boundary or merely spawn a future; both satisfy the current prose's informal
"schedule" mechanism but behave differently.

Classification: `PI_PARITY_DEFECT` (`L08-R002` remains open).

## Remaining L08-R004 defect — contract and evidence overclaim closure

Current `spec/agent.md` and AG-009 state that listener dispatch starts immediately at callback time
and that PASS 7 reproduces Pi exactly. The implementation does not. The evidence also does not
discriminate the missing behavior:

- `test_on_execution_update_does_not_block_the_tools_own_execute` deliberately records only after
  the listener has already awaited, so it proves non-blocking completion, not eager listener entry;
- no test uses a listener with a synchronous prefix and checks that it runs before the tool's
  post-update continuation;
- no new test actually uses two parallel tool calls to assert cross-call callback/dispatch order,
  despite AG-009 claiming that behavior is proven by the single-call non-blocking test.

Two reasonable Rust implementations can therefore follow different observable timing while each
claims conformance. Classification: `CONTRACT_ASSURANCE_DEFECT` (`L08-R004` remains open).

## Manifest ledger

| Row | Result |
|---|---|
| AG-001 | PASS; implementation pointer cleanup remains non-blocking hardening. |
| AG-002 | PASS. |
| AG-003 | PASS. |
| AG-004 | PASS. |
| AG-005 | PASS. |
| AG-006 | PASS. |
| AG-007 | PASS; active abort propagation remains Layer 09 deferred parity. |
| AG-008 | PASS. |
| AG-009 | **FAIL** for callback-time update delivery and discriminating evidence. |
| AG-010 | PASS. |
| AG-021 | PASS. |
| AG-020 / AG-022 | Correctly absent. |

Manifest structure contains 76 rows and 76 unique IDs. Placeholder scenarios remain explicitly
deferred and are not counted as satisfying implemented evidence.

## Whole-state-machine regression and Rust feasibility

PASS 7 changes only the update hook path plus evidence. No regression was found in the previously
audited prompt/continue forms, context snapshot and whole-context replacement, dynamic tool
visibility, first-turn steering, turn continuation, terminate, represented error/aborted handling,
failure recovery, runtime state settlement, `agent_end.messages`, or Layer-09 boundary.

The canonical runner remains thin. Rust can implement the Pi rule without copying Python mechanics:
the synchronous update callback can begin the Agent reducer/listener dispatch and store the
resulting future, while execution later joins those futures before finalization. No certified
lower-layer observable contract needs reopening; the existing additive Layer-06 observer seam can
be corrected narrowly.

## Fresh gates

```text
uv run pytest -q
    PASS — 1057 collected; 1038 passed, 19 xfailed; 100.00% coverage

uv run ruff check .
    PASS

uv run mypy src
    PASS — 57 source files

schema validation
    PASS — 185 passed

agent conformance
    PASS — 35 passed, 19 xfailed

manifest inventory
    PASS — 76 rows / 76 unique IDs

focused callback-timing probe
    FAIL against pinned order — candidate: tool-continued before listener-entered
```

Green general gates do not override the discriminating source-level mismatch.

## Findings

```text
PI_PARITY_DEFECT
    L08-R002 STILL OPEN
        update listener coroutine is scheduled at callback time but does not begin there
        first listener synchronous effects occur after the tool continues, unlike pinned Pi

CONTRACT_ASSURANCE_DEFECT
    L08-R004 STILL OPEN
        spec/AG-009 claim immediate callback-time listener start that implementation lacks
        single-call evidence is cited as proof of untested cross-call ordering

PI_BEHAVIOR_UNCERTAIN
    none

PARITY_CONSTRAINED_RISK
    none

PARITY_NEUTRAL_HARDENING
    refresh stale implementation/status pointers in unaffected manifest prose
```

## Narrow remediation

1. Make the update callback begin the Agent reduce/listener path before returning, while retaining
   Pi's non-blocking completion and later join-before-finalize behavior.
2. Add a discriminating listener-synchronous-prefix test proving `listener-entered` precedes the
   tool's continuation after `update()`.
3. Add a real two-call parallel test proving callback/dispatch initiation order across calls.
4. Align spec/AG-009 claims and evidence pointers with the actually implemented language-neutral
   rule. Any changed candidate SHA requires another exact-SHA independent review.

## Scope confirmation

```text
Rust Layer 08 implementation modified
    NO

Python/shared candidate branches modified
    NO

Layer 09 started
    NO
```
