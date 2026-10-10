# L0506-D005 Rust acyclic argument-isolation audit

Coordination: minion-agent#190. Requirement: TOOL-003. **Candidate for independent Rust closure review; not self-certified.**

## Authority and scope

- Accepted code baseline: `aa14b0551292dd852db112af8903fbf9f42510c1` (Python/shared #191 merged).
- Accepted docs baseline: `fbdbc679e00bacd4b1e3a7b8ccd5f0a75340b5eb` (#278 merged).
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`. Audited `validation.ts::validateToolArguments` (structuredClone before validation), `agent-loop.ts::prepareToolCall` (validated args to the hook), and `executePreparedToolCall` (the same validated args to execute, original raw args to updates).
- Normative authority: `spec/tools.md` **Validated-argument isolation**, the feasibility matrix, contract record section 7, and Owner **L0506D005-Q001** (#190 comment 6091246259).
- **Acyclic prepared graphs only. No validation change. #193 remains open and excluded.** This candidate neither executes the characterization-only cycle case nor certifies cyclic validation.

## Changes

**No production code change.** The already-certified Rust preflight calls `PreparedValue::structured_clone()` once after preparation. Its identity memo copies containers once and keeps aliases inside the new graph; the waterfall and execute retain the resulting handles.

`minion-agent-rust/crates/minion-agent/tests/arg_isolation_conformance.rs`:

- runs all **21** unchanged canonical documents through `execute_tool_calls`, real prepare, clone, validation, registered before-hook waterfall, execute and live update dispatch;
- decodes raw JSON using certified `RawValue::decode`, including binary64 rounding and overflow; observes runtime numbers with ryu-js and named -0/NaN/infinities, strings as exact UTF-16 units, objects in their actual iteration order;
- only translates fixture shims and listener programs; never clones, validates, orders or constructs expected observations in the adapter;
- compares the entire committed expected observation, including immediate outcomes, raw-after and emitted updates, and independently checks update delivery;
- checks actual root identity across every listener and execute, not merely equality of values;
- retains a shim-produced source handle to check fresh root and nested allocation identity. Raw and prepared Rust container element types differ, so an allocation cannot be shared between them. The reused-raw-child canonical identity fact is tested by the stronger fresh-allocation assertion against the retained converted shim child, with final raw-value isolation and raw update observations also required;
- adds a real-preflight binding witness for aliases crossing object/array frontiers, repeated array references, freshness at every container, mutations in execute and retained-source/raw isolation, and K1 order after mutation.

## Discriminating controls

`minion-agent-rust/scripts/argument-isolation-negative-controls.py` mutates production seams **only in a disposable copy**. An unmutated eight-test baseline must select and pass every exact intended witness. A kill requires Cargo exit 101, the selected test failing at its declared assertion, and no compiler/setup error. Sources are restored in `finally`, then all intended witnesses must pass again. No cycle is introduced by any control.

| Control | Real seam changed | Intended witness / reason |
|---|---|---|
| shallow-copy-restored | preflight clone replaced with a fresh root retaining children | reused child: `clone isolates retained shim child` assertion fails |
| clone-forgets-aliases | clone memo reads bypassed, object and array | alias: `same` fact false |
| clone-per-listener | new clone before each hook invocation | one graph: root identity differs across listeners/execute |
| json-round-trip-clone | preflight projects through JSON | runtime values: non-finite graph cannot reach execute unchanged |
| clone-reverses-ordinary-keys | clone enumerates source object backwards | ordering: actual ordinary-key order differs |
| updates-carry-validated-instead-of-raw | update captures validated args | raw mutation: update observation contains hook mutations |

## Fresh evidence

Fresh G3 evidence (2026-10-10), code `9178c49835a4f2941fe01416a1e6dda62c666eac`:

| Gate | Windows x86_64 | Linux x86_64 |
|---|---|---|
| Workspace tests, including doctests | 661 passed, 0 failed, 0 ignored | 657 passed, 0 failed, 1 ignored |
| Isolation adapter | 8 passed; all 21 canonical documents | 8 passed; all 21 canonical documents |
| Source controls | 6/6 intended-witness kills; baseline/restored 8/8 | 6/6 intended-witness kills; baseline/restored 8/8 |
| fmt / strict Clippy / strict rustdoc / xtask conformance verify | PASS | PASS |

Shared schema and manifest validation: **915 passed** on Windows, no coverage gate requested for this Rust-only audit. Windows full-suite results were generated before the last control-output-only edits; the Rust sources, adapter and manifest are identical at the reported final code head, and the final control script was freshly rerun. Linux ran the final committed head. Existing MSVC LNK4098 `LIBCMT` linker warnings appeared on numerous unchanged test binaries and this adapter; all commands exited 0. Linux's one ignored case is the existing `explicit_waiting_queue_timer_witness` in `builtin_mutation_corpus.rs`; no new skip or ignore was added.

Both batches use pinned Rust 1.97.1 and ICU4C 78.3, and ran sequentially in the granted host window, with no competing agent gate batch. All Windows temp/cache/build files are project-local on E:. Linux uses E:-backed source/Cargo/cache/log mounts, a read-only root filesystem and `/tmp` tmpfs; no named volume. Logs are `.tmp/l0506d005-rust/{windows,linux}/{test,clippy,doc,xtask,controls-summary}.log` and the individual `controls/*.log`; shared validation is `schema-manifest.log`.

The initial control batch stopped as INVALID after two valid kills: the per-listener anchor also matched the after-hook. The script now anchors the `BeforeToolCallAction::Proceed` arm specifically. A subsequent batch reached six intended semantic failures but rejected its restored baseline because concurrent `--nocapture` output split a test-status line. Serial execution alone still allowed uncaptured panic output to split the line. The final runner uses captured output and serial test execution; its complete Windows batch proves all six intended kills and a green restored baseline. Interrupted or parser-invalid batches are not counted as complete control evidence.

Reproduction: source `.agents/project-environment.ps1` on Windows, set the pinned ICU identity and its native library path, then from `minion-agent-rust` run `cargo fmt --all -- --check`, `cargo clippy --offline --workspace --all-targets --all-features -- -D warnings`, `cargo test --offline --workspace --all-features`, `RUSTDOCFLAGS="-D warnings" cargo doc --offline --workspace --no-deps` (with the same ICU native library flag), and `cargo run --offline -p xtask -- conformance verify`. Export the committed tree into a disposable path containing `control`, then run `python scripts/argument-isolation-negative-controls.py --tree <copy>/minion-agent-rust --logs <logs>`.

Linux uses image `rust@sha256:b1b3c9c0d921d7fa0a6d1f9ec7e4eab87f8c8ec97644c3d791450f131dec813f`, Rust 1.97.1, Node 22.15.1, the verified shared ICU4C 78.3 build, and offline Cargo. Copy the E:-mounted checkout into `/tmp` tmpfs and strip CR from shell scripts; keep source mount read-only. Bind E: caches at `/cargo-home` and `/target`, logs at `/logs`, ICU at `/icu` and Node at `/node`. Set `TMP=TEMP=TMPDIR=/tmp`, `CARGO_HOME=/cargo-home`, `CARGO_TARGET_DIR=/target`, `RUSTFLAGS="-L native=/icu/icu/lib"`, `RUSTDOCFLAGS="-D warnings -L native=/icu/icu/lib"`, `LD_LIBRARY_PATH=/icu/icu/lib`, `MINION_AGENT_ICU_IDENTITY=/icu/icu-identity.txt`, `RUST_ICU_MAJOR_VERSION_NUMBER=78`; put Node and the pinned Rust toolchain on PATH. Run the same gates and controls sequentially. The task's exact local drivers and logs are under `.tmp/l0506d005-rust/`.

## Disposition

Python/shared approval and merge are already recorded on #190. Rust remains **candidate / independent closure review pending**. No new semantic mapping or divergence, validation redesign, pydantic change, preparation-boundary change, cyclic-validation claim or later-layer work is included.
