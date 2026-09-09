# Layer 10 — L10-R001/R002/R004 contract convergence (disposition semantics + canonical-scenario grammar/observation)

**Revision 3, NOT yet approved.** Revision 1 was independently challenged
(`assurance/layers/10-provider-abstraction-convergence-challenge.md`, docs PR #47, review commit
`60ef1cd5410c81bd33b526859cca5d49dc096584`): **CONVERGENCE CONTRACT — CHANGES REQUIRED**, findings
`C10-C001`-`C10-C004` (summarized below, all addressed in revision 2). Revision 2 was independently
challenged again (same docs PR #47, review commit `1ced90250ca7c0df7169780ae95a4dcf6d410b70`):
**CONVERGENCE CONTRACT — CHANGES REQUIRED** a second time, with `C10-C001`-`C10-C004` explicitly
confirmed closed ("No additional challenge remains for `C10-C001` through `C10-C004`") and one new
finding:

- **`C10-C005`** (the new same-fixture/two-handle witness exposes a REAL Python PRODUCTION defect,
  not merely a new grammar capability): revision 2's own required acceptance witness -- register
  the SAME adapter fixture twice under two distinct handles, withdraw only the first, the second
  registration remains resolvable -- exercises `AI-030`'s own ALREADY-normative rule that a
  withdrawal handle owns exactly the entries its own `register()` call added. Current
  `LlmService.register()` (`llm/service.py`) cannot satisfy this: it records only the ADAPTER
  OBJECT in `_adapters`, and its returned closure removes an entry whenever the CURRENT value `is
  adapter`. Registering the SAME adapter object twice makes the two calls indistinguishable by that
  check -- the review's own direct reproduction confirms it: `register(a)` twice, `models()` shows
  1 entry, withdrawing the FIRST handle drops it to 0 (wrong; the SECOND registration should
  remain). Revision 2 mischaracterized this witness as a new grammar capability with "no PASS-2
  baseline" needing only schema/runner/scenario work; it is a genuine `CONTRACT_ASSURANCE_DEFECT`
  in already-certified Python production code, requiring an actual Python production repair as part
  of this convergence's own implementation pass.

Revision 3 (this text) accordingly adds a Python production repair surface -- previously-accepted
`C10-C001`-`C10-C004` are UNCHANGED from revision 2, reproduced below only for continuity.

**Prior challenge findings, addressed in revision 2, unchanged since (see the exact wording in
docs PR #47's own review commits for the full original text):**

- **`C10-C001`**: `streamSimple`'s own deferred-parity closure criterion states the observable,
  externally-invocable obligation explicitly, not merely internal per-provider translation
  plumbing.
- **`C10-C002`**: `register`/`withdraw` redesigned around explicit, unique handle ids with
  pre-flight reference validation, closing the fixture-vs-handle ambiguity.
- **`C10-C003`**: the combined `queries[].id`/`steps[].stream.as` observation namespace gained
  uniqueness and dangling-expectation validation, with setup-only observations explicitly
  permitted.
- **`C10-C004`**: owner detection requires exactly one request-count delta, failing explicitly on
  zero or multiple matches.

**Trigger check (mandatory, `process/agent-workflow.md` §11.8):**

- **`L10-R002`**: found by the PASS-1 review (`AI-029` mixed Pi's own resolution mapping, a Minion
  architectural simplification, and Minion-only registration/withdrawal/introspection mechanics
  under one `adopted` disposition), "fixed" in PASS 2 (split `AI-030` out for the registration
  mechanics), found STILL OPEN by the PASS-2 targeted re-review: `AI-029` itself still carries
  `disposition: adopted` even though the review holds its own remaining content -- Minion's eager
  rejection where Pi settles in-band -- is an OBSERVABLE divergence from Pi, not merely an
  authorized architectural choice. **Two independent reviews on the same finding ID -> the "same
  material finding survives two independent reviews" trigger is MET.**
- **`L10-R004`**: found by the PASS-1 review (no canonical evidence at all for registration/
  replacement/withdrawal/introspection/adapter-detected-failure settlement), "fixed" in PASS 2 (a
  new `llm_service` canonical family, four scenarios, a new runner), found STILL OPEN by the
  PASS-2 targeted re-review with two NEW concrete, reproduced defects in that new infrastructure
  itself: the schema accepts a `behavior: reject` adapter missing its own required
  `reject_message`, and the runner's own ownership-observation logic is unsound (a stale,
  value-equality search over historical request logs, not an observation of which adapter's own
  request log actually grew). **Two independent reviews on the same finding ID -> the trigger is
  MET.**
- **`L10-R001`** does not itself meet the automatic per-ID threshold (its PASS-1 rejection was
  "`streamSimple` misread as optional," genuinely fixed in PASS 2; its PASS-2-targeted rejection is
  a DIFFERENT specific defect -- disposition mixing -- found for the first time). It shares the
  IDENTICAL root cause as `L10-R002`, however (a manifest row's own `disposition:` field must
  describe only genuinely single-disposition content; mixed adopted/deferred/divergent content
  under one label is the exact defect class both findings share), and is bundled into this SAME
  convergence pass for coordination efficiency -- the same "freeze unrelated implementation work,
  bundle a non-triggering sibling finding sharing the same mechanism" pattern the `L09-R012`
  convergence already established for `L09-R015`/`L09-R016`.
- **`C10-C005`** does not itself need a separate two-review repeat-trigger determination: it is a
  finding raised DURING this SAME already-active convergence's own challenge cycle (`§11.8.4`), not
  a fresh independent contract review outside the convergence -- exactly the iterative
  characterization/challenge negotiation `§11.8` already provides for, not a new instance of the
  repeated-rejection trigger. It is absorbed into this convergence's own already-open scope, per the
  challenge review's own explicit instruction ("Revision 3 must... add `C10-C005` to the open
  convergence surface").

**Determination:** enter `CONTRACT_CONVERGENCE` for THREE coupled surfaces: (A) manifest
disposition semantics as applied to `AI-028`/`AI-029`/`AI-030`/`AI-031` (`L10-R001`/`L10-R002`),
(B) the `llm-service` canonical scenario schema/runner's own grammar completeness and
ownership-observation soundness (`L10-R004`), and (C), new in revision 3, `LlmService.register()`'s
own Python PRODUCTION registration-call-ownership defect (`C10-C005`). This is a `§11.8.3`
characterization pass, proposed here for Codex's own independent agreement. No implementation in
this artifact -- `§11.8.1`'s "freeze unrelated implementation work" applies, including to the newly
identified production repair.

## Exact state under convergence

- code PR: `EGAILab/minion-agent#20`, exact head: `bad0f74552fbb73c71f15553ba321fc1d8609a10`
- docs PR: `EGAILab/minion-agent-docs#45`, exact head: `558c03e4b0e67f162fee669e8f9c7c08747bebf3`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- `L10-R003`: CONFIRMED OPEN Rust-implementation-only defect, already correctly disclosed by both
  reviews, unaffected by and out of scope for this convergence. Layer 11: not started, unaffected.

## Root-cause characterization

### A. Disposition semantics (`L10-R001`/`L10-R002`)

Both reviews converge on the same underlying question: what does a manifest row's own
`disposition:` field actually assert? Re-reading this project's own established precedent directly
(`AG-015`'s own split-off row, `pi-parity-manifest.yaml` line ~2400, its own text explicitly
states the principle): `disposition: adopted` asserts that THIS row's own OBSERVABLE behavior
matches pinned Pi's own observable behavior for the same input -- not that the row's content is
architecturally authorized, justified, or a reasonable design choice. `disposition: intentional
divergence` asserts the row's own observable behavior differs from Pi's, by deliberate choice,
regardless of how well-justified that choice is (master-design authorization is why a divergence
is ACCEPTABLE, not evidence that it stops being a divergence). `disposition: deferred parity`
asserts Pi requires some behavior/operation this row's own surface does not implement AT ALL yet
-- content genuinely absent, with a stated future owner -- distinct from divergence (which
implements something, just differently) and from adoption (which implements the same thing).

That row's own text states the exact same lesson this convergence needs to re-apply: "This row's
own disposition is `deferred parity`, distinctly from [a sibling row's] `adopted` and [another
sibling's] `intentional divergence` -- exactly the kind of distinction a single bundled row
previously obscured." `AI-028`/`AI-029` are the SAME class of previously-obscured bundling,
confirmed independently by two separate reviews now.

**Applied to `AI-028` (`L10-R001`):** the row bundles two DIFFERENT Pi operations with two
DIFFERENT actual dispositions. `stream` is genuinely implemented and genuinely matches Pi's own
observable `stream()` behavior for a resolved adapter (Python-side; `L10-R003` is a Rust-only gap,
not a Python row-disposition question) -- `adopted`. `streamSimple` is NOT implemented at Layer 10
at all -- its own translation content is inherently per-API and has nothing generic to implement
until Layer 11 -- `deferred parity`, not `adopted`, and not silently folded into a row whose own
label says "adopted" for the WHOLE row.

**Applied to `AI-029` (`L10-R002`):** the row's entire observable content is "what happens when
`LlmService.stream()` is asked to resolve an identity." Its own DISTINGUISHING behavior -- the
only part of this row a caller can actually observe and that differs from a trivial pass-through
-- is what happens on a MISS: Minion rejects EAGERLY for both "no such identity at all" (a case
Pi's own `models.ts` doesn't symmetrically have, since Minion has no config-driven catalog to
compare against) and "an identity whose own api has no matching implementation" (a case Pi settles
IN-BAND, via `apiFor`/`dispatch`'s own `lazyStream`). There is no separately-observable
"adopted-and-correct" sub-behavior within this row distinct from its own eager-rejection design --
the HIT case (successful resolution and dispatch) is not independently Pi-parity-interesting on
its own; it is `AI-028`'s own `stream` contract that governs what a resolved dispatch looks like.
Since the row's own entire distinguishing observable content diverges from Pi's own observable
behavior (even though master-design-authorized), the correct disposition for the WHOLE row is
`intentional divergence`, not `adopted` -- the review's own second offered remediation path, and
the one this checkpoint proposes (rather than a further split, which would separate mechanism from
behavior without producing any independently-testable "adopted" remainder).

### B. Canonical scenario grammar completeness and ownership-observation soundness (`L10-R004`)

Two DISTINCT, unrelated implementation defects in the NEW `llm-service` canonical infrastructure
authored under PASS 2 -- not one shared root cause, but both are genuine gaps in newly-authored
test infrastructure that basic adversarial self-testing (deliberately feeding the new schema a
malformed document; deliberately constructing a scenario that reuses an identity across two
adapters) would have caught before handoff.

**B1 -- schema completeness.** `adapterEntry`'s own `behavior`/`reject_message` fields are
independently optional-or-required with no CROSS-FIELD constraint tying them together: a
`behavior: reject` entry validates even with `reject_message` entirely absent (then crashes
`_build_adapter` with an unhandled `KeyError` at RUNTIME, not a schema-validation failure at
AUTHORING time); a `behavior: ok` entry validates even WITH an inapplicable `reject_message`
present (silently ignored, ambiguous whether that is intentional). Two independent runners
(Python today, a future Rust one) could each resolve this ambiguity differently and both remain
schema-valid, defeating the entire point of a language-neutral schema.

**B2 -- ownership-observation soundness.** `llm_service_runner.py`'s own `resolve` query handler
determines which adapter served a request by searching `adapters.items()` (registration order) for
the first whose OWN `.requests[-1]` is VALUE-EQUAL to the just-issued `request`. This is unsound
whenever two different adapters have EVER received value-equal `Request` objects -- trivially
likely in this exact scenario family, since every `Request` this runner constructs is
`Request(model=identity, system="", messages=(), tools=())`: the ONLY field that ever varies is
`model`, so two calls to the SAME identity through DIFFERENT adapters (a legitimate, exactly-the-
scenario-this-family-exists-to-test sequence: register A for identity X, call `stream(X)` once
through A, register B for X -- replacing A -- then resolve X again) produce two value-EQUAL
requests, one in A's own log and one in B's. The search finds A first (registration order),
reporting the WRONG owner even though `LlmService` itself correctly dispatched the second call to
B. The review's own reproduction confirms this exactly: real current owner `B`, runner observation
`adapter-a`.

### C. Registration-call ownership defect in Python production (`C10-C005`), new in revision 3

`AI-030`'s own already-certified normative rule (unchanged since PASS 2, restated here for
precision): `register(adapter)` returns a withdrawal handle scoped to EXACTLY the entries THAT
call added -- an EARLIER registration's own handle must be a safe no-op once a LATER call has
replaced the same identity, never removing what the later call added. This rule was always stated
in terms of REGISTRATION CALLS, never adapter OBJECTS -- but the current implementation conflates
the two.

Direct read of `llm/service.py::LlmService.register`, confirmed by the review's own reproduction:

```python
def register(self, adapter: Adapter) -> Callable[[], None]:
    ids = [ModelId(adapter.provider, model, adapter.api) for model in adapter.models]
    for model_id in ids:
        self._adapters[model_id] = adapter
    def withdraw() -> None:
        for model_id in ids:
            if self._adapters.get(model_id) is adapter:
                del self._adapters[model_id]
    return withdraw
```

The withdrawal closure's own ownership check, `self._adapters.get(model_id) is adapter`, tests
ADAPTER OBJECT identity, not REGISTRATION CALL identity. These are the SAME question only when an
adapter object is registered at most once. When the identical adapter OBJECT is registered TWICE
(for the same or different identities -- a legitimate use this DSL's own required witness now
constructs, and nothing in `AI-030`'s own normative rule forbids), both calls' own closures share
the exact same `is adapter` test, so NEITHER handle can distinguish "I am the call that currently
owns this entry" from "some other call registered the same object here too." The FIRST handle
therefore incorrectly removes the SECOND (current) registration's own entry -- confirmed directly:
`register(a)` twice, `models()` shows 1 entry, withdrawing the FIRST handle drops it to 0 (should
remain 1, since the second registration is still current).

This is a `CONTRACT_ASSURANCE_DEFECT` in already-certified Layer-02/Layer-10-PASS-1/PASS-2 Python
production code -- not a canonical-DSL-only gap. The DSL's own new same-fixture/two-handle witness
did not introduce a new requirement; it is the first witness to actually EXERCISE a case
`AI-030`'s own rule already covered but no prior test happened to construct (registering the exact
same adapter object more than once was never tried before this convergence's own required
witness).

## Proposed design

### A. Manifest disposition split/relabel

- **`AI-028`** narrowed to `stream` only (own `pi:`/`rule:`/`tests:`/`python:`/`rust:` content
  unchanged in substance from the PASS-2 revision, minus the `streamSimple`-deferral paragraph,
  which moves to the new row below); `disposition: adopted` (unchanged -- this part of the row was
  never in question).
- **New `AI-031`**: `streamSimple` -- Pi source `packages/ai/src/types.ts::ProviderStreams.
  streamSimple`, surface "per-API simple-options translation, public callable obligation (Layer 11,
  deferred)," rule stating the same content PASS 2 already wrote (required by Pi; a thin per-API
  wrapper translating `SimpleStreamOptions` into that API's own specific options, delegating to
  that same module's own `stream()`) PLUS the explicit closure criterion `C10-C001` requires: the
  parity obligation this row defers is the OBSERVABLE, EXTERNALLY INVOCABLE operation --
  `streamSimple(model, context, SimpleStreamOptions) -> AssistantMessageEventStream` in Pi's own
  terms, some Minion-idiomatic equivalent SHAPE in Python/Rust (an `Adapter`-protocol method, a
  free function, whatever Layer 11's own design settles on) that a CALLER can actually invoke and
  get a stream back -- not merely internal per-provider option-translation plumbing buried inside
  adapter construction with no caller-facing entry point at all. This row is NOT closeable by
  Layer 11 building SOME internal translation helper; it is closeable only once Minion exposes a
  callable a caller can invoke to get pinned Pi's own `streamSimple` behavior, `disposition:
  deferred parity`, explicit `PROV-###`/Layer-11 future owner.
- **`AI-029`**: `disposition:` changed from `adopted` to `intentional divergence`. `rule:` text
  gains one clarifying sentence stating explicitly why (master-design authorization justifies the
  divergence; it does not make the divergence adopted Pi behavior) -- otherwise unchanged in
  substance from the PASS-2 revision, which already correctly explained the mechanism, just under
  the wrong disposition label.
- `AI-030` unchanged (the PASS-2 review's own re-review confirmed it coherent).

### B. Canonical schema and runner correction

**B1 fix** -- `llm-service-scenario.schema.json`'s own `adapterEntry` gains a conditional
constraint (`if`/`then`/`else`, JSON Schema 2020-12): `if behavior == "reject"`, `then` require
`reject_message`; `else` (i.e. `behavior == "ok"`) forbid it (`not: {required: ["reject_message"]}`)
-- both directions of the ambiguity closed, not just the missing-field one, since the review found
BOTH directions schema-valid today.

**B2 fix, revised under `C10-C004`** -- `llm_service_runner.py`'s own `resolve` query handler no
longer searches by value equality, AND no longer normalizes an ambiguous or empty result into a
plausible-looking owner via `next(...)`'s own first-match behavior. It snapshots each candidate
adapter's own `len(candidate.requests)` BEFORE issuing the request, then, after the call, collects
EVERY adapter whose own count grew and asserts there is EXACTLY one:

```python
before = {adapter_id: len(candidate.requests) for adapter_id, candidate in adapters.items()}
... # issue the request via service.stream(request), drain it
grown = [
    adapter_id
    for adapter_id, candidate in adapters.items()
    if len(candidate.requests) == before[adapter_id] + 1
]
if len(grown) != 1:
    raise AssertionError(
        f"query {query['id']!r}: expected exactly one adapter's own request log to grow by "
        f"this resolve's own stream() call, observed {len(grown)}: {grown!r}"
    )
owner = grown[0]
```

This observes WHICH adapter's own request log actually grew as a direct result of THIS specific
call -- sound regardless of whether two adapters have ever received value-equal requests, since it
never compares request CONTENT at all, only each candidate's own count delta -- and a zero- or
multiple-adapter-growth outcome (a genuine runner or `MockAdapter` instrumentation defect, or a
`LlmService` behavior this DSL's own model does not yet account for) fails LOUDLY as an explicit
assertion, never silently masqueraded as "whichever adapter happened to be checked first."

### C. Registration-handle grammar, revised under `C10-C002`

The prior grammar addressed `withdraw` by adapter FIXTURE id (`withdraw: adapter-a`), which
`AI-030`'s own normative claim -- "`register()` returns a withdrawal handle scoped to EXACTLY the
entries THAT call added" -- cannot represent once the same fixture might be registered more than
once. Design option 1 of the two the challenge offered (a unique handle id per registration action)
is adopted, since it is strictly more faithful to the real mechanism's own richness than
restricting the DSL to at-most-once-per-fixture registration:

```yaml
steps:
  - register: { adapter: adapter-a, as: reg-a-1 }
  - withdraw: reg-a-1
  - register: { adapter: adapter-a, as: reg-a-2 }   # the SAME fixture, registered again
  - withdraw: reg-a-2
```

`register` becomes an object (`{adapter: <fixture id>, as: <handle id>}`, both required,
non-empty strings) rather than a bare fixture-id string; `withdraw` now names a HANDLE id (a
`register` step's own `as`), never a fixture id directly. A `stream` step's own `identity`/`as`
shape is unchanged (it was never ambiguous -- it targets a MODEL IDENTITY, not a fixture or a
handle).

Pre-flight structural validation (`llm_service_runner.py`, a new `_validate_references`, mirroring
`tool_registry_runner.py::_validate_references`'s own established "validate the scenario's own
declarative references before any registry object is constructed" pattern -- the runner's own
input-validation boundary, not a simulation of `LlmService`'s own registration/resolution
semantics) rejects, before any step executes:

- a duplicate `adapters[].id` value (currently schema-valid, silently keeps the last one -- must
  become an explicit, loud rejection instead);
- a `register.adapter` naming a fixture no `adapters[]` entry declares (currently a raw `KeyError`
  at step-execution time -- must become a clear, descriptive rejection at validation time, matching
  the same "malformed canonical input" phrasing `tool_registry_runner.py` already uses);
- a `register.as` handle id reused by an earlier `register` step in the SAME scenario (handle ids
  must be unique within one scenario, since `withdraw` addresses exactly one by that id);
- a `withdraw` naming a handle id no EARLIER `register` step in this scenario ever declared
  (currently silently does nothing -- must become an explicit rejection).

A `withdraw` naming a handle that has ALREADY been withdrawn (a double-withdrawal of the SAME
handle) is deliberately NOT rejected -- `LlmService`'s own real withdrawal closure is safely
idempotent (it only removes an entry it can verify it still owns), and the canonical grammar should
exercise that real, legitimate behavior rather than forbid it.

### D. Observation-id namespace integrity, new under `C10-C003`

`queries[].id` and `steps[].stream.as` write into the SAME flat `observations` mapping the runner
returns; nothing previously required them to be collision-free, and nothing required an `expect`
key to name a real, declared observation. The SAME pre-flight `_validate_references` pass adds:

- every `queries[].id` and `steps[].stream.as` value, taken TOGETHER as one namespace, must be
  unique within the scenario -- a duplicate (whether two queries, two stream steps, or one of
  each) is rejected explicitly, not silently overwritten last-write-wins;
- every key in the top-level `expect` mapping must name an observation id that was actually
  declared somewhere in `llm_service.queries`/`llm_service.steps[].stream.as` -- a dangling
  expectation (naming nothing that exists) is rejected explicitly.

Explicitly PERMITTED, stated normatively rather than left implicit: an observation id that IS
declared (a query ran, or a `stream` step executed) but that `expect` never asserts on is a legal
setup-only action -- the new `E`-scenario's own initial `stream` call through adapter A exists
purely to populate A's own request log ahead of the later replacement/resolve sequence, and is
never itself named in `expect`. This is the exact case `C10-C003` named explicitly; stating it
normatively here closes the ambiguity rather than leaving it as an unstated convention a future
scenario author or reviewer would have to infer.

### E. New discriminating scenario

A new canonical scenario (or an added step/query sequence in an existing one) reproducing the
review's own exact witness, updated to the new handle-based `register`/`withdraw` grammar (`C`):
register adapter A for an identity under its own handle, issue one `stream()` call through A at
that identity as a deliberately setup-only, unasserted observation (`D`; populating A's own request
log with a value-equal entry to what a later call will also produce), register adapter B for the
SAME identity under its own separate handle (replacing A), then `resolve` that identity again --
expected owner `B`. This is the exact shape no PASS-2 scenario happened to construct (the existing
`llm-service-withdrawal-does-not-remove-a-later-replacement.yaml` never calls `stream()` through
the earlier registrant before replacement, so its own request log stays empty and the bug never
triggers there).

### F. Registration-call ownership repair, new under `C10-C005`

**Language-neutral observable rule (unchanged, now explicit):** a withdrawal handle owns exactly
the registry entries added by its OWN `register()` call -- including when two SEPARATE calls
register the IDENTICAL adapter object for the identical model identities. Registering the same
object twice does not merge or share ownership between the two calls; each call's own handle
withdraws only its own contribution, exactly as if two different adapter objects had been used.
This was already `AI-030`'s own normative claim; this convergence does not change the RULE, only
repairs an implementation that did not actually satisfy it for a case no prior test constructed.

**Python production repair.** `LlmService.register` gains a fresh, opaque per-call token -- any
value guaranteed unique to THIS call, unrelated to adapter object identity -- stored alongside the
adapter, and the withdrawal closure checks the TOKEN, not the adapter object, to decide whether it
still owns an entry:

```python
def register(self, adapter: Adapter) -> Callable[[], None]:
    token = object()  # unique per call; distinguishes this registration from any other,
                       # including a later one for the identical adapter object
    ids = [ModelId(adapter.provider, model, adapter.api) for model in adapter.models]
    for model_id in ids:
        self._adapters[model_id] = (adapter, token)

    def withdraw() -> None:
        for model_id in ids:
            entry = self._adapters.get(model_id)
            if entry is not None and entry[1] is token:
                del self._adapters[model_id]

    return withdraw
```

`stream()`/`models()` are updated to unwrap the `(adapter, token)` pair (`stream()` uses only the
adapter; `models()` is unaffected, since it already only ever read the dict's own KEYS). This is
one illustrative Python mechanism, not a mandated one -- the review's own required constraint is
only that SOME per-call-unique marker exists; a monotonically increasing counter, a `uuid4()`, or
any other opaque per-call value satisfies the same rule identically. Behavior for every
ALREADY-certified case is unchanged: ordinary registration/resolution (`token` is irrelevant to
`stream()`'s own dispatch, which reads only `adapter`), replace-in-place (a later `register()` call
always overwrites the dict entry regardless of token, so "last write wins" is untouched), and
ordinary non-stale withdrawal (the handle's own token still matches, since nothing replaced it).
The ONLY behavior this changes is the previously-broken case: two calls registering the identical
adapter object no longer share a false ownership signal, because each call's own `token` is a
distinct object regardless of whether `adapter` is too.

Double-withdrawal remains safely idempotent, unchanged: the first successful `withdraw()` call
deletes the dict entry entirely, so a second call on the SAME handle finds `entry is None` and
takes no action -- it never risks re-deleting a DIFFERENT, later registration's own entry that
might occupy the same key by then, for exactly the same reason the token-based check already
prevents that for the FIRST call.

## Required acceptance witnesses

1. Schema: `behavior: reject` with `reject_message` OMITTED -> schema validation FAILS (currently
   passes -- a genuine RED witness against the PASS-2 schema).
2. Schema: `behavior: ok` WITH `reject_message` present -> schema validation FAILS (currently
   passes -- a second, independent RED witness).
3. Runner: the review's own exact reproduction, updated to the new handle grammar (register A
   under a handle; stream through A; register B under a SEPARATE handle for the SAME identity;
   resolve) -> observed owner is `B`, not `A` (currently reports `A` -- a genuine RED witness
   against the PASS-2 runner; new under the revised grammar since the PASS-2 runner has no handle
   concept to construct this exact sequence against at all).
4. Runner/production (`C10-C002`/`C10-C005`, corrected characterization): a scenario registering
   the SAME adapter fixture twice under two DIFFERENT handles, withdrawing only the FIRST handle ->
   the SECOND registration's own entry remains resolvable (proves handles, not fixtures, are the
   unit of withdrawal, AND exercises the Python production repair directly). This is a genuine RED
   witness against the EXACT PASS-2 candidate's own `llm/service.py` -- revision 2 incorrectly
   described it as a new grammar capability with no PASS-2 baseline; the challenge review's own
   direct reproduction confirms it fails against PASS-2 production code regardless of grammar.
5. Runner (`C10-C002`): a scenario with a duplicate `adapters[].id`, a `register.adapter` naming an
   undeclared fixture, a `register.as` handle id reused by an earlier registration, and a
   `withdraw` naming an undeclared handle -- each independently -> `_validate_references` rejects
   with a clear, descriptive error before any step executes (four narrow negative witnesses, one
   per malformed shape).
6. Runner (`C10-C003`): a scenario with a duplicate observation id (two `queries[].id`, or a
   `queries[].id` colliding with a `steps[].stream.as`) -> rejected explicitly; a scenario whose
   `expect` names an undeclared observation id -> rejected explicitly; the `E`-scenario's own
   setup-only `stream` step (never named in `expect`) -> runs successfully, confirming setup-only
   observations remain legal.
7. Runner (`C10-C004`): a deliberately instrumented double-registration for the SAME identity under
   the SAME adapter object (so two DIFFERENT `adapters.items()` entries could plausibly both show
   request-count growth against a naively-shared mock) -> the corrected owner-detection either
   still resolves a genuine sole owner or raises the new explicit `AssertionError`, never silently
   picks a first match; paired with a direct unit-level check that the `len(grown) != 1` guard
   itself fires correctly for a synthetically-constructed zero-growth and multiple-growth case.
8. Manifest: `AI-028` (narrowed), new `AI-031` (with its own explicit public-callable closure
   criterion), `AI-029` (relabeled) all present with mutually coherent, single-subject dispositions;
   83/83 unique rows (82 PASS-2-era + 1 new).
9. Direct Python unit test (`C10-C005`, new in revision 3, `tests/llm/test_service.py`): the
   review's own exact reproduction at the `LlmService` API directly, with no canonical DSL in the
   way -- `w1 = service.register(a); w2 = service.register(a)` for the same identity (or
   `a`'s own declared models); `service.models()` shows one identity; `w1()`; `service.models()`
   STILL shows that identity (the second registration's own entry survives); a resolving `stream()`
   call still dispatches to `a` (trivially true here since it is the same object, but confirms
   nothing was corrupted); `w2()`; `service.models()` now shows no such identity (the CURRENT,
   still-owning handle correctly removes its own entry) -- the symmetric check the review's own
   required item 5 asks for.
10. Direct Python unit test (`C10-C005`): double-withdrawal remains idempotent -- `w1()` twice in a
    row (after `w2()` has already run, or standalone) raises nothing and leaves state unchanged on
    the second call, matching the ALREADY-established idempotent-withdrawal guarantee, now verified
    to survive the token-based rewrite too.

Confirmed via revert-and-confirm once implemented: witnesses 1-9 must FAIL against the exact
PASS-2 candidate SHAs above (schema currently accepts both malformed shapes; the PASS-2 grammar has
no handle concept and no reference validation at all, so witness 5's own four malformed-input
sub-cases are either silently accepted or fail with an unclear low-level error rather than an
explicit, descriptive rejection; the PASS-2 owner-detection cannot fail loudly; PASS-2's own
`LlmService.register` genuinely removes the second registration's entry when the first handle
withdraws, so witnesses 4 and 9 both fail) and PASS once the corrected schema/grammar/validation/
runner/production code are restored; witness 10 (double-withdrawal idempotency) already passes
against PASS-2 production code today (the pre-existing guarantee this rewrite must not regress) and
serves as a regression guard, not a RED witness.

## Normative deltas required

- `minion-agent/pi-parity-manifest.yaml`: `AI-028` narrowed (`streamSimple` content removed); new
  `AI-031` (`streamSimple`, `deferred parity`, explicit public-callable closure criterion); `AI-029`'s
  own `disposition:` changed to `intentional divergence` with one clarifying sentence added to
  `rule:`; `AI-030`'s own `rule:` gains a short note that registration is handle-scoped, addressed
  by handle id, not fixture id (documentary alignment with the corrected canonical grammar, no
  behavior change -- `AI-030`'s own Python evidence already worked this way).
- `minion-agent-docs/spec/llm.md`: mirror both disposition corrections in prose (as revision 1
  already specified), plus one sentence in the `AI-030` paragraph stating the same handle-scoped-
  not-fixture-scoped clarification.
- `minion-agent/conformance/schema/llm-service-scenario.schema.json`: the `if`/`then`/`else`
  constraint on `adapterEntry`; `step.register` changed from a bare string to an object
  (`{adapter, as}`, both required); `step.withdraw` now documented as naming a handle id, not a
  fixture id (no schema-level change needed for `withdraw` itself, since it was already a bare
  string -- only its own semantic meaning changes, stated in the schema's own `$comment`).
- `minion-agent-python/tests/conformance/llm_service_runner.py`: the count-delta ownership
  observation with explicit exactly-one-owner enforcement (`C10-C004`); a new
  `_validate_references` pre-flight pass (duplicate adapter ids, unknown/duplicate handle
  references, duplicate/dangling observation ids -- `C10-C002`/`C10-C003`).
- `minion-agent/conformance/agent/*.yaml`: all four existing PASS-2 scenarios updated to the new
  `register: {adapter, as}` grammar (a mechanical rewrite, no behavioral change to what each already
  asserts); the new discriminating registration-then-stream-then-replace-then-resolve scenario
  (`E`), authored directly against the new grammar.
- `minion-agent-python/src/minion_agent/llm/service.py`, new in revision 3 (`C10-C005`):
  `LlmService.register`/its own returned withdrawal closure, and `LlmService.stream` (to unwrap the
  new per-call token alongside the adapter) -- the ONLY Python PRODUCTION source file this
  convergence's own implementation pass touches; every other delta above is documentation, schema,
  or test/tooling.
- `minion-agent-python/tests/llm/test_service.py`, new in revision 3 (`C10-C005`): the two direct
  unit-level witnesses (required acceptance witnesses 9-10).
- `minion-agent-docs/assurance/layers/10-provider-abstraction-python.md`: a new PASS 3 section
  recording this convergence's own implementation once agreed.

## Rust implementability

Three of the four original surfaces (disposition labeling, conditional schema grammar,
observation-namespace integrity, count-delta ownership enforcement) remain shared-contract/
Python-tooling concerns implicating no Rust production code. The corrected `AI-028`/`AI-029`/
`AI-031` dispositions are simpler for a future Rust implementation pass to trace against (each row
now asserts exactly one thing), not harder. The corrected schema's own `if`/`then`/`else` grammar
and handle-scoped `register`/`withdraw` shape are both standard, language-neutral JSON Schema/DSL
constructs any future Rust scenario runner must respect structurally -- a handle-based design in
particular maps directly onto Rust's own idiomatic resource-ownership patterns (an owned handle
value, consumed by `withdraw`), noted for whoever eventually builds a Rust `llm_service` runner,
not implemented here.

`C10-C005`'s own registration-call-ownership rule, however, is a LANGUAGE-NEUTRAL observable rule
(section F above), and certified Rust's own `LlmService::register(identity, adapter)` -- already
confirmed under PASS 2 to take one `(ModelIdentity, Arc<dyn LlmAdapter>)` pair per call with no
withdrawal handle of any kind (`AI-030`'s own Rust status, unaffected by this convergence) -- has
no withdrawal mechanism to exhibit this exact defect YET, since it cannot withdraw at all. This
convergence does NOT prescribe how a future Rust implementation pass represents per-call ownership
(an owned, move-only handle type Rust's own borrow checker would enforce single-use on is one
natural fit, matching how `_Reservation`'s own one-shot design was chosen for a different Layer-09
finding, but this is Rust's own future implementation decision, not mandated here) -- only that
WHEN Rust eventually implements withdrawal, it must satisfy the SAME observable rule: two
registration calls for the identical adapter object must remain independently ownable and
independently withdrawable. Recorded as a future Rust obligation alongside `L10-R003`, not resolved
by this convergence.

## Out of scope / deferred

- `L10-R003` (current Rust production permits an eager adapter-start failure) -- untouched,
  remains an open, disclosed Rust-implementation defect for a future Rust pass.
- `C10-C005`'s own future Rust obligation (certified Rust `LlmService::register` has no withdrawal
  mechanism at all yet, so cannot currently exhibit or fix this exact defect) -- recorded, not
  implemented; Rust's own eventual withdrawal design is that future pass's own decision.
- Any Rust `llm_service` canonical runner implementation -- not started; the current gap (Rust's
  own agent-conformance discovery does not yet classify `llm_service`-keyed documents at all) is
  pre-existing, unaffected by this convergence, and not a new obligation created here.
- Layer 11 (Real providers) -- not started.

```text
CONVERGENCE CONTRACT
    PROPOSED -- AWAITING INDEPENDENT AGREEMENT (revision 3)

OPEN FINDINGS
    L10-R001 (bundled, same root cause as L10-R002, non-blocking on its own)
    L10-R002
    L10-R004
    C10-C005 (Python production repair, new in revision 3)

PROVISIONALLY ACCEPTED (confirmed closed by the revision-2 challenge; unchanged in revision 3)
    C10-C001
    C10-C002
    C10-C003
    C10-C004

CORE DESIGN RETAINED (accepted in revision 1, unchanged)
    AI-028 narrowed to stream (adopted); new AI-031 for streamSimple (deferred parity)
    AI-029 relabeled intentional divergence; AI-030 unchanged except a documentary handle-scoping
      note
    if/then/else schema constraint tying reject_message to behavior
    count-delta ownership observation with exactly-one-owner enforcement (not value equality)
    handle-scoped register/withdraw grammar with pre-flight reference validation
    unified, validated observation-id namespace with an explicit setup-only-observation policy
    new register-A/stream-A/replace-B/resolve discriminating scenario

NEW IN REVISION 3 (`C10-C005`)
    LlmService.register's own withdrawal closure checked ADAPTER OBJECT identity, not
    REGISTRATION CALL identity -- registering the identical adapter object twice made both
    calls' own handles indistinguishable, so the FIRST handle incorrectly removed the SECOND
    (current) registration's own entry. Confirmed by the reviewer's own direct reproduction
    against the exact PASS-2 candidate. Repaired with a fresh, opaque per-call token stored
    alongside the adapter; the withdrawal closure now checks the token, not the adapter object.
    Every already-certified behavior (resolution, replace-in-place, non-stale withdrawal,
    double-withdrawal idempotency) is unchanged; only the previously-broken same-object-twice
    case is fixed. Two new direct Python unit witnesses added (tests/llm/test_service.py); the
    canonical same-fixture/two-handle witness is now correctly characterized as a genuine RED
    witness against PASS-2 production code, not a new grammar-only capability.

ACCEPTANCE WITNESSES
    conformance/schema/llm-service-scenario.schema.json (2 new negative schema witnesses)
    minion-agent-python/tests/conformance/llm_service_runner.py (count-delta ownership with
      exactly-one enforcement; new _validate_references negative witnesses -- duplicate adapter
      id, unknown/duplicate handle reference, duplicate/dangling observation id)
    conformance/agent/ (1 new discriminating scenario reproducing the review's own exact witness
      under the new handle grammar; 1 new same-fixture-two-handles witness -- now a genuine RED
      witness against PASS-2 PRODUCTION code; 4 existing scenarios mechanically updated to the
      new grammar)
    minion-agent-python/tests/llm/test_service.py (2 new direct unit witnesses: symmetric
      current-handle withdrawal, double-withdrawal idempotency under the token rewrite)
    pi-parity-manifest.yaml (AI-028 narrowed, new AI-031 with explicit closure criterion, AI-029
      relabeled, AI-030 documentary handle-scoping note)
    -- none yet written; this is a contract/evidence checkpoint, not an implementation pass

NORMATIVE DELTAS
    minion-agent/pi-parity-manifest.yaml (AI-028/AI-029/AI-030/new AI-031)
    minion-agent-docs/spec/llm.md (disposition-framing corrections; AI-030 handle-scoping note)
    minion-agent/conformance/schema/llm-service-scenario.schema.json (if/then/else grammar;
      register becomes {adapter, as}; withdraw documented as handle-scoped)
    minion-agent-python/src/minion_agent/llm/service.py (Python PRODUCTION repair, new in
      revision 3 -- the only production source file this convergence's implementation pass
      touches)
    minion-agent-python/tests/llm/test_service.py (2 new direct unit witnesses, new in revision 3)
    minion-agent-python/tests/conformance/llm_service_runner.py (count-delta ownership with
      exactly-one enforcement; new _validate_references pre-flight pass)
    minion-agent/conformance/agent/*.yaml (4 scenarios updated to new grammar; 1 new scenario)
    minion-agent-docs/assurance/layers/10-provider-abstraction-python.md (new PASS 3 section)
```
