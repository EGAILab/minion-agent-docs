# L12-D011 — a NUL-containing spawn input fails with pinned Node's literal diagnostic

Status: **contract draft, for independent contract review** (Codex). Python: NOT_IMPLEMENTED. Rust: NOT_IMPLEMENTED. Cross-language: NOT CLOSED.
Coordination: `minion-agent#224`. Provenance: `#195`. Requirements: `EXEC-013` (new); `EXEC-005`, `TOOL-034`, `TOOL-036`, `TOOL-037`.

**Owner decisions:**
- `#195` issuecomment-6137514688 (sha256 `3d2cd6ce8473babd72d12b5cd92032de6ab4332f7c43a950508376a11300ddf6`): APPROVE OPTION 1, PINNED PI LITERAL NUL-SPAWN DIAGNOSTIC.
- `#224` issuecomment-6137796390 (sha256 `3b4d4f0ab37fd76f5abac79b94ca0efdf4d0fc3c608fb6610ca4469483b2f0d2`): APPROVE OPTION 1, VALIDATE ALL RETAINED ENTRIES (the Windows case-collision boundary).

**Normative contract:** `spec/execution.md` §21. Manifest: `EXEC-013`. Canonical: `conformance/agent/spawn-nul/spawn-nul.json`.

## 1. Authority and characterization

- **Pins:** Node v22.15.1, read at tag `v22.15.1`:
  - `lib/child_process.js` lines 538–705 (`normalizeSpawnArguments`) and 963–975 (`validateArgumentNullCheck`);
  - `lib/internal/errors.js` 1444–1451 (`ERR_INVALID_ARG_VALUE`);
  - `lib/internal/util/inspect.js` 200–260 (defaults, `meta`), 501–581 (`addQuotes`, `strEscape`) and 1683–1706 (`formatPrimitive`).
- **Pinned Pi** `b7bb00b9`: `find.ts:269`, `grep.ts:226` and `bash.ts:103`. Each call is inside a `try` that surfaces the synchronous throw.

**Measured** in two host windows granted by Codex, Windows then Linux (the `python:3.13` image, Node 22.15.1 linux-x64). The probes and raw outputs are in `data/l12-d011/characterization/`. 38 pinned rows and 12 Minion-Python rows were measured on each platform, and no NUL case started a process. The results are summarized on #224 (issuecomment-6137690586):

- **Message:** the message, kind, names and `cwd` reason text match §21.2.
- **Precedence:** `file`, then `args` in order (first invalid only), then `options.cwd`, then `options.argv0` (unused by Minion), then the environment, name before value.
- **Environment order:**
  - Windows sorts by UTF-16 code unit and drops `toUpperCase` duplicates, keeping the first: `A` beats `Z`, `10` beats `2`, `K` beats `k`;
  - Linux uses ECMAScript property order: `2` before `10` before `Z`, and `k` before `K` when `k` was inserted first.
- **Inspect:** every rule in §21.2 was observed on both platforms, including NBSP kept, the backtick choice, the `' +\n  '` split, the 127/128/129 boundary, a surrogate pair cut at 128, and the 10000-unit trailer.
- **Tools:** `find` pattern `args[7]` and path `args[8]`; `bash` command `args[1]`.
  - On Windows, the path in a `find` message is the resolved native path, with its backslashes escaped.
  - Pre-aborted: the pipeline answers `Operation aborted`, as already certified.
- **Minion Python today:** `LocalSubprocess.spawn` raises `ValueError` for a NUL in the file, argv, cwd, an environment name or an environment value. The text is `embedded null character` on Windows and `embedded null byte` on Linux. The tools surface that text through the pipeline catch-all (`tools/execute.py:844`).
- **Minion Rust today** (read only): `Command::spawn` returns `InvalidInput`, which becomes `spawn_error` with the OS text. `find` and `grep` add `Failed to run fd:` / `Failed to run ripgrep:`, and `bash` its start-failure text.
- **`grep` is included in scope.** Its pattern and glob reach `rg`'s argv, and Pi surfaces the throw (`grep.ts:369`). #195 noted only that `grep`'s NUL **path** fails earlier, at the directory probe. The same rule therefore applies to `grep`.

## 2. Contract summary

See `spec/execution.md` §21. In brief:
- the rule (21.1);
- the diagnostic and the `inspect` subset (21.2);
- the effective-environment order (21.3);
- the Windows collision boundary (21.4);
- the tool boundary with its narrow distinction (21.5);
- what is unchanged (21.6);
- the evidence (21.7).

**Points flagged for the checkpoint:**
- **`options.cwd`** is included. It is the same pre-spawn surface, with Node's own reason text. At tool level a NUL cwd is rejected earlier, by the existing checks.
- **`grep`** is included, as described in §1.

## 3. Cross-language feasibility matrix (kit template, WORKFLOW §4.1.1)

Pinned Pi `b7bb00b9`. Author: Claude. Independent checkpoint reviewer: Codex.

### 3.1 Runtime value-domain matrix

| Value | Pi runtime | Python | Rust | Canonical | Lossless? | Witness |
|---|---|---|---|---|---|---|
| spawn `file` / `args[j]` | JS string (UTF-16; lone surrogates possible from tool input) | `str` (lone surrogates representable) | `ctx.subprocess` argv `&[String]` (scalar only); tool inputs `JsString` (UTF-16), converted by `to_utf8_lossy` **before** spawning | `{"utf16": …}` | **NO for Rust: finding L12D011-F1** | `fmt/lone-high-surrogate`, `fmt/lone-low-surrogate` |
| `options.cwd` | JS string | `str` | `Option<PathBuf>` (OS path; WTF-8 on Windows) | `{"utf16": …}` | NUL cases are scalar strings: yes | `name/cwd`, precedence pairs |
| env name / value | own properties of a JS object (insertion order; integer-like first) | `dict[str, str]` (insertion order kept) | `BTreeMap<String, String>` (sorted by UTF-8 bytes; insertion order **lost**) | ordered `[[name, value], …]` | **NO for Rust (POSIX order): finding L12D011-F2** | `env/order-*`, `env/collision-*` |
| diagnostic message | JS string; may contain raw NUL (in the name) and a lone high surrogate (128-unit cut) | `str` | `SubprocessError.message: String`, which **cannot** hold the lone surrogate of `len/surrogate-pair-straddles-128` | `{"utf16": …}` | **NO for Rust: part of L12D011-F1** | `len/surrogate-pair-straddles-128` |
| tool result text | JS string | `str` | `String` | `{"utf16": …}` | the same as the message | tool cases |

The other items in the template's checklist:
- **NOT_APPLICABLE**, with no numeric values on this surface: binary64, ±0, ±Infinity, NaN, the 2^53 boundary, `JSON.stringify` projection.
- **AUDITED:** undefined/null (`cwd` null = the provider's; `env` null = no overlay); UTF-16 code units; a valid pair; lone high and low surrogates.
- **NOT_APPLICABLE:** Unicode normalization and Unicode version. No case mapping is involved, because §21.4 performs no arbitration; the §15.5 consumer arbitration is unchanged and already certified.

**Value-domain carriers:**
- **RAW INPUT** (tool arguments): JS string, Python `str`, Rust `JsString`. Lossless.
- **PREPARED:** the same.
- **SCHEMA:** NOT_APPLICABLE, since no schema change is involved.
- **TOOL RESULT:** text as in the table above. The Rust lone-surrogate cut is F1.
- **PERSISTENCE / PROVIDER:** the existing projections are unchanged, and NOT_APPLICABLE to new values. Only error text is involved, already in the domain the result carries.

**Canonical-case audit:** every string is `{"utf16": …}`. The cases outside the scalar domain are the two lone-surrogate formatting cases and the straddle case's expected message. Each needs F1's resolution for Rust.

### 3.2 Lower-layer capability matrix

| Operation | Lower layer | Certified seam | Exact Pi semantics? | Python sufficient? | Rust sufficient? | Additive extension? | Reopen? |
|---|---|---|---|---|---|---|---|
| pre-spawn NUL validation with Node's message | EXEC-005 / new EXEC-013 | `ctx.subprocess.spawn` → `Err(spawn_error)` | yes, through the existing `spawn_error` code with the specified message | yes | for scalar inputs yes; F1 and F2 open | EXEC-013 is a delta row on the same seam; no new API for Python | none for Python; Rust per F1/F2 resolution |
| tool-level passthrough without the wrapper | Layer 13 (TOOL-034/036/037) | tool `execute` and `spawn_engine` | yes | needs a binding-internal mark on the error (§21.5) | the same | none | no |
| effective-environment order | EXEC-005 / EXEC-010 / §15.3 | the composed environment | Windows: sorting is enough; POSIX: needs composition order | yes (dict order, explicit UTF-16 sort key on Windows) | F2 | possibly, for Rust | per F2 |

### 3.3 Cross-runtime hazard checklist

| Hazard | State | Evidence / reason |
|---|---|---|
| `JSON.parse` | NOT_APPLICABLE | no JSON on the surface; canonical strings are code-unit arrays |
| `JSON.stringify` | NOT_APPLICABLE | the same |
| `Number` conversion | NOT_APPLICABLE | the only numbers are lengths and indices, all integers |
| `Math` semantics | NOT_APPLICABLE | none |
| negative zero | NOT_APPLICABLE | none |
| non-finite | NOT_APPLICABLE | none |
| `String.length` / UTF-16 | AUDITED | the 128 cut, the 76 / 16 / 10000 thresholds and `N` are all in code units (§21.2); `len/*` cases |
| `RegExp` | AUDITED | `strEscape` regex and loop paths; `fmt/over-100-*` prove they agree |
| Unicode / ICU version | NOT_APPLICABLE | no case mapping in §21; §15.5 is unchanged |
| Array ordering | AUDITED | Windows sorts names by UTF-16 code units (JS default sort); Python and Rust need an explicit UTF-16 key |
| Object property ordering | AUDITED | POSIX env order: integer-like names first (`env/order-integer-like-names`); F2 |
| Promise scheduling | NOT_APPLICABLE | Node's throw is synchronous; Minion's check precedes any await on the native spawn |
| `AbortSignal` | AUDITED | pre-abort precedes the check (`abort/pre-aborted-before-nul`; the tool-level pipeline controls) |
| timers | NOT_APPLICABLE | none |
| Node/libuv error mapping | AUDITED | `ERR_INVALID_ARG_VALUE` text; the non-NUL `ENOENT` control keeps the OS text |
| filesystem access semantics | NOT_APPLICABLE | the check precedes any filesystem access by `spawn` |
| platform path handling | AUDITED | `find`'s resolved Windows path is escaped (`tool/find/nul-absolute-search-path` uses a short absolute path per platform for a deterministic cut) |
| external package versions | AUDITED | Node 22.15.1, Pi `b7bb00b9`, fd 10.4.2, ripgrep 15.2.0 (TOOL-038 pins) |

### 3.4 Concurrency / order matrix

`spawn`:
1. start;
2. abort check (`Err(aborted)`);
3. **the NUL check, synchronous, before any native call**;
4. the native spawn.

No lock, no await between 2 and 4, and no cleanup, since nothing is created.

| Ordering guarantee | Realistic wrong implementation | Witness that kills it |
|---|---|---|
| the NUL check before any native spawn | checking after `create_subprocess_exec` / `Command::spawn` raises (catch-and-map) | the spy at the native spawn: zero calls |
| the abort before the NUL check | the NUL check first | `abort/pre-aborted-before-nul` |
| file → args → cwd → env | checking the env first, or the args after cwd | the `precedence/*` cases |
| the first invalid argument wins | the last, or all joined | `precedence/args-first-invalid-wins` |
| name before value | value first | `env/name-before-value-same-entry` |
| the tool passes the raw diagnostic | keeping `Failed to run fd:` | the tool cases |
| a narrow tool distinction | string-matching `"The argument"`, which mislabels a genuine engine message | binding witness: a non-NUL spawn failure whose OS text starts with "The " still gets the wrapper |

### 3.5 Neighborhood expansion record

| Family | Members probed | Source | New rows / findings |
|---|---|---|---|
| F2-like value domains (UTF-16) | lone high, lone low, pair, BMP, a straddle at the cut | the probe and generator | F1 |
| F3 Unicode / case | case-colliding env names on Windows | the probe (`env-case-dupe-win`) | Owner decision on #224 |
| F5 ordering | env order on both platforms, integer-like names | the probe | F2 |
| F7 carriers | argv, cwd, env, message, tool text | source reading | F1, F2 |

### 3.6 Verdict

```text
FEASIBILITY
    BLOCKED   open findings for the checkpoint:
      L12D011-F1  CONTRACT_ASSURANCE_DEFECT (representation)
        Rust cannot carry a lone surrogate in spawn argv or SubprocessError.message.
        Resolution options for Codex (Rust feasibility owner):
          (a) the check runs over the JavaScript-string argv the tools assemble, before
              to_utf8_lossy, with a JsString-capable message on the Rust error;
          (b) an additive JsString argv / message representation on the Rust seam.
        The raw-seam lone-surrogate cases then run where Rust can express them.
        Owner escalation only if a non-additive reopen is needed.
      L12D011-F2  CONTRACT_ASSURANCE_DEFECT (representation)
        Rust's BTreeMap env loses composition order, which POSIX multi-entry precedence needs.
        Resolution options:
          (a) an ordered env representation in Rust;
          (b) Codex proposes an alternative that keeps §21.3 observable.
        Owner escalation only if a non-additive reopen is needed.
```

## 4. Evidence plan

- **Generation:** `data/l12-d011/gen/`:
  - `spawn_nul_cases.mjs` holds the single input definition;
  - `gen_spawn_nul.mjs` runs on each platform, using Node `spawn` plus Pi's sliced `find`, `grep` and `bash`;
  - `merge_spawn_nul.mjs` writes `conformance/agent/spawn-nul/spawn-nul.json`.
- **Canonical runners:** both bindings get a thin `spawn-nul` runner, which calls the real `spawn` once, or the real tool through the pipeline, and compares.
- **Binding witnesses:** listed in spec §21.7.
- **Negative controls:** the §3.4 wrong implementations.

## 5. History

- 2026-10-13: #195 characterized and the options packet posted. The Owner decided Option 1, and #224 was opened.
- Characterized on Windows and Linux. The Owner decided the Windows collision boundary.
- This contract draft written.
