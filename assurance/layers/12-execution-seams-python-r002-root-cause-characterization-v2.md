# Layer 12 WP-12.1 -- `L12-PY-R002` root characterization, revision 2

```text
IMPLEMENTATION AUTHORIZED: NO
```

## Why this artifact exists

The independent checkpoint review of `minion-agent-docs#121` @
`854f5c1097b9aa2aee2494bd378753961d478314`
(`minion-agent-docs#120` @ `2a99d49371b740f0a4a01862383143478672b660`) rejected that
characterization. It confirmed the WHATWG/UTS46 direction and the committed 27-row Node
behavior matrix, but rejected the proposed realization: it composed `idna==3.19`'s Unicode 17.0
UTS46 mapping table with Python 3.13's own Unicode 15.1 `unicodedata` (used by
`check_initial_combiner`/`check_bidi`), against a pinned-floor Node v22.19.0 that reports Unicode
16.0/ICU 77.1. A systematic 10,607-label probe found 30 acceptance mismatches, with two clean
opposite-direction witnesses: `xn--3pc` (Node accepts, the prototype rejected) and `xn--8g0n`
(Node rejects, the prototype accepted).

This revision corrects the authority model per the reviewer's own required minimal correction,
going one level deeper than WHATWG/UTS46 prose: it identifies and directly executes the EXACT
Ada C++ library Node v22.19.0 vendors, uses it as the concrete oracle, and evaluates
implementation strategies against measured, mechanical agreement with that oracle rather than
against abstract standards text.

`minion-agent#44` remains UNCHANGED since `1848873fc9626b699990a29b1f35c7baba78cc34`.
`minion-agent-rust/**` is untouched. `L12-PY-R004` is not reopened.

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

## 2. Semantic authority order (corrected, per the reviewer's own requirement)

```text
1. pinned Pi observable behavior
2. Node v22.19.0 executable behavior (the version pinned Pi actually declares support for)
3. Node v22.19.0's vendored Ada 2.9.2 behavior (the concrete engine producing that behavior)
4. WHATWG URL Standard / UTS46 -- explanatory standards context, NOT an independent override
```

The WHATWG citation from the prior (rejected) revision remains ACCURATE as an explanation of the
STANDARDS PROFILE Ada's own implementation is inspired by (`CheckHyphens=false`, `CheckBidi=true`,
`CheckJoiners=true`, `UseSTD3ASCIIRules=false`) -- the independent review itself confirmed this
citation is correct. It is demoted here from "the operative implementation rule" to "explanatory
context": the executable authority (Ada 2.9.2, item 3 above) is what Minion must reproduce, and
this artifact now DEMONSTRATES agreement with that authority mechanically rather than asserting
it follows from the standard's prose.

## 3. ICU framing corrected

Runtime metadata (Node's own reported ICU/Unicode version, e.g. "ICU 77.1 / Unicode 16.0" for
v22.19.0) describes the JavaScript-visible `Intl`/ICU surface, which is a SEPARATE subsystem from
the URL/domain-conversion path. Node's `fileURLToPath`/`domainToUnicode` do not call ICU directly
at all for this operation -- confirmed by the `node_url.cc` source above, which calls
`ada::idna::to_unicode` exclusively, and by Ada's own source, which implements Punycode
decode/encode and its validity criteria as generated data tables internal to the `ada-url`
project, not via any ICU binding. The earlier characterization's framing of this as "Node ICU vs
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
against the DIRECT Ada 2.9.2 oracle exactly as Node itself reports.

## 5. Node 22.19.0 vs direct Ada 2.9.2 -- proof, not assumption

A systematic corpus was built using the SAME methodology the independent review itself used ("one
or more representative codepoints from every interval in `idna.uts46data`"): one representative
codepoint from each of the 8,372 non-ASCII/non-surrogate intervals in `idna==3.19`'s own
`uts46data` interval table, each placed in a Punycode-encoded label as `xn--<encoding of
"a"+codepoint>` (a leading `a` isolates the swept codepoint from the leading-combining-mark
structural rule) -- **8,244 cases** after excluding ASCII and surrogate-range intervals.
Committed: `assurance/layers/data/12-python-r002-ada-oracle/systematic_corpus.txt`.

Run through the SAME `node_probe`-style harness (`systematic_node_probe.mjs`, committed) against
checksum-verified Node v22.19.0 (Pi's declared floor) and v22.23.2 (drift check), and through
`oracle.cpp` (the direct Ada 2.9.2 oracle):

```text
NODE 22.19.0 vs NODE 22.23.2 (drift check)
    cases tested: 8244
    acceptance mismatches: 0
    output mismatches: 0

NODE 22.19.0 vs DIRECT ADA 2.9.2
    cases tested: 8244
    acceptance mismatches: 0
    output mismatches: 0
```

**Zero mismatches over the entire systematic corpus.** This is not inferred from reading the
source chain in section 1 -- it is measured, mechanical agreement between the two executables.
Strategy A's (direct Ada reuse) core premise is proven, not assumed.

## 6. Python-accessible Ada implementations -- separately characterized, not assumed equivalent

The Python candidate's current dependency is `ada-url>=4.0.0` (per `pyproject.toml`). Per the
reviewer's own instruction ("Ada 4.0 is a much later implementation/data generation than Node's
vendored 2.9.2 -- do not assume equivalence"), this was NOT assumed -- it was measured, using the
SAME 8,244-case systematic corpus, through the two-step pipeline Node's own architecture uses
(`ada_url.URL(u).host` for the parse/accept step, then `ada_url.idna_to_unicode(host)` for the
decode step; an unchanged `"xn--..."` result after the decode step is treated as rejected,
matching `oracle.cpp`'s own convention and Ada's own `to_unicode` fallback behavior):

```text
DIRECT ADA 2.9.2 vs PYTHON ada-url==4.0.0 (current pinned dependency)
    cases tested: 8244
    acceptance mismatches: 115
    output mismatches: 0
```

All 115 mismatches are Ada-2.9.2-rejects/ada-url-4.0.0-accepts or the reverse, at codepoints that
were assigned to a general category between Ada 2.9.2's (~September 2024) and Ada 4.0.0's
(~2026) respective Unicode-data-generation snapshots -- e.g. `xn--a-nnd` (U+0897 ARABIC PEPET,
assigned in a later Unicode version than Ada 2.9.2's own data) is rejected by Ada 2.9.2 but
accepted by `ada-url==4.0.0`; `xn--a-0hc` (U+05D0 HEBREW LETTER ALEF, long-assigned) is accepted
by Ada 2.9.2 but rejected by `ada-url==4.0.0` in this systematic sweep (full row-level detail:
`assurance/layers/data/12-python-r002-ada-oracle/README.md`'s own headline-results section and
the raw `systematic_pyada_400.txt`/`systematic_ada292.txt` files). This IS a genuine
Unicode-version-boundary gap, exactly as the reviewer's own framing anticipated for THIS specific
pairing -- 115/8244 (1.4%), not the far larger drift an earlier (methodologically flawed, `.host`
attribute only, no `idna_to_unicode` decode step) internal check of this artifact's own working
notes had first suggested.

## 7. Investigating whether Python can call the exact Ada 2.9.2 primitive directly

Rather than accept the 1.4% `ada-url==4.0.0` gap or hand-port Ada's algorithm a third time, the
PyPI release history of `ada-url` itself was checked
(`https://pypi.org/pypi/ada-url/json`) for a release whose vendored Ada core matches 2.9.2
(released ~September 2024, per the singleheader amalgamation's own
`/* auto-generated on 2024-09-02 ... */` comment). `ada-url==1.15.3` (uploaded
2024-09-09T19:44:57, four days after that generation date) was installed in an isolated scratch
virtual environment (no modification to the project's own pinned dependency) and run through the
SAME 8,244-case corpus via the SAME two-step pipeline:

```text
DIRECT ADA 2.9.2 vs PYTHON ada-url==1.15.3
    cases tested: 8244
    acceptance mismatches: 0
    output mismatches: 0
```

**Exact match.** `ada-url==1.15.3`'s own `URL(...)` constructor additionally already REJECTS
`xn--8g0n`/`xn--abc-ppe`/`xn--abc-jdc`/`xn--a` directly at parse time (raising `ValueError`) --
unlike `ada-url==4.0.0`, whose `.host` property passed these through unvalidated (the specific,
now-corrected methodology error in an earlier internal check of this same investigation). Host
syntax/IPv4/IPv6/forbidden-code-point handling (the OTHER responsibility `_file_url_to_path`
delegates to `ada_url.URL`, unrelated to this specific finding) was spot-checked and is
unchanged: IPv6 canonicalization (`[::ffff:192.168.1.1]` -> `[::ffff:c0a8:101]`), invalid IPv4
rejection (`256.256.256.256`), and domain lowercasing (`EXAMPLE.COM` -> `example.com`) all match
prior findings.

`ada-url==1.15.3` publishes prebuilt wheels for CPython 3.8-3.12 and PyPy on Windows,
manylinux (x86_64/aarch64), musllinux (x86_64/aarch64), and macOS (x86_64/arm64/universal2) --
full platform coverage, no build toolchain required for installation (verified against the
package's own PyPI file listing).

**`PyICU` was also investigated and ruled out** (unchanged conclusion from the prior revision):
`uv pip install pyicu` fails in this environment (`RuntimeError: Please install pkg-config... or
set ICU_VERSION`), requiring a system ICU installation -- the same portability/deployment-risk
disqualification already applied to `urlstd`/`icupy` in the original R002 library research. Not
relevant regardless, per section 3 above: Node's URL/domain-conversion path does not call ICU at
all for this operation.

## 8. Reclassifying the prior 30 mismatches

The rejected prototype (`_relaxed_punycode_label`/`_relaxed_codepoint_ok`, composing `idna`'s
Unicode-17.0 `uts46data` VALID/DEVIATION status with Python `unicodedata`'s bidi/combining-mark
checks) was run against the SAME 8,244-case systematic corpus and compared against the direct
Ada 2.9.2 oracle:

```text
DIRECT ADA 2.9.2 vs REJECTED PROTOTYPE (idna.uts46data-driven)
    cases tested: 8244
    mismatches: 59 (58 in ONE direction: Ada accepts, prototype rejects;
                     1 in the opposite direction)
```

(59 on this specific 8,244-case corpus, not necessarily the reviewer's own reported "30" --
different systematic corpora sample different representative codepoints per interval; both
figures are evidence of the SAME underlying defect class, not a discrepancy requiring
reconciliation.)

**Root-cause grouping** (every mismatch inspected, not left as one generic "Unicode version"
bucket):

```text
Group 1 -- Unicode codepoint-assignment-boundary difference between idna's Unicode-17.0
    uts46data table and Ada 2.9.2's own (older, ~Unicode-16-era) validity data:
    the majority of the 58 "Ada accepts, prototype rejects" cases. Example: xn--a-x88h
    (a FARSI/Arabic-Indic-adjacent codepoint) -- Ada 2.9.2 accepts it, but idna's own
    Unicode-17.0 table does NOT classify it VALID/DEVIATION (a genuine version-boundary
    disagreement, matching the reviewer's own diagnosed shape).

Group 2 -- algorithmic/structural difference, NOT explained by Unicode-version alignment at
    all: Ada 2.9.2's OWN validity gate (confirmed in section 1 to live inside
    ada::parse<ada::url>'s internal host-processing, not in a simple per-codepoint
    VALID/DEVIATION table lookup) accepts some codepoints idna.uts46data's table structurally
    excludes regardless of version -- for example, several high-plane script-extension
    codepoints in the "Ada accepts, prototype rejects" set do not correspond to any
    documented Unicode-17.0-vs-16.0 reclassification, indicating idna.uts46data's VALID/
    DEVIATION-only acceptance criterion is not a faithful STRUCTURAL proxy for whatever
    validity gate Ada's own C++ implementation actually applies -- independent of which
    Unicode version that table targets. This is the artifact's own central, corrected
    conclusion: even a hypothetical PERFECTLY Unicode-version-aligned reimplementation of
    idna.uts46data-based validation would NOT be guaranteed to match Ada 2.9.2, because the
    two implementations are not running the same algorithm shape, only a similar one.

Both discriminating witnesses (xn--3pc, xn--8g0n) fall in Group 1 territory for xn--8g0n
(a newer-Unicode-assigned CJK extension codepoint idna's Unicode-17.0 table marks valid but
Ada 2.9.2 -- and Node -- reject) and reveal a Group-2-shaped defect for xn--3pc (a
long-assigned combining mark idna's own check_initial_combiner structural rule rejects
outright, regardless of Unicode version, that Ada's actual pipeline does not reject at all
for a hostname already presented as pre-formed Punycode).
```

This reclassification directly supports section 9's conclusion: the fix is not "align Unicode
table versions" (a Group-1-only fix) -- it is "stop reimplementing the algorithm in Python
entirely" (addressing both groups at once, per section 7's own proof).

## 9. The two discriminating witnesses -- retained as regression witnesses only

```text
xn--3pc   -- Node/Ada 2.9.2 ACCEPTS (decodes to U+0C3C TELUGU SIGN NUKTA)
xn--8g0n  -- Node/Ada 2.9.2 REJECTS (U+2EBF0 CJK UNIFIED IDEOGRAPH-2EBF0, PARSE_ERROR)
```

Both are now part of the permanent 8,244-case systematic corpus committed in section 5's own
directory, and will be added to the production R002 differential corpus
(`12-python-r002-differential-corpus.md`) on implementation. They do NOT themselves define the
rule -- section 5's mechanical Node-vs-Ada-2.9.2 agreement is the rule; these two are
regression-detection instruments confirming an implementation reproduces it.

## 10. Implementation strategies evaluated

```text
STRATEGY A -- reuse an Ada implementation directly, exact-pinned to a version matching
    Node's own vendored core (ada-url==1.15.3)
    behavioral match to Ada 2.9.2: EXACT (0/8244, section 7)
    portability: full wheel coverage, all major platforms + PyPy, no build toolchain
    dependency complexity: single ordinary pip dependency, same package already used
    maintenance: package is no longer at HEAD (project moved to 4.x), but an EXACT pin is
        the explicit goal here, not staying current -- see section 15's version-stability
        mechanism for how this is kept safe
    RECOMMENDED

STRATEGY B -- pin/use a NEWER Ada version behaviorally compatible with Node 22.19
    ada-url==4.0.0 (current dependency): NOT compatible (115/8244 mismatches, section 6)
    no other candidate release was found to be BOTH more current than 1.15.3 AND exactly
        matching Ada 2.9.2's behavior over this corpus -- not further pursued; Strategy A's
        exact-match release already exists and is a strictly better fit

STRATEGY C -- port the exact Ada 2.9.2 IDNA algorithm/data into Python by hand
    attempted TWICE now (round 2's "So"-category patch; this episode's own idna.uts46data-
        driven prototype) and failed differently both times
    section 8's own reclassification shows the failure is not solely a fixable Unicode-
        version-alignment problem -- Group 2 is a genuine algorithm-shape difference that
        would require reverse-engineering Ada's OWN validity gate (confirmed in section 1 to
        live inside ada::parse's internal host-processing, not exposed as a simple
        documented table) from C++ source, an ongoing maintenance burden with no assurance
        of completeness
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

## 11. No mixed-version composition is proposed

This revision does not propose any composition of `idna.uts46data` (at any version) with Python
`unicodedata` (at any version) as authoritative. Section 8 shows why: even with perfect Unicode-
version alignment, such a composition would not be guaranteed to match Ada 2.9.2's own validity
gate, because the two are not the same algorithm. `_relaxed_punycode_label`/
`_relaxed_codepoint_ok` (the round-2-rejected prototype) are proposed for REMOVAL on
implementation, not further patching.

## 12. Recommended implementation strategy

**Strategy A**: pin `ada-url==1.15.3` EXACTLY (not a range) as the sole dependency for BOTH
`_file_url_to_path`'s host-syntax/IPv4/IPv6/forbidden-code-point role (already delegated to
`ada_url.URL`, unaffected by this finding beyond the version pin itself) and
`_domain_to_unicode`'s Punycode-to-Unicode decode role, which changes from the current
`idna.decode()`-plus-relaxed-retry composition to `ada_url.idna_to_unicode()` directly, gated by
`ada_url.URL(...)`'s own now-correctly-rejecting parse step. The `idna` package's role in the
implementation is eliminated for this specific decode responsibility (it may remain a dependency
for anything else that needs it, if applicable elsewhere in the codebase -- not investigated
here, out of this finding's scope).

## 13. Version-stability mechanism

Per the reviewer's own requirement ("what prevents a dependency upgrade from silently changing
R002 behavior"), TWO independent mechanisms are proposed, on implementation:

```text
1. EXACT dependency pin: "ada-url==1.15.3" in pyproject.toml (not ">=", not "~="). A future
   maintainer wanting to move to a newer ada-url must do so as an explicit, deliberate action,
   not an incidental transitive/range-resolved bump.

2. Mechanically-checked differential gate: the 8,244-case systematic corpus committed in
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

## 14. Portable contract (unchanged)

```text
For file:// behavior adopted from Pi, Minion reproduces pinned Pi/Node observable semantics.
```

Ada 2.9.2 is the REFERENCE IMPLEMENTATION AUTHORITY this pass uses to verify that reproduction --
not an abstract requirement that Python "must use Ada 2.9.2" as an API contract. Rust may use a
different mechanism (its own `url`/`idna` crate ecosystem) provided it reproduces the same
observable semantics against the SAME oracle (section 15).

## 15. Rust implications (not modified this pass)

`EXEC-002`/`EXEC-003` file:// conversion remains `REVALIDATE_REQUIRED`, unchanged and untouched.
The FUTURE Rust revalidation plan should use the SAME Node 22.19/Ada 2.9.2 executable oracle
(this artifact's own `assurance/layers/data/12-python-r002-ada-oracle/` corpus and tooling) as
its comparison target, rather than comparing Rust's own `url` crate output only against Python's
implementation (which would make Rust's certification transitively dependent on Python's own
correctness rather than on the shared authoritative oracle both must independently satisfy).

## 16. R004 -- untouched

`L12-PY-R004`'s provisional closure (from targeted closure review 6,
`minion-agent-docs#120` @ `09423f0a962d1139ba16155eff6113c026a1f89a`) is not reopened by this
pass. Rust's R004-A/R004-B revalidation/remediation remain separate, future, Rust-owned work.

## 17. Verification checklist

```text
1. PR #44 unchanged.......................... CONFIRMED (still 1848873fc9626b699990a29b1f35c7baba78cc34)
2. Rust production code unchanged............ CONFIRMED (last touching commit 429368c, unmodified)
3. Node v22.19.0 source chain cited exactly... CONFIRMED (node_url.cc lines 210-228, 611-624, quoted verbatim)
4. Ada 2.9.2 version cited exactly........... CONFIRMED (ADA_VERSION "2.9.2" in vendored header)
5. Direct Ada 2.9.2 oracle exists, reproducible CONFIRMED (oracle.cpp + vendored source + README build steps)
6. Node vs Ada behavior compared mechanically. CONFIRMED (8244/8244 agreement, section 5)
7. Python ada-url 4.0 behavior compared........ CONFIRMED (115/8244 mismatches, section 6, own subsection)
8. No mixed-version custom UTS46 proposal...... CONFIRMED (section 11; prototype proposed for removal)
9. Prior systematic evidence retained/superseded CONFIRMED (8244-case corpus committed; prior 27-row
                                                  matrix's own cases are a subset, all still passing)
10. xn--3pc / xn--8g0n permanent witnesses...... CONFIRMED (section 9; committed in the 8244-case corpus)
11. Dependency/version stability addressed..... CONFIRMED (section 13, two independent mechanisms)
12. R004 provisionally closed, not reopened.... CONFIRMED (section 16)
13. Rust EXEC-002/EXEC-003 REVALIDATE_REQUIRED. CONFIRMED (section 15, unchanged)
14. Implementation remains unauthorized........ CONFIRMED (header banner; PROPOSED, not AGREED)
15. Layer 13 remains NOT STARTED............... CONFIRMED (not mentioned/touched anywhere in this pass)
```

## Convergence checkpoint

```text
CONVERGENCE CHECKPOINT
    PROPOSED FOR IMPLEMENTATION

OPEN FINDINGS
    L12-PY-R002

ACCEPTANCE WITNESSES
    assurance/layers/12-execution-seams-python-r002-root-cause-characterization-v2.md
        (this artifact)
    assurance/layers/data/12-python-r002-ada-oracle/ (oracle.cpp, vendored Ada 2.9.2 source
        with checksums, systematic_corpus.txt [8244 cases], all raw oracle outputs, README.md)

NORMATIVE DELTAS
    minion-agent-python/pyproject.toml: pin ada-url==1.15.3 exactly (currently >=4.0.0)
    minion-agent-python/src/minion_agent/execution/filesystem.py: _domain_to_unicode
        delegates to ada_url.idna_to_unicode() directly (gated by ada_url.URL()'s own
        parse-time rejection); _relaxed_punycode_label/_relaxed_codepoint_ok removed
    pi-parity-manifest.yaml EXEC-002 row: cite the corrected authority chain (Pi -> Node
        22.19.0 -> Ada 2.9.2) and the exact-pin + differential-gate version-stability
        mechanism, superseding the "So"-category and UTS46-flag-table framings
    a new permanent pytest fixture asserting the pinned ada-url reproduces the committed
        Ada-2.9.2-oracle-verified corpus exactly (section 13, mechanism 2)

NEXT_OWNER
    Codex (independent checkpoint review)
```

`minion-agent#44` remains at `1848873fc9626b699990a29b1f35c7baba78cc34`, unmodified by this
pass. `minion-agent-rust/**` unmodified. This artifact does not, and per §11.8.10 cannot,
self-approve `AGREED FOR IMPLEMENTATION`.
