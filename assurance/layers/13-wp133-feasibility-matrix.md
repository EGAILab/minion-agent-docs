# Cross-Language Feasibility Matrix — `WP-13.3`: `bash`

**Required by:** `process/agent-workflow.md` §4.1.1. `bash` crosses the Layer 05/06 boundary, is string- and byte-heavy, and rests on three Layer 12 seams.
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`, Node v22.15.1. **Author:** Claude. **Independent checkpoint reviewer:** Codex.
**Inputs:**
- characterization `13-wp133-bash-characterization.md` (§§1–13), with its executable evidence in `data/13-wp133/`;
- Owner decisions Q1 (`minion-agent#50` comment `5945376145`) and Q2/Q3 (comment `5950860191`);
- scoping v4 (shell-selection matrix);
- the certified Layer 12 contract (`spec/execution.md` §§3, 5, 6, 7) and its Python and Rust seam shapes, read for representation only.

**Verdict (§6): BLOCKED.** There are three lower-layer capability gaps, `WP133-F1` to `F3`. Each needs an additive lower-layer interface that does not exist yet. Under `minion-agent#75` items 5 and 6 the interface's shape is an Owner decision, as every earlier Layer 12 extension (`WP-12.E1` to `E3`) was. Everything else is `AUDITED`.

---

## 1. Runtime value-domain matrix

| Observable value / field | Pi wire/source repr | Pi runtime repr | Python repr | Rust repr | Canonical serialization | Lossless across all? | Risk / witness needed |
|---|---|---|---|---|---|---|---|
| `command` argument | JSON string | JS string (UTF-16; lone surrogates possible, `L0206-D002`) | `str` (`L0206-D002` domain) | per `L0206-D002` | JSON string, `\uD800` escapes | **AUDITED**: the raw-domain carrier is certified by `L0206-D002`. Placing it on argv or stdin is a separate projection, below | lone surrogate in `command` (row "argv/stdin projection") |
| `command` on argv / stdin | — | Node `spawn` argv: UTF-16 → OS. Windows `CreateProcessW` takes UTF-16 verbatim; POSIX encodes to UTF-8, lone surrogate → U+FFFD. Stdin: `end(string)` UTF-8, lone surrogate → `EF BF BD` | `subprocess` argv `str`; Windows UTF-16; POSIX `os.fsencode` (surrogateescape ≠ WHATWG) | `OsString`: Windows UTF-16 via `OsStringExt::from_wide`; POSIX bytes | the bytes the child receives | **AUDITED, rule needed**: the contract states the projection as the child-observed bytes (POSIX and stdin: WHATWG UTF-8 encode; Windows argv: UTF-16 code units). Python must not use surrogateescape | witness: `printf %s "<lone surrogate>"` per platform |
| `timeout` argument | JSON number, optional | JS number (`-0`, ±Infinity reachable at runtime, `L0506-D001`) | `float`, `None` | `Option<f64>` | JSON number | **AUDITED**: `resolveTimeoutMs`, characterization §2 | `0`, `-0`, `-1`, `NaN`, ±Infinity, `2147483.647`/`.648`, `0.25`; the error text renders `MAX_TIMEOUT_MS / 1000` = `2147483.647` |
| timeout in the status text `Command timed out after ${timeout} seconds` | — | `String(number)` of the **given** seconds | needs JS `Number#toString` | needs JS `Number#toString` | text | **AUDITED**: F1 rendering, already a shared helper (`_js.py` / Rust's JS-number formatter, used by WP-13.2) | `0.25`, `1e-7` → `1e-7`, `1.5`, `100`, `0.1+0.2` |
| output bytes → text | raw `Buffer` chunks from both pipes | one streaming `TextDecoder` (WHATWG UTF-8, non-fatal) | `codecs.getincrementaldecoder("utf-8")(errors="replace")`: equal to Node on every probed case (`F0 80`, `ED A0 80`, `F4 90`, `C0 AF`, `FF`, a truncated tail, and splits across 2–4 chunks; scratch probe 2026-10-02) | a streaming decoder with WHATWG replacement (for example `encoding_rs`) | text | **AUDITED, rule needed**: the contract names WHATWG streaming decode across the merged chunk sequence. Pinned Node is the authority, and each binding shows equality on the corpus | split char across chunks; char interrupted by the other stream; invalid byte; truncated trailing sequence; the maximal-subpart cases `F0 80`, `ED A0 80`, `F4 90` |
| line/byte counts, truncation | — | UTF-8 byte length of decoded text; `\n` count | ints | `usize` | numbers in `details.truncation` | **AUDITED**: integer counts; `truncate.ts` is already Layer 13's shared constant set (`TOOL-028`) | 2000/2001 lines, 51200/51201 bytes, rolling trim above 204800 |
| `formatSize` | — | `toFixed(1)` on `n/1024` | needs JS `toFixed` | needs JS `toFixed` | text | **AUDITED**: F1; `toFixed(1)` is exact decimal rounding of the binary64 value. The WP-13.1 `read` notice already uses the same helper | `(51201/1024).toFixed(1)`, `150016/1024`; a value at a `.x5` boundary |
| `details.truncation` | — | `TruncationResult` object: `content, truncated, truncatedBy, totalLines, totalBytes, outputLines, outputBytes, lastLinePartial, firstLineExceedsLimit, maxLines, maxBytes` | `dict` | `serde_json::Value` / struct | JSON | **AUDITED**: closed key set; values are strings, bools, ints and `null` (`truncatedBy`). `content` repeats the shown tail **verbatim** | `details` equality on every truncation case; F6 key order is outside K1 (`spec/tools.md`), so compare as a key set |
| `details.fullOutputPath` | — | JS string, `os.tmpdir()/pi-bash-<16 hex>.log` | `str` | `String` (a filesystem path, `L12-D001`) | JSON string | **AUDITED, mapping**: the path is random either way. The contract certifies its *construction* (row "temp file" in §2), and canonical cases normalize it | the temp file holds the raw bytes (sha256) |
| `exitCode` | — | `number \| null` | `int \| None` (`ExitStatus.exit_code`) | `Option<i32>` | number in the status text | **AUDITED**: `null` → success (no status line). Windows Git Bash reports external SIGKILL as `2304` (characterization §11): a platform fact, not a binding choice | external kill per platform |
| session env values (Q1) | — | JS strings from the session | `str` | `String` | env var values | **AUDITED for representation**: Windows environment values are UTF-16, and a Rust `String` cannot hold a lone surrogate. Session ids, provider and model ids and reasoning levels are Minion-generated ASCII. `MINION_SESSION_FILE` is a path (`L12-D001` domain), but no persisted session file exists today (Q1 §5: absent) | **DEFERRED_WITH_REASON**: a lone-surrogate session-file path. Trigger: the first persisted session-file form (`spec/session.md`, "future persisted form") |
| inherited environment | — | `process.env` copy: a plain object, **case-sensitive** keys | `os.environ` (Windows: case-insensitive, upper-cased keys) | `std::env::vars_os` (Windows: case-preserving) | env block | **finding, part of `WP133-F1`**: strip semantics on Windows depend on key case. Pi deletes exact-case keys from a case-sensitive copy | `mInIoN_session_id` inherited on Windows |

### 1.1 Four value domains (F7)

| Domain | Pi repr | Python repr | Rust repr | Owning seam | Lossless across all? |
|---|---|---|---|---|---|
| INSTANCE | prepared `{command: string, timeout?: number}`; no `prepareArguments` | the same | the same | Layer 06 | **AUDITED**: `L0206-D002` / `L0506-D001` |
| SCHEMA | `Type.Object({command: String, timeout: Optional(Number)})`, ASCII names, no `additionalProperties` | dict schema | the same | Layer 05 | **AUDITED**: ASCII, no `const`, `enum` or `pattern` |
| RAW/WIRE | provider-decoded arguments | `L0206-D002` | `L0206-D002` | Layer 02 | **AUDITED** |
| SERIALIZED/PROJECTED | argv/stdin bytes to the child; the result text | see §1 rows | | Layer 12 / this WP | **AUDITED** with the two "rule needed" rows above |

**Canonical-case audit:** no case's schema holds a value outside the JSON scalar domain.

## 2. Lower-layer capability matrix

| Required semantic operation | Owning lower layer | Existing certified seam/API | Expresses exact Pi semantics? | Python repr sufficient? | Rust repr sufficient? | New additive extension required? | Non-additive reopen required? |
|---|---|---|---|---|---|---|---|
| spawn shell with argv (`[...args, command]`) or stdin transport (`-s`, command written then closed); stdin `ignore` for argv | 12 | `ctx.subprocess.spawn(argv, SpawnOptions{stdin: null\|piped})`; `WritableStream.write`/`close` | **YES**. Pi ignores stdin write errors (`on("error", ()=>{})`); Minion ignores the `write` result | yes | yes | no | no |
| kill the process tree on abort | 12 | spawn-time `signal` → tree kill (§6) | **YES**: Pi's `killProcessTree` = Layer 12's certified tree/group kill | yes | yes | no | no |
| kill the process tree on timeout | 12 | `Process.terminate()` (tree kill; `wait()` → `Ok`) | **YES**. Classification is bash's own, from its own flags (§4); it does not depend on `wait()`'s cause | yes | yes | no | no |
| wait for settlement: `close`, or exit plus both pipes ended, or exit plus 100 ms of no data (re-armed per chunk) | 12 | `wait()` (exit only) plus `read_chunk()` until EOF; the 100 ms grace is the caller's composition (`spec/execution.md` §5.6: "a caller wanting idle-grace … composes it itself") | **YES** as a composition. This is the same rule as `ctx.shell` §5.6 / Pi `waitForChildProcess`, `EXIT_STDIO_GRACE_MS = 100` | yes | yes | no | no |
| merged raw chunks of both pipes, in arrival order | 12 | two `ReadableStream`s read concurrently. Arrival order = the order the two reads complete | **YES, with a stated limit**: cross-pipe order is scheduler-dependent in Pi too. Certified: the order within each stream, and the merge order as observed by the reader. Canonical cases separate cross-stream writes in time | yes | yes | no | no |
| spawn failure (`error` event) | 12 | `spawn` → `Err(spawn_error)`; `read_chunk` → `Err(pipe_error)` | **PARTIAL**: Pi surfaces raw Node text (`spawn /bin/bash ENOENT`), and an unhandled pipe `error` crashes Pi. Under O1/C012 the raw part maps to a Minion-defined wrapper (contract §Error text) | yes | yes | no | no |
| `fsAccess(cwd, F_OK)`, following symlinks; any failure → "Working directory does not exist" | 12 | `ctx.fs.canonical_path(cwd)`: `Ok` ⇒ accessible; any `Err` ⇒ the message | **YES**. `canonical_path` follows symlinks and fails exactly where `access(F_OK)` path resolution fails. Not `ctx.fs.exists`, which is `lstat`-based and propagates non-`not_found` errors | yes | yes | no | no |
| `existsSync(candidate)` for shell discovery, following symlinks; any error ⇒ `false` | 12 | `ctx.fs.canonical_path(p)` is `Ok` | **YES**, as above. Negative control: an `exists`-based check passes a dangling-symlink `shell_path` | yes | yes | no | no |
| `where bash.exe` / `which bash` probe, 5000 ms, `status === 0 && stdout`, first line of `trim().split(/\r?\n/)` | 12 | `ctx.subprocess.spawn(["where","bash.exe"])` plus a composed 5 s timer → `terminate()`; decode stdout | **YES** as a composition. A `trim()` is the JS whitespace set (F2/F3: `\s` ≠ Python `str.strip()`; needs the shared JS-trim helper, as WP-13.2 already has) | yes | yes | no | no |
| `process.platform === "win32"` for the discovery branch | 12 | **none**: `ExecutionWorldIdentity` is opaque | **NO** | — | — | **YES: `WP133-F2`** | no |
| read world env values `ProgramFiles`, `ProgramFiles(x86)` (Node: case-insensitive lookup on Windows) | 12 | **none**: the provider's base environment is not readable | **NO** | — | — | **YES: `WP133-F1`** | no |
| spawn env = base env minus `MINION_*` (exact case) plus live values | 12 | `SpawnOptions{env, inherit_env}` can only **overlay** the base env; it cannot remove a key. With `inherit_env=false` the caller must supply the whole env, which it cannot read | **NO** | — | — | **YES: `WP133-F1`** | no |
| temp file for the full output: create, append raw bytes per chunk, close | 12 | `ctx.fs.create_temp_file(prefix, suffix)` (§3.7, private dir + unique name); `ctx.fs.append_file(path, bytes)` | **YES, mapping**: the path shape differs from Pi's `tmpdir()/pi-bash-<hex>.log` (random either way). Prefix `minion-bash-` follows Q1's namespace (`MINION_ARCHITECTURAL_MAPPING`). A creation or append failure has no Pi equivalent (Pi's unhandled stream `error` would crash the process): the contract defines it | yes | yes | no | no |
| live session state: session id, persisted session file, model `provider`/`id`, thinking level, read at spawn-context time (`ExtensionContext` getters, `runner.ts:690-712`; `agent-session.ts:2539-2543`) | 05/06 (tool execution context), 07 (`AgentInstance`), 08 (session) | **none**. A tool's `execute(tool_call_id, args, signal?, update?)` gets no per-call context. `execute_call` receives `ctx=instance.ctx` but does not pass it on. The values exist (`AgentInstance.model`/`thinking_level`, `SessionLog.session_id`) | **NO** | — | — | **YES: `WP133-F3`** | no |
| world compatibility: `fs` and `subprocess` address the same cwd and temp file | 12 | `validate([("fs", …), ("subprocess", …)])` (§7) at the tool's activation | **YES** (`MINION_EXTENSION`; §7 names `bash` as the motivating consumer) | yes | yes | no | no |

## 3. Cross-runtime hazard checklist

| Hazard | State | Evidence / reason |
|---|---|---|
| `JSON.parse` | NOT_APPLICABLE | no `prepareArguments`; arguments arrive decoded (`L0206-D002`) |
| `JSON.stringify` | NOT_APPLICABLE | `bash` serializes nothing itself; `details` projection is `L0506-D003`'s |
| `Number` conversion / numeric coercion | AUDITED | `timeout * 1000` in binary64; `> 2147483647`; `Number.isFinite`; `<= 0` (`-0 <= 0` is true → rejected) |
| `Math` semantics | NOT_APPLICABLE | no `Math` call on an observable path (`Math.max` sets `maxRollingBytes`, a constant) |
| negative zero | AUDITED | `timeout: -0` → `Invalid timeout: must be a finite number of seconds` |
| non-finite values | AUDITED | ±Infinity and NaN → the same text (`L0506-D001` admits them at runtime) |
| `String.length` / UTF-16 | AUDITED | lengths are UTF-8 bytes from `Buffer.byteLength`. The one UTF-16-sensitive path is argv projection (§1) |
| `RegExp` | AUDITED | `isLegacyWslBashPath` (ASCII, after `toLowerCase()`, F3: ASCII-only effect on the matched set); `split(/\r?\n/)` |
| Unicode / ICU version | AUDITED | `toLowerCase()` on a path: a non-ASCII character can lower-case differently by Unicode version, but cannot affect an ASCII-only pattern match. No normalization |
| Array ordering | NOT_APPLICABLE | none |
| Object property ordering | AUDITED | env object key order does not reach the child observably (the OS env block); `details` key order is outside K1 (`spec/tools.md`) |
| Promise scheduling | AUDITED | §4: settlement, classification and output acceptance order |
| `AbortSignal` | AUDITED | the pre-spawn check after timeout validation; an abort after spawn → tree kill; classification after settlement checks `signal.aborted` **first** (opposite to `ctx.shell` §5.4's timeout-first) |
| `setTimeout` / timers | AUDITED | the timeout timer (ms, ≤ 2^31−1); the 100 ms idle grace; `where`/`which` 5000 ms. Pi's 100 ms update throttle is not certified (Q2) |
| Node/libuv error mapping | AUDITED | spawn and pipe errors → contract wrapper (§2); `where`/`which` failures are silent (scoping v4) |
| filesystem access semantics | AUDITED | `access`/`existsSync` follow symlinks → `canonical_path`, not `exists` (§2) |
| platform-specific path handling | AUDITED + finding | WSL matcher normalizes `/` → `\`; Windows Git Bash candidates are built with `\\` from env values (`WP133-F1`/`F2`) |
| external package / runtime versions | AUDITED | Node 22.15.1; no npm package on the `bash` path. Git Bash and bash versions are environment: the probe records them |

## 4. Concurrency / order matrix

| Operation | Start | Registration point | Lock acquisition | Await points | Abort checkpoints | Failure points | Settle point | Cleanup / release | Observable completion ordering |
|---|---|---|---|---|---|---|---|---|---|
| `bash.execute` | after Layer 06 preflight (a pre-aborted call never reaches `execute`) | none (no mutation queue: Q5, Pi's own behavior) | none | spawn-context build (`F3` read; `F1` env read); then the `exec` steps | (a) after timeout validation, before shell discovery; (b) abort after spawn → tree kill | 1 invalid timeout; 2 aborted; 3 shell discovery (`Custom shell path not found` / Windows "No bash shell found"); 4 cwd; 5 spawn | settlement (§2) | timer cleared; listener removed; temp file closed **before** the result is returned | result text is fixed by the **final** snapshot after `finish()` flushes the decoder |
| output intake | first chunk | — | — | each `read_chunk` | — | `pipe_error` | stops at settlement (`acceptingOutput = false`); late chunks are dropped | — | per-stream order kept; temp-file bytes are exactly the accepted chunks, in intake order |
| classification | settlement | — | — | — | — | — | — | — | `signal.aborted` → `Command aborted`; else timed out → `Command timed out after N seconds`; else exit code |

| Ordering guarantee | Realistic wrong implementation | Witness that kills it |
|---|---|---|
| invalid timeout is reported before an abort | abort check first (`ctx.shell` §5.4 order) | pre-spawn abort plus `timeout: 0` → `Invalid timeout…` (needs a tool-level abort after preflight) |
| abort is checked before shell discovery and cwd | discovery first | aborted after preflight plus a missing `shell_path` → `Command aborted` |
| shell discovery before the cwd check | cwd first (`ctx.subprocess` natural order) | missing `shell_path` plus missing cwd → `Custom shell path not found: …` |
| aborted wins over timed-out at classification | `ctx.shell`'s timeout-first precedence | timeout fires, then abort arrives during the kill/settle window → `Command aborted` |
| an abort during the idle grace after a clean exit still classifies as aborted | classify from `wait()`'s cause (`NONE` → success) | `printf a` exits; abort within the 100 ms grace → `a\n\nCommand aborted` |
| settlement waits for the idle grace, not `wait()` alone | return at process exit | a backgrounded child writes 50 ms after the parent exits → the output is included |
| a detached descendant holding the pipes does not hang the call | wait for EOF | `(sleep 5 &); printf x` → settles in about 100 ms with `x` |
| one decoder across both streams | decode per stream (`ctx.shell`'s shape) | a character interrupted by a stderr chunk → `�x��` |
| the decoder is never reset between chunks | a fresh decoder per chunk | a character split across two writes → `€`, not `��` |
| the temp file holds raw bytes | write decoded text | invalid-UTF-8 output over 51200 bytes → file sha256 equals the raw bytes |
| truncated is computed from the totals, not the tail | `truncateTail` alone | 369000-byte case: the rolling trim plus totals → `Showing lines 7753-9000 of 9000` |
| the status line follows the formatted output, including the truncation notice | status before the notice | exit 3 with more than 2000 lines → notice, then `\n\nCommand exited with code 3` |

## 5. Neighborhood expansion record

| Family | Members probed | Pi observation source | New rows / findings |
|---|---|---|---|
| F1 JS Number | `-0`, ±Infinity, NaN, `2147483.647`/`.648`, fractional, `String(n)` and `toFixed(1)` | `bash_probe.mjs` (characterization §11); `resolveTimeoutMs` | rows "timeout", "status text", "formatSize" |
| F2 JS String/UTF-16 | lone surrogate in `command`; UTF-16 argv vs UTF-8 stdin | source audit; probe extension in the contract corpus | row "argv/stdin projection" |
| F3 Unicode/ICU | `toLowerCase` in the WSL matcher; JS `trim()` whitespace set | source audit | §3 rows; shared JS-trim helper |
| F4 Async/order | §4 in full | probe (abort, timeout, the update sequence) | §4 controls |
| F5 Error/coercion projection | spawn and pipe errors; `err.message` passthrough; `String(timeout)` | source audit | §2 "spawn failure" row |
| F6 ECMAScript object order | env object; `details` | source audit | outside K1 (`spec/tools.md`) |
| F7 Schema runtime domain | the four domains | §1.1 | none |

## 6. Verdict

```text
FEASIBILITY
    BLOCKED   open findings:
      WP133-F1  (LOWER_LAYER_CAPABILITY_GAP, Layer 12)  world environment: read values; spawn
                with inherited keys removed. Owner: interface shape (#75 items 5/6).
      WP133-F2  (LOWER_LAYER_CAPABILITY_GAP, Layer 12)  world platform for shell discovery.
                Owner: interface shape (#75 items 5/6).
      WP133-F3  (LOWER_LAYER_CAPABILITY_GAP, Layers 05/06 + 07/08)  per-call live session state
                for a tool's execute. Owner: interface shape (#75 item 5).
```

Every other row is AUDITED, NOT_APPLICABLE or DEFERRED_WITH_REASON. The two "rule needed" rows (argv/stdin projection, WHATWG streaming decode) and the temp-file failure rule are the contract's to state; they are not lower-layer gaps.
