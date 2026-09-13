# Layer 11 Auth Foundation — Fifth Final Complete Independent Rust Contract Review

## Exact review target and control state

```text
code PR #25
    e61eedc9684d61529f4ef9c0eeb9c0c9621d1bbb

docs PR #54
    ced9a36d252eee42904345962dd96d82ce6c38a6

fourth complete review
    docs PR #63 @ 3698582a40df491afb888094b6e725dfd0bffcb1

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

Both candidate heads were fetched from GitHub, were remote-reachable, open, Ready for Review,
and unmerged. The latest coordination comment on issue #24 records these exact heads,
`STATUS = RUST_CONTRACT_REVIEW`, and `NEXT_OWNER = Codex`. (The issue description itself retains
an older convergence snapshot; the latest state-bearing comment is the current handoff.) This
verdict applies only to the two exact candidate SHAs above.

This was a new complete `agent-workflow.md` §11.8.8 audit, not a targeted check. Review order was
pinned Pi, normative spec, manifest, canonical evidence, certified Rust architecture, assurance,
then Python as secondary implementation evidence. No candidate branch, shared semantic file,
Python file, Rust file, or Layer-12 file was modified.

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

The candidate closes the fourth review's stated NaN, positive-Infinity, and NaN-refresh
witnesses. The full special-number audit found one adjacent, executable Pi mismatch: the code and
contract apply the new one-millisecond fallback to **negative** infinity too, while pinned Pi's
preceding `Math.max(1000, ...)` converts negative infinity to the ordinary one-second minimum.
This is `L11-R016`, a blocking `PI_PARITY_DEFECT` on the already-active L11-R014 convergence
surface.

## Independent pinned-Pi audit

Re-read directly at the pinned revision:

- `packages/ai/src/auth/types.ts`
- `packages/ai/src/auth/context.ts`
- `packages/ai/src/auth/credential-store.ts`
- `packages/ai/src/auth/resolve.ts`
- `packages/ai/src/auth/oauth/pkce.ts`
- `packages/ai/src/auth/oauth/device-code.ts`
- `packages/ai/src/utils/abort.ts`
- relevant auth/model tests and call sites

The audit reconfirmed the credential vocabulary and live-reference behavior, credential-store
serialization/cancellation, context tilde/error behavior, refresh authority, PKCE derivation, and
device polling state machine. There is no Pi uncertainty for the open finding: the relevant
calculation is directly visible at `device-code.ts:51-54`.

## Complete finding ledger

| Finding | Exact-candidate result |
|---|---|
| L11-R001 | CLOSED — the per-provider FIFO task chain, queued pre-task check, post-callback discard, prompt caller race, and pruning remain represented and tested. |
| L11-R002 | CLOSED — refresh receives the combined caller-or-15-second-timeout signal. |
| L11-R003 | CLOSED — blank normalization is still default-context-only, not a protocol rule. |
| L11-R004 | CLOSED — server slow-down override is accepted only when finite and positive. |
| L11-R005 | CLOSED — the generic auth/provider orchestration vocabulary has an explicit deferred owner and closure criterion. |
| L11-R006 | CLOSED — credential mappings retain live, mutable reference semantics, including durable static-typing evidence. |
| L11-R007 | CLOSED — current-entry insertion order remains normative and tested. |
| L11-R008 | CLOSED — leading-tilde support remains protocol-owned. |
| L11-R009 | CLOSED — credential scalar fields remain reassignable. |
| L11-R010 | CLOSED — API-key `env` is flat string-to-string while OAuth `extra` is open recursive JSON. |
| L11-R011 | CLOSED — one effective validity threshold drives trigger, locked recheck, and explicit-minimum post-validation. |
| L11-R012 | CLOSED — ordinary finite initial/server intervals are floored to whole milliseconds before the minimum. |
| L11-R013 | CLOSED — default file existence uses literal leading-tilde concatenation and one whole-operation ordinary-exception boundary. |
| L11-R014 | CLOSED for its stated NaN and positive-Infinity witnesses — unused values do not fail setup; used values progress at 1 ms. The broader wording exposed L11-R016. |
| L11-R015 | CLOSED — explicit NaN minimum propagates through the effective threshold and suppresses refresh. |
| L11-R016 | OPEN — negative infinity is incorrectly routed to the 1 ms invalid-timer fallback instead of Pi's ordinary 1-second minimum. |

## L11-R014 and L11-R015 remediation verification

For NaN and positive infinity, the candidate now preserves the arithmetic value until the sleep
boundary and schedules the next fake-clock poll after `0.001` seconds. The nested NaN
slow-down-fallback path is also kept non-finite until that boundary. Those tests are
discriminating against the rejected one-second candidate.

`refresh_if_expiring` now uses a dedicated JavaScript-style maximum operation. With a stored
credential expiring at 120000 ms, `now = 0`, and an explicit NaN minimum, the effective threshold
is NaN, no expiry comparison succeeds, the refresh callback is not invoked, and the original
credential is returned. That matches pinned Pi.

The new implementation and normative prose therefore close the two findings exactly as raised by
the fourth review; the rejection is for the newly exposed negative-infinity branch, not a
re-litigation of those witnesses.

## L11-R016 — negative infinity is not an invalid host-timer delay in pinned Pi

Classification: `PI_PARITY_DEFECT`.

Pinned Pi computes its initial interval before any host timer is called:

```text
intervalMs = Math.max(1000, Math.floor(intervalSeconds * 1000))
```

The three relevant special values do not share one result:

```text
NaN        -> Math.max(1000, NaN)       -> NaN       -> host timer clamps to 1 ms
+Infinity  -> Math.max(1000, +Infinity) -> +Infinity -> host timer clamps to 1 ms
-Infinity  -> Math.max(1000, -Infinity) -> 1000      -> ordinary 1000 ms timer
```

The candidate instead bypasses `max` for every value for which `math.isfinite` is false. It
therefore carries `-Infinity` into `abortable_sleep`, whose blanket non-finite rule clamps it to
`0.001` seconds. The contract's general “non-finite” wording makes the same incorrect collapse.

### Minimal discriminating witness

```text
finding
    L11-R016

Pi/source basis
    device-code.ts:51-54 applies Math.max(MINIMUM_INTERVAL_MS, floor(value))
    before device-code.ts:94 calls abortableSleep/setTimeout

setup
    initial interval = negative infinity
    no expiry deadline
    first poll = pending
    second poll = complete("token")
    injectable clock records requested sleep

expected pinned-Pi observation
    poll count = 2
    elapsed/requested delay = 1.000 seconds

exact candidate observation
    poll count = 2
    elapsed/requested delay = 0.001 seconds

why discriminating
    both runs complete, but the candidate schedules the retry one thousand times earlier;
    no scheduler precision or progress-only argument can erase the explicit arithmetic split
```

The executable Python probe against the exact candidate returned `ok 0.001 2`; the pinned
JavaScript arithmetic probe returned `1000 1000` for the normalized/requested milliseconds.

Narrow remediation: revise the L11-R014 convergence characterization to distinguish NaN and
positive infinity from negative infinity. Preserve negative infinity through `Math.floor` but
still apply the ordinary minimum operation, yielding one second. Add the exact
`negative-infinity -> pending -> complete` witness as permanent evidence and update PROV-010 and
`spec/auth.md` without weakening the already-correct NaN/positive-Infinity rule. No lower-layer
change is required.

## Manifest, spec, canonical evidence, and Rust feasibility

The manifest parses as 92 rows with 92 unique ids. Layer-11 rows PROV-006 through PROV-010 remain
`adopted`; PROV-011 through PROV-013 remain explicit `deferred parity`. R014/R015 evidence pointers
and disposition wording are structurally valid, but PROV-010's adopted special-number rule is
semantically incomplete because it groups all non-finite initial intervals together.

The six auth-device-code scenarios validate and pass through the real
`poll_device_code_flow` seam. The runner only scripts poll outcomes, supplies an advancing clock,
and normalizes the terminal observation; it does not implement retry/backoff/deadline decisions.
Special-number timing remains explicit Python language evidence, which is a reasonable boundary,
but it presently lacks the negative-infinity witness.

The certified Rust tree has no Layer-11 auth implementation yet. Its existing typed cancellation
and async foundations can support the contract without changing Layers 01-10. Rust can implement
the credential/store/context/PKCE surfaces independently. It cannot faithfully implement
PROV-010 until the shared initial-interval rule distinguishes the three special-number outcomes;
copying the current blanket “non-finite -> 1 ms” wording would reproduce the known Pi defect.

## Fresh evidence and gates

Executed against the exact code candidate with that worktree's source on `PYTHONPATH`:

```text
full pytest
    1291 passed, 19 xfailed, 0 failed

production-source coverage
    100% (all minion_agent source modules; the combined source+test table rounds to 99%)

ruff check
    PASS

mypy
    PASS, 69 files including all three permanent typing fixtures

focused auth/schema/manifest/layering set
    328 passed

auth-device canonical
    6 passed

manifest
    92 rows, 92 unique ids

ruff format --check
    same 7 pre-existing drift files; no new drift attributable to this candidate
```

Green tests do not override L11-R016 because the negative-infinity branch has no permanent
witness. No other active `PI_PARITY_DEFECT`, `CONTRACT_ASSURANCE_DEFECT`, or
`PI_BEHAVIOR_UNCERTAIN` was found in the complete review.

## Required next action

Return the narrow L11-R016 correction to the shared/Python owner. Any changed candidate SHA needs
another complete §11.8.8 exact-SHA review because this is a final-complete-review rejection. Do
not implement Rust Layer 11 and do not start Layer 12.
