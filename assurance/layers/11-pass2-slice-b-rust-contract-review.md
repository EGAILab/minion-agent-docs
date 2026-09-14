# Layer 11 Pass 2 Slice B — independent Rust contract review

## Exact review target

- code PR: `EGAILab/minion-agent#31` @
  `14fb5183f4978e3163e58a5a32b4481f496c7aa4`
- docs PR: `EGAILab/minion-agent-docs#77` @
  `2250f4dc770f533725c1cee05b046756f2034747`
- accepted code base: `main` @ `039050710579d6511a63c25077093bfe83006b11`
- accepted docs base: `master` @ `479e388599f4f36a19c15532fd2ce33531b02704`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- coordination: `EGAILab/minion-agent#29`; its latest structured handoff comment names
  `NEXT_OWNER: Codex`, `NEXT_ACTION: complete independent exact-SHA review`, and the exact heads
  above. The issue body itself still describes the preceding Slice-A-to-Slice-B handoff; this
  review used the newer structured comment as the current coordination record.
- governance source checked: the owner message recorded verbatim at
  `https://github.com/EGAILab/minion-agent/issues/29#issuecomment-5659001629` authorizes the
  `PROV-013`/`PROV-014` split, adopts the interaction vocabulary, and keeps orchestration and Slice
  C out of scope.

Both candidate PRs were open, Ready for Review, mergeable, remote-reachable, and based on the
accepted Slice A defaults when this review began. Neither branch is derived from the quarantined
Pass-2 incident artifacts.

## Independent Pi audit

Read pinned Pi first, before the candidate implementation:

- `packages/ai/src/auth/types.ts:118-241`: `AuthPrompt`, `AuthInfoLink`, `AuthEvent`,
  `AuthInteraction`, `ProviderAuthInteraction`, `ApiKeyAuth`, `OAuthAuth`, `ProviderAuth`.
- `packages/ai/src/models.ts`: login normalization from `AuthInteraction` to
  `ProviderAuthInteraction` and provider login dispatch.
- relevant auth call sites for optional `isSubscription` observation.

The union members, optional fields, readonly option/link arrays, async callback results, and the
at-least-one-auth-method binding are known. No Pi uncertainty remains.

The candidate's per-variant class/type-alias representation is an acceptable language mapping of
Pi's discriminated unions: class/enum variant identity supplies the discriminator, and Rust can
use typed enums without copying Python dataclass mechanics. Tuple use for Pi's readonly arrays is
also coherent. Enforcing the documented `ProviderAuth` non-empty invariant at construction is
parity-neutral hardening.

## Findings

### L11-SB-R001 — `PI_PARITY_DEFECT` — optional `isSubscription` is collapsed into `false`

**Pi/source basis:** `OAuthAuth.isSubscription?: boolean` at pinned
`packages/ai/src/auth/types.ts:211`. The three observable states are absent/`undefined`, `false`,
and `true`; the workflow explicitly requires missing/null/false distinctions to be audited.

**Minimal witness:** construct an OAuth auth-method value without supplying `isSubscription`.

- Pi expected: the property is absent (and a direct read yields `undefined`).
- candidate observed: `OAuthAuth(...).is_subscription is False`; the field type is `bool` and the
  default is `False`.
- discriminating reason: an implementation cannot distinguish omitted from explicitly false, so
  the adopted public vocabulary has narrowed Pi's optional field.

**Minimal correction:** represent the field as genuinely optional (`bool | None`, absent default)
and add witnesses covering absent, explicit false, and true. Keep Slice C behavior out of scope.

### L11-SB-R002 — `PI_PARITY_DEFECT` — normalized interaction is not a subtype of the base interaction

**Pi/source basis:** pinned Pi defines
`ProviderAuthInteraction = AuthInteraction & { signal: AbortSignal }` at `types.ts:164`. A
provider-normalized interaction therefore remains usable wherever `AuthInteraction` is accepted;
it only strengthens `signal` from optional to required.

**Minimal witness:** under the candidate's own strict static-type gate:

```python
def as_base(value: ProviderAuthInteraction) -> AuthInteraction:
    return value
```

- Pi expected: valid by the intersection/subtype definition.
- candidate observed: mypy reports `Incompatible return value type`; `signal` expected
  `Abortable | None`, got `Abortable`.
- discriminating reason: the committed typing fixture avoids rather than proves the required
  relationship by defining two unrelated fake classes. Its claim that a matching object conforms
  to both is contradicted by the candidate's own type checker.

**Minimal correction:** model the strengthened interaction so one concrete normalized interaction
is statically usable as both public interfaces, and add this exact assignment/subtyping witness to
the permanent typing fixture. The implementation mechanism is language-specific; the relationship
is normative.

### L11-SB-R003 — `CONTRACT_ASSURANCE_DEFECT` — auth callback inputs are underspecified and Python silently changes Pi's grouping

**Pi/source basis:** `ApiKeyAuth.check` and `resolve` each accept one structured input containing
`ctx`, optional `credential`, and required `signal` (`types.ts:182-198`). `login`, OAuth `login`,
`refresh`, and `toAuth` have their own distinct required argument and async-result shapes.

The normative Slice B section reduces these to `ApiKeyAuth{name, resolve, login?, check?}` and
`OAuthAuth{name, login, refresh, to_auth, ...}`. It does not state the callback inputs,
requiredness, async results, or whether Pi's structured check/resolve input is preserved or mapped
idiomatically. Python then defines check/resolve as three positional arguments, with
`credential` always present as `None` rather than a structured optional member. The manifest calls
the row adopted but records no disposition for this mapping.

Two independent Rust implementers can reasonably choose a typed input struct or three arguments
and both satisfy the current prose. That is precisely the ambiguity the shared contract must
remove before Rust implementation.

**Minimal correction:** specify every callable's semantic input bundle, optionality, await/result
shape, and error behavior language-neutrally. State whether languages may group the check/resolve
bundle idiomatically; if so, make clear that this is a mapping rather than a Pi-visible semantic
change. Align Python evidence to the resolved rule.

### L11-SB-R004 — `CONTRACT_ASSURANCE_DEFECT` — evidence overclaims select-result behavior

**Pi/source basis:** `AuthInteraction.prompt()` returns the selected option's `id`, not its label
(`types.ts:149-160`).

The manifest says `tests/auth/test_interaction.py` covers “AuthPromptSelect option id vs label,”
but the test only asserts that the first stored option has `id == "browser"`. It never invokes an
interaction, makes a selection, or observes the returned value. The assurance artifact itself
acknowledges that the behavior is “documented, not independently re-derivable from a pure-data
test alone.”

**Minimal correction:** do not claim the construction test proves return semantics. Either add a
real interaction-level witness through an actual implementation seam, or explicitly assign that
behavioral evidence obligation to the later slice that first supplies that seam while keeping the
current Slice B claim limited to vocabulary shape.

### L11-SB-R005 — `PI_PARITY_DEFECT` — adopted public values are frozen without a disposition

**Pi/source basis:** the fields in pinned Pi's `AuthPrompt`, `AuthInfoLink`, `AuthEvent`,
`ApiKeyAuth`, `OAuthAuth`, and `ProviderAuth` public object/interface shapes are not `readonly`
(only the two collection values are readonly). Field reassignment is therefore allowed.

**Minimal witness:** construct an `AuthPromptText`, then assign a different `message`; construct an
`OAuthAuth`, then assign a different `name` or `isSubscription` value.

- Pi expected: ordinary property reassignment succeeds.
- candidate observed: every new dataclass is `frozen=True`; Python raises `FrozenInstanceError`.
- discriminating reason: this is a directly observable restriction on the adopted public
  vocabulary, not merely internal storage. The candidate manifest explicitly advertises frozen
  dataclasses while retaining disposition `adopted`; no intentional divergence is recorded.

This project already resolved the same public-value question for Layer-11 credentials by adopting
Pi's assignable fields unless a divergence is approved. Existing frozen internal/result values do
not silently authorize freezing this newly adopted public configuration/callback vocabulary.

**Minimal correction:** preserve assignability for Pi's non-readonly public fields, or obtain and
record explicit governance approval for an intentional divergence. Retaining tuples for Pi's
readonly option/link arrays is unaffected.

## Evidence and gates

Fresh checks against the exact candidate:

- `pytest tests/auth/test_interaction.py --no-cov -q`: `14 passed`.
- `mypy src/minion_agent tests/typing`: success, `72 source files`.
- `pytest tests/conformance/test_manifest_validation.py --no-cov -q`: `8 passed`.
- targeted `ruff check` on the three new Python files: clean.
- independent negative typing probe for `ProviderAuthInteraction -> AuthInteraction`: failed with
  the exact incompatible-`signal` diagnostic recorded in L11-SB-R002.
- direct runtime shape probe: no `type` attribute (accepted class-variant mapping), frozen field
  assignment raises, and omitted `is_subscription` observes `False`.

Green construction and repository gates do not override the type/contract failures above. A full
1,335-test rerun was not needed to establish this review-only rejection; the candidate's reported
full-suite result is not disputed.

No shared files, Python files, Rust production, Rust tests, or canonical scenarios were modified
by this review. Only this review artifact was added.

## Rust implementability

The already-certified Rust auth foundation supplies typed credentials, `AuthContext`, and
`Abortable`. Rust can idiomatically add enum variants, callback traits/futures, and a validated
`ProviderAuth` once the shared contract resolves the findings above. It should not have to consult
Python mechanics to decide optional-state preservation, the interaction subtype relationship, or
callback argument grouping.

`PROV-013` orchestration remains correctly deferred. Slice C (`PROV-012`) and Layer 12 remain not
started. No certified lower layer needs reopening.

## Verdict

```text
shared Layer-11 Pass-2 Slice-B contract
    REJECTED

Python Slice B
    REOPENED

Rust Slice B
    BLOCKED / NOT_IMPLEMENTED

Layer 11 Pass 2
    NOT CLOSED

Slice C / PROV-012
    NOT STARTED

Layer 12
    NOT STARTED
```

The verdict applies only to code
`14fb5183f4978e3163e58a5a32b4481f496c7aa4` and docs
`2250f4dc770f533725c1cee05b046756f2034747`.

## Next action

Return L11-SB-R001 through L11-SB-R005 to the shared/Python owner for narrow remediation. Any new
candidate SHA requires a new independent exact-SHA review. Do not start Slice C, implement Rust
Slice B, or start Layer 12.
