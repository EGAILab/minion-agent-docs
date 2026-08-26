# Layer 05 (Tool Model + Registry) — Rust Implementation-Owner Re-Review Package

**Prepared:** 2026-08-26
**Prepared by:** Claude (Python/shared-contract owner, per the adopted workflow)
**Why this exists:** the original Layer-05 candidate (`minion-agent@d9054fe`,
`minion-agent-docs@7728d55`) was independently reviewed by Rust and **REJECTED** — see
`05-tool-model-registry-rust-review.md`, reviewed at `minion-agent-docs@fc741e0e4ba162303b89732dc5704744468bb1e5`,
one `PI_PARITY_DEFECT` (`L05-R001`) and four `CONTRACT_ASSURANCE_DEFECT`s (`L05-R002`..`L05-R005`).
This package requests a **fresh, independent** Rust review of the repaired candidate. Python
self-certifying after repair does not constitute Rust approval; do not treat this package as
already accepted.

**Do not modify Rust in response to this package without first recording a verdict.**

---

## 1. What changed since the rejected candidate (`fc741e0e4ba162303b89732dc5704744468bb1e5`)

This is a **narrow remediation pass** responding to exactly the five findings below. It does not
start Layer 06, does not touch Rust, and does not redesign the tools subsystem beyond what each
finding required.

```text
Finding    Repair (full detail: 05-tool-model-registry.md §19)
L05-R001   GrammarConstrainedSampling rewritten from an open dict[str,str] to two independently-
           optional named fields (openai_lark, openai_regex), matching pinned Pi's closed
           GrammarFormat = "openai_lark" | "openai_regex" union. as_json() omits unset keys.
           Canonical schema/scenarios closed to the same 2-key domain.
L05-R002   ToolRegistry.visible_from/resolve/schemas widened to accept ScopeKey | Scope | None;
           given a live Scope, a disposed scope now returns empty rather than falling back to
           ancestor/global visibility -- reusing the already-certified Scope.disposed property.
           ScopedRegistry/ScopeTree (Layer 01) unmodified.
L05-R003   Empirically confirmed (Python REPL probe + new canonical scenario) that a scoped
           registration survives its owning plugin's unmount and is withdrawn only by scope
           disposal/explicit withdrawal -- Model 2 (scope-owned-after-registration), matching this
           review's own description of Rust's FiberInitContext::effect routing. Adopted as
           normative; spec/tools.md and the TOOL-014 manifest row corrected from an inaccurate
           either/or framing. No Runtime/registry code changed -- this was a documentation defect,
           not a behavioral one.
L05-R004   The conformance runner's _ScopeTable now raises on an unresolved scope_parent or query
           scope name instead of silently treating it as "no parent"/"untagged" -- input
           validation at the runner boundary, not registry-semantics simulation.
L05-R005   Canonical parameters shorthand (missing/null meaning "empty object") removed; scenarios
           must write parameters explicitly, including the empty-object case. Docs tightened to
           "object-valued JSON Schema," not "arbitrary JSON Schema." Python's own
           ToolDefinition.parameters keeps None as a host-language-only convenience, unaffected.
```

**Reviewed commits (delta candidate):**

```text
minion-agent        (uncommitted at package time; see commit recorded in the covering commit
                     message) src/minion_agent/llm/tools.py (GrammarConstrainedSampling
                     restructured), src/minion_agent/tools/registry.py (Scope-aware query
                     methods), src/minion_agent/tools/execute.py, src/minion_agent/tools/batch.py
                     (type widening pass-through), src/minion_agent/agent_loop/driver.py (2 call
                     sites updated to pass Scope instead of ScopeKey), tests/conformance/
                     tool_registry_runner.py (_ScopeTable rejects unresolved references, grammar
                     construction updated), tests/llm/test_tool_schema.py (updated + 2 new tests),
                     tests/typing/valid_tool_construction.py (updated for new constructor shape),
                     conformance/schema/tool-registry-scenario.schema.json (closed grammar domain,
                     required parameters), conformance/agent/tool-registry-*.yaml (7 existing
                     scenarios updated, 1 new scenario added: tool-registry-scoped-registration-
                     survives-plugin-unmount), pi-parity-manifest.yaml (TOOL-014 row corrected)
minion-agent-docs   (uncommitted at package time) spec/tools.md (grammar-domain and registration-
                     lifecycle prose corrected), assurance/layers/05-tool-model-registry.md
                     (§19 remediation history appended, header status updated), this handoff
                     (rewritten for re-review)
```

**Pinned Pi revision:** `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged).

---

## 2. Scope (unchanged from the original package)

**In scope:** the tool definition field contract, `ctx.tools` registry authority, scoped
visibility/ordering, same-name shadowing across scopes, same-scope duplicate-name resolution,
registration lifecycle (effect-owned; ownership-precise, not either/or, per `L05-R003`), and
model-facing schema projection.

**Explicitly out of scope:** identical to the original package §1 — `prepare_arguments`/`execute`
invocation, `AgentToolResult` handling, batch execution semantics, provider-specific enforcement,
built-in tools, approval/sandbox policy, and cancellation propagation all remain Layer 06/09/11/13
territory, untouched by this pass.

---

## 3. Rust's required independent verdict, per question

Re-verify all eight questions from the original package (§3 there) against the repaired candidate
directly — do not assume a prior verdict on an earlier revision still holds. In addition:

1. **`L05-R001`:** re-read `packages/ai/src/types.ts` `GrammarFormat`/`GrammarVariants` directly at
   the pinned commit. Confirm the closed 2-value domain and the `Partial<Record<...>>`
   omit-unset-key semantics this package now claims.
2. **`L05-R002`:** confirm independently that a disposed-scope query correctly observes nothing at
   Layer 05, and that this reuses `Scope.disposed` rather than duplicating disposal tracking.
3. **`L05-R003`:** confirm whether Rust's own (not-yet-implemented) registry design, when built,
   will exhibit the same scope-owned-after-registration lifetime this package claims matches
   `FiberInitContext::effect`'s routing — or whether Rust's own architecture in fact differs from
   what this review's own write-up described. This package's Model-2 adoption rests on that
   description; if it was imprecise, say so now rather than after Rust implementation begins.
4. **`L05-R004`:** confirm the runner's reference-validation is genuinely input-validation, not a
   parallel scope-lookup algorithm.
5. **`L05-R005`:** confirm `TSchema`'s object-shaped-in-practice claim directly against TypeBox
   usage in pinned Pi, and confirm no legitimate Pi tool construction path relies on a bare
   boolean-shorthand JSON Schema for `parameters`.

---

## 4. Fresh Python evidence to reproduce, not merely trust

```text
full pytest (coverage enabled):     849 passed, 29 xfailed, 0 failed, 100.00% coverage
ruff check .:                        All checks passed
mypy (configured scope):             Success, no issues found in 57 source files
mypy + typing fixtures:              Success, no issues found in 59 source files
schema validation:                   148 passed
tool-registry canonical:             9 discovered / 9 executed / 9 passed / 0 deferred
Runtime canonical (regression):      26 passed (unchanged)
Session canonical (regression):      20/20 passed (unchanged, certified count preserved)
XFORM canonical (regression):        14/14 passed (unchanged, certified count preserved)
```

Reproduce via (from `minion-agent-python/`): `uv run pytest`, `uv run ruff check .`,
`uv run mypy src/minion_agent`, `uv run mypy src/minion_agent tests/typing/valid_message_
construction.py tests/typing/valid_tool_construction.py`.

---

## 5. Canonical evidence design (updated)

`conformance/schema/tool-registry-scenario.schema.json` now requires `parameters` explicitly on
every tool entry (no missing/null shorthand) and closes the grammar `variants` object to exactly
`openai_lark`/`openai_regex`. 9 scenario files (8 original, revised where a finding required it,
plus 1 new: `tool-registry-scoped-registration-survives-plugin-unmount`). Every field remains
language-neutral — confirm directly by reading the files, not from this summary. Note the runner's
one structural property relevant to `L05-R003`'s evidence: `queries` are all evaluated after every
`steps` entry has run, never interleaved — a scenario proving an intermediate lifecycle state
(e.g., "still visible after unmount, before disposal") must stop its `steps` at that point rather
than including a later disposal step.

---

## 6. Explicitly out of scope for this package

Identical to the original package §6 — `TOOL-001`..`TOOL-007`, Layer 06/09/11, and `LAY-F001` are
not reopened or part of this review.

## 7. Expected outcome

```text
LAYER 05 SHARED CONTRACT
    APPROVED
```

or a precise rejection naming exactly which field, rule, or boundary is not language-neutral or not
Pi-compatible — using fresh finding IDs if new issues are found, not reusing `L05-R001`..`L05-R005`
for anything other than confirming those exact five are now resolved. If approved, Rust's own
implementation-timing adjudication follows, per the same review-before-remediation workflow used at
every prior layer this session.
