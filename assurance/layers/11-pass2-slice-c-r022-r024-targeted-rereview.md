# Layer 11 Pass 2 Slice C — R022/R023/R024 targeted convergence re-review

## Exact target

```text
code PR #33
    1d3d9b958b7acd58ace6eaf8edb68870f45633cf

docs PR #92
    83238d30039bbf2c8cb5f88a95a4a8f35f519d03

base main
    ea3b64caca84e95245fa0d5f2a1a650452686649

base docs master
    1e3c224ed7912d51fa28f33563622e5155947cda

originating final-complete review
    minion-agent-docs PR #96
    e23a7ebdcd21a2bc883dd84aa640c32bc9a8f42b

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

The exact candidate heads were fetched from GitHub and matched issue #29. Both candidate PRs were
open, Ready for Review, unmerged, and remote-reachable. Issue #29 was open with
`STATUS: CONTRACT_CONVERGENCE`, `NEXT_OWNER: Codex`, and requested this targeted review. This was
review mode only: no candidate/shared/Python/Rust file and no Layer 12 work was modified.

## Source recheck and correction to the originating review

Pinned Pi's `openai-codex.ts` status/body ordering and the WHATWG body-decoding behavior were
rechecked before the implementation. The R022 and R023 source characterizations remain correct.

The originating review's supplementary R024 statement about top-level infinity was wrong. Direct
Node verification gives:

```text
JSON.stringify(Infinity)
    "null" (typeof result == "string")

JSON.stringify({x: Infinity, y: -Infinity, z: NaN})
    {"x":null,"y":null,"z":null}
```

`JSON.stringify(undefined)`, not `JSON.stringify(Infinity)`, returns JavaScript `undefined`.
The candidate correctly challenged the mistaken statement and implemented the actual pinned
runtime behavior. This review supersedes only that inaccurate supplementary sentence; the
originating R024 crash witness and classification were valid.

## Finding results

### L11-SC-R023 — PROVISIONALLY CLOSED

`HttpResponse.text()` now uses UTF-8 decoding with exactly-one-leading-BOM handling. Independent
inspection and tests confirm:

- a leading UTF-8 BOM is removed before JSON parsing/text observation;
- an interior `U+FEFF` remains data;
- malformed UTF-8 replacement behavior is retained.

The shared spec and manifest state the language-neutral Fetch rule. No lower-layer delta is
needed. R023 is provisionally closed at the exact code/docs SHA pair above.

### L11-SC-R024 — PROVISIONALLY CLOSED

`js_json_stringify` now checks number finiteness before decimal decomposition and renders
`Infinity`, `-Infinity`, and `NaN` as `null` at both top level and nested positions. The real
device-start overflow path now produces the required exact invalid-response message rather than
raising `AssertionError`. The tests distinguish valid overflowing JSON number syntax (`1e400`)
from the invalid bare JSON token `Infinity`. R024 is provisionally closed at the exact code/docs
SHA pair above.

### L11-SC-R022 — STILL OPEN (refined resource-lifecycle witness)

The candidate fixes the original ordering/classification witnesses:

- `post()` returns after status/headers without consuming the body;
- device-start 404 and device-poll 403/404 are no longer blocked by a never-ending body;
- refresh 2xx body-read failure now propagates at `_read_token_response`, outside the
  request-level refresh wrapper;
- status-conditioned R018 behavior and signal cancellation remain intact.

However, the redesign leaves every response whose body is intentionally not read open. With the
default `HttpxTransport`, it also leaves the newly-created owned `AsyncClient` open. This is the
exact device-start-404/device-poll-403-or-404 path introduced to close R022; polling can repeat the
leak once per pending response.

Minimal executable witness through the real seam:

```text
setup
    tracked httpx.AsyncByteStream records whether __aiter__ starts and aclose runs
    MockTransport returns status 404 with that stream
    call _start_device_auth(HttpxTransport(...), signal)

candidate after the fixed status-only return
    read_started = false       # original ordering defect is fixed
    stream_closed = false      # response is abandoned open

candidate after explicitly closing the injected AsyncClient
    stream_closed = false      # client close does not close the abandoned response

same witness with HttpxTransport's default/owned client
    client_closed = false
    stream_closed = false
```

The observed trace was:

```text
after status-only return {'read_started': False, 'stream_closed': False}
after external client close {'stream_closed': False}
owned transport after status-only return {'client_closed': False, 'stream_closed': False}
```

The convergence artifact's assertion that these resources can rely on “ordinary Python object-
lifetime cleanup” is therefore not evidence of cleanup and is false for the observable close
hooks. `httpx` manual streaming requires explicit asynchronous response closure; an async close
cannot be manufactured by ordinary synchronous object destruction. Absence of a `ResourceWarning`
does not prove the response/client was closed.

This is a parity-neutral implementation/lifecycle defect in the R022 seam, not a request to read
the body and not a shared Pi-semantic change. The narrow remediation is to provide an idempotent
async discard/close operation (or an equivalent internal mechanism) and invoke it on every
status-only branch, closing the streamed response and any owned client without consuming the body.
An idiomatic Rust implementation may satisfy the same lifecycle property through RAII/drop; the
Python mechanism is not normative. Permanent evidence must reproduce both the injected-response
and owned-client observations above, plus the repeated 403/404 polling path, while retaining all
existing R022 ordering/failure/cancellation witnesses.

Because the implementation pass is not production-sound on the very status-only path R022 owns,
R022 is not yet provisionally closed.

## Contract and evidence notes

- The current R022/R023/R024 normative behavior is independently implementable in Rust without
  reading Python.
- No canonical runner simulates these network/stream behaviors; explicit language tests are the
  appropriate evidence.
- No certified lower layer needs reopening.
- The convergence agreement's trigger paragraph says the layer-wide three-rejection trigger was
  not met “per-ID,” despite workflow section 11.8 defining that second trigger at layer scope.
  The project did enter convergence and completed the required checkpoint, so this wording does
  not invalidate the semantic work, but it should be corrected in the next assurance increment.

## Fresh gates

```text
focused auth transport/OAuth/JSON suites
    147 passed

full suite without coverage addopts
    1484 passed, 19 xfailed, 0 failed

full configured suite
    PASS; 100.00% coverage; 3863 statements / 0 missed

ruff
    PASS

mypy src/minion_agent tests/typing
    PASS; 75 source files

schema + manifest validation
    213 passed
```

Green gates do not exercise the abandoned-response lifecycle witness above.

## Targeted verdict

```text
L11-SC-R022
    STILL OPEN

L11-SC-R023
    PROVISIONALLY CLOSED

L11-SC-R024
    PROVISIONALLY CLOSED

Layer 11 Pass 2 Slice C
    REJECTED / CONTRACT_CONVERGENCE CONTINUES

Rust Slice C
    NOT_IMPLEMENTED / BLOCKED

Layer 12
    NOT STARTED
```

Next action is one narrow R022 lifecycle remediation followed by targeted closure review. A final
complete section 11.8.8 review remains required after every finding is provisionally closed.
