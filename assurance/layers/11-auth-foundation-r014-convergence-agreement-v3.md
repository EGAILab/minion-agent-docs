# Layer 11 — L11-R014/L11-R016 convergence agreement, revision 3

## Decision

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION
```

Exact checkpoint reviewed:

- code PR `EGAILab/minion-agent#25` at `e61eedc9684d61529f4ef9c0eeb9c0c9621d1bbb`;
- docs PR `EGAILab/minion-agent-docs#54` at `ced9a36d252eee42904345962dd96d82ce6c38a6`;
- pinned Pi at `b7bb00b936dbe21b8e160b3e89efdec361846699`;
- revision-2 agreement: `11-auth-foundation-r014-convergence-agreement-v2.md`;
- originating fifth final-complete review: docs PR #64 at
  `a594ac49334241ed842289e714253f38c67b5baf`.

This is revision 3 of the L11-R014 convergence checkpoint. Revision 2's own decision (a non-finite
USED interval clamps to Pi's real host-timer magnitude, one millisecond, via a dedicated
`NON_FINITE_INTERVAL_FALLBACK_SECONDS` constant kept separate from the ordinary polling floor)
remains CORRECT for `NaN` and POSITIVE `Infinity`. What revision 2 got wrong was applying that
SAME one-millisecond clamp to NEGATIVE `Infinity` too -- a genuinely different case pinned Pi
itself treats differently, which this revision (tracked as new finding `L11-R016`) corrects.

## What the fifth review found

Revision 2's own implementation checked `not math.isfinite(seconds)` to decide whether to apply
the one-millisecond host-timer clamp. That predicate is `True` for `NaN`, positive `Infinity`,
AND negative `Infinity` alike -- but pinned Pi's own arithmetic treats negative `Infinity`
completely differently from the other two. `Math.max(MINIMUM_INTERVAL_MS, Math.floor(-Infinity *
1000))` is an ORDINARY numeric comparison: `-Infinity` is a valid, well-ordered number (unlike
`NaN`, which fails every comparison), and it simply LOSES to `MINIMUM_INTERVAL_MS` in the `Math.max`
call, exactly like any other too-small finite value would. The result, `MINIMUM_INTERVAL_MS`
(1000 ms = one second), is an ORDINARY, valid delay by the time it would reach `setTimeout` -- Pi's
own host-timer clamp is never even consulted for this input, because the value is never invalid to
begin with once `Math.max` has already resolved it.

## Challenge pass (§11.8.4)

Independently re-verified, this pass, directly against pinned Pi source and basic IEEE-754/
ECMAScript comparison semantics:

- `packages/ai/src/auth/oauth/device-code.ts:51-53`: `Math.max(MINIMUM_INTERVAL_MS, Math.floor(
  (options.intervalSeconds ?? DEFAULT_POLL_INTERVAL_SECONDS) * 1000))` -- confirmed this is a
  single, ordinary `Math.max` call with no branch or special-case for any particular input value.
- ECMAScript's own `Math.max` specification: returns `NaN` if EITHER argument is `NaN`; otherwise
  returns the numerically larger argument via ordinary IEEE-754 comparison, which DOES correctly
  order negative `Infinity` (it compares as less than every other real number, including a very
  large negative finite number) -- confirmed via direct computation: `max(1000, -Infinity) ==
  1000` in ordinary numeric comparison, in both JavaScript and Python identically (this is NOT one
  of the JS/Python `Math.max`/`max()` behavioral differences `L11-R015` found; that mismatch was
  specific to `NaN`'s own non-orderable comparison behavior, which does not apply to `-Infinity`,
  an ordinarily-orderable value in both languages).
- Confirmed Python's own `max(1.0, float("-inf"))` returns `1.0` -- the SAME correct result Pi's
  own `Math.max` produces, with NO special-casing needed, unlike the `NaN` case `L11-R014`/
  `L11-R015` both had to specifically guard against.

**Answering the §11.8.4 checklist:**

- *Is the Pi source mapping correct?* Yes, confirmed above.
- *Is the behavior matrix complete enough?* Yes, with the addition of the negative-`Infinity` row,
  now explicit: it takes the ORDINARY `max()` branch (matching Pi), not the host-timer-clamp
  branch (which only `NaN`/positive `Infinity` take).
- *Are any cases implementation mechanics rather than observable semantics?* No -- which numeric
  values participate in ordinary comparison (negative `Infinity`, like all finite numbers) versus
  which fail it (`NaN`) or exceed the valid host-timer range (positive `Infinity`) is a genuine
  Pi-observable distinction, not a Python-specific detail.
- *Can both Python and Rust implement the rule idiomatically?* Yes -- `x.is_nan() || x ==
  f64::INFINITY` (Rust) or `math.isnan(x) or x == math.inf` (Python) are both simple, direct
  predicates requiring no special numeric library support.
- *Does this reopen revision 1 or revision 2's own core decision?* No -- the DECISION to clamp
  `NaN`/positive `Infinity` to one millisecond, using a dedicated constant separate from the
  ordinary polling floor, is UNCHANGED. Only the PREDICATE deciding which values receive that
  clamp is corrected.

## Agreed correction

| Observation | Revision 2 (rejected) | Revision 3 (agreed) |
|---|---|---|
| `NaN`, actually used | clamps to `NON_FINITE_INTERVAL_FALLBACK_SECONDS` (0.001s) | UNCHANGED |
| positive `Infinity`, actually used | clamps to `NON_FINITE_INTERVAL_FALLBACK_SECONDS` (0.001s) | UNCHANGED |
| negative `Infinity`, actually used | ALSO clamps to `NON_FINITE_INTERVAL_FALLBACK_SECONDS` (0.001s) -- WRONG | resolves via the ORDINARY `max(MINIMUM_INTERVAL_SECONDS, ...)` branch, yielding `MINIMUM_INTERVAL_SECONDS` (1.0s), matching Pi exactly |

## Agreed implementation and evidence constraints

- introduce a dedicated predicate (`_needs_host_timer_clamp` or equivalent) that is `True` only
  for `NaN` or POSITIVE `Infinity`, `False` for negative `Infinity` and every finite value;
- apply this predicate at ALL THREE call sites revision 2 touched (the `abortable_sleep` clamp
  itself, the initial-interval setup, and the slow_down fallback increment) -- not only the one
  the review's own witness directly exercised, for the same internal-consistency reason revision 2
  itself already established;
- add the required negative-`Infinity` witness (`interval_seconds=float("-inf")`, `pending` then
  `complete`, asserting `clock.elapsed == pytest.approx(1.0)`, NOT `0.001`) as permanent regression
  evidence;
- retain every revision-1/revision-2 witness for `NaN`/positive `Infinity` UNCHANGED (still
  asserting `0.001`) -- this correction narrows the predicate, it does not touch their own cases.

## Scope and feasibility

No certified lower layer needs reopening. This is a pure predicate-precision correction; the
overall clamp-point design (inside `abortable_sleep`, deferred from the pure-arithmetic helper) is
unchanged from revision 1. Rust can implement the corrected predicate trivially. No Rust
implementation is authorized by this document.

## Agreement status

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION

OPEN FINDING
    L11-R014 (revision 3) / L11-R016

CHALLENGE FINDINGS
    (none -- the fifth review's own finding is confirmed correct on independent re-verification)

NEXT OWNER
    Claude

NEXT ACTION
    Implement the corrected predicate at all three affected call sites, add the negative-Infinity
    witness, synchronize spec/manifest, rerun the full suite including every previously-closed
    L11-R001 through L11-R015 test, and return the exact remote candidate for a new complete
    review.
```

This agreement is a convergence checkpoint, not final contract approval or Layer-11 certification.
A new complete exact-SHA review remains mandatory once this fix is implemented.
