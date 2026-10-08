# L12-D004 — Python `canonical_path` ELOOP parity (Layer 12 delta)

**Status:** Python CERTIFIED (merged, `#162` -> `5477eaeb`). Rust: no change required (existing
conformance confirmed, §5 and §8). Cross-language closure is pending (§8).

**Requirement:** `EXEC-002` (`spec/execution.md` §3, `canonical_path`; `DIRECT_PI_PARITY`).

**Classification:** `PI_PARITY_DEFECT` in certified Layer 12, Python binding only. There is **no
contract change**.

**Governance:** Owner decision, 2026-10-08, recorded verbatim at `minion-agent#158`
issuecomment-6054403282, §2. It authorizes reopening certified Layer 12 **solely** to correct Python
`canonical_path` symlink-cycle behaviour, using the OS `realpath` semantics. It also sets this
condition: *"If OS realpath introduces unrelated semantic differences, STOP and return with evidence
and options."*

**Origin:** found while implementing WP-14.1 (`WP141-I002`). Canonical scenario
`skills-c01-symlink-cycle` failed on Linux.

## 1. Defect

- **Pi.** Pinned Pi's `canonicalPath` (`packages/agent/src/harness/env/nodejs.ts:635`) is
  `realpath(resolvePath(cwd, path))`, from `node:fs/promises`. That is libuv's `uv_fs_realpath`, which
  is the OS `realpath(3)` on POSIX and `GetFinalPathNameByHandleW` on Windows.
  - The kernel counts every symlink traversed while it resolves one path.
  - Resolution therefore fails with `ELOOP` once that count exceeds `MAXSYMLINKS` (40 on Linux).
- **Minion's certified Python provider.** It used `os.path.realpath(path, strict=True)`. On POSIX
  that is a *userspace*, component-by-component walk, and each `lstat` it issues sees only an
  already-resolved prefix. It therefore never reaches the kernel's traversal limit.
- **Effect.** Where Pi fails, Python succeeds.
- **WP-14.1 consequence.** A `loop -> ..` cycle is canonicalized at every depth, so discovery
  descends one level further before failing. It then emits four filesystem diagnostics instead of
  the contracted one.

## 2. Characterization (executed; `data/12-l12-d004/`)

**Fixture.** `fixture.py` builds one tree, and 44 probe paths are resolved through **Minion's own
`resolve_local_path`**, the certified mirror of Pi's lexical `resolvePath`. The tree covers:
- files, directories and missing paths;
- a trailing slash on a file;
- lexical `..`, including `..` through symlinks;
- dangling links;
- relative and absolute targets;
- a self-loop and a two-node cycle;
- acyclic chains of 39, 40 and 41 links;
- a `loop/a/back -> ..` cycle walked 4, 39, 40 and 41 levels deep;
- over-long names;
- permission denial.

**Probes.**

| Probe | What it runs |
|---|---|
| `probe_node.mjs` | The **byte-copied pinned** `NodeExecutionEnv.canonicalPath`, under Node v22.15.1 |
| `probe_python.py` | Linux: the current certified `LocalFileSystem.canonical_path`, raw `os.path.realpath(strict=True)`, and the proposed libc `realpath(3)` with its errno mapped by the certified `to_fs_error` |
| `probe_python_win.py` | Windows: the current `canonical_path` |

**Linux** (`python:3.13`, run as `nobody` so permission denial is real; `run_linux.sh`): **44 cases.** (Corrected from "45" in remediation 1; the fixture has always had 44.)
- **Proposed vs Pi:** **0 differences.** Success paths are identical, and every error has the same
  `FsErrorCode`.
- **Current vs Pi:** **exactly 2 differences**, both ELOOP traversal-limit cases.

  | Probe path | Pi | Current | Proposed |
  |---|---|---|---|
  | `chain-41/0`, an **acyclic** chain of 41 symlinks | `unknown` (ELOOP) | success | `unknown` (ELOOP) |
  | `loop/a` + `back/a` × 41 (the c01 cycle) | `unknown` (ELOOP) | success | `unknown` (ELOOP) |

- **Unchanged and already equal to Pi:** chains of 39 and 40 links, the cycle walked up to 40
  levels, the self-loop and two-node cycle (current already reports ELOOP), and every non-symlink
  case: ENOENT, ENOTDIR, ENAMETOOLONG, EACCES, trailing slashes, lexical `..`.

**Windows** (Node and Python on the same NTFS tree, 44 cases; permission denial is not applicable):
- **Resolution matches Pi everywhere.** That includes both 41-level cases: the Windows
  reparse-point limit differs from POSIX `MAXSYMLINKS`, and Pi resolves them too.
- **Six pre-existing differences in error *classification*:**

  | Cases | Pi | Python |
  |---|---|---|
  | self-loop, two-node cycle (4) | `unknown` (ELOOP) | `invalid` |
  | over-long names (2) | `not_found` (ENOENT) | `invalid` |

  These belong to the open Layer 12 Windows error-map issue `minion-agent#69`, and are **not
  changed** here (§4).

## 3. Correction (Python, `minion_agent/execution/filesystem.py`)

- **POSIX.** `canonical_path` now makes **one** call to the OS `realpath(3)`, through
  `_libc_realpath`, following the existing `_libc_access` pattern. It uses the allocating form and
  frees the result exactly once. The errno is kept, raised as `OSError`, and classified by the
  certified `to_fs_error`.
- **Windows.** Unchanged: `os.path.realpath(strict=True)` already uses `GetFinalPathNameByHandleW`,
  as libuv does.
- **Path resolution.** `resolve_local_path` and `native_path` are unchanged and still run before the
  call, as in Pi.

**On the STOP condition.** The only behavioural differences the correction introduces are the two
ELOOP rows in §2.
- One is the cycle itself.
- The other, an acyclic chain of more than 40 links, comes from the **same** kernel traversal limit.
  It is not a separate semantic, and it moves to Pi's result.
- No difference outside the symlink-traversal limit appeared on either platform.

This is therefore judged within the authorized scope, and is disclosed here for the reviewer and
the Owner.

**Downstream.** Downstream consumers of `canonical_path` now see Pi's `unknown` for a path whose
resolution exceeds the traversal limit on Linux:
- `EXEC-003` `resolve()`;
- `TOOL-032`'s mutation-queue key (where `unknown` is not one of the `not_found`/`not_supported`
  fallbacks);
- `TOOL-025`;
- WP-14.1 discovery.

Before this change they saw a success.

## 4. Not changed: the Windows classification gap

The six Windows rows in §2 are pre-existing, sit outside the authorized scope, and are tracked by
`minion-agent#69`. Four of them are symlink-cycle cases, so they are **returned to the Owner** with
these options:
- **(a)** leave them to `#69`. This is the default.
- **(b)** authorize a follow-up delta that classifies Windows `ELOOP`-equivalent failures as
  `unknown`.

WP-14.1 is unaffected: any non-`not_found` code yields the single fs-origin diagnostic, and `c01`
passes on Windows.

## 5. Cross-language status

Rust's `canonical_path` (`execution/filesystem.rs`) uses `tokio::fs::canonicalize`, which is
`std::fs::canonicalize`, which is `realpath(3)` on Unix. It is therefore expected to have Pi's
behaviour already. This is a cross-layer status observation, not an oracle. The Rust owner is asked
to confirm it with a witness for the 41-link chain and the deep cycle. If Rust conforms, no Rust
change is needed.

## 6. Evidence

**Tests:** `minion-agent-python/tests/execution/test_filesystem_canonical_path_eloop.py`, 15 tests.
- **The POSIX branch on any host,** through a fake libc:
  - one `realpath` call on the resolved path;
  - the decoded result;
  - the result freed exactly once;
  - ELOOP, ENOENT, EACCES and ENOTDIR classification.
- **The Windows branch** delegates to `os.path.realpath(strict=True)`.
- **Real-host regressions:**
  - a self-referential symlink;
  - a three-node cycle;
  - valid chains of 1, 5, 39 and 40 links;
  - a 41-link chain (POSIX);
  - the cycle walked 40 and 41 levels deep.

  The Windows cycle rows are strict `xfail`s citing `#69`.

**Known-bad control (Linux).** The old userspace `realpath` was restored in a disposable copy. The
intended real-host witnesses fail:
- `test_a_chain_beyond_the_symlink_limit_is_unknown_as_in_pi`;
- `test_a_cycle_walked_deep_fails_at_the_traversal_limit[41-True]`.

The fake-libc tests also fail, as expected, because that branch bypasses libc. The candidate passes
15/15.

**Gates:**

| Platform | Result |
|---|---|
| Windows, pinned ICU | 5,088 passed, 32 skipped, 21 xfailed; coverage 100%; ruff and mypy clean |
| Linux (`python:3.13`, pinned ICU) | 4,807 passed, 0 failed, 19 xfailed |

**Downstream:** the WP-14.1 `skills-c01-symlink-cycle` row on Linux, re-run on the WP-14.1 branch
rebased onto this candidate. It is recorded in the WP-14.1 assurance record.

## 7. Remediation 1 — `L12D004-R001` (Codex implementation review 1)

**Review:** Codex, **CHANGES REQUESTED** on code `#162` @ `856fb414` / docs `#257` @ `f23e079d`,
posted verbatim at `minion-agent#163` issuecomment-6055084766.

**Finding `L12D004-R001` (high).** The POSIX branch passed the path to `realpath(3)` as a C string,
which ends at the first NUL. A path containing NUL therefore resolved its prefix: with an existing
`file`, `file\0missing` returned `Ok(file)` where the previous implementation raised `ValueError`
(and pinned Pi returns `unknown`). That is an unrelated semantic difference — exactly the Owner's
STOP condition — and the original claim that "only the two ELOOP-limit rows change" was false
outside the 44-path corpus. NUL disposition is `minion-agent#133`'s and is **not** decided here.

**Correction (code `#162` @ `32287fa5`).** A NUL-containing path never reaches the C call. It keeps
the previous resolution, `os.path.realpath(strict=True)`, unchanged, so every NUL outcome is the
pre-delta outcome: `ValueError` in general, `not_found` when an earlier component is missing. All
other paths are unchanged from candidate 1.

**New witnesses** (`test_filesystem_canonical_path_eloop.py`, now 19 tests):
- fake libc: a NUL path delegates to the previous resolution and libc is never called or freed;
- real host, with an existing prefix `file`: `file\0missing`, `missing\0file` and `file\0` give
  exactly the previous outcome on that host, and never `file`'s canonical path.

**Known-bad control (Linux).** With the NUL guard removed in a disposable copy (`data/12-l12-d004/known_bad_nul.py`,
run from the copy's `minion-agent-python/`), all four new tests fail; the other 15 pass.

**NUL neighbourhood (Linux, new; `data/12-l12-d004/`).**
- Probe: `probe_nul.py` over `cases-nul.json` (8 paths, including an absolute path, a NUL after a
  symlink, and a NUL after a missing directory), run by `run_nul_linux.sh`.
- It records `canonical_path`, `resolve` (EXEC-003) and `mutation_queue_key` (TOOL-032) for
  `origin/main` and for the candidate, plus pinned Pi `canonicalPath`.
- Result: `nul-main.json` and `nul-candidate.json` are **byte-identical** (8/8 rows, all three
  consumers). Pi (`nul-node.json`) returns `unknown` (`ERR_INVALID_ARG_VALUE`) on all 8. That
  pre-existing Python/Pi difference belongs to `#133` and is unchanged by this delta.
- Codex's own `neighbors.py` replay also gives identical output on `main` and the candidate.

**Evidence correction.** The Linux corpus count is 44, not 45 (§2 corrected in place, with a note).

**Fresh gates (code `#162` @ `32287fa5`):**

| Platform | Result |
|---|---|
| Windows, pinned ICU | 5,092 passed, 32 skipped, 21 xfailed; coverage 100%; ruff and mypy clean |
| Linux (`python:3.13`, pinned ICU) | 5,029 passed, 0 failed, 97 skipped, 19 xfailed |

A first Windows run had one error, `WinError 10055` (socket buffer exhaustion while creating an
asyncio event loop) in `test_prepared_string_conformance.py`, a module this delta does not touch. That
file passed alone (38/38), and the full rerun above is clean. It is a host resource failure, not a
result.

**Unchanged:** Codex's judgment that the 41-link chain is in scope; the Rust status (no correction
required); the Windows classification gap (§4, Owner options pending).

## 8. Final review, merge and certification

**Final review:** Codex's complete independent final review (workflow §11.4) **APPROVED** the exact
pair, code `#162` @ `32287fa5` and docs `#257` @ `d70e27ba`. `L12D004-R001` is CLOSED and there are
no new findings. It is posted verbatim at `minion-agent#163` issuecomment-6057581461.

**Merge.** The Owner authorized merging on that approval (2026-10-08, recorded in `#163`'s state).
Both PRs were squash-merged at the approved heads by guarded merge:

| PR | Merge commit |
|---|---|
| Code `#162` | `5477eaeb37bbe89bc1d261acadf680e265739acf` |
| Docs `#257` | `1c148c49e48c33f6f85c410a2ae6d02d8c137b26` |

Both merge commits are reachable from the default branches.

**Traceability.** Manifest `EXEC-002`'s `python` field now records the merged correction. The
"candidate, issue pending" wording that Codex noted as stale is replaced (code PR
`layer/12-d004-certification`).

**Status:**
- `EXEC-002` Python, `L12-D004`: **CERTIFIED** — the targeted Layer 12 correction is independently
  approved and merged.
- `EXEC-002` Rust: **no change required**. The existing `tokio::fs::canonicalize` →
  `std::fs::canonicalize` → `realpath(3)` already has the kernel traversal limit. Codex confirmed
  this by a Linux boundary probe and a source audit; it is not a new Rust certification.
- `L12-D004` cross-language: **closure pending** the closure review of this certification record.

**Still excluded, unchanged:**
- `#69`: the six Windows classification differences (§4). The Owner has not chosen between the §4
  options, so the default (leave it to `#69`) holds.
- `#133`: NUL disposition, including the pre-existing Python/Pi NUL difference.
