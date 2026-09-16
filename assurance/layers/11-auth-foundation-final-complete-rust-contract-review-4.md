# Layer 11 Auth Foundation — Fourth Final Complete Independent Rust Contract Review

## Exact review target

```text
code PR #25
    bbc06e97e1c0db3b0ece798841c15ea80540d6f8

docs PR #54
    4965f37c2dbbe91682f14244a52ad14c0bbda60e

prior complete review
    docs PR #62 @ 2d9062bded434e10054a7374509efa41ece257db

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

Both candidate heads were fetched from GitHub, matched coordination issue #24, and were open,
Ready for Review, unmerged, and remote-reachable. This was a new complete `agent-workflow.md`
§11.8.8 audit. Review order was pinned Pi, normative spec, manifest, canonical evidence,
certified Rust architecture, assurance, then Python as secondary implementation evidence.

No candidate branch, shared semantic file, Python file, Rust file, or Layer-12 file was modified.

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

L11-R001 through L11-R013 remain closed. The convergence implementation makes the next poll
reachable for L11-R014, but its newly normative one-second delay is an unapproved observable
departure from pinned Pi rather than adopted parity. A new complete-audit finding, L11-R015,
shows the same JavaScript/Python NaN arithmetic asymmetry in OAuth refresh validity.

## Independent pinned-Pi audit

Re-read directly at the pinned revision:

- `packages/ai/src/auth/types.ts`
- `packages/ai/src/auth/context.ts`
- `packages/ai/src/auth/credential-store.ts`
- `packages/ai/src/auth/resolve.ts`
- `packages/ai/src/auth/oauth/pkce.ts`
- `packages/ai/src/auth/oauth/device-code.ts`
- `packages/ai/src/utils/abort.ts`
- relevant `oauth-device-code.test.ts` and `models-runtime.test.ts` call sites

Pinned source still establishes the previously reviewed credential vocabulary/reference behavior,
store serialization and cancellation checkpoints, default context behavior, refresh ownership,
PKCE derivation, and device-code state machine. No source uncertainty remains for either open
finding below.

## Complete finding ledger

| Finding | Exact-candidate result |
|---|---|
| L11-R001 | CLOSED — queued pre-task cancellation, post-callback discard, caller wait race, and chain pruning remain correct. |
| L11-R002 | CLOSED — refresh still receives caller-or-timeout combined cancellation. |
| L11-R003 | CLOSED — blank normalization remains default-context-only. |
| L11-R004 | CLOSED — server slow-down intervals require finite and positive. |
| L11-R005 | CLOSED — deferred auth/provider orchestration has an explicit owner and closure criterion. |
| L11-R006 | CLOSED — credentials remain live and mutable, with permanent typing evidence. |
| L11-R007 | CLOSED — current-entry insertion order remains normative and tested. |
| L11-R008 | CLOSED — leading-tilde support remains protocol-owned. |
| L11-R009 | CLOSED — credential scalar fields remain reassignable. |
| L11-R010 | CLOSED — API-key env and OAuth extra domains remain separated. |
| L11-R011 | CLOSED for finite explicit minima — the same effective threshold drives all three checks. L11-R015 is a distinct non-finite edge. |
| L11-R012 | CLOSED — finite initial/server intervals floor to whole milliseconds. |
| L11-R013 | CLOSED — resolution and access share one ordinary-exception boundary and exact literal tilde concatenation. |
| L11-R014 | STILL OPEN — non-finite used intervals now progress, but the exact one-second rule is an unapproved observable Pi divergence. |
| L11-R015 | OPEN — explicit NaN OAuth minimum validity refreshes in Minion but suppresses refresh in Pi. |

## L11-R014 — convergence implementation changes Pi-visible delay by three orders of magnitude

Classification: `PI_PARITY_DEFECT`.

The implementation correctly closes the prior permanent-hang witness: `abortable_sleep` now checks
`math.isfinite` and both NaN and Infinity eventually reach a second poll. The permanent tests are
genuinely discriminating for that prior failure.

The convergence refinement introduced a different normative rule, however: both special values
must wait exactly `MINIMUM_INTERVAL_SECONDS` (one second). Pinned Pi does not do that:

1. `pollOAuthDeviceCodeFlow` passes the NaN/Infinity delay to exported `abortableSleep` and then
   directly to the host `setTimeout`.
2. Node clamps NaN and out-of-range Infinity delays to one millisecond. A fresh local Node probe
   observed both callbacks promptly and emitted the expected Infinity clamp warning.
3. The candidate's real/fake sleep boundary instead waits exactly one second, and the spec and
   PROV-010 make that exact value normative.

Minimal discriminating witness:

```text
finding
    L11-R014

setup
    initial interval = NaN or Infinity
    first poll = pending
    second poll = complete

pinned Pi / Node
    host setTimeout normalizes the invalid delay to 1 ms; second poll is prompt

candidate
    intervening elapsed fake-clock time is exactly 1.0 second

why discriminating
    both implementations now make progress, but they schedule observably different delays;
    the candidate deliberately asserts the difference rather than inheriting host timing
```

The prior review proposed only the portable progress/non-hang rule and explicitly left exact
host-specific latency non-normative. The shared owner then refined that into an exact one-second
Minion rule without a subsequent independent agreement or owner-approved intentional divergence.
PROV-010 remains `adopted`. Calling Node's exact latency non-normative does not make a deliberate
one-second replacement adopted Pi behavior.

Narrow resolution: either preserve Pi's minimal host-timer normalization as closely as practical
(without making Rust reproduce JavaScript mechanics), or obtain §11.7 governance approval and
record an explicit intentional divergence consistently. If only progress is intended to be
normative, remove the exact one-second assertion from the shared rule/evidence rather than
presenting it as adopted parity.

## L11-R015 — NaN explicit OAuth validity changes refresh ownership behavior

Classification: `PI_PARITY_DEFECT` and `CONTRACT_ASSURANCE_DEFECT`.

Pinned `resolveStoredOAuth` computes:

```text
minimumValidityMs = Math.max(300000, minOAuthValidityMs ?? 0)
expiresSoon = Date.now() + minimumValidityMs >= credential.expires
```

For an explicit `NaN`, ECMAScript `Math.max` returns `NaN`, and every `expiresSoon` comparison is
false. A stored credential is therefore returned without refresh. Python computes
`max(300000.0, NaN)` with ordinary ordered comparisons, returns `300000.0`, and refreshes a
credential within five minutes.

Fresh executable witness against the exact candidate:

```text
finding
    L11-R015

setup
    now = 0 ms
    stored OAuth expiry = 120000 ms
    explicit minimum_validity_ms = NaN
    refresh callback returns a distinct credential

pinned Pi
    effective threshold = NaN
    expiresSoon = false
    refresh calls = 0; original credential returned

candidate
    trigger_validity_ms = 300000
    refresh calls = 1; refreshed credential returned

why discriminating
    the provider mutation authority is invoked in one implementation and not the other
```

The Python public seam accepts `float | None`; spec and PROV-008 neither restrict the value to
finite numbers nor disposition a narrower domain. Their general `max(default, explicit-or-zero)`
wording is insufficient across languages because JavaScript and Python/Rust NaN-max operations
have different semantics. Rust would have to guess whether to preserve NaN, clamp it, or reject it.

Required remediation: state and evidence the pinned NaN behavior, or explicitly narrow the input
domain through an approved divergence. Add the witness above as permanent language evidence. This
finding is new and has not independently triggered convergence.

## Manifest, canonical, and Rust feasibility

| Row | Result |
|---|---|
| PROV-006 | PASS — vocabulary, mutable credential references, env/extra split, and context rules agree. |
| PROV-007 | PASS — serialization, ordering, mutation, and cancellation remain coherent. |
| PROV-008 | FAIL only for L11-R015's explicit-NaN threshold behavior. |
| PROV-009 | PASS — entropy, base64url, and SHA-256 derivation remain complete. |
| PROV-010 | FAIL only for L11-R014's unapproved exact one-second replacement. |
| PROV-011 | PASS (deferred) — Codex account projection has a concrete owner/closure criterion. |
| PROV-012 | PASS (deferred) — browser/device endpoint integration has a concrete owner/criterion. |
| PROV-013 | PASS (deferred) — generic auth orchestration remains explicitly owned. |

Manifest validation passes with 92 rows / 92 unique IDs. No placeholder is counted as implemented
evidence.

Six auth-device-code scenarios remain schema-valid and execute through a thin runner. The runner
constructs typed outcomes and a fake clock, calls the real poller, and normalizes its result; it
does not implement retry, backoff, expiry, or terminal behavior. Special non-JSON floats are
appropriately language-test evidence.

Rust can implement all closed rules using existing typed `RunSignal`, Tokio synchronization,
ordered containers, SHA-256 support, and current conformance conventions. Neither open finding
requires a Layer 01–10 semantic delta. Rust must not begin while the shared special-number rules
are divergent/ambiguous.

## Fresh exact-candidate gates

```text
full Python suite
    1289 passed, 19 xfailed, 0 failed

coverage
    100.00% — 3139 statements, 0 missed

auth + schema + manifest + auth canonical + layering selection
    326 passed

ruff check
    PASS

mypy including all three permanent typing fixtures
    PASS — 69 source files

ruff format --check
    same seven pre-existing drift files; no candidate-owned new drift

manifest
    92 rows / 92 unique IDs

candidate Rust diff
    none
```

Green tests prove the candidate's currently written rules; they do not convert either known
special-number mismatch into Pi parity.

## Findings and next action

```text
PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    L11-R014 — exact one-second non-finite sleep is not pinned Pi's host-timer behavior
    L11-R015 — explicit NaN validity refreshes in Minion but not in pinned Pi

CONTRACT_ASSURANCE_DEFECT
    L11-R015 — accepted NaN input has no language-neutral threshold disposition/evidence

PARITY_NEUTRAL_HARDENING
    none

PARITY_CONSTRAINED_RISK
    none
```

Return only L11-R014 and L11-R015. R014 remains in convergence; challenge the exact-delay
classification or seek owner approval before another implementation. Characterize and remediate
R015 with its executable witness. Then return one new exact remote candidate for another complete
review. Do not implement Rust Layer 11 or start Layer 12.
