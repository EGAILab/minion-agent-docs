# Layer 11 Pass 2 Slice C — mandatory final-complete Rust contract review

## Exact review target

```text
code PR #33
    f96740c821a0226033cfadfe7a7e8e55f0b117c4

docs PR #92
    eed2538969cc562cc6a8dfbdd4206e5f82703243

code base main
    ea3b64caca84e95245fa0d5f2a1a650452686649

docs base master
    1e3c224ed7912d51fa28f33563622e5155947cda

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699

targeted convergence review
    minion-agent-docs PR #95
    de770efbb51b03331e0f118c2a998e8967c4b583
```

Both candidate heads were fetched from GitHub immediately before the verdict and matched issue
#29. Both PRs were open, Ready for Review, unmerged, and remote-reachable. Issue #29 was open with
`STATUS: RUST_CONTRACT_REVIEW`, `NEXT_OWNER: Codex`, and a request for this mandatory complete
workflow section 11.8.8 review. The candidate is not derived from a quarantined artifact.

This was review mode only. No candidate, shared semantic file, Python implementation, Rust
implementation, Layer 12 work, or prior review artifact was modified.

## Authority and independent audit

The review used the required order: pinned Pi, parity manifest, normative spec, evidence/tests,
certified lower-layer architecture, assurance/handoff, and Python implementation last.

Pinned Pi source inspected directly included:

- `packages/ai/src/auth/oauth/openai-codex.ts`, especially `readTokenResponse`,
  `startOpenAICodexDeviceAuth`, `pollOpenAICodexDeviceAuth`, browser callback handling, token
  exchange, and refresh;
- `packages/ai/src/auth/oauth/pkce.ts` and `device-code.ts`;
- the adopted Fetch/WHATWG URL/ECMAScript behavior used by those call sites.

The complete current `PROV-012` and `PROV-016` spec/manifest rules were then checked against the
candidate. The convergence-targeted result remains valid for its exact surface: R011's Web IDL
USVString conversion correctly combines an explicit adjacent high/low surrogate pair, replaces
only genuinely unpaired surrogates, and confines conversion to the URL-constructor probe; R012,
R018, and R021 also remain provisionally closed. The complete review nevertheless found three new
observable surfaces that the targeted review did not cover.

## Complete prior-finding ledger

| Finding | Complete-review result |
|---|---|
| `L11-SC-R001` | CLOSED — auth-URL notification remains before the cleanup boundary. |
| `L11-SC-R002` | CLOSED — browser/manual/server race and state-validation ordering remain coherent. |
| `L11-SC-R003` | CLOSED / SUPERSEDED FOR SIX FIELDS — Pi truthiness is characterized; `PROV-016` separately governs the approved six-field narrowing. |
| `L11-SC-R004` | CLOSED — the written request-cancellation and parse/failure distinctions are correct; R022 below is a new implementation failure to preserve those distinctions. |
| `L11-SC-R005` | CLOSED — the owner-approved field-type divergence remains narrow and traceable. |
| `L11-SC-R006` | CLOSED — exact callback/device status error shapes remain specified. |
| `L11-SC-R007` | CLOSED — callback code rejects absent and empty values in state-before-code order. |
| `L11-SC-R008` | CLOSED — callback content type and handler-wide exception containment remain explicit. |
| `L11-SC-R009` | CLOSED — a pre-aborted browser flow cancels the server source without skipping notify/manual prompt. |
| `L11-SC-R010` | CLOSED FOR PREVIOUS WITNESSES — exact templates and ECMAScript `JSON.stringify` authority remain specified; R024 is a newly reached numeric case. |
| `L11-SC-R011` | PROVISIONALLY CLOSED — full scalar-value-string conversion passes the targeted witness and controls. |
| `L11-SC-R012` | PROVISIONALLY CLOSED — ECMA trim and number coercion remain correct for the prior matrix. |
| `L11-SC-R013` | CLOSED — invalid JSON constants remain rejected. |
| `L11-SC-R014` | CLOSED — array-index recognition is ASCII-only and bounded. |
| `L11-SC-R015` | CLOSED — pre-aborted request signals are checked before scheduling. |
| `L11-SC-R016` | CLOSED — owned HTTP client disables its independent timeout. |
| `L11-SC-R017` | CLOSED — owned HTTP client follows redirects. |
| `L11-SC-R018` | PROVISIONALLY CLOSED FOR ITS TARGETED WITNESS — ordinary non-2xx body-read failures are swallowed and 2xx failures propagate at the transport boundary; R022 shows the eager boundary still changes caller-visible ordering/classification. |
| `L11-SC-R019` | CLOSED — governance provenance is durable and scoped. |
| `L11-SC-R020` | CLOSED — live documentation references remain current. |
| `L11-SC-R021` | PROVISIONALLY CLOSED — the JSON module no longer overclaims its parser implementation. |

## New findings

### L11-SC-R022 — `PI_PARITY_DEFECT` — eager body buffering collapses Pi's response/body phases

Pinned Pi's Fetch promise resolves when status/headers are available. Each caller then decides
whether and when to consume the body:

```text
device start, 404
    fixed not-enabled error immediately; body is never read

device poll, 403 or 404
    PENDING immediately; body is never read

refresh, 2xx body-read rejection
    fetch already succeeded; readTokenResponse's response.json rejection propagates raw
```

The candidate's `HttpxTransport.post` instead awaits `response.aread()` before it returns any
`HttpResponse`. This is observably different, not merely a transport-mechanics choice.

Minimal executable witness A:

```text
setup
    httpx MockTransport returns status 404 and an AsyncByteStream whose body never completes
    call _start_device_auth through the real HttpxTransport

Pi expected
    DeviceCodeNotEnabledError is produced immediately
    body consumption is not started

candidate observed
    body consumption starts and the call times out
    observed trace: "timed out True"
```

Minimal executable witness B:

```text
setup
    httpx MockTransport returns status 200 and a body stream raising RuntimeError("body boom")
    call _refresh_access_token through the real HttpxTransport

Pi expected
    raw body-read error propagates from readTokenResponse

candidate observed
    OAuthRefreshTransportError("OpenAI Codex token refresh error: body boom")
```

The second result occurs because the eager read happens inside `refresh_fetch`'s request-level
try/catch instead of later in `_read_token_response`. The same architectural collapse can also
misclassify exchange/device body failures through the login-cancellation wrapper.

Required remediation is semantic, not a special-case status table in the transport: preserve a
two-phase response seam (or an observationally equivalent design) so callers can inspect status
before optional body consumption and body-read rejection occurs at Pi's caller-equivalent point.
Permanent witnesses must at least cover device-start 404 and device-poll 403/404 with a
never-completing/failing body, plus refresh 2xx body-read failure remaining raw. Existing R018
success/non-success failure witnesses must remain green. No certified lower layer needs reopening.

### L11-SC-R023 — `PI_PARITY_DEFECT` — Fetch's leading UTF-8 BOM removal is missing

WHATWG Fetch's body text decoding removes one leading UTF-8 BOM before `Response.text()` or
`Response.json()` exposes the text. Pinned Pi uses those APIs. The candidate's `HttpResponse.text`
uses `body.decode("utf-8", errors="replace")`, which retains `U+FEFF`.

Minimal executable witness:

```text
input bytes
    EF BB BF + {"access_token":"a","refresh_token":"r","expires_in":1}

Node/Fetch expected
    Response.text() == '{"access_token":"a","refresh_token":"r","expires_in":1}'
    Response.json() succeeds

candidate observed
    HttpResponse.text() begins with U+FEFF
    _read_token_response raises JSONDecodeError:
      "Unexpected UTF-8 BOM (decode using utf-8-sig)"
```

This is a known Pi mismatch and the current language-neutral text does not explicitly pin Fetch's
UTF-8 BOM-removal detail, so remediation must synchronize spec/manifest evidence as well as the
implementation. A permanent witness must cover a BOM-prefixed successful JSON response and a
non-2xx text response; only an initial BOM is removed, while an interior U+FEFF remains data.

### L11-SC-R024 — `PI_PARITY_DEFECT` — valid overflowing JSON numbers crash the JSON.stringify renderer

JSON number syntax permits an exponent such as `1e400`. ECMAScript `JSON.parse` produces
`Infinity`; this is distinct from the invalid bare token `Infinity`, which R013 correctly rejects.
ECMAScript `JSON.stringify` then renders non-finite numbers inside arrays/objects as `null`.

Minimal executable witness:

```text
input
    {"x":1e400,"y":-1e400}

Pi/Node expected
    parsed values: Infinity, -Infinity
    JSON.stringify result: {"x":null,"y":null}

candidate observed
    js_json_loads produces {'x': inf, 'y': -inf}
    js_json_stringify raises AssertionError
```

The failure reaches a real public path. A device-start response
`{"device_auth_id":"d","user_code":"u","interval":1e400}` is correctly rejected by the interval
finiteness rule, but construction of the required exact invalid-response message crashes with the
same `AssertionError` instead of rendering `interval` as `null`.

Remediation must implement the complete applicable `JSON.stringify` non-finite behavior and add
permanent direct-renderer plus real-call-site witnesses. It must also characterize top-level
non-finite input: raw `JSON.stringify(Infinity)` returns JavaScript `undefined`, and Pi's template
interpolation therefore contributes the text `undefined`. The current spec correctly names
ECMAScript `JSON.stringify` as complete authority, but its discriminating constraints/evidence
should be extended for this newly reached case so Rust does not repeat the defect.

## Whole-surface and contract-quality result

- Browser flow ordering, callback routing, PKCE, manual/server race precedence, cancellation
  mapping, device poll outcomes, field-type divergence, URL parsing/USVString conversion, and the
  previously reviewed finite JSON-number/string/property cases remain coherent.
- No canonical runner is simulating Slice-C production behavior. Slice C relies on explicit
  language tests where the network/listener cases are not suitable canonical fixtures.
- The existing lower-layer PKCE, device poll, signal, credential, and interaction contracts need
  no semantic reopen.
- R022 shows that the Python transport abstraction currently changes production ordering and error
  classification despite correct-looking caller code.
- R023 would allow independent Rust and Python implementations to choose different decoding
  behavior unless the Fetch rule is made explicit.
- R024 violates the already-normative `JSON.stringify` authority and lacks the exact witness that
  would have detected it.
- Rust cannot begin from a candidate with these active known Pi mismatches.

This final review has discovered new blockers after the prior convergence findings were
provisionally closed. Under workflow section 11.8.8, classify them normally and apply the trigger
again to the new/open surface. R022 and R023 are coupled at the HTTP response/body boundary; R024
is a separate renderer surface. A changed candidate requires another complete final review after
the new findings receive their appropriate characterization/remediation and targeted evidence.

## Fresh gates at the rejected exact candidate

Green gates do not override the semantic findings:

```text
uv run pytest -q
    PASS; 100.00% coverage; 3845 statements / 0 missed

uv run pytest -o addopts='' -q
    1472 passed, 19 xfailed, 0 failed

uv run ruff check .
    PASS

uv run mypy src/minion_agent tests/typing
    PASS; 75 source files

uv run pytest tests/conformance/test_schema_validation.py \
              tests/conformance/test_manifest_validation.py -o addopts='' -q
    213 passed

focused Slice-C auth/JSON tests
    114 passed
```

## Verdict

```text
Layer 11 Pass 2 Slice C shared contract/candidate
    REJECTED

Python Slice C
    REOPENED

Rust Slice C
    NOT_IMPLEMENTED / BLOCKED

Layer 11 Pass 2
    NOT CLOSED

Layer 12
    NOT STARTED

active PI_PARITY_DEFECT
    L11-SC-R022
    L11-SC-R023
    L11-SC-R024

PI_BEHAVIOR_UNCERTAIN
    none
```

Narrow next action: return the exact witnesses above to the shared/Python owner. Do not implement
Rust Slice C and do not start Layer 12.
