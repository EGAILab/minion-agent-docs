# Layer 11 Pass 2 Slice C — convergence targeted-closure re-review 2

## Exact target

```text
code PR #33
    f96740c821a0226033cfadfe7a7e8e55f0b117c4

docs PR #92
    eed2538969cc562cc6a8dfbdd4206e5f82703243

base main
    ea3b64caca84e95245fa0d5f2a1a650452686649

base docs master
    1e3c224ed7912d51fa28f33563622e5155947cda

prior targeted re-review
    minion-agent-docs PR #94
    7e46d3d796b0b84b0dfefb952d3727c5095e109c

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

The exact candidate heads were fetched from GitHub and verified open, Ready for Review, unmerged,
and identical to issue #29's handoff. Issue #29 is open and names `NEXT_OWNER: Codex`. This is the
workflow section 11.8.7 targeted review of the sole remaining finding, not the final section
11.8.8 complete review.

## Verdict

```text
targeted convergence closure
    APPROVED

L11-SC-R011
    PROVISIONALLY CLOSED

L11-SC-R012
    PROVISIONALLY CLOSED

L11-SC-R018
    PROVISIONALLY CLOSED

L11-SC-R021
    PROVISIONALLY CLOSED

final complete review
    REQUIRED / NOT YET PERFORMED

Rust Layer 11 Pass 2 Slice C
    NOT STARTED

Layer 12
    NOT STARTED
```

## L11-SC-R011 closure

The candidate now implements the full Web IDL scalar-value-string conversion rather than treating
each surrogate-range Python code point independently:

- a high surrogate immediately followed by a low surrogate is combined with the standard UTF-16
  formula;
- a high surrogate without an immediate low partner is replaced with `U+FFFD`;
- a low surrogate not consumed as the second half of a valid pair is replaced with `U+FFFD`;
- ordinary Unicode scalar values, including already-combined astral values, pass unchanged;
- only the value passed to WHATWG URL construction is converted; Pi's fallback branches retain
  the original string.

The prior exact witness now matches pinned Pi/Node:

```text
input query value
    chr(0xD83D) + chr(0xDE00)

pinned Pi / Node
    "😀"

candidate
    "😀"
```

Additional reviewer probes also match Node's scalar-value conversion:

```text
high + low          -> 😀
low + high          -> ��
high + "a"          -> �a
high + high + low   -> �😀
low + high + low    -> �😀
high + low + low    -> 😀�
```

The direct helper evidence distinguishes an explicit adjacent surrogate pair from an
already-combined astral Python scalar. The end-to-end URL witness proves the real
`parse_authorization_input` seam uses the converter. The spec and manifest now describe the full
pair-aware algorithm and no longer make the prior false claim that every Python surrogate code
point is necessarily unpaired.

No active uncertainty, parity defect, or contract-assurance defect remains within the agreed
convergence surface. This is provisional finding closure only; workflow section 11.8.8 still
requires one complete independent review of these exact final candidate SHAs.

## Fresh evidence

```text
focused Slice-C tests
    PASS — 114 passed

full pytest
    PASS — 1472 passed, 19 xfailed

coverage
    PASS — 100.00% (3845 statements)

ruff
    PASS

mypy
    PASS — 75 source files

schema / manifest validation
    PASS — 213 passed

reviewer USVString sequence probes
    PASS — 6/6 matched Node
```

## Findings

```text
PI_PARITY_DEFECT
    none active within the targeted convergence surface

CONTRACT_ASSURANCE_DEFECT
    none active within the targeted convergence surface

PI_BEHAVIOR_UNCERTAIN
    none

PARITY_NEUTRAL_HARDENING
    none

PARITY_CONSTRAINED_RISK
    none
```

The exact candidate is eligible for the mandatory final complete review. Do not merge it, start
Rust Slice C, or start Layer 12 on the strength of provisional closure alone.
