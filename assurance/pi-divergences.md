# Approved Pi divergences

This is the canonical, human-readable registry of **accepted** differences between Minion and pinned Pi.

**Policy.** Owner decision, 2026-10-04: practical Pi compatibility (`minion-agent#75` comment `5973629428`; `process/agent-workflow.md` §1 and §6.1).
- A divergence is listed here only after Owner governance.
- Each one has a permanent witness, and a parity-manifest row with the `intentional divergence` disposition.
- Certified work is not audited retroactively; there is no backfill.

| ID | Title | Work package | Status |
|---|---|---|---|
| `DIV-001` | Bash lookup interruption termination semantics | WP-13.3 (`TOOL-034`) | APPROVED |

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
