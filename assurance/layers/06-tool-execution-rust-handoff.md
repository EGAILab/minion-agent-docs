# Layer 06 (Tool Execution Pipeline) — Rust Implementation-Owner Final Closure Review Package (round 2)

**Prepared:** 2026-08-26
**Prepared by:** Claude (Python/shared-contract owner, per the adopted workflow)
**Why this exists:** the previous narrow repair to `L06-R003`/`L06-R006` was independently
re-reviewed by Rust as a final-closure check
(`assurance/layers/06-tool-execution-rust-final-closure.md`). That review confirmed `L06-R001`,
`L06-R002`, `L06-R004`, and `L06-R005` resolved, and reopened `L06-R003`/`L06-R006` again on a
**narrower** defect than either finding originally described: the prior fix restored protected
after-hook fields only once, after the entire `tools/post-execute` waterfall completed, which left
a gap where a listener earlier in the chain could delegate a forged replacement and the very next
listener could observe it before the end-of-waterfall restoration ever ran. This package requests
a fresh, independent, final closure review of the per-listener repair. Python self-certifying after
repair does not constitute Rust approval.

**Do not modify Rust in response to this package without first recording a verdict.**

---

## 1. The repair since the reviewed candidate

```text
L06-R003 (PI_PARITY_DEFECT) / L06-R006 (CONTRACT_ASSURANCE_DEFECT) -- resolved together again,
as both prior rounds directed, since both concern the same production seam.

before:
    _finalize() (execute.py) snapshotted tool_call_id/tool_name/added_tool_names before
    dispatching the tools/post-execute waterfall, and restored them from that snapshot AFTER
    the waterfall completed. This made the FINAL ToolResult's identity/added_tool_names
    unforgeable, but did nothing about what an intermediate listener could see: a raw listener
    delegating via next(replacement) passed `replacement` straight to the next listener,
    unmodified, since EventBus.waterfall's next() has no way to intercept that handoff. The
    Rust final-closure review reproduced this directly: a raw listener delegated a forged
    tool_call_id="evil-id"/tool_name="evil-name"/added_tool_names=("evil",); a
    helper-registered listener running after it read those (still-forged) values off the
    ToolResult it received and copied them into its own AfterToolCallOverride.details --
    making the forgery observable in the final result after all, through a field the fix
    never touched.

after:
    EventBus.waterfall (runtime/events.py) gained one new, optional keyword parameter,
    normalize_step: Callable[[tuple], tuple] | None = None. When supplied, it runs on
    whatever a listener passes to next(...) BEFORE the next listener receives it. Every other
    event's dispatch is byte-for-byte unchanged (the parameter defaults to None and nothing
    else in the codebase passes it) -- additive, not a redesign, and no second/parallel hook
    dispatch mechanism was introduced. _finalize now passes a normalize_step closure that
    restores the same protected baseline (tool_call_id/tool_name/added_tool_names, captured
    before the waterfall starts) onto whatever ToolResult is about to become the NEXT
    listener's input, leaving every Pi-allowed field (content/details/is_error/usage/
    terminate) exactly as the delegating listener produced it. The existing end-of-waterfall
    restoration is RETAINED, unchanged, because a listener that short-circuits instead of
    calling next has no downstream listener for normalize_step to protect, and that value
    still needs correcting before it becomes the whole waterfall's own return value. Three
    enforcement points now work together: normalize_step (new, at every next() delegation),
    end-of-waterfall restoration (unchanged, for a short-circuiting last listener), and
    ToolResult's frozen-dataclass in-place-mutation guarantee (pre-existing, unrelated to
    this pass). None is redundant with the others; none was removed to add another.
```

**Reviewed commits (delta candidate):** see the covering commit messages; committed on top of
`minion-agent-docs@573c11521c22b89aef53f83f70b48dfcf19dfbc8` (the merged Rust final-closure review
artifact) and the corresponding `minion-agent` candidate
(`minion-agent@4185fa6c8e7baf311f1bc4652c9f90e240bff070`).

**Pinned Pi revision:** `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged).

---

## 2. Scope (unchanged, narrower still than the previous package)

Identical to the previous package's §2. This package does **not** reopen `L06-R001`, `L06-R002`,
`L06-R004`, or `L06-R005` — the final-closure review already confirmed all four resolved, no code
or documentation touched by those findings changed in this pass. Do not re-litigate them; a
verdict on this package should treat them as settled. This pass also does not touch the before-hook
waterfall (`tools/pre-execute`), which was never implicated in any of the three review rounds.

---

## 3. Rust's required verdict, per repair

1. Confirm `EventBus.waterfall` (`runtime/events.py`) genuinely applies `normalize_step` to a
   listener's `next(replacement)` argument before the *next* listener in the chain receives it —
   not merely before the waterfall's own final return.
2. Independently reproduce (or verify the delta's own test reproduces) the exact scenario the
   final-closure review used: a raw listener delegates a `ToolResult` with a forged
   `tool_call_id`/`tool_name`/`added_tool_names`; a listener running after it reads the current
   result and copies those three fields into an allowed field (`details`). Confirm the observing
   listener sees the **original** values, not the forgery, and that this holds regardless of which
   registration path (`register_after_tool_call_hook` or raw `ctx.events.on(TOOLS_POST_EXECUTE,
   ...)`) produced either listener, and regardless of registration order.
3. Confirm `normalize_step` does not discard or reset legitimately accumulated Pi-allowed fields
   (`content`, `details`, `is_error`, `usage`, `terminate`) that earlier listeners produced with no
   attack involved — the fix must be scoped to the three protected fields only.
4. Confirm the end-of-waterfall restoration in `_finalize` was retained (not replaced) and still
   covers the case where the *last* active listener short-circuits instead of delegating via
   `next`, since `normalize_step` cannot reach a value that never passes through `next`.
5. Confirm `EventBus.waterfall`'s new parameter is genuinely additive: every event other than
   `tools/post-execute` dispatches identically to before, since no other call site passes
   `normalize_step`.
6. Confirm no second, parallel hook-registration or hook-dispatch mechanism was introduced —
   `register_after_tool_call_hook` and raw `ctx.events.on(TOOLS_POST_EXECUTE, ...)` still
   participate in the same single ordered waterfall.
7. **Regression-only confirmation (not re-review) for `L06-R001`, `L06-R002`, `L06-R004`,
   `L06-R005`:** spot check that nothing in this narrow delta touched the files/behaviors those
   findings closed — a confirmation that scope discipline held, not a re-audit of the findings
   themselves.

---

## 4. Fresh Python evidence to reproduce, not merely trust

```text
full pytest (coverage enabled):     917 passed, 19 xfailed, 0 failed, 100.00% coverage
ruff check .:                        All checks passed
mypy (configured scope):             Success, no issues found in 57 source files
mypy + typing fixtures:              Success, no issues found in 59 source files
schema validation:                   165 passed (unchanged)
Layer-05 ToolRegistry canonical:      9 passed (unchanged) + 7 harness-validation tests (unchanged)
Runtime canonical (regression):      26 passed (unchanged)
Session canonical (regression):      20/20 passed (unchanged)
XFORM canonical (regression):        14/14 passed (unchanged)
Layer-06 canonical:                   10 discovered / 10 executed / 10 passed / 0 deferred (unchanged)
manifest parse + unique-ID audit:    65 / 65 unique (unchanged count; TOOL-005's rule text and
                                      Python evidence pointer extended in place, no rows added
                                      or removed)
```

Reproduce via (from `minion-agent-python/`): `uv run pytest`, `uv run ruff check .`,
`uv run mypy src/minion_agent`, `uv run mypy src/minion_agent tests/typing/valid_message_
construction.py tests/typing/valid_tool_construction.py`.

New tests added this pass, all in `tests/tools/test_post_execute.py`:

```text
test_a_downstream_listener_cannot_observe_a_predecessors_forged_identity
    the exact reproduction from the final-closure review. Verified to fail against the
    pre-fix candidate (confirmed directly: reverting only execute.py/events.py to their
    prior committed state and re-running this test alone fails with the forged values) and
    to pass after the fix.
test_per_step_normalization_preserves_legitimate_accumulated_overrides
    three chained listeners, no attack -- proves the fix does not discard legitimate
    accumulated content/terminate overrides.
test_reversed_mixed_registration_order_shares_the_same_authority
    the inverse registration order of the existing mixed-path test (helper, then raw
    attacker, then a further helper observer).
```

---

## 5. Explicitly out of scope for this package

Identical to the previous package's §5, plus: this round's own predecessor fix (final-only
restoration) is superseded, not merely extended — do not evaluate it as a separate, still-valid
layer of protection; evaluate only the per-step `normalize_step` mechanism plus the retained
end-of-waterfall restoration, together, as described in §1. Rust Layer 06 implementation and
Layer 07 remain out of scope regardless of this package's outcome.

## 6. Expected outcome

```text
LAYER 06 SHARED CONTRACT
    APPROVED
```

or a precise rejection naming exactly which field, rule, or boundary is not language-neutral or
not Pi-compatible — using fresh finding IDs if new issues are found, not reusing `L06-R003` or
`L06-R006` for anything other than confirming those exact two are now resolved. If approved, Rust's
own implementation-timing adjudication follows, per the same review-before-remediation workflow
used at every prior layer this session.
