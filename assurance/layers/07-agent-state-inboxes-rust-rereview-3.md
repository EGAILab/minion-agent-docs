# Layer 07 — PASS 4 Independent Rust Contract Re-Review

**Review type:** contract-only. No Rust, Python, shared contract, manifest, or canonical implementation file was modified.

**Verdict:** APPROVED FOR RUST IMPLEMENTATION.

## Starting state and lineage

- `minion-agent`: `19ecb88ded6adc89847467a14f459b041735abc5`
- `minion-agent-docs`: `2af18a1b16e9b0c175b1595e49638c006e323018`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- preceding Rust review: `assurance/layers/07-agent-state-inboxes-rust-rereview-2.md`
- preceding review commit: `437bb7a6fe9f4843169d2f226fbd18004959b1ac`
- PASS 4 commits contain no `minion-agent-rust/**` or unrelated Phase-5 file changes.

The candidate was reviewed in isolated worktrees. The pre-existing Phase-5 modification in the main docs checkout remained untouched.

## Finding closure ledger

| Finding | Prior objection | PASS 4 repair | Independent verification | Verdict |
|---|---|---|---|---|
| L07-R004 | Observe-bearing mixed Inbox actions remained schema-valid | Every operation branch excludes every other operation key; enqueue/clear branches also exclude `observe` | Exhaustive 15-pair matrix, with and without `observe` (30 variants), rejected every mixed action; eight valid single-operation variants remained valid | **RESOLVED** |
| L07-R007 | `AgentInstance.tools` raised on a valid bare context instead of exposing Pi's empty default | Total accessor returns `()` when the tools service is unavailable, otherwise projects `visible_from(scope)` | Bare instance returned `()`; registered scoped tool was visible before and after reset | **RESOLVED** |

Previously closed L07-R001 through L07-R003 and L07-R005/L07-R006 remain closed. PASS 4 did not introduce contradictory evidence.

## Pinned Pi re-audit

Pinned Pi creates `AgentState.tools` as `initialState?.tools?.slice() ?? []`, so a public empty default is required. Its reset retains tools while clearing messages, runtime fields, and both queues. The corrected Minion projection now matches that observable default while retaining the already-approved registry-backed storage divergence.

Pinned Pi's complete nine-field AgentState remains accounted for: `systemPrompt`, `model`, `thinkingLevel`, `messages`, `tools`, `isStreaming`, `streamingMessage`, `pendingToolCalls`, and `errorMessage`. The concrete pinned AgentMessage domain remains the certified `Message` union because pinned `CustomAgentMessages` is empty.

## L07-R004 — canonical/schema closure

The action schema has six mutually exclusive branches: `steer`, `follow_up`, `inject`, `clear`, `claim`, and `has_queued_messages`. Each branch explicitly excludes the five other operation keys. The four enqueue/clear branches additionally exclude `observe`; `claim` and `has_queued_messages` may carry it.

Independent adversarial validation checked all 15 unordered operation-key pairs both without and with `observe` (30 malformed variants). Every variant was rejected. Independent positive validation checked eight valid single-operation shapes, including observed and unobserved claim/pending actions; all were accepted.

The two direct scenarios remain language-neutral:

- `agent-inbox-queue-mode-fifo`
- `agent-inbox-queue-independence-and-clearing`

They exercise real Inbox FIFO/claim modes, independence, targeted clearing, and clear-all. The runner translates scenario vocabulary to real Inbox calls; it does not choose queue semantics, synthesize results, or repair invalid actions.

## L07-R007 — tools totality closure

`AgentInstance.tools` now has a total rule stated in spec, AG-017, implementation, and tests:

- unavailable/unmounted tools service: empty tuple;
- available service: fresh `ToolRegistry.visible_from(instance.scope.key)` projection;
- reset: the same registry/scope relationship remains visible.

Independent probes observed `()` on a bare valid instance, `("echo",)` after registering a scoped tool, and the same value after reset. No duplicate registry, ordering, shadowing, withdrawal, or visibility semantics were introduced. Those remain Layer-05 authority.

## Manifest and specification

The manifest has 75 rows and 75 unique IDs. AG-013's stale wake cross-reference now points to AG-019. AG-017 records tools totality and cites both the absent-service and reset-retention tests. Its `intentional divergence` remains explicitly about ownership/live-reference/setter architecture, not a license for different default visibility behavior.

The earlier coherent split remains intact:

- AG-015: adopted two-value `isStreaming` projection; Layer 08 owns run timing.
- AG-017: Session/registry-backed public projections and their disclosed architectural divergence.
- AG-018: runtime field vocabulary/initial values; transition behavior deferred concretely to Layer 08.
- AG-019: Minion-only wake facility.
- AG-016: Pi reset plus explicit Minion wake preservation.

No shared rule remains ambiguous for Rust implementation.

## Lower-layer impact and Rust feasibility

No certified lower-layer semantic change is required:

- Layer 01 Runtime: reuse context/service/event facilities.
- Layer 02 LLM: reuse the certified Message union.
- Layer 03 Session: reuse certified reset marker and effective-message derivation.
- Layer 04 XFORM: no dependency change.
- Layer 05 tools: project the certified ToolRegistry visibility surface.
- Layer 06 execution: no change.

Rust can implement Layer 07 from shared artifacts without reading Python. It can represent mutable instance configuration/runtime fields, Session-backed messages, registry-backed tools with an empty unavailable-service default, deterministic inbox queues and claim modes, the Minion wake latch, reset, and status vocabulary. Layer-08 run-loop transition timing remains explicitly out of scope.

## Verification evidence

- Full Python suite: 972 passed, 19 xfailed, 0 failed.
- Coverage: 100.00% (`2390/2390` statements).
- Ruff: pass.
- mypy: pass (57 source files in the configured `src` invocation).
- Schema tests: 183 passed.
- Focused Agent/Inbox/conformance tests: 53 passed.
- Manifest: 75 rows / 75 unique IDs.
- Independent schema matrix: 30 malformed pair variants rejected; 8 valid variants accepted.
- Independent tools probes: empty default, mounted visibility, and post-reset visibility passed.
- Isolated code/docs worktrees were clean before adding this artifact.

## Active findings

### PI_PARITY_DEFECT

None.

### CONTRACT_ASSURANCE_DEFECT

None.

### PARITY_NEUTRAL_HARDENING

None required for approval.

### PARITY_CONSTRAINED_RISK

None blocking.

### PI_BEHAVIOR_UNCERTAIN

None.

## Verdict

```text
shared Layer-07 contract
    APPROVED FOR RUST IMPLEMENTATION

Python Layer 07
    CERTIFIED

Rust Layer 07
    NOT_IMPLEMENTED

Layer 07 cross-language
    NOT CLOSED

Layer 08
    NOT STARTED
```

Stop here. The next pass is a separate Rust Layer-07 implementation, conformance, assurance, and certification pass.
