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

## Checkpoint review 1 (Codex): REJECTED

#199 issuecomment-6103008491, at docs `559acb9c` / code `b8062daa`.

- **`CE-L12D007-02-C001`** (high, CONTRACT_ASSURANCE_DEFECT). The Windows EPERM recovery stage (`fixWinEPERM`) was missing:
  - its two entry sites (a child `lstat` EPERM and an `unlink` EPERM);
  - chmod/stat success, ENOENT and other failure;
  - original-versus-retry error provenance;
  - file, directory and link outcomes.
  - Reviewer neighbour: `lstat` EPERM followed by a failing recovery gives `permission_denied` under Pi, but **ok** in the candidate, with the child deleted.
- **`CE-L12D007-02-C002`** (medium). O001 cannot be excluded on the strength of the certified L12-D005 mechanism. It needs an explicit Owner disposition.

The reviewer confirmed the I003 core characterization, all 13 rows on both platforms, and the comparator's listed differences.

## Revision 2 (Claude): response to C001 / C002

### Owner disposition of O001 (C002)

**ADOPT PI** (#199 issuecomment-6103080422, verbatim; cross-referenced on #126). It authorizes a targeted correction of L12-D005's certified Windows recovery outcomes in both bindings, as `DIRECT_PI_PARITY`.

O001 is therefore no longer out of scope: E11 is an acceptance row on both platforms. §17's other rules stand, in particular that a link target is never changed. Pinned Pi was measured to keep that rule (rows L9, U7 below).

### Recovery-stage characterization (C001)

`ce02-recovery-matrix.json`, 18 rows. Pinned Pi's real `NodeExecutionEnv.remove` runs with one or more injected failures (`ce02-recovery-pi-probe.mjs`), and every entry left read-only is recorded.

| Row | Entry and stage | Pi on Windows (`ce02-recovery-pi-win32.jsonl`) |
|---|---|---|
| L1 / L2 | child `lstat` EPERM; recovery succeeds (file / directory) | ok; chmod, stat, then unlink / rmdir ×1 |
| L3 | `lstat` EPERM, chmod EIO | `permission_denied` at the child (the **original** error); no unlink; child remains |
| L4 | `lstat` EPERM, chmod ENOENT | the child counts as removed, so the tree's final rmdir ENOTEMPTY gives `unknown` at `tree` |
| L5 | `lstat` EPERM, stat EIO | `permission_denied` (original); no unlink |
| L6 | `lstat` EPERM, stat ENOENT | as L4 |
| L7 | `lstat` EPERM, the retry unlink EIO | `unknown` at the child (the **retry's** error) |
| L8 | `lstat` EPERM on a directory, rmdir EIO | `unknown` at the child |
| L9 | `lstat` EPERM on a file link to a read-only outside target | ok; the link is removed; **the target stays read-only** |
| U1 (= E11) | `unlink` EPERM once | ok; chmod, stat, unlink ×2 |
| U2 | `unlink` EPERM, chmod EIO | `permission_denied` (original) |
| U3 | `unlink` EPERM, stat ENOENT | as L4 |
| U4 | `unlink` EPERM, then the retry EIO | `unknown` (retry's error) |
| U5 | `unlink` EPERM twice (persistent) | `permission_denied` (retry's error) |
| U6 | a real read-only file, no injection | ok, with no recovery at all (libuv ignores the attribute) |
| U7 | `unlink` EPERM on a link to a read-only outside target | ok; **the target stays read-only** |
| T1 | single-file `remove` (not recursive), `unlink` EPERM once | ok (the same recovery at top level) |
| T2 | T1 with chmod EIO | `permission_denied` (original) |

On **Linux** (`ce02-recovery-pi-linux.jsonl`, uid 1000) there is no recovery stage:
- an `lstat` EPERM goes on to `unlink`;
- an `unlink` EPERM goes to `_rmdir`, where ENOTDIR gives the original error. T1 and T2 make that `rmdir` too.

The revision 1 Linux Pi matrix replayed byte-identical.

**Candidate `b8062daa`:**
- Windows: 12 DIFF rows. The outcome differences are L3 to L6 (the `lstat` EPERM entry skips recovery) and U1, U4, U7, T1 (L12-D005's conditional retry). L2, L8, U3 and U5 differ in calls only.
- Linux: matches every outcome. T1 and T2 differ only by Pi's extra top-level `rmdir`: the top-level non-directory does not share the child routing.

### Revised OBSERVABLE RULES

These are normative §19.5 in docs (proposed), and they supersede R1 to R5 above.

- **R1 (revised).** Classification applies to **every entry, the `remove` target included** (Node's `rm` is `rimraf` for any target).
  - The entry's own `lstat`, now, decides.
  - ENOENT: removed. Windows EPERM: R6 recovery (original = the `lstat` error). Other failures: unlink (R2).
  - A directory's outcome is the entry's outcome (`I003`).
- **R2 (revised).** An unlink failure:
  - ENOENT: removed;
  - EISDIR, or EPERM on POSIX: `_rmdir` with the original error;
  - Windows EPERM: R6;
  - else: that failure.
- **R3, R4:** unchanged (rmdir-first; ENOTDIR gives the original error; first-failure propagation, sequential; #127 untouched).
- **R5 (revised).** Each failure reports its failing call's code and §14.8 origin, except where R3 / R6 return the **original** error.
- **R6 (new), Windows recovery:**
  - **a.** Clear the entry's own read-only attribute without following links. This is a success whether or not the attribute was set. Its failure gives ENOENT → removed, else the original error.
  - **b.** Inspect the entry, following links. ENOENT → removed; any other failure → the original error.
  - **c.** A directory goes to `_rmdir` with the original error. Otherwise **one** more unlink, whose own failure is the result (ENOENT → removed).
  - A link target's attributes are never changed (§17 rule 3).

### MINIMAL EXECUTABLE WITNESSES (revised)

- **Acceptance:** `ce02_compare.py` reports **all MATCH** for both matrices on both platforms, with **no expected differences**. That covers E11/U1 and T1/T2's top-level routing.
  - The comparator now also compares `readonly` where a row records it, so a changed link target is a DIFF.
- **Permanent binding witnesses** (`tests/execution/test_filesystem_rimraf.py`, real `LocalFileSystem.remove`, the same injection seams):
  - the rows C0, E1 to E12, L1 to L9, U1 to U7, T1 and T2;
  - the platform-specific ones are skipped on the other platform.
- **The L12-D005 canonical corpus** (`conformance/agent/fs-remove-readonly`, 21 documents) must still pass unchanged. Its cases are persistent conditions, so R6 yields the same outcomes.

### NEGATIVE CONTROLS (revised: revision 1's N1 to N5 stand)

| Control | Mutation | Killed by |
|---|---|---|
| N6 | Windows `lstat` EPERM routed straight to unlink (no recovery) | L3, L5 |
| N7 | a recovery chmod/stat failure returns its own error, not the original | L3, L5, U2, T2 |
| N8 | retry only when a read-only attribute was set (L12-D005's conditional retry) | U1, U4, T1 |
| N9 | the retry failure replaced by the original error | L7, U4 |
| N10 | the attribute correction follows links (changes the target) | L9, U7 (`readonly`) |
| N11 | the top-level non-directory bypasses the shared routing | T1, T2 on Linux (the `rmdir` call) |

### SPEC / MANIFEST / CONFORMANCE DELTAS (revised)

- `spec/execution.md` **§19.5** (new; proposed): rules 1 to 6 as above, with the Owner decision.
- **§17:** a correction note under the disproven "genuine ACL denial" premise. The original sentence is kept.
- **Manifest:** `fs_error_codes_pinned_pi_literal` will cite §19.5 at implementation. The L12-D005 entry gains a pointer.
- **Canonical:** none added. Fault injection has no language-neutral fixture, so the evidence is binding-level with a pinned-Pi oracle per language. The `fs-remove-readonly` corpus is unchanged and re-run.

### IMPLEMENTATION CONSTRAINTS (revised)

- One routing serves the `remove` target and every child: catch `lstat` failures around `lstat` only, then dispatch outside that handler.
- R6 replaces L12-D005's conditional retry on Windows, keeping its link-safety:
  - the own-attribute correction never follows links and is a no-op success when the attribute is not set;
  - the inspection follows links;
  - there is one retry.
- No additional retries, no parallel removal, #127 untouched. POSIX gains no recovery stage.
- **Rust** implements R1 to R6 natively (`remove_dir_all` violates R3/R4). No language-specific extension point is involved. The rules are outcome rules; the evidence is the shared matrices.

### OUT-OF-SCOPE / DEFERRED (revised)

- O001 is now adopted (above).
- Concurrent child removal and first-settled-failure selection: #127 / DIV-008.
- The top-level validation `lstat` count is not compared.

## CONVERGENCE CHECKPOINT (revision 2)

**PROPOSED FOR IMPLEMENTATION** (revision 2, Claude)

- **OPEN FINDINGS:** `L12D007-I003`, `CE-L12D007-02-C001`, `CE-L12D007-02-C002`. C002 has the Owner's disposition recorded.
- **ACCEPTANCE WITNESSES:**
  - both matrices all MATCH on Windows and Linux, with no exceptions;
  - the permanent per-row witnesses;
  - controls N1 to N11 each killed by their named rows;
  - the `fs-remove-readonly` corpus unchanged and passing.
- **NORMATIVE DELTAS:** spec §19.5 (new), the §17 correction note, manifest pointers at implementation.
- **NEXT_OWNER:** Codex, for checkpoint review 2 of exactly this proposal.

## Checkpoint review 2 (Codex): REJECTED

#199 issuecomment-6103179882, at docs `9b9aef6f` / code `b8062daa`.

- **Accepted:** C002's governance (the Owner's ADOPT PI), and C001's recovery-stage characterization (R6, the 18 rows, L9/U7 link-target safety). N1 to N11 are appropriate *planned* controls.
- **`CE-L12D007-02-C003`** (high, CONTRACT_ASSURANCE_DEFECT). Initial target validation was conflated with `rimraf` classification.
  - Node's `rm` first runs `validateRmOptions`. Its target `lstat` failure is returned as is, except force + ENOENT.
  - Only after that does `rimraf`'s own classification `lstat` (with recovery) run.
  - The reviewer's witness: a non-recursive file whose first `lstat` gives EPERM is `permission_denied` with no recovery under Pi. A blanket target R1 would recover and succeed.
- **Implementation-evidence reminder:** the Python recovery probe had no adapter for the own-attribute correction stage, so its chmod injections never fired. Re-running it after implementation could not have shown L3/L4/U2/T2 as all-MATCH.

## Revision 3 (Claude): response to C003 and the evidence reminder

### Source

Node v22.15.1, re-fetched and hashed:
- `lib/internal/fs/promises.js` (blob `ebf9f379`): `rm` awaits `validateRmOptionsPromise`, then `lazyRimRaf()(path, options)`.
- `lib/internal/fs/utils.js` (blob `95cb4fc8`): `validateRmOptions`:
  - `lstat(path)` failing: `force` && ENOENT → proceed; else `cb(err)`;
  - a directory && !recursive → `ERR_FS_EISDIR`;
  - else proceed.

### Validation-stage characterization (`ce02-validation-matrix.json`, 10 rows)

`lstat #1` is the target validation; `lstat #2` is `rimraf`'s classification.

| Row | Case | Pi, Windows and Linux (identical results) |
|---|---|---|
| V1 | file, not recursive, validation `lstat` EPERM | `permission_denied`; `lstat` ×1 only; the file remains |
| V2 | file, not recursive, **classification** `lstat` EPERM | ok. Windows: chmod, stat, unlink (recovery). Linux: unlink |
| V3 | directory, recursive, validation `lstat` EPERM | `permission_denied`; nothing else |
| V4 | directory, recursive, classification `lstat` EPERM | ok (Windows through recovery) |
| V5 | validation `lstat` EIO | `unknown`; nothing else |
| V6 | missing, no force | `not_found` |
| V7 | missing, force | ok; `rimraf`'s `lstat` ENOENT |
| V8 | existing file, validation `lstat` ENOENT, no force | `not_found`; the file remains |
| V9 | existing file, validation `lstat` ENOENT, **force** | **ok, and the file is removed** (`rimraf`'s own `lstat` finds it) |
| V10 | file, classification `lstat` EIO | ok (unlink) |

Candidate `b8062daa` (both platforms):
- MATCH: V1, V3, V5, V6, V7, V8.
- **DIFF:** V9. The candidate returns ok but leaves the file, because it stops at force + not_found.
- **UNFIRED** (the binding never makes the call): V2, V4, V10. The candidate has no classification `lstat` for the target; it reuses validation's answer.

### Evidence hygiene: injections must fire

- Both recovery probes now take a matrix argument and `force`, and report `unfired` (planned injections that never matched a call).
- `ce02_compare.py` classifies per row:
  - fired only in Pi → **UNFIRED** (unexercised; never credited);
  - unfired on both sides → not applicable on that platform, and the outcomes are still compared (for example `fixWinEPERM`'s chmod/stat on Linux);
  - fired only in the binding → DIFF.
- The Windows recovery outputs were regenerated with the new probe. Pinned Pi is identical on all 18 rows apart from the added `unfired` field, which is empty for every Pi row. The candidate shows UNFIRED on L3-L6, U2, U4, U5 and T2: it has no correction / inspection / second-unlink stage to inject.
- On Linux, all 13 + 18 + 10 rows ran. The revision 1 Pi output is byte-identical.
  - The recovery rows match except T1/T2 (top-level routing). Rows whose injections Pi never makes on Linux are not applicable.
  - The validation rows are as on Windows.

### Revised OBSERVABLE RULES (= §19.5, revision 3)

- **R0 (new), target validation:**
  - A target `lstat` failure is the result as is, with no recovery, except force + ENOENT, which continues to R1.
  - A directory without recursive gives #125.
  - Otherwise continue to R1.
- **R1:** now explicitly post-validation, with its own fresh `lstat`; R0's answer is never reused.
- **R2 to R6:** unchanged from revision 2.

### Witnesses and controls (additions)

- **Paired permanent witnesses:**
  - V1 against V2: file, validation against classification EPERM; on Windows, recovery runs only in V2;
  - V3 against V4: the same for a directory;
  - V6 against V7: a missing target without and with force;
  - V8 against V9: validation ENOENT without and with force.
- **New controls:**

  | Control | Mutation | Killed by |
  |---|---|---|
  | N12 | the validation error routed into recovery | V1, V3 on Windows (ok instead of `permission_denied`) |
  | N13 | the validation answer reused, no classification `lstat` | V2, V4, V10 (UNFIRED) |
  | N14 | force + validation ENOENT returns at once | V9 (the file remains) |

- **Binding evidence seam** (implementation constraint):
  - The binding's own-attribute correction is one injectable call, which the probe maps to the matrix's `chmod`.
  - Its following inspection maps to `stat`, the retry to the second `unlink`, and the target's classification `lstat` is a call of its own.
  - Acceptance needs **zero binding-side UNFIRED** in every matrix on both platforms.
  - The correction stays no-follow (never a link-following chmod).

## CONVERGENCE CHECKPOINT (revision 3)

**PROPOSED FOR IMPLEMENTATION** (revision 3, Claude)

- **OPEN FINDINGS:** `L12D007-I003`, `CE-L12D007-02-C001`, `CE-L12D007-02-C002` (Owner disposition recorded), `CE-L12D007-02-C003`.
- **ACCEPTANCE WITNESSES:**
  - `ce02_compare.py` over all three matrices (13 + 18 + 10 rows) on Windows and Linux: every row MATCH. "Not applicable" is allowed only where pinned Pi itself makes no such call on that platform. There are no expected differences and no binding-side UNFIRED.
  - The permanent per-row witnesses, including the V pairs.
  - Controls N1 to N14, each killed by its named rows.
  - The `fs-remove-readonly` corpus unchanged and passing.
- **NORMATIVE DELTAS:** spec §19.5 (revision 3: rule 0, post-validation rule 1) and the §17 correction note. Manifest pointers at implementation.
- **NEXT_OWNER:** Codex, for checkpoint review 3 of exactly this proposal.
