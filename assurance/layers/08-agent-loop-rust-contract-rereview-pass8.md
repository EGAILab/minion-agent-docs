# Layer 08 — Independent Rust Contract Re-review (PASS 8)

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

PASS 8 correctly fixes the PASS-7 first-listener timing defect: the first listener's synchronous
prefix now runs before the tool continues. The exact Agent listener seam remains observably
over-eager for two or more synchronous listeners, however. Pinned Pi's `await listener(...)`
suspends after listener 1 even when it returns a non-promise value; Minion's eagerly-driven
`EventBus.serial` continues through every synchronous listener without a real suspension. Thus
PASS 8 produces `listener-1, listener-2, tool-continued`, while pinned Pi produces
`listener-1, tool-continued, listener-2`.

## Exact review target

| Item | Exact remote state reviewed |
|---|---|
| Code PR | `EGAILab/minion-agent#13` @ `c20376cba8dbae7ca795f747cb0b126ab39f7a1e` |
| Docs PR | `EGAILab/minion-agent-docs#3` @ `af207e1602b68cf92a2400b50ebe768f9e7d64be` |
| Pinned Pi | `b7bb00b936dbe21b8e160b3e89efdec361846699` |
| PASS-2 rejection | docs PR #4 @ `88a6aa6c1c1994026001c60045d4c55c00331a52` |
| PASS-3 rejection | docs PR #5 @ `a64b78ad2507b142ca7cda911b8968aa61af6a20` |
| PASS-4 rejection | docs PR #6 @ `65e665f28e29ebe6cf8deb792b206c108d32b1a6` |
| PASS-5 rejection | docs PR #7 @ `8875ebce5b20b8c67d6d86350464fb71107d1204` |
| PASS-6 rejection | docs PR #8 @ `752754ade96fc9c2c84eaafd61e671840373e82e` |
| PASS-7 rejection | docs PR #9 @ `5713b393a8870882c500f193c9976a6b0465ff02` |

Issue `EGAILab/minion-agent#12` recorded the same PASS-8 heads, `STATUS =
RUST_CONTRACT_REVIEW`, and `NEXT_OWNER = Codex`. Both candidate PRs were open, Ready for Review,
and unmerged. The main docs checkout's unrelated Phase-5 modification was preserved untouched.

## Independent Pi audit

Reviewed pinned Pi before candidate implementation:

- `packages/agent/src/agent-loop.ts::executePreparedToolCall` (`670-711`);
- `packages/agent/src/agent.ts::processEvents` (`544-591`);
- `packages/agent/src/types.ts::AgentEvent`, `AgentEventListener`;
- surrounding execution/finalization and run-failure paths previously audited for this layer.

Pi's synchronous update callback directly calls async `emit/processEvents` and stores the returned
promise. JavaScript begins the async function body immediately. `processEvents` performs its
reducer, enters the listener loop, invokes listener 1, and then reaches `await listener(...)`.
Crucially, JavaScript `await` schedules continuation as a microtask even when listener 1 returned
`void`; listener 2 is therefore not invoked in the original update callback stack. Tool execution
resumes after update returns, and listener 2 follows in the microtask continuation. Pi later joins
the full event promise before finalization/end.

## PASS-8 repair independently verified

`_execute_and_finalize.update()` now uses `asyncio.eager_task_factory` directly. The revised
single-listener test is genuinely discriminating and passes. A focused exact-candidate probe
confirmed:

```text
listener-entered
tool-continued
listener-resumed
```

This closes the specific PASS-7 defect. The existing join-before-finalize, pending-call visibility,
listener-failure propagation, late-update suppression, and live start/end behavior also remain
correct. A focused two-call production probe produced callback order and listener-entry order
`A1, B1, A2`, confirming capture/replay has not returned.

## Remaining L08-R002 defect — N-listener suspension boundary

Minion's Agent seam is `EventBus.serial`. It awaits `_call(callback, ...)`; `_call` invokes a
synchronous callback and returns without suspending. Under `eager_task_factory`, the entire chain
of synchronous callbacks can therefore run inline before task construction returns.

Focused probe using the real `EventBus.serial` path:

```text
PASS-8 Minion
    listener-1
    listener-2
    tool-continued

pinned JavaScript processEvents
    listener-1
    tool-continued
    listener-2
```

This is Pi-observable: the synchronous tool may inspect state changed by listener 2 immediately
after `update()` returns. Pi does not expose that state change until the promise continuation;
PASS 8 does. The same distinction affects which listener prefixes can run before another parallel
tool callback fires.

This is not a request to copy Python or JavaScript mechanics into Rust. The language-neutral rule
is that update dispatch begins synchronously through listener 1, listener completion is joined
later, and serial listener advancement occurs across the same asynchronous suspension boundary Pi
creates for every `await listener`. Rust can implement that rule with an explicit future/yield
boundary.

Classification: `PI_PARITY_DEFECT`; `L08-R002` remains open.

## Remaining L08-R004 defect — evidence still under-discriminates the chain

The revised test contains only one listener. It proves eager entry and non-blocking suspended
completion, but cannot distinguish correct Pi listener-loop behavior from PASS 8's over-eager
multi-listener chain. There is no permanent two-listener test checking the tool continuation
between listener 1 and listener 2. There is also still no permanent two-call parallel test, though
the independent review probe confirms the current implementation's callback order.

The normative spec says Minion matches Pi's serial listener delivery exactly and calls
`eager_task_factory` an exact reproduction. That statement is false for multiple synchronous
listeners. An independent Rust implementer following Pi may insert the listener-to-listener
suspension; one mechanically following the Python description may not. The contract/evidence is
therefore not yet sufficient for approval.

Classification: `CONTRACT_ASSURANCE_DEFECT`; `L08-R004` remains open.

## Finding ledger

| Finding | PASS-8 status |
|---|---|
| `L08-R001` snapshot / prepare-next-turn | **CLOSED — no regression** |
| `L08-R002` live lifecycle/update delivery | **STILL OPEN — N-listener timing** |
| `L08-R003` streaming partial fidelity | **CLOSED — no regression** |
| `L08-R004` normative coherence/evidence | **STILL OPEN — single-listener evidence insufficient** |
| `L08-R005` no turn cap | **CLOSED — no regression** |
| `L08-R006` first-turn steering | **CLOSED — no regression** |
| `L08-R007` prompt forms | **CLOSED — no regression** |
| `L08-R008` represented terminal messages | **CLOSED — no regression** |
| `L08-R009` / `L08-R010` boundary stop | **CLOSED — mechanism remains absent** |

## Manifest / canonical audit

AG-001 through AG-010 and AG-021 were rechecked. AG-007 remains correctly deferred to Layer 09;
AG-020 and AG-022 remain absent. AG-009 fails only for the N-listener update timing and its evidence
claim. Other rows remain coherent with the previously audited state machine. Placeholder scenarios
are explicitly deferred and are not counted as satisfying Layer-08 evidence.

Manifest structure contains 76 rows and 76 unique IDs. The canonical runner remains thin and does
not simulate update dispatch.

## Lower-layer / Rust feasibility

No certified lower-layer observable contract is proven to require reopening. PASS 8's additive
Layer-06 update observer hook remains a viable boundary. The correction may require an
Agent-specific serial dispatch adapter or a narrowly audited additive Runtime facility so that a
synchronous listener is followed by an explicit suspension before the next listener. It must not
globally alter certified EventBus behavior without the normal lower-layer delta audit.

Rust can implement the language-neutral Pi rule idiomatically using a synchronously-started event
future and explicit serial suspension points. Rust Layer 08 remains unimplemented in this review.

## Fresh evidence and gates

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

focused single-listener PASS-8 probe
    PASS — listener-entered, tool-continued, listener-resumed

focused two-call callback-order probe
    PASS — callbacks/listener entries A1, B1, A2

focused two-listener Pi comparison
    FAIL — Minion runs listener 2 before tool continuation; Pi runs it after
```

Green general gates do not override the focused parity failure.

## Findings

```text
PI_PARITY_DEFECT
    L08-R002 STILL OPEN
        eager task start runs every synchronous Minion listener inline
        pinned Pi yields after listener 1 before advancing the serial chain

CONTRACT_ASSURANCE_DEFECT
    L08-R004 STILL OPEN
        spec overclaims exact listener delivery
        evidence has no discriminating two-listener lifecycle test

PI_BEHAVIOR_UNCERTAIN
    none

PARITY_CONSTRAINED_RISK
    none

PARITY_NEUTRAL_HARDENING
    remove superseded PASS-6 prose from current production docstrings
    add permanent two-call update-order regression coverage
```

## Narrow remediation

1. Preserve synchronous entry into listener 1, but introduce Pi's asynchronous suspension before
   advancing to listener 2 when listener 1 returns synchronously.
2. Add a real two-listener test proving `listener-1, tool-continued, listener-2`.
3. Retain tests for single-listener eager entry, pending state, failure propagation, join-before-end,
   and real two-call callback order.
4. Correct spec/AG-009's exactness claim and evidence pointers to the final implemented rule.
5. If Runtime dispatch is changed rather than an Agent-specific adapter being used, perform the
   required narrow post-certification delta audit before claiming Layer-08 approval.

Any changed candidate SHA requires another complete independent Rust contract review.

## Scope confirmation

```text
Rust Layer 08 implementation modified
    NO

Python/shared candidate branches modified
    NO

Layer 09 started
    NO
```
