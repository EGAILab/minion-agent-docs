# Layer 10 (Provider abstraction + mock adapter) — Python/shared certification, PASS 1

## Layer scope

Per `process/implementation-conformance-workflow.md` §6's own dependency-ordered audit list,
Layer 10 is "Provider abstraction + mock adapter" -- the GENERIC seam between the Agent/tool
layers and a concrete model provider: the `Adapter` implementation-module contract, `LlmService`'s
own registration/resolution/dispatch, the never-raises stream contract, and the `MockAdapter`
reference implementation that exercises it. It explicitly does NOT cover any real provider's own
wire-protocol encoding (Responses/Completions streaming decode, thinking/text-signature replay,
active transport cancellation) -- that is Layer 11 ("Real providers," `PROV-###`, master design
Phase 5), not started, and untouched by this pass.

## Existing-code audit (mandatory before assuming this layer starts from zero)

Per the project's own existing-code rule, this layer's own target surface was read from scratch
before any new work began, not assumed unimplemented merely because no `assurance/layers/10-*`
file existed yet. Finding: it is NOT a from-zero layer. `llm/service.py` (`Adapter` protocol,
`LlmService`, `ModelId`, `Request`, `_settled()`), `llm/errors.py`
(`LlmError`/`UnknownModelError`/`AdapterProtocolError`), and `llm/adapters/mock.py`
(`MockAdapter`/`ScriptedResponse`/`_Replay`) already exist, are already extensively exercised by
Layer 02's own conformance evidence (`conformance/agent/eager-invalid-model-fails-before-stream.
yaml`, `public-stream-fuses-after-first-terminal.yaml`, `represented-provider-error-rides-stream.
yaml`, and others), and were already independently Pi-parity-audited under Layer 02's own pass
(`assurance/layers/02-llm.md`, findings `LLM-011`, `LLM-012`, `LLM-018`, `LLM-019`, `LLM-F006`,
`LLM-F007`, `LLM-F009`, `LLM-F010`) -- built and certified as necessary infrastructure to test the
LLM vocabulary itself, before Layer 10 existed as its own dependency-order entry.

What was genuinely missing, confirmed by direct inspection rather than assumed: `spec/llm.md`, the
NORMATIVE language-neutral contract both Python and Rust are meant to be built from, said nothing
at all about the `Adapter` protocol's own shape, `LlmService`'s own registration/resolution
mechanism, or the `MockAdapter` reference-implementation contract -- only Python docstrings and
manifest `rule:` prose (`AI-011`, `AI-012`) carried this material, and neither of those rows
actually covers the adapter-protocol/registry surface itself (`AI-011` covers `Context`'s own
`system_prompt`/`messages`/`tools` fields; `AI-012` covers the never-raises return contract). A
future Rust implementer of this seam (already substantially done under Layer 02's own Rust pass,
per its own handoff notes -- see "Rust status" below) would have had no normative spec section to
build from or check against for this specific surface. This is the documentary gap this pass
closes; it is not a code defect in the existing implementation.

## Pi source audit (this pass, before any spec/manifest change)

Re-read directly against pinned Pi (`ref-repos/pi` @ `b7bb00b936dbe21b8e160b3e89efdec361846699`,
confirmed matching `pi-parity-manifest.yaml`'s own pinned revision):

- `packages/ai/src/types.ts:264-336` -- `ProviderStreams` (the uniform implementation-module
  contract every `packages/ai/src/api/*` module satisfies: `stream(model, context, options?)`) and
  `StreamFunction` (the caller-facing callable shape, with its own doc comment stating the
  never-raises contract in the same words the existing `AI-012`/`LLM-018` audit already certified).
- `packages/ai/src/models.ts:735-812` -- `createProvider`/`apiFor`/`dispatch`: Pi's own two-level
  resolution (a `Provider` object built once, optionally keyed by `model.api` for a provider
  spanning more than one wire protocol; a model whose api has no matching implementation produces
  an IN-BAND stream error via `lazyStream`, not an eager exception).

Both are new, explicit citations -- the existing Layer-02 audit referenced `StreamFunction`'s own
doc comment for the never-raises contract already, but neither `models.ts`'s own two-level
resolution mechanism nor a direct comparison against Minion's own flat `LlmService` registry had
been written down anywhere before this pass.

## Findings

### Finding 1 -- `AI-028`/`AI-029`: adapter-protocol and registry surface had no manifest row

**Classification:** `CONTRACT_ASSURANCE_DEFECT`, documentary only -- traceability/evidence-pointer
completeness, not a semantic or behavioral defect. The underlying Python implementation was already
correct and already had genuine canonical/unit-test evidence; nothing pointed FROM that evidence
back to an explicit Pi-source citation for the adapter-protocol shape or the registry-resolution
mapping specifically.

**Remediation:** two new manifest rows. `AI-028` (adapter/implementation-module contract): maps
Pi's `ProviderStreams`/`StreamFunction` to Minion's `Adapter` protocol, citing `MockAdapter` as the
certified reference implementation. `AI-029` (registration and model resolution): maps Pi's own
two-level `Provider`/`apiFor` resolution to Minion's flat `LlmService._adapters` registry as an
intentional, disclosed architectural SIMPLIFICATION (not a literal port) -- explicitly cross-
referencing master design §4's own eager/lazy boundary as the authorizing decision for collapsing
Pi's two distinct failure cases (no `Provider` selected at all; a selected `Provider` lacking an
implementation for this model's own `api`) into Minion's single eager `UnknownModelError` check.
Both rows cite ALREADY-EXISTING, already-passing evidence (`eager-invalid-model-fails-before-
stream`, `test_a_later_adapter_replaces_an_earlier_one_for_the_same_model`, etc.) -- no new test
was required, since the behavior these rows describe was already correctly implemented and already
evidenced; the rows themselves are what was missing.

**Pi reproduction:** direct source reads above; no Rust or Python behavior change follows from this
finding, only new manifest/spec content.

### Finding 2 -- `spec/llm.md` had no normative section for the provider-abstraction seam

**Classification:** `CONTRACT_ASSURANCE_DEFECT`. The frozen master design and pinned Pi both
specify this contract; the informal record of it (Python docstrings, the Layer-02 assurance
narrative) was accurate but never promoted into the actual normative spec document a Rust
implementer -- or a future Python remediation pass -- is meant to build from and check against.

**Remediation:** a new `spec/llm.md` "## Provider abstraction (Layer 10)" section, formalizing
both `AI-028` and `AI-029`'s own content as normative prose: the implementation-module contract,
the reference-implementation characterization of `MockAdapter`, the registration/resolution
mapping (including the explicit disclosure that Minion's eager `UnknownModelError` collapses two
Pi-distinguishable cases into one), and the existing `ModelId.api` default caveat (previously only
in a Python docstring, now normative) restated precisely, unchanged in substance from
`LLM-F006`'s own already-certified disclosure.

## Regression verification for previously-closed findings

`LLM-011`, `LLM-012`, `LLM-018`, `LLM-019`, `LLM-F006`, `LLM-F007`, `LLM-F009`, `LLM-F010`
(Layer 02): unaffected -- this pass's own diff is confined to `pi-parity-manifest.yaml` (two new
rows, no existing row's `rule:`/`python:`/`tests:`/`disposition` field touched) and `spec/llm.md`
(one new section appended; every existing line unchanged). No Python source file was modified.
`AI-027` (Layer 09's own additive `Request.signal` field): unaffected, not referenced by either new
row's own scope.

## Quality gates (fresh, this pass)

```text
pytest (full suite):                 1131 passed, 19 xfailed (pre-existing, unrelated), 0 failed
coverage (certified src packages):   100.00%, unchanged (no source file touched)
ruff check:                          clean (whole tree)
ruff format --check:                 clean on every file this pass touched; the same pre-existing,
                                      unrelated 7-file drift noted in every earlier layer's own
                                      passes remains untouched and out of this pass's ownership
mypy (configured scope, src only):   clean, 0 errors, 58 source files
conformance/ (full):                 298 passed, 19 xfailed -- unaffected, unchanged this pass (no
                                      canonical scenario added/changed; both new manifest rows cite
                                      ALREADY-EXISTING passing scenarios)
manifest parse + unique-ID audit:    81 / 81 unique (79 existing + AI-028 + AI-029)
```

## Active findings (after this pass)

```text
PI_PARITY_DEFECT              none
CONTRACT_ASSURANCE_DEFECT     none -- both findings this pass closed by documentary-only remediation
PI_BEHAVIOR_UNCERTAIN         none
unapproved intentional divergence   none
disclosed Minion architectural mapping   LlmService's own flat, single-level registry
                               (AI-029) collapsing Pi's own two-level Provider/apiFor resolution
                               and its two distinct failure cases into one eager check -- already
                               implemented and already exercised, now explicitly cross-referenced
                               against the exact Pi source and the exact master-design authorization
disclosed Minion-specific constraint   ModelId.api defaults to "mock" (LLM-F006, unchanged,
                               correctly still deferred -- becomes actively wrong only once Layer 11
                               adds a second api value, not yet reached)
Rust cross-language dependency      see "Rust status" below
Layer 11                       NOT STARTED
```

## Rust status

Not audited or modified by this pass (Python/shared-contract owner's own hard boundary --
`minion-agent-rust/**` is out of scope unless the ownership rule changes for this task). Both new
manifest rows' own `rust:` pointers note, based on `assurance/layers/02-llm.md`'s own prior Rust
handoff section (read, not modified, this pass), that a typed adapter trait/mock and the exact
model-lookup/eager-stream-creation boundary already exist in `minion-agent-rust/crates/minion-
agent/src/llm/` from Layer 02's own already-certified Rust pass -- this is a claim carried forward
from that prior, already-merged assurance record, not independently re-verified against Rust
source in this pass. Independent Rust confirmation (whether the existing Rust implementation
already satisfies `AI-028`/`AI-029` as newly formalized, or needs a small remediation) is Codex's
own next action, per the standing cross-language workflow -- not assumed complete here merely
because the underlying code likely already exists.

## Verdict

```text
Python Layer 10     CERTIFIED (self-certified; pending independent Rust contract review)
Rust Layer 10          STATUS UNKNOWN -- likely substantially satisfied by Layer 02's own prior
                          Rust pass, not independently confirmed by this pass
shared Layer-10 contract   READY FOR INDEPENDENT RUST CONTRACT REVIEW of AI-028/AI-029 and the new
                             spec/llm.md section against the exact Rust symbols Layer 02's own
                             handoff already named
Layer 10 cross-language     NOT CLOSED
Layer 11                     NOT STARTED
```

## Workflow-process retrospective note (this pass)

A layer's own dependency-order position in `process/implementation-conformance-workflow.md` §6 is
independent of whether its underlying code and even most of its Pi-parity evidence already exist:
Layer 10's own target surface was built, exercised, and largely audited as necessary infrastructure
during Layer 02's own pass, long before Layer 10's own turn in the audit order arrived. Treating
"Layer 10 has not started" as "Layer 10's own code does not exist yet" would have led to redundant
reimplementation; the existing-code rule's own instruction ("audit it from scratch... then keep,
realign, or replace only what evidence requires") produced the correct outcome here -- a
documentary-formalization pass, not a build pass. This is consistent with, not a new instance of,
the general principle already stated in that rule; recorded here only because this is the first
layer in this project's history where the gap between "code exists" and "layer has started" was
this large (a full prior layer's worth of already-certified work), which is worth a future retro-
spective noting explicitly if it recurs (e.g., if Layer 12 "Execution seams" turns out to already
be substantially built under Layer 06's own tool-execution pass).

## Next action (superseded -- see PASS 2 below)

Create the Layer 10 coordination issue in `minion-agent` (`STATUS: PYTHON_SHARED`, `NEXT_OWNER:
Claude` while candidates are pushed, then `RUST_CONTRACT_REVIEW`/`NEXT_OWNER: Codex` once pushed).
Push this pass's commits to new `layer/10-python-shared` branches (both repos); open paired PRs
identifying the layer, companion PR, coordination issue, exact candidate head SHAs, pass type
(Python/shared, documentary-only), and stop condition (ready for independent Rust contract review
of `AI-028`/`AI-029` and the new `spec/llm.md` section; Layer 11 remains not started; no Python or
Rust behavior was changed by this pass). Request Codex confirm whether the existing Rust
implementation already satisfies both new rows as formalized, or identify a narrow remediation, per
the standing ownership flow. Do not implement Rust. Do not start Layer 11.

# PASS 2 — remediate L10-R001..R004 (misstated Pi shape, mixed dispositions, current Rust defect, missing canonical evidence)

## Re-review reference

The independent Rust contract review of the PASS-1 candidate (code PR #20 @
`4deef8f8d8dba1f109057ee03755aa7a55ad1a7c`, docs PR #45 @ `1d395df1770cc7d6a32bc4597f1220c4f8e3de5b`,
`assurance/layers/10-provider-abstraction-rust-contract-review.md`, review commit
`d43559dfbc1770bb8508fcb2f27a88c0f5a4530c`) **REJECTED** the candidate with four findings:

- **`L10-R001`** (`PI_PARITY_DEFECT`): PASS 1 misread pinned Pi's own `ProviderStreams.streamSimple`
  as optional; it is required (only `fetchDeferred?`/`cancelDeferred?` are optional). PASS 1's own
  "direct, faithful mapping" claim for Minion's single-operation `Adapter` protocol needed an
  explicit disposition for the missing second required operation, not a false "optional" reading.
- **`L10-R002`** (`CONTRACT_ASSURANCE_DEFECT`): `AI-029` mixed Pi's own single-vs-API-map provider
  dispatch, Minion's eager full-identity simplification, Minion-only registration/withdrawal
  mechanics, and `models()` introspection under ONE `adopted` disposition -- different semantic
  subjects that cannot coherently share one disposition. The row's own Rust evidence was also
  materially inaccurate (current Rust has no adapter-declared model set, withdrawal handle, or
  `models()` at all).
- **`L10-R003`** (`PI_PARITY_DEFECT`, current Rust production, OPEN): `LlmAdapter::start` may return
  an eager, typed `AdapterStartError` after the model has already resolved and the adapter's own
  code has already run -- contrary to Pi's own never-raises boundary, which requires an expected
  failure at that point to settle IN the returned stream. The permanent Rust test
  `adapter_start_failure_remains_eager_and_typed` locks this in as current, not hypothetical,
  behavior.
- **`L10-R004`** (`CONTRACT_ASSURANCE_DEFECT`): the cited canonical scenarios never exercised the
  newly normative registration/replacement/withdrawal/introspection/resolution/failure-settlement
  rules -- only stream-terminal-content scenarios, none of which construct a multi-adapter registry
  or an adapter-DETECTED (as opposed to mid-network) failure.

The review's own read-only checks (Rust adapter/stream/conformance tests 11/11, schema validation
185/185, manifest 81/81 unique IDs) passed but explicitly did not close any finding: "Green tests
do not close the findings because the new contract is misstated and the cited tests do not
discriminate the missing behavior."

## Findings, reproduced against the exact candidate and remediated

### L10-R001 — `streamSimple` misread as optional

**Re-review finding:** confirmed by re-reading `packages/ai/src/types.ts:264-281` directly: neither
`stream` nor `streamSimple` carries a `?`; both are required. Only `fetchDeferred?`/`cancelDeferred?`
are optional.

**Root cause:** re-reading `streamSimple`'s own implementations directly (e.g.
`packages/ai/src/api/openai-completions.ts:683-702`), it is not a semantically distinct operation --
every API module's own `streamSimple` is a thin wrapper translating the provider-neutral
`SimpleStreamOptions` into that ONE API's own specific options shape, then delegating to that SAME
module's own `stream()`. Its content is therefore inherently wire-protocol-specific, with nothing
generic to specify at Layer 10's own abstraction level.

**Remediation:** `AI-028`'s own `rule:` corrected to state both operations are required, and
`streamSimple`'s own translation responsibility explicitly DEFERRED to Layer 11 (`PROV-###`) --
disclosed as a deferred mapping, not silently declared optional or silently omitted. `spec/llm.md`
corrected identically.

### L10-R002 — AI-029 mixed several semantic subjects under one disposition

**Re-review finding:** confirmed -- the prior `AI-029` covered Pi's own resolution mapping
(genuinely Pi-motivated), Minion's eager-lookup simplification (a disclosed architectural choice
authorized by master design §4), and Minion-only registration/withdrawal/introspection mechanics
(no Pi analogue at all) as one row with one `adopted` disposition.

**Remediation:** split into two rows. `AI-029` narrowed to ONLY the resolution/unresolvable-identity
mapping (kept `disposition: adopted`, since this half IS genuinely Pi-motivated via
`createProvider`/`apiFor`/`dispatch` plus master design's own eager/lazy boundary). New `AI-030`
covers registration/replacement/withdrawal/introspection (`disposition: intentional divergence`,
matching the pattern `AG-011` already uses for `Inbox.inject` -- a Minion architectural extension
with literally no Pi behavior to diverge FROM, since Pi has no registry concept at all). Both rows'
own Rust evidence corrected to match direct source re-reads (see `L10-R003`/below): `AI-029`'s own
resolution/unresolvable-identity behavior IS confirmed satisfied by current Rust; `AI-030`'s own
registration surface is only PARTIALLY satisfied (replacement works; withdrawal and `models()` do
not exist in Rust at all), disclosed as open, not claimed complete.

### L10-R003 — current Rust permits an eager adapter-start failure the never-raises boundary forbids

**Re-review finding:** confirmed by direct source read. `minion-agent-rust/crates/minion-agent/src/
llm/adapter.rs::LlmAdapter::start(&self, request) -> Result<RawAssistantStream, AdapterStartError>`
grants a synchronous, typed failure channel usable even after a model has resolved and the
adapter's own code has run. `service.rs::LlmService::stream` folds this into the SAME eager
`LlmStartError` enum as the (correctly eager) unknown-model case: `Err(LlmStartError::
AdapterStart(_))`. The permanent test `adapter_start_failure_remains_eager_and_typed`
(`tests/llm_adapter.rs`) constructs exactly the case Pi's own contract forbids -- an adapter
reporting "invalid provider configuration," an ordinary EXPECTED failure, not a programming bug --
and asserts it surfaces eagerly. `exhausted_scripted_adapter_fails_before_stream_creation` shows
Rust's own reference/scripted adapter diverges from Python's already-certified `MockAdapter` the
identical way: an exhausted script is an in-band `StopReason.ERROR` response in Python
(`MockAdapter._take()`) but an eager `AdapterStart` error in Rust.

**Classification:** `PI_PARITY_DEFECT`, current Rust production, genuinely OPEN -- not something
this shared/Python pass fixes (Rust ownership boundary; the review's own required remediation
explicitly scopes this to "a later implementation pass").

**Remediation (this pass):** `AI-028`'s own `rust:` pointer corrected from "already implemented, no
new requirement" (false) to an explicit `PENDING` marker naming the exact defect
(`LlmAdapter::start`/`AdapterStartError`, `ScriptedAdapter`'s own matching divergence) and stating
remediation is a future Rust implementation pass's own responsibility. `spec/llm.md` corrected to
state the current-Rust gap explicitly rather than silently presenting Rust as compliant.

### L10-R004 — cited canonical evidence never exercised the newly normative rules

**Re-review finding:** confirmed -- `eager-invalid-model-fails-before-stream`/`public-stream-fuses-
after-first-terminal`/`represented-provider-error-rides-stream` all exercise stream TERMINAL
content or the (already-certified) unknown-model case; none construct more than one registered
adapter, exercise replacement/withdrawal, exercise `models()`, or distinguish an adapter-DETECTED
failure from a mid-network one.

**Remediation:** a new canonical family, discriminated by a top-level `llm_service` key
(`conformance/schema/llm-service-scenario.schema.json`, following the SAME "extra schema for
`conformance/agent/`'s own directory, not a new top-level canonical family" convention
`tool-registry-scenario.schema.json`/`agent-inbox-scenario.schema.json` already established) --
exercises the real `LlmService`/`Adapter`/`MockAdapter` seam directly, with no Agent loop in the
way. Four new scenarios:

- `llm-service-registration-and-replacement.yaml` -- same-identity replacement, different-identity
  independence, and the eager unresolvable-identity case, all as direct `resolve` queries (`AI-029`/
  `AI-030`'s own required discriminating dimension).
- `llm-service-withdrawal-does-not-remove-a-later-replacement.yaml` -- a stale withdrawal (an
  earlier registrant's own handle, called after a later registrant has already replaced the same
  key) is a safe no-op; an ordinary withdrawal (the current owner's own handle) does remove its own
  entry (`AI-030`).
- `llm-service-introspection-reflects-current-registrations.yaml` -- `models()` tracks
  registration/withdrawal exactly, with one entry per model name a multi-model adapter declares
  (`AI-030`).
- `llm-service-adapter-detected-failure-settles-in-band.yaml` -- an adapter that detects an expected
  failure at stream-creation time settles IN the returned stream (`settled: error`), never raises,
  distinct from the SEPARATE, legitimately-eager unresolvable-identity case (`AI-028`/`L10-R003`'s
  own required discriminating dimension, direct at this seam rather than only through the Agent
  loop).

A new `tests/conformance/llm_service_runner.py` drives the real seam (register through the real
`register()` effect, withdraw through the real handle it returns, `stream()` drained to its own
terminal, `models()`/resolution observed through the public API only -- ownership of a `resolve`
query is determined via `MockAdapter.requests`, its own sanctioned testability instrumentation
already established under `LLM-F009`, never a private `LlmService` attribute); a new
`test_llm_service_conformance.py` parametrizes over every `llm_service`-keyed scenario, matching the
existing `tool_registry`/`agent_inbox` runner pattern exactly. `test_schema_validation.py` and
`test_agent_conformance.py` both updated to recognize and correctly route/exclude the new
discriminator key, the same way they already do for `tool_registry`/`agent_inbox`/`transform`.

All four new scenarios were run directly against the real Python seam and PASS (Rust remains
unmodified by this pass; the `llm-service-adapter-detected-failure-settles-in-band` scenario is
EXPECTED to currently fail if run against Rust's own `xtask conformance verify`, since it exercises
exactly the `L10-R003` defect that pass does not fix -- this is disclosed here, not silently
claimed passing for Rust).

## Regression verification for previously-closed findings

`LLM-011`, `LLM-012`, `LLM-018`, `LLM-019`, `LLM-F006`, `LLM-F007`, `LLM-F009`, `LLM-F010`
(Layer 02): unaffected -- no existing Python source file was modified; the diff is confined to two
new test/runner files, four new canonical scenarios, one new schema, two small additions to
existing schema-validation/agent-conformance test files (a new discriminator branch each, mirroring
existing ones exactly), and the manifest/spec text corrected in place. `AI-011`/`AI-012`/`AI-027`
(the never-raises contract, `Context`, and the Layer-09 signal addition): unaffected, not
referenced by this pass's own corrections.

## Quality gates (fresh, this pass)

```text
pytest (full suite):                 1140 passed, 19 xfailed (pre-existing, unrelated), 0 failed
coverage (certified src packages):   100.00%, unchanged (no source file under src/ touched)
ruff check:                          clean (whole tree)
ruff format --check:                 clean on every file this pass touched; the same pre-existing,
                                      unrelated 7-file drift noted in every earlier layer's own
                                      passes remains untouched and out of this pass's ownership
mypy (configured scope, src only):   clean, 0 errors, 58 source files
conformance/ (full):                 307 passed, 19 xfailed (up from 298 -- 4 new llm_service
                                      scenarios, 5 new schema-validation checks)
manifest parse + unique-ID audit:    82 / 82 unique (79 PASS-9-era + AI-028/AI-029 from PASS 1 +
                                      new AI-030 this pass)
```

## Active findings (after this pass)

```text
PI_PARITY_DEFECT               L10-R003 -- OPEN, current Rust production only (LlmAdapter::start/
                                AdapterStartError permits an eager failure the never-raises
                                boundary forbids); disclosed, not silently claimed satisfied;
                                remediation is a future Rust implementation pass's own decision
CONTRACT_ASSURANCE_DEFECT      none -- L10-R002/R004 closed this pass
PI_BEHAVIOR_UNCERTAIN          none
unapproved intentional divergence   none
disclosed Minion architectural mapping   AI-029's own eager full-identity-lookup simplification of
                                Pi's two-level Provider/apiFor resolution (unchanged from PASS 1,
                                now correctly isolated to its own coherent row)
disclosed Minion-specific constraint   AI-030 (registration/withdrawal/introspection, no Pi
                                analogue, disposition: intentional divergence); ModelId.api's own
                                Python-only "mock" default (LLM-F006, unchanged, now explicitly
                                marked Python-specific rather than universalized in spec/llm.md)
Rust cross-language dependency      PARTIAL -- AI-029's own resolution/unresolvable-identity
                                behavior confirmed satisfied by direct source read; AI-028's own
                                never-raises boundary for adapter-detected failures (L10-R003) and
                                AI-030's own withdrawal/introspection surface are OPEN, disclosed
                                gaps for a future Rust implementation pass
Layer 11                       NOT STARTED
```

## Verdict

```text
Python Layer 10     CERTIFIED (self-certified; pending independent Rust contract review)
Rust Layer 10          NOT_IMPLEMENTED for L10-R003/AI-030's own open gaps; PARTIALLY_IMPLEMENTED
                          for AI-028's stream/AI-029's resolution behavior, per direct source
                          confirmation this pass
shared Layer-10 contract   READY FOR TARGETED RUST CONTRACT RE-REVIEW of L10-R001/R002/R003/R004
                             together; the corrected AI-028/AI-029/AI-030 rows and spec/llm.md
                             section, plus the new llm-service canonical evidence
Layer 10 cross-language     NOT CLOSED
Layer 11                     NOT STARTED
```

## Workflow-process retrospective note (this pass)

A prior pass's own confident "already implemented / no new requirement" claim about the OTHER
language needs the SAME source-verification discipline as any other Pi-parity claim, not a lower
bar because it is a cross-language status note rather than a semantic rule: PASS 1 asserted current
Rust already satisfied the never-raises boundary and the full registration surface without reading
`minion-agent-rust/**` at all (a reasonable ownership-boundary choice for NOT modifying Rust, but
not for asserting its current behavior). The independent review caught a genuine, current defect
(`L10-R003`) and a materially inaccurate completeness claim (`L10-R002`) this pass could have
caught itself by reading the three Rust files it eventually did read here, before ever claiming
their state. This is the SAME lesson `assurance/process-history.md`'s own Layer 09 entry already
recorded for a DIFFERENT direction (a convergence checkpoint's own "can the other language
implement this" question needing to ask whether the underlying extensibility point exists there at
all) -- here the miss was narrower and more basic: do not describe the other language's current
behavior without having read it, even when the point of the pass is explicitly to avoid modifying
that language.

## Next action

Push this pass's commits to the existing `layer/10-python-shared` branches (both repos); update PR
#20/#45 bodies with the PASS-2 remediation summary and new head SHAs. Update coordination issue #19
(`minion-agent`): `STATUS: RUST_CONTRACT_REVIEW`, new exact `CODE PR`/`DOCS PR` SHAs, append the
PASS-1 rejection reference (`minion-agent-docs#46` @ `d43559dfbc1770bb8508fcb2f27a88c0f5a4530c`) to
`PRIOR REVIEW EVIDENCE`, `NEXT_OWNER: Codex`, `NEXT_ACTION: complete a targeted independent Rust
contract review of this PASS-2 candidate against L10-R001/L10-R002/L10-R003/L10-R004 together --
confirm the corrected AI-028/AI-029/AI-030 dispositions and Rust-status disclosures are now
accurate, and confirm the new llm-service canonical scenarios genuinely discriminate what they
claim to (including that the adapter-detected-failure scenario correctly reproduces L10-R003
against current Rust, not merely against Python). L10-R003/AI-030's own open Rust gaps remain
explicitly NOT fixed by this pass and are not blocking further shared/Python work; Layer 11 remains
not started`. Then stop. Do not merge any candidate or review-evidence PR. Do not implement Rust.
Do not start Layer 11.

# PASS 3 — implement the agreed §11.8 convergence surface (L10-R001/R002/R004, C10-C005)

## Convergence reference

The PASS-2 candidate (code PR #20 @ `bad0f74552fbb73c71f15553ba321fc1d8609a10`, docs PR #45 @
`f6375ebbe12a5a76099b86966fec3e57d3b105ca`) was re-reviewed and **REJECTED** a second time
(`minion-agent-docs#47` @ `2df53c68aa374b291846e9f64216534a054b4c0a`): `L10-R001`/`L10-R002`
partially resolved but blocking (the corrected `AI-028`/`AI-029` still bundled `stream`/`streamSimple`
under one disposition), `L10-R004` still open (the runner's own value-equality `resolve` search and
the schema's missing `reject_message` grammar constraint). `L10-R002` and `L10-R004` met the
repeated-finding threshold, opening the mandatory `agent-workflow.md` §11.8 Contract Convergence
Protocol (issue #19: `STATUS: CONTRACT_CONVERGENCE`).

Three convergence-checkpoint revisions followed (`minion-agent-docs#45` @
`405798a93dfe058f212072256b354985091c07af`, `6254988ea5e98610b381ddb3a40530e16b75847b`,
`f6375ebbe12a5a76099b86966fec3e57d3b105ca`), each independently challenged (`minion-agent-docs#47`
@ `60ef1cd5410c81bd33b526859cca5d49dc096584`, `1ced90250ca7c0df7169780ae95a4dcf6d410b70`) and each
closing the prior challenge's own findings (`C10-C001`..`C10-C004` in revision 2; `C10-C005` -- a genuine PASS-2 Python production
defect in `LlmService.register`'s own withdrawal-ownership check, not merely a documentary gap --
newly raised against revision 2 and closed in revision 3). The convergence was independently
**AGREED FOR IMPLEMENTATION** (`minion-agent-docs#47` @ `05e03a7faefb9bbc45eeff20ed1996267414d16d`),
with one binding implementation clarification: the checkpoint's own "Rust implementability" section
had suggested a consuming, move-only Rust handle type as one natural fit for `C10-C005`'s ownership
rule; the reviewer ruled this non-conforming, since it would make the ALREADY-agreed idempotent-
repeat-withdrawal observation impossible to express, and required the misleading example removed
from current wording. This pass implements the full agreed surface
(`assurance/layers/10-provider-abstraction-contract-checkpoint-r002-r004-convergence.md`, revision
3, corrected per that clarification) and closes `L10-R001`, `L10-R002`, `L10-R004`, and `C10-C005`
together, per the agreement's own recorded `NEXT_ACTION`.

## Findings closed this pass

### L10-R001 / L10-R002 (repeated) — `AI-028` still bundled `stream` and `streamSimple` under one disposition

**Remediation:** `AI-028` narrowed to cover ONLY `stream` (`disposition: adopted`, unchanged for
that half). New `AI-031` created for `streamSimple` (`disposition: deferred parity`), carrying the
same wire-protocol-specific characterization PASS 2 already established for it, now under its own
correct disposition rather than bundled with a satisfied operation, plus an explicit closure
criterion (`C10-C001`, binding on whichever future pass closes it): the obligation Layer 11 owes is
an EXTERNALLY INVOCABLE operation matching Pi's own `streamSimple(model, context, options) ->
AssistantMessageEventStream` shape, not merely internal per-provider translation plumbing with no
caller-facing entry point. `spec/llm.md` mirrors both corrections, plus a new `streamSimple`
paragraph.

`AI-029`'s own `disposition:` corrected from `adopted` to `intentional divergence` (`C10-C001`): the
row's own text already characterized Minion's single eager `UnknownModelError` check as "an
intentional, disclosed Minion architectural SIMPLIFICATION... not a literal mechanical port" --
that is a description of divergence, not adoption; master design's own eager/lazy boundary
authorizes the collapse, but authorization is a separate claim from "matches Pi's own observable
behavior." `spec/llm.md` corrected identically.

`AI-030`'s own `rule:` gains the documentary corrections the convergence agreement requires: a note
that the canonical scenario grammar addresses registration by HANDLE id, not fixture id, and an
explicit statement of the token-based, per-registration-call ownership mechanism (see `C10-C005`
below) plus the idempotent-repeated-withdrawal guarantee, stated as a binding, non-negotiable
observable rule rather than left implicit. `spec/llm.md` mirrors this.

### L10-R004 (repeated) — schema/runner defects the prior pass's own evidence never closed

**Remediation, schema (`C10-C002`):** `conformance/schema/llm-service-scenario.schema.json`'s
`adapterEntry` now carries an `if`/`then`/`else` constraint tying `reject_message` to `behavior`
both directions (required when `reject`, forbidden when `ok`) -- PASS-2's schema accepted both
malformed shapes silently. `step.register` changed from a bare fixture-id string to a `{adapter,
as}` object (both required): `adapter` names the fixture being registered, `as` introduces the
handle id its own withdrawal is later addressed by. `withdraw` now names a handle id, never a
fixture id.

**Remediation, runner grammar and validation (`C10-C002`/`C10-C003`):**
`tests/conformance/llm_service_runner.py` rewritten for the new grammar (`register`/`withdraw`
steps address handles via a `handles: dict[str, Callable[[], None]]` map, replacing PASS-2's
fixture-id-keyed `withdrawals` map that could not express two independent handles for the same
fixture). A new `_validate_references` pre-flight pass (mirroring
`tool_registry_runner.py::_validate_references`'s own established boundary) rejects, before any
`LlmService`/`Adapter` object is constructed: a duplicate `adapters[].id`; a `register.adapter`
naming an undeclared fixture; a `register.as` handle id reused by an earlier `register` step; a
`withdraw` naming an undeclared handle; a duplicate observation id across the single
`queries[].id`/`steps[].stream.as` namespace; an `expect` key naming no declared observation id.
Deliberately NOT rejected: withdrawing an already-withdrawn handle (idempotent, `AI-030`) and a
declared observation id `expect` never names (a legitimate setup-only action). A new
`tests/conformance/test_llm_service_runner_validation.py` exercises these cases directly against
the runner module, independent of the canonical scenario schema: seven tests confirm each malformed
shape is rejected, and two confirm the two deliberately-permitted cases above proceed normally (the
file's remaining three tests exercise the `_owner_from_growth` guard directly -- see `C10-C004`
below).

**Remediation, ownership-detection defect (`C10-C004`):** the `resolve` query's ownership search
was a value-equality search over `MockAdapter.requests` -- unsound, since every `Request` this
runner builds varies only in `model`, so two adapters called through different identities produce
value-equal requests and the search could silently pick the wrong, registration-order-first
adapter. This is the review's own exact reproduction (register A; stream through A; register B
replacing A for the same identity; resolve -- reported `A`, not the real current owner `B`). Fixed
by snapshotting each candidate's own request-log length BEFORE the call (before invoking
`LlmService.stream()`, not merely before draining the returned stream -- `MockAdapter.stream()`
appends synchronously at call time, and `LlmService.stream()` invokes it eagerly) and requiring
EXACTLY one candidate's count to have grown by one afterward, raising `AssertionError` on zero or
multiple matches rather than normalizing via `next()`'s own first-match behavior. Factored into a
standalone `_owner_from_growth` helper, directly unit-tested against synthetically-constructed
zero-growth and multiple-growth cases (a naively-shared mock object under two fixture ids), not
only through the full scenario-document runner.

Two new canonical scenarios: `llm-service-resolve-ownership-survives-replacement.yaml` (the
review's own exact reproduction under the new handle grammar, including a setup-only `stream`
step never named in `expect`, proving that permission explicitly) and
`llm-service-same-fixture-two-handles.yaml` (see `C10-C005` below). The four PASS-2 scenarios
mechanically updated to the new `register`/`withdraw` grammar. `test_schema_validation.py` gains
four new parametrized checks (two negative, two positive) pinning the `reject_message`/`behavior`
constraint directly against the schema, independent of any scenario file.

### C10-C005 — per-registration-call ownership: a genuine PASS-2 production defect, not a new grammar-only capability

**Finding (raised against convergence revision 2, closed in revision 3):** revision 2 mischaracterized
the same-fixture/two-handle witness as "a new capability the PASS-2 grammar could not even express...
with no PASS-2 baseline to revert against." The challenge review corrected this: the witness
exercises `AI-030`'s already-normative rule that a withdrawal handle owns exactly the entries its own
`register()` call added, and PASS-2's actual `LlmService.register`/`withdraw` -- `self._adapters.get
(model_id) is adapter` -- checks adapter-OBJECT identity, not registration-CALL identity, so it
cannot distinguish two calls that happen to register the identical adapter object. The review's own
direct reproduction: `register(a)` twice, `models()` shows one entry, withdrawing the FIRST handle
incorrectly dropped it to zero instead of leaving the second registration live.

**Remediation:** `minion-agent-python/src/minion_agent/llm/service.py::LlmService.register`
rewritten to store a fresh, opaque per-call `token = object()` alongside the adapter
(`self._adapters[model_id] = (adapter, token)`); the returned withdrawal closure checks
`entry[1] is token`, not the adapter object, before deleting an entry. `stream()` unpacks the tuple
and is otherwise unchanged. This is the ONLY production source file this convergence touches.

Two new direct Python unit witnesses (`tests/llm/test_service.py`):
`test_registering_the_same_adapter_object_twice_gives_each_call_its_own_ownership` (the review's own
exact reproduction at the `LlmService` API directly -- register the same object twice, withdraw the
first, confirm the second registration's own entry survives, withdraw the second, confirm it is
correctly removed) and the pre-existing `test_withdrawing_twice_is_harmless` (already covers
double-withdrawal idempotency; re-confirmed, not new). New canonical DSL witness:
`llm-service-same-fixture-two-handles.yaml`, the same shape expressed at the scenario layer under
the new handle grammar.

## Binding implementation clarification applied

`assurance/layers/10-provider-abstraction-contract-checkpoint-r002-r004-convergence.md`'s own "Rust
implementability" section is corrected in place: the "an owned, move-only handle type Rust's own
borrow checker would enforce single-use on" suggestion is withdrawn and replaced with an explicit
statement that any future Rust representation must keep repeat withdrawal a safe no-op (e.g. a
handle exposing `withdraw(&self)` rather than a consuming `withdraw(self)`), matching the SAME
observable rule this pass's own Python fix establishes. No other checkpoint content changed; this
is the exact, narrow correction the agreement's own binding clarification required.

## Revert-and-confirm (genuine RED against the exact PASS-2 candidate)

Each production/tooling fix was verified to genuinely discriminate before being trusted, per this
project's own established discipline -- backed up, reverted to the exact PASS-2 state, confirmed
RED, restored, confirmed GREEN:

- **`service.py` (`C10-C005`):** reverted to PASS-2's `is adapter`-based check ->
  `test_registering_the_same_adapter_object_twice_gives_each_call_its_own_ownership` FAILED exactly
  as the review's own reproduction predicted (`models()` incorrectly showed `frozenset()` after
  only the first handle's withdrawal). Restored -> all 10 `test_service.py` tests pass.
- **`llm_service_runner.py`'s own `resolve` ownership detection (`C10-C004`):** the fixed
  count-delta logic temporarily replaced with PASS-2's own value-equality search (grammar/schema
  left at their current, fixed state, since PASS-2's grammar cannot express this scenario at all)
  -> `llm-service-resolve-ownership-survives-replacement.yaml` FAILED, reporting the stale owner
  `adapter-a` instead of the real current owner `adapter-b`. Restored -> all 6 llm-service
  scenarios pass again.
- **`llm-service-scenario.schema.json`'s own `adapterEntry` constraint (`C10-C002`):** validated
  the two malformed shapes (`behavior: reject` without `reject_message`; `behavior: ok` with
  `reject_message` present) directly against the EXACT PASS-2 schema file (`git show HEAD:...`,
  the committed PASS-2 candidate) -- both passed validation with zero errors under PASS-2, and are
  now correctly rejected.

The `_validate_references` negative witnesses and the `_owner_from_growth` synthetic zero-/
multiple-growth witnesses have no PASS-2 baseline to revert against in the classical sense (PASS-2
had no such validation or guard at all -- the check simply did not exist), so their RED evidence is
the check's own absence in PASS-2, not a revert-and-confirm cycle; each is confirmed to pass
against the current, fixed code.

## Regression verification for previously-closed findings

`LLM-011`, `LLM-012`, `LLM-018`, `LLM-019`, `LLM-F006`, `LLM-F007`, `LLM-F009`, `LLM-F010`
(Layer 02), `AI-011`/`AI-012`/`AI-027` (never-raises contract, `Context`, Layer-09 signal): all
unaffected. `service.py`'s own change is additive at the exact boundary `AI-030` already owned (the
withdrawal closure's own internal ownership check); every existing caller of `register`/`stream`/
`models()` is unaffected, confirmed by the full existing `test_service.py` suite passing unchanged
plus the one new test. No other Python source file under `src/` was touched.

## Quality gates (fresh, this pass)

```text
pytest (full suite):                 1161 passed, 19 xfailed (pre-existing, unrelated), 0 failed
coverage (certified src packages):   100.00%, unchanged
ruff check:                          clean (whole tree)
ruff format --check:                 clean on every file this pass touched; the same pre-existing,
                                      unrelated 7-file drift noted in every earlier layer's own
                                      passes remains untouched and out of this pass's ownership
mypy (configured scope, src only):   clean, 0 errors, 58 source files
conformance/ (full):                 327 passed, 19 xfailed (up from 307 -- new llm_service
                                      scenarios, a new runner-validation file, and new
                                      schema-validation checks account for the increase)
manifest parse + unique-ID audit:    83 / 83 unique (82 PASS-2-era + new AI-031)
```

## Active findings (after this pass)

```text
PI_PARITY_DEFECT               L10-R003 -- OPEN, current Rust production only, unchanged by this
                                pass (out of scope per the agreement's own explicit instruction)
CONTRACT_ASSURANCE_DEFECT      none -- L10-R001/R002/R004 and C10-C005 closed this pass
PI_BEHAVIOR_UNCERTAIN          none
unapproved intentional divergence   none
disclosed Minion architectural mapping   AI-029's own eager full-identity-lookup simplification,
                                now correctly disposed as intentional divergence rather than adopted
disclosed Minion-specific constraint   AI-030 (registration/withdrawal/introspection, token-based
                                per-call ownership, idempotent repeated withdrawal, no Pi analogue);
                                AI-031 (streamSimple, deferred parity, explicit closure criterion);
                                ModelId.api's own Python-only "mock" default (LLM-F006, unchanged)
Rust cross-language dependency      PARTIAL, unchanged by this pass -- AI-029's own resolution
                                behavior confirmed satisfied; AI-028's never-raises boundary
                                (L10-R003) and AI-030's withdrawal/introspection surface remain OPEN,
                                disclosed gaps; C10-C005's own future Rust obligation recorded
                                (certified Rust `LlmService::register` has no withdrawal mechanism
                                at all yet, so cannot currently exhibit or fix this exact defect)
Layer 11                       NOT STARTED
```

## Verdict

```text
Python Layer 10     CERTIFIED (self-certified; pending independent Rust §11.8.7 targeted
                       finding-closure review)
Rust Layer 10          NOT_IMPLEMENTED for L10-R003/AI-030's own open gaps; PARTIALLY_IMPLEMENTED
                          for AI-028's stream/AI-029's resolution behavior, unchanged by this pass
shared Layer-10 contract   READY FOR TARGETED §11.8.7 FINDING-CLOSURE REVIEW of
                             L10-R001/R002/R004/C10-C005 together, against this exact candidate
Layer 10 cross-language     NOT CLOSED
Layer 11                     NOT STARTED
```

## Next action

Push this pass's commits to the existing `layer/10-python-shared` branches (both repos); verify
both new commits are remote-reachable; update PR #20/#45 bodies with this implementation summary
and the new head SHAs. Update coordination issue #19 (`minion-agent`): `STATUS:
RUST_CONTRACT_REVIEW`, new exact `CODE PR`/`DOCS PR` SHAs, append the independent-agreement
reference (`minion-agent-docs#47` @ `05e03a7faefb9bbc45eeff20ed1996267414d16d`) to `PRIOR REVIEW
EVIDENCE`, `NEXT_OWNER: Codex`, `NEXT_ACTION: complete a targeted §11.8.7 finding-closure review of
this candidate against L10-R001/L10-R002/L10-R004/C10-C005 together -- confirm the corrected
AI-028/AI-029/AI-030/AI-031 dispositions, the handle-based registration grammar and its reference
validation, the count-delta exactly-one ownership fix, and the token-based per-registration-call
Python production repair all genuinely close their respective findings against this exact
candidate, not merely against the agreed design. L10-R003 remains an explicit, disclosed, OPEN
Rust-only defect, out of scope per the agreement; Layer 11 remains not started`. Then stop. Do not
merge any candidate or review-evidence PR. Do not implement Rust. Do not start Layer 11.
