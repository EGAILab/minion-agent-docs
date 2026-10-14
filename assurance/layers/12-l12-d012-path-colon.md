# L12-D012 — path resolution of colon-bearing components and the malformed `file:` literal fallback

Status: **contract APPROVED and merged** (code #230 → `5a244f13`, docs #304 → `b0b3de6c`). **Python: implementation candidate** (§11, F002 fix), for independent implementation review. *(Earlier: CONTRACT_DRAFT; Python REVALIDATE_REQUIRED on Windows, F002.)* Rust: REVALIDATE_REQUIRED (F001). Cross-language: NOT CLOSED.
Provenance: `#224` L12D011-RUST-F001 (issuecomment-6164614623); triage issuecomment-6164695679; scoping 1 `#229` issuecomment-6164885136.
Requirements: `EXEC-002` (`ctx.fs` path resolution, §3.2), `EXEC-005` (the spawn cwd, which uses the same resolver). `TOOL-026` is a neighbor: it reuses the Layer-12 resolver and is not reopened (§5).

## 1. Classification

This is WORKFLOW §11.8.11(c): new discriminating evidence that already-certified implementations do not satisfy an existing, correctly characterized requirement.
- The rule is `spec/execution.md` §3.2, **DIRECT_PI_PARITY** with pinned Pi `b7bb00b9` `packages/agent/src/harness/env/nodejs.ts:51-65` `resolvePath`.
- **The contract is not reopened** (§11.10). The rule already reads: a malformed `file://` URL is kept as an ordinary path, and a relative result is resolved against cwd by Node's `path.resolve` (`lib/path.js`, Node v22.15.1).
- The defects are implementation defects plus **a shared-evidence gap**. No canonical case covers this neighborhood: `fs-path-file-url.json` has no malformed-with-separator or colon-component case.

## 2. Authority behavior (characterization)

The probe is `data/l12-d012/scoping/scope_probe.mjs`: pinned Pi `resolvePath`, sliced unmodified and checked at `ref-repos/pi` HEAD `b7bb00b9`, run on Node v22.15.1. win32 runs natively on Windows 11. The posix column was first computed with `path.posix` and `fileURLToPath({windows:false})` injected (`scope-node.json`).

That column is **confirmed natively on Linux**. `native_probe.mjs` adds the platform-native column, meaning the same function with the platform's own `path` and `fileURLToPath`, exactly as Pi runs. It was run in `node:22.15.1-bookworm-slim` in a host window granted by Codex (launcher `run-linux-char.ps1`): **native Linux = posix column 23/23** (`native-linux.json`). On Windows, the native column equals the win32 column 23/23 (`native-win32.json`).

Provider cwd is `C:\x` (win32) and `/x` (posix):

| # | Input | win32 (native) | linux (native) |
|---|---|---|---|
| 1 | `file:///C:/a%2Fb` (malformed: encoded separator) | `C:\x\file:\C:\a%2Fb` | `/x/file:/C:/a%2Fb` |
| 2 | `file:/C:/a%2Fb` | `C:\x\file:\C:\a%2Fb` | `/x/file:/C:/a%2Fb` |
| 3 | `file:a%2Fb` | `C:\x\file:a%2Fb` | `/x/file:a%2Fb` |
| 4 | `file:///tmp/a%2Fb` | `C:\x\file:\tmp\a%2Fb` | `/x/file:/tmp/a%2Fb` |
| 5 | `file:x/y%2Fz` | `C:\x\file:x\y%2Fz` | `/x/file:x/y%2Fz` |
| 6 | `x/c:/d` | `C:\x\x\c:\d` | `/x/x/c:/d` |
| 7 | `x\c:\d` | `C:\x\x\c:\d` | `/x/x\c:\d` |
| 8 | `c:d` (drive-relative, the cwd's drive) | `c:\x\d` | `/x/c:d` |
| 9 | `x/c:` | `C:\x\x\c:` | `/x/x/c:` |
| 10 | `x/c:/` | `C:\x\x\c:` | `/x/x/c:` |
| 11 | `x/c:d/e` | `C:\x\x\c:d\e` | `/x/x/c:d/e` |
| 12 | `a::/b` (drive-relative, **another** drive) | `a:\:\b` | `/x/a::/b` |
| 13 | `x/:/y` | `C:\x\x\:\y` | `/x/x/:/y` |
| 14 | `:` | `C:\x\:` | `/x/:` |
| 15 | `x:y:z/w` (drive-relative, another drive) | `x:\y:z\w` | `/x/x:y:z/w` |
| 16 | `x/C:/y` | `C:\x\x\C:\y` | `/x/x/C:/y` |
| 17 | `x/C:\y` | `C:\x\x\C:\y` | `/x/x/C:\y` |
| 18 | `x//C:/y` | `C:\x\x\C:\y` | `/x/x/C:/y` |
| 19 | `a:/b` (absolute, another drive) | `a:\b` | `/x/a:/b` |
| 20 | `C:\y` | `C:\y` | `/x/C:\y` |
| 21 | `C:y` (drive-relative, the cwd's drive) | `C:\x\y` | `/x/C:y` |
| 22 | `file:///C:/a/b` (valid) | `C:\a\b` | `/C:/a/b` |
| 23 | `file:///tmp/a` (valid on posix, no drive on win32) | `C:\x\file:\tmp\a` (literal fallback) | `/tmp/a` |

**The observable rules, as Node implements them:**
- **win32.** A component's colon is an ordinary character **except** in a leading `X:` device prefix of the whole input.
  - A drive-relative input on the cwd's own drive resolves against the cwd.
  - A drive-relative input on **another** drive `D:` (**revision 2**, §7): the rule is Node's own branch, quoted below (§3.1). It is not a paraphrase; revision 1's "first source that matches the drive" paraphrase was wrong (C001).
    - The base is **selected first**: the inherited `=D:` entry if it is a non-empty string, otherwise `process.cwd()`.
    - The selected base is **then** replaced by `D:\` only when it is missing, or when its first two characters differ from `D:` (case-insensitively) **and** its third character is `\`.
    - Any other selected value is used literally, as the next path of the resolution, even when it is relative, rooted, on another drive, or bare.

    Rows 12 and 15 above have no inherited `=A:`/`=X:` entry. The selected base is the process cwd on `E:`, which fails the device check and has `\` third, so the result is the drive root.
  - Interior `X:` components are never devices.
- **posix.** `:` and `\` are ordinary characters.

## 3. Host state (revised in revision 1, §7)

The win32 other-drive rule above is part of the **existing, unchanged §3.2 contract**, including its two host dependencies: the inherited `=D:` entry and the process cwd's drive. **Nothing is removed from the contract.** An implementation that always resolves against the drive root is **not** conformant.

Native characterization (`drive_env_child.mjs`): a child Node launched with `=A:=A:\deep` and `=X:=X:\q` in its environment block resolves:
- `a::/b` to `a:\deep\:\b`;
- `x:y:z/w` to `x:\q\y:z\w`.

The same child without those entries gives `a:\:\b` and `x:\y:z\w`. A drive-relative input on the process cwd's own drive (`e:leaf`) resolves under the process cwd.

Two observations matter for implementations and runners:
- The entries are **not enumerable**: `Object.keys(process.env)` does not show them, but the lookup reads them.
- Assigning them in-process has no effect: `process.env['=a:'] = …` reads back `undefined` (`drive_env_probe2.mjs`).

A Python child sees the inherited entry through `GetEnvironmentVariableW('=A:')` but **not** through `os.environ` or `os.getenv` (`py_drive_env.mjs`). That is relevant to F002's fix.

### 3.1 The branch, verbatim (Node v22.15.1 `lib/path.js` `win32.resolve`, read from the running Node by `path.win32.resolve.toString()`, the `i === -1` iteration with a drive but no absolute path yet)

```js
        path = process.env[`=${resolvedDevice}`] || process.cwd();

        // Verify that a cwd was found and that it actually points
        // to our drive. If not, default to the drive's root.
        if (path === undefined ||
            (StringPrototypeToLowerCase(StringPrototypeSlice(path, 0, 2)) !==
            StringPrototypeToLowerCase(resolvedDevice) &&
            StringPrototypeCharCodeAt(path, 2) === CHAR_BACKWARD_SLASH)) {
          path = `${resolvedDevice}\\`;
        }
```

The selected `path` then goes through the same root and device parsing as any argument in the loop, so a selected value on another device is skipped, as Node skips any such argument. Bindings implement this branch **as written**, including:
- `||`: an empty entry selects the process cwd;
- the conjunction: a non-matching device without `\` third is kept;
- the subsequent parsing.

### 3.2 Native partition (revision 2; `drive_partition.mjs`, output `partition-win32.json`)

Pinned Pi `resolvePath` (sliced unmodified) runs in **32 real child processes**. Each child's environment block carries the crafted `=D:` entry or omits it, and each child runs from the project root on `E:`. Provider cwd `C:\x`, input `d:leaf`. The entry values are strings only: nothing is accessed, created or used as a cwd. The probe ran in a host window granted by Codex.

| Inherited `=D:` value | D = E (the process cwd's drive) | D = A (another drive) | Class (selected base → predicate) |
|---|---|---|---|
| absent | `e:\AI\…\Minion-Agent\leaf` | `a:\leaf` | process cwd → E: keeps it; for A:, mismatch with `\` third → root |
| `""` (empty) | `e:\AI\…\Minion-Agent\leaf` | `a:\leaf` | `\|\|` selects the process cwd (as above) |
| `D:\deep` | `e:\deep\leaf` | `a:\deep\leaf` | match → kept |
| `d:\deep` (lower case) | `e:\deep\leaf` | `a:\deep\leaf` | case-insensitive match → kept |
| `D:/deep` | `e:\deep\leaf` | `a:\deep\leaf` | match → kept |
| `D:rel` | `e:rel\leaf` | `a:rel\leaf` | match → kept; drive-relative result |
| `D:` | `e:leaf` | `a:leaf` | match → kept; result **not absolute** |
| `X:\other` | `e:\leaf` | `a:\leaf` | mismatch and `\` third → **root**, with **no** fallback to the process cwd (the reviewer's witness) |
| `X:/other` | `e:leaf` | `a:leaf` | mismatch, but `/` third → kept; then skipped as another device |
| `X:other` | `e:leaf` | `a:leaf` | mismatch, `o` third → kept, then skipped |
| `X:` | `e:leaf` | `a:leaf` | mismatch, no third char → kept, then skipped |
| `relative` | `e:relative\leaf` | `a:relative\leaf` | no device, `l` third → kept literally |
| `\deep` | `e:\deep\leaf` | `a:\deep\leaf` | `e` third → kept; rooted on D: |
| `/deep` | `e:\deep\leaf` | `a:\deep\leaf` | as above |
| `\\srv\share` | `e:leaf` | `a:leaf` | `s` third → kept; a UNC device, skipped |
| `r` | `e:r\leaf` | `a:r\leaf` | single character → kept literally |

The reviewer's seven rows (`#229` 6166182330) are reproduced exactly. The partition is enumerated **from the predicate**:
- selection source: entry or cwd, with empty versus absent;
- the device test: match versus mismatch, with case;
- the third character: `\`, `/`, another character, or absent;
- the subsequent parse of a kept value: absolute on D:, drive-relative, bare device, other device, UNC, relative, rooted.

**The finite evidence set controls this host state explicitly.** It is a limitation of these examples, not of the contract:
- **Baseline cases** (rows 12 and 15 style) carry **preconditions**: no inherited `=A:`/`=X:` entry, and a process cwd not on `A:`/`X:`. The generator and every runner verify the preconditions at entry, through the same lookup the binding uses, and **refuse** to run (fail closed) when they do not hold. A host-dependent expected value is never silently rewritten.
- **Controlled cases** run the real resolver seam in a **child process launched with a crafted environment block** (`=A:=A:\deep`, `=X:=X:\q`) and a crafted cwd. They exercise branch 1 for each binding.
- **Branch 2**, the process cwd's own drive, is a controlled case too. The child's cwd is a contained sandbox directory, and the expectation is expressed relative to that cwd, through a placeholder the runner fills from the cwd it set itself.
- **Controls:** each case's precondition check must refuse a run where the entry is inherited, which is a missing-precondition control. Each controlled case pairs with its baseline (entry absent versus entry present), which is the discriminating pair.
- **Revision 2 controlled classes** (§3.2):
  - the **wrong-drive entry with `\` third on the process cwd's drive** (`=E:` = `X:\other` → `e:\leaf`). It pairs with the absent-entry row (`e:\…\leaf` under the process cwd), and its control is an implementation that falls through to the process cwd;
  - **empty versus absent** at precondition entry, which stay distinct;
  - one each of: the matching drive-relative entry, the bare device, the mismatch without `\` third, relative, rooted, and UNC.

  An implementation that "searches for the first source matching the drive" fails the first pair. One that treats any mismatch as root fails the `/`-third row.

## 4. Current bindings

| Binding | Equal to pinned Pi | Differs |
|---|---|---|
| Python certified `resolve_local_path` (win32) | 21/23 | **#12, #15: other-drive drive-relative.** Python gives `a::\b` and `x:y:z\w`. That is **L12D012-F002** |
| Rust logical `path::resolve`/`normalize` and `filesystem::resolve_local_path` | to be characterized by the Rust owner | #1 (Codex, #224 RUST-F001): `C:\x\file:C:a%2Fb` / `C:a%2Fb`. The separator after any `:`-ending component is dropped, and `PathBuf` pushing interprets embedded drives. That is **L12D012-F001** |

Python on **Linux equals pinned Pi 23/23** (`python:3.13`; `linux-char.sh`, output `py-linux.txt`), so **F002 is Windows-only**.

## 5. Proposed scope

**In scope:**
1. **Shared cases.** A new canonical document `conformance/agent/fs-path-domain/fs-path-resolution.json`, with a small lexical schema extension or a new `path-resolution-scenario.schema.json`. Each case gives the per-platform provider cwd, the input (UTF-16 units), and the expected absolute path per platform, all **generated from pinned Pi on Windows and Linux natively**.
   - The observable is `ctx.fs.absolute_path` with the provider cwd. It is lexical: no filesystem access, and **no writes to colon components** (on Windows those would create NTFS alternate data streams).
   - A spawn-cwd step reusing the L12-D011 NUL diagnostic is **not** added; #224's existing case covers the spawn path.
   - The win32 other-drive rows run as the baseline, precondition-checked cases plus the controlled child-process cases of §3 (revision 1).
2. **Rust characterization, inside scoping (Codex, scoping review 1).** All 23 inputs and the §3 controlled cases go through the real Rust `absolute_path` seam on both platforms. The native scalar resolver used by consumers and the logical/lossless resolver serving the spawn cwd are characterized as well. Agreements and disagreements are both recorded. The pre-fix observations are kept as negative-control evidence. This happens **before** any resolver correction and before the shared case/feasibility freeze. The nearest rooted, drive-relative and colon-with-separator compositions inform the finite case set.
3. **Python:** fix F002 (all three branches of the other-drive rule), with lower-layer regressions (EXEC-002, EXEC-005 and the TOOL-026 consumers).
4. **Rust (Codex):** fix F001 in both resolvers, plus whatever the characterization in item 2 finds, with the affected lower-layer regressions.

**Not reopened:** every other path rule; `~` expansion; URL decoding; error codes; the NUL rule (#224); TOOL-026's tool-level rejection of malformed `file:` URLs. Those tool cases (`builtin-*-malformed-file-url-rejected…`) stay as certified.

## 6. Plan and stop condition

1. ~~Native Linux confirmation of the posix column~~: done (§2, 23/23).
2. Scoping review 2 of revision 1, together with the Rust full-matrix characterization (Codex, §5 item 2).
3. Generation and the cases (baseline with verified preconditions, plus controlled child-process cases), then independent review.
4. Python F002 (Claude) and Rust F001 (Codex), each through independent review.
5. Closure.

## 7. Scoping review 1 and revision 1

**Scoping review 1** (Codex, `#229` issuecomment-6165976216) was CHANGES REQUESTED at `dc4eda67`. It accepted the §11.8.11(c) classification, the 23-row neighborhood (reproduced on Windows by the reviewer, Python 21/23), the lexical observable and the routing. Codex also directed that the Rust full-matrix characterization belongs in scoping.

**L12D012-C001** (MEDIUM, blocking): the host-state domain was incomplete. Node's `win32.resolve` reads an **inherited per-drive cwd entry** before falling back to `process.cwd()`. The reviewer's in-memory fixture shows `=a:` and `=x:` changing rows 12 and 15 even with the process cwd on `E:`. The original §3 also placed the process-own-drive case "out of the contract's observable surface", which a test-domain restriction cannot do.

The original §3 text, kept for history:

> "Setting `=X:` in-process had no effect (`drive_env_probe.mjs`). Therefore the shared cases: use other-drive letters that are never the generating or running host's process-cwd drive …; record the host-drive assumption …; leave any other-drive case on the process's own drive out of the contract's observable surface. It is host state, not a lexical rule."

**Revision 1:**
1. §2 states the full three-branch other-drive rule.
2. §3 now holds:
   - both host dependencies, native characterization of the inherited branch (`drive_env_child.mjs`), why in-process assignment shows nothing (`drive_env_probe2.mjs`), and Python's access path (`py_drive_env.mjs`);
   - the explicit statement that the contract is unchanged and a root-only implementation is non-conformant;
   - preconditions verified at generator and runner entry, with fail-closed refusal;
   - controlled child-process cases for branches 1 and 2;
   - a missing-precondition control and the discriminating pairs.
3. §5 adds the Rust characterization inside scoping.

**Scoping review 2** (Codex, `#229` issuecomment-6166182330) was CHANGES REQUESTED at `e3b97682`. **C001 was refined, not closed.** Revision 1's §2 described a "first source matching the drive" search. Node instead **selects** the inherited value (or the process cwd) **before** its device check. So a wrong-drive entry suppresses the process-cwd fallback, and relative, rooted and drive-relative entries are used literally. The reviewer's native seven-value child partition is the witness.

**Trigger A fired** (C001 survived reviews 1 and 2). The route is recorded in `#229` `history.routes` (RT-6): the Owner was notified with the default CONTRACT_CONVERGENCE route, and the narrow targeted-fix exception was taken on a finite dimension, namely one verbatim source branch whose predicate enumerates the partition. If C001 survives review 3, the work package moves to CONTRACT_DRAFT and enters CONTRACT_CONVERGENCE with no further point fix. The kit has no SCOPING → CONTRACT_CONVERGENCE transition.

The revision-1 text of §2, kept for history:

> "resolves against the **first** of these that Node's `win32.resolve` finds: 1. the process's inherited per-drive cwd entry `=D:` …, when it names a path on `D:`; 2. otherwise `process.cwd()`, when that is on `D:`; 3. otherwise `D:\`."

**Revision 2:**
1. §2 states the selection-then-check rule.
2. §3.1 quotes Node's branch verbatim, read from the running v22.15.1.
3. §3.2 is the native **32-child partition**, which reproduces the reviewer's seven rows exactly and extends them by predicate class.
4. §3 adds the revision-2 controlled classes, including the wrong-drive-entry/process-cwd pair with its fall-through control, and the empty versus absent distinction.


#224's Rust handback waits on this work package's merge (`#224` `blocked_by` `#229`).

**Scoping review 3** (Codex, `#229` issuecomment-6166718345) was **targeted APPROVED** at `6422f558`: C001 is closed at scoping/proposal level. The missing-precondition and fall-through runtime controls remain required at the canonical-runner stage.

## 8. Pre-fix Rust characterization (Codex) and Claude's independent inspection

The Rust owner's pre-fix characterization is docs #305 @ `e8a201ec` (`12-l12-d012-rust-scoping.md`). It covers all 23 inputs and the 32 host-state classes, through the real `absolute_path`, logical, native scalar and draft lossless seams, on both platforms, with no correction.
- **Windows:** every seam gives 9/23 on the baseline and 10/32 on the host-state classes.
- **Linux:** 13/23, except native scalar at 23/23.

Claude recomputed every comparison from the archived arrays against **Claude's own** Pi observations (§§2, 3.2): **0 disagreements**, with the integrity ledger at 17/17 (`#229` issuecomment-6167853233). On every host-state row, every Rust seam returns the drive-relative input unresolved. Its 10/32 matches are exactly the classes where Node also returns `D:leaf`.

## 9. Shared cases (contract draft)

**The document:** `conformance/agent/path-resolution/path-resolution.json`, with schema `conformance/schema/path-resolution-scenario.schema.json`. It has its own directory, because the L12-D001 `fs-path-domain/` schema test validates every file there. It holds 80 cases:

| Set | Cases | Observable |
|---|---|---|
| `win32/baseline/01-23` | the §2 inputs, provider cwd `C:\x` | in-process `absolute_path` under **verified preconditions**: no inherited `=A:`/`=X:` entry, and a process cwd not on `A:`/`X:`/`C:` |
| `win32/host/cwd-drive/01-16` | the §3.2 values on the child cwd's own drive | a **child process** with a crafted environment block (exactly that `=D:` entry, no other `=`-entry) and a contained sandbox cwd; precondition: the child cwd is not on `C:` |
| `win32/host/a-drive/01-16` | the §3.2 values on `A:` | as above; precondition: the child cwd is not on `A:`/`C:` |
| `linux/baseline/01-25` | the §2 inputs plus `e:leaf` and `a:leaf`, provider cwd `/x` | in-process; no host state (NOT_APPLICABLE) |

**Templates.** A cwd-dependent value is a template of parts: literal UTF-16 text, `cwd_drive` (upper or lower case), or `cwd_tail` (the child cwd after its device). The runner fills them from the cwd it set for the child. The generator **proves** each template: every host case runs from two different sandbox cwds, and the template derived from the first must reproduce the second exactly.

**Generation:** `data/l12-d012/gen/` (`run-gen.mjs`, `gen_path_resolution.mjs`, `merge_path_resolution.mjs`, `io.mjs`), run in a host window granted by Codex:
- **Pi.** Pinned Pi `resolvePath`, sliced unmodified, on native Node v22.15.1: Windows natively, and Linux in one read-only `node:22.15.1-bookworm-slim` container with read-only binds and private `/tmp` only.
- **Writes.** The generator writes nothing, only stdout. Every file is written by the launcher through the fs-guard (`makeRun`, `writeOutput`), and nothing is deleted.
- **Missing-precondition controls.** The generator launched with an inherited `=A:` or `=X:` entry **refuses** with exit 3 and writes nothing. Both refused (`precondition-controls.json`).

**Agreement with the reviewed characterization:**
- win32 baseline equals §2 at 23/23, and linux baseline equals the native Linux column at 23/23; the two extra POSIX spellings give `/x/e:leaf` and `/x/a:leaf`;
- the a-drive host cases equal §3.2 at 16/16;
- the cwd-drive templates, filled with the scoping probe's cwd, equal §3.2 at 16/16.

The schema tests in `tests/conformance/test_schema_validation.py` (15 tests: well-formedness, validation, 12 malformed variants, corpus shape) pass.

**Required of every binding's runner** (the canonical-runner stage, to be independently reviewed):
1. **Verify the preconditions at entry** through the binding's own lookup (Python: `GetEnvironmentVariableW`; Rust: `std::env::var_os`), and the process cwd's drive. **Refuse** otherwise; never rewrite an expectation.
2. **Run host cases in a child process** whose environment block is built from scratch: the parent's ordinary variables, minus every `=`-prefixed entry, plus exactly the case's entry. Its cwd is a contained sandbox directory. Fill the templates from that cwd.
3. **Permanent controls:**
   - a missing-precondition refusal;
   - the wrong-drive-entry/process-cwd pair (`cwd-drive/08` against `cwd-drive/01`) killing a fall-through implementation;
   - the `/`-third row (`/09`) killing an implementation that treats any mismatch as the root;
   - the absent/empty distinction (`/01`, `/02`).
4. **Never** pass any case path to a filesystem operation or use it as a cwd.

## 10. Cross-language feasibility matrix (kit template, WORKFLOW §4.1.1)

**1. Runtime value domain**

| Observable value | Pi | Python | Rust | Canonical | Lossless? | Evidence |
|---|---|---|---|---|---|---|
| input path, provider cwd | JS string | `str` | `String` / `JsString` | `utf16` | YES: the corpus is ASCII only; no lone surrogates in this WP (the Unicode domain is L12-D001's, unchanged) | AUDITED |
| resolved absolute path (`absolute_path` result) | JS string | `str` | the provider's existing lossless logical result | `utf16` / template | YES | AUDITED |
| inherited `=D:` entry | `process.env['=D:']` (hidden, not enumerable, not assignable in-process) | `GetEnvironmentVariableW` (not `os.environ`): §3, `py_drive_env.mjs` | `std::env::var_os`: #305 matched Node's values exactly | template `entry` | YES | AUDITED |
| process cwd | `process.cwd()` | `os.getcwd()` | `std::env::current_dir` | `cwd_drive` / `cwd_tail` parts | YES | AUDITED |
| non-absolute result (`D:leaf`, `D:rel\leaf`) | returned as is | `str` | string | `utf16` / template | YES; bindings must not "complete" it | AUDITED |

**2. Lower-layer capability**

| Operation | Layer | Seam | Exact Pi semantics today? | Python sufficient? | Rust sufficient? | Additive? | Reopen? |
|---|---|---|---|---|---|---|---|
| lexical resolution (§3.2) | L12 EXEC-002 / EXEC-005 | `ctx.fs.absolute_path`; spawn cwd resolver | NO: F002 (Python, win32 other-drive), F001 (Rust, all its seams) | yes (implementation fix) | yes (implementation fix) | no new seam | **none**: implementation defects against the unchanged contract (§1) |
| reading the inherited per-drive entry | OS environment | none today | Python reads `os.environ` only; Rust does not read it | `GetEnvironmentVariableW` via `ctypes` | `var_os` | binding-internal | none |

**3. Hazard checklist**

| Hazard | State | Reason / evidence |
|---|---|---|
| platform-specific path handling (separators, drive letters, case) | **AUDITED** | §§2, 3, 3.2; the subject of this WP |
| external runtime versions | AUDITED | Node v22.15.1 native on both platforms; Pi `b7bb00b9`; images named in §9 |
| `String.length` / UTF-16 units | AUDITED | ASCII corpus; `utf16` canonical form |
| Unicode / ICU | NOT_APPLICABLE | no case mapping or normalization: the device comparison is ASCII `toLowerCase` |
| `JSON.parse` / `JSON.stringify`, `Number`, `Math`, negative zero, non-finite values | NOT_APPLICABLE | no numeric or JSON values |
| `RegExp` | NOT_APPLICABLE | none in the path |
| Array / Object ordering | NOT_APPLICABLE | no collections observed |
| Promises, `AbortSignal`, timers | NOT_APPLICABLE | synchronous lexical resolution |
| Node/libuv error mapping | NOT_APPLICABLE | resolution never errors (malformed URLs fall back literally) |
| filesystem access semantics | NOT_APPLICABLE | lexical only; case paths are never accessed (§9 runner rule 4) |

**4. Concurrency / order:** NOT_APPLICABLE. Resolution is synchronous; host cases are independent child processes.

**5. Neighborhood:** colon components and the malformed-URL fallback (§2, 23 rows); the inherited-entry partition (§3.2, 32 classes by selection source × device test × third character × subsequent parse); POSIX drive-looking spellings (2). The F-family "platform path handling" is covered; no new family applies.

**6. Verdict:**

```text
FEASIBILITY   READY   every row AUDITED / NOT_APPLICABLE; F001 and F002 are implementation findings with a
                      binding-local fix and no lower-layer reopen; no open contract finding
```

## 11. Python implementation (F002), candidate

**Contract review 1** (Codex, `#229` issuecomment-6168692064, round 4) **APPROVED** the shared contract at code `7b38744e` / docs `9c360722`. It was merged by guarded exact-head merges: code #230 → `5a244f13`, docs #304 → `b0b3de6c`. The Python candidate is on `layer/12-d012-python` at `c905ec0a` (three commits on `5a244f13`).

**The fix (`execution/filesystem.py`, `execution/_libuv_win32.py`):**
- **The hook.** `resolve_local_path` gains one branch, on win32 only (`sys.platform`): a drive-relative input on another drive than the provider cwd's (`_is_other_drive_relative`) is resolved by `node_win32_resolve([cwd, path], …)`. **Every other input keeps the certified pipeline unchanged**, which already equals Pi (§4: 21/23, and Linux 23/23).
- **`node_win32_resolve`** is a literal port of Node v22.15.1 `path.win32.resolve`. Its parts:
  - `_win32_root`, the root match: UNC device, `X:` device, rooted, or relative;
  - the right-to-left argument loop, with another-device arguments skipped;
  - `_node_normalize_string`, the port of `normalizeString`;
  - `_select_drive_base`, the §3.1 branch verbatim: `inherited(device) or process_cwd()`, then the root only when the first two characters differ **and** the third is `\`.
- **The two host dependencies** are injected: the real ones are `_libuv_win32.inherited_drive_cwd` and `os.getcwd`.
- **`inherited_drive_cwd(device)`** reads `=D:` with `GetEnvironmentVariableW`, because CPython's `os.environ` drops `=`-prefixed names. It returns `None` when the entry is absent (`ERROR_ENVVAR_NOT_FOUND`), `""` when it is present but empty, and otherwise the value, growing the buffer as needed.

**The canonical runner** (`tests/conformance/path_resolution_runner.py`, `test_path_resolution_conformance.py`) is thin; every observation is the real `LocalFileSystem.absolute_path`:
- **Baseline cases** run in-process **after their preconditions are verified** through `inherited_drive_cwd` and the process cwd's drive. An unmet precondition fails with `PRECONDITION REFUSED`; an expectation is never rewritten.
- **Host cases** (win32) run in a **child Python process**. Its environment block is the parent's ordinary variables (`os.environ` holds no `=`-entry) plus exactly the case's entry, and its cwd is a pytest sandbox directory on E:. The input and expectation templates are filled from the child's reported cwd. No case path is ever accessed.
- **Coverage per platform.** On win32: 23 baseline and 32 host cases. On linux: 25 baseline cases. A selection test asserts the counts.

**Permanent controls (record §9 requirement 3, contract review item 6).** Each wrong selection is a monkeypatched `_select_drive_base`, and each must be **killed by its named case** while the real selection passes it:

| Control | Known-bad selection | Killed by |
|---|---|---|
| fall-through (revision 1's rejected paraphrase) | the first source naming the device, else the root | `cwd-drive/08` (`=E:` = `X:\other`) |
| mismatch-always-root | any device mismatch selects the root | `cwd-drive/09` (`X:/other`) |
| empty-is-a-value | an empty entry is used instead of the process cwd | `cwd-drive/02` |
| missing precondition | present entries (including **empty**) and a process cwd on a forbidden drive | must REFUSE; absent passes |

A pair test asserts that `01` equals `02` and differs from `08`. A child-environment test asserts that the crafted block carries exactly the case's entry.

**Port witnesses** (`tests/execution/test_path_resolution_port.py`) are checked against **Node's own observations**: `tests/execution/data/node_win32_resolve.json`, generated by `data/l12-d012/gen/gen_port_fixture.mjs` on Node v22.15.1, with a copy in `data/l12-d012/python-implementation/`. The fixture has three kinds of rows:
- **46 rows** with an absolute device base, where Node consults no host state. These are called with lookups that **fail if consulted**.
- **7 rows** from real Node children with a crafted `=A:` entry, covering relative, `..`, rooted, UNC, single-character and bare-device entries. These include non-absolute results such as `a:..\leaf`.
- **8 `path.win32.normalize` rows** for `normalizeString` with a tail that does not end in a separator.

The tests also cover the drive-relative classification, the hook (lookup used for another drive, not for the cwd's drive) and `inherited_drive_cwd`'s absent, empty and grown-buffer branches.

**Gates at `c905ec0a`** (host windows granted by Codex; `data/l12-d012/python-implementation/{windows,linux}`):

| Gate | Windows | Linux (`python:3.13`, pytest 9.1.1, uid 1000, pinned ICU 78.3) |
|---|---|---|
| pytest | **6696 passed**, 43 skipped, 19 xfailed, 0 failed; exit 0 | **6489 passed**, 208 skipped, 19 xfailed, 0 failed; exit 1 (coverage only) |
| coverage | **100%** (9876 statements) | 96.76%, 320 missed. Per-file missed counts **equal** the established base-equal set except `_libuv_win32.py` (159 → 174, the Windows-only reader; the module is never imported on Linux) and `filesystem.py` (63 → 65, the two statements of the win32 hook body) |
| mypy | clean (118 files); exit 0 | exactly the base's 15 errors (set-equal, line numbers aside); exit 1 |
| ruff | clean; the 5 changed files formatted (whole-tree drift of 7 untouched files, informational) | clean; exit 0 |

**Runs not credited** (disclosed):
- Windows at `ea99028`: coverage 99.99%, one unreachable `normalizeString` line. Node-derived `normalize` witnesses were added in `c7b4499`.
- Linux at `c7b4499`, run 1: the launcher died on a PowerShell 5.1 stderr/`Stop` interaction. The launcher was fixed.
- Linux at `c7b4499`, run 2: **one new Linux mypy error**. The hook used `os.name`, so Linux mypy saw the Windows-only module as attribute-less. Fixed in `c905ec0a` with `sys.platform`, the guard every other call site uses.
- Windows at `c905ec0a`, run 1: one failure in `test_bash_shell.py::test_lookup_lifecycle_rows[timeoutWhileAlive]`, a timing row unrelated to this change. The run took 621 s against the usual 263 s, under the load of four long-running VS Code ripgrep indexing processes (not ours, not touched). The file passed 5/5 in isolation, and the full gate was rerun at the same head: the credited run above.
- Development runs before the windows.

**Status:** F002 is an implementation candidate for independent implementation review. F001 (Rust) is next, from the merged contract. The manifest's EXEC-002/EXEC-005 status lines are updated in the post-merge status sync. Cross-language: NOT CLOSED.
