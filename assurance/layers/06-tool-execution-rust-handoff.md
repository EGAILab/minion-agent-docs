# Layer 06 (Tool Execution Pipeline) — Rust Implementation-Owner Final Closure Review Package

**Prepared:** 2026-08-26
**Prepared by:** Claude (Python/shared-contract owner, per the adopted workflow)
**Why this exists:** the repaired candidate from the first remediation round was independently
re-reviewed by Rust (`assurance/layers/06-tool-execution-rust-rereview.md`). That re-review
**confirmed** `L06-R002`, `L06-R004`, and `L06-R005` resolved, and **reopened** three:
`L06-R001` (`CONTRACT_ASSURANCE_DEFECT` — stale `ToolDefinition.parameters` documentation),
`L06-R003` (`PI_PARITY_DEFECT` — raw public `EventBus` registration still able to bypass
after-hook override authority), and `L06-R006` (`CONTRACT_ASSURANCE_DEFECT` — dangling `TOOL-022`
requirement citation). This package requests a **fresh, independent, final** closure review of
the narrow repair to exactly those three. Python self-certifying after repair does not constitute
Rust approval.

**Do not modify Rust in response to this package without first recording a verdict.**

---

## 1. The three repairs since the re-reviewed candidate

```text
L06-R001 (CONTRACT_ASSURANCE_DEFECT)

before:
    _validate() (execute.py) genuinely validates a raw, object-valued JSON-Schema dict via
    the jsonschema library -- that runtime fix was already correct and already confirmed by
    the first re-review. But ToolDefinition.parameters' own docstring (definition.py) still
    said a raw dict "bypasses Python-side argument validation" / is "not Python-validated" --
    a stale, self-contradicting public-API claim, caught directly against the already-correct
    runtime behavior.

after:
    definition.py's module docstring and the ToolDefinition.parameters field docstring both
    rewritten: Layer 05 only stores the schema: a pydantic model class, or a raw JSON Schema
    dict. Layer 06's execute.py validates execution arguments against it before execute runs
    -- via pydantic for a model class, via the general jsonschema library for a raw dict.
    Construction here (Layer 05) never validates anything itself, regardless of
    representation. No runtime behavior changed; no new test needed for a documentation-only
    correction (the runtime-behavior test coverage already exists from the first remediation
    round and is unchanged).

L06-R003 (PI_PARITY_DEFECT)

before:
    register_after_tool_call_hook's own AfterToolCallOverride type is correctly constrained
    (no slot for tool_call_id/tool_name/added_tool_names) -- but tools/post-execute remains a
    public Runtime event, and nothing stops a caller from registering a listener directly via
    ctx.events.on(TOOLS_POST_EXECUTE, ...) that returns a whole, differently-identified
    ToolResult. The re-review directly proved this raw path rewrites tool_call_id/tool_name/
    added_tool_names -- fields pinned Pi's AfterToolCallResult gives a hook no way to touch at
    all, through either registration path. Fixing only the helper was insufficient: the
    constraint has to live at the authoritative dispatch boundary, not a registration-path-
    specific helper.

after:
    _finalize() (execute.py) now snapshots tool_call_id/tool_name/added_tool_names from the
    pre-hook result before dispatching the tools/post-execute waterfall, and unconditionally
    restores them from that snapshot after the waterfall completes -- regardless of whether
    any listener (helper-registered or raw-registered) tried to replace them. This is the one
    production call site every tools/post-execute dispatch necessarily passes through, so the
    enforcement point is registration-path-independent by construction. No change to the
    generic EventBus; no parallel hidden hook system; TOOLS_POST_EXECUTE remains a public,
    exported event. Five new tests added directly against the raw public registration seam
    (not only the helper): a raw listener cannot replace identity/added_tool_names; a raw
    listener CAN still change Pi-allowed fields (content, terminate) -- the fix is scoped, not
    a lockdown; in-place mutation of the frozen ToolResult is proven structurally impossible
    independent of this fix; a raw listener and a helper-registered listener mixed in the same
    chain share the same authority; and the existing failure short-circuit holds with a raw
    listener present.

L06-R006 (CONTRACT_ASSURANCE_DEFECT)

before:
    register_after_tool_call_hook's docstring cited TOOL-022, which does not exist anywhere in
    the 65-row manifest -- a dangling requirement citation. Per the re-review's own framing,
    this could not be closed by fixing the citation alone: it also required L06-R003's
    authoritative-boundary fix, since the helper's docstring previously overstated its own
    authority ("the only sanctioned way to extend tools/post-execute", "cannot replace
    execution identity... not merely by convention") -- a claim the raw-registration bypass
    made false.

after:
    The TOOL-022 citation removed and replaced with TOOL-005, which already covers N-listener
    composition semantics (added in the first remediation round) and was extended this pass to
    describe the second R003 closure explicitly. No new manifest row added -- an existing
    citation was corrected, not a placeholder invented, per this pass's own preference for
    that resolution when an existing requirement already covers the behavior. The helper's
    docstring itself softened from "the only sanctioned way" to "the recommended way", with an
    explicit note that its own constraint is a convenience and _finalize's restoration is the
    actual authoritative boundary -- and the matching prose in spec/tools.md's "After-hook
    waterfall" paragraph corrected identically, so no surface still claims replacement is
    prevented "by construction" of the helper alone.
```

**Reviewed commits (delta candidate):** see the covering commit messages; committed on top of
`minion-agent-docs@09764e6fc86ee8619a6139202a8eee9440d6aabf` (the merged Rust re-review artifact)
and the corresponding `minion-agent` candidate.

**Pinned Pi revision:** `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged).

---

## 2. Scope (unchanged, narrower than the first package)

Identical to the first package's §2, plus: this package does **not** reopen `L06-R002`,
`L06-R004`, or `L06-R005` — the re-review already confirmed all three resolved, no code or
documentation touched by those findings changed in this pass, and no fresh evidence for them is
included here beyond the regression numbers in §4 (which cover the whole suite, not those
findings specifically). Do not re-litigate them; a verdict on this package should treat them as
settled.

---

## 3. Rust's required verdict, per repair

1. **`L06-R001`:** confirm `definition.py`'s module docstring and the `ToolDefinition.parameters`
   field docstring no longer state or imply that a raw, object-valued JSON-Schema `dict` bypasses
   or is exempt from Python-side validation, and that they accurately describe Layer 05 as
   storage-only and Layer 06 (`execute.py`) as the validator (pydantic for a model class,
   `jsonschema` for a raw `dict`). Confirm no other public-facing description of `parameters`
   anywhere in the delta (docstrings, `spec/tools.md`, the manifest) still carries the stale
   claim.
2. **`L06-R003`:** confirm directly against `execute.py`'s `_finalize()` that `tool_call_id`,
   `tool_name`, and `added_tool_names` are restored from the pre-hook result unconditionally,
   independent of how many `tools/post-execute` listeners ran or which registration API
   (`register_after_tool_call_hook` or raw `ctx.events.on(TOOLS_POST_EXECUTE, ...)`) produced
   the waterfall's output. Independently attempt (or verify the delta's own tests attempt) a raw
   public registration that returns a whole, differently-identified `ToolResult`, and confirm the
   three protected fields survive unchanged while Pi-allowed fields (`content`, `details`,
   `is_error`, `usage`, `terminate`) still change freely. Confirm the fix required no change to
   the generic `EventBus` and introduced no second, hidden hook-registration mechanism.
3. **`L06-R006`:** confirm no `TOOL-022` citation remains anywhere in the delta, that
   `register_after_tool_call_hook`'s docstring cites an existing manifest row (`TOOL-005`)
   accurately covering its behavior, and that no surface (docstring, spec, manifest) still claims
   whole-result replacement is prevented "by construction" of the helper alone rather than by
   `_finalize`'s dispatch-boundary enforcement.
4. **Regression-only confirmation (not re-review) for `L06-R002`, `L06-R004`, `L06-R005`:** spot
   check that nothing in this narrow delta touched the files/behaviors those findings closed
   (error-message formatting, canonical scenario count, signal-defer wording) — a confirmation
   that scope discipline held, not a re-audit of the findings themselves.

---

## 4. Fresh Python evidence to reproduce, not merely trust

```text
full pytest (coverage enabled):     914 passed, 19 xfailed, 0 failed, 100.00% coverage
ruff check .:                        All checks passed
mypy (configured scope):             Success, no issues found in 57 source files
mypy + typing fixtures:              Success, no issues found in 59 source files
schema validation:                   165 passed (unchanged)
Layer-05 ToolRegistry canonical:      9 passed (unchanged) + 7 harness-validation tests (unchanged)
Runtime canonical (regression):      26 passed (unchanged)
Session canonical (regression):      20/20 passed (unchanged)
XFORM canonical (regression):        14/14 passed (unchanged)
Layer-06 canonical:                   10 discovered / 10 executed / 10 passed / 0 deferred (unchanged)
manifest parse + unique-ID audit:    65 / 65 unique (unchanged count; TOOL-005/TOOL-003 rule
                                      text corrected in place, no rows added or removed)
```

Reproduce via (from `minion-agent-python/`): `uv run pytest`, `uv run ruff check .`,
`uv run mypy src/minion_agent`, `uv run mypy src/minion_agent tests/typing/valid_message_
construction.py tests/typing/valid_tool_construction.py`.

New tests added this pass, all in `tests/tools/test_post_execute.py`, exercising the raw public
registration seam directly (not only `register_after_tool_call_hook`):

```text
test_a_raw_event_listener_cannot_replace_execution_identity
test_a_raw_event_listener_may_still_change_allowed_fields
test_in_place_mutation_of_the_result_is_structurally_impossible
test_mixed_raw_and_helper_listeners_share_the_same_authority
test_middle_listener_failure_skips_later_listeners_with_a_raw_listener_present
```

---

## 5. Explicitly out of scope for this package

Identical to the first package's §5 (which is itself identical to the original package's §6),
plus: `L06-R002`, `L06-R004`, and `L06-R005` — already confirmed resolved by the prior re-review,
not reopened, and not touched by this narrow pass (see §2). Rust Layer 06 implementation and
Layer 07 remain out of scope regardless of this package's outcome.

## 6. Expected outcome

```text
LAYER 06 SHARED CONTRACT
    APPROVED
```

or a precise rejection naming exactly which field, rule, or boundary is not language-neutral or
not Pi-compatible — using fresh finding IDs if new issues are found, not reusing `L06-R001`,
`L06-R003`, or `L06-R006` for anything other than confirming those exact three are now resolved.
If approved, Rust's own implementation-timing adjudication follows, per the same
review-before-remediation workflow used at every prior layer this session.
