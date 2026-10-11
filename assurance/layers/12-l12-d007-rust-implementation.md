# L12-D007 Rust implementation candidate

Status: independent Rust closure review pending; **not certified**.

## 1. Authority and scope

Implementation starts at code `51e53ba711d2cd4ecfdce7e7478016646397978b`
and docs `e652cc8a61ed2cd63743db17b453ce0c5dc26283`, handed off on
minion-agent#199 comment 6104299937. Authority is pinned Pi
`b7bb00b936dbe21b8e160b3e89efdec361846699`, Node 22.15.1 / libuv 1.49.2,
spec/execution.md sections 19.1–19.5 and the section 17 correction.
Owner O001 ADOPT PI (comment 6103080422) supersedes L12-D005's conditional
Windows EPERM recovery. Python is not the Rust oracle.

Excluded: #127 multi-failure selection, #133-F2 native-name decoding,
subprocess/shell error codes. EXEC-007/008/009 retain their operations and
not_supported semantics; their failures use the corrected mapper.

## 2. Implementation

- `execution/filesystem.rs` maps Windows raw native errors through libuv's
  literal table rather than ErrorKind's lossy translation. Open, mkdir,
  directory-query and read/write overrides apply at the failing call only.
  A read/write handle denial becomes ERROR_INVALID_FLAGS (unknown), before
  EOF handling. Read's path-less fallback retains the logical JS string.
- `minion-agent-native-fs` owns Windows handles for libuv-equivalent CreateFileW
  access/disposition and sharing; handle-based NtQueryDirectoryFile enumeration
  uses FILE_LIST_DIRECTORY without a separate metadata probe. Unlink/rmdir
  use own-entry disposition, with read-only correction never following links.
- `execution/filesystem/rimraf.rs` implements target validation, fresh entry
  classification, unlink-to-rmdir routing, rmdir-first traversal, failure
  propagation and Windows fixWinEPERM as an explicit work stack. Recovery
  performs own-attribute correction, following inspection and one retry;
  correction/inspection failures preserve the original error except ENOENT.
  Retry failures retain their own error and failing-call origin.
- Recursive disappearance acceptance is platform-neutral. A missing target
  without force remains not_found. Existing NUL containment and native
  JS-string projection remain at their certified boundaries.
- The pending append write is still joined with flush before returning.

## 3. Evidence and containment

`fs_path_domain_conformance.rs` runs the real LocalFileSystem with canonical
fs-error-codes, error-origin, path-domain and NUL cases. Fixture setup supports
symlinks, own-entry ACL denial, exclusive handles and byte-range locks.
Every fixture mutation, provider target, restore and cleanup has a positive
containment proof. Restore only acts on an existing non-link entry; failures
are loud. Permission-sensitive Linux cases are separately run as uid 1000;
root's skipped permission cases are not credited as coverage of that surface.

The Rust CE-02 probe is the private Operations collaborator injected into the
real LocalFileSystem.remove, not a second removal implementation. It emits
the agreed JSON shape and compares all 13 + 18 + 10 rows against byte-copied
pinned-Pi Windows/Linux outputs in `filesystem/ce02-data`. Calls, origins,
remaining entries, read-only state and unfired injections are checked.
All nine copied matrix/oracle files match the original docs Git blob IDs at
the approved baseline (not merely parsed JSON equality). Windows checkout
CRLF conversion is not treated as an oracle change.

Binding witnesses include:

- real read/read-lines/read-binary/write/append handle-phase denials with a
  lone-surrogate logical path, unknown before EOF;
- a 2048-level controlled tree through real remove on a 256 KiB thread stack;
- a child vanishing between enumeration and fresh lstat, plus no-force missing
  target regression;
- real read-only targets/trees and protection of a link's read-only target.

`scripts/error-codes-negative-controls.py` checks every intended baseline,
requires the selected test and row plus its assertion failure, rejects compile
or setup failures, restores sources and proves the restored baseline. Mutants
operate only on a disposable containment-checked copy. N6/N8/N11/N13 may
intentionally bypass an injection; all other matrix controls must fire it.
Windows-only recovery controls are NOT_APPLICABLE on Linux, not credited there.
The Owner-adopted recovery controls replace the historical L12-D005 synthetic
conditional-retry controls; those old anchors do not certify this new policy.

## 4. Development findings

Self-found and fixed before handoff: std OpenOptions translated a Windows
directory-write failure differently from Pi, so the native call now uses
CreateFileW with libuv's flags and call-specific EISDIR override. The initial
listing metadata precheck was replaced with handle-based directory enumeration
to preserve EXEC-007's no-per-entry-probe boundary. A fixture proof reparsed a
colon-containing relative suffix as a drive; full absolute components now
avoid that error. The I004 witness was strengthened from mapper-only evidence
to all five real provider handle phases.
The strengthened test guard initially refused a canonical `.` resolving to
its own case root before dispatch. Such roots are now positively proven from
the explicit fixture base; the base, project root and drive root remain refused.
The non-root Linux corpus includes a successful rename of a mode-000 directory.
Cleanup independently proves and resets its newly encountered directory entry;
the stale original restore path is never used to authorize this operation.
This cleanup adjustment is Unix-only and does not change provider outcomes.

An unconstrained development build exhausted allocation resources; it was
stopped and investigated, and gates use two Cargo jobs. A first full test
attempt omitted MINION_SEARCH_ENGINE_ARTIFACTS and failed the official-artifact
prerequisite; that setup attempt is not credited. Fresh final gates use pinned
ICU and official search artifacts. No shared semantic rule was changed.

The first Linux clippy pass stopped before tests on two cfg-only lints:
the retained Windows read-only tests' import and the Windows rename-cleanup
helper lacked Windows cfg guards. Both are now guarded, without changing the
active Windows code or any provider behavior. That failed batch is not credited;
final Windows and Linux gates are rerun sequentially at the corrected head.

The next Linux clippy pass identified a Unix-only fixture literal: permission
mode `0` must be written as `0o0` under the current clippy lint. The value is
unchanged. This pass also stopped before tests or native fixtures; its result
is not credited. The corrected source receives a focused Linux clippy check
before the final Windows-then-Linux G3 runs.

The first full Linux test run at `4ee8938b` stopped on recovery row
`L9-link-to-readonly-target`: result, origin, calls and remaining entries
matched Pi, but the binding probe reported an empty read-only list. The probe
had wrongly restricted both read-only fixture setup and its observer to
Windows. Pi's recovery probe uses `chmod(0444)` and observes the owner-write
bit on both platforms. The Rust test now creates mode-0444 entries on Unix
and observes their owner-write bit without following links; Windows fixture
behavior is unchanged. No production or oracle change was made. That failed
run is retained and not credited; the corrected candidate receives fresh
Windows-then-Linux gates and controls.

The first disposable control copy omitted three neutral corpus files included
by existing Rust unit tests. Recompiling its first mutant failed at compile
time; that attempt was INVALID, not a kill. The copy recipe now includes the
frontmatter, ignore and ADA oracle files, and the control driver rewrites the
unmutated sources before checking every baseline, forcing a fresh build.

During that corrected-head control rebuild, a separate Minion-Memory batch
occupied the host from 18:24 to 18:33 on 2026-10-11. No intended witness or
mutant result had completed during the overlap: the first baseline result
was written at 18:34:42, after the coordinator's HOST CLEAR at 18:33:29.
The credited control observations run in isolation after that clearance.
The corrected-head Windows G3 had already completed at 18:08 and was not
overlapped. Linux starts only after the Windows controls finish.

## 5. Reproduction environment

Windows uses Windows 11 Pro x86-64 build 26200, Rust 1.97.1
(`8bab26f4f`, 2026-07-14), the pinned ICU 78.3 identity and official search-engine
artifacts. Dot-source the project `.agents/project-environment.ps1` for every
shell; use its project-local Cargo home and Windows target, with
`CARGO_BUILD_JOBS=2`, `RUST_ICU_MAJOR_VERSION_NUMBER=78`, ICU's `bin64` on PATH,
`RUSTFLAGS=-L native=<project>/.toolchain/icu-78.3-src/icu/lib64`, and
`RUSTDOCFLAGS=-D warnings -L native=<same lib64 directory>`.
Set `MINION_AGENT_ICU_IDENTITY` to that build's `pinned-icu-identity.txt` and
`MINION_SEARCH_ENGINE_ARTIFACTS=<project>/.toolchain/search-engines/dl`.
Run fmt, clippy (all targets/features, `-D warnings`), full workspace tests,
rustdoc and xtask conformance verify; run the CE-02 test with `--nocapture`.
The Windows linker emits the pre-existing ICU LIBCMT/LNK4098 warning; it is
disclosed, not suppressed.

For Windows controls, copy the tracked `minion-agent-rust/` and `conformance/`
trees into a disposable project-local sandbox, together with these three
compile-time test inputs (preserving their repository-relative paths):
`minion-agent-python/tests/skills/data/frontmatter-corpus.json`,
`minion-agent-python/tests/skills/data/ignore-corpus.json`, and
`minion-agent-python/tests/execution/data/r002_ada_oracle/systematic_ada292.txt`.
Do not copy targets or Git metadata. Prove each copy destination's lexical
and real ancestry before copying. With the environment above, invoke
`python minion-agent-rust/scripts/error-codes-negative-controls.py --tree
<sandbox>/minion-agent-rust --logs <project>/.tmp/<control-logs>` from the
candidate checkout. The script refuses a control tree outside the project,
validates every mutation destination, and restores all source files even
when a control is INVALID. Its final restored-baseline check is mandatory.

Linux uses the cached `rust:1.97.1-trixie` image
(`rust@sha256:b1b3c9c0d921d7fa0a6d1f9ec7e4eab87f8c8ec97644c3d791450f131dec813f`),
Rust 1.97.1 and Node 22.15.1.
Observed container: Debian 13.6 x86-64, Python 3.13.5;
host kernel `6.18.40.1-microsoft-standard-WSL2`. No added capability or privileged
mode is used. The permission-sensitive corpus subprocesses use uid/gid 1000
and clear supplementary groups.
The committed `scripts/l12d007-linux-gates.sh` is the exact in-container recipe:
copy the source to private tmpfs `/tmp`, strip CR from shell scripts, use
`RUSTFLAGS` and `RUSTDOCFLAGS` with `-L native=/build/icu/lib`, and run the full
gates, CE-02 probe, uid-1000 corpora and controls sequentially. The launcher
proves every bind source's resolved ancestry immediately before Docker:
project worktree (read-only), separate Linux Cargo home/target (writable),
ICU and Node/search artifacts (read-only), project log directory (writable).
The container root is read-only; `/tmp` is a private executable tmpfs.
No named volume or host location outside the project is writable.

## 6. Fresh gates

Interim draft: the Windows results below are at
`3235a8974f3dd7ed11da30ca5758b38904eaca77`. The subsequent Unix fixture-literal
correction is `4ee8938b98bcfb46b390b85a0408cf678d5ea7bf`; focused Linux fmt/clippy
passed there. Its full Windows G3, 41-row probe, 17 controls and 921 shared
validation tests passed. Its Linux full tests exposed the probe-fixture defect
described in section 4, so the corrected final-head gates remain pending. These draft
results do not hand off or certify the later head.

- Windows full workspace/all-features tests: **669 passed, 0 failed, 0 ignored**.
  fmt, clippy (all targets/features, `-D warnings`), rustdoc (`-D warnings`)
  and xtask conformance verify passed. The real path-domain adapter compares
  all **604** applicable cases (240 error codes + 237 NUL + 127 prior path/tool
  cases); no Windows case is excluded. The 21-document read-only corpus passes
  its Windows-applicable cases.
- Windows controls: **17/17 KILLED**, all 17 intended unmutated witnesses selected
  and passed, then the restored baseline passed.
- Shared manifest/schema validation: **921 passed** on the candidate.
- Linux results and the final standalone CE-02 results are recorded at handoff
  after sequential runs. Independent review, merge and certification remain
  required.
