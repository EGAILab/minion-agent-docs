# Layer 10 — Rust implementation preflight blocker

**Status:** `BLOCKED BEFORE RUST EDITS`

## Starting state

- merged code baseline: `f12c0e37f8d33ca8be78028ab4ec9bd2b59c9eb8`
- merged docs baseline: `8e18072666c104369cbed2922e7d9084a090af9d`
- approved shared/Python heads recorded by coordination issue #19:
  - code: `ea4f250fe0c6d640036960459dd74711795a51d7`
  - docs: `a99f348f947431ecfa1b09cdc00f137f3fd0cd80`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Rust implementation branch: `impl/10-provider-abstraction-rust`, created from merged code
  baseline; no Rust files were modified.

The implementation preflight followed the required authority order and re-read the merged Layer-10
spec, manifest rows `AI-012`, `AI-028`–`AI-032`, all seven `llm-service` canonical scenarios, the
existing Rust LLM service/adapter architecture, and pinned Pi's `ProviderStreams`, `MutableModels`,
compat registry, and faux-provider registration surfaces.

## L10-I001 — exact-SHA approval evidence drift

**Classification:** `CONTRACT_ASSURANCE_DEFECT`

The merged final review artifact
`assurance/layers/10-provider-abstraction-final-contract-rereview-3.md` says its exact approved
candidate is code `a7d05f26...` / docs `7c8d8ed6...`. Those are the preceding PASS-6 candidate
heads. The actual final PASS-7 candidate approved and merged was code `ea4f250f...` / docs
`a99f348f...`, as recorded by issue #19 and the final review/PR comments.

This does not make the merged semantic contract ambiguous, but it violates the exact-SHA evidence
invariant and must be corrected by an explicit erratum that preserves the original review history.

## L10-I002 — stale canonical Pi-source characterization

**Classification:** `CONTRACT_ASSURANCE_DEFECT`

Three current canonical scenario notes contradict the approved Layer-10 spec and manifest row
`AI-030`:

- `conformance/agent/llm-service-registration-and-replacement.yaml` says Pi has no
  adapter-registration concept at all;
- `conformance/agent/llm-service-withdrawal-does-not-remove-a-later-replacement.yaml` says Pi has no
  analogue for registry machinery;
- `conformance/agent/llm-service-introspection-reflects-current-registrations.yaml` says `models()`
  has no direct Pi analogue.

Pinned Pi and the approved contract identify three live comparison surfaces:
`MutableModels`, compat's API registry, and `registerFauxProvider`'s per-call unregister handle.
Minion intentionally adopts none of their exact granularity/composition rules, under the recorded
owner-approved `AI-030` divergence, but it is incorrect to say there is no Pi concept or analogue.

The canonical expected observations remain coherent. The narrow repair is documentary: update the
three notes to accurately identify the Pi comparison surfaces and state that Minion's full-identity,
per-registration-call semantics are the approved intentional divergence. Do not change scenario
operations or expected behavior.

## Findings and stop verdict

```text
PI_BEHAVIOR_UNCERTAIN       none
PI_PARITY_DEFECT            none newly found
CONTRACT_ASSURANCE_DEFECT   L10-I001, L10-I002
PARITY_CONSTRAINED_RISK     none
PARITY_NEUTRAL_HARDENING    none
```

```text
shared Layer-10 contract    REOPENED for narrow evidence-only remediation
Python Layer 10             remains implemented; certification evidence needs repair
Rust Layer 10               BLOCKED / NOT_IMPLEMENTED
Layer 10 cross-language     NOT CLOSED
Layer 11                    NOT STARTED
```

No Rust, Python, spec, manifest, schema, or canonical expected-result file was modified in this
preflight. After the shared owner repairs the two evidence defects and supplies a fresh exact-SHA
approval/handoff, Rust implementation can resume from the same typed design: remove the resolved
adapter's eager expected-error channel, add per-registration-call idempotent withdrawal and
`models()` introspection, and wire the seven canonical scenarios through the real Rust service.
