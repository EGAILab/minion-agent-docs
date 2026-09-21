# Layer 13 — Built-in Tools scoping (revision 3)

Mode: scoping / read-only audit. **IMPLEMENTATION AUTHORIZED: NO.**

Targeted remediation of the independent Rust-side re-review (`minion-agent-docs#126` @
`e63c4163bb4841a3a6891360edda117aada5ce97`, reviewing revision 2 at `538d2bf3b57b1206404643b2d52c2a52512a875e`)
against revision 2 (`minion-agent-docs#124` @ `538d2bf3b57b1206404643b2d52c2a52512a875e`).
Revisions 1 and 2 are left unmodified as historical reviewed records; this file supersedes both.

Of revision 2's five addressed findings, the re-review confirmed four fully resolved
(`L13-S001`, `L13-S003`, `L13-S004`, `L13-S005`) and one partially resolved
(`L13-S002` -- the four concrete inaccuracies were fixed, but the shell-selection audit itself
was left internally contradictory). It also raised two new findings (`L13-S006`, `L13-S007`).
Only those three items (`L13-S002`'s remainder, `L13-S006`, `L13-S007`) are addressed below;
everything else in revision 2 is unchanged and not revisited.

## Starting state (unchanged)

```text
code main:    92aa4be168dc82111832467922089206e858a9c4
docs master:  ec36ed92a9a57f5fc8db4f76103a2d202cb82cbc
pinned Pi:    b7bb00b936dbe21b8e160b3e89efdec361846699
```

## L13-S002 remainder — bash shell-selection audit, completed

`utils/shell.ts:getShellConfig` now read in full (lines 67-120, the entire function), not
partially. The complete resolution order, verified directly against pinned-Pi source:

```text
1. An explicit caller-supplied shell path, if it exists on disk -- else a hard
   error listing the searched Git Bash locations and setup options.
2. Windows only: Git Bash at %ProgramFiles%\Git\bin\bash.exe or
   %ProgramFiles(x86)%\Git\bin\bash.exe, whichever exists first; else a
   bash.exe found via `where` on PATH, verified to actually exist on disk
   (since `where` can report stale/nonexistent paths); else a hard error.
3. Unix only, in order: /bin/bash if it exists; else the first result of
   `which bash` on PATH; else -- silently, no error -- fall back to plain
   "sh" with argv transport ({shell: "sh", args: ["-c"]}). Unlike the
   Windows path, Unix never throws if no bash is found at all; it degrades
   to "sh" instead.
```

This corrects revision 2's internally contradictory claim that `getShellConfig` was "read" while
also stating the Unix fallback chain was "not re-verified line-by-line" and leaving it an open
item -- that hedge is removed; the chain above is the complete, verified behavior. Command
transport (`argv` via `-c`, or `stdin` via `-s` only for the legacy-WSL-bash-path pattern) is
unchanged from revision 2's description and was already fully read in that revision.

This is documentary/source-audit remediation only. `TOOL-034` (bash schema, no-default-timeout,
shell-selection order, argv-vs-stdin transport) is unchanged in ID, scope, and classification --
only the underlying audit backing it is now complete rather than partially hedged.

## L13-S006 — WP-13.1's readiness state, corrected

Revision 2 called `WP-13.1` (`read`/`ls`) "genuinely unblocked" while its own `TOOL-027` (the
`read` tool's macOS filename-fallback heuristics) still carries an explicit
`[owner disposition: adopt / drop]` marker, and the (unchanged, inherited from revision 1)
Open questions section still lists that exact decision as unresolved. No owner disposition for
`TOOL-027` exists as of this revision -- this pass does not fabricate one.

**Correction:** `WP-13.1` is narrowly governance-blocked on `TOOL-027`'s disposition specifically,
not implementation-ready as a whole, pending that one decision. This does not reopen `L13-S004`'s
resolved finding (the *structural* split -- decoupling `read`/`ls` from the *separately*
governance-blocked `find`/`grep` engine question -- remains correct and unchanged); it corrects
only the readiness *label* applied to the resulting package. Once `TOOL-027` is dispositioned
(adopt or drop), `WP-13.1` becomes fully unblocked with no further scoping change required --
`TOOL-025`/`TOOL-026`/`TOOL-028` carry no open governance dependency of their own.

## L13-S007 — requirement count, corrected

Revision 2's closing note claimed "15 entries, same count as revision 1" while actually
enumerating `TOOL-025` through `TOOL-038` -- 14 rows. This was an arithmetic/proofreading error,
not a hidden omission: revision 1's `TOOL-008` (edit fuzzy-match algorithm) and `TOOL-009` (edit
BOM/line-ending detection and restoration) were intentionally consolidated into revision 2's
single `TOOL-031` (both are the same `edit-diff.ts` algorithm family, applied in the same code
path on the same normalized content, and splitting them produced two requirements that could not
be independently tested or certified without the other), but the closing note was never updated
to reflect that deliberate 15-to-14 consolidation, and instead asserted an unchanged count.

**Correction:** the proposed requirement set is **14 entries** (`TOOL-025` through `TOOL-038`),
not 15. No row is missing; `TOOL-031`'s scope explicitly covers what were two separate rows in
revision 1, and its own listed scope text already said "fuzzy-match algorithm, unchanged-line
preservation, BOM and line-ending detection/restoration" -- the consolidation was already present
in the row's content, only the summary count was wrong.

## Everything else (unchanged from revision 2)

The corrected `L13-S001` acquisition matrix, the completed `L13-S002` corrections for `read`/
`grep`/`find`/`ls` (image retention, grep's own context reconstruction, find's default-vs-custom
scoping, ls's sort/skip/suffix/empty-text rules), the `L13-S003` mutation-queue atomicity and
provider-scoping requirement (`TOOL-032`), the `L13-S004` four-package structural split
(`WP-13.1`/`WP-13.2`/`WP-13.3`/`WP-13.4`), the `L13-S005` non-colliding `TOOL-025`..`038` ID
range, and every section not named above (Mutation queue characterization, Path resolution,
Truncation constants, Parity classification, Semantic authority, High-risk surfaces, Acceptance-
oracle strategy, Cross-language impact) are unchanged from revision 2 and remain in force.

## Implementation authorized

```text
NO
```
