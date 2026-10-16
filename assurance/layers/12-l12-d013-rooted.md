# L12-D013: win32 rooted drive-less input (scoping 1)

Status: **CLOSED: PYTHON AND RUST APPROVED AND MERGED** (§15). Rust: Claude closure review 1 (`#235` issuecomment-6225928456) at code #242 `1c0a1783` / docs #317 `862f78bb`, merged as code → `24dfe1ea`, docs → `8d9674d2`. L12-D013 cross-language is CLOSED. *(Earlier: PYTHON APPROVED AND MERGED; RUST REVALIDATION PENDING, §13.)* Final complete review 9 approved the frozen pair, and both PRs are merged; L12-D013 cross-language is NOT CLOSED. *(Earlier: DIV-009 PYTHON REMEDIATION for targeted closure of `L12D013-PY-I001`, §11–§12.)* That remediation came after checkpoint CE-L12D013-01 was agreed (review 6). *(Earlier: REMEDIATION: DIV-009 contract amendment for independent agreement, §10.)* Implementation review 4 found `L12D013-PY-I001`, and the Owner decided it as `DIV-009`. *(Earlier: PYTHON IMPLEMENTATION CANDIDATE for independent implementation review, §9.)* Contract review 3 approved contract candidate 2 (§8). *(Earlier: CONTRACT CANDIDATE 2 for independent contract re-review, §8.)* Contract review 2 requested changes to candidate 1 (§7); §8 records the narrow remediation. Scoping 1 was approved by Codex review 1. Python is not corrected yet. *(Earlier: CONTRACT CANDIDATE for independent contract review, §7. Before that: SCOPING, PROPOSED for independent scoping review.)* Coordination: `minion-agent#235`. Delta of `EXEC-002`/`EXEC-005`. Class: governing, CP-6 (WORKFLOW 11.8.11(c)).

## 1. Source

- **Origin:** the `#229` Rust closure review 1 (issuecomment-6183035989).
- **Python:** merged Python resolves `\leaf` against the *provider* cwd's drive.
- **Pinned Pi:** resolves it against the *process* cwd's device.
- **Gap:** spec §3.2 says "an absolute result is used as-is (syntactically normalized)" without naming where the device comes from. The 80-case corpus has no win32 rooted drive-less row, which is why both certifications missed this.

## 2. Authority (pinned Pi, Node v22.15.1)

`resolvePath` (`nodejs.ts:51-65`, Pi `b7bb00b9`) is `isAbsolute(p) ? resolve(p) : resolve(cwd, p)`. `path.win32.isAbsolute` is true for every input whose first unit is `\` or `/`. Such an input therefore reaches `path.win32.resolve(p)` **without the provider cwd**.

`win32.resolve` (`lib/path.js` at v22.15.1) parses the input's root as follows:

- **One leading separator** (or the input is a single separator): `rootEnd = 1`, `isAbsolute = true`, device `''`.
- **Two leading separators:**
  - It is a UNC root only when `server`, one or more separators, and `share` follow, with both parts non-empty. Then the device is `\\server\share` and the input is used with that device.
  - Otherwise there is **no device and `rootEnd = 0`**, so the whole input, separators included, becomes the tail. Examples: `\\leaf`, `\\srv\`, `\\\leaf`.
- **An absolute tail with an empty device:** the loop reaches `i = -1` with `resolvedDevice` empty and takes `path = process.cwd()`. **No `=X:` entry is consulted.**
  - The cwd's own root parse supplies the device: `E:`, `\\localhost\E$`, or `\\?\E:` (parsed as server `?`, share `E:`).
  - The loop then ends. The cwd's tail is unused, because the input was already absolute.
- **Result:** `device + '\' + normalizeString(tail)`.
  - Both separators are accepted, and `\` is emitted.
  - Empty and `.` segments are dropped, and `..` is clamped at the root.

The `process.cwd()` operand is the one settled in CE-L12D012-02 R1 (libuv's `uv_cwd` single final-separator trim, then the native string view). Its read failure keeps the existing L12-D012 typed error, with no guessing.

POSIX is not affected: `/leaf` is absolute there and is used as-is.

## 3. Characterization (read-only, Codex-granted windows)

All children run with an existing directory as their cwd. Nothing is created, written, renamed or deleted, and results go to stdout only. Pinned Pi's `resolvePath` is sliced unmodified from the verified pinned blob.
- The Python source is `minion-agent-python/src` at `b7d046fe`, identical to main `83a78655`.
- The Rust observer is the ignored `native_observer` test built from `666e7365` (the code merged as `83a78655`), on the reviewer-only target.

| Run | Probe | Output | Dimensions |
|---|---|---|---|
| 1 | `rooted_probe.py` `b19a9160…` | `rooted-probe-1.json` `9dd52873…` | cwd {plain `E:\…`, root `E:\`, extended `\\?\E:\…`} × provider {`C:\x`, `E:\y`, `\\srv\share\x`, `\\?\C:\x`} × `=C:`/`=E:` {absent, present elsewhere} × 19 inputs; Node + Python |
| 2 | `rooted_probe2.py` `9235516f…` | `rooted-probe-2.json` `8fae1de1…` | run 1's partition, plus a UNC cwd `\\localhost\E$\…` and 6 more inputs (incomplete-UNC `\\srv\`; complete-UNC controls `\\srv\share`, `\\srv\share\leaf`, `//srv/share/leaf`, `\\srv\\share`, `\\.\leaf`); Node + Python + Rust |

Evidence, ledger and summarizers: `data/l12-d013/scoping/` (`SHA256SUMS`).

### 3.1 Results

- **Pinned Node.**
  - A result depends only on the cwd form and the input. The provider cwd and the inherited entries never changed it: 456/456 observations in run 1 and 800/800 in run 2.
  - Every drive-less rooted input took the process cwd's device: `E:\leaf`, `\\?\E:\leaf`, `\\localhost\E$\leaf`.
  - The incomplete UNC forms were treated as a whole tail: `\\leaf` → `E:\leaf`, `\\srv\` → `E:\srv`, `\\\leaf` → `E:\leaf`.
  - The complete UNC inputs kept their own device: `\\srv\share` → `\\srv\share\`, and `\\srv\\share` → `\\srv\share\`.
- **Rust** (`83a78655` code): **800/800 equal to Node** in run 2, across every cwd form including the UNC and the extended cwd.
- **Merged Python:** not equal to Node in every combination.

  | Python mismatch class | Example (Node → Python) | Cause |
  |---|---|---|
  | M1: the device comes from the provider | `\leaf`: `E:\leaf` → `C:\leaf`; extended cwd `\\?\E:\leaf` → `C:\leaf`; UNC cwd `\\localhost\E$\leaf` → `C:\leaf` | `os.path.isabs('\\leaf')` is false on Python 3.13, so the input goes through `os.path.join(provider_cwd, p)` |
  | M2: an incomplete UNC is kept as UNC | `\\leaf` → `\\leaf\`; `\\srv\` → `\\srv\\`; `//leaf`, `\/leaf`, `/\leaf`, `\\\leaf` similarly | ntpath's UNC split differs from Node's root parse |
  | M3: repeated separators inside a complete UNC root | `\\srv\\share`: `\\srv\share\` → `\\srv\\share` | ntpath does not collapse the separator run between server and share |

  Equal rows: only the complete-UNC controls `\\srv\share`, `\\srv\share\leaf`, `//srv/share/leaf` and `\\.\leaf` (4 of 25), plus the M1 inputs when the provider and process drives agree (18/25 for the `E:\y` provider with a plain or root cwd).

## 4. Proposed shared statement (spec §3.2, win32; DIRECT_PI_PARITY)

> On win32, an input absolute under Node's `path.win32.isAbsolute` is resolved as Node's `path.win32.resolve(input)`. In particular:
>
> - A **complete UNC root** is exactly two leading separators, a non-empty server, one or more separators, then a non-empty share; either separator may be used. It is the result's device. The rest is normalized. The root is emitted with single `\` separators and a trailing `\` when the tail is empty.
> - An input whose root has **no device** is resolved against the **process cwd's device**: a leading `\` or `/` that does not complete such a root, or a double-separator form that is not a complete UNC root.
>   - The device comes from the same root parse of the process-cwd native operand (CE-L12D012-02 R1): `X:`, `\\server\share`, or a namespace root such as `\\?\E:`.
>   - The provider cwd and inherited `=X:` entries play no part.
>   - The tail is the input after its one-unit root. For a double-separator form that is not a complete UNC root, the whole input is the tail.
> - The result is `device\` plus the normalized tail: `.` and empty segments dropped, `..` clamped at the root, `\` emitted.
> - A process-cwd read failure is the existing typed error.

This uses no Python or Rust mechanics. The drive-letter, drive-relative (L12-D012) and relative-input rules are unchanged.

## 5. Proposed canonical additions

The new rows are host cases using the existing crafted-child mechanism, with verified preconditions: the process-cwd drive is not the provider's, and the cwd form is as stated. They refuse fail-closed. Expectations are generated from pinned Node only.

| Group | Inputs | Purpose |
|---|---|---|
| R1 process device | `\leaf`, `/leaf`, `\`, `\..\leaf`, `\a\b\..\c` with provider `C:\x` and a process cwd on another drive | M1 |
| R2 incomplete UNC | `\\leaf`, `//leaf`, `\\srv\`, `\\\leaf` | M2 |
| R3 complete-UNC control | `\\srv\share\leaf`, `\\srv\share`, `\\srv\\share` | used as-is; M3 |
| R4 extended cwd | `\leaf` with cwd `\\?\E:\…` | the namespace device |

A UNC process cwd is characterized here (`\\localhost\E$`), but it is **not proposed as a canonical host case**, because it depends on the admin share. It is recorded as a characterization witness only.

## 6. Plan and stop condition

1. Independent scoping review (Codex) of §§2–5 and the evidence.
2. Shared cases plus the Python correction (M1–M3) on paired candidates, then independent Python review.
3. Rust revalidation against the new cases. Rust already matches 800/800, so a new Rust code change is not expected.
4. Closure. `#236` (the home source) stays separate.

## 7. Scoping review 1 and the contract candidate

Codex's independent scoping review 1 (`#235` issuecomment-6187901717) **APPROVED** scoping 1 for contract and corpus drafting at `d3d5d82c`. It accepted M3 explicitly in scope and set five requirements for the candidate. This section answers each one. The corpus counts and expectations below are filled in from the generation run (§7.3).

### 7.1 The contract delta

| Artifact | Change |
|---|---|
| `spec/execution.md` §3.2 | The rooted and UNC-root statement of §4, which applies to the post-`~`/`file://` logical input at Pi's unchanged absolute-or-relative decision. It names the spawn-cwd consumer. |
| `conformance/schema/path-resolution-scenario.schema.json` | Host cases may carry `cwd_form` (`ordinary`, the default, or `extended`). An extended case has `drive: cwd`, `entry: null` and no `cwd_tail` part. Templates are filled from the **ordinary** sandbox path. The runner verifies the observed child cwd spelling and refuses otherwise. |
| `conformance/agent/path-resolution/path-resolution.json` | The 80 L12-D012 cases are unchanged and in order (the merge refuses otherwise). It appends 19 Node-generated cases: `win32/baseline/rooted-01..04` (R3, complete UNC, independent of every cwd); `win32/host/rooted/01..09` (R1 and R2, ordinary child cwd); `win32/host/rooted-extended/01..02` (R4, `\\?\` child cwd); `linux/baseline/rooted-01..04` (POSIX no-regression). |
| `pi-parity-manifest.yaml` | EXEC-002 and EXEC-005 entries `fs_path_resolution_rooted_and_unc_root`, CONTRACT_DRAFT, Python REVALIDATE_REQUIRED (`L12D013-F001`), Rust revalidation. |
| `tests/conformance/test_schema_validation.py` | The shape is 99 cases with group counts, and the first 80 cases are unchanged. There are 4 new schema mutations for `cwd_form`. |
| `data/l12-d013/gen/` | The generator, merger and launcher. The launcher checks the actual Node version, the pinned Pi blob, the provisioned image id and the container's Node version before its first write. |

### 7.2 The five requirements

1. **Placement.** The statement applies to the input after `~` expansion and `file://` conversion, at Pi's existing `isAbsolute ? resolve(p) : resolve(cwd, p)` decision. Neither step moves, and no logical string is projected.
2. **Cwd form in the schema and runner.** This is `cwd_form` as described in §7.1. Each binding's runner launches the child at `\\?\` + the ordinary sandbox path for `extended`. It verifies that the child reports exactly that spelling and that the drive is not `C:` (the provider's). Otherwise it REFUSES. Expectations stay Node-generated, and the adapters stay thin.
3. **Named negative controls.** They are required of the Python implementation candidate. Each has a green baseline, a paired positive and the intended failure:

   | Control | Wrong behavior | Killed by | Paired positive |
   |---|---|---|---|
   | D013-C1 provider-drive substitution | a device-less root takes the provider cwd's drive | `win32/host/rooted/01` (`\leaf`) | `win32/baseline/rooted-01` (`\\srv\share\leaf`, own device) |
   | D013-C2 incomplete-UNC retention | `\\leaf` and `\\srv\` are kept as UNC (ntpath split) | `win32/host/rooted/06` (`\\leaf`) and `/08` (`\\srv\`) | `win32/baseline/rooted-01` (`\\srv\share\leaf`) |
   | D013-C3 separator run kept | the server–share separator run is not collapsed | `win32/baseline/rooted-03` (`\\srv\\share`) | `win32/baseline/rooted-02` (`\\srv\share`) |
   | D013-C4 namespace stripped / wrong cwd operand | the extended process cwd loses `\\?\` | `win32/host/rooted-extended/01` | `win32/host/rooted/01` |

   The existing L12-D012 cases and native-boundary controls stay in place and unchanged.
4. **UNC process cwd.** The admin-share cwd stays characterization only. Permanent coverage of a `\\server\share` process-cwd device sits at the pure root-parser seam: each binding's port is driven in-process with an injected process cwd, as the L12-D012 port tests already do. Nothing foreign is mutated. The process-cwd failure mapping stays covered by the existing L12-D012 witnesses.
5. **EXEC-005 consumer.** Each binding adds a spawn-cwd witness: a rooted spawn `cwd` resolves through the same rule. Rust revalidates against the merged cases with fresh evidence and independent review, and the 800 archived matches do not replace that.

**Merge plan (for the reviewer's decision).** Merging the corpus alone would put rows on main that merged Python fails (M1–M3). I propose keeping the contract pair unmerged after contract approval and adding the Python correction on the same branches. The pair would merge only after the independent Python implementation review, so main's gates stay green. The alternative is to merge the contract with these rows marked as known Python failures, and I don't propose that.

### 7.3 Generation run

The run was granted by Codex (combined #236/#235 window, 2026-10-15) and is recorded as `gen-1`. Codex confirmed the launcher on paper before the grant: `run-gen.mjs` `70b3ae31…`, `gen_rooted.mjs` `39115db4…`, `merge_rooted.mjs` `60ad55ea…`.

- **Preflights before the first write:**
  - host Node v22.15.1;
  - `ref-repos/pi` `nodejs.ts` blob equal to `b7bb00b9:packages/agent/src/harness/env/nodejs.ts` (`1225efb9`);
  - the provisioned image id `ec318fe0…`;
  - container Node v22.15.1.

  A failing check command exits 1 and an explicit mismatch exits 3. Both stop before any write.
- **Windows.** Node children ran from two fs-guard-contained cwds (`.tmp/claude-scratch/i235/gen-1/cwd-a`, `cwd-b`, both on `E:`) and from their `\\?\` spellings. Each child verified its exact cwd spelling and the absence of any `=`-prefixed entry. Every template was proven against both cwds.
- **Linux.** One container ran with `--read-only --network none --pull never`, a private `/tmp`, and read-only binds of `ref-repos/pi` and the generator directory.
- **Outputs:**
  - `run-gen-1/win32-partial.json` `f5adff47…` and `run-gen-1/linux-partial.json` `1bb0e1e3…`;
  - the canonical corpus `path-resolution.json`, 99 cases, `da78a095…`, written through `assertOutput`.

  The merge proved the first 80 cases unchanged. Nothing was deleted.
- **Schema.** The whole document validates against the candidate schema (`ffd562dc…`), with 0 errors (`show_gen.py`).

| Case | cwd form | Input | Pinned Node expectation |
|---|---|---|---|
| `win32/baseline/rooted-01` | — | `\\srv\share\leaf` | `\\srv\share\leaf` |
| `win32/baseline/rooted-02` | — | `\\srv\share` | `\\srv\share\` |
| `win32/baseline/rooted-03` | — | `\\srv\\share` | `\\srv\share\` |
| `win32/baseline/rooted-04` | — | `//srv/share/leaf` | `\\srv\share\leaf` |
| `win32/host/rooted/01`–`05` | ordinary | `\leaf`, `/leaf`, `\`, `\..\leaf`, `\a\b\..\c` | `<D>:\leaf`, `<D>:\leaf`, `<D>:\`, `<D>:\leaf`, `<D>:\a\c` |
| `win32/host/rooted/06`–`09` | ordinary | `\\leaf`, `//leaf`, `\\srv\`, `\\\leaf` | `<D>:\leaf`, `<D>:\leaf`, `<D>:\srv`, `<D>:\leaf` |
| `win32/host/rooted-extended/01`–`02` | extended | `\leaf`, `\\leaf` | `\\?\<D>:\leaf` |
| `linux/baseline/rooted-01`–`04` | — | `/leaf`, `//leaf`, `\leaf`, `\\srv\share` | `/leaf`, `/leaf`, `/x/\leaf`, `/x/\\srv\share` |

`<D>` is the `cwd_drive` (upper) part, the drive of the ordinary child sandbox. Every expectation agrees with the scoping characterization (§3.1). The ledger is `data/l12-d013/gen/SHA256SUMS`.

**Disclosed.** The corpus `notes` keeps its L12-D012 opening ("section 3.2 … unchanged") and gains an L12-D013 suffix. It isn't hand-edited, because the generated document must stay reproducible from the reviewed merger. §3.2 itself is changed by this candidate.

**Expected state of the candidate.** Merged Python does not implement this rule (M1–M3), and its runner does not yet read `cwd_form`. The Python conformance suite is therefore expected to fail the new win32 rows, and its case-count assertion (55/25), on this contract-only head. That is the REVALIDATE_REQUIRED state, not a test-infrastructure defect. The Python correction and runner support are added on the same branches after contract approval (merge plan above). Codex's schema/manifest validation suite is the gate for this contract head.

## 8. Contract review 2 and candidate 2

Codex's independent contract review 2 (`#235` issuecomment-6200287886) **requested changes** at code `dc57331d` / docs `d4adb121`. It found two blocking `CONTRACT_ASSURANCE_DEFECT`s and one non-blocking item. It found the rest of the contract faithful to Pi: the win32 statement, R1–R4, C1–C4, the UNC-cwd port seam, the EXEC-005 requirement and the merge plan. Candidate 2 is the narrow remediation below. Nothing else changes. The 99 case objects are identical to candidate 1, and the 80 inherited cases are still unchanged and in order.

### 8.1 C001: the extended-cwd restriction now covers `input`

- **Defect.** The schema enforced "an extended case uses no `cwd_tail` part" only on `expect`. An extended case with `input` `{"parts": [{"cwd_tail": true}]}` validated with zero errors.
- **Repair.** The schema has a new `$defs/no_cwd_tail`. The case-level extended conditional applies it to **both** `input` and `expect`. The `drive: cwd` and `entry: null` restrictions are unchanged. No runner compensates for it.
- **Permanent witnesses** in `test_schema_validation.py`:
  - **Rejected:** the existing `expect` mutation, and a separate new `input` mutation (Codex's exact witness);
  - **Accepted:** a `cwd_tail` part in `input` or in `expect` of an ordinary-cwd host case, with `cwd_form: ordinary` and with `cwd_form` absent (4 parametrized positives).

### 8.2 C002: M4 is in scope

- **The authority rule is unchanged.** Pinned Pi resolves an absolute POSIX input as Node's `path.posix.resolve(input)`, which collapses any run of leading `/` to one. The candidate-1 spec sentence "a leading `/` is absolute and used as-is" read as if POSIX needed no normalization. It now says the input is normalized as `path.posix.resolve`, so `//leaf` is `/leaf`. This clarifies the wording and changes no rule.
- **Merged Python needs a correction there.** "POSIX unchanged" (§2, §6, §7.1's "POSIX no-regression") describes the authority. It does not claim that merged Python is correct on POSIX:
  - Python's `resolve_local_path` absolute branch uses `os.path.normpath`;
  - POSIX `normpath` keeps exactly two leading slashes;
  - so `//leaf` gives `//leaf` where Node gives `/leaf`.

  This is **M4**, found in the `#236` Linux characterization and confirmed independently by contract review 2. It is a required-parity correction, not an accepted divergence.

| Python mismatch class | Example (Node → Python) | Cause |
|---|---|---|
| M4: two leading POSIX slashes kept | `//leaf`: `/leaf` → `//leaf` | `posixpath.normpath` preserves exactly two leading `/` |

- **Scope and plan.** §6 step 2 and the §7.2 merge plan now cover M1–**M4**. The Python correction on the same branches fixes M4 in the shared resolver. It also checks the EXEC-005 consumer (the effective spawn `cwd`) for the same resolver.
- **Revalidation.** Python REVALIDATE_REQUIRED (`L12D013-F001`) covers win32 (M1–M3) **and POSIX (M4)**. Both manifest entries say so now; candidate 1 said "Python on win32" only. The Python revalidation runs the merged corpus natively on win32 and on Linux.
- **Control.** This adds to §7.2's table. Like C1–C4, it is a requirement of the implementation candidate and is not credited as executed here:

  | Control | Wrong behavior | Killed by | Paired positive |
  |---|---|---|---|
  | D013-C5 two POSIX leading slashes kept | an absolute POSIX input keeps exactly two leading `/` | `linux/baseline/rooted-02` (`//leaf` → `/leaf`) | `linux/baseline/rooted-01` (`/leaf`) |

  It runs after a green baseline, as C1–C4 do.
- **Cases.** `linux/baseline/rooted-02` and its Node-derived expectation are unchanged. No new canonical case is needed.

### 8.3 N001: the corpus `notes` opening

The merger no longer carries the stale L12-D012 opening ("section 3.2 (DIRECT_PI_PARITY), unchanged;"). It now writes "…, as amended by L12-D013;", and refuses if the inherited prefix is not found. The JSON was not hand-edited:
- the merger was rerun alone (`node merge_rooted.mjs`, host Node v22.15.1), over the code `HEAD^` 80-case corpus and the unchanged, reviewed `run-gen-1` partials;
- this is pure stdout computation, with no child, resolver run or Docker.

The output differs from candidate 1's corpus only on the `notes` line: every case object and `authority` are identical.

| Artifact | Candidate 1 | Candidate 2 |
|---|---|---|
| `gen/merge_rooted.mjs` | `60ad55ea…` | `5884dcd5…` (ledger updated; 6/6 entries verified) |
| `path-resolution.json` (99 cases) | `da78a095…` | `17aac054…` |
| `path-resolution-scenario.schema.json` | `cb6c3d58…` | `601f07e0…` |

All hashes are SHA-256 of the committed content, which has LF line endings. Correction: §7.3's schema hash `ffd562dc…` is the CRLF working-copy spelling of the same candidate-1 blob, whose committed content is `cb6c3d58…`. The ledger and corpus hashes in §7.3 were already of LF content.

The §7.3 disclosure about the stale opening is superseded by this item.

### 8.4 Expected state of candidate 2

This is unchanged from §7.3, with M4 added. Merged Python is expected to fail the new win32 rows and `linux/baseline/rooted-02` on this contract-only head. The schema and manifest suites are the gate for the contract head.

### 8.5 Contract-head gate and disclosure

- **Gate.** This ran in a Codex-granted 5-minute Windows window (`#209`, 2026-10-16). It was sequential pytest only, at code `4bc4754c` with a clean tree, with candidate `src` on `PYTHONPATH`. Coverage was off (`-o addopts=""`), and basetemps and TMP were under `.tmp/`.
  - `test_schema_validation.py -k path_resolution`: **24 passed**, 931 deselected (the schema file only).
  - `test_schema_validation.py` plus `test_manifest_validation.py`: **963 passed**. That is review 2's 958 plus the 5 new tests (1 rejection and 4 positives).

  There was no Cargo, Docker or child process.
- **Disclosed and not credited.** Before asking for that window, I ran the focused schema file once at the uncommitted state with no host window, which breaks the `#209` rule. Its result was buried in the coverage report and is not credited. Codex's grant does not authorize that run after the fact. Its only artifact is the gitignored `.coverage` file inside the code worktree.
- **Merge rerun (§8.3).** This was a single pure-Node stdout computation with no child process, and it ran outside a window. It is disclosed here for the same reason.

## 9. Contract review 3 and the Python implementation

Codex's contract re-review 3 (`#235` issuecomment-6200544181) **APPROVED** contract candidate 2 (code `4bc4754c` / docs `4078f87e`) for the Python implementation, and closed C001, C002 and N001. The implementation is on the same unmerged branches, as the merge plan says. `L12D013-F001` stays open until independent review.

### 9.1 The Python correction

All of it is in `resolve_local_path` (`minion_agent/execution/filesystem.py`), the one resolver behind `ctx.fs` and the `ctx.shell`/`ctx.subprocess` spawn cwd:
- **win32, M1–M3.** After the `~`/`file://` steps and the L12-D012 drive-relative branch, an input whose first unit is `\` or `/` is `node_win32_resolve([input])`. That is the existing literal port of Node's `win32.resolve`, given the input **alone**.
  - Its only host operand is the process cwd through the existing native view (CE-L12D012-02).
  - The inherited-entry hook is passed, but the port never consults it for a single absolute argument.
  - A complete UNC root is its own device, and every other root takes the process cwd's device.
- **POSIX, M4.** The result of both branches passes through `node_posix_single_root`, which reduces any run of leading `/` to one, as `path.posix.resolve` does.
  - The absolute branch is the corpus case `linux/baseline/rooted-02`.
  - The relative branch (a provider cwd spelled `//x`) is the same Node rule. Its values come from pinned Node itself: the gate's `node-posix` check printed `["/x/a","/leaf","/"]` for `resolve('//x','a')`, `resolve('/x','//leaf')` and `resolve('//x','..')`.
- **Removed.** `L12-PY-R002`'s bare-root trailing-separator fix-up. A bare UNC root now takes the port, which emits that separator itself, and a bare `C:` is not absolute. The block became unreachable, and run 1 showed it as the one uncovered line.

### 9.2 Runner, witnesses and controls

- **Runner** (`tests/conformance/path_resolution_runner.py`, thin):
  - For `cwd_form: extended` it launches the child at `\\?\` + the ordinary sandbox path.
  - It REFUSES unless the child reports exactly that spelling: no case-folding and no other namespace.
  - It fills templates from the ordinary sandbox path. Ordinary cases are unchanged.
  - Case counts are 70 on win32 and 29 on linux.
- **Rooted classes through the real resolver.** On win32, each of the 15 rooted cases runs through `resolve_local_path` with an injected synthetic process cwd. Any inherited-entry read fails the test. The canonical host cases also run in real crafted children.
- **Node-recorded port fixture** `tests/execution/data/node_rooted_cwd.json` (`ef273b41…`):
  - It is frozen from the scoping capture `rooted-probe-2.json` by `impl/build_fixture.py`, which refuses if Node's result varies within a cwd form.
  - It holds 25 inputs × 4 process-cwd forms: drive root, plain, extended, and the UNC admin share `\\localhost\E$\…`. That covers §7.2 item 4 at the pure seam, without the UNC path ever being used as a real cwd.
  - On win32 the real resolver also reproduces all 100 rows under each of the 4 characterized providers.
- **EXEC-005 consumer.** `test_exec005_rooted_spawn_cwd_uses_the_process_device` spawns a child with provider cwd `C:\never-used` and the rooted spelling of a contained `tmp_path`. The child must start in `tmp_path`, on the process drive; merged Python's M1 would have chosen `C:`.
- **Controls**, each with a green baseline and its paired positive green under the wrong behavior:

  | Control | Wrong behavior installed | Killed by | Paired positive |
  |---|---|---|---|
  | D013-C1 | the process-cwd operand replaced by the provider `C:\x` | `win32/host/rooted/01` | `win32/baseline/rooted-01` |
  | D013-C2 | ntpath's UNC split as the root parse | `win32/host/rooted/06` and `/08` | `win32/baseline/rooted-01` |
  | D013-C3 | the raw server/share separator run kept in the device | `win32/baseline/rooted-03` | `win32/baseline/rooted-02` |
  | D013-C4 | the extended process cwd's `\\?\` stripped | `win32/host/rooted-extended/01` | `win32/host/rooted/01` |
  | D013-C5 | `node_posix_single_root` as the identity (two leading `/` kept) | `linux/baseline/rooted-02` | `linux/baseline/rooted-01` |

  There are also runner refusal controls: an extended child reporting the ordinary, case-folded or `\\.\` spelling is REFUSED, and the exact spelling is admitted. The D012 native-boundary controls and regressions are unchanged and still run.

### 9.3 Gate launchers

The Python gate launchers were rebuilt after two Codex paper checks.
- **First check:** the #229-derived shell launchers were refused because of unchecked run names, a cleanup-capable basetemp, a non-fatal preflight and a writable `/out` bind.
- **Second check:** the rebuilt launchers were refused because of spawn timeouts and buffer limits that could terminate a gate, and incomplete bundle parsing.

The approved launchers (`impl/gates/`) do the following:
- They use the reviewed fs-guard only, with plain new run names.
- Every input is proven before any mkdir, and every Linux bind is re-proven immediately before Docker.
- Every log is opened `wx` right after its `assertOutput` proof and receives the gate's output directly, with no buffer, no timeout and no automatic termination.
- pytest's basetemp is proven contained and missing before pytest starts. A failed preflight refuses.
- Linux has only read-only binds, and its nonce bundle is parsed byte-complete before anything is published.

The intercepted controls passed before the first gate: `win-controls.mjs` 18/18 and `linux-controls.mjs` 29/29 (outputs `gates/*-controls-1.txt`). Runs 2 and 3 carry that execution at the same hashes; it was not rerun.

### 9.4 Gates (Codex-granted windows, 2026-10-16)

| Run | Code head | Windows | Linux (`python:3.13`, uid 1000) |
|---|---|---|---|
| 1 | `83481021` | pytest 7330 passed / 0 failed, but coverage 99.99% (the removed line); ruff 4 × E501; format of 1 changed file | 6654 passed / 0 failed; ruff 4 × E501 |
| 2 | `3265d040` | pytest 7330 / 0, coverage 100%; ruff 1 × E501 (my rewrap moved the overflow) | 6654 / 0; ruff 1 × E501 |
| **3** | **`aefc67e3`** | **preflight, icu, ruff, format of changed files, mypy (118 files), pytest 7330 passed / 0 failed / 47 skipped / 19 xfailed with coverage 100.00%: all exit 0** | **icu-build, pip, versions, ruff exit 0; pytest 6654 passed / 0 failed / 670 skipped / 19 xfailed** |

Each run recorded every exit as-is, and nothing was fixed or rerun inside a grant. Run 3 is the credited tier. Two Linux exits are nonzero and identical to the accepted `#229` Linux baseline:
- pytest exits 1 on the coverage gate alone (96.74%), because 100% is gated on Windows;
- mypy exits 1 with the same 15 errors (win32 `ctypes` attributes and the missing `jsonschema` stubs), line-for-line equal to `#229`'s and to run 2's.

The whole-tree format check lists the same 7 pre-existing files as `#229`, none of them touched here. The logs are in `impl/gates/win-3`, `impl/gates/linux-3` and `impl/gates/history` (ledger `impl/SHA256SUMS`).

### 9.5 Open point for the implementation review: a process-cwd read failure

- **Contract.** Spec §3.2 says a failure to read the process cwd is "the existing typed error", and spec §2 makes normalizing a bare `OSError` the provider's obligation.
- **Merged Python.** `os.getcwd()` failing inside `resolve_local_path` escapes as a bare `OSError` from every `ctx.fs` operation and from the spawn-cwd resolution. This was already true of the L12-D012 drive-relative branch, and it is now also true of the rooted branch.
- **Not invented here.** Neither the contract nor CE-L12D012-02 names the code or path of that typed error for Python, so this candidate does not invent one.
- **Reachability.** On win32 a process cwd cannot be removed while the process holds it, so the read is not expected to fail in practice. POSIX never reads it in this branch.
- **Proposal.** Record it as a Python finding for the reviewer's disposition: either a separate work package, which specifies the `FsError`/`ShellError`/`SubprocessError` mapping across every operation, or a statement that it is accepted as is.

### 9.6 Disclosures

- The M4 helper is also applied to the relative branch. This goes beyond the one corpus row, and its values are Node-recorded (§9.1).
- The EXEC-005 witness covers `ctx.subprocess`. `ctx.shell` uses the same `resolve_local_path` call for its cwd (`shell.py`) and has no separate witness here.
- The two refused launcher designs never executed.

### 9.7 State

*(Superseded by §13.1.)*

- Python Layer-12 delta L12-D013: implemented, **PENDING INDEPENDENT REVIEW** (`L12D013-F001` open).
- Rust: revalidation against the merged cases after merge.
- L12-D013 cross-language: **NOT CLOSED**.

*(Historical. The phrase "Python is not corrected yet" in the opening status line described the contract phase; §9 is the implementation.)*

## 10. Implementation review 4, `L12D013-PY-I001` and the DIV-009 amendment

Codex's implementation review 4 (`#235` issuecomment-6201717410) **requested changes** at code `aefc67e3` / docs `7094e652`.
- **Accepted (the success path):** the M1–M4 correction, the runner, the fixture provenance, controls C1–C4 (rerun by the reviewer) and C5 (installed on the production seam).
- **One blocking finding, `L12D013-PY-I001`** (`CONTRACT_ASSURANCE_DEFECT`): spec §3.2 promised "the existing typed error" for a failed native process-cwd read, but no such typed outcome exists.
  - Python lets the original `OSError` escape. The reviewer showed this with an injected read failure through `absolute_path`, `file_info`, `ctx.subprocess.spawn` and `ctx.shell.exec`, checking exception identity.
  - Pinned Pi itself propagates the exception, so a new catch is not `DIRECT_PI_PARITY`.

### 10.1 Correction of a false claim

§7.2 item 4 said: "The process-cwd failure mapping stays covered by the existing L12-D012 witnesses." **That is wrong for Python.** No Python witness covers a failed read, and merged Python has no mapping (§9.5). The sentence stays in §7 as history and is withdrawn here.

### 10.2 Owner decision

The Owner decided the finding as an intentional practical-parity divergence, **`DIV-009`**: "APPROVE OPTION 1: TYPED FAILURE, DIV-009". It is recorded verbatim at `#235` issuecomment-6205758223 (sha256 `77cd22f3…`), superseding the short summary at issuecomment-6205744819. It includes:
- the normative rule;
- the Rust reconciliation;
- scope and precedence;
- the required witnesses and negative controls;
- ten governance steps, of which step 7 is independent agreement on the revised contract before any production change.

It is a scoped amendment within L12-D013, with no separate work package.

### 10.3 Characterization (read-only; source, plus the reviewer's executed witnesses)

| Seam | Pinned Pi | Merged Python | Rust (reviewed; not modified) |
|---|---|---|---|
| `ctx.fs` (every operation) | `resolvePath` first, outside any `try`; the throw rejects the operation | `resolve_local_path` first, in all 16 resolver-using methods (and again in the NUL wrapper); the `OSError` escapes | `resolved()` → `map_fs_error`: typed `FsError`, **no path** |
| `ctx.shell.exec` | pre-abort, timeout, then `resolvePath` (`nodejs.ts:376`), before shell config and the `access` catch; the throw rejects | same order; the `OSError` escapes | same order; `ShellError(SpawnError, error.to_string())` |
| `ctx.subprocess.spawn` | no Pi seam (Minion extension) | pre-abort, then resolution, then the §21 checks; the `OSError` escapes | pre-abort, the empty-argv check, then resolution; `map_spawn_error` → `spawn_error` |

**Where the read happens (lazy).**
- win32: the rooted or incomplete-UNC branch (L12-D013), and the L12-D012 drive-relative branch when the inherited `=X:` entry is absent or empty.
- Never: for a complete UNC root, `X:\…`, or a relative input against an absolute provider `cwd`.
- POSIX:
  - Pinned Node and Rust read it only when **no argument is absolute**, that is, a relative or empty provider `cwd` with a relative input.
  - **Merged Python never reads it on POSIX.** It joins the two relative strings instead. That is a separate, pre-existing difference for a non-absolute provider `cwd`. It is recorded here as an observation only and not reopened, per the decision's scope.
  - The DIV-009 rule applies wherever a binding's resolver reads the cwd. Making Python read it there would be a path-resolution change outside this amendment.

**Observations the implementation must handle.**
- **The NUL wrapper.** In Python, the L12-D006 NUL wrapper (`_contain_nul`) resolves the arguments a second time, inside its own `ValueError` handler. A failing cwd read there must not escape either.
- **Empty argv.** With an empty argv and a failing read, the two bindings' subprocess orders differ (Rust's empty-argv check comes first). That edge lies outside this amendment's precedence rule, which keeps each existing earlier check.
- **Reachability.** On win32 the real process cwd cannot be removed while the process uses it, so every witness injects the failure at the native-read boundary. No real directory is deleted or invalidated.

### 10.4 The amendment (this candidate; docs and manifest only)

- **`spec/execution.md`:**
  - §2 gains one paragraph that names the only point where pinned Pi's implementation leaves the `Result` boundary, and points to §22.
  - §3.2's "the existing typed error" is corrected to `DIV-009`'s typed failure, with a correction note.
  - **New §22** states the rule: where the read happens (unchanged and lazy), the typed failure per seam (code and diagnostic from the original native error; `path` = the caller's logical argument as passed; `rename_file` source before destination; `spawn_error` with no process created), precedence (unchanged), what stays an exception, and what is unchanged.
- **`assurance/pi-divergences.md`:** a new `DIV-009` entry and table row (APPROVED by the Owner; witnesses pending).
- **`pi-parity-manifest.yaml`** (code): a new row `EXEC-002-DIV-009`, disposition `intentional divergence`, plus `EXEC-004` and `EXEC-005` traceability lines. Python is REMEDIATION_REQUIRED. Rust is REVALIDATE_REQUIRED for this surface only.

### 10.5 Planned witnesses and controls (the remediation after agreement)

All failures are injected at each binding's native process-cwd read boundary (Python: `_native_process_cwd_view`). Witnesses run through the real public seams and need no destructive fixture.

- **Witnesses:**
  - win32 rooted (`\leaf`, `\\leaf`) and L12-D012 drive-relative inputs (absent and empty entry), each read failing with ENOENT, with permission denied, and with another OS error;
  - each observed `code`, diagnostic and `path`;
  - the caller's path preserved exactly, including a lone-surrogate value and a `file://` or `~` spelling (`path` is the argument as passed);
  - `absolute_path`, `file_info`, `rename_file` (a failing source, then a failing destination) and the other resolver consumers;
  - `ctx.shell.exec` and `ctx.subprocess.spawn`, with a fail-if-reached native spawn spy;
  - abort precedence: `ctx.fs` reports the read failure under an aborted signal; the shell and subprocess pre-abort checks still decide first;
  - timeout validation first, then the §21 NUL checks after resolution;
  - no side effects, through filesystem call spies;
  - lazy-read controls: complete UNC, `X:\`, a non-empty inherited entry, and POSIX absolute inputs never read the cwd;
  - the NUL-wrapper second resolution;
  - pinned-Pi-versus-Minion rows: the pinned slice on Node with a throwing `process.cwd` (a rejection) beside the binding's typed result.
- **Negative controls**, each with a green baseline and a named killing witness:
  1. leak the raw `OSError`;
  2. a fixed wrong code (for example everything `unknown`);
  3. omit `path`;
  4. substitute the provider `cwd` for the caller path;
  5. read the cwd for a complete-UNC or `X:\` input;
  6. catch every exception, so an injected `TypeError` or `AssertionError` would be swallowed;
  7. retry with a fabricated cwd;
  8. start a process despite the failure.
- **Rust:** revalidation of this surface only, after the shared merge. The `ctx.fs` mapping gains the caller's logical path, and existing codes, laziness and typed shell/subprocess handling are preserved.

### 10.6 Review requested

This is independent agreement on the revised contract (§10.4, decision step 7), before the Python remediation changes any production behaviour.

### 10.7 Documentary corrections (review 4, non-blocking)

§9.4 says the Linux mypy errors are "line-for-line equal" to `#229`'s. The precise statement: they are the **same 15 diagnostics, modulo source-line offsets**. The `filesystem.py` lines moved by +13, for example 982 → 995. There is no new mypy error.

## 11. The DIV-009 Python remediation (after CE-L12D013-01)

Contract review 5 (issuecomment-6205917076) fired trigger A and opened convergence episode CE-L12D013-01. After the Owner's `rename_file` amendment (issuecomment-6206113367), the checkpoint `12-l12-d013-convergence-ce01.md` was **agreed for implementation** by checkpoint review 6 (issuecomment-6206812375). This section records the remediation. `L12D013-PY-I001` and `L12D013-F001` stay open until targeted closure.

### 11.1 Implementation (code; production modules `filesystem.py`, `shell.py`, `subprocess.py`)

- **The one converted boundary.** `resolve_local_path` passes the port a reader that calls the native process-cwd view.
  - Only an `OSError` raised by that read becomes `ProcessCwdReadError`. It carries the native error (also chained as `__cause__`) and the caller's argument exactly as passed.
  - It is not an `OSError` subclass, so no unrelated handler can reclassify it.
  - Every other exception propagates, as K6 witnesses.
  - The read point and its laziness are unchanged. The no-read rows run with a fail-if-called reader.
- **`ctx.fs`.** All 16 resolver-using methods carry `@_typed_cwd_failure`, which returns `Err(to_pi_fs_error(native, raw argument))`. That is the native classification and diagnostic, with the native error as `cause`.
  - Resolution precedes every abort check and native call, so nothing native follows the failure. A spy on `asyncio.to_thread` witnesses this.
- **Origin-sensitive propagation.** A private mark on the native error identifies a DIV-009 failure:
  - `exists` returns it instead of `Ok(False)`;
  - `resolve` returns it instead of falling back to `absolute_path`;
  - native `lstat` and `realpath` outcomes keep their behaviour, paired by witnesses.
- **The NUL error path** (L12-D006) reuses the resolutions the operation recorded during the call, through a per-call context variable. It never resolves again.
  - A `ValueError` from before any resolution is re-raised unchanged.
  - Effects made earlier (`write_file`'s and `append_file`'s parent creation) stay.
- **`rename_file`:** source, destination, abort, rename, by the Owner amendment.
- **`ctx.shell.exec`** and **`ctx.subprocess.spawn`** return `spawn_error` carrying the native failure, at their resolution step. Neither shell discovery nor a native process creation follows.

### 11.2 Permanent witnesses and controls (`tests/execution/test_div009_cwd_read_failure.py`)

- **Reading rows:** every NP cell class of the checkpoint's §2 matrix (rooted and incomplete-UNC inputs under all seven provider forms, and other-drive and same-drive inputs with an absent or empty entry), each with four native errors:
  - ENOENT → `not_found`;
  - permission denied → `permission_denied`;
  - Win32 87 → `invalid`;
  - EIO → `unknown`.

  Each row asserts the code, the diagnostic, the raw `path`, `cause` identity and exactly one read.
- **No-read rows:** every no-read cell class, with a fail-if-called reader. On POSIX, merged Python performs no read in any of the 24 rows, a recorded observation that is not certified.
- **The caller's path:** a lone surrogate, a `file://srv/` spelling and a trailing-separator spelling are each reported raw.
- **Every consumer:** all 16 resolver-using methods plus `exists`, through the real seam, with a native-call spy, unsignalled and (for the seven that inspect it) under an aborted signal.
- **Derived operations:** `exists` and `resolve`, each paired with a real native absence.
- **Rename:** R1–R10 of checkpoint §4, plus the successful un-aborted positive (a real rename inside `tmp_path`). Each row asserts the outcome and the number and order of reads. The NUL write and append rows keep their parent effect.
- **Shell and subprocess:** `ctx.shell.exec` with a pre-abort and timeout precedence row; `ctx.subprocess.spawn` with pre-abort, NUL-after-resolution and NUL-only rows, against a spawn spy.
- **Controls K1–K12**, each run against its named witness: the witness is first asserted green, then the wrong behaviour is installed and the same witness must fail.
  - K1 leak the raw `OSError`; K2 a fixed code; K3 omit `path`; K4 the provider `cwd` as `path`; K5 an eager read; K6 catch everything; K7 a fabricated cwd;
  - K8 spawn anyway; K9 the former Python rename order; K10 `exists` returning `false`; K11 the `resolve` fallback; K12 the NUL handler resolving again.
- **Pinned-Pi side:**
  - the read-domain run `rd-1` (checkpoint §2);
  - implementation review 4's executed authority witness (the pinned slice on real Node with a throwing `process.cwd` rejects; reviewer probe `d013-cwd-error-authority-r4.cjs`).

  No new Node probe was added.

### 11.3 Gates (Codex-granted windows, 2026-10-16; launchers unchanged at `7d42b468` / `48b3dbda` / `579b8d52`, their controls carried, not rerun)

| Run | Code head | Windows | Linux (`python:3.13`, uid 1000) |
|---|---|---|---|
| 4 | `f37316b1` | pytest 7770 passed / 0 failed / 81 skipped / 19 xfailed, coverage 100.00%; ruff, mypy, icu, node-posix 0; **format-changed 1** (one ruff reformat of a test call) | 6682 passed / 0 failed / 1116 skipped; ruff 0; coverage and mypy exits at the Linux baseline |
| **5** | **`4cb5b5e2`** | **every gate exit 0**: pytest 7770 passed / 0 failed / 81 skipped / 19 xfailed, coverage 100.00%; ruff, format-changed, mypy (118 files), icu, node-posix | icu-build, pip, versions, ruff 0; pytest **6682 passed / 0 failed** / 1116 skipped (the win32-only rows) / 19 xfailed; coverage-only pytest exit 1 (96.60%, 100% being gated on Windows) and mypy exit 1 (the same 15 diagnostics as runs 3–4, modulo line offsets), both at the established Linux baseline |

Run 5 is the credited tier. The single change from run 4 is that reformat. The whole-tree format check lists the same 7 pre-existing files as `#229`.
- **Logs:** `data/l12-d013/impl/gates/win-5`, `linux-5`, and the run 4 summaries in `gates/history`. The `impl/SHA256SUMS` ledger now has 86 entries, all verified.
- **Manifest status.** The `EXEC-002-DIV-009` row still says Python REMEDIATION_REQUIRED, and its witness entry PENDING. Editing it now would move the code head off the gated `4cb5b5e2`, so the row is updated by the post-closure status sync.

## 12. Targeted closure review 7 and the slot-identity remediation

Targeted closure review 7 (issuecomment-6216781677, at code `4cb5b5e2` / docs `791eaa10`) returned **CHANGES_REQUESTED**. `L12D013-PY-I001` stays open as the same finding, a `PI_PARITY_DEFECT` on the same NUL-handler surface. `L12D013-F001` stays open for the later complete review. This is the first rejected targeted closure after checkpoint review 6, so the two-failure invalidation threshold of kit §11.8.10 has not fired. The review found no new divergence and needed no Owner decision. §11's record stays as it was.

### 12.1 The defect (review 7)

The §11.1 NUL error path recorded each resolution under the key `(cwd, path)` and looked `rename_file`'s two arguments up by that key. With equal source and destination spellings, the destination's resolution overwrote the source's.

The process cwd is mutable process-wide, so the two reads need not agree. Review 7's witness: rooted `\same<NUL>x` for both arguments, reads `E:\proc` then `F:\proc`, and a spy native rename rejecting the NUL. Pinned Pi (`renameFile`, `nodejs.ts:590-599`) reports `toFileError(error, source)`, so the fallback is `E:\same<NUL>x`. Python reported `F:\same<NUL>x`. The read count stayed two, so R10 and K12 could not see it.

Spec 18.1 requires the resolved source fallback, unprojected. Spec 22.2 requires the resolutions already made, not the first replaced by the last.

### 12.2 Remediation (code `07731c8b`, `filesystem.py`)

- The NUL error path records one `(cwd, path, resolved)` entry per resolution, in call order. An entry is an argument slot, not an argument value.
- Each wrapped operation resolves its path arguments once each, in argument order. Slot *i* is therefore entry *i*. The handler classifies the rejection only when entry *i* is argument *i*'s own resolution, and otherwise re-raises.
- Unchanged, as the handback required:
  - nothing is memoized across the two reads;
  - no read is added;
  - the logical fallback is not projected;
  - the rename order is unchanged.

### 12.3 Permanent witnesses and controls (`tests/execution/test_div009_cwd_read_failure.py`)

- **R11 rows.** Each row covers distinct or equal spellings, with stable (`E:`, `E:`) or varying (`E:`, `F:`) reads:
  - distinct-stable;
  - distinct-varying;
  - equal-stable;
  - equal-varying;
  - equal-varying-raw, where both arguments carry a raw lone surrogate.

  Each row goes through the real `rename_file`. A spy replaces `os.replace`, records the two native arguments and raises the host's `ValueError('embedded null character')`, so no filesystem call is made. Each row asserts:
  - `unknown` with the source slot's own logical path, the surrogate kept raw;
  - the spy saw the native projections of the source and destination slots' own resolutions;
  - exactly two reads.
- **Controls K13 and K13-raw.** Each reinstalls a value-keyed, last-wins lookup of the recorded resolutions, using the existing K-control harness against the equal-varying and equal-varying-raw rows. Each witness is first asserted green on the baseline. The same witness must then fail with the control installed.
- **Wrong-slot re-raise.** When the first recorded resolution is of another path, the `ValueError` propagates and is not classified.

### 12.4 Gates (run 6, Codex-granted window, 2026-10-17; launchers unchanged at `7d42b468` / `48b3dbda` / `579b8d52`, their controls carried, not rerun)

| Run | Code head | Windows | Linux (`python:3.13`, uid 1000) |
|---|---|---|---|
| **6** | **`07731c8b`** | **every gate exit 0**: pytest 7778 passed / 0 failed / 81 skipped / 19 xfailed, coverage 100.00%; ruff, format-changed, mypy, icu, node-posix | icu-build, pip, versions, ruff 0; pytest **6683 passed / 0 failed** / 1123 skipped / 19 xfailed; coverage-only pytest exit 1 (96.60%) and mypy exit 1 (the same 15 diagnostics as run 5, modulo line offsets), both at the established Linux baseline |

- **Counts.** Run 6 adds 8 cases to run 5's 7770 on Windows: R11 ×5, K13, K13-raw and the wrong-slot case. On Linux it adds 1, the wrong-slot case. The other 7 are win32-only and skip.
- **Format.** The whole-tree format check lists the same 7 pre-existing files as run 5.
- **Logs.** The logs are `data/l12-d013/impl/gates/win-6` and `linux-6`. The run-5 directories stay as they were. The `impl/SHA256SUMS` ledger now has 122 entries, all verified.
- **Manifest status** is unchanged and deferred to the post-closure status sync, as in §11.3.

### 12.5 Review requested

The request is a targeted `L12D013-PY-I001` closure review at the exact pushed pair: code #238 `07731c8b` and the docs head carrying this section. The candidate does not enter FINAL_CONTRACT_REVIEW and does not start Rust revalidation.

## 13. Targeted closure review 8, final complete review 9, merge and state

- **Review 8.** Targeted closure review 8 (issuecomment-6217444941) **APPROVED** code `07731c8b` / docs `7d8fb3cc` and provisionally closed `L12D013-PY-I001`. Its evidence is the unchanged review-7 reduction, now passing, and the R11 partition with K13 installed. The two equal-spelling, varying-read rows fail as intended; the others pass.
- **F001 route.** Before the final review, the author reconciled `L12D013-F001` from existing evidence only (`#235` history `f001_route_reconciliation`):
  - F001 is the WP's umbrella finding, not a CE-L12D013-01 finding.
  - Its M1–M4 success surface was found sound in review 4, which executed controls D013-C1 to C4. C5 is author Linux evidence only.
  - Its remaining condition was the final complete review. It was not recorded as closed by the author.
- **Review 9.** Final complete review 9 (issuecomment-6217925725) **APPROVED** the frozen pair for the exact-SHA merge gate and **closed** `L12D013-F001` and `L12D013-PY-I001`.
  - The reviewer ran D013-C1, C2-06, C2-08, C3 and C4 with their paired positives, and K1–K13.
  - Its focused Windows integration run had 2203 passed and 38 skipped.
  - C5 stays credited as author Linux evidence. Linux coverage and mypy remain the disclosed baseline limitations.
- **Merge.** Both PRs were merged with `minion_process merge` at the approved heads:
  - code #238 `07731c8b` → `393138f8` on `main`;
  - docs #310 `7d8fb3cc` → `349bef8b` on `master`.

  Each merge commit is reachable from its default branch. `#235` records the merged baseline and is in RUST_IMPLEMENTATION.
- **Documentary status sync** (this section, the DIV-009 registry entry and the manifest rows `EXEC-002`, `EXEC-003`, `EXEC-004`, `EXEC-005` and `EXEC-002-DIV-009`):
  - It marks Python's merged outcome and replaces the PENDING witness markers with the merged witness file.
  - It keeps Rust REVALIDATE_REQUIRED and the historical approvals and limitations.
  - It makes no semantic change. It is reviewed separately at its own exact heads, as review 9 required.

### 13.1 State

- Python Layer-12 delta L12-D013, including DIV-009: **APPROVED AND MERGED**.
- Shared L12-D013 contract (the section 3.2 rooted and UNC-root statement, the 99-case corpus, spec section 22): merged, and **READY FOR INDEPENDENT RUST REVALIDATION**. The surface is narrow: the merged rooted cases, and DIV-009's `ctx.fs` caller-path mapping and `rename_file` order.
- Rust: **REVALIDATE_REQUIRED**.
- L12-D013 cross-language: **NOT CLOSED**.

## 14. Rust revalidation block `L12D013-RUST-C001` and the entry-point clarification

**The block.** The Rust revalidation, handed off at issuecomment-6218754488, stopped at its start (issuecomment-6219403726). Codex classified it as `L12D013-RUST-C001`, a `CONTRACT_ASSURANCE_DEFECT`.
- **Codex's evidence:** a draft diagnostic, code #240 `447b7dfa` / docs #315 `9c8e9012`, which is not to be merged. No production fix, read move or certification was made.
- **The cause is mine,** as shared-contract author. CE-01 §2 said "Rust reads in exactly Node's cells", source-derived, and handoff §B.1 required every N cell through Rust's real seams.
- **What Rust's public provider actually does:** it applies the OS-path adapter that CE-L12D012-02 §2 preserves. The adapter strips an extended provider prefix. So at the public seam, `\\?\C:\base` with `c:leaf` makes no read and returns `c:\base\leaf`. The raw logical entry reads once.

**Clarification** (this candidate; proposed for independent agreement before Rust resumes):
- **CE-01 §2 and new §2.1** state the read domain per entry point, from the frozen `rd-1` Node rows. For provider `\\?\C:\base` against `C:\base`, 36 of 48 rows are equal, every rooted row among them. 12 differ: `c:leaf` ×4, `leaf` ×4 and `""` ×4.
- **Spec §22.1** gains the per-entry-point rule.
- **Spec §22.5** records Rust's public extended-provider success-value difference from pinned Pi as an observation, neither changed nor certified. Python matches Pi in all 48 rows. It is tracked as a separate delta on the drive-relative and base-resolution surface, which decides whether to align or diverge.
- **No semantic change:** no read is added or moved, the adapter is not removed, the corpus is unchanged, and the DIV-009 Owner decisions are untouched.
- **Evidence:** `data/l12-d013/rust-c001/` contains `ext_rows.py`, its output (`rows: 36 same, 12 differ`), its exit 0 and an empty stderr. The ledger `SHA256SUMS` has 4 entries.
  - It is a read-only comparison of the committed `rd-1/node.out`.
  - It was run once, with the kit venv's `python -I -B`, outside a `#209` window, since it is a pure JSON read with no build, gate or native probe.
  - The Rust public-seam values themselves come only from Codex's diagnostic.

**After agreement.**
1. The merged clarification.
2. A corrected Rust handoff addendum. It replaces §B.1 with the per-entry-point requirement and adds a characterization of the public-seam extended-provider rows, recorded and not certified.
3. The separate delta issue.

**State:** `L12D013-RUST-C001` is open, with Claude as next owner. Python stays approved and merged. Rust is REVALIDATE_REQUIRED. L12-D013 cross-language is NOT CLOSED.

## 15. Rust outcome (post-merge status sync)

- Rust L12-D013 revalidation, including DIV-009: **APPROVED and MERGED**.
  - Claude closure review 1 (`#235` issuecomment-6225928456) approved code #242 `1c0a1783` / docs #317 `862f78bb` with no findings. It reran both platforms from a fresh checkout on Claude-only targets in `#209` windows: Windows 710 passed, 0 failed, 2 ignored, 33 controls KILLED; Linux 700 passed, 0 failed, 3 ignored, 27 controls KILLED and 6 NOT_APPLICABLE.
  - Merged with `minion_process merge` at the approved heads: code → `24dfe1ea`, docs → `8d9674d2`. The Rust record is [`12-l12-d013-rust.md`](12-l12-d013-rust.md).
  - `L12D013-RUST-C001` is closed with the work package; its clarification was merged as docs #316.
- L12-D013 cross-language: **CLOSED**.
- Not certified here: the 48 public extended-provider rows of spec §22.5 stay observations, tracked by `#241` (frozen, Owner cut-over issuecomment-6222791583). `#224` is separate.
