# Layer 12 WP-12.E1 / EXEC-007 Rust implementation candidate

Mode: Rust implementation and certification-candidate handoff

## Exact authority and candidate

- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- approved shared specification: `minion-agent-docs/master @ bf4eacdafbf9f66cb3ec80befb657575813dd46c`
- merged Python/default baseline: `minion-agent/main @ a7a5ca723f73730957141553b2502dfa91a108a9`
- coordination: `EGAILab/minion-agent#53`
- Rust candidate: `EGAILab/minion-agent#56 @ 4325072819c3fca5e2ea5e373c379f8b4e54756e`

The owner authorized Rust WP-12.E1 only after PR #55's merge was verified. This pass implements
only the approved additive `EXEC-007` surface. It does not implement WP-13.1 or begin Layer 14.

## Architecture

`minion-agent-rust/crates/minion-agent/src/execution/filesystem.rs` now owns:

- `DirEntryProbeKind`, with the exact serialized vocabulary `file`, `directory`,
  `symlink_to_file`, `symlink_to_directory`, and `other`;
- `DirEntryProbe`, whose `name` and resolved `path` identify the addressed entry rather than a
  followed target;
- additive `FileSystem::list_dir_raw` and `FileSystem::probe_dir_entry` methods;
- local-provider implementations of both methods.

The trait defaults return the existing `FsErrorCode::NotSupported`, so providers that cannot
supply the capability fail through the certified Layer-12 vocabulary without being forced to
invent an approximation.

`LocalFileSystem::list_dir_raw` performs one pre-operation abort check, invokes the provider's
raw directory enumeration, preserves that enumeration order, and returns names without stat,
lstat, classification, sorting, or kind filtering.

`LocalFileSystem::probe_dir_entry` deliberately does not inspect its signal. It resolves the
addressed path using the certified filesystem path rule, lstat-classifies the addressed entry,
and follows symlinks only for target-kind classification. Broken symlinks remain per-call errors;
plain and symlinked special kinds collapse to `other`.

Existing `list_dir`, `file_info`, `FileInfo`, and `FileKind` code paths were not changed. Layer 13
still owns sorting, per-probe skip behavior, and the successful-result cap. No Layer-13 loop was
added to production code.

## Evidence

The integration suite in
`minion-agent-rust/crates/minion-agent/tests/execution_filesystem.rs` covers:

- raw provider-order enumeration and zero target-following/eager classification;
- the approved lazy cap-before-next-probe consumption shape;
- plain file/directory and symlink-to-file/directory classification;
- plain and symlinked special kinds as `other` on Unix;
- broken-symlink per-call failure with caller-controlled continuation;
- resolved addressed-entry name/path identity;
- asymmetric cancellation semantics;
- default-provider `not_supported` behavior;
- exact enum serialization;
- unchanged existing `list_dir` and `file_info` behavior.

The manifest update is evidence/status only: `EXEC-007`'s semantic rule and `intentional
divergence` disposition are unchanged.

## Fresh gates

From `minion-agent-rust/`:

```text
cargo fmt --all -- --check
    PASS

cargo clippy --workspace --all-targets --all-features -- -D warnings
    PASS

cargo test --workspace --all-features
    PASS -- 372 tests on Windows, 0 failed
    (the additional Unix special-file witness is cfg(unix))

RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps
    PASS

cargo run -p xtask -- conformance verify
    PASS

cargo run -p xtask -- layering
    PASS

cargo run -p xtask -- coverage
    PASS
```

Shared validation from the repository root:

```text
pytest --no-cov tests/conformance/test_manifest_validation.py
                tests/conformance/test_schema_validation.py
                tests/test_layering.py
    PASS -- 218 passed

git diff --check
    PASS
```

MSVC emits the already-documented `ada-url` `LNK4098` linker warning while linking test binaries.
All compile, strict-clippy, test, and documentation gates pass.

## Findings and status

```text
PI_PARITY_DEFECT
    none

CONTRACT_ASSURANCE_DEFECT
    none

PI_BEHAVIOR_UNCERTAIN
    none

PARITY_CONSTRAINED_RISK
    none blocking

PARITY_NEUTRAL_HARDENING
    typed five-way enum; additive not_supported trait defaults

Python WP-12.E1
    CERTIFIED / MERGED

Rust WP-12.E1
    CERTIFICATION CANDIDATE

Layer 12 WP-12.E1 cross-language
    NOT CLOSED pending independent closure verification

WP-13.1 implementation
    NOT STARTED

Layer 14
    NOT STARTED
```

The next owner must independently verify PR #56 at the exact candidate SHA. Codex does not merge
or self-certify this candidate in this pass.

## WP12E1-I003 remediation

The first independent Rust closure review rejected candidate
`4325072819c3fca5e2ea5e373c379f8b4e54756e` on one assurance-only finding:
`list_dir_raw`'s no-per-entry-probing rule was true in production but only indirectly evidenced by
the broken-symlink integration witness.

Updated Rust candidate: `eb9911850c3576188a4a2d2d178c061a5382537f`.

The remediation adds one private, narrow `DirectoryProbeOperations` seam shared by the two new
EXEC-007 local-provider methods. Production uses the Tokio implementation. A unit witness invokes
the real public `LocalFileSystem::list_dir_raw` with a counting implementation and requires:

```text
raw enumeration calls
    1

symlink_metadata calls
    0

following metadata calls
    0
```

The seam does not change the public API or observable production behavior. It exists so the
contract's zero-probe invariant is mechanically observable rather than inferred from incidental
filesystem behavior.

The reviewer's exact negative control was replayed: a swallowed following-`metadata` call was
inserted once per returned name. The new witness failed with `metadata_calls = 2`; production was
then restored and the witness passed. The manifest change adds only this evidence pointer.

Fresh gates on the updated candidate:

```text
cargo fmt --all -- --check
    PASS

cargo clippy --workspace --all-targets --all-features -- -D warnings
    PASS

cargo test --workspace --all-features
    PASS -- 373 tests on Windows, 0 failed

RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps
    PASS

cargo run -p xtask -- conformance verify
    PASS

cargo run -p xtask -- layering
    PASS

cargo run -p xtask -- coverage
    PASS

shared manifest/schema/layering validation
    PASS -- 218 passed

git diff --check
    PASS
```

`WP12E1-I003` is remediated pending independent targeted closure. Candidate status remains Rust
WP-12.E1 `CERTIFICATION CANDIDATE`; cross-language closure remains pending. WP-13.1 and Layer 14
remain not started.

## WP12E1-I003 refined remediation

The targeted review of candidate `eb9911850c3576188a4a2d2d178c061a5382537f` credited the
orchestration-level witness above but correctly re-opened `WP12E1-I003` at a narrower scope: its
substitute counting implementation did not execute
`TokioDirectoryProbeOperations::read_dir_names`, so a direct per-entry Tokio metadata call inside
that concrete loop remained undetected.

The original orchestration witness remains unchanged. Two complementary witnesses now cover the
refined risk:

- `real_tokio_raw_listing_invokes_zero_probe_operations` wraps and delegates to the real Tokio
  implementation, invokes the public `LocalFileSystem::list_dir_raw` against a real temporary
  directory containing an ordinary file and a broken symlink, and requires one raw enumeration
  dispatch with zero calls through either probe operation;
- `concrete_tokio_raw_enumerator_has_no_direct_metadata_probe` guards the concrete Tokio raw-loop
  implementation itself against direct `metadata` or `symlink_metadata` calls that would bypass
  the delegating decorator's counters.

This combination distinguishes the two separate regression surfaces: orchestration accidentally
requesting a probe through the typed seam, and the concrete raw enumerator performing a direct
per-entry probe internally. No public or observable production semantics changed.

The independent reviewer's exact mutation was replayed inside the real Tokio enumeration loop:

```rust
let _ = tokio::fs::metadata(entry.path()).await;
```

With that mutation present, the concrete-loop witness failed. After restoring the correct raw
enumerator, both complementary witnesses and the retained orchestration witness passed.

Fresh gates on the refined candidate:

```text
cargo fmt --all -- --check
    PASS

cargo clippy --workspace --all-targets --all-features -- -D warnings
    PASS

cargo test --workspace --all-features
    PASS -- 375 tests on Windows, 0 failed

RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps
    PASS

cargo run -p xtask -- conformance verify
    PASS

cargo run -p xtask -- layering
    PASS

cargo run -p xtask -- coverage
    PASS

shared manifest/schema/layering validation
    PASS -- 218 passed

git diff --check
    PASS
```

`WP12E1-I003` remains pending independent targeted closure at the replacement exact SHA. Rust
WP-12.E1 remains a `CERTIFICATION CANDIDATE`; cross-language closure remains pending. WP-13.1 and
Layer 14 remain not started.

## Targeted closure, final review, merge, and cross-language closure verification

Appended by Claude (independent reviewer for the Rust side; Python/shared-contract owner). Earlier
sections above are preserved unchanged as the historical record.

### Targeted closure of `WP12E1-I003` (candidate `4301816d6ba66f3be1d5f5b4b48fdeb46f939ac0`)

The refined remediation kept the orchestration-level witness and added two complementary witnesses:
`real_tokio_raw_listing_invokes_zero_probe_operations` (a delegating decorator over the real
`TokioDirectoryProbeOperations`, run against a real temporary directory containing an ordinary file
and a broken symlink) and `concrete_tokio_raw_enumerator_has_no_direct_metadata_probe` (a structural
guard on the concrete `read_dir_names` body).

Independent replay, in an isolated worktree at the exact candidate SHA: the reviewer's original
mutation (a swallowed `tokio::fs::metadata(entry.path())` call per entry inside
`TokioDirectoryProbeOperations::read_dir_names`) is not caught by the decorator witness alone,
because it bypasses the trait dispatch the decorator counts. It is caught by the structural witness
(FAIL with the mutation, PASS once reverted). The two witnesses together close the finding.

```text
WP12E1-I003
    CLOSED
```

### Final complete review (same candidate)

```text
verdict
    APPROVED
blocking findings
    none
cargo test -p minion-agent
    PASS -- 0 failures
cargo clippy -p minion-agent --all-targets
    PASS
round-2 diff scope
    filesystem.rs test additions + 2-line manifest evidence addition only
```

### Merge (owner-authorized, executed by Codex)

```text
minion-agent-docs#157  631aaabbf07891af7f7d65c1b303f5c440d925a0
    -> master 6c807fd92d9876610b14f2a523715069a43bb004  (sole parent bf4eacdafbf9f66cb3ec80befb657575813dd46c)
minion-agent#56        4301816d6ba66f3be1d5f5b4b48fdeb46f939ac0
    -> main   0b1dd8a870c11087f8414e831a5f86003c8c489a  (sole parent a7a5ca723f73730957141553b2502dfa91a108a9)
```

Both merged trees were independently confirmed identical to their approved candidate trees.

### Cross-language closure verification (accepted default branches)

Run against `minion-agent/main` `0b1dd8a870c11087f8414e831a5f86003c8c489a` and
`minion-agent-docs/master` `6c807fd92d9876610b14f2a523715069a43bb004`, in an isolated worktree:

```text
Python full pytest
    PASS -- 1740 passed, 4 skipped, 19 xfailed
Python coverage
    PASS -- 100.00%
ruff
    PASS
manifest validation
    PASS -- 8 passed
Rust cargo test -p minion-agent
    PASS -- 347 passed, 0 failed
Rust merge Python-file delta
    none
manifest EXEC-007 evidence references
    29 listed, 29 resolve to existing Python/Rust test functions
spec section 11 contract text
    unchanged since approved revision 4 (docs merge added only this assurance record)
```

Cross-language semantics agree on every surface the contract fixes: the five-value
`DirEntryProbeKind` vocabulary (`file`, `directory`, `symlink_to_file`, `symlink_to_directory`,
`other`, verified by a Rust serde witness and the Python enum values); `list_dir_raw` returning raw
provider-order names with one pre-read abort checkpoint and zero per-entry probes; `probe_dir_entry`
doing a non-following classification plus a conditional following stat, never inspecting `signal`,
reporting a broken symlink as a per-call `not_found`, and identifying the addressed entry by the
resolved path its `file_info` counterpart produces; `not_supported` for incapable providers; and
unchanged `list_dir`/`file_info`/`FileInfo`/`FileKind`.

One documentary inconsistency was found and is corrected alongside this entry: three current-status
markers in `spec/execution.md` (the §3 inventory tag, the §11 status banner, the §11.6 heading) and
the `EXEC-007` manifest status prose still described the pre-implementation state. No semantic
contract text changed.

```text
Python WP-12.E1 / EXEC-007
    CERTIFIED
Rust WP-12.E1 / EXEC-007
    CERTIFIED
cross-language EXEC-007
    CLOSURE VERIFIED -- coherent (pending the status-only sync and the final issue #53 state write)
non-blocking WP12E1-OBS-001
    OPEN, tracked separately as minion-agent#57; not a WP-12.E1 blocker
WP-13.1 / Layer 14
    not started
```
