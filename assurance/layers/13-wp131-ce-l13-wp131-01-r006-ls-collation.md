# CE-L13-WP131-01 — Lane C: `ls` collation semantics (`R006`)

Mode: §11.8 sub-checkpoint characterization, Lane C only. **No Python or Rust implementation
performed or authorized. No Layer 12 production change. Review this lane only -- do not reopen
`R003`/`R004`/`R008` (frozen `CHECKPOINT-READY`) or `R002`/`R005` (`OWNER_DECISION_RESOLVED`:
`R002-A`, `R005-A`) unless this lane presents concrete contradictory evidence.**

Parent episode: `CE-L13-WP131-01` (`minion-agent#48`). Revises the prior combined checkpoint's
`R006` section (`minion-agent-docs#132` @ `f873217f35c142b0177bddb80e8934ddf2eac2d9`, rejected in
`minion-agent-docs#135`: "not yet neutral or implementable... A/B/C must each describe an
actually implementable cross-language rule").

---

## Pinned Pi's exact pipeline, re-confirmed

`ls.ts:154-155`, quoted: `entries.sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()))`
-- no locale argument passed to either `toLowerCase()` or `localeCompare()`. `Array.prototype
.sort` is a stable sort (ES2019+), so any pair comparing equal preserves its pre-sort (directory-
enumeration) relative order.

## Correction: `toLowerCase()` is not "case folding" -- verified, both directions

**`.toLowerCase()` performs Unicode's full default case-conversion mapping, not a simple 1:1
codepoint substitution, and is NOT the same operation as Unicode case folding** -- both facts
verified directly this session, in both JavaScript and Python:

```text
"İ" (U+0130, LATIN CAPITAL LETTER I WITH DOT ABOVE) .toLowerCase()
  JS:     "i̇" (TWO codepoints: U+0069 "i" + U+0307 COMBINING DOT ABOVE) -- a
          1-to-2 EXPANSION, proving this is the FULL default case-conversion
          mapping, not a simple per-codepoint table
  Python: str.lower() produces the IDENTICAL two-codepoint expansion --
          Python's .lower() also implements Unicode's full default case
          mapping, not a simple mapping (a genuinely useful, verified point
          of cross-language agreement, unlike collation itself, below)

"ß" (U+00DF, LATIN SMALL LETTER SHARP S -- already lowercase) .toLowerCase()
  JS:     "ß" (UNCHANGED)
  Python: str.lower() -> "ß" (UNCHANGED, matches)
  -- if this were FULL CASE FOLDING (a distinct Unicode algorithm, used for
  case-INSENSITIVE COMPARISON, not case conversion), "ß" folds to "ss" per
  the Unicode CaseFolding.txt data file's own full-folding mapping. It does
  NOT under .toLowerCase() in either language. "STRASSE".toLowerCase() ->
  "strasse" (7 chars) != "straße".toLowerCase() -> "straße" (6 chars) --
  they remain UNEQUAL strings after toLowerCase(), which is why the
  original Lane checkpoint's "case-folded" terminology was imprecise
  enough to matter: a reader could reasonably assume ß/ss equivalence,
  which does not hold for the ACTUAL Pi operation.
```

**Corrected terminology for every option below**: the primary transform is `toLowerCase()`
(Unicode Default Case Conversion, full mapping, locale-independent table -- distinct from both
"simple case mapping" and "case folding"), never "case folding" or "case-folded" as shorthand.

## `localeCompare()`'s default-locale dependency, re-confirmed with an added negative control

Unchanged from the rejected checkpoint's own findings, re-verified: this session's environment
resolves `new Intl.Collator().resolvedOptions().locale` to `"en-001"` (Node 22.15.1, ICU 76.1,
`win32`); `LANG`/`LC_ALL` environment-variable overrides had no effect on this Windows/Node build
(a negative result for cross-machine reproduction within this session, not a refutation -- the
source-level fact that no locale is ever pinned in `ls.ts` stands independent of this session's
own inability to reproduce a second concrete environment).

**New this lane**: constructed a direct discriminating case showing ordinal (codepoint) comparison
and locale-aware comparison genuinely diverge, not merely differ in this session's specific
corpus coincidentally agreeing:

```text
Ordinal comparison (toLowerCase(), then plain codepoint '<'/'>'):
  non-ASCII characters (e.g. "é" U+00E9 = 233) sort AFTER every ASCII
  letter (e.g. "z" U+007A = 122) unconditionally -- an ordinal comparator
  can NEVER interleave an accented/non-Latin name among ASCII names the
  way locale-aware collation does (locale collation "tailors" many
  accented Latin letters to sort adjacent to their base letter, e.g. é
  near e, not after z).

Locale comparison (this session's default en-001):
  demonstrated in the original Lane checkpoint's corpus: "café"/"cafe"/
  "Café" interfile with each other and with plain ASCII names; "straße"
  sorts adjacent to "strasse" (an ICU tailoring rule, not a codepoint
  proximity).
```

These are not the same rule producing coincidentally identical output on small examples -- they
are two different algorithms that agree only when a corpus happens not to exercise their
difference (as the original checkpoint's specific 3-name `STRASSE`/`straße`/`strasse` sub-case
did, misleadingly, since `ß`'s codepoint (223) does happen to exceed `s`'s (115) ordinally, in
that one case producing the same relative order both ways -- not evidence the two algorithms
generally agree).

## Corrected, concrete option matrix

### `R006-A` -- environment-sensitive host collation (corrected: honest divergence disclosure, no
claim of literal Pi-parity)

**Concrete mechanisms, identified by language (the rejected checkpoint left this abstract)**:

```text
Python: locale.strxfrm() after locale.setlocale(locale.LC_COLLATE, "")
        -- uses the OS's OWN native collation facility, NOT ICU. Verified
        this session: default Windows locale identifier is
        ('English_world', '1252') -- a WINDOWS-SPECIFIC locale name/
        codepage string with NO equivalent form on POSIX, where Python's
        locale module instead surfaces glibc/musl-style locale names
        (e.g. "en_US.UTF-8"). This is not merely "a different engine from
        Node's ICU" -- it is two DIFFERENT locale-naming/data systems
        within Python itself, depending on the host OS, neither of which
        is ICU.

Rust:   a system-ICU binding (e.g. `icu` crate family bound to the host's
        installed ICU, where available) OR an OS-native collation API
        binding. No such binding is currently a direct dependency of
        minion-agent-rust (verified this lane: Cargo.lock currently
        includes icu_collections/icu_locale_core/icu_normalizer/
        icu_properties/icu_provider -- foundational ICU4X components,
        transitively present, likely via an unrelated normalization/IDNA
        dependency chain -- but NOT icu_collator, the actual comparison
        crate; none of the present crates perform locale-aware string
        comparison today).
```

**Honest divergence disclosure (corrects the rejected checkpoint's implicit "preserves Pi's
semantics" framing)**: none of these mechanisms shares Node/V8's specific default-locale-
resolution algorithm, ICU version (76.1 in this session), or collation-rule data. Even where a
given mechanism happens to use ICU (a hypothetical Rust ICU binding), matching Node's *exact*
observable default locale requires independently replicating Node's own resolution algorithm (how
it derives `"en-001"` from the host environment) -- not something any of these bindings does
automatically by merely "having no pinned locale." **This option cannot honestly be described as
preserving Pi's exact environment-sensitive behavior; at best it preserves the *category* of
behavior (locale-sensitive, non-deterministic across machines) while using entirely different,
independently-resolved defaults per language.**

```text
Cross-language reproducibility: NONE guaranteed -- three independently-
  resolved, non-ICU-for-two-of-three-languages defaults
Pi-fidelity:                    approximate at best, unverifiable without
  per-machine testing; the CATEGORY of behavior (locale-sensitive) matches,
  the SPECIFIC observable order does not reliably match
Testability:                    poor -- no single expected order is
  portable across CI/dev machines, let alone stable relative to Pi
```

### `R006-B` -- deterministic Minion ordering (corrected terminology, corrected tie-break framing)

**Corrected exact algorithm** (supersedes the rejected checkpoint's imprecise "simple case-folded"
wording):

```text
primary key:   toLowerCase() -- Unicode's full Default Case Conversion
               mapping (verified above), NOT a simple mapping, NOT case
               folding; Unicode version = whatever version each
               language's own standard library ships (a residual,
               likely-negligible cross-version risk, not eliminated by
               this option, noted as an open sub-question rather than
               ignored)
comparison:    ordinal (codepoint-by-codepoint) comparison of the two
               lowercased strings
tie-break:     ordinal comparison of the two ORIGINAL (un-lowercased)
               strings
```

**Corrected disclosure (the rejected checkpoint's actual defect)**: this tie-break is **not** "a
deterministic spelling of Pi's own behavior." Pi's real tie-break, for two names that compare
equal after `toLowerCase().localeCompare()`, is **whatever order the underlying filesystem
happened to enumerate them in** (preserved by `Array.sort`'s stability) -- not a string comparison
at all. An ordinal-original-string tie-break imposes a NEW, filesystem-enumeration-independent
rule (e.g. it would always order `"Apple"` before `"apple"` -- uppercase `A` = 0x41 sorts before
lowercase `a` = 0x61 -- regardless of which one the filesystem happened to list first), which is
observably different from Pi's actual behavior on any real directory where the enumeration order
disagrees with ordinal original-string order. **This is a genuine, disclosed intentional
divergence, not a faithful determinization of Pi's own rule** -- Pi's own rule is not itself
deterministic (it depends on filesystem enumeration order, which this project has not
characterized and which is itself platform/filesystem-driver-dependent), so no tie-break choice
here can be "a deterministic spelling of" a rule that has no single spelling to begin with.

```text
Cross-language reproducibility: FULL -- ordinal comparison of Unicode
  code points is identical in every language with correct Unicode string
  handling; toLowerCase()'s full-mapping table is a standard Unicode data
  table any conformant implementation reproduces identically (Python
  verified to agree with JS on the one tested case above)
Pi-fidelity:                    DIVERGENT, disclosed -- non-ASCII
  collation-tailored adjacency (e.g. é near e) is lost, replaced by
  strict "all non-ASCII sorts after all ASCII" ordinal grouping; the
  tie-break for case-differing names is a NEW deterministic rule, not Pi's
  own (non-deterministic, enumeration-order-dependent) tie behavior
Testability:                    EXCELLENT -- one portable expected order
  per test corpus, valid on every platform/CI environment
```

### `R006-C` -- pinned collation implementation (corrected: concrete candidate libraries identified)

**Concrete candidates, identified this lane (the rejected checkpoint left this entirely
theoretical)**:

```text
Python: PyICU (`pip install PyICU`) -- a mature, actively maintained
        binding to a real ICU installation, exposing icu.Collator with
        explicit locale/rule control. Requires either bundling a specific
        ICU version or depending on the host's installed ICU (a
        version-pinning question of its own).

Rust:   the `icu` crate family's `icu_collator` component (ICU4X,
        the official Unicode-maintained Rust port of ICU) --
        NOT currently a dependency (verified this lane: absent from
        Cargo.lock, though its sibling foundational crates
        icu_normalizer/icu_properties/icu_provider are already
        transitively present at icu_provider 2.3.1, likely via an
        unrelated dependency chain -- e.g. IDNA/URL handling, matching
        this same project's own R002/L12-PY-R002 experience with
        delegated Unicode-processing libraries). Adding icu_collator at
        a version compatible with the already-present 2.3.1-family
        crates is the natural path.
```

**Feasibility assessment (the rejected checkpoint's own required gap)**: both candidates are real,
maintained libraries with active development; PyICU wraps genuine ICU (version depends on the
bundled/system ICU), and `icu_collator` is ICU4X -- Unicode's own reimplementation of ICU
semantics in Rust, not merely "ICU-inspired." **These are NOT the same codebase as Node's own
bundled ICU** (Node uses `full-icu`/system ICU via V8's own binding, a C++ ICU build), so even
this option does not achieve literal Pi byte-for-byte parity without ALSO pinning the exact ICU
data/rule VERSION across all three ICU integrations (Node's, PyICU's, and ICU4X's) -- itself a
nontrivial, ongoing maintenance burden (three independent ICU integrations, potentially updated on
different schedules, would need deliberate version alignment, analogous to `WP-13.4`'s exact
`fd`/`rg` pinning question but for a locale-data library instead of a binary tool).

```text
Cross-language reproducibility: HIGH if both bindings are pinned to
  compatible collation-rule versions (not automatic -- requires ongoing
  version-alignment maintenance across two independent ICU integrations)
Pi-fidelity:                    HIGH if the pinned locale/rules are
  additionally chosen to match Node's own ICU 76.1 default-locale
  resolution (en-001 in this session) -- itself requiring either
  replicating Node's resolution algorithm or simply hardcoding that same
  locale as Minion's own pin (a governance choice, not automatic)
Testability:                    GOOD once pinned -- portable, but only as
  stable as the pin itself; an un-pinned "use whatever ICU is installed"
  variant would have the same poor testability as R006-A
Deployment/maintenance burden:  the recurring "third dependency to keep
  version-aligned" cost identified above -- not free, but bounded and
  precedented by this project's own WP-13.4 exact-pin approach
```

No option is selected. `TOOL-028`'s collation scope cannot proceed to contract-review-ready status
until the owner picks one (or specifies another option this characterization did not anticipate).

## Lane-C status

```text
R006:  OWNER_DECISION_REQUIRED
```
