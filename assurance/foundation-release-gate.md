# Minion Agent — Pi-Compatible Foundation Release Gate

**Status:** Working final gate  
**Purpose:** Determine whether the current Minion Agent foundation can be declared a completed Pi-compatible baseline.

This gate certifies **Pi-fidelity foundation quality**. It does not claim that all known post-parity production improvements have already been implemented.

## 1. Contract baseline

- [ ] Frozen design identified and current
- [ ] Adopted Pi revision pinned
- [ ] `/pi-parity-manifest.yaml` complete for current baseline
- [ ] Every manifest row has a disposition
- [ ] Normative specs complete for implemented foundation layers
- [ ] Shared conformance schema valid
- [ ] No contradiction among frozen design/spec/conformance

## 2. Shared conformance

- [ ] `conformance/runtime/` complete for adopted runtime contract
- [ ] `conformance/session/` complete for implemented/adopted session contract
- [ ] `conformance/agent/` complete for implemented/adopted agent/tool/transform semantics
- [ ] Thin-runner rule reviewed
- [ ] No semantic behavior implemented inside a conformance adapter

## 3. Layer certifications

Record current status:

| Layer | Python | Rust | Certification |
|---|---|---|---|
| Runtime kernel | | | |
| LLM vocabulary | | | |
| Session + artifacts | | | |
| Target-model transformation | | | |
| Tool model + registry | | | |
| Tool execution | | | |
| Agent state + queues | | | |
| Agent loop | | | |
| Cancellation | | | |
| Provider abstraction/mock | | | |
| Real providers | | | |
| Execution seams | | | |
| Built-in tools | | | |
| Prompt + skills | | | |
| Compaction | | | |
| Telemetry/invariants | | | |
| Integrated foundation | | | |

Use language implementation status:

```text
IMPLEMENTED
NOT_IMPLEMENTED
DEFERRED
NOT_APPLICABLE
```

A layer not yet implemented in Rust is not automatically a release failure when the agreed project phase allows Python to lead, but its planned Rust phase must be explicit.

## 4. Python gates

- [ ] Applicable canonical conformance green
- [ ] Language-specific tests green
- [ ] 100% configured line-coverage floor green
- [ ] `mypy --strict` green
- [ ] `ruff` green
- [ ] Property/invariant tests green
- [ ] Concurrency/fault-injection tests green where applicable
- [ ] No tests retained solely because they assert superseded semantics

## 5. Rust gates

For every layer Rust has reached:

- [ ] Applicable canonical conformance green
- [ ] Unit/integration tests green
- [ ] Type/public API direction matches frozen design
- [ ] No Python-semantic dependency
- [ ] No runner-side reimplementation of canonical semantics

## 6. Security assurance

- [ ] Every implemented layer has trust-boundary review
- [ ] Input-validation boundaries documented
- [ ] Secret-handling review complete
- [ ] Resource-abuse risks reviewed
- [ ] Cross-agent/scope isolation reviewed
- [ ] No unclassified security BLOCKER/HIGH finding

Parity-constrained security risks may remain only if explicitly recorded in `risk-register.md`.

## 7. Reliability / operational assurance

- [ ] Cancellation semantics documented and tested
- [ ] Timeout policy documented where applicable
- [ ] Retry policy documented where applicable
- [ ] Cleanup/shutdown ownership documented
- [ ] Backpressure/resource-limit behavior reviewed
- [ ] Persistence/restart behavior reviewed where applicable
- [ ] No unclassified reliability BLOCKER/HIGH finding

## 8. Observability assurance

- [ ] Critical run/tool/provider paths are trace-correlatable
- [ ] Failure categories observable
- [ ] Cancellation distinguishable from error
- [ ] Sensitive fields excluded/redacted as required
- [ ] Telemetry does not silently alter semantic execution
- [ ] Major observability blind spots are resolved or risk-registered

## 9. Documentation assurance

- [ ] README status matches repository reality
- [ ] Public API documentation current
- [ ] Layer assurance reports current
- [ ] Planned vs implemented layers clearly distinguished
- [ ] Documentation drift findings closed or explicitly recorded

## 10. Finding closure

- [ ] All findings classified
- [ ] No unresolved `PI BEHAVIOR UNCERTAIN`
- [ ] No unresolved Pi parity defect
- [ ] No open parity BLOCKER
- [ ] No open parity-neutral BLOCKER/HIGH hardening issue without explicit exception
- [ ] Every parity-constrained risk recorded in `risk-register.md`

## 11. Evals

Model-backed evals are not semantic release authority.

- [ ] Eval layer, if present, is treated as behavioral-effectiveness evidence
- [ ] No eval result has silently overridden known Pi-compatible semantics

## 12. Final disposition

```text
PI-COMPATIBLE FOUNDATION BASELINE

[ ] APPROVED
[ ] BLOCKED
[ ] PARTIAL — implementation phase not yet complete
```

### Approval rationale

...

### Remaining post-parity risks

...

### Next phase

After approval, use `risk-register.md` as input to the explicit post-parity production-hardening review.
