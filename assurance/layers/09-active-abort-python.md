# Layer 09 — Active abort/cancellation, Python implementation

# PASS 1 — initial implementation

## Starting state

- accepted code baseline: `minion-agent@main` `3ec1a386c86a93a13344ed38d796fbb74e9817bd`
- accepted docs baseline: `minion-agent-docs@master` `ecb809798b7437045e1325683306c3f15f46571e`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Layer 08: CROSS-LANGUAGE CERTIFIED / CLOSED
- convergence contract: `assurance/layers/09-active-abort-contract-checkpoint.md` (revisions 1-2),
  targeted re-review `assurance/layers/09-active-abort-rust-checkpoint-rereview.md` --
  `L09-C001`/`L09-C002`/`L09-C003` all `PROVISIONALLY CLOSED @ ecb8097`,
  `CONVERGENCE CONTRACT AGREED FOR PYTHON IMPLEMENTATION`

This is the implementation pass authorized by that agreed checkpoint. It implements exactly the
contract the checkpoint's two revisions and the targeted re-review settled; it does not
re-derive semantics from scratch.

## Implementation

**`RunSignal`** (`runtime/signal.py`, new module, `RT-024`): a poll-based cancellation flag
(`aborted` property, idempotent `abort()`), one instance per run, deliberately NOT built on
`asyncio.Task.cancel()`/`CancelledError` -- matching pinned Pi's own cooperative, never-forced
`AbortSignal` semantics and certified Rust Layer 06's own already-reserved poll-based
`ToolExecutionSignal` trait. Exported from `runtime/__init__.py` -- an additive new public symbol,
not a change to any existing certified `runtime/` file.

**`AgentInstance.signal`/`abort()`** (`agent/instance.py`, `AG-007`): `signal: RunSignal | None`,
`None` while idle, matching pinned Pi's own `Agent.signal` getter. `abort()` is a no-op when idle,
otherwise flips the active run's own signal; never itself changes `status`, so `reset()` still
rejects until the run has actually settled.

**`AgentLoop` signal lifecycle** (`agent_loop/driver.py`): `_run_wrapped` creates a NEW
`RunSignal()` at the same point it performs its other three unconditional entry writes, and clears
it back to `None` in the same `finally` block that undoes them -- matching pinned Pi's own `new
AbortController()`/`finishRun()` lifecycle exactly, live through `_settle_run_failure`'s own
recovery dispatch and `agent_end` listener settlement.

**Consumer wiring:** `AGENT_LIFECYCLE_EVENT`/`AGENT_PREPARE_NEXT_TURN`/`AGENT_TURN_STOPPING`
listeners need NO new parameter -- they already receive `instance` as their first argument (an
established Minion convention predating this layer), so `instance.signal` is already reachable. An
intentional, disclosed architectural mapping from pinned Pi's own explicit-parameter threading for
these same consumers (Pi's own `subscribe`/wrapping-closure design has no `instance`-equivalent
object to hang the signal on instead). `llm/service.py::Request` gains an optional `signal:
RunSignal | None = None` field (`AI-027`), carried through to `adapter.stream(request)` unexamined.
`tools/execute.py`/`tools/batch.py` thread `signal` explicitly (`TOOL-024`), since Layer 06 has no
`instance` access at all:

- `_preflight` checks `signal.aborted` exactly once, immediately after the `TOOLS_PRE_EXECUTE`
  waterfall resolves, before the `Block`/`Proceed` decision is examined -- winning over a `Block`,
  losing to an unknown tool / a validation exception / a throwing before-hook listener (all of
  which return/raise before the signal is ever read);
- `_execute_and_finalize` passes `signal` to a tool's own `execute()` as a new, arity-detected
  fourth positional parameter (`_wants_signal`), preserving an existing 3-parameter tool's own
  `update`-only meaning unchanged;
- `execute_batch`'s sequential branch polls `signal.aborted` AFTER each call's own complete
  lifecycle, before starting the next; its parallel branch polls it after each call's own preflight
  OUTCOME (immediate or prepared) is recorded, before preflighting the next source call -- NOT
  after execution, so a retained prepared closure still starts via the existing concurrent barrier
  even after a later poll sees the signal aborted.

No canonical scenario was filled this pass: `active-abort-tool`/`active-abort-provider`/`abort-
settles-before-idle` (`conformance/agent/`) remain unfilled placeholders. The checkpoint's own
required regression evidence is instead delivered as permanent Python-level explicit-language
tests -- the same "canonical OR explicit language test" standard the independent Layer-08 review
itself accepted for `L08-R014`. Building canonical vocabulary for injecting a mid-scenario
`abort()` trigger and asserting signal state is a genuinely separate, larger addition than this
pass's own scope, consistent with this project's "don't design for hypothetical future
requirements" convention.

## Evidence

New tests, organized by the checkpoint finding each one closes:

**`RunSignal` itself** (`runtime/test_signal.py`): fresh-not-aborted, `abort()` sets aborted,
idempotent `abort()`, two signals independent.

**`AgentInstance.signal`/`abort()`** (`agent/test_instance.py`): `None` while idle, `abort()`
while idle is a no-op, `abort()` flips an attached signal, `abort()` does not make `reset()` legal
before the run settles.

**`L09-C002`, preflight abort/error priority** (`tools/test_execute.py`): unknown tool wins over
an aborted signal; a validation failure wins; a throwing before-hook wins; an aborted signal wins
over a RETURNED `Block` decision (the actually-discriminating witness, `block: True` + aborted, not
`block: False` + aborted); no-before-hook-plus-aborted produces `"Operation aborted"`; a call
proceeds normally when the signal is not aborted. Plus the cooperative-execute()-parameter tests:
a 4-parameter tool receives the signal; a 3-parameter tool's own meaning is unchanged; `execute()`
is not forcibly interrupted by an aborted signal; the after-hook runs unconditionally despite one.

**`L09-C001`, sequential vs. parallel batch abort algorithms** (`tools/test_batch.py`): sequential
abort after a call completes skips the rest of the batch; the parallel A/B/C discriminating
witness, reproduced from the independent review's own trace; a batch completes normally when the
signal is never aborted.

**Wiring integration** (`agent_loop/test_active_abort.py`, through the REAL `AgentLoop`, not
`execute_batch`/`_preflight` called directly): signal is `None` before and after a run; the active
run's signal reaches `Request.signal`, observed on the mock adapter's own captured request; `reset()`
stays illegal while an aborted run is still settling; abort from a tool's own before-hook, mid
parallel batch, truncates through the real loop exactly as the unit-level witness describes;
a scripted represented-`aborted` terminal is unaffected by this pass's own wiring (regression).

**RED evidence:** the two batch-level discriminating tests (`test_sequential_abort_after_a_call_
completes_skips_the_rest_of_the_batch`, `test_parallel_abort_witness_matches_the_discriminating_
trace`) were run against `tools/batch.py` with both `if signal.aborted: break` polls temporarily
removed -- both failed, the parallel one showing the exact wrong trace (`start_c`/`end_c` where the
fix requires `end_a`), confirming genuine discrimination before restoring the fix.

**GREEN evidence:** every test above passes against the implementation as committed.

## Regression verification

Layer 08's own full suite (agent/agent_loop/session/tools/runtime/llm) re-run unchanged and green
-- no `AGENT_LIFECYCLE_EVENT`/`AGENT_TURN_STOPPING`/`AGENT_PREPARE_NEXT_TURN` listener signature
changed, no `EventBus`/waterfall/serial dispatch semantic touched, no Layer-06 preflight/batch
ORDERING rule (`TOOL-023`/`IR-L06-001`) reopened -- `signal` is threaded alongside the existing
barrier, not through it. Layer-02's own certified non-cancelled stream vocabulary/settlement is
unaffected: `Request.signal` is a new optional field no existing caller supplies, and `LlmService.
stream()`/`_settled()` never read it.

`tests/runtime/test_public_surface.py` updated: `RunSignal` added to the expected `runtime.__all__`
set (a deliberate, reviewed addition to a certified-surface test, not a drift).

## Quality gates (fresh, this pass)

```text
pytest (full suite):                 1071 passed, 19 xfailed (pre-existing, unrelated), 0 failed
coverage (certified src packages):   100.00%, including runtime/signal.py (10 statements, 0 missed)
ruff check:                          clean (whole tree)
ruff format --check:                 clean on every file this pass touched; the same pre-existing,
                                      unrelated 7-file drift noted in every earlier Layer-08 pass
                                      remains untouched and out of this pass's ownership scope
mypy (configured scope, src only):   clean, 0 errors, 58 files (up from 57 -- runtime/signal.py)
schema validation:                   unaffected, unchanged this pass
conformance/ (full):                 all passing (unchanged -- no canonical scenario added/changed)
manifest parse + unique-ID audit:    78 / 78 unique (AG-007 gained a Layer-09 paragraph; two new
                                      rows, AI-027 and TOOL-024)
placeholder-evidence audit:          active-abort-tool/active-abort-provider/abort-settles-before-
                                      idle remain explicitly unfilled and are NOT cited as
                                      satisfying evidence anywhere in this pass's own rows
```

## Active findings

```text
PI_PARITY_DEFECT              none
CONTRACT_ASSURANCE_DEFECT     none -- L09-C001/C002/C003 all closed by this implementation
PI_BEHAVIOR_UNCERTAIN         none
unapproved intentional divergence   none
disclosed Minion architectural mapping   AGENT_LIFECYCLE_EVENT/AGENT_PREPARE_NEXT_TURN/
                               AGENT_TURN_STOPPING read the signal via instance.signal rather than
                               an explicit parameter (spec/agent.md's own "Active abort
                               propagation" section); a single preflight abort checkpoint covers
                               both of pinned Pi's two (spec/tools.md)
disclosed Minion-specific constraint   4-parameter arity dispatch required for a tool wanting
                               signal (cannot want signal alone without also declaring update)
Rust cross-language dependency      NOT_IMPLEMENTED -- certified Rust Layer 06's own
                               ToolExecutionSignal seam remains reserved, unexercised; awaiting
                               this candidate's own independent contract review
Layer 10                       NOT STARTED
```

## Verdict

```text
Python Layer 09     CERTIFIED (self-certified; pending independent Rust contract review)
Rust Layer 09         NOT_IMPLEMENTED
shared Layer-09 contract   READY FOR INDEPENDENT RUST CONTRACT REVIEW
Layer 09 cross-language     NOT CLOSED
Layer 10                     NOT STARTED
```

## Next action (superseded -- see PASS 2 below)

Push this pass's commits to new short-lived candidate branches in both repos (`layer/09-python-
shared`), open paired PRs, create/update the Layer-09 coordination issue's own `CODE PR`/`DOCS PR`/
`STATUS: RUST_CONTRACT_REVIEW`/`NEXT_OWNER: Codex` state, and request a full independent Rust
contract review of the exact candidate SHAs against this document, `assurance/layers/09-active-
abort-contract-checkpoint.md`, and the manifest rows above (`AG-007`, `AI-027`, `TOOL-024`). Then
stop. Do not implement Rust. Do not start Layer 10.

This candidate (code PR `minion-agent#17` @ `b5e44bb780e67dc8fccd27f630ce8d783b11303c`, docs PR
`minion-agent-docs#26` @ `fdf4d3860d875cb4e800bba01784e22f7ba79ee4`) was independently reviewed and
**REJECTED FOR RUST IMPLEMENTATION** (`minion-agent-docs#27`, review commit
`0a781d3f6710d633f9fcf4c10ef11422dfeef1ee`, `assurance/layers/09-active-abort-rust-contract-
review.md`): the batch algorithms and preflight priority (`L09-C001`/`L09-C002`) were confirmed
correct; five `PI_PARITY_DEFECT`/`CONTRACT_ASSURANCE_DEFECT` findings (`L09-R001`..`L09-R005`)
blocked the propagation/authority/settlement half. See PASS 2 below.

# PASS 2 — remediate L09-R001 through L09-R005

## Re-review reference

The independent Rust contract review of the PASS-1 candidate (see above) rejected it: shared
Layer-09 contract `REJECTED FOR RUST IMPLEMENTATION`, Python Layer 09 `REOPENED`. Full review
text: `assurance/layers/09-active-abort-rust-contract-review.md` on branch
`review/09-active-abort-contract` (not reproduced verbatim here).

## Findings, reproduced against pinned Pi and remediated

### L09-R004 — signal authority exceeded Pi's own read-only guarantee

**Re-review finding:** `PI_PARITY_DEFECT`. PASS 1's own `RunSignal` exposed a PUBLIC `abort()` to
every consumer -- a tool or adapter holding it could trigger cancellation itself, authority pinned
Pi's own `AbortSignal` (observational only; mutation lives solely on the private
`AbortController`) does not grant. `AgentInstance.signal` was also a plain public attribute any
listener could REASSIGN mid-run (`instance.signal = RunSignal()`), redirecting later requests to a
caller-supplied replacement -- violating pinned Pi's own "one unchanged signal identity per run."
An executable witness showed an `AgentStart` listener replacing the signal and a later request
observing the replacement, not the original.

**Pi reproduction:** re-confirmed directly against pinned Pi source (`ref-repos/pi` @ `b7bb00b`,
`agent.ts`): `AbortController` is a private field on the class created inside `runWithLifecycle`;
`Agent.signal` is a bare getter with no setter at all, returning `this.activeRun?.abortController.
signal` -- the `.signal` PROPERTY of the controller (pinned Pi's own `AbortSignal`), never the
controller itself. No consumer-facing type in pinned Pi's own surface has an `abort()` method
except `Agent.abort()`.

**Classification:** `PI_PARITY_DEFECT`.

**Remediation:** `runtime/signal.py` now defines TWO types. `RunAbortController` -- the PRIVATE
mutator, held only by `AgentInstance` as `_active_controller` (no public accessor at all) --
constructs its own `RunSignal` view ONCE, cached as `.signal`, so every access returns the
identical object for the controller's whole lifetime. `RunSignal` -- the READ-ONLY view every
consumer actually receives -- has NO `abort()` method structurally; `hasattr(signal, "abort")` is
`False`. `AgentInstance.signal` is now a read-only PROPERTY with no setter: `instance.signal = x`
raises `AttributeError` unconditionally. Two new internal methods, `_start_run_signal`/`_end_run_
signal`, are the ONLY way the controller is created/cleared -- called exclusively from `AgentLoop.
_run_wrapped`, matching the same "Layer 07 owns vocabulary, Layer 08 owns per-run lifecycle" split
already established for `streaming_message`/`pending_tool_calls`/`error_message`.

**RED evidence:** confirmed the PASS-1 candidate's own `test_abort_flips_the_active_signal`-style
test (`instance.signal = RunSignal()`) previously SUCCEEDED (proving the vulnerability was real,
not hypothetical) before the property/setter removal made that exact statement raise
`AttributeError` instead.

**GREEN evidence:** `test_signal_has_no_public_setter` (`agent/test_instance.py`) asserts
`AttributeError` on assignment; `test_the_read_only_signal_has_no_abort_method`/
`test_run_signal_cannot_be_constructed_without_a_controller` (`runtime/test_signal.py`) assert the
structural guarantees directly; `test_the_signal_is_the_same_object_across_accesses`/
`test_signal_is_the_same_object_across_the_whole_run` confirm stable identity.

### L09-R002 — exception-after-abort was hard-coded `error`, never reading the signal

**Re-review finding:** `PI_PARITY_DEFECT`. `AgentLoop._settle_run_failure` hard-coded
`stop_reason=StopReason.ERROR` and never read `instance.signal.aborted` at all, contradicting this
row's own already-correct normative text (`AG-007`) -- the prose was written correctly in PASS 1
but the code was never actually updated to match it. An executable witness: a listener calls
`instance.abort()` then raises once; the candidate settled `stop_reason: error`, not `aborted`.

**Pi reproduction:** re-confirmed `runWithLifecycle`'s own `catch (error) { await this.
handleRunFailure(error, abortController.signal.aborted); }` (`agent.ts:504-505`) and
`handleRunFailure`'s own use of that boolean directly as `stopReason: aborted ? "aborted" :
"error"` (`agent.ts:519`) -- causation is deliberately irrelevant; the classification is purely a
function of the signal's CURRENT state at the read.

**Classification:** `PI_PARITY_DEFECT`.

**Remediation:** `_settle_run_failure` now reads `self.instance.signal` at the top of the method
and selects `StopReason.ABORTED` when `signal is not None and signal.aborted`, `StopReason.ERROR`
otherwise -- a single, direct translation of Pi's own boolean-to-stop-reason mapping.

**RED evidence:** the new `test_exception_after_abort_is_settled_as_aborted_not_error`
(`agent_loop/test_active_abort.py`) run against the reverted (hard-coded `ERROR`) implementation
fails, observing `stop_reason: error` where `aborted` is required.

**GREEN evidence:** the same test passes against the fix; the paired
`test_an_unrelated_exception_without_abort_is_still_settled_as_error` confirms the NON-aborted
case is unaffected.

### L09-R001 — before/after tool hooks never actually received the signal

**Re-review finding:** `PI_PARITY_DEFECT`. Despite the checkpoint's own consumer matrix and this
row's own PASS-1 prose both claiming tool hooks received `signal` "threaded explicitly," the
`TOOLS_PRE_EXECUTE`/`TOOLS_POST_EXECUTE` waterfall DISPATCH calls never actually included it among
their own payload arguments -- a registered listener had no way to observe it through the
declared seam at all. Executable witnesses: a variadic before-listener and a raw after-listener
each observed zero `RunSignal` instances among their own received arguments, despite `signal`
genuinely being active and non-`None` for the surrounding call.

**Pi reproduction:** re-confirmed `prepareToolCall`'s own `config.beforeToolCall(context, signal)`
and `finalizeExecutedToolCall`'s own `config.afterToolCall(context, signal)`
(`agent-loop.ts:619-627`, `724-736`) -- `signal` is the hook's own SECOND parameter in both cases,
not merely something the LOOP checks on the hook's behalf.

**Classification:** `PI_PARITY_DEFECT`.

**Remediation:** `signal` is now an explicit payload argument on both waterfall dispatches:
`ctx.events.waterfall(TOOLS_PRE_EXECUTE, call, definition, validated_arguments, signal, terminal=
..., ...)` and `ctx.events.waterfall(TOOLS_POST_EXECUTE, result, signal, terminal=..., ...)`.
Every listener registered against either event now receives it as a positional parameter
immediately before `next_`. A listener that delegates via bare `next_()` sees it unchanged
automatically (`EventBus.waterfall`'s own `replacement or current` rule); one that delegates with
an explicit replacement value must re-supply it (`next_(replacement, signal)`) or later listeners
in the chain will not see it -- `register_after_tool_call_hook`'s own production wrapper does this
correctly, and `_finalize`'s own `_restore` identity-protection `normalize_step` (`L06-R003`) was
widened to tolerate a variable-length trailing tail (`current[0]`/`current[1:]`) rather than
requiring exactly one element, so a listener that forgets to re-supply degrades gracefully to "no
signal for later listeners" instead of raising `ValueError` on unpack. Every existing production
and test listener across `execute.py`, `tests/conformance/agent_runner.py`, and the whole test
suite (`test_execute.py`, `test_batch.py`, `test_post_execute.py`, `test_active_abort.py`) updated
to accept the new argument.

**RED evidence:** the exact executable witnesses from the review (a variadic before-listener, a
raw after-listener) were reproduced as `test_before_hook_receives_the_active_signal`/
`test_after_hook_receives_the_active_signal` and run against the reverted (pre-widening) waterfall
calls first -- both failed with a `TypeError` (missing positional argument) confirming the
listener signature genuinely could not have received `signal` under the old dispatch.

**GREEN evidence:** both tests pass against the widened dispatch, each asserting the received
signal `is` the exact same object the surrounding call's own `signal` argument was.

### L09-R003 — signal-only tools were not representable

**Re-review finding:** `PI_PARITY_DEFECT`. PASS 1's own PURE-ARITY dispatch (`_wants_signal`:
arity >= 4; `_wants_update`: arity >= 3) could not represent pinned Pi's own genuinely signal-only
`execute(toolCallId, params, signal)` -- a tool wanting cancellation but no live updates was
forced to declare an unused 4th `update` parameter. PASS 1's own candidate test explicitly
asserted this as the ONLY representable shape (`wants_update: true, wants_signal: false` for a
3-parameter tool, unconditionally), while the manifest's own `TOOL-024` row claimed `disposition:
adopted` -- full capability coverage -- for a design that structurally could not express one of
Pi's own four combinations.

**Pi reproduction:** re-confirmed `AgentTool.execute: (toolCallId, params, signal?, onUpdate?) =>
Promise<AgentToolResult<TDetails>>` (`types.ts:395-400`) -- `signal?`/`onUpdate?` are INDEPENDENT
optional parameters; TypeScript's own type system permits a 3-argument implementation that
receives `(toolCallId, params, signal)` with no `onUpdate` at all.

**Classification:** `PI_PARITY_DEFECT`.

**Remediation:** `ToolDefinition.wants_signal: bool = False` (Layer 05, `tools/definition.py`) --
an EXPLICIT, declared capability rather than an arity inference. `_wants_signal(definition)`/
`_wants_update(definition)` (renamed from arity-only free functions taking a bare callable to
definition-aware ones) now consult both the flag and the arity:

```text
wants_signal   arity   execute(...) receives
False          2       (tool_call_id, arguments)                    -- neither (unchanged)
False          3       (tool_call_id, arguments, update)             -- update only (unchanged)
True           3       (tool_call_id, arguments, signal)             -- signal only (NEW)
True           4       (tool_call_id, arguments, signal, update)     -- both (unchanged)
```

`wants_signal=False` (every pre-Layer-09 tool, unconditionally) preserves the EXACT prior dispatch
for both of its own rows; only `wants_signal=True` changes any existing meaning, and only for
tools that explicitly opt in.

**RED evidence:** `test_a_signal_only_tool_receives_no_update_slot` (a 3-parameter tool declaring
`wants_signal=True`, expecting `(id, args, signal)`) run against the PASS-1 candidate's own
arity-only dispatch fails: the old code would have dispatched it as `(id, args, update)` --
UPDATE, not signal -- observably wrong for this exact shape.

**GREEN evidence:** the same test passes against the `wants_signal`-aware dispatch;
`test_a_three_parameter_tools_own_meaning_is_unchanged` (from PASS 1, re-run) confirms
`wants_signal=False` tools are completely unaffected.

### L09-R005 — `transformContext` was entirely absent from the contract and implementation

**Re-review finding:** `CONTRACT_ASSURANCE_DEFECT`. Pinned Pi's own `config.transformContext(
messages, signal)`, invoked immediately before every provider request, was omitted from the
checkpoint's own consumer matrix and had no Minion equivalent at any layer. `AGENT_PRE_STEP` is
NOT equivalent: it runs once, at input admission boundaries, changing what gets durably admitted;
`transformContext` runs on every request and never mutates the persistent transcript.

**Pi reproduction:** re-confirmed `streamAssistantResponse`'s own `messages = await config.
transformContext(messages, signal)` (`agent-loop.ts:288-292`) reassigns only that function's own
LOCAL variable -- never `context.messages`/`currentContext.messages`.

**Classification:** `CONTRACT_ASSURANCE_DEFECT`.

**Remediation:** new `AGENT_TRANSFORM_CONTEXT` waterfall event (`agent/events.py`, Layer 08 --
manifest row `AG-023`), listener signature `(instance, messages, signal, next_) -> tuple[Message,
...]`. Dispatched in `AgentLoop._run_step` (new `_transform_context` method) immediately before
`Request` construction, transforming the already-history-windowed message tuple; the result feeds
ONLY `Request.messages` for that one request and is never written back to `context`/`RunContext`.
Zero listeners (every caller before this pass) preserves prior behavior exactly. Terminal reflects
whatever `messages` value is current when the chain ends (matching `tools/post-execute`'s own
"terminal is the current payload" convention, not a fixed value, since a delegating listener's own
transformation must not be discarded).

**RED evidence:** N/A in the usual sense -- this event did not exist before this pass, so there is
no "reverted implementation" to run the new tests against; the discriminating evidence is that the
new tests FAIL if the dispatch is removed entirely (confirmed by temporarily removing the
`_transform_context` call and observing `AttributeError`/no-op behavior) rather than by comparing
against a prior buggy behavior.

**GREEN evidence:** `test_transform_context_receives_messages_and_the_active_signal` confirms a
registered listener receives the admitted messages and the active run's own non-`None` signal.
`test_transform_context_output_is_provider_local_not_persistent` is the required discriminating
witness: a listener injects a synthetic marker message; the marker appears in the FIRST request's
own `Request.messages`, appears AGAIN (independently re-injected, not accumulated) in the SECOND
request after a tool call, and is absent from `AgentInstance.messages`'s own durable, offline-
visible transcript at every point -- proving the transform is genuinely provider-local and
non-persistent.

## Regression verification for previously-closed findings

`L09-C001`/`L09-C002` (batch algorithms, preflight priority): unaffected -- the review's own
ledger confirmed these correct in the PASS-1 candidate, and this pass's own diff to `_preflight`/
`execute_batch` is additive (new `signal` payload argument, `wants_signal`-aware dispatch) on top
of the SAME algorithm structure, not a rewrite of it. Every PASS-1 test for these two findings
re-run unchanged and still passing. `TOOL-023`/`IR-L06-001` (sequential-preflight/concurrent-
execution barrier): unaffected, not reopened. Layer 08's own full suite: unaffected, no
`AGENT_LIFECYCLE_EVENT`/`AGENT_PREPARE_NEXT_TURN`/`AGENT_TURN_STOPPING` listener signature changed
(only the genuinely NEW `AGENT_TRANSFORM_CONTEXT` event was added).

## Quality gates (fresh, this pass)

```text
pytest (full suite):                 1083 passed, 19 xfailed (pre-existing, unrelated), 0 failed
coverage (certified src packages):   100.00%, including runtime/signal.py (19 statements) and the
                                      widened tools/execute.py, tools/batch.py, agent/instance.py,
                                      agent_loop/driver.py, agent/events.py
ruff check:                          clean (whole tree)
ruff format --check:                 clean on every file this pass touched; the same pre-existing,
                                      unrelated 7-file drift noted in every earlier pass remains
                                      untouched and out of this pass's ownership scope
mypy (configured scope, src only):   clean, 0 errors, 58 files
schema validation:                   unaffected, unchanged this pass
conformance/ (full):                 all passing, including the updated agent_runner.py listener
                                      signatures (TOOLS_PRE_EXECUTE dispatch widened)
manifest parse + unique-ID audit:    79 / 79 unique (AG-007/AI-027/TOOL-024 gained PASS-2
                                      paragraphs; one new row, AG-023, for AGENT_TRANSFORM_CONTEXT)
placeholder-evidence audit:          active-abort-tool/active-abort-provider/abort-settles-before-
                                      idle remain explicitly unfilled and are NOT cited as
                                      satisfying evidence anywhere in any row touched this pass
```

## Active findings (after this pass)

```text
PI_PARITY_DEFECT              none -- L09-R001/R002/R003/R004 all closed
CONTRACT_ASSURANCE_DEFECT     none -- L09-R005 closed
PI_BEHAVIOR_UNCERTAIN         none
unapproved intentional divergence   none
disclosed Minion architectural mapping   AGENT_LIFECYCLE_EVENT/AGENT_PREPARE_NEXT_TURN/
                               AGENT_TURN_STOPPING/AGENT_TRANSFORM_CONTEXT read the signal via
                               instance.signal or an explicit payload argument rather than Pi's own
                               explicit-parameter-everywhere design (spec/agent.md); a single
                               preflight abort checkpoint covers both of pinned Pi's two
                               (spec/tools.md); ToolDefinition.wants_signal is an explicit
                               capability flag rather than Pi's fully-independent optional
                               parameters
Rust cross-language dependency      NOT_IMPLEMENTED -- certified Rust Layer 06's own
                               ToolExecutionSignal seam remains reserved, unexercised; awaiting
                               this candidate's own independent contract review
Layer 10                       NOT STARTED
```

## Verdict

```text
Python Layer 09     CERTIFIED (self-certified; pending independent Rust contract review)
Rust Layer 09         NOT_IMPLEMENTED
shared Layer-09 contract   READY FOR INDEPENDENT RUST CONTRACT REVIEW (remediated candidate; no
                             prior Rust approval carries forward from the rejected PASS-1
                             candidate)
Layer 09 cross-language     NOT CLOSED
Layer 10                     NOT STARTED
```

## Workflow-process retrospective notes (this cycle)

First Layer-09 finding set to reach a FULL independent contract review (as opposed to a checkpoint
re-review) after the checkpoint's own convergence protocol closed. Captured for later integration
into `process/agent-workflow.md`:

1. A checkpoint's own consumer matrix can itself be incomplete in a way NEITHER checkpoint
   revision's own review caught (`L09-R005`): both checkpoint reviews focused on the SEQUENCING/
   PRIORITY questions the original findings named (`L09-C001`/`L09-C002`/`L09-C003`) and did not
   independently re-derive the COMPLETE consumer list from Pi source themselves at that stage --
   that only happened once a full contract review, with its own mandate to re-audit everything,
   was performed. A checkpoint closing three named findings is not the same guarantee as "this
   surface's full consumer list is complete."
2. Prose in a checkpoint/spec document is not evidence that the CODE matches it (`L09-R001`,
   `L09-R002`): both were cases where the NORMATIVE TEXT already said the correct thing, but the
   implementation never actually did it. A contract-checkpoint-agreed design does not by itself
   guarantee the subsequent implementation pass correctly transcribed every consumer/checkpoint
   into working code -- each one needs its own executable witness proving delivery, not merely a
   restatement of the design intent.
3. A "disclosed limitation" is not automatically an acceptable one (`L09-R003`): PASS 1 correctly
   DISCLOSED that its arity-only dispatch could not represent a signal-only tool, but disclosure is
   not the same as an approved intentional divergence -- the manifest row's own `disposition:
   adopted` implicitly claimed the opposite (full capability coverage), and the disclosure itself
   should have been the signal to escalate or fix, not merely note.
4. Authority questions (`L09-R004`: who can MUTATE a value vs. who can merely OBSERVE it) are a
   distinct category from propagation questions (does the value REACH a consumer at all) and need
   their own explicit review pass -- this session's own checkpoint work focused heavily on
   propagation/timing/priority (matching the ORIGINAL `L09-C001`/`C002`/`C003` findings) and never
   separately asked "and can a consumer that merely observes this value also mutate it?" until an
   independent implementation review asked exactly that.

## Next action (superseded -- see PASS 3 below)

Push this pass's commits to the existing `layer/09-python-shared` branches (both repos); update PR
#17/#26 bodies with the PASS-2 remediation summary and new head SHAs. Update coordination issue
#16 (`minion-agent`): `STATUS: RUST_CONTRACT_REVIEW`, new exact `CODE PR`/`DOCS PR` SHAs, append
the PASS-1 rejection reference (`minion-agent-docs#27` @ `0a781d3f6`) to `PRIOR REVIEW EVIDENCE`,
`NEXT_OWNER: Codex`, `NEXT_ACTION: complete a full independent Rust contract review of this PASS-2
candidate against L09-R001 through L09-R005 specifically; L09-C001/C002/C003 remain provisionally
closed unless this review finds a new issue with them`. Then stop. Do not merge any candidate or
review-evidence PR. Do not implement Rust. Do not start Layer 10.

This candidate (code PR `minion-agent#17` @ `ee24b8d03bdd4ed26e22356165fe4809be07ec05`, docs PR
`minion-agent-docs#26` @ `5474cf1fdea345438920500a55f9f7032ff16cdc`) was independently
re-reviewed and **REJECTED FOR RUST IMPLEMENTATION**, targeted (`minion-agent-docs#28`, review
commit `9a8b9632f78a7bf0ba398f9ba4cc314981bdb8d4`, `assurance/layers/09-active-abort-rust-
targeted-rereview.md`): `L09-C001`/`L09-C002`, `L09-R002`, `L09-R003`, and the transform-context
semantic surface portion of `L09-R005` were confirmed correct; `L09-R001`/`L09-R004` were only
partially resolved, and a new finding, `L09-R006`, explained why. See PASS 3 below.

# PASS 3 — remediate L09-R006 (and close the residual L09-R001/R004 gap)

## Re-review reference

The independent Rust targeted re-review of the PASS-2 candidate (see above) rejected it: shared
Layer-09 contract `REJECTED FOR RUST IMPLEMENTATION`, Python Layer 09 `REOPENED`. Full review
text: `assurance/layers/09-active-abort-rust-targeted-rereview.md` on branch
`review/09-active-abort-targeted-pass2` (not reproduced verbatim here).

## Finding, reproduced against pinned Pi and remediated

### L09-R006 — raw waterfall listeners could replace or drop the authoritative signal for later listeners

**Re-review finding:** `PI_PARITY_DEFECT`. PASS 2's own fix for `L09-R001` added `signal` as an
explicit payload argument to `TOOLS_PRE_EXECUTE`/`TOOLS_POST_EXECUTE`, but never protected it from
a listener's own delegation call: a raw listener could call `next_(replacement_args...,
forged_signal)` -- or delegate WITHOUT re-supplying `signal` at all -- and the NEXT listener in the
same waterfall chain would observe the forgery or `None` instead of the run's own original signal.
The review's own executable witness showed later `tools/pre-execute` and `tools/post-execute`
listeners receiving a fabricated replacement signal while execution still succeeded (`is_original=
False is_replacement=True result_error=False` for both events). `spec/tools.md`'s own PASS-2 text
made this an EXPLICIT, documented contract ("must re-supply it... or later listeners will not see
it") rather than an oversight -- contradicting the same document's own "the SAME per-run signal
reaches every consumer" guarantee.

**Pi reproduction:** re-confirmed pinned Pi's own `beforeToolCall(context, signal)`/
`afterToolCall(context, signal)` (`agent-loop.ts:619-627`, `724-736`) and `config.transformContext(
messages, signal)` (`agent-loop.ts:288-292`) all thread the SAME `AbortSignal` instance from
`activeRun.abortController.signal` at every call site -- pinned Pi has no waterfall/middleware
chain at all for these hooks (each is a single, directly-invoked optional callback), so it has no
analogous "a listener redirects what the next listener sees" hazard in the first place. The hazard
is Minion-specific, introduced by choosing a waterfall/delegation design for these seams; closing
it is a Minion-owned integrity guarantee, not itself a Pi behavior being reproduced.

**Classification:** `PI_PARITY_DEFECT` (breaks the "same signal reaches every consumer" contract
`AG-007`/`TOOL-024` both already claimed as certified).

**Remediation:** `signal` (like `tool_call_id`/`tool_name`/`added_tool_names`, `L06-R003`) is
AUTHORITATIVE event metadata, not ordinary payload a listener is free to transform when it
delegates. All three waterfall dispatches that carry it now supply a `normalize_step` closure that
forces the payload tuple's own `signal` slot back to the closure-captured ORIGINAL value at every
listener-to-listener handoff, regardless of what a listener passes when it delegates:

- `tools/execute.py::_preflight` -- new `_restore_signal` closure for `TOOLS_PRE_EXECUTE`;
- `tools/execute.py::_finalize` -- its own pre-existing `_restore` closure (`L06-R003`) extended
  to also force `signal` back to the original, replacing PASS 2's own "tolerate either shape"
  behavior with unconditional restoration, for `TOOLS_POST_EXECUTE`;
- `agent_loop/driver.py::_transform_context` -- new `_restore_signal` closure for
  `AGENT_TRANSFORM_CONTEXT`.

A listener no longer needs to re-supply `signal` when delegating with a replacement result, and
cannot override it for a later listener even by supplying a forgery or omitting it entirely --
`register_after_tool_call_hook`'s own wrapper was simplified accordingly: it no longer re-supplies
`signal` on delegation, relying on `_restore` to preserve it regardless. `spec/tools.md`'s own
"must re-supply or lose it" language and `spec/agent.md`'s consumer/settlement matrix are corrected
to describe the authoritative-restoration guarantee instead, per the review's own explicit
instruction to synchronize spec and manifest.

**RED evidence:** five new regression tests in `tools/test_execute.py` (before-hook redirect,
before-hook drop, after-hook redirect, after-hook drop, and the after-hook wrapper's own
simplification) plus one in `agent_loop/test_active_abort.py`
(`test_a_transform_listener_cannot_redirect_a_later_listener_to_a_replacement_signal`) were each
run against the PASS-2 candidate with the corresponding `normalize_step` argument temporarily
stripped -- all six failed, observing the forged/omitted signal reach the later listener exactly as
the review's own witness described -- before restoring the fix.

**GREEN evidence:** all six pass against the fix, each asserting the later listener observed the
run's own ORIGINAL signal object -- the same one the surrounding request/call actually received --
never the forgery.

## Regression verification for previously-closed findings

`L09-C001`/`L09-C002` (batch algorithms, preflight priority), `L09-R002` (exception
classification), `L09-R003` (signal-only tools), and the transform-context SEMANTIC surface portion
of `L09-R005` (provider-local, non-persistent): unaffected -- the targeted re-review's own ledger
confirmed all as `PROVISIONALLY CLOSED`, and this pass's own diff is additive (a `normalize_step`
closure on three already-existing waterfall dispatches) on top of the SAME dispatch structure, not
a rewrite of it. Every PASS-1/PASS-2 test for these findings re-run unchanged and still passing.
`TOOL-023`/`IR-L06-001` (sequential-preflight/concurrent-execution barrier): unaffected, not
reopened.

## Quality gates (fresh, this pass)

```text
pytest (full suite):                 1089 passed, 19 xfailed (pre-existing, unrelated), 0 failed
coverage (certified src packages):   100.00%, including the extended tools/execute.py and
                                      agent_loop/driver.py
ruff check:                          clean (whole tree)
ruff format --check:                 clean on every file this pass touched; the same pre-existing,
                                      unrelated 7-file drift noted in every earlier pass remains
                                      untouched and out of this pass's ownership scope
mypy (configured scope, src only):   clean, 0 errors, 58 source files
schema validation:                   unaffected, unchanged this pass
conformance/ (full):                 all passing (unchanged -- no canonical scenario added/changed)
manifest parse + unique-ID audit:    79 / 79 unique (AG-007/AG-023/TOOL-024 each gained a PASS-3
                                      paragraph; no new row -- this fix is within their own
                                      already-described surfaces, not a new capability)
placeholder-evidence audit:          active-abort-tool/active-abort-provider/abort-settles-before-
                                      idle remain explicitly unfilled and are NOT cited as
                                      satisfying evidence anywhere in any row touched this pass
```

## Active findings (after this pass)

```text
PI_PARITY_DEFECT              none -- L09-R001/R002/R003/R004/R006 all closed
CONTRACT_ASSURANCE_DEFECT     none -- L09-R005 closed (both halves)
PI_BEHAVIOR_UNCERTAIN         none
unapproved intentional divergence   none
disclosed Minion architectural mapping   AGENT_LIFECYCLE_EVENT/AGENT_PREPARE_NEXT_TURN/
                               AGENT_TURN_STOPPING/AGENT_TRANSFORM_CONTEXT read the signal via
                               instance.signal or an explicit payload argument rather than Pi's own
                               explicit-parameter-everywhere design (spec/agent.md); a single
                               preflight abort checkpoint covers both of pinned Pi's two
                               (spec/tools.md); ToolDefinition.wants_signal is an explicit
                               capability flag rather than Pi's fully-independent optional
                               parameters; normalize_step-based authoritative signal restoration at
                               every waterfall handoff is a Minion-specific integrity guarantee with
                               no Pi analogue (Pi has no waterfall/delegation chain for these hooks)
disclosed Minion-specific constraint   4-parameter arity dispatch required for a tool wanting
                               signal (cannot want signal alone without also declaring update)
Rust cross-language dependency      NOT_IMPLEMENTED -- certified Rust Layer 06's own
                               ToolExecutionSignal seam remains reserved, unexercised; awaiting
                               this candidate's own independent contract review
Layer 10                       NOT STARTED
```

## Verdict

```text
Python Layer 09     CERTIFIED (self-certified; pending independent Rust contract review)
Rust Layer 09         NOT_IMPLEMENTED
shared Layer-09 contract   READY FOR INDEPENDENT RUST CONTRACT REVIEW (remediated candidate; no
                             prior Rust approval carries forward from the rejected PASS-2
                             candidate)
Layer 09 cross-language     NOT CLOSED
Layer 10                     NOT STARTED
```

## Workflow-process retrospective notes (this cycle)

1. An "authoritative restoration" fix applied to one waterfall dispatch does not automatically
   generalize to a sibling dispatch carrying the same value (`L09-R006`): `L06-R003`'s own
   `normalize_step` precedent already existed for `tool_call_id`/`tool_name`/`added_tool_names` on
   `TOOLS_POST_EXECUTE` before this pass, yet PASS 2 added `signal` to THREE waterfall dispatches
   (`TOOLS_PRE_EXECUTE`, `TOOLS_POST_EXECUTE`, `AGENT_TRANSFORM_CONTEXT`) as ordinary payload
   without asking whether the SAME precedent applied to each of them individually. A value that
   needs authoritative-restoration protection on one dispatch needs it evaluated explicitly, seam
   by seam, wherever else it is threaded -- not assumed inherited from a sibling's own protection.
2. Documenting a limitation precisely is not the same as the limitation being acceptable
   (`L09-R006`, echoing `L09-R003`'s own PASS-2 retrospective note): PASS 2's own spec text stated
   the "must re-supply or lose it" behavior clearly and accurately -- it was not an implementation
   bug hiding behind vague prose -- but accurate documentation of an authority gap is still an
   authority gap; the independent review treated the precise disclosure as the defect report
   itself, not as mitigating it.

## Next action (superseded -- see PASS 4 below)

Push this pass's commits to the existing `layer/09-python-shared` branches (both repos); update PR
#17/#26 bodies with the PASS-3 remediation summary and new head SHAs. Update coordination issue
#16 (`minion-agent`): `STATUS: RUST_CONTRACT_REVIEW`, new exact `CODE PR`/`DOCS PR` SHAs, append
the PASS-2 targeted-review rejection reference (`minion-agent-docs#28` @ `9a8b9632f`) to `PRIOR
REVIEW EVIDENCE`, `NEXT_OWNER: Codex`, `NEXT_ACTION: complete a targeted independent Rust re-review
of this PASS-3 candidate against L09-R001/L09-R004/L09-R006 specifically; L09-C001/C002, L09-R002/
R003, and the transform-context portion of L09-R005 remain provisionally closed unless this review
finds a new issue with them`. Then stop. Do not merge any candidate or review-evidence PR. Do not
implement Rust. Do not start Layer 10.

This candidate (code PR `minion-agent#17` @ `ffecd2f9860dc4edd1d605f22ad571f5b36f66c5`, docs PR
`minion-agent-docs#26` @ `7dde9ad3e4596e1d1fb64207de62f7bff00eace1`) was targeted-re-reviewed and
all of `L09-R001`/`L09-R004`/`L09-R006` were `PROVISIONALLY CLOSED` (`minion-agent-docs#29`, review
commit `17c6abdc234f0ced60f543421608679d95744304`, `assurance/layers/09-active-abort-rust-
targeted-rereview-pass3.md`). Per `process/agent-workflow.md` §11.8.8, every blocking finding
being provisionally closed triggers the mandatory
FINAL COMPLETE independent review of one exact candidate SHA pair -- code `ffecd2f9860dc4edd1d
605f22ad571f5b36f66c5`, docs `7dde9ad3e4596e1d1fb64207de62f7bff00eace1` (unchanged since PASS 3;
no new commits were needed to request it). That final review **REJECTED FOR RUST IMPLEMENTATION**
(`minion-agent-docs#30`, review commit `364504a1e1823ff40277da5a4fe08c0dc3e407cb`, `assurance/
layers/09-active-abort-rust-final-contract-review.md`): `L09-C001`-`C003` and `L09-R001`-`R006`
were all confirmed CLOSED at that exact candidate; three NEW findings the targeted reviews never
exercised blocked it -- `L09-R007`/`L09-R008` (`PI_PARITY_DEFECT`) and `L09-R009`
(`CONTRACT_ASSURANCE_DEFECT`). See PASS 4 below.

# PASS 4 — remediate L09-R007, L09-R008, L09-R009 (§11.8.8 final review findings)

## Re-review reference

The mandatory `process/agent-workflow.md` §11.8.8 final complete independent review of the exact
PASS-3 candidate (code `ffecd2f9860dc4edd1d605f22ad571f5b36f66c5`, docs
`7dde9ad3e4596e1d1fb64207de62f7bff00eace1`) rejected it: shared Layer-09 contract `REJECTED FOR
RUST IMPLEMENTATION`, Python Layer 09 `REOPENED`. All checkpoint findings (`L09-C001`-`C003`) and
all prior implementation-review findings (`L09-R001`-`R006`) were independently re-confirmed
CLOSED at this exact candidate -- this pass does not reopen or re-touch any of them. Full review
text: `assurance/layers/09-active-abort-rust-final-contract-review.md` on branch
`review/09-active-abort-final-contract` (not reproduced verbatim here).

## Findings, reproduced against pinned Pi and remediated

### L09-R007 — signal lifetime inverted at public RUNNING/IDLE status transitions

**Re-review finding:** `PI_PARITY_DEFECT`. This row's own rule (`AG-007`) states `signal` is live
for the run's ENTIRE active duration and `None` while idle. `AgentInstance.set_status` emits
`agent/status` and calls `on_status_change` SYNCHRONOUSLY. `AgentLoop._run_wrapped` (PASS 1
through PASS 3) published `set_status(RUNNING)` BEFORE calling `_start_run_signal()`, and
published `set_status(IDLE)` BEFORE calling `_end_run_signal()`. An independent real-loop witness
registered `on_status_change`, read `instance.signal` at each transition, and called
`instance.abort()` when RUNNING was published:

```text
status_observations = [('running', True, None), ('idle', False, False)]
request_signal_aborted = False
after_run_signal_is_none = True
```

The RUNNING observer saw no signal (its own `abort()` call was consequently a no-op, and the
following provider request's own signal was NOT aborted); the IDLE observer saw the JUST-FINISHED
run's still-live signal, not `None`. Both values become correct once each synchronous callback
returns -- the defect is a genuine visibility gap during the callback itself, not merely a stale
final value.

**Pi reproduction:** re-confirmed against pinned Pi source (`ref-repos/pi` @ `b7bb00b`,
`agent.ts`): Pi creates and installs the active run/controller BEFORE setting `isStreaming = true`,
and `finishRun` clears `isStreaming` and THEN removes `activeRun` -- outside Minion's own
synchronous transition-callback seam (which Pi does not have an equivalent of), there is no
externally interleavable point between those writes in Pi's own execution either. Minion's own
status-observer callback is an intentional Minion architectural extension (Pi has no synchronous
"observe every status transition" hook), but once that extension exists, it must see values
consistent with Pi's own "controller-first, isStreaming-second" / "isStreaming-cleared-first,
controller-removed-second" write order, not the inverted order PASS 1-3 implemented.

**Classification:** `PI_PARITY_DEFECT`.

**Remediation:** `AgentLoop._run_wrapped` now calls `self.instance._start_run_signal()` BEFORE
`self.instance.set_status(AgentStatus.RUNNING)`, and `self.instance._end_run_signal()` BEFORE
`self.instance.set_status(AgentStatus.IDLE)` in the `finally` block. This reorders ONLY the signal
calls relative to `set_status` -- the relative order of `set_status`/`streaming_message`/
`error_message` (entry) and `set_status`/`streaming_message`/`pending_tool_calls` (exit) is
unchanged, preserving `AG-008`'s own already-certified write order matching pinned Pi's
`runWithLifecycle`/`finishRun` exactly.

**RED evidence:** the new `test_the_running_status_observer_sees_a_live_signal_and_the_idle_
observer_sees_none` (`agent_loop/test_active_abort.py`), run against the PASS-3 candidate's own
`RUNNING`-then-`_start_run_signal`/`IDLE`-then-`_end_run_signal` ordering (temporarily restored via
revert-and-confirm), fails: the RUNNING observer sees `instance.signal is None`, and the following
request's own signal is confirmed NOT aborted -- reproducing the review's own witness exactly.

**GREEN evidence:** the same test passes against the corrected ordering: the RUNNING observer sees
a live signal and its own `abort()` call lands (confirmed via the following request's `signal.
aborted is True`); the IDLE observer sees `None`.

### L09-R008 — the recommended after-hook helper hides the signal

**Re-review finding:** `PI_PARITY_DEFECT`. Pinned Pi calls `afterToolCall(context, signal)`
unconditionally -- every after-hook receives the active signal. Raw `tools/post-execute` listeners
do (`L09-R001`/`L09-R006`), but the public, exported, documented-as-recommended
`register_after_tool_call_hook` helper still defined its hook as `Callable[[ToolResult], ...]` and
invoked only `hook(result)`. An independent witness registered a helper hook accepting `(result,
signal)` and executed a real tool call with an active signal:

```text
seen = []
is_error = True
content = "hook() missing 1 required positional argument: 'signal'"
```

A caller using the intended, constrained typed-hook API could not observe cancellation through its
after-hook at all -- only a raw listener bypassing the recommended path could.

**Pi reproduction:** re-confirmed `finalizeExecutedToolCall`'s own `config.afterToolCall(context,
signal)` (`agent-loop.ts:724-736`) -- `signal` is unconditionally the hook's own second parameter
in pinned Pi; there is no "the recommended wrapper omits it" carve-out in Pi's own design, since Pi
has no separate wrapper/raw-listener distinction at all (that split is a Minion-specific
architectural extension for composing N hooks -- `TOOL-005`).

**Classification:** `PI_PARITY_DEFECT`.

**Remediation:** new `_hook_wants_signal(hook)` (`tools/execute.py`) inspects `hook`'s own arity:
`>= 2` means the hook declared its own second parameter for `signal`. Unlike `execute()`'s own
`wants_signal`/arity split (`L09-R003`, `TOOL-024`), arity alone is unambiguous here -- a hook has
only ONE optional second slot, with no `update`-shaped alternative it could be confused with, so no
separate declared-capability flag is needed. `register_after_tool_call_hook`'s own `listener` now
calls `hook(result, signal)` when `_hook_wants_signal(hook)`, otherwise `hook(result)` exactly as
before -- every one-parameter hook written before this pass is unaffected.

**RED evidence:** three new tests (`tests/tools/test_post_execute.py`) -- a two-parameter hook
receiving the active signal, the same form receiving `None` while idle, and a one-parameter hook
regression -- run against the PASS-3 candidate's own always-`hook(result)` call (temporarily
restored via revert-and-confirm): the two signal-aware tests fail with the exact `TypeError` the
review's own witness reproduced (surfaced as an error `ToolResult`, since `_execute_and_finalize`
converts an after-hook exception into one), while the one-parameter regression test correctly
stays green throughout, confirming the fix does not merely shift the failure elsewhere.

**GREEN evidence:** all three pass against the arity-aware dispatch.

### L09-R009 — manifest and assurance retained contradictory superseded rules

**Re-review finding:** `CONTRACT_ASSURANCE_DEFECT`. `TOOL-024`'s own opening paragraphs stated the
PASS-1-era "four-parameter-only" design and the PASS-2-era "must re-supply or degrade" design as
though still current, without being clearly marked superseded -- an independent Rust implementer
could reasonably derive conflicting `execute()`/hook APIs from this row alone despite `spec/
tools.md` already containing the correct rule. This assurance document's own PASS-3 "Active
findings" section separately still listed "4-parameter arity dispatch required for a tool wanting
signal (cannot want signal alone without also declaring update)" as an active disclosed
constraint, disproven since PASS 2's own `L09-R003` remediation. `AG-007`'s own opening "DEFERRED
to Layer 09... not Layer 08's ownership" wording, read in isolation, could also be misread as a
current-state claim rather than the Layer-08-era historical text it is.

**Classification:** `CONTRACT_ASSURANCE_DEFECT`.

**Remediation:** `TOOL-024` gained a `CURRENT RULE` summary at the very top of its own `rule:`
text, stating the unambiguous current `execute()` dispatch table and the `signal`-authority
guarantee in one place, and its two superseded PASS-1/PASS-2 claims were annotated IN PLACE
(bracketed `[SUPERSEDED ...]` notes, not deletions -- preserving the historical remediation record
this project's own conventions require) pointing back to that summary and to the specific
later-PASS finding that superseded each one. `AG-007` gained an equivalent `CURRENT STATUS` note
at the top of its own `rule:` text, pointing past its own historical "DEFERRED" wording to its
`disposition: adopted` and the actual Layer-09 rule below. This document's own now-corrected
"Active findings (after this pass)" section (below) replaces the stale PASS-3 line -- it is
current, superseding PASS 3's own copy, the same way each pass's own "Next action" is marked
superseded without rewriting the pass's own historical prose.

**Evidence:** a manifest structural audit (`yaml.safe_load` + unique-ID count) confirms 79/79
unique rows, unchanged, after every wording correction -- this is a documentation-clarity fix, not
a capability/row-count change. No new Python behavior was introduced by this finding; there is no
RED/GREEN pair for it, matching pinned Pi's own review the same way `L09-R009`'s classification
(`CONTRACT_ASSURANCE_DEFECT`, not `PI_PARITY_DEFECT`) already signals.

## Regression verification for previously-closed findings

`L09-C001`-`C003` and `L09-R001`-`R006`: unaffected -- the final review's own ledger independently
re-confirmed all as CLOSED at the exact PASS-3 candidate before finding the three new surfaces
above, and this pass's own diff is additive (a two-line reorder in `_run_wrapped`, one new
arity-check function plus a one-line dispatch change in `register_after_tool_call_hook`, and
documentation-only manifest/assurance wording) on top of the SAME already-certified structures, not
a rewrite of any of them. Every PASS-1/PASS-2/PASS-3 test for these findings re-run unchanged and
still passing. `AG-008`'s own certified `set_status`/`streaming_message`/`error_message`/
`pending_tool_calls` relative write order: unaffected, not reopened -- only the signal calls moved
relative to `set_status`, not relative to each other.

## Quality gates (fresh, this pass)

```text
pytest (full suite):                 1093 passed, 19 xfailed (pre-existing, unrelated), 0 failed
coverage (certified src packages):   100.00%, including the extended tools/execute.py and
                                      agent_loop/driver.py
ruff check:                          clean (whole tree)
ruff format --check:                 clean on every file this pass touched; the same pre-existing,
                                      unrelated 7-file drift noted in every earlier pass remains
                                      untouched and out of this pass's ownership scope
mypy (configured scope, src only):   clean, 0 errors, 58 source files
schema validation:                   unaffected, unchanged this pass (tests/conformance/test_
                                      schema_validation.py + tests/llm/test_tool_schema.py: 196
                                      passed)
conformance/ (full):                 298 passed, 19 xfailed (unchanged -- no canonical scenario
                                      added/changed)
manifest parse + unique-ID audit:    79 / 79 unique (AG-007/TOOL-024 each gained a PASS-4
                                      paragraph plus a CURRENT-RULE/CURRENT-STATUS clarifying note;
                                      no new row -- L09-R007/R008 are within their own
                                      already-described surfaces, and L09-R009 is a wording fix)
placeholder-evidence audit:          active-abort-tool/active-abort-provider/abort-settles-before-
                                      idle remain explicitly unfilled and are NOT cited as
                                      satisfying evidence anywhere in any row touched this pass
```

## Active findings (after this pass)

```text
PI_PARITY_DEFECT              none -- L09-R001/R002/R003/R004/R006/R007/R008 all closed
CONTRACT_ASSURANCE_DEFECT     none -- L09-R005/R009 closed
PI_BEHAVIOR_UNCERTAIN         none
unapproved intentional divergence   none
disclosed Minion architectural mapping   AGENT_LIFECYCLE_EVENT/AGENT_PREPARE_NEXT_TURN/
                               AGENT_TURN_STOPPING/AGENT_TRANSFORM_CONTEXT read the signal via
                               instance.signal or an explicit payload argument rather than Pi's own
                               explicit-parameter-everywhere design (spec/agent.md); a single
                               preflight abort checkpoint covers both of pinned Pi's two
                               (spec/tools.md); ToolDefinition.wants_signal is an explicit
                               capability flag rather than Pi's fully-independent optional
                               parameters; normalize_step-based authoritative signal restoration at
                               every waterfall handoff, and register_after_tool_call_hook's own
                               arity-based signal delivery, are Minion-specific integrity/
                               convenience mechanisms with no direct Pi analogue (Pi has no
                               waterfall/delegation chain or wrapper/raw-listener split for these
                               hooks)
disclosed Minion-specific constraint   none currently active -- the PASS-1-era "4-parameter arity
                               dispatch required for signal-only tools" constraint this document
                               previously listed here was disproven by PASS 2's own L09-R003
                               remediation (`wants_signal` makes a genuinely 3-parameter
                               signal-only tool representable) and should not have still appeared
                               in PASS 3's own copy of this section -- removed here per L09-R009
Rust cross-language dependency      NOT_IMPLEMENTED -- certified Rust Layer 06's own
                               ToolExecutionSignal seam remains reserved, unexercised; awaiting
                               this candidate's own independent contract review
Layer 10                       NOT STARTED
```

## Verdict

```text
Python Layer 09     CERTIFIED (self-certified; pending independent Rust contract review)
Rust Layer 09         NOT_IMPLEMENTED
shared Layer-09 contract   READY FOR INDEPENDENT RUST CONTRACT REVIEW (remediated candidate; no
                             prior Rust approval carries forward from the rejected PASS-3
                             candidate -- the §11.8.8 final review found new blocking surfaces the
                             convergence-targeted reviews had no mandate to exercise)
Layer 09 cross-language     NOT CLOSED
Layer 10                     NOT STARTED
```

## Workflow-process retrospective notes (this cycle)

1. `process/agent-workflow.md` §11.8.8's own final complete review is not a rubber stamp on top of
   provisionally-closed targeted findings -- it exists precisely because §11.8.7's own targeted
   re-reviews deliberately scope themselves to "open finding(s) + semantic dependencies touched by
   the fix + previously-closed high-risk regressions affected by the change," not a full re-audit
   of the whole layer against Pi from scratch. `L09-R007` (status/signal boundary timing) and
   `L09-R008` (the helper hook's own missing signal parameter) were both genuine, PRE-EXISTING
   defects present since PASS 1/PASS 2 respectively -- neither was introduced by PASS 3's own
   `L09-R006` fix, and neither was a "semantic dependency" or "regression" a PASS-3-scoped targeted
   review would have had any reason to re-examine. Only a review with an explicit mandate to
   re-derive the COMPLETE consumer/settlement surface from Pi source, independent of what the most
   recent targeted finding named, was positioned to find them.
2. This is the SAME general shape of gap `L09-R005`'s own PASS-1 retrospective note already
   recorded for the checkpoint-vs-full-review distinction (a checkpoint closing named findings is
   not the same guarantee as "this surface's full consumer list is complete") -- §11.8.8
   generalizes that lesson to the convergence-targeted-review-vs-final-review distinction, and this
   pass is a second, independent confirmation of the same general shape of gap recurring at a
   different review-scoping boundary. A project relying on scoped/targeted re-reviews for
   efficiency should expect this class of gap to recur at each such boundary and should treat the
   final complete review as load-bearing, not ceremonial, every time.
3. A stale claim can persist for multiple passes even after the code it describes has been fixed
   (`L09-R009`, echoing `L09-R003`'s own PASS-2 note and `L09-R006`'s own PASS-3 note about
   documenting-a-limitation-precisely-is-not-the-same-as-acceptable): PASS 2 fixed the actual
   `execute()` capability gap `L09-R003` named, but PASS 3's own "Active findings" section still
   copied forward PASS 1's original "4-parameter arity dispatch required" language into ITS OWN
   "current" section without checking whether it remained true. Carrying forward a fixed-findings
   list from the previous pass's own template is not the same as re-verifying each line is still
   accurate.

## Next action

Push this pass's commits to the existing `layer/09-python-shared` branches (both repos); update PR
#17/#26 bodies with the PASS-4 remediation summary and new head SHAs. Update coordination issue
#16 (`minion-agent`): `STATUS: RUST_CONTRACT_REVIEW`, new exact `CODE PR`/`DOCS PR` SHAs, append
the PASS-3 §11.8.8 final-review rejection reference (`minion-agent-docs#30` @ `364504a1e`) to
`PRIOR REVIEW EVIDENCE`, `NEXT_OWNER: Codex`, `NEXT_ACTION: complete a targeted independent Rust
re-review of this PASS-4 candidate against L09-R007/L09-R008/L09-R009 specifically; L09-C001-C003
and L09-R001-R006 remain provisionally closed unless this review finds a new issue with them. Per
§11.8.8, once this targeted re-review also provisionally closes its findings, ANOTHER final
complete review of that exact candidate is required before certification -- this is not optional
and does not shortcut back to a single targeted-review approval`. Then stop. Do not merge any
candidate or review-evidence PR. Do not implement Rust. Do not start Layer 10.
