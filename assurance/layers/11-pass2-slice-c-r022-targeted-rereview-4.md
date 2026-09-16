# Layer 11 Pass 2 Slice C — L11-SC-R022 targeted re-review 4

## Exact target

```text
code PR #33
    f225596f8fba1debac4a116f5d73203bbd503097

docs PR #92
    f55dd808593415bc0d94487bf3f28ea21745202c

base main
    ea3b64caca84e95245fa28f33563622e5155947cda

base docs master
    1e3c224ed7912d51fa28f33563622e5155947cda

prior targeted review
    minion-agent-docs PR #99
    73cae8defca0df8897b04f6d7b5e2249cc188531

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

The exact heads were fetched from GitHub and matched issue #29. Both candidate PRs were open,
Ready for Review, unmerged, and remote-reachable. Issue #29 was open with
`STATUS: CONTRACT_CONVERGENCE`, `NEXT_OWNER: Codex`, and requested this narrow R022 review. The
candidate is not derived from a quarantined artifact. No candidate/shared/Python/Rust file and no
Layer 12 work was modified by this review.

## Review scope and source basis

This review followed `agent-workflow.md` §11.8.7. It rechecked the one open finding, the shared
cleanup helper changed by the remediation, and the previously-closed R022 exception/status
dependencies. Pinned Pi remains the semantic authority: the status-only device-start and
device-poll branches do not expose a new cleanup failure outcome. Cancellation remains observable;
the Minion transport must nevertheless attempt all resources it owns before propagation completes.

The candidate changed the shared cleanup helper from two sequential close blocks to a genuine
`try/finally`: response close remains inside `suppress(Exception)`, while owned-client close runs
in `finally`. Because `asyncio.CancelledError` is not an `Exception`, it is not swallowed, but the
owned-client close is reached before it resumes propagating.

## L11-SC-R022 — PROVISIONALLY CLOSED

The exact third-review witness now passes through both the direct `HttpResponse.discard()` seam
and the real device-start status-only seam:

```text
setup
    HttpxTransport owns its AsyncClient
    response status is 404
    response aclose() raises asyncio.CancelledError

observed
    asyncio.CancelledError propagates
    owned-client close is attempted first
    owned client is closed
```

This is discriminating against the rejected `931dc4f` candidate, where cancellation exited before
the client close. The change also preserves the earlier requirements:

- ordinary response-close failures remain suppressed and cannot replace the fixed Pi outcome;
- an ordinary response-close failure cannot skip owned-client cleanup;
- injected clients are not closed by the transport;
- status-only branches do not read abandoned bodies;
- repeated device polling closes every abandoned response;
- successful body reads and `discard()` share one idempotent close path.

The helper marks the cleanup path consumed before awaiting, so concurrent or repeated calls remain
one-shot. A cancellation or failure from the owned-client close itself may prevent that close from
finishing, but the required independent attempt has occurred; this review does not demand an
unbounded shield/retry mechanism absent from the adopted contract.

No normative shared-contract delta or lower-layer reopen is required. Rust may satisfy the same
observable resource-ownership rule using idiomatic RAII/cancellation-safe mechanics rather than
copying Python's control flow.

## Other finding state

```text
L11-SC-R023
    PROVISIONALLY CLOSED (unchanged)

L11-SC-R024
    PROVISIONALLY CLOSED (unchanged)
```

All currently known Slice C blockers are therefore provisionally closed at this exact candidate.
This targeted result is not final Slice C approval.

## Fresh checks

```text
affected HTTP transport + OAuth suites
    122 passed (`--no-cov`; production target files are covered by the candidate's full gate)

ruff
    PASS

mypy
    PASS; 71 source files

manifest validation
    8 passed (`--no-cov`)
```

The candidate owner reports the complete gate as 1496 passed / 19 pre-existing xfailed / 0 failed,
100% coverage, no `ResourceWarning`, and clean ruff/mypy. This targeted review independently reran
the affected suites and static/manifest gates; the mandatory final complete review must rerun the
full release-level evidence against the unchanged exact SHA pair.

## Verdict

```text
L11-SC-R022
    PROVISIONALLY CLOSED @ f225596f8fba1debac4a116f5d73203bbd503097

L11-SC-R023
    PROVISIONALLY CLOSED

L11-SC-R024
    PROVISIONALLY CLOSED

Layer 11 Pass 2 Slice C
    ALL KNOWN FINDINGS PROVISIONALLY CLOSED
    NOT YET APPROVED / NOT MERGED

Rust Slice C
    NOT_IMPLEMENTED / BLOCKED PENDING FINAL CONTRACT APPROVAL

Layer 12
    NOT STARTED
```

Per `agent-workflow.md` §11.8.8, the next and only next action is one complete independent review
of this exact remote code/docs SHA pair. This review does not authorize merging the candidate,
starting Rust Slice C, or starting Layer 12.
