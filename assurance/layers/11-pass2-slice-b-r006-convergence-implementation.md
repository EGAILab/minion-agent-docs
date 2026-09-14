# Layer 11 Pass 2, Slice B — §11.8 contract convergence: L11-SB-R003 (second fix) and L11-SB-R006

## Candidates

```text
rejected candidate (second independent Rust contract review)
    code PR #31 @ 907004181b6a6cadea5e899a87c77584a1787e55
    docs PR #77 @ c0c20d2a30f67d7fc414d605b00f7e0458a2af13

second independent Rust contract review (rejecting; §11.8 convergence trigger)
    docs PR #79 @ 2bc1dd2b04c075faf38a1980de148284dee541c7
    assurance/layers/11-pass2-slice-b-rust-contract-rereview.md

first independent Rust contract review (rejecting; for lineage only, already superseded)
    docs PR #78 @ 25334e68981ed977dfef2731a4cbeed2cd142f06
    assurance/layers/11-pass2-slice-b-rust-contract-review.md

pinned Pi: b7bb00b936dbe21b8e160b3e89efdec361846699
```

## §11.8 trigger check (mandatory, restated)

`L11-SB-R003` closed the original grouping-ambiguity half on the first remediation pass but was
found `PARTIALLY_RESOLVED_BLOCKING` on the second independent review for a distinct remaining
gap (failure/delivery semantics) -- the same finding ID surviving two independent reviews, meeting
the §11.8 trigger exactly, as recorded on coordination issue `#29`. This document is the
§11.8.6 implementation pass following that trigger; the characterization and challenge passes were
already performed and posted to issue `#29` (the convergence comment enumerating L11-SB-R003's
closed half, the re-verified Pi citations for its open half, and the L11-SB-R006 options analysis)
before any owner governance decision was requested.

## L11-SB-R003 — second fix: failure and delivery semantics

Independently re-verified every citation the re-review gave, directly against pinned Pi, before
writing anything:

- `packages/ai/src/models.ts:495-504` -- `Models.checkProviderAuth` `await`s `ApiKeyAuth.check(...)`
  inside its own `try`/`catch`; a rejection is caught and wrapped as an auth-check failure.
- `packages/ai/src/auth/resolve.ts:184-192` (`resolveApiKey`) -- `ApiKeyAuth.resolve` is `await`ed
  inside a `try`/`catch`; a rejection is caught and wrapped as an auth failure.
- `packages/ai/src/auth/resolve.ts:174-178` -- `OAuthAuth.toAuth` is `await`ed inside a `try`/`catch`;
  a rejection is caught and wrapped as an OAuth-derivation failure. This corrects the FIRST
  remediation pass's own wrong claim that `to_auth` was "not expected to raise" -- side-effect-free
  and "can fail" are independent properties, and Pi's own real call site treats it as fallible.
- direct `interaction.notify(...)` call sites in `packages/coding-agent/src/auth/openai-codex.ts:429,456`
  -- a direct, un-awaited, un-wrapped synchronous statement at both real call sites, no `try`/`catch`,
  no detachment/spawn mechanism. A synchronous throw propagates directly to the caller; `notify` is
  NOT fire-and-forget in the sense of "failures are swallowed."

**Fix:** rewrote `spec/auth.md`'s `PROV-014` section to state, for every callable
(`login`/`check`/`resolve`/`refresh`/`to_auth`), that it MAY raise/reject and that the later
orchestration owner determines wrapping/handling; corrected `notify()`'s own description from the
ambiguous "sync, fire-and-forget" to "SYNCHRONOUS, direct call -- NOT fire-and-forget/detached,"
stating explicitly that a thrown/raised exception propagates directly to the caller. Corrected the
prior pass's own wrong `to_auth`-does-not-raise claim. Made the identical corrections in the Python
module's own docstrings (`ApiKeyCheck`, `ApiKeyResolve`, `OAuthToAuth`, `AuthInteraction.notify`).

No production behavior changed: Python's own `Callable[..., Awaitable[T]]` and bare
`def notify(...) -> None` already permitted raising and already propagated synchronously; only the
prose was incomplete, exactly as the re-review's own classification (`CONTRACT_ASSURANCE_DEFECT`)
stated. Confirmed via the unchanged, still-passing `tests/auth/test_interaction.py` suite.

Pushed ahead of the owner's L11-SB-R006 governance decision, as commits `1818697` (code) /
`ea73cdd` (docs) on the same candidate branches -- see "Fresh quality gates" below for the combined
post-R006 gate run covering both fixes together.

## L11-SB-R006 — owner governance decision and implementation

### Independent re-verification of the review's own witness

Reproduced the review's own exact failing probe before analyzing further:

```python
def replace_signal(interaction: AuthInteraction, signal: Abortable) -> None:
    interaction.signal = signal
```

confirmed failing under the L11-SB-R002 fix (`signal` as a read-only `@property`) with `mypy`'s own
`Property "signal" defined in "AuthInteraction" is read-only`.

### Why no Python code change alone resolves this

Attempted a read/write `@property` with a matching `.setter`, narrowed identically on
`ProviderAuthInteraction`, in an isolated probe before concluding anything:

```python
class AuthInteraction(Protocol):
    @property
    def signal(self) -> Abortable | None: ...
    @signal.setter
    def signal(self, value: Abortable | None) -> None: ...

class ProviderAuthInteraction(Protocol):
    @property
    def signal(self) -> Abortable: ...
    @signal.setter
    def signal(self, value: Abortable) -> None: ...
```

This reintroduces the ORIGINAL `L11-SB-R002` failure: a read/write property with a setter is
invariant for the same reason a plain mutable attribute is, since `ProviderAuthInteraction`'s own
setter would need to accept ONLY `Abortable` -- narrower than `AuthInteraction`'s own setter
accepting `Abortable | None` -- which violates Liskov contravariance for the setter parameter. No
Python construct (attribute, read-only property, or read/write property with a setter) can hold
both "`ProviderAuthInteraction` is a subtype of `AuthInteraction`" and "`signal` is assignable
through an `AuthInteraction`-typed reference to `Abortable | None`" simultaneously, because jointly
they would permit writing `None` into storage a `ProviderAuthInteraction`-typed caller has already
assumed is never `None` -- a genuine, mathematically irreducible incompatibility between Pi's own
(TypeScript-unsound) mutable-property variance and Python's sound static type system, not a defect
in either the L11-SB-R002 fix or this project's own Python port.

Also confirmed (grep of `packages/ai/src`, `packages/coding-agent/src`): zero call sites anywhere
in pinned Pi ever reassign `.signal` on an interaction-shaped object after construction. This
narrowed the actual stakes without deciding the question -- consistent with this project's own
established precedent (`L11-R006`/`L11-R009`, and this same slice's own `L11-SB-R005`) that "Pi's
own type permits X" is treated as binding regardless of whether existing call sites exercise X,
so the finding was still escalated to owner governance rather than dismissed on this basis alone.

### Governance decision

Per `agent-workflow.md` §11.10, this genuine observable-type-guarantee divergence required owner
governance, not a unilateral implementation choice. The full options analysis (Option
A -- preserve subtyping via read-only properties, disclose the widened-reference assignment
limitation; Option B -- drop subtyping, restore full mutability; Option C -- further research) was
posted to coordination issue `#29` before any further code change. The owner approved **Option A**
in full, posted verbatim as the durable `GOVERNANCE_SOURCE`:

```text
https://github.com/EGAILab/minion-agent/issues/29#issuecomment-5664609556
```

Decision, exactly as approved: keep `signal` as a read-only `@property` on both
`AuthInteraction`/`ProviderAuthInteraction` (preserving the subtype relationship and the
provider-login guaranteed-signal invariant); classify the resulting widened-reference assignment
limitation as an INTENTIONAL, NARROW, owner-approved language-binding divergence; scope it
explicitly to widened-reference static assignment only -- NOT a runtime immutability requirement,
so a concrete implementation's own mutable `signal` field/setter through its own concrete type
remains unaffected; record the approval as `GOVERNANCE_SOURCE`; track it in a separate manifest
row rather than mixing it into `PROV-014`'s own otherwise-`adopted` disposition; give Rust
language-neutral guidance only (preserve the semantic contract, no Python-property-mechanics
prescription).

### Implementation

- **Code** (`src/minion_agent/auth/interaction.py`): no mechanism change -- `signal` remains the
  read-only `@property` design from the L11-SB-R002 fix, per the decision's own explicit
  "keep the read-only Protocol-property design" instruction. Extended `AuthInteraction`'s own
  docstring with the full divergence disclosure (citing `GOVERNANCE_SOURCE`, the Liskov proof, the
  tried-and-rejected setter approach, the zero-call-site finding, the exact scope, and a
  `PROV-015` cross-reference); extended `ProviderAuthInteraction`'s own docstring to cross-reference
  it. No `Any`, cast, or `type: ignore` was introduced anywhere, matching the decision's own
  explicit prohibition.
- **Manifest** (`pi-parity-manifest.yaml`): extended `PROV-014`'s own `rule:` text with the
  L11-SB-R003 second-fix paragraph and a pointer to the new row (keeping `PROV-014` itself
  `adopted` and coherent, per the decision's own "do not silently mix" instruction). Added a new
  `PROV-015` row, `disposition: intentional divergence`, citing the same `GOVERNANCE_SOURCE`
  permalink, the two Pi properties in tension, the soundness proof, the exact scope, and explicit
  Rust guidance mirroring the decision's own language. Manifest row count: 94 (was 93).
- **Spec** (`spec/auth.md`): inserted a new `## Interaction-type assignability divergence
  (\`PROV-015\`, intentional divergence)` section immediately after `PROV-014`'s own section and
  before the `PROV-013` section, documenting the same content normatively for a reader with no
  access to the manifest or this document. Annotated the pre-existing `PROV-014` "**Mutability.**"
  paragraph with a pointer to the new section, since its own prior unqualified "every field ...
  is ORDINARILY ASSIGNABLE" claim is no longer accurate for `signal` specifically without that
  cross-reference.
- **Permanent static-type evidence**: the decision's own "add permanent static-type evidence that
  `ProviderAuthInteraction` is accepted wherever `AuthInteraction` is required" requirement was
  already satisfied by the L11-SB-R002 fix's own `_as_base_interaction`/`_also_base_interaction`
  witness in `tests/typing/valid_interaction_vocabulary.py` -- confirmed still present and still
  passing under `mypy`; no new fixture file was needed.

## Fresh quality gates

Run after both the L11-SB-R003 second fix and the L11-SB-R006 implementation, at the current
(not-yet-pushed) working-tree state on `layer-11-pass2-slice-b-interaction-vocabulary` in both
`minion-agent` and `minion-agent-docs`:

- `ruff format --check .`: 7 files would be reformatted -- the same pre-existing baseline drift
  (`session/operations.py`, `tools/registry.py`, `tests/agent/test_instance.py`,
  `tests/conformance/session_runner.py`, `tests/conformance/transform_runner.py`,
  `tests/tools/test_post_execute.py`, `tests/tools/test_updates.py`), none of which this pass
  touched.
- `ruff check .`: clean, all checks passed.
- `mypy` (default gate, `src/minion_agent`): clean, 68 source files.
- `mypy src/minion_agent tests/typing`: clean, 72 source files.
- `pytest tests/auth/test_interaction.py --no-cov -q`: 16 passed, 0 failed (no behavior change --
  both fixes this round are docstring/spec/manifest only).
- `tests/conformance/test_manifest_validation.py`: 8 passed.
- Full `pytest` suite (fresh, with coverage): 1337 passed, 19 xfailed (pre-existing, unrelated),
  0 failed.
- Coverage: 100.00% (`TOTAL` 3308 statements, 0 missed).
- Manual secret scan of the three changed files (`interaction.py`, `pi-parity-manifest.yaml`,
  `spec/auth.md`): clean.

## Convergence checkpoint record

- Trigger: §11.8, `L11-SB-R003` surviving two independent reviews (see above).
- Characterization and challenge passes: performed and posted to issue `#29` prior to any owner
  decision (the convergence comment restating the re-verified Pi behavior matrix for R003's
  remaining gap, and the full options analysis for R006).
- Agreed-for-implementation checkpoint: the owner's `GOVERNANCE_SOURCE` comment at
  `https://github.com/EGAILab/minion-agent/issues/29#issuecomment-5664609556`, approving Option A.
- Implementation: this document.
- Fresh complete review: requested next, from Codex, against the updated exact SHAs once pushed --
  per §11.8.8, the prior COMMENTED/rejecting reviews do not carry forward.

## Next action

Push to the same candidate branches, updating PRs #31/#77 in place. `STATUS = RUST_CONTRACT_REVIEW`,
requesting a NEW complete exact-SHA review per §11.8.8 (both prior reviews are stale against the
updated SHAs). `NEXT_OWNER = Codex`. Slice C (`PROV-012`) remains NOT started. Layer 12 remains NOT
started.
