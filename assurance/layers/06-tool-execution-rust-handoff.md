# Layer 06 (Tool Execution Pipeline) — Rust Implementation-Owner Re-Review Package

**Prepared:** 2026-08-26
**Prepared by:** Claude (Python/shared-contract owner, per the adopted workflow)
**Why this exists:** the first Layer-06 candidate (`minion-agent@ee563ff`,
`minion-agent-docs@e96c154`) was independently reviewed by Rust and **REJECTED** on exactly six
findings (`assurance/layers/06-tool-execution-rust-review.md`): `L06-R001`, `L06-R002` (both
`PI_PARITY_DEFECT`), and `L06-R003`..`L06-R006` (`CONTRACT_ASSURANCE_DEFECT`). This package
requests a **fresh, independent** re-review of the repaired candidate. Python self-certifying
after repair does not constitute Rust approval.

**Do not modify Rust in response to this package without first recording a verdict.**

---

## 1. The six repairs since the rejected candidate (`e96c154ac760ff4e1f06bcec4c14be588e470a18`)

```text
L06-R001 (PI_PARITY_DEFECT)

before:
    Python's _validate() exempted a raw, object-valued JSON-Schema dict from validation
    entirely; the canonical schema-validation scenario used a Python-specific
    parameters: {requires: [...]} shorthand that dynamically built a Pydantic model,
    never exercising the approved cross-language schema boundary.

after:
    _validate() validates BOTH representations for real: a pydantic-model-backed tool via
    pydantic; a raw, object-valued JSON-Schema dict via the general `jsonschema` library
    against the exact schema Layer 05 approved (now a real production dependency, not
    dev-only). Pi's TypeBox-specific coercion algorithm remains deliberately unreproduced
    byte-for-byte -- a disclosed, narrower divergence, not a validation exemption. The
    canonical scenario now uses a plain JSON Schema mapping.

L06-R002 (PI_PARITY_DEFECT)

before:
    Every generic exception-handling branch formatted f"{type(error).__name__}: {error}",
    unconditionally prefixing the Python runtime class name (e.g. "RuntimeError: boom").

after:
    All three sites (prepare/before-hook failure, execute() failure, after-hook failure) use
    the bare error message (str(error)) with no class-name prefix, matching pinned Pi's own
    error.message-only convention exactly. Canonical scenario expectations corrected; three
    unit tests strengthened from substring containment to exact equality, so they actually
    prove the prefix is gone.

L06-R003 (CONTRACT_ASSURANCE_DEFECT)

before:
    tools/post-execute was a waterfall over the entire, frozen ToolResult -- a listener could
    return/replace the whole result, observably rewriting tool_call_id, tool_name, or
    added_tool_names, none of which pinned Pi's AfterToolCallResult type allows a hook to
    touch at all.

after:
    New AfterToolCallOverride type carries exactly Pi's five AfterToolCallResult fields, with
    no slot for identity/added_tool_names. New register_after_tool_call_hook() is the only
    sanctioned registration path: a hook returns an override (or None); the framework merges
    it field-by-field. All test/runner call sites migrated; the smoking-gun test proving the
    old whole-result-replacement capability was replaced with one proving it is gone.

L06-R004 (CONTRACT_ASSURANCE_DEFECT)

before:
    The candidate changed exactly ten Layer-06 scenarios, but assurance prose, the freeze
    gate, and the handoff said nine/9 throughout.

after:
    Every current-candidate surface now says ten/10, with the list re-numbered 1-10.
    Historical review artifacts are untouched.

L06-R005 (CONTRACT_ASSURANCE_DEFECT)

before:
    spec/assurance/manifest claimed "no AbortSignal-equivalent type exists in either
    language" -- false for Rust, which already reserves ToolExecutionSignal/
    ToolExecutionRequest.signal in tools/definition.rs.

after:
    Replaced with the accurate asymmetry: Python has no signal abstraction yet; Rust already
    reserves one, unused. The defer itself (behavioral, not architectural) remains accepted --
    only the stated basis was corrected. No Rust file read or modified differently.

L06-R006 (CONTRACT_ASSURANCE_DEFECT)

before:
    The N-listener extension was classified inconsistently: PARITY_NEUTRAL_HARDENING in
    assurance, an undispositioned "deliberate Minion addition" in spec, plain `adopted` with
    no separate requirement in the manifest.

after:
    Classified consistently everywhere as an intentional Minion architectural extension over
    a directly-Pi-compatible single-listener baseline. TOOL-004/TOOL-005 each now state both
    the baseline and the extension explicitly. Resolved together with L06-R003, as the review
    itself directed.
```

**Reviewed commits (delta candidate):** see the covering commit messages; committed on top of
`minion-agent@ee563ffad65f1c8624536cbf8cc65dc395efe39a` and
`minion-agent-docs@d090b3ca79a66ca74117646210ce643c7264130b` (the merged review artifact).

**Pinned Pi revision:** `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged).

---

## 2. Scope (unchanged)

Identical to the first package's §1. None of the six repairs touch prepare-before-validation
ordering, execution-mode scheduling, sequential contagion, parallel start/end/result ordering,
failure isolation, the length-stop rule, late-update suppression, namespace treatment, the
terminate ownership boundary, or the `pendingToolCalls` Layer-07+ deferral -- the review did not
reject any of those, and this package does not reopen them.

---

## 3. Rust's required verdict, per repair

1. **`L06-R001`:** confirm `_validate()` genuinely validates a raw, object-valued JSON-Schema
   `dict` (not merely accepting it unchecked), and that the canonical
   `schema-validation-failure-becomes-tool-error` scenario's `parameters:` is a plain JSON Schema
   mapping, not a Pydantic-shaped shorthand. Independently judge whether Rust's own idiomatic
   validation approach can satisfy "arguments conform to the supplied schema" without needing
   TypeBox's exact coercion semantics (this package does not presume that answer).
2. **`L06-R002`:** confirm no canonical expectation or unit-test assertion anywhere in the
   Layer-06 delta still permits/requires a Python exception-class-name prefix, checking by exact
   equality, not substring containment.
3. **`L06-R003`:** confirm `AfterToolCallOverride`/`register_after_tool_call_hook` genuinely make
   whole-result replacement structurally impossible through the sanctioned API, and that every
   test/runner call site was migrated (no lingering raw `ctx.events.on(TOOLS_POST_EXECUTE, ...)`
   registration exercising the old capability anywhere in the delta).
4. **`L06-R004`:** re-discover the actual Layer-06 scenario count directly from the repository
   (do not trust this package's own "10") and confirm every current-candidate surface agrees with
   what you find.
5. **`L06-R005`:** confirm directly against `minion-agent-rust/crates/minion-agent/src/tools/
   definition.rs` that `ToolExecutionSignal`/`ToolExecutionRequest.signal` exist as stated, and
   that the corrected spec/manifest wording accurately describes the asymmetry.
6. **`L06-R006`:** confirm the single-listener case is genuinely unchanged (still exactly
   Pi-compatible) and that the N-listener fold's ordering/failure semantics are documented
   precisely enough for Rust to reproduce independently.

---

## 4. Fresh Python evidence to reproduce, not merely trust

```text
full pytest (coverage enabled):     909 passed, 19 xfailed, 0 failed, 100.00% coverage
ruff check .:                        All checks passed
mypy (configured scope):             Success, no issues found in 57 source files
mypy + typing fixtures:              Success, no issues found in 59 source files
schema validation:                   165 passed (unchanged)
Layer-05 ToolRegistry canonical:      9 passed (unchanged) + 7 harness-validation tests (unchanged)
Runtime canonical (regression):      26 passed (unchanged)
Session canonical (regression):      20/20 passed (unchanged)
XFORM canonical (regression):        14/14 passed (unchanged)
Layer-06 canonical:                   10 discovered / 10 executed / 10 passed / 0 deferred
manifest parse + unique-ID audit:    65 / 65 unique
```

Reproduce via (from `minion-agent-python/`): `uv run pytest`, `uv run ruff check .`,
`uv run mypy src/minion_agent`, `uv run mypy src/minion_agent tests/typing/valid_message_
construction.py tests/typing/valid_tool_construction.py`.

---

## 5. Explicitly out of scope for this package

Identical to the first package's §6, plus: none of the previously-approved (non-rejected) Layer-06
semantics are reopened by this package -- see §2.

## 6. Expected outcome

```text
LAYER 06 SHARED CONTRACT
    APPROVED
```

or a precise rejection naming exactly which field, rule, or boundary is not language-neutral or
not Pi-compatible — using fresh finding IDs if new issues are found, not reusing `L06-R001`..
`L06-R006` for anything other than confirming those exact six are now resolved. If approved,
Rust's own implementation-timing adjudication follows, per the same review-before-remediation
workflow used at every prior layer this session.
