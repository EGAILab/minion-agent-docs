# Layer 10 — final complete independent Rust contract re-review

**Review mode:** mandatory workflow §11.8.8 final complete exact-SHA contract review.

## Exact review target

- code PR #20: `ef1d2b033deced9cbc0396467eeda2f3e3454008`
- docs PR #45: `038fc5488e8b7473654f37ec04d49d7a5881c622`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- convergence agreement: docs PR #47 at
  `4a4012b14541dabc98d3ccfc0faedd363099436e`
- targeted convergence review: docs PR #47 at
  `ae599ba9660907593ac9d020bdeca1ca57d01fe2`

Both candidate PRs were fetched before review. Their remote heads matched coordination issue #19,
both were Ready for Review, open, unmerged, and mergeable. The verdict applies only to the exact
pair above. Neither candidate branch, Rust production, nor Layer 11 was modified.

## Independent Pi audit

The review followed the required order: pinned Pi, normative spec, manifest, canonical evidence,
certified Rust architecture, assurance, and Python only as secondary implementation evidence.

Pinned Pi source independently re-read:

- `packages/ai/src/types.ts`: `ProviderStreams`, `StreamFunction`, `SimpleStreamOptions`,
  `DeferredFetchOptions`, `DeferredCancelOptions`, and `DeferredHandle`;
- `packages/ai/src/models.ts`: `Provider`, `Models`, `MutableModels`, `ModelsImpl.stream`,
  `streamSimple`, `fetchDeferred`, `cancelDeferred`, `createProvider`, `apiFor`, and `dispatch`;
- `packages/ai/src/api/lazy.ts`: `LazyApiCapabilities` and deferred capability wrappers;
- `packages/ai/src/compat.ts`: `ApiProvider`, its registry operations, `resolveApiProvider`, and
  `registerFauxProvider`;
- `packages/ai/src/providers/faux.ts`: `FauxProviderRegistration`, ordinary stream behavior, and
  deferred fetch/cancel behavior.

The resulting current spec accurately distinguishes Pi's required `stream`/`streamSimple`, optional
deferred capabilities, Models-facing error boundaries, three registry surfaces, and Minion's
owner-approved full-identity registry divergence.

## Complete finding ledger

| Finding | Final result at this exact candidate |
|---|---|
| `L10-R001` | **CLOSED.** Required `streamSimple` is no longer called optional; `AI-031` records explicit Layer-11 deferred parity with a public-callable closure criterion. |
| `L10-R002` | **CLOSED.** `AI-028`, `AI-029`, `AI-030`, and `AI-031` each have a coherent subject and disposition. |
| `L10-R003` | **OPEN RUST-ONLY IMPLEMENTATION DEFECT, accurately disclosed.** Current Rust exposes eager `AdapterStartError` after adapter invocation. This is the implementation target, not a shared-contract blocker. |
| `L10-R004` | **CLOSED.** Direct canonical evidence, conditional schema behavior, handle grammar, reference validation, and exact owner observation all use the real production seam. |
| `C10-C005` | **CLOSED.** Python ownership is per registration call and repeated/stale withdrawal is an idempotent no-op. |
| `L10-R005` | **CLOSED semantically.** `AI-030` and the spec now compare all three Pi surfaces accurately, include faux per-call unregister precedent and tag-dependent removal, and record scoped owner governance. |
| `L10-R006` | **CLOSED.** `AI-032` explicitly defers all four observable deferred-operation layers without fabricated current evidence. |
| `L10-R007` | **CLOSED behaviorally.** Scenario-derived provisioning removes the runner's fixed eight-call cap and the nine-call scenario passes. |
| `L10-R008` | **NEW — OPEN.** Layer-10 manifest evidence entries are structurally malformed and the L10-R007 canonical witness is not linked from a requirement row. |

## Requirement/disposition audit

### `AI-012` — never-raises provider stream

The adopted shared rule remains correct: after a resolved stream function is invoked, expected
operational failures settle in the returned stream. Python's returned-stream settlement is
certified. Rust's eager adapter-start result channel is correctly isolated as `L10-R003`.

**Result:** PASS as a shared rule; Rust repair pending.

### `AI-028` — `stream`

The row covers only Pi's required `stream` operation, maps typed request fields without prescribing
Python structure, and cites real in-band settlement evidence. `adopted` is coherent.

**Result:** PASS semantically; evidence-link defect noted under `L10-R008`.

### `AI-031` — `streamSimple`

Pinned Pi requires the operation. The explicit defer to Layer 11 is defensible because translation
is provider/protocol specific, and the closure criterion requires an externally callable
equivalent rather than internal translation plumbing. It cites no placeholder as satisfied.

**Result:** PASS for deferred parity.

### `AI-032` — `fetchDeferred` / `cancelDeferred`

The row accurately distinguishes:

1. low-level stream versus void return shapes;
2. high-level represented fetch failure versus eager cancel rejection;
3. mixed-API per-model capability selection with the same asymmetry; and
4. supported faux unknown/cancelled-handle behavior.

The closure criterion is external and observable, names Layer 11, and does not confuse
`AI-009`'s handle vocabulary with behavior.

**Result:** PASS for deferred parity.

### `AI-029` — resolution / unresolvable identity

The row accurately records Minion's eager full-identity miss as an intentional divergence from
Pi's two-level provider/API selection and in-band wrong-API result. Python and current Rust already
implement the selected Minion boundary. Adapter-start behavior remains separately owned by
`AI-028`/`L10-R003`.

**Result:** PASS semantically; one malformed evidence value under `L10-R008`.

### `AI-030` — registration / replacement / withdrawal / introspection

The current rule now truthfully compares:

- `MutableModels` whole-provider keying and replacement;
- compat's API-keyed, tag-scoped temporary registry; and
- `registerFauxProvider`'s freshly generated, non-collision-checked per-call tag and returned
  `unregister()` precedent.

It distinguishes tag-dependent stale removal, Minion's generic per-call ownership, full-identity
composition, idempotent withdrawal, and narrower introspection. The owner approval is recorded and
properly scoped. The spec and manifest no longer deny analogous Pi registration/introspection.

**Result:** PASS semantically; one malformed evidence value under `L10-R008`.

## Canonical review

Seven direct Layer-10 scenarios exist:

1. `llm-service-adapter-detected-failure-settles-in-band`
2. `llm-service-introspection-reflects-current-registrations`
3. `llm-service-more-than-eight-calls-settle-ok`
4. `llm-service-registration-and-replacement`
5. `llm-service-resolve-ownership-survives-replacement`
6. `llm-service-same-fixture-two-handles`
7. `llm-service-withdrawal-does-not-remove-a-later-replacement`

The schema enforces one operation per step, behavior-dependent `reject_message`, strict identity
shape, and unambiguous observation variants. The shared semantic validator rejects duplicate
fixtures/handles/observations, unknown references, and dangling expectations while explicitly
allowing repeat withdrawal and unasserted setup observations.

The runner is thin: it constructs real `MockAdapter` instances, calls real `LlmService` methods,
uses returned withdrawal handles, drains real streams, and observes request-count growth. It does
not implement registration, resolution, replacement, withdrawal, or settlement. Its new maximum
possible call count is a non-predictive provisioning upper bound. All nine calls in the regression
scenario settle successfully.

**Result:** PASS behaviorally. Manifest traceability is incomplete under `L10-R008`.

## Existing Rust architecture and feasibility

Current Rust provides typed `ModelIdentity`, `LlmRequest`, `LlmAdapter`, `AssistantStream`,
`ScriptedAdapter`, and `LlmService`. An idiomatic Layer-10 implementation can:

- remove the expected eager adapter-start error channel and return a stream that settles failures;
- add per-registration ownership and repeatable idempotent withdrawal without copying Python's
  object token mechanism;
- expose current identity introspection;
- implement the direct canonical runner through real Rust service/adapter methods; and
- leave `streamSimple` and deferred operations explicitly pending for Layer 11.

The registry lock is already released before adapter code runs. No Runtime, Session, Tool, Agent,
or other certified lower-layer semantic redesign is required. Rust can implement the written rule
without reading Python control flow.

## Contract-quality answers

```text
runner simulates production registry/settlement semantics?    NO
runner imposes a hidden numeric call cap?                     NO
canonical grammar permits divergent operation interpretation? NO
Python workaround compensates for incomplete semantics?       NO
shared spec has two observable interpretations?               NO
owner-approved divergence accurately scoped?                  YES
deferred behavior has explicit owner/closure criterion?       YES
lower certified semantic layer must reopen?                   NO
Rust can implement independently and idiomatically?           YES
manifest evidence values structurally valid and complete?     NO (L10-R008)
```

## New finding

### `L10-R008` — malformed and incomplete Layer-10 manifest evidence

**Classification:** `CONTRACT_ASSURANCE_DEFECT` — blocking.

Parsing the current manifest with `yaml.safe_load` shows that two Layer-10 `tests:` entries are
YAML mappings, not evidence strings, because an unquoted `:` separates a key and value:

```text
AI-029 tests[1]  dict
    llm-service-resolve-ownership-survives-replacement.yaml (... query: ...)

AI-030 tests[7]  dict
    llm-service-same-fixture-two-handles.yaml (... witness: ...)
```

The current “84 rows / 84 unique IDs” audit does not validate evidence value types and therefore
reports success despite malformed traceability data. The same whole-manifest probe finds two
pre-existing `AG-007` entries with the same quoting defect. Correcting those two documentary values
does not reopen Layer 09 semantics, but a manifest-wide validator should detect them.

Additionally, the new `llm-service-more-than-eight-calls-settle-ok.yaml` acceptance witness appears
only in assurance prose; no requirement row's `tests:` list points to it. `AI-028` is the natural
owner because the scenario proves repeated successful calls through the adapter `stream` seam.

**Minimal reproduction:** parse the manifest and require every `tests` member to be a non-empty
string. Current result: four non-string members, including the two Layer-10 entries above.

**Narrow remediation:** quote/fold the malformed Layer-10 evidence entries as scalar strings; fix
the two pre-existing `AG-007` documentary entries or otherwise make the whole manifest pass the
same invariant; link the nine-call scenario from its owning Layer-10 requirement; and extend the
manifest validation gate to require `tests` to be a list of non-empty strings. No production,
canonical behavior, spec semantics, disposition, or owner-governance change is needed.

## Fresh evidence

```text
Python full suite                         1163 passed, 19 xfailed, 0 failed
coverage                                  100.00%
ruff                                      PASS
mypy                                      PASS, 58 source files
conformance                               329 passed, 19 xfailed, 0 failed
Layer-10 direct scenarios                 7 passed
Layer-10 runner validation                12 passed
current Rust targeted LLM tests           6 passed
manifest rows / unique IDs                84 / 84
manifest non-string tests entries         4 (AI-029, AI-030, AG-007 x2)
```

The green behavior suites do not override malformed/incomplete manifest evidence.

## Cross-layer impact

- Layers 01–08: no delta required.
- Layer 09: no semantic reopen; two pre-existing evidence strings need documentary quoting.
- Layer 10 shared/Python: one narrow assurance repair remains.
- Rust Layer 10: not implemented; `L10-R003` remains its known production repair target.
- Layer 11: not started.

## Verdict

```text
shared Layer-10 contract    REJECTED @ code ef1d2b0 / docs 038fc54
Python Layer 10             REOPENED FOR ASSURANCE ONLY
Rust Layer 10               BLOCKED / NOT_IMPLEMENTED
Layer 10 cross-language     NOT CLOSED
Layer 11                    NOT STARTED

PI_BEHAVIOR_UNCERTAIN       none
PI_PARITY_DEFECT             L10-R003 (current Rust only; disclosed implementation target)
CONTRACT_ASSURANCE_DEFECT   L10-R008
PARITY_CONSTRAINED_RISK     none
```

## Next action

Return to the shared/Python owner for the narrow manifest-evidence remediation under `L10-R008`.
Any changed candidate SHA requires another complete exact-SHA review. Do not implement Rust Layer
10 and do not start Layer 11.
