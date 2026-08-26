# Layer 05 Rust implementation evidence — Tool model and registry

Date: 2026-08-26

## Scope and authority

This artifact records the Rust implementation of the already-approved Layer-05 shared contract.
It consumes:

- `minion-agent@89865c05933f4e6081da4ef776e34464a8c5a523` as the implementation baseline;
- `minion-agent-docs@76c57584f3fcaf1ecf32e40af8939e67703312fc` as the approved-contract baseline;
- pinned Pi `b7bb00b936dbe21b8e160b3e89efdec361846699`.

The implementation candidate is
`minion-agent@5d4420823b88b9e8c8596fff333f961f55a1582f`.

Layer-06 execution behavior, providers, provider validation, and built-in tools were not started.

## Implementation

The production seams are:

- `minion-agent-rust/crates/minion-agent/src/llm/vocabulary.rs`: object-valued parameter
  schemas and the closed constrained-sampling model;
- `minion-agent-rust/crates/minion-agent/src/tools/definition.rs`: callback-bearing agent tool
  definition, label, optional execution-mode override, and owned capability boundaries;
- `minion-agent-rust/crates/minion-agent/src/tools/registry.rs`: the Runtime-backed tool registry;
- `minion-agent-rust/crates/minion-agent/src/runtime/coordinator.rs` and `runtime/fiber.rs`:
  additive plumbing that exposes the single Runtime-owned registry through each coordinated
  context;
- `minion-agent-rust/crates/minion-agent/src/runtime/scoped_registry.rs`: the existing certified
  scoped registry remains the owner of visibility, ordering, scope liveness, withdrawal, and
  scope-disposal behavior.

No second scope tree, lifecycle graph, or winner cache was introduced. Unscoped registrations
are attached to the registering fiber's effect store. Scoped registrations are owned only by the
target scope and therefore survive the originating plugin's unmount.

The parameter boundary accepts every JSON object representation, including `{"type":"string"}`
and top-level combinators, while rejecting non-object containers. It does not require a schema
that describes an object instance. Constrained sampling preserves absent, explicit false,
JSON-schema, and grammar states; grammar keys are closed to `openai_lark` and `openai_regex`, and
an empty grammar map remains valid at this layer.

`prepare_arguments` and `execute` are owned `Send + Sync + 'static` capabilities. Layer 05 stores
and projects their metadata but does not invoke either capability.

## Canonical evidence

`minion-agent-rust/crates/minion-agent/tests/tool_registry_conformance.rs` dynamically discovers
the nine `tool-registry-*.yaml` Agent-family scenarios. It validates fixture references before
Runtime construction, then uses real Runtime, Scope, Fiber, Context, ToolRegistry, withdrawal,
unmount, and scope-disposal seams. The adapter does not walk ancestry, select shadow winners,
sort visible tools, simulate lifecycle removal, special-case disposed scopes, or execute tools.

```text
Layer-05 ToolRegistry
    discovered  9
    executed    9
    passed      9
    deferred    0

Runtime canonical family
    26 current scenarios

Session canonical family
    20 current scenarios

XFORM canonical subset
    14 current scenarios
```

The nine Layer-05 scenarios are:

1. `tool-registry-nearer-shadows-farther`
2. `tool-registry-plugin-disposal-withdraws`
3. `tool-registry-resolve-unknown-is-absent`
4. `tool-registry-same-scope-duplicate-name`
5. `tool-registry-schema-projection`
6. `tool-registry-scope-disposal-withdraws`
7. `tool-registry-scoped-registration-survives-plugin-unmount`
8. `tool-registry-scope-visibility`
9. `tool-registry-withdrawal-restores-farther`

Seven additional harness tests reject malformed parent, query, mount, unmount/withdrawal,
disposal, self-parent, and cyclic scope references before Runtime side effects.

## Rust tests

Focused evidence is in:

- `tests/tool_model.rs`: seven model, schema, constrained-sampling, grammar, execution-mode, and
  capability-boundary tests;
- `tests/tool_registry.rs`: four visibility, ordering, shadowing, duplicate, withdrawal, unknown,
  and disposed-requester tests;
- `tests/tool_registry_lifecycle.rs`: four real Runtime lifecycle tests;
- `tests/tool_registry_conformance.rs`: one nine-scenario real-seam test and seven fixture-integrity
  tests.

Every dummy callback used by registry/conformance evidence fails if invoked, proving that the
Layer-05 path does not cross into Layer 06.

## Fresh gates

Run from `minion-agent-rust` at the implementation candidate:

```text
cargo fmt --check
    PASS

cargo clippy --workspace --all-targets --all-features -- -D warnings
    PASS

cargo test --workspace --all-features
    169 passed
    0 failed

RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps
    PASS

cargo run -p xtask -- conformance verify
    PASS

uv run pytest --no-cov tests/conformance/test_schema_validation.py -q -rA
    165 passed

pi-parity-manifest.yaml parse and unique-ID audit
    60 / 60
```

## Traceability and findings

TOOL-008 through TOOL-016 retain their approved semantic rules and dispositions. Their Rust
planned-phase markers were replaced with production and test pointers only; this is an
evidence-only manifest update.

```text
PI_PARITY_DEFECT             none
CONTRACT_ASSURANCE_DEFECT    none
PI_BEHAVIOR_UNCERTAIN        none
PARITY_CONSTRAINED_RISK      none
PARITY_NEUTRAL_HARDENING     private typed object boundary and grouped Runtime resources
```

The hardening items do not change observable semantics.

## Verdict

```text
Rust Layer 05
    CERTIFIED

Layer 05 cross-language
    CERTIFIED / CLOSED

Rust current certified position
    Layer 05

Layer 06
    ELIGIBLE
    NOT STARTED
```
