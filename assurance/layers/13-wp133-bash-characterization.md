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

- **Error output is formatted** before the status line, so a truncation notice can precede it. **Corrected (`WP133-CON-R001`, §16):** there are two branches.
  - Abort and timeout are caught and formatted with `formatOutput(snapshot, "")`.
  - A non-zero exit is classified **after** the ordinary `formatOutput(snapshot)`, whose empty text is `(no output)`. So `exit 255` with no output gives `(no output)\n\nCommand exited with code 255`, as §11 records.
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
- If the cut is not at a line boundary, the snapshot drops the partial first line. **Corrected (`WP133-CON-R002`, §16):** the drop happens only when the tail contains a `\n`. With no `\n`, the whole retained tail is the snapshot text (`getSnapshotText`: `firstNewline === -1 ? this.tailText : …`).

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

## 16. Contract review 1 and its remediation (`WP133-CON-R001`..`R004`)

**Codex independent contract checkpoint review 1** (docs #229 @ `30972b61`; comment `5971240442`, verbatim): **CHANGES REQUIRED**, four `CONTRACT_ASSURANCE_DEFECT`s. Codex replayed the 36 Windows cases, the projection probe and the existence probe unchanged, and all matched the committed outputs.

**Trigger check (§11.8):**
- **A** has not fired: each finding is new in this review.
- **B** is treated as fired: the output surface has produced successors after remediation. Audit 1 raised `R002` (BOM); this review raised `CON-R001` (formatting) and `CON-R002` (rolling tail).
- **C** fires if the two audits count as complete reviews.
- The work package is already in `CONTRACT_CONVERGENCE` (`CE-WP133-01`). The four findings are folded into that episode for targeted closure (§11.8.7), then one final complete review (§11.8.8). Codex's evidence narrows each finding to one rule, so a targeted correction can close it.

**Pinned Pi re-audited** (`b7bb00b9`): `bash.ts` `formatOutput`, its caught branch and its completed branch; `output-accumulator.ts` `trimTail` and `getSnapshotText`; `bash.ts` `setTimeout(…, timeoutMs)`. **Node v22.15.1:** `internal/timers` `Timeout` (a delay outside `[1, TIMEOUT_MAX]` becomes 1) and `insert` (`MathTrunc(msecs)`), read from the host's own internals with `--expose-internals`.

| Finding | Rule (now in `spec/tools.md` WP-13.3) | Evidence |
|---|---|---|
| `CON-R001` | an execution-completed result, including a non-zero exit, uses `(no output)`; only an abort or a timeout uses `""`; any other error discards output | `out/pi-*.json` `exit/255-no-output`, `exit/one-no-output` (already committed) |
| `CON-R002` | the `starts_at_line_boundary` flag; a snapshot drops through the first `\n` only when one exists | new `harness/boundary_probe.mjs` → `out/boundary-win32.json` `rolling`: 7 cases on the pinned accumulator |
| `CON-R003` | the timer is scheduled for `max(1, trunc(timeout × 1000))` whole ms; validation and the status text are unchanged | `out/boundary-win32.json` `timers`: 8 values, the scheduled duration read from Node's timer list |
| `CON-R004` | the feasibility matrix reconciled (revision 3): F1–F3 resolved by `EXEC-010`/`TOOL-042`, Rust's configured baseline, verdict FEASIBLE; WP-12.E4 is closed in both languages (Rust `a0ff3e47`) | `13-wp133-feasibility-matrix.md` §§1, 2, 3, 6; the revision-2 verdict kept as §6.1 |

**Rolling-tail rows** (`boundary-win32.json`):
- a single 250000-byte line, in one chunk and in five: content 51200 bytes, one partial line;
- a single line of `€`, 210000 bytes: 51198 bytes;
- a mid-line cut with a later newline in the same chunk: the 60000-byte line, partial at 51200;
- a mid-line cut with the newline in a later chunk: only the 1000-byte `b` line. Here `lastLinePartial` is false and `truncatedBy` is `"bytes"`, from the totals;
- a cut just after a newline: nothing dropped;
- exactly 204800 bytes: no trim.

The accumulator and timers are pure JavaScript, so the rows are platform-independent; the Windows run is recorded.

**Timer rows:**

| seconds | 0.0005 | 0.000999 | 0.001 | 0.0019 | 0.0025 | 0.25 | 1.5 | 2147483.647 |
|---|---|---|---|---|---|---|---|---|
| scheduled ms | 1 | 1 | 1 | 1 | 2 | 250 | 1500 | 2147483647 |

**New negative controls** (spec, witnesses §4):
- `""` as a non-zero exit's empty text;
- always or never dropping the partial first line;
- scheduling the raw or rounded `ms`.

```text
CONVERGENCE (CE-WP133-01), targeted closure requested
OPEN FINDINGS
    WP133-CON-R001, WP133-CON-R002, WP133-CON-R003, WP133-CON-R004 (remediated, pending closure)
NEXT_OWNER
    Codex (targeted closure review of the four findings, with known-bad checks)
```

### 16.1 Targeted closure 1 and `N001`

**Codex targeted closure 1** (docs #229 @ `9ddd59c8`, `.tmp/wp133-review/CLOSURE1.md`): `WP133-CON-R001`..`R004` are **all provisionally CLOSED**.
- Codex's fresh run of `boundary_probe.mjs` was byte-identical to the committed blob.
- Its known-bad checks:
  - R001: the old empty text gives `Command exited with code 1` and `Command exited with code 255`, so both pinned no-output cases reject it;
  - R002: always-drop fails three rows;
  - R003: the raw product fails four timer rows and rounding fails two;
  - R004: the active-feasibility assertions fail against `30972b61`.

**`N001`** (non-blocking, control accounting): the spec's "never dropping" control was **not** killed by the seven rows, because every newline-bearing row ended in a line longer than 51200 bytes, which `truncateTail` cuts anyway.

**Response: the control is observable, and it is now killed.** A search over a long fragment followed by `k` short lines (`k` from 1 to 2500) found 21 differing cases. Three are now permanent rows:

| Row | Pinned content / truncation | Never-drop |
|---|---|---|
| `longLineThenNewline` (`a`×250000 + `\n`) | empty; `bytes`, totalLines 1, outputLines 0, outputBytes 0 | 51200 `a`, one partial line |
| `longLineThenTenLines` | 9 lines, 18 bytes | one byte fewer: the fragment is kept and cut |
| `longLineThen2001Lines` | `bytes`, 2000 lines, 4000 bytes | `truncatedBy` `"lines"`, 3999 bytes |

- The probe now runs both controls itself, as subclasses of the pinned accumulator; Pi's source is unchanged. Results are in `boundary-win32.json` `controls`.
- `longLineThenNewline` also records a Pi quirk that an implementation must reproduce: an empty snapshot with a truncation notice, `(no output)\n\n[Showing lines 2-1 of 1 (50.0KB limit). …]`.
- The rule (§8, spec) is unchanged. This adds evidence only.

```text
CONVERGENCE (CE-WP133-01)
    WP133-CON-R001..R004 PROVISIONALLY CLOSED (targeted closure 1); N001 answered with discriminating rows
NEXT_OWNER
    Codex (final complete exact-SHA contract review, section 11.8.8)
```

## 17. Final complete review 1 and `WP133-CON-R005`

**Codex final complete review 1** (§11.8.8; docs #229 @ `3ec675de`; comment `5971607011`, verbatim): **CHANGES REQUIRED**, one finding, classified **Case A**. `CON-R001`..`R004` and `N001` remain closed. Codex re-ran the boundary, projection and existence probes (byte-identical) and the 36-case Windows probe (equal except the fresh temporary path).

- **`WP133-CON-R005`** (CONTRACT_ASSURANCE_DEFECT). Pinned `findBashOnPath` calls Node `spawnSync` with no `maxBuffer`. Node v22.15.1's default is `1024 * 1024`, and `spawn_sync.cc` counts it **across the captured streams**. Overflow kills the probe with `ENOBUFS`, so the lookup fails. The contract had no budget, so a lookup that prints a valid path followed by too much output was selectable.

**Trigger check (§11.8):**
- **A** has not fired: R005 is new.
- **B** has not fired: the lookup's resource bound is a new surface, not output, timers, environment or existence.
- **C:** this is the second rejected complete contract review, the fourth if both audits count. Codex's classification is Case A, so the next steps are narrow remediation, targeted closure, then the final complete review.

**Pinned source re-audited:** `shell.ts` `findBashOnPath`, both branches, with options `{encoding: "utf-8", timeout: 5000, windowsHide: true}`.

**Node, executed directly** (combined raw bytes → result): stdout only, 1048576 → status 0; 1048577 → `status null`, `ENOBUFS`. The same boundary holds for stderr only and for 524288 + 524288 versus 524289 + 524288.

**Decoding, characterized while here:** `encoding: "utf-8"` is `Buffer#toString`, WHATWG replacement that keeps the BOM. `EF BB BF /b FF \n` decodes to `FEFF 002F 0062 FFFD 000A`, and `trim` removes the leading U+FEFF.

**Remediation:** see spec "The lookup"; feasibility matrix revision 4, lookup row; new `harness/lookup_probe.mjs` → `out/lookup-win32.json`. The probe:
- slices the pinned `findBashOnPath` and runs it unchanged;
- replaces only the lookup program, with Pi's options captured and recorded;
- has 8 rows and 2 controls, and fails on any child error other than `ENOBUFS`. A first draft passed megabytes on the command line, and its children failed with `ENAMETOOLONG`, which would have looked like a refusal; the guard catches that.

The rule changes nothing else: the discovery order, time limit, first-line parsing, existence checks, error text and the `bash` command's own output are unchanged.

```text
CONVERGENCE (CE-WP133-01)
OPEN FINDINGS
    WP133-CON-R005 (remediated, pending targeted closure)
NEXT_OWNER
    Codex (targeted closure of R005, then final complete review)
```

## 18. Targeted closure 2 and convergence episode `CE-WP133-02` (the lookup lifecycle)

**Codex targeted closure 2** (docs #229 @ `496872bf`, `.tmp/wp133-review/CLOSURE2.md`):
- **`WP133-CON-R005` NOT CLOSED.** The budget amount, the combined accounting, the boundary, the lookup-only scope and the decoding were confirmed (8 rows byte-identical, both controls killed). But "overflow or time limit ⇒ not found" is wrong: Pi tests only `status === 0 && stdout`, and Node keeps a recorded exit status when a later error arrives.
- **New: `WP133-CON-R006`.** `spawnSync` collects until exit **and** pipe completion, with no idle grace. A path written by a descendant after the parent exits is selected.
- Codex corrected its own FINAL1 claim, "overflow always refuses", as too broad. That claim is kept as history.

**Trigger check:**
- **A has fired for R005:** it survived the final review and this targeted closure.
- R006 is on the same coupled surface: parent exit, the pipes, resource interruption and selection.

**Convergence episode `CE-WP133-02`** opens for the bounded **lookup-lifecycle** surface. `CE-WP133-01`'s findings (existence, `R001`..`R004`) stay provisionally closed and are not reopened.

### 18.1 Sources audited

- **Pinned `shell.ts` `findBashOnPath`**, both branches.
- **Node v22.15.1 `src/spawn_sync.cc`** (fetched at tag `v22.15.1`, file SHA-1 `c6c9d2d0…`):
  - `TryInitializeAndRunLoop`: `uv_run(UV_RUN_DEFAULT)`, which runs until the process handle and every pipe close;
  - the kill timer: `uv_unref`, started at spawn for `timeout`;
  - `OnRead`: stores the chunk, **then** `IncrementBufferSizeAndCheckOverflow`;
  - `Kill()`: `uv_process_kill` (`SIGTERM`) **only if the process has not exited**, then `CloseStdioPipes()`;
  - `OnExit`: records `exit_status_` and `term_signal_`;
  - `SetError`: the first error wins and never clears the status;
  - `BuildResultObject`: `status` is null only for a signal termination (or no start), else the exit code, **alongside** any `error`.

### 18.2 Behaviour matrix (executed, `out/lookup-lifecycle-win32.json`)

| Row | Lookup program | Pi `status` / `error` | Selected |
|---|---|---|---|
| `parentPathExit0` | the parent prints the path, exits 0 | 0 / — | path |
| `parentPathExit1` | the same, exits 1 | 1 / — | — |
| `descendantPathAfterExit` | the parent exits 0 at once; a descendant holding the pipes prints the path 250 ms later | 0 / — | **path** |
| `descendantPathAfterExitParentExit1` | the same, the parent exits 1 | 1 / — | — |
| `overflowWhileAlive` | path, then 2 MiB stderr, while alive | null (`SIGTERM`) / `ENOBUFS` | — |
| `overflowAfterExit` | path, exit 0; a descendant floods 2 MiB stderr at 250 ms | 0 / `ENOBUFS` | **path** |
| `overflowAfterExitParentExit1` | the same, exit 1 | 1 / `ENOBUFS` | — |
| `timeoutWhileAlive` | path, then alive for 5400 ms | null (`SIGTERM`) / `ETIMEDOUT` | — |
| `timeoutAfterExit` | path, exit 0; a descendant holds the pipes for 5400 ms | 0 / `ETIMEDOUT` | **path** |
| `descendantPathAfterTimeout` | exit 0; a descendant prints the path at 5400 ms | 0 / `ETIMEDOUT` | — (stdout empty at the interruption) |
| `descendantPathThenOverflow` | exit 0; a descendant prints the path at 250 ms, then floods at 350 ms | 0 / `ENOBUFS` | **path** |

**Discriminating dimensions:**
- whether the process exited before the interruption;
- whether output comes after the exit;
- which interruption, if any;
- the exit code.

The budget boundary itself is `lookup-win32.json` (8 rows, §17).

### 18.3 Observable rules

These are now in the spec, "The lookup":
1. Collection ends at exit **plus** EOF on both pipes, with no idle grace; or at the budget, after storing the crossing chunk; or at 5000 ms.
2. An interruption terminates only an unexited process, which then has no status. An exited process keeps its status.
3. Selection is `status === 0 && stdout`, then the first line after `trim`, then the platform's existence rule. The interruption never forces "not found" by itself.
4. Decoding is unchanged from §17.

### 18.4 Minimal witnesses and negative controls

The probe runs four asynchronous compositions over `child_process.spawn` against the pinned result:

| Composition | Disagrees on |
|---|---|
| **the contract rule** (18.3) | **none** (`contractAgreesOnAllRows: true`) |
| exit-only settlement | `descendantPathAfterExit`, `descendantPathThenOverflow` |
| bash's 100 ms idle grace | `descendantPathAfterExit`, `descendantPathThenOverflow` |
| fail on any interruption | `overflowAfterExit`, `timeoutAfterExit`, `descendantPathThenOverflow` |

From `lookup-win32.json`: an unbounded budget is killed by the three over-budget rows, and a per-stream budget by the stderr and combined rows.

The probe ran twice, with identical output. The timing margins are at least 250 ms around both the 100 ms grace and the 5000 ms limit.

### 18.5 Implementation constraints, mapping and exclusions

- **Feasibility:** the rules compose over the certified Layer 12 seams (`spawn`, concurrent `read_chunk`, `wait`, `terminate`, read cancellation), with no new API.
- **Kill scope (`MINION_ARCHITECTURAL_MAPPING`):** Pi signals only the direct child; Minion's `terminate()` is a tree kill. Selection is the same, because an unexited lookup is not found either way. Descendants of an already-exited lookup are left alone in both.
- **Out of scope:**
  - exact capture sizes after a budget interruption, which depend on read chunking (only the first line matters to selection);
  - a POSIX `which` run (the same `spawnSync` path; not executed on Linux in this pass);
  - Pi's `windowsHide` (a console-window flag, not observable to the tool).

```text
CONVERGENCE CHECKPOINT (CE-WP133-02)
    PROPOSED
OPEN FINDINGS
    WP133-CON-R005 (trigger A), WP133-CON-R006
ROOT-CAUSE SURFACE
    the where/which lookup lifecycle: process exit x pipe completion x budget/timer interruption x selection
NEXT_OWNER
    Codex (checkpoint review)
```

## 19. Checkpoint review 1 of `CE-WP133-02`, the Owner decisions, and `DIV-001`

**Codex checkpoint review 1** (docs #229 @ `7e23ad62`; comment `5971794856`): CHANGES REQUIRED, `CE-WP133-02-C001`.
- Pi's lookup interruption is a direct-child `SIGTERM`. On POSIX, a lookup that handles it and exits 0 keeps `status` 0 and is selected.
- Minion's `terminate()` is an uncatchable group `SIGKILL`, so the earlier claim "selection unaffected" was disproved.
- This is a governance question.

**Owner decisions:**
1. `CE-WP133-02-C001` = Option 1 (#50 comment `5973189849`): a new Layer 12 direct-child termination, WP-12.E5 (#141). E5 went through contract approval and a Python implementation. Its review exposed POSIX PID-reaping races on threaded-reaper hosts (`WP12E5-I001`).
2. **Practical-parity cut-over** (#50 comment `5973629192`; #75 comment `5973629428`). WP-12.E5 is **superseded** (#141 closed; PRs #142/#237 closed unmerged and preserved). This difference is accepted as **`DIV-001`** (`assurance/pi-divergences.md`). The lookup interruption uses the certified `terminate()`.

**Revised rule** (spec, "The lookup", "On interruption"): an interruption of an **unexited** lookup calls `terminate()`, and its status is what `wait()` reports. That status is not 0 when the kill is effective (corrected in §19.1). An exited lookup keeps its status. Selection and every other lifecycle rule (§18) are unchanged.

**Evidence: the 15-row lifecycle probe**, run on Windows and on Linux (`node:22.15.1-bookworm-slim`, twice, byte-identical).
- **New rows:** four `SIGTERM`-response rows (`trapExit0OverflowWhileAlive`, `trapExit0TimeoutWhileAlive`, `trapExit7TimeoutWhileAlive`, `trapDelayedExit0TimeoutWhileAlive`).
- **A probe fix:** the `flood` step now completes, or fails quietly, before the next step. Before, a following `process.exit()` could discard a pending pipe write on Linux, and an `EPIPE` could crash the program, so two rows did not test what they were named for.

| Composition | Windows | Linux |
|---|---|---|
| **Minion** (uncatchable kill on interruption) | agrees with Pi on all 15 | differs from Pi on **exactly** the 3 `DIV-001` rows (`trapExit0Overflow`, `trapExit0Timeout`, `trapDelayedExit0Timeout`: Pi selects, Minion does not). `trapExit7` agrees, because neither selects |
| Pi-faithful direct `SIGTERM` (characterization) | agrees on all 15 | agrees on all 15 |
| exit-only settlement (control) | killed by 2 rows | killed by 2 rows |
| 100 ms idle grace (control) | killed by 2 rows | killed by 2 rows |
| fail on any interruption (control) | killed by 3 rows | killed by 3 rows |

The probe composes Minion's kill as a `SIGKILL` of the lookup process. That models the uncatchable kill. The tree scope is Layer 12's certified behaviour and does not affect selection.

```text
CONVERGENCE CHECKPOINT (CE-WP133-02), revised
    PROPOSED
OPEN FINDINGS
    WP133-CON-R005, WP133-CON-R006 (lookup lifecycle), CE-WP133-02-C001 (resolved by Owner: DIV-001)
NEXT_OWNER
    Codex (checkpoint re-review)
```

### 19.1 Checkpoint re-review 2 and `CE-WP133-02-C002`

**Codex checkpoint re-review 2** (docs #229 @ `64fc2110`, `.tmp/wp133-review/CE02-CHECKPOINT2.md`): CHANGES REQUIRED.
- Codex replayed all 15 rows on both platforms, byte-identical. Minion differs from Pi on exactly the `DIV-001` rows, and every control is killed. `C001` is OWNER_RESOLVED.
- **`CE-WP133-02-C002`** (CONTRACT_ASSURANCE_DEFECT): the text claimed that an interrupted, initially live lookup is "never" selected. But `terminate()` is best-effort, and §6/`L12-R020` keeps the real exit code. So a lookup that completes **naturally** with 0 after the interruption decision, and before the kill dispatch, is selected.
- This is ordinary parity, not `DIV-001`. Pi's `Kill()` also checks the recorded exit first.

**Remediation:**
- The spec, matrix revision 6 and the `DIV-001` entry now say that an **effective** hard kill selects nothing, while a real code from a natural completion or an unsuccessful kill is read by the unchanged predicate.
- New permanent witness `harness/lookup_termination_race.py` (from Codex's reviewer probe). It drives the accepted Layer 12 `LocalSubprocess` from `main` `a0ff3e47`. Its only control point is `_issue_kill`, which lets the real child exit 0 before forwarding the real tree-kill dispatch.

| Host | Live at interruption | Cause | `wait()` code | Selected | Control (interruption forces "not found") |
|---|---|---|---|---|---|
| Windows (Python 3.13.5) | yes | `explicit` | `0` | `C:/valid/bash.exe` | killed |
| Linux (Python 3.13.15) | yes | `explicit` | `0` | `/valid/bash` | killed |
