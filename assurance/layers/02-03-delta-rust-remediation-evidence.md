# Rust Layer 02/03 post-certification delta remediation evidence

Date: 2026-08-24

## Contract review

- reviewed shared candidate: `minion-agent@c5f6bb1491d39900f5ec390c3f5aeb367218cc60`
- reviewed spec candidate: `minion-agent-docs@5a375840850b547698734b00926d4a038fcd8e1d`
- prior broad delta review: `minion-agent-docs@6d2944ed106032d2f65b40c49a4d37e4fa55aee1`
- narrow SES-F007 approval: `minion-agent-docs@cb468b8f1b416ea688f0f65f491d1abba5703eca`

Formal Rust implementation-owner verdicts:

```text
SES-F007
    APPROVED

LAYER 02 DELTA CONTRACT
    APPROVED

LAYER 03 DELTA CONTRACT
    APPROVED
```

The SES-F004 history correction is approved. A/C/D/F were unaffected by the narrow remediation.

## Rust remediation

- branch: `fix/rust-layer02-03-delta-remediation`
- remediation head: `408bd1f9e1147711ef0d16381937da035ece580c`
- PR: <https://github.com/EGAILab/minion-agent/pull/5>
- merge: `7e45cd124762d1d7ba57e0fd0eca0a08adcb6922`

Changes:

- LLM-F011: `ToolResultMessage.tool_name` is again a required `String`; missing serde input fails,
  and the real non-default name round-trips.
- SES-F004: Rust retains `session/compaction`; canonical evidence reads real committed event kinds.
- SES-F005: typed role-specific content enums remain unchanged; no dynamic workaround was added.
- SES-F006: the runner invokes real `Session::fork` and maps the typed boundary error; it does not
  prevalidate.
- SES-F007: no production semantic change was required. `Session::compact` retains one event-log
  mutex across reset-floor/surface/provenance calculation and marker append. A multithreaded
  regression checks committed compaction provenance relative to append/reset/compact mutation.
- SES-F008: the namespace segment now excludes hyphens while later path segments retain them,
  exactly matching the canonical expression.
- Session conformance discovers 19 scenarios, executes 18, and explicitly defers only
  `request-reconstruction-after-target-transform.yaml` to Layer 04.

The conformance adapter remains thin: it translates canonical typed input, invokes real Session
APIs, reads real committed events, maps typed errors, and normalizes output. It does not invent tool
names, rewrite event identities, pre-check fork boundaries, implement compaction/derivation,
schedule concurrency, or simulate Agent/XFORM semantics.

## Verification

Fresh PR-head gates:

```text
cargo fmt --all -- --check
    PASS

cargo clippy --workspace --all-targets --all-features -- -D warnings
    PASS

cargo test --workspace --all-features
    PASS — 128 passed, 0 failed

RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps
    PASS

cargo run -p xtask -- conformance verify
    PASS
```

The complete workspace test suite was rerun on merged `main` at
`7e45cd124762d1d7ba57e0fd0eca0a08adcb6922`: 128 passed, 0 failed.

Session canonical disposition:

```text
discovered: 19
executed: 18
deferred: 1
deferred scenario: request-reconstruction-after-target-transform
```

No new `PI_PARITY_DEFECT`, `PI_BEHAVIOR_UNCERTAIN`, or
`CONTRACT_ASSURANCE_DEFECT` was found during remediation.

## Handoff disposition

```text
Rust ready for Layer-02 final delta certification audit?
    YES

Rust ready for Layer-03 final delta certification audit?
    YES, after Layer 02 closes

Layer 04 started?
    NO
```

This document reports Rust readiness only. It does not change the shared certification status.
The parity manifest's stale Rust evidence pointers remain for the shared assurance owner to update
during final closure using the final implementation and merge paths above.
