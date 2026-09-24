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
