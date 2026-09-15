# Layer 11 Pass 2 Slice C — independent Rust-side Python implementation review

## Verdict

```text
PROV-012 / PROV-016 Python implementation
    REJECTED

Python Layer 11 Pass 2 Slice C
    NOT CERTIFIED

Rust Layer 11 Pass 2 Slice C
    NOT STARTED

Layer 11 Pass 2 cross-language
    NOT CLOSED

Layer 12
    NOT STARTED
```

This verdict applies only to:

```text
code PR #33
    5e6b82c3009ab18859d0523745cc52e472b7e64c

base main
    ea3b64caca84e95245fa0d5f2a1a650452686649

normative docs master
    1e3c224ed7912d51fa28f33563622e5155947cda

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

The PR head was fetched from `refs/pull/33/head`, checked out independently, and confirmed
remote-reachable. PR #33 was open, Ready for Review, mergeable, and unmerged. Coordination issue
#29 was open and named `NEXT_OWNER: Codex` and the exact candidate SHA above.

## Authority and scope

The review used this order:

1. pinned Pi `packages/ai/src/auth/oauth/openai-codex.ts` and the runtime behavior of the
   JavaScript/WHATWG primitives it directly invokes;
2. merged `spec/auth.md`;
3. the candidate parity-manifest changes for `PROV-010`, `PROV-012`, and `PROV-016`;
4. the candidate tests;
5. Python source only after the contract/source audit.

The review did not inspect or modify Rust implementation code and did not begin Layer 12.

## Pi/contract audit

The candidate correctly implements substantial parts of the approved contract: fixed endpoints
and authorization parameters; callback-server status/path/state/code handling; the disclosed
notify-before-cleanup boundary; the server/manual-prompt race shape; the fixed login-method
vocabulary; device polling through `PROV-010`; the exchange-vs-refresh error-wrapping asymmetry;
the six-field `PROV-016` strict-string divergence; and most of the dedicated
`JSON.stringify` renderer, including negative zero, notation thresholds, ordinary non-ASCII,
control characters, lone surrogates, and ordinary ASCII array-index keys.

Those correct portions do not close the row because the following observable blockers remain.

## Findings

### L11-SC-R011 — `PI_PARITY_DEFECT`: manual authorization input does not implement `new URL`

**Affected code:** `auth/openai_codex_oauth.py::parse_authorization_input` (around line 298).

Pinned Pi first executes `new URL(value)` inside `try/catch`. A successful absolute WHATWG URL is
read through `searchParams`; a URL-construction failure falls through to fragment/query/bare-code
parsing. The candidate substitutes `urlsplit(value)` and accepts the URL branch only when both
`scheme` and `netloc` are non-empty. It also fails to catch `urlsplit` exceptions.

Minimal discriminating witnesses:

```text
input
    mailto:user@example.com?code=abc&state=xyz

Pi / Node
    {code: "abc", state: "xyz"}

candidate
    {code: absent, state: "xyz"}
```

The same defect reproduces with `file:///tmp?code=abc&state=xyz`. Separately:

```text
input
    http://[

Pi
    new URL throws inside its catch; parsing falls through to bare code
    {code: "http://[", state: absent}

candidate
    uncaught ValueError("Invalid IPv6 URL")
```

**Required correction:** implement the accepted absolute-URL and failed-URL-fallback behavior of
Pi's WHATWG `URL` seam, with permanent witnesses for a valid absolute URL without an authority and
for a host-parser error that must fall through rather than escape.

### L11-SC-R012 — `PI_PARITY_DEFECT`: device interval string coercion is not JavaScript `Number`

**Affected code:** `auth/openai_codex_oauth.py::_js_number_coerce` (around lines 435-460).

The contract and pinned Pi require `Number(json.interval.trim())`. The candidate's regular
expressions accept syntax JavaScript rejects and use Unicode `\d` where JavaScript numeric literal
digits are ASCII.

Minimal witnesses independently reproduced against Node 22:

```text
input       Node Number(input)    candidate
"+0x1"      NaN                   1.0
"١"         NaN                   1.0
```

The first candidate value allows a response Pi rejects; the second also demonstrates that a
host-language Unicode-digit predicate is not the ECMAScript numeric grammar.

**Required correction:** reproduce `Number(trimmed)` for this JSON-string domain rather than a
broader Python regular-expression approximation, and retain both witnesses permanently.

### L11-SC-R013 — `PI_PARITY_DEFECT`: response parsing accepts non-JSON constants

**Affected code:** all plain `json.loads` calls in `auth/openai_codex_oauth.py`, especially
`_read_token_response` around line 667.

WHATWG `Response.json()` uses JSON parsing and rejects the bare tokens `NaN`, `Infinity`, and
`-Infinity`. Python's default `json.loads` accepts those extensions. The candidate consequently
accepts this response and constructs a token whose expiry is NaN:

```json
{"access_token":"a","refresh_token":"r","expires_in":NaN}
```

Pinned `JSON.parse` rejects it with `SyntaxError`. This contradicts the normative rule that a
2xx JSON-parse failure propagates raw before field validation.

**Required correction:** use one JS-JSON-parse-equivalent response parser consistently at all
four response parsing sites (including swallowed parsing in the non-2xx device-poll error probe),
and add invalid-constant witnesses.

### L11-SC-R014 — `PI_PARITY_DEFECT`: ECMAScript array-index detection accepts Unicode digits

**Affected code:** `auth/js_json.py::_is_array_index` (around line 115).

`str.isdigit()` is broader than the ECMAScript canonical ASCII decimal array-index grammar. The
candidate treats the Arabic-Indic key `"١"` as index 1 and reorders it. Node does not.

Minimal witness, preserving insertion order shown:

```text
value
    {"١":"arabic", "2":"two", "x":0}

Pi / JSON.stringify
    {"2":"two","١":"arabic","x":0}

candidate
    {"١":"arabic","2":"two","x":0}
```

Very long digit-only keys can additionally make the candidate's `int(key)` throw even though
ECMAScript treats them as ordinary non-index keys.

**Required correction:** restrict array-index recognition to canonical ASCII decimal strings and
make out-of-range/arbitrarily long keys non-throwing; preserve the Unicode-digit witness.

### L11-SC-R015 — `PI_PARITY_DEFECT`: a pre-aborted transport signal can still start and win

**Affected code:** `auth/http_transport.py::run_cancellable` (around lines 75-83).

The candidate schedules the request and checks task completion before checking `signal.aborted`.
With a pre-aborted signal and an immediately completing operation it returns success and confirms
the request started:

```text
candidate
    result = 42
    request_started = true

Node fetch with an already-aborted AbortSignal
    AbortError
    server request count = 0
```

Pi's `fetchWithLoginCancellation` then maps that fetch failure to exactly `"Login cancelled"`.
The existing candidate test uses a never-completing coroutine and therefore does not distinguish
this completion-before-check bug.

**Required correction:** make pre-abort observable before request initiation/completion and add an
immediately-completing discriminating witness through the real transport cancellation seam.

### L11-SC-R016 — `PI_PARITY_DEFECT`: the concrete client leaks an unapproved five-second timeout

**Affected code:** `auth/http_transport.py::HttpxTransport.post` (around line 110).

The owned client is constructed as `httpx.AsyncClient()` and therefore has a five-second default
timeout. The approved contract explicitly requires timeout behavior to map through Minion's
existing signal contracts and never become an httpx-defined timeout. Pinned `fetch` has no
corresponding five-second cap.

Executable loopback witness:

```text
server responds after 5.2 seconds; signal remains active

candidate default HttpxTransport
    httpx.ReadTimeout at approximately 5 seconds

Node fetch
    HTTP 200
```

This is especially material for refresh, whose already-certified `CombinedSignal` owns a distinct
15-second timeout budget.

**Required correction:** remove the implicit concrete-client timeout and add a discriminating
transport witness proving no independent shorter client timeout truncates the signal-owned budget.

### L11-SC-R017 — `PI_PARITY_DEFECT`: the concrete client disables pinned fetch redirects

**Affected code:** `auth/http_transport.py::HttpxTransport.post` (around line 110).

Pinned Pi uses `fetch`, whose default redirect mode follows redirects. `httpx.AsyncClient()` has
`follow_redirects=False`. A scripted 302-to-200 witness produces:

```text
Node fetch
    requests /start then /final; returns 200

candidate HttpxTransport
    requests /start only; returns 302
```

That changes the provider operation from success to a non-2xx error at the same public seam.

**Required correction:** pin and implement the redirect behavior of the adopted fetch calls and
add a 302 witness through the concrete transport.

### L11-SC-R018 — `PI_PARITY_DEFECT`: the response seam cannot reproduce `statusText` fallback

**Affected code:** `auth/http_transport.py::HttpResponse` and
`auth/openai_codex_oauth.py::_read_token_response` (around lines 649-660).

For an empty/unreadable non-2xx token response, Pi formats `text || response.statusText`. The
candidate response type carries no status text and substitutes a four-entry private lookup. For a
standard empty-body 401 response:

```text
Node Response
    statusText = "Unauthorized"
    message = "OpenAI Codex token exchange failed (401): Unauthorized"

candidate
    message = "OpenAI Codex token exchange failed (401): "
```

The buffered response design also cannot represent Pi's specified body-read failure fallback:
body-read failure becomes a request-level transport exception before any `HttpResponse` exists.

**Required correction:** make the transport response seam capable of reproducing both status-text
and body-read-failure fallback semantics; add empty-body 401 and unreadable-body witnesses. Do not
grow another incomplete hand-maintained status table.

### L11-SC-R019 — `CONTRACT_ASSURANCE_DEFECT`: the lower-layer widening lacks governance provenance

**Affected artifact:** `pi-parity-manifest.yaml::PROV-010` and `PROV-012` implementation-closure
paragraphs.

The candidate says the owner approved widening the already-certified `PROV-010` signature, but it
does not cite a durable governance source for that exact decision. The only durable owner scope
record located on issue #29 is comment `5659001629`; it says that if `PROV-012` cannot be expressed
without changing `PROV-008/009/010`, work must stop and the discovered defect must go through
governance. It does not itself approve this later widening. The implementation handoff's assertion
that approval occurred is another agent's assertion and is not valid provenance under workflow
section 11.10.

This is a handoff-validation defect even if the type widening is technically sound and behavior
preserving.

**Required correction:** durably record and cite the owner's explicit decision for this exact
lower-layer delta, including scope; or revert the delta and return to the owner. Do not infer
approval from the implementation or the author's report.

### L11-SC-R020 — `CONTRACT_ASSURANCE_DEFECT`: current evidence contains stale/incorrect claims

Two narrow current-state errors remain:

1. `auth/__init__.py` still says real OAuth HTTP calls and the Codex callback/device integration are
   “not yet implemented,” contradicting the candidate it packages.
2. `PROV-012.tests` cites `L11-SB-R009` for pre-aborted browser ordering; the established finding is
   `L11-SC-R009`.

**Required correction:** update only the current package narrative and the stale finding ID.

## Contract-quality answers

```text
Does the candidate use the real production seams?
    YES, generally; the local server, provider flow, transport, poller, and renderer are real.

Does the test suite simulate core OAuth behavior in a runner?
    NO.

Can Python and Rust satisfy the current implementation evidence yet disagree observably?
    YES — URL parsing, Number coercion, JSON parsing/order, cancellation, timeout,
    redirects, and response status fallback all supply concrete disagreements.

Does an earlier certified layer require a delta?
    YES — the candidate widens PROV-010's static signal boundary; the semantic behavior appears
    unchanged, but the required governance provenance is absent.

Can Rust Slice C begin?
    NO. The Python/shared candidate must close the blockers first.
```

## Fresh gates

The exact candidate environment was recreated with `uv sync`; an initial run using a neighboring
checkout's editable virtual environment was discarded because coverage correctly attributed zero
lines to the exact worktree.

```text
uv run pytest -q
    PASS
    1434 passed + 19 pre-existing xfailed (1453 collected)
    coverage 100.00% (3788 statements, 0 missed)

uv run ruff check .
    PASS

uv run mypy src/minion_agent tests/typing
    PASS (75 source files)
```

Green gates do not override the executable parity witnesses above.

## Finding classification

```text
PI_PARITY_DEFECT
    L11-SC-R011
    L11-SC-R012
    L11-SC-R013
    L11-SC-R014
    L11-SC-R015
    L11-SC-R016
    L11-SC-R017
    L11-SC-R018

CONTRACT_ASSURANCE_DEFECT
    L11-SC-R019
    L11-SC-R020

PI_BEHAVIOR_UNCERTAIN
    none

PARITY_NEUTRAL_HARDENING
    none

PARITY_CONSTRAINED_RISK
    none
```

## Next action

Return the exact findings above to the Python/shared owner for one coherent remediation pass. The
remediation must turn each executable witness into permanent regression evidence and repair the
governance/current-artifact issues. Any changed PR head requires a fresh independent exact-SHA
review. Do not implement Rust Slice C and do not start Layer 12.
