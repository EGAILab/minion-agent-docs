# Layer 07 — Fresh Independent Rust Contract Re-Review

**Review type:** contract-only; no Rust, Python, shared semantic, or canonical implementation files modified.

**Verdict:** REJECTED. The remediation closes L07-R001 and L07-R002, but L07-R003, L07-R004,
and L07-R005 remain blocking. One additional specification-accuracy issue is recorded as L07-R006.

## Starting state

- `minion-agent`: `61b7b4c83e439bd2c890d617763d2c7c53cdefef`
- `minion-agent-docs`: `32bf5a907e9d58497a0dec0dc6118d794ae1cb61`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- previous review: `assurance/layers/07-agent-state-inboxes-rust-review.md`
- previous review commit: `bb6bd276a2093904d0fbe424bafd45d2b6c08443`
- PASS 2.5 docs remediation `a323ed0b13383624d12b094ba65b84463c61b59a` and the
  subsequent spec-verification commit are present.
- The unrelated Phase-5 working-tree document remained untouched.

## Previous-finding ledger

| Finding | Original blocker | Claimed remediation | Independent verification | Verdict |
|---|---|---|---|---|
| L07-R001 | Mutable per-instance configuration and complete public-state ownership were absent | Added mutable `system_prompt`, `model`, `thinking_level`, runtime vocabulary, authority map | Pi fields and current-value ownership are now enumerated; Python instance fields and tests exist; L08 consumption is explicitly separate | **RESOLVED** |
| L07-R002 | Queue API narrowed Pi `AgentMessage` to `UserMessage` | Broadened Inbox/envelope/Agent wrappers to certified Layer-02 `Message` | Pinned `CustomAgentMessages` is empty, so the concrete pinned domain is exactly `Message`; mixed roles are accepted and tested | **RESOLVED** |
| L07-R003 | Fresh-instance replacement did not implement Pi's in-place reset | Added in-place active-guarded reset, but deliberately omitted message clearing | Identity/runtime/queue behavior is repaired; observable messages remain uncleared even though certified Session already provides the exact reset boundary | **PARTIALLY_RESOLVED_BLOCKING** |
| L07-R004 | No language-neutral direct Inbox canonical evidence | Added two direct scenarios, schema, and thin Python runner | Concrete scenarios exercise real Inbox behavior, but action schema is ambiguous and claimed clear-all evidence is absent | **PARTIALLY_RESOLVED_BLOCKING** |
| L07-R005 | Agent-state/disposition coverage incomplete | Added AG-014–016 and expanded authority map | AG-015 still combines adopted, deferred, divergent, and extension semantics under `adopted`; claimed Agent tools projection is not exposed; wake/reset relation is unspecified | **PARTIALLY_RESOLVED_BLOCKING** |

## Pinned Pi public-state audit

Pinned `AgentState` contains exactly nine fields:

1. mutable `systemPrompt`, default `""`;
2. mutable `model`, default internal `DEFAULT_MODEL`;
3. mutable seven-valued `thinkingLevel`, default `"off"`;
4. `messages` live-array getter plus shallow-copy assignment;
5. `tools` live-array getter plus shallow-copy assignment;
6. readonly `isStreaming`, initially false;
7. readonly optional `streamingMessage`, initially undefined;
8. readonly `pendingToolCalls`, initially an empty Set;
9. readonly optional `errorMessage`, initially undefined.

The repaired authority map mentions all nine. Current-value ownership for mutable configuration and
runtime vocabulary is clear. Messages and tools are intentionally mapped to Session and ToolRegistry
projections rather than duplicate stores. That architectural mapping is feasible, but the tools
projection is not yet present on Python `AgentInstance`, and AG-015 does not give its observable
divergences/deferred transitions coherent manifest dispositions.

Pi uncertainty: none material.

## AgentMessage domain

Pinned Pi defines `AgentMessage = Message | CustomAgentMessages[keyof CustomAgentMessages]`.
`CustomAgentMessages` is an empty declaration-merging interface at the pinned revision; consequently
the concrete pinned domain is exactly the already-certified Layer-02 `Message` union:
`UserMessage | AssistantMessage | ToolResultMessage`.

The typed `prompt` overload accepts one `AgentMessage` or an array; the distinct convenience overload
accepts text plus optional images. `steer` and `followUp` each accept one AgentMessage. Pi has no
`inject`; Minion correctly classifies silent injection as an extension. Provider conversion is a
later boundary and does not narrow Inbox storage.

The repaired shared mapping is correct. Python Inbox, envelope, and Agent wrappers now accept
`Message`, and language tests include assistant/tool-result/mixed-role FIFO cases.

## Reset audit

| State | Pi | Current Minion candidate | Match |
|---|---|---|---|
| messages | clear to empty | unchanged Session projection | **NO** |
| isStreaming/status | false/idle | idle precondition; remains idle | YES |
| streamingMessage | undefined | `None` | YES |
| pendingToolCalls | new empty Set | empty frozenset | YES |
| errorMessage | undefined | `None` | YES |
| steering queue | cleared | cleared | YES |
| follow-up queue | cleared | cleared | YES |
| identity/instance | preserved | preserved | YES |
| systemPrompt | preserved | preserved | YES |
| model | preserved | preserved | YES |
| thinkingLevel | preserved | preserved | YES |
| tools relationship | preserved | scope/registry relationship preserved | YES |

Pi rejects reset while active with exact text before any mutation. The repaired Python candidate
matches the guard, atomic rejection, in-place identity, configuration retention, runtime clearing,
and queue clearing. It does not clear observable messages.

### Mandatory messages disposition

- Pi clears observable messages: **YES**.
- Minion currently clears `AgentInstance.messages`: **NO**.
- Layer 03 prevents compliance: **NO**.
- A separate Layer-07 cursor is required: **NO**.
- Current AG-016/spec disposition is valid: **NO**.
- Classification: **PI_PARITY_DEFECT**, blocking.

The candidate's premise is factually contradicted by the certified Session contract and both current
implementations. Layer 03 already specifies an append-only `session/reset` marker whose derivation
excludes all prior surface while preserving Session identity and auditable physical history. Python
exports `session.reset(log)`; Rust exposes `Session::reset()`; both projections already honor the
marker. Rust Session language/conformance tests prove post-reset derivation excludes prior messages.

Therefore Agent reset can perform its active guard, append the existing reset marker, clear runtime
state and queues, and continue projecting messages through the same Session. This is precisely a
higher-layer use of certified Layer-03 semantics. No physical truncation, Layer-03 change, or new
projection mechanism is necessary.

Required action: make `AgentInstance.reset()` invoke the certified Session reset operation, add a
test that appends messages then proves `instance.messages == ()` after reset, and correct AG-016/spec/
assurance prose and disposition. AG-016 cannot remain `adopted` while explicitly omitting a required
observable effect.

## Inbox canonical review

Direct scenarios:

- `conformance/agent/agent-inbox-queue-mode-fifo.yaml`
- `conformance/agent/agent-inbox-queue-independence-and-clearing.yaml`

For these concrete documents, the runner is thin: it constructs a real Inbox, translates declarative
operations to its methods, and serializes returned observations. It does not store queues, calculate
FIFO, choose claim outcomes, or synthesize clear/pending behavior. The scenarios directly prove
one-at-a-time/all FIFO claims, empty/repeated claims, enqueue-after-claim behavior, queue independence,
single-target clear, and OR-style pending observation.

Two assurance gaps remain:

1. The schema's `action` uses only `minProperties: 1`; it permits multiple operation keys in one
   action. The Python runner then supplies Python-specific `if/elif` precedence. An independently
   constructed document containing both `steer` and `follow_up` validates with zero schema errors,
   yet another language could reasonably dispatch both or reject it. The action must be a `oneOf`
   of exactly one operation, with `observe` constrained to claim/pending operations.
2. AG-013 claims the clearing scenario exercises `clear_all`, but neither scenario contains
   `clear: {queue: all}`. Add a direct clear-all observation (to the existing scenario or a small
   additional scenario) before claiming that canonical evidence.

The text-only enqueue fixture deliberately tests ordering rather than the full message union. That
is acceptable because the schema says so explicitly and the domain is independently fixed by the
Layer-02 type plus language tests; the runner does not filter messages returned by production.

## Wake

Pi has no wake flag. Minion's `wake_requested`/`take_wake` is correctly described as an intentional
architectural extension. Ordinary queue clear is stated and tested to leave wake untouched.

However reset's relation to wake is not specified. Current Python reset delegates `clear_all`, so a
pre-existing wake survives. A Rust implementer could reasonably clear it as runtime state. Because
wake is public and observable, the Layer-07 rule must explicitly state whether reset preserves or
consumes it and provide evidence. This is part of L07-R005's incomplete extension disposition.

## Status / isStreaming

Pi's active-run transition writes are: `runWithLifecycle` sets true after establishing the active
run; `finishRun`, invoked from `finally`, sets false before clearing remaining runtime state. Reset
also assigns false, and initialization establishes false.

Layer 07 correctly owns the two-value public vocabulary and idle initial value; Layer 08 correctly
owns active-run transition timing. `IDLE`/`RUNNING` is a lossless projection of false/true.

The verification-pass sentence that “No other code path in pinned Pi ever assigns isStreaming” is
incorrect because reset explicitly assigns false (and initialization sets the initial false value).
The intended statement can be repaired narrowly to “no other active-run lifecycle path.” This is
L07-R006, a contract-assurance accuracy defect.

## Manifest / requirements

| Requirement | Pi source / mapping | Shared rule | Evidence | Rust implementable? | Verdict |
|---|---|---|---|---|---|
| AG-010 | agent-end invocation-local message set | Layer-08 event result | Existing later-layer canonical | Later | Boundary unchanged |
| AG-011 | PendingMessageQueue, steer/followUp | two FIFO queues, full concrete Message domain; inject/provenance extensions | Python tests + two direct scenarios for queue mechanics | YES | PASS |
| AG-012 | QueueMode/drain | exact all/one-at-a-time policies | Python tests + FIFO scenario | YES | PASS |
| AG-013 | clear methods/hasQueuedMessages | independent clear and pending OR | Python tests + partial canonical | YES | FAIL assurance: clear-all canonical claim false |
| AG-014 | mutable configuration | per-instance mutable current values | Python tests | YES | PASS |
| AG-015 | remaining AgentState fields and wake | projections, status/runtime vocabulary, divergences/extensions | Incomplete/mixed; no Agent tools accessor | Partly | FAIL |
| AG-016 | Agent.reset | adopted in-place reset | Python tests omit messages; certified Session reset already available | YES | FAIL parity |

AG-015 is internally inconsistent under `disposition: adopted`: it contains an intentional messages
live-reference divergence, a non-reproduced tools setter, deferred runtime transitions, and an
intentional wake extension. Split or otherwise formally classify these independently. Additionally,
the spec calls ToolRegistry visibility “the Agent's public tools projection,” but Python
`AgentInstance` exposes no tools accessor; the manifest points only to `ToolRegistry.visible_from`.
Add the actual Agent-level projection or explicitly revise the claimed public surface.

## Lower-layer impact

- Layer 01 Runtime — delta required: **NO**. L07 may reuse Context/scope/events.
- Layer 02 LLM — delta required: **NO**. Certified `Message` is the inbox domain.
- Layer 03 Session — delta required: **NO**. Existing reset marker and derivation already satisfy
  the needed effective-history reset while retaining append-only audit history.
- Layer 04 XFORM — delta required: **NO**. Provider transformation remains later.
- Layer 05 Tool model/registry — delta required: **NO**. Add only an Agent-level view over existing
  visibility; do not alter registry semantics.
- Layer 06 Tool execution — delta required: **NO**.

## Cross-language implementability

Rust can implement the repaired portions without Python-specific mechanics: mutable typed fields,
the certified Message enum, two `VecDeque` queues, deterministic policies, an explicit wake flag,
and the two-value status projection are natural.

Reset is also independently implementable by calling the certified Rust Session reset API. What is
not independently implementable yet is the *current written contract as a whole*: it simultaneously
claims adopted reset parity and omits message clearing; it leaves wake-on-reset unresolved; and it
does not define a concrete Agent-level tools projection surface. Two reasonable Rust implementers
could therefore produce observably different implementations.

## Verification observations

- Python focused Agent/Inbox/property/direct-canonical tests: **51 passed**.
- Shared conformance schema validation: **169 passed**.
- Manifest parse/uniqueness: **72 rows / 72 unique IDs**.
- Independent malformed-action probe: an action containing both `steer` and `follow_up` produced
  **0 schema validation errors**, confirming the ambiguity.
- Rust Session language tests: **9 passed**.
- Rust Session conformance: **1 passed**.

Green tests do not close the missing reset assertion or the canonical-schema ambiguity because
neither is currently represented by those test expectations.

## Findings

### PI_PARITY_DEFECT

- **L07-R003 remains blocking:** observable Agent messages are not cleared by reset despite Pi and
  despite an already-certified Session reset mechanism.
- **L07-R005 public tools sub-finding:** Python does not expose the Agent-level tools projection the
  spec claims.

### CONTRACT_ASSURANCE_DEFECT

- **L07-R004 remains blocking:** canonical action schema permits ambiguous multi-operation actions,
  and claimed clear-all canonical evidence is absent.
- **L07-R005 remains blocking:** AG-015 mixes incompatible dispositions, and wake-on-reset plus the
  Agent tools projection are underspecified.
- **L07-R006:** the isStreaming write-point statement incorrectly excludes reset/initialization.

### PARITY_NEUTRAL_HARDENING

- Rust may use typed enums, `VecDeque`, immutable snapshots, and synchronized state internally.

### PARITY_CONSTRAINED_RISK

None.

### PI_BEHAVIOR_UNCERTAIN

None.

## Verdict

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

Rust implementation modified
    NO
```

## Narrow next action

1. Use the already-certified Session reset marker from `AgentInstance.reset()` and prove projected
   messages become empty.
2. Make Inbox canonical actions structurally exclusive and add actual clear-all canonical evidence.
3. Split/correct AG-015 dispositions; expose or precisely define the Agent-level tools projection;
   specify wake-on-reset.
4. Correct the isStreaming write-point sentence.
5. Re-certify shared/Python Layer 07, then repeat the independent Rust contract review.

Do not implement Rust Layer 07 and do not start Layer 08.
