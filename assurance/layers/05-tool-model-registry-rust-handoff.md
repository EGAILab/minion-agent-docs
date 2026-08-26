# Layer 05 (Tool Model + Registry) — Final Rust Closure Review Package

**Prepared:** 2026-08-26
**Prepared by:** Claude (Python/shared-contract owner, per the adopted workflow)
**Why this exists:** the second-remediation candidate (`minion-agent@f945c59`,
`minion-agent-docs@8714e28`) was independently re-reviewed by Rust a third time and **rejected on
exactly one remaining finding** — `05-tool-model-registry-rust-final-rereview.md`: `L05-R005`.
`L05-R001`, `L05-R002`, `L05-R003`, `L05-R004`, and `L05-R006` were all confirmed **RESOLVED** and
were not reopened. This package requests a **narrow final closure review** of `L05-R005` alone,
plus a regression confirmation that the other five findings were not disturbed.

**Do not modify Rust in response to this package without first recording a verdict.**

---

## 1. The only change since the third-rejected candidate (`8714e28299e656f054bfc172c316a85052fe9e3e`)

```text
L05-R005

before:
    Python ToolDefinition.parameters accepted a raw dict only when
    parameters.get("type") == "object" -- rejecting e.g. {"type": "string"}
    and a top-level {"oneOf": [...]}

after:
    Python ToolDefinition.parameters accepts any dict (any JSON-object-valued
    mapping) in addition to a pydantic BaseModel subclass, matching the
    already-correct spec/canonical/Pi boundary exactly

still rejected:
    missing (dataclass-required argument)
    None
    boolean (true/false)
    array
    string
    number

new regression coverage:
    {"type": "string"} accepted
    {"oneOf": [{"type": "string"}, {"type": "number"}]} accepted
    arbitrary object members ($comment, custom-extension) preserved unchanged
```

Root cause: two different meanings of "object-valued" were conflated in the second remediation.
"The schema's own JSON representation is a mapping" (correct, matches Pi's `Tool<TParameters
extends TSchema>`, generic over TypeBox's whole `TSchema` domain, not narrowed to `TObject`) was
implemented as "the schema must describe an object instance via a top-level `type: object`
keyword" (incorrect, narrower than what pinned Pi and the canonical schema both already allowed).
Full root-cause writeup: `05-tool-model-registry.md` §21.1.

**No other surface's semantic domain changed.** The canonical schema, `spec/tools.md`'s core rule,
and TOOL-016's rule were already correct — only the Python public constructor was wrong. Two
clarifying sentences were added (to `spec/tools.md` and TOOL-016) to preempt the same confusion
recurring; neither changes any rule.

**Reviewed commits (delta candidate):**

```text
minion-agent        (uncommitted at package time; see the covering commit) src/minion_agent/tools/
                     definition.py (__post_init__ narrowed to "is a mapping"), tests/tools/
                     test_definition.py (1 invalid case removed, 2 new parametrized tests),
                     tests/conformance/test_schema_validation.py (2 new positive regression
                     cases -- canonical schema needed no change), tests/typing/
                     valid_tool_construction.py (2 new positive constructions),
                     pi-parity-manifest.yaml (TOOL-016 rule text corrected -- it previously
                     asserted the same false claim that misled the second remediation)
minion-agent-docs   (uncommitted at package time) spec/tools.md (one clarifying sentence, no
                     rule change), assurance/layers/05-tool-model-registry.md (§21 third-
                     remediation history appended, header updated), this handoff (rewritten for
                     the final closure review)
```

**Pinned Pi revision:** `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged).

---

## 2. Rust's required verdict

1. Confirm the repaired `ToolDefinition.__post_init__` accepts `{"type": "string"}` and a
   top-level `{"oneOf": [...]}`, and still rejects missing/`None`/boolean/array/string/number
   values.
2. Confirm no other file's semantic domain drifted (spec, TOOL-016, and canonical schema should
   read as pure clarification/traceability fixes, not rule changes — diff them directly).
3. Confirm `L05-R001`, `L05-R002`, `L05-R003`, `L05-R004`, `L05-R006` were not touched and remain
   resolved (regression only — this package does not ask for their re-audit).
4. If satisfied, return:

```text
LAYER 05 SHARED CONTRACT
    APPROVED
```

so Rust's own implementation-timing adjudication can follow. If not satisfied, return a precise
finding — a fresh ID if genuinely new, not a reuse of `L05-R001`..`L05-R006`.

---

## 3. Fresh Python evidence to reproduce, not merely trust

```text
full pytest (coverage enabled):     883 passed, 29 xfailed, 0 failed, 100.00% coverage
ruff check .:                        All checks passed
mypy (configured scope):             Success, no issues found in 57 source files
mypy + typing fixtures:              Success, no issues found in 59 source files
schema validation:                   165 passed (163 + 2 new regression probes)
tool-registry canonical:             9 discovered / 9 executed / 9 passed / 0 deferred (unchanged)
tool-registry harness validation:    7 discovered / 7 executed / 7 passed (unchanged)
Runtime canonical (regression):      26 passed (unchanged)
Session canonical (regression):      20/20 passed (unchanged)
XFORM canonical (regression):        14/14 passed (unchanged)
```

Reproduce via (from `minion-agent-python/`): `uv run pytest`, `uv run ruff check .`,
`uv run mypy src/minion_agent`, `uv run mypy src/minion_agent tests/typing/valid_message_
construction.py tests/typing/valid_tool_construction.py`.

---

## 4. Explicitly out of scope for this package

`L05-R001`, `L05-R002`, `L05-R003`, `L05-R004`, `L05-R006` — already resolved, not reopened, not
part of this review. `TOOL-001`..`TOOL-007`, Layer 06, Layer 09, Layer 11, `LAY-F001` — not part of
this review, unchanged.

## 5. Expected outcome

```text
LAYER 05 SHARED CONTRACT
    APPROVED
```

If approved, Rust's own implementation-timing adjudication (required now vs. explicitly deferred)
follows. This package does not presume that answer.
