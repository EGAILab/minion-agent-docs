# Layer 13 — Built-in Tools scoping

Mode: scoping / read-only audit. **IMPLEMENTATION AUTHORIZED: NO.**

## Starting state

```text
code main:    92aa4be168dc82111832467922089206e858a9c4
docs master:  ec36ed92a9a57f5fc8db4f76103a2d202cb82cbc
pinned Pi:    b7bb00b936dbe21b8e160b3e89efdec361846699
```

All three verified remote-reachable before this pass began. `ref-repos/pi` (the pinned-Pi
checkout used for this audit) is already checked out at `b7bb00b936dbe21b8e160b3e89efdec361846699`
-- confirmed via `git log -1 --format=%H` matching the pin exactly, not assumed.

## Layer boundary

**Layer 12 owns** (certified, `EXEC-001`..`EXEC-006`, `minion-agent-python/src/minion_agent/execution/`):
`FileSystem`/`LocalFileSystem` (`filesystem.py`), `FsTarget` (`filesystem.py:559`, opaque
`target_key: str` field at `:565`), `FileSystem.process_path`/`LocalFileSystem.process_path`
(`filesystem.py:553`, `:814`; `target_key = canonical_path(path)` on success, falls back to a
lexical absolute path), `Shell`/`LocalShell`/`ShellResult` (`shell.py`), `Subprocess`/
`LocalSubprocess`/`Process`/`SpawnOptions`/`StdioMode`/`ExitStatus`/`ReadableStream`/
`WritableStream` (`subprocess.py`), `ExecutionWorldIdentity`/`compatible`/`validate`/
`IncompatiblePair` (`world.py`), `FsErrorCode`/`ShellErrorCode`/`SubprocessErrorCode`
(`errors.py`), and `resolve_local_path`/`_file_url_to_path` (the R002-certified Ada-2.9.2-backed
`file://` URL conversion).

**Layer 13 owns** (this scoping pass): the built-in tool surface itself -- `bash`, `read`, `write`,
`edit`, `find` (glob-pattern file search; Pi's own name for what the prior hypothesis called
"glob"), `grep`, and `ls` -- their argument schemas, path-argument handling, output/truncation
shapes, error classification as observed at the tool boundary, and same-target mutation
serialization for `write`/`edit`.

**Layer 14 (not scoped here)**: anything past the built-in-tool set itself -- e.g. the tool
registry's own dynamic/extension-tool machinery already exists in both languages
(`minion-agent-python/src/minion_agent/tools/` and `minion-agent-rust/crates/minion-agent/src/
tools/`: `registry.py`/`registry.rs`, `execution.py`/`execution.rs`, `definition.py`/
`definition.rs`, `batch.py`, `plugin.py`, `events.py`, `decisions.py`, `result.py`) and is
explicitly out of scope for Layer 13, which only fills in the concrete built-in tools that plug
into that existing framework.

**Confirmed consumption, not redefinition, of one Layer 12 surface already:** Pi's own path
normalization (`packages/coding-agent/src/utils/paths.ts:95-97`, `normalizePath`) resolves a
`file://`-prefixed tool `path` argument by calling Node's own `fileURLToPath` directly -- the
exact same concrete conversion Layer 12/R002 already built a certified, oracle-verified seam for
(`_file_url_to_path`, Ada 2.9.2-backed). This is strong, source-confirmed evidence that Layer 13's
`path`-argument resolution for `read`/`write`/`edit`/`find`/`grep`/`ls` should route through
Layer 12's already-certified `ctx.fs`/`resolve_local_path` seam for the `file://` case rather than
reimplementing any part of that conversion. No defect or missing requirement was found in Layer 12
during this pass; nothing here proposes reopening it.

## Pi audit (pinned `b7bb00b936dbe21b8e160b3e89efdec361846699`)

Two parallel tool layers exist in the pinned Pi source:

- `packages/agent/src/harness/tools/` -- a smaller SDK-level harness exposing only
  `bash`/`edit`/`read`/`write` (no `find`/`grep`/`ls`, no exported mutation queue).
- `packages/coding-agent/src/core/tools/` -- the full, product-level built-in tool set:
  `bash.ts`, `read.ts`, `write.ts`, `edit.ts` (+ `edit-diff.ts`), `find.ts`, `grep.ts`, `ls.ts`,
  `file-mutation-queue.ts`, `truncate.ts`, `path-utils.ts`, `output-accumulator.ts`.
  `index.ts`'s `allToolNames` is exactly `{read, bash, edit, write, grep, find, ls}`.

**This scoping pass treats `packages/coding-agent/src/core/tools/` as the audit target** -- it is
the complete, coherent, currently-shipping built-in tool inventory, and matches the scale implied
by the prior WP-13.1/13.2 hypothesis. The narrower `packages/agent/src/harness/tools/` variant is
noted as a lower-level SDK surface but is not separately scoped; if a future pass needs it, treat
it as a subset, not a divergent contract.

Symbols/files actually read for this audit (exact source, not inferred from names): `bash.ts`
(511 lines, full), `read.ts` (358 lines, full), `write.ts` (275 lines, full), `edit.ts` (461
lines, full), `edit-diff.ts` (556 lines, full), `find.ts` (380 lines, full), `grep.ts` (schema +
delegation, partial), `ls.ts` (schema + operations, partial), `file-mutation-queue.ts` (61 lines,
full), `truncate.ts` (276 lines, full), `path-utils.ts` (118 lines, full),
`utils/paths.ts:1-140` (partial), `utils/tools-manager.ts:1-60,330-368` (partial, fd/rg
acquisition).

## Current Minion audit

**Python** (`minion-agent-python/src/minion_agent/tools/`): `__init__.py`, `batch.py`,
`decisions.py`, `definition.py`, `events.py`, `execute.py`, `plugin.py`, `registry.py`,
`result.py`, with matching tests under `tests/tools/`. This is exclusively the generic
tool-definition/registration/execution/batching framework. No file named `bash`/`read`/`write`/
`edit`/`find`/`glob`/`grep`/`ls` exists, and a case-insensitive grep for those names plus
`built_in_tool`/`BuiltinTool` across `src/minion_agent/tools/*.py` returned nothing.

**Rust** (`minion-agent-rust/crates/minion-agent/src/tools/`): `definition.rs`, `execution.rs`,
`registry.rs`, `mod.rs`, with matching integration/conformance tests. Same shape as Python: the
generic framework only, confirmed via `struct`/`fn` grep (`ToolDefinition`, `ToolExecutionRequest`,
`ToolRegistry`, lifecycle/hook types) -- no built-in-tool-specific code found.

**Conclusion:** clean slate. No pre-existing code, in either language, anticipates or
pre-certifies any Layer 13 built-in tool's behavior. Nothing to preserve, realign, or
mislabel as already-adopted.

## Built-in tool inventory

### `bash`

- Input: `command: string`, `timeout?: number` (seconds; **no default timeout**, unlike every
  other tool here). `MAX_TIMEOUT_MS = 2_147_483_647` (~24.8 days); non-finite/`<=0` timeout is a
  pre-spawn validation error.
- Working directory must exist (`F_OK` check) before spawning, or a distinct pre-spawn error is
  raised.
- Shell invocation is config-driven (`getShellConfig`): either argv-transport (command appended
  to the shell's argv) or stdin-transport (command written to the spawned shell's stdin then the
  stream is closed) -- not investigated further in this pass; `shell.ts`'s exact selection logic
  is an open item for the implementation-scoping pass, not this one.
- Process tree handling: `detached: process.platform !== "win32"` at spawn (POSIX only, enabling
  process-group kill); pid tracked in a global registry
  (`trackDetachedChildPid`/`untrackDetachedChildPid`) for cleanup.
- **Timeout and abort both kill via `killProcessTree(pid)`** and exit-wait via
  `waitForChildProcess(child)`, explicitly commented as avoiding a hang "on inherited stdio
  handles held by detached descendants." This is the exact problem class Layer 12/R004-B already
  solved (target-exit-only settlement, not blocked on an unbounded kill helper). Strong evidence
  `bash`'s process lifecycle should consume `ctx.subprocess` directly rather than re-deriving its
  own kill/wait logic.
- `exitCode: number | null` (`null` = signaled/killed); non-zero non-null exit is a tool error
  carrying the accumulated output; a `null` exit is only reached via the more specific
  abort/timeout error paths (pattern-matched on thrown error message text: `"aborted"` /
  `"timeout:<seconds>"`).
- Output: streamed via an `OutputAccumulator`, truncated from the **tail** (last N lines/bytes,
  opposite direction from `read`), using the same `DEFAULT_MAX_LINES`/`DEFAULT_MAX_BYTES`
  constants as every other tool. If truncated, full output is persisted to a temp file and its
  path surfaced in the result text.
- Live throttled (100 ms) partial-output updates exist for TUI streaming; not a core semantic
  requirement -- classify as an optional UX feature, not a parity obligation.
- Environment: starts from a shell-env snapshot, deletes `PI_SESSION_ID`/`PI_SESSION_FILE`/
  `PI_PROVIDER`/`PI_MODEL`/`PI_REASONING_LEVEL`, then re-adds them (`exposeSessionEnvironment`,
  default true) from the current session/model/thinking-level. The `PI_*` names themselves are
  Pi-branded and not literal parity material -- Minion would use its own namespace; classify as
  `MINION_ARCHITECTURAL_MAPPING`.
- A `commandPrefix` option and an extension `spawnHook` exist (command/cwd/env rewrite point
  before spawn) -- extension surface, not core tool contract.
- Semantic authority: `PI_SOURCE_ALGORITHM` for the shell-spawn/kill/timeout logic in
  `bash.ts`/`shell.ts` (Pi's own TypeScript, not delegated); but its underlying kill/wait
  mechanics are the same problem Layer 12 already certified as a Minion shared contract, so the
  practical authority for that portion is `MINION_SHARED_CONTRACT` (`ctx.subprocess`), not a
  fresh Pi-source port.

### `read`

- Input: `path: string`, `offset?: number` (1-indexed line), `limit?: number` (max lines).
- Path resolution: `resolveReadPathAsync` -- normal `resolveToCwd` first (see Path resolution,
  below), then, only if the resolved path does not exist, four macOS-specific fallback probes in
  order: AM/PM narrow-no-break-space substitution, NFD Unicode normalization, straight-to-curly
  apostrophe substitution, and NFD+curly combined -- each existence-checked before falling
  through to the next. This is a macOS-screenshot-filename convenience heuristic specific to
  `read` (not `write`/`edit`, which use plain `resolveToCwd`). Classify as `PLATFORM_BEHAVIOR`
  scoped to macOS; candidate for explicit adopt/drop disposition rather than blind port --
  Minion's own execution-world model may make this moot (a remote/virtual `FileSystem` provider
  would not have macOS's filename-encoding quirks at all).
- Separate `access()` (readability) check before the actual read -- a distinct error path from a
  read failure.
- Image support: MIME-sniffed, returned as an image content block, auto-resized (default on) to
  2000x2000 max; non-vision models get a text note instead, image content omitted.
- Text: `content.split("\n")`; out-of-bounds `offset` is an explicit, distinguishable error citing
  total line count. Truncation via `truncateHead` (see Truncation, below) -- always applied
  **after** any user `limit`, so a user `limit` cannot bypass the byte/line ceiling. Truncated
  output tells the model the exact `offset` to resume at; a single line exceeding the byte limit
  alone gets a bash-fallback hint (`sed -n '<n>p' <path> | head -c <bytes>`) instead of content.
- Cancellation: genuine `AbortSignal` support -- checked before starting and via an abort-event
  listener that rejects immediately.
- Does **not** participate in the mutation queue (confirmed by grep: only `write.ts`/`edit.ts`
  import `withFileMutationQueue`).
- Semantic authority: `PI_SOURCE_ALGORITHM` (native Node fs + Pi's own truncation/offset logic);
  `PLATFORM_BEHAVIOR` for the macOS fallback probes specifically.

### `write`

- Input: `path: string`, `content: string`. Creates parent directories recursively
  (`mkdir(dir, {recursive: true})`) before writing. Full overwrite, no read-before-write
  requirement, no diff shown to the model.
- Participates in the mutation queue, keyed on the `resolveToCwd`-resolved absolute path (the
  queue itself further resolves that key via `realpath`, see Mutation queue, below).
- **Cancellation is deliberately NOT abort-listener-driven while the queue lock is held** -- a
  code comment explains this explicitly: releasing the queue lock mid-flight (via an abort
  listener firing during an in-flight `fs.writeFile`) could let a later queued operation start
  before the aborted operation's own filesystem write has actually settled. Instead, `signal
  .aborted` is checked after each `await` (`throwIfAborted()`), so the lock is held until the
  current fs operation itself finishes, then the abort is surfaced. This is a genuinely important,
  non-obvious cancellation-vs-serialization interaction that a correct port must preserve exactly
  -- and it directly answers scoping question 10 for `write`/`edit` specifically (their
  cancellation semantics differ from `read`'s on purpose).
- Success message reports `content.length` **bytes** -- but `.length` is JS `String.length`
  (UTF-16 code units), not `Buffer.byteLength(content, "utf-8")` as used everywhere else in this
  codebase (`truncate.ts`, `read.ts`'s size formatting). For any content containing non-ASCII
  (specifically non-BMP or multi-byte UTF-8) characters, the reported byte count is source-verified
  wrong relative to what was actually written. This is a genuine Pi-source quirk, not a
  transcription error on this pass's part -- record it explicitly rather than silently
  "correcting" it if literal-message parity is ever required, and flag it as a candidate
  `CONTRACT_ASSURANCE_DEFECT`-adjacent note for the eventual contract draft (Minion is not
  obligated to reproduce an off-by-encoding user-facing string; this is a disposition point, not
  an instruction to copy the bug).
- Semantic authority: `PI_SOURCE_ALGORITHM`, `MINION_SHARED_CONTRACT` for the mutation-queue
  participation (Layer 12's kill/settlement lesson applies analogously to lock-vs-cancellation
  ordering here, even though the mechanism is different).

### `edit`

- Input: `path: string`, `edits: {oldText: string, newText: string}[]` (plus tolerant input
  coercion: a single `{oldText, newText}` object, a JSON-string-encoded array, or legacy top-level
  `oldText`/`newText` are all normalized into the `edits[]` shape before validation --
  `prepareEditArguments`; classify this coercion layer as `MINION_EXTENSION`-optional, a
  model-compatibility shim rather than core contract).
- File must already exist (distinct `access()`-based error if not).
- **Multi-edit matching is all-at-once against the original content**, not incremental: every
  `edits[].oldText` is located in the same original (BOM-stripped, LF-normalized) content before
  any replacement is applied.
- Exact match is tried first; only if that fails does fuzzy matching activate
  (`normalizeForFuzzyMatch`: Unicode NFKC, per-line trailing-whitespace strip, smart-quote →
  ASCII, Unicode dash variants → ASCII hyphen, Unicode space variants → ASCII space).
  **Critically: fuzzy mode, once triggered by any single edit in the call, is applied to *all*
  edits in that call** -- every edit's match position is then computed in fuzzy-normalized space,
  not just the one that needed it.
- Uniqueness (exactly one occurrence) and non-overlap (sorted match ranges must not intersect)
  are both enforced, each with a distinguishable, edit-index-citing error message; a would-be
  no-op (`baseContent === newContent` after all replacements) is also rejected as an error.
- **When fuzzy matching was used, only the touched line ranges are rewritten from the
  fuzzy-normalized text; every untouched line is copied back verbatim from the original,
  byte-for-byte** (`applyReplacementsPreservingUnchangedLines`) -- fuzzy normalization never
  silently rewrites whitespace/Unicode elsewhere in the file. This is the single most
  implementation-subtle piece of Pi-source algorithm found in this audit and must be ported as an
  algorithm, not approximated.
- BOM is stripped before matching and restored (prepended) on write; original line-ending style
  (`\r\n` vs `\n`, detected from whichever appears first in the file) is detected before matching
  and restored on write, after all matching/replacement happens in LF-normalized space.
- Same mutation-queue participation and same deliberate check-after-await cancellation strategy
  as `write` (identical code shape; same rationale).
- Semantic authority: `PI_SOURCE_ALGORITHM` -- this is exactly the kind of "large delegated
  standard" the R002 lesson (do not approximate witness-by-witness) applies to, except here the
  algorithm is Pi's own TypeScript (fully readable, not a third-party binary), so the correct
  strategy is a faithful direct port plus a differential test corpus built from this exact
  algorithm, not guesswork from tool-call examples.

### `find` (the "glob" tool)

- Input: `pattern: string` (glob, e.g. `*.ts`, `**/*.json`, `src/**/*.spec.ts`), `path?: string`
  (search root, default cwd), `limit?: number` (default **1000**).
- **Delegates all glob matching to an external `fd` binary** (`sharkdp/fd`), not a
  JS/Pi-reimplemented glob engine: `fd --glob --color=never --hidden [--no-require-git]
  --max-results <N> [--full-path] -- <pattern> <searchPath>`.
- `--no-require-git` is added only when the search root is **not** inside a git repository
  (walked up via repeated `.git`-existence checks); inside a repo, `fd`'s default git-aware
  `.gitignore` behavior applies, which stops parent `.gitignore` rules at nested-repo boundaries
  -- the source comments this as a deliberate fix for a specific Pi issue (`earendil-works/pi#5960`),
  not incidental behavior.
- Pattern containing `/` switches `fd` to `--full-path` mode and, unless the pattern already
  starts with `/`, `**/`, or is exactly `**`, prepends `**/` to it (full-path mode otherwise
  anchors at the search root); on Windows, `/` inside such a pattern is rewritten to the character
  class `[/\\]` so it matches either separator.
- Output is truncated **by bytes only** (`truncateHead` called with `maxLines:
  Number.MAX_SAFE_INTEGER`) -- line-count truncation is effectively disabled for `find`, unlike
  every other tool. Results are relativized to the search root and posix-separator-normalized
  (`relativizeFindResultPath`), preserving a trailing separator for directory matches.
- Cancellation: `AbortSignal` supported, kills the `fd` child via plain `child.kill()` (not the
  fuller `killProcessTree` used by `bash`) -- a real, if likely low-risk (short-lived process),
  asymmetry worth carrying forward as an explicit disposition rather than an oversight.
- **`fd`'s own version is not pinned.** `ensureTool("fd")` first looks for a system-installed
  binary (`fd` or `fdfind` on `PATH`); only if none is found does it download the **latest**
  GitHub release of `sharkdp/fd` for the current platform/arch. Pi itself therefore has no single
  fixed version of the engine defining its own glob semantics -- it is whatever happens to be on
  the user's `PATH`, or whatever was "latest" whenever `fd` was first downloaded on that machine.
  See High-risk surfaces, below -- this is a materially different situation from R002's exact,
  pinnable Ada 2.9.2 authority.
- Semantic authority: `DELEGATED_LIBRARY_BEHAVIOR`, specifically an **unpinned/floating** one.

### `grep`

- Input: `pattern: string` (regex or literal, `literal?: boolean` flag), `path?: string`,
  `glob?: string` (file filter), `ignoreCase?: boolean`, `context?: number` (lines before/after),
  `limit?: number` (default **100** matches).
- **Delegates to an external `rg` (ripgrep) binary** the same way `find` delegates to `fd`,
  including the identical unpinned-version acquisition path (`ensureTool("rg")`: system `PATH`
  first, else latest GitHub release of `BurntSushi/ripgrep`). Invocation observed:
  `rg --json --line-number --color=never --hidden [--glob <glob>] ...`, parsed from `rg`'s
  structured `--json` event stream rather than scraped from plain text.
  Full argument surface (case-insensitivity flag placement, literal-vs-regex flag, context-line
  flag, and match-line length capping via `GREP_MAX_LINE_LENGTH = 500` chars per line with a
  `... [truncated]` suffix) was not fully read line-by-line in this pass and should be completed
  in the implementation-scoping step, not assumed from the schema alone.
- Semantic authority: `DELEGATED_LIBRARY_BEHAVIOR`, unpinned/floating -- same classification and
  same open risk as `find`.

### `ls`

- Input: `path?: string` (default cwd), `limit?: number` (default **500** entries).
- Native `fs.readdir`/`fs.stat` -- no external binary delegation, no glob/regex matching.
- Byte-truncated output (same `truncateHead`/`DEFAULT_MAX_BYTES` family); entry-count limit
  separately reported when hit.
- Not read in full detail in this pass (schema + `LsOperations` shape only); directory-entry
  formatting (what per-entry metadata is shown, symlink handling, hidden-file inclusion) is an
  open item for implementation scoping.
- Semantic authority: `PI_SOURCE_ALGORITHM` (native, no delegation).

## Mutation queue characterization

`file-mutation-queue.ts`, fully read (61 lines):

- **Key**: `realpath(resolve(filePath))`; if `realpath` fails with `ENOENT`/`ENOTDIR` (target
  does not exist yet -- the common `write`-creates-a-new-file case), falls back to the plain
  `resolve(filePath)` string. The key is therefore the *canonical, symlink-resolved* absolute
  path whenever the target already exists, and a lexical absolute path only for not-yet-existing
  targets. This maps directly onto Layer 12's own `FsTarget.target_key` derivation
  (`canonical_path(path)` on success, lexical-absolute fallback otherwise, `filesystem.py:799-811`)
  -- the two are the same idea at different layers, strong evidence Layer 13's queue key should
  literally *be* `FsTarget.target_key`, not a second, independently-derived key.
- **Ordering**: FIFO per key. A separate, single global `registrationQueue` promise chain
  serializes only the (async, because it does a `realpath` I/O call) *registration* step, so that
  when two operations for the same key are issued concurrently, their relative order in the
  per-key FIFO chain is determined by call order into `withFileMutationQueue`, not by which
  `realpath` call happens to resolve first. Without this, two near-simultaneous writes to the same
  file could serialize in a nondeterministic order.
- **Participation**: only `write` and `edit` (confirmed by grep: no other tool file imports
  `withFileMutationQueue`). `read` explicitly does not participate. `bash` does not participate --
  it has no awareness of the mutation queue at all, even if the command it runs mutates a file
  that `write`/`edit` also targets in the same session (an intentional, or at least undocumented,
  gap -- not investigated further; record as an open question, not a finding).
- **Different keys run fully concurrently** -- no cross-key blocking of any kind.
- **Acquire/release**: a caller "joins" its key's chain by awaiting the current tail of that
  chain; release happens in a `finally` block after the wrapped callback settles (success or
  throw), so a callback failure does not deadlock the queue for that key. After release, if no
  other caller queued behind this one, the map entry for that key is deleted (a memory-cleanup
  optimization with no other observable effect).
- **Cancellation**: the queue itself has no abort-awareness; `write`/`edit` build their own
  check-after-each-`await` cancellation on top of it, deliberately not tied to the queue's
  acquire/release boundary (see `write`/`edit` above).

## Path resolution (cross-tool)

All of `read`/`write`/`edit`/`find`/`grep`/`ls` funnel their `path` argument through
`resolveToCwd` (`path-utils.ts` → `utils/paths.ts:resolvePath`/`normalizePath`), which, in order:
optionally trims, normalizes Unicode space variants to ASCII space, strips a leading `@` (a
CLI `@file` convention carried through uniformly to every tool, not just a CLI-only concern),
applies Windows Git-Bash/MSYS/Cygwin/WSL drive-path normalization (`/c/...`, `/mnt/c/...`,
`/cygdrive/c/...` → `C:\...`) on `win32` only, expands a leading `~`/`~/`/`~\` against
`os.homedir()`, and -- the Layer 12 connection noted above -- converts a `file://`-prefixed value
via Node's own `fileURLToPath`. Relative results are resolved against `cwd` via Node's lexical
`path.resolve` (no symlink following at this stage; symlink/canonicalization only happens later,
inside the mutation queue's own key derivation for `write`/`edit`). `read` additionally applies
four macOS-filename fallback probes only when the initially resolved path does not exist (see
`read`, above).

## Truncation (cross-tool constants, from `truncate.ts`, fully read)

```text
DEFAULT_MAX_LINES     = 2000
DEFAULT_MAX_BYTES     = 51200   (50 * 1024)
GREP_MAX_LINE_LENGTH  = 500     (chars per grep match line, with "... [truncated]" suffix)
```

Two independent limits, whichever is hit first wins, both computed with UTF-8-aware
`Buffer.byteLength` (except `write`'s own success-message byte count, see `write` above, which
uses UTF-16 `.length` instead -- an isolated inconsistency, not the general rule). `read` and `ls`
truncate from the **head**; `bash` and (byte-only) `find` truncate from the **tail**/by-bytes-only
respectively; `bash`'s tail truncation is the only place a partial (non-line-aligned) final
segment can appear in output (`lastLinePartial`), handled via UTF-8-boundary-safe byte slicing
(`truncateStringToBytesFromEnd`).

## Parity classification

```text
DIRECT_PI_PARITY
    - bash timeout/abort → kill-then-wait semantics (mirrors Layer 12 R004-B exactly)
    - truncation head/tail selection and the two numeric limits (2000 lines / 50KB)
    - edit: exact-then-fuzzy matching algorithm, uniqueness/overlap/no-op rejection,
      BOM/line-ending handling, unchanged-line preservation under fuzzy mode
    - write/edit: mutation-queue key derivation and FIFO-per-key ordering
    - find/grep: argument shape (pattern/path/glob/limit/context/ignoreCase/literal) --
      but NOT necessarily the underlying match semantics, see MINION_EXTENSION below

MINION_ARCHITECTURAL_MAPPING
    - mutation-queue key should be literally Layer 12's FsTarget.target_key, not a
      second independently-derived key -- same idea, different layer, deliberate reuse
    - file:// path-argument handling should route through Layer 12's certified
      resolve_local_path/_file_url_to_path seam
    - bash environment-variable exposure (PI_* names are Pi-branded; Minion needs its
      own namespace even though the underlying mechanism -- expose session metadata to
      the spawned shell -- is direct parity)
    - write/edit cancellation-vs-queue-lock ordering (check-after-await, not
      abort-listener-during-lock) is a Minion-relevant correctness property to
      preserve, expressed through whatever cancellation primitive ctx.fs/ctx.subprocess
      already exposes, not necessarily Pi's exact AbortSignal-check-loop shape

MINION_EXTENSION (candidate; owner disposition needed, see Open questions)
    - find/grep's exact match engine: Minion is not obligated to shell out to fd/rg
      specifically (Pi's own choice is itself unpinned/floating, see High-risk surfaces),
      so "parity" here can only mean equivalent observable glob/regex semantics for a
      Minion-chosen, explicitly pinned engine -- not byte-identical fd/rg output
    - read's macOS filename-fallback heuristics (AM/PM, NFD, curly-quote probing) --
      platform-specific UX convenience, not obviously required for a faithful contract
    - bash/edit's tolerant input-coercion shims (edits-as-JSON-string, single-edit-object,
      legacy oldText/newText) -- model-compatibility accommodations, not semantic contract
    - live throttled partial-output streaming (bash) -- TUI/UX feature
```

## Semantic authority (per significant surface)

```text
PI_SOURCE_ALGORITHM        edit's fuzzy-match/apply/preserve-unchanged-lines algorithm;
                            read/bash/ls truncation and offset/limit logic; path
                            resolution (paths.ts); mutation-queue FIFO-per-key logic
DELEGATED_LIBRARY_BEHAVIOR find -> fd (sharkdp/fd), grep -> rg (BurntSushi/ripgrep) --
                            BOTH UNPINNED at the Pi layer (see High-risk surfaces)
PLATFORM_BEHAVIOR          read's macOS filename-fallback probes; Windows Git-Bash/
                            MSYS/Cygwin/WSL path normalization; bash's POSIX-vs-Windows
                            process-group/detached-spawn handling
MINION_SHARED_CONTRACT     bash's kill/wait lifecycle (== Layer 12 R004-A/R004-B);
                            file:// path conversion (== Layer 12 R002); mutation-queue
                            key derivation (== Layer 12 FsTarget.target_key)
```

## Proposed requirements (draft namespace: `TOOL-###`)

Provisional only -- final IDs, exact wording, and completeness are implementation-scoping work,
not this pass's. Listed to show the shape and dependencies expected, not to freeze numbering.

```text
TOOL-001  bash: argument schema, timeout semantics, no-default-timeout behavior
          Pi source: bash.ts               DIRECT_PI_PARITY (schema) / MINION_SHARED_CONTRACT (kill/wait)
          WP: bash                         depends on: Layer 12 ctx.subprocess

TOOL-002  bash: output truncation (tail, byte+line, temp-file-on-truncation)
          Pi source: bash.ts, truncate.ts  DIRECT_PI_PARITY
          WP: bash                         depends on: TOOL-001

TOOL-003  read: argument schema, offset/limit, truncation (head)
          Pi source: read.ts, truncate.ts  DIRECT_PI_PARITY
          WP: read/query tools             depends on: (none)

TOOL-004  read: file:// / path-argument resolution
          Pi source: path-utils.ts         MINION_ARCHITECTURAL_MAPPING
          WP: read/query tools             depends on: Layer 12 resolve_local_path

TOOL-005  read: macOS filename-fallback heuristics [owner disposition: adopt / drop]
          Pi source: path-utils.ts         PLATFORM_BEHAVIOR / MINION_EXTENSION
          WP: read/query tools             depends on: TOOL-004

TOOL-006  write: schema, overwrite semantics, parent-dir auto-creation
          Pi source: write.ts              DIRECT_PI_PARITY
          WP: mutation tools                depends on: TOOL-010

TOOL-007  edit: multi-edit exact-match algorithm, uniqueness/overlap/no-op rejection
          Pi source: edit-diff.ts          DIRECT_PI_PARITY
          WP: mutation tools                depends on: TOOL-010

TOOL-008  edit: fuzzy-match algorithm and unchanged-line preservation
          Pi source: edit-diff.ts          DIRECT_PI_PARITY
          WP: mutation tools                depends on: TOOL-007

TOOL-009  edit: BOM and line-ending detection/restoration
          Pi source: edit-diff.ts          DIRECT_PI_PARITY
          WP: mutation tools                depends on: TOOL-007

TOOL-010  write/edit: mutation-queue key derivation and FIFO-per-key serialization
          Pi source: file-mutation-queue.ts  MINION_ARCHITECTURAL_MAPPING
          WP: mutation tools                depends on: Layer 12 FsTarget.target_key

TOOL-011  write/edit: cancellation-vs-lock ordering (check-after-await)
          Pi source: write.ts, edit.ts     MINION_ARCHITECTURAL_MAPPING
          WP: mutation tools                depends on: TOOL-010

TOOL-012  find: argument schema, path-relativization, byte-only truncation
          Pi source: find.ts               DIRECT_PI_PARITY (shape) / see TOOL-014
          WP: search tools                  depends on: (none)

TOOL-013  grep: argument schema, match/context/limit shape
          Pi source: grep.ts               DIRECT_PI_PARITY (shape) / see TOOL-014
          WP: search tools                  depends on: (none)

TOOL-014  find/grep: match-engine parity strategy for an explicitly pinned engine
          Pi source: tools-manager.ts      MINION_EXTENSION -- OWNER DECISION REQUIRED
          WP: search tools                  depends on: TOOL-012, TOOL-013

TOOL-015  ls: argument schema, entry listing, byte truncation
          Pi source: ls.ts                 DIRECT_PI_PARITY (not fully read; needs completion)
          WP: search tools                  depends on: (none)
```

## Proposed work packages

Candidate B (filesystem read/query vs. filesystem mutation vs. bash), not Candidate A from the
prior hypothesis, is this pass's recommendation -- rationale below.

```text
WP-13.1  Filesystem read/query tools: read, find, grep, ls
WP-13.2  Filesystem mutation tools: write, edit, the shared mutation queue
WP-13.3  bash
```

Rationale: `read`/`find`/`grep`/`ls` share no mutation-queue dependency, no cancellation-ordering
subtlety, and no Layer-12-subprocess dependency -- they are independently certifiable against
Layer 12's `ctx.fs` alone and carry the *lowest* convergence risk of the three groups, so bundling
them lets that whole surface close first. `write`/`edit` share the mutation queue, its FIFO
key-derivation mapping onto `FsTarget.target_key`, and the identical cancellation-ordering
subtlety -- these are genuinely coupled and reviewing them together avoids re-litigating the same
queue characterization twice. `bash` is its own package because it is the only tool that consumes
`ctx.subprocess` at all, carries the R004-A/R004-B cross-reference, and has zero technical
dependency on the mutation queue or `find`/`grep`'s external-binary question -- coupling it to
either other group would force its (likely fast) closure to wait on the (likely slower,
owner-decision-blocked) `find`/`grep` engine-pinning question.

The prior hypothesis's WP-13.1 (`bash`+`read`+`write`+`edit`+serialization) would force `bash` --
which has no mutation-queue involvement at all -- to share a convergence episode with the queue
characterization, and its WP-13.2 (`glob`+`grep` only) would leave `read`/`ls` orphaned relative
to either package despite `read` sharing `find`/`grep`'s complete independence from mutation
concerns. Candidate B was chosen over a hypothetical single split by dependency shape (mutation
queue vs. subprocess vs. neither), not by filename grouping, per the explicit instruction to avoid
packages that merely mirror filenames.

`find`/`grep`'s external-binary/version-pinning question (`TOOL-014`) is intentionally *inside*
WP-13.1 rather than split out into its own package: it blocks `find`/`grep` implementation but not
`read`/`ls`, and splitting it further would produce a work package with a single open owner
decision and nothing else to certify independently.

## High-risk surfaces

```text
1. find/grep external-binary version pinning (HIGHEST RISK, OWNER DECISION REQUIRED)
   Pi's own `fd`/`rg` acquisition is UNPINNED: system PATH binary preferred, else
   latest-at-download-time GitHub release. There is no single "pinned Pi fd/rg version"
   to build an R002-style executable oracle against, because Pi itself does not have
   one -- its own observable glob/grep behavior varies by end-user machine. This is a
   fundamentally different situation from R002 (Ada 2.9.2), not a smaller version of the
   same problem. Options for the eventual contract (not decided here):
     a) Minion pins an exact fd/rg version itself (a deliberate, documented divergence
        from Pi's floating behavior, but restores testability);
     b) Minion defines its own glob/regex contract independent of fd/rg's exact
        semantics, treating "equivalent observable behavior" rather than "identical
        output" as the parity bar;
     c) some hybrid (pin for the differential-test corpus; document that a real
        Pi install may differ).
   This must be resolved BEFORE TOOL-012/013/014 implementation begins, not discovered
   mid-implementation the way R002 was.

2. edit's fuzzy-match-then-preserve-unchanged-lines algorithm
   Read in full and characterized above; the risk is porting it incorrectly (e.g.
   normalizing the whole file instead of only touched-line ranges), not incomplete
   characterization. Recommend a direct line-by-line port plus a differential corpus
   generated by running edit-diff.ts's own functions against constructed fixtures
   (exact match / fuzzy match / mixed-in-one-call / overlap / no-op cases), analogous to
   R002's approach but against Pi's own readable source rather than a third-party binary.

3. bash shell-invocation selection (getShellConfig / commandTransport)
   Not fully read in this pass (see bash entry, "not investigated further"). Needs a
   dedicated read of shell.ts before TOOL-001 implementation.

4. write's byte-count message quirk (content.length vs Buffer.byteLength)
   Low implementation risk, but an explicit disposition (reproduce the quirk verbatim
   for literal message parity, or intentionally fix it and document the divergence) is
   needed before TOOL-006 implementation so it is a decision, not an accident either way.

5. bash-vs-mutation-queue non-participation
   bash does not participate in the write/edit mutation queue at all, even though a bash
   command can freely mutate a file write/edit also targets. Not clear whether this is
   deliberate (bash's effects are the user/model's own responsibility) or an accepted gap
   in Pi. Recorded as an open question (section below), not a finding against Pi.
```

## Acceptance-oracle strategy (proposed, pre-implementation)

```text
bash kill/wait lifecycle       -- reuse Layer 12's existing ctx.subprocess conformance
                                   suite and R004-A/B witnesses directly; no new oracle
                                   needed, only new bash-level integration witnesses
truncation (head/tail/bytes)   -- fixed behavior matrix (exact byte-boundary/UTF-8
                                   cases), ported directly from truncate.ts's own logic
edit fuzzy-match algorithm     -- differential corpus generated by executing Pi's own
                                   edit-diff.ts functions (Node, pinned Pi checkout)
                                   against constructed fixtures; permanent regression
                                   gate mirroring R002's committed-corpus pattern
mutation queue FIFO/keying     -- property-style concurrency corpus (same-key ordering,
                                   different-key concurrency, failure-does-not-deadlock,
                                   realpath-vs-lexical-fallback) against the real
                                   FsTarget.target_key-based implementation
find/grep matching             -- BLOCKED on high-risk surface #1 above; no oracle
                                   strategy can be finalized until the pin/no-pin owner
                                   decision is made
path resolution (tilde, @,     -- fixed behavior matrix per platform; Windows Git-Bash/
Windows shell paths, file://)     MSYS/Cygwin/WSL cases need Windows CI coverage
                                   specifically, not just logic review
```

## Cross-language impact

Every surface above is expressed at the tool-argument/observable-output boundary, not internal
architecture -- both Python and Rust are free to implement independently as long as the observable
contract (schemas, error classification, truncation shape, mutation ordering) matches. The
mutation-queue key reuse of `FsTarget.target_key` and the bash kill/wait reuse of `ctx.subprocess`
both already have Python AND Rust implementations from Layer 12 (Python: `filesystem.py`,
`subprocess.py`; Rust: `filesystem.rs`, `subprocess.rs`, both independently certified in Layer
12), so Layer 13 in both languages should be able to build directly on already-cross-language-
certified seams for those two surfaces specifically -- a lower cross-language risk than Layer 12's
own R002/R004 had at the point Layer 13 begins. `find`/`grep`'s external-binary question (risk #1)
is cross-language-symmetric: whatever pin/no-pin decision is made applies identically to both
implementations, since both would shell out to (or bind) the same external engine choice.

## Open questions / owner decisions

```text
1. find/grep external-engine pinning strategy (see High-risk surface #1) -- REQUIRES
   OWNER DECISION before TOOL-012/013/014 implementation scoping.
2. write's byte-count message quirk: reproduce verbatim or intentionally diverge? --
   low-stakes, but needs an explicit disposition, not silence.
3. read's macOS filename-fallback heuristics: adopt, or treat as Pi-UX-only and drop? --
   depends partly on whether Minion's execution-world model even has a concept of
   "the local machine's filename encoding quirks" for a given FsTarget/provider.
4. bash's non-participation in the mutation queue: intentional Pi design or an accepted
   gap? -- informational only; does not block implementation scoping, but should be
   explicitly noted as "Pi's own behavior, not investigated further" rather than silently
   assumed correct-by-default when Minion's own bash tool is designed.
```

## Implementation authorized

```text
NO
```
