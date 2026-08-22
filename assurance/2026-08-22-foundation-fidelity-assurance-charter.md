# Minion Agent — Foundation Fidelity & Assurance Charter

**Date:** 2026-08-22  
**Status:** Current assurance-program charter  
**Repository baseline checked:** `EGAILab/minion-agent` `main`

## 1. Goal

Minion Agent is undergoing a one-time bottom-up realignment against the frozen 2026-08-20 design and the adopted Pi baseline.

The goal is not only to identify code that must be retained, modified, or rewritten. The goal is to establish a foundation whose:

- behavior;
- implementation;
- tests;
- conformance;
- documentation;
- known security/reliability/observability risks;

are all explicit and traceable.

The current project priority remains:

> **Reproduce Pi observable behavior and semantics as closely as practical.**

Pi source at the adopted revision is the default behavioral compatibility oracle for agent-loop, LLM/provider, message-transformation, tool, session, and related harness behavior.

## 2. Two-stage assurance model

```text
Stage 1 — Pi Fidelity Foundation
    reproduce Pi-visible behavior
    correct Minion parity defects
    apply parity-neutral hardening
    document parity-constrained risks

Stage 2 — Post-Parity Hardening
    review documented risks
    improve security/reliability/operability/performance
    explicitly approve any intended divergence from Pi
```

A production-quality improvement does not automatically override Pi semantics.

## 3. Decision rule

Every finding asks:

```text
Does fixing this issue change Pi-visible behavior?
```

If **no**, it is parity-neutral hardening and may be fixed now.

If **yes**, preserve Pi-compatible behavior for the baseline and record the risk for later hardening.

If unclear:

```text
stop
-> audit Pi source
-> update manifest/spec/conformance
-> decide only after the behavior is known
```

Do not resolve Pi uncertainty using generic best practice.

## 4. Finding classifications

Every finding must have exactly one classification:

### A. PI PARITY DEFECT IN MINION

Minion differs from adopted Pi semantics.

**Action:** fix now.

### B. PARITY-NEUTRAL HARDENING

The implementation can be improved without changing Pi-visible behavior.

**Action:** fix now when practical.

### C. PARITY-CONSTRAINED RISK

The issue is real, but changing it would alter Pi-visible behavior.

**Action:** document and defer.

### D. PI BEHAVIOR UNCERTAIN

The correct Pi-compatible behavior has not yet been established.

**Action:** source-audit Pi before implementation changes.

## 5. Current repository baseline

Current monorepo structure:

```text
minion-agent/
├── conformance/
│   ├── agent/
│   ├── runtime/
│   ├── schema/
│   └── session/
├── minion-agent-python/
├── minion-agent-rust/
└── pi-parity-manifest.yaml
```

The canonical parity manifest currently lives at:

```text
/pi-parity-manifest.yaml
```

The Python implementation currently contains:

```text
runtime/
llm/
session/
telemetry/
agent/
agent_loop/
tools/
```

The Rust implementation currently contains the runtime foundation only.

Later layers such as real providers, execution seams, built-in tools, skills, full compaction behavior, and model-backed evals are not all implemented yet.

Audit status must therefore distinguish:

```text
CURRENTLY_IMPLEMENTED
PLANNED_NOT_IMPLEMENTED
DEFERRED
NOT_APPLICABLE
```

## 6. Current repo-grounded migration hypothesis

Strong retain candidates:

```text
runtime kernel
append-only session/storage substrate
artifact store
deterministic test infrastructure
```

Strong rewrite/heavy-realignment candidates:

```text
LLM vocabulary
target-model transformation
Agent public state/queues
agent_loop/driver.py
tool execution semantics
active abort propagation
provider-facing reconstruction
```

Tools and session must be audited by responsibility, not as all-or-nothing packages:

```text
tool registry/model          -> retain/modify candidate
tool execution pipeline      -> heavy realignment candidate

session storage/artifacts    -> retain candidate
session derive/reconstruction-> realignment candidate
```

This is a starting hypothesis, not a substitute for audit evidence.

## 7. Audit order

```text
0. Shared contract / conformance / audit infrastructure
1. Runtime kernel
2. LLM semantic vocabulary
3. Session + artifacts
4. Target-model transformation
5. Tool model + registry
6. Tool execution pipeline
7. Agent public state + inbox/queues
8. Agent run/turn state machine
9. Cancellation across Agent / LLM / tools
10. Provider abstraction + mock adapter
11. Real providers
12. Execution seams
13. Built-in tools
14. Prompt assembly + skills
15. Full compaction behavior
16. Telemetry + diagnostics + invariants
17. Integrated foundation
18. Model-backed evals
```

LLM vocabulary precedes session projection because the current session projection depends directly on message/content schema.

## 8. Validation philosophy

Correctness and behavioral effectiveness remain separate:

```text
Correctness
    spec
    /pi-parity-manifest.yaml
    canonical conformance
    language-specific tests
    property/state/concurrency/fuzz tests

Behavioral effectiveness
    model-backed evals
```

A lower eval score does not authorize changing known Pi semantics during baseline parity work.

## 9. Final principle

For every important behavior, the foundation should be able to answer:

```text
What is required?
Where does the requirement come from?
What does Pi do?
Where is Minion's implementation?
Which executable evidence proves it?
How does it fail?
How is it observed?
What risks remain?
Why were those risks fixed or deferred?
```

The current program is:

> **Build the most solid Pi-compatible Minion Agent foundation possible, while clearly separating parity-preserving quality improvements from future intentional divergences.**
