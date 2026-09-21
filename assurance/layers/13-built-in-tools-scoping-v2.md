# Layer 13 — Built-in Tools scoping (revision 2)

Mode: scoping / read-only audit. **IMPLEMENTATION AUTHORIZED: NO.**

Targeted remediation of the independent Rust-side scope review (`minion-agent-docs#125` @
`8aa47e478dc91e029420ae0ce34df041acd5a668`, verdict `CHANGES REQUIRED` on all three of scope/
work-package-split/requirement-set; Layer 12 boundary `CLEAR`, not reopened) against revision 1
(`minion-agent-docs#124` @ `ee2e2403b1d905dcfcd2cd41d2108dfc4b428d9c`). Revision 1 is left
unmodified as the historical record of what was actually reviewed; this file supersedes it.
Findings not named below (`L13-S00x` not listed) were not raised and are not revisited.

## Starting state (unchanged from revision 1)

```text
code main:    92aa4be168dc82111832467922089206e858a9c4
docs master:  ec36ed92a9a57f5fc8db4f76103a2d202cb82cbc
pinned Pi:    b7bb00b936dbe21b8e160b3e89efdec361846699
```

## What the review confirmed correct (unchanged, not revisited)

Product-level tool inventory (`read`/`bash`/`edit`/`write`/`grep`/`find`/`ls`); the generic
registry/execution framework staying separate from concrete built-in tools; assigning path/file/
process primitives to Layer 12; Layer 13 as a consumer, not a redefiner, of those seams; the core
`edit` fuzzy-match/apply/preserve-unchanged-lines characterization; the mutation queue's key
derivation, different-key concurrency, and `finally`-based release. Layer 12 boundary: **CLEAR**,
**no reopen required** -- both revisions agree, and this revision does not touch Layer 12.

## L13-S001 — external search-engine acquisition matrix, corrected

Full three-stage precedence (`tools-manager.ts`, now read in full):

```text
1. Pi's own managed tools directory (getBinDir()) -- if a previously-downloaded
   binary already exists there, use it directly. No version check on reuse.
2. System PATH -- fd or fdfind (fd only); rg (ripgrep) -- via a plain executable-
   exists probe. Whatever version is on PATH is used unverified.
3. Download -- fetch the LATEST GitHub release tag for sharkdp/fd or
   BurntSushi/ripgrep, EXCEPT: fd specifically on darwin+x64 is hardcoded to
   version "10.3.0" regardless of what is actually latest at download time (no
   comment in source explaining why; not investigated further in this pass).
   The downloaded binary is cached into the managed tools directory, so it is
   found by stage 1 on every subsequent run on that machine.
```

This corrects revision 1's flattened "PATH first, else latest, both unpinned" framing. The
overall conclusion revision 1 drew -- pinned Pi does not define one single, universal `fd`/`rg`
semantic version across all installations -- still holds under the full matrix: stage 1 depends on
per-machine download history, stage 2 depends on the end user's own system binary, and stage 3 is
version-floating except for exactly one platform/architecture combination. The Darwin x64
exception is real but narrow; it does not supply a universal pin and does not change High-risk
surface #1's conclusion in the Acceptance-oracle-strategy section below, which is otherwise
unchanged from revision 1 and still stands.

## L13-S002 — Pi audit completed; corrections to specific tool descriptions

`grep.ts` and `ls.ts` are now read in full (previously partial); bash's shell-selection helper
(`utils/shell.ts:getShellConfig`) is now read. Corrections to revision 1's built-in tool inventory
follow; everything in revision 1 not named below is unchanged.

**`read` -- image content is not omitted for non-vision models.** Revision 1 said non-vision
models "get a text note instead of actual image, image content omitted." That is wrong: on a
successful image read, `content` unconditionally includes both the text note *and* the image
block (`content = [{type:"text",...}, {type:"image",...}]`); the non-vision note is appended text,
not a replacement. The tool itself never omits the image; if omission happens at all, it happens
in a later request-projection step outside this tool's own boundary, which this pass did not
audit and does not claim.

**`grep` -- context lines are Pi's own logic, not delegated to `rg`.** The actual invocation is
`rg --json --line-number --color=never --hidden [--ignore-case] [--fixed-strings] [--glob <glob>]
-- <pattern> <searchPath>` -- no `--context`/`-C` flag is ever passed to `rg`. Context is
reconstructed in TypeScript: matches are collected from `rg`'s JSON event stream during streaming,
then (only after `rg` exits, so a custom async `readFile` backend can be awaited) each matched
file is re-read once (cached per file, CRLF/CR normalized to LF by Pi itself, not by `rg`) and a
context window (`[lineNumber - context, lineNumber + context]`, clamped to file bounds) is sliced
directly out of those lines. When `context === 0` and `rg` already supplied the matched line's
text in its JSON event, that text is used directly without a re-read (a pure optimization for the
no-context case). Match/context line formatting mirrors grep -C convention (`path:N: text` for the
match line, `path-N- text` for context lines). Each individual output line is separately truncated
to `GREP_MAX_LINE_LENGTH` (500 chars, `"... [truncated]"` suffix) before the whole output is
byte-truncated (no line cap; match count is the other cap, default 100, `rg`'s own child process
is killed once the limit is reached). Exit code 1 from `rg` (its own "no matches" convention) is
treated as success/empty, not a tool error. Semantic authority for grep's context/formatting logic
is therefore `PI_SOURCE_ALGORITHM`, not `DELEGATED_LIBRARY_BEHAVIOR` -- only the underlying
pattern match itself (which lines are matches at all) is delegated to `rg`.

**`find` -- "delegates all glob matching to `fd`" applies to the default implementation only.**
`FindOperations.glob` is a pluggable override (the same pattern every other tool's `*Operations`
interface already has, e.g. `GrepOperations`, `ReadOperations`) allowing a custom glob
implementation (for SSH/remote backends) to replace the `fd` child-process path entirely. Revision
1's "delegates all glob matching" claim is corrected to apply explicitly to `find`'s default local
implementation; the custom-operations path is a distinct, already-abstracted seam and does not
change the `DELEGATED_LIBRARY_BEHAVIOR` classification of the *default* implementation.

**`ls` -- previously-omitted observable rules, now recorded.** Entries are sorted
case-insensitively via `a.toLowerCase().localeCompare(b.toLowerCase())`; directories get a
trailing `/` suffix (determined by a per-entry `stat` after the initial `readdir`); an entry whose
individual `stat` call fails is silently **skipped** (not included, not surfaced as a partial
error) via a bare `continue`; the entry-count limit is applied only against successfully-stat'd
entries (an entry skipped due to a stat failure does not count against the limit); zero results
(an empty directory, or every entry happening to fail `stat`) produces the literal text
`"(empty directory)"` with no truncation details. Output is byte-truncated only, same as `find`/
`grep` (no separate line cap; entry count is the other cap, default 500).

**`bash` -- shell-selection order, now recorded.** `getShellConfig` resolves, in order: (1) an
explicit caller-supplied shell path, if it exists on disk, else a hard error; (2) on Windows, Git
Bash at `%ProgramFiles%\Git\bin\bash.exe` or `%ProgramFiles(x86)%\Git\bin\bash.exe` if either
exists, else a `bash.exe` found via `where` on `PATH` (verified to actually exist on disk, since
`where` can report stale/nonexistent paths); (3) on Unix, `/bin/bash` first per the function's own
doc comment (exact fallback chain to `PATH` then `sh` not re-verified line-by-line in this pass --
open item, not a blocking one, for implementation scoping). Command transport is argv-based
(`-c <command>`) in the normal case; it switches to stdin-based (`-s`, command written to the
spawned shell's stdin then the stream closed) only when the resolved shell path matches a specific
legacy-WSL-bash pattern (`C:\Windows\System32\bash.exe` or `...\Sysnative\bash.exe`, case- and
separator-insensitive).

## L13-S003 — mutation queue: call-order atomicity and provider scoping, bound explicitly

Revision 1 correctly identified that the queue key should be Layer 12's `FsTarget.target_key`, but
did not bind the atomicity guarantee that makes Pi's own queue FIFO-by-call-order rather than
FIFO-by-key-resolution-completion-order. Pinned Pi's `withFileMutationQueue` uses a single global
`registrationQueue` promise chain to serialize exactly two steps -- deriving the (asynchronous,
because it does a `realpath` I/O call) key, and linking the operation onto that key's per-key
tail -- as one atomic critical section, before releasing the global gate and letting the wrapped
operation itself run concurrently with unrelated keys. Without that global gate, two calls
targeting the same file could resolve their keys out of call order (since `realpath` is async I/O
with no ordering guarantee across concurrent calls) and enqueue in the wrong order despite both
eventually deriving the identical correct key.

**Corrected `TOOL-010` requirement (supersedes revision 1's TOOL-010 in substance, renumbered
below per L13-S005):** the Layer 13 mutation queue's reservation/registration step -- resolve the
target's `FsTarget`/`target_key` via the already-certified Layer 12 `resolve()`, then link the
operation onto that key's per-key FIFO tail -- MUST itself be one atomic, globally-ordered critical
section across all pending `write`/`edit` calls, so that same-target calls enqueue in the order
they were made, not the order their (asynchronous) target resolution happens to complete in. The
critical section covers registration only; the wrapped filesystem operation itself must still run
concurrently with unrelated keys once registered, exactly as in Pi. This requires no Layer 12
semantic change -- it consumes `resolve()`/`FsTarget` as already certified.

**Queue ownership / provider scoping (new, requested by the review):** an opaque `target_key`
string alone is not necessarily a safe cross-provider namespace -- Python's `FsTarget.target_key`
is a bare string with no provider tag, and Rust's `FsTarget`/`TargetKey` similarly does not expose
provider identity through the key alone. Two different `FileSystem`/`ctx.fs` providers (e.g. two
independent remote/virtual providers) could in principle produce coincidentally identical
`target_key` values for genuinely unrelated targets, which a queue keyed on the bare string alone
would then incorrectly serialize together. The Layer 13 contract must scope the mutation queue per
provider/`FileSystem` instance (or otherwise incorporate provider identity into the effective
queue key), not assume a single global keyspace the way this single-provider-per-process Pi
implementation implicitly can.

## L13-S004 — work-package split, revised

Revision 1's Candidate B coupled `find`/`grep` (which the same artifact calls
governance-blocked, pending the L13-S001 engine-pinning owner decision) into the same package as
`read`/`ls` (unblocked, native, lowest risk) -- directly contradicting its own stated rationale
that this package should be independently certifiable and close first. Corrected split, still
chosen by dependency shape rather than filename grouping:

```text
WP-13.1  Native filesystem query tools: read, ls
         (no mutation queue, no subprocess, no external-binary dependency --
         genuinely unblocked; can close first)

WP-13.2  Filesystem mutation tools: write, edit, the shared mutation queue
         (unchanged from revision 1's rationale: coupled by the queue, its
         FsTarget.target_key-derived keying, and the identical
         cancellation-vs-lock-ordering subtlety)

WP-13.3  bash
         (unchanged from revision 1's rationale: the only tool consuming
         ctx.subprocess; zero technical dependency on the mutation queue or
         on WP-13.4's engine question)

WP-13.4  Delegated search tools: find, grep
         (split out from WP-13.1 specifically because both are blocked on the
         L13-S001 external-engine pinning owner decision; grouping them
         separately means that decision blocks only this package, not the
         genuinely-unblocked read/ls surface)
```

`write`/`edit`+queue (WP-13.2) and `bash` (WP-13.3) are unchanged from revision 1 -- the review did
not fault their grouping, only the `read`/`ls` vs. `find`/`grep` coupling.

## L13-S005 — requirement IDs reassigned to a non-colliding range

`pi-parity-manifest.yaml` already contains certified `TOOL-001` through `TOOL-021`, plus
`TOOL-023` and `TOOL-024` (verified directly against the manifest, not merely on the reviewer's
say-so: `grep -n "^- id: TOOL-" pi-parity-manifest.yaml` in `minion-agent` lists exactly those 23
IDs). Those rows govern the generic tool-execution framework (batch sequencing, hooks,
cancellation -- e.g. `TOOL-001`'s `pi: packages/agent/src/agent-loop.ts::executeToolCalls`,
`python: src/minion_agent/tools/batch.py`), a different, already-certified surface from the
built-in tools this scoping pass covers. `TOOL-022` does not currently appear in the manifest;
this revision does **not** claim it as available, since an apparent gap in an existing certified
namespace may be intentional/reserved for reasons not visible to this audit -- flagged as an open
note, not assumed free.

Layer 13's built-in-tool requirements are renumbered into an unclaimed, contiguous block starting
at `TOOL-025` (immediately past the highest existing ID, skipping the unclaimed `TOOL-022` gap
entirely rather than resolving its status here):

```text
TOOL-025  read: argument schema, offset/limit, truncation (head)
          Pi source: read.ts, truncate.ts     DIRECT_PI_PARITY
          WP: WP-13.1                          depends on: (none)

TOOL-026  read: file:// / path-argument resolution
          Pi source: path-utils.ts             MINION_ARCHITECTURAL_MAPPING
          WP: WP-13.1                          depends on: Layer 12 resolve_local_path

TOOL-027  read: macOS filename-fallback heuristics [owner disposition: adopt / drop]
          Pi source: path-utils.ts             PLATFORM_BEHAVIOR / MINION_EXTENSION
          WP: WP-13.1                          depends on: TOOL-026

TOOL-028  ls: argument schema, case-insensitive sort, '/' suffix, stat-failure
          skip, entry-limit-after-skip, empty-directory text, byte truncation
          Pi source: ls.ts, truncate.ts        DIRECT_PI_PARITY
          WP: WP-13.1                          depends on: (none)

TOOL-029  write: schema, overwrite semantics, parent-dir auto-creation
          Pi source: write.ts                  DIRECT_PI_PARITY
          WP: WP-13.2                          depends on: TOOL-032

TOOL-030  edit: multi-edit exact-match algorithm, uniqueness/overlap/no-op rejection
          Pi source: edit-diff.ts              DIRECT_PI_PARITY
          WP: WP-13.2                          depends on: TOOL-032

TOOL-031  edit: fuzzy-match algorithm, unchanged-line preservation, BOM and
          line-ending detection/restoration
          Pi source: edit-diff.ts              DIRECT_PI_PARITY
          WP: WP-13.2                          depends on: TOOL-030

TOOL-032  write/edit: mutation-queue key derivation, atomic call-order
          registration, provider-scoped queue identity, FIFO-per-key
          serialization (L13-S003 corrected characterization)
          Pi source: file-mutation-queue.ts    MINION_ARCHITECTURAL_MAPPING
          WP: WP-13.2                          depends on: Layer 12 FsTarget.target_key

TOOL-033  write/edit: cancellation-vs-lock ordering (check-after-await)
          Pi source: write.ts, edit.ts         MINION_ARCHITECTURAL_MAPPING
          WP: WP-13.2                          depends on: TOOL-032

TOOL-034  bash: argument schema, no-default-timeout, shell-selection order,
          argv-vs-stdin command transport
          Pi source: bash.ts, shell.ts         DIRECT_PI_PARITY (schema/selection) /
                                                MINION_SHARED_CONTRACT (kill/wait)
          WP: WP-13.3                          depends on: Layer 12 ctx.subprocess

TOOL-035  bash: output truncation (tail, byte+line, temp-file-on-truncation)
          Pi source: bash.ts, truncate.ts      DIRECT_PI_PARITY
          WP: WP-13.3                          depends on: TOOL-034

TOOL-036  find: argument schema, default-fd-delegation vs. custom-operations
          scoping, path-relativization, byte-only truncation
          Pi source: find.ts                   DIRECT_PI_PARITY (shape) / see TOOL-038
          WP: WP-13.4                          depends on: (none)

TOOL-037  grep: argument schema, Pi-owned context reconstruction (not
          delegated to rg), per-line and byte truncation
          Pi source: grep.ts                   PI_SOURCE_ALGORITHM (context/formatting) /
                                                see TOOL-038 (match delegation)
          WP: WP-13.4                          depends on: (none)

TOOL-038  find/grep: match-engine parity strategy for an explicitly pinned
          engine, given Pi's own three-stage unpinned/narrowly-pinned
          acquisition matrix (L13-S001 corrected characterization)
          Pi source: tools-manager.ts          MINION_EXTENSION -- OWNER DECISION REQUIRED
          WP: WP-13.4                          depends on: TOOL-036, TOOL-037
```

`TOOL-039` and above remain unclaimed for this pass; the set above (15 entries, same count as
revision 1) is provisional pending review, not final wording.

## Unchanged from revision 1

Mutation queue characterization's key-derivation description, Path resolution section, Truncation
constants, Parity classification table's substance (surfaces renamed to match new TOOL IDs above,
classifications unchanged), Semantic authority table, High-risk surfaces #2-#5, Acceptance-oracle
strategy, Cross-language impact, and Open questions are all unchanged from revision 1 except where
explicitly corrected above (grep/find semantic-authority notes now reflect L13-S002's grep
correction; the find/grep oracle strategy explicitly incorporates L13-S001's corrected matrix but
reaches the same "BLOCKED on owner decision" conclusion).

## Implementation authorized

```text
NO
```
