# L12-D007 cross-language feasibility matrix (workflow 4.1.1; finding L12D007-C003)

Coordination: minion-agent#199. Contract: `spec/execution.md` section 19.

**Scope.** For each dimension that distinguishes the L12-D007 rules, this matrix records:
- pinned Pi/libuv's native call;
- the Python binding's call and its disposition;
- a read-only audit of the current Rust seam (`minion-agent-rust/crates/minion-agent/src/execution/filesystem.rs` at `minion-agent` `origin/main` `319f5f3a`);
- the required witness.

The Rust column is a **feasibility assessment, not a Rust design**. The Rust owner confirms or corrects each Rust cell when implementing, against the same corpus. Nothing here uses Rust behavior as a semantic oracle.

**Classification seam.**
- Pi: Win32 error → libuv `uv_translate_sys_error` → `toFileError`.
- Python today: CPython `errno` / `OSError` subclass (`to_fs_error`), or, when the C runtime is in the path, no `winerror` at all.
- Rust today: `io::Error::kind()` (`map_fs_error`, line 1278). `ErrorKind` collapses Win32 causes: 123/161/206 → `InvalidFilename`, 267 → `NotADirectory`, 32/33 → `Uncategorized`. `raw_os_error()` keeps the Win32 code whenever the error came from a Win32 call.

## Matrix

| # | Dimension | Pi / libuv 1.49.2 native call | Python: call and disposition | Rust: audited seam and feasibility | Required witness |
|---|---|---|---|---|---|
| 1 | Generic Win32 translation | `uv_translate_sys_error` | **Implemented:** `to_pi_fs_error` keys on `winerror` (pinned table). | **Feasible:** key `raw_os_error()` through the same pinned table, scoped to the Pi-derived operations. `ErrorKind` alone is insufficient. | the corpus name-class, link-loop and sharing/lock rows |
| 2 | Read open of a file/directory | `fs__open`: `CreateFileW`, full sharing, `FILE_FLAG_BACKUP_SEMANTICS` | **Implemented:** CPython `open()` (C runtime, no `winerror`, refuses directories) is replaced by libuv's call (`_libuv_win32.open_like_libuv`). | **Gap, feasible:** `tokio::fs::read` → std `File::open` uses `CreateFileW` **without** backup semantics, so a directory open fails 5 where libuv's succeeds. It must make libuv's open (`OpenOptionsExt::custom_flags(FILE_FLAG_BACKUP_SEMANTICS)`, share modes) and keep `raw_os_error`. | directory read → `is_directory` (logical path); **denied directory → `permission_denied`; held directory → `unknown`** (C002) |
| 3 | Read / write of the open handle | `fs__read` / `fs__write`: `ReadFile` / `WriteFile` | **Implemented:** the C runtime's `_read`/`_write` (which collapse 33 → `EACCES`) are replaced by `ReadFile`/`WriteFile` on the handle (`_HandleIO`). | **Likely already equivalent:** std `File` read/write are `ReadFile`/`WriteFile`, with `raw_os_error` preserved. To confirm. | lock-violation read/write → `unknown`; directory read → 1 → `is_directory` |
| 4 | Write/append open (`w`/`a`) | `fs__open` `CREATE_ALWAYS` / `OPEN_ALWAYS`; `ERROR_FILE_EXISTS` under create-without-exclusive → `EISDIR` | **Implemented**, including the special case. An append's directory open succeeds and the write fails with 1 (no path, so the logical path). | **Gap, feasible:** std `OpenOptions` create/truncate dispositions match, but there is no backup semantics and no 80 → `EISDIR` special case. Reproduce both. | directory write/append → `is_directory` (the path rule differs: open versus write failure); denied/held directory |
| 5 | Directory listing | `fs__scandir`: `CreateFileW(FILE_LIST_DIRECTORY \| SYNCHRONIZE)`, full sharing, backup semantics; a non-directory gives explicit `ENOTDIR` | **Implemented:** libuv's open before `os.scandir` (`check_listable`), because `FindFirstFileW` answers 267 for a file and differs under sharing. | **Gap, feasible:** `tokio::fs::read_dir` → std `FindFirstFileW` (as CPython). Add libuv's directory open first, or enumerate from that handle. | `list_dir` of a held file → `unknown`; of a file → `not_directory`; of a denied directory → `permission_denied` |
| 6 | Non-recursive `create_dir` | `fs__mkdir`: `CreateDirectoryW`; 123/267 forced to `EINVAL` | **Implemented:** `invalid` for those `winerror`s. | **Feasible:** `tokio::fs::create_dir` is `CreateDirectoryW` (`raw_os_error` kept). Add the 123/267 → `invalid` rule. | invalid-name / over-long / stream non-recursive → `invalid` |
| 7 | Recursive `create_dir` and write/append parent `mkdir` | Node `MKDirp` over libuv `mkdir`; `EINVAL` from 123 takes the stat fallback; the stat's own error is reported | **Already conforming** via the existing step-for-step `_node_mkdirp` plus the corrected mapper (the stat's 123 → `not_found`). | **To audit:** Rust has its own recursive walk (lines 931-940 and 1473). It must reach the stat fallback for 123/267 and classify the stat error by Win32 code. Error-origin paths are unchanged (L12-D001). | recursive invalid-name → `not_found`; non-directory component → `not_directory` (the path the walk was at) |
| 8 | `remove`: unlink and rmdir | `fs__unlink_rmdir`: open the entry (`FILE_READ_ATTRIBUTES \| FILE_WRITE_ATTRIBUTES \| DELETE`, full sharing, reparse point, backup semantics), delete through the handle (POSIX delete, ignore read-only; fallback: clear read-only, then delete) | **Implemented:** `_libuv_win32.unlink_like_libuv` for top-level files/links, and a depth-first walk using it for recursive trees. It replaces `DeleteFileW` / `shutil.rmtree`, whose access rights differ. | **Gap, feasible:** `remove_file` is `DeleteFileW` (needs only `DELETE`); `remove_dir_all` is handle-based but its access rights need checking against libuv's. Make libuv's open plus delete per entry. | read-denied file → `permission_denied` (top level, `force`, recursive); **tree with a read-denied entry → `permission_denied` naming the entry**; read-only entry deleted (L12-D005 still green) |
| 9 | Non-recursive remove of a directory (#125) | Node `rm` raises `ERR_FS_EISDIR` before any syscall | **Implemented:** `unknown` (logical path), both platforms. | **Feasible:** a provider-level refusal mapped to `unknown`. | the corpus `remove` / `remove-force` of a directory |
| 10 | `force` swallows not-found | Node `rm({force})` ignores its libuv `ENOENT` (Win32 2/3/123/161/267 …) | **Implemented:** swallows exactly what the mapper classifies `not_found`. | **Feasible:** the same predicate on the translated code, not `ErrorKind::NotFound`. | invalid-name / over-long / stream `remove-force` → `ok`; denied file `remove-force` → `permission_denied` |
| 11 | `rename_file`, `file_info`, `exists`, `canonical_path` | `MoveFileExW`; libuv `fs__stat` (by-name fast path / `FILE_READ_ATTRIBUTES` open); `fs__realpath` (`CreateFileW` access 0, backup semantics) | **Implemented** through the corrected mapper; the corpus is green, including denied/held rows. | **Feasible with audit:** std rename is `MoveFileExW`; `metadata` / `canonicalize` open with backup semantics. Classify with the pinned table; confirm per row against the corpus. | corpus rows (for example a denied file's `file_info` → `ok`, held-directory `rename` → `unknown`) |
| 12 | NUL handling (L12-D006, section 18) | Node argument validation | **Unchanged.** The libuv-equivalent calls reject a NUL **before** ctypes (which would truncate at it) with the same `ValueError`, so section 18's containment is untouched. | Rust's NUL rejection is the separate L12-D006 delta (#194); unchanged here. | the existing 237-case NUL corpus stays green |
| 13 | Temp operations | Pi `createTempDir` / `createTempFile` | Use the corrected mapper. | Corrected mapper; no special case. | existing temp witnesses |
| 14 | EXEC-007/008/009 (`list_dir_raw`, `probe_dir_entry`, `check_readable`, `check_read_write`) | the Node primitive each maps (semantics are Minion extensions on Windows) | **Implemented:** semantics unchanged; failure classification through the corrected mapper; `list_dir_raw` makes `list_dir`'s directory open. | **Feasible:** keep the ACL-aware probes; route their failure classification through the same Win32 mapping (closes section 13.4's recorded sharing-violation difference). | **consistency witnesses:** the same Windows condition (link loop, sharing violation, name class) gives the same code from the primitive and from the Pi-derived operations |
| 15 | `not_supported` capability answers | none (provider capability) | **Unchanged.** | **Unchanged.** | the existing capability witnesses |
| 16 | POSIX | libuv `open(2)` / `read(2)` / `unlink(2)` … errno → `toFileError` | **Unchanged** except #125 (row 9). Mode-000 precedence is already libuv's. | **Unchanged** except #125. | Linux corpus (non-root uid 1000) |

## Realistic wrong implementations each witness must reject (controls)

- **A global errno or `ErrorKind` remap** (for example `InvalidInput` → `unknown`, or `EINVAL` → `not_found`): rejected by row 6 (non-recursive `create_dir` must stay `invalid`) and by L12-D006's unrelated-`InvalidInput` witness.
- **A target-type `is_directory` substitution**: rejected by the denied-directory and held-directory rows (C002).
- **Keeping the runtime's own open or list call and translating its code**: rejected by the held-file `list_dir` row, the denied-directory read row and the read-denied-file `remove` row.
- **Mapping the read error but not the open error, or the reverse**: rejected by the lock-violation read/write rows versus the held-file rows.
- **Keeping `DeleteFileW` / `rmtree` for removal**: rejected by the read-denied-file and tree-with-denied-entry `remove` rows.
- **Leaving EXEC-007/008/009 on the old mapper**: rejected by the consistency witnesses (row 14).

## Deferred / not applicable

- **Not applicable:** subprocess and shell error codes (§2.2, §2.3); `#133`-F2 native-name decoding; DIV-008 (#127).
- **Not exercised by the corpus:** Win32 codes the matrix never reaches (206, 145, 17, …). These follow the pinned table by construction; no special case exists for them.
