# Layer 11 Pass 2, Slice B — L11-SB-R007 documentary correction

## Candidates

```text
rejected candidate (third independent Rust contract review)
    code PR #31 @ 9e056afda7b27ce5b25092edbf47751bcaffec68
    docs PR #77 @ 1cacc9043b14f2a66be5e8896e50cba5ec63b519

third independent Rust contract review (rejecting, one narrow finding)
    docs PR #80 @ c75f939d7a69daa9dcca34ce94d63b8543bdb298
    assurance/layers/11-pass2-slice-b-rust-contract-final-review.md

pinned Pi: b7bb00b936dbe21b8e160b3e89efdec361846699
```

## §11.8 mandatory trigger check

`L11-SB-R007` is a NEW finding ID -- zero prior rejections on this exact ID, so the "same finding
survives two independent reviews" condition does not apply to it directly. The LAYER/SLICE as a
whole has now accumulated three rejected contract reviews (docs PR #78, #79, #80), which DOES meet
the second §11.8 trigger condition on its own terms.

Proceeding with an ordinary targeted point-fix instead of re-entering full `CONTRACT_CONVERGENCE`
is a deliberate decision, stated explicitly per §11.8's own mandatory-trigger-check requirement,
not a default: the third review's own evidence already narrows the remaining surface to two
mechanically-bounded, directly-cited documentary corrections (a call-site-accuracy overstatement in
one normative paragraph, and one nonexistent file path in a since-superseded assurance artifact),
with a Pi behavior matrix that is not in dispute and no new semantic disagreement to characterize.
This is not genuine unresolved semantic breadth requiring another characterization/challenge cycle
-- entering full convergence here would add process overhead without adding information, matching
the review's own recorded reasoning in `11-pass2-slice-b-rust-contract-final-review.md`'s own
"Convergence/final-review status" section.

## Independent re-verification of both defects

Re-read pinned Pi directly (`ref-repos/pi` at the pinned SHA) before touching any prose, rather
than accepting the review's own citations at face value:

**Defect 1 -- login is not wrapped, unlike check/resolve/refresh/to_auth.**
`packages/ai/src/models.ts:565-575`:

```typescript
async login(providerId: string, type: AuthType, interaction: AuthInteraction): Promise<Credential> {
    const signal = operationSignal(interaction.signal);
    signal.throwIfAborted();
    const provider = this.providers.get(providerId);
    if (!provider) throw new ModelsError("provider", `Unknown provider: ${providerId}`);
    const method = type === "oauth" ? provider.auth.oauth : provider.auth.apiKey;
    if (!method?.login) {
        throw new ModelsError("auth", `${provider.name} does not support ${type} login`);
    }
    const loginOperation: Promise<Credential> = method.login({ ...interaction, signal });
    const credential = await raceWithAbortSignal(loginOperation, signal);
    ...
```

Confirmed: no `try`/`catch` encloses `method.login(...)` or the `raceWithAbortSignal` await at
lines 574-575. `Models.login()` does have a LATER `try`/`catch` at `models.ts:591-613`, but reading
its own body confirms that block wraps only the subsequent credential-store `modify()` mutation
step, never the login call itself. The prior revision's blanket "every async callable ... each of
which awaits the callable inside its own try/catch and wraps a rejection" statement was therefore
false for both `ApiKeyAuth.login` and `OAuthAuth.login` (both routed through this same
`Models.login()` call site, selected via `type === "oauth" ? provider.auth.oauth :
provider.auth.apiKey`).

**Defect 2 -- nonexistent assurance path.** Searched the pinned Pi tree directly:

```text
$ find . -iname "openai-codex.ts"
./packages/ai/src/auth/oauth/openai-codex.ts
./packages/ai/src/providers/openai-codex.ts
$ ls packages/coding-agent/src/auth/openai-codex.ts
ls: cannot access 'packages/coding-agent/src/auth/openai-codex.ts': No such file or directory
```

Confirmed: `packages/coding-agent/src/auth/openai-codex.ts` does not exist anywhere in pinned Pi.
The real file is `packages/ai/src/auth/oauth/openai-codex.ts`, containing `interaction.notify(...)`
at exactly lines 429 and 456 as previously cited (the LINE numbers were always correct; only the
directory prefix was wrong). Grepped every changed file across both repos for the wrong path:
found it in exactly one place, `assurance/layers/11-pass2-slice-b-r006-convergence-implementation.md`
line 45 -- an already-published historical review artifact, left unmodified per this project's own
"preserve historical review artifacts, append remediation/re-review evidence instead of rewriting
history" rule. `spec/auth.md` and `interaction.py` themselves only ever cited the bare filename
(`openai-codex.ts:429`, `:456`, no directory prefix) -- ambiguous but not literally the wrong path
-- and are both now upgraded to the fully-qualified, unambiguous path as part of this fix, closing
off the ambiguity the review's own finding implicitly flagged as a documentary-quality risk.

## Fix

- **`spec/auth.md`** (`PROV-014` section, "Failure and delivery semantics" paragraph): replaced the
  single blanket wrapping claim with two explicitly distinguished groups --
  `check`/`resolve`/`to_auth`/`refresh` (wrapped at their own cited call sites, unchanged citations)
  versus `login` (NOT wrapped, citing `models.ts:565-575` for the unwrapped call and
  `models.ts:591-613` for the unrelated later mutation-only wrapping an earlier revision had
  incorrectly generalized from). Upgraded the `notify()` citation to the fully-qualified
  `packages/ai/src/auth/oauth/openai-codex.ts:429`, `:456`.
- **`pi-parity-manifest.yaml`** (`PROV-014` row): added a "THIRD CORRECTION (`L11-SB-R007` ...)"
  paragraph mirroring the spec fix exactly, including the mandatory-trigger-check statement above;
  upgraded the same `notify()` citation to the fully-qualified path in the existing "SECOND
  CORRECTION" paragraph.
- **`interaction.py`**: upgraded `AuthInteraction`'s own `notify()` docstring paragraph to the
  fully-qualified path; extended `ApiKeyLogin`'s own docstring with an "UNWRAPPED AT PI'S OWN REAL
  CALL SITE (`L11-SB-R007` ...)" paragraph citing the same evidence, and `OAuthLogin`'s own
  docstring with a shorter cross-reference to it (both auth-method variants share the identical
  `Models.login()` call site).
- No Python behavior, type signature, or test assertion changed -- confirmed by rerunning the
  unchanged `tests/auth/test_interaction.py` suite (16/16, unchanged) and the full suite below.
  Matches the review's own explicit "No production change is required" / "No Python behavior or
  type design needs to change for this finding" classification.

## Fresh quality gates

- `ruff format --check .`: 7 pre-existing baseline-drift files, none touched by this pass (same
  baseline as every prior round this slice).
- `ruff check .`: clean, all checks passed.
- `mypy` (default gate, `src/minion_agent`): clean, 68 source files.
- `mypy src/minion_agent tests/typing`: clean, 72 source files.
- `pytest tests/auth/test_interaction.py --no-cov -q`: 16 passed, 0 failed (no behavior change).
- `tests/conformance/test_manifest_validation.py`: 8 passed.
- Full `pytest` suite (fresh, with coverage): 1337 passed, 19 xfailed (pre-existing, unrelated),
  0 failed.
- Coverage: 100.00% (`TOTAL` 3308 statements, 0 missed).
- Manual secret scan of the three changed files (`interaction.py`, `pi-parity-manifest.yaml`,
  `spec/auth.md`): clean.

## Next action

Push to the same candidate branches, updating PRs #31/#77 in place. `STATUS = RUST_CONTRACT_REVIEW`,
requesting a new complete exact-SHA review per §11.8.8 (all three prior reviews are stale against
the updated SHAs). `NEXT_OWNER = Codex`. Slice C (`PROV-012`) remains NOT started. Layer 12 remains
NOT started.
