# Layer 11 Pass 2 Slice C — final complete Rust contract review

## Exact review target

- Code PR `EGAILab/minion-agent#32`:
  `a30a8406a51ba7a60f5fb1b6879613f23f69a30a`
- Docs PR `EGAILab/minion-agent-docs#82`:
  `b01be45378aa0a02ba16359785489ae5752287b5`
- Code base: `bd61b4a8acf03755a336c4cef7f0aacbc2ad100f`
- Docs base: `46870f172d2e1f67b876d8da34421136a4780643`
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Prior reviews: docs PR #83 at
  `3b4f35495670349d7495c0eda92e8ab18d28ba64`, docs PR #84 at
  `a68c4b60f5bec2fd2d4c9f9c1f2b8233bd20c7dc`, and docs PR #85 at
  `775f571cc0ee5323a1a713a3c3bfdfd0a826ac7b`.

Issue #29 recorded the same candidate pair, `STATUS = RUST_CONTRACT_REVIEW`, and
`NEXT_OWNER = Codex`. Both candidate PRs were open, Ready for Review, unmerged, and
remote-reachable. This was a complete §11.8.8 review-only pass. No shared, Python, Rust, Slice-D,
or Layer-12 implementation was changed.

## Independent source audit

Re-read pinned Pi before the candidate claims, including all of
`packages/ai/src/auth/oauth/openai-codex.ts`, `oauth/device-code.ts`, `oauth/pkce.ts`,
`utils/abort.ts`, `utils/provider-env.ts`, and the pinned Codex OAuth tests. Then reviewed the
manifest, full normative `PROV-012`/`PROV-016` spec, certified auth dependencies, assurance, and
handoff.

## Finding ledger

| Finding | Independent result | Status |
|---|---|---|
| `L11-SC-R001` | Auth-URL notification correctly remains before the cleanup boundary. | CLOSED |
| `L11-SC-R002` | Browser race/state matrix remains correct. | CLOSED |
| `L11-SC-R003` | Pi baseline remains accurately characterized; the six-field exception is separately governed by `PROV-016`. | CLOSED / SUPERSEDED FOR THE SIX FIELDS |
| `L11-SC-R004` | Outbound cancellation, parse, and failure distinctions remain correct. | CLOSED |
| `L11-SC-R005` | Owner-approved Option A remains narrow, traceable, and internally coherent. | CLOSED |
| `L11-SC-R006` | Exact select, method-error, callback-host, and device-start status-error shapes remain pinned. | CLOSED |
| `L11-SC-R007` | Callback `code` now rejects both absent and empty values, preserving state-before-code order. | CLOSED |
| `L11-SC-R008` | Common content type and whole-handler exception-to-500 containment are now explicit. | CLOSED |
| `L11-SC-R009` | Pre-aborted browser flow now cancels only the server source and still notifies/prompts in Pi order. | CLOSED |

The agreed convergence matrix for R007-R009 is complete and requires no lower-layer reopen.

## New finding

### L11-SC-R010 — `CONTRACT_ASSURANCE_DEFECT` — parsed-response error serialization is not pinned

Three public failure paths interpolate the parsed JSON value through JavaScript
`JSON.stringify`, with distinct exact prefixes in pinned Pi:

```text
Invalid OpenAI Codex device code response: ${JSON.stringify(json)}
Invalid OpenAI Codex device auth token response: ${JSON.stringify(json)}
OpenAI Codex token ${operation} response missing fields: ${JSON.stringify(json)}
```

The current contract never states the first exact template, abbreviates the second as
`"Invalid ... token response: <body>"`, and states the third as `{the parsed body}` without defining
its rendering. That is insufficient for independent implementation: Python's ordinary object
stringification, Python `json.dumps`, compact JSON, and Rust `serde_json::Value` formatting can
differ in quoting, whitespace, key ordering, booleans, and null spelling while each could plausibly
be called “the parsed body.” The difference is especially reachable through `PROV-016`'s required
truthy-non-string rejection witnesses.

Minimal correction:

1. pin all three complete prefixes/templates above;
2. state that the suffix is the ECMAScript `JSON.stringify` serialization of the successfully
   parsed JSON value, not the original response bytes and not a host-language debug representation;
3. require discriminating future witnesses covering at least `null`, an array, and a multi-field
   object whose compact quoting/separators and property order distinguish host representations.

No certified lower-layer change is required. This is a bounded `PROV-012` documentary/evidence
correction.

## Contract quality and Rust feasibility

- No canonical runner simulates Slice-C behavior; implementation has not started.
- Existing PKCE, device-poll, signal, credential, and interaction seams remain sufficient.
- R001-R009 and `PROV-016` are independently implementable in typed Rust.
- R010 still allows Python and Rust to emit observably different public error messages under the
  same written rule. Rust must not guess a Python mechanism or silently choose its own renderer.
- There is no `PI_BEHAVIOR_UNCERTAIN`; pinned source supplies the exact templates and renderer.

Because the slice is already in convergence, R010 remains on that convergence track. The table
above is the source-derived characterization; the shared owner should challenge it and amend the
agreed checkpoint before applying the narrow documentary correction.

## Fresh gates

At the exact candidate:

- `uv run pytest -q`: **1337 passed, 19 xfailed, 0 failed**, **100.00%** coverage.
- `uv run pytest tests/conformance/test_manifest_validation.py --no-cov -q`: **8 passed**.
- `uv run ruff check .`: PASS.
- `uv run mypy src/minion_agent tests/typing`: PASS (72 source files).
- Manifest: 95 rows / 95 unique IDs.

These green structural/lower-layer gates do not resolve R010.

## Verdict

```text
Layer 11 Pass 2 Slice C shared contract
    REJECTED

Python Slice C
    NOT_IMPLEMENTED / BLOCKED

Rust Slice C
    NOT_IMPLEMENTED / BLOCKED

Layer 11 Pass 2
    NOT CLOSED

Layer 12
    NOT STARTED
```

R001-R009 are closed at this exact candidate. Challenge and remediate only R010 through the active
convergence protocol, then request another complete exact-SHA review. Do not begin Slice-C
implementation or Layer 12.
