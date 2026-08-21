# Minion Agent Rust — Plan 1: Conformance and Runtime Implementation Plan

> **Status note (2026-08-21): written against the superseded 2026-08-18 design.** Per the frozen
> `2026-08-20-minion-agent-design.md`'s realignment guidance (§9), Rust may retain completed Phase 1
> runtime unless revised `runtime/` conformance exposes a conflict. The conformance scenario format
> has since changed; cross-check against
> `minion-agent-docs/process/2026-08-21-phase-0-spec-conformance-realignment.md` before treating
> scenario-format details here as current.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the reproducible Rust workspace, vendored canonical-conformance workflow, and typed Cordis-semantic runtime whose lifecycle, services, events, scopes, and effects pass the shared runtime scenarios.

**Architecture:** One publishable `minion-agent` crate exposes typed APIs over an `Arc<RuntimeCore>` whose heterogeneous service and listener storage is erased internally. Fibers serialize their own transitions, gate effect creation by loading generation, and never hold runtime-global locks across awaits. A tooling-only `xtask` verifies the canonical snapshot, per-file coverage, and source-level layering.

**Tech Stack:** Rust 1.97.1, Edition 2024, Tokio, tokio-util, async-trait, futures, serde, serde_json, schemars, thiserror, parking_lot, indexmap; serde_yaml, jsonschema, proptest, and anyhow for tests/tooling only.

**Spec:** `minion-agent-docs/plans/rust/2026-08-18-rust-phases-0-2-implementation-design.md`, implementing `minion-agent-docs/design/2026-08-18-minion-agent-design.md` §3, §8, and §9.

## Global Constraints

- The normative design and canonical scenarios outrank both language implementations.
- The publishable surface is one crate, `minion-agent`; `xtask` is tooling only.
- Normal Rust builds and tests never require the sibling Python checkout.
- Service identity is the normative string name; `TypeId` validates one retained Rust contract per name and is never a semantic key.
- Normative names compare by string value.
- Runtime-global locks are never held across plugin, listener, or disposer awaits.
- Disposers execute sequentially in strict reverse registration order; all are attempted and failures retain that execution order.
- `Failed` is stable until disposal/remount; reconciliation never retries it.
- An invalidated loading generation closes effect registration before unwind and never emits a transient `Active`.
- Scopes determine registration eligibility and ownership, not registry-specific composition.
- No executable agent-loop, inbox, tool-registry, or tool-execution semantics are introduced.
- Every semantic behavior shared with Python belongs in canonical conformance; Rust-only stress and implementation-mechanism checks remain Tier 2.
- Core `runtime/**` files require 100% line coverage, with only narrow source-location exclusions carrying a written reason.
- Use conventional commits and commit after every task.

---

## File Structure

```text
minion-agent-rust/
  .gitignore
  Cargo.toml
  Cargo.lock
  rust-toolchain.toml
  conformance/
    SOURCE.json
    schema/*.json
    runtime/*.yaml
    session/*.yaml
    agent/*.yaml
  crates/minion-agent/
    Cargo.toml
    src/lib.rs
    src/runtime/
      mod.rs
      error.rs
      identity.rs
      disposable.rs
      scope.rs
      scoped_registry.rs
      event.rs
      service.rs
      plugin.rs
      fiber.rs
      context.rs
      registry.rs
    tests/
      runtime_disposable.rs
      runtime_scope.rs
      runtime_event.rs
      runtime_service.rs
      runtime_fiber.rs
      runtime_reactive.rs
      runtime_properties.rs
      runtime_conformance.rs
      support/mod.rs
      support/runtime_scenario.rs
  xtask/
    Cargo.toml
    src/main.rs
    src/conformance.rs
    src/coverage.rs
    src/layering.rs
    tests/conformance_snapshot.rs
    tests/layering.rs
```

The `runtime` files each own one concept. `fiber.rs` owns state and generation;
`registry.rs` owns reconciliation; `context.rs` is the façade joining services,
events, scopes, and effects. Conformance support performs parsing and result
projection only.

---

### Task 1: Scaffold the pinned Cargo workspace

**Files:**
- Create: `minion-agent-rust/.gitignore`
- Create: `minion-agent-rust/Cargo.toml`
- Create: `minion-agent-rust/rust-toolchain.toml`
- Create: `minion-agent-rust/crates/minion-agent/Cargo.toml`
- Create: `minion-agent-rust/crates/minion-agent/src/lib.rs`
- Create: `minion-agent-rust/xtask/Cargo.toml`
- Create: `minion-agent-rust/xtask/src/main.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/scaffold.rs`

**Interfaces:**
- Consumes: Rust stable 1.97.1 with `rustfmt`, `clippy`, and `llvm-tools-preview`.
- Produces: workspace members `crates/minion-agent` and `xtask`; library constant `VERSION: &str`; `cargo run -p xtask -- help`.

- [ ] **Step 1: Write the failing scaffold test**

```rust
use minion_agent::VERSION;

#[test]
fn package_exposes_a_non_empty_version() {
    assert!(!VERSION.is_empty());
}
```

- [ ] **Step 2: Run the test to verify the crate is absent**

Run: `cargo test -p minion-agent --test scaffold`

Expected: failure because the workspace and package do not exist.

- [ ] **Step 3: Create the workspace and pinned toolchain**

Use this workspace manifest:

```toml
[workspace]
members = ["crates/minion-agent", "xtask"]
resolver = "3"

[workspace.package]
edition = "2024"
license = "MIT"
rust-version = "1.97"
version = "0.1.0"

[workspace.dependencies]
anyhow = "1"
async-trait = "0.1"
futures = "0.3"
indexmap = "2"
jsonschema = "0.33"
parking_lot = "0.12"
proptest = "1"
schemars = "1"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
serde_yaml = "0.9"
sha2 = "0.10"
thiserror = "2"
tokio = { version = "1", features = ["macros", "rt-multi-thread", "sync"] }
tokio-util = "0.7"
```

Use this `rust-toolchain.toml`:

```toml
[toolchain]
channel = "1.97.1"
components = ["clippy", "llvm-tools-preview", "rustfmt"]
profile = "minimal"
```

The library manifest inherits workspace metadata and initially depends only on
`serde` and `thiserror`; add other dependencies in the task that uses them.
The `xtask` binary accepts exactly `help`, `conformance`, `coverage`, and
`layering`, prints usage for `help`, and returns a nonzero exit for unknown
commands.

- [ ] **Step 4: Implement the minimal library surface**

```rust
#![forbid(unsafe_code)]

pub const VERSION: &str = env!("CARGO_PKG_VERSION");
```

- [ ] **Step 5: Verify the workspace**

Run:

```text
cargo fmt --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace --all-features
cargo run -p xtask -- help
```

Expected: every command succeeds and `Cargo.lock` is created.

- [ ] **Step 6: Commit**

```text
git add .gitignore Cargo.toml Cargo.lock rust-toolchain.toml crates xtask
git commit -m "chore: scaffold Rust workspace"
```

---

### Task 2: Build conformance snapshot tooling without vendoring yet

**Files:**
- Create: `minion-agent-rust/xtask/src/conformance.rs`
- Modify: `minion-agent-rust/xtask/src/main.rs`
- Create: `minion-agent-rust/xtask/tests/conformance_snapshot.rs`

**Interfaces:**
- Consumes: a source checkout path supplied explicitly with `--source`.
- Produces: `SnapshotManifest { source_repository, source_commit, files }`; commands `conformance sync --source PATH` and `conformance verify`.

- [ ] **Step 1: Write fixture-based failing tests**

Create a temporary fixture under `std::env::temp_dir()` containing
`conformance/schema/runtime-scenario.schema.json` and
`conformance/runtime/example.yaml`. Assert that:

```rust
let manifest = build_manifest(&source, "abc123")?;
assert_eq!(manifest.source_commit, "abc123");
assert_eq!(manifest.files.len(), 2);
assert!(manifest.files[0].path < manifest.files[1].path);
assert!(manifest.files.iter().all(|f| f.sha256.len() == 64));
```

Add tests that `verify_snapshot` reports a changed byte, a missing file, and an
unrecorded JSON/YAML file. Cleanup the fixture with `remove_dir_all` after each
test.

- [ ] **Step 2: Run the tests to verify the module is absent**

Run: `cargo test -p xtask --test conformance_snapshot`

Expected: compile failure because `build_manifest` and `verify_snapshot` do not
exist.

- [ ] **Step 3: Implement deterministic manifest generation**

Define:

```rust
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SnapshotFile {
    pub path: String,
    pub sha256: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SnapshotManifest {
    pub source_repository: String,
    pub source_commit: String,
    pub files: Vec<SnapshotFile>,
}

pub fn build_manifest(source: &Path, commit: &str) -> anyhow::Result<SnapshotManifest>;
pub fn sync_snapshot(source: &Path, destination: &Path) -> anyhow::Result<()>;
pub fn verify_snapshot(destination: &Path) -> anyhow::Result<()>;
```

Walk directories with `std::fs::read_dir`, include only `.json` and `.yaml`,
sort slash-normalized relative paths, hash raw bytes with SHA-256, and write
pretty JSON ending in one newline. Obtain the source commit with
`git -C PATH rev-parse HEAD`. Reject a dirty source checkout so a manifest can
always be reproduced from its recorded commit.

`sync` replaces only files listed in the previous/new manifest; it must not
delete unrelated files. `verify` hashes the local snapshot and reports every
mismatch in one deterministic error.

- [ ] **Step 4: Wire CLI parsing with `std::env::args_os`**

Accept only:

```text
xtask conformance sync --source <path>
xtask conformance verify
```

Resolve the destination as `<workspace>/conformance`; do not persist the local
source path in `SOURCE.json`. Store `source_repository` as
`minion-agent-python/conformance`.

- [ ] **Step 5: Run tests and a dry fixture sync**

Run: `cargo test -p xtask --test conformance_snapshot`

Expected: all snapshot tests pass. Do not sync the real Python suite yet; Task
7 owns the canonical lifecycle gate.

- [ ] **Step 6: Commit**

```text
git add xtask Cargo.toml Cargo.lock
git commit -m "feat: add conformance snapshot tooling"
```

---

### Task 3: Add normative identities, runtime errors, and reversible effects

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/runtime/mod.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/runtime/identity.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/runtime/error.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/runtime/disposable.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/lib.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/runtime_disposable.rs`

**Interfaces:**
- Consumes: `futures::future::BoxFuture`, `parking_lot::Mutex`, `thiserror`.
- Produces: `ServiceName`, `EventName`, `DisposeError`, `DisposeErrors`, `EffectStore`, and `EffectHandle`.

- [ ] **Step 1: Write failing identity and disposal tests**

Cover value equality and strict reverse, exactly-once disposal:

```rust
#[tokio::test]
async fn disposers_run_sequentially_in_reverse_order() {
    let seen = Arc::new(Mutex::new(Vec::new()));
    let effects = EffectStore::new();
    for label in ["first", "second", "third"] {
        let seen = Arc::clone(&seen);
        effects.push(label, move || Box::pin(async move {
            seen.lock().push(label);
            Ok(())
        })).unwrap();
    }
    effects.close_and_dispose().await.unwrap();
    assert_eq!(&*seen.lock(), &["third", "second", "first"]);
}
```

Also assert: a second disposal is a no-op; failures are returned in reverse
execution order after remaining entries run; pushing after `close()` returns
`RuntimeError::InactiveOwner`; and two independently allocated
`ServiceName::new("tools")` values compare equal.

- [ ] **Step 2: Run tests to verify failure**

Run: `cargo test -p minion-agent --test runtime_disposable`

Expected: compile failure because the runtime types do not exist.

- [ ] **Step 3: Implement identities and concrete errors**

Use `Arc<str>` newtypes with checked non-empty lowercase names and value-based
`Eq`, `Ord`, and `Hash`. Define concrete errors:

```rust
#[derive(Debug, Error)]
pub enum RuntimeError {
    #[error("invalid normative name {0:?}")]
    InvalidName(String),
    #[error("cannot create effect on inactive owner {owner}")]
    InactiveOwner { owner: String },
    #[error("service {name} is already provided by {holder}")]
    ServiceConflict { name: ServiceName, holder: String },
    #[error("service {name} has Rust contract {expected}, not {actual}")]
    ServiceTypeMismatch { name: ServiceName, expected: &'static str, actual: &'static str },
}
```

`DisposeError` contains `label` and `message`; `DisposeErrors(Vec<DisposeError>)`
preserves execution order.

- [ ] **Step 4: Implement the effect-registration gate**

`EffectStore` contains a short-held `parking_lot::Mutex` around
`{ accepting: bool, entries: Vec<Arc<EffectSlot>> }`. `close()` atomically sets
`accepting = false` and clones the reverse entry order. Each `EffectSlot`
contains a mutex-protected `Option<Disposer>` so an `EffectHandle` and bulk
unwind race safely and only one takes the closure. No mutex guard survives an
await.

- [ ] **Step 5: Run focused and formatting checks**

Run:

```text
cargo fmt --check
cargo clippy -p minion-agent --all-targets -- -D warnings
cargo test -p minion-agent --test runtime_disposable
```

Expected: all pass.

- [ ] **Step 6: Commit**

```text
git add crates/minion-agent Cargo.toml Cargo.lock
git commit -m "feat: add runtime identities and reversible effects"
```

---

### Task 4: Implement scope identity and eligibility-only scoped storage

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/runtime/scope.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/runtime/scoped_registry.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/runtime/mod.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/runtime_scope.rs`

**Interfaces:**
- Consumes: `EffectStore` and `RuntimeError` from Task 3.
- Produces: `ScopeId`, `ScopeTree`, `ScopeHandle`, `ScopedRegistry<T>`, and `RegistrationHandle`.

- [ ] **Step 1: Write failing scope tests**

Construct `root → definition → instance → turn` plus a sibling instance. Assert:

```rust
assert!(tree.is_ancestor(definition.id(), turn.id()));
assert!(!tree.is_ancestor(turn.id(), definition.id()));
assert!(!tree.is_ancestor(sibling.id(), turn.id()));
assert_eq!(registry.visible_from(turn.id()), vec!["turn", "instance", "definition", "global"]);
```

Also assert ancestor queries never see descendant entries, sibling entries are
invisible, and disposing `instance` settles `turn` before `instance` while
leaving `definition` and the sibling intact. Do not assert ordering between two
sibling descendants.

- [ ] **Step 2: Run tests to verify failure**

Run: `cargo test -p minion-agent --test runtime_scope`

Expected: compile failure for missing scope types.

- [ ] **Step 3: Implement immutable parent-linked scopes**

Allocate monotonic `u64` IDs inside `ScopeTree`; store parent and child IDs in
short-held locks. `ScopeHandle::dispose()` marks the subtree disposed, takes
descendants grouped deepest-first, closes their effect stores, and awaits each
scope's reverse unwind outside the tree lock. Sort only by depth; sibling order
must not appear in public traces.

- [ ] **Step 4: Implement eligibility-only storage**

`ScopedRegistry<T>` stores registration order, optional owner scope, and
`Arc<T>`. `visible_from(request_scope)` returns every eligible entry nearest
scope first and preserves registration order within one scope. It does not
deduplicate keys or define shadowing; later registries compose returned entries.
Registration installs removal into the owning scope's `EffectStore`.

- [ ] **Step 5: Run focused checks and commit**

Run: `cargo test -p minion-agent --test runtime_scope`

```text
git add crates/minion-agent
git commit -m "feat: add nested scope ownership and eligibility"
```

---

### Task 5: Implement typed event declarations and snapshot dispatch

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/runtime/event.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/runtime/mod.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/runtime_event.rs`

**Interfaces:**
- Consumes: `EventName`, `ScopeTree`, and `EffectStore`.
- Produces: `DispatchMode`, `EventSpec<P, R>`, `EventBus`, and single-use `Next<P, R>`.

- [ ] **Step 1: Write failing dispatch tests**

Test declaration-mode mismatch, registration order, parallel error aggregation,
serial last-result behavior, waterfall delegation/replacement/short-circuit,
terminal values, and second `next` rejection. Add a deterministic snapshot test:
listener A waits on a channel, listener B is disposed after dispatch snapshots,
then A is released; both A and B must run in the current dispatch and only A in
the next.

- [ ] **Step 2: Run tests to verify failure**

Run: `cargo test -p minion-agent --test runtime_event`

- [ ] **Step 3: Implement typed declarations over erased listener storage**

Define:

```rust
pub struct EventSpec<P, R> {
    name: EventName,
    mode: DispatchMode,
    terminal: Arc<dyn Fn(&P) -> R + Send + Sync>,
}
```

Internally store payload/result `TypeId`s and callbacks erased behind `Any`.
Reject redeclaration with a different mode or Rust contract. Snapshot admitted
callbacks under lock, release it, then execute. Scope admission accepts
untagged listeners and listeners whose tag is an ancestor of the dispatch tag.

- [ ] **Step 4: Implement single-use waterfall continuation**

Use an `AtomicBool` in `Next`; `call(replacement: Option<P>)` returns
`WaterfallError::NextAlreadyCalled` on the second call. Build the chain from the
snapshot so registrations cannot mutate it mid-dispatch. The empty chain and
delegation past the last listener invoke `terminal`.

- [ ] **Step 5: Run focused checks and commit**

Run: `cargo test -p minion-agent --test runtime_event`

```text
git add crates/minion-agent
git commit -m "feat: add typed snapshot event dispatch"
```

---

### Task 6: Implement name-keyed services with retained Rust contracts

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/runtime/service.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/runtime/mod.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/runtime_service.rs`

**Interfaces:**
- Consumes: `ServiceName`, future-compatible owner state queries, and
  `EffectStore`.
- Produces: `Service` trait, `ServiceRegistry`, `ServiceRegistration`, and typed
  `provide::<S>` / `require::<S>` operations.

- [ ] **Step 1: Write failing service tests**

Define two concrete test services both naming `tools`. Assert exclusive active
registration, invisible `Loading`/`Unloading` owners, optional check-predicate
gating, removal without fallback, and retained contract mismatch after unload:

```rust
let registration = registry.provide::<ToolsA>(owner.clone(), Arc::new(ToolsA), None)?;
registration.dispose().await?;
let error = registry.provide::<ToolsB>(other, Arc::new(ToolsB), None).unwrap_err();
assert!(matches!(error, RuntimeError::ServiceTypeMismatch { .. }));
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cargo test -p minion-agent --test runtime_service`

- [ ] **Step 3: Implement service contracts and erased values**

```rust
pub trait Service: Send + Sync + 'static {
    const NAME: &'static str;
}
```

Key active registrations and retained metadata only by `ServiceName`. Store
`Arc<S>` as `Arc<dyn Any + Send + Sync>` and downcast on typed lookup. Retain
`TypeId::of::<S>()` and `type_name::<S>()` after registration removal. A
registration occupies the exclusive slot even while its owner is `Loading`,
but resolution requires `Active` plus the optional predicate.

- [ ] **Step 4: Run focused checks and commit**

Run: `cargo test -p minion-agent --test runtime_service`

```text
git add crates/minion-agent
git commit -m "feat: add typed name-keyed service registry"
```

---

### Task 7: Vendor the lifecycle-aligned canonical suite

**Files:**
- Create by sync: `minion-agent-rust/conformance/SOURCE.json`
- Create by sync: `minion-agent-rust/conformance/schema/*.json`
- Create by sync: `minion-agent-rust/conformance/runtime/*.yaml`
- Create by sync: `minion-agent-rust/conformance/session/*.yaml`
- Create by sync: `minion-agent-rust/conformance/agent/*.yaml`
- Test: `minion-agent-rust/xtask/tests/conformance_snapshot.rs`

**Interfaces:**
- Consumes: the lifecycle-aligned Python baseline at commit `88aa220` or a
  clean descendant that still passes both canonical runtime cases.
- Produces: the exact Phase-1 canonical snapshot consumed by Tasks 8–12.

- [ ] **Step 1: Verify the Python source is clean and committed**

Run in `minion-agent-python`:

```text
git status --short
git log -1 --oneline
uv run pytest
uv run ruff check .
uv run mypy
```

Expected: empty status, commit `88aa220` or a reviewed descendant, and all
gates green. Commit `88aa220` was verified on 2026-08-18 with `320 passed, 1
skipped` and 100% scoped line coverage. If the status is dirty or any gate
fails when this plan is executed, stop Plan 1 here; independent Tasks 1–6 may
remain complete, but the runtime lifecycle implementation must not proceed
against an uncommitted oracle.

- [ ] **Step 2: Verify both canonical files and their exact semantic traces**

Require:

```text
conformance/runtime/failed-remains-failed.yaml
conformance/runtime/dependency-loss-during-loading-never-activates.yaml
```

The first must end `failed → disposed` without `pending` or a second `loading`.
The second must contain `pending → loading → pending`, no `active` or
`unloading`, and reverse exactly-once disposal of loading-created effects.

- [ ] **Step 3: Sync from the clean source checkout**

Run in `minion-agent-rust`:

```text
cargo run -p xtask -- conformance sync --source ..\minion-agent-python
cargo run -p xtask -- conformance verify
```

Expected: `SOURCE.json` records the exact Python commit and every JSON/YAML
hash; verify passes without accessing Python.

- [ ] **Step 4: Validate every vendored scenario against its vendored schema**

Add a test that maps `runtime`, `session`, and `agent` directories to their
schema, parses YAML, converts it to JSON, and calls `jsonschema::validator_for`.
Unknown keys must fail because schemas use `additionalProperties: false`.

- [ ] **Step 5: Commit**

```text
git add conformance xtask Cargo.toml Cargo.lock
git commit -m "test: vendor canonical conformance snapshot"
```

---

### Task 8: Implement plugin specs and the complete fiber lifecycle

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/runtime/plugin.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/runtime/fiber.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/runtime/mod.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/runtime_fiber.rs`

**Interfaces:**
- Consumes: `EffectStore`, `ServiceName`, `CancellationToken`, serde config.
- Produces: `PluginSpec<C>`, erased `DynPluginSpec`, `PluginInitError`,
  `FiberState`, `FiberHandle`, and transition trace subscription.

- [ ] **Step 1: Write the state-table tests first**

Cover every transition in the shared lifecycle table. Explicitly assert:

```rust
assert_eq!(trace, [Pending, Loading, Failed]);
dependencies.toggle_off_then_on();
registry.reconcile().await?;
assert_eq!(fiber.state(), Failed);
assert_eq!(initialization_count.load(Ordering::SeqCst), 1);
fiber.dispose().await?;
assert_eq!(fiber.state(), Disposed);
```

Add barrier/channel tests for dependency invalidation and disposal during
`Loading`. Release the initialization only after invalidation. Expected trace
is `Pending, Loading, Pending` or `Pending, Loading, Disposed`; neither may
contain `Active` or `Unloading`.

- [ ] **Step 2: Write the effect-race test**

Pause initialization immediately before a second `ctx.effect`. Invalidate the
generation and allow unwind to begin, then release the attempted registration.
Assert it returns `InactiveOwner`, never enters the owned stack, and the first
effect disposes once.

- [ ] **Step 3: Run tests to verify failure**

Run: `cargo test -p minion-agent --test runtime_fiber`

- [ ] **Step 4: Implement typed plugin specs without procedural macros**

`PluginSpec<C>` stores name, injected names, a `schemars` schema function, and
an async initializer returning `Result<(), PluginInitError>`. Erase config and
initializer only when mounting. Config deserialization errors occur before a
fiber is created.

- [ ] **Step 5: Implement serialized generation-aware transitions**

Use a per-fiber Tokio mutex for transition ownership plus a short-held state
lock containing `{ state, generation, effects, cancellation }`. Run the pinned
initializer inside `tokio::select!` against its generation's cancellation
token. The invalidation signal path may update the short-held state while the
loading transition owns the transition mutex; it does not begin unwind itself.
Invalidation:

1. increments generation;
2. closes that generation's `EffectStore`;
3. cancels the token;
4. causes the loading transition's `select!` branch to drop the initializer;
5. confirms the closed store cannot accept another effect;
6. unwinds outside locks;
7. commits `Pending` or `Disposed` without transient `Active`.

Explicit disposal first signals invalidation, then waits for serialized
transition ownership and the same unwind result. This makes cancellation plus
the effect gate the correctness boundary; dropping a future alone is never
treated as cleanup.

Successful initialization rechecks generation, not-disposed state, and a
dependency validator immediately before the `Active` transition. Only a
returned `PluginInitError` produces `Failed`; panics are not caught as ordinary
plugin failure.

- [ ] **Step 6: Run focused tests and commit**

Run: `cargo test -p minion-agent --test runtime_fiber`

```text
git add crates/minion-agent
git commit -m "feat: implement transactional fiber lifecycle"
```

---

### Task 9: Implement Context and reactive plugin reconciliation

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/runtime/context.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/runtime/registry.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/runtime/mod.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/runtime_reactive.rs`

**Interfaces:**
- Consumes: Tasks 3–8.
- Produces: `Context::root`, `extend`, `scope`, `effect`, `provide`, `require`,
  `on`, `mount`; `PluginRegistry::reconcile` and `unmount`.

- [ ] **Step 1: Write failing cascade and isolation tests**

Assert a dependent remains pending until its service appears, unloads when it
disappears, reloads after return, and a failed fiber never reloads. Add two
independent blocked initializers and show releasing one completes it without
waiting for the other. No sleep may establish ordering.

- [ ] **Step 2: Run tests to verify failure**

Run: `cargo test -p minion-agent --test runtime_reactive`

- [ ] **Step 3: Implement the shared core and façade**

`RuntimeCore` owns service registry, event bus, scope tree, plugin registry, and
monotonic IDs. `Context` carries `Arc<RuntimeCore>`, optional fiber generation,
and optional scope. `effect`, `provide`, and `on` register through the nearest
scope owner when scoped, otherwise through the fiber generation.

- [ ] **Step 4: Implement reconciliation without global awaited locks**

Snapshot mounted fibers and visible service names, signal invalid active or
loading fibers first, then schedule eligible pending fibers. Await each fiber
transition without holding registry locks and loop until a complete pass makes
no state change. Dependency cycles simply remain `Pending`; termination follows
from the finite set of actual state changes, not a wall-clock delay or arbitrary
pass limit. Reconciliation never joins a `Loading` transition it did not start;
it only invalidates that generation, allowing an initializer that caused its
own dependency loss to return without a re-entrant wait. Recheck dependencies
through the fiber commit validator.

- [ ] **Step 5: Run focused tests and commit**

Run: `cargo test -p minion-agent --test runtime_reactive`

```text
git add crates/minion-agent
git commit -m "feat: add reactive runtime context"
```

---

### Task 10: Parse canonical runtime scenarios into fixture-only types

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/tests/support/mod.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/support/runtime_scenario.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/runtime_conformance.rs`

**Interfaces:**
- Consumes: vendored runtime schema/YAML.
- Produces: serde scenario structs and `load_runtime_scenarios()`, without any
  lifecycle semantics.

- [ ] **Step 1: Write schema/parse tests**

Load every `conformance/runtime/*.yaml`, deserialize with `deny_unknown_fields`,
and assert the file stem appears in the test case name. Add a malformed fixture
with an unknown key and assert deserialization fails.

- [ ] **Step 2: Run to verify failure**

Run: `cargo test -p minion-agent --test runtime_conformance parse_`

- [ ] **Step 3: Define exact scenario DTOs**

Mirror the vendored schema with `RuntimeScenario`, `PluginFixture`, untagged
`Step`, `DispatchFixture`, `TraceEntry`, and expected error/result fields.
Represent `during_load` as `Vec<Step>`. DTOs may convert strings and values but
must not compute visibility, lifecycle, or event results.

- [ ] **Step 4: Run parse tests and commit**

Run: `cargo test -p minion-agent --test runtime_conformance parse_`

```text
git add crates/minion-agent/tests
git commit -m "test: parse canonical runtime scenarios"
```

---

### Task 11: Execute every canonical runtime scenario through the real runtime

**Files:**
- Modify: `minion-agent-rust/crates/minion-agent/tests/support/runtime_scenario.rs`
- Modify: `minion-agent-rust/crates/minion-agent/tests/runtime_conformance.rs`

**Interfaces:**
- Consumes: real `Context`, plugin, event, scope, and lifecycle APIs.
- Produces: `run_runtime_scenario(&RuntimeScenario) -> RunOutcome` with exact
  trace, result, and normalized error.

- [ ] **Step 1: Add one failing test per vendored scenario**

Generate a libtest case loop or one test that reports the scenario filename on
failure. Compare trace arrays exactly; extra and missing entries fail.

- [ ] **Step 2: Implement fixture construction only**

Build real `PluginSpec`s whose bodies create the declared effects, services,
listeners, and `during_load` operations. Record callbacks from real fiber state
and effect notifications. The runner may map YAML strings to API calls but may
not decide a transition or synthesize an effect-disposal trace.

- [ ] **Step 3: Implement scenario steps through public APIs**

Map `mount`, `unmount`, `dispose_scope`, and `dispatch` to the real context.
Run `during_load` through the same step function. Normalize only error type and
message fields declared by the schema.

- [ ] **Step 4: Run conformance**

Run: `cargo test -p minion-agent --test runtime_conformance -- --nocapture`

Expected: all canonical runtime cases, including the two lifecycle additions,
pass with exact traces.

- [ ] **Step 5: Commit**

```text
git add crates/minion-agent/tests
git commit -m "test: pass canonical runtime conformance"
```

---

### Task 12: Add runtime properties and deterministic concurrency coverage

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/tests/runtime_properties.rs`
- Modify as coverage requires: `minion-agent-rust/crates/minion-agent/src/runtime/*.rs`

**Interfaces:**
- Consumes: complete public runtime.
- Produces: property coverage for effect, service, scope, and lifecycle invariants.

- [ ] **Step 1: Add proptest properties**

Generate effect label lists and assert reverse exactly-once disposal. Generate
scope trees and assert eligibility iff untagged or owner is an ancestor.
Generate owner states/check booleans and assert service resolution iff
registered, `Active`, and predicate true.

- [ ] **Step 2: Add deterministic interleaving matrices**

Use barriers/channels to cover invalidation before initializer poll, during an
await, after initializer return but before commit, and simultaneous explicit
dispose. Assert one terminal state and no lock is held across the controlled
await.

- [ ] **Step 3: Run the complete runtime suite**

Run: `cargo test -p minion-agent --all-features`

Expected: all unit, property, concurrency, and conformance tests pass.

- [ ] **Step 4: Commit**

```text
git add crates/minion-agent
git commit -m "test: add runtime invariant properties"
```

---

### Task 13: Enforce source-level layering and per-file coverage

**Files:**
- Create: `minion-agent-rust/xtask/src/layering.rs`
- Create: `minion-agent-rust/xtask/src/coverage.rs`
- Modify: `minion-agent-rust/xtask/src/main.rs`
- Create: `minion-agent-rust/xtask/tests/layering.rs`

**Interfaces:**
- Consumes: Rust source tree and `cargo llvm-cov --json` output.
- Produces: `layering verify` and `coverage verify` gates.

- [ ] **Step 1: Write failing layering fixtures**

Fixture source under `runtime/` containing `use crate::llm::Request;` must fail.
Fixture LLM source containing `crate::session::SessionLog` must fail. Comments
and string literals containing those spellings must not fail.

- [ ] **Step 2: Implement the bounded source-level checker**

Strip comments and string/character literals with a small lexical state
machine, then scan imports and qualified paths. Enforce:

```text
runtime -> no llm/session/agent/tools
llm -> no session/agent/tools
session -> no agent/tools
telemetry -> no agent/tools
```

Report file, line, and forbidden edge. Document that macros/re-exports remain a
review constraint rather than claiming compiler completeness.

- [ ] **Step 3: Write coverage parser tests**

Feed a small LLVM coverage JSON fixture with one 99% runtime file and assert
failure names that file; 100% files pass. Reject broad ignore patterns.

- [ ] **Step 4: Implement scoped coverage verification**

Spawn `cargo llvm-cov --package minion-agent --all-features --json`, parse file
summaries, normalize paths, and require 100% lines for
`src/runtime/**/*.rs`. Allow only explicit source-location exclusions recorded
as `// coverage: exclude <reason>` on the excluded line.

- [ ] **Step 5: Run both gates and commit**

Run:

```text
cargo run -p xtask -- layering verify
cargo run -p xtask -- coverage verify
```

```text
git add xtask crates/minion-agent Cargo.toml Cargo.lock
git commit -m "test: enforce runtime layering and coverage"
```

---

### Task 14: Freeze the Plan 1 public surface and run all gates

**Files:**
- Modify: `minion-agent-rust/crates/minion-agent/src/runtime/mod.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/lib.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/runtime_public.rs`
- Create: `minion-agent-rust/README.md`

**Interfaces:**
- Consumes: all Plan 1 components.
- Produces: documented public runtime surface used by Plan 2.

- [ ] **Step 1: Write the public-surface test**

Import and minimally exercise every exported Plan 1 type from an integration
test. Assert no exported identifier contains `cordis`, and compile a plugin
mount using only public APIs.

- [ ] **Step 2: Restrict exports to exercised APIs**

Re-export only the types consumed by canonical scenarios, tests, or Plan 2's
documented mounting needs. Keep erased storage and transition internals private.
Add module-level rustdoc explaining Cordis design lineage without using Cordis
in public identifiers.

- [ ] **Step 3: Document setup and the snapshot gate**

README commands must use the pinned toolchain and explain that ordinary builds
are standalone while `conformance sync` requires an explicit clean source
checkout.

- [ ] **Step 4: Run final Plan 1 verification**

Run:

```text
cargo fmt --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace --all-features
cargo run -p xtask -- coverage verify
cargo run -p xtask -- layering verify
cargo run -p xtask -- conformance verify
$env:RUSTDOCFLAGS='-D warnings'; cargo doc --workspace --no-deps
```

Expected: every command succeeds; the vendored manifest names the clean Python
commit containing both lifecycle scenarios.

- [ ] **Step 5: Commit**

```text
git add crates/minion-agent README.md
git commit -m "docs: freeze Rust runtime public surface"
```

---

## Definition of Done

- [ ] Python is green at a committed revision containing
  `failed-remains-failed` and
  `dependency-loss-during-loading-never-activates`.
- [ ] Rust vendors and verifies that exact canonical snapshot.
- [ ] Every canonical runtime scenario passes through the real typed runtime.
- [ ] The stale-load trace never contains transient `Active` or `Unloading`.
- [ ] Once invalidation closes an effect generation, no effect from it can
  become owned while unwind runs.
- [ ] `Failed` never returns to `Pending` except through disposal and a newly
  mounted fiber identity.
- [ ] Services are keyed semantically by name and retain one Rust type contract
  across unload/reload.
- [ ] Effects unwind sequentially, reverse-order, exactly once, with ordered
  aggregate errors.
- [ ] Scope and event snapshot semantics pass canonical and property tests.
- [ ] Formatting, Clippy, tests, scoped coverage, layering, snapshot, and
  rustdoc gates are green.
- [ ] No executable Phase 2 or Phase 3 semantics are present.

## Plan 2 Entry Contract

Plan 2 may rely on the public `Context`, plugin/fiber lifecycle, services,
events, scopes, scoped registry, effect ownership, conformance snapshot tool,
and verification gates delivered here. It must not reach into erased runtime
storage or private transition state.
