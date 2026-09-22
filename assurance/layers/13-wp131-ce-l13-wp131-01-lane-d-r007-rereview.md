# CE-L13-WP131-01 Lane D R007 independent re-review

**Mode:** convergence sub-checkpoint review only. No Python or Rust implementation was performed
or authorized. No Layer 12 or Layer 14 work was performed.

## Exact target

```text
coordination issue:  EGAILab/minion-agent#48
status:              CONTRACT_CONVERGENCE
next owner:          Codex
docs PR:             EGAILab/minion-agent-docs#132
docs head:           838cb89846598a1fd1702ab93de03a2e53c5bcd6
manifest PR:         EGAILab/minion-agent#52
manifest head:       cca8d8b325bb159be549e10c8321b3468f043e7f (frozen)
docs base:           master @ 0bbd737fab8c1360995f4efff2b41c1c5531a9c3
code base:           main @ 92aa4be168dc82111832467922089206e858a9c4
pinned Pi:           b7bb00b936dbe21b8e160b3e89efdec361846699
episode:             CE-L13-WP131-01
artifact:            assurance/layers/13-wp131-ce-l13-wp131-01-r007-ls-enumeration.md
companion evidence:  assurance/layers/data/13-wp131-ce-l13-wp131-01/
                     r007-ls-enumeration-live-witness.txt
scope:               R007 only (Lane D revision 2)
prior review:        EGAILab/minion-agent-docs#144 @
                     3804d93b5b71562c7f550a35293f8ac0652eea03
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

## Prior-finding closure ledger

### L13-WP131-R007-C1

```text
status: RESOLVED
```

Revision 2 correctly adds both symlink cases to the matrix and to R007-a/R007-b:

- a directory symlink is followed and receives `/` in Pi, but current Layer 12 classifies the
  link itself as `SYMLINK`;
- a broken symlink is skipped by Pi's failed following-stat, but current Layer 12 includes it as
  `SYMLINK`.

The live transcript and pinned source support both statements.

### L13-WP131-R007-C2

```text
status: NOT_RESOLVED
classification: CONTRACT_ASSURANCE_DEFECT
```

Revision 2 selects one new provider-neutral operation and avoids changing `FileInfo`/`FileKind`,
which resolves the prior type-authority ambiguity. But the selected operation cannot provide the
claimed Pi-equivalent execution order.

Pinned Pi performs:

```text
raw readdir
sort ALL raw names
for each name in sorted order:
    if successful-result count reached limit: stop immediately
    stat this one name
    skip failure or append success
```

The proposed `list_dir_entries()` instead performs:

```text
raw enumeration
stat/probe EVERY entry in provider enumeration order
return the complete probe list
Layer 13 sorts afterward and computes the cap
```

Having enough final data to reconstruct Pi's *content* does not reproduce Pi's observable work
boundary. The proposal probes entries Pi never reaches, and probes them in a different order.
That changes at least:

- when and whether cancellation can reject the call;
- whether a slow or non-settling provider stat beyond the cap delays the call;
- which TOCTOU filesystem mutations are observed;
- provider-visible request ordering for remote/custom execution worlds.

This also contradicts the candidate's statement that cap timing becomes structurally equivalent.
R008 already makes cancellation during per-entry classification observable, so this cannot be
deferred as an internal performance detail.

#### Discriminating witness

```text
setup:
    provider raw order: ["z_slow", "a_ok"]
    sorted order:       ["a_ok", "z_slow"]
    limit:              1
    stat("a_ok"):       immediate success, not a directory
    stat("z_slow"):     suspends until aborted

pinned Pi:
    sorts first; stats a_ok; returns ["a_ok"] without ever statting z_slow

revision-2 R007-b:
    list_dir_entries probes z_slow before returning any list; the call blocks or is aborted

why discriminating:
    final-content reconstruction cannot undo an extra external operation that already happened
```

Required correction: define an additive provider-neutral surface that lets Layer 13 preserve the
actual loop boundary. A coherent shape may be a paired capability (`list raw names` plus
`symlink-following per-entry directory probe`) under one Layer-12 delta, or another typed streaming
surface that permits caller-controlled sorted order and early stop. Do not require a single
eager full-scan operation if that single operation destroys the behavior being adopted.

### L13-WP131-R007-C3

```text
status: PARTIALLY_RESOLVED_BLOCKING
classification: CONTRACT_ASSURANCE_DEFECT
```

The positive TOCTOU comparison now recreates one documented path identically for each sequential
run, fixing the prior mismatch. The negative control is conceptually appropriate. However, the
companion file still claims to contain full raw output while replacing the Python negative-control
output with literal `...` placeholders and saying the full dictionaries existed only in session
output. Session-only output is not durable evidence.

Required correction: record the actual complete negative-control output in the companion artifact
and keep the commands/setup exactly reproducible. This is documentary/evidence-only; it does not
change the confirmed source characterization.

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
