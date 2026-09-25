# WP-12.E2 / EXEC-008 Rust implementation candidate

Mode: Rust implementation and exact-SHA closure handoff. This is not a cross-language closure verdict.

## Authority and provenance

- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- accepted shared contract: `minion-agent-docs/master @ 7007732a26965facff73ccdaf82b4ee856d3683e`, `spec/execution.md` §12 and `EXEC-008`
- merged Python/default baseline: `minion-agent/main @ 9987bd8112168792e41d8da5b474c8c7f330b1d1` (approved Python PR #63)
- owner merge/Rust authorization: `minion-agent#62`, [governance comment](https://github.com/EGAILab/minion-agent/issues/62#issuecomment-5825599328); full issue-body transition verified before both merge and Rust coding
- Rust code PR: [minion-agent#64](https://github.com/EGAILab/minion-agent/pull/64) @ `54e33cf8c8d155f6ad4d66076a32ea0dc0034f7b`

The implementation starts from the verified squash merge of the exact approved Python candidate. The squash-merge tree equals Python PR #63's reviewed tree; its parent is the prior accepted `main` commit. No Python file was changed by the Rust candidate. WP-13.1 and Layer 14 remain outside this authorization.

## Implementation mapping

`FileSystem::check_readable(path, signal)` is additive. Its default is `FsErrorCode::NotSupported` for providers without the capability. `LocalFileSystem` resolves the path through the already-certified `resolved()` seam and runs a single metadata-class native query on Tokio's blocking pool. The signal argument is accepted but not inspected.

- POSIX: safe `nix::unistd::access(path, R_OK)` with no preliminary stat or content open. The operation's own errno is classified by the existing `map_fs_error`. An embedded NUL is rejected as `unknown` before the C-string boundary.
- Windows: safe `OpenOptionsExt` requesting only `FILE_READ_DATA` (also `FILE_LIST_DIRECTORY` for directories), `FILE_FLAG_BACKUP_SEMANTICS`, and permissive sharing. This follows the final symlink, tests read/list ACLs, closes the handle without consuming content, and preserves the owner-approved difference from Node/libuv's attribute-only Windows access. An embedded NUL is rejected as `unknown` before the native call.

No existing `FileSystem` method, `FsErrorCode`, path resolver, `FileInfo`, or `FileKind` behavior was changed. The manifest change updates only EXEC-008 implementation/evidence/status pointers; its behavioral rule and `intentional divergence` disposition remain unchanged. No Layer-13 read tool or fallback was implemented.

## Discriminating evidence

Rust tests in `execution_readability.rs` and `execution_filesystem.rs` exercise readable files/directories, relative resolution, symlink-following and dangling-target failure, Windows deny-read ACLs on files and directories, host path-shape errors, embedded NUL classification, pre-aborted-signal non-inspection, provider `not_supported`, and unchanged `file_info`/file content. Linux-only tests cover `access(R_OK)` permission modes and parent search permission, FIFO without a writer (prompt return, no content open), and symlink-loop error mapping. The Linux suite was executed both as root and as an unprivileged user; only the latter can discriminate permission-bit behavior.

The canonical Layer-13 tool path is not implemented in this work package. EXEC-008's approved §12.6 witness matrix is exercised through the real Rust filesystem seam, not a runner simulation. Existing canonical suites continue to run through `xtask conformance verify`.

## Fresh gates

From `minion-agent-rust/` at the candidate:

```text
cargo fmt --all -- --check                                  PASS
cargo clippy --workspace --all-targets --all-features -- -D warnings  PASS
cargo test --workspace --all-features --quiet               PASS: 381 tests, 0 failures; 0 doctests
RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps    PASS
cargo run -p xtask -- conformance verify                     PASS
cargo run -p xtask -- layering                              PASS
cargo run -p xtask -- coverage                              PASS
```

Linux Docker Rust focused suite: 7/7 passed as root and 7/7 as unprivileged `nobody`. Windows focused suite: 6/6 passed. Shared manifest/schema validation: 213/213 passed. `git diff --check` passed. The pre-existing MSVC `ada-url` `LNK4098` linker warning remains nonfatal and is not introduced by EXEC-008.

## Findings and handoff

```text
PI_PARITY_DEFECT             none found
CONTRACT_ASSURANCE_DEFECT    none found in executable EXEC-008 semantics
PI_BEHAVIOR_UNCERTAIN        none
PARITY_CONSTRAINED_RISK     none blocking
PARITY_NEUTRAL_HARDENING    safe typed platform wrappers; no unsafe code in the crate

Python EXEC-008             approved and merged
Rust EXEC-008               certification candidate, independent review pending
WP-12.E2 cross-language     NOT CLOSED
WP-13.1 implementation      NOT AUTHORIZED
Layer 14                    NOT STARTED
```

The approved spec §12 still carries its original draft-era authorization/status marker. That marker is documentary state, not a new semantic rule; the durable issue #62 governance and exact-SHA approval supersede it operationally. The shared owner should status-sync it at closure without changing §12's behavioral contract.

Next owner: Claude, for independent exact-SHA Rust closure verification of PR #64 and this assurance candidate. Codex does not merge its own Rust candidate or start WP-13.1.

## Narrow remediation after independent closure review

The independent review of code `54e33cf8c8d155f6ad4d66076a32ea0dc0034f7b` and this artifact at `227b06894afa3b99643351b0fa39132bd4541266` found two blockers. This section appends their remediation; the earlier candidate record above is preserved as the state reviewed at those SHAs.

### WP12E2-RI001 — host unsupported is not provider incapability

The previous local implementation reused `map_fs_error`, whose `io::ErrorKind::Unsupported` branch produces `FsErrorCode::NotSupported`. A host `ENOSYS` or Windows error 120 could therefore masquerade as a provider lacking EXEC-008. The additive `map_readability_error` now maps only this host-error kind to `Unknown`, leaving every other error kind and all existing uses of `map_fs_error` unchanged. The trait default remains the only `NotSupported` source for `check_readable`.

Permanent tests cover `NotFound`, `NotADirectory`, `PermissionDenied`, `InvalidInput`, generic `Other`, and `Unsupported`; POSIX raw `ENOENT`, `ENOTDIR`, `EACCES`, `ELOOP`, `EIO`, `EINVAL`, and `ENOSYS`; and Windows raw error 120. A temporary negative-control mutation restoring the broad `map_fs_error` call made `host_readability_errors_never_report_missing_provider_capability` fail with actual `NotSupported` versus expected `Unknown`; the conforming mapper was restored before final gates.

### WP12E2-RI002 — permanent stat-before-access race witness

The POSIX production path still performs one `access(path, R_OK)` and no preliminary stat. A narrow internal query boundary now permits a deterministic unit witness to remove an existing target immediately before that authoritative access call. It asserts one query and `NotFound` from the access syscall, not a fabricated permission denial. The boundary changes no public API or observable production behavior.

A temporary guarded stat-then-boolean-access mutation at that boundary made `target_removed_at_access_boundary_preserves_not_found_and_one_query` fail with actual `PermissionDenied` versus expected `NotFound`; the conforming implementation was restored. This is the I001 mechanism the first Rust candidate's tests failed to distinguish. The POSIX permission test also gained a scope-bound mode-restoration guard so a failed assertion does not strand a 000 directory and hide later test results.

### Fresh remediation gates

```text
Windows Rust 1.97.1:
  cargo fmt --all -- --check                                  PASS
  cargo clippy --workspace --all-targets --all-features -- -D warnings  PASS
  cargo test --workspace --all-features --quiet               PASS: 383 tests, 0 failures
  RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps    PASS
  cargo run -p xtask -- conformance verify                     PASS
  cargo run -p xtask -- layering                              PASS
  cargo run -p xtask -- coverage                              PASS

Linux Docker:
  filesystem unit tests                                       8/8 PASS
  focused EXEC-008 integration tests                          7/7 PASS as root
  same integration binary                                     7/7 PASS unprivileged

Shared validation:
  manifest/schema/layering pytest                             218/218 PASS
```

No Python implementation, shared semantic rule, manifest disposition, other Layer-12 operation, WP-13.1 implementation, or Layer-14 file changed in this remediation. The issue #62 follow-ups for pre-existing Layer-12 behavior remain separate and unauthorized for this pass.

Remediation code candidate: [minion-agent#64](https://github.com/EGAILab/minion-agent/pull/64) @ `f339dfcadff5ceb76dd607498cd092c461bb09a9`.

Current disposition: RI001 and RI002 are *remediated, pending independent exact-SHA re-review*; not self-closed or cross-language certified. No merge is authorized.
