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

## Remediation 2: `L0506-D001-I001` (convergence episode `CE-L0506-D001-I001-01`)

**Trigger.** The Remediation 1 walker survived as I001: Codex's review `#90` comment `5918098742` found that walking the *validated* instance is branch-lossy on unions (`list[float] | list[Any]`, `Inner | dict[str, Any]`). That opened the convergence episode `CE-L0506-D001-I001-01` (`l0506-d001-ce-i001-01.md`):

| Revision | Outcome | Findings |
|---|---|---|
| rev 1 | CHANGES REQUIRED | characterization and six-cell classification accepted; C001 validator replay, C002 after-validator non-finite |
| rev 2 | CHANGES REQUIRED | C001 resolved; clamp scope needs no Owner escalation; C002 refined (malformed-sibling exemption) |
| rev 3 | **APPROVED, AGREED FOR IMPLEMENTATION** | Codex, `#200` @ `a341386f`, evidence prototype `ec0ffb8e` |

**The fix** (`execute.py`, `_reject_declared_non_finite`, `_shape`, `_record_shape`), integrated exactly as agreed:
1. **One ordinary pydantic validation.** Each user validator runs once, in pydantic's order, with its result.
2. **The delivered value is judged.** `model_dump()` is the value handed to the before-hook and `execute()`, and it is returned unchanged.
3. **It is validated against a callback-free, finite-only structural shape of the declared types.** Record types become shape models over their delivered keys, including aliases under `serialize_by_alias` and computed fields; extra keys are allowed. No `Annotated` metadata, decorators, defaults or custom schemas are copied, and any other class is checked by `isinstance`. Recursion resolves through forward references.
4. **Any `finite_number` error rejects.**
   - A union some finite-only alternative accepts reports nothing (Pi's `anyOf`), so `Any`/`object`/extra positions keep their values.
   - An out-of-shape position reports only its own mismatch, and never exempts another position.
   - A declared `int` is finite-only as well.

The Remediation 1 walker is removed.

**Witnesses.**
- `test_prepared_runtime_validation.py`: the declared positions, both union orders, `Literal`, recursive and mutually recursive models, and `float | str` rejection. It also holds five rule negative controls: no check, a whole-value sweep, JSON-schema number fields only, first union member only, and a witness table.
- `test_prepared_runtime_callbacks.py` (new, real `execute_call` pipeline):
  - **C001:** one-shot callback traces, returned values and `-0` sign, plus the replay negative control;
  - **C002:** field/before/model/`Annotated`/nested callback-produced ±Infinity and NaN, rejected before the hook and `execute`;
  - malformed-sibling, integer, nested-sibling and list-element witnesses, plus the rev-2 whole-record-exemption negative control;
  - no-sweep and callback-finite (clamp) controls;
  - `NewType`/type alias/`RootModel`/`TypeVar`/enum/computed/alias kinds.

**Matrix** (`data/l0506-d001-ce-i001-01/rev2/`), 105 cells against pinned Pi's verdicts and returned values:
- 97 are identical;
- 6 are the accepted `TOOL-003` coercion cells;
- 2 differ only by pydantic's default-fill of `thing: None`.

The production tree reproduces `out/minion.json` byte-identically.

**Spec.** The *Pydantic-model parameters* bullet of TOOL-041 (`spec/tools.md`) is replaced by the agreed rev-3 wording. The manifest's TOOL-041 `python` note names the mechanism.

**Gates** (code `8f6400a5ea0841c1350e323aa73cf0fa4ed82458`, Windows, pinned ICU, fresh):

| Gate | Result |
|---|---|
| `pytest` | **2332 passed**, 16 skipped, 19 xfailed; coverage **100%** (`tools/execute.py` 226/226) |
| `ruff check`, format (changed files), `mypy` (91 files) | clean |
| manifest validation | in suite, passed |
| delta gate | 19/19 |
| §8 negative controls (`test_prepared_runtime_negative_controls.py`) | 7/7 killed |

The Linux container was not run; the change is platform-independent validator logic.

**Status.** `L0506-D001-I001` is REMEDIATED, pending Codex's §11.8.7 targeted convergence closure. The §11.8.8 final complete review comes after that. Rust and cross-language are unchanged: NOT_IMPLEMENTED and NOT CLOSED.

## Remediation 3: `L0506-D001-I002` (convergence episode `CE-L0506-D001-I001-01` rev 4)

**Trigger.** Codex's §11.8.8 final complete review (`#200`, on code `8f6400a5` / docs `f352ff92`) returned CHANGES REQUIRED. I001 was confirmed PROVISIONALLY_CLOSED by the preceding targeted closure (`#200` comment `5918998489`). The new finding, `L0506-D001-I002`, is a CONTRACT_ASSURANCE_DEFECT and blocking:
- **Symptom.** A callback delivering the string `"Infinity"`, `"-Infinity"` or `"NaN"` in a declared `float` field was rejected.
- **Cause.** The rev-3 shape's lax `float` coerced the string into the number it spells.
- **Baseline.** The accepted baseline `3c15b057` delivers the string unchanged.

Accepted. The characterization and checkpoint are CE rev 4, **APPROVED, AGREED FOR IMPLEMENTATION** (Codex, `#200` @ `d5df1187`, evidence prototype `0b39d173`).

**The fix** (`execute.py`, integrated exactly as agreed, with the `minion-agent-python/` tree identical to `0b39d173`):
- The finite shape's numeric leaves are strict. A declared `float` becomes `Annotated[float, AllowInfNan(False), Strict()]`, and a declared `int` becomes `Annotated[int, Strict()] | <that float>`.
- As a result, `finite_number` is reported only for an actual runtime non-finite float.
- A delivered value of another type is out of shape: it is delivered unchanged, and it never exempts a sibling.
- Everything else in Remediation 2 is unchanged.

**Witnesses** (`test_prepared_runtime_callbacks.py`), each for `"Infinity"`, `"-Infinity"`, `"NaN"`, plus the controls `"outside"` and `"1"`:
- a numeric-looking string delivered in `float`, `int`, a `list[float]` element and a nested record's `float` passes, and the hook and `execute` receive the original string;
- a string in `float`/`int`/`list[float]`/`float | str` beside a genuine ±Infinity/NaN `float` sibling is rejected before the hook and `execute`.

The 6 numeric-looking-string witnesses fail on `8f6400a5` and pass here.

**Spec.** TOOL-041 *Pydantic-model parameters* gains the agreed precision clause: "Only an actual runtime number is judged: a delivered value of another type (for example the string `"Infinity"`) is never converted into one." The manifest's TOOL-041 `python` note names the strict numeric leaves and I002.

**Gates** (code `683103a73584bc12190a61a5c2e826ab1b50b4ac`, Windows, pinned ICU, fresh):

| Gate | Result |
|---|---|
| `pytest` | **2357 passed**, 16 skipped, 19 xfailed; coverage **100%** (`tools/execute.py` 231/231) |
| `ruff check`, format (changed files), `mypy` (91 files) | clean |
| manifest validation | passed |
| delta gate | 19/19 |
| §8 negative controls | 7/7 killed |
| 105-cell matrix | byte-identical (`518d4051…`) |

The Linux container was not run; the change is platform-independent.

**Status.** `L0506-D001-I002` is REMEDIATED, pending Codex's §11.8.7 targeted closure. `L0506-D001-I001` stays PROVISIONALLY_CLOSED. The §11.8.8 final complete review follows. Rust and cross-language are unchanged: NOT_IMPLEMENTED and NOT CLOSED.
