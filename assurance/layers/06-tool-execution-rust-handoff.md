# Layer 06 (Tool Execution Pipeline) — Rust Implementation-Owner Review Package

**Prepared:** 2026-08-26
**Prepared by:** Claude (Python/shared-contract owner, per the adopted workflow)
**Why this exists:** Layer 06 (per `process/implementation-conformance-workflow.md` §6 —
**Tool execution pipeline**, following certified, cross-language Layer 05) is the next assurance
layer. This package requests Rust's independent implementation-owner review of the Python/shared
candidate before any Rust implementation begins.

**Reviewed commits (delta candidate):** see the covering commit messages in `minion-agent` and
`minion-agent-docs`, committed on top of `minion-agent@8b5b0045d7a53a4c04a1ff492115c3a41dd3bf09`
(Rust Layer 05 cross-language certified) and `minion-agent-docs@8c5a77e2962ec01f7d32e768503f022562b2738b`.

**Pinned Pi revision:** `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged).

**Do not modify Rust in response to this package without first recording a verdict.**

---

## 1. Scope

**In scope for this review:** tool resolution, `prepare_arguments` invocation ordering and
capability shape, argument validation's boundary (not its algorithm — see §4), before/after
hooks' observable semantics (not Minion's own extension mechanism — see §5), `execute` invocation
(`tool_call_id`, live updates, late-update suppression), execution-mode resolution and contagion,
parallel/sequential batch scheduling and its two orderings, per-call failure isolation, the
length-stop special case, `ToolResultMessage` construction, and pass-through preservation of
`usage`/`details`/`added_tool_names`/`namespace`.

**Explicitly out of scope** (do not review as if these were being certified):

```text
The full Agent run loop, prompt()/continue() lifecycle                -- later Agent-loop layer
Steering/follow-up message injection                                  -- later Agent-loop layer
shouldStopAfterTurn/prepareNextTurn                                    -- later Agent-loop layer
Whether terminate=true suppresses/continues the next model turn        -- later Agent-loop layer
Cancellation/abort propagation through execute/hooks                   -- assurance Layer 09
Provider-specific constrained-sampling enforcement                     -- Real Providers, Layer 11
Layer 05 (Tool model + registry) itself -- already cross-language      -- not reopened
  certified; consumed unmodified
```

---

## 2. What changed — full detail in `assurance/layers/06-tool-execution.md`

Ten findings/requirement additions (`TOOL-001`..`TOOL-006` pre-existing rows, corrected and given
real implementation pointers for the first time; `TOOL-017`..`TOOL-021` new rows), plus one
genuine `PI_PARITY_DEFECT` found and repaired within this same pass (the after-hook previously
ran unconditionally on every outcome, including ones that never reached `execute()`; a second,
previously-uncaught after-hook exception path was also fixed). Full Pi source citations are in
the assurance document §§2–9 — this package does not repeat them; verify against the pinned
source directly, not against this summary.

---

## 3. Rust's required independent verdict, per question — do not trust Python's classification

1. **Does the per-call pipeline match pinned Pi's exact stage order and skip conditions?** Re-read
   `packages/agent/src/agent-loop.ts::prepareToolCall`/`executePreparedToolCall`/
   `finalizeExecutedToolCall` directly. Confirm: `prepareArguments` runs strictly before
   validation; the before-hook, prepare, and validation share one failure class ("immediate,"
   never reaching `execute()` or the after-hook); an `execute()` failure is a *different* outcome
   class that still reaches the after-hook; an after-hook exception replaces the entire prior
   result, not merging with it.

2. **Are the two orderings (`tool_execution_end` completion order, `ToolResultMessage` source
   order) both genuinely honored simultaneously in a parallel batch?** Confirm from
   `executeToolCallsParallel` directly — the completion-order guarantee comes from emitting
   `tool_execution_end` inside each per-call async closure (fires whenever that closure's own
   work finishes); the source-order guarantee comes from `Promise.all`'s own input-order
   preservation of its resolved array, not a manual sort. Confirm Python's
   `asyncio.gather` provides the equivalent structural guarantee, and that this package's
   evidence (`parallel-tool-completion-vs-message-order`) actually exercises both orders
   distinguishably (a call listed first finishing second).

3. **Is the contagion rule genuinely batch-level, not per-tool grouping?** Confirm
   `executeToolCalls` picks between `executeToolCallsSequential`/`Parallel` exactly once per
   batch (`config.toolExecution === "sequential" || hasSequentialToolCall`), and that DSH-style
   partial grouping around an exclusive call is explicitly NOT what pinned Pi does.

4. **Is the length-stop rule complete?** Confirm `failToolCallsFromTruncatedMessage` skips
   resolution/preparation/validation/hooks/`execute()` entirely for every call — not merely
   "doesn't call execute" — and that `terminate` is unconditionally `false`, never routed through
   `shouldTerminateToolBatch`. Confirm the exact literal error-message text this package
   reproduces (`"Tool call \"{name}\" was not executed: the response hit the output token limit,
   so its arguments may be truncated. Re-issue the tool call with complete arguments."`) against
   the pinned source string exactly.

5. **Is the validation-algorithm boundary correctly scoped?** Confirm
   `packages/ai/src/utils/validation.ts::validateToolArguments` is genuinely TypeBox-specific
   coercion machinery, not a language-neutral algorithm this package should have reproduced.
   Independently judge whether Rust's own idiomatic validation approach (whatever shape that
   takes) can satisfy the *observable* contract (arguments conforming to schema succeed; a
   pydantic-equivalent-typed schema in Rust validates for real; a raw/dynamic schema
   representation may not) without needing to mirror TypeBox's exact coercion semantics.

6. **Is `signal`'s deferral to Layer 09 justified, not an evasion?** Confirm directly that no
   `AbortSignal`-equivalent type exists anywhere in this codebase yet (`minion-agent-rust` too) —
   if one has since been added, this deferral needs re-litigating, not silently accepted.

7. **Does canonical evidence test real registry/executor/event behavior?** Read
   `tests/conformance/agent_runner.py` directly. Confirm every Layer-06-owned scenario drives the
   real `ToolRegistry`/`Context`/`execute_batch`/`execute_call`/`execute_length_stop_batch`/event
   seam, and that the runner's new stub capabilities (`parameters: {requires: [...]}`,
   `prepare_arguments`, `emits_updates`/`late_update`, the `raise` listener action) are
   declarative fixture construction, not a parallel execution-semantics implementation.

8. **Can Rust implement the contract idiomatically without Python-shaped artifacts?** Specifically
   assess: can Rust's own idiomatic execution design express "batch-level contagion,
   completion-order events + source-order messages, immediate-vs-executed after-hook skip,
   late-update suppression" without needing to mirror Python's `asyncio.gather`/closure-capture
   mechanics? Nothing in this package's own architecture should require it.

---

## 4. Fresh Python evidence to reproduce, not merely trust

```text
full pytest (coverage enabled):     903 passed, 19 xfailed, 0 failed, 100.00% coverage
ruff check .:                        All checks passed
mypy (configured scope):             Success, no issues found in 57 source files
mypy + typing fixtures:              Success, no issues found in 59 source files
schema validation:                   165 passed (unchanged)
Layer-05 ToolRegistry canonical:      9 passed (unchanged) + 7 harness-validation tests (unchanged)
Runtime canonical (regression):      26 passed (unchanged)
Session canonical (regression):      20/20 passed (unchanged)
XFORM canonical (regression):        14/14 passed (unchanged)
Layer-06 canonical (new):            9 discovered / 9 executed / 9 passed / 0 deferred
manifest parse + unique-ID audit:    65 / 65 unique
```

Reproduce via (from `minion-agent-python/`): `uv run pytest`, `uv run ruff check .`,
`uv run mypy src/minion_agent`, `uv run mypy src/minion_agent tests/typing/valid_message_
construction.py tests/typing/valid_tool_construction.py`.

---

## 5. Cross-language hazards for Rust's own future implementation

```text
async task completion ordering        Python: asyncio.gather array-order guarantee; Rust's own
                                       concurrency primitive (e.g. futures::future::join_all)
                                       needs the equivalent input-order guarantee -- confirm it
                                       has one before relying on it the same way
exception vs. Result conversion       Every Pi "throw" becomes a Python exception caught at a
                                       specific pipeline boundary; Rust will have typed Result/
                                       Err values instead -- the BOUNDARY (which stage's failure
                                       reaches the after-hook, which doesn't) is the contract,
                                       not the language mechanism
callback lifetime / late updates      Python uses a captured-closure boolean flag
                                       (accepting_updates) set false once execute()'s own future
                                       resolves; Rust must express the same "after this call's
                                       own future/task completes, further update calls are inert"
                                       rule without necessarily using a flag
JSON schema validation differences    Deliberately NOT reproduced in Python beyond pydantic-
                                       backed tools (see package §5 item 5) -- Rust does not need
                                       to match TypeBox's exact coercion algorithm either
usage/details optionality             usage: Option<Usage>, details: dynamic/opaque payload,
                                       added_tool_names: omitted-when-empty (not null, not [])
                                       on the wire -- already an established Layer-02 convention,
                                       unmodified by this layer
event sequencing                      tool_execution_start always precedes resolution;
                                       tool_execution_end always follows the after-hook (when it
                                       runs) -- both fire exactly once per call regardless of
                                       outcome, including length-stop and unknown-tool
source-order reconstruction           Never a post-hoc sort; must fall out of the concurrency
                                       primitive's own structural ordering guarantee
```

---

## 6. Explicitly out of scope for this package

- Layer 05 (Tool model + registry) — already cross-language certified, not reopened.
- Layer 07 (Agent run loop), Layer 09 (cancellation), Layer 11 (Real Providers) — not started,
  not part of this review's verdict.

## 7. Expected outcome

```text
LAYER 06 SHARED CONTRACT
    APPROVED
```

or a precise rejection naming exactly which field, rule, or boundary is not language-neutral or
not Pi-compatible. If approved, Rust's own implementation-timing adjudication (required now vs.
explicitly deferred) follows, per the same review-before-remediation workflow used at every prior
layer this session — this package does not presume that answer.
