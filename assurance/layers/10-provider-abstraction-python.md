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

## Next action

Create the Layer 10 coordination issue in `minion-agent` (`STATUS: PYTHON_SHARED`, `NEXT_OWNER:
Claude` while candidates are pushed, then `RUST_CONTRACT_REVIEW`/`NEXT_OWNER: Codex` once pushed).
Push this pass's commits to new `layer/10-python-shared` branches (both repos); open paired PRs
identifying the layer, companion PR, coordination issue, exact candidate head SHAs, pass type
(Python/shared, documentary-only), and stop condition (ready for independent Rust contract review
of `AI-028`/`AI-029` and the new `spec/llm.md` section; Layer 11 remains not started; no Python or
Rust behavior was changed by this pass). Request Codex confirm whether the existing Rust
implementation already satisfies both new rows as formalized, or identify a narrow remediation, per
the standing ownership flow. Do not implement Rust. Do not start Layer 11.
