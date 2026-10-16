# L12-D013 convergence episode CE-L12D013-01: the DIV-009 failure-outcome and precedence surface

Status: **SETTLED; PYTHON AND RUST APPROVED AND MERGED.** Rust: Claude closure review 1 (`#235` issuecomment-6225928456) at code #242 `1c0a1783` / docs #317 `862f78bb`, merged as code → `24dfe1ea`, docs → `8d9674d2` (`12-l12-d013-rooted.md` §15). *(Earlier: SETTLED; PYTHON APPROVED AND MERGED, below.)* `L12D013-PY-I001` was provisionally closed by targeted closure review 8 (issuecomment-6217444941) and closed by final complete review 9 (issuecomment-6217925725). The code was merged as `393138f8` and the docs as `349bef8b` (`12-l12-d013-rooted.md` §13). Rust revalidation is pending. *(Earlier: AGREED FOR IMPLEMENTATION, below.)* **AGREED FOR IMPLEMENTATION** (checkpoint review 6, `#235` issuecomment-6206812375, at code `6ac14acf` / docs `5bb8bd4d`). The Python remediation is recorded in `12-l12-d013-rooted.md` §11, pending targeted closure of `L12D013-PY-I001`. Targeted closure review 7 (issuecomment-6216781677) requested changes; the slot-identity remediation is §12 there. *(Earlier: PROPOSED CHECKPOINT for independent agreement.)*
- Coordination: `minion-agent#235`.
- Finding: `L12D013-PY-I001` (open).
- Trigger: A. I001 survived implementation review 4 (issuecomment-6201717410) and contract review 5 (issuecomment-6205917076). Route RT-6's default, as review 5 recorded.
- Governing decisions: the Owner's DIV-009 decision (issuecomment-6205758223) and its `rename_file` amendment (issuecomment-6206113367).

## 1. What review 5 asked the checkpoint to settle

| Item | Question | Where settled |
|---|---|---|
| A | `rename_file` order: Pi and Rust resolve source, then destination, then abort; Python resolves destination, aborts, then resolves source | the Owner amendment; §4 |
| B | the complete existing read domain, by binding, platform and argument form | §2 (characterized) |
| C | propagation through derived consumers (`exists`, `resolve`) and later resolutions (the NUL error path) | §3 |
| — | subprocess precedence: keep Rust's earlier empty-argv rejection explicit | spec §22.3 |
| — | POSIX scope: DIV-009 governs the outcome wherever a binding already reads; Python's non-read is not certified | spec §22.1, §22.5 |

## 2. The read-domain matrix (characterized)

**Run `rd-1`**, in a Codex-granted `#209` window on 2026-10-16, at code `6ac14acf`, with Python `src` byte-equal to `aefc67e3`.
- **Launcher and probes:** the paper-approved launcher `ce01/run-ce01.mjs` (`277ca758`). Its intercepted controls (`run-ce01-controls.mjs`, `3ccdeb6a`) passed before the run. Disclosure: only their non-PASS lines (none) were printed, so the per-control lines were not retained.
  - Pinned Pi: `read_domain_node.mjs` (`1000ebf2`) runs the exact `resolvePath` slice, with the blob verified, on Node v22.15.1's `path.win32`/`path.posix`.
  - Python: `read_domain_python.py` (`abb20e0c`) runs the real `resolve_local_path`.
  - Each probe counts every native process-cwd read, and every `=X:` read (case-insensitive on win32), with an injected process cwd (`E:\proc`, `/proc`) and injected entry states.
- **Comparator** `compare_read_domain.py` (`5cc4c88d`): exact key-set coverage for both captures (Node 360 = 336 win32 + 24 POSIX, Python 336), unique and well formed; per row it compares the value, the read count and the case-normalized `=X:` sequence.
- **Exits:** all three processes exited 0, every `.err` is empty, and **no row of either capture is an error row**, so no error-diagnostic parity is claimed or needed.
- **Evidence:** `data/l12-d013/ce01/` (ledger `SHA256SUMS`, 15 entries), including the per-cell table `rd-1-classes.txt`.

**Win32 matrix by provider form × input form.** Each cell lists the four inherited-entry states in order: absent, empty, same-drive entry, other-drive entry.
- **N** = Node reads the process cwd; **P** = Python does; **–** = no read.
- **!** = a differing value or `=X:` sequence.

| Provider form | complete root (`C:\x`, `\\srv\share\x`, both `file://`) | device-less rooted / incomplete UNC (`\leaf`, `/leaf`, `\\leaf`, `\\srv\`) | other-drive (`a:leaf`) | same-drive (`c:leaf`) | relative or empty (`leaf`, `""`) |
|---|---|---|---|---|---|
| `C:\base` (device and root) | –– –– –– –– | NP NP NP NP | NP NP –– –– | –– –– –– –– | –– –– –– –– |
| `\\srv\share\base`, `\\?\C:\base` | –– –– –– –– | NP NP NP NP | NP NP –– –– | NP NP –– –– | –– –– –– –– |
| `\base` (rooted, no device) | –– –– –– –– | NP NP NP NP | –– –– –– –– | –– –– –– –– | **N–! N–! N–! N–!** |
| `C:base` (drive-relative) | –– –– –– –– | NP NP NP NP | NP NP –– –– | **N–! N–! ––! ––!** | **N–! N–! ––! ––!** |
| `base`, `""` (relative, empty) | –– –– –– –– | NP NP NP NP | NP NP –– –– | NP NP –– –– | **N–! N–! N–! N–!** |

**Totals (win32, 336 rows).** 300 rows are equal, 36 differ, and there is no row where Python reads but Node does not.
- Node reads in 162 rows, Python in 132.
- All 132 rows where Python reads are rows where Node reads, with an equal value, read count and `=X:` sequence.
- **All 36 differences are a single class:** a provider `cwd` with **no absolute root of its own** (`\base`, `C:base`, `base`, `""`) combined with an input that supplies none either. There, Node reads the process cwd (30 rows) or the same-drive `=C:` entry (6 `C:base` rows, values differ). Python joins the strings and reads nothing.
- That is the pre-existing Python success-path difference that spec §22.5 records and does not reopen. Its cells are **unreachable for DIV-009 in Python**. Nothing is moved there and no new disposition is taken.

**POSIX (Node).** 6 of 24 rows read: provider `base` or `""` with input `x`, `""` or `\leaf`. No row with an absolute provider or input reads. Merged Python's POSIX branch contains no read (source).

**Rust, per entry point** (corrected for `L12D013-RUST-C001`, §2.1).
- **The lossless logical resolver entry,** with raw provider units, reads in exactly Node's POSIX and win32 cells (review 5, `path.rs:123-147`, `path_resolve.rs:93-122`; source-derived).
- **The public providers** first apply the certified OS-path provider adapter, which strips an extended `\\?\` prefix.
- Its revalidation witnesses each entry point's own reading cells by injection.

*(Earlier text: "Rust reads in exactly Node's POSIX and win32 cells … and its revalidation must witness them by injection", stated without the entry-point qualification. Codex found the conflict at the start of the Rust revalidation, #235 issuecomment-6219403726.)*

### 2.1 Rust entry points and the extended provider (`L12D013-RUST-C001`)

**Finding.** `L12D013-RUST-C001`, a `CONTRACT_ASSURANCE_DEFECT` raised by Codex during the Rust revalidation (#235 issuecomment-6219403726; draft diagnostic code #240 `447b7dfa` / docs #315 `9c8e9012`, not to be merged). The revalidation handoff's §B.1 and this section's Rust sentence assigned Node's raw-input matrix to every Rust seam.

**What Rust does.** Rust's public `LocalFileSystem` holds its provider `cwd` as an OS path. CE-L12D012-02 §2 preserves the adapter that maps it before resolution: `native_units`, then `without_extended_prefix`. It also requires that the adapter never be used for a native read.

**Discriminating witness** (Codex diagnostic 3, Windows, injected reader, provider `\\?\C:\base`, input `c:leaf`, `=C:` absent):

| Entry point | Observation |
|---|---|
| Rust's raw logical resolver | one read, the injected error |
| real `LocalFileSystem::absolute_path` | zero reads, `Ok(c:\base\leaf)` |
| paired ordinary provider `C:\base` | zero reads, `Ok(c:\base\leaf)` |
| paired complete-UNC provider | one read, the injected error |

**The frozen Node rows** (`rd-1/node.out`) compare provider `\\?\C:\base` with `C:\base`. **36 of 48 rows are equal,** and these include every rooted and incomplete-UNC row, every complete-root row and every other-drive row. **12 differ:**
- `c:leaf`: Node reads `=c:` in all four entry states, and the process cwd too when the entry is absent or empty. It gives `c:\leaf`, or `c:\deep\leaf` for the same-drive entry. The ordinary provider gives `c:\base\leaf` with no read.
- `leaf` and `""`: Node keeps the prefix (`\\?\C:\base\leaf`, `\\?\C:\base`). The ordinary provider gives `C:\base\leaf` and `C:\base`.

**Disposition (narrow; proposed for independent agreement):**
1. **The read-domain requirement is per entry point** (spec §22.1).
   - Rust's raw logical entry must witness every N cell of this section by injection, the extended-provider `c:leaf` cells included.
   - Each public seam (`ctx.fs`, `ctx.shell.exec`, `ctx.subprocess.spawn`) must witness the cells where it reads. For an extended provider, those are the cells of its adapted form, characterized by injection at that seam and recorded with value and read count.
   - Each no-read cell of a seam runs with a fail-if-called reader.
   - No read is added, moved or forced eager. No prefix is stripped at a native read, and the adapter is not removed.
2. **DIV-009's outcome rules (spec §22.2–§22.4) apply unchanged** wherever an entry point reads. That includes the caller-path mapping, precedence, the rename order and slot identity, `exists`/`resolve`/NUL propagation, and the exception boundary.
3. **The success-value difference is an observation, not certified** (spec §22.5). At Rust's public seams an extended provider differs from pinned Pi in the 12 rows above. Python matches Pi there. The difference lies on the drive-relative and base-resolution surface (L12-D012 and the base §3.2 rule), outside L12-D013's rooted rule. It is tracked as a separate delta, which decides whether to align or to diverge. Neither choice is made here.
4. **Unchanged:** the rooted and UNC-root rule, the corpus, DIV-009's Owner decision and amendment, Python's approval and merge, and the CE-L12D012-02 adapter.

**Consequences for the witnesses (§5).**
- Python's DIV-009 failure witnesses use every **NP** cell class: rooted and incomplete-UNC inputs under each provider form, and other-drive and same-drive inputs with an absent or empty entry.
- Its fail-if-called witnesses use every **––** cell class.
- The **N–!** cells are not Python DIV-009 rows.
- Rust's revalidation covers every N cell, including the provider-without-root class and the six POSIX rows.

## 3. The operation-outcome matrix (DIV-009, every resolver consumer)

"Fails" means the native process-cwd read fails while resolving the named argument. Order and outcome are the spec's §22.2–§22.3.

| Operation | Read point | Outcome of a failed read | Notes |
|---|---|---|---|
| `absolute_path`, `canonical_path`, `file_info`, `read_text_file`, `read_text_lines`, `read_binary_file`, `write_file`, `append_file`, `list_dir`, `list_dir_raw`, `probe_dir_entry`, `check_readable`, `check_read_write`, `create_dir`, `remove` | resolution of `path`, first, before any abort check and native call | `Err(FsError(native code, native diagnostic, path = raw argument))` | under an aborted signal the read failure wins (Pi's order); no further call |
| `rename_file` | source, then destination (amendment) | the first failing argument's error, the raw source or destination; the destination is not resolved after a source failure | abort is checked only after both resolve, keeping `aborted` with the resolved destination |
| `exists` | via `file_info` | the same `Err` propagates, **never `Ok(False)`**, even for a `not_found` classification | Pi: `exists` → `fileInfo`, whose throw propagates |
| `resolve` (`EXEC-003`) | via `canonical_path` | the same `Err` propagates; **no `absolute_path` fallback** and no second read | the fallback stays limited to the native `realpath` failure |
| NUL error path (L12-D006 wrapper) | none: it uses the resolutions already made | the L12-D006 outcome, unchanged | no further read; earlier certified effects (`write_file`'s parent) stay |
| `ctx.shell.exec` | after pre-abort and timeout validation | `ShellError(spawn_error)` carrying the native diagnostic | before shell discovery; nothing spawned |
| `ctx.subprocess.spawn` | after pre-abort (Rust: after its empty-argv check) | `SubprocessError(spawn_error)` carrying the native diagnostic | before the §21 checks; no native process creation |
| `join_path`, `create_temp_dir`, `create_temp_file`, `process_path`, `cleanup` | no path resolution | — | out of DIV-009 |

**Converted:** only an operational OS error raised by the native read itself. In Python that is an `OSError` from the process-cwd view; in Rust, the `io::Error` that the cwd view returns. Every other exception keeps its current behaviour.

## 4. `rename_file` rows (the Owner amendment's required evidence)

Python's aligned order is source, destination, abort, rename. Each row asserts the outcome **and** the number and order of native cwd reads.

| Row | Source | Destination | Signal | Injected reads | Expected outcome | Reads |
|---|---|---|---|---|---|---|
| R1 | `\src` (reads) | `E:\abs\dst` (no read) | aborted | fail | DIV-009 error, path `\src` | 1 (source) |
| R2 | same | same | not aborted | fail | DIV-009 error, path `\src` | 1 |
| R3 | `E:\abs\src` | `\dst` (reads) | aborted | fail | DIV-009 error, path `\dst` | 1 (destination) |
| R4 | same | same | not aborted | fail | DIV-009 error, path `\dst` | 1 |
| R5 | `\src` | `\dst` | not aborted | first read fails | the source's error; the destination is not resolved | 1 |
| R6 | `\src` | `\dst` | not aborted | first succeeds, second fails | the destination's error, path `\dst` | 2 |
| R7 | `\src` | `\dst` | aborted | both succeed | `aborted`, path = the resolved destination | 2 |
| R8 | `E:\abs\src` | `\\srv\share\dst` | aborted | a read would fail the test | `aborted`, resolved destination | 0 |
| R9 | existing native rename error origin and symlink semantics | | | | unchanged (L12-D001, L12-R002) | 0 |
| R10 | NUL in the source, with a reading destination | | | | the L12-D006 outcome; no read inside the error path | as resolution |

## 5. Witnesses (Python remediation; Rust revalidates its surface)

All failures are injected at the native read boundary, never through a deleted real cwd:
- the matrix rows of §2 that read: each fails with ENOENT, with permission denied, and with one other OS error (for example `ERROR_INVALID_NAME` / `EINVAL`); each keeps its own classification and diagnostic;
- every no-read row of §2, run with a fail-if-called reader;
- the caller's path: lone-surrogate, `file://` and `~` spellings of a reading input are reported exactly as passed;
- every row of §3, and the R1–R10 rename rows of §4;
- a pinned-Pi-versus-Minion witness: the pinned slice with a throwing `process.cwd` rejects, while the binding returns its typed result for the same row;
- no side effects, through spies on every filesystem native call and on native process creation.

## 6. Negative controls (green baseline, then the intended witness fails)

| Control | Wrong behaviour | Killed by |
|---|---|---|
| K1 | the raw `OSError` leaks | the `absolute_path`/`file_info` rows |
| K2 | a fixed code (everything `unknown`) | ENOENT → `not_found`, permission → `permission_denied` |
| K3 | `path` omitted | the path rows |
| K4 | the provider `cwd` as `path` | the path rows |
| K5 | the cwd read for a complete UNC or `X:\` input | the fail-if-called no-read rows |
| K6 | catch everything | an injected `TypeError` from the reader must propagate |
| K7 | retry with a fabricated cwd | the read count, and the typed outcome |
| K8 | start a process despite the failure | the spawn spy |
| K9 | the former Python rename order (destination, abort, source) | R1 (`aborted` instead of the source failure) and the read order |
| K10 | `exists` turns a DIV-009 `not_found` into `Ok(False)` | the `exists` row |
| K11 | `resolve` falls back to `absolute_path` after the failure | the `resolve` row's outcome and read count |
| K12 | the NUL error path resolves again | R10, with the second read scripted to fail |

## 7. Normative deltas in this checkpoint

- **Spec §22:**
  - §22.1 restates the read domain by Node's predicate, with the relative/empty/device-less provider class, the qualified no-read sentence, and the rule that DIV-009 governs the outcome wherever a binding already reads.
  - §22.2 gains the amended `rename_file` order and the derived-operation propagation (`exists`, `resolve`, the NUL error path).
  - §22.3 keeps Rust's empty-argv rejection explicit, together with the rename order.
  - §22.5 states that Python's POSIX non-read is neither changed nor certified.
- **Registry `DIV-009`:** the rename amendment, the derived-operation outcomes and the added controls.
- **Manifest `EXEC-002-DIV-009`:** the same, plus `EXEC-003` traceability.

## 8. Checkpoint requested

Independent agreement on §§2–7. §2 is filled from the granted `rd-1` run. After agreement:
1. the Python remediation on the same branches, with gates and the full witness and control set;
2. implementation review;
3. merge;
4. Rust revalidation of its narrow surface.
