# Layer 11 Pass 2 Slice C — second mandatory final-complete Rust review

## Exact review target

```text
code PR #33
    f225596f8fba1debac4a116f5d73203bbd503097

docs PR #92
    f55dd808593415bc0d94487bf3f28ea21745202c

code base main
    ea3b64caca84e95245fa0d5f2a1a650452686649

docs base master
    1e3c224ed7912d51fa28f33563622e5155947cda

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699

latest targeted review
    minion-agent-docs PR #100
    bdfcf4ada0a92e6c6ed5097bc9627fc2f01a5a14
```

Immediately before review, both candidate PRs were fetched from GitHub and their actual remote
heads matched issue #29 exactly. Both PRs were open, Ready for Review, unmerged, and
remote-reachable. Issue #29 was open with `STATUS: RUST_CONTRACT_REVIEW`, `NEXT_OWNER: Codex`, and
the request for this complete workflow section 11.8.8 review. The candidate is based on the
accepted defaults, not on a quarantined artifact.

This was review mode only. No candidate code, shared semantic file, Python implementation, Rust
implementation, Layer 12 work, or previous review evidence was modified.

## Authority and audit order

The review used the required independent order:

1. pinned Pi;
2. current parity manifest;
3. current normative auth spec;
4. explicit tests/evidence;
5. certified lower-layer architecture;
6. assurance/handoff;
7. Python implementation only as secondary evidence.

Pinned Pi source inspected directly included:

- `packages/ai/src/auth/oauth/openai-codex.ts`, including `parseAuthorizationInput`,
  `fetchWithLoginCancellation`, browser callback/race handling, device start/poll, token exchange,
  `readTokenResponse`, and refresh;
- `packages/ai/src/auth/oauth/device-code.ts`, `pkce.ts`, and auth types;
- the directly invoked WHATWG `URLSearchParams`, Fetch response, and ECMAScript JSON behavior.

The complete current `PROV-012` and `PROV-016` rules were audited, not merely the latest cleanup
patch. The latest targeted result is sound for its exact witness: R022's response-close
`CancelledError` propagates while the owned-client close is still attempted from `finally`.
R023 and R024 also remain closed. The complete review nevertheless found four new blockers on
surfaces not covered by that narrow review.

## Previous-finding ledger

| Finding | Complete-review result |
|---|---|
| `L11-SC-R001` | CLOSED — auth-URL notification remains outside the cleanup boundary as Pi places it. |
| `L11-SC-R002` | CLOSED — browser/manual/server race precedence and state validation remain coherent. |
| `L11-SC-R003` | CLOSED / SUPERSEDED FOR SIX FIELDS — Pi truthiness is characterized and `PROV-016` separately governs the approved narrowing. |
| `L11-SC-R004` | CLOSED — request cancellation and parse/failure distinctions remain specified. |
| `L11-SC-R005` | CLOSED — the owner-approved six-field divergence remains narrow and traceable. |
| `L11-SC-R006` | CLOSED — exact callback/device error shapes remain specified. |
| `L11-SC-R007` | CLOSED — callback code rejects absent and empty values in the required order. |
| `L11-SC-R008` | CLOSED — callback response headers and handler-wide containment remain explicit. |
| `L11-SC-R009` | CLOSED — pre-abort affects the server wait without skipping notify/manual prompt. |
| `L11-SC-R010` | CLOSED — exact error templates defer completely to ECMAScript `JSON.stringify`. |
| `L11-SC-R011` | CLOSED — WHATWG URL parsing and full Web IDL USVString conversion pass the complete prior witness set. |
| `L11-SC-R012` | CLOSED — ECMA trim and numeric coercion remain correct for the prior matrix. |
| `L11-SC-R013` | CLOSED — invalid bare JSON constants remain rejected. |
| `L11-SC-R014` | CLOSED — array-index recognition is ASCII-only and bounded. |
| `L11-SC-R015` | CLOSED — pre-aborted request signals are checked before scheduling. |
| `L11-SC-R016` | CLOSED — an owned HTTP client has no independent timeout. |
| `L11-SC-R017` | CLOSED — an owned HTTP client follows redirects. |
| `L11-SC-R018` | CLOSED — 2xx/non-2xx body-read behavior remains status-sensitive and Pi-compatible. |
| `L11-SC-R019` | CLOSED — governance provenance is durable and scoped. |
| `L11-SC-R020` | CLOSED — live documentation references remain current. |
| `L11-SC-R021` | CLOSED — the JSON module no longer overclaims parser behavior. |
| `L11-SC-R022` | PROVISIONALLY CLOSED — lazy status/body separation, discard cleanup, ordinary cleanup failure containment, and cancellation-safe owned-client cleanup all pass their discriminating witnesses. |
| `L11-SC-R023` | PROVISIONALLY CLOSED — Fetch-compatible leading BOM handling remains implemented. |
| `L11-SC-R024` | PROVISIONALLY CLOSED — non-finite JSON values render as ECMAScript `null`. |

## New findings

### L11-SC-R025 — `PI_PARITY_DEFECT` — owned-client cleanup can replace the real request failure

Pinned Pi's `fetchWithLoginCancellation` rethrows the original request rejection whenever the
signal did not abort. Refresh then derives its public error from that original rejection. Pi has
no observable client-close operation whose failure can replace the request result.

The candidate's `HttpxTransport.post` performs owned-client cleanup in the pre-response failure
handler without containing an ordinary cleanup failure:

```python
except BaseException:
    if owns_client:
        await client.aclose()
    raise
```

Minimal executable witness:

```text
setup
    force the internally-created client's send() to raise ConnectionError("send boom")
    force the same client's aclose() to raise RuntimeError("close boom")
    call HttpxTransport.post through the real candidate seam

Pi expected
    the request failure remains the observable failure
    refresh would wrap/describe "send boom"

candidate observed
    RuntimeError("close boom")
    __cause__ == ConnectionError("send boom")
```

This is discriminating: a cleanup implementation that merely attempts the close but lets its own
ordinary error escape passes every existing success/body-discard test while changing the public
failure. It is also inconsistent with the candidate's correctly established R022 rule that an
unobservable cleanup failure must not replace the Pi-visible outcome.

Required remediation: always attempt owned-client cleanup after a pre-response failure, but do not
allow an ordinary cleanup error to replace the original request/cancellation result. Keep
cancellation behavior explicit rather than accidentally swallowing it. Add permanent real-seam
witnesses for an ordinary request failure plus a raising owned-client close and for the applicable
refresh/login cancellation boundary. No certified lower layer needs reopening.

### L11-SC-R026 — `CONTRACT_ASSURANCE_DEFECT` — current normative prose still says implementation does not exist

The current normative `spec/auth.md` contradicts the current adopted manifest and implementation:

```text
line 746
    Python implementation, tests, and gates ... are a separate, following pass;
    this section ... is not ... a claim that Python ... code ... exists.

line 1697
    implementation pass ... not yet performed -- no Python code for this row exists yet
```

Those sentences are current contract prose, not a clearly labeled historical assurance snapshot.
The manifest now marks `PROV-012` adopted and the candidate contains the implementation and tests.
An independent Rust implementer cannot determine the current release state from mutually
contradictory normative artifacts.

Required remediation: update the current normative section to the implemented candidate state and
remove or clearly historical-scope every related current-state assertion. Preserve historical
assurance/remediation records; no implementation change is required for this finding.

### L11-SC-R027 — `PI_PARITY_DEFECT` — bare query strings with a leading `?` lose `code`

Pinned Pi's bare-query fallback constructs `new URLSearchParams(value)`. That constructor accepts
an optional leading `?` and excludes it from the first key. The spec's current "no leading `?`
required" wording likewise permits the leading form. Python's `urllib.parse.parse_qs(value)` does
not strip it, so the candidate parses the first key as `?code`.

Minimal executable witness:

```text
input
    ?code=abc&state=xyz

pinned Node/Pi primitive
    Object.fromEntries(new URLSearchParams(input))
    -> {"code":"abc","state":"xyz"}

candidate
    parse_authorization_input(input)
    -> ParsedAuthorizationInput(code=None, state="xyz")
```

The witness distinguishes the real Pi fallback from the currently tested no-prefix input
`code=abc&state=xyz`. Required remediation: reproduce the optional-leading-`?` behavior and add
permanent positive and empty-value controls (for example `?code=`). Make the spec wording explicit
rather than relying on "not required" to imply optionality.

### L11-SC-R028 — `CONTRACT_ASSURANCE_DEFECT` — outbound OAuth requests have no discriminating evidence

The contract normatively specifies endpoint, content type, and request fields for device start,
device poll, authorization-code exchange, and refresh. The Python test double records only the URL:

```python
async def post(self, url, *, headers, body, signal):
    self.calls.append(url)
    ...
```

`headers`, `body`, and `signal` are discarded. Existing tests therefore remain green if production
sends the right endpoint with an empty/wrong payload or wrong content type.

Minimal mutation witness:

```text
mutation
    keep each endpoint URL unchanged
    replace its request headers/body with empty or wrong values

existing observation
    transport.calls == [EXPECTED_URL]

result
    still passes because the only recorded field is URL
```

This evidence is not discriminating for the normative wire-input rule. Required remediation:
record the complete request observation at the fake transport boundary and add permanent tests for
all four operations, asserting endpoint, content type, and semantically decoded JSON/form fields.
Raw percent-encoding spelling need only be pinned if the normative contract makes it observable;
do not overclaim byte equality where field equivalence is the stated rule.

## Whole-surface and contract-quality result

- Browser flow ordering, callback routing, PKCE, manual/server precedence, status/body separation,
  device polling, approved field narrowing, WHATWG URL construction, USVString conversion, JSON
  parse/stringify behavior, and the R022 cleanup path remain coherent for their existing evidence.
- R025 is a newly reached pre-response cleanup branch adjacent to, but not covered by, R022's
  post-response discard witnesses.
- R027 is a concrete pinned-Pi mismatch at a public parser boundary.
- R026 makes the normative current-state narrative self-contradictory.
- R028 means Python can pass all current tests while violating request-construction rules Rust is
  expected to implement independently.
- No canonical runner simulates Slice-C behavior. Explicit language tests are appropriate for
  these injected transport/listener cases, but those tests must observe the full claimed seam.
- No certified lower-layer semantic delta is required. `PROV-009`, `PROV-010`, Layer 09 signals,
  interaction vocabulary, and credentials remain reusable unchanged.
- Rust cannot begin from a candidate with two known Pi mismatches and incomplete/contradictory
  contract evidence.

Each finding is new in this complete review. None has yet survived a remediation/re-review cycle,
and the new surface is sufficiently characterized by the witnesses above; a new convergence
checkpoint is not required by section 11.8. Re-enter ordinary Python remediation, then perform a
new complete section 11.8.8 review of the changed exact candidate.

## Fresh gates at the rejected exact candidate

Green gates do not override the findings:

```text
uv run pytest -q
    PASS
    1496 passed, 19 xfailed, 0 failed
    100.00% coverage; 3878 statements / 0 missed

uv run pytest --collect-only -q --no-cov
    1515 tests collected

uv run ruff check .
    PASS

uv run ruff format --check .
    known pre-existing baseline only: 7 files would be reformatted

uv run mypy src/minion_agent tests/typing
    PASS; 75 source files

schema / manifest / layering suites
    PASS; 218 tests

manifest inventory
    95 rows / 95 unique IDs
```

## Verdict

```text
Layer 11 Pass 2 Slice C shared contract/candidate
    REJECTED

Python Slice C
    REOPENED / NOT CERTIFIED

Rust Slice C
    NOT_IMPLEMENTED / BLOCKED

Layer 11 Pass 2
    NOT CLOSED

Layer 12
    NOT STARTED

active PI_PARITY_DEFECT
    L11-SC-R025
    L11-SC-R027

active CONTRACT_ASSURANCE_DEFECT
    L11-SC-R026
    L11-SC-R028

PI_BEHAVIOR_UNCERTAIN
    none
```

Narrow next action: return L11-SC-R025 through L11-SC-R028 to the shared/Python owner as one
coherent remediation pass. Any candidate SHA change requires another complete section 11.8.8
review. Do not implement Rust Slice C and do not start Layer 12.
