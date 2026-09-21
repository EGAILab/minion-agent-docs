# Layer 12 L12-PY-R002 root-cause checkpoint review

Mode: independent convergence checkpoint review (`agent-workflow.md` sections 11.8.4,
11.8.5, and 11.8.10)

Verdict: **REJECTED - CHECKPOINT NOT AGREED FOR IMPLEMENTATION**

## Exact target

- checkpoint PR: `EGAILab/minion-agent-docs#121`
- reviewed checkpoint SHA: `854f5c1097b9aa2aee2494bd378753961d478314`
- artifact:
  `assurance/layers/12-execution-seams-python-r002-root-cause-characterization.md`
- frozen Python PR: `EGAILab/minion-agent#44`
- frozen Python SHA: `1848873fc9626b699990a29b1f35c7baba78cc34`
- prior checkpoint-invalidation review evidence: `EGAILab/minion-agent-docs#120` at
  `e2ca998371ebedaeddf02ae3e3775d8642d94a10`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`

The coordination issue was open and valid, assigned `NEXT_OWNER = Codex`, and recorded the exact
remote-reachable PR heads above. PR #44 was unchanged, as required. This review modified no Python,
shared-contract, or Rust implementation. Layer 13 was not started.

## Result

```text
WHATWG/UTS46 root direction
    PARTIALLY CONFIRMED

committed 27-row Node behavior matrix
    REPRODUCED

proposed UTS46-table-driven implementation model
    REJECTED - not behaviorally sound beyond the finite matrix

L12-PY-R002
    OPEN

AGREED FOR IMPLEMENTATION
    NO
```

The checkpoint correctly replaces the prior category-by-category IDNA2008 patching model with the
WHATWG URL Standard's UTS46-based direction. Its citation of the WHATWG non-strict flag values is
accurate: `CheckHyphens=false`, `CheckBidi=true`, `CheckJoiners=true`,
`UseSTD3ASCIIRules=false`, `Transitional_Processing=false`, and
`IgnoreInvalidPunycode=false`. The official UTS46 processing model also confirms that decoded
Punycode labels are validated using the UTS46 validity criteria rather than IDNA2008's
PVALID/CONTEXTO rules.

The committed `root_cause_probe.mjs` produced all 27 claimed rows on Node v22.19.0 and v22.23.2,
with zero differences between the two outputs. The finite table is accurate.

The blocker is the proposed realization of that model. It combines versioned data and validation
functions that do not reproduce the pinned Node runtime outside those 27 rows:

- `idna==3.19` supplies a Unicode **17.0** UTS46 mapping table;
- this review host's Python 3.13 `unicodedata` is Unicode **15.1**;
- `idna.core.check_initial_combiner` and `check_bidi` use Python's `unicodedata`, while the
  proposed per-codepoint validity loop uses `idna`'s separate Unicode-17 table;
- pinned-floor Node v22.19.0 reports Unicode **16.0** / ICU 77.1, while the v22.23.2 drift check
  reports Unicode **17.0** / ICU 78.2.

That mixed-version composition is not merely theoretical. A systematic probe using the proposed
function verbatim against one or more representative codepoints from every interval in
`idna.uts46data` exercised 10,607 A-labels and found **30 acceptance mismatches** against each of
Node v22.19.0 and v22.23.2. The same 30 mismatches appeared on both Node versions.

## C12-R002-ROOT-R001 - versioned UTS46/Unicode model remains incomplete

**Classification:** `CONTRACT_ASSURANCE_DEFECT`  
**Severity:** blocking

### Witness A - proposed function rejects a Node-accepted label

```text
input
    file://xn--3pc/share

decoded codepoint
    U+0C3C TELUGU SIGN NUKTA (Mn)

Node v22.15.1 / v22.19.0 / v22.23.2
    accepted
    Windows path contains the literal U+0C3C host label

proposed checkpoint function
    rejected by idna.core.check_initial_combiner
    "Label begins with an illegal combining character"
```

This directly disproves the checkpoint's claim that keeping Python `idna`'s leading-combining
check is a behaviorally complete description of the pinned Node surface. It also demonstrates
that quoting the current abstract UTS46 validity criterion is insufficient without accounting
for the concrete versioned behavior of Node/ICU and the exact API path Pi uses.

### Witness B - proposed function accepts a Node-rejected label

```text
input
    file://xn--8g0n/share

decoded codepoint
    U+2EBF0 CJK UNIFIED IDEOGRAPH-2EBF0

Node v22.15.1 / v22.19.0 / v22.23.2
    rejected with ERR_INVALID_URL

proposed checkpoint function
    accepted because idna 3.19's Unicode-17 UTS46 table marks the codepoint valid;
    NFC / initial-combiner / bidi checks also pass
```

This is the opposite failure direction. A generic "use the installed UTS46 table's V/D status"
rule does not reproduce the pinned Node surface even when the drift-check Node reports Unicode
17.0. The checkpoint therefore cannot safely authorize the proposed function merely because it
matches the hand-selected 27 rows.

## Why this blocks checkpoint agreement

The checkpoint was reset specifically because a finite witness matrix had repeatedly hidden the
next semantic dimension. Its replacement strategy must therefore explain and control the
versioned UTS46/Unicode boundary, not introduce another implicit dependency on whichever Unicode
tables happen to ship in Python and `idna`.

Two conforming Python environments could otherwise satisfy the written proposal while producing
different outcomes as their Python or `idna` Unicode data versions change. Rust would likewise
lack a language-neutral rule for selecting its Unicode/IDNA data version. That is exactly the
kind of cross-language ambiguity a convergence checkpoint must resolve before implementation.

## Minimal checkpoint correction required

Return to characterization/challenge; do not modify PR #44 yet.

1. Add both exact witnesses above to the permanent behavior matrix and reproduce them across the
   supported Node floor and drift-check runtime.
2. Characterize the concrete version relationship among Node's URL/ICU behavior, the UTS46
   mapping table, Unicode general-category data, bidi data, and CONTEXTJ data.
3. Replace the mixed-version proposal with a language-neutral rule that fixes which observable
   table/profile is authoritative and prevents dependency upgrades from silently changing the
   result.
4. Demonstrate the revised prototype against a systematic cross-table corpus, not only the 27
   selected examples. At minimum, include representative boundaries from every UTS46 status
   interval and preserve both acceptance directions above.
5. Obtain a new independent checkpoint approval before production implementation resumes.

This correction does not reopen R004-A or the other provisional Python closures. Rust's three
marked surfaces remain `REVALIDATE_REQUIRED` and untouched.

## Evidence run

```text
committed root_cause_probe.mjs
    27 rows on Node v22.19.0
    27 rows on Node v22.23.2
    0 differences

environment versions
    idna package: 3.19
    idna UTS46/IDNA data: Unicode 17.0.0
    Python unicodedata: Unicode 15.1.0
    Node v22.19.0: Unicode 16.0 / ICU 77.1
    Node v22.23.2: Unicode 17.0 / ICU 78.2

systematic checkpoint-prototype probe
    10,607 representative A-labels
    30 acceptance mismatches vs Node v22.19.0
    30 acceptance mismatches vs Node v22.23.2
    witness sets identical across both Node versions
```

## Stop state

```text
checkpoint 854f5c10...
    REJECTED

L12-PY-R002
    OPEN

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

Authoritative references checked:

- WHATWG URL Standard, IDNA algorithms: <https://url.spec.whatwg.org/#idna>
- Unicode UTS #46 processing and validity criteria:
  <https://www.unicode.org/reports/tr46/#Processing>
