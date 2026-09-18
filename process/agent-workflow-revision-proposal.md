# Minion Agent — Agent Workflow Revision Proposal

**Status:** ADOPTED (2026-09-19). Applied to `process/agent-workflow.md` (§4.2, §11.1–§11.1.3,
§11.2.1, §11.4, §11.8, §11.8.7, §11.8.7.1, §11.8.8, §11.13, §11.14, §12.6, §14.2) and to a new
canonical `process/coordination-state.md`. This document is preserved verbatim as the historical
proposal record, per this project's own "preserve review/remediation history" rule — the applied
result is the live `process/agent-workflow.md` and `process/coordination-state.md`, not this file.
**Motivation:** Layer 11 process retrospective, following the Layer 11 Pass 2 Slice C closure and
the PROV-013 scope-audit pass (issue #35).
**Scope:** Coordination model, convergence control, review evidence, deferred work, and automation.
**Non-goals:** This proposal does **not** weaken Pi fidelity, semantic authority, independent review, exact-SHA approval, governance provenance, quarantine semantics, or cross-language certification.

## Application notes (added at adoption time)

This proposal was drafted without a live view of `process/agent-workflow.md`, so two of its target
section numbers collided with content already present in the file. Both were resolved by merging
rather than renumbering, specifically to avoid invalidating the many existing historical citations
to `§11.8.7`/`§11.8.8` embedded in prior commit messages and assurance records (e.g. Layer 11 Pass 2
Slice C's own "second/third mandatory final-complete review (§11.8.8)" citations):

- The proposal's new `§11.8.1 Convergence episode` collided with the existing `§11.8.1 Convergence
  objective`. Applied as one merged section, `§11.8.1 Convergence objective and episode tracking`,
  rather than renumbering `§11.8.2`–`§11.8.9` (which would have silently broken every existing
  `§11.8.7`/`§11.8.8` citation in project history).
- The proposal's new `§12.5 Machine validation of coordination state` collided with the existing
  `§12.5 Commit discipline`. Applied as `§12.6` instead, immediately after the existing `§12.5`.

The proposal's own §15 ("Migration of current Layer 11") is a worked example rather than a durable
process rule, and its content now lives as the concrete example in `process/coordination-state.md`
§12 (populated with the real issue/PR numbers from this project's own history: issue #24 (WP-11.1),
issue #29 (WP-11.2/11.3/11.4), issue #35 (WP-11.D1), issue #27/PR #28/docs PR #73 (incident)) rather
than being duplicated as prose inside `agent-workflow.md` itself. The proposal's own §16 ("Process
invariants retained unchanged") was a summary/self-check for this proposal document, not new prose
for the workflow file; each invariant it lists was independently re-verified to still hold in the
applied result before this proposal was marked ADOPTED.

Everything else below is the original proposal text, unmodified.

---

## 1. Summary of the change

The existing workflow is strong at semantic correctness and forensic traceability, but Layer 11 exposed three scaling problems:

1. a single assurance layer can contain several independently certifiable bodies of work;
2. repeated review/remediation cycles can fall back into full reviews even after `CONTRACT_CONVERGENCE`;
3. GitHub issues/comments are being used simultaneously as current state and historical event log, causing stale issue bodies and excessive coordination ceremony.

This revision introduces:

- **work packages** as the operational/certification unit inside a layer;
- an explicit **workflow state machine**;
- a binding targeted-review rule during convergence;
- mandatory **negative-control validation** for discriminating witnesses;
- separation of **current coordination state** from append-only history;
- an explicit `WAITING_FOR_TRIGGER` state for deferred parity;
- machine-checkable coordination metadata;
- reduced reliance on one assurance PR per review event.

The semantic authority chain remains unchanged:

```text
adopted Pi source
    -> parity manifest
    -> normative spec
    -> canonical conformance
    -> implementations
```

---

# 2. Replace §4.2 with the following

## 4.2 Work-package slicing

A large assurance layer MAY be divided into smaller **work packages** without changing the architectural layer boundary.

A work package is the smallest unit that has all of the following:

- a bounded semantic surface;
- an explicit set of parity-manifest requirement IDs;
- a coherent contract/evidence set;
- a single coordination state;
- a clear certification or deferred-parity outcome.

Example:

```text
Layer 11 — Real Providers
    WP-11.1 Auth Foundation
    WP-11.2 Codex Account Projection
    WP-11.3 Provider/Auth Interaction Vocabulary
    WP-11.4 Codex OAuth Network Integration
    WP-11.D1 Generic Auth Orchestration — DEFERRED
```

A work package SHOULD be organized around observable semantic ownership, not implementation modules.

### 4.2.1 Layer versus work-package status

A **layer** is an architectural grouping.

A **work package** is the unit of active coordination, review, implementation, and certification.

A layer MAY contain:

```text
CLOSED work packages
+
DEFERRED work packages with binding closure triggers
```

A layer is considered complete for the current baseline when every in-scope requirement is either:

```text
CERTIFIED / ADOPTED
or
DEFERRED PARITY with an explicit closure trigger
or
INTENTIONAL DIVERGENCE with valid governance provenance
```

Do not use "Pass" as a semantic or certification level. Review rounds are events within a work package, not additional project hierarchy.

---

# 3. Replace §11.1 with the following

## 11.1 Coordination issue per active work package

Create one coordination issue in `minion-agent` for each **active work package**, not necessarily one issue for the entire architectural layer.

A layer MAY also have one umbrella/index issue whose only purpose is to summarize work-package disposition.

Examples:

```text
Layer 11 — Real Providers                    # umbrella/index
WP-11.1 — Auth Foundation                    # operational issue
WP-11.2 — Codex Account Projection           # operational issue
WP-11.4 — Codex OAuth Network Integration    # operational issue
WP-11.D1 — Generic Auth Orchestration        # deferred tracking
```

The operational issue contains one machine-readable current-state block:

```yaml
workflow:
  schema_version: 1
  layer: "11"
  work_package: "WP-11.4"
  status: CONTRACT_CONVERGENCE
  code_pr: 33
  code_sha: "<remote SHA>"
  docs_pr: 92
  docs_sha: "<remote SHA>"
  open_findings:
    - L11-SC-R025
    - L11-SC-R027
  next_owner: Claude
  next_action: "Implement the agreed acceptance matrix and return for targeted closure."
  governance_source: null
  deferred_trigger: null
```

This block is the **current control state**.

Comments and assurance records are historical event/evidence records. They MUST NOT be treated as the primary source of current ownership/status when the state block exists.

### 11.1.1 Current-state update rule

Whenever any of the following changes:

- `STATUS`;
- current code/docs candidate SHA;
- open finding set;
- `NEXT_OWNER`;
- `NEXT_ACTION`;
- governance dependency;
- deferred closure trigger;

the coordination issue's current-state block MUST be updated.

Do not leave a stale issue body and rely on a later comment to override it.

### 11.1.2 Exactly one active owner

For active states, there must be exactly one `next_owner` and one concrete `next_action`.

For passive deferred state:

```text
WAITING_FOR_TRIGGER
```

`next_owner` and `next_action` MAY be `none`; `deferred_trigger` MUST be present and binding.

---

# 4. Replace the status vocabulary in §11.1 with the following

## 11.1.3 Work-package states

Allowed states:

```text
SCOPING
CONTRACT_DRAFT
CONTRACT_REVIEW
PYTHON_IMPLEMENTATION
IMPLEMENTATION_REVIEW
REMEDIATION
CONTRACT_CONVERGENCE
FINAL_CONTRACT_REVIEW
RUST_IMPLEMENTATION
CLOSURE_REVIEW
WAITING_FOR_TRIGGER
CLOSED
INCIDENT
INVALID_UNAUTHORIZED
BLOCKED_FOR_OWNER
```

### State intent

`SCOPING`
: Read-only audit and boundary definition. No implementation authorization is implied.

`CONTRACT_DRAFT`
: Shared contract/evidence is being authored before implementation.

`CONTRACT_REVIEW`
: Independent review of the proposed semantic contract.

`PYTHON_IMPLEMENTATION`
: The shared/Python owner is implementing an approved/checkpointed contract.

`IMPLEMENTATION_REVIEW`
: Independent review of implementation plus permanent evidence.

`REMEDIATION`
: Narrow correction of review findings before convergence has triggered.

`CONTRACT_CONVERGENCE`
: Repeated/coupled semantic defects are being characterized and closed through the convergence protocol.

`FINAL_CONTRACT_REVIEW`
: All known blockers are provisionally closed; one complete exact-SHA review is pending.

`RUST_IMPLEMENTATION`
: Rust implementation against the merged approved shared contract.

`CLOSURE_REVIEW`
: Cross-language closure verification.

`WAITING_FOR_TRIGGER`
: Deferred parity is valid and no implementation is authorized until a named event occurs.

`CLOSED`
: The work package is durably complete for its disposition.

`INCIDENT`
: Coordination object is retained for process/forensic history and is not actionable implementation state.

`INVALID_UNAUTHORIZED`
: Artifact was created or mutated outside valid authorization and is governed by quarantine semantics.

`BLOCKED_FOR_OWNER`
: A governance decision is required before work may proceed.

---

# 5. Replace §11.4 with the following

## 11.4 Standard work-package ownership flow

```text
SCOPING
   ↓
CONTRACT_DRAFT
   ↓
independent CONTRACT_REVIEW
   ↓
checkpoint / approval for implementation
   ↓
PYTHON_IMPLEMENTATION
   ↓
IMPLEMENTATION_REVIEW
   ↓
┌───────────────────────────────┐
│ no blocking findings          │
│     ↓                         │
│ FINAL_CONTRACT_REVIEW         │
│     ↓                         │
│ merge approved shared/Python  │
└───────────────────────────────┘
              │
              └── blocking findings
                         ↓
                    REMEDIATION
                         ↓
              targeted or complete review
                         ↓
                 trigger §11.8?
                   /          \
                 no            yes
                 ↓              ↓
            REMEDIATION   CONTRACT_CONVERGENCE
                                ↓
                       characterize + challenge
                                ↓
                            checkpoint
                                ↓
                         coherent fix pass
                                ↓
                    negative-control witness gate
                                ↓
                         TARGETED REVIEW
                                ↓
                     all blockers provisionally
                              closed
                                ↓
                       FINAL_CONTRACT_REVIEW
                                ↓
                       ONE complete exact-SHA
                           independent review
                                ↓
                              merge
                                ↓
                       RUST_IMPLEMENTATION
                                ↓
                         CLOSURE_REVIEW
                                ↓
                              CLOSED
```

Rust implementation starts from the merged approved shared contract, never from an unapproved Python candidate branch.

A work package MUST NOT transition directly from `CONTRACT_CONVERGENCE` to a complete final review while a known convergence finding remains open.

---

# 6. Replace §11.8 trigger text with the following

## 11.8 Contract convergence protocol

The normal remediation/re-review loop is intentionally strict, but it MUST NOT become an unbounded semantic-discovery loop.

Enter `CONTRACT_CONVERGENCE` automatically when **any** of the following occurs:

```text
A. the same material finding survives two independent reviews;

B. the same semantic root-cause surface produces two successor findings
   after remediation, even when the finding IDs differ;

C. the work package accumulates three rejected complete contract reviews;

D. the reviewer and implementation owner agree that the remaining blockers
   form one tightly-coupled semantic surface that is more efficiently
   characterized together.
```

These triggers are evaluated separately:

- trigger A is finding-specific;
- trigger B is root-cause/surface-specific;
- trigger C is work-package-wide;
- trigger D is an early opt-in.

Do not reinterpret a work-package-wide trigger as finding-specific or vice versa.

### 11.8.1 Convergence episode

Each convergence episode receives a stable ID:

```text
CE-L11-04-01
```

The episode records:

```text
OPEN FINDINGS
ROOT-CAUSE SURFACE
PI SYMBOLS / TESTS AUDITED
OBSERVABLE RULES
BEHAVIOR MATRIX
MINIMAL EXECUTABLE WITNESSES
NEGATIVE CONTROLS
CURRENT CANDIDATE FAILURES
SPEC / MANIFEST / CONFORMANCE DELTAS
IMPLEMENTATION CONSTRAINTS
OUT-OF-SCOPE / DEFERRED BEHAVIOR
```

New findings discovered inside the same root-cause surface are added to the existing episode instead of automatically starting another complete-review loop.

---

# 7. Replace §11.8.7 with the following

## 11.8.7 Targeted convergence closure is mandatory

After a convergence implementation pass, the independent reviewer MUST perform a targeted finding-closure review.

The review scope is:

```text
open convergence finding(s)
+
semantic dependencies touched by the fix
+
previously-closed high-risk regressions affected by the change
```

A complete release-level work-package review MUST NOT be substituted for this targeted closure step merely because the candidate SHA changed.

A complete review is permitted before all convergence findings are provisionally closed only when the reviewer records a concrete reason that the remediation changed semantic surface outside the convergence checkpoint.

A successful targeted review records:

```text
Lxx-Ryyy
    PROVISIONALLY CLOSED @ <candidate SHA>
```

If a finding remains open, the reviewer MUST provide a new/refined discriminating witness.

Do not simply restate the prior finding.

---

# 8. Add new §11.8.7.1

## 11.8.7.1 Negative-control gate for discriminating witnesses

Before a blocking executable finding can be marked `PROVISIONALLY CLOSED`, its permanent witness must demonstrate both:

```text
known-bad behavior -> FAIL
candidate behavior -> PASS
```

The negative control MAY be established by:

- reverting the specific fix in a temporary worktree;
- executing the witness against a known-bad prior SHA;
- substituting a deliberately incorrect implementation at the relevant seam;
- another deterministic mutation that reproduces the reported defect.

The evidence record MUST state:

```text
finding ID
negative-control method
known-bad mutation/SHA
expected failure
observed failure
candidate SHA
observed pass
```

A test that passes only on the candidate but has not been shown to fail against a realistic incorrect implementation is supporting evidence, not a discriminating closure witness.

For documentary-only findings where no executable distinction exists, record:

```text
NEGATIVE_CONTROL
    NOT_APPLICABLE — documentary/traceability-only
```

with the reason.

---

# 9. Replace §11.8.8 with the following

## 11.8.8 One final complete review per settled convergence episode

Once every blocking finding in the active convergence episode is provisionally closed:

1. freeze the candidate to one exact remote code/docs SHA pair;
2. run all complete gates;
3. transition to `FINAL_CONTRACT_REVIEW`;
4. perform **one** complete independent contract review of that exact candidate;
5. if approved, apply the normal exact-SHA merge gate.

If the final complete review discovers a new blocker:

### Case A — narrow, independent blocker

If the blocker is demonstrably outside the settled convergence root-cause surface and can be closed without changing the wider contract:

```text
FINAL_CONTRACT_REVIEW
    -> targeted remediation
    -> targeted closure review
    -> FINAL_CONTRACT_REVIEW
```

Do not automatically re-run the entire convergence characterization.

### Case B — coupled/new semantic surface

If the blocker exposes another coupled semantic surface or invalidates the prior convergence matrix:

```text
new convergence episode
```

with a new episode ID.

The existence of a changed candidate SHA alone is **not** sufficient reason to perform a complete review before targeted closure is finished.

---

# 10. Add new §11.13

## 11.13 Deferred parity and trigger-based work

A parity row may legitimately remain deferred when its real integration seam does not yet exist.

Use:

```text
STATUS
    WAITING_FOR_TRIGGER
```

when all of the following are true:

- the row has an explicit `deferred parity` disposition;
- the reason for deferral is architectural/integration readiness, not unresolved semantic uncertainty;
- a concrete closure trigger is recorded;
- no production implementation is currently authorized.

Required state:

```yaml
status: WAITING_FOR_TRIGGER
next_owner: null
next_action: null
deferred_trigger:
  type: architecture_event
  description: >
    A real provider/auth composition surface exists that requires
    Models-equivalent orchestration.
```

`WAITING_FOR_TRIGGER` is not active implementation work and is excluded from the active-state rule requiring a next owner/action.

When the trigger fires:

1. create or reactivate a normal active work package;
2. fetch current default-branch reality;
3. perform a fresh contract-first Pi audit;
4. do not resume implementation directly from the historical deferred audit;
5. consume already-certified lower/vocabulary requirements normally.

---

# 11. Add new §11.14

## 11.14 Current state versus historical event log

GitHub coordination has two distinct data classes:

```text
CURRENT STATE
    issue state block / machine-readable coordination record

HISTORY / EVIDENCE
    comments
    review records
    assurance artifacts
    PR timeline
    commits
```

Rules:

- Current state is mutable and MUST be kept current.
- Historical evidence is append-only; do not rewrite prior rejection into approval.
- A later comment MUST NOT silently supersede a stale current-state block.
- Automation and receiving agents MUST read current state first, then use the history to validate it.
- Historical assurance remains durable evidence even after the current-state block advances.

This separation prevents a coordination issue from becoming an event log pretending to be a state store.

---

# 12. Replace §11.2 review-artifact guidance with the following addition

## 11.2.1 Review evidence packaging

A separate docs PR is **not required for every review event**.

A work package SHOULD prefer:

```text
one candidate PR pair
+
one durable review ledger / assurance record
+
coordination issue event comments
```

over creating a new branch/PR solely to store each individual review round.

Create a separate assurance PR when at least one of the following is true:

- normative/process/assurance source files are intentionally changed;
- the review artifact itself must become part of the accepted default-branch milestone;
- a convergence agreement/checkpoint needs durable repository content before implementation;
- repository policy requires the evidence to be merged as a file.

Otherwise, a SHA-bound review record attached to the coordination issue/PR is sufficient intermediate evidence, provided it contains:

```text
reviewer role
candidate code/docs SHA
pinned Pi revision
scope
findings
discriminating witness links/details
verdict
next transition
```

At certification, material intermediate evidence SHOULD be summarized into the final assurance record rather than requiring every review event to remain a standalone merged document.

Do not reduce evidence quality; reduce redundant repository objects.

---

# 13. Add new §12.5

## 12.5 Machine validation of coordination state

The coordination state defined by `process/coordination-state.md` SHOULD be validated automatically.

At minimum, automation should reject:

- unknown workflow states;
- active states with no `next_owner`;
- active states with no `next_action`;
- `WAITING_FOR_TRIGGER` without `deferred_trigger`;
- `INVALID_UNAUTHORIZED` or `INCIDENT` states attempting a handoff;
- candidate SHAs that are not remote-reachable;
- changed candidate SHA paired with a stale final approval;
- governance-dependent decisions without `governance_source`;
- a candidate derived from a quarantined artifact;
- transition to `FINAL_CONTRACT_REVIEW` while convergence findings remain open;
- transition to Rust implementation before shared/Python contract approval/merge;
- a claimed provisional closure without required discriminating negative-control evidence.

The validator enforces workflow structure only. It does not decide semantics.

---

# 14. Add to §14.2 retrospective questions

Add:

- Did the chosen work-package boundary match the actual independently certifiable semantic surface?
- Did the work package create more coordination/review artifacts than the assurance value justified?
- After convergence fired, were targeted closure reviews used until every blocker was provisionally closed?
- Did any final review re-open a previously settled root-cause surface because the convergence matrix was incomplete?
- Did every executable closure witness demonstrate a realistic negative control?
- Did the current-state block remain synchronized with comments/PR state?
- Should any deferred work have been represented as `WAITING_FOR_TRIGGER` instead of active/open workflow?

---

# 15. Migration of current Layer 11

The existing Layer 11 history SHOULD NOT be rewritten.

Map the existing durable history conceptually as:

```text
Layer 11 — Real Providers

WP-11.1 Auth Foundation
    source coordination: issue #24
    disposition: CLOSED

WP-11.2 Codex Account Projection (PROV-011)
    source coordination: issue #29 / Slice A
    disposition: CLOSED

WP-11.3 Provider/Auth Interaction Vocabulary (PROV-014)
    source coordination: issue #29 / Slice B
    disposition: CLOSED

WP-11.4 Codex OAuth Network Integration (PROV-012, PROV-016)
    source coordination: issue #29 / Slice C
    disposition: CLOSED

WP-11.D1 Generic Auth Orchestration (PROV-013)
    source coordination: issue #35
    disposition: WAITING_FOR_TRIGGER
    trigger: real provider/auth composition surface requiring
             Models-equivalent orchestration

Incident record
    issue #27
    disposition: INVALID_UNAUTHORIZED / QUARANTINED
```

This migration is a classification overlay only. Do not renumber or rewrite historical finding IDs, commits, PRs, or assurance evidence.

---

# 16. Process invariants retained unchanged

This revision explicitly preserves the following existing invariants:

- Pi source remains the behavioral authority for adopted Pi-derived behavior.
- Manifest/spec/conformance remain shared language-neutral contract authorities.
- Python is not Rust's oracle.
- Rust is not Python's oracle.
- Independent review remains mandatory.
- Exact-SHA final approval remains mandatory.
- Governance-dependent decisions require explicit provenance.
- Unauthorized artifacts remain quarantined.
- Rust begins from merged approved shared semantics.
- Cross-language closure remains a distinct gate.
- Later-layer implementation must not be pulled forward merely to simplify current-layer work.
- Deferred parity must be explicit; silence is never a valid disposition.

The objective is not fewer checks. It is fewer **redundant control-plane artifacts and unnecessary full-review resets** while preserving or increasing semantic assurance.
