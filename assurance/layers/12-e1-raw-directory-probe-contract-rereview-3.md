# WP-12.E1 independent Rust contract re-review 3

## Verdict

```text
WP-12.E1 shared contract
    APPROVED

Python WP-12.E1
    NOT_IMPLEMENTED

Rust WP-12.E1
    NOT_IMPLEMENTED

Existing Layer-12 certification
    UNCHANGED

WP-13.1 Lane E
    NOT REVIEWED / UNCHANGED
```

This approval authorizes no implementation. Per coordination issue #53, the next step is an
explicit owner decision on implementation authorization.

## Exact review target

| Item | Exact state |
|---|---|
| Coordination | `EGAILab/minion-agent#53`, `NEXT_OWNER = Codex` |
| Manifest PR | `EGAILab/minion-agent#54` @ `30d534636665932b7e0f804ff498ac65fc3f5c18` |
| Docs PR | `EGAILab/minion-agent-docs#147` @ `8bf1c7afb22ddd5629274e3f2580f355f7f3d0f8` |
| Prior revision-3 review | `EGAILab/minion-agent-docs#150` @ `eb01d9acc67142eeabf086c7278fc9078ebbf0ad` |
| Pinned Pi | `b7bb00b936dbe21b8e160b3e89efdec361846699` |

Both candidate PRs were open, Ready for Review, and their exact heads matched issue #53. The
candidate is not marked as derived from a quarantined artifact. Review applies only to these exact
SHAs.

## Targeted WP12E1-R006 closure

All four requested documentary corrections are present:

1. every revision-3 attribution for refined `WP12E1-R003` now cites review PR #149, not #148;
2. the stale statement that no durable Codex review existed is removed;
3. the normative rule now requires the language-neutral, already-certified section 3.2 path
   resolution before classification; Python's `resolve_local_path` is explicitly illustrative
   implementation evidence only, and Rust remains free to use its certified native mechanism; and
4. the revision summary, section-11.4 paragraph, and relative-path witness heading all carry the
   corrected attribution.

The diff from revision 3 is documentation-only and does not alter the resolved behavior:
`DirEntryProbe.path` is the resolved addressed-entry path, `name` is its basename, and
symlink-following classification never substitutes the target object's identity.

**WP12E1-R006: CLOSED.**

## Complete finding ledger

| Finding | Final result |
|---|---|
| `WP12E1-R001` | CLOSED |
| `WP12E1-R002` | CLOSED |
| `WP12E1-R003` | RESOLVED |
| `WP12E1-R004` | CLOSED |
| `WP12E1-R005` | CLOSED |
| `WP12E1-R006` | CLOSED |

## Contract-quality result

- The public operation inventory and manifest requirement agree.
- `list_dir_raw` owns raw provider-order enumeration and performs no per-entry probing.
- `probe_dir_entry` owns one addressed-entry classification with explicit symlink-following kinds
  and per-call errors.
- Layer 13 owns sorting, skip-on-probe-error, cap-before-next-probe, and its outer abort behavior.
- Cancellation is explicitly a Minion architectural mapping rather than falsely attributed to a
  single Pi interface.
- Existing `list_dir`, `file_info`, `FileInfo`, and `FileKind` semantics remain unchanged.
- The witness plan is discriminating and covers every identified extension boundary.
- Rust can implement the contract using its certified Layer-12 path/error/cancellation types without
  reading or copying Python mechanics.

## Findings by taxonomy

```text
PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    none

CONTRACT_ASSURANCE_DEFECT
    none

PARITY_NEUTRAL_HARDENING
    none

PARITY_CONSTRAINED_RISK
    none
```

## Formal approval

```text
WP-12.E1 contract at:
    minion-agent#54 @ 30d534636665932b7e0f804ff498ac65fc3f5c18
    minion-agent-docs#147 @ 8bf1c7afb22ddd5629274e3f2580f355f7f3d0f8

is APPROVED as a contract-first additive Layer-12 extension.
```

This does not certify either implementation, merge either candidate, authorize Python/Rust work,
modify WP-13.1 Lane E, or start Layer 14.
