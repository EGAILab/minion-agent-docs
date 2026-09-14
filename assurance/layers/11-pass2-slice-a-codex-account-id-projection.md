# Layer 11 Pass 2, Slice A — Codex account-id projection (`PROV-011`)

## Authority and baseline

- accepted code baseline: `main` @ `08433b0e8aa1f4502a2ebd3b6a8c553f29f6f99a`
- accepted docs baseline: `master` @ `e7f31a33f6fd10ae58bd87d12dd7a9c8de2524fe`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- coordination issue: `minion-agent#29` (clean restart after incident containment; supersedes the
  quarantined `minion-agent#27`, preserved as incident evidence only per `agent-workflow.md`
  §11.12)
- owner scope decision: `LAYER 11 PASS 2 — OWNER SCOPE DECISION` (2026-09-14), approving Slice A
  (`PROV-011`), the `PROV-013` split (new `PROV-014` row for the interaction vocabulary, deferred
  orchestration retained under `PROV-013`), Slice B (vocabulary, contract-first) before Slice C
  (`PROV-012` network integration), and `httpx` as the approved implementation-mechanics choice
  for Slice C's own HTTP transport. This is the `GOVERNANCE_SOURCE` for this slice
  (`agent-workflow.md` §11.10).

## Incident-containment note

Per `agent-workflow.md` §11.12 (quarantine semantics), NONE of the content in the quarantined
`minion-agent#27`/`minion-agent#28`/`minion-agent-docs#73` was reused as evidence for this slice.
Every Pi fact below was independently re-derived this pass, fresh, by reading pinned Pi source
directly and, for the two subtlest behaviors, cross-checking against a live Node v22 process.

## Scope

Slice A only, per the owner's own explicit scope: `decodeJwt`, `chatgpt_account_id` extraction,
`credentialsFromToken` semantics, and the OAuth access-token -> `ModelAuth` bearer/api-key
projection. No signature verification was added where Pi performs only unverified claim decoding.
Only synthetic credentials/JWT fixtures were used -- no real account, token, or secret anywhere in
the committed test suite.

Explicitly NOT in this slice (each is a separate, later Pass-2 slice or remains untouched):
`PROV-012` (Codex OAuth network integration), the `PROV-013`/`PROV-014` split itself (structural
manifest/spec work belongs to Slice B, which also implements the vocabulary), `LlmService`
extension, any new generic auth-orchestration architecture, and Layer 12.

## Independent Pi audit (fresh, this slice)

Read directly from pinned Pi, not summarized from any prior artifact:

- `packages/ai/src/auth/oauth/openai-codex.ts:103-113` (`decodeJwt`), `:396-401` (`getAccountId`),
  `:403-416` (`credentialsFromToken`), `:541-543` (`toAuth`).
- `packages/ai/src/auth/types.ts` (`OAuthCredential`'s own `accountId` field placement, confirming
  the Minion-specific `extra` mapping below is a disclosed divergence, not direct parity).

Independently confirmed against a live Node v22 process (not inferred from documentation) before
implementing:

```text
atob("eyJhIjoxfQ")           -- succeeds, missing padding tolerated
atob("-_-_")                  -- throws DOMException: Invalid character
atob("+/+/")                  -- succeeds (standard base64 alphabet, same bit patterns)
atob(base64(utf8("héllo")))   -- returns "hÃ©llo" (Latin-1 interpretation of UTF-8 bytes,
                                  NOT the original "héllo")
```

The exact synthetic JWT fixture used in both the live-Node cross-check and the committed Python
test suite: header `{"alg":"none","typ":"JWT"}`, payload `{"https://api.openai.com/auth":
{"chatgpt_account_id":"acct_synthetic_test_123"},"email":"héllo@example.com"}` (the `email`
claim's own non-ASCII character is the mojibake witness), signature segment the literal `sig`
(never verified). No real account, token, or secret.

## Implementation

`minion-agent-python/src/minion_agent/auth/openai_codex.py` (new): `decode_jwt`, `get_account_id`,
`credentials_from_token`, `to_auth`. `decode_jwt` pads the payload segment to a multiple of 4
before `base64.b64decode(..., validate=True)` (matching `atob`'s tolerance for missing padding
while still rejecting base64url's `-`/`_`), decodes the result as Latin-1 (not UTF-8) before
`json.loads`, and does not itself validate the parsed shape -- the graceful non-object tolerance
lives in `get_account_id`, exactly where Pi's own optional chaining provides it, not earlier.
`credentials_from_token` places the extracted account id under `OAuthCredential.extra["account_id"]`
(a disclosed Minion-specific mapping, not direct Pi parity -- Pi's own `OAuthCredential` carries
`accountId` as a literal top-level field) and raises `ValueError` when no usable account id can be
extracted, matching Pi's own thrown `Error`.

`tests/auth/test_openai_codex.py` (new, 17 tests): full payload round-trip; the Latin-1 mojibake
witness pinned to the exact codepoints cross-checked against Node; a revert-and-confirm witness
proving the mojibake is genuinely from the Latin-1 choice (decoding the SAME raw bytes as UTF-8
recovers the original character); missing base64 padding accepted; base64url alphabet characters
rejected; malformed token segment counts; invalid JSON; the JSON-`null`-literal/malformed-token
ambiguity faithfully reproduced; non-object decoded payload (array/string) does not raise;
missing/non-object claim namespace; non-string/empty account id; `credentials_from_token` success
and failure paths; `to_auth` bearer projection.

**Independently confirmed discriminating by revert-and-confirm (two subtlest behaviors)**:

1. Reverted the Latin-1 decode to UTF-8: the mojibake-witness test failed with the exact opposite
   symptom (`'héllo@example.com'` recovered instead of the expected mojibake), proving the test
   actually exercises the Latin-1 choice, not an unrelated property. Restored; full suite passed.
2. Reverted `base64.b64decode(padded, validate=True)` to a non-validating decode: the base64url-
   rejection test's OWN original fixture (`"-_-_"`, an all-invalid-character payload) was first
   found to be NON-discriminating -- a non-validating decoder silently strips `-`/`_`, and an
   all-`-_` payload strips down to nothing, producing an empty-JSON parse failure that ALSO returns
   `None`, masking the real defect. Replaced with a fixture deliberately constructed so a lenient
   decoder would still succeed (`"eyJh-IjoxfQ=="`, a single `-` inserted into an otherwise-valid
   standard-base64 encoding of `{"a":1}`, which strips back to the exact original valid encoding).
   Against the reverted (non-validating) code, this correctly failed with `{'a': 1}` returned
   instead of `None`. Restored the validating decode; full suite passed.

## Normative deltas

- `spec/auth.md`: the JWT-decode/account-id/bearer-projection content moved from the "Deferred
  Codex-specific behavior (`PROV-011`, `PROV-012`)" section into a new, fully-normative "Codex
  account-id projection (`PROV-011`, Pass 2 Slice A, adopted)" section, stating both `atob` quirks
  as binding cross-language rules and the Minion-specific `extra` mapping explicitly. The
  remaining deferred section is renamed "Deferred Codex network integration (`PROV-012`)" and
  keeps only the network-integration content. The `PROV-013` section is UNCHANGED in this slice
  (the split is Slice B's own deliverable, per the owner's explicit sequencing).
- `pi-parity-manifest.yaml`: `PROV-011`'s `rule`/`tests`/`python`/`disposition` updated from
  `deferred parity` to `adopted`; `rust` field states Python-only for this slice, Rust a separate
  later handoff. 92 -> 92 rows (no row added or removed; `PROV-011` already existed as a deferred
  row).

## Fresh quality gates

- `tests/auth/test_openai_codex.py` (targeted, `--no-cov`): 17 passed, 0 failed.
- Full `pytest` suite (fresh, with coverage): 1315 passed, 19 xfailed (pre-existing, unrelated), 0
  failed.
- Coverage: 100.00% (`TOTAL` 3188 statements, 0 missed).
- `ruff check .`: clean.
- `mypy` (default gate, `files = ["src/minion_agent"]`): clean, 67 source files.
- `mypy` including all typing fixtures: clean, 70 source files.
- `ruff format --check .`: same pre-existing 7-file drift baseline (179 files total now formatted,
  up from 177 -- the two new files), no new drift.
- `tests/test_layering.py`, `tests/conformance/*`: all passing, including manifest validation.
- Manual secret scan of the new/changed auth files: clean (synthetic fixtures only, no real
  account, token, or secret).

## Findings

None. No `PI_PARITY_DEFECT`, `CONTRACT_ASSURANCE_DEFECT`, or `PI_BEHAVIOR_UNCERTAIN`.

## Next action

Per the owner's own approved implementation order, Slice B (new interaction-vocabulary manifest
row, contract/spec/tests first, splitting it out of `PROV-013` as `PROV-014`) is next, followed by
Slice C (`PROV-012`, consuming Slice B's own vocabulary). This slice's own candidate is pushed for
the normal independent review cycle; do not proceed to Slice B implementation without that review
completing, per the same discipline Pass 1 and the incident-containment process both established.
