# Layer 11 Pass 2, Slice B — provider-auth interaction/auth-method vocabulary (`PROV-014`)

## Authority and baseline

- accepted code baseline: `main` @ `039050710579d6511a63c25077093bfe83006b11` (Slice A merged)
- accepted docs baseline: `master` @ `479e388599f4f36a19c15532fd2ce33531b02704` (Slice A + its
  second re-review merged)
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- coordination issue: `minion-agent#29`
- `GOVERNANCE_SOURCE` (`agent-workflow.md` §11.10): the owner's own scope-decision message, posted
  verbatim at `https://github.com/EGAILab/minion-agent/issues/29#issuecomment-5659001629` --
  explicitly authorizes the `PROV-013` split (new `PROV-014` row for the vocabulary), Slice B
  contract-first, and states the vocabulary "is ADOPTED in Pass 2 ... no longer deferred merely
  because generic Models-level orchestration is deferred."

## Scope

Contract-first, per the owner's own explicit sequencing (Slice A -> Slice B vocabulary -> Slice C
network integration, so Slice C never implements against an unfrozen contract). VOCABULARY ONLY:
the login-interaction/prompt/notification vocabulary (`AuthPrompt`/`AuthInfoLink`/`AuthEvent`/
`AuthInteraction`/`ProviderAuthInteraction`) and the per-provider auth-method vocabulary
(`ApiKeyAuth`/`OAuthAuth`/`ProviderAuth`), split out of the previously-bundled `PROV-013` row.

Explicitly NOT in this slice, per the same owner instruction: any `Models`-equivalent dispatcher,
any `LlmService` extension, any new generic `AuthService`/`AuthManager` architecture, and
`PROV-012` itself (Slice C, which will CONSUME this vocabulary in a later pass).

## Independent Pi audit

`packages/ai/src/auth/types.ts:118-241` -- `AuthPrompt`, `AuthInfoLink`, `AuthEvent`,
`AuthInteraction`, `ProviderAuthInteraction`, `ApiKeyAuth`, `OAuthAuth`, `ProviderAuth`. This exact
range was read directly and in full during the Pass-2 restart's own fresh audit (recorded on
`minion-agent#29`, before the owner's scope decision), not re-derived from any quarantined source
per `agent-workflow.md` §11.12. Also cross-referenced `packages/ai/src/auth/resolve.ts` and
`packages/ai/src/models.ts` (`Models.login`'s own commit-race-safety semantics, `resolve.ts`/
`models.ts:565-615`) to confirm the orchestration half these vocabulary types feed into is
genuinely separable and genuinely still blocked on a `Provider`/`LlmService` integration point
Minion does not have (`LlmService` confirmed fresh to expose only `register`/`models`/`stream`).

## Implementation

`minion-agent-python/src/minion_agent/auth/interaction.py` (new):

- `AuthPromptText`/`AuthPromptSecret`/`AuthPromptOption`/`AuthPromptSelect`/`AuthPromptManualCode`
  plus the `AuthPrompt` union type alias -- matching Pi's own tagged-union shape via the project's
  established per-variant-dataclass-plus-type-alias pattern (`DevicePollResult`, `PROV-010`).
- `AuthInfoLink`, `AuthEventInfo`/`AuthEventUrl`/`AuthEventDeviceCode`/`AuthEventProgress` plus the
  `AuthEvent` union type alias.
- `AuthInteraction`/`ProviderAuthInteraction` as TWO separate, standalone `Protocol` classes (not
  one narrowing the other through inheritance) -- `signal`'s own declared type differs (`Abortable
  | None` vs. required `Abortable`), and a mutable `Protocol` attribute is invariant under mypy, so
  inheritance-based narrowing would not type-check safely; `Protocol`'s own structural typing means
  any object satisfying both shapes conforms to both regardless of declared inheritance. `signal`
  reuses the already-certified `Abortable` structural protocol (`auth/signal.py`, `PROV-008`) --
  no new cancellation primitive introduced.
- `ApiKeyAuth`/`OAuthAuth` as frozen dataclasses of `Callable`-typed fields, matching the project's
  own established convention for an injected callable (`refresh.py`'s own `RefreshOperation`).
  `ProviderAuth` enforces Pi's own binding doc-comment requirement (at least one of `api_key`/
  `oauth` present) via `__post_init__`, a real runtime invariant, not merely documented convention.

`tests/auth/test_interaction.py` (new, 14 tests): construction and field-default coverage for
every variant, `AuthPromptSelect`'s own option-`id`-not-`label` return semantics (documented, not
independently re-derivable from a pure-data test alone -- see the typing fixture below for the
part that IS independently checkable), `ProviderAuth`'s own `__post_init__` invariant (rejects
zero of `api_key`/`oauth`; accepts `api_key`-only, `oauth`-only, and both), `ApiKeyAuth`/
`OAuthAuth` field defaults.

`tests/typing/valid_interaction_vocabulary.py` (new, permanent static-type evidence, mypy-checked
only, never executed by pytest): proves a PROPERLY-typed provider implementation -- not pytest's
own loosely-typed inline callbacks (`# type: ignore[no-untyped-def]`, since pytest's default gate
never type-checks `tests/`) -- actually satisfies `AuthInteraction`/`ProviderAuthInteraction`'s own
structural `Protocol` shape and every `Callable` type alias (`ApiKeyLogin`/`ApiKeyCheck`/
`ApiKeyResolve`/`OAuthLogin`/`OAuthRefresh`/`OAuthToAuth`) under full mypy strictness. Required two
separate fake-interaction classes (`_FakeInteraction`/`_FakeProviderInteraction`), confirming the
`AuthInteraction`/`ProviderAuthInteraction` invariance reasoning above empirically: a single class
whose `signal` attribute tried to satisfy both protocols' differing declared types failed to
type-check (`Incompatible types in assignment`, `expected "Abortable | None", got "Abortable"`)
before being split into two classes.

## Fresh quality gates

- `tests/auth/test_interaction.py` (targeted, `--no-cov`): 14 passed, 0 failed.
- Full `pytest` suite (fresh, with coverage): 1335 passed, 19 xfailed (pre-existing, unrelated), 0
  failed.
- Coverage: 100.00% (`TOTAL` 3306 statements, 0 missed).
- `ruff check .`: clean.
- `mypy` (default gate, `files = ["src/minion_agent"]`): clean, 68 source files.
- `mypy` including all typing fixtures: clean, 72 source files.
- `ruff format --check .`: same pre-existing 7-file drift baseline (182 files total now formatted,
  up from 179 -- the three new files), no new drift.
- `tests/test_layering.py`, `tests/conformance/*`: all passing, including manifest validation
  (93/93 unique rows -- 92 pre-existing + the new `PROV-014` row, `PROV-013` narrowed in place).
- Manual secret scan of the new/changed files: clean.

## Normative deltas

- `spec/auth.md`: new adopted "Provider-auth interaction and auth-method vocabulary (`PROV-014`,
  Pass 2 Slice B, adopted)" section stating the full vocabulary as language-neutral normative
  prose; "Deferred generic auth/provider orchestration surface" section narrowed to describe ONLY
  `resolveProviderAuth`/`Models`-level dispatch, now explicitly built on top of `PROV-014`.
- `pi-parity-manifest.yaml`: `PROV-013` narrowed to the orchestration half only (disposition
  unchanged, `deferred parity`); new `PROV-014` row added for the vocabulary (`adopted`). 93 rows
  total (92 previously + 1 new; no row removed).

## Findings

None. No `PI_PARITY_DEFECT`, `CONTRACT_ASSURANCE_DEFECT`, or `PI_BEHAVIOR_UNCERTAIN`.

## Next action

Push candidate branches (fresh, not derived from either quarantined branch). `STATUS =
RUST_CONTRACT_REVIEW`, requesting a complete exact-SHA review per §11.8.8. `NEXT_OWNER = Codex`.
Do not start Slice C (`PROV-012`). Do not start Layer 12.
