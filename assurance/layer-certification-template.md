# <Layer Name> — Fidelity Assurance & Certification

**Layer ID:** `<NN>`  
**Status:** `NOT_STARTED | IN_AUDIT | REMEDIATING | CERTIFIED | BLOCKED`  
**Audit date:**  
**Auditor:**  
**Python status:** `IMPLEMENTED | NOT_IMPLEMENTED | DEFERRED | NOT_APPLICABLE`  
**Rust status:** `IMPLEMENTED | NOT_IMPLEMENTED | DEFERRED | NOT_APPLICABLE`

---

## 1. Scope

### Owns

- ...

### Does not own

- ...

### Depends on

- ...

### Depended on by

- ...

---

## 2. Normative sources

- Frozen design:
- Spec:
- `/pi-parity-manifest.yaml` rows:
- Canonical conformance:
- Pinned Pi source paths/symbols:
- Approved divergences:

---

## 3. Pi behavior summary

Document the audited Pi-visible behavior for this layer.

Do not infer unspecified behavior from best practice.

---

## 4. Requirement traceability

| ID | Requirement | Source | Python implementation | Rust implementation | Executable evidence | Status |
|---|---|---|---|---|---|---|
| `<ID>` | ... | ... | ... | ... | ... | `PASS/FAIL/PENDING` |

---

## 5. Implementation inventory

| File/module | Responsibility | Decision | Evidence |
|---|---|---|---|
| ... | ... | `RETAIN / RETAIN + HARDEN / MODIFY / REWRITE / DELETE / DEFER` | ... |

---

## 6. Existing-test audit

| Test | Requirement | Current validity | Disposition | Reason |
|---|---|---|---|---|
| ... | ... | ... | `KEEP / STRENGTHEN / MOVE TO CONFORMANCE / REWRITE / DELETE` | ... |

Possible reason: `SUPERSEDED_CONTRACT`.

---

## 7. Missing test / conformance coverage

### Canonical conformance

- [ ] ...

### Language-specific tests

- [ ] ...

### Property/invariant tests

- [ ] ...

### State-machine tests

- [ ] ...

### Concurrency tests

- [ ] ...

### Fuzz tests

- [ ] ...

### Fault-injection tests

- [ ] ...

---

## 8. Failure model

For each meaningful failure define:

| Failure | Surface | Result/throw/event | Retry? | Abort interaction | Logged/telemetry? |
|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... |

---

## 9. Security review

### Trust boundaries

- ...

### Input validation

- ...

### Authority / privilege

- ...

### Secret handling

- ...

### Resource abuse / bounds

- ...

### Isolation

- ...

---

## 10. Reliability and operations

- Cancellation:
- Timeouts:
- Retry:
- Cleanup:
- Shutdown:
- Backpressure:
- Partial failure:
- Persistence/restart:
- Dependency disappearance:

---

## 11. Observability

### Events

- ...

### Logs

- ...

### Metrics

- ...

### Traces

- ...

### Correlation IDs

- ...

### Sensitive fields excluded from telemetry

- ...

---

## 12. Performance / complexity

| Path | Expected complexity/budget | Evidence | Risk |
|---|---|---|---|
| ... | ... | ... | ... |

---

## 13. Public API / serialization

- Public API:
- Internal API:
- Stable/experimental:
- Serialized schemas:
- Cross-language fields:
- Round-trip tests:

---

## 14. Documentation audit

| Document | Accuracy | Required action |
|---|---|---|
| ... | ... | ... |

---

## 15. Findings

| ID | Severity | Classification | Description | Disposition / action |
|---|---|---|---|---|
| ... | `BLOCKER/HIGH/MEDIUM/LOW` | `PI_PARITY_DEFECT / CONTRACT_ASSURANCE_DEFECT / PARITY_NEUTRAL_HARDENING / PARITY_CONSTRAINED_RISK / PI_BEHAVIOR_UNCERTAIN` | ... | ... |

Any parity-constrained risk must also be entered into `../risk-register.md`.

A `CONTRACT_ASSURANCE_DEFECT` must be repaired before certification; it is not risk-register debt.

---

## 16. Certification gate

```text
Design alignment                         [ ]
Pi parity                                [ ]
Normative spec                           [ ]
Parity manifest                          [ ]
Canonical conformance                    [ ]
Python tests where implemented           [ ]
Rust tests where implemented             [ ]
Property/invariant tests                 [ ]
Concurrency tests where applicable       [ ]
Fault-injection tests where applicable   [ ]
Security review                          [ ]
Reliability review                       [ ]
Observability review                     [ ]
Performance review                       [ ]
Public API review                        [ ]
Documentation                            [ ]
All findings classified                  [ ]
No unresolved Pi uncertainty             [ ]
No unresolved parity defect              [ ]
No unresolved contract-assurance defect  [ ]
Deferred risks recorded                  [ ]
```

## 17. Certification result

**Result:** `CERTIFIED | BLOCKED | NOT YET ELIGIBLE`

**Rationale:**

...

**Follow-up dependencies:**

...
