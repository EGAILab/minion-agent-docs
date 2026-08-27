# Layer 07 — Rust Implementation, Conformance, and Certification

**Status:** CERTIFIED. Layer 07 is cross-language certified and closed. Layer 08 was not started.

## Authority and starting state

- code baseline: `19ecb88ded6adc89847467a14f459b041735abc5`
- docs baseline containing approval: `444e0e582007dc73a6b6d058ec8535387804fc00`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- approval artifact: `assurance/layers/07-agent-state-inboxes-rust-rereview-3.md`

## Architecture

Rust adds a typed `agent` module:

- `identity.rs`: immutable definition defaults, exact seven-value thinking vocabulary, and idle/running status.
- `inbox.rs`: typed `Message` envelopes, two FIFO queues, exact claim policies, clear/pending operations, and an independent level-triggered wake latch.
- `instance.rs`: immutable identity/dependency handles, one coherent mutex-protected mutable state object, a status/reset serialization gate, Session-backed messages, live ToolRegistry projection, Agent-level Inbox delegates, and typed reset errors.

Session, Context, scope, Message, ModelIdentity, and ToolRegistry are reused. No duplicate transcript, registry, scope tree, or run-loop mechanism was introduced. State locks are not held while calling Session or ToolRegistry/Context seams.

## Contract realization

- AgentMessage is the existing typed `Message` enum; User, Assistant, and ToolResult variants are proven.
- `system_prompt`, `model`, and explicit seven-value `ThinkingLevel` are per-instance mutable state; `xhigh` serializes verbatim.
- messages are derived live through `Session::derive_messages()`.
- reset invokes `Session::reset()`, leaving physical history intact and effective messages empty.
- tools are a live `ToolRegistry::visible(scope)` projection; absent context/registry is empty, and withdrawal is observed immediately.
- Inbox uses two synchronized `VecDeque` values; ALL and ONE_AT_A_TIME preserve FIFO and queue independence.
- wake is independent of queue content; clear and reset preserve it; take consumes only wake.
- runtime field vocabulary and reset behavior exist without implementing Layer-08 transition timing.
- active reset returns the exact semantic error and mutates nothing.

## TDD evidence

Meaningful RED checkpoints were observed before production implementation:

- Inbox tests initially failed because `minion_agent::agent` did not exist.
- Agent state/reset tests initially failed because AgentDefinition/Instance/Status/ThinkingLevel were absent.
- Agent-level Inbox delegation tests initially failed for missing steer/follow-up/inject/clear/pending methods.
- `ThinkingLevel::XHigh` initially serialized as `x-high`; the exact `xhigh` regression failed, then passed after the explicit mapping.

Focused GREEN evidence:

- `agent_inbox`: 4 passed.
- `agent_state`: 6 passed.
- `agent_inbox_conformance`: 1 passed; two canonical Layer-07 scenarios discovered and executed by the real Inbox.

## Canonical runner audit

The Rust adapter dynamically discovers canonical Agent documents containing `agent_inbox`. It parses boundary values, calls real Inbox operations, and serializes observations. It does not implement FIFO, claim selection, clear semantics, queue independence, Session reset, tool visibility, wake state, or expected results.

Canonical Layer-07 inventory:

1. `agent-inbox-queue-mode-fifo` — PASS.
2. `agent-inbox-queue-independence-and-clearing` — PASS.

Discovered 2; executed 2; passed 2; deferred 0.

## Gates and regressions

- `cargo fmt --all -- --check`: PASS.
- `cargo clippy --workspace --all-targets --all-features -- -D warnings`: PASS.
- `cargo test --workspace --all-features`: PASS, including all Layer 01–06 suites and new Layer 07 suites.
- `RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps`: PASS.
- `cargo run -p xtask -- conformance verify`: PASS.
- shared schema validation: 183 passed.
- manifest validation: 75 rows / 75 unique IDs; every Layer-07 row has Rust evidence.

Sensitive lower-layer regressions remained green: Runtime event/service/scope/lifecycle, typed LLM vocabulary and streams, Session reset/derivation, XFORM canonical, ToolRegistry visibility/lifecycle/canonical, and Layer-06 execution/canonical.

## Traceability

AG-011 through AG-019/AG-016 now point to the Rust production module, language tests, and direct canonical runner where applicable. Only Rust evidence fields changed; shared rules and dispositions did not.

## Findings

- PI_PARITY_DEFECT: none.
- CONTRACT_ASSURANCE_DEFECT: none.
- PI_BEHAVIOR_UNCERTAIN: none.
- PARITY_CONSTRAINED_RISK: none blocking.
- PARITY_NEUTRAL_HARDENING: typed enums, synchronized deterministic queues, one coherent state lock, and a separate reset/status serialization gate.

## Final verdict

```text
Python Layer 07
    CERTIFIED

Rust Layer 07
    CERTIFIED

shared Layer-07 contract
    APPROVED / IMPLEMENTED

Layer 07 cross-language
    CERTIFIED / CLOSED

Layer 08
    NOT STARTED

Layer 08 eligible
    YES
```
