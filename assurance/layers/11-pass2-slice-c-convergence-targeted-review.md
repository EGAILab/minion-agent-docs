# Layer 11 Pass 2 Slice C — independent convergence targeted-closure review

## Exact target and verdict

```text
code PR #33
    00c693c3abaf6ab1b018e6c7da7abd8c0af20102

docs PR #92
    c35a3c702b0506cfd051c42599cbc6e504c7afba

base main
    ea3b64caca84e95245fa0d5f2a1a650452686649

base docs master
    1e3c224ed7912d51fa28f33563622e5155947cda

prior rejected implementation candidate
    dbea50d9dc35e1fddc2b7d1b1a589b35f6637928

prior independent review
    minion-agent-docs PR #91
    b7b7c7a869a1c4c94ad4c006cba50148ef517c8a

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

Both candidate SHAs were fetched from GitHub and verified as the current, remote-reachable heads
of open, Ready-for-Review, unmerged PRs. Issue #29 was open, recorded `NEXT_OWNER: Codex`, named
these exact SHAs, and cited the owner-authored `url-py` governance decision at
`https://github.com/EGAILab/minion-agent/issues/29#issuecomment-5689770460`. The cited comment's
author association is `OWNER` and its scope covers the dependency/mechanism used here.

This is the workflow section 11.8.7 targeted closure review of the agreed convergence surface,
not the final section 11.8.8 complete review.

```text
convergence implementation
    REJECTED

L11-SC-R011
    STILL OPEN

L11-SC-R012
    PROVISIONALLY CLOSED

L11-SC-R018
    STILL OPEN

L11-SC-R021
    PROVISIONALLY CLOSED

Python Layer 11 Pass 2 Slice C
    NOT CERTIFIED

Rust Layer 11 Pass 2 Slice C
    NOT STARTED

Layer 12
    NOT STARTED
```

## Review order and scope

The review used this order:

1. pinned Pi `packages/ai/src/auth/oauth/openai-codex.ts` and the ECMAScript/WHATWG operations it
   directly invokes;
2. current `spec/auth.md` and `pi-parity-manifest.yaml` rules;
3. prior rejected review and the convergence agreement;
4. current tests and candidate implementation as secondary evidence.

No Rust implementation file, Layer-12 artifact, shared semantic rule, or Python candidate file was
modified. The candidate's governance-dependent dependency addition was checked against the
durable owner decision rather than inferred from the implementation.

## Targeted closure ledger

### L11-SC-R011 — STILL OPEN (`PI_PARITY_DEFECT`)

The converged repair correctly replaces the `urlsplit` success proxy with `url-py`'s WHATWG URL
parser. The earlier malformed-port and malformed-host witnesses now match Pi. A 60-case
differential probe covering valid/non-special URLs, rejected special-scheme hosts, repeated and
blank parameters, `+`, malformed percent encodings, NUL, encoded parameter names, and fallback
query strings found no difference.

The Python binding nevertheless receives a Python Unicode string and attempts to encode it as
UTF-8 before the Rust URL parser runs. A Python string may contain an unpaired UTF-16 surrogate;
JavaScript strings may too. WHATWG URL construction converts its input to a USVString, replacing
each unpaired surrogate with `U+FFFD`. The binding instead raises `UnicodeEncodeError` before the
candidate's `_WhatwgURLError` handler can apply Pi's fallback logic.

Minimal discriminating witnesses:

```text
witness A
    input = "https://example.test/?code=<lone high surrogate>&state=s"

pinned Pi / Node
    new URL performs USVString conversion
    searchParams.get("code") = U+FFFD
    result = {code: U+FFFD, state: "s"}

candidate
    URL.parse raises UnicodeEncodeError
    parse_authorization_input propagates the exception
```

```text
witness B
    input = <lone high surrogate>

pinned Pi / Node
    new URL's USVString-converted probe is rejected as a URL
    Pi falls through using the ORIGINAL trimmed JavaScript string
    result.code is the original lone surrogate

candidate
    URL.parse raises UnicodeEncodeError
    fallback is never reached
```

The pair is discriminating: it prevents a repair from merely replacing surrogates in the public
input before all branches (which would make witness B wrong) or merely treating the binding error
as URL rejection (which would make witness A wrong). The WHATWG probe must receive the equivalent
USVString while fallback branches retain Pi's original trimmed string. Rust's native `String`
cannot represent this input, so this is a Python/Pi boundary witness, not a demand for a Rust-only
surrogate representation.

Required remediation: revise the active convergence characterization to include Web-IDL
USVString conversion at the URL-constructor boundary, implement that conversion without altering
the original fallback value, and add both permanent witnesses.

### L11-SC-R012 — PROVISIONALLY CLOSED (`PI_PARITY_DEFECT` resolved)

`js_trim` enumerates exactly the ECMA-262 `WhiteSpace` and `LineTerminator` code points, includes
`U+FEFF`, excludes checked format-character negative controls, and is used at both Pi `.trim()`
boundaries. The non-decimal conversion maps Python's `float(int(...))` overflow to positive
infinity, allowing the existing finite-value guard to reject it as Pi does. The prior BOM and huge
hex witnesses pass, and no competing host whitespace predicate remains.

### L11-SC-R018 — STILL OPEN (`PI_PARITY_DEFECT`)

The status split is now correct for an `httpx.HTTPError`: a 2xx body-read error propagates and a
non-2xx body-read error becomes an empty body. Pinned Pi's non-2xx operation is broader:
`response.text().catch(() => "")` handles any promise rejection from the body-read operation, not
only one library-specific error hierarchy. The approved transport is injectable, and HTTPX's
public `AsyncByteStream` seam does not require a custom stream to raise `httpx.HTTPError`.

Minimal discriminating witness:

```text
setup
    inject an httpx.MockTransport returning status 401
    its AsyncByteStream.__aiter__ raises RuntimeError("body boom")

pinned Pi
    response.text() rejects
    catch(() => "") supplies an empty body
    non-2xx handling continues with status/reason-phrase fallback

candidate
    HttpxTransport.post catches only httpx.HTTPError
    RuntimeError("body boom") escapes
```

The same stream under status 200 must continue to propagate. That companion preserves the
already-correct status-conditioned boundary and prevents a return to the first remediation's
uniform catch.

Required remediation: make the non-2xx body-read boundary swallow any ordinary body-read failure
representable by the Python transport seam while leaving 2xx failures uncaught, and permanently
test both status branches with an exception outside `httpx.HTTPError`.

### L11-SC-R021 — PROVISIONALLY CLOSED (`CONTRACT_ASSURANCE_DEFECT` resolved)

The module documentation now accurately distinguishes the dedicated `JSON.stringify` renderer
from the `json.loads`-based parser with `parse_constant` and `parse_int` hooks. It no longer claims
that both directions avoid the standard library.

## Contract-quality result

The shared rules remain coherent: exact WHATWG URL construction and status-conditioned body-read
handling already require the two behaviors above. The defects are in the Python realization and
its evidence, not an ambiguity that would force independent Rust implementations to guess. The
`url-py` mechanism is explicitly subordinate to pinned Pi and therefore does not redefine the
contract when its Python binding has a representational edge.

No canonical runner simulates these semantics. No certified lower layer requires reopening.
`PROV-012` remains independently implementable in Rust once the Python candidate closes the
active convergence surface.

## Gate evidence

Fresh review-side checks against the exact code SHA:

```text
ruff
    PASS

mypy
    PASS — 75 source files

focused auth tests
    126 tests reached PASS before the repository-wide 100% coverage policy correctly rejected
    a focused-only invocation; this is not reported as a standalone certification gate

full pytest
    PASS — 1463 passed, 19 xfailed

coverage
    PASS — 100.00%

schema / manifest validation
    PASS — 213 passed

differential WHATWG/query probe
    60 cases, 0 differences on ordinary Unicode-scalar inputs

new R011 surrogate probe
    4/4 candidate cases raised UnicodeEncodeError; pinned Node returned values/fallbacks

new R018 non-httpx body-read probe
    candidate raised RuntimeError for status 401; pinned Pi rule requires empty-body fallback
```

## Findings and verdict

```text
PI_PARITY_DEFECT
    L11-SC-R011 — STILL OPEN
    L11-SC-R018 — STILL OPEN

CONTRACT_ASSURANCE_DEFECT
    none active beyond the missing permanent witnesses attached to the two parity defects

PI_BEHAVIOR_UNCERTAIN
    none

PARITY_NEUTRAL_HARDENING
    none

PARITY_CONSTRAINED_RISK
    none
```

The convergence implementation at the exact reviewed SHAs is rejected. The final complete review
is not yet eligible. Return only the two refined convergence findings to the Python/shared owner;
do not start Rust Slice C or Layer 12.
