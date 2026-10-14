# L12-D012 — path resolution of colon-bearing components and the malformed `file:` literal fallback

Status: **SCOPING** (`minion-agent#229`). Python: REVALIDATE_REQUIRED on Windows (F002). Rust: REVALIDATE_REQUIRED (F001). Cross-language: NOT CLOSED.
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
  - A drive-relative input on **another** drive `D:` (revised in revision 1, §7) resolves against the **first** of these that Node's `win32.resolve` finds:
    1. the process's **inherited per-drive cwd entry** `=D:` (looked up as `process.env['=D:']`), when it names a path on `D:`;
    2. otherwise `process.cwd()`, when that is on `D:`;
    3. otherwise `D:\`.

    Rows 12 and 15 above are case 3: there was no inherited `=A:`/`=X:` entry, and the process cwd is on `E:`.
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

**The finite evidence set controls this host state explicitly.** It is a limitation of these examples, not of the contract:
- **Baseline cases** (rows 12 and 15 style) carry **preconditions**: no inherited `=A:`/`=X:` entry, and a process cwd not on `A:`/`X:`. The generator and every runner verify the preconditions at entry, through the same lookup the binding uses, and **refuse** to run (fail closed) when they do not hold. A host-dependent expected value is never silently rewritten.
- **Controlled cases** run the real resolver seam in a **child process launched with a crafted environment block** (`=A:=A:\deep`, `=X:=X:\q`) and a crafted cwd. They exercise branch 1 for each binding.
- **Branch 2**, the process cwd's own drive, is a controlled case too. The child's cwd is a contained sandbox directory, and the expectation is expressed relative to that cwd, through a placeholder the runner fills from the cwd it set itself.
- **Controls:** each case's precondition check must refuse a run where the entry is inherited, which is a missing-precondition control. Each controlled case pairs with its baseline (entry absent versus entry present), which is the discriminating pair.

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


#224's Rust handback waits on this work package's merge (`#224` `blocked_by` `#229`).
