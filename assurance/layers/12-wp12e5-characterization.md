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
| `ignoredThenSelfExit0`* | `code 0`, exit ≥ 400 ms after the request | `signal SIGTERM`, at once |
| `descendantNotTargeted` | parent `signal SIGTERM`; the descendant, **in the same process group**, writes its marker | parent `signal SIGTERM`; the descendant writes its marker |
| `alreadyExited` (kill after exit) | `kill()` returns false; `code 3` stands | the same |
| `spawnSyncTimeoutHandledExit0` (Pi's lookup shape) | **`status 0`**, `ETIMEDOUT`, stdout has the path | `status null`, `SIGTERM`, `ETIMEDOUT` |

**Notes:**
- \* **Label.** Despite its name, `ignoredThenSelfExit0` installs a handler that schedules the exit, so it is a second delayed-handler row (contract review 1, nonblocking). Node cannot set `SIG_IGN`. The truly ignored case is the Python witness `test_posix_ignored_sigterm_then_own_exit` (`SIG_IGN`, §6).
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

## 6. Contract review 1 and the Python implementation

**Contract review 1** (Codex; docs #237 @ `93c63141`, comment `5973294244`): **APPROVED**.
- Codex replayed the kill probe unchanged on Windows and on Linux. All 8 rows matched on each platform.
- The Windows `exit_code: None` choice was accepted.
- Implementation reminders, all applied below:
  - make the repeated-call witness acknowledged;
  - exercise a later `terminate()` and a later abort after a request, through the real provider;
  - a truly ignored `SIGTERM`.

**Python candidate** (`minion-agent#142`):
- `execution/subprocess.py`: `Process.terminate_child()`.
  - **POSIX:** `os.kill(pid, SIGTERM)`. `Popen.send_signal` is not used, because its `poll()` can reap the child out from under asyncio's child watcher. The direct child leads its own session, so the group's other members are untouched.
  - **Windows:** the transport's `Popen.terminate()`, which is `TerminateProcess(handle, 1)`. It is effective iff `returncode` stays unset; CPython maps an already-exited process's `ERROR_ACCESS_DENIED` to its real code. `wait()` reports an effective termination as `None`.
  - **No-op** once exited, already called, or after `terminate()`. The first-claim `_kill_cause` is never touched.

| Witness (`tests/execution/test_terminate_child.py`) | Host |
|---|---|
| default → `None`; handled → `0`, `7`; a 500 ms handler → not settled at 250 ms, then `0`; `SIG_IGN` then its own exit → not settled, then `0` | Linux container |
| direct child only: an in-group descendant survives `terminate_child()`, and `terminate()` on a twin kills it | Linux container |
| single delivery: the second call comes after the child acknowledges the first `SIGTERM` → count 1 | Linux container |
| a later spawn-signal abort → `Err(aborted)`; a later `terminate()` → `SIGKILL`, `None` | Linux container |
| effective termination → `None`; a descendant survives; `terminate()` still reports `1`; an exited-but-unobserved process is not effective (real `4`); terminate failure and missing transport are swallowed | Windows |
| no-op after exit (real code kept), after `terminate()`, repeated calls | both |

**Negative controls** (`scripts/e5_negative_controls.py`; each applies one fault to a copy of `src` and runs the witnesses):

| Fault | Platform | Killed |
|---|---|---|
| `as-terminate` | both | yes (Linux 8, Windows 3 failing tests) |
| `posix-sigkill` | POSIX | yes (7) |
| `posix-killpg` | POSIX | yes (the descendant witness) |
| `handled-exit-as-no-status` | both | yes (Linux 5, Windows 1) |
| `delayed-exit-completed-at-request` | POSIX | yes (7) |
| `resend-on-repeat` | POSIX | yes (the acknowledged count) |
| `claims-the-cause` | POSIX | yes (the later-abort witness) |
| `windows-synthesized-1` | Windows | yes (2) |
| `windows-tree-kill` | Windows | yes (3) |

- **The repeated-call witness was first vacuous.** With two back-to-back requests, the two `SIGTERM`s coalesced, because standard signals are not queued, and `resend-on-repeat` survived. The witness now waits for the child's acknowledgement before the second call, and the control is killed.

**Gates:**
- Windows (Python 3.13.5, pinned ICU): full `pytest` **4268 passed, 38 skipped, 19 xfailed**, coverage **100.00%**; `ruff` and `mypy` clean; manifest validation 8 passed.
- Linux (`python:3.13`, Python 3.13.15): `test_terminate_child.py` plus the Layer 12 `test_subprocess.py` regression, **43 passed, 8 skipped** (Windows-only). The POSIX controls were run there.

## 7. Implementation review 1 and `WP12E5-I001`

**Implementation review 1** (Codex; code #142 @ `1ea5dad4` / docs #237 @ `eb855bbd`, comment `5973429690`): **CHANGES REQUIRED**, one finding. Every gate was otherwise green, and Codex replayed them all.

- **`WP12E5-I001`** (PI_PARITY_DEFECT, high). On Linux, asyncio's default pidfd child watcher reaps the child (`waitpid`), then publishes the exit to the transport through a callback queued with `call_soon_threadsafe`. A task that runs in between sees `returncode is None`, and the candidate's `os.kill(pid, SIGTERM)` then targets a **released** PID. If the PID is reused, that is a different process. Codex's probe showed the signal request after reaping; it returned `ESRCH`, with no reuse in that run.
- **Why the gates missed it:** the no-op-after-exit witness awaited `wait()` first, after the exit had been published.

**Remediation** (`_posix_terminate_child`):
1. `pidfd_open(pid)` first (Linux), pinning the process the PID names at that moment.
2. `waitid(P_PID, pid, WEXITED | WNOHANG | WNOWAIT)`, which never reaps:
   - `ChildProcessError`: already reaped, so do nothing;
   - a result: exited and unreaped (a zombie), already finished, so do nothing;
   - `None`: running and unreaped. Reaping is irreversible, so the pidfd from step 1 names this same child.
3. `pidfd_send_signal(pidfd, SIGTERM)`. It is safe even if a reap follows, and gives `ESRCH`.

- **Without pidfd** (Linux before 5.3, other POSIX systems), `os.kill` follows step 2 directly. asyncio's watcher then reaps on a thread, so a microsecond window remains there. This is disclosed. The certified hosts are Linux with pidfd and Windows.
- **No other behaviour changes:** spawn, the watcher, cause classification, `terminate()`, stdio and the `wait()` outcomes are untouched.

**New permanent witnesses** (Linux container, pidfd available, kernel 6.18):
- `test_posix_released_pid_is_never_signalled`: Codex's technique, kept permanently. The request is scheduled from asyncio's own child-watcher callback, after the reap and before the exit is published. It asserts that the child was reaped, that `returncode` was still `None`, that **no** signal request was made through `os.kill` or `pidfd_send_signal`, and that the final code 7 is preserved.
- `test_posix_exited_unreaped_child_is_not_signalled`: the event loop is blocked, so the exited child stays a zombie. No request is made, and the real code 5 stands.
- **RED against the rejected `1ea5dad4`:** both fail.

**Controls:**
- New: `unsynchronized-kill` (the rejected candidate), killed by both new witnesses; `zombie-signalled`, killed by the zombie witness.
- POSIX controls rewritten for the helper: `posix-sigkill` and `posix-killpg` patch both send paths.
- Linux: **9/9 killed**. Windows: **4/4 killed**, unchanged.

**Gates:** Linux, `test_terminate_child.py` plus `test_subprocess.py`: **45 passed, 8 skipped**. Windows (Python 3.13.5, pinned ICU): **4268 passed, 40 skipped, 19 xfailed**, coverage **100.00%**; `ruff`, `ruff format` and `mypy` clean; manifest validation 8 passed.
