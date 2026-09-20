# Layer 12 convergence checkpoint-reset independent re-review

Mode: checkpoint-only re-review (`agent-workflow.md` sections 11.8.5, 11.8.10, and 11.8.11)

Verdict: **CHANGES REQUIRED — IMPLEMENTATION REMAINS UNAUTHORIZED**

## Exact target

- checkpoint PR: `EGAILab/minion-agent-docs#121`
- reviewed SHA: `77919d50c424e0884e70de163a7ae53d804bba0d`
- prior rejected checkpoint SHA: `2f8741bea5be842fdbddddb492cab6d9a6b547fe`
- prior independent review: `EGAILab/minion-agent-docs#120` at
  `ca91006402ecf952f5e73691eca684d60ee3edaa`
- frozen diagnostic Python candidate: `EGAILab/minion-agent#44` at
  `d44ea0e2b46e18997a425e514c7ab8f458642f7d`
- certified Rust baseline inspected read-only:
  `2b309ee8cecbc333a7965781087677bd6cbba46b`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`

The PR heads were remote-reachable and unchanged when this review began. PRs #44, #120, and #121
were open, ready for review, and unmerged. No Python or Rust implementation was modified. Layer 13
was not started.

## Required verdict shape

```text
CHECKPOINT REVIEW

R002 CHARACTERIZATION
    APPROVED

R004 CHARACTERIZATION
    REJECTED

RUST REVALIDATION
    REQUIRED

PROCESS RULE
    APPROVED

AGREED FOR IMPLEMENTATION
    NO
```

## Prior findings recheck

### C12-RESET-R001 — partially resolved, still blocking

Revision 2 correctly establishes in the R004-B section, the 15-state matrix, both principal
summaries, and the requested-review scope that the current contract already selects process-exit-
only settlement. It correctly classifies Rust's helper-coupled settlement as an implementation
defect rather than a competing policy. Those changes resolve the substance of the prior finding.

However, the R004-A consequence paragraph still states:

> This part of the correction is NOT authorized for implementation yet -- see the settlement
> question below, which is unresolved and affects how this classification model interacts with
> `wait()`'s own contract.

That is a current, unqualified statement inside the same revised checkpoint. It directly
contradicts R004-B and the revision summary, which correctly say the settlement question is
already resolved by `spec/execution.md` section 6. A Rust implementer can therefore read two
incompatible current states from one purportedly agreed checkpoint.

### C12-RESET-R002 — resolved

The amended section 11.8.11 now has three distinct triggers:

1. a new shared semantic requirement;
2. a materially mischaracterized existing requirement; and
3. new discriminating evidence that a certified implementation fails an existing, correctly
   characterized requirement.

Trigger 3 covers R002 without pretending the Node/Pi rule changed. The added authority guard also
correctly states that an implementation divergence is not a competing semantic authority. The
rule preserves narrow scope and historical certification evidence. `PROCESS RULE = APPROVED`.

## C12-RESET-R003 — residual contradictory R004 status

**Classification:** `CONTRACT_ASSURANCE_DEFECT`  
**Severity:** blocking

**Affected section:**
`assurance/layers/12-execution-seams-python-convergence-checkpoint-reset.md`, R004-A consequence
paragraph immediately before R004-B.

**Failure mode:** the checkpoint simultaneously says the settlement question is unresolved and
that the retained normative spec already resolves it. Independent Python or Rust implementation
cannot rely on an internally contradictory checkpoint as an agreed contract.

**Minimal correction:** replace only that residual sentence with language consistent with the
rest of revision 2: R004-A implementation remains unauthorized pending independent checkpoint
approval, while R004-B itself is already resolved by the retained process-exit-only rule and
requires Rust revalidation/remediation rather than a policy choice. Re-scan the artifact for any
other unqualified current statement calling R004-B unresolved or undecided.

This is documentary and narrow. It does not reopen the accepted R002 characterization, the R004-A
state machine, the retained R004-B semantic rule, or the approved process amendment.

## Reproducibility evidence

The newly committed corpus bundle is coherent and useful non-normative evidence:

- rebuilding `matrix_full.tsv` from the committed raw outputs produced a clean worktree;
- the script independently reported 65 comparable cases, Python `61/65`, and Rust `48/65`;
- the two committed Node result files contain 68 rows each and compare byte-for-byte equal;
- the corpus remains explicitly subordinate to pinned Pi plus supported Node behavior.

The README's checkout-path edit is a manual setup step, not a semantic defect. The committed
scripts close the prior non-blocking reproducibility note.

## Rust revalidation

```text
EXEC-002/EXEC-003 file:// conversion
    REVALIDATE_REQUIRED

R004-A subprocess classification
    REVALIDATE_REQUIRED — add discriminating states 7/9/10 evidence

R004-B subprocess settlement
    REVALIDATE_REQUIRED — current Rust source conflicts with the retained process-exit-only rule
```

This remains narrow revalidation. It does not reopen unrelated Layer-12 Rust certification and
does not authorize a Rust change in this checkpoint-review pass.

## Final checkpoint disposition

```text
CONVERGENCE CHECKPOINT
    NOT AGREED FOR IMPLEMENTATION

implementation authorized
    NO

Python PR #44
    FROZEN_DIAGNOSTIC

Rust affected surfaces
    REVALIDATE_REQUIRED

Layer 13
    NOT STARTED
```

Return the single sentence-level correction above to the characterization owner. A corrected exact
SHA requires another checkpoint-only review. Do not resume Python or Rust implementation in this
pass.
