# CE-L12-D001-01: `FsError` error-origin convergence (L12-D001, `minion-agent#123`)

**Episode:** `CE-L12-D001-01`. **Status:** `CONTRACT_CONVERGENCE`, checkpoint PROPOSED FOR IMPLEMENTATION, revision 2 (§12; revision 1 was REJECTED on C001, resolved in §13).
**Author:** Claude (characterization, challenge and proposal). **Independent checkpoint reviewer:** Codex.
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`, Node v22.15.1.

## 0. Entry (workflow §11.8 trigger check)

- **A: fired.** `L12-D001-R001` (error origin) survived two independent reviews:
  - contract review 1, docs #227 comment `5943733961`;
  - the targeted re-review, `5944258531`, which found the `list_dir` per-entry residue.
- **B: fired.** `L12-D001-R002` is a successor finding on the same root-cause surface: the §14.8 mkdir walk wording.
- **C: not fired.** The work package has two rejected contract reviews.

Ordinary point-fixing stops here. This record characterizes the **whole** surface, so that no third site is discovered one review at a time.

## 1. Open findings

| Finding | Class | Residue at code `1738324b` / docs `ba093953` |
|---|---|---|
| `L12-D001-R001` | PI_PARITY_DEFECT | `list_dir` names the directory when an entry's own `lstat` fails; Pi names the native entry. Found in this sweep: a recursive `remove` failing inside the tree names the target; Pi names the inner entry |
| `L12-D001-R002` | CONTRACT_ASSURANCE_DEFECT | §14.8 walk step 4 said "`EEXIST` in every other case", which is false for a failed non-intermediate `stat` (the stat's own error is kept). The implementation and its test were already right |

## 2. Root-cause surface

**Which path an `FsError` names.**

Pinned Pi's rule, `toFileError(error, fallback)` (`nodejs.ts:97-121`): Node's `err.path` if the Node error carries one, else the operation's fallback. A binding must therefore reproduce, for each failure:
1. **which native call failed**: the argument, an ancestor (the mkdir walk), an entry (listing or recursive removal), or the source (rename);
2. **whether Node's error names a path**: a read of a directory, a Windows append to a directory, and the JS-level `rm` / `FileError` sites name none, or name the logical string.

Codes (§2.1), the native projection, aliasing, `target_key` and `file://` are **not** this surface.

## 3. Pi symbols and sources audited

| Source | Use |
|---|---|
| `packages/agent/src/harness/env/nodejs.ts`: `toFileError`, `abortResult`, `fileInfoFromStats`, every `NodeExecutionEnv` method | every catch / `FileError` site (§5) |
| Node v22.15.1 `src/node_file.cc` `MKDirpAsync` (blob `49816349d8bab37fea1d84e5326ee5a11acad7a2`) | the recursive-mkdir walk |
| Node v22.15.1 `lib/internal/fs/rimraf.js` (blob `24bf3f46b878e711beadcdc8e1b08700d10aa3c5`) | `rm`'s removal walk, including `fixWinEPERM` |
| Node `fs.promises.rm` / `validateRmOptionsPromise` | the non-recursive directory refusal (`ERR_FS_EISDIR`, logical string) |

## 4. Observable rules

These are normative in `spec/execution.md` §14.8; this section summarizes them.

- **R-A.** An OS-originated failure names the native path of the native call that failed.
- **R-B.** A failure whose Node error names no path names the resolved logical path:
  - a read of a directory;
  - a Windows append to a directory;
  - abort.

  The rename fallback is the logical source.
- **R-C.** JS-level failures name what Pi constructs: `rm`'s directory refusal names the logical string; `fileInfoFromStats`' unsupported type is `invalid`, naming the logical path.
- **R-D.** The mkdir walk (§14.8 steps 1–4, corrected by R002) decides both the path and, for a file used as a component, the code.
- **R-E.** The removal walk (`rimraf`) names the failing entry inside the tree. Its Windows `EPERM` retry is an outcome difference, recorded as `#126` and outside this surface.

## 5. Behavior matrix: every Pi site against the Python binding

"Linux" and "Windows" refer to the observed Pi behavior. Witnesses: `r001` = `data/l12-d001/r001/`, `ce` = `data/l12-d001/ce/`, `corpus` = `fs-path-error-origin.json` / `fs-path-missing.json`.

| # | Pi site | Failing call → `FsError.path` | Python site | At `1738324b` | Witness |
|---|---|---|---|---|---|
| 1 | `readTextFile` catch | `readFile(arg)` → native arg; directory → none → logical; abort → logical | `read_text_file` | match (Windows directory: `#67`) | corpus, r001 |
| 2 | `readTextLines` catch / loop aborts | `createReadStream(arg)` → as #1 | `read_text_lines` | match (`#67`) | corpus, r001 |
| 3 | `readBinaryFile` catch | as #1 | `read_binary_file` | match (`#67`) | corpus, r001 |
| 4 | `writeFile` catch | mkdir walk position; `writeFile(arg)` → native arg; abort after mkdir → logical | `write_file` | match | corpus, r001 |
| 5 | `appendFile` catch | mkdir walk; `appendFile(arg)` → native (Linux) / none → logical (Windows directory) | `append_file` | match (Windows directory: `#67`) | corpus, r001 |
| 6 | `renameFile` catch | `rename(src, dst)` → native **source** | `rename_file` | match | corpus, r001 |
| 7 | `fileInfo` catch | `lstat(arg)` → native arg | `file_info` | match | corpus |
| 8 | `fileInfoFromStats` | unsupported type → `invalid`, logical | `file_info` (`_UnsupportedFileType`) | match | ce `fifo-file-info` (Linux) |
| 9 | `listDir` outer catch | `readdir(arg)` → native arg | `list_dir` | match | corpus |
| 10 | `listDir` per-entry catch | `lstat(entryPath)` → native **entry** | `list_dir` → `_file_info_sync` | **DIFF**: names the directory (R001) | ce `entry-vanish` (both platforms) |
| 11 | `canonicalPath` catch | `realpath(arg)` → native arg (full, not a prefix) | `canonical_path` (explicit native arg; `os.path.realpath`'s own `filename` is a prefix on POSIX and is not used) | match | corpus |
| 12 | `exists` | via #7; `not_found` → `Ok(false)` | `exists` | match | corpus |
| 13 | `createDir` catch | walk position (recursive), `mkdir(arg)` otherwise | `create_dir` | match | corpus, r001 |
| 14 | `remove`, missing | `rm` validation `lstat` → native arg | `remove` | match | corpus |
| 15 | `remove`, directory without `recursive` | `ERR_FS_EISDIR` → logical string | `remove` | path matches (code: `#125`) | r001 |
| 16 | `remove` recursive, **one** failing call inside | `rimraf` failing call → native inner entry / directory | `remove` → `shutil.rmtree` | **DIFF**: names the target (R001, found here) | ce `rm-inner`, `rm-unreadable-dir`, `rm-readonly-parent` (Linux, non-root) |
| 16b | `remove` recursive, **several** failing children | the **first child failure to settle** (concurrent `_rmchildren`) | `remove` → `shutil.rmtree` (sequential: first-enumerated) | **excluded from L12-D001** (C001, Option 3): `#127` | scope-boundary witness `ce/multi/` (§13) |
| 17 | abort sites (`abortResult(signal, resolved)`) | logical resolved | `_aborted(resolved)` | match (fixed in R001 remediation 1) | `test_fs_error_origin.py` |
| 18 | `createTempDir` / `createTempFile` | no caller path; temp path | `create_temp_*` | n/a (no caller path) | — |
| 19 | `readTextLines` `maxLines <= 0` | no call | — | n/a | — |
| 20 | `exec` / shell | not `ctx.fs` | — | n/a | — |

**Minion extensions with no Pi site** (`list_dir_raw`, `probe_dir_entry`, `check_readable`, `check_read_write`; spec §11–§13): these are mappings. An OS failure names the native argument, per §14.2's row, which they already follow. They are unchanged here.

## 6. Minimal executable witnesses

- **Authority (Pi).** `data/l12-d001/ce/ce.mjs` imports `NodeExecutionEnv` unmodified. The interleaving goes through `node:fs/promises.readdir`, the binding Pi imports; it removes the entry after the enumeration returns, and no errno is fabricated. Results: `out/pi-win32.json` (4 cases) and `out/pi-linux.json` (10 cases, non-root uid 1000).
- **Binding.** `ce/ce.py` runs the same programs through `LocalFileSystem`, removing the entry immediately before the provider's own `lstat` of it.

| Comparison | Windows | Linux |
|---|---|---|
| `1738324b` (`out/cmp-before-*.txt`) | 4/4 differ | 8/10 differ |
| local prototype, §8 (`out/cmp-after-*.txt`) | 2/4 differ (both `#126`) | 0/10 differ |

## 7. Negative controls (to add with the implementation)

Each must fail its witness while the agreed implementation passes:
1. `list_dir` maps every `OSError` to the **directory** path (the `1738324b` behavior). It fails `entry-vanish`.
2. A recursive `remove` names the removal **target**. It fails `rm-inner`.
3. `rmtree` re-raises without the carrier (the Python 3.12 quirk that names the enclosing directory). It fails `rm-inner`.
4. The mkdir walk turns a failed non-intermediate `stat` into `EEXIST` (the pre-R002 wording). It fails `test_an_unstatable_target_reports_the_stat_failure`.

The existing 12 controls stay.

## 8. Implementation constraints and the local prototype

This was a feasibility demonstration on the unpushed local branch `ce/l12-d001-01-impl`, which is not a candidate. Changes:
- `list_dir` reports `exc.filename` when the `OSError` names one (the entry), else the native directory.
- `remove` reports `exc.filename` when present, else the logical path.
- The recursive branch calls `shutil.rmtree(path, onexc=...)`. The handler sets the failing call's path and carries the first failure out in a non-`OSError` wrapper, `_RemovalFailure`. Python 3.12's `rmtree` would otherwise catch the re-raised error at the enclosing directory and report it as that directory's `scandir` failure.

Constraints for both bindings:
- **Rust:** reproduce `rimraf`'s failing-call path. `std::fs::remove_dir_all` reports a path of its own choosing, or none.
- **Rust:** reproduce `list_dir`'s per-entry origin.
- **Both:** no behavior change other than the error path.

The Windows `EPERM` retry is `#126`. It is not adopted here.

## 9. Spec, manifest and conformance deltas

- **`spec/execution.md` §14.8:**
  - characterization pointers, and the statement that the table is a complete sweep;
  - the `list_dir` per-entry row corrected (native entry, deterministically witnessable);
  - new rows for recursive `remove` (`rimraf`) and for the unsupported-type `invalid`;
  - walk step 4 corrected (R002);
  - `#126` recorded.
- **Manifest:** the EXEC-002 / EXEC-003 L12-D001 entries name `data/l12-d001/ce/`, and they name the new binding witnesses once those are added.
- **Conformance:** none of these witnesses is a language-neutral scenario.
  - The per-entry origin needs an interleaving seam inside the binding.
  - The recursive-removal origin needs a non-root POSIX user and a permission fixture.
  - Each binding pins them in its own tests against the committed Pi authority outputs, `ce/out/pi-*.json`. The Rust handoff states them as required witnesses.

## 10. Out of scope / deferred

- `#67`: Windows opening a directory as a file (code and, for read/append, path).
- `#125`: the code for `remove` of a directory without `recursive`.
- `#126`: the outcome of a Windows recursive `remove` with a read-only entry.
- **Multi-failure selection** in a recursive `remove`: pinned Pi reports the **first child failure to settle**. This is excluded from L12-D001's certification by Owner decision C001, Option 3, and tracked as `#127` (§13). It is a known parity gap, not a licence to report any failing child.
- macOS: DEFERRED_WITH_REASON (decision §13).

## 11. Challenge pass (workflow §11.8.4)

- **Pi source mapping correct?** Yes. Every row of §5 cites a `NodeExecutionEnv` site, and each walk is audited at its pinned Node source.
- **Matrix complete enough to distinguish realistic wrong implementations?** Yes. The four new controls (§7) each target a distinct realistic error: the directory-for-entry mapping (the actual R001 residue), the target-for-inner mapping, the `rmtree` quirk, and the R002 wording. The r001 and corpus controls already cover the earlier sites.
- **Any cases implementation mechanics rather than observable semantics?** The `rmtree` quirk is a Python mechanism. Its control exists because a natural Python implementation hits it. The observable rule (R-E) is language-neutral.
- **Does any fix silently reopen a lower certified layer?** No. §2–§3 never specified `FsError.path`. The outcome difference (`#126`) and code differences (`#67`, `#125`) are recorded, not remediated.
- **Can both bindings implement it idiomatically?** Yes.
  - Python: the prototype, §8.
  - Rust: an explicit removal walk and a per-entry error mapping over its JS-string path. No extensibility point exists in only one language; the interleaving seam is test-only on both sides.
- **Is every excluded case traceable?** Yes. Multi-failure selection has its own scope-boundary witness (§13), an Owner disposition and a finding (`#127`). No other single-failure origin is excluded.
- **Are all previous review findings represented by an acceptance criterion?**
  - R001 original: corpus `error/*/parent-file/*`, plus the "requested target" control.
  - R001 residue: `entry-vanish`, plus control 1.
  - Recursive-remove site: `rm-*`, plus controls 2–3.
  - R002: the existing test, plus control 4.

## 12. Convergence checkpoint

```text
CONVERGENCE CHECKPOINT
    PROPOSED FOR IMPLEMENTATION

OPEN FINDINGS
    L12-D001-R001 (residue: list_dir per-entry origin; recursive remove inner origin)
    L12-D001-R002 (section 14.8 walk step 4 wording)
    CE-L12-D001-01-C001 (multi-failure selection): RESOLVED BY EXPLICIT SCOPE DISPOSITION (section 13)

ACCEPTANCE WITNESSES
    authority: assurance/layers/data/l12-d001/ce/ (ce.mjs; out/pi-win32.json, out/pi-linux.json)
    scope boundary (not acceptance; C001 Option 3): ce/multi/ -- Pi first-settled under controlled completion
               order (both orders, both names, both platforms); Minion first-enumerated; natural 17/3, 18/2
    binding:   ce.py results equal to the authority on Linux (10/10) and on Windows except #126 (2/4 are #126)
    Python tests to add: entry-vanish interleaving (both names, every host); recursive-remove inner
               origin (real on non-root POSIX; forced on every host); the _RemovalFailure carrier
    negative controls 1-4 of section 7; the existing 12 controls unchanged
    existing: fs-path-error-origin.json, r001 probe, test_an_unstatable_target_reports_the_stat_failure

NORMATIVE DELTAS
    spec/execution.md section 14.8 (this docs head)
    pi-parity-manifest.yaml EXEC-002 / EXEC-003 L12-D001 entries (evidence pointers, with the implementation)

NEXT_OWNER
    Codex (checkpoint review of exactly this proposal)
```

## 13. C001: multi-failure selection (checkpoint revision 2)

**Review.** Codex's checkpoint review (docs #227 comment `5944401954`) returned REJECTED on `CE-L12-D001-01-C001`. Revision 1 permitted "one failing child" where Pi's `_rmchildren` forwards the **first child failure to settle**. Codex's controlled witness showed it: entry order a, b, settlement b, a → `tree/b`.

**Owner decision.** CE-L12-D001-01-C001, **Option 3** (`#123` comment `5944529920`, verbatim):
- Carve multi-failure selection out of L12-D001 as its own finding.
- Do not change the recursive-remove implementation for it.
- Do not substitute a membership or arbitrary-child rule.

```text
Pi multi-failure selection:   CHARACTERIZED
exact rule:                   FIRST_SETTLED
current binding parity:       NOT CLAIMED
L12-D001 scope:               EXCLUDES MULTI-FAILURE SELECTION
separate finding:             RECORDED -- L12-RM-MULTI-FAILURE-SELECTION, minion-agent#127
checkpoint blocker C001:      RESOLVED BY EXPLICIT SCOPE DISPOSITION
```

**Scope-boundary witness.** This is not an acceptance witness. It lives in `data/l12-d001/ce/multi/`.

| Probe | What it shows | Result |
|---|---|---|
| `controlled.mjs` (adapted from Codex's probe): real pinned `NodeExecutionEnv` and Node's real `rimraf`. Two children whose `unlink` fails; instrumentation controls only the completion order | Pi selects first-settled | settlement a, b → `/a`; b, a → `/b`, for `tree` and `t<U+D800>` alike, on Windows and Linux (`out/pi-controlled-*.json`) |
| `controlled.py`: the same tree through the Python binding | Minion does not guarantee first-settled: it has no completion order to follow | **prototype:** the first-enumerated child (Linux `/b`, Windows `/a`). **`1738324b`:** the target |
| `natural.mjs` / `natural.py`: real failures, Linux, non-root, 20 runs | real scheduling variability; not the rule | Pi: 17/3 and 18/2 (`a`/`b`). Python: 20/20 `a` (prototype); 20/20 the target (`1738324b`) |

**Deletion extent.** In the tested positions (the protected child first, middle and last among 20 siblings), Pi and Python both removed every sibling. No finding comes from this characterization. That does not imply the selection semantics are equivalent, and a future concurrent remediation must revalidate it (decision §8).

**Unchanged.** Every other row of §5 remains an exact L12-D001 claim (decision §7): single-failure provenance, addressed paths, the parent `mkdir`, `rename`, the `list_dir` entry, projection, logical versus native, `canonical_path` and `target_key`.
