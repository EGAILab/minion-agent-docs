# Minion Agent — Reusable runtime hazard families

**Referenced by:** `process/agent-workflow.md` §4.1.1, §9.4, §9.5; `process/templates/cross-language-feasibility-matrix.md`.

A **hazard family** is a recurring language/runtime behavior class whose members must be probed together. Every family here was paid for with a late finding (source column).

**Rules.**
- **When a WP's semantic path touches a family**, the feasibility matrix (§4.1.1) lists every member as a probe point. Each member is characterized against pinned Pi and recorded `AUDITED`, `NOT_APPLICABLE` (with reason) or `DEFERRED_WITH_REASON`.
- **When a review finding hits one member**, the neighborhood-expansion rule (§9.4) requires the whole family to be characterized before remediation is proposed.
- **When a new hazard class is discovered** and is generalizable, add it here as part of that finding's remediation. Add a new member to an existing family, or a new family.
  - *Generalizable* means another WP could plausibly reach the same runtime behavior.
  - The addition is a process change, and it is reviewed with the finding.
- **Families are characterization inputs, not semantic authority.** Pinned Pi remains the source, and the spec/conformance remain the contract (`agent-workflow.md` §3, §9.3).

**Reusable probes.** Where a family has an executable pinned-Pi harness, it lives under `reference/pi-characterization/families/<family>/` (non-normative, §9.3), with a member-per-case layout that a WP-specific probe can import. Until a family harness exists, the WP's own characterization harness enumerates the members from this file.

---

## F1. JS Number

**Source:** WP-13.2 I002 (JSON number beyond binary64), I002-refinement (`-0`), I004 (runtime ±Infinity); L0506-D001 C001, I002 (numeric-looking string).

| Member | Probe |
|---|---|
| normal finite | a representative value survives each boundary unchanged |
| integer ≤ 2^53 | exact |
| 2^53 boundary | 2^53, 2^53+1 (rounds), −2^53 |
| large finite | 1e308, `Number.MAX_VALUE` |
| overflow → +Infinity | `1e309` through `JSON.parse` / arithmetic |
| overflow → −Infinity | `-1e309` |
| +0 | stays `0` |
| −0 | sign preserved at runtime; `JSON.stringify(-0) === "0"` |
| NaN | reachable at this boundary? (only via shim/arithmetic, never via JSON) |
| numeric-looking string | `"Infinity"`, `"NaN"`, `"1"`: never silently a number unless Pi coerces |
| JSON.stringify projection | non-finite → `null`, `-0` → `0`; a diagnostic projection is not a runtime value |
| declared integer vs number | non-finite and fractional in an `integer` position |

## F2. JS String / UTF-16

**Source:** WP-13.2 I003 (valid surrogate pair held as two characters); WP-13.1 read projection.

| Member | Probe |
|---|---|
| ASCII | baseline |
| BMP non-ASCII | e.g. `é`, `中` |
| astral scalar | e.g. `😀` (2 code units, 1 scalar) |
| explicit surrogate pair | `"\uD83D\uDE00"` built from escapes |
| lone high surrogate | `"\uD83D"` |
| lone low surrogate | `"\uDE00"` |
| length / index / slice units | `String.length`, offsets, `slice`, diff hunks in UTF-16 code units |
| encoding / replacement | UTF-8 encode of lone surrogates (→ U+FFFD), decode of invalid bytes |

## F3. Unicode / ICU

**Source:** WP-13.1 R006 (`ls` collation, 5 revisions), R006-C (pinned ICU profile), FR003 (profile not enforced).

| Member | Probe |
|---|---|
| pinned runtime Unicode / ICU version | the version Pi's Node embeds vs Python/Rust; pinned build identity |
| normalization version drift | NFC/NFD of characters whose composition changed across versions |
| case mapping | locale-sensitive (`İ`, `ß`), `toLowerCase` vs `toLocaleLowerCase` |
| collation | locale, strength, numeric option, ties; `localeCompare` vs byte order |
| characters newer than the pinned version | unassigned in the pinned version, assigned in the host's |

## F4. Async / order

**Source:** WP-13.2 I001 (settle window instead of firing timers; queue witness weakness); Layers 08/09 listener ordering.

| Member | Probe |
|---|---|
| abort before work | already-aborted signal at entry |
| abort during await | abort while suspended at each await point |
| work settles before abort | completion wins |
| error settles before abort | failure wins; which error is observed |
| queue waiter | second operation waits on the first (same key) |
| prior operation fails | waiter proceeds; no per-key residue |
| prior operation aborts | waiter proceeds; ordering preserved |
| timer beyond naive polling interval | completion scheduled later than any fixed settle window (fire timers, don't wait them out) |
| microtask vs macrotask | continuation ordering relative to listeners |

## F5. Error / coercion projection

**Source:** L0506-D001 R001 (diagnostic serialization), I001/C002 (union/callback coercion), I002 (numeric-looking string → `finite_number`); WP-12.E3 C001; WP-13.1 R010 (error projection).

| Member | Probe |
|---|---|
| fixed Pi-authored template | exact text from Pi source |
| raw provider / host text | passed through unchanged vs templated |
| hybrid template + provider text | composition order and separators |
| same Minion error code from multiple sources | every host/runtime condition that yields the code; can a *coercion* produce it from a non-matching value? |
| platform-specific host result | Windows vs POSIX errno/messages |
| coercion vs original value | does a check judge the delivered value or a coerced copy? |
| union / alternative selection | complete-value alternatives in both orders; a mismatched sibling must not exempt another position |
| callback / hook output | values produced after validation (after-validators, hooks) are judged as delivered |
