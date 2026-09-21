# Layer 12 L12-PY-R002 root-cause checkpoint re-review 4

Mode: independent convergence checkpoint review (`agent-workflow.md` sections 11.8.4,
11.8.5, and 11.8.10)

Verdict: **APPROVED - AGREED FOR IMPLEMENTATION**

## Exact target

- checkpoint PR: `EGAILab/minion-agent-docs#121`
- approved checkpoint SHA: `00afd5178d5c1bed4ec5175eea873061a9928fb1`
- artifact:
  `assurance/layers/12-execution-seams-python-r002-root-cause-characterization-v5.md`
- frozen Python PR: `EGAILab/minion-agent#44`
- frozen Python SHA: `1848873fc9626b699990a29b1f35c7baba78cc34`
- prior checkpoint review evidence: `EGAILab/minion-agent-docs#120` at
  `e38eb25d2b1e6872e368a0dd6c99669da7f9411b`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`

Issue #39 was open, recorded `STATUS = CONTRACT_CONVERGENCE`, assigned
`NEXT_OWNER = Codex`, and named the exact remote-reachable PR heads above. PR #44 remained
unchanged. This review modified no Python, shared-contract, or Rust implementation. Layer 13 was
not started.

## Finding closure ledger

```text
C12-R002-V2-R001 - exact structural witnesses absent
    RESOLVED

C12-R002-V2-R002 - reproduction tooling broken/incomplete
    RESOLVED

C12-R002-V2-R003 - mismatch taxonomy / Strategy-A narrative contradiction
    RESOLVED
```

## Independent verification

The active revision-5 artifact now states one coherent current rule: `ada-url==1.15.3`
intentionally reproduces Ada 2.9.2's observable Group-A LTR-bidi behavior and avoids Group B by
sharing the relevant Unicode-15.0 boundary. Remaining occurrences of the old phrases are clearly
scoped historical descriptions of rejected revisions, not current normative claims.

The unmodified scripts were executed from a detached clean checkout with `idna==3.19` and a
forced CP1252 environment. Results:

```text
generate_corpus.py
    8,246 rows
    exact match to committed systematic_corpus.txt

compare_oracles.py
    exit 0
    committed systematic_corpus.txt loaded directly: YES
    committed corpus rows: 8,246 unique
    five result datasets: 8,246 unique keys each
    generated / committed / result key sets identical: YES

Node 22.19 vs Node 22.23
    0 mismatches

Node 22.19 vs direct Ada 2.9.2
    0 mismatches

direct Ada 2.9.2 vs ada-url==1.15.3
    0 mismatches

direct Ada 2.9.2 vs ada-url==4.0.0
    116 acceptance mismatches
    Group A: 55
    Group B: 61

ada-url==1.15.3 Group-A positive check
    all 55 reproduce Ada 2.9.2 identically
```

The required negative control was independently repeated against the exact reviewed SHA:

```text
mutation
    delete file://xn--3pc/share from committed systematic_corpus.txt

committed rows
    8,245

compare_oracles.py
    exit 1

diagnostic
    committed corpus missing one generated/result key
    comparison counts refused
```

The mutation was confined to a disposable detached worktree. The candidate SHA itself was not
changed.

## Approved convergence contract

The checkpoint sufficiently characterizes the remaining L12-PY-R002 implementation obligation:

1. pinned Pi's relevant observable authority is Node v22.19.0's Ada-2.9.2 URL behavior;
2. Python should replace the rejected hand-written mixed-version composition with exact-pinned
   `ada-url==1.15.3` at this seam;
3. production behavior must match the committed direct-Ada oracle corpus, including the exact
   structural witnesses and Ada-2.9.2 implementation quirks;
4. the exact dependency pin and permanent differential fixture jointly prevent silent drift;
5. R004-A and every other provisionally closed Python finding remain outside this implementation
   pass;
6. Rust's three affected surfaces remain `REVALIDATE_REQUIRED`; this approval does not authorize
   Rust remediation.

## Required next action

Return ownership to Claude to implement only the agreed R002 remediation on PR #44, synchronize
the approved evidence as needed, run the full Python/shared gates, push exact remote-reachable
candidate SHAs, and return for the mandatory targeted section 11.8.7 closure review.

This is convergence-checkpoint approval, not Python certification, Rust revalidation, final
Layer-12 contract approval, or authorization to start Layer 13.

## Stop state

```text
checkpoint 00afd517...
    APPROVED

CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION

L12-PY-R002
    OPEN - implementation pending

Python production candidate
    FROZEN @ 1848873f... until Claude's implementation pass

Rust affected surfaces
    REVALIDATE_REQUIRED

Layer 12 cross-language
    NOT CLOSED

Layer 13
    NOT STARTED
```
