# Layer 11 Auth Foundation — Seventh Final Complete Independent Rust Contract Review

## Exact target

```text
code PR #25
    35382f5b1a69d50afda4d72ae48b8e1d1970787b

docs PR #54
    37f1cb1bc867f2983d1af3eccaaff71193a26b19

sixth complete review
    docs PR #65 @ b5d1eb909c382b5068a1d82f9c9d16c7e6ec16ef

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

Both exact heads were fetched from GitHub and matched issue #24's latest state-bearing comment.
Both PRs were open, Ready for Review, unmerged, and remote-reachable. The issue assigned
`NEXT_OWNER = Codex` and requested a new complete §11.8.8 review.

This review independently re-read pinned Pi, the full auth spec/manifest/canonical evidence,
existing certified Rust architecture, assurance, and finally Python. No candidate, shared,
Python, Rust, or Layer-12 file was modified.

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

`L11-R017` and `L11-R018` close as raised. The new direct-timer characterization calls itself a
full model of Node's `setTimeout` delay contract but implements only its range clamp, not its
separate non-integer truncation rule. `L11-R019` is therefore a blocking direct-call parity and
contract-evidence defect.

## Independent source audit and complete ledger

Re-read directly at pinned Pi:

- `packages/ai/src/auth/types.ts`
- `packages/ai/src/auth/context.ts`
- `packages/ai/src/auth/credential-store.ts`
- `packages/ai/src/auth/resolve.ts`
- `packages/ai/src/auth/oauth/pkce.ts`
- `packages/ai/src/auth/oauth/device-code.ts`
- `packages/ai/src/utils/abort.ts`
- relevant auth/model tests and callers

The direct timer behavior was also checked against Node's official timer contract: out-of-range
delays are reset to 1 ms **and non-integer delays are truncated to an integer**.

| Finding | Exact-candidate result |
|---|---|
| L11-R001 | CLOSED — FIFO store chaining, all cancellation checkpoints, caller race, discard, and pruning remain correct. |
| L11-R002 | CLOSED — refresh receives caller-or-timeout combined cancellation. |
| L11-R003 | CLOSED — blank normalization is default-context-only. |
| L11-R004 | CLOSED — server slow-down overrides require finite positive values. |
| L11-R005 | CLOSED — deferred generic auth/provider orchestration remains explicitly owned. |
| L11-R006 | CLOSED — credential objects/mappings preserve live mutable references and typing evidence. |
| L11-R007 | CLOSED — current-entry insertion order remains normative. |
| L11-R008 | CLOSED — leading-tilde support remains protocol-owned. |
| L11-R009 | CLOSED — credential scalar fields remain mutable. |
| L11-R010 | CLOSED — flat API-key env and recursive OAuth extra remain distinct. |
| L11-R011 | CLOSED — one effective validity threshold drives all refresh checks. |
| L11-R012 | CLOSED — finite poll-loop intervals floor to whole milliseconds. |
| L11-R013 | CLOSED — default file resolution/access retain the whole-operation failure boundary. |
| L11-R014 | CLOSED — NaN/positive-infinity poll-loop handling remains correct. |
| L11-R015 | CLOSED — explicit NaN refresh minimum suppresses refresh. |
| L11-R016 | CLOSED — poll-loop negative infinity resolves to one second. |
| L11-R017 | CLOSED — raw negative infinity, zero, and negative finite direct sleep inputs now receive the host minimum. |
| L11-R018 | CLOSED — the spec now separates poll-loop normalization from direct exported sleep semantics. |
| L11-R019 | OPEN — direct valid fractional-millisecond delays are not truncated as Node truncates them. |

## L11-R017 / L11-R018 closure

The new `_needs_setimeout_clamp` correctly models Node's inclusive range check after converting
seconds to milliseconds. The three permanent witnesses distinguish the formerly broken raw
negative-infinity, zero, and negative-finite paths, each observing 1 ms. Poll-loop normalization
now uses only its required NaN exception, leaving both infinities to ordinary ordered maximum
semantics. Existing NaN/+infinity/-infinity poll-loop witnesses retain their correct values.

The current spec now clearly names two boundaries:

1. poll-loop arithmetic (`Math.floor` then `Math.max`);
2. independently exported `abortableSleep` passing raw milliseconds to Node's timer.

The prior all-non-finite contradiction is removed. R017 and R018 close.

## L11-R019 — direct valid non-integer milliseconds are not truncated

Classification: `PI_PARITY_DEFECT` and `CONTRACT_ASSURANCE_DEFECT`.

Pinned Pi's exported `abortableSleep` forwards its `ms` argument directly to Node's
`setTimeout`. Node's official contract has two relevant and distinct normalization steps:

```text
out of range / NaN
    set delay to 1 ms

otherwise non-integer
    truncate delay to an integer number of milliseconds
```

The candidate implements only the first. `_needs_setimeout_clamp(0.0019)` converts to `1.9` ms,
finds it within `[1, 2147483647]`, and leaves the original `0.0019` seconds untouched.
`abortable_sleep` consequently asks its injected sleep seam for exactly `0.0019` seconds. Pinned
Pi/Node truncates `1.9` ms to `1` ms.

### Minimal discriminating witness

```text
finding
    L11-R019

Pi/source basis
    device-code.ts:26-43 forwards raw ms to setTimeout
    Node timer contract: non-integer delays are truncated to an integer

setup
    call direct abortable_sleep with 0.0019 seconds (1.9 ms)
    signal absent
    injected sleep records requested duration

pinned Pi / Node
    effective requested delay = 1 ms

candidate
    recorded delay = 1.9 ms

why discriminating
    the value is valid and in range, so all new clamp witnesses pass while this separate
    host-timer normalization step remains absent
```

An executable exact-candidate probe observed `[0.0019]` and total `0.0019`. The spec and PROV-010
describe a “FULL setTimeout bounds check” but never state the adjacent truncation rule; a Rust
implementation would reasonably preserve fractional milliseconds or truncate them and both could
claim the current wording.

Narrow remediation: characterize the complete direct timer normalization once, adding the
1.9-ms-to-1-ms witness and a language-neutral rule equivalent to: apply the invalid-delay clamp,
otherwise truncate valid fractional milliseconds toward zero before scheduling. Keep this direct
rule separate from the already-correct poll-loop flooring. No lower-layer change is required.

## Manifest, canonical evidence, and Rust feasibility

The manifest validates as 92 rows with 92 unique ids. PROV-006 through PROV-010 remain adopted;
PROV-011 through PROV-013 remain deferred with explicit closure criteria. Six auth-device-code
canonical scenarios pass through a thin real-poller runner. Direct special-number/timer behavior
appropriately remains language evidence, but it lacks the valid fractional-millisecond witness.

Rust Layers 01-10 need no reopening. Rust can represent the entire closed auth surface with its
existing typed async/cancellation foundations, but must not implement the incomplete direct timer
rule by copying Python's range-only mechanism.

## Fresh gates

```text
full pytest
    1295 passed, 19 xfailed, 0 failed

production-source coverage
    100%

ruff check
    PASS

mypy
    PASS, 69 files including permanent typing fixtures

focused auth/schema/manifest/layering
    332 passed

auth-device canonical
    6 passed

manifest
    92 rows, 92 unique ids

ruff format --check
    same 7 pre-existing drift files
```

No other active parity, contract-assurance, or Pi-uncertainty finding was found.

## Required next action

Return only `L11-R019` to the shared/Python owner as a narrow continuation of the existing direct
timer convergence surface. Add the exact valid fractional-millisecond witness and complete the
direct `setTimeout` normalization rule. Any changed candidate SHA requires another complete
§11.8.8 review. Do not implement Rust Layer 11 and do not start Layer 12.
