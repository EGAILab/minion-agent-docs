# Minion Agent Assurance

This directory contains the assurance framework for Minion Agent's current Pi-alignment program.

The current semantic priority is:

> **Pi behavioral fidelity first.**

Production-quality review is performed during the same bottom-up audit, but an improvement that would change Pi-visible behavior is documented and deferred unless it is explicitly approved as an intentional divergence.

## Documents

- `2026-08-22-foundation-fidelity-assurance-charter.md` — why this audit exists, its scope, current repository baseline, and governing priorities.
- `fidelity-assurance-method.md` — the normative procedure every layer audit follows.
- `layer-certification-template.md` — reusable template for each layer audit/certification report.
- `risk-register.md` — centralized register of parity-constrained and other production risks.
- `foundation-release-gate.md` — final gate for declaring the Pi-compatible foundation baseline complete.

## Suggested working structure

```text
minion-agent-docs/
└── assurance/
    ├── README.md
    ├── 2026-08-22-foundation-fidelity-assurance-charter.md
    ├── fidelity-assurance-method.md
    ├── layer-certification-template.md
    ├── risk-register.md
    ├── foundation-release-gate.md
    └── layers/
        ├── 01-runtime.md
        ├── 02-llm.md
        ├── 03-session-artifacts.md
        ├── 04-target-model-transformation.md
        ├── 05-tool-model-registry.md
        ├── 06-tool-execution.md
        ├── 07-agent-state-queues.md
        ├── 08-agent-loop.md
        ├── 09-cancellation.md
        ├── 10-provider-abstraction.md
        └── ...
```

The canonical Pi parity manifest currently lives at `/pi-parity-manifest.yaml`. Shared language-neutral conformance remains under `/conformance/`.
