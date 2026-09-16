# Layer 11 Pass 2 Slice C — convergence targeted-closure re-review

## Exact target

```text
code PR #33
    41fc55627708dab7b95996662e206328c3796067

docs PR #92
    34de79d031b7a30deccb6b5d01ddec81398fa8fb

base main
    ea3b64caca84e95245fa0d5f2a1a650452686649

base docs master
    1e3c224ed7912d51fa28f33563622e5155947cda

prior targeted review
    minion-agent-docs PR #93
    3a61fa9b41cb21f41e7c91ac15ca18b30d008191

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

The current remote PR heads are open, Ready for Review, unmerged, and exactly match issue #29's
handoff. Issue #29 is open and names `NEXT_OWNER: Codex`. This is a workflow section 11.8.7
targeted re-review of `L11-SC-R011` and `L11-SC-R018`, not the final complete review.

## Verdict

```text
targeted convergence closure
    REJECTED

L11-SC-R011
    STILL OPEN

L11-SC-R018
    PROVISIONALLY CLOSED

L11-SC-R012
    PROVISIONALLY CLOSED (unchanged)

L11-SC-R021
    PROVISIONALLY CLOSED (unchanged)

Python Layer 11 Pass 2 Slice C
    NOT CERTIFIED

Rust Layer 11 Pass 2 Slice C
    NOT STARTED

Layer 12
    NOT STARTED
```

## L11-SC-R011 — STILL OPEN (`PI_PARITY_DEFECT`)

The repair correctly applies conversion only to the URL-constructor probe and retains the
original string for fallback. Both prior lone-surrogate witnesses now match Pi. The conversion
helper's premise is nevertheless false for Python's public string domain:

> any Python string character whose own codepoint still falls in the surrogate range is
> necessarily an unpaired one

Python can contain a valid UTF-16 surrogate pair as two adjacent explicit code points, for
example `chr(0xD83D) + chr(0xDE00)`. Web IDL's USVString conversion recognizes that high/low pair
and converts it to the single scalar `U+1F600`. The candidate maps each code point independently
to `U+FFFD`, producing two replacement characters.

Minimal discriminating witness:

```text
input
    "https://example.test/?code=" + chr(0xD83D) + chr(0xDE00) + "&state=s"

pinned Pi / Node
    Web IDL USVString conversion combines the valid high/low pair
    result = {code: "😀", state: "s"}

candidate
    to_usv_string replaces each surrogate independently
    result = {code: "��", state: "s"}
```

This is distinct from the existing test's use of the already-combined Python scalar `"😀"`.
Passing an astral scalar through unchanged does not prove correct conversion of an explicit
adjacent surrogate pair—the exact branch the new helper owns.

Required remediation: implement the actual Web IDL scalar-value-string conversion: combine a
valid high-surrogate/low-surrogate pair into its scalar value, replace only unpaired surrogates,
and continue to preserve the original pre-conversion value for Pi's fallback branches. Correct
the helper/spec/manifest rationale that presently treats every Python surrogate code point as
necessarily unpaired. Add both a direct helper witness and an end-to-end URL-query witness using
an explicitly constructed adjacent pair.

## L11-SC-R018 — PROVISIONALLY CLOSED (`PI_PARITY_DEFECT` resolved)

The non-2xx body-read boundary now catches ordinary exceptions independently of HTTPX's own
hierarchy, while the same failure under a 2xx status is re-raised. The permanent witnesses use an
injected `AsyncByteStream` raising `RuntimeError`, exactly reproducing the prior review witness.
`asyncio.CancelledError` remains outside `Exception`, consistently preserving the contract's
operation-cancellation boundary. No exception-type restriction remains on ordinary non-2xx
body-read failures.

## Contract-quality result

The normative rule—Web IDL USVString conversion before WHATWG URL construction—is correct. The
remaining defect is the Python helper's incomplete realization and its overclaiming rationale,
not an unresolved Pi rule or a lower-layer incompatibility. Rust's native `String` contains only
Unicode scalar values, so this host-representation witness creates no Rust-only surrogate type
obligation.

The final section 11.8.8 review remains ineligible until `L11-SC-R011` closes. No canonical runner
simulates either reviewed behavior, and no lower certified layer requires reopening.

## Fresh evidence

```text
focused auth tests
    PASS — 132 passed

full pytest
    PASS — 1469 passed, 19 xfailed

coverage
    PASS — 100.00% (3832 statements)

ruff
    PASS

mypy
    PASS — 75 source files

schema / manifest validation
    PASS — 213 passed

new paired-surrogate probe
    pinned Node: code = "😀", state = "s"
    candidate:   code = "��", state = "s"
```

## Findings

```text
PI_PARITY_DEFECT
    L11-SC-R011 — STILL OPEN

CONTRACT_ASSURANCE_DEFECT
    none independently active; the incorrect rationale/evidence is coupled to R011

PI_BEHAVIOR_UNCERTAIN
    none

PARITY_NEUTRAL_HARDENING
    none

PARITY_CONSTRAINED_RISK
    none
```

Return only `L11-SC-R011` to the active convergence track. Do not start the final complete review,
Rust Slice C, or Layer 12.
