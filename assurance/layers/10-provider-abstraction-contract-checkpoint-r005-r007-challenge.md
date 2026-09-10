# Layer 10 — L10-R005/R006/R007 convergence challenge

**Checkpoint reviewed:** docs PR #45 at
`43216a98d1c911f808a1f1557e73ed3d3239c0bb`

**Code candidate retained by the checkpoint:** code PR #20 at
`4d63349d85d517359545b94ce0937548d3fb7314`

**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`

**Prior final review:** docs PR #47 at
`e8a2d395dc4697eb65b42958eb043c9c7eede185`

**Result:** `CHANGES REQUIRED`; the checkpoint is not yet `AGREED FOR IMPLEMENTATION`.

This is the independent workflow §11.8.4 challenge pass. It is limited to the technical
Pi-source mapping requested by coordination issue #19. The owner's §11.7 approval of Minion's
full-identity registry divergence is accepted as a closed governance decision and is not being
re-litigated. No candidate, Python, Rust, spec, manifest, schema, or conformance file was changed.

## Source audit

The challenge independently re-read these pinned-Pi surfaces before assessing the proposed
deltas:

- `packages/ai/src/models.ts`: `Provider`, `Models`, `MutableModels`, `ModelsImpl.fetchDeferred`,
  `ModelsImpl.cancelDeferred`, `createProvider`, `apiFor`, and capability synthesis;
- `packages/ai/src/types.ts`: `DeferredFetchOptions`, `DeferredCancelOptions`, `ProviderStreams`,
  and `DeferredHandle`;
- `packages/ai/src/api/lazy.ts`: `LazyApiCapabilities`, `fetchDeferred`, and `cancelDeferred`;
- `packages/ai/src/providers/faux.ts`: `FauxProviderRegistration`, `fetchDeferred`, and
  `cancelDeferred`;
- `packages/ai/src/compat.ts`: `registerApiProvider`, `unregisterApiProviders`, and
  `registerFauxProvider`.

The proposed `L10-R007` runner correction is also independently sound: provisioning every
fixture with the scenario's total possible stream/resolve observation count is a safe upper bound
that does not predict which adapter resolution will select. A greater-than-eight-call scenario is
the right discriminating witness. No challenge remains on that finding.

## Challenge C10-D001 — the Pi registry comparison omits the direct faux/mock registration handle

The checkpoint correctly identifies `MutableModels` and the underlying deprecated compat
`ApiProvider` registry, but its claim that Minion's per-registration withdrawal handle is simply
“the opposite granularity” from Pi's compat surface is incomplete for this layer's mock-adapter
scope.

Pinned `compat.ts::registerFauxProvider()` creates a fresh source id for that call, registers the
faux provider through `registerApiProvider`, and returns a `FauxProviderRegistration` whose public
`unregister()` closes over that unique source id. `FauxProviderRegistration` declares that method
in `providers/faux.ts`. This is a live public Pi operation and a direct per-registration
unregistration analogue on the faux/mock provider surface, even though its underlying generic
registry primitive remains bulk tag-scoped.

The behavior matrix also incorrectly calls stale/superseded removal “not applicable” for the
compat registry. Its result depends on tag identity:

```text
register api=x, source=A
register api=x, source=B
unregister source=A
    current B remains

register api=x, source=S
register api=x, source=S
unregister source=S
    current replacement is removed
```

Thus compat has observable stale-source safety when tags differ and deliberate bulk/current-entry
removal when tags coincide. `registerFauxProvider` normally supplies a unique tag per call, so its
returned old handle cannot remove a later faux registration made by another call.

This does not invalidate the approved intentional divergence. Minion still differs in keying,
composition, introspection, and the fact that per-call ownership is the generic registration
rule rather than a faux-specific wrapper over tag-scoped removal. It does mean the promised
“honest comparison against both real Pi registries” is not yet technically complete.

Revision 2 must:

1. include `compat.ts::registerFauxProvider` and `FauxProviderRegistration.unregister` in the
   Pi-source mapping for `AI-030`/the normative spec;
2. distinguish the generic tag-scoped operation from the faux wrapper's unique-per-call handle;
3. replace the matrix's “stale removal not applicable” entry with the two tag-identity outcomes;
4. narrow any “opposite granularity” statement so it does not deny Pi's actual faux/mock
   per-registration observable surface.

No production redesign and no governance reopening follows from this documentary correction.

## Challenge C10-D002 — deferred-operation semantics need the capability/error boundary

The proposed `AI-032` correctly separates deferred-operation behavior from `AI-009`'s handle
vocabulary and correctly defers wire-protocol implementation to Layer 11. Its current rule is not
yet complete enough to prevent two independent implementations from choosing different public
failure behavior.

Pinned Pi has two distinct abstraction levels:

- `ProviderStreams.fetchDeferred`, when present, returns an `AssistantMessageEventStream`;
  `Models.fetchDeferred` awaits `.result()` and returns an `AssistantMessage`.
- `Models.fetchDeferred` wraps provider lookup, capability lookup, auth, and delegation inside a
  lazy stream. Missing provider/capability and delegated failures therefore settle as the
  represented assistant error boundary rather than escaping from this high-level operation.
- `ProviderStreams.cancelDeferred`, when present, returns `Promise<void>`;
  `Models.cancelDeferred` performs provider/capability lookup and auth eagerly. A missing provider
  or missing capability throws. The faux implementation's unknown handle is a silent no-op, but
  that best-effort rule is not a general statement that every cancel failure is suppressed.
- `createProvider` exposes each provider-level capability only if at least one configured API
  implementation supplies it. For a mixed-API provider, selecting an API entry without the
  capability produces an in-band fetch error but an eager cancel error.

The checkpoint currently states the faux unknown-handle outcomes but does not bind these
provider/capability boundaries. A future Layer-11 implementation could therefore satisfy its
proposed prose while incorrectly making `cancelDeferred` globally never-raising, or making
high-level `fetchDeferred` throw on unsupported capability.

Revision 2 must make the deferred acceptance contract distinguish:

1. low-level provider-stream return shapes from high-level Models-facing return shapes;
2. supported-capability unknown/cancelled-handle behavior from missing provider/capability
   behavior;
3. fetch's represented-error boundary from cancel's eager error boundary;
4. mixed-API capability selection, while leaving actual protocol encoding to Layer 11.

Executable provider witnesses may remain deferred to Layer 11, but the row/spec must state these
observable closure criteria now. This is a contract characterization correction, not a request to
start Layer 11 or add speculative production plumbing.

## Challenge result

| Finding | Result | Required action |
|---|---|---|
| `L10-R005` | revision required | add faux registration handle and accurate tag/stale-removal mapping |
| `L10-R006` | revision required | specify provider/capability and fetch-vs-cancel failure boundaries |
| `L10-R007` | accepted for implementation | retain non-predictive provisioning and >8-call witness |

Both requested revisions are documentary/contract characterization. They do not reopen a lower
certified layer, do not change the owner's approved divergence, and are implementable
independently in Python and Rust at their owning future phases.

```text
CONVERGENCE CONTRACT
    CHANGES REQUIRED

PROVISIONALLY ACCEPTED
    L10-R007

REVISION REQUIRED
    L10-R005
    L10-R006

NEXT OWNER
    Claude

NEXT ACTION
    Publish checkpoint revision 2 addressing C10-D001 and C10-D002, then return for independent
    §11.8.5 agreement. Do not implement the proposed checkpoint before agreement.
```

`L10-R003` remains the previously disclosed Rust-only implementation defect outside this
checkpoint. No Rust Layer-10 implementation or Layer-11 work is authorized by this challenge.

---

## Revision 2 agreement — checkpoint `004c92b268a01fc50ad05af90708f5ad539a4242`

**Result:** `CONVERGENCE CONTRACT — AGREED FOR IMPLEMENTATION`.

Revision 2 closes both challenge findings against the Pi source:

- `C10-D001`: the checkpoint now includes `compat.ts::registerFauxProvider`, the public
  `FauxProviderRegistration.unregister()` operation, its per-call generated source tag, and the
  distinct-tag/shared-tag stale-removal outcomes of the underlying generic registry. It correctly
  distinguishes Pi's faux-specific per-registration observable precedent from Minion's generic
  per-registration ownership rule. The already-recorded owner approval remains scoped and valid;
  no registry redesign or governance reopening is required.
- `C10-D002`: the checkpoint now separates low-level provider-stream shapes, high-level
  Models-facing behavior, mixed-API capability selection, and supported faux handle behavior. It
  binds fetch's represented failure settlement separately from cancel's eager provider/capability
  rejection and its supported-capability unknown-handle no-op. This is complete enough to prevent
  the two realistic wrong implementations identified by the challenge while leaving wire encoding
  and executable provider evidence to Layer 11.
- `L10-R007`: remains accepted. The proposed total-observation upper bound does not predict adapter
  ownership and the greater-than-eight-call scenario directly detects the runner's hidden cap.

### Binding source-accuracy clarification

Pinned `registerFauxProvider` generates a fresh pseudo-random source tag on every call but does not
collision-check it. Current normative wording must therefore avoid promising mathematically
guaranteed uniqueness. Describe the implementation as a freshly generated per-call tag (normally
distinct), and characterize per-call stale safety for the observed distinct-tag case. The shared-
tag matrix already records the collision/reuse outcome. This is a precision correction to prose,
not a new semantic design or a reason for another checkpoint revision.

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION

OPEN FINDINGS TO IMPLEMENT
    L10-R005
    L10-R006
    L10-R007

ACCEPTANCE WITNESSES
    corrected AI-030 three-surface Pi comparison and scoped governance record
    distinct-tag and shared-tag compat removal outcomes
    externally callable Layer-11 deferred operations preserving all four AI-032 boundaries
    greater-than-eight calls through one behavior=ok canonical adapter
    runner provisions without predicting the resolved adapter

NORMATIVE DELTAS
    checkpoint revision 2, plus the binding source-tag wording clarification above

NEXT OWNER
    Claude

NEXT ACTION
    Implement the agreed convergence surface, prove RED against the exact rejected candidate,
    push exact candidate SHAs, and return for the targeted workflow §11.8.7 finding-closure review.
```

This agreement is not final Layer-10 contract approval. `L10-R003` remains a disclosed Rust-only
implementation defect. After targeted closure, workflow §11.8.8 still requires a complete review
of the exact final shared/Python candidate before Rust implementation may begin. Do not start
Layer 11.
