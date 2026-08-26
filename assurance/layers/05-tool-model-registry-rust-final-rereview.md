# Layer 05 Tool Model + Registry — Final Independent Rust Re-Review

**Review date:** 2026-08-26

**Implementation candidate:** `minion-agent@f945c598f7dabe3a68fb4158a723f824cefd89f4`

**Documentation candidate:** `minion-agent-docs@8714e28299e656f054bfc172c316a85052fe9e3e`

**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`

**Prior reviews:** `fc741e0e4ba162303b89732dc5704744468bb1e5`,
`61d42dc311c0fd5922197c34c4e326969bf64731`,
`7e288a62280969251153e080f28305ebad48fadc`

**Verdict:** **REJECTED** — only `L05-R005` remains open. `L05-R001`, `L05-R002`,
`L05-R003`, `L05-R004`, and `L05-R006` are resolved.

This is review-only evidence. No Rust, Python, spec, canonical, or manifest file was changed. The
unrelated Phase-5 provider-review working-tree edit was preserved untouched.

## 1. Closure table

| Finding | Current repair | Evidence | Rust verdict |
|---|---|---|---|
| `L05-R001` | Closed two-key GrammarFormat; empty variants admitted | Pi types, spec, TOOL-008, schema matrix | **RESOLVED** |
| `L05-R002` | Disposed `Scope` observes no tools; TOOL-015 trace | spec, manifest, real canonical case, Rust Runtime | **RESOLVED** |
| `L05-R003` | Scope-owned-after-registration | TOOL-014, real lifecycle scenario, both Runtime seams | **RESOLVED** |
| `L05-R004` | Whole-document reference prevalidation before Runtime construction | runner source, seven harness tests | **RESOLVED** |
| `L05-R005` | Required object-valued parameters at public boundary | spec, TOOL-016, schema, Python constructor probes | **OPEN** |
| `L05-R006` | Null rejected on input; null allowed only in output observation | split schema definitions and matrix tests | **RESOLVED** |

## 2. Resolved repairs

### L05-R001

Pinned Pi defines only `openai_lark` and `openai_regex`, and its `Partial<Record<...>>` permits
`{}`. The current spec summary, detailed prose, TOOL-008, input/output schemas, Python named-field
model, and schema tests now agree. Unknown keys and explicit input null are rejected. Empty,
lark-only, regex-only, and both-key maps are admitted. Provider-time usability checks remain
Layer 11.

### L05-R002

`spec/tools.md` and new Minion-architecture row TOOL-015 now state that a disposed/inactive
requesting `Scope` observes no tools. The real scenario proves empty enumeration despite otherwise
eligible ancestors. Certified Rust `active_ancestor_chain` already returns no chain for inactive
scopes. Layer 01 remains closed and no Runtime delta is required.

### L05-R003

The scope-owned-after-registration rule and scenario remain unchanged and green. A scoped tool
survives its originating plugin's unmount and is removed by explicit withdrawal or scope disposal.
Rust can store owned `Send + Sync + 'static` callbacks in the scope-owned registration without a
second lifecycle system.

### L05-R004

`_validate_references()` now runs before `Context()` construction. It validates parent existence,
self-parenting/cycles, mount/unmount/withdraw plugin references, disposal scopes, and query scopes.
Seven harness tests cover malformed cases and a valid hierarchy. It performs fixture validation
only; ancestry, visibility, shadowing, ordering, and disposal remain real Runtime/ToolRegistry
behavior.

### L05-R006

Canonical input and output use separate schema definitions. Input admits only omitted, false,
JSON-schema config, or grammar config; explicit null is rejected. Output may use null solely as the
established normalized representation of internal absence. This does not create a fifth semantic
input state.

## 3. Remaining blocker — L05-R005

**Taxonomy:** `PI_PARITY_DEFECT` + `CONTRACT_ASSURANCE_DEFECT`

**Affected requirement:** `TOOL-016`

**Affected contract:** `spec/tools.md`, required object-valued parameter schema

**Affected implementation evidence:**
`minion_agent.tools.definition.ToolDefinition.__post_init__`

The shared contract and canonical schema define an **object-valued JSON Schema** boundary. The
canonical schema's `"type": "object"` constrains the JSON value to be a mapping; it does not require
that mapping to contain a JSON Schema keyword `"type": "object"`. It therefore correctly admits,
for example:

```json
{"oneOf":[{"type":"string"},{"type":"number"}]}
{"type":"string"}
```

Both are object-valued schema representations, and Pi's generic `TParameters extends TSchema`
does not narrow its parameter to TypeBox's object-schema subtype.

The repaired Python public constructor instead accepts a raw dict only when:

```python
parameters.get("type") == "object"
```

Fresh direct probes produced:

```text
root-oneOf   canonical schema ACCEPT   ToolDefinition TypeError
root-string  canonical schema ACCEPT   ToolDefinition TypeError
object-root  canonical schema ACCEPT   ToolDefinition ACCEPT
```

This also conflicts with the requirement to preserve legitimate top-level `oneOf`/`anyOf`/`allOf`
and unknown object members without turning Layer 05 into a schema validator. A Rust implementation
cannot tell whether to preserve every object-valued schema as the shared schema says, or enforce a
top-level object-instance discriminator as Python does.

Minimal repair: retain requiredness and reject missing/null/boolean values, but accept any mapping
as the raw object-valued schema representation. Remove the `parameters.get("type") == "object"`
restriction (or, if a top-level object-instance schema is truly intended, narrow spec, manifest,
canonical schema, and Pi disposition explicitly). Add public-constructor tests for a top-level
combinator/annotation schema. Python Layer-05 certification remains affected until aligned.

## 4. Evidence and architecture

Fresh focused verification:

- tool-registry canonical: **9 collected, 9 passed**;
- canonical schema validation: **163 collected, 163 passed**;
- runner reference-validation tests: **7 collected, 7 passed**;
- Rust `runtime_disposable`, `runtime_fiber`, `runtime_scope`: **42 passed, 0 failed**;
- exact semantic scenario inventory: **9**.

The canonical runner remains thin. Rust can reuse its existing `ScopedRegistry`, `ScopeHandle`,
`EffectStore`, and ordered registration vector. No Runtime redesign, second scope tree, Python
dependency, provider subsystem, or Layer-06 execution behavior is required.

## 5. Verdict

```text
Layer-05 shared contract
    REJECTED

remaining blocker
    L05-R005

Python Layer 05
    certification affected pending public-boundary repair

Rust Layer 05
    NOT_IMPLEMENTED

Rust current certified position
    Layer 04

Rust implementation modified
    NO

Layer 06
    NOT STARTED
```

Return only `L05-R005` to the shared/Python owner. Do not reopen the other five findings and do not
begin Rust Layer-05 implementation.
