# Layer 11 Pass 2 Slice C — independent Rust-side Python implementation re-review

## Exact target and verdict

```text
code PR #33
    dbea50d9dc35e1fddc2b7d1b1a589b35f6637928

base main
    ea3b64caca84e95245fa0d5f2a1a650452686649

normative docs master
    1e3c224ed7912d51fa28f33563622e5155947cda

prior rejected implementation candidate
    5e6b82c3009ab18859d0523745cc52e472b7e64c

prior independent review
    minion-agent-docs PR #90
    3498f010098e7ab8d16a06864259f2927f8b0406

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

The current PR head was fetched from GitHub and checked out detached. PR #33 was open, Ready for
Review, and unmerged. Issue #29 was open and named `NEXT_OWNER: Codex` and the same exact SHA.

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

Seven of the ten prior findings close. Three survive with refined executable witnesses. Because
the same finding IDs have now remained open through two independent reviews, workflow section
11.8's automatic convergence trigger applies to `L11-SC-R011`, `L11-SC-R012`, and
`L11-SC-R018`. Another unconstrained point-fix pass is not authorized before a convergence
checkpoint is agreed.

## Review order

1. pinned Pi `packages/ai/src/auth/oauth/openai-codex.ts` and the JavaScript/WHATWG primitives it
   invokes;
2. merged `spec/auth.md` and manifest rules;
3. prior findings and exact witnesses;
4. candidate remediation diff and tests;
5. Python implementation as secondary evidence.

No Rust implementation file or Layer-12 artifact was read as an implementation candidate or
modified.

## Prior-finding closure ledger

### L11-SC-R011 — STILL OPEN (`PI_PARITY_DEFECT`)

The two prior witnesses now pass: scheme-only `mailto:`/`file:` URLs reach query parsing, and
`http://[` falls through instead of raising. The repair still substitutes “`urlsplit` found any
scheme” for “WHATWG `new URL(value)` succeeded.” Those predicates are not equivalent.

Refined discriminating witness:

```text
input
    http://example.com:bad?code=x&state=s

pinned Pi
    new URL(value) throws because the port is invalid
    URL parsing is caught
    bare-query fallback sees no parameter named exactly "code"
    result = {code: absent, state: "s"}

candidate
    urlsplit succeeds and reports scheme "http"
    candidate commits to its URL branch
    result = {code: "x", state: "s"}
```

`http://%?code=x&state=s` produces the same difference through an invalid host. This proves the
problem is the proxy predicate itself, not one missing exception class.

Required convergence characterization: define the observable accepted/rejected/fallback classes
of Pi's actual WHATWG URL operation and select a mechanism that implements that boundary, rather
than continuing to patch individual `urlsplit` differences.

### L11-SC-R012 — STILL OPEN (`PI_PARITY_DEFECT`)

The signed non-decimal and Unicode-digit witnesses now pass. The hand-written grammar still does
not reproduce `Number(raw.trim())` completely.

Refined discriminating witnesses:

```text
input
    U+FEFF followed by "1"

pinned Pi / Node
    trim removes U+FEFF
    Number(...) = 1

candidate
    Python str.strip leaves U+FEFF
    result = NaN
```

and:

```text
input
    "0x" followed by 1000 hexadecimal "f" digits

pinned Pi / Node
    Number(...) = Infinity
    the caller's finite-value guard produces the specified invalid-response error

candidate
    float(int(...)) raises OverflowError before the caller's guard
```

Required convergence characterization: bind trimming and string-to-number conversion to the
ECMAScript operations as a whole, with a finite witness matrix spanning whitespace, decimal,
non-decimal, overflow, invalid syntax, and special values. Avoid another regular-expression patch
whose accepted language is only a subset approximation.

### L11-SC-R013 — CLOSED

`js_json_loads` is used at all four response parsing sites, rejects the three Python extension
constants, and coerces integer literals through the already-established IEEE-754-double mapping.
The original invalid-`NaN` response now fails during parsing rather than producing a NaN expiry.

### L11-SC-R014 — CLOSED

Array-index classification is now ASCII-only, rejects empty/noncanonical keys, bounds length
before integer conversion, and preserves Unicode-digit and oversized keys as ordinary string
properties. Both prior witnesses are permanent.

### L11-SC-R015 — CLOSED

`run_cancellable` checks the signal before scheduling the coroutine and closes the unstarted
coroutine on rejection. The new immediately-completing witness proves neither the operation body
nor its success can win when the signal is already aborted.

### L11-SC-R016 — CLOSED

The production-owned `httpx.AsyncClient` is constructed with `timeout=None`. The implicit
five-second httpx timeout no longer truncates Minion's signal-owned timeout budget.

The injected-client constructor remains an implementation/test seam whose supplied client may
carry its own policy. That does not reopen the production-owned default finding, but its contract
should remain described narrowly so callers do not mistake arbitrary injected configuration for a
guaranteed conforming production client.

### L11-SC-R017 — CLOSED

The production-owned client sets `follow_redirects=True`, and the permanent 302-to-200 test proves
actual following rather than inspecting only a constructor argument.

### L11-SC-R018 — STILL OPEN (`PI_PARITY_DEFECT`)

The status-text half closes: `HttpResponse.reason_phrase` now carries the real response reason and
the empty-body 401 witness produces `Unauthorized`.

The body-read half overcorrects. `HttpxTransport.post` catches every `httpx.HTTPError` raised by
`response.aread()` and replaces it with an empty body regardless of HTTP status. Pi applies
`.text().catch(() => "")` only in the non-2xx error branches. On every 2xx path it calls
`response.json()` without such a catch, so a body-read failure propagates from that operation; it
is not converted into an empty body and then into a JSON-parse error.

Refined discriminating witness:

```text
setup
    HTTP status/headers arrive as 200 OK
    reading the body then fails (connection reset / raising response stream)

pinned Pi
    response.json() rejects with the body-read failure
    the failure propagates through the existing call-site boundary

candidate HttpxTransport
    catches the read failure
    returns HttpResponse(status=200, body=b"", reason_phrase="OK")
    caller instead raises a fabricated empty-input JSONDecodeError
```

The candidate's new permanent test actually fixes status at 200 while asserting the incorrect
empty-body outcome, so it codifies the mismatch.

Required convergence characterization: represent body-read success/failure without losing it at
the generic transport boundary, then pin the call-site distinction:

```text
non-2xx text read failure
    empty-string fallback, then statusText/reason handling

2xx JSON body read failure
    propagate the read failure; do not replace it with a parse failure
```

This is a language-neutral response-seam requirement, not a prescription to expose httpx types.

### L11-SC-R019 — CLOSED

Issue #29 comment `5687465258` records the exact question/options and the owner's selected answer,
with `authorAssociation=OWNER`. The manifest cites that durable source and accurately scopes the
behavior-preserving `PROV-010` static type widening.

### L11-SC-R020 — CLOSED

The auth package narrative now describes the implemented Pass-2 surface and continuing exclusions.
The evidence reference is corrected to `L11-SC-R009`.

## New finding

### L11-SC-R021 — `CONTRACT_ASSURANCE_DEFECT`: parser documentation contradicts implementation

`auth/js_json.py` states that neither conversion direction is a `json.dumps`/`json.loads` call
with adjusted options and that no combination of their parameters can reproduce either algorithm.
The parser implemented immediately below is literally:

```python
json.loads(text, parse_int=float, parse_constant=_reject_js_incompatible_constant)
```

The renderer genuinely is dedicated; the parser deliberately and reasonably reuses the standard
parser with semantic hooks. The current broad sentence is false and makes the assurance narrative
internally inconsistent.

Required correction: narrow the “dedicated/no adjusted stdlib call” claim to rendering, and
describe parsing as standard JSON parsing with the two required ECMAScript-fidelity hooks. No
production behavior change is required for this finding.

## Convergence trigger and required checkpoint

```text
STATUS
    CONTRACT_CONVERGENCE

OPEN_SURFACE
    L11-SC-R011 — WHATWG URL success/failure/fallback boundary
    L11-SC-R012 — ECMAScript trim + StringToNumber boundary
    L11-SC-R018 — status-sensitive body-read failure handling
    L11-SC-R021 — narrow documentary correction

NEXT_OWNER
    Claude (challenge/characterization pass)
```

Before another implementation pass, record an agreed behavior matrix and the exact witnesses above
in a convergence checkpoint per workflow sections 11.8.4–11.8.5. The implementation pass must turn
the refined witnesses into permanent evidence and rerun the seven closed findings affected by the
same modules.

## Fresh gates

The exact candidate environment was synchronized before running gates.

```text
uv run pytest -q
    PASS
    1455 passed
    19 pre-existing xfailed
    1474 collected
    coverage 100.00% (3808 statements, 0 missed)

uv run ruff check .
    PASS

uv run mypy src/minion_agent tests/typing
    PASS (75 source files)
```

A focused three-file test run executed all affected tests successfully; its expected global
coverage failure was not treated as a gate because the repository enforces 100% across all source
files. The full suite above is the valid coverage gate.

Green gates do not override the refined Pi/Node witnesses.

## Classification

```text
PI_PARITY_DEFECT
    L11-SC-R011
    L11-SC-R012
    L11-SC-R018

CONTRACT_ASSURANCE_DEFECT
    L11-SC-R021

PI_BEHAVIOR_UNCERTAIN
    none

PARITY_NEUTRAL_HARDENING
    none

PARITY_CONSTRAINED_RISK
    none
```

## Stop condition

Do not merge PR #33. Do not implement Rust Slice C. Do not start Layer 12. Resume Python/shared
implementation only after the convergence checkpoint is independently agreed.
