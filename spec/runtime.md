# Runtime Semantics

Minion's primary intentional architectural divergence from Pi (`pi-parity-manifest.yaml`
`MINION-001`). Cordis-semantic, not a Cordis port. Authority here is the frozen master design's §3,
not pinned Pi source. Requirement IDs (`RT-###`) follow `process/requirement-id-convention.md` and
are cited by `assurance/layers/01-runtime.md`.

## RT-001 — Fiber lifecycle

```text
Pending --deps satisfied--> Loading --success + deps still visible--> Active
Pending --dispose--> Disposed
Loading --dependency invalidation--> unwind --> Pending
Loading --init failure--> unwind --> Failed
Loading --dispose--> unwind --> Disposed
Active --dependency loss--> Unloading --> unwind --> Pending
Active --dispose--> Unloading --> unwind --> Disposed
Failed --dispose--> Disposed
Disposed --dispose--> no-op
```

`Failed` is stable: dependency changes never retry it; no restart operation exists; recovery is
disposal followed by a fresh mount. `Loading` is a transaction over owned effects — a `Loading`
attempt invalidated by dependency loss or disposal cannot register further owned effects, and
existing effects unwind only after the attempt is stopped, so the fiber settles back at `Pending`
without ever passing through `Active`/`Unloading`. The cancellation/serialization mechanism is
implementation-specific; the no-race result is not.

## RT-004 to RT-008 — Service resolution

Identity is `(name, realm)`, compared by string value only — never object/enum/pointer/type
identity. Registration is exclusive: a second `provide()` for a held name raises, naming the fiber
that already holds it; no last-wins, no priority. There is no fallback stack — revocation removes
the slot and notifies dependents; an earlier provider is never retained and never resurfaces.
Visibility is narrower than registration: a service resolves only while its providing fiber is
`Active`, and an optional `check` predicate may narrow visibility further. Dependents react to the
resolved provider — every fiber injecting a service is rechecked when that service appears or
disappears.

**Revocation reconciles inline, not afterward.** A provider's `provide()` effect disposer both
revokes the registration and calls reconciliation itself, nested inside the disposing fiber's own
unwind. A dependent that loses its service therefore completes its own unload/pending transition
*during* the provider's disposal, before the provider's own fiber reaches `Disposed` — not as a
separate step afterward. This is what makes the no-fallback-stack guarantee (RT-006) observably
race-free: there is no window where the provider is gone but a dependent has not yet reacted.

## RT-009 to RT-012 — Scoped registration

A scope is a tagged context; the registration context determines both visibility and ownership — a
registration can never be visible in one scope but disposed via another. Two directions differ:
registration visibility inherits *down* (a child scope sees its own and ancestors' registrations; an
ancestor never sees a descendant's); event admission extends *up* (a listener tagged with an
ancestor receives a descendant's dispatch, never the reverse). An untagged listener/registration
participates everywhere. Disposing a scope removes exactly its own and its descendants'
registrations, in reverse creation order, leaving ancestors and siblings intact.

## RT-013 to RT-015 — Effects

`ctx.effect(fn)` runs `fn` immediately and collects its disposer; disposers run in reverse order on
disposal or fiber unload, whichever first. Double-disposal is a no-op — both at the individual
effect level and at the fiber level (unmounting an already-disposed plugin a second time produces no
further disposal trace). Creating an effect on a fiber that is not `Loading` or `Active` raises —
this covers `Disposed`, `Failed`, `Unloading`, and `Pending`, not merely the terminal `Disposed`
case.

## RT-016 — Dispatch modes

```text
mode      awaited  order         returns
emit      no       registration  no (fire and forget)
parallel  yes      concurrent    no (errors aggregated)
serial    yes      registration  yes (last value wins)
waterfall yes      registration  yes (around-middleware)
```

Dispatch mode is declared where the event is declared; declaring the same event with two different
modes is a **startup error** — it surfaces at declaration time, before any step that uses the event
runs, not as an ordinary mid-scenario failure.

## RT-017 to RT-022 — Waterfall

A listener is invoked as `listener(*args, next)`. Not calling `next` short-circuits: downstream
listeners never run, and the short-circuiting listener's own return value is the chain's result.
Calling `next()` delegates with the current arguments and returns whatever downstream produced,
unchanged. Calling `next(*replacement)` delegates with replacements instead. `next` may be called at
most once per listener; a second call raises. Every waterfall event declares a terminal continuation
— the value produced when the innermost listener delegates past the end of the chain, and equally
the result of a chain with zero mounted listeners; it is never implicitly `None`. Scope filtering on
dispatch is additive: an untagged listener is always admitted regardless of the dispatch's scope key
(including a dispatch that carries no scope key at all); a tagged listener is admitted only when its
key is the dispatch's key or an ancestor of it, so a dispatch with no key at all admits only untagged
listeners.

## RT-023 — Config

Plugin config validates through Pydantic; JSON Schema export is available where the conformance
layer needs it. This is a Python-specific mechanism detail — not part of the language-neutral
runtime contract `conformance/runtime/` covers, and not required to have canonical conformance
evidence. A second-language implementation validates config through its own idiomatic mechanism.
