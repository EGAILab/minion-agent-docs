# Tool Execution Pipeline — Fidelity Assurance & Certification

**Layer ID:** `06` (per `process/implementation-conformance-workflow.md` §6's dependency-aware
assurance order). Master designation for this layer's own content: **Phase 4 — Tools** (the
master does not split registry from execution; assurance does, per §6 items 5/6 — Layer 05 owns
the tool model/registry, this document owns execution).
**Status:** `CERTIFIED` (Python/shared candidate, this pass).
**Audit date:** 2026-08-26.
**Auditor:** Claude (Python-driven, per adopted workflow).
**Python status:** `CERTIFIED` — real `ToolRegistry`/`Context`/effect/event integration, all
Layer-06-owned canonical scenarios green, full Pi audit complete, one genuine `PI_PARITY_DEFECT`
found and repaired during this pass (see §9).
**Rust status:** `NOT_IMPLEMENTED` — Rust has no tool-execution seam yet; currently sits at Layer
05 (certified cross-language, including a real Rust implementation, `minion-agent@8b5b004`). One
layer lag, process-conforming (`process/implementation-conformance-workflow.md` §§5.9, 7, 7.3).
**Rust modified: NO.**

---

## 1. Scope

### Owns (Layer 06)

Everything that takes already-produced `ToolCall`s plus the Layer-05 `ToolDefinition`/
`ToolRegistry` surface and executes those calls: tool resolution, `prepare_arguments` invocation
ordering, argument validation, before/after hooks, `execute` invocation (capability shape,
`tool_call_id`, live updates, late-update suppression), execution-mode resolution and contagion,
parallel/sequential batch scheduling, per-call failure isolation, the two normative orderings
(completion vs. source), the length-stop special case, `ToolResultMessage` construction, and
pass-through preservation of `usage`/`details`/`added_tool_names`/`namespace`.

### Explicitly does not own (later Agent-loop layers, or Layer 09/11)

The full Agent run loop, `prompt()`/`continue()` lifecycle, steering/follow-up message injection,
`shouldStopAfterTurn`/`prepareNextTurn`, whether a `terminate=true` batch (or anything else)
suppresses/continues the next model turn, cancellation/abort propagation (assurance Layer 09 — no
`AbortSignal`-equivalent type exists anywhere in this codebase yet, in either language), and
provider-specific constrained-sampling enforcement (Real Providers, assurance Layer 11).

### Depends on

- **Layer 05** (Tool model + registry) — cross-language certified. This layer consumes
  `ToolDefinition`/`ToolRegistry` unmodified; no Layer-05 field, method signature, or semantic
  rule changed shape.
- **Layer 02** (LLM vocabulary) — certified. Every execution outcome produces a
  `ToolResultMessage` satisfying the already-certified contract (`tool_name` required,
  `usage`/`details`/`added_tool_names` optional).
- **Runtime** (Layer 01) — certified. Reuses the existing `EventBus` (`emit`/`waterfall`
  dispatch modes) unmodified; two new `EMIT`-mode events were declared
  (`tools/execution-start`/`tools/execution-end`), no Runtime primitive changed.

---

## 2. Pi source audit

Read directly at pinned Pi `b7bb00b936dbe21b8e160b3e89efdec361846699`:

- `packages/agent/src/types.ts` — `AgentTool`, `AgentToolResult`, `AgentToolUpdateCallback`,
  `ToolExecutionMode`, `BeforeToolCallResult`/`AfterToolCallResult`, `BeforeToolCallContext`/
  `AfterToolCallContext`, `AgentEvent` (`tool_execution_start`/`_update`/`_end`), `AgentState`
  (`pendingToolCalls` -- confirmed Layer-07+, not this layer's).
- `packages/agent/src/agent-loop.ts` — `executeToolCalls`, `executeToolCallsSequential`,
  `executeToolCallsParallel`, `prepareToolCall`, `executePreparedToolCall`,
  `finalizeExecutedToolCall`, `failToolCallsFromTruncatedMessage`, `createToolResultMessage`,
  `shouldTerminateToolBatch`, `prepareToolCallArguments`.
- `packages/ai/src/types.ts` — `ToolCallBlock.namespace?` (confirmed unused anywhere in
  agent-loop.ts's resolution/event/result logic — pure pass-through metadata).
- `packages/ai/src/utils/validation.ts::validateToolArguments`/`validateToolCall` — confirmed
  TypeBox-specific coercion/validation, not reproduced in Python (see §7).

No pinned-Pi uncertainty remained after this audit; every rule in §§3–8 below traces to an exact
quoted source passage.

---

## 3. Per-call pipeline stages

```text
resolve -> prepare_arguments -> validate -> before-hook -> execute (+ updates) -> after-hook
```

`tool_execution_start`/`tool_execution_end` bracket every call unconditionally. An **immediate**
outcome (unknown tool, a prepare/validate/before-hook exception, or an explicit before-hook block)
never reaches `execute()` or the after-hook. Pinned Pi's `finalizeExecutedToolCall` (the
after-hook) is invoked **only** for an outcome that actually reached `execute()`, success or
failure alike — confirmed by `executeToolCallsSequential`/`Parallel` calling
`finalizeExecutedToolCall` exclusively inside the `preparation.kind !== "immediate"` branch.

**Genuine `PI_PARITY_DEFECT` found and repaired (§9):** the pre-existing, uncertified Python
pipeline ran the after-hook (`tools/post-execute`) unconditionally on *every* outcome, including
immediate ones. Repaired: `_immediate()` now emits `tool_execution_end` directly and returns,
never calling `_finalize()`.

`resolve` uses the certified Layer-05 `ToolRegistry.resolve(name, scope)`; pinned Pi resolves by
`currentContext.tools?.find(t => t.name === toolCall.name)` over a plain array, since Pi has no
registry at all. The lookup *outcome* (found/absent) is the shared contract, not the mechanism —
already established, unmodified Minion architecture.

---

## 4. `prepare_arguments`, validation, capability shape

`prepareToolCallArguments` (Pi) always runs before `validateToolArguments` — confirmed by direct
call order in `prepareToolCall`. Reordering this would be a `PI_PARITY_DEFECT`; the pre-existing
Python pipeline never invoked `prepare_arguments` at all (a Layer-05-disclosed gap, `TOOL-F002`) —
now closed (`TOOL-018`). Pi's shim never mutates the source `ToolCall`: `prepareToolCallArguments`
returns the original object unchanged when `preparedArguments === toolCall.arguments`
(reference-equality), else a spread copy. Python's `_prepare()` passes a fresh `dict(arguments)`
copy in, matching the same nonmutation guarantee via a different mechanism (verified directly:
`test_prepare_arguments_does_not_mutate_the_original_call`).

Validation: pinned Pi's `validateToolArguments` (`packages/ai/src/utils/validation.ts`) performs
TypeBox-specific coercion (`structuredClone`, `normalizeOptionalNulls`, `Value.Convert`, a
fallback JSON-Schema coercion path for non-TypeBox schemas) — this exact algorithm is
**not** reproduced in Python. Layer 05 already established "Layer 05 is not a JSON Schema
validator"; this pass extends that decision explicitly to Layer 06: a pydantic-model-backed
`ToolDefinition.parameters` gets real Python validation (`model_validate`); a raw JSON-Schema
`dict` gets none. This is a disclosed, intentional Python-only limitation, not a silently-skipped
contract — recorded here rather than discovered by a future reviewer reading only the code.

Capability shape: pinned Pi's `execute(toolCallId, params, signal?, onUpdate?)`. Python's
`execute(tool_call_id, arguments)` (+ `update` when the tool declares a third parameter) now
passes the pipeline's own real call id, closing half of the `TOOL-F003` gap Layer 05 disclosed.
`signal` remains unrealized: no `AbortSignal`-equivalent type exists anywhere in this codebase
yet, in either language — confirmed by direct search, unchanged from the Layer-05-era finding.
This is assurance Layer 09's obligation, not Layer 06's.

---

## 5. Hooks

Minion's `tools/pre-execute` (waterfall, terminal `Proceed(validated_arguments)`) and
`tools/post-execute` (waterfall over the result) realize pinned Pi's single optional
`beforeToolCall`/`afterToolCall` callbacks as composable listener chains — an intentional,
already-established Minion architectural generalization (Pi has exactly one hook slot per
extension point; Minion allows N, each cooperatively delegating via `next()`).

Pinned Pi's `prepareToolCall` wraps `prepareArguments` + `validateToolArguments` +
`beforeToolCall` in **one** try/catch (confirmed by direct source inspection: a single `try`
block spans all three calls). A before-hook listener that throws — rather than returning a
structured `{block: true}` — collapses to the same generic error result as a prepare/validation
failure. Python's `execute_call` now wraps the equivalent three-stage sequence
(`_prepare` + `_validate` + the `tools/pre-execute` waterfall dispatch) in one `try`/`except`,
matching this exactly (verified: `test_a_raising_before_hook_listener_produces_an_error_result`).

`tools/pre-execute` may additionally replace the arguments a listener sees
(`Proceed(arguments=...)`) — an intentional Minion addition pinned Pi's `BeforeToolCallResult`
has no equivalent for (`{block?, reason?, terminate?}` only, no argument-replacement field). This
predates Layer 06 and is preserved unmodified; disclosed here as an already-established,
opt-in-only architectural augmentation that does not change default (unused) observable behavior.

After-hook merge (`finalizeExecutedToolCall`): `content ?? result.content`, `details ?? ...`,
`usage ?? ...`, `terminate ?? ...`, `isError ?? isError` — nullish-coalescing field-by-field,
never a deep merge. `addedToolNames` is **not** in `AfterToolCallResult`'s field list at all; the
after-hook structurally cannot touch it. If the after-hook throws, Pi's catch block replaces the
entire result with a bare `createErrorToolResult(...)` — no `usage`/`details`/`terminate` survive.
Python's new after-hook try/except (added this pass — see §9) matches exactly.

---

## 6. Batch execution: mode, contagion, ordering

Effective mode is decided by the batch (`TOOL-020`): Layer 05's `execution_mode: None`
deliberately means "no per-tool preference," never "parallel" (`TOOL-F004`, unmodified). Pinned
Pi's own default is "parallel" (`AgentLoopConfig.toolExecution?` docstring, "Default: parallel").
`execute_batch`'s new `default_mode: ExecutionMode = ExecutionMode.PARALLEL` parameter matches
this exactly; omitting it does not accidentally serialize an otherwise-parallel batch (verified:
`test_the_run_level_default_is_parallel_when_unspecified`).

Contagion (`hasSequentialToolCall`): the run-level default being sequential, **or** any tool call
in the batch resolving to a tool whose own `execution_mode` is sequential, forces the **entire**
batch sequential — confirmed this is a batch-level, not per-tool, decision: Pi's
`executeToolCalls` picks between `executeToolCallsSequential`/`Parallel` **once**, for the whole
call. An unresolvable name is never exclusive. This algorithm was already correctly implemented
pre-Layer-06 (`_is_sequential`'s per-tool half); this pass adds the missing run-level-default half
(`TOOL-020`, verified: `test_the_run_level_default_serializes_the_batch_even_without_a_sequential_tool`).

Two orders, stated directly in pinned Pi's own `ToolExecutionMode` docstring: `tool_execution_end`
fires in actual **completion** order; the final `ToolResultMessage` sequence preserves **source**
order regardless. Both hold simultaneously in one parallel batch. Python's `asyncio.gather`
preserves input-array order in its resolved output — the same structural guarantee as JS's
`Promise.all` — so source-order reconstruction requires no manual sort; `completion_order` is
recorded separately via a side-effecting append inside each per-call coroutine. This was already
correctly implemented pre-Layer-06 and is unmodified; `parallel-tool-completion-vs-message-order`
is new canonical evidence for it (previously covered only by unit tests).

Length stop (`failToolCallsFromTruncatedMessage`): confirmed **no** resolution, preparation,
validation, before-hook, or `execute()` runs for any call in the batch when the originating
assistant message's stop reason is `length` — not even an unknown-tool lookup. Each call becomes
the identical, literal error message Pi emits (`"Tool call \"{name}\" was not executed: the
response hit the output token limit, so its arguments may be truncated. Re-issue the tool call
with complete arguments."`), in source order. `tool_execution_start`/`tool_execution_end` still
fire for each. `terminate` is unconditionally `False` — Pi's function returns
`{messages, terminate: false}` directly, never routing through `shouldTerminateToolBatch`. This
entire function (`execute_length_stop_batch`) and its wiring into `driver.py`'s stop-reason
dispatch were newly added this pass — the length-stop rule did not exist in Python at all before.

---

## 7. Contract-quality guardrail applied

Per the established rule ("contract stability is not a goal in itself... reopen only when the
better implementation requires a different observable semantic rule"): the decision to leave
Pi's TypeBox-specific validation/coercion algorithm unreproduced (§4) was evaluated against this
guardrail and kept as an intentional, disclosed divergence — building a general JSON Schema
validator/coercion engine in Python solely to match TypeBox's exact behavior would be new,
speculative machinery with no current consumer, contradicting Layer 05's own settled "Layer 05 is
not a JSON Schema validator" position. No other warning sign from the guardrail's own list
(runner implementing scheduling, runner constructing error results, duplicated validation logic,
late-update suppression only in tests, post-hoc ordering hacks, hook-replacement semantics
differing by failure path) was found.

---

## 8. Canonical evidence

Nine scenarios were `TO_BE_FILLED` placeholders directly owned by this layer; one
(`pending-tool-calls-state`) was reclassified as Layer-07+ (`AgentState.pendingToolCalls` is an
Agent-level state-surface concern pinned Pi's own type places outside `AgentTool`/
`AgentToolResult`/the execution functions entirely — not reopened by this pass). All nine
Layer-06-owned scenarios are now green, executed through the real production seam
(`ToolRegistry`, `Context`, the real `execute_call`/`execute_batch`/`execute_length_stop_batch`,
the real event bus):

```text
after-hook-failure-replaces-result-with-tool-error
before-hook-failure-becomes-tool-error
execute-failure-becomes-tool-error
late-tool-update-ignored
length-stop-executes-no-tools
parallel-tool-completion-vs-message-order
prepare-arguments-failure-becomes-tool-error
schema-validation-failure-becomes-tool-error
tool-batch-parallel
tool-batch-sequential-contagion
```

`schema-validation-failure-becomes-tool-error` needed a genuine, validated parameter schema
(Layer 05's own empty-object raw-dict default performs no validation) — the runner's `_stub()`
now supports `parameters: {requires: [...]}`, dynamically building a real pydantic model, an
acceptable "scripted `ToolDefinition`" mock seam (§37 of the kickoff instruction), not a
simulation of execution semantics. `late-tool-update-ignored` needed a deterministic way to fire
an update strictly after the tool settles — the runner schedules a single cooperative
scheduler-yield task (`asyncio.sleep(0)` then `update()`), drained via `asyncio.gather` after the
scenario's own steps finish, so the assertion is never a race. Neither addition computes any
tool-execution semantic itself; both remain thin, declarative fixture construction.

`expect_messages` gained a `text_contains` alternative to exact `text` for one case
(`schema-validation-failure-becomes-tool-error`): pydantic's own `ValidationError` formatting is
host-library-specific, not a stable cross-language contract, unlike the length-stop message
(which is pinned Pi's own literal string and is asserted exactly).

Regression, unchanged: Runtime canonical 26, Session canonical 20, XFORM canonical 14, Layer-05
`ToolRegistry` canonical 9 (+ 7 harness-validation tests) — all still green, confirmed by full
suite run, not assumed.

Runner thinness confirmed: it constructs real `ToolDefinition`s and dispatches them through the
real `ToolRegistry`/`execute_batch`/`execute_call`; it does not choose scheduling, call
`prepare_arguments`/validate/hooks itself, catch `execute` exceptions to build a `ToolResult`,
reorder output messages, emit `tool_execution_end` itself, suppress late updates itself, or
implement the length-stop rule itself (that dispatch lives in production `driver.py`).

---

## 9. Findings

**One genuine `PI_PARITY_DEFECT`, found and repaired within this pass** (never carried forward as
an open finding): the pre-existing, uncertified Python pipeline ran the after-hook
(`tools/post-execute`) unconditionally on *every* outcome, including immediate ones (unknown
tool, validation failure, before-hook block) — contradicting pinned Pi's
`finalizeExecutedToolCall`, which is invoked only for an outcome that actually reached
`execute()`. A pre-existing test (`test_an_error_result_is_transformed_too`) asserted the old,
incorrect behavior on an unknown-tool call; it was replaced with two corrected tests
(`test_an_execute_failure_is_transformed_too`, proving the after-hook *does* run for a genuine
`execute()` failure, and `test_an_unknown_tool_never_reaches_the_after_hook`, proving it does
*not* run for an immediate one). Repair: `execute_call` restructured so immediate outcomes
(`_immediate()`) emit `tool_execution_end` and return directly, never calling `_finalize()`.

Separately, and discovered while writing the after-hook-failure canonical scenario (which failed
with an escaping, uncaught `RuntimeError` before the fix): the after-hook's own exceptions were
never caught at all in the pre-existing code — a listener that threw would propagate out of
`execute_call` entirely rather than becoming an error result. This gap predates Layer 06 and was
not introduced by this pass. Repair: a second `try`/`except` was added around `_finalize()`
itself, matching pinned Pi's separate `finalizeExecutedToolCall` try/catch exactly — an after-hook
exception now replaces the entire prior result with a plain error result, discarding whatever
`usage`/`details`/`terminate` it carried, matching §5's merge rule precisely.

No other `PI_PARITY_DEFECT`, `CONTRACT_ASSURANCE_DEFECT`, or `PI_BEHAVIOR_UNCERTAIN` remains
active. One `PARITY_NEUTRAL_HARDENING`: `tools/pre-execute`'s argument-replacement capability and
the waterfall-based N-listener hook architecture, both pre-existing and unmodified, remain
disclosed intentional divergences from Pi's single-callback hook shape (§5) — they do not change
default observable behavior for any scenario that does not specifically exercise them.

---

## 10. Contract-quality questions

```text
Can Rust implement Layer 06 without reading Python source?          YES -- spec/tools.md states
                                                                      every rule in language-
                                                                      neutral terms with exact
                                                                      Pi citations
Can a later Agent-loop layer consume this without redesign?          YES -- execute_batch/
                                                                      execute_length_stop_batch
                                                                      already accept a default
                                                                      mode, a real ToolRegistry,
                                                                      and produce ordered
                                                                      ToolResultMessages plus
                                                                      completion-order metadata;
                                                                      driver.py's own stop-reason
                                                                      dispatch is the only new
                                                                      integration point, and it
                                                                      required no other
                                                                      turn/step logic to change
Is the runner thin?                                                   YES (§8)
Is execution ordering fully specified?                                YES (§6) -- both orders
                                                                      stated, neither invented
Is error/failure-taxonomy semantics fully specified?                  YES (§3-5, §9)
Is the signal/update boundary fully specified?                        YES (§4) -- update/late-
                                                                      update precise; signal
                                                                      explicitly deferred to
                                                                      Layer 09 with the exact
                                                                      reason (no type exists)
Is the Layer-05 contract preserved unmodified?                        YES -- zero ToolDefinition/
                                                                      ToolRegistry semantic
                                                                      changes this pass
```

---

## 11. Freeze gate

```text
Pi execution-pipeline audit complete?                 YES (§2)
Layer 06/Agent-loop boundary explicit throughout?      YES (§1, spec/tools.md)
Per-call pipeline stages pinned?                       YES (§3-5)
Batch mode/contagion/ordering pinned?                  YES (§6)
Length-stop rule pinned and implemented?               YES (§6)
Canonical evidence: real registry/executor/events?     YES (§8) -- no simulated semantics
9/9 Layer-06-owned canonical scenarios green?          YES (§8)
Layer-05 ToolRegistry regression checked?              YES (§8) -- 9/9 + 7/7 unchanged
Runtime/Session/XFORM regression checked?              YES (§8) -- 26/20/14 unchanged
Full Python gates green?                               YES (§12) -- 903 passed/19 xfailed/100%
Contract-quality review all green?                     YES (§10)
Active PI_PARITY_DEFECT?                               NONE (repaired within this pass, §9)
Active CONTRACT_ASSURANCE_DEFECT?                       NONE
Active PI_BEHAVIOR_UNCERTAIN?                          NONE
Rust implementation status recorded?                   NOT_IMPLEMENTED, VALIDLY ONE LAYER BEHIND
```

All green.

```text
Layer 06 shared contract candidate    READY FOR INDEPENDENT RUST REVIEW
Python Layer 06                       CERTIFIED
Rust Layer 06                         NOT_IMPLEMENTED -- VALIDLY ONE LAYER BEHIND
```

---

## 12. Fresh gates

```text
full pytest (coverage enabled):     903 passed, 19 xfailed, 0 failed, 100.00% coverage
ruff check .:                        All checks passed
mypy (configured scope):             Success, no issues found in 57 source files
mypy + typing fixtures:              Success, no issues found in 59 source files
schema validation:                   165 passed (unchanged)
manifest: parse + unique-ID audit:   65 / 65 unique
```

Reproduce via (from `minion-agent-python/`): `uv run pytest`, `uv run ruff check .`,
`uv run mypy src/minion_agent`, `uv run mypy src/minion_agent tests/typing/valid_message_
construction.py tests/typing/valid_tool_construction.py`.

Layer 07 (the Agent run loop proper — `prompt()`/`continue()` lifecycle, steering/follow-up,
turn-continuation decisions) is **not started**. Real Providers (assurance Layer 11) and
cancellation (assurance Layer 09) remain untouched and unstarted.
