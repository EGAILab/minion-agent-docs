# Layer 07 — Independent Rust Review of Agent State and Inboxes

**Verdict:** REJECTED pending narrow shared/Python remediation. Rust Layer 07 was not implemented.

## Starting state

- `minion-agent`: `e8e129b7f0b1b9c9bc0f034f7a7969e2fb5de276`
- `minion-agent-docs`: `e575ea194320abedd9a1104337e27478b76a05a5`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Layers 01–06 remain certified and closed.
- The unrelated Phase-5 working-tree document was not read, staged, or modified.

## Pinned Pi audit

`AgentState` exposes the actual mutable backing state. `systemPrompt`, `model`, and
`thinkingLevel` are directly assignable and are read for later runs. `messages` and `tools`
are public get/set arrays; assignment shallow-copies, while the returned arrays remain live.
The runtime-owned fields start as `isStreaming=false`, `streamingMessage=undefined`,
`pendingToolCalls=empty`, and `errorMessage=undefined`.

`PendingMessageQueue` stores `AgentMessage[]` in FIFO order. Its mode is exactly `"all" |
"one-at-a-time"`. `all` returns a shallow snapshot and empties the queue;
`one-at-a-time` removes and returns only the oldest item; an empty drain returns `[]`.
Steering and follow-up are distinct queue instances, default independently to
`one-at-a-time`, and expose mutable modes.

`Agent.steer` and `Agent.followUp` each accept the full `AgentMessage` union and enqueue one
message without checking active/idle state. `hasQueuedMessages()` is the OR of both queues.
The three clear methods are idempotent queue clears.

`Agent.reset()` is a public, in-place operation which rejects while active. When idle it clears
messages, streaming/error/pending-tool state, and both queues. It retains system prompt, model,
thinking level, tools, queue modes, listeners, and configuration.

## Public-state disposition review

| Pi field | Required ownership/disposition | Candidate status |
|---|---|---|
| `isStreaming` | L07 vocabulary/initial storage; L08 transition timing | Partly specified through public `AgentStatus`; formal adaptation disposition incomplete |
| `streamingMessage` | L07 vocabulary/initial storage; L08 transitions | Deferred narratively, not completely represented as L07 public state |
| `pendingToolCalls` | L07 vocabulary/initial storage; L08 transitions | Deferred narratively, not completely represented as L07 public state |
| `errorMessage` | L07 vocabulary/initial storage; L08 transitions | Deferred narratively, not completely represented as L07 public state |
| `systemPrompt` | Mutable per-instance public state; later run consumption | Omitted as a purported non-blocking adjacent gap |
| `model` | Mutable per-instance public state; later run consumption | Frozen/shared definition only |
| `thinkingLevel` | Mutable per-instance public state; provider projection later | No equivalent current instance state |
| `messages` | Public Agent projection backed by authoritative Session state | Authority identified, public projection semantics not specified |
| `tools` | Public Agent projection backed by authoritative ToolRegistry | Authority identified, public projection semantics not specified |

All fields are therefore **not** accounted for by a complete formal disposition.

The frozen `AgentDefinition` is compatible with a future mutable `AgentInstance` overlay, so no
architectural redesign is required. That feasibility does not make the present semantic omission
non-blocking: Pi mutations are immediately observable and affect subsequent runs. Layer 07 must
define current per-instance state and its mutation surface; Layer 08 may own when run snapshots are
consumed.

## Steering and follow-up review

The two-queue FIFO structure and `ALL`/`ONE_AT_A_TIME` claim mechanics match Pi's queue primitive.
Empty, repeated, and post-enqueue claims are naturally implementable. Separate targets correctly
avoid a cross-queue global sequence, leaving polling priority to Layer 08.

The accepted message domain does not match. Pi accepts `AgentMessage`; Python's `Inbox`, envelope,
and aliases accept only `UserMessage`. This excludes assistant, tool-result, and registered custom
messages that Pi can queue. The assurance narrative calls this intentional, while `AG-011` and the
spec describe adopted, non-rejecting queue behavior. This needs an official intentional-divergence
or deferred-parity disposition, or the API must be broadened.

`NEXT_STEP` and `NEXT_TURN` are acceptable category/provenance labels at Layer 07. Their polling
timing remains Layer 08. Silent `inject` and origin metadata are Minion extensions and must remain
distinguished from the adopted Pi baseline.

## Clear, pending, reset, and wake review

Python's one-target clear, clear-all, and OR-style `has_pending` correctly implement the queue
primitive. Clear operations leave `wake_requested` unchanged. Pi has no corresponding wake bit;
because Python exposes both `wake_requested` and `take_wake`, this is an observable Minion
architectural extension, not Pi parity.

The reset disposition is not coherent. The spec and `AG-013` describe fresh-instance replacement
as an intentional divergence from Pi's in-place `reset`, but the manifest row disposition is
`adopted`. Fresh replacement is observably different in identity, references, listeners, active-run
rejection, and retained configuration. Session's append-only log does not prevent a logical reset
projection. Reset must either be implemented at its proper ownership boundary or formally deferred/
diverged; it cannot be certified as adopted.

## L07/L08 boundary

Layer 07 can own state vocabulary, initial/current values, queue storage, claim/clear/pending
primitives, and public mutation/projection APIs. Layer 08 should own polling times, cross-queue
priority, run-state transitions, provider-loop orchestration, and message/session appends caused by
runs. Direct queue conformance does not require Layer 08.

The proposed Rust boundary is feasible without Session, Runtime, ToolRegistry, Layer-06, or scope
redesign. Rust currently has no Agent/Inbox implementation at all; a typed Agent instance with two
`VecDeque` queues and projections over existing Session/ToolRegistry authorities is straightforward.

## Canonical decision

The zero-canonical decision is rejected. The queue primitives are directly observable and already
callable independently of the run loop. A missing schema branch is a remediable assurance gap, not
evidence that the semantics belong to Layer 08.

Minimum language-neutral remediation should add a small `agent_inbox`-style action/observation seam
whose adapters invoke real Inbox primitives. Two or three scenarios can cover:

1. FIFO, empty/repeated claims, `one-at-a-time`, `all`, and enqueue-after-claim snapshot behavior.
2. Steering/follow-up independence, clear-one, clear-all, and OR-style queued-message observation.
3. If retained as shared behavior, wake versus silent injection and clear/wake independence.

The adapter must not implement FIFO, claiming, clearing, or wake semantics. No scenario should poll a
run, choose steering/follow-up priority, or exercise turn timing.

## Manifest and spec review

- `AG-011`: **FAIL** — queue mechanics are mostly complete, but the adopted disposition conflicts
  with the `AgentMessage` to `UserMessage` narrowing and Minion-only injection/provenance additions;
  canonical evidence is absent.
- `AG-012`: **FAIL for assurance** — exact claim policies are correct and implementable, but have no
  language-neutral canonical evidence.
- `AG-013`: **FAIL** — clear/pending mechanics are correct, but the row calls fresh-instance reset an
  intentional divergence while retaining `disposition: adopted`; canonical evidence is absent.
- Additional requirements/dispositions are required for the complete `AgentState` public surface,
  particularly mutable instance configuration and Session/ToolRegistry-backed views.
- `AG-008` is too broad and future-oriented to supply those missing Layer-07 rules.
- No direct contradiction with the future orchestration intent of `AG-001`–`AG-010` was found, but
  ownership overlap must be made explicit.

The spec is language-neutral for the queue algorithm itself, but public state, reset, accepted
message domain, wake/status adaptations, and formal deferral/divergence classifications are not
complete.

## Rust feasibility

- Existing Agent state/queues: absent.
- Session redesign required: **NO**.
- Runtime redesign required: **NO**.
- ToolRegistry redesign required: **NO**.
- Layer-06 change required: **NO**.
- Layer-08 implementation required for Layer-07 primitives: **NO**.
- Rust implementation feasible after contract remediation: **YES**.

An immutable definition can supply defaults while each instance owns mutable current configuration,
Inbox, status/runtime fields, and authority-backed message/tool projections. Detailed run-loop
integration remains Layer 08.

## Verification observations

- Python Inbox/property focus: **27 passed**.
- Shared schema validation: **166 passed**.
- Manifest parse and uniqueness: **69 / 69 unique IDs**.
- Rust workspace tests: **PASS**; there are no Rust Agent/Inbox tests or production modules yet.
- Newly owned Layer-07 canonical scenarios: **0**.
- Existing full-loop Agent scenarios exercise later orchestration and do not substitute for direct
  Layer-07 primitive conformance.

## Findings

### PI_PARITY_DEFECT

1. **L07-R001 — mutable instance public state omitted.** Pi exposes mutable per-instance
   `systemPrompt`, `model`, and `thinkingLevel`; the candidate has only a frozen shared definition
   and no formal parity disposition.
2. **L07-R002 — queue input domain narrowed.** Pi accepts `AgentMessage`; Python accepts only
   `UserMessage`, without a coherent official disposition.
3. **L07-R003 — reset is not Pi-equivalent.** Fresh-instance replacement is not the adopted,
   in-place, idle-only reset operation.

### CONTRACT_ASSURANCE_DEFECT

1. **L07-R004 — no language-neutral canonical evidence.** Direct queue behavior is independently
   observable now; zero scenarios is unjustified.
2. **L07-R005 — public-state/disposition coverage incomplete.** The nine Pi fields, public
   projections, status/wake adaptations, narrowing, and reset do not all have complete requirement
   rows and official dispositions.

### PI_BEHAVIOR_UNCERTAIN

None.

### PARITY_CONSTRAINED_RISK

None. Rust can implement the repaired boundary idiomatically.

### PARITY_NEUTRAL_HARDENING

Atomic claim implementation and immutable snapshot return shapes may be used internally provided
the observable queue contract is unchanged.

## Verdict and next action

```text
shared Layer-07 contract
    REJECTED

Python Layer 07
    REOPENED

Rust Layer 07
    BLOCKED

Layer 07 cross-language
    NOT CLOSED

Layer 08
    NOT STARTED
```

Return for narrow shared/Python remediation only: formalize the complete public-state ownership and
dispositions; resolve the accepted message domain; correct reset/wake/status classifications; and
add minimal direct language-neutral Inbox canonical evidence. Then repeat the independent Rust
contract review. Do not implement Rust Layer 07 before that approval.
