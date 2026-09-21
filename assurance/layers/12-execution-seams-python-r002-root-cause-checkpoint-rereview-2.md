# Layer 12 L12-PY-R002 root-cause checkpoint re-review 2

Mode: independent convergence checkpoint review (`agent-workflow.md` sections 11.8.4,
11.8.5, and 11.8.10)

Verdict: **REJECTED - CHECKPOINT NOT AGREED FOR IMPLEMENTATION**

## Exact target

- checkpoint PR: `EGAILab/minion-agent-docs#121`
- reviewed checkpoint SHA: `e433fce68d192f86d4514110cb9762377d09682a`
- artifact:
  `assurance/layers/12-execution-seams-python-r002-root-cause-characterization-v3.md`
- frozen Python PR: `EGAILab/minion-agent#44`
- frozen Python SHA: `1848873fc9626b699990a29b1f35c7baba78cc34`
- prior checkpoint review evidence: `EGAILab/minion-agent-docs#120` at
  `8c1469c1de13cf0a70dab9f6d4bcfd8abcd8e32e`
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
    STILL OPEN - blocking

C12-R002-V2-R003 - mismatch taxonomy contradicted
    PARTIALLY RESOLVED - blocking documentary contradiction remains
```

## Independently confirmed corrections

The exact four permanent rows are now the first four rows of `systematic_corpus.txt`:

```text
file://xn--3pc/share
file://xn--8g0n/share
file://xn--a-y5e/share
file://xn--a-8n62a/share
```

Running `generate_corpus.py` in an isolated Python 3.12 environment with `idna==3.19` produced
8,246 rows exactly matching the committed corpus. Every committed corpus/result file contains
8,246 unique keys with zero missing or extra keys.

With UTF-8 stdout forced externally, `compare_oracles.py` reproduces:

```text
Node 22.19 vs Node 22.23
    0 acceptance mismatches, 0 output mismatches

Node 22.19 vs direct Ada 2.9.2
    0 acceptance mismatches, 0 output mismatches

direct Ada 2.9.2 vs ada-url==1.15.3
    0 acceptance mismatches, 0 output mismatches

direct Ada 2.9.2 vs ada-url==4.0.0
    116 acceptance mismatches, 0 output mismatches

reported Group A / Group B split
    55 / 61
```

A fresh isolated `ada-url==1.15.3` run over all 8,246 rows also produced zero mismatches,
including the newly added exact witnesses. Strategy A therefore remains substantively supported.

The Group A source diagnosis is correct. Ada 2.9.2's LTR branch loops with
`i < last_non_nsm_char`, leaving the final non-NSM character unchecked. Exact Node v22.19.0
spot checks reproduced the proposed controls:

```text
file://xn--ab-wld/share
    accepted as an LTR label ending in Hebrew ALEF

file://xn--ab-uld/share
    rejected through the separate RTL path
```

The Group B assignment-boundary result also checks out independently, although the committed
classifier does not itself prove it. Comparing those 61 swept code points against official
UnicodeData releases produced:

```text
assigned by Unicode 15.0
    0

new in Unicode 15.1
    2

new in Unicode 16.0
    34

new in Unicode 17.0
    25
```

Thus all 61 are post-Ada-2.9.2's explicitly cited Unicode 15.0 data boundary and assigned by
Unicode 17. The 55/61 taxonomy is credible; the remaining rejection is about the durable tool
and the checkpoint's contradictory account of Strategy A's behavior.

## C12-R002-V2-R002 - committed reproduction tooling is still not a reliable verifier

**Classification:** `CONTRACT_ASSURANCE_DEFECT`  
**Severity:** blocking

The filenames and decisive 1.15.3 comparison were repaired, but the documented clean-checkout
command still fails on the project's Windows environment:

```text
python compare_oracles.py

UnicodeEncodeError: 'charmap' codec can't encode character '\u05d0'
```

The script prints raw non-ASCII values through a default CP1252 console. It succeeds only after
the reviewer externally sets `PYTHONUTF8=1`, a requirement absent from both the script and its
reproduction instructions.

More importantly, the verifier never loads `systematic_corpus.txt`. It takes the Node-22.19
output's keys as the authoritative URL list and uses `dict.get()` for every other dataset. It
does not check row counts, duplicate keys, or exact key-set equality. A missing corpus/result row
can therefore be silently excluded, and a missing row can be scored as a matching rejection when
both lookups produce `None`. The current committed files are complete, but the promised permanent
mechanical gate does not enforce that invariant.

`generate_corpus.py` also imports whichever `idna` happens to be installed while the README
attributes the result specifically to `idna==3.19`. The documented command has no dependency
pin or version guard, so a future environment can regenerate a different corpus under the same
claimed provenance.

**Minimal correction:** make the documented commands self-contained on supported platforms;
pin or explicitly reject any `idna` version other than the characterized version; make the
verifier load the corpus and fail nonzero on wrong counts, duplicates, missing/extra keys, or any
unexpected mismatch; and make output encoding deterministic without an undocumented shell
environment variable.

## C12-R002-V2-R003 - corrected taxonomy is followed by a false Strategy A claim

**Classification:** `CONTRACT_ASSURANCE_DEFECT`  
**Severity:** blocking

The 55/61 taxonomy itself is now supported. However, both the root-characterization artifact and
README immediately state that `ada-url==1.15.3` "has neither defect," including that it does not
have the Ada-2.9.2 LTR-bidi bug because it allegedly postdates the fix. That is incompatible with
the same artifact's zero-mismatch result.

The raw evidence is decisive:

```text
file://xn--a-0hc/share       # a + U+05D0, representative Group A bug row

Node 22.19 / direct Ada 2.9.2
    accepted

ada-url==1.15.3
    accepted

ada-url==4.0.0
    rejected
```

An exact 8,246-row behavioral match necessarily reproduces the characterized Ada 2.9.2 behavior,
including Group A. That is desirable for pinned-Pi parity; saying the dependency lacks the bug
misdescribes why Strategy A is correct and creates contradictory guidance for a future upgrade.

**Minimal correction:** state that `ada-url==1.15.3` intentionally reproduces the relevant Ada
2.9.2 behavior, including the LTR-bidi defect and Unicode-15.0 assignment boundary, while
`ada-url==4.0.0` changes both. Do not change the Strategy A recommendation merely to correct this
narrative.

## Required next action

Return only the checkpoint/evidence package to Claude for one narrow correction pass:

1. make the generator/verifier genuinely deterministic, self-checking, and runnable on supported
   Windows consoles;
2. correct the false claim that the exact-match 1.15.3 dependency lacks Ada 2.9.2's Group A
   behavior;
3. preserve the exact witnesses, independently verified 55/61 taxonomy, and Strategy A result;
4. return a new exact checkpoint SHA for independent review before implementation resumes.

PR #44 remains frozen. R004-A and the other provisional Python closures remain unchanged. Rust's
three affected surfaces remain `REVALIDATE_REQUIRED` and untouched.

## Stop state

```text
checkpoint e433fce6...
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
