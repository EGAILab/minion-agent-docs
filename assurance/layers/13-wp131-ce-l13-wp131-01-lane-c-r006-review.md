# CE-L13-WP131-01 Lane C R006 independent review

**Mode:** convergence sub-checkpoint review only. No Python or Rust implementation was performed
or authorized. No Layer-12 or Layer-14 work was performed.

## Exact target

```text
coordination issue:  EGAILab/minion-agent#48
status:              CONTRACT_CONVERGENCE
next owner:          Codex
docs PR:             EGAILab/minion-agent-docs#132
docs head:           54eaadbf29bc7bd85d3bc7f341a9285b78f59525
manifest PR:         EGAILab/minion-agent#52
manifest head:       cca8d8b325bb159be549e10c8321b3468f043e7f (frozen)
docs base:           master @ 0bbd737fab8c1360995f4efff2b41c1c5531a9c3
code base:           main @ 92aa4be168dc82111832467922089206e858a9c4
pinned Pi:           b7bb00b936dbe21b8e160b3e89efdec361846699
episode:             CE-L13-WP131-01
artifact:            assurance/layers/13-wp131-ce-l13-wp131-01-r006-ls-collation.md
scope:               R006 only (Lane C)
```

The issue-recorded heads matched the open remote PR heads and were remote-reachable. The issue
carried valid governance provenance, and the candidate was not derived from quarantined work.
R003/R004/R008 and resolved R002-A/R005-A were not reopened.

## Result

```text
R006 CHARACTERIZATION:  REJECTED
OWNER DECISION READY:   NO
IMPLEMENTATION:         NOT AUTHORIZED
```

## Verified source facts

Pinned Pi's comparator is exactly:

```text
a.toLowerCase().localeCompare(b.toLowerCase())
```

with no explicit locale, followed by stable `Array.sort`. Direct probes confirmed:

- U+0130 lowercases to U+0069 U+0307 in both pinned Node and current Python;
- U+00DF remains U+00DF under lowercase, while full case folding maps it to `ss`;
- the current Node environment resolves `Intl.Collator` to `en-001`, ICU 76.1, CLDR 46,
  Unicode 16.0;
- Python's current process locale is `English_world.1252` and its Unicode tables are 15.1;
- Rust 1.97.1 reports `char::UNICODE_VERSION == 17.0.0`;
- `icu_provider` 2.3.1 and sibling ICU4X components are transitively present through the
  URL/IDNA dependency chain, while `icu_collator` is absent.

The correction from "case folding" to Unicode default lowercase mapping and the disclosure that
Pi's equal-comparison tie order is filesystem-enumeration order are both accurate.

## Blocking findings

### L13-WP131-R006-C1 — `CONTRACT_ASSURANCE_DEFECT`

R006-A's concrete Rust mechanism is factually wrong. It offers a "system-ICU binding (e.g. `icu`
crate family bound to the host's installed ICU)." The Rust `icu` crate is the ICU4X meta-crate;
its official documentation describes compiled data and explicit `DataProvider`s. It is not a
binding to the host's installed ICU4C library. A real native ICU4C binding is a different crate
family, such as `rust_icu_ucol`/`rust_icu_sys`.

This matters to the option's observable claim: ICU4X compiled data is a pinned/library-provided
profile, not the proposed host-native/default environment-sensitive mechanism. The option as
written therefore does not identify the concrete Rust realization it claims to identify.

Required correction: name an actual host-dependent Rust mechanism and its platform support, such
as native OS collation APIs or an ICU4C binding linked to the host ICU installation. State the
global/process-locale and concurrency consequences of Python `setlocale`, and do not use the
ICU4X `icu` crate as evidence for host-ICU behavior.

Primary references:

- <https://docs.rs/icu/latest/icu/> — `icu` is the ICU4X meta-crate and describes compiled/custom
  provider data;
- <https://github.com/google/rust_icu> — `rust_icu` exposes bindings to ICU4C's C API.

### L13-WP131-R006-C2 — `CONTRACT_ASSURANCE_DEFECT`

R006-B simultaneously leaves Unicode lowercase-table versions unpinned and claims
`Cross-language reproducibility: FULL` plus one portable expected order "valid on every
platform." Those statements cannot both be true for the general input domain.

The current toolchains already demonstrate the version split:

```text
pinned Node: Unicode 16.0
current Python: Unicode 15.1
current Rust: Unicode 17.0
```

Rust's own standard-library documentation explicitly says the Unicode version underlying `char`
and `str` methods changes over time and is not considered a breaking change. A filename containing
a code point whose assignment or lowercase mapping differs across those table versions can receive
different primary keys. Agreement on U+0130 and U+00DF proves only those witnesses, not the claimed
universal reproducibility.

Required correction: either pin a common lowercase mapping/version and describe how both languages
consume it, or downgrade the reproducibility claim and disclose version-dependent ordering as a
real residual divergence/risk. A fixed canonical corpus can be portable only if every character in
that corpus is proven stable across the supported table versions; that is weaker than a fully
reproducible general rule.

Primary reference: <https://doc.rust-lang.org/std/primitive.char.html> documents that
`char::UNICODE_VERSION` governs Unicode-dependent string behavior and changes with toolchain
updates.

### L13-WP131-R006-C3 — `CONTRACT_ASSURANCE_DEFECT`

R006-C names real libraries but still does not provide the concrete shared
locale/ruleset/**version** strategy required by the prior challenge. PyICU uses ICU4C. Rust
`icu_collator` uses ICU4X with its own provider/compiled data. The candidate acknowledges they are
different engines and says they would need "compatible" versions, but supplies neither a mapping
between ICU 76.1/CLDR 46 and ICU4X 2.3.1 data nor a differential witness showing identical
comparison results for the proposed profile.

The claim `Pi-fidelity: HIGH` is also too broad. Hardcoding `en-001` may match this review machine's
default, but Pi deliberately asks the host for its default locale. On a host where Pi resolves a
different locale, a pinned `en-001` Minion profile is an intentional observable divergence.

A more concrete shared-engine candidate exists and must at least be assessed: link both PyICU and
Rust `rust_icu_ucol` to the same pinned ICU4C library/data artifact, then pin locale and collator
options and run the discriminating corpus through Node, Python, and Rust. ICU4X may remain an
option, but then cross-engine equivalence needs mechanical differential evidence rather than an
assumption based on common Unicode stewardship.

Required correction:

1. provide at least one exact candidate tuple: engine/artifact version, locale, collation/options,
   and data/version discipline for both languages;
2. state whether it is a shared ICU4C artifact or a cross-engine mapping;
3. if cross-engine, define the differential evidence required before the option is feasible;
4. classify a fixed locale as divergence from Pi's host-default behavior except on environments
   where that default happens to match.

## Option-set assessment

The three high-level policies are a useful and likely exhaustive partition:

1. host/environment-sensitive ordering with approximate Pi similarity;
2. deterministic ordinal Minion ordering;
3. a pinned collation profile.

The problem is not the number of options. It is that their concrete mechanisms, reproducibility,
and parity consequences are still misstated. The owner cannot compare cost and fidelity reliably
from the exact candidate.

## Verdict and next action

```text
R006:                      CHARACTERIZATION REJECTED
Lane C:                    CHANGES REQUIRED
Implementation authorized:NO
Python WP-13.1:            NOT_IMPLEMENTED / NOT AUTHORIZED
Rust WP-13.1:              NOT_IMPLEMENTED / BLOCKED
Layer 13 cross-language:   NOT CLOSED
Layer 14:                  NOT STARTED
```

Return only Lane C to the shared-contract owner. Correct the Rust host-collation mechanism, the
unpinned-Unicode reproducibility claim, and the pinned-profile feasibility/parity description.
Preserve all frozen/resolved findings and do not begin Lane D or Lane E.
