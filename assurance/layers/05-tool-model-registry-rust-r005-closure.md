# Layer 05 Tool Model + Registry — Rust L05-R005 Closure Review

**Review date:** 2026-08-26

**Implementation candidate:** `minion-agent@89865c05933f4e6081da4ef776e34464a8c5a523`

**Documentation candidate:** `minion-agent-docs@2a4a3c71ebe7ab45e5ba6efb806b12911154432b`

**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`

**Previous final Rust review:** `12787ab70cef69d96e9fbcb503a0733a9a1b1465`

**Verdict:** **APPROVED FOR RUST IMPLEMENTATION**. `L05-R005` is resolved and the five
previously resolved Layer-05 findings remain closed.

This was a review-only pass. No Rust, Python, shared specification, canonical, or manifest file was
changed. The unrelated Phase-5 working-tree modification was preserved untouched and unstaged.

## 1. L05-R005 closure

Pinned Pi declares `Tool<TParameters extends TSchema = TSchema>` with required
`parameters: TParameters`; it does not narrow the generic to `TObject` or require a top-level
`"type": "object"` keyword.

The current shared rule and TOOL-016 now distinguish the schema value's representation from the
kind of JSON instance described by that schema:

- `parameters` is required and represented by a JSON mapping/object;
- the mapping may describe any supported Pi `TSchema`, including `{"type":"string"}` and a
  top-level `oneOf`;
- missing, null, booleans, arrays, strings, and numbers are outside this Layer-05 boundary;
- `{"type":"object","properties":{}}` remains the explicit empty/no-argument schema.

Python's `ToolDefinition.__post_init__` now accepts any `dict` (or supported Pydantic model class)
and contains no top-level type discriminator. `ToolDefinition.schema()` publishes raw mappings
unchanged. Direct probes accepted and preserved the empty-object, string-instance, top-level
combinator, and arbitrary-member examples; they rejected omission, `None`, both booleans, an
array, a string, and a number.

The canonical schema requires `parameters` with JSON type `object`. Its focused matrix accepts the
string-instance and top-level-combinator schema objects and rejects missing, null, and boolean
containers. Static typing fixtures admit both non-object-instance examples. Spec, TOOL-016,
canonical evidence, Python public behavior, and the future Rust boundary therefore agree.

## 2. Finding closure

| Finding | Verdict | Reason |
|---|---|---|
| `L05-R001` | **RESOLVED** | Closed Pi grammar-key domain and empty variants remain unchanged. |
| `L05-R002` | **RESOLVED** | Disposed requesting scope still observes no tools under TOOL-015. |
| `L05-R003` | **RESOLVED** | Scope-owned registration lifetime and plugin-unmount survival remain unchanged. |
| `L05-R004` | **RESOLVED** | Whole-document reference validation still precedes Runtime construction. |
| `L05-R005` | **RESOLVED** | Public Python and canonical boundaries now accept every object-valued schema without requiring `type: object`. |
| `L05-R006` | **RESOLVED** | Explicit constrained-sampling null remains invalid on semantic input. |

## 3. Verification evidence

- Exact Python construction probes: all four positive and seven negative cases behaved as required.
- Focused tool-definition, schema-validation, registry canonical, and harness-validation tests:
  all passed.
- Layer-05 canonical registry scenarios: `9/9` passed through the real seam.
- Canonical harness validation: `7/7` passed, including unknown-parent and unknown-query rejection.
- Mypy over `src/minion_agent` plus `valid_tool_construction.py`: success across 58 source files.
- The canonical runner remains an adapter/validator and contains no registry semantics.

## 4. Rust feasibility and layer boundary

Rust can represent `parameters` as an owned JSON object boundary while keeping the enclosing tool
model typed. No Python source knowledge, Runtime redesign, second scope tree, or Layer-06 behavior
is required. Layer 06 can later consume the preserved schema for validation/execution without
redesigning Layer 05.

No active `PI_PARITY_DEFECT`, `CONTRACT_ASSURANCE_DEFECT`, `PI_BEHAVIOR_UNCERTAIN`, blocking
`PARITY_CONSTRAINED_RISK`, or requested `PARITY_NEUTRAL_HARDENING` remains.

## 5. Status

```text
Layer-05 shared contract
    APPROVED FOR RUST IMPLEMENTATION

Python Layer 05
    CERTIFIED

Rust Layer 05
    NOT_IMPLEMENTED

Rust current certified position
    Layer 04

Layer 06
    NOT STARTED
```

The next action is a separate Rust Layer-05 implementation, conformance, and assurance pass.
