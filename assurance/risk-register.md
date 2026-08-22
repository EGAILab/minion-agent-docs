# Minion Agent — Foundation Risk Register

**Purpose:** Central register for production-quality risks discovered during Pi-fidelity work, especially risks that cannot be fixed without changing Pi-visible semantics.

This is not a generic backlog. A risk belongs here when it is relevant to foundation assurance and needs an explicit disposition.

## Classification

- `PARITY_CONSTRAINED` — fixing now would change Pi-visible behavior.
- `PARITY_NEUTRAL_PENDING` — can be fixed without semantic divergence, but remediation is intentionally deferred.
- `POST_PARITY_REVIEW` — broader production improvement to reconsider after the compatible baseline.
- `ACCEPTED` — explicitly accepted risk with rationale.
- `RESOLVED` — remediation completed.

## Register

| Risk ID | Layer | Severity | Classification | Risk | Pi/contract dependency | Why not fixed now | Planned action | Status |
|---|---|---|---|---|---|---|---|---|
| `RISK-001` | | | | | | | | |

## Entry requirements

Every risk must identify:

1. the affected layer;
2. severity;
3. whether it is observable to callers/models/plugins;
4. the relevant Pi/spec/conformance dependency;
5. why current remediation is or is not compatible with parity;
6. the future decision required;
7. current status.

## Rules

A `PI BEHAVIOR UNCERTAIN` finding should not be placed here as a substitute for source audit. Resolve the uncertainty first.

A `PI PARITY DEFECT IN MINION` also does not belong here as accepted debt; it must be remediated before certification.

A parity-constrained risk may remain through the baseline only when:

```text
the Pi-compatible behavior is understood
AND
the risk is documented
AND
the semantic divergence is intentionally deferred
```

After the Pi-compatible foundation baseline is complete, this register becomes a primary input to the post-parity hardening program.
