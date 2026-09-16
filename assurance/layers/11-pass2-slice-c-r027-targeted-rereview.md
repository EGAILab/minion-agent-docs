# Layer 11 Pass 2 Slice C — R027 targeted convergence re-review

## Exact target

```text
code PR #33
    a51bfcd8e34be0c9d0b72f935321ffb50804a5f0

docs PR #92
    c04f00a6309336fc697c41a2aa4d622599792370

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699

previous targeted review
    minion-agent-docs PR #103
    b16a1686143fb7da3c48dbaec344b3eae312c80c
```

Both candidate heads were fetched, open, ready, unmerged, and remote-reachable. The code diff from
the previous targeted candidate contains only the one missing parser witness and matching manifest
evidence. No production, Rust, or Layer 12 file changed.

## L11-SC-R027

`PROVISIONALLY CLOSED` at `a51bfcd8e34be0c9d0b72f935321ffb50804a5f0`.

The complete agreed witness matrix now exists through the real parser seam:

```text
?code=abc&state=xyz
    code="abc", state="xyz"

?code=&state=xyz
    code="", state="xyz"

??code=1
    code absent
```

The new empty-value case proves present-empty remains distinct from absent after exactly one leading
question mark is removed.

Independent mutation verification used a detached worktree of the exact candidate and explicitly
printed the imported production module path before running the tests:

```text
imported module
    <detached worktree>/minion-agent-python/src/minion_agent/auth/openai_codex_oauth.py

mutation
    revert to parse_qs(value, keep_blank_values=True)

result
    non-empty leading-? witness: FAIL
    present-empty leading-? witness: FAIL
    double-? boundary witness: PASS
```

This is the expected discriminating trace: the first two require stripping the one leading
character; the third must remain unchanged by that fix.

## Checks

```text
three R027 witnesses
    3 passed on the unmodified candidate

manifest validation
    8 passed

ruff
    PASS

mypy
    PASS; 75 source files
```

## Verdict

```text
L11-SC-R025
    PROVISIONALLY CLOSED (unchanged from PR #103)

L11-SC-R027
    PROVISIONALLY CLOSED

all known Slice-C findings
    PROVISIONALLY CLOSED

Python Slice C
    NOT YET CERTIFIED — final-complete review pending

Rust Slice C
    NOT_IMPLEMENTED / BLOCKED

Layer 12
    NOT STARTED
```

The exact unchanged candidate is now eligible for one complete independent section 11.8.8 review.
This targeted result is not final Slice-C approval or certification.
