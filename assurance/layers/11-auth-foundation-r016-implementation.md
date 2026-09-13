# Layer 11 — L11-R016 (§11.8 convergence revision 3) implementation

## Candidates

```text
prior rejected candidate
    code e61eedc9684d61529f4ef9c0eeb9c0c9621d1bbb
    docs ced9a36d252eee42904345962dd96d82ce6c38a6

fifth final-complete review
    docs PR #64 @ a594ac49334241ed842289e714253f38c67b5baf

convergence agreement (L11-R014/L11-R016, revision 3)
    assurance/layers/11-auth-foundation-r014-convergence-agreement-v3.md
```

## Implementation

`device_code.py`: new `_needs_host_timer_clamp(seconds: float) -> bool` predicate --
`math.isnan(seconds) or seconds == math.inf` -- explicitly `False` for negative `Infinity` (and
every finite value), `True` only for `NaN` or positive `Infinity`. Replaces the overly broad
`not math.isfinite(...)` check at all three affected call sites:

1. `abortable_sleep`'s own clamp (`if _needs_host_timer_clamp(seconds): seconds =
   NON_FINITE_INTERVAL_FALLBACK_SECONDS`) -- negative `Infinity` now falls through to the ordinary
   `while remaining > 0` loop, which already treats a non-positive duration as "no wait needed"
   with no further change required.
2. The initial-interval setup (`interval = _initial_floored if _needs_host_timer_clamp(...) else
   max(MINIMUM_INTERVAL_SECONDS, _initial_floored)`) -- negative `Infinity` now takes the ordinary
   `max()` branch, which Python's own plain `max()` already resolves correctly to
   `MINIMUM_INTERVAL_SECONDS` (unlike `NaN`, negative `Infinity` participates normally in ordering
   comparisons).
3. The slow_down fallback increment (same pattern) -- `interval` can never actually BE negative
   `Infinity` at this call site in practice (already resolved ordinarily at setup), but uses the
   same predicate for correctness-by-construction rather than relying on that invariant.

`NON_FINITE_INTERVAL_FALLBACK_SECONDS`'s own docstring extended with a paragraph explicitly
excluding negative `Infinity` and cross-referencing the new predicate's own docstring for the
exact reasoning.

New test `test_negative_infinity_used_for_a_pending_response_clamps_to_the_rfc_floor`:
`interval_seconds=float("-inf")`, `pending` then `complete`, asserts `poll.call_count == 2` and
`clock.elapsed == pytest.approx(1.0)` (the ordinary RFC 8628 floor, NOT the 0.001s host-timer
clamp the `NaN`/positive-`Infinity` tests assert).

**Independently confirmed discriminating by revert-and-confirm**: temporarily reverted all three
`_needs_host_timer_clamp(...)` call sites back to `not math.isfinite(...)`, reran the new test,
confirmed it failed (`0.001 == 1.0` mismatch -- the reverted code incorrectly applied the
one-millisecond clamp to negative `Infinity`), then restored the fix and confirmed the full suite
(28 device-code tests) passes, including the pre-existing `NaN`/positive-`Infinity` witnesses
(still correctly asserting `0.001`, proving the correction is properly SCOPED to negative
`Infinity` only, not a blanket reversal).

A minor, unrelated formatting drift in `device_code.py`/`test_device_code.py` (introduced
incidentally while editing, not a semantic issue) was caught by `ruff format --check` and
corrected before finalizing, restoring the pre-existing seven-file baseline drift exactly.

## Normative deltas

- `spec/auth.md`: new paragraph explicitly distinguishing negative `Infinity` (ordinary
  one-second RFC-8628 floor) from `NaN`/positive `Infinity` (one-millisecond host-timer clamp).
- `pi-parity-manifest.yaml`: `PROV-010`'s rule text extended with the `L11-R016` history; test
  count updated to 28 with the new witness named explicitly.

## Fresh quality gates

- `pytest` (full suite, with coverage): 1292 passed, 19 xfailed (pre-existing, unrelated), 65
  skipped, 0 failed.
- Coverage: 100.00% (`TOTAL` 3150 statements, 0 missed).
- `ruff check .`: clean.
- `mypy` (default gate): clean, 66 source files.
- `mypy` including all three permanent typing fixtures: clean, 69 source files.
- `ruff format --check .`: back to the same pre-existing 7-file drift (a transient 2-file drift
  introduced mid-edit was caught and corrected before this final run).
- `tests/test_layering.py`: 5/5.
- `tests/conformance/test_manifest_validation.py`: 8/8.
- `tests/conformance/test_schema_validation.py`: clean, unchanged.
- `tests/conformance/test_auth_device_code_conformance.py`: 6/6, unchanged.
- Manual secret scan of every changed `auth/`/`tests/auth/` file: clean.

## Next action

Push to the same candidate branches, updating PRs #25/#54 in place. `STATUS = RUST_CONTRACT_REVIEW`,
requesting a NEW complete exact-SHA review per §11.8.8. `NEXT_OWNER = Codex`. Do not implement Rust
yet. Do not start Layer 12.
