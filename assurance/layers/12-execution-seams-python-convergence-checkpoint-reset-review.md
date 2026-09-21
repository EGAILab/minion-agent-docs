# Layer 12 convergence checkpoint-reset independent review

Mode: checkpoint-only review (`agent-workflow.md` §11.8.5/§11.8.10)

Verdict: **CHANGES REQUIRED — IMPLEMENTATION REMAINS UNAUTHORIZED**

## Exact target

- checkpoint PR: `EGAILab/minion-agent-docs#121`
- reviewed SHA: `2f8741bea5be842fdbddddb492cab6d9a6b547fe`
- frozen diagnostic Python candidate: `EGAILab/minion-agent#44` at
  `d44ea0e2b46e18997a425e514c7ab8f458642f7d`
- certified Rust baseline reviewed read-only: `2b309ee8cecbc333a7965781087677bd6cbba46b`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`

No Python or Rust implementation was reviewed as a new candidate or modified in this pass. Layer
13 was not started.

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
    NEEDS REVISION

AGREED FOR IMPLEMENTATION
    NO
```

## R002 characterization — approved

The revised artifact correctly establishes the authority chain:

```text
pinned Pi resolvePath
    -> Node url.fileURLToPath
    -> Node path.isAbsolute/path.resolve
```

The executable Node behavior at the declared supported floor is the normative oracle; the finite
corpus is representative regression evidence rather than a replacement semantic definition. The
primary-oracle correction to checksum-verified Node `v22.19.0`, plus the `v22.23.2` drift check,
removes the earlier unsupported version-stability assumption.

The committed table contains 65 comparable rows and its reported counts independently reconcile:
4 Python mismatches and 17 Rust mismatches. Model A—delegated Node/Pi compatibility—is the only
disposition coherent with the existing direct-parity classification absent owner-approved
divergence. The research-first requirement to prototype a standards-faithful composition against
the whole corpus before integration is appropriate.

Rust revalidation is required for the narrowly identified `EXEC-002`/`EXEC-003` file-URL branch.
The historical Rust certification remains evidence; its current validity for this surface is no
longer established.

Non-blocking evidence hardening: preserve the exact corpus generator/probe script in a later
evidence update so the table and version-drift comparison can be reproduced mechanically. This
does not alter the semantic oracle and is not required to accept the characterization itself.

## R004-A characterization — acceptable component

The reset correctly distinguishes cause classification from settlement timing. The deterministic
first-claim model is coherent and observable:

- the monitor claims `SIGNAL` only after its latest liveness observation still reports running;
- explicit termination claims `EXPLICIT`;
- the first successful claim wins;
- kill-helper success/failure does not rewrite an existing claim;
- final classification depends on the stored claim.

The source description of the certified Rust implementation is accurate: the atomic claim occurs
before `kill_process_tree`, and helper outcome is not used to revise it. The proposed model is a
material clarification of the ambiguous phrase “whichever caused the actual kill first”; if the
checkpoint is later approved, the implementation/remediation pass must update the normative spec
and evidence explicitly rather than leaving the clarified rule only in assurance prose.

## C12-RESET-R001 — R004-B is not an unresolved equal-policy choice

**Classification:** `CONTRACT_ASSURANCE_DEFECT`  
**Severity:** blocking

The artifact correctly observes that Rust's monitor awaits `kill_process_tree()` before awaiting/
publishing the target process outcome. It then presents two co-equal policies:

- Policy A: `wait()` settles on process exit alone;
- Policy B: `wait()` may await termination machinery.

The current authority chain already resolves this question. `spec/execution.md` §6 explicitly
states that `wait()` settles on the process's own exit alone. An implementation contradiction does
not make the normative rule undecided (`agent-workflow.md` §§3 and 7); certified Rust code is not a
semantic authority and cannot implicitly reopen the contract.

Observable failure mode:

```text
target process has exited
external kill/taskkill helper remains pending indefinitely

normative contract
    wait() settles from the target exit

certified Rust implementation
    wait() remains pending because monitor_child awaits kill_process_tree first
```

Minimal correction:

1. Record Policy A as the retained current contract.
2. Classify the Rust settlement behavior as a narrowly scoped implementation defect requiring
   Rust revalidation/remediation.
3. Remove the suggestion that Policy B is available merely because it matches existing Rust.
   Policy B may be proposed only through an explicit shared-contract/governance reopen.
4. Keep R004-A classification separate and update the matrix/verdict accordingly.

Because R004-B remains incorrectly characterized, `R004 CHARACTERIZATION` is rejected as a whole
even though the R004-A component is acceptable.

## C12-RESET-R002 — revalidation trigger omits the R002 case it claims to govern

**Classification:** `CONTRACT_ASSURANCE_DEFECT`  
**Severity:** blocking process-rule defect

Proposed §11.8.11 triggers `REVALIDATE_REQUIRED` when language B discovers:

1. a new shared semantic requirement; or
2. that an existing shared requirement was materially mischaracterized.

R002 is neither. The shared requirement was already direct parity with Node/Pi and remains so. The
new differential corpus instead proves that an already-certified implementation does not satisfy
an existing, correctly characterized requirement. The artifact applies §11.8.11 to R002, but the
rule's own trigger text does not authorize that application.

Minimal correction: add a third trigger equivalent to:

```text
new discriminating evidence shows that an already-certified implementation does not satisfy an
existing shared requirement, even though the requirement itself was characterized correctly
```

Retain the narrow-scoping and historical-evidence language. The checkpoint-invalidation rule and
the proposal-versus-independent-approval correction are otherwise approved.

## Rust revalidation

```text
EXEC-002/EXEC-003 file:// conversion
    REVALIDATE_REQUIRED

R004-A subprocess classification
    REVALIDATE_REQUIRED — add discriminating states 7/9/10 evidence

R004-B subprocess settlement
    REVALIDATE_REQUIRED — current source conflicts with process-exit-only spec
```

This is narrow revalidation, not a claim that unrelated Layer-12 Rust behavior is uncertified.
No Rust modification is authorized by this review.

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

Return the two checkpoint corrections above to the characterization owner. A corrected exact SHA
requires another checkpoint-only review. Do not resume Python or Rust implementation in the same
pass.
