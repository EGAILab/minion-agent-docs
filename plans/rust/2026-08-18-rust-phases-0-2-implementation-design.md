# Minion Agent Rust — Phases 0–2 Implementation Design

**Date:** 2026-08-18  
**Status:** Approved for implementation planning  
**Implements:** Phases 0–2 of the language-neutral
`design/2026-08-18-minion-agent-design.md`

## 1. Purpose and scope

This document defines the first Rust implementation slice of Minion Agent:

- Phase 0: language-neutral conformance formats and snapshot workflow;
- Phase 1: the Cordis-semantic plugin runtime;
- Phase 2: the provider-neutral LLM vocabulary, session log, content-addressed
  request state, and telemetry seam.

The Rust implementation follows the frozen language-neutral design directly.
The Python implementation is a peer and the current canonical conformance
source, not the specification from which Rust behavior is inferred.

This effort also includes minimal Python corrections when a new canonical case
exposes behavior that contradicts an already-frozen semantic rule. Such changes
are contract alignment, not new Python features. Unrelated Python refactoring is
out of scope.

No executable Phase 3 semantics are introduced. Types or hooks strictly needed
by Phase 1–2 contracts are allowed; the agent loop, inbox semantics, tool
registry, tool execution pipeline, and built-in tools are not.

## 2. Repository shape

`minion-agent-rust` is a small Cargo workspace with one publishable library:

```text
minion-agent-rust/
  Cargo.toml
  rust-toolchain.toml
  crates/
    minion-agent/
      Cargo.toml
      src/
        runtime/
        llm/
        session/
        telemetry/
  conformance/
    SOURCE.json
    schema/
    runtime/
    session/
    agent/
  tests/
  xtask/
```

One library distribution preserves the frozen design's package boundary. Rust
modules provide subsystem isolation without turning every plugin or service
into an independently versioned crate.

Dependency direction is explicit:

- `runtime` depends on no higher subsystem;
- the provider-neutral LLM vocabulary does not depend on `session`, `agent`, or
  `tools`; runtime integration is allowed only where mounting requires it;
- `session` may depend on the LLM vocabulary;
- telemetry is observational and cannot influence semantic behavior;
- Phase 1–2 code does not depend on future `agent` or `tools` modules.

`xtask` is tooling only. It manages conformance snapshots, coverage, and
source-level layering checks. It neither implements runtime semantics nor
participates in normal library builds.

## 3. Runtime architecture

### 3.1 Typed API and erased storage

The public API uses strongly typed Rust services, events, and configurations.
`RuntimeCore` erases heterogeneous values internally behind thread-safe
containers. Contexts are lightweight views sharing an `Arc<RuntimeCore>` and
carrying fiber ownership plus optional scope identity.

Services have a normative string name. That string is the only semantic key.
Rust `TypeId` validates the associated service contract but never creates a
second key space. Rust newtypes compare normative names by string value;
`TypeId`, allocation identity, and pointer identity are never consulted for
semantic equality.

A normative service name is associated with one compatible Rust type contract
for the lifetime of its `RuntimeCore`. Unloading a provider removes its active
value and registration, but not the retained name/type association. Reusing the
same name later with an incompatible Rust type is an error.

The conformance runners are thin dynamic adapters over these typed APIs. They
may parse scenario data, convert values, create fixtures, and project observed
results. They must not decide service visibility, event propagation, stream
settlement, session derivation, or any other semantic result.

### 3.2 Fibers and effects

A fiber owns validated plugin configuration, lifecycle state, and an ordered
async disposer stack. The complete normative state graph, stable `Failed`
semantics, and loading-versus-unwind exclusion are defined in §3 of the
language-neutral design. Rust represents those states directly:

```text
Pending | Loading | Active | Failed | Unloading | Disposed
```

Effects created during loading become owned immediately. Disposal awaits each
disposer sequentially in strict reverse registration order. Every disposer is
attempted even when earlier cleanup fails. The final aggregate preserves
reverse execution order so diagnostics are deterministic. Double disposal is a
no-op, and creating an effect through a disposed owner fails.

Rust realizes the normative lifecycle as follows:

1. Deserialize and validate configuration.
2. Create the child context and `Fiber(Pending)`.
3. Record normative injected service names.
4. When every dependency is actively visible, enter `Loading`.
5. Invoke the plugin. Effects and registrations become owned immediately, but
   registrations remain externally invisible while the owner is not `Active`.
6. On successful initialization, re-check the lifecycle generation, disposal
   state, and dependency visibility before committing to `Active`.
7. On a represented `PluginInitError`, unwind created effects and settle at
   `Failed`; panics and impossible transition states remain invariant failures.
8. On dependency invalidation, unwind and settle at `Pending` without ever
   committing a stale activation.
9. On explicit disposal, invalidate in-flight work, unwind exactly once, and
   settle at `Disposed`.

Lifecycle transitions for one fiber are serialized. A generation/cancellation
signal can invalidate an awaited transition without holding a global lock.
Invalidation first cancels or drops the initialization future and closes the
effect-registration gate for that generation. Unwind begins only after the
attempt can no longer create an owned effect. Every effect-registration call
checks that its owning generation remains live. Reconciliation never retries a
`Failed` fiber; disposal followed by a new mount is the recovery path.
Runtime-global service, event, and scope locks are never held across plugin,
listener, or disposer awaits.

Leaving `Active` immediately makes registrations supplied by that fiber
invisible. Dependents are scheduled for reconciliation, after which effect
unwind removes the registrations. This preserves the frozen distinction
between registration, active visibility, and retained Rust type metadata.

### 3.3 Services and reactive dependency

Service registration is exclusive by normative name. There is no priority,
last-wins behavior, or fallback stack. A service resolves exactly when:

```text
registration exists
AND owner fiber is Active
AND the optional provider visibility predicate admits the request
```

Services themselves are process-wide in this phase; service shadowing and
isolation realms remain deferred. Scope eligibility applies to registrations
inside a resolved service, not to resolving the service. A scoped registration
is eligible exactly when it is untagged or its owning scope is the requesting
scope or one of that scope's ancestors.

Provider appearance or disappearance schedules dependent fiber reconciliation.
Reconciliation does not hold a global critical section across awaits and cannot
block unrelated fibers from progressing.

### 3.4 Events

Event contracts declare their normative name, dispatch mode, typed payload and
result, and a terminal continuation for waterfall events. The four modes retain
the frozen semantics: `emit`, `parallel`, `serial`, and `waterfall`.

Waterfall continuations accept either the current arguments or replacements and
may be called at most once. Delegating past the final listener produces the
declared terminal value. Decision and transformation behavior are patterns over
this one mechanism, not separate dispatch modes.

Event admission is snapshot-based:

```text
lock listener storage
  → compute the admitted ordered sequence
  → unlock
  → execute callbacks
```

Registration or disposal after the snapshot affects later dispatches only.

### 3.5 Scopes

Scopes form an immutable parent-linked tree. The registration context
determines both visibility and ownership. Registration visibility inherits
downward; event admission extends upward; untagged entries follow the frozen
global rules.

Generic scoped storage determines eligibility and ownership only. Each registry
defines its own composition semantics.

Disposing a scope settles descendant scopes before their parent and removes the
effects and registrations owned through each. Ancestors and siblings remain
unaffected. No semantic ordering is guaranteed between sibling scopes.

## 4. Phase 2 services

### 4.1 LLM vocabulary

Messages, content blocks, stop reasons, usage, requests, and stream chunks are
immutable `serde`-serializable Rust enums and structs with explicit
language-neutral tags.

Image content uses:

```text
ImageSource::Inline(Bytes)
ImageSource::Artifact(ArtifactHash)
```

Inline bytes stay binary in typed Rust values. JSON session and conformance
serialization encodes them as base64. Provider adapters independently choose
the wire encoding required by their API. Mutable paths or URLs must resolve to
owned, content-addressed artifacts before becoming model-visible.

### 4.2 Stream boundary

`LlmService::stream(request)` returns:

```rust
Result<AssistantStream, LlmStartError>
```

The outer result carries eager caller, request, model-selection, and
configuration failures. After an `AssistantStream` is returned, consumers see
`StreamChunk` values only: no `Result` items and no iteration errors.

`AssistantStream` wraps the raw adapter stream and enforces the public contract:

- represented provider, network, model, cancellation, and adapter faults become
  terminal error or aborted chunks;
- premature raw EOF synthesizes a terminal error carrying the accumulated
  partial assistant message, `stop_reason = error`, and an adapter-protocol
  diagnostic;
- the first terminal is exposed exactly once;
- after the first terminal the public stream is fused and exposes no later
  items;
- fusion performs no hidden draining or background polling solely to diagnose
  later adapter output;
- releasing the wrapper releases or cancels the raw stream through the
  adapter's normal lifecycle.

Expected adapter faults are represented as values. Panics remain programming or
invariant failures and are not part of the operational stream protocol.

The scripted mock adapter is a real adapter used by conformance and Tier-2
tests. It records requests and covers successful, tool-call, represented-error,
aborted, under-scripted, and malformed-stream cases.

### 4.3 Session events and append

Session event identity is an extensible normative string, represented by an
ergonomic Rust newtype. Core event names are associated constants, not a closed
enum. The log accepts any well-formed event name without prior registration,
matching §5's open-namespace rule.

`SessionService` supports lifecycle-owned registration of open event-kind
strings with additional validation and optional surface projection.
Registration attaches behavior; it does not create the string identity or
admit the event to model history by itself. Its internal extension table is not
a public architectural abstraction. Plugin-specific projections remain
implementation-specific unless separately standardized.

All append paths share one boundary:

```text
typed helper or conformance data
  → event-kind/data validation
  → atomic sequence allocation and append
  → committed event publication
```

Sequence order therefore equals committed append order. Rejected validation
leaves no log trace. The conformance adapter cannot bypass the boundary used by
typed callers.

### 4.4 Derivation and operations

The append-only log remains semantic truth. Core surface events project to
messages; log-only events do not. Registered plugin surface projections join
the projection in log order.

Derivation processes operations in log order:

- reset establishes the active surface boundary;
- each compaction identifies an explicitly superseded effective range,
  replacement summary, and retained-tail provenance;
- repeated, overlapping, nested, and fork-local replacements are deterministic;
- neither original entries nor retained copies are emitted twice;
- fork ancestry is referenced at a fixed boundary rather than copied.

No operation deletes history or changes session identity.

### 4.5 Artifacts and request reconstruction

The runtime-wide artifact store hashes bytes with SHA-256 and exposes no V1
deletion operation. Every artifact referenced by a committed event or request
header remains resolvable for the lifetime needed to reconstruct that session.

Request headers store sorted component-name-to-hash mappings. Dispatch assembly
and reconstruction use the same canonical component composition function.
Conformance asserts reconstructed model input, never storage layout.

### 4.6 Telemetry

Telemetry spans are typed while their attributes remain JSON-safe. Emission is:

```text
raw span
  → known-secret sanitization
  → fixed admitted sink snapshot
  → sinks
```

Sanitization always precedes extension points. Sink failures are contained,
reported diagnostically, and never alter, cancel, retry, or fail the observed
operation. Remaining sinks still run. The recording sink ships in Phase 2;
production sinks remain deferred.

Runtime, session, and agent semantic conformance never depends on telemetry
success. Telemetry sanitization and span-shape contracts are tested
independently.

## 5. Canonical conformance workflow

The canonical suite remains in `minion-agent-python/conformance/` with exactly
three families:

```text
conformance/
  runtime/
  session/
  agent/
```

No `llm/` family is introduced without deliberately revising the main design.
Stream-boundary scenarios live under `agent/`.

Rust vendors an exact snapshot. `conformance/SOURCE.json` records the source
repository revision, exact file set, and hashes. `xtask conformance verify`
fails on any mismatch. Normal Rust tests and builds never require the sibling
Python checkout.

Semantic changes follow §8's canonical workflow. `xtask` supports both branches:
an alignment case that exposes and minimally corrects a divergence, and a
coverage case that pins behavior existing implementations already satisfy. It
never requires manufacturing a failure before a scenario may be vendored.
After all capable existing implementations are green, `xtask` records and
syncs the exact snapshot; Rust then implements or verifies the same case, and
all applicable implementations remain green.

The Python event-kind and post-return stream alignment has already landed in
commit `6c47c0d`. Plan 2 verifies and preserves it. The canonical `agent/`
stream scenarios still need to be added.

Phase 2 introduces a partial `agent/` conformance runner for stream-contract
operations. It invokes the real `LlmService` and `AssistantStream`. Phase 3
extends the same adapter with agent-loop operations rather than replacing it.
A family runner may grow as phases expose new operations, but never implements
the semantics being tested.

## 6. Error handling

Public library APIs use concrete `thiserror` enums. `anyhow` is limited to
`xtask` and test/conformance harnesses.

- Expected caller, configuration, validation, provider, and operational
  failures return typed errors.
- Internal impossible states and violated framework invariants panic or emit an
  invariant diagnostic.
- No `anyhow::Error` leaks into public semantic contracts.
- Cleanup attempts every disposer and reports failures only after the ordered
  unwind completes.

## 7. Verification

### 7.1 Test layers

Rust verification has four layers:

1. Unit tests for typed APIs, validation, state transitions, serialization, and
   error mapping.
2. Deterministic Tokio concurrency tests using barriers and channels for stale
   loading, disposal during loading, append order, listener snapshots, and
   reconciliation. Wall-clock sleeps never establish correctness; an outer
   timeout may detect hangs.
3. Property tests for disposal idempotence/order, full service eligibility,
   scope ancestry, JSON round trips, committed sequence order, session
   derivation, and public stream shape.
4. Canonical scenarios invoking the real typed library through thin adapters.

The public stream property is `non-terminal*`, exactly one terminal, then EOF.
It does not require observing raw adapter output after fusion.

### 7.2 Coverage

Core semantic files require 100% line coverage:

```text
crates/minion-agent/src/runtime/**
crates/minion-agent/src/llm/**
crates/minion-agent/src/session/**
crates/minion-agent/src/telemetry/**
```

`xtask coverage verify` consumes `cargo llvm-cov` JSON and enforces the target
per file. Tests, `xtask`, generated code, and conformance glue are outside this
scope. An exclusion must identify a specific source location and reason; broad
file or directory exclusions are not accepted merely to preserve the number.
Defensive branches unreachable through safe APIs receive documented exclusions
rather than tests that corrupt private state.

### 7.3 Layering and documentation

`xtask layering verify` statically rejects forbidden source-level dependency
edges visible through imports and qualified module references. CI and review
prevent macro or re-export indirection from being used to bypass the rules. The
check does not claim compiler-complete dependency analysis.

Documentation builds with warnings denied:

```text
RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps
```

Requiring documentation for every public item is a separate lint decision and
is not enabled implicitly.

### 7.4 Required gates

```text
cargo fmt --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace --all-features
xtask coverage verify
xtask layering verify
RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps
xtask conformance verify
```

Every public API introduced in Phases 1–2 is exercised by canonical conformance
or Rust Tier-2 tests. No public API exists solely for anticipated Phase 3 use.

## 8. Dependency budget and toolchain

The initial allowed dependency budget is:

```text
runtime:
  tokio, tokio-util, async-trait, futures
  parking_lot, indexmap
  serde, serde_json, schemars, thiserror

phase 2:
  bytes, base64, sha2

test/tooling only:
  serde_yaml, jsonschema, proptest, anyhow
```

This is a budget, not a commitment. The implementation removes unused crates
and prefers the standard library or an already-required dependency when it
meets the contract cleanly. Test and tooling dependencies do not leak into the
publishable library's normal dependency graph.

Development targets Edition 2024 on a repository-pinned stable toolchain. The
initial pin matches the verified local stable toolchain (`1.97.1`). Before the
first published release, determine and declare the lowest Rust version actually
supported by the implementation and dependency graph, then verify it in CI.

## 9. Delivery plans and completion

Detailed executable plans are written under `plans/rust/`:

1. `2026-08-18-plan-1-conformance-and-runtime.md`
2. `2026-08-18-plan-2-llm-session-telemetry.md`

Plan 1 delivers repository/tooling setup, canonical runtime alignment, the
vendored snapshot workflow, runtime primitives, reactive dependency, and green
runtime conformance.

Plan 2 delivers the still-missing canonical agent-family stream cases, LLM
vocabulary and stream enforcement, the partial agent-family runner, session
semantics and artifacts, telemetry, public surfaces, property tests, and all
quality gates. Already-landed Python event-kind, stream, and session alignment
is verified rather than repeated; any remaining Python correction is limited to
what a new canonical case proves necessary.

The slice is complete when:

- Python and Rust pass the shared canonical scenarios applicable through Phase 2;
- all Rust verification gates pass;
- normal Rust builds and tests require no sibling repository;
- every public Phase 1–2 API is exercised by current semantics;
- the runtime substrate is complete enough for Plan 3 without implementing any
  executable Phase 3 behavior.
