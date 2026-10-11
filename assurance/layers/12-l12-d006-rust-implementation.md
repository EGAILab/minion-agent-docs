# L12-D006 — Rust interior-NUL filesystem rejection

Status: implementation candidate; independent Rust closure review pending. This
record does not certify the candidate or close #194, #65 or #133-F1.

## 1. Authority and provenance

- Coordination: `minion-agent#194`, Rust owner Codex; Owner decision on #65 and
  #133-F1 selects **PINNED PI UNKNOWN** (decision digest
  `ebb3579cd2a32f96d634a6c06dd6a26e1cfcc931e39df6ae32b3446902887f1c`).
- Normative authority: `spec/execution.md` §18, composed with the certified
  L12-D001 logical/native path and §14.8 error-origin rules.
- Adopted Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`, real harness
  `NodeExecutionEnv` and `toFileError`, Node `v22.15.1`. The shared 237-case
  `fs-path-nul.json` is derived from this authority, not from Python results.
- Merged starting code: `0ab81a0c518f15e899738cc0ce986d29b2bcd61b` (#196).
  Merged starting docs: `e499c91d022e086be0f6fa3c5cb046e1752471d0` (#280).
- Short-lived branches: `layer/12-l12d006-rust` and
  `assurance/12-l12d006-rust`. Python and shared normative semantics are unchanged.

## 2. Implementation

`crates/minion-agent/src/execution/filesystem.rs` distinguishes an interior-NUL
binding rejection from an ordinary `InvalidInput`: the native path contains NUL,
the error is `InvalidInput`, and it has no OS error number. Only that rejection
becomes `unknown`. The general mapper remains unchanged; non-NUL `InvalidInput`,
OS-origin `InvalidInput` and `InvalidData` remain `invalid`.

The NUL binding rejection has no native `err.path`. Existing call-site error
handling therefore supplies the resolved **logical** path, including unpaired
UTF-16 units; it never substitutes the OS projection. Rename preserves its source
fallback even when it is the destination whose argument is rejected. Temp-dir
rejection has no fallback; temp-file rejection names the would-be file after its
directory was created.

This is not a blanket early-validation rule. Abort, non-positive line limits,
lexical operations and write/append parent creation retain their certified order.
`canonical_path` alone checks the entire resolved argument before any walk, as
Node's realpath does; `resolve` propagates that failure without a lexical fallback.
File-URL decoding remains at the certified resolution seam, before the rejected
native call. No new public API or dependency is introduced.

## 3. Real-seam evidence

`tests/fs_path_domain_conformance.rs` extends the existing thin real-provider
adapter with the additive shared operation/step fields. It compares the committed
expectations without regenerating or rewriting them: **237 NUL cases on each
platform**, together with all prior L12-D001 cases (117 Windows plus 10 declared
Linux-only exclusions; 127 Linux). Its count assertions reject a missing corpus.

`tests/execution_nul.rs` adds six permanent witnesses:

1. NUL is unknown and the logical fallback retains a lone surrogate.
2. `%00` in a valid file URL is decoded before classification; rename names source.
3. Write and append create a new parent before a final-component rejection.
4. Whole-argument canonical rejection precedes a nonexistent-prefix walk; resolve
   propagates it.
5. Temp-dir has no fallback; temp-file names the would-be file and leaves its new
   directory observable.
6. Real registered read/write/edit/ls tools render the certified failure through
   the real execution pipeline; write's mutation-queue failure precedes mkdir.

The prior L12-D001 NUL-origin witness is retained with its now-authorized `unknown`
expectation. The private `l12d006_other_invalid_input_keeps_invalid` unit protects
the general mapper and OS-error distinction.

## 4. Intended-witness controls (§9.7)

`scripts/nul-path-negative-controls.py` mutates only an explicitly disposable
`control-code` tree. It first proves each intended witness is selected and passes;
source anchors must be unique and non-equivalent. A kill requires Cargo's test
failure status, the exact intended test's `FAILED` line, one runtime failure and
the discriminating assertion text. Compilation/setup errors are INVALID. Finally
it restores the source and proves all intended witnesses green again.

| Control | Intended witness / reason |
|---|---|
| Global `InvalidInput` remap | Private mapper unit: unrelated `InvalidInput` must stay invalid |
| Keep NUL invalid | NUL/provider witness: error code must be unknown |
| Native projected fallback | Same provider witness: fallback must retain the logical lone unit |
| Premature write validation | Parent-creation witness: parent must already exist |
| Raw-argument-only remap | File-URL witness: `%00` has no raw NUL but is rejected after decoding |
| Canonical walk before check | Missing-prefix witness: whole-argument NUL rejection wins |

Merely removing Rust's explicit canonical check would be equivalent here because
`std::fs::canonicalize` also validates its entire NUL-containing argument. The
walk-before-check control instead performs a prefix metadata walk first, which is
the semantically wrong mechanism this witness must detect; an equivalent mutation
is not counted as a kill.

## 5. Fresh gates and reproducibility

Fresh Windows G3 passed: fmt, strict clippy, full workspace tests **671 passed,
0 failed, 0 ignored**, strict rustdoc and xtask conformance verification. The full
G3 source was `f66a6444ee52fe8a8c5aa0b2273e76dfa76f97c0`. The subsequent
`30fa1b45c0e6d133cc5e0b787dfb5831296d39af` changes only the negative-control
script's NUL-invalid source anchor; production, tests and manifest are identical.
At that final source, shared manifest/schema validation passed **920 tests**.
Windows controls proved all six intended baselines green, **6/6 intended-witness
kills**, and all six restored baselines green. The first controls attempt was
INVALID (a non-unique anchor), not a semantic kill; it was restored and replaced
by this uniquely anchored replay. Existing MSVC LNK4098 test-link warnings remain
disclosed; none caused a gate failure.

Linux full workspace tests at the final source passed **667 tests, 0 failed,
1 ignored**. The ignored existing witness is
`recursive_remove_single_failure_reports_the_inner_native_call`, requiring a
non-root POSIX permission run; this root-run result does not claim that witness.
The NUL 237-case corpus and every new binding witness passed. Linux fmt, strict
clippy, strict rustdoc and xtask conformance verification also passed. All six
Linux controls were killed by their intended assertions, and every restored
intended baseline passed. The corrected sequential Linux launcher exited 0;
the interrupted launcher attempt remains uncredited.

Windows and Linux batches run sequentially under the granted host reservation.
Rust `1.97.1`, the verified shared ICU 78.3 build and Node `v22.15.1` are used.
Cargo is offline, with the existing pinned lock/vendor stores. All writable host
storage is under the project on E:. Linux copies source into tmpfs `/tmp` for POSIX
fixtures, strips CR only in that copy's shell scripts, and binds the E-local Linux
Cargo home/target and ICU/artifact stores; no Docker named volume is used.

### Safety preflight and interrupted evidence

The drive-root incident in an unrelated characterization interrupted the earlier
Windows batch. That incomplete run is not credited. Before this resumed batch,
the task adapter, binding witnesses and control runner were hardened:

- `tests/support/fs_containment.rs` checks each computed mutation argument after
  production path resolution, both rename endpoints, fixture creation and every
  individual cleanup deletion. Raw parent traversal, drive-relative, bare-drive,
  UNC and absolute mutation names are refused; colon names require `./`.
- Windows fixture allocation is explicitly under the project `.tmp/process-temp`;
  Linux requires an explicit private container fixture sandbox. Lexical and real
  containment are both checked, and unresolved links fail closed.
- The control runner requires a disposable `control-code` tree, checks source and
  log writes/restoration, and verifies the temp/Cargo environment before launch.
- The launchers check every host output/mount target; archive links are refused.
  Container copies use checked per-file operations rather than unchecked recursive
  copying. The root filesystem and individual source binds are read-only; only the
  E-local Linux Cargo home, target and log directories are writable host binds.

The Owner independently confirmed private container tmpfs writes on 2026-10-10.
The first Linux launch was stopped after discovering a launcher defect: assignment
to PowerShell's read-only `$HOME` failed, but execution continued and that existing
system value became an unauthorized writable `C:\Users\erick` bind. No Linux gate
logs were produced and that attempt is not credited. No cleanup or recovery was
attempted; a read-only check found no `rustup` directory, while Claude separately
reported no Cargo/rustup artifacts. These are limited observations, not proof of
the complete absence of writes. Incident: #194 comment 6097826521.

The Owner answered **Yes** to correcting the launcher and resuming Linux under
three conditions: non-colliding variable names, Stop error handling plus native
exit checks, and immediate lexical/real containment checks on every actual bind
source strictly below the project root. Decision/correction recorded at #194
comment 6100128663. The corrected launcher uses `$taskCargoHome`, strict mode,
`$ErrorActionPreference = 'Stop'`, a checked Docker exit and `Assert-BindSource`.
It refuses all reparse-point ancestors and even the root directory itself. Its
preflight rejects `C:\Users\erick`, the project root and an outside sibling.
Inspection of the resumed container confirms every host bind source is below E's
project root, with only the stated Cargo home/target and log directories writable.
The new safety checks do not change production code or canonical expectations.
The legacy lower-layer fixtures are not claimed to have all been rewritten with
this helper; their temporary allocation is nevertheless pinned by this recipe.

### Reproduction environment

On Windows, source the project `.agents/project-environment.ps1` in each fresh
shell. Set `CARGO_BUILD_JOBS=2`, `RUST_ICU_MAJOR_VERSION_NUMBER=78`,
`RUSTFLAGS=-L native=<project>/.toolchain/icu-78.3-src/icu/lib64` and
`RUSTDOCFLAGS=-D warnings -L native=<project>/.toolchain/icu-78.3-src/icu/lib64`.
Use `MINION_AGENT_ICU_IDENTITY=<project>/.toolchain/icu-78.3-src/pinned-icu-identity.txt`,
put that build's `icu/bin64` on PATH, and set
`MINION_SEARCH_ENGINE_ARTIFACTS=<project>/.toolchain/search-engines/dl`.
Run the five G3 commands sequentially, with `--offline` on Cargo dependency users.
Export the committed code tree to a checked project-local `control-code` directory;
run `python minion-agent-rust/scripts/nul-path-negative-controls.py --project-root
<project> --tree <control-code>/minion-agent-rust --logs <project-local-logs>`.

Linux uses the existing x86_64 Rust 1.97.1 image
`rust@sha256:b1b3c9c0d921d7fa0a6d1f9ec7e4eab87f8c8ec97644c3d791450f131dec813f`,
with `--pull never --rm --read-only --tmpfs /tmp:rw,exec,size=16g`.
Construct `/project` from individual read-only binds of project `AGENTS.md`, the
code worktree, `.tmp/l12d006-rust`, `.tmp/wp141-node-linux` and `.toolchain` at their
corresponding `/project/...` destinations. Do not bind the root itself. Writable binds are exactly the project
`.tmp/cache/cargo-home-linux`, `.tmp/cache/cargo-target/linux` and task log directory,
at their corresponding `/project/...` paths. Copy the code and a separate control
copy into `/tmp/l12d006-session/{work,control-code}`; normalize CRLF to LF only in
the copied `*.sh` files. Refuse source links and check each destination's lexical
and real containment. Create `/tmp/l12d006-session/fixtures` and set
`MINION_FIXTURE_ROOT`, `TMP`, `TEMP`, `TMPDIR` to that path.

Set `CARGO_HOME=/project/.tmp/cache/cargo-home-linux`,
`CARGO_TARGET_DIR=/project/.tmp/cache/cargo-target/linux`, `CARGO_BUILD_JOBS=2`,
`RUSTUP_HOME=$CARGO_HOME/rustup`, `RUSTUP_TOOLCHAIN=1.97.1`,
`RUST_ICU_MAJOR_VERSION_NUMBER=78`,
`RUSTFLAGS=-L native=/project/.toolchain/icu-78.3-linux/icu/lib`,
`RUSTDOCFLAGS=-D warnings -L native=/project/.toolchain/icu-78.3-linux/icu/lib`,
`LD_LIBRARY_PATH=/project/.toolchain/icu-78.3-linux/icu/lib`, and
`MINION_AGENT_ICU_IDENTITY=/project/.toolchain/icu-78.3-linux/icu-identity.txt`.
Use Node v22.15.1 on PATH and the same read-only engine artifact store under
`/project/.toolchain/search-engines/dl`. Disable Python bytecode writes. Run G3 from
the copied work tree, then the control script with `--project-root /project
--container-sandbox /tmp/l12d006-session --tree
/tmp/l12d006-session/control-code/minion-agent-rust --logs <bound-task-log>/controls`.
No extra capability or privileged mode is requested. The task-local launcher and
per-gate logs are retained under `.tmp/l12d006-rust` for the independent reviewer.

## 6. Boundaries and closure handoff

The correction does not alter unrelated `InvalidInput`, file-URL semantics,
logical/native projection, cancellation, rename fallback, parent creation,
read-only removal, permission/error-code policy or native-name decoding.
Subprocess NUL (#195), #133-F2, #67/#69/#125 and the other deferred Layer-12
findings stay separate. macOS is not claimed by these Windows/Linux gates.

Python is already merged under the independent final review. Rust remains a
candidate, **not certified**. Claude independently reviews the exact pushed code
and docs heads; only that closure review can certify this Rust delta.
