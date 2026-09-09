# Layer 10 — L10-R001/R002/R004 contract convergence (disposition semantics + canonical-scenario grammar/observation)

**Revision 1, PROPOSED — AWAITING INDEPENDENT AGREEMENT.**

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
  streamSimple`, surface "per-API simple-options translation (Layer 11, deferred)," rule stating
  the exact same content PASS 2 already wrote (required by Pi; a thin per-API wrapper translating
  `SimpleStreamOptions` into that API's own specific options, delegating to that same module's own
  `stream()`; nothing generic to implement at Layer 10's own abstraction level), `disposition:
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

**B2 fix** -- `llm_service_runner.py`'s own `resolve` query handler no longer searches by value
equality. It snapshots each candidate adapter's own `len(candidate.requests)` BEFORE issuing the
request, then, after the call, identifies the SOLE adapter whose own count increased by exactly
one:

```python
before = {adapter_id: len(candidate.requests) for adapter_id, candidate in adapters.items()}
... # issue the request via service.stream(request), drain it
owner = next(
    adapter_id
    for adapter_id, candidate in adapters.items()
    if len(candidate.requests) == before[adapter_id] + 1
)
```

This observes WHICH adapter's own request log actually grew as a direct result of THIS specific
call -- sound regardless of whether two adapters have ever received value-equal requests, since it
never compares request CONTENT at all, only each candidate's own count delta.

### C. New discriminating scenario

A new canonical scenario (or an added step/query sequence in an existing one) reproducing the
review's own exact witness: register adapter A for an identity, issue one `stream()` call through
A at that identity (populating A's own request log with a value-equal entry to what a later call
will also produce), register adapter B for the SAME identity (replacing A), then `resolve` that
identity again -- expected owner `B`. This is the exact shape no PASS-2 scenario happened to
construct (the existing `llm-service-withdrawal-does-not-remove-a-later-replacement.yaml` never
calls `stream()` through the earlier registrant before replacement, so its own request log stays
empty and the bug never triggers there).

## Required acceptance witnesses

1. Schema: `behavior: reject` with `reject_message` OMITTED -> schema validation FAILS (currently
   passes -- a genuine RED witness against the PASS-2 schema).
2. Schema: `behavior: ok` WITH `reject_message` present -> schema validation FAILS (currently
   passes -- a second, independent RED witness).
3. Runner: the review's own exact reproduction (register A; stream through A; register B for the
   SAME identity; resolve) -> observed owner is `B`, not `A` (currently reports `A` -- a genuine
   RED witness against the PASS-2 runner).
4. Manifest: `AI-028` (narrowed), new `AI-031`, `AI-029` (relabeled) all present with mutually
   coherent, single-subject dispositions; 83/83 unique rows (82 PASS-2-era + 1 new).

Confirmed via revert-and-confirm once implemented: witnesses 1-3 must FAIL against the exact
PASS-2 candidate SHAs above (schema currently accepts both malformed shapes; runner currently
reports the wrong owner) and PASS once the corrected schema/runner/new scenario are restored.

## Normative deltas required

- `minion-agent/pi-parity-manifest.yaml`: `AI-028` narrowed (`streamSimple` content removed); new
  `AI-031` (`streamSimple`, `deferred parity`); `AI-029`'s own `disposition:` changed to
  `intentional divergence` with one clarifying sentence added to `rule:`.
- `minion-agent-docs/spec/llm.md`: mirror both disposition corrections in prose -- the
  implementation-module paragraph split to name `streamSimple` as deferred-parity content
  distinctly from `stream`'s own adopted status; the resolution paragraph's own framing corrected
  from implying "adopted, but simplified" to stating plainly this is an intentional, disclosed
  divergence.
- `minion-agent/conformance/schema/llm-service-scenario.schema.json`: the `if`/`then`/`else`
  constraint on `adapterEntry`.
- `minion-agent-python/tests/conformance/llm_service_runner.py`: the snapshot-based ownership
  observation.
- `minion-agent/conformance/agent/*.yaml`: the new discriminating registration-then-stream-then-
  replace-then-resolve scenario.
- `minion-agent-docs/assurance/layers/10-provider-abstraction-python.md`: a new PASS 3 section
  recording this convergence's own implementation once agreed.

## Rust implementability

No Rust production code is implicated by this convergence -- both surfaces (disposition labeling,
canonical schema/runner correctness) are shared-contract/Python-tooling concerns. The corrected
`AI-028`/`AI-029`/`AI-031` dispositions are simpler for a future Rust implementation pass to trace
against (each row now asserts exactly one thing), not harder. The corrected schema's own
`if`/`then`/`else` grammar is a standard JSON Schema construct any future Rust scenario runner must
also respect structurally (reject an adapter entry missing its own required `reject_message`, and
one carrying an inapplicable one) -- noted for whoever eventually builds a Rust `llm_service`
runner, not implemented here. `L10-R003` remains the sole open Rust-production obligation,
unaffected by and explicitly out of scope for this convergence.

## Out of scope / deferred

- `L10-R003` (current Rust production permits an eager adapter-start failure) -- untouched,
  remains an open, disclosed Rust-implementation defect for a future Rust pass.
- Any Rust `llm_service` canonical runner implementation -- not started; the current gap (Rust's
  own agent-conformance discovery does not yet classify `llm_service`-keyed documents at all) is
  pre-existing, unaffected by this convergence, and not a new obligation created here.
- Layer 11 (Real providers) -- not started.

```text
CONVERGENCE CONTRACT
    PROPOSED -- AWAITING INDEPENDENT AGREEMENT (revision 1)

OPEN FINDINGS
    L10-R001 (bundled, same root cause as L10-R002, non-blocking on its own)
    L10-R002
    L10-R004

ACCEPTANCE WITNESSES
    conformance/schema/llm-service-scenario.schema.json (2 new negative schema witnesses)
    minion-agent-python/tests/conformance/llm_service_runner.py (corrected ownership observation)
    conformance/agent/ (1 new discriminating scenario reproducing the review's own exact witness)
    pi-parity-manifest.yaml (AI-028 narrowed, new AI-031, AI-029 relabeled)
    -- none yet written; this is a contract/evidence checkpoint, not an implementation pass

NORMATIVE DELTAS
    minion-agent/pi-parity-manifest.yaml (AI-028/AI-029/new AI-031)
    minion-agent-docs/spec/llm.md (disposition-framing corrections)
    minion-agent/conformance/schema/llm-service-scenario.schema.json (if/then/else grammar)
    minion-agent-python/tests/conformance/llm_service_runner.py (snapshot-based ownership)
    minion-agent/conformance/agent/*.yaml (new scenario)
    minion-agent-docs/assurance/layers/10-provider-abstraction-python.md (new PASS 3 section)
```
