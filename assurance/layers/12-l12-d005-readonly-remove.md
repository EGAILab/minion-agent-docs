# L12-D005: Windows `remove` ignores the read-only attribute

Layer 12 post-certification delta. Coordination: minion-agent#188. Provenance: `L12-RM-READONLY-WINDOWS`
(minion-agent#126). Requirement: `EXEC-002`. Normative text: `spec/execution.md` §17.

**Governance.**
- The Owner first authorized adopting pinned Pi's Windows behaviour, then took it to be `rimraf`'s `fixWinEPERM` (#126 issuecomment-6086596348).
- Characterization showed the actual mechanism is libuv's own deletion, which also covers non-recursive remove. Claude returned to the Owner, as that decision required.
- The amended decision (issuecomment-6087116283) adopts pinned Pi's actual rule:
  - read-only files are removable, recursively and non-recursively;
  - read-only-attributed directories are removable when recursive;
  - Python fixes files and directories, and Rust fixes directories only;
  - ACL, sharing and other errors are unchanged;
  - symlink targets are never modified;
  - POSIX is unchanged;
  - non-recursive directory remove stays with #125.

## 1. Authority

| Source | Identity | What it shows |
|---|---|---|
| Pi `NodeExecutionEnv.remove` | `b7bb00b9` `packages/agent/src/harness/env/nodejs.ts:661-668` | `rm(resolved, {recursive, force})`; errors through `toFileError` |
| Node `lib/internal/fs/rimraf.js` | v22.15.1, git blob `24bf3f46b878e711beadcdc8e1b08700d10aa3c5` (extracted from the pinned binary; hash identical to §14.8's citation) | `_rimraf` → `lstat`, `unlink`; `EPERM` → `fixWinEPERM`: `chmod(0o666)`, `stat`, then `unlink` or `_rmdir`; a failed `chmod` or `stat` returns the original error (`ENOENT` → success) |
| libuv `src/win/fs.c` | v1.49.2 (Node's `process.versions.uv`), git blob `f2215bb3082178193d37f8429536bfe7b707dd0d` | `fs__unlink_rmdir`: `CreateFileW(FILE_READ_ATTRIBUTES \| FILE_WRITE_ATTRIBUTES \| DELETE, FILE_FLAG_OPEN_REPARSE_POINT …)`, then `FILE_DISPOSITION_DELETE \| POSIX_SEMANTICS \| IGNORE_READONLY_ATTRIBUTE`; the fallback clears `FILE_ATTRIBUTE_READONLY`, then sets the delete flag. Both `unlink` and `rmdir`. |

**Consequence:**
- On Windows, the read-only attribute never blocks a Node deletion.
- `fixWinEPERM` is reached only for a deletion that still fails, which means a genuine ACL denial. There `chmod` fails, or the retry fails, so `permission_denied` is returned for that entry.
- Every Windows probe call below was instrumented to record each `fs.chmod` call. No read-only case calls `chmod`. Only the ACL-denied cases do.

## 2. Characterization (Windows 11; Node v22.15.1; Python 3.13.5 at `main` `bf39b46d`; Rust 1.97.1 at `bf39b46d`)

The probes are in `data/l12-d005/characterization/`:
- `pi-probe.mjs`: pinned Pi's real `NodeExecutionEnv`;
- `py-probe.py`: the certified `LocalFileSystem`;
- `rust-probe.rs`: a disposable test, run only in a scratch copy and never committed.

Raw outputs sit beside them. In the table, `p_d` is `permission_denied`.

| Case | Pi | Python | Rust |
|---|---|---|---|
| read-only file in a tree (recursive) | ok | `p_d` `t/sub/f` | ok |
| read-only file as target, recursive | ok | `p_d` `f` | ok |
| read-only file as target, **non-recursive** | ok | `p_d` `f` | ok |
| several nested read-only files | ok | `p_d` (first met) | ok |
| read-only *directory* in a tree | ok | `p_d` `t/d` | `p_d` `t/d` |
| read-only directory as target, empty / non-empty (recursive) | ok / ok | `p_d` `d` / `p_d` `d/f` | (not run) |
| read-only directory as target, non-recursive | `unknown` `d` (`ERR_FS_EISDIR`; #125) | `is_directory` | (#125) |
| mixed read-only files and directories | ok | `p_d` `t/x/y` | (not run) |
| read-only symlink itself (link attribute) | ok; target untouched | `p_d` `t/link` | (not run) |
| removing *through* a symlink to a read-only file, non-recursive | ok (link only); target still read-only | ok | (not run) |
| symlink to an external read-only file or directory, in a tree | ok; target untouched | ok; target untouched | (not run) |
| ACL: file deny `DELETE` (+ parent deny `DELETE_CHILD`) | `p_d` `t/f` | same | same |
| ACL: directory deny `DELETE` | `p_d` `t/d` | same | same |
| ACL: target file denied | `p_d` `f` | same | same |
| read-only file + deny `WRITE_ATTRIBUTES` (attribute correction denied) | `p_d` `t/f` (`chmod` attempted) | same | same |
| read-only file + deny `DELETE` (retry denied) | `p_d` `t/f` (`chmod` attempted) | same | same |
| entry vanishes during the recursive walk (controlled `readdir` hook) | ok (hook fired) | Linux: ok (hook fired). Windows: confounded by read-only siblings | (not run) |

**Linux controls** (Docker `python:3.13`, uid 1000, trees on tmpfs; Node v22.15.1 Linux):
- Pi and Python agree on every case.
- Read-only files (mode 0444) are removed.
- Symlink targets are untouched.
- The vanishing entry is treated as removed.
- A mode-0555 subdirectory gives `p_d`, naming `t/sub/f`.

Nothing changes on POSIX.

## 3. Contract

`spec/execution.md` §17 is normative. It covers:
- the rule for files, directories and the symlink itself;
- the unchanged ACL and other semantics, with codes and §14.8 origin paths;
- concurrent disappearance counting as removed;
- POSIX unchanged;
- binding-defined mechanism within limits: no broadening, no change to deletions that already succeed or fail for another reason, and no modification of a link's target.

§14.8's bullet on #126 gains a correction note for its `fixWinEPERM` attribution. The original sentence is kept.

## 4. Canonical evidence

`conformance/agent/fs-remove-readonly/` holds 20 documents, shaped by `fs-remove-readonly-scenario.schema.json`.
- **Fixture ops** (native setup only): `file`, `dir`, `readonly` (Windows attribute; POSIX clears the write bits), `readonly_link`, `symlink`, `deny_delete`, `deny_write_attributes`.
- **Assertions:** the `Result` (code and path components), `expect_left`, and the external targets' existence, read-only state and text.
- **Platforms:** cases shared by both platforms give identical Pi results on Linux and Windows. The generator enforces this.
- **Case split:** 12 cases are Windows-only (attributes and ACLs), and 1 is Linux-only (the mode-0555 control).

**Generation:**
1. `gen/cases.json` holds the case definitions.
2. `gen/pi-oracle.mjs` runs them through pinned Pi, writing `pi-win32.json` and `pi-linux.json`.
3. `gen/gen-canonical.py` turns those outputs into the documents.

**Runner:** the Python runner `tests/conformance/fs_remove_runner.py` prepares the fixture natively, calls the real `LocalFileSystem.remove` once, and observes the result. It restores attributes and ACLs afterwards.

**Contract-stage status in Python on Windows:**
- 10 cases are `xfail(strict=True)`: every read-only file, directory and link case.
- The 8 others already pass: the ACL denials, the attribute-correction and retry denials, the symlink-through cases and the Linux-shared file cases with no read-only attribute involved.
- 1 Linux case is an explicit skip.

**Running as root on POSIX.** Root bypasses permission checks, so the mode-0555 control cannot be observed as root. The test skips it under root with an explicit reason. Its Linux evidence comes from a non-root (uid 1000) run.

**Schema validation tests** cover well-formedness, every document validating, and seven malformed shapes being rejected. That includes `../` path escape, which first slipped through a dot-permitting segment pattern and was fixed.

## 5. Discrimination at the contract stage (`data/l12-d005/controls.py`)

**Recipe:**
1. Copy the contract candidate's `minion-agent-python/`, `conformance/` and manifest to an E: scratch directory.
2. Apply `gen/planned_fix.py` to that copy, and change nothing else.
3. Run `python controls.py <python> <copy>/minion-agent-python <logs>`.

The script passes `--runxfail`, clears `PYTEST_ADDOPTS`, and requires every intended witness to be selected and PASS unmutated (`-rA`). A kill needs exit 1, exactly the intended witnesses failing, and a canonical assertion signature.

**Fresh results** (Windows, Python 3.13.5):
- **Planned correction applied:** baseline `10 intended witnesses selected and PASS`. Every control is **KILLED**:

  | Control | Witnesses |
  |---|---|
  | `top-level-delete-not-retried` | non-recursive and recursive read-only target |
  | `tree-entries-not-retried` | child and nested read-only files |
  | `directories-not-retried` | empty read-only directory target and directory in a tree |
  | `attribute-cleared-on-the-link-target` | the read-only link itself, and the read-only external target staying read-only |
  | `acl-denial-swallowed` | recursive and non-recursive ACL-denied target |

- **Unchanged candidate:** `INVALID baseline` (7 witnesses not green). The recipe cannot report kills against the defective binding.

**A survivor, recorded.** A first control, `attribute-cleared-through-the-link` (`os.chmod` without `follow_symlinks=False`), **survived**. On Windows, `os.chmod` sets the attribute on the link itself either way, so the mutant is observably equivalent. It was replaced by a mutant that clears the attribute on the link's *resolved target*. That is the hazard the Owner named. A new case was also added, `rec-readonly-symlink-to-readonly-external-file`, where both link and target are read-only and the target must stay read-only. The replacement is killed by both witnesses.

## 6. Python implementation plan (after contract approval)

- **Mechanism:**
  - on a `PermissionError` from deleting a file, symlink or directory, check whether the entry's **own** attribute carries `FILE_ATTRIBUTE_READONLY`;
  - if so, clear it without following reparse points, and retry the deletion once;
  - otherwise, or if clearing fails, raise the original error;
  - a retry failure raises the retry's error;
  - `FileNotFoundError` during the correction or retry counts as removed.
- **Where it applies:**
  - the top-level `os.remove` and symlink paths;
  - `shutil.rmtree`'s `onexc` handler, for `unlink`, `remove` and `rmdir`, keeping §14.8's failure-origin naming.
- **Python 3.12 support** (`requires-python >= 3.12`):
  - `os.chmod(…, follow_symlinks=False)` is unavailable on Windows before 3.13;
  - on 3.12 the attribute must be cleared through a handle opened with `FILE_FLAG_OPEN_REPARSE_POINT` (`SetFileInformationByHandle(FileBasicInfo)`), or the equivalent;
  - the witnesses include the link case.
- **Witnesses:**
  - the canonical corpus, with the strict xfails removed;
  - binding witnesses for the concurrent-disappearance race: the vanishing entry during the walk, and vanishing between the failed delete and the attribute correction;
  - regression of §14.8's origin cases and the L12-D001 corpus.

## 7. Rust (implementation by the Rust owner after contract approval)

- **Already conformant:** read-only files, including non-recursive.
- **To fix:** a read-only-attributed directory, in a tree or as the target.
- **Required:**
  - the same canonical corpus driven through Rust's real `remove`;
  - the concurrency witnesses;
  - Rust-side controls, including one restoring the current directory failure.
- **Unchanged:** Linux behaviour, and the non-recursive directory rule (#125).
