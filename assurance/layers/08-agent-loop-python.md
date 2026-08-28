# Layer 08 — Agent Loop (run/turn state machine) — Python

**Status: PASS 2 complete. Python Layer 08 is substantially implemented and self-certified,
pending independent Rust contract review before certification is final.** See "PASS 2" below for
the complete picture; PASS 1's own text (run/turn event boundary only) is preserved unmodified
beneath it as historical record.

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

## Next action (superseded -- see PASS 2 below)

Continue the Layer-08 Python/shared pass: correct AG-002/003/005-010's dispositions (narrow each to
what is actually true today, matching the AG-001/AG-004 pattern), then work through the "still open"
list in `spec/agent.md`, in particular `prompt()`/`continue()` caller rules and
`streamingMessage`/`pendingToolCalls`/`errorMessage` transition timing, before any Rust handoff.

# PASS 2 — complete Layer-08 semantic surface and manifest repair

## Repair of PASS-1's own coordination/evidence metadata

Corrected before substantive implementation, per the governing instruction's own explicit §0:

- "Starting state" above corrected from the Layer-07 PASS-4-remediation SHA (`19ecb88...`) to the
  branch's own actual merge-base with each repo's default branch (`d0911cb...`/`881daf5...`,
  confirmed via `git merge-base`) -- `19ecb88...` is an ancestor of the correct base, not the base
  itself.
- PR #13's body corrected to name its companion PR explicitly (`EGAILab/minion-agent-docs#3`).
- Both PRs converted to Draft (workflow hygiene, not a semantic requirement) until this candidate
  was genuinely coherent.

## Manifest disposition audit -- not a mechanical `adopted` -> `deferred parity` relabel

The governing instruction was explicit: `disposition` answers "what is Minion's semantic decision
for this Pi surface," not "is it implemented/tested/certified." Each of `AG-002`/`003`/`005`/`006`/
`007`/`008`/`009`/`010` was independently audited against pinned Pi and against what this pass
actually implements, one row at a time -- not batch-relabeled.

Result: seven rows (`AG-002`, `AG-003`, `AG-005`, `AG-006`, `AG-008`, `AG-009`, `AG-010`) are Layer
08's own target and ARE implemented this pass -- each corrected to `disposition: adopted`, with real
evidence replacing every citation of a still-unfilled placeholder scenario. One row (`AG-007`,
active abort propagation) was never Layer 08's target at all -- it is explicitly Layer 09's, per the
already-certified Layer-07 contract's own deferral and this pass's own governing instruction ("Do
not implement Layer-09 active cancellation propagation") -- corrected to `disposition: deferred
parity`, recording the exact later layer (09) and trigger (a future Layer-09 pass). No row was
relabeled `deferred parity` merely because it was unfinished; every `deferred parity` here reflects
a genuine "Pi requires this, a later NAMED layer owns it" decision.

Full per-row rationale is in `pi-parity-manifest.yaml` itself (each row's own `rule:` text); summary:

```text
AG-001  adopted (PASS 1, unchanged)          initial prompt event order
AG-002  adopted (corrected, real evidence)    initial steering poll + continue()'s no-double-drain
AG-003  adopted (corrected, real evidence)    continuation invocation output (agent_end.messages)
AG-004  adopted (PASS 1, unchanged)          turn definition/order
AG-005  adopted (corrected, real evidence --   follow-up timing (mid-run continuation implemented,
         genuine implementation gap closed)    not just an evidence gap)
AG-006  adopted (corrected, real evidence -- prompt()/continue_() caller rules (new entry points)
         genuine implementation gap closed)
AG-007  deferred parity (corrected --          active abort propagation: Layer 09's own target,
         was wrongly `adopted`)                not Layer 08's
AG-008  adopted (corrected, real evidence --   runtime-state transition timing (narrowed off the
         genuine implementation gap closed)    already-certified Layer-07 config-facing subset)
AG-009  adopted (corrected, real evidence --   handleRunFailure
         genuine implementation gap closed)
AG-010  adopted (corrected, real evidence --   agent_end message set (run-scoped accumulator,
         genuine implementation gap closed)    both pre-seeded and empty-seeded paths)
```

## Python implementation (this pass)

`src/minion_agent/agent_loop/driver.py` restructured substantially:

- **`prompt(message)`/`continue_()`** (new): pinned Pi's `Agent.prompt()`/`Agent.continue()`
  exactly, including all four distinct "already processing" strings (`prompt()`'s, `continue_()`'s,
  the internal `_run_wrapped` defensive guard's, and the already-certified Layer-07 `reset()`'s),
  `continue_()`'s full branch structure (steering-drain with `skip_initial_steering_poll`,
  follow-up-drain, plain continuation), confirmed directly against `agent.ts:348-407`.
- **`_RunSnapshot`** (new): `system_prompt`/`model`/`thinking_level` read once at run start
  (pinned Pi's `createContextSnapshot()`), with an `apply()` method `prepareNextTurn` updates
  run-locally, never written back to `AgentInstance`.
- **`_run_wrapped`/`_execute_run`/`_run_inner`** (restructured): status/`error_message` reset at
  run entry; a genuine outer/inner nested loop matching pinned Pi's `runLoop` exactly -- the outer
  loop polls follow-up only once the inner loop naturally exhausts, and continues the *same* run
  when follow-up is found (mid-run continuation, previously missing entirely); `terminate` now
  affects only `has_more_tool_calls`, never skipping `prepareNextTurn`/`shouldStopAfterTurn`/the
  steering poll for that turn (a correction to a previously-wrong "hard termination precedes the
  decision" design, confirmed wrong against pinned Pi source).
- **`_prepare_next_turn`** (new): `agent/prepare-next-turn` waterfall event, returning
  `RunConfigUpdate` (new, in `decisions.py`), applied to the run snapshot.
- **`_settle_run_failure`/`_LoopCallbackFailure`** (new): pinned Pi's `handleRunFailure`, narrowly
  scoped to `agent/pre-step`/`agent/turn-stopping`/`agent/prepare-next-turn` dispatch failures only
  -- each of the three dispatch call sites wraps its own `Exception` and re-raises as
  `_LoopCallbackFailure`, so a genuinely different failure (an unresolvable model, a provider
  error) is never caught by this fallback and continues to propagate/settle via its own existing,
  different mechanism.
- **`_run_step`**: now reads `snapshot.system_prompt`/`.model` instead of
  `self.instance.definition.system`/`.model` (the disclosed Layer-07 PASS-2.5 scope boundary,
  closed this pass); writes `streaming_message` (text-only partial content, disclosed
  simplification -- see below) and `pending_tool_calls` (via temporary `tools/execution-start`/
  `tools/execution-end` listeners around the batch call, an existing Layer-06 seam, not a new
  resolution mechanism) for the duration of one provider request/tool batch; sets `error_message`
  from a truthy `reply.error_message`.

`src/minion_agent/agent/events.py`: added `AGENT_PREPARE_NEXT_TURN` (waterfall); corrected
`AGENT_TURN_STOPPING`'s own docstring, which previously and incorrectly claimed hard termination
skipped dispatch entirely.

`src/minion_agent/agent/decisions.py`: added `RunConfigUpdate` (`system_prompt`/`model`/
`thinking_level`, all-`None` terminal = pass-through).

`tests/conformance/agent_runner.py`: added a `continue: true` step type (thin call-through to
`loop.continue_()`, same pattern as `await_idle`) and an `"agent_end_messages"` extraction (one
list of message texts per `AgentEnd`, for asserting run-scoped `agent_end.messages` directly).
`conformance/schema/agent-scenario.schema.json` extended to match (`continue` step property,
`expect_agent_end_messages` top-level field).

## Disclosed simplification: `streaming_message` content fidelity

`streaming_message`'s non-`None`/`None` *transition timing* is exact (matches pinned Pi's
`message_start`/`message_update`/`message_end` write points precisely). Its *content* during that
window is text-only (accumulated `TextDelta`s); thinking/tool-call partial content is not
reconstructed. This is a genuine, disclosed simplification, not a silently dropped requirement:
Minion's certified Layer-02/04 `collect()` exposes only raw stream deltas, never a live partial
message object for this layer to build a richer reconstruction from, and inventing a full
incremental content-block reconstructor (matching arbitrary partial tool-call JSON, etc.) would be
new Layer-02/04-adjacent capability, out of this narrow Layer-08 pass's scope to add. Recorded as
`intentional divergence` on content fidelity specifically, within `AG-008`'s own disposition text --
not a `PI_BEHAVIOR_UNCERTAIN` (there is no uncertainty about what pinned Pi does) and not a
`PI_PARITY_DEFECT` (the observable contract this layer actually certifies -- presence/absence
timing -- is exact).

## Canonical evidence added this pass

Two new legacy-shape scenarios, both exercising the real `AgentLoop` end to end:

- `two-runs-have-independently-scoped-agent-end-messages.yaml` -- two separate followup+await_idle
  cycles, proving `agent_end.messages` is independently scoped per run (item 1 of the governing
  instruction's canonical-evidence list).
- `continuation-excludes-the-prior-runs-messages.yaml` -- `continue()`'s follow-up-drain sub-case
  (via the new `continue: true` step), proving the second run's `agent_end.messages` excludes the
  first run's own messages (item 2's steering/follow-up-drain half; the plain empty-seeded
  continuation half of item 2 remains Python-test-only --
  `test_continue_sends_full_history_when_last_message_is_not_assistant` -- since it requires no
  entering messages at all, which a purely declarative scenario cannot force without a custom
  turn-stopping listener the runner does not support).

Items 3/4 (mutable config changed between/during runs), 8/9 (`prepareNextTurn`/`shouldStopAfterTurn`
ordering, terminate's non-skip behavior) require registering a custom Python listener mid-scenario,
which the declarative YAML runner has no mechanism for -- these remain Python-test-only, already
covered (`test_prepare_next_turn_can_override_system_prompt_run_locally`,
`test_a_turn_stopping_listener_failure_settles_gracefully`, and the `terminate` tests in
`test_terminate.py`/`test_run_entry_points.py`). Item 5 (`error_message` persists/clears) is
Python-test-only (`test_a_pre_step_listener_failure_settles_gracefully` and friends prove
persistence through a settled failure; clearing at next-run-start is implicit in every subsequent
successful `prompt()`/`continue_()` test passing with a clean transcript). Item 6 (no double-drain)
and item 7 (follow-up consumed only when otherwise stopping) are both language-test-covered
(`test_continue_does_not_double_drain_steering_after_pre_drain`; mid-run continuation itself, tested
throughout `test_run_entry_points.py` and `test_provenance.py`). Item 10 (multiple turns, one run
bracket) was already closed in PASS 1 (`tool-round-trip.yaml`,
`projected-execution-ends-follow-completion-order.yaml`).

## RED → GREEN (this pass)

- `prompt()`/`continue_()` and all their rejection paths: each new test failed with
  `AttributeError` (`AgentLoop` had no such method) before implementation, passed after.
- Mid-run follow-up continuation: `test_one_at_a_time_accumulates_causes_onto_the_same_run` and
  `origin-survives-one-at-a-time.yaml` both failed against the pre-restructure driver (asserting two
  separate runs, as PASS 1 left it) before being corrected to assert one run with accumulated
  causes, matching the new, verified-correct behavior.
- Terminate no longer skips dispatch:
  `test_terminate_is_not_overridable_even_though_the_decision_still_fires` and
  `test_the_event_is_still_dispatched_when_nothing_is_owed` both failed (`asked == []` was the old,
  now-wrong assertion) against the pre-fix driver before being corrected.
- `handleRunFailure` narrowness: `test_an_unresolvable_model_still_raises_uncaught` was written
  against an intentionally-too-broad first implementation (a bare `except Exception` around the
  whole run body) and failed by observing the model error silently absorbed instead of raised --
  caught before this pass ever reached a green state, fixed by narrowing to
  `_LoopCallbackFailure` at the three specific dispatch call sites.
- `pending_tool_calls`/`streaming_message` coverage: each new branch (temporary listener
  subscription, partial-text accumulation, defensive-guard path, `_RunSnapshot.apply()`'s
  model/thinking_level branches) was driven to 100% coverage by dedicated tests, not left as an
  untested code path.

## Quality gates (fresh, this pass)

```text
full pytest (coverage enabled):     1003 passed, 19 xfailed, 0 failed, 100.00% coverage
                                     (was 980 at the start of this pass)
ruff check .:                        All checks passed
mypy (configured scope + typing fixtures): Success, no issues found in 59 source files
schema validation:                   185 passed (was 179 at the start of this pass; +6: two new
                                      `continue`/`expect_agent_end_messages` scenario validations
                                      plus their well-formedness checks)
conformance/ (full):                 all passing
manifest parse + unique-ID audit:    75 / 75 unique (unchanged -- no new rows, seven existing rows
                                      corrected in place)
```

## Contract-quality check (this pass's own additions)

```text
Does terminate skip prepareNextTurn/shouldStopAfterTurn/steering?         NO (was YES before this
                                                                             pass -- corrected)
Does a run-local prepareNextTurn override ever persist to AgentInstance?   NO
Does mid-run follow-up continue the same run or start a new one?          SAME run (was a new run
                                                                             before this pass --
                                                                             corrected)
Does handleRunFailure catch a model/provider failure it should not?        NO (regression-tested)
Is error_message cleared at the failing run's own agent_end?               NO -- only at next run
                                                                             start or reset, matching
                                                                             pi exactly
Duplicate state authority (pending_tool_calls vs. Layer-06's own tracking)? NO -- add/remove through
                                                                             existing tools/execution-
                                                                             start/end events, not a
                                                                             second tracking mechanism
Contract quality (this pass's own scope)                                   PASS
```

## Active findings (after this pass)

```text
PI_PARITY_DEFECT              none
CONTRACT_ASSURANCE_DEFECT     none -- all ten AG-001..AG-010 rows now carry accurate dispositions
                               with real evidence (or an explicit, correct deferral for AG-007)
PI_BEHAVIOR_UNCERTAIN         none active (the two PASS-1 candidates remain dispositioned
                               non-blocking; no new candidates raised this pass)
PARITY_CONSTRAINED_RISK       none blocking
```

One disclosed, intentional simplification remains, not classified as a defect: `streaming_message`
content fidelity is text-only (see above) -- the observable contract this layer certifies (non-
`None`/`None` transition timing) is exact; only mid-stream thinking/tool-call content reconstruction
is not attempted, and would require new Layer-02/04-adjacent capability this narrow pass does not
add.

## Verdict

```text
Python Layer 08     CERTIFIED (self-certified; pending independent Rust contract review)
Rust Layer 08         NOT_IMPLEMENTED
shared Layer-08 contract   READY FOR INDEPENDENT RUST CONTRACT REVIEW
Layer 08 cross-language     NOT CLOSED
Layer 09                     NOT STARTED
```

## Next action (superseded -- see PASS 3 below)

Mark PRs #13/#3 Ready for Review (from Draft) at their current heads, update coordination issue #12
(`STATUS: RUST_CONTRACT_REVIEW`, `NEXT_OWNER: Codex`), and stop. Do not merge the shared/Python
PRs. Do not implement Rust. Do not start Layer 09.

# PASS 3 — remediation for the independent Rust contract rejection (L08-R001..R008)

## Rejection reference

The independent Rust review of the PASS-2 candidate (code PR #13 @ `45a7e039233e262eabb7821c1aeb
713024ac3bda`, docs PR #3 @ `fe854a6f583359512cfb538a628ba5e3a6811a47`) **REJECTED** it
(`minion-agent-docs#4` @ `88a6aa6c1c1994026001c60045d4c55c00331a52`, branch
`review/08-rust-contract`). Full AG-001..AG-010 review ledger: AG-001/003/005/007 PASS; AG-002 FAIL
(`L08-R006`); AG-004 FAIL (`L08-R001`, `L08-R004`); AG-006 FAIL (`L08-R007`); AG-008 FAIL
(`L08-R003`); AG-009 FAIL (`L08-R002`); AG-010 FAIL (`L08-R002`). Eight blocking findings total.
This pass treats all eight as blocking until independently reproduced against pinned Pi and
disposed; none of PASS 2's own self-certification claims are trusted without re-verification. Prior
Rust approval does not exist for this or any later candidate SHA -- the rejection at `88a6aa6`
applies only to the superseded PASS-2 candidate; a full independent re-review of this PASS-3
candidate is required before any Layer-08 certification claim stands.

The rejected review evidence PR (#4) is not modified or overwritten by this pass; it remains the
immutable record of what PASS 2 actually was and why it was rejected.

## Findings, reproduced against pinned Pi and remediated

### L08-R001 — incomplete run snapshot and truncated `prepareNextTurn`

**Review finding:** PASS 2's `_RunSnapshot` carried only `{system_prompt, model, thinking_level}`,
and its `RunConfigUpdate` could replace only `system_prompt`. Pinned Pi's own
`Agent.createContextSnapshot()` snapshots the WHOLE `AgentContext{systemPrompt, messages, tools}`
at run start, and `AgentLoopTurnUpdate.context: AgentContext` (`prepareNextTurn`'s return value)
replaces that whole object, never one field.

**Pi reproduction:** confirmed directly against source. `Agent.createContextSnapshot()`
(agent.ts:437-441): `{systemPrompt: this._state.systemPrompt, messages: this._state.messages.slice(),
tools: this._state.tools.slice()}` -- a shallow top-level-array copy, not a deep clone.
`AgentLoopTurnUpdate` (types.ts:138-145): `{context?: AgentContext, model?: Model<any>,
thinkingLevel?: ThinkingLevel}`. `runLoop`'s own mutation (agent-loop.ts:226-238):
`currentContext = nextTurnSnapshot.context ?? currentContext` (whole-object swap via `??`, never a
per-field merge); `model`/`reasoning` independently optional, with the already-certified `AG-014`
`"off"`-vs-`undefined` special case.

**Classification:** `PI_PARITY_DEFECT` (the truncated snapshot/update was an observable behavior
gap, not merely an evidence gap).

**Remediation:** new `RunContext{system_prompt, messages: list[Message], tools:
tuple[ToolDefinition, ...]}` / `RunConfig{model, thinking_level}` (`agent/decisions.py`), replacing
the old three-field `_RunSnapshot`. `RunConfigUpdate.context: RunContext | None` now replaces the
whole `RunContext` when set; `model`/`thinking_level` remain independent per-field replacements.
`_execute_run` snapshots both once at run start from `self.instance.system_prompt`,
`derive_messages(self.instance.log)`, and `self.tools.visible_from(self.instance.scope)` -- never
re-read after that point. `_run_step`, `_should_stop`, and `_prepare_next_turn` all take
`context`/`config` as explicit parameters, matching pinned Pi's own `ShouldStopAfterTurnContext`/
`PrepareNextTurnContext` shape (`message`, `tool_results`, `context`, `new_messages`) exactly.

**RED evidence:** the PASS-2 candidate's own `RunConfigUpdate` had no `context` field at all --
`test_prepare_next_turn_can_replace_the_whole_context` could not even be expressed against it.

**GREEN evidence:** `test_run_start_snapshot_ignores_a_later_caller_config_change`,
`test_run_start_snapshot_ignores_session_changes_from_outside_the_run`,
`test_prepare_next_turn_can_replace_the_whole_context`,
`test_prepare_next_turn_can_replace_model_and_thinking_level`,
`test_prepare_next_turn_context_replacement_does_not_persist_to_the_next_run`,
`test_should_stop_and_prepare_next_turn_receive_pis_full_context`.

**Spec/manifest changes:** `AG-004` rewritten (see L08-R004 below, same row). `AG-002`'s own
`python:` field updated to name `_run_inner` accurately.

**Disposition:** resolved. `AG-004`: adopted.

### L08-R002 — narrow, hand-picked failure boundary instead of pinned Pi's real `handleRunFailure`

**Review finding:** PASS 2's `_LoopCallbackFailure` only wrapped three listener dispatch sites
(`AGENT_PRE_STEP`/`AGENT_TURN_STOPPING`/`AGENT_PREPARE_NEXT_TURN`), narrower than pinned Pi's real
boundary (`runWithLifecycle` wraps the WHOLE run executor). PASS 2 also inserted a synthetic
`turn_start` before the failure's `turn_end`/`agent_end`, which pinned Pi never emits, and its
`agent_end.messages` used the normal run-scoped accumulator rather than pinned Pi's own
`[failureMessage]`-only fallback.

**Pi reproduction:** confirmed against source. `handleRunFailure`'s bare sequence:
`message_start(failure)`, `message_end(failure)`, `turn_end(failure, [])` with no preceding
`turn_start`, `agent_end(messages=[failure])`. Distinct from a represented `error`/`aborted`
assistant message reaching its OWN turn normally (agent-loop.ts:196-200, uses the run's own
`newMessages` accumulator) -- two different mechanisms (see `L08-R008` below), not one.

**Classification:** `PI_PARITY_DEFECT`.

**Remediation:** `_execute_run`'s catch boundary widened to `try`/`except Exception` around the
whole `_run_inner` call, with `UnknownModelError` explicitly excluded (re-raised uncaught -- pinned
Pi resolves a model eagerly, before a stream is returned, so an unresolvable one is a caller/config
bug, not a run-executor failure). `_settle_run_failure` no longer appends a synthetic `turn_start`;
it appends only `ASSISTANT_MESSAGE` + `TURN_END` with an explicit `{"message": ...}` override.
`_execute_run` threads the returned failure message into `AGENT_END`'s own payload as an explicit
`{"messages": [...]}` override. `agent/projection.py`'s `project()` was extended to honor both
overrides directly (`if "message"/"messages" in entry.data: ... else: <normal accumulator>`) rather
than inventing a synthetic `turn_start` pinned Pi never emits -- fixing the projection, not Pi's own
event trace, per this pass's own explicit instruction. `_LoopCallbackFailure` is retained only as an
unused historical marker; nothing raises it.

**RED evidence:** `test_a_pre_step_listener_failure_settles_gracefully`'s own assertion
(`EventKind.TURN_START not in kinds`) failed once `TURN_START`'s correct L08-R006 placement (before
the initial claim) meant a pre-step failure legitimately has one already logged -- this was itself
a test-authoring correction, not a code regression (a `TURN_START` a run's own PRIOR, genuine
progress already logged is fine and expected; only one `_settle_run_failure` itself invents is the
defect). `test_failure_agent_end_messages_is_only_the_failure_message` failed against the
unremediated code (`AGENT_END` never carried a `"messages"` override, so `project()` fell back to
whatever `run_messages` held).

**GREEN evidence:** `test_a_pre_step_listener_failure_settles_gracefully` (exact-sequence
assertion), `test_failure_agent_end_messages_is_only_the_failure_message`,
`test_a_turn_stopping_listener_failure_settles_gracefully`,
`test_a_prepare_next_turn_listener_failure_settles_gracefully`,
`test_a_post_turn_callback_failure_settles_gracefully`,
`test_an_unresolvable_model_still_raises_uncaught`.

**Spec/manifest changes:** `AG-009`, `AG-010` rewritten.

**Disposition:** resolved. `AG-009`, `AG-010`: adopted.

### L08-R003 — `streaming_message`/canonical scenarios lost thinking/tool-call partial content

**Review finding:** `streaming_message` was reconstructed as accumulated text only, when the
already-certified Layer-02/04 `StreamChunk` carries a complete `partial: AssistantMessage` on every
variant. Canonical scenarios also encoded `message_update -> message_start` (reversed) for the
assistant reply's own streaming lifecycle.

**Pi reproduction:** `stream.py`'s own module docstring, confirmed against the certified type:
"every chunk carries `partial`, the message as assembled so far." `streamAssistantResponse`
(agent-loop.ts:281-372): `"start"` -> `message_start`; `"text_start"/.../"toolcall_end"` -> ALL map
to `message_update` carrying the full shallow-copied partial, not a delta string; `"done"/"error"`
-> `message_end` always, `message_start` only defensively if `!addedPartial`.

**Classification:** `PI_PARITY_DEFECT` (content fidelity) + `CONTRACT_ASSURANCE_DEFECT` (canonical
ordering).

**Remediation:** `_run_step`'s `log_chunk` closure sets `self.instance.streaming_message =
chunk.partial` directly from every applicable chunk variant (text/thinking/tool-call
start/delta/end), with no independent delta-accumulation attempted. New `EventKind.
ASSISTANT_STREAM_START` log entry (the stream's own `"start"` chunk) opens the reply's
`MessageStart`; `ASSISTANT_MESSAGE`'s own `MessageStart` is suppressed when that already opened one
(`stream_open` flag in `project()`), matching pinned Pi's `!addedPartial` fallback exactly. Six
canonical scenarios corrected in place (`turn-lifecycle`, `causes-preserved-under-claim-all`,
`premature-eof-synthesizes-error-terminal`, `projected-execution-ends-follow-completion-order`,
`public-stream-fuses-after-first-terminal`, `tool-round-trip`) -- audited every Layer-08 canonical
scenario asserting assistant streaming lifecycle, not only the two the review named.

**RED evidence:** the certified `MockAdapter` only emits text deltas, so a test-local-only
`_RichStreamAdapter` (implementing the same informal `Adapter` protocol, not touching certified
adapter code) was needed to exercise thinking/tool-call partial fidelity at all -- before this pass
there was no way to even express that evidence.

**GREEN evidence:** `test_streaming_message_carries_the_full_partial_for_text`,
`test_streaming_message_carries_the_full_partial_for_thinking`,
`test_streaming_message_carries_the_full_partial_for_tool_calls`,
`test_streaming_message_clears_after_the_message_finalizes`,
`test_message_start_precedes_message_update_for_a_streamed_reply`, plus all seven corrected
canonical scenarios and the two focused unit tests in `tests/agent/test_projection.py`.

**Spec/manifest changes:** `AG-008` rewritten (the "text-only, intentional divergence" claim
removed as false).

**Disposition:** resolved. `AG-008`: adopted.

### L08-R004 — AG-004 contradicted the current candidate with stale PASS-1 narrative

**Review finding:** `AG-004`'s rule text still said `prepareNextTurn` was "NOT implemented at all,"
directly contradicting `AGENT_PREPARE_NEXT_TURN`'s real (if truncated) PASS-2 implementation.

**Classification:** `CONTRACT_ASSURANCE_DEFECT`.

**Remediation:** `AG-004` rewritten as one coherent current rule describing the actual adopted
behavior after `L08-R001`'s remediation: `turn_end -> prepareNextTurn (whole-context replacement) ->
shouldStopAfterTurn -> steering poll -> follow-up only if otherwise stopping`, with real,
non-placeholder evidence citations. The represented-error/aborted carve-out (`AG-021`) is cross-
referenced, not folded in, since it is a distinct row (`L08-R008`). A repo-wide grep for
`prepareNextTurn`/`not implemented`/`tracked gap`-flavored stale assertions against the current
candidate found no other contradictions once `AG-008`/`AG-009` were also corrected under their own
findings above.

**Disposition:** resolved. `AG-004`: adopted (see `L08-R001` above for the same row's fuller text).

### L08-R005 — `max_steps` risked an unapproved observable Pi divergence

**Review finding:** PASS 2's `max_steps` check ran BEFORE `prepareNextTurn`/`shouldStopAfterTurn`/
the steering poll for the turn that hit the cap, which would skip pinned Pi's own unconditional
post-turn ordering for that turn -- an observable divergence from `AG-004` that was never disclosed
or approved as intentional.

**Pi reproduction:** pinned Layer 08 has no `max_steps`-equivalent stop rule at all; this is
entirely a Minion host/pump safety extension with no Pi counterpart to diverge from or converge on.

**Classification:** `PARITY_CONSTRAINED_RISK` (an unapproved observable divergence risk, not yet a
confirmed defect since the review asked for resolution before merge, not after).

**Remediation:** a parity-neutral placement was possible and is what this pass adopts --
`_run_inner`'s `max_steps` check moved to AFTER `prepareNextTurn`/`shouldStopAfterTurn`/the steering
poll have already run unconditionally for the turn that reached the cap. It now gates only whether
a FURTHER turn is attempted, never skips pinned Pi's own post-turn ordering for a turn that already
happened. No owner escalation was needed since a parity-neutral arrangement existed. New manifest
row `AG-020` records `max_steps` explicitly as a Minion-only architectural/host extension, disposed
`intentional divergence` (not `adopted`, since there is no Pi rule to have adopted).

**Disposition:** resolved without escalation. `AG-020` (new row): intentional divergence.

### L08-R006 — initial steering poll claimed before `TURN_START` was logged

**Review finding:** the first turn's steering claim happened before `TURN_START` was appended,
observably backwards from pinned Pi's own emission order.

**Pi reproduction:** `runAgentLoop` (agent-loop.ts:95-118) emits `agent_start`, `turn_start`, then
the initial prompt messages' own lifecycle, THEN calls `runLoop`, whose own FIRST statement is the
initial steering poll -- strictly a post-`turn_start` event, confirmed directly.

**Classification:** `PI_PARITY_DEFECT`.

**Remediation:** `_run_inner` now appends `TURN_START` unconditionally BEFORE the initial claim/
`_pre_step` dispatch; `_run_step`'s own `open_turn=False` flag for that first turn prevents a
duplicate append. Continuation's own no-double-drain special case (`skip_initial_steering_poll`)
preserved unchanged.

**RED/GREEN evidence:** offline projection cannot prove this (inbox claims are not themselves
projected events) -- discriminating evidence is listener-based: an `AGENT_PRE_STEP` listener
inspects live `instance.log.events` for `TURN_START` at the moment the initial claim reaches it
(`test_the_initial_steering_claim_happens_after_turn_start`).

**Spec/manifest changes:** `AG-002` rewritten.

**Disposition:** resolved. `AG-002`: adopted.

### L08-R007 — no `prompt(text, images?)` convenience surface

**Review finding:** pinned Pi's `Agent.prompt()` accepts a plain string (optionally with images) as
a convenience overload; Minion's `AgentLoop.prompt()` only accepted the typed `Message |
tuple[Message, ...]` boundary.

**Classification:** `PI_PARITY_DEFECT`.

**Remediation:** `prompt()` gained `images: tuple[ImageBlock, ...] = ()` and a `str` branch that
normalizes into exactly one `UserMessage` whose content is `(TextBlock(text=message), *images)` --
text first, then the supplied images, in order, matching pinned Pi's own `[{type:"text",...},
...images]` construction. The typed boundary is unchanged and unnarrowed; both forms coexist.

**GREEN evidence:** `test_prompt_accepts_a_plain_string`,
`test_prompt_string_with_one_image_orders_text_then_image`,
`test_prompt_string_with_multiple_images_preserves_order`,
`test_prompt_accepts_a_tuple_of_typed_messages_unchanged` (renamed from
`test_prompt_accepts_a_tuple_of_messages`, whose name the manifest's own `AG-006` row cited stale
until corrected this pass).

**Spec/manifest changes:** `AG-006` rewritten.

**Disposition:** resolved. `AG-006`: adopted.

### L08-R008 — represented assistant error/aborted ran the full post-turn sequence

**Review finding:** PASS 2 collapsed a represented `error`/`aborted` assistant message into the same
branch as an ordinary no-more-tool-calls stop, running `prepareNextTurn`/`shouldStopAfterTurn`/the
steering and follow-up poll regardless of `stop_reason`.

**Pi reproduction:** confirmed directly (agent-loop.ts:196-200), immediately after
`streamAssistantResponse` returns: `if (stopReason === "error" || stopReason === "aborted")` emits
that turn's own `turn_end` with empty `toolResults` and returns immediately -- no tool calls
inspected/executed, none of the four post-turn hooks/queues touched.

**Classification:** `PI_PARITY_DEFECT`.

**Remediation:** new `_StepResult.terminal` flag, set by `_run_step` when `reply.stop_reason in
(ERROR, ABORTED)`; `_run_inner` returns immediately on `terminal`, before ever calling
`_prepare_next_turn`/`_should_stop`/claiming steering or follow-up. Uses the run's own normal
`new_messages` accumulator for `agent_end.messages` (agent-loop.ts:199's own `newMessages`) --
distinct from `L08-R002`'s `handleRunFailure` override, an unrelated mechanism for an unexpected
THROWN exception, never for a normally-produced represented-error message.

**RED evidence:** an initial test draft queued the steering message to prove non-consumption BEFORE
`run_until_idle()` started, which the run's own unconditional INITIAL poll (`AG-002`, unrelated to
this finding) claimed regardless of the turn's later outcome -- a test-design flaw, not a code
defect, corrected by queuing from within an `AGENT_PRE_STEP` listener dispatched AFTER that initial
poll has already run.

**GREEN evidence:** `test_represented_error_skips_prepare_stop_steering_and_follow_up`,
`test_represented_aborted_skips_prepare_stop_steering_and_follow_up`,
`test_represented_error_agent_end_messages_uses_the_normal_accumulator`.

**Spec/manifest changes:** new row `AG-021`.

**Disposition:** resolved. `AG-021` (new row): adopted.

## Full re-audit after remediation

The whole Layer-08 run state machine was reconstructed from pinned Pi and re-verified with no
interaction bug introduced across all eight fixes together: fresh prompt, `prompt(text/images)`,
plain continue, assistant-last continue with steering/follow-up pre-drain, tool-driven/steering-
driven/follow-up-driven next turn, tool `terminate`, assistant `error`/`aborted`, an unexpected
run-executor failure, `prepareNextTurn` whole-context replacement, multiple independent runs,
runtime-state transitions, and `agent_end.messages` across every path above -- each checked for
event order, the exact context/messages sent to the provider, queue consumption, invocation-local
messages, and mutable-vs-run-local state persistence. No regression surfaced; the full Python test
suite (1000+ tests), 100% coverage, and full canonical conformance all pass together against the
single combined candidate (see quality gates below).

## Canonical contract cleanup

19 agent canonical scenarios remain `TO_BE_FILLED_FROM_PINNED_PI_BEHAVIOR` placeholders. None is
cited as evidence by any manifest row above (each row cites real, filled scenarios or focused
Python tests instead), each placeholder's deferred purpose is unchanged from prior passes, and no
manifest row depends on an unfilled placeholder for its own disposition.

## Quality gates (fresh, this pass)

```text
pytest (full suite):                 all passing, 0 failures
coverage (certified src packages):   100% (agent, agent_loop, llm, runtime, session, telemetry,
                                      tools)
ruff check:                          clean
ruff format --check:                 clean (files touched this pass)
mypy (configured scope, src only):   clean, 0 errors
schema validation:                   all passing (unchanged from PASS 2's own 185)
conformance/ (full):                 all passing, including the 7 scenarios corrected this pass
manifest parse + unique-ID audit:    77 / 77 unique (+2 new rows: AG-020, AG-021; six existing rows
                                      corrected in place: AG-002, AG-004, AG-006, AG-008, AG-009,
                                      AG-010)
```

## Active findings (after this pass)

```text
PI_PARITY_DEFECT              none -- all eight L08-R001..R008 findings resolved
CONTRACT_ASSURANCE_DEFECT     none -- AG-004's stale narrative corrected; no other contradictory
                               current-state claims found
PI_BEHAVIOR_UNCERTAIN         none active
PARITY_CONSTRAINED_RISK       none -- max_steps resolved without an unapproved divergence
unapproved intentional divergence   none -- AG-020 (max_steps) is disposed explicitly, not silently
                               preserved
```

## Verdict

```text
Python Layer 08     CERTIFIED (self-certified; pending independent Rust contract review)
Rust Layer 08         NOT_IMPLEMENTED
shared Layer-08 contract   READY FOR INDEPENDENT RUST CONTRACT REVIEW (remediated candidate; no
                             prior Rust approval carries forward from the rejected PASS-2 candidate)
Layer 08 cross-language     NOT CLOSED
Layer 09                     NOT STARTED
```

## Next action (superseded -- see PASS 4 below)

Push this pass's commits to the existing `layer/08-python-shared` branches (both repos); update PR
#13/#3 bodies with the PASS-3 remediation summary, new head SHAs, and L08-R001..R008 disposition;
mark both Ready for Review once the candidate gate above is satisfied. Update coordination issue
#12 to `STATUS: RUST_CONTRACT_REVIEW`, `CODE PR #13 @ <new SHA>`, `DOCS PR #3 @ <new SHA>`,
`NEXT_OWNER: Codex`, `NEXT_ACTION: complete independent re-review against the new candidate SHAs;
the prior rejection (88a6aa6) applies only to the superseded PASS-2 candidate`. Then stop. Do not
merge PR #13, #3, or review-evidence PR #4. Do not implement Rust. Do not start Layer 09.

# PASS 4 — remediation for the independent Rust re-review rejection (L08-R002, R004, R005, R006, R009)

## Re-review reference

The independent Rust re-review of the PASS-3 candidate (code PR #13 @ `d8caf5c1f299063111a5b47fec3df
45f9f9d50fc`, docs PR #3 @ `580fb279ec8703528632b9861bbc80b13d0f5171`) **REJECTED** it
(`minion-agent-docs#5` @ `a64b78ad2507b142ca7cda911b8968aa61af6a20`, branch
`review/08-rust-contract-rereview`). Four findings from the PASS-2 rejection CLOSED: `L08-R001`
(run snapshot/whole-context replacement), `L08-R003` (streaming partial fidelity, implementation and
evidence -- though the normative spec contradicting it was itself `L08-R004`), `L08-R007`
(`prompt(text, images?)`), `L08-R008` (represented error/aborted terminal). Five findings STILL
OPEN or NEW: `L08-R002` (recovery is projected, not listener-dispatched -- `CONTRACT_ASSURANCE_
DEFECT`), `L08-R004` (`spec/agent.md` never updated, contradicts manifest/implementation --
`CONTRACT_ASSURANCE_DEFECT`), `L08-R005` (`max_steps` still truncates the Pi-equivalent path,
mislabeled parity-neutral -- `PI_PARITY_DEFECT`), `L08-R006` (initial steering still claimed before
the prompt's own lifecycle, only after `turn_start` -- `PI_PARITY_DEFECT`), `L08-R009` (new: the
pre-existing local `cancel()` latch has no coherent Layer-08/09 manifest disposition --
`CONTRACT_ASSURANCE_DEFECT`). This pass treats all five as blocking until independently reproduced
against pinned Pi and remediated; the four closed findings are re-verified for regression only (not
re-litigated), per this pass's own explicit instruction not to reopen them unless necessarily
affected by the PASS-4 work itself (initial-turn admission restructuring, `L08-R006`, necessarily
touches the same code path `L08-R001`/`L08-R008` depend on, so both were re-verified with focused
regression tests -- see below).

Prior Rust approval does not exist for this or any later candidate SHA -- the rejection at
`a64b78a` applies only to the superseded PASS-3 candidate. The rejected review evidence PRs (#4,
#5) are not modified or overwritten by this pass; they remain the immutable record of what PASS 2
and PASS 3 actually were and why each was rejected.

## Findings, reproduced against pinned Pi and remediated

### L08-R002 — recovery must use the same listener-bearing seam as ordinary progress

**Re-review finding:** PASS 3 corrected the visible failure trace (catch-boundary width, no
synthetic `turn_start`, the `agent_end.messages` override) but still produced it through raw
`SessionLog.append` calls with no live listener dispatch at all. Pinned Pi's `handleRunFailure`
delivers its four-event sequence through `processEvents`, the SAME seam ordinary lifecycle events
use -- a listener can observe and, by throwing, interrupt the recovery sequence itself. Two
independent Rust implementations could reasonably choose different recovery-listener semantics from
a written contract that never specified this.

**Pi reproduction:** confirmed directly against source (agent.ts:511-591). `processEvents(event)`
first reduces `Agent._state` for the event, then awaits every subscribed listener in registration
order with no catch around the loop -- a throw aborts the remaining listeners for that event and
propagates out of `processEvents` itself. `handleRunFailure` awaits four such calls sequentially
(`message_start(failure)`, `message_end(failure)`, `turn_end(failure, [])`,
`agent_end(messages=[failure])`); a throw at any one aborts the rest and propagates all the way out
to the caller of `prompt()`/`continue()` (no further catch around `handleRunFailure`'s own call
site), while `finally { finishRun() }` still settles status.

**Architectural question asked first, per this pass's own explicit instruction:** did Minion have
ONE production seam corresponding to `processEvents`, where an Agent event both updates state and
awaits live listeners? Answer: NO. `agent/projection.py::project()` only ever reconstructs pi's
`AgentEvent` vocabulary OFFLINE, by walking a completed log -- it cannot dispatch or interrupt
anything live. This is the genuine Layer-08 contract-assurance defect: a missing common Agent
lifecycle event seam, not a recovery-only gap. Per this pass's own instruction, the fix was to
introduce the minimal coherent seam used by BOTH normal and recovery lifecycle, not a recovery-only
special dispatcher.

**Classification:** `CONTRACT_ASSURANCE_DEFECT`.

**Remediation:** new `AGENT_LIFECYCLE_EVENT` (`agent/events.py`, `SERIAL` dispatch mode).
`EventBus.serial`'s existing semantics -- sequential await, no catch around the loop, propagates a
listener's exception immediately -- already match pinned Pi's raw listener loop exactly; no new
dispatch primitive was needed. New `AgentLoop._dispatch_agent_event(event)` helper dispatches one
`agent/projection.py` `AgentEvent` payload through it. New `AgentLoop._admit_messages(messages,
context, new_messages)` helper centralizes every message-admission point (previously duplicated
inline in `_run_step`) to log, dispatch (`MessageStart` then `MessageEnd`), and accumulate each
message the same way -- used by the prompt, steering, tool-result-triggered continuation, and
follow-up admission points alike. `_run_step` now also dispatches `TurnStart`/`TurnEnd` live, and
`_execute_run` dispatches `AgentStart` and the ordinary-path `AgentEnd`. `_settle_run_failure`
(now `async`) dispatches its own four-event sequence through the SAME seam, in the same order, and
lets a thrown listener propagate uncaught -- proven by four dedicated regressions, one per recovery
event, each also confirming exactly which log entries the aborted sequence still durably recorded
(the "reduce" step precedes the dispatch that then throws) and that status still settles via
`_run_wrapped`'s own `finally`.

**Scope boundary, disclosed rather than silently narrowed:** the assistant reply's OWN streamed
message lifecycle is NOT dispatched through this seam -- the certified Layer-02/04 `collect()`
accepts only a synchronous `on_chunk` callback, so a chunk-level listener has nothing to `await`.
This is an existing, certified-layer constraint this pass does not reopen, and does not affect
`handleRunFailure` fidelity (the failure's own message lifecycle is synthesized directly in async
code) or `streaming_message` content fidelity (`L08-R003`, unrelated, unaffected). Documented
explicitly in `AGENT_LIFECYCLE_EVENT`'s own docstring and in `spec/agent.md`.

**RED evidence:** before this pass, no live dispatch existed at all -- a listener registered on any
would-be "lifecycle" hook simply never fired during a run; only offline `project()` after the fact
could reconstruct the trace. The four recovery-interruption tests could not even be expressed
against the PASS-3 candidate.

**GREEN evidence:** `test_a_run_executor_failure_recovers_through_the_live_lifecycle_event_seam`,
`test_a_post_turn_callback_failure_recovers_through_the_live_seam`,
`test_failure_message_start_listener_failure_interrupts_recovery`,
`test_failure_message_end_listener_failure_interrupts_recovery`,
`test_failure_turn_end_listener_failure_interrupts_recovery`,
`test_failure_agent_end_listener_failure_interrupts_recovery`.

**Spec/manifest changes:** `spec/agent.md`'s Layer-08 section rewritten (`L08-R004`, same pass);
`AG-009` manifest row rewritten.

**Disposition:** resolved. `AG-009`: adopted.

### L08-R004 — `spec/agent.md` never updated to match the actual contract

**Re-review finding:** manifest `AG-004` and the implementation were both correct, but
`spec/agent.md`'s Layer-08 section still described PASS-2 behavior: `streaming_message` called
text-only with a false claim that the certified stream exposes only raw deltas; `handleRunFailure`
described as wrapping only three listener sites with a synthetic matched `turn_start`;
`prepareNextTurn` described as system_prompt-only. A candidate can pass every test and still fail
review if the NORMATIVE document a second implementation is meant to trust contradicts what the
code and manifest actually do.

**Classification:** `CONTRACT_ASSURANCE_DEFECT`.

**Remediation:** `spec/agent.md`'s entire Layer-08 section rewritten as one coherent current
statement (this file), removing every historical PASS-1/PASS-2/PASS-3 evolutionary narrative from
the normative text -- that history now lives here, in assurance, exclusively. A full consistency
pass was run across pinned Pi, `spec/agent.md`, the manifest, canonical conformance, and the Python
implementation together (not merely the lines the review named): `streaming_message`'s false
text-only claim removed; `handleRunFailure`'s narrow-boundary/synthetic-turn-start claims removed
and replaced with the actual live-seam description (`L08-R002`, above); `prepareNextTurn`'s
system-prompt-only claim removed and replaced with the whole-context description; the stale
`max_steps` cap description removed entirely (`L08-R005`, below); new sections added for the staged
initial-turn admission (`L08-R006`, below) and `request_boundary_stop()` (`L08-R009`, below).

**Disposition:** resolved. `AG-004`'s own manifest text needed no semantic change (the re-review
found it already correct) -- only a note added disclosing what was actually defective (the spec,
not this row) and confirming the consistency pass. `AG-004`: adopted, unchanged.

### L08-R005 — `max_steps` removed entirely from the Pi-equivalent run seam

**Re-review finding:** PASS 3's repositioning (checking the cap after `prepareNextTurn`/
`shouldStopAfterTurn`/the steering poll) fixed the INTRA-turn ordering defect PASS 2 introduced, but
not the CROSS-run observable divergence: with a tool result requiring another turn, the cap still
returned `agent_end(reason="max_steps")` where pinned Pi would have started the next provider
request. `AG-020`'s own `disposition: intentional divergence` while its prose claimed no observable
divergence existed was internally incoherent, and merely adding the row was never governance
approval for the divergence itself.

**Classification:** `PI_PARITY_DEFECT`.

**Explicit instruction followed:** do not request owner approval for the divergence; the project
default is Pi fidelity, and no product requirement demonstrated a need to preserve this specific
observable difference. `max_steps` must not alter the behavior of a Pi-equivalent `prompt()`/
`continue()` run.

**Remediation:** removed entirely, not deprecated-in-place. `AgentDefinition.max_steps` (the field),
the `_run_inner` step-counter check, the conformance schema's `config.max_steps` property, and the
canonical fixture that used to exercise the cap are all deleted -- the field had no coherent
remaining role once the check was gone, and keeping an inert field/schema property would itself be
exactly the "dead semantics" this pass was asked not to preserve. No replacement host-level cap was
introduced: `run_until_idle()` cannot replicate the old per-invocation semantics even if it wanted
to (no visibility into turns within one already-open `_execute_run`), and no product requirement
currently demonstrates a genuine need for one. Manifest row `AG-020` was REMOVED (not merely
relabeled) -- once the mechanism no longer exists, in either pinned Pi or Minion, there is no
surface left for a manifest row to map; keeping a row for a fully-removed mechanism would itself
become stale historical narrative mixed into current normative content, which this pass was asked
to eliminate, not reproduce for a different row.

**RED evidence:** `max-steps-bounds-a-turn.yaml` (the prior canonical fixture) asserted the cap
fired at 2 turns despite the model requesting a third -- the exact shape pinned Pi does not bound.

**GREEN evidence:** the fixture was rewritten (renamed
`no-turn-count-cap-on-pi-equivalent-run.yaml`) to prove the OPPOSITE: 21 tool-driven turns (one more
than the old default cap of 16) all complete normally in one run, with no host-imposed stop.
Focused regression: `test_a_long_tool_loop_is_not_bounded_by_any_turn_count`. Two Python unit tests
whose sole premise was the removed cap (`test_max_steps_bounds_a_runaway_tool_loop`,
`test_continue_cannot_override_max_steps`) were removed as testing a mechanism that no longer
exists, not converted into weaker assertions.

**Spec/manifest changes:** `spec/agent.md`'s Layer-08 section states the absence of any turn-count
cap explicitly; `AG-020` removed.

**Disposition:** resolved without escalation -- a parity-neutral default (removal) was available and
adopted; no owner approval was sought or needed. `AG-020`: removed.

### L08-R006 — initial prompt lifecycle must be complete before the steering claim

**Re-review finding:** PASS 3 only achieved `turn_start -> steering claim`, the WEAKER condition the
original `L08-R006` finding did not actually require. Pinned Pi's real order additionally requires
the initial prompt's own COMPLETE message lifecycle (`message_start` then `message_end`) to be
observable, live, before the steering queue is claimed at all. PASS 3's `_run_inner` appended
`TURN_START`, immediately called `_claim_step_input()`, and only THEN, inside `_run_step`, logged
`entering + claimed_steering` together as one combined batch -- a listener present at claim time saw
`TURN_START` already logged but not the prompt's own lifecycle.

**Pi reproduction:** confirmed directly against source (agent-loop.ts:95-118, 161). `runAgentLoop`
emits `agent_start`, `turn_start`, then the initial prompt messages' own complete lifecycle, and only
then calls `runLoop`, whose own first statement is the initial steering poll.

**Classification:** `PI_PARITY_DEFECT`.

**Remediation:** `_run_inner`'s first-turn handling restructured into two explicit, sequential
admission stages, both using the new `_admit_messages` helper (`L08-R002`, above): (1) a
`PreStepReason.INITIAL` decision governs the caller's own entering prompt ALONE, admitted (logged,
dispatched live, accumulated) immediately; (2) only then is `_claim_step_input()` called, and if
non-empty, a SECOND, independent `PreStepReason.STEERING` decision governs the claimed batch,
admitted the same way. Both stages' messages still feed the SAME first provider request -- pinned
Pi never splits them into separate turns, only their own admission/lifecycle timing is staged.
`_run_step` itself no longer performs message admission at all; every call site (this staged first
turn, steady-state per-turn admission, and follow-up-triggered continuation admission) now admits
before calling it, uniformly.

**RED evidence:** `test_the_initial_steering_claim_happens_after_turn_start` (the PASS-3 evidence)
only asserted `TURN_START in kinds` at claim time -- the weaker condition the re-review named
exactly. Reproducing the re-review's own suggested trace (`agent_start, turn_start, prompt
message_start, prompt message_end, steering claim, steering message_start, steering message_end,
provider request`) against the PASS-3 candidate would have failed at the third element (the
combined batch had not yet been logged/dispatched at claim time).

**GREEN evidence:** `test_the_initial_prompt_lifecycle_precedes_the_steering_claim` -- a
listener-driven trace across both `AGENT_LIFECYCLE_EVENT` (proving the prompt's own `message_start`/
`message_end` fire before the steering-reason claim marker) and the final request (proving both
messages still land in one combined request, never split into separate turns). The prior, weaker
`test_the_initial_steering_claim_happens_after_turn_start` and `continue-steering-no-double-drain`
regression (`test_continue_does_not_double_drain_steering_after_pre_drain`) both still hold
unchanged. New coverage for the second admission stage's own rejection path:
`test_a_rejection_during_the_initial_steering_admission_ends_the_turn`.

**Spec/manifest changes:** `spec/agent.md`'s Layer-08 section gained its own "Initial-turn
admission" section; `AG-002` manifest row rewritten.

**Disposition:** resolved. `AG-002`: adopted.

### L08-R009 — `AgentLoop.cancel()` had no coherent Layer-08/09 disposition

**Re-review finding (new):** `AgentLoop.cancel()` is a public, observable method with real current
effects (ends the run at the next turn boundary), but no manifest row disposed it, `spec/agent.md`
never defined its relationship to `AG-007` (Layer-09's own deferred active cancellation), and an
implementation comment incorrectly pointed to `AG-019` (Layer-07's own unrelated wake signal). Two
independent Rust implementations could reasonably reach different conclusions about whether Layer 08
must implement this latch at all, or what it means.

**Classification:** `CONTRACT_ASSURANCE_DEFECT`.

**Resolution path, per this pass's own explicit framework:** determined whether this method is part
of the intended PUBLIC Agent semantic surface or only an internal Minion driver mechanism. It is
genuinely NOT pinned Pi's own cancellation surface -- pinned Pi''s own name for that concept is
`Agent.abort()` (a different name), and its real job (active provider/tool/hook signal propagation)
is something this method has never attempted and still does not; Layer 07's own already-certified
contract already places that at Layer 09. This is Case B of the re-review's own framework: a
pre-existing, genuinely Minion-internal mechanism, not the Agent cancellation API, that happens to
be reachable through the same driver object.

**Remediation:** renamed `AgentLoop.cancel()` to `AgentLoop.request_boundary_stop()`, and the
internal flag from `_cancelled` to `_boundary_stop_requested`, so neither name implies pi's own
`abort()` semantics. The observable `agent_end` reason changed from `"cancelled"` to
`"boundary_stop"` for the same reason. Behavior is otherwise unchanged from PASS 3: checked only
after the current turn's own post-turn ordering has already run unconditionally, gating only
whether a further turn is attempted; no provider/stream/tool/hook/transport signal is sent. New
manifest row `AG-022` disposes it explicitly, with an explicit cross-reference from `AG-007` so the
two are never conflated.

**GREEN evidence:** `test_boundary_stop_ends_the_turn_at_the_next_boundary`,
`test_a_boundary_stopped_turn_still_records_its_tool_result`,
`test_boundary_stop_clears_so_the_next_turn_runs` (renamed from the PASS-3 `test_cancellation.py`
suite, now `test_boundary_stop.py`, with matching renamed assertions).

**Spec/manifest changes:** `spec/agent.md` gained a `request_boundary_stop()` section, distinct from
and cross-referenced against "Active abort propagation (explicitly out of scope)"; new manifest row
`AG-022`; `AG-007` gained a cross-reference to it.

**Disposition:** resolved. `AG-022` (new row): intentional divergence.

## Regression verification for the four closed findings

PASS-4's own restructuring (staged first-turn admission, the new live-dispatch seam, `max_steps`
removal, the `cancel()` rename) touches central control flow shared with `L08-R001`/`L08-R003`/
`L08-R007`/`L08-R008`. Each was re-verified, not re-litigated:

- `L08-R001` (full `RunContext` snapshot, whole-context replacement, dynamic `added_tool_names`
  visibility): all prior PASS-3 evidence re-run unchanged and passing
  (`test_run_start_snapshot_ignores_a_later_caller_config_change`,
  `test_prepare_next_turn_can_replace_the_whole_context`,
  `test_added_tool_names_already_visible_is_not_duplicated`, and siblings) -- the staged admission
  restructuring changed WHEN messages are admitted, not the snapshot/replacement mechanics
  themselves, which are untouched.
- `L08-R003` (`chunk.partial` full streaming fidelity, `message_start -> message_update* ->
  message_end`): all prior evidence re-run unchanged and passing
  (`test_streaming_message_carries_the_full_partial_for_text/thinking/tool_calls`,
  `test_message_start_precedes_message_update_for_a_streamed_reply`) -- this pass's explicit scope
  boundary (streamed events not on the new live seam) leaves the streaming mechanism itself
  untouched.
- `L08-R007` (`prompt(text, images?)`, typed `Message` input unchanged): all prior evidence re-run
  unchanged and passing; unaffected by admission-timing or failure-seam changes.
- `L08-R008` (represented error/aborted immediate terminal): `_StepResult.terminal`'s own semantics
  are unchanged, but its own PASS-3 evidence needed a genuine mechanism update (not merely a
  re-run): the initial-poll-timing fix this pass made (`L08-R006`) meant queuing steering during the
  INITIAL pre-step dispatch no longer discriminates anything about R008 specifically (that poll now
  admits before the turn ever runs, regardless of outcome) -- the tests were rewritten to queue from
  within a live `AGENT_LIFECYCLE_EVENT` listener watching this turn's own `TurnEnd` instead, which
  correctly proves the STEADY-STATE poll (not the initial one) never fires
  (`test_represented_error_skips_prepare_stop_steering_and_follow_up`,
  `test_represented_aborted_skips_prepare_stop_steering_and_follow_up`, both still green).

No interaction bug surfaced from any of the four re-verifications; the full suite (below) confirms
this across the whole combined candidate, not merely these targeted checks.

## Full Layer-08 semantic reconstruction

The whole run state machine was independently walked against pinned Pi again after remediation:
`prompt(Message)`/`prompt([Message...])`/`prompt(text)`/`prompt(text, images)`; plain continuation;
assistant-last continuation with steering pre-drain, follow-up pre-drain, and neither available;
first-turn prompt-then-steering ordering; tool-driven/steering-driven/follow-up-driven continuation;
`prepareNextTurn` (whole context, model, thinking level); dynamically added tools; `terminate`;
represented `error`; represented `aborted`; an unexpected run-executor failure; failure-listener
interruption at each of the four recovery events; multiple independent runs; streaming state;
pending tool calls; `error_message`; `agent_end.messages` across every path above -- for each,
event order, the exact context/messages sent to the provider, queue consumption, invocation-local
messages, and mutable-vs-run-local state persistence were checked. No `max_steps`-shaped termination
exists anywhere in the Pi-equivalent run path any more.

## Canonical and language-specific evidence

Language-neutral canonical evidence added/changed where the runner can express the rule:
`no-turn-count-cap-on-pi-equivalent-run.yaml` (renamed and rewritten from
`max-steps-bounds-a-turn.yaml`, proving the opposite of what it used to). The initial-turn admission
ordering (`L08-R006`) and recovery-listener interruption (`L08-R002`) both remain explicit
Python-test-only evidence, deliberately: both require live listener dispatch and inbox-claim timing
the canonical runner does not (and should not) simulate -- teaching the runner to fake production
listener/queue semantics merely to get YAML coverage was explicitly out of scope for this pass. If
these listener-driven rules become important enough to express across implementations generally,
that is future conformance-runner enhancement work, not something folded into this pass.

## Quality gates (fresh, this pass)

```text
pytest (full suite):                 all passing, 0 failures
coverage (certified src packages):   100%
ruff check:                          clean
ruff format --check:                 clean (files touched this pass)
mypy (configured scope, src only):   clean, 0 errors
schema validation:                   all passing
conformance/ (full):                 all passing, including the rewritten max-steps-cap regression
manifest parse + unique-ID audit:    77 / 77 unique (AG-020 removed, AG-022 added -- net unchanged;
                                      AG-002/AG-004/AG-009/AG-021 corrected in place; AG-007 gained a
                                      cross-reference)
stale normative-text audit:          spec/agent.md's Layer-08 section rewritten as one coherent
                                      current statement with no historical PASS-1/2/3 narrative mixed
                                      into normative text; grep across spec/reference/design docs
                                      found no other current-state contradiction (`.cancel()`/
                                      `max_steps`/text-only-streaming/three-hand-picked-sites
                                      references remaining are all in dated historical design
                                      documents describing what was true when THEY were written, not
                                      edited -- preserving historical review artifacts per this
                                      project's own rule)
placeholder-evidence audit:          no Layer-08 manifest row cites an unfilled placeholder scenario
                                      as satisfying evidence
```

## Active findings (after this pass)

```text
PI_BEHAVIOR_UNCERTAIN         none
PI_PARITY_DEFECT              none -- L08-R005 (max_steps) and L08-R006 (initial admission order)
                               both resolved
CONTRACT_ASSURANCE_DEFECT     none -- L08-R002 (live recovery seam), L08-R004 (spec staleness), and
                               L08-R009 (cancel disposition) all resolved
unapproved intentional divergence   none -- AG-020 removed rather than left mislabeled; AG-022's own
                               divergence (request_boundary_stop) is explicitly disposed, not silent
Layer-09 implementation       none -- request_boundary_stop() and handleRunFailure both compose
                               correctly with a future Layer-09 implementation without implementing
                               any part of it themselves
```

## Verdict

```text
Python Layer 08     CERTIFIED (self-certified; pending independent Rust contract review)
Rust Layer 08         NOT_IMPLEMENTED
shared Layer-08 contract   READY FOR INDEPENDENT RUST CONTRACT REVIEW (remediated candidate; no
                             prior Rust approval carries forward from either rejected candidate)
Layer 08 cross-language     NOT CLOSED
Layer 09                     NOT STARTED
```

## Workflow-process retrospective notes (this cycle)

Second rejection/remediation cycle for this layer. Captured for later integration into
`process/agent-workflow.md` at Layer-08's own closure retrospective, NOT applied to that file now:

1. Pre-handoff consistency check must compare normative spec, manifest, assurance, conformance, and
   implementation together -- PASS 3 changed four of those five and left `spec/agent.md` stale,
   which is exactly what caused this rejection cycle (`L08-R004`).
2. Any Minion-only feature riding on a Pi-equivalent execution path must answer "can this change an
   observable result relative to pinned Pi?" before being labeled parity-neutral -- `max_steps`
   answered "yes" and was removed instead of relabeled (`L08-R005`).
3. A remediation pass must retest the EXACT discriminating observation the review finding names, not
   a weaker nearby condition that happens to also pass -- PASS 3's own `L08-R006` fix proved
   "after `turn_start`" when pinned Pi's real requirement was "after the complete prompt lifecycle,"
   a materially weaker condition that still let the underlying defect through.
4. Listener-bearing failure/lifecycle semantics require live-dispatch evidence -- projected log
   equality alone (what PASS 3's own `L08-R002` evidence relied on) is insufficient to prove a
   listener seam exists or can be interrupted; this pass's own recovery tests all assert on live
   listener invocation order, never log content alone.

## Next action (superseded -- see PASS 5 below)

Push this pass's commits to the existing `layer/08-python-shared` branches (both repos); update PR
#13/#3 bodies with the PASS-4 remediation summary, new head SHAs, reviewed/rejected predecessor
SHAs, and L08-R002/R004/R005/R006/R009 closure status; mark both Ready for Review once the candidate
gate above is satisfied. Update coordination issue #12 to `STATUS: RUST_CONTRACT_REVIEW`,
`CODE PR #13 @ <new SHA>`, `DOCS PR #3 @ <new SHA>`, `PRIOR REVIEW EVIDENCE: PASS-2 rejection #4 @
88a6aa6, PASS-3 rejection #5 @ a64b78a`, `NEXT_OWNER: Codex`, `NEXT_ACTION: complete a full
independent Layer-08 contract re-review against the new PASS-4 candidate SHAs; all prior verdicts
apply only to their exact superseded candidates`. Then stop. Do not merge PR #13, #3, #4, or #5. Do
not implement Rust. Do not start Layer 09.

# PASS 5 — remediation for the independent Rust re-review rejection (L08-R002, R004, R005, R009, R010)

## Re-review reference

The independent Rust re-review of the PASS-4 candidate (code PR #13 @ `0161b0424e1b95fe2cea9590be8
d6de8260ae69c`, docs PR #3 @ `b27d3cef56938b97f59f6066b24671f75b97963d`) **REJECTED** it
(`minion-agent-docs#6` @ `65e665f28e29ebe6cf8deb792b206c108d32b1a6`, branch
`review/08-rust-contract-rereview-pass4`). One finding CLOSED: `L08-R006` (initial prompt lifecycle
before the steering claim -- the staged-admission fix genuinely closed this). Four findings STILL
OPEN or NEW: `L08-R002` (the live seam excluded the assistant's own streamed lifecycle and
Layer-06's own tool-execution events, and reduced state for the WRONG event in several places --
`PI_PARITY_DEFECT`), `L08-R004` (the normative spec's own Layer-07 section retained stale
present-tense claims that Layer 08 was unimplemented, contradicting the Layer-08 section later in
the same document -- `CONTRACT_ASSURANCE_DEFECT`), `L08-R005` (the replacement no-cap canonical
compared itself against a prior scenario override, not the actual removed implementation default,
so it did not discriminate against the regression it claimed to guard -- `CONTRACT_ASSURANCE_DEFECT`
evidence gap, not a production defect), `L08-R009` (`request_boundary_stop()` remained a public
method that could alter a Pi-equivalent run's own observable outcome with no owner governance
approval for the divergence -- `PI_PARITY_DEFECT`), and new `L08-R010` (`AG-022`'s own stated rule
contradicted the actual implementation for a follow-up-driven continuation -- `CONTRACT_ASSURANCE_
DEFECT`). This pass treats all five as blocking until independently reproduced against pinned Pi
and remediated; `L08-R006` is re-verified for regression only, not re-litigated, since this pass's
own restructuring (direct stream iteration, reduce-timing corrections) touches the same code path.

Prior Rust approval does not exist for this or any later candidate SHA -- the rejection at
`65e665f` applies only to the superseded PASS-4 candidate. The rejected review evidence PRs (#4,
#5, #6) are not modified or overwritten by this pass; they remain the immutable record of what
PASS 2, PASS 3, and PASS 4 actually were and why each was rejected.

## Findings, reproduced against pinned Pi and remediated

### L08-R002 — the live seam was still incomplete and mistimed

**Re-review finding, part 1 (completeness):** the assistant reply's own streamed `message_start`/
`message_update`/`message_end` were excluded from the live seam on the theory that the certified
`collect()`'s synchronous `on_chunk` callback made it infeasible. The re-review explicitly rejected
this: "The synchronous Python `collect(on_chunk=...)` callback is an implementation constraint, not
a Pi-visible contract limitation... Python can restructure its Layer-08 consumption without
changing Layer 02/04 semantics." Layer-06's own `tools/execution-start`/`tools/execution-end`
events were also never delivered to the unified seam at all -- only to their own separate,
Layer-06-scoped listeners.

**Re-review finding, part 2 (state-reduction timing):** "`_admit_messages` appends one finalized
Session message before dispatching both `MessageStart` and `MessageEnd`; therefore a start listener
already sees the message in `AgentInstance.messages`, while Pi adds it only at `message_end`. Minion
also does not set `streaming_message` for that `MessageStart` before the listener, while Pi does."
The same defect existed in `_settle_run_failure`, which additionally set `error_message` only AFTER
`turn_end`'s own listeners had already run, not before.

**Pi reproduction:** confirmed directly against source. Pi's own `AgentEvent` union delivered
through `Agent.subscribe`/`processEvents` includes `tool_execution_start`/`tool_execution_end`
alongside the message/turn/agent events. `processEvents`'s own reducer switch applies uniformly to
every `message_start`/`message_end`, not only the assistant's own streamed one: `streamingMessage =
event.message` at `message_start`; `streamingMessage = undefined; messages.push(event.message)` at
`message_end`. The `turn_end` reducer sets `errorMessage` as part of that same reduce, before that
event's own listeners run.

**Classification:** `PI_PARITY_DEFECT`.

**Remediation, completeness:** `_run_step` no longer calls the certified `collect()` convenience
wrapper for the assistant's own reply -- it iterates `self.llm.stream(request)` directly, an async
loop reproducing `collect()`'s own trivial drain logic (including its own `AdapterProtocolError`
invariant, satisfied by an `assert` rather than a raise once confirmed genuinely unreachable through
the certified `LlmService._settled()` wrapper every call site actually uses -- see RED/GREEN below),
with an `await self._dispatch_agent_event(...)` call added per chunk. `collect()` itself is
untouched, still certified, still used by every other caller (`llm/stream.py`, `llm/service.py`
tests, `MockAdapter` tests, and Layer 08's own now-restored `on_chunk` coverage -- see below).
Layer-06's own `tools/execution-start`/`tools/execution-end` EMIT events are captured, in real time,
into an ordered list by the SAME temporary listener that already tracked `pending_tool_calls`; once
the tool batch settles, every captured event is redelivered through `AGENT_LIFECYCLE_EVENT`, in the
exact order Layer 06 emitted it (every call's own `_preflight`/start always precedes any call's own
execute/end -- `tools/batch.py`'s own certified structure, confirmed by direct audit before relying
on it). This is a disclosed, narrower fidelity than pinned Pi's own live blocking dispatch for this
one event pair specifically: captured-then-redelivered means a slow Minion listener cannot causally
delay a specific tool call's own further progress the way a slow pinned Pi listener could, since
Layer-06's own EMIT (synchronous, fire-and-forget) dispatch mode is certified and this pass does not
reopen it -- every event still reaches the unified seam, completely and in order, just not with
Pi's own full causal-blocking property for this one pair.

**Remediation, reduce timing:** `_admit_messages` now sets `streaming_message = message` and
dispatches `MessageStart` FIRST, then sets `streaming_message = None`, appends the durable log
entry, and dispatches `MessageEnd` -- reduce, then dispatch, per event, matching pinned Pi's own
reducer exactly. `_run_step`'s own assistant-reply handling and tool-result handling do the same.
`_settle_run_failure` does the same for its own four-event sequence, and now sets `error_message`
as part of `turn_end`'s own reduce, before that event's dispatch, not after. `AgentLoop._run_wrapped`
now also mirrors pinned Pi's `runWithLifecycle`/`finishRun` unconditional writes exactly
(`streaming_message`/`error_message` reset at entry; `streaming_message`/`pending_tool_calls` reset
at exit via `finally`) rather than leaving some of that state to whatever the last turn happened to
leave behind.

**RED evidence:** before this pass, `test_a_run_executor_failure_recovers_through_the_live_
lifecycle_event_seam` and its siblings only ever observed `MessageStart`/`MessageEnd`/`TurnEnd`/
`AgentEnd` for ADMITTED messages and the failure sequence -- never for the assistant's own reply, at
all, regardless of how the test was written; there was no live event to observe. Removing driver.py's
own call to `collect(stream, on_chunk)` also silently dropped the ONLY exerciser of `collect()`'s own
`on_chunk` parameter in the entire test suite, a certified-layer coverage regression caught by the
full quality gate, not the Rust review.

**GREEN evidence:** `test_a_run_executor_failure_recovers_through_the_live_lifecycle_event_seam` and
`test_a_post_turn_callback_failure_recovers_through_the_live_seam` (both updated to expect the
assistant reply's own `MessageStart`/`MessageEnd` in sequence), `test_a_stream_with_no_start_chunk_
still_gets_a_message_start` (pinned pi's own `!addedPartial` defensive fallback, now genuinely live),
`test_turn_end_sets_error_message_even_for_a_non_terminal_reply` (the reduce applies unconditionally,
not only to a represented-error turn), `test_failure_message_start_listener_failure_interrupts_
recovery` (corrected: the failure's own `ASSISTANT_MESSAGE` log entry is durably appended at
`message_end` time, not `message_start` time, so a `message_start`-listener failure now correctly
shows NO `ASSISTANT_MESSAGE` entry at all, not one that "already happened"), and
`tests/llm/test_stream.py::test_collect_calls_on_chunk_for_every_chunk_in_order` (certified-layer
evidence, restoring `on_chunk`'s own coverage independent of any Layer-08 caller).

**Spec/manifest changes:** `spec/agent.md`'s Layer-08 section rewritten again ("The live Agent-event
seam" section); `AG-009` manifest row rewritten.

**Disposition:** resolved. `AG-009`: adopted.

### L08-R004 — Layer-07's own stale present-tense claims about Layer 08

**Re-review finding:** "The document's opening and Layer-07 authority map also retain present-tense
claims that Layer 08 is 'not yet certified,' AG-001..010 are 'unimplemented,' and
`streaming_message`, `pending_tool_calls`, and `error_message` are 'not yet wired.' Those statements
are not clearly limited to a historical Layer-07 candidate; they conflict with the current Layer-08
contract later in the same normative document." PASS 4 rewrote the Layer-08 section itself but never
audited the Layer-07 section above it, which predates Layer 08's own existence and was never updated
once Layer 08 was implemented.

**Classification:** `CONTRACT_ASSURANCE_DEFECT`.

**Remediation:** every present-tense "not yet implemented"/"not yet wired"/"not yet certified" claim
about Layer 08 in the Layer-07 section was located and corrected to point forward to the Layer-08
section's own current description, without rewriting Layer-07's own substantive content (which
Layer 07 still owns and remains accurate about): the document's own opening paragraph, the authority
map's own three "not yet wired" table cells, the mutable-configuration section's own forward
reference, the public-processing-status section's own two paragraphs, and a stale `AG-009` cross-
reference (Layer 07's own text pointed at Layer 08's `AG-009` for `AgentDefinition`'s shared
defaults -- the correct row is `AG-014`, confirmed by direct manifest lookup, not assumed).

**Disposition:** resolved. No manifest row directly corresponds to this doc-only defect; `spec/
agent.md` itself is the artifact.

### L08-R005 — the no-cap canonical was not actually discriminating

**Re-review finding:** "The new `no-turn-count-cap-on-pi-equivalent-run` canonical contains only
three tool turns. Against the PASS-3 implementation with its default cap of 16 and with no
scenario-supplied cap, it would pass unchanged. Its description claims it exceeds an 'old default-2'
fixture, but 2 was an explicit scenario override, not the old implementation default." PASS 4's own
canonical rewrite compared itself against the PREVIOUS SCENARIO's own scripted `config.max_steps: 2`
override, not the actual REMOVED implementation default (`AgentDefinition.max_steps == 16`) -- a
real mistake, not a labeling issue: three turns proves nothing about a 16-turn cap.

**Classification:** `CONTRACT_ASSURANCE_DEFECT` (evidence gap only; the production removal itself
was already correct and re-confirmed by direct source/structural search this pass, matching the
re-review's own "no remaining production cap found" note).

**Remediation:** the canonical scenario rewritten to script 20 tool-calling turns before its final
stopping turn -- more than the actual former default (16), not an arbitrary small number, so it
genuinely would have failed against the pre-removal implementation with no scenario override.

**RED evidence:** the pre-fix scenario (3 tool turns) passing is not meaningful RED/GREEN evidence
by itself; the re-review's own textual analysis (re-derived independently before trusting it) is
what establishes the defect.

**GREEN evidence:** `no-turn-count-cap-on-pi-equivalent-run.yaml` (21 provider-script turns, 42
expected messages), passing against the current implementation;
`test_a_long_tool_loop_is_not_bounded_by_any_turn_count` (Python-level regression, unchanged from
PASS 4, already correctly scripted at 20+1 turns there).

**Disposition:** resolved. No manifest row (`AG-020` remains removed, per PASS 4's own reasoning,
re-confirmed this pass: there is no Pi semantic surface and no Minion mechanism left to map).

### L08-R009 / L08-R010 — `request_boundary_stop()` removed entirely

**Re-review finding:** "`request_boundary_stop()` is public on `AgentLoop`. A tool or external host
can call it during an ordinary `prompt()`/`continue()` run, after which Minion may return
`agent_end(reason="boundary_stop")` instead of making the next provider request pinned Pi would
make. This is an observable extension on the same execution seam, not merely private pump
bookkeeping... no owner/governance approval for this new observable divergence is recorded." A new,
second finding (`L08-R010`) additionally caught that the implementation did not even correctly
enforce `AG-022`'s own stated rule: "The latch is checked only while the inner loop has tool- or
steering-driven work. If the current turn would otherwise stop, `_run_inner` breaks before checking
the latch, claims follow-up, and starts another turn in the same run despite the pending
boundary-stop request." Renaming `cancel()` to `request_boundary_stop()` (PASS 4) correctly
separated it from Layer-09's own `abort()`, but naming alone was never governance approval for the
divergence the rename disclosed.

**Classifications:** `PI_PARITY_DEFECT` (`L08-R009`, the unapproved public divergence);
`CONTRACT_ASSURANCE_DEFECT` (`L08-R010`, the rule/implementation contradiction).

**Resolution:** per this project's own standing default -- Pi fidelity, and no demonstrated product
need to preserve an observable divergence -- applied consistently with `max_steps`'s own removal
(`L08-R005`, PASS 4): `request_boundary_stop()` removed entirely, not fixed-and-kept. Removing the
mechanism closes `L08-R010` too, definitionally -- there is no longer a rule for the implementation
to contradict. `AgentLoop.request_boundary_stop`, the internal `_boundary_stop_requested` flag, and
the `_run_inner` check for it are all deleted. Manifest row `AG-022` removed; `AG-007`'s own
cross-reference to it corrected to note the removal. `tests/agent_loop/test_boundary_stop.py`'s
boundary-stop-specific tests removed; its one unrelated test (`test_a_blocked_agent_does_not_stall_
another`, progress isolation between independent instances, never used the latch) moved to a new
file, `test_progress_isolation.py`, under its own accurate name.

**Disposition:** resolved by removal. `AG-022`: removed. `AG-007`: unqualified deferral to Layer 09
again, cross-reference note updated.

## Regression verification for the closed finding

`L08-R006` (initial prompt lifecycle before the steering claim): the staged first-turn admission
itself is unchanged by this pass's own restructuring (direct stream iteration and reduce-timing
fixes both apply INSIDE `_run_step`'s own body and to `_admit_messages`'s own internals, neither of
which touch the two-stage admission sequencing `_run_inner` performs before `_run_step` is ever
called). `test_the_initial_prompt_lifecycle_precedes_the_steering_claim` still passes, extended only
to also observe the assistant reply's own now-live `MessageStart`/`MessageEnd` arriving AFTER the
steering claim (expected: they belong to the provider request that follows admission, not to
admission itself). No interaction bug surfaced.

## Full Layer-08 semantic reconstruction

Re-walked against pinned Pi after remediation, with particular attention to the two mechanisms this
pass rewrote: streamed-reply dispatch (every content kind -- text, thinking, tool-call -- still
produces correct `streaming_message` fidelity AND now also live `MessageUpdate` dispatch, checked
together, not separately) and tool-execution event delivery (captured-then-redelivered ordering
checked against a multi-call parallel batch, confirming starts precede ends and both preserve their
own established relative order). `error_message`'s own reduce-timing fix was checked against BOTH
the represented-error/aborted terminal path and the ordinary end-of-turn path (a normal reply
carrying an incidental `error_message`, now a dedicated regression). No `max_steps`- or
`request_boundary_stop()`-shaped termination exists anywhere in the Pi-equivalent run path.

## Quality gates (fresh, this pass)

```text
pytest (full suite):                 all passing, 0 failures
coverage (certified src packages):   100% -- includes restoring collect()'s own on_chunk coverage,
                                      lost when driver.py stopped calling it directly, caught by this
                                      gate itself before being reported as a finding
ruff check:                          clean
ruff format --check:                 clean (files touched this pass)
mypy (configured scope, src only):   clean, 0 errors
schema validation:                   all passing
conformance/ (full):                 all passing, including the genuinely-discriminating no-cap
                                      regression (21 turns, not 3)
manifest parse + unique-ID audit:    76 / 76 unique (AG-022 removed; AG-009 rewritten; AG-007
                                      cross-reference corrected)
stale normative-text audit:          spec/agent.md's Layer-07 section's own present-tense claims
                                      about Layer 08 corrected; the Layer-08 section's own remaining
                                      internal contradiction (the assistant-event carve-out) resolved
                                      by the L08-R002 fix itself, not merely reworded
placeholder-evidence audit:          no Layer-08 manifest row cites an unfilled placeholder scenario
                                      as satisfying evidence
```

## Active findings (after this pass)

```text
PI_BEHAVIOR_UNCERTAIN         none
PI_PARITY_DEFECT              none -- L08-R002 (complete live seam, correct reduce timing) and
                               L08-R009 (unapproved boundary-stop divergence) both resolved
CONTRACT_ASSURANCE_DEFECT     none -- L08-R004 (Layer-07's own stale claims), L08-R005 (non-
                               discriminating canonical), and L08-R010 (AG-022 rule contradiction,
                               closed by removal) all resolved
unapproved intentional divergence   none -- AG-022 removed rather than left unapproved; no
                               remaining Layer-08 row claims a divergence without disposing it
Layer-09 implementation       none -- handleRunFailure composes correctly with a future Layer-09
                               implementation without implementing any part of it
```

## Verdict

```text
Python Layer 08     CERTIFIED (self-certified; pending independent Rust contract review)
Rust Layer 08         NOT_IMPLEMENTED
shared Layer-08 contract   READY FOR INDEPENDENT RUST CONTRACT REVIEW (remediated candidate; no
                             prior Rust approval carries forward from any rejected candidate)
Layer 08 cross-language     NOT CLOSED
Layer 09                     NOT STARTED
```

## Workflow-process retrospective notes (this cycle)

Third rejection/remediation cycle for this layer. Captured for later integration into
`process/agent-workflow.md` at Layer-08's own closure retrospective, NOT applied to that file now:

1. An implementation constraint in a certified LOWER layer (`collect()`'s synchronous `on_chunk`)
   is not automatically a Pi-visible contract limitation at the layer consuming it -- a caller can
   often restructure its own consumption (iterate the stream directly) without reopening or
   modifying the lower layer at all. This distinction should have been checked before PASS 4 cited
   the constraint as a reason to exclude coverage, not after a second rejection.
2. When a public method removal (`max_steps`, PASS 4) resolves cleanly without owner escalation,
   the SAME default applies to a structurally similar case (`request_boundary_stop()`) found later
   in the SAME layer -- this pass applied that precedent directly rather than re-deriving whether
   escalation was needed from scratch.
3. A "regression that proves the opposite of what a removed mechanism used to prove" canonical must
   be benchmarked against the ACTUAL removed value, not a scenario-local override that happened to
   be smaller and easy to exceed -- re-verify the specific number a discriminating scenario needs to
   exceed by checking the removed field's own former default, not by re-using a nearby number from
   the scenario being replaced.
4. A stale-normative-text audit must cover the WHOLE document a Rust reviewer treats as one
   contract, not only the section a given pass directly edited -- PASS 4 rewrote the Layer-08
   section correctly but never re-read the Layer-07 section above it for claims ABOUT Layer 08.
5. Removing a certified lower-layer call site (e.g. `collect()`) can silently drop that lower
   layer's own test coverage for a parameter/branch nothing else exercises -- the full quality gate
   (100% coverage across ALL certified packages, not just the layer being changed) is what catches
   this, not the Rust review; treat a coverage gate failure in an unrelated certified package as a
   direct signal of exactly this kind of accidental exercise loss, not noise to route around.

## Next action

Push this pass's commits to the existing `layer/08-python-shared` branches (both repos); update PR
#13/#3 bodies with the PASS-5 remediation summary, new head SHAs, reviewed/rejected predecessor
SHAs, and L08-R002/R004/R005/R009/R010 closure status; mark both Ready for Review once the candidate
gate above is satisfied. Update coordination issue #12 to `STATUS: RUST_CONTRACT_REVIEW`,
`CODE PR #13 @ <new SHA>`, `DOCS PR #3 @ <new SHA>`, `PRIOR REVIEW EVIDENCE: PASS-2 rejection #4 @
88a6aa6, PASS-3 rejection #5 @ a64b78a, PASS-4 rejection #6 @ 65e665f`, `NEXT_OWNER: Codex`,
`NEXT_ACTION: complete a full independent Layer-08 contract re-review against the new PASS-5
candidate SHAs; all prior verdicts apply only to their exact superseded candidates`. Then stop. Do
not merge PR #13, #3, #4, #5, or #6. Do not implement Rust. Do not start Layer 09.
