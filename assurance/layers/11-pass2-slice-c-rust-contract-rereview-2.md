# Layer 11 Pass 2 Slice C — second independent Rust contract re-review

## Exact review target

- Code PR `EGAILab/minion-agent#32`:
  `fe2a7b5416a9d1f99c2c995515004ff8f4b5aa61`
- Docs PR `EGAILab/minion-agent-docs#82`:
  `e113902c7a73a4d6830d2f2bb52510adb3ac3865`
- Code base: `bd61b4a8acf03755a336c4cef7f0aacbc2ad100f`
- Docs base: `46870f172d2e1f67b876d8da34421136a4780643`
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- First rejected review: docs PR #83 at
  `3b4f35495670349d7495c0eda92e8ab18d28ba64`
- Second rejected review: docs PR #84 at
  `a68c4b60f5bec2fd2d4c9f9c1f2b8233bd20c7dc`
- Owner governance source for `L11-SC-R005` Option A:
  `https://github.com/EGAILab/minion-agent/issues/29#issuecomment-5676459844`

Issue #29 recorded the same remote-reachable candidate pair, `STATUS = RUST_CONTRACT_REVIEW`, and
`NEXT_OWNER = Codex`. Both candidate PRs were open, Ready for Review, and unmerged. This was a
review-only pass. No candidate contract, Python, Rust, Slice-D, or Layer-12 work was changed.

## Authority and source audit

The review used pinned Pi first, followed by the parity manifest, normative spec, already-certified
auth seams, assurance/history, and the implementation handoff. Re-read directly:

- `packages/ai/src/auth/oauth/openai-codex.ts`, including login dispatch, callback server,
  browser/manual race, device flow, token exchange, and refresh;
- `packages/ai/src/auth/oauth/device-code.ts` and `pkce.ts`;
- `packages/ai/src/utils/abort.ts` and `provider-env.ts`;
- the pinned Codex OAuth tests and the current `PROV-006`, `PROV-011`, `PROV-012`, `PROV-014`,
  `PROV-015`, and `PROV-016` shared authority.

The candidate is still contract-only: no Python or Rust implementation of `PROV-012` exists and no
canonical runner claims otherwise.

## Previous-finding closure

| Finding | Independent result | Status |
|---|---|---|
| `L11-SC-R001` | `auth_url` notification remains correctly outside the browser cleanup boundary. | CLOSED |
| `L11-SC-R002` | Empty manual input, whole-flow abort while manual input remains pending, and truthy state validation remain fully specified. | CLOSED |
| `L11-SC-R003` | Pi's actual truthy-any-type baseline and ECMAScript interval coercion remain accurately characterized; the owner-approved exception is isolated in `PROV-016`. | CLOSED / SUPERSEDED FOR THE SIX NAMED FIELDS BY `PROV-016` |
| `L11-SC-R004` | Device start/poll cancellation, JSON parsing, and refresh/exchange failure distinctions remain correct. | CLOSED |
| `L11-SC-R005` | The owner explicitly selected Option A. `PROV-016` separately records the narrow intentional divergence, its rationale, exact six-field scope, Pi baseline, Rust obligation, and required future witnesses. `PROV-012` remains `deferred parity`; its disposition is not overloaded. | CLOSED |
| `L11-SC-R006` | The select prompt's missing signal, exact unknown-method error, callback-host empty/whitespace distinction, and exact device-start non-404 error format are now pinned. | CLOSED |

The governance record is valid: it is an owner-authored durable issue comment, not an assistant
recommendation or inferred approval. It authorizes only strict string validation for
`device_auth_id`, `user_code`, `authorization_code`, `code_verifier`, `access_token`, and
`refresh_token` at the provider response boundary.

## New findings

### L11-SC-R007 — `PI_PARITY_DEFECT` — empty callback `code` is incorrectly accepted

The callback-server table says `query "code" absent -> 400` and `otherwise -> 200`. That makes a
present empty value such as `/auth/callback?state=<valid>&code=` successful under the written rule.
Pinned Pi obtains the value with `URLSearchParams.get` and then tests `if (!code)`
(`openai-codex.ts`, callback handler), so both `null` (absent) and `""` (present but empty) return
400 with `"Missing authorization code."`; only a non-empty code returns 200 and settles the wait.

Minimal correction: change the callback matrix to reject both absent and empty code, preserve the
state-before-code validation order, and require a permanent implementation witness that
distinguishes an empty `code=` from a non-empty code.

### L11-SC-R008 — `CONTRACT_ASSURANCE_DEFECT` — callback HTTP response surface is incomplete

The section calls its callback rules **EXACT**, but omits two directly observable Pi behaviors:

1. every 200/400/404/500 callback response sets
   `Content-Type: text/html; charset=utf-8`;
2. an exception while parsing or handling a callback request is caught by the request handler and
   produces status 500 with the internal-error page rather than escaping or becoming a 404.

The statement that HTML body presentation is out of scope does not disposition the HTTP status or
content-type header. A Rust implementation can currently omit the header or propagate a malformed
request failure and still appear to satisfy the table, while differing from Pi.

Minimal correction: pin the common response content type and the handler's 500 containment branch.
The HTML template may remain presentation-only. Add deterministic server-boundary witnesses for
the common header and the 500 branch, or explicitly narrow the claimed observable surface through
owner-approved governance; do not call the current table exact while leaving these choices open.

### L11-SC-R009 — `CONTRACT_ASSURANCE_DEFECT` — pre-aborted browser login is unspecified

Pinned Pi has a material ordering not captured by the current race table. After starting the local
server it registers the whole-flow abort listener and immediately invokes it when
`interaction.signal.aborted` is already true. This cancels only the server wait. Pi then still emits
the `auth_url` notification, creates the separately-signalled manual prompt, and waits for that
prompt; the pre-aborted whole-flow signal does not promptly reject browser login and does not abort
the manual prompt. The current table covers an abort while both sources are pending, but does not
state the already-aborted-at-entry case or the listener/immediate-check position relative to
notification and prompt creation.

Minimal correction: specify this ordering and require a pre-aborted browser-flow witness proving
notification and manual prompting still occur, the server source is already cancelled, and only
the eventual cleanup aborts the manual prompt. This requires no lower-layer change.

## Convergence trigger and characterization

This is the third rejected complete contract review for Slice C, so §11.8's automatic
`CONTRACT_CONVERGENCE` trigger is met. The remaining surface is the local browser callback boundary:

| Witness | Pinned Pi result | Required shared result |
|---|---|---|
| valid state, missing `code` | 400, missing-code error | same |
| valid state, `code=` | 400, missing-code error | same |
| valid state, non-empty code | 200; settle with code | same |
| ordinary callback response | `text/html; charset=utf-8` | same unless separately governed |
| callback handler throws | contained 500 response | same unless separately governed |
| browser flow begins with whole-flow signal already aborted | cancel server source; still notify and create/wait for manual prompt; manual prompt is aborted only during cleanup | same |

This table is the reviewer's §11.8 characterization, not an implementation design. The shared owner
must challenge it against pinned Pi and record an agreed checkpoint before remediation.

## Contract quality and Rust feasibility

- No canonical runner simulates Slice-C production semantics; none exists yet.
- `PROV-016` is coherent and independently implementable in typed Rust.
- The rest of browser/device/token orchestration is implementable using the certified PKCE,
  device-poll, signal, credential, and interaction vocabulary.
- The three findings above let independent implementations disagree at observable HTTP and
  cancellation boundaries. Rust must not guess or copy future Python mechanics.
- No certified lower-layer semantic delta is required.
- No `PI_BEHAVIOR_UNCERTAIN` remains; pinned source resolves all three findings.

## Fresh validation

At the exact code candidate:

- `uv run pytest -q`: **1337 passed, 19 xfailed, 0 failed**, **100.00%** coverage.
- `uv run pytest tests/conformance/test_manifest_validation.py --no-cov -q`: **8 passed**.
- `uv run ruff check .`: PASS.
- `uv run mypy src/minion_agent tests/typing`: PASS (72 source files).
- Manifest: 95 rows / 95 unique IDs; `PROV-016` is a separate intentional-divergence row.

Green structural/lower-layer gates do not override the new contract defects.

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

`L11-SC-R001` through `L11-SC-R006` are closed at this exact candidate. Enter convergence for the
local callback boundary (`L11-SC-R007` through `L11-SC-R009`), remediate only after an agreed
checkpoint, and request a new exact-SHA complete review. Do not begin Slice-C implementation or
Layer 12.
