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
