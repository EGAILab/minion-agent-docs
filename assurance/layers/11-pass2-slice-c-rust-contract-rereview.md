# Layer 11 Pass 2 Slice C — independent Rust contract re-review

## Exact review target

- Code PR `EGAILab/minion-agent#32`: `0585e84857979b7e2120bc9ed7aa2bff599523da`
- Docs PR `EGAILab/minion-agent-docs#82`: `5b86da23d4537cd155ee70cf038a9233ad99a8f6`
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- First rejected review: docs PR #83 at
  `3b4f35495670349d7495c0eda92e8ab18d28ba64`
- Coordination issue #29 recorded the same remote-reachable candidates and
  `NEXT_OWNER = Codex`.

Both candidate PRs were open, Ready for Review, unmerged, and remote-reachable. This is a complete
contract re-review, not implementation. No candidate/shared/Python/Rust file was changed.

## Pi audit and previous-finding closure

Re-read the relevant pinned source directly: all of
`packages/ai/src/auth/oauth/openai-codex.ts`, plus `oauth/device-code.ts`, `oauth/pkce.ts`,
`utils/abort.ts`, `utils/provider-env.ts`, and `test/openai-codex-oauth.test.ts`.

| Finding | Independent result | Status |
|---|---|---|
| L11-SC-R001 | Spec now accurately puts `auth_url` notification before the cleanup boundary and preserves Pi's cleanup bypass on a synchronous notification failure. | CLOSED |
| L11-SC-R002 | The race table now covers empty manual input, flow abort while manual input remains pending, and truthy-only manual state validation. | CLOSED |
| L11-SC-R003 | The response-validation prose now accurately states Pi's erased-type truthiness checks and ECMAScript `Number(trimmed)` interval coercion. | CLOSED, but exposes R005 below |
| L11-SC-R004 | Device start/poll cancellation translation, success/error JSON parsing, and caller+timeout `CombinedSignal` behavior are now accurate. | CLOSED |

## New findings

### L11-SC-R005 — `CONTRACT_ASSURANCE_DEFECT` — PROV-012 contradicts certified typed surfaces

The corrected contract now requires arbitrary JavaScript-truthy JSON values to pass through fields
that existing certified contracts make strings:

- PROV-012 requires `user_code` of any truthy JSON type, then requires emitting that unchanged in
  PROV-014 `AuthEventDeviceCode.user_code`, whose certified Python/shared shape is `str`.
- PROV-012 permits a truthy non-string `refresh_token` to reach PROV-011
  `credentials_from_token`/PROV-006 `OAuthCredential.refresh`, whose certified shape is `str`.
- Truthy non-string `authorization_code`/`code_verifier` are passed to Pi's `URLSearchParams`, which
  applies JavaScript string coercion. The current contract says to accept them but does not define
  their provider-request encoding for a typed Rust implementation.

Python can violate annotations dynamically, but Rust cannot simultaneously expose the certified
typed fields and forward an arbitrary JSON value unchanged. The suggestion to use `JsonValue` at
the response check does not resolve the downstream public-type contradiction. Two implementations
could therefore both follow different parts of the written contract and disagree observably.

Required action: perform the explicit cross-layer delta/governance decision before implementation.
Either (a) approve and separately disposition stricter network-boundary validation that preserves
the certified typed surfaces, or (b) formally reopen/widen every affected shared public type and
specify JavaScript coercion at each downstream boundary. Do not solve this with Python `Any`, Rust
runner-only dynamic values, or an undocumented local cast.

### L11-SC-R006 — `CONTRACT_ASSURANCE_DEFECT` — remaining exact input/error shapes are ambiguous

The rest of the source audit found several public distinctions still omitted:

1. Pi's login-method select prompt omits its optional per-prompt `signal` member. The contract
   specifies its message/options but not this missing-field observation. An implementation may
   attach the whole-flow signal and still appear conforming.
2. Unknown selection raises exactly `Unknown OpenAI Codex login method: ${method}`
   (`openai-codex.ts:532-533`); the contract says only “raise/reject”.
3. `getCallbackHost()` uses JavaScript truthiness through `getProviderEnvValue(...) || default`.
   Exactly `""` defaults, but whitespace-only environment content is truthy and is used as the bind
   host. “Absent or blank” can reasonably cause a Python implementation to strip whitespace.
4. Device-start's non-404 error has an exact observable format and omits the colon entirely when
   body reading yields empty: `OpenAI Codex device code request failed with status ${status}` plus
   optional `: ${body}`. “Generic status+body message” does not pin this.

Required action: state these exact missing/value/error distinctions and assign discriminating fake
interaction/transport witnesses. This is documentary/canonical completion; no lower-layer change is
needed.

## Contract quality and Rust feasibility

- No runner currently simulates Slice-C production semantics; implementation has not begun.
- The corrected concurrency and failure rules are otherwise implementable through the existing
  PKCE, device-poll, abort, and auth vocabulary seams.
- R005 is a real cross-layer semantic conflict, not an implementation preference. It must be
  resolved before Python or Rust chooses a representation.
- R006 admits observably different implementations under the current prose.
- No `PI_BEHAVIOR_UNCERTAIN` remains; direct source resolves every item above.

## Fresh gates

At the exact code candidate:

- `uv run pytest -q`: **1337 passed, 19 xfailed, 0 failed**, **100.00%** coverage.
- `uv run pytest tests/conformance/test_manifest_validation.py --no-cov -q`: **8 passed**.
- `uv run ruff check .`: PASS.
- `uv run mypy src/minion_agent tests/typing`: PASS (72 source files).
- Manifest remains 94 rows / 94 unique IDs.

## Verdict

```text
Layer 11 Pass 2 Slice C shared contract
    REJECTED

Python Slice C
    NOT_IMPLEMENTED / BLOCKED

Rust Slice C
    NOT_IMPLEMENTED / BLOCKED

Layer 11 Pass 2
    NOT CLOSED

Layer 12
    NOT STARTED
```

L11-SC-R001 through R004 are closed at this exact candidate. Remediate only R005/R006, perform the
required governance step for R005, and request another exact-SHA review. Do not begin Slice-C
implementation or Layer 12.
