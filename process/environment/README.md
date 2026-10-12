# Minion-Agent build environment and gate guards (`minion-agent#209`, TOOL-209 `#214`)

These are the versioned copies of Minion-Agent's environment entry points and gate guards. Owner decisions on `minion-agent#209` (2026-10-12) set them. The **live copies** are what agents run: they sit in the project root `E:\AI\Projects\OpenMinds\Minions\Minion-Agent`, which is not a git repository. Each live copy must be **byte-identical** to the file here at the merged revision. A change lands here first, by reviewed PR, and the live copy is then replaced from the merged file.

| File here | Live copy | What it does |
|---|---|---|
| `project-environment.ps1` | `.agents/project-environment.ps1` | PowerShell entry point, used by Codex and by Claude's PowerShell calls. Sets temp and cache paths on E:, the shared cargo home and target `.tmp/cache/cargo-target/windows`, and `CARGO_BUILD_JOBS=4`. |
| `claude-env.sh` | `.tmp/claude-env.sh` | Bash entry point for Claude. Uses the **same** cargo home, target and job limit as the PowerShell entry point, so the dependency cache is no longer split. |
| `gate-preflight.ps1` | `.agents/gate-preflight.ps1` | Read-only check run before every gate, plus a boundary self-test (described below). |
| `gate-watchdog.ps1` | `.agents/gate-watchdog.ps1` | Alert-only stall watchdog (described below). |
| `gate-guard.ps1` | `.agents/gate-guard.ps1` | The containment guard that every write in this tooling goes through (described below). |
| `gate-guard-selftest.ps1` | none; it is evidence tooling | The guard's self-test |
| `gate-watchdog-controls.ps1` | none; it is evidence tooling | The negative-control driver for all three self-tests |

The Linux gate containers set `CARGO_BUILD_JOBS=4` themselves. Their scripts were changed in `minion-agent#210`, merged as `e681c22f`.

## Decisions implemented (`#209` items 1, 4, 5 and 7)

1. **Job limit.** `CARGO_BUILD_JOBS=4` in every entry point. There is no manual "2 while another project builds" knob; the preflight's memory wait covers that case.
4. **Shared targets.** There is one cargo home and one target per platform under `.tmp/cache/`. Dependencies are shared. Each worktree path still builds its own copy of the project's crates, so a target grows with the number of worktrees, not with the dependencies.
   - **Thresholds** (Owner decision, `#209` issuecomment-6113930799):
     - **report** a target over **150 GB**;
     - **clean trigger:** E: has under **300 GB** free, or a target is over **250 GB**.
   - **Cleaning** is never automatic. It runs once, in a window when no agent is building, through the containment helper, and removes the artifacts of worktrees that no longer exist first. No script here deletes build artifacts.
5. **Focused first.** Run focused tests while working (G0–G2) and the full two-platform gates at handoff and closure (G3). No tooling change was needed.
7. **Stall watchdog**, alert-only, described below.

Items 2 (closing the emulator) and 3 (the page file: 32 GB on E:, plus a small system-managed one on C:) are the Owner's own actions; item 3 is pending. Item 6 (combining control builds) was not pursued.

## `gate-preflight.ps1`

`powershell -NoProfile -File .agents\gate-preflight.ps1 [-MinFreeGB 16] [-MaxWaitMinutes 30] [-Sizes]`

- **Memory:** waits until at least `MinFreeGB` GiB of physical memory is free, polling every 30 s.
  - The decision compares **exact bytes**. The displayed value is only for reading, and is rounded **down** to two decimals. So 15.96 GiB refuses and is shown as 15.96, never as 16 (TOOL209-R003).
  - It **exits 2** if memory never frees up within `MaxWaitMinutes`. It never stops the emulator, Minion-Memory's batches or another agent's build. A launcher must refuse to start a gate on a nonzero exit.
- **Active builds:** lists the running `cargo`, `rustc` and `docker` processes. Cargo's lock queues concurrent builds in the shared target.
- **Disk and targets:** reports E: free space against the 300 GB clean trigger. With `-Sizes`, it also reports each target against 150 GB (report) and 250 GB (clean trigger), comparing bytes.
- **`-SelfTest`:** six boundary cases against 16 GiB:
  - 15.96 GiB, and one KiB below 16 GiB, refuse;
  - exactly 16 GiB, one KiB above, and 30.5 GiB pass;
  - zero refuses.

  Each case also checks the rounded-down display. The self-test is pure computation and writes nothing.
- **Fail-closed witness:** `-MinFreeGB 999 -MaxWaitMinutes 0` exits 2 with `PREFLIGHT FAIL`.

## `gate-guard.ps1`: containment for every write (TOOL209-R001)

All of this tooling's own writes (the self-test logs and the control mutants) go through `Guard-Op mkdir|write|append|remove`. `Guard-Op` proves containment **immediately before that one operation**. Nothing runs when the proof fails:

1. **Form.** Empty paths, UNC/device paths (`\\…`), drive-relative forms (`X:foo`) and `..` segments are refused.
2. **Lexical.** The full path must lie strictly below the project root. The root itself is refused, and so is a sibling such as `Minion-Agent-backup`.
3. **Real path.** Every existing component from the drive root down to the target is inspected. A junction or link anywhere on the path, including above the project root, refuses the operation. So does a failed or empty inspection.

`remove` deletes exactly one entry and is never recursive. Watch mode of the watchdog and the preflight perform no writes at all.

The self-test is `gate-guard-selftest.ps1`, 14 cases, and never touches disk. It replaces the mutation with a counter and simulates links and inspection failures. Each refusal case must throw **and** reach zero mutation calls; each positive must reach exactly one. One positive inspects the real path, which also shows that no component of the actual project-root path is a link today.

## `gate-watchdog.ps1`

`powershell -NoProfile -File .agents\gate-watchdog.ps1 -ProgressLog <log> -WatchPid <launcher pid> [-StallSeconds 900] [-PollSeconds 30]`

- **Convention** (the shape of the kit's planned launchers, so it can be upstreamed unchanged): the gate launcher appends its output to `.tmp/gate-logs/<run-id>.log`, and its last line is `GATE-END <exit code>`. Run the watchdog in the background (a Monitor), so its output reaches the agent.
- **Behavior:**
  - The watchdog reads only the log's length.
  - If the log has not grown for `StallSeconds` (default 15 minutes) while the launcher is alive, it prints one `STALL ALERT` line, and repeats it after each further `StallSeconds` without growth. The agent then investigates: process tree, CPU, memory, lock holders.
  - **It never kills, stops or deletes anything**, and watch mode writes nothing.
  - After a cache reset, a cold link of the heavy crates under 4 jobs can exceed 15 minutes. The first alert after a reset is therefore expected, and the alert text says so.
- **Exit codes:**
  - `0`: `GATE-END` appeared, or the launcher ended with a log present;
  - `3`: the launcher ended and the log never appeared;
  - `64`: usage error.
- **`-SelfTest`:** four cases on short timings:
  - a stall alerts;
  - a growing log does not alert (the control);
  - `GATE-END` ends the watch;
  - a missing log with an ended launcher exits 3.

  Every write goes through `Guard-Op`: the directory, each append made by the writer process (including `GATE-END`), and each cleanup removal of exactly the files that run wrote. Watching starts only after the writer's first line exists, so process start-up time under load cannot leak into the 3 s stall window.

## `gate-watchdog-controls.ps1`: negative controls (TOOL209-R002)

Kit `WORKFLOW.md` §9.7 rules, enforced by the driver:

- **Baseline first.** Each unmodified self-test (watchdog, guard, preflight) must exit 0, print its pass marker, and print a `PASS` line for **every** one of its cases. A baseline that is not green makes the run INVALID (exit 2), and no mutant is credited.
- **Strict kill.** A mutant counts as **KILLED** only when all of these hold:
  - its anchor was found and its source really changed;
  - the self-test exited 1 with its fail marker;
  - **every intended case** printed `FAIL`;
  - every other case printed `PASS`.
- **Everything else is INVALID, never a kill:** setup, parse or usage errors (for example exit 64), missing cases, unrelated failures, wrong exit codes, timeouts. A timed-out child is reported and left to finish; nothing is killed.
- **Exit codes:** 0 only for a green baseline with every mutant KILLED; 1 when a mutant survived or was invalid; 2 for an invalid baseline.

The seven mutants, each with its intended failing case or cases:

| Mutant | Target | Intended failing case(s) |
|---|---|---|
| `never-alerts` | watchdog | stall alerts |
| `ignores-growth` | watchdog | growing log, no alert (control) |
| `ignores-gate-end` | watchdog | GATE-END ends the watch |
| `missing-log-exit-0` | watchdog | missing log, launcher ended |
| `guard-ignores-links` | guard | junction ancestor (.tmp); junction above the root (Minions); link at the target itself |
| `guard-inspection-failure-passes` | guard | inspection throws |
| `preflight-rounds-before-compare` | preflight (the R003 defect) | 15.96 GiB below 16; one KiB below 16 GiB |

**`-DriverSelfTest`** checks the driver's own rules with a fake child and no disk writes, in seven scenarios:
- every child exits 64 with no witness: exit 2, zero kills. This is the reviewer's counterfeit from review 1;
- a green baseline with mutants exiting 64;
- mutants failing an unintended case;
- the intended case failing while another case is missing;
- a baseline missing a case;
- a timeout;
- positive: exactly the intended cases fail, and all 7 are killed.

Every scenario except the last must credit zero kills.

## Evidence (Windows 11, 2026-10-12)

**Revision 2**, remediating review 1 (#214 issuecomment-6116581685, findings TOOL209-R001–R003):
- `gate-guard-selftest.ps1`: **14/14 PASS**.
- `gate-preflight.ps1 -SelfTest`: **6/6 PASS**.
  - The fail-closed witness exits 2.
  - A normal run exits 0.
- `gate-watchdog.ps1 -SelfTest`: **4/4 PASS** in three consecutive runs.
- `gate-watchdog-controls.ps1 -DriverSelfTest`: **7/7 PASS**.
- `gate-watchdog-controls.ps1`: three baselines **GREEN** and mutants **7/7 KILLED**, with 0 survived and 0 invalid.
  - On the run before the start-up wait was added, the driver correctly reported `missing-log-exit-0` **INVALID**, not killed: an unrelated case had failed on start-up timing. That fix is in this revision.
- After the runs, nothing the tooling wrote remains under `.tmp/gate-logs`. The empty `controls` folder there was left by the revision 1 driver.

Revision 1 (`db2d9965`) claimed "4/4 KILLED". The reviewer showed that the driver would have credited setup failures (R002), so that claim is **withdrawn**. It is superseded by the strict results above.
