# Layer 11 Pass 2 Slice C — L11-SC-R011/R012/R018 convergence agreement

## Decision

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION
```

Exact checkpoint reviewed:

- code PR `EGAILab/minion-agent#33` at `dbea50d9dc35e1fddc2b7d1b1a589b35f6637928`;
- docs PR `EGAILab/minion-agent-docs#91` at `b7b7c7a869a1c4c94ad4c006cba50148ef517c8a`, whose own
  embedded characterization (per finding, inline in the review body) is the §11.8.3 artifact
  this document challenges and agrees;
- pinned Pi at `b7bb00b936dbe21b8e160b3e89efdec361846699`;
- base `main` at `ea3b64caca84e95245fa0d5f2a1a650452686649`;
- normative docs master at `1e3c224ed7912d51fa28f33563622e5155947cda`.

Coordination issue #29 recorded `NEXT_OWNER: Claude (challenge/characterization pass)` after the
second independent review (`minion-agent-docs#91`) rejected candidate `dbea50d` with three
findings that survived two independent reviews each (`L11-SC-R011`, `L11-SC-R012`, `L11-SC-R018`)
plus one new documentary finding (`L11-SC-R021`). This is convergence-challenge/agreement
evidence only; no candidate, shared semantic file, or Rust production was changed by writing this
document — the implementation itself is recorded separately, in the same remediation pass this
checkpoint authorizes.

## Trigger check (agent-workflow.md §11.8, mandatory)

- `L11-SC-R011`: raised by the first Python-implementation review (`minion-agent-docs#90`),
  remediated once (a `urlsplit`-scheme-truthy check with a `try`/`except ValueError` fallback),
  found STILL OPEN by the second review (`#91`) for a refined reason — the two original witnesses
  now pass, but a new witness (an invalid, non-numeric port) shows the underlying predicate itself
  is still not equivalent to WHATWG `new URL(value)` construction. **Same material finding
  survives two independent reviews** — the first §11.8 trigger condition is met.
- `L11-SC-R012`: raised by `#90`, remediated once (unsigned-only non-decimal regexes, ASCII-only
  digit matching), found STILL OPEN by `#91` for two refined reasons — a byte-order-mark trimming
  gap and an overflow-to-`OverflowError` crash, neither exercised by the first round's own
  witnesses. **Same material finding survives two independent reviews.**
- `L11-SC-R018`: raised by `#90`, remediated once (a two-phase `stream=True` send separating
  status/headers from body-read), found STILL OPEN by `#91` because the fix over-corrected —
  catching a body-read failure regardless of status, where pinned Pi only swallows it on the
  non-2xx path. **Same material finding survives two independent reviews.**

All three independently meet the first trigger condition on their own. `L11-SC-R021` is a new,
single-review documentary finding (`CONTRACT_ASSURANCE_DEFECT`) bundled into the same remediation
pass because it shares the same module and does not require its own convergence cycle.

## Challenge pass (§11.8.4)

Independently re-verified, this pass, directly against pinned Pi source and live Node (not merely
trusted from the review's own embedded characterization):

### L11-SC-R011

- `packages/ai/src/auth/oauth/openai-codex.ts:73-101` (`parseAuthorizationInput`, full re-read):
  confirmed the exact structure — `trim()`, then `try { new URL(value); ... } catch { /* not a
  URL */ }`, then the `"#"`-split strategy, then the bare-query-string strategy, then the bare-code
  fallback. `new URL(value)` is the WHATWG URL Standard constructor, not a Node-specific extension.
- Live Node confirmed the review's own refined witness end-to-end (not merely that `new URL`
  throws): running Pi's exact algorithm against `"http://example.com:bad?code=x&state=s"` produces
  `{code: undefined, state: "s"}` — `new URL` throws on the invalid port, falling through to the
  bare-query-string strategy, which parses the WHOLE original string as one `URLSearchParams`
  input, producing a single non-matching key (`"http://example.com:bad?code"`) and a genuine
  `state` pair. `urlsplit("http://example.com:bad?...").scheme` is confirmed still `"http"` (a
  truthy value my prior fix's own `if parsed_url is not None and parsed_url.scheme:` predicate
  could not distinguish from a valid URL).
- A broader battery (14 cases: valid ordinary URL, no-authority schemes, invalid port, invalid
  host character, empty host, host containing a space, an invalid scheme character, a schemeless
  string, userinfo+port) was run against BOTH live Node `new URL()` and `url-py`'s own
  `URL.parse` — every rejection and every acceptance matched exactly, including cases beyond the
  reviewer's own two witnesses (e.g. `"http://"` — empty host for a special scheme — throws in
  both Node and `url-py`, but `urlsplit` alone does not raise for it at all).

**Answering the §11.8.4 checklist:**

- *Is the Pi source mapping correct?* Yes, confirmed above via direct source re-read and running
  Pi's exact algorithm live in Node against the refined witness.
- *Is the behavior matrix complete enough to distinguish realistic wrong implementations?* Yes —
  the broader battery above specifically includes the class of bug a property-level `urlsplit`
  patch cannot fix (port/host validation), not only the two originally-reported cases.
- *Are any cases implementation mechanics rather than observable semantics?* No — WHATWG URL
  construction success/failure is itself the observable Pi behavior; which Python library
  reproduces it is the implementation mechanic, already disclosed as such in the owner's own
  governance decision below.
- *Does any proposed fix silently reopen a lower certified layer?* No — `parse_authorization_input`
  has no certified-layer dependency; this change is local to `openai_codex_oauth.py`.
- *Can both Python and Rust implement the rule idiomatically?* Yes, and unusually well: Rust's own
  natural choice for WHATWG URL parsing is the `url` crate (servo), the SAME crate `url-py` binds
  — both languages can literally share the identical parsing engine, eliminating cross-language
  drift risk entirely for this specific rule, not merely reducing it.
- *Does the defect's own root cause depend on an extensibility point one language's own certified
  lower layers exposes and the other does not?* No — this is a pure string/URL-parsing-fidelity
  question with no cross-layer extensibility point involved.
- *Are all previous review findings represented by an executable or documentary acceptance
  criterion?* Yes — see the agreed witness list below, which supersedes the original two-witness
  list with the full battery.

**Refinement over the proposed characterization:** the review's own text names the invalid-port
case as the "minimal discriminating case" without prescribing a mechanism. This agreement adds a
concrete mechanism decision (below) and widens the required witness set beyond the two originally
reported cases, since a mechanism swap risks introducing new gaps a narrower witness set would
miss.

**Mechanism decision, recorded via owner governance** (`GOVERNANCE_SOURCE`, verbatim at
`https://github.com/EGAILab/minion-agent/issues/29#issuecomment-5689770460`, per
`agent-workflow.md` §11.10): the owner approved `url-py` (PyPI, MIT license, binding the same Rust
`url` crate/servo a Rust implementation would naturally use) as the implementation mechanism,
replacing the `urlsplit`-based proxy entirely — explicitly disclosed as an IMPLEMENTATION
MECHANISM, not a semantic oracle: pinned Pi behavior, the shared contract, and executable
witnesses remain authoritative; a future `url-py`/`rust-url` release that diverges observably from
pinned Pi would be a bug to fix, not a parity redefinition. The owner's own decision also records
required closure evidence (replace the proxy entirely, no parallel hand-written validator;
preserve/extend the witness set; differentially verify against live Node; keep the
success/failure→fallback branching itself under test) and dependency conditions (licensing,
platform/wheel availability, `py.typed`/type-stub availability, no `url-py` types crossing the
shared contract boundary) — all independently confirmed during this challenge pass (MIT license;
`py.typed` marker and `.pyi` stubs present; a prebuilt wheel exists for this project's own
Windows/CPython 3.13 target; `mypy --strict` passes against the stub-typed API with no
type-ignore needed).

### L11-SC-R012

- `packages/ai/src/auth/oauth/openai-codex.ts:217` (already characterized in the first-round
  convergence work for this row): confirmed again this pass that the coercion is literally
  `Number(json.interval.trim())` — both `.trim()` and `Number()` are ordinary ECMAScript builtins,
  not Pi-specific logic, so BOTH operations' own exact semantics are in scope, not only `Number()`
  in isolation.
- Live Node confirmed `String.prototype.trim()` removes `U+FEFF` (`"﻿1".trim() === "1"`),
  alongside the standard ASCII whitespace/control set and the full Unicode `Zs`
  (`Space_Separator`) category plus line terminators (`U+2028`/`U+2029`) — the review's own witness
  reproduced exactly; a fixed, explicit code-point set (not Python's own `str.strip()`, and not a
  generic "is this character whitespace" predicate) is required to reproduce it precisely.
- Live Node confirmed `Number("0x" + "f".repeat(1000))` is exactly `Infinity` — JS `Number`'s own
  silent-overflow behavior for a value outside IEEE-754 double range, not a thrown error. Live
  Python confirmed `float(int("f" * 1000, 16))` raises an uncaught `OverflowError` for the
  identical magnitude — this is a Python-arbitrary-precision-int-to-float narrowing-conversion
  behavior with no ECMAScript analog, and the review's own witness reproduced exactly.

**Answering the §11.8.4 checklist:**

- *Is the Pi source mapping correct?* Yes, confirmed above.
- *Is the behavior matrix complete enough to distinguish realistic wrong implementations?* Yes —
  the refined witnesses specifically target the two dimensions ("what exactly counts as
  whitespace" and "what happens at the boundary of representable magnitude") a naive
  regex-plus-`str.strip()` implementation gets wrong, distinct from the first round's own
  sign/Unicode-digit dimensions.
- *Are any cases implementation mechanics rather than observable semantics?* No — both the exact
  trim code-point set and the overflow-to-`Infinity` result are observable ECMAScript behavior,
  not Python mechanics; the FIX (a Python `OverflowError` catch) is mechanics, the REQUIRED
  RESULT (`Infinity`) is not.
- *Does any proposed fix silently reopen a lower certified layer?* No — `_js_number_coerce` has no
  certified-layer dependency.
- *Can both Python and Rust implement the rule idiomatically?* Yes — an explicit fixed
  whitespace-code-point set and a saturating/overflow-to-infinity numeric conversion are both
  ordinary, idiomatic constructs in either language.
- *Does the defect's own root cause depend on an extensibility point one language's own certified
  lower layers exposes and the other does not?* No.
- *Are all previous review findings represented by an executable or documentary acceptance
  criterion?* Yes — see the agreed witness list below.

**Refinement over the proposed characterization:** the review's own text names the two refined
witnesses without specifying the exact whitespace code-point set. This agreement makes it
concrete (see "Agreed observable matrix" below) rather than leaving "matches `trim()`" as an
unspecified black box a future implementer could get subtly wrong again.

### L11-SC-R018

- `packages/ai/src/auth/oauth/openai-codex.ts:126-130,199-209,251-264` (`readTokenResponse`,
  `startOpenAICodexDeviceAuth`, `pollOpenAICodexDeviceAuth`'s own `poll()`, all three re-read in
  full): confirmed the IDENTICAL pattern repeats three times — every non-`2xx`/`!response.ok`
  branch reads the body via `response.text().catch(() => "")` (a body-read failure becomes an
  empty string); every `2xx`/`response.ok` branch reads the body via `response.json()` with NO
  catch at all (a body-read failure is an uncaught rejection propagating through the existing
  call-site boundary, exactly like a JSON-syntax-parse failure on successfully-read bytes would).
- The review's own refined witness (a `200 OK` response whose body-read then fails) was
  independently reproduced against the actual candidate code via a scripted `httpx.MockTransport`
  response whose body stream raises during iteration: confirmed the prior remediation's own
  `except httpx.HTTPError: response_body = b""` unconditionally swallowed this regardless of
  status, producing exactly the fabricated `HttpResponse(status=200, body=b"", ...)` the review
  describes, which the caller then turns into a synthetic `JSONDecodeError` on an empty string —
  never a real Pi behavior.

**Answering the §11.8.4 checklist:**

- *Is the Pi source mapping correct?* Yes, confirmed above across all three real call sites, not
  only `readTokenResponse`.
- *Is the behavior matrix complete enough to distinguish realistic wrong implementations?* Yes —
  it directly separates "does the fallback string/reason-phrase mechanism work" (already closed)
  from "is swallowing a body-read failure conditioned on status" (the open half), matching exactly
  the dimension the first remediation missed.
- *Are any cases implementation mechanics rather than observable semantics?* One, which the
  review's own text already flags: the exact BOUNDARY between "status/headers received" and "body
  read attempted" is an httpx/`stream=True` implementation mechanic with no direct Pi-source
  analog (Pi's `fetch()` already separates these natively); the OBSERVABLE, portable requirement
  is only "a body-read failure after a 2xx status propagates; after a non-2xx status it does not,"
  not any particular staging mechanism to achieve that.
- *Does any proposed fix silently reopen a lower certified layer?* No — this is local to
  `HttpxTransport.post`, already this row's own transport seam.
- *Can both Python and Rust implement the rule idiomatically?* Yes — any HTTP client capable of
  observing the status code before or independently of a body-read failure (both httpx's own
  `stream=True` and Rust's `reqwest` support this) can implement a `status_code` check guarding
  whether a body-read error is converted to an empty body or re-raised.
- *Does the defect's own root cause depend on an extensibility point one language's own certified
  lower layers exposes and the other does not?* No.
- *Are all previous review findings represented by an executable or documentary acceptance
  criterion?* Yes — see the agreed witness list below, which adds the missing 2xx-propagates case
  as a DISTINCT witness from the already-closed non-2xx-swallows case, rather than one witness
  standing in for both.

**Refinement over the proposed characterization:** none beyond what the review's own text already
specified precisely (status-conditioned catching, pinned to the exact 2xx/non-2xx boundary) — this
challenge pass found the review's own required correction already fully actionable as stated.

### L11-SC-R021 (documentary, single review, bundled)

Independently re-read `js_json.py`'s own module docstring and `js_json_loads`'s own body: the
docstring's blanket claim ("Neither direction is a `json.dumps`/`json.loads` call with adjusted
options") is contradicted by `js_json_loads`'s own literal implementation
(`json.loads(text, parse_int=float, parse_constant=_reject_js_incompatible_constant)`), confirmed
via direct source read. The renderer (`js_json_stringify`) genuinely has no such stdlib
equivalent (confirmed by this row's own extensive `L11-SC-R010` review history). No behavior
change required — narrowing the claim to the rendering direction only, and describing the parsing
direction accurately, resolves the documentary contradiction.

## Agreed observable matrix (final)

| Finding | Observation | Required result |
|---|---|---|
| R011 | value has a recognized scheme, authority (if the scheme requires one) is non-empty with a valid host and numeric in-range port | WHATWG `new URL(value)` succeeds; `{code, state}` come from its own query string |
| R011 | value has a recognized scheme requiring an authority, but the host is empty, contains a forbidden character, or the port is non-numeric or out of `[0, 65535]` | WHATWG construction FAILS; falls through to the next parsing strategy against the ORIGINAL untouched input |
| R011 | value has a recognized scheme not requiring an authority (e.g. `mailto:`, `file:` with an empty host) | WHATWG construction succeeds even with no authority component |
| R011 | value has no recognized scheme at all (schemeless, or an invalid scheme character) | WHATWG construction FAILS; falls through |
| R012 | `interval` string has ECMA-262 `WhiteSpace`/`LineTerminator` characters (including `U+FEFF`) at either end | trimmed exactly per that fixed code-point set before coercion, matching `String.prototype.trim` exactly, not a host-language whitespace predicate |
| R012 | trimmed `interval` string is a hex/octal/binary literal whose magnitude exceeds IEEE-754 double range | coerces to `Infinity` (never a raised/uncaught error), which then fails the caller's own pre-existing finiteness guard |
| R018 | response status is `2xx`, but reading the body subsequently fails (e.g. connection reset mid-body) | the failure PROPAGATES through the existing call-site boundary, exactly like a JSON-syntax-parse failure on successfully-read bytes would; NEVER converted into a synthetic empty-body success |
| R018 | response status is non-`2xx`, and reading the body subsequently fails | the failure is swallowed to an empty body string, and the existing `{body text, or the status's own reason phrase}` fallback applies exactly as it already does for a genuinely empty body |

## Agreed implementation and evidence constraints

The implementation pass must:

- for R011: replace the `urlsplit`-based proxy in `parse_authorization_input` entirely with
  `url-py`'s `URL.parse`/`URLError`, per the owner's own governance decision; do not retain a
  second, parallel hand-written WHATWG validator; add permanent witnesses for the full agreed
  matrix above (not only the two originally-reported cases), each differentially confirmed live
  against Node during this pass;
- for R012: add a shared `js_trim` helper (the exact fixed ECMA-262 whitespace/line-terminator
  code-point set) used at every call site that trims before an ECMAScript numeric/URL coercion —
  both `_js_number_coerce` AND `parse_authorization_input`, since both share the identical `.trim()`
  primitive in pinned Pi, even though the second review only separately flagged the numeric-coercion
  call site; catch the non-decimal-literal overflow case and return `Infinity`; add permanent
  witnesses for the BOM-trim and overflow cases, cross-checked against live Node;
- for R018: condition `HttpxTransport.post`'s own body-read-failure catch on the response's status
  code (2xx re-raises; non-2xx swallows to an empty body); add a permanent witness for BOTH
  branches (a 2xx-propagates witness is new; the non-2xx-swallows witness already exists and must
  be re-run, not merely assumed unaffected);
- for R021: narrow `js_json.py`'s own module docstring claim to the rendering direction only —
  documentation-only, no test required beyond the existing suite continuing to pass;
- synchronize `spec/auth.md` (the WHATWG success/failure/fallback boundary for
  `parse_authorization_input`, the exact trim/overflow rules for `interval` coercion, and the
  status-conditioned body-read-failure rule for token exchange/refresh) and
  `pi-parity-manifest.yaml` (`PROV-012`'s own rule/tests/python fields) with the agreed matrix
  above, per §11.8.6's synchronization requirement;
- rerun every directly-affected previously-closed finding's own test (the full
  `test_openai_codex_oauth.py`/`test_http_transport.py`/`test_js_json.py` suites, not only the new
  witnesses) to confirm no regression;
- add `url-py` as a project dependency per the owner's own recorded conditions (license, wheel
  availability, no `url-py` types crossing the shared contract boundary);
- push the candidate and return the exact remote SHA for a fresh, complete independent review.

## Scope and feasibility

No certified lower layer needs reopening for any of the three findings. Rust can implement all
three agreed rules idiomatically — R011 especially so, since Rust's own natural WHATWG URL
mechanism (`url` crate/servo) is the literal same engine `url-py` binds, eliminating cross-language
drift risk for that specific rule rather than merely reducing it. No Rust implementation is
authorized by this document; Rust Layer 11 Pass 2 Slice C remains not started until the
remediated shared/Python candidate is independently reviewed and approved under the normal
workflow.

## Agreement status

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION

OPEN FINDINGS
    L11-SC-R011
    L11-SC-R012
    L11-SC-R018
    L11-SC-R021 (bundled, single-review documentary finding, no convergence trigger of its own)

CHALLENGE FINDINGS
    R011: mechanism decision recorded via owner governance (url-py); witness set widened beyond
        the two originally-reported cases to the full agreed matrix.
    R012: exact trim code-point set made concrete rather than left as "matches trim()."
    R018: none beyond what the review's own text already specified precisely.
    R021: none -- documentary correction only, confirmed accurate as described.

NEXT OWNER
    Claude

NEXT ACTION
    Implement the agreed matrix for R011/R012/R018, apply the R021 documentary correction, add
    every required permanent witness, synchronize spec/auth.md and pi-parity-manifest.yaml, rerun
    the full affected test suites, add the url-py dependency per the owner's own recorded
    conditions, and return the exact remote candidate SHA for a new complete independent review.
```

This agreement is a convergence checkpoint, not final contract approval or Layer-11 certification.
A new complete exact-SHA review remains mandatory once this fix is implemented.
