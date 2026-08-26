# Tool Model + Registry — Fidelity Assurance & Certification

**Layer ID:** `05` (per `process/implementation-conformance-workflow.md` §6's dependency-aware
assurance order — **not** the master design's own "Phase 5," which is Real Providers, assurance
Layer 11; see `LAY-F001`). Master designation for this layer's own content: **Phase 4 — Tools**
(the master does not split registry from execution; assurance does, per §6 items 5/6).
**Status:** `IN_AUDIT` → first candidate self-certified 2026-08-25, independently **REJECTED**
(`L05-R001`..`L05-R005`, §19) → first remediation → independently **REJECTED again**
(`L05-R001`, `L05-R002`, `L05-R004`, `L05-R005` remained open, new `L05-R006` found; `L05-R003`
confirmed **RESOLVED**, §20) → second remediation, this pass → repaired candidate
**READY FOR FRESH RUST RE-REVIEW**. This document preserves that full history rather than being
rewritten as though earlier candidates never existed; §§1–18 are the original, now-superseded
self-certification record; §19 is the first remediation, also now superseded on the five points
§20 revisits — read both as history, not current verdict. §20 is the current state.
**Audit date:** 2026-08-25 (original); first remediation 2026-08-26; second remediation 2026-08-26.
**Auditor:** Claude (Python-driven, per adopted workflow).
**Python status:** `CERTIFIED` (post-second-remediation, this pass) — real `ToolRegistry`/`Context`/
scope/effect integration, 9/9 canonical scenarios green (unchanged from the first remediation --
this round is a contract-consistency/evidence-integrity repair, not a new behavioral scenario),
163 schema-validation cases (148 + 15 new domain-boundary probes this round), full Pi audit
re-verified, all six Rust-review findings resolved (`L05-R001`, `L05-R002`, `L05-R004`, `L05-R005`,
`L05-R006` repaired this round; `L05-R003` unchanged, still resolved).
**Rust status:** `NOT_IMPLEMENTED` — Rust has no `tools/` module at the frozen baseline; currently
sits at Layer 04 (certified). One-layer lag, process-conforming
(`process/implementation-conformance-workflow.md` §§5.9, 7, 7.3). **Rust modified: NO.**

---

## 1. Scope

### Owns (Layer 05)

- **Tool definition fields** mirroring pinned Pi's `Tool`/`AgentTool`: `name`, `description`,
  `parameters`, `constrained_sampling?`, `label` (required), `prepare_arguments?` (field/signature
  only), `execute` (field/signature only — capability shape, not invocation), `execution_mode?`
  (field/signature only — metadata, not contagion behavior).
- **`ctx.tools` registry ownership/authority**: single-source-of-truth for executable tools and
  their model-facing schemas (intentional Minion architecture, `MINION`-flavored divergence — Pi
  has no registry concept at all).
- **Registration lifecycle**: registration as a reversible effect, real Runtime scope/fiber
  integration, withdrawal, plugin-unload/scope-disposal withdrawal.
- **Scoped visibility and composition**: nearest-scope-first order, same-name shadowing across
  scopes, same-scope duplicate-name resolution, `resolve()`'s unknown-name semantics.
- **Model-facing schema projection**: `ToolDefinition -> ToolSchema`, preserving every Pi-visible
  field including constrained-sampling metadata, for every tool visible from a given scope.

### Explicitly does not own (Layer 06 and beyond)

- `prepare_arguments`'s actual invocation timing/ordering in the pipeline.
- `execute`'s actual invocation: `tool_call_id`/cancellation-`signal` wiring, argument validation,
  before/after hooks, error-to-result conversion.
- `AgentToolResult`'s partial-result/usage/`added_tool_names`/`terminate` handling.
- Batch execution: sequential contagion, completion-order vs. source-order, terminate fold,
  `length`-stop tool safety (`TOOL-001`..`TOOL-007`, already-existing manifest rows, **not
  re-certified by this pass** — they remain Layer-06-owned, unaudited by this document).
- Concrete provider-specific tool-call-ID normalization, constrained-sampling enforcement/fallback,
  and any provider wire encoding (Real Providers, assurance Layer 11).
- Built-in tools (`bash`/`read`/`write`/`edit`/`glob`/`grep`, assurance Layer 13) and
  approval/sandbox policy (explicitly plugin territory, never generic-registry semantics).
- Cancellation propagation (`signal` actually carrying a real run-scoped abort — assurance Layer 09;
  no such signal type exists anywhere in the codebase yet, confirmed by direct search during the
  earlier Layer-05-labeled-as-Real-Providers reconnaissance pass, carried forward as a known,
  still-open architecture gap this layer's `execute` capability-shape fix (`TOOL-F003`) explicitly
  does not close).

### Depends on

- Layer 01 (Runtime) — certified. `ctx.tools`'s registration/visibility/disposal is a direct,
  unmodified consumer of the certified `ScopedRegistry`/`Context.effect`/`Scope` seam; this pass's
  own integration testing is the first real end-to-end exercise of `register_tool()` through a
  mounted plugin and a real scope, and it surfaced one real Layer-05-owned typing gap (`TOOL-F006`)
  without finding any Layer-01 defect (§13).
- Layer 02 (LLM vocabulary) — certified. `ToolSchema` lives in `llm/tools.py`, the same
  provider-neutral vocabulary module Layer 02 owns; this pass extends it (`constrained_sampling`)
  without finding any Layer-02 contradiction (§14).

### Depended on by

- Layer 06 (Tool execution pipeline) — consumes `ToolDefinition`/`ToolRegistry` directly; this
  layer's own contract-quality question (§16) is whether Layer 06 can build correct
  `prepare_arguments`/`execute`/cancellation behavior on top of the public shape frozen here
  without a further breaking redesign.
- Layer 09 (Cancellation) — `execute`'s capability shape now has a `signal` slot ready for a real
  cancellation type once Layer 09 defines one; this layer does not itself define that type.
- Layer 11 (Real Providers) — consumes `ToolSchema`/`constrained_sampling` for wire encoding.

---

## 2. Normative sources

- **Frozen master:** `2026-08-20-minion-agent-design.md` §7 "Tools (`ctx.tools`)" (registration as
  effect, `ctx.tools` authority, the tool contract's own field list, built-in tools, approval as a
  plugin), §6 "Tool selection and constrained sampling" (the `constrained_sampling` shape,
  "adapters may fall back... plugin registry remains authoritative"), §9 build order (Phase 4
  "Tools" — registry and execution pipeline are one master phase, split by assurance §6 into
  Layers 05/06).
- **Spec:** `spec/tools.md` — previously entirely Layer-06 content plus one unverifiable sentence
  ("Tool definitions preserve constrained-sampling metadata where implemented"); rewritten this
  pass with an explicit Layer-05 section, preserving the Layer-06 content unchanged below an
  explicit "not certified by Layer 05" boundary.
- **`/pi-parity-manifest.yaml`:** `TOOL-001`..`TOOL-007` (all Layer-06-owned, execution pipeline,
  unaudited by this pass), `TOOL-008` (constrained sampling — found citing a dangling test
  reference to a scenario that was never created, corrected this pass). New rows `TOOL-009`..
  `TOOL-014` added this pass for the Layer-05 surfaces (§9).
- **Canonical conformance:** none existed for Layer 05 before this pass — `conformance/agent/`'s
  existing tool-related placeholders (`tool-batch-*`, `prepare-arguments-failure-becomes-tool-
  error`, etc.) are all Layer-06-owned, still `TO_BE_FILLED`, untouched. 8 new scenarios added this
  pass under a new discriminator (`tool_registry`) and schema (§10).
- **Pinned Pi source** (`ref-repos/pi`, commit `b7bb00b936dbe21b8e160b3e89efdec361846699`,
  unchanged): `packages/ai/src/types.ts` (`Tool`, `ConstrainedSamplingConfig`, `GrammarFormat`,
  `GrammarVariants`), `packages/agent/src/types.ts` (`AgentTool`, `ToolExecutionMode`,
  `AgentToolResult`, `AgentToolUpdateCallback`, `AgentState.tools`, `AgentContext.tools`). Read in
  full (the relevant sections); every field cited below traces to an exact read line, not
  inference (§3).

---

## 3. Pi behavior summary

Read directly at the pinned commit, not assumed from the master's own paraphrase (which itself
turned out to have a real gap — see `TOOL-F001`):

**`packages/ai/src/types.ts` lines 493–519:**

```ts
export type GrammarFormat = "openai_lark" | "openai_regex";
export type GrammarVariants = Partial<Record<GrammarFormat, string>>;

export type ConstrainedSamplingConfig =
    | { type: "json_schema"; strict: "prefer" | "require" }
    | { type: "grammar"; variants: GrammarVariants };

export interface Tool<TParameters extends TSchema = TSchema> {
    name: string;
    description: string;
    parameters: TParameters;
    constrainedSampling?: false | ConstrainedSamplingConfig;
}
```

`constrainedSampling` is genuinely optional (`?`) — three states, not two: absent, `false`, or a
config variant. `GrammarFormat`'s known values today are OpenAI-specific; the `variants` map's own
keys are an open string set, not a closed enum (matches this project's `api`/`provider` rule
elsewhere).

**`packages/agent/src/types.ts` lines 42, 260–268, 333–343, 361–419:**

```ts
export type ToolExecutionMode = "sequential" | "parallel";

export interface AgentToolResult<T> {
    content: (TextContent | ImageContent)[];
    details: T;
    usage?: Usage;
    addedToolNames?: string[];
    terminate?: boolean;
}

export type AgentToolUpdateCallback<T = any> = (partialResult: AgentToolResult<T>) => void;

export interface AgentTool<TParameters extends TSchema = TSchema, TDetails = any>
    extends Tool<TParameters> {
    label: string;                                        // REQUIRED -- no `?`
    prepareArguments?: (args: unknown) => Static<TParameters>;
    execute: (
        toolCallId: string,
        params: Static<TParameters>,
        signal?: AbortSignal,
        onUpdate?: AgentToolUpdateCallback<TDetails>,
    ) => Promise<AgentToolResult<TDetails>>;
    executionMode?: ToolExecutionMode;
}

export interface AgentState {
    ...
    set tools(tools: AgentTool<any>[]);
    get tools(): AgentTool<any>[];
    ...
}
```

Confirmed directly, not inferred:

1. **`label` is required**, not optional. The frozen master's own §7 field list (`name`,
   `description`, `parameters`, `constrained_sampling?`, `prepare_arguments?`, `execution_mode?`,
   `execute(..., signal, on_update)`) never mentions `label` at all — a real gap in the master's own
   paraphrase, not merely a Python implementation gap (`TOOL-F001`).
2. **`execute`'s real signature carries `toolCallId` and `signal?: AbortSignal`** as its first and
   third parameters. The master's own field list (`execute(..., signal, on_update)`) does gesture at
   a `signal` parameter (unlike `label`), but current Python (`ToolFn = Callable[..., ...]`) had no
   parameter slots for either `toolCallId` or `signal` at all before this pass, and today's
   dispatch (`execute.py`) still doesn't invoke either (`TOOL-F003`).
3. **`executionMode` default is a run-level setting, not a per-tool one.** A separate, later-read
   section of `packages/agent/src/types.ts` (an `AgentOptions`-like interface, `toolExecution?:
   ToolExecutionMode`, default `"parallel"`) governs the *run's* default; `AgentTool.executionMode?`
   is a *per-tool override* of that default. A tool that doesn't set it should defer to whatever the
   run's own default is — not be indistinguishable from a tool that explicitly requested `"parallel"`
   (`TOOL-F004`).
4. **`AgentState.tools` is a plain mutable array property** (`set`/`get tools(): AgentTool<any>[]`)
   with no scoping, ownership, or shadowing concept whatsoever — "Assigning a new array copies the
   top-level array" is the entire lifecycle story. This directly confirms the registry/scoping/
   shadowing/withdrawal rules this layer certifies are **100% Minion architecture**, not
   Pi-derived — matching frozen master §7's own framing, now independently verified against Pi
   source rather than assumed (§9's manifest rows disposition accordingly).
5. **`AgentToolResult`/`AgentToolUpdateCallback`** confirm the `execute` return shape and the
   partial-update callback's own shape, read only far enough to type `execute`'s target signature
   coherently — their actual runtime semantics (usage handling, `terminate` fold, etc.) are
   Layer-06 territory and not audited further here, per the originating instruction's own explicit
   boundary.

No `PI_BEHAVIOR_UNCERTAIN` findings — every claim above traces to an exact read line at the pinned
commit.

---

## 4. Shared-contract repair (`spec/tools.md`)

Previously: entirely Layer-06 pipeline content, plus one sentence ("Tool definitions preserve
constrained-sampling metadata where implemented") that could not be verified true or false, since
no field existed anywhere to preserve.

Rewritten this pass (full text: `spec/tools.md`) with an explicit two-layer structure: a new Layer
05 section (tool definition fields, registry ownership/visibility/shadowing/lifecycle, explicitly
listing what remains uncertified) placed above the preserved, unmodified Layer-06 pipeline content,
now itself explicitly labeled `NOT CERTIFIED BY LAYER 05` with a pointer to the still-open
Layer-06 audit obligation.

---

## 5. Requirement traceability

| Requirement | Source | Python implementation | Canonical/direct evidence | Status |
|---|---|---|---|---|
| Tool field completeness (`name`/`description`/`parameters`/`constrained_sampling`/`label`/`prepare_arguments`/`execute`-shape/`execution_mode`) | `types.ts::Tool`/`AgentTool` | `tools/definition.py::ToolDefinition`, `llm/tools.py::ToolSchema` | `tests/typing/valid_tool_construction.py`, `tool-registry-schema-projection` | `PASS` |
| `ctx.tools` sole authority | design §7 | `tools/registry.py::ToolRegistry`, `tools/plugin.py::tools_plugin` | `tool-registry-scope-visibility` | `PASS` |
| Scoped visibility, normative order | design §3 (Runtime), applied to tools | `ToolRegistry.visible_from` via `ScopedRegistry` | `tool-registry-scope-visibility` | `PASS` |
| Same-name shadowing + withdrawal fallback | design §7 | `ToolRegistry.visible_from`'s `setdefault` composition | `tool-registry-nearer-shadows-farther`, `tool-registry-withdrawal-restores-farther` | `PASS` |
| Same-scope duplicate-name rule (`TOOL-F009`) | Minion architecture, previously undefined | `ScopedRegistry` insertion order + first-match composition | `tool-registry-same-scope-duplicate-name` | `PASS` |
| `resolve()` unknown-name semantics | design §7 (implied) | `ToolRegistry.resolve` | `tool-registry-resolve-unknown-is-absent` | `PASS` |
| Registration lifecycle (effect-owned, plugin/scope disposal withdraws) | design §3/§7 | `register_tool`, real `ctx.effect`/`Scope.dispose` | `tool-registry-plugin-disposal-withdraws`, `tool-registry-scope-disposal-withdraws` | `PASS` |
| Model-facing schema projection, all fields | `types.ts::Tool` | `ToolDefinition.schema()` | `tool-registry-schema-projection` | `PASS` |

---

## 6. Existing Python implementation audit

**`llm/tools.py::ToolSchema`** — before this pass: `name`/`description`/`parameters` only, no
`constrained_sampling` field at all — a silent field omission (`TOOL-F005`, `PI_PARITY_DEFECT` +
`CONTRACT_ASSURANCE_DEFECT`, not merely "deferred": nothing in prior assurance history recorded
this as an approved divergence). **Fixed** this pass: `ConstrainedSampling`/
`JsonSchemaConstrainedSampling`/`GrammarConstrainedSampling` added, `ToolSchema.constrained_sampling:
ConstrainedSampling | Literal[False] | None = None`, `as_json()` extended with the project's
established null-for-absent convention (not key omission).

**`tools/definition.py::ToolDefinition`** — before this pass: `name`/`description`/`parameters`/
`execute`/`mode` only. **Fixed** this pass: `label: str` added (required, `TOOL-F001`);
`constrained_sampling`/`prepare_arguments` added (optional, `TOOL-F002`/`TOOL-F005`); `mode`'s
default changed from a concrete `ExecutionMode.PARALLEL` to `None` (`TOOL-F004`); `parameters`'s
type widened from `type[BaseModel] | None` to `type[BaseModel] | dict[str, Any] | None` so a real
JSON Schema value — the actual model-facing contract — is directly constructible without inventing
a dynamic Pydantic model, which canonical/cross-language evidence genuinely needs (`TOOL-F010`);
`ToolFn`'s docstring corrected to state the full target capability shape and the real gap against
it (`TOOL-F003`, not implemented, Layer-06/09 territory).

**`tools/registry.py::ToolRegistry`/`register_tool`** — audited via direct real integration
testing (§13), not read-only inspection: visibility/shadowing/composition logic was already
correct (reuses the certified `ScopedRegistry` unmodified, `setdefault`-based nearest-first-wins
composition already matches the frozen shadowing rule exactly). One real gap found and fixed:
`register_tool()`'s own return-type annotation (`Callable[[], Any]`) did not communicate that the
withdrawal handle must be awaited — real integration testing (mounting a real plugin, registering
through a real scope, calling the handle synchronously) silently failed to withdraw, confirmed to
be `ctx.effect()`'s own consistent, correct, by-design async-handle behavior (both
`Fiber.effect`/`_scoped_effect` return `Callable[[], Awaitable[None]]`) — not a Runtime defect
(`TOOL-F006`, fixed by tightening `register_tool()`'s own type/docstring, no Runtime change).

**`tools/execute.py`/`tools/batch.py`** — inspected only for the Layer-05/Layer-06 boundary
(§7); their own Pi-parity is **not** audited or certified by this pass. One tiny structural
compatibility fix was required and made: `_validate()`'s `None`-parameters branch extended to also
cover the new `dict`-parameters case (both skip Python-side Pydantic validation identically) — a
one-line `isinstance` addition, not a pipeline redesign, required because the widened
`ToolDefinition.parameters` type would otherwise crash real execution for a `dict`-parameters tool.
`batch.py::_is_sequential`'s `definition.mode is ExecutionMode.SEQUENTIAL` check was re-verified
directly to already be `None`-safe (an `is` comparison against a specific enum member) — no change
needed, confirming `TOOL-F004`'s fix is fully backward-compatible with existing Layer-06 code.

**Existing tool tests** — all 17 pre-existing `ToolDefinition(...)` construction call sites across
12 test files updated to supply the new required `label` field; one existing test
(`test_a_definition_defaults_to_parallel`) asserted the exact behavior `TOOL-F004` corrected and was
rewritten (`test_a_definition_defaults_to_no_per_tool_mode_override`) to assert the corrected
contract, not deleted — its original intent (a per-tool `SEQUENTIAL` override still works) is
preserved by its still-passing sibling test.

---

## 7. Layer 05 / Layer 06 boundary review

Every change this pass was scoped to structural compatibility, never Layer-06 behavior:

```text
prepareArguments ordering                  UNCHANGED (field only, never invoked by this pass)
schema-validation failure conversion       UNCHANGED (one isinstance-widening line, same behavior
                                             for None and dict parameters -- both skip validation)
before/after hooks                         UNCHANGED
parallel/sequential contagion              UNCHANGED (`is ExecutionMode.SEQUENTIAL` still correct
                                             for the new None default)
update delivery                            UNCHANGED
terminate semantics                        UNCHANGED
execution events                           UNCHANGED
ToolResult construction                    UNCHANGED
```

`execute.py`/`batch.py` were touched in exactly one line each, both purely additive
compatibility fixes required for the new `ToolDefinition` shape to "compile/run" at all (per the
originating instruction's own explicit exception), not behavioral changes. No canonical XFORM/
Session/Runtime scenario was touched. Full regression confirmed green (§12).

---

## 8. Registry lifecycle correctness (direct integration evidence)

Proven through the real seam, not `registry._entries` mutation, via a direct empirical probe before
any canonical scenario was written, then via the 8 canonical scenarios themselves:

```text
register -> visible immediately under normal effect semantics       PASS
withdraw (awaited handle) -> no longer visible                       PASS
plugin/fiber unload -> no longer visible                             PASS (tool-registry-plugin-
                                                                        disposal-withdraws)
scope disposal -> its own registrations withdrawn                    PASS (tool-registry-scope-
                                                                        disposal-withdraws)
ancestor survives child disposal                                     PASS
sibling survives sibling disposal                                    PASS
shadowed ancestor becomes visible when nearer registration withdraws PASS (tool-registry-
                                                                        withdrawal-restores-farther)
```

---

## 9. Parity manifest audit

`TOOL-001`..`TOOL-007` (all Layer-06, execution pipeline) — inspected only to confirm they remain
correctly out of this pass's scope; not re-verified, not re-certified, unchanged.

`TOOL-008` (constrained sampling) — found citing `tool-constrained-sampling-schema`, a scenario
name that was never actually created (a dangling reference, `CONTRACT_ASSURANCE_DEFECT`).
Corrected: rule text tightened to the exact three-state shape, `tests:` pointed at the real new
canonical scenario and direct unit tests, `python:` pointed at both real implementation locations.

`TOOL-009`..`TOOL-014` (new) — one row per Layer-05 surface (§5's table), each with an explicit
`pi:` field distinguishing Pi-derived rows (`TOOL-009`, citing `agent/types.ts::AgentTool`) from
Minion-architecture rows (`TOOL-010`..`TOOL-014`, `pi: N/A`, `disposition: intentional divergence`)
— per the originating instruction's explicit demand not to cite a Pi symbol as evidence for
behavior Pi does not have. Manifest re-validated: 58 rows (was 52), 0 duplicates, every row has an
explicit disposition.

---

## 10. Canonical evidence

**Family:** `agent` (no new `conformance/tools/` directory — matches the project's fixed
three-family rule). **New schema:** `conformance/schema/tool-registry-scenario.schema.json`, a
third schema for `conformance/agent/`'s own directory (alongside the unified and transform
shapes), discriminated by a top-level `tool_registry` key, wired into
`test_schema_validation.py`'s existing discriminator function and into
`test_agent_conformance.py`'s full-loop exclusion (matching the transform shape's own precedent
exactly).

**New runner:** `tests/conformance/tool_registry_runner.py` — mounts the real `tools_plugin` on a
real `Context`, builds a synthetic `PluginSpec` per scenario `plugins[]` entry whose `apply()`
registers real `ToolDefinition`s through the real `register_tool()` effect (awaiting the returned
handle correctly, per `TOOL-F006`), opens/disposes real `Scope`s, unmounts real plugin fibers, and
queries `visible_from`/`resolve`/`schemas` on the real `ToolRegistry`. Implements no visibility,
shadowing, ordering, or withdrawal logic itself.

**Scenarios (8, all passing):**

```text
tool-registry-scope-visibility                untagged/parent/child/sibling visibility + order
tool-registry-nearer-shadows-farther          cross-scope same-name shadowing
tool-registry-withdrawal-restores-farther     shadowing fallback after withdrawal
tool-registry-same-scope-duplicate-name       earliest-registered-within-scope wins (TOOL-F009)
tool-registry-resolve-unknown-is-absent       resolve() unknown name -> None, not error
tool-registry-schema-projection               full field/constrained-sampling projection (4 states)
tool-registry-plugin-disposal-withdraws       real fiber unmount withdraws
tool-registry-scope-disposal-withdraws        real scope disposal withdraws, siblings/ancestors safe
```

```text
discovered:  8
executed:    8
passed:      8
deferred:    0
```

Every expected value (including visibility order and full schema projections) was verified
against the real runner's actual output before being committed to the scenario file, not
hand-computed and assumed correct (per this project's established arithmetic-precision
discipline) — the ordering assertions in particular directly caught and corrected an initial
wrong guess (§ nearest-first vs. reverse) before any scenario was finalized.

**Existing tool-related placeholders** (`tool-batch-parallel`, `tool-batch-sequential-contagion`,
`prepare-arguments-failure-becomes-tool-error`, `schema-validation-failure-becomes-tool-error`,
`before-hook-failure-becomes-tool-error`, `execute-failure-becomes-tool-error`,
`after-hook-failure-replaces-result-with-tool-error`, `terminate-*`, `length-stop-executes-no-
tools`, `parallel-tool-completion-vs-message-order`, `pending-tool-calls-state`) — all
Layer-06-owned, all still `TO_BE_FILLED`, untouched by this pass.

---

## 11. Security review

- Tool names/descriptions/schemas are data, never evaluated as code — confirmed, no `eval`/dynamic
  code construction anywhere in `tools/definition.py`/`registry.py`.
- Registration cannot escape its owning lifecycle: proven directly (§8) via real fiber/scope
  disposal, not asserted.
- Registry lookup (`resolve`/`visible_from`/`schemas`) never invokes `execute` — confirmed by
  direct source read; the canonical runner's own synthetic `execute` callables are never called by
  any Layer-05 registry operation (only real tool *execution*, explicitly out of scope, would ever
  call them).
- No malformed-schema-generation boundary issue found: an empty/`None` `parameters` value always
  produces a valid, defined empty-object schema rather than an error or `None` output.
- No cross-scope tool-object leakage found: `ToolDefinition` instances are frozen dataclasses,
  immutable after construction (§8's lifecycle proof also confirms no scope's registry entry is
  ever mutated by another scope's operations).

---

## 12. Regression

```text
full pytest (coverage enabled):  845 passed, 29 xfailed, 0 failed, 100.00% coverage
  -- +17 vs. the prior 828: 4 new tool-registry-related unit/typing-adjacent tests already counted
     in that 828 baseline are unaffected; the +17 breaks down as 8 new canonical scenarios x 1
     parametrized case each in test_tool_registry_conformance.py (8) + 1 new schema-wellformed
     parametrized case for tool-registry-scenario.schema.json (1) + 8 new schema-validation
     parametrized cases, one per new scenario file (8) = 17, git-diff/collect-only verified, not
     estimated.
ruff check .:                     All checks passed
mypy (configured scope):          Success, no issues found in 57 source files
mypy + both typing fixtures:      Success, no issues found in 59 source files
Runtime canonical:                26 passed (unchanged)
Session canonical:                 20/20 passed (unchanged, certified count preserved)
XFORM canonical:                   14/14 passed (unchanged, certified count preserved)
schema validation:                147 passed (was 138; +9 = 8 new scenarios + 1 new schema-
                                    wellformed check)
```

No previously certified layer's canonical count changed. No Layer-01/02/03/04 semantic file was
touched.

---

## 13. Layer-01 (Runtime) regression rule — invoked, resolved without a delta audit

Real integration testing (§6/§8) found `register_tool()`'s handle must be awaited, discovered via a
direct empirical probe (a synchronous call silently failed to withdraw a scope-owned registration).
Traced to root cause before concluding anything: `Fiber.effect()`'s own type
(`Callable[[], Awaitable[None]]`) and `_scoped_effect()`'s own implementation (`async def dispose()`)
are **both correct and mutually consistent** — Runtime's own certified behavior is exactly as
designed, deliberately uniform async disposal regardless of fiber vs. scope ownership. The defect
was isolated entirely to `tools/registry.py::register_tool()`'s own imprecise type signature, fixed
within this pass. **No Layer-01 post-certification delta audit was triggered** — Runtime's
certified contract and behavior are unaffected and unchanged.

## 14. Layer-02 (LLM vocabulary) regression rule — invoked, resolved without a delta audit

Adding `constrained_sampling` to `llm/tools.py::ToolSchema` extends Layer-02-owned vocabulary. Direct
check: does this contradict anything Layer 02 already certified? No — `ToolSchema` had no
`constrained_sampling` field before (a silent omission, not a certified "this field does not
exist" claim), and no existing canonical scenario or test asserted its absence as meaningful. **No
Layer-02 post-certification delta audit was triggered** — this is a pure additive extension to
already-certified vocabulary, not a contradiction of it.

---

## 15. Findings

| ID | Category | Finding | Disposition |
|---|---|---|---|
| `TOOL-F001` | `PI_PARITY_DEFECT` + `CONTRACT_ASSURANCE_DEFECT` | `label` (pinned Pi `AgentTool.label`, required) absent from both the master's own §7 field list and `ToolDefinition` | `RESOLVED` — field added (required, no default); 17 call sites fixed; static evidence added |
| `TOOL-F002` | `CONTRACT_ASSURANCE_DEFECT` | `prepare_arguments` (pinned Pi `AgentTool.prepareArguments?`) entirely absent from `ToolDefinition` | `RESOLVED` (field/signature only) — invocation explicitly deferred to Layer 06 |
| `TOOL-F003` | `CONTRACT_ASSURANCE_DEFECT` | `execute`'s capability shape lacks `tool_call_id`/cancellation-`signal` parameter slots pinned Pi's `AgentTool.execute` has | Documented as the target shape (`ToolFn`'s docstring); **not implemented** — real dispatch still only realizes the `(params)`/`(params, on_update)` subset; Layer-06/Layer-09 (cancellation) closure obligation |
| `TOOL-F004` | `PI_PARITY_DEFECT` | `ToolDefinition.mode` defaulted to a concrete `PARALLEL`, conflating "no per-tool preference" with an explicit override | `RESOLVED` — default changed to `None`; `_is_sequential` re-verified `None`-safe; one existing test corrected, not deleted |
| `TOOL-F005` | `PI_PARITY_DEFECT` + `CONTRACT_ASSURANCE_DEFECT` | `constrained_sampling` (pinned Pi `Tool.constrainedSampling?`) entirely absent from `ToolSchema`/`ToolDefinition` | `RESOLVED` end to end — types, schema projection, canonical evidence (all 4 states) |
| `TOOL-F006` | `CONTRACT_ASSURANCE_DEFECT` | `register_tool()`'s return-type annotation did not communicate its withdrawal handle must be awaited; found via real integration testing, not Runtime defect (§13) | `RESOLVED` — type/docstring corrected |
| `TOOL-F008` | `CONTRACT_ASSURANCE_DEFECT` | Scoped tool visibility/schema-projection order was never pinned as normative anywhere | `RESOLVED` — pinned (nearest-scope-first, ancestors outward, untagged last) in spec + canonical evidence |
| `TOOL-F009` | `CONTRACT_ASSURANCE_DEFECT` | Same-scope duplicate-name registration behavior was entirely underspecified | `RESOLVED` — pinned (earliest-registered-within-scope wins, matching the real `ScopedRegistry`'s own existing behavior) + canonical evidence |
| `TOOL-F010` | `CONTRACT_ASSURANCE_DEFECT` | `ToolDefinition.parameters` could only be a Pydantic model class — no way to construct a real definition from a language-neutral JSON Schema value, which canonical/cross-language evidence genuinely needs | `RESOLVED` — type widened to also accept a raw `dict`; one-line compatibility fix in `execute.py` so `dict`-parameters tools don't crash Layer-06 dispatch |

No active `PI_PARITY_DEFECT`, `PI_BEHAVIOR_UNCERTAIN`, or `CONTRACT_ASSURANCE_DEFECT` remains for
current-layer scope. `TOOL-F007` was never assigned (a runner-thinness design note, not a
discovered defect — removed from an earlier draft rather than left as a dangling citation).

---

## 16. Contract-quality review

```text
Can Rust implement Tool/AgentTool definition semantics from the spec
  without reading Python?                                          YES -- spec/tools.md's field
                                                                      list is fully language-neutral
Can Rust implement registry scope/shadowing from canonical data
  without reproducing Python container mechanics?                  YES -- canonical fixtures use
                                                                      plain names/scopes/JSON Schema,
                                                                      no Python/Pydantic concept
Can Layer 06 later execute tools without requiring a different
  ToolDefinition public contract?                                  YES for the frozen fields;
                                                                      execute's real signature will
                                                                      still need Layer-06/09 wiring
                                                                      work, but the capability SHAPE
                                                                      is now correct and stable
Does the registry use certified Runtime scope/effect semantics
  rather than duplicating them?                                    YES -- ScopedRegistry/Context.
                                                                      effect/Scope reused unmodified
Does the model-facing Tool value preserve every Pi-visible field
  we intend to support?                                            YES -- name/description/
                                                                      parameters/constrained_sampling/
                                                                      label/prepare_arguments/execute-
                                                                      shape/execution_mode, all present
Are same-scope name collisions explicitly defined?                 YES -- TOOL-F009, pinned
Is constrained sampling represented end to end without provider
  code?                                                              YES -- TOOL-F005, no provider
                                                                      logic anywhere in Layer 05
```

All green — no `CONTRACT_ASSURANCE_DEFECT` remains open from this review.

---

## 17. Rust applicability and review status

Rust has no `tools/` module at the frozen baseline (`llm/`, `runtime/`, `session/` only) and
currently sits at Layer 04 (certified). Python reaching Layer 05 while Rust remains at Layer 04 is
a one-layer lag, explicitly process-conforming
(`process/implementation-conformance-workflow.md` §§5.9, 7, 7.3 — the same rule already
established and reused at every prior layer transition this session). No Rust code was written,
modified, or scaffolded this pass.

```text
RUST LAYER-05 IMPLEMENTATION TIMING
    NOT_IMPLEMENTED -- VALIDLY ONE LAYER BEHIND
```

See the companion handoff, `05-tool-model-registry-rust-handoff.md`, for the independent review
request.

---

## 18. Freeze gate

```text
Pi Tool/AgentTool audit complete?                    YES (§3)
Master field list gap found and corrected?           YES -- label (§3, TOOL-F001)
Layer 05/06 boundary explicit throughout?             YES (§1, §4, §7)
Tool definition contract complete?                    YES (§5, §6)
Registry authority/visibility/shadowing pinned?       YES (§5, §9)
Same-scope collision defined?                          YES (TOOL-F009)
Canonical evidence: real ToolRegistry/Context/scope?  YES (§10) -- no simulated visibility
8/8 canonical scenarios green?                         YES (§10)
Runtime regression checked, no delta needed?           YES (§13)
LLM vocabulary regression checked, no delta needed?    YES (§14)
Session/XFORM regression green (20/20, 14/14)?         YES (§12)
Full Python gates green?                                YES (§12) -- 845 passed/29 xfailed/100%
Contract-quality review all green?                     YES (§16)
Active PI_PARITY_DEFECT?                                NONE (§15)
Active PI_BEHAVIOR_UNCERTAIN?                           NONE (§15)
Active CONTRACT_ASSURANCE_DEFECT?                       NONE (§15)
Rust implementation status recorded?                    NOT_IMPLEMENTED, VALIDLY ONE LAYER BEHIND
```

All green.

```text
Layer 05 shared contract candidate    READY FOR RUST REVIEW
Python Layer 05                        CERTIFIED
Rust Layer 05                          NOT_IMPLEMENTED -- VALIDLY ONE LAYER BEHIND
```

Layer 06 (Tool execution pipeline) is **not started**. Real Providers (assurance Layer 11) remains
untouched and unstarted.

---

## 19. Rust review rejection and remediation (this pass, 2026-08-26)

The §§1–18 self-certification above was submitted for independent Rust review via
`05-tool-model-registry-rust-handoff.md` (candidate `minion-agent@d9054fe`,
`minion-agent-docs@7728d55`). Rust's independent review, recorded verbatim in
`05-tool-model-registry-rust-review.md` (candidate reviewed at
`minion-agent-docs@fc741e0e4ba162303b89732dc5704744468bb1e5`), returned:

```text
Layer-05 shared contract    REJECTED
  L05-R001   PI_PARITY_DEFECT           grammar variants modeled as an open map; pinned Pi's
                                         GrammarFormat is a closed 2-value union
  L05-R002   CONTRACT_ASSURANCE_DEFECT  disposed-scope query semantics unresolved/untested
  L05-R003   CONTRACT_ASSURANCE_DEFECT  plugin/scope dual-ownership lifetime underspecified
  L05-R004   CONTRACT_ASSURANCE_DEFECT  malformed scope references silently accepted by the runner
  L05-R005   CONTRACT_ASSURANCE_DEFECT  parameters value domain / null-absence conflation unresolved
Rust implementation modified: NO
Layer 06: NOT STARTED
```

Per the adopted workflow, a Rust rejection returns findings to the Python/shared owner for narrow
repair; Python re-certifying after repair does not itself constitute Rust approval — a fresh
independent Rust re-review of the repaired candidate is required before Rust implementation may
begin. This section records that repair; it does not claim approval.

### 19.1 Finding disposition table

```text
Finding    Root cause                              Repair                                    Evidence
L05-R001   GrammarConstrainedSampling.variants      Rewrote to two independently-optional      types.ts:493-495
           modeled as an open dict[str,str]; an     named fields (openai_lark, openai_regex),  (pinned commit,
           earlier draft's docstring falsely        matching Pi's closed GrammarFormat =       re-read directly);
           claimed this matched Pi.                 "openai_lark"|"openai_regex" union.         llm/tools.py;
                                                     as_json() omits unset keys (mirrors Pi's   test_tool_schema.py
                                                     Partial<Record<...>> semantics). Schema    (3 tests);
                                                     tightened to the same closed 2-key shape.  tool-registry-scenario
                                                                                                 .schema.json
L05-R002   ScopedRegistry.visible_from() operates   Widened ToolRegistry.visible_from/          registry.py;
           purely on an immutable ScopeKey chain,   resolve/schemas to accept ScopeKey | Scope  01-runtime.md
           with zero awareness of scope liveness    | None; when given a live Scope object,     lines 108-137
           -- structurally cannot itself enforce    check .disposed and return empty if so,     (Layer-01
           a disposed-scope rule. Layer-01's own    reusing the already-certified Scope.disposed evidence that
           certification never actually exercised   property. ScopedRegistry/ScopeTree (Layer   this was never
           this question (no real registry existed  01) untouched. Classified Outcome C         cross-verified);
           yet) -- genuinely silent/ambiguous,       (three-outcome protocol): Layer-01 silent,  tool-registry-scope-
           not an established rule either side       resolved via contract-quality judgment at  disposal-withdraws
           violated.                                 the highest layer that can express it.     .yaml (rewritten)
L05-R003   Registration lifecycle was described as   Empirically confirmed (Python REPL probe,  runtime/context.py
           "plugin unmount OR scope disposal          then real canonical scenario) that a       (effect() routing
           withdraws," an inaccurate either/or.       scoped registration survives its owning    order); tool-
           Actual certified Runtime behavior          plugin's unmount and is withdrawn only by  registry-scoped-
           (Context.effect() routes to the nearest    scope disposal/explicit withdrawal --      registration-
           enclosing scope's disposables whenever     Model 2 (scope-owned-after-registration),  survives-plugin-
           one exists, never the fiber's, regardless  matching Rust's own described              unmount.yaml (new);
           of which plugin/fiber is executing) was    architecture exactly. Adopted Model 2 as    spec/tools.md
           never made explicit in spec prose.         normative; corrected spec/tools.md and     (rewritten);
                                                       the TOOL-014 manifest row precisely;        TOOL-014 row
                                                       documented callback-lifetime-safety
                                                       guidance for tool authors (no code change
                                                       needed -- the Runtime already behaves this
                                                       way correctly by design).
L05-R004   The conformance runner's _ScopeTable        _ScopeTable.key_for() now raises           tool_registry_
           silently treated an unresolved              ValueError for an unknown scope_parent;    runner.py
           scope_parent (or query scope) name as       new require_live() raises for an unknown   (_ScopeTable);
           "no parent"/"untagged" rather than           query scope. This is runner input-        tool-registry-
           rejecting malformed canonical input --       validation (rejecting malformed scenario   scope-disposal-
           masking the fact that an earlier revision    references), explicitly distinct from      withdraws.yaml
           of tool-registry-scope-disposal-withdraws    implementing registry lookup/shadowing      (rewritten with a
           .yaml never actually proved the hierarchy    semantics (which remains entirely in the    real root-scope
           it claimed.                                  real ToolRegistry/ScopedRegistry).          plugin)
L05-R005   parameters accepted a missing/null           Object-valued JSON Schema boundary          llm/tools.py
           shorthand meaning "empty object," and        clarified in docs (never the boolean-       (docstring);
           the contract's docs overclaimed "arbitrary   shorthand forms of JSON Schema, which       tool-registry-
           JSON Schema" when Pi's TSchema is always     TypeBox's TSchema never produces).           scenario.schema
           object-shaped in practice. Conflated          Canonical parameters shorthand removed:     .json (required,
           "absent" with "empty" at the fixture          scenario schema now requires parameters     no null option);
           layer.                                       explicitly (including the empty-object       tool-registry-
                                                          case); runner reads spec["parameters"]       schema-projection
                                                          directly (no .get() fallback). Python's      .yaml + 6 other
                                                          own ToolDefinition.parameters keeps None     scenarios updated
                                                          as a legitimate host-language ergonomic
                                                          convenience -- not the same decision as
                                                          the canonical-contract boundary.
```

### 19.2 Cross-layer regression protocol outcome (`L05-R002`)

Applied the mandated three-outcome protocol: (A) lower layer already normatively defines the
behavior and the higher layer was simply wrong; (B) lower layer already normatively defines the
opposite behavior and an implementation silently deviated; (C) lower layer is silent/ambiguous.
`assurance/layers/01-runtime.md` lines 108-137 (RT-010) show the disposed-scope-query question was
never actually exercised at Layer-01 certification time, because no real registry existed yet to
expose it — this is **Outcome C**. Resolved via contract-quality judgment at Layer 05 only, reusing
the already-certified, already-public `Scope.disposed` primitive; `ScopedRegistry`/`ScopeTree`
(Layer 01) were read for confirmation but not modified.

### 19.3 Ownership-lifetime model decision (`L05-R003`)

Of the three possible models the review posed (1: intersection — active only while both plugin
mounted and scope active; 2: scope-owned-after-registration — survives plugin unmount until scope
disposal; 3: plugin-owned-storage with a scope-based visibility filter), empirical confirmation via
both a direct Python REPL probe and the new canonical scenario
(`tool-registry-scoped-registration-survives-plugin-unmount.yaml`) shows Python's actual, certified
Runtime behavior is **Model 2**, matching the Rust review's own description of Rust's architecture
(`FiberInitContext::effect` routes scoped effects to the scope's own store; fiber/plugin unmount
disposes only the fiber's own generation store). Model 2 is adopted as the normative rule because
it is what both languages' already-certified Runtimes already do, correctly, by design — not a new
Layer-05 policy invented to resolve the finding.

**Callback lifetime safety:** a `ToolDefinition`'s `execute`/`prepare_arguments` closures may
remain reachable (via the surviving registration) after their originating plugin has unmounted, for
as long as the owning scope stays active. Nothing in the current architecture ties a Python
closure's captured state to its originating plugin's own lifecycle — the closure remains callable
regardless. The actual risk is entirely on the tool author's side: a closure that captures a
resource whose *own* lifetime is scoped to the plugin's mount (rather than to the registration's
owning scope) would reference torn-down state after unmount, but the registry has no way to detect
or prevent this generically, and nothing at Layer 05 currently constructs such a closure. This is
documented as explicit tool-author guidance in `spec/tools.md` rather than a defect to fix in code,
consistent with the disposition already used for `TOOL-F002`/`TOOL-F003` (a Layer-06-adjacent
concern that Layer 05 discloses but does not itself need to enforce, since Layer 05 owns the
definition's lifetime, not its invocation).

### 19.4 Canonical scenario count

9 discovered / 9 executed / 9 passed / 0 deferred (8 original + 1 new:
`tool-registry-scoped-registration-survives-plugin-unmount`, proving the specific
survives-plugin-unmount case the review flagged as missing evidence for).

### 19.5 Contract-quality questions (re-affirmed post-remediation)

```text
Can Rust implement this without ever reading Python source?         YES -- every rule in this
                                                                       document and its schema/
                                                                       scenario files is stated in
                                                                       language-neutral terms
Can Layer 06 be implemented against this contract without
  redesigning Layer 05?                                              YES -- no Layer-05 field,
                                                                       method signature, or
                                                                       lifecycle rule changed shape
                                                                       in a way that would require
                                                                       Layer-06 rework
Does the registry still reuse certified Runtime scope/effect
  semantics unmodified, with no parallel logic invented?             YES -- ScopedRegistry/
                                                                       Context.effect/Scope.disposed
                                                                       reused directly; no Layer-01
                                                                       code changed
```

### 19.6 New candidate

```text
Layer-05 shared contract    READY FOR FRESH RUST RE-REVIEW
Python Layer 05             CERTIFIED (post-remediation)
Rust Layer 05                NOT_IMPLEMENTED
Rust modified                NO
Layer 06                     NOT STARTED
```

See the updated `05-tool-model-registry-rust-handoff.md` for the re-review request and the exact
commit delta since `fc741e0e4ba162303b89732dc5704744468bb1e5`.

---

## 20. Second Rust review rejection and remediation (this pass, 2026-08-26)

The §19 repair above was submitted for fresh independent Rust re-review (candidate
`minion-agent@816fc9f`, `minion-agent-docs@ddfe715`). That re-review, recorded verbatim in
`05-tool-model-registry-rust-rereview.md` (commits `61d42dc`, `7e288a6`), returned:

```text
Layer-05 shared contract    REJECTED

L05-R001   OPEN     grammar contract internally contradictory (stale summary/manifest prose,
                     empty-variants domain mismatch between schema and Python)
L05-R002   OPEN     disposed-scope rule works but is absent from the normative spec/manifest
L05-R003   RESOLVED scope-owned-after-registration lifetime confirmed coherent -- not reopened
L05-R004   OPEN     parent validation raises inside plugin apply(), swallowed by reconciliation,
                     surfaces only as an incidental KeyError later -- not effective at the boundary
L05-R005   OPEN     required-parameters boundary still contradicted by public ToolDefinition.parameters
L05-R006   NEW/OPEN canonical input accepts explicit `constrained_sampling: null` as an
                     undefined fifth alias for absent
```

This section records the repair of the five remaining/new findings. `L05-R003` was not reopened;
no code, spec, or manifest text describing it changed.

### 20.1 Pi re-audit for this round

Re-read `packages/ai/src/api/constrained-sampling.ts` directly (not re-read at the first pass,
which only inspected `types.ts`): `resolveGrammarConstrainedSampling` (lines 230–263) throws `"no
supported grammar variant was provided"` when both `variants.openai_lark` and
`variants.openai_regex` are absent/blank -- but only when actually resolving grammar constrained
sampling for a provider request. Pi's `GrammarVariants = Partial<Record<GrammarFormat, string>>`
type itself statically permits `{}`; nothing in `types.ts` forbids constructing a `Tool` with an
empty grammar selection. The rejection is real, but it lives in the `ai` package's provider
request-construction path, i.e. Real Providers/assurance Layer 11 territory, not the `Tool`-model
boundary Layer 05 owns. **Decision: Layer 05 accepts `variants: {}`; Layer 11 will need to enforce
"at least one variant" when it eventually resolves grammar constrained sampling for a request.**
No other Pi uncertainty remains for this round.

### 20.2 Finding disposition table

```text
Finding    Root cause                                Repair                                Evidence
L05-R001   Tool-summary prose and the TOOL-008        spec/tools.md Tool summary + prose      constrained-
           manifest row still said grammar keys       rewritten; TOOL-008 rewritten to        sampling.ts:230-
           were an open string-keyed map (stale       state the closed 2-key domain and       263 (pinned Pi,
           from before the first remediation's own    the empty-variants-is-Pi-valid          re-read this
           type fix); canonical schema's grammar      finding with citation; canonical         round); spec/
           `variants` sub-schema still had            schema's minProperties: 1 removed        tools.md;
           `minProperties: 1`, rejecting `{}` even     from constrainedSamplingInput's          TOOL-008;
           though Python's GrammarConstrainedSampling  variants (both key positions --          tool-registry-
           (both fields optional, no __post_init__     canonical toolInput and expected-        scenario.schema
           minimum) already permitted it.              output). 4 new schema probe tests        .json; 9 new
                                                        (grammar-empty-variants + the other       schema-domain
                                                        3 key-shape cases + unknown-key           tests
                                                        rejection).
L05-R002   spec/tools.md never stated the disposed-    Added an explicit normative paragraph    spec/tools.md
           scope rule at all (only the assurance       to spec/tools.md's Registry section.      Registry
           doc's own remediation history mentioned      New requirement TOOL-015 (this           section;
           it) -- a Rust implementer following spec    behavior was previously untraced --       TOOL-015;
           + manifest alone could not derive the        TOOL-010 amended with a forward           TOOL-010
           behavior. TOOL-010 (general registry         pointer). No Runtime/registry code
           authority/visibility) never mentioned         change -- this was purely a
           post-disposal observation.                    documentation/traceability gap.
L05-R004   _ScopeTable.key_for()'s ValueError for an    New _validate_references() function      tool_registry_
           unresolved scope_parent raises INSIDE a      runs before any Context/plugin/scope      runner.py
           plugin's apply() callback during             object is constructed: checks every       (_validate_
           root.plugins.reconcile() -- the plugin        scope_parent, query scope, step           references);
           framework records that as a fiber            plugin-id, and dispose_scope              7 new harness-
           application failure and continues            reference against the plugins[]           validation
           reconciliation rather than propagating        declarations, plus self-parent/cycle      tests (direct
           the exception, so the scenario later          detection in the parent graph --          reproduction of
           failed with an incidental KeyError            all before any mount/reconcile call.       the review's
           instead of the promised direct rejection.                                               exact failure)
L05-R005   Canonical/schema-level requiredness was      ToolDefinition.parameters type            definition.py
           correct, but the public ToolDefinition.      narrowed to type[BaseModel] |             (parameters,
           parameters type still allowed | None,        dict[str, Any] (None removed).            __post_init__);
           and schema() still had a None-handling       New __post_init__ rejects None and        execute.py
           branch -- two independent Rust designs        non-object-shaped dicts at               (_validate, dead
           (required value vs. optional+normalize)       construction, not only via typing.        None-branch
           would both find support in the package.       schema()'s dead None-branch removed.      removed); 24
                                                          All ~24 non-negative-test callsites        callsites
                                                          across src/tests updated to pass the       updated; 2 new
                                                          explicit empty schema; 2 new negative       negative unit
                                                          unit tests; TOOL-016 added (base Tool       tests; TOOL-016
                                                          fields were never traced at all before).
L05-R006   Canonical constrainedSamplingInput schema     Removed the {"type": "null"} branch       tool-registry-
           allowed { "type": "null" } as one of the      from constrainedSamplingInput (input      scenario.schema
           oneOf variants, silently treating explicit    side only). Split a separate               .json
           null the same as key-omission. The            constrainedSamplingOutput def for the      (constrained-
           EXPECTED-output side legitimately uses         expectedSchema position, which keeps       SamplingInput
           null for "absent" (matches as_json()'s own     the null-for-absence branch (matches       vs -Output); 9
           established optional-field convention) --      as_json()'s own established, unchanged     new schema-
           conflating the two positions under one         convention -- output null is not the       domain tests
           $ref was itself part of the defect.            same finding as input null).
```

### 20.3 Grammar contract, closed

```text
allowed keys        openai_lark, openai_regex (closed to pinned Pi's GrammarFormat union)
empty variants       ACCEPT at Layer 05 (Pi's type permits {}; Pi's own rejection is Layer-11
                      provider request-construction behavior, cited above -- not pulled into
                      Layer 05 merely because a later provider requires one)
unknown keys          REJECT (canonical schema additionalProperties: false; Python's
                      GrammarConstrainedSampling has exactly two named fields, structurally
                      cannot hold an unknown key at all)
TOOL-008              corrected -- closed domain, empty-variants finding, and the L05-R006
                      null-is-not-absent rule all stated with citations
spec/schema/Python/
  manifest agreement   YES
```

### 20.4 Parameters contract, closed

```text
required              YES -- ToolDefinition.parameters: type[BaseModel] | dict[str, Any], no
                        default, no None in the type
missing                REJECT (dataclass-required argument; TypeError if omitted)
null                   REJECT (__post_init__ raises TypeError)
boolean                REJECT (__post_init__ raises TypeError -- neither a dict nor a BaseModel
                        subclass)
non-object dict         REJECT (__post_init__ requires top-level "type": "object" when the value
                        is a dict; does not otherwise validate nested JSON Schema keywords --
                        Layer 05 is not a JSON Schema validator)
explicit empty schema   ACCEPT ({"type": "object", "properties": {}}, tool author supplies it)
public ToolDefinition
  agrees with spec       YES
typing fixtures agree   YES (valid_tool_construction.py no longer constructs with None; the type
                        itself excludes it, so mypy already rejects what the old fixture asserted
                        was valid -- runtime rejection is proven separately by 2 new pytest
                        negative tests, since a dynamically-typed caller can still bypass mypy)
```

### 20.5 Constrained-sampling contract, closed

```text
absent (key/field omitted)   ACCEPT
false                        ACCEPT
json_schema config           ACCEPT
grammar config                ACCEPT (including variants: {})
explicit null (canonical
  toolInput position)         REJECT (L05-R006)
explicit null (expected-
  output position)             ACCEPT unchanged -- established as_json() absence convention,
                                a different semantic position from canonical input
four-state contract exact?    YES
```

### 20.6 Canonical reference validation, closed

```text
validation before runtime side effects?   YES -- _validate_references() runs before the root
                                            Context/tools_plugin is even constructed
unknown query scope                        direct ValueError, unchanged from the first
                                            remediation (was already correct)
unknown parent scope                       direct ValueError, now raised during prevalidation --
                                            no longer swallowed by plugin reconciliation
other reference classes checked            step mount/unmount/withdraw plugin ids; step
                                            dispose_scope scope name; scope_parent self-reference;
                                            scope_parent cycles
runner still thin?                          YES -- _validate_references() only checks that
                                            declared names exist and the parent graph is acyclic;
                                            it computes no visibility, ancestry resolution,
                                            shadowing, or ordering
```

### 20.7 Registry lifetime regression (`L05-R003`, unchanged)

```text
scope-owned-after-registration    preserved, unchanged
scoped registration survives
  plugin unmount?                  YES (tool-registry-scoped-registration-survives-plugin-unmount,
                                    still green, not touched this round)
scope disposal withdraws?          YES (tool-registry-scope-disposal-withdraws, still green)
L05-R003 remains resolved?         YES -- no code, spec, or manifest text describing it changed
```

### 20.8 Canonical/schema counts

9 tool-registry scenarios discovered / 9 executed / 9 passed / 0 deferred (unchanged -- this round
is contract-consistency/evidence-integrity repair, not new product-semantic behavior, so no 10th
scenario was needed; R001/R005/R006 are covered by schema-domain tests, R002 by the existing
scope-disposal scenario, R004 by dedicated harness-validation tests). 163 schema-validation cases
(148 + 15 new: 6 parameters-domain + 9 constrained-sampling-domain probes). 7 new harness-validation
tests for `_validate_references()`. 2 new `ToolDefinition` negative unit tests. Full pytest: 873
passed, 29 xfailed, 100.00% coverage.

### 20.9 Contract-quality re-affirmation

```text
Can Rust determine the complete GrammarVariants domain
  without reading Python?                                   YES -- spec/tools.md + TOOL-008 state
                                                              it directly with a Pi citation
Is {} accepted/rejected based on Pi evidence rather than
  canonical accident?                                        YES -- Pi evidence cited in spec,
                                                              TOOL-008, and the canonical schema's
                                                              own $comment
Does TOOL-008 now say exactly what the current spec says?    YES
Is disposed-scope observation explicitly normative?           YES -- spec/tools.md Registry
                                                              section + TOOL-015
Can Rust find its requirement/evidence without reading
  Python?                                                     YES
Does malformed parent input fail before runtime side
  effects?                                                    YES
Can any missing fixture reference still be silently
  converted into a different graph?                           NO -- all reference classes
                                                              enumerated in §20.6 are validated
Is ToolDefinition.parameters required in spec, runtime
  constructor, typing, canonical schema, and tests?            YES, all five
Are missing/null parameters impossible or rejected at every
  semantic public boundary?                                    YES
Does a no-argument tool use an explicit empty schema?          YES
Is explicit constrained_sampling:null rejected?                YES (canonical input position;
                                                              output position is a different,
                                                              unaffected convention)
Are the four constrained-sampling states exact and
  exhaustive?                                                  YES
Is L05-R003 still resolved with scope-owned lifetime?          YES, unchanged
Has Runtime remained unchanged?                                YES -- zero edits under
                                                              src/minion_agent/runtime/ or
                                                              minion-agent-rust/ this round
Can Rust now implement Layer 05 from Pi + spec + manifest +
  canonical evidence without Python source?                    YES
Can Layer 06 consume the model later without redesign?         YES -- no field, method
                                                              signature, or lifecycle rule changed
                                                              shape this round
Are there zero active PI_PARITY_DEFECT findings?               YES
Are there zero active CONTRACT_ASSURANCE_DEFECT findings?      YES
Is there zero PI_BEHAVIOR_UNCERTAIN?                            YES
```

### 20.10 New candidate

```text
Layer-05 shared contract    READY FOR FRESH RUST RE-REVIEW
Python Layer 05             CERTIFIED (post-second-remediation)
Rust Layer 05                NOT_IMPLEMENTED
Rust modified                NO
Layer 06                     NOT STARTED
```

See the rewritten `05-tool-model-registry-rust-handoff.md` for the re-review request and the exact
delta since `7e288a62280969251153e080f28305ebad48fadc`.
