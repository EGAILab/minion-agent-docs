# Layer 11 Pass 2 Slice C — R025/R027 targeted convergence review

## Exact target

```text
code PR #33
    fba888a70bf26f4ae94d1b6fbbe74e14a4ff24af

docs PR #92
    c04f00a6309336fc697c41a2aa4d622599792370

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699

convergence-triggering review
    minion-agent-docs PR #102
    1241a2749dbb04feef373717f0c14e0d19358c4f
```

The remote heads matched issue #29 and were open, ready, unmerged, and remote-reachable. The
candidate contains no Rust changes and Layer 12 has not started.

Issue #29 requested a final-complete review directly. The preceding convergence review explicitly
required targeted section 11.8.7 closure first, followed by a final-complete review only after all
findings closed. This artifact records that mandatory targeted gate; it does not silently skip it.

## Targeted result

### L11-SC-R025 — PROVISIONALLY CLOSED

Both agreed witnesses now genuinely prove cleanup is attempted:

- the successful-close path restores `assert created[0].is_closed`;
- the raising-close path records and asserts `close_attempted` while independently asserting the
  original request error remains observable.

Independent mutation against a detached worktree of the exact candidate deleted the complete
pre-response owned-client cleanup block. Both tests then failed at their cleanup observations.
R025 is provisionally closed at `fba888a70bf26f4ae94d1b6fbbe74e14a4ff24af`.

### L11-SC-R027 — STILL OPEN

Two of the three agreed witnesses now exist:

```text
?code=abc&state=xyz
    code="abc", state="xyz"

??code=1
    code absent
```

The first fails when the production fix is reverted; the second correctly proves only one leading
question mark is special.

The third binding witness from the convergence-triggering review remains absent:

```text
?code=&state=xyz
    code="", state="xyz"
```

This case is not redundant. It proves the boundary preserves the observable distinction between a
present-but-empty value and an absent value after the leading question mark is removed — one of the
project's explicit cross-language contract hazards. A plausible special-case implementation that
handles only non-empty `code` still passes the two newly-added tests while violating the agreed
empty-value rule.

Minimal remediation: add the exact empty-value witness above through the real
`parse_authorization_input` seam. It must fail an implementation that returns `None` for that
input. No production or shared semantic change is currently indicated.

## Independent checks

```text
unmodified targeted tests
    20 passed

manifest validation
    8 passed

ruff
    PASS

mypy
    PASS; 75 source files

combined mutation (remove cleanup + revert leading-question-mark fix)
    3 failures, 1 pass
    failures were the two R025 witnesses and the non-empty R027 witness
```

## Verdict

```text
L11-SC-R025
    PROVISIONALLY CLOSED

L11-SC-R027
    STILL OPEN — CONTRACT_ASSURANCE_DEFECT

Layer 11 Pass 2 Slice C
    REJECTED / CONTRACT_CONVERGENCE CONTINUES

Python Slice C
    NOT CERTIFIED

Rust Slice C
    NOT_IMPLEMENTED / BLOCKED

Layer 12
    NOT STARTED
```

The candidate is not eligible for the final-complete section 11.8.8 review yet. Add the one missing
R027 empty-value witness, then return the changed exact SHA for another targeted closure review.
After every convergence finding is provisionally closed, one final complete review remains
mandatory.
