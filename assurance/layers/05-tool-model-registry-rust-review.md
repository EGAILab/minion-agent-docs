# Layer 05 Tool Model + Registry — Independent Rust Contract Review

**Review date:** 2026-08-26  
**Implementation candidate:** `minion-agent@d9054fe799f5209a2887f2b22d1dc482ec72826c`  
**Documentation candidate:** `minion-agent-docs@6443b4635e1e737c1173a501674f94e66406d94e`  
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`  
**Verdict:** **REJECTED** — one `PI_PARITY_DEFECT` and four `CONTRACT_ASSURANCE_DEFECT`s block Rust implementation.

This is a review-only artifact. No Rust Layer-05 implementation was made. Python was inspected only
after Pi, the shared contract, canonical evidence, and Rust architecture.

## 1. Pi audit

Pinned Pi defines:

- `Tool`: required `name`, `description`, and `parameters`; optional
  `constrainedSampling?: false | ConstrainedSamplingConfig`.
- `GrammarFormat = "openai_lark" | "openai_regex"` and
  `GrammarVariants = Partial<Record<GrammarFormat, string>>`.
- constrained sampling as `json_schema { strict: prefer | require }` or
  `grammar { variants }`; absence and explicit `false` remain representable.
- `AgentTool`: required `label` and `execute`; optional synchronous `prepareArguments`; optional
  `executionMode` with `sequential | parallel` values.
- `execute(toolCallId, params, signal?, onUpdate?) -> Promise<AgentToolResult>`.
- plain `AgentState.tools` / optional `AgentContext.tools` arrays. Pi has no scoped tool registry;
  Minion registry rules are architectural mappings, not direct Pi features.

The Layer-05/06 split is otherwise sound: Layer 05 represents metadata and callback capability
boundaries; Layer 06 invokes preparation/execution, applies scheduling, handles updates and
cancellation, and converts results/errors.

## 2. Evidence table

| Area | Pi audited | Spec complete | Canonical evidence | Rust feasible | Finding |
|---|---:|---:|---:|---:|---|
| Tool base model | YES | YES | schema projection | YES | none |
| parameters schema | YES | YES | schema projection | YES | parity-constrained raw-JSON boundary |
| constrained sampling | YES | NO | partial | YES after repair | `L05-R001` |
| label | YES | YES | schema projection | YES | none |
| executionMode | YES | YES | language tests | YES | none |
| prepareArguments boundary | YES | YES | type evidence | YES | none |
| execute boundary | YES | YES, behavior deferred | type evidence | YES | none |
| visibility | n/a/mapped | contradictory at disposed scope | YES | NO as written | `L05-R002` |
| shadowing | n/a/mapped | YES | YES | YES | none |
| duplicate names | n/a/mapped | YES | YES | YES | none |
| ordering | n/a/mapped | YES | YES | YES | none |
| withdrawal/lifecycle | mapped | intersection underspecified | incomplete | needs Runtime seam decision | `L05-R003` |
| lifecycle fixture integrity | n/a/mapped | YES | NO | n/a | `L05-R004` |
| raw schema / null boundary | mapped | NO | NO | YES after repair | `L05-R005` |

## 3. Findings

### L05-R001 — grammar variants falsely widened and attributed to Pi

**Taxonomy:** `PI_PARITY_DEFECT`  
**Affected requirement:** `TOOL-008`  
**Source evidence:** pinned Pi `packages/ai/src/types.ts::GrammarFormat/GrammarVariants`  
**Affected contract:** `spec/tools.md` constrained-sampling model  
**Affected canonical schema:** `conformance/schema/tool-registry-scenario.schema.json`

Pi's grammar map is not open-string-keyed. Its key type is the closed union
`"openai_lark" | "openai_regex"`, with either key optional. The spec, manifest, assurance record,
and canonical schema instead say arbitrary string keys are valid and claim this matches Pi.
Consequently Rust cannot know whether to expose a closed Pi-compatible enum/map or accept unknown
formats as shared-contract-valid values.

Minimal repair: either restrict the shared/canonical shape to the two pinned Pi formats, or record
an explicit, reviewed Minion divergence (with rationale and disposition) instead of calling the
open map adopted Pi parity. Add negative/positive schema evidence for the chosen rule. Python
Layer-05 certification must reopen because its public type and schema currently accept the widened
surface.

### L05-R002 — disposed-scope query contradicts certified Runtime semantics

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`  
**Affected requirements:** `TOOL-010`, `TOOL-014`  
**Affected contract:** `spec/tools.md` visibility and lifecycle rules  
**Affected scenario:** `tool-registry-scope-disposal-withdraws.yaml`

The scenario disposes `child`, then queries *from that disposed child* and expects the global
`root_tool`. Certified Rust `ScopedRegistry::visible_from` uses
`ScopeTree::active_ancestor_chain`; an inactive request scope intentionally yields no visibility.
Existing Runtime tests pin that result as empty. This conflicts with the contract's claim that tool
visibility reuses certified Runtime scope rules unmodified.

Minimal repair: define whether querying an inactive/disposed scope is valid and its exact result.
Then either change the scenario to query from a live scope, expect no tools from an inactive scope,
or approve a distinct nearest-live-ancestor tool lookup without changing the certified generic
`ScopedRegistry` rule. Rust must not silently change Runtime behavior to satisfy the fixture.

### L05-R003 — plugin/scope dual ownership is not fully specified or evidenced

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`  
**Affected requirement:** `TOOL-014`  
**Affected contract:** `spec/tools.md` registration lifecycle  
**Affected canonical evidence:** `tool-registry-plugin-disposal-withdraws.yaml`,
`tool-registry-scope-disposal-withdraws.yaml`

The contract says either plugin unmount or owning-scope disposal withdraws a registration. The
canonical suite proves unmount only for an unscoped plugin and scope disposal only for a scoped
registration; it never proves unmount of a plugin whose tool is scope-owned. In certified Rust,
`FiberInitContext::effect` routes scoped effects to the scope effect store, while fiber unmount
disposes only the fiber generation store. Thus a scoped registration would survive plugin unmount
until scope disposal.

Minimal repair: explicitly specify the dual-owner intersection and add a canonical scenario for a
scoped plugin unmount. If both events must withdraw, document the required language-neutral
idempotent ownership semantics. Rust can then add a narrow fiber-bound disposal attachment while
reusing the existing scope tree; it must not create a second scope hierarchy.

### L05-R004 — scope-disposal fixture does not construct its claimed hierarchy

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`  
**Affected requirements:** `TOOL-010`, `TOOL-014`  
**Affected scenario:** `tool-registry-scope-disposal-withdraws.yaml`  
**Affected runner boundary:** `_ScopeTable.key_for`

The fixture declares `scope_parent: root_scope`, but no plugin/step ever creates `root_scope`.
`_ScopeTable.key_for` resolves a missing parent with `dict.get()` and silently creates `child` and
`sibling` as parentless scopes. The green scenario therefore does not prove the descendant cascade,
ancestor survival, or sibling relationship claimed by its notes. The schema also does not validate
parent references.

Minimal repair: construct the parent scope explicitly and reject unresolved parent references at
the canonical boundary. Re-run the observation through the real Runtime seam after resolving
`L05-R002`'s disposed-query rule.

### L05-R005 — “arbitrary JSON Schema” and legacy-null aliases are not pinned

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`  
**Affected requirement:** `TOOL-010`  
**Affected contract:** `spec/tools.md` parameter representation  
**Affected schema/runner:** `tool-registry-scenario.schema.json`, `_tool_definition`

The contract claims arbitrary/raw JSON Schema, but the canonical schema accepts only JSON objects;
valid boolean schemas (`true` and `false`) cannot be represented. Conversely, `parameters` may be
omitted or explicitly null and the runner silently maps both to the empty object schema. The same
input-side omission/null conflation exists for constrained sampling even though Pi's model has
absent/false/config, not null.

Minimal repair: either define the public boundary as object-valued JSON Schema (and remove the
“arbitrary JSON Schema” overclaim) or admit the complete intended JSON Schema value domain. Specify
whether canonical input null is a deliberate legacy/DSL alias and keep that alias out of the typed
model. Add schema probes for the adopted boundary.

## 4. Canonical and manifest review

Eight scenarios exist and are dynamically consumable by Rust:

1. `tool-registry-nearer-shadows-farther`
2. `tool-registry-plugin-disposal-withdraws`
3. `tool-registry-resolve-unknown-is-absent`
4. `tool-registry-same-scope-duplicate-name`
5. `tool-registry-schema-projection`
6. `tool-registry-scope-disposal-withdraws`
7. `tool-registry-scope-visibility`
8. `tool-registry-withdrawal-restores-farther`

The Python runner is thin for lookup, shadowing, ordering, withdrawal, and resolution: it creates
real contexts/scopes/fibers, registers through the real API, and reads real registry results. Its
scope table does not itself implement visibility, but its silent missing-parent fallback materially
weakens one fixture. The two lifecycle scenarios also leave the dual-owner intersection untested,
and one fixture encodes the disposed-scope contradiction described above.

Manifest rows `TOOL-010` through `TOOL-014` correctly identify Minion registry architecture as
`N/A` for direct Pi equivalence and use `intentional divergence`. `TOOL-008`, however, incorrectly
labels the open grammar-key surface `adopted` Pi behavior. `TOOL-009` correctly records the
AgentTool field boundary and Layer-06/09 invocation defer.

## 5. Rust feasibility and boundary

Rust can represent the model independently with typed enums/capabilities, an owned JSON value at
the parameter-schema boundary, and erased `Send + Sync + 'static` callbacks returning boxed
futures. `None`, explicit disabled/false, JSON-schema config, and grammar config are losslessly
representable. An ordered map or a two-key typed structure can represent repaired grammar variants.

The existing `ScopeTree`, `ScopedRegistry`, `EffectStore`, and explicit async
`RegistrationHandle::dispose` are reusable. They already provide nearest-first ancestry,
registration-order stability, same-scope earliest-wins composition, fallback after removal, and
scope-owned cleanup. A second scope tree is unnecessary and prohibited by the architecture.

A narrow Runtime API addition may be needed after contract repair to attach a scoped tool's
withdrawal to its mounting fiber as well as its scope. That is not a coordinator/tree redesign,
but the observable dual-owner rule must be settled first. Dropping a Rust registration handle is
not currently RAII withdrawal; explicit async disposal is the certified mechanism.

## 6. Layer-05 / Layer-06 ownership

| Concern | Layer 05 | Layer 06 |
|---|---|---|
| tool metadata / parameters / constrained sampling / label | own | consume |
| executionMode override | represent absence/sequential/parallel | resolve and enforce |
| prepareArguments | represent synchronous capability | invoke, order, handle errors |
| execute | represent future-capable signature | invoke and dispatch |
| validation timing and hooks | no | yes |
| sequential contagion / parallel execution | no | yes |
| update and cancellation | signature shape only | behavioral handling |
| result/error conversion / terminate folding | no | yes |

This separation is adequate and permits Layer 06 to consume the repaired Layer-05 model without
redesigning it.

## 7. Verdict

Proportional verification performed during review:

- Python tool-registry canonical plus schema validation: **155 passed** with coverage disabled for
  the focused run. (The first focused invocation's tests passed but the process correctly failed
  the repository-wide 100% coverage threshold because it was not the full suite.)
- Rust `runtime_scope`, `runtime_disposable`, and `runtime_fiber`: **42 passed**.

```text
Layer-05 shared contract
    REJECTED

Rust Layer 05
    NOT_IMPLEMENTED

Rust implementation modified
    NO

Layer 06
    NOT STARTED
```

Required next action: return `L05-R001`..`L05-R005` to the shared/Python owner for narrow repair,
new candidate SHAs, and a fresh Rust review. Do not begin Rust Layer-05 implementation.
