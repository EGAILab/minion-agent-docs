# CE-L13-WP131-01 — Lane B revision 3: `R002` one-sentence correction

Mode: §11.8 sub-checkpoint characterization, Lane B, `R002` revision only. **No Python or Rust
implementation performed or authorized. No Layer 12 production change. Review this revision only
-- `R003`/`R004`/`R008` remain frozen `CHECKPOINT-READY` and `R005` remains
`OWNER_DECISION_RESOLVED (R005-A)`; do not reopen any of them unless this revision presents
concrete contradictory evidence.**

Targeted remediation of the independent Lane B re-review (`minion-agent-docs#139` @
`43014fdbcef682a5d813d333e3eecca4946d100e`, verdict `R002 CHARACTERIZATION REJECTED`, one
documentary blocker) against Lane B revision 2 (`minion-agent-docs#132` @
`225d195171aea8112da355e0d6e2d98a8846eaf4`). The re-review independently confirmed both of
revision 2's substantive corrections accurate -- including, notably, directly reproducing the
POSIX side itself (Linux/WSL: `FileNotFoundError`/`ENOENT` -> `FsErrorCode.NOT_FOUND`), which
revision 2 had only reasoned through without direct testing. The sole defect was a literal,
internal self-contradiction: revision 2's own mapping explanation correctly derived `EINVAL ->
FsErrorCode.INVALID`, then immediately stated the opposite conclusion in the next sentence -- a
leftover from an earlier draft that was never updated when the surrounding text was corrected.

## The fix

Revision 2, `Correction 1`'s mapping paragraph ended:

```text
...explicit `exc.errno == errno.EINVAL` check (line 105) ->
FsErrorCode.INVALID. CONFIRMED: NOT_FOUND, not INVALID.
```

The final sentence directly contradicts the derivation immediately preceding it. Corrected to:

```text
...explicit `exc.errno == errno.EINVAL` check (line 105) ->
FsErrorCode.INVALID. CONFIRMED: INVALID, not NOT_FOUND.
```

No other change to revision 2's substance.

## Platform-dependence claim upgraded from reasoned to independently confirmed

Revision 2's POSIX claim was explicitly flagged as "reasoned, not directly re-verified... in this
session." The independent re-reviewer performed that verification directly (Linux/WSL, the exact
retained literal fall-through path, this same class of witness) and confirmed:
`FileNotFoundError`/`ENOENT` -> `FsErrorCode.NOT_FOUND` on POSIX, for the identical malformed
input that produces `EINVAL`/`FsErrorCode.INVALID` on Windows. The platform-dependence claim is
therefore now independently confirmed on both platforms, not reasoned-through on one side only.

## Corrected characterization summary

```text
R002-B's real consequence: CONFIRMED platform-dependent --
  Windows: EINVAL -> FsErrorCode.INVALID (verified directly, this lane)
  POSIX:   ENOENT -> FsErrorCode.NOT_FOUND (independently verified by the
           Lane-B reviewer on Linux/WSL, minion-agent-docs#139)
  -- not a single stable "indistinguishable from missing file" claim.

R002-A's mechanism: reuse _file_url_to_path directly (unwrapped), not a
  new independent parser -- requires only a visibility change to an
  already-certified, unmodified Layer-12 function. (Unchanged from
  revision 2; independently confirmed as the correct architectural
  direction by the Lane-B reviewer.)
```

Both `R002-A`/`R002-B` remain the complete, exhaustive set of genuinely distinct observable
options (independently reconfirmed by the reviewer this round: "Parser placement/visibility is a
mechanism, not a third semantic option").

## Lane-B status (this revision)

```text
R002:  OWNER_DECISION_REQUIRED
```
