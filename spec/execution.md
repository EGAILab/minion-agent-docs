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

### 3.1 Cancellation (independent review, `L12-R001`/`L12-R008` -- resolved in convergence episode
`CE-L12-01-01`, `minion-agent-docs#113`)

An earlier revision of this document flagged only `append_file`'s missing `signal` handling as
`PI_BEHAVIOR_UNCERTAIN`. Independent review found the SAME gap on TEN of sixteen `FileSystem`
methods, not one, and not nine (an earlier remediation's own prose miscounted its own adjacent
list): pinned Pi's own `FileSystem` INTERFACE (`types.ts:222-283`) declares `signal?` on every
operation, but pinned Pi's own harness-tier REFERENCE IMPLEMENTATION (`NodeExecutionEnv`,
`nodejs.ts`) does not actually accept or check it on `absolute_path`, `join_path`, `append_file`,
`file_info`, `canonical_path`, `exists`, `create_dir`, `remove`, `create_temp_dir`, or
`create_temp_file` at all -- confirmed directly by reading each method's own concrete signature.

**Sourcing decision (reversed at convergence):** an earlier revision of this section chose to
adopt pinned Pi's own INTERFACE-declared contract -- every operation accepting and checking
`signal` -- as a stricter `MINION_ARCHITECTURAL_MAPPING`. Convergence review found this was an
UNAPPROVED intentional divergence: this project's own established epistemology treats live,
OBSERVED behavior as the authoritative definition of "Pi behavior," never a type declaration's
unfulfilled promise, without exception, elsewhere in this same document (§3.5's rename semantics,
§3.7's cleanup scope, §5.6's completion rule all follow the reference implementation over the
interface where they differ). Cancellation gets no special exception. Minion therefore adopts
pinned Pi's own OBSERVABLE reference-implementation cancellation behavior exactly, including its
incompleteness, as **DIRECT_PI_PARITY** -- not the fuller interface promise. Choosing the fuller
interface instead would itself have been the divergence requiring its own owner escalation
(`agent-workflow.md` §11.7) that no governance record grants.

**Public API shape (refined at `L12-R001`, targeted closure review, `minion-agent-docs#114`):** the
operation inventory (§3 above) declares `signal?` on EVERY operation, including the ten listed
below -- matching pinned Pi's own `FileSystem` INTERFACE shape exactly (`types.ts:222-283`, which
also declares `signal?` uniformly). This is a single, explicit, DELIBERATE decision about the
PUBLIC TYPED API surface, kept separate from the decision about OBSERVABLE BEHAVIOR below: every
`ctx.fs` operation ACCEPTS an optional `signal` argument (a uniform seam-wide signature, easy for a
caller to use consistently without checking which operations happen to support it); whether that
argument is INSPECTED is a separate, per-operation fact, stated in the table below. For the ten
operations in the "does not inspect" group, `signal` is accepted (the call compiles/type-checks
and is a normal, successful call) but has NO effect on that operation's own behavior -- there is no
operation in this contract whose typed signature omits the parameter; there is no operation that
raises or errors merely for being passed one it does not inspect. A Rust implementation exposes
this as an ordinary `Option<&CancelToken>` (or equivalent) parameter on every trait method, unused
in the body for the ten listed operations -- not a second, narrower trait shape.

**Binding per-operation table** (firm requirement, matching pinned Pi's own reference
implementation exactly -- no "SHOULD" advisory language, no Minion-added cancellation checkpoint
beyond what Pi itself observably performs; refined at `L12-R009`, final complete review,
`minion-agent-docs#114`, CE-L12-01-02 -- the checkpoint COUNT and ORDER per operation, not merely a
pre-aborted/mid-operation binary):

```text
read_text_file, read_binary_file:
    checks pre-aborted; signal threaded into the single underlying read call (nodejs.ts:502-511,
    544-553) -- a single-phase operation, no separate checkpoint beyond that.

write_file:
    checks pre-aborted; awaits recursive parent mkdir (itself NOT abort-checked); checks AGAIN
    immediately after mkdir completes, before the write begins; signal also threaded into the
    underlying write call (nodejs.ts:555-572) -- THREE checkpoints, not one.

read_text_lines:
    checks pre-aborted (before opening the read stream); signal passed to the underlying stream;
    re-checks at EACH loop iteration (once per yielded line); checks ONCE MORE after the loop
    completes, before returning success (nodejs.ts:513-542) -- FOUR checkpoints.

list_dir:
    checks pre-aborted; re-checks at each loop iteration (once per directory entry); NO check
    after the loop completes (nodejs.ts:611-633) -- genuinely FEWER checkpoints than
    read_text_lines, despite both superficially "looping over entries."

rename_file:
    checks pre-aborted only; the underlying rename() call accepts no signal option at all
    (nodejs.ts:585-600) -- no mid-operation checkpoint of any kind.

accepts signal (uniform typed API, per above) but does NOT inspect it -- a pre-aborted or
live signal has no effect; the call always proceeds normally -- MATCHES Pi exactly, not a
Minion gap:
    absolute_path, join_path, append_file, file_info, canonical_path, exists, create_dir,
    remove, create_temp_dir, create_temp_file
```

This resolves `L12-R008` as a direct consequence: `EXEC-002` (the manifest row covering `ctx.fs`)
is coherently `adopted` in full -- there is no divergence bundled into it at all, so no split
disposition or `PI_BEHAVIOR_UNCERTAIN` flag is needed.

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
`writeFile`/`appendFile` from `node:fs/promises`, with no `O_NOFOLLOW`-equivalent flag) traverse a
symlink at its final path component exactly as the OS's own `open()` would. The non-following
guarantee is real, but it applies to a NARROWER set of operations than the earlier text claimed.

**Second correction record (convergence episode `CE-L12-01-01`, `minion-agent-docs#113`):** the
first remediation's own fix above then MISCLASSIFIED `rename_file` as ordinary symlink-following
content I/O, and omitted `remove` from the matrix entirely. Confirmed directly against pinned Pi:
`renameFile` calls Node's raw `rename(source, destination)` (`nodejs.ts:594`) and `remove` calls
raw `rm(resolved, {recursive, force})` (`nodejs.ts:664`) -- both direct OS-primitive wrappers with
no dereferencing flag. Standard POSIX semantics apply: `rename()` operates on the SOURCE directory
entry itself, never its target (confirmed by an executable witness: `target.txt="X"`, `link.txt ->
target.txt`, `rename_file("link.txt", "moved.txt")` leaves `target.txt` unchanged and produces a
`moved.txt` that is ITSELF a symlink, per §5's `L12-R002` witness); `rm()`/`unlink()` on a symlink
removes the link entry, and recursive removal of a directory-symlink does not recurse into the
target directory's own contents. Corrected, complete per-operation-class matrix:

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
  `append_file`) -- **DOES follow a symlink at its final path component**, matching the underlying
  OS `open()` semantics these operations are built on (`readFile`/`writeFile`/`appendFile` from
  `node:fs/promises`, `nodejs.ts:502-577`, none of which passes any no-follow flag). Reading through
  a symlink returns the TARGET's own content; writing/appending through a symlink mutates the
  TARGET, not the link itself.
- **`rename_file`** -- **NEVER traverses.** Operates on the SOURCE directory entry itself (the link
  object, if the source is a symlink) -- it renames/moves the LINK, not its target. If the
  destination already exists, `rename_file` replaces the destination's own directory entry, not a
  target that entry might itself point to.
- **`remove`** -- **NEVER traverses.** Removes the addressed symlink itself. Recursive removal of a
  directory-symlink removes the link only; it never recurses into the target directory's own
  contents. Safety-relevant: this is the guarantee a caller relies on to avoid an accidental
  cascading delete through a link.
- **`create_dir` through an existing symlink** -- follows platform `mkdir` semantics at the existing
  prefix (a symlinked parent directory in the path is transparently traversed by the OS's own path
  resolution, the same as any other program's `mkdir -p` would observe); no separate Minion rule
  beyond what the underlying OS primitive already does.

The distinction that survives is: path resolution never traverses symlinks (nothing to traverse --
it never touches the filesystem), metadata never traverses symlinks (deliberately, via `lstat`),
canonicalization always traverses symlinks (that is its entire job), ordinary content I/O traverses
symlinks because the OS primitives underneath it do, and `rename_file`/`remove` never traverse
because they operate on the addressed directory entry itself, matching raw POSIX `rename()`/`rm()`
semantics exactly -- none of this is symlink-following logic this seam adds on its own.

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

**Cancellation:** `append_file` accepts `signal` (the uniform typed API, §3.1) but does not
inspect it -- it matches pinned Pi's own reference implementation exactly (§3.1's table), not a
Minion gap.

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

**Correction record (refined at `L12-R017`, second final complete review, `minion-agent-docs#114`,
CE-L12-01-03):** an earlier revision of this section attributed pinned Pi's own combined
`NodeExecutionEnv.cleanup()` child-process-killing behavior to `ctx.fs`'s own `cleanup()`. That
misattributes Pi's COMBINED environment's behavior to the wrong split provider: in Pi's own
unsplit `ExecutionEnv`, `cleanup()` kills active children because `exec()`'s own spawned child
shares the SAME `activeChildPids` tracking set that `cleanup()` iterates (`nodejs.ts:429,691-694`)
-- a `ctx.shell`-owned concern, not a `ctx.fs`-owned one. Corrected: `ctx.fs.cleanup()` makes NO
child-process claim at all. `ctx.shell`'s own active-command cleanup is specified in §5.

**DIRECT_PI_PARITY**, narrowly scoped. `cleanup()` MUST be best-effort -- it must never raise/
reject regardless of what it fails to clean up. It currently has no OTHER observable effect: it
does NOT track or remove temporary files/directories created via §3.7 (no pinned Pi evidence that
it does), and it does NOT track or kill child processes (that is `ctx.shell`'s own concern, §5) --
a conforming `ctx.fs.cleanup()` MAY be a true no-op.

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
identical bytes would incorrectly collide to the SAME key, and editing ONE file's content would
change ITS OWN key even though its resource identity has not changed.

**Second correction record (convergence episode `CE-L12-01-01`, `minion-agent-docs#113`):** the
first remediation's own fix above then required BOTH "survives rename" (a resource-identity
property) AND "not-yet-existing-target support" (a location-identity property) from ONE mechanism
-- a genuine logical impossibility, not a wording nitpick: a device+inode-equivalent pair can
satisfy the former but cannot predict a future inode for a path that does not exist yet; a
canonical-path string can satisfy the latter but changes on rename. Resolved by re-reading pinned
Pi's own REAL mutation-queue keying mechanism (`file-mutation-queue.ts:20-26`,
`getMutationQueueKey`): it is a canonical-path STRING, falling back to the absolute path when
canonicalization fails (the not-yet-existing-path case) -- genuinely LOCATION-based, and NOT
designed to survive rename at all. `target_key` adopts this same model as
**MINION_ARCHITECTURAL_MAPPING**: it preserves the OBSERVABLE guarantee Pi's own queue relies on
(stable, comparable keys for read-before-edit/version-guarded-write checks) using Minion's own
`FsTarget` shape, without inventing a stronger rename-survival requirement Pi's own real mechanism
never provides and a future Layer 13 queue never actually needs (Pi's own queue simply treats a
renamed file's old and new paths as unrelated queue keys, and that is safe, not a defect).

```text
resolve(path) -> target_key = canonical_path(path) if it exists, else absolute_path(path)
    -- mirrors Pi's own getMutationQueueKey exactly, including the not-yet-existing fallback
```

**Exact fallback condition (refined at `L12-R016`, second final complete review,
`minion-agent-docs#114`, CE-L12-01-03 -- the prose above ("if it exists" / "when canonicalization
fails") does not commit to a precise condition, permitting mutually different Rust
implementations).** `absolute_path` is used ONLY when `canonical_path` fails with error code
`not_found` or `not_supported`. Any OTHER `canonical_path` failure (`permission_denied`,
`invalid`, `not_directory`, `is_directory`, `unknown`) PROPAGATES as `resolve()`'s own `FsError` --
`resolve()` does NOT silently fall back to `absolute_path` for those cases. This is
`DIRECT_PI_PARITY`: pinned Pi's own `getMutationQueueKey` (`file-mutation-queue.ts:20-26`) falls
back for exactly these two codes and re-throws (propagates) for any other.

**`resolve()`'s own cancellation classification (refined at `L12-R016`, CE-L12-01-03).**
`resolve(path, signal?)` is in the accepts-but-does-not-inspect group (§3.1) -- a direct
consequence of composing two operations (`absolute_path`, `canonical_path`) that are BOTH already
in that group; a pre-aborted or live `signal` has no effect on `resolve()`'s own outcome.

Binding requirements:

- **Symlink identity is fixed when canonicalization succeeds -- not provider-discretionary, but not
  unconditional either (refined at `L12-R018`, third final complete review,
  `minion-agent-docs#114`, convergence episode `CE-L12-01-04`; narrowed per the `agent-workflow.md`
  §11.10 governance decision recorded in `minion-agent-docs#117`).** An earlier revision of this
  bullet claimed the symlink/target key-sharing guarantee holds UNCONDITIONALLY, for every
  provider, with no exception. That contradicts the exact fallback condition (§4 above,
  `not_found`/`not_supported` only): a provider whose `canonical_path` returns `not_supported` for
  every path falls back to LEXICAL `absolute_path` for both a symlink and its target -- two
  different lexical paths, hence two DIFFERENT `target_key` values, even though the symlink
  addresses the target. Corrected: `resolve(path)` identifies the resource a
  `canonical_path`-equivalent resolution of `path` would reach (§3.2) WHEN `canonical_path`
  succeeds -- a symlink and its target therefore share one `target_key` for every
  canonicalization-CAPABLE provider (every provider this row currently certifies; pinned Pi's own
  local reference implementation's `toFileError` never produces `not_supported` at all,
  `nodejs.ts:97-121`, so this narrowing has no effect on any current provider). A provider whose
  `canonical_path` is unsupported is explicitly NOT required to alias-unify a symlink with its
  target -- a documented provider limitation, not a contract violation; a future Layer 13 consumer
  relying on alias unification for correctness must not depend on it when paired with such a
  provider. This is still not a separate rule layered on top of §3.2's own resolution -- it falls
  out of the SAME `canonical_path`-based derivation, conditioned on that derivation actually
  succeeding.
- **Location, not resource, is the identity.** `target_key` identifies a PATH's resolved location,
  not an underlying inode/resource. Content mutation in place leaves `target_key` unchanged (same
  path, same canonicalization). Renaming `a` to `b` CHANGES the `target_key` (`a` and `b` are
  different canonical paths) -- this is CORRECT, not a defect: Pi's own real queue does the same.
  Deleting `a` and creating a new, unrelated file also named `a` REUSES the same `target_key` as
  the old `a`, PROVIDED no ancestor directory component of `a`'s path is or becomes a symlink in
  between (see the not-yet-existing-target bullet below for the case where it is) -- when it holds,
  this reuse is correct and safe: serializing the new file's own operations against the same queue
  key the old file used is conservative, never wrong. A mechanism whose output depends on content (a
  content hash) or on a device+inode-equivalent pair is explicitly EXCLUDED, not merely unspecified
  -- a content hash fails the content-mutation-stability case above and collides across distinct
  files with identical bytes; a device+inode pair cannot satisfy the not-yet-existing-path case
  below. Canonical-path-string (falling back to absolute-path) is the ONE specified mechanism, not
  one option among several.
- **Provider/world scoping.** A `target_key` is meaningful only for comparison against other
  `target_key` values produced by the SAME provider instance. Two `target_key` values from
  DIFFERENT provider instances (even if by coincidence their opaque values happen to be equal, or
  even if the two providers are known to be execution-world-compatible per §7) MUST NOT be assumed
  to identify the same resource -- cross-provider resource identity is out of scope for this
  primitive; `process_path` (below) is the ONLY sanctioned cross-capability bridge, and it crosses
  from filesystem identity to a PROCESS-usable path, never from one filesystem provider's identity
  space into another's.
- **Stability and comparability.** Within one provider instance, `target_key` MUST support stable
  equality comparison for the resource's entire lifetime under the location-based rule above (two
  `resolve()` calls that reach the SAME resolved location, per the derivation above, produce equal
  keys -- this is how a symlink and its target correctly share one key despite being syntactically
  different paths, per the symlink-identity bullet above; two `resolve()` calls that reach
  DIFFERENT resolved locations produce unequal keys, even if their content happens to be
  byte-identical) and MUST be usable as a hash-map/set key (stable hash consistent with equality).
  ("Different paths" alone is not the right test -- two DIFFERENT syntactic paths can resolve to
  the SAME location, as the symlink case shows; it is the RESOLVED LOCATION that must match for
  keys to be equal.)
- **Not-yet-existing targets, and the symlinked-ancestor exception (refined at `L12-R005`,
  targeted closure review, `minion-agent-docs#114`).** `resolve()` MUST succeed for a path that does
  not yet exist (a write/create operation's own future target) -- the mutation-serialization use
  case this bridge exists for explicitly requires serializing concurrent CREATE operations at the
  same not-yet-existing path, not only operations on already-existing resources. Per the derivation
  above, a not-yet-existing path's `target_key` is its `absolute_path` (the canonicalization
  fallback) -- a PURELY LEXICAL value that does NOT resolve any symlink, including one in an
  ANCESTOR directory component of the path. A later `resolve()` call for the SAME path, once the
  resource exists, uses `canonical_path`, which DOES resolve every symlink component, ancestors
  included (`realpath`-equivalent, confirmed against `nodejs.ts:635-642`). For an ordinary path
  with no symlinked ancestor, these two forms coincide, so the `target_key` is stable across
  creation. **For a path whose ancestor directory is (or becomes) a symlink, they do NOT coincide,
  and `target_key` CHANGES across creation** -- confirmed by direct reasoning about `realpath`
  semantics and reproduced with an executable witness (§10): `resolve("link/new.txt")` before
  `new.txt` exists (`link` a symlink to `real`) yields the lexical `.../link/new.txt`; after
  creating the file through `link`, `resolve("link/new.txt")` yields the canonicalized
  `.../real/new.txt` -- unequal. This is NOT a Minion-introduced defect: pinned Pi's own real
  `getMutationQueueKey` calls the exact same `absolutePath`/`canonicalPath` pair in the exact same
  fallback order (`file-mutation-queue.ts:20-26`), so Pi's own real mutation queue has this
  identical property. `target_key` adopts Pi's OBSERVABLE behavior here exactly, including this
  instability, rather than inventing a stronger cross-creation guarantee Pi's own real mechanism
  does not provide -- consistent with this document's own cancellation sourcing decision (§3.1):
  Minion does not silently strengthen an incomplete Pi mechanism into an idealized promise. A
  caller that needs stability through creation under a symlinked ancestor must not create through
  a symlinked ancestor, or must re-`resolve()` after creation and treat the two keys as
  potentially different.
- **Opacity.** `target_key` carries no promised syntax beyond the equality/hash contract above. A
  caller must not attempt to derive a filesystem path, a backend type, or any other structured
  meaning from it.
- **`process_path` scoped to the producing provider only (refined at `L12-R014`, final complete
  review, `minion-agent-docs#114`, CE-L12-01-02; second correction, targeted closure review,
  `minion-agent-docs#114`, CE-L12-01-02).** An earlier revision of this bullet permitted
  `process_path(target)` to be called on the producing provider "or one the caller has
  independently validated as execution-world-compatible via §7." That contradicted this section's
  own provider/world-scoping rule above (`target_key` is meaningful only within the producing
  provider instance): execution-world compatibility (§7) is a statement about whether a RESULTING
  PATH STRING is meaningful across providers, not a grant of authority for a SECOND provider to
  decode the FIRST provider's own opaque `target_key`. Corrected: `process_path(target)` MUST be
  called on the SAME provider instance that produced `target` -- no exception.

  A first fix then stated calling it on any other provider is "OUTSIDE this contract (undefined)"
  while, two sentences later, ALSO requiring a detecting provider to "return a specific `FsError`
  (`invalid`)" -- two incompatible classifications for the identical call (one implementation
  could type/provenance-gate the call as unrepresentable; another could accept the call and return
  `invalid`; both cannot be the one contract). Corrected to ONE rule: calling `process_path` on any
  provider instance other than the one that produced `target` is UNIFORMLY undefined -- a caller
  bug, not a case with its own required `Result`. A provider MAY, as a best-effort diagnostic,
  detect foreign provenance and return `FsError(invalid)` rather than fabricating a wrong path, but
  this is explicitly NOT required -- a provider that cannot detect it (an opaque foreign key that
  happens to parse) is free to do anything, including producing a meaningless path, since the
  caller has already violated the contract by calling on the wrong provider instance in the first
  place. There is no longer a MUST anywhere in this bullet for the foreign-provider case; the
  return-invalid behavior is optional, best-effort hardening a provider MAY choose to implement,
  never a normative requirement a caller may rely on.

  The cross-seam workflow this bridge exists for is: `resolve()` and `process_path()` both happen
  on the ORIGINATING `ctx.fs` provider; the resulting PATH STRING (never the `FsTarget`, never the
  `target_key` itself) is what gets handed to a `ctx.shell`/`ctx.subprocess` provider independently
  validated as execution-world-compatible (§7) with that SAME `ctx.fs` provider -- world
  compatibility justifies trusting the resulting STRING is meaningful to that shell/subprocess
  provider; it never grants decode authority over another provider's own key. This is the
  mechanism `bash`/edit-via-process (Layer 13's own future consumers) will use to hand a resolved
  target to a
  shell/subprocess command without re-resolving the path themselves and without the filesystem and
  process capabilities needing to agree on path syntax ahead of time.

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
This check happens AFTER shell discovery (§5.1), not before -- see §5.4's exact six-step
pre-spawn order for the full, exact sequence.

### 5.3 Environment

**DIRECT_PI_PARITY.** `inherit_env` defaults to `True`. When `True`, the effective environment is
the seam provider's own default environment (its own inherited/base environment) overlaid by any
per-call `env`. When `False`, the effective environment is EXACTLY the per-call `env` and nothing
else -- no inherited variables leak through (`nodejs.ts:240-251`, `getShellEnv`).

### 5.4 Timeout, abort, and their precedence

**DIRECT_PI_PARITY.** `timeout` is in seconds; there is no default timeout. An invalid timeout
(non-finite or non-positive) is a `Result` failure at call time, before any process is spawned,
never a validation exception (`nodejs.ts:38-49`).

**Exact timeout ceiling (refined at `L12-R011`, final complete review, `minion-agent-docs#114`,
CE-L12-01-02 -- an earlier revision of this section said "roughly `2^31/1000` seconds," which is
`2147483.648`, not the actual boundary):** pinned Pi's own constant is `MAX_TIMEOUT_MS =
2_147_483_647` (`2^31 - 1`, `nodejs.ts:34`). A timeout is rejected (`timeout` error code) when
`timeout * 1000 > 2_147_483_647`. The largest ACCEPTED value is therefore `2147483.647` seconds
EXACTLY (`2147483.647 * 1000 = 2147483647.0`, not greater than the ceiling); `2147483.648` seconds
is rejected. A typed cross-language contract cannot use an approximation at this exact
accept/reject boundary.

Killing a command, on either abort or timeout,
terminates its ENTIRE process tree/group, not merely the directly-spawned process -- a command
that itself backgrounds a child process does not leave that child running after the parent command
is killed (`nodejs.ts:253-276`, process-group kill on POSIX via a negative PID targeting the whole
group, falling back to single-PID kill if the group-kill itself fails; a tree-kill primitive on
Windows).

**Complete failure-precedence matrix (independent review, `L12-R007` -- an earlier revision of
this section stated only the mid-flight timeout-vs-abort ordering, not the full pre-spawn and
post-spawn sequence pinned Pi actually uses; refined at `L12-R010`, final complete review,
`minion-agent-docs#114`, CE-L12-01-02 -- the combined "cwd/shell resolution" step split into its
own exact two-step order). Confirmed against `nodejs.ts:371-497`, checked in this EXACT order:**

```text
1. Pre-aborted signal        -- checked FIRST, before timeout is even validated, before cwd is
                                 resolved, before a shell is resolved. A signal already aborted at
                                 call time short-circuits everything below.
2. Invalid timeout            -- validated next (finite, positive, within the exact boundary
                                 above); a validation failure here means no process is ever spawned.
3. Lexical cwd resolution     -- options.cwd resolved against the provider's own cwd, or the
                                 provider's own cwd used as-is; a pure string operation, no
                                 filesystem touch yet.
4. Shell discovery            -- getShellConfig(); MAY fail shell_unavailable. Happens BEFORE the
                                 cwd existence check below, not after -- a configured-nonexistent
                                 shell together with a nonexistent cwd observably returns
                                 shell_unavailable, never spawn_error.
5. cwd existence check        -- access(cwd); MAY fail spawn_error. Happens AFTER shell discovery.
6. [process runs]
7. On completion/interruption, exactly one of, in this precedence order:
       a. callback_error      -- a throwing onStdout/onStderr callback (§5.5) wins over everything
                                  below, even if a timeout or abort ALSO applies to the same call.
       b. timeout              -- if the timeout fired, classified `timeout` even if the signal
                                  also happened to be (or becomes) aborted.
       c. aborted              -- only when neither (a) nor (b) applies.
       d. success              -- `{stdout, stderr, exit_code}`, regardless of exit_code (§5.6).
```

An independent implementation MUST NOT guess any step of this ordering -- steps 1-5 determine
whether a process is ever spawned at all and which specific error a caller observes when more than
one pre-spawn condition is simultaneously invalid, and step 7's own ordering determines which
single classification a caller observes when multiple post-spawn failure conditions are
simultaneously true.

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
overstates the actual mechanism: `waitForChildProcess` (`nodejs.ts:278-345`) arms an idle-grace
timer once the process itself exits, and finalizes -- destroying the stdout/stderr streams -- once
that timer fires, EVEN IF a detached descendant process still holds the inherited stdio pipes open
(a pinned Windows-only regression test, `nodejs-env.test.ts:379-400`, exists specifically to prove
the call settles in exactly this scenario rather than hanging forever waiting for true EOF).

**Second correction record (convergence episode `CE-L12-01-01`, `minion-agent-docs#113`):** "a
short idle period" above was left too vague -- independently re-read `nodejs.ts`'s own
`armIdleTimer`/`onData`/`onExit` handlers (lines ~305-334) for the exact constant and reset
semantics. The complete, exact rule, **DIRECT_PI_PARITY**: once the directly-spawned process
exits, arm an idle-grace timer of `EXIT_STDIO_GRACE_MS = 100` milliseconds. Any stdout/stderr data
received BEFORE that timer fires RESETS it (`onData` clears the pending timer and re-arms a fresh
100ms window) -- so a process that exits but whose stdio keeps producing data every &lt;100ms keeps
pushing completion out, not merely waiting a single fixed 100ms from exit. `exec()` settles once
the timer fires with no further data having reset it, OR once both stdout and stderr streams have
independently ended/closed on their own, whichever happens first -- not once every inherited pipe
descriptor, including ones held by unrelated detached descendants, has reached EOF.

This idle-grace mechanism is explicitly `ctx.shell`'s OWN layered concern, built on top of
`ctx.subprocess`'s simpler primitives -- it is not part of `ctx.subprocess`'s own `wait()` contract
at all (§6 below states `wait()` settles on process exit alone, independent of stdio state; a
caller wanting `ctx.shell`-like idle-grace behavior directly on `ctx.subprocess` composes it itself
from `wait()` plus its own timer around `read_chunk()` calls).

### 5.7 Cleanup

**DIRECT_PI_PARITY (refined at `L12-R017`, second final complete review, `minion-agent-docs#114`,
CE-L12-01-03 -- reassigned here from `ctx.fs`'s own §3.8, which misattributed this behavior to the
wrong split provider).** `cleanup()` MUST kill the process tree of every command THIS provider
instance currently has in flight (tracked internally, independent of `ctx.subprocess`'s own
per-`Process` disposal model, an unrelated, already-settled concern from `CE-L12-01-01`) and clear
its own tracking; like every `cleanup()` in this contract, it is best-effort and MUST NOT raise.
This matches pinned Pi's own combined `NodeExecutionEnv.cleanup()`, whose `activeChildPids` set is
shared with `exec()`'s own spawned children (`nodejs.ts:429,691-694`).

**Settlement of a cleanup-killed in-flight command (`DIRECT_PI_PARITY` -- refined, targeted closure
review, `minion-agent-docs#114`, CE-L12-01-03: an earlier revision overgeneralized this to
"unconditionally settles with `exit_code: 0`," which pinned Pi does NOT state).** A command killed
by `cleanup()` does NOT go through the `aborted`/`timeout` classification machinery (§5.4) at all
-- no signal fired, no timeout elapsed. Its own `exec()` call settles through the ORDINARY
exit-handling path: `exitCode: code ?? 0` (`nodejs.ts:495`), where `code` is whatever numeric exit
code the child process's own `exit` event reports (`number | null`). This is CONDITIONAL, not a
blanket zero: if the child reports a numeric exit code `K` (a real possibility -- a process being
killed does not guarantee a null/signal-terminated exit code on every platform or in every timing
window), the caller observes `Ok({stdout, stderr, exit_code: K})`, preserving `K` exactly; `0` is
substituted ONLY when `code` is absent/null. Either way the result is a SUCCESS, never `aborted` or
`timeout` -- a `cleanup()`-triggered kill never sets the abort signal or fires the timeout, so
those classifications never apply regardless of which exit-code case occurs.

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
genuinely different observable behavior. A first remediation round added a complete contract but
left three residual gaps, resolved at convergence episode `CE-L12-01-01` (`minion-agent-docs#113`):
a `spawn(options.signal)` vs. a separately-abortable `wait(signal)` created an unresolved
classification ambiguity for "abort the original spawn signal, then call `wait()` with no
argument"; `wait()`'s own relationship to stdio drain was left unstated; and the disposal language
mixed an unconditional "MUST NOT leak" with only a "SHOULD attempt termination," a combination not
actually achievable in idiomatic Rust (`Drop` cannot `await` asynchronous cleanup). The complete
contract below resolves all three.

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
    wait() -> Result[ExitStatus, SubprocessError]
    terminate() -> None              -- best-effort, must not raise, idempotent

ExitStatus{exit_code: int | None}
    -- exit_code is None when the process was killed (via terminate(), or via the ORIGINAL
       spawn-time signal) before it produced a normal exit code

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
- **`cwd`/environment defaults (refined at `L12-R012`, final complete review,
  `minion-agent-docs#114`, CE-L12-01-02).** `MINION_EXTENSION` -- `ctx.subprocess` has no Pi seam
  to source these from, but the frozen design's own statement that `ctx.shell`'s local provider
  spawns THROUGH `ctx.subprocess` requires this seam's own cwd/environment rule to be well-defined,
  so it mirrors `ctx.shell`'s own already-specified rule (§5.2, §5.3) exactly rather than inventing
  a second, independent one. `cwd`, when omitted, defaults to the provider's own current working
  directory (the same concept `ctx.fs`'s own `cwd` and `ctx.shell`'s own default cwd use); when
  supplied and relative, it resolves against that same provider cwd, using the identical lexical
  resolution rule `ctx.fs`'s own `absolute_path` (§3.2) uses -- not a separately re-implemented
  mechanism. `inherit_env=true` (default): the effective environment is the provider's own
  base/inherited environment overlaid by any per-call `env` -- identical to `ctx.shell`'s own §5.3
  rule. `inherit_env=false`: the effective environment is EXACTLY the per-call `env` and nothing
  else -- no inherited variables leak through, identical to `ctx.shell`'s own rule.
- **One signal, not two (convergence `CE-L12-01-01`).** `spawn()` accepts `options.signal`;
  `wait()` takes NO signal parameter of its own. Cancellation flows ONLY through the ORIGINAL
  spawn-time signal. A pre-aborted `signal` supplied to `spawn()` MUST short-circuit before any
  process is started, returning `aborted` -- matching `ctx.shell`'s own §5.4 step-1 precedent. A
  signal that aborts AFTER the process has started triggers termination; there is no longer a
  second, independently-abortable `wait(signal)` call to reconcile against the first.
- **`wait()` classification.** `wait()` returns `Err(aborted)` when the process was killed because
  the spawn-supplied `signal` fired (at any point, before or after the `wait()` call itself); it
  returns `Ok(ExitStatus{exit_code: None})` when the process was killed via an explicit
  `terminate()` call with no spawn-signal involved -- the caller asked for this outcome, so it is
  not reported as an error. If both occur (the spawn signal fires and the caller also calls
  `terminate()`), whichever caused the actual kill first determines the classification; a
  `terminate()` racing a signal that already fired is a no-op (idempotence, below) and does not
  change the classification the signal already established.
- **`wait()` is independent of stdio state.** `wait()` settles on the PROCESS's own exit alone --
  it does not wait for, and is not affected by, the state of `stdout`/`stderr`/`stdin`. A caller
  wanting BOTH "the process exited" and "I have drained all output" does both explicitly (`wait()`
  plus continued `read_chunk()` calls until each configured stream reports EOF). `ctx.shell`'s own
  idle-grace completion heuristic (§5.6) is a SEPARATE, higher-level concern its local provider
  layers on top of these lower-level primitives -- it is not part of `ctx.subprocess`'s own
  contract, which stays simple and composable.
- **Idempotence.** `wait()` is safe to call repeatedly and/or concurrently; once the process has
  settled, every call (past or still in flight) returns the SAME result. `terminate()` is safe to
  call repeatedly, including after the process has already exited or already been terminated --
  every call after the first is a no-op, matching `cleanup()`'s own best-effort/never-raise
  discipline (§3.8, §5).
- **Process/stream ownership and disposal (convergence `CE-L12-01-01`).** A `Process` value OWNS
  its own stdio handles and underlying OS process handle. Calling `wait()` or `terminate()` is the
  ONLY guaranteed-safe disposal path, in EITHER language equally -- this is a CALLER obligation,
  not an implicit-cleanup guarantee. Dropping/disposing a `Process` value without having called
  either first is UNDEFINED behavior (a caller bug), not a scenario this API promises to handle
  safely: an unconditional "MUST NOT leak the OS process" on implicit disposal is not achievable in
  idiomatic Rust, since `Drop` cannot `await` asynchronous cleanup, so this contract does not make
  that promise. Python MAY additionally offer an async context-manager form whose `__aexit__` calls
  `terminate()` as an ergonomic convenience, but the underlying contract does not depend on it, and
  Rust needs no equivalent to satisfy this contract.
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

**Concrete primitive (refined at `L12-R013`, final complete review, `minion-agent-docs#114`,
CE-L12-01-02 -- an earlier revision of this section stated only the governing rule in prose, with
no type shape, comparison operation, compatibility relation, or typed failure result; this left
"the compatibility VOCABULARY" above as an unfulfilled promise).** `MINION_EXTENSION`, no Pi
source:

```text
ExecutionWorldIdentity: opaque, provider-declared value; supports equality comparison

compatible(a: ExecutionWorldIdentity, b: ExecutionWorldIdentity) -> bool
    -- the compatibility relation. EQUALITY-ONLY (refined at L12-R013, targeted closure review,
       minion-agent-docs#114, CE-L12-01-02): compatible(a, b) := (a == b), full stop. An earlier
       revision additionally permitted a provider to declare itself compatible with specific OTHER
       identity values without defining whether that declaration must be mutual/symmetric or how
       one-sided declarations combine -- observably ambiguous (validate() could depend on provider
       order). No deployment this row certifies needs broader-than-equality compatibility, so the
       simplest and only defensible rule is adopted: compatible() is equality, which is inherently
       symmetric (compatible(a, b) always equals compatible(b, a)) and therefore order-independent
       by construction, with no separate declaration model to specify or get wrong.

validate(providers: list[(name: str, identity: ExecutionWorldIdentity)]) ->
    Result[None, ExecutionWorldError]
    -- called by a CONSUMER (never the runtime) at its own activation, over the specific set of
       providers it needs to address the SAME resource through. Returns Err(ExecutionWorldError)
       naming (by the caller-supplied name/diagnostic label) every pairwise-incompatible provider
       if any pair among the given providers fails compatible(); returns Ok(None) otherwise.
       Providers not passed to a given validate() call are never implicated -- mounting
       incompatible capabilities that no consumer ever asks to be validated together remains
       legal, matching the "mixed worlds are a legitimate deployment" rule above unchanged.

ExecutionWorldError
    incompatible_pairs: ordered list of {left: str, right: str}
```

**Concrete `ExecutionWorldError` payload (refined at `L12-R019`, third final complete review,
`minion-agent-docs#114`, CE-L12-01-04 -- an earlier revision required only that the error "name
every pairwise-incompatible provider," with no stated field shape, ordering, or duplicate-label
handling; two conforming implementations could expose incompatible public APIs).**
`MINION_EXTENSION`, no Pi source:

```text
incompatible_pairs: one entry per pairwise-incompatible combination found among the providers
    passed to validate(), enumerated in the SAME relative order the caller supplied them -- for
    input index i < j, an incompatible pair appears as {left: name[i], right: name[j]} (never the
    reversed order), deterministic and independent of implementation choice beyond the caller's
    own input order.

Caller-supplied labels (the "name" in each (name, identity) tuple) MUST be unique within one
    validate() call; a duplicate label is a caller precondition violation (undefined behavior for
    this primitive), not a case ExecutionWorldError itself needs to represent.

Any human-readable message text a provider or runtime attaches is NON-NORMATIVE -- implementations
    MAY include one for diagnostics, but callers and canonical normalization MUST NOT depend on
    its exact wording; incompatible_pairs is the sole normative payload.
```

---

## 8. Local providers

**Correction record (refined at `L12-R017`, second final complete review, `minion-agent-docs#114`,
CE-L12-01-03):** an earlier revision of this section blanketed ALL THREE local providers'
observable behavior as `DIRECT_PI_PARITY`, including `ctx.subprocess` (§6) -- directly
contradicting §6's own text and `EXEC-005`'s own disposition, both of which correctly state
`ctx.subprocess` is `MINION_EXTENSION` with NO direct Pi seam at all. A local subprocess provider
does not acquire direct-Pi status merely because its primitive set was informed by Pi's combined
shell implementation's own process-management internals. Corrected, per-seam-accurate:

**`DIRECT_PI_PARITY`** for the `ctx.fs` (§3) and `ctx.shell` (§5) local providers' observable
behavior -- both genuinely sourced from pinned Pi's own harness-tier reference implementation.
**`MINION_EXTENSION`** for the `ctx.subprocess` (§6) local provider, matching `EXEC-005`'s own
disposition (`intentional divergence`) -- no Pi seam exists for it to be direct parity with.
**`MINION_ARCHITECTURAL_MAPPING`** for the fact that these are three separate local providers
rather than one combined local `ExecutionEnv`, unchanged.

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

This first-remediation candidate (code `1572bda4bb35a4bf4382e0aaea29b6fafd24ad4a`, docs
`89da9afde11e183d5c4ed7ee19893a819d1cd55b`) was independently RE-reviewed and REJECTED a second
time (`minion-agent-docs#112`, review commit `89d826e101310c07a59eddd072f4d80cd7384ef0`): the same
eight material findings survived in refined form, firing `agent-workflow.md` §11.8 trigger A and
opening convergence episode `CE-L12-01-01`. Every refined claim was independently re-verified
against pinned Pi source before acceptance (a genuine "nine vs. ten" counting error and a genuine
`FsTarget` logical impossibility were both caught this way, not merely asserted by the review). The
§11.8.4 challenge pass and §11.8.5 `AGREED FOR IMPLEMENTATION` checkpoint are recorded in
`minion-agent-docs#113` (`assurance/layers/12-execution-seams-r001-r008-convergence-agreement.md`).
This candidate is the resulting coherent fix pass (§11.8.6), applying the agreed design decisions:

```text
L12-R001/R008  reversed: adopt pinned Pi's OBSERVABLE cancellation behavior (DIRECT_PI_PARITY),
    not the fuller interface promise -- §3.1, firm per-operation table, no divergence language.
    EXEC-002 becomes coherently `adopted` in full as a direct consequence.

L12-R002  rename_file and remove corrected to NEVER traverse symlinks (they operate on the
    addressed directory entry itself, matching raw POSIX rename()/rm()); create_dir-through-a-
    link added to the matrix -- §3.2.

L12-R003  design/2026-08-20-minion-agent-design.md section 7 corrected to the same narrower claim
    spec/execution.md section 1 already stated (Pi's own execution tools require the FileSystem+
    Shell combination; JsonlSessionRepoFileSystem is a real FileSystem-only counter-example to a
    blanket claim) -- closing the frozen-design-vs-derived-spec contradiction the refined finding
    identified. Scoped as a citation-accuracy-only correction, not an architecture change, per
    established precedent (Layer 11 Pass 2 Slice C, L11-SC-R026).

L12-R004  design section 7's own Values table corrected to match the per-operation boundary
    spec/execution.md section 2 already adopted (non-zero exit is a SUCCESS value, not a Result
    error; "stale version"/"remote unavailable" removed, matching no declared code).

L12-R005  target_key redefined as LOCATION-based (canonical_path, falling back to absolute_path
    for a not-yet-existing target) -- matching pinned Pi's own real getMutationQueueKey mechanism
    exactly -- dropping the prior draft's self-contradictory "must also survive rename" requirement
    and excluding device+inode as a permitted mechanism -- section 4.

L12-R006  one signal, not two: wait() takes no signal parameter; cancellation flows only through
    spawn()'s own options.signal. wait() settles on process exit alone, independent of stdio state.
    Disposal reframed as an explicit wait()/terminate() caller obligation, not an implicit-safety
    MUST unachievable in idiomatic Rust (Drop cannot await async cleanup) -- section 6.

L12-R007  exact EXIT_STDIO_GRACE_MS = 100 (ms) constant and its reset-on-data semantics restored,
    explicitly scoped as ctx.shell's own layered concern, not ctx.subprocess's -- section 5.6.
```

Per the standard flow (`agent-workflow.md` §4.1 and §11.8.7): this coherent-fix-pass candidate is
ready for the MANDATORY targeted closure review scoped to `L12-R001` through `L12-R008` and their
acceptance witnesses (§10 below), with the negative-control evidence `agent-workflow.md` §11.8.7.1
requires -- not a fresh full release-level review, unless the reviewer records a concrete reason
this remediation changed semantic surface outside the convergence checkpoint. No Python or Rust
implementation is authorized by this document alone.

That candidate (code `2e925792b0ff4ccd54e538c42917561974e2d2ce`, docs
`e202076fc0c78471b96aa3838f18545ac66b0b95`) received its §11.8.7 targeted closure review
(`minion-agent-docs#114`, review commit `1644536aa70c53d26d1f47d3292cd4d99f9e2755`) and was
REJECTED again: `L12-R002`, `L12-R003`, `L12-R006`, `L12-R007`, `L12-R008` were PROVISIONALLY
CLOSED; `L12-R001`, `L12-R004`, `L12-R005` survived in further-refined, narrower form. Every
refined claim was independently re-verified before acceptance (the `file_info(path, signal?)`
signature vs. §3.1's own "does not accept" prose was directly re-read and confirmed
self-contradictory; the design document's "every failure... returns a typed error value" sentence
was directly re-read alongside its own adjacent exceptions table and confirmed self-contradictory;
the `target_key` missing-to-create instability under a symlinked ancestor was independently
re-derived from `realpath`/`canonical_path` semantics and confirmed to be a property pinned Pi's
own real `getMutationQueueKey` shares exactly, not a Minion-introduced defect). This narrowly
targeted remediation resolves all three:

```text
L12-R001  settled the public-API-shape question left implicit by the prior remediation: every
    operation's typed signature keeps signal? uniformly (matching Pi's own interface shape); for
    the ten operations that do not inspect it, the parameter is explicitly ACCEPTED-BUT-IGNORED,
    not omitted -- section 3.1, new "Public API shape" subsection, plus two witnesses (section 10).

L12-R004  narrowed design/2026-08-20-minion-agent-design.md section 7's "every failure, including
    unexpected backend failures, returns a typed error value" to scope explicitly to EXPECTED
    operational/environmental failures, matching its own adjacent exceptions table and matching
    spec/execution.md section 2 (which was already correctly scoped and required no change) --
    design.md section 7, plus a documentary witness (section 10).

L12-R005  documented the symlinked-ancestor exception to missing-then-create target_key stability:
    the key CAN change across creation when an ancestor directory component is/becomes a symlink,
    because canonical_path resolves every ancestor symlink while the pre-creation absolute_path
    fallback resolves none -- confirmed to be a property pinned Pi's own real getMutationQueueKey
    shares exactly (same absolutePath/canonicalPath fallback pair), not engineered away, per this
    document's own established practice of adopting Pi's observable behavior over an idealized
    promise (section 3.1). Also fixed "different paths produce unequal keys" to say "different
    RESOLVED LOCATIONS," removing the apparent contradiction with the symlink/target equal-key
    rule -- section 4, plus an executable witness (section 10).
```

Per `agent-workflow.md` §11.8.7: this narrowly-scoped remediation candidate is ready for another
targeted closure review of exactly `L12-R001`, `L12-R004`, `L12-R005` and their semantic
dependencies, plus re-confirmation that the five already-provisionally-closed findings remain
undisturbed (this pass touched none of their settled rules). No Python or Rust implementation is
authorized by this document alone.

That candidate (code `71a341802349e0c6f706d599648f8566153318eb`, docs
`1279c0287d03a3ba42fa32d3ee6b25fc42b04e8a`) closed `L12-R001`/`R004`/`R005` (second targeted
closure review, `minion-agent-docs#114` @ `6bb5222158dace4f4b24bb7cea5d06a515aa12ae`, then a final
one-sentence fix at docs `1279c02` itself closed the remaining `L12-R001` wording gap), settling
all eight `CE-L12-01-01` findings. The exact candidate then received its MANDATORY `agent-workflow.md`
§11.8.8 final complete review (`minion-agent-docs#114` @ `c36a2ee22c990b1f829933f6b785ba7813e33210`)
and was REJECTED: six NEW findings, `L12-R009` through `L12-R014`, coupled to and in places
invalidating the settled matrices for filesystem cancellation, shell precedence, subprocess
defaults, execution-world compatibility, and the `FsTarget` bridge. Per §11.8.8 Case B, this opened
a NEW convergence episode, `CE-L12-01-02` (`L12-R001` through `L12-R008` remain
historically/provisionally closed for the exact issues they addressed). The §11.8.4 challenge pass
and §11.8.5 `AGREED FOR IMPLEMENTATION` checkpoint for `CE-L12-01-02` are recorded in
`minion-agent-docs#115`, `assurance/layers/12-execution-seams-r009-r014-convergence-agreement.md`
@ `9c1171e6e427c0b709fceae00b82f04d04bbb697`. This section documents the resulting coherent fix
pass (§11.8.6), applying the agreed design decisions:

```text
L12-R009  replaced the three-bucket cancellation grouping with the complete, checkpoint-accurate
    table: read_text_file/read_binary_file (single mid-operation checkpoint); write_file (THREE
    checkpoints -- pre, after-mkdir, mid-write); read_text_lines (FOUR checkpoints -- pre,
    mid-stream, each loop iteration, and a post-loop check); list_dir (pre and each loop
    iteration only, no post-loop check -- genuinely fewer than read_text_lines); rename_file
    (pre-check only, no mid-operation option exists on the underlying call) -- section 3.1.

L12-R010  split the prior combined "cwd/shell resolution" step into its own exact two-step order
    (lexical cwd resolution, then shell discovery, then the cwd existence check) -- confirmed
    shell discovery completes BEFORE the cwd existence check, giving a combined-invalidity
    input a deterministic single classification -- section 5.4 (also cross-referenced from 5.2).

L12-R011  replaced "roughly 2^31/1000 seconds" with the exact boundary: 2147483.647 seconds is
    the largest accepted value; 2147483.648 seconds is rejected -- section 5.4.

L12-R012  defined ctx.subprocess's own SpawnOptions cwd/environment defaults, mirroring
    ctx.shell's own already-specified rule exactly (coherent with the design's own stated
    ctx.shell-spawns-through-ctx.subprocess relationship) -- section 6.

L12-R013  defined a concrete ExecutionWorldIdentity/compatible()/validate() shape, replacing
    prose-only governance language with a typed identity value, an explicit compatibility
    relation (equality always sufficient, broader relations permitted), and a typed failure
    result naming the incompatible providers -- section 7.

L12-R014  narrowed process_path to the producing provider only, removing the "or a compatible
    provider" allowance that contradicted target_key's own existing provider-scoping rule --
    section 4.
```

Per `agent-workflow.md` §11.8.7: this coherent-fix-pass candidate is ready for the MANDATORY
targeted closure review scoped to `L12-R009` through `L12-R014` and their acceptance witnesses
(§10 below), plus re-confirmation that the whole-contract audit areas the final review already
rechecked remain undisturbed (this pass touched none of their settled rules). No Python or Rust
implementation is authorized by this document alone.

That candidate (code `8201e611a01d5849da4afdb612ef1134452be313`, docs
`f12b7e2f58983905248ff4a4411db35913ce3d44`) received its `CE-L12-01-02` targeted closure review
(`minion-agent-docs#114` @ `ed5a5a6eda2cf3daab9bcf6e1dd49810aba3bb2a`): `L12-R009`-`R012`
PROVISIONALLY CLOSED; `L12-R013`/`R014` STILL OPEN in refined form. This is the narrowly-scoped
remediation of exactly those two:

```text
L12-R013  compatibility narrowed to EQUALITY-ONLY, removing the prior "a provider MAY declare
    itself compatible with specific other identities" allowance, which left symmetry and
    declaration combination undefined (validate() could observably depend on provider order).
    Equality is inherently symmetric, closing the gap without inventing a new declaration model
    -- section 7, plus a new symmetry/order-independence witness (section 10).

L12-R014  collapsed the two incompatible classifications (uniformly undefined vs. a detecting
    provider MUST return FsError(invalid)) into ONE rule: calling process_path on a
    non-producing provider is uniformly undefined; returning FsError(invalid) is now an
    OPTIONAL best-effort diagnostic a provider MAY implement, never a MUST a caller can rely on
    -- section 4, witness updated (section 10).
```

Per `agent-workflow.md` §11.8.7: this narrowly-scoped remediation candidate is ready for another
targeted closure review of exactly `L12-R013`/`L12-R014` and their semantic dependencies, plus
re-confirmation that `L12-R009`-`R012` and the `CE-L12-01-01` findings remain undisturbed (this
pass touched neither). If both close, `CE-L12-01-02` is settled and another §11.8.8 final complete
review becomes available. No Python or Rust implementation is authorized by this document alone.

That candidate closed `L12-R013`/`R014` (`CE-L12-01-02` targeted closure review,
`minion-agent-docs#114`), settling all six `CE-L12-01-02` findings on top of the eight already-
settled `CE-L12-01-01` findings. The resulting exact candidate (code
`88cf0b4564262cddf2aa5fe1a2de66cbe5dfa99e`, docs `a4eb07c764ea8006c867f574475779c9fcfa78ae`) then
received a SECOND mandatory §11.8.8 final complete review (`minion-agent-docs#114` @ `2b5f333`)
and was REJECTED: three NEW findings, `L12-R015` through `L12-R017`. Per §11.8.8 Case B, this
opened a THIRD convergence episode, `CE-L12-01-03` (`L12-R001` through `L12-R014` remain
historically/provisionally closed for the exact issues they addressed). The §11.8.4 challenge pass
and §11.8.5 `AGREED FOR IMPLEMENTATION` checkpoint for `CE-L12-01-03` are recorded in
`minion-agent-docs#116`, `assurance/layers/12-execution-seams-r015-r017-convergence-agreement.md`.
This section documents the resulting coherent fix pass:

```text
L12-R015  synced EXEC-001's own copy of the result/exception boundary with the scoping already
    settled elsewhere (design.md section 7's L12-R004 fix, spec/execution.md section 2, both
    unchanged and already correct) -- EXEC-001's own independent copy of the identical claim was
    never checked during that earlier fix. An unexpected OPERATIONAL failure still normalizes
    (to unknown when unmapped); a broken invariant/programming bug remains an exception, even
    from within a seam provider.

L12-R016  aligned the frozen design's own FsTarget bridge bullets with the settled location-key
    model (resolved-location framing, not "the same file... same key" / "canonical path"),
    preserving the owner-approved bridge mechanism unchanged -- section 4's target_key fallback
    narrowed to the exact Pi condition (not_found/not_supported only, confirmed against
    file-mutation-queue.ts); resolve()'s own cancellation classification stated explicitly
    (accepts-but-does-not-inspect, following from its own constituent operations).

L12-R017  split section 8's blanket DIRECT_PI_PARITY claim per seam (fs/shell direct-parity,
    subprocess Minion extension, matching EXEC-005's own already-correct disposition); reassigned
    active-process-tracking cleanup from ctx.fs (section 3.8, corrected to make no such claim) to
    ctx.shell (new section 5.7), matching Pi's own combined cleanup() behavior exactly, including
    the exact non-error settlement a cleanup-killed in-flight command produces
    (Ok(exit_code: 0), confirmed against nodejs.ts's own code ?? 0 normalization).
```

Per `agent-workflow.md` §11.8.7: this coherent-fix-pass candidate is ready for the MANDATORY
targeted closure review scoped to `L12-R015` through `L12-R017` and their acceptance witnesses
(§10 below), plus re-confirmation that all previously-settled areas remain undisturbed (this pass
touched none of their settled rules). No Python or Rust implementation is authorized by this
document alone.

That candidate's targeted closure review (`minion-agent-docs#114` @
`cb3cb3ea9adf70003a1d1ba3c110a450905cb549`) closed `L12-R015`/`R016`; `L12-R017` remained open in
refined form: the settlement rule above overgeneralized "cleanup-killed commands settle with
`exit_code: 0`" as unconditional, when pinned Pi's own `code ?? 0` is CONDITIONAL -- a real numeric
exit code `K`, when the killed child reports one, is preserved, not overwritten to `0`. This is
the narrow fix: §5.7's settlement rule and its §10 witness now state both cases (numeric code `K`
preserved; `0` substituted ONLY when absent/null), matching `EXEC-004`.

That candidate's second targeted closure review closed `L12-R017`, settling all seventeen findings
across `CE-L12-01-01` through `CE-L12-01-03`. The resulting exact candidate (code
`997d22ba52b2040cf190fa3e9515c6db738aad1b`, docs `d0ab7b53cf16d3da17360ea5faa633a235ee8e7a`) then
received a THIRD mandatory §11.8.8 final complete review (`minion-agent-docs#114` @
`aee3912fef830b42e60f301a51213a6c97d2bd1e`) and was REJECTED: two NEW findings, `L12-R018`
(the exact `not_found`/`not_supported` fallback condition, settled at `L12-R016`, was never
re-checked against the ALSO-settled unconditional symlink/target identity guarantee -- the two
contradict for a hypothetical non-canonicalizing provider) and `L12-R019` (`ExecutionWorldError`'s
own public payload shape was never defined). Per §11.8.8 Case B, this opened a FOURTH convergence
episode, `CE-L12-01-04`. Because narrowing the symlink/target guarantee touches the frozen design's
own bridge invariant, the §11.10 governance-decision provenance requirement applied: the owner was
asked directly and approved narrowing it (Pi's own real mutation-queue mechanism was never
unconditional either). The §11.8.4 challenge pass, the §11.10 governance record, and the §11.8.5
`AGREED FOR IMPLEMENTATION` checkpoint for `CE-L12-01-04` are recorded in `minion-agent-docs#117`,
`assurance/layers/12-execution-seams-r018-r019-convergence-agreement.md`. This section documents
the resulting coherent fix pass:

```text
L12-R018  narrowed the symlink/target target_key identity guarantee (section 4) to hold when
    canonicalization succeeds -- every provider this row currently certifies, since pinned Pi's
    own local reference implementation never produces not_supported at all. A provider whose
    canonical_path is unsupported is explicitly not required to alias-unify a symlink with its
    target; design.md section 7's own bridge bullet gained the same one-clause clarification.

L12-R019  defined ExecutionWorldError's own concrete payload (section 7): an ordered
    incompatible_pairs list of {left, right} labels, enumerated by input index with i < j;
    unique caller-supplied labels as a precondition; human-readable text explicitly non-normative.
```

Per `agent-workflow.md` §11.8.7: this coherent-fix-pass candidate is ready for the MANDATORY
targeted closure review scoped to `L12-R018`/`L12-R019` and their acceptance witnesses (§10 below),
plus re-confirmation that all previously-settled areas remain undisturbed (this pass touched none
of their settled rules). No Python or Rust implementation is authorized by this document alone.

## 10. Discriminating behavior/witness matrix

Per the review's own required correction ("add the checkpoint behavior/witness matrix"). No
executable implementation exists yet, so these are PREDICTED observable outcomes stated precisely
enough to become real regression tests once implementation begins -- not yet executed evidence.
Witnesses below marked "convergence `CE-L12-01-01`" are adopted from `minion-agent-docs#113` §5 and
supersede the prior version of the same witness where one existed (`L12-R001`, `L12-R002`).

```text
CANCELLATION (§3.1, convergence `CE-L12-01-01` -- supersedes the prior version of this witness)
    setup:    an existing file; a pre-aborted signal; file_info called through the Minion typed
              seam (which accepts signal? on every operation, per §3.1's public-API-shape rule)
    call:     file_info(path, signal)
    expected: the call compiles/type-checks and returns Ok(FileInfo{...}) -- the signal argument
              is accepted but has no effect, matching pinned Pi's own observed behavior exactly
              (Pi's own NodeExecutionEnv.fileInfo has no such parameter in its reference
              implementation at all, but Minion's typed seam accepts one uniformly per operation
              and simply does not inspect it here)
    negative control: a candidate requiring Err(aborted) here is WRONG under this agreement -- the
              opposite of the earlier (now-reversed) draft's own requirement, which chose the
              fuller interface promise over Pi's actual observed behavior; a candidate that OMITS
              the signal parameter from file_info's own typed signature is ALSO wrong under this
              agreement -- the parameter is part of the uniform public API shape (§3.1), only its
              inspection is per-operation

CANCELLATION SIGNATURE UNIFORMITY (§3.1, targeted closure review, `minion-agent-docs#114`)
    setup:    the full ctx.fs operation inventory (§3)
    expected: every operation's typed signature includes an optional signal parameter, with no
              exceptions -- the ten operations in section 3.1's "accepts but does not inspect"
              group keep the parameter in their signature; they differ from the other six only in
              whether the parameter has any effect, never in whether it is present at all
    negative control: an implementation that drops the signal parameter from, e.g., file_info's
              own typed signature (rather than accepting and ignoring it) fails this witness even
              if file_info's own observable behavior is otherwise correct

SYMLINK FOLLOWING, CONTENT I/O (§3.2)
    setup:    target.txt with content "X"; link.txt symlinked to target.txt
    call A:   read_text_file("link.txt")
    expected: Ok("X") -- content I/O follows the symlink
    call B:   file_info("link.txt")
    expected: Ok(FileInfo{kind: symlink, ...}) -- lstat-based metadata does not

SYMLINK FOLLOWING, RENAME (§3.2, convergence `CE-L12-01-01`)
    setup:    target.txt="X"; link.txt -> target.txt
    call:     rename_file("link.txt", "moved.txt")
    expected: target.txt unchanged; moved.txt is itself a symlink (kind: symlink) whose content,
              read through it, is still "X"
    negative control: an implementation that moves/renames target.txt itself, or that resolves the
              link before renaming, fails this witness

TARGET IDENTITY IS LOCATION-BASED, NOT RESOURCE-BASED (§4, convergence `CE-L12-01-01` --
    supersedes "TARGET IDENTITY SURVIVES MUTATION" below by clarifying scope: content mutation in
    place still keeps target_key stable; rename does not)
    setup:    a.txt and b.txt, distinct files, identical content "same"; resolve both
    expected: distinct target_key values (never collide on content, matching the existing
              "does not collide" witness below); rename a.txt to c.txt CHANGES a's own target_key
              (correct, not a defect); deleting a.txt and creating a new a.txt (with NO symlinked
              ancestor directory) REUSES the same target_key the old a.txt had (correct and safe,
              not a defect)
    negative control: a device+inode-based implementation fails the missing-then-create case (it
              cannot predict a future inode for a path that does not exist yet); a content-hash
              implementation fails both the content-mutation-stability case and the distinct-
              identical-files case

TARGET IDENTITY CHANGES ACROSS CREATION UNDER A SYMLINKED ANCESTOR (§4, targeted closure review,
    `minion-agent-docs#114` -- refined `L12-R005`; this is the DOCUMENTED EXCEPTION to the
    previous witness's missing-then-create stability, not a contradiction of it)
    setup:    directory real/; symlink link -> real; path link/new.txt (does not yet exist)
    call A:   resolve("link/new.txt") before new.txt exists
    expected: canonicalization fails (not_found -- the final component does not exist yet), so
              target_key falls back to the purely lexical absolute_path, ".../link/new.txt"
              (unresolved -- absolute_path never touches the filesystem, so it does not resolve
              the "link" ancestor either)
    call B:   create new.txt through link/new.txt, then resolve("link/new.txt") again
    expected: canonicalization now succeeds and resolves EVERY symlink component including the
              ancestor, producing ".../real/new.txt" -- a DIFFERENT string than call A's key
    negative control: an implementation asserting these two keys are equal is WRONG under this
              agreement -- pinned Pi's own real getMutationQueueKey has this identical property
              (file-mutation-queue.ts:20-26, calling the same absolutePath/canonicalPath fallback
              pair in the same order), so this instability is DIRECT_PI_PARITY, not a Minion defect
              to engineer away

PROCESS WAIT, ONE SIGNAL (§6, convergence `CE-L12-01-01`)
    setup:    spawn a process with a signal; abort that ORIGINAL spawn signal; call wait() with no
              argument (wait() takes none)
    expected: Err(aborted) -- the classification derives from the spawn-time signal alone, since a
              separate wait-time signal no longer exists in this contract
    second setup: drop a running Process without calling wait() or terminate()
    expected: documented as undefined/caller-error, not required to be leak-safe

SHELL IDLE-GRACE, EXACT RESET CONSTANT (§5.6, convergence `CE-L12-01-01`)
    setup:    a direct child exits; its own stdout emits one more chunk at +80ms; nothing else
              happens
    expected: exec() settles at approximately +180ms (80ms elapsed, plus a fresh 100ms grace
              re-armed by the reset), not at +100ms (which would mean the timer did not reset on
              the +80ms data)

SHELL FAILURE PRECEDENCE (§5.4)
    setup:    a command whose onStdout callback raises, AND whose timeout also elapses
    expected: Result.Err(ShellError(callback_error)) -- callback_error wins over timeout even
              though both conditions are true

SHELL COMPLETION (§5.6)
    setup:    a command that exits while a detached descendant still holds inherited stdio open
    expected: exec() settles (does not hang) once the direct child exits plus the 100ms idle-grace
              period elapses with no further data -- not once the detached descendant's own pipe
              reaches EOF

PROCESS WAIT VS. TERMINATE (§6)
    setup:    a running process; caller calls terminate() with no spawn-time signal involved
    expected: wait() returns Ok(ExitStatus{exit_code: None})
    contrast: same process, but the ORIGINAL spawn-time signal (not terminate()) triggers the kill
    expected: wait() returns Err(SubprocessError(aborted)) -- same underlying kill mechanism,
              deliberately different classification depending on WHO initiated it; see also
              "PROCESS WAIT, ONE SIGNAL" above, which is this same witness restated to make
              explicit that wait() itself takes no signal argument

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

ERROR-STYLE SCOPE IS "EXPECTED FAILURES," NOT "EVERY FAILURE" (§2, targeted closure review,
    `minion-agent-docs#114` -- refined `L12-R004`, corrected in
    design/2026-08-20-minion-agent-design.md section 7, not in this section, which was already
    correctly scoped)
    setup:    a seam provider's own internal invariant is violated (a genuine provider bug), and it
              throws/panics before producing an operational FsError/ShellError/SubprocessError
    reader A: follows a literal "every failure, including unexpected backend failures, becomes a
              typed Result" reading
    reader B: follows this section's own boundary table (§2) -- an unnormalized backend exception
              escaping a seam is itself a provider bug, an EXCEPTION, not a Result
    expected: only reader B matches this document's own stated rule; the design document's
              equivalent prose (section 7) is corrected to match, so both documents now agree

CANCELLATION CHECKPOINT COUNT DIFFERS BY OPERATION (§3.1, convergence `CE-L12-01-02`)
    setup:    read_text_lines whose signal aborts AFTER the last line has been yielded to the
              caller's loop but BEFORE the operation itself returns
    expected: Err(aborted) -- the post-loop checkpoint catches this window
    negative control: an implementation checking only pre-aborted-and-each-loop-iteration (no
              post-loop check) returns Ok(lines) here, failing this witness
    second setup: the identical timing, but on list_dir instead of read_text_lines (signal aborts
              after the last entry has been yielded but before the operation returns)
    expected: Ok(entries) -- list_dir has NO post-loop checkpoint, unlike read_text_lines
    negative control: an implementation treating list_dir and read_text_lines as identical (both
              Err(aborted) or both Ok here) fails one half of this witness
    third setup: write_file whose signal aborts AFTER parent-directory mkdir completes but BEFORE
              the write call begins
    expected: Err(aborted); no content write may have started
    negative control: an implementation checking only pre-aborted (no after-mkdir check) proceeds
              to write, failing this witness

SHELL PRE-SPAWN ORDER, COMBINED INVALIDITY (§5.4, convergence `CE-L12-01-02`)
    setup:    shell.exec() called with a configured, nonexistent custom shell path AND a
              nonexistent cwd
    expected: Err(ShellError(shell_unavailable)) -- shell discovery fails first
    negative control: an implementation checking cwd existence before shell discovery returns
              Err(ShellError(spawn_error)) instead, failing this witness

SHELL TIMEOUT EXACT BOUNDARY (§5.4, convergence `CE-L12-01-02`)
    setup:    timeout = 2147483.647 seconds; separately, timeout = 2147483.648 seconds
    expected: 2147483.647 is Ok (accepted, spawns normally); 2147483.648 is
              Err(ShellError(timeout)) before any process is spawned
    negative control: an implementation using "roughly 2^31/1000" (2147483.648) as its own accept
              boundary accepts the second case, failing this witness

SUBPROCESS CWD/ENVIRONMENT DEFAULTS (§6, convergence `CE-L12-01-02`)
    setup:    spawn() with cwd omitted, in a provider whose own cwd is /work
    expected: the child process's own observable cwd is /work
    second setup: spawn() with inherit_env=true and env={"X":"1"}, in a provider whose base
              environment includes Y=2
    expected: the child observes both X=1 and Y=2
    third setup: spawn() with inherit_env=false and env={"X":"1"}
    expected: the child observes ONLY X=1 -- no inherited variable leaks through
    negative control: an implementation defaulting cwd to the OS process cwd rather than the
              provider's own cwd, or dropping the base environment under inherit_env=true, fails
              these witnesses

EXECUTION-WORLD COMPATIBILITY, CONCRETE PRIMITIVE (§7, convergence `CE-L12-01-02` -- supersedes
    the "EXECUTION-WORLD COMPATIBILITY (§7)" witness above by exercising the concrete
    compatible()/validate() shape rather than only the governing rule in prose)
    setup:    two synthetic providers, A and B, declaring EQUAL execution-world identities; a
              synthetic consumer calling validate([("a", A.identity), ("b", B.identity)])
    expected: Ok(None) -- equal identities are always compatible
    second setup: A and B declaring UNEQUAL identities; same validate() call
    expected: Err(ExecutionWorldError) naming both "a" and "b"
    negative control: an implementation with no concrete validate()/ExecutionWorldError shape
              cannot even express this witness, which is itself the finding

EXECUTION-WORLD COMPATIBILITY IS SYMMETRIC AND ORDER-INDEPENDENT (§7, targeted closure review,
    `minion-agent-docs#114` -- refined `L12-R013`, CE-L12-01-02)
    setup:    two unequal identities A and B
    expect:   compatible(A, B) == compatible(B, A) (both false, since compatibility is
              equality-only and A != B); validate([("a",A),("b",B)]) and
              validate([("b",B),("a",A)]) produce the SAME outcome (both Err, naming both
              providers regardless of which order they were passed in)
    negative control: a candidate permitting one-sided/asymmetric compatibility declarations (the
              now-removed "broader relation" option) could make these two validate() calls
              disagree depending on provider order -- this witness would catch that regression

PROCESS_PATH SCOPED TO THE PRODUCING PROVIDER ONLY (§4, convergence `CE-L12-01-02` -- refined
    `L12-R014`, targeted closure review, `minion-agent-docs#114`: ONE rule, not two)
    setup:    FsTarget resolved on provider A; process_path(target) called on provider B, a
              DIFFERENT provider instance independently validated as execution-world-compatible
              with A
    expected: this call is UNIFORMLY undefined (a caller bug) -- the correct workflow calls
              process_path on provider A itself, then hands the resulting STRING to a
              shell/subprocess provider compatible with A. A conforming provider B MAY, as
              best-effort hardening, detect the foreign provenance and return FsError(invalid)
              instead of a fabricated path, but this is NOT required -- a caller must not rely on
              receiving any particular Result from this out-of-contract call
    negative control: a candidate asserting this call MUST succeed is WRONG; a candidate asserting
              a detecting provider MUST return FsError(invalid) is ALSO wrong -- both would
              contradict the single "uniformly undefined, optional best-effort diagnostic only"
              rule this agreement settles on

ERROR/EXCEPTION BOUNDARY CONSISTENT ACROSS EXEC-001/DESIGN/SPEC (§2, convergence `CE-L12-01-03`)
    setup:    read EXEC-001's own text, design.md section 7's Error style paragraph, and
              spec/execution.md section 2 side by side, for a provider invariant violation that
              throws/panics before producing an operational error
    expected: all three now state the SAME distinction -- operational (however unexpected)
              normalizes to a typed Result error; invariant/programming failures remain
              exceptions, including from within a provider's own implementation
    negative control: a candidate where EXEC-001's own prose still reads as an unscoped "every
              failure becomes Result" claim fails this witness even if the other two are correct

FSTARGET RESOLVED-LOCATION FRAMING MATCHES ACROSS DESIGN/SPEC (§4, convergence `CE-L12-01-03`)
    setup:    file.txt and hardlink.txt, two hard links to the SAME underlying inode; resolve both
    expected: DIFFERENT target_key values (different canonical paths) -- confirming design.md's
              own corrected bridge bullet ("different LOCATIONS... even when... the same
              resource") and NOT the pre-correction "same file... same key" claim
    second setup: canonical_path(missing/path) failing with permission_denied (not
              not_found/not_supported)
    expected: resolve() returns Err(FsError(permission_denied)) -- it does NOT silently fall back
              to absolute_path for this error code
    third setup: resolve(path, signal) with a pre-aborted signal, on an EXISTING path
    expected: Ok(FsTarget{...}) -- resolve() accepts signal but does not inspect it
    negative control: a candidate falling back to absolute_path on ANY canonicalization error
              (not just not_found/not_supported) fails the second case; a candidate returning
              Err(aborted) on the third case fails that one

CTX.SHELL CLEANUP KILLS ACTIVE COMMANDS; SETTLEMENT PRESERVES A REAL EXIT CODE (§5.7, targeted
    closure review, `minion-agent-docs#114` -- refined `L12-R017`, CE-L12-01-03: an earlier version
    of this witness claimed an unconditional exit_code: 0, which pinned Pi does not guarantee)
    setup A:  shell.exec() in flight (no timeout, no external abort signal fired); caller calls
              shell.cleanup() while it is still running; the killed child reports NO numeric exit
              code (null/absent, the common signal-terminated case)
    expected A: the in-flight process tree is killed; exec() settles Ok({stdout, stderr,
              exit_code: 0}) -- 0 substituted because the code was absent/null
    setup B:  identical, except the killed child DOES report a numeric exit code K (e.g. 137)
              before/as part of settling
    expected B: exec() settles Ok({stdout, stderr, exit_code: K}) -- K is PRESERVED, not
              overwritten to 0
    both cases: NOT Err(aborted), NOT Err(timeout) -- cleanup-triggered termination never sets the
              abort signal or fires the timeout, regardless of which exit-code case occurs
    negative control: an implementation whose shell.cleanup() is a true no-op leaves the command
              running, failing this witness; an implementation classifying either settlement as
              Err(aborted) fails, since no abort signal was ever involved; an implementation that
              unconditionally returns exit_code: 0 regardless of a real observed code K fails
              case B specifically

LOCAL-PROVIDER PARITY IS PER-SEAM, NOT BLANKET (§8, convergence `CE-L12-01-03`)
    setup:    read section 8's own parity claim for ctx.subprocess (section 6) side by side with
              EXEC-005's own disposition
    expected: both now say MINION_EXTENSION/intentional divergence -- no remaining blanket
              DIRECT_PI_PARITY claim covering ctx.subprocess
    negative control: a candidate still claiming DIRECT_PI_PARITY for section 6 in section 8's own
              text fails this witness

SYMLINK/TARGET IDENTITY HOLDS ONLY WHEN CANONICALIZATION SUCCEEDS (§4, targeted closure review,
    `minion-agent-docs#114` -- refined `L12-R018`, CE-L12-01-04, governance decision recorded in
    `minion-agent-docs#117`)
    setup:    a stub provider whose canonical_path returns Err(not_supported) for every path;
              resolve("link") and resolve("target") (link a symlink to target, by the provider's
              own semantics, though it cannot canonicalize to prove it)
    expected: target_key("link") != target_key("target") -- UNEQUAL, an explicitly documented
              limitation of this provider, not a contract violation
    second setup: the SAME stub provider; resolve("link") called twice for the identical path
    expected: EQUAL target_key both times -- stability for repeated resolution of the SAME path
              still holds even without canonicalization
    negative control: a candidate asserting target_key("link") == target_key("target") for a
              not_supported provider is WRONG under this agreement; a candidate asserting a
              canonicalization-CAPABLE provider's own symlink/target keys may legitimately differ
              is ALSO wrong -- the guarantee still holds unconditionally for every provider this
              row currently certifies (none of which ever produces not_supported)

EXECUTIONWORLDERROR HAS A CONCRETE, ORDERED PAYLOAD (§7, targeted closure review,
    `minion-agent-docs#114` -- refined `L12-R019`, CE-L12-01-04)
    setup:    validate([("fs", A), ("shell", B), ("subprocess", C)]) with A/B incompatible, A/C
              incompatible, B/C compatible
    expected: Err(ExecutionWorldError{incompatible_pairs: [{left:"fs",right:"shell"},
              {left:"fs",right:"subprocess"}]}) -- exactly these two entries, in input-index order
    second setup: validate([("a", X), ("a", Y)]) -- duplicate label "a"
    expected: undefined behavior (caller precondition violation) -- not a case this primitive is
              required to represent in its own Result
    negative control: an implementation returning only a human-readable string, an unordered set,
              or pairs in a different order than input-index i<j fails this witness
```
