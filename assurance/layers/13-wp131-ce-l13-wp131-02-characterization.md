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
