# Layer 11 Auth Foundation — Tenth Final Complete Independent Rust Contract Review

## Exact target

```text
code PR #25
    78e6fbf0b04fea377b0ee9a71ad917b98fe06f04

docs PR #54
    5f7e1a17a9f8f033e5a1f9f32801f2bc266bb48c

ninth complete review
    docs PR #68 @ 82ca8a7b58f0c5fdb584060ecbe7ab5176fcd51d

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

Both exact candidate heads were fetched from GitHub, matched issue #24's latest state-bearing
comment, and were open, Ready for Review, unmerged, and remote-reachable. This was a complete
§11.8.8 review in the required Pi → spec/manifest/canonical → existing Rust architecture →
assurance → Python order. No candidate, shared, Python, Rust, or Layer-12 file was modified.

The separate process-only retrospective PR #69 was also inspected. It changes only
`process/agent-workflow.md`, accurately captures the recurring test-double-drift failure mode,
and does not alter Layer-11 semantics or this exact-SHA approval target.

## Verdict

```text
shared Layer-11 Auth Foundation contract
    APPROVED FOR RUST IMPLEMENTATION

Python Layer 11 Pass 1
    CERTIFIED

Rust Layer 11
    NOT_IMPLEMENTED

Layer 11 cross-language
    NOT CLOSED

Layer 12
    NOT STARTED
```

`L11-R021` closes. All production scheduling arithmetic is tolerance-free; the exact fractional
expiry witness now follows Pi/Node's whole-millisecond truncation, while the earlier deterministic
clock regression is fixed only in the two fake clocks that manufactured accumulated float drift.
No active `PI_BEHAVIOR_UNCERTAIN`, `PI_PARITY_DEFECT`, or `CONTRACT_ASSURANCE_DEFECT` remains in
this Layer-11 slice.

## Complete source audit and finding ledger

Re-read pinned Pi auth types, default context, credential store, refresh resolution, PKCE,
device-code polling/direct sleep, abort utility, and relevant callers. Rechecked the complete
Layer-11 Pass-1 spec, PROV-006 through PROV-013, all six auth-device canonical scenarios and their
schema/runner, the assurance lineage, and certified Rust Runtime/LLM/Agent seams through Layer 10.

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
| L11-R012 | CLOSED — caller/server intervals use exact whole-millisecond flooring. |
| L11-R013 | CLOSED — context resolution/access failure boundary remains correct. |
| L11-R014 | CLOSED — NaN/+infinity poll-loop behavior remains correct. |
| L11-R015 | CLOSED — NaN refresh minimum suppresses refresh. |
| L11-R016 | CLOSED — poll-loop negative infinity resolves to one second. |
| L11-R017 | CLOSED — direct invalid delays receive host-minimum normalization. |
| L11-R018 | CLOSED — direct timer and poll-loop boundaries remain distinct in the spec. |
| L11-R019 | CLOSED — direct valid fractional delays truncate to whole milliseconds. |
| L11-R020 | CLOSED — public/direct flooring has no epsilon. |
| L11-R021 | CLOSED — deadline remainder has no epsilon; fake-clock drift is test-local. |

## L11-R021 closure

The production `_snap_deadline_remainder_to_whole_milliseconds` helper is removed. Both deadline
paths pass their exact computed remainder into `abortable_sleep`, whose valid-delay normalization
uses the same exact whole-millisecond flooring as every other delay. No epsilon or tolerant
rounding remains under `src/minion_agent/auth`.

The required exact witness now observes:

```text
expires_in_seconds
    0.0019999995

wait_before_first_poll
    true

requested sleep
    0.001 seconds

poll attempts
    1

result
    complete
```

An independent executable probe against the exact candidate produced:

```text
{'result': 'ok', 'sleeps': [0.001], 'total': 0.001, 'now': 0.001}
```

The deterministic canonical expiry regression remains green because `FakeClock` and
`_InstantClock` now round their own accumulated elapsed counters to nanosecond precision. That is
test infrastructure, not production behavior. The runner still delegates interval, deadline,
backoff, and polling decisions to the real `poll_device_code_flow`; it does not implement those
semantics itself.

## Manifest, canonical evidence, and Rust feasibility

PROV-006 through PROV-010 each have coherent adopted rules and concrete Python evidence.
PROV-011 through PROV-013 remain explicit deferred parity with named closure criteria and no
fabricated evidence. All `tests` fields are lists. The manifest validates as 92 rows / 92 unique
ids.

The auth-device schema permits the contract's positive numeric interval/expiry domain. Six
language-neutral scenarios execute the real poller through a thin scripted-transport and fake-clock
boundary. Timing precision and cancellation remain appropriately covered by language tests rather
than simulated by the canonical runner.

Certified Rust Layers 01-10 require no semantic delta. Rust can independently implement the auth
vocabulary, per-provider serialized store, composed cooperative refresh signal, PKCE, and
device-code state machine with typed APIs and Rust-native timing/ownership. It need not reproduce
Python's sliced-sleep or fake-clock mechanics. Deferred provider-specific/network behavior remains
outside this Pass-1 slice.

## Contract-quality answers

```text
canonical runner simulates production retry/backoff/deadline semantics
    NO

Python workaround remains in production solely for test infrastructure
    NO

two conforming implementations may choose observably different timer normalization
    NO

earlier certified layer requires reopening
    NO

Rust must consult Python mechanics to implement the contract
    NO

unapproved observable divergence
    NONE
```

## Fresh gates

```text
full pytest
    1298 passed, 19 xfailed, 0 failed

production-source coverage
    100% (3152 statements, 0 missed)

ruff check
    PASS

mypy
    PASS, 69 files including all permanent typing fixtures

focused auth/schema/manifest/layering
    335 passed

auth-device canonical
    6 passed

manifest
    92 rows, 92 unique ids

format check
    same 7 pre-existing drift files
```

## Findings

```text
PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    none

CONTRACT_ASSURANCE_DEFECT
    none

PARITY_CONSTRAINED_RISK
    none

PARITY_NEUTRAL_HARDENING
    test-only fake clocks round their own accumulated elapsed counters, preserving production semantics
```

## Required next action

Merge the exact approved code/docs candidates under the repository squash policy, merge this
review evidence, update issue #24 to `STATUS = RUST_IMPLEMENTATION` / `NEXT_OWNER = Codex`, and
begin Rust Layer-11 Pass-1 implementation only in a separate implementation pass. Do not start
Layer 12.
