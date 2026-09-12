# Layer 11 Auth Foundation — Second Final Complete Independent Rust Contract Review

## Exact target and verdict

```text
code PR #25
    fc78f40f0bb8da50281f6ace607f5f39edb8227d

docs PR #54
    909dcff408ad96a6fd499c1933daa382bd668536

prior final complete review
    docs PR #60 @ 3a32162bf3fb82ab680781927996b644c56169bf

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

Both candidate heads were fetched from GitHub, matched the latest handoff comment on coordination
issue `EGAILab/minion-agent#24`, and were open, Ready for Review, unmerged, and remote-reachable.
This was a new complete `agent-workflow.md` §11.8.8 review, not a targeted check of only the latest
three fixes. No candidate, Rust, or Layer-12 file was modified.

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

## Independence and source audit

Review order remained pinned Pi, normative spec, manifest, canonical scenarios/schema, certified
Rust architecture, assurance, then Python only as implementation evidence. Directly re-read pinned
sources included:

- `packages/ai/src/auth/types.ts`
- `packages/ai/src/auth/context.ts`
- `packages/ai/src/auth/credential-store.ts`
- `packages/ai/src/auth/resolve.ts`
- `packages/ai/src/auth/oauth/pkce.ts`
- `packages/ai/src/auth/oauth/device-code.ts`
- relevant pinned auth/model/device-code tests and call sites

The new candidate diff was also audited against the prior rejected exact SHA before the whole
surface was rechecked.

## Finding closure ledger

| Finding | Result at exact candidate |
|---|---|
| L11-R001 | CLOSED — store queue cancellation and caller-visible race remain correct. |
| L11-R002 | CLOSED — refresh receives the combined caller/timeout signal. |
| L11-R003 | CLOSED — blank normalization remains default-context-only. |
| L11-R004 | CLOSED — server-provided slow-down intervals require finite and positive. |
| L11-R005 | CLOSED — deferred generic auth orchestration remains explicitly owned. |
| L11-R006 | CLOSED — live mutable credential semantics and permanent typing evidence remain intact. |
| L11-R007 | CLOSED — insertion-order listing remains normative and tested. |
| L11-R008 | CLOSED — leading-tilde support remains protocol-level. |
| L11-R009 | CLOSED — scalar credential fields remain reassignable. |
| L11-R010 | CLOSED — API-key env and OAuth extra domains remain correctly separated. |
| L11-R011 | CLOSED — all three expiry checks now reuse Pi's effective threshold; the smaller-than-default witness is discriminating. |
| L11-R012 | CLOSED for the reported finite-fraction defect — both finite interval sources now floor to whole milliseconds. A newly exposed non-finite initial-input regression is L11-R014. |
| L11-R013 | STILL OPEN — exact tilde concatenation is fixed, but the promised whole-operation failure boundary is not. |

## R011/R012 remediation verification

The real candidate now rejects the original R011 witness:

```text
now                         0 ms
explicit minimum            60000 ms
refreshed expiry             120000 ms
effective threshold          300000 ms
result                       OAuthRefreshError
```

`refresh_if_expiring` uses `trigger_validity_ms` for the initial check, under-lock recheck, and
post-refresh check, matching Pi's single `expiresSoon` closure.

For finite `1.2349`-second initial and server-provided intervals, the real candidate schedules
exactly `1.234` seconds in both cases. Spec, PROV-010, implementation, and tests now agree on the
whole-millisecond floor for finite values.

## Blocking findings

### L11-R013 — whole-operation file-existence failure boundary remains incomplete

Classification: `PI_PARITY_DEFECT` (same finding remains open).

Pinned Pi places module loading, home-directory lookup, path transformation, and filesystem access
inside one `try/catch`, returning `false` for every thrown failure.

The candidate performs this operation before its `try`:

```python
resolved = os.path.expanduser("~") + resolved[1:]
```

and catches only `OSError` around `Path.exists`. Therefore the implementation and its own new
normative prose (“the WHOLE operation ... resolves False on ANY error”) disagree.

Fresh executable witnesses against the exact candidate:

```text
os.path.expanduser("~") raises OSError("home unavailable")
    candidate: propagates OSError
    pinned Pi: returns false

Path.exists raises RuntimeError("non-os failure")
    candidate: propagates RuntimeError
    pinned Pi: returns false
```

The committed access-error test covers only an `OSError` raised inside the narrow `try`; it cannot
catch either residual. The `~suffix` concatenation witness itself now passes and remains valid.

Required remediation: put resolution and access in the same failure boundary and catch the
language's ordinary operation-error domain, not only `OSError`. Add both a home-resolution failure
witness and a non-`OSError` access failure witness. Keep the corrected literal concatenation.

### L11-R014 — millisecond helper rejects non-finite initial intervals unlike Pi

Classification: `PI_PARITY_DEFECT` (new).

Pinned Pi's initial interval option is a JavaScript `number` and is not guarded by
`Number.isFinite` (that guard exists only for a server `slow_down` value). JavaScript
`Math.floor`/`Math.max` do not throw for special numeric values:

```text
Infinity   -> Infinity
NaN        -> NaN
-Infinity  -> 1000 ms after the minimum clamp
```

In particular, if the first poll returns `complete`, Pi returns the completed value without ever
sleeping, even when the configured initial interval is `Infinity` or `NaN`.

The new Python `_floor_to_whole_milliseconds` calls `math.floor` unconditionally during setup.
Fresh real-candidate witnesses:

```text
initial interval = Infinity; first poll = complete
    candidate: OverflowError before poll
    pinned Pi: complete value returned

initial interval = NaN; first poll = complete
    candidate: ValueError before poll
    pinned Pi: complete value returned
```

This regression was introduced by the R012 fix. The public Python input is `float | None`; the
spec does not narrow the initial interval to finite values or disposition a stricter Minion input
domain. PROV-010 remains `adopted`.

Required remediation: preserve Pi's non-throwing numeric setup semantics for non-finite initial
values, with at least the immediate-complete `Infinity`/`NaN` witnesses. If the project instead
wants to reject non-finite caller input, that is an observable narrowing requiring an explicit
contract disposition and the normal governance path; it cannot be introduced incidentally by the
floor helper. Keep the finite R012 flooring behavior unchanged.

## Manifest/spec/canonical audit

| Row | Result |
|---|---|
| PROV-006 | FAIL — the normative whole-operation/any-error rule is correct, but Python does not implement it (R013). Other credential/context rules pass. |
| PROV-007 | PASS — store serialization, ordering, mutation, and cancellation remain coherent. |
| PROV-008 | PASS — R011 is fixed; ownership, signal, double-checking, and error classes remain coherent. |
| PROV-009 | PASS — PKCE rule and evidence remain complete. |
| PROV-010 | FAIL — finite flooring is fixed, but unguarded Pi initial-number behavior is narrowed by a throwing helper (R014). |
| PROV-011 | PASS (deferred) — concrete future closure criterion remains explicit. |
| PROV-012 | PASS (deferred) — concrete future closure criterion remains explicit. |
| PROV-013 | PASS (deferred) — generic auth/provider orchestration remains explicitly owned. |

Manifest validation passes with 92 rows / 92 unique IDs. No placeholder is counted as adopted
evidence.

Six auth-device-code canonical scenarios still execute through a thin runner using the real
poller. The runner does not implement interval, retry, deadline, or terminal-result logic. Its
intentional lack of elapsed-time observation means finite flooring and non-finite setup require
language-level evidence unless the canonical observation shape is later extended.

## Rust feasibility and lower-layer impact

The certified Rust architecture still has no Layer-11 auth implementation. It provides typed
signals, Tokio synchronization, deterministic testing support, hashing dependencies, and the
existing canonical-runner conventions needed for an idiomatic implementation.

R013 and R014 require no Layer 01–10 semantic change. Rust can implement the eventual corrected
rules without reading Python mechanics, once the shared/Python candidate is coherent. Rust must
not begin from the present rejected candidate.

## Fresh gates

```text
full Python suite
    1283 passed, 19 xfailed, 0 failed

coverage
    100.00% — 3135 statements, 0 missed

auth + schema + manifest + canonical + layering selection
    320 passed

ruff
    PASS

mypy including all three typing fixtures
    PASS — 69 source files

manifest
    92 rows / 92 unique IDs

Rust candidate files changed
    none
```

Green committed tests do not exercise either residual witness.

## Findings summary and next action

```text
PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    L11-R013 — whole-operation/any-error DefaultAuthContext failure boundary remains incomplete
    L11-R014 — non-finite initial device interval now throws before an immediate successful poll

CONTRACT_ASSURANCE_DEFECT
    none separate from the implementation/evidence contradiction in L11-R013/R014

PARITY_NEUTRAL_HARDENING
    none

PARITY_CONSTRAINED_RISK
    none
```

Return only L11-R013 and L11-R014 to the shared/Python owner. R013 has now survived a second
independent review, so the repeated-finding §11.8 convergence trigger is met for that finding and
must be checked before remediation. R014 is new. Push a new exact candidate and request review;
do not implement Rust Layer 11 or start Layer 12.

## L11-R013 convergence characterization (§11.8.3)

This review also serves as the mandatory characterization checkpoint for the repeated R013
surface. It is **PROPOSED — AWAITING INDEPENDENT CHALLENGE**, not agreed for implementation.

```text
OPEN FINDING
    L11-R013

PI SYMBOLS AUDITED
    packages/ai/src/auth/context.ts::defaultProviderAuthContext.fileExists
    packages/ai/src/auth/types.ts::AuthContext.fileExists

OBSERVABLE RULES
    protocol: leading tilde denotes the user's home
    default implementation: any leading ~ is replaced by literal home+suffix concatenation
    default implementation: resolution and access share one failure boundary
    any ordinary resolution/access failure returns false

BEHAVIOR MATRIX
    ordinary existing path                  -> true
    ordinary absent path                    -> false
    ~suffix with known home+suffix target   -> true
    home resolution raises OSError          -> false
    filesystem access raises OSError        -> false
    filesystem access raises other ordinary exception -> false

MINIMAL EXECUTABLE WITNESSES
    retain the existing ~suffix witness
    add an injected home-resolution OSError witness
    add an injected non-OSError access-failure witness

CURRENT CANDIDATE FAILURES
    home resolution occurs before try and propagates
    except OSError is narrower than the specified/Pi catch

SPEC / MANIFEST / CONFORMANCE DELTAS
    normative spec and PROV-006 already state the correct general rule
    implementation and evidence only need alignment unless challenge finds wording ambiguity
    no canonical schema change required

IMPLEMENTATION CONSTRAINTS
    keep literal home+suffix concatenation
    one failure boundary must enclose both resolution and access
    do not weaken protocol-level leading-tilde ownership

OUT OF SCOPE
    browser-specific always-false behavior (Minion has no browser target)
    provider-specific credential file discovery
    Rust implementation
```

The shared/Python owner must independently challenge this Pi mapping and matrix before coding R013,
then record an agreed checkpoint per §11.8.5. R014 has not triggered convergence and may be handled
as a normal point fix, but both fixes may return as one exact candidate.
