# Layer 12 convergence checkpoint-reset independent re-review 2

Mode: checkpoint-only review (`agent-workflow.md` sections 11.8.5, 11.8.10, and 11.8.11)

Verdict: **APPROVED — AGREED FOR IMPLEMENTATION**

## Exact target

- checkpoint PR: `EGAILab/minion-agent-docs#121`
- reviewed SHA: `2db656c01126bfb775d1fe453241e191ed78b2f0`
- immediately prior rejected SHA: `77919d50c424e0884e70de163a7ae53d804bba0d`
- prior independent review evidence: `EGAILab/minion-agent-docs#120` at
  `8e501a34c26f5965bccc0094c05a1d1f73ef1ea5`
- frozen diagnostic Python candidate: `EGAILab/minion-agent#44` at
  `d44ea0e2b46e18997a425e514c7ab8f458642f7d`
- certified Rust baseline inspected read-only:
  `2b309ee8cecbc333a7965781087677bd6cbba46b`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`

The coordination issue was open and valid, assigned `NEXT_OWNER = Codex`, and identified the
same remote-reachable PR head. PRs #44, #120, and #121 were open and unmerged. No Python or Rust
implementation was modified. Layer 13 was not started.

## Checkpoint verdict

```text
CHECKPOINT REVIEW

R002 CHARACTERIZATION
    APPROVED

R004 CHARACTERIZATION
    APPROVED

RUST REVALIDATION
    REQUIRED

PROCESS RULE
    APPROVED

AGREED FOR IMPLEMENTATION
    YES
```

## Correction verification

The exact change from `77919d50...` to `2db656c0...` is confined to the R004-A consequence
paragraph. It removes the last current statement calling R004-B unresolved and now states the two
independent facts coherently:

1. R004-A remains a proposed Python correction until this independent checkpoint approval; and
2. R004-B is already resolved by the retained process-exit-only contract and requires narrow
   Rust revalidation/remediation rather than a Python policy decision.

A full phrase scan found no other unqualified current statement treating R004-B as unresolved,
undecided, or a competing policy. Remaining matches either assert the corrected retained rule or
describe superseded history explicitly.

## Agreed characterization

### R002

Pinned Pi delegates file-URL conversion to supported Node `fileURLToPath`/path behavior. That
executable behavior remains the normative oracle; the committed 65-case corpus is representative,
non-exhaustive evidence. The frozen Python candidate's `61/65` and certified Rust baseline's
`48/65` counts were independently reproduced from the committed raw outputs in the preceding
review. Model A, delegated Node/Pi compatibility, is agreed.

### R004-A

Cause classification uses the deterministic first-claim state machine recorded by the checkpoint:
`NONE`, `SIGNAL`, or `EXPLICIT`; the first valid claim wins; kill-helper success or failure does
not retroactively rewrite an existing claim. This replaces the ambiguous physical-causality
wording with observable state-machine semantics.

### R004-B

The retained contract is unchanged: `wait()` settles on the target process's own exit alone.
Rust's current helper-coupled settlement is a narrow implementation defect against that rule, not
an alternative semantic policy.

## Rust revalidation

```text
EXEC-002/EXEC-003 file:// conversion
    REVALIDATE_REQUIRED

R004-A subprocess classification
    REVALIDATE_REQUIRED — add discriminating states 7/9/10 evidence

R004-B subprocess settlement
    REVALIDATE_REQUIRED — remediate current helper-coupled settlement against the retained rule
```

This does not reopen unrelated Layer-12 Rust certification. It also does not authorize Rust
changes during the Python implementation pass.

## Authorized next step

The convergence checkpoint is now `AGREED FOR IMPLEMENTATION`. The Python/shared owner may modify
PR #44 only for the agreed R002 and R004-A remediation and its required evidence/spec updates.
After that exact candidate is pushed, control returns to Codex for the targeted finding-closure
review required by section 11.8.7.

This approval does not certify the Python candidate, does not close either finding, does not
authorize Rust revalidation in the same pass, and does not authorize Layer 13.
