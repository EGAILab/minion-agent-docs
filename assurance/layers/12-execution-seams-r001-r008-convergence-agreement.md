# Layer 12, WP-12.1 — `L12-R001`–`L12-R008` convergence characterization challenge and agreement

**Episode:** `CE-L12-01-01`
**Trigger:** `agent-workflow.md` §11.8, trigger A — the same eight material findings survived two
independent reviews (`minion-agent-docs#111` @ `092f63a5e3136f598fe1e508d4c60f6d8fe4dc17`;
`minion-agent-docs#112` @ `89d826e101310c07a59eddd072f4d80cd7384ef0`).
**This document performs:** the §11.8.4 challenge pass against the re-review's own characterization,
and records the §11.8.5 `AGREED FOR IMPLEMENTATION` checkpoint.
**Candidate this episode is about:** code `1572bda4bb35a4bf4382e0aaea29b6fafd24ad4a` (PR #40), docs
`89da9afde11e183d5c4ed7ee19893a819d1cd55b` (PR #110) — both REJECTED a second time; neither is
changed by this document. The coherent fix pass (§11.8.6) is a separate, later step.

---

## 1. Independent re-verification of the characterization

Every claim in the re-review was independently re-checked against pinned Pi source
(`b7bb00b936dbe21b8e160b3e89efdec361846699`) before being accepted, not taken on the review's own
prose. All are confirmed correct.

- **`L12-R001` "ten, not nine" methods**: independently recounted directly from
  `env/nodejs.ts`'s own concrete method signatures: `absolutePath`, `joinPath`, `appendFile`,
  `fileInfo`, `canonicalPath`, `exists`, `createDir`, `remove`, `createTempDir`, `createTempFile` —
  ten methods, confirmed. The prior remediation's own prose said "nine" while its own adjacent list
  literally named all ten -- a plain counting error, confirmed.
- **`L12-R002` `rename`/`remove` symlink semantics**: independently confirmed `renameFile` calls
  Node's raw `rename(source, destination)` (`nodejs.ts:594`) and `remove` calls raw
  `rm(resolved, {recursive, force})` (`nodejs.ts:664`) -- both direct OS-primitive wrappers with no
  symlink-dereferencing flag. Standard POSIX semantics (confirmed, not merely asserted): `rename()`
  operates on the source directory entry itself, never its target; `rm()`/`unlink()` on a symlink
  removes the link entry, and recursive removal of a directory-symlink does not recurse into the
  target directory's own contents. The prior remediation's classification of `rename_file` as
  ordinary symlink-following content I/O was factually wrong; `remove` was omitted from the matrix
  entirely. Both confirmed.
- **`L12-R003`/`L12-R004` frozen-design contradiction**: independently re-read
  `design/2026-08-20-minion-agent-design.md` §7 directly. Lines 1301-1305 still state "no consumer
  takes `FileSystem` or `Shell` alone" verbatim. The normative Values table (~line 1380) still
  lists `stale version`, `non-zero process exit`, and `remote unavailable` as seam-error Values.
  Both are the EXACT source the original (already-corrected-in-derived-spec) mistakes were copied
  from. Confirmed: the frozen design itself, not only the derived spec, needs correction.
- **`L12-R005` identity-model matrix**: independently re-derived the four-case table by direct
  reasoning (not merely trusting the review's own table): a rename-survives requirement and a
  not-yet-existing-target requirement cannot both be satisfied by one mechanism (device+inode
  cannot predict a future inode for a missing path; a canonical-path string changes on rename).
  Confirmed as a genuine logical incompatibility in the prior draft, not a wording nitpick.
  Independently re-read `packages/agent/src/harness/tools/file-mutation-queue.ts`'s own
  `getMutationQueueKey` (lines 20-26): Pi's own REAL mutation-queue key is a canonical-path STRING
  (falling back to the absolute path when canonicalization fails, e.g. for a not-yet-existing
  path) -- genuinely location-based, and NOT designed to survive rename at all. This is the
  concrete Pi evidence the prior draft never actually checked before inventing a stronger,
  self-contradictory requirement.
- **`L12-R006` process/stream gaps**: independently re-read the exact `Process`/`wait()` shape in
  the rejected candidate spec; confirmed the three gaps as described (spawn-signal vs. wait-signal
  ambiguity; `wait()`'s own relationship to stdio EOF left unstated; MUST/SHOULD disposal
  inconsistency).
- **`L12-R007` idle-grace constant**: independently re-read `nodejs.ts`'s own `armIdleTimer`/
  `onData`/`onExit` (lines ~305-334): `onData` re-arms the idle timer (`armIdleTimer`, which itself
  clears any existing timer before scheduling a new one) whenever data arrives AFTER exit has
  already occurred -- confirmed a genuine reset-on-data timer, constant `EXIT_STDIO_GRACE_MS =
  100` (ms), not a vague "short" period.
- **`L12-R008`**: a direct consequence of `L12-R001`'s own resolution (below) — confirmed no
  separate technical claim beyond what `L12-R001` already establishes.

No part of the characterization is rejected. All eight findings remain open, refined, as
characterized.

## 2. Challenge pass (`agent-workflow.md` §11.8.4)

**Is the Pi source mapping correct?** Yes, independently confirmed above for every claim.

**Is the behavior matrix complete enough to distinguish realistic wrong implementations?** Yes —
the re-review's own "Observable behavior matrix to settle" table (reproduced and adopted in §4
below) covers every dimension a realistic alternative implementation could get wrong.

**Are any cases implementation mechanics rather than observable semantics?** The re-review's own
"Implementation constraints and exclusions" already draws this line correctly (no Python
callback/task mechanics, no Rust `Drop`/Tokio mechanics prescribed) and is adopted unchanged.

**Does any proposed fix silently reopen a lower certified layer?** No. Every fix is confined to the
new Layer 12 surface (`spec/execution.md`, the frozen design's own §7 factual rationale, and the
`EXEC-###` manifest rows). No certified Runtime/Agent/Auth semantics are touched.

**Can both Python and Rust implement the rule idiomatically?** Yes, WITH one correction to the
characterization's own framing: `L12-R006`'s disposal requirement as literally worded ("MUST NOT
leak" on implicit disposal) is not achievable in idiomatic Rust, since `Drop` cannot `await`
asynchronous cleanup. §3.4 below resolves this by NOT requiring implicit-disposal safety as a MUST
at all -- explicit `wait()`/`terminate()` is the only guaranteed-safe path in either language, which
both Python and Rust can implement identically.

**Does the defect's root cause depend on an extensibility point one language's certified lower
layer exposes and the other does not?** No -- Layer 12 has no certified lower-layer extension-point
dependency of this kind; both languages start from the same footing.

**Are all previous review findings represented by an executable or documentary acceptance
criterion?** Yes -- §5 below states one for each of `L12-R001`-`L12-R008`.

## 3. Design decisions (resolving the two deepest findings)

### 3.1 `L12-R001`/`L12-R008` — cancellation: adopt observable Pi behavior, not the fuller interface

**Decision:** Minion's `ctx.fs` contract adopts pinned Pi's own ACTUAL, OBSERVABLE reference-
implementation cancellation behavior as `DIRECT_PI_PARITY` -- including its incompleteness -- rather
than "upgrading" to the type interface's fuller, unfulfilled promise. This project's own established
epistemology (every prior Pi-parity investigation in this project's history, without exception, has
treated live observable behavior as authoritative over a type declaration alone) applies here
without a new exception. Choosing the fuller interface over the shipped behavior would have been a
genuine, material INTENTIONAL DIVERGENCE requiring its own owner escalation (`agent-workflow.md`
§11.7) that the existing governance record does not grant; adopting the observable behavior exactly
needs no such escalation at all, and is the more conservative, more clearly Pi-faithful choice.

**Binding per-operation table** (replaces the prior "SHOULD honor mid-operation cancellation"
advisory language with a firm requirement matching Pi's own exact, confirmed behavior):

```text
checks pre-aborted AND honors mid-operation cancellation (signal threaded to the underlying I/O):
    read_text_file, read_binary_file, write_file

checks pre-aborted AND re-checks at each loop iteration:
    read_text_lines, list_dir

checks pre-aborted only, no mid-operation checkpoint (a single fast syscall):
    rename_file

does not accept or check a signal at all -- MATCHES Pi exactly, not a Minion gap:
    absolute_path, join_path, append_file, file_info, canonical_path, exists, create_dir,
    remove, create_temp_dir, create_temp_file
```

This resolves `L12-R008` as a direct consequence: `EXEC-002` becomes coherently `adopted` in full
(no mixed disposition), since there is no longer any divergence bundled into it at all.

### 3.2 `L12-R002` — complete symlink matrix, `rename`/`remove` corrected

```text
lexical path resolution (absolute_path, join_path)  -- never traverses (touches no filesystem object)
lstat-based metadata (file_info, list_dir, exists)   -- never traverses (reports kind: symlink)
explicit canonicalization (canonical_path)           -- always traverses (its entire purpose)
content I/O (read_text_file, read_binary_file,
             write_file, append_file)                -- traverses at the final path component
                                                          (matches OS open() with no no-follow flag)
rename_file                                          -- NEVER traverses -- operates on the source
                                                          directory entry itself (the link object,
                                                          if source is a symlink); replacing an
                                                          existing destination replaces the
                                                          destination's own directory entry, not a
                                                          target it might point to
remove                                                -- NEVER traverses -- removes the addressed
                                                          symlink itself; recursive removal of a
                                                          directory-symlink removes the link only,
                                                          never recurses into the target directory's
                                                          own contents (safety-relevant: this is the
                                                          case a caller relies on to avoid an
                                                          accidental cascading delete through a link)
create_dir through an existing symlink                -- follows platform mkdir semantics at the
                                                          existing prefix; no separate Minion rule
```

### 3.3 `L12-R005` — `FsTarget` identity: location-based, matching Pi's own real mechanism

**Decision:** `target_key` is LOCATION-derived (canonical-path-based), NOT resource-derived
(inode-based), matching pinned Pi's own real `getMutationQueueKey` mechanism exactly
(`file-mutation-queue.ts:20-26`: canonical path, falling back to absolute path when canonicalization
fails for a not-yet-existing target). This DROPS the prior draft's own over-specified "survives
rename" requirement, which Pi's own real mechanism never provides and a future Layer 13 queue never
actually needs (Pi's own queue simply treats a renamed file's old and new paths as unrelated queue
keys, and that is safe -- not a defect).

```text
resolve(path) -> target_key = canonical_path(path) if it exists, else absolute_path(path)
    (mirrors Pi's own getMutationQueueKey exactly, including the not-yet-existing fallback)

content mutation in place        -> target_key UNCHANGED (same path, same canonicalization)
rename a -> b                    -> target_key CHANGES (a and b are different canonical paths;
                                     this is CORRECT, not a defect -- Pi's own queue does the same)
missing a, then create a         -> target_key STABLE across the create (both resolve to a's own
                                     absolute/canonical path before and after)
delete old a, create new a       -> target_key REUSED (both resolve to the same path) -- correct
                                     and safe: serializing the new file's own operations against
                                     the same queue key the old file used is conservative, not wrong
symlink and its target           -> SAME target_key (canonical_path already fully resolves
                                     symlinks, §3.2 above, so this falls out for free)
```

Explicitly REMOVED from the permitted-mechanism list: a content hash (already excluded, unchanged)
AND a device+inode pair (newly excluded -- cannot satisfy the not-yet-existing-target requirement,
per §1's own confirmed matrix). Canonical-path-string is now the ONE specified mechanism, not one
option among several, since the "legitimate implementation choice" framing is what let two
incompatible identity models coexist in the prior draft.

### 3.4 `L12-R006` — process/stream contract completed

- **One signal, not two.** `Process.wait()` takes NO signal parameter of its own. Cancellation
  flows ONLY through `spawn()`'s own `options.signal`. `wait()` returns `Err(aborted)` when the
  process was killed because that ORIGINAL spawn-supplied signal fired (at any point, before or
  after the `wait()` call itself); it returns `Ok(ExitStatus{exit_code: None})` when the process was
  killed via an explicit `terminate()` call with no spawn-signal involvement. This removes the
  ambiguity entirely -- there is no longer a second, independently-abortable `wait(signal)` call to
  reconcile against the first.
- **`wait()` settles on process exit alone**, independent of stdio stream state. `ctx.subprocess` is
  the lower-level primitive; a caller wanting BOTH "process exited" and "I have drained all output"
  must do both explicitly (`wait()` plus continued `read_chunk()` calls until each stream reports
  EOF). `ctx.shell`'s own local provider, built on `ctx.subprocess`, layers ITS OWN idle-grace
  completion heuristic (§3.5 below) on top of these lower-level primitives -- that heuristic belongs
  to `ctx.shell`, not to the raw `ctx.subprocess` seam, which stays simple and composable.
- **Disposal:** `wait()` or `terminate()` is the ONLY guaranteed-safe disposal path, in EITHER
  language equally -- this is a caller obligation, not an implicit-cleanup guarantee. Failing to
  call either before a `Process` value is dropped/goes out of scope is UNDEFINED behavior (a caller
  bug), not a scenario the API promises to handle safely. This removes the prior MUST/SHOULD
  contradiction by not making a MUST claim implicit disposal cannot actually satisfy in idiomatic
  Rust (`Drop` cannot await async cleanup) -- Python MAY additionally offer an async context-manager
  form whose `__aexit__` calls `terminate()`, as an ergonomic convenience, but the underlying
  contract does not depend on it.

### 3.5 `L12-R007` — exact idle-grace constant and reset semantics

`ctx.shell`'s own `exec()` completion rule (this remains `ctx.shell`'s own concern, per §3.4 above,
built on `ctx.subprocess`'s simpler primitives): once the directly-spawned process exits, arm a
100 ms idle-grace timer. Any stdout/stderr data received before that timer fires RESETS it (clears
and re-arms for another 100 ms). `exec()` settles once the timer fires with no further data having
reset it, OR once both stdout and stderr streams have independently ended/closed, whichever happens
first. This is `DIRECT_PI_PARITY` (`nodejs.ts` `EXIT_STDIO_GRACE_MS = 100`, `armIdleTimer`/`onData`).

## 4. Observable behavior matrix (adopted from the re-review's own characterization, §11.8.3)

```text
Filesystem cancellation  -- every operation: pre-aborted; unbounded operations additionally:
                             abort before first I/O, during first awaited I/O, between multi-step
                             phases (mkdir-then-write), after observable completion
Symlinks                  -- lexical path, metadata/list, canonicalization, read/write/append,
                             rename source, rename destination, remove file-link, recursive remove
                             directory-link, create-dir through an existing link
Result authority           -- non-zero child exit, backend operational error, invariant/provider
                             bug, cleanup/terminate best effort
Target identity             -- equivalent lexical paths, symlink/target, content mutation, rename,
                             missing->create, delete->recreate, foreign provider, compatible-world
                             provider
Process lifecycle          -- pre-aborted spawn; spawn-signal abort after start; explicit
                             terminate; racing causes; repeated/concurrent wait; pipe error; child
                             exit with inherited pipe held by a descendant; drop/dispose without
                             explicit wait/terminate (documented as undefined, not silently safe)
Shell lifecycle             -- pre-abort vs. invalid timeout vs. cwd/shell resolution; callback vs.
                             timeout vs. abort; direct exit plus EOF/close/100 ms reset-on-data grace
World compatibility        -- same identity, different identity, explicitly compatible identities
                             if supported, bridge present/absent, diagnostic ownership
```

## 5. Acceptance witnesses (one per finding, discriminating -- to become permanent regression
   evidence during the coherent fix pass, `agent-workflow.md` §11.8.7.1)

```text
L12-R001  setup: existing file, pre-aborted signal
          call:  file_info(path, signal)
          expect: Ok(FileInfo{...}) -- matches Pi's own observed behavior exactly (no signal check)
          negative control: a candidate requiring Err(aborted) here would be WRONG under this
          agreement (the opposite of the rejected draft's own requirement)

L12-R002  setup: target.txt="X"; link.txt -> target.txt
          call:  rename_file("link.txt", "moved.txt")
          expect: target.txt unchanged; moved.txt is itself a symlink (kind: symlink) whose
          content, read through it, is still "X"
          negative control: an implementation that moves/renames target.txt itself, or that
          resolves the link before renaming, fails this witness

L12-R003  setup: read design/2026-08-20-minion-agent-design.md section 7 and spec/execution.md
          section 1 side by side after the coherent fix pass
          expect: both state the SAME narrower claim (Pi's execution tools require the
          combination; JsonlSessionRepoFileSystem is the counter-example to a blanket claim) --
          no remaining contradiction between frozen design and derived spec

L12-R004  setup: read design section 7's Values table and spec/execution.md section 2 side by side
          expect: both state non-zero exit as a SUCCESS value, not a Result error; both list the
          SAME FsErrorCode/ShellErrorCode/SubprocessErrorCode taxonomy with no unmapped entries

L12-R005  setup: file a.txt; b.txt with identical content "same"; resolve both
          expect: distinct target_key values (never collide on content); rename a.txt to c.txt
          changes its own target_key; deleting and recreating a.txt reuses the same target_key
          negative control: a device+inode-based implementation fails the missing-then-create case
          (cannot predict the future inode); a content-hash implementation fails both the
          content-mutation-stability case and the distinct-identical-files case

L12-R006  setup: spawn a process with a signal; abort that ORIGINAL signal; call wait() with no
          argument
          expect: Err(aborted) -- the classification derives from the spawn-time signal, not a
          separate wait-time one (which no longer exists)
          second setup: drop a running Process without calling wait() or terminate()
          expect: documented as undefined/caller-error, not required to be leak-safe

L12-R007  setup: a direct child exits; its own stdout emits one more chunk at +80ms; nothing else
          happens
          expect: exec() settles at approximately +180ms (80ms + a fresh 100ms grace from the
          reset), not at +100ms (which would mean the timer did not reset on the +80ms data)

L12-R008  setup: run the manifest validator against EXEC-002 after the coherent fix pass
          expect: exactly one disposition (adopted), no PI_BEHAVIOR_UNCERTAIN flag remaining, no
          divergent rule bundled into it
```

## 6. Normative deltas required (coherent fix pass, next step -- not performed by this document)

```text
design/2026-08-20-minion-agent-design.md section 7
    -- narrow factual correction only, preserving the owner-approved three-seam architecture:
       "no consumer takes FileSystem or Shell alone" -> "Pi's own execution tools require the
       combination; a real FileSystem-only consumer (JsonlSessionRepoFileSystem) also exists";
       remove non-zero-exit/stale-version/remote-unavailable from the Values table, matching the
       per-operation boundary already adopted in spec/execution.md. This is a citation-accuracy
       correction to the design's own stated Pi-source rationale, not a change to the owner-
       approved three-seam/FsTarget/execution-world architecture itself -- no fresh owner
       escalation required, matching this project's own established precedent for correcting
       stale/incorrect source-citation prose (Layer 11 Pass 2 Slice C, L11-SC-R026).

spec/execution.md
    -- section 3.1: replace the "SHOULD honor mid-operation cancellation" framing with the firm
       per-operation table in section 3.1 above (matching Pi's own observed behavior exactly, no
       divergence);
    -- section 3.2: correct rename_file's own symlink classification; add remove and
       create_dir-through-a-link to the per-operation matrix;
    -- section 4: replace the identity-mechanism discussion with the location/canonical-path
       model in section 3.3 above; remove device+inode as a permitted mechanism;
    -- section 6: remove wait()'s own separate signal parameter; state wait()'s independence from
       stdio state explicitly; correct the disposal MUST/SHOULD to the undefined-on-implicit-
       disposal framing in section 3.4 above;
    -- section 5.6/new subsection: state the exact 100ms EXIT_STDIO_GRACE_MS reset-on-data rule
       from section 3.5 above, explicitly as ctx.shell's own layered concern, not ctx.subprocess's;
    -- section 10: extend the witness matrix with section 5 above's entries.

pi-parity-manifest.yaml
    -- EXEC-002: rule text updated to the firm per-operation cancellation table and the corrected
       symlink matrix; remains disposition: adopted (no divergence, no split needed);
    -- EXEC-003: rule text updated to the location/canonical-path identity model;
    -- EXEC-005: rule text updated to the one-signal process/stream contract;
    -- EXEC-004: rule text updated to cite the exact 100ms reset-on-data constant.
```

## 7. Convergence contract

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION

EPISODE
    CE-L12-01-01

OPEN FINDINGS
    L12-R001 L12-R002 L12-R003 L12-R004 L12-R005 L12-R006 L12-R007 L12-R008

ACCEPTANCE WITNESSES
    section 5 above (one per finding)

NORMATIVE DELTAS
    design/2026-08-20-minion-agent-design.md section 7 (factual correction only)
    spec/execution.md sections 1, 2, 3.1, 3.2, 4, 5.6, 6, 10
    pi-parity-manifest.yaml EXEC-002, EXEC-003, EXEC-004, EXEC-005

NEXT_OWNER
    Claude (coherent fix pass, agent-workflow.md section 11.8.6)
```

This checkpoint means the remaining observable surface is sufficiently characterized for one
coherent implementation-of-the-contract pass -- it is NOT final contract approval. A targeted
closure review (`agent-workflow.md` §11.8.7) of the resulting exact candidate, with the negative-
control evidence required by §11.8.7.1, remains mandatory before `FINAL_CONTRACT_REVIEW`. No Python
or Rust Layer 12 implementation, and no Layer 13 work, is authorized by this document.
