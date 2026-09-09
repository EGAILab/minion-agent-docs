# Layer 09 active abort — PASS 8 targeted Rust re-review

## Target and mode

This review targets exactly:

- code PR `EGAILab/minion-agent#17` at
  `551aa162cb0ff0c6b052f6a1500d8687d0ded825`;
- docs PR `EGAILab/minion-agent-docs#26` at
  `57b7f8797a11670f77388f0ecb35f1f43d98d4a5`;
- pinned Pi at `b7bb00b936dbe21b8e160b3e89efdec361846699`.

Both candidate heads were fetched from GitHub, were open and ready for review,
and matched issue #16. This is the targeted §11.8.7 review of L09-R012 through
L09-R016 against the revision-2 convergence agreement in docs PR #35 at
`5c796f3b1bac3ee6a1c71f80a2dac2163d055f83`.

Review only: no Python, shared-contract, or Rust implementation file was
modified.

## Result

```text
PASS 8 TARGETED CLOSURE
    REJECTED

L09-R012
    PROVISIONALLY CLOSED

L09-R013
    PROVISIONALLY CLOSED

L09-R014
    PROVISIONALLY CLOSED

L09-R015
    STILL OPEN

L09-R016
    PROVISIONALLY CLOSED

NEW L09-R017
    OPEN
```

The claim-before-observer architecture closes the exact R013/R014 re-entrancy
window and AG-011's current prose is repaired. The tools signal-status prose and
docstring are also current. Two discriminating failures remain.

## Closure ledger

### L09-R012 — AG-011 contradiction

**PROVISIONALLY CLOSED.**

AG-011 no longer says the run-entry operation removes by count after a peek. It
describes the current claim-bound reservation/rollback rule, identifies the
superseded mechanisms as history, and points to current implementation/tests.
Manifest integrity is 79 rows / 79 unique IDs.

The new reservation mutability defect below is tracked separately as R017; it
does not make the original documentary R012 wording stale.

### L09-R013 — claiming then throwing observer

**PROVISIONALLY CLOSED.**

`Inbox._reserve()` destructively removes the selected A/B batch before the
RUNNING observer executes. The observer therefore cannot claim that same batch.
On notification failure, `_run_wrapped` rolls the reservation back ahead of
later input. The exact real-driver witness is present and passes.

### L09-R014 — partial-prefix duplicate admission

**PROVISIONALLY CLOSED.**

The peek/commit window no longer exists. A RUNNING observer cannot remove a
partial prefix from a batch already held by the reservation. The real-driver
terminal-response witness proves the observer sees no selected input and the
run admits A/B once.

### L09-R015 — authoritative Agent identity

**STILL OPEN.**

The redirect half is fixed: both `AGENT_PRE_STEP` and
`AGENT_PREPARE_NEXT_TURN` use a per-dispatch `normalize_step` which overwrites a
replacement tuple's first slot with the original Agent.

The claimed omission evidence is not discriminating. Its listener calls
`next_()` with no replacement arguments. `EventBus.waterfall` defines that as
“forward the current tuple unchanged,” so the original Agent was never omitted
even before this fix.

A true omission preserves every transformable field but delegates without the
first Agent field. Executable witness against the exact candidate:

```python
async def first(instance, message, tool_results, context, new_messages, next_):
    return await next_(message, tool_results, context, new_messages)

async def second(instance, message, tool_results, context, new_messages, next_):
    seen.append(instance)
    return await next_()
```

Observed through the real Agent loop:

```text
downstream listener calls
    0

Agent.error_message
    second() missing 1 required positional argument: 'next_'
```

The normalizer receives four values, treats the first transformable value as
the replaceable Agent slot, and returns only four values. The downstream
listener never observes the original Agent/signal; the run instead becomes a
represented failure. This differs from the agreed drop rule.

Required remediation: make each normalizer arity-aware. For the exact expected
payload length it replaces slot zero; for a tuple one field shorter it prepends
the original Agent without discarding the first transformable field. Add true
omission witnesses for both events. Keep malformed unrelated arities governed
by the existing waterfall misuse/error policy.

### L09-R016 — stale current signal prose

**PROVISIONALLY CLOSED.**

`spec/tools.md`, TOOL-009, and `_execute_and_finalize` now distinguish the
historical Layer-05 defer from current Layer-09 realization and describe all
four signal/update capability combinations. Historical text elsewhere is
explicitly marked superseded/current and is not counted as current guidance.

## L09-R017 — reservation batch is mutable

Classification: **CONTRACT_ASSURANCE_DEFECT**.

The agreed C09-1 contract requires a reservation bound to the exact batch
removed by its creating claim, with read-only `reservation.envelopes` and no
path for caller-supplied replacement envelopes. `_Reservation.envelopes` is a
plain writable slot in the exact candidate.

Minimal executable witness through the real Inbox:

```text
follow-up queue: A
r = inbox._reserve(NEXT_TURN, ONE_AT_A_TIME)   # r initially owns A
steering queue: B
r.envelopes = (B,)
r.rollback()
```

Observed:

```text
NEXT_TURN
    B

NEXT_STEP
    B

original A present
    false

copies of B's envelope ID across queues
    2
```

Thus the implementation can lose the truly reserved envelope and manufacture
a duplicate foreign envelope with one assignment. The existing “foreign
envelope” test only calls `rollback(envelope)`/`commit(envelope)` and proves the
terminal methods accept no argument. It does not prove the separately agreed
read-only batch binding.

Required remediation: make the bound batch genuinely immutable to the holder
of a reservation. One suitable Python shape stores it only in a private slot and
exposes a read-only property; do not provide a setter or mutable container.
Add the assignment witness above and verify the true originally claimed batch
is the only batch rollback can restore. Retain all one-shot terminal-action
tests.

## Affected regression audit

- R007 entry status/signal rollback ordering: unchanged by the new flow and
  passing.
- R010 unrestricted public restore: the public method remains absent; R017 is
  the distinct mutable-binding route on the new reservation.
- R011 unrelated-front deletion: eliminated with the removed peek/commit
  window.
- Pi prepare-next-turn signal citation: corrected and aligned with
  `Agent.createLoopConfig()`.
- `AGENT_TURN_STOPPING`: serial fan-out remains outside the redirect hazard.
- Transform-context and tool hook signal normalizers: unchanged.
- Lower layers: no contract reopening is required.

## Evidence

Fresh targeted suite at the exact code SHA:

```text
tests/agent/test_inbox.py
tests/agent_loop/test_active_abort.py
    66 passed
```

Author-reported aggregate gates remain green (1123 passed, 19 xfailed, 100%
coverage, ruff/mypy clean), but the two missing witnesses above are not covered
by that suite.

## Taxonomy

```text
PI_PARITY_DEFECT
    L09-R015 (still open)

CONTRACT_ASSURANCE_DEFECT
    L09-R017 (new)

PI_BEHAVIOR_UNCERTAIN
    none

PARITY_CONSTRAINED_RISK
    none

PARITY_NEUTRAL_HARDENING
    none
```

## Verdict and next action

```text
shared/Python Layer 09
    NOT READY FOR FINAL COMPLETE REVIEW

Rust Layer 09
    BLOCKED / NOT_IMPLEMENTED

Layer 09 cross-language
    NOT CLOSED

Layer 10
    NOT STARTED
```

Revise the convergence implementation narrowly for R015's true omission and
R017's immutable reservation binding, convert both exact observations into
permanent regression evidence, rerun the affected convergence matrix and full
gates, and return exact remote SHAs for another targeted review. Do not perform
the final §11.8.8 complete review until both are provisionally closed.
