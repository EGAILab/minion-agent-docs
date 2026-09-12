# Layer 11 Auth Foundation — Third Final Complete Independent Rust Contract Review

## Exact target

```text
code PR #25
    658028decd8f86dfd4229693a4719c7fd06ca652

docs PR #54
    1e111b9e1742954eb40d24dfb755dafcd0bbfec8

prior complete review
    docs PR #61 @ 382bb4e04e1963ca52671c2d5aa7c3a7c1c8f014

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

Both exact heads were fetched from GitHub, matched issue #24's latest handoff, and were open,
Ready for Review, unmerged, and remote-reachable. This was another complete §11.8.8 review, not a
targeted check. No candidate or Rust file was modified.

## Verdict

```text
shared Layer-11 Auth Foundation contract
    REJECTED

Python Layer 11 Pass 1
    REOPENED

Rust Layer 11
    BLOCKED / NOT_IMPLEMENTED

Layer 11 cross-language
    NOT CLOSED

Layer 12
    NOT STARTED
```

L11-R001 through L11-R013 are closed at this exact candidate. L11-R014 remains open with a refined
used-interval witness. Because the same non-finite-initial-interval finding has now survived two
complete reviews, its own §11.8 convergence trigger is met.

## Independent audit and closure ledger

Review order was pinned Pi, spec, manifest, canonical evidence, certified Rust architecture,
assurance, then Python. Re-read sources included the complete pinned auth types/context/store/
resolve/PKCE/device-code files and relevant tests/call sites.

| Finding | Exact-candidate result |
|---|---|
| L11-R001 | CLOSED — store cancellation/serialization remains Pi-compatible. |
| L11-R002 | CLOSED — combined refresh signal and timeout remain correct. |
| L11-R003 | CLOSED — protocol/default environment behavior remains correctly split. |
| L11-R004 | CLOSED — server intervals require finite and positive. |
| L11-R005 | CLOSED — deferred generic auth orchestration remains owned. |
| L11-R006 | CLOSED — live mutable credentials and permanent typing evidence remain intact. |
| L11-R007 | CLOSED — list ordering remains pinned. |
| L11-R008 | CLOSED — leading-tilde support remains protocol-owned. |
| L11-R009 | CLOSED — scalar credential mutability remains implemented. |
| L11-R010 | CLOSED — env/extra domains remain separated. |
| L11-R011 | CLOSED — effective threshold is reused for all three expiry checks. |
| L11-R012 | CLOSED — finite initial/server intervals floor to whole milliseconds. |
| L11-R013 | CLOSED — resolution and access are now inside one `except Exception` boundary; all agreed witnesses pass. |
| L11-R014 | STILL OPEN — immediate success no longer throws, but a non-finite interval that is actually used still diverges. |

The L11-R013 convergence agreement matches pinned `defaultProviderAuthContext.fileExists`.
Candidate witnesses now return `False` for home-resolution `OSError`, access `OSError`, and access
`RuntimeError`, while preserving literal `home + suffix` expansion. No narrower exception filter or
out-of-bound resolution remains.

## L11-R014 — non-finite initial interval remediation is incomplete

Classification: `PI_PARITY_DEFECT` plus an incomplete shared disposition.

The prior review's immediate-complete witnesses now pass: `_floor_to_whole_milliseconds` returns
non-finite input unchanged, so `Infinity`/`NaN` do not throw before the first poll.

The same public inputs remain observably wrong once a first poll returns `pending`:

1. Pinned Pi computes `Math.max(1000, Math.floor(interval * 1000))`. JavaScript preserves
   `Infinity` and yields `NaN` for NaN; neither arithmetic operation throws.
2. Pi passes that delay to its host timer. In the pinned Node runtime, both non-finite delays settle
   promptly (the review probe observed both callbacks), so the next poll occurs.
3. Python returns non-finite input from the helper, but `max(1.0, NaN)` silently changes NaN to
   `1.0`; a `pending -> complete` probe therefore waits one second under the injected clock.
4. Python leaves Infinity as Infinity, then the accepted poll-sliced `abortable_sleep` subtracts
   finite slices from Infinity forever. A no-deadline `pending -> complete` run never reaches its
   second poll.

Fresh exact-candidate evidence:

```text
NaN, pending -> complete
    candidate: completes after 1.0 simulated second
    Pi/Node timer: non-finite delay settles promptly, then second poll runs

Infinity, pending -> complete, no deadline
    candidate: remains in infinite 50ms slicing (three successive slices observed, no progress)
    Pi/Node timer: callback settles, then second poll runs
```

The normative text says non-finite initial intervals are accepted and flooring is a pass-through,
but specifies only the case where the interval is never used. It also claims this matches Pi's
numeric behavior while Python's subsequent clamp does not preserve NaN. A Rust implementer still
must guess whether a used non-finite interval retries, hangs, errors, or is normalized.

Required action: enter convergence for L11-R014 and explicitly characterize the stable
language-neutral observation for *used* non-finite intervals. At minimum, neither value may throw
or prevent all future polling solely because of numeric conversion; a `pending -> complete`
witness must eventually reach the second poll. Exact sub-millisecond host-timer latency need not be
made normative if Pi's supported hosts differ, but progress versus permanent hang must be.

If the project instead narrows the caller input domain to finite values, that is an observable
intentional divergence requiring owner governance; it cannot coexist with the current adopted row
and tests asserting non-finite input is accepted.

## L11-R014 convergence characterization (§11.8.3)

Status: **PROPOSED — AWAITING INDEPENDENT CHALLENGE**.

```text
OPEN FINDING
    L11-R014

PI SYMBOLS / RUNTIME AUDITED
    packages/ai/src/auth/oauth/device-code.ts::pollOAuthDeviceCodeFlow
    packages/ai/src/auth/oauth/device-code.ts::abortableSleep
    pinned Node setTimeout numeric-delay behavior

OBSERVABLE RULES
    finite initial and accepted server intervals floor to whole milliseconds
    server non-finite values use the +5s fallback (L11-R004)
    initial non-finite values do not fail before polling
    immediate complete returns without sleeping
    pending with non-finite initial input does not permanently prevent the next poll

BEHAVIOR MATRIX
    finite 1.2349, pending -> complete    floor to 1.234 then complete
    NaN, immediate complete              complete, no setup error
    Infinity, immediate complete         complete, no setup error
    NaN, pending -> complete              next poll remains reachable
    Infinity, pending -> complete         next poll remains reachable
    non-finite server slow_down           ignore value, current interval + 5s

MINIMAL WITNESSES
    retain both immediate-complete tests
    add NaN pending->complete with deterministic non-hanging observation
    add Infinity pending->complete with deterministic non-hanging observation

CURRENT FAILURES
    NaN becomes 1.0 at Python max rather than preserving timer-input behavior
    Infinity enters a non-terminating sliced sleep without a deadline

SPEC / MANIFEST / EVIDENCE DELTAS
    define progress/non-hang behavior once challenge resolves host-timer mapping
    update PROV-010 and language evidence
    canonical schema need not encode special floats

IMPLEMENTATION CONSTRAINTS
    preserve R004 server finite guard
    preserve R012 finite millisecond floor
    preserve immediate-poll-before-sleep behavior
    do not prescribe JavaScript timer internals where only eventual progress is observable

OUT OF SCOPE
    real provider/device endpoint transport
    exact wall-clock latency for host-specific special timer values
    Rust implementation and Layer 12
```

The shared/Python owner must challenge whether “eventual next-poll progress, exact delay
non-normative” is the correct cross-host abstraction or propose a more precise source-grounded
mapping before implementation.

## Manifest, canonical, and Rust feasibility

PROV-006–009 and PROV-011–013 pass. PROV-010 fails only on L11-R014's incomplete non-finite
initial interval semantics; its finite interval, outcome, timeout, and cancellation rules pass.
Manifest structure is valid: 92 rows / 92 unique IDs.

Six auth-device-code scenarios still execute through a thin runner using the real poller. No runner
implements retry, backoff, deadline, or error behavior. Special non-JSON numeric values remain
appropriately language-test evidence rather than canonical YAML.

Rust can implement every closed rule using existing typed signals, Tokio synchronization, hashing,
and conformance conventions. R014 requires no lower-layer reopen, but its shared observation must
be settled before Rust starts; otherwise Rust would invent its own Duration conversion/hang policy.

## Fresh gates

```text
full Python suite
    1287 passed, 19 xfailed, 0 failed

coverage
    100.00% — 3137 statements, 0 missed

auth + schema + manifest + canonical + layering selection
    324 passed

ruff
    PASS

mypy including all three typing fixtures
    PASS — 69 source files

ruff format --check
    same seven pre-existing drift files; no candidate-owned new drift

manifest
    92 rows / 92 unique IDs

Rust files changed
    none
```

## Findings and next action

```text
PI_BEHAVIOR_UNCERTAIN
    none after convergence characterization is challenged; currently the cross-host abstraction
    for used non-finite delays requires agreement

PI_PARITY_DEFECT
    L11-R014 — used NaN/Infinity initial intervals still diverge; Infinity can hang forever

CONTRACT_ASSURANCE_DEFECT
    L11-R014 used-interval behavior is not specified despite accepting these values

PARITY_NEUTRAL_HARDENING
    none

PARITY_CONSTRAINED_RISK
    none
```

Return only L11-R014. Challenge and agree the characterization, implement discriminating
pending-to-complete witnesses, then return a new exact candidate for another complete review. Do
not implement Rust Layer 11 or start Layer 12.
