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
or retry succeeds. Windows recursive enumeration/child deletion also accepts a concurrently
vanished entry. These new disappearance branches are Windows-only; POSIX behavior is retained.

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
unselected witnesses are INVALID.

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
survives, correctly, because the outer Windows recursive seam also accepts NotFound. That is
not a killed control and is not counted. The revised control preserves the original permission
error on that disappeared retry, which changes the actual recursive result and is discriminated
by the permanent disappearance witness. No production correction was needed.

## 5. Fresh gates and reproducibility

Gate results are recorded below after the frozen candidate's batches complete.

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
Windows and Linux batches run sequentially.

An exploratory Windows batch was discarded before freezing the final implementation. It is
not credited as G3. Only the fresh frozen-tree results below support this handoff.

## 6. Handoff boundary

Rust implementation is not self-certified. NEXT_OWNER Claude independently reviews the exact
remote candidate pair. Python was merged after its independent final review; cross-language
L12-D005 remains NOT CLOSED until the Rust review and normal merge/status-sync gates complete.
