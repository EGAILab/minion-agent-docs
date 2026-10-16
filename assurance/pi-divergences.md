# Approved Pi divergences

This is the canonical, human-readable registry of **accepted** differences between Minion and pinned Pi.

**Policy.** Owner decision, 2026-10-04: practical Pi compatibility (`minion-agent#75` comment `5973629428`; `process/agent-workflow.md` §1 and §6.1).
- A divergence is listed here only after Owner governance.
- Each one has a permanent witness, and a parity-manifest row with the `intentional divergence` disposition.
- Certified work is not audited retroactively; there is no backfill.

| ID | Title | Work package | Status |
|---|---|---|---|
| `DIV-001` | Bash lookup interruption termination semantics | WP-13.3 (`TOOL-034`) | APPROVED |
| `DIV-002` | Windows `find` full-path glob zero-directory semantics | WP-13.4 (`TOOL-036`) | APPROVED |
| `DIV-003` | Search-engine acquisition is explicit rather than tool-triggered | WP-13.4 (`TOOL-038`) | APPROVED |
| `DIV-004` | Skill frontmatter uses the Minion YAML subset rather than the full yaml@2.9.0 language | WP-14.1 (`HAR-010`) | APPROVED |
| `DIV-005` | Invalid skill-discovery entry does not abort the entire discovery | WP-14.1 (`HAR-001`) | APPROVED |
| `DIV-006` | An invalid ignore pattern is dropped with a diagnostic instead of aborting discovery | WP-14.1 (`HAR-011`) | APPROVED |
| `DIV-007` | Frontmatter block collections nest at most 64 deep | WP-14.1 (`HAR-010`) | APPROVED |
| `DIV-008` | Recursive remove with several failing children: first-encountered failure, sequential traversal | L12-D008 (`EXEC-002`) | APPROVED |
| `DIV-009` | A failed native process-cwd read during path resolution is a typed failure, not a throw | L12-D013 (`EXEC-002`, `EXEC-004`, `EXEC-005`) | APPROVED (Owner); witnesses pending |

---

## DIV-001 — Bash lookup interruption termination semantics

- **Affected:** WP-13.3 `bash` (`minion-agent#50`), shell discovery (`TOOL-034`). Only the `where` / `which` lookup that runs when no Git Bash candidate or `/bin/bash` is found (`spec/tools.md`, WP-13.3, "The lookup").
- **Pi behaviour.** `findBashOnPath` uses `spawnSync`. When the lookup is still alive at its 5000 ms limit or at its 1 MiB combined output budget, Node sends a **direct-child `SIGTERM`**. On POSIX, a lookup can handle that signal, exit 0, and have its already-printed path **selected**.
- **Minion behaviour.** The interruption calls the certified Layer 12 `Process.terminate()`, an uncatchable tree/group hard kill.
  - When the kill is effective, the lookup then has no exit status (POSIX) or the OS code (Windows), and its path is **not** selected. A lookup that completes naturally before the kill reaches it keeps its real code and is read by the unchanged selection rule, as in Pi (`CE-WP133-02-C002`). That race is not part of this divergence.
  - Minion may also end descendants of the lookup that Pi would leave running.
  - Everything else is unchanged: the timer, the budget, settlement and selection for every outcome reachable under the hard kill.
- **Classification:** intentional practical-parity divergence.
  - Pi's intentional abstraction: no (an incidental Node `spawnSync` detail).
  - Realistic in normal use: no.
  - Exact parity needs disproportionate architecture: yes.
- **Why it is incidental.** Observing it needs a deliberately controlled replacement for the normal `which` lookup that:
  - stays alive until the lookup timeout or the output-budget interruption;
  - handles `SIGTERM`;
  - exits successfully after the signal;
  - has already printed a valid shell path.

  Exact parity needed a new cross-language Layer 12 primitive (WP-12.E5, `minion-agent#141`) solely for this. Implementing it exposed POSIX PID-reaping races on pidfd-less, threaded-reaper hosts. Closing them unconditionally could require replacing asyncio's child-reaping architecture, a cost far beyond the agent-level value.
- **Realistic user impact:** none in normal use. A real `which` does not trap `SIGTERM` and keep a lookup alive for 5 s or emit 1 MiB. Normal shell lookup behaviour stays fully compatible and is covered.
- **Platforms:** POSIX. Windows has no demonstrated `SIGTERM`-handling difference, because both mechanisms are uncatchable there.
- **Permanent witnesses:**
  - `assurance/layers/data/13-wp133/harness/lookup_lifecycle_probe.mjs` → `out/lookup-lifecycle-{win32,linux}.json`. Minion's rule differs from pinned Pi on exactly the `trapExit0OverflowWhileAlive`, `trapExit0TimeoutWhileAlive` and `trapDelayedExit0TimeoutWhileAlive` rows on Linux, and nowhere on Windows (`div001`, `minion.differencesAreExactlyDiv001`).
  - The WP-13.3 implementation witnesses: the interruption is `terminate()`, and such a lookup is not selected.
    - Python: `tests/tools/builtin/test_bash_shell.py::test_div001_interruption_is_terminate_not_sigterm`, plus `test_lookup_lifecycle_rows` (the probe's Minion column).
    - The negative control `lookup-direct-sigterm` in `scripts/wp133_bash_negative_controls.py`.
- **Manifest:** row `TOOL-034-DIV-001` (lookup interruption), disposition `intentional divergence`, added with the WP-13.3 Python code candidate, beside `TOOL-034` and `TOOL-035`.
- **Governance:** Owner practical-parity decision, 2026-10-04 (`minion-agent#50` comment `5973629192`; `#141` comment `5973628920`; `#75` comment `5973629428`). It supersedes Owner decision `CE-WP133-02-C001` = Option 1 (`#50` comment `5973189849`).
- **Reconsideration trigger:** a real Minion consumer independently needs a direct-child graceful termination primitive for a normal operational requirement. Future tests reproducing this contrived lookup difference are **not** a trigger.

---

## DIV-002 — Windows `find` full-path glob zero-directory semantics

- **Affected:** WP-13.4 `find` (`minion-agent#51`, `TOOL-036`). Only full-path patterns, those containing `/`, on Windows (`spec/tools.md`, WP-13.4, `find` step 5).
- **Pi behaviour.** `find.ts` rewrites every `/` of a full-path pattern to `[/\\]` on Windows. That breaks the glob's `/**/` component, which can normally match zero directories.
  - `src/**/*.spec.ts` returns `src/sub/d.spec.ts` and `src/sub/deep/er/e.spec.ts` but **not** `src/b.spec.ts`.
  - `src/**/er/**/*.spec.ts` returns nothing.
  - On Linux, the same patterns return the expected files.
- **Minion behaviour.** On Windows, each `**/` component keeps its ordinary meaning, zero or more whole directory levels, while still accepting either separator. Windows results then equal Linux results for ordinary recursive patterns such as these; where a retained Pi-Windows construct is composed with a component, see **Composition** below (WP134-IMPL-R005).
  - The contract specifies only this observable behaviour. Python and Rust may normalize differently, provided the shared witnesses agree.
- **Scope.** Only the zero-directory meaning of `**/` changes.
  - Every other construct keeps exactly Pi's Windows meaning on the pinned `fd`. Notably, a single-segment `*` crosses `\` there, so on Windows `src/*.spec.ts` also returns nested files, in Pi and in Minion alike. That is parity, recorded in characterization F-2.
  - Linux is unchanged.
  - **Composition (clarification, `CE-L13-WP134-01`, adding no scope).** The correction is component-local.
    - The Windows result is the union, over keeping or removing each recursive `**/` component, of Pi's own Windows result for the resulting pattern.
    - "Windows results equal Linux results" therefore holds for patterns whose other constructs mean the same on both platforms.
    - Where a retained Pi-scope construct is composed with a recursive component, that construct keeps its Windows meaning in every branch, and Windows can differ from Linux. For example, `src/**/a*.ts` also returns `src/a/sub/b.ts` on Windows through the single-`*` crossing.
    - When fd rejects the pattern, the result is Pi's diagnostic.
    - Rules and evidence: `spec/tools.md`, WP-13.4, "Recursive components and Pi-scope constructs"; `assurance/layers/13-wp134-ce01-convergence.md`.
- **Classification:** intentional practical-parity divergence.
- **Practical-parity assessment (Owner):**
  - Pi's intentional abstraction: no (a separator-rewrite defect).
  - Realistic in normal use: yes (`src/**/*.spec.ts`).
  - Exact parity would make Minion less useful and inconsistent across platforms; the correction needs no extra architecture.
- **Realistic user impact:** positive. Windows users get the same files as Linux users for ordinary recursive patterns.
- **Platforms:** Windows only.
- **Permanent witnesses:**
  - `assurance/layers/data/13-wp134/out/search-{win32,linux}.json`, the `find/*/full-path-*` cases. Pi's Windows behaviour is the reference side, reproducible with `harness/search_probe.mjs`.
  - `out/div002-win32.json` (`harness/div002_probe.mjs`): one candidate normalization equals Linux on every `**/` case and leaves the `*` scope cases exactly as Pi has them.
  - The implementation's shared witnesses: direct, one-level, deeper and two-`**` cases, plus the `src/*.spec.ts` scope check, on both platforms.
- **Manifest:** row `TOOL-036-DIV-002`, disposition `intentional divergence`.
- **Governance:** Owner decision WP-13.4 Q1 = Option A (`minion-agent#51` comment `5988502021`).
- **Reconsideration trigger:** a pinned `fd` upgrade whose full-path glob handles both separators natively.

---

## DIV-003 — Search-engine acquisition is explicit rather than tool-triggered

- **Affected:** WP-13.4 `find` and `grep` (`minion-agent#51`, `TOOL-038`). This is engine acquisition only; what the engines match is unchanged.
- **Pi behaviour.** `ensureTool` acquires `fd` and `rg` **during the tool call**, in this order:
  - Pi's managed tools directory;
  - otherwise `PATH` (`fd`/`fdfind`, `rg`);
  - otherwise a download of the **latest** GitHub release, except `fd 10.3.0` on darwin/x64.
  When none of these works, the call fails with `fd is not available and could not be downloaded` or `ripgrep (rg) is not available and could not be downloaded`.
- **Minion behaviour.**
  - Engines are provisioned **explicitly** with `provision_search_engines()`. Only the exact pinned artifact for a certified platform (win32-x64, linux-x64) is used. Its artifact SHA-256 is verified before extraction and its binary SHA-256 after, and the binary is installed atomically in a Minion-managed store.
  - A `find` or `grep` call never touches the network and never consults `PATH`. It verifies the store's binary hash before every spawn.
  - An absent or failing engine produces Minion-owned text naming the engine, the reason and the provisioning action. An uncertified platform produces its own text.
- **Classification:** intentional practical-parity divergence (acquisition timing and mechanism only).
- **Practical-parity assessment (Owner):**
  - Pi's intentional abstraction: no (operational and package-management behaviour, not search semantics).
  - Realistic in normal use: yes.
  - Exact parity would bring network access, TLS and proxy handling, retries, cache locking, archive extraction and nondeterministic external failures into an ordinary tool call, against the minimal-harness goal.
- **Realistic user impact:** a one-time provisioning step. Offline use is first-class once provisioned. CI provisions explicitly, optionally from a verified local source.
- **Platforms:** all. Uncertified platforms have no managed engine and no `PATH` fallback.
- **Permanent witnesses** (WP-13.4 implementation):
  - unprovisioned-store text, with no spawn and no network access;
  - a binary with a hash mismatch refused at use time;
  - a wrong artifact hash installs nothing;
  - an interrupted install leaves nothing that verifies;
  - idempotent re-provisioning;
  - uncertified-platform text;
  - the negative controls "PATH fallback", "trust without verifying" and "download from a tool call".
- **Manifest:** row `TOOL-038-DIV-003`, disposition `intentional divergence`.
- **Governance:** Owner decision WP-13.4 Q3 = Option B (`minion-agent#51` comment `5988502021`).
- **Reconsideration trigger:** a product requirement for zero-step first use that outweighs the added acquisition surface.

---

## DIV-004 — Skill frontmatter uses the Minion YAML subset rather than the full yaml@2.9.0 language

- **Affected:** WP-14.1 skill discovery (`minion-agent#158`, `HAR-010`). This is frontmatter parsing only; extraction (`---` delimiters, CR normalization, the body) is unchanged.
- **Pi behaviour.** The harness `parseFrontmatter` passes the frontmatter text to `yaml@2.9.0` `parse`, the full YAML 1.2 language: flow collections, anchors and aliases, tags, merge keys, complex keys, directives, multi-line quoted scalars, explicit block indentation, and so on. Its failures are reported with the library's own message text.
- **Minion behaviour.** The text is read by the Minion frontmatter subset (`spec/harness.md` WP-14.1, HAR-010, rules 1–7):
  - **Inside the subset,** the value is identical to `yaml@2.9.0`. That includes the YAML 1.2 core distinctions (`yes`/`on` stay strings), folded and literal block scalars with Pi's trailing-newline chomping, comments, nested block mappings and block sequences.
  - **Outside it,** the result is a deterministic `parse_failed`, never a partial interpretation. The message is the Minion-defined `frontmatter is not valid in the supported YAML subset` (PP-14-1).
- **Classification:** intentional practical-parity divergence.
- **Practical-parity assessment (Owner):**
  - Pi's intentional abstraction: no. Pi delegates to a general YAML implementation whose full surface is irrelevant to skill metadata.
  - Realistic in normal use: no for the excluded constructs. All 25 realistic skill frontmatter shapes characterized are inside the subset.
  - Exact parity would need a byte-faithful port of a general YAML implementation in both languages.
- **Realistic user impact:** none for ordinary skill metadata. A `SKILL.md` that uses an excluded construct gets a `parse_failed` warning and is not loaded, where Pi would load it. A non-declared root `.md` is skipped silently, as Pi skips its own parse failures.
- **Platforms:** all.
- **Permanent witnesses:**
  - the WP-14.1 canonical rows labelled `DIV-004` (each excluded construct through the real loader; Pi's own result kept in the evidence data);
  - the differential soundness evidence (`assurance/layers/data/14-wp141/subset-diff.mjs`): whenever the subset accepts, `yaml@2.9.0` accepts with an identical value tree;
  - the eleven fuzz negative controls (`fuzz-controls.mjs`), each killed on all three seeds;
  - the realistic-shape acceptance set (`subset-realistic.mjs`).
- **Manifest:** row `HAR-010-DIV-004`, disposition `intentional divergence`.
- **Governance:** Owner decision, Layer 14 WP-14.1 (`minion-agent#158` issuecomment-6051472129, §2–§6).
- **Reconsideration trigger:** a realistic skill corpus that needs an excluded construct.

---

## DIV-005 — Invalid skill-discovery entry does not abort the entire discovery

- **Affected:** WP-14.1 skill discovery (`minion-agent#158`, `HAR-001`). This affects only the ignore-check step of a directory walk.
- **Pi behaviour.** `relativeEnvPath` converts `\` to `/`. For a POSIX entry whose name starts with `\`, or consists only of `\`, the root-relative path becomes `/name`, `/` or the empty string. `ignore@7.0.5` `ignores()` throws `RangeError` or `TypeError` on such a path. Pi does not catch it, so the **whole** `loadSkills` call rejects, discarding every skill and diagnostic already collected, including those from earlier roots.
- **Minion behaviour.** An entry whose ignore-check path is empty or starts with `/` produces exactly one diagnostic. Discovery skips that entry and continues, keeping the skills found before and after it and in other roots. The diagnostic is:

  ```text
  {code: invalid_path, path: <entry addressed path>,
   message: "entry path cannot be matched against ignore rules"}
  ```
- **Classification:** intentional practical-parity divergence.
- **Practical-parity assessment (Owner):**
  - Pi's intentional abstraction: no. It is an incidental consequence of Pi's path and ignore implementation.
  - Realistic in normal use: no (such names are legal but rare).
  - Exact parity is cheap, but it would make the harness lose unrelated skills.
- **Realistic user impact:** a single oddly named entry no longer makes all skills disappear.
- **Platforms:** POSIX. Windows cannot create such names. Names starting with `.` are skipped before the check on every platform.
- **Permanent witnesses:**
  - the WP-14.1 canonical rows labelled `DIV-005`: a leading-backslash file after a collected sibling, a leading-backslash directory, a later root after an earlier root, a successful skill both before **and after** the invalid entry (`r05`, `WP141-C002`), and the inner-backslash control that still loads normally;
  - the model negative controls (`assurance/layers/data/14-wp141/model-controls.mjs`): "stops walking the directory after the invalid entry" is caught by `r05` alone, and "skips without a diagnostic" is caught by `r01`, `r02`, `r03` and `r05`;
  - Pi's rejection is kept in `assurance/layers/data/14-wp141/out-linux.json`.
- **Manifest:** row `HAR-001-DIV-005`, disposition `intentional divergence`.
- **Governance:** Owner decision, Layer 14 WP-14.1 (`minion-agent#158` issuecomment-6051472129, §9–§11).
- **Reconsideration trigger:** none expected.

---

## DIV-006 — An invalid ignore pattern is dropped with a diagnostic instead of aborting discovery

- **Affected:** WP-14.1 skill discovery (`minion-agent#158`, `HAR-011`). This is ignore-file reading only; matching with valid patterns is unchanged.
- **Pi behaviour.**
  - Pinned `ignore@7.0.5` builds each rule's JavaScript RegExp lazily. A pattern whose RegExp is invalid throws `SyntaxError` when that rule is first evaluated. Examples are an out-of-order character range (`[~-a]`, `[é-a]`) or an unterminated class (`[ab/c`).
  - Pi does not catch it, so the whole `loadSkills` call rejects and every skill is lost.
  - Whether it throws depends on rule order and on the path being checked: a negated rule is not evaluated until something is ignored.
- **Minion behaviour.**
  - When an ignore file is read, each prefixed pattern whose RegExp pinned `ignore` would reject is dropped.
  - Each dropped pattern gets exactly one diagnostic, emitted in line order right after that file is read:

    ```text
    {code: invalid_ignore_pattern, path: <the ignore file>,
     message: "ignore pattern is not valid and was dropped"}
    ```
  - The valid patterns are added in their original order, and discovery continues.
  - Patterns `ignore` itself skips (blank, `#`, an invalid trailing backslash) stay silent.
  - With no invalid pattern, behaviour is identical to Pi (`spec/harness.md` WP-14.1, HAR-011 "Invalid patterns").
- **Classification:** intentional practical-parity divergence.
- **Practical-parity assessment (Owner):**
  - Pi's intentional abstraction: no. It is an incidental consequence of lazy RegExp construction.
  - Realistic in normal use: rare, but a single typo in a `.gitignore` under a skills root would lose all skills.
  - Exact parity is reproducible, but it is fragile and order-dependent.
- **Realistic user impact:** one malformed ignore line no longer makes all skills disappear. The line is reported instead.
- **Platforms:** all.
- **Permanent witnesses:**
  - canonical `skills-i10-invalid-patterns-dropped-valid-kept` (mixed: an out-of-order range, a negated invalid pattern and an unterminated class, interleaved with valid patterns);
  - canonical `skills-i11-invalid-prefix-from-directory-name` (a directory named `[~-a]` makes its own ignore file's patterns invalid);
  - the positive control `skills-i12-valid-patterns-only`, identical to pinned Pi;
  - the model controls: *drops without a diagnostic* is killed by `i10` and `i11`, and *stops reading the file at the first invalid pattern* is killed by `i10`;
  - Python regressions in `minion-agent-python/tests/skills/test_discovery.py`;
  - Pi's rejection is kept in `assurance/layers/data/14-wp141/out-linux.json`.
- **Manifest:** row `HAR-011-DIV-006`, disposition `intentional divergence`.
- **Governance:** Owner decision, WP141-I001 Option B (`minion-agent#158` issuecomment-6054403282, §1).
- **Reconsideration trigger:** none expected.

---

## DIV-007 — Frontmatter block collections nest at most 64 deep

- **Affected:** WP-14.1 skill discovery (`minion-agent#158`, `HAR-010`), the frontmatter subset only.
- **Pi behaviour.**
  - `yaml@2.9.0` accepts nested block mappings and sequences until its recursive parser exhausts the
    host JavaScript stack.
  - Pi's `parseFrontmatter` then contains the failure as a parse failure.
  - The cut-off depth is a property of the Node build and stack size (about 950 levels observed at
    the pin). It is not a language rule.
- **Minion behaviour.**
  - The root mapping is depth 1, and each nested mapping or sequence is one deeper.
  - A file whose frontmatter has a collection at depth 65 or more is outside the subset. It is
    therefore `parse_failed` for a declared `SKILL.md` and silently skipped otherwise. This holds
    identically in every binding.
  - Within the bound, values are unchanged.
  - A reader stack exhaustion is still contained as the same outcome (defence in depth,
    `WP141-R002`).
- **Classification:** intentional practical-parity divergence.
- **Practical-parity assessment (Owner):** Pi's cut-off is host-dependent, so exact parity is not
  reproducible across bindings. Realistic skill frontmatter nests a few levels. A fixed bound makes
  every binding agree.
- **Divergence band:** Pi loads frontmatter nested 65 to about 950 deep; Minion reports it as
  `parse_failed`. Beyond Pi's limit, both fail.
- **Platforms:** all.
- **Permanent witnesses:**
  - canonical `skills-n01-depth-63-and-64-load` (identical to Pi);
  - `skills-n02-depth-65-is-parse-failed-sibling-loads`, `skills-n03-sequence-counts-as-a-level`
    and `skills-n04-pi-accepts-depth-100-and-500` (divergences DIV-007; Pi's acceptance is kept in
    `assurance/layers/data/14-wp141/out-*.json`);
  - Python boundary tests at 63, 64, 64 with a sequence, 65, 65 with a sequence, 100 and 500, plus
    the lifted-bound containment test;
  - controls: an off-by-one bound is killed by the 64 witnesses, and a removed bound by the 65+
    witnesses.
- **Manifest:** row `HAR-010-DIV-007`, disposition `intentional divergence`.
- **Governance:** Owner decision, WP141-R003 Option 1 (`minion-agent#158` issuecomment-6058827431).
- **Reconsideration trigger:** none expected.

---

## DIV-008 — Recursive remove with several failing children: first-encountered failure, sequential traversal

- **Affected:** recursive `remove` (Layer 12, `EXEC-002`), spec `execution.md` §19.5 rule 4 as amended by L12-D008 (§20). Coordination `minion-agent#215`; provenance `#127` (`L12-RM-MULTI-FAILURE-SELECTION`).
- **Pi behaviour** (pinned Pi, Node v22.15.1 `rimraf` `_rmchildren`, blob `24bf3f46`):
  - Every child's removal starts before any settles.
  - The first child failure to **settle** is reported, through the `done` guard.
  - The other started removals continue, and `remove()` can return before they finish.
  - A directory's final `rmdir` runs only if every child succeeded.
  - Which failure settles first depends on scheduling. The set left behind once everything drains does not depend on it:
    - every reachable removable entry is gone;
    - a failed entry remains with its ancestors;
    - a directory that could not be listed, or whose first `rmdir` failed with a non-descending error, keeps its unvisited subtree (`L12D008-C001`).
- **Minion behaviour** (Python and Rust):
  - Traversal is sequential, depth first, in the host's enumeration order, which is never re-sorted.
  - A failure does not stop the remaining siblings.
  - The **first failure encountered** in that traversal is reported, unchanged.
  - The call returns only after every child has been attempted.
  - When it returns, the same set remains as in Pi's drained state. The composition is above; witnessed by rows M, S and the boundary rows B1–B7.
- **Classification:** intentional practical-parity divergence. It covers only:
  - (1) first-encountered versus first-settled **selection** when more than one entry fails, including the reported code and origin path;
  - (2) the **absence of sibling concurrency**: Pi may return before outstanding removals finish, and the order in which entries disappear differs.

  It does **not** cover the final removed set, which is required parity and is witnessed against Pi's drained state. It does not weaken single-failure error origin (L12-D001), successful recursive deletion, symlink non-traversal, error classification (L12-D007), or `force`/`recursive` semantics.
- **Practical-parity assessment (Owner):** reproducing Node's scheduling would mean redesigning both bindings' removal for a timing-dependent choice. Only the final removed set is operationally meaningful, and it matches.
- **Divergence band:** a removal with two or more failing entries whose traversal order differs from Pi's settlement order. In the characterized rows that is M2, M4, M6, M8 and M10 on Windows, and the rows whose Linux enumeration order differs. In these the reported path, and possibly the code, differ. With one failing entry, the selection is the same.
- **Platforms:** all. The enumeration order is the host's: alphabetical on NTFS; on Linux tmpfs, reverse creation order.
- **Permanent witnesses:**
  - **Data:** `assurance/layers/data/l12-d008/`, holding the matrix of 13 controlled rows plus 2 natural Linux rows × 10 runs. It has pinned-Pi outputs with a settlement snapshot and a drained snapshot on Windows and Linux, the bindings' outputs, and `div008_compare.py`. The comparator requires extent parity against Pi's drained state, completeness, and the binding's own first-encountered selection. Its self-test rejects a false first-settled claim, a skipped sibling, an extent difference, late calls and an outcome difference.
  - **Python:** `tests/execution/test_filesystem_remove_multi_failure.py`, through the real `LocalFileSystem.remove`, with a pinned-Pi oracle on both platforms. Its controls are the pre-L12-D008 stop-at-first walk (killed on completeness and extent) and a report-the-last-failure walk (killed on selection, including the false first-settled claim).
  - **Rust:** `crates/minion-agent/src/execution/filesystem/rimraf/tests/div008.rs` against byte-copies of the shared matrix and pinned-Pi oracles, `scripts/div008-probe.py`, which feeds the shared comparator, and `scripts/div008-negative-controls.py` (the same two control walks, killed by the named witnesses). Merged at code #219 → `f7400987`, record `assurance/layers/12-l12-d008-rust-implementation.md`.
- **Status:** CERTIFIED_CLOSED cross-language (`#215`, Rust closure review 3, issuecomment-6134407241).
- **Manifest:** row `EXEC-002-DIV-008`, disposition `intentional divergence`.
- **Governance:**
  - Owner decision on `#127` ("APPROVE OPTION 1, WITH CORRECTED SCOPE, INTENTIONAL DIVERGENCE: DIV-008", recorded verbatim, sha256 `f135e947…6fe`).
  - Amended on new evidence by the Owner's extent decision "Continue siblings" (`#215` issuecomment-6118734550): the divergence then covers selection and timing only, not extent.
- **Reconsideration trigger:**
  - a real Minion consumer needs Pi-compatible first-settled or in-flight semantics;
  - sequential traversal causes a material operational problem;
  - the removal architecture changes for an independent reason.

  A contrived scheduling mismatch alone is not a trigger.

---

## DIV-009 — A failed native process-cwd read during path resolution is a typed failure, not a throw

- **Affected:** path resolution for `ctx.fs` (`EXEC-002`), `ctx.shell` (`EXEC-004`) and `ctx.subprocess` (`EXEC-005`). Spec `execution.md` §22, with §2 and §3.2 as corrected. Coordination `minion-agent#235` (L12-D013); provenance `L12D013-PY-I001` (implementation review 4, issuecomment-6201717410).
- **Pi behaviour** (pinned Pi `b7bb00b9`, Node v22.15.1):
  - `resolvePath` (`nodejs.ts:51-65`) reaches Node's `path.resolve`, which reads `process.cwd()` where the algorithm needs it.
  - On win32 that is a device-less rooted or incomplete-UNC input, or a drive-relative input on another drive whose inherited `=X:` entry is absent or empty. On POSIX it is the case where no argument is absolute.
  - The call sits outside any `try`: `absolutePath` returns `ok(resolvePath(…))` (`nodejs.ts:359-360`), and `exec` resolves its cwd before its later `access` catch (`nodejs.ts:376`).
  - So a failed read throws and the operation rejects, contrary to Pi's own interface rule (`types.ts:228-229`).
  - Reviewer witness: the exact pinned slice on real Node with a throwing `process.cwd` propagates that exception (review 4, `d013-cwd-error-authority-r4.cjs`).
- **Minion behaviour** (Python and Rust), per §22:
  - The read happens at the same point, lazily. When it fails with an operational OS error, the operation returns a typed failure where it resolves the path:
    - `ctx.fs`: `FsError` with the native error's own classification and diagnostic, and the caller's logical path argument as `path`;
    - `ctx.shell.exec`: `ShellError(spawn_error)`;
    - `ctx.subprocess.spawn`: `SubprocessError(spawn_error)`, with no process created.
  - Nothing is retried or substituted, and only that read's operational failure is converted.
- **Classification:** intentional practical-parity divergence. It covers only the **outcome** of that failed read: a typed result instead of a rejection. It does **not** cover where or when the read happens, the resolution algorithm, any successful result, the classification of the native error, or any other failure mapping.
- **Practical-parity assessment** (Claude's analysis, presented with the question the Owner decided; the decision text itself is in Governance):
  - Pi's intentional abstraction: no. Pi's interface says these operations never throw; the throw is an implementation gap.
  - Realistic in normal use: no. On win32 a process's cwd cannot be removed while it is in use, and on POSIX a read is reachable only with a relative provider `cwd`.
  - Exact parity would mean an exception escaping the §2 `Result` boundary, which callers are not designed to handle.
- **Realistic user impact:** an environment whose process cwd cannot be read gets an ordinary error result from the affected operation instead of an unexpected exception.
- **Platforms:** all, wherever a binding's resolver reads the native process cwd (§22.1).
- **Permanent witnesses:** to be added with the implementation. Required by the Owner decision:
  - injected native-read failures (never a deleted or invalidated real cwd) through the real public seams `absolute_path`, `file_info`, the other resolver consumers, `ctx.shell.exec` and `ctx.subprocess.spawn`;
  - win32 rooted and L12-D012 drive-relative inputs, with lazy-read and complete-UNC controls, and the POSIX branches where a read is reachable;
  - native ENOENT, permission-denied and other OS errors, each keeping its own classification;
  - caller-path preservation, including UTF-16 values;
  - no filesystem or process side effects, and the existing abort and validation precedence;
  - pinned-Pi-versus-Minion rows.
  - Negative controls for: a leaked raw `OSError`, a wrong code, an omitted caller path, the provider `cwd` substituted for the caller path, an unneeded process-cwd read, indiscriminate catching, a retry with a fabricated cwd, and a process started despite the failure.
- **Manifest:** row `EXEC-002-DIV-009`, disposition `intentional divergence`, with `EXEC-004`/`EXEC-005` traceability.
- **Governance:** Owner decision "APPROVE OPTION 1: TYPED FAILURE, DIV-009" (`#235` issuecomment-6205758223, recorded verbatim, sha256 `77cd22f3…`). It includes the Rust reconciliation: Rust's typed handling is kept, its `ctx.fs` mapping gains the caller's logical path, and only that surface is REVALIDATE_REQUIRED.
- **Status:** APPROVED by the Owner. The contract amendment is pending independent review, and witnesses are pending implementation.
- **Reconsideration trigger:** pinned Pi is updated to normalize this failure itself, or a real consumer needs Pi's rejection.
