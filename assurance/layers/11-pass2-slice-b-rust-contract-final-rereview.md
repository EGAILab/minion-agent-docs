# Layer 11 Pass 2 Slice B — independent Rust contract final re-review

## Exact review target

- Code PR `EGAILab/minion-agent#31`: `985874f1566bc34a6622a2f16a4621166a272e9d`
- Docs PR `EGAILab/minion-agent-docs#77`: `f6aa34296c0ebfda32ff3998ec6ff007ccba0ced`
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Coordination: `EGAILab/minion-agent#29`, `STATUS = RUST_CONTRACT_REVIEW`,
  `NEXT_OWNER = Codex`, with the same remote-reachable candidate heads.
- Prior rejected exact-SHA reviews remain separate in docs PRs #78, #79, and #80.

This is a complete §11.8.8 review of the final Slice-B candidate. It is review evidence only: no
candidate semantic file, Python file, Rust file, Slice-C work, or Layer-12 work was changed.

## Authority and Pi audit

Reviewed in the required order: pinned Pi, normative specification, parity manifest, language
evidence, existing Rust feasibility, assurance lineage, and Python only as secondary evidence.
Directly re-read:

- `packages/ai/src/auth/types.ts:118-241` (`AuthPrompt`, `AuthEvent`, `AuthInteraction`,
  `ProviderAuthInteraction`, `ApiKeyAuth`, `OAuthAuth`, `ProviderAuth`);
- `packages/ai/src/models.ts:475-615` (`checkProviderAuth`, `Models.login` and credential commit);
- `packages/ai/src/auth/resolve.ts:127-193` (`refresh`, `toAuth`, and API-key resolution boundaries);
- `packages/ai/src/auth/oauth/openai-codex.ts:429,456` (direct `notify` calls).

Pi confirms that `login` is awaited through `raceWithAbortSignal` without a surrounding login-call
`try`/`catch`; the later `models.ts:591-613` catch covers credential mutation only. Pi separately
wraps `check`, `resolve`, `refresh`, and `toAuth` at their cited consumers. The candidate now states
that distinction exactly. The live path for the synchronous `notify` witnesses is also correct.

## Complete finding ledger

| Finding | Independent result | Status |
|---|---|---|
| L11-SB-R001 | `is_subscription: bool | None` preserves absent/false/true. | CLOSED |
| L11-SB-R002 | Read-only protocol properties preserve the required-to-optional structural subtype. | CLOSED |
| L11-SB-R003 | Every callable shape, language mapping, fallibility, and delivery boundary is explicit. | CLOSED |
| L11-SB-R004 | Evidence no longer overclaims an unimplemented prompt-return behavior. | CLOSED |
| L11-SB-R005 | Public vocabulary dataclasses remain assignable; only Pi-readonly collections use tuples. | CLOSED |
| L11-SB-R006 | The unavoidable Python variance trade-off is isolated in PROV-015 and backed by the explicit owner decision at issue #29 comment `5664609556`. | CLOSED |
| L11-SB-R007 | Login wrapping and the Codex OAuth source path are corrected in live spec, manifest, and code documentation. The superseded bad path is retained only in immutable historical evidence and is explicitly identified by the new correction artifact. | CLOSED |

## Contract and implementation-quality audit

- PROV-014 has one coherent adopted subject: the interaction/auth-method vocabulary.
- PROV-015 alone records the narrow, owner-approved Python static-binding divergence. It does not
  prescribe Python mechanics to Rust and introduces no runtime immutability.
- PROV-013 remains explicitly deferred orchestration and is not falsely counted as Slice-B evidence.
- `ProviderAuth` enforces Pi's at-least-one-method invariant.
- Optional fields preserve missing/false distinctions; callable argument and result shapes are
  language-neutral despite the disclosed Python positional mapping.
- No runner simulates behavior, no placeholder is counted as implemented evidence, and Slice B
  requires no certified-lower-layer semantic delta.
- An idiomatic Rust implementation can represent the unions with enums, the callable surfaces with
  traits/futures, required versus optional signals with typed views, and mutable public vocabulary
  without consulting Python control-flow mechanics.

No active `PI_PARITY_DEFECT`, `CONTRACT_ASSURANCE_DEFECT`, `PI_BEHAVIOR_UNCERTAIN`, or unapproved
observable divergence was found.

## Fresh gates

Run in a clean detached worktree at the exact code candidate:

- `uv run pytest -q`: **1337 passed, 19 xfailed, 0 failed**; **100.00%** coverage (3308/3308).
- `uv run ruff check .`: PASS.
- `uv run mypy src/minion_agent tests/typing`: PASS, 72 source files.
- `uv run pytest tests/auth/test_interaction.py --no-cov -q`: **16 passed**.
- `uv run pytest tests/conformance/test_manifest_validation.py --no-cov -q`: **8 passed**.
- `uv run ruff format --check .`: reports the same seven pre-existing drift files documented by
  the candidate; none is changed by Slice B or L11-SB-R007.

## Verdict

```text
Layer 11 Pass 2 Slice B shared contract
    APPROVED FOR MERGE / NEXT-PHASE USE

Python Slice B
    CERTIFIED

Rust Slice B
    NOT_IMPLEMENTED

Layer 11 Pass 2
    NOT CLOSED

Slice C / PROV-012
    NOT STARTED

Layer 12
    NOT STARTED
```

Approval applies only to the exact two candidate SHAs above. It does not approve later commits,
implement Rust Slice B, close Layer 11 Pass 2, authorize PROV-013 orchestration, begin Slice C, or
begin Layer 12.
