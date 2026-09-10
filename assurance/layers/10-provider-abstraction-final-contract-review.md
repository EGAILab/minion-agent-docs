# Layer 10 — final complete independent Rust contract review

**Review mode:** workflow §11.8.8 final complete exact-SHA contract review.

## Exact review target

- code PR #20: `4d63349d85d517359545b94ce0937548d3fb7314`
- docs PR #45: `57edf9fd08e9b7411d32177f5991756182dd6a7a`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- targeted convergence closure: docs PR #47 at
  `69c01a1e9d1de01b28d128219fbf2b6a8f67ff48`

Both candidate PRs were fetched again before review. Their remote heads matched issue #19, both
were Ready for Review, open, unmerged, and mergeable. The verdict below applies only to the exact
pair above. Neither candidate branch, Rust production, nor Layer 11 was modified.

## Review order and Pi audit

The review followed the required independent order: pinned Pi, normative spec, manifest,
canonical schema/scenarios, certified Rust architecture, assurance, then Python as secondary
implementation evidence.

Pinned Pi source read directly:

- `packages/ai/src/types.ts::ProviderStreams`, `StreamFunction`, `SimpleStreamOptions`,
  `DeferredFetchOptions`, and `DeferredCancelOptions`;
- `packages/ai/src/models.ts::Provider`, `Models`, `MutableModels`, `ModelsImpl`,
  `createProvider`, `apiFor`, and `dispatch`;
- `packages/ai/src/compat.ts::ApiProvider`, `registerApiProvider`, `getApiProvider`,
  `getApiProviders`, `unregisterApiProviders`, `resolveApiProvider`, `stream`, and
  `streamSimple`;
- `packages/ai/src/api/lazy.ts::lazyApi`;
- `packages/ai/src/providers/faux.ts` deferred fetch/cancel implementation.

This wider source walk was necessary because the candidate's Layer-10 section treated
`types.ts::ProviderStreams` plus only `models.ts::createProvider/apiFor` as the complete provider
abstraction. It is not complete at the pinned revision.

## Prior finding closure ledger

| Finding | Final-review result |
|---|---|
| `L10-R001` | **CLOSED at this exact candidate.** `stream` and `streamSimple` are now separate rows with coherent current dispositions. |
| `L10-R002` | **CLOSED narrowly for the prior bundling defect.** `AI-029` and `AI-030` are separate subjects. New Pi-source evidence below exposes a different incompleteness in `AI-030`; it is recorded as `L10-R005`, not silently folded back into the old finding. |
| `L10-R003` | **OPEN Rust-only implementation defect.** Current Rust still permits eager `AdapterStartError` after resolved adapter invocation. This is accurately disclosed and is not repaired in review mode. |
| `L10-R004` | **CLOSED narrowly for the prior schema/reference/owner-observation defects.** Conditional `reject_message`, handle references, pre-flight validation, and exactly-one count growth are present. The separate fixed-cap runner defect below is new `L10-R007`. |
| `C10-C005` | **CLOSED at this exact candidate.** Python withdrawal ownership is per registration call through a fresh token; same-object double registration and idempotent withdrawal are covered. |

## Requirement and disposition audit

### `AI-012` — never-raises stream boundary

The shared rule remains Pi-grounded: after a resolved provider stream function is invoked,
expected request/provider/model/runtime failures settle in the returned stream. Python satisfies
the represented adapter-failure witness. Current Rust's separate eager adapter-start failure is
correctly disclosed as `L10-R003`.

**Result:** PASS as a shared rule; Rust implementation remains pending.

### `AI-028` — `stream`

The row now covers one semantic operation and uses `adopted` coherently. The mapping from Pi's
`(model, context, options?)` call to Minion's typed `Request` is language-neutral. The canonical
adapter-detected failure scenario reaches the real service/adapter seam.

**Result:** PASS.

### `AI-031` — `streamSimple`

The row accurately recognizes `streamSimple` as required in pinned Pi and does not cite fabricated
current evidence. Its `deferred parity` closure criterion requires an externally invocable Layer-11
operation, not merely internal translation code.

**Result:** PASS for the declared defer.

### `AI-029` — resolution and unresolved identity

The row consistently records Minion's eager full-identity lookup as an intentional divergence from
the selected `createProvider/apiFor/dispatch` path. Python and current Rust both implement the
Minion rule.

However, pinned Pi exposes more than this one resolution path: `compat.ts` has its own public API
provider registry and eager `resolveApiProvider` boundary. That omission becomes material in
`AI-030`, whose claimed absence of any Pi registry analogue is false.

**Result:** PASS for its narrow written subject, subject to `L10-R005` repairing the complete
registry/dispatch authority map.

### `AI-030` — registration, replacement, withdrawal, introspection

The Minion rule itself is clear and independently implementable: full-identity registration,
last-write replacement, per-call repeatable withdrawal handles, stale-handle safety, and unordered
current-model introspection.

Its Pi basis and disposition are not correct. The row and spec repeatedly state that Pi has no
registration/withdrawal/introspection concept. Pinned Pi exposes two directly relevant public
registries:

1. `MutableModels.setProvider/deleteProvider/clearProviders` with
   `getProviders/getProvider/getModels/getModel`; and
2. `compat.registerApiProvider/getApiProvider/getApiProviders/unregisterApiProviders`, including
   last-write API replacement and source-scoped unregister.

The Minion design may still intentionally choose a flat full-model-identity registry and
per-registration handles, but the contract must first compare it to Pi's actual registries. It
must distinguish adopted behavior (for example last-write replacement and stale-owner safety)
from architectural differences (key granularity, whole-provider versus per-model replacement,
handle shape, and introspection shape). One `intentional divergence` row premised on “no Pi
analogue” cannot do that.

**Result:** FAIL — `L10-R005`.

## Canonical review

Six Layer-10 scenarios were discovered:

1. `llm-service-adapter-detected-failure-settles-in-band`
2. `llm-service-introspection-reflects-current-registrations`
3. `llm-service-registration-and-replacement`
4. `llm-service-resolve-ownership-survives-replacement`
5. `llm-service-same-fixture-two-handles`
6. `llm-service-withdrawal-does-not-remove-a-later-replacement`

The schema's operation shapes, handle grammar, conditional `reject_message`, identity triples,
and observation namespaces are language-neutral. `_validate_references` validates fixture
integrity rather than implementing registry behavior. Registration, withdrawal, resolution,
introspection, and stream settlement go through the real Python `LlmService`/`MockAdapter` seam.
The fixed owner detector snapshots request counts before dispatch and rejects zero/multiple growth.

One new runner defect remains: `_build_adapter()` scripts exactly eight identical responses for
every fixture. The schema has no eight-call limit, and `behavior: ok` describes the adapter's
behavior rather than “ok for eight calls, then error.” Therefore a schema-valid ninth call is
silently converted into MockAdapter's exhausted-script error by runner provisioning. This is an
observable runner-created semantic cap, not production `LlmService` behavior.

**Result:** FAIL — `L10-R007`.

## Existing Rust architecture and implementability

Current certified Rust has a strict typed `ModelIdentity`, typed `LlmRequest`, `LlmAdapter`,
`AssistantStream`, and `LlmService`. It can implement the corrected language-neutral contract
idiomatically:

- remove `AdapterStartError` as an expected operational channel and represent such failures in
  the returned stream (`L10-R003`);
- add replacement/withdrawal/introspection using a typed registration handle or another
  repeat-callable mechanism without copying Python's token representation;
- preserve the existing no-lock-across-adapter-call design;
- implement any explicitly deferred provider operations later through typed Rust APIs.

No lower-layer Rust redesign is required. But Rust cannot implement a Pi-grounded Layer-10
registry contract independently while the shared artifacts deny the pinned source registries and
leave their relationship to Minion unresolved.

## New findings

### `L10-R005` — incomplete/incorrect Pi registry authority map

**Classification:** `CONTRACT_ASSURANCE_DEFECT` — blocking.

**Pi/source basis:**

- `packages/ai/src/models.ts:225-230,269-291` exposes mutable provider registration,
  replacement, deletion, clearing, and introspection.
- `packages/ai/src/compat.ts:76-163` exposes mutable API-provider registration, lookup,
  introspection, source-scoped unregister, and faux-provider registration.

**Minimal discriminating witness:**

```text
Pinned Pi:
    createModels()
    setProvider(A: id=p, models=[alpha,beta])
    setProvider(B: id=p, models=[alpha])
    getModels(p) -> [alpha]
    deleteProvider(p)
    getModels(p) -> []

Candidate Minion:
    register(A: provider=p, models=[alpha,beta])
    register(B: provider=p, models=[alpha])
    models() -> [p/alpha from B, p/beta from A]
```

The pinned-Pi half was executed directly against the pinned checkout and produced exactly
`[alpha,beta] -> [alpha] -> []`.

**Why discriminating:** Pi does have a runtime registration surface, and its whole-provider
replacement granularity differs observably from Minion's per-full-identity replacement. Pi also
has an API-provider registry even closer to Minion's adapter seam. The candidate's “no analogue”
premise prevents a correct adopted/diverged mapping.

**Required remediation:** re-audit both pinned registries; repair spec, manifest, canonical notes,
and assurance; split adopted semantics from Minion-only mechanics into coherent dispositions.
If an observable divergence remains after the truthful mapping, obtain the governance approval
required by workflow §11.7 rather than inferring it from the current implementation.

### `L10-R006` — optional deferred provider operations have no disposition

**Classification:** `CONTRACT_ASSURANCE_DEFECT` — blocking.

**Pi/source basis:** `ProviderStreams.fetchDeferred?` and `cancelDeferred?`, the public
`Provider`/`Models.fetchDeferred` and `cancelDeferred` delegation, `lazyApi` capability handling,
and the pinned faux provider's concrete implementations.

**Candidate state:** the spec and `AI-028` mention these operations only to contrast their
optionality with required `stream`/`streamSimple`. No manifest row adopts, defers, or intentionally
diverges them, despite the manifest's own rule that every Pi-visible surface receives a
disposition. `AI-009` covers only `DeferredHandle` vocabulary, not either operation.

**Required remediation:** add explicit, single-subject disposition(s), owner layer, closure
criteria, and evidence status for deferred fetch and cancel. Do not count handle vocabulary as
behavioral coverage.

### `L10-R007` — canonical runner injects an undocumented eight-call cap

**Classification:** `CONTRACT_ASSURANCE_DEFECT` — blocking.

**Minimal executable witness:** a schema-valid `llm_service` document with one `behavior: ok`
adapter, one registration, and nine named stream steps for the same identity.

```text
schema validation     0 errors
candidate observed    [ok, ok, ok, ok, ok, ok, ok, ok, error]
ninth error_message   mock script exhausted after 8 response(s); the scenario asked for one more
expected              nine ok settlements
```

**Why discriminating:** the ninth error comes solely from `_build_adapter()`'s hard-coded
`[response] * 8`, not from the schema, scenario, `LlmService`, or adapter behavior declaration.
Thus the runner changes valid canonical semantics instead of merely dispatching them.

**Required remediation:** provision scripted responses without an undocumented numeric cap (for
example, based on the document's maximum possible observations, without predicting which adapter
the service will choose), and add the exact greater-than-eight witness as permanent runner/schema
evidence.

## Fresh gates and probes

Against the exact candidate:

```text
full Python suite                         1161 passed, 19 xfailed, 0 failed
coverage                                  100.00%
conformance suite                         327 passed, 19 xfailed, 0 failed
ruff                                      PASS
mypy                                      PASS, 58 source files
manifest                                  83 rows / 83 unique ids; dispositions parse
targeted current Rust LLM tests           6 passed
schema-valid nine-stream runner probe     FAILS semantically on call 9 (L10-R007)
pinned-Pi Models registration probe       [alpha,beta] -> [alpha] -> []
```

Green existing suites do not override the three new contract/evidence defects.

## Cross-layer impact

- Layers 01–09: no observable contract delta is presently required.
- Layer 02 LLM vocabulary/stream settlement: no reopen is required; Layer 10 consumes it.
- Layer 10 shared/Python: must reopen narrowly for `L10-R005`–`L10-R007`.
- Rust Layer 10: remains blocked/not implemented; `L10-R003` is still its known local repair.
- Layer 11: not started.

## Final verdict

```text
shared Layer-10 contract    REJECTED @ code 4d63349d / docs 57edf9f
Python Layer 10             REOPENED
Rust Layer 10               BLOCKED / NOT_IMPLEMENTED
Layer 10 cross-language     NOT CLOSED
Layer 11                    NOT STARTED

PI_BEHAVIOR_UNCERTAIN       none
PI_PARITY_DEFECT             L10-R003 (current Rust only; disclosed implementation target)
CONTRACT_ASSURANCE_DEFECT   L10-R005, L10-R006, L10-R007
PARITY_CONSTRAINED_RISK     none
```

This is the third rejected Layer-10 contract-review cycle, so workflow §11.8's automatic trigger
requires the new surface to return to `CONTRACT_CONVERGENCE`. The candidate PRs must not merge.

## Next action

The shared/Python owner should produce a convergence characterization/checkpoint for
`L10-R005`–`L10-R007`, grounded in both pinned Pi registries and the optional deferred operations,
with the nine-call runner witness binding. Do not repair Rust or start Layer 11. Any changed
candidate SHA requires renewed targeted closure followed by another final exact-SHA review.
