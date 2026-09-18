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
interfaces. Pi's own EXECUTION-TOOL consumers depend on their combination -- `ExecutionEnv extends
FileSystem, Shell` (`types.ts:315`), consumed as `ExecutionToolContext.env: ExecutionEnv`
(`tool-context.ts:5`) by every built-in execution tool (`bash`/`read`/`write`/`edit`) -- so a Pi
execution tool that only reads files still requires a full `ExecutionEnv`, and a local filesystem
can never be paired with a remote shell for THAT consumer class.

**Correction record (independent review, `L12-R003`):** an earlier revision of this section
overgeneralized this to "no Pi consumer takes `FileSystem` or `Shell` alone." That is false --
confirmed directly against pinned Pi: `packages/agent/src/harness/session/jsonl/types.ts` defines
`JsonlSessionRepoFileSystem = Pick<FileSystem, "absolutePath"|"joinPath"|"readTextFile"|
"readTextLines"|"writeFile"|"appendFile"|"renameFile"|"fileInfo"|"listDir"|"exists"|"createDir"|
"remove">`, consumed by `JsonlSessionRepoOptions.fs` -- a real, `FileSystem`-only Pi consumer with
no `Shell` dependency at all. The accurate claim is narrower: Pi's own BUILT-IN EXECUTION TOOLS
require the combined `ExecutionEnv`; Pi's own session-persistence layer does not. Minion's own
three-way split (§1 above) remains motivated and valid regardless -- it is not weakened by this
correction, since even a single counter-example consumer confirms Pi's own combined dependency is
an execution-tool-specific constraint, not a fundamental one, which is exactly the kind of
constraint Minion's own split is free to relax.

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

**This rule applies per-operation, not uniformly to every method on a seam.** Some operations have
a documented SUCCESS value that itself reports an otherwise-unsuccessful outcome (§5.6: a shell
command's own non-zero exit code is not a `Result` error at the `ctx.shell` seam -- it is
information carried inside a successful `Result`). Lifecycle/cleanup methods (`cleanup()`,
`Process.terminate()`) are explicitly exempt from returning `Result` at all (§3.8, §6) -- they are
best-effort and must not raise, but they are not themselves classified as "operations that return
typed errors." §2.1-§2.3 below state exactly which codes exist and which operations can produce
them; a finding of "X is listed as a Value but no declared code represents it, or no operation can
produce it" is a defect in this document, not a license to invent an unmapped condition.

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

**Correction record (independent review, `L12-R004`):** an earlier revision of this section listed
"non-zero process exit" as a `Result`-error Value while §5.6 correctly stated the opposite --
confirmed directly self-contradictory, and confirmed factually wrong against pinned Pi (`env.exec
("exit 7")` returns `Ok({stdout:"", stderr:"", exitCode:7})`, `nodejs-env.test.ts:448-449`). It
also listed "stale version" and "remote/backend unavailable" as Values with no corresponding
declared code anywhere in this document. All three are removed from this section; §2.1-§2.3 below
are now the SOLE source of truth for which codes exist.

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
aborted | spawn_error | pipe_error | unknown
```

`spawn_error` covers a failure to start the process at all (binary not found, permission denied to
execute, working directory does not exist -- the reference `Shell.exec()` implementation checks
this LAST condition explicitly and eagerly, before ever attempting to spawn, `nodejs.ts:379-390`,
returning a specific diagnostic rather than a generic OS spawn failure). `pipe_error` covers a
failure reading/writing the process's own stdio streams after it has started. `aborted` is
produced by `spawn()` for a pre-aborted signal and by `wait()` when the process is terminated via
signal-triggered cancellation (§6.4).

**Correction record (independent review, `L12-R006`):** an earlier revision of this taxonomy
included `timeout`, but no operation in this contract (`spawn`, `wait`, `terminate`) accepts a
`timeout` parameter that could ever produce it -- `ctx.subprocess` has no native timeout concept at
all; a caller wanting a timeout composes its own signal with a timer (exactly how `ctx.shell`'s own
local provider layers its own `timeout` option on top of `ctx.subprocess`'s pre-aborted/`abort`
signal primitive, per §6.5). Removed. Every code above now maps to at least one operation defined
in §6, and §6 states exactly which operation can produce which code.

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

### 3.1 Cancellation -- explicit sourcing decision (independent review, `L12-R001`)

An earlier revision of this document flagged only `append_file`'s missing `signal` handling as
`PI_BEHAVIOR_UNCERTAIN`. Independent review found the SAME gap on nine of sixteen `FileSystem`
methods, not one: pinned Pi's own `FileSystem` INTERFACE (`types.ts:222-283`) declares `signal?`
on every operation, but pinned Pi's own harness-tier REFERENCE IMPLEMENTATION
(`NodeExecutionEnv`, `nodejs.ts`) does not actually accept or check it on `absolute_path`,
`join_path`, `append_file`, `file_info`, `canonical_path`, `exists`, `create_dir`, `remove`,
`create_temp_dir`, or `create_temp_file` at all -- confirmed directly by reading each method's own
concrete signature. This is a genuine interface/reference-implementation conflict in pinned Pi
itself, not a Minion drafting gap to quietly resolve by guessing which operations "seem like" they
need cancellation.

**Sourcing decision:** Minion adopts pinned Pi's own INTERFACE-declared contract -- every `ctx.fs`
operation accepts an optional `signal` and MUST check it -- as the normative target, rather than
silently inheriting the reference implementation's own incomplete threading of it. This is a
**MINION_ARCHITECTURAL_MAPPING**, not unqualified direct parity: Minion is choosing the STRICTER,
fully-self-consistent half of a self-inconsistent Pi source, not reproducing either half verbatim.
Recorded here explicitly, per the review's own instruction, rather than left as an implicit
inference from operation duration.

Binding requirement for every `ctx.fs` operation: a pre-aborted `signal` MUST short-circuit the
operation before any filesystem I/O begins, returning an `aborted` `FsError` (matching the pattern
pinned Pi's own reference implementation already uses consistently on the operations it DOES check,
e.g. `readTextFile`, `nodejs.ts:502-511`). For an operation whose own work is genuinely unbounded
(a large file read/write, a large directory listing), the operation SHOULD also honor cancellation
that arrives mid-operation, not merely at entry.

Pinned Pi's own reference implementation's ACTUAL per-method behavior, recorded for engineering
awareness (this is what a Python/Rust local provider is improving on, not copying):

```text
checks pre-aborted AND honors mid-operation cancellation:
    read_text_file, read_binary_file, write_file       (signal passed through to the underlying
                                                          Node read/write call)
    read_text_lines, list_dir                          (re-checked at each loop iteration)

checks pre-aborted only (no mid-operation checkpoint, but the call is a single fast syscall):
    rename_file

does not accept or check the signal at all in the reference implementation:
    absolute_path, join_path, append_file, file_info, canonical_path, exists, create_dir,
    remove, create_temp_dir, create_temp_file
```

### 3.2 Path resolution

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

**Correction record (independent review, `L12-R002`):** an earlier revision of this section stated
symlinks are "never followed by path resolution or by any operation" except `canonical_path`. That
claim was wrong -- confirmed against pinned Pi directly: ordinary content operations (`readFile`/
`writeFile`/`appendFile`/`rename` from `node:fs/promises`, with no `O_NOFOLLOW`-equivalent flag)
traverse a symlink at its final path component exactly as the OS's own `open()`/`rename()` would.
The non-following guarantee is real, but it applies to a NARROWER set of operations than the
earlier text claimed. Corrected, per-operation-class:

- **Lexical/addressed path resolution** (`absolute_path`, `join_path`) -- pure string/path
  manipulation; touches no filesystem object at all and therefore cannot traverse a symlink either
  way (`resolvePath`, `nodejs.ts:51-65`, never calls a filesystem-inspecting primitive).
- **`lstat`-based metadata** (`file_info`, `list_dir`, `exists`) -- non-following (`lstat`-
  equivalent, `nodejs.ts:602-609, 611-633, 644-649`); a symlink itself is reported as kind
  `symlink`, never silently resolved to its target's own kind. `exists` is derived from `file_info`
  (a `not_found` result maps to `false`; any other error propagates), so it inherits the same
  non-following behavior.
- **Explicit canonicalization** (`canonical_path`) -- the one operation whose entire PURPOSE is to
  resolve symlinks (`realpath`-equivalent, `nodejs.ts:635-642`); opt-in, never implicit.
- **Ordinary content I/O** (`read_text_file`, `read_text_lines`, `read_binary_file`, `write_file`,
  `append_file`, `rename_file`) -- **DOES follow a symlink at its final path component**, matching
  the underlying OS `open()`/`rename()` semantics these operations are built on (`readFile`/
  `writeFile`/`appendFile`/`rename` from `node:fs/promises`, `nodejs.ts:502-600`, none of which
  passes any no-follow flag). Reading through a symlink returns the TARGET's own content; writing/
  appending through a symlink mutates the TARGET, not the link itself.

The distinction that survives is: path resolution never traverses symlinks (nothing to traverse --
it never touches the filesystem), metadata never traverses symlinks (deliberately, via `lstat`),
canonicalization always traverses symlinks (that is its entire job), and ordinary content I/O
traverses symlinks because the OS primitives underneath it do, not because this seam adds any
symlink-following logic of its own.

### 3.3 Reads

**DIRECT_PI_PARITY.** `read_text_lines`'s own `max_lines` stops reading once that many lines have
been produced -- a large file is not read in full merely to return its first few lines
(`nodejs.ts:513-542`, streamed line-by-line via a line reader, breaking out of the loop once the
limit is hit). `max_lines <= 0` (when explicitly provided) returns an empty list without touching
the file at all.

### 3.4 Writes

**DIRECT_PI_PARITY.** `write_file` and `append_file` both create missing parent directories
recursively before writing (`nodejs.ts:564, 577`) -- a caller never needs a separate
`create_dir(parents_of(path))` call before writing a file in a not-yet-existing directory tree.
`write_file` creates-or-overwrites; `append_file` creates-or-appends. Neither copies across
filesystems -- both operate on one resolved path within the SAME `ctx.fs` provider.

**Cancellation:** the reference implementation's own `append_file` does not thread its abort signal
through to the underlying write call at all -- one instance of the broader interface/reference-
implementation cancellation conflict resolved at §3.1. Per that section's sourcing decision,
Minion's own `append_file` MUST accept and check `signal` (pre-aborted short-circuit required; the
write itself is typically small enough that mid-operation cancellation is not required, matching
`rename_file`'s own "checked at entry only" tier in §3.1's table).

### 3.5 Rename

**DIRECT_PI_PARITY.** `rename_file` is atomic and REPLACES an existing destination
(`nodejs.ts:585-600`, a direct OS rename, not implemented as copy-then-delete). It does not copy
across filesystems/devices -- a cross-filesystem rename fails with a normal `FsError` rather than
silently falling back to a copy.

### 3.6 Metadata and listing

**DIRECT_PI_PARITY.** `file_info` returns `{name, path, kind, size, mtime_ms}` for the addressed
path without following symlinks. `list_dir` returns direct children only (non-recursive), each
entry's own `FileInfo` also computed without following symlinks (`nodejs.ts:611-633` -- `lstat` on
each entry, not `stat`).

### 3.7 Temporary resources

**DIRECT_PI_PARITY** for creation shape; **corrected, not adopted,** for any cleanup obligation.
`create_temp_dir` creates a fresh, uniquely-named directory under the platform temp root.
`create_temp_file`, per the reference implementation, creates a FRESH temp DIRECTORY first and then
places the temp file inside it with a random-UUID-based name (`nodejs.ts:679-688`) -- i.e. every
temp FILE also gets its own private temp DIRECTORY, not merely a unique filename in a shared temp
directory. This creation SHAPE is adopted directly.

**Correction record (independent review, `L12-R003`):** an earlier revision of this section implied
that this shape means `cleanup()` "must also remove that file's own private directory." Confirmed
against pinned Pi directly that this is FALSE: `NodeExecutionEnv.cleanup()` (`nodejs.ts:691-694`)
does nothing with temporary files or directories at all -- it only kills active child processes and
clears its own tracked PID set. Pi's own test suite proves creation and suffix shape only; it does
not prove removal, and there is no pinned Pi evidence that either the temp file or its private
directory is ever automatically removed. This document therefore adopts ONLY the creation shape
above as DIRECT_PI_PARITY; it makes NO cleanup-obligation claim for temp resources at all, adopted
or otherwise -- `cleanup()`'s own scope is defined narrowly in §3.8 below, and does not extend to
them. A future implementation MAY choose to track and remove temp resources on cleanup as a
deliberate Minion-specific hardening, but that would be a new, separately-dispositioned
`MINION_EXTENSION`, not something this row adopts from Pi.

### 3.8 Cleanup

**DIRECT_PI_PARITY**, narrowly scoped. `cleanup()` releases the filesystem provider's OWN tracked
resources (matching pinned Pi's own `NodeExecutionEnv.cleanup()`, which tracks and kills active
child-process PIDs -- itself really a `ctx.subprocess`-owned concern this filesystem-facing method
happens to also expose, `nodejs.ts:691-694`) and MUST be best-effort -- it must never raise/reject
regardless of what it fails to clean up. It does NOT track or remove temporary files/directories
created via §3.7 (no pinned Pi evidence that it does).

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

**Correction record (independent review, `L12-R005`):** an earlier revision of this section left
the same-resource-identity rule underspecified enough that it was not implementable as a portable
equality key, and self-contradictory on symlink handling (it said a symlink and its target's own
identity "depend on whether the provider chooses to follow it," while separately requiring the
SAME underlying resource to always yield the SAME key -- a rule cannot simultaneously be
provider-discretionary and fixed). It also listed a content hash as a permitted backend mechanism,
which cannot actually satisfy the stated guarantee in either direction: two DIFFERENT files with
identical bytes would incorrectly collide to the SAME key (falsely appearing to be the same
resource), and editing ONE file's content would change ITS OWN key even though its resource
identity has not changed (violating "the same underlying resource... MUST resolve to the SAME
`target_key`" for the single most important case that guarantee exists for -- a file being
repeatedly mutated by a future Layer 13 serialization queue). Both defects are corrected below.

Binding requirements:

- **Symlink identity is fixed, not provider-discretionary.** `resolve(path)` identifies the
  resource a `canonical_path`-equivalent resolution of `path` would reach (§3.2) -- a symlink and
  its target therefore always share one `target_key`, for every provider, with no per-provider
  choice. This is a DELIBERATE, FIXED contract rule (not itself claimed as Pi parity, since Pi has
  no `target_key` concept to compare against), chosen specifically so the identity guarantee below
  cannot become provider-relative.
- **Same-resource identity survives mutation, not merely re-resolution.** The same underlying
  filesystem resource, reached through two syntactically different but semantically equivalent
  paths (a relative path and its resolved absolute form; a symlink and its target), MUST resolve to
  the SAME `target_key` -- INCLUDING before and after the resource's own content changes. A
  mechanism whose output depends on content (a content hash) is therefore explicitly EXCLUDED, not
  merely unspecified; permitted mechanisms are ones tied to the resource's own location/identity on
  the backing store (a canonical path string, a device+inode-equivalent pair, or another
  location-derived identifier), never one tied to content.
- **Provider/world scoping.** A `target_key` is meaningful only for comparison against other
  `target_key` values produced by the SAME provider instance. Two `target_key` values from
  DIFFERENT provider instances (even if by coincidence their opaque values happen to be equal, or
  even if the two providers are known to be execution-world-compatible per §7) MUST NOT be assumed
  to identify the same resource -- cross-provider resource identity is out of scope for this
  primitive; `process_path` (below) is the ONLY sanctioned cross-capability bridge, and it crosses
  from filesystem identity to a PROCESS-usable path, never from one filesystem provider's identity
  space into another's.
- **Stability and comparability.** Within one provider instance, `target_key` MUST support stable
  equality comparison for the resource's entire lifetime (two `resolve()` calls for the same
  resource, at different times, produce equal keys; two `resolve()` calls for different resources
  produce unequal keys) and MUST be usable as a hash-map/set key (stable hash consistent with
  equality) -- this is the exact requirement a future Layer 13 serialization queue needs to key
  its own per-resource queues on.
- **Not-yet-existing targets.** `resolve()` MUST succeed for a path that does not yet exist (a
  write/create operation's own future target) -- the mutation-serialization use case this bridge
  exists for explicitly requires serializing concurrent CREATE operations at the same not-yet-
  existing path, not only operations on already-existing resources. For a not-yet-existing path,
  `target_key` identifies the LOCATION a create/write at that exact path would resolve to (its
  canonicalized parent directory combined with the literal final path component, since there is no
  existing object to canonicalize through yet). A later `resolve()` call for the SAME path, once
  the resource exists, MUST produce an equal `target_key` (assuming no symlink was introduced at
  that location in the meantime) -- creation does not invalidate the identity a pre-creation
  `resolve()` already established.
- **Opacity.** `target_key` carries no promised syntax beyond the equality/hash contract above. A
  caller must not attempt to derive a filesystem path, a backend type, or any other structured
  meaning from it.
- **`process_path` ownership and foreign targets.** `process_path(target)` returns the path a
  process spawned in the CORRESPONDING execution world can open to reach the same resource. It
  MUST be called on the SAME provider instance that produced `target` (or one the caller has
  independently validated as execution-world-compatible via §7 -- that validation is the CALLER's
  responsibility, not this primitive's). A provider that can detect the target did not originate
  from itself or a compatible world MUST return a specific `FsError` (`invalid`) rather than
  fabricating a syntactically-plausible but meaningless path; a provider that cannot detect this
  (an opaque foreign key that happens to parse) is not required to detect it, but MUST NOT silently
  produce a path known to be wrong. This is the mechanism `bash`/edit-via-process (Layer 13's own
  future consumers) will use to hand a resolved target to a shell/subprocess command without
  re-resolving the path themselves and without the filesystem and process capabilities needing to
  agree on path syntax ahead of time.

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
never a validation exception (`nodejs.ts:38-49`). Killing a command, on either abort or timeout,
terminates its ENTIRE process tree/group, not merely the directly-spawned process -- a command
that itself backgrounds a child process does not leave that child running after the parent command
is killed (`nodejs.ts:253-276`, process-group kill on POSIX via a negative PID targeting the whole
group, falling back to single-PID kill if the group-kill itself fails; a tree-kill primitive on
Windows).

**Complete failure-precedence matrix (independent review, `L12-R007` -- an earlier revision of
this section stated only the mid-flight timeout-vs-abort ordering, not the full pre-spawn and
post-spawn sequence pinned Pi actually uses). Confirmed against `nodejs.ts:371-497`, checked in
this EXACT order:**

```text
1. Pre-aborted signal        -- checked FIRST, before timeout is even validated, before cwd is
                                 resolved, before a shell is resolved. A signal already aborted at
                                 call time short-circuits everything below.
2. Invalid timeout            -- validated next (finite, positive, within range); a validation
                                 failure here means no process is ever spawned.
3. cwd/shell resolution       -- the working directory existence check (§5.2) and shell resolution
                                 (§5.1) happen after 1-2 but before spawn.
4. [process runs]
5. On completion/interruption, exactly one of, in this precedence order:
       a. callback_error      -- a throwing onStdout/onStderr callback (§5.5) wins over everything
                                  below, even if a timeout or abort ALSO applies to the same call.
       b. timeout              -- if the timeout fired, classified `timeout` even if the signal
                                  also happened to be (or becomes) aborted.
       c. aborted              -- only when neither (a) nor (b) applies.
       d. success              -- `{stdout, stderr, exit_code}`, regardless of exit_code (§5.6).
```

An independent implementation MUST NOT guess any step of this ordering -- steps 1-3 determine
whether a process is ever spawned at all, and step 5's own ordering determines which single
classification a caller observes when multiple failure conditions are simultaneously true.

### 5.5 Streaming callbacks and callback-error propagation

**DIRECT_PI_PARITY.** `on_stdout`/`on_stderr`, when provided, are invoked with each chunk as it
arrives, in addition to (not instead of) accumulating the FULL stdout/stderr the final `Result`
carries -- a caller does not have to choose between streaming and the final aggregate. If either
callback itself raises, the raised failure is classified `callback_error`, and the in-flight
command is killed as a side effect of that classification (§2.2) -- a throwing callback is not
merely skipped or logged. `callback_error` takes precedence over every other classification (§5.4).

### 5.6 Result shape and completion

**DIRECT_PI_PARITY.** A successful `exec()` returns `{stdout, stderr, exit_code}` regardless of
whether `exit_code` is zero -- a non-zero exit is NOT itself a `Result` failure at the `ctx.shell`
seam; classifying a non-zero exit as a tool-level failure (as the future `bash` built-in tool does)
is Layer 13's own concern, not this seam's.

**Correction record (independent review, `L12-R007`):** an earlier revision of §6 (`ctx.subprocess`)
described `ctx.shell`'s own completion discipline as requiring stdio to "fully drain," which reads
as a guarantee to wait for full pipe EOF. Confirmed against pinned Pi directly that this
overstates the actual mechanism: `waitForChildProcess` (`nodejs.ts:278-345`) arms a short idle-grace
timer once the process itself exits, and finalizes -- destroying the stdout/stderr streams -- once
that timer fires, EVEN IF a detached descendant process still holds the inherited stdio pipes open
(a pinned Windows-only regression test, `nodejs-env.test.ts:379-400`, exists specifically to prove
the call settles in exactly this scenario rather than hanging forever waiting for true EOF). The
actual rule: `exec()` completes once the DIRECTLY-SPAWNED process has exited AND a short idle
period has elapsed with no further stdout/stderr activity from it -- not once every inherited pipe
descriptor, including ones held by unrelated detached descendants, has reached EOF. §6.3 restates
this correctly for `ctx.subprocess`'s own `wait()`.

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
stream handling, process-group kill on timeout/abort, idle-grace completion, §5.6), which is
exactly the primitive set a `ctx.subprocess` seam would need to expose for `ctx.shell`'s own local
provider to be built from it rather than duplicating it.

**Correction record (independent review, `L12-R006`):** an earlier revision of this section
proposed a shape ("stdin, if requested" with no actual request parameter; raw streams with no
defined read/write/close operations or error boundary; no stdio configuration, cancellation-vs-
termination `wait()` semantics, repeated-call idempotence, ownership/disposal, or chunk-type
specification) that left two independent, both-plausible Rust implementations able to expose
genuinely different observable behavior. The complete contract below replaces it.

```text
StdioMode = inherit | piped | null
    -- inherit: shares the parent process's own file descriptor
    -- piped:   exposes a readable/writable stream on the returned Process
    -- null:    discarded (stdin) / not captured (stdout, stderr)

SpawnOptions{
    cwd?, env?, inherit_env=True,
    stdin: StdioMode = null,
    stdout: StdioMode = piped,
    stderr: StdioMode = piped,
    signal?,
}
    -- defaults match ctx.shell's own local-provider spawn shape (no stdin unless requested;
       stdout/stderr piped so they can be captured), not an arbitrary choice.

spawn(argv, options?: SpawnOptions) -> Result[Process, SubprocessError]

Process
    pid
    stdin: WritableStream | None     -- present only when stdin=piped was requested
    stdout: ReadableStream | None    -- present only when stdout=piped was requested
    stderr: ReadableStream | None    -- present only when stderr=piped was requested
    wait(signal?) -> Result[ExitStatus, SubprocessError]
    terminate() -> None              -- best-effort, must not raise, idempotent

ExitStatus{exit_code: int | None}
    -- exit_code is None when the process was killed (via terminate() or a wait()-supplied signal)
       before it produced a normal exit code

WritableStream
    write(data: bytes) -> Result[None, SubprocessError]
    close() -> None                  -- best-effort, signals EOF to the child's own stdin; must
                                         not raise; idempotent

ReadableStream
    read_chunk() -> Result[bytes | None, SubprocessError]   -- None chunk means EOF
```

Binding requirements:

- **`argv`-direct only.** `spawn` takes an argument VECTOR, never a command string. The seam MUST
  NOT shell-interpret its arguments under any circumstance -- no quoting/globbing/variable
  expansion/pipeline syntax is ever applied to `argv` elements. A caller that wants shell semantics
  explicitly invokes `ctx.shell` instead; `ctx.subprocess` never does this implicitly on a caller's
  behalf, regardless of what the command looks like.
- **Stdio configuration.** Every stream defaults per `SpawnOptions` above; `Process`'s own
  `stdin`/`stdout`/`stderr` fields are populated ONLY for streams configured `piped` -- a caller
  reads its own configuration, not a runtime check, to know which fields exist.
- **Chunk type.** Stream chunks are raw `bytes`, never decoded text -- unlike `ctx.shell`'s own
  higher-level `exec()` (which returns decoded text since it is explicitly a shell-command-output
  primitive), `ctx.subprocess` is the lower-level, protocol-agnostic primitive; a caller speaking a
  binary/framed protocol (MCP over stdio, an LSP's own JSON-RPC framing) owns its own decoding.
- **Pre-aborted vs. post-spawn signal.** A pre-aborted `signal` supplied to `spawn()` MUST
  short-circuit before any process is started, returning `aborted` -- matching `ctx.shell`'s own
  §5.4 step-1 precedent. A signal that aborts AFTER the process has started triggers termination
  (below); its effect on `wait()`'s own return value is defined next.
- **`wait()` after cancellation vs. `terminate()`.** These are classified DIFFERENTLY, deliberately:
  a `wait(signal)` call whose OWN signal argument triggers the kill returns the `aborted` error
  (matching `ctx.shell`'s own precedent that caller-external cancellation is a `Result` failure);
  an explicit `terminate()` call with NO signal involved is the caller's OWN deliberate action, not
  an unexpected failure, so the subsequent `wait()` returns SUCCESS with `ExitStatus{exit_code:
  None}` -- the caller asked for this outcome, so it is not reported as an error. If both occur
  (a signal fires and the caller also calls `terminate()`), whichever caused the actual kill first
  determines the classification; a `terminate()` racing a signal that already fired is a no-op
  (idempotence, below) and does not change the classification the signal already established.
- **Idempotence.** `wait()` is safe to call repeatedly and/or concurrently; once the process has
  settled, every call (past or still in flight) returns the SAME result. `terminate()` is safe to
  call repeatedly, including after the process has already exited or already been terminated --
  every call after the first is a no-op, matching `cleanup()`'s own best-effort/never-raise
  discipline (§3.8, §5).
- **Process/stream ownership and disposal.** A `Process` value OWNS its own stdio handles and
  underlying OS process handle. Dropping/disposing a `Process` without having called `wait()` or
  `terminate()` MUST NOT leak the OS process -- implicit disposal (a Python context-manager
  `__aexit__`, a Rust `Drop`) SHOULD attempt best-effort termination, though callers SHOULD prefer
  an explicit `terminate()`/`wait()` rather than relying on it.
- **Pipe failures are independent of process-lifecycle status.** A pipe read/write failure is
  observed AT THE POINT OF THAT OPERATION (`read_chunk()`/`write()` itself returns a `pipe_error`
  `Result`) and does NOT itself change what `wait()` eventually returns -- `wait()` reports the
  PROCESS's own exit/termination status only, independent of whether its stdio streams separately
  experienced an I/O error. The two failure domains are deliberately kept apart.
- **Termination/cancellation kills the whole tree.** `terminate()` and signal-triggered
  cancellation both kill the whole process tree/group where the platform supports it, matching
  `ctx.shell`'s own §5.4 guarantee -- this is the SAME underlying mechanism `ctx.shell`'s local
  provider is built from, so the guarantee must genuinely be shared, not merely similarly worded.
- **Spawn failures.** A failure to start the process at all (binary not found, not executable,
  working directory missing) is a `Result` failure classified `spawn_error`, never an exception.

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

## 9. Remediation record

This is a confirmed contract-first-checkpoint candidate (`agent-workflow.md` §4.1): the surface
combines direct Pi parity, deliberate Minion architectural mappings, three separate error domains,
a genuinely new cross-provider compatibility mechanism, resource identity, cancellation, raw
process lifecycle, and local-provider normalization, with several interacting dimensions whose
cross-product matters.

The first candidate (code `1018f5d2478c0de1ed5c086389e109c8d5e6222a`, docs
`922243d6f747186c4a895dea5830fa755ef2c011`) was independently reviewed and REJECTED
(`minion-agent-docs#111`, review commit `092f63a5e3136f598fe1e508d4c60f6d8fe4dc17`) with eight
findings, `L12-R001` through `L12-R008`. Every finding was independently re-verified against
pinned Pi source, the pinned Pi test suite, or existing manifest precedent before being accepted --
none was taken on the review's own prose alone. All eight were confirmed substantively correct.
Disposition of each, all resolved in this candidate:

```text
L12-R001  PI_BEHAVIOR_UNCERTAIN    cancellation gap much broader than append_file alone
    -> RESOLVED: §3.1 (new), explicit sourcing decision (interface over reference
       implementation) plus the full per-operation table.

L12-R002  PI_PARITY_DEFECT          "only canonical_path follows symlinks" is false
    -> RESOLVED: §3.2, corrected per-operation-class (lexical resolution never touches the
       filesystem; lstat-based metadata never follows; canonical_path always follows;
       ordinary content I/O follows because the underlying OS open()/rename() does).

L12-R003  CONTRACT_ASSURANCE_DEFECT  temp-cleanup and "no consumer alone" overstatements
    -> RESOLVED: §3.7/§3.8 (cleanup makes no temp-resource claim at all); §1 (narrowed to
       "Pi's own execution tools require the combination," with JsonlSessionRepoFileSystem
       cited as the direct counter-example to the old blanket claim).

L12-R004  CONTRACT_ASSURANCE_DEFECT  Result/error rule self-contradictory and under-mapped
    -> RESOLVED: §2 (removed "non-zero process exit"/"stale version"/"remote unavailable"
       from the Values list; stated the rule applies per-operation, not uniformly; §2.1-§2.3
       are now the sole taxonomy source).

L12-R005  CONTRACT_ASSURANCE_DEFECT  FsTarget identity not implementable as written
    -> RESOLVED: §4, full rewrite -- fixed (non-provider-discretionary) symlink identity,
       content-hash mechanism explicitly excluded, provider/world scoping, equality/hash
       requirement, not-yet-existing-target behavior, process_path ownership and foreign-
       target failure mode.

L12-R006  CONTRACT_ASSURANCE_DEFECT  subprocess capability not a complete process/stream contract
    -> RESOLVED: §6, full rewrite -- stdio configuration, typed stream operations, pre-
       aborted-vs-post-spawn signal behavior, wait()-after-cancellation-vs-terminate()
       classification, repeated-call idempotence, ownership/disposal, chunk type, pipe-
       failure/wait() independence; timeout removed from SubprocessErrorCode (§2.3).

L12-R007  PI_PARITY_DEFECT          shell completion and failure precedence incomplete/overstated
    -> RESOLVED: §5.4 (full pre-spawn/post-spawn precedence matrix), §5.6 (corrected
       "fully draining" to the actual idle-grace-after-exit mechanism, citing the pinned
       Windows regression test that exists specifically to prove non-EOF-wait settlement).

L12-R008  CONTRACT_ASSURANCE_DEFECT  manifest subjects/dispositions incoherent
    -> RESOLVED: companion minion-agent PR -- EXEC-001 split (SubprocessErrorCode moved into
       EXEC-005); EXEC-003/EXEC-005/EXEC-006 redispositioned intentional divergence, matching
       existing manifest precedent (MINION-001/002) for Minion-only surfaces with no Pi
       equivalent; EXEC-002's PI_BEHAVIOR_UNCERTAIN resolved by L12-R001 above, so `adopted`
       is correct again, not a lingering contradiction.
```

Per the standard flow (`agent-workflow.md` §4.1): this remediated draft is ready for a fresh
independent Pi audit of the exact new candidate SHA. An explicit `AGREED FOR IMPLEMENTATION`
checkpoint is still required before Python implementation begins. No Python implementation is
authorized by this document alone.

## 10. Discriminating behavior/witness matrix

Per the review's own required correction ("add the checkpoint behavior/witness matrix"). No
executable implementation exists yet, so these are PREDICTED observable outcomes stated precisely
enough to become real regression tests once implementation begins -- not yet executed evidence.

```text
CANCELLATION (§3.1)
    setup:    an existing file; a pre-aborted signal
    call:     file_info(path, signal) on the Minion contract (not pinned Pi's own reference impl)
    expected: Result.Err(FsError(aborted)) -- the operation never touches the filesystem
    contrast: pinned Pi's own NodeExecutionEnv.fileInfo has no signal parameter at all and would
              succeed; this is the exact point where Minion's contract deliberately diverges from
              Pi's own incompletely-conforming reference implementation, per §3.1's sourcing
              decision -- the witness must assert against MINION's stated contract, not Pi's.

SYMLINK FOLLOWING (§3.2)
    setup:    target.txt with content "X"; link.txt symlinked to target.txt
    call A:   read_text_file("link.txt")
    expected: Ok("X") -- content I/O follows the symlink
    call B:   file_info("link.txt")
    expected: Ok(FileInfo{kind: symlink, ...}) -- lstat-based metadata does not

SHELL FAILURE PRECEDENCE (§5.4)
    setup:    a command whose onStdout callback raises, AND whose timeout also elapses
    expected: Result.Err(ShellError(callback_error)) -- callback_error wins over timeout even
              though both conditions are true

SHELL COMPLETION (§5.6)
    setup:    a command that exits while a detached descendant still holds inherited stdio open
    expected: exec() settles (does not hang) once the direct child exits plus a short idle grace
              period -- not once the detached descendant's own pipe reaches EOF

PROCESS WAIT VS. TERMINATE (§6)
    setup:    a running process; caller calls terminate() with no signal involved
    expected: wait() returns Ok(ExitStatus{exit_code: None})
    contrast: same process, but a caller-supplied signal (not terminate()) triggers the kill
    expected: wait() returns Err(SubprocessError(aborted)) -- same underlying kill mechanism,
              deliberately different classification depending on WHO initiated it

PIPE FAILURE INDEPENDENCE (§6)
    setup:    a process whose stdout pipe experiences a read failure mid-execution, but which
              itself exits normally with code 0
    expected: the failing read_chunk() call returns Err(SubprocessError(pipe_error)); a
              concurrent/subsequent wait() still returns Ok(ExitStatus{exit_code: 0}) -- the pipe
              failure does not propagate into the process-lifecycle result

TARGET IDENTITY SURVIVES MUTATION (§4)
    setup:    resolve("file.txt") -> target_key K1; write_file("file.txt", new content);
              resolve("file.txt") again -> target_key K2
    expected: K1 == K2 -- a content-hash-based mechanism would fail this witness (K1 != K2 after
              the write), which is exactly why §4 excludes content hashing as a permitted
              mechanism

TARGET IDENTITY DOES NOT COLLIDE ACROSS DISTINCT RESOURCES (§4)
    setup:    a.txt and b.txt, two distinct files with byte-identical content "same"
    expected: resolve("a.txt").target_key != resolve("b.txt").target_key -- a content-hash-based
              mechanism would fail this witness too (both files would hash identically)

EXECUTION-WORLD COMPATIBILITY (§7)
    setup:    two synthetic providers declaring different execution-world identities; a synthetic
              consumer requiring both to address the same resource
    expected: the consumer's own activation-time validation fails with a diagnostic naming the
              incompatible providers; a DIFFERENT synthetic consumer needing only one of the two
              capabilities activates successfully alongside the same mismatched pairing
```
