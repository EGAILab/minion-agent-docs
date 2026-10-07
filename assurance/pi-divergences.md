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
