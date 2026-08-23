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
| `RISK-001` | `03` (session/artifacts) | HIGH | `PARITY_NEUTRAL_PENDING` | `SessionLog`/`ArtifactStore` are pure in-memory Python objects (`self._events: list`, `self._content: dict`) with no persistence, crash recovery, or restart behavior. A process restart loses all session history and artifacts. | Confirmed against pinned Pi source (`packages/agent/src/harness/session/`): Pi's `Session`/`SessionStorage` is built around a pluggable durable backend (JSONL, SQLite via `session-backends/sqlite-node`) with lane-scoped runs, suspended/deferred operations, durable program state, pending writes, replay policy, and crash/deferred resume. The frozen design (`2026-08-20-minion-agent-design.md` "Stratum C — Pi AgentHarness durable operation parity", lines 110-116, and item 9 of its phase list, line 1851) already names this exact gap explicitly and classifies it as "a known deferred parity phase, not an optional future abstraction," assigned to **Phase 9**. Durability itself would not change Pi-visible model history (the reconstructed message sequence is identical whether stored in memory or on disk) — the divergence is scope/sequencing, not semantic-preservation, which is why `PARITY_NEUTRAL_PENDING` rather than `PARITY_CONSTRAINED`. | Explicitly out of scope for Phases 1-4 (a Pi-compatible agent driven entirely by a mock) and Phase 5 (real providers) per the design's own phase ordering (line 1853); building it now would be unplanned scope expansion into a body of work the design deliberately sequenced later (lanes, suspended/deferred operations, replay policy, crash resume — none of which Layer 03's current audit scope covers). | Phase 9 implements durable `SessionStorage` parity (lane-scoped runs, durable program state, pending writes, replay policy, crash/deferred resume) per the design's own commitment. Until then, the design's own text is binding: "Minion MUST NOT claim complete Pi AgentHarness parity" (line 116). | `ACCEPTED` — confirmed intentional and already normatively scoped by the frozen design; recorded here per this register's own entry requirements rather than left implicit. Discovered during Layer 03's §10 reliability review (2026-08-23). |

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

A `CONTRACT_ASSURANCE_DEFECT` does not belong here either. Missing/inconsistent spec, conformance,
traceability, evidence, or required dispositions must be repaired before certification rather than
recorded as deferred production risk.

A parity-constrained risk may remain through the baseline only when:

```text
the Pi-compatible behavior is understood
AND
the risk is documented
AND
the semantic divergence is intentionally deferred
```

After the Pi-compatible foundation baseline is complete, this register becomes a primary input to the post-parity hardening program.
