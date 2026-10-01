# L0206-D002 contract draft: raw `ToolCall.arguments` JavaScript value domain (`AI-003`)

- **Coordination:** `minion-agent#103`.
- **Governance:** Owner decision `L0506-D002-Q001`, Option 1 (`minion-agent#99` comment `5926162818`); `standing_delegation: minion-agent#75`.
- **State:** SCOPING → CONTRACT_DRAFT → CONTRACT_REVIEW.
- **Characterization:** `l0206-d002-characterization.md` (pass 1, 39 cases, Pi and Python).

## What this delivers

| Deliverable | Where |
|---|---|
| contract text | `spec/llm.md`, "Raw tool-call argument value domain (`AI-003`, cross-layer delta `L0206-D002`)". Also `spec/session.md` (event data domain) and a correction note on `spec/tools.md`'s L0506-D001 "two domains" line |
| manifest | `minion-agent` `pi-parity-manifest.yaml` `AI-003` (rule, tests, Python, Rust) and `MINION-002` (log domain). `TOOL-041`'s raw-domain sentence is corrected only after `L0506-D002` merges, to avoid concurrent edits of one row (`agent-workflow.md` §11.15) |
| canonical witnesses | `minion-agent` `conformance/agent/raw-arguments/`: 3 JSON documents, 33 cases, shape `raw-arguments-scenario.schema.json` |
| Python evidence | `tests/conformance/raw_arguments_runner.py`, `test_raw_arguments_conformance.py` (33), `tests/session/test_raw_arguments_negative_controls.py` (decision §11), schema tests. No production change |
| authority | `data/l0206-raw-boundaries/` (`harness/make_scenarios.py` generates the scenarios) |

## Cross-Language Feasibility Matrix (`process/templates/cross-language-feasibility-matrix.md`)

**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`. **Author:** Claude. **Independent checkpoint reviewer:** Codex.

### 1. Runtime value-domain matrix

| Observable value / field | Pi wire/source | Pi runtime | Python | Rust (certified) | Canonical | Lossless across all? | Witness |
|---|---|---|---|---|---|---|---|
| raw string leaf, scalar (ASCII, BMP, pair) | JSON text | UTF-16 code units | `str` | `serde_json` string | `{"utf16": units}` | YES | 5 cases |
| raw string leaf with an unpaired surrogate (any position, adjacent, reversed, mixed) | escaped `\udXXX` | UTF-16, lone kept | `str` (surrogate code points) | **cannot hold** | `{"utf16": units}` | **NO (Rust): Q001** | 14 cases + nested + array |
| raw string empty / NUL | `""`, `\u0000` | as given | `str` | `String` | units | YES | 3 cases |
| raw object key with an unpaired surrogate | escaped key | UTF-16 key | `str` key | **cannot hold** | `{"$keys": …}` | **NO (Rust)** | `keys/surrogate-keys` |
| raw number `-0` (also from `-1e-400`) | `-0` | `-0` | `float -0.0` | `f64 -0.0`, if the number path keeps it (to verify) | `{"number": "-0"}` | Python YES; Rust TO VERIFY | 2 cases |
| raw number ±Infinity (overflow literal) | `1e999`, 400 digits | ±Infinity | `float ±inf` | **cannot hold** | `{"number": "+Infinity"}` | **NO (Rust)** | 3 cases |
| raw number binary64 rounding | `9007199254740993` | `9007199254740992` | `int` (value as decoded) | `serde_json` number | token | YES for the decoded value; decoder requirement below | 1 case |
| raw key enumeration order | JSON object | ECMAScript order | insertion order | sorted | not asserted | NO (both) | **`L0206-D001`** (#100), outside this delta |
| Pi persisted session line | — | `JSON.stringify`: `-0`→`0`, ±Inf→`null`, lone→`\udXXX` | no persisted byte form (Layer 03 is in memory) | none | n/a | N/A at certified layers | characterized (R-N2/R-N3) |

**Four value domains** (template §1.1):

| Domain | Status |
|---|---|
| INSTANCE | prepared values are `L0506-D002`; the raw instance is this delta |
| SCHEMA | `L05-D001`; here only the open schema `{type: object, properties: {}}` is used, which is scalar |
| RAW/WIRE | this delta; the decoder requirement R-N4 is stated |
| SERIALIZED/PROJECTED | Pi's persisted JSON line is characterized (no Minion counterpart yet); provider-outbound (`sanitizeSurrogates`) is Layer 11's |

### 2. Lower-layer capability matrix

| Operation | Layer | Certified seam | Exact Pi semantics? | Python | Rust | Additive extension? | Non-additive reopen? |
|---|---|---|---|---|---|---|---|
| construct a `ToolCall`/`AssistantMessage` holding the domain | 02 | `ToolCallBlock.arguments: dict` / `llm/vocabulary.rs` | Python yes | YES | **NO** | **YES:** a raw runtime value type (decision §7) | NO |
| session append + replay | 03 | `SessionLog.append` + `encode_message`/`decode_message` | Python yes | YES | **NO** (event data is `serde_json`) | **YES:** the same value type in event data | NO |
| `tool_execution_start`/`_update` payload | 06 | event emission | Python yes | YES | NO until the above lands | rides on the above | NO |
| Layer-06 input, no `prepare_arguments` | 06 | `execute_call` | Python yes | YES | NO until the above lands | rides on the above (meets L0506-D002's prepared type) | NO |
| raw decoder (provider text → value) | 11 (future) | none certified | — | `json.loads` is **not** `JSON.parse`-equivalent (2^53+1, `-0`, overflow) | — | the R-N4 requirement on Layer 11 | NO |

### 3. Cross-runtime hazard checklist

| Hazard | State | Evidence / reason |
|---|---|---|
| `JSON.parse` | AUDITED | strings, numbers, keys, duplicates (last value, first position), `__proto__` own property |
| `JSON.stringify` | AUDITED | the persisted-line projection (R-N2); not a Minion boundary today |
| `Number` conversion | AUDITED | binary64 rounding, `-0`, overflow, underflow |
| `Math` semantics | NOT_APPLICABLE | none on this path |
| negative zero | AUDITED | live `-0` through every Pi boundary; Python carries it |
| non-finite values | AUDITED | live ±Infinity; Python carries it; Rust cannot |
| `String.length` / UTF-16 | AUDITED | code units at every boundary |
| `RegExp` | NOT_APPLICABLE | the open schema has no `pattern` |
| Unicode / ICU | NOT_APPLICABLE | no normalization on this path |
| array ordering | AUDITED | array string case keeps order |
| object property ordering | DEFERRED_WITH_REASON | `L0206-D001` (#100), by Owner decision K1 |
| Promise scheduling, `AbortSignal`, timers | NOT_APPLICABLE | unchanged certified behavior |
| Node errors, filesystem, paths | NOT_APPLICABLE | none |
| package versions | AUDITED | Node 22.15.1, typebox 1.3.7 (SRI), `pi_sources.sha256` |

### 4. Concurrency / order

`NOT_APPLICABLE`: no new async behavior.

### 5. Neighborhood expansion record

| Family | Members probed | Source | Rows / findings |
|---|---|---|---|
| F2 String/UTF-16 | the decision §6 list: 19 members, nested, array, literal pair | `raw_probe.mjs` | string rows |
| F1 Number | large finite, 2^53+1, `-0`, 0, ±overflow, 400 digits, ±underflow, subnormal | `raw_probe.mjs` | number rows; numbers folded in (characterization scope decision) |
| F6 Object order | the K1 neighborhood | `raw_probe.mjs` | deferred to `L0206-D001` |
| F7 Schema domain | the open schema only | — | `L05-D001` owns the schema domain |

### 6. Verdict

```text
FEASIBILITY
    READY for the L0206-D002 scope: every row AUDITED / NOT_APPLICABLE / DEFERRED_WITH_REASON.
    The Rust "NO" rows are Q001 itself, resolved by the raw runtime value type the Owner decision authorizes (§7).
    Rust -0 handling is flagged TO VERIFY for the contract review.
    Outside the scope, with owners: L0206-D001 (key order), L05-D001 (schema domain), Layer 11 (decoder, R-N4).
```

## Decisions made in the draft (for the independent review)

1. **Numbers are folded in.** Raw ±Infinity and `-0` share the root, the boundaries and the Rust type with the strings (characterization, scope decision). This is flagged for Owner override.
2. **Persisted form is N/A at the certified layers.** Minion's Layer-03 log is in memory and replays the live value. Pi's persisted-line projection is characterized for whichever layer later maps `session-manager.ts`.
3. **The decoder is a requirement, not a seam.** There is no certified Minion raw decoder. R-N4 binds the first one, Layer 11. `provider_text` is carried in each case as evidence.
4. **The event payload is observed by value.** Pi hands the hook a `structuredClone` (`validateToolArguments`), so object identity is not part of the contract.
5. **`TOOL-041`'s raw sentence is corrected later.** `spec/tools.md` gets a correction note now. The `TOOL-041` manifest row is edited after `L0506-D002` merges, since that delta is editing the row.

## Reviewer checklist

1. Reproduce `data/l0206-raw-boundaries/out/raw.json` and the scenario directory (README-equivalent commands in `harness/`).
2. Check every boundary in the decision §4 table, and the N/A reasons.
3. Check decisions 1-5, especially the numeric fold-in and the persisted-form N/A.
4. Check the §11 negative controls kill their mutants (`test_raw_arguments_negative_controls.py`).
5. Check Rust feasibility: a raw runtime value type for `ToolCall.arguments`, session event data and event payloads; `-0` handling.

## Status

- `L0206-D002` contract: READY FOR INDEPENDENT CONTRACT REVIEW.
- Python: conforms with no production change (33 cases, all six boundaries; §11 negative controls), PENDING contract review.
- Rust: NOT_IMPLEMENTED.
- WP-13.2: non-blocking (characterization §10 check).

## Remediation 1: `L0206-D002-R001`, `L0206-D002-R002`

**Trigger.** Codex's independent contract review (`minion-agent-docs#210` comment `5926939115`) REJECTED the draft with two evidence findings. Both are accepted.
- Codex accepted draft decisions 1-5, including the numeric fold-in and the persisted-form N/A.
- Codex verified Rust `-0` offline: `serde_json` 1.0.140 parses `-0`, `-0.0` and `-1e-400` as negative zero, and rejects `1e999`.
- Codex flagged that `#103` recorded `requirements: []`. It is corrected to `[AI-003, MINION-002]`.

### `L0206-D002-R001`: the update boundary had no evidence

**The defect.** The contract named `tool_execution_update` arguments, but no case emitted an update. Codex instrumented the real emitter: 33 passes and zero `tools/update` emissions.

**The fix.**
- **Authority.** The Pi probe's tool now calls `onUpdate` once. Pinned Pi emits exactly one `tool_execution_update` per case, and its `args` is the raw object (characterization addendum; `raw.json` sha256 `101981da…`).
- **Runner.** The canonical tool's `execute` takes Minion's `update` callback and reports one `ToolPartialResult`. The runner observes:
  - the `tools/update` payload;
  - the `on_execution_update` delivery passed to `execute_call`.

  Each must hold exactly one observation, equal to the raw value. `tool_execution_end` stays N/A.
- **Negative controls.** Two single-point source mutants normalize the raw argument at **one** update seam only: the `tools/update` emission, and the `on_execution_update` delivery. In each, construction, replay, start, hook and execute stay correct, and the case fails only on that update observation.

### `L0206-D002-R002`: the numeric fixture grammar was lossy

**The defect.** The schema admitted `9007199254740993`, which the Python decoder delivered unrounded while observation rounded it away. It admitted `1e999` as a "finite" token, and `NaN`, which is outside the raw domain.

**The fix.**
- **Schema.** A number token is either a NAMED `+Infinity`, `-Infinity` or `-0`, or a finite literal. `NaN` is removed.
- **Preflight.** A language-neutral PREFLIGHT, run before dispatch and failing the document, requires a finite literal to denote a finite binary64 value **and** be exactly its ECMAScript `Number::toString`.
- **Observation** is strict: an integer that is not exactly a binary64 value renders as `non_binary64_int`, never through a float.
- **Witnesses:**
  - the preflight refuses `9007199254740993`, `±1e999`, `NaN`, `-0.0`, `1.0`, `1E3` and `0.1000`;
  - the preflight accepts the canonical `0`, `9007199254740992`, `1.7976931348623157e+308`, `5e-324`, `0.1`, `-1.5` and `1e+21`;
  - the schema refuses `NaN`, `Infinity`, `1garbage`, `+1` and `01`;
  - strict observation tells `9007199254740993` from `9007199254740992`;
  - real hook-value witness: a pipeline delivering the unrounded integer fails `number/integer-2p53-plus-1`.
- All 33 generated cases already used canonical tokens and are unchanged.

**Gates:** 2554 passed, 17 skipped, 19 xfailed; 100% coverage; ruff and mypy clean.

**Status:** R001 and R002 are REMEDIATED, pending targeted re-review.

---

## Convergence episode `CE-L0206-D002-01` (R002 numeric fixture domain)

**Trigger check (§11.8).**
- **Trigger A HAS fired:** `L0206-D002-R002` survived two independent reviews: CONTRACT1, docs #210 comment `5926939115`, and CONTRACT2, comment `5927166786`.
- **Trigger B:** no other finding on this surface.
- **Trigger C:** two complete-or-targeted rejections, not three.
- So the episode is entered, with no ordinary point-fix pass. R001 stays provisionally closed (CONTRACT2).

**Characterization** (§11.8.3): Codex's seed matrix in CONTRACT2. **Challenge pass** (§11.8.4, this author), independently re-executed:

| Probe | Node 22.15.1 (`JSON.parse`, `String`, `BigInt`) | Python (`float`, `number_to_string`, `int(float)`) |
|---|---|---|
| `1000000000000000100` | value `1000000000000000128`; prints `1000000000000000100` | same; `int(token)` would give `…100` (the defect) |
| `-1000000000000000100` | `-1000000000000000128`; prints the token | same |
| `1000000000000000000` | exact | exact |
| `1e21` | prints `1e+21`; integral `10^21` | — |
| `9007199254740993` | `9007199254740992` | same |
| integer `2^1024 - 2^970` and above | — | `float()` raises `OverflowError` |
| integer `2^1024 - 2^970 - 1` | — | rounds to `1.7976931348623157e+308` and is **not** exactly representable |

**Challenge answers.**
- **Pi mapping:** correct. The raw value is `JSON.parse`'s binary64. `Number::toString` prints the shortest round-trip decimal, not the exact integer.
- **Mechanics vs semantics:** the defect is in fixture decoding and observation (shared evidence), not in a Minion production seam. No lower layer reopens.
- **Both languages:**
  - Rust's `f64::from_str` is correctly rounded, and serde's `f64` path likewise, so a Rust fixture decoder that parses to `f64` already denotes the right value.
  - Python must not use `int(token)`.
  - The rules below are language-neutral.
- **One-language-only cost?** The hazard is Python's arbitrary-precision `int` meeting decimal spelling. Rust needs only the language-neutral rules, not a fix.

### Proposed rules (N1–N5)

- **N1 (value).** A finite literal denotes **binary64(literal)**, the correctly rounded (round-half-even) parse. That is `JSON.parse`'s value, which for a canonical literal is the value whose `Number::toString` the literal is. Named tokens denote ±Infinity and −0.
- **N2 (binding representation of a fixture).** A binding decodes a finite literal **through binary64**.
  - Python: `f = float(literal)`. The value is `int(f)` when the literal is spelled without `.`/`e`/`E` (D001's integral-integer representation, now of the **exact binary64 integer**); otherwise it is `f`.
  - The spelled decimal digits are never used as an integer.
- **N3 (total, strict observation).** A runtime number observes as `{"number": Number::toString(binary64)}` exactly when it **is** a binary64 value. That covers a float, which is finite or a named value, and an int whose float conversion succeeds without `OverflowError` and converts back to the same integer. Every other int observes as a controlled `{"non_binary64_int": decimal}`, with no exception, at, below or above the overflow boundary.
- **N4 (independent expectation).** A case's expected observation is computed **from the scenario text**, not through the fixture decoder. A number leaf's expectation is its token itself (canonical by the preflight); a string leaf's is its code units. A `non_binary64_int` marker can therefore never satisfy a valid number fixture.
- **N5 (preflight, unchanged from R002).** A finite literal must be canonical: finite, and equal to `Number::toString` of its binary64 value. A named token is `+Infinity`, `-Infinity` or `-0`. There is no `NaN`.

### Behavior matrix → acceptance witnesses (seed rows, each permanent)

| Row | Witness |
|---|---|
| exact integer-looking `10^18` | new canonical case (Pi authority): hook/execute/update values equal the token |
| non-exact integer-looking `±1000000000000000100` | new canonical cases (Pi authority: decode = `±…128`): every boundary observes the token. The **old decoder mutant** (`int(token)`) fails them |
| integral exponential `1e+21` | new canonical case |
| fractional, subnormal, max finite | existing `5e-324` and `1.7976931348623157e+308`; new `0.1` |
| named | existing ±Infinity and −0; `NaN` refused (schema) |
| noncanonical / out of domain | existing refusals (`9007199254740993`, `1e999`, `NaN`, alternate spellings) |
| malformed runtime int at an observer | unit witnesses: `9007199254740993`, `1000000000000000100`, `2^1024-2^970-1`, `2^1024-2^970`, `2^1024`, `2^1024+1` all observe as `non_binary64_int`, with no exception; `1000000000000000128` and `2^53` observe as numbers |
| independent expectation | a **decoder mutant** (`int(token)`) and an **observer mutant** (rendering via `float`) each fail the `±1000000000000000100` / `integer-2p53` cases |
| real observers | the wrong value at **one** seam is killed for numbers too: an existing-style single-seam mutant (hook, execute, start, update event, update delivery) delivering `1000000000000000100` where the case expects `…128` |

**Normative deltas.**
- `spec/llm.md`: the number-token sentence gains N1–N4.
- `raw-arguments-scenario.schema.json`: `$defs.token` comment gains N1–N4.
- The runner: N2–N4.
- The Pi probe: add `1000000000000000000`, `±1000000000000000100`, `1e21` and `0.1`, regenerating the number document (10 → 15 cases).
- No production code. No manifest semantic change, only counts.

```text
CONVERGENCE CHECKPOINT
    PROPOSED FOR IMPLEMENTATION

OPEN FINDINGS
    L0206-D002-R002

ROOT ABSTRACTION
    a number fixture names a binary64 VALUE: decode through binary64 (N1/N2), observe strictly and totally (N3),
    expect from the scenario text, never through the decoder (N4); preflight unchanged (N5)

ACCEPTANCE WITNESSES
    the behavior matrix above: 5 new Pi-authority canonical cases; observer totality units; decoder and observer
    mutants; single-seam number mutants

NORMATIVE DELTAS
    spec/llm.md number-token rule; raw-arguments-scenario.schema.json $defs.token; raw_arguments_runner.py; Pi probe

NEXT_OWNER
    Codex (checkpoint review; no implementation before APPROVED)
```

### Checkpoint revision 2: response to C-L0206-D002-01-01 / -02 (Codex, REJECTED revision 1)

- **Review:** docs #210 comment `5927266982`, published verbatim.
- **Accepted:** both findings.
- **Unchanged:** N1, N2, N4 and N5, the scope, and R001's provisional closure.

**C-01: a second observer exception boundary.**
- Python limits int ↔ decimal-string conversion to 4300 digits by default, so `str(±10**4300)` raises `ValueError`, independently of the float-overflow boundary at `2^1024 - 2^970`.
- Re-probed (Python 3.13.5): `str(10**4299)` succeeds; `str(10**4300)`, `str(-(10**4300))` and `str(10**5000)` raise; `hex()` succeeds on all of them. Power-of-two bases are not subject to the digit limit.

**N3′ (replacing N3).** A runtime number observes as `{"number": Number::toString(binary64)}` exactly when it **is** a binary64 value. That means a float (finite or named), or an int whose float conversion succeeds and converts back to the same integer.
- Every other int observes as `{"non_binary64_int": hex(value)}`: signed hexadecimal, `-0x…` for negatives.
- The observer is non-throwing for every int. It catches the float conversion's `OverflowError`, and it never converts an invalid int to a decimal string.
- No process-wide setting (`sys.set_int_max_str_digits`) is touched.
- Two exception boundaries are witnessed independently:
  - float overflow: `2^1024 - 2^970 - 1`, `2^1024 - 2^970`, `2^1024`, `2^1024 + 1`;
  - decimal-digit limit: `±10**4299` and `±10**4300` (both signs), and `10**5000`.

  Each observes as the hex marker without raising, and `±1000000000000000128`, `2^53` and `1e18` observe as numbers.
- Rust has no digit limit and needs no counterpart. The language-neutral rule is "total, controlled marker for an out-of-domain integer"; the hex spelling is Python's own.

**C-02: what kills each mutant.** This table replaces the revision-1 "independent expectation" row:

| Mutant | Killed by | Not claimed |
|---|---|---|
| **decoder** `int(token)` (spelled digits); observer correct; expectation independent (N4) | the new canonical cases `number/±1000000000000000100`: the strict observer sees `…100`, which is not a binary64 value, and reports the hex marker ≠ the expected token | not killed by `number/integer-2p53-plus-1`, whose token `9007199254740992` is exact |
| **observer** coercing ints through `float()` (lossy) | direct unit witnesses: the observer applied to `1000000000000000100`, `-1000000000000000100` and `9007199254740993` must yield `non_binary64_int`. The lossy observer yields the number token instead, so those units go RED | not killed by any correct canonical run: with a correct decoder the delivered value is the exact binary64 int, and both observers agree |
| **wrong value at one seam** (hook, execute, start, update event, update delivery, replay), delivering `1000000000000000100` where `…128` is due | the strict runner refuses each: the case fails at that seam's observation | — |
| **the lossy observer defeats the seam refusal** (demonstration) | a permanent witness runs the hook-seam wrong-value mutant twice: with the strict observer the case fails; with the lossy observer monkeypatched in, it passes. The witness asserts both, recording that the strict observer is what refuses the wrong value | — |

```text
CONVERGENCE CHECKPOINT
    PROPOSED FOR IMPLEMENTATION (revision 2)

OPEN FINDINGS
    L0206-D002-R002

ROOT ABSTRACTION
    unchanged N1/N2/N4/N5; N3' total strict observation (hex marker, both exception boundaries)

ACCEPTANCE WITNESSES
    5 new Pi-authority canonical cases; N3' totality units at the float-overflow and decimal-digit boundaries (both
    signs); the C-02 mutant table (decoder -> canonical +/-1000000000000000100; lossy observer -> direct units;
    single-seam wrong values -> strict runner; lossy-observer demonstration)

NORMATIVE DELTAS
    spec/llm.md number-token rule; raw-arguments-scenario.schema.json $defs.token; raw_arguments_runner.py; Pi probe

NEXT_OWNER
    Codex (checkpoint review; no implementation before APPROVED)
```

### Implementation of checkpoint revision 2 (after AGREED FOR IMPLEMENTATION, Codex `#210` comment `5929956207`)

- **Authority.** 5 new Pi number cases (characterization addendum 2). The number document grows from 10 to 15 cases, 38 in all.
- **Runner** (`raw_arguments_runner.py`):
  - **N2:** `number()` decodes through `float(token)`, and an integral spelling becomes `int(float(token))`.
  - **N3':** `observe()` uses `is_binary64_int`. The float conversion's `OverflowError` is caught, and the marker is `{"non_binary64_int": hex(v)}`. Hex is exempt from the digit limit, and no process-wide setting is touched.
  - **N4:** `check()` compares against `expect(case["arguments"])`, which is computed from the scenario text.
- **Witnesses** (`tests/session/test_raw_arguments_negative_controls.py`):
  - **Totality:** 12 out-of-domain ints, covering both signs at the float-overflow midpoint and the 4300-digit boundaries, and `10**5000`. Each yields the hex marker without raising, and the digit limit is unchanged.
  - **Exact ints:** 4 exact binary64 ints render as their tokens.
  - **Decoder mutant** (`int(token)`): killed by the canonical `number/±1000000000000000100` cases, and GREEN without the mutant.
  - **Lossy observer:** killed by direct units on `±1000000000000000100` and `9007199254740993`.
  - **Single-seam wrong values:** `1000000000000000100` delivered where `…128` is due, at the hook, execute, start, update event, update delivery and replay. Each is refused by the strict runner, and the seam's own observation differs.
  - **Demonstration:** the hook-seam wrong value is refused with the strict observer and accepted with the lossy observer monkeypatched in.
  - The earlier R002 witnesses (preflight, schema, the `2^53+1` hook) remain.
- **Status:** R002 is REMEDIATED against the revision-2 agreement, pending §11.8.7 targeted closure. R001 stays provisionally closed.
