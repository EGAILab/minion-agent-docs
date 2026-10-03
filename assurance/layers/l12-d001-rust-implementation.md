# L12-D001 — Rust implementation candidate

Implementer: Codex. Independent closure review: **PENDING**. This record does not certify the implementation.

## 1. Authority and provenance

Owner authorization: [issue #123 comment 5966887521](https://github.com/EGAILab/minion-agent/issues/123#issuecomment-5966887521). Implementation handoff: [comment 5944836121](https://github.com/EGAILab/minion-agent/issues/123#issuecomment-5944836121).

Starting accepted branches: code `4c735ed6b14409aec508e01b382f0254f71b05cf`; docs `c8a7f77c632d086ae46a825192ca72ce101403c4`. Code candidate: PR #132, `b46ce592c1fda0322b572528a2bd6111d4e59794`, branch `layer/12-d001-rust`. The change is confined to Rust; Python, shared spec, manifest semantics and canonical expected results are unchanged.

Authority is pinned Pi `b7bb00b936dbe21b8e160b3e89efdec361846699`, its `packages/agent/src/harness/env/nodejs.ts`, the adopted tool path pipeline, and accepted `spec/execution.md` §14. Node v22.15.1 `MKDirpAsync` and `rimraf` supply the error-origin rules already agreed in CE-L12-D001-01. No Python implementation is used as the behavioral oracle.

## 2. Typed implementation

`execution::FsPath` reuses the certified `ResultString`/`JsString` UTF-16 primitive. It is not a second string authority. The filesystem trait accepts lossless paths; `FileInfo`, `DirEntryProbe`, `FsTarget` and `FsError.path` carry the appropriate lossless value. Scalar convenience methods convert into the same trait seam. The primitive gains `Hash` for location-key use, without changing equality or serialization.

| Carrier | Implementation boundary |
|---|---|
| logical resolution/join | code-unit lexical operations in `execution/path.rs`; no UTF-8 or OS conversion |
| local OS arguments | explicit `String::from_utf16_lossy` immediately before the native operation; valid pairs survive |
| logical outputs | absolute path, metadata identity, missing-target key, abort/no-path errors retain logical units |
| native outputs | canonical path, enumerated names, OS failing-call paths use the actual native value |
| existing-target key | native canonical path; all projected aliases agree |
| file URL | USVString projection at the URL-constructor boundary, then the unchanged delegated Ada conversion |
| tool path and text | prepared UTF-16 extraction and code-unit interpolation through read/write/edit/ls, including edit patch headers |

`LocalFileSystem` uses an explicit Node-compatible mkdir walk instead of the host recursive-create shortcut. Its pending-child `EEXIST`/failed-stat branch returns `not_directory`; a final failed stat preserves the stat error. Rename OS errors carry source, while Pi's pre-call abort carries the logical destination. Per-entry listing errors retain the actual entry. Recursive removal carries each failing call rather than overwriting it at the enclosing operation. The existing excluded #125 code/outcome behavior is not changed; a directory refusal's no-path carrier is logical.

Scalar regression fixtures needed typed signatures. One Windows fake previously addressed fixture scripts using Rust's `\\?\` canonical prefix; it now matches Node-compatible ordinary canonical paths. The old scalar target-key assertion was adapted for the same representational difference. No canonical expected result was edited.

## 3. Canonical and binding evidence

`tests/fs_path_domain_conformance.rs` is a thin real-provider/real-tool adapter. It does not calculate path projection or repair provider output. Cases select only their committed platform expectation; listing order normalization is confined to the canonical observation. All tool cases use the actual Runtime and Layer-06 execution seam.

| Document | Linux | Windows |
|---|---:|---:|
| names | 22 | 22 |
| missing | 22 | 22 |
| aliases | 2 | 2 |
| file URL | 10 | 10 |
| error origin | 66 | 56 |
| tools | 5 | 5 |
| total executed | **127** | **117** |

Windows excludes exactly the ten committed Linux-only directory-open cases, printing their #67 notes. These are not reported as executed successes.

Permanent focused witnesses cover native aliasing and distinct missing keys, logical metadata, logical-directory/native-entry listing composition, valid-pair preservation, independent unpaired-unit replacement, logical abort paths, cancellation non-inspection for metadata/append, rename source origin and destination abort, and the non-recursive directory no-path carrier. `execution::filesystem::tests` also supplies the deterministic vanished-entry interleaving and the injected failed-stat walk. The real POSIX recursive-remove failure runs as **nobody**, not root; it is explicitly ignored by default and run with `--include-ignored` in the Linux driver. All seven focused Linux tests execute in that run (six on Windows).

Supplementary no-path audit: Node v22.15.1 rejects NUL-containing arguments with `ERR_INVALID_ARG_VALUE` and no `err.path` (`data/l12-d001-rust/nul-probe.cjs`). A path containing both NUL and an unpaired surrogate therefore needs a logical fallback too. The candidate preserves that carrier through thirteen operations, parent-mkdir failure and rename, without moving validation ahead of write/append parent creation. **The existing Rust code mapping is deliberately unchanged:** readability/read-write NUL refusals are `unknown`; generic filesystem NUL binding failures are `invalid`. The latter differs from Pi's `toFileError` default `unknown` for `ERR_INVALID_ARG_VALUE`; it is an inherited scalar error-code gap, not remediated or claimed as new code parity by this path-carrier delta. This disclosure is for the closure reviewer's scope assessment, not a new shared disposition.

## 4. Discriminating controls

Seventeen controls were applied individually to production source, compiled, executed and restored. Every control failed an assertion or panicked at the intended runtime boundary; compilation failure is not counted as a kill. Exact source replacements and failing witness identifiers are in `data/l12-d001-rust/negative-controls.json`. Most controls were executed before the supplementary NUL carrier correction; their mechanisms and canonical witnesses are unchanged. The requested-target control was re-executed with the final source shape. The NUL control reverts only `filesystem.rs` to the prior candidate `a55bfb1`, keeping the new permanent witness, and fails at write's logical-vs-native path assertion.

The ten FSP-Q001 controls are: early tool projection, tool-text projection, non-scalar refusal, ls-dot substitution, raw Windows OS passthrough, strict host-codec refusal, valid-pair replacement, raw directory component leakage, projecting missing keys, and logical existing keys. Additional controls cover requested-target origin, host recursive-create shortcut, listing-directory origin, failed-stat `EEXIST`, the enclosing-catch carrier, and recursive-root origin. The last control leaves all 127 canonical cases green but fails the real non-root inner-call witness, demonstrating why that binding evidence is necessary.

Rust's analogue of the Python enclosing-catch defect is overwriting an already-carried `FsError.path` in the outer `remove` mapping. It is not an exception-introspection implementation; the corresponding mutant is still detected.

To replay a control, apply only its `before` → `after` replacement to a clean code candidate, run the identified canonical or binding test, require RED, restore it, then require GREEN. For `listing-directory-origin` and `failed-stat-exists`, run `cargo test --all-features --lib execution::filesystem::tests`. For `recursive-root-origin`, run the Linux binding driver as below. Other controls use `cargo test --all-features --test fs_path_domain_conformance`.

## 5. Build and replay

Pinned Rust toolchain: **1.97.1**. Windows uses the already-verified shared ICU4C 78.3 build and identity file (`RUST_ICU_MAJOR_VERSION_NUMBER=78`, native link directory, runtime DLL path, `MINION_AGENT_ICU_IDENTITY`). The repository's pinned ICU build instructions apply; no alternate system ICU is substituted.

Linux uses `rust:1.97.1-bookworm`, the official ICU4C 78.3 source artifact with SHA-512 `04a49455e1489030c520a4bfd2664fa2171e7938d08f2acdbbcb1fda976639fd8b1f0704f2eec89ba59a7b6d118ceaab6ec5a096e40d9085a0895d91ce225245`, and a source-built ICU in an isolated build volume. Source is mounted read-only. The replay driver is `data/l12-d001-rust/linux.sh`: mount the code candidate at `/src`, an isolated writable build volume at `/build`, and the verified archive directory at `/artifacts`; invoke the driver with `sh`. It verifies the archive, builds ICU if absent, creates the library-integrity identity, runs all 127 canonical cases, three lexical/URL/scalar-compatibility unit tests, and explicitly runs all seven binding tests as a non-root user. For independent replay, use a fresh build volume rather than trusting an existing ICU install.

## 6. Fresh final gates

| Gate at code `b46ce592` | Fresh result |
|---|---|
| `cargo fmt --all -- --check` | PASS |
| `cargo clippy --workspace --all-targets --all-features -- -D warnings` | PASS |
| `cargo test --workspace --all-features` (Windows) | **503 passed, 0 failed, 0 ignored** across workspace test binaries |
| `RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps` | PASS |
| `cargo run -p xtask -- conformance verify` | PASS |
| shared schema + manifest validation | **404 passed** (focused gate; Python whole-suite coverage disabled, not claimed) |
| docs process suite | **336 passed** |
| Linux canonical corpus | **127/127** |
| Windows canonical corpus | **117/117**, ten explicitly documented exclusions |
| focused binding tests | Windows **6/6**; Linux non-root **7/7**, including the explicitly enabled permission witness |
| Linux lexical/URL/scalar compatibility units | **3/3** |
| runtime source controls | **17/17 detected**, all restored |

The Windows pinned-ICU linker emits its existing `LNK4098` default-library conflict warning. This is disclosed; it does not turn into a Rust clippy/rustdoc warning, and all executable gates complete successfully. No full Linux workspace gate is claimed: Linux evidence in this pass is the complete domain corpus and the focused binding/unit suites above.

An earlier complete regression attempt caught two scalar fixture addressing/assertion mismatches, which were repaired as described above. A diagnostic run caught and corrected an intermediate interpolation regression (`{i}` left literal in an edit error). Those failed runs are not reported as approval evidence. Source mutants are all removed, and the code worktree is clean at the reported commit.

## 7. Boundaries and handoff

`#67`, `#125`, `#126`, `#127` remain excluded and unremediated. In particular, recursive-child removal here is sequential; **multi-failure first-settled parity is not claimed**. Windows EPERM chmod/retry is not added. macOS remains deferred with reason. No bash/E4, K1, WP-13.2 redesign or later-layer work is included.

Python L12-D001: already CERTIFIED at the accepted baseline. Shared contract: APPROVED / MERGED. Rust: **IMPLEMENTED CANDIDATE, NOT CERTIFIED**. Cross-language closure: **PENDING independent review**. NEXT_OWNER after verified handoff: Claude, CLOSURE_REVIEW. No merge or certification is performed by this implementation pass.
