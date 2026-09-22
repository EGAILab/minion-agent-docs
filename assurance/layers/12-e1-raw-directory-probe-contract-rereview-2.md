# WP-12.E1 independent Rust contract re-review 2

## Verdict

```text
WP-12.E1 shared contract
    REJECTED

Python WP-12.E1
    NOT_IMPLEMENTED

Rust WP-12.E1
    BLOCKED

Existing Layer-12 certification
    UNCHANGED

WP-13.1 Lane E
    NOT REVIEWED / UNCHANGED
```

The refined `WP12E1-R003` semantic defect is resolved. One narrow current-state/provenance defect
introduced by revision 3 must be corrected before implementation authorization.

## Exact review target

| Item | Exact state |
|---|---|
| Coordination | `EGAILab/minion-agent#53` |
| Manifest PR | `EGAILab/minion-agent#54` @ `30d534636665932b7e0f804ff498ac65fc3f5c18` (unchanged) |
| Docs PR | `EGAILab/minion-agent-docs#147` @ `7d3f96370811071056dd9611b7f953199d325b85` |
| Revision-2 rejection | `EGAILab/minion-agent-docs#149` @ `1abeed5863a81452d4ff2e2340586569622ab2e6` |
| Pinned Pi | `b7bb00b936dbe21b8e160b3e89efdec361846699` |

Both candidate PRs were open, Ready for Review, mergeable, and their exact heads were fetched and
verified before review. This review applies only to the two candidate SHAs above.

## Refined R003 recheck

**Result: RESOLVED.** Revision 3 now requires ordinary Layer-12 path resolution before
classification and returns the resolved addressed-entry path and its basename. It preserves the
separate, correct rule that following a symlink for kind classification never substitutes the
target object's identity. The new relative-path witness distinguishes the corrected rule from the
revision-2 raw-input rule.

This agrees with:

- pinned Pi `NodeExecutionEnv.fileInfo`: `resolvePath(cwd, input)` precedes `fileInfoFromStats`;
- normative `spec/execution.md` section 3.2: paths passed to any `ctx.fs` operation use the shared
  resolution rules;
- certified Python: `file_info` resolves before `_file_info_sync` constructs `FileInfo`;
- certified Rust: `file_info` calls `info_for(self.resolved(path))`.

No semantic blocker remains in the actual `DirEntryProbe.path` rule.

## Blocking finding

### WP12E1-R006 — revision-3 provenance and authority text is false/stale

**Classification:** `CONTRACT_ASSURANCE_DEFECT`

**Affected text:** revision-3 additions in `spec/execution.md` sections 11 and 11.4, plus their
review references in the new witness heading.

Revision 3 repeatedly calls the refined finding “`minion-agent-docs#148`'s refined
`WP12E1-R003`” and says Codex reached a usage limit before durably recording it. That is no longer
the project history and was never the content of PR #148:

- PR #148 is the first review; its R003 says `name`/`path` were undefined.
- PR #149 @ `1abeed5863a81452d4ff2e2340586569622ab2e6` is the durable second review; its refined R003
  identifies the raw-input-versus-resolved-`FileInfo.path` contradiction.

The revision-3 normative paragraph additionally says the operation resolves via Python's concrete
`resolve_local_path`. That function is valid secondary implementation evidence, but it is not the
language-neutral authority Rust implements. The binding rule is the already-certified Layer-12
resolution contract in section 3.2 (derived from pinned Pi's `resolvePath`).

Minimal correction:

1. cite PR #149, not #148, for the refined R003 finding;
2. remove the stale claim that no durable Codex record exists;
3. state the normative operation in language-neutral terms: apply section 3.2's certified path
   resolution before classification; retain Python's function only as optional implementation
   evidence, not as the shared mechanism Rust must reuse; and
4. update every revision-3 heading/paragraph carrying the stale #148 attribution.

No behavioral redesign, manifest change, implementation, or new witness is required. The existing
relative-path witness already discriminates the corrected semantic rule.

## Prior finding ledger

| Finding | Result at revision 3 |
|---|---|
| `WP12E1-R001` | CLOSED |
| `WP12E1-R002` | CLOSED |
| `WP12E1-R003` | RESOLVED |
| `WP12E1-R004` | CLOSED |
| `WP12E1-R005` | CLOSED |
| `WP12E1-R006` | OPEN — documentary/provenance only |

## Findings by taxonomy

```text
PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    none

CONTRACT_ASSURANCE_DEFECT
    WP12E1-R006 -- false review provenance and Python-specific authority wording

PARITY_NEUTRAL_HARDENING
    none

PARITY_CONSTRAINED_RISK
    none
```

## Next action

Apply only the four documentary corrections under `WP12E1-R006`, then request exact-SHA targeted
closure review. Do not change the now-correct `DirEntryProbe` behavior, do not implement Python or
Rust, do not alter existing Layer-12 operations, do not touch WP-13.1 Lane E, and do not start
Layer 14.
