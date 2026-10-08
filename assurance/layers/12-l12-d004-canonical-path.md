# L12-D004 — Python `canonical_path` ELOOP parity (Layer 12 delta)

**Status:** Python candidate, pending independent review. Rust: an existing-conformance confirmation
is requested (see §5).

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

**Fixture.** `fixture.py` builds one tree, and 45 probe paths are resolved through **Minion's own
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

**Linux** (`python:3.13`, run as `nobody` so permission denial is real; `run_linux.sh`): **45 cases.**
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
