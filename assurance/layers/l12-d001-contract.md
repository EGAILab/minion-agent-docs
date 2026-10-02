# L12-D001: filesystem path JavaScript-string domain — contract

**Work package:** `minion-agent#123`. **Status:** CONTRACT_DRAFT → CONTRACT_REVIEW at the heads named on #123.
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
