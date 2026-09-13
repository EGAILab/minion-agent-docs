# Layer 11 — L11-R013 convergence agreement

## Decision

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION
```

Exact checkpoint reviewed:

- code PR `EGAILab/minion-agent#25` at `fc78f40f0bb8da50281f6ace607f5f39edb8227d`;
- docs PR `EGAILab/minion-agent-docs#54` at `909dcff408ad96a6fd499c1933daa382bd668536`;
- pinned Pi at `b7bb00b936dbe21b8e160b3e89efdec361846699`;
- originating second final-complete review: docs PR #61 at
  `382bb4e04e1963ca52671c2d5aa7c3a7c1c8f014`, whose own embedded characterization is the §11.8.3
  artifact this document challenges and agrees.

The exact docs checkpoint and coordination issue #24 were fetched from GitHub. Issue #24 recorded
`STATUS = CONTRACT_CONVERGENCE` and `NEXT_OWNER = Claude`. This is convergence-challenge/agreement
evidence only; no candidate, shared semantic file, or Rust production was changed by writing this
document.

## Trigger check (agent-workflow.md §11.8, mandatory)

`L11-R013` was first raised by the first final-complete review (docs PR #60) and, after a first
remediation attempt, found STILL OPEN by the second final-complete review (docs PR #61) -- `same
material finding survives two independent reviews`, the first §11.8 OR-condition. Convergence is
therefore mandatory. `L11-R014`, raised for the first time by the same review, has not met either
trigger condition on its own and is handled as an ordinary point fix in the same implementation
pass (the review's own closing note: "R014 has not triggered convergence and may be handled as a
normal point fix, but both fixes may return as one exact candidate").

## Challenge pass (§11.8.4)

Independently re-verified, this pass, directly against pinned Pi source (not merely trusted from
the review's own embedded characterization):

- `packages/ai/src/auth/context.ts::defaultProviderAuthContext.fileExists` (full re-read): confirmed
  the ENTIRE method body -- the dynamic `node:fs/promises`/`node:os` module imports, the
  `os.homedir()` call, the tilde-concatenation itself, AND the `fs.access(resolved)` call -- sits
  inside ONE `try` block, with a single, bare `catch { return false; }` at the end that filters on
  no exception type whatsoever. This confirms the review's own characterization exactly: the prior
  (first) remediation had placed `os.path.expanduser("~")` (the Python equivalent of `os.homedir()`
  concatenation) OUTSIDE its own `try`, and had narrowed the `catch` to `except OSError`, both
  genuine deviations from this exact source shape, not merely plausible restatements of it.
- `packages/ai/src/auth/types.ts::AuthContext.fileExists` (re-read): confirmed the protocol-level
  requirement (leading `~` denotes the user's home, in some form) is unaffected by this finding --
  `L11-R013` concerns only `defaultProviderAuthContext`'s own concrete algorithm and failure
  boundary, exactly as the review's own ledger states ("L11-R008 CLOSED... L11-R013 STILL OPEN").

**Answering the §11.8.4 checklist:**

- *Is the Pi source mapping correct?* Yes, confirmed above -- the characterization's own behavior
  matrix and both "current candidate failures" rows match source exactly.
- *Is the behavior matrix complete enough to distinguish realistic wrong implementations?* Yes --
  it directly covers both ways the first remediation was wrong (a resolution-stage failure, and a
  non-`OSError` access-stage failure), which is precisely what discriminates a "wraps only the
  access call" implementation from a genuinely whole-operation one.
- *Are any cases implementation mechanics rather than observable semantics?* No -- "one failure
  boundary enclosing both resolution and access" and "no exception-type filter" are both directly
  observable behaviors (what input/failure produces what return value), not a Python-specific
  mechanism choice.
- *Does any proposed fix silently reopen a lower certified layer?* No. Nothing here touches Layer
  09's `RunSignal` or any other certified layer.
- *Can both Python and Rust implement the rule idiomatically?* Yes -- "resolve the path, then check
  the filesystem, with every step inside one error boundary that maps any failure to `false`" is a
  natural shape in both languages (a single `try`/`except Exception` in Python; a single `Result`-
  chained block collapsed to `Ok(false)` on any `Err` in Rust, with no special-casing of a
  particular error variant).
- *Does the defect's own root cause depend on an extensibility point one language's own certified
  lower layers exposes and the other does not?* No -- pure vocabulary/control-flow semantics, no
  cross-layer extensibility point involved.
- *Are all previous review findings represented by an executable or documentary acceptance
  criterion?* Yes, via the characterization's own three witnesses (retain the existing `~suffix`
  witness; add an injected home-resolution failure witness; add an injected non-`OSError` access
  failure witness), all adopted below unchanged.

No revision to the characterization's own Pi/source audit, behavior matrix, or witness list is
required -- the challenge confirms all of it as correct and sufficiently discriminating.

## Agreed observable matrix (adopted from the characterization unchanged)

| Observation | Required result |
|---|---|
| ordinary existing path | `True` |
| ordinary absent path | `False` |
| `~suffix` with a known `<home><suffix>` target | `True` (literal concatenation, no separator) |
| home-directory resolution itself raises | `False` |
| filesystem access raises `OSError` | `False` |
| filesystem access raises a non-`OSError` ordinary exception | `False` |

## Agreed implementation and evidence constraints

The implementation pass must:

- keep the already-correct literal `home + suffix` concatenation from the first remediation
  unchanged (the `~suffix` witness already passes and must keep passing);
- wrap resolution AND access together in ONE `try`, with NO exception-type filter narrower than
  the ordinary Python operation-error domain (`Exception`, not a specific subclass);
- add the home-resolution-failure witness and the non-`OSError` access-failure witness as permanent
  regression evidence, alongside the already-existing `OSError`-during-access witness;
- not weaken the protocol-level leading-tilde requirement (`L11-R008`, unaffected, remains closed);
- not introduce a provider-specific credential-file read or any browser-specific branch (both
  explicitly out of scope, matching the characterization's own "OUT OF SCOPE" list).

The normative `spec/auth.md`/`PROV-006` deltas: the characterization notes the general prose rule
was already correct and only implementation/evidence needed to catch up; this pass nonetheless
sharpens the wording (explicitly naming "including home-directory resolution itself" and "filtered
to no particular exception type") so a future implementer cannot repeat the exact same narrowing
this finding twice caught.

## Scope and feasibility

No certified lower layer needs reopening. Rust can implement the agreed whole-operation failure
boundary idiomatically once the shared/Python candidate is coherent. No Rust implementation is
authorized by this document; Rust Layer 11 remains blocked until the remediated shared/Python
candidate (this fix plus the co-located `L11-R014` point fix) is independently reviewed and
approved under the normal workflow.

Real provider transport, browser OAuth, and Layer 12 remain out of scope and untouched.

## Agreement status

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION

OPEN FINDING
    L11-R013

CHALLENGE FINDINGS
    (none -- the characterization's own Pi/source audit and behavior matrix were confirmed correct
    on challenge; no revision was required before implementation)

NEXT OWNER
    Claude

NEXT ACTION
    Implement L11-R013 per the agreed matrix and constraints above, in the same pass as the
    co-located L11-R014 point fix, add the agreed witnesses, synchronize spec/manifest, rerun the
    full suite including every previously-closed L11-R001 through L11-R012 test, and return the
    exact remote candidate for a new complete review.
```

This agreement is a convergence checkpoint, not final contract approval or Layer-11 certification.
A new complete exact-SHA review remains mandatory once this fix (and `L11-R014`) are implemented.
