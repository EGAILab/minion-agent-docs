# Layer 11 Pass 2, Slice B — L11-SB-R001 through L11-SB-R005 remediation

## Candidates

```text
prior rejected candidate (first independent Rust contract review)
    code PR #31 @ 14fb5183f4978e3163e58a5a32b4481f496c7aa4
    docs PR #77 @ 2250f4dc770f533725c1cee05b046756f2034747

first independent Rust contract review (rejecting)
    docs PR #78 @ 25334e68981ed977dfef2731a4cbeed2cd142f06
    assurance/layers/11-pass2-slice-b-rust-contract-review.md
```

## Trigger check

First review of Slice B's own candidate; none of the five findings has itself survived a prior
review, and the slice has not accumulated three rejections. §11.8 convergence is NOT triggered.
Ordinary targeted remediation, addressing all five findings together since each is narrow and none
depends on characterizing a new semantic disagreement.

## L11-SB-R001 — is_subscription collapses absent into false

Independently re-confirmed: pinned Pi's `OAuthAuth.isSubscription?: boolean` is genuinely
optional -- absent/`undefined`, `false`, and `true` are three distinct observable states. The
candidate's `is_subscription: bool = False` field could not represent "absent" as anything other
than the SAME value as an explicit `false`.

**Fix:** `is_subscription: bool | None = None`. **New tests:** a default-value witness
(`is_subscription is None`, not `False`) and a three-state witness (absent/`False`/`True` all
independently constructed and observed). **Revert-and-confirm:** reverted to `bool = False`;
both new tests failed with the exact reported symptom (`assert False is None`). Restored; both
passed.

## L11-SB-R002 — ProviderAuthInteraction not statically usable as AuthInteraction

Independently reproduced the review's own exact witness before fixing anything:

```python
def as_base(value: ProviderAuthInteraction) -> AuthInteraction:
    return value
```

failed under the candidate's own `signal: Abortable` (mutable attribute) with `mypy`'s own
`Incompatible return value type ... expected "Abortable | None", got "Abortable"`. Root cause: a
mutable `Protocol` attribute is INVARIANT under Python's static-typing rules, which does not match
pinned Pi's own `ProviderAuthInteraction = AuthInteraction & { signal: AbortSignal }` intersection
type, under which a value with `signal` always present trivially satisfies "signal optionally
present" (ordinary structural subtyping).

**Fix:** independently verified, via two isolated `mypy --strict` probes before touching production
code, that declaring `signal` as a READ-ONLY `@property` in BOTH protocols (rather than a plain
attribute) makes the relationship covariant -- `ProviderAuthInteraction`'s own narrower `Abortable`
return correctly satisfies `AuthInteraction`'s own wider `Abortable | None` requirement -- and
separately confirmed a concrete implementation using an ORDINARY MUTABLE instance attribute (not
itself a `@property`) still satisfies a Protocol's own read-only property declaration, so no
concrete provider implementation is affected by this fix. **New evidence:** the exact
`as_base`-shaped assignability witness the review specified is now a permanent typing-fixture
check (`_as_base_interaction`/`_also_base_interaction` in
`tests/typing/valid_interaction_vocabulary.py`). **Revert-and-confirm:** reverted both `@property`
declarations back to plain attributes; `mypy` reproduced the exact review-reported diagnostic.
Restored; `mypy src/minion_agent tests/typing` returned clean, 72 source files.

## L11-SB-R003 — callback input bundles and result shapes underspecified

Re-read `packages/ai/src/auth/types.ts:170-230` directly. Confirmed the review's own finding: Pi's
`ApiKeyAuth.check`/`resolve` each take ONE structured input (`{ctx, credential?, signal}`); the
candidate's own Python signatures split this into three positional parameters, without the
normative spec ever stating this was a deliberate, disclosed mapping (as opposed to two
independent implementers reasonably choosing a bundled struct vs. positional arguments and both
being "correct").

**Fix:** rewrote the `spec/auth.md` `PROV-014` section to state every callable's own full input
bundle, requiredness, and async-result shape explicitly (all of `ApiKeyAuth.login`/`check`/
`resolve`, `OAuthAuth.login`/`refresh`/`to_auth`), and explicitly discloses the check/resolve
three-parameter rendering as a language MAPPING of Pi's own single structured input, stating
plainly that it changes no observable input value, requiredness, or result shape. Extended the
Python module's own `ApiKeyCheck`/`ApiKeyResolve` docstrings with the identical disclosure.

No production behavior changed (the Python signatures were already correct; only the spec's own
completeness was the defect) -- confirmed by rerunning the unchanged test suite.

## L11-SB-R004 — select-result test overclaims prompt() return behavior

Independently re-read the flagged test and the row's own `tests:` description; confirmed the
review's own finding exactly: the test constructs an `AuthPromptSelect` and asserts the FIRST
option's own stored `id`, never invoking any `AuthInteraction` or observing a `prompt()` return
value -- Slice B implements no concrete `AuthInteraction` at all, so no such behavioral witness is
currently possible.

**Fix:** renamed the test to `test_auth_prompt_select_stores_options_with_distinct_id_and_label_fields`,
rewrote its own docstring to state plainly what it does and does NOT prove, strengthened it to
assert `id != label` (catching an accidental field swap, which the original version's identical-
looking assertions would not have), and corrected the manifest's own `tests:` description to match.
The actual behavioral claim (`prompt()` returns `id`, not `label`) remains stated as NORMATIVE in
`spec/auth.md` (Pi's own doc comment is the authority for it), explicitly flagged there as awaiting
a real `AuthInteraction` implementation to test against, not evidenced by Slice B's own test suite.

## L11-SB-R005 — adopted public vocabulary frozen without a disposition

Independently re-read pinned Pi's own `types.ts:118-241` field declarations, confirming the
review's own finding: none of the public object/interface fields carry `readonly` (only the two
COLLECTION fields, `AuthPromptSelect.options`/`AuthEventInfo.links`, do -- both remain `tuple`s
here, unaffected by this fix, since a collection's own element-replacement restriction is a
different question from an ordinary field's own reassignability). The candidate's `frozen=True` on
every new dataclass was an unapproved, undisclosed divergence from that assignable-field
semantics -- and this project has ALREADY resolved the identical question once, for Layer-11
credentials (`PROV-006`, `L11-R006`/`L11-R009`): adopt Pi's assignable fields in full, no
intentional divergence approved without explicit owner governance, which does not exist here for
this vocabulary either.

**Fix:** removed `frozen=True` from all thirteen dataclasses (kept `slots=True`). **New test:**
`test_public_vocabulary_fields_are_mutable_matching_pi` constructs several representative
instances (`AuthPromptText`, `AuthPromptOption`, `AuthEventProgress`, `OAuthAuth`) and reassigns a
field on each, asserting the new value is observed. **Revert-and-confirm:** reverted all thirteen
`@dataclass(slots=True)` back to `@dataclass(frozen=True, slots=True)`; the new test failed with
the exact reported symptom (`dataclasses.FrozenInstanceError: cannot assign to field 'message'`).
Restored; the full 16-test suite passed.

## Fresh quality gates

- `tests/auth/test_interaction.py` (targeted, `--no-cov`): 16 passed, 0 failed.
- `tests/conformance/test_manifest_validation.py`: 8/8.
- `ruff check .` / `ruff format --check .`: clean, same pre-existing 7-file drift baseline.
- `mypy` (default gate, `files = ["src/minion_agent"]`): clean, 68 source files.
- `mypy` including all typing fixtures: clean, 72 source files.
- Full `pytest` suite (fresh, with coverage): 1337 passed, 19 xfailed (pre-existing, unrelated), 0
  failed.
- Coverage: 100.00% (`TOTAL` 3308 statements, 0 missed).
- Manual secret scan of changed files: clean.

## Next action

Push to the same candidate branches, updating PRs #31/#77 in place. `STATUS = RUST_CONTRACT_REVIEW`,
requesting a NEW complete exact-SHA review per §11.8.8 (prior approval is stale). `NEXT_OWNER =
Codex`. Do not start Slice C. Do not start Layer 12.
