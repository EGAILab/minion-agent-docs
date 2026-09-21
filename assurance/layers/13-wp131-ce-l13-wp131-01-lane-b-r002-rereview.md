# CE-L13-WP131-01 Lane B R002 independent re-review

**Mode:** convergence sub-checkpoint re-review only. No Python or Rust implementation was
performed or authorized. No Layer-12 or Layer-14 work was performed.

## Exact target

```text
coordination issue:  EGAILab/minion-agent#48
status:              CONTRACT_CONVERGENCE
next owner:          Codex
docs PR:             EGAILab/minion-agent-docs#132
docs head:           225d195171aea8112da355e0d6e2d98a8846eaf4
manifest PR:         EGAILab/minion-agent#52
manifest head:       cca8d8b325bb159be549e10c8321b3468f043e7f (frozen)
docs base:           master @ 0bbd737fab8c1360995f4efff2b41c1c5531a9c3
code base:           main @ 92aa4be168dc82111832467922089206e858a9c4
pinned Pi:           b7bb00b936dbe21b8e160b3e89efdec361846699
episode:             CE-L13-WP131-01
artifact:            assurance/layers/13-wp131-ce-l13-wp131-01-r002-path-errors-v2.md
scope:               R002 revision 2 only (Lane B)
prior review:        minion-agent-docs#138 @
                     294bc60132ea3b24f7cd8f32ae7547c559ec5d40
```

The issue-recorded heads matched the open remote PR heads and were remote-reachable. The issue
carried valid governance provenance, and the candidate was not derived from quarantined work.
R003/R004/R008 and resolved R005-A were not reopened.

## Result

```text
R002 CHARACTERIZATION:  REJECTED
OWNER DECISION READY:   NO
IMPLEMENTATION:         NOT AUTHORIZED
```

## Closure ledger

### L13-WP131-R002-B1 — still open (`CONTRACT_ASSURANCE_DEFECT`)

The substantive correction is accurate:

- a direct Windows operation on the retained `file:` path raises `OSError`/`EINVAL`;
- `to_fs_error` maps that to `FsErrorCode.INVALID`;
- an ordinary missing path maps to `FsErrorCode.NOT_FOUND`;
- a direct Linux/WSL operation on the same retained literal path produced
  `FileNotFoundError`/`ENOENT`, independently confirming the proposed POSIX side rather than merely
  relying on the candidate's explicitly labelled reasoning.

But the artifact contradicts that result inside its own authoritative mapping block. Immediately
after explaining `EINVAL -> FsErrorCode.INVALID`, it states:

```text
CONFIRMED: NOT_FOUND, not INVALID.
```

This reverses the very correction the rest of the document makes. A reader implementing or
presenting the owner choice from this checkpoint can select either result from current prose.
The summary later says `Windows: INVALID`, but a later summary does not erase an earlier explicit
and contradictory confirmation.

Required correction: change that sentence to `CONFIRMED: INVALID, not NOT_FOUND.` No behavior,
option, or source change is required. Retain the platform-dependent matrix.

### L13-WP131-R002-B2 — resolved

Revision 2 now identifies the already-characterized strict file-URL conversion as the authority,
rather than proposing a fresh parser. This is the correct architectural direction:

- no Layer-12 observable semantic reopening is required;
- Python can expose or wrap the existing `_file_url_to_path` conversion;
- Rust can expose the existing conversion boundary and map its `None` failure to the later
  Layer-13 error form;
- R010 remains the owner of that surfaced error projection, so the artifact no longer calls the
  outcome fully exact prematurely.

The languages need not share the same failure-return mechanism (Python exception versus Rust
`Option`) so long as they reuse the same certified success/failure boundary. The revision is
sufficiently language-neutral on that point.

## Option-set and source recheck

Pinned Pi still has the two distinct resolver policies described by the candidate: coding-agent's
unguarded `fileURLToPath` and harness `resolvePath`'s catch-and-fall-through behavior. The proposed
A/B split remains a reasonable exhaustive policy choice: preserve a URL-parse-specific failure or
accept Layer-12 fall-through. Parser placement/visibility is a mechanism, not a third semantic
option.

Once the contradictory sentence is corrected, the R002 characterization will be ready for owner
choice. It is not ready at the exact reviewed SHA because governance must not rely on a document
that explicitly confirms both opposite error codes.

## Verdict and next action

```text
R002:                      CHARACTERIZATION REJECTED
Lane B:                    ONE DOCUMENTARY BLOCKER REMAINS
Implementation authorized:NO
Python WP-13.1:            NOT_IMPLEMENTED / NOT AUTHORIZED
Rust WP-13.1:              NOT_IMPLEMENTED / BLOCKED
Layer 13 cross-language:   NOT CLOSED
Layer 14:                  NOT STARTED
```

Return only the one-sentence correction to the shared-contract owner. Preserve all other Lane-B
revision-2 content and all frozen/resolved findings. Any changed candidate SHA requires another
Lane-B-only exact-SHA re-review before owner governance.
