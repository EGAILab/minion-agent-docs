# CE-L13-WP131-01 — Lane B: malformed `file://` path behavior (`R002`)

Mode: §11.8 sub-checkpoint characterization, Lane B only. **No Python or Rust implementation
performed or authorized. No Layer 12 production change. Review this lane only -- do not reopen
`R003`/`R004`/`R008` (frozen `CHECKPOINT-READY`) or Lane A's `R005` (`OWNER_DECISION_RESOLVED`,
`R005-A`, `minion-agent#48` governance record) unless this lane presents concrete contradictory
evidence.**

Parent episode: `CE-L13-WP131-01` (`minion-agent#48`). Gives `R002` its own complete
characterization -- the second independent review (`minion-agent-docs#134`) found it had none,
appearing only inside manifest-coherence discussion.

---

## Pi's exact behavior

**Pi input**: a `read`/`ls` tool `path` argument beginning with the literal characters `file://`,
where the remainder does not parse as a well-formed, platform-representable file URL.

**Pi source path**: `packages/coding-agent/src/utils/paths.ts`, `normalizePath` (lines 95-97,
quoted in full):

```js
if (/^file:\/\//.test(normalized)) {
  return fileURLToPath(normalized);
}
```

No `try`/`catch` around this call. `normalizePath` is called by `resolveToCwd`
(`path-utils.ts:48-50`), which every `read`/`ls` path-argument resolution goes through
(`path-utils.ts:40-49`, `resolveToCwd`, re-confirmed this lane). A thrown exception here
propagates unguarded to the tool's own outer `try`/`catch` (`read.ts:243-332`'s async IIFE, or
`ls.ts`'s equivalent), which does a bare `reject(error)`/`reject(e)` with the **raw, unmodified**
Node exception -- no custom message wrapping.

**Exact malformed-URL witnesses (directly executed this session, Node `fileURLToPath`, this
session's platform `win32`)**:

```text
fileURLToPath("file:///C:/%ZZ")        -> THROWS URIError, message "URI malformed"
                                           (invalid percent-encoding: %ZZ is not valid hex)
fileURLToPath("file:///%ZZ")            -> THROWS URIError, message "URI malformed"
fileURLToPath("file://")                -> THROWS TypeError, code ERR_INVALID_FILE_URL_PATH,
                                           message "File URL path must be absolute"
fileURLToPath("file:///C:/valid.txt")   -> SUCCEEDS -> "C:\\valid.txt" (control case, confirms
                                           the probe methodology against a well-formed input)
fileURLToPath("file:///C:/%25")         -> SUCCEEDS -> "C:\\%" (valid percent-encoding of the
                                           literal "%" character, a second control case
                                           distinguishing "contains a percent sign" from
                                           "contains invalid percent-encoding")
```

Two distinct JS exception shapes reach the tool caller unguarded: `URIError` (malformed
percent-encoding, no `.code` set) and `TypeError` with `.code === "ERR_INVALID_FILE_URL_PATH"`
(structurally parseable URL that does not resolve to an absolute path on the current platform --
itself platform-dependent: a POSIX-style `file:///name.txt` with no drive letter is rejected as
"must be absolute" specifically on Windows, since Windows `fileURLToPath` requires a drive-letter
path; the identical URL string may succeed on POSIX).

**Pi observable result**: the tool call rejects with the raw JS exception (its constructor name,
`.message`, and, for the `TypeError` case, its `.code`) as the surfaced error -- not a
Pi-hand-authored message, not normalized across the two exception shapes, and not identical
across platforms for the "must be absolute" case specifically.

## Minion's exact behavior

**Minion input**: the identical `path` argument, after Layer 13's shared preprocessing pipeline
(Unicode-space normalize, `@`-strip, Windows-shell-path normalize -- `TOOL-026`, unaffected by
this finding) reaches `ctx.fs`'s read-only operations (`read_text_file`/`list_dir`/etc.), each of
which resolves the string via the already-certified `resolve_local_path` (Layer 12,
`filesystem.py:86-126`).

**Layer-12 resolution path** (quoted in full, lines 102-113, re-confirmed this lane):

```python
elif normalized.startswith("file://"):
    with suppress(ValueError, OSError):
        normalized = _file_url_to_path(normalized)
```

`_file_url_to_path`'s own internal failure (invalid percent-encoding, malformed structure, etc.)
raises `ValueError`/`OSError`, which this `suppress()` context manager silently discards --
**`normalized` is left completely UNCHANGED** (still the literal `"file://..."` string), and
execution falls through to the SAME `isabs`/`resolve` pipeline every other path goes through
(lines 114-126).

**Minion observable result (directly executed this session, reproducing `resolve_local_path`
exactly, `cwd = "C:\cwd"`)**:

```text
resolve_local_path(cwd, "file:///C:/%ZZ")       -> "C:\\cwd\\file:\\C:\\%ZZ"
resolve_local_path(cwd, "file:///%ZZ")           -> "C:\\cwd\\file:\\%ZZ"
resolve_local_path(cwd, "file://")               -> "C:\\cwd\\file:"
resolve_local_path(cwd, "file:///C:/valid.txt")  -> "C:\\valid.txt"    (control case, correct)
```

The literal `"file://..."` string is **not** recognized as an absolute path by `os.path.isabs`
(it does not match a drive-letter or UNC prefix), so it falls to the final `else` branch and is
treated as an ordinary **relative path segment**, joined onto `cwd` and lexically normalized.
The result is a syntactically well-formed but almost-certainly-nonexistent path. When this string
is subsequently passed to `ctx.fs.read_text_file()`/`list_dir()`/etc., the underlying OS call
fails with "no such file or directory," which Layer 12 already classifies as `FsErrorCode
.NOT_FOUND` (`filesystem.py`'s `to_fs_error`, an already-certified Layer 12 mapping, not examined
further in this lane -- see Lane E/`R010` for the complete `FsErrorCode` projection question).

**Minion observable result, in summary**: an ordinary `not_found`-class `FsError` -- the SAME
error shape and classification a genuinely-missing ordinary file path would produce. No
URL-parsing-specific error, no distinction between "malformed URL" and "well-formed but
nonexistent path."

## Reason for the difference

Pi's `coding-agent` tool layer's own path resolver (`utils/paths.ts`) calls `fileURLToPath`
**unguarded**. Layer 12's `resolve_local_path` -- which Layer 13 consumes rather than
re-deriving, per `TOOL-026`'s already-established, unchallenged architectural mapping -- mirrors a
**different** pinned-Pi function instead: the harness-level resolver
(`packages/agent/src/harness/env/nodejs.ts:57-62`), which explicitly wraps the same call in
`try { normalized = fileURLToPath(normalized); } catch { /* keep malformed URLs as ordinary
paths */ }`. Pi itself is internally inconsistent between these two resolvers on this exact
point -- one catches, one does not. Layer 12's `L12-PY-R002` characterization (this project's own
prior work, independently reviewed and certified) deliberately chose to match the **catching**
harness-level resolver, for reasons specific to that layer's own scope. `TOOL-026` then built
Layer 13's path pipeline on top of that already-certified, catching seam -- inheriting its
fall-through behavior for this one input class as a side effect, not a Layer-13-specific design
choice.

## Owner-decision options

### `R002-A` -- reproduce Pi's `coding-agent`-layer (uncaught) malformed-URL failure semantics

**Mechanism (this lane's own finding, not previously identified)**: this does **not** require
modifying Layer 12. Layer 13's shared path pipeline (`TOOL-026`) can add its own explicit,
strict `file://` URL pre-validation step -- mirroring `utils/paths.ts`'s unguarded
`fileURLToPath` call exactly -- that runs BEFORE handing the (now-guaranteed-well-formed-or-
not-a-`file://`-URL) string to `ctx.fs`. A malformed `file://` URL would then be rejected by
Layer 13 itself, with a Layer-13-defined error, before ever reaching Layer 12's own (unchanged,
still-catching) `resolve_local_path`. Layer 12's existing seam, and every other input class that
does not begin with `file://`, is completely unaffected.

```text
Pi parity status:            exact (same class of failure -- "this URL does not
                              parse" -- surfaced distinctly from "this path does
                              not exist"), though the EXACT exception text/type
                              would still need its own disposition (see R010,
                              Lane E) since Pi's own raw JS exception text is not
                              itself a stable contract (see R010's own findings)
Layer-12 impact:              NONE -- Layer 13 adds its own pre-check; Layer 12's
                              resolve_local_path is not modified, not reopened
Python/Rust implementability: straightforward -- a small, explicit
                              "file://"-prefix + URL-well-formedness pre-check,
                              independently written per language, raising a
                              Layer-13-defined error rather than falling through
Public error/result difference: a malformed file:// path becomes its own
                              distinguishable error class (e.g. "invalid file
                              URL"), separate from "not found" -- a NEW
                              distinguishable outcome Layer 13 did not have
                              before
Manifest disposition:         adopted, once the exact Layer-13 error shape is
                              settled (depends on Lane E/R010)
```

### `R002-B` -- accept the Layer-12-backed operational-error semantics as-is

```text
Pi parity status:            divergent -- a malformed file:// URL and a
                              genuinely nonexistent ordinary path become
                              observably indistinguishable (both surface as
                              "not found"), where Pi's own coding-agent tools
                              distinguish them (a URL-parse exception vs. a
                              filesystem access failure)
Layer-12 impact:              NONE -- no change; already-certified behavior
                              consumed exactly as-is
Python/Rust implementability: none needed -- this is the CURRENT behavior of
                              both the Lane-A-unaffected pipeline and any
                              already-drafted TOOL-026 text; zero additional
                              implementation work
Public error/result difference: a malformed file:// URL is indistinguishable
                              from "file not found" -- the model/caller cannot
                              tell "you typed a broken URL" from "that file
                              genuinely does not exist"
Manifest disposition:         intentional divergence, with this exact
                              consequence disclosed explicitly (as this lane's
                              own artifact already does)
```

No third option is identified in this lane -- unlike `R005` (where a shared-but-non-Pi engine was
a meaningful third path), there is no analogous "consistent-but-different-from-both" option here:
the only two observably distinct behaviors are "surface a distinguishable parse error" (`A`) or
"don't" (`B`); a Layer-13-only pre-check versus a Layer-12 catch-removal are not two different
OBSERVABLE options, they are two different MECHANISMS for achieving the same observable outcome
(`A`) -- and this lane already identifies the lower-cost mechanism (no Layer 12 change needed) as
the one worth recording, rather than presenting a mechanism choice as if it were a second
observable option.

No option is selected here.

## Lane-B status

```text
R002:  OWNER_DECISION_REQUIRED
```
