# Layer 05 (Tool Model + Registry) — Rust Implementation-Owner Review Package

**Prepared:** 2026-08-25
**Prepared by:** Claude (Python/shared-contract owner, per the adopted workflow)
**Why this exists:** Layer 05 (per `process/implementation-conformance-workflow.md` §6's
dependency-aware assurance order — **Tool model + registry**, not the master's own "Phase 5,"
which is Real Providers/assurance Layer 11; see `LAY-F001` if this terminology is unfamiliar) is
the next assurance layer after certified Layer 04. This package requests Rust's independent
implementation-owner review of the Python/shared candidate before any Rust implementation begins.

**Reviewed commits (delta candidate):**

```text
minion-agent        <PYTHON_CANDIDATE_SHA>   src/minion_agent/llm/tools.py (ConstrainedSampling
                     types, ToolSchema.constrained_sampling), src/minion_agent/tools/definition.py
                     (label/prepare_arguments/constrained_sampling fields, mode default fix,
                     parameters type widened), src/minion_agent/tools/registry.py (register_tool
                     type/docstring fix), src/minion_agent/tools/execute.py (one-line dict-
                     parameters compatibility fix), conformance/schema/tool-registry-scenario.
                     schema.json (new), conformance/agent/tool-registry-*.yaml (8 new scenarios),
                     tests/conformance/tool_registry_runner.py (new),
                     tests/conformance/test_tool_registry_conformance.py (new),
                     tests/conformance/test_schema_validation.py (discriminator wiring),
                     tests/conformance/test_agent_conformance.py (exclusion wiring),
                     tests/typing/valid_tool_construction.py (new), pi-parity-manifest.yaml
                     (TOOL-008 corrected, TOOL-009..TOOL-014 added), 17 existing test call sites
                     updated for the new required `label` field
minion-agent-docs   <DOCS_CANDIDATE_SHA>      spec/tools.md (Layer 05/06 split, full Layer-05
                     section added), assurance/layers/05-tool-model-registry.md (this pass's full
                     audit record), this handoff, pi-parity-manifest.yaml changes recorded above
                     live in the minion-agent repo, not here
```

**Pinned Pi revision:** `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged).

**Do not modify Rust in response to this package without first recording a verdict.**

---

## 1. Scope

**In scope for this review:** the tool definition field contract (`name`/`description`/
`parameters`/`constrained_sampling`/`label`/`prepare_arguments`-shape/`execute`-shape/
`execution_mode`), `ctx.tools` registry authority, scoped visibility/ordering, same-name
shadowing across scopes, same-scope duplicate-name resolution, registration lifecycle
(effect-owned, plugin/scope disposal withdraws), and model-facing schema projection.

**Explicitly out of scope** (do not review as if these were being certified):

```text
prepare_arguments's actual invocation timing/ordering        -- Layer 06
execute's actual invocation (validation, hooks, error
  conversion, tool_call_id/signal wiring)                     -- Layer 06 / Layer 09
AgentToolResult partial-result/usage/added_tool_names/
  terminate handling                                          -- Layer 06
Batch execution: contagion, ordering, terminate fold,
  length-stop safety (TOOL-001..TOOL-007, pre-existing,
  NOT touched or re-certified by this pass)                   -- Layer 06
Provider-specific constrained-sampling enforcement/fallback,
  concrete tool-call-ID normalization, wire encoding           -- Real Providers, assurance Layer 11
Built-in tools (bash/read/write/edit/glob/grep)                -- assurance Layer 13
Approval/sandbox policy                                        -- plugin territory, never generic
                                                                   registry semantics
Real cancellation propagation (no signal type exists in the
  codebase yet at either language)                              -- assurance Layer 09
```

---

## 2. What changed — full detail in `assurance/layers/05-tool-model-registry.md`

Ten findings (`TOOL-F001`..`TOOL-F006`, `TOOL-F008`..`TOOL-F010`; `TOOL-F007` never assigned — a
design note, not a defect), all `RESOLVED` for Python/shared scope, three explicitly **not**
implemented and recorded as Layer-06/09 closure obligations (`TOOL-F002`, `TOOL-F003`). Full
Pi source citations (exact lines, exact quotes) are in the assurance document §3 — this package
does not repeat them; verify against the pinned source directly, not against this summary.

---

## 3. Rust's required independent verdict, per question — do not trust Python's classification

1. **Does pinned Pi `Tool` contain every field claimed by the shared contract?** Re-read
   `packages/ai/src/types.ts` lines ~493–519 directly at the pinned commit. Confirm
   `constrainedSampling?: false | ConstrainedSamplingConfig` is genuinely optional (three states:
   absent/false/config), and that `ConstrainedSamplingConfig`'s two variants
   (`json_schema{strict}`/`grammar{variants}`) are exactly as this package states — not assumed
   from Python's own type names.

2. **Does pinned Pi `AgentTool` contain every claimed definition field?** Re-read
   `packages/agent/src/types.ts` lines ~361–419 directly. Specifically confirm: `label: string` has
   no `?` (required); `execute`'s real parameter list is
   `(toolCallId, params, signal?, onUpdate?)`; `executionMode?` is genuinely optional and distinct
   from a separate run-level `toolExecution?` default elsewhere in the same file (confirm that
   second field's existence and default independently — do not take this package's word for it).

3. **Are execution behaviors correctly deferred to Layer 06?** Confirm that `prepare_arguments`'s
   invocation, `execute`'s actual invocation (including `tool_call_id`/`signal` wiring), and
   `AgentToolResult` handling are genuinely absent from this package's Python implementation (not
   silently implemented and mislabeled as "field only"). Grep `tools/execute.py` directly.

4. **Does Minion's `ctx.tools` registry preserve frozen architecture?** Confirm directly against
   pinned Pi that `AgentState.tools`/`AgentContext.tools` really is a plain array property with no
   registry/scoping concept — i.e., that everything this package calls "Minion architecture, not
   Pi-derived" (registry authority, scoped visibility order, same-name shadowing, same-scope
   duplicate-name resolution, lifecycle) is correctly attributed, not silently citing a Pi symbol
   for behavior Pi does not have.

5. **Are scope/shadowing/disposal semantics coherent with certified Runtime?** Confirm the
   registry reuses the certified `ScopedRegistry`/`Context.effect`/`Scope` seam unmodified (no
   parallel visibility/shadowing algorithm invented inside the tools package). Independently
   evaluate whether Rust's own eventual registry implementation can and should reuse Rust's
   equivalent certified Runtime scope seam the same way, or whether an idiomatic Rust
   implementation has a structurally different but equally correct approach — this package does
   not presume Rust's own architecture.

6. **Does canonical evidence test real registry behavior?** Read
   `tests/conformance/tool_registry_runner.py` directly. Confirm it contains no
   visibility/shadowing/ordering/withdrawal logic of its own — every observable outcome must come
   from calling the real `ToolRegistry`/`Context`/`Scope` API, never computed by the runner.
   Confirm the 8 canonical scenarios' `expect` blocks were derived from actual runner output
   (verifiable by running them), not hand-computed assumptions.

7. **Does Python match the shared contract?** Run the Python gates yourself rather than trusting
   the reported numbers (§4 below has exact commands).

8. **Can Rust implement the contract idiomatically without Python-shaped artifacts?** Specifically
   assess: can Rust's own idiomatic tool-registry design (whatever shape that takes) express
   "nearest-scope-first, same-name shadowing, same-scope earliest-wins, effect-owned lifecycle"
   without needing to mirror Python's specific `ScopedRegistry`/dataclass mechanics? The canonical
   fixture data (§5) is designed to be constructible from any language — confirm this is actually
   true by inspecting the schema and scenario files directly, not assumed from this package's own
   claim.

---

## 4. Fresh Python evidence to reproduce, not merely trust

```text
full pytest (coverage enabled):     845 passed, 29 xfailed, 0 failed, 100.00% coverage
ruff check .:                        All checks passed
mypy (configured scope):             Success, no issues found in 57 source files
mypy + typing fixtures
  (tests/typing/valid_message_construction.py, tests/typing/valid_tool_construction.py):
                                      Success, no issues found in 59 source files
schema validation:                   147 passed
tool-registry canonical:             8 discovered / 8 executed / 8 passed / 0 deferred
Runtime canonical (regression):      26 passed (unchanged)
Session canonical (regression):      20/20 passed (unchanged, certified count preserved)
XFORM canonical (regression):        14/14 passed (unchanged, certified count preserved)
```

Reproduce via (from `minion-agent-python/`): `uv run pytest`, `uv run ruff check .`,
`uv run mypy src/minion_agent`, `uv run mypy src/minion_agent tests/typing/valid_message_
construction.py tests/typing/valid_tool_construction.py`.

---

## 5. Canonical evidence design, for Rust's own future implementation

`conformance/schema/tool-registry-scenario.schema.json` defines a `tool_registry` scenario shape:
named plugins declaring a scope (optional) and the tools they register (name/description/label/
parameters-as-raw-JSON-Schema/constrained_sampling), a step sequence (`mount`/`unmount`/`withdraw`/
`dispose_scope`), and named queries (optionally with `resolve` checks) evaluated once at the end
against the real registry. Every field is language-neutral — no Python/Pydantic concept appears
anywhere in the 8 scenario files; confirm this directly by reading them.

---

## 6. Explicitly out of scope for this package

- `TOOL-001`..`TOOL-007` (Layer-06, pre-existing, unaudited by this pass) — not reopened, not part
  of this review.
- Layer 06, Layer 09 (cancellation), Layer 11 (Real Providers) — not started, not part of this
  review's verdict.
- `LAY-F001` terminology reconciliation — already closed, not reopened.

## 7. Expected outcome

```text
LAYER 05 SHARED CONTRACT
    APPROVED
```

or a precise rejection naming exactly which field, rule, or boundary is not language-neutral or not
Pi-compatible. If approved, Rust's own implementation-timing adjudication (required now vs.
explicitly deferred) follows, per the same review-before-remediation workflow used at every prior
layer this session — this package does not presume that answer.
