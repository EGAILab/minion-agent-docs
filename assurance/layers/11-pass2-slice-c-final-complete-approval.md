# Layer 11 Pass 2 Slice C — final complete independent Rust contract review

## Verdict

`APPROVED FOR RUST IMPLEMENTATION`

This approval is exact-SHA-bound to:

```text
minion-agent PR #33
    a51bfcd8e34be0c9d0b72f935321ffb50804a5f0

minion-agent-docs PR #92
    c04f00a6309336fc697c41a2aa4d622599792370

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

The reviewed candidates were remote-reachable, Ready for Review, cleanly mergeable, and unmerged when this review began. Issue `EGAILab/minion-agent#29` was open with `STATUS = RUST_CONTRACT_REVIEW`, `NEXT_OWNER = Codex`, and one final complete §11.8.8 review as its next action. Neither candidate derives from a quarantined artifact.

This approval authorizes a separate Rust Slice-C implementation pass after the shared/Python candidates are merged. It does not certify Rust Slice C and does not start Layer 12.

## Review lineage

The complete Slice-C review history was preserved in review PRs `#90` through `#104`. The last targeted review, docs PR `#104` at `455ed86c36bc7fdcc5265a4aabb2373206aae9c7`, provisionally closed `L11-SC-R027` at the exact candidate above. `L11-SC-R025` had already been provisionally closed by docs PR `#103`. This review did not rely on provisional closure as final certification: it re-audited the complete Slice-C surface and reran the complete gates.

## Authority and source audit

The review used the required order:

1. pinned Pi;
2. normative spec;
3. parity manifest;
4. canonical/shared evidence;
5. certified Rust architecture;
6. assurance/handoff;
7. Python implementation as secondary implementation evidence.

Pinned Pi source inspected included the complete relevant `packages/ai/src/auth/oauth/openai-codex.ts` flow, especially:

- `parseAuthorizationInput`;
- `fetchWithLoginCancellation`;
- `readTokenResponse`;
- authorization-code exchange and refresh;
- local callback-server construction and route handling;
- browser/manual-code race behavior;
- device-code start and poll mapping;
- `loginOpenAICodexDeviceCode` and `loginOpenAICodex`.

Related adopted auth vocabulary, signal, PKCE, device-code, and credential seams were checked where Slice C consumes them. No Pi behavior remained uncertain.

## Complete semantic audit

The final candidate accounts for the complete approved Slice-C surface:

- browser/PKCE authorization URL construction and `auth_url` notification ordering;
- local callback-server bind behavior, route table, shared headers, contained handler failure, state validation, and success/error pages;
- the server/manual-input race, including pre-abort, empty input, cancellation, and cleanup ordering;
- WHATWG URL construction, USVString conversion, and URLSearchParams behavior, including exactly one leading `?`, present-empty values, and double-`?` data;
- device-code start and polling status/error mapping, interval coercion, cancellation, timeout, and abandoned-response cleanup;
- code exchange and token refresh request shapes and asymmetric cancellation behavior;
- the separation between response-status availability and lazy body consumption;
- successful-response body-read failure propagation versus non-success fallback behavior;
- UTF-8 BOM stripping and response reason-phrase behavior;
- ECMAScript JSON parsing/stringification constraints needed by exact error messages, including property order, IEEE-754 number behavior, non-finite rendering, surrogate handling, and invalid constant rejection;
- no browser-launch ownership creep and no generic PROV-013 orchestration implementation.

`PROV-012` is coherently `adopted`. `PROV-016` separately records the owner-approved intentional divergence that requires actual strings for exactly six provider-response fields. Its governance source and exact scope are durable and do not leak into other auth or JSON boundaries. The manifest contains 95 rows and 95 unique IDs.

The complete implementation diff contains no `minion-agent-rust/**` change.

## Finding closure

All known findings `L11-SC-R001` through `L11-SC-R028` are closed for the reviewed exact candidate.

The last evidence-only gaps were rechecked directly:

- `L11-SC-R025`: removing pre-response owned-client cleanup makes the strengthened close-attempt witnesses fail while the original request failure remains the observable outcome;
- `L11-SC-R027`: reverting the one-leading-`?` normalization makes both non-empty and present-empty leading-`?` witnesses fail, while the double-`?` boundary remains distinct;
- `L11-SC-R026`: current normative prose identifies the implemented Python state accurately;
- `L11-SC-R028`: the fake transport records and asserts URL, copied headers, body semantics, and signal-facing request ownership rather than URL alone.

No new finding was opened.

```text
PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    none

CONTRACT_ASSURANCE_DEFECT
    none

PARITY_CONSTRAINED_RISK
    none

unapproved observable divergence
    none
```

## Contract-quality and Rust implementability

The shared contract describes observable behavior rather than Python mechanics. The injectable transport seam preserves Pi's two-phase status/body behavior without making `httpx` normative. The callback server, browser/manual race, cancellation, JSON/URL behavior, and resource-lifecycle obligations are stated in language-neutral terms. The canonical/test adapters do not simulate the production semantics they claim to prove.

An independent Rust implementation can use Rust-native URL, HTTP, task-race, cancellation, listener, and disposal mechanisms while preserving the contract. It does not need to consult Python control flow or introduce a Rust-only semantic rule. Existing certified Rust auth foundation types provide the required lower-layer vocabulary; no lower-layer reopen is required.

## Fresh gates

Executed against code candidate `a51bfcd8e34be0c9d0b72f935321ffb50804a5f0`:

```text
uv run pytest -q
    PASS — 1,504 passed, 19 expected xfailed
    3,880 statements, 100.00% coverage

uv run pytest -q --no-cov
    PASS

uv run pytest -W error::ResourceWarning tests/auth -q --no-cov
    PASS — 317 auth tests, no ResourceWarning

uv run ruff check .
    PASS

uv run mypy src/minion_agent tests/typing
    PASS — 75 source files

uv run pytest tests/test_layering.py \
  tests/conformance/test_manifest_validation.py \
  tests/conformance/test_schema_validation.py -q --no-cov
    PASS — 218 tests

manifest parse
    PASS — 95 rows, 95 unique IDs

uv run ruff format --check .
    expected baseline result — the same seven pre-existing drift files;
    no Slice-C candidate file is among them
```

The full collection contains 1,523 cases: 1,504 passing and 19 established Layer-08 placeholder xfails. No Slice-C scenario is counted through an unfilled placeholder.

## Lower-layer impact

```text
PROV-008 refresh authority
    semantic delta required: NO

PROV-009 PKCE
    semantic delta required: NO

PROV-010 generic device-code poller
    semantic delta required: NO
    the already-approved Abortable type widening remains behavior-preserving

PROV-014 / PROV-015 interaction vocabulary
    semantic delta required: NO

Layer 12
    started: NO
```

## Formal status

```text
shared Layer-11 Pass-2 Slice-C contract
    APPROVED FOR RUST IMPLEMENTATION

Python Slice C
    CERTIFIED at the reviewed exact candidate after merge

Rust Slice C
    NOT_IMPLEMENTED

Layer 11 Pass 2 cross-language
    NOT CLOSED

Layer 12
    NOT STARTED
```

## Next action

Merge the exact approved shared/Python candidates under the exact-SHA gate, preserve the historical review evidence on the default branch, update issue `#29` to `STATUS = RUST_IMPLEMENTATION` and `NEXT_OWNER = Codex`, then stop. Rust Slice-C implementation must be a separate pass.
