# CE-L13-WP131-01 Lane E — independent R010 revision 2 re-review

## Verdict

```text
R010 CHARACTERIZATION
    REJECTED

OWNER DECISION READY
    NO

Python/Rust Layer 13 implementation
    NOT AUTHORIZED
```

Revision 2 closes the two findings from the first Lane-E review in substance: it presents two
unselected owner options, preserves Pi's stable authored text in both, identifies normalization of
raw/hybrid text as an intentional divergence, and restores the previously omitted ordinary
`FsErrorCode` cases. It is not yet owner-decision ready because option `R010-B` promises a
structured error-code result that the certified cross-language tool boundary cannot currently
produce, and the mapping omits a whole-call `not_supported` result explicitly permitted by the
approved `R007-b` dependency. A smaller documentary count contradiction also remains.

## Exact review target

| Item | Exact state |
|---|---|
| Coordination | `EGAILab/minion-agent#48`, `STATUS = CONTRACT_CONVERGENCE`, `NEXT_OWNER = Codex` |
| Docs PR | `EGAILab/minion-agent-docs#132` @ `b13769cd261c29926ab44d5b1c056bbce4f0ff02` |
| Artifact | `assurance/layers/13-wp131-ce-l13-wp131-01-r010-error-projection.md` |
| Frozen manifest | `EGAILab/minion-agent#52` @ `cca8d8b325bb159be549e10c8321b3468f043e7f` |
| Approved WP-12.E1 contract candidate | `EGAILab/minion-agent-docs#147` @ `8bf1c7afb22ddd5629274e3f2580f355f7f3d0f8` |
| WP-12.E1 approval evidence | `EGAILab/minion-agent-docs#151` @ `f050d81ee81156fa101992b4e2c09298ba766166` |
| Pinned Pi | `b7bb00b936dbe21b8e160b3e89efdec361846699` |

The coordination issue was open and valid; both candidate PR heads were open, Ready for Review,
mergeable, remote-reachable, and exactly matched the issue state. This review is Lane E / R010
only. It does not reopen R006, R007, existing Layer-12 semantics, or WP-12.E1 approval.

## Independent authority audit

Re-read directly, in authority order:

- pinned Pi `packages/coding-agent/src/core/tools/ls.ts:115-176`;
- pinned Pi `packages/coding-agent/src/core/tools/read.ts:225-310`;
- pinned Pi `packages/agent/src/agent-loop.ts::executePreparedToolCall` and
  `createErrorToolResult`;
- certified `spec/tools.md` generated-error and `details` rules;
- certified `spec/execution.md` `FsErrorCode` vocabulary;
- approved WP-12.E1 `spec/execution.md` section 11; and
- existing certified Python and Rust tool-execution public shapes.

Confirmed Pi behavior remains as the candidate states:

- `ls` authors `Path not found: <path>` and `Not a directory: <path>`;
- `ls` wraps `readdir` failure as `Cannot read directory: <underlying message>`;
- its earlier `stat` failure is raw;
- `read` lets `access` and later `readFile` failures remain raw;
- both tools author `Operation aborted`; and
- a rejected tool execution is converted by Pi's `createErrorToolResult`, whose `details` is `{}`.

Revision 2 therefore correctly fixes former `L13-WP131-R010-A` and
`L13-WP131-R010-B`; those two findings are closed. The blockers below are new consequences of
checking the proposed owner options against the actual certified Minion seams.

## Revision-2 closure ledger

| Prior finding | Revision-2 result | Status |
|---|---|---|
| `L13-WP131-R010-A` | Two genuine, unselected owner options now separate Pi-structural preservation from an explicitly governed raw/hybrid-text divergence. | `RESOLVED` |
| `L13-WP131-R010-B` | The ordinary raw/hybrid mapping now includes `not_found`, `permission_denied`, `not_directory`, `invalid`, and `unknown` rather than collapsing to two codes. | `RESOLVED` |

## Blocking findings

### L13-WP131-R010-C — option B requires a structured failure channel the certified tool seam does not expose

**Classification:** `CONTRACT_ASSURANCE_DEFECT`

Option `R010-B` promises that the final tool-level error result carries both its normalized text
and the exact underlying `FsErrorCode` as structured data. That is not currently an independently
implementable cross-language rule:

- pinned Pi's rejected `execute()` path calls `createErrorToolResult`, which fixes `details` to
  `{}`;
- certified `spec/tools.md` section 5 likewise requires generated execution errors to retain
  `details: {}`;
- Python's execution boundary converts a raised tool exception with `text_result(...,
  is_error=True)`, whose details default to `{}`; and
- Rust's public `ExecuteTool` returns `Result<AgentToolResult, ToolCapabilityError>`. The error
  variant carries only a message, and `immediate_error` converts it to a result with empty details.
  Unlike Python's larger internal `ToolResult`, `AgentToolResult` has no `is_error` field through
  which a Layer-13 tool could return its own finalized error while preserving custom details.

The option therefore cannot be implemented in both languages merely by consuming Layer 12. It
either needs a separately reviewed lower-layer/tool-result delta, or it must stop promising that
the final tool error exposes structured `FsErrorCode` and instead state precisely where the cause
is retained internally for message selection.

Minimal discriminating witness:

```text
setup
    a Layer-13 tool calls a filesystem provider which returns
    FsError(code=permission_denied, message=<provider text>)

execution through the certified Rust tool seam
    ToolDefinition.execute -> Err(ToolCapabilityError(<projected text>))

certified result
    is_error = true
    content  = <projected text>
    details  = {}

R010-B requirement
    the same final tool-level error result also carries
    FsErrorCode.permission_denied as structured data

distinction
    the required structured value is absent; adding it requires a new seam or a lower-layer
    semantic delta, not a Layer-13 implementation choice
```

**Minimal correction:** choose and document one implementable architecture before presenting the
owner menu. Either (a) preserve the certified generated-error result shape and use the code only
internally to choose the normalized text, correcting “supplements, not replaces” accordingly, or
(b) open a narrow, explicit tool-result/lower-layer delta that provides the same structured-error
surface in Python and Rust. Do not imply the current Layer-06 contract already supplies it.

### L13-WP131-R010-D — actual R007-b consumption can surface `not_supported`, but the mapping excludes it

**Classification:** `CONTRACT_ASSURANCE_DEFECT`

Revision 2 says raw/hybrid sites preserve the full certified taxonomy, then its per-site mapping
explicitly excludes `not_supported`. That may describe Node's local `stat`/`readdir` calls, but it
does not describe the Minion seam Layer 13 has already been governed to consume. The approved
WP-12.E1 contract states that a provider unable to implement `list_dir_raw` or
`probe_dir_entry` returns `FsErrorCode.not_supported`; it includes a dedicated discriminating
witness for that case.

This is a concrete Lane-E interaction with the already-approved R007-b boundary, not a re-review
of R007. `list_dir_raw` failure occurs before the per-entry loop and is a whole-tool failure that
R010 must project. In contrast, an individual `probe_dir_entry` error is skipped by the
owner-approved Layer-13 loop and does not become tool-level error text. The candidate currently
states neither distinction and leaves the owner matrix incomplete for a reachable provider.

Minimal discriminating witness:

```text
setup
    an otherwise-valid filesystem provider returns Err(not_supported) from list_dir_raw(path)

approved R007-b consumption
    enumeration cannot begin; this is not an individual probe error and cannot be skipped

candidate mapping
    excludes not_supported from the ls enumeration/raw-hybrid failure set

distinction
    two implementations can choose different model-visible results for the same certified
    lower-layer outcome while both claim to follow R010 revision 2
```

**Minimal correction:** map every error outcome reachable through the actual Layer-12 operations
used by `read` and `ls`, including `list_dir_raw -> not_supported`. Explicitly separate
whole-operation errors that R010 projects from per-entry `probe_dir_entry` errors that the R007-b
loop skips. If any read-side operation can also report provider capability `not_supported`, cover
it under the same general rule rather than limiting the table to Node-local errno observations.

### L13-WP131-R010-E — the owner matrix calls four stable templates “three”

**Classification:** `CONTRACT_ASSURANCE_DEFECT` (documentary)

Sections 3 and 4 repeatedly say Pi has “THREE” hand-authored sites/templates, while the same text
enumerates four distinct stable strings:

1. `Path not found: <path>`;
2. `Not a directory: <path>`;
3. `Cannot read directory: <underlying message>`; and
4. `Operation aborted`.

The abort wording is shared by both tools, but that does not reduce this list of distinct stable
templates to three. An owner-facing matrix must not contradict its own inventory.

**Minimal correction:** say “four templates” (or use wording such as “three `ls` templates plus
the shared abort template”) consistently.

## Contract-quality answers

| Question | Answer |
|---|---|
| Does revision 2 provide two genuinely different, unselected owner options? | Yes. |
| Are Pi's stable authored strings preserved in both options? | Yes. |
| Is raw/hybrid normalization correctly labeled an intentional divergence? | Yes. |
| Is option B implementable through the currently certified cross-language tool seam? | No. |
| Does the mapping cover every outcome of the actual approved Layer-12 dependency? | No. |
| Does this review reopen R007 or existing Layer-12 semantics? | No. |
| Can an owner make a fully informed, implementable choice now? | No. |

## Findings by taxonomy

```text
PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    none (the intentional divergence is presented for governance, not yet selected)

CONTRACT_ASSURANCE_DEFECT
    L13-WP131-R010-C -- option B promises structured FsErrorCode across a seam that erases it
    L13-WP131-R010-D -- mapping omits reachable list_dir_raw not_supported and skip/project split
    L13-WP131-R010-E -- four stable templates are repeatedly counted as three

PARITY_NEUTRAL_HARDENING
    none

PARITY_CONSTRAINED_RISK
    none
```

## Required next action

Revise Lane E only:

1. make option B structurally implementable without silently changing certified Layer 05/06
   semantics, or explicitly scope a separate lower-layer delta;
2. map `not_supported` and distinguish whole-operation projection from skipped per-entry probes;
3. correct the four-template count; and
4. return the same two-option owner matrix for another Lane-E-only review.

Preserve R006/R007, WP-12.E1 approval, and all frozen findings. Do not implement Python or Rust
Layer 13, change Layer 12, or start Layer 14.
