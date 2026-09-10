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
                                per-call ownership, idempotent repeated withdrawal; Pi comparison
                                corrected under L10-R005/PASS 4 below, see that pass's own Active
                                findings table for the current-state summary); AI-031 (streamSimple,
                                deferred parity, explicit closure criterion); ModelId.api's own
                                Python-only "mock" default (LLM-F006, unchanged)
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

# PASS 4 — implement the agreed §11.8 convergence surface (L10-R005/R006/R007)

## Convergence reference

The final complete independent Rust contract review of the PASS-3 candidate (code PR #20 @
`4d63349d85d517359545b94ce0937548d3fb7314`, docs PR #45 @ `57edf9fd08e9b7411d32177f5991756182dd6a7a`,
`minion-agent-docs#47` @ `e8a2d395dc4697eb65b42958eb043c9c7eede185`) confirmed `L10-R001`/`L10-R002`/
`L10-R004`/`C10-C005` CLOSED but **REJECTED** the candidate on three new findings, and Layer 10 had
by then accumulated three rejected contract reviews -- `agent-workflow.md` §11.8's own automatic
trigger ("layer accumulates three rejected contract reviews") applied regardless of finding
repetition (issue #19: `STATUS: CONTRACT_CONVERGENCE`).

- **`L10-R005`**: `AI-030`'s own "Pi has no adapter-registration concept at all" premise was false.
- **`L10-R006`**: `fetchDeferred`/`cancelDeferred` had no disposition anywhere.
- **`L10-R007`**: the canonical runner's own `_build_adapter()` hard-coded exactly 8 scripted
  responses per fixture, silently capping what a schema-valid scenario could express.

A first characterization checkpoint (`10-provider-abstraction-contract-checkpoint-
r005-r007-convergence.md`, docs PR #45 @ `d445901cc8441e6ab66acfd929df4e93e6fc6763`) independently
re-audited pinned Pi (`ref-repos/pi` at the pinned SHA) and proposed corrections. The repository
owner separately APPROVED (`§11.7`) continuing Minion's registry as an intentional divergence,
scoped to `AI-030`'s own granularity, recorded in the checkpoint (docs PR #45 @
`43216a98d1c911f808a1f1557e73ed3d3239c0bb`). An independent challenge (`minion-agent-docs#47` @
`273951ad2b4a1bd6aa984b502a370b79935a0931`) accepted `L10-R007` outright but found two gaps in the
Pi-source mapping (`C10-D001`: the checkpoint omitted `compat.ts::registerFauxProvider`'s own
per-call `unregister()` precedent and mischaracterized stale-removal as "not applicable"; `C10-D002`:
the proposed deferred-operation row conflated several distinct fetch/cancel failure boundaries).
Revision 2 (docs PR #45 @ `004c92b268a01fc50ad05af90708f5ad539a4242`) remediated both, each
independently re-verified against `ref-repos/pi` before being accepted. The revision was
**AGREED FOR IMPLEMENTATION** (`minion-agent-docs#47` @ `4a4012b14541dabc98d3ccfc0faedd363099436e`),
with one binding source-accuracy clarification: `registerFauxProvider`'s own pseudo-random source
tag is NOT collision-checked, so normative wording must describe it as "freshly generated per-call,
normally distinct," never as mathematically guaranteed unique. This pass implements the full agreed
surface and closes `L10-R005`, `L10-R006`, and `L10-R007` together, per the agreement's own recorded
`NEXT_ACTION`.

## Findings closed this pass

### L10-R005 — `AI-030`'s false "no Pi analogue" premise

**Remediation:** `AI-030`'s `pi:` and `rule:` fields rewritten to compare Minion's registry against
THREE real, currently-live Pi surfaces, each independently re-read against `ref-repos/pi` this pass:
(1) `models.ts::MutableModels.setProvider/deleteProvider/clearProviders` -- keyed by `provider.id`,
whole-provider replacement; (2) `compat.ts`'s generic `registerApiProvider`/`unregisterApiProviders`
-- keyed by `provider.api`, bulk tag-scoped removal, an explicitly TEMPORARY compatibility surface
("deleted with the coding-agent ModelManager migration"); (3) `compat.ts::registerFauxProvider`,
built on (2) -- generates a fresh, pseudo-random `sourceId` per call (per the binding clarification,
described as "freshly generated per-call, normally distinct," NOT guaranteed unique) and returns a
`FauxProviderRegistration` (`providers/faux.ts:132-141`) whose own `unregister()` closes over that
call's tag, a live per-registration-call unregistration precedent on Pi's OWN faux/mock surface
specifically. The stale-removal matrix now states the actual tag-identity-dependent outcomes
(differing tags: safe; shared tags: deliberate bulk/current-entry removal) instead of the prior
"not applicable" claim. `LlmService.models()`'s own "no Pi analogue" claim corrected similarly --
Pi's own introspection (`getProviders`/`getModels`, `getApiProvider`/`getApiProviders`) is real and
directly comparable, just at each surface's own coarser key.

Minion's registry matches none of the three (finer-grained keying, per-key rather than whole-
provider/api replacement, generic rather than faux-specific per-call ownership) -- this conclusion
is unchanged from PASS 3's own reasoning, now grounded in an accurate, complete comparison rather
than a false "no analogue at all" premise. `disposition:` unchanged (`intentional divergence`).

**Governance (`§11.7`, recorded):** the repository owner explicitly approved continuing Minion's
registry semantics as an intentional divergence, scoped to `AI-030`'s own registration/replacement/
withdrawal/introspection granularity, against exactly the three-surface comparison above. Full
decision text is recorded in the convergence checkpoint's own `GOVERNANCE DECISION (§11.7) --
RECORDED` section and summarized in `AI-030`'s own `rule:` field. `spec/llm.md`'s own `AI-030`
section mirrors all of the above, plus the same governance citation.

No Python source file changed for this finding -- purely documentary, per the checkpoint's own
`IMPLEMENTATION CONSTRAINTS` (no redesign toward any of the three Pi surfaces was requested or
proposed).

### L10-R006 — `fetchDeferred`/`cancelDeferred` had no disposition

**Remediation:** new manifest row `AI-032` (`disposition: deferred parity`), mirroring `AI-031`'s
own `streamSimple` shape but stating FOUR distinct observable layers pinned Pi keeps separate
(each independently re-verified against `ref-repos/pi` this pass, not merely restated from the
checkpoint's own prose):

1. Low-level, per-API-module (`types.ts::ProviderStreams.fetchDeferred?`/`cancelDeferred?`):
   `fetchDeferred` returns a stream (never-raises, matching `stream`/`AI-012`); `cancelDeferred`
   returns `Promise<void>`.
2. High-level, caller-facing (`models.ts::ModelsImpl.fetchDeferred`/`cancelDeferred`, read directly
   at `models.ts:706-732` this pass): NOT symmetric -- `fetchDeferred` wraps provider/capability
   lookup, auth, and delegation entirely inside `lazyStream(...).result()`, so a missing provider or
   capability settles as a REPRESENTED, in-band `AssistantMessage` error; `cancelDeferred` performs
   the SAME lookup EAGERLY outside any `lazyStream` wrapper (confirmed via `ModelsImpl.
   requireProvider`'s own plain synchronous `throw`, `models.ts:628-634`), so the identical failure
   THROWS as a rejected promise instead.
3. Provider-level, mixed-API capability selection (`models.ts::createProvider`, `:835-859`, read
   directly this pass): a per-model capability mismatch in a mixed-API provider inherits the
   IDENTICAL asymmetry as (2) -- fetch settles in-band, cancel throws eagerly.
4. Reference (faux/mock) implementation's own concrete unknown/cancelled-handle behavior
   (`providers/faux.ts:567-642`, already characterized in the checkpoint's revision 1): for a
   SUPPORTED capability specifically, fetch's own unknown/cancelled-handle failure settles in-band;
   cancel's own unknown handle is a silent no-op -- distinct from (2)/(3)'s missing-provider/
   capability case, not the same rule restated.

Closure criterion: a future Layer-11 implementation must preserve all four distinctions -- it must
not make `cancel_deferred` globally never-raising, and must not make `fetch_deferred` throw eagerly
on a missing/unsupported capability. Executable provider witnesses remain deferred to Layer 11
(Layer 10 has no concrete wire-protocol implementation to test against). `spec/llm.md` gains a new
matching `fetchDeferred`/`cancelDeferred` section. No Python source file changed for this finding
either -- `AI-009`'s own already-certified `DeferredHandle` vocabulary is unaffected, and no
speculative Layer-11 plumbing was added.

### L10-R007 — canonical runner's own undocumented eight-call cap

**Remediation:** `tests/conformance/llm_service_runner.py::_build_adapter` no longer hard-codes
`script = [response] * 8`. A new `_max_possible_calls(spec_doc)` helper counts every
`steps[].stream` action plus every `queries[].resolve` query in the scenario document (each is at
most one call to SOME one adapter) and returns that total; `_build_adapter` now accepts this count
as `script_length` and provisions exactly that many identical scripted responses per fixture -- a
safe, non-predictive upper bound (it does not guess which adapter the service will actually
resolve to; every fixture gets the SAME generous bound). New canonical scenario
`llm-service-more-than-eight-calls-settle-ok.yaml`: one `behavior: ok` adapter, one registration,
nine `stream` calls against the same identity, all expecting `ok` -- the review's own exact
reproduction.

## Revert-and-confirm (genuine RED against the exact PASS-3 candidate)

`L10-R007`'s fix was verified to genuinely discriminate before being trusted: the exact PASS-3
candidate's own `llm_service_runner.py` (`git show 4d63349:...`, confirmed as a clean, isolated
diff against the fixed version -- only the `_build_adapter`/`_max_possible_calls`/call-site change)
was temporarily restored; the new nine-call scenario FAILED exactly as the review's own
reproduction predicted (`call_9`: `error` instead of `ok`, `"mock script exhausted after 8
response(s); the scenario asked for one more"`). The fix was restored; all 7 llm-service scenarios
and all 12 runner-validation tests pass again.

`L10-R005`/`L10-R006` are purely documentary/manifest corrections with no Python behavior change,
so there is no code to revert-and-confirm against -- their own acceptance evidence is the corrected
prose itself, independently checkable against the cited Pi source ranges (all re-read directly
against `ref-repos/pi` this pass, not merely copied from the checkpoint's own text), plus the
recorded `§11.7` governance decision for `L10-R005` specifically.

## Regression verification for previously-closed findings

`L10-R001`/`L10-R002`/`L10-R004`/`C10-C005` (PASS 3): unaffected -- `service.py` was not touched
this pass; the four PASS-3-era `llm_service` scenarios and the two `C10-C004`/`C10-C005` scenarios
all still pass unchanged. `LLM-011`/`LLM-012`/`LLM-018`/`LLM-019`/`LLM-F006`/`LLM-F007`/`LLM-F009`/
`LLM-F010` (Layer 02): unaffected, no source file under `src/` was touched by this pass at all --
the only production-adjacent change is test/tooling (`llm_service_runner.py`).

## Quality gates (fresh, this pass)

```text
pytest (full suite):                 1163 passed, 19 xfailed (pre-existing, unrelated), 0 failed
coverage (certified src packages):   100.00%, unchanged (no source file under src/ touched)
ruff check:                          clean (whole tree)
ruff format --check:                 clean on every file this pass touched; the same pre-existing,
                                      unrelated 7-file drift noted in every earlier layer's own
                                      passes remains untouched and out of this pass's ownership
                                      (llm_service_runner.py itself needed one auto-format pass
                                      after this pass's own edit, applied and re-verified clean)
mypy (configured scope, src only):   clean, 0 errors, 58 source files
conformance/ (full):                 329 passed, 19 xfailed (up from 327 -- one new >8-call
                                      llm_service scenario, plus its own schema-validation checks)
manifest parse + unique-ID audit:    84 / 84 unique (83 PASS-3-era + new AI-032)
```

## Active findings (after this pass)

```text
PI_PARITY_DEFECT               L10-R003 -- OPEN, current Rust production only, unchanged by this
                                pass (out of scope per the agreement's own explicit instruction)
CONTRACT_ASSURANCE_DEFECT      none -- L10-R005/R006/R007 closed this pass
PI_BEHAVIOR_UNCERTAIN          none
unapproved intentional divergence   none
disclosed Minion architectural mapping   AI-029's own eager full-identity-lookup simplification,
                                unchanged by this pass
disclosed Minion-specific constraint   AI-030 (registration/withdrawal/introspection, now compared
                                honestly against all three real Pi registration surfaces, owner-
                                approved intentional divergence, §11.7 decision recorded); AI-031
                                (streamSimple, deferred parity); AI-032 (fetchDeferred/
                                cancelDeferred, deferred parity, four-layer closure criterion, new
                                this pass); ModelId.api's own Python-only "mock" default
                                (LLM-F006, unchanged)
Rust cross-language dependency      PARTIAL, unchanged by this pass -- AI-029's own resolution
                                behavior confirmed satisfied; AI-028's never-raises boundary
                                (L10-R003) and AI-030's withdrawal/introspection surface remain OPEN,
                                disclosed gaps
Layer 11                       NOT STARTED
```

## Verdict

```text
Python Layer 10     CERTIFIED (self-certified; pending independent Rust §11.8.7 targeted
                       finding-closure review)
Rust Layer 10          NOT_IMPLEMENTED for L10-R003/AI-030's own open gaps; PARTIALLY_IMPLEMENTED
                          for AI-028's stream/AI-029's resolution behavior, unchanged by this pass
shared Layer-10 contract   READY FOR TARGETED §11.8.7 FINDING-CLOSURE REVIEW of L10-R005/R006/R007
                             together, against this exact candidate
Layer 10 cross-language     NOT CLOSED
Layer 11                     NOT STARTED
```

## Next action

Push this pass's commits to the existing `layer/10-python-shared` branches (both repos); verify
both new commits are remote-reachable; update PR #20/#45 bodies with this implementation summary
and the new head SHAs. Update coordination issue #19 (`minion-agent`): `STATUS:
RUST_CONTRACT_REVIEW`, new exact `CODE PR`/`DOCS PR` SHAs, append the independent-agreement
reference (`minion-agent-docs#47` @ `4a4012b14541dabc98d3ccfc0faedd363099436e`) to `PRIOR REVIEW
EVIDENCE`, `NEXT_OWNER: Codex`, `NEXT_ACTION: complete a targeted §11.8.7 finding-closure review of
this candidate against L10-R005/L10-R006/L10-R007 together -- confirm the corrected AI-030
three-surface comparison (including the binding non-guaranteed-uniqueness wording for
registerFauxProvider's own source tag) and the new AI-032 row's own four-layer closure criterion
genuinely close their respective findings against this exact candidate, and confirm the
>8-call canonical scenario and the runner's own non-predictive provisioning fix genuinely close
L10-R007. L10-R003 remains an explicit, disclosed, OPEN Rust-only defect, out of scope; note that
after this targeted closure, workflow §11.8.8 still requires ONE final complete review of the exact
final candidate before Rust implementation may begin; Layer 11 remains not started`. Then stop. Do
not merge any candidate or review-evidence PR. Do not implement Rust. Do not start Layer 11.

# PASS 5 — remediate the §11.8.7 targeted closure review's own narrow L10-R005 finding

## Targeted closure reference

The §11.8.7 targeted finding-closure review of the PASS-4 candidate (code PR #20 @
`1c4f2959c5ffeaed35f8a97cfbc1509ebaadbdc5`, docs PR #45 @ `cd8b690fccbd63f8b20bdb187bc1f0b6f7c61ed2`,
`minion-agent-docs#47` @ `ae599ba9660907593ac9d020bdeca1ca57d01fe2`) returned `REJECTED -- NARROW
REVISION REQUIRED`:

- **`L10-R006`**: `PROVISIONALLY CLOSED`. New `AI-032`/`spec/llm.md` state all four agreed
  observable layers; `C10-D002` satisfied.
- **`L10-R007`**: `PROVISIONALLY CLOSED`. Fresh targeted execution (`test_llm_service_conformance.py`
  + `test_llm_service_runner_validation.py`, 19 passed) confirms the non-predictive provisioning
  fix and the new >8-call scenario against real production `LlmService`/`MockAdapter`.
- **`L10-R005`**: still `OPEN`, `CONTRACT_ASSURANCE_DEFECT` (the ORIGINAL finding, not a new one).
  `pi-parity-manifest.yaml::AI-030` retained two statements readable as the disproven current
  premise even after PASS 4's own correction elsewhere in the SAME row: the row-opening "there is
  no Pi behavior to 'adopt' here at all" (a historical framing PASS 4 never updated), and
  `LlmService.models()`'s own "with no Pi analogue" claim (PASS 4 corrected this exact language in
  `spec/llm.md` but missed the parallel manifest paragraph). The review found both by reading the
  full row, not merely PASS 4's own narrative summary of it.

Independently re-verified this pass: both quoted phrases were confirmed present, verbatim, at
`pi-parity-manifest.yaml` lines 602-603 and 705-709 (pre-remediation), exactly as the review cited
them -- not accepted on the review's own prose alone.

## Finding closed this pass

### L10-R005 — residual contradictory wording in `AI-030`

**Remediation (documentary only, no production/schema/runner/governance change, matching the
review's own required scope):**

1. The row-opening historical sentence ("Split out of `AI-029` under `L10-R002`...there is no Pi
   behavior to 'adopt' here at all") rewritten to state the CURRENT, corrected rule directly:
   three real Pi registration surfaces exist (`L10-R005`, cross-referenced to the corrected
   comparison later in the same row), but Minion directly adopts NONE of them -- the conclusion
   (a Minion architectural extension is still the right disclosure) is unchanged, only the
   now-contradicted "no Pi behavior at all" framing is removed.
2. The `LlmService.models()` paragraph's own "with no Pi analogue" claim replaced with the SAME
   corrected language PASS 4 already applied to `spec/llm.md`: Pi's own `MutableModels.
   getProviders`/`getProvider`/`getModels`/`getModel` and `compat.ts`'s own `getApiProvider`/
   `getApiProviders` are real, directly-comparable introspection surfaces (not "no analogue"),
   each at its own coarser key, with richer catalog/refresh semantics this project does not need
   yet.
3. This pass's own PASS-4 `Active findings` table entry for `AI-030` corrected to stop
   reasserting "no Pi analogue" as a current-state summary; it now points to PASS 4's own later
   `Active findings` table (the one immediately following PASS 4's own implementation, which
   already correctly said "now compared honestly against all three real Pi registration
   surfaces") rather than restating the superseded phrase. PASS 3's OWN `Active findings` table
   (an earlier, historical per-pass snapshot, preserved per this project's own
   historical-artifact-preservation rule) is left untouched -- it accurately reflects the state as
   of PASS 3, before PASS 4's own correction existed, and is not the "active" summary a reader
   would mistake for current.

`spec/llm.md` needed NO change this pass -- the review's own audit confirmed the normative spec
already states the corrected comparison accurately; only the manifest (and this assurance
document's own PASS-4 summary line) had drifted from it.

## Regression verification for previously-closed findings

`L10-R006`/`L10-R007` (PASS 4, provisionally closed by the targeted review above): unaffected --
no file either finding's own evidence depends on was touched this pass. `L10-R001`/`L10-R002`/
`L10-R004`/`C10-C005` (PASS 3): unaffected, no production file touched. No Python source file under
`src/` or `tests/` was touched by this pass at all -- the diff is confined to `pi-parity-manifest.
yaml` prose and this assurance document's own PASS-4 summary line.

## Quality gates (fresh, this pass)

```text
pytest (full suite):                 1163 passed, 19 xfailed (pre-existing, unrelated), 0 failed
                                      (unchanged from PASS 4 -- no Python file touched)
coverage (certified src packages):   100.00%, unchanged
ruff check:                          clean (whole tree)
ruff format --check:                 clean; the same pre-existing, unrelated 7-file drift remains
mypy (configured scope, src only):   clean, 0 errors, 58 source files
conformance/ (full):                 329 passed, 19 xfailed, unchanged from PASS 4
manifest parse + unique-ID audit:    84 / 84 unique, unchanged from PASS 4 (documentary edit only,
                                      no row added or removed)
```

## Active findings (after this pass)

```text
PI_PARITY_DEFECT               L10-R003 -- OPEN, current Rust production only, unchanged
CONTRACT_ASSURANCE_DEFECT      none -- L10-R005 closed this pass; L10-R006/R007 already
                                provisionally closed by the targeted review
PI_BEHAVIOR_UNCERTAIN          none
unapproved intentional divergence   none
disclosed Minion architectural mapping   AI-029's own eager full-identity-lookup simplification,
                                unchanged
disclosed Minion-specific constraint   AI-030 (registration/withdrawal/introspection, compared
                                honestly against all three real Pi registration surfaces
                                throughout the ENTIRE row now, no residual contradictory wording,
                                owner-approved intentional divergence, §11.7 decision recorded);
                                AI-031 (streamSimple, deferred parity); AI-032 (fetchDeferred/
                                cancelDeferred, deferred parity, four-layer closure criterion);
                                ModelId.api's own Python-only "mock" default (LLM-F006, unchanged)
Rust cross-language dependency      PARTIAL, unchanged
Layer 11                       NOT STARTED
```

## Verdict

```text
Python Layer 10     CERTIFIED (self-certified; pending the mandatory §11.8.8 final complete review)
Rust Layer 10          NOT_IMPLEMENTED for L10-R003/AI-030's own open gaps; PARTIALLY_IMPLEMENTED
                          for AI-028's stream/AI-029's resolution behavior, unchanged
shared Layer-10 contract   L10-R005/R006/R007 all now closed at this exact candidate; READY FOR
                             THE MANDATORY §11.8.8 FINAL COMPLETE REVIEW
Layer 10 cross-language     NOT CLOSED
Layer 11                     NOT STARTED
```

## Next action

Push this pass's commits to the existing `layer/10-python-shared` branches (both repos); verify
both new commits are remote-reachable; update PR #20/#45 bodies with this remediation summary and
the new head SHAs. Update coordination issue #19 (`minion-agent`): `STATUS: RUST_CONTRACT_REVIEW`,
new exact `CODE PR`/`DOCS PR` SHAs, append the targeted-closure-rejection reference
(`minion-agent-docs#47` @ `ae599ba9660907593ac9d020bdeca1ca57d01fe2`) to `PRIOR REVIEW EVIDENCE`,
`NEXT_OWNER: Codex`, `NEXT_ACTION: confirm L10-R005's own residual contradictory wording is fully
removed from AI-030 (both the row-opening historical sentence and the LlmService.models() paragraph)
and from this assurance document's own PASS-4 summary line, then -- since L10-R006/L10-R007 are
already provisionally closed and no further finding is open -- proceed directly to the mandatory
§11.8.8 final complete review of this exact candidate. L10-R003 remains an explicit, disclosed,
OPEN Rust-only defect, out of scope; Layer 11 remains not started`. Then stop. Do not merge any
candidate or review-evidence PR. Do not implement Rust. Do not start Layer 11.

# PASS 6 — remediate the mandatory §11.8.8 final complete review's own narrow L10-R008 finding

## Final complete review reference

The MANDATORY §11.8.8 final complete independent Rust contract review of the PASS-5 candidate
(code PR #20 @ `ef1d2b033deced9cbc0396467eeda2f3e3454008`, docs PR #45 @
`038fc5488e8b7473654f37ec04d49d7a5881c622`, `minion-agent-docs#47` @
`dc5b6a48eed12269a2c13f6a8bb6c008c0aa03e5`) confirmed `L10-R001`/`L10-R002`/`L10-R004`/`C10-C005`/
`L10-R005`/`L10-R006`/`L10-R007` all CLOSED -- "All semantics, canonical behavior, runner design,
and Rust feasibility otherwise passed" -- but **REJECTED** the candidate on one new, narrow finding:

- **`L10-R008`** (`CONTRACT_ASSURANCE_DEFECT`, blocking): parsing `pi-parity-manifest.yaml` with
  `yaml.safe_load` showed two Layer-10 `tests:` entries (`AI-029[1]`, `AI-030[7]`) were YAML
  mappings, not evidence strings -- an unquoted `: ` inside a plain scalar list item silently
  starts a one-key mapping, which `yaml.safe_load` accepts without error. The same whole-manifest
  probe found two PRE-EXISTING `AG-007` entries with the identical defect. Separately, the new
  `llm-service-more-than-eight-calls-settle-ok.yaml` acceptance witness (`L10-R007`) appeared only
  in assurance prose, linked from no requirement row's own `tests:` list.

Independently re-verified this pass: parsed the manifest and confirmed all four malformed entries
present, verbatim, exactly as the review cited them (`AI-029` tests[1], `AI-030` tests[7], `AG-007`
tests[36] and tests[38], all `dict` instead of `str`) -- not accepted on the review's own prose
alone.

## Finding closed this pass

### L10-R008 — malformed and incomplete Layer-10 manifest evidence

**Remediation (documentary only, matching the review's own required narrow scope -- no production,
canonical behavior, spec semantics, disposition, or owner-governance change):**

1. The two Layer-10 `tests:` entries (`AI-029`, `AI-030`) and the two pre-existing `AG-007` entries
   quoted as proper single-quoted YAML scalar strings (embedded apostrophes doubled per YAML
   single-quote escaping), so each parses as a plain string again, not a one-key mapping.
2. `llm-service-more-than-eight-calls-settle-ok.yaml` added to `AI-028`'s own `tests:` list --
   `AI-028` is the natural owner, since the scenario proves repeated successful calls through the
   `stream` seam `AI-028` itself governs.
3. A new, PERMANENT automated gate: `tests/conformance/test_manifest_validation.py`, five tests --
   unique row IDs, every row carries the required field set, every row's own `disposition` is one
   of the three values `agent-workflow.md` section 8 defines, every `tests:` entry is a non-empty
   STRING (the exact structural check this finding's own root cause needed and the prior ad-hoc,
   manually-run "N rows / N unique IDs" one-liner never performed), and every row has at least one
   `tests:` entry. This closes the review's own explicit "extend the manifest validation gate"
   requirement -- the check is now a committed, repeatable pytest module, not a one-off command
   typed into a shell each pass.

## Revert-and-confirm (genuine RED against the exact PASS-5 candidate)

The new `test_every_tests_entry_is_a_non_empty_string` gate was verified to genuinely discriminate
before being trusted: the exact PASS-5 candidate's own `pi-parity-manifest.yaml` (`git show
ef1d2b0:pi-parity-manifest.yaml`) was temporarily restored in place of the fixed manifest; the new
test FAILED, reporting exactly the four malformed entries the review's own audit found (`AI-029`
tests[1], `AI-030` tests[7], `AG-007` tests[36], `AG-007` tests[38], all `dict`) -- the other four
new manifest-validation tests passed even against the unfixed candidate (row-ID uniqueness,
required fields, valid dispositions, and non-empty `tests:` lists were never the defect). The fixed
manifest was restored; all five tests pass again.

## Regression verification for previously-closed findings

`L10-R001`/`L10-R002`/`L10-R004`/`C10-C005`/`L10-R005`/`L10-R006`/`L10-R007`: unaffected -- no
production, schema, runner, spec, or disposition content changed, only manifest evidence-string
quoting and one new traceability link. No Python source file under `src/` was touched. All seven
llm-service canonical scenarios and all twelve runner-validation tests still pass unchanged.

## Quality gates (fresh, this pass)

```text
pytest (full suite):                 1168 passed, 19 xfailed (pre-existing, unrelated), 0 failed
coverage (certified src packages):   100.00%, unchanged (no source file under src/ touched)
ruff check:                          clean (whole tree)
ruff format --check:                 clean on every file this pass touched; the same pre-existing,
                                      unrelated 7-file drift noted in every earlier layer's own
                                      passes remains untouched (the new test_manifest_validation.py
                                      itself needed one auto-format pass after this pass's own
                                      edit, applied and re-verified clean)
mypy (configured scope, src only):   clean, 0 errors, 58 source files
conformance/ (full):                 334 passed, 19 xfailed (up from 329 -- five new manifest
                                      validation tests)
manifest parse + unique-ID audit:    84 / 84 unique, unchanged; ALL tests[] entries now confirmed
                                      genuine non-empty strings (0 malformed, down from 4), enforced
                                      going forward by the new permanent gate
```

## Active findings (after this pass)

```text
PI_PARITY_DEFECT               L10-R003 -- OPEN, current Rust production only, unchanged
CONTRACT_ASSURANCE_DEFECT      none -- L10-R008 closed this pass; no finding remains open
PI_BEHAVIOR_UNCERTAIN          none
unapproved intentional divergence   none
disclosed Minion architectural mapping   AI-029's own eager full-identity-lookup simplification,
                                unchanged
disclosed Minion-specific constraint   AI-030 (registration/withdrawal/introspection, compared
                                honestly against all three real Pi registration surfaces, no
                                residual contradictory wording, owner-approved intentional
                                divergence, §11.7 decision recorded); AI-031 (streamSimple,
                                deferred parity); AI-032 (fetchDeferred/cancelDeferred, deferred
                                parity, four-layer closure criterion); ModelId.api's own
                                Python-only "mock" default (LLM-F006, unchanged)
Rust cross-language dependency      PARTIAL, unchanged
Layer 11                       NOT STARTED
```

## Verdict

```text
Python Layer 10     CERTIFIED (self-certified; pending independent re-review of this exact
                       candidate -- L10-R008 was raised at the mandatory §11.8.8 final complete
                       review itself, so per that review's own instruction, "any changed candidate
                       SHA requires another complete exact-SHA review," the NEXT review of this
                       candidate is another full §11.8.8 final complete review, not a narrower
                       targeted closure)
Rust Layer 10          NOT_IMPLEMENTED for L10-R003/AI-030's own open gaps; PARTIALLY_IMPLEMENTED
                          for AI-028's stream/AI-029's resolution behavior, unchanged
shared Layer-10 contract   No finding open at this exact candidate; READY FOR ANOTHER MANDATORY
                             §11.8.8 FINAL COMPLETE REVIEW (the changed-SHA rule applies since
                             L10-R008 was found at that exact review stage)
Layer 10 cross-language     NOT CLOSED
Layer 11                     NOT STARTED
```

## Next action

Push this pass's commits to the existing `layer/10-python-shared` branches (both repos); verify
both new commits are remote-reachable; update PR #20/#45 bodies with this remediation summary and
the new head SHAs. Update coordination issue #19 (`minion-agent`): `STATUS: RUST_CONTRACT_REVIEW`,
new exact `CODE PR`/`DOCS PR` SHAs, append the final-complete-rejection reference
(`minion-agent-docs#47` @ `dc5b6a48eed12269a2c13f6a8bb6c008c0aa03e5`) to `PRIOR REVIEW EVIDENCE`,
`NEXT_OWNER: Codex`, `NEXT_ACTION: L10-R008 was raised at the mandatory §11.8.8 final complete
review itself -- per that review's own instruction, a changed candidate SHA requires ANOTHER
complete exact-SHA review, not a narrower targeted closure. Perform a full §11.8.8 final complete
review of this exact candidate: confirm the four manifest evidence entries now parse as genuine
strings, confirm the new >8-call scenario is now linked from AI-028's own tests: list, and confirm
the new permanent manifest-validation gate itself correctly enforces the structural invariant this
finding exposed. L10-R003 remains an explicit, disclosed, OPEN Rust-only defect, out of scope;
Layer 11 remains not started`. Then stop. Do not merge any candidate or review-evidence PR. Do not
implement Rust. Do not start Layer 11.

# PASS 7 — remediate the second §11.8.8 review's own narrow L10-R008 finding (container-type gap)

## Second final complete review reference

The second mandatory §11.8.8 final complete review of the PASS-6 candidate (code PR #20 @
`a7d05f26b22e1168c58578f5423d9a5c6f2ed0e3`, docs PR #45 @ `7c8d8ed68d0c903b8262e82aca80537bd2267ed8`,
`minion-agent-docs#47` @ `b41bcd982eb65072717a49b5c9214db1253893d7`) confirmed every OTHER finding
CLOSED -- `L10-R001`/`L10-R002`/`L10-R004`/`C10-C005`/`L10-R005`/`L10-R006`/`L10-R007` -- but
**REJECTED** narrowly: `L10-R008` was PARTIALLY RESOLVED, not fully closed.

The review's own discriminating probe: `test_manifest_validation.py`'s PASS-6 checks iterated
`row["tests"]` and inspected only what iteration yielded, never asserting the container itself was
a `list`. A scalar STRING is itself iterable, yielding one-character strings that are each
individually non-empty -- so a synthetic row `{"tests": "evidence"}` passed BOTH the
"every entry is a non-empty string" check (its own iteration yields `"e"`, `"v"`, `"i"`, ...,
each non-empty) AND the separate "at least one entry" truthiness check (a non-empty string is
truthy). Independently re-verified this pass by reconstructing the exact PASS-6 file's own two
check bodies against the reviewer's own synthetic row -- both incorrectly reported zero violations,
confirmed before any fix was written.

## Finding closed this pass

### L10-R008 — permanent manifest gate did not assert `tests` is a list before iterating it

**Remediation:** `tests/conformance/test_manifest_validation.py` rewritten around a single,
directly-testable `_tests_field_violations(row)` helper that asserts `isinstance(row["tests"],
list)` FIRST, before any iteration -- a non-list container is rejected immediately, never iterated.
The two PASS-6 checks (`test_every_tests_entry_is_a_non_empty_string`,
`test_every_row_has_at_least_one_tests_entry`) replaced with one `test_every_row_tests_field_is_
well_formed` that runs the same helper against the real manifest. Four new direct unit tests
exercise the helper itself against synthetic rows, independent of the real manifest content:
`test_tests_field_violations_rejects_a_scalar_string_container` -- the review's own exact
discriminating probe, `{"id": "X", "tests": "evidence"}`, now correctly rejected;
`test_tests_field_violations_accepts_a_well_formed_list` -- the positive counterpart;
`test_tests_field_violations_rejects_an_empty_list`; `test_tests_field_violations_rejects_a_
non_string_entry` -- a list containing one genuine string and one non-string member.

## Revert-and-confirm (genuine RED against the exact PASS-6 candidate)

The new scalar-container rejection was verified to genuinely discriminate before being trusted:
the exact PASS-6 candidate's own two check bodies (`git show a7d05f2:.../test_manifest_
validation.py`) were reconstructed and run directly against the reviewer's own synthetic probe
row (`{"id": "X", "tests": "evidence"}`) -- both PASS-6 checks reported ZERO violations (the bug,
reproduced exactly as the review described), confirming the exact candidate the review examined
genuinely had this gap. The new `_tests_field_violations` helper, run against the same row,
correctly reports one violation naming the container-type defect. All 8 tests in the rewritten
module pass against the real manifest (which remains clean, unchanged from PASS 6).

## Regression verification for previously-closed findings

`L10-R001`/`L10-R002`/`L10-R004`/`C10-C005`/`L10-R005`/`L10-R006`/`L10-R007`: unaffected -- only
`tests/conformance/test_manifest_validation.py` changed; no manifest content, production, schema,
runner, spec, or disposition file was touched. All seven llm-service canonical scenarios and all
twelve runner-validation tests still pass unchanged.

## Quality gates (fresh, this pass)

```text
pytest (full suite):                 1171 passed, 19 xfailed (pre-existing, unrelated), 0 failed
coverage (certified src packages):   100.00%, unchanged
ruff check:                          clean (whole tree)
ruff format --check:                 clean; the same pre-existing, unrelated 7-file drift remains
mypy (configured scope, src only):   clean, 0 errors, 58 source files
conformance/ (full):                 337 passed, 19 xfailed (up from 334 -- net +3 from the
                                      rewritten manifest-validation module: 2 checks replaced by
                                      1, plus 4 new direct unit witnesses)
manifest parse + unique-ID audit:    84 / 84 unique, unchanged; container-type structural gap now
                                      closed by the permanent gate itself
```

## Active findings (after this pass)

```text
PI_PARITY_DEFECT               L10-R003 -- OPEN, current Rust production only, unchanged
CONTRACT_ASSURANCE_DEFECT      none -- L10-R008 fully closed this pass; no finding remains open
PI_BEHAVIOR_UNCERTAIN          none
unapproved intentional divergence   none
disclosed Minion architectural mapping   AI-029's own eager full-identity-lookup simplification,
                                unchanged
disclosed Minion-specific constraint   AI-030 (registration/withdrawal/introspection, compared
                                honestly against all three real Pi registration surfaces, owner-
                                approved intentional divergence, §11.7 decision recorded); AI-031
                                (streamSimple, deferred parity); AI-032 (fetchDeferred/
                                cancelDeferred, deferred parity, four-layer closure criterion);
                                ModelId.api's own Python-only "mock" default (LLM-F006, unchanged)
Rust cross-language dependency      PARTIAL, unchanged
Layer 11                       NOT STARTED
```

## Verdict

```text
Python Layer 10     CERTIFIED (self-certified; pending independent re-review of this exact
                       candidate -- L10-R008 was raised at a mandatory §11.8.8 final complete
                       review itself, so per that review lineage's own repeated instruction, "any
                       changed candidate SHA requires another complete exact-SHA review," the NEXT
                       review of this candidate is another full §11.8.8 final complete review)
Rust Layer 10          NOT_IMPLEMENTED for L10-R003/AI-030's own open gaps; PARTIALLY_IMPLEMENTED
                          for AI-028's stream/AI-029's resolution behavior, unchanged
shared Layer-10 contract   No finding open at this exact candidate; READY FOR ANOTHER MANDATORY
                             §11.8.8 FINAL COMPLETE REVIEW
Layer 10 cross-language     NOT CLOSED
Layer 11                     NOT STARTED
```

## Next action

Push this pass's commits to the existing `layer/10-python-shared` branches (both repos); verify
both new commits are remote-reachable; update PR #20/#45 bodies with this remediation summary and
the new head SHAs. Update coordination issue #19 (`minion-agent`): `STATUS: RUST_CONTRACT_REVIEW`,
new exact `CODE PR`/`DOCS PR` SHAs, append the second-final-complete-rejection reference
(`minion-agent-docs#47` @ `b41bcd982eb65072717a49b5c9214db1253893d7`) to `PRIOR REVIEW EVIDENCE`,
`NEXT_OWNER: Codex`, `NEXT_ACTION: L10-R008 was raised at a mandatory §11.8.8 final complete review
itself -- per that review's own repeated instruction, a changed candidate SHA requires ANOTHER
complete exact-SHA review, not a narrower targeted closure. Perform a full §11.8.8 final complete
review of this exact candidate: confirm the manifest-validation gate now asserts tests is a list
before iterating it, and confirm the new scalar-container negative witness genuinely discriminates.
L10-R003 remains an explicit, disclosed, OPEN Rust-only defect, out of scope; Layer 11 remains not
started`. Then stop. Do not merge any candidate or review-evidence PR. Do not implement Rust. Do
not start Layer 11.
