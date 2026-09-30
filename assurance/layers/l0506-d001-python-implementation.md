# L0506-D001 Python implementation candidate (`TOOL-041`)

- **Coordination:** `minion-agent#88`.
- **Governance:** Owner decision `L13-WP132-I004`, Option 1 (`#49` comment `5912178299`); `standing_delegation: #75`.
- **State:** PYTHON_IMPLEMENTATION → IMPLEMENTATION_REVIEW.

## Baseline

- The contract is AGREED FOR IMPLEMENTATION (`minion-agent-docs#199`), and merged: docs #195 → master `a8041e0a`; code #89 → main `3c15b057`.
- Candidate: code #90 @ `2bb229dffe1072a90b80ba9644355d2528381dec`, one commit on main `3c15b057`.

## Change

**`minion_agent/tools/execute.py`:**
- **`PreparedArgumentsValidator`** is Draft 2020-12 with `number` redefined as finite-only:
  - ±inf and NaN are not `number`;
  - `integer` was already finite-only;
  - `-0.0` stays valid for both.

  A position the schema does not constrain is never checked, so a non-finite value there is kept. This fixes **`L0506-D001-C001`**: certified Python accepted ±inf and NaN in a declared `number`.
- **`_reject_declared_non_finite`** gives pydantic-model tools the same rule. After pydantic accepts the arguments, the prepared arguments are checked against the model's own JSON schema, and only a non-finite value in a declared numeric position is reported; pydantic stays authoritative otherwise. A model whose JSON schema cannot be generated is left to pydantic, as disclosed in the spec.
- **Unchanged:** preparation, the hook dispatch and `execute`. Their values already flow in memory as Python numbers: `int`, and `float` including `-0.0`, ±`inf` and `nan`.

The manifest `TOOL-041` `python:` field is updated.

## Evidence

**Canonical.** `tests/conformance/prepared_runtime_runner.py` and `test_prepared_runtime_conformance.py` run the **delta gate `L0506-D001`**, selected explicitly by `gate`.
- It covers 19 custom cases through the real `execute_call`, all passing, with the language-neutral preflight on every case.
- The hook and `execute` observe the authority's tokens, and the raw arguments are unchanged.
- The gate-`WP-13.2` real-`edit` document is not run here (`L0506-D001-R003`). It runs with WP-13.2 after certification.

**Negative controls** (Owner decision §8), in `tests/tools/test_prepared_runtime_negative_controls.py`. Each is a single-point mutant of the real Layer 06 code, killed by named canonical cases. A test first proves the witnesses pass unmutated.

| Mutant | Killed by |
|---|---|
| Infinity rejected (a type that cannot hold it) | undeclared ±Infinity |
| Infinity mapped to null | undeclared ±Infinity / NaN |
| Infinity clamped to max finite | undeclared ±Infinity |
| Infinity stringified | undeclared ±Infinity / NaN |
| `-0` collapsed to `+0` | declared-number, declared-integer and undeclared `-0` |
| hook projection losing a non-finite value (source mutant of the pre-execute dispatch; `execute` still gets the real value) | undeclared ±Infinity / NaN |
| validator accepting non-finite in a declared `number` (C001 reverted) | declared-number ±Infinity / NaN |

**Pydantic.** `tests/tools/test_prepared_runtime_validation.py` checks that:
- a declared float rejects ±inf and NaN;
- `-0.0` and `1e308` pass, with the sign of zero kept;
- an unconstrained extra keeps `inf`;
- a model without a JSON schema is left to pydantic.

## Fresh gates

These ran on Windows, on the candidate, with the pinned ICU 78.3 environment:

| Gate | Result |
|---|---|
| `pytest` | **2213 passed**, 16 skipped, 19 xfailed; coverage **100%** |
| `ruff check`, format (changed files), `mypy` | clean |

The Linux container was not run. The change is platform-independent validator logic over Python floats.

## Status

- `L0506-D001` Python: IMPLEMENTATION CANDIDATE, pending independent exact-SHA review.
- Rust: NOT_IMPLEMENTED (Codex's: the prepared-runtime value representation).
- Cross-language: NOT CLOSED.

## Remediation 1: `L0506-D001-I001`

**Trigger.** Codex's implementation review (`minion-agent-docs#200` comment `5913924339`, code #90 @ `2bb229df`) found that the pydantic path still passed ±Infinity and NaN to the hook and `execute` for:
- a **nullable** numeric field: the JSON-schema check filtered `type` errors, but a nullable number fails under `anyOf`;
- a model with an unrelated **opaque** field: JSON-schema generation failed, and the check fell back to pydantic alone.

Accepted.

**Characterization.** A first attempt forced `allow_inf_nan=False` into the model's pydantic-core schema and revalidated. It was rejected by evidence: pydantic-core honors that flag on `float` and `nullable` nodes but ignores it inside a `model` node. Probed on pydantic 2.13.4 / pydantic-core 2.46.4, whatever the node's `config` or `ref`.

**The fix** (`execute.py`, `_reject_declared_non_finite`).
- After pydantic accepts the arguments, the **validated model** is walked against its declared field types, with no JSON schema involved.
- A non-finite float is rejected in any declared numeric position: a plain field, an `Optional` or other union, `Annotated`, a list, a positional or variadic tuple, a set, a dict's values, a nested model, a dataclass, or a TypedDict.
- A position whose declared type admits it keeps the value. That means `Any` or `object`, or a union containing one, and undeclared extras.
- Pydantic stays the authority for every other rule. The earlier disclosed limit, a model without a JSON schema, no longer exists.

**Witnesses** (`tests/tools/test_prepared_runtime_validation.py`, 42 tests).
- For each of ±inf and NaN, rejection at every declared position above, including both of the review's probes (`Optional[float]`, and a model with an opaque field).
- Kept: `Any`, a union with `Any`, an undeclared extra, and a value inside `Any`.
- `-0.0` keeps its sign, directly and inside a list, and finite nested structures pass.

**Gates** (code `1b1505c3a3ffd103300fe157d41ea8dca6a2fb26`, Windows, pinned ICU):

| Gate | Result |
|---|---|
| `pytest` | **2252 passed**, 16 skipped, 19 xfailed; coverage **100%** |
| `ruff check`, format (changed files), `mypy` | clean |
| delta gate | 19/19 |
| §8 negative controls | 7/7 killed |

The Linux container was not run, since the change is platform-independent.
