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

## REVISION 2 — remediates the independent §11.8.4 challenge of revision 1

The independent challenge of revision 1 (`10-provider-abstraction-contract-checkpoint-
r005-r007-challenge.md`, review commit `273951ad2b4a1bd6aa984b502a370b79935a0931`, docs PR #47):
**`CHANGES REQUIRED`**. `L10-R007` accepted outright, no challenge remains. Two findings against
this checkpoint's own Pi-source mapping:

- **`C10-D001`**: the registry comparison omitted `compat.ts::registerFauxProvider`'s own
  `FauxProviderRegistration.unregister()` -- a LIVE, direct per-registration-call unregistration
  analogue on the faux/mock provider surface (a fresh, unique `sourceId` generated PER CALL, closed
  over by that call's own returned `unregister()`), even though the underlying generic
  `unregisterApiProviders(sourceId)` primitive it is built on remains bulk tag-scoped. The behavior
  matrix's own "not applicable" entry for compat-registry stale removal was also wrong -- the
  outcome depends on tag identity (differing tags: stale removal is safe, matching Minion's own
  behavior; shared tags: the removal is a deliberate bulk/current-entry operation).
- **`C10-D002`**: the proposed `AI-032` conflated several distinct observable failure boundaries
  pinned Pi keeps separate: low-level `ProviderStreams.fetchDeferred?`/`cancelDeferred?` return
  shapes versus high-level `Models.fetchDeferred`/`cancelDeferred` behavior; a supported
  capability's own unknown/cancelled-handle outcome versus a MISSING provider/capability outcome;
  and `fetchDeferred`'s represented (in-band) error boundary versus `cancelDeferred`'s eager
  (thrown) one, including for mixed-API per-model capability selection.

Both findings were independently re-verified against `ref-repos/pi` at the pinned SHA before this
revision (not accepted on the challenge's own prose alone) -- see the updated `PI SYMBOLS`,
`OBSERVABLE RULES`, and `BEHAVIOR MATRIX` sections below, each marked where revision 2 changed
them. `L10-R007`'s own section is UNCHANGED from revision 1 (accepted, no revision needed). The
owner's `§11.7` governance decision for `L10-R005` (recorded below) is UNCHANGED and was
explicitly NOT re-litigated by the challenge -- these are documentary/mapping corrections to the
comparison the owner already approved, not a reopening of that approval.

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
  `clearApiProviders`), `:160-176` (**revision 2, `C10-D001`**: `registerFauxProvider(options)` --
  generates a fresh `sourceId` via `Math.random()...` PER CALL, registers through
  `registerApiProvider(..., sourceId)`, and returns a `FauxProviderRegistration` whose own
  `unregister()` closure calls `unregisterApiProviders(sourceId)` with THAT call's unique tag),
  `:242-248` (`resolveApiProvider`, the eager-throw-on-missing-provider lookup `stream()`/
  `streamSimple()` use internally).
- `packages/ai/src/providers/faux.ts:132-141` (**revision 2, `C10-D001`**: `FauxProviderRegistration`
  interface, declares `unregister: () => void` as a live public member of the returned
  registration object).
- `packages/ai/src/models.ts:628-634` (**revision 2, `C10-D002`**: `ModelsImpl.requireProvider` --
  a plain synchronous `throw new ModelsError(...)` for an unknown provider, not wrapped in any
  error-settling mechanism), `:706-732` (**revision 2, `C10-D002`**: `ModelsImpl.fetchDeferred`
  wraps `requireProvider`/capability-check/auth/delegation ENTIRELY inside `lazyStream(...).result()`
  -- every failure in that chain settles as a represented, RESOLVED `AssistantMessage`, never a
  rejected promise; `ModelsImpl.cancelDeferred` is a plain `async` method, NOT wrapped in
  `lazyStream` -- `requireProvider`'s own synchronous throw and its own direct
  `if (!provider.cancelDeferred) throw` both become a REJECTED promise), `:835-859` (**revision 2,
  `C10-D002`**: `createProvider`'s own mixed-API capability synthesis -- provider-level
  `fetchDeferred` is wrapped in its OWN `lazyStream` per-model capability check, an in-band
  settlement; provider-level `cancelDeferred` is a plain `async` function with a direct `throw` for
  the SAME per-model capability mismatch -- the identical fetch-vs-cancel asymmetry one level up).
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
   the given tag -- a bulk, tag-scoped removal at the GENERIC primitive level; two registrations
   sharing one `sourceId` are indistinguishable and removed together at that level. This module is
   Pi's own explicitly TEMPORARY compatibility surface ("deleted with the coding-agent ModelManager
   migration") -- live in the pinned revision, but Pi's own stated direction is away from it, not
   toward it.
3. **(revision 2, `C10-D001`)** Built ON TOP of (2): `compat.ts::registerFauxProvider(options)`
   generates a FRESH, unique `sourceId` (`Math.random()...`) on EVERY call, registers through
   `registerApiProvider(..., sourceId)`, and returns a `FauxProviderRegistration`
   (`providers/faux.ts:132-141`) whose own `unregister()` method closes over THAT call's unique
   tag and calls `unregisterApiProviders(sourceId)` with it. Because each call's own tag is unique,
   this IS a live, direct per-registration-call unregistration analogue on Pi's own faux/mock
   provider surface -- the exact scope this Layer-10 checkpoint concerns itself with -- even though
   it is built as a thin per-call convention over the generic bulk-tag-scoped primitive in (2), not
   a separate registry mechanism. Two `registerFauxProvider()` calls' own `unregister()` handles are
   therefore mutually independent in practice: calling an earlier call's own handle cannot remove a
   later call's own registration, because their generated tags differ.

   Stale/superseded removal for `compat.ts`'s registry depends on TAG IDENTITY, not call order
   alone (revision 1 incorrectly called this "not applicable"):

   ```text
   register api=x, source=A
   register api=x, source=B          # B replaces A in the single api=x map entry
   unregister source=A               # A's own tag no longer matches the current entry
       current B remains             # -- stale-removal safety, same OUTCOME as Minion's own rule
   ```

   ```text
   register api=x, source=S
   register api=x, source=S          # same tag reused for both calls (registerFauxProvider never
                                      # does this itself; only a caller of the lower-level
                                      # registerApiProvider/unregisterApiProviders primitives could)
   unregister source=S
       current entry removed         # tags coincide -- deliberate bulk/current-entry removal
   ```

Neither `MutableModels` nor `compat.ts`'s GENERIC registry primitive matches Minion's own
`LlmService`: Minion keys per FULL `(provider, model, api)` identity (finer-grained than either Pi
registry, both of which key on a single string), replaces per KEY rather than per whole
provider/api (so two Minion adapters sharing a `provider` id but declaring different models
COEXIST, unlike `MutableModels.setProvider`'s wholesale swap), and makes per-call ownership the
GENERIC registration rule (every `register()` call gets its own handle, unconditionally) rather
than a faux-specific convention layered over a bulk-tag-scoped primitive the way `compat.ts`'s own
per-call safety is achieved. `registerFauxProvider`'s own `unregister()` is a genuine, narrower
precedent for per-call safety on Pi's OWN mock-provider surface specifically -- it does not
invalidate the broader granularity/composition/introspection differences above, but the prior
"opposite granularity" framing overstated how different Minion's withdrawal model is from Pi's own
faux/mock convention specifically. The rule this checkpoint proposes, now against the complete
comparison: Minion's registry remains a genuine, disclosed Minion architectural choice with NO
single Pi registry it directly adopts -- grounded in an honest comparison against BOTH real Pi
registries AND their own faux/mock-provider convention, not the original row's false "no analogue
at all" premise.

**`L10-R006`.** `fetchDeferred`/`cancelDeferred` are Pi-required-when-present, capability-gated,
per-wire-protocol-module operations -- the SAME status class as `streamSimple` (`AI-031`): nothing
generic to specify at Layer 10's own provider-agnostic abstraction level until a real provider
(Layer 11) exists to implement one. Revision 1 stated this correctly but too coarsely; pinned Pi
keeps FOUR distinct observable layers separate, and a future Layer-11 implementation must preserve
all four, not collapse them (`C10-D002`):

1. **Low-level, per-API-module** (`types.ts::ProviderStreams.fetchDeferred?`/`cancelDeferred?`):
   `fetchDeferred`, when present, returns a NEW `AssistantMessageEventStream` (the SAME never-raises
   boundary `stream` already has, `AI-012`). `cancelDeferred`, when present, returns `Promise<void>`
   -- not stream-shaped at all.
2. **High-level, caller-facing** (`models.ts::ModelsImpl.fetchDeferred`/`cancelDeferred`): NOT
   symmetric. `fetchDeferred` wraps provider lookup, capability lookup, auth, and delegation
   ENTIRELY inside `lazyStream(...).result()` -- an unknown provider, a missing capability, or a
   delegated failure all settle as a REPRESENTED (resolved, in-band) `AssistantMessage` with an
   error `stopReason`, never a rejected promise. `cancelDeferred` performs the SAME provider/
   capability lookup EAGERLY, outside any `lazyStream` wrapper -- an unknown provider or a missing
   capability THROWS (a rejected promise), not a represented error. This is a genuine, deliberate
   ASYMMETRY between the two operations at the high-level boundary, not an oversight to smooth over.
3. **Provider-level, mixed-API capability selection** (`models.ts::createProvider`, `:835-859`):
   a provider built from an api-map synthesizes `provider.fetchDeferred`/`cancelDeferred` only if
   AT LEAST ONE api entry supports it -- but a caller may still pick a model whose OWN specific api
   entry lacks it. That per-model mismatch inherits the IDENTICAL fetch-vs-cancel asymmetry as (2):
   the synthesized `fetchDeferred` wraps its own capability check in `lazyStream` (in-band
   settlement); the synthesized `cancelDeferred` is a plain `async` function with a direct `throw`
   for the same mismatch (eager rejection).
4. **Reference (faux/mock) implementation's own concrete unknown/cancelled-handle behavior**
   (`providers/faux.ts:567-642`, already characterized in revision 1, unchanged): for a SUPPORTED
   capability, an unknown or already-cancelled `DeferredHandle` is NOT the same case as (2)/(3)'s
   missing-provider/missing-capability case above -- `fetchDeferred`'s own unknown/cancelled-handle
   failure settles as an in-band error event on the returned stream (the `queueMicrotask` body's own
   `try`/`catch` pushes an `error` chunk directly, never throwing out of `fetchDeferred` itself);
   `cancelDeferred`'s own unknown handle is a SILENT NO-OP (`deferredResponses.get(handle.id)` may
   be `undefined`, and nothing happens -- not an error, not a throw). This is the "best-effort,
   idempotent for unknown handles" behavior revision 1 already stated correctly, but it applies ONLY
   to a supported capability's own handle-resolution outcome, not to a missing provider/capability
   at all -- conflating the two would let cancel appear "always idempotent" when in fact only its
   handle-resolution failure mode is.

Both operations still build on `AI-009`'s own already-certified `DeferredHandle` vocabulary -- this
checkpoint proposes a NEW row for the BEHAVIOR these two operations require, not a change to
`AI-009` itself. Closure criterion (unchanged from revision 1, now grounded in the four layers
above): a future Layer-11 implementation must expose an externally invocable operation preserving
ALL FOUR distinctions -- it must NOT make `cancel_deferred` globally never-raising (collapsing (2)
into (1)'s shape), and it must NOT make `fetch_deferred` throw eagerly on a missing/unsupported
capability (collapsing (2) into (3)'s cancel-side behavior). Executable provider witnesses remain
deferred to Layer 11 (Layer 10 has no concrete wire-protocol implementation to test against); this
checkpoint commits only to the observable closure criteria stated here.

**`L10-R007`.** The canonical `llm_service` schema and grammar impose NO limit on how many times a
scenario may `stream` through the same registered identity; `behavior: ok` describes the adapter's
OWN behavior (always settles successfully), not a bounded number of successful calls. The runner's
own response provisioning is pure test-harness mechanics and must never silently narrow what a
schema-valid document can express.

## BEHAVIOR MATRIX

| Dimension | Pi `MutableModels` | Pi `compat.ts` generic registry | Pi `compat.ts::registerFauxProvider` (revision 2) | Minion `LlmService` (current) |
|---|---|---|---|---|
| Registration key | `provider.id` | `provider.api` | `provider.api`, via a fresh per-call `sourceId` | `(provider, model, api)` full identity |
| Replacement granularity | whole provider (all models swapped atomically) | whole api entry | whole api entry (inherits the generic registry) | per full-identity key only |
| Removal | `deleteProvider(id)` / `clearProviders()`, whole-provider | `unregisterApiProviders(sourceId)`, bulk tag-scoped | per-call `unregister()`, closes over that call's own unique tag | per-registration-call handle, `AI-030`/`C10-C005` |
| Removal of a stale/superseded entry | whole-provider swap has no "stale handle" concept to begin with | depends on tag identity: differing tags leave the current entry untouched (safe); shared tags remove the current entry (deliberate) | safe -- each call's own unique tag can never match a later call's differing tag | safe no-op (`AI-030`) |
| Repeat-removal idempotency | `deleteProvider` on an absent id is a silent no-op | `unregisterApiProviders` on an unknown/already-removed tag is a silent no-op | inherits the generic primitive's own idempotency | safe no-op (`AI-030`/`C10-C005`, binding) |
| Introspection | `getProviders`/`getProvider`/`getModels`/`getModel` | `getApiProvider`/`getApiProviders` | same, plus the registration's own returned `models`/`getModel`/`state` | `models()` |
| Deprecation status | current, forward architecture | explicitly temporary, scheduled for deletion | built on the temporary registry; itself Pi's own faux/mock-provider convenience layer | N/A (Minion-only) |
| `fetchDeferred`/`cancelDeferred`, missing provider/capability | `Models.fetchDeferred` settles in-band (`lazyStream`-wrapped); `Models.cancelDeferred` throws eagerly (not wrapped) -- see `L10-R006` | n/a (not part of this registry's own surface) | n/a | absent entirely -- no `Adapter` method, no `LlmService` method |
| `fetchDeferred`/`cancelDeferred`, supported-capability unknown/cancelled handle | faux reference: fetch settles in-band (error event on the stream); cancel is a silent no-op (idempotent) | n/a | n/a | absent entirely |

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

**`L10-R005`, revision 2 (`C10-D001`)** — the faux/mock per-call unregister witness, independently
re-executable against `ref-repos/pi`:

```text
r1 = registerFauxProvider()   # unique sourceId S1
r2 = registerFauxProvider()   # unique sourceId S2, for the SAME api if r1/r2 share one
r1.unregister()               # unregisterApiProviders(S1) -- S1 matches nothing now live
getApiProvider(<api>)         # r2's own registration is still live
```

Confirms Pi's OWN faux/mock convenience layer already gives each `registerFauxProvider()` call
independent, per-call withdrawal safety -- the same OUTCOME Minion's `AI-030`/`C10-C005` already
guarantees generically, reached by a different mechanism (a per-call random tag over a bulk-tag
primitive, versus Minion's per-call opaque token checked directly by the withdrawal closure).

**`L10-R006`** (proposed, to be added as permanent evidence once a Layer-11 provider exists to
exercise it -- Layer 10 itself has no concrete implementation to test against; see IMPLEMENTATION
CONSTRAINTS): none executable at Layer 10 today. The witness this row commits to for whichever
future pass closes it, now stated against all four observable layers (revision 2, `C10-D002`): a
Layer-11 adapter that supports deferred responses exposes a callable `fetch_deferred`/
`cancel_deferred` (or equivalent) where (a) a supported capability's own unknown/cancelled-handle
outcome matches the faux reference (fetch settles in-band, cancel is a silent idempotent no-op),
AND (b) a MISSING provider/capability is NOT collapsed into the same shape as (a) for either
operation -- `fetch_deferred` may still settle that case in-band (matching Pi's high-level
`Models.fetchDeferred`), but `cancel_deferred` must NOT be made globally never-raising just because
its handle-resolution failure mode happens to be a no-op. Neither operation is merely internal
option-translation plumbing with no caller-facing entry point.

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

**`pi-parity-manifest.yaml::AI-030`** — `pi:` field corrected to cite
`packages/ai/src/models.ts::MutableModels` (`225-230,269-291`),
`packages/ai/src/compat.ts::ApiProvider registry, registerFauxProvider` (`76-176`, revision 2), and
`packages/ai/src/providers/faux.ts::FauxProviderRegistration` (`132-141`, revision 2). `rule:`
rewritten to state the full behavior-matrix comparison above -- both registries' own granularity/
replacement/removal semantics, `compat.ts`'s own "temporary, deleted with the ModelManager
migration" status, AND `registerFauxProvider`'s own per-call unregister precedent on Pi's faux/mock
surface specifically (revision 2) -- and conclude Minion's registry remains an intentional
divergence because its OWN granularity and its GENERIC (not faux-specific) per-call withdrawal
rule genuinely differ from all three, not because none exists. `disposition:` unchanged
(`intentional divergence`), governance already decided (see below).

**New `pi-parity-manifest.yaml::AI-032`** — `fetchDeferred`/`cancelDeferred`, `disposition:
deferred parity`, mirroring `AI-031`'s own shape: cites `types.ts::ProviderStreams.fetchDeferred?/
cancelDeferred?`, `models.ts::ModelsImpl.fetchDeferred/cancelDeferred` (`706-732`, revision 2),
`models.ts::createProvider`'s own mixed-API capability synthesis (`835-859`, revision 2),
`api/lazy.ts::LazyApiCapabilities`, `providers/faux.ts` reference behavior. Explicit closure
criterion requiring an externally invocable Layer-11 operation for each, stated against all FOUR
observable layers from `OBSERVABLE RULES` above (revision 2, `C10-D002`) -- not merely
"never-raises fetch, best-effort cancel" as revision 1 stated too coarsely. Explicitly notes
`AI-009` already covers the `DeferredHandle` VOCABULARY this row's own BEHAVIOR builds on, so as
not to re-litigate that row.

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
  concludes divergence DOES remain after the truthful mapping (see BEHAVIOR MATRIX). **This
  governance item is now DECIDED** -- see `GOVERNANCE DECISION (§11.7)` below.
- `L10-R006`'s remediation is ALSO documentary/disposition-only at this layer -- Layer 10 has no
  concrete wire-protocol implementation to attach real `fetch_deferred`/`cancel_deferred` behavior
  to yet (matching `AI-031`'s own already-accepted reasoning for `streamSimple`). Do not build
  speculative Python plumbing for an operation with no Layer-11 provider to exercise it.
- `L10-R007`'s fix touches only `llm_service_runner.py` (test/tooling code, not `src/`) plus one
  new canonical scenario. No production `LlmService`/`Adapter` source file changes.
- Rust: unaffected. `L10-R005`/`L10-R006` are shared-contract/documentation corrections; `L10-R007`
  is Python-only test tooling. None of the three requires or implies any Rust change.

## GOVERNANCE DECISION (§11.7) — RECORDED

The repository owner APPROVED continuing Minion's existing `LlmService` registry semantics as an
intentional, disclosed divergence, on the exact behavior-matrix comparison this checkpoint
documents above. Recorded verbatim (owner's own words, via the shared/Python owner's relay):

```text
L10-R005 GOVERNANCE DECISION
APPROVED — INTENTIONAL DIVERGENCE

Minion may retain the existing LlmService registry semantics:
- registration key:            full (provider, api, model_id) identity
- composition/replacement:     per full-identity key
- withdrawal ownership:        per individual registration call / withdrawal handle
- stale or repeated withdrawal: does not remove a later replacement

This intentionally differs from both pinned-Pi registry surfaces:
1. MutableModels
   - provider.id keyed
   - whole-provider replacement/removal
2. compat.ts ApiProvider registry
   - api keyed
   - last-write-wins per API
   - bulk sourceId-scoped unregister
   - explicitly temporary compatibility surface

RATIONALE
The divergence is architectural and deliberate, not based on an absence of Pi precedent. It
follows Minion's frozen registration-ownership model, where the registration context owns its
registration lifetime and individual registries define their own composition semantics, and it is
consistent with Minion's frozen canonical model identity of (provider + api + model_id).
Redesign toward MutableModels is therefore NOT required for Layer 10.

REQUIRED DOCUMENTATION
AI-030 and spec/llm.md must:
- explicitly cite and compare both real Pi registries;
- remove any claim that Pi has no analogous registration concept;
- mark Minion's granularity/replacement/withdrawal behavior as intentional divergence;
- state the exact observable differences;
- record this governance approval;
- avoid implying that unrelated provider behavior is also approved to diverge.

SCOPE OF APPROVAL
This approval applies only to L10-R005 / AI-030 registry registration, replacement, introspection,
and withdrawal granularity. It does not approve unrelated provider/API semantic divergence and
does not alter the project's general Pi-fidelity requirement.
```

This decision does not by itself close `L10-R005` or advance this checkpoint to `AGREED FOR
IMPLEMENTATION` -- the independent Codex challenge of the Pi-source mapping (§11.8.4) remains a
SEPARATE, still-outstanding track. `L10-R006`/`L10-R007` are unaffected by this decision (neither
involves an intentional-divergence claim). **Revision 2 note:** the `C10-D001` faux/mock per-call
`unregister()` precedent found above is a REFINEMENT of the same comparison the owner already
approved (it strengthens, not weakens, the case that Minion's per-call withdrawal has SOME Pi
precedent, just not at the generic-registry level) -- it does not change the SCOPE OF APPROVAL or
require the owner to re-decide anything.

## OUT-OF-SCOPE / DEFERRED BEHAVIOR

- `L10-R003` (current Rust `AdapterStartError`): unchanged, not addressed here.
- Any redesign of Minion's own registry to more closely match any of the three Pi surfaces
  (`MutableModels`, `compat.ts`'s generic registry, `registerFauxProvider`): not proposed; see
  IMPLEMENTATION CONSTRAINTS.
- Actual `fetchDeferred`/`cancelDeferred` Python implementation: Layer 11's own future obligation,
  same as `streamSimple` (`AI-031`).
- Layer 11 (Real providers): not started.

---

## CONVERGENCE CONTRACT

    PROPOSED -- AWAITING INDEPENDENT AGREEMENT (revision 2)

REVISION HISTORY
    Revision 1: first characterization pass, docs PR #45 @ d445901cc8441e6ab66acfd929df4e93e6fc6763.
    Revision 1 challenge: CHANGES REQUIRED (C10-D001, C10-D002; L10-R007 accepted), docs PR #47 @
      273951ad2b4a1bd6aa984b502a370b79935a0931.
    Revision 2 (this revision): remediates C10-D001 (faux/mock per-call unregister precedent,
      tag-identity-dependent stale removal) and C10-D002 (four-layer fetch/cancel capability and
      error-boundary distinction), docs PR #45 @ 43216a98d1c911f808a1f1557e73ed3d3239c0bb (revision
      1 head) -> this commit.

OPEN FINDINGS
    L10-R005
    L10-R006
    L10-R007

ACCEPTANCE WITNESSES
    L10-R005: the pinned-Pi MutableModels probe (re-executable against ref-repos/pi); the
      revision-2 faux/mock per-call unregister probe (also re-executable); the corrected AI-030
      rule: text itself (independently checkable against all cited Pi source ranges); owner
      governance sign-off recorded on issue #19 and in this checkpoint.
    L10-R006: new AI-032 manifest row and spec/llm.md paragraph stating all four observable layers
      from revision 2's OBSERVABLE RULES, checkable against the cited Pi source ranges; no
      executable evidence exists or is claimed at Layer 10 (deferred to Layer 11).
    L10-R007: the greater-than-eight-call canonical scenario (new), llm_service_runner.py's own
      fixed-provisioning fix, revert-and-confirm against the exact PASS-3 candidate. UNCHANGED
      since revision 1; already accepted by the challenge.

NORMATIVE DELTAS
    minion-agent/pi-parity-manifest.yaml (AI-030 corrected with the full three-surface comparison,
      new AI-032 stating all four observable layers)
    minion-agent-docs/spec/llm.md (AI-030 paragraph corrected, new fetchDeferred/cancelDeferred
      paragraph stating all four observable layers)
    minion-agent/conformance/agent/ (one new >8-call scenario)
    minion-agent-python/tests/conformance/llm_service_runner.py (_build_adapter provisioning fix)

NEXT_OWNER
    Codex

NEXT_ACTION
    Independent challenge (§11.8.4) of this revision 2: confirm the C10-D001/C10-D002 remediation
    above (the faux/mock per-call unregister precedent and tag-identity stale-removal matrix; the
    four-layer fetch/cancel capability and error-boundary distinction) fully addresses both
    findings, and that no further Pi-source-mapping gap remains before this checkpoint can be
    marked `AGREED FOR IMPLEMENTATION` under §11.8.5. The §11.7 governance track for L10-R005
    remains RESOLVED (`GOVERNANCE DECISION (§11.7) -- RECORDED` above) and is not part of this
    challenge. L10-R007 is closed and needs no further challenge.
