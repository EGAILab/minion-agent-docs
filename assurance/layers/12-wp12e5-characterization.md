# WP-12.E5 — direct-child termination: characterization

**Work package:** `minion-agent#141`. **Contract:** `spec/execution.md` §16 (`EXEC-011`).
**Authorization:** Owner decision `CE-WP133-02-C001` = Option 1 (`minion-agent#50` comment `5973189849`).
**Origin:** WP-13.3 convergence `CE-WP133-02`; Codex's checkpoint review 1 (docs #229 comment `5971794856`) showed that Pi's lookup interruption is a direct-child `SIGTERM`, and that a lookup that handles it and exits 0 is selected. Minion's `terminate()` group `SIGKILL` cannot reproduce that.

## 1. Sources audited

| Source | Symbol | Observation |
|---|---|---|
| pinned Pi `b7bb00b9`, `utils/shell.ts` | `findBashOnPath` | `spawnSync(…, {encoding: "utf-8", timeout: 5000})`; no `killSignal`, so the default is `SIGTERM` |
| Node v22.15.1 `src/spawn_sync.cc` | `Kill()` | `uv_process_kill(&uv_process_, kill_signal_)` **only if `exit_status_ < 0`** (not exited), then `CloseStdioPipes()`; once only (`killed_`) |
| | `OnExit`, `BuildResultObject` | records the exit code and signal; `status` is null only for a signal termination |
| libuv 1.49.2 `src/unix/process.c` | `uv_process_kill` → `uv_kill` | `kill(pid, signum)`: a positive PID, the direct child only |
| libuv 1.49.2 `src/win/process.c` | `uv__kill` (`SIGTERM`) | `TerminateProcess(process_handle, 1)`. On success `uv_process_kill` records `exit_signal = SIGTERM`. If the process had already exited, `ERROR_ACCESS_DENIED` is mapped to `UV_ESRCH` and no signal is recorded |
| Minion Layer 12 (accepted `main`) | `Process.terminate()` | Python: `os.killpg(pid, SIGKILL)` (POSIX), `taskkill /F /T` (Windows). Rust: `kill -KILL` on the group, `taskkill` |

## 2. Executed behaviour (`data/12-wp12e5/harness/kill_probe.mjs`)

The probe uses Node v22.15.1 on Windows 11 (build 26200) and on Linux in `node:22.15.1-bookworm-slim`. Each child signals readiness once its `SIGTERM` disposition is installed, then gets one `ChildProcess.kill()`, which is the same `uv_process_kill(SIGTERM)` as `spawn_sync`'s `Kill()`.

| Row | Linux | Windows |
|---|---|---|
| `default` | `code null, signal SIGTERM` | `code null, signal SIGTERM` |
| `handledExit0` | **`code 0`** | `code null, signal SIGTERM` (not interceptable) |
| `handledExit7` | **`code 7`** | `code null, signal SIGTERM` |
| `handledDelayedExit0` (exits 500 ms after the signal) | `code 0`, exit ≥ 400 ms after the request | `signal SIGTERM`, at once |
| `ignoredThenSelfExit0` | `code 0`, exit ≥ 400 ms after the request | `signal SIGTERM`, at once |
| `descendantNotTargeted` | parent `signal SIGTERM`; the descendant, **in the same process group**, writes its marker | parent `signal SIGTERM`; the descendant writes its marker |
| `alreadyExited` (kill after exit) | `kill()` returns false; `code 3` stands | the same |
| `spawnSyncTimeoutHandledExit0` (Pi's lookup shape) | **`status 0`**, `ETIMEDOUT`, stdout has the path | `status null`, `SIGTERM`, `ETIMEDOUT` |

**Notes:**
- **A Windows confounder, controlled.** In the first Windows run, the descendant died with its parent. The cause was not `TerminateProcess`: a Node child puts the processes it spawns into its own kill-on-close job object, and that job closed when the child died. The descendant is now spawned detached (outside that job) on Windows, and it survives. A Minion `terminate_child()` must not reproduce that job behaviour: it is a property of the child program, not of the termination.
- **A repeated `ChildProcess.kill()`** resends on POSIX (`true`) and does not on Windows (`false`, already exited). Pi's lookup goes through `spawn_sync`'s `Kill()`, which sends once. The contract follows that path.

## 3. Rules (contract §16)

1. **POSIX:** one `SIGTERM` to the direct PID. Never `SIGKILL`, the group, or descendants.
2. **Windows:** direct `TerminateProcess`. No tree, no job.
3. **No-op cases:** the process has already exited, the operation was already called, or `terminate()` was already called.
4. **`wait()`** reports the child's own final outcome. On Windows, an effective termination reports `exit_code: None`, as Node's `signal: SIGTERM` does, not the synthesized `1`.
5. **Not a cause claim.** The §6 first-claim classification is unchanged.

## 4. Feasibility

- **Python:**
  - POSIX: `asyncio.subprocess.Process.send_signal(SIGTERM)`. `Popen.send_signal` polls first and skips an exited process.
  - Windows: `Process.terminate()` → `TerminateProcess(handle, 1)`. CPython maps `PermissionError` on an exited process to its real code, which distinguishes an effective termination.
  - The local provider already spawns POSIX children with `start_new_session=True`. That is why a direct-PID `SIGTERM` leaves the group's other members alone.
- **Rust:** `libc::kill(pid, SIGTERM)` after a `try_wait()` check, or `Child::kill` → `TerminateProcess` on Windows. That is Rust's to design and certify.
- **No change** to `terminate()`, spawn, or the signal watcher.

## 5. Open questions for the contract review

- **Windows `exit_code: None`.** This is the Node-faithful representation (§16.3), and it differs from `terminate()`'s preserved `1`. The WP-13.3 lookup selects nothing either way.
- **POSIX witnesses on a Windows host.** The Python gate runs on Windows. The POSIX witnesses (1–5, 8) run in a Linux container against the same source, and are reported with the gate.
