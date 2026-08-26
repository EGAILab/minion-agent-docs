# Tool Execution Pipeline — Fidelity Assurance & Certification

**Layer ID:** `06` (per `process/implementation-conformance-workflow.md` §6's dependency-aware
assurance order). Master designation for this layer's own content: **Phase 4 — Tools** (the
master does not split registry from execution; assurance does, per §6 items 5/6 — Layer 05 owns
the tool model/registry, this document owns execution).
**Status:** `IN_AUDIT` → first candidate self-certified 2026-08-26 (§§1–12 below) → independently
**REJECTED** (`L06-R001`..`L06-R006`, `assurance/layers/06-tool-execution-rust-review.md`) →
remediation (§13) → repaired candidate independently **RE-REVIEWED**
(`assurance/layers/06-tool-execution-rust-rereview.md`) and **REJECTED again on three of six**
(`L06-R001`, `L06-R003`, `L06-R006` re-opened; `L06-R002`, `L06-R004`, `L06-R005` confirmed
resolved) → narrow remediation, this pass (§14) → repaired candidate **READY FOR FINAL RUST
CLOSURE REVIEW**. §§1–12 preserve the original audit; §§3–8 have inline corrections where the
first candidate's own technical claims were factually wrong (validation-exemption, signal-defer
wording, hook disposition) — read the corrected text as current, §13 as the record of the first
remediation round, and §14 as the record of the second, narrower one.
**Audit date:** 2026-08-26 (original); remediation 2026-08-26; second narrow remediation
2026-08-26.
**Auditor:** Claude (Python-driven, per adopted workflow).
**Python status:** `CERTIFIED` (post second remediation) — real `ToolRegistry`/`Context`/effect/
event integration, 10/10 Layer-06-owned canonical scenarios green (corrected count, `L06-R004`),
full Pi audit re-verified, all six original Rust-review findings resolved (§13), and the three
findings the independent re-review reopened (§14) resolved at their actual authoritative
boundary.
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

Validation: pinned Pi's `validateToolArguments` (`packages/ai/src/utils/validation.ts`) validates
every `Tool.parameters: TSchema`, with no exemption for a raw-object-schema representation, via
TypeBox-specific coercion (`structuredClone`, `normalizeOptionalNulls`, `Value.Convert`, a fallback
JSON-Schema coercion path for non-TypeBox schemas). **Corrected (`L06-R001`):** the first
candidate incorrectly exempted a raw JSON-Schema `dict` from validation entirely -- a genuine
`PI_PARITY_DEFECT`, not an acceptable Layer-05-scoped limitation, since Layer 05's own "Layer 05
is not a JSON Schema validator" position was never meant to license Layer 06 skipping validation
altogether. A pydantic-model-backed `ToolDefinition.parameters` gets real pydantic validation; a
raw, object-valued JSON-Schema `dict` is now validated for real too, via the general `jsonschema`
library against the exact schema Layer 05 approved. TypeBox's exact coercion/conversion algorithm
remains unreproduced byte-for-byte -- that narrower divergence (validate vs. clone-and-coerce
identically) is disclosed and intentional; skipping validation outright was not.

Capability shape: pinned Pi's `execute(toolCallId, params, signal?, onUpdate?)`. Python's
`execute(tool_call_id, arguments)` (+ `update` when the tool declares a third parameter) now
passes the pipeline's own real call id, closing half of the `TOOL-F003` gap Layer 05 disclosed.
`signal` remains behaviorally unrealized in Layer 06. **Corrected (`L06-R005`):** the first
candidate claimed "no `AbortSignal`-equivalent type exists anywhere in this codebase yet, in
either language" -- false for Rust. Certified Rust Layer 05 already reserves a structural signal
seam (`ToolExecutionSignal`, `ToolExecutionRequest.signal` in
`minion-agent-rust/crates/minion-agent/src/tools/definition.rs`) without exercising cancellation
behavior. The accurate asymmetry: Python has no signal abstraction yet; Rust already has one,
unused. The defer itself was, and remains, correctly accepted -- only its stated basis was wrong.
Assurance Layer 09 owns cancellation propagation and can add it without changing any non-cancelled
rule this document states, and without requiring Rust to discard its existing seam.

---

## 5. Hooks

Minion's `tools/pre-execute` and `tools/post-execute` realize pinned Pi's single optional
`beforeToolCall`/`afterToolCall` callbacks. **Corrected (`L06-R006`):** the first candidate
described the N-listener extension inconsistently across this document (`PARITY_NEUTRAL_HARDENING`),
`spec/tools.md` (a bare "deliberate Minion addition/generalization" with no explicit disposition
keyword), and the manifest (`TOOL-004`/`TOOL-005` left at plain `adopted`, with no separate
requirement for chaining/replacement). The single-listener case is directly Pi-compatible (same
input, same allowed replacement surface, same failure semantics as Pi's own callback). Supporting
**N** ordered listeners per stage, composed as a deterministic registration-order fold, is an
**intentional Minion architectural extension** pinned Pi does not itself define -- classified
consistently as such now everywhere (spec, this document, `TOOL-004`/`TOOL-005`), not as
parity-neutral hardening: with more than one listener, execution is observably different from
what a single Pi callback could express.

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
after-hook structurally cannot touch it, and neither can `tool_call_id`/`tool_name`. If the
after-hook throws, Pi's catch block replaces the entire result with a bare
`createErrorToolResult(...)` — no `usage`/`details`/`terminate` survive. **Corrected (`L06-R003`):**
the first candidate let a `tools/post-execute` listener return/replace the entire `ToolResult`
directly through the raw waterfall, which could observably rewrite `tool_call_id`/`tool_name`/
`added_tool_names` -- fields Pi's own type gives a hook no way to touch at all. The only sanctioned
registration path is now `register_after_tool_call_hook`: a hook returns an `AfterToolCallOverride`
(exactly Pi's five fields) or `None`, and the framework performs the merge -- a hook cannot return
a full `ToolResult` through this path even if it tried, since the type has no slot for the
excluded fields. With N listeners (`L06-R006`), each sees the result exactly as merged by every
earlier listener, and a mid-chain exception replaces the accumulated result the same way a single
listener's exception would (see §13).

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

**Ten** scenarios were `TO_BE_FILLED` placeholders directly owned by this layer; one
(`pending-tool-calls-state`) was reclassified as Layer-07+ (`AgentState.pendingToolCalls` is an
Agent-level state-surface concern pinned Pi's own type places outside `AgentTool`/
`AgentToolResult`/the execution functions entirely — not reopened by this pass). An earlier
revision of this document said "nine" despite the list immediately below it already containing
ten names — a genuine arithmetic inconsistency (`L06-R004`), corrected here and everywhere else
in this candidate's own surfaces (spec, freeze gate, handoff, manifest notes); historical review
artifacts that correctly described an earlier, nine-scenario candidate are left untouched as
history, not rewritten. All ten Layer-06-owned scenarios are green, executed through the real
production seam (`ToolRegistry`, `Context`, the real
`execute_call`/`execute_batch`/`execute_length_stop_batch`, the real event bus):

```text
1. after-hook-failure-replaces-result-with-tool-error
2. before-hook-failure-becomes-tool-error
3. execute-failure-becomes-tool-error
4. late-tool-update-ignored
5. length-stop-executes-no-tools
6. parallel-tool-completion-vs-message-order
7. prepare-arguments-failure-becomes-tool-error
8. schema-validation-failure-becomes-tool-error
9. tool-batch-parallel
10. tool-batch-sequential-contagion

discovered: 10 | executed: 10 | passed: 10 | deferred: 0
```

`projected-execution-ends-follow-completion-order` is a separate, pre-existing Agent
log/projection scenario, not one of these ten (confirmed by the second Rust review; not
Layer-06-owned and not counted here).

`schema-validation-failure-becomes-tool-error` now uses a plain, object-valued JSON Schema
mapping -- the actual Layer-05 shared `ToolDefinition.parameters` representation -- rather than
the Python-specific `parameters: {requires: [...]}` shorthand an earlier revision used to
dynamically build a Pydantic model (`L06-R001`; that shorthand exercised a Python-only validation
path, not the approved cross-language schema boundary, and was removed from the runner and
schema entirely). `late-tool-update-ignored` needed a deterministic way to fire an update strictly
after the tool settles — the runner schedules a single cooperative scheduler-yield task
(`asyncio.sleep(0)` then `update()`), drained via `asyncio.gather` after the scenario's own steps
finish, so the assertion is never a race. Neither addition computes any tool-execution semantic
itself; both remain thin, declarative fixture construction.

`expect_messages` retains a `text_contains` alternative to exact `text` for one case
(`schema-validation-failure-becomes-tool-error`): the `jsonschema` library's own validation-error
message is host-library-specific, not a stable cross-language contract (neither pydantic's nor
Pi's own TypeBox-derived wording) -- only the Minion-authored `"invalid arguments: "` prefix is
asserted there. This is unlike the length-stop message (pinned Pi's own literal string) and the
generic failure-stage messages (`L06-R002`, now the raised error's bare message with no Python
exception-class prefix), both of which are asserted exactly.

Regression, unchanged: Runtime canonical 26, Session canonical 20, XFORM canonical 14, Layer-05
`ToolRegistry` canonical 9 (+ 7 harness-validation tests) — Layer 05's own scenario count is
genuinely 9 and is unaffected by this Layer-06 count correction; all still green, confirmed by
full suite run, not assumed.

Runner thinness confirmed: it constructs real `ToolDefinition`s and dispatches them through the
real `ToolRegistry`/`execute_batch`/`execute_call`; it does not choose scheduling, call
`prepare_arguments`/validate/hooks itself, catch `execute` exceptions to build a `ToolResult`,
reorder output messages, emit `tool_execution_end` itself, suppress late updates itself, or
implement the length-stop rule itself (that dispatch lives in production `driver.py`).

---

## 9. Findings (first-pass self-audit; see §13 for the six Rust-review findings and their repair)

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

No other `PI_PARITY_DEFECT`, `CONTRACT_ASSURANCE_DEFECT`, or `PI_BEHAVIOR_UNCERTAIN` remained
active in this first-pass self-audit. **Superseded by `L06-R006` (§13):** this section originally
classified the N-listener hook architecture as `PARITY_NEUTRAL_HARDENING`; the independent Rust
review found that classification inconsistent with spec/manifest and, more importantly, incorrect
in substance -- N-listener composition is observably different from what a single Pi callback
expresses, so it is an **intentional Minion architectural extension**, not parity-neutral
hardening. `tools/pre-execute`'s argument-replacement capability remains correctly classified as
a disclosed intentional divergence, unaffected by this correction.

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
10/10 Layer-06-owned canonical scenarios green?        YES (§8)
Layer-05 ToolRegistry regression checked?              YES (§8) -- 9/9 + 7/7 unchanged (Layer 05's
                                                          own count, not affected by the Layer-06
                                                          count correction)
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

---

## 13. Independent Rust review rejection and remediation (this pass, 2026-08-26)

The §§1–12 candidate above was submitted for independent Rust review
(`assurance/layers/06-tool-execution-rust-review.md`, candidate `minion-agent@ee563ff`,
`minion-agent-docs@e96c154`). That review returned:

```text
Layer-06 shared contract    REJECTED
L06-R001   PI_PARITY_DEFECT           raw object-valued schemas bypass validation
L06-R002   PI_PARITY_DEFECT           canonical error content includes Python exception class names
L06-R003   CONTRACT_ASSURANCE_DEFECT  after-hook field contract and production seam conflict
L06-R004   CONTRACT_ASSURANCE_DEFECT  canonical inventory is arithmetically inconsistent
L06-R005   CONTRACT_ASSURANCE_DEFECT  signal-defer evidence is factually stale
L06-R006   CONTRACT_ASSURANCE_DEFECT  Minion hook augmentation classification is inconsistent
```

This section records the repair of all six. `L06-R003` and `L06-R006` were resolved together
(the review itself said to), since both concern the same production seam.

### 13.1 Finding disposition

```text
Finding    Root cause                                Repair                              Evidence
L06-R001   validateToolArguments in pinned Pi         _validate() now validates raw       execute.py
           validates every Tool.parameters: TSchema,  object-valued schemas for real,     (_validate,
           with no exemption -- the first candidate   via the general jsonschema          ArgumentValid
           exempted a raw JSON-Schema dict from        library, against the exact         ationError);
           validation entirely, and the canonical      Layer-05-approved schema.          schema-
           schema-validation scenario used a           Canonical fixture rewritten to      validation-
           Python-specific parameters: {requires:      a plain JSON Schema mapping,        failure-
           [...]} shorthand that dynamically built     removing the requires shorthand     becomes-tool-
           a Pydantic model instead of exercising      from the runner and schema          error.yaml; 4
           the approved cross-language boundary.        entirely. jsonschema moved from     new unit
                                                        a dev-only to a real production      tests
                                                        dependency (pyproject.toml).
L06-R002   Every generic exception-handling branch     f"{type(error).__name__}: {error}"  execute.py (3
           in execute_call formatted                   replaced with the bare error         sites); 4
           f"{type(error).__name__}: {error}",          message (str(error)) at all three    canonical
           unconditionally prefixing the Python         sites: prepare/before-hook           scenarios'
           runtime class name -- pinned Pi's own        failure, execute() failure, after-    expect_
           error conversion uses error.message only     hook failure. Three existing unit    messages
           (a JS Error("boom").message is "boom",       tests strengthened from substring     corrected; 3
           not "Error: boom"). The pydantic-            containment to exact equality, so      unit tests
           validation-failure path ("invalid            they actually prove the prefix is     strengthened
           arguments: {error}") was already correct     gone rather than merely tolerating    to exact
           and untouched.                               it.                                   equality
L06-R003   tools/post-execute was a waterfall over      New AfterToolCallOverride type        decisions.py;
           the entire, frozen ToolResult -- a listener  (decisions.py) carries exactly        execute.py
           could return/replace the whole result,       Pi's five AfterToolCallResult         (_merge_
           observably rewriting tool_call_id,           fields, with no slot for identity/    override,
           tool_name, or added_tool_names, none of      added_tool_names. New                 register_
           which pinned Pi's AfterToolCallResult         register_after_tool_call_hook() is    after_tool_
           type allows a hook to touch at all.           the only sanctioned registration      call_hook);
                                                          path: a hook returns an override      test_post_
                                                          (or None), the framework merges       execute.py
                                                          it field-by-field before the next      (rewritten);
                                                          hook runs. All test/runner call        agent_
                                                          sites (test_post_execute.py,           runner.py
                                                          agent_runner.py's after-hook           (post branch
                                                          listener) migrated to the new          rewritten)
                                                          helper; the smoking-gun test
                                                          (test_a_listener_may_own_the_
                                                          result_outright) was replaced with
                                                          one proving the old capability is
                                                          gone.
L06-R004   The candidate changed exactly ten Layer-06   Every current-candidate surface        spec/tools.md
           placeholder fixtures and the assurance        (this document §8, its freeze gate,   (no stale
           inventory listed ten names, but the           the Rust handoff, this section)       count
           assurance prose, freeze gate, handoff, and    now says ten/10, with the actual       existed
           reported result said nine/9 -- a genuine      ten-item list re-numbered 1-10.        there);
           arithmetic inconsistency, not a real           Historical review artifacts           06-tool-
           scenario-count regression.                     (05-*, and this document's own        execution.md
                                                           §8/§11 prose) are corrected in        §8/§11;
                                                           place since they described the        06-tool-
                                                           CURRENT candidate incorrectly, not     execution-
                                                           a genuinely superseded earlier one.    rust-
                                                                                                  handoff.md
L06-R005   The first candidate's spec/manifest/           Replaced with the accurate            spec/tools.md
           handoff prose claimed "no AbortSignal-         asymmetry: Python has no signal        (2 sites);
           equivalent type exists in either language" --  abstraction yet; certified Rust        TOOL-018;
           false for Rust. Certified Rust Layer 05        Layer 05 already reserves one          06-tool-
           already contains ToolExecutionSignal and       structurally, unused. The defer        execution.md
           ToolExecutionRequest.signal in                  itself (behavioral, not               §4
           tools/definition.rs.                            architectural) was already
                                                            correctly accepted and remains
                                                            accepted -- only the stated basis
                                                            was corrected. No Rust file was
                                                            read differently than before; no
                                                            Rust file was changed.
L06-R006   Pi defines one callback per hook stage;         Classified consistently everywhere    spec/tools.md
           Minion's N-listener waterfalls, argument        now: single-listener is directly      §5; 06-tool-
           replacement in pre-hooks, and whole-result      Pi-compatible baseline; N-listener     execution.md
           transformation in post-hooks are observable     composition is an intentional          §5; TOOL-004/
           plugin-composition semantics the first          Minion architectural extension,        TOOL-005
           candidate classified inconsistently:            not parity-neutral hardening.          rule text
           PARITY_NEUTRAL_HARDENING in this document,      TOOL-004 (before-hook) and
           "deliberate Minion addition" with no             TOOL-005 (after-hook) each now
           disposition keyword in spec/tools.md, and        state both the Pi baseline and the
           TOOL-004/TOOL-005 left at plain adopted          Minion extension, with the extension
           with no separate requirement for                explicitly attributed to Minion, not
           chaining/replacement.                            to pinned Pi. Resolved together with
                                                             L06-R003's post-hook type boundary,
                                                             as the review itself directed.
```

### 13.2 Hook composition, fully specified (`L06-R006`)

```text
Zero listeners     No transformation. Directly Pi-compatible (matches Pi's own optional-callback
                    absence).
One listener        Same stage, same input, same allowed replacement surface, same failure
                    semantics as Pi's corresponding callback. Directly Pi-compatible.
N listeners          Intentional Minion architectural extension. Deterministic, registration-order
                    fold -- Runtime's own EventBus listener-registration order (the same ordering
                    primitive `tools/pre-execute`/`tools/post-execute` already used before this
                    pass), not an unordered set/dict. Rust can reproduce the same ordering by
                    preserving whatever registration-order primitive its own Runtime equivalent
                    exposes.

Before-hook waterfall:  listener 1 receives current validated arguments; may delegate (optionally
                        replacing arguments via Proceed) or return a decision (Block/Proceed)
                        directly, short-circuiting later listeners. A raised exception unwinds
                        the whole waterfall -- later before-hooks skipped, execute skipped, after
                        hooks never run -- converted to an error result via the L06-R002 message
                        rule.

After-hook waterfall:   listener 1 receives the current (post-execute) ToolResult; may return an
                        AfterToolCallOverride (or None); the framework merges it before listener 2
                        runs, so listener 2 sees exactly what listener 1 produced. A raised
                        exception stops later after-hooks and replaces the ENTIRE accumulated
                        result with a plain error result (L06-R002 message rule) -- earlier
                        successful overrides are discarded, not preserved, matching Pi's own
                        single-callback failure semantics extended to N listeners.
```

### 13.3 Re-checked contract-quality questions (post-remediation)

```text
Does the production executor validate every shared JsonSchemaObject?    YES (§13.1, L06-R001)
Does any cross-language canonical scenario depend on a Pydantic class?  NO -- the requires
                                                                          shorthand was removed
Does any runtime ToolResult contain Python exception class prefixes?    NO (§13.1, L06-R002;
                                                                          proven by exact-equality
                                                                          unit tests, not substring
                                                                          containment)
Can after hooks rewrite source identity?                                 NO -- AfterToolCallOverride
                                                                          has no slot for it
Can after hooks rewrite added_tool_names if Pi forbids it?                NO -- same reason
Is the multi-listener waterfall deterministic and documented?            YES (§13.2)
Is the multi-listener behavior classified consistently?                  YES -- intentional Minion
                                                                          architectural extension,
                                                                          everywhere
Does zero/one-listener behavior remain Pi-compatible?                    YES
Does signal documentation correctly describe both Python and Rust?       YES (§13.1, L06-R005)
Can Layer 09 add cancellation without changing non-cancelled rules?      YES -- no non-cancelled
                                                                          rule in this document
                                                                          changed shape
Does every current inventory count match actual discovery?               YES -- 10/10/10/0
Can Rust implement the repaired contract without reading Python?         YES
```

### 13.4 Regression

Full pytest: 909 passed, 19 xfailed, 100.00% coverage (was 903; +6 net: 4 new R001 raw-schema
tests, 1 new R003 "hook returns None" test, 1 new R003 "after-hook raises" test, minus the one
removed R003 smoking-gun test that proved forbidden behavior). `ruff check .`: all checks passed.
`mypy` (src + typing fixtures): success, 59 files (required adding `types-jsonschema` as a dev
dependency once `jsonschema` became a real production import). Schema validation: 165 (unchanged
-- `L06-R001`'s fix lives in the runner and production code, not the JSON-schema-validation
gate itself). Manifest: 65/65 unique rows (unchanged count; six rows' `rule:` text corrected
in place, no rows added or removed). Layer-06 canonical: 10/10/10/0 (corrected count, `L06-R004`).
Layer-05 `ToolRegistry` canonical 9/9 + 7/7 harness-validation (unchanged, Layer 05 untouched).
Runtime/Session/XFORM regression: 26/20/14 (unchanged).

### 13.5 New candidate

```text
L06-R001 .. L06-R006          RESOLVED
Layer-06 shared contract      READY FOR FRESH RUST RE-REVIEW
Python Layer 06               CERTIFIED (post-remediation)
Rust Layer 06                  NOT_IMPLEMENTED
Rust modified                  NO
Layer 07                       NOT STARTED
```

See the rewritten `06-tool-execution-rust-handoff.md` for the re-review request and the exact
delta since `e96c154ac760ff4e1f06bcec4c14be588e470a18`.

---

## 14. Independent Rust re-review: three findings reopened, and their narrow remediation (this pass, 2026-08-26)

The §13 candidate was submitted for a fresh, independent Rust re-review
(`assurance/layers/06-tool-execution-rust-rereview.md`, candidate
`minion-agent@ee563ffad65f1c8624536cbf8cc65dc395efe39a` docs delta plus the §13 remediation
commit). That re-review confirmed `L06-R002`, `L06-R004`, and `L06-R005` genuinely resolved, and
reopened three:

```text
Layer-06 shared contract    REJECTED (partial -- 3 of 6 confirmed resolved)
L06-R001   CONTRACT_ASSURANCE_DEFECT   ToolDefinition.parameters docstring still stale
L06-R003   PI_PARITY_DEFECT            raw public EventBus registration still bypasses
                                        after-hook override authority
L06-R006   CONTRACT_ASSURANCE_DEFECT   register_after_tool_call_hook cites a nonexistent
                                        requirement (TOOL-022)
```

This section records the narrow repair of all three. `L06-R002`, `L06-R004`, `L06-R005` were not
reopened and are not touched by this pass.

### 14.1 Finding disposition

```text
Finding    Root cause                                  Repair                            Evidence
L06-R001   The §13 repair fixed _validate()'s runtime   definition.py's module docstring   definition.py
           behavior (a raw dict is genuinely            and ToolDefinition.parameters      (module
           validated) but never updated                 field docstring rewritten: Layer   docstring,
           definition.py's own docstrings, which        05 stores the schema; Layer 06's   parameters
           still said a raw-dict tool "bypasses         execute.py validates arguments     field
           Python-side argument validation" / is        against it (pydantic for a model   docstring)
           "not Python-validated" -- a stale,            class, jsonschema for a raw
           self-contradicting public-API claim the      dict); construction itself never
           re-review caught directly against the         validates anything, regardless of
           actual, already-correct runtime behavior.     representation. No runtime
                                                          change; no new test needed for a
                                                          docstring-only fix.
L06-R003   register_after_tool_call_hook's own           _finalize() (execute.py) now       execute.py
           constrained AfterToolCallOverride type is     snapshots tool_call_id/            (_finalize);
           correct, but tools/post-execute remains a     tool_name/added_tool_names from    test_post_
           public Runtime event -- nothing stops a       the pre-hook result before          execute.py
           caller from registering a raw listener        dispatching the waterfall, and     (5 new
           directly via ctx.events.on(TOOLS_POST_        unconditionally restores them      tests)
           EXECUTE, ...) and returning a whole,          afterward, regardless of which
           differently-identified ToolResult -- which    registration path produced the
           the re-review directly proved rewrites        waterfall's output. This moves
           tool_call_id/tool_name/added_tool_names.       enforcement to the one place
           Fixing only the helper was insufficient:       every tools/post-execute
           the constraint has to live at the              dispatch necessarily passes
           authoritative dispatch boundary, not a         through, making it registration-
           registration-path-specific helper.             path-independent by
                                                           construction -- no change to the
                                                           generic EventBus, no parallel
                                                           hidden hook system, no removal
                                                           of the public TOOLS_POST_EXECUTE
                                                           event.
L06-R006   register_after_tool_call_hook's docstring      TOOL-022 citation removed and     execute.py
           cited TOOL-022, which does not exist in the    replaced with TOOL-005 (already   (docstring);
           65-row manifest -- a dangling requirement      covers N-listener composition     pi-parity-
           citation. Could not be closed by fixing the    semantics). TOOL-005's own rule    manifest.yaml
           citation alone (per the re-review's own        text extended to describe the     (TOOL-005,
           framing): R006 also required R003's            second R003 closure explicitly.   TOOL-003)
           authoritative-boundary fix, since the           No new manifest row added (the
           helper's docstring previously overstated its    instruction's own preference:
           own authority ("only sanctioned way",           repoint to an existing row over
           "structurally impossible... not merely by       inventing a placeholder).
           convention") -- both corrected together.
```

### 14.2 Authoritative after-hook boundary, restated precisely (`L06-R003`)

```text
Pi-allowed override fields (AfterToolCallResult):   content, details, isError, usage, terminate
NOT overridable by any hook, any registration path: tool_call_id, tool_name, added_tool_names

Can register_after_tool_call_hook override tool_call_id/tool_name/added_tool_names?         NO
  (AfterToolCallOverride has no slot for them -- unchanged from §13)
Can a raw ctx.events.on(TOOLS_POST_EXECUTE, ...) listener override them?                     NO
  (was YES before this pass -- the exact defect the re-review proved; _finalize's
  unconditional post-waterfall restoration now closes it regardless of registration path)
Does the fix require changing the generic EventBus, or hiding TOOLS_POST_EXECUTE?             NO
Is the constraint uniform across zero/one/N listeners, mixed helper+raw registration?         YES
  (verified: test_a_raw_event_listener_cannot_replace_execution_identity,
  test_mixed_raw_and_helper_listeners_share_the_same_authority,
  test_middle_listener_failure_skips_later_listeners_with_a_raw_listener_present)
Can a listener still mutate the ToolResult object in place instead of returning a new one?    NO
  (ToolResult is @dataclass(frozen=True, slots=True) -- structurally impossible independent
  of this fix; proven directly, not merely assumed:
  test_in_place_mutation_of_the_result_is_structurally_impossible)
Are allowed fields (content, details, usage, terminate) still overridable through the raw
  public path, i.e. is the fix scoped to identity/added_tool_names only, not a lockdown?      YES
  (verified: test_a_raw_event_listener_may_still_change_allowed_fields)
Is the omitted-vs-explicit-None override distinction preserved?                              YES
  (unchanged from the prior round -- AfterToolCallOverride fields default to None meaning
  "no override"; _merge_override already treats None as "keep current value")
```

Public API audit (§21 of the governing instruction): the only two ways to register a
`tools/post-execute` listener are `register_after_tool_call_hook(ctx, hook)` and direct
`ctx.events.on(TOOLS_POST_EXECUTE, listener)` -- `TOOLS_POST_EXECUTE` is an ordinary exported
string constant in `minion_agent.tools.events`, and `EventBus.on`/`waterfall` are fully generic,
non-event-specific APIs with no per-event type enforcement, so no third registration surface
exists. Because the fix lives in `_finalize` -- the one production call site every
`tools/post-execute` dispatch passes through regardless of how listeners were registered -- it is
correct by construction for both current paths and any future one that reuses the same event.

No negative-typing-fixture convention exists in this repository (consistent with the precedent
set at the `L05-R005` remediation); runtime enforcement at the dispatch boundary, proven by the
public-seam tests above, is treated as sufficient here too.

### 14.3 Regression

Full pytest: 914 passed, 19 xfailed, 0 failed, 100.00% coverage (was 909; +5 net, the five new
`L06-R003` public-seam tests in `test_post_execute.py`; no test removed). `ruff check .`: all
checks passed. `mypy` (src + typing fixtures): success, 59 files (unchanged file count -- no new
module added). Schema validation: 165 (unchanged -- this pass touches no JSON-schema-validation
gate). Manifest: 65/65 unique rows (unchanged count; `TOOL-005` and `TOOL-003` rule text corrected
in place; no rows added or removed, `TOOL-022` never existed as a row and is no longer cited
anywhere). Layer-06 canonical: 10/10/10/0 (unchanged -- no new canonical scenario needed for a
documentation-plus-enforcement-boundary fix, per the governing instruction's own guidance).
Layer-05 `ToolRegistry` canonical 9/9 + 7/7 harness-validation (unchanged, Layer 05 untouched).
Runtime/Session/XFORM regression: 26/20/14 (unchanged).

### 14.4 New candidate

```text
L06-R001    RESOLVED
L06-R002    RESOLVED (confirmed by re-review, not reopened, not touched this pass)
L06-R003    RESOLVED
L06-R004    RESOLVED (confirmed by re-review, not reopened, not touched this pass)
L06-R005    RESOLVED (confirmed by re-review, not reopened, not touched this pass)
L06-R006    RESOLVED
Layer-06 shared contract       READY FOR FINAL RUST CLOSURE REVIEW
Python Layer 06                CERTIFIED
Rust Layer 06                  NOT_IMPLEMENTED
Rust modified                  NO
Layer 07                       NOT STARTED
```

See the rewritten `06-tool-execution-rust-handoff.md` for the narrow final-closure-review request
and the exact delta since the `06-tool-execution-rust-rereview.md` candidate.
