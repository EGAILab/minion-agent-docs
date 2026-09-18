# Minion Agent — Coordination State Specification

**Canonical location:** `process/coordination-state.md`
**Referenced by:** `process/agent-workflow.md` §11.1, §11.1.3, §11.13, §12.6
**Purpose:** Define a machine-checkable current-state model for GitHub work-package coordination.

---

## 1. Principle

The project separates:

```text
current workflow state
from
historical evidence
```

Current state answers:

- What work package is active?
- What exact candidate is current?
- What findings remain open?
- Who acts next?
- What exact action is authorized?
- Is governance required?
- Is the work waiting on an architectural trigger?

Historical evidence answers:

- What happened previously?
- Which candidates were rejected?
- Why?
- Which witnesses were used?
- Which findings were remediated?
- Which governance decisions were made?

A GitHub issue body (or future dedicated state file) stores current state.

Comments, PR reviews, assurance records, and commits store history/evidence.

---

## 2. Required state block

Recommended representation:

```yaml
workflow:
  schema_version: 1

  layer: "11"
  work_package: "WP-11.4"
  title: "Codex OAuth Network Integration"

  status: CONTRACT_CONVERGENCE

  requirements:
    - PROV-012
    - PROV-016

  code:
    pr: 33
    sha: "0123456789abcdef..."
    base: "main"

  docs:
    pr: 92
    sha: "fedcba9876543210..."
    base: "master"

  pinned_pi: "b7bb00b936dbe21b8e160b3e89efdec361846699"

  convergence:
    episode: "CE-L11-04-02"
    open_findings:
      - L11-SC-R025
      - L11-SC-R027

  next_owner: Claude
  next_action: >
    Implement the agreed R025/R027 acceptance matrix and return the
    exact candidate for targeted closure review.

  governance_source: null
  deferred_trigger: null

  quarantine:
    derived_from_quarantined_artifact: false

  updated_by: "Claude"
  updated_reason: "Entered convergence after repeated/coupled review findings."
```

---

## 3. Allowed values

### 3.1 `status`

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

State intent is defined in `process/agent-workflow.md` §11.1.3; this file defines only the machine-checkable shape and invariants.

### 3.2 `next_owner`

```text
Claude
Codex
Owner
none/null
```

Other named owners may be added when the project adds additional implementation/review roles.

---

## 4. State invariants

### 4.1 Active-state invariant

For:

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
BLOCKED_FOR_OWNER
```

require:

```text
next_owner != null
next_action != null
```

`BLOCKED_FOR_OWNER` requires:

```text
next_owner: Owner
```

### 4.2 Deferred-state invariant

For:

```text
WAITING_FOR_TRIGGER
```

require:

```text
deferred_trigger != null
next_owner == null
next_action == null
```

### 4.3 Closed-state invariant

For:

```text
CLOSED
```

require:

- no open blocking findings;
- accepted/default-branch milestone recorded;
- final disposition recorded for every owned requirement.

### 4.4 Unauthorized/incident invariant

For:

```text
INCIDENT
INVALID_UNAUTHORIZED
```

the state is non-actionable.

It MUST NOT authorize:

- implementation;
- review of the artifact as a candidate;
- certification;
- handoff;
- merge.

---

## 5. Candidate invariants

When `code.pr` is present:

```text
code.sha
```

must identify that PR's current remote-reachable candidate head unless the state explicitly records a frozen prior candidate under review.

Same for docs.

A final approval is bound to:

```text
(code.sha, docs.sha)
```

If either changes:

```text
final approval becomes stale
```

Intermediate targeted finding closure remains valid as historical evidence for the specific finding/candidate, but the final complete approval gate must operate on the exact final pair.

---

## 6. Convergence model

Recommended shape:

```yaml
convergence:
  episode: "CE-L11-04-02"
  root_cause_surface: >
    pre-response HTTP cleanup and authorization-input parsing witness completeness
  open_findings:
    - L11-SC-R027
  provisionally_closed:
    - finding: L11-SC-R025
      sha: "abc..."
      review_evidence: "docs#103"
```

### Rules

If `status == CONTRACT_CONVERGENCE`:

- `convergence.episode` is required;
- at least one `open_findings` entry is required until targeted closure completes;
- transition to `FINAL_CONTRACT_REVIEW` is forbidden while `open_findings` is non-empty.

When all findings are provisionally closed:

```text
CONTRACT_CONVERGENCE
    -> FINAL_CONTRACT_REVIEW
```

---

## 7. Discriminating witness record

For an executable blocking finding (see `process/agent-workflow.md` §11.8.7.1):

```yaml
witness:
  finding: L11-SC-R027
  positive:
    candidate_sha: "abc..."
    command: "pytest ..."
    expected: "PASS"
    observed: "PASS"
  negative_control:
    method: "temporary source mutation"
    mutation: "remove exactly-one-leading-question-mark normalization"
    expected: "relevant parser regression test fails"
    observed: "FAILED as expected"
```

For documentary-only findings:

```yaml
witness:
  finding: L11-SC-R026
  negative_control:
    method: NOT_APPLICABLE
    reason: "documentary/traceability-only finding"
```

A validator does not need to execute arbitrary mutation tests initially. It can first validate that the closure record contains the required fields.

---

## 8. Governance source

When semantic scope, intentional divergence, lower-layer reopening, Pi-baseline change, or other owner-governed decisions are involved (see `process/agent-workflow.md` §11.10):

```yaml
governance_source:
  artifact: "https://github.com/EGAILab/minion-agent/issues/29#issuecomment-..."
  decision: >
    Adopt PROV-014 separately and keep PROV-013 orchestration deferred.
  scope:
    - PROV-013
    - PROV-014
```

A recommendation is not a governance source.

Silence is not a governance source.

An agent's own assertion that the owner approved something is not a governance source.

---

## 9. Deferred trigger

Example:

```yaml
deferred_trigger:
  type: architecture_event
  description: >
    Minion introduces a real provider/auth composition surface that requires
    Models-equivalent login/logout/checkAuth/getAuth orchestration.
  on_fire:
    action: >
      Perform a fresh contract-first Pi audit against the concrete integration
      requirements. Do not resume directly from the historical deferred audit.
```

The trigger should describe an observable project event, not merely a date.

---

## 10. Legal transition sketch

```text
SCOPING
  -> CONTRACT_DRAFT
  -> WAITING_FOR_TRIGGER
  -> BLOCKED_FOR_OWNER

CONTRACT_DRAFT
  -> CONTRACT_REVIEW

CONTRACT_REVIEW
  -> PYTHON_IMPLEMENTATION
  -> CONTRACT_DRAFT
  -> CONTRACT_CONVERGENCE
  -> BLOCKED_FOR_OWNER

PYTHON_IMPLEMENTATION
  -> IMPLEMENTATION_REVIEW

IMPLEMENTATION_REVIEW
  -> FINAL_CONTRACT_REVIEW
  -> REMEDIATION
  -> CONTRACT_CONVERGENCE

REMEDIATION
  -> IMPLEMENTATION_REVIEW
  -> CONTRACT_CONVERGENCE

CONTRACT_CONVERGENCE
  -> FINAL_CONTRACT_REVIEW
  # only when all active episode findings are provisionally closed

FINAL_CONTRACT_REVIEW
  -> RUST_IMPLEMENTATION
  -> REMEDIATION
  -> CONTRACT_CONVERGENCE
  -> BLOCKED_FOR_OWNER

RUST_IMPLEMENTATION
  -> CLOSURE_REVIEW

CLOSURE_REVIEW
  -> CLOSED
  -> RUST_IMPLEMENTATION       # remediation of Rust candidate
  -> BLOCKED_FOR_OWNER

WAITING_FOR_TRIGGER
  -> SCOPING                   # only when trigger fires

BLOCKED_FOR_OWNER
  -> any specifically authorized legal continuation state
```

`INCIDENT` and `INVALID_UNAUTHORIZED` are terminal/non-actionable for candidate workflow purposes.

---

## 11. Suggested validator rules

A first implementation can be simple and deterministic.

Pseudo-rules:

```text
if status in ACTIVE_STATES:
    require next_owner
    require next_action

if status == WAITING_FOR_TRIGGER:
    require deferred_trigger
    forbid next_owner
    forbid next_action

if status == CONTRACT_CONVERGENCE:
    require convergence.episode
    require convergence.open_findings.length > 0
        unless transition is immediately being made to FINAL_CONTRACT_REVIEW

if transition_to == FINAL_CONTRACT_REVIEW:
    require convergence.open_findings.length == 0
    require all convergence findings == PROVISIONALLY_CLOSED

if governance-dependent fields changed:
    require governance_source

if quarantine.derived_from_quarantined_artifact:
    reject handoff

if status in [INCIDENT, INVALID_UNAUTHORIZED]:
    reject candidate handoff/review/merge

if final_approval.sha_pair != current_candidate.sha_pair:
    approval is stale

if provisional_closure is claimed for executable finding:
    require positive witness record
    require negative-control witness record
```

---

## 12. Layer 11 example after migration

This is a **classification overlay only**, applied retroactively for illustration. It does not renumber or rewrite any historical finding ID, commit, PR, or assurance evidence from before this schema existed.

```yaml
layer: "11"
title: "Real Providers"
work_packages:
  - id: WP-11.1
    title: Auth Foundation
    requirements: [PROV-006, PROV-007, PROV-008, PROV-009, PROV-010]
    status: CLOSED
    source_coordination: "issue #24"

  - id: WP-11.2
    title: Codex Account Projection
    requirements: [PROV-011]
    status: CLOSED
    source_coordination: "issue #29"

  - id: WP-11.3
    title: Provider/Auth Interaction Vocabulary
    requirements: [PROV-014]
    status: CLOSED
    source_coordination: "issue #29"

  - id: WP-11.4
    title: Codex OAuth Network Integration
    requirements: [PROV-012, PROV-016]
    status: CLOSED
    source_coordination: "issue #29"

  - id: WP-11.D1
    title: Generic Auth Orchestration
    requirements: [PROV-013]
    status: WAITING_FOR_TRIGGER
    source_coordination: "issue #35"
    deferred_trigger:
      type: architecture_event
      description: >
        A real provider/auth composition surface exists that requires
        Models-equivalent orchestration.

incidents:
  - issue: 27
    status: INVALID_UNAUTHORIZED
    related_artifacts:
      - "minion-agent PR #28 @ ed58b714613000bdee6eedfb41a38b2ceb9b5a56"
      - "minion-agent-docs PR #73 @ cbc3ba5f373b0a63d5e611fe7e40f6dcca79ff08"
```

This representation makes the project state explicit without rewriting any historical Layer 11 artifact.
