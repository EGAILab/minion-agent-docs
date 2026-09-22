# CE-L13-WP131-01 Lane D R007 independent re-review 2

**Mode:** convergence sub-checkpoint review only. No Python or Rust implementation was performed
or authorized. No Layer 12 or Layer 14 work was performed.

## Exact target

```text
coordination issue:  EGAILab/minion-agent#48
status:              CONTRACT_CONVERGENCE
next owner:          Codex
docs PR:             EGAILab/minion-agent-docs#132
docs head:           d4e12d4eca8e750782a3f8b0edd86718286f13e2
manifest PR:         EGAILab/minion-agent#52
manifest head:       cca8d8b325bb159be549e10c8321b3468f043e7f (frozen)
docs base:           master @ 0bbd737fab8c1360995f4efff2b41c1c5531a9c3
code base:           main @ 92aa4be168dc82111832467922089206e858a9c4
pinned Pi:           b7bb00b936dbe21b8e160b3e89efdec361846699
episode:             CE-L13-WP131-01
artifact:            assurance/layers/13-wp131-ce-l13-wp131-01-r007-ls-enumeration.md
companion evidence:  assurance/layers/data/13-wp131-ce-l13-wp131-01/
                     r007-ls-enumeration-live-witness.txt
scope:               R007 only (Lane D revision 3)
prior review:        EGAILab/minion-agent-docs#145 @
                     d203451f189b438eaaf441d3701386c8d1f42e50
```

The issue-recorded heads matched the open remote PR heads and were remote-reachable. The handoff
carried the required governance provenance and was not derived from quarantined work. R006 was not
re-reviewed; its paused state remains unchanged. Every other frozen/resolved lane was preserved.

## Result

```text
R007 CHARACTERIZATION:  APPROVED
OWNER DECISION READY:   YES
IMPLEMENTATION:         NOT AUTHORIZED
```

## Independent verification

### Lazy additive surface

Revision 3 replaces the rejected eager full scan with one coherent two-operation Layer-12 delta:

```text
list_dir_raw(path) -> Result[list[str], FsError]
probe_dir_entry(path) -> Result[DirEntryProbe, FsError]
```

The operations preserve the exact authority split needed by pinned Pi:

1. `list_dir_raw` returns provider-order names without stat/classification.
2. Layer 13 applies the selected R006 ordering to all raw names.
3. Before each probe, Layer 13 checks its successful-result cap.
4. `probe_dir_entry` performs one symlink-following classification and returns its own typed
   result/error without changing existing `FileInfo` or `FileKind`.
5. Layer 13 skips an individual probe error and continues, matching Pi's per-entry catch.

Against the prior review's discriminating case:

```text
raw order:      [z_slow, a_ok]
sorted order:   [a_ok, z_slow]
limit:          1
```

Layer 13 probes `a_ok`, reaches one successful result, and exits at the next loop guard without
calling `probe_dir_entry(z_slow)`. Thus cancellation, latency, TOCTOU exposure, and provider-call
count beyond the cap match Pi structurally rather than merely reconstructing the same final text.

The new `DirEntryProbe` vocabulary is separate from certified `FileInfo`/`FileKind`. Existing
Layer-12 operations and callers remain unchanged. This is correctly characterized as an additive
Layer-12 delta requiring narrow cross-language revalidation if selected, not as a reopening of the
existing operations' certification.

### Divergence coverage

The owner menu now covers all five source-confirmed differences:

```text
4a  FIFO/socket/device: Pi includes; current Layer-12 composition omits
4b  per-entry error:    Pi skips one; current Layer-12 composition fails whole call
4c  cap-boundary:       content can differ when 4a/4b occurs before the cap
4d  directory symlink: Pi follows and appends /; current Layer 12 reports SYMLINK
4e  broken symlink:    Pi skips; current Layer 12 includes SYMLINK
```

R007-a accurately asks the owner to govern all five observable divergences. R007-b supplies the
two-phase capability needed to reproduce them without changing existing semantics.

### Evidence correction

The positive TOCTOU witness uses the same explicitly recreated path/setup for sequential Node and
Python runs. The negative control now records the complete Python output with all names, paths,
and kinds; no `...` placeholder remains. The evidence is durable and discriminates the injected
vanish from the ordinary all-entries-survive case.

## Owner decision menu

No option is selected by this review.

```text
R007-a — accept and govern the five disclosed divergences
    Layer-12 delta: none
    WP-13.1 uses current list_dir()
    Pi fidelity: intentionally lower on 4a-4e
    implementation cost: lowest

R007-b — authorize the additive two-operation Layer-12 capability
    Layer-12 delta: list_dir_raw + probe_dir_entry + new DirEntryProbe type
    existing operations/types/callers: unchanged
    WP-13.1 owns sorting, lazy probing, per-entry skip, and cap-before-probe
    Pi fidelity: structurally high on 4a-4e and the cap/cancellation boundary
    implementation cost: moderate plus narrow Python/Rust Layer-12 revalidation
```

Either choice requires an explicit owner governance source before contract integration or
implementation. Approval of the characterization does not approve either option.

## Verdict

```text
R007:                      CHARACTERIZATION APPROVED
Lane D:                    OWNER DECISION READY
Owner decision ready:      YES
Implementation authorized:NO
Python WP-13.1:            NOT_IMPLEMENTED / NOT AUTHORIZED
Rust WP-13.1:              NOT_IMPLEMENTED / BLOCKED
Layer 13 cross-language:   NOT CLOSED
Layer 14:                  NOT STARTED
```

Move only R007 to `BLOCKED_FOR_OWNER`. Preserve R006's paused state and every other
frozen/resolved finding. Do not begin Lane E until the coordination workflow authorizes it.
