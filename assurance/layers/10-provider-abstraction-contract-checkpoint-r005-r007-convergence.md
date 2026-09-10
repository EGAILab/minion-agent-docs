# Layer 10 — L10-R005/R006/R007 contract convergence checkpoint

**Convergence trigger check (`agent-workflow.md` §11.8, mandatory):** Layer 10 has now accumulated
three rejected contract reviews (PASS-1 rejection, PASS-2 targeted rejection, and this final
complete review's own rejection) -- the second of the two independent `§11.8` trigger conditions
("layer accumulates three rejected contract reviews") is met regardless of whether any single
finding ID repeats, per the final review's own explicit statement: "This is the third rejected
Layer-10 contract-review cycle, so workflow §11.8's automatic trigger requires the new surface to
return to `CONTRACT_CONVERGENCE`." Issue #19 already reflects `STATUS: CONTRACT_CONVERGENCE`,
`NEXT_OWNER: Claude`. This document is the first characterization pass for `L10-R005`/`L10-R006`/
`L10-R007` (`§11.8.3`), produced by the shared/Python owner per the final review's own `NEXT_ACTION`
rather than by the discovering reviewer, matching this project's established practice for this
layer's two prior convergence cycles.

**Review target this checkpoint responds to:** `minion-agent-docs/assurance/layers/
10-provider-abstraction-final-contract-review.md`, review commit
`e8a2d395dc4697eb65b42958eb043c9c7eede185`, docs PR #47, reviewing code PR #20 @
`4d63349d85d517359545b94ce0937548d3fb7314` / docs PR #45 @ `57edf9fd08e9b7411d32177f5991756182dd6a7a`
(the PASS-3 candidate that closed `L10-R001`/`L10-R002`/`L10-R004`/`C10-C005`).

## OPEN FINDINGS

- **`L10-R005`** (`CONTRACT_ASSURANCE_DEFECT`, blocking): `AI-030`'s own "Pi has NO adapter-
  registration concept at all" premise is false. Pinned Pi exposes two real, currently-live
  registries this row never compared itself against.
- **`L10-R006`** (`CONTRACT_ASSURANCE_DEFECT`, blocking): `ProviderStreams.fetchDeferred?`/
  `cancelDeferred?` are mentioned only to contrast their optionality against required `stream`/
  `streamSimple`; no manifest row gives either operation its own disposition. `AI-009` covers only
  `DeferredHandle` vocabulary, not either operation's own behavior.
- **`L10-R007`** (`CONTRACT_ASSURANCE_DEFECT`, blocking): `llm_service_runner.py::_build_adapter()`
  hard-codes `script = [response] * 8`; a schema-valid ninth `stream` call against the same
  identity is silently converted into `MockAdapter`'s own exhausted-script error by runner
  provisioning, not by anything the scenario document, schema, or `LlmService` actually declares.
- **`L10-R003`** (`PI_PARITY_DEFECT`, current Rust production only): unchanged, out of scope,
  explicitly not addressed by this checkpoint or the pass it leads to.

## PI SYMBOLS / TESTS AUDITED (this pass, independently re-read against the pinned checkout)

Pinned Pi is available locally at the exact pinned revision (`ref-repos/pi`, `git log -1` confirms
HEAD `b7bb00b`). Read directly, not taken from the review's own prose:

- `packages/ai/src/models.ts:97-131` (`Provider<TApi>` interface), `:159-230` (`Models`/
  `MutableModels` interfaces: `getProviders`/`getProvider`/`getModels`/`getModel`/`setProvider`/
  `deleteProvider`/`clearProviders`), `:254-329` (`ModelsImpl`'s own concrete `setProvider`/
  `deleteProvider`/`clearProviders`/`getModels`/`getModel`), `:762-862` (`createProvider`/`apiFor`/
  `dispatch`, re-confirming `AI-029`'s own already-correct characterization is unaffected).
- `packages/ai/src/compat.ts:1-11` (module docstring, verbatim: "Temporary compatibility entrypoint
  preserving the old global pi-ai API surface... This module is deleted with the coding-agent
  ModelManager migration."), `:83-158` (`ApiProvider` interface, `apiProviderRegistry` module-level
  `Map`, `registerApiProvider`/`getApiProvider`/`getApiProviders`/`unregisterApiProviders`/
  `clearApiProviders`), `:242-248` (`resolveApiProvider`, the eager-throw-on-missing-provider
  lookup `stream()`/`streamSimple()` use internally).
- `packages/ai/src/types.ts:264-281` (`ProviderStreams`, re-confirming `stream`/`streamSimple`
  required, `fetchDeferred?`/`cancelDeferred?` optional -- unchanged from `AI-028`/`AI-031`),
  `:227-236` (`DeferredFetchOptions`/`DeferredCancelOptions`), `:409-419` (`DeferredHandle`,
  already `AI-009`'s own certified vocabulary, unaffected).
- `packages/ai/src/api/lazy.ts:63-98` (`lazyApi`/`LazyApiCapabilities`): `fetchDeferred`/
  `cancelDeferred` are CAPABILITY-gated per wire-protocol module, added to the returned
  `ProviderStreams` object only when the underlying module declares it supports them -- the same
  per-module, wire-protocol-specific shape `streamSimple` already has under `AI-031`.
- `packages/ai/src/providers/faux.ts:567-642` (`fetchDeferred`/`cancelDeferred` reference
  implementation): `fetchDeferred` returns a NEW `AssistantMessageEventStream`; an unknown or
  cancelled handle settles as an in-band `error` event/terminal (never a thrown exception) --
  the SAME never-raises boundary `AI-012`/`AI-028` already require for `stream`. `cancelDeferred`
  is `Promise<void>`, best-effort: an unknown handle (`deferredResponses.get(handle.id)` returns
  `undefined`) is silently a no-op, not an error -- idempotent by construction, not merely by
  convention.
- Minion side: `minion-agent-python/src/minion_agent/llm/messages.py::DeferredHandle` (already
  certified, `AI-009`, vocabulary only); `llm/service.py::Adapter`/`LlmService` (no
  `fetch_deferred`/`cancel_deferred` method of any kind exists); `tests/conformance/
  llm_service_runner.py::_build_adapter` (the `[response] * 8` cap).

## OBSERVABLE RULES

**`L10-R005`.** Pinned Pi has two real, currently-live (non-deprecated `MutableModels`;
deprecated-but-still-live `compat.ts`) dynamic registries, with DIFFERENT granularity and
replacement semantics from each other AND from Minion's own `LlmService`:

1. `MutableModels.setProvider(provider)` is keyed by `provider.id` alone (no model/api
   component). It is a WHOLE-PROVIDER upsert: the new `Provider` object's own `getModels()`
   entirely REPLACES whatever that provider id previously exposed -- there is no per-model
   merge. `deleteProvider(id)`/`clearProviders()` remove at the same whole-provider granularity.
   `getProviders`/`getProvider`/`getModels`/`getModel` are the introspection surface, and (per
   `ModelsImpl.getModels`, `models.ts:294-314`) a provider whose own `getModels()` throws is
   silently treated as contributing zero models (best-effort), not a validation error.
2. `compat.ts`'s `registerApiProvider(provider, sourceId?)` is keyed by `provider.api` (a single
   api string, module-level `Map`). It is also last-write-wins (`Map.set`), so ANY later
   registration for the same api string replaces the prior one, regardless of who registered it.
   `unregisterApiProviders(sourceId)` removes EVERY entry whose own recorded `sourceId` matches
   the given tag -- a bulk, tag-scoped removal; two registrations sharing one `sourceId` are
   indistinguishable and removed together. This module is Pi's own explicitly TEMPORARY
   compatibility surface ("deleted with the coding-agent ModelManager migration") -- live in the
   pinned revision, but Pi's own stated direction is away from it, not toward it.

Neither registry matches Minion's own `LlmService`: Minion keys per FULL `(provider, model, api)`
identity (finer-grained than either Pi registry, both of which key on a single string), replaces
per KEY rather than per whole provider/api (so two Minion adapters sharing a `provider` id but
declaring different models COEXIST, unlike `MutableModels.setProvider`'s wholesale swap), and
scopes withdrawal per INDIVIDUAL REGISTRATION CALL via an opaque handle (`AI-030`/`C10-C005`),
the opposite granularity from `compat.ts`'s shared-tag bulk unregister. The rule this checkpoint
proposes: Minion's registry remains a genuine, disclosed Minion architectural choice with NO
directly-adopted Pi registry -- but that conclusion must now rest on an HONEST comparison against
both real Pi registries, not the previous row's false "no analogue at all" premise.

**`L10-R006`.** `fetchDeferred`/`cancelDeferred` are Pi-required-when-present, capability-gated,
per-wire-protocol-module operations -- the SAME status class as `streamSimple` (`AI-031`): nothing
generic to specify at Layer 10's own provider-agnostic abstraction level until a real provider
(Layer 11) exists to implement one. `fetchDeferred` inherits the SAME never-raises boundary
`stream` already has (`AI-012`); `cancelDeferred` is a separate, best-effort, idempotent-for-
unknown-handles void operation with no returned stream at all. Both operate on `AI-009`'s own
already-certified `DeferredHandle` vocabulary -- this checkpoint proposes a NEW row for the
BEHAVIOR these two operations require, not a change to `AI-009` itself.

**`L10-R007`.** The canonical `llm_service` schema and grammar impose NO limit on how many times a
scenario may `stream` through the same registered identity; `behavior: ok` describes the adapter's
OWN behavior (always settles successfully), not a bounded number of successful calls. The runner's
own response provisioning is pure test-harness mechanics and must never silently narrow what a
schema-valid document can express.

## BEHAVIOR MATRIX

| Dimension | Pi `MutableModels` | Pi `compat.ts` registry | Minion `LlmService` (current) |
|---|---|---|---|
| Registration key | `provider.id` | `provider.api` | `(provider, model, api)` full identity |
| Replacement granularity | whole provider (all models swapped atomically) | whole api entry | per full-identity key only |
| Removal | `deleteProvider(id)` / `clearProviders()`, whole-provider | `unregisterApiProviders(sourceId)`, bulk tag-scoped | per-registration-call handle, `AI-030`/`C10-C005` |
| Removal of a stale/superseded entry | not applicable (no per-call handle concept) | not applicable (tag-scoped, not call-scoped) | safe no-op (`AI-030`) |
| Repeat-removal idempotency | `deleteProvider` on an absent id is a silent no-op | `unregisterApiProviders` on an unknown tag is a silent no-op | safe no-op (`AI-030`/`C10-C005`, binding) |
| Introspection | `getProviders`/`getProvider`/`getModels`/`getModel` | `getApiProvider`/`getApiProviders` | `models()` |
| Deprecation status | current, forward architecture | explicitly temporary, scheduled for deletion | N/A (Minion-only) |
| `fetchDeferred`/`cancelDeferred` | `Models.fetchDeferred`/`cancelDeferred` delegate to `Provider`; `Provider.fetchDeferred`/`cancelDeferred` synthesized by `createProvider` only when an underlying `ProviderStreams` module declares them | n/a (not part of this registry's own surface) | absent entirely -- no `Adapter` method, no `LlmService` method |

## MINIMAL EXECUTABLE WITNESSES

**`L10-R005`** (the final review's own pinned-Pi probe, independently re-executable against
`ref-repos/pi`):

```text
createModels(); setProvider(A: id=p, models=[alpha,beta]); setProvider(B: id=p, models=[alpha])
getModels(p) -> [alpha]              # whole-provider replacement, beta is GONE, not merged
deleteProvider(p); getModels(p) -> []
```

versus Minion's own current, already-certified `test_a_later_adapter_replaces_an_earlier_one_for_
the_same_model`-style behavior at the SAME nominal scenario shape (register `A: provider=p,
models=[alpha,beta]`; register `B: provider=p, models=[alpha]`; `models()` -> `[p/alpha from B,
p/beta from A]`, beta from A SURVIVES because it is keyed independently of alpha). This checkpoint
does not propose changing Minion's own observed behavior here -- it proposes correcting the row's
own claim about what Pi does, and the row's own comparison against it.

**`L10-R006`** (proposed, to be added as permanent evidence once a Layer-11 provider exists to
exercise it -- Layer 10 itself has no concrete implementation to test against; see IMPLEMENTATION
CONSTRAINTS): none executable at Layer 10 today. The witness this row commits to for whichever
future pass closes it: a Layer-11 adapter that supports deferred responses exposes a callable
`fetch_deferred`/`cancel_deferred` (or equivalent) matching `fetchDeferred`'s own never-raises
boundary and `cancelDeferred`'s own best-effort/idempotent-unknown-handle behavior, both
independently observable, neither merely internal option-translation plumbing.

**`L10-R007`** (the final review's own witness, reproduced): a `llm_service` document with one
`behavior: ok` adapter, one registration, and nine `stream` steps against the same identity.
Schema validates with 0 errors; the candidate runner currently settles calls 1-8 as `ok` and call 9
as `error` (`"mock script exhausted after 8 response(s); the scenario asked for one more"`),
solely because `_build_adapter()` provisions exactly 8 scripted responses regardless of how many
calls the scenario actually makes.

## CURRENT CANDIDATE FAILURES

- `pi-parity-manifest.yaml::AI-030` and `spec/llm.md`'s own `AI-030` paragraph both assert Pi has
  no registration/withdrawal/introspection concept at all -- refuted directly by `MutableModels`
  and `compat.ts` above.
- No manifest row and no `spec/llm.md` paragraph disposes `fetchDeferred`/`cancelDeferred` at all.
- `llm_service_runner.py::_build_adapter` fails the nine-call witness above (reproducible today
  against the exact PASS-3 candidate).

## SPEC / MANIFEST / CONFORMANCE DELTAS NEEDED (proposed, not yet applied)

**`pi-parity-manifest.yaml::AI-030`** — `pi:` field corrected to cite BOTH
`packages/ai/src/models.ts::MutableModels` (`225-230,269-291`) and
`packages/ai/src/compat.ts::ApiProvider registry` (`76-163`). `rule:` rewritten to state the
behavior-matrix comparison above (both registries' own granularity/replacement/removal semantics,
including `compat.ts`'s own "temporary, deleted with the ModelManager migration" status) and
conclude Minion's registry remains an intentional divergence because its OWN granularity and
withdrawal-scoping genuinely differ from BOTH real Pi registries, not because none exists.
`disposition:` unchanged (`intentional divergence`) pending the governance step below.

**New `pi-parity-manifest.yaml::AI-032`** — `fetchDeferred`/`cancelDeferred`, `disposition:
deferred parity`, mirroring `AI-031`'s own shape: cites `types.ts::ProviderStreams.fetchDeferred?/
cancelDeferred?`, `models.ts::Models.fetchDeferred/cancelDeferred`, `api/lazy.ts::LazyApiCapabilities`,
`providers/faux.ts` reference behavior; explicit closure criterion requiring an externally
invocable Layer-11 operation for each, matching the never-raises (`fetchDeferred`) and best-effort-
idempotent (`cancelDeferred`) rules above; explicitly notes `AI-009` already covers the
`DeferredHandle` VOCABULARY this row's own BEHAVIOR builds on, so as not to re-litigate that row.

**`spec/llm.md`** — mirrors both corrections: the `AI-030` paragraph rewritten to match the
manifest, plus a new `fetchDeferred`/`cancelDeferred` paragraph mirroring `AI-031`'s own
`streamSimple` paragraph shape.

**`conformance/agent/`** — no schema change required (the six existing `llm_service` scenario
files remain valid; `L10-R005`/`L10-R006` are pure disposition/documentation corrections with no
observable Python behavior change). New permanent regression evidence for `L10-R007`: a scenario
with more than eight `stream` steps against one identity, all expecting `ok`.

**`minion-agent-python/tests/conformance/llm_service_runner.py::_build_adapter`** — remove the
hard-coded `[response] * 8`. Proposed fix: size each fixture's own script to the scenario
document's own total possible observation count (every `steps[].stream` entry plus every
`queries[].resolve` entry -- each is at most one call to some ONE adapter, so sizing EVERY
fixture's own script to that same total is a safe, non-predictive upper bound, exactly matching
the final review's own guidance: "without predicting which adapter the service will choose").

## IMPLEMENTATION CONSTRAINTS

- `L10-R005`'s remediation is DOCUMENTARY/disposition-only -- no Python source file changes, no
  observable `LlmService` behavior changes. Any apparent temptation to make `register`/`withdraw`
  MATCH one of the two real Pi registries more closely is explicitly OUT OF SCOPE for this
  checkpoint: the final review's own required remediation is "re-audit... repair spec, manifest,
  canonical notes, and assurance; split adopted semantics from Minion-only mechanics into coherent
  dispositions" -- it does not ask for a redesign, and this checkpoint does not propose one.
- `L10-R005` requires `agent-workflow.md` §11.7 owner governance approval before this checkpoint
  can become `AGREED FOR IMPLEMENTATION`: the final review's own text states "If an observable
  divergence remains after the truthful mapping, obtain the governance approval required by
  workflow §11.7 rather than inferring it from the current implementation." This checkpoint
  concludes divergence DOES remain after the truthful mapping (see BEHAVIOR MATRIX), so this is a
  live governance item, not a formality -- see NEXT_ACTION below.
- `L10-R006`'s remediation is ALSO documentary/disposition-only at this layer -- Layer 10 has no
  concrete wire-protocol implementation to attach real `fetch_deferred`/`cancel_deferred` behavior
  to yet (matching `AI-031`'s own already-accepted reasoning for `streamSimple`). Do not build
  speculative Python plumbing for an operation with no Layer-11 provider to exercise it.
- `L10-R007`'s fix touches only `llm_service_runner.py` (test/tooling code, not `src/`) plus one
  new canonical scenario. No production `LlmService`/`Adapter` source file changes.
- Rust: unaffected. `L10-R005`/`L10-R006` are shared-contract/documentation corrections; `L10-R007`
  is Python-only test tooling. None of the three requires or implies any Rust change.

## OUT-OF-SCOPE / DEFERRED BEHAVIOR

- `L10-R003` (current Rust `AdapterStartError`): unchanged, not addressed here.
- Any redesign of Minion's own registry to more closely match either Pi registry: not proposed;
  see IMPLEMENTATION CONSTRAINTS.
- Actual `fetchDeferred`/`cancelDeferred` Python implementation: Layer 11's own future obligation,
  same as `streamSimple` (`AI-031`).
- Layer 11 (Real providers): not started.

---

## CONVERGENCE CONTRACT

    PROPOSED -- AWAITING INDEPENDENT AGREEMENT

OPEN FINDINGS
    L10-R005
    L10-R006
    L10-R007

ACCEPTANCE WITNESSES
    L10-R005: the pinned-Pi MutableModels probe above (re-executable against ref-repos/pi),
      the corrected AI-030 rule: text itself (independently checkable against both cited Pi source
      ranges), owner governance sign-off recorded on issue #19 or this checkpoint.
    L10-R006: new AI-032 manifest row and spec/llm.md paragraph, checkable against the cited Pi
      source ranges; no executable evidence exists or is claimed at Layer 10 (deferred to Layer 11).
    L10-R007: the greater-than-eight-call canonical scenario (new), llm_service_runner.py's own
      fixed-provisioning fix, revert-and-confirm against the exact PASS-3 candidate.

NORMATIVE DELTAS
    minion-agent/pi-parity-manifest.yaml (AI-030 corrected, new AI-032)
    minion-agent-docs/spec/llm.md (AI-030 paragraph corrected, new fetchDeferred/cancelDeferred
      paragraph)
    minion-agent/conformance/agent/ (one new >8-call scenario)
    minion-agent-python/tests/conformance/llm_service_runner.py (_build_adapter provisioning fix)

NEXT_OWNER
    Codex

NEXT_ACTION
    Independent challenge (§11.8.4) of this characterization: confirm the Pi source mapping above
    (MutableModels/compat.ts granularity comparison, fetchDeferred/cancelDeferred capability-gated
    status, the >8-call witness design) is correct and complete enough to implement once. Separately
    and explicitly: L10-R005 needs agent-workflow.md §11.7 owner governance sign-off on continuing
    Minion's own intentional divergence now that the comparison is grounded in both real Pi
    registries -- this is being raised to the repository owner directly alongside this checkpoint;
    record the owner's decision on issue #19 once given, independent of the Codex challenge pass.
