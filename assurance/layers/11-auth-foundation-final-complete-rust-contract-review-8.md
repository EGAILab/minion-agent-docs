# Layer 11 Auth Foundation — Eighth Final Complete Independent Rust Contract Review

## Exact target

```text
code PR #25
    769af8be33caff97a5483ee3c3abbb14f8dbbc78

docs PR #54
    914a318dd183cd5257c9931dc223a3150d22a763

seventh complete review
    docs PR #66 @ f976d4c68a59bb4ef338fdc737c6eb65e89617dd

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

Both exact heads were fetched from GitHub, matched issue #24's latest state-bearing comment, and
were open, Ready for Review, unmerged, and remote-reachable. This was a full §11.8.8 review in
the required Pi → spec/manifest/canonical → Rust → assurance → Python order. No candidate,
shared, Python, Rust, or Layer-12 file was modified.

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

`L11-R019` closes for its exact 1.9 ms witness. The epsilon introduced to repair internal
fake-clock drift is applied inside the shared/public flooring helper, where it changes genuine
caller inputs immediately below a whole-millisecond boundary. This creates `L11-R020`, a new
blocking `PI_PARITY_DEFECT`.

## Complete source audit and finding ledger

Re-read pinned Pi auth types, context, credential store, refresh resolution, PKCE, device-code
polling/direct sleep, abort utility, and relevant callers/tests. Node's official timer contract
was rechecked for both invalid-delay normalization and truncation of valid non-integer delays.

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
| L11-R012 | CLOSED for ordinary values not within the new epsilon window; R020 is the new boundary regression. |
| L11-R013 | CLOSED — context resolution/access failure boundary remains correct. |
| L11-R014 | CLOSED — NaN/+infinity poll-loop behavior remains correct. |
| L11-R015 | CLOSED — NaN refresh minimum suppresses refresh. |
| L11-R016 | CLOSED — poll-loop negative infinity resolves to one second. |
| L11-R017 | CLOSED — direct invalid delays receive host-minimum normalization. |
| L11-R018 | CLOSED — direct timer and poll-loop boundaries remain distinct in the spec. |
| L11-R019 | CLOSED for the exact witness — direct 1.9 ms truncates to 1 ms. |
| L11-R020 | OPEN — epsilon-tolerant flooring rounds genuine just-below-boundary inputs upward, unlike Pi/Node truncation. |

## L11-R019 closure

The direct `abortable_sleep(0.0019)` witness now observes `0.001` seconds. Invalid-range handling
remains correct, and the canonical expiry scenario no longer performs an extra poll. R019 is
closed on its stated behavior.

## L11-R020 — global epsilon changes genuine public inputs

Classification: `PI_PARITY_DEFECT`.

The candidate changed the shared `_floor_to_whole_milliseconds` operation from:

```text
floor(seconds * 1000) / 1000
```

to:

```text
floor(seconds * 1000 + 0.000001) / 1000
```

That epsilon is intended to repair accumulated floating-point error in an internally derived
deadline remainder. It is also applied to raw direct-sleep inputs and caller/server poll
intervals. The assurance claim that it is smaller than any genuine fractional delay a caller can
pass is false: the public float domain has no such minimum spacing around millisecond boundaries.

### Minimal discriminating witness

```text
finding
    L11-R020

Pi/source basis
    direct abortableSleep forwards 1.9999995 ms to Node setTimeout
    Node truncates valid non-integer delays toward zero

setup
    call direct abortable_sleep with 0.0019999995 seconds
    signal absent
    injected sleep records requested duration

pinned Pi / Node
    trunc(1.9999995 ms) = 1 ms

candidate
    floor(1.9999995 + 0.000001) = 2 ms
    recorded delay = 0.002 seconds

why discriminating
    the value is a genuine representable caller input just below 2 ms, not accumulated clock
    drift; the epsilon changes the integer timer bucket
```

The executable exact-candidate probe observed `[0.002]`; the pinned host normalization is
`Math.trunc(1.9999995) == 1`.

The same helper also governs `L11-R012` caller/server interval flooring, so this is not confined
to the direct helper. For example, an initial interval just below an integer-millisecond boundary
can be rounded upward although Pi's explicit `Math.floor` rounds it downward.

Narrow remediation: keep exact flooring/truncation for every public/caller-provided value. Isolate
the numerical robustness treatment to the internally derived deadline remainder, or redesign the
fake-clock/sleep accounting so it does not require altering public normalization. Add the exact
just-below-boundary witness and correct PROV-010's claim that the epsilon cannot mask genuine
fractional input. Do not replace the fixed epsilon with another global tolerance.

## Contract, evidence, and Rust feasibility

The normative spec's exact flooring/truncation statements are Pi-correct. The Python
implementation violates them in the epsilon window, while PROV-010 incorrectly classifies the
global epsilon as parity-neutral. The manifest otherwise validates as 92 rows / 92 unique ids;
PROV-011 through PROV-013 remain explicit deferred parity.

Six auth-device canonical scenarios pass through the real poller and the runner remains thin.
Their finite values do not discriminate R020. Rust Layers 01-10 require no reopening, but Rust
must not copy this Python-only global tolerance into its public normalization.

## Fresh gates

```text
full pytest
    1296 passed, 19 xfailed, 0 failed

production-source coverage
    100%

ruff check
    PASS

mypy
    PASS, 69 files including permanent typing fixtures

focused auth/schema/manifest/layering
    333 passed

auth-device canonical
    6 passed

manifest
    92 rows, 92 unique ids

format check
    same 7 pre-existing drift files
```

No other active parity, contract-assurance, or Pi-uncertainty finding was found.

## Required next action

Return only `L11-R020` to the shared/Python owner as a narrow numerical-boundary correction.
Separate exact public normalization from internal deadline-drift handling and add the exact
just-below-boundary witness. Any changed candidate SHA requires another complete §11.8.8 review.
Do not implement Rust Layer 11 and do not start Layer 12.
