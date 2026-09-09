# Layer 09 active abort — PASS 9 targeted Rust re-review

## Exact target

- code PR `EGAILab/minion-agent#17`:
  `e015c20c25b3506372c1887a6f7b079a7f8d9e7a`;
- docs PR `EGAILab/minion-agent-docs#26`:
  `7012b28ee5b8784a8b72367afd294a1b2b1ad99c`;
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`;
- PASS-8 targeted rejection: docs PR #36 at
  `9d93ddf5a50c32c2d1738e53d5a56b8c7d1962b9`.

Both exact candidates were fetched from GitHub and matched issue #16. This is
the narrow workflow §11.8.7 closure review for L09-R015 and L09-R017. No
candidate, shared semantic, Python, or Rust implementation file was changed.

## Verdict

```text
L09-R015
    PROVISIONALLY CLOSED @ exact PASS-9 SHAs

L09-R017
    PROVISIONALLY CLOSED @ exact PASS-9 SHAs

all known Layer-09 blockers
    PROVISIONALLY CLOSED

final complete §11.8.8 review
    REQUIRED NEXT
```

This is not final contract approval and does not authorize Rust implementation.

## L09-R015 — true Agent omission

**PROVISIONALLY CLOSED.**

Both affected `normalize_step` closures are now arity-aware:

- `AGENT_PREPARE_NEXT_TURN`: a four-field replacement is interpreted as the
  five-field payload with authoritative Agent omitted, so the original Agent is
  prepended without discarding `message`;
- `AGENT_PRE_STEP`: the corresponding two-field replacement prepends the
  original Agent without discarding `reason`;
- a full-length replacement continues to have its first slot replaced with the
  original Agent;
- unrelated malformed arities retain the existing waterfall error behavior.

The former non-discriminating `next_()` tests were corrected in place. They now
delegate every transformable field while genuinely omitting Agent. The exact
reviewer witness was also executed independently through the real Agent loop:

```text
downstream listener calls
    1

downstream Agent is original instance
    true

Agent.error_message
    none
```

The redirect tests remain green, so the new omission branch does not regress
the already-correct replacement case. Because the original Agent is restored,
the downstream listener also reaches the original active run signal through
`instance.signal`, preserving the pinned-Pi mapping.

## L09-R017 — immutable reservation binding

**PROVISIONALLY CLOSED.**

`_Reservation` now stores the claimed tuple in private `_envelopes` and exposes
`envelopes` as a getter-only property. Ordinary assignment raises
`AttributeError`; rollback reads the private bound tuple rather than a mutable
public slot.

The exact reviewer witness was executed independently:

```text
reserve A from NEXT_TURN
queue foreign B at NEXT_STEP
attempt reservation.envelopes = (B,)
    AttributeError
rollback
    NEXT_TURN = [A]
    NEXT_STEP = [B]
```

No ID is duplicated and the truly reserved A is retained. Existing one-shot
terminal witnesses remain green: double rollback, commit-then-rollback,
rollback-then-commit, and foreign arguments to terminal methods cannot mutate
the queue twice or inject replacement input.

## Dependency regression

The PASS-9 diff is confined to the two agreed surfaces plus traceability:

- claim-before-observer reservation timing is unchanged;
- R013 claiming-and-throwing and R014 partial-prefix cases remain structurally
  closed;
- R012's AG-011 current rule remains coherent;
- R016's signal-capability wording remains current;
- redirect normalization remains unchanged for full-length payloads;
- no lower-layer contract is reopened;
- transport cancellation remains deferred to PROV-004;
- no Rust implementation or Layer 10 work began.

## Fresh evidence

At the exact code SHA:

```text
tests/agent/test_inbox.py
tests/agent_loop/test_active_abort.py
    68 passed

manifest
    79 rows / 79 unique IDs (author gate)

full Python gate
    1125 passed / 19 xfailed / 100% coverage (author gate)

ruff / mypy
    clean (author gate)
```

The targeted review additionally executed both missing witnesses directly; the
observed values are recorded above.

## Findings

```text
PI_PARITY_DEFECT
    none active — L09-R015 provisionally closed

CONTRACT_ASSURANCE_DEFECT
    none active — L09-R017 provisionally closed

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

The next and only action is the mandatory workflow §11.8.8 final complete
independent contract review of these exact PASS-9 candidate SHAs. It must audit
the entire Layer-09 contract and normal certification gate, not only R015/R017.
If either candidate head changes first, this provisional exact-SHA state is
stale and the new candidate must be reviewed.
