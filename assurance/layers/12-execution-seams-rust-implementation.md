# Layer 12 Rust implementation and certification candidate

Mode: Rust implementation/certification

Approved shared baseline:

- minion-agent/main at c772938f70d1932b8d27a44aab956f3d338cde74
- minion-agent-docs/master at 554a0750fcbdc5346f6f0407af621339d65a79f8
- pinned Pi b7bb00b936dbe21b8e160b3e89efdec361846699
- approval artifact assurance/layers/12-execution-seams-final-contract-review-4.md

Rust candidate commit: 60ba230785e65d322e4170c0fa3841779d127d30

## Scope

This pass implements only WP-12.1:

- the ctx.fs, ctx.shell, and ctx.subprocess capability services;
- their typed result/error vocabularies;
- local providers;
- FsTarget, opaque TargetKey, and provider-scoped process_path;
- execution-world identity and consumer-triggered compatibility validation.

It does not implement built-in tools or the mutation-serialization queue. Those remain Layer 13.
Python Layer 12 remains unimplemented, so this candidate does not claim cross-language closure.

## Architecture

Production code is under minion-agent-rust/crates/minion-agent/src/execution/:

| Module | Ownership |
|---|---|
| error.rs | exact FsErrorCode, ShellErrorCode, and SubprocessErrorCode vocabularies |
| signal.rs | read-only abort observation plus separately held cancellation authority |
| filesystem.rs | typed FileSystem, local provider, operation-specific cancellation, and FsTarget |
| subprocess.rs | argv-direct spawn, raw byte streams, repeatable wait/terminate, and tree termination |
| shell.rs | discovery/precedence, callbacks, aggregate output, timeout/abort, idle grace, and cleanup |
| world.rs | opaque identities, equality-only compatibility, and ordered incompatible pairs |
| service.rs | fs, shell, and subprocess Runtime service values plus one local-provider bundle |

Certified lower-layer Runtime service ownership is reused. The execution module does not create a
parallel registry or global compatibility rule. Compatibility remains a consumer-invoked check.

TargetKey is a private-representation newtype exposing equality/hash only; callers cannot parse its
canonical-path implementation. FsTarget carries private provider provenance so process_path can
reject a foreign-provider target as permitted hardening.

The local shell provider composes the real local subprocess provider. Shell-only text decoding,
callbacks, aggregate output, timeout precedence, and the 100ms idle-grace rule do not leak into raw
Process.wait().

## Evidence

Rust language/integration evidence:

- execution_filesystem.rs: seven tests covering nested writes, line limiting, invalid UTF-8,
  metadata/listing, cancellation, replacement rename, temporary creation, FsTarget, and cleanup;
- execution_process.rs: five tests covering argv-direct spawn, raw pipes, environment, repeatable
  wait, idempotent termination, signal cancellation, and spawn failures;
- execution_shell.rs: seven tests covering output/callback aggregation, nonzero exit success,
  callback precedence, timeout boundary, pre-abort, discovery order, environment, and cleanup;
- execution_world.rs: four tests covering equality-only symmetry, ordered incompatible pairs,
  unrelated provider legality, shared local identity, and service names.

The approved Layer-12 contract contains a prose witness matrix but no executable Layer-12 canonical
scenario family. No Rust runner was invented to substitute for absent shared canonical evidence.
All existing canonical families pass through the unchanged xtask conformance verify gate.

The manifest change is evidence-only: EXEC-001 through EXEC-006 Rust pointers and test lists now
name the production modules and integration tests. Rules and dispositions are unchanged.

## Fresh gates

From minion-agent-rust/:

    cargo fmt --all -- --check
        PASS
    cargo clippy --workspace --all-targets --all-features -- -D warnings
        PASS
    cargo test --workspace --all-features
        PASS -- 354 passed, 0 failed
    RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps
        PASS
    cargo run -p xtask -- conformance verify
        PASS
    cargo run -p xtask -- layering
        PASS
    cargo run -p xtask -- coverage
        PASS (repository-configured gate)

Shared validation:

    pytest --no-cov tests/conformance/test_manifest_validation.py
        tests/conformance/test_schema_validation.py
        PASS -- 213 passed
    manifest inventory
        101 rows / 101 unique IDs
    git diff --check
        PASS

## Findings

    PI_PARITY_DEFECT
        none
    CONTRACT_ASSURANCE_DEFECT
        none
    PARITY_CONSTRAINED_RISK
        none blocking
    PI_BEHAVIOR_UNCERTAIN
        none
    PARITY_NEUTRAL_HARDENING
        opaque TargetKey; foreign-FsTarget provenance rejection;
        incremental UTF-8 callback decoder; typed error payloads

## Candidate status

    shared Layer-12 contract
        APPROVED / IMPLEMENTED IN RUST
    Python Layer 12
        NOT IMPLEMENTED
    Rust Layer 12
        CERTIFICATION CANDIDATE
    Layer 12 cross-language
        NOT CLOSED
    Layer 13
        NOT STARTED

The next owner independently verifies the exact remote Rust candidate and this evidence. This pass
does not authorize Layer 13.
