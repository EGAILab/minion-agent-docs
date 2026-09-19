# Layer 12 WP-12.1 — independent Rust contract re-review

## Exact review target

- Code PR `EGAILab/minion-agent#40` @
  `1572bda4bb35a4bf4382e0aaea29b6fafd24ad4a`
- Docs PR `EGAILab/minion-agent-docs#110` @
  `89da9afde11e183d5c4ed7ee19893a819d1cd55b`
- Current code default at review start: `main` @
  `b60a6365a08e69551417b7a4334b46f5701020d4`
- Current docs default at review start: `master` @
  `2e0ba62801c042dfe186ed133bbf55d431c1f99a`
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Prior rejected candidate: code
  `1018f5d2478c0de1ed5c086389e109c8d5e6222a`, docs
  `922243d6f747186c4a895dea5830fa755ef2c011`
- Prior review: `assurance/layers/12-execution-seams-rust-contract-review.md`
  @ `092f63a5e3136f598fe1e508d4c60f6d8fe4dc17`

Issue `EGAILab/minion-agent#39` was open and its machine-readable current-state
block named the exact candidate heads above, `status: CONTRACT_REVIEW`,
`next_owner: Codex`, a non-empty next action, and owner-authored scope provenance
at issue comment `5736233272`. Both candidate PRs were open, Ready for Review,
unmerged, and their exact heads were remote-reachable. Neither candidate is
derived from a quarantined artifact.

This was a review-only pass. No Python, Rust, canonical, manifest, spec, or
Layer-13 implementation file was modified.

## Independent authority audit

The review used pinned Pi first, then the frozen master design, candidate
manifest/spec, existing certified Rust architecture, and the handoff. Python
was not used as a semantic oracle.

Pinned Pi sources inspected directly:

- `packages/agent/src/harness/types.ts`: `FileErrorCode`, `ExecutionErrorCode`,
  `FileInfo`, `FileSystem`, `ShellExecOptions`, `Shell`, `ExecutionEnv`;
- `packages/agent/src/harness/env/nodejs.ts`: `resolvePath`, `toFileError`,
  `waitForChildProcess`, `NodeExecutionEnv.exec`, and every filesystem method;
- `packages/agent/src/harness/session/jsonl/types.ts`;
- `packages/agent/src/harness/tools/tool-context.ts`;
- `packages/agent/test/harness/nodejs-env.test.ts`.

The remediation fixes important parts of the first candidate: metadata and
content-I/O symlink behavior are now distinguished; temporary resources are no
longer falsely claimed to be removed; non-zero shell exit is no longer called a
seam error in the spec; subprocess has typed stdio configuration and operations;
and Minion-only manifest rows no longer claim adoption. The exact candidate is
still not a complete, internally coherent implementation checkpoint.

## Finding closure ledger

| Finding | Remediation result | Current classification | Status |
|---|---|---|---|
| `L12-R001` | Method inventory added, but the observable interface-over-reference choice lacks governance, the count is wrong, and mid-operation behavior remains optional | `PI_PARITY_DEFECT` + `CONTRACT_ASSURANCE_DEFECT` | **STILL OPEN** |
| `L12-R002` | Read/write/metadata distinction improved, but `rename_file` is still classified as following the final symlink and `remove` is omitted | `PI_PARITY_DEFECT` | **STILL OPEN** |
| `L12-R003` | Candidate spec fixes temp cleanup and narrows the consumer claim, but the frozen master design still states the disproved blanket consumer claim | `CONTRACT_ASSURANCE_DEFECT` | **STILL OPEN** |
| `L12-R004` | Candidate spec/manifest fix the local contradiction, but the frozen master design still normatively calls non-zero exit/stale version/remote unavailable typed seam errors | `CONTRACT_ASSURANCE_DEFECT` | **STILL OPEN** |
| `L12-R005` | More identity dimensions are named, but the resulting invariant and the expressly permitted key mechanisms contradict one another | `CONTRACT_ASSURANCE_DEFECT` | **STILL OPEN** |
| `L12-R006` | Typed process/stream shape added, but post-spawn spawn-signal settlement, raw wait completion, and disposal guarantees remain ambiguous | `CONTRACT_ASSURANCE_DEFECT` | **STILL OPEN** |
| `L12-R007` | Precedence order and idle-grace concept added, but the Pi-observable nominal 100 ms/reset-on-data rule is reduced to an undefined “short” period | `CONTRACT_ASSURANCE_DEFECT` | **STILL OPEN** |
| `L12-R008` | Three Minion-only rows are corrected, but `EXEC-002` still combines adopted behavior with an unapproved observable divergence under `adopted` | `CONTRACT_ASSURANCE_DEFECT` | **STILL OPEN** |

## Blocking findings

### L12-R001 — filesystem cancellation source choice remains unapproved and underspecified

The candidate correctly discovers that the concrete `NodeExecutionEnv` ignores
the declared signal on **ten**, not “nine,” of sixteen operation methods:
`absolutePath`, `joinPath`, `appendFile`, `fileInfo`, `canonicalPath`, `exists`,
`createDir`, `remove`, `createTempDir`, and `createTempFile`.

The proposed rule then chooses the interface over the shipped observable
implementation: every Minion operation must return `aborted` for a pre-aborted
signal. That is an observable divergence for the ten methods above, not merely
an implementation mapping. The recorded governance source approves the WP and
requires direct Pi behavior to be distinguished from Minion mapping; it does
not approve this source choice. `EXEC-002` nevertheless remains `adopted`.

The same section says genuinely unbounded operations only **SHOULD** honor
mid-operation cancellation. That leaves two conforming implementations free to
make observably different choices even for methods where pinned Pi demonstrably
does thread/check the signal. An implementation checkpoint needs a binding
per-method requirement, not advisory language.

**Discriminating witness:** with an existing file and a pre-aborted signal,
pinned `NodeExecutionEnv.fileInfo(path, signal)` ignores the extra runtime
argument and returns metadata. The candidate requires `Err(aborted)` without
touching the filesystem. That difference is deliberate and must either receive
scoped owner approval and a coherent divergence disposition or be changed to
the adopted observable baseline.

**Required correction:** resolve and govern the observable source choice;
correct the ten-of-sixteen inventory; define binding entry and mid-operation
checkpoints per method; split the divergent cancellation rule from direct Pi
adoption in the manifest if the divergence is approved.

### L12-R002 — the corrected symlink table still gets rename wrong

Pinned Pi calls Node's `rename(source, destination)` directly. Renaming a
symlink renames the link directory entry; it does not traverse the link and
rename its target. Replacing a destination symlink replaces the link entry,
not its target. The candidate instead groups `rename_file` with ordinary
content I/O and says it follows a symlink at the final component.

The candidate also leaves `remove` outside its per-operation symlink matrix.
Pinned `rm()` removes the addressed symlink itself; recursive removal of a link
to a directory does not recursively remove the target directory. This is both
observable and safety-relevant.

**Executable witness run during review:** create `target.txt`, create
`link.txt -> target.txt`, then rename `link.txt` to `moved.txt`. Node produced:

```json
{"targetExists":true,"linkExists":false,"movedIsSymlink":true,"targetContent":"X","movedContent":"X"}
```

An implementation following the candidate sentence would act on the target
rather than move the link object. A second probe recursively removed a
directory symlink and observed the link removed while the target directory and
its child remained.

**Required correction:** complete the per-operation matrix, separating
read/write/append traversal from rename/remove directory-entry behavior (and
state any remaining create-directory edge explicitly).

### L12-R003 — the corrected consumer claim still contradicts the frozen design

The candidate spec now accurately cites
`JsonlSessionRepoFileSystem = Pick<FileSystem, ...>` as a real filesystem-only
Pi consumer. The frozen master design at §7 still says every Pi consumer
depends on the `ExecutionEnv` intersection and that no consumer takes
`FileSystem` or `Shell` alone. Both cannot remain current authority.

The temporary-resource part of the original finding is corrected: the draft no
longer claims Pi cleanup removes created temp files/directories.

**Required correction:** synchronize the frozen design's factual architecture
rationale with the verified Pi source, preserving the narrower true statement
that Pi's built-in execution tools use the combined environment.

### L12-R004 — Result/error authority remains contradictory across documents

The candidate spec and `EXEC-001` now correctly treat a non-zero child exit as
successful shell/process observation, and remove unowned stale-version and
remote-unavailable codes. The frozen master design still states, normatively,
that non-zero process exit, stale version, and remote unavailable are typed
execution-seam error values and that every execution failure becomes a typed
error. That directly contradicts the remediated spec's per-operation rule.

**Documentary witness:** compare frozen design §7 lines 1358-1385 with
`spec/execution.md` §2 and `EXEC-001`/`EXEC-004`. A Rust implementer following
the frozen higher-level authority would classify `exit 7` as an error; one
following the candidate returns `Ok({exit_code: 7})`.

**Required correction:** update the frozen design's table/rule to the same
per-operation boundary, or provide a valid authority-preserving correction
mechanism that leaves one unambiguous current rule.

### L12-R005 — `FsTarget` still has mutually incompatible identity requirements

The draft requires stable equality for the same resource's entire lifetime and
different keys for different resources, including through content mutation. It
also expressly permits a canonical-path string as the mechanism. A canonical
path changes when the same underlying file is renamed and is reused if that
file is deleted and a different file is created at the same path. It therefore
cannot satisfy the stated lifetime/resource invariant.

The other expressly permitted example, device+inode identity, handles rename
but cannot predict the future inode needed to make a missing target's pre-create
key equal its post-create key. The contract mixes **resource identity** and
**address/location identity** without choosing which one Layer 13 actually
keys.

**Discriminating matrix:**

| Case | Resource key | Location key |
|---|---:|---:|
| content mutation in place | stable | stable |
| rename `a` to `b` | stable | changes |
| missing `a`, then create `a` | cannot be predicted without provider bookkeeping | stable |
| delete old `a`, create new `a` | changes | reused |

The current prose requires both columns simultaneously while naming mechanisms
that each implement only one.

**Required correction:** choose and govern the identity model; define rename,
delete/recreate, pre-create, symlink, and foreign-target
outcomes consistently; remove permitted mechanisms that cannot satisfy the
chosen invariant.

### L12-R006 — subprocess settlement and ownership remain incomplete

The new typed shape is a substantial improvement, but three load-bearing
choices remain undefined or contradictory:

1. `SpawnOptions.signal` is retained after spawn and “triggers termination,”
   but the following classification rule only defines a signal passed to
   `wait(signal)`. A later abort of the spawn-supplied signal can therefore
   plausibly yield either `Err(aborted)` or `Ok(exit_code: None)` from a plain
   `wait()`.
2. `wait()` does not say whether it settles on direct-child exit independently
   of stdout/stderr EOF, or waits for pipe drain/close. That distinction is
   observable when a detached descendant retains inherited pipe handles and is
   essential to composing the local shell provider.
3. Disposal says a dropped process **MUST NOT** leak, but only **SHOULD** attempt
   termination. It does not define the binding ownership action/reaping
   guarantee that satisfies the MUST, especially for Rust `Drop`, which cannot
   await asynchronous cleanup.

**Discriminating witnesses:** abort only the signal originally supplied to
`spawn`, then call `wait()` without a signal; separately let a direct child exit
while a descendant holds a pipe open; finally drop a still-running process and
observe whether the process/tree remains alive and whether it is reaped. The
candidate does not determine one result for these cases.

**Required correction:** complete the process state/settlement matrix for both
signal sources, direct-exit versus stream lifetime, concurrent/repeated waits,
and mandatory disposal/reaping. Do not prescribe Python or Rust mechanics.

### L12-R007 — shell idle-grace behavior is still not independently reproducible

The candidate correctly retracts “full EOF drain” and records reset-on-data
idle-grace semantics conceptually. Pinned Pi uses a nominal
`EXIT_STDIO_GRACE_MS = 100`: after direct-child exit the timer is armed, and
every later data event resets it; stream end/close may settle earlier. The
candidate reduces the binding rule to a “short idle period.” A 10 ms, 100 ms,
or 2 s grace all fit that adjective but are observably different for delayed
post-exit output and caller latency.

**Discriminating witness:** direct child exits; an inherited pipe emits data at
80 ms and remains open. Pinned Pi resets its 100 ms timer and settles roughly
100 ms after that activity (unless both streams end/close first). A fixed
100-ms-since-exit implementation or an arbitrarily chosen “short” grace
settles at a different point.

**Required correction:** specify the nominal 100 ms grace, reset conditions,
early end/close settlement, and reasonable timing-test tolerance. Keep this
separate from the raw subprocess seam's own wait rule.

### L12-R008 — manifest coherence is only partially repaired

`EXEC-003`, `EXEC-005`, and `EXEC-006` now correctly use the project's
Minion-only `intentional divergence` precedent, and `SubprocessErrorCode` has
been moved out of `EXEC-001`. `EXEC-002`, however, still places direct Pi
filesystem behavior and the candidate's observable interface-over-reference
cancellation divergence under one `adopted` disposition. Calling the latter an
architectural mapping in prose does not make the row machine-coherent.

**Required correction:** after the R001 source/governance decision, give the
divergent rule its own coherent row/disposition or adopt the actual observable
Pi behavior. One row must not combine adoption and intentional divergence.

## Existing Rust architecture and implementability

Certified Rust already provides typed services/context, runtime signals,
Tokio/futures, disposal ownership, and typed errors. It can implement execution
capabilities idiomatically without copying Python mechanics. No certified lower
layer needs reopening.

Rust cannot independently implement this exact draft without guessing:

- whether ten filesystem methods intentionally diverge from the pinned
  implementation and which mid-operation cancellations are mandatory;
- link-object versus target behavior for rename/remove;
- resource identity versus location identity;
- the outcome of a spawn-supplied post-start abort;
- process wait/drain/drop/reaping semantics;
- the actual shell idle-grace constant and reset points.

Those are observable contract decisions, not Rust implementation preferences.

## Structural evidence

Fresh checks against the exact candidate:

- `uv run pytest tests/conformance/test_manifest_validation.py --no-cov -q`:
  `8 passed`.
- Parsed manifest: `101` rows, `101` unique IDs; `EXEC-001` through
  `EXEC-006` are present.
- No Layer-12 canonical runner/scenario or implementation exists yet, as
  expected for this contract checkpoint.
- Candidate changes remain confined to `spec/execution.md` and the six
  manifest rows; no Python/Rust implementation was reviewed or modified.

Structural green gates do not override the semantic blockers.

## Mandatory convergence characterization

### Trigger

Workflow §11.8 trigger A has fired: the same material findings
`L12-R001` through `L12-R008` have survived two independent reviews. Another
ordinary point-fix pass is not valid. Open episode:

```text
EPISODE
    CE-L12-01-01

OPEN FINDINGS
    L12-R001 .. L12-R008

ROOT-CAUSE SURFACE
    Execution-seam source authority and complete cross-language behavior:
    filesystem cancellation/path identity, Result authority, process/shell
    settlement and ownership, and coherent manifest dispositions.
```

### Observable behavior matrix to settle

| Surface | Required cases |
|---|---|
| Filesystem cancellation | every operation: pre-aborted; unbounded operations: abort before first I/O, during first awaited I/O, between multi-step phases, after observable completion |
| Symlinks | lexical path, metadata/list, canonicalization, read/write/append, rename source, rename destination, remove file link, recursive remove directory link, create-dir through existing link |
| Result authority | non-zero child exit, backend operational error, invariant/provider bug, cleanup/terminate best effort |
| Target identity | equivalent lexical paths, symlink/target, content mutation, rename, missing→create, delete→recreate, foreign provider, compatible-world provider |
| Process lifecycle | pre-aborted spawn; spawn-signal abort after start; wait-signal abort; explicit terminate; racing causes; repeated/concurrent wait; pipe error; child exit with inherited pipe; drop/dispose/reap |
| Shell lifecycle | pre-abort vs invalid timeout vs cwd/shell resolution; callback vs timeout vs abort; direct exit plus EOF/close/100-ms reset-on-data grace |
| World compatibility | same identity, different identity, explicitly compatible identities if supported, bridge present/absent, diagnostic ownership |

### Minimal witnesses / negative controls

- R001: known Pi `fileInfo` ignores pre-abort versus proposed Minion abort.
- R002: rename/remove a symlink; a wrong follow-target implementation must fail.
- R003/R004: automated authority-consistency check or direct documentary diff
  against the frozen design; negative control is the current contradictory text.
- R005: one implementation based on canonical path and one based on inode must
  be run through the full target-identity matrix; each exposes a different
  contradiction in the current draft.
- R006: use distinct spawn and wait signals plus a detached pipe holder and a
  live-process disposal probe.
- R007: emit post-exit data before the nominal grace expires and prove timer
  reset; contrast with a timer that never resets.
- R008: manifest validation must reject a row that combines adopted Pi behavior
  and an observable intentional divergence under one disposition.

### Normative deltas needed

- `design/2026-08-20-minion-agent-design.md`: synchronize the two disproved
  factual/normative statements without changing the owner-approved architecture.
- `spec/execution.md`: settle the complete matrices above and remove the
  identity/process contradictions.
- `pi-parity-manifest.yaml`: split/disposition the cancellation divergence and
  synchronize the settled identity/process rules.
- Contract-checkpoint evidence: add the full discriminating matrix and planned
  negative controls; executable conformance remains for the later
  implementation pass.

### Implementation constraints and exclusions

- Do not prescribe Python callback/task mechanics or Rust `Drop`/Tokio
  mechanics; specify observable ownership and settlement.
- Do not reopen certified Runtime/Agent/Auth semantics.
- Do not implement built-in tools or the Layer-13 mutation queue.
- Do not begin Python or Rust implementation until the convergence contract is
  challenged and recorded `AGREED FOR IMPLEMENTATION` under §11.8.5.

## Verdict

```text
shared Layer-12 WP-12.1 contract
    REJECTED

workflow state
    CONTRACT_CONVERGENCE (CE-L12-01-01)

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
`1572bda4bb35a4bf4382e0aaea29b6fafd24ad4a` and docs
`89da9afde11e183d5c4ed7ee19893a819d1cd55b`.

## Next action

Claude performs the §11.8.4 challenge pass against convergence episode
`CE-L12-01-01`, revises the matrix where pinned Pi or the owner-approved Minion
architecture requires it, and records an explicit §11.8.5
`CONVERGENCE CONTRACT — AGREED FOR IMPLEMENTATION` before changing the
candidate. Do not implement Python or Rust Layer 12 and do not start Layer 13
until that checkpoint is agreed.
