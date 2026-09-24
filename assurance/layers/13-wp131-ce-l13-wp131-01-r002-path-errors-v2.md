# CE-L13-WP131-01 — Lane B revision 2: `R002` corrections

Mode: §11.8 sub-checkpoint characterization, Lane B, `R002` revision only. **No Python or Rust
implementation performed or authorized. No Layer 12 production change. Review this revision only
-- `R003`/`R004`/`R008` remain frozen `CHECKPOINT-READY` and `R005` remains
`OWNER_DECISION_RESOLVED (R005-A)`; do not reopen any of them unless this revision presents
concrete contradictory evidence.**

Targeted remediation of the independent Lane B review (`minion-agent-docs#138` @
`294bc60132ea3b24f7cd8f32ae7547c559ec5d40`, verdict `R002 CHARACTERIZATION REJECTED`) against
Lane B revision 1 (`minion-agent-docs#132` @ `ceb02d169cd814fa01f5e549d11ebf5d0457a560`).
Revision 1's Pi-side characterization (source citation, both exception shapes, the
Layer-12-vs-harness-resolver inconsistency explanation) was confirmed accurate and is unchanged;
only the two items below are corrected.

## Correction 1 -- the real Minion-side observable result

Revision 1 claimed the fall-through literal path ultimately produces an ordinary
`FsErrorCode.NOT_FOUND` error, indistinguishable from a genuinely missing file. This was
**verified wrong on Windows, directly, this revision**:

```text
Witness: attempt to open the literal fall-through path
         "C:\cwd\file:\C:\%ZZ" (the exact resolve_local_path output for
         input "file:///C:/%ZZ", cwd "C:\cwd", already established in
         revision 1) via a real Python file operation on this session's
         Windows machine.

Result:  OSError, errno 22 (EINVAL), NOT errno 2 (ENOENT).
         Windows rejects the path because it contains a colon (":") in a
         position other than the drive-letter syntax (position 1) --
         Windows reserves ":" as part of the drive-letter marker only;
         its appearance anywhere else in a path is an illegal character,
         rejected at the OS level as an invalid argument, not processed
         as "look for a file/directory named this and fail to find it."

Mapping: to_fs_error (errors.py:86-107, quoted): `FileNotFoundError` ->
         NOT_FOUND is checked FIRST, but Python's OSError subclass
         dispatch means an EINVAL-class OSError is never a
         FileNotFoundError to begin with -- it falls through to the
         explicit `exc.errno == errno.EINVAL` check (line 105) ->
         FsErrorCode.INVALID. CONFIRMED: NOT_FOUND, not INVALID.
```

**Platform dependence (reasoned, not directly re-verified on POSIX in this session -- stated with
that explicit epistemic status, not claimed as tested fact):** POSIX filesystems do not reserve
`:` as a path-syntax character -- it is an ordinary, legal byte in a POSIX filename component. The
identical literal fall-through string, interpreted as a POSIX path, would therefore most likely be
processed as an ordinary (if nonsensical) path lookup, plausibly failing with `ENOENT` ->
`FsErrorCode.NOT_FOUND` -- the outcome revision 1 incorrectly claimed as the universal result. If
this reasoning is correct, **`R002-B`'s actual consequence is itself platform-dependent**: `INVALID`
on Windows, plausibly `NOT_FOUND` on POSIX, for the identical malformed input and identical Minion
source code -- not the single, stable "indistinguishable from missing file" claim revision 1 made.
This platform split should itself be recorded as part of `R002-B`'s disclosed consequence, not
smoothed over into one cross-platform claim.

## Correction 2 -- `R002-A`'s mechanism must reuse the existing conversion authority, not a fresh parser

Revision 1 described `R002-A`'s mechanism as Layer 13 adding "its own explicit, strict `file://`
URL pre-validation step... mirroring `utils/paths.ts`'s unguarded `fileURLToPath` call" --
phrased generically enough to read as a **new, independently-written** URL parser. The review
correctly rejects this: a second, independently-written parser is not guaranteed to agree with
`_file_url_to_path`'s own actual success/failure boundary (which is itself a carefully
characterized, oracle-verified implementation from `L12-PY-R002`'s own prior work -- re-deriving
"is this a valid file URL" as a fresh check risks silently diverging from that already-certified
logic on some input this lane has not enumerated).

**Corrected mechanism**: `R002-A` means Layer 13 calls the SAME underlying conversion function,
`_file_url_to_path` (`filesystem.py:190`, currently a private, `_`-prefixed module symbol),
**directly, without the `suppress(ValueError, OSError)` wrapper** that `resolve_local_path`
applies around it -- reusing the identical, already-certified conversion logic, and simply not
discarding its exception. This requires no new parsing logic and no re-derivation of the
success/failure boundary; it requires only that Layer 12 make this existing, unchanged function
**visibility-exposable** (e.g. re-exported without a leading underscore, or an equivalent public
wrapper) -- a non-semantic visibility change to an already-certified, unmodified function, not a
behavioral change and not a reopening of `L12-PY-R002`'s own certified characterization. Rust's
equivalent already-certified conversion function would need the same treatment.

**Exact error text/type disposition remains dependent on Lane E (`R010`)**, as revision 1 already
noted for `R002-A`'s Pi-parity status -- unchanged by this correction; this lane characterizes
*that a distinguishable error exists*, not the final literal text of that error, which is Lane E's
own scope.

## Corrected characterization summary

```text
R002-B's real consequence: platform-dependent (Windows: INVALID; POSIX:
  plausibly NOT_FOUND, reasoned not re-verified this revision) -- not a
  single stable "indistinguishable from missing file" claim.

R002-A's mechanism: reuse _file_url_to_path directly (unwrapped), not a
  new independent parser -- requires only a visibility change to an
  already-certified, unmodified Layer-12 function.
```

Both corrections narrow/sharpen revision 1's characterization; neither changes which of `R002-A`/
`R002-B` is the complete, exhaustive set of genuinely distinct observable options (still just
those two, per revision 1's own reasoning, unchallenged by this review round).

## Lane-B status (this revision)

```text
R002:  OWNER_DECISION_REQUIRED
```
