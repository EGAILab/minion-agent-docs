# Layer 05 (Tool Model + Registry) — Rust Implementation-Owner Re-Review Package (Round 2)

**Prepared:** 2026-08-26
**Prepared by:** Claude (Python/shared-contract owner, per the adopted workflow)
**Why this exists:** the first-remediation candidate (`minion-agent@816fc9f`,
`minion-agent-docs@ddfe715`) was independently re-reviewed by Rust and **REJECTED again** — see
`05-tool-model-registry-rust-rereview.md` (`61d42dc`, `7e288a6`): `L05-R001`, `L05-R002`,
`L05-R004`, `L05-R005` remained open, and a new `L05-R006` was found. `L05-R003` was confirmed
**RESOLVED** and was not reopened. This package requests a **second fresh, independent** Rust
review of the newly repaired candidate. Python self-certifying after repair does not constitute
Rust approval.

**Do not modify Rust in response to this package without first recording a verdict.**

---

## 1. What changed since the second-rejected candidate (`7e288a62280969251153e080f28305ebad48fadc`)

This is a **narrow contract-consistency / evidence-integrity repair** responding to exactly the
five findings below. It does not start Layer 06, does not touch Rust, does not reopen Layer 01,
and does not redesign the tools subsystem. `L05-R003` was not touched (no code, spec, or manifest
text describing it changed).

```text
Finding    Repair (full detail: 05-tool-model-registry.md §20)
L05-R001   Fixed the two remaining stale surfaces (Tool-summary prose in spec/tools.md, TOOL-008's
           manifest rule) that still described grammar variants as an open string-keyed map, and
           closed the schema/Python empty-variants mismatch: removed minProperties: 1 from the
           canonical schema's grammar variants sub-schema (both the input and output positions).
           Pi's GrammarVariants = Partial<Record<GrammarFormat, string>> statically permits {};
           Pi's own rejection of an empty grammar selection happens at provider request-
           construction time (packages/ai/src/api/constrained-sampling.ts::
           resolveGrammarConstrainedSampling), Real Providers/Layer 11 territory, not Layer 05.
L05-R002   Added the disposed-scope observation rule to spec/tools.md's Registry section as an
           explicit normative statement (previously stated only in this project's own assurance
           history, never in the spec a from-scratch implementer would read). New requirement
           TOOL-015 traces it; TOOL-010 amended with a forward pointer. No Runtime/registry code
           changed -- existing behavior and evidence were already correct.
L05-R004   The conformance runner now validates every declarative reference (scope_parent, query
           scope, step plugin ids, dispose_scope scope, plus self-parent/cycle detection in the
           parent graph) in a dedicated pass BEFORE any Context/plugin/scope object is
           constructed, replacing the previous approach where an unresolved scope_parent's
           ValueError was raised inside a plugin's apply() during reconciliation and silently
           swallowed as a fiber failure. 7 new harness-validation tests reproduce the review's
           exact failure mode directly and confirm it is now a clean, immediate rejection.
L05-R005   ToolDefinition.parameters is now `type[BaseModel] | dict[str, Any]` (None removed from
           the type), with a new __post_init__ that rejects None and non-object-shaped dicts at
           construction (not only via typing, since a dynamically-typed caller can bypass mypy).
           All ~24 non-negative-test callsites across src/tests updated to pass the explicit empty
           schema. 2 new negative unit tests. New manifest row TOOL-016 traces the base Tool
           interface fields, which no prior row covered.
L05-R006   Removed canonical toolInput's constrainedSamplingInput { "type": "null" } branch, so an
           explicit null is rejected as fixture input (the absent state must omit the key). Split
           a separate constrainedSamplingOutput schema definition for the expected-output position,
           which correctly keeps accepting null there -- that is a different, pre-existing, and
           unaffected convention (ToolSchema.as_json()'s own established null-for-absence rule),
           not the same finding as canonical-input null.
```

**Reviewed commits (delta candidate):**

```text
minion-agent        (uncommitted at package time; see the covering commit) src/minion_agent/tools/
                     definition.py (parameters required, __post_init__ validation),
                     src/minion_agent/tools/execute.py (dead None-branch removed),
                     tests/conformance/tool_registry_runner.py (_validate_references()),
                     tests/conformance/test_tool_registry_runner_validation.py (new, 7 tests),
                     tests/conformance/test_schema_validation.py (15 new domain-boundary tests),
                     tests/tools/test_definition.py (2 new negative tests, 1 test updated),
                     ~24 test/typing callsites updated for required parameters,
                     conformance/schema/tool-registry-scenario.schema.json (minProperties removed,
                     constrainedSamplingInput/-Output split, null rejected on the input side),
                     pi-parity-manifest.yaml (TOOL-008 corrected, TOOL-010 cross-referenced,
                     TOOL-015 and TOOL-016 added)
minion-agent-docs   (uncommitted at package time) spec/tools.md (grammar/parameters/constrained-
                     sampling/disposed-scope prose corrected), assurance/layers/
                     05-tool-model-registry.md (§20 second-remediation history appended, header
                     updated), this handoff (rewritten for the second re-review)
```

**Pinned Pi revision:** `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged).

---

## 2. Scope (unchanged)

Identical to the round-1 package §2. `L05-R003`'s resolved lifetime matrix (scope-owned-after-
registration) is unchanged and not part of this round's requested review scope, though a reviewer
confirming the round is welcome to re-affirm it did not regress.

---

## 3. Rust's required independent verdict, per question

Re-verify all questions from the original and round-1 packages against this candidate directly.
In addition, for this round specifically:

1. **`L05-R001`:** confirm `packages/ai/src/api/constrained-sampling.ts::resolveGrammarConstrainedSampling`
   (lines ~230–263) is genuinely provider-request-construction logic, not something that should be
   read as a `Tool`-model-level constraint. If it should be pulled into Layer 05 after all, say so
   with a specific reason (e.g., evidence that some other Pi call site constructs/validates a
   `Tool` value itself, not just a provider request, and rejects empty variants there).
2. **`L05-R002`:** confirm the new spec/tools.md paragraph and TOOL-015 are sufficient for an
   implementer with no access to this project's assurance history to derive the exact rule.
3. **`L05-R004`:** attempt to reproduce a malformed-reference scenario against the repaired runner
   and confirm it fails cleanly and immediately, not via an incidental downstream error.
4. **`L05-R005`:** confirm no remaining code path constructs a `ToolDefinition` with `None`/missing
   `parameters` that bypasses `__post_init__` (e.g., via `object.__new__` or similar), and confirm
   the "object-valued, not arbitrary JSON Schema" boundary is stated consistently in spec, schema,
   manifest, and code.
5. **`L05-R006`:** confirm the input/output split is correct and that no canonical fixture still
   writes an input-side explicit null anywhere.

---

## 4. Fresh Python evidence to reproduce, not merely trust

```text
full pytest (coverage enabled):     873 passed, 29 xfailed, 0 failed, 100.00% coverage
ruff check .:                        All checks passed
mypy (configured scope):             Success, no issues found in 57 source files
mypy + typing fixtures:              Success, no issues found in 59 source files
schema validation:                   163 passed (148 + 15 new domain-boundary probes)
tool-registry canonical:             9 discovered / 9 executed / 9 passed / 0 deferred (unchanged)
tool-registry harness validation:    7 discovered / 7 executed / 7 passed (new, R004)
Runtime canonical (regression):      26 passed (unchanged)
Session canonical (regression):      20/20 passed (unchanged)
XFORM canonical (regression):        14/14 passed (unchanged)
```

Reproduce via (from `minion-agent-python/`): `uv run pytest`, `uv run ruff check .`,
`uv run mypy src/minion_agent`, `uv run mypy src/minion_agent tests/typing/valid_message_
construction.py tests/typing/valid_tool_construction.py`.

---

## 5. Canonical evidence design (delta)

The 9 tool-registry scenario files are unchanged in count and behavior from round 1. What changed
is the *schema* validating them (`conformance/schema/tool-registry-scenario.schema.json`): grammar
`variants` no longer requires `minProperties: 1` at either the input or output position, and the
input position (`constrainedSamplingInput`) no longer accepts `{"type": "null"}` as a valid
alternative (the output position, `constrainedSamplingOutput`, correctly still does — these are
now two distinct schema definitions, not one shared `$ref`). New non-canonical harness tests
(`tests/conformance/test_tool_registry_runner_validation.py`) exercise the runner's own reference
validation directly with hand-built documents, deliberately not as canonical product-semantic
scenarios, per this project's own distinction between harness/schema integrity and registry
semantics.

---

## 6. Explicitly out of scope for this package

Identical to the round-1 package §6, plus: `L05-R003` and everything in
`05-tool-model-registry-rust-rereview.md` §4 (the resolved lifetime matrix) — not reopened, not
part of this review.

## 7. Expected outcome

```text
LAYER 05 SHARED CONTRACT
    APPROVED
```

or a precise rejection naming exactly which field, rule, or boundary is not language-neutral or not
Pi-compatible — using fresh finding IDs if new issues are found, not reusing `L05-R001`..`L05-R006`
for anything other than confirming those exact six are now resolved. If approved, Rust's own
implementation-timing adjudication follows, per the same review-before-remediation workflow used at
every prior layer this session.
