# WP-13.1 Rust implementation candidate — `read` and `ls`

Mode: Rust implementation candidate for independent shared/Python-owner review. This record is not cross-language closure or merge authorization.

## Authority and provenance

- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`.
- Accepted code baseline: `minion-agent/main @ b60f47157965c4aa81c96a20a6105758d33cbf9f` (Python WP-13.1 accepted).
- Accepted docs baseline: `minion-agent-docs/master @ 7dc654c90bcba6b8eecc41aacd789c58ecbac25e`.
- Owner Option-A representation decision: `minion-agent#48#issuecomment-5852786213`.
- Approved exact-SHA Option-A contract correction: code PR #71 `932d75250bdb24f5ea45b0ea8050c1233a0fe09e`, docs PR #170 `e4641de833a3aca2ff293b441caac87969899455`, independent approval `minion-agent#48#issuecomment-5852862615`. Those correction PRs remain separate and unmerged as of this candidate; approval explicitly allowed Rust implementation to resume.
- Rust implementation candidate: `minion-agent#72 @ 8b4eda3722fdcbc0c3fa011d87e919b77252a368`.

## Architecture

`minion-agent-rust/crates/minion-agent/src/tools/builtin/` owns `create_read_tool`, `create_ls_tool`, the shared path/truncation/numeric/MIME helpers, the pinned Photon host and image pipeline, and an ICU adapter. These construct real typed `ToolDefinition` values and return real `AgentToolResult` values. The tools use the certified `FileSystem` trait directly; they do not duplicate filesystem state, the Layer-05 registry, or Layer-06 execution semantics. The Layer-03/agent surfaces are untouched.

`read` uses `check_readable` (with the approved `not_supported` fallback), one `read_binary_file`, the pinned magic-byte sniffer, the JS-number text selection and head truncation, and the exact Photon WASM image path. All filesystem calls receive no abort signal, matching Pi; the outer race answers an abort without force-canceling the worker, and the worker checks the approved access checkpoints. A model-capability provider is consulted at image-result time, with a note only for a known non-vision model.

`ls` uses `probe_dir_entry` for the addressed directory, `list_dir_raw` for raw names, the pinned ICU root lowercase plus en-001 stable sort, then a cap-before-next-probe loop. Per-entry probe failures are skipped. The two tools retain their distinct Pi error sites and use the approved R010-B cause vocabulary where raw provider error text is not certified.

The certified Layer-12 `file_url_to_path` helper was made public and re-exported so the TOOL-026 pipeline consumes the real strict URL conversion rather than reimplementing it. Its behavior and existing callers were not changed.

The core crate retains `#![forbid(unsafe_code)]`. The narrow `minion-agent-pinned-icu` companion crate owns the unavoidable ICU FFI and Windows loaded-module enumeration. It checks runtime ICU 78.3, the official source-tarball SHA-512 identity, every loaded ICU module's name and SHA-256 against the verified-build identity file, and required common/i18n/data roles; mismatches fail closed. Rust links `rust_icu_ucol`/`rust_icu_sys` 5.8.0 against the pinned ICU build. The Windows test run used one local verified ICU4C 78.3 build from `.toolchain/icu-78.3-src` with `RUST_ICU_MAJOR_VERSION_NUMBER=78`, `RUST_ICU_LINK_SEARCH_DIR`, `MINION_AGENT_ICU_IDENTITY`, and the pinned `bin64` prepended to `PATH`.

The Photon WASM asset is the exact `@silvia-odwyer/photon-node` 0.3.4 artifact, SHA-256 `10468181565c56004c867f3a4af96f89a0ef5a63a72f2b5fb12c1f1992a3615c`, mechanically copied from the accepted Python package. The safe Wasmtime 49.0.0 host verifies that hash before compiling and invokes the same pinned exports. The compiled module is cached, while each processing call uses a fresh instance. The candidate search, EXIF orientation, BMP conversion, no-resize fast path, second resize decode, and exact encoded bytes are exercised by canonical evidence. Rust's `ImageBlock::data` stores canonical base64 text internally; the semantic value is the MIME plus exact decoded bytes, matching the approved Option-A contract. A direct language test asserts canonical Layer-02 JSON serialization.

## Conformance and language evidence

`minion-agent-rust/crates/minion-agent/tests/builtin_tool_conformance.rs` discovers all 45 shared `builtin_tool` scenario documents under `conformance/agent`, constructs filesystem fixtures, layers only schema-declared provider responses over the real `LocalFileSystem`, invokes the real `ToolDefinition` through the certified Layer-06 `execute_tool_calls` pipeline, and compares the canonical projection. The runner does not sort, truncate, decode images, classify errors, or implement queue/claim behavior. It checks image MIME, exact decoded-byte SHA-256 and length, and standard-base64 round-tripping. It also verifies filesystem call/probe traces when expected. The same test was run against the approved exact-SHA Option-A scenario tree via `MINION_AGENT_CONFORMANCE_ROOT`, without copying or modifying shared scenarios.

Focused language tests cover path preprocessing and malformed URL rejection, MIME sniffing, JS-number text selection, head truncation, pinned ICU stable sort and fail-closed identity negative controls, Photon BMP conversion/resize bytes, fast-path unchanged bytes, and canonical image serialization. The exact Photon BMP witnesses match pinned Pi byte hashes.

`agent_loop_conformance` classifies the new `builtin_tool` documents as a separate executed family, avoiding an unclassified-document regression in the pre-existing Agent suite. The lower-layer canonical and language suites remain in the full Rust workspace test gate.

## Fresh gates

From `minion-agent-rust/`, with the pinned ICU environment above:

```text
cargo fmt --all -- --check
    PASS

cargo clippy --workspace --all-targets --all-features -- -D warnings
    PASS

cargo test --workspace --all-features
    PASS — 400 tests, 0 failed (Windows, all features)

RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps
    PASS

cargo run -p xtask -- conformance verify
    PASS

Rust builtin canonical against accepted baseline and approved Option-A candidate
    PASS — 45 documents, 154 cases

shared schema + manifest validation on exact approved Option-A code candidate
    PASS — 259 tests
```

The Windows linker prints `LNK4098` (static CRT default-library conflict) when linking the pinned ICU build. It does not change loaded-library identity or test results; the strict Clippy and test commands otherwise pass. This is disclosed as toolchain/linkage hardening to watch, not a parity disposition.

No Python production file, shared semantic rule, canonical scenario, or manifest disposition was edited by the Rust implementation branch. The Option-A correction remains its own approved but unmerged PR pair. Layer 14 was not started.

## Handoff status

Rust WP-13.1 is an implementation/certification **candidate**, pending independent exact-SHA review by the shared/Python owner. It is not merged or cross-language closed. The contract correction PRs and the Rust implementation PR must not be merged without the next owner/workflow authorization. Coordination transfers to `NEXT_OWNER = Claude` after the Rust candidate and this assurance are pushed and remote-reachable.

## Remediation after independent review of the first candidate

The exact `8b4eda37` / `ff19a84c` candidate was rejected in [the independent Rust review](https://github.com/EGAILab/minion-agent/pull/72#issuecomment-5853528408). The preceding sections are the original candidate's historical evidence, not claims that its review passed. This section records the subsequent Rust-only remediation; the new exact heads and fresh gate counts are recorded below after verification.

- **RW-F001 (`PI_PARITY_DEFECT`):** a BMP converted to PNG and then resized to JPEG now constructs its conversion hint from the final MIME. The no-resize branch still names PNG. A deterministic 2100×2100 noise BMP exercises the JPEG result, while the pre-existing no-resize BMP test protects the PNG branch.
- **RW-F002 (`PI_PARITY_DEFECT`):** the scale hint now formats the exact binary64 value with ECMAScript's positive `toFixed(2)` rounding. It does not pre-round `scale * 100` in binary64. Direct witnesses assert `1.075→1.07`, `1.125→1.13`, `1.005→1.00`, `2.675→2.67`, and `1.325→1.32`; a 2150-wide BMP exercises the full image path. The positive image-dimension `Math.round` sites also use Rust's half-away-from-zero `f64::round` (RW-F004).
- **RW-F003 (`CONTRACT_ASSURANCE_DEFECT`, discriminating evidence):** new Rust witnesses cover all seven surviving material mutants. M04 aborts inside the real `FileSystem::read_binary_file` seam and checks the worker-settlement result. M09 verifies an invalid ICU identity at the sort seam. M10 presents a second same-basename loaded module with different bytes, then a byte-identical twin. M11 injects failed and truncated Windows module-path lookups. M13 uses noise whose PNG exceeds the ceiling while both JPEG qualities 80 and 85 fit, and asserts the first eligible candidate's exact bytes. M14 tests both sides of the exact base64 ceiling and demands re-encoding at equality. M19 inserts `acTL` before `IDAT` into a PNG and demands MIME rejection.

Each M04/M09/M10/M11/M13/M14/M19 witness was run against its corresponding temporary single-point mutant, observed to fail for the intended reason, and the production line restored via a narrow patch. The first M13 witness did **not** kill the 80↔85 reorder because quality 85 did not fit; its input was strengthened until both JPEG candidates fit, and the rerun then failed on the reorder. No mutant remains in the candidate.

The reviewer separately ran the first candidate in a disposable Linux `rust:1.97.1-bookworm` image with a hash-checked pinned ICU4C 78.3 build: strict Clippy, all 45 builtin canonical documents, the pinned-ICU tests and 80 library tests passed. Four full-workspace failures were confined to older Layer-12 cancellation/process/shell tests and reproduced on unmodified `main` in the same image. This is **reviewer-provided platform evidence**, not a claim that this remediation was freshly run on Linux; the lower-layer follow-ups remain out of WP-13.1 scope. `xtask layering` and `xtask coverage` are pre-existing no-op stubs and are not counted as verification gates. Only `xtask conformance verify` is counted below.

### Remediation gates and handoff

From the remediated Rust worktree, with the verified ICU4C 78.3 library/identity environment:

```text
cargo fmt --all -- --check
    PASS
cargo clippy --workspace --all-targets --all-features -- -D warnings
    PASS
cargo test --workspace --all-features -j 2 --quiet
    PASS — 409 tests, 0 failed, Windows
RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps --quiet
    PASS
cargo run -p xtask -- conformance verify
    PASS
MINION_AGENT_CONFORMANCE_ROOT=<exact Option-A #71 worktree>
cargo test -p minion-agent --all-features --test builtin_tool_conformance every_builtin_scenario_uses_real_rust_tools_and_execution
    PASS — 45 documents / 154 cases
```

The restricted test sandbox caused two pre-existing Windows subprocess tests to fail at `remove_dir_all` with OS sharing error 32. The identical `execution_process` suite passed 6/6 outside that restriction, followed by the complete unsandboxed 409/409 workspace pass. No lower-layer source was edited. `LNK4098` remains a disclosed linker warning, not a failed gate.

Remediated Rust candidate code commit: `a5ca307cee7eb9561bc2f3cc6f5935c0fd1dbc25` on PR #72. The paired assurance head is recorded in issue #48 after both pushes are verified. This remains an independent-review candidate, not a merge or cross-language closure; Layer 14 remains unauthorized.

## RW-F005: Windows module-inventory fail-closed propagation

The independent re-review of code `a5ca307c` and docs `31ca5639` closed RW-F001, RW-F002, RW-F004, and six of seven RW-F003 mutant rows, but identified [RW-F005](https://github.com/EGAILab/minion-agent/pull/72#issuecomment-5869587882): the Windows `GetModuleFileNameW` classifier was tested, while the per-handle inventory loop's propagation of its error was not. This section is an append-only remediation record; it does not rewrite the earlier candidate or its review.

The production Windows enumerator now calls `loaded_module_paths_with(handles, getter)`. That helper owns the same per-handle `module_path_with(...)?` loop used by production, with only the OS lookup injectable. Two Windows language tests present three valid ICU-role paths followed by one failed (`0`) or truncated (`buffer.len()`) lookup. One requires the whole inventory to return the complete-path error; the other passes that inventory through the real `sort_names_with_inventory` seam and requires sorting to fail before an otherwise valid three-role identity can produce a result. Existing `list_dir`/ICU identity semantics are unchanged.

The exact M11b negative control replaced the loop's `?` with a silent `if let Ok(path)` skip. Both tests failed independently: inventory incorrectly returned the three good paths, and sorting incorrectly returned `["a", "b"]`. The mutation was then restored; both tests passed. No mutant remains in the candidate. The earlier reviewer also corrected its M21 claim: the impractical exact-encoder-output boundary mutant is not counted as killed or as new evidence here.

Fresh Windows gates on final code commit `41eb013d8db9eaa14670d010dcdddaa28d37063d`, using the verified pinned ICU4C 78.3 environment:

```text
cargo fmt --all -- --check
    PASS
cargo clippy --workspace --all-targets --all-features -- -D warnings
    PASS
cargo test --workspace --all-features -j 2 --quiet
    PASS — 411 tests, 0 failed
RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps --quiet
    PASS
cargo run -p xtask -- conformance verify
    PASS
MINION_AGENT_CONFORMANCE_ROOT=<exact Option-A #71 worktree>
cargo test -p minion-agent --all-features --test builtin_tool_conformance every_builtin_scenario_uses_real_rust_tools_and_execution -- --nocapture
    PASS — 45 documents / 154 cases
```

The test count was independently checked with `cargo test --workspace --all-features -- --list` (411 `: test` entries). The previously disclosed Windows `LNK4098` warning remains non-fatal. No Linux rerun is claimed for this Windows-only targeted change. No shared contract, Python code, canonical scenario, or lower-layer behavior was changed. The pair remains pending independent exact-SHA review; neither merge nor cross-language closure nor Layer 14 is authorized.
