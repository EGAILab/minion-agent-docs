# Layer 11 Pass 2 Slice C — third mandatory final-complete Rust review

## Exact review target

```text
code PR #33
    f5555f23421f014fcc79580bc746053d994dd00f

docs PR #92
    c04f00a6309336fc697c41a2aa4d622599792370

code base main
    ea3b64caca84e95245fa0d5f2a1a650452686649

docs base master
    1e3c224ed7912d51fa28f33563622e5155947cda

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699

previous complete review evidence
    minion-agent-docs PR #101
    a28cf30c9ed28d2d71a034e91ebcb1a015b3bbe9
```

Both candidate heads were fetched from GitHub immediately before review and matched issue #29.
Both PRs were open, Ready for Review, unmerged, and remote-reachable. Issue #29 was open with
`STATUS: RUST_CONTRACT_REVIEW`, `NEXT_OWNER: Codex`, and a request for a new complete section
11.8.8 review. The handoff is valid and neither candidate derives from a quarantined artifact.

This was review mode only. No candidate/shared/Python/Rust file, Layer 12 work, or prior review
artifact was modified.

## Independent whole-surface audit

The review re-read pinned Pi first, especially `packages/ai/src/auth/oauth/openai-codex.ts`:
`parseAuthorizationInput`, `fetchWithLoginCancellation`, browser callback/race handling, device
start/poll, exchange, `readTokenResponse`, and refresh. It then audited the current `PROV-012` and
`PROV-016` manifest/spec contract, complete evidence inventory, lower-layer seams, and only then
the Python implementation.

The full prior `L11-SC-R001` through `L11-SC-R024` ledger remains closed/provisionally closed. No
new Pi mismatch was found elsewhere in the browser flow, callback server, device flow, token
response, lazy HTTP body, JSON, cancellation, or approved six-field-divergence surfaces. The four
findings returned by the previous complete review were audited individually below.

## Finding closure ledger

### L11-SC-R025 — `PARTIALLY_RESOLVED_BLOCKING`

The production correction is semantically correct: an ordinary owned-client `aclose()` failure is
suppressed, so it no longer replaces the original pre-response request failure. Cancellation is
still not silently suppressed.

The required permanent evidence is not discriminating, however. The remediation deleted the only
assertion in
`test_httpx_transport_closes_owned_client_when_getting_the_response_itself_fails` that checked
`created[0].is_closed`. The new
`test_httpx_transport_owned_client_close_failure_does_not_replace_request_failure` asserts only the
original `ConnectionError`; it does not record/assert that `aclose()` ran.

Executable mutation witness, run against a detached worktree of the exact candidate:

```text
mutation
    delete the entire pre-response `if owns_client: await client.aclose()` cleanup block

tests run
    test_httpx_transport_closes_owned_client_when_getting_the_response_itself_fails
    test_httpx_transport_owned_client_close_failure_does_not_replace_request_failure

candidate evidence result
    2 passed
```

Thus both purported cleanup witnesses pass an implementation that never attempts cleanup at all.
This is an active `CONTRACT_ASSURANCE_DEFECT` refinement of R025, not a remaining production parity
error.

Minimal closure criterion:

```text
pre-response failure + successful owned close
    original failure observable
    owned close attempted exactly once

pre-response failure + ordinary owned-close failure
    original failure observable
    owned close attempted exactly once
```

Restoring the removed `is_closed` assertion and adding an explicit close-attempt flag/count to the
raising-close witness are sufficient; production code need not change if those witnesses pass.

### L11-SC-R026 — `RESOLVED`

The two stale current-state sentences in `spec/auth.md` now accurately state that Python exists,
`PROV-012` is adopted, Rust is not implemented, and the spec remains language-neutral authority.
Historical assurance/manifest chronology remains clearly historical and was not rewritten.

### L11-SC-R027 — `PARTIALLY_RESOLVED_BLOCKING`

The production correction is semantically correct and was independently compared with Node:
exactly one leading `?` is removed before bare-query parsing, while a second leading `?` remains
ordinary key data.

But the permanent witnesses explicitly required by the prior review do not exist. The test file
still contains only the old no-prefix case `code=abc&state=xyz`; there is no test for
`?code=abc&state=xyz`, `?code=`, or the one-leading-character boundary. The manifest nevertheless
claims that a permanent `parse_authorization_input("?code=abc&state=xyz")` witness exists.

Executable mutation witness, run against a detached worktree of the exact candidate:

```text
mutation
    revert the production branch to `parse_qs(value, keep_blank_values=True)`

tests run
    every existing `parse_authorization_input` test

candidate evidence result
    14 passed
```

The evidence therefore cannot detect reintroduction of the exact Pi mismatch, and the manifest
evidence pointer is factually false. This is an active `CONTRACT_ASSURANCE_DEFECT` refinement of
R027.

Minimal closure criterion: add permanent discriminating cases for at least:

```text
?code=abc&state=xyz
    code="abc", state="xyz"

?code=&state=xyz
    code="", state="xyz"

??code=abc&state=xyz
    code absent, state="xyz"   # exactly one leading `?` stripped
```

The reverted production implementation above must fail the new witness set.

### L11-SC-R028 — `RESOLVED`

The fake transport now snapshots URL, headers, body, and signal. Four real-seam tests separately
exercise device start, device poll, authorization-code exchange, and refresh, asserting exact
endpoint/content type and semantically decoded JSON/form fields. This closes the original
non-discriminating URL-only evidence gap without overclaiming raw percent-encoding equality.

## Contract-quality result

- The shared semantic rules are independently implementable in Rust once the evidence gate closes.
- No lower-layer semantic reopen is required.
- No runner simulates Slice-C production behavior.
- No `PI_BEHAVIOR_UNCERTAIN` or newly discovered production `PI_PARITY_DEFECT` remains.
- Certification still cannot proceed while the manifest claims a nonexistent witness and the
  cleanup tests pass a mutation that removes cleanup entirely.

R025 and R027 now appear in a second independent review after remediation and remain open. The
workflow section 11.8 convergence trigger therefore applies even though the remaining work is
narrow evidence completion rather than a semantic disagreement. The acceptance matrix above is
the reviewer's proposed characterization. The implementation owner should record agreement, add
the exact witnesses in one coherent pass, and return the changed exact SHAs for targeted closure
under section 11.8.7; a successful targeted closure must still be followed by one final complete
section 11.8.8 review.

## Fresh gates

Green gates do not override the evidence defects:

```text
uv run pytest -q / uv run pytest -q --no-cov
    PASS
    1501 passed, 19 xfailed, 0 failed
    100.00% coverage; 3880 statements / 0 missed

uv run pytest --collect-only -q --no-cov
    1520 tests collected

uv run pytest -W error::ResourceWarning tests/auth -q --no-cov
    PASS; 314 auth tests

uv run ruff check .
    PASS

uv run mypy src/minion_agent tests/typing
    PASS; 75 source files

layering + manifest validation + schema validation
    PASS; 218 tests

uv run ruff format --check .
    known pre-existing baseline only: 7 files would be reformatted

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

active CONTRACT_ASSURANCE_DEFECT
    L11-SC-R025 (evidence refinement)
    L11-SC-R027 (evidence refinement)

active PI_PARITY_DEFECT
    none in the current production code

PI_BEHAVIOR_UNCERTAIN
    none
```

Next action: enter the narrow R025/R027 convergence checkpoint using the explicit acceptance
matrix above. Do not implement Rust Slice C and do not start Layer 12.
