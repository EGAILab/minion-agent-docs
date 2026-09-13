# Layer 11 — L11-R017 / L11-R018 implementation

## Candidates

```text
prior rejected candidate (sixth final-complete review)
    code d6c3dd47d557f6a1eb2a72daf0b4ae1bf2301c37 (introduced `_needs_host_timer_clamp`, L11-R016)
    docs PR #65 @ b5d1eb909c382b5068a1d82f9c9d16c7e6ec16ef

sixth final-complete review (rejecting)
    assurance/layers/11-auth-foundation-final-complete-rust-contract-review-6.md
    (Codex's own review branch/PR #65 -- not merged into this branch; referenced by SHA only)
```

## §11.8 trigger-check statement

Layer 11 has now accumulated six rejected complete reviews. The mandatory §11.8 "three rejected
reviews" trigger was already crossed at the fifth review (L11-R014/L11-R016) and this layer has
been operating under convergence discipline since `11-auth-foundation-r013-convergence-agreement.md`.
`L11-R017` and `L11-R018` are each a FIRST occurrence (neither finding has itself survived a prior
rejection), so neither independently re-triggers a fresh convergence episode under the "same finding
survives two reviews" clause -- but the layer-level "three rejected reviews" trigger remains
continuously active, and the review's own required remediation explicitly frames this as "one narrow
boundary-separation remediation on the existing special-number convergence surface," i.e. a
continuation of the SAME convergence work already underway (revisions 1-3 of `L11-R014`/`L11-R016`),
not an independent point-fix outside it. This document therefore proceeds as a convergence
implementation record under the existing episode, per the same discipline as
`11-auth-foundation-r016-implementation.md`, rather than opening a new standalone agreement
checkpoint -- the correction is narrowly scoped, the affected surface and call sites are already
fully mapped from the prior three revisions, and the review's own text does not request a fresh
characterization/challenge negotiation, only implementation of the boundary distinction it already
specified in detail.

## Independent re-verification

Re-read `packages/ai/src/auth/oauth/device-code.ts` directly, not the review's own prose alone:

- `abortableSleep` is its own top-level `export function`, callable independently of
  `pollOAuthDeviceCodeFlow` -- confirmed it performs NO normalization of its own `ms` parameter
  before passing it to `setTimeout`.
- `pollOAuthDeviceCodeFlow`'s own interval computation (`Math.max(MINIMUM_INTERVAL_MS,
  Math.floor(...))`) happens entirely BEFORE any call into `abortableSleep`, and is the only
  normalization anywhere in the call chain.
- Independently confirmed via direct computation (not merely restating the review) that
  `not (1 <= x*1000 <= 2_147_483_647)` requires no explicit `NaN`/`Infinity` branching:
  `float("nan") >= 1` and `float("nan") <= 2_147_483_647` are each `False` in Python (matching
  JS's own `NaN` comparison semantics exactly), so the predicate already evaluates `True` for
  `NaN` with no special case; `float("-inf")*1000 <= 2_147_483_647` is `True` but `>= 1` is
  `False`, correctly failing the lower bound; `float("inf")*1000 >= 1` is `True` but `<=
  2_147_483_647` is `False`, correctly failing the upper bound; `0.0` and `-5.0` both fail the
  lower bound directly.
- Traced every existing device-code test scenario by hand against the simplified poll-loop
  predicate (`math.isnan(...)` only, dropping the `== math.inf` exclusion): confirmed positive and
  negative `Infinity` reach byte-identical results whether or not they are explicitly excluded,
  since Python's own plain `max()` already resolves both correctly against
  `MINIMUM_INTERVAL_SECONDS` with no special-casing required -- the exclusion was redundant at
  this boundary (though harmless), not incorrect; simplifying it removes a predicate this boundary
  never actually needed, and importantly avoids the now-deleted `_needs_host_timer_clamp` becoming
  a dangling reference.

**Answering the §11.8.4-equivalent checklist:**

- *Is the Pi source mapping correct?* Yes, confirmed above -- two independently-callable functions,
  two different observable contracts for the same raw input.
- *Is the behavior matrix complete enough?* Yes, now covering: `NaN`/positive `Infinity`/negative
  `Infinity`/zero/negative-finite/positive-sub-millisecond, at BOTH the poll-loop-normalized
  boundary and the direct-call boundary.
- *Are any cases implementation mechanics rather than observable semantics?* No -- which function a
  caller invokes (the poll loop vs. the exported sleep primitive directly) is itself an
  Pi-observable API distinction, not a Python-specific detail.
- *Can both Python and Rust implement the rule idiomatically?* Yes -- `_needs_setimeout_clamp` is a
  direct range check with no special-case branching; the poll-loop's own `math.isnan(...)` check is
  equally direct.
- *Does this reopen any of revisions 1-3's own core decisions?* No -- the poll-loop's own clamp
  target (`NaN` only, ordinary `max()` for everything else) is UNCHANGED from revision 3. Only
  `abortable_sleep`'s OWN predicate, for its role as an independently-callable function, is
  broadened to match Node's full bounds check.

## Agreed correction

| Call path | Input | Prior (rejected) | Corrected |
|---|---|---|---|
| Poll loop's own normalization (initial interval, slow_down fallback) | `NaN` | clamps via `abortable_sleep` to 0.001s | UNCHANGED |
| Poll loop's own normalization | +/-`Infinity` | ordinary `max()`, resolves to floor/unchanged | UNCHANGED (predicate simplified to `math.isnan` only; result identical) |
| `abortable_sleep` called directly | `NaN`, +`Infinity` | clamps to 0.001s | UNCHANGED |
| `abortable_sleep` called directly | -`Infinity` | performs ZERO sleep (bug) | clamps to 0.001s |
| `abortable_sleep` called directly | `0.0`, negative finite | performs ZERO/negative sleep (bug) | clamps to 0.001s |

## Implementation

`device_code.py`:

- New `_needs_setimeout_clamp(seconds: float) -> bool`, replacing `_needs_host_timer_clamp`
  entirely: `milliseconds = seconds * 1000; return not (1 <= milliseconds <= 2_147_483_647)` --
  models Node's full `setTimeout` bounds check directly, with no `NaN`/`Infinity` special-casing
  (ordinary chained comparison already produces the correct answer for every case). Used ONLY by
  `abortable_sleep`'s own clamp.
- Both poll-loop call sites (initial-interval setup; slow_down fallback increment) simplified from
  `_needs_host_timer_clamp(x)` to `math.isnan(x)`, since positive/negative `Infinity` both already
  resolve correctly through ordinary `max()` at this boundary without exclusion.
- `NON_FINITE_INTERVAL_FALLBACK_SECONDS`'s own docstring rewritten to state the "two separate
  boundaries, two different rules" distinction explicitly, cross-referencing both predicates.

`tests/auth/test_device_code.py`: three new direct (non-poll-loop) `abortable_sleep` tests --
`float("-inf")`, `0.0`, `-5.0` -- each asserting at least one sleep call occurs and the total
elapsed time is `pytest.approx(0.001)`, i.e. Pi's real magnitude, not zero sleep at all.

**Independently confirmed discriminating by revert-and-confirm**: temporarily reverted
`_needs_setimeout_clamp`'s body to the OLD `_needs_host_timer_clamp` predicate
(`math.isnan(seconds) or seconds == math.inf`) while leaving the three new tests in place; all
three failed with the exact pre-fix symptom (`assert 0 >= 1`, i.e. zero sleep calls) rather than
completing with the expected `0.001` total. Restored the corrected predicate and reran the full
`tests/auth/test_device_code.py` suite (31/31 passed), confirming the fix is genuinely
discriminating and introduces no regression in any of the twenty-eight pre-existing witnesses
(including the `L11-R014`/`L11-R016` `NaN`/positive-`Infinity`/negative-`Infinity` poll-loop
witnesses, still asserting their own prior values unchanged).

A transient `E501` (line-too-long) drift introduced while writing the new inline comments/docstrings
was caught by `ruff check` and corrected before finalizing.

## Normative deltas

- `spec/auth.md`: the general "non-finite interval clamps to one millisecond" paragraph is rewritten
  to name the two separate boundaries explicitly (poll-loop normalization vs. the exported
  `abortableSleep`/`abortable_sleep` seam) and to scope each rule to the boundary it actually
  governs -- resolving the literal contradiction `L11-R018` identified between that paragraph and
  the adjacent negative-`Infinity` paragraph. A new paragraph states the direct-call
  `abortableSleep` rule (Node's full bounds check, uniform across sign) explicitly.
- `pi-parity-manifest.yaml`: `PROV-010`'s rule text extended with the `L11-R017` history and the
  `L11-R018` spec-correction cross-reference; test count updated to 31 with the new witnesses named
  explicitly.

## Fresh quality gates

- `tests/auth/test_device_code.py` (targeted, `--no-cov`): 31 passed, 0 failed.
- `tests/conformance/test_manifest_validation.py`: 8/8.
- `ruff check src/minion_agent/auth/device_code.py` / `tests/auth/test_device_code.py`: clean.
- `ruff format --check` on both changed files: clean (no new drift beyond the pre-existing
  baseline).
- `mypy src/minion_agent/auth/device_code.py`: clean.
- Full-repo gate suite (pytest with coverage, `ruff check .`, `mypy` including typing fixtures,
  `ruff format --check .`, `tests/test_layering.py`, `tests/conformance/test_schema_validation.py`,
  `tests/conformance/test_auth_device_code_conformance.py`, manual secret scan): to be run and
  recorded with exact fresh counts immediately before push, per this project's "report fresh
  counts, never reuse old numbers" rule.

## Next action

Push to the same candidate branches, updating PRs #25/#54 in place. `STATUS = RUST_CONTRACT_REVIEW`,
requesting a NEW complete exact-SHA review per §11.8.8. `NEXT_OWNER = Codex`. Do not implement Rust
yet. Do not start Layer 12.
