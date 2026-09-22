# CE-L13-WP131-01 — Lane D: `R007` (`ls` enumeration/cap semantics vs. current Layer-12 capability)

Mode: §11.8 sub-checkpoint characterization, Lane D, `R007` only, per the `CE-L13-WP131-01 --
Owner Process Decision` lane decomposition and the `R006-C Correction 3c -- Owner Process
Decision` amendment authorizing Lane D to start without waiting on Lane C's external-feasibility
block. **No Python or Rust implementation performed or authorized. No Layer 12 production
change.** `R003`/`R004`/`R008` remain frozen `CHECKPOINT-READY`; `R002`/`R005` remain
`OWNER_DECISION_RESOLVED`; `R006-A`/`R006-B` remain `RESOLVED`; `R006-C` remains
`FEASIBILITY_BLOCKED` (paused, not reopened here). This lane does not discuss or re-review `R006`.

**Revision 2 of this document.** Independent review (`minion-agent-docs#144` @
`3804d93b5b71562c7f550a35293f8ac0652eea03`) confirmed revision 1's core finding (the `ls.ts`-
versus-harness-`listDir` mapping, and Divergences 4a/4b/4c below) but rejected owner readiness on
three blocking points, all addressed in this revision: (1) symlink-to-directory and broken-symlink
behavior were missing from the divergence matrix and both owner options -- added as Divergences
4d/4e, live-verified, in Section 4 and folded into Section 7's options; (2) the `R007-b` options
did not name one concrete, implementable, provider-neutral additive surface -- Section 7 is
rewritten around a single consolidated proposal; (3) the paired TOCTOU witness (Divergence 4b)
used two different, one undocumented, directory paths for its Node and Python runs -- rerun in
Section 5's companion evidence against one shared, identically-recreated directory, with a
negative control added.

## 0. Why this is a fresh characterization, not a resubmission of the original `R007` text

The original combined checkpoint (`minion-agent-docs#132`, the pre-lane-decomposition
`13-wp131-ce-l13-wp131-01-characterization.md`, Part 7) characterized `R007` around a single
"cap-timing information loss" claim, built on a minimal witness (`e1` ok, `e2` ok, `e3` fails
classification "e.g. permission-denied `lstat`", claimed to be "silently skipped, matching Pi's
OWN skip-on-unsupported-kind spirit"). The independent reviewer found that witness invalid:
Layer 12's actual `_list_dir_sync` only silently skips `_UnsupportedFileType`, not arbitrary
`OSError` -- a permission failure does not produce the silent-omission behavior the witness
assumed.

Re-investigating from scratch (not merely swapping the witness's failure type) surfaced something
larger: **Layer 12's `_list_dir_sync` was modeled on the WRONG Pi function.** Its own source
comment says "Matches pinned Pi's own listDir exactly: ... (`fileInfoFromStats` returns an error
Result Pi discards, `info.ok ? push : skip`)". `fileInfoFromStats` is not defined in `ls.ts` at
all -- it lives in `packages/agent/src/harness/env/nodejs.ts`, the HARNESS-level filesystem
abstraction, inside a *different* `listDir()` method (`nodejs.ts:611-633`) that is not what the
`ls` TOOL uses. The `ls` tool (`ls.ts`) has its own, entirely separate inline enumeration loop
(`readdir`/`stat` via `LsOperations`, defaulting to raw `node:fs/promises` calls -- confirmed at
`ls.ts:1,46-50`), which never calls the harness's `FileSystemEnv.listDir()` or `fileInfoFromStats`
at all. Layer 12's `_list_dir_sync` faithfully mirrors the HARNESS `listDir()` (verified below) --
which is correct for whatever Layer-12 surface was built to match the harness contract -- but this
means **Layer 12's `list_dir()` was never a mirror of the `ls` TOOL's own semantics in the first
place**, and `TOOL-028`/`WP-13.1`'s draft (building `ls` directly on `list_dir()`) inherits that
mismatch.

This is a `CONTRACT_ASSURANCE_DEFECT`-class finding per the shared-contract authoring rules
(`../minion-agent-docs/process/agent-workflow.md`, this workspace's `CLAUDE.md`): the original R007
witness picked the wrong divergence to demonstrate, but a real, larger, directly-provable
divergence exists in its place. All claims below are demonstrated with **live-executed
reproductions** (real Node.js against `ls.ts`'s exact loop; a faithful Python port of
`_list_dir_sync`/`_file_info_sync`/`_file_kind_from_stat`'s exact logic) in WSL, not hand-traced --
raw transcripts are in the companion evidence file (Section 5).

## 1. Pi's exact `ls` tool pipeline (`ls.ts:145-176`, quoted in full)

```text
1. entries = readdir(dirPath)                    -- ALL raw names, unfiltered, OS-enumeration
                                                     order (ops.readdir, default = node:fs/
                                                     promises' readdir; NOT the harness
                                                     FileSystemEnv.listDir())
2. entries.sort((a,b) =>
     a.toLowerCase().localeCompare(b.toLowerCase()))
3. for each sorted entry, IN ORDER:
   3a. if results.length >= effectiveLimit: set
       entryLimitReached=true, BREAK -- the CURRENT
       entry (and all after it) is never examined
   3b. else: try { stat = await ops.stat(fullPath);   -- default = node:fs/promises' stat,
             if (stat.isDirectory()) suffix="/" }        which FOLLOWS symlinks and does NOT
       catch { continue }                                throw merely because the target is a
                                                           FIFO/socket/device -- ANY THROWN
                                                           exception (permission-denied, ENOENT
                                                           from a vanished entry, ELOOP, etc.)
                                                           is what triggers the silent skip, not
                                                           the entry's kind
       results.push(entry + suffix)
4. loop ends (array exhausted OR step 3a fired)
```

Two properties matter and were not both captured in the original characterization:

- **(P1) `ops.stat` does not throw on kind-unusual-but-accessible entries.** `fs.stat` succeeds on
  FIFOs, sockets, and device files exactly as it does on regular files -- it just reports
  `isDirectory()===false` for them. Pi's `ls` therefore **includes** such entries in its listing,
  as plain (non-directory) entries, indistinguishable in output from a regular file.
- **(P2) the per-entry `catch` is a blanket catch-all**, triggered only by a genuinely thrown
  exception (permission-denied, a vanished/TOCTOU-raced entry, a broken symlink under certain
  conditions, etc.) -- and when it fires, exactly ONE entry is omitted; the loop continues
  normally to the next entry and the overall call still succeeds.

## 2. Pi's harness-level `listDir()` (`nodejs.ts:611-633`, quoted in full) -- NOT used by the `ls`
tool, but what Layer 12's `list_dir()` actually mirrors

```text
async listDir(path):
  entries = readdir(resolved, {withFileTypes:true})   -- whole-call try/catch around this AND
                                                           the loop below
  infos = []
  for entry in entries:
    try:
      info = fileInfoFromStats(entryPath, await lstat(entryPath))  -- lstat, NOT stat: does NOT
                                                                       follow symlinks
      if info.ok: infos.push(info.value)               -- fileInfoFromStats returns an err()
                                                           Result (not a throw) for a kind it
                                                           can't classify (not file/dir/symlink) --
                                                           silently dropped here
    except (error):
      return err(toFileError(error, entryPath))         -- ANY OTHER exception (permission-denied,
                                                           vanished entry, etc.) aborts the ENTIRE
                                                           listDir() call
  return ok(infos)
```

## 3. Minion Layer-12's exact pipeline (`filesystem.py:443-461`, `_file_info_sync:378-389`,
`_file_kind_from_stat:368-375`, all quoted in full; unchanged, matches Section 2 exactly)

```python
def _file_kind_from_stat(st):
    if S_ISREG(st.st_mode): return FILE
    if S_ISDIR(st.st_mode): return DIRECTORY
    if S_ISLNK(st.st_mode): return SYMLINK
    return None

def _file_info_sync(path):
    st = os.lstat(path)                       # lstat, matches Section 2, NOT Section 1's stat
    kind = _file_kind_from_stat(st)
    if kind is None:
        raise _UnsupportedFileType
    return FileInfo(...)

def _list_dir_sync(path, signal):
    infos = []
    with os.scandir(path) as entries:
        for entry in entries:
            try:
                infos.append(_file_info_sync(entry.path))
            except _UnsupportedFileType:
                continue                        # matches Section 2's fileInfoFromStats-err-skip
            # any OTHER exception (e.g. FileNotFoundError, PermissionError) is NOT caught here --
            # it propagates out of _list_dir_sync entirely, failing the WHOLE call
    return infos
```

**Confirmed: Layer 12's `list_dir()` is a faithful, correct mirror of Section 2 (the harness
`listDir()`), not of Section 1 (the `ls` tool's own loop).** The two Pi functions genuinely
disagree with each other on both (P1) kind-inclusion and, in effect, on cap semantics (Section 2
has no cap concept at all, matching Layer 12). `WP-13.1`'s draft, which builds the `ls` TOOL
directly on `list_dir()`, is therefore built on the wrong Pi reference function for `TOOL-028`'s
actual target behavior.

## 4. Five live-verified divergences (not hand-traced -- see Section 5 for full transcripts)

### 4a. Kind-inclusion (cap-independent): Pi includes FIFO/socket/device entries; Minion omits them

Directory: `e1_file.txt` (regular), `e2_file.txt` (regular), `e3_fifo` (a real FIFO, created with
`mkfifo`). Run against the REAL `ls.ts` loop (Node, live) and a faithful Python port of
`_list_dir_sync` (live):

```text
Pi ls.ts loop (limit=500):     results = ["e1_file.txt", "e2_file.txt", "e3_fifo"]
Minion list_dir() survivors:   [e1_file.txt, e2_file.txt]   -- e3_fifo silently DROPPED
```

Pi shows the FIFO as a plain listed entry (no special marker, same as a regular file). Minion's
`list_dir()` -- and therefore any Layer-13 `ls` built directly on it -- omits it entirely, with no
signal to the caller that anything was dropped. This has nothing to do with the entry-count cap;
it reproduces with `limit=500` against a 3-entry directory.

### 4b. Whole-call failure vs. per-entry skip (cap-independent, more severe than previously
characterized): a single transient per-entry failure fails Minion's ENTIRE listing; Pi's succeeds

Directory: `e1_file.txt`, `e2_file.txt`, `e4_vanishing.txt` -- then `e4_vanishing.txt` is deleted
after the initial scan/readdir but before its own per-entry stat (a real TOCTOU race,
deterministically reproduced for the test rather than relying on race timing):

```text
Pi ls.ts loop (limit=500):        results = ["e1_file.txt", "e2_file.txt"], entryLimitReached=false
                                   (e4 silently skipped; the call SUCCEEDS)
Minion list_dir() (faithful
Python port, live-run):           WHOLE-CALL FAILURE: FileNotFoundError
                                   [Errno 2] No such file or directory: '.../e4_vanishing.txt'
                                   (NO survivors returned at all -- e1 and e2 are also lost,
                                   even though both still exist and are perfectly listable)
```

This is the corrected replacement for the original (invalid) witness, and it is a **stronger**
finding than a mere signal-truthfulness nuance: a single entry that vanishes mid-listing (a
realistic condition under concurrent filesystem activity, not a contrived edge case), or a single
entry the caller lacks permission to `lstat`, turns a Layer-13 `ls` built on today's `list_dir()`
into a **total, unwarranted failure** for a directory Pi's own `ls` tool would list successfully
minus that one entry. `_UnsupportedFileType`'s narrow catch is the wrong shape for `TOOL-028`: Pi's
per-entry catch in `ls.ts` is unconditional (any thrown error), not kind-specific.

### 4c. Combined effect: a kind-unsupported entry positioned within Pi's pre-cap window produces
genuinely different CONTENT, not just a different truncation signal

Directory (sorted order): `e1_file.txt`, `e2_fifo` (FIFO), `e3_file.txt`, `e4_file.txt`. `limit=2`.

```text
Pi ls.ts loop (limit=2):                results = ["e1_file.txt", "e2_fifo"], entryLimitReached=true
                                         (e2_fifo occupies the 2nd of Pi's 2 shown slots; e3, e4
                                         never even examined -- the cap fires immediately after)

Minion list_dir() full survivors:       [e1_file.txt, e3_file.txt, e4_file.txt]   (e2_fifo dropped
                                         during the unconditional full enumeration)
Layer-13-style post-hoc cap=2:          ["e1_file.txt", "e3_file.txt"], entry_limit_reached=true
```

Both sides agree the limit was reached (`entryLimitReached`/`entry_limit_reached` both `true` here
-- the original characterization's framing, that the divergence is purely about this flag's
truthfulness, undersold the actual severity). The **displayed content differs**: Pi's second entry
is `e2_fifo`; Minion-based Layer 13's second entry is `e3_file.txt` -- a file Pi's `ls` never even
reaches in this call. A caller cannot tell, from either output alone, that the two systems
disagree about what is actually in the directory's first two (sorted, limit-respecting) entries.

**Root-cause correction from the original characterization**: the original framing presented
"cap-timing" as a free-standing divergence. Live-tested here (Section 5, cases with no
kind-unsupported or vanishing entries at all) confirms that when every entry classifies
identically in both systems, cap-then-stop (Pi) and full-scan-then-slice (Minion-composed) produce
IDENTICAL output -- the cap-timing structure by itself is not observable. The cap only becomes an
*amplifier*: it is Divergences 4a/4b (kind-inclusion and per-entry-failure-handling) landing at or
before the cap boundary that make the final output differ. `R007` is therefore best understood as
"Layer 12's `list_dir()` is the wrong Pi reference function for the `ls` tool, and the cap
interacts with that mismatch to also corrupt content, not just a truncation signal" -- not as an
isolated cap-arithmetic quirk.

### 4d. Directory-symlinks: Pi classifies by the RESOLVED target; Minion classifies the link itself

`ops.stat`'s default (`node:fs/promises`' `stat`) FOLLOWS symlinks; Layer 12's `_file_info_sync`
uses `os.lstat`, which does NOT. Live-verified on a real symlink pointing at a real directory:

```text
Node fs.statSync(dir_symlink):        isDirectory() = true   (resolves through the link)
Python os.lstat(dir_symlink)
  + _file_kind_from_stat:             kind = SYMLINK          (does not resolve the link)
```

End-to-end (directory containing `e1_file.txt`, `e2_dirlink` -> `real_target_dir`, limit=500):

```text
Pi ls.ts loop:              results = ["e1_file.txt", "e2_dirlink/", "real_target_dir/"]
                             (e2_dirlink shown WITH a trailing slash -- treated as a directory)
Minion list_dir() survivors: e2_dirlink classified kind=SYMLINK, not DIRECTORY
```

A caller cannot tell, from Minion's classification alone, that `e2_dirlink` resolves to a
directory the way Pi's own output implies.

### 4e. Broken symlinks: Pi OMITS them (the inverse direction from 4a); Minion INCLUDES them

Live-verified on a real symlink pointing at a non-existent target:

```text
Node fs.statSync(broken_symlink):     THROWS (ENOENT) -- following the dead link fails
Python os.lstat(broken_symlink)
  + _file_kind_from_stat:             succeeds, kind = SYMLINK (lstat never resolves the target,
                                       so a missing target does not matter to it at all)
```

In the same end-to-end run as 4d (`e3_brokenlink` -> `does_not_exist`):

```text
Pi ls.ts loop:               e3_brokenlink is ABSENT from results entirely -- ops.stat's ENOENT
                              is caught by the per-entry catch-all, silently skipped
Minion list_dir() survivors: e3_brokenlink IS present, kind=SYMLINK
```

This is the exact inverse of Divergence 4a: there, Pi included an entry (a FIFO) that Minion
silently dropped. Here, Pi silently drops an entry (a broken symlink) that Minion includes. Both
directions stem from the same root cause: Pi's `ls` tool classifies via symlink-following `stat`
with a blanket per-entry catch, while Layer 12's `list_dir()` classifies via non-following `lstat`
with a kind-specific catch -- two independently different policies that happen to agree only on
regular files, directories, and (for classification purposes, though not for broken-target
purposes) live symlinks to regular files.

## 5. Companion evidence

Raw, live-executed transcripts (real Node.js running `ls.ts`'s exact loop; a faithful Python port
of `_list_dir_sync`/`_file_info_sync`/`_file_kind_from_stat`'s exact logic; run in WSL Ubuntu,
Node v24.14.0, Python 3.10.12) for all five cases above (4a-4e), including the corrected,
shared-directory-plus-negative-control rerun of Divergence 4b, plus the raw `mkfifo`/`ln -s`/
`stat`/`lstat` classification checks that grounded them, are recorded at
`assurance/layers/data/13-wp131-ce-l13-wp131-01/r007-ls-enumeration-live-witness.txt`.

## 6. Falsification attempt: can existing certified Layer-12 operations be composed to reproduce
Pi's `ls` tool exactly?

The certified `FileSystem` Protocol's only relevant operations are `list_dir()` (Section 3: full
scan, survivors-or-whole-call-error, `lstat`-based, skips only kind-unclassifiable entries) and
`file_info()` (single-path classification, also `lstat`-based). Neither, alone or composed:

- exposes raw, unclassified entry NAMES prior to per-entry stat (needed to reproduce Pi's
  cap-before-stat structure, Section 1 property in isolation);
- follows symlinks the way `ops.stat`'s default (`node:fs/promises`' `stat`) does -- `list_dir`/
  `file_info` are `lstat`-based throughout, which is precisely what produces Divergences 4d/4e
  (Section 4), not merely an incidental footnote as revision 1 treated it;
- includes kind-unclassifiable entries the way `ops.stat`'s success-on-FIFO/socket/device behavior
  does (Section 4a);
- allows one per-entry failure to be silently skipped without failing the whole call for any
  failure OTHER than kind-unclassifiable (Section 4b).

**Confirmed, not merely asserted**: given the currently certified Layer-12 `FileSystem` Protocol
exactly as defined, Layer 13 cannot reproduce Pi's `ls` tool's actual behavior via any composition
of existing operations, on any of five independently live-verified points (4a-4e). This is a
structural property of the certified interface (built to mirror a *different* Pi function), not an
implementation gap in a particular provider.

## 7. Additive-capability options (characterization only; none implemented or selected here)

**`R007-a` -- accept the observable divergences, governed.** Record `TOOL-028` as an intentional,
disclosed divergence from Pi on five specific points: (1) FIFO/socket/device entries are omitted
from Layer-13 `ls` output rather than listed as plain entries (4a); (2) a single per-entry failure
(permission-denied, TOCTOU-vanished) fails the WHOLE listing rather than omitting just that entry
(4b); (3) content at the cap boundary can differ, not just the truncation signal, when (1) or (2)
apply near it (4c); (4) a symlink to a directory is classified `SYMLINK`, not shown as a directory
the way Pi's resolved-target view would (4d); (5) a broken symlink is included (as `SYMLINK`)
rather than silently omitted the way Pi's resolved-target view would (4e). No Layer 12 change.
Lowest implementation cost -- `WP-13.1` as already drafted (using `list_dir()` directly) already
produces this behavior without modification; this option only requires a governance record.

**`R007-b` -- ONE consolidated additive Layer-12 operation, sized against all five divergences.**
Revision 1's two-candidate proposal (a raw-names operation plus a separate "permissive" per-entry
wrapper) was rejected: a Layer-13-local wrapper around the EXISTING `file_info()` cannot recover
kind information `file_info()` has already discarded before returning (the unsupported-kind case
is a `raise`/discarded-Result *inside* `_file_info_sync`, never reaching any caller-side wrapper to
reinterpret), and giving that wrapper's result type a new `OTHER` kind would only work by mutating
the EXISTING, widely-relied-upon `FileKind` enum `file_info()`/`list_dir()` already use --
precisely what "purely additive, nothing existing changes" rules out.

**Corrected, single, concrete proposal:**

```text
list_dir_entries(path) -> Result[list[DirEntryProbe], FsError]
```

- **Entirely new operation, entirely new result type** (`DirEntryProbe`) -- NOT a reuse or
  extension of `FileInfo`/`FileKind`. The existing `file_info()` and `list_dir()`, their result
  types, and every existing caller are completely unchanged; this is additive in the strict sense
  the process requires, not a rename or reinterpretation of anything certified today.
- Internally enumerates the directory (like `list_dir()`), but for EACH raw entry performs its OWN
  symlink-FOLLOWING stat (mirroring `ops.stat`'s default, i.e. Python's `os.stat`, not `os.lstat`)
  rather than reusing `_file_info_sync`'s `lstat`-based classification. This is what closes 4d
  (a directory-symlink's resolved target is what gets classified, matching Pi) and 4e (a broken
  symlink's stat-follow failure becomes a per-entry outcome, not a silent lstat-success).
- **Never aborts the whole call for one bad entry.** Each element of the returned list is itself a
  per-entry outcome -- either a successful classification (carrying a kind field whose value set is
  `FILE | DIRECTORY | SYMLINK_TO_FILE | SYMLINK_TO_DIRECTORY | OTHER | FAILED`, where `OTHER` is
  used for FIFO/socket/device -- closing 4a -- and `FAILED` carries the raw per-entry error, e.g.
  the permission-denied or TOCTOU case) or that per-entry failure marker. This closes 4b: Layer 13
  decides, per entry, whether to skip a `FAILED` marker (reproducing Pi's blanket catch-and-continue
  exactly) or surface it -- Layer 12 no longer makes that policy choice centrally.
- Returned in **provider/raw enumeration order, unsorted, with NO cap applied** -- Layer 13 sorts
  the full list itself (as it already must, to match `R006`'s ordering rules) and then applies its
  own cap. Because nothing is silently dropped and nothing aborts the whole call anymore (4a/4b/4d/
  4e all closed), a post-hoc cap over this operation's COMPLETE, corrected per-entry list is now
  provably equivalent in content to Pi's cap-before-stat loop: Pi's `entryLimitReached` is true
  exactly when at least one more raw entry (of any eventual fate) exists after the position of the
  `effectiveLimit`-th entry Pi would have counted as a success (`FILE`/`DIRECTORY`/`SYMLINK_*`/
  `OTHER`, not `FAILED`) -- a rule Layer 13 can now compute exactly from this operation's complete
  output, closing 4c as a direct consequence of closing 4a/4b/4d/4e, not as a separate mechanism.

This is deliberately ONE operation with ONE new result type, not a pair of loosely-related
candidates -- addressing the independent review's specific objection that revision 1's proposal did
not name a single implementable, provider-neutral surface.

**Ruled out outright**: modifying `list_dir()`'s or `file_info()`'s existing skip/fail/classify
behavior directly. Either would be a backward-incompatible change to an already-certified Layer-12
operation (every existing caller's observed behavior would change), not a narrow additive
extension, and is out of this lane's (and this Layer's) authority to propose as anything other than
"ruled out."

If `R007-b` is chosen, the correct process framing is a **narrow, backward-compatible Layer-12
extension** (one new operation and one new result type added to the Protocol; every existing
certified operation, type, caller, and `EXEC-*` requirement unchanged) requiring its own narrow
revalidation on both languages -- NOT a reopening or invalidation of Layer 12's existing historical
certification. This pass does not create, implement, or certify this operation; it only
characterizes it as a candidate.

**Consequences summary (neutral, for owner decision):**

```text
                          R007-a (accept)      R007-b (list_dir_entries)
Layer 12 change           none                 additive only -- one new operation, one new
                                               result type; every existing operation/type/
                                               caller unchanged
Python impact              none beyond WP-13.1  one new operation + WP-13.1 consumes it
Rust impact                 none beyond WP-13.1  one new operation + WP-13.1 consumes it
Fidelity to Pi's `ls`        LOW on all five      HIGH on all five (structural reproduction of
  tool specifically           divergences          ls.ts's own loop becomes possible, including
                                                    the cap-boundary content match)
Implementation cost           lowest               moderate -- new Layer-12 surface + its own
                                                    revalidation, not merely a WP-13.1-local change
```

## 8. Status (this revision)

```text
R007-4a (kind-inclusion):             live-verified, characterized
R007-4b (whole-call vs per-entry):    live-verified, characterized; witness corrected this
                                       revision (shared directory + negative control, replacing
                                       the independently-flagged mismatched-path transcript)
R007-4c (combined/cap-boundary):      live-verified, characterized
R007-4d (directory-symlink):          live-verified, characterized (new this revision)
R007-4e (broken symlink):             live-verified, characterized (new this revision)
R007-b:                               revised to one consolidated, concrete, provider-neutral
                                       operation (list_dir_entries), replacing the rejected
                                       two-candidate proposal
R007 overall:                         OWNER_DECISION_REQUIRED (R007-a vs. R007-b)
```

No option is selected. `TOOL-028` cannot proceed to contract-review-ready status until the owner
decides.
