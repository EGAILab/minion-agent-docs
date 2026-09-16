# Layer 10 — independent Rust contract review

**Verdict:** `REJECTED` for the exact candidate pair below. Rust Layer 10 is blocked; Layer 11 was
not started.

## Exact review target

- code PR #20: `4deef8f8d8dba1f109057ee03755aa7a55ad1a7c`
- docs PR #45: `1d395df1770cc7d6a32bc4597f1220c4f8e3de5b`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- coordination issue: `EGAILab/minion-agent#19`, verified `STATUS = RUST_CONTRACT_REVIEW` and
  `NEXT_OWNER = Codex`

Both PRs were open, Ready for Review, unmerged, cleanly mergeable, and their remote heads matched
issue #19. The review used detached/isolated worktrees. Neither candidate branch was modified.

## Authority and source audit

Reviewed in the required order:

1. pinned Pi `packages/ai/src/types.ts`, especially `ProviderStreams` and `StreamFunction`;
2. pinned Pi `packages/ai/src/models.ts`, especially `CreateProviderOptions`, `createProvider`,
   `apiFor`, and `dispatch`;
3. candidate `pi-parity-manifest.yaml`, rows `AI-028` and `AI-029`;
4. candidate `spec/llm.md`, “Provider abstraction (Layer 10)”;
5. cited canonical scenarios and their real Rust runner;
6. certified Rust `llm/adapter.rs`, `llm/service.rs`, `llm/scripted.rs`, and focused tests;
7. Layer-02 assurance and the Layer-10 handoff;
8. Python implementation/tests only after the independent audit.

Pinned Pi's exact interface is:

```text
ProviderStreams
    stream(...)       required
    streamSimple(...) required
    fetchDeferred?    optional
    cancelDeferred?   optional
```

`StreamFunction` returns `AssistantMessageEventStream`; its source comment requires expected
request/model/runtime failures after invocation to be represented in that stream. `createProvider`
accepts either one `ProviderStreams` implementation or an API-keyed map. A missing API-map entry is
returned as a lazy/in-band stream failure.

## Requirement ledger

### AI-028 — adapter/implementation-module contract

**Result: FAIL.** The row and spec say Pi “also allows optional `streamSimple`”, but the pinned
interface declares `streamSimple` as required. Only `fetchDeferred` and `cancelDeferred` are
optional. The candidate then calls Minion's single `stream(request)` protocol a “direct, faithful
mapping” without disposing or mapping the second required Pi operation.

The Rust trait is also not the shape the row claims is already implemented:

```text
LlmAdapter::start(request) -> Result<RawAssistantStream, AdapterStartError>
```

It has no provider/api/models capability surface, and it admits an eager adapter rejection after
the model has resolved and adapter code has been invoked. The permanent Rust test
`adapter_start_failure_remains_eager_and_typed` proves this is current production behavior. That
does not satisfy the candidate's own direct-mapping/never-raises rule.

### AI-029 — registration and model-to-implementation resolution

**Result: FAIL.** The row combines several different semantic subjects under `disposition:
adopted`:

- Pi's single-vs-API-map provider dispatch;
- Minion's flat full-identity registry and eager missing-key simplification;
- replacement and withdrawal behavior with no direct Pi registration analogue;
- `models()` introspection, explicitly described as Minion-only.

Those subjects have different mappings/dispositions and cannot coherently share one `adopted`
label. The frozen design's eager caller-error boundary can justify Minion resolving a missing full
identity before provider invocation, but it does not make the rest of the Minion-only registration
API source-identical Pi behavior.

The row's Rust evidence is materially inaccurate. Current Rust:

```text
register(ModelIdentity, Arc<dyn LlmAdapter>) -> ()
```

It performs last-write replacement and exact full-identity lookup, but it has no adapter-declared
model set, withdrawal handle, stale-withdrawal protection, or `models()` introspection. Therefore
the statement that the row adds no Rust requirement is false.

The normative spec also universalizes the Python-only `ModelId.api = "mock"` default. Certified
Rust already requires an explicit strict three-part `ModelIdentity`; the Layer-02 assurance records
that this default was a Python-specific temporary compromise. A language-neutral specification
must not present it as the cross-language Minion contract.

## Canonical evidence audit

The cited scenarios are real and their Rust adapter is thin:

- `eager-invalid-model-fails-before-stream` proves only exact missing-identity lookup before an
  assistant stream exists;
- `public-stream-fuses-after-first-terminal` proves terminal fusion;
- `represented-provider-error-rides-stream` proves an already-represented provider failure remains
  in-band.

They do not prove the new adapter protocol's required operations/identity metadata, registration of
declared models, replacement, stale withdrawal, introspection, or the selected-provider/missing-API
case. The latter behaviors are supported only by Python language tests. This omission is
material because Rust and Python already differ on precisely those newly normative behaviors.

Direct provider-service behavior is independently observable without Layer 11, so a small
language-neutral scenario seam is feasible now. At minimum it should discriminate registration,
same-identity replacement, stale withdrawal, current-model introspection if retained as shared
surface, exact full-identity resolution, and expected post-resolution adapter-start failure
settlement.

## Rust architecture feasibility

Rust can implement a corrected Layer-10 boundary without redesigning Layers 01–09. The existing
typed `ModelIdentity`, `LlmAdapter`, `LlmService`, `AssistantStream`, and `ScriptedAdapter` are the
right authorities. Necessary changes, if the corrected shared contract retains them, are narrow
Layer-10 work:

- settle the exact mapping for Pi's required `stream` and `streamSimple` operations;
- make expected failures after resolved adapter invocation enter the returned stream;
- add typed registration ownership/withdrawal and introspection semantics, or explicitly exclude
  them from the shared surface with coherent dispositions;
- preserve explicit three-part Rust identity rather than copying Python's temporary default.

No Runtime, Session, XFORM, Tool, Agent, or cancellation contract must reopen.

## Findings

### L10-R001 — `PI_PARITY_DEFECT`

The candidate misreads required `ProviderStreams.streamSimple` as optional and certifies a
single-operation Minion protocol as a direct faithful mapping without an explicit disposition for
the missing operation.

### L10-R002 — `CONTRACT_ASSURANCE_DEFECT`

`AI-029` and the normative spec mix Pi adoption, an architectural simplification, and Minion-only
registration/introspection extensions under one `adopted` disposition. The prose is Python-shaped
and contradicts certified Rust's strict identity and current registration surface.

### L10-R003 — `PI_PARITY_DEFECT` (current Rust production)

`LlmAdapter::start` may return eager `AdapterStartError` after successful model resolution and
adapter invocation. The candidate's own never-raises rule requires expected adapter/provider
failure at that point to be represented by the returned assistant stream. Current tests explicitly
lock in the opposite behavior.

### L10-R004 — `CONTRACT_ASSURANCE_DEFECT`

The candidate's canonical citations do not exercise most newly normative AI-028/AI-029 behavior,
and its Rust evidence claims completeness despite demonstrable missing public semantics. A minimal
direct language-neutral provider-service seam is feasible without Layer 11.

No `PI_BEHAVIOR_UNCERTAIN` remains: the relevant pinned Pi types and dispatch code are explicit.

## Test observations

Read-only candidate checks:

- focused Rust adapter/stream/conformance suites: PASS, 11 tests;
- shared schema validation: PASS, 185 tests;
- manifest parse/uniqueness: PASS, 81 rows / 81 unique IDs.

Green tests do not close the findings because the new contract is misstated and the cited tests do
not discriminate the missing behavior.

## Verdict and narrow remediation

```text
shared Layer-10 contract   REJECTED
Python Layer 10            REOPENED
Rust Layer 10              BLOCKED
Layer 10 cross-language    NOT CLOSED
Layer 11                   NOT STARTED
```

Required shared/Python remediation:

1. Correct the pinned `ProviderStreams` shape and explicitly map/dispose both required operations.
2. Split or rewrite AI-029 so each row has one coherent semantic subject and disposition; make the
   rules language-neutral and mark Python's temporary `api="mock"` default as Python-specific.
3. Settle the exact expected-failure boundary after resolved adapter invocation, then align the
   shared rule and Python evidence. Rust remediation belongs to a later implementation pass.
4. Add minimal direct language-neutral provider-service evidence for the retained registration,
   replacement/withdrawal/introspection, resolution, and failure-settlement rules; do not count
   neighboring stream-terminal scenarios as proof of those rules.
5. Replace the inaccurate Rust “already implemented/no new requirement” pointers with honest
   pending/remediation status until exact Rust evidence exists.

STOP after shared/Python remediation. Any new candidate SHA requires a fresh independent Rust
review. Do not implement Rust Layer 10 and do not start Layer 11.
