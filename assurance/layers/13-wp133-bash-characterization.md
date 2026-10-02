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
