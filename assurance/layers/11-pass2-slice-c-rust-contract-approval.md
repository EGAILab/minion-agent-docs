# Layer 11 Pass 2 Slice C — independent Rust contract approval

## Exact approved target

- Code PR #32: `36484b9d0be025721239af840c6ebfa6e9f8dbfb`
- Docs PR #82: `1e3980bda81775870a0e5bdf2765a4b967722740`
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Prior review evidence: docs PRs #83 through #88, preserved as separate historical records.

Issue #29 recorded the same remote-reachable pair and `NEXT_OWNER = Codex`. Both candidate PRs
were open, Ready for Review, and unmerged when the review began. This was a complete §11.8.8
review-only pass; no Python, Rust, Slice-D, or Layer-12 implementation was performed.

## Independent audit

Re-read pinned Pi's complete Codex OAuth network surface before the candidate claims:

- `packages/ai/src/auth/oauth/openai-codex.ts`;
- `packages/ai/src/auth/oauth/device-code.ts` and `pkce.ts`;
- `packages/ai/src/utils/abort.ts` and `provider-env.ts`;
- pinned Codex OAuth tests.

Then reviewed the full manifest and normative `PROV-012`/`PROV-016` contract, certified auth
dependencies, all prior findings, the convergence checkpoints, and Rust implementability.

## Finding closure

| Finding | Final result |
|---|---|
| `L11-SC-R001` | CLOSED — auth-URL notification/cleanup boundary is Pi-accurate. |
| `L11-SC-R002` | CLOSED — browser race and state-validation matrix is complete. |
| `L11-SC-R003` | CLOSED — Pi's runtime baseline is accurate; six-field exception separately governed. |
| `L11-SC-R004` | CLOSED — cancellation, parse, and outbound failure surfaces are complete. |
| `L11-SC-R005` | CLOSED — owner-approved Option A is traceable and isolated in `PROV-016`. |
| `L11-SC-R006` | CLOSED — exact input/missing/error shapes are pinned. |
| `L11-SC-R007` | CLOSED — absent and empty callback codes both return 400. |
| `L11-SC-R008` | CLOSED — callback content type and exception-to-500 containment are pinned. |
| `L11-SC-R009` | CLOSED — pre-aborted browser-flow ordering is explicit. |
| `L11-SC-R010` | CLOSED — exact templates use ECMAScript `JSON.stringify` as the complete normative authority; Unicode/lone-surrogate, negative-zero, number-notation, and property-order witnesses are correctly constrained without claiming the prose examples replace the standard. |

No active `PI_PARITY_DEFECT`, `CONTRACT_ASSURANCE_DEFECT`, or `PI_BEHAVIOR_UNCERTAIN` remains.
The single intentional divergence (`PROV-016`) has explicit owner provenance, exact scope, Pi
baseline, rationale, and future cross-language evidence obligations.

## Contract quality and Rust feasibility

- No runner or placeholder is counted as implementation evidence; `PROV-012` remains
  `deferred parity` until implementation.
- The browser callback, manual race, device flow, token exchange/refresh, cancellation, exact
  failures, and `JSON.stringify` rendering are language-neutral and unambiguous.
- Existing certified credential, interaction, signal, PKCE, and device-poll seams are sufficient;
  no lower-layer reopen is required.
- Rust can implement the contract idiomatically with typed response decoding, an explicit
  ECMAScript-compatible error renderer, deterministic fake transport/server evidence, and no
  Python-specific mechanism.
- Python and Rust cannot make different observable choices while both satisfying the current
  written contract on the audited surface.

## Fresh gates

- `uv run pytest -q`: **1337 passed, 19 xfailed, 0 failed**, **100.00%** coverage.
- `uv run pytest tests/conformance/test_manifest_validation.py --no-cov -q`: **8 passed**.
- `uv run ruff check .`: PASS.
- `uv run mypy src/minion_agent tests/typing`: PASS (72 source files).
- Manifest: 95 rows / 95 unique IDs.
- Candidate diffs pass `git diff --check`.

## Verdict

```text
Layer 11 Pass 2 Slice C shared contract
    APPROVED FOR IMPLEMENTATION

Python Slice C
    NOT_IMPLEMENTED

Rust Slice C
    NOT_IMPLEMENTED

Layer 11 Pass 2
    NOT CLOSED

Layer 12
    NOT STARTED
```

Approval applies only to the exact candidate SHAs above. The next action is a separate Python
Slice-C implementation pass against the merged approved contract. Rust implementation and Layer 12
must not begin in this review pass.
