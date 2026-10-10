# Convergence episode `CE-L12D007-02`: recursive child classification, unlink/rmdir routing and error propagation

Coordination: `minion-agent#199` (L12-D007). Entered by Codex under trigger B, in targeted re-review issuecomment-6102913331, at code `b8062daa` / docs `a6e40c39`.

The surface has now produced three findings:
- author `L12D007-PY-I001`: rmdir-first;
- reviewer `L12D007-I002`: the cached child type;
- reviewer `L12D007-I003`: the child error swallowed and retried.

`CE-L12D007-01` (containment) is settled and untouched. The approved §19 contract is **not** reopened: every rule below is retained pinned-Pi behavior already required by §19 / §14.8.

## Revision 1: characterization and checkpoint proposal (Claude)

### OPEN FINDINGS

- **`L12D007-I003`** (high, PI_PARITY_DEFECT). `_rimraf_child` places `os.lstat(path)` AND the directory branch's `_rimraf(path)` in the same `lstat` exception handler.
  - A removal error from a positively identified directory is taken for a failed `lstat` and falls through to `unlink`. An `unlink` that then meets the directory calls `_rimraf` a second time.
  - So a failing child removal can become a successful destructive operation.

### ROOT-CAUSE SURFACE

How one child of a recursive removal is classified, which native call follows which failure, and which error, if any, leaves the walk. This covers both the walk's own rmdir / readdir and everything nested beneath a child.

### PI SYMBOLS / TESTS AUDITED

- Node v22.15.1 `lib/internal/fs/rimraf.js`, blob `24bf3f46` (re-fetched; hash verified): `rimraf` (the ENOENT → success wrapper), `_rimraf`, `fixWinEPERM`, `_rmdir`, `_rmchildren`.
- Node's `rm` / `fs.promises.rm` (validate, then `rimraf`) and Pi `NodeExecutionEnv.remove` → `fs.rm`, at pinned Pi `b7bb00b` (clean).
- libuv 1.49.2 `src/win/error.c` (blob `7abf906b`): the errno each injected Win32 code becomes.

### OBSERVABLE RULES (proposed; each is pinned Node's, not a new contract rule)

- **R1. Child classification.**
  - `lstat(child)` alone decides: a directory goes to `_rmdir(child, null)`; anything else goes to `unlink(child)`. Libuv's `lstat` reports a junction as a link.
  - `lstat` failing ENOENT counts as removed.
  - Any other `lstat` failure goes on to `unlink(child)`. On Windows, an `lstat` EPERM goes to `fixWinEPERM(child, lstatErr)`.
  - **The directory branch's outcome is the child's outcome.** It is never re-routed through the `lstat`-failure or `unlink` path. This is `I003`.
- **R2. `unlink(child)` failure routing.**
  - ENOENT counts as removed.
  - EISDIR goes to `_rmdir(child, unlinkErr)`.
  - EPERM goes to `fixWinEPERM` on Windows, and to `_rmdir(child, unlinkErr)` on POSIX.
  - Anything else is the child's error, with no other call made.
- **R3. `_rmdir(dir, originalErr)`.**
  - `rmdir(dir)` ENOTEMPTY / EEXIST / EPERM goes to `_rmchildren(dir)`.
  - ENOTDIR gives `originalErr` (none means success).
  - Any other error is the result, with no listing and no retry. ENOENT counts as removed.
- **R4. `_rmchildren(dir)`.**
  - A `readdir(dir)` failure is the result.
  - Each child goes through R1. **The first child error is the result, propagated unchanged from any depth.** The failing call's own error and path are not re-attempted, wrapped, or replaced by an ancestor's later call.
  - Only after every child succeeds: `rmdir(dir)`, whose error (ENOENT counts as removed) is the result.
- **R5. Error identity.** The reported code and path are those of the failing native call (`CE-L12-D001-01`; §14.8). No call is retried except `fixWinEPERM`'s single certified retry (L12-D005).

### BEHAVIOR MATRIX (pinned Pi, measured)

The matrix is `data/l12-d007/ce02/ce02-matrix.json`, and the probe is `ce02-pi-probe.mjs`. It runs pinned Pi's real `NodeExecutionEnv.remove('tree', {recursive: true})` with ONE injected failure of one native call; every other call is real.

The rows below are pinned Pi's results on both Windows (`ce02-pi-win32.jsonl`) and Linux (`ce02-pi-linux.jsonl`, uid 1000). Call counts are per path.

| Row | Injection | Pi result (path) | Pi calls that matter | Remains |
|---|---|---|---|---|
| C0 | none (tree: child/f, g) | ok | each directory rmdir ×2; each file unlink ×1 | nothing |
| E1 | rmdir(child) #1 EIO | unknown (`tree/child`) | rmdir child ×1; no unlink of child | tree, child |
| E2 | unlink(child/f) #1 EIO | unknown (`tree/child/f`) | unlink f ×1; rmdir child ×1 | all |
| E3 | readdir(child) #1 EACCES | permission_denied (`tree/child`) | readdir child ×1; rmdir child ×1 | all |
| E4 | rmdir(child) #2 EIO | unknown (`tree/child`) | rmdir child ×2 | tree, child |
| E5 | rmdir(child) #1 EBUSY | unknown (`tree/child`) | rmdir child ×1; no readdir of child | all |
| E6 | unlink(child file) #1 EBUSY | unknown (`tree/child`) | unlink ×1; no rmdir of child | all |
| E7 | lstat(child file) #1 EIO | ok | goes on to unlink ×1 | nothing |
| E8 | lstat(child file) #1 ENOENT | unknown (`tree`): the final rmdir's ENOTEMPTY | no unlink of child | tree, child |
| E9 | lstat(child dir) #1 EIO | ok | unlink child ×1, then rmdir child ×1 (Windows via `fixWinEPERM`: chmod, stat) | nothing |
| E10 | unlink(child/sub/f) #1 EIO | unknown (`tree/child/sub/f`) | every ancestor rmdir ×1 only | all |
| E11 | unlink(child file) #1 EPERM | **Linux:** permission_denied (`tree/child`) via rmdir ENOTDIR → original. **Windows:** ok (`fixWinEPERM` retried the unlink) | see O001 | Linux: all; Windows: nothing |
| E12 | rmdir(child/sub) #1 EIO | unknown (`tree/child/sub`) | rmdir sub ×1; child ×1 | all |

### MINIMAL EXECUTABLE WITNESSES

- **Cross-implementation acceptance** (characterization, both platforms): `ce02_py_probe.py` runs the same matrix through the Python candidate's real `LocalFileSystem.remove`. It injects at the calls the walk makes: `os.lstat`, `os.stat`, `os.scandir`, `_node_rmdir`, and the unlink seam (Windows `_libuv_unlink`, POSIX `os.unlink`).
  - `ce02_compare.py <pi> <py>` compares result, path, remains, and per-path rmdir / unlink / readdir / child-`lstat` counts. It ignores the top-level `lstat tree` (Node's own validation) and `stat` / `chmod` (fixWinEPERM mechanics).
  - **Acceptance:** every row MATCHes on Linux and on Windows, except `E11` on Windows (O001).
  - Linux runs through `run-linux-ce02.sh` (both probes, uid 1000, private tmpfs, guard-proven read-only mounts).
- **Permanent Python witnesses** (code repo, `tests/execution/test_filesystem_rimraf.py`), through the real `LocalFileSystem.remove` with the same single-call injection:
  - one parametrized witness per row, C0 and E1 to E10 and E12, asserting Pi's result, path, remains, and the counts of the row's decisive calls;
  - `E11` on POSIX only.

### NEGATIVE CONTROLS (each must be killed by its intended witness)

- **N1, broad catch (the `I003` defect):** the `lstat` handler again encloses the directory branch. Killed by E1, E2, E3, E4, E5, E10 and E12.
- **N2, retry the child's rmdir once on failure:** killed by E1 (rmdir count 2, result ok).
- **N3, swallow a child error and continue to the next sibling / final rmdir:** killed by E2 and E10 (wrong result and path).
- **N4, report the ancestor instead of the failing entry** (a failure re-labelled with the child's path): killed by E2 and E10 (path).
- **N5, list before rmdir:** killed by E5 (readdir of child ×1 where Pi has 0) and by the existing empty-unlistable witness.

### CURRENT CANDIDATE FAILURES (code `b8062daa`)

`ce02-py-candidate-b8062daa-{win32,linux}.jsonl` compared with Pi:

- **DIFF on both platforms:** E1, E2, E3, E4, E5, E10, E12. In each, the injected error is swallowed, the child is unlinked or re-walked, the removal reports **ok**, and the tree is gone. This is `I003`, broader than the reviewer's single row.
- **MATCH:** C0, E6, E7, E8, E9; and E11 on Linux.
- **DIFF on Windows only:** E11 (O001, below).

### SPEC / MANIFEST / CONFORMANCE DELTAS

None. R1 to R5 are already pinned Node's behavior under §19 (literal `toFileError` per failing call) and §14.8 (failing-call origin). The record gains §13; the manifest line is unchanged. No canonical case is added: the matrix needs single-call fault injection, which the language-neutral fixture vocabulary does not have, so it stays implementation-level evidence with a pinned-Pi oracle in both languages.

### IMPLEMENTATION CONSTRAINTS

- `_rimraf_child`: catch `lstat` failures around `lstat` ONLY, then dispatch outside that handler:
  - a directory (not a junction) goes to `_rimraf(path)`, whose error propagates unchanged;
  - otherwise R2.
- Kept: R2's unlink-meets-directory routing with `originalErr`, no-follow behavior, vanished-entry acceptance, rmdir-first, the sequential order, and L12-D005's certified retry.
- No new retries, no parallel removal; #127 is untouched.
- Rust implements R1 to R5 natively (`remove_dir_all` would violate R3/R4). The rules use no language-specific extension point.

### OUT-OF-SCOPE / DEFERRED BEHAVIOR

- **O001 (observation, Windows):** a ONE-SHOT `unlink` EPERM on a file with no read-only attribute (E11).
  - Pi's `fixWinEPERM` always chmods, stats and retries the unlink once, so it succeeds when the cause was transient.
  - Certified L12-D005 retries only when the entry's own read-only attribute was set and cleared ("No retry when the attribute was not set", `12-l12-d005-readonly-remove.md` §implementation). Under a persistent cause (the ACL denials L12-D005 characterized) both give `permission_denied`.
  - The same rule governs a non-recursive file `remove` (Node's `rm` is `rimraf` there too).
  - Changing it would reopen certified L12-D005 behavior. That is not within this episode; it is proposed as a separate follow-up for Owner governance, and is recorded here so it is not rediscovered as a successor finding.
- Concurrent child removal and first-settled-failure selection: #127 / DIV-008, unchanged.
- Top-level `lstat` and validation (Node's `rm` checks the target first): unchanged and not compared.

## CONVERGENCE CHECKPOINT

**PROPOSED FOR IMPLEMENTATION** (revision 1, Claude)

- **OPEN FINDINGS:** `L12D007-I003`.
- **ACCEPTANCE WITNESSES:**
  - `data/l12-d007/ce02/` matrix: `ce02_compare.py` all MATCH on Linux, and on Windows except E11 (O001);
  - the permanent per-row witnesses in `tests/execution/test_filesystem_rimraf.py`;
  - negative controls N1 to N5, each killed by its named rows.
- **NORMATIVE DELTAS:** none (record §13 only).
- **NEXT_OWNER:** Codex, for the checkpoint review of exactly this proposal.
