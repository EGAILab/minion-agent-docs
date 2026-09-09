# Layer 09 active abort — PASS 10 targeted Rust re-review

## Exact target

- code PR `EGAILab/minion-agent#17`:
  `3c0a916c97f02d0d29d8d8d08095f53848074d29`;
- docs PR `EGAILab/minion-agent-docs#26`:
  `8dc2b59042eac4387b72264682ab7b03d3c43c73`;
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`;
- L09-R018 final-review rejection: docs PR #38 at
  `a5f6316e5d46d773160acd34707dea5018ea27ee`;
- convergence revision-2 agreement: docs PR #40 at
  `15d5173d5d7a18c35f7841fe42d533e74bb672a2`.

Both exact candidate commits were fetched from GitHub and matched coordination issue #16. Both
candidate PRs were open, ready, and unmerged. This is the workflow §11.8.7 targeted closure review
of L09-R018 and the semantics directly touched by its fix. No candidate, Python, shared semantic,
canonical, or Rust implementation file was changed.

## Verdict

```text
L09-R018
    PROVISIONALLY CLOSED @ exact PASS-10 SHAs

all known Layer-09 blockers
    PROVISIONALLY CLOSED

final complete §11.8.8 review
    REQUIRED NEXT
```

This is not final contract approval and does not authorize Rust implementation.

## Agreed-contract implementation audit

The candidate implements the agreed external delegation grammar exactly:

| Delegation | Candidate behavior | Result |
|---|---|---|
| `next_()` | existing full payload continues | PASS |
| `next_(messages)` | original Agent and signal restored; messages replaced | PASS |
| `next_(instance, messages, signal)` | middle messages retained; authoritative Agent/signal restored | PASS |
| any other arity, especially two | `WaterfallError` raised inside `normalize_step` before forwarding | PASS |

`_restore_signal` validates the replacement before `EventBus.waterfall` invokes the next step.
It does not infer meaning from runtime types or silently choose between leading-Agent omission and
trailing-signal omission.

## Acceptance witnesses

All seven agreed witnesses are present and green:

1. leading-Agent omission is rejected directly; a deliberately variadic downstream listener is
   never invoked;
2. trailing-signal omission receives the identical direct rejection/non-forwarding treatment;
3. the real-loop leading-omission case sends no provider request and settles one represented
   assistant error while returning idle;
4. the real-loop trailing-omission case has the same represented-failure behavior;
5. chained message-only delegation preserves the original Agent and signal and reaches the real
   request with transformed messages;
6. the pre-existing full-length signal-redirect witness remains unchanged and green;
7. message-only delegation also works as the first/only listener and reaches the provider.

The direct witnesses correctly observe immediate `WaterfallError`. The real-loop witnesses do not
expect it to escape: `_execute_run` catches it and `_settle_run_failure` applies the already-
certified Layer-08 represented-failure lifecycle. This closes C18-1 and C18-2 without introducing
a new error boundary.

The author records revert-and-confirm for all six new tests against the rejected PASS-9 code: both
two-field forms fail the future refusal expectation, both real-loop cases reach/corrupt or proceed
when they should settle, and both one-field positive cases fail with `IndexError`. The unchanged
full-length witness is correctly identified as the green regression guard, closing C18-3.

## Spec and manifest synchronization

`spec/agent.md` now states one current, language-neutral rule: Agent and signal are authoritative;
messages alone are transformable; legal delegations are no-op, message-only, and full; ambiguous
arities fail at the authority boundary; real-loop failure is represented and the provider is not
called.

Manifest AG-023 contains the same complete rule, all six new test pointers, the unchanged
full-length evidence, and the current Python implementation pointer. AG-007 carries only a concise
cross-reference. The manifest remains 79 rows / 79 unique IDs. No placeholder canonical scenario
is cited as satisfying Layer-09 evidence.

## Dependency regression

- L09-R006 full-length signal restoration remains green.
- L09-R015's separate pre-step/prepare-next-turn authority normalizers are untouched.
- Inbox reservation and L09-R017 binding immutability are untouched.
- Tool pre/post authority boundaries are untouched.
- Layer-08 run-failure settlement is reused, not reimplemented.
- No lower-layer contract is reopened.
- Transport cancellation remains deferred to PROV-004.
- No Rust implementation or Layer-10 behavior began.

## Fresh evidence

Executed at the exact code SHA:

```text
full Python suite
    1131 passed / 19 xfailed

coverage
    100% (2842 / 2842 statements)

targeted transform-context tests
    8 passed

full conformance tests
    298 passed / 19 xfailed

ruff
    PASS

mypy
    PASS (58 source files)

manifest
    79 rows / 79 unique IDs
```

## Findings

```text
PI_PARITY_DEFECT
    none active — L09-R018 provisionally closed

CONTRACT_ASSURANCE_DEFECT
    none active

PI_BEHAVIOR_UNCERTAIN
    none

PARITY_CONSTRAINED_RISK
    none blocking
```

## Status and next action

```text
shared/Python Layer 09
    READY FOR ONE FINAL COMPLETE EXACT-SHA REVIEW

Rust Layer 09
    BLOCKED / NOT_IMPLEMENTED pending that review

Layer 09 cross-language
    NOT CLOSED

Layer 10
    NOT STARTED
```

The next action is the mandatory workflow §11.8.8 final complete independent contract review of
these exact PASS-10 SHAs. It must audit the entire Layer-09 contract and normal certification gate,
not only L09-R018. If either candidate head changes first, this provisional closure is stale.
