# Layer 11 Auth Foundation — Ninth Final Complete Independent Rust Contract Review

## Exact target

```text
code PR #25
    10b5b13a9a3c7f8001ffff87cc330cd6907adbee

docs PR #54
    0a51ce99b9b3017cbf6df52e5cfefe4ff042984b

eighth complete review
    docs PR #67 @ 6120bb4c03ff71eeeffee2c064c458f6b2a8485d

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

Both exact heads were fetched from GitHub, matched issue #24's latest state-bearing comment, and
were open, Ready for Review, unmerged, and remote-reachable. This was a complete §11.8.8 review
in the required Pi → spec/manifest/canonical → existing Rust architecture → assurance → Python
order. No candidate, shared, Python, Rust, or Layer-12 file was modified.

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

`L11-R020` closes: genuine caller/server/direct delays once again use exact truncation, and the
required direct `1.9999995 ms -> 1 ms` witness passes. The replacement epsilon helper is not,
however, isolated from caller data: a deadline remainder includes the caller's
`expires_in_seconds`. A caller-supplied fractional expiry immediately below a whole-millisecond
boundary is rounded upward before it reaches `abortable_sleep`. This creates `L11-R021`, a new
blocking `PI_PARITY_DEFECT` and paired `CONTRACT_ASSURANCE_DEFECT` in PROV-010's claim that the
remainder is never a genuine external value.

## Complete source audit and finding ledger

Re-read pinned Pi auth types, context, credential store, refresh resolution, PKCE, device-code
polling/direct sleep, abort utility, and relevant callers. Rechecked the complete Layer-11 Pass-1
spec, PROV-006 through PROV-013, all six auth-device canonical scenarios and their schema/runner,
the current assurance lineage, and the certified Rust Runtime/LLM/Agent seams through Layer 10.

| Finding | Exact-candidate result |
|---|---|
| L11-R001 | CLOSED — FIFO store chain and cancellation checkpoints remain correct. |
| L11-R002 | CLOSED — refresh receives combined caller/timeout cancellation. |
| L11-R003 | CLOSED — blank normalization remains default-context-only. |
| L11-R004 | CLOSED — slow-down override requires finite positive input. |
| L11-R005 | CLOSED — generic auth/provider orchestration remains explicitly deferred. |
| L11-R006 | CLOSED — credential values preserve live mutable references. |
| L11-R007 | CLOSED — current-entry insertion order remains normative. |
| L11-R008 | CLOSED — leading-tilde support remains protocol-owned. |
| L11-R009 | CLOSED — scalar credential fields remain mutable. |
| L11-R010 | CLOSED — flat env and recursive extra remain distinct. |
| L11-R011 | CLOSED — one effective validity threshold governs refresh checks. |
| L11-R012 | CLOSED — caller/server intervals use exact whole-millisecond flooring again. |
| L11-R013 | CLOSED — context resolution/access failure boundary remains correct. |
| L11-R014 | CLOSED — NaN/+infinity poll-loop behavior remains correct. |
| L11-R015 | CLOSED — NaN refresh minimum suppresses refresh. |
| L11-R016 | CLOSED — poll-loop negative infinity resolves to one second. |
| L11-R017 | CLOSED — direct invalid delays receive host-minimum normalization. |
| L11-R018 | CLOSED — direct timer and poll-loop boundaries remain distinct in the spec. |
| L11-R019 | CLOSED — direct valid fractional delays truncate to whole milliseconds. |
| L11-R020 | CLOSED — the public flooring helper is exact and the near-boundary direct witness passes. |
| L11-R021 | OPEN — the tolerant deadline-remainder helper still rounds caller-supplied fractional expiry upward. |

## L11-R020 closure

`_floor_to_whole_milliseconds` is restored to exact
`floor(seconds * 1000) / 1000`. Caller intervals, finite positive server intervals, and direct
`abortable_sleep` inputs no longer share the epsilon. The permanent direct
`abortable_sleep(0.0019999995)` witness observes `0.001` seconds, and the prior canonical expiry
scenario remains green. PROV-010 explicitly corrects the prior epsilon-neutrality claim.

## L11-R021 — deadline remainder is not purely internal data

Classification: `PI_PARITY_DEFECT` + `CONTRACT_ASSURANCE_DEFECT`.

The new `_snap_deadline_remainder_to_whole_milliseconds` helper computes:

```text
floor(remaining_seconds * 1000 + 0.000001) / 1000
```

and is called in both deadline-capped sleep paths. The implementation and PROV-010 describe
`remaining = deadline - now()` as an internal value that can never contain a genuine external
fraction. That premise is false. `deadline` is constructed directly from the public
`expires_in_seconds`; pinned Pi likewise computes:

```text
deadline = Date.now() + expiresInSeconds * 1000
remainingMs = deadline - Date.now()
abortableSleep(min(intervalMs, remainingMs), ...)
```

`expiresInSeconds` is a `number`, not an integer-only value. With a stable clock, a fractional
expiry therefore survives into `remainingMs` unchanged. Pi passes that value to `setTimeout`,
whose valid non-integer delay is truncated toward zero. The candidate first applies its epsilon
and can move the value into the next millisecond bucket.

### Minimal discriminating witness

```text
finding
    L11-R021

Pi/source basis
    pollOAuthDeviceCodeFlow computes its deadline from public expiresInSeconds
    and sends the resulting remainingMs to abortableSleep without epsilon snapping

minimal setup
    interval_seconds = 5
    expires_in_seconds = 0.0019999995
    wait_before_first_poll = true
    stable injected clock at 0
    injected sleep records its requested duration
    first poll returns complete

Pi / Node
    remainingMs = 1.9999995
    setTimeout truncates it to 1 ms

candidate
    tolerant remainder helper maps 1.9999995 ms to 2 ms
    recorded sleep = 0.002 seconds

why discriminating
    the fractional part originates in the public expiry input, not clock-summation drift;
    moving it across the timer bucket is observable before the first poll
```

The executable probe against the exact candidate produced:

```text
{'result': 'ok', 'sleeps': [0.002], 'total': 0.002}
```

The expected Pi-equivalent requested sleep is `0.001` seconds.

Narrow remediation: remove tolerance from any value that may retain caller-supplied fractional
expiry information. Fix the fake-clock/sliced-sleep drift without changing the semantic deadline
value — for example by making the injected clock/accounting model preserve the intended timer
ticks, or by applying a correction only when its provenance proves the remainder should be an
exact millisecond. Add the exact expiry witness above. Correct PROV-010 and the helper docstring's
claim that deadline remainder is never genuine external input. Do not introduce another blanket
epsilon over all deadline remainders.

## Contract, canonical evidence, and Rust feasibility

The schema correctly permits positive fractional `expires_in_seconds`, so it does not rescue the
candidate by narrowing expiry to integers. The six canonical scenarios pass through the real
poller and the runner remains thin, but none uses a fractional expiry near a millisecond boundary;
they do not discriminate R021.

PROV-006 through PROV-009 remain coherent and implemented. PROV-011 through PROV-013 remain
explicit deferred parity with closure criteria and no fabricated evidence. PROV-010's primary
state-machine rules are coherent, but its L11-R020 correction overclaims the provenance of the
remainder and therefore does not yet provide a stable independently implementable deadline rule.

Certified Rust Layers 01-10 need no semantic delta. Rust can implement the auth vocabulary,
store, refresh, PKCE, and ordinary device-flow state machine idiomatically using its existing
typed and poll-based seams. It must not copy the Python epsilon workaround. Rust Layer 11 remains
blocked until the shared/Python expiry-boundary rule is corrected.

## Fresh gates

```text
full pytest
    1297 passed, 19 xfailed, 0 failed

production-source coverage
    100% (3158 statements, 0 missed)

ruff check
    PASS

mypy
    PASS, 69 files including all permanent typing fixtures

focused auth/schema/manifest/layering
    334 passed

auth-device canonical
    6 passed

manifest
    92 rows, 92 unique ids

format check
    same 7 pre-existing drift files
```

No other new active parity, contract-assurance, or Pi-uncertainty finding was found.

## Required next action

Return only `L11-R021` to the shared/Python owner as the next narrow numerical-boundary
correction. Preserve exact caller-derived fractional expiry behavior while solving the
implementation-only clock-drift regression. Any changed candidate SHA requires another complete
§11.8.8 review. Do not implement Rust Layer 11 and do not start Layer 12.
