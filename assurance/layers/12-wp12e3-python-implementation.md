# WP-12.E3 / EXEC-009 — Python implementation candidate (`check_read_write`)

Mode: Python implementation candidate (Claude) for independent exact-SHA review by Codex. It is not merged and not cross-language closed.

## Authority and provenance

- **Contract:** `spec/execution.md` §13 at `minion-agent-docs/master` `57bc24933b820f15fc167e7c0cd4859768bc8e84` (contract #176, reviews #177/#179), and manifest `EXEC-009` at `minion-agent/main` `5ad1b9ed5734ae892b7e864133e982e9efe8b015` (#80).
- **Governance:**
  - owner decision `L13-WP132-O2` = A-1, refined (`minion-agent#49` comment `5881558193`);
  - the routine lifecycle is delegated under `minion-agent#75`;
  - the contract merge was decided at `minion-agent#79` comment `5883673332`.
- **Candidate:** `minion-agent` branch `impl/12-e3-python` @ `7438caaba3cd964718dcb9f9a9ae3ecd5e03672f` (base `5ad1b9ed`).

## Implementation

`minion-agent-python/src/minion_agent/execution/filesystem.py`, additive only:
- **The Protocol** gains one member, `check_read_write`.
- **`LocalFileSystem.check_read_write`** resolves with §3.2's rules and runs one host decision off the event loop. `OSError` is classified by `to_fs_error`. An embedded NUL is `unknown`, as `check_readable` treats it. `signal` is accepted and not inspected.
- **POSIX:** `_check_read_write_posix` makes exactly one libc `access(path, R_OK | W_OK)` and keeps its own errno. There is no preliminary `stat` and no fabricated code.
- **Windows:** `_check_read_write_windows` makes exactly one `CreateFileW` through `_windows_open_probe`:
  - requesting `FILE_READ_DATA | FILE_WRITE_DATA`, which is list + add-file on a directory;
  - with all sharing modes, `OPEN_EXISTING` and backup semantics;
  - following symlinks;
  - never requesting `FILE_DELETE_CHILD`.
- **Unchanged:** `check_readable` (EXEC-008) and every other operation. Their code is untouched; the Windows probe is a new helper, not a refactor of EXEC-008's.

## Evidence

`minion-agent-python/tests/execution/test_filesystem_check_read_write.py` covers every §13.6 row as a provider-parameterized witness, run against `LocalFileSystem` and against **16 negative-control mutants**, each of which must fail its named witness:

| Mutant | Fails |
|---|---|
| readability-only | the readable-not-writable and read-only-directory rows |
| readable fallback inside the provider | the readable-not-writable row |
| writability-only | the writable-not-readable row |
| truncating open | the content/size/mtime-unchanged row |
| create-entry-to-prove | the 0666-directory row |
| requests delete-child | the Windows deny-delete-child row |
| libuv attribute-only access | the Windows deny-write-ACL and dangling-link rows |
| final symlink not followed | the dangling-link row |
| existence-only | two rows |
| open-for-read (blocks) | the FIFO row |
| missing NUL guard | the embedded-NUL row |
| pre-abort rejection | the signal row |
| silent success without the extension | the capability row |

**Two further discriminating tests:**
- the combined-operation row: POSIX exactly one `access(resolved, R_OK | W_OK)`; Windows exactly one probe with mask `0x3`, and `0x40` absent;
- the two-probe mutant making two host decisions.

The POSIX errno table covers ENOENT, ENOTDIR, EACCES, EPERM, EROFS, ETXTBSY, ELOOP, EIO and EINVAL.

**Fresh runs:**

| Host | Result |
|---|---|
| Windows 11 (this candidate) | full suite with 100.00% coverage (`filesystem.py` 513/513); `ruff check` clean; `mypy` clean (91 files); the new file is `ruff format`-clean (the 9 unformatted files are pre-existing on `main`) |
| Windows, EXEC-009 file | 46 passed, 5 skipped. The skips are POSIX-only rows. The Windows ACL rows pass: deny-write, deny-read, the read-only attribute of a file and of a directory, and deny-delete-child |
| Linux, `python:3.13-slim`, **unprivileged** user | EXEC-009 file: 44 passed, 7 skipped (Windows-only rows). The 0666-directory row passes (`Ok`, then creating an entry fails `permission_denied`), as do the FIFO row and every POSIX negative control. Regression, `test_filesystem_check_readable.py` + `test_filesystem.py`: 157 passed, 34 skipped (Windows-only) |
| Linux, same image, **root** | 33 passed. The 6 permission rows are skipped and reported as the contract requires, never faked |

The read-only-filesystem row is witnessed through the errno table (`EROFS` -> `unknown`) rather than by mounting a read-only filesystem, which the test hosts cannot do unprivileged. This is disclosed, not faked.

## Scope and handoff

- No Layer-13 code changes. `edit`'s consumption of EXEC-009 belongs to WP-13.2.
- Rust EXEC-009 is not started; that is the next phase after the Python merge, implemented by Codex and reviewed by Claude.
- Requested: an independent Codex exact-SHA implementation review of `minion-agent` #82 @ `7438caab`.
- Layer 14 is NOT authorized.
