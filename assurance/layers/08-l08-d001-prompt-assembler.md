# L08-D001 — Optional prompt assembler at the request snapshot (Layer 08 delta)

**Status:** contract delta, for independent contract review. Python: NOT_IMPLEMENTED. Rust:
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
