# Layer 12 Rust revalidation and remediation candidate

Mode: Rust implementation/revalidation

## Exact baseline and candidate

- merged code baseline: `minion-agent/main @ ea6f886a82284c80d520663b36f063d787d3f9ec`
- merged docs baseline: `minion-agent-docs/master @ 0bb3ca96e441822b58d0914d5606226b176fa92f`
- approved Python candidate: `b9c04e00aa2803304b7e9c1f5462e15eb524a709`
- approved checkpoint: `00afd5178d5c1bed4ec5175eea873061a9928fb1`
- final Python review evidence: `b794bd06f3958c321a2681348ec52e3e6ed08647`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Rust candidate: `minion-agent#46 @ 5751b732985dccc4bd6bba7797c51bcf14cb3497`

Issue `EGAILab/minion-agent#39` authorized exactly three Rust-owned obligations after Python
certification: EXEC-002/EXEC-003 file-URL revalidation against the direct Ada 2.9.2 oracle,
R004-A state 7/9/10 evidence, and the R004-B process-settlement correction. No Layer 13 work was
authorized or performed.

## EXEC-002 / EXEC-003: exact file-URL conversion

The prior Rust implementation delegated to `url::Url::to_file_path()`. That implementation did
not reproduce pinned Node's Ada-backed host validation and Unicode projection.

The candidate exact-pins `ada-url = 3.1.0`. That crate's bundled header declares
`ADA_VERSION "2.9.2"`, the same concrete engine version used by pinned Node. Production now uses
that parser for host syntax, canonicalization, host-type discrimination, and IDNA-to-Unicode. A
narrow Rust layer retains only the `fileURLToPath`-specific rules already fixed by the shared
contract: raw-backslash normalization, strict percent decoding, encoded-separator rejection,
Windows drive/UNC conversion, POSIX local-host restriction, and malformed-URL literal fallback.

The permanent unit gate consumes the already-committed direct-oracle dataset in
`minion-agent-python/tests/execution/data/r002_ada_oracle/systematic_ada292.txt`. It compares the
real exact-pinned Rust Ada binding against all 8,246 rows, including the two named bidi/version
discriminators. Result: `8,246/8,246`, zero mismatches. Separate cross-platform conversion
witnesses cover the path-specific layer after Ada parsing.

No Python output is used as the oracle.

## R004-A: deterministic first-claim classification

The production cause remains one atomic state in `{NONE, SIGNAL, EXPLICIT}`. The first successful
compare-and-exchange wins; helper success and OS-level physical causality cannot rewrite it.

New discriminating witnesses cover:

- state 7: SIGNAL claims before the natural-exit observation; a later EXPLICIT claim loses and a
  numeric process exit remains classified `aborted`;
- state 9: the external kill helper reports failure, fallback termination settles the process,
  and the already-claimed SIGNAL classification remains `aborted`;
- state 10's classification half: a delayed helper does not alter the already-claimed cause.

## R004-B: settlement on target-process exit

The prior monitor awaited `kill_process_tree()` before it awaited and published the target
process's exit. A hung external helper therefore kept every `Process::wait()` pending after the
target was already gone, contradicting the retained §6 rule.

The monitor now starts the external process-tree helper independently and races only two relevant
observations:

1. target process exit -- publish immediately, without joining the helper;
2. helper completion -- if it failed, issue the direct-child fallback, then await target exit.

The state-10 witness supplies a permanently pending helper and a real short-lived target process.
`wait_for_exit_or_kill_helper` settles successfully under a timeout, proving helper completion is
not an outcome dependency. State 9 separately proves helper failure still invokes fallback rather
than silently abandoning termination.

## Architecture and scope

- Existing typed `FileSystem`, `Subprocess`, `Process`, and error vocabularies are unchanged.
- No parallel path, process, registry, or state authority was introduced.
- Shared spec rules, dispositions, and canonical behavior were not edited.
- The manifest change is evidence-only for EXEC-002 and EXEC-005.
- Python implementation files were not modified.
- Layer 13 was not started.

## Fresh gates

From `minion-agent-rust/`:

```text
cargo fmt --all -- --check
    PASS

cargo clippy --workspace --all-targets --all-features -- -D warnings
    PASS

cargo test --workspace --all-features
    PASS -- 363 passed, 0 failed

RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps
    PASS

cargo run -p xtask -- conformance verify
    PASS

cargo run -p xtask -- layering
    PASS

cargo run -p xtask -- coverage
    PASS
```

Shared validation from `minion-agent-python/`:

```text
uv run pytest tests/conformance/test_schema_validation.py \
    tests/conformance/test_manifest_validation.py tests/test_layering.py -q --no-cov
    PASS -- 218 passed

git diff --check
    PASS
```

On MSVC, linking test binaries emits `LNK4098` from exact-pinned `ada-url` 3.1.0's own build
script selecting the static C runtime while the Rust binaries use the dynamic runtime. All link,
test, strict-clippy, and rustdoc gates pass. This is dependency build noise, not an observable
contract defect; changing the dependency source or suppressing linker diagnostics was not mixed
into this narrow semantic pass.

## Findings and verdict

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
    exact dependency pin and permanent 8,246-case direct-oracle gate

Python Layer 12 WP-12.1
    CERTIFIED

Rust Layer 12 WP-12.1
    CERTIFICATION CANDIDATE

shared Layer-12 contract
    APPROVED / IMPLEMENTED

Layer 12 cross-language
    NOT CLOSED pending independent closure verification

Layer 13
    NOT STARTED
```

The next owner must independently verify the exact remote Rust candidate and this assurance
artifact. Codex must not merge or begin Layer 13 in this pass.
