# WP-13.3 `bash`: pinned-Pi characterization (source audit)

**Work package:** `minion-agent#50` (CONTRACT_DRAFT). **Requirements:** `TOOL-034` (schema, no default timeout, shell selection, command transport), `TOOL-035` (output: tail truncation, temp file).
**Author:** Claude. This is characterization, not a contract.
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`, Node v22.15.1.
**Scoping authority:** `13-built-in-tools-scoping-v4.md` (shell-selection matrix, CE-L13-SCOPE-01, closed), together with the unrevised sections of revisions 1–3.

This first pass is a **source audit**. Every rule cites its line. Executable probes against the pinned sources come next (§9). Nothing here is yet asserted by a canonical case.

## 1. Symbols audited

| File (pinned) | Symbols |
|---|---|
| `coding-agent/src/core/tools/bash.ts` | `resolveTimeoutMs`, `bashSchema`, `createLocalBashOperations` (`exec`), `resolveSpawnContext`, `createBashToolDefinition` (`execute`: `emitOutputUpdate`, `scheduleOutputUpdate`, `handleData`, `finishOutput`, `formatOutput`, `appendStatus`), the description string |
| `coding-agent/src/utils/shell.ts` | `getShellConfig`, `getBashShellConfig`, `isLegacyWslBashPath`, `findBashOnPath`, `getShellEnv`, `killProcessTree`, `trackDetachedChildPid` / `untrackDetachedChildPid` |
| `coding-agent/src/utils/child-process.ts` | `waitForChildProcess` (`EXIT_STDIO_GRACE_MS = 100`) |
| `coding-agent/src/core/tools/output-accumulator.ts` | `OutputAccumulator` (`append`, `finish`, `snapshot`, `closeTempFile`, `getLastLineBytes`, `trimTail`, `shouldUseTempFile`, `ensureTempFile`) |
| `coding-agent/src/core/tools/truncate.ts` | `truncateTail`, `truncateStringToBytesFromEnd`, `splitLinesForCounting`, `formatSize`, `DEFAULT_MAX_LINES = 2000`, `DEFAULT_MAX_BYTES = 51200` |

## 2. Input

- **Schema** (`bash.ts:39-42`): `{command: string, timeout?: number}`, with `timeout` in **seconds**. There is **no default timeout**.
- **Timeout validation** (`resolveTimeoutMs`, `bash.ts:28-37`) runs inside `exec`, **before** the abort check and before shell selection:
  - `undefined`: no timeout.
  - Not finite, or `<= 0`: throws `Invalid timeout: must be a finite number of seconds`.
  - `timeout * 1000 > 2147483647`: throws `Invalid timeout: maximum is 2147483.647 seconds`. The number is rendered by JavaScript `Number` to string: `MAX_TIMEOUT_MS / 1000`.
  - Otherwise the value in milliseconds is `timeout * 1000`, a binary64 product. Fractional seconds are allowed.
- The thrown message is the tool's error text. These errors are not caught by the `aborted` / `timeout:` branches (§6).

## 3. Order of the pre-spawn checks (`createLocalBashOperations.exec`, `bash.ts:91-101`)

1. `resolveTimeoutMs(timeout)`, which may throw (§2).
2. `signal?.aborted` → throws `aborted` → the tool text is `Command aborted` (§6).
3. `getShellConfig(shellPath)`, which may throw (scoping v4 matrix: custom path not found; Windows "No bash shell found ...").
4. `fsAccess(cwd, F_OK)`. On failure it throws `Working directory does not exist: ${cwd}\nCannot execute bash commands.`

The tool's `execute` builds the spawn context before calling `exec` (`resolveSpawnContext`, §5), and emits the initial empty update before `exec` (§7).

## 4. Spawn and lifecycle (`bash.ts:103-154`)

- **Spawn:** `spawn(shell, transport === "stdin" ? args : [...args, command], {cwd, detached: platform !== "win32", env, stdio: [stdin ? "pipe" : "ignore", "pipe", "pipe"], windowsHide: true})`.
  - With stdin transport, the command is written to stdin, which is then ended; stdin errors are ignored.
  - With argv transport, stdin is **ignored**: the child sees no stdin at all.
- **Process tracking:** the pid is tracked for shutdown cleanup (`trackDetachedChildPid`). This is process-global and not observable by a single call.
- **Timeout:** when given, after `timeoutMs` the call sets `timedOut` and runs `killProcessTree(pid)`.
- **Abort:** an abort after spawn runs `killProcessTree(pid)`. A signal already aborted at listener registration kills immediately; because §3 step 2 throws first, that case is only reachable through a race.
- **Output:** `stdout` and `stderr` `data` events both go to **one** `onData(Buffer)`, in arrival order. The two streams interleave, as raw bytes.
- **Settlement:** `waitForChildProcess(child)`, `child-process.ts:47-136`, with an idle grace of 100 ms:
  - It resolves on `close`. After `exit`, it also resolves once both pipes have ended, or once 100 ms pass without data. The grace re-arms on each data chunk.
  - It rejects on the child's `error` event, for example a spawn failure. The rejection propagates as a thrown `Error` with the Node message (§6).
- **Result after settlement:** `signal.aborted` → throws `aborted`; else `timedOut` → throws `timeout:${timeout}`, where `timeout` is the **seconds value as given** (JS `String(number)`); else `{exitCode}`.
  - The exit code is `number | null`. It is `null` when the process ended by signal without abort or timeout, for example an external kill.
- **`killProcessTree`** (`shell.ts:204-225`):
  - Windows: `taskkill /F /T /PID <pid>`, detached, errors ignored.
  - POSIX: `process.kill(-pid, "SIGKILL")` (the process group); if that throws, `process.kill(pid, "SIGKILL")`.

## 5. Environment and spawn context (`resolveSpawnContext`, `bash.ts:162-184`; `getShellEnv`, `shell.ts:120-131`)

- **The base is `getShellEnv()`:** `process.env`, with Pi's own `bin` directory (`getBinDir()`) prepended to the `PATH` variable unless already present.
  - That variable is looked up case-insensitively (the first key whose lower case is `path`), else `PATH`.
- **Then** the five session keys are deleted: `PI_SESSION_ID`, `PI_SESSION_FILE`, `PI_PROVIDER`, `PI_MODEL`, `PI_REASONING_LEVEL`.
- **Then, when `exposeSessionEnvironment` (default `true`) and an extension context are present**, they are re-added from the session:
  - `PI_SESSION_ID` always;
  - `PI_SESSION_FILE` if there is a session file;
  - `PI_PROVIDER` and `PI_MODEL` if there is a model;
  - `PI_REASONING_LEVEL` if the thinking level is truthy.
- **Command prefix:** `commandPrefix` (an option), when set, makes the command `${prefix}\n${command}`.
- **Spawn hook:** `spawnHook` (an option) may rewrite `{command, cwd, env}`.
- **The tool's `cwd`** is the factory's `cwd`, fixed per tool instance. The command has no `cwd` argument.

## 6. Results and errors (`execute`, `bash.ts:420-455`)

| Outcome | Tool result |
|---|---|
| exit code `0`, or `null` without abort or timeout | **success**: the text is the formatted output (§8), or `(no output)` when empty. `details` is `{truncation, fullOutputPath}` when truncated, else `undefined` |
| exit code non-zero (not `null`) | **error**: `${text ? text + "\n\n" : ""}Command exited with code ${exitCode}` |
| abort (`aborted` thrown) | **error**: `${text ? text + "\n\n" : ""}Command aborted`. The text is the formatted output collected so far, with the empty text `""` |
| timeout (`timeout:N` thrown) | **error**: `${text ? text + "\n\n" : ""}Command timed out after ${N} seconds`, where `N` is the seconds value as given |
| any other thrown error (invalid timeout, shell selection, missing `cwd`, spawn error) | **error**: the error's own message, unchanged. Output, if any, is discarded |

- **Error output is formatted** before the status line (`finishOutput` + `formatOutput(snapshot, "")`), so a truncation notice can precede `Command aborted`.
- **An error result's `details`:** Pi throws, so the error result carries no truncation `details`. Under the certified Layer-06 rule, a thrown error becomes `{content: [text], details: {}}`.

## 7. Partial updates (`bash.ts:353-401`)

- **Initial update:** before `exec`, the tool emits `onUpdate({content: [], details: undefined})`.
- **Data updates:** each data chunk marks the output dirty. An update is emitted at most once per 100 ms (`BASH_UPDATE_THROTTLE_MS`): immediately if 100 ms have passed since the last one, else by a timer.
  - Each update is `{content: [{type: "text", text: snapshot.content || ""}], details: {truncation: truncated ? truncation : undefined, fullOutputPath}}`.
  - It uses `snapshot({persistIfTruncated: true})`, so a temp file path can appear in a partial update.
- **On finish:** `finishOutput` emits a final pending update, then takes the final snapshot.
- **Scoping classification:** live throttled streaming was a `MINION_EXTENSION` *candidate* ("TUI/UX feature"). That classification is open (§10, Q2). The initial empty update and the update payloads are observable at Layer 06 (`tool_execution_update`).

## 8. Output accumulation and truncation (`output-accumulator.ts`; `truncate.ts`)

**Decoding.**
- One streaming `TextDecoder` (UTF-8, non-fatal, so invalid bytes become U+FFFD) decodes **the interleaved raw chunks of both streams** (`decode(data, {stream: true})`).
- A multi-byte sequence split across chunks is joined. A sequence interrupted by the other stream's chunk is decoded as it arrives.
- `finish()` flushes the decoder: incomplete trailing bytes become U+FFFD.

**Counting.**
- `totalRawBytes` counts the raw bytes.
- `totalDecodedBytes` counts the UTF-8 length of the decoded text, which can differ from the raw count after replacement.
- `totalLines` counts the `\n` characters, plus 1 if the last line is open.
- `getLastLineBytes()` is the decoded byte length of the current (last) line.

**The rolling tail.** The decoded text is kept as a tail.
- Once over `4 × maxBytes` (204800), it is trimmed to the last `2 × maxBytes` (102400) bytes at a UTF-8 boundary.
- If the cut is not at a line boundary, the snapshot drops the partial first line.

**The temp file.** It is opened when `totalRawBytes > maxBytes`, `totalDecodedBytes > maxBytes` or `totalLines > maxLines`, or by a `persistIfTruncated` snapshot of truncated output.
- Its path is `join(os.tmpdir(), "pi-bash-" + randomBytes(8).hex + ".log")`.
- It receives the **raw bytes**: the earlier chunks first, then every later chunk. It is closed at the end.

**Snapshot.**
- `truncateTail(tailText, {maxLines: 2000, maxBytes: 51200})` provides the content.
- `truncated` is `totalLines > maxLines || totalDecodedBytes > maxBytes`, recomputed from the totals and **not** from the tail alone.
- `truncatedBy` is the tail's own value, else `"bytes"` if the byte limit was exceeded, else `"lines"`.

**`truncateTail`** (`truncate.ts:168-243`):
- Lines come from `split("\n")`, dropping one trailing empty piece.
- It keeps whole lines from the end while both limits hold, counting the joining newline.
- If even the last line alone exceeds `maxBytes`, it keeps that line's last `maxBytes` bytes, starting at a UTF-8 boundary. That sets `lastLinePartial`.

**Formatted text** (`formatOutput`): `snapshot.content || emptyText`, then, if truncated:

| Case | Appended notice |
|---|---|
| `lastLinePartial` | `\n\n[Showing last ${formatSize(outputBytes)} of line ${totalLines} (line is ${formatSize(lastLineBytes)}). Full output: ${path}]` |
| truncated by lines | `\n\n[Showing lines ${totalLines - outputLines + 1}-${totalLines} of ${totalLines}. Full output: ${path}]` |
| truncated by bytes | `\n\n[Showing lines ${start}-${totalLines} of ${totalLines} (50.0KB limit). Full output: ${path}]` |

`formatSize`: under 1024 → `${n}B`; under 1 MiB → `${(n/1024).toFixed(1)}KB`; else `${(n/1048576).toFixed(1)}MB`.

## 9. Planned executable characterization (next pass)

**Approach.** Use the pinned sources' own code under Node v22.15.1:
- `truncate.ts` and `output-accumulator.ts` run whole: no runtime imports beyond Node built-ins.
- `bash.ts`'s `createLocalBashOperations` and `execute` body are sliced unmodified.
- `shell.ts` is imported with `getBinDir` stubbed, which is the only non-built-in import on the paths exercised.

**The neighborhood to probe:**
- timeout validation (`0`, `-1`, `NaN`, `Infinity`, `2147483.647`, `2147483.648`, fractional);
- exit codes `0`, `1`, `255`, and killed by an external signal (exit `null` → success);
- abort before and after spawn; a timeout during output;
- stdout and stderr interleaving;
- a multi-byte character split across chunks, and invalid UTF-8;
- truncation boundaries (2000/2001 lines, 51200/51201 bytes), a partial last line, a trailing newline, CRLF;
- the rolling-tail trim (over 204800 bytes);
- the temp file's content (raw bytes) and naming;
- the update sequence under controlled timing;
- a missing `cwd`;
- the shell-selection branches already fixed by scoping v4.

## 10. Questions for the Owner (to be posed as an options packet before the contract)

The scoping classified these as mapping or extension *candidates* without a decision.

| | Question |
|---|---|
| **Q1** | **Session environment variables.** Pi exposes `PI_SESSION_ID` / `PI_SESSION_FILE` / `PI_PROVIDER` / `PI_MODEL` / `PI_REASONING_LEVEL` (default on) and strips inherited copies. Minion's names and sources (session id, the persisted file, provider and model, reasoning level) need a mapping, and the default and the strip behavior need a decision. `getShellEnv` also prepends Pi's own `bin` directory to `PATH`; what is Minion's equivalent, if any? |
| **Q2** | **Partial updates.** Pi emits an initial empty update, then throttled (100 ms) snapshot updates with truncation details and the temp path. They are observable as Layer-06 `tool_execution_update` events. Parity, or the scoping's "TUI/UX feature" extension? |
| **Q3** | **Extension surfaces.** `operations` (pluggable exec, for example SSH), `commandPrefix`, `spawnHook` and `shellPath`. Which are part of Minion's `bash` factory API, and does Minion's execution-world model replace `operations` with the `ctx.shell` / `ctx.subprocess` provider? |
| **Q4** | **The process seam.** The scoping directs the kill/wait lifecycle to the certified `ctx.subprocess`. Pi's `bash` decodes both streams through **one** streaming decoder in arrival order. `ctx.shell.exec` decodes each stream separately, and `ctx.subprocess` gives raw bytes per stream. So exact interleaved decoding needs `ctx.subprocess` with merged raw chunks in arrival order. Arrival order across two pipes is itself scheduling-dependent. This is a feasibility row, not necessarily an Owner question. |
| **Q5** | (informational, scoping open question 4) `bash` does not take part in the mutation queue. This is recorded as Pi's own behavior. |

## 11. Executable characterization: results (pass 2)

`data/13-wp133/harness/bash_probe.mjs` runs pinned Pi's own `truncate.ts` and `output-accumulator.ts` whole. It runs sliced, unmodified `shell.ts`, `child-process.ts` and `bash.ts` (`resolveTimeoutMs`, `createLocalBashOperations`, `resolveSpawnContext`, the tool's `execute` body). Only `getBinDir` is stubbed.

The probe executes 36 real commands under Node v22.15.1:
- **Windows 11:** Git Bash (`C:\Program Files\Git\bin\bash.exe`, `-c`), output `out/pi-win32.json`.
- **Linux:** `node:22.15.1-bookworm-slim`, `/bin/bash`, as a non-root user, output `out/pi-linux.json`.

`harness/show.py` summarizes either output.

**The platforms agree on every observable except:**
- **The update count in three truncation cases** (chunk timing). The update **sequence shape** is stable: an initial empty update, then snapshots.
- **The missing-`cwd` message:** the path text.
- **An external `SIGKILL`** (`kill -9 $$`). Linux: exit `null` → **success**, `(no output)`. Windows Git Bash reports exit `2304` → `Command exited with code 2304`.

**Confirmed rules** (the §2–§8 source audit, now executed):
- **Output is kept verbatim**, including a trailing newline (`hello\n`) and CRLF. Empty output becomes `(no output)`, and so does a failing command with no output: `(no output)\n\nCommand exited with code 255`.
- **Non-zero exit:** `x\n\n\nCommand exited with code 1`. This is the output including its own newline, then `\n\n`, then the status.
- **Decoding:**
  - an invalid byte becomes U+FFFD (`x�y`);
  - a character split across two writes is joined (`€`);
  - a character interrupted by a stderr chunk becomes `�x��` (one U+FFFD, the stderr text, then one U+FFFD per orphaned continuation byte);
  - an incomplete trailing sequence becomes U+FFFD (`ok�`).
- **Truncation:**
  - 2000 lines, not truncated;
  - 2001 lines → `[Showing lines 2-2001 of 2001. Full output: <path>]` (the same with no trailing newline);
  - exactly 51200 bytes, not truncated;
  - 51201 bytes on one line → a partial line, `[Showing last 50.0KB of line 1 (line is 50.0KB). ...]`;
  - 5000 short lines → by lines, 3001-5000;
  - 369000 bytes → by bytes, `[Showing lines 7753-9000 of 9000 (50.0KB limit). ...]` through the rolling-tail trim;
  - a multi-byte partial line → `(line is 146.5KB)`. The decoded line length counts 3 bytes per `€`.
- **The temp file** is `pi-bash-<16 hex>.log`, holding the **raw** bytes (sizes and sha256 recorded).
- **A failing command with truncated output:** the error text carries the truncation notice, then `\n\nCommand exited with code 3`, and **no** `details` (Pi throws).
- **Timeouts:**
  - `before\n\n\nCommand timed out after 0.5 seconds`; without output, `Command timed out after 0.5 seconds`; `0.25` renders as `0.25`;
  - invalid values: `0`, `-1` and `Infinity` → `Invalid timeout: must be a finite number of seconds`; `2147483.648` → `Invalid timeout: maximum is 2147483.647 seconds`;
  - `2147483.647` is accepted.
- **Abort:** before spawn → `Command aborted`; during the command → `before\n\n\nCommand aborted`.
- **Updates:** the sequence for `printf a; sleep .4; printf b` is `[content: [] (no text), "a", "ab"]`.

This characterization pass needs no Owner input. The contract does: §10 Q1–Q3.

## 12. Owner decision Q1 (session environment), recorded

**Decision:** Option 1, a Minion namespace (`minion-agent#50` comment `5945376145`, verbatim).

**Variables:**
- `MINION_SESSION_ID`
- `MINION_SESSION_FILE`, only when a persisted session file exists; otherwise absent, never `""`
- `MINION_PROVIDER`
- `MINION_MODEL`
- `MINION_REASONING_LEVEL`

**Behavior:**
- Exposure is on by default.
- Inherited `MINION_*` copies are stripped, then rebuilt from live state.
- Inherited `PI_*` variables are **not** touched.
- There is no `PATH` change today. An optional managed-bin prefix hook exists for WP-13.4: it adds the directory once and never adds a placeholder.

**Classification:**

| Part | Classification |
|---|---|
| the mechanism | DIRECT_PI_PARITY / PI_SOURCE_ALGORITHM |
| the namespace | MINION_ARCHITECTURAL_MAPPING |
| the value source | MINION_SHARED_CONTRACT |
| the managed-bin `PATH` | MINION_ARCHITECTURAL_MAPPING |

**Disable mode** (decision §7, settled from source).
- Pi's `resolveSpawnContext` (`bash.ts:169-174`) deletes the five session keys **unconditionally**. It re-adds them only when `exposeSessionEnvironment && ctx`.
- Mapped: with exposure disabled, inherited `MINION_*` session variables are **removed** and nothing is injected.
- With exposure enabled but no live context, the same holds: removed, not re-added.

**Still open:** Q2 (partial updates) and Q3 (the factory surface).

## 13. Owner decisions Q2 and Q3, recorded

**Source:** `minion-agent#50` comment `5950860191` (verbatim).

**Q2: partial updates.** The final result is core; partial-output updates are optional UX.
- Pi's throttled updates (§7), its initial empty update and the 100 ms cadence are **not certified**. Zero intermediate `tool_execution_update` events is conforming. Synthetic updates must not be fabricated.
- The final result **is** certified exactly: accumulation, exit status, abort, timeout, error text, tail truncation, limits, the temp file, and the final text and `details`.
- Future streaming is `MINION_EXTENSION / OPTIONAL_UX`, carried by the existing event and update architecture. It must not change the final result.

**Q3: factory surface.**

| Pi option | Decision | Classification |
|---|---|---|
| `shellPath` | exposed as `shell_path`, optional. Truthy → scoping v4 branch 1; absent or falsy → platform discovery | PI_SOURCE_ALGORITHM, binding projection |
| `exposeSessionEnvironment` | exposed, default `true` (§12) | MINION_ARCHITECTURAL_MAPPING |
| `commandPrefix` | not exposed in core; future extension | unadopted Pi extension API |
| `spawnHook` | not exposed in core; future extension | unadopted Pi extension API, not a divergence |
| `operations` | no parameter; mapped to the execution context (`ctx.subprocess` for the process lifecycle, consuming Layer 12 unchanged; `ctx.fs` where required; session state) | MINION_ARCHITECTURAL_MAPPING / MINION_SHARED_CONTRACT |
| managed-bin `PATH` prefix | none today; a future concern of the execution environment, with no WP-13.4 dependency | (§12) |

**Feasibility.** `13-wp133-feasibility-matrix.md` maps the "execution context" Q3 names onto the certified seams. Three capabilities Pi's `bash` reads are missing below Layer 13:
- `WP133-F1`: the world's environment (read; spawn with inherited keys removed);
- `WP133-F2`: the world's platform;
- `WP133-F3`: per-call live session state for a tool's `execute`.

Their interface shapes go to the Owner before the contract can freeze.

## 14. Independent audit 1 and remediation

**Codex audit 1** (docs #229 @ `fafce487`; comment `5965735271`, verbatim): CHANGES REQUIRED. All 36 Windows cases replayed identically; only the random `cwd/missing` path differed. The gaps F1–F3 and the settlement composition were confirmed. There were three findings:

- **`WP133-AUD-R001`** (CONTRACT_ASSURANCE_DEFECT): the matrix said Windows argv passes UTF-16 through verbatim. It does not.
  - **Remediation:** `harness/projection_probe.mjs`, run under Node v22.15.1 on Windows 11 with Git Bash 5.3.15 and on `node:22.15.1-bookworm-slim` (`out/projection-{win32,linux}.json`).
  - **Finding:** both platforms agree. Node replaces each unpaired surrogate with U+FFFD before the OS boundary on argv and on stdin alike:
    - `a\uD800b` and `a\uDC80b` → child argv `0061 FFFD 0062`; bytes in bash `61 EF BF BD 62`;
    - a reversed pair → two U+FFFD;
    - a valid pair is kept.
  - **Rule:** the command is projected to its scalar form before transport, on both platforms and both transports. The raw-argument carrier is unchanged.
- **`WP133-AUD-R002`** (CONTRACT_ASSURANCE_DEFECT): Pi's default `TextDecoder` strips one leading BOM, and the decoder the matrix proposed did not.
  - **Remediation:** the same probe drives pinned `OutputAccumulator` directly. Results on both platforms:
    - `EF BB BF 61` → `a`, 1 decoded byte, whether given whole, split 1+2 or split 1+1+1;
    - a doubled BOM keeps one U+FEFF;
    - a non-leading BOM is kept (`x﻿a`, 5 bytes);
    - a BOM alone → empty (so `(no output)`);
    - `EF BB` then `61` → `�a`.
  - The rule is stated in the matrix's output row.
- **`WP133-AUD-R003`** (CONTRACT_ASSURANCE_DEFECT): `canonical_path` is followed existence only for a provider that canonicalizes; `not_supported` is not absence.
  - **Disposition** (matrix §2, disclosed): `bash` requires a canonicalizing `ctx.fs`. `not_supported` settles the call with a disclosed Minion error, never "does not exist".
  - No other certified operation gives followed existence: `exists` and `file_info` are `lstat`-based, and `check_readable` also requires readability.

**Nonblocking audit notes, carried into the contract:**
- **Settlement over `ctx.subprocess`:** do not settle on `wait()` alone, and do not wait indefinitely for EOF. The 100 ms idle grace re-arms on accepted data. `Err(aborted)` from `wait()` is the expected cancellation outcome, while the final classification checks abort first, including an abort during the post-exit grace. Pending reads are cancelled and released at settlement.
- **Stdin transport:** writing and closing stdin must not block the timeout, output and exit monitoring. Pi's `stdin.end(command)` queues the write and closes; a child that never reads must still time out or abort. A write failure is ignored.
- **Timer resolution:** Node's `setTimeout` coerces a delay below 1 ms to 1 ms and schedules at integer-millisecond libuv resolution. Fractional-millisecond timeouts (for example `0.0005` s) need boundary witnesses in the contract.
- **Matrix §3:** Windows env key order is observable through duplicate arbitration (`12-wp12e4-characterization.md` C001). This is revised.
- **Temp-file and raw-error wrappers:** the contract states their exact rules; they are not left as "generic".

## 15. Audit 2 and convergence episode CE-WP133-01 (`WP133-AUD-R003`)

**Codex audit re-review 2** (docs #229 @ `901d9798`; comment `5966930289`, verbatim):
- R001 and R002 are **CLOSED**.
- **R003 NOT CLOSED.** Requiring a canonicalizing provider does not make `canonical_path` equal to followed existence. Pinned `getShellConfig` on Linux selects and runs a shell at `/proc/<pid>/fd/<n>`, the descriptor of an unlinked file: `existsSync` is true, the shell runs and prints `ok`, while `realpath` is ENOENT.
- Codex directed an audit of EXEC-007 `probe_dir_entry`.
- R003 has now survived two independent reviews, so **§11.8 trigger A** has fired. This section is the convergence characterization and checkpoint.

**Characterization: an executed differential.** Pinned Node's three predicates (`existsSync`, `access(F_OK)`, `realpath`) are compared with the certified EXEC-007 `probe_dir_entry` OS sequence: `lstat`, then `stat` if the entry is a symlink (`filesystem.py::_probe_dir_entry_sync`, `minion-agent` main `4c735ed6`). Python executes it on the same fixtures.

- **Linux.** Harness `harness/existence_probe.sh`. Node runs in `node:22.15.1-bookworm-slim` (`node@sha256:ec318fe0…`) as uid 1000; CPython 3.12.15 runs in `python:3.12-slim` (`python@sha256:eeb8088e…`) as uid 65534. Outputs: `out/existence-{node,python}-linux.json`. There are 13 cases:
  - a file, a directory and the directory with a trailing slash;
  - symlinks to a file and to a directory;
  - a dangling symlink;
  - a FIFO and a symlink to a FIFO;
  - a file under a mode-000 directory;
  - a symlink loop;
  - a missing path;
  - `file/child`;
  - `/proc/PID/fd/7`, an unlinked copy of `/bin/sh` held open.
- **Windows 11.** Harness `harness/existence_probe_win.mjs`, Node v22.15.1 and CPython 3.13.5, output `out/existence-win32.json`. There are 9 cases:
  - a file, a directory and the directory with a trailing separator;
  - symlinks to a file and to a directory;
  - a dangling symlink;
  - a junction;
  - a missing path;
  - `file\child`.

| Predicate | Linux (13) | Windows (9) |
|---|---|---|
| `existsSync` vs `probe_dir_entry` `Ok` | **equal on all 13**, the descriptor path included | **equal on all 9** |
| `access(F_OK)` vs `probe_dir_entry` `Ok` | **equal on all 13** | differs on the **dangling symlink**: `access` succeeds (Node's Windows `access` does not follow), `probe` ENOENT |
| `access(F_OK)` vs non-following `lstat` (`file_info`) `Ok` | not executed; inferred to differ on the dangling symlink and the symlink loop (`lstat` succeeds on any symlink). Not used on POSIX | **equal on all 9** |
| `realpath` (`canonical_path`) vs `existsSync` | differs on the **descriptor path** | equal |

**Checkpoint (proposed): the R003 disposition.**
- **Shell discovery** (`existsSync`, scoping v4 branches 1, 2a, 2b and 2c), on both platforms: the candidate exists iff `ctx.fs.probe_dir_entry(p)` is `Ok`. Any other `Err` means "not found", as `existsSync`'s catch-all `false` does.
- **cwd check** (`fsAccess(cwd, F_OK)`):
  - `POSIX`: `probe_dir_entry(cwd)` is `Ok`.
  - `WINDOWS`: `file_info(cwd)` is `Ok`. It does not follow symlinks, matching Node's Windows `access`.
  - The platform comes from WP-12.E4 (#130).
  - Any other `Err` gives `Working directory does not exist: ${cwd}\nCannot execute bash commands.`
  - On Windows, a dangling-symlink cwd passes the check, as in Pi, and then fails at spawn: the spawn-error wrapper.
- **`not_supported`** from either operation is never treated as absence. It settles the call with the disclosed Minion error (contract §Error text). EXEC-007 lets a provider omit `probe_dir_entry`; every local provider supplies it.
- **`canonical_path` is not used.**

**Witnesses:** both differential harnesses become contract evidence. These cases carry over:
- the Linux descriptor-path shell, which Pi selects and runs;
- the dangling-symlink `shell_path`, which is not found;
- the Windows dangling-symlink cwd, which passes the check and fails at spawn.

**Negative controls (bash binding level):**
- a `canonical_path`-based existence check, killed by the descriptor path;
- an `exists`/`file_info`-based `existsSync`, killed by the dangling symlink;
- a `probe_dir_entry`-based Windows cwd check, killed by the Windows dangling-symlink cwd.

```text
CONVERGENCE CHECKPOINT (CE-WP133-01)
    PROPOSED
OPEN FINDINGS
    WP133-AUD-R003 (trigger A)
DISPOSITION
    existsSync -> probe_dir_entry Ok; access(F_OK) -> POSIX probe_dir_entry Ok, WINDOWS file_info Ok;
    not_supported -> disclosed prerequisite error; canonical_path not used
EVIDENCE
    out/existence-{node,python}-linux.json (13), out/existence-win32.json (9)
NEXT_OWNER
    Codex (checkpoint review)
```
