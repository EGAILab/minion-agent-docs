# Layer 12 L12-PY-R002 root-cause checkpoint re-review 3

Mode: independent convergence checkpoint review (`agent-workflow.md` sections 11.8.4,
11.8.5, and 11.8.10)

Verdict: **REJECTED - CHECKPOINT NOT AGREED FOR IMPLEMENTATION**

## Exact target

- checkpoint PR: `EGAILab/minion-agent-docs#121`
- reviewed checkpoint SHA: `28eda819295355b97e8e5072b02af5fdcc87f347`
- artifact:
  `assurance/layers/12-execution-seams-python-r002-root-cause-characterization-v4.md`
- frozen Python PR: `EGAILab/minion-agent#44`
- frozen Python SHA: `1848873fc9626b699990a29b1f35c7baba78cc34`
- prior checkpoint review evidence: `EGAILab/minion-agent-docs#120` at
  `93a44820695d4ec6ce413230cfa0dac1b31d2663`
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
    PARTIALLY RESOLVED - blocking committed-corpus omission remains

C12-R002-V2-R003 - mismatch taxonomy / Strategy-A narrative contradiction
    STILL OPEN - one active contradictory sentence remains
```

## Independently confirmed corrections

Under a forced CP1252 environment, both scripts now complete successfully because they configure
UTF-8 output. Running the generator with `idna==3.19` produces 8,246 rows exactly matching the
committed corpus. The generator rejects a different installed `idna` version. The comparator now
rejects duplicate keys within loaded result files and verifies that the five loaded result files
share the generated 8,246-key set.

The comparator reproduces zero Node/Ada and Ada/1.15.3 mismatches, the 116 Ada/4.0 mismatches,
the 55/61 taxonomy, and explicitly checks that all 55 Group-A rows have identical Ada-2.9.2 and
`ada-url==1.15.3` outputs. These checks correctly support Strategy A.

## C12-R002-V2-R002 - verifier still ignores the committed permanent corpus

**Classification:** `CONTRACT_ASSURANCE_DEFECT`  
**Severity:** blocking

`compare_oracles.py` imports `generate_urls()` and compares each raw result file against that
freshly generated set. It never loads
`assurance/layers/data/12-python-r002-ada-oracle/systematic_corpus.txt`, despite listing that file
as a required input and despite the checkpoint naming the committed file as the permanent gate.

The defect was reproduced directly against the exact reviewed SHA:

```text
mutation
    delete file://xn--3pc/share from committed systematic_corpus.txt

committed corpus rows after mutation
    8,245

compare_oracles.py exit
    0

reported integrity
    all five result datasets share 8,246 generated keys
```

Thus the exact regression witness can disappear from the committed permanent fixture while the
claimed verifier remains green. The prior review explicitly required the verifier to load the
corpus and reject wrong counts, duplicates, and missing/extra keys; checking generated URLs and
raw outputs without checking the committed fixture does not close that requirement.

**Minimal correction:** load `systematic_corpus.txt` as its own checked input, reject duplicate
rows, and require exact ordered or key-set equality among the committed corpus,
`generate_urls()`, and every result dataset. Add a negative-control witness showing that deleting
or duplicating a committed corpus row makes the verifier exit nonzero.

## C12-R002-V2-R003 - active checkpoint prose still says the exact-match dependency lacks the bug

**Classification:** `CONTRACT_ASSURANCE_DEFECT`  
**Severity:** blocking

Revision 4 adds the correct explanation in section 8 and the comparator adds positive evidence,
but the same current artifact still says in section 6:

```text
Neither group affects the Strategy A recommendation (section 12):
ada-url==1.15.3 has neither defect (section 7).
```

That is the exact claim this revision says it corrected. It contradicts section 8 and the new
executable check proving `ada-url==1.15.3` reproduces all 55 Group-A rows identically. An exact
behavioral match must reproduce pinned Ada 2.9.2's observable LTR-bidi defect; doing so is why the
dependency is suitable for pinned-Pi parity.

**Minimal correction:** replace the residual sentence with the current rule: Strategy A is
unaffected because `ada-url==1.15.3` reproduces both the relevant Ada-2.9.2 Group-A behavior and
its Unicode-15.0 assignment boundary exactly. Re-scan the complete active artifact for equivalent
stale wording.

## Required next action

Return only the checkpoint/evidence package to Claude for a mechanical correction pass:

1. make the verifier validate the committed `systematic_corpus.txt` itself and add a negative
   control for removal/duplication of a committed row;
2. remove the one residual contradictory sentence from the current characterization;
3. preserve the independently confirmed exact witnesses, 55/61 taxonomy, portability fixes,
   explicit Group-A check, and Strategy A result;
4. return a new exact checkpoint SHA for independent review before implementation resumes.

PR #44 remains frozen. R004-A and the other provisional Python closures remain unchanged. Rust's
three affected surfaces remain `REVALIDATE_REQUIRED` and untouched.

## Stop state

```text
checkpoint 28eda819...
    REJECTED

L12-PY-R002
    OPEN

Strategy A
    PROVISIONALLY SOUND

Python production candidate
    FROZEN @ 1848873f...

AGREED FOR IMPLEMENTATION
    NO

Rust affected surfaces
    REVALIDATE_REQUIRED

Layer 12 cross-language
    NOT CLOSED

Layer 13
    NOT STARTED
```
