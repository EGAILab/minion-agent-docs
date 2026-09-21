# Layer 13 built-in tools — second independent Rust-side scope re-review

Mode: targeted independent scope re-review only. No Python or Rust implementation was
authorized or performed.

## Exact review target

```text
coordination issue: EGAILab/minion-agent#47
candidate PR:       EGAILab/minion-agent-docs#124
candidate SHA:      7a26c635923253e563d2a6b929d1c0b865c2d20f
candidate base:     ec36ed92a9a57f5fc8db4f76103a2d202cb82cbc
candidate artifact: assurance/layers/13-built-in-tools-scoping-v3.md
prior review PR:    EGAILab/minion-agent-docs#126
prior review SHA:   e63c4163bb4841a3a6891360edda117aada5ce97
code baseline:      92aa4be168dc82111832467922089206e858a9c4
pinned Pi:          b7bb00b936dbe21b8e160b3e89efdec361846699
```

The candidate head was fetched from GitHub and matched issue #47. PR #124 was open, Ready for
Review, unmerged, and remote-reachable. The issue was open, assigned `NEXT_OWNER = Codex`, named
this exact SHA, and explicitly continued to withhold implementation authorization.

## Targeted closure results

### L13-S002 — shell-selection audit remainder

**Result: STILL OPEN (`CONTRACT_ASSURANCE_DEFECT`).** Revision 3 now records the complete Unix
fallback order correctly: `/bin/bash`, then the first `which bash` result, then silent fallback
to `sh -c`. The previous unaudited hedge is gone.

One newly-added statement in the same “complete resolution order” remains contrary to pinned
`utils/shell.ts:getShellConfig`. Revision 3 says a caller-supplied shell path that does not exist
causes “a hard error listing the searched Git Bash locations and setup options.” That detailed
error belongs only to the Windows no-shell-found branch after all automatic locations fail. The
explicit-path branch immediately throws exactly:

```text
Custom shell path not found: <customShellPath>
```

It does not list automatic locations or setup options. This distinction is observable error
behavior on the very selection surface `TOOL-034` proposes to cover.

**Minimal semantic correction:** separate the explicit-path failure from the Windows automatic-
search exhaustion failure and record each source behavior accurately. No implementation or lower-
layer change is needed.

### L13-S006 — WP-13.1 readiness

**Result: RESOLVED.** Revision 3 no longer calls WP-13.1 unblocked. It accurately marks the
package narrowly governance-blocked on the unresolved `TOOL-027` adopt/drop decision, without
inventing owner provenance or disturbing the already-correct four-package structure.

### L13-S007 — requirement inventory/count

**Result: RESOLVED.** Revision 3 accurately states that `TOOL-025` through `TOOL-038` is 14 rows
and explains the deliberate consolidation of revision 1's edit fuzzy-match and BOM/line-ending
subjects into `TOOL-031`. The row's written scope already covers both subjects, so no omission is
left.

## Mandatory convergence trigger

The same material L13-S002 source-audit finding remained open in the original review and in the
first re-review, so workflow §11.8 trigger A has fired: the same finding survived two independent
reviews before this round. Revision 3 did not record the mandatory trigger check or a justified
exception and introduced another error on the same shell-selection/error surface.

The next pass must therefore enter `CONTRACT_CONVERGENCE` for L13-S002 rather than continue an
untracked ordinary point-fix cycle. The convergence surface is narrow:

```text
root cause surface:
    pinned Pi getShellConfig selection, transport, and distinguishable failures

minimum matrix:
    explicit path exists / missing
    Windows Git Bash first location / second location / PATH / exhausted
    Unix /bin/bash / PATH bash / sh fallback
    argv transport / legacy-WSL stdin transport
    exact branch-specific failure behavior
```

The characterization/checkpoint remains documentary and source-derived. It does not authorize
Layer 13 implementation.

## Regression check

No change in revision 3 regresses the previously closed acquisition-matrix, mutation-queue,
work-package-separation, or requirement-ID findings. Layer 12 remains a sufficient dependency and
requires no reopen.

## Formal verdict

```text
LAYER 13 SCOPE
    CHANGES REQUIRED

WORK-PACKAGE SPLIT
    APPROVED

REQUIREMENT SET
    CHANGES REQUIRED

LAYER-12 BOUNDARY
    CLEAR

IMPLEMENTATION AUTHORIZED
    NO
```

Next action: enter `CONTRACT_CONVERGENCE`, characterize and checkpoint the complete
`getShellConfig` matrix, correct the explicit-path error statement, and return the exact docs
candidate for targeted closure. Do not implement Python or Rust Layer 13.
