# Layer 10 — convergence targeted finding-closure review

**Review mode:** workflow §11.8.7 targeted closure, not final contract approval.

## Exact candidate

- code PR #20: `4d63349d85d517359545b94ce0937548d3fb7314`
- docs PR #45: `57edf9fd08e9b7411d32177f5991756182dd6a7a`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- agreed convergence contract: docs PR #47 at
  `05e03a7faefb9bbc45eeff20ed1996267414d16d`

Both candidate PRs were open, Ready for Review, unmerged, and cleanly mergeable. Their exact
remote heads matched coordination issue #19. Candidate branches and Rust production were not
modified.

## Closure ledger

### L10-R001 — disposition of `stream` versus `streamSimple`

**PROVISIONALLY CLOSED.** `AI-028` now covers only Pi's adopted `stream`/never-raises surface.
`AI-031` separately records required `streamSimple` as `deferred parity`, assigns Layer 11, cites
no fabricated current evidence, and requires an externally callable Minion equivalent before the
row can close.

### L10-R002 — resolution and registry dispositions

**PROVISIONALLY CLOSED.** `AI-029` now accurately labels Minion's eager full-identity failure
boundary as `intentional divergence`; master-design authorization is no longer confused with Pi
adoption. `AI-030` independently covers Minion-only registration, replacement, withdrawal, and
introspection with its own coherent intentional-divergence disposition. Python's temporary API
default remains explicitly Python-specific.

### L10-R004 — canonical grammar and observation

**PROVISIONALLY CLOSED.** The schema enforces `reject_message` exactly for rejecting adapters.
Registration actions create explicit handle ids; withdrawal names a handle, not a fixture.
Pre-flight validation rejects duplicate fixtures, undeclared fixtures/handles, duplicate handles,
combined query/stream observation-id collisions, and dangling expectations while explicitly
allowing setup-only observations.

Resolution observation snapshots request counts before `stream()` and requires exactly one
adapter to grow. The permanent A-stream/replacement-B scenario reports B, and zero/multiple-owner
unit witnesses fail loudly rather than selecting a plausible first match. The runner dispatches
real `LlmService` operations and does not implement registry semantics itself.

### C10-C005 — per-registration-call ownership

**PROVISIONALLY CLOSED.** `LlmService.register()` stores a fresh opaque token per call alongside
the adapter. Withdrawal checks that token, so registering the identical adapter object twice does
not allow the first/stale handle to remove the second registration. The second/current handle
removes its entry and repeated withdrawal remains a safe no-op. The direct language test and
canonical same-fixture/two-handles scenario exercise the real production seam.

### L10-R003 — current Rust eager adapter-start failure

**OPEN, OUTSIDE THIS CONVERGENCE.** The contract still accurately marks current Rust's
`AdapterStartError` channel as a `PI_PARITY_DEFECT` for the later Rust Layer-10 implementation
pass. Nothing in this targeted review certifies or repairs it.

## Acceptance evidence

Independent fresh runs against the exact candidate:

```text
targeted service/schema/runner/canonical tests    224 passed
full Python suite                                 1161 passed, 19 xfailed, 0 failed
coverage                                          100.00%
ruff                                              PASS
mypy                                              PASS, 58 source files
manifest                                          83 rows / 83 unique ids
```

Source inspection additionally confirmed:

- the request-count snapshot occurs before eager `LlmService.stream()` invocation;
- `_owner_from_growth` requires exactly one delta;
- every existing scenario uses the new handle grammar;
- the replacement witness uses an unasserted setup stream deliberately and legally;
- `AI-030` and `spec/llm.md` make idempotent repeat withdrawal normative and reject a consuming
  single-use Rust representation;
- no Rust file and no Layer-11 surface changed.

## Targeted verdict

```text
L10-R001    PROVISIONALLY CLOSED @ code 4d63349 / docs 57edf9f
L10-R002    PROVISIONALLY CLOSED @ code 4d63349 / docs 57edf9f
L10-R004    PROVISIONALLY CLOSED @ code 4d63349 / docs 57edf9f
C10-C005    PROVISIONALLY CLOSED @ code 4d63349 / docs 57edf9f

L10-R003    OPEN RUST IMPLEMENTATION DEFECT

shared Layer-10 contract    NOT YET FINALLY APPROVED
Rust Layer 10               BLOCKED pending final contract review, then implementation
Layer 10 cross-language     NOT CLOSED
Layer 11                    NOT STARTED
```

Per workflow §11.8.8, the next action is one final complete independent contract review of this
exact candidate pair. Provisional closure does not satisfy the final certification gate. If either
candidate head moves, the final review target must be updated and re-verified before approval.
