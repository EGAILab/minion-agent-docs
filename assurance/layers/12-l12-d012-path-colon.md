# L12-D012 — path resolution of colon-bearing components and the malformed `file:` literal fallback

Status: **SCOPING** (`minion-agent#229`). Python: REVALIDATE_REQUIRED (F002). Rust: REVALIDATE_REQUIRED (F001). Cross-language: NOT CLOSED.
Provenance: `#224` L12D011-RUST-F001 (issuecomment-6164614623); triage issuecomment-6164695679; scoping 1 `#229` issuecomment-6164885136.
Requirements: `EXEC-002` (`ctx.fs` path resolution, §3.2), `EXEC-005` (the spawn cwd, which uses the same resolver). `TOOL-026` is a neighbor: it reuses the Layer-12 resolver and is not reopened (§5).

## 1. Classification

This is WORKFLOW §11.8.11(c): new discriminating evidence that already-certified implementations do not satisfy an existing, correctly characterized requirement.
- The rule is `spec/execution.md` §3.2, **DIRECT_PI_PARITY** with pinned Pi `b7bb00b9` `packages/agent/src/harness/env/nodejs.ts:51-65` `resolvePath`.
- **The contract is not reopened** (§11.10). The rule already reads: a malformed `file://` URL is kept as an ordinary path, and a relative result is resolved against cwd by Node's `path.resolve` (`lib/path.js`, Node v22.15.1).
- The defects are implementation defects plus **a shared-evidence gap**. No canonical case covers this neighborhood: `fs-path-file-url.json` has no malformed-with-separator or colon-component case.

## 2. Authority behavior (characterization)

The probe is `data/l12-d012/scoping/scope_probe.mjs`: pinned Pi `resolvePath`, sliced unmodified and checked at `ref-repos/pi` HEAD `b7bb00b9`, run on Node v22.15.1. win32 runs natively on Windows 11. The **posix** column is computed with `path.posix` and `fileURLToPath({windows:false})` injected; it is **provisional until native Linux generation**. Output: `scope-node.json`.

Provider cwd is `C:\x` (win32) and `/x` (posix):

| # | Input | win32 | posix (provisional) |
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
  - A drive-relative input on **another** drive resolves against that drive's root. Node consults the per-drive cwd, and it uses `process.cwd()` when that is on the same drive; see §3.
  - Interior `X:` components are never devices.
- **posix.** `:` and `\` are ordinary characters.

## 3. Determinism constraint

For an input that is drive-relative on a drive other than the provider cwd's, Node's `win32.resolve` falls back to `process.cwd()` **when the process cwd is on that drive**. Otherwise it uses the drive root. Setting `=X:` in-process had no effect (`drive_env_probe.mjs`). Therefore the shared cases:
- use other-drive letters that are **never** the generating or running host's process-cwd drive. The generators and runners on this project run from `E:`, so the cases use `a:` and `x:`;
- record the host-drive assumption in the case notes;
- leave any other-drive case on the process's own drive out of the contract's observable surface. It is host state, not a lexical rule.

## 4. Current bindings

| Binding | Equal to pinned Pi | Differs |
|---|---|---|
| Python certified `resolve_local_path` (win32) | 21/23 | **#12, #15: other-drive drive-relative.** Python gives `a::\b` and `x:y:z\w`. That is **L12D012-F002** |
| Rust logical `path::resolve`/`normalize` and `filesystem::resolve_local_path` | to be characterized by the Rust owner | #1 (Codex, #224 RUST-F001): `C:\x\file:C:a%2Fb` / `C:a%2Fb`. The separator after any `:`-ending component is dropped, and `PathBuf` pushing interprets embedded drives. That is **L12D012-F001** |

Python POSIX behavior is to be confirmed natively with the Linux generation.

## 5. Proposed scope

**In scope:**
1. **Shared cases.** A new canonical document `conformance/agent/fs-path-domain/fs-path-resolution.json`, with a small lexical schema extension or a new `path-resolution-scenario.schema.json`. Each case gives the per-platform provider cwd, the input (UTF-16 units), and the expected absolute path per platform, all **generated from pinned Pi on Windows and Linux natively**.
   - The observable is `ctx.fs.absolute_path` with the provider cwd. It is lexical: no filesystem access, and **no writes to colon components** (on Windows those would create NTFS alternate data streams).
   - A spawn-cwd step reusing the L12-D011 NUL diagnostic is **not** added; #224's existing case covers the spawn path.
2. **Python:** fix F002, with lower-layer regressions (EXEC-002, EXEC-005 and the TOOL-026 consumers).
3. **Rust (Codex):** fix F001 in both resolvers, characterize the rest of this matrix, and run the affected lower-layer regressions.

**Not reopened:** every other path rule; `~` expansion; URL decoding; error codes; the NUL rule (#224); TOOL-026's tool-level rejection of malformed `file:` URLs. Those tool cases (`builtin-*-malformed-file-url-rejected…`) stay as certified.

## 6. Plan and stop condition

1. Native Linux confirmation of the posix column, in a host window.
2. Generation and the cases.
3. Independent review of the scoping and the cases (Codex).
4. Python F002 (Claude) and Rust F001 (Codex), each through independent review.
5. Closure.

#224's Rust handback waits on this work package's merge (`#224` `blocked_by` `#229`).
