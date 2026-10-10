# L12-D006: a NUL-containing path fails as `unknown`

Layer 12 post-certification delta.
- **Coordination:** minion-agent#194.
- **Provenance:** `L12-NUL` (minion-agent#65) and `#133`-F1.
- **Requirements:** `EXEC-002`, `EXEC-003`.
- **Normative text:** `spec/execution.md` §18.

**Governance.** The Owner decision "#65 + #133-F1, APPROVE OPTION 1: PINNED PI UNKNOWN" is recorded verbatim on #65 and #133 (sha256 `ebb3579cd2a32f96d634a6c06dd6a26e1cfcc931e39df6ae32b3446902887f1c`).
- **Scope:** one narrowly scoped, contract-first delta in both bindings. It is `DIRECT_PI_PARITY`, with no blanket rule.
- **Required characterization:** every operation, individually, against pinned Pi on Windows and Linux.
- **Ordering:** existing ordering and early returns are preserved (abort precedence, `max_lines`, write/append parent creation), and no universal early validation is added.
- **Fallback:** the logical-path fallback is preserved.
- **Python** must not catch every `ValueError`. **Rust** must not globally remap `InvalidInput`.
- **Separate:** #133-F2 stays separate.
- **Required controls:** an escaped Python `ValueError`, Rust returning `invalid`, a global `InvalidInput` remap, premature validation, and logical-path corruption.

## 1. Authority (pinned Pi `b7bb00b9`, Node v22.15.1)

| Symbol | What it shows |
|---|---|
| `nodejs.ts` `NodeExecutionEnv.*` (502–689) | Each operation resolves the logical path and passes it to one `fs.promises` call, or a short sequence of calls: `writeFile` and `appendFile` call `mkdir(parent, {recursive})` first. Every catch is `toFileError(error, <fallback>)`. `renameFile` falls back to `source`. `createTempDir` has no fallback. `createTempFile` falls back to the file path |
| `nodejs.ts` `toFileError` (97–121) | The path is `err.path` if it is a string, else the fallback. A code not in its switch gives `unknown` |
| Node `ERR_INVALID_ARG_VALUE` | Thrown by Node's path validation for a NUL-containing argument. It is a `TypeError` with no `err.path` |
| `coding-agent` `file-mutation-queue.ts` `getMutationQueueKey` | `realpath(resolve(p))`. Only `ENOENT`/`ENOTDIR` fall back to the lexical path, so the NUL rejection propagates |
| `coding-agent` tools | `read`, then `access`; `ls` uses `pathExists` (`access`, all errors become `false`) → "Path not found"; `grep` uses `stat` in a catch → "Path not found"; `find` swallows errors in its `.git` probe, then `spawn(fd, args)` (spawn surface, #195) |

## 2. Characterization (`data/l12-d006/characterization/`)

`pi-nul-probe.mjs` drives the real `NodeExecutionEnv`, imported unmodified. `py-nul-probe.py` drives the certified `LocalFileSystem` at `main` `4efa52ff`. They cover the same matrix:
- every operation, with NUL at the beginning, middle and end, in the final component under a new parent, in a parent component, and with a lone surrogate;
- rename with the NUL in the source, the destination or both;
- abort, with the operations that take a signal;
- `read_text_lines` with `max_lines: 0`;
- temp prefix and suffix;
- the side effects left behind.

**Platforms:** Windows 11 and Linux (Docker, uid 1000, tmpfs). Pi is **identical** on both, apart from random temp names.

| Surface | Pinned Pi | Python (certified) |
|---|---|---|
| every filesystem-touching operation | `unknown` + logical path | `ValueError` escapes, from almost every operation |
| `write_file` / `append_file`, NUL only in the final component | `new/` created, then `unknown` | `new/` created, then `ValueError` |
| `rename_file`, NUL only in the destination | `unknown` naming the **source** | `ValueError` |
| `exists` | `Err(unknown)` (not `false`) | `ValueError` |
| `canonical_path` | `unknown` + logical path | Windows: `unknown`, but the lone-surrogate case projects to U+FFFD. Linux: `ValueError`, or `not_found` when an earlier component is missing (component walk) |
| `check_readable`, `check_read_write` (EXEC-008/009) | (Node `access` rejects) | `unknown`: already conforms |
| `list_dir_raw`, `probe_dir_entry` (EXEC-007) | (Node `readdir`/`lstat` reject) | `ValueError` |
| `resolve` / `target_key` (EXEC-003) | `getMutationQueueKey` throws | as `canonical_path` |
| `absolute_path`, `join_path` | the NUL string | the same |
| `read_text_lines` with `max_lines: 0` | `ok([])` | the same |
| abort with a NUL path | `aborted` (rename: destination) | the same |
| `create_temp_dir` (NUL prefix) | `unknown`, no path | `ValueError` |
| `create_temp_file` (NUL prefix or suffix) | directory created, then `unknown` naming the file path | `ValueError` |

**Tools (Python, Windows):**
- `read` already reports `Cannot access <abs>: unknown filesystem error`.
- `write` and `edit` give `Cannot resolve <path>: unknown filesystem error`, with no parent created.
- `ls`, `find` and `grep` leak `lstat: embedded null character in path`.

**Rust** answers `invalid` (#65 and #133 records). Its characterization and correction belong to the Rust owner.

## 3. Contract

`spec/execution.md` §18 is normative:
- §18.1: the rule and the per-operation table;
- §18.2: what is unchanged;
- §18.3: the tool boundary;
- §18.4: the evidence.

The `fs-path-domain` schema gains, **additively**:
- the operations `list_dir_raw`, `probe_dir_entry`, `check_readable` and `check_read_write`;
- the optional step fields `max_lines`, `force` and `aborted`.

Every L12-D001 document still validates. The shared runner calls the real `LocalFileSystem` for them: `aborted` passes an already-aborted `RunAbortController` signal, and `remove` now passes the step's `recursive` / `force`. No existing L12-D001 `remove` step carries either field, which was checked.

## 4. Canonical evidence

`conformance/agent/fs-path-domain/fs-path-nul.json` holds 158 cases. It is generated by `gen/make_cases.py`, then `gen/pi_oracle.mjs`, then `gen/gen_canonical.py`.
- **Oracle:** pinned Pi's real `NodeExecutionEnv`, plus `getMutationQueueKey` sliced unmodified for `target_key`.
- **Minion-only operations:** the oracle requires the mapped Node primitive to reject with `ERR_INVALID_ARG_VALUE` and no `err.path`, then applies `toFileError`'s rule.
- **Platforms:** generation **fails** unless Windows and Linux observe identically.

**Contract-stage Python:**
- Windows: 116 strict xfails; Linux: 126. The Linux extra is the `canonical_path` / `target_key` component walk.
- The pending set is a rule in the test, and it reproduces both measured sets exactly.

**Binding witnesses** (`tests/execution/test_filesystem_nul.py`):

| Witness | Contract-stage state |
|---|---|
| temp dir: no path | strict xfail |
| temp file, prefix and suffix | strict xfail |
| an unrelated `ValueError` still raises | passes |
| `read` tool | already conforms |
| `write` / `edit` tools | Windows passes; Linux is strict xfail |
| `ls` tool | strict xfail |
| a lexical control | passes |

The `find` tool is not witnessed here. Its subprocess launch is #195.

## 5. Discrimination at the contract stage (`data/l12-d006/controls.py`)

**Recipe:** apply `gen/planned_fix.py` to a scratch copy of the candidate, then run `controls.py`.

**Controls:**

| Control | Mutation |
|---|---|
| `nul-value-error-escapes` | the `ValueError` escapes |
| `nul-mapped-to-invalid` | the code becomes `invalid` |
| `premature-nul-validation` | the NUL is rejected before the native call |
| `projected-fallback-path` | the fallback path is projected |
| `rename-names-the-destination` | rename names the destination |
| `every-value-error-contained` | every `ValueError` is contained |
| `canonical-path-walks-first` | the component walk runs first; observable on **Linux** only, since Windows `realpath` rejects the NUL itself |

Results: see §8 (appended when run).

**Planned fix** (`gen/planned_fix.py`):
- A `_contain_nul` decorator on every path-taking `LocalFileSystem` operation. It turns CPython's "embedded null" `ValueError` into `Err(unknown, <logical resolved path>)`, but only when a path argument actually contains U+0000.
- `canonical_path` checks its whole argument first.
- The temp operations are handled explicitly.
- Because the native call raises at the same point Node's call rejects, the order and side effects (parent creation) carry over unchanged.
- On the overlay, the full `fs-path` conformance module (L12-D001 and L12-D006) passes with `--runxfail`, and so do the binding witnesses. Ruff and mypy are clean.

## 6. Feasibility

`l12-d006-feasibility-matrix.md`.

## 7. Rust (Rust owner, after contract approval)

- Map **only** the NUL validation failure (std/nix `InvalidInput` from an interior NUL) to `unknown`, with the logical fallback.
- Keep `invalid` for every other `InvalidInput`.
- Keep the L12-D001 projection.
- Run the same canonical corpus through the real provider, plus Rust controls for: a global `InvalidInput` remap, `invalid` kept, a projected fallback path, and premature validation.

## 8. Contract-stage results (fresh, at this candidate)

**Gates:**
- **Windows** (Python 3.13.5, pinned ICU): **5558 passed / 50 skipped / 141 xfailed**, coverage **100%** (9317 statements); ruff and mypy clean.
- **Linux** (Docker `python:3.13`, tmpfs):
  - full suite as root: **5483 passed / 0 failed**;
  - the NUL surfaces as uid 1000 (`fs-path` conformance, binding witnesses, L12-D001 negative controls): **176 passed / 132 xfailed**.
- **Disclosed (L12-D001 negative-control module):** `test_the_unmodified_code_passes_every_case` loads the shared `CASES`, so at the contract stage it skips the L12-D006 pending set by the same rule (`_l12_d006_pending`).
- **Disclosed (unrelated bash timing flake):** a first Windows run failed `builtin-bash-abort-during` (output before the abort missing under load). It passed 3/3 in isolation and in the rerun. It is unrelated to this delta.

**Controls** (`controls.py` on the planned-fix overlay):
- **Windows:** baseline **8 intended witnesses PASS**; **6/6 KILLED**. `canonical-path-walks-first` is NOT RUN, because it is observable on Linux only.
- **Linux** (uid 1000): baseline **9 PASS**; **7/7 KILLED**, including `canonical-path-walks-first`.
- A first Linux attempt reported pytest exit 4 because `pytest-cov` was missing for the driver's `--no-cov`. It was discarded and rerun with `pytest-cov` installed.

## 9. Contract review 1 and remediation 1

**Review 1** (Codex; #194 issuecomment-6093062123; verdict sha256 `4e22cf8b6a033a016e6a24e34bb3c6cd36a8b1f3a3413cea834ab9a08d8055e0`).
It reviewed code `1b014860` and docs `160dd5bb`. Verdict: **CHANGES REQUESTED**.

**`L12D006-C001`** (high, `CONTRACT_ASSURANCE_DEFECT`): the decoded-NUL `file://` composition was missing from the acceptance evidence.
- A valid URL ending in `%00x` carries no literal U+0000. L12-D001's certified URL resolution decodes it into the NUL that the native call rejects.
- The planned fix's containment tested the caller's **raw** arguments, so it re-raised the host `ValueError`. Codex observed this on both platforms for `read_text_file` and `exists`.
- `canonical_path` agreed, because it checks the resolved path explicitly.
- All 158 cases used literal NUL strings, so the controls and corpus could not see the gap.

**Remediation 1:**
- **Spec §18.1:** the rule now names the argument "**after** the existing L12-D001 resolution". It says explicitly that `file://` `%00` decoding is a source of the NUL and that the fallback is the decoded logical path. The normative rule is otherwise unchanged.
- **Cases** (`gen/make_cases.py`): the operation set now also runs on `file_url_tail` paths (the schema's existing URL form):
  - `url-final` (`f%00x`), `url-in-parent-component` (`p%00q/child`) and `url-under-new-parent` (`new/a%00b`, with the parent-creation follow-up);
  - the controls: a plain URL succeeds; `%2500` decodes to the literal `%00`, giving an ordinary `not_found`, and a write succeeds, read back through the literal name; a rename to a `%00` URL destination names the source.
  - The corpus is now **237** cases.
- **Oracle** (`gen/pi_oracle.mjs`):
  - URL arguments are built exactly as the shared runner builds them (`pathToFileURL(cwd).href + "/" + tail`);
  - the Minion-only primitives and `target_key` now resolve with **pinned Pi's own `resolvePath`**, sliced unmodified from `nodejs.ts`, instead of `path.resolve`;
  - re-run on Windows and Linux: identical, enforced by the generator.
- **Planned fix:** `_contain_nul` tests the **resolved** path arguments (`resolve_local_path`): the operation's path, plus `rename_file`'s destination. Other arguments, such as `write_file`'s content, are never treated as paths. The error path stays the operation's decoded logical path, which for `rename_file` is the source.
- **Control:** the new `argument-only-containment` restores the raw-argument test. Its intended witnesses are `url-final/read_text_file`, `url-final/exists` and `url-control/rename_file-to-url-nul`. The three anchors the change moved were re-pointed.
- **Feasibility matrix:** a new row for the `file://` `%00` route.
- **Contract-stage pending rule:**
  - URL cases follow the literal-NUL rule, apart from the URL controls, of which only the rename to a `%00` URL is pending;
  - Windows check: the rule reproduces the measured 174 failures exactly.

**Remediation 1, fresh results:**
- **Windows** (3.13.5): **5579 passed / 50 skipped / 199 xfailed**, coverage **100%**; ruff and mypy clean.
- **Linux** (Docker `python:3.13`):
  - full suite as root: **5498 passed / 0 failed**;
  - the NUL surfaces as uid 1000: **191 passed / 196 xfailed**.
- **Controls** (planned-fix overlay):
  - Windows: baseline **11 PASS**, **7/7 KILLED**, including `argument-only-containment` (3 URL witnesses); `canonical-path-walks-first` NOT RUN (Linux only);
  - Linux (uid 1000): baseline **12 PASS**, **8/8 KILLED**.

## 10. Contract re-review 2 and Python implementation

**Re-review 2** (Codex; #194 issuecomment-6094152341): **APPROVED**; `L12D006-C001` CLOSED at code `3fe658fc` / docs `674bf29c`.

**Integration.** `main` had moved (L12-D005 Rust and L0506-D005 Python merged), so `main` was merged into the branch first.
- The only conflict was adjacent manifest edits: L12-D005's Rust note beside the L12-D006 entry.
- **Disclosed:** the same merge commit refreshes the L12-D006 manifest entry. It was still describing the 158-case contract-stage corpus; it now gives 237 cases, the resolved-argument rule and Python's implementation. The C001 remediation had missed this explanatory text.

**Implementation** (code #196):
- **Production:** `gen/planned_fix.py` applied as written. That means `_contain_nul` on the resolved path arguments, `canonical_path`'s whole-argument check, and the temp-creation handling.
- **Contract-stage scaffolding removed:** the strict xfails, the L12-D001 negative-control skip and the binding `PENDING` markers.
- **Certified-test consequence** (disclosed now; it surfaced only in the full suite):
  - `tests/execution/test_filesystem_canonical_path_eloop.py::test_a_nul_path_keeps_the_previous_outcome…` was an L12-D004 (`L12D004-R001`) witness. It asserted the NUL outcome equals the *previous* resolution, while stating "NUL's disposition is minion-agent#133's and is not decided here".
  - L12-D006 is that disposition. The witness now asserts `Err(unknown)` with the logical path and keeps its R001 guarantee: never the prefix's canonical path.
  - The contract-stage overlay runs covered only the fs-path modules, not the full suite, so this consequence was not listed at the contract stage. It changes no L12-D004 rule.
- **New binding witnesses:** an unrelated `ValueError` in `create_temp_dir` / `create_temp_file` still raises. These cover the two remaining branches.

**Fresh gates:**
- **Windows:** **5826 passed / 50 skipped / 21 xfailed**, coverage **100%** (9385); ruff and mypy clean.
- **Linux:**
  - full suite as root: **5763 passed / 0 failed**;
  - the NUL surfaces as uid 1000 (including the L12-D004 witness): **408 passed**.
- **Controls** (`controls.py` against the implementation itself):
  - Windows: baseline **11 PASS**, **7/7 KILLED** (`canonical-path-walks-first` is Linux-only);
  - Linux (uid 1000): baseline **12 PASS**, **8/8 KILLED**.

## 11. Implementation review 1 and remediation 1

**Review 1** (Codex; #194 issuecomment-6095732196; verdict sha256 `2a37d2ce44dc677def6def75b16287265414e0727a82ae69e92bee3c5319f7b0`). Verdict: **CHANGES REQUESTED**.
- **`L12D006-I001`:** `_contain_nul` declared `self, path, /`, so `path` was positional-only. Every keyword call (`read_text_file(path=…)`, `rename_file(source=…, destination=…)`) now raised `TypeError` where the baseline returned `Ok`, across all 15 decorated operations.

**Remediation 1:**
- **Fix:** the wrapper forwards `*args, **kwargs` unchanged. On a contained `ValueError` it binds them against the operation's own signature (`inspect.signature`, computed once at decoration) and reads the path arguments by name: `path`, or `rename_file`'s `source` and `destination`. Containment, the error path and the precedence rules are unchanged.
- **Witnesses** (`test_filesystem_nul.py`):
  - for every decorated operation, a keyword call gives exactly the positional call's Result;
  - a keyword call with a literal or `file://` `%00` NUL is contained as `unknown` with the logical path;
  - a keyword `rename_file` to a `%00` destination names the source and leaves it intact.
- **Control:** `positional-only-wrapper` restores the regression and is killed by the `read_text_file` and `rename_file` keyword witnesses (`TypeError`). `premature-nul-validation` is re-anchored to the binding.

**Fresh gates:**
- **Windows:** **5872 passed / 50 skipped / 21 xfailed**, coverage **100%** (9388); ruff and mypy clean. A first run hit only #197's bash race (with its one coverage line); it passed on rerun.
- **Linux:**
  - full suite as root: **5809 / 0**;
  - the NUL surfaces as uid 1000: **454 passed**.
- **Controls:** Windows baseline **13 PASS**, **8/8 KILLED**; Linux (uid 1000) baseline **14 PASS**, **9/9 KILLED**.
