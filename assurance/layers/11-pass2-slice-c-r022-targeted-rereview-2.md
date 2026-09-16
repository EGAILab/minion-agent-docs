# Layer 11 Pass 2 Slice C — L11-SC-R022 targeted re-review 2

## Exact target

```text
code PR #33
    33914cbf52c009fefc8589b21bd8d1b680495374

docs PR #92
    f55dd808593415bc0d94487bf3f28ea21745202c

base main
    ea3b64caca84e95245fa0d5f2a1a650452686649

base docs master
    1e3c224ed7912d51fa28f33563622e5155947cda

prior targeted review
    minion-agent-docs PR #97
    6a76703cbbb72e854fc672fbbf87bb509783574f

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

The exact heads were fetched from GitHub and matched issue #29. Both candidate PRs were open,
Ready for Review, unmerged, and remote-reachable. Issue #29 was open with
`STATUS: CONTRACT_CONVERGENCE`, `NEXT_OWNER: Codex`, and requested this narrow R022 review. No
candidate/shared/Python/Rust file and no Layer 12 work was modified.

## What is now correct

The candidate's `HttpResponse.discard()` closes an ordinary abandoned streamed response without
starting a body read. For a default/owned client it also closes the client; repeated device-poll
403 responses are each discarded; discard after a completed text read and discard of a synthetic
buffered response are harmless. The convergence agreement's trigger text is also corrected to
recognize the layer-scoped three-rejection trigger.

The prior leak witness is therefore closed for successful cleanup operations.

## L11-SC-R022 — STILL OPEN (cleanup failure must not replace Pi's status-only outcome)

The new cleanup is an implementation mechanism. Pinned Pi never reads the response body on
device-start 404 or device-poll 403/404 and therefore returns its fixed semantic outcome without
exposing a body-stream cleanup operation. The candidate instead awaits `response.discard()` before
that outcome. If the streamed response's `aclose()` raises, that cleanup error replaces the Pi
outcome.

Minimal executable witness through the real candidate seam:

```text
setup
    httpx MockTransport returns status 404
    its AsyncByteStream body is never iterated
    AsyncByteStream.aclose() raises RuntimeError("close boom")
    call _start_device_auth(HttpxTransport(client), signal)

Pi expected
    fixed DeviceCodeNotEnabledError
    cleanup mechanics are not observable

candidate observed
    RuntimeError("close boom")
```

Fresh observed output:

```text
RuntimeError 'close boom'
```

There is a second exception-safety defect in the shared close helper: it awaits
`response.aclose()` before closing an owned client, without a `finally`. If response close raises,
the owned client is never closed. The helper sets its `closed` guard before either await, so later
calls become no-ops and cannot retry the skipped client cleanup.

The narrow remediation is:

1. preserve the fixed device-start/poll status-only outcome even when discard/close mechanics
   fail; cleanup failure must not become a new public auth failure;
2. attempt owned-client closure even if response closure fails;
3. retain idempotency without marking unattempted cleanup as successfully complete;
4. add permanent witnesses for both device-start 404 and device-poll 403/404, including an owned
   client, using a stream whose `aclose()` raises;
5. retain every prior R022 ordering, failure-classification, cancellation, no-read, and repeated-
   poll closure witness.

This is a refined witness for the same R022 lifecycle mechanism, not a shared semantic change and
not a lower-layer reopen. An idiomatic Rust implementation may use infallible/destructor-based
resource release; Python's cleanup mechanism is not normative.

## Previously closed findings

R023 and R024 were untouched and remain provisionally closed at this candidate lineage. The
originating review's inaccurate top-level-Infinity statement remains superseded: direct Node
verification gives the string `"null"`.

## Fresh checks

```text
affected HTTP transport + OAuth suites
    116 passed

ruff
    PASS

mypy src/minion_agent tests/typing
    PASS; 75 source files

schema + manifest validation
    213 passed
```

The candidate owner reports 1490 passed / 19 xfailed and 100% coverage for the full suite; the
targeted review did not need to repeat the unchanged full suite after the refined executable
witness independently failed through production code.

## Verdict

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

Next action is the narrow exception-safe cleanup correction above, followed by another targeted
R022 closure review. One final complete section 11.8.8 review is still required afterward.
