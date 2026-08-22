# Minion Agent — Fidelity Assurance Method

**Status:** Normative engineering procedure for layer audits.

## 1. Authority

Current layer audits must use:

- frozen master design;
- normative spec;
- `/pi-parity-manifest.yaml`;
- canonical `/conformance/` scenarios;
- pinned Pi source;
- approved intentional-divergence decisions.

For covered finite examples, canonical conformance is the executable oracle. For general rules outside those examples, the normative spec governs.

## 2. Per-layer workflow

Every layer follows this sequence:

```text
1. Identify normative sources
2. Audit relevant Pi source
3. Inventory implementation files
4. Inventory existing tests
5. Enumerate requirements
6. Map requirement -> implementation -> executable evidence
7. Audit failure behavior
8. Audit security
9. Audit observability
10. Audit reliability / operations
11. Audit performance / complexity
12. Audit API / serialization contracts
13. Classify every finding
14. Fix Pi parity defects
15. Fix parity-neutral hardening
16. Add/repair conformance and tests
17. Record parity-constrained risks
18. Certify the layer
```

## 3. Requirement traceability

Every normative requirement should have a stable ID, following
`process/requirement-id-convention.md` (prefixes, granularity, stability rules, and the
relationship to parity-manifest IDs).

Examples:

```text
RT-001
LLM-001
SES-001
TOOL-001
AGENT-001
```

Each requirement maps to:

```text
requirement
    -> source
    -> implementation
    -> canonical conformance or language-specific test
    -> result
```

No normative requirement may lack executable evidence.

No canonical scenario may lack a mapped requirement.

No Pi parity row may lack a disposition.

No public serialized field may lack schema/test coverage.

## 4. Implementation disposition

Each audited module receives one evidence-based disposition:

```text
RETAIN
RETAIN + HARDEN
MODIFY
REWRITE
DELETE
DEFER
```

Do not decide by directory name alone.

## 5. Existing-test audit

Existing tests are themselves audit subjects.

For every test ask:

- What requirement does it prove?
- Is that requirement still normative?
- Does it assert public behavior or an obsolete implementation detail?
- Does it duplicate canonical conformance?
- Does it exercise the real path?
- Is it deterministic?
- Does it encode a superseded contract?

Test disposition:

```text
KEEP
STRENGTHEN
MOVE TO CONFORMANCE
REWRITE
DELETE
```

Auxiliary audit reason:

```text
SUPERSEDED_CONTRACT
```

Python already enforces 100% line coverage for the currently covered core packages. This remains a floor only:

```text
100% line coverage
    !=
100% normative requirement coverage
    !=
Pi semantic parity
```

## 6. Testing layers

### Canonical conformance

Use for cross-language observable semantics and Pi compatibility.

### Language-specific unit tests

Use for Python/Rust implementation mechanics not intended as cross-language contract.

### Property/invariant tests

Examples:

```text
event sequence strictly increases
no effect survives owner disposal
double dispose is safe
request reconstruction equals dispatched request
source-order tool results stay source ordered
```

Preferred tools:

```text
Python: Hypothesis
Rust:   proptest
```

### State-machine tests

Use where lifecycle/state transitions matter, including:

- Fiber;
- Agent;
- Session;
- provider streams;
- tool execution.

### Concurrency tests

Use where applicable:

- concurrent agents;
- dependency disappearance;
- abort during provider streaming;
- abort during tools;
- parallel tool completion;
- concurrent session operations;
- shutdown during active work.

### Fuzz tests

Recommended for:

- provider parsers;
- serialized messages;
- tool arguments;
- stream chunks;
- signatures;
- session log decoding.

### Fault injection

Inject failure at every meaningful external or asynchronous boundary:

```text
before call
during call
after partial result
during cancellation
during cleanup
during listener execution
during persistence
```

## 7. Security review

For every layer inspect:

### Trust boundaries

- user input;
- model output;
- provider output;
- plugin input;
- tool input;
- filesystem/network data;
- persisted data.

### Validation

Define where untrusted data is parsed and what invalid input does.

### Authority

Define who can register, execute, mutate, and own teardown.

### Secrets

Check possible leakage via logs, errors, telemetry, session data, tool results, and provider metadata.

### Resource abuse

Check for unbounded queues, recursion, retry, output, session growth, and orphan work.

### Isolation

Check agent, scope, run, tool, and session isolation.

Security does not override Pi semantics automatically; apply the finding classification rules.

## 8. Reliability / operational review

Each applicable layer defines:

- cancellation;
- timeout;
- retry;
- cleanup ownership;
- shutdown;
- partial failure;
- dependency disappearance;
- backpressure;
- persistence atomicity;
- restart behavior.

## 9. Observability review

Each layer documents:

```text
events
logs
metrics
traces
correlation identifiers
error classification
sensitive fields
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

Telemetry/logging failure must not silently become a semantic dependency.

## 10. Performance review

Audit for:

- accidental quadratic behavior;
- unbounded memory;
- pathological allocation;
- needless serialization;
- lock contention;
- runaway concurrency;
- expensive reconstruction.

Performance hardening may happen immediately if Pi-visible semantics stay unchanged.

## 11. Documentation audit

Documentation is part of certification.

Documentation drift receives ordinary findings, usually `PARITY-NEUTRAL HARDENING`.

Current repository evidence already shows why this matters: implementation status can move ahead of README claims.

## 12. Severity

### BLOCKER

Semantic corruption, parity contradiction, invalid conformance, serious security/data-loss risk, undefined core lifecycle.

### HIGH

Major reliability problem, cancellation failure, concurrency race, silent failure, unsafe persistence, critical observability blind spot.

### MEDIUM

Robustness, maintainability, or documentation problem.

### LOW

Cleanup, ergonomics, minor documentation, optional optimization.

## 13. Language status

For each layer record implementation status separately:

```text
IMPLEMENTED
NOT_IMPLEMENTED
DEFERRED
NOT_APPLICABLE
```

Python may certify a reached layer while Rust is `NOT_IMPLEMENTED`, provided the shared contract is complete and the Rust planned phase is explicit.

Neither implementation becomes the behavioral oracle.
