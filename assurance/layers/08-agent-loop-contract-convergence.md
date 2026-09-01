# Layer 08 — Contract Convergence (L08-R002 / L08-R004)

Entered per `process/agent-workflow.md` §11.8. Trigger: the same material finding
(`L08-R002`/`L08-R004`, `tool_execution_update` dispatch-timing semantics) has survived five
consecutive independent reviews (PASS-4 through PASS-8 rejections), far exceeding both the
"same finding survives two reviews" and "layer accumulates three rejected reviews" triggers.

```text
STATUS
    CONTRACT_CONVERGENCE

OPEN_SURFACE
    L08-R002 (PI_PARITY_DEFECT), L08-R004 (CONTRACT_ASSURANCE_DEFECT) --
    AGENT_LIFECYCLE_EVENT serial listener-dispatch suspension timing
```

## Characterization (source: PASS-8 independent Rust re-review, docs PR #10 @ `2818dd8`)

The PASS-8 rejection report already constitutes a de facto characterization pass — it contains an
independent Pi audit, a language-neutral observable rule, minimal executable witnesses (two
focused probes, one passing, one failing with exact traces), current-candidate failure evidence,
and implementation constraints. Reproduced and independently re-verified here, not merely copied.

### Open findings

- `L08-R002` (`PI_PARITY_DEFECT`): Minion's `AGENT_LIFECYCLE_EVENT` dispatch, driven eagerly via
  `asyncio.eager_task_factory`, runs every synchronous listener in a chain to completion inline,
  with no suspension between them. Pinned Pi's own serial listener loop suspends after EVERY
  listener -- including a fully synchronous one -- before advancing to the next.
- `L08-R004` (`CONTRACT_ASSURANCE_DEFECT`): `spec/agent.md`'s `ToolExecutionUpdate` bullet and
  `AG-009` claim exact reproduction of pinned Pi's dispatch timing; this is false for two or more
  synchronous listeners. The PASS-8 regression test (`test_on_execution_update_starts_
  synchronously_but_does_not_block_the_tool`) uses exactly one listener and cannot discriminate
  single- from multi-listener timing.

### Pi symbols audited (re-confirmed directly against `ref-repos/pi` @ `b7bb00b`, this pass)

- `packages/agent/src/agent.ts::processEvents`, lines 544-591 -- read in full, this pass, not
  merely re-cited: the reducer switch (544-582) runs synchronously, then
  `for (const listener of this.listeners) { await listener(event, signal); }` (588-590).
- `packages/agent/src/agent-loop.ts::executePreparedToolCall`, lines 670-711 (re-confirmed
  unchanged from PASS 7/8's own audits).

### Observable rule (language-neutral, per workflow §10)

Serial listener dispatch for one event advances one listener at a time; after EACH listener's own
invocation completes (regardless of whether that listener itself performed any async work), the
dispatching coroutine/task yields at least one scheduling turn to its host runtime's event loop
before invoking the next listener. A caller that triggered the dispatch synchronously (the tool's
own `update()`) resumes as soon as the dispatch reaches ITS OWN first such yield -- i.e., after
listener 1's own synchronous work, not after the whole chain.

This is a general property of `await`/`async` in JavaScript (an `await` expression always defers
its continuation by at least one microtask turn, even for an already-settled/non-Promise operand)
that Python's own `await` does not share (awaiting a coroutine that itself never performs a
genuine suspension completes synchronously, with zero scheduler turns). The rule is a real,
Pi-observable serial-dispatch property, not an implementation artifact of either language.

### Minimal executable witnesses

Reproduced independently, this pass, before proposing a fix (workflow §9.3):

```python
# two-listener probe against Minion's real EventBus.serial + eager_task_factory (current, FAILS):
order = ['listener-1', 'listener-2', 'tool-continued']   # observed
# required (matches PASS-8's own pinned-Pi focused probe):
order = ['listener-1', 'tool-continued', 'listener-2']
```

Standalone verification of the proposed fix (below), run before integrating it:

```python
import asyncio

order = []

def listener1(event): order.append('listener-1')
def listener2(event): order.append('listener-2')

async def _call(cb, *args):
    result = cb(*args)
    if hasattr(result, '__await__'):
        return await result
    return result

async def serial_yielding(callbacks, *args):
    for cb in callbacks:
        await _call(cb, *args)
        await asyncio.sleep(0)   # the added, unconditional per-listener yield

async def dispatch(event):
    await serial_yielding([listener1, listener2], event)

async def main():
    loop = asyncio.get_running_loop()
    task = asyncio.eager_task_factory(loop, dispatch('update'))
    order.append('tool-continued')
    await task

asyncio.run(main())
assert order == ['listener-1', 'tool-continued', 'listener-2']   # PASSES
```

### Current candidate failures

PASS-8 candidate (code `c20376c`, docs `af207e1`): `EventBus.serial` (`runtime/events.py`) has no
per-listener yield of any kind -- `_call(callback, *args)` returns synchronously for a synchronous
`callback`, and `serial()`'s own `for callback in self._chain(...): result = await self._call(...)`
never suspends between iterations unless a listener itself genuinely awaits something. Confirmed
by direct source read, this pass (`runtime/events.py:131-157`).

### Implementation constraints (from the PASS-8 review, independently affirmed)

- Do not globally alter `EventBus.serial`'s own certified default behavior -- every existing
  caller besides `AGENT_LIFECYCLE_EVENT` must observe zero change.
- Do not encode Python/JS mechanics into the shared contract -- the fix must express "yield after
  every listener" as an observable dispatch property, not "call `asyncio.sleep(0)`" as if that
  were itself the rule.
- Any change to `runtime/events.py` (a certified Layer-05 module) requires the narrow
  post-certification delta audit this project's own conventions already require for a
  lower-layer touch, confirming no other certified consumer's own observable behavior changes.

### Out of scope / deferred

- `EventBus.parallel`/`waterfall` dispatch modes: untouched: neither is Pi's own serial listener
  loop, and no open finding names them.
- Rust implementation: not attempted; the language-neutral rule above is what Rust must satisfy,
  not any Python-specific primitive.

## Challenge pass (Claude, implementation/shared-contract owner)

- **Is the Pi source mapping correct?** Yes -- independently re-read `agent.ts:544-591` this
  pass, byte for byte; the `for` loop with `await listener(...)` inside is exactly as described.
- **Is the behavior matrix complete enough to distinguish realistic wrong implementations?** The
  two-probe evidence (1-listener pass, 2-listener fail) is sufficient to prove the defect and to
  validate a fix, but the PERMANENT regression suite needs a 2-listener test asserting the full
  three-step order, plus confirmation that a 3rd, 4th, ... listener each gets its own yield (not
  just "listener 2 is deferred once") -- added to the acceptance-witness list below.
- **Are any cases implementation mechanics rather than observable semantics?** The `asyncio.sleep(0)`
  primitive itself is Python mechanics; the OBSERVABLE rule (stated above, language-neutrally) is
  what belongs in spec/manifest text. The convergence artifact keeps both, clearly separated.
- **Does the proposed fix silently reopen a lower certified layer?** It touches `runtime/events.py`
  (Layer 05, certified), which is why this is flagged explicitly rather than folded silently into a
  Layer-08-only pass. The proposed design (an additive, default-`False` `yield_after_each` keyword
  argument on `EventBus.serial`, used only by `AgentLoop._dispatch_agent_event`) preserves every
  existing `serial()` caller's own certified behavior exactly -- verified by inspection: every other
  `serial()` call site in the codebase omits the new keyword, so its default (`False`, current
  behavior, no yield) applies unchanged. This still requires the narrow delta audit named above
  before claiming Layer-08 approval, per the PASS-8 review's own instruction.
- **Can both Python and Rust implement the rule idiomatically?** Python: an explicit
  `await asyncio.sleep(0)` (or the runtime's own equivalent single-tick yield) after each listener,
  gated by an opt-in flag so unrelated `EventBus.serial` callers are unaffected. Rust: an explicit
  `.await` on a single-poll-ready future (e.g. `tokio::task::yield_now()` or equivalent) after each
  listener in whatever serial-dispatch loop Rust's own Agent seam eventually implements -- the
  review's own suggestion, independently plausible.
- **Are all previous review findings represented by an executable or documentary acceptance
  criterion?** Yes for everything already closed (`L08-R001`, `R003`, `R005`-`R010`, unaffected by
  this fix); the two currently-open findings get the acceptance witnesses below.

## Convergence contract checkpoint

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION

OPEN FINDINGS
    L08-R002, L08-R004

DESIGN
    EventBus.serial (runtime/events.py) gains an additive, keyword-only
    `yield_after_each: bool = False` parameter. When True, the dispatch loop
    awaits a single-tick scheduler yield (`asyncio.sleep(0)`) after EVERY
    listener's own invocation, unconditionally -- matching pinned Pi's own
    `for (const listener of listeners) { await listener(event, signal); }`,
    where JS's `await` always defers at least one microtask turn regardless
    of whether the listener itself performed real async work. Every existing
    `serial()` call site keeps the default (False); only
    AgentLoop._dispatch_agent_event (agent_loop/driver.py) passes
    `yield_after_each=True` for AGENT_LIFECYCLE_EVENT specifically.

ACCEPTANCE WITNESSES
    - a new two-listener test proving `[listener-1, tool-continued, listener-2]`
      through the real ToolExecutionUpdate seam (extends
      test_on_execution_update_starts_synchronously_but_does_not_block_the_tool
      or a sibling test), matching the PASS-8 review's own focused probe exactly
    - a 3-listener variant confirming each listener gets its own yield, not
      only the first
    - existing single-listener test (unchanged, still required)
    - a regression test on an unrelated existing `EventBus.serial` caller
      confirming zero observable behavior change with the new parameter
      omitted (the narrow lower-layer delta audit's own evidence)
    - existing pending-state, listener-failure-propagation, join-before-end,
      and live start/end tests all re-run unchanged

NORMATIVE DELTAS
    spec/agent.md ToolExecutionUpdate bullet (state the corrected,
    per-listener-yield rule; stop claiming exact reproduction without it);
    AG-009 manifest row (new paragraph, PASS-9); runtime/events.py's own
    EventBus.serial docstring (document the new parameter and its own
    certified default-False backward-compatibility guarantee)

NEXT_OWNER
    Claude (implementation pass, PASS 9)
```

This is not final contract approval. It records that the remaining observable surface is
sufficiently characterized for one coherent implementation attempt, per workflow §11.8.5.

## Implementation pass (PASS 9)

Completed per workflow §11.8.6. Full detail (implementation, delta audit, RED/GREEN evidence,
regression verification, quality gates) is in `assurance/layers/08-agent-loop-python.md`'s own
"# PASS 9" section, not duplicated here. Summary: `EventBus.serial` gained the agreed additive
`yield_after_each: bool = False` parameter exactly as designed above; `AgentLoop._dispatch_agent_
event` is the one caller that opts in; the standalone verification scripts above were re-confirmed
against the real implementation (not merely the standalone reproduction) via new permanent tests at
both the `EventBus` and `AgentLoop` levels, including a two-listener test through the real
production seam that fails against the reverted implementation and passes against PASS 9.

```text
STATUS
    L08-R002, L08-R004 -- awaiting targeted re-review (workflow §11.8.7)

CANDIDATE
    code PR #13 (new SHA after PASS 9) / docs PR #3 (new SHA after PASS 9)

NEXT_OWNER
    Codex (targeted finding-closure review, workflow §11.8.7 -- not a full
    release-level layer audit)
```
