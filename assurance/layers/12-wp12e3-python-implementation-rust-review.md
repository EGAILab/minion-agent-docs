# WP-12.E3 / EXEC-009 — independent Python implementation review

**Verdict: APPROVED**, for the exact remote candidate heads below. This is Python implementation approval only, not Rust implementation or cross-language certification.

## Target and authority

- Reviewer: Codex, independent Rust-side reviewer.
- Coordination: `EGAILab/minion-agent#79`, `IMPLEMENTATION_REVIEW`, `NEXT_OWNER = Codex` at review start.
- Code PR `EGAILab/minion-agent#82` at `7438caaba3cd964718dcb9f9a9ae3ecd5e03672f`, parent/base `5ad1b9ed5734ae892b7e864133e982e9efe8b015`.
- Docs PR `EGAILab/minion-agent-docs#181` at `1e4b6a310d4f2c3730f228bf76372ac91534d63b`, base `57bc24933b820f15fc167e7c0cd4859768bc8e84`.
- Both heads were fetched from the PR refs, verified remote-reachable, open, ready and mergeable; the code diff is limited to `filesystem.py`, the new EXEC-009 test file and EXEC-009 manifest evidence; the docs diff adds only the implementation assurance record. Both diffs pass `git diff --check`.
- Pinned Pi `b7bb00b936dbe21b8e160b3e89efdec361846699`: `packages/coding-agent/src/core/tools/edit.ts:105-109,347-356` uses one `fs.promises.access(path, R_OK | W_OK)` before reading, matching the accepted POSIX rule. The approved shared authority is `spec/execution.md` §13 and manifest `EXEC-009` on the accepted defaults. The Windows single-`CreateFileW` mapping is the traceable owner decision O2 at issue #49 comment `5881558193`, not a claim about Pi's Windows/libuv implementation.

## Source and behavior review

The candidate adds one typed `FileSystem.check_read_write(path, signal?) -> Result[None, FsError]` member and one `LocalFileSystem` implementation. It does not edit an existing operation. `resolve_local_path` is reused, including the established `file://`, tilde and cwd rules. An embedded NUL is rejected before either native API and mapped to the same `unknown` code as `check_readable`. The signal is accepted without inspection.

On POSIX, `_check_read_write_posix` calls the existing `_libc_access()` binding once with `os.R_OK | os.W_OK`, retains the call's own `errno`, and sends the resulting `OSError` through the certified `to_fs_error` mapper. It neither opens nor reads a target. On Windows, `_check_read_write_windows` delegates to one new `_windows_open_probe` call with `FILE_READ_DATA | FILE_WRITE_DATA`, all share modes, `OPEN_EXISTING`, backup semantics for directories, and no reparse-point flag. It does not request `FILE_DELETE_CHILD`, add a second access probe, or read/write content. The handle is closed after success. The approved Windows ACL/symlink policy is thus represented by the real host access decision, not inferred from `stat`, `file_info`, `exists` or `check_readable`.

The tests exercise regular files, directories (including POSIX read+write without search and Windows delete-child denial), permission halves independently, symlinks and loops, missing/non-directory paths, FIFO non-blocking, relative resolution, NUL, pre-aborted signal, unsupported provider, and host error mapping. The direct branch tests count one POSIX `access` and one Windows open with the correct rights mask. Sixteen named mutant cases are run through the same behavior witnesses, plus a two-probe host-call-count mutant. The manifest lists executable test locations and keeps Rust `not implemented`; its `intentional divergence` disposition remains correct for the owner-approved Windows rule. No canonical runner simulates this filesystem operation.

## Fresh verification

The independently created review environment imports `minion_agent.execution.filesystem` from the fetched candidate worktree, not the older editable install. The first unconfigured full run failed only because the certified `ls` collation code correctly refused to load without the pinned ICU identity. After setting `MINION_AGENT_ICU_BIN` and `MINION_AGENT_ICU_IDENTITY` to the existing verified ICU4C 78.3 build, the fresh full run passed:

| Gate | Result |
| --- | --- |
| Windows focused EXEC-009 tests | Passed; the full run includes every new witness and mutant. |
| Linux unprivileged `python:3.13-slim` focused EXEC-009 run | 44 passed, 7 Windows-only skipped. |
| Full Python `pytest` with coverage, configured pinned ICU | **2,136 passed, 16 skipped, 19 expected failures, 100.00% coverage** (`filesystem.py` 513/513 statements covered). |
| `ruff check src tests` | Passed. |
| `ruff format --check` on the changed Python files | 2 files already formatted. |
| `mypy src/minion_agent tests/typing` | Passed; 95 source files. |
| Manifest YAML parse / unique IDs | 110 rows, 110 unique IDs. |
| Lower-layer regressions | Included in the full Python run; focused EXEC-009 + EXEC-008 + existing filesystem tests also passed. |

The read-only mount (`EROFS`) is witnessed by injecting that *actual host errno* into the single-call branch and checking the certified mapping to `unknown`, not by pretending to mount a read-only filesystem. This limit is disclosed by the candidate assurance and does not weaken the contract's other direct host witnesses. The accepted §13 spec still says `CONTRACT_DRAFT`; that is a status marker to synchronize at the appropriate accepted milestone, not a semantic change introduced by this implementation candidate.

## Verdict and next boundary

No active `PI_PARITY_DEFECT`, `CONTRACT_ASSURANCE_DEFECT` or unapproved divergence was found in this exact candidate. **Python WP-12.E3 / EXEC-009: APPROVED FOR MERGE** at code `7438caaba3cd964718dcb9f9a9ae3ecd5e03672f` and docs `1e4b6a310d4f2c3730f228bf76372ac91534d63b`. Under the delegated workflow, Claude owns the exact-SHA merge and merged-baseline verification, then hands off Rust EXEC-009 separately. A moved head invalidates this approval. Rust WP-12.E3: **NOT_IMPLEMENTED**. Cross-language WP-12.E3: **NOT CLOSED**. Layer 14: **NOT AUTHORIZED**.
