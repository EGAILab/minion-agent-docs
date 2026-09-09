# Layer 10 — L10-R001/R002/R004 contract convergence (disposition semantics + canonical-scenario grammar/observation)

**Revision 2, NOT yet approved.** Revision 1 (this same file) was independently challenged
(`assurance/layers/10-provider-abstraction-convergence-challenge.md`, docs PR #47, review commit
`60ef1cd5410c81bd33b526859cca5d49dc096584`): **CONVERGENCE CONTRACT — CHANGES REQUIRED**. The
disposition split/relabel (A), the conditional schema fix and count-delta observation direction
(B1/B2), and the new register-A/stream-A/replace-B/resolve witness (C) were all accepted as-is.
Pinned Pi was independently reconfirmed to require `streamSimple` as a public, invocable operation,
not merely internal plumbing. Four challenge findings required revision:

- **`C10-C001`** (streamSimple's own deferred-parity closure criterion was too weak): the proposed
  `AI-031` risked being markable "complete" once SOME internal per-provider option translation
  existed, without Minion ever exposing an externally invocable operation matching Pi's own
  `streamSimple(model, context, options) -> AssistantMessageEventStream` shape. Revision 2 states
  the observable-callable closure criterion explicitly.
- **`C10-C002`** (registration-handle grammar was ambiguous): the proposed canonical grammar still
  addressed `withdraw` by adapter FIXTURE id, not by a specific REGISTRATION's own handle --
  undefined for a fixture registered more than once, for a duplicate fixture id, and for an
  unknown register/withdraw reference. Revision 2 redesigns `register`/`withdraw` around explicit,
  unique handle ids and adds pre-flight reference validation, following the same "runner validates
  structural references before any registry object is touched" pattern
  `tool_registry_runner.py::_validate_references` already established.
- **`C10-C003`** (observation-id namespace had no integrity rules): `queries[].id` and
  `steps[].stream.as` write the same `observations` mapping with no uniqueness or
  dangling-reference check. Revision 2 adds both, and states explicitly that an observation never
  referenced by `expect` is a legal setup-only action (the new C-witness's own A-stream step is the
  concrete example).
- **`C10-C004`** (count-delta observation could still silently pick a wrong owner): the proposed
  `next(...)` search silently takes the first adapter whose count grew, masking a zero- or
  multiple-match runner defect as a plausible-looking owner. Revision 2 collects every adapter
  whose own count grew and asserts EXACTLY one, failing explicitly otherwise.

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

**Determination:** enter `CONTRACT_CONVERGENCE` for two coupled surfaces: (A) manifest disposition
semantics as applied to `AI-028`/`AI-029`/`AI-030` (`L10-R001`/`L10-R002`), and (B) the
`llm-service` canonical scenario schema/runner's own grammar completeness and ownership-observation
soundness (`L10-R004`). This is a `§11.8.3` characterization pass, proposed here for Codex's own
independent agreement. No implementation in this artifact -- `§11.8.1`'s "freeze unrelated
implementation work" applies.

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
4. Runner (`C10-C002`): a scenario registering the SAME adapter fixture twice under two DIFFERENT
   handles, withdrawing only the FIRST handle -> the SECOND registration's own entry remains
   resolvable (proves handles, not fixtures, are the unit of withdrawal).
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

Confirmed via revert-and-confirm once implemented: witnesses 1-3 and 5-7 must FAIL against the
exact PASS-2 candidate SHAs above (schema currently accepts both malformed shapes; the PASS-2
grammar has no handle concept and no reference validation at all; the PASS-2 owner-detection
cannot fail loudly) and PASS once the corrected schema/grammar/validation/runner are restored;
witness 4 is a NEW capability the PASS-2 grammar could not even express (no handle concept to
construct it with), so it has no PASS-2 baseline to revert against -- it is added as permanent
regression evidence for the new grammar directly.

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
- `minion-agent-docs/assurance/layers/10-provider-abstraction-python.md`: a new PASS 3 section
  recording this convergence's own implementation once agreed.

## Rust implementability

No Rust production code is implicated by this convergence -- all four surfaces (disposition
labeling, conditional schema grammar, handle-scoped registration grammar, observation-namespace
integrity, count-delta ownership enforcement) are shared-contract/Python-tooling concerns. The
corrected `AI-028`/`AI-029`/`AI-031` dispositions are simpler for a future Rust implementation pass
to trace against (each row now asserts exactly one thing), not harder. The corrected schema's own
`if`/`then`/`else` grammar and handle-scoped `register`/`withdraw` shape are both standard,
language-neutral JSON Schema/DSL constructs any future Rust scenario runner must respect
structurally -- a handle-based design in particular maps directly onto Rust's own idiomatic
resource-ownership patterns (an owned handle value, consumed by `withdraw`), noted for whoever
eventually builds a Rust `llm_service` runner, not implemented here. `L10-R003` remains the sole
open Rust-production obligation, unaffected by and explicitly out of scope for this convergence.

## Out of scope / deferred

- `L10-R003` (current Rust production permits an eager adapter-start failure) -- untouched,
  remains an open, disclosed Rust-implementation defect for a future Rust pass.
- Any Rust `llm_service` canonical runner implementation -- not started; the current gap (Rust's
  own agent-conformance discovery does not yet classify `llm_service`-keyed documents at all) is
  pre-existing, unaffected by this convergence, and not a new obligation created here.
- Layer 11 (Real providers) -- not started.

```text
CONVERGENCE CONTRACT
    PROPOSED -- AWAITING INDEPENDENT AGREEMENT (revision 2)

OPEN FINDINGS
    L10-R001 (bundled, same root cause as L10-R002, non-blocking on its own)
    L10-R002
    L10-R004

CORE DESIGN RETAINED (accepted in revision 1, unchanged)
    AI-028 narrowed to stream (adopted); new AI-031 for streamSimple (deferred parity)
    AI-029 relabeled intentional divergence; AI-030 unchanged
    if/then/else schema constraint tying reject_message to behavior
    count-delta ownership observation (not value equality)
    new register-A/stream-A/replace-B/resolve discriminating scenario

CHALLENGE FINDINGS ADDRESSED
    C10-C001  AI-031's own closure criterion now states the deferred parity obligation is an
              externally invocable operation matching Pi's own streamSimple(model, context,
              options) -> stream shape, not merely internal per-provider translation plumbing
    C10-C002  register/withdraw redesigned around explicit, unique handle ids (not fixture ids);
              new pre-flight _validate_references rejects duplicate adapter ids, unknown/
              duplicate handle references, matching tool_registry_runner.py's own established
              reference-validation pattern
    C10-C003  queries[].id and steps[].stream.as now share one namespace with uniqueness and
              dangling-expectation validation; setup-only unasserted observations explicitly
              stated legal
    C10-C004  owner detection collects every adapter whose own request count grew and asserts
              exactly one, raising explicitly on zero or multiple matches rather than silently
              picking a first match

ACCEPTANCE WITNESSES
    conformance/schema/llm-service-scenario.schema.json (2 new negative schema witnesses)
    minion-agent-python/tests/conformance/llm_service_runner.py (count-delta ownership with
      exactly-one enforcement; new _validate_references negative witnesses -- duplicate adapter
      id, unknown/duplicate handle reference, duplicate/dangling observation id)
    conformance/agent/ (1 new discriminating scenario reproducing the review's own exact witness
      under the new handle grammar; 1 new same-fixture-two-handles witness; 4 existing scenarios
      mechanically updated to the new grammar)
    pi-parity-manifest.yaml (AI-028 narrowed, new AI-031 with explicit closure criterion, AI-029
      relabeled, AI-030 documentary handle-scoping note)
    -- none yet written; this is a contract/evidence checkpoint, not an implementation pass

NORMATIVE DELTAS
    minion-agent/pi-parity-manifest.yaml (AI-028/AI-029/AI-030/new AI-031)
    minion-agent-docs/spec/llm.md (disposition-framing corrections; AI-030 handle-scoping note)
    minion-agent/conformance/schema/llm-service-scenario.schema.json (if/then/else grammar;
      register becomes {adapter, as}; withdraw documented as handle-scoped)
    minion-agent-python/tests/conformance/llm_service_runner.py (count-delta ownership with
      exactly-one enforcement; new _validate_references pre-flight pass)
    minion-agent/conformance/agent/*.yaml (4 scenarios updated to new grammar; 1 new scenario)
    minion-agent-docs/assurance/layers/10-provider-abstraction-python.md (new PASS 3 section)
```
