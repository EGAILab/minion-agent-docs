# L12-D005 Rust implementation candidate — readonly directory removal

Status: implementation candidate; independent Rust closure review pending. Not certified.
Coordination: `minion-agent#188`. Provenance: Owner decisions on `#126`, comments
`6086596348` and `6087116283` (the latter supersedes the original rimraf premise).

## 1. Accepted inputs and authority

- Code baseline: `4efa52ff7c17033d4059edbc24a5979630d548e3`.
- Docs baseline: `4ce6aa65d3855cf8b5dea6c55d23691521a745f4`.
- Shared contract: `spec/execution.md` §§14.8 and 17; the approved 21-document
  `conformance/agent/fs-remove-readonly/` corpus. Python approval: issue comment `6090261622`.
- Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`, real
  `NodeExecutionEnv.remove` → `fs.promises.rm`; Node `22.15.1`, libuv `1.49.2`.
- Adopted libuv `fs__unlink_rmdir` (`src/win/fs.c`, blob
  `f2215bb3082178193d37f8429536bfe7b707dd0d`) addresses the entry without following a
  reparse point and ignores its readonly attribute. Attribute correction is a binding
  mechanism, not a normative chmod requirement. Python is not the Rust oracle.

## 2. Implementation and scope

`execution/filesystem.rs` retains the existing delete-first recursive walk and failing-call
path mapping. A Windows permission-denied directory deletion opens the addressed entry for
READ/WRITE_ATTRIBUTES with OPEN_REPARSE_POINT and BACKUP_SEMANTICS. If its own readonly bit
is set, it clears only that bit and retries the deletion once. No readonly bit, failure to
open/query/update, or an unrelated error preserves the original deletion error. A failed
retry supplies its own error and addressed-entry origin. A vanished entry during correction
or retry succeeds. Recursive enumeration/child deletion accepts a concurrently vanished entry
on every platform, as §17 rule 5 requires. A missing top-level target without force still fails;
POSIX permission semantics remain unchanged. The original Windows-only disappearance claim
was incorrect and is corrected by closure-review remediation R001 (§7).

The narrow `minion-agent-native-fs` crate holds the unsafe native buffer calls, leaving
`minion-agent`'s `forbid(unsafe_code)` unchanged. A standard Rust `File` owns the handle and
closes it on every return/unwind path; `OpenOptions` retains the existing Windows NUL and
long-path handling. Zero FileBasicInfo time fields leave timestamps unchanged. Other
attributes are preserved.

**Self-found neighbor:** the real corpus exposed that a Windows directory symlink was
previously sent to `remove_file` and refused with `permission_denied`. No-follow metadata now
selects directory deletion for that directory reparse entry, without traversing it. The
canonical external-readonly-directory case proves the target and its attributes survive.
This implements §17 rule 3, not a new contract rule. File deletion is otherwise unchanged.

No Python or shared semantic contract edits. ACL/sharing error mapping, cancellation,
non-recursive ordinary directory behavior (#125), and POSIX permissions stay unchanged.
Other excluded Layer-12 findings are not remediated or certified by this candidate.

## 3. Permanent evidence

- `tests/fs_remove_readonly_conformance.rs`: fixture-only native adapter; invokes real
  `LocalFileSystem.remove` once per applicable document and compares the result, failing path,
  surviving entries and external target state. ACLs/attributes are restored for cleanup.
  Windows: 19 applicable documents. Linux: 9; the permission-denied case requires uid 1000,
  so the Linux recipe runs the corpus both in the full suite and as that unprivileged uid.
- `src/execution/filesystem/readonly_tests.rs`: portable controlled-operation witnesses for
  distinct retry-error/path, unchanged original on failed/absent correction, exactly one retry,
  and synchronized disappearance during correction/retry. On Windows the successful correction
  uses the actual native attribute binding, not a simulated attribute change.
- Windows binding witnesses: real target/tree removal, no-follow external readonly directory
  target, >260-character directory path, and unchanged non-recursive readonly-directory refusal.
- No timed sleeps or assertion retries.

## 4. Intended-witness controls

`scripts/readonly-remove-negative-controls.py` mutates only an explicitly disposable control
tree, restores every source in `finally`, and first proves each intended baseline is selected
and passing. A kill requires the exact witness FAILED, a semantic panic with its expected
signature, one failed test, and Cargo test exit 101. Compilation/infrastructure failures and
unselected witnesses are INVALID. After restoring the sources the runner invalidates only
the small native-helper package's regenerable Cargo artifacts, rebuilds, and requires every
intended witness to pass again. This leaves the single shared platform target in a verified
unmutated state.

| Control | Intended witness | Discriminator |
|---|---|---|
| no-directory-correction | distinct retry-error origin | permission_denied instead of not_directory |
| retry-keeps-first-error | distinct retry-error origin | same code distinction |
| correction-error-replaces-original | correction failure | message no longer names first delete |
| vanished-correction-is-error | concurrent disappearance | real recursive seam returns Err |
| vanished-retry-keeps-original | concurrent disappearance | disappeared retry incorrectly returns the original permission error |
| retry-twice | retry bound | 3 attempts rather than 2 |
| restore-directory-failure (Windows) | real target/tree removal | readonly directory remains / remove returns Err |
| follow-reparse-target (Windows) | external-target protection | correction follows and changes target |

Self-found control equivalence: merely returning the retry's NotFound from the inner helper
survives, correctly, because the outer recursive seam also accepts NotFound (originally
Windows-only, corrected to every platform in §7). That is
not a killed control and is not counted. The revised control preserves the original permission
error on that disappeared retry, which changes the actual recursive result and is discriminated
by the permanent disappearance witness. No production correction was needed.

Self-found cache hazard: a control's native-helper artifact was reused across the scratch and
candidate worktrees after source restoration, making the first full Windows run fail the
no-follow witness. Cleaning only `minion-agent-native-fs` and rerunning the unchanged exact
witness passed. The product source was correct; this was compiled-mutant contamination in
the shared Cargo target. That failed batch is not a passing gate. The restoration proof above
was added to the runner; fresh isolated complete gates replace the affected batch.

## 5. Fresh gates and reproducibility

Frozen code candidate: `5f6b0e712266c00e6768d85f5f233f7946a94bea`.

Windows G3: **648 passed, 0 failed, 0 ignored** (including 4 doctests). Formatting,
strict all-target/all-feature clippy, warning-strict rustdoc and xtask conformance verification
passed. The existing MSVC linker LNK4098 warning remains; clippy and rustdoc gates are green.
The real readonly corpus executes 19 applicable documents. All 8 intended-witness controls
were killed, with selected green baselines and the final restored 8-test baseline green.
The fresh pinned-Pi/Node Windows replay has 19 rows identical to the committed oracle after
JSON parsing (checkout CRLF vs generated LF is not claimed as raw-byte identity).

Linux G3: **644 passed, 0 failed, 1 ignored** (including 4 doctests). The ignored
pre-existing `recursive_remove_single_failure_reports_the_inner_native_call` permission
witness was then run explicitly as uid/gid 1000 and **passed (1/0)**. Formatting,
strict all-target/all-feature clippy, warning-strict rustdoc and xtask verification passed.
The readonly corpus passed all **9 applicable documents as uid/gid 1000**, including empty
mode-0555 directory success and the nonempty-directory child permission-error origin.
All **6 portable controls** were killed at their intended witnesses; every selected baseline
passed and the final restored **4-test** baseline passed. The 2 Windows-native controls are
Windows-only, not represented as Linux executions.

The Linux image is `rust:1.97.1-trixie`, pinned by RepoDigest
`rust@sha256:b1b3c9c0d921d7fa0a6d1f9ec7e4eab87f8c8ec97644c3d791450f131dec813f`.
Both platforms used Rust 1.97.1 and Node 22.15.1 with the certified ICU4C 78.3 environment.
Fresh logs are retained under `.tmp/l12d005-rust/logs-windows`,
`controls-windows-restored`, and `logs-linux-final` (including the Linux controls and
unprivileged corpus). The extra non-root origin witness log is `posix-origin-unprivileged.log`.

Shared schema and manifest validation: **885 passed** in a final sequential Windows batch
using the candidate's unchanged Python source, pinned ICU environment, and
`pytest tests/conformance/test_schema_validation.py tests/conformance/test_manifest_validation.py
-q -o addopts=''`. This is schema/traceability validation, not a new Python implementation pass.

The first Linux attempt was stopped before completion when another full Python gate batch
was discovered on the host. Only the Codex container was stopped. That load-overlapped attempt
is discarded under section 9.8; it is not credited as a gate result.

Storage: all host temp/cache/targets/logs/worktrees are under the project root on E:.
Dot-source `.agents/project-environment.ps1` in each shell. Windows uses Rust/Cargo 1.97.1,
the pinned ICU4C 78.3 library/bin/identity, Node 22.15.1 and official pinned search artifacts.
Set `RUST_ICU_MAJOR_VERSION_NUMBER=78`, `RUSTFLAGS=-L native=<project>/.toolchain/icu-78.3-src/icu/lib64`,
and `RUSTDOCFLAGS=-D warnings -L native=<same>`. Set the ICU identity and artifact paths as in
prior certified gates. The same shared platform Cargo target is used for controls and gates.

Windows commands, sequentially: `cargo fmt --all -- --check`; `cargo clippy --workspace
--all-targets --all-features -- -D warnings`; `cargo test --workspace --all-features`;
`cargo doc --workspace --no-deps`; `cargo run -p xtask -- conformance verify`.
Run the control script with `--tree <project>/.tmp/l12d005-rust/control-code/minion-agent-rust`
and `--logs <project>/.tmp/l12d005-rust/controls-windows` after copying the candidate and its
compiled Python fixture files (fixtures only, never Python production as oracle).

Linux recipe: committed `minion-agent-rust/scripts/l12d005-linux-gates.sh`, executed in
`rust:1.97.1-trixie`, read-only rootfs, `--tmpfs /tmp:rw,exec,size=16g`; project E: bind mounts:
candidate source read-only at `/source`, Cargo home/target at `/cargo-home` and `/target`,
logs at `/logs`, pinned `.toolchain/icu-78.3-linux` at `/icu`, Node Linux binary at `/node`,
and official search artifact directory at `/search-artifacts`. The script copies the tree to
tmpfs, strips CR from shell scripts, runs G3, executes the readonly corpus as uid/gid 1000,
then runs controls in another disposable tmpfs copy. No Docker named volumes or C: caches.
Windows and Linux batches run sequentially. After the stopped Linux attempt, Claude explicitly
confirmed HOST CLEAR and reserved the host until completion notification. The credited Linux
batch ran in that isolated window. To run the existing ignored origin witness, use the
`fs_path_domain` executable selected by the fresh test log with Docker `--user 1000:1000`,
the same image and ICU environment, tmpfs `/tmp`, and a read-only E:-backed target mount;
pass `--ignored --exact recursive_remove_single_failure_reports_the_inner_native_call --nocapture`.

An exploratory Windows batch was discarded before freezing the final implementation. It is
not credited as G3. Only the fresh frozen-tree results below support this handoff.

## 6. Handoff boundary

Rust implementation is not self-certified. NEXT_OWNER Claude independently reviews the exact
remote candidate pair. Python was merged after its independent final review; cross-language
L12-D005 remains NOT CLOSED until the Rust review and normal merge/status-sync gates complete.

## 7. Closure review 1 and L12D005-R001 remediation

Claude's independent closure review 1 (#188 comment `6091933845`) rejected code
`5f6b0e712266c00e6768d85f5f233f7946a94bea` / docs
`6f5fa99c15a1c293f98e006596014c937a477339`: the recursive-disappearance branches were
Windows-only even though §17 rule 5 applies on all platforms. Rule 6 freezes POSIX
**permission** semantics, not the contrary recursive-disappearance behavior. Pinned Pi's
Linux `entry-vanishes-during-recursive` observation is success. Other implementation
surfaces were accepted subject to this finding. Earlier §5 counts are historical evidence
for the rejected candidate, not credited to this remediation.

The recursive walk now accepts NotFound after the initial target lstat on every platform:
the first rmdir, directory opening/iteration, a child vanishing before its lstat, and
post-removal. Only a walk-child receives the internal missing-entry acceptance; top-level
missing-target handling still requires the caller's `force`. No permission or error-code
mapping changes. Windows own-attribute correction, no-follow behavior, one retry and
original/retry error provenance remain unchanged.

Five portable permanent witnesses use the real `remove_addressed_with` recursive seam.
The private operations seam delegates to actual OS calls by default. Its no-op
`before_child_metadata` hook lets a test unlink the actual child only after real enumeration
and before the production lstat. The read-dir/initial-rmdir/final-rmdir witnesses synchronize
disappearance at each actual call boundary; no sleeps, assertion retries or simulated walk.
The fifth witness uses public `LocalFileSystem.remove` to prove missing targets without
force still fail (recursive and nonrecursive), while force succeeds.

Linux-only controls restore each rejected Windows-only gate independently (child lstat,
read-dir, first rmdir, final rmdir). Each must fail its exact intended portable witness on
Linux. A portable control also wrongly ignores top-level force and must fail its public
missing-target witness. These extend the existing control batch to 9 Windows / 11 Linux
controls, with the same selected-green-baseline and semantic-kill validation.

Fresh remediation gate results and the exact remote pair are recorded below only after
sequential Windows/Linux gates in a host window granted by Claude. Rust certification and
R001 closure remain the independent reviewer's decision.

Remediation code: `e28dfe951e5fc35b1f8627d2d1d3e71f9966c8cd` (parent is the rejected
`5f6b0e712266c00e6768d85f5f233f7946a94bea`). Only the Rust removal implementation,
private test seam/witnesses and control script changed. No Python, shared contract or
canonical expectation changes.

Fresh Windows G3: **653 passed, 0 failed, 0 ignored**, including 4 doctests.
Formatting, strict all-target/all-feature clippy, warning-strict rustdoc and xtask
conformance verification passed. The real readonly corpus passed all 19 applicable
documents. All **9/9 controls** were killed by their intended witnesses; each selected
baseline passed, and the final restored compiled baseline passed **13/13** tests.
The pre-existing MSVC LNK4098 warning remains; it is not a new product diagnostic.
Fresh logs: `.tmp/l12d005-rust/r001/windows/` (including `controls/`).

Fresh Linux G3: **649 passed, 0 failed, 1 ignored**, including 4 doctests.
The pre-existing ignored permission/origin witness
`recursive_remove_single_failure_reports_the_inner_native_call` then passed explicitly
as uid/gid 1000 (**1 passed, 0 failed**) using the executable from this fresh G3 log.
Formatting, strict all-target/all-feature clippy, warning-strict rustdoc and xtask
conformance verification passed. The readonly corpus passed all **9 applicable documents
as uid/gid 1000**. All **11/11 controls** were killed at their intended witnesses;
the 11 selected baselines were green and the final restored compiled baseline passed
**9/9** tests. In particular, restoring any of the four Windows-only disappearance
gates produces the expected semantic failure on Linux, not a compile/infrastructure error.
Fresh logs: `.tmp/l12d005-rust/r001/linux/`, including `controls/`,
`corpus-unprivileged.log` and `posix-origin-unprivileged.log`.

Both batches used Rust 1.97.1, Node 22.15.1 and verified ICU4C 78.3. The existing
Linux recipe and exact image digest in section 5 were reused; source and control copies
were in tmpfs, with E:-backed Cargo home/target and logs. No named volume or C: cache.
Windows and Linux G3/controls ran sequentially in the host window explicitly granted
by Claude. All Codex gate processes/containers finished before the host-release notice.
No exploratory or failing batch is substituted for these fresh results. Schema,
manifest and corpus files are unchanged by this remediation; section 5's 885 shared
validation passes remain historical evidence, not newly rerun results.

R001 is **remediated in the candidate, not self-closed**. The paired PRs return to
Claude for independent exact-SHA closure review. Rust remains **NOT CERTIFIED** and
cross-language L12-D005 remains **NOT CLOSED** pending that review and normal integration.
