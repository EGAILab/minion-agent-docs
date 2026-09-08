# Layer 09 PASS 3 — targeted independent Rust finding-closure review

**Verdict:** TARGETED FINDINGS PROVISIONALLY CLOSED. L09-R001, L09-R004, and L09-R006 are
resolved at the exact PASS-3 candidate SHAs below. Together with the previously provisionally
closed findings, the convergence ledger has no active blocker. Per `agent-workflow.md` section
11.8.8, this is not yet approval for Rust implementation: exactly one final complete exact-SHA
contract review is required next.

## Exact reviewed state

- code PR: `EGAILab/minion-agent#17`
- exact code head: `ffecd2f9860dc4edd1d605f22ad571f5b36f66c5`
- docs PR: `EGAILab/minion-agent-docs#26`
- exact docs head: `7dde9ad3e4596e1d1fb64207de62f7bff00eace1`
- PASS-2 rejected code head: `ee24b8d03bdd4ed26e22356165fe4809be07ec05`
- PASS-2 rejected docs head: `5474cf1fdea345438920500a55f9f7032ff16cdc`
- PASS-2 targeted review: docs PR #28 / commit
  `9a8b9632f78a7bf0ba398f9ba4cc314981bdb8d4`
- PASS-1 full review: docs PR #27 / commit
  `0a781d3f6710d633f9fcf4c10ef11422dfeef1ee`
- accepted shared baseline: code `3ec1a386c86a93a13344ed38d796fbb74e9817bd`, docs
  `ecb809798b7437045e1325683306c3f15f46571e`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- coordination issue: `EGAILab/minion-agent#16`, received as `RUST_CONTRACT_REVIEW`,
  `NEXT_OWNER = Codex`

Both candidate heads were fetched, remote-reachable, matched issue #16, Ready for Review, and
open/unmerged. Candidate branches were not modified. Existing untracked `.worktrees/` were
preserved.

## Review scope and authority

This is the section 11.8.7 targeted closure review requested by issue #16. The authority order was
pinned Pi, normative spec, manifest, conformance, certified Rust architecture, assurance, and
Python implementation last. The following Pi surfaces were rechecked:

- `agent.ts`: private `AbortController`, public read-only `Agent.signal`, `Agent.abort`,
  failure classification, and listener signal delivery;
- `agent-loop.ts`: `transformContext`, before/after hook delivery, preflight polls, and sequential
  versus parallel batch boundaries;
- `types.ts`: callback and tool execute signal shapes.

The targeted implementation review covered all three changed waterfall seams, direct replacement
and omission attacks, semantic payload preservation, the previously provisionally closed
C001/C002/R002/R003/R005 witnesses, and lower-layer isolation.

## Targeted closure ledger

### L09-R001 — before/after hook signal delivery

`TOOLS_PRE_EXECUTE` and `TOOLS_POST_EXECUTE` still supply the exact active signal to the first
listener. PASS 3 now also uses event-specific `normalize_step` closures to restore the original
signal before every later listener. A raw listener may still transform the hook-owned semantic
payload, but cannot redirect or drop signal metadata.

Independent reproduction against the exact code head:

```text
tools/pre-execute replace original=True forged=False error=False
tools/pre-execute drop    original=True forged=False error=False
tools/post-execute replace original=True forged=False error=False
tools/post-execute drop    original=True forged=False error=False
```

The helper-registered after-hook continues to compose with a later raw listener and preserves both
the helper's result override and original signal identity.

**Status:** `PROVISIONALLY CLOSED @ ffecd2f9860dc4edd1d605f22ad571f5b36f66c5 / 7dde9ad3e4596e1d1fb64207de62f7bff00eace1`.

### L09-R004 — signal authority and identity

The PASS-2 public-controller split remains intact: consumers receive a read-only `RunSignal`,
`AgentInstance.signal` is not assignable, and only the private active controller is mutated by
`AgentInstance.abort()`. PASS 3 closes the residual authority path: raw middleware can no longer
substitute a different signal for downstream consumers at any of the affected seams.

The normalization is dispatch-local and captures the authoritative original value. It does not
change generic EventBus behavior or grant the listener mutation authority over that value.

**Status:** `PROVISIONALLY CLOSED @ ffecd2f9860dc4edd1d605f22ad571f5b36f66c5 / 7dde9ad3e4596e1d1fb64207de62f7bff00eace1`.

### L09-R006 — authoritative signal metadata across waterfall boundaries

The exact PASS-2 blocker is resolved at all three seams:

- `_preflight._restore_signal` preserves listener-owned call/definition/arguments positions and
  restores the original signal at position four;
- `_finalize._restore` continues restoring protected Layer-06 result identity while now also
  restoring the original signal at position two;
- `_transform_context._restore_signal` restores the original instance and signal while retaining
  the listener-transformed messages.

Independent transform-context reproduction covered both a forged replacement and omission:

```text
transform-context replace original=True forged=False messages=1
transform-context drop    original=True forged=False messages=1
```

The normative `spec/tools.md`, `spec/agent.md`, `AG-007`, `AG-023`, and `TOOL-024` text now agree:
signal is authoritative metadata and callers do not need to re-supply it. The old permitted
“degrade to no signal” statement is gone.

**Status:** `PROVISIONALLY CLOSED @ ffecd2f9860dc4edd1d605f22ad571f5b36f66c5 / 7dde9ad3e4596e1d1fb64207de62f7bff00eace1`.

## Previously closed finding regression

- **L09-C001:** sequential and parallel batch algorithms remain distinct; A/B/C behavior and
  inter-call polling tests pass.
- **L09-C002:** unknown/prepare/validation/hook-throw priority remains ahead of abort; abort after
  a returning hook still beats block/proceed.
- **L09-R002:** recovery still reads live aborted state; aborted and non-aborted exception
  classification tests pass.
- **L09-R003:** none, update-only, signal-only, and signal-plus-update tool capabilities remain
  independently representable.
- **L09-R005:** transform-context remains per-request and provider-local, never persistent; its
  signal metadata is now authoritative for every listener.

No new witness reopened these findings.

## Lower-layer and Rust feasibility

The correction is an opt-in normalization at the three Layer-09 dispatches. It does not change
Runtime's default waterfall semantics or any non-cancelled Layer-06 ordering/result behavior. Rust
can implement the language-neutral rule idiomatically by keeping the read-only signal handle
outside listener-transformable state or restoring it at each typed listener boundary. No lower
certified semantic contract must reopen.

The three Layer-09 canonical files remain placeholders and are not counted as executable evidence.
Permanent Python language tests are therefore the current evidence for these listener-driven
witnesses; the final complete review must retain that limitation explicitly.

## Fresh evidence

```text
focused tools/batch/agent-loop tests
    69 passed, 0 failed

independent replacement/omission probes
    pre-execute, post-execute, transform-context: all preserve original signal

full Python suite
    1089 passed, 19 xfailed, 0 failed

coverage
    100.00% (2791/2791 statements)

ruff
    PASS

mypy src
    PASS (58 source files)

manifest
    79 rows / 79 unique IDs
```

## Finding status and verdict

```text
L09-C001    PROVISIONALLY CLOSED
L09-C002    PROVISIONALLY CLOSED
L09-C003    PROVISIONALLY CLOSED
L09-R001    PROVISIONALLY CLOSED
L09-R002    PROVISIONALLY CLOSED
L09-R003    PROVISIONALLY CLOSED
L09-R004    PROVISIONALLY CLOSED
L09-R005    PROVISIONALLY CLOSED
L09-R006    PROVISIONALLY CLOSED

PI_BEHAVIOR_UNCERTAIN
    none in targeted scope

PI_PARITY_DEFECT
    none in targeted scope

CONTRACT_ASSURANCE_DEFECT
    none in targeted scope

PARITY_CONSTRAINED_RISK
    none blocking

shared Layer-09 contract
    TARGETED FINDINGS PROVISIONALLY CLOSED
    READY FOR ONE FINAL COMPLETE EXACT-SHA REVIEW

Python Layer 09
    candidate self-certified; final independent review pending

Rust Layer 09
    NOT_IMPLEMENTED

Layer 09 cross-language
    NOT CLOSED

Layer 10
    NOT STARTED
```

Next action: perform exactly one final complete independent Layer-09 contract review of code
`ffecd2f9860dc4edd1d605f22ad571f5b36f66c5` and docs
`7dde9ad3e4596e1d1fb64207de62f7bff00eace1` under workflow section 11.8.8. Do not begin Rust
implementation unless that review approves these exact SHAs. Any candidate movement invalidates
this closure and requires review of the new exact heads.
