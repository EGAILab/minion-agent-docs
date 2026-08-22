# Minion Agent — Foundation Fidelity & Assurance Audit

**Date:** 2026-08-22  
**Status:** Repo-grounded revision of the proposed normative engineering process for the current Pi-alignment program  
**Repository checked:** `EGAILab/minion-agent` `main` on 2026-08-22  
**Primary goal:** Reproduce Pi observable behavior and semantics as closely as practical, while building a documented evidence base for later production hardening.

---

## 1. Purpose

Minion Agent is currently in a one-time realignment phase against the frozen 2026-08-20 design and the adopted Pi baseline.

The objective of this audit is broader than simply identifying modules to rewrite.

For every layer of the Minion Agent foundation, the audit must establish:

- whether the implementation matches the frozen design;
- whether Pi-visible semantics match the adopted Pi baseline;
- whether existing tests actually prove the current normative behavior;
- whether test coverage is complete for all known contracts and invariants;
- whether documentation accurately describes the layer;
- whether security, reliability, observability, operability, performance, and maintainability risks are understood;
- whether those risks can be fixed without changing Pi-visible semantics;
- which risks must be deferred to a later post-parity hardening phase.

The result should be a foundation that is not merely “passing tests”, but whose behavior, implementation, tests, documentation, and known risks are traceable and explainable.


### 1.1 Current repository baseline

The current monorepo layout relevant to this audit is:

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

The canonical Pi parity manifest currently lives at:

```text
/pi-parity-manifest.yaml
```

It is **not** currently located under `/conformance/`.

The shared `conformance/` directory contains language-neutral canonical scenario data. Python and Rust runners consume that shared contract from their language-specific implementation trees.

The Python implementation currently contains these major packages:

```text
minion_agent/
├── runtime/
├── llm/
├── session/
├── telemetry/
├── agent/
├── agent_loop/
└── tools/
```

The Rust implementation currently contains the runtime foundation only. Later semantic layers such as LLM, session, tools, Agent, agent loop, and providers are not yet implemented in Rust.

Later audit layers such as filesystem/shell/subprocess execution seams, built-in tools, skills, full compaction support, real providers, and model-backed evals are part of the planned foundation but are not all present in the current repository.

The audit MUST distinguish:

```text
CURRENTLY_IMPLEMENTED
PLANNED_NOT_IMPLEMENTED
DEFERRED
NOT_APPLICABLE
```

rather than treating every planned layer as already existing.

---

## 2. Governing priority

The current project priority remains:

> **Pi behavioral fidelity first.**

Pi source at the adopted revision is the default behavioral compatibility oracle for agent-loop, LLM/provider, message transformation, tool, session, and related harness behavior.

The audit MUST NOT silently replace Pi behavior with a cleaner, safer, more abstract, or more production-oriented behavior merely because the alternative appears preferable.

If a production-quality improvement changes Pi-visible semantics, it is not an ordinary hardening fix. It is a potential future intentional divergence and must be deferred unless the frozen design is formally revised.

This audit therefore separates two goals:

```text
Stage 1 — Pi Fidelity Foundation
    reproduce Pi-visible behavior
    correct Minion parity defects
    apply parity-neutral hardening
    document all other production risks

Stage 2 — Post-Parity Hardening
    review documented risks
    improve security/reliability/operability/performance
    explicitly approve any intentional divergence from Pi
```

---

## 3. The key decision rule

Every audit finding must answer:

```text
Does fixing this issue change Pi-visible behavior?
```

### If NO

The issue is **parity-neutral hardening**.

It may be fixed during the current fidelity phase.

Examples:

- redacting secrets from logs;
- avoiding unnecessary memory copies;
- improving internal type safety;
- adding bounded internal buffers where externally invisible;
- eliminating resource leaks;
- adding diagnostics;
- improving test determinism;
- making cleanup idempotent;
- strengthening input validation when valid Pi-compatible inputs behave identically.

### If YES

The issue is **parity-constrained**.

The current baseline should preserve Pi-compatible behavior, and the issue must be recorded for later hardening.

Examples may include:

- changing retry behavior that alters caller-visible timing or failure semantics;
- restricting a tool capability that Pi exposes;
- changing queue or continuation behavior;
- changing model-visible transformation behavior;
- changing error settlement semantics;
- changing turn/run lifecycle behavior.

### If unclear

The issue is **Pi behavior uncertain**.

The required action is:

```text
stop
-> inspect Pi source
-> update manifest/spec/conformance
-> then decide
```

Do not resolve uncertainty using generic best practice.

---

## 4. Required finding classifications

Every finding must have exactly one of these dispositions.

### A. PI PARITY DEFECT IN MINION

Minion's current behavior differs from the adopted Pi semantics.

**Action:** fix now.

### B. PARITY-NEUTRAL HARDENING

The implementation can be improved without changing observable Pi-compatible behavior.

**Action:** fix now when practical.

### C. PARITY-CONSTRAINED RISK

The issue is real, but fixing it would change observable Pi-compatible behavior.

**Action:** document now; defer the semantic decision to post-parity hardening.

### D. PI BEHAVIOR UNCERTAIN

The current evidence is insufficient to determine the correct Pi-compatible behavior.

**Action:** source-audit Pi before implementation changes.

No finding may remain without a disposition.

---

## 5. Bottom-up audit strategy

The audit proceeds from the lowest foundational layers upward.

A higher layer should not be treated as stable while it depends on an uncertified lower layer.

Recommended order, adjusted to the current repository dependency structure:

```text
0. Shared contract / conformance / audit infrastructure
   /pi-parity-manifest.yaml
   conformance/schema/
   conformance/runtime/
   conformance/session/
   conformance/agent/

1. Runtime kernel
   Context
   Fiber
   services
   effects
   events
   scopes
   reactive dependencies
   Python + Rust

2. LLM semantic vocabulary
   content blocks
   messages
   usage
   diagnostics
   deferred state
   stream vocabulary
   Python first; Rust when Phase 2 reaches it

3. Session + artifacts
   append-only log
   serialization
   projection / derive_messages
   fork/reset
   session-level compaction event/projection semantics where currently implemented
   artifact store
   request reconstruction

4. Target-model transformation

5. Tool model + registry

6. Tool execution pipeline

7. Agent public state + inbox/queues

8. Agent run/turn state machine

9. Cancellation and lifecycle propagation across Agent / LLM / tools

10. Provider abstraction + mock adapter

11. Real providers

12. Execution seams
    filesystem
    shell
    subprocess

13. Built-in tools

14. Prompt assembly + skills

15. Full compaction behavior

16. Telemetry + diagnostics + invariants

17. Integrated foundation

18. Model-backed evals
```

LLM vocabulary is audited before session projection because the current session projection directly depends on the message/content schema. Certifying session projection before replacing the obsolete LLM vocabulary would make that certification immediately stale.

The order may be adjusted when a dependency requires it, but audit ownership and certification boundaries must remain explicit. A planned layer that is not yet implemented should be recorded as `PLANNED_NOT_IMPLEMENTED`; it is not a certification failure merely because its implementation phase has not started.

---

## 6. Per-layer audit workflow

Each layer follows the same process.

```text
1. Identify authoritative design/spec/manifest rules, including `/pi-parity-manifest.yaml`
2. Audit relevant Pi source
3. Inventory implementation files
4. Inventory existing tests
5. Map requirements -> implementation -> tests
6. Identify semantic gaps
7. Audit failure behavior
8. Audit security
9. Audit observability
10. Audit reliability and operational behavior
11. Audit performance/complexity risks
12. Audit API and serialization contracts
13. Classify all findings
14. Fix parity defects
15. Fix parity-neutral hardening
16. Add/repair conformance and tests
17. Document deferred parity-constrained risks
18. Certify the layer
```

---

## 7. Requirement traceability

“100% complete” must mean complete traceability, not an impossible claim that every conceivable runtime state has been tested.

Every normative requirement should have a stable requirement ID.

Examples:

```text
RT-001
RT-002

SES-001
SES-002

LLM-001
LLM-002

TOOL-001
AGENT-001
```

Each requirement should map to:

```text
requirement
    -> source
    -> implementation
    -> canonical conformance or language-specific test
    -> result
```

Example:

| Requirement | Source | Implementation | Test | Status |
|---|---|---|---|---|
| AGENT-014 | `spec/agent.md` | `agent_loop/driver.py` | `initial-steering-before-first-request` | PASS |

There should be:

- no normative requirement without executable evidence;
- no canonical scenario without a mapped requirement;
- no Pi parity manifest row without a disposition;
- no public serialized field without schema/test coverage.

---

## 8. Implementation classification

Every audited module should be classified as:

```text
RETAIN
RETAIN + HARDEN
MODIFY
REWRITE
DELETE
DEFER
```

The classification must be evidence-based.

Example:

```text
runtime/service.py

design alignment        PASS
Pi relevance            N/A / intentional divergence
runtime conformance     PASS
failure semantics       PASS
security                PASS
observability           PARTIAL

decision:
    RETAIN + HARDEN
```

Example:

```text
agent_loop/driver.py

design alignment        FAIL
Pi lifecycle parity     FAIL
terminate semantics     FAIL
abort propagation       FAIL
old tests encode superseded design

decision:
    REWRITE
```

The audit must not assume in advance that a module must be rewritten simply because the design changed.

Likewise, existing code must not be retained simply because it already exists.

---

## 9. Current repo-grounded migration boundary

The current repository supports a stronger, evidence-based starting hypothesis.

### 9.1 Strong retain candidates

Audit first and retain where revised conformance remains green:

```text
runtime/
    Context
    Fiber
    services
    effects
    event dispatch
    scopes
    scoped registries
    plugin lifecycle

session/
    append-only log substrate
    artifact store
    storage/event mechanics

test infrastructure
    deterministic fixtures
    property-test support
    conformance runners
```

The Rust implementation currently reinforces the runtime-retention hypothesis: its implemented surface is the runtime kernel, with corresponding runtime tests.

### 9.2 Strong rewrite / heavy-realignment candidates

Current source already demonstrates superseded assumptions in these areas:

```text
llm/content.py
llm/messages.py
agent_loop/driver.py
```

The current LLM vocabulary lacks the frozen Pi-aligned replay/signature and richer assistant/tool-result fields required by the new design.

The current agent loop explicitly models:

```text
step = one model request plus its tools
turn = zero or more steps
```

and currently interprets all-results `terminate` as a hard break before turn-stopping, while cancellation is cooperative and boundary-only. These assumptions conflict with the frozen Pi-aligned semantics and make `agent_loop/driver.py` a strong rewrite candidate.

### 9.3 Tools must be split by responsibility

Do not classify the entire `tools/` package as one rewrite unit.

Current structure includes:

```text
tools/
├── batch.py
├── decisions.py
├── definition.py
├── events.py
├── execute.py
├── plugin.py
├── registry.py
└── result.py
```

Recommended audit stance:

```text
tool model / registry / plugin ownership
    -> AUDIT FIRST
    -> likely RETAIN + MODIFY where compatible

tool execution semantics
    -> HEAVY REALIGN / likely REWRITE
```

The current execution path already converts several failure modes into tool error results, but it does not yet fully encode the frozen Pi-compatible prepare/validate/before/execute/after boundary semantics. In particular, post-execute failure replacement and the explicit prepare-arguments stage require dedicated audit and likely restructuring.

### 9.4 Session must be split by substrate vs projection

Current session structure includes:

```text
session/
├── artifacts.py
├── derive.py
├── events.py
├── log.py
├── operations.py
├── request_header.py
└── service.py
```

Recommended audit stance:

```text
log / artifact / storage substrate
    -> strong RETAIN candidate

derive / serialization / request reconstruction
    -> MODIFY / REALIGN against new message vocabulary
```

References to compaction at this stage mean only the session-level compaction event/projection semantics that are already present. A complete compaction subsystem is a later layer.

### 9.5 This remains a hypothesis, not a substitute for audit

Every module must still receive one evidence-based disposition:

```text
RETAIN
RETAIN + HARDEN
MODIFY
REWRITE
DELETE
DEFER
```

---

## 10. Test audit

Existing tests are themselves audit subjects.

Every existing test should answer:

- Which normative requirement does this test prove?
- Is that requirement still valid?
- Is the test asserting observable behavior or an obsolete implementation detail?
- Is the same behavior already covered by canonical conformance?
- Does the test exercise the real production path?
- Is it deterministic?
- Does it encode superseded 2026-08-18 semantics?

Each test should be classified:

```text
KEEP
STRENGTHEN
MOVE TO CONFORMANCE
REWRITE
DELETE
```

Passing obsolete tests are not evidence of parity.


The Python project already enforces `fail_under = 100` line coverage for the core implemented packages. This is valuable as a floor, but it MUST NOT be treated as proof of semantic completeness or Pi parity.

The current repository is an explicit example of why:

```text
100% line coverage
    does not imply
100% normative requirement coverage
    and does not imply
Pi semantic parity
```

Tests can cover every line while still encoding a superseded contract.

For audit reporting, a test may use an auxiliary reason such as:

```text
SUPERSEDED_CONTRACT
```

while its final disposition remains one of:

```text
KEEP
STRENGTHEN
MOVE TO CONFORMANCE
REWRITE
DELETE
```

---

## 11. Testing layers

### 11.1 Canonical conformance

Use for:

- cross-language observable semantics;
- Pi-visible behavior;
- public serialized contract shape;
- exact finite compatibility examples.

Canonical conformance remains the executable oracle for covered cases.

### 11.2 Language-specific unit tests

Use for:

- Python internals;
- Rust internals;
- language-specific error plumbing;
- type guarantees;
- implementation-specific adapter mechanics.

### 11.3 Property/invariant tests

Use for persistent invariants such as:

```text
event sequence strictly increases
no effect survives owner disposal
double dispose is safe
every committed request reconstructs identically
source-order tool results remain source ordered
session derivation never emits duplicate retained-tail entries
```

Preferred tools:

```text
Python: Hypothesis
Rust:   proptest
```

### 11.4 State-machine tests

Recommended for:

- Fiber lifecycle;
- Agent state;
- Session lifecycle;
- provider stream state;
- tool execution state.

### 11.5 Concurrency tests

Where applicable:

- concurrent agents;
- service disappearance during dependency changes;
- abort during provider stream;
- abort during tool execution;
- parallel tool completion;
- concurrent session append;
- shutdown during active work.

### 11.6 Fuzz tests

Recommended for:

- provider parsers;
- message serialization;
- tool argument parsing;
- stream chunk parsing;
- signature parsing;
- log decoding.

### 11.7 Fault injection

Inject failure at every external/asynchronous boundary:

```text
before call
during call
after partial result
during cancellation
during cleanup
during listener execution
during persistence
```

---

## 12. Security review during parity work

Security is reviewed now, but it does not automatically override Pi semantics.

For every layer, inspect:

### Trust boundaries

- user input;
- model output;
- provider output;
- plugin input;
- tool input;
- filesystem/network input;
- persisted data.

### Validation

- where external data is parsed;
- who validates it;
- what invalid input does;
- whether invalid state can enter core semantics.

### Authority

- who can register;
- who can execute;
- who owns teardown;
- who can mutate shared state.

### Secrets

Check whether secrets can leak through:

- logs;
- errors;
- telemetry;
- session persistence;
- tool results;
- provider metadata.

### Resource abuse

Check for:

- unbounded queues;
- unbounded recursion;
- unbounded retry;
- unbounded tool output;
- unbounded session growth on hot paths;
- orphan background work.

### Isolation

Check:

- cross-agent visibility;
- scope leakage;
- retained run-local state;
- tool state leakage;
- session identity crossover.

Security findings must be classified using the parity decision rule.

---

## 13. Reliability and operational review

Each layer should define:

- cancellation behavior;
- timeout behavior;
- retry behavior;
- cleanup ownership;
- shutdown behavior;
- partial failure semantics;
- dependency disappearance behavior;
- backpressure or queue limits;
- persistence atomicity where applicable;
- restart behavior where persistence exists.

Potential production concerns are recorded even when parity prevents immediate changes.

---

## 14. Observability review

Each layer should document:

```text
events
logs
metrics
traces
correlation identifiers
error classification
sensitive fields that must not be recorded
```

Recommended correlation vocabulary:

```text
runtime_id
agent_instance_id
session_id
run_id
turn_id
request_id
tool_call_id
provider_request_id
```

Observability must be sufficient to reconstruct a failure path without changing semantic behavior.

Logging and telemetry failure should not become an implicit semantic dependency unless explicitly designed that way.

---

## 15. Performance review

The current phase does not optimize away Pi semantics.

Performance review exists to detect:

- accidental quadratic behavior;
- unbounded growth;
- pathological allocations;
- needless serialization;
- lock contention;
- runaway concurrency;
- expensive reconstruction.

Where possible, document expected complexity.

Example targets:

```text
service lookup                  expected O(1)
event dispatch                  O(admitted listeners)
session append                  no whole-history rewrite
tool batch execution            bounded by configured concurrency
artifact lookup                 bounded content-addressed lookup
```

Performance fixes that preserve semantics may be applied immediately.

Performance fixes that change Pi-visible behavior are deferred.

---

## 16. Documentation required per layer

Each certified layer should have an assurance document containing:

1. Purpose and ownership
2. Dependencies
3. Normative contract
4. Pi mapping
5. Public API surface
6. Serialization contract
7. Invariants
8. Failure model
9. Security review
10. Reliability/operational review
11. Observability contract
12. Performance considerations
13. Test strategy
14. Conformance mapping
15. Implementation classification
16. Findings and dispositions
17. Deferred risks
18. Certification status

Recommended location:

```text
minion-agent-docs/
└── assurance/
    ├── README.md
    ├── fidelity-assurance-method.md
    ├── runtime.md
    ├── session.md
    ├── llm.md
    ├── tools.md
    ├── agent.md
    ├── providers.md
    ├── execution.md
    └── foundation-release-gate.md
```


### 16.1 Documentation drift is itself an audit finding

Documentation accuracy is part of certification, not a cleanup task after implementation.

For example, the current Python README is already stale relative to the repository: it says that the agent loop and tool subsystem “follow”, while both `agent_loop/` and `tools/` are present, and it refers to an `evals/` location that is not currently present in the Python repository.

Documentation drift should therefore receive ordinary findings and dispositions, for example:

```text
DOC-001
Severity: MEDIUM
Classification: PARITY_NEUTRAL_HARDENING
Finding: README implementation status and repository layout are stale
Action: update during current fidelity work
```

Documentation fixes that do not alter Pi-visible behavior are parity-neutral hardening and should normally be completed during the current stage.

---

## 17. Layer certification gate

A layer is ready to certify only when:

```text
Design alignment                         PASS
Pi parity                                PASS / N/A / documented divergence
Normative spec                           COMPLETE
Parity manifest                          COMPLETE
Canonical conformance                    PASS
Python tests                             PASS where Python implements the layer
Rust implementation status               RECORDED
Rust tests/conformance                    PASS where Rust implements the layer
Property/invariant tests                 PASS where applicable
Concurrency tests                        PASS where applicable
Fault-injection tests                    PASS where applicable
Security review                          COMPLETE
Reliability review                       COMPLETE
Observability review                     COMPLETE
Performance review                       COMPLETE
Public API review                        COMPLETE
Documentation                            COMPLETE
All findings classified                  COMPLETE
No unresolved Pi uncertainty             PASS
No unresolved parity defect              PASS
Deferred parity-constrained risks         RECORDED
```

For Rust, record one of:

```text
IMPLEMENTED
NOT_IMPLEMENTED
DEFERRED
NOT_APPLICABLE
```

A Python layer may complete its certification while Rust is legitimately `NOT_IMPLEMENTED` for that phase, provided the shared spec/conformance contract is complete and the Rust status/planned phase is explicit. This preserves the agreed Python-leading, Rust-following development rhythm without making Python the behavioral oracle.

This gate certifies:

> **Pi-fidelity foundation quality**

It does not claim that all known production risks have already been eliminated.

---

## 18. Severity

Suggested severity model:

### BLOCKER

- semantic corruption;
- Pi parity contradiction;
- invalid conformance;
- data-loss risk;
- serious security flaw;
- undefined core lifecycle behavior.

### HIGH

- significant reliability risk;
- cancellation failure;
- silent error;
- major observability blind spot;
- concurrency race;
- unsafe persistence behavior.

### MEDIUM

- robustness issue;
- maintainability concern;
- partial documentation;
- non-critical production hardening gap.

### LOW

- cleanup;
- ergonomics;
- minor documentation;
- optional optimization.

For the current fidelity stage:

- unresolved parity BLOCKER/HIGH findings block certification;
- parity-neutral BLOCKER/HIGH hardening should normally be fixed;
- parity-constrained risks may remain only if explicitly documented and accepted for baseline parity.

---

## 19. Relationship to evals

Evals are not the mechanism for proving Pi semantic correctness.

The validation stack remains:

```text
Correctness
    spec
    /pi-parity-manifest.yaml
    shared canonical conformance/
    Python/Rust language-specific tests
    property/state/concurrency/fuzz tests

Behavioral effectiveness
    model-backed evals
```

The current shared conformance families are:

```text
conformance/runtime/
conformance/session/
conformance/agent/
conformance/schema/
```

Language-specific runners may live under each implementation, but they must remain thin adapters over the shared canonical cases.

Pi-style evals answer:

> “Does this agent configuration perform well on real tasks?”

Future Minion eval infrastructure may also compare interventions such as:

```text
skill
tool
tool set
MCP server
plugin
prompt
model
provider
memory strategy
compaction strategy
agent policy
```

using paired treatment/control experiments.

That future eval layer must remain separate from the current Pi fidelity gate.

A lower eval score does not authorize changing a known Pi semantic during baseline parity work.

---

## 20. Post-parity hardening phase

After the Pi-compatible foundation is certified, the accumulated risk register becomes the input to a separate hardening program.

At that point the project may deliberately ask:

```text
Should Minion remain Pi-compatible here?
Or should it intentionally improve the behavior?
```

Any intentional observable divergence must follow the normal governance path:

```text
risk finding
    -> design decision
    -> explicit divergence
    -> spec update
    -> conformance update
    -> Python/Rust implementation
    -> migration/compatibility review
```

No divergence should arise accidentally from a “production cleanup”.

---

## 21. Final project principle

The audit should produce a foundation where every important behavior can answer:

```text
What is the required behavior?
Where does that requirement come from?
What does Pi do?
Where is Minion's implementation?
Which test proves it?
How does it fail?
How is it observed?
What risks remain?
Why were those risks fixed now or deferred?
```

The current program is therefore:

> **Build the most solid Pi-compatible Minion Agent foundation we can, while clearly separating parity-preserving engineering quality from future intentional improvements.**

Pi fidelity is the current semantic priority.

Assurance ensures that fidelity is implemented deliberately rather than accidentally.

Post-parity hardening comes next.


---

## 22. Repo-grounded revision notes

This revision incorporates direct inspection of the current `EGAILab/minion-agent` monorepo.

Confirmed repository facts reflected above:

- canonical parity manifest is currently `/pi-parity-manifest.yaml`;
- shared canonical conformance families are at repository root;
- Python currently implements runtime, LLM, session, telemetry, agent, agent loop, and tools;
- Rust currently implements the runtime foundation only;
- Python already enforces 100% line coverage for the core implemented packages;
- existing Agent-loop source still carries superseded turn/terminate/cancellation assumptions;
- current LLM content/message vocabulary is narrower than the frozen Pi-aligned contract;
- tool registry/model and tool execution should be audited as separate responsibilities;
- session storage/artifact substrate and session projection/reconstruction should be audited separately;
- documentation drift already exists and is therefore explicitly part of the assurance process.

These observations refine execution order and audit scope. They do not alter the governing semantic principle:

> **Pi fidelity remains the current priority; production improvements that change Pi-visible semantics are documented and deferred unless formally approved as intentional divergence.**
