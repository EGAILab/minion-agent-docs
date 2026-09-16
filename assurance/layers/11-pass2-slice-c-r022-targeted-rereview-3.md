# Layer 11 Pass 2 Slice C — L11-SC-R022 targeted re-review 3

## Exact target

```text
code PR #33
    931dc4f21f5b100972e7d053aee64ade422e975f

docs PR #92
    f55dd808593415bc0d94487bf3f28ea21745202c

base main
    ea3b64caca84e95245fa0d5f2a1a650452686649

base docs master
    1e3c224ed7912d51fa28f33563622e5155947cda

prior targeted review
    minion-agent-docs PR #98
    8ca245f8150014b582117d16ff78a0f19ff6ed15

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

The exact heads were fetched from GitHub and matched issue #29. Both PRs were open, Ready for
Review, unmerged, and remote-reachable. Issue #29 was open with
`STATUS: CONTRACT_CONVERGENCE`, `NEXT_OWNER: Codex`, and requested this narrow R022 review. No
candidate/shared/Python/Rust file and no Layer 12 work was modified.

## What is now correct

For ordinary `Exception` failures, response close no longer replaces Pi's fixed status-only
outcome and no longer skips the owned-client close attempt. The new device-start, device-poll,
injected-client, and owned-client witnesses are real and pass. Every earlier R022 ordering,
no-read, failure-classification, and successful-cleanup witness remains green.

## L11-SC-R022 — STILL OPEN (cancellation-safe cleanup is not independent)

The implementation says both close attempts are independent while deliberately allowing
`asyncio.CancelledError` to propagate. Those requirements are compatible: a `finally`-equivalent
path can attempt owned-client closure and then let cancellation propagate. The candidate instead
runs two sequential `contextlib.suppress(Exception)` blocks. Because `CancelledError` is a
`BaseException`, cancellation from `response.aclose()` exits the helper before the owned client is
attempted. The `closed` guard was already set to `True`, so a later retry is also a no-op.

Minimal executable witness:

```text
setup
    HttpxTransport owns its AsyncClient
    MockTransport returns status 404
    response stream aclose() raises asyncio.CancelledError
    call _start_device_auth through the real seam

required
    cancellation propagates
    owned-client close is still attempted before propagation completes

candidate observed
    CancelledError propagates
    owned client remains open
```

Fresh trace:

```text
CancelledError 'cancel during response close'
owned client closed False
```

This is the cancellation counterpart of the exact same exception-safety requirement from the
previous review, not a request to suppress cancellation. It also matches this transport's existing
initial-request failure path, which attempts owned-client cleanup after catching `BaseException`
and then re-raises.

Narrow remediation:

1. keep `CancelledError` observable;
2. ensure owned-client close is attempted in a `finally`-equivalent path even if response close is
   cancelled;
3. define the guard/state so cancellation cannot mark unattempted cleanup as fully complete;
4. add a permanent owned-client cancellation witness and retain all ordinary-exception/status-
   outcome witnesses.

No shared Pi rule or certified lower layer needs changing. An idiomatic Rust implementation may
obtain this property through its own RAII/cancellation-safe cleanup mechanics.

## Other finding state

R023 and R024 remain provisionally closed and untouched. The corrected top-level
`JSON.stringify(Infinity) == "null"` rule remains valid.

## Fresh checks

```text
affected HTTP transport + OAuth suites
    120 passed

ruff
    PASS

mypy src/minion_agent tests/typing
    PASS; 75 source files
```

The candidate owner reports 1494 passed / 19 xfailed and 100% coverage for the full suite. The
targeted review stopped after the new production witness failed, as required by the convergence
loop.

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

Next action is the narrow cancellation-safe cleanup correction above, followed by another targeted
R022 closure review. One final complete section 11.8.8 review remains required afterward.
