# Rust Monorepo History Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import the standalone Rust implementation and all 19 of its commits into the shared code monorepo under `minion-agent-rust/`, then make it consume the single root canonical conformance suite.

**Architecture:** Join the unrelated histories with a non-squashed Git subtree import so the original Rust commit IDs remain reachable. Follow the generated import commit with one ordinary integration commit that deletes the obsolete vendored snapshot and changes `xtask conformance verify` into a monorepo-layout verifier over the root contract artifacts.

**Tech Stack:** Git subtree/bundle/worktrees, PowerShell, Rust 1.97, Cargo, Tokio test suite, Python 3.12, uv, pytest, Ruff, mypy.

**Spec:** `minion-agent-docs/process/2026-08-21-rust-monorepo-history-import.md`

## Global Constraints

- Destination path is exactly `minion-agent/minion-agent-rust/`.
- Preserve source head `041b9975b87a5a9e79180c4229cabee8a10d4bc5` and all 19 source commits as reachable ancestors with their original object IDs.
- Do not squash or rewrite destination history.
- The checked-out final tree has exactly one `conformance/` and one `pi-parity-manifest.yaml`, both at the monorepo root.
- `minion-agent-docs/` remains a separate repository.
- Keep `minion-agent-rust/` as a nested Cargo workspace; do not create a monorepo-root Cargo workspace.
- Do not introduce semantic Phase 2+ implementation work.
- Do not mutate or delete the original standalone Rust checkout.
- Use command-scoped `safe.directory`; do not modify global Git trust configuration.
- Preserve unrelated user changes in every repository.

---

## File Structure

The import creates the existing Rust tree below `minion-agent/minion-agent-rust/`. The integration task then changes only:

```text
minion-agent/
├── conformance/                              # retained canonical root data
├── pi-parity-manifest.yaml                   # retained canonical root manifest
└── minion-agent-rust/
    ├── Cargo.toml                            # remove snapshot-only dependency entries if unused
    ├── Cargo.lock                            # regenerated after dependency cleanup
    ├── crates/minion-agent/                  # imported unchanged
    ├── conformance/                          # delete entire active vendored copy
    └── xtask/
        ├── Cargo.toml                        # remove snapshot hashing/serialization dependencies
        ├── src/conformance.rs                # verify root ownership/layout; no syncing
        ├── tests/cli.rs                      # verify new CLI contract
        └── tests/conformance_snapshot.rs     # replace with conformance_layout.rs
```

---

### Task 1: Join the complete Rust ancestry under the monorepo prefix

**Files:**
- Create through Git subtree: `minion-agent-rust/**`
- Preserve: original standalone `../minion-agent-rust/**`

**Interfaces:**
- Consumes: clean destination `main` at or after `1d7d9ad`, clean source `feat/rust-plan-1` at `041b997`.
- Produces: branch `chore/import-rust-history` whose current tree contains the full source snapshot under `minion-agent-rust/` and whose ancestry contains the original source head.

- [ ] **Step 1: Create an isolated destination worktree**

Use the `using-git-worktrees` skill. From the workspace root, create a sibling worktree from current `minion-agent/main`:

```powershell
git -C minion-agent worktree add ..\minion-agent-rust-import -b chore/import-rust-history main
```

Expected: a new clean worktree at `E:\AI\Projects\OpenMinds\Minions\minion-agent-rust-import` without changing the main checkout.

- [ ] **Step 2: Reconfirm immutable import facts**

```powershell
$source = 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/minion-agent-rust'
git -C ..\minion-agent-rust-import status --porcelain
git -c safe.directory=$source -C minion-agent-rust status --porcelain
git -c safe.directory=$source -C minion-agent-rust rev-parse HEAD
git -c safe.directory=$source -C minion-agent-rust rev-list --count HEAD
git -c safe.directory=$source -C minion-agent-rust ls-files | Measure-Object
Test-Path ..\minion-agent-rust-import\minion-agent-rust
```

Expected: both status outputs empty; source head exactly `041b9975b87a5a9e79180c4229cabee8a10d4bc5`; commit count 19; tracked-file count 51; destination prefix absent.

- [ ] **Step 3: Create a recoverable source bundle**

```powershell
$source = 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/minion-agent-rust'
$bundle = 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.tmp/minion-agent-rust-before-monorepo.bundle'
New-Item -ItemType Directory -Force (Split-Path $bundle) | Out-Null
git -c safe.directory=$source -C minion-agent-rust bundle create $bundle feat/rust-plan-1
git bundle verify $bundle
```

Expected: bundle verification reports `feat/rust-plan-1` and a complete history.

- [ ] **Step 4: Import without squashing**

Run from the isolated destination worktree:

```powershell
$bundle = 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.tmp/minion-agent-rust-before-monorepo.bundle'
git subtree add --prefix=minion-agent-rust $bundle feat/rust-plan-1 -m "chore: import Rust implementation history"
```

Expected: Git creates the subtree join commit and `minion-agent-rust/Cargo.toml` exists.

- [ ] **Step 5: Verify the generated history join before integration edits**

```powershell
git merge-base --is-ancestor 041b9975b87a5a9e79180c4229cabee8a10d4bc5 HEAD
git rev-list --count 041b9975b87a5a9e79180c4229cabee8a10d4bc5
git log --graph --oneline --decorate -25
git status --short
```

Expected: ancestor check exits 0; source commit count is 19; the graph shows both histories joined; status is clean. Do not amend the generated subtree commit.

---

### Task 2: Replace vendored snapshot tooling with root-contract verification

**Files:**
- Delete: `minion-agent-rust/conformance/**`
- Modify: `minion-agent-rust/xtask/src/conformance.rs`
- Modify: `minion-agent-rust/xtask/tests/cli.rs`
- Delete: `minion-agent-rust/xtask/tests/conformance_snapshot.rs`
- Create: `minion-agent-rust/xtask/tests/conformance_layout.rs`
- Modify: `minion-agent-rust/xtask/Cargo.toml`
- Modify if dependencies become unused: `minion-agent-rust/Cargo.toml`
- Modify: `minion-agent-rust/Cargo.lock`

**Interfaces:**
- Consumes: nested Cargo workspace path and monorepo root contract layout.
- Produces: `xtask::conformance::verify_layout(workspace: &Path) -> anyhow::Result<()>` and CLI `cargo run -p xtask -- conformance verify`.

- [ ] **Step 1: Write layout tests that express single ownership**

Replace snapshot tests with `xtask/tests/conformance_layout.rs`. Build a temporary layout containing `repo/minion-agent-rust` and these root paths:

```text
repo/pi-parity-manifest.yaml
repo/conformance/schema/
repo/conformance/runtime/
repo/conformance/session/
repo/conformance/agent/
```

Tests must call `verify_layout(&workspace)` and assert:

```rust
assert!(verify_layout(&workspace).is_ok());
assert!(verify_layout(&layout_missing("agent")).unwrap_err().to_string().contains("agent"));
assert!(verify_layout(&layout_with_private_snapshot()).unwrap_err().to_string().contains("private conformance"));
```

Use a test-owned temporary directory type with `Drop` cleanup, following the existing nonce-based test pattern. Do not add a new tempfile dependency.

- [ ] **Step 2: Update CLI tests to the new command surface**

In `xtask/tests/cli.rs`:

- keep `conformance verify` as a successful command against the real monorepo layout;
- assert `conformance sync`, `conformance sync --source ...`, and unknown subcommands fail with the new usage text;
- remove every read or assertion involving `SOURCE.json`.

- [ ] **Step 3: Run the focused tests to verify RED**

```powershell
Set-Location minion-agent-rust
cargo test -p xtask --test conformance_layout --test cli
```

Expected: compilation fails because `verify_layout` does not exist and the old CLI still accepts the snapshot-oriented shape.

- [ ] **Step 4: Implement root layout verification**

Replace `xtask/src/conformance.rs` with a small layout verifier:

```rust
use std::ffi::OsString;
use std::path::Path;

use anyhow::{bail, Context};

const FAMILIES: [&str; 4] = ["schema", "runtime", "session", "agent"];

pub fn verify_layout(workspace: &Path) -> anyhow::Result<()> {
    let root = workspace
        .parent()
        .context("Rust workspace must be nested below the monorepo root")?;
    let canonical = root.join("conformance");

    if workspace.join("conformance").exists() {
        bail!("private conformance snapshot is forbidden: {}", workspace.join("conformance").display());
    }
    if !root.join("pi-parity-manifest.yaml").is_file() {
        bail!("missing root parity manifest: {}", root.join("pi-parity-manifest.yaml").display());
    }
    for family in FAMILIES {
        let path = canonical.join(family);
        if !path.is_dir() {
            bail!("missing canonical conformance directory: {}", path.display());
        }
    }
    Ok(())
}

pub fn run_cli(args: &[OsString]) -> anyhow::Result<()> {
    let workspace = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("xtask manifest directory has a workspace parent");
    match args {
        [command] if command == "verify" => verify_layout(workspace),
        _ => bail!("usage: xtask conformance verify"),
    }
}
```

Keep error messages deterministic and path-specific. Do not parse scenarios or implement semantic validation here.

- [ ] **Step 5: Remove the private snapshot and snapshot-only dependencies**

From the monorepo worktree root:

```powershell
git rm -r -- minion-agent-rust/conformance
```

Remove `serde`, `serde_json`, and `sha2` from `xtask/Cargo.toml` when no other xtask module uses them. Remove corresponding root workspace dependency entries only if `rg` proves no workspace member uses them. Run `cargo check -p xtask` to update and validate `Cargo.lock`.

- [ ] **Step 6: Run focused tests to verify GREEN**

```powershell
Set-Location minion-agent-rust
cargo fmt --check
cargo test -p xtask --test conformance_layout --test cli
cargo run -p xtask -- conformance verify
```

Expected: all commands exit 0 and verification reads `../conformance` plus `../pi-parity-manifest.yaml`.

- [ ] **Step 7: Commit the monorepo integration**

```powershell
Set-Location ..
git add -- minion-agent-rust/Cargo.toml minion-agent-rust/Cargo.lock minion-agent-rust/xtask
git status --short
git commit -m "refactor: consume canonical root conformance from Rust"
```

Expected: the staged diff includes the nested conformance deletion and tooling changes only; the original standalone checkout remains unchanged.

---

### Task 3: Prove history, ownership, and both implementation paths

**Files:**
- Verify only; no planned source changes.

**Interfaces:**
- Consumes: completed import and integration commits.
- Produces: evidence that ancestry, canonical ownership, Rust gates, and Python conformance paths survive the migration.

- [ ] **Step 1: Verify ancestry and source preservation**

From the monorepo import worktree:

```powershell
$sourceHead = '041b9975b87a5a9e79180c4229cabee8a10d4bc5'
git merge-base --is-ancestor $sourceHead HEAD
git rev-list --count $sourceHead
git cat-file -t $sourceHead
git log --oneline --follow -- minion-agent-rust/crates/minion-agent/src/runtime/fiber.rs | Select-Object -First 12
git -c safe.directory='E:/AI/Projects/OpenMinds/Minions/Minion-Agent/minion-agent-rust' -C 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/minion-agent-rust' status --porcelain
```

Expected: exit 0, count 19, object type `commit`, imported file history is visible, source checkout remains clean.

- [ ] **Step 2: Verify canonical ownership mechanically**

```powershell
if (Test-Path minion-agent-rust/conformance) { throw 'private Rust conformance remains' }
if (-not (Test-Path conformance)) { throw 'root conformance missing' }
if (-not (Test-Path pi-parity-manifest.yaml)) { throw 'root parity manifest missing' }
$all = Get-ChildItem -Recurse -Directory -Filter conformance
$all.FullName
```

Expected: the only semantic scenario directory is the monorepo root. Test-package directories named `tests/conformance` are permitted because they contain language-specific runners, not canonical scenario copies.

- [ ] **Step 3: Run every applicable Rust gate from the new location**

```powershell
Set-Location minion-agent-rust
cargo fmt --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace --all-features
cargo run -p xtask -- conformance verify
cargo run -p xtask -- layering verify
cargo run -p xtask -- coverage verify
$env:RUSTDOCFLAGS='-D warnings'
cargo doc --workspace --no-deps
Remove-Item Env:RUSTDOCFLAGS
```

Expected: every available gate exits 0. If `cargo llvm-cov` or a declared dependency is unavailable in the environment, record the exact command/error as an environmental limitation; do not claim that gate passed and do not weaken the gate.

- [ ] **Step 4: Run Python path and conformance regression gates**

```powershell
Set-Location ..\minion-agent-python
$env:UV_CACHE_DIR = (Join-Path (Get-Location) '.uv-cache-task-rust-import')
uv run pytest tests/conformance/test_schema_validation.py tests/conformance/test_runtime_conformance.py -q
uv run ruff check .
uv run mypy
Remove-Item Env:UV_CACHE_DIR
```

Expected: schema/runtime conformance and static gates pass while resolving the monorepo root suite.

- [ ] **Step 5: Verify the final branch and report**

```powershell
Set-Location ..
git status --short
git log --graph --decorate --oneline -25
git diff main...HEAD --stat
```

Expected: clean status; one subtree import commit plus one integration commit; no unrelated files. Report both commit IDs, all gate results, any explicitly unavailable gate, and the unchanged standalone source location. Do not delete the original checkout.

---

## Definition of Done

- [ ] `minion-agent-rust/` exists inside the shared code monorepo.
- [ ] Original Rust head `041b9975b87a5a9e79180c4229cabee8a10d4bc5` is an ancestor of the migration branch.
- [ ] All 19 original Rust commits remain reachable with unchanged IDs.
- [ ] The current tree has no private Rust conformance snapshot or `SOURCE.json`.
- [ ] Rust and Python resolve the same root canonical conformance data.
- [ ] Rust and Python applicable gates have fresh recorded results.
- [ ] The monorepo migration branch is clean and ready for review/integration.
- [ ] The standalone Rust checkout remains clean and recoverable.
