# Layer 11 Pass 2 Slice B — independent Rust contract re-review

## Exact review target

- remediated code PR: `EGAILab/minion-agent#31` @
  `907004181b6a6cadea5e899a87c77584a1787e55`
- remediated docs PR: `EGAILab/minion-agent-docs#77` @
  `c0c20d2a30f67d7fc414d605b00f7e0458a2af13`
- prior rejected code: `14fb5183f4978e3163e58a5a32b4481f496c7aa4`
- prior rejected docs: `2250f4dc770f533725c1cee05b046756f2034747`
- prior review: docs PR `#78` @ `25334e68981ed977dfef2731a4cbeed2cd142f06`,
  `assurance/layers/11-pass2-slice-b-rust-contract-review.md`
- accepted code base: `main` @ `039050710579d6511a63c25077093bfe83006b11`
- accepted docs base: `master` @ `479e388599f4f36a19c15532fd2ce33531b02704`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`

Both candidate PRs were open, Ready for Review, and remote-reachable at these exact heads. The
latest structured comment on open coordination issue `EGAILab/minion-agent#29` records
`STATUS: RUST_CONTRACT_REVIEW`, `NEXT_OWNER: Codex`, and the same SHA pair. The owner governance
record at issue comment `#issuecomment-5659001629` remains valid and unchanged.

This was a complete re-review, not a prose-only closure check. Pinned Pi was re-read before the
remediation diff and Python implementation.

## Pi audit

Re-read directly:

- `packages/ai/src/auth/types.ts:118-241` — complete Slice B vocabulary and callable shapes.
- `packages/ai/src/models.ts:487-508,565-575` — check/login dispatch, normalization of
  `AuthInteraction` to `ProviderAuthInteraction`, and callback failure wrapping.
- `packages/ai/src/auth/resolve.ts:170-193` — `toAuth`/`ApiKeyAuth.resolve` rejection handling.
- direct auth-provider `interaction.notify(...)` call sites — synchronous direct invocation.

No Pi behavior remains uncertain.

## Previous-finding closure ledger

### L11-SB-R001 — RESOLVED

`OAuthAuth.is_subscription` is now `bool | None = None`. The permanent test distinguishes absent,
explicit false, and true. The spec and manifest preserve the three states. This matches Pi's
`isSubscription?: boolean`.

### L11-SB-R002 — RESOLVED, with a distinct new mutability finding below

The exact prior witness now type-checks:

```python
def as_base(value: ProviderAuthInteraction) -> AuthInteraction:
    return value
```

Read-only protocol access makes the required-signal protocol covariantly usable as the
optional-signal protocol. That closes the original subtype failure. Whether the chosen mechanism
also preserves Pi's assignable `signal` field is a separate observable dimension and is recorded
as new `L11-SB-R006`, rather than silently reopening the narrower original diagnosis.

### L11-SB-R003 — PARTIALLY_RESOLVED_BLOCKING

The spec now lists each callback's inputs/results and explicitly permits idiomatic grouping of
`ApiKeyAuth.check/resolve`'s `{ctx, credential?, signal}` bundle. That closes the original grouping
ambiguity. Pinned Pi's actual call sites construct the object with a `credential` member whose
value may be `undefined`, so Python's `None` value mapping does not lose a call-site state here.

The correction is incomplete for failure semantics:

- Pi awaits `ApiKeyAuth.check`; rejection is caught and wrapped as an auth-check failure
  (`models.ts:495-504`).
- Pi awaits `ApiKeyAuth.resolve`; rejection is caught and wrapped as an auth failure
  (`resolve.ts:184-192`).
- Pi awaits `OAuthAuth.toAuth`; rejection is caught and wrapped as an OAuth derivation failure
  (`resolve.ts:174-178`).
- `AuthInteraction.notify` is a direct synchronous `void` call. A synchronous throw propagates;
  it is not a detached/spawned notification.

The remediated spec states errors for login and refresh, but not check/resolve, and says `to_auth`
is merely “not expected to raise.” It labels `notify` “sync, fire-and-forget,” which can reasonably
be implemented either as direct synchronous delivery or detached best-effort delivery. Python's
`Callable[..., Awaitable[T]]` implicitly permits exceptions, but Rust must choose an explicit
`Result`/error surface. Two independent Rust implementations can therefore satisfy the current
prose while disagreeing observably when these callbacks fail.

Classification: `CONTRACT_ASSURANCE_DEFECT`.

Minimal correction: specify language-neutrally that all async auth callables may fail/reject and
that the later orchestration owner determines wrapping/handling; define `notify` as direct
synchronous invocation whose throw propagates, not fire-and-forget detachment. Rust may choose a
typed error, but must be able to represent these failures without redesign.

### L11-SB-R004 — RESOLVED

The test, manifest, and assurance now accurately claim construction/field-shape evidence only.
The `prompt(select)` returns-option-id behavior remains normative and is explicitly assigned an
executable-evidence obligation when the first concrete interaction seam is introduced. No fake
behavioral proof is counted for this vocabulary-only slice.

### L11-SB-R005 — RESOLVED

All thirteen new public dataclasses are mutable, while the two Pi-readonly collections remain
tuples. The new runtime witness confirms representative reassignment and source inspection confirms
`frozen=True` was removed from every new class.

## New finding

### L11-SB-R006 — `PI_PARITY_DEFECT` — the covariance fix makes `AuthInteraction.signal` read-only

Pinned Pi's `AuthInteraction.signal?: AbortSignal` and the required signal in its
`ProviderAuthInteraction` intersection are not `readonly`. The remediated normative spec also says
every non-collection field in this section is ordinarily assignable.

Minimal static witness against the candidate:

```python
def replace_signal(interaction: AuthInteraction, signal: Abortable) -> None:
    interaction.signal = signal
```

Expected from Pi/current spec: assignment is allowed.

Candidate observation under strict mypy:

```text
Property "signal" defined in "AuthInteraction" is read-only
```

A concrete class with a mutable attribute satisfying a read-only protocol does not close this:
code receiving the public `AuthInteraction` type still cannot perform an assignment Pi and the
spec permit. The remediation restored covariance by dropping a different adopted capability.

Minimal correction: characterize and model both requirements together — normalized interaction
subtyping and assignable signal — or explicitly obtain governance approval and disposition for a
language-level divergence if Python's static type system cannot expose both safely. Permanent
typing evidence must cover both the prior `ProviderAuthInteraction -> AuthInteraction` witness and
the assignment witness above. Do not weaken the already-closed dataclass mutability rule.

## Contract and architecture review

- Per-variant dataclasses/type aliases remain an acceptable language mapping of Pi's tagged
  unions; typed Rust enums are independently implementable.
- Pi-readonly option/link collections remain correctly represented as immutable sequences.
- `ProviderAuth`'s non-empty construction invariant is parity-neutral hardening of Pi's binding
  requirement.
- `PROV-013` orchestration remains coherently deferred and was not implemented accidentally.
- Existing certified Rust `AuthContext`, credential, `Abortable`, and async callback foundations
  are sufficient once R003/R006 are resolved. No certified lower layer requires reopening.
- No canonical runner exists for this pure vocabulary slice and none is fabricated. Language-level
  shape/typing evidence is appropriate, subject to the two blockers above.

## Fresh evidence

Executed against the exact remediated code SHA:

- `pytest tests/auth/test_interaction.py --no-cov -q`: `16 passed`.
- `mypy src/minion_agent tests/typing`: success, `72 source files`.
- `ruff check` on the changed Slice B Python files: clean.
- `pytest tests/conformance/test_manifest_validation.py --no-cov -q`: `8 passed`.
- full `pytest`: `1337 passed, 19 xfailed`, coverage `100.00%` (`3308` statements, `0` missed).
- exact subtype probe: passes.
- exact signal-assignment probe: fails with the read-only-property diagnostic above.

Green repository gates do not override an observable public-type mismatch or an incomplete Rust
failure contract.

## Convergence trigger

`L11-SB-R003` has now survived two independent reviews: the first review found the callback
contract incomplete, and this complete re-review confirms that input/result grouping was repaired
but failure/delivery semantics remain unresolved. This meets the mandatory §11.8 trigger exactly.
The new `L11-SB-R006` is also tightly coupled to the prior R002/R005 type-shape fixes: one attempted
mechanism preserved subtyping by removing assignability. The next state is therefore
`CONTRACT_CONVERGENCE`, not another unconstrained point-fix pass.

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
`907004181b6a6cadea5e899a87c77584a1787e55` and docs
`c0c20d2a30f67d7fc414d605b00f7e0458a2af13`.

No Python, shared semantic, canonical, or Rust files were modified by this review. Only this new
review artifact was added; the original rejected review remains unchanged.

## Next action

Enter §11.8 contract convergence on the narrow remaining surfaces:

1. finish L11-SB-R003's callback failure/delivery semantics; and
2. resolve L11-SB-R006's combined subtyping-plus-mutability contract with discriminating static
   witnesses.

The checkpoint must record the Pi behavior matrix, the Rust-representable failure/result surface,
both interaction typing witnesses, and the agreed language-neutral contract before implementation
resumes.

Any updated code/docs SHA requires another independent exact-SHA review. Do not start Slice C,
implement Rust Slice B, or start Layer 12.
