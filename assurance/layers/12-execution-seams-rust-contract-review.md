# Layer 12 WP-12.1 — independent Rust contract review

## Exact review target

- Code PR `EGAILab/minion-agent#40` @
  `1018f5d2478c0de1ed5c086389e109c8d5e6222a`
- Docs PR `EGAILab/minion-agent-docs#110` @
  `922243d6f747186c4a895dea5830fa755ef2c011`
- Current code default at review start: `main` @
  `b60a6365a08e69551417b7a4334b46f5701020d4`
- Code candidate merge base: `53d97970243f5181cd9ea1d1b229722d7ed97db4`.
  The later default-branch commit only updates the already-deferred AI-031/AI-032
  coordination pointer; it does not change this review's Layer-12 source mapping.
- Current docs default and candidate merge base: `master` @
  `2e0ba62801c042dfe186ed133bbf55d431c1f99a`
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Coordination: `EGAILab/minion-agent#39`. Its machine-readable body named the
  exact candidate heads above, `status: CONTRACT_REVIEW`, `next_owner: Codex`,
  and the owner-authored scope decision at issue comment `5736233272`.

Both candidate PRs were open, Ready for Review, mergeable, unmerged, and
remote-reachable when review began. The review was read-only with respect to
the candidate, Python, Rust, canonical scenarios, and Layer 13.

## Independent authority audit

The audit order was pinned Pi first, then the frozen master design, candidate
spec, manifest, existing certified Rust architecture, and coordination
handoff. Python was not used as a semantic source.

Pinned Pi sources inspected directly include:

- `packages/agent/src/harness/types.ts`: `FileErrorCode`, `ExecutionErrorCode`,
  `FileInfo`, `FileSystem`, `ShellExecOptions`, `Shell`, `ExecutionEnv`;
- `packages/agent/src/harness/env/nodejs.ts`: `resolvePath`, `toFileError`,
  `waitForChildProcess`, `NodeExecutionEnv.exec`, and every filesystem method;
- `packages/agent/src/harness/session/jsonl/types.ts` and its call sites;
- `packages/agent/src/harness/tools/tool-context.ts`;
- `packages/agent/test/harness/nodejs-env.test.ts`.

The owner-approved Layer-12 boundary is coherent: execution seams, local
providers, FsTarget/process-path mapping, and execution-world compatibility
belong in WP-12.1; built-in tools and file-mutation serialization do not.
The following semantic blockers prevent the draft from becoming the agreed
implementation checkpoint.

## Findings

### L12-R001 — `PI_BEHAVIOR_UNCERTAIN` — filesystem cancellation conflict is much broader than `append_file`

Pinned `FileSystem` places an optional `AbortSignal` on every operation except
`cleanup()`. The pinned `NodeExecutionEnv`, however, ignores that signal on
`absolutePath`, `joinPath`, `appendFile`, `fileInfo`, `canonicalPath`, `exists`,
`createDir`, `remove`, `createTempDir`, and `createTempFile`. It checks or
threads cancellation only for `readTextFile`, `readTextLines`,
`readBinaryFile`, `writeFile`, `renameFile`, and `listDir`; even those use
different mechanisms and checkpoints.

The candidate exposes `signal?` on all methods but flags only `append_file` as
uncertain. An independent implementation therefore cannot know whether a
pre-aborted signal must short-circuit each method, whether cancellation is
best-effort only at selected checkpoints, or whether the public Pi interface
rather than its shipped Node provider controls the adopted rule.

**Discriminating witness:** create an existing file and a pre-aborted signal,
then call `fileInfo(path, signal)` and `appendFile(path, data, signal)` on
pinned `NodeExecutionEnv`. The implementation ignores the extra signal in
both methods: metadata succeeds and append mutates the file. A contract that
requires every declared signal to short-circuit produces `aborted` and no
mutation instead.

**Required correction:** provide a method-by-method cancellation matrix and
resolve the interface/reference-implementation conflict explicitly. Do not
infer intentionality from operation duration. If Minion adopts the interface
contract over the concrete pinned implementation, record that source choice
and its disposition rather than calling it unqualified direct parity.

### L12-R002 — `PI_PARITY_DEFECT` — the draft falsely says only `canonical_path` follows symlinks

`resolvePath` does not canonicalize symlinks, and `fileInfo`/`listDir` use
`lstat`, but ordinary Node filesystem operations still follow symlinks where
their underlying OS operation does. `readFile(link)` reads the target;
`writeFile(link, ...)` and `appendFile(link, ...)` mutate the target. The Pi
type comments say addressed paths are not *canonicalized* automatically and
specifically promise non-following metadata; they do not promise that all I/O
operations refuse to traverse links.

The candidate instead states that symlinks are never followed by path
resolution **or by any operation** except `canonical_path`. That is observably
different from pinned Pi.

**Discriminating witness:** create `target.txt`, create `link.txt` pointing to
it, and call `readTextFile("link.txt")`. Pinned Pi's provider returns the
target contents. A no-follow implementation rejects or reads a distinct link
object.

**Required correction:** specify symlink behavior per operation. Preserve the
distinction among lexical/addressed path resolution, `lstat`-based metadata,
explicit canonicalization, and ordinary file-content operations.

### L12-R003 — `CONTRACT_ASSURANCE_DEFECT` — temp-resource cleanup and Pi dependency claims overstate the source

The draft treats the private directory created by `createTempFile` as implying
that cleanup must remove both file and directory. Pinned `NodeExecutionEnv`
does not track either: `cleanup()` only kills active child processes and clears
its PID set. The Pi test only proves creation and suffix shape. It does not
prove removal. The normative text must not turn an implementation-composition
detail into an adopted cleanup obligation without a disposition.

The architecture rationale also says no Pi consumer takes `FileSystem` alone.
Pinned `JsonlSessionRepoFileSystem` is a real `Pick<FileSystem, ...>` consumed
by the JSONL session repository. It is accurate to say Pi's built-in execution
tools use `ExecutionToolContext.env: ExecutionEnv`; it is not accurate to say
every real consumer does.

**Discriminating witness:** create a temp file through `NodeExecutionEnv`, call
`cleanup()`, then check the file and private directory. Both remain. Separately,
`JsonlSessionRepoOptions.fs` type-checks with its filesystem-only picked
surface and no shell.

**Required correction:** state only source-supported temp creation/cleanup
behavior and narrow the combined-dependency claim to the consumer tier for
which it is true. The owner-approved Minion three-seam architecture remains
valid; its source rationale must be accurate.

### L12-R004 — `CONTRACT_ASSURANCE_DEFECT` — the shared Result/error rule is internally contradictory

The candidate says every seam operation returns `Result[T, E]` and that
non-zero process exit is an operational failure represented by a typed error.
It later correctly says `Shell.exec` returns `Ok` for any exit code, and
`Process.wait()` returns the exit code as a success value. `cleanup()` and
`terminate()` also deliberately return no `Result`, while raw pipe operations
have no defined result boundary at all. `stale version` is listed as an error
although no Layer-12 code includes it and no `FsErrorCode` represents it;
`remote/backend unavailable` is likewise not assigned to a normative code.

**Discriminating witness:** pinned `env.exec("exit 7")` returns
`ok({stdout:"", stderr:"", exitCode:7})`, which its pinned test asserts. The
draft's shared rule simultaneously classifies the same condition as a Result
error.

**Required correction:** define the boundary per method/operation, distinguish
success values that report an unsuccessful child exit from seam-operation
failure, remove future Layer-13 conditions from this layer, and map every
owned operational condition to exactly one declared code. Exempt cleanup and
other best-effort lifecycle methods explicitly rather than using an untrue
universal rule.

### L12-R005 — `CONTRACT_ASSURANCE_DEFECT` — `FsTarget` identity is not implementable as written

The same-resource rule lacks the scope and type invariants required for a
portable equality key. It does not say whether keys from different filesystem
provider instances/worlds may be compared, whether `target_key` must implement
stable equality and hashing, what `resolve()` does for a not-yet-existing write
target, who owns `process_path`, or what happens when a target is passed to a
foreign provider/world.

The text also says symlink identity may depend on whether a provider chooses to
follow it while simultaneously requiring the same underlying resource to have
the same key. Those statements conflict. Finally, it lists a content hash as a
permitted mechanism. A content hash gives two distinct equal-content files the
same identity and changes when one resource's content changes, violating the
stated resource-identity guarantee in both directions.

**Discriminating witness:** create two distinct files with identical bytes.
They are different filesystem resources and must have different mutation-queue
identities; the draft expressly permits a mechanism that gives them the same
key. Mutating one file then changes its key even though its resource identity
has not changed.

**Required correction:** define provider/world scoping, equality/hash
requirements, existing versus missing targets, alias/symlink treatment,
`process_path` ownership, and foreign-target failure. Remove mechanisms that
cannot satisfy the normative invariant. Rust must be able to choose a typed
key without inventing observable identity rules.

### L12-R006 — `CONTRACT_ASSURANCE_DEFECT` — the subprocess capability is not a complete process/stream contract

The proposed shape says stdin is available "if requested," but `spawn()` has
no stdio request/configuration parameter. It exposes raw streams while saying
pipe failures cross as `Result`, without specifying typed read/write/close
operations or whether native stream exceptions may escape. It does not define:

- pre-aborted versus post-spawn signal behavior;
- what `wait()` returns after signal cancellation or `terminate()`;
- repeated/concurrent `wait()` and repeated `terminate()`;
- process/pipe ownership, drop/disposal, or leak prevention;
- stdin close/EOF behavior and stdout/stderr chunk type;
- whether pipe failure changes `wait()` or is observed only by pipe I/O;
- why `timeout` exists in `SubprocessErrorCode` when neither `spawn`, `wait`,
  nor `terminate` accepts a timeout.

Two reasonable Rust implementations can expose `AsyncRead`/`AsyncWrite` (native
I/O errors) or typed Result-returning stream handles and both fit the prose,
yet callers observe different error and lifecycle semantics.

**Required correction:** supply a complete language-neutral process state and
stream-ownership matrix, including cancellation, termination, wait
idempotence, stdio configuration, pipe error observation, and cleanup. Revise
the error vocabulary to exactly the operations that can produce each code.
This is a Minion extension, so coherence with the frozen design—not a false Pi
citation—is the acceptance criterion.

### L12-R007 — `PI_PARITY_DEFECT` — shell completion and competing-failure precedence are incomplete/overstated

The draft uses pinned `Shell.exec` to require complete stdio drain. Pinned
`waitForChildProcess` actually arms a 100 ms idle grace after process exit and
then finalizes and destroys stdout/stderr even if a detached descendant still
holds inherited pipes open. The pinned Windows regression test exists
specifically to prove the call settles rather than waiting for full pipe EOF.
That behavior cannot support a universal "fully draining" requirement for the
new subprocess seam.

The high-risk failure ordering is also only partially specified. Pinned source
settles `callback_error` before `timeout`, then `aborted`, and checks a
pre-aborted signal before validating timeout or resolving shell/cwd. An
independent Rust implementation must not guess these observable precedence
rules.

**Discriminating witness:** spawn a shell that exits while a detached child
retains inherited stdio. Pinned Pi settles after its post-exit idle grace; a
contract implementation waiting for full EOF remains pending. For competing
failure classification, a callback throw wins over a timeout/aborted signal in
the pinned settlement order.

**Required correction:** describe the actual exit/close/idle-grace completion
rule or explicitly disposition a different Minion policy. Add the complete
pre-spawn and post-spawn error-precedence matrix needed by this §4.1 contract
checkpoint.

### L12-R008 — `CONTRACT_ASSURANCE_DEFECT` — manifest subjects and dispositions are incoherent

All six rows use `disposition: adopted`, including EXEC-003/005/006, whose own
text says there is no Pi equivalent and labels them Minion mapping/extensions.
EXEC-001 combines direct Pi error vocabularies with the new subprocess
extension under one disposition. EXEC-002 claims adoption while retaining an
active Pi uncertainty. This violates the manifest invariant that one row has
one coherent semantic subject and one defensible disposition; prose labels do
not repair a contradictory machine disposition.

The frozen architecture and owner decision authorize these Minion surfaces,
but authorization does not turn them into adopted Pi behavior. Existing
manifest precedent uses `intentional divergence` for Minion-only public
facilities and splits mixed subjects when their dispositions differ.

**Required correction:** split mixed rows where needed and assign each direct
Pi rule, architectural mapping, and extension its defensible disposition.
No row may be `adopted` while carrying unresolved `PI_BEHAVIOR_UNCERTAIN`.

## Evidence and structural gates

Fresh checks against the exact candidate:

- `uv run pytest tests/conformance/test_manifest_validation.py --no-cov -q`:
  `8 passed`.
- Parsed manifest: `101` rows, `101` unique IDs; EXEC-001 through EXEC-006
  are present.
- Candidate diff: only `pi-parity-manifest.yaml` and `spec/execution.md`.
- No canonical execution scenario exists yet. That is acceptable for an
  initial draft, but the remediated checkpoint must include a discriminating
  behavior/witness matrix for cancellation, path/symlink behavior, shell
  precedence/completion, process lifecycle, target identity, and world
  compatibility before implementation starts.

Structural green gates do not override the semantic blockers above.

## Existing Rust architecture and implementability

Certified Rust already has typed services, `Context`, `ScopeHandle`, runtime
signals, Tokio/futures support, and disposal ownership. It can represent the
three seams as typed services and can use Rust-native futures and process I/O
without copying Python mechanics. No certified lower-layer semantic reopening
is established by this review.

Rust cannot implement this candidate independently without choosing semantics
the shared artifacts leave contradictory or undefined: cancellation for half
the filesystem surface, symlink traversal, target-key scope, stream errors and
ownership, wait/termination behavior, and shell completion/precedence. Those
choices are observable and cannot be deferred to implementation preference.

## Contract-quality answers

- No runner currently simulates production behavior; there is no Layer-12
  runner yet.
- The draft contains implementation-source claims that pinned Pi contradicts.
- The new Minion subprocess and target identity surfaces need more contract,
  not Python-shaped mechanisms.
- Two conforming implementations can currently make observably different
  choices on several owned behaviors.
- No Layer-13 built-in tool or mutation queue is needed to repair the contract.
- The owner-approved WP-12.1 boundary remains appropriate.

## Verdict

```text
shared Layer-12 WP-12.1 contract
    REJECTED

Python Layer 12
    NOT_IMPLEMENTED / BLOCKED

Rust Layer 12
    NOT_IMPLEMENTED / BLOCKED

Layer 12 cross-language
    NOT CLOSED

Layer 13
    NOT STARTED
```

This verdict applies only to code
`1018f5d2478c0de1ed5c086389e109c8d5e6222a` and docs
`922243d6f747186c4a895dea5830fa755ef2c011`.

## Next action

Return L12-R001 through L12-R008 to the shared-contract owner for targeted
contract remediation. Resolve the Pi-source conflicts, complete the
Minion-owned process/identity contracts, align manifest dispositions, and add
the checkpoint behavior/witness matrix. Any changed candidate SHA requires a
new independent exact-SHA contract review. Do not begin Python or Rust Layer
12 implementation, and do not start Layer 13.
