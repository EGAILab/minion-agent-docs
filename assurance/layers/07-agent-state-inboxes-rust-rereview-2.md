# Layer 07 — PASS 3 Independent Rust Contract Re-Review

**Review type:** contract-only. Rust, Python, shared specification, manifest, and canonical production files were not modified.

**Verdict:** REJECTED. PASS 3 resolves the reset/session defect and the manifest/status defects, and adds real clear-all evidence. Two blocking defects remain: the canonical action schema still accepts some mixed-operation actions, and the new public tools projection is undefined for an otherwise valid Agent instance without a mounted tools service.

## Starting state

- `minion-agent`: `1f1a297bd57a345f23caf22d13fcf47b57e17b72`
- `minion-agent-docs`: `a4b91af908d6afd9dafd4e436bf0c5026ce03f5a`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- preceding Rust review: `assurance/layers/07-agent-state-inboxes-rust-rereview.md`
- preceding review commit: `e25006668a59109d4dd03829c04e37d52f434107`
- both PASS 3 commits exclude the unrelated Phase-5 document and `minion-agent-rust/**`.

## Rejection ledger

| Finding | Original Rust objection | PASS 3 repair | Independent result |
|---|---|---|---|
| L07-R003 | Reset did not clear observable messages despite an existing certified Session reset boundary | `AgentInstance.reset()` now calls the certified Session reset operation | **RESOLVED** |
| L07-R004 | Direct Inbox schema admitted ambiguous actions and clear-all was not exercised | Added `oneOf`, observe restrictions, and a real clear-all sequence | **PARTIALLY_RESOLVED_BLOCKING**: clear-all is now proven, but observe-bearing mixed actions still validate |
| L07-R005 | Agent-state subjects/dispositions were bundled; tools projection absent; reset/wake unspecified | Split AG-015/017/018/019, added tools projection, specified wake preservation | **PARTIALLY_RESOLVED_BLOCKING**: dispositions and wake are repaired, but tools is not total on a valid bare-context instance |
| L07-R006 | Spec falsely claimed no other Pi write to `isStreaming` | Limited the exclusivity claim to active-run lifecycle and separately named construction/reset | **RESOLVED** |

## Pinned Pi and reset/session integration

Pinned Pi's nine `AgentState` fields remain `systemPrompt`, `model`, `thinkingLevel`, `messages`, `tools`, `isStreaming`, `streamingMessage`, `pendingToolCalls`, and `errorMessage`. `Agent.reset()` rejects atomically while active; while idle it clears messages, runtime fields, and both queues and retains configuration, identity, listeners, queue modes, and tools.

The certified Session contract already contains the required non-destructive reset mechanism. Reset appends a `session/reset` marker; effective derivation uses the latest marker as an exclusive floor; physical event history remains available for audit. PASS 3's `AgentInstance.reset()` calls that real operation. Consequently `AgentInstance.messages` becomes empty after reset without truncation or a Layer-03 semantic change. Rust's certified Session implementation already exposes equivalent reset/derivation behavior.

Reset preserves a pending Minion wake signal. The spec and AG-016 identify this as a Minion architectural rule, not Pi behavior. Queue clearing and wake consumption remain orthogonal.

## Canonical/schema review — blocking L07-R004 remainder

The two direct scenarios are language-neutral and invoke the real Inbox seam. The FIFO scenario exercises both claim modes, empty claims, and enqueue-after-claim. The independence scenario now populates both queues, executes `clear: {queue: all}`, and observes both empty. The runner delegates clear-all to `Inbox.clear_all()` and does not synthesize FIFO or clear results.

The action schema nevertheless does not enforce exactly one operation in all cases. Its `oneOf` branches require their own operation key, but do not exclude the other operation keys. Adding `observe` disables an enqueue/clear branch while leaving a claim/observation branch eligible. Independent validation accepted all of these malformed actions with zero errors:

- `{steer, claim, observe}`
- `{follow_up, claim, observe}`
- `{clear, has_queued_messages, observe}`

The runner then silently executes only the first recognized key because dispatch is an `if`/`elif` chain. Two conforming language runners could therefore interpret the same schema-valid action differently. Existing schema tests cover multi-operation actions without `observe` and single forbidden operations with `observe`, but not this interaction.

Required narrow repair: enforce exactly one operation key independently of observe eligibility (or make every branch exclude all other operation keys), and add regression cases for mixed observe-bearing actions. The runner must continue to dispatch rather than define operation-selection semantics.

## Manifest/status review

The manifest contains 75 rows and 75 unique IDs. The split subjects are coherent:

- AG-015: `isStreaming` two-value public projection, adopted; Layer 08 owns live transition timing.
- AG-017: Session-backed messages and registry-backed tools projections, intentional storage/ownership divergence; intended observable behavior remains mapped explicitly.
- AG-018: runtime field vocabulary and initial values now, transition timing deferred explicitly to Layer 08.
- AG-019: Minion-only wake latch, intentional extension/divergence.
- AG-016: Pi reset plus the explicit Minion wake-preservation rule.

The repaired isStreaming prose accurately distinguishes the two active-run lifecycle transitions from initialization and reset. L07-R006 is closed.

One nonblocking traceability blemish remains: AG-013 refers to AG-014 for wake semantics; the intended row is AG-019. Historical sections of the cumulative PASS 3 assurance also retain superseded UserMessage/row-count statements, although later text and current authority artifacts correct them.

## Agent tools projection — new blocking finding L07-R007

`AgentInstance.tools` correctly calls the certified Layer-05 `ToolRegistry.visible_from(scope)` when a tools service is mounted; it does not duplicate registry ordering, shadowing, withdrawal, or scope semantics. However, `AgentInstance` is publicly constructible and routinely tested with a bare `Context()`. On that valid state, the accessor raises:

`ServiceNotFoundError: no active provider for service 'tools'`

Pinned Pi initializes `state.tools` to an empty array, so the public field is always observable and defaults empty. Neither the shared contract nor AG-017 declares a mounted tools service as an AgentInstance invariant, and the agents plugin does not establish that dependency. The language test evidence only covers manually mounted registries.

Classification: **L07-R007 — PI_PARITY_DEFECT and CONTRACT_ASSURANCE_DEFECT**. The current candidate both fails Pi's default-empty observable behavior and leaves Rust implementers to guess whether tools-service presence is mandatory.

Required narrow repair: specify and enforce one coherent total public-state rule. Either ensure every valid AgentInstance is wired to the authoritative ToolRegistry, or define the projection's absent-service behavior as the Pi-compatible empty set. Add evidence for the default state and strengthen reset evidence to read registered tools before and after reset. No Layer-05 redesign is required.

## AgentState and lower-layer impact

All nine fields have explicit shared ownership. AgentMessage remains the pinned concrete `Message` union because pinned `CustomAgentMessages` is empty; User, Assistant, and ToolResult messages remain accepted at AgentMessage boundaries.

No certified lower-layer semantic delta is required:

- Layer 01 Runtime: no delta.
- Layer 02 LLM/message model: no delta.
- Layer 03 Session: no delta; Layer 07 consumes the already-certified reset marker/effective floor.
- Layer 04 XFORM: no delta.
- Layer 05 tools: no semantic delta; only Layer-07 wiring/default projection must be clarified.
- Layer 06 execution: no delta.

Rust can implement the reset, messages projection, inbox, wake, status vocabulary, and runtime-field shape from shared artifacts. Rust cannot independently implement the public tools state until the totality/wiring rule above is resolved. It also must not implement against a schema that admits ambiguous mixed actions.

## Verification

- Fresh schema suite: 179 tests passed, but the independent adversarial probes above demonstrate missing coverage and a real schema defect.
- Fresh Ruff: pass.
- Fresh mypy over `src`: pass (57 source files).
- Manifest structure: 75 rows / 75 unique IDs.
- Independent bare-context tools probe reproduced `ServiceNotFoundError`.
- PASS 3 commit file audit: no Rust files and no Phase-5 file in either candidate commit.

## Active findings

### PI_PARITY_DEFECT

- **L07-R007:** `AgentInstance.tools` is not a total Pi-compatible public state projection for a valid default/bare context.

### CONTRACT_ASSURANCE_DEFECT

- **L07-R004:** the canonical action schema accepts observe-bearing mixed operations.
- **L07-R007:** the contract does not define whether tools-service presence is an AgentInstance invariant or what the absent-service projection returns.

### PARITY_NEUTRAL_HARDENING

- None required for approval.

### PARITY_CONSTRAINED_RISK

- None beyond the active blockers above.

### PI_BEHAVIOR_UNCERTAIN

- None.

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
```

Only the two narrow repairs above are required before another independent Rust contract review. Rust Layer 07 and Layer 08 were not started.
