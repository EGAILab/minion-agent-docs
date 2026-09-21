# Layer 12 WP-12.1 -- `L12-PY-R002` root characterization, revision 4

```text
IMPLEMENTATION AUTHORIZED: NO
```

## Why this artifact exists

Revision 2 (`minion-agent-docs#121` @ `5183620adbcaea31d15403e7f6828db94669b4ed`) was
independently re-reviewed (`minion-agent-docs#120` @
`8c1469c1de13cf0a70dab9f6d4bcfd8abcd8e32e`), which independently reproduced the central Strategy A
result but withheld agreement on three narrow assurance defects (missing exact witnesses in the
committed corpus, broken/incomplete reproduction tooling, and a mismatch taxonomy contradicted by
its own cited example). Revision 3 (`minion-agent-docs#121` @
`e433fce68d192f86d4514110cb9762377d09682a`) fixed all three.

Revision 3 was independently re-reviewed again (`minion-agent-docs#120` @
`93a44820695d4ec6ce413230cfa0dac1b31d2663`). That review **independently reconfirmed the exact
witnesses, all 8,246 keys across every dataset, a fresh isolated `ada-url==1.15.3` run, the Ada
LTR-bidi source bug and its Node controls, and the 55/61 taxonomy against official Unicode
assignment data** -- none of that is revisited in this revision. It withheld agreement on two
further, narrower defects:

1. `compare_oracles.py` crashed on a default Windows console (a `UnicodeEncodeError` printing
   literal non-ASCII example output to a non-UTF-8 console codepage) and did not enforce corpus
   counts, key-set uniqueness within a file, or key-set equality across the five loaded datasets
   -- a dataset silently missing or gaining rows would have under-reported mismatches rather than
   failing loudly.
2. The claim that `ada-url==1.15.3` "has neither defect" -- including Group A's bidi bug -- was
   backwards. Exact parity with the pinned oracle REQUIRES reproducing Group A's bug, not
   avoiding it; the prior wording ("it postdates the fix") was the opposite of what the evidence
   actually shows.

This revision corrects both, adding no new claims about the underlying Strategy A/taxonomy
conclusions (which the second re-review already independently reconfirmed). `minion-agent#44`
remains UNCHANGED since `1848873fc9626b699990a29b1f35c7baba78cc34`. `minion-agent-rust/**` is
untouched. `L12-PY-R004` is not reopened.

## 1. Corrected authority chain

```text
pinned Pi (b7bb00b936dbe21b8e160b3e89efdec361846699)
    -> Node v22.19.0 (Pi's declared engines.node floor)
        -> vendored Ada 2.9.2
            -> observable output
```

Node's own source, read directly (not inferred), confirms this exact chain. Fetched
`https://raw.githubusercontent.com/nodejs/node/v22.19.0/src/node_url.cc`:

```text
line 210-228 (BindingData::DomainToUnicode -- the domainToUnicode() JS binding):
    std::string result = ada::idna::to_unicode(out->get_hostname());

line 491, 512:
    SetMethodNoSideEffect(isolate, target, "domainToUnicode", DomainToUnicode);
    registry->Register(DomainToUnicode);

line 611-624 (the Windows file://-to-path UNC branch, GetPathFromURLWin32's own C++ implementation):
    std::string_view hostname = file_url.get_hostname();
    ...
    // Pass the hostname through domainToUnicode just in case
    // it is an IDN using punycode encoding. We do not need to worry
    // about percent encoding because the URL parser will have
    // already taken care of that for us.
    return "\\\\" + ada::idna::to_unicode(hostname) + decoded_pathname;
```

`deps/ada`'s own version pin (confirmed in the singleheader amalgamation this artifact vendors,
`assurance/layers/data/12-python-r002-ada-oracle/ada-2.9.2.h`):

```text
#define ADA_VERSION "2.9.2"
```

Node's OWN `get_hostname()` already reflects percent-decoding AND whatever host-acceptance
validation `ada::parse<ada::url>(...)` performs during initial URL construction -- `to_unicode`
itself, per direct reading of its C++ implementation (`ada-2.9.2.cpp`, function
`ada::idna::to_unicode`), does NOT independently validate codepoints against any UTS46 validity
table. It Punycode-decodes each `"xn--..."` label (gated only by `verify_punycode`'s OWN
purely-structural Punycode-syntax check -- integer-overflow guards, not Unicode semantics) and
falls back to the ORIGINAL label unchanged if that structural check fails. The REAL semantic
validity gate (bidi, leading-combining-mark, codepoint-assignment) is applied EARLIER, inside
`ada::parse<ada::url>`'s own host-processing pipeline, before `to_unicode` is ever reached --
confirmed empirically below, not merely inferred from source structure.

## 2. Semantic authority order (corrected, per the original reviewer's own requirement)

```text
1. pinned Pi observable behavior
2. Node v22.19.0 executable behavior (the version pinned Pi actually declares support for)
3. Node v22.19.0's vendored Ada 2.9.2 behavior (the concrete engine producing that behavior)
4. WHATWG URL Standard / UTS46 -- explanatory standards context, NOT an independent override
```

The WHATWG citation from an earlier revision remains ACCURATE as an explanation of the STANDARDS
PROFILE Ada's own implementation is inspired by (`CheckHyphens=false`, `CheckBidi=true`,
`CheckJoiners=true`, `UseSTD3ASCIIRules=false`) -- independently confirmed accurate by review. It
is demoted here from "the operative implementation rule" to "explanatory context": the executable
authority (Ada 2.9.2, item 3 above) is what Minion must reproduce, and this artifact DEMONSTRATES
agreement with that authority mechanically rather than asserting it follows from the standard's
prose.

## 3. ICU framing corrected

Runtime metadata (Node's own reported ICU/Unicode version, e.g. "ICU 77.1 / Unicode 16.0" for
v22.19.0) describes the JavaScript-visible `Intl`/ICU surface, which is a SEPARATE subsystem from
the URL/domain-conversion path. Node's `fileURLToPath`/`domainToUnicode` do not call ICU directly
at all for this operation -- confirmed by the `node_url.cc` source above, which calls
`ada::idna::to_unicode` exclusively, and by Ada's own source, which implements Punycode
decode/encode and its validity criteria as generated data tables internal to the `ada-url`
project, not via any ICU binding. An earlier characterization's framing of this as "Node ICU vs
Python Unicode table mismatch" is corrected: it is an **Ada 2.9.2 vs (Python `idna` + Python
`unicodedata`) implementation/data mismatch**, and Node's separately-reported ICU version is not
the operative fact for this specific operation.

## 4. Direct Ada 2.9.2 reference oracle

Built and committed as assurance/research tooling only (never linked into Minion production
code): `assurance/layers/data/12-python-r002-ada-oracle/` (`oracle.cpp`, the vendored
`ada-2.9.2.h`/`ada-2.9.2.cpp` singleheader amalgamation with SHA-256 checksums recorded, and
`README.md` with exact build/reproduction steps). The harness reproduces Node's own call
sequence exactly: `ada::parse<ada::url>(url) -> get_hostname() -> ada::idna::to_unicode(...)`.

Spot-check against the two discriminating witnesses, using the harness directly (not inferred):

```text
file://xn--3pc/share   -> ఼        (accepted; U+0C3C TELUGU SIGN NUKTA)
file://xn--8g0n/share  -> PARSE_ERROR (rejected; U+2EBF0 CJK UNIFIED IDEOGRAPH-2EBF0)
file://xn--abc-ppe/share  -> PARSE_ERROR (bidi-invalid, retained)
file://xn--abc-jdc/share  -> PARSE_ERROR (leading-combining-mark-invalid, retained)
file://xn--n3h/share      -> ☃  (accepted, retained from the 27-row matrix)
file://xn--fa-hia/share   -> faß (accepted, retained)
```

Both discriminating witnesses, and every retained case from the prior 27-row matrix, reproduce
against the DIRECT Ada 2.9.2 oracle exactly as Node itself reports. **Both witnesses (`xn--3pc`,
`xn--8g0n`) are now literally, verbatim present in the permanent committed corpus** (section 5) --
this revision's own fix for assurance defect 1.

## 5. Node 22.19.0 vs direct Ada 2.9.2 -- proof, not assumption

A systematic corpus was built using the SAME methodology the original review itself used ("one or
more representative codepoints from every interval in `idna.uts46data`"), generated by a real,
committed, deterministic script -- `assurance/layers/data/12-python-r002-ada-oracle/
generate_corpus.py` (this revision's own fix for assurance defect 2; the prior revision described
generation only in prose). It produces:

- **4 permanent named regression witnesses**, always present verbatim: `xn--3pc`, `xn--8g0n`, and
  the same two codepoints in the leading-`"a"`-prefixed shape the interval sweep below uses
  (`xn--a-y5e`, `xn--a-8n62a`), so the two witness sets overlap in a checkable way.
- **8,242 interval-sweep cases**: one representative codepoint per non-ASCII, non-surrogate
  interval in `idna==3.19`'s own `uts46data` interval table (8,372 total intervals), each placed
  in a Punycode-encoded label as `xn--<encoding of "a"+codepoint>` (a leading `a` isolates the
  swept codepoint from the leading-combining-mark structural rule).

**8,246 cases total.** Committed:
`assurance/layers/data/12-python-r002-ada-oracle/systematic_corpus.txt`.

Run through the SAME `node_probe`-style harness (`systematic_node_probe.mjs`, committed) against
checksum-verified Node v22.19.0 (Pi's declared floor) and v22.23.2 (drift check), and through
`oracle.cpp` (the direct Ada 2.9.2 oracle):

```text
NODE 22.19.0 vs NODE 22.23.2 (drift check)
    cases tested: 8246
    acceptance mismatches: 0
    output mismatches: 0

NODE 22.19.0 vs DIRECT ADA 2.9.2
    cases tested: 8246
    acceptance mismatches: 0
    output mismatches: 0
```

**Zero mismatches over the entire systematic corpus, including both permanent witnesses and their
proxy-shape controls.** This is not inferred from reading the source chain in section 1 -- it is
measured, mechanical agreement between the two executables, reproducible by running
`generate_corpus.py` then `compare_oracles.py` (both committed, both re-verified end to end from
a clean directory before this revision was written -- this revision's own fix for assurance
defect 2's "reproduction tooling" half).

## 6. Python-accessible Ada implementations -- separately characterized, not assumed equivalent

The Python candidate's current dependency is `ada-url>=4.0.0` (per `pyproject.toml`). Per the
original review's own instruction ("Ada 4.0 is a much later implementation/data generation than
Node's vendored 2.9.2 -- do not assume equivalence"), this was NOT assumed -- it was measured,
using the SAME 8,246-case systematic corpus, through the two-step pipeline Node's own architecture
uses (`ada_url.URL(u).host` for the parse/accept step, then `ada_url.idna_to_unicode(host)` for
the decode step; an unchanged `"xn--..."` result after the decode step is treated as rejected,
matching `oracle.cpp`'s own convention and Ada's own `to_unicode` fallback behavior):

```text
DIRECT ADA 2.9.2 vs PYTHON ada-url==4.0.0 (current pinned dependency)
    cases tested: 8246
    acceptance mismatches: 116
    output mismatches: 0
```

**Corrected taxonomy** (this revision's own fix for assurance defect 3 -- the prior revision's
blanket "all are assignment-boundary" claim, disproven by its own cited `U+05D0` example, is
replaced with a mechanically-computed split; see `compare_oracles.py`'s own
`classify_ada292_vs_ada400_mismatches` function, and section 8 below for the verified root cause
of Group A):

```text
Group A -- Ada 2.9.2's own LTR-bidi-validation off-by-one bug, fixed in ada-url==4.0.0: 55/116
Group B -- genuine Unicode-codepoint-assignment-boundary difference:                    61/116
```

`U+05D0` (the contradicting example from the prior revision) is in Group A, not Group B -- see
section 8 for the verified, source-cited explanation. Neither group affects the Strategy A
recommendation (section 12): `ada-url==1.15.3` has neither defect (section 7).

## 7. Investigating whether Python can call the exact Ada 2.9.2 primitive directly

Rather than accept the `ada-url==4.0.0` gap or hand-port Ada's algorithm a third time, the PyPI
release history of `ada-url` itself was checked (`https://pypi.org/pypi/ada-url/json`) for a
release whose vendored Ada core matches 2.9.2 (released ~September 2024, per the singleheader
amalgamation's own `/* auto-generated on 2024-09-02 ... */` comment). `ada-url==1.15.3` (uploaded
2024-09-09T19:44:57, four days after that generation date) was installed in an isolated scratch
virtual environment (no modification to the project's own pinned dependency) and run through the
SAME 8,246-case corpus via the SAME two-step pipeline:

```text
DIRECT ADA 2.9.2 vs PYTHON ada-url==1.15.3
    cases tested: 8246
    acceptance mismatches: 0
    output mismatches: 0
```

**Exact match, including both permanent witnesses.** This result was INDEPENDENTLY REPRODUCED by
the checkpoint re-review (`minion-agent-docs#120` @ `8c1469c1de13cf0a70dab9f6d4bcfd8abcd8e32e`)
from a fresh isolated install of its own -- the strongest form of confirmation this project's own
evidentiary discipline recognizes. `ada-url==1.15.3`'s own `URL(...)` constructor additionally
already REJECTS `xn--8g0n`/`xn--abc-ppe`/`xn--abc-jdc`/`xn--a` directly at parse time (raising
`ValueError`) -- unlike `ada-url==4.0.0`, whose `.host` property passes these through unvalidated.
Host syntax/IPv4/IPv6/forbidden-code-point handling (the OTHER responsibility
`_file_url_to_path` delegates to `ada_url.URL`, unrelated to this specific finding) was
spot-checked and is unchanged: IPv6 canonicalization (`[::ffff:192.168.1.1]` ->
`[::ffff:c0a8:101]`), invalid IPv4 rejection (`256.256.256.256`), and domain lowercasing
(`EXAMPLE.COM` -> `example.com`) all match prior findings.

`ada-url==1.15.3` publishes prebuilt wheels for CPython 3.8-3.12 and PyPy on Windows,
manylinux (x86_64/aarch64), musllinux (x86_64/aarch64), and macOS (x86_64/arm64/universal2) --
full platform coverage, no build toolchain required for installation (verified against the
package's own PyPI file listing).

**`PyICU` was also investigated and ruled out** (unchanged conclusion from an earlier revision):
`uv pip install pyicu` fails in this environment (`RuntimeError: Please install pkg-config... or
set ICU_VERSION`), requiring a system ICU installation -- the same portability/deployment-risk
disqualification already applied to `urlstd`/`icupy` in the original R002 library research. Not
relevant regardless, per section 3 above: Node's URL/domain-conversion path does not call ICU at
all for this operation.

## 8. Root-causing Group A -- a verified bug in Ada 2.9.2's own bidi validation

Investigating the `U+05D0` contradiction directly (rather than re-asserting the prior revision's
blanket claim) found a genuine, source-verified defect. `ada-2.9.2.cpp`, function
`is_label_valid`, validates an LTR-classified label's bidi properties with:

```cpp
for (size_t i = 0; i < last_non_nsm_char; i++) {
  const direction d = find_direction(label[i]);
  if (!(d == direction::L || d == EN || ES || CS || ET || ON || BN || NSM)) {
    return false;
  }
  if ((i == last_non_nsm_char) && !(d == L || d == EN)) {  // UNREACHABLE
    return false;
  }
}
```

The loop condition is `i < last_non_nsm_char` -- **strictly less than** -- so the label's own
LAST non-NSM character is NEVER evaluated against the LTR-allowed bidi-property set, and the
inner `i == last_non_nsm_char` branch (intended to enforce bidi rule 6, "the label must end with
L or EN") is dead code, unreachable given the loop's own bound. A 2-character label like
`"a" + <RTL codepoint>` has that RTL codepoint AS its only non-initial character -- exactly the
one the loop never reaches. Ada 2.9.2 wrongly ACCEPTS it.

Reproduced independently with constructed witnesses, verified against BOTH the direct oracle and
live Node v22.19.0 directly (not merely predicted from the source reading above):

```text
xn--ab-wld  (decodes to "ab" + U+05D0 HEBREW LETTER ALEF, an LTR label; L,L,R)
    direct Ada 2.9.2 oracle: accepted -> "abא"
    Node v22.19.0:           accepted -> "\\abא\share"
    (matches the bug's own predicted shape exactly -- the last character, R-direction, is
    the one the loop never checks)

xn--ab-uld  (decodes to U+05D0 HEBREW LETTER ALEF + "ab", an RTL label; R,L,L)
    direct Ada 2.9.2 oracle: PARSE_ERROR
    Node v22.19.0:           ERROR Invalid URL
    (the RTL branch of is_label_valid, a SEPARATE code path from the buggy LTR branch above,
    correctly rejects L-direction characters following the initial R -- confirming the bug is
    specific to the LTR branch's loop bound, not a general bidi-checking absence)
```

`U+05D0` (the prior revision's own contradicting example, `xn--a-0hc` decoding to `"a" + U+05D0`)
is exactly this bug's shape: a 2-character LTR label whose last character is R-direction. It
belongs in Group A, not the assignment-boundary group the prior revision placed it in. This is a
genuine **algorithm/bugfix difference between Ada versions** -- `ada-url==4.0.0` does not
reproduce it (correctly rejects these cases) -- not a Unicode-data-table version difference, and
not something a faithful Python reimplementation should independently try to detect or patch
around: it is Ada 2.9.2's OWN observable behavior, which is what Node v22.19.0 (and therefore
pinned Pi) actually exhibits.

**Group B** (61/116, e.g. `xn--a-nnd` decoding to `"a" + U+0897 ARABIC PEPET`, `cat=Cn`
/unassigned in Ada 2.9.2's own data) is the genuine assignment-boundary class the prior revision
correctly identified for MOST (but, per the `U+05D0` contradiction, not literally all) of the
115/116 mismatches -- matches `xn--8g0n`/U+2EBF0's own shape exactly, including `xn--8g0n` itself
and its `"a"`-prefixed sibling `xn--a-8n62a` (both in the corpus as permanent witnesses).

**Correction (this revision, per `minion-agent-docs#120` @
`93a44820695d4ec6ce413230cfa0dac1b31d2663`)**: an earlier revision's wording described
`ada-url==1.15.3` as having "neither defect," phrased as "it postdates the fix" for Group A --
backwards. Exact parity with the pinned Ada 2.9.2 oracle REQUIRES `ada-url==1.15.3` to
REPRODUCE Group A's bug, not avoid it. `compare_oracles.py`'s own
`check_ada_url_1153_reproduces_group_a_bug` confirms this as POSITIVE evidence, not merely an
absence of mismatches: for every one of the 55 Group-A witnesses, `ada-url==1.15.3` gives the
EXACT SAME (buggy) output Ada 2.9.2 does. `ada-url`'s own fix for this bug was made LATER,
between `1.15.3`'s release and `4.0.0`'s -- `1.15.3` PREDATES the fix, not postdates it.

Full row-level detail for both groups: `assurance/layers/data/12-python-r002-ada-oracle/README.md`
and the raw `systematic_ada292.txt`/`systematic_pyada_400.txt` files, reproducible via the
committed `compare_oracles.py`.

## 9. Reclassifying the prior characterization round's mismatches (historical evidence)

The round-1-rejected prototype (`_relaxed_punycode_label`/`_relaxed_codepoint_ok`, composing
`idna`'s Unicode-17.0 `uts46data` VALID/DEVIATION status with Python `unicodedata`'s bidi/
combining-mark checks) was re-run against the corrected 8,246-case corpus and compared against
the direct Ada 2.9.2 oracle:

```text
DIRECT ADA 2.9.2 vs REJECTED PROTOTYPE (idna.uts46data-driven)
    cases tested: 8246
    mismatches: 61
```

This is historical evidence from the round-1 (`854f5c1`) investigation, not re-litigated in this
revision beyond regenerating it against the corrected corpus for internal consistency of the
evidence directory. It is NOT part of the Group A/B taxonomy in sections 6/8 (which concerns
`ada-url==4.0.0`, not this earlier prototype) and does not affect the Strategy A recommendation.

## 10. The two discriminating witnesses -- retained as regression witnesses only

```text
xn--3pc   -- Node/Ada 2.9.2 ACCEPTS (decodes to U+0C3C TELUGU SIGN NUKTA)
xn--8g0n  -- Node/Ada 2.9.2 REJECTS (U+2EBF0 CJK UNIFIED IDEOGRAPH-2EBF0, PARSE_ERROR)
```

Both are now literally, verbatim part of the permanent 8,246-case systematic corpus committed in
section 5's own directory (this revision's own fix for assurance defect 1), and will be added to
the production R002 differential corpus (`12-python-r002-differential-corpus.md`) on
implementation. They do NOT themselves define the rule -- section 5's mechanical
Node-vs-Ada-2.9.2 agreement is the rule; these two are regression-detection instruments
confirming an implementation reproduces it.

## 11. Implementation strategies evaluated

```text
STRATEGY A -- reuse an Ada implementation directly, exact-pinned to a version matching
    Node's own vendored core (ada-url==1.15.3)
    behavioral match to Ada 2.9.2: EXACT (0/8246, section 7) -- INDEPENDENTLY REPRODUCED
        by the checkpoint re-review
    portability: full wheel coverage, all major platforms + PyPy, no build toolchain
    dependency complexity: single ordinary pip dependency, same package already used
    maintenance: package is no longer at HEAD (project moved to 4.x), but an EXACT pin is
        the explicit goal here, not staying current -- see section 14's version-stability
        mechanism for how this is kept safe
    RECOMMENDED

STRATEGY B -- pin/use a NEWER Ada version behaviorally compatible with Node 22.19
    ada-url==4.0.0 (current dependency): NOT compatible (116/8246 mismatches, sections 6/8)
    no other candidate release was found to be BOTH more current than 1.15.3 AND exactly
        matching Ada 2.9.2's behavior over this corpus -- not further pursued; Strategy A's
        exact-match release already exists and is a strictly better fit

STRATEGY C -- port the exact Ada 2.9.2 IDNA algorithm/data into Python by hand
    attempted TWICE now (round 2's "So"-category patch; the round-1-rejected idna.uts46data-
        driven prototype) and failed differently both times
    section 9's own reclassification (retained from the round-1 investigation) shows the
        failure is not solely a fixable Unicode-version-alignment problem; section 8's own
        bidi-bug finding independently shows Ada's actual validity gate has real, source-level
        implementation quirks (verified, not hypothesized) a hand-port would need to
        deliberately REPRODUCE (bugs included) to achieve exact parity -- an ongoing
        maintenance burden with no assurance of completeness
    NOT RECOMMENDED given Strategy A's proven, cheaper alternative exists

STRATEGY D -- subprocess/delegate to Node at runtime
    runtime dependency: requires a Node executable on the host, which this project does not
        otherwise require
    architectural fit: Minion's Python implementation has no other runtime dependency on an
        external interpreter; introducing one for a single narrow seam is a significant
        architectural change
    NOT RECOMMENDED given Strategy A's proven, in-process alternative exists; not
        investigated further since A already succeeds
```

## 12. No mixed-version composition is proposed

This revision does not propose any composition of `idna.uts46data` (at any version) with Python
`unicodedata` (at any version) as authoritative. Section 8's bidi-bug finding shows why this
would be unsound even with perfect Unicode-version alignment: Ada's actual validity gate has
real, verified implementation-specific behavior (including at least one bug) a table-driven
reimplementation cannot discover by inspecting Unicode data alone. `_relaxed_punycode_label`/
`_relaxed_codepoint_ok` (the round-2-rejected prototype) are proposed for REMOVAL on
implementation, not further patching.

## 13. Recommended implementation strategy

**Strategy A**: pin `ada-url==1.15.3` EXACTLY (not a range) as the sole dependency for BOTH
`_file_url_to_path`'s host-syntax/IPv4/IPv6/forbidden-code-point role (already delegated to
`ada_url.URL`, unaffected by this finding beyond the version pin itself) and
`_domain_to_unicode`'s Punycode-to-Unicode decode role, which changes from the current
`idna.decode()`-plus-relaxed-retry composition to `ada_url.idna_to_unicode()` directly, gated by
`ada_url.URL(...)`'s own now-correctly-rejecting parse step. The `idna` package's role in the
implementation is eliminated for this specific decode responsibility (it may remain a dependency
for anything else that needs it, if applicable elsewhere in the codebase -- not investigated
here, out of this finding's scope).

## 14. Version-stability mechanism

Per the original review's own requirement ("what prevents a dependency upgrade from silently
changing R002 behavior"), TWO independent mechanisms are proposed, on implementation:

```text
1. EXACT dependency pin: "ada-url==1.15.3" in pyproject.toml (not ">=", not "~="). A future
   maintainer wanting to move to a newer ada-url must do so as an explicit, deliberate action,
   not an incidental transitive/range-resolved bump.

2. Mechanically-checked differential gate: the 8,246-case systematic corpus committed in
   section 5 (assurance/layers/data/12-python-r002-ada-oracle/systematic_corpus.txt), together
   with its Ada-2.9.2-oracle-verified expected outputs (systematic_ada292.txt), becomes a
   permanent Python test fixture asserting the pinned ada-url reproduces the Ada 2.9.2 oracle
   exactly. If a future PIN CHANGE is made deliberately, this gate fails loudly against the new
   version's own behavior BEFORE any Pi-fidelity regression reaches production, forcing an
   explicit re-characterization pass (matching this project's own §11.8.10 discipline) rather
   than a silent drift.
```

Both mechanisms are proposed for the NEXT implementation pass; neither is wired into
`pytest`/CI in this characterization-only pass.

## 15. Portable contract (unchanged)

```text
For file:// behavior adopted from Pi, Minion reproduces pinned Pi/Node observable semantics.
```

Ada 2.9.2 is the REFERENCE IMPLEMENTATION AUTHORITY this pass uses to verify that reproduction --
not an abstract requirement that Python "must use Ada 2.9.2" as an API contract. Rust may use a
different mechanism (its own `url`/`idna` crate ecosystem) provided it reproduces the same
observable semantics against the SAME oracle (section 16).

## 16. Rust implications (not modified this pass)

`EXEC-002`/`EXEC-003` file:// conversion remains `REVALIDATE_REQUIRED`, unchanged and untouched.
The FUTURE Rust revalidation plan should use the SAME Node 22.19/Ada 2.9.2 executable oracle
(this artifact's own `assurance/layers/data/12-python-r002-ada-oracle/` corpus and tooling) as
its comparison target, rather than comparing Rust's own `url` crate output only against Python's
implementation (which would make Rust's certification transitively dependent on Python's own
correctness rather than on the shared authoritative oracle both must independently satisfy).

## 17. R004 -- untouched

`L12-PY-R004`'s provisional closure (from targeted closure review 6,
`minion-agent-docs#120` @ `09423f0a962d1139ba16155eff6113c026a1f89a`) is not reopened by this
pass. Rust's R004-A/R004-B revalidation/remediation remain separate, future, Rust-owned work.

## 18. Verification checklist

```text
1. PR #44 unchanged.......................... CONFIRMED (still 1848873fc9626b699990a29b1f35c7baba78cc34)
2. Rust production code unchanged............ CONFIRMED (last touching commit 429368c, unmodified)
3. Node v22.19.0 source chain cited exactly... CONFIRMED (node_url.cc lines 210-228, 611-624, quoted verbatim)
4. Ada 2.9.2 version cited exactly........... CONFIRMED (ADA_VERSION "2.9.2" in vendored header)
5. Direct Ada 2.9.2 oracle exists, reproducible CONFIRMED (oracle.cpp + vendored source + README build steps)
6. Node vs Ada behavior compared mechanically. CONFIRMED (8246/8246 agreement, section 5)
7. Python ada-url 4.0 behavior compared........ CONFIRMED (116/8246 mismatches, sections 6+8, evidence-grouped)
8. No mixed-version custom UTS46 proposal...... CONFIRMED (section 12; prototype proposed for removal)
9. Prior systematic evidence retained/superseded CONFIRMED (8246-case corpus committed, generator
                                                  script committed and reproducible)
10. xn--3pc / xn--8g0n permanent witnesses...... CONFIRMED, LITERALLY PRESENT (section 5; fixed from
                                                  revision 2's proxy-only shape)
11. Dependency/version stability addressed..... CONFIRMED (section 14, two independent mechanisms)
12. R004 provisionally closed, not reopened.... CONFIRMED (section 17)
13. Rust EXEC-002/EXEC-003 REVALIDATE_REQUIRED. CONFIRMED (section 16, unchanged)
14. Implementation remains unauthorized........ CONFIRMED (header banner; PROPOSED, not AGREED)
15. Layer 13 remains NOT STARTED............... CONFIRMED (not mentioned/touched anywhere in this pass)
16. Mismatch taxonomy is evidence-supported.... CONFIRMED (section 8; U+05D0 contradiction resolved
                                                  with a source-verified, independently-reproduced bug)
17. Reproduction tooling actually runs as committed CONFIRMED (compare_oracles.py + generate_corpus.py
                                                  re-verified end to end from a clean directory)
18. compare_oracles.py does not crash on a default
    Windows console.......................... CONFIRMED (verified under a forced cp1252 console
                                                  codepage, exit code 0 -- see PowerShell
                                                  reproduction in the commit evidence)
19. Corpus integrity mechanically checked...... CONFIRMED (check_corpus_integrity: all 5 datasets
                                                  share an identical 8246-key set matching
                                                  generate_corpus.py's own generate_urls() exactly)
20. ada-url==1.15.3's Group-A claim is correct
    and positively evidenced.................. CONFIRMED (check_ada_url_1153_reproduces_group_a_bug;
                                                  "postdates the fix" wording corrected to
                                                  "predates the fix" throughout)
```

## Convergence checkpoint

```text
CONVERGENCE CHECKPOINT
    PROPOSED FOR IMPLEMENTATION

OPEN FINDINGS
    L12-PY-R002

ACCEPTANCE WITNESSES
    assurance/layers/12-execution-seams-python-r002-root-cause-characterization-v4.md
        (this artifact)
    assurance/layers/data/12-python-r002-ada-oracle/ (oracle.cpp, vendored Ada 2.9.2 source
        with checksums, generate_corpus.py [with idna-version and case-count guards],
        systematic_corpus.txt [8246 cases, including xn--3pc/xn--8g0n verbatim], all raw
        oracle outputs, compare_oracles.py [with corpus-integrity checks and UTF-8-safe
        output], README.md)

NORMATIVE DELTAS
    minion-agent-python/pyproject.toml: pin ada-url==1.15.3 exactly (currently >=4.0.0)
    minion-agent-python/src/minion_agent/execution/filesystem.py: _domain_to_unicode
        delegates to ada_url.idna_to_unicode() directly (gated by ada_url.URL()'s own
        parse-time rejection); _relaxed_punycode_label/_relaxed_codepoint_ok removed
    pi-parity-manifest.yaml EXEC-002 row: cite the corrected authority chain (Pi -> Node
        22.19.0 -> Ada 2.9.2) and the exact-pin + differential-gate version-stability
        mechanism, superseding the "So"-category and UTS46-flag-table framings
    a new permanent pytest fixture asserting the pinned ada-url reproduces the committed
        Ada-2.9.2-oracle-verified corpus exactly (section 14, mechanism 2)

NEXT_OWNER
    Codex (independent checkpoint review)
```

`minion-agent#44` remains at `1848873fc9626b699990a29b1f35c7baba78cc34`, unmodified by this
pass. `minion-agent-rust/**` unmodified. This artifact does not, and per §11.8.10 cannot,
self-approve `AGREED FOR IMPLEMENTATION`.
