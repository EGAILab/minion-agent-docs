# Layer 11 — L11-R014 revision-2 (§11.8 convergence) + L11-R015 (point fix) implementation

## Candidates

```text
prior rejected candidate
    code bbc06e97e1c0db3b0ece798841c15ea80540d6f8
    docs 4965f37c2dbbe91682f14244a52ad14c0bbda60e

fourth final-complete review
    docs PR #63 @ 3698582a40df491afb888094b6e725dfd0bffcb1

convergence agreement (L11-R014, revision 2)
    assurance/layers/11-auth-foundation-r014-convergence-agreement-v2.md
```

## Implementation, per finding

### `L11-R014` revision 2 (§11.8 convergence, per the agreed checkpoint)

`device_code.py`: new dedicated constant `NON_FINITE_INTERVAL_FALLBACK_SECONDS = 0.001`
(distinct from `MINIMUM_INTERVAL_SECONDS`, which remains RFC 8628's own unrelated floor for
ordinary finite intervals), replacing `MINIMUM_INTERVAL_SECONDS` as `abortable_sleep`'s own
non-finite clamp value.

Two additional internal-consistency fixes (not directly probed by the review, but the SAME bug
class at other call sites in the same function): the initial-interval setup computation and the
slow_down fallback increment both independently risked Python `max()` silently neutralizing a
`NaN` operand before it ever reached `abortable_sleep`'s own explicit `math.isfinite` check --
both now defer to that single clamp point via an explicit finiteness check of their own, rather
than relying on `max()`'s own order-dependent comparison.

Tests renamed/updated: `test_initial_interval_nan_used_for_a_pending_response_clamps_to_pi_magnitude`
and `..._infinity_..._clamps_to_pi_magnitude` now assert `pytest.approx(0.001)`, not `1.0`. New
test `test_nan_initial_interval_stays_non_finite_through_a_slow_down_fallback_increment` covers
the nested case.

**Independently confirmed discriminating by revert-and-confirm**: temporarily reverted the clamp
constant back to `1.0`, reran the three affected tests, confirmed all three failed reporting
`1.0 == 0.001` mismatches, then restored the fix.

### `L11-R015` (new, ordinary point fix -- has not independently met the §11.8 trigger)

`refresh.py`: new `_js_style_max(a, b) -> float` helper, matching JS `Math.max`'s own NaN-
propagation rule (`NaN` if either operand is `NaN`) rather than Python's plain `max()`, which
silently discards a `NaN` operand via ordinary `>`/`<` comparison. `trigger_validity_ms`'s own
computation now uses this helper instead of plain `max()`.

New test `test_explicit_minimum_validity_nan_suppresses_refresh_entirely`, matching the review's
own exact witness: a stored credential with `expires=120_000.0`, `now_ms=0.0`, an explicit
`minimum_validity_ms=float("nan")`, and a `refresh` callable that would return a distinct
credential if called -- asserts the ORIGINAL credential is returned unchanged and `refresh_calls
== 0`.

**Independently confirmed discriminating by revert-and-confirm**: temporarily reverted
`_js_style_max` back to plain `max()`, reran the new test, confirmed it failed (the refresh WAS
incorrectly triggered and a different credential returned), then restored the fix.

## Normative deltas

- `spec/auth.md`: the device-code section's non-finite-interval paragraph rewritten to state the
  corrected one-millisecond magnitude and the two-revision history (why the value changed, not
  just what it currently is); new paragraph in the refresh-authority section stating the explicit-
  NaN-suppresses-refresh rule.
- `pi-parity-manifest.yaml`: `PROV-010`'s `L11-R014` paragraph extended with the "third
  remediation" history; `PROV-008` gained a new `L11-R015` paragraph. Both rows keep
  `disposition: adopted` -- both are corrections to already-adopted Pi-parity rules.

## Fresh quality gates

- `pytest` (full suite, with coverage): 1291 passed, 19 xfailed (pre-existing, unrelated), 65
  skipped, 0 failed.
- Coverage: 100.00% (`TOTAL` 3148 statements, 0 missed).
- `ruff check .`: clean.
- `mypy` (default gate): clean, 66 source files.
- `mypy` including all three permanent typing fixtures: clean, 69 source files.
- `ruff format --check .`: the same pre-existing 7-file drift, unchanged.
- `tests/test_layering.py`: 5/5.
- `tests/conformance/test_manifest_validation.py`: 8/8.
- `tests/conformance/test_schema_validation.py`: clean, unchanged.
- `tests/conformance/test_auth_device_code_conformance.py`: 6/6, unchanged (no canonical scenario
  content changed -- both findings' discriminating evidence lives in Python unit tests).
- Manual secret scan of every changed `auth/`/`tests/auth/` file: clean.

## Next action

Push to the same candidate branches, updating PRs #25/#54 in place. `STATUS = RUST_CONTRACT_REVIEW`,
requesting a NEW complete exact-SHA review per §11.8.8. `NEXT_OWNER = Codex`. Do not implement Rust
yet. Do not start Layer 12.
