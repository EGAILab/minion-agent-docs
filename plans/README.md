# Minion Agent Implementation Plans

This directory contains implementation plans for the Python and Rust implementations.

A dated plan is **not automatically current** merely because it is detailed or executable-looking.
Always read its status banner and cross-check the current frozen design, normative spec, parity
manifest, and canonical conformance before implementing from it.

## Current semantic authority

Implementation plans are downstream of:

```text
design/2026-08-20-minion-agent-design.md
spec/
/pi-parity-manifest.yaml        # in the minion-agent code monorepo
/conformance/                   # in the minion-agent code monorepo
process/implementation-conformance-workflow.md
```

A plan must not redefine these artifacts.

## Existing plans

### Python

The existing 2026-08-18/19 Python plans were written before the 2026-08-20 Pi-fidelity correction.

Their top-of-file status banners are authoritative for whether material is retained, superseded, or
requires realignment.

In particular:

```text
2026-08-18-plan-1-conformance-and-runtime.md
    largely retained where revised runtime conformance stays green

2026-08-18-plan-2-llm-session-telemetry.md
    LLM vocabulary / transformation substantially superseded

2026-08-18-plan-3-agent-loop.md
    agent-loop semantics substantially superseded

2026-08-19-plan-4-tools.md
    tool semantics require Pi-aligned realignment
```

Do not treat these old plans as current semantic authority.

### Rust

Rust Phase 1 runtime is retained unless revised runtime conformance exposes a real conflict.

Superseded Phase 2+ plans must be rewritten/reconciled against the frozen 2026-08-20 master,
current spec, parity manifest, and canonical conformance before implementation.

## New plans

New executable plans should:

1. name the frozen design revision;
2. name relevant parity-manifest row IDs;
3. name relevant spec sections / requirement IDs;
4. name canonical conformance scenarios;
5. state Python/Rust implementation status;
6. state whether the plan is active, superseded, completed, or historical;
7. follow `process/implementation-conformance-workflow.md`;
8. include the applicable assurance/certification step.

Recommended status vocabulary:

```text
ACTIVE
COMPLETED
SUPERSEDED
HISTORICAL
DRAFT
```

A plan that becomes superseded should receive a clear top-of-file status banner rather than relying
on readers to infer staleness from its date.
