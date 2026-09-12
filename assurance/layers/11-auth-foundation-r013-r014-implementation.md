# Layer 11 — L11-R013 (convergence implementation) + L11-R014 (point fix)

## Candidates

```text
prior rejected candidate
    code fc78f40f0bb8da50281f6ace607f5f39edb8227d
    docs 909dcff408ad96a6fd499c1933daa382bd668536

second final-complete review
    docs PR #61 @ 382bb4e04e1963ca52671c2d5aa7c3a7c1c8f014

convergence agreement (L11-R013)
    assurance/layers/11-auth-foundation-r013-convergence-agreement.md
```

## Implementation, per finding

### `L11-R013` (§11.8 convergence implementation, per the agreed checkpoint)

`context.py::DefaultAuthContext.file_exists` rewritten to wrap its ENTIRE body -- home-directory
resolution (the literal `os.path.expanduser("~") + path[1:]` concatenation, unchanged from the
first remediation) AND the filesystem check -- in one `try`, catching `Exception` broadly (not
`OSError` alone), matching Pi's own bare `try { ... } catch { return false; }` with no
exception-type filter.

New tests: `test_file_exists_returns_false_on_a_home_resolution_error` (patches
`os.path.expanduser` to raise `OSError`, proving resolution-stage failures are now caught) and
`test_file_exists_returns_false_on_a_non_os_error_during_access` (patches `Path.exists` to raise
`RuntimeError`, proving the catch is no longer `OSError`-only). The pre-existing `~suffix`
concatenation witness and the pre-existing `OSError`-during-access witness both remain unchanged
and still pass.

**Independently confirmed discriminating by revert-and-confirm**: temporarily reverted to the
first (rejected) remediation shape (resolution outside `try`, `except OSError` only) and reran the
two new tests. The home-resolution witness failed as expected. The non-`OSError` witness caused
the raised `RuntimeError` to propagate uncaught out of `file_exists` (confirmed directly in the
traceback, which also cascaded into pytest's own internal traceback-formatting machinery calling
the same globally-monkeypatched `Path.exists` a second time -- itself further proof the exception
was not contained by the reverted code, not a flaw in the confirmation). Restored the fix and
confirmed the full suite passes cleanly with no such cascade (the fix never lets the exception
reach a point where pytest's own machinery would need to handle it).

### `L11-R014` (ordinary point fix, no convergence trigger met)

`device_code.py::_floor_to_whole_milliseconds` gained an early return for non-finite input
(`if not math.isfinite(seconds): return seconds`), matching Pi's own `Math.floor`/`Math.max`
never raising for `Infinity`/`NaN` -- they propagate the special value arithmetically instead.
This is scoped to the SAME helper `L11-R012` introduced; the finite-value flooring behavior
`L11-R012` fixed is completely unchanged.

New tests: `test_initial_interval_infinity_does_not_throw_when_the_first_poll_completes` and
`test_initial_interval_nan_does_not_throw_when_the_first_poll_completes`, both using a
`ScriptedPoll` that completes on the very first attempt, proving setup with a non-finite initial
interval does not crash before `poll` is ever called, and the completed value is returned normally.

**Independently confirmed discriminating by revert-and-confirm**: temporarily removed the
non-finite early return, reran both new tests, confirmed both failed with the exact `OverflowError`
(`Infinity`) and `ValueError` (`NaN`) the review itself reported, at the exact `math.floor` call
site. Restored the fix and confirmed the full suite passes.

## Normative deltas

- `spec/auth.md`: the `file_exists` paragraph's rule 2 sharpened to explicitly name "including
  home-directory resolution itself" and "filtered to no particular exception type," so a future
  implementer cannot repeat this exact narrowing a third time. New "Non-finite initial intervals
  must not fail setup" paragraph in the device-code section.
- `pi-parity-manifest.yaml`: `PROV-006`'s `L11-R013` paragraph rewritten to describe both required
  corrections together and the exact gap the first remediation left; `PROV-010` gained a new
  `L11-R014` paragraph. Both rows keep `disposition: adopted` -- both are corrections to
  already-adopted Pi-parity rules, not new divergences.

## Fresh quality gates

- `pytest` (full suite, with coverage): 1287 passed, 19 xfailed (pre-existing, unrelated), 65
  skipped, 0 failed.
- Coverage: 100.00% (`TOTAL` 3137 statements, 0 missed).
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
requesting a NEW complete exact-SHA review per §11.8.8 (the prior two "final complete" reviews were
both rejected; the next review again rechecks the full contract, not only these two findings).
`NEXT_OWNER = Codex`. Do not implement Rust yet. Do not start Layer 12.
