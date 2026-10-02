# L12-D001: filesystem path JavaScript-string domain — contract

**Work package:** `minion-agent#123`. **Status:** CONTRACT_REVIEW (re-review after `L12-D001-R001`, §7) at the heads named on #123.
**Authorization:** Owner decision FSP-Q001, Option 1 (`#123` comment `5943405192`; transcription note `5943409360`).
**Normative text:** `spec/execution.md` §14.
**Characterization:** `fs-path-jsstring-scoping.md`. **Feasibility:** `l12-d001-feasibility-matrix.md`.

## 1. Pinned-Pi symbols audited (`b7bb00b9`)

| Symbol | Fixes |
|---|---|
| `packages/agent/src/harness/env/nodejs.ts`: `NodeExecutionEnv` (`resolvePath`, `toFileError`, `abortResult`, `fileInfoFromStats`, every fs method) | the Layer-12 authority itself; it is executed, not re-implemented |
| `coding-agent/src/core/tools/file-mutation-queue.ts` `getMutationQueueKey` | `target_key`: realpath, or the raw `resolve` for ENOENT/ENOTDIR |
| `coding-agent/src/utils/paths.ts` `normalizePath`/`resolvePath`; `core/tools/path-utils.ts` `resolveToCwd` | tool preprocessing keeps code units; unguarded `fileURLToPath` (R002-A) |
| `write.ts:229`, `edit.ts:380`, `ls.ts` | tool-authored text interpolates the path as given; `ls` lists the addressed directory |
| Node v22.15.1 fs binding, `url.fileURLToPath` | the native projection; the scalar-value URL input |

## 2. Requirements and scope

- **Rows.** `EXEC-002` (provider) and `EXEC-003` (`FsTarget`) get the L12-D001 rule. The tool rows `TOOL-025`/`028`/`029`/`030` get inheritance-test pointers only.
- **Not reopened.** No disposition changes. EXEC-001…009, WP-13.1 and WP-13.2 are not reopened (decision §14). Their scalar claims are unchanged, and the corpus contains every scalar control.

## 3. Canonical evidence

`minion-agent` `conformance/agent/fs-path-domain/` (`fs-path-domain-scenario.schema.json`):

| Document | Cases | Source |
|---|---|---|
| `fs-path-names` | 22 | authority |
| `fs-path-missing` | 22 | authority |
| `fs-path-alias` | 2 | authority |
| `fs-path-file-url` | 10 | authority |
| `fs-path-tools` | 5 | Pi tool templates + authority facts (stated in the document) |

- **Authority:** `data/l12-d001/out/pi-{linux,win32}.json`; the observations are identical. `make_scenarios.py` refuses to generate otherwise.
- **The runner is thin.** `tests/conformance/fs_path_runner.py` makes one real `LocalFileSystem` call (or `resolve()`, or one real tool call) per step and observes only.

## 4. Python

The production change is `execution/filesystem.py`:
- **`scalar_value_string` / `native_path`**, applied at every OS call and to OS-error paths.
- **Logical path kept** for `absolute_path`, `file_info` name and path, list-entry paths, abort errors and non-OS errors.
- **`file_url_to_path`** applies the scalar-value conversion before the unchanged ada parse.

| Check | Result |
|---|---|
| Windows host | **62/62** (56 `ctx.fs` + 5 tool + completeness) |
| Linux (`python:3.13`) | **57/57** `ctx.fs` cases |
| the old provider on Windows | **37/57** fail |

The tool cases need the pinned ICU build (`ls`) and run where it is available.

**Negative controls** (`tests/execution/test_fs_path_negative_controls.py`, decision §19). The unmodified code fails 0/61.

| Mutant | Failing cases |
|---|---|
| early tool-level U+FFFD conversion | 3 (tools) |
| tool message rewritten to U+FFFD | 3 (tools) |
| rejection before `ctx.fs` (Rust's former behavior) | 3 (tools) |
| `ls` `"."` substitution (Rust's former behavior) | 3 (tools) |
| raw OS passthrough (Python Windows defect) | 37 |
| host-codec exception (Python POSIX defect) | 37 |
| valid pair replaced | 13 |
| raw surrogate leaked in a directory component | 20 |
| always-project-before-`target_key` | 34 |
| never-project-before-`target_key` | 18 |

## 5. Rust

NOT_IMPLEMENTED. Required, with the type design left to Rust:
- a lossless JS-string path through the `ctx.fs` trait, the file-URL conversion and the tools' path extraction;
- native projection at the OS call;
- removal of the tools' "path is required" refusal and of `ls`'s `"."` substitution;
- passing the 56 + 5 cases and Rust equivalents of the §19 controls.

## 6. Deferred / open

- **macOS:** DEFERRED_WITH_REASON; run the probe before claiming macOS certification.
- **The §8 queue race:** Pi parity, documented, not redesigned.
- **WP-13.4 (#51)** consumes this contract once it is approved (decision §17).

## 7. Contract review 1 → remediation (`L12-D001-R001`)

**Codex verdict:** CHANGES REQUIRED at code `adc9b174` / docs `4b809f11`, with one blocking finding, `L12-D001-R001` (PI_PARITY_DEFECT). Published verbatim at docs #227 comment `5943733961`.

**The finding.** The contract promised Node's `err.path` for OS-originated errors, but the provider always reported the requested target.
- **Codex's witness:** a write or append to `a<U+D800>/child`, where `a<U+D800>` is a file.
- **Pi** names the parent `a<U+FFFD>`. **Python** named `a<U+FFFD>/child`.
- The rest of the contract was found coherent and reproducible.
- A non-blocking runner diagnostic (`step['op']` on a tool step) was also fixed.

### 7.1 Characterization: the error-origin neighborhood

The finding asked for the neighborhood, not one site. `data/l12-d001/r001/probe.mjs` runs 39 failure programs through Pi's `NodeExecutionEnv`, for an ordinary name and an unpaired-surrogate name (78 cases). It runs on Windows 11 and on Linux (`node:22.15.1-alpine`). For each case it records Pi's `FsError`, Node's own `code`, and whether Node's error had a path.

The 39 programs cover:
- a file as the parent or grandparent of `write_file`, `append_file` and `create_dir` (recursive and not);
- reads, `file_info`, `exists`, `list_dir`, `canonical_path` and `remove`, through a file component or of a missing path;
- every operation on a directory;
- `rename_file`, with source-side and destination-side failures.

Findings (normative text in `spec/execution.md` §14.8):
- **The failing call decides the path.**
  - Parent creation is Node's recursive-`mkdir` walk (`src/node_file.cc` `MKDirpAsync`, blob `49816349…`). It names the path it was at.
  - A file as the parent itself: the walk reports that parent.
  - A file further up: Linux reports the directory asked for; Windows reports the blocking file. **Node differs by platform here.**
  - `rename_file` names the source for every failure.
- **Node errors that name no path use Pi's logical fallback.** The candidate projected all of these:
  - a read of a directory (both platforms);
  - an append to a directory (Windows);
  - `remove`'s directory refusal (Node's own `ERR_FS_EISDIR`, which names the logical string).
- **The scalar-path consequence is identical**, since one mechanism serves all paths. §2–§3 never specified `FsError.path`. No certified claim changes (decision §14), and the rule is now specified for every path.
- **Pi versus Python** (`r001/out/cmp-{before,after}-{win32,linux}.txt`, 78 cases each):

| | Windows | Linux |
|---|---|---|
| Cases differing before | 26 | 15 |
| Cases differing after | 14 | 4 |

- **Every remaining difference is a code, outside this delta, recorded separately:**
  - `#67` (scope note `5943979973`): opening a directory as a file on Windows gives `permission_denied`. For read and append the path follows too, because Node names none.
  - New `#125` `L12-RM-DIRECTORY-CODE`: `remove` of a directory gives `unknown` in Pi and `is_directory` in Python. Remediation is not authorized, per the `#67`/`#69` policy.
- **Paths:** every path matches on Linux. On Windows every path matches except the `#67` cases.

### 7.2 Python

Changes in `execution/filesystem.py`:
- **`_node_mkdirp`** reproduces Node's walk step for step. It replaces `os.makedirs` for `write_file` / `append_file` parents and for recursive `create_dir`. The error names `exc.filename`, the walk's position.
- **A read failing as a directory** (`IsADirectoryError`, POSIX) reports the resolved logical path. Node opens the directory, and its read error names no path.
- **`remove`:** an error without a `filename` reports the logical path. That is the directory refusal, raised on Node's behalf. OS failures report the native path.
- **`append_file`:** parent creation and the append are now separate, so each names its own path.
- **Pre-aborted `read_text_file` / `read_binary_file` / `write_file`** now report the resolved path, as Pi's `abortResult(signal, resolved)` does. Before, they reported the caller's raw string.
- **Disclosed side effect:** on Windows, the walk turns a recursive creation through a file into Pi's `not_directory` (Python previously reported `not_found`). No certified test or scenario asserted the old value.

### 7.3 Evidence and gates (fresh)

**Authority.**
- `data/l12-d001/` regenerates with the unchanged `run.sh`, in host mode (Windows) and container mode (Linux).
- `cases.json` has 122 cases, adding 66 `error/*`. The 56 existing observations are byte-unchanged. 31 of the new cases differ by platform in Pi itself.
- `make_scenarios.py` keeps the Linux = Windows assertion for the path-domain documents and emits `expect_by_platform` only in `fs-path-error-origin`. The four existing documents regenerate byte-identically.
- Probe programs not in the corpus (7 per name):
  - `missing/{read,list-dir,canonical}` are already in `fs-path-missing`;
  - `rename/missing-source-lone-dst` is in the corpus as `rename/missing-source-named-dest`;
  - `rename/source-in-lone-dir-dest-missing` is the destination-side pattern already pinned by `rename/dest-parent-missing`;
  - `self-dir{,-nonempty}/remove` is the `#125` code.

**Corpus.**
- `fs-path-error-origin.json` has 66 cases. The 10 directory-open cases are `platforms: [linux]`, with a `platform_note` naming `#67`.
- The schema adds the six operations, `expect_by_platform`, and `platforms`/`platform_note`, with rejection tests.

**Python.**

| Run | Result |
|---|---|
| Windows host | all 122 `ctx.fs` + 5 tool cases pass; 10 skipped, each with its note |
| Linux container | **122/122** `ctx.fs` cases, including the 10 Linux-only ones |
| Reviewed head `adc9b174` | fails **12** cases on Windows and **11** on Linux |

**Negative controls (12).** The unmodified code fails none.

| Mutant | Windows kills |
|---|---|
| requested target named by write/append | 8 |
| the `os.makedirs` walk instead of Node's | 8 |
| the ten §19 controls (larger corpus) | 3 / 3 / 3 / 3 / 60 / 65 / 13 / 37 / 34 / 18 |

**Focused tests.** `tests/execution/test_fs_error_origin.py` has 21 tests:
- every branch of the walk;
- the read-of-directory fallback, forced on every host;
- `remove`'s two paths;
- the pre-abort resolved path.

**Gates.**
- `pytest`: 4029 passed, 27 skipped, 19 xfailed. Coverage 100.00%.
- `ruff check` clean; `mypy` clean (97 files).
- `ruff format`: the touched files are formatted, except `tests/execution/test_filesystem.py`, which was already unformatted at `adc9b174`.

### 7.4 Rust (unchanged scope, one addition)

In addition to §5:
- Parent and directory creation must reproduce Node's walk (§14.5, §14.8). The platform's "create all" primitive is not enough.
- The binding must pass the error-origin corpus on each platform it runs.
