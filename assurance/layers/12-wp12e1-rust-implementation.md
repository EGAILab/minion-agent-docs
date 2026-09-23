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
