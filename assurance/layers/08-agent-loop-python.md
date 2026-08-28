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

## Next action

Push this pass's commits to the existing `layer/08-python-shared` branches (both repos); update PR
#13/#3 bodies with the PASS-3 remediation summary, new head SHAs, and L08-R001..R008 disposition;
mark both Ready for Review once the candidate gate above is satisfied. Update coordination issue
#12 to `STATUS: RUST_CONTRACT_REVIEW`, `CODE PR #13 @ <new SHA>`, `DOCS PR #3 @ <new SHA>`,
`NEXT_OWNER: Codex`, `NEXT_ACTION: complete independent re-review against the new candidate SHAs;
the prior rejection (88a6aa6) applies only to the superseded PASS-2 candidate`. Then stop. Do not
merge PR #13, #3, or review-evidence PR #4. Do not implement Rust. Do not start Layer 09.
