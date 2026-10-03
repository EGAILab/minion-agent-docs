# WP-12.E4 / EXEC-010 — Rust implementation candidate

Status: **IMPLEMENTED CANDIDATE; independent CLOSURE_REVIEW pending**. This implementation does not certify itself.

Exact code candidate: `4589c5aad2f652791a4c7071b46e0077351573a0` on `layer/12-e4-rust`. The paired docs SHA is recorded by the handoff, avoiding a self-referential commit identifier.

## Authority and starting state

- Code: accepted `main @ 3f98a22aee6876efb380b380be1f63c2aeb2ad33` (Python/shared PR #138).
- Docs: accepted `master @ 31294d35dcd8fea08f95f05c944718ea388fd661` (PR #230).
- Independent shared/Python approval: docs #230 comment `5970715165`.
- Authorization/handoff: minion-agent#130 comment `5970723112`, with #130 RUST_IMPLEMENTATION / NEXT_OWNER Codex; Owner implementation instruction in the controlling conversation.
- Normative contract: `spec/execution.md §15`, EXEC-010; Owner F1/F2 Option A and C002 Option B. Pi `b7bb00b936dbe21b8e160b3e89efdec361846699`; Node **v22.15.1**.

Python is CERTIFIED at that merged pair as recorded by the shared owner. Rust remains a candidate, and WP-12.E4 cross-language closure is not established by this record.

## Implementation / semantic ownership

`execution::Platform` closes the provider declaration to Windows/Posix. `Subprocess::platform()` is read-only; `LocalSubprocess` returns its compile-time local family. There is no public retagging field or setter. The execution-world identity and all existing spawn behavior are unchanged.

`execution::EnvSnapshot` owns private `EnvEntries`: POSIX names/values as byte vectors, Windows names/values as the certified `JsString` UTF-16 primitive. Borrowed entries and lookups are immutable; `copy()` returns a deep owned entry copy. Constructor/clone/copy introduce no shared mutable identity. This accommodates remote/virtual native baselines without forcing them through scalar strings. Snapshot entry order is not normative.

`LocalSubprocess::base_env()` clones its **existing configured baseline**, not the ambient host environment. The unchanged baseline is `std::env::vars()` captured at construction, or `with_base_env`'s supplied map. E4-OBS-2 (construction-time capture) and E4-OBS-3 (non-Unicode construction panic) are **recorded, not changed**. No `vars_os` substitution, live host refresh, env overlay change or spawn lifecycle change was made.

Windows snapshot lookup processes UTF-16 units through native unit uppercase. The core crate retains `forbid(unsafe_code)`. A small dependency-free `minion-agent-native-env` crate isolates the value-only `ntdll!RtlUpcaseUnicodeChar` FFI call on Windows. On other hosts, the core uses the same shared pinned table. This binding does not capture an environment or own provider policy.

`tools::builtin::environment` owns the §15.5 consumer helpers, not a bash implementation:

1. `node_environment_view`: POSIX bytes or generalized UTF-8 from Windows UTF-16; pairs combine, lone units remain their three-byte invalid sequences; invalid names are dropped; values use maximal-subpart replacement; BOM is retained.
2. Exact-spelling removal and scalar-string injection.
3. `windows_spawn_environment`: sort names by UTF-16 units, compute Unicode-16 full root-uppercase keys, retain the first name for each key. It never merges entries at snapshot capture or substitutes this key for native lookup.
4. The existing `SpawnOptions` env can receive the full scalar result with `inherit_env = false`; JS-string-to-OS projection remains a separate boundary (identity for these scalar outputs).

The existing pinned-ICU crate supplies `upper_unicode16_batch`: it verifies the loaded ICU4C 78.3 artifact identity once per composition transaction, maps only code points assigned by Unicode 16.0, and uses root full uppercase. There is no new ICU build, external crate upgrade, global locale change or persistent pin-verification cache.

## Required artifact integrity

Vendored without re-derivation from the accepted Python artifact into:

`minion-agent-rust/crates/minion-agent/src/execution/windows_upcase.json`

SHA-256:

`78580c216df002802980880f491c6ef31dc594f8c8ca2cb23f27b0d90f637df8`

The copy contains **973** mapped units and build-26200 provenance. A Rust-scoped `.gitattributes` rule marks it `-text` so Git cannot alter its byte-based pin through line-ending conversion. The permanent test verifies its hash and map count. No authority table was regenerated. The full 65,536-unit live/pinned comparison passes on this Windows host; differences on other Windows builds remain the expressly disclosed contract hazard, not a universal identity claim.

## Evidence

`crates/minion-agent/tests/execution_environment.rs` covers:

- Exact artifact hash/count and exhaustive current-host native/pinned comparison.
- Native lookup: ASCII case, é/É, distinct ß/ss and ı/I, astral suffix distinctions, lone UTF-16 units; no capture-stage deduplication.
- Isolated snapshots and mutable deep copies, including a provider baseline change after obtaining a snapshot.
- All eight POSIX value rows, invalid names, kept non-ASCII names, BOM and exact POSIX lookup.
- Windows lone high/low units, three replacements, invalid-name dropping and explicit-pair/scalar equivalence.
- Five duplicate pairs, both insertion orders, selected names and values.
- Fake Windows provider baseline/ProgramFiles/PATH, exact MINION removal, injection and duplicate arbitration.
- Local declaration and configured-map authority, independent provider clone/configuration and snapshot stability.
- Real provider spawn: inherited baseline equals a reconstruction with inherit=false; a caller-only env remains exact under inherit=false.

The two compile-fail doctests protect snapshot mutability and platform retagging. Each has a positive compilation/runtime neighbor. During development the first mutation attempt exposed a missing native rustdoc search path that could make compile-fail tests pass vacuously. That harness defect was corrected; the positive neighbors pass, and making the protected fields public now fails specifically because the forbidden snippets **compile successfully**, not because linkage is unavailable.

`scripts/e4-negative-controls.py` emits guarded forward/inverse apply_patch faults without writing the source itself. Its anchors must match exactly once. Results are in `data/12-wp12e4-rust/negative-controls.json`: **14/14 killed** through real assertion or doctest failures, all restored:

| Fault | Discriminator |
|---|---|
| public snapshot entries | compile-fail witness unexpectedly compiles |
| public/retaggable provider platform | compile-fail witness unexpectedly compiles |
| host baseline instead of configured baseline | local configured-map witness |
| ASCII-only native lookup | é/É lookup |
| lowercase consumer arbitration | sharp-S pair |
| ASCII-only consumer arbitration | non-ASCII pair |
| casefold consumer arbitration | dotless-I pair (mutant implements the exact casefold results of these control inputs) |
| one replacement per unpaired unit | three-replacement value |
| pair encoding without combining | explicit-pair value |
| BOM stripping | POSIX BOM row |
| retaining invalid names | invalid-name row |
| last enumerated duplicate wins | UTF-16-first value/name |
| case-insensitive removal | inherited MINION case variant |
| inherit=false leaks configured baseline | real caller-only child |

Fresh execution of the committed Windows Node probes (`unicode_names.mjs`, `native_names.py`, `envunits_win.py`) matches all three committed outputs after LF/CRLF normalization only. Linux native probes were not rerun on a Linux kernel in this Windows pass; POSIX byte rules execute in the portable Rust witnesses. No new canonical family was fabricated: §15's approved evidence is binding-level tests.

## Gates and reproduction

Fresh G3 results: full workspace tests **541 passed / 0 failed** (including four doctests: two positive compilation guards and two compile-fail protections); the new environment integration binary has **10 passed / 0 failed**. Format check, strict workspace/all-targets/all-features clippy, warnings-denied rustdoc and xtask conformance verification all passed. All 14 source mutants were killed by the intended assertion/compile-fail observation, then restored before the full suite. These are implementation evidence, not independent certification.

The existing MSVC link invocation emits LNK4098 (LIBCMT conflict); tests nevertheless link and pass. No new external dependency or linker policy was introduced. Full-suite output is retained locally in `.tmp/e4-rust/test-final.log`; the exact command includes `--no-fail-fast -j 2` and the environment below.

Pinned Rust **1.97.1**, offline cached dependencies; existing verified ICU4C 78.3 build. Build output is on **C:** (`C:/Users/erick/AppData/Local/Temp/minion-d4-rust-target`), not the nearly-full E: drive. Local `.tmp/e4-rust/cargo.ps1` records the full environment. Required linkage/runtime inputs:

```text
RUST_ICU_MAJOR_VERSION_NUMBER=78
RUSTFLAGS=-L native=<verified ICU>/icu/lib64
RUSTDOCFLAGS=-D warnings -L native=<verified ICU>/icu/lib64
MINION_AGENT_ICU_IDENTITY=<verified ICU>/pinned-icu-identity.txt
PATH includes <verified ICU>/icu/bin64 and the pinned Rust toolchain
CARGO_TARGET_DIR=<C: build-output directory>
```

The native search path in RUSTDOCFLAGS is needed by the **positive** doctest guard, not just documentation generation. Use the normal equivalent lib path on other hosts. Commands:

```text
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace --all-features --no-fail-fast
RUSTDOCFLAGS="-D warnings <native search path>" cargo doc --workspace --no-deps
cargo run -p xtask -- conformance verify
```

Shared schema/manifest validation was executed against the accepted candidate source: **404 passed**, **118/118 unique manifest rows**. The shared contract, Python source and manifest semantics were not modified.

## Scope / stop

No new platform, managed-tool PATH, bash tool, E4-OBS-1/2/3 remediation or other work package is implemented here. Prior Layer-12 operations and historical certifications are not reopened. The immutable API and source guards preserve ownership while permitting provider-neutral lossless native data.

Reusable verification lesson: compile-fail evidence needs a matching positive compilation guard when external linkage is involved; an unrelated linker failure is not discrimination. It is recorded here without modifying process authority in this implementation task.

Next: independent exact-SHA CLOSURE_REVIEW by Claude. No merge, cross-language certification or next-layer work is performed by the implementer.
