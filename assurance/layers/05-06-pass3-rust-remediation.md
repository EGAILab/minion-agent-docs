# PASS 3 — Rust Layer-06 Remediation and Re-Certification

Date: 2026-08-26

## Starting state and authority

```text
minion-agent       1779f0c25c373f5e81abd5b2df8b1621c705042f
minion-agent-docs  081cd9ba3e57733717a184dab134cb329fc88ec0
pinned Pi          b7bb00b936dbe21b8e160b3e89efdec361846699
Python Layer 06    CERTIFIED
Rust Layer 06      IN_REMEDIATION
```

Work was performed on isolated code/docs worktrees. The unrelated Phase-5 working-tree change was
not inspected, staged, or modified. Python production and tests, shared specifications, canonical
fixtures, Layer-05 semantics, and Layer 07 were not changed.

## Architecture

Layer 06 remains an execution layer over the certified Runtime-owned `ToolRegistry`, existing
`ToolDefinition` capabilities, `JsonSchemaObject`, EventBus, and `ToolExecutionSignal`. No second
registry or scope tree was introduced and Runtime lifecycle semantics were not redesigned.

Parallel execution now has two explicit internal phases:

1. `preflight_one` resolves, prepares, validates, and runs before hooks sequentially in source
   order, producing either an immediate result or a `PreparedToolCall`;
2. only after every source call settles preflight does
   `execute_and_finalize_prepared` run prepared calls concurrently.

Sequential batches still run each call's complete pipeline before the next call. Length-stop
remains an early branch that emits required start/end events and generated error results without
resolution or callback invocation.

## Finding remediation and RED → GREEN evidence

### IR-L06-001 — sequential preflight barrier

Before the fix,
`parallel_preflight_settles_in_source_order_before_any_prepared_execute` observed:

```text
start:a, start:b, before:a, execute:a, end:a, before:b, end:b
```

instead of the Pi sequence. After the split it observes:

```text
start:a, before:a, start:b, before:b, end:b, execute:a, end:a
```

`parallel_batch_preflights_every_valid_call_before_either_execute_begins` also failed before the
split (`before:a, execute:a, before:b, execute:b`) and now proves both calls complete preflight
before either execute body starts. Existing deterministic tests continue to prove concurrent
overlap after the barrier, completion-order end events, source-order results, sequential contagion,
and isolated immediate failures.

Status: **RESOLVED**.

### IR-L06-002 — non-Pi nullish clear states

`AfterToolCallOverride` now exposes only omit-or-concrete replacement for `details`, `usage`, and
`terminate`; nested `Option<Option<T>>` clear states and clear-valued builders were removed.

For raw whole-result listeners, `normalize_successful_after_result` preserves the accumulated
prior value whenever one of those fields is nullish, while restoring `tool_call_id`, `tool_name`,
and execute-produced `added_tool_names` at every listener boundary. A later listener therefore
sees accumulated concrete replacements and never a predecessor's attempted clear. Hook failures
travel through a distinct `WaterfallError::ListenerFailed` path and still replace the entire
prior result with a generated error rather than being normalized as a successful override.

The focused raw/helper waterfall test failed before the repair with both listener observations
equal to `(None, None, None)`; it now proves initial preservation, concrete replacement,
listener-to-listener preservation, and the correct final values. Existing raw failure,
protected-field, and short-circuit tests remain green.

Status: **RESOLVED**.

### IR-L06-003 — unknown-tool text

Rust continues to emit exactly `Tool nonexistent not found`, matching pinned Pi. The corrected
cross-layer canonical assertion passes without adapter rewriting.

Status: **RESOLVED / ALREADY CONFORMANT**.

### IR-L06-004 — generated error details

The centralized generated-error path now supplies an explicit empty JSON object for `details`.
Focused language evidence covers unknown tool, prepare, validation, before-hook, execute,
after-hook, and length-stop errors. The execute-failure after hook observes `{}` before any
successful override. After-hook failure replaces prior details/usage/terminate with a plain
generated error, while a successful tool's explicit details remain unchanged.

Status: **RESOLVED**.

### IR-L06-005 — original arguments in updates

`ToolExecutionUpdate` now contains `arguments`. The update callback captures the source
`ToolCall.arguments` before preparation. The focused test proves that execute receives
`{raw: 1, prepared: true}` while the update event exposes exactly `{raw: 1}`, together with the
source call id, tool name, and partial result. Late updates remain production-suppressed.

Status: **RESOLVED**.

## Canonical adapter and runner audit

The Rust Layer-06 adapter discovers Layer-06-owned scenario paths from the canonical manifest's
Layer-06 requirement evidence rather than a fixed scenario-name/count list. Current discovery is:

```text
discovered  11
executed    11
passed      11
deferred     0
```

The scenario names are:

1. `after-hook-failure-replaces-result-with-tool-error`
2. `before-hook-failure-becomes-tool-error`
3. `execute-failure-becomes-tool-error`
4. `late-tool-update-ignored`
5. `length-stop-executes-no-tools`
6. `parallel-preflight-settles-sequentially-before-execute`
7. `parallel-tool-completion-vs-message-order`
8. `prepare-arguments-failure-becomes-tool-error`
9. `schema-validation-failure-becomes-tool-error`
10. `tool-batch-parallel`
11. `tool-batch-sequential-contagion`

The corrected pre-existing `an-unknown-tool-does-not-serialize-a-batch` cross-layer fixture also
passes independently, proving exact unknown text and present-empty generated-error details.

The adapter records production start/end/update events and scripted callback entry only. It does
not implement preflight, choose scheduling, reorder traces/results, reconstruct original update
arguments, synthesize `details={}`, or rewrite error text.

## Rust language evidence

`tool_execution.rs` now has 20 passing tests covering the complete Layer-06 production seam,
including the two preflight-barrier tests, raw/helper nullish authority, every generated-error
path, original-vs-prepared update arguments, late suppression, dual parallel ordering,
sequential contagion, failure isolation, metadata, signal pass-through, length-stop isolation,
source identity, JSON Schema validation, and stage reachability.

## Verification

Fresh commands and results:

```text
cargo fmt --all -- --check
    PASS

cargo clippy --workspace --all-targets --all-features -- -D warnings
    PASS

cargo test --workspace --all-features
    PASS — 191 Rust tests, 0 failed; doc tests also passed

RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps
    PASS

cargo run -p xtask -- conformance verify
    PASS

Python schema-only validation (coverage disabled for this focused gate)
    PASS — 166

manifest parse / unique-ID audit
    PASS — 66 / 66 unique
```

Regression evidence from the full Rust run:

```text
Runtime     90 Rust test functions green, including 26 canonical scenarios
LLM         34 green
Session     10 Rust test functions green, including 20 canonical scenarios
XFORM       14 canonical scenarios green
Layer 05    23 Rust test functions green; 9 canonical + 7 harness checks
Layer 06    20 language tests green; 11 owned canonical + corrected unknown cross-layer probe
```

## Manifest and traceability

The manifest remains 66/66 unique requirements. Rust evidence pointers were refreshed for
`TOOL-005`, `TOOL-019`, `TOOL-021`, and `TOOL-023`. `TOOL-023` is no longer pending. No shared
semantic rule or Layer-05 disposition changed.

## Findings and closure

```text
PI_PARITY_DEFECT             none active
CONTRACT_ASSURANCE_DEFECT    none active
PI_BEHAVIOR_UNCERTAIN        none active
PARITY_CONSTRAINED_RISK      none active

PARITY_NEUTRAL_HARDENING
    typed AfterToolCallOverride
    PreparedToolCall/indexed source-order result reconstruction
    per-listener successful-result normalizer

intentional Minion architectural extension
    ordered zero/one/N hook composition
```

The shared contract is unchanged. Python and Rust produce the same corrected canonical outcomes.
Structural signal plumbing remains intact; Layer-09 cancellation behavior was not implemented.

```text
Python Layer 06    CERTIFIED
Rust Layer 06      CERTIFIED
Layer 06           CROSS-LANGUAGE CERTIFIED / CLOSED
Layers 01–06       CROSS-LANGUAGE CERTIFIED / CLOSED
Layer 07           ELIGIBLE / NOT STARTED
```
