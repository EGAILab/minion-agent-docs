# Layer 11 — L11-R006/L11-R008 targeted-closure remediation (round 2) + L11-R009/L11-R010

## Review target rejected by this remediation

```text
code PR #25
    ffe43baf122e25156c6d206343fee07c3c849d6c

docs PR #54
    843b6581312c5dedece91beaae2eb9832fd29529

review PR #57
    b3e6a88cfa1f0399cf02a7f53287e9c09af7ac37

verdict
    REJECTED AT TARGETED CLOSURE GATE
```

## Trigger check (agent-workflow.md §11.8, mandatory)

`L11-R006` has now been raised, in refined form, by THREE independent reviews (docs PR #55, docs
PR #56, docs PR #57/this review) -- well past the two-repeat trigger, and this layer has now
accumulated three rejected contract reviews overall. Both §11.8 trigger conditions are met, several
times over. This remains the SAME convergence episode already opened for `L11-R006`/`L11-R008`
(`11-auth-foundation-r006-r008-convergence-agreement.md`) -- the targeted-closure review found the
prior implementation pass incomplete/inconsistent, not a new semantic disagreement requiring a new
characterization/challenge/agreement cycle. `L11-R009` and `L11-R010` are new findings, discovered
directly on the exact credential surface `L11-R006`'s own implementation touched -- both are folded
into this same remediation, per the same "one tightly-coupled semantic surface" allowance already
invoked for `L11-R008`.

## What the targeted-closure review found, and why the prior pass under-delivered

The owner's own governance decision (recorded in the convergence agreement) was correct and is NOT
revisited here. What was incomplete was its IMPLEMENTATION:

1. **`L11-R006`, still open**: the prior pass removed the shallow `MappingProxyType` wrapper and
   proved NESTED-value aliasing, but never actually exercised the review's own more direct minimal
   witness -- assigning a BRAND-NEW top-level key through the returned, statically-typed mapping
   itself (`credential.env["NEW"] = "v"`). Because `env`/`extra` were still typed as read-only
   `Mapping[...]`, this operation was rejected by mypy even though the underlying runtime `dict`
   would have permitted it -- a real, load-bearing gap: a typed Rust/Python caller following the
   PUBLIC API surface, not bypassing it via `# type: ignore`, could not actually exercise the
   agreed Pi-parity behavior at all.
2. **`L11-R008`, still open**: the new `_SecondNativeAuthContext` witness passed
   `os.path.expanduser("~")` (an ALREADY-EXPANDED absolute path) to `file_exists`, not a literal
   leading `~`. A non-compliant implementation that never expands `~` at all would pass this exact
   input unchanged, since the input no longer contains a `~` character by the time it reaches the
   method under test. The witness proved nothing about tilde-handling specifically.
3. **`L11-R009`, new**: the prior pass unfroze `env`/`extra`'s own VALUES but left both credential
   dataclasses themselves `frozen=True`, so ordinary scalar-field reassignment
   (`credential.key = "B"`) still raised `FrozenInstanceError` -- an inconsistent, partial
   application of the SAME owner decision (adopt Pi's live-reference behavior), since Pi's own
   plain credential objects permit reassigning ANY field, not only nested container values.
4. **`L11-R010`, new**: the prior pass's own witnesses constructed `ApiKeyCredential.env` with
   nested dict/list values to prove "recursive aliasing," but pinned Pi's own `ProviderEnv` type
   (`types.ts:113`) is `Record<string, string>` -- flat string-to-string only. Recursive JSON
   belongs exclusively to `OAuthCredential.extra`'s own open index-signature domain. The prior
   pass's own evidence was constructed outside `env`'s actual Pi-defined domain.

## Why this remediation does not require a new owner escalation

`L11-R009`'s own resolution -- unfreezing the credential dataclasses so scalar fields are
reassignable -- is the DEFAULT, no-extra-approval-needed path under the owner's own already-recorded
rationale: "the project's frozen policy requires Pi-visible behavior to be adopted unless there is
a sufficiently strong reason for an intentional divergence... therefore Layer 11 should preserve Pi
parity here." Pi's own credential objects permit scalar-field mutation with no exception carved out
for it; KEEPING the dataclasses frozen would be the divergence requiring approval, not removing
`frozen=True`. This is a consistent, complete APPLICATION of the existing agreed decision, not a
new governance question -- no second escalation to the repository owner was made or is required.

## Remediation, per finding

### `L11-R006` (refined witness)

- `test_credential.py`: replaced the flat env-mutation test with
  `test_w_r006_2_assigning_a_new_top_level_key_on_env_persists` -- constructs `ApiKeyCredential(
  env={})`, assigns `credential.env["NEW"] = "v"` with NO `# type: ignore`, and asserts the result.
  This only type-checks because `env`'s own field type changed from `Mapping[str, str] | None` to
  `dict[str, str] | None` (see `L11-R010` below).
- Added the equivalent for `extra`:
  `test_w_r006_new_top_level_key_assignment_on_extra_persists`.
- `test_store.py`: renamed/refocused the store-level integration witness to
  `test_w_r006_env_new_key_survives_a_store_round_trip` (new-key assignment through a `modify()`-
  returned credential, observed by a later `read()`) and added
  `test_w_r006_extra_nested_mutation_survives_a_store_round_trip` (the nested-value case, now
  correctly scoped to `extra` only per `L11-R010`).

### `L11-R008` (refined witness)

- `test_context.py`: `test_w_r008_1_a_second_native_auth_context_also_supports_leading_tilde` now
  calls `ctx.file_exists("~")` with the LITERAL string, not a pre-expanded path.
- Added `_NonExpandingAuthContext` and
  `test_w_r008_1_negative_control_a_non_expanding_context_fails_the_same_literal_input`, proving
  the positive witness actually discriminates (a non-compliant implementation fails it).
- Also fixed `DefaultAuthContext`'s own pre-existing `test_file_exists_expands_a_leading_tilde`,
  which had the identical non-discriminating shape, for consistency and stronger evidence (not
  itself a blocking finding, since `DefaultAuthContext`'s own correctness was never in question,
  but the same defect class was left uncorrected there and is fixed while in this exact area).

### `L11-R009` (new)

- `credential.py`: removed `frozen=True` from both `@dataclass(...)` decorators
  (`ApiKeyCredential`, `OAuthCredential`) -- `slots=True` retained.
- `test_credential.py`: added `test_w_r009_api_key_credential_scalar_fields_are_reassignable` and
  `test_w_r009_oauth_credential_scalar_fields_are_reassignable` (bare dataclass-level).
- `test_store.py`: added `test_w_r009_scalar_field_mutation_survives_a_store_round_trip` (the
  reviewer's own exact minimal witness: store a credential, mutate a scalar field on the object
  returned by `modify()`, confirm a later `read()` observes it).

### `L11-R010` (new)

- `credential.py`: `ApiKeyCredential.env` narrowed from `Mapping[str, str] | None` to
  `dict[str, str] | None` (flat, matching Pi's own `ProviderEnv`); `OAuthCredential.extra` changed
  from `Mapping[str, JsonValue]` to `dict[str, JsonValue]` (still fully open/recursive, now
  concretely mutable rather than merely readable). Both docstrings updated to state the domain
  split explicitly and cite `types.ts:113`.
- `test_credential.py`: `test_w_r006_1_mutating_the_original_env_mapping_after_construction_is_
  observable` narrowed to flat string values only (no nested dict/list); the nested-value
  constructor-aliasing witness (`test_w_r006_1_oauth_credential_extra_original_mapping_aliasing`)
  and the new nested-mutation witness
  (`test_w_r006_2_mutating_a_nested_value_reached_through_extra_persists`) both moved exclusively
  onto `OAuthCredential.extra`.

## Normative deltas

- `spec/auth.md`: the top-of-file vocabulary paragraph now states the `env`/`extra` domain split
  explicitly ("evidence for one field must never be constructed using the other's own domain");
  the credential value/reference semantics section extended to state scalar-field reassignability
  explicitly, corrected to describe the new-top-level-key witness (not only nested mutation), and
  the `AuthContext.file_exists` section's own prose was already correct (only its EVIDENCE needed
  fixing, confirmed by the review itself: "The normative spec, PROV-006, and AuthContext protocol
  documentation now correctly place leading-`~` support at protocol level").
- `pi-parity-manifest.yaml`, `PROV-006`: rule text rewritten to cover all four findings
  (`L11-R003`/`L11-R006`/`L11-R008`/`L11-R009`/`L11-R010`) with corrected, complete evidence lists.

## Fresh quality gates (this remediation)

- `pytest` (full suite, with coverage): 1278 passed, 19 xfailed (pre-existing, unrelated), 65
  skipped, 0 failed.
- Coverage: 100.00% (`TOTAL` 3127 statements, 0 missed).
- `ruff check .`: clean.
- `mypy`: clean, 66 source files -- including a direct positive check that
  `credential.env["NEW"] = "v"` and `credential.key = "B"` both type-check with no `# type:
  ignore`, closing the exact typed-mutation gap the review's own probe demonstrated.
- `ruff format --check .`: the same pre-existing 7-file drift, unchanged.
- `tests/test_layering.py`: 5/5.
- `tests/conformance/test_manifest_validation.py`: 8/8.
- `tests/conformance/test_schema_validation.py`: clean, unchanged.
- Manual secret scan of every changed `auth/`/`tests/auth/` file: only the same two synthetic
  `"sk-test"` placeholders already present -- no real credential.

## Next action

Push updated commits to the same candidate branches (`layer-11-pass1-auth-foundation` in both
repos), updating PRs #25/#54 in place. `STATUS = RUST_CONTRACT_REVIEW` (targeted closure review
re-requested for `L11-R006`, `L11-R008`, `L11-R009`, `L11-R010` specifically). `NEXT_OWNER =
Codex`. Do not implement Rust yet. If all four findings are provisionally closed and no other
blocker remains, perform the one final complete §11.8.8 review before any certification.
