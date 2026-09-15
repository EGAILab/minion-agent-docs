# Layer 11 Pass 2 Slice C — independent Rust contract review

## Exact review target

- Code PR `EGAILab/minion-agent#32`: `c5b925a918c3e5b8002bae5e990f5605d43c7a0a`
- Docs PR `EGAILab/minion-agent-docs#82`: `6acb561fddb5f1787371a7a494eaecd2dd3a6831`
- Code base: `bd61b4a8acf03755a336c4cef7f0aacbc2ad100f`
- Docs base: `46870f172d2e1f67b876d8da34421136a4780643`
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Coordination issue #29 named the same remote-reachable heads and `NEXT_OWNER = Codex`.

Both candidate PRs were open, Ready for Review, unmerged, and mergeable when review began. This
was a review-only pass. No candidate contract, Python, Rust, Slice-D, or Layer-12 work was changed.

## Authority and source audit

Reviewed in the required order: pinned Pi, manifest, normative spec, existing certified seams,
handoff, and implementation only where needed. Directly read in full or at the relevant symbols:

- `packages/ai/src/auth/oauth/openai-codex.ts` (all 544 lines);
- `packages/ai/src/auth/oauth/pkce.ts`;
- `packages/ai/src/auth/oauth/device-code.ts`;
- `packages/ai/src/utils/abort.ts`;
- `packages/ai/src/utils/provider-env.ts`;
- `packages/ai/test/openai-codex-oauth.test.ts`.

The proposed contract correctly captures the principal constants, URL construction, route-order,
limited `#` split, device poll mapping, form bodies, account projection reuse, and the distinction
between transport cancellation and `raceWithAbortSignal`. The following blockers remain.

## Findings

### L11-SC-R001 — `PI_PARITY_DEFECT` — browser cleanup overclaim

The contract says the manual prompt is cancelled, server closed, and flow abort listener detached
when the browser flow concludes by **any** success/error/cancellation path. Pinned Pi emits
`interaction.notify(auth_url)` at `openai-codex.ts:456-460` **before** entering the `try/finally` at
line 462. A synchronous `notify` throw therefore bypasses lines 501-504: the server is not closed,
the listener is not detached, and the manual abort controller is not aborted. This is especially
observable because PROV-014 correctly specifies that `notify` throws synchronously.

Required correction: state Pi's actual boundary and add a discriminating notification-failure
witness, or obtain and record owner approval for an intentional observable cleanup hardening. Do
not silently move `notify` under cleanup while calling the row adopted.

### L11-SC-R002 — `CONTRACT_ASSURANCE_DEFECT` — browser race/state matrix is incomplete

The source has additional discriminating outcomes not fixed by the current prose:

1. A manual prompt resolving first with `""` or whitespace still runs its `.then`, stores the
   value, and calls `server.cancelWait()` (`470-473`). The server is discarded; after the already
   completed manual promise is rechecked, the flow raises `"Missing authorization code"`. It does
   not continue waiting for a later server code.
2. Flow-signal abort calls only `server.cancelWait()` (`449-451`). If the manual prompt remains
   pending, Pi then awaits that prompt at line 490; `manualAbort.abort()` does not occur until the
   `finally`, so flow abort alone need not settle browser login promptly. The current text does not
   state this and can reasonably be implemented as prompt cancellation.
3. Manual state validation uses `if (parsed.state && parsed.state !== state)` (`485`, `494`). An
   empty parsed state (for example `code#`) bypasses validation; the contract's “state is present”
   wording can require a mismatch instead.

Required correction: extend the browser behavior matrix and permanent implementation witnesses to
cover empty/whitespace manual completion, flow abort while manual input remains pending, and empty
versus non-empty parsed state. Preserve which source is destructively cancelled and when.

### L11-SC-R003 — `PI_PARITY_DEFECT` — network JSON validation is stricter than Pi

The contract requires non-empty **strings** for `device_auth_id`, `user_code`,
`authorization_code`, `code_verifier`, `access_token`, and `refresh_token`. Pi's casts are erased at
runtime; its guards test only JavaScript truthiness for those fields (`219-224`, `254`, `138`). A
truthy number/object is accepted and forwarded. A direct Node witness also confirms that a
whitespace-only interval string becomes numeric zero via `Number(json.interval.trim())` and is
accepted; a host `float(trimmed)` implementation would reject it.

Required correction: specify and witness the actual runtime truthiness/ECMAScript-number-coercion
boundary, or obtain owner approval and separately disposition a stricter validation divergence.
Static TypeScript annotations are not runtime validation and cannot support the current rule.

### L11-SC-R004 — `CONTRACT_ASSURANCE_DEFECT` — failure surface is incomplete/inaccurate

- `startOpenAICodexDeviceAuth` and every device-token poll use `fetchWithLoginCancellation`
  (`192`, `241`), so they share exchange's cancellation translation: a request rejection observed
  while the signal is aborted becomes exactly `"Login cancelled"`; otherwise the transport error
  propagates unchanged. The contract assigns this rule only to “Exchange”.
- On a 2xx response, `response.json()` rejection occurs before each manual validation in device
  start, device poll, and token parsing (`211`, `252`, `132`). Pi propagates that parser rejection;
  it does not convert invalid JSON into the candidate's invalid/missing-field message. The contract
  does not pin this distinction.
- The explanation that refresh receives “a fixed time budget, not a user-driven cancellation” is
  inaccurate. Certified PROV-008 combines the caller signal **and** timeout. The observable rule
  (refresh wraps every request failure uniformly) is correct; its stated source rationale is not.

Required correction: enumerate request-rejection and JSON-parse-rejection behavior for all four
outbound surfaces (device start, device poll, exchange, refresh), and correct the CombinedSignal
description. Add discriminating fake-transport witnesses; no live network is needed.

## Contract-quality answers

- No canonical runner exists yet, so none currently simulates production behavior.
- The shared contract cannot yet drive independent Python/Rust implementations to one result for
  the cases above; two reasonable implementations can observably disagree.
- No certified PROV-008/009/010 semantic delta is required to correct these findings. They are
  Slice-C mapping/specification defects, not lower-layer incompatibilities.
- No `PI_BEHAVIOR_UNCERTAIN` remains: each blocker is resolved by direct pinned source.
- The contract-first structure is appropriate, but implementation must not begin until these
  source-grounded rules and witnesses are agreed.

## Fresh validation

At the exact code candidate:

- `uv run pytest tests/conformance/test_manifest_validation.py --no-cov -q`: 8 passed.
- `uv run ruff check .`: PASS.
- `uv run mypy src/minion_agent tests/typing`: PASS (72 source files).
- Manifest: 94 rows / 94 unique IDs.

These structural gates do not override the semantic blockers.

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

Remediation is contract/evidence-only and limited to L11-SC-R001 through R004. Do not begin Python
or Rust Slice-C implementation and do not start Layer 12. Any candidate SHA change requires a new
exact-SHA review.
