# CE-L13-WP131-02 — characterization: abort ordering (`I001`) and read failure sites (`C012`)

Mode: workflow §11.8.3 characterization pass (assigned to Claude by `minion-agent#48`,
`NEXT_OWNER = Claude`, after Codex's targeted closure review found both findings still open --
trigger A). **No implementation performed.** Frozen candidates: code #60 @ `61f40e4d`, docs #162 @
`30d3af20`. Pinned Pi `b7bb00b936dbe21b8e160b3e89efdec361846699`, Node 22.15.1.

## OPEN FINDINGS

- `L13-WP131-I001` (`PI_PARITY_DEFECT`): outcome when the abort and the work's completion race.
  Latest witness (Codex, #60, targeted review of `61f40e4d`): abort, then the blocked work settles
  before the 10 ms poll wakes -> the candidate returns SUCCESS; Pi returns `Operation aborted`.
- `L13-WP131-C012` (`CONTRACT_ASSURANCE_DEFECT`): which of Pi's two error sites (`access` vs content
  read) a `read` failure belongs to. Latest witness (Codex): successful access, then
  `read_binary_file -> Err(not_found)` (file removed between the steps) or `Err(unknown)` -> the
  candidate says `Cannot access ...`; Pi's `ops.access` already succeeded, so Pi says `Cannot read`.

## PI SYMBOLS / TESTS AUDITED

`core/tools/read.ts:223-334` (promise executor; `onAbort`; checkpoints at 246/249; `if (aborted)
return` at 325; `catch ... if (!aborted) reject(error)`), `core/tools/ls.ts:103-230` (`onAbort`;
listener removed after the entry loop at 178; unconditional `reject(e)` in the outer catch),
`utils/mime.ts:25-35` (`detectSupportedImageMimeTypeFromFile`: its own `open`+`read`),
`ReadOperations.access` = `fs.promises.access(path, R_OK)`. Live probes (Node 22.15.1):

```text
host            probe                                  access(R_OK)   readFile
Linux (non-root) unreadable file (mode 000)            EACCES access  EACCES open
Linux            directory / symlink -> directory       ok             EISDIR read
Windows 11       unreadable file (deny-read ACL)        ok  (!)        EPERM open
Windows 11       directory                              ok             EISDIR read
```

libuv's `access` on Windows checks existence and attributes only, never the ACL, so Pi's
`access(R_OK)` cannot report an unreadable file there. Pinned Pi's error SITE for an unreadable file
is therefore host-dependent: `Cannot access` on POSIX, `Cannot read` on Windows.

## OBSERVABLE RULES

**I001 -- abort ordering (read and ls).**

- R-I1 The tool's outcome is decided by ORDER: if the signal is aborted before the work reaches its
  settle point (read: `resolve` at read.ts:327; ls: `resolve` after the entry loop), the outcome is
  `Operation aborted`; if the work settled first, its result or error stands. A failure the work
  throws AFTER the abort is also `Operation aborted` (read: `if (!aborted) reject(error)`; ls: the
  promise is already rejected).
- R-I2 The rejection is delivered as soon as the implementation observes the abort. How soon is
  implementation latency, not an observable ordering rule.
- R-I3 The abort never cancels or signals in-flight `ctx.fs` work (closed at `61f40e4d`, kept).
- R-I4 `read` stops at its checkpoints (after path resolution; after the access step); `ls` has none
  and runs to completion (kept).

Decision point for R-I1: the settle point is the last synchronous step of the work -- no await
between the final `signal.aborted` check and producing the result. With that, polling latency cannot
change the outcome. `RunSignal` stays as certified (poll-based, Layer 09); no lower-layer change.

**C012 -- read's access step and failure sites.**

- R-C1 Access step = `canonical_path(p)` (core `EXEC-002`; strict `realpath`: follows symlinks, fails
  `not_found` for a missing path or a dangling link, `not_directory`/`permission_denied`/`invalid`/
  `unknown` (e.g. a symlink loop) for the path itself). `Err(code)` -> `Cannot access <path>:
  <phrase>`. A provider that cannot supply it answers `not_supported`, which R010-B already places
  at the access site ("a provider that cannot supply this check").
- R-C2 Directory: `file_info(<canonical path>)` (core) -- kind `directory` -> `Cannot read <path>: is
  a directory` (Pi: access ok, readFile `EISDIR`, on both hosts, directly or through a symlink).
  This no longer depends on how a provider classifies a directory READ, so the Windows Layer 12
  classification defect is not reached. `file_info` failing here means the target vanished after the
  access step: `Cannot read <path>: <phrase>`.
- R-C3 Content: `read_binary_file(p)` (no signal). `Err(code)` -> `Cannot read <path>: <phrase>` for
  every code, **except `permission_denied`, whose site is the owner decision below** (Pi is
  host-dependent). `not_found` after a successful access (removed in between), `unknown`,
  `is_directory` (replaced by a directory in between), `not_supported`: all `Cannot read`, as in Pi.
- R-C4 `EXEC-007` is not used by `read` (closed at `61f40e4d`, kept).

## OWNER DECISION REQUIRED (§11.7): the site of an unreadable file

Pinned Pi reports an existing, unreadable regular file as `Cannot access <path>: permission denied`
on POSIX and `Cannot read <path>: permission denied` on Windows (probes above). No certified
`ctx.fs` operation checks readability without reading. Options:

- **C012-A (recommended):** `permission_denied` from the content read is reported at the ACCESS site,
  on every host. Matches Pi on POSIX (Pi's primary platform and the one R010-B's own table assumes,
  since it lists `permission_denied` among the access site's reachable codes); diverges from Pi on
  Windows. Deterministic.
- **C012-B:** report it at the READ site on every host. Matches Pi on Windows; diverges on POSIX, and
  leaves R010-B's access-site `permission_denied` reachable only for a non-searchable parent
  directory.
- **C012-C:** follow the provider's own platform (POSIX-like -> access site, Windows -> read site).
  Matches Pi on both hosts for local providers; makes the text depend on the provider's platform,
  which R002-A's precedent (uniform, provider-independent rejection) argued against, and needs a
  platform notion `ctx.fs` does not currently expose.

Whichever is chosen is `TOOL-039` error-text territory (R010-B, `intentional divergence`) and would be
recorded there.

## BEHAVIOR MATRIX

I001 (both tools unless noted; "blocked" = a provider call awaiting release):

```text
abort timing                                          expected outcome        fs work after abort
before execute (pre-aborted)                          Operation aborted       none
after execute starts, before the first fs call        Operation aborted       none (read cp1; ls: all)
while the access/dir probe is blocked                 Operation aborted,      read: the blocked call
                                                      delivered while         completes, then stops
                                                      still blocked           (no read); ls: continues
while read_binary_file is blocked (read)              Operation aborted       read completes; image
                                                                              processing may run; result
                                                                              discarded
abort, then the blocked work settles before any       Operation aborted       -
poll can observe it (Codex's witness)
work throws AFTER the abort                           Operation aborted       -
work throws BEFORE the abort                          that error              -
work settles, then abort before the caller resumes    the work's result       -
work settles, caller resumed, then abort              the work's result       -
```

C012 (`<path>` = `absolute_path` of the step-5 string):

```text
case                                                   R-rule   expected text
missing file                                           C1       Cannot access <path>: no such file or directory
dangling symlink                                       C1       Cannot access <path>: no such file or directory
component is a file                                    C1       Cannot access <path>: not a directory
symlink loop                                           C1       Cannot access <path>: unknown filesystem error
provider without canonical_path                        C1       Cannot access <path>: not supported by this provider
directory                                              C2       Cannot read <path>: is a directory
symlink to directory                                   C2       Cannot read <path>: is a directory
file_info fails after canonical_path (race)            C2       Cannot read <path>: <phrase>
read -> not_found after access (removed in between)    C3       Cannot read <path>: no such file or directory
read -> unknown                                        C3       Cannot read <path>: unknown filesystem error
read -> is_directory / not_supported / not_directory   C3       Cannot read <path>: <phrase>
unreadable file (read -> permission_denied)            owner    C012-A: Cannot access ... / C012-B: Cannot read ...
provider without EXEC-007                              C4       reads normally
```

## MINIMAL EXECUTABLE WITNESSES (to become permanent evidence)

- `W-I1` Codex's ordering witness at the race seam: work blocked; `abort()` then `release()` in the
  same step -> `Operation aborted` (candidate `61f40e4d`: SUCCESS -> FAIL).
- `W-I2` the same at the tool seam for `read` and `ls` (scripted provider blocks, abort + release).
- `W-I3` work fails after abort -> `Operation aborted`; fails before -> its error.
- `W-I4` work settles, then abort before the caller resumes -> the result (guards against an
  over-correction that re-checks the signal after settling).
- `W-I5` (kept) blocked call completes uncancelled, no signal passed, read stops / ls continues.
- `W-C1` canonical scenario (R010-B): scripted `canonical_path` errors -> access site per code; real
  missing file and dangling symlink.
- `W-C2` canonical scenario: real directory and symlink to a directory -> `Cannot read ... is a
  directory` (passes on Windows without any Layer 12 change).
- `W-C3` canonical scenario: scripted `read_binary_file` `not_found`/`unknown`/`is_directory`/
  `not_supported` after a successful access -> `Cannot read` (Codex's witness).
- `W-C4` canonical scenario for the owner-decided `permission_denied` site.
- `W-C5` (kept) provider without EXEC-007 reads normally; `fs_calls` pinned to
  `canonical_path`, `file_info`, `read_binary_file`.

Negative controls (§11.8.7.1), to run against the implementation: settle-then-check removed
(W-I1 must fail), result re-checked after settling (W-I4 must fail), error site by code as at
`61f40e4d` (W-C3 must fail), `probe_dir_entry` access (W-C5 must fail), directory from the read's
code only (W-C2 must fail on Windows).

## CURRENT CANDIDATE FAILURES (`61f40e4d`)

W-I1, W-I2 (settle order), W-I3 (post-abort failure surfaces as its own error), W-C3 (`not_found`/
`unknown` reported at the access site), W-C2 for a symlink to a directory on Windows.

## SPEC / MANIFEST / CONFORMANCE DELTAS NEEDED

`spec/tools.md`: the read/ls cancellation rules gain R-I1 (ordering, including post-abort failure);
the read operation mapping becomes R-C1..C4 with the owner-decided `permission_denied` site; R010-B's
site paragraph is aligned; `TOOL-039` gains the decided site rule. Manifest `TOOL-025`/`TOOL-039`
tests: W-C1..C5. Conformance: the R010-B scenario is rescripted on `canonical_path`; new
directory/symlink-to-directory cases. Schema/runner: scripted `canonical_path`.

## IMPLEMENTATION CONSTRAINTS

- No Layer 09 change: `RunSignal` stays poll-based; ordering is decided by a synchronous check at
  the settle point, prompt delivery by observation.
- No Layer 12 change: `canonical_path` and `file_info` are certified core operations; the two Layer 12
  Python defects (newline translation; Windows directory-read classification) stay escalated and are
  no longer reached by `read`.
- Rust: implementable idiomatically (a synchronous `is_aborted()` check at the settle point; the same
  three core operations). The poll-based observation is a Python-only mechanism; nothing requires
  Rust to poll.

## OUT-OF-SCOPE / DEFERRED

The Layer 06 pipeline's own handling of a signal aborted after `execute` returns (certified Layer 06
/09 behavior, unchanged). Pi's separate sniff `open` before `readFile` (one Minion read replaces
both; only a race between them could differ). Races between `canonical_path` and `file_info` beyond
R-C2's rule.

## CONVERGENCE CHECKPOINT

```text
PROPOSED FOR IMPLEMENTATION  (subject to the owner's C012 permission_denied-site decision)

OPEN FINDINGS
    L13-WP131-I001, L13-WP131-C012

ACCEPTANCE WITNESSES
    W-I1..W-I5, W-C1..W-C5 (above); negative controls listed above

NORMATIVE DELTAS
    spec/tools.md (read/ls cancellation; read operation mapping; R010-B sites; TOOL-039),
    pi-parity-manifest.yaml (TOOL-025, TOOL-039 tests), conformance/agent/builtin-*.yaml,
    conformance/schema/builtin-tool-scenario.schema.json

NEXT_OWNER
    Codex (checkpoint review of exactly this proposal); Owner for the C012 site decision
```

---

## Revision 2 -- after checkpoint review REJECTED (`CE13-C001`, `CE13-C002`)

Codex's §11.8.5 review of revision 1 at `30ecdd55` (minion-agent-docs#162 comment `5821849846`):
**REJECTED** for C012 (I001: no checkpoint blocker). Revision 1 above is kept as reviewed history.
Both points are accepted.

**Governance note.** Before this rejection was known, the owner answered revision 1's menu and
selected C012-A (`minion-agent#48` comment `5822062094`), explicitly placing a `permission_denied`
returned by `read_binary_file` at the access site "on every provider/host". That menu did not
present CE13-C002's post-access history, so per the review it is an answer to an incomplete menu. It
is recorded, not treated as settling C002; the complete menu below goes back to the owner after
this revision is independently reviewed.

### CE13-C001 -- the access step's own operation may be unsupported

Certified Layer 12 (`spec/execution.md` §4, `L12-R018`) allows `canonical_path -> not_supported` on a
provider that still supports `file_info` and `read_binary_file`. Pi's `ReadOperations.access` and
`readFile` are supplied independently, so every Pi provider has an access check; a Minion provider
may not have the symlink-following one. Options:

- **Q1 -- fail.** `canonical_path -> not_supported` is `Cannot access <path>: not supported by this
  provider` (R010-B's "provider cannot supply this check"). `read` is unusable on such a provider.
  This is the dependency C012 exists to remove.
- **Q2 -- fall back to `file_info` (recommended).** On `not_supported`, the access step is
  `file_info(p)` (core, `lstat`): `Err(code)` -> access site; `kind == directory` -> `Cannot read ...
  is a directory`. Because `lstat` does not follow a final symlink, a content read failing with
  `not_found`, `not_directory` or `invalid` UNDER THE FALLBACK is reported at the access site (those
  are exactly what the missing symlink-following check would have caught); all other read failures
  stay at the read site. Deterministic for a given provider capability; differs from the primary
  path only in which site a post-access removal is attributed to, and only on such providers.
- **Q3 -- skip the check.** On `not_supported`, go straight to the read and attribute purely by the
  read's code (the `61f40e4d` rule). Rejected by review for ordinary providers; restricted to this
  case it is Q2 without `file_info`'s directory decision.

Whichever is chosen is an observable provider-capability difference and needs owner approval
(Codex: "explicitly seek Owner approval for an observable provider-capability divergence").

### CE13-C002 -- `permission_denied` has two histories the error code cannot tell apart

```text
history                                             Pi (POSIX)        Pi (Windows)
H1 unreadable before the access check               Cannot access     Cannot read
H2 readable at access, unreadable before readFile   Cannot read       Cannot read
```

Minion's primary path sees `canonical_path Ok, file_info Ok(file), read_binary_file ->
permission_denied` in BOTH histories. No certified operation checks readability without reading.
Options:

- **P1 -- access site always** (the owner's current C012-A). H1 matches Pi on POSIX; H2 on POSIX and
  both histories on Windows are reported at the access site where Pi says `Cannot read`. H2 needs a
  permission change in the window between two consecutive filesystem calls.
- **P2 -- read site always** (C012-B). H2 matches Pi everywhere and H1 matches Pi on Windows; H1 on
  POSIX (the common, stable case) diverges.
- **P3 -- readability probe from an existing core operation.** Add `read_text_lines(p, max_lines=1)`
  to the access step (certified: it opens the file and reads at most one line; `max_lines <= 0` would
  not touch the file). `permission_denied` there -> access site (H1); a later
  `read_binary_file -> permission_denied` -> read site (H2). Matches Pi on POSIX for BOTH histories;
  on Windows H1 still differs (Pi's `access` never sees the ACL), exactly as P1. Costs: one extra open
  and a partial read per `read` call (up to the first newline -- the whole file if it has none), the
  probe's own `not_supported` needs the Q-rule above, and a directory on Windows reaches the Layer 12
  classification defect unless `file_info` decides it first (it does, per R-C2).
- **P4 -- Layer 12 extension.** A certified readability-check operation (`access(R_OK)` without
  reading). Lower-layer change in both languages; owner authorization and a Layer 12 contract pass.

Recommendation: **P1 with Q2**, i.e. the owner's C012-A as already decided, with its H2 consequence
stated. It needs no new mechanism, and H2 only arises when a file's permissions change in the window
between two consecutive filesystem calls. If the owner wants H2 to match Pi on POSIX, P3 does that
with core operations at the stated cost.

### Revised behavior matrix (C012; rows unchanged from revision 1 are not repeated)

```text
case                                                        rule    expected
canonical_path not_supported; file_info Ok(file); read Ok   Q2      reads normally (CE13-C001 witness)
canonical_path not_supported; file_info Err(not_found)      Q2      Cannot access <path>: no such file or directory
canonical_path not_supported; dangling symlink; read NF     Q2      Cannot access <path>: no such file or directory
canonical_path not_supported; read unknown                  Q2      Cannot read <path>: unknown filesystem error
H1: unreadable before access (POSIX-like provider)          P1      Cannot access <path>: permission denied
H2: permission removed between access and read              P1      Cannot access <path>: permission denied (Pi: Cannot read)
                                                            P3      Cannot read <path>: permission denied
```

Added witnesses: `W-C6` (CE13-C001: `canonical_path -> not_supported`, `file_info` ok, read ok ->
success; negative control: Q1 must fail it), `W-C7` (CE13-C002 H1: scripted access-step
`permission_denied`), `W-C8` (CE13-C002 H2: access ok, scripted read `permission_denied`; its
expected text is set by the owner's P choice; negative control: the other P option must fail it).

### Revised checkpoint

```text
PROPOSED FOR IMPLEMENTATION  (revision 2; subject to the owner's Q and P choices)

OPEN FINDINGS
    L13-WP131-I001 (no checkpoint blocker at revision 1), L13-WP131-C012 (+ CE13-C001, CE13-C002)

ACCEPTANCE WITNESSES
    W-I1..W-I5, W-C1..W-C8, with the listed negative controls

NORMATIVE DELTAS
    as revision 1, plus: the access-step fallback rule (Q) and the permission_denied rule (P) in
    spec/tools.md and TOOL-039

NEXT_OWNER
    Codex (checkpoint review of revision 2); then the owner for Q and P
```

---

## Revision 3 -- complete access matrix after checkpoint review REJECTED (`CE13-C003`)

Codex's §11.8.5 review of revision 2 at `2545bc42` (minion-agent-docs#162, 2026-09-24T20:57Z):
**REJECTED** -- `CE13-C003`: an unreadable directory fails Pi's `access(R_OK)` (EACCES, access site),
but revision 1/2's `file_info` directory shortcut answered `Cannot read ... is a directory` without
any readability check. Accepted. Revisions 1-2 are kept as history.

Three access edges in a row were found one at a time, so this revision stops patching cases and
measures the whole surface.

### Complete measured matrix

Evidence: `data/13-wp131-ce-l13-wp131-02-access-matrix/` (fixture `setup.sh`; `node_probe.mjs` runs
pinned Pi's read path operation by operation -- `access(R_OK)` (read.ts:248), `open`+`read` 4100
bytes (mime.ts sniff), `readFile` (read.ts:256/273); `minion_probe.py` runs the certified Layer 12
`LocalFileSystem`). Linux: Node 22.15.1 `node:22.15.1-bookworm-slim` as uid `node`, Python 3.12
`python:3.12-slim` as `nobody`, both unprivileged (mode bits apply). Windows 11: this host, Node
22.15.1, Python 3.13.5, deny ACLs.

```text
LINUX                   Pi: access  sniff    readFile   Pi site            | Minion read_binary_file
f_ok                        ok      ok       ok         -- success         | ok
f_000 (unreadable file)     EACCES  EACCES   EACCES     ACCESS             | permission_denied
d_ok (readable dir)         ok      EISDIR   EISDIR     READ (is a dir)    | is_directory
d_000 (unreadable dir)      EACCES  EACCES   EACCES     ACCESS  (CE13-C003)| permission_denied
d_x (search-only dir)       EACCES  EACCES   EACCES     ACCESS             | permission_denied
d_r (read, no search)       ok      EISDIR   EISDIR     READ (is a dir)    | is_directory
d_x/inner                   ok      ok       ok         -- success         | ok
d_r/inner (unsearchable)    EACCES  EACCES   EACCES     ACCESS             | permission_denied
lk -> f_ok                  ok      ok       ok         -- success         | ok
lk -> f_000                 EACCES  EACCES   EACCES     ACCESS             | permission_denied
lk -> d_ok                  ok      EISDIR   EISDIR     READ (is a dir)    | is_directory
lk -> d_000                 EACCES  EACCES   EACCES     ACCESS             | permission_denied
dangling symlink            ENOENT  ENOENT   ENOENT     ACCESS             | not_found
symlink loop                ELOOP   ELOOP    ELOOP      ACCESS             | unknown
f_ok/x (file component)     ENOTDIR ENOTDIR  ENOTDIR    ACCESS             | not_directory
missing                     ENOENT  ENOENT   ENOENT     ACCESS             | not_found

WINDOWS                 Pi: access  sniff    readFile   Pi site            | Minion read_binary_file
f_000 (deny read)           ok      EPERM    EPERM      READ               | permission_denied
d_ok                        ok      EISDIR   EISDIR     READ (is a dir)    | permission_denied (L12 defect)
d_000 (deny read)           ok      EPERM    EPERM      READ               | permission_denied
lk -> f_000 / lk -> d_000   ok      EPERM    EPERM      READ               | permission_denied
dangling symlink            ok (!)  ENOENT   ENOENT     READ               | not_found
symlink loop                ok (!)  ELOOP    ELOOP      READ               | invalid
f_ok/x                      ENOENT  ENOENT   ENOENT     ACCESS             | not_found
missing                     ENOENT  ENOENT   ENOENT     ACCESS             | not_found
```

(All other Windows rows succeed or match; full data in the JSON files.)

### What the matrix shows

1. **Linux (POSIX) -- the site is a function of the filesystem state, and that state is visible in one
   read's error code.** `access(R_OK)` fails exactly when the path does not resolve (`ENOENT`,
   `ENOTDIR`, `ELOOP`) or the target -- file OR directory -- is not readable (`EACCES`). The ONLY
   content-read failure that is not already an access failure is `EISDIR`, from a READABLE directory
   (directly or through a symlink). Minion's `read_binary_file` returns the corresponding code in
   every row (`permission_denied`, `not_found`, `not_directory`, `unknown`, `is_directory`).
2. **Windows -- Pi's `access` checks almost nothing.** libuv's `access` uses file attributes and does
   not follow the final symlink: it succeeds for unreadable files and directories, dangling links and
   link loops. Nearly every Windows failure is therefore the READ site in Pi.
3. **Pi's two calls open a race window; Minion needs only one call.** Codex's CE13-C002 H2 and C012's
   "removed between access and read" are states that CHANGE between Pi's `access` and `readFile`.
   With a single content read there is no such window to reproduce; each Minion call observes one
   state, and the rule below reports the site Pi reports for that state on POSIX.

### Proposed rule (replaces revisions 1-2's access step)

```text
read's filesystem access = ONE ctx.fs.read_binary_file(p) -- no separate access step, no signal.
  Ok                                         -> continue (sniff, image or text)
  Err(is_directory)                          -> "Cannot read <path>: is a directory"
  Err(not_supported)                         -> "Cannot read <path>: not supported by this provider"
  Err(not_found | permission_denied | not_directory | invalid | unknown)
                                             -> "Cannot access <path>: <cause phrase>"
<path> = ctx.fs.absolute_path(<step-5 string>)
```

This is Pi's POSIX site for every stable filesystem state in the matrix (Linux rows: 16/16), uses one
certified core operation (no `canonical_path`, `file_info` or `EXEC-007` dependency -- CE13-C001 and
the original C012 cannot arise), handles unreadable directories (CE13-C003) and needs no Layer 12
change. `not_supported` stays a read-site failure: the provider cannot supply content (R010-B).

### Disclosed divergences (for the owner)

- **D1 -- Windows host.** Pi reports most Windows failures at the READ site (row 2). The rule reports
  the POSIX site on every host -- the same choice as the owner's C012-A rationale ("matches Pi on
  POSIX; deterministic provider-independent projection; no platform concept in ctx.fs"), extended
  from `permission_denied` to all codes.
- **D2 -- Pi's race window.** A path whose state changes between Pi's `access` and `readFile` (removed,
  made unreadable, replaced by a directory) gets Pi's READ site; Minion, making one call, reports
  the site for the state it observed. Pi's own outcome in that window depends on timing.
- **D3 -- scope change versus the recorded C012-A text.** The owner's decision (`#48` comment
  `5822062094`) says that apart from `permission_denied`, failures "after the access step" stay at the
  read site (`not_found` -> `Cannot read ...`, etc.). That text assumed a separate access step
  (revision 1). With no separate step, a `not_found`/`not_directory`/`invalid`/`unknown` from the one
  read IS the state Pi's `access` rejects, so the rule reports it at the access site. This needs the
  owner's explicit confirmation; it is not assumed.
- **D4 -- Windows Layer 12 defect.** Certified Python `read_binary_file` on Windows classifies a
  readable directory as `permission_denied` (Node: `EISDIR`), so a directory read on Windows would
  say `Cannot access <path>: permission denied` instead of `Cannot read <path>: is a directory`. The
  fix belongs in Layer 12 (already escalated); `read` does not work around it with a check that
  would reintroduce CE13-C003.

### Alternatives for the owner menu

- **M-A (recommended):** the rule above (D1-D4 disclosed).
- **M-B:** a Layer 12 readability operation (`access(R_OK)`-equivalent) to reproduce Pi's two-call
  structure, including its race window. Still host-dependent (D1 unless the operation copies libuv's
  Windows behavior). Lower-layer change in both languages.
- **M-C:** READ site for every content failure (Windows-like). Diverges from Pi on POSIX for every
  missing / unreadable / bad-path case -- the common cases.

### Revised witnesses (replace W-C1..W-C8)

- `W-A1..W-A16`: one canonical case per Linux matrix row, real fixture where the host allows it
  (Windows cannot create mode-000 semantics), otherwise scripted `read_binary_file` codes; expected
  text from the Linux Pi site column.
- `W-A17` provider without `EXEC-007`, and a provider whose `canonical_path` is `not_supported`:
  reads normally, `fs_calls` = `read_binary_file` only.
- `W-A18` `not_supported` from `read_binary_file` -> `Cannot read ... not supported by this provider`.
- Negative controls: a `file_info` directory shortcut (fails W-A for `d_000`), any separate access
  step (fails W-A17's `fs_calls`), the revision-1 rule "every read failure is the read site except
  permission_denied" (fails `missing`/`dangling`).

I001 is unchanged (no checkpoint blocker at revisions 1-2).

### Revised checkpoint

```text
PROPOSED FOR IMPLEMENTATION  (revision 3; subject to the owner's M choice and D3 confirmation)

OPEN FINDINGS
    L13-WP131-I001, L13-WP131-C012 (+ CE13-C001, CE13-C002, CE13-C003)

ACCEPTANCE WITNESSES
    W-I1..W-I5; W-A1..W-A18 with the listed negative controls

NORMATIVE DELTAS
    spec/tools.md (read operation mapping -> the single-read rule; R010-B site text; D1-D4 disclosed;
    read/ls cancellation per I001), TOOL-039 (site rule and divergences), manifest TOOL-025/039 tests,
    conformance/agent/builtin-*.yaml

NEXT_OWNER
    Codex (checkpoint review of revision 3); then the owner for M and D3
```

---

## Revision 4 -- outcome cross-product and owner menu after checkpoint review REJECTED (`CE13-C004`)

Codex's §11.8.5 review of revision 3 at `c16ef87f` (minion-agent-docs#162, 2026-09-24T21:09Z):
**REJECTED** -- `CE13-C004`: a STABLE path can pass Pi's `access` and fail a later operation
(`/proc/self/mem`, Node 22.15.1 non-root: `access(R_OK)` ok, sniff `EIO`, `readFile` `EIO`), and an
independently supplied `ReadOperations` can do the same. Revision 3's one-read rule sends that `EIO`
(Layer 12 `unknown`) to the ACCESS site. Accepted. Revisions 1-3 are kept as history; revision 3's
matrix stays valid for static ordinary files.

### The structure, not more cases

Pinned Pi (`read.ts:47-61`, `248-273`) runs three independently supplied operations in order:
`A = access(p)` (required), `S = detectImageMimeType(p)` (optional; default = `open` + `read` 4100),
`R = readFile(p)`. The site is decided by WHICH operation failed:

```text
A        S        R        Pi outcome
fail(c)  -        -        Cannot access <path>: <c>
ok       fail(c)  -        Cannot read <path>: <c>          (a sniff failure is a read-stage failure)
ok       ok       fail(c)  Cannot read <path>: <c>
ok       ok       ok       success
```

Every code `c` that can occur at BOTH `A` and a later stage is ambiguous to any design that does not
itself perform `A`. From the measured matrix plus CE13-C004: `not_found`, `permission_denied`,
`not_directory`, `invalid`, `unknown` all occur at `A` (static states) AND at `S`/`R` (EIO, races,
Windows' attribute-only `access`, or any provider). Only `is_directory` is read-stage-only; only a
provider-level `not_supported` is unambiguous by definition.

**Conclusion: no composition of certified Layer 12 operations reproduces `A`.** `canonical_path`/
`file_info`/`probe_dir_entry` resolve paths but never check readability; `read_binary_file`/
`read_text_lines` check readability only by reading, which merges `A` with `R`. Preserving Pi's sites
in general needs an `A`-equivalent operation, or an owner-approved divergence.

### Owner menu (complete by construction: every row of the table above, every code)

- **G1 -- add Pi's `access` seam to `ctx.fs` (recommended; the only Pi-faithful option).** A new
  additive Layer 12 extension operation (e.g. `EXEC-008 check_readable(path, signal?) ->
  Result[None, FsError]`) with Pi's `access(path, R_OK)` meaning: resolve following symlinks; fail for
  an unresolvable path or a target that cannot be read; never read content. `read` then performs A,
  then one `read_binary_file` for S+R: A's error -> `Cannot access`, the read's error -> `Cannot read`,
  for every code -- reproducing the table exactly, including CE13-C004 and every race.
  Costs and sub-decisions: a Layer 12 contract pass and implementation in BOTH languages (reopens a
  certified layer -- owner authorization); its meaning on Windows (POSIX-style readability, as the
  owner's C012-A rationale chose, rather than libuv's attribute-only check); and what `read` does on a
  provider without the extension -- recommended: fall back to G2 below, disclosed as a
  provider-capability difference (CE13-C001's lesson: an optional operation must not make `read`
  unusable).
- **G2 -- one read, site from the error code (revision 3's rule).** No lower-layer change.
  Diverges from Pi whenever a later stage fails with an access-capable code: a stable I/O error
  (`EIO` -> `unknown`, CE13-C004), any virtual/remote provider whose read fails after its own access
  would pass, the Windows host (most failures), and Pi's race window.
- **G2' -- G2 with `unknown` moved to the read site.** Fixes CE13-C004's `EIO`; a symlink loop
  (`ELOOP`, an `A` failure) then reads `Cannot read ... unknown filesystem error`. All other G2
  divergences remain.
- **G3 -- one template for both sites.** Report every filesystem failure of `read` with one wording
  (e.g. `Cannot read <path>: <cause phrase>`). Removes the site distinction entirely: a change to the
  owner-decided R010-B (`TOOL-039`) templates, and it no longer reproduces Pi's `Cannot access` text
  anywhere.

The owner's C012-A decision (`#48` comment `5822062094`) and revision 3's D3 question both fold into
this choice: under G1 the site is exact and C012-A only fixes the Windows meaning of the new
operation; under G2/G2' the owner accepts the listed divergences; under G3 the question disappears.

### Witnesses for any option

`W-X1` Codex's CE13-C004 witness at the seam: scripted provider, `A ok`, read `Err(unknown)` (EIO)
-> `Cannot read <path>: unknown filesystem error` under G1/G2', `Cannot access ...` under G2 (the
chosen option decides; the other must fail it as its negative control). `W-X2` `A fail(c)` for every
code -> `Cannot access` (G1). `W-X3` `A ok`, read fail(c) for every code -> `Cannot read` (G1). `W-X4`
provider without the new operation -> the fallback rule. Revision 3's `W-A1..W-A18` stay as the
static-state regression set; I001's `W-I1..W-I5` unchanged.

### Checkpoint

```text
NOT PROPOSED FOR IMPLEMENTATION -- awaiting the owner's G choice (§11.7 governance:
G1 reopens Layer 12; G2/G2'/G3 are intentional divergences).

OPEN FINDINGS
    L13-WP131-I001 (characterization accepted at revisions 1-3), L13-WP131-C012
    (+ CE13-C001..C004)

NEXT_OWNER
    Owner (G choice); then Claude authors the checkpoint for the chosen option and Codex reviews it
    (§11.8.5). Implementation stays frozen.
```

---

## Revision 5 -- G1 checkpoint on certified `EXEC-008`

Mode: workflow §11.8.3 checkpoint authoring, resumed by the fired deferred trigger on
`minion-agent#48` after `WP-12.E2` / `EXEC-008` became `CERTIFIED_CLOSED` (`minion-agent#62`, closure
record in its body; owner closure decision `#62` comment `5827959957`, section 4). **No
implementation performed.** The WP-13.1 candidate stays frozen: code #60 @ `61f40e4d`, docs #162 @
`ceae53a4` (this revision's parent). Revisions 1-4 are kept as reviewed history.

### Governance and certified inputs

- **C012 structure:** the owner selected `G1` (`minion-agent#48` comment `5822609576`).
  - G2, G2' and G3 are not selected as primary semantics.
  - The G2 rule survives only as the disclosed fallback for providers without `EXEC-008`.
- **The `check_readable` seam:** `EXEC-008 check_readable(path, signal?) -> Result[None, FsError]`, `spec/execution.md`
  §12, certified at docs `master` `e1d9b817096de2797df00b17f354c2ca1451629a`.
  - Python is at `minion-agent/main` `9987bd81`; Rust is at `689db685`.
  - The manifest status is synced at `6dbec20a`.
- **Its certified behaviour:**
  - it follows symlinks and consumes no content;
  - POSIX is `access(path, R_OK)`, keeping the native errno;
  - Windows reports the target's real readability (a deny ACL gives `permission_denied`, a dangling link gives `not_found`);
  - an embedded NUL gives `unknown`;
  - `not_supported` means only that the provider lacks the capability;
  - `signal` is accepted but not inspected.
- **Layer-13 consumption:** the §12.5 pattern is normative for `read` (`TOOL-025`). This revision applies
  it; it does not re-derive it.
- **Owner-required resumption sequence** (`#62` comment `5827959957`, section 4):
  1. update this checkpoint;
  2. integrate: `check_readable` failure -> `Cannot access`, later read failure -> `Cannot read`, provider without `EXEC-008` -> disclosed G2 fallback;
  3. preserve the settled I001 ordering rule;
  4. Codex §11.8.5 review;
  5. only then remediate the frozen Python candidate.

### What G1 supersedes

| Superseded | Status now |
|---|---|
| Revision 1's R-C1..R-C4 (`canonical_path` access step, `file_info` directory shortcut) | superseded |
| Revision 2's Q/P options | superseded |
| Revision 3's single-read site-from-code rule and its D1-D4 | superseded (D3 is moot) |
| Revision 4's G2/G2'/G3 | not selected; G2 kept only as the fallback |
| The owner's C012-A (`#48` comment `5822062094`) | Windows meaning now lives in `EXEC-008`'s certified Windows disposition; no separate `read` rule remains |
| Docs #162's `spec/tools.md` "`read`: operation mapping" steps 3-4 (`file_info` access step, then read-code -> site collapse) | superseded |
| Docs #162's "Disclosed edges of that mapping" | superseded |
| Docs #162's "Which `ctx.fs` failure lands at which of these two sites..." site paragraph | superseded |
| Frozen code #60's `_read_failure_site` and its `file_info` access step | superseded |

### Observable rules (C012 under G1)

```text
read's filesystem access (replaces #162 "read: operation mapping" steps 3-4; steps 1-2 and 5 unchanged):

1. Cancellation pre-check ("Operation aborted", no ctx.fs call).                    [unchanged]
2. Path: TOOL-026 steps 1-4 ...; abort checkpoint (read.ts:246).                     [unchanged]
3. Access -- Pi's A = ops.access(absolutePath) = access(R_OK):
     r = ctx.fs.check_readable(p)          -- NO signal (Pi passes none to access)
       Err(not_supported)  -> the provider lacks EXEC-008: continue in FALLBACK mode
       Err(c)              -> "Cannot access <path>: <cause(c)>"          for EVERY other code c
       Ok                  -> continue in NORMAL mode
   Abort checkpoint (read.ts:249) -- also after the not_supported answer (A has completed).
4. Content (Pi's S + R: the MIME sniff's own open/read and readFile):
     ONE ctx.fs.read_binary_file(p)        -- NO signal
       NORMAL mode:    Err(c) -> "Cannot read <path>: <cause(c)>"                 for EVERY code c
       FALLBACK mode:  Err(is_directory | not_supported) -> "Cannot read <path>: <cause(c)>"
                       Err(any other c)                  -> "Cannot access <path>: <cause(c)>"
5. Sniff the first 4100 bytes, then image or text.                                    [unchanged]

<path> = ctx.fs.absolute_path(<step-5 string>)                                        [unchanged]
```

- **R-G1. The operation that failed owns the site, whatever the code.**
  - Step 3's failure is the access site; step 4's failure is the read site.
  - This is Pi's `A`/`S`/`R` table (revision 4) reproduced exactly.
  - No error code is ever translated into a site.
- **R-G2. A directory is not decided by `read`.**
  - A readable directory passes step 3, and step 4 fails `is_directory` -> `Cannot read <path>: is a directory` (Pi: `access` ok, `readFile` `EISDIR`).
  - An unreadable directory fails step 3 -> `Cannot access <path>: permission denied` (Pi, `CE13-C003`).
  - There is no `file_info` or `canonical_path` shortcut.
- **R-G3. Fallback is only for a genuine capability gap.**
  - It is entered only on step 3's `not_supported`.
  - The certified first-party providers never produce `not_supported` from `check_readable` (§12.5, and `WP12E2-RI001` closed in Rust), so on them the normal mode always applies.
  - The fallback is a provider-capability fallback and an intentional approximation (the owner's G2). It is never described as Pi-equivalent.
- **R-G4. `ctx.fs` calls.**
  - The filesystem-access calls are exactly `check_readable(p)` then `read_binary_file(p)`, in that order, neither receiving the signal.
  - `absolute_path` is still used only to build `<path>` text.
  - `read` makes no `canonical_path`, `file_info`, `probe_dir_entry`, `list_dir_raw` or `read_text_*` call; `EXEC-007` stays unused.
  - A step-2 rejection or an abort at checkpoint 246 makes no `check_readable` call. A step-3 failure, or an abort at checkpoint 249, makes no `read_binary_file` call.

### Observable rules (I001 -- unchanged, integrated)

I001's settled rules R-I1..R-I4 are unchanged; characterization was accepted at revisions 1-3, and no checkpoint blocker has been raised against them.
- **Where the checkpoints are:** R-I4's two `read` checkpoints are now "after path resolution" (read.ts:246) and "after `check_readable` returns, including its `not_supported` answer" (read.ts:249).
- **A blocked `check_readable`:**
  - `"Operation aborted"` is delivered as soon as the abort is observed, while the call is still blocked (R-I2).
  - The call is neither cancelled nor given the signal (R-I3). `EXEC-008` does not inspect a signal anyway, and `read` passes none.
  - When it completes, `read` stops at checkpoint 249 and makes no `read_binary_file` call.
- **Settle point (R-I1):** abort before the settle point, including a failure thrown after the abort, gives `Operation aborted`. A result or error settled before the abort stands. `RunSignal` stays as certified; there is no Layer 09 change.

### Behavior matrix (G1; `<path>` as above)

POSIX (the revision 3 Linux measurement, re-read under G1 -- every row equals Pi's site):

```text
case                         check_readable        read_binary_file      read's text
f_ok / lk -> f_ok            Ok                    Ok                    success
f_000 / lk -> f_000          permission_denied     (not called)          Cannot access <path>: permission denied
d_ok / lk -> d_ok / d_r      Ok                    is_directory          Cannot read <path>: is a directory
d_000 / lk -> d_000 / d_x    permission_denied     (not called)          Cannot access <path>: permission denied
d_x/inner                    Ok                    Ok                    success
d_r/inner (unsearchable)     permission_denied     (not called)          Cannot access <path>: permission denied
dangling symlink / missing   not_found             (not called)          Cannot access <path>: no such file or directory
symlink loop                 unknown (ELOOP)       (not called)          Cannot access <path>: unknown filesystem error
f_ok/x (file component)      not_directory         (not called)          Cannot access <path>: not a directory
embedded NUL                 unknown               (not called)          Cannot access <path>: unknown filesystem error
```

Provenance rows (any host; scripted provider over the real seam):

```text
case                                            A (check_readable)   later read            read's text
A fails with c (every code except not_supported) Err(c)              (not called)          Cannot access <path>: <cause(c)>
A ok, read fails with c (every code)            Ok                   Err(c)                Cannot read <path>: <cause(c)>
stable EIO after A (CE13-C004, /proc/self/mem)  Ok                   Err(unknown)          Cannot read <path>: unknown filesystem error
target removed after A                          Ok                   Err(not_found)        Cannot read <path>: no such file or directory
permission removed after A (CE13-C002 H2)       Ok                   Err(permission_denied) Cannot read <path>: permission denied
unreadable before A (CE13-C002 H1)              Err(permission_denied) (not called)        Cannot access <path>: permission denied
provider without EXEC-008, read ok              Err(not_supported)   Ok                    success (FALLBACK)
provider without EXEC-008, read fails c         Err(not_supported)   Err(c)                is_directory|not_supported -> Cannot read; else Cannot access
provider without EXEC-007                       Ok                   Ok                    success (EXEC-007 unused)
```

Windows (Python `LocalFileSystem`, certified `EXEC-008` Windows disposition), with every Pi difference disclosed:

```text
case                     check_readable      read's text                                   pinned Pi on Windows
f_000 / lk -> f_000      permission_denied   Cannot access <path>: permission denied       Cannot read (EPERM)          W-1
d_000                    permission_denied   Cannot access <path>: permission denied       Cannot read (EPERM)          W-1
dangling symlink         not_found           Cannot access <path>: no such file ...        Cannot read (ENOENT)         W-1
symlink loop             invalid             Cannot access <path>: invalid path            Cannot read (ELOOP->unknown) W-1, W-2
d_ok (readable dir)      Ok                  Cannot read <path>: permission denied         Cannot read ... is a dir     W-3
f_ok/x, missing          not_found           Cannot access <path>: no such file ...        Cannot access (ENOENT)       equal
```

### Disclosed divergences

- **W-1: Windows site.** On Windows, Pi's `access` is libuv's attribute-only check, so most Windows failures land at Pi's read site. Minion reports the access site for them.
  - This is the certified `EXEC-008` Windows disposition, `MINION_ARCHITECTURAL_MAPPING`: the owner's C012-A/G1 rationale is deterministic readability semantics with no platform identity in `ctx.fs`.
  - It is inherited from `EXEC-008`; `read` adds nothing.
- **W-2: Windows symlink-loop code.** Python classifies it `invalid` where Node reports `ELOOP` (-> `unknown`); Rust gives `unknown`.
  - This is the pre-existing Layer-12 mapper divergence `L12-WINDOWS-ERROR-MAP`, `minion-agent#69`, remediation not authorized. `read` inherits whatever `check_readable` reports and does not remap it.
- **W-3: Windows readable directory.** Certified Python `read_binary_file` classifies a directory read as `permission_denied` (`L12-WINDOWS-DIRECTORY-READ`, `minion-agent#67`, remediation not authorized).
  - The site matches Pi (`Cannot read`); the cause phrase differs.
  - `read` does not work around it: a `file_info` shortcut would reintroduce `CE13-C003`.
- **F-1: fallback.** On a provider without `EXEC-008`, sites are recovered from codes (G2). This is an intentional approximation, disclosed as a provider-capability difference, never Pi-equivalent.
  - It is reachable only on third-party providers (R-G3).
- **Race parity:** there is none to disclose.
  - With `A` performed, Pi's race windows (`H2`, removal after access, `CE13-C004`) are reproduced exactly: whichever call observed the failure owns the site.
  - Pi's separate sniff `open` before `readFile` is merged into one `read_binary_file`; both are read-stage, so the site is identical (revision 1, "out of scope").

### Resolution of the checkpoint findings

| Finding | Resolution under G1 |
|---|---|
| `CE13-C001` (optional access-step operation) | `EXEC-008` is an additive capability whose absence is answered explicitly (`not_supported`), and R-G3's disclosed fallback keeps `read` usable. It also uses no `canonical_path`/`EXEC-007` dependency. |
| `CE13-C002` (two `permission_denied` histories) | `A` distinguishes H1 (access site) from H2 (read site), as in Pi. |
| `CE13-C003` (unreadable directory) | Fails `A` -> access site. |
| `CE13-C004` (stable EIO after a successful access) | A read-stage failure -> `Cannot read`. |
| `L13-WP131-C012` | Resolved by R-G1..R-G4, subject to this checkpoint's review. |
| `L13-WP131-I001` | Resolved by R-I1..R-I4 as integrated above. |

### Acceptance witnesses (replace W-C1..W-C8, W-A17/W-A18 and W-X1..W-X4; W-I1..W-I5 kept)

The G1 witnesses. The owner's required witness list (`#48` comment `5822609576`) maps onto W-G1..W-G10.
- `W-G1`: `A` fails with every R010-B vocabulary code except `not_supported` (`not_found`, `permission_denied`, `not_directory`, `is_directory`, `invalid`, `unknown`) -> `Cannot access <path>: <cause>`. There is no `read_binary_file` call. Scripted `check_readable`.
- `W-G2`: `A` ok, then the read fails with each of the seven vocabulary codes (including `not_supported`) -> `Cannot read <path>: <cause>`. Scripted `read_binary_file`.
  - `aborted` is unreachable from `ctx.fs` here: neither call receives the signal.
- `W-G3`: stable `unknown` (EIO) after `A` ok -> `Cannot read` (Codex's `CE13-C004`).
- `W-G4`: a real missing target -> `Cannot access ... no such file or directory`.
- `W-G5`: target removed after `A` -> `Cannot read ... no such file or directory` (scripted read `not_found` after a real `A` ok).
- `W-G6`: permission denied at `A` -> `Cannot access ... permission denied`.
  - Real fixture: a POSIX mode-000 file run unprivileged, and a Windows deny-`RD` ACE; otherwise scripted.
- `W-G7`: permission denied after `A` -> `Cannot read ... permission denied` (scripted read).
- `W-G8`: a real symlink to a readable target -> success.
- `W-G9`: a real dangling symlink -> `Cannot access ... no such file or directory`.
- `W-G10`: provider without `EXEC-008` (scripted `check_readable` -> `not_supported` for every path).
  - Read ok -> success.
  - Read `is_directory` / `not_supported` -> `Cannot read`.
  - Read `not_found` / `permission_denied` / `not_directory` / `invalid` / `unknown` -> `Cannot access`.
- `W-G11`: a readable directory, real and through a symlink -> `Cannot read <path>: is a directory` on POSIX.
  - On Windows the expected text records W-3 explicitly, rather than skipping the case.
- `W-G12`: an unreadable directory -> `Cannot access ... permission denied` (`CE13-C003`).
- `W-G13`: `fs_calls` pinning.
  - Success -> `[check_readable, read_binary_file]`.
  - `A` fails -> `[check_readable]`.
  - Step-2 rejection -> `[]`.
  - None of the calls carries a signal.
- `W-G14`: the checkpoint-249 abort. `check_readable` is blocked; abort; release -> `Operation aborted`, and no `read_binary_file` call (R-I4 + W-I5 on the new seam).

The I001 witnesses `W-I1..W-I5` are unchanged; W-I5's blocked access call is now `check_readable`. Revision 3's Linux static matrix stays as regression evidence under the G1 expectations above.

Negative controls (§11.8.7.1), each of which must fail the stated witness:

| Negative control | Must fail |
|---|---|
| Swap provenance: site from the code in normal mode (the `61f40e4d` / #162 rule) | W-G2, W-G3, W-G5, W-G7 |
| Always use the fallback, even when `A` succeeded | W-G3, W-G5, W-G7 |
| Skip `A` (read only) | W-G6, W-G12, W-G13 |
| Treat `A`'s `not_supported` as `Cannot access` | W-G10 |
| `file_info` directory shortcut | W-G12, W-G13 |
| Pass the signal to `check_readable` / `read_binary_file` | W-G13, W-I5 |
| Read after a checkpoint-249 abort | W-G14 |
| Settle-then-check removed | W-I1 |
| Result re-checked after settling | W-I4 |

### Normative deltas

- **`spec/tools.md`:**
  - replace #162's "`read`: operation mapping" steps 3-4 with the rules above, and replace "Disclosed edges" with W-1..W-3 and F-1;
  - rewrite the site paragraph ("Which `ctx.fs` failure lands at which of these two sites ...") to R-G1;
  - R010-B's two-site table: the access site's reachable codes become every code `check_readable` can return except `not_supported`, plus the fallback's; the read site's become all codes;
  - the cancellation paragraph names checkpoint 249 as "after `check_readable`";
  - the "access step history" bullet gains the G1 entry.
- **`pi-parity-manifest.yaml`:**
  - `TOOL-025` (depends on `EXEC-008`; tests W-G*), `TOOL-039` (site rule by provenance; W-1..W-3 and F-1 disclosed);
  - no change to `EXEC-008`.
- **`conformance/schema/builtin-tool-scenario.schema.json`:**
  - `provider.check_readable` (an array of `scriptedError`, per path);
  - `provider.without_exec_008` (`const: true`: `check_readable` returns `not_supported`);
  - `provider.file_info` is kept for `ls` only if still used there.
  - The runner stays thin: it answers scripted calls and records calls, and it never performs `read`'s site logic.
- **`conformance/agent/builtin-read-*.yaml`:**
  - the R010-B per-code scenario is rescripted onto `check_readable` (access site) and `read_binary_file` after `A` ok (read site);
  - new scenarios cover W-G3/W-G5/W-G7/W-G10/W-G12/W-G13/W-G14.

### Implementation constraints

- Python only; Rust WP-13.1 is not authorized.
- No Layer 09 change.
- No Layer 12 change: `EXEC-008` is certified as-is; `#65`/`#66`/`#67`/`#69`/`#70` are not remediated here.
- `read` uses `check_readable` as specified in §12.5, without remapping its codes.

### Checkpoint

```text
PROPOSED FOR IMPLEMENTATION  (revision 5; G1 on certified EXEC-008)

OPEN FINDINGS
    L13-WP131-I001  (rules R-I1..R-I4, integrated above)
    L13-WP131-C012  (rules R-G1..R-G4; CE13-C001..C004 resolved as stated above)

ACCEPTANCE WITNESSES
    W-I1..W-I5, W-G1..W-G14, with the negative controls above;
    revision 3 Linux static matrix as regression evidence under G1 expectations

DISCLOSED DIVERGENCES
    W-1 (EXEC-008 Windows disposition), W-2 (#69), W-3 (#67), F-1 (G2 fallback)

NORMATIVE DELTAS
    spec/tools.md (read mapping, site paragraph, R010-B site table, cancellation checkpoint text),
    pi-parity-manifest.yaml (TOOL-025, TOOL-039), conformance schema (check_readable scripting,
    without_exec_008), conformance/agent/builtin-read-*.yaml

NEXT_OWNER
    Codex -- §11.8.5 review of exactly this checkpoint. Implementation of the frozen Python
    candidate starts only after checkpoint agreement.
```

---

## Revision 6 -- delta-inventory corrections after checkpoint review REJECTED (`CE13-C005`, `CE13-C006`)

Codex's §11.8.5 review of revision 5 at `90dddb7e` (minion-agent-docs#162 comment `5828171940`;
review-only evidence docs #166 @ `c83f10a7`): **REJECTED**, for two live normative contradictions
missing from revision 5's delta inventory. R-G1..R-G4, W-G1..W-G14, W-1..W-3/F-1 and the integrated
I001 rules were found acceptable for the checkpoint. Both findings are accepted. Revision 5 is kept
as reviewed history; this revision amends only its checkpoint-249 wording, its witnesses and its
normative-delta inventory. The rules R-G1..R-G4 are otherwise unchanged.

### CE13-C005 -- the fallback branch must pass checkpoint 249 (`spec/execution.md` §12.5)

- **The contradiction:** certified `spec/execution.md` §12.5 (docs `master` `e1d9b817`) sends `Err(not_supported)` straight to "step 3 in FALLBACK mode", and only its `Ok` branch visits the `read.ts:249` abort checkpoint. Revision 5 requires the checkpoint after `check_readable` returns, including its `not_supported` answer. An implementation could follow either text.
- **Pi's placement:** pinned Pi checks `if (aborted) return` immediately after its access call returns, before the sniff and `readFile` (`read.ts:248-250`). Pi has no fallback, so the Pi-faithful placement is a checkpoint after the access stage has completed, whichever way it completed.
- **The rule (amends revision 5's step 3):**

  ```text
  3. Access:
       r = ctx.fs.check_readable(p)          -- no signal
         Err(not_supported)  -> mode := FALLBACK
         Err(c)              -> "Cannot access <path>: <cause(c)>"      (stop)
         Ok                  -> mode := NORMAL
     Abort checkpoint (read.ts:249): ONE check, reached in BOTH modes, before any content work.
     An abort observed here -> "Operation aborted"; no read_binary_file call in either mode.
  ```

- **Classification:** `CONTRACT_ASSURANCE_DEFECT`, in §12.5's Layer-13 consumption pattern. §12.5 is normative for `TOOL-025`, not part of `EXEC-008`'s operation semantics.
- **What the correction leaves alone:**
  - `check_readable`'s signature, POSIX and Windows semantics, error mapping and its accepted-not-inspected signal;
  - its §12.6 witnesses;
  - the Python/Rust certification;
  - the fallback's site mapping.
- It changes only where `read` places its checkpoint on the fallback branch. No `EXEC-008` implementation changes, because neither certified implementation contains Layer-13 `read` code.
- **New witness, `W-G15` (fallback abort):**
  - Setup: a provider without `EXEC-008` (`check_readable` returns `not_supported`); the signal is aborted after that answer and before any content read.
  - Expected: `"Operation aborted"`, with `fs_calls == [check_readable]`: zero `read_binary_file` calls.
  - The normal-branch counterpart is `W-G14`.
- **Negative control:** a literal pre-correction §12.5 reading, where `not_supported` goes directly to the fallback read and skips the checkpoint, must fail `W-G15`.

### CE13-C006 -- the path pipeline still names `file_info` for `read` (`spec/tools.md`, TOOL-026 step 5)

- **The contradiction:** candidate `spec/tools.md` (docs #162) says, in the TOOL-026 path pipeline's step 5, "`file_info then read_binary_file for read`, core operations only". Revision 5's R-G4 forbids `file_info`, and its delta list did not name this upstream passage.
- **Replacement text for `read` in step 5:** "`check_readable` then `read_binary_file` for read (`EXEC-008`, `spec/execution.md` §12.5; see '`read`: operation mapping' below; `L13-WP131-C012`)".
  - Unchanged: `ls`'s `probe_dir_entry` / `list_dir_raw` (`EXEC-007`) and every TOOL-026 path transformation.
- **Sweep of the live `spec/tools.md` at `90dddb7e`**, every `read`-access instruction:

  | Location | Wording | Disposition |
  |---|---|---|
  | lines 609-612, path pipeline step 5 | `file_info then read_binary_file` | **replace** (this finding) |
  | lines 939-943, site paragraph | "with the core `file_info` as the access step ..." | **replace** (already in revision 5's delta list) |
  | lines 966-980, "`read`: operation mapping" steps 3-4 | `file_info` access step; code -> site | **replace** (already listed) |
  | lines 987-996, "Access step history" | `IMPL-C002`, `probe_dir_entry`, then C012 | **keep as history**, append the G1 entry |
  | line 638, the `L13-WP131-R002` correction | names `file_info` among operations that take `path: str` | **unchanged**: historical and descriptive, not a `read` access instruction |

  No other live `read`-access instruction names `file_info`, `canonical_path`, `probe_dir_entry` or `list_dir_raw`.
- **New witness, `W-G16` (no `file_info` dependency):** a conforming provider supports `check_readable` and `read_binary_file` but returns `not_supported` from `file_info` (and from `canonical_path`).
  - Expected: `read` succeeds on a readable file, with `fs_calls == [check_readable, read_binary_file]`.
- **Negative control:** an implementation following the uncorrected step 5 (calling `file_info`) must fail `W-G16`, and `W-G13`'s call pinning.

### Complete normative-delta inventory (replaces revision 5's list)

1. **Carry §12 onto the WP-13.1 docs branch first.**
   - Docs #162's base (`f46051fb`) predates `WP-12.E2`, so its `spec/execution.md` has no §12.
   - The branch merges current docs `master` (`e1d9b817`) before any §12.5 edit. A clean merge was verified with `git merge-tree`.
   - This is a merge, not a rewrite: #162's history and every review artifact stay unchanged.
2. **`spec/execution.md` §12.5 (CE13-C005):**
   - the consumption pattern gains the common checkpoint rule above;
   - a correction note under §12.5 cites this revision and states that `EXEC-008`'s operation semantics, witnesses and certification are unchanged;
   - §12's status paragraph ("unchanged in substance from its approved, merged revision") gains "except the §12.5 Layer-13 checkpoint correction noted there".
3. **`spec/tools.md`:**
   - TOOL-026 path pipeline step 5 (CE13-C006);
   - "`read`: operation mapping" steps 3-4 -> R-G1..R-G4 with the amended step 3;
   - the site paragraph -> R-G1;
   - "Disclosed edges" -> W-1..W-3 and F-1;
   - R010-B's two-site table: reachable codes per revision 5;
   - the `read` cancellation paragraph: checkpoint 249 = "after `check_readable` returns, in both modes";
   - the "Access step history" bullet: append the G1 entry;
   - the `read` witness list gains W-G1..W-G16.
4. **`pi-parity-manifest.yaml`:**
   - `TOOL-025`: depends on `EXEC-008`; tests W-G1..W-G16, W-I1..W-I5;
   - `TOOL-039`: the site rule is by provenance; W-1..W-3 and F-1 are disclosed;
   - `EXEC-008`: no change.
5. **`conformance/schema/builtin-tool-scenario.schema.json`:**
   - `provider.check_readable` (`scriptedError[]`) and `provider.without_exec_008` (`const: true`);
   - scripted `file_info` / `canonical_path` `not_supported` for `W-G16`;
   - a scripted abort point between `check_readable` and the content read, for `W-G14`/`W-G15`.
   - The runner stays thin: it answers scripted calls, records `fs_calls` and triggers the abort. It never performs `read`'s site or checkpoint logic.
6. **`conformance/agent/builtin-read-*.yaml`:**
   - the R010-B per-code scenario is rescripted onto `check_readable` (access site) and `read_binary_file` after `A` ok (read site);
   - new scenarios cover W-G3, W-G5, W-G7, W-G10, W-G12..W-G16.

### Acceptance witnesses (amends revision 5)

W-I1..W-I5; W-G1..W-G16 (W-G15 and W-G16 are new here); revision 5's negative controls, plus:

| Negative control | Must fail |
|---|---|
| Fallback skips checkpoint 249 | W-G15 |
| `read` calls `file_info` / follows the uncorrected step 5 | W-G16 and W-G13 |

### Checkpoint

```text
PROPOSED FOR IMPLEMENTATION  (revision 6 = revision 5 amended for CE13-C005 and CE13-C006)

OPEN FINDINGS
    L13-WP131-I001  (R-I1..R-I4; checkpoint 249 reached in both NORMAL and FALLBACK modes)
    L13-WP131-C012  (R-G1..R-G4 with the amended step 3; CE13-C001..C004 resolved per revision 5;
                     CE13-C005 and CE13-C006 addressed above)

ACCEPTANCE WITNESSES
    W-I1..W-I5, W-G1..W-G16, with the negative controls of revisions 5 and 6

DISCLOSED DIVERGENCES
    W-1 (EXEC-008 Windows disposition), W-2 (#69), W-3 (#67), F-1 (G2 fallback)

NORMATIVE DELTAS
    the complete inventory above (items 1-6)

NEXT_OWNER
    Codex -- §11.8.5 re-review of exactly this revision. The frozen Python candidate (#60 @ 61f40e4d)
    is not touched until checkpoint agreement.
```
