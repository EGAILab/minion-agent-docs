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

## Next action

Push this pass's commits to the existing `layer/09-python-shared` branches (both repos); update PR
#17/#26 bodies with the PASS-2 remediation summary and new head SHAs. Update coordination issue
#16 (`minion-agent`): `STATUS: RUST_CONTRACT_REVIEW`, new exact `CODE PR`/`DOCS PR` SHAs, append
the PASS-1 rejection reference (`minion-agent-docs#27` @ `0a781d3f6`) to `PRIOR REVIEW EVIDENCE`,
`NEXT_OWNER: Codex`, `NEXT_ACTION: complete a full independent Rust contract review of this PASS-2
candidate against L09-R001 through L09-R005 specifically; L09-C001/C002/C003 remain provisionally
closed unless this review finds a new issue with them`. Then stop. Do not merge any candidate or
review-evidence PR. Do not implement Rust. Do not start Layer 10.
