# Layer 09 — Active abort/cancellation, Python implementation

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

## Next action

Push this pass's commits to new short-lived candidate branches in both repos (`layer/09-python-
shared`), open paired PRs, create/update the Layer-09 coordination issue's own `CODE PR`/`DOCS PR`/
`STATUS: RUST_CONTRACT_REVIEW`/`NEXT_OWNER: Codex` state, and request a full independent Rust
contract review of the exact candidate SHAs against this document, `assurance/layers/09-active-
abort-contract-checkpoint.md`, and the manifest rows above (`AG-007`, `AI-027`, `TOOL-024`). Then
stop. Do not implement Rust. Do not start Layer 10.
