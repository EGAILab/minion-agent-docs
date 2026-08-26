# Layer 05–06 Independent Review Remediation — Shared/Python Pass

**Remediation date:** 2026-08-26
**Remediated by:** Claude (shared-contract/Python owner, per the adopted workflow)
**Scope of this pass:** shared contract (`spec/tools.md`, `pi-parity-manifest.yaml`, canonical
conformance) and Python implementation only. **No Rust production code, tests, or conformance
adapter were modified.** This is PASS 1 of a three-pass sequence agreed for this remediation:
PASS 1 (this document) repairs the shared/Python side; PASS 2 is a fresh, independent Rust review
of the corrected shared contract; PASS 3 is Rust remediation, gated on PASS 2's approval. Combining
Rust remediation into this same pass would have broken the two-language independent-review
discipline this whole assurance process depends on, so it was deliberately not attempted here.

---

## Starting state

```text
minion-agent          5683fd9de82c0bf7fdb4462e241c687cd26afcb6  (main, PR #11 merged:
                                                                  Rust Layer 06 implementation)
minion-agent-docs     4b52cd6b21502e05e38999a6450d44d4f2247c57  (master, PR #2 merged:
                                                                  Rust Layer 06 certified)
pinned Pi             b7bb00b936dbe21b8e160b3e89efdec361846699  (local ref-repos/pi checkout,
                                                                  confirmed at this exact commit)
```

Layer 06 was **cross-language certified / closed** at this starting point
(`06-tool-execution-rust-implementation.md`). An independent review against this certified
candidate found six findings, two of which (`IR-L06-001`, `IR-L06-004`) prove that Python and Rust
had certified *in agreement with each other* while both disagreed with pinned Pi -- the reason
prior cross-language certification is evidence of implementation agreement, never semantic
authority on its own.

The unrelated Phase-5 provider-design working-tree modification
(`design/2026-08-20-phase-5-real-providers-amendment-proposal-review-feedback.md`) was present,
untouched, unstaged, and uncommitted throughout, per this session's standing constraint.

---

## Pi re-audit

Read directly at pinned Pi `b7bb00b936dbe21b8e160b3e89efdec361846699` (local checkout,
`ref-repos/pi`):

- `packages/agent/src/agent-loop.ts::executeToolCallsParallel` -- confirmed the sequential
  preflight loop (`for` over `toolCalls`, `await prepareToolCall(...)` per call) followed by a
  single `Promise.all` over deferred closures for calls that reached `"prepared"`; an immediate
  outcome is finalized and its `tool_execution_end` emitted inline, inside the sequential loop,
  before the barrier.
- `packages/agent/src/agent-loop.ts::prepareToolCall` -- confirmed the exact unknown-tool text,
  `` `Tool ${toolCall.name} not found` ``, and the `try`/`catch` boundary around
  `prepareToolCallArguments` + `validateToolArguments` + `beforeToolCall`.
- `packages/agent/src/agent-loop.ts::finalizeExecutedToolCall` / `createErrorToolResult` --
  confirmed the field-by-field nullish-coalescing merge, and that `createErrorToolResult` returns
  `details: {}` (an empty object, never absent), which `createToolResultMessage` copies verbatim
  with no conditional collapse.
- `packages/agent/src/types.ts::AfterToolCallResult` -- confirmed every field is a *single-level*
  optional (`details?: unknown`, etc.); Pi has no way to distinguish "explicitly cleared" from
  "omitted."
- `packages/agent/src/types.ts::AgentToolResult<T>` -- confirmed `details: T` is **required**, not
  optional, on the executed-result type itself.
- `packages/agent/src/types.ts::AgentEvent` -- confirmed `tool_execution_update`'s exact fields
  (`toolCallId`, `toolName`, `args`, `partialResult`), and, by tracing `executePreparedToolCall`,
  that `args` is `prepared.toolCall.arguments` -- the **original**, untouched call
  `prepareToolCall` was given, not the `prepareArguments`-shimmed or schema-validated value.

No pinned-Pi uncertainty remained after this audit; every rule below traces to an exact quoted
source passage.

---

## IR-L06-001 — Sequential preflight barrier in parallel batches

**Classification:** `CONTRACT_ASSURANCE_DEFECT` + `PI_PARITY_DEFECT` (both apply: the shared
contract never stated the barrier, and the Python/Rust implementations it authorized were
observably wrong relative to Pi).

**Pi evidence:** see re-audit above. Confirmed directly by reading `executeToolCallsParallel`
line by line: preflight (`resolve` → `prepareArguments` → `validateToolArguments` →
`beforeToolCall`) for every call in the batch runs inside one plain, sequential `for` loop, with
`await prepareToolCall(...)` blocking that loop until each call's preflight settles. Only entries
of kind `"prepared"` are deferred as closures; they are invoked concurrently, via a single
`Promise.all`, only *after* the loop over every source call has finished.

**Contract repair:** `spec/tools.md`'s "Batch execution" section rewritten to state the two-phase
structure explicitly (sequential preflight, then concurrent execute/finalize for the calls that
survived it), with the exact event-interleaving example pinned Pi requires
(`tool_execution_start(A)`, `preflight(A)`, `tool_execution_start(B)`, `preflight(B)`, barrier,
`execute(A)`/`execute(B)`). `pi-parity-manifest.yaml` gained a new row, **`TOOL-023`**, dedicated
to this rule (deliberately not folded into `TOOL-006`'s "result/event ordering" prose, per the
governing instruction's own "do not hide the rule inside prose about result ordering"); `TOOL-001`
and `TOOL-006` each gained a cross-reference clarifying what they do and do not own relative to
`TOOL-023`.

**Canonical repair:** two new Python-level regression tests were added
(`tests/tools/test_batch.py`), both exercising the real production `execute_batch` /
`_preflight` / `_execute_and_finalize` seam directly -- not a simulation:

```text
test_preflight_is_sequential_and_settles_before_any_execute_begins
    Scenarios A+B combined: call "a"'s before-hook awaits a real scheduler tick; call "b" has no
    such delay. Asserts events[:4] == ["start_a", "before_a", "start_b", "before_b"] and that
    both "execute_a"/"execute_b" occur only after both before-hooks have settled. Confirmed to
    FAIL against the pre-fix candidate (temporarily reverted batch.py/execute.py and re-ran this
    test alone: produced ["start_a", "start_b", "before_b", "execute_b", "before_a", "execute_a"]
    -- start_b fired before before_a, and execute_b fired before before_a, exactly the violation
    this test exists to catch) and to PASS after the fix.

test_an_immediate_preflight_failure_does_not_block_a_later_calls_preflight
    Scenario C: an unknown-tool call ("missing") is followed by a real call ("b"). Asserts
    events == ["start_missing", "start_b", "before_b"] -- "missing" never reaches a before-hook at
    all, and does not delay "b"'s own start/preflight.
```

Scenario D (prepared calls still overlap concurrently after the barrier) is already covered,
unchanged, by the pre-existing `test_parallel_tools_actually_overlap`. Scenario E (source-order
results, completion-order ends) is already covered, unchanged, by
`test_results_come_back_in_assistant_source_order` / `test_completion_order_is_recorded_separately`.

**Known gap, explicitly deferred, not silently skipped:** a fully language-neutral canonical
YAML scenario (`conformance/agent/*.yaml`, executable by both Python's and Rust's real production
executor once Rust is repaired) was **not** added this pass. The existing scenario schema's only
timing primitive (`tools.<name>.delay_ticks`) delays a tool's `execute()` stage, not its
before-hook/preflight stage, and no existing `listeners` action can inject a genuine async
suspension into preflight -- reproducing the exact race this finding depends on would require a
new schema/runner primitive (e.g. a before-hook delay), which is new, speculative canonical-runner
machinery this pass's own Python-only proof did not need. Building it now, before Rust's own fix
exists to consume it, was judged premature; the Python-level regression tests above are real,
proven against the actual production seam, and sufficient to close this finding on the Python
side. Adding the cross-language canonical scenario is recommended as a fast-follow, either before
or during PASS 3 (Rust remediation), once there are two implementations for it to distinguish.

**Python repair:** `execute.py` split `execute_call`'s single monolithic pipeline into two
functions with no duplicated rules between them: `_preflight` (resolve → `prepare_arguments` →
validate → before-hook waterfall; returns a `_Prepared` or an already-finalized `ToolResult` for
an immediate outcome) and `_execute_and_finalize` (execute + live updates + after-hook waterfall;
always ends by emitting `tool_execution_end`). `execute_call` itself becomes a two-line wrapper
(`_preflight` then, if prepared, `_execute_and_finalize`) used both for a standalone single call
and, unchanged, for `execute_batch`'s sequential-mode path. `batch.py::execute_batch`'s parallel
branch now runs `_preflight` in a plain sequential `for` loop across all source calls first (the
barrier), recording an immediate outcome's completion right there, then runs
`_execute_and_finalize` concurrently, via `asyncio.gather`, only for the calls that survived
preflight.

**Rust repair:** **not attempted this pass.** Rust Layer 06 (`minion-agent-rust/crates/
minion-agent/src/tools/execution.rs`) still uses `FuturesUnordered<execute_one(...)>` where
`execute_one` performs preflight and execution together -- the same shape the prior Python
candidate had. This is explicitly out of scope for PASS 1 and is recorded as `PENDING` on
`TOOL-023`'s manifest row for PASS 3.

**Verdict:** shared contract and Python **RESOLVED**. Rust **OPEN**, deferred to PASS 3 by
design, not by omission.

---

## IR-L06-002 — Rust after-hook nullish override semantics

**Classification:** `PI_PARITY_DEFECT`, **Rust-only**.

**Pi evidence:** `AfterToolCallResult`'s fields are each a single-level optional
(`details?: unknown`, `usage?: Usage`, etc.); Pi's own type system gives a hook no way to express
"explicitly clear this field" as distinct from "I did not set this field" -- both are the same
absent/`undefined` JS value, merged the same way by `?? `.

**Repair (shared/canonical scope only, per PASS 1):** re-confirmed Python's
`AfterToolCallOverride` (`decisions.py`) already mirrors this exactly -- flat `field: X | None`
with no second `Optional` layer, so Python is *structurally* incapable of representing the
Pi-incompatible "explicitly clear" state Rust's independent review found. This is not a fix, since
nothing was wrong: `test_omitted_fields_are_unchanged` and `test_there_is_no_deep_merge` already
prove it, unchanged this pass. `pi-parity-manifest.yaml`'s `TOOL-005` row gained a paragraph
recording this finding's disposition precisely, so the rule Rust needs to conform to is stated
unambiguously without needing to read Python's implementation technique.

**Cross-language result:** Python conformant (confirmed, unchanged). Rust's
`AfterToolCallOverride` reportedly uses `Option<Option<Value>>`/`Option<Option<Usage>>`, which
*does* expose the extra state Pi lacks -- a genuine, Rust-specific API defect. **Not fixed this
pass** (Rust production code is out of scope for PASS 1); deferred to PASS 3.

**Verdict:** shared rule confirmed and stated precisely in the manifest. Python **RESOLVED
(already conformant)**. Rust **OPEN**, deferred to PASS 3.

---

## IR-L06-003 — Python unknown-tool error text

**Classification:** `PI_PARITY_DEFECT`, Python-only (Rust already matched Pi, per the governing
instruction's own note, unverified independently this pass since it requires reading Rust source
-- deferred to PASS 2's confirmation step).

**Pi evidence:** `` createErrorToolResult(`Tool ${toolCall.name} not found`) ``, exact string.

**Repair:** `execute.py`'s unknown-tool branch changed from `f"unknown tool {call.name!r}"` (wrong
wording, wrong casing, Python `repr`-quoting) to `f"Tool {call.name} not found"`. Every
substring-only assertion of the old text was strengthened to exact equality
(`tests/tools/test_execute.py::test_an_unknown_tool_produces_an_error_result`,
`tests/agent_loop/test_tool_round_trip.py::test_an_unknown_tool_still_closes_the_loop`).
`pi-parity-manifest.yaml`'s `TOOL-017` row gained the exact-text requirement and citation.

**Exact output:** for a call naming `missing`, the model-visible text is now exactly
`Tool missing not found` (confirmed via both the direct unit test and the full agent-loop
round-trip test).

**Verdict:** **RESOLVED** (Python). Rust's own text was not independently re-verified from source
this pass (out of scope for PASS 1); PASS 2 should confirm it directly rather than trust this
pass's restatement of the governing instruction's claim.

---

## IR-L06-004 — Preserve Pi error `details: {}`

**Classification:** `PI_PARITY_DEFECT`, affecting Python (fixed) and Rust (deferred).

**Pi evidence:** `AgentToolResult.details: T` is **required**, not optional, on the interface
itself; `createErrorToolResult` sets it to `{}`; `createToolResultMessage` copies
`finalized.result.details` verbatim with no conditional logic. An empty-but-present `{}` is
therefore Pi's actual, common, unremarkable state for every error result and every tool that never
sets its own details -- never "the same as absent."

**Python repair:** `result.py::ToolResult.to_message()` changed `details=self.details or None` to
`details=self.details` -- a straight pass-through. `ToolResult.details` already defaulted to `{}`
(unrelated to this fix, pre-existing), so this one-line change is sufficient: every error path
(unknown tool, prepare/validate failure, before-hook block/throw, execute failure, after-hook
failure) already carried `details={}` internally; only the final model-visible projection was
incorrectly collapsing it. `added_tool_names` was independently re-checked and is *not* affected:
Pi's own `createToolResultMessage` conditionally *omits* that key when the array is empty
(`addedToolNames?.length ? {...} : {}`), which Minion's existing `self.added_tool_names or None`
already matched and still does -- this finding was scoped to `details` only, by design, not
carried over into a change that was never wrong.

**Rust repair:** **not attempted this pass** (production code, out of scope for PASS 1). The
independent review's claim that Rust's immediate/error helper produces `details: None` was not
independently re-verified from source this pass; PASS 2 should confirm it directly.

**Canonical evidence:** `tests/tools/test_result.py::test_a_result_with_no_details_carries_the_
empty_dict_on_the_message` (renamed and re-asserted from `... carries_none_on_the_message`, which
asserted the old, incorrect behavior directly). `pi-parity-manifest.yaml`'s `TOOL-021` row gained
the exact rule text and this test's citation. A dedicated cross-language canonical YAML scenario
asserting `details == {}` through the full agent-loop message projection was not added this pass,
for the same reason given under IR-L06-001's "known gap" note: the existing schema's
`expect_messages` matcher was not audited for whether it can assert a structured `details: {}`
value distinctly from an absent key without further schema work, and Python's own unit-level
proof (above) is real, exercises the actual `ToolResult.to_message()` production seam, and is
sufficient to close the Python side. Recommended as a PASS 3 fast-follow, once Rust's fix exists
to cross-check against it.

**Verdict:** Python **RESOLVED**. Rust **OPEN**, deferred to PASS 3.

---

## IR-L06-005 — Tool update event payload decision

**Classification:** `CONTRACT_ASSURANCE_DEFECT` (a genuine gap, not a Pi-parity violation per se,
since Minion's event *architecture* -- EMIT-mode Runtime events carrying real objects, not a
decomposed wire payload -- was already an accepted, disclosed divergence from Pi's `AgentEvent`
union; the gap was that the *payload* carried strictly less information than Pi's own event for no
stated reason).

**Pi evidence:** `AgentEvent`'s `tool_execution_update` variant carries `toolCallId`, `toolName`,
`args`, `partialResult`. Tracing `executePreparedToolCall`'s own emit call site confirmed `args`
is `prepared.toolCall.arguments` -- and `PreparedToolCall.toolCall` is the *original* parameter
`prepareToolCall` was given, not `prepareToolCallArguments`'s shimmed output or
`validateToolArguments`'s validated output.

**Chosen disposition: Option A — adopt Pi's payload.** No concrete Minion architectural reason
favored the narrower shape Minion had; the fields are cheap to preserve and useful to observers,
matching the governing instruction's own stated preference absent a reason to diverge.

**Rationale:** `tools/execution-start` and `tools/execution-end` already carry Pi-equivalent
information (`tool_call_id`/`tool_name`/`args` and `tool_call_id`/`tool_name`/`result`
respectively) -- `tools/update` carrying strictly less was an inconsistency within Minion's own
event vocabulary, not a deliberate design choice recorded anywhere.

**Spec/manifest/canonical changes:** `spec/tools.md`'s "Live updates" paragraph states the new
payload and the `args`-is-original-not-validated rule explicitly. `pi-parity-manifest.yaml`'s
`TOOL-019` row gained the full decision record (problem, chosen option, rationale, exact new
payload shape, exact `arguments` provenance) and a new test citation.

**Implementation result:** `execute.py`'s `update(partial)` closure (now inside
`_execute_and_finalize`) emits `ctx.events.emit(TOOLS_UPDATE, call.id, call.name, call.arguments,
partial, scope=scope)` -- four positional arguments where there were two. Every existing listener
signature across the codebase was updated to match (`tests/tools/test_updates.py`,
`tests/conformance/agent_runner.py`). A new test,
`test_updates_carry_the_tool_name_and_original_arguments`, proves the tool name and the
*original*, pre-validation arguments both survive into the emitted payload, using a call whose
raw argument (`note="original"`) would be indistinguishable from validated output only because the
stub schema has no properties to transform -- the test asserts against the call's own raw
arguments dict, not a coincidentally-identical validated one.

**Verdict:** **RESOLVED** (shared contract + Python). This is a Minion-architecture event-payload
decision, not a Pi-parity finding in the after-the-fact sense, so there is no separate Rust
"defect" to defer -- PASS 3 (or an earlier Rust-side pass, since Rust's Layer 06 already has its
own `ToolExecutionUpdate` event type per its assurance record) should align Rust's own update
event payload with this same decision, but that is new Rust work, not a fix to something Rust
built wrong.

---

## IR-L05/06-006 — Assurance and documentation contradictions

**Classification:** `CONTRACT_ASSURANCE_DEFECT`.

**Signal seam (`§9.1`):** searched every current spec/assurance surface
(`spec/tools.md`, `assurance/layers/06-tool-execution.md` and its later sections,
`assurance/layers/05-tool-model-registry.md`) for a live claim that "no `AbortSignal`-equivalent
exists in either language." The only occurrences found are inside `spec/tools.md`'s own corrective
prose (`` an earlier revision incorrectly claimed "no equivalent type exists in either language" ``)
and inside the historical `06-tool-execution-rust-review.md` review artifact (correctly preserved,
unedited, as history of what the first review found). **No live, current-state claim remains** --
this was already fully corrected during the `L06-R005` remediation round, before this pass began.
No edit was needed or made.

**`tool_call_id` wiring (`§9.2`):** searched for any current claim that Python execution does not
receive the real tool-call id. `05-tool-model-registry.md` (Layer 05's own historical
certification report) still describes `TOOL-F003` as a disclosed, then-open gap -- this is
**correct as history**: Layer 05 certified before Layer 06 existed, and disclosing the gap for a
later layer to close is exactly what that report is supposed to record; rewriting it now would
erase the record the governing instruction itself says must remain (`"Do not alter historical
review documents merely to erase the record of prior findings"`). The **current**, authoritative
traceability already correctly states the closure: `pi-parity-manifest.yaml`'s `TOOL-018` row says
plainly that `execute(tool_call_id, arguments)` "receives the pipeline's own real call id... closing
part of the `TOOL-F003` gap Layer 05 disclosed," and `execute.py`'s own `_execute_and_finalize`
(this pass's refactor of the same call site) still passes `call.id` as `execute`'s first argument,
unchanged in behavior. No stale claim was found on any current surface; no edit was needed.

**Verdict:** **RESOLVED** -- confirmed already correct from the prior remediation round; this pass
made no changes for this finding, since none were needed.

---

## Layer 05 regression

Not redesigned. Confirmed unaffected, full suite: `tests/conformance/test_tool_registry_
conformance.py` + `test_tool_registry_runner_validation.py` — **16 passed** (9 canonical + 7
harness-validation, unchanged counts). No `ToolDefinition`/`ToolRegistry` field, method signature,
or semantic rule changed shape this pass. `05-tool-model-registry.md` itself was not edited (see
IR-L05/06-006 above).

## Layer 06 regression

```text
full pytest (coverage enabled):     920 passed, 19 xfailed, 0 failed, 100.00% coverage
ruff check .:                        All checks passed
mypy (configured scope):             Success, no issues found in 57 source files
mypy + typing fixtures:              Success, no issues found in 59 source files
schema validation:                   165 passed (unchanged)
Layer-05 ToolRegistry canonical:      9 passed (unchanged) + 7 harness-validation tests (unchanged)
Runtime canonical (regression):      26 passed (unchanged)
Session canonical (regression):      20/20 passed (unchanged)
XFORM canonical (regression):        14/14 passed (unchanged)
Layer-06 canonical:                   10 discovered / 10 executed / 10 passed / 0 deferred (unchanged)
manifest parse + unique-ID audit:    66 / 66 unique (was 65; +1, TOOL-023, the only new row)
```

Every prior Layer-06 rule was independently re-run, not assumed: immediate-outcome skip of
execute/after-hook, execute-outcome-always-reaches-after-hook, the after-hook's five-field
override surface and three-field protection (including the per-listener normalization from the
prior remediation round), N-listener composition and its failure semantics, batch contagion,
run-level default, length-stop's zero-work rule, live-update/late-update suppression (now with the
richer payload), metadata pass-through (`usage`/`added_tool_names`/`namespace`, and now `details`
correctly), and the terminate fold. None of these regressed; the two Layer-06 canonical
placeholder counts, the manifest row count (net `+1`), and the full-suite pass/xfail counts are
the only numbers that changed, and every change is accounted for above.

## Canonical runner audit

Confirmed by direct code reading, not assumption: `tests/conformance/agent_runner.py` was touched
only to update the `tools/update` listener lambda's signature (2 args → 4 args, cosmetic --
matching the new emit shape) and gained no new logic. It still constructs real `ToolDefinition`s,
dispatches through the real `ToolRegistry`/`execute_batch`/`execute_call`, and does not: perform
preflight itself, manually reorder executions, fake completion order, validate schemas instead of
production, merge after-hook results itself, normalize protected fields itself, synthesize missing
error metadata production omitted, or simulate late-update suppression. The two new
`test_batch.py` regression tests for `IR-L06-001` are ordinary pytest unit tests exercising
`execute_batch`/`_preflight`/`_execute_and_finalize` directly -- not part of the YAML canonical
runner, and not a simulation of the barrier: they observe the real, production event stream.

## Cross-language conformance

Not evaluated this pass, by design (PASS 1 is shared/Python only). Rust Layer 06 remains at its
prior certified state (`06-tool-execution-rust-implementation.md`,
`minion-agent@5683fd9`) -- **not modified**. The corrected shared contract (spec + manifest +
canonical) is now the reference PASS 2 (independent Rust re-review) must judge Rust's *current*
implementation against; PASS 3 (Rust remediation) follows only if PASS 2 finds Rust genuinely
diverges from the corrected contract on `IR-L06-001`/`IR-L06-002`/`IR-L06-004` (`IR-L06-003`'s
Rust text and `IR-L05/06-006` were already stated to be Rust-conformant/non-issues by the governing
instruction and this document respectively, but neither was independently re-verified from Rust
source this pass -- PASS 2 should confirm both directly rather than trust either restatement).

## Manifest / traceability

```text
rows: 66 (was 65)
unique IDs: 66 (confirmed, no duplicates)
new row: TOOL-023 (sequential preflight barrier, IR-L06-001)
rows edited (rule text extended in place, no semantic rule removed): TOOL-001, TOOL-005, TOOL-006,
    TOOL-017, TOOL-019, TOOL-021
TOOL-022: still absent as a row; still not cited anywhere current (unchanged from the prior
    remediation round)
```

## Quality gates

```text
full pytest (coverage enabled):     920 passed, 19 xfailed, 0 failed, 100.00% coverage
ruff check .:                        All checks passed
mypy src/minion_agent
    + tests/typing/valid_message_construction.py
    + tests/typing/valid_tool_construction.py:  Success, no issues found in 59 source files
schema validation:                   165 passed
manifest structural/unique-ID validation: 66 / 66 unique
```

Rust gates (`cargo fmt`/`clippy`/`test`/`doc`, `xtask conformance verify`) were **not** run this
pass -- no Rust file was touched, and running them would not exercise anything this pass changed.

## Active findings

```text
PI_PARITY_DEFECT
    IR-L06-002 (Rust AfterToolCallOverride nested-Option API) -- OPEN, Rust-only, deferred to
        PASS 3
    IR-L06-001's Rust half (FuturesUnordered<execute_one> lacks the sequential preflight
        barrier) -- OPEN, deferred to PASS 3
    IR-L06-004's Rust half (immediate/error helper details representation, unverified from
        source this pass) -- OPEN, deferred to PASS 2/3

CONTRACT_ASSURANCE_DEFECT
    none active on the shared/Python side

PARITY_CONSTRAINED_RISK
    none

PI_BEHAVIOR_UNCERTAIN
    none

intentional Minion architectural extensions
    ordered N-listener hook composition (before- and after-hook, unchanged this pass)
    tools/pre-execute argument replacement (unchanged this pass)
    tools/update payload now Pi-equivalent by deliberate adoption (IR-L06-005), not a divergence
```

Zero active findings block the **shared contract or Python**. Three Rust-side findings remain
open by design, awaiting PASS 2/PASS 3.

## Final verdict

```text
Layer 05
    implementation semantics: CERTIFIED / CLOSED (unchanged, no redesign required)
    assurance contradictions: RESOLVED (confirmed already correct; no edit needed this pass)

Layer 06
    shared contract: CORRECTED
    canonical conformance: CORRECTED (regression green; one language-neutral scenario for
        IR-L06-001 explicitly deferred, see that finding's "known gap" note)
    Python: CERTIFIED
    Rust: NOT RE-CERTIFIED -- prior certification stands only against the PRE-correction
        contract; IR-L06-001/002/004's Rust halves remain open until PASS 2/PASS 3
    cross-language: NOT CLOSED -- gated on PASS 2 (independent Rust review of this corrected
        contract) and, if needed, PASS 3 (Rust remediation)

Layer 07
    NOT STARTED
```

This intentionally does **not** match the instruction's own "Expected successful verdict" template
verbatim (`Layer 06 — CERTIFIED / CLOSED`), because that template describes the state after **all
three passes** complete, and this document records only PASS 1. Declaring Layer 06 cross-language
closed here, with three Rust-side findings still open and zero Rust code reviewed or changed,
would be exactly the "mask the problem" / "certify while a known Pi mismatch remains" outcome the
governing instruction explicitly forbids.

## Commits / artifacts

```text
minion-agent (code):     see covering commit -- batch.py, execute.py, result.py, pi-parity-
                          manifest.yaml, and 5 touched test files
minion-agent-docs (docs): see covering commit -- spec/tools.md, this artifact
```

## Next action

**PASS 2**: an independent Rust review of the corrected shared contract
(`spec/tools.md` + `pi-parity-manifest.yaml`, this candidate) against Rust's *existing* Layer-06
implementation, specifically judging:

```text
IR-L06-001  does Rust's FuturesUnordered<execute_one(...)> preflight sequentially, barrier, then
            execute concurrently -- or does it still preflight every call concurrently?
IR-L06-002  does Rust's AfterToolCallOverride expose Option<Option<T>>, and if so, does that
            genuinely permit an override Pi cannot express?
IR-L06-003  confirm directly from Rust source that the unknown-tool text already matches
            `Tool {name} not found` exactly (not re-verified this pass)
IR-L06-004  confirm directly from Rust source what the immediate/error helper's `details`
            representation actually is (not re-verified this pass)
IR-L06-005  Rust's own `ToolExecutionUpdate` payload, aligned with the Option-A decision recorded
            here (new alignment work, not a "fix," since Rust built its own event type
            independently)
```

Do **not** implement Rust in response to this document. **PASS 3** (Rust remediation) follows only
after PASS 2 records its verdict.
