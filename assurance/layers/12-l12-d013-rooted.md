# L12-D013: win32 rooted drive-less input (scoping 1)

Status: **CONTRACT CANDIDATE for independent contract review** (§7). Scoping 1 was approved by Codex review 1. Python is not corrected yet. *(Earlier: SCOPING, PROPOSED for independent scoping review.)* Coordination: `minion-agent#235`. Delta of `EXEC-002`/`EXEC-005`. Class: governing, CP-6 (WORKFLOW 11.8.11(c)).

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
