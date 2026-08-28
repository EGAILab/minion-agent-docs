# Layer 08 — Agent Loop (run/turn state machine) — Python

**Status: IN PROGRESS. PASS 1 (this document) corrects the run/turn event boundary and is NOT a
full Layer-08 certification.** Several manifest rows (`AG-002`, `AG-003`, `AG-005`, `AG-006`,
`AG-007`, `AG-008`, `AG-009`, `AG-010`) still carry a false `disposition: adopted` inherited from
before this pass and remain open, disclosed defects -- see "Active findings" below.

Coordination: `EGAILab/minion-agent#12`, branch `layer/08-python-shared` (both repos).

## Starting state

- `minion-agent`: `d0911cbd2b1df8332f5422f99d33c5426fe3e3f2` (`main` at the point
  `layer/08-python-shared` branched -- Layer 07 cross-language certified and its manifest evidence
  committed; not the `19ecb88...` PASS-4-remediation SHA, which is an ancestor of this, not the
  branch's own base)
- `minion-agent-docs`: `881daf5c67f368740b245df872c0da9cf8c29a9a` (`master` at the point
  `layer/08-python-shared` branched -- includes `process/agent-workflow.md`)
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`

## Pi audit

Read in full: `packages/agent/src/agent-loop.ts` (796 lines), `packages/agent/src/agent.ts` (592
lines, re-read beyond the Layer-07 surface), `packages/agent/src/types.ts` (443 lines). Directory
listing of `packages/agent/src/` confirmed no other Layer-08-relevant files (`harness/`, `search/`,
`index.ts`, `node.ts`, `proxy.ts`, `stream-fn.ts` are package-barrel/CLI/transport concerns).

Full findings recorded in `spec/agent.md`'s "Layer 08" section. Summary of what this pass acted on:

- Run = one `prompt()`/`continue()` invocation (`agent_start`/`agent_end`). Turn = one assistant
  response + its tool calls/results, never more than one provider request
  (`turn_start`/`turn_end`). Confirmed directly against `runAgentLoop`/`runLoop`.
- `agent_start`/`turn_start` fire in that order, before the entering messages are logged, on every
  turn (not only the first) -- confirmed against `runAgentLoop` (top-level, turn 1) and `runLoop`'s
  own `if not firstTurn: emit turn_start` branch (turn 2+).
- `agent_end.messages` is invocation-local: pre-seeded with prompt messages for `runAgentLoop`,
  empty-seeded for `runAgentLoopContinue` -- confirmed exactly, though only the pre-seeded case is
  currently reachable through Minion's own architecture (see "Active findings").
- `turn_end{message, toolResults}`: pi's real payload, not an empty event.
- Of pi's `turn_end -> prepareNextTurn -> shouldStopAfterTurn -> steering poll` ordering,
  `prepareNextTurn` has no Minion equivalent at all; the other three stages are real and verified.

Two `PI_BEHAVIOR_UNCERTAIN` candidates were raised and dispositioned as non-blocking with cited
evidence (not asserted as "minor"):

- Stream-exhaustion-without-terminal fallback (`streamAssistantResponse`, agent-loop.ts:363-371):
  confirmed out of Layer-08's observable scope. `_run_step` calls the already-certified Layer-02/04
  `collect()` (`src/minion_agent/llm/stream.py`), which owns all raw stream iteration and already
  has its own, different, defined behavior (raises `AdapterProtocolError` on an adapter that ends
  without a terminal chunk, rather than pi's defensive fallback). Layer 08 never touches raw stream
  chunks itself; whatever `collect()` returns or raises is what Layer 08 reacts to.
- Aborted-tool-call error tagging (`executePreparedToolCall`'s catch block): explicitly Layer 09's
  ownership (active abort propagation), not Layer 08's -- not resolved here, and not required to be.

## Contract found to already exist, and its defect

`pi-parity-manifest.yaml` already carried ten placeholder rows for this exact surface, `AG-001`
through `AG-010`, all `disposition: adopted`, predating this pass. Checked directly: several cited
only still-unfilled placeholder canonical scenarios (`family`/`given`/`when`/`expect` shape,
`TO_BE_FILLED_FROM_PINNED_PI_BEHAVIOR` throughout) as their evidence -- a false certification claim,
not merely undocumented. `AG-001` (initial prompt event order) and `AG-004` (turn definition/order)
are corrected this pass with real evidence for what this pass actually verified and implemented.
The other eight remain flagged, not corrected -- see "Active findings".

## Python implementation

`src/minion_agent/agent_loop/driver.py`:

- `_run_turn` renamed `_run_once` (owns `AGENT_START`/`AGENT_END`, the run boundary -- pi's own
  vocabulary, not `_run_step`'s old multi-step "turn"). `_run_step` kept its name (per explicit
  governing instruction: the helper name does not need to match pi's own noun set, since pi has no
  "step" concept at all -- only the *observable boundary it emits* needs to match pi's turn
  exactly), now brackets itself with `TURN_START`/`TURN_END` around exactly one provider request,
  appended in pi's own order (`TURN_START` before the entering messages).
- `causes` relocated from the old `TURN_START`/`TURN_END` to `AGENT_START`/`AGENT_END`: it describes
  what triggered the *run*, not each turn within it.

`src/minion_agent/session/events.py`: added `EventKind.AGENT_START`/`AGENT_END` ("agent/start"/
"agent/end"); removed `EventKind.STEP_START`/`STEP_END` (made unused by this pass's own change --
zero manifest rows or spec text ever claimed them, confirmed by grep before removal).

`src/minion_agent/agent/projection.py`: `AgentStart`/`AgentEnd` are now driven entirely by real
`AGENT_START`/`AGENT_END` log entries (never synthesized around the whole log -- a log with no run
in it now projects to nothing; a log with several runs projects several independently-scoped
brackets). `AgentEnd.messages` is a run-scoped accumulator (every message produced/consumed since
the matching `AGENT_START`, reset at each one) -- reconstructed from existing `MessageStart`/
`MessageEnd` emission, not a second, independently-logged copy. `TurnEnd.message`/`.tool_results`
similarly reconstructed per-turn from the same source. `TurnStart` lost its `causes` field (now a
bare, zero-field dataclass matching pi's own bare `turn_start` exactly).

## Canonical scenarios corrected

Two existing legacy-shape scenarios asserted the pre-fix (wrong) single-turn-bracket-spans-two-
requests shape and are now corrected to match pi's real per-turn granularity:

- `conformance/agent/tool-round-trip.yaml`
- `conformance/agent/projected-execution-ends-follow-completion-order.yaml`

Five other legacy-shape scenarios (`turn-lifecycle`, `causes-preserved-under-claim-all`,
`premature-eof-synthesizes-error-terminal`, `public-stream-fuses-after-first-terminal`,
`represented-provider-error-rides-stream`) needed no changes -- each exercises exactly one provider
request, so the pre-fix single-bracket shape happened to already be correct for them; they continue
passing unmodified.

Six unified-shape placeholder scenarios remain `TO_BE_FILLED_FROM_PINNED_PI_BEHAVIOR`
(`initial-prompt-order-after-turn-start`, `initial-steering-before-first-request`,
`continue-steering-no-double-drain`, `agent-end-messages-prompt-vs-continuation`,
`turn-lifecycle-order`, `terminate-still-runs-prepare-and-stop-policy`) -- not filled this pass;
`AG-001`/`AG-004` cite real, already-passing legacy-shape evidence instead, explicitly not claiming
these placeholders as evidence.

## RED → GREEN

- Schema-level: reproduced the wrong single-turn-bracket shape directly by running
  `tool-round-trip.yaml`/`projected-execution-ends-follow-completion-order.yaml` against the
  unmodified `driver.py`/`projection.py` and observing the old (pre-fix) event sequence; both now
  pass against the corrected two-turn sequence.
- Append-order: reverted the `TURN_START`-before-`USER_MESSAGE` fix and re-ran
  `test_the_turn_is_logged_in_order`, reproducing the wrong order before restoring it.
- All renamed/relocated `EventKind` references across ~10 test files were mechanically updated to
  match (`STEP_START`/`STEP_END` -> `TURN_START`/`TURN_END`; `TURN_START`/`TURN_END`'s `causes`/
  `reason` reads -> `AGENT_START`/`AGENT_END`), each verified failing (`AttributeError`/`KeyError`)
  before the fix and passing after.

## Contract-quality check

```text
Does a turn ever bracket more than one provider request?                 NO (was YES before this
                                                                            pass)
Does agent_end.messages scope to one run, not the whole log?              YES
Does a log with no run boundary synthesize a false AgentStart/AgentEnd?   NO (was YES before this
                                                                            pass)
Is causes/reason data attached at the correct (run vs turn) granularity?  YES
Duplicate state authority (raw log payload vs. derived projection)?        NO -- TurnEnd/AgentEnd
                                                                            payloads are
                                                                            reconstructed from
                                                                            existing log content,
                                                                            never double-logged
Contract quality (this pass's own scope)                                  PASS
```

## Quality gates (fresh, this pass)

```text
full pytest (coverage enabled):     980 passed, 19 xfailed, 0 failed, 100.00% coverage
ruff check .:                        All checks passed
ruff format --check (touched files): clean
mypy (configured scope + typing fixtures): Success, no issues found in 59 source files
conformance/ (full):                 all passing (was 32 failing immediately after the boundary
                                      fix, before test/scenario updates)
manifest parse + unique-ID audit:    75 / 75 unique (unchanged -- AG-001/AG-004 corrected in place,
                                      no new rows)
```

## Active findings

```text
PI_PARITY_DEFECT              none blocking this pass's own scope
CONTRACT_ASSURANCE_DEFECT     AG-002/003/005/006/007/008/009/010 still carry a false
                               `disposition: adopted` inherited from before this pass, several
                               citing only unfilled placeholder scenarios as evidence -- flagged,
                               not corrected this pass; must be resolved before Layer 08 as a whole
                               is certified
PI_BEHAVIOR_UNCERTAIN         none active (both candidates dispositioned non-blocking, see Pi
                               audit above)
PARITY_CONSTRAINED_RISK       none blocking
```

Substantial, disclosed scope remains open (not findings against this pass's own narrow claim, but
required before Layer 08 as a whole can be certified): `prompt()`/`continue()` caller rules,
`prepareNextTurn`, mid-run follow-up continuation (Minion's pump architecture starts a new run per
queued follow-up batch rather than continuing one run across several), `streamingMessage`/
`pendingToolCalls`/`errorMessage` transition-timing writes, `handleRunFailure`. Full detail in
`spec/agent.md`'s "Still open" list.

## Verdict

```text
Python Layer 08     PARTIAL -- run/turn event boundary corrected and verified; substantial scope
                     remains unimplemented (see Active findings)
Rust Layer 08        NOT_IMPLEMENTED
shared Layer-08 contract   NOT READY FOR RUST REVIEW -- AG-002/003/005-010's false-adopted
                            disposition must be corrected first, and the "still open" scope is too
                            large to hand off as a coherent contract yet
Layer 08 cross-language     NOT CLOSED
Layer 09                     NOT STARTED
```

## Next action

Continue the Layer-08 Python/shared pass: correct AG-002/003/005-010's dispositions (narrow each to
what is actually true today, matching the AG-001/AG-004 pattern), then work through the "still open"
list in `spec/agent.md`, in particular `prompt()`/`continue()` caller rules and
`streamingMessage`/`pendingToolCalls`/`errorMessage` transition timing, before any Rust handoff.
