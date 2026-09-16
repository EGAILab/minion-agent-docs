# Layer 11 Pass 2 Slice C — L11-SC-R022/R023/R024 convergence agreement

## Decision

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION
```

Exact checkpoint reviewed:

- code PR `EGAILab/minion-agent#33` at `f96740c821a0226033cfadfe7a7e8e55f0b117c4`;
- docs PR `EGAILab/minion-agent-docs#92` at `eed2538969cc562cc6a8dfbdd4206e5f82703243`;
- pinned Pi at `b7bb00b936dbe21b8e160b3e89efdec361846699`;
- originating mandatory final-complete review (workflow §11.8.8): docs PR #96 at
  `e23a7ebdcd21a2bc883dd84aa640c32bc9a8f42b`.

Issue #29 recorded `STATUS: CONTRACT_CONVERGENCE`, `NEXT_OWNER: Claude`,
`NEXT_ACTION: challenge and checkpoint L11-SC-R022/R023/R024 before remediation`. This is
convergence-challenge/agreement evidence only; no candidate, shared semantic file, or Rust
production was changed by writing this document.

## Trigger check (agent-workflow.md §11.8, mandatory)

All three findings are FIRST-OCCURRENCE: none has yet survived a repeat review, and Slice C's
running review count is well past three rejections in total, but these three specific finding
IDs are new. Neither strict §11.8 trigger condition is independently met per-ID. The final
review's own text recommends treating them together where they are genuinely coupled ("R022 and
R023 are coupled at the HTTP response/body boundary; R024 is a separate renderer surface"), and
the coordination issue's own `NEXT_ACTION` explicitly requests a challenge/checkpoint pass before
remediation given R022's architectural weight (a real seam redesign, not a point patch). This
document treats R022+R023 as one coupled characterization (both touch
`HttpResponse`/`HttpxTransport`'s own response/body boundary) and R024 as a separate, narrower,
self-contained fix bundled into the same implementation pass -- not because either has met the
numeric trigger, but because the coordination explicitly asked for this pass before remediation
and R022 alone justifies the rigor.

## Challenge pass (§11.8.4)

Independently re-verified, this pass, directly against pinned Pi source and live Node/Python
probes (not merely trusted from the review's own text):

### L11-SC-R022 -- eager body buffering collapses Pi's response/body phases

- `packages/ai/src/auth/oauth/openai-codex.ts:191-233` (`startOpenAICodexDeviceAuth`) and
  `:235-290` (`pollOpenAICodexDeviceAuth`'s own `poll()`), full re-read: confirmed the `404`
  device-start branch and the `403`/`404` device-poll branch both return/reject WITHOUT ever
  calling `.text()`/`.json()` -- `fetchWithLoginCancellation` only awaits `fetch()` itself
  (status/headers), never the body, so these branches genuinely never touch the response body at
  all in Pi's own execution.
- `:171-189` (`refreshAccessToken`): confirmed `readTokenResponse(response, "refresh")` is called
  OUTSIDE the function's own `try`/`catch` (which wraps only the `fetch()` call itself) -- a
  `response.json()` rejection inside `readTokenResponse` therefore propagates RAW, never passing
  through the uniform `"OpenAI Codex token refresh error: ..."` wrapper.
- Reproduced BOTH witnesses live against the exact rejected candidate BEFORE any fix: witness A
  (a `404` device-start response whose body stream never completes) causes `_start_device_auth`
  to hang until an external timeout, instead of raising `DeviceCodeNotEnabledError` immediately;
  witness B (a `200` refresh response whose body-read raises `RuntimeError("body boom")`) surfaces
  as `OAuthRefreshTransportError("OpenAI Codex token refresh error: body boom")`, not the raw
  `RuntimeError` Pi's own structure would propagate.
- Root cause confirmed: `HttpxTransport.post`'s own `do_request` unconditionally calls
  `await response.aread()` before ever returning an `HttpResponse` to the caller -- the CALLING
  code in `openai_codex_oauth.py` already has the CORRECT branch structure (the 404/403/404
  branches already never call `.text()`; `_read_token_response` is already called OUTSIDE
  `refresh_fetch`'s own wrapper) -- the collapse happens entirely one layer below, in the
  transport's own eager buffering, not in this module's own control flow.

**Answering the §11.8.4 checklist:**

- *Is the Pi source mapping correct?* Yes, confirmed above via direct re-read of all three call
  sites plus live reproduction of both witnesses against the exact rejected candidate.
- *Is the behavior matrix complete enough to distinguish realistic wrong implementations?* Yes --
  it directly separates "does the transport ever start reading the body before a caller asks"
  (the actual defect) from "does the transport-level status/reason-phrase fallback already work"
  (already correctly closed by R018), which a caller-side-only fix could not address since the
  root cause is entirely inside the transport.
- *Are any cases implementation mechanics rather than observable semantics?* One: the EXACT
  mechanism by which laziness is achieved (a closure-based deferred read vs. some other shape) is
  implementation mechanics; the OBSERVABLE requirement is only "a caller that never asks for the
  body must not be blocked by it, and a body-read failure must surface exactly where Pi's own
  code structure would let it surface, not one architectural layer earlier."
- *Does any proposed fix silently reopen a lower certified layer?* No -- this is confined to
  `http_transport.py`'s own `HttpResponse`/`HttpxTransport`, plus mechanical `await` additions at
  `openai_codex_oauth.py`'s own existing call sites; no certified lower layer's own contract
  changes.
- *Can both Python and Rust implement the rule idiomatically?* Yes -- any HTTP client capable of
  separating "response headers received" from "body consumption" (Python's own `httpx` with
  `stream=True`; Rust's own `reqwest` with its default streaming body model) can implement this
  rule idiomatically; deferred/lazy body consumption is the NATURAL default shape in both
  ecosystems, not an unusual accommodation.
- *Does the defect's own root cause depend on an extensibility point one language's own certified
  lower layers exposes and the other does not?* No -- this is a pure HTTP-client-usage question
  local to this row's own transport seam, with no cross-layer extensibility point involved.
- *Are all previous review findings represented by an executable or documentary acceptance
  criterion?* Yes -- both witnesses (device-start-404-never-reads-body,
  refresh-2xx-body-failure-propagates-raw) are captured in the agreed matrix below, plus the
  device-poll 403/404 analog the review names as a required companion.

### L11-SC-R023 -- Fetch's leading UTF-8 BOM removal is missing

- Confirmed live: WHATWG `TextDecoder('utf-8').decode(...)` (the algorithm Fetch's own
  `Response.text()`/`.json()` use for UTF-8 body decoding) strips exactly one leading BOM
  (`EF BB BF`) and leaves an INTERIOR `U+FEFF` untouched -- reproduced against the exact bytes
  `EF BB BF` + a JSON body, and separately against a body with `U+FEFF` in the MIDDLE of the text
  (confirmed NOT stripped there).
- Confirmed live against the exact candidate: `HttpResponse.text()`'s own
  `body.decode("utf-8", errors="replace")` leaves the BOM in place as a literal `U+FEFF`
  character, which Python's own `json.loads` then explicitly REJECTS with its own dedicated error
  message (`"Unexpected UTF-8 BOM (decode using utf-8-sig)"`), confirmed live -- a BOM-prefixed
  token response would fail entirely, not merely render with a stray character.
- Confirmed live: Python's own `bytes.decode("utf-8-sig")` strips exactly one leading BOM and
  leaves an interior one untouched -- the SAME two-case behavior as `TextDecoder`, and it composes
  correctly with the EXISTING `errors="replace"` fallback for malformed bytes (confirmed live: a
  BOM-prefixed body containing an invalid UTF-8 byte still strips the BOM AND replaces the
  invalid byte with `U+FFFD`).

**Answering the §11.8.4 checklist:**

- *Is the Pi source mapping correct?* Yes -- this is standard Fetch/`TextDecoder` platform
  behavior Pi relies on implicitly by using `Response.text()`/`.json()`, not Pi-specific logic;
  confirmed against the WHATWG-specified decoding algorithm directly.
- *Is the behavior matrix complete enough to distinguish realistic wrong implementations?* Yes --
  it requires BOTH a leading-BOM-stripped case and an interior-BOM-preserved negative control, so
  an implementation that strips EVERY `U+FEFF` occurrence (not only a leading one) is also ruled
  out, not only one that strips none at all.
- *Are any cases implementation mechanics rather than observable semantics?* No -- the resulting
  decoded text is directly observable (it determines whether JSON parsing succeeds and what the
  parsed value contains).
- *Does any proposed fix silently reopen a lower certified layer?* No -- confined to
  `HttpResponse.text()`'s own decode call.
- *Can both Python and Rust implement the rule idiomatically?* Yes -- Python's own
  `"utf-8-sig"` codec and Rust's own UTF-8 BOM-stripping utilities (or a two-line manual prefix
  check) both implement this trivially.
- *Does the defect's own root cause depend on an extensibility point one language's own certified
  lower layers exposes and the other does not?* No.
- *Are all previous review findings represented by an executable or documentary acceptance
  criterion?* Yes -- both the leading-BOM-success case and the interior-BOM-preserved negative
  control are in the agreed matrix below, plus a non-2xx BOM-prefixed text case the review
  explicitly also requires.

**Refinement over the review's own text:** since R023 is fixed inside `HttpResponse.text()`
itself (the SAME method R022's redesign already touches, since laziness moves the decode call
into the same lazy path), both fixes land in one coherent edit to that method, not two separate
passes.

### L11-SC-R024 -- valid overflowing JSON numbers crash the `JSON.stringify` renderer

- Confirmed live: `JSON.parse('{"x":1e400,"y":-1e400}')` produces `{x: Infinity, y: -Infinity}`
  (JSON number syntax permits an exponent this large; ECMAScript's own numeric literal parsing
  overflows to the corresponding infinite value, matching ordinary `Number` overflow behavior --
  this is DISTINCT from the bare invalid token `Infinity`, which `L11-SC-R013` correctly rejects,
  since `1e400` is syntactically a valid JSON NUMBER, not the non-JSON bare identifier token).
- Confirmed live: `JSON.stringify({x: Infinity, y: -Infinity})` produces
  `{"x":null,"y":null}` -- ECMA-262's own `SerializeJSONProperty` step for a non-finite Number
  returns the string `"null"` unconditionally, regardless of position (top-level or nested).
- Confirmed live against the exact candidate: `js_json_loads` correctly parses `1e400`/`-1e400`
  into Python `inf`/`-inf` (matching Pi); `js_json_stringify` then raises an uncaught
  `AssertionError` from `_shortest_digits_and_exponent`'s own `assert sign == 0` step, which
  assumes a FINITE magnitude decomposes into an ordinary `Decimal` digit tuple -- `Decimal(repr(
  float("inf")))` does not, and the function was never guarded against non-finite input reaching
  it at all.
- **Correction to the review's own text, independently verified and found inaccurate**: the
  review additionally claims "raw `JSON.stringify(Infinity)` returns JavaScript `undefined`."
  Confirmed live this is FALSE -- `JSON.stringify(Infinity)` returns the STRING `"null"`
  (`typeof` `"string"`), identical to the nested case; `JSON.stringify(undefined)` (a
  DIFFERENT, unrelated input) is what returns `undefined`. Per this row's own established
  discipline (never implement a review's claim without independent verification; correct a wrong
  claim rather than encode it), this agreement implements the VERIFIED top-level behavior
  (`"null"`, uniform with the nested case), not the reviewed text's own inaccurate claim. This
  also means NO top-level-vs-nested special case is needed at all: `js_json_stringify`'s existing
  recursive structure already treats the top-level call identically to a nested one, so a single
  fix inside the number-rendering step covers both positions uniformly. `js_json_stringify`'s own
  `JsonValue` input domain (`null`/bool/number/str/list/dict) has no representation for JS
  `undefined` in the first place, so the `undefined`-specific case the review's text describes is
  not reachable through this function at all and requires no handling.

**Answering the §11.8.4 checklist:**

- *Is the Pi source mapping correct?* Yes for the core crash-reproducing claim (independently
  reproduced against both Node and the candidate); the review's own supplementary claim about
  top-level `undefined` was independently checked and found incorrect, corrected above rather
  than propagated.
- *Is the behavior matrix complete enough to distinguish realistic wrong implementations?* Yes --
  covers the direct-renderer case (nested non-finite values inside an object) and the real
  call-site case (a device-start `interval` overflow reaching the exact invalid-response
  message), which is the review's own concrete evidence that this is reachable through a real
  public path, not merely a synthetic renderer unit test.
- *Are any cases implementation mechanics rather than observable semantics?* No.
- *Does any proposed fix silently reopen a lower certified layer?* No -- confined to
  `js_json.py`'s own number-rendering step, already this row's own owned module.
- *Can both Python and Rust implement the rule idiomatically?* Yes -- checking `math.isfinite`
  (Python) or `f64::is_finite` (Rust) before attempting decimal decomposition is trivial and
  idiomatic in both languages.
- *Does the defect's own root cause depend on an extensibility point one language's own certified
  lower layers exposes and the other does not?* No.
- *Are all previous review findings represented by an executable or documentary acceptance
  criterion?* Yes -- both the direct-renderer non-finite case and the real device-start-overflow
  call-site case are in the agreed matrix below.

## Agreed observable matrix (final)

| Finding | Observation | Required result |
|---|---|---|
| R022 | device-start response status is `404`, body stream never completes/fails | `DeviceCodeNotEnabledError` raised immediately; body consumption never starts |
| R022 | device-poll response status is `403` or `404`, body stream never completes/fails | `PENDING` outcome returned immediately; body consumption never starts |
| R022 | refresh response status is `2xx`, body-read subsequently fails | the raw underlying body-read error propagates UNCHANGED, never wrapped as `OAuthRefreshTransportError` |
| R022 | existing R018 success/non-success body-read-failure witnesses (2xx propagates raw; non-2xx swallows to empty body, any exception type) | UNCHANGED, must remain green after the seam redesign |
| R023 | response body bytes begin with the 3-byte UTF-8 BOM (`EF BB BF`) | exactly one leading BOM is stripped before the text is exposed via `.text()`; a BOM-prefixed successful JSON body parses correctly, and a BOM-prefixed non-2xx text body is used verbatim (BOM-stripped) as the failure-message body text |
| R023 | response body bytes contain `U+FEFF` NOT at the very start (encoded mid-string) | left untouched -- only a LEADING BOM is special |
| R024 | a JSON value being rendered (at any nesting depth, including top-level) is a non-finite Python `float` (`inf`, `-inf`, or `nan` reached via `js_json_loads`'s own already-correct overflow parsing) | renders as the JSON literal `null`, never raises |
| R024 | a real call-site value (e.g. device-start's own `interval` field) overflows to `Infinity`/`-Infinity` via `js_json_loads` | the existing finite-value validation guard still rejects it as invalid (unchanged); the resulting `"Invalid ... response: {rendered json}"` message renders successfully with `null` in place of the overflowing field, instead of crashing with `AssertionError` |

## Agreed implementation and evidence constraints

The implementation pass must:

- for R022: redesign `HttpResponse`/`HttpxTransport.post` so status/`reason_phrase` are available
  to a caller BEFORE the body is read, and body consumption happens ONLY when a caller explicitly
  requests it (`.text()`, made `async`) -- the exact mechanism (a lazily-invoked, signal-aware
  read closure captured at `post()`-time) is an implementation detail; existing
  `HttpResponse(status=..., body=...)` construction (used throughout the test suite for
  synthetic, already-known responses) MUST remain valid and requires no test-fixture redesign,
  only the necessary `await` additions everywhere `.text()` is now called;
- preserve the EXISTING signal-based cancellation guarantee across the split: BOTH the initial
  status/headers phase AND the later lazy body-read phase must remain racing against `signal` via
  `run_cancellable`, not only the first phase (a regression here would silently drop cancellation
  coverage during body-reading, which no review has asked for but which the existing design
  already provides and must not lose);
- preserve the EXISTING owned-client-closes-itself guarantee (`R016`) for every path that DOES
  read the body, and for the initial-phase-failure path (closing eagerly if even getting
  status/headers fails); an owned client whose body is deliberately never read by the caller
  (the abandoned-body case, e.g. device-start 404) may rely on ordinary Python object lifetime
  cleanup rather than a new explicit close-on-abandon API, since neither pinned Pi's own runtime
  nor any prior review requires deterministic cleanup for a body a caller intentionally never
  consumes, and introducing new explicit-cleanup API surface is exactly the kind of unrelated
  scope expansion `agent-workflow.md` §11.8.6 warns against;
- for R023: strip a leading UTF-8 BOM (and only a leading one) inside the SAME `.text()` method
  R022's redesign already touches, using `"utf-8-sig"` in place of `"utf-8"` for the decode,
  keeping the existing `errors="replace"` fallback;
- for R024: guard `_js_number_to_string`/`_shortest_digits_and_exponent` against a non-finite
  input, rendering `"null"` uniformly for `inf`/`-inf`/`nan` at any nesting depth (no special
  top-level case, per the corrected challenge-pass finding above);
- convert every reviewer witness into permanent regression evidence, rerun every directly-affected
  previously-closed finding's own test (the full `test_http_transport.py`/
  `test_openai_codex_oauth.py`/`test_js_json.py` suites, not only the new witnesses), and
  synchronize `spec/auth.md`/`pi-parity-manifest.yaml` with the agreed matrix above;
- push the candidate and return the exact remote SHA for a new complete independent review, since
  this final-complete review's own rejection makes `L11-SC-R011` PROVISIONALLY CLOSED but the
  Slice as a whole `NOT CERTIFIED` until these three findings close too.

## Scope and feasibility

No certified lower layer needs reopening for any of the three findings. Rust can implement all
three agreed rules idiomatically (deferred body consumption is `reqwest`'s own natural default
shape; UTF-8 BOM stripping and non-finite-to-`null` JSON rendering are both trivial, common
patterns). No Rust implementation is authorized by this document; Rust Layer 11 Pass 2 Slice C
remains `NOT_IMPLEMENTED / BLOCKED` until the remediated shared/Python candidate is independently
reviewed and approved under the normal workflow.

## Agreement status

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION

OPEN FINDINGS
    L11-SC-R022
    L11-SC-R023
    L11-SC-R024

CHALLENGE FINDINGS
    R022: none beyond what the review's own text already specified precisely -- confirmed both
        witnesses live against the exact rejected candidate before designing the fix.
    R023: none -- confirmed the leading-vs-interior BOM distinction live, composes correctly
        with the existing errors="replace" fallback.
    R024: one correction, not a refinement -- the review's own claim that top-level
        JSON.stringify(Infinity) returns undefined is independently verified FALSE (it returns
        the string "null", identical to the nested case); this agreement implements the
        verified behavior, not the reviewed claim, and notes no top-level-vs-nested special case
        is needed as a result.

NEXT OWNER
    Claude

NEXT ACTION
    Implement the agreed matrix for R022/R023/R024, add every required permanent witness,
    synchronize spec/auth.md and pi-parity-manifest.yaml, rerun the full affected test suites,
    and return the exact remote candidate SHA for a new complete independent review.
```

This agreement is a convergence checkpoint, not final contract approval or Layer-11
certification. A new complete exact-SHA review remains mandatory once this fix is implemented.
