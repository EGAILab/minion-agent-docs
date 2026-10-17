> **Update since this check was drafted (2026-10-17, before #235 closed).** The analysis below is unchanged; only the following facts moved:
> - **#235 L12-D013 is CLOSED.** Rust was approved by Claude's closure review 1 and merged: code `24dfe1ea`, docs `8d9674d2`, status sync `be07d20c` / `ebba7b16`. Rust now matches the rooted/UNC-root rule and DIV-009, so B16's "Rust pending revalidation" no longer applies.
> - **#224 L12-D011 is frozen as RECORDED**, with kit status BLOCKED_FOR_OWNER, after its cheap attempt failed. As §4.4 says, it has no WP-13.1 effect.
> - **The current tree** for the re-baseline is docs master `2d29aeb4` and code main `be07d20c`. The refs in the header below are the ones the check was run against.

# WP-13.1 baseline check (draft, read-only)

Prepared 2026-10-17 by Claude for Owner decision `minion-agent#75` issuecomment-6222791583, item 5.
**Preparation only. Nothing is authorized, implemented, posted or merged by this draft.**

```text
mode:            read-only baseline check (no fetch, no build, no test run)
docs compared:   origin/master 4dd294c0  (minion-agent-docs)
code compared:   origin/main   91a4ddef  (minion-agent)
scope baseline:  code 92aa4be1, docs ec36ed92, scope PR #124 @ 29bfe53b, closure 2026-09-21 (#47)
pinned Pi:       b7bb00b936dbe21b8e160b3e89efdec361846699 (unchanged)
```

Every claim below cites a file:line at those refs, a commit, or an issue comment. Anything not
checked against source is marked UNVERIFIED.

---

## 0. Headline finding: the premise needs correcting first

The cut-over decision says that the check "compares the closed Layer 13 scope (docs #124 `29bfe53b`,
code baseline `92aa4be1`, closure 2026-09-21) against the current baseline" and that "authorizing
Layer 13 itself stays the Owner's decision". The record shows something different: **WP-13.1 is
not a pending package. It was contracted, implemented and certified in both languages after the
scope closed.**

- `minion-agent#48`, "Layer 13 WP-13.1 — Native filesystem query tools (read, ls) —
  CERTIFIED_CLOSED", closed 2026-09-28. Its state block reads `wp131_certification: python CERTIFIED,
  rust CERTIFIED, cross_language CERTIFIED_CLOSED, open_findings: []`.
- Certified baselines (#48 state block, `wp131_certification.baselines`):
  - Python accepted at main `b60f4715` (#60). Rust accepted at main `9802721f` (#72).
  - RUST-I001 correction: docs `074b37f2` (#170), code `45579e1f` (#71).
  - Documentary sync: docs master `74094467` (#172), code main `32fe82d2` (#73).
- Post-closure hardening `minion-agent#74`, CLOSED 2026-09-28: five extra TOOL-025 witnesses (A-E).
  Accepted at code main `8a359d0e`, docs master `2f097fc6`. WP-13.1 semantics unchanged.
- `spec/tools.md:1057-1066` at `4dd294c0` still leads with that status.
- The other three packages are closed too: WP-13.2 `#49`, WP-13.3 `#50`, WP-13.4 `#51`. Layer 14
  WP-14.1/14.2 (`#158`/`#159`) are closed as well.

So the useful question is not "is WP-13.1 ready to start?" It is **"does certified WP-13.1 still
hold on today's lower layers, and what in its scope and contract text has gone stale?"** This draft
answers both forms:

- §2 lists every change since the scope baseline.
- The material ones are the **post-certification** changes (after docs `74094467` / code
  `32fe82d2`, and after #74's `2f097fc6` / `8a359d0e`).

Owner-facing consequence: a "Layer 13 authorization" for WP-13.1 would authorize nothing new. What
can still be decided is a **re-baseline (revalidation) of the certified package**, plus the
documentary corrections below (§6).

---

## 1. What WP-13.1 is

### 1.1 As scoped (scoping v4 and its carried-forward revisions)

- Definition: `13-built-in-tools-scoping-v2.md:159-162`:
  "WP-13.1 Native filesystem query tools: read, ls (no mutation queue, no subprocess, no
  external-binary dependency -- genuinely unblocked; can close first)".
- Readiness, as finally scoped: `13-built-in-tools-scoping-v4.md:101-102`, "`WP-13.1` `read`/`ls`,
  narrowly governance-blocked on `TOOL-027`'s unresolved disposition". The full correction is at
  `13-built-in-tools-scoping-v3.md:62-68`.
- v4 carries the rest forward unchanged: `13-built-in-tools-scoping-v4.md:97-108`, including
  "Path resolution, Truncation constants, Parity classification, Semantic authority, High-risk
  surfaces, Acceptance-oracle strategy, Cross-language impact, Open questions".
- Scoped requirement rows (`13-built-in-tools-scoping-v2.md:202-217`):

| ID | Scope text | Pi source | Classification | Depends on |
|---|---|---|---|---|
| `TOOL-025` | read: argument schema, offset/limit, truncation (head) | `read.ts`, `truncate.ts` | DIRECT_PI_PARITY | none |
| `TOOL-026` | read: file:// / path-argument resolution | `path-utils.ts` | MINION_ARCHITECTURAL_MAPPING | Layer 12 `resolve_local_path` |
| `TOOL-027` | read: macOS filename-fallback heuristics [owner disposition: adopt / drop] | `path-utils.ts` | PLATFORM_BEHAVIOR / MINION_EXTENSION | TOOL-026 |
| `TOOL-028` | ls: schema, case-insensitive sort, `/` suffix, stat-failure skip, entry-limit-after-skip, empty-directory text, byte truncation | `ls.ts`, `truncate.ts` | DIRECT_PI_PARITY | none |

- Pi symbols audited for WP-13.1:
  - `13-built-in-tools-scoping.md:71-77`: `read.ts` (358 lines, full), `ls.ts` (partial, then full
    per `v2.md:57`), `truncate.ts`, `path-utils.ts`, `utils/paths.ts:1-140`.
  - Path pipeline: `utils/paths.ts:95-97` `normalizePath`/`fileURLToPath` (`scoping.md:44-52`) and
    `resolveToCwd`/`resolveReadPathAsync` (`scoping.md:145-153`, `:330-343`).
  - Behavior: `read` at `scoping.md:142-168` (and v2's image correction, `v2.md:61-67`); `ls` at
    `scoping.md:286-295` and `v2.md:95-103`.
- Lower-layer requirements consumed, as scoped:
  - Layer 12 `EXEC-001`..`EXEC-006` (`scoping.md:19-28`).
  - Specifically `resolve_local_path` / `_file_url_to_path` for `file://` (`scoping.md:44-52`,
    `:376-377`, `v2.md:208`).
  - The scope closure: "Layer 13 consumes the certified filesystem/target/subprocess seams. No
    scoped rule requires a lower-layer semantic delta" (`13-built-in-tools-scope-final-closure.md:77-78`).

### 1.2 As certified (what actually binds today)

- Requirements are **TOOL-025, TOOL-026, TOOL-028, TOOL-039, TOOL-040**, with TOOL-027
  `NOT_ADOPTED_CORE`. Sources: #48 state block `requirements`; `spec/tools.md:1057-1058`; manifest rows
  `pi-parity-manifest.yaml:7463` (TOOL-025), `:7555` (TOOL-026), `:7614` (TOOL-027), `:7638`
  (TOOL-028), `:7997` (TOOL-039), `:8067` (TOOL-040) at `91a4ddef`.
  - TOOL-039 is the R010-B closed error vocabulary, `intentional divergence`.
  - TOOL-040 is the R006-C pinned ICU 78.3 collation, `intentional divergence`, with
    NORMALIZATION_MODE=ON.
- Owner decisions folded in (#48): TOOL-027 NOT_ADOPTED_CORE (#47 governance 2026-09-21), R002-A,
  R005-A (pinned Photon WASM), R006-C, R007-b (gave EXEC-007), R010-B, C012-A, then G1 (gave EXEC-008).
- Lower-layer requirements consumed, as certified:
  - `EXEC-002` path resolution (§3.2) via `absolute_path` and the operations below.
  - `EXEC-007` `list_dir_raw` / `probe_dir_entry`, for `ls` (`spec/execution.md` §11, normative
    consumption §11.5).
  - `EXEC-008` `check_readable`, for `read` (§12, consumption §12.5).
  - `read_binary_file`.
  - The certified `_file_url_to_path`, exposed as `file_url_to_path`, for TOOL-026 step 4.
  - The `FsErrorCode` taxonomy (§2.1).
  - Exact text: `spec/tools.md:1131-1139` (step 5) and `:1528-1549` (read operation mapping).
  - `read` never uses `file_info`, `canonical_path` or EXEC-007 (`spec/tools.md:1544-1545`; witness
    `builtin-read-does-not-depend-on-file-info-or-canonical-path.yaml`).
- Shared canonical evidence at the certified tree: 45 documents / 154 cases (#48
  `cross_language_closure.evidence`), raised by #74 to Rust 50 documents / 163 cases (#74
  `accepted_*`). At `91a4ddef` the `conformance/agent/` tree holds 50 `builtin-read-*` /
  `builtin-ls-*` files, plus the WP-13.1-relevant tool document `fs-path-domain/fs-path-tools.json`.

---

## 2. Changes merged since the scope baselines that touch WP-13.1's seams, sections, rows or requirements

Legend: **INVALIDATES** means a WP-13.1 scope or contract statement is now wrong. **REFINES** means
the statement stands, but its lower-layer meaning or observable outcome changed and should be
restated or re-witnessed. **UNTOUCHED** means checked, and no WP-13.1 effect.

### 2.1 Window A: scope closure to WP-13.1 certification (docs `ec36ed92..74094467`, 15 commits)

This window is WP-13.1 itself. It is listed for completeness. These are not deltas against a
certified package.

| Change | What it did | Effect on scoping v4 |
|---|---|---|
| WP-12.E1 / EXEC-007: docs #147 `bf4eacd`, #157, #158 `3f83681`; code certified at `578281fd` (#53) | additive `list_dir_raw` / `probe_dir_entry`, needed by `ls` (R007-b) | **INVALIDATES** the closure's "No scoped rule requires a lower-layer semantic delta" (`closure.md:77-78`) and v2's "no external ... dependency" framing: WP-13.1 needed two additive Layer-12 extensions |
| WP-12.E2 / EXEC-008: docs #163 `7007732`, #164, #165 `e1d9b81`; code `6dbec20a` (#62) | additive `check_readable`, Pi's `access` stage for `read` (owner G1) | same as above |
| WP-13.1 contract #160 `b1ed153`, R005-A #161 `f46051f`, impl-pass repairs #162 `5e395c6`, #169, #170 `074b37f`, #171 `e2f35bf`, #172 `7409446`; code #52/#59 → `cb8ed1c1`, #60 → `b60f4715`, #71, #72 → `9802721f`, #73 → `32fe82d2` | contract, both implementations, certification | supersedes v2's 4-row set with the 5-row certified set, adds pinned Photon WASM (R005-A) and pinned ICU4C 78.3 (R006-C) as **pinned external engine dependencies** of WP-13.1 |

### 2.2 Window B: after WP-13.1 certification (docs `74094467..4dd294c0`, 137 commits; code `32fe82d2..91a4ddef`)

The code paths below are unchanged since certification. `git log 32fe82d2..origin/main` on
`minion-agent-python/src/minion_agent/tools/builtin/{read,ls,paths}.py` returns no commits. Every
WP-13.1 movement is therefore **inherited from Layer 12 / Layer 05-06**, not authored in the tools.

| # | Change (issue; docs / code) | Delta | What changed (verified in diff / spec text) | WP-13.1 effect |
|---|---|---|---|---|
| B1 | `#74` hardening; docs #174/#175 → `2f097fc6`, code #76/#77 → `8a359d0e` | — | five discriminating TOOL-025 witnesses (BMP hint, `toFixed` tie, JPEG candidate, size cutoff, APNG) | **UNTOUCHED** (adds evidence only; M21 boundary stays the accepted limit) |
| B2 | `#115` EXEC-002-R1-PY-STR; code #117 → `564da41` (2026-10-02); closes `#66` | Layer-12 remediation | Python `read_text_file` decodes bytes like Node (no newline translation) | **UNTOUCHED** in behavior: `read` decodes `read_binary_file` itself. The parenthetical at `spec/tools.md:1579-1581` ("Python's text-mode file reading translates newlines") is now historical, see §3 S12 |
| B3 | WP-12.E3 / EXEC-009; docs `f70a714` §13, `148e719`; code `ada1032` | additive | `check_read_write` for `edit` | **UNTOUCHED**: read/ls do not call it |
| B4 | `#78` documentary; docs `8241a98` (`spec/execution.md:578-588`) | documentary | `resolve()` fallback set is not DIRECT_PI_PARITY | **UNTOUCHED**: WP-13.1 never uses `resolve()`/`FsTarget` (`spec/tools.md:1161-1173`) |
| B5 | WP-13.2 contract; docs `59eba17` (#178) | Layer 13 sibling | added "Shared preprocessing versus tool-specific dispatch" (`spec/tools.md:1145-1148`) and extended the R010-B vocabulary to WP-13.2 by `L13-WP132-O1` (`:1475-1476`) | **REFINES** wording only. The diff hunk states "`read` and `ls` use the read-only dispatch written in step 5, unchanged". These are the only two edits to the WP-13.1 section (`git diff 74094467 origin/master -- spec/tools.md`, hunks `@@ -631` and `@@ -956`) |
| B6 | `#123` L12-D001 JS-string path domain; docs `c8a7f77` (§14), `9200d13`; code `4c735ed` (#124 Python), Rust candidate per docs #231 | L12-D001 | A `ctx.fs` path is a JavaScript string (lone surrogates allowed); native projection only at the OS call (`spec/execution.md:2668-2686`); `absolute_path` logical (`:2700`). §14.5 (`:2734-2737`): the **Rust tools must stop refusing a non-scalar path ("path is required") and `ls` must stop substituting `"."`**. Tool-level canonical doc `fs-path-tools` (5 cases through the real `write`/`read`/`ls`/`edit`, `:2750`) | **REFINES** TOOL-025/026/028's input domain from scalar strings to JS strings. This was a real Rust WP-13.1 behavior change after certification, governed as an additive L12 delta that "does not reopen" WP-13.1 (`:2659`). Scoping v4 is silent on the domain |
| B7 | WP-12.E4 / EXEC-010; docs `31294d3` §15 | additive | execution-world environment/platform | **UNTOUCHED**: TOOL-026 step 3's Windows test is the host (`paths.py:72` `os.name == "nt"`), not EXEC-010 |
| B8 | Layer 05/06 deltas L0206-D001 (`8521106`), L0206-D002 (`2ef3828`), L05-D001 (`c624330`), L0506-D001 (`a8041e0`…`7b51664`, TOOL-041 numeric ±Infinity/−0), L0506-D002 (`74f125e`), L0506-D003 (`7d73072`), L0506-D004 (`20776f0`, TOOL-042 per-call context), L0506-D005 (`fbdbc67`) | Layer 05/06 | argument/result value domains and the per-call context for **every** tool | **REFINES** at the tool boundary (the `path`, `offset`, `limit` argument domains WP-13.1 receives). The WP-13.1 spec section cites none of them (`grep TOOL-041\|L0506\|TOOL-042` over `spec/tools.md:1104-2001`: no hit). Whether read/ls canonical cases cover the ±Infinity/−0 prepared domain: **UNVERIFIED** |
| B9 | `#163` L12-D004; docs `1c148c4`, `9f15b92`; code `5477eae` | L12-D004 | Python `canonical_path` on POSIX via libc `realpath(3)`, giving Linux ELOOP → `unknown` | **UNTOUCHED**. The D004 record lists `TOOL-025` as a downstream consumer (`12-l12-d004-canonical-path.md:111`), but certified `read` never calls `canonical_path` (`spec/tools.md:1544`; witness `builtin-read-does-not-depend-on-file-info-or-canonical-path`), and Python `check_readable` uses libc `access(2)` (`filesystem.py:957-967`). That record line is inaccurate; note it, no WP-13.1 action |
| B10 | `#188` L12-D005; docs `4ce6aa6` §17; code `4efa52f` | L12-D005 | Windows `remove` ignores read-only | **UNTOUCHED** |
| B11 | `#194` L12-D006 (closes `#65`, `#133`-F1); docs `e499c91` §18, `cbb2873`; code `0ab81a0` (Python), `29089a88` (Rust) | L12-D006 | a native call whose path contains U+0000 fails `Err(unknown)` with the logical path (`spec/execution.md:3155-3161`), including EXEC-007/008 (`:3176-3178`). **Tool boundary specified** (`:3198-3205`): `read` → `Cannot access <absolute>: unknown filesystem error` (at `check_readable`); `ls` → `Path not found: <path>` | **REFINES** TOOL-025/026/028 with a new defined outcome. Before D006, Python raised `ValueError` (host exception escape, `#65`). Not in scoping v4 or the certified WP-13.1 witness matrix; witnessed in `fs-path-nul.json` (237 cases) and binding tool-boundary tests (`:3219`) |
| B12 | `#199` L12-D007 (closes `#67`, `#69`, `#125`); docs `e652cc8` §19, `dd9fd15`; code `51e53ba` (Python), `68793a31` (Rust) | L12-D007 | `FsErrorCode` = pinned Pi's literal `toFileError` result per op/input/host (`spec/execution.md:3249-3292`, §2.1 corrected `:143-155`). Windows directory read → `is_directory` when libuv's open succeeds (`:3280`, `:3289`); Windows link loop → `unknown` (`:3268`, `:3288`). EXEC-007/008 failure classification follows the corrected mapper (`:3309-3313`) | **INVALIDATES** the certified `read` disclosures W-2 and W-3 (`spec/tools.md:1571-1575`). W-3's "a readable Windows directory reads `Cannot read <path>: permission denied`" is now `Cannot read <path>: is a directory` (Pi's phrase). W-2's "Windows symlink-loop CODE is the Layer-12 mapper's (#69)" is now Pi's `unknown`. Both changes move the bindings **toward** Pi. **REFINES** the `ls` per-entry skip (EXEC-007 codes changed, the skip is code-agnostic, so `ls` output is unchanged) and `read`'s cause phrase on Windows |
| B13 | `#215` L12-D008 / DIV-008; docs `4eba7f6` §20; code `e925266` | L12-D008 | recursive `remove` | **UNTOUCHED** |
| B14 | `#224` L12-D011 (Python only merged); docs `a080af4` §21, `f065a0c`, `aa06a61`; code `be02f9f3`, `f9935672` | L12-D011 | NUL in a **spawn** input; tool boundary is `find`/`grep`/`bash` only (`spec/execution.md:3576-3586`); filesystem codes unchanged (`:3598`) | **UNTOUCHED** |
| B15 | `#229` L12-D012; docs `b0b3de6`, `b2e8148`, `3cfb799`, `d69c9e2`; code `5a244f13` (contract), `8bb165e5` (Python F002), `83a78655` (Rust F001); corpus `conformance/agent/path-resolution/path-resolution.json` | L12-D012 | §3.2 **not reopened**. Implementations corrected to it: win32 drive-relative other-drive selection reads `=D:` then process cwd (`12-l12-d012-path-colon.md` §2-§3.1); colon-bearing components are ordinary except a leading `X:` device; Rust's malformed `file:` literal fallback | **REFINES** the absolute target and `<path>` text of `read`/`ls` for inputs like `c:d`, `a::/b`, `x/c:/d` on win32. The record states "TOOL-026 is a neighbor ... not reopened" and keeps `builtin-*-malformed-file-url-rejected…` as certified (`12-l12-d012-path-colon.md:5`, `:157`). R002-A step 4 is untouched because it intercepts `file://` before `ctx.fs` |
| B16 | `#235` L12-D013 (Python merged, Rust in flight); docs `349bef8` (§3.2 rooted rule), `c311119`, `4dd294c` (§22.1/§22.5); code `393138f8` (#238), `91a4ddef` (#239); Rust draft #242 @ `1c0a1783` | L12-D013 + DIV-009 | win32 rooted drive-less (`\leaf`, `/leaf`) and incomplete-UNC inputs take the **process** cwd's device, never the provider cwd's (`spec/execution.md:344-366`); POSIX `//leaf` → `/leaf`. **DIV-009** (`:95-100`, §22): a failed native process-cwd read is a typed `Err(FsError)` from **every** resolving operation, `absolute_path` included (`:3661-3664`) | **REFINES** `read`/`ls` targets and `<path>` text for rooted/UNC inputs on win32 (Python now matches Pi; Rust pending revalidation). **Exposes one small contract gap**: `ls`'s `<path>` is defined as "what `ctx.fs.absolute_path` returns" (`spec/tools.md:1716-1718`) with no failure case, while `read` defines a fallback (`:1548-1549`, "if that call itself fails, the step-5 string"). Before DIV-009, `absolute_path` was effectively infallible. Both bindings already fall back to the step-5 string: Python `ls.py:53-54` (`directory = working if isinstance(resolved, Err) ...`), Rust `ls.rs:42-44` (`unwrap_or_else(\|_\| working.clone())`). So this is a spec-wording gap, not a behavior gap |
| B17 | Manifest rows TOOL-025..028/039/040 after `32fe82d2` | — | TOOL-025/028: `tests:` additions only (L12-D001 `fs-path-tools.json`; the five #74 scenarios on TOOL-025). TOOL-026: the "Scope extension (WP-13.2 …)" note and a `python:` write/edit note. TOOL-039: names WP-13.2, plus the `L13-WP132-O1` paragraph. TOOL-027, TOOL-040, EXEC-007 and EXEC-008: byte-identical | **UNTOUCHED** in rule text: every addition says "WP-13.1's certification ... unchanged". TOOL-026's "not yet certified" tail is stale (S12) |

Frozen, no merged change: `#236` L12-D014 (`~` home source) and `#241` L12-D015 (Rust extended
`\\?\` provider cwd). See §4.

### 2.3 Code-side detail (manifest, Python/Rust execution, canonical corpus)

Read-only `git log`/`git show` on `origin/main`, `32fe82d2..91a4ddef`. Between `32fe82d2` and
`8a359d0e` no source file changed (#74 added tests and scenarios only).

**WP-13.1 tool source.**

- **Python:** no commits to `tools/builtin/{read,ls,paths,_signal,image,mime,truncate,_js}.py`.
  `collation.py` gained two additive helpers: `53290de` (#87, WP-13.2, `nfkc_unicode16`) and
  `3f98a22` (#138, WP-12.E4, `upper_unicode16`). The `ls` key and compare path is unchanged.
- **Rust:** `tools/builtin/{read,ls,paths}.rs` were touched only by domain deltas: `ee87245` (#94,
  L0506-D001), `2bb8e68` (#120, L0506-D003), `ed0d810` (#132, L12-D001) and `b88b6a7` (#134,
  L0206-D001/K1). Rust semantics were not analysed (ownership rule); the B6 effect comes from the
  spec text.

**Canonical scenarios.**

- No `conformance/agent/builtin-read*` or `builtin-ls*` file changed after `8a359d0e`, so no WP-13.1
  expected output changed.
- New Layer-12 corpora that reach read/ls seams:
  - `fs-path-domain/fs-path-tools.json` (D001, `4c735ed`): tool level;
  - `fs-path-nul.json` (D006, `0ab81a0`): `check_readable`, `read_binary_file`, `probe_dir_entry`,
    `list_dir_raw`, `absolute_path`;
  - `fs-error-codes.json` (D007, `51e53ba`);
  - `path-resolution/path-resolution.json` (D012 `5a244f1`, extended by D013 `393138f`).

**Python `execution/**`, read/ls-observable.**

- `564da41` (B2): none.
- `4c735ed` (B6): surrogate paths become addressable; tool text stays logical through `absolute_path`.
- `5477eae` (B9): none.
- `0ab81a0` (B11): `_contain_nul`, so a NUL path is `Err(unknown)` with the logical path. This
  replaces an escaping `ValueError`.
- `51e53ba` (B12): `errors.to_pi_fs_error` plus `_libuv_win32.py`:
  - Windows directory read → `is_directory`;
  - link loop through `check_readable` → `unknown` (it was `invalid`);
  - sharing violation → `unknown`;
  - Win32 123/267 → `not_found`.
  - **The certified WP-13.1 test `tests/tools/builtin/test_read_access_and_abort_order.py::test_w_g11`
    was edited in this commit** to assert `Cannot read <p>: is a directory` on every platform. So
    W-3's retirement is already witnessed at binding level, though not by a shared canonical case.
- `8bb165e` (B15): on win32, another-drive drive-relative input now goes through Node's literal
  `win32.resolve` branch.
  - A **bare `file:` without `//`** (e.g. `file:a%2Fb`) is not intercepted by TOOL-026 step 4,
    which tests for `"file://"` (`spec/tools.md:1123`). So it reaches `resolve_local_path` and
    takes D012's colon-component rule.
  - That is already DIRECT_PI_PARITY: Pi's `normalizePath` also only converts `file://`. It is
    worth one WP-13.1 re-baseline witness. **UNVERIFIED** whether a builtin case covers it today.
- `393138f` (B16): the rooted/UNC-root rule (`filesystem.py:226-235`), the POSIX `//leaf` collapse
  (`:244-247`), and DIV-009's `ProcessCwdReadError` → `Err(FsError)` from every op, `absolute_path`
  included.
  - Under DIV-009, `read` answers `Cannot access <step-5 string>: <cause>`.
  - `ls` answers `Path not found: <step-5 string>`. That fallback is what S13 asks the spec to state.
- `e925266`, `4efa52f`, `3f98a22`, `c06e1c7`, `f993567`: no read/ls effect.

**Rust `execution/**` commits on main** (listed, not analysed):

- `ed0d810` (D001), `29089a8` (D006), `68793a3` (D007), `fd6c025` (D005), `f740098` (D008),
  `83a7865` (D012 F001);
- `50186ab`, `a0ff3e4` (EXEC-010), `62caa15`, `59cab4a`, `8a2a394`, `161ea5d`.

**No Rust L12-D013 commit is on main yet** (#242 is a draft).

**Per-binding state of the frozen surfaces at `91a4ddef`:**

- **`~` (#236).**
  - Python `execution/filesystem.py:190-193`: `os.path.expanduser("~")`. On Windows that reads
    `USERPROFILE`, with `HOME` ignored; on POSIX it reads `HOME`, then pwd; `~\` is accepted on nt
    only.
  - Rust `crates/minion-agent/src/execution/path.rs:129-134`: `HOME`, then `USERPROFILE`, so `HOME`
    comes first on Windows too.
  - Pi `os.homedir()`: on win32 `USERPROFILE`, never `HOME`.
- **Extended `\\?\` provider cwd (#241).**
  - Python uses the provider cwd raw (`filesystem.py:206-235`) and matches all 48 frozen rows.
  - Rust `path.rs:32-47` (`logical_provider_path` → `without_extended_prefix`) strips `\\?\` and
    `\\?\UNC\`: 12 of 48 rows differ.

**Manifest Layer-12 rows WP-13.1 consumes.**

- EXEC-002 gained these tests:
  - `fs_path_javascript_string_domain` (D001);
  - `fs_remove_readonly_windows` (D005);
  - `fs_path_nul_unknown` (D006);
  - `fs_error_codes_pinned_pi_literal` (D007);
  - `fs_path_resolution_colon_and_drive_relative` (D012, cross-language CLOSED);
  - `fs_path_resolution_rooted_and_unc_root` (D013, Rust REVALIDATE_REQUIRED);
  - `process_cwd_read_failure` (DIV-009).
- New rows: EXEC-002-DIV-008, EXEC-002-DIV-009, EXEC-009, EXEC-010, EXEC-012, EXEC-013.
- EXEC-007 and EXEC-008 are unchanged.

---

## 3. Stale statements in scoping v4 (with what v4 carries forward), and proposed corrections

The scoping artifacts are reviewed historical records and must not be edited (CLAUDE.md, "Preserve
historical review artifacts"). Each correction is therefore proposed for a **new** appended record
(for example `13-wp131-rebaseline-<date>.md`), never as an edit to v1-v4.

| ID | Stale statement (file:line) | Why stale | Proposed correction |
|---|---|---|---|
| S1 | `scoping-v4.md:101-102` "WP-13.1 ... narrowly governance-blocked on TOOL-027's unresolved disposition"; `scoping-v3.md:62-68`; `scoping.md:599-613` open question 3 | TOOL-027 was dispositioned `NOT_ADOPTED_CORE` on 2026-09-21 (#47 state block `owner_governance_decisions`), and WP-13.1 has been CERTIFIED_CLOSED since 2026-09-28 (#48) | "WP-13.1 CERTIFIED_CLOSED (#48); TOOL-027 NOT_ADOPTED_CORE; certified baselines docs `74094467` / code `32fe82d2`, hardened by #74 at `2f097fc6` / `8a359d0e`." |
| S2 | `scoping-v4.md:18-22` starting state `92aa4be1` / `ec36ed92` | historical only. The WP-13.1 baseline is now the certified tree plus §2.2's deltas | new baseline: docs `4dd294c0`, code `91a4ddef` (or the tips at re-baseline time), pinned Pi unchanged |
| S3 | `scoping-v2.md:202-217` WP-13.1 = TOOL-025..028 | the certified set is TOOL-025, 026, 028, 039, 040 (027 not adopted) | restate the 5-row set with TOOL-039/040 as `intentional divergence` (R010-B, R006-C) |
| S4 | `scoping-v2.md:160-162` "no external-binary dependency -- genuinely unblocked" | certified `read` requires the pinned Photon WASM (sha256 `10468181…`, `spec/tools.md:1596-1600`); `ls` requires pinned ICU4C 78.3 collation (R006-C, TOOL-040) | "no subprocess, no mutation queue; two pinned engine dependencies: Photon 0.3.4 WASM (R005-A) and ICU4C 78.3 (R006-C)" |
| S5 | `scope-final-closure.md:77-78` "No scoped rule requires a lower-layer semantic delta"; `scoping.md:44-52` | WP-13.1 needed two additive Layer-12 extensions (EXEC-007, EXEC-008), and has since inherited L12-D001/D006/D007/D012/D013 | "WP-13.1 consumes EXEC-002 (§3.2 as amended by L12-D012/D013 and DIV-009), EXEC-007, EXEC-008, `read_binary_file`, `file_url_to_path`, the §2.1 taxonomy as corrected by L12-D007, the §14 JS-string domain and the §18 NUL rule" |
| S6 | `scoping.md:19-28` Layer-12 inventory `EXEC-001..006` with `filesystem.py:559/565/553/814` line refs | Layer 12 now runs to EXEC-013 plus DIV-008/009; the line numbers have moved | replace with the requirement IDs and spec sections above; drop the line numbers |
| S7 | `scoping.md:44-52`, `:376-377` "`file://` ... should route through Layer 12's ... `ctx.fs`/`resolve_local_path` seam" | superseded by R002-A: TOOL-026 step 4 calls the strict conversion **before** `ctx.fs` and rejects malformed URLs (`spec/tools.md:1123-1130`, `:1186-1196`) | "`file://` is converted at TOOL-026 step 4 by the certified strict conversion; `resolve_local_path`'s own `file://` handling is never reached for WP-13.1 (`spec/tools.md:1139-1142`)" |
| S8 | `scoping.md:330-343` Path resolution: "expands a leading `~`/`~/`/`~\` against `os.homedir()`" (and Pi-parity framing at `:401-403` "path resolution (paths.ts)" `PI_SOURCE_ALGORITHM`) | Owner decision 2026-10-17 (#75 issuecomment-6222791583 item 3): Layer 13 claims **no parity** for the home-directory source while #236 is frozen, and inherits per-binding Layer-12 behavior | add the #236 marker (§4.1) to every `~` statement |
| S9 | `scoping.md:339-341` "Relative results are resolved against `cwd` via Node's lexical `path.resolve`" | on win32, a rooted drive-less input uses the **process** cwd's device (L12-D013), and a drive-relative other-drive input selects `=D:` then the process cwd (L12-D012). The provider cwd is not the only base, and DIV-009 makes resolution fallible | "resolution is Layer 12 §3.2 as amended (L12-D012, L12-D013) with DIV-009's typed failure; an extended `\\?\` provider cwd: no parity claimed (#241, Rust)" |
| S10 | `scoping.md:580-582` oracle "path resolution (tilde, @, Windows shell paths, file://) -- fixed behavior matrix per platform" | tilde cannot carry a parity oracle while #236 is frozen; the rest is owned by Layer 12's `path-resolution.json` corpus | drop tilde from the WP-13.1 oracle; cite `conformance/agent/path-resolution/path-resolution.json` (L12-D012/D013) for resolution |
| S11 | `scoping.md:79-95` "Conclusion: clean slate. No pre-existing code" | both bindings implement read/ls (`tools/builtin/read.py`, `ls.py`; `crates/minion-agent/src/tools/builtin/read.rs`, `ls.rs`) | "certified implementations exist; re-baseline audits them per the Existing-code rule" |
| S12 | (contract, not scoping) `spec/tools.md:1567-1576` W-2/W-3; `:1579-1581` newline parenthetical; `:1676-1678` `ls` status "CONTRACT_INTEGRATED, pending ... final ... review"; manifest TOOL-026 `rule` tail "WP-13.2 contract draft ... not yet certified" (`pi-parity-manifest.yaml` TOOL-026 row) | W-2/W-3 closed by L12-D007 (B12); #66 fixed by B2; `ls` certified; WP-13.2 CERTIFIED_CLOSED (#49) | documentary status sync of `spec/tools.md` WP-13.1 and the TOOL-026 row, appended, with the earlier text kept as history, as the #172/#73 pattern did |
| S13 | (contract gap) `spec/tools.md:1716-1718` `ls` `<path>` with no `absolute_path`-failure case | DIV-009 (B16) made `absolute_path` fallible | add "if that call itself fails, the step-5 string", mirroring `read` (`:1548-1549`). Both bindings already do this (B16). Classification proposal: `CONTRACT_ASSURANCE_DEFECT`, documentary, behavior-neutral, plus a binding witness |
| S14 | `scoping.md:142-168` and `:286-295` say nothing about the path value domain | L12-D001 extended it to JS strings; L12-D006 defined NUL outcomes at the tool boundary | cite §14 and §18.3 as inherited WP-13.1 behavior |

---

## 4. Where WP-13.1 touches `~` expansion and provider-cwd forms; `#224`

### 4.1 `~` (#236, L12-D014, frozen `WAITING_FOR_TRIGGER`)

**Exposure.** `read` and `ls` never expand `~` themselves. TOOL-026 step 5 hands the preprocessed
string to `ctx.fs`, where "Tilde expansion, absolute-path normalization, and cwd-relative resolution
all happen INSIDE that provider call, via the SAME already-certified resolve_local_path logic"
(`spec/tools.md:1135-1139`). That makes the home-directory source observable in:

- `read`'s target and its `<path>` text: `<path> = ctx.fs.absolute_path(<step-5 string>)`
  (`spec/tools.md:1548-1549`);
- `ls`'s target, its `<path>` text (`:1716-1718`) and its per-entry joins (`:1735`), for any `path`
  argument equal to `~` or starting with `~/`, or `~\` on win32 (`spec/execution.md:335-336`).

**Current canonical evidence does not depend on it.**

- `git grep '"~'` over `conformance/` at `91a4ddef` hits only binary image fixtures.
- None of the 50 `builtin-read-*` / `builtin-ls-*` documents, `fs-path-tools.json` or
  `path-resolution.json` uses a `~` path.
- No Python builtin tool test uses one (`tests/tools/builtin`, `git grep "~"`: no hit).

**Rows and statements that must carry the marker** "`~` home-directory source: no parity claimed;
inherits per-binding Layer-12 behavior (#236, frozen)":

1. Manifest `TOOL-026` (`pi-parity-manifest.yaml:7555`). Its `pi:` field cites
   `utils/paths.ts:75-106` and `nodejs.ts:51-65` (both contain the `~` branch), and its
   `disposition` is `adopted`. Today nothing excludes `~` from that adoption.
2. Manifest `TOOL-025` (`:7463`) and `TOOL-028` (`:7638`), where they describe resolution or
   `<path>` text.
3. `spec/tools.md:1135-1139` (TOOL-026 step 5).
4. The scoping text at S8/S10 (in the appended record, not by editing v1).
5. Any future WP-13.1 re-baseline witness. **Rule: no Layer-13 case may use a `~` path**. If one
   cannot avoid it, it carries `#236` in its `platform_note` / `notes`, and its expectation is the
   binding's, not Pi's.

There are **no existing Layer 13 cases to re-mark**: none depends on the home source.

### 4.2 Extended `\\?\` provider cwd (#241, L12-D015, frozen)

**Exposure.**

- Rust's public `ctx.fs` strips an extended prefix from the provider cwd before resolution
  (`spec/execution.md:3648-3650`, `:3694-3703`).
- For provider `\\?\C:\base`, Pi resolves `leaf` → `\\?\C:\base\leaf` and `""` → `\\?\C:\base`;
  Rust gives `C:\base\leaf` and `C:\base`, with 12 of 48 rows different (#241 state).
- Merged Python matches all 48 rows (`:3700`).
- For WP-13.1 this affects every relative or empty `path` on a Rust provider whose cwd is
  extended, including `ls`'s default `"."` (`spec/tools.md:1690-1691`, `:1715`). The `<path>` text
  and the targets differ.

**Rows and statements that must carry the marker** "extended (`\\?\`) provider cwd: no parity
claimed (#241, frozen)":

- manifest `TOOL-026`;
- manifest `TOOL-028` (default `"."`);
- `spec/tools.md:1131-1139` (step 5);
- `spec/tools.md:1715-1718` (`ls` `<path>`).

**Canonical evidence.** No `builtin-*` case uses an extended provider cwd (`git grep '\\\\?\\'` over
`conformance/agent/builtin-*`: no hit). The L12-D013 corpus's
`win32/host/rooted-extended/*` rows are **rooted** inputs, whose extended rows equal their ordinary
pairs (`spec/execution.md:3703`). They are not affected by #241 and need no marker.

### 4.3 Adjacent, not frozen: provider cwd without an absolute root

`spec/execution.md:3645` and `:3692` record that merged Python joins instead of reading the process
cwd when the provider cwd itself is relative or empty. It is "a recorded observation for separate
governance" and is not frozen by the 2026-10-17 decision. WP-13.1 cases always use an absolute
sandbox cwd, so they do not reach it.

Proposed handling: treat it like #241. No parity is claimed for a non-absolute provider cwd, and no
Layer-13 case uses one. **The Owner should confirm** that this falls under the same rule (it is not
explicitly covered by item 3 of the decision).

### 4.4 `#224` L12-D011 (NUL in a spawn argument)

- **Scope.** L12-D011 touches only `ctx.subprocess` spawn inputs: executable, argv, env, `options.cwd`
  (`spec/execution.md:3482-3600`). Its tool boundary is `find`, `grep` and `bash`
  (`:3576-3586`), and filesystem error codes are explicitly unchanged (`:3598`).
- **WP-13.1 has no spawn.** NUL handling for `read`/`ls` is L12-D006's filesystem rule (B11), which
  is already CERTIFIED_CLOSED in both bindings (#194).
- **If #224 closes:** no WP-13.1 effect.
- **If #224 is frozen as RECORDED:** no WP-13.1 effect. Python's merged §21 behavior and Rust's
  unimplemented one stay a WP-13.3/13.4 matter only.
- **WP-13.1 does not depend on #224 either way.** The only rule needed is negative: no WP-13.1
  re-baseline witness may route a NUL through anything but `ctx.fs`.

---

## 5. Open Layer-12 items: status and WP-13.1 dependency

Status from each issue's state block, read 2026-10-17. Issue dates are last-updated.

| Issue | Status (state block) | Remaining | WP-13.1 dependency |
|---|---|---|---|
| `#235` L12-D013 (2026-10-16) | `RUST_IMPLEMENTATION`, consequence governing/CP-6; EXEC-002/005; CE-L12D013-01 AGREED; open findings none; `L12D013-RUST-C001` provisionally closed. Python merged (code `393138f8`, docs `349bef8b`; sync `91a4ddef` / `c311119c`; C001 clarification docs `4dd294c0`) | Rust draft #242 @ `1c0a1783`: the Windows exact-head run was active and Linux pending (issuecomment-6221204306), not yet recorded; then handoff, Claude's independent Rust closure review, status sync, close. Diagnostic drafts code #240 and docs #315 are not to be merged | **YES (soft).** It is the resolver for every WP-13.1 `ctx.fs` call (rooted / UNC-root inputs, DIV-009 → S13). Python is already aligned. A WP-13.1 re-baseline should start **after** #235 closes, as the Owner already ordered (item 5) |
| `#224` L12-D011 (2026-10-15) | `RUST_IMPLEMENTATION`; EXEC-013/005, TOOL-034/036/037; `L12D011-RUST-F001` open pending independent closure (its blocker #229 merged). Python merged | Rust draft #228 @ `f611770a` (rebased on `83a78655`), "not review-ready"; exact-head Windows-then-Linux G3 gates; or freeze as RECORDED (Owner item 2) | **NO** (§4.4) |
| `#207` L12-D010 (2026-10-11) | RECORDED, "track separately" (#199 issuecomment-6113189438); no state block / work package | Windows exotic reparse points (volume-GUID junction, non-surrogate tag, malformed APPEXECLINK) vs libuv's readlink-gated `lstat`/`unlink` classification | **MARGINAL, UNVERIFIED.** It could change `ls`'s `probe_dir_entry` kind (the `/` suffix or skip) for those entries on Windows. Not characterized for EXEC-007. Proposed: no claim for such entries; no WP-13.1 case uses them |
| `#195` L12-SPAWN-NUL (2026-10-13) | RECORDED; Owner decision issuecomment-6137514688 carried out as #224 | provenance record only | **NO** |
| `#193` L06-RUST-CYCLIC-VALIDATION (2026-10-09) | RECORDED, out of scope for L0506-D005 | Rust stack overflow on a cyclic prepared graph; only a custom `prepare_arguments` shim can produce one | **NO** (no built-in tool produces such a graph) |
| `#133` L12-D001 follow-up (2026-10-10) | RECORDED; F1 resolved by L12-D006 (#194). **F2 open**: Owner "APPROVE OPTION 1: ADOPT PINNED PI NATIVE-NAME DECODING" (issuecomment-6086601508) authorizes a contract-first L12 delta naming `list_dir_raw`/`probe_dir_entry`. No delta issue or ID was ever allocated ("L12-D008" in comment 6101817955 went to DIV-008) | unscheduled | **YES for `ls`, edge only.** For non-Unicode native names, `ls` output differs from Pi today: POSIX non-UTF-8 bytes, Windows lone surrogates (Pi: three U+FFFD per surrogate; Rust: one; Python: raw surrogates). The difference reaches the listing text, the sort keys and the per-entry joins. Not a blocker under the Owner's process lesson (edge case → RECORDED). It needs an explicit "no parity claimed for non-Unicode native names until #133-F2" marker on TOOL-028/TOOL-040 |

Already closed and inherited (no longer open): `#65` (L12-D006), `#66` (B2), `#67` and `#69`
(L12-D007), which retire W-2/W-3 (S12). Frozen: `#236`, `#241` (§4).

**Which ones WP-13.1 depends on:**

- **#235: sequencing only.** Re-baseline after it closes.
- **#133-F2 and #207: no-parity markers** for their edge domains.
- **#224, #195, #193: none.**

---

## 6. Verdict

```text
VERDICT: NEEDS SCOPE DELTA  (documentary re-baseline of a CERTIFIED package; not BLOCKED)
```

This is not "READY: baseline refresh only". The changes needed are more than new SHAs: one stated
disclosure is now wrong (W-2/W-3), one contract sentence is missing (S13), and three no-parity
markers must be added. It is not BLOCKED either: no open item stops WP-13.1, and certified
behavior has only moved toward Pi.

**Scope delta list (all documentary or contract-wording; no Python or Rust semantic change is
proposed):**

1. **Status correction (S1-S3, S11).** WP-13.1 is CERTIFIED_CLOSED. TOOL-027 is NOT_ADOPTED_CORE.
   The requirement set is TOOL-025/026/028/039/040. Record the new baseline (docs/code tips after
   #235 closes).
2. **Dependency restatement (S4-S7, S9, S14).** Pinned Photon WASM and ICU4C 78.3. EXEC-002 §3.2
   as amended by L12-D012 and L12-D013, DIV-009, EXEC-007, EXEC-008, the §14 JS-string domain, the
   §18 NUL tool boundary, and the §19 corrected codes.
3. **Retire W-2/W-3** (`spec/tools.md:1571-1575`) as closed by L12-D007. A Windows readable
   directory is now `Cannot read <path>: is a directory` when libuv's open succeeds, and a Windows
   link loop is `unknown`.
   - The binding test `test_read_access_and_abort_order.py::test_w_g11` was already updated in
     `51e53ba` (§2.3).
   - No shared canonical `builtin-read` case pins the Windows directory outcome: no builtin
     scenario changed after `8a359d0e`. Proposed: add one, Windows-gated.
   - Also add one witness for a bare `file:` (no `//`) path reaching the resolver (§2.3, B15).
4. **S13**: `ls` `<path>` falls back to the step-5 string when `absolute_path` fails (DIV-009).
   Wording only; both bindings already comply (`ls.py:53-54`, `ls.rs:42-44`). Add a binding
   witness.
5. **No-parity markers:**
   - `~` (#236) on TOOL-026 (and TOOL-025/028 resolution text) and on `spec/tools.md:1135-1139`;
   - extended `\\?\` provider cwd (#241, Rust) on TOOL-026/TOOL-028 and on `spec/tools.md:1715-1718`;
   - non-Unicode native names (#133-F2) on TOOL-028/TOOL-040;
   - optionally, Windows exotic reparse entries (#207) and a non-absolute provider cwd (§4.3,
     needs Owner confirmation).
6. **Documentary sync (S12)** of `spec/tools.md:1579-1581` and `:1676-1678`, and of the manifest
   TOOL-026 tail ("WP-13.2 ... not yet certified").
7. **Revalidation run (evidence, not semantics).** Fresh full WP-13.1 canonical suites (50
   `builtin-read/ls` documents plus `fs-path-tools`) on the post-#235 tree in both bindings, through
   Codex's build queue (#209), with no new behavior expected.
   - **Rust only:** confirm the B6 tool changes (non-scalar path accepted, no `"."` substitution)
     are in the certified tool paths.
   - UNVERIFIED whether the WP-13.1 suites have run green on every post-certification tip.
     Plausible, since each L12 delta reports full gates, but not checked here.

**Proposed next step for the Owner's authorization.**

1. Confirm the premise correction in §0: WP-13.1 is CERTIFIED_CLOSED, and the request is a
   re-baseline, not a first authorization.
2. After #235 closes, authorize a **WP-13.1 re-baseline work package**. Proposed classification:
   kind `delta`, documentary consequence class, to be checked against kit `consequence-classes.md`.
   It would consist of:
   - one docs PR: an appended re-baseline record plus the `spec/tools.md` WP-13.1 status, W-2/W-3,
     S13 and marker edits;
   - one code PR: the TOOL-025/026/028/039/040 manifest marker and status edits;
   - a Codex-scheduled exact-head revalidation run of the WP-13.1 suites in both bindings;
   - an independent Codex review.
3. Decide two small points with it:
   - whether a non-absolute provider cwd (§4.3) and #207's reparse entries take the same
     "no parity claimed" rule as #236/#241;
   - whether #133-F2 stays RECORDED for Layer 13 (proposed: yes).
4. Any further Layer 13 work beyond WP-13.1 is a separate Owner decision. All four Layer 13
   packages are already closed, so the "next layer" after the Layer 12 cut-over is Layer 15, since
   Layer 14 is also closed. **UNVERIFIED** whether Layer 15 scoping has started; not checked here.
