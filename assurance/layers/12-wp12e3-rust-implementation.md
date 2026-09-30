# WP-12.E3 / EXEC-009 — Rust implementation candidate

**Status:** Rust candidate for independent exact-SHA implementation review, not cross-language closure.

## Authority and starting state

- Pinned Pi `b7bb00b936dbe21b8e160b3e89efdec361846699`: `packages/coding-agent/src/core/tools/edit.ts:96-109,347-356` calls one `fs.access(path, R_OK | W_OK)` before reading. The approved Windows rule is an explicit Minion mapping, not a claim that libuv's Windows attribute-only behavior is equivalent.
- Accepted code `main` at branch creation: `ada1032644d3da701f4ad319a7d5e1402aafcf4d` (merged Python EXEC-009).
- Accepted docs `master`: `41374e7953fc4d1f8eab9bd879a186048b69c609` (`spec/execution.md` §13 and approved implementation review).
- Coordination: `minion-agent#79`, `RUST_IMPLEMENTATION`, `NEXT_OWNER = Codex` at start. The branch was created directly from accepted `main`; unrelated local worktrees were preserved.

## Typed Rust seam

`minion-agent-rust/crates/minion-agent/src/execution/filesystem.rs` adds `FileSystem::check_read_write(path, signal?)` with a default `not_supported` result for providers lacking EXEC-009. The first-party `LocalFileSystem` override resolves with the existing §3.2 path rule and performs one blocking host decision outside the async executor. Its accepted signal is deliberately not inspected.

- POSIX: one `nix::unistd::access` with `R_OK | W_OK`, retaining its errno; NUL is rejected before the call. A host `Unsupported` error maps to `unknown`, never to the capability-level `not_supported` answer.
- Windows: one `OpenOptions`/`CreateFileW` open with `FILE_READ_DATA | FILE_WRITE_DATA`, all share modes, `OPEN_EXISTING` (the default), and `FILE_FLAG_BACKUP_SEMANTICS`. It does not request `FILE_DELETE_CHILD`, create, truncate, consume bytes, or open the final reparse point itself. NUL is rejected before the open. The returned handle closes immediately.
- The existing `check_readable`, `list_dir`, `file_info`, error vocabulary, and every other Layer-12 operation remain unchanged. No Layer-13 edit-tool consumption was implemented.

The Rust evidence derives from §13.6 and the pinned Pi/approved host mapping, not from Python implementation mechanics. The new `execution_read_write_access.rs` tests direct/relative/symlink success, non-mutation, directory success, missing/dangling/non-directory/NUL classes, signal non-inspection, POSIX non-root permission matrix, FIFO non-blocking, symlink loop, and Windows ACL/read-only-attribute cases. Existing `execution_filesystem.rs` verifies a provider without the extension returns `not_supported` for every path. Private host-boundary unit tests assert one probe and NUL-before-probe behavior; error-mapping tests include host `Unsupported -> unknown`. Readability-only, writability-only, existence-only, truncating-open, and delete-child-requesting implementations are discriminated by the applicable witnesses. A mounted read-only filesystem was not available; the POSIX errno boundary is exercised with an injected `EROFS` result rather than a fake mount.

## Fresh gates

All commands ran on the candidate with the verified workspace ICU4C 78.3 build selected (`RUST_ICU_MAJOR_VERSION_NUMBER=78`, `RUST_ICU_LINK_SEARCH_DIR` and `MINION_AGENT_ICU_IDENTITY` pointing to `.toolchain/icu-78.3-src`, its `bin64` first on `PATH`, and pinned native link search). The initial attempt without this environment failed in third-party `rust_icu_sys`; it is not an EXEC-009 failure.

| Gate | Result |
| --- | --- |
| `cargo fmt --all -- --check` | PASS |
| `cargo clippy --workspace --all-targets --all-features -- -D warnings` | PASS |
| `cargo test --workspace --all-features --quiet` | PASS: **419 passed**, 0 failed, 53 result groups; includes certified lower-layer regressions |
| `RUSTDOCFLAGS='-D warnings' cargo doc --workspace --no-deps --quiet` | PASS |
| `cargo run -p xtask -- conformance verify` | PASS |
| Shared Python schema/manifest validation (`test_manifest_validation.py`, `test_schema_validation.py`) | PASS: **264 passed** |
| Focused Windows filesystem tests | PASS: `execution_filesystem` 16/16, new `execution_read_write_access` 6/6; direct one-probe unit witness 1/1 |
| Linux pinned-ICU container, EXEC-009 integration binary run as unprivileged `nobody` | PASS: **5/5**, including actual POSIX 0444/0222/0666 permission witnesses and FIFO |
| Linux POSIX injected one-access/errno unit witness | PASS: **1/1** |

The Windows linker reports an existing `LNK4098` CRT-default-library warning when linking with the pinned ICU imports; it does not fail the strict Rust clippy/doc gates. No Python source, shared spec, canonical expected behavior, or manifest disposition changed. The manifest's `rust:` field is evidence-only and explicitly says independent closure review is pending.

**Handoff:** independent Claude review of the exact pushed Rust code and docs evidence SHAs. Python EXEC-009 is merged; Rust EXEC-009 is **IMPLEMENTED, NOT YET CERTIFIED**; WP-12.E3 cross-language is **NOT CLOSED**. WP-13.2 implementation and Layer 14 remain outside this pass.
