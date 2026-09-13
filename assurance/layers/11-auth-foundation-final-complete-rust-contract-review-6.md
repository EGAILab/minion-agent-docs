# Layer 11 Auth Foundation — Sixth Final Complete Independent Rust Contract Review

## Exact target

```text
code PR #25
    d6c3dd47d557f6a1eb2a72daf0b4ae1bf2301c37

docs PR #54
    9cb6f5c570588f05cfbd1babe3883255b0c1732f

fifth complete review
    docs PR #64 @ a594ac49334241ed842289e714253f38c67b5baf

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

The exact candidate heads were fetched from GitHub. Both PRs were open, Ready for Review,
unmerged, and remote-reachable. Issue #24's latest state-bearing comment records these heads,
`STATUS = RUST_CONTRACT_REVIEW`, and `NEXT_OWNER = Codex`.

This was a new complete `agent-workflow.md` §11.8.8 review. It re-read pinned Pi, the whole auth
specification and manifest slice, canonical evidence, certified Rust architecture, assurance,
and only then Python. No candidate, shared, Python, Rust, or Layer-12 file was modified.

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

The candidate correctly closes `L11-R016` at the poll-loop initial-interval boundary. The full
review found that applying the same predicate to the separately exported/direct sleep boundary
creates a different Pi mismatch (`L11-R017`), and that the normative spec retains mutually
incompatible general and negative-infinity rules (`L11-R018`).

## Pi audit and complete finding ledger

Re-read at pinned Pi:

- `packages/ai/src/auth/types.ts`
- `packages/ai/src/auth/context.ts`
- `packages/ai/src/auth/credential-store.ts`
- `packages/ai/src/auth/resolve.ts`
- `packages/ai/src/auth/oauth/pkce.ts`
- `packages/ai/src/auth/oauth/device-code.ts`
- `packages/ai/src/utils/abort.ts`
- relevant auth/model tests and callers

| Finding | Exact-candidate result |
|---|---|
| L11-R001 | CLOSED — per-provider FIFO cancellation checkpoints, caller race, result discard, and pruning remain correct. |
| L11-R002 | CLOSED — refresh receives caller-or-timeout combined cancellation. |
| L11-R003 | CLOSED — blank normalization is default-context-only. |
| L11-R004 | CLOSED — server slow-down overrides require finite positive values. |
| L11-R005 | CLOSED — later generic auth/provider orchestration has an explicit disposition and closure criterion. |
| L11-R006 | CLOSED — credential objects and mappings retain live mutable reference semantics with typing evidence. |
| L11-R007 | CLOSED — current-entry insertion order remains normative. |
| L11-R008 | CLOSED — leading-tilde support remains protocol-owned. |
| L11-R009 | CLOSED — credential scalar fields remain mutable. |
| L11-R010 | CLOSED — flat API-key env and open recursive OAuth extra remain distinct. |
| L11-R011 | CLOSED — one effective validity threshold governs all three refresh checks. |
| L11-R012 | CLOSED — ordinary finite poll intervals floor to whole milliseconds. |
| L11-R013 | CLOSED — default file resolution/access share the correct whole-operation error boundary. |
| L11-R014 | CLOSED for NaN and positive-infinity initial poll-loop behavior. |
| L11-R015 | CLOSED — explicit NaN refresh minimum suppresses refresh. |
| L11-R016 | CLOSED — initial negative infinity now reaches the ordinary one-second minimum. |
| L11-R017 | OPEN — direct `abortable_sleep(-Infinity)` returns without a sleep, unlike pinned Pi's exported `abortableSleep`, whose raw invalid delay is host-clamped. |
| L11-R018 | OPEN — current normative prose first groups every used non-finite interval into the 1 ms rule, then assigns negative infinity 1 second. |

## L11-R016 closure

The new poll-loop witness is valid and discriminating:

```text
initial interval = -Infinity
poll outcomes = pending, complete("token")
candidate observed sleep = 1.000 seconds
pinned Pi = Math.max(1000, Math.floor(-Infinity)) = 1000 ms
```

NaN and positive-infinity witnesses remain at `0.001` seconds, so the correction is scoped and
does not regress `L11-R014`. `L11-R016` is closed.

## L11-R017 — the direct sleep boundary has no preceding Math.max

Classification: `PI_PARITY_DEFECT`.

Pinned Pi exports two distinct operations in `device-code.ts`:

1. `pollOAuthDeviceCodeFlow` normalizes its initial interval with `Math.max(1000, floor(...))`.
2. `abortableSleep(ms, signal, message)` passes its own caller-supplied `ms` directly to
   `setTimeout` with no preceding minimum operation.

Negative infinity therefore behaves differently at the two boundaries. At the poll-loop boundary
it becomes 1000 ms before sleep (the now-fixed `L11-R016`). At the direct sleep boundary it reaches
Node's timer as a raw invalid delay and is clamped by that host timer to its minimal delay.

The candidate uses `_needs_host_timer_clamp` at both boundaries. Because that predicate excludes
negative infinity, `abortable_sleep` sets `remaining = -Infinity`, the `while remaining > 0`
condition is false, and the function completes without invoking its injected sleep even once.

### Discriminating witness

```text
finding
    L11-R017

Pi/source basis
    device-code.ts:26-43 passes raw ms directly to setTimeout

setup
    call the direct/exported sleep helper with negative infinity
    signal is not aborted
    record scheduled sleep calls

pinned Pi
    host timer schedules its minimum delay (approximately 1 ms)

candidate
    injected sleep calls = []
    returns synchronously through a zero-iteration loop

why discriminating
    this bypasses pollOAuthDeviceCodeFlow, so its Math.max normalization cannot be borrowed
```

Fresh probes against the exact candidate and Node produced respectively `[]` and an asynchronously
scheduled timer callback. The fix must use boundary-specific normalization: retain the corrected
poll-loop predicate, but model the direct raw timer boundary independently. Also characterize raw
zero/negative finite delays while repairing this exported seam, because Node applies the same
host-timer minimum to those raw values and the current zero-iteration loop does not.

## L11-R018 — contradictory current normative prose

Classification: `CONTRACT_ASSURANCE_DEFECT`.

`spec/auth.md` currently says:

```text
“A non-finite interval that IS actually used ... clamps ... [to] one millisecond”
```

and explains that `NaN`/`Infinity` both take that path. The later L11-R016 paragraph says negative
infinity is a different case and takes one second. Both statements are current and general; the
first was not narrowed to NaN/positive infinity. A Rust implementer cannot obey both literally.
PROV-010 similarly retains historical/general wording before its correction paragraph, although
the later paragraph makes the intended poll-loop result easier to infer.

Narrow remediation: rewrite the current general rule so its subject is exactly NaN and positive
infinity, with negative infinity stated once as the ordinary-minimum branch. Keep remediation
history in assurance rather than leaving contradictory current normative sentences.

## Manifest, canonical evidence, and Rust feasibility

The manifest validates as 92 rows with 92 unique ids. PROV-006 through PROV-010 remain adopted;
PROV-011 through PROV-013 remain explicit deferred parity. The six auth-device scenarios pass
through the real poll state machine; the runner scripts outcomes and advances a clock without
implementing retry/backoff semantics. Special-number scheduling remains language evidence.

Existing Rust Layers 01-10 need no semantic reopening. The typed async/cancellation foundations
are adequate for auth. Rust can implement the poll-loop distinction idiomatically, but it cannot
implement the full adopted `abortableSleep` surface from the current contradictory/incorrect rule
without guessing or copying the Python mechanism. Rust Layer 11 therefore remains blocked.

## Fresh gates

```text
full pytest
    1292 passed, 19 xfailed, 0 failed

production-source coverage
    100%

ruff check
    PASS

mypy
    PASS, 69 files including all permanent typing fixtures

focused auth/schema/manifest/layering
    329 passed

auth-device canonical
    6 passed

manifest
    92 rows, 92 unique ids

ruff format --check
    same 7 pre-existing drift files
```

Green gates do not cover the direct negative-infinity sleep witness. No other active parity,
contract-assurance, or uncertainty finding was found.

## Required next action

Return `L11-R017` and `L11-R018` to the shared/Python owner as one narrow boundary-separation
remediation on the existing special-number convergence surface. Any new candidate SHA requires
another complete §11.8.8 review. Do not implement Rust Layer 11 and do not start Layer 12.
