# L08-D001 — Optional prompt assembler at the request snapshot (Layer 08 delta)

**Status:** contract APPROVED and merged; Python implementation candidate (§7) for independent review. Rust:
NOT_IMPLEMENTED.

**Classification:** `MINION_EXTENSION`, additive. With no assembler installed, the certified
behaviour is unchanged.

**Requirement served:** `HAR-016` (WP-14.2, `minion-agent#159`), "the textual tool section and the
request tool schemas derive from one `ctx.tools` visible-tool snapshot".

**Governance:** Owner decision `PP-14-9`, Option A, recorded verbatim at `minion-agent#159`
issuecomment-6057640884. It authorizes this delta in both bindings, implementation only after an
independent contract review. It sets this STOP condition: *"If the proposed interface cannot
preserve existing snapshot/override semantics, return with evidence and alternatives for Owner
decision rather than broadening the delta."*

**Normative text:** `spec/agent.md`, Layer 08, "Optional prompt assembler".

## 1. Why Layer 08

- **What Layer 08 does today:** the certified driver takes the run's `RunContext` once at run start
  (`L08-R001`). Each request then builds its tool schemas from `RunContext.tools` and its system
  text from `RunContext.system_prompt`, or from the per-step override.
- **Why nothing else can guarantee it:** `ctx.tools` has no change notification. Any prompt
  assembled outside the driver is assembled from a different read of the registry than the one the
  request uses.
- **Pi's equivalent:** an eager rebuild (C-11). Minion has no trigger for one.

## 2. Requirement map (Owner decision `PP-14-9`)

| # | Owner requirement | Delta rule |
|---|---|---|
| 1 | The assembler receives the same, stable tool snapshot used for execution and the schemas | `tools` is the request's own `RunContext.tools` |
| 2 | Assembly does not re-read the registry | An obligation on the assembler. It is witnessed for Layer 14's assembler, and the driver passes no registry |
| 3 | Registry changes after the snapshot do not alter the active execution snapshot | The existing `L08-R001` rule, extended to the prompt, with witnesses |
| 4 | Existing snapshot, `prepareNextTurn` and override semantics are preserved | Unchanged; the override bypasses the assembler; listeners see the base (§3) |
| 5 | With no assembler, behaviour is unchanged | The rules are inert; the existing suites pass unmodified |
| 6 | The interface is generic, with no Layer 14 dependency | `assemble(base, tools) -> string` |
| 7 | Deterministic failure, never a partial pair | Nothing is sent and no header is recorded; the run settles through `handleRunFailure` |
| 8 | Positive, negative and concurrency witnesses | Listed in the spec section |

## 3. Design choice for review: assemble at request build, not into `RunContext`

**Rejected alternative.** Assemble when the snapshot is *captured*, and store the result in
`RunContext.system_prompt`: once at run start, and again after a `prepareNextTurn` replacement.

**Why it was rejected:**
- After a replacement, a re-assembly would need a base, but the replacement's `system_prompt` would
  already be assembled. That means either double assembly or a second, hidden "base" field.
- A replacement that intentionally sets a final prompt would be silently re-assembled, which
  changes `prepareNextTurn` semantics (Owner requirement 4).
- In-place growth through `added_tool_names` happens after capture. It would leave the stored
  prompt stale relative to the next request's schemas.

**The chosen rule.** Assemble at request build from `(RunContext.system_prompt, RunContext.tools)`.
- **Why it works:** it avoids all three problems. The request is the only point where the schemas
  are final.
- **The observable consequence, for review:** with an assembler installed, `RunContext.system_prompt`
  is the base. A `prepareNextTurn` listener therefore reads and replaces the base, not the assembled
  text. Without an assembler, the two are the same thing, as today.
- **If the reviewer judges** that this changes certified `prepareNextTurn` semantics beyond what
  requirement 4 allows, the STOP condition applies, and this returns to the Owner with these two
  alternatives.

## 4. Impact on certified Layer 08 evidence

- **No assembler (every existing caller):** the code path is identical, and so are the header
  bytes. All certified Layer 08 canonical cases and Python and Rust suites must pass unmodified.
  Any change to an existing expectation is a defect in the implementation, not in the contract.
- **New witnesses:** added in both bindings (the spec section).
- **Certification:** the Layer 08 certification is extended by this delta's own review and closure.
  It is not reopened.

## 5. Implementation scope (after contract approval)

- **Python** (`minion_agent/agent_loop`):
  - an optional `prompt_assembler` driver collaborator, settable through the loop factory;
  - the request-build step in `_run_step` calls it as specified, before `record_header`;
  - the failure path reuses the existing `except Exception` → `_settle_run_failure`.
- **Rust:** the equivalent seam on the driver, under the same contract. It is implemented by the
  Rust owner after review.
- **Layer 14 (WP-14.2):** the HAR-015 composer is the first assembler. It is a separate work
  package and is not part of this delta.

## 6. Requested review

Independent contract-delta review of `spec/agent.md` "Optional prompt assembler" and this record.
Specifically:
1. Is §3's choice within Owner requirement 4, or a semantic change needing the Owner?
2. Is the failure rule correct against the certified `handleRunFailure` seam, including a failure
   on a later turn?
3. Are the planned witnesses sufficient for both bindings?
4. Is the generic signature implementable identically in Rust, including the synchronous rule?

## 7. Python implementation (candidate)

**Contract:** approved by Codex contract review 1 (`minion-agent#166` issuecomment-6058279097) and
merged: code `#165` → `b1f8108b`, docs `#260` → `142d0491`.

**Code** (`minion-agent-python/src/minion_agent/agent_loop/`):
- **`driver.py`:**
  - `type PromptAssembler = Callable[[str, tuple[ToolDefinition, ...]], str]`;
  - an optional `AgentLoop(prompt_assembler=...)` collaborator, default `None`;
  - `_system_text(decision, context)`, which applies the contract's three cases in order:
    1. the per-step override, verbatim;
    2. otherwise `prompt_assembler(context.system_prompt, context.tools)`, when one is installed;
    3. otherwise `context.system_prompt`.
  - A non-string result raises `TypeError`.
  - `_run_step` computes the system text **before** `record_header`, so a failing assembler records
    no header and sends no request. Its exception reaches `_execute_run`'s certified
    `except Exception` → `_settle_run_failure` path unchanged.
- **`__init__.py`:** `AgentLoopFactory.for_instance(instance, *, prompt_assembler=None)`, and
  `PromptAssembler` is exported.

**Unchanged:** when no assembler is installed, the request-build path computes the same
`system_base` as before. The certified suites pass unmodified (gates below).

**Witnesses** (`tests/agent_loop/test_prompt_assembler.py`, 13 tests):
1. no assembler: the request and header are exactly the stored prompt;
2. run start: one call, with the base and the run-start tuple;
3. a tool registered after run start (from a tool's own execute) is in neither the prompt nor the
   schemas;
4. a `prepareNextTurn` replacement drives the next prompt and schemas;
5. a listener reads and replaces the base, not the assembled text;
6. `added_tool_names` growth reaches the prompt and the schemas;
7. the override is sent verbatim, and the assembler is not called;
8. concurrent registry churn at every await point of a 7-request run: for each request, the
   assembler's tools equal the request's schemas;
9. a raising assembler, which sends nothing and records no header; the run ends `failed`;
10. a non-string result, likewise;
11. a later-turn failure, which keeps the earlier request and header and settles as `failed`;
12. the header records and reconstructs the assembled text;
13. the factory installs the assembler, or leaves it absent.

**Kill controls** (disposable copy; `data/08-l08-d001/controls.py`): all 5 killed.

| Mutant | Killed by witnesses |
|---|---|
| Assembler fed from the live registry | 3, 4 |
| Reversed snapshot order | 6 |
| Override reassembled | 7 |
| Stale assembled text (first request only) | 3, 4, 6, 8, 11 |
| Header published before assembly | 7, 9, 10, 11, 12 |

**Fresh gates (code @ `53287050`):**

| Platform | Result |
|---|---|
| Windows, pinned ICU 78.3 | **5,105 passed, 32 skipped, 21 xfailed**; coverage **100%** (8,256 statements); ruff clean; mypy clean (109 files) |
| Linux (`python:3.13`, pinned ICU, search engines mounted) | **5,042 passed, 0 failed, 97 skipped, 19 xfailed** |

**Rust:** NOT_IMPLEMENTED. Codex implements under the same contract after this review.

## 8. Remediation 1 (Codex implementation review 1)

**Review:** Codex, **CHANGES REQUESTED** at code `#168` @ `53287050` / docs `#262` @ `27cad9ed`.

**Finding `L08D001-R001` (medium, `CONTRACT_ASSURANCE_DEFECT`).**
- **Defect:** an assembler raising `UnknownModelError` escaped through the driver's certified eager
  model-error exemption (`_execute_run`'s `except UnknownModelError: raise`). For both the first
  and a later request, no failure message and no failed `agent_end` were produced.
- **Why it matters:** the contract requires every assembler failure to settle through
  `handleRunFailure`, whatever its class.

**Correction (code @ `3ca9308e`).**
- **The seam:** `_system_text` catches any ordinary `Exception` from the assembler and re-raises it
  as `PromptAssemblyError`, which keeps the same text (so the failure message is unchanged) and
  keeps the original as `__cause__`. No exemption meant for another origin can capture it.
- **Unchanged:**
  - `BaseException`s (cancellation, `KeyboardInterrupt`) pass through untouched;
  - the certified `UnknownModelError` exemption is not modified, and genuine model resolution
    still propagates eagerly.

**Witnesses** (`tests/agent_loop/test_prompt_assembler.py`, now 16):
- `test_an_assembler_raising_unknown_model_error_still_settles_as_failed[1|2]`, for the first and
  a later request: no request or header for the failing request, the earlier header kept, one
  failure message with the assembler's text, `agent_end` `failed`, status idle;
- `test_a_genuinely_unknown_model_still_propagates_eagerly_with_an_assembler`: the certified eager
  path stays green.

**Known-bad:** with the code @ `53287050` driver, both `UnknownModelError` witnesses fail; the
eager-path witness passes.

**Fresh gates (code @ `3ca9308e`):**

| Platform | Result |
|---|---|
| Windows | **5,108 passed, 32 skipped, 21 xfailed**; coverage **100%** (8,260 statements); ruff and mypy clean |
| Linux | **5,045 passed, 0 failed, 97 skipped, 19 xfailed** |

## 9. Remediation 2 (Codex final review 2: `L08D001-R002`)

**Review:** Codex, **CHANGES REQUESTED** at code `#168` @ `3ca9308e` / docs `#262` @ `ac16a4f7`.
- `L08D001-R001` is **CLOSED**.
- New finding `L08D001-R002` (medium, `CONTRACT_ASSURANCE_DEFECT`): the committed control
  `data/08-l08-d001/controls.py` no longer built an executable "stale assembled text" mutant.
  - **Cause:** remediation 1 moved the assembler call into a `try` at 12 spaces. The control's
    8-space anchor then matched a suffix of that line, and the mutant's second line fell outside the
    `try`, giving a `SyntaxError`.
  - **Effect:** the script reported `SURVIVED -> []`, so no intended witness ever ran.
- No production or contract change was requested. The production code is unchanged at `3ca9308e`.

**Correction (docs only; `controls.py`).**
- **Anchors** start at a line start (a leading newline), so they can never match a suffix of a
  more-indented line. The stale mutant keeps its meaning: it reuses the first non-empty assembled
  text on later requests, with the error-origin handling unchanged.
- **Validity guards.** Every mutant must change the source and must compile (`py_compile`). The
  pytest exit status must be 0 (survived) or 1 (killed). Anything else is reported **INVALID** and
  fails the run. A syntax, collection or usage error is never counted as a kill (workflow §9.7).
- **The guard is exercised:** run in a container without `pytest-cov`, all five mutants reported
  INVALID (pytest exit status 4, an unknown `--no-cov`) rather than a false kill or survival.

**Results at code `3ca9308e`.** Each mutant compiles and is killed by its intended witnesses, on
Windows and on Linux (exit 0 on both):

| Mutant | Killed by |
|---|---|
| Live-registry assembly | late registration; `prepareNextTurn` replacement |
| Reversed snapshot order | `added_tool_names` growth |
| Override reassembled | the verbatim-override witness |
| Stale assembled text | late registration, replacement, growth, concurrent churn, later-turn failure, `UnknownModelError[2]` |
| Header published before assembly | override, raising, non-string, later-turn failure, header reconstruction, `UnknownModelError[1]` and `[2]` |

## 10. Dependency on L08-D002 (Owner decision on `L08D001-RUST-C001`)

- **The defect:** the Rust checkpoint found that the certified Rust driver records no request
  header (`L08D001-RUST-C001`, `CONTRACT_ASSURANCE_DEFECT`).
- **The decision:** the Owner opened `L08-D002` (`minion-agent#171`), which makes "one
  request/header per provider request" normative in both bindings (spec/agent.md, "Request header
  per provider request").
- **What changes here:** this delta's step 4 ("record the request header") and its "no assembler:
  unchanged" guarantee are read relative to that corrected baseline. AG-024 is unchanged. Python
  already conforms.
- **Rust order:** Rust L08-D001 is integrated and certified only after L08-D002 is.
