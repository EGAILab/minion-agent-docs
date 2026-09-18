# Execution Capability Seams (Layer 12, WP-12.1)

This document covers the three execution capability seams -- `ctx.fs`, `ctx.shell`, and
`ctx.subprocess` -- their shared error/Result boundary, the `FsTarget`/`target_key`/`process_path`
bridge that keeps independently-swappable filesystem/process capabilities able to refer to the
same resource, execution-world compatibility, and the local providers needed to exercise and
certify all of the above.

It does **not** cover built-in tools (`bash`/`read`/`write`/`edit`/`glob`/`grep`) or the per-file
mutation-serialization queue -- both move to Layer 13 (owner decision, `GOVERNANCE_SOURCE`
`https://github.com/EGAILab/minion-agent/issues/39#issuecomment-5736233272`, per
`agent-workflow.md` §11.10). This row's own closure criterion is limited to the capability seams
themselves plus the identity guarantee a future Layer 13 mutation queue needs to use safely --
implementing that queue here would be scope creep this decision explicitly forbids.

Every requirement below is labeled with exactly one of:

```text
DIRECT_PI_PARITY            -- pinned Pi's own observable behavior, ported as-is
MINION_ARCHITECTURAL_MAPPING -- a deliberate Minion-specific shape/mechanism with no Pi equivalent,
                                 built to preserve an observable guarantee Pi provides differently
MINION_EXTENSION             -- a deliberate Minion-specific capability with no Pi equivalent at all
```

per the owner's own explicit requirement that a Minion-specific rule must never acquire a false
Pi-parity citation merely because it sits beside Pi-derived rules in the same document.

Pinned Pi revision: `b7bb00b936dbe21b8e160b3e89efdec361846699`. Primary Pi sources audited:
`packages/agent/src/harness/types.ts` (interface/error vocabulary) and
`packages/agent/src/harness/env/nodejs.ts` (the harness-tier reference `ExecutionEnv`
implementation -- the concrete source of every specific behavioral claim below that isn't already
stated abstractly in `types.ts`).

---

## 1. Architecture: three seams, not one combined environment

**MINION_ARCHITECTURAL_MAPPING.** Pinned Pi defines `FileSystem` and `Shell` as separate
interfaces but every real consumer depends on their combination, `ExecutionEnv extends FileSystem,
Shell` (`types.ts:315`; `ExecutionToolContext.env: ExecutionEnv`, `tool-context.ts:5` -- no Pi
consumer takes `FileSystem` or `Shell` alone). Pi therefore split the TYPES but not the DEPENDENCY:
a Pi consumer that only reads files still requires a full `ExecutionEnv`, so a local filesystem can
never be paired with a remote shell in Pi's own architecture.

Minion splits the dependency itself. Three independent capability seams:

```text
ctx.fs           -- filesystem operations
ctx.shell        -- shell command execution
ctx.subprocess   -- raw argv-direct process spawning
```

Each consumer declares only the capability it actually uses. `read`/`glob`/`grep` need `fs` only.
An MCP-over-stdio integration needs `subprocess` only. `bash` needs `fs` + `shell` in the SAME
execution world (§7). An edit-via-external-process consumer needs `fs` + `subprocess` in the same
world. This table is illustrative of the compatibility mechanism (§7); the consumers themselves
(`bash`, `glob`, `grep`, MCP transports) are Layer 13+ territory, not certified by this row.

This split is Minion's own mechanism for a real, useful deployment shape Pi's combined dependency
cannot express at all (e.g. local configuration files alongside a remote shell), not a
simplification of Pi behavior and not itself an observable-behavior change to any single seam's own
operations.

---

## 2. The Result/error boundary (shared across all three seams)

**DIRECT_PI_PARITY**, generalized to a third seam pinned Pi does not have (§6). Pinned Pi's own
`FileSystem`/`Shell` operation methods "must never throw or reject. All filesystem failures,
including unexpected backend failures, must be encoded in the returned `Result`" (`types.ts:228-
229`). Minion adopts this exact boundary for all three seams:

```text
Result[T, FsError]           # ctx.fs
Result[T, ShellError]        # ctx.shell
Result[T, SubprocessError]   # ctx.subprocess
```

The governing rule, stated once so it need not be repeated per operation:

> An execution-seam operation normalizes every expected operational/environmental failure into a
> typed `Result` error. Framework/provider invariant violations and programming errors remain
> exceptions (Python) / panics (Rust).

**Values** (expected, caller-handleable): not found, permission denied, invalid path, stale
version (Layer 13's own future concern via `FsTarget`, not this row's), timeout, abort/cancelled,
non-zero process exit, I/O failure, remote/backend unavailable.

**Exceptions** (framework/provider bugs, never caller-handleable): invalid internal state,
impossible state transition, a provider failing to normalize a backend exception into its own
error vocabulary, assertion failures, programming errors.

Normalization is the PROVIDER's obligation, never the caller's: a bare `OSError` (Python), a raw
platform/OS exception, or an unmapped backend error escaping a seam operation is itself a provider
bug, not a condition callers are expected to catch. Each implementation language maps its own
native error primitives (Python's `OSError.errno`, `subprocess` exceptions; Rust's `std::io::Error`
kinds) onto the SAME language-neutral code taxonomy below -- the exact native-to-code mapping is
implementation mechanics, not itself part of this contract, but the RESULTING code taxonomy and
which conditions must map to which code are normative.

### 2.1 `FsError` codes

**DIRECT_PI_PARITY** (`FileErrorCode`, `types.ts:132-140`):

```text
aborted | not_found | permission_denied | not_directory | is_directory | invalid |
not_supported | unknown
```

Confirmed concrete mapping in the harness-tier reference implementation (`nodejs.ts:97-121`,
`toFileError`): `ABORT_ERR -> aborted`, `ENOENT -> not_found`, `EACCES`/`EPERM -> permission_denied`,
`ENOTDIR -> not_directory`, `EISDIR -> is_directory`, `EINVAL -> invalid`, anything else ->
`unknown`. This exact errno list is Node-specific mechanics; the CONDITIONS these codes represent
(the argument is a directory when a file was expected, the reverse, the operation was cancelled,
etc.) are the language-neutral contract each provider must reproduce from its own OS primitives.

### 2.2 `ShellError`/`ExecutionError` codes

**DIRECT_PI_PARITY** (`ExecutionErrorCode`, `types.ts:158-164`):

```text
aborted | timeout | shell_unavailable | spawn_error | callback_error | unknown
```

`callback_error` is a genuinely distinctive Pi behavior, not an obvious inclusion: if a caller's
own `onStdout`/`onStderr` streaming callback throws, the reference implementation catches it,
classifies the FAILURE (not the original command) as `callback_error`, and aborts the in-flight
command as a side effect (`nodejs.ts:462-468, 474-478`) -- a throwing callback terminates the whole
`exec()` call, it does not merely fail to receive further chunks.

`shell_unavailable` fires when no usable shell binary can be resolved at all (§5.1).

### 2.3 `SubprocessError` codes

**MINION_EXTENSION** (`ctx.subprocess` has no direct Pi seam to inherit an error taxonomy from;
this taxonomy is derived from the OBSERVABLE process-lifecycle failure modes `ctx.shell`'s own
local provider already demonstrates it needs, per `nodejs.ts`'s own `exec()`, since the master
design states `ctx.shell`'s local provider spawns through `ctx.subprocess`):

```text
aborted | timeout | spawn_error | pipe_error | unknown
```

`spawn_error` covers a failure to start the process at all (binary not found, permission denied to
execute, working directory does not exist -- the reference `Shell.exec()` implementation checks
this LAST condition explicitly and eagerly, before ever attempting to spawn, `nodejs.ts:379-390`,
returning a specific diagnostic rather than a generic OS spawn failure). `pipe_error` covers a
failure reading/writing the process's own stdio streams after it has started. This taxonomy MUST
be treated as a draft pending independent review (§9) -- it is the one place in this contract with
no Pi source to audit against, and the reviewer should check it against the process-lifecycle
primitives §6 actually requires, not merely accept it as complete.

---

## 3. `ctx.fs` (filesystem seam)

**DIRECT_PI_PARITY** for the operation set and their individual observable behaviors, confirmed
against `types.ts:222-283` (interface) and `nodejs.ts:359-694` (harness-tier reference
implementation, the concrete source for every behavioral claim not already explicit in the
interface's own doc comments):

```text
cwd                                                   -- current working directory for relative paths
absolute_path(path, signal?) -> Result[str, FsError]
join_path(parts, signal?) -> Result[str, FsError]
read_text_file(path, signal?) -> Result[str, FsError]
read_text_lines(path, max_lines?, signal?) -> Result[list[str], FsError]
read_binary_file(path, signal?) -> Result[bytes, FsError]
write_file(path, content, signal?) -> Result[None, FsError]
append_file(path, content, signal?) -> Result[None, FsError]
rename_file(source, destination, signal?) -> Result[None, FsError]
file_info(path, signal?) -> Result[FileInfo, FsError]
list_dir(path, signal?) -> Result[list[FileInfo], FsError]
canonical_path(path, signal?) -> Result[str, FsError]
exists(path, signal?) -> Result[bool, FsError]
create_dir(path, recursive=True, signal?) -> Result[None, FsError]
remove(path, recursive=False, force=False, signal?) -> Result[None, FsError]
create_temp_dir(prefix="tmp-", signal?) -> Result[str, FsError]
create_temp_file(prefix="", suffix="", signal?) -> Result[str, FsError]
cleanup() -> None   # best-effort, must not raise
```

```text
FileInfo{name, path, kind, size, mtime_ms}
FileKind = file | directory | symlink
```

### 3.1 Path resolution

**DIRECT_PI_PARITY.** Paths passed to any `ctx.fs` operation may be absolute or relative to `cwd`.
Confirmed concrete resolution rules from the reference implementation (`nodejs.ts:51-65`,
`resolvePath`):

- a bare `~` resolves to the home directory;
- a path starting with `~/` (or, on Windows, `~\`) resolves to `home_directory + rest_of_path`;
- a `file://` URL is parsed to a filesystem path; a malformed `file://` URL is kept as an ordinary
  (almost certainly invalid) path string rather than raising, preserving the never-throw contract
  -- it surfaces later as an ordinary `not_found`/`invalid` `Result` from whichever operation
  actually touches it, not as a resolution-time exception;
- an absolute result is used as-is (syntactically normalized); a relative result is resolved
  against `cwd`.

Symlinks are never followed by path resolution or by any operation method except `canonical_path`,
which is the one explicit, opt-in symlink-resolution operation (`realpath`-equivalent,
`nodejs.ts:635-642`). `file_info`/`list_dir`/`exists` all use the non-following stat form
(`lstat`-equivalent, `nodejs.ts:602-609, 611-633, 644-649`) -- a symlink itself is reported as kind
`symlink`, never silently resolved to its target's own kind.

### 3.2 Reads

**DIRECT_PI_PARITY.** `read_text_lines`'s own `max_lines` stops reading once that many lines have
been produced -- a large file is not read in full merely to return its first few lines
(`nodejs.ts:513-542`, streamed line-by-line via a line reader, breaking out of the loop once the
limit is hit). `max_lines <= 0` (when explicitly provided) returns an empty list without touching
the file at all.

### 3.3 Writes

**DIRECT_PI_PARITY.** `write_file` and `append_file` both create missing parent directories
recursively before writing (`nodejs.ts:564, 577`) -- a caller never needs a separate
`create_dir(parents_of(path))` call before writing a file in a not-yet-existing directory tree.
`write_file` creates-or-overwrites; `append_file` creates-or-appends. Neither copies across
filesystems -- both operate on one resolved path within the SAME `ctx.fs` provider.

**Independent review note:** the reference implementation's own `append_file` does not thread its
abort signal through to the underlying write call at all (`nodejs.ts:574-583` takes no
`abortSignal` parameter, unlike every sibling read/write operation) -- confirmed by direct
comparison against `writeFile`'s own signature two lines above it, which does. This SHOULD be
treated as `PI_BEHAVIOR_UNCERTAIN` rather than silently ported or silently corrected: it may be an
intentional simplification (append is typically fast/small) or an overlooked omission in Pi's own
reference implementation. The independent reviewer (§9) should confirm which, and this section
updated with the resolution before the checkpoint closes.

### 3.4 Rename

**DIRECT_PI_PARITY.** `rename_file` is atomic and REPLACES an existing destination
(`nodejs.ts:585-600`, a direct OS rename, not implemented as copy-then-delete). It does not copy
across filesystems/devices -- a cross-filesystem rename fails with a normal `FsError` rather than
silently falling back to a copy.

### 3.5 Metadata and listing

**DIRECT_PI_PARITY.** `file_info` returns `{name, path, kind, size, mtime_ms}` for the addressed
path without following symlinks. `list_dir` returns direct children only (non-recursive), each
entry's own `FileInfo` also computed without following symlinks (`nodejs.ts:611-633` -- `lstat` on
each entry, not `stat`).

### 3.6 Temporary resources

**DIRECT_PI_PARITY**, one Minion-facing implementation choice flagged for review. `create_temp_dir`
creates a fresh, uniquely-named directory under the platform temp root. `create_temp_file`, per the
reference implementation, creates a FRESH temp DIRECTORY first and then places the temp file inside
it with a random-UUID-based name (`nodejs.ts:679-688`) -- i.e. every temp FILE also gets its own
private temp DIRECTORY, not merely a unique filename in a shared temp directory. This is worth the
independent reviewer explicitly confirming is intentional (it means `cleanup()`-adjacent temp-file
removal must also remove that file's own private directory, not just the file) rather than an
implementation-mechanics accident of how the reference implementation happens to be composed from
two calls.

### 3.7 Cleanup

**DIRECT_PI_PARITY.** `cleanup()` releases filesystem resources and MUST be best-effort -- it must
never raise/reject regardless of what it fails to clean up.

---

## 4. The `FsTarget` bridge

**MINION_ARCHITECTURAL_MAPPING** (owner-approved explicitly, `GOVERNANCE_SOURCE` cited above --
"the following Minion-specific architecture is explicitly approved as a mapping/divergence from Pi
rather than direct Pi parity"). Has no Pi equivalent: Pi's own combined `ExecutionEnv` never needs
resource identity to survive across independently-swappable capabilities, because it never permits
independent swapping in the first place.

```text
resolve(path, signal?) -> Result[FsTarget, FsError]

FsTarget
    target_key: opaque, backend-defined identity value
    -- no further public structure; callers must not parse it, compare its syntax to a path, or
       infer backend identity/location from its shape

process_path(target: FsTarget) -> Result[str, FsError]
    -- returns the path usable by a process running in the target's own execution world
```

Binding requirements:

- **Same-resource identity.** The same underlying filesystem resource, reached through two
  syntactically different but semantically equivalent paths (e.g. a relative path and its resolved
  absolute form; a path and a symlink to the same target, if the provider's own `resolve()`
  chooses to follow it -- that choice belongs to the provider, not this contract), MUST resolve to
  the SAME `target_key`. This is the guarantee a future Layer 13 mutation-serialization queue will
  key on (`process/agent-workflow.md` §11.13's "consume already-certified... requirements
  normally" applies here once Layer 13 exists) -- Layer 12 owns proving the guarantee holds, not
  building the queue that will eventually rely on it.
- **Opacity.** `target_key` carries no promised syntax. A caller must not attempt to derive a
  filesystem path, a backend type, or any other structured meaning from it beyond equality
  comparison.
- **`process_path`.** Returns the path a process spawned in the CORRESPONDING execution world
  (§7) can open to reach the same resource. This is the mechanism `bash`/edit-via-process (Layer
  13's own future consumers) will use to hand a resolved target to a shell/subprocess command
  without re-resolving the path themselves and without the filesystem and process capabilities
  needing to agree on path syntax ahead of time.

This section states the REQUIRED guarantees; it does not specify a backend mechanism (content
hash, device+inode pair, canonical path string, or something else) -- that is a legitimate
implementation choice each provider makes for itself, provided the same-resource-identity guarantee
holds.

---

## 5. `ctx.shell`

**DIRECT_PI_PARITY** for the observable contract, confirmed against `types.ts:285-312`
(`ShellExecOptions`/`Shell`) and the harness-tier reference implementation's own `exec()`
(`nodejs.ts:367-500`):

```text
exec(command, cwd?, env?, inherit_env=True, timeout?, signal?, on_stdout?, on_stderr?)
    -> Result[{stdout, stderr, exit_code}, ShellError]

cleanup() -> None   # best-effort, must not raise
```

### 5.1 Shell resolution

**DIRECT_PI_PARITY** for the OBSERVABLE guarantee; the exact discovery mechanism is
implementation mechanics each provider implements with platform-appropriate primitives, not a
literal line-by-line port. The reference implementation's own observable behavior: prefer `bash`
if one can be located (a configured custom shell path; else a well-known local install path; else
a `PATH` search); on POSIX, silently fall back to `sh` if no `bash` is found at all (`exec()` never
fails purely for lacking `bash` on POSIX); on Windows, fail with `shell_unavailable` and a specific,
actionable diagnostic if no `bash` can be located by any method (`nodejs.ts:196-238`) -- Windows has
no silently-acceptable fallback shell the way POSIX has `sh`.

### 5.2 Working directory precondition

**DIRECT_PI_PARITY.** The reference implementation checks that the resolved working directory
exists BEFORE attempting to spawn anything, failing early with `spawn_error` and a specific
diagnostic naming the missing directory if it does not (`nodejs.ts:379-390`) -- this is not merely
an incidental OS spawn failure surfacing generically; it is checked and reported specifically.

### 5.3 Environment

**DIRECT_PI_PARITY.** `inherit_env` defaults to `True`. When `True`, the effective environment is
the seam provider's own default environment (its own inherited/base environment) overlaid by any
per-call `env`. When `False`, the effective environment is EXACTLY the per-call `env` and nothing
else -- no inherited variables leak through (`nodejs.ts:240-251`, `getShellEnv`).

### 5.4 Timeout, abort, and their precedence

**DIRECT_PI_PARITY.** `timeout` is in seconds; there is no default timeout. An invalid timeout
(non-finite, non-positive, or exceeding roughly `2^31/1000` seconds -- the underlying platform
timer's own representable range) is a `Result` failure at call time, before any process is spawned,
never a validation exception (`nodejs.ts:38-49`). When BOTH a timeout and the caller's own abort
signal are in play and the command is killed, timeout takes precedence in the returned failure's
own classification: if the timeout fired, the result is classified `timeout` even if the signal
also happened to be (or becomes) aborted; only when the timeout did NOT fire does an aborted signal
classify the result as `aborted` (`nodejs.ts:487-494`, checked in that exact order). Killing a
command, on either abort or timeout, terminates its ENTIRE process tree/group, not merely the
directly-spawned process -- a command that itself backgrounds a child process does not leave that
child running after the parent command is killed (`nodejs.ts:253-276`, process-group kill on POSIX
via a negative PID targeting the whole group, falling back to single-PID kill if the group-kill
itself fails; a tree-kill primitive on Windows).

### 5.5 Streaming callbacks and callback-error propagation

**DIRECT_PI_PARITY.** `on_stdout`/`on_stderr`, when provided, are invoked with each chunk as it
arrives, in addition to (not instead of) accumulating the FULL stdout/stderr the final `Result`
carries -- a caller does not have to choose between streaming and the final aggregate. If either
callback itself raises, the raised failure is classified `callback_error`, and the in-flight
command is killed as a side effect of that classification (§2.2) -- a throwing callback is not
merely skipped or logged.

### 5.6 Result shape

**DIRECT_PI_PARITY.** A successful `exec()` returns `{stdout, stderr, exit_code}` regardless of
whether `exit_code` is zero -- a non-zero exit is NOT itself a `Result` failure at the `ctx.shell`
seam; classifying a non-zero exit as a tool-level failure (as the future `bash` built-in tool does)
is Layer 13's own concern, not this seam's.

---

## 6. `ctx.subprocess`

**MINION_EXTENSION.** Owner-directed: "Its contract must be designed from the frozen master
architecture rather than represented as Pi parity." Pinned Pi's own harness layer has no standalone
capability seam for this at all; the design's own justification (`design/2026-08-20-minion-agent-
design.md` §7) is that protocol-over-stdio integrations (MCP over stdio, language servers,
browser automation) need raw process/stream lifecycle, not shell command execution, and that
`ctx.shell`'s own LOCAL provider is built on top of `ctx.subprocess` rather than re-implementing
process management itself -- confirmed structurally plausible against the reference `Shell.exec()`
implementation's own process-management primitives (`nodejs.ts:392-499`: argv-direct spawn, stdio
stream handling, process-group kill on timeout/abort, exit-plus-stdio-drain waiting), which is
exactly the primitive set a `ctx.subprocess` seam would need to expose for `ctx.shell`'s own local
provider to be built from it rather than duplicating it.

Required capability, at minimum:

```text
spawn(argv, cwd?, env?, inherit_env=True, signal?) -> Result[Process, SubprocessError]

Process
    pid
    stdin    -- raw writable stream, if requested
    stdout   -- raw readable stream
    stderr   -- raw readable stream
    wait() -> Result[int | None, SubprocessError]   # exit code, or None if killed before exiting
    terminate()   -- best-effort, must not raise; kills the process (and, matching ctx.shell's own
                     §5.4 guarantee, its full process tree/group where the platform supports it)
```

Binding requirements:

- **`argv`-direct only.** `spawn` takes an argument VECTOR, never a command string. The seam MUST
  NOT shell-interpret its arguments under any circumstance -- no quoting/globbing/variable
  expansion/pipeline syntax is ever applied to `argv` elements. A caller that wants shell semantics
  explicitly invokes `ctx.shell` instead; `ctx.subprocess` never does this implicitly on a caller's
  behalf, regardless of what the command looks like.
- **Process lifecycle.** `wait()` observes the process's own exit, matching `ctx.shell`'s own
  "wait for exit AND for stdio streams to fully drain" discipline (§5, reference implementation
  `nodejs.ts:278-345`) rather than resolving the instant the OS reports the process as exited while
  a few more buffered output bytes are still in flight.
- **Termination/cancellation.** `terminate()` and signal-triggered cancellation both kill the whole
  process tree/group where the platform supports it, matching `ctx.shell`'s own §5.4 guarantee --
  this is the SAME underlying mechanism `ctx.shell`'s local provider is built from, so the
  guarantee must genuinely be shared, not merely similarly worded.
- **Spawn failures.** A failure to start the process at all (binary not found, not executable,
  working directory missing) is a `Result` failure classified `spawn_error`, never an exception.
- **Pipe/I/O failures.** A failure reading or writing the process's own stdio streams after it has
  started is a `Result` failure classified `pipe_error`.

---

## 7. Execution-world identity and compatibility

**MINION_EXTENSION.** No Pi equivalent -- Pi's combined `ExecutionEnv` never needs this because it
is never independently swappable in the first place (§1).

```text
Every execution-capability provider (a ctx.fs, ctx.shell, or ctx.subprocess implementation)
declares an opaque execution-world identity at construction/activation.
```

The governing rule (owner-restated verbatim in the approving decision, binding as written):

> Mounting capabilities from different execution worlds is legal. A consumer that needs multiple
> capabilities to address the SAME resource must validate that those capabilities belong to
> compatible execution worlds. Cross-world resource transfer requires an explicit bridge
> capability.

This is deliberately **not** a global runtime rule requiring every mounted `fs`/`shell`/
`subprocess` provider to share one world -- a local `ctx.fs` for configuration alongside a remote
`ctx.shell` is a legitimate deployment with nothing wrong about it, right up until something tries
to carry a resource between them.

**Validation is the CONSUMER's responsibility, not the runtime's.** A future consumer that needs
`fs` + `shell` in the same world (`bash`) or `fs` + `subprocess` in the same world (edit-via-
process) performs its own compatibility check at its own activation, failing with a diagnostic
naming the incompatible providers if the worlds don't match; an unrelated consumer that doesn't
need cross-seam resource identity mounts happily beside an incompatible pairing without complaint.

**This row's own certification scope.** WP-12.1 owns the compatibility VOCABULARY (the identity
type, the comparison/validation primitive a consumer calls) and proves the mechanism itself works
correctly, using synthetic/test consumers -- it does NOT implement any real Layer 13 consumer
(`bash`, etc.) to prove this, and does not need to.

---

## 8. Local providers

**DIRECT_PI_PARITY** for observable behavior (§3-§6 above, each already citing the harness-tier
reference implementation as its concrete source), **MINION_ARCHITECTURAL_MAPPING** for the fact
that they are three separate local providers rather than one combined local `ExecutionEnv`.

The basic local filesystem, shell, and subprocess providers needed to exercise and certify §2-§7
are in scope for this row. Each MUST satisfy the exact same shared contracts (§2-§7) as any future
remote/sandboxed provider -- no local-machine assumption may be baked into the abstract capability
contracts themselves; where the local providers' own concrete behavior (real OS errno mapping,
real shell-binary discovery, real process-group semantics) is genuinely platform-specific
mechanics rather than an observable cross-provider guarantee, that mechanics lives in the local
provider's own implementation, not in this contract.

All three local providers share one execution-world identity by construction (they all operate on
the same local machine) -- this is the SIMPLEST possible case for §7's compatibility mechanism,
not an exemption from declaring/validating identity at all.

---

## 9. Required independent review

This is a confirmed contract-first-checkpoint candidate (`agent-workflow.md` §4.1): the surface
combines direct Pi parity, deliberate Minion architectural mappings, three separate error domains,
a genuinely new cross-provider compatibility mechanism, resource identity, cancellation, raw
process lifecycle, and local-provider normalization, with several interacting dimensions whose
cross-product matters (an execution-world mismatch is only observable when a consumer actually
needs two capabilities at once; a timeout racing an abort has a specific precedence rule; a
throwing callback aborts a command as a side effect of its own error classification).

Two items are explicitly flagged above as needing the reviewer's own judgment before this
checkpoint can close, not merely a rubber-stamp of this draft:

- §3.3's `append_file` abort-signal omission (`PI_BEHAVIOR_UNCERTAIN` candidate);
- §6's `SubprocessError` taxonomy, which has no Pi source to audit against at all.

Per the standard flow (`agent-workflow.md` §4.1): this draft is the Claude Pi-audit half of the
contract-first checkpoint. An independent Pi audit of this same semantic slice, resolution of any
findings, and an explicit `AGREED FOR IMPLEMENTATION` checkpoint are required before Python
implementation begins. No Python implementation is authorized by this document alone.
