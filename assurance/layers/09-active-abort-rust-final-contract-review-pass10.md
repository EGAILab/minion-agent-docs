# Layer 09 active abort — final independent Rust contract review (PASS 10)

## Exact target and verdict

**APPROVED FOR RUST IMPLEMENTATION.**

- code PR `EGAILab/minion-agent#17`:
  `3c0a916c97f02d0d29d8d8d08095f53848074d29`;
- docs PR `EGAILab/minion-agent-docs#26`:
  `8dc2b59042eac4387b72264682ab7b03d3c43c73`;
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`;
- PASS-10 targeted closure: docs PR #41 at
  `aa1ba27dccdbacb318fbff28c958a20031f008da`.

Both exact candidates were fetched from GitHub, matched coordination issue #16, and remained open,
ready, mergeable, and unmerged throughout the review. This is the mandatory workflow §11.8.8
complete review after all findings were provisionally closed. Approval applies only to the exact
SHA pair above.

## Independent Pi audit

The review used pinned Pi first, then normative spec, manifest, canonical evidence, certified Rust
architecture, assurance, and Python only as secondary evidence.

Re-read directly at the pinned revision:

- `packages/agent/src/agent.ts`: `ActiveRun`, `Agent.signal`, `abort`, `prompt`, `continue`,
  `createLoopConfig`, `runWithLifecycle`, `handleRunFailure`, `finishRun`, `processEvents`;
- `packages/agent/src/agent-loop.ts`: `streamAssistantResponse`, `transformContext`, continuation
  callbacks, sequential/parallel tool batches, preflight, execution updates, and finalization;
- `packages/agent/src/types.ts`: callback, signal, request, hook, tool, update, and lifecycle types;
- relevant pinned tests/call sites for abort identity, callbacks, and batch truncation.

The resulting contract matches Pi: a fresh controller/read-only signal per run; Agent-only abort
authority; cooperative polling rather than forced task cancellation; the same signal at every
consumer; transform context immediately before each request; exact preflight error/abort priority;
distinct sequential and parallel batch truncation; after-hook execution despite abort; abort not
itself terminating the run; failure classification from current signal state; and cleanup after
settlement. Real provider-transport cancellation remains explicitly deferred to PROV-004.

## Complete finding ledger

| Finding | Final result |
|---|---|
| L09-C001 | CLOSED — sequential and parallel abort algorithms are distinct and complete. |
| L09-C002 | CLOSED — six-outcome preflight priority matches Pi. |
| L09-C003 | CLOSED — complete consumer/ignore-signal/terminal matrix. |
| L09-R001 | CLOSED — raw/helper tool hooks receive the active signal. |
| L09-R002 | CLOSED — failure classification reads the signal at settlement. |
| L09-R003 | CLOSED — all four signal/update tool capability combinations exist. |
| L09-R004 | CLOSED — read-only signal view and Agent-only cancellation authority. |
| L09-R005 | CLOSED — provider-local transform-context seam exists. |
| L09-R006 | CLOSED — transform signal/Agent metadata cannot be redirected or dropped. |
| L09-R007 | CLOSED — status/signal entry and exit failure policy is complete. |
| L09-R008 | CLOSED — recommended after-tool helper delivers signal when requested. |
| L09-R009 | CLOSED — superseded prose is clearly historical. |
| L09-R010 | CLOSED — unrestricted public queue restoration authority removed. |
| L09-R011 | CLOSED — former peek/commit identity defect removed. |
| L09-R012 | CLOSED — current AG-011 reservation rule is coherent. |
| L09-R013 | CLOSED — re-entrant observer cannot claim reserved input. |
| L09-R014 | CLOSED — partial-prefix duplication removed. |
| L09-R015 | CLOSED — pre-step/prepare-next-turn Agent authority handles redirect and true omission. |
| L09-R016 | CLOSED — tool signal-capability prose/current pointers corrected. |
| L09-R017 | CLOSED — reservation binding is getter-only and one-shot. |
| L09-R018 | CLOSED — transform delegation grammar is unambiguous and enforced at the boundary. |

No prior closure regressed under the final whole-contract audit.

## Requirement ledger

| Row | Adopted/deferred rule | Evidence | Rust ownership / verdict |
|---|---|---|---|
| AI-027 | Request carries cooperative signal | Python language tests; placeholders excluded | Add typed request signal; PASS. |
| AG-007 | Run signal lifecycle, authority, propagation, failure settlement | Complete Python language matrix | Agent/controller/driver; PASS. |
| AG-011 | FIFO inbox identity/order and reservation integration | Direct canonical plus language tests | Existing Inbox plus private entry reservation; PASS. |
| AG-023 | Provider-local transform context with authoritative Agent/signal | Seven convergence witnesses | Typed transform event/delegation; PASS. |
| TOOL-009 | Explicit signal/update capability vocabulary | Language tests | Typed capability flags/traits; PASS. |
| TOOL-018 | Layer-06 structural signal seam activated here | Certified Rust seam | No redesign; PASS. |
| TOOL-024 | Signal through pre/execute/post and batch polling | Full Python tool matrix | Extend existing executor; PASS. |
| PROV-004 | Actual transport abort | Explicit later-provider defer | Correctly outside Layer 09. |

The manifest parses as 79 rows / 79 unique IDs. Dispositions are coherent and every current
implementation/evidence pointer inspected resolves to the claimed surface.

## Canonical and evidence policy

`active-abort-provider`, `active-abort-tool`, and `abort-settles-before-idle` remain explicit
`TO_BE_FILLED_FROM_PINNED_PI_BEHAVIOR` placeholders. They are not counted by manifest or assurance
as satisfying evidence. Listener-driven behavior is carried by discriminating language tests.
No canonical runner simulates abort, signal propagation, transform normalization, or inbox
reservation semantics.

## Whole-contract state-machine audit

The complete audit covered and passed:

- signal absent while idle, installed before RUNNING observation, stable for one run, and removed
  before IDLE observation;
- idle abort no-op and active abort idempotence;
- RUNNING-observer failure rollback, exact-once reserved input, order/identity preservation, and
  unrelated observer side effects;
- IDLE-observer failure after all committed cleanup writes;
- provider request and per-request transform receiving the same active signal;
- provider-local transform output never mutating persistent/run-local history;
- invalid transform delegation rejected before downstream delivery and settled as an ordinary
  represented run error without provider invocation;
- lifecycle, prepare-next-turn, turn-stopping, before/after tool hooks, tool execution, and update
  consumers receiving the same signal;
- unknown/validation/hook errors retaining priority over abort where Pi does;
- sequential and parallel batch checkpoints, including the A/B/C parallel witness;
- signal-only, update-only, both, and neither tool execution forms;
- unconditional post-tool hook and normal turn/continuation policy after cooperative abort;
- represented `StopReason.ABORTED` remaining distinct from active propagation;
- an exception after abort settling as aborted, while an unrelated exception settles as error;
- every consumer being free to ignore abort, allowing ordinary completion;
- transport cancellation and Layer 10 remaining out of scope.

## L09-R018 final regression

The agreed `{0,1,3}` transform delegation grammar is implemented exactly. Six new tests plus the
unchanged full-length redirect guard prove both invalid two-field readings, non-forwarding to a
variadic listener, Layer-08 represented failure, message-only positive delegation, and real
provider payload. The candidate diff from PASS 9 is confined to `_transform_context`, its tests,
AG-007/AG-023 traceability, spec, and assurance.

## Rust implementability and lower-layer delta

Certified Rust Layers 01–08 already contain typed Agent/Inbox/LLM structures, lifecycle events,
continuation hooks, `ToolExecutionSignal`, and `ToolExecutionRequest.signal`. Layer 09 can be
implemented independently and idiomatically with:

- a private abort controller and public read-only run signal;
- an optional typed signal on provider requests;
- typed transform delegation where only messages are replaceable;
- the existing Layer-06 preflight/execution split and signal seam;
- a private linear inbox-entry reservation;
- current Layer-08 failure/lifecycle settlement.

No observable contract in Runtime, LLM, Session, XFORM, Tool model/registry, Tool execution,
Agent state/inboxes, or Agent loop requires reopening. Rust need not reproduce Python variadic
tuple mechanics.

## Contract-quality answers

- Runner simulates production semantics: **NO**.
- Python workaround compensates for incomplete shared semantics: **NO**.
- Provider-visible projection/order differs from Pi: **NO**.
- Earlier certified layer prevents faithful implementation: **NO**.
- Transform delegation admits two valid observable readings: **NO**.
- Layer-10 or transport behavior leaked into Layer 09: **NO**.
- Rust can implement without consulting Python mechanics: **YES**.
- Python and Rust could satisfy the written contract while making materially different choices:
  **NO** for the audited Layer-09 surface.

## Fresh gates

Executed against exact code SHA `3c0a916c97f02d0d29d8d8d08095f53848074d29`:

```text
full Python suite
    1131 passed / 19 xfailed

coverage
    100% (2842 / 2842 statements)

targeted active-abort transform tests
    8 passed

full conformance tests
    298 passed / 19 xfailed

ruff check
    PASS

mypy
    PASS (58 source files)

manifest
    79 rows / 79 unique IDs
```

`ruff format --check .` continues to report the same seven unrelated pre-existing drift files;
none is touched by PASS 10. All PASS-10-owned files pass the formatting scope. This is retained as
nonblocking pre-existing parity-neutral hygiene, not misreported as a green whole-tree format gate.

## Active findings and final status

```text
PI_PARITY_DEFECT
    none

CONTRACT_ASSURANCE_DEFECT
    none

PI_BEHAVIOR_UNCERTAIN
    none

blocking PARITY_CONSTRAINED_RISK
    none

unapproved observable divergence
    none
```

```text
shared Layer-09 contract
    APPROVED FOR RUST IMPLEMENTATION

Python Layer 09
    CERTIFIED

Rust Layer 09
    NOT_IMPLEMENTED

Layer 09 cross-language
    NOT CLOSED

Layer 10
    NOT STARTED
```

## Next action

Merge the exact approved shared/Python candidates using the repository's required squash policy,
land the review evidence, and update issue #16 to `STATUS = RUST_IMPLEMENTATION`,
`NEXT_OWNER = Codex`. Then stop. Rust Layer-09 implementation requires a separate pass.
