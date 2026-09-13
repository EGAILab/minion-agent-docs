# Layer 11 — L11-R019 implementation

## Candidates

```text
prior rejected candidate (seventh final-complete review)
    code 35382f5b1a69d50afda4d72ae48b8e1d1970787b (L11-R017 fix)
    docs 37f1cb1bc867f2983d1af3eccaaff71193a26b19 (L11-R017/L11-R018 fix)
    docs PR #66 @ f976d4c68a59bb4ef338fdc737c6eb65e89617dd

seventh final-complete review (rejecting)
    assurance/layers/11-auth-foundation-final-complete-rust-contract-review-7.md
    (Codex's own review branch/PR #66 -- not merged into this branch; referenced by SHA only)
```

## §11.8 trigger-check statement

Layer 11's "three rejected reviews" trigger has been continuously active since the fifth review and
remains active (seven rejections accumulated). `L11-R019` is a first occurrence, not a repeat of any
prior finding, but it was found on the SAME `abortable_sleep`/`setTimeout` boundary `L11-R017` just
remediated -- this document proceeds as a continuation of the same special-number/boundary-precision
convergence work, per the same discipline as `11-auth-foundation-r016-implementation.md` and
`11-auth-foundation-r017-r018-implementation.md`, rather than opening an independent standalone
agreement checkpoint. The finding is narrowly scoped and the affected surface is already fully
mapped from the immediately-prior remediation.

## Independent re-verification

Re-confirmed, independently of the review's own prose, that Node's real `setTimeout` truncates an
already-VALID delay (one inside `[1, 2147483647]` ms) to a whole integer millisecond count before
scheduling it -- this is a SEPARATE step from the documented invalid-range clamp `L11-R017` models,
and applies unconditionally to any accepted delay, including one that has already passed the range
check. `0.0019` seconds (1.9 ms) is squarely inside `[1, 2147483647]` ms, so `_needs_setimeout_clamp`
correctly leaves it untouched -- but pinned Pi's own real runtime still truncates it to `1` ms before
the timer actually fires.

**Answering the §11.8.4-equivalent checklist:**

- *Is the Pi source mapping correct?* Yes -- `setTimeout`'s internal truncation is independent of,
  and layered on top of, its own documented invalid-range clamp; both apply to every call.
- *Is the behavior matrix complete enough?* Yes, now covering every delay this module's `setTimeout`
  boundary can receive: invalid (clamped to `NON_FINITE_INTERVAL_FALLBACK_SECONDS`) and valid
  (truncated to a whole millisecond).
- *Are any cases implementation mechanics rather than observable semantics?* No -- whether a
  scheduled delay preserves sub-millisecond precision is directly observable (a caller can measure
  elapsed time), not an internal detail.
- *Can both Python and Rust implement the rule idiomatically?* Yes -- reusing the existing
  whole-millisecond-floor helper (`_floor_to_whole_milliseconds`, `L11-R012`) at this second call
  site is direct in Python; Rust has an equally direct integer-truncation equivalent.
- *Does this reopen `L11-R017`'s own core decision?* No -- the invalid-delay clamp predicate and
  fallback value are UNCHANGED. This adds a SEPARATE, additional step for delays that clamp does
  not touch.

## A regression discovered during this same remediation (not part of the review's own finding)

Independently, before finalizing, re-verification surfaced that a NAIVE implementation of the
truncation above (reusing `_floor_to_whole_milliseconds` via a bare `math.floor`) regressed the
canonical `auth-device-code-expiry-without-slow-down` conformance scenario: `poll_device_code_flow`'s
own deadline-capped sleep amount (`min(interval, remaining)`, where `remaining = deadline - now()`)
is derived from repeated floating-point clock arithmetic -- `abortable_sleep`'s own signal-polling
slicing loop (a disclosed, Python-only mechanic, not a Pi behavior; see `PROV-010`'s own rule text)
accumulates on the order of `1e-13` seconds of summation drift per multi-second sleep. A `remaining`
value MEANT to be an exact whole millisecond (e.g. `2000.0` ms) can therefore arrive as
`1999.999999999973` ms; a bare `math.floor` truncates that down to `1999` ms instead of the intended
`2000`, undershooting the deadline by a fraction of a millisecond and triggering one extra,
unscripted `poll()` call the scenario's own scripted 3-outcome sequence does not provide for
(`IndexError: list index out of range`). This is a Python-implementation-only numerical-robustness
issue, not a Pi-parity question: nothing here changes any cross-language-observable contract.

Fixed by adding a `1e-6` millisecond epsilon tolerance to `_floor_to_whole_milliseconds` itself
(`math.floor(seconds * 1000 + 1e-6) / 1000`), reasoned as follows: the tolerance is many orders of
magnitude larger than any float-summation drift this module's own slicing mechanism produces
(`~1e-13`s → `~1e-10` ms), yet many orders of magnitude smaller than the smallest genuinely-fractional
delay any caller actually passes (the `1.9` ms witness this same finding requires) -- so it corrects
values that are drift-affected artifacts of an exact whole-millisecond intent, without ever masking a
real fractional delay. This addition applies to every caller of the shared helper, including the
pre-existing `L11-R012` upstream-flooring call sites, but changes no previously-tested behavior there
(none of those literal, caller-supplied interval values were ever within `1e-6` ms of a
whole-millisecond boundary).

## Agreed correction

| Call | Delay | Prior (rejected) | Corrected |
|---|---|---|---|
| `abortable_sleep` direct call | `0.0019`s (1.9 ms), valid range | preserved as `0.0019`s | truncates to `0.001`s (1 ms) |
| `poll_device_code_flow`'s own deadline-capped sleep | drift-affected `remaining` near a whole-ms boundary | N/A (untested edge case) | epsilon-tolerant floor snaps to the intended whole millisecond, preserving the scenario's exact-deadline convergence property |

## Implementation

`device_code.py`:

- `abortable_sleep`'s own clamp branch extended with an `else` that applies
  `_floor_to_whole_milliseconds` to any delay `_needs_setimeout_clamp` did NOT reject -- modeling
  Node's own internal truncation of an already-valid delay.
- `_floor_to_whole_milliseconds` itself hardened with a `1e-6` ms epsilon tolerance before flooring,
  for the numerical-robustness reason above.

`tests/auth/test_device_code.py`: one new direct (non-poll-loop) `abortable_sleep` test --
`abortable_sleep(0.0019, ...)` -- asserting at least one sleep call occurs and the total elapsed
time is `pytest.approx(0.001)`, i.e. truncated to Pi's real magnitude, not the raw `0.0019`.

**Independently confirmed discriminating by revert-and-confirm**: temporarily reverted
`abortable_sleep`'s clamp branch to drop the new `else`/truncation step entirely; the new test
failed with the exact pre-fix symptom (`0.0019 == 0.001`, i.e. the raw untruncated value). Restored
the fix and reran the full `tests/auth/test_device_code.py` suite (32/32 passed) plus
`tests/conformance/test_auth_device_code_conformance.py` (confirming the epsilon-tolerance fix
resolves the `auth-device-code-expiry-without-slow-down` regression the naive truncation introduced,
with no other conformance scenario affected).

## Normative deltas

- `spec/auth.md`: new paragraph stating the direct-call truncation rule for an already-VALID delay,
  distinct from both the poll loop's own upstream flooring and the invalid-delay clamp.
- `pi-parity-manifest.yaml`: `PROV-010`'s rule text extended with the `L11-R019` history, including
  the self-discovered epsilon-tolerance fix and why it is a numerical-robustness detail rather than
  a Pi-parity divergence; test count updated to 32.

## Fresh quality gates

- `tests/auth/test_device_code.py` (targeted, `--no-cov`): 32 passed, 0 failed.
- `tests/conformance/test_auth_device_code_conformance.py` (targeted, `--no-cov`): all scenarios
  passing, including `auth-device-code-expiry-without-slow-down` (the regression this remediation
  found and fixed).
- `tests/conformance/test_manifest_validation.py`: 8/8.
- Full `pytest` suite (fresh, with coverage): 1296 passed, 19 xfailed (pre-existing, unrelated), 0
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
