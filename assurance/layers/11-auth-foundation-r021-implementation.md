# Layer 11 — L11-R021 implementation

## Candidates

```text
prior rejected candidate (ninth final-complete review)
    code 10b5b13a9a3c7f8001ffff87cc330cd6907adbee (L11-R020 fix)
    docs 0a51ce99b9b3017cbf6df52e5cfefe4ff042984b (L11-R020 implementation record)
    docs PR #68 @ 82ca8a7b58f0c5fdb584060ecbe7ab5176fcd51d

ninth final-complete review (rejecting)
    review-worktrees/l11-final9-evidence/assurance/layers/11-auth-foundation-final-complete-rust-contract-review-9.md
    (Codex's own review branch/PR #68 -- not merged into this branch; referenced by SHA only)
```

## §11.8 trigger-check statement

Layer 11's "three rejected reviews" trigger has been continuously active since the fifth review
(nine rejections accumulated). `L11-R021` is a first occurrence, found on the SAME
deadline-remainder surface `L11-R019`/`L11-R020` have now BOTH tried and failed to fix -- this is
the THIRD consecutive rejection on this exact surface, which independently also crosses the
"same finding survives two reviews" trigger in substance (not the identical finding ID, but the
identical underlying design mistake: adding tolerance to `poll_device_code_flow`'s own scheduling
arithmetic). This document proceeds as a continuation of the same special-number/boundary-precision
convergence episode, but this time resolves it by REMOVING the tolerance-in-production-code
approach entirely, rather than attempting a fourth narrower variant of the same flawed design.

## What the ninth review found, and why it is correct

`L11-R020`'s own fix moved the epsilon tolerance out of the shared `_floor_to_whole_milliseconds`
helper and into a new, narrowly-named `_snap_deadline_remainder_to_whole_milliseconds`, reasoning
that `poll_device_code_flow`'s own `remaining = deadline - now()` is "internally derived" and
therefore safe to snap. That reasoning has a hole: `remaining` is not reliably internal OR
drift-affected -- it is exactly `deadline - now()`, and on a FIRST computation (before any sleep has
happened, e.g. `wait_before_first_poll=True` with a short `expires_in_seconds`), `now()` has not
advanced by any summation at all, so `remaining` is arithmetic-identical to the caller's own supplied
`expires_in_seconds` -- a genuine public value with zero drift. The review's own reproduction
(`expires_in_seconds=0.0019999995`, `wait_before_first_poll=True`, stable clock) is exactly this
case: no sleep has occurred, `remaining` equals the caller's own 1.9999995 ms expiry exactly, and the
narrowly-scoped epsilon still rounded it UP to 2 ms -- pinned Pi's real `setTimeout` truncates it
DOWN to 1 ms.

## Independent re-verification

- Traced the `wait_before_first_poll` branch by hand: `deadline = now() + expires_in_seconds`
  (computed once, before any sleep); `remaining = deadline - now()` (computed immediately after,
  still before any sleep). With `now()` unchanged between these two reads (a stable/fake clock at
  its initial value), `remaining == expires_in_seconds` bit-for-bit -- there is no floating-point
  operation here that could introduce ANY drift, let alone one an epsilon should compensate for.
- Confirmed by direct computation that the previously-restored `_snap_deadline_remainder_to_whole_
  milliseconds(0.0019999995)` returns `0.002`, not `0.001` -- reproducing the review's own claim
  independently.
- Re-examined every call site of `deadline - now()` in the module (the `wait_before_first_poll`
  branch and the main loop's own retry-sleep computation) and confirmed BOTH can, depending only on
  how many sleeps happen to have preceded them, be either a drift-affected internal quantity OR an
  exact copy of a genuine public input -- there is no reliable way to distinguish the two cases from
  the call site alone, because they are literally the same expression evaluated at different points
  in the loop's own lifetime. This confirms no narrowing of WHERE tolerance is applied can fix the
  problem -- the tolerance itself does not belong in this module's production arithmetic at all.
- Re-confirmed the actual source of the drift the two prior revisions were trying to compensate for:
  `tests/auth/test_device_code.py`'s `FakeClock` and `tests/conformance/auth_device_code_runner.py`'s
  `_InstantClock` both advance `elapsed` via repeated `self.elapsed += seconds`, once per
  `abortable_sleep`-internal slice (`poll_interval_seconds`, default `0.05`s) -- a REAL monotonic
  clock (`time.monotonic()`) is read directly and carries no such compounding summation error; this
  drift is entirely a property of these two Python-only test doubles, never of Pi's own real timing
  or of this module's own production scheduling arithmetic.

**Answering the §11.8.4-equivalent checklist:**

- *Is the Pi source mapping correct?* Yes -- `Math.trunc` never rounds to nearest, for any input,
  with no tolerance of any kind; this module's own production arithmetic must match that exactly.
- *Is the behavior matrix complete enough?* Yes -- this finding closes the matrix by establishing
  that NO value this module ever schedules should receive tolerance, regardless of provenance.
- *Are any cases implementation mechanics rather than observable semantics?* The fix itself now
  lives entirely in implementation mechanics (the two fake clocks' own rounding), which is exactly
  the correct place for it -- it was the PRIOR two revisions that incorrectly let a
  mechanics-only concern (test-double drift) leak into observable production semantics.
- *Can both Python and Rust implement the rule idiomatically?* Yes -- a Rust port needs no
  tolerance logic anywhere in its own production scheduling code either; any drift-prone test
  double it builds would carry the equivalent fix in its own test-only code, never in the port
  itself.
- *Does this reopen `L11-R019`'s own core decision?* No -- the decision that a valid delay must
  truncate exactly (no tolerance) is now applied MORE consistently than `L11-R019` originally
  achieved, closing the gap `L11-R020` left open.

## Agreed correction

| Value | Prior (rejected, `L11-R020`) | Corrected |
|---|---|---|
| Caller `interval_seconds` / server `slow_down` interval | exact floor | UNCHANGED, exact floor |
| `abortable_sleep` direct-call delay | exact floor | UNCHANGED, exact floor |
| `poll_device_code_flow`'s own `remaining = deadline - now()` | epsilon-snapped via `_snap_deadline_remainder_to_whole_milliseconds` | tolerance REMOVED entirely; flows to `abortable_sleep` raw, truncated only by the same exact `_floor_to_whole_milliseconds` every other delay uses |
| `expires_in_seconds=0.0019999995`, `wait_before_first_poll=True` (new witness) | rounded UP to `0.002`s (in this exact scenario, overshooting the deadline entirely and timing out with zero poll attempts) | truncates DOWN to `0.001`s |
| `FakeClock`/`_InstantClock`'s own `elapsed` accumulation | plain `+=`, drift-prone over many slices | `round(self.elapsed + seconds, 9)` after every increment |

## Implementation

`device_code.py`:

- `_snap_deadline_remainder_to_whole_milliseconds` REMOVED entirely.
- Both call sites that compute `remaining = deadline - now()` (the `wait_before_first_poll` branch
  and the main loop's own retry-sleep computation) no longer snap it at all -- `remaining` flows to
  `abortable_sleep` exactly as computed, which truncates it via the same exact
  `_floor_to_whole_milliseconds` every other delay in this module uses, with zero tolerance.
- `_floor_to_whole_milliseconds`'s own docstring rewritten to state plainly that it is now the ONLY
  truncation this module performs, applied identically to every delay regardless of provenance, and
  to explain why the drift-compensation concept belongs in test doubles, never in production code.

`tests/auth/test_device_code.py`: `FakeClock.sleep` changed from `self.elapsed += seconds` to
`self.elapsed = round(self.elapsed + seconds, 9)`. New permanent witness
`test_wait_before_first_poll_exact_expiry_remainder_truncates_like_node`: calls
`poll_device_code_flow` with `expires_in_seconds=0.0019999995`, `wait_before_first_poll=True`,
asserting `clock.elapsed == pytest.approx(0.001)` and `poll.call_count == 1`.

`tests/conformance/auth_device_code_runner.py`: `_InstantClock.sleep` given the identical rounding
fix, for the same reason.

**Independently confirmed discriminating by revert-and-confirm (both halves)**:

1. Temporarily reintroduced the old epsilon-snap logic (`math.floor(remaining * 1000 + 1e-6) /
   1000`) at the `wait_before_first_poll` call site while leaving the new witness test in place: it
   failed -- not merely with the wrong sleep duration, but with a full `DeviceFlowTimedOut`, since
   the wrongly-rounded 2 ms sleep overshoots the scenario's own 1.9999995 ms deadline entirely,
   preventing even a single `poll()` call. Restored the fix; the witness (and the full 34-test
   suite) passed.
2. Temporarily reverted `_InstantClock.sleep` back to plain `self.elapsed += seconds`: the
   pre-existing `auth-device-code-expiry-without-slow-down` conformance scenario reproduced the
   EXACT original `L11-R019` regression symptom (`IndexError: list index out of range`, one extra
   unscripted `poll()` call from accumulated drift). Restored the rounding fix; the scenario passed
   again.

## Normative deltas

- `spec/auth.md`: unchanged -- no tolerance concept was ever part of the normative,
  cross-language-observable contract; this finding only removes a Python-implementation-only defect
  that never had spec-level expression.
- `pi-parity-manifest.yaml`: `PROV-010`'s rule text gains a `L11-R021` correction paragraph appended
  after the (now-superseded) `L11-R020` provenance claim, preserving that claim's own history per
  this project's append-only remediation-history convention; test count updated to 34.

## Fresh quality gates

- `tests/auth/test_device_code.py` (targeted, `--no-cov`): 34 passed, 0 failed.
- `tests/conformance/test_auth_device_code_conformance.py` (targeted, `--no-cov`): all scenarios
  passing, including `auth-device-code-expiry-without-slow-down` (re-confirmed via the
  revert-and-confirm pass above).
- `tests/conformance/test_manifest_validation.py`: 8/8.
- Full `pytest` suite (fresh, with coverage): 1298 passed, 19 xfailed (pre-existing, unrelated), 0
  failed.
- Coverage: 100.00% (`TOTAL` 3152 statements, 0 missed).
- `ruff check .`: clean.
- `mypy` (default gate, `files = ["src/minion_agent"]`): clean, 66 source files.
- `mypy` including all three permanent typing fixtures: clean, 69 source files.
- `ruff format --check .`: back to the same pre-existing 7-file drift baseline, no new drift.

## Next action

Push to the same candidate branches, updating PRs #25/#54 in place. `STATUS = RUST_CONTRACT_REVIEW`,
requesting a NEW complete exact-SHA review per §11.8.8. `NEXT_OWNER = Codex`. Do not implement Rust
yet. Do not start Layer 12.
