# Layer 13 built-in tools — independent Rust-side scope re-review

Mode: targeted independent scope re-review only. No Python or Rust implementation was
authorized or performed.

## Exact review target

```text
coordination issue: EGAILab/minion-agent#47
candidate PR:       EGAILab/minion-agent-docs#124
candidate SHA:      538d2bf3b57b1206404643b2d52c2a52512a875e
candidate base:     ec36ed92a9a57f5fc8db4f76103a2d202cb82cbc
candidate artifact: assurance/layers/13-built-in-tools-scoping-v2.md
prior review PR:    EGAILab/minion-agent-docs#125
prior review SHA:   8aa47e478dc91e029420ae0ce34df041acd5a668
code baseline:      92aa4be168dc82111832467922089206e858a9c4
pinned Pi:          b7bb00b936dbe21b8e160b3e89efdec361846699
```

The candidate and prior review heads were fetched from their GitHub pull-request refs and
matched issue #47. PR #124 was open, Ready for Review, mergeable, unmerged, and
remote-reachable. The issue was open, assigned `NEXT_OWNER = Codex`, named this exact candidate,
and continued to state that implementation is not authorized.

## Authority and targeted audit

The re-review used pinned Pi first, then the proposed revision, the current parity-manifest
namespace, and the prior finding text. The specific Pi sources rechecked at the pin included
`utils/tools-manager.ts`, `utils/shell.ts`, `core/tools/file-mutation-queue.ts`, and the affected
`read.ts`, `grep.ts`, `find.ts`, and `ls.ts` behaviors. Python was not used as a semantic oracle.

## Finding closure ledger

### L13-S001 — external search-engine acquisition matrix

**Result: RESOLVED.** Revision 2 now records the actual precedence: Pi-managed cached binary,
system `PATH`, then download; downloads normally follow the latest GitHub release, with the
specific `fd` Darwin-x64 `10.3.0` exception. The resulting conclusion is also properly narrow:
pinned Pi supplies no universal cross-installation engine version.

### L13-S002 — incomplete Pi audit and observable inaccuracies

**Result: PARTIALLY_RESOLVED_BLOCKING.** The four concrete inaccuracies from the prior review are
corrected: a successful image read retains the image block; grep constructs context itself after
the match stream; fd delegation is scoped to find's default implementation; and the omitted ls
ordering/suffix/stat-skip/empty rules are recorded.

The shell-audit part is not closed. Revision 2 first says `utils/shell.ts:getShellConfig` was read,
but later says the Unix fallback chain was “not re-verified line-by-line” and leaves it as an open
item. It nevertheless proposes `TOOL-034` as covering shell-selection order. Pinned
`getShellConfig` is short and unambiguous: after an optional valid explicit path, Windows checks
the two Git-Bash locations then `where bash.exe`; Unix checks `/bin/bash`, then the first result of
`which bash`, then returns `sh -c`. A scope artifact cannot claim audit completion and propose a
selection-order requirement while expressly leaving part of that order unaudited.

**Minimal correction:** record the complete Unix fallback chain (and remove the contradictory
open-item statement). This is documentary/source-audit remediation only; it does not require
implementation or a Layer 12 change.

### L13-S003 — mutation-queue call order and provider scoping

**Result: RESOLVED.** `TOOL-032` now binds target resolution plus per-key tail insertion into one
globally ordered registration critical section, while leaving actual operations concurrent for
different keys. It also requires provider-scoped queue identity instead of treating a bare opaque
target-key string as a universal namespace. That is sufficient for later language-neutral
contract work and continues to consume, rather than redefine, Layer 12's `resolve()`/`FsTarget`.

### L13-S004 — independently certifiable work-package split

**Result: RESOLVED AS TO THE ORIGINAL FINDING.** Delegated `find`/`grep` are now isolated in
WP-13.4, so their engine-governance decision no longer blocks native `read`/`ls` merely by package
membership. Mutation tools plus their queue remain together, and bash remains separate.

### L13-S005 — requirement-ID collision

**Result: RESOLVED.** The proposed rows move to the currently unused `TOOL-025` through
`TOOL-038` range and preserve all certified existing rows. The current manifest contains
`TOOL-001` through `TOOL-021`, then `TOOL-023` and `TOOL-024`; revision 2 appropriately does not
assume the `TOOL-022` gap is available.

## New consistency findings

### L13-S006 — WP-13.1 is called unblocked while it contains an unresolved owner decision

**Classification:** `CONTRACT_ASSURANCE_DEFECT`

Revision 2 calls WP-13.1 (`read`/`ls`) “genuinely unblocked” and says it can close first, but its
own `TOOL-027` still says the read tool's macOS filename-fallback behavior needs an owner
`adopt / drop` disposition. The unchanged revision-1 open-questions section likewise says that
decision is unresolved. The package split itself is structurally sound, but its readiness state
is not: a work package containing a governance-dependent unresolved disposition is not currently
unblocked for implementation/certification.

**Minimal correction:** either obtain and record valid owner provenance for `TOOL-027`, or mark
WP-13.1 as governance-blocked on that narrow decision while retaining the four-package split.
Do not infer a disposition from the scoping recommendation.

### L13-S007 — the proposed requirement inventory contradicts its own count

**Classification:** `CONTRACT_ASSURANCE_DEFECT`

The proposal enumerates `TOOL-025` through `TOOL-038`, which is 14 rows, then states that the set
has “15 entries, same count as revision 1.” Revision 1 actually had 15 proposed subjects, while
revision 2 consolidates some of them without explaining whether the consolidation is intentional.
This leaves the exact proposed inventory ambiguous: either one subject was accidentally omitted
or the stated count/history is wrong.

**Minimal correction:** state the intended count accurately and, if 14 is intentional, briefly
identify the deliberate consolidation so the requirement inventory is auditable. If a subject was
omitted, restore it with a non-colliding ID instead.

## Layer 12 boundary

```text
Layer 12 boundary: CLEAR
Layer 12 reopen required: NO
```

None of the remaining defects changes the certified filesystem, target-key, execution-world, or
subprocess contracts. They are Layer 13 scoping/assurance issues.

## Formal verdict

```text
LAYER 13 SCOPE
    CHANGES REQUIRED

WORK-PACKAGE SPLIT
    CHANGES REQUIRED

REQUIREMENT SET
    CHANGES REQUIRED

LAYER-12 BOUNDARY
    CLEAR

IMPLEMENTATION AUTHORIZED
    NO
```

Required next action is narrow scoping remediation only: close the remaining shell-audit gap,
make WP-13.1's governance dependency explicit or resolve it with valid owner provenance, and
reconcile the requirement inventory/count. Do not implement Python or Rust Layer 13.
