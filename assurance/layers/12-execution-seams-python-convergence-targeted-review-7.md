# Layer 12 Python convergence targeted closure review 7

Mode: targeted finding-closure review (`agent-workflow.md` section 11.8.7)

Verdict: **REJECTED - L12-PY-R002 REMAINS OPEN; CHECKPOINT INVALIDATED**

## Exact target

- Python implementation PR: `EGAILab/minion-agent#44`
- reviewed Python SHA: `1848873fc9626b699990a29b1f35c7baba78cc34`
- companion docs PR: `EGAILab/minion-agent-docs#121`
- reviewed docs SHA: `3910dd4c3222620f56bce9c2143eef7d4d8ce975`
- prior targeted review evidence: `EGAILab/minion-agent-docs#120` at
  `09423f0a962d1139ba16155eff6113c026a1f89a`
- agreed checkpoint SHA: `2db656c01126bfb775d1fe453241e191ed78b2f0`
- checkpoint approval evidence: `EGAILab/minion-agent-docs#120` at
  `80bbf9d8dd0a117826d39aff706e863558cd76fb`
- certified Rust baseline, read-only: `2b309ee8cecbc333a7965781087677bd6cbba46b`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`

The coordination issue was open and valid, assigned `NEXT_OWNER = Codex`, and recorded the same
remote-reachable PR heads. Both candidate PRs were open, ready for review, and unmerged. No Python,
shared-contract, or Rust implementation was modified by this review. Layer 13 was not started.

## Targeted result

```text
L12-PY-R002
    STILL OPEN - PI_PARITY_DEFECT

L12-PY-R004-A
    PROVISIONALLY CLOSED - unchanged and outside this review

previous provisional closures R001/R003/R005/R006/R007
    RETAINED

CE-L12-PY-01-01 checkpoint
    INVALIDATED for R002 under section 11.8.10

ready for another implementation attempt
    NO - revised characterization/challenge and a new explicit checkpoint approval are required
```

## What the remediation closed

The two witnesses from targeted review 6 now pass through the real Python filesystem seam:

```text
file://%E2%98%83.com/share       -> UNC host containing U+2603 SNOWMAN
file://%F0%9F%92%A9.com/share   -> UNC host containing U+1F4A9 PILE OF POO
```

The implementation's retry is genuinely limited to otherwise-disallowed codepoints whose
Unicode general category is `So`; it does not simply bypass all structural validation. The
focused filesystem suite passed (`132 passed, 4 skipped`), including the existing malformed
Punycode, bidi, combining-mark, CONTEXTJ, and CONTEXTO controls. The committed comparison data
reports Python `67/67` and Rust `48/67` for its finite corpus.

Those facts close the two exact examples but do not close the material R002 rule. The agreed
Model A makes supported Node `fileURLToPath` behavior the oracle and explicitly treats the corpus
as non-exhaustive. The candidate's category-specific relaxation remains observably incomplete.

## L12-PY-R002 - still open

**Classification:** `PI_PARITY_DEFECT`  
**Severity:** blocking

Pinned Pi delegates `file://` conversion to Node's `fileURLToPath`. Independent execution on both
the supported Node floor (`v22.19.0`) and the drift-check runtime (`v22.23.2`) found adjacent
accepted codepoint classes that the candidate's `So`-only retry does not cover.

### Discriminating witness W-R002-RESET-2A

```text
input
    file://%E2%82%AC.com/share

decoded host codepoint
    U+20AC EURO SIGN, Unicode category Sc

Node v22.19.0 / v22.23.2
    accepted; returns a UNC path whose host is the literal euro-sign label

candidate 1848873f
    does not return that UNC path;
    resolve_local_path falls back to the local literal path
    C:\cwd\file:\%E2%82%AC.com\share
```

### Discriminating witness W-R002-RESET-2B

```text
input
    file://%E2%88%9E.com/share

decoded host codepoint
    U+221E INFINITY, Unicode category Sm

Node v22.19.0 / v22.23.2
    accepted; returns a UNC path whose host is the literal infinity-sign label

candidate 1848873f
    does not return that UNC path;
    resolve_local_path falls back to the local literal path
    C:\cwd\file:\%E2%88%9E.com\share
```

Both runtimes produced identical outcomes. These are not a new semantic surface or a different
finding: they are the same percent-decoded non-ASCII host round-trip and the same overly strict
IDNA codepoint-class rejection identified by the preceding R002 review. They directly disprove
the remediation's assumption that accepting category `So` is an adequate realization of the
general delegated-WHATWG rule.

The candidate's explicit statement that other not-yet-witnessed disallowed categories are not
covered is candid, but it cannot make the known observable mismatch compatible with an `adopted`
direct-parity row. A finite witness patch is not a substitute for the checkpoint's promised full
delegated behavior.

## Checkpoint invalidation

This is the **second targeted convergence-closure failure** of the same material
`L12-PY-R002` finding after checkpoint `2db656c0...` was explicitly approved:

1. review 6 (`09423f0a...`) found the `So` snowman/emoji witnesses;
2. this review finds the `Sc` euro and `Sm` infinity witnesses after the `So`-only patch.

`agent-workflow.md` section 11.8.10 therefore applies mechanically. The checkpoint is presumed
inadequate and implementation must stop. Before a third implementation attempt, the convergence
owner must return to characterization/challenge, identify the missing root abstraction in the
URL/host conversion strategy, revise the differential matrix beyond one Unicode category, and
obtain a new independent `AGREED FOR IMPLEMENTATION` approval.

The next checkpoint must not encode another finite category allowlist unless independent evidence
shows that allowlist is the actual Node/WHATWG rule. It should characterize the host conversion
algorithm or select a delegation boundary capable of satisfying it, while retaining the already
proven malformed-Punycode, bidi, combining-mark, IPv4/IPv6, forbidden-codepoint, and fallback
behavior.

## Evidence and gates

```text
focused Python filesystem tests
    133 passed, 4 skipped, 0 failed

committed comparison matrix
    67 comparable rows
    Python 67/67
    Rust 48/67

prior exact witnesses
    Node v22.19.0/v22.23.2: accepted
    Python candidate: accepted through real resolve_local_path seam

new adjacent-category witnesses
    Node v22.19.0/v22.23.2: Sc and Sm hosts accepted as UNC hosts
    Python candidate: both fall back to local literal paths
```

On this Windows console the committed `build_matrix.py` prints its summary counts, then exits with
`UnicodeEncodeError` while rendering Rust's Unicode mismatch details under CP1252. The underlying
UTF-8 TSV data is readable and the counts are reproducible; this is a non-semantic evidence-script
portability hardening note, not the parity blocker above.

## Required next action

Return to checkpoint characterization, not direct implementation:

1. invalidate the R002 portion of checkpoint `2db656c0...` in the coordination state;
2. extend the executable Node/Python corpus with the exact `Sc` and `Sm` witnesses above and a
   principled cross-category characterization set;
3. explain the actual WHATWG/Node host-conversion boundary that accepts these while retaining
   Node's genuine rejection classes;
4. propose a revised implementation strategy from that characterization;
5. obtain a new independent checkpoint review and explicit approval before changing production
   code again.

Do not alter the provisional closure of R004-A. Rust's three marked surfaces remain
`REVALIDATE_REQUIRED`; this review does not implement them. Do not begin final complete review or
Layer 13.

## Stop state

```text
Python Layer 12
    NOT CERTIFIED

L12-PY-R002
    OPEN

CE-L12-PY-01-01 checkpoint (R002 portion)
    INVALIDATED

L12-PY-R004-A
    PROVISIONALLY CLOSED

Rust affected surfaces
    REVALIDATE_REQUIRED

Layer 12 cross-language
    NOT CLOSED

Layer 13
    NOT STARTED
```
