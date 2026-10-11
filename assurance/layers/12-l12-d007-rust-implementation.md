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
Closure review 1 found that this replacement also dropped four still-governing
disappearance witnesses. That was an evidence defect, not an obsolete policy:
section 7 restores readdir, first/final rmdir and recovery-unlink ENOENT coverage.

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

The subsequent Linux full suite at `485f5e85` stopped at the existing NUL
temp-creation witness: `std::env::temp_dir()` was `/tmp`, while the explicitly
declared fixture base was `/tmp/l12d007/fixtures`. This was a recipe prerequisite
failure, not a provider outcome mismatch. The recipe now sets TMP/TEMP/TMPDIR
to that contained fixture base after creating it. Its source copy preserves
timestamps so the shared Cargo target can reuse unchanged inputs. The failed
log is retained; neither this incomplete G3 nor its unexecuted controls is
credited. No Rust production, test assertion, or oracle change was made.

The first disposable control copy omitted three neutral corpus files included
by existing Rust unit tests. Recompiling its first mutant failed at compile
time; that attempt was INVALID, not a kill. The copy recipe now includes the
frontmatter, ignore and ADA oracle files, and the control driver rewrites the
unmutated sources before checking every baseline, forcing a fresh build.

During the historical `3235a897` control rebuild, a separate Minion-Memory batch
occupied the host from 18:24 to 18:33 on 2026-10-11. No intended witness or
mutant result had completed during the overlap: the first baseline result
was written at 18:34:42, after the coordinator's HOST CLEAR at 18:33:29.
The credited control observations run in isolation after that clearance.
That historical Windows G3 had already completed at 18:08 and was not
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
Run `cargo check -p minion-agent-native-fs` independently (before any workspace
check, so feature unification cannot mask undeclared native dependencies).
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

Final code candidate: `a2fa8333060b350b0f2cb1697fc1a8c9d563121a`
(minion-agent PR #206, branch `layer/12-d007-rust`). The evidence below was
run at that exact head, Windows then Linux sequentially, on 2026-10-11/12.
The assurance candidate is minion-agent-docs PR #289, branch
`assurance/12-d007-rust`; its exact final head is in the handoff on #199.
Earlier incomplete batches described in section 4 are not credited.

- Windows full workspace/all-features tests: **669 passed, 0 failed, 0 ignored**.
  fmt, clippy (all targets/features, `-D warnings`), rustdoc (`-D warnings`)
  and xtask conformance verify passed. The real path-domain adapter compares
  all **604** applicable cases (240 error codes + 237 NUL + 127 prior path/tool
  cases); no Windows case is excluded. The 21-document read-only corpus passes
  its **19** Windows-applicable documents.
- Windows controls: **17/17 KILLED**, all 17 intended unmutated witnesses selected
  and passed, then the restored baseline passed.
- Linux full workspace/all-features tests (including doctests): **662 passed,
  0 failed, 1 ignored**. fmt, strict clippy/rustdoc and xtask conformance verify
  passed. The ignored `recursive_remove_single_failure_reports_the_inner_native_call`
  requires an unprivileged host: it was additionally run explicitly as uid/gid
  1000 with `--exact --ignored --nocapture`, and passed (**1/1**).
- Linux uid-1000 real-provider path corpus: **524 applicable cases**,
  including **160** error-code and **237** NUL cases, with **0** privileged
  exclusions. The **80** Windows-only error-code conditions are explicitly
  excluded on Linux, not credited. The real read-only corpus passed all **9**
  Linux-applicable documents out of the shared 21-document set.
- Standalone CE-02 probe: **41/41 MATCH on Windows and Linux** (13 routing,
  18 recovery, 10 validation), with zero binding-only unfired injections.
  Origins, calls, remaining entries and read-only state match the pinned-Pi
  blobs through the real LocalFileSystem removal seam.
  Windows fires every planned injection. Nine Linux recovery rows have
  unfired Windows-only chmod/stat injections on **both Pi and Rust**; these
  are the shared comparator's explicit NOT_APPLICABLE calls, not missed
  binding coverage. Their result/call/origin/remaining-state comparisons
  still MATCH, and the complete unfired sets also match Pi exactly.
- Linux controls: **10/10 KILLED**, all 10 intended baselines selected and
  passed, followed by a passing restored baseline. Windows-only controls
  are recorded NOT_APPLICABLE on Linux, never counted as kills.
- Shared manifest/schema validation: **921 passed** on the candidate.

The Windows control process completed with exit 0 at 23:49 on 2026-10-11;
its full output and restored-baseline log were checked before crediting it.
The subsequent Linux recipe and controls completed with exit 0, including
the uid-1000 corpora. No overlapped or partial run is credited. The final
shared validation refresh passed after Linux finished.

Local evidence is under `<project>/.tmp/codex-scratch/l12d007/`:
`windows-final-{fmt,clippy,test,doc,xtask,ce02}.log`, `windows-controls/`,
`shared-validation.log`, and `linux-logs/` (full gate logs, CE-02,
uid-1000 corpus logs, `permission-origin-uid1000.log`, and `control-details/`).
The non-root ignored witness uses the full-suite binary from its Cargo log
and a fresh private tmpfs sandbox; it does not reuse earlier fixtures.

Rust L12-D007: **IMPLEMENTED, INDEPENDENT REVIEW PENDING; NOT CERTIFIED**.
Python is approved and merged. Cross-language: **NOT CLOSED**. Independent
exact-pair closure review, merge and status synchronization remain required.

## 7. Rust closure review 1 remediation

Claude's independent review of `a2fa8333` / `aba1664d` was CHANGES REQUESTED
on [#199 comment 6111409107](https://github.com/EGAILab/minion-agent/issues/199#issuecomment-6111409107).
Section 6 is the historical candidate-1 evidence, not approval or evidence for
this changed candidate. R001/R002/R003 each survived one Rust review; none has
survived two reviews, no successor Rust finding on this root has accumulated,
and there is one rejected complete Rust review. Ordinary targeted remediation
is appropriate; the shared CE-02 agreement and exclusions are unchanged.

### R001: raw Windows directory/reparse classification

`delete_entry` now reads raw FILE_ATTRIBUTE_DIRECTORY / REPARSE_POINT from the
opened no-follow handle's metadata. It does not infer those bits from std's
`is_dir` / `is_symlink` view, which hides DIRECTORY on name-surrogate links.
This follows pinned libuv `fs__unlink_rmdir`, blob
`f2215bb3082178193d37f8429536bfe7b707dd0d`.
The neighborhood source audit also retains that function's subsequent
`fs__readlink_handle` validation for a directory reparse unlink: the payload
is queried from the same handle, valid symlinks / drive-path junctions /
application execution links are accepted, and unsupported tags are denied.
Rmdir itself does not apply this unlink-only validation. Portable payload
units cover accepted/rejected tags, a volume junction, malformed offset and
application-link string count. No target is followed or changed by validation.

Permanent real-provider probe `directory_link_recovery_matches_pinned_pi`
adds U8/L10 (directory symlink) and U9/L11 (junction) on Windows; Linux runs
U8/L10, with junction rows explicitly inapplicable. The separate matrix and
oracle files in `filesystem/ce02-data/dirlink-*` transcribe the review's
pinned-Pi outputs; no original shared matrix/oracle is changed. These rows
compare every call, origin, remaining entry, read-only state and fired injection.
Both link and its fixed target are positively proven inside the fixture sandbox;
`outside/keep` means outside the removed TREE, not outside the sandbox.
Four Windows controls restore both old std classification predicates and are
each assigned to their own U8/L10/U9/L11 witness. An additional portable control
accepts unsupported reparse tags and must fail the payload witness.

### R002: restore still-governing disappearance evidence

The prior replacement of conditional L12-D005 recovery controls wrongly
dropped four disappearance stages. They are now permanent witnesses through
the real LocalFileSystem removal walk and its existing Operations collaborator:
readdir, first rmdir, final rmdir, and the Windows recovery retry unlink.
At the injected call a concurrent remover actually deletes the contained entry,
then reports ENOENT. Each witness asserts the injection fired, success, exact
call counts and no remaining entries. Only empty directories or a single file
are removed by the injection; it never recursively removes a computed target.
The first three stages execute on both platforms; the recovery-unlink stage
is Windows-only because POSIX does not enter fixWinEPERM. Each has a separate
control returning the missing error at that exact branch; no production
removal-policy change is required. The earlier child-lstat disappearance and
top-level no-force missing-target witness remain in place.

### R003: independent native-package feature hygiene

The native-fs crate explicitly declares Win32_Security, required by CreateFileW.
The new same-handle reparse query also declares System_IO / System_Ioctl locally.
Both platform recipes run `cargo check -p minion-agent-native-fs` independently;
a workspace check cannot substitute for it. The disposable-copy known-bad
check without Win32_Security fails with E0425 (CreateFileW unavailable), while
the corrected package check passes. This is build evidence, not a semantic kill.

### Development disclosure

The first focused Windows run passed both symlink rows and all disappearance
witnesses but junction creation failed before the provider: `mklink` parsed
forward slashes in the fixture path as a switch. The fixture now passes proven
Windows-separator paths. The failure was investigated and preserved; it is
not credited as a witness or negative-control kill. The corrected focused run
passed all nine selected removal tests. All historical logs were copied to
`history-a2fa8333/` before new evidence replaced the active log paths.

Fresh final-head gates and intended-witness controls will be recorded here
before handoff. Rust remains NOT CERTIFIED; findings require Claude's targeted
independent closure review at the new exact pair.

The first full Windows remediation batch at `5c676db0` stopped at strict
clippy's `items_after_test_module` lint, before its tests: the new payload test
module preceded `clear_readonly_entry`. Tests were moved to a separate
`native-fs/src/tests.rs` module declared after production items. The failed
log is retained and not credited; the complete batch restarts at `cc742fbe`.
An interim 25-control run at `caf5725` completed with all intended kills and
a restored green baseline; its logs are preserved, but the final-head run
also includes the payload control and is the handoff evidence.
