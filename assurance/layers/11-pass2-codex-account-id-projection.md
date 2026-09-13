# Layer 11 Pass 2, Slice A — Codex account-id projection (`PROV-011`)

**Status:** `IMPLEMENTED, PENDING INDEPENDENT REVIEW`. Layer 12 was not started.

## Scope decision

Coordination issue #27 recorded an explicit owner decision before implementation began: Pass 2
implements PROV-011 (JWT account-id projection) and, in a later slice, PROV-012 (Codex network
integration). PROV-013 (`resolveProviderAuth`/`Models.checkAuth/getAuth/login/logout`
orchestration) is deferred -- Minion's own `LlmService` (`llm/service.py`) has no auth integration
point yet (only `register`/`models`/`stream`), and wiring auth in requires either extending an
already-certified Layer 06/07/10 contract or designing a new composing module. This slice (Slice A)
covers only PROV-011, the pure/non-network half, per this project's own semantic-slicing
convention (`agent-workflow.md` §4.2).

## Pi audit

Read directly, not inferred from documentation, before writing any code:

- `packages/ai/src/auth/oauth/openai-codex.ts` (`decodeJwt`, `getAccountId`,
  `credentialsFromToken`, `OpenAICodexOAuth.toAuth`) -- the JWT decode/projection functions this
  row ports.
- `packages/ai/src/auth/oauth/oauth-page.ts` -- confirmed static, deterministic, HTML-escaped
  output with no embedded secrets (relevant to `PROV-012`'s own future slice, not this one).
- `packages/ai/src/utils/provider-env.ts` -- confirmed a separate, net-new (for `PROV-012`)
  internal env-var helper, distinct from `AuthContext.env`'s own already-certified `PROV-006`
  contract.
- `packages/ai/src/auth/resolve.ts`, `packages/ai/src/auth/types.ts` (`AuthPrompt`/`AuthEvent`/
  `AuthInteraction`/`ProviderAuthInteraction`/`OAuthAuth`/`ApiKeyAuth`/`ProviderAuth`), and
  `packages/ai/src/models.ts` (`checkAuth`/`getAuth`/`login`/`logout`) -- read in full to
  understand `PROV-013`'s own scope and confirm the owner-approved deferral boundary; not exercised
  by this slice's own code.
- `packages/ai/src/providers/openai-codex.ts` -- confirmed the model/completions API adapter
  itself (`openai-codex-responses`) is a separate, later phase; Layer 11 is auth-only.
- `packages/coding-agent/src/utils/open-browser.ts`, `packages/coding-agent/src/modes/
  interactive/interactive-mode.ts:5925` -- confirmed browser launching is a CLI-layer concern
  entirely OUTSIDE `packages/ai/src/auth/**` (`packages/ai`'s own auth module only emits the
  `auth_url` notification event); Minion does not have an equivalent CLI layer yet, so `PROV-012`'s
  own future slice does not need to implement actual browser launching either.

## Independent Node cross-checks (before implementing, not after)

`atob`'s own exact behavior was independently confirmed live against a real Node process
(`v22.15.1`), not inferred from MDN prose, for every edge case this row's own implementation
depends on:

```text
atob("eyJzdWIiOiIxMjM0NTY3ODkwIn0")         -> decodes fine (missing padding accepted)
atob("-_-_")                                -> throws "Invalid character"
atob("eyJhIjoxf")  (len%4==1)                -> throws "The string to be decoded is not
                                                 correctly encoded."
atob(base64_of('{"name":"café"}'))          -> "{\"name\":\"cafÃ©\"}" -- MOJIBAKE, codepoints
                                                 [0x63, 0x61, 0x66, 0xc3, 0xa9]
```

A candidate Python implementation (`base64.b64decode(padded, validate=True)` +
`raw.decode("latin-1")` + `json.loads`) was checked against each of these cases directly in a
Python REPL before being committed, confirming byte-for-byte identical results (including the
exact mojibake codepoints) rather than assuming Latin-1 decode would "obviously" match.

## Implementation

`minion-agent-python/src/minion_agent/auth/openai_codex.py` (new file):

- `_decode_jwt_payload`: three-segment split, standard-base64-only decode with padding leniency
  (`validate=True` rejects base64url's own `-`/`_`), Latin-1 interpretation before JSON parsing.
- `get_account_id`: namespaced claim extraction, non-empty-string guard.
- `credential_from_token`: raises on failed extraction; stores `accountId` on
  `OAuthCredential.extra`.
- `to_auth`: bearer `ModelAuth(api_key=credential.access)` projection.

`tests/auth/test_openai_codex.py` (new file, 13 tests): well-formed extraction, unpadded
base64url-shaped payload, wrong segment count, base64url-specific characters, invalid base64
length, non-JSON payload, missing claim path, non-string/empty-string account id, the exact
mojibake witness, credential projection (success and failure), and the bearer projection. All
fixtures are synthetic JWT-shaped strings built from ordinary Python dicts -- no real
account/token appears anywhere.

**Independently confirmed discriminating by revert-and-confirm**: temporarily changed the
Latin-1 decode to a UTF-8 decode (the "obviously more correct" choice a naive port might make);
the mojibake witness failed with the exact wrong (correctly-decoded, non-mojibake) codepoints
instead of the pinned mojibake ones. Restored the fix; all 13 tests passed. Separately confirmed
that removing `validate=True` from the base64 decode call did NOT change this test suite's own
outcome for the specific `-_-_` witness (Python's default lenient decode discards the invalid
characters, producing an empty payload that still fails JSON parsing by a different path) -- this
is disclosed directly in that test's own docstring rather than left as an implied claim the test
does not actually support; `validate=True` remains the semantically exact match for `atob`'s own
documented behavior regardless of whether a single black-box witness can distinguish it from the
lenient alternative for every possible input.

## Normative deltas

- `spec/auth.md`: new `## Codex account-id projection (PROV-011, Layer 11 Pass 2, adopted)`
  section with the full decode/projection contract; the prior single "Deferred Codex-specific
  behavior" section split, with PROV-012's own remaining scope kept under its own now-narrower
  deferred section. Document header and two other stray `PROV-011`/deferred cross-references
  updated to stop describing this row as not-yet-covered.
- `pi-parity-manifest.yaml`: `PROV-011`'s `disposition` changed from `deferred parity` to
  `adopted`; rule text rewritten with the full decode contract and the independently-confirmed
  edge-case behaviors; `python` field points at the new module; `rust` field left `NOT YET
  IMPLEMENTED` (this slice is Python/shared-contract only, per the standard ownership flow --
  Rust implementation follows only after this candidate is merged and reviewed).

## Fresh quality gates

- `tests/auth/test_openai_codex.py` (targeted, `--no-cov`): 13 passed, 0 failed.
- Full `pytest` suite (fresh, with coverage): 1311 passed, 19 xfailed (pre-existing, unrelated), 0
  failed.
- Coverage: 100.00% (`TOTAL` 3190 statements, 0 missed) -- `openai_codex.py` itself at 100%.
- `ruff check .`: clean.
- `mypy` (default gate, `files = ["src/minion_agent"]`): clean, 67 source files.
- `mypy` including all three permanent typing fixtures: clean, 70 source files.
- `ruff format --check .`: same pre-existing 7-file drift baseline, no new drift.
- `tests/test_layering.py`: 5/5.
- `tests/conformance/test_manifest_validation.py`: 8/8, 92/92 unique rows (row count unchanged --
  this slice modified `PROV-011`'s existing row content only, added no new row).
- Manual secret scan of changed files: clean (all JWT-shaped fixtures are synthetic).

## Next action

Push to the candidate branches (`layer-11-pass2-codex-oauth` in both repos), update coordination
issue #27's `STATUS`/`NEXT_OWNER`, and request independent Rust-owner review of this candidate per
the standard ownership flow. `NEXT_OWNER = Codex`. Do not implement Rust for this slice; do not
start PROV-012 (Slice B) implementation until this slice's own contract is reviewed, and do not
start Layer 12.
