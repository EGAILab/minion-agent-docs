# Layer 05 Tool Model + Registry — Independent Rust Re-Review

**Review date:** 2026-08-26

**Repaired implementation candidate:** `minion-agent@816fc9f57fd8aded7af264ad2361b4194b594089`

**Repaired documentation candidate:** `minion-agent-docs@ddfe715bedfc1cc1dd7c5c8996b9bf0de842ee37`

**Original rejection:** `minion-agent-docs@fc741e0e4ba162303b89732dc5704744468bb1e5`

**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`
**Verdict:** **REJECTED** — `L05-R001`, `L05-R002`, `L05-R004`, and `L05-R005`
remain open; new `L05-R006` was found. `L05-R003` is resolved.

This is a review-only artifact. No Rust or shared semantic artifact was modified. The unrelated
working-tree edit to the Phase-5 provider review-feedback document was preserved untouched.

## 1. Authority audit

Pinned Pi still defines:

- `Tool`: required `name`, `description`, `parameters`; optional
  `constrainedSampling?: false | ConstrainedSamplingConfig`.
- `GrammarFormat = "openai_lark" | "openai_regex"` and
  `GrammarVariants = Partial<Record<GrammarFormat, string>>`.
- `AgentTool`: required `label` and future-producing `execute`; optional synchronous
  `prepareArguments`; optional `executionMode` (`sequential | parallel`).
- plain tool arrays, not Minion's scoped registry. Registry rules are Minion architectural
  mappings and must remain identified as such.

No Pi behavior is uncertain. The Layer-05/06 boundary remains correct: Layer 05 owns model and
capability shape; Layer 06 owns invocation, validation, scheduling, updates, cancellation behavior,
and result conversion.

## 2. Finding closure table

| Finding | Previous issue | Repaired rule | Evidence checked | Rust verdict |
|---|---|---|---|---|
| `L05-R001` | Open grammar keys | Closed two-key model | Pi types, spec, schema, manifest, Python model/tests | **OPEN** |
| `L05-R002` | Disposed-scope ambiguity | Disposed `Scope` observes no tools | Layer-01 evidence, spec, manifest, scenario, Python/Rust Runtime | **OPEN** |
| `L05-R003` | Plugin/scope lifetime ambiguity | Scope-owned after scoped registration | Spec, TOOL-014, new scenario, both Runtime ownership seams | **RESOLVED** |
| `L05-R004` | Missing parent silently accepted | Reference checks plus real parent fixture | Scenario, runner, malformed-reference probes | **OPEN** |
| `L05-R005` | Parameter domain/null shorthand | Required object-valued schema canonically | Pi, spec, schema, canonical files, Python public type | **OPEN** |

## 3. Remaining and new findings

### L05-R001 — grammar contract remains internally contradictory

**Taxonomy:** `PI_PARITY_DEFECT` + `CONTRACT_ASSURANCE_DEFECT`

**Affected requirement:** `TOOL-008`

**Affected spec:** `spec/tools.md`, Tool summary and constrained-sampling prose

**Affected evidence:** `pi-parity-manifest.yaml`, canonical grammar schema

Several repaired surfaces correctly close keys to `openai_lark` and `openai_regex`: the detailed
spec prose, Python named fields, and canonical `additionalProperties: false`. However:

1. the normative Tool summary still says `grammar{variants: open-string-keyed map}`;
2. current manifest row `TOOL-008` still says the keys are open and “never a closed enum”;
3. Pi's `Partial<Record<GrammarFormat, string>>` statically permits `{}`, while canonical
   `minProperties: 1` rejects an empty variants object; Python's two optional fields can produce
   that empty object.

Minimal repair: make the summary and manifest closed-keyed, decide the Pi-compatible empty-map
state at Layer 05, and align Python/schema/canonical evidence. Provider-time rejection of an empty
grammar selection must not be pulled into Layer 05 merely because a later provider requires one.
Python Layer-05 certification remains affected.

### L05-R002 — disposed-scope behavior works but is absent from the normative contract

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`

**Affected requirements:** `TOOL-010` and the missing disposed-observation trace

**Affected spec:** `spec/tools.md`, Registry

**Affected evidence:** `tool-registry-scope-disposal-withdraws.yaml`

The repaired fixture expects no tools from a disposed `Scope`, Python's real `ToolRegistry` checks
`Scope.disposed`, and certified Rust `ScopedRegistry` already returns empty for an inactive
`ScopeId`. Layer 01 was silent about this particular post-disposal observation, so no Layer-01
reopening or Runtime source delta is needed.

But `spec/tools.md` never states the disposed-scope rule, and `TOOL-010` still describes only active
nearest/ancestor/global visibility. A Rust implementer following spec + manifest cannot derive the
new behavior without reading the scenario, handoff, or Python. The Python API also accepts a bare
`ScopeKey`, which bypasses liveness and can return ancestor/global tools after the corresponding
`Scope` was disposed, leaving the semantic query input insufficiently pinned.

Minimal repair: normatively state that ToolRegistry observation requires a live scope handle and a
disposed/inactive requesting scope yields no tools; trace it in the manifest/requirements; decide
whether the bare-key overload is internal, invalid for this rule, or intentionally has different
semantics. Layer 01 remains closed.

### L05-R004 — parent validation is not effective at the runner boundary

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`

**Affected evidence:** `tool-registry-scope-disposal-withdraws.yaml`, `_ScopeTable`

The fixture now creates `root_scope` and correctly proves live ancestor/sibling survival plus empty
disposed-child visibility. Unknown query scopes raise a useful `ValueError`. An unknown
`scope_parent`, however, fails inside plugin application; reconciliation records the fiber failure
and continues. The full scenario later surfaces only an incidental `KeyError('child')`, rather than
the promised explicit malformed-parent rejection. A fresh real-runner probe reproduced this.

Minimal repair: validate all parent/query/step references before mounting, or explicitly propagate
the plugin-application validation failure from reconciliation. This remains boundary validation,
not registry simulation.

### L05-R005 — required parameter boundary still conflicts with the public definition

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`

**Affected contract:** `spec/tools.md`, Tool definition/empty schema

**Affected implementation evidence:** `ToolDefinition.parameters`

Canonical repair is correct: `parameters` is required, null is rejected, every fixture writes the
empty object schema explicitly, nested object-valued schemas preserve arbitrary keywords, and
boolean schemas are explicitly outside the declared domain.

The semantic/public boundary is still contradictory. The Tool summary says `parameters` is a
required JSON Schema object, but nearby prose says a tool “with no parameter schema” is normalized.
Python's public `ToolDefinition.parameters` remains `... | None` and accepts missing/None as an
empty schema. Two independent Rust designs—required `serde_json::Value` versus optional value with
normalization—would both find support in the package.

Minimal repair: either make the public tool definition require an object-valued schema end to end,
or explicitly specify a language-neutral authoring normalization from absence to the required
empty-object semantic value. Align Python typing/evidence and state what Rust must expose. Boolean
schemas may remain out of scope.

### L05-R006 — canonical input invents a null constrained-sampling alias

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`

**Affected requirement:** `TOOL-008`

**Affected schema/runner:** `constrainedSamplingInput`, `_constrained_sampling`

The shared model lists exactly absent, false, JSON-schema config, and grammar config. Canonical
input additionally accepts explicit null and maps it to the same Python `None` as absence. The spec
does not define null as a legacy/DSL alias. A focused schema probe confirmed explicit null is
accepted.

Minimal repair: remove null from canonical input or explicitly define and justify the boundary
normalization while keeping it distinct from the typed semantic states. Output normalization may
continue using a separately specified canonical null-for-absence convention.

## 4. Resolved lifetime model (`L05-R003`)

The repaired lifetime matrix is coherent:

| Registration | Plugin unmount | Scope disposal | Explicit withdrawal |
|---|---|---|---|
| unscoped/fiber-owned | withdrawn | n/a | withdrawn |
| scoped/scope-owned | survives | withdrawn | withdrawn |

The new `tool-registry-scoped-registration-survives-plugin-unmount` scenario mounts one scoped
plugin, registers one tool, unmounts that same plugin, keeps the scope live, and observes that same
registration. The existing scope-disposal and explicit-withdrawal scenarios cover the other legs.
The runner does not manually preserve or withdraw anything.

This matches certified Rust: scope-owned `ScopedRegistry::register` installs removal in the
scope's `EffectStore`; fiber unmount disposes only the fiber-generation store. No fiber-bound dual
ownership, Runtime redesign, or second lifecycle coordinator is needed. Future callback objects can
safely outlive the registering fiber when stored as owned `Send + Sync + 'static` values with owned
captures. Tool authors must not capture resources with a shorter external lifetime.

## 5. Canonical review

Nine scenarios were discovered and all nine run through the real Python ToolRegistry/Runtime seam:

1. `tool-registry-nearer-shadows-farther`
2. `tool-registry-plugin-disposal-withdraws`
3. `tool-registry-resolve-unknown-is-absent`
4. `tool-registry-same-scope-duplicate-name`
5. `tool-registry-schema-projection`
6. `tool-registry-scope-disposal-withdraws`
7. `tool-registry-scoped-registration-survives-plugin-unmount`
8. `tool-registry-scope-visibility`
9. `tool-registry-withdrawal-restores-farther`

The runner remains thin for visibility, ancestry, shadowing, fallback, ordering, withdrawal,
plugin unmount, and scope disposal. It constructs real objects and normalizes observations. The
only active runner issue is ineffective end-to-end malformed-parent reporting (`L05-R004`).

Focused verification:

- Python tool-registry canonical: 9 collected, passed with `--no-cov`.
- Python canonical schema validation: 148 collected, passed with `--no-cov`.
- Rust `runtime_disposable`, `runtime_fiber`, `runtime_scope`: 42 passed, 0 failed.
- Schema probes: unknown grammar rejected; empty grammar rejected; explicit null constrained
  sampling accepted; missing/null parameters rejected; nested object schema accepted.

## 6. Rust implementability

After shared repair, Rust can reuse the existing `ScopeTree`, `ScopeHandle`, `ScopedRegistry`,
`EffectStore`, and explicit idempotent `RegistrationHandle`. No second scope tree or Runtime
redesign is required. Deterministic insertion-order composition supports nearest-first enumeration,
same-scope earliest-wins, shadowing, and fallback.

The model can use typed enums for constrained sampling/execution mode, an owned JSON object at the
schema boundary, and owned erased callbacks returning boxed futures. Layer 06 can later consume
that shape without redesign. Current blockers are contract/evidence clarity, not a Rust ownership
or architecture impossibility.

## 7. Verdict

```text
Layer-05 shared contract
    REJECTED

Python Layer 05
    certification affected by R001/R005/R006 and evidence integrity

Rust Layer 05
    NOT_IMPLEMENTED

Rust current certified position
    Layer 04

Rust implementation modified
    NO

Layer 06
    NOT STARTED
```

Return only the remaining findings (`L05-R001`, `L05-R002`, `L05-R004`, `L05-R005`) and new
`L05-R006` to the shared/Python owner for a narrow repair and fresh Rust re-review. Do not begin
Rust Layer-05 implementation.
