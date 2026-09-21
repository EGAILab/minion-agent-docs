# CE-L13-WP131-01 Lane B R002 independent review

**Mode:** convergence sub-checkpoint review only. No Python or Rust implementation was performed
or authorized. No Layer-12 or Layer-14 work was performed.

## Exact target

```text
coordination issue:  EGAILab/minion-agent#48
status:              CONTRACT_CONVERGENCE
next owner:          Codex
docs PR:             EGAILab/minion-agent-docs#132
docs head:           ceb02d169cd814fa01f5e549d11ebf5d0457a560
manifest PR:         EGAILab/minion-agent#52
manifest head:       cca8d8b325bb159be549e10c8321b3468f043e7f (frozen)
docs base:           master @ 0bbd737fab8c1360995f4efff2b41c1c5531a9c3
code base:           main @ 92aa4be168dc82111832467922089206e858a9c4
pinned Pi:           b7bb00b936dbe21b8e160b3e89efdec361846699
episode:             CE-L13-WP131-01
artifact:            assurance/layers/13-wp131-ce-l13-wp131-01-r002-path-errors.md
scope:               R002 only (Lane B)
```

The issue-recorded heads matched the open, Ready-for-Review remote PR heads and were
remote-reachable. The issue carried valid governance provenance for the lane-isolated review and
for the already-resolved R005-A choice. The candidate was not derived from quarantined work.
R003/R004/R008 and R005 were not reopened.

The review independently read pinned Pi's `packages/coding-agent/src/utils/paths.ts`,
`core/tools/path-utils.ts`, `read.ts`, `ls.ts`, and
`packages/agent/src/harness/env/nodejs.ts`; executed Node's `fileURLToPath` on Windows; and invoked
the certified Python Layer-12 resolver and real `LocalFileSystem.read_text_file` seam. The existing
Rust Layer-12 resolver was inspected only after those authorities.

## Requested result

```text
R002 CHARACTERIZATION:  REJECTED
OWNER DECISION READY:   NO
IMPLEMENTATION:         NOT AUTHORIZED
```

## Verified Pi behavior

Pinned coding-agent `normalizePath` calls `fileURLToPath` without a guard. `resolveToCwd`, `read`,
and `ls` do not normalize the resulting exception. Direct Windows/Node probes reproduced:

```text
file:///C:/%ZZ      -> URIError("URI malformed"), no code
file:///%ZZ         -> URIError("URI malformed"), no code
file://             -> TypeError("File URL path must be absolute"),
                       code ERR_INVALID_FILE_URL_PATH
file:///C:/valid.txt-> C:\valid.txt
file:///C:/%25      -> C:\%
```

The second exception family is platform-dependent: for example, a drive-less file URL is invalid
under Windows rules but may be a valid absolute POSIX file URL.

The candidate also correctly identifies Pi's separate harness resolver: its `resolvePath` catches
`fileURLToPath` failure and keeps the literal URL for ordinary path resolution. The certified
Layer-12 resolver deliberately follows that catching seam. This is a real pinned-Pi internal
difference, not a contradiction introduced by Minion.

## Blocking findings

### L13-WP131-R002-B1 — `CONTRACT_ASSURANCE_DEFECT`

The artifact's claimed Minion observable result is false on the platform on which it says it was
directly reproduced. It executes only `resolve_local_path`, then infers that the resulting path is
"almost certainly nonexistent" and therefore becomes `FsErrorCode.NOT_FOUND`. On Windows the
retained `file:` component is not merely missing; it is an invalid filesystem path. Invoking the
real certified seam produced:

```text
LocalFileSystem.read_text_file("file:///C:/%ZZ") -> FsErrorCode.INVALID
LocalFileSystem.read_text_file("file:///%ZZ")    -> FsErrorCode.INVALID
LocalFileSystem.read_text_file("file://")        -> FsErrorCode.INVALID
```

The underlying error was Windows `EINVAL` (`[Errno 22] Invalid argument`). A genuinely missing
ordinary path produces `NOT_FOUND`, so the candidate's central R002-B assertion that the two are
observably indistinguishable is not true on Windows. On a POSIX filesystem the retained literal is
normally a legal relative pathname and a missing entry can produce `NOT_FOUND`; the current
Layer-12-backed outcome is therefore itself platform-dependent.

Minimal discriminating witness:

```text
setup:      LocalFileSystem(temp_directory) on Windows
inputs:     "file:///%ZZ" and "ordinary-missing-file"
expected:   characterize the real certified seam without assuming an OS outcome
observed:   malformed URL -> INVALID; ordinary missing path -> NOT_FOUND
why:        disproves both the claimed NOT_FOUND result and claimed indistinguishability
```

Required correction: replace the inferred single Minion result with an actual operation-level,
platform-aware matrix (at least Windows and POSIX) for both `read` and `ls`-class access. Correct
R002-B's consequence and disposition discussion accordingly. The retained literal still loses the
specific *URL-parse* provenance, but it does not always collapse to the same error code as a
missing ordinary file.

### L13-WP131-R002-B2 — `CONTRACT_ASSURANCE_DEFECT`

R002-A overstates its mechanism and parity status. Exact pinned-Pi acceptance/rejection is not a
generic "URL-well-formedness" check: it is the platform-sensitive `fileURLToPath` algorithm. This
project's Layer-12 work required a pinned Ada engine plus a large differential corpus and
fileURLToPath-specific rules to reproduce that boundary in both languages. Independently writing
a new "small" Layer-13 parser would duplicate certified lower-layer semantics and could accept or
reject a different URL set.

The existing implementations already contain a characterized strict conversion helper, but it is
not currently a Layer-13 API: Python's `_file_url_to_path` is private and Rust's
`file_url_to_path` is private to the filesystem module. Thus the accurate mechanism statement is:

- no Layer-12 **observable semantic reopening** is necessary;
- implementation should reuse/refactor the already-characterized strict conversion authority;
- a narrow internal visibility/API delta may be required, or duplication must carry the same
  differential-evidence burden;
- R002-A is not "exact" until Lane E/R010 fixes the surfaced Layer-13 error form. It currently
  preserves the parse-error-versus-operational-error distinction while deferring the exact
  error projection.

Required correction: replace the generic independent pre-parser proposal with a concrete
language-neutral reuse boundary for the certified strict file-URL conversion semantics. State
honestly whether the implementation needs an additive lower-layer visibility seam and keep that
distinct from a Layer-12 semantic change. Remove the present "exact" parity label until R010's
observable error form is settled.

## Option-set assessment

At the intended semantic level, the two choices are a reasonable exhaustive partition:

1. preserve a URL-parse-specific failure distinct from ordinary filesystem access; or
2. accept the certified Layer-12 fall-through and its platform-dependent operational result.

A different internal parser placement is a mechanism, not a third observable policy. Rejecting
valid `file://` inputs as well would be a separate behavior, but it has no identified Pi or Minion
authority and need not be elevated as a viable governance option.

The owner cannot choose responsibly from the current text because R002-B's advertised observable
consequence is wrong and R002-A's advertised mechanism/equivalence is overstated. Once both are
corrected, the A/B policy split can be owner-decision-ready.

## Contract-quality answers

```text
Pinned coding-agent source mapping accurate?             YES
Two Node exception shapes reproduced?                    YES
Harness/coding-agent resolver difference accurate?       YES
Certified Layer-12 fall-through accurately described?    YES, at resolution only
Real Minion operation result accurately described?       NO
R002-B consequence accurate cross-platform?              NO
R002-A needs no Layer-12 semantic reopening?              YES
R002-A needs only a generic small parser?                 NO
Observable A/B policy partition reasonable?              YES
Owner decision ready?                                    NO
```

## Verdict and next action

```text
R002:                      CHARACTERIZATION REJECTED
Lane B:                    CHANGES REQUIRED
Implementation authorized:NO
Python WP-13.1:            NOT_IMPLEMENTED / NOT AUTHORIZED
Rust WP-13.1:              NOT_IMPLEMENTED / BLOCKED
Layer 13 cross-language:   NOT CLOSED
Layer 14:                  NOT STARTED
```

Return only Lane B to the shared-contract owner. Preserve R003/R004/R008 as frozen
`CHECKPOINT-READY` and R005 as `OWNER_DECISION_RESOLVED (R005-A)`. Revise the operation-level
Minion matrix and R002-A mechanism/equivalence language, then request another Lane-B-only review.
