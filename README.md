# Minion Agent Documentation

This repository contains the architecture, normative semantic specification, engineering process,
assurance framework, implementation plans, and supporting reference material for Minion Agent.

Minion Agent has one semantic contract and two first-class implementations: Python and Rust.

The current semantic priority is:

> **Pi behavioral fidelity first.**

Pi at the adopted revision is the default compatibility oracle for Pi-visible agent, LLM/provider,
message-transformation, tool, session, and harness behavior. Minion's plugin/runtime architecture is
the primary intentional architectural divergence.

## Where to start

### Frozen architecture

Current frozen master:

```text
design/2026-08-20-minion-agent-design.md
```

Older dated design documents and review-feedback files are retained as historical record unless they
explicitly state otherwise.

### Normative semantics

```text
spec/
    authority.md
    llm.md
    target-model-transformation.md
    session.md
    agent.md
    tools.md
    harness.md
```

The spec defines the general language-neutral semantic rules.

### Development governance

```text
process/implementation-conformance-workflow.md
```

This is the active workflow for:

```text
Pi audit
-> parity manifest
-> spec
-> canonical conformance
-> implementation
-> implementation tests
-> assurance audit
-> remediation / risk registration
-> layer certification
-> phase freeze
```

### Assurance

```text
assurance/
```

Start with:

```text
assurance/README.md
assurance/2026-08-22-foundation-fidelity-assurance-charter.md
assurance/fidelity-assurance-method.md
assurance/layer-certification-template.md
assurance/risk-register.md
assurance/foundation-release-gate.md
```

Layer evidence belongs under:

```text
assurance/layers/
```

The next bottom-up foundation audit begins with the runtime layer.

### Implementation plans

```text
plans/
```

Read `plans/README.md` before using a dated implementation plan. Several 2026-08-18/19 plans were
written against the superseded 2026-08-18 design and remain only as implementation-history material
unless their status banner explicitly says otherwise.

### Reference material

```text
reference/
```

Reference documents are informational unless explicitly marked normative. In particular, the
human-readable Pi parity manifest is not the machine-readable source of truth.

## Canonical executable artifacts live in the code monorepo

The documentation repository is separate from the code monorepo.

Current code-monorepo shape:

```text
minion-agent/
├── conformance/
│   ├── runtime/
│   ├── session/
│   ├── agent/
│   └── schema/
├── minion-agent-python/
├── minion-agent-rust/
└── pi-parity-manifest.yaml
```

Canonical machine-readable artifacts:

```text
Minion code repo: /pi-parity-manifest.yaml
Minion code repo: /conformance/
```

Do not create language-specific copies of these artifacts.

## Authority map

```text
Frozen design
    architecture + mandatory project decisions
        ↓
Normative spec
    general semantic rules
        ↓
Canonical conformance
    executable finite examples
        ↓
Python / Rust implementations
```

The parity manifest provides traceability from the adopted Pi source to the spec/conformance and both
implementations.

The process document governs how changes are developed and frozen.

The assurance framework governs how implementation evidence, risks, and certification are collected.

Neither process nor assurance may redefine frozen semantic behavior.

## Active versus historical material

### Active

```text
design/2026-08-20-minion-agent-design.md
spec/
process/implementation-conformance-workflow.md
assurance/ current framework
code-monorepo /pi-parity-manifest.yaml
code-monorepo /conformance/
```

### Historical / supporting

```text
superseded 2026-08-18 design material
dated design review feedback
superseded implementation plans
assurance/archive/
dated process-review documents
reference/ human-readable views
```

Historical material remains useful for traceability but must not silently override the active
authority chain.
