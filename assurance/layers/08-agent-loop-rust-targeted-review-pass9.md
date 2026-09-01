# Layer 08 — Rust targeted contract review, PASS 9

## Review status

This is the targeted finding-closure review authorized by `process/agent-workflow.md` §11.8.7
after contract convergence. It is not the final complete Layer-08 contract review required by
§11.8.8.

```text
code PR #13
    a5a0fdc1a95d7e8f7f347de4bf9569d07abb426a

docs PR #3
    eb4965d5344c14aeb5da030341602a60ef2f0386

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699

review scope
    L08-R002
    L08-R004
    EventBus.serial dependency delta
    affected tool-update lifecycle regressions

Rust implementation
    NOT STARTED

Layer 09
    NOT STARTED
```

The coordination issue was independently checked before review: issue #12 named these exact PR
heads, `STATUS = RUST_CONTRACT_REVIEW`, `NEXT_OWNER = Codex`, and requested a targeted §11.8.7
review. Both candidate PRs were open, Ready for Review, and unmerged.

## Authority and source witness

The review used the required order: pinned Pi, the convergence contract and normative spec,
manifest, executable evidence, dependency implementation, then Python assurance. Python was not
used as the semantic oracle.

Pinned Pi was re-read at the exact pinned commit:

- `packages/agent/src/agent.ts::processEvents` reduces state and then performs a registration-order
  `for` loop with `await listener(event, signal)` after every listener invocation.
- `packages/agent/src/agent-loop.ts::executePreparedToolCall` starts `emit(...)` from the tool's
  synchronous update callback, retains the returned promise, and joins all update promises after
  `execute()` settles but before finalization and `tool_execution_end`.

The discriminating observable consequence is the convergence witness: with two synchronous Agent
lifecycle listeners and a tool that continues immediately after calling `update()`, pinned Pi's
order is:

```text
listener-1
tool-continued
listener-2
```

JavaScript begins the async dispatch synchronously through listener 1, while each `await` defers
the dispatch continuation before the next listener. This is the language-neutral rule Rust must
preserve; `asyncio.eager_task_factory` and `asyncio.sleep(0)` are Python realization details, not
the Rust contract.

## Convergence checkpoint review

`assurance/layers/08-agent-loop-contract-convergence.md` contains the required characterization,
challenge pass, agreed contract checkpoint, acceptance witnesses, and lower-layer dependency
constraints. The implemented design matches that checkpoint exactly:

- `EventBus.serial` adds keyword-only `yield_after_each: bool = False`;
- the opt-in path yields after every listener, including a synchronous listener and the final
  listener;
- `AgentLoop._dispatch_agent_event` is the only production caller opting in;
- `AgentLoop._should_stop` and the generic conformance dispatch retain the default behavior;
- parallel and waterfall dispatch are untouched.

The implementation neither buffers nor replays update lifecycle events. Tool update delivery still
starts eagerly at callback time, remains non-blocking to the tool after the first listener boundary,
and is joined before finalization/end.

## Finding ledger

### L08-R002 — Agent lifecycle listener suspension timing

**Previous blocker:** PASS 8 began update dispatch at callback time but an eagerly driven Python
serial chain ran all synchronous listeners inline. It produced
`listener-1, listener-2, tool-continued`, unlike pinned Pi.

**PASS-9 change:** Agent lifecycle serial dispatch opts into an unconditional scheduling boundary
after each listener. The tool-update callback retains the already-correct eager start and trailing
join.

**Independent evidence:**

- the real AgentLoop two-listener test produces
  `listener-1, tool-continued, listener-2`;
- the EventBus three-listener witness proves the boundary occurs after every listener, not only
  once after listener 1;
- the pre-existing one-listener eager-start witness remains green;
- pending-tool state remains visible during update delivery;
- a rejecting update listener remains a genuine run failure and prevents finalization/end;
- the full suite is green with 100% configured coverage.

```text
L08-R002
    PROVISIONALLY CLOSED
    @ code a5a0fdc1a95d7e8f7f347de4bf9569d07abb426a
    @ docs eb4965d5344c14aeb5da030341602a60ef2f0386
```

### L08-R004 — contract/evidence overstated exact timing

**Previous blocker:** the normative contract claimed exact Pi timing while evidence covered only
one listener and could not discriminate PASS 8's over-eager multi-listener behavior.

**PASS-9 change:** `spec/agent.md`, `spec/runtime.md`, and AG-009 state the per-listener suspension
boundary. The permanent evidence cross-product covers one listener, two listeners through the real
AgentLoop seam, three listeners at the dependency seam, and default-off behavior.

The normative rule is implementable independently in Rust: a Rust Agent lifecycle dispatch loop
can await each listener and explicitly yield once before advancing, without copying Python's task
factory or event-loop mechanism. The runner does not synthesize this ordering.

```text
L08-R004
    PROVISIONALLY CLOSED
    @ code a5a0fdc1a95d7e8f7f347de4bf9569d07abb426a
    @ docs eb4965d5344c14aeb5da030341602a60ef2f0386
```

## Certified dependency delta

The change touches the previously certified Runtime EventBus. The delta is narrow and opt-in.
Every `.serial(` call site was enumerated. Only `_dispatch_agent_event` supplies
`yield_after_each=True`; all other production/conformance consumers omit it and retain the prior
default. New Runtime tests positively prove both default-off behavior and the opt-in two/three
listener behavior. No existing dispatch mode, ordering rule, error rule, or return rule changes for
default consumers.

This does not require reopening the existing Runtime behavior for its current consumers. Rust will
need the same opt-in semantic capability when Layer 08 is implemented, but no Rust code is changed
or approved by this review.

## Verification

Fresh reviewer commands against the exact code candidate produced:

```text
focused semantic witnesses
    8 selected tests passed
    pytest's configured global coverage gate then failed, as expected for a selected subset

full pytest suite
    exit 0
    100.00% configured coverage
    19 expected xfails visible in progress output

ruff check .
    PASS

mypy src
    PASS — 57 source files

ruff format --check (four PASS-9-touched files)
    PASS — 4 files already formatted

full ruff format --check .
    reports 7 pre-existing, PASS-9-untouched files as reformattable
```

The full-suite run includes schema and conformance tests. The whole-tree format observation is not
a semantic finding against L08-R002/R004 and none of the seven reported files belongs to PASS 9;
it is recorded rather than hidden. PASS-9-touched files are format-clean.

## Contract-quality answers

```text
runner simulates listener scheduling
    NO

production owns eager start, per-listener suspension, join, and failure propagation
    YES

default Runtime consumers changed
    NO

Python-specific mechanism made normative for Rust
    NO

Rust can implement the observable rule idiomatically
    YES

active PI_PARITY_DEFECT in targeted surface
    none

active CONTRACT_ASSURANCE_DEFECT in targeted surface
    none

active PI_BEHAVIOR_UNCERTAIN in targeted surface
    none
```

## Targeted verdict

```text
L08-R002
    PROVISIONALLY CLOSED @ exact PASS-9 candidate

L08-R004
    PROVISIONALLY CLOSED @ exact PASS-9 candidate

shared Layer-08 contract
    NOT YET FINALLY APPROVED

Python Layer 08
    self-certified candidate; final independent review pending

Rust Layer 08
    NOT_IMPLEMENTED

Layer 08 cross-language
    NOT CLOSED

Layer 09
    NOT STARTED
```

Per `process/agent-workflow.md` §11.8.8, the next action is exactly one final complete independent
Layer-08 contract review of these exact candidate SHAs. This targeted verdict must not be carried
forward if either candidate head changes.
