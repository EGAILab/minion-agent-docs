# Layer 12 WP-12.1 -- `L12-PY-R002` root-cause characterization (checkpoint invalidated, round 2)

```text
IMPLEMENTATION AUTHORIZED: NO
```

## Why this artifact exists

`agent-workflow.md` §11.8.10 (checkpoint invalidation on repeated targeted-closure failure) has
fired for `L12-PY-R002`:

- Targeted closure review 6 (`minion-agent-docs#120` @ `09423f0a962d1139ba16155eff6113c026a1f89a`)
  rejected candidate `a7dcd65` for two witnesses in Unicode category `"So"` (a snowman and a pile
  of poo).
- The remediation (`minion-agent#44` @ `1848873`) fixed exactly those two witnesses by widening
  `idna.decode()`'s own strict disallowed-codepoint check to accept category `"So"` specifically.
- Targeted closure review 7 (`minion-agent-docs#120` @ `e2ca998371ebedaeddf02ae3e3775d8642d94a10`)
  confirmed the `"So"` witnesses now pass, but supplied TWO MORE witnesses in ADJACENT categories
  the same fix did not cover: `%E2%82%AC.com` (Sc, euro sign) and `%E2%88%9E.com` (Sm, infinity) --
  both accepted by live Node, both still rejected by the round-2 candidate.

This is the SAME material finding failing a SECOND targeted closure review after the
`AGREED FOR IMPLEMENTATION` checkpoint at `minion-agent-docs#121` @ `2db656c`. Per §11.8.10, the
checkpoint is now invalidated. Per its own required next step, this artifact:

1. identifies the unmodeled semantic dimension the prior checkpoint (and both remediation
   attempts) missed;
2. characterizes it against a much wider, systematically-constructed differential probe, not one
   more hand-picked witness pair;
3. proposes a revised implementation strategy, prototyped (not committed) and verified against
   every witness gathered here;
4. ends `IMPLEMENTATION AUTHORIZED: NO` and requests independent checkpoint review before any
   further change to `minion-agent#44`.

`minion-agent#44` has NOT been modified since `1848873fc9626b699990a29b1f35c7baba78cc34`
(unchanged in this pass). `minion-agent-rust/**` has not been touched.

## What both prior remediation attempts got wrong

Both attempts treated the failure as "the strict `idna.decode()` disallowed-codepoint table is
missing an entry" and patched the missing entry (first `"So"`, and this artifact's own
investigation below shows the SAME shape of gap recurs for `"Sc"`, `"Sm"`, and in principle any
other category the strict IDNA2008 table disallows but Node's own algorithm does not). That is
category-by-category patching of a SYMPTOM, not characterization of the RULE Node actually
applies. The root defect is architectural: `idna.decode()` (the `kjd/idna` PyPI package) implements
**IDNA2008** validation (RFC 5891/5892/5893's own PVALID/CONTEXTJ/CONTEXTO/DISALLOWED codepoint
table, its own hyphen-placement rule, its own canonical-Punycode-re-encoding rule). Node's
`fileURLToPath`/WHATWG URL host parsing does **not** implement IDNA2008 at all -- it implements
**Unicode IDNA Compatibility Processing (UTS #46)**, specifically the WHATWG URL Standard's own
`domain to ASCII`/`domain to Unicode` algorithms, which invoke UTS46 with a SPECIFIC, non-default
flag configuration that diverges from IDNA2008 in multiple independent, previously-uncharacterized
ways -- not just the disallowed-codepoint table.

## Authoritative source: WHATWG URL Standard §3.3 IDNA

Fetched directly from `https://url.spec.whatwg.org/` (not guessed, not read from a secondary
source) -- the domain-to-ASCII and domain-to-Unicode algorithms:

```text
domain parser ToASCII(domain, beStrict):
    Unicode ToASCII with domain_name=domain,
        CheckHyphens=beStrict, CheckBidi=true, CheckJoiners=true,
        UseSTD3ASCIIRules=beStrict, Transitional_Processing=false,
        VerifyDnsLength=beStrict, IgnoreInvalidPunycode=false.

domain to Unicode(domain):
    Unicode ToUnicode with domain_name=domain,
        CheckHyphens=false, CheckBidi=true, CheckJoiners=true,
        UseSTD3ASCIIRules=false, Transitional_Processing=false,
        IgnoreInvalidPunycode=false.
    If an error was recorded, return domain unchanged.
```

The basic URL parser's own host-parsing step for a special scheme (`file:` included) invokes
`domain parser ToASCII` with `beStrict = false` for an ordinary (non-strict-mode) parse -- the
mode `new URL(...)`/`fileURLToPath` actually use. This single, authoritative parameter set
explains EVERY divergence this episode has found, across THREE independent review rounds, in one
coherent model:

| flag | value (non-strict) | explains |
|---|---|---|
| `CheckHyphens` | **false** | leading/trailing/double hyphen after decode is NOT rejected (new witness below) |
| `CheckBidi` | **true** | `xn--abc-ppe` (RTL-invalid) correctly rejected |
| `CheckJoiners` | **true** | CONTEXTJ (ZWJ/ZWNJ placement, `xn--abc-jdc`... see correction below) enforced |
| `UseSTD3ASCIIRules` | **false** | symbol codepoints (`So`/`Sc`/`Sm`, NOT merely `"So"`) are NOT rejected -- this is the actual root cause of BOTH review-6 and review-7's witnesses |
| `Transitional_Processing` | **false** | no legacy deviation-character special-casing |
| (canonical Punycode re-encoding, RFC 5891 §5.3) | **not part of UTS46 at all** | `xn---bbk` (a non-canonical A-label) decodes successfully on live Node (new witness below) -- this project's OWN prior implementations, across every revision, wrongly enforced this IDNA2008-only rule |
| (CONTEXTO placement) | **not gated by any UTS46 ToUnicode flag** | `xn--aa-0ea` (`a·a`, CONTEXTO-invalid middle-dot placement) is ACCEPTED by live Node (new witness below) -- this project's OWN prior implementations wrongly enforced this too |

Two of these rows (`xn--abc-jdc` and CONTEXTO) required correcting this artifact's own first-draft
hypothesis mid-investigation -- see "Corrections found during this characterization" below.

## Corrections found during this characterization

While building the behavior matrix below, two additional, previously-uncharacterized
IDNA2008-vs-UTS46 divergences were found that neither prior remediation attempt exercised at all
(no corpus witness touches them):

1. **Hyphen placement is not enforced.** `xn---abc-/xn--abc--` (decoding to `-abc`/`abc-`, a
   leading/trailing literal hyphen) are ACCEPTED by live Node. Every prior revision of
   `_domain_to_unicode`/`_relaxed_punycode_label` called `idna.core.check_hyphen_ok`, which WOULD
   reject these -- an unexercised latent defect, not yet in the corpus, now characterized here
   before it causes an eighth review round.
2. **CONTEXTO placement is not enforced; canonical Punycode re-encoding is not required.**
   `xn--aa-0ea` (`a·a`, CONTEXTO-invalid) and `xn---bbk` (a non-canonical "fake A-label" per RFC
   5891 §5.3, which correctly re-decodes to `ま`) are BOTH accepted by live Node. Every prior
   revision enforced both rules (via `idna.core.check_label`'s CONTEXTO loop and `ulabel`'s
   canonical-reencoding check respectively) -- also latent, uncharacterized defects.

Both were caught BEFORE proposing an implementation, not after another rejected review round,
because this pass characterizes the RULE (via the authoritative WHATWG spec text) rather than
only the two witnesses the last review happened to supply.

## Behavior matrix -- 27 witnesses, independently verified against live Node

Every row below was verified by direct execution of `node -e` / a `.mjs` probe script against
THREE Node versions: locally-available v22.15.1, and freshly re-downloaded, checksum-verified
v22.19.0 (Pi's declared floor) and v22.23.2 (latest 22.x) -- all three produced BYTE-FOR-BYTE
IDENTICAL output for all 27 cases (`diff` empty in both directions), consistent with this
episode's own already-established Node version-stability finding. Reproduction script:
`assurance/layers/data/12-python-r002-scripts/root_cause_probe.mjs` (new, committed alongside
this artifact).

| # | A-label | dimension exercised | live Node result | IDNA2008 (`idna.decode`, prior candidate) |
|---|---|---|---|---|
| 1 | `xn--n3h` | disallowed-codepoint table, `So` | `☃` (accepted) | rejected (fixed round 2, `"So"`-only) |
| 2 | `xn--ls8h` | disallowed-codepoint table, `So` | `💩` (accepted) | rejected (fixed round 2, `"So"`-only) |
| 3 | `xn--lzg` | disallowed-codepoint table, `Sc` | `€` (accepted) | **still rejected -- review 7's exact witness** |
| 4 | `xn--59g` | disallowed-codepoint table, `Sm` | `∞` (accepted) | **still rejected -- review 7's exact witness** |
| 5 | `xn--a` | disallowed-codepoint table, `Cc` control | rejected | rejected (correct, coincidentally) |
| 6 | `xn--0y0c` | disallowed-codepoint table, `Co` private-use | rejected | rejected (correct, coincidentally) |
| 7 | `xn--zva` | disallowed-codepoint table, `Cn` unassigned | rejected | rejected (correct, coincidentally) |
| 8 | `xn--abc-ppe` | `CheckBidi` | rejected | rejected (correct) |
| 9 | `xn--abc-jdc` | leading-combining-mark (unconditional UTS46 rule, not flag-gated) | rejected | rejected (correct) |
| 10 | `xn---bbk` | canonical Punycode re-encoding (RFC 5891 §5.3 -- NOT a UTS46 rule) | `ま` (accepted) | **rejected -- latent, uncharacterized defect** |
| 11 | `xn--` | empty A-label payload (structural, not IDNA/UTS46) | rejected | rejected (correct) |
| 12 | `xn--a-` | hyphen-ending payload (structural decode, distinct from hyphen-PLACEMENT rule) | `a` (accepted) | rejected (correct rule, wrong reason -- see note) |
| 13 | `xn--zzzz` | malformed Punycode digits | rejected | rejected (correct) |
| 14 | `xn---abc-` | `CheckHyphens` (leading literal hyphen) | `-abc` (accepted) | **rejected -- latent, uncharacterized defect** |
| 15 | `xn--abc--` | `CheckHyphens` (trailing literal hyphen) | `abc-` (accepted) | **rejected -- latent, uncharacterized defect** |
| 16 | `xn--e-xbb` | NFC normalization (unconditional UTS46 rule) | rejected | rejected (correct) |
| 17 | `xn--ll-0ea` | CONTEXTO, valid placement (`l·l`) | `l·l` (accepted) | accepted (correct, coincidentally) |
| 18 | `xn--aa-0ea` | CONTEXTO, invalid placement (`a·a`) | `a·a` (accepted -- NOT gated) | **rejected -- latent, uncharacterized defect** |
| 19 | `xn--11b6iy14e` | `CheckJoiners`/CONTEXTJ, valid (virama+ZWJ) | accepted | accepted (correct) |
| 20 | `xn--a-ugn` | `CheckJoiners`/CONTEXTJ, invalid (bare ZWJ) | rejected | rejected (correct) |
| 21 | `xn--a-4ba` | disallowed-codepoint table, NBSP (`Zs`) | rejected | rejected (correct, coincidentally) |
| 22 | `xn--a-vca` | disallowed-codepoint table, soft hyphen (`Cf`) | rejected | rejected (correct, coincidentally) |
| 23 | `xn--a-0gn` | disallowed-codepoint table, dash punctuation (`Pd`, U+2010) | `a‐` (accepted) | rejected (would newly regress if `Pd` not widened) |
| 24 | `xn--a-jv3s` | disallowed-codepoint table, emoji (`So`, grinning face) | `a😀` (accepted) | rejected pre-round-2; accepted post-round-2 |
| 25 | `xn--fa-hia` | existing corpus witness (`faß`) | `faß` (accepted) | accepted (correct) |
| 26 | `xn--bcher-kva` | existing corpus witness (`bücher`) | `bücher` (accepted) | accepted (correct) |
| 27 | `xn--zca` | existing corpus witness (`ß`) | `ß` (accepted) | accepted (correct) |

Row 12's note: the prior candidate's rejection of `xn--a-` was coincidentally correct in OUTCOME
but for the WRONG reason -- it rejected on a hand-written "payload must not end with a hyphen"
guard (mirroring `idna.core.ulabel`'s OWN structural check, itself a manifestation of the
IDNA2008-specific hyphen rule), not because Node rejects it. Node in fact ACCEPTS `xn--a-`,
decoding to `a` -- the prior guard was importing an extra, wrong restriction that happened not to
matter for this ONE witness (an empty label after stripping the trailing hyphen would fail for an
unrelated reason regardless) but is a real latent defect the wide sweep here now catches before
it causes another review round on a witness like `xn--ab-` (which SHOULD decode to `ab`, and does
on live Node, confirmed separately during this pass).

## Proposed root-cause fix -- prototyped, NOT committed

**Model**: decode a `"xn--..."` A-label by RFC 3492 Punycode decode, then validate the result
against Unicode UTS46's OWN mapping-table status (VALID or DEVIATION required for every
codepoint -- exactly the table the `idna` package's own `idna.uts46data` module already ships,
used internally by `idna.core.uts46_remap` for a DIFFERENT purpose (ToASCII mapping) but reusable
here directly), NFC normalization, the leading-combining-mark rule, `CheckJoiners`/CONTEXTJ, and
`CheckBidi` -- explicitly WITHOUT `check_hyphen_ok`, WITHOUT the CONTEXTO check, and WITHOUT the
canonical-Punycode-re-encoding check, all three of which are IDNA2008-only rules the WHATWG/UTS46
profile Node actually runs does not apply.

```python
import bisect
import idna.core as _idna_core
from idna.uts46data import uts46_starts, uts46_statuses
from idna.intranges import intranges_contain

_UTS46_VALID = ord("V")
_UTS46_DEVIATION = ord("D")

def _decode_punycode_label(alabel: str) -> str:
    payload = alabel[4:].encode("ascii")
    if not payload:
        raise _idna_core.IDNAError("Malformed A-label", code="invalid_alabel")
    decoded = payload.decode("punycode")  # UnicodeError -> caller wraps as IDNAError
    if not decoded:
        raise _idna_core.IDNAError("Empty label", code="empty_label")
    _idna_core.check_nfc(decoded)
    _idna_core.check_initial_combiner(decoded)
    for pos, ch in enumerate(decoded):
        cp = ord(ch)
        i = cp if cp < 256 else bisect.bisect_right(uts46_starts, cp) - 1
        if uts46_statuses[i] not in (_UTS46_VALID, _UTS46_DEVIATION):
            raise _idna_core.InvalidCodepoint(f"disallowed codepoint U+{cp:04X}", code="uts46_disallowed")
        if intranges_contain(cp, _idna_core.idnadata.codepoint_classes["CONTEXTJ"]):
            if not _idna_core.valid_contextj(decoded, pos):
                raise _idna_core.InvalidCodepointContext("joiner not allowed", code="contextj")
    _idna_core.check_bidi(decoded)
    return decoded
```

This REPLACES `_relaxed_punycode_label` entirely (the category-by-category `"So"`-only widening
from round 2 is superseded, not extended) and becomes the ONLY decode path -- there is no longer
a two-tier "strict `idna.decode()` first, relaxed retry second" structure, since this function
IS the correct rule directly, not a fallback.

**Prototype verification** (this pass, not committed to `filesystem.py`): this exact function was
implemented in a scratch script and run against all 27 witnesses in the behavior matrix above --
**27/27 matched live Node exactly**, including every one of the newly-discovered latent defects
(hyphen-placement, CONTEXTO, canonical-re-encoding) that were NOT in any prior witness set. It was
also spot-checked against the corpus's own existing punycode rows (`xn--fa-hia.de`,
`xn--strae-oqa.de`, `XN--BCHER-KVA` case-insensitivity, `xn--zzzz`, `xn--`, `xn--a`) with no
regressions.

**Why not `PyICU`** (the theoretically most faithful option, calling ICU4C's `uidna_*` functions
with the exact WHATWG-specified flags directly): attempted `uv pip install pyicu` in this
environment -- build FAILED (`RuntimeError: Please install pkg-config... or set ICU_VERSION`),
requiring a system ICU installation this project does not have and should not require, for the
SAME portability/deployment-risk reason `urlstd`/`icupy` was already disqualified in the original
R002 library research (`12-execution-seams-python-convergence-checkpoint-reset.md` §"Research:
existing Python WHATWG URL implementations"). Not re-litigating that disposition; citing it as
already-settled.

**Why not `ada_url.idna_to_unicode()` directly**: it was investigated FIRST in this pass and
matches Node closely for the disallowed-codepoint-table dimension specifically (confirmed
correct for `So`/`Sc`/`Sm`/`Cc`/`Co`/`Cn`/`Zs`/`Cf`/`Pd`), but is STRICTER than Node on the
hyphen-placement dimension (it rejects `xn---abc-`/`xn--abc--`, which live Node accepts) and its
own Python binding exposes no configuration flags to disable that check
(`inspect.signature(ada_url.idna_to_unicode)` takes only `s`). Composing it with a SEPARATE
override for hyphen-placement specifically was considered and rejected as more fragile than
reusing `idna`'s own already-available UTS46 mapping-table data directly, which requires no
library-internals workaround at all.

**What is NOT proposed to change**: `ada_url.URL`'s own role in `_file_url_to_path` (host-syntax/
IPv4/IPv6/forbidden-code-point validation and canonicalization, `HostType` discrimination) is
UNAFFECTED by this finding and is not touched. Only the PUNYCODE-LABEL-DECODE step within
`_domain_to_unicode` changes.

## Acceptance witnesses (to become permanent regression evidence on implementation)

All 27 rows in the behavior matrix above, plus the existing 67-case corpus reverified with no
regressions (prototype spot-checked against its punycode-bearing rows; full reverification is
part of the NEXT implementation pass, not this characterization pass).

## Normative deltas

None required beyond what `pi-parity-manifest.yaml`'s `EXEC-002` row and
`_file_url_to_path`/`_domain_to_unicode`'s own docstrings already say about delegating to Node's
real algorithm -- this fix makes the IMPLEMENTATION match that already-correct characterization
more precisely; it does not change what is claimed. The manifest row's own R002 paragraph should
be extended (on implementation, not in this pass) to name UTS46/WHATWG's specific flag
configuration as the operative rule, superseding the round-2 entry's narrower `"So"`-category
framing.

## Implementation constraints

- Do not reintroduce `check_hyphen_ok`, `valid_contexto`, or the canonical-Punycode-re-encoding
  check for THIS decode path -- all three are confirmed, live-Node-verified NOT to apply.
- Do not scope the disallowed-codepoint check to any enumerated Unicode category list (`"So"`,
  etc.) -- use the UTS46 mapping table's own VALID/DEVIATION status directly, which is the
  general rule, not an approximation of it.
- Keep NFC, leading-combining-mark, CONTEXTJ, and bidi checks -- all four remain live-Node-verified
  as enforced.
- `ada_url.URL`'s own host-syntax/IPv4/IPv6/forbidden-code-point role is unchanged.

## Out-of-scope / deferred

- `Transitional_Processing`/deviation-character handling: `Unicode 15.1` deprecated transitional
  processing entirely (per `idna.core.uts46_remap`'s own docstring) and this project's pinned
  `idna` version already treats deviation codepoints as always-kept, matching
  `Transitional_Processing=false` -- no additional work identified.
- `VerifyDnsLength`: WHATWG sets this to `beStrict` (false in the non-strict mode `fileURLToPath`
  uses) -- not exercised by any witness in this corpus; not proposed for implementation unless a
  future witness requires it.
- Percent-decoded-non-ASCII-host `ada_url` ToASCII round-trip (the divergence characterized, not
  fixed, in the round-1 remediation and partially addressed in round 2): this fix's own decode
  path is now UTS46-table-driven rather than IDNA2008-driven, which should make that round-trip
  correct for a STRICTLY WIDER set of inputs than round 2's `"So"`-only widening did -- but this
  is not independently re-characterized in this pass beyond the witnesses above; a future gap in
  that specific class would be a separate finding, not silently claimed closed here.

## Convergence checkpoint

```text
CONVERGENCE CHECKPOINT
    PROPOSED FOR IMPLEMENTATION

OPEN FINDINGS
    L12-PY-R002

ACCEPTANCE WITNESSES
    assurance/layers/12-execution-seams-python-r002-root-cause-characterization.md
        (this artifact) -- 27-case behavior matrix, live-Node-verified across v22.15.1/
        v22.19.0/v22.23.2 (byte-for-byte identical)
    assurance/layers/data/12-python-r002-scripts/root_cause_probe.mjs (new, committed)

NORMATIVE DELTAS
    pi-parity-manifest.yaml EXEC-002 row (on implementation): name the UTS46/WHATWG flag
        configuration as the operative rule, superseding the round-2 "So"-category framing
    minion-agent-python/src/minion_agent/execution/filesystem.py: _domain_to_unicode /
        _relaxed_punycode_label replaced by the UTS46-mapping-table-driven decode function
        prototyped above (not yet committed)

NEXT_OWNER
    Codex (independent checkpoint review)
```

`minion-agent#44` remains at `1848873fc9626b699990a29b1f35c7baba78cc34`, unmodified by this
pass. `minion-agent-rust/**` unmodified. Requesting independent `CHECKPOINT REVIEW` per
§11.8.5 STEP 2 before any further change to production code. This artifact does not, and
cannot, self-approve `AGREED FOR IMPLEMENTATION` (§11.8.10's own explicit prohibition, applying
with particular force now that the invalidation rule has fired once already for this finding).
