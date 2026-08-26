# Layer 06 Tool Execution — Rust Implementation Assurance

## Status

```text
Shared Layer-06 contract  APPROVED (d2ec2aabfbfa89b683aecd7358d937f5b8bba606)
Python Layer 06          CERTIFIED
Rust Layer 06            CERTIFIED
Layer 06                 CROSS-LANGUAGE CERTIFIED / CLOSED
Layer 07                 ELIGIBLE / NOT STARTED
```

## Starting state

- Code: `b6edc5ca0571244f098db8db0544f08f0be332eb`
- Docs approval: `d2ec2aabfbfa89b683aecd7358d937f5b8bba606`
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`

The unrelated Phase-5 provider-design working-tree modification was not inspected, staged, or
committed. Python production and canonical/shared semantic files were not changed.

## Architecture

Rust adds `tools/execution.rs` as one typed execution layer over the certified Runtime-owned
`ToolRegistry`. It reuses `Context::tools()`, Runtime `EventBus`, the existing scope tree,
`JsonSchemaObject`, `ToolExecutionRequest`, `ToolExecutionSignal`, and the owned Layer-05
capabilities. No second registry, scope graph, or lifecycle owner was introduced, and Runtime
semantics were not redesigned.

The production entry point implements:

```text
resolve
→ prepare_arguments
→ JSON Schema validation
→ registration-ordered before-hook waterfall
→ execute + live updates
→ registration-ordered after-hook waterfall
→ ToolResultMessage normalization
```

Immediate failures skip execute and after hooks. Execute failures reach the after-hook. Errors
expose their semantic message without Rust debug/type wrappers.

`AfterToolCallOverride` structurally contains only Pi-authorized fields: content, details,
is_error, usage, and terminate. It has no representation for tool_call_id, tool_name, or
added_tool_names, so protected authority holds at every listener boundary without reproducing
Python's snapshot/restore mechanism. Zero/one/N listener composition is deterministic;
N-listener composition remains the intentional Minion architectural extension.

Batch execution deliberately emits starts in source order, emits ends from each completing
future, and restores final messages to source-index slots. The deterministic test proves source
A/B, completion B/A, starts A/B, ends B/A, results A/B. Sequential run mode or one resolved
sequential tool serializes the whole batch. Per-call failures remain isolated.

Live updates use production-owned atomic acceptance state and are ignored after the execute
future settles. Length-stop emits start/end and one error result per call while performing zero
resolution, preparation, validation, hook, or execution work. Signal plumbing is preserved in
`ToolExecutionRequest`; cancellation behavior remains Layer 09.

## Implementation and tests

- Production: `minion-agent-rust/crates/minion-agent/src/tools/execution.rs`
- Capability error normalization: `minion-agent-rust/crates/minion-agent/src/tools/definition.rs`
- Language/integration tests: `minion-agent-rust/crates/minion-agent/tests/tool_execution.rs`
- Thin canonical adapter: `minion-agent-rust/crates/minion-agent/tests/tool_execution_conformance.rs`

Focused Rust evidence:

```text
tool_execution                     13 passed
Layer-06 canonical                 10 discovered / 10 executed / 10 passed / 0 deferred
```

The canonical adapter dynamically discovers the ten approved Agent-family files, constructs
scripted real `ToolDefinition` callbacks, registers through the real `ToolRegistry`, invokes the
production executor, and observes production events/results. It does not validate arguments,
choose execution mode, schedule calls, reorder results, convert errors, suppress updates, or
implement length-stop behavior.

## Gates and regressions

Fresh successful commands from the isolated Rust implementation worktree:

```text
cargo fmt --check
    PASS

cargo clippy --workspace --all-targets --all-features -- -D warnings
    PASS

cargo test --workspace --all-features
    PASS — 183 tests/doc-tests, 0 failed

RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps
    PASS

cargo run -p xtask -- conformance verify
    PASS

uv run pytest tests/conformance/test_schema_validation.py -q --no-cov
    PASS — 165

manifest structural/unique-ID validation
    PASS — 65 / 65 unique requirement rows
```

Canonical regression inventory remains:

```text
Runtime       26
Session       20
XFORM         14
ToolRegistry   9 (+ 7 fixture-integrity tests)
Layer 06      10 / 10 / 10 / 0
```

The full Rust workspace gate covers the certified LLM, Runtime, Session, XFORM, and Layer-05
language/integration suites. Layer-05 model, registry, lifecycle, and canonical tests remain green.

## Traceability and findings

`pi-parity-manifest.yaml` received evidence-only Rust pointers for TOOL-001 through TOOL-006 and
TOOL-017 through TOOL-021. Normative rules, dispositions, Python evidence, schemas, and canonical
fixtures were unchanged.

```text
PI_PARITY_DEFECT             none
CONTRACT_ASSURANCE_DEFECT    none
PARITY_CONSTRAINED_RISK      none
PI_BEHAVIOR_UNCERTAIN        none

PARITY_NEUTRAL_HARDENING
    typed AfterToolCallOverride
    indexed source-order result slots
    jsonschema crate validation seam
    atomic late-update acceptance guard

intentional Minion architectural extension
    deterministic N-listener hook composition
```

## Verdict

```text
Python Layer 06              CERTIFIED
Rust Layer 06                CERTIFIED
Layer 06                     CROSS-LANGUAGE CERTIFIED / CLOSED
Rust certified through       Layer 06
Layer 07                     ELIGIBLE / NOT STARTED
```
