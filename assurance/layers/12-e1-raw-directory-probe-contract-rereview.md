# WP-12.E1 independent Rust contract re-review

## Verdict

```text
WP-12.E1 shared contract
    REJECTED

Python WP-12.E1
    NOT_IMPLEMENTED

Rust WP-12.E1
    BLOCKED

Layer 12 existing certified surface
    UNCHANGED / REMAINS CERTIFIED

Layer 13 WP-13.1 Lane E
    NOT REVIEWED / UNCHANGED
```

One narrow contract contradiction remains in the `DirEntryProbe.path` rule. The other four findings
from the first review are closed, and the two-phase architecture remains sound.

## Exact review target

| Item | Exact state |
|---|---|
| Coordination | `EGAILab/minion-agent#53`, `STATUS = CONTRACT_CONVERGENCE`, `NEXT_OWNER = Codex` |
| Code/manifest PR | `EGAILab/minion-agent#54` @ `30d534636665932b7e0f804ff498ac65fc3f5c18` |
| Docs/spec PR | `EGAILab/minion-agent-docs#147` @ `525d646e99fdf2773da666687aff321bce90aba1` |
| Prior rejected review | `EGAILab/minion-agent-docs#148` @ `de4860bf864bf8791a1e920f4100924f5f0923b8` |
| Pinned Pi | `b7bb00b936dbe21b8e160b3e89efdec361846699` |
| Governance source | `EGAILab/minion-agent#48#issuecomment-5771291305` (`R007-b`) |

Both candidate PRs were open, Ready for Review, mergeable, and their exact heads were fetched and
verified remote-reachable before review. The issue's paired SHA record matched the PR heads. The
handoff declared no quarantine derivation. Review applies only to the two SHAs above.

## Authority and source audit

The review used the required order: pinned Pi, normative spec, manifest, certified Layer-12
architecture, then the remediation handoff.

Re-read independently:

- pinned Pi `packages/coding-agent/src/core/tools/ls.ts:145-176` (`readdir`, caller-side sort,
  cap-before-probe, following `stat`, per-entry catch/skip);
- pinned Pi `packages/agent/src/harness/env/nodejs.ts:51-65, 81-91, 602-633`
  (`resolvePath`, `fileInfoFromStats`, `fileInfo`, `listDir`);
- candidate `spec/execution.md` sections 2.1, 3, 3.1, 3.2, 3.6, and 11;
- candidate manifest rows `EXEC-001`, `EXEC-002`, `EXEC-003`, and new `EXEC-007`;
- certified Python `LocalFileSystem.file_info` / `_file_info_sync` and certified Rust
  `LocalFileSystem::file_info` / `info_for` only after the source/spec audit, to verify the claimed
  lower-layer convention.

The fundamental owner-selected design remains coherent: raw provider-order names, caller-side
sorting, lazy symlink-following probes, per-probe errors, and cap-before-next-probe can reproduce
Pi's product-level `ls` loop without changing the already-certified harness-derived `list_dir` or
`file_info` operations.

## Prior-finding closure ledger

### WP12E1-R001 — authoritative operation inventory

**Result: CLOSED.** Section 3 now lists both additive signatures and marks them as
`CONTRACT_DRAFT`, while the pre-existing inventory lines remain unchanged. Section 11 is no longer
a second contract disconnected from the authoritative public surface.

### WP12E1-R002 — requirement/disposition/evidence chain

**Result: CLOSED.** Issue #53 now names `EXEC-007`; the manifest contains one independently scoped
row with the Pi-derived product behavior, the Minion additive mapping, the `intentional divergence`
disposition, governance source, planned language owners, and planned evidence. The row does not
claim either implementation exists. Manifest validation passed: `8 passed`; parsed inventory is
`102 rows / 102 unique IDs`, and `EXEC-007.tests` is a list of 11 strings.

### WP12E1-R003 — `DirEntryProbe.name` / `.path`

**Result: PARTIALLY_RESOLVED_BLOCKING.** The fields are no longer undefined, but their new rule is
internally contradictory with the certified convention it claims to reuse. See refined finding
below.

### WP12E1-R004 — cancellation ownership

**Result: CLOSED.** Section 11 now labels direct-operation cancellation as a
`MINION_ARCHITECTURAL_MAPPING` rather than deriving it by analogy from two incompatible Pi
surfaces. It specifies one pre-read check for `list_dir_raw`, no inspection by
`probe_dir_entry`, no native in-flight cancellation in either operation, and assigns the future
outer tool race/checkpoints to Layer 13's separately settled R008 contract. The witness matrix
distinguishes the two direct-operation rules.

### WP12E1-R005 — discriminating evidence plan

**Result: CLOSED.** The expanded matrix covers raw provider order and zero probes; plain file and
directory; symlink-to-file and symlink-to-directory; symlink-to-other collapse; successful
`other`; broken symlink/per-call error; unsupported provider; cancellation; name/path identity;
lazy cap behavior; and unchanged existing operations. Each entry includes a negative control. No
runner or implementation exists yet, so these remain honestly marked planned/predicted.

## Blocking finding

### WP12E1-R003 (refined) — `DirEntryProbe.path` contradicts the cited `FileInfo.path` convention

**Classification:** `CONTRACT_ASSURANCE_DEFECT`

**Affected text:** candidate `spec/execution.md` section 11.4, the paragraph beginning
“`DirEntryProbe.name`/`.path` identity”, plus its section-11.6 witnesses and `EXEC-007` rule text.

The candidate requires:

```text
DirEntryProbe.path = EXACT path string passed by the caller, never re-resolved
```

and calls that “identical” to certified `FileInfo.name`/`.path`. It is not. Pinned Pi's
`NodeExecutionEnv.fileInfo` first executes `resolved = resolvePath(this.cwd, path)` and passes that
resolved value to `fileInfoFromStats`; the returned `FileInfo.path` is the resolved value and
`name = basename(resolved)`. The certified Python implementation likewise calls
`resolve_local_path(self.cwd, path)` before `_file_info_sync` builds the result. The certified Rust
implementation calls `self.info_for(self.resolved(path))` and returns that resolved path.

Minimal discriminating witness:

```text
cwd
    /workspace

call
    file_info("sub/item")

certified FileInfo convention
    path = /workspace/sub/item
    name = item

candidate probe rule for the analogous call
    probe_dir_entry("sub/item").path = "sub/item"
```

The new operation may deliberately preserve the lexical caller string, or it may reuse the
resolved `FileInfo` convention, but the contract cannot require the first while asserting the
second. The same ambiguity also matters for `~`, `file://`, and syntactically normalized paths.
Rust should not have to guess whether the explicit “exact input” sentence or the claimed
lower-layer convention owns the observable result.

**Minimal correction required:** choose and state one rule consistently:

1. if the intended rule is exact caller input, remove the false `FileInfo` equivalence and label
   this as its own deliberate Layer-12 mapping, then update `EXEC-007` and witnesses accordingly;
   or
2. if the intended rule is the certified `FileInfo` convention, require normal Layer-12 path
   resolution first and return that resolved addressed-entry path, then update the witnesses.

In either case, preserve the already-correct rule that following a symlink for classification never
substitutes the resolved **target object's** identity. Add one relative-path witness (and, if the
general Layer-12 resolver is reused, rely on its already-certified `~`/`file://` coverage rather
than duplicating that machinery).

## Contract-quality answers

| Question | Result |
|---|---|
| Does the contract change existing `list_dir`/`file_info` semantics? | No. |
| Does it reopen historical Layer-12 certification? | No. |
| Is the two-phase raw-enumerate / sort / lazy-probe boundary implementable? | Yes. |
| Can Rust implement every observable field without guessing? | **No**, only because `DirEntryProbe.path` has conflicting authorities. |
| Does any current runner simulate the new behavior? | No runner exists; evidence is correctly planned. |
| Is Lane E implicated? | No; it was not reviewed or modified. |

## Findings by taxonomy

```text
PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    none

CONTRACT_ASSURANCE_DEFECT
    WP12E1-R003 (refined) -- path identity/resolution contradiction

PARITY_NEUTRAL_HARDENING
    none

PARITY_CONSTRAINED_RISK
    none
```

## Gates run

```text
uv run pytest tests/conformance/test_manifest_validation.py -q --no-cov
    8 passed

independent YAML inventory probe
    102 rows
    102 unique IDs
    EXEC-007.tests type = list
    EXEC-007 planned tests = 11
```

The first invocation without `--no-cov` also executed all eight manifest tests successfully but
returned non-zero solely because running that narrow file cannot meet the repository-wide 100%
coverage threshold; it was rerun with coverage disabled to obtain the relevant gate result above.

## Required next action

Return only the narrow `WP12E1-R003` correction to the shared-contract owner. Do not implement
Python or Rust, do not modify existing Layer-12 behavior, do not touch WP-13.1 Lane E, and do not
start Layer 14. Any changed candidate SHA requires another exact-SHA review of the correction.
