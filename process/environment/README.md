# Minion-Agent build environment and gate guards (`minion-agent#209`)

These are the versioned copies of Minion-Agent's environment entry points and gate guards. Owner decisions on `minion-agent#209` (2026-10-12) set them. The **live copies** are what agents run: they sit in the project root `E:\AI\Projects\OpenMinds\Minions\Minion-Agent`, which is not a git repository. Each live copy must be **byte-identical** to the file here at the merged revision. A change lands here first, by reviewed PR, and the live copy is then replaced from the merged file.

| File here | Live copy | What it does |
|---|---|---|
| `project-environment.ps1` | `.agents/project-environment.ps1` | PowerShell entry point, used by Codex and by Claude's PowerShell calls. Sets temp and cache paths on E:, the shared cargo home and target `.tmp/cache/cargo-target/windows`, and `CARGO_BUILD_JOBS=4`. |
| `claude-env.sh` | `.tmp/claude-env.sh` | Bash entry point for Claude. Uses the **same** cargo home, target and job limit as the PowerShell entry point, so the dependency cache is no longer split. |
| `gate-preflight.ps1` | `.agents/gate-preflight.ps1` | Read-only check run before every gate (described below). |
| `gate-watchdog.ps1` | `.agents/gate-watchdog.ps1` | Alert-only stall watchdog (described below). |
| `gate-watchdog-controls.ps1` | none; it is evidence tooling | Negative controls for the watchdog's self-test |

The Linux gate containers set `CARGO_BUILD_JOBS=4` themselves. Their scripts were changed in `minion-agent#210`, merged as `e681c22f`.

## Decisions implemented (`#209` items 1, 4, 5 and 7)

1. **Job limit.** `CARGO_BUILD_JOBS=4` in every entry point. There is no manual "2 while another project builds" knob; the preflight's memory wait covers that case.
4. **Shared targets.** There is one cargo home and one target per platform under `.tmp/cache/`. Dependencies are shared. Each worktree path still builds its own copy of the project's crates, so a target grows with the number of worktrees, not with the dependencies.
   - **Thresholds** (Owner decision, `#209` issuecomment-6113930799):
     - **report** a target over **150 GB**;
     - **clean trigger:** E: has under **300 GB** free, or a target is over **250 GB**.
   - **Cleaning** is never automatic. It runs once, in a window when no agent is building, through the containment helper, and removes the artifacts of worktrees that no longer exist first. Neither guard here deletes anything.
5. **Focused first.** Run focused tests while working (G0–G2) and the full two-platform gates at handoff and closure (G3). No tooling change was needed.
7. **Stall watchdog**, alert-only, described below.

Items 2 (closing the emulator) and 3 (the page file: 32 GB on E:, plus a small system-managed one on C:) are the Owner's own actions. Item 6 (combining control builds) was not pursued.

## `gate-preflight.ps1`

`powershell -NoProfile -File .agents\gate-preflight.ps1 [-MinFreeGB 16] [-MaxWaitMinutes 30] [-Sizes]`

- **Memory:** waits until `MinFreeGB` of physical memory is free, polling every 30 s, and **exits 2** if that doesn't happen within `MaxWaitMinutes`. It never stops the emulator, Minion-Memory's batches or another agent's build. A launcher must refuse to start a gate on a nonzero exit.
- **Active builds:** lists the running `cargo`, `rustc` and `docker` processes. Cargo's lock queues concurrent builds in the shared target.
- **Disk and targets:** reports E: free space against the 300 GB clean trigger. With `-Sizes`, it also reports each target against 150 GB (report) and 250 GB (clean trigger).
- **Fail-closed witness:** `-MinFreeGB 999 -MaxWaitMinutes 0` exits 2 with `PREFLIGHT FAIL`.

## `gate-watchdog.ps1`

`powershell -NoProfile -File .agents\gate-watchdog.ps1 -ProgressLog <log> -WatchPid <launcher pid> [-StallSeconds 900] [-PollSeconds 30]`

- **Convention** (the shape of the kit's planned launchers, so it can be upstreamed unchanged): the gate launcher appends its output to `.tmp/gate-logs/<run-id>.log`, and its last line is `GATE-END <exit code>`. Run the watchdog in the background (a Monitor), so its output reaches the agent.
- **Behavior:**
  - The watchdog reads only the log's length.
  - If the log has not grown for `StallSeconds` (default 15 minutes) while the launcher is alive, it prints one `STALL ALERT` line, and repeats it after each further `StallSeconds` without growth. The agent then investigates: process tree, CPU, memory, lock holders.
  - **It never kills, stops or deletes anything.**
  - After a cache reset, a cold link of the heavy crates under 4 jobs can exceed 15 minutes. The first alert after a reset is therefore expected, and the alert text says so.
- **Exit codes:**
  - `0`: `GATE-END` appeared, or the launcher ended with a log present;
  - `3`: the launcher ended and the log never appeared;
  - `64`: usage error.
- **Self-test:** `-SelfTest` runs four cases against short timings:
  - a stall alerts;
  - a growing log does not alert (the control);
  - `GATE-END` ends the watch;
  - a missing log with an ended launcher exits 3.

  It writes only inside `.tmp\gate-logs\selftest-<pid>`. Every target, including the cleanup, passes a containment check first (lexical resolution under the project root, and no link anywhere on the path), and the check fails closed.
- **Negative controls:** `gate-watchdog-controls.ps1` makes four mutants, one per case: never alerts, ignores growth, ignores `GATE-END`, and exits 0 on a missing log. Each must make the self-test fail on its own case.

## Evidence at this candidate (Windows 11, 2026-10-12)

- `gate-watchdog.ps1 -SelfTest`: **4/4 PASS**.
- `gate-watchdog-controls.ps1`: **4/4 KILLED**, each failing on the intended case.
- `gate-preflight.ps1`: normal run exits 0. The fail-closed witness (`-MinFreeGB 999 -MaxWaitMinutes 0`) exits 2.
- The `CARGO_BUILD_JOBS` and `CARGO_TARGET_DIR` values were checked after dot-sourcing `project-environment.ps1`.
