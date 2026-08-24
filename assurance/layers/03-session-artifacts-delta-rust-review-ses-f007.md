# Rust narrow re-review — SES-F007 compaction linearization

Date: 2026-08-24

## Reviewed state

- `minion-agent`: `c5f6bb1491d39900f5ec390c3f5aeb367218cc60`
- `minion-agent-docs`: `5a375840850b547698734b00926d4a038fcd8e1d`
- previous Rust rejection: `6d2944ed106032d2f65b40c49a4d37e4fa55aee1`

## SES-F007 re-review

The previous rejection is confirmed: the first remediation specified append atomicity but did not
make compaction's effective-surface/provenance snapshot and marker commit one observable mutation.

The corrected `spec/session.md` now requires those operations to form one linearizable operation
relative to append, reset, and other compactions. It explicitly prohibits any such mutation from
committing between the snapshot and marker in the observable serialization order. Events before
the linearization point participate in the snapshot; events after it cannot alter the recorded
provenance.

The rule is mechanism-neutral. A mutex, actor, serial executor, or a cooperative execution model
with no suspension/re-entry point can satisfy it. It does not require Rust locks, universal
thread-safe Session access, linearized reads, or a lock spanning all message derivation. It applies
only when an implementation admits concurrent Session mutation; otherwise it is satisfied by
construction.

### Python evidence

`operations.compact()` calls `effective_surface()` and then `SessionLog.append()` synchronously.
The complete path contains no `await`, yield, callback, hook, descriptor invocation, or other
supported user-code/re-entry point between snapshot and marker append. `effective_surface()` reads
immutable tuple snapshots and applies built-in filtering; `append()` validates JSON-safe built-in
values and mutates the private list synchronously. Under the supported single-threaded cooperative
asyncio model, another coroutine cannot interleave in that interval.

The focused concurrency test is appropriate language-level evidence. It schedules many append and
compact calls between operations and checks each committed compaction's provenance against events
committed before its marker. It does not mock Session behavior or implement scheduling in canonical
conformance.

### Rust evidence

Current `Session::compact()` acquires `inner.events` once and retains that same mutex guard while it
computes the reset floor, effective surface, retained provenance, and `superseded_through`, then
calls `append_locked()` for the marker. `append()`, `reset()`, and other `compact()` calls require
the same mutex. Therefore none can commit between the snapshot and marker.

No Rust semantic change is required for SES-F007. A focused regression remains appropriate during
the consolidated Rust remediation.

### Evidence split

No canonical concurrency scheduler is required. The shared specification defines the observable
cross-language rule; Python and Rust language-level tests prove their respective execution-model
mechanisms. Adding scheduling semantics to the YAML runner would violate the thin-runner boundary.

## SES-F004 history correction

**APPROVED.** The assurance record and Python commentary now state accurately that bare
`compaction` was the previously certified normative value and that the delta deliberately
superseded it with `session/compaction`. They no longer recast the old value as an unpinned typo.

## Regression impact

- A — LLM-F011: UNAFFECTED.
- C — SES-F005: UNAFFECTED.
- D — SES-F006: UNAFFECTED.
- F — SES-F008: UNAFFECTED.

## Formal verdicts

```text
SES-F007
    APPROVED

LAYER 02 DELTA CONTRACT
    APPROVED

LAYER 03 DELTA CONTRACT
    APPROVED
```

The shared contract is sufficiently precise and language-neutral for consolidated Rust Layer-02/
Layer-03 delta remediation to begin. Layer 04 remains out of scope.
