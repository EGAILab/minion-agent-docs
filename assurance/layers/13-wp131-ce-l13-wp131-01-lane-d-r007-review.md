# CE-L13-WP131-01 Lane D R007 independent review

**Mode:** convergence sub-checkpoint review only. No Python or Rust implementation was performed
or authorized. No Layer 12 or Layer 14 work was performed.

## Exact target

```text
coordination issue:  EGAILab/minion-agent#48
status:              CONTRACT_CONVERGENCE
next owner:          Codex
docs PR:             EGAILab/minion-agent-docs#132
docs head:           978788d55f45f70791b75da2bb2c03d178182673
manifest PR:         EGAILab/minion-agent#52
manifest head:       cca8d8b325bb159be549e10c8321b3468f043e7f (frozen)
docs base:           master @ 0bbd737fab8c1360995f4efff2b41c1c5531a9c3
code base:           main @ 92aa4be168dc82111832467922089206e858a9c4
pinned Pi:           b7bb00b936dbe21b8e160b3e89efdec361846699
episode:             CE-L13-WP131-01
artifact:            assurance/layers/13-wp131-ce-l13-wp131-01-r007-ls-enumeration.md
companion evidence:  assurance/layers/data/13-wp131-ce-l13-wp131-01/
                     r007-ls-enumeration-live-witness.txt
scope:               R007 only (Lane D revision 1)
```

The issue-recorded heads matched the open remote PR heads and were remote-reachable. The handoff
carried the required governance provenance and was not derived from quarantined work. R006 was not
re-reviewed; its paused state remains unchanged. Every other frozen/resolved lane was preserved.

## Result

```text
R007 CHARACTERIZATION:  REJECTED
OWNER DECISION READY:   NO
IMPLEMENTATION:         NOT AUTHORIZED
```

## Independently confirmed source mapping

The characterization's central correction is valid:

- pinned Pi `packages/coding-agent/src/core/tools/ls.ts` defines its own `LsOperations`, whose
  defaults are raw `node:fs/promises` `readdir` and `stat`;
- the product `ls` loop sorts raw names, checks the cap before the next per-entry `stat`, follows
  symlinks through `stat`, includes every successfully-statted non-directory kind as a plain name,
  and catches any per-entry `stat` exception before continuing;
- pinned Pi `packages/agent/src/harness/env/nodejs.ts::listDir` is a different surface using
  `readdir(..., {withFileTypes:true})`, `lstat`, `fileInfoFromStats`, unsupported-kind omission,
  and whole-call failure for other per-entry exceptions;
- current Python Layer 12 `_list_dir_sync` uses `os.scandir`, `os.lstat`, omits only
  `_UnsupportedFileType`, and lets other per-entry exceptions fail the operation.

Therefore 4a and 4b are genuine source-level differences, and 4c is their genuine cap-boundary
consequence. The narrower claim that cap timing alone is observationally neutral when every raw
entry survives identically is also correct.

## Blocking findings

### L13-WP131-R007-C1 — `CONTRACT_ASSURANCE_DEFECT`

The characterization identifies but deliberately leaves unresolved a fourth divergence produced
by the same seam: Pi uses symlink-following `stat`, while Layer 12 uses `lstat` and returns a
`SYMLINK` entry.

This is observable in at least two ordinary cases:

```text
symlink -> directory: Pi appends "/"; Layer-12-composed ls sees SYMLINK and does not.
broken symlink:       Pi's stat throws and the entry is skipped; Layer 12 returns SYMLINK and the
                      composed ls includes it.
```

The current normative draft already discloses the broken-symlink difference under R007, proving
it belongs to this exact owner surface. Yet R007-a asks the owner to approve only three listed
divergences, and R007-b claims high fidelity on "all three" while leaving symlink behavior
unchanged. Selecting either option would therefore leave a known observable difference without a
coherent disposition.

Required correction: include symlink-following behavior in R007's matrix and both owner options.
If accepting divergence, name both symlink-to-directory suffix and broken-symlink inclusion. If
seeking parity, ensure the additive capability can perform Pi's following-stat directory test and
per-entry catch behavior.

### L13-WP131-R007-C2 — `CONTRACT_ASSURANCE_DEFECT`

R007-b is not yet one implementable, language-neutral additive capability. Candidate `(ii)` is
described as a `file_info_permissive` operation that returns `FileInfo` with a new `OTHER`
`FileKind`, but also as a "Layer-13-local wrapper, not necessarily a new certified Layer-12
operation." Neither form works as stated:

- a Layer-13 wrapper over existing `file_info()` cannot recover an unsupported kind after the
  provider has already converted it to an error;
- adding `OTHER` changes the certified Layer-12 `FileKind` vocabulary and every provider-facing
  serialization/type consumer, so it is not merely a local wrapper;
- even a successful `OTHER` classification does not reproduce Pi's symlink-following directory
  suffix behavior;
- arbitrary `ctx.fs` providers cannot be bypassed with local OS calls without violating the
  provider-neutral execution-world contract.

The owner can choose "accept divergences" versus "authorize a narrow additive Layer-12 delta,"
but the parity option must first identify a concrete provider-neutral surface sufficient to run
the product `ls` loop. One viable shape would expose raw names plus a per-path, symlink-following
directory predicate/stat result whose error remains per-entry catchable; other typed shapes are
possible. The contract must select one, not alternate between a local wrapper and a protocol
extension with different type consequences.

### L13-WP131-R007-C3 — `CONTRACT_ASSURANCE_DEFECT`

The companion evidence says all commands and full raw output are recorded exactly, and describes
Case B as the same vanish-before-stat setup in both languages. The transcript does not support
that claim:

```text
setup and Node target:   /tmp/r007_caseB2
Python target:           /tmp/r007_caseB
```

No setup for `/tmp/r007_caseB` is recorded in Case B. The Python result is consistent with the
source-level reasoning, but this transcript is not a reproducible paired witness and cannot be
the claimed live comparison.

Required correction: rerun the exact paired witness against one recorded setup/path (preferably
through the real Minion Layer-12 seam where practical), record commands and output, and retain a
negative control showing the whole-call failure disappears when no entry vanishes.

## Discriminating witness matrix required by remediation

```text
case                         Pi product ls              current Layer-12 composition
FIFO/socket/device           include plain name         omit unsupported kind
entry vanishes after scan    skip entry; call succeeds  whole call fails
symlink -> directory         include with "/"           include as symlink/no "/"
broken symlink               skip entry                 include as symlink
all entries survive          cap-before-stat output      post-hoc cap output is identical
unsupported before cap       includes/counts it          omits; later survivor can replace it
```

The revised owner menu must state which rows are accepted divergences and which rows the additive
surface makes structurally reproducible.

## Verdict

```text
R007:                      CHARACTERIZATION REJECTED
Lane D:                    CHANGES REQUIRED
Owner decision ready:      NO
Implementation authorized:NO
Python WP-13.1:            NOT_IMPLEMENTED / NOT AUTHORIZED
Rust WP-13.1:              NOT_IMPLEMENTED / BLOCKED
Layer 13 cross-language:   NOT CLOSED
Layer 14:                  NOT STARTED
```

Return only Lane D to the shared-contract owner. Preserve R006's paused state and every other
frozen/resolved finding. Do not begin Lane E.
