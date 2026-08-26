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

**This "Next action" was held before PASS 2 began.** See PASS 1B below.

---

# PASS 1B — Shared/canonical closure (2026-08-26)

**Why PASS 2 was held:** the PASS 1 report above declared `CONTRACT_ASSURANCE_DEFECT: 0` on the
shared/Python side while two of its own sections explicitly said the opposite: `IR-L06-001`'s
"known gap" note said outright that "a language-neutral YAML canonical scenario was not added,"
and `IR-L06-005`'s payload decision had no canonical evidence at all -- only Python unit tests.
Both are newly discovered, newly corrected shared cross-language rules; leaving either without
executable, language-neutral evidence reproduces the exact failure mode that let the original
defects through certification unnoticed in the first place: Python green, Rust green, the existing
ten canonical scenarios green, while both implementations disagreed with Pi. A third gap was found
independently during this pass, not flagged by PASS 1 at all: `definition.py`'s own `ToolFn`
docstring still carried the stale "no `AbortSignal`-equivalent type exists... in either language"
claim PASS 1's `IR-L05/06-006` section claimed to have already fully swept -- PASS 1's grep had
been scoped to `spec/`/`assurance/layers/` only and never searched
`minion-agent-python/src/` at all.

## BLOCKER A closed — IR-L06-001 canonicalized

The conformance schema (`conformance/schema/agent-scenario.schema.json`) gained one new
observation, `expect_tool_trace`: an ordered list of `[stage, tool_call_id]` entries
(`start`/`before`/`execute`/`end`), populated by four small, unconditional, always-installed
listeners in `tests/conformance/agent_runner.py` -- two trivial `EMIT`-mode listeners on
`tools/execution-start`/`tools/execution-end`, one waterfall listener on `tools/pre-execute`
(registered `prepend=True` so it always wraps the entire before-hook chain, recording its marker
only *after* `next_()` settles -- so it fires exactly once a call's before-hook stage has fully
resolved, whatever the scenario's own listeners decided, without ever deciding anything itself),
and one line inside the tool-stub's own `execute()` body recording the moment it starts running.
None of these four listeners choose scheduling, reorder anything, or decide any outcome -- they
only append to a list as production emits real events.

No timing/sleep primitive was needed, per the governing instruction's own suggested shape: the new
scenario `parallel-preflight-settles-sequentially-before-execute.yaml` gives call `t2` a
before-hook that unconditionally blocks it (the existing `block`/`only_tool` listener primitive,
unchanged) while `t1` is an ordinary tool that reaches `execute()`. Pinned Pi's own semantics
require `t2`'s immediate outcome to settle -- and its `tool_execution_end` to fire -- strictly
before `t1` is allowed to reach `execute()`, regardless of source order:

```text
expect_tool_trace:
  [start, t1]
  [before, t1]
  [start, t2]
  [before, t2]
  [end, t2]
  [execute, t1]
  [end, t1]
```

**RED confirmed:** the pre-fix `execute.py`/`batch.py` (temporarily restored via
`git checkout 5683fd9 -- ...`, then reverted back to the corrected HEAD) produced `execute(t1)`
immediately after `before(t1)` -- **before** `start(t2)`/`before(t2)`/`end(t2)` ever ran -- because
wrapping each call's entire pipeline in one `asyncio.gather` let `t1`'s whole synchronous pipeline
(nothing in it ever awaits a real suspension point) run to completion in a single scheduler step
before `t2`'s task was ever given a turn. **GREEN confirmed** against the corrected implementation,
producing exactly the trace above. Both runs are the actual pytest output, not asserted from
memory.

The pre-existing `tool-batch-parallel` canonical scenario (unchanged) remains the evidence that
phase 2 (execute/finalize once every call has survived preflight) stays genuinely concurrent --
the fix did not accidentally serialize execution while fixing preflight. `pi-parity-manifest.yaml`'s
`TOOL-023` row now cites both scenarios together, as the governing instruction asked, "stronger
than one complicated timing scenario."

Runner-thinness, explicitly re-confirmed: the runner does not compute the barrier, does not decide
which call executes when, and does not reorder or synthesize any trace entry -- every entry is a
direct, unmodified record of a real production event or the tool stub's own body executing.

**Verdict:** `IR-L06-001` shared canonical **RESOLVED**. (Python and shared contract were already
`RESOLVED` from PASS 1; only the shared-canonical half was open.)

## BLOCKER B closed — IR-L06-005 canonically protected

`conformance/schema/agent-scenario.schema.json`'s `expect_updates` item shape changed from a bare
`[tool_call_id, partial]` pair (which could not express `tool_name`/`arguments` at all) to an
object: `{tool_call_id, tool_name, arguments, partial}`. The existing `late-tool-update-ignored`
scenario (its only consumer) was extended rather than duplicated, per the governing instruction's
own preference: its `chatty` tool now declares `prepare_arguments: {set: {prepared: true}}`, and
the provider script's tool call carries `{raw: 1}`. `prepared` only exists after preparation, so
asserting

```yaml
expect_updates:
  - tool_call_id: t1
    tool_name: chatty
    arguments: { raw: 1 }
    partial: live
```

proves the update event reports the call's ORIGINAL arguments (no `prepared` key), not the
prepared/merged value `execute()` itself receives -- both halves of the contract (execution uses
prepared args; the event payload uses original args) are proven by one small, clear fixture,
exactly as the governing instruction's §11 preferred.

**Verdict:** `IR-L06-005` shared canonical **RESOLVED**.

## BLOCKER C closed — IR-L05/06-006 re-verified against actual source, and found genuinely stale

Independently re-read, not re-grepped-narrowly: `minion-agent-python/src/minion_agent/tools/
definition.py`'s `ToolFn` type alias docstring, in full, at candidate `f73057e`. It said, verbatim:

```text
The `signal` (cancellation) parameter remains unrealized -- no `AbortSignal`-equivalent type
exists anywhere in this codebase yet, in either language; that gap is assurance Layer 09's, not
Layer 06's, to close.
```

This is the exact stale claim PASS 1's `IR-L05/06-006` section claimed was "already fully
corrected... before this pass began" -- a genuine miss, caused by scoping that pass's search to
`spec/`/`assurance/layers/` and never searching `minion-agent-python/src/` itself. **Corrected**
to the accurate asymmetry (Python has no `AbortSignal`-equivalent abstraction at all yet; certified
Rust Layer 05 already reserves `ToolExecutionSignal`/`ToolExecutionRequest.signal` structurally,
unexercised; Layer 06 certifies non-cancelled semantics; Layer 09 owns cancellation).

A second, related staleness was found and fixed while re-checking as instructed:
`pi-parity-manifest.yaml`'s `TOOL-009` row still said, present-tense, "today's Python dispatch
realizes only a (params)/(params, on_update) subset, no tool_call_id or cancellation signal
parameter" -- true when Layer 05 certified, false since Layer 06 closed the `tool_call_id` half.
Rephrased historically, per the governing instruction's own preferred pattern: "Layer 05 initially
represented only a subset; Layer 06 subsequently closed tool_call_id wiring; signal behavior
remains deferred, asymmetrically."

A third occurrence was found in `spec/tools.md`'s own Layer-05 tool-definition table (`` today's
dispatch realizes only a (params)/(params, on_update) subset ``) and corrected the same way.

An exhaustive re-search (not a narrow one) across `minion-agent-python/src/`, `pi-parity-
manifest.yaml`, and `minion-agent-docs/spec/` for `` today's ``, "does not receive", "no
tool_call_id", "realizes only... subset", and the `AbortSignal` phrase found no further
occurrences outside corrective/historical quoting (the manifest's own `TOOL-018` row, this
artifact's own PASS 1 section, and the historical `06-tool-execution-rust-review.md` artifact,
correctly preserved as history).

**Verdict:** `IR-L05/06-006` **RESOLVED** -- for real this time, with the miss disclosed rather
than silently corrected. `05-tool-model-registry.md` itself remains untouched, correctly, since it
is a dated historical certification report, not a current-state document.

## Canonical inventory (updated)

```text
Layer-06 canonical (dynamically discovered, not hard-coded):
    discovered  11  (was 10; +1: parallel-preflight-settles-sequentially-before-execute)
    executed    11
    passed      11
    deferred     0

schema validation:  166 passed (was 165; +1, the new scenario file)
```

`an-unknown-tool-does-not-serialize-a-batch` (pre-existing, not part of the "10/11 owned"
placeholder-derived inventory) was extended with `expect_messages` asserting the exact unknown-tool
text and `details: {}` on all three of its tool results -- closing `IR-L06-003`'s and
`IR-L06-004`'s remaining "canonical, not just Python-unit" gaps without adding a new fixture.

## Runner audit (after extension)

```text
Does the runner perform the preflight barrier?         NO
Does the runner decide which tool executes?            NO
Does the runner synthesize end ordering?                NO
Does the runner rewrite tool update args/name?          NO
Does the runner synthesize details={}?                  NO
Does the runner rewrite unknown-tool error text?        NO
```

Confirmed by direct code reading: the four trace-recording listeners and the `details`/`arguments`
projections added to `agent_runner.py` only ever read a real production object's own field
(`m.details`, the real `ToolResult.to_message()`'s text, the real `TOOLS_UPDATE` emission's own
arguments) or append to a list the instant a real event fires. No new logic decides an outcome,
reorders anything, or fabricates a value the production seam did not itself produce.

## Re-run gates (after PASS 1B changes)

```text
full pytest (coverage enabled):     922 passed, 19 xfailed, 0 failed, 100.00% coverage
ruff check .:                        All checks passed
mypy (configured scope + typing fixtures): Success, no issues found in 59 source files
schema validation:                   166 passed (was 165)
manifest parse + unique-ID audit:    66 / 66 unique (unchanged count from PASS 1; TOOL-005/009/
                                      017/019/021/023 rule text extended in place, no rows added
                                      or removed this pass)
Runtime canonical (regression):      26 passed (unchanged)
Session canonical (regression):      20/20 passed (unchanged)
XFORM canonical (regression):        14/14 passed (unchanged)
Layer-05 ToolRegistry canonical:      9 passed (unchanged) + 7 harness-validation tests (unchanged)
Layer-06 canonical:                   11 discovered / 11 executed / 11 passed / 0 deferred
```

## Finding status after PASS 1B

```text
IR-L06-001
    shared contract   RESOLVED
    shared canonical  RESOLVED
    Python            RESOLVED
    Rust              OPEN

IR-L06-002
    Python            conformant (already, unchanged)
    shared rule       RESOLVED (manifest states the exact nullish rule precisely enough for a
                       conforming Rust type; no canonical fixture was added specifically for this
                       finding, since it was not raised as a PASS-1B blocker and Python's own
                       structural conformance is proof enough on this side)
    Rust              OPEN

IR-L06-003
    shared canonical  RESOLVED
    Python            RESOLVED
    Rust              TO VERIFY (not independently re-verified from Rust source this pass)

IR-L06-004
    shared canonical  RESOLVED
    Python            RESOLVED
    Rust              OPEN

IR-L06-005
    disposition       Pi payload ADOPTED (Option A)
    shared canonical  RESOLVED
    Python            RESOLVED
    Rust              OPEN

IR-L05/06-006
    current normative/source documentation   RESOLVED (three occurrences found and fixed this
                                              pass; PASS 1's own claim of completeness was wrong,
                                              disclosed here rather than silently patched over)
```

## Active shared/Python findings (after PASS 1B)

```text
PI_PARITY_DEFECT                 0
CONTRACT_ASSURANCE_DEFECT        0
PI_BEHAVIOR_UNCERTAIN            0
PARITY_CONSTRAINED_RISK          0
```

Three Rust-side findings (`IR-L06-001`, `IR-L06-002`, `IR-L06-004`'s Rust halves) and one
unverified claim (`IR-L06-003`'s Rust text) remain open; none of them block declaring the
shared/Python side ready, per the governing instruction's own explicit rule that Rust findings
"remain separately open and do not prevent declaring READY FOR INDEPENDENT RUST REVIEW."

## Verdict (supersedes PASS 1's own, for the shared/Python side only)

```text
Python Layer 06                CERTIFIED
Shared Layer-06 contract       READY FOR INDEPENDENT RUST REVIEW
Rust Layer 06                  NOT RE-CERTIFIED / IN_REMEDIATION
Rust modified                  NO
Layer 07                       NOT STARTED
```

## Next action

**PASS 2**: an independent Rust review of this now-canonically-complete shared contract
(`spec/tools.md` + `pi-parity-manifest.yaml` + the corrected/added canonical scenarios) against
Rust's existing Layer-06 implementation. The judgment list under PASS 1's own "Next action" above
still applies unchanged; PASS 2 now also has `parallel-preflight-settles-sequentially-before-
execute` and the extended `late-tool-update-ignored`/`an-unknown-tool-does-not-serialize-a-batch`
scenarios available to run against Rust directly, rather than only Python-side unit-test evidence
to trust. Do not implement Rust in response to this document.

Do **not** implement Rust in response to this document. **PASS 3** (Rust remediation) follows only
after PASS 2 records its verdict.

---

# PASS 2.5 — `CA-L06-007` narrow correction (2026-08-26)

## PASS-2 rejection reason

The independent Rust review of PASS 1B's corrected contract
(`assurance/layers/05-06-pass2-independent-rust-review.md`, commit
`88e479fc4a987d486ee12b18609243f868828fa7`) confirmed `IR-L06-003`/`IR-L05/06-006` resolved and the
`parallel-preflight-settles-sequentially-before-execute`/`late-tool-update-ignored` canonical
evidence sound and language-neutral, but found one new blocking defect in the shared evidence
itself, not in either implementation:

```text
CA-L06-007  CONTRACT_ASSURANCE_DEFECT

an-unknown-tool-does-not-serialize-a-batch's PASS-1B revision asserted details: {} on ALL THREE
of its tool results -- the generated unknown-tool error (correct) AND its two ordinary
successful results (unjustified: their fixtures declare only result.text, and neither Pi nor the
canonical schema supplies a details value for an undeclared successful outcome). A runner
satisfying that assertion would have had to invent a host default and pass it off as shared
semantics -- exactly the kind of accidental, unexamined divergence this whole assurance process
exists to catch.
```

`Layer-06 shared contract: REJECTED`; `Python Layer 06: CERTIFIED` (unaffected); `Rust Layer 06:
IN_REMEDIATION`; `Layer 06 cross-language: NOT CLOSED`.

## Pi source evidence (re-confirmed)

Re-read directly, not re-trusted from PASS 1's own prior citation:

- `packages/agent/src/types.ts::AgentToolResult<T>` -- `details: T` is **required**, generic over
  the tool's own detail type. Nothing in the interface or its surrounding code assigns a default.
- `packages/agent/src/agent-loop.ts::createErrorToolResult` -- the ONE place Pi's own execution
  code supplies `details: {}`, unconditionally, for a Layer-06-synthesized error result.
- `packages/agent/src/agent-loop.ts::createToolResultMessage` -- copies `finalized.result.details`
  verbatim, with no conditional logic, for every outcome, error or success alike.

Confirmed exactly: **generated-error `details` is always `{}`; a successful result's `details` is
whatever the tool itself returned; Pi never synthesizes a `{}` for an undeclared successful
result.** The old incorrect assumption -- present in PASS 1B's own canonical fixture and in
`spec/tools.md`/`TOOL-021`'s prose -- was that "empty-but-present, never absent" applied uniformly
to every tool result regardless of outcome, when it in fact only describes Layer 06's own
error-generation helper.

## Spec repair

`spec/tools.md`'s `details` paragraph (batch-execution section) rewritten to state the two halves
explicitly and separately: generated errors always get pinned Pi's `{}` via
`createErrorToolResult`; successful results preserve exactly what the tool returned, with Layer 06
never synthesizing or defaulting a value for one that declares none. The prior wording's "every
tool that never sets details" phrase -- the exact source of the conflation -- was removed.

## TOOL-021 repair

`pi-parity-manifest.yaml`'s `TOOL-021` row rewritten the same way: the two halves stated
separately, the erroneous canonical-evidence claim ("asserts `details: {}` on all three of its
tool results... proving the empty-but-present state survives identically for both error and
success paths") corrected to describe the actual, narrower, correct evidence. A new test citation,
`test_generated_error_details_and_tool_supplied_details_are_distinct`, added.

## Canonical repair

`conformance/agent/an-unknown-tool-does-not-serialize-a-batch.yaml`: the `details: {}` assertions
removed from the `slow` and `quick` successful results' `expect_messages` entries (their keys
omitted entirely, not replaced with `details: null` or any other value); the generated error's
`details: {}` assertion retained unchanged. The scenario's own description updated to record why,
attributing the correction to the independent PASS-2 review by its finding ID.

No schema or runner change was needed for this repair: `test_agent_conformance.py`'s
`expect_messages` matcher already treated an omitted `details` key in a fixture's expectation as
"not part of this assertion" (`if "details" in expected: ...`, with no `else` branch), never as an
implicit `{}` or `null` expectation -- confirmed by direct code reading before deciding no change
was required, per the governing instruction's own explicit preference for verifying this rather
than assuming it.

## Runner audit

```text
runner supplies successful details={}          NO
runner synthesizes generated error {}           NO -- production (createErrorToolResult's Python
                                                 equivalent, text_result's ToolResult default)
                                                 supplies it; the runner only reads
                                                 ToolResultMessage.details off the real message
production generates error {}                   YES (confirmed: text_result's ToolResult.details
                                                 default is {}, unchanged from PASS 1B)
runner thin                                     YES
```

All four PASS-1B/PASS-2 runner-thinness guarantees re-confirmed unchanged: no preflight barrier,
no unknown-tool text rewriting, no update-payload rewriting, no synthesized ordering.

## Python result behavior

No production code changed this pass. `ToolResult.to_message()`'s PASS-1B fix (`details=
self.details`, a straight pass-through, no collapsing) is retained exactly as is -- correct for
both halves of the rule, since it neither collapses a generated error's `{}` nor invents a value
for a successful result that has none. `ToolResult.details`'s own dataclass default (`{}`) also
remains unchanged: it is a Python API convenience for constructing a `ToolResult` without
mentioning `details` at all, not a claim about what pinned Pi requires for a successful outcome --
this distinction is now stated explicitly in `spec/tools.md`/`TOOL-021` rather than left implicit.

A new focused regression, `test_generated_error_details_and_tool_supplied_details_are_distinct`
(`tests/tools/test_execute.py`), proves both halves through the real `execute_call` pipeline in
one test: an unknown-tool call (generated error) carries `{}`; a tool that explicitly returns
`ToolResult(..., details={"source": "tool"})` carries that value unchanged. No parity test was
added asserting Python's own host-level `{}` default for an otherwise-unspecified successful
result, per the governing instruction's explicit instruction not to.

## Quality gates

```text
full pytest (coverage enabled):     923 passed, 19 xfailed, 0 failed, 100.00% coverage
                                     (was 922; +1, the new CA-L06-007 regression test)
ruff check .:                        All checks passed
mypy (configured scope + typing fixtures): Success, no issues found in 59 source files
schema validation:                   166 passed (unchanged -- no schema file touched this pass)
manifest parse + unique-ID audit:    66 / 66 unique (unchanged row count; TOOL-021 rule text
                                      corrected in place, no rows added or removed)
Runtime canonical (regression):      26 passed (unchanged)
Session canonical (regression):      20/20 passed (unchanged)
XFORM canonical (regression):        14/14 passed (unchanged)
Layer-05 ToolRegistry canonical:      9 passed (unchanged) + 7 harness-validation tests (unchanged)
Layer-06 canonical:                   11 discovered / 11 executed / 11 passed / 0 deferred
                                      (unchanged count from PASS 1B -- no scenario added or
                                      removed, one existing scenario's assertions corrected)
```

`parallel-preflight-settles-sequentially-before-execute`, `late-tool-update-ignored`, and
`an-unknown-tool-does-not-serialize-a-batch` were each individually re-run and confirmed passing
after this pass's changes, not merely included in the aggregate count above.

## `CA-L06-007` closure

```text
spec: error details={} only for generated errors                YES
spec: successful details are tool-supplied                      YES
TOOL-021: same distinction                                      YES
canonical: generated error asserts {}                            YES
canonical: undeclared successful details are not asserted        YES
runner: no host default injected as shared semantics             YES (confirmed: none was)
Python: generated error {} preserved                              YES
schema/canonical: language-neutral                                YES (no schema change was
                                                                   needed; existing omitted-key
                                                                   semantics already correct)

CA-L06-007                                                        RESOLVED
```

## Rust findings carried forward, unchanged

```text
IR-L06-001   OPEN   missing sequential preflight barrier
IR-L06-002   OPEN   extra after-hook clear states (Option<Option<T>>)
IR-L06-003   RESOLVED / ALREADY CONFORMANT
IR-L06-004   OPEN   generated error details absent rather than {}
IR-L06-005   OPEN   update payload missing original args
```

None of these were touched, fixed, or reclassified from the shared side this pass.

## Verdict

```text
Layer 05                        CERTIFIED / CLOSED (unaffected)
Python Layer 06                 CERTIFIED
Shared Layer-06 contract        APPROVED FOR RUST REMEDIATION
CA-L06-007                       RESOLVED

active shared PI_PARITY_DEFECT           0
active shared CONTRACT_ASSURANCE_DEFECT  0
active shared PI_BEHAVIOR_UNCERTAIN      0

Rust Layer 06                    IN_REMEDIATION
Layer 06 cross-language          NOT CLOSED
Layer 07                         NOT STARTED
```

## Next action

**PASS 3**: Rust Layer-06 remediation against this now-fully-approved shared contract, addressing
`IR-L06-001`, `IR-L06-002`, `IR-L06-004`, and `IR-L06-005` (all still open, all Rust-only). No
further broad shared/canonical contract review is required unless PASS 3's own implementation work
uncovers genuinely new semantic evidence -- this narrow correction closed the one gap PASS 2 found;
it does not reopen anything PASS 2 already approved.
