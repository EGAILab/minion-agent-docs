# L0506-D002 contract draft: prepared runtime JavaScript string domain (`TOOL-041`)

- **Coordination:** `minion-agent#99`.
- **Governance:** Owner decision `WP132-RUST-C001`, Option 1 (`minion-agent#49` comment `5924605017`); `standing_delegation: minion-agent#75`.
- **State:** SCOPING → CONTRACT_DRAFT → CONTRACT_REVIEW.
- **Characterization pass 1:** `l0506-d002-characterization.md` (186 cases), kept as history. This pass supersedes its harness with the authority below. All 180 shared cells agree.

## What this delivers

| Deliverable | Where |
|---|---|
| contract text | `spec/tools.md`, Layer 06, "Prepared runtime string domain (`TOOL-041`, post-certification delta `L0506-D002`)" |
| manifest | `minion-agent` `pi-parity-manifest.yaml` `TOOL-041`: surface, rule (D002 CONTRACT_DRAFT), tests, Python and Rust status |
| canonical witnesses | `minion-agent` `conformance/agent/prepared-runtime-string/`: 8 documents, 193 cases, shape `conformance/schema/prepared-string-scenario.schema.json` (own directory: the certified D001 runners are unaffected) |
| Python evidence | `tests/conformance/prepared_string_runner.py`, `test_prepared_string_conformance.py` (173), `test_prepared_string_edit_gate.py` (20), `tests/tools/test_prepared_string_negative_controls.py`, and schema tests in `test_schema_validation.py`. No production change |
| authority | `data/l0506-d002/` (see its `README.md`) |

## Cross-Language Feasibility Matrix (`process/templates/cross-language-feasibility-matrix.md`)

**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`. **Author:** Claude. **Independent checkpoint reviewer:** Codex.

### 1. Runtime value-domain matrix

| Observable value / field | Pi wire/source repr | Pi runtime repr | Python repr | Rust repr (certified today) | Canonical/wire serialization | Lossless across all? | Risk / witness |
|---|---|---|---|---|---|---|---|
| prepared string value (ASCII, BMP, valid pair) | JSON string (escaped or literal) | UTF-16 code units | `str` (pair = one astral code point) | `String` | `{"utf16": units}` | YES | 60 cells (3 members × 8 schemas) + 3 edit cases |
| prepared string with an unpaired surrogate (high/low × start/middle/end/only, adjacent, reversed, mixed) | escaped `\udXXX` (edit `JSON.parse`), or a shim | UTF-16 code units, lone units kept | `str` with surrogate code points (`surrogatepass`) | **cannot hold** (`String` is UTF-8) | `{"utf16": units}` | **NO (Rust): `WP132-RUST-C001`**, resolved by this delta's authorized extension | 112 cells + 14 edit cases; negative controls |
| empty string, NUL alone/inside | `""`, `\u0000` | 0 units / U+0000 | `str` | `String` | `{"utf16": []}`, `[0]` | YES | 24 cells + 3 edit cases |
| prepared object **key** with an unpaired surrogate or pair | `JSON.parse` key / shim key | UTF-16 code units | `str` key | `BTreeMap<String, _>` key: **cannot hold** | `{"$key": units, "value": v}` | **NO (Rust)**, same extension (keys share the domain) | `key/*` (5) + replacement-key case |
| string in a nested object / array element | as above | as above | as above | as above | pointer `/outer/inner`, `/list/1` | as rows above | 3 position cases |
| hook replacement value (Minion `Proceed(arguments=...)`) | n/a (Minion extension) | n/a | `str` | `String` | `hook_replace_set` | **NO (Rust)**, same extension | 4 replacement cases (contract expectations) |
| UTF-8 file bytes of a prepared string | n/a | `Buffer.from(s, "utf8")` | `encode_utf8` (certified WP-13.2) | WP-13.2 (pending) | `file_utf8_hex` | YES (projection; WP-13.2 gate) | 20 edit cases |
| Pi failure diagnostic | n/a | `JSON.stringify`: `\udXXX` escapes, pair literal, `\u0000` | own `TOOL-003` text | own `TOOL-003` text | not canonical (Pi text) | n/a (Minion text is its own; producing it must not fail) | `diagnostic/lone-surrogates` |
| **raw** `ToolCall.arguments` string with an unpaired surrogate | escaped `\udXXX` in provider JSON | UTF-16 (`JSON.parse`) | `str` | `serde_json::Value`: **cannot hold** | (raw domain) | **NO (Rust)**, outside D002 (decision §1) | `L0506-D002-Q001` (Owner) |
| key enumeration order | JSON object | ECMAScript order (index keys first) | insertion order | sorted (`BTreeMap`) | n/a | **NO (both)**, outside D002 | `L0206-D001` (`#100`, Owner decision K1) |

Template checklist: finite binary64 … NaN are `NOT_APPLICABLE` here (numbers are `L0506-D001`, certified). `undefined`/missing, `null` and `false`/empty are `NOT_APPLICABLE`: they are not strings, and the empty string is covered. Numeric-looking strings are `NOT_APPLICABLE`: a string is never coerced on this path, and D001's RC002 disclosure is unchanged. UTF-16 code units, valid pair and lone surrogate: `AUDITED` (rows above). Unicode normalization/version: `NOT_APPLICABLE`, since no normalization happens on this path; `pattern`'s `.` is code-point based, not version-dependent for these members.

### 2. Lower-layer capability matrix

| Required semantic operation | Owning lower layer | Existing certified seam/API | Expresses exact Pi semantics? | Python repr sufficient? | Rust repr sufficient? | New additive extension required? | Non-additive reopen required? |
|---|---|---|---|---|---|---|---|
| hold a UTF-16 string in the prepared value | 05 | `prepare_arguments` result (`TOOL-041` `PreparedValue`) | Python yes; Rust no | YES | **NO** | **YES:** a UTF-16-capable prepared string (authorized by the Owner decision) | NO |
| hold a UTF-16 object key in the prepared value | 05 | same | Python yes; Rust no | YES | **NO** | **YES:** the same extension for keys | NO |
| validate `type`/`minLength`/`maxLength`/`pattern`/`const`/`enum` over UTF-16 strings | 06 | Python `PreparedArgumentsValidator`; Rust `prepared_validation.rs` (a JSON Schema engine over `serde_json::Value` plus a numeric carrier) | Python yes (160/160 cells); Rust: the engine cannot see a lone surrogate | YES | **NO** | **YES:** a lossless string carrier, or code-unit-aware keyword evaluation (code-point length, Unicode-mode `pattern`, code-unit equality) | NO |
| hand the value to the pre-execute listener, a replacement, and execute | 06 | `execute_call` waterfall and execute seam | yes | YES | NO until the above lands | no further (rides on the representation) | NO |
| UTF-8 encode for file bytes | 12/13 (WP-13.2) | `encode_utf8` | yes | YES | WP-13.2 (pending) | NO | NO |
| decode an escaped lone surrogate in the edit `edits` string | 13 (WP-13.2) | the `edit` prepare `JSON.parse` | Python yes | YES | Rust: needs a `JSON.parse`-equivalent decoder yielding code units, since a `serde_json` string cannot carry a lone surrogate | inside WP-13.2 Rust (gate-WP-13.2 witness) | NO |

### 3. Cross-runtime hazard checklist

| Hazard | State | Evidence / reason |
|---|---|---|
| `JSON.parse` (number precision, duplicate keys, `__proto__`) | AUDITED | Escaped pairs combine and escaped lone surrogates stay (20 edit cases). Duplicate key: last value, first position (pass 1 S4, F6). `__proto__` becomes an own property (pass 1 S4) |
| `JSON.stringify` (non-finite, `-0`, `undefined`, key order) | AUDITED (strings) | Lone surrogates are escaped `\udXXX`, NUL `\u0000`, and a pair is literal (diagnostic case). Numbers belong to D001. Key order belongs to L0206-D001 |
| `Number` conversion / numeric coercion | NOT_APPLICABLE | Strings are never coerced on this path |
| `Math` semantics | NOT_APPLICABLE | No arithmetic on strings |
| negative zero | NOT_APPLICABLE | D001 |
| non-finite values | NOT_APPLICABLE | D001 |
| `String.length` / UTF-16 code units | AUDITED | The value is carried as code units. JSON Schema length counts code points (S2) |
| `RegExp` (`u` mode) | AUDITED | Pi compiles `pattern` in Unicode mode: `.` matches a pair as one character and a lone surrogate as one (`pattern-*` cells) |
| Unicode / ICU version | NOT_APPLICABLE | No normalization, case mapping or collation on this path |
| Array ordering | NOT_APPLICABLE | Arrays keep order in every binding (`position/array-element`) |
| Object property ordering | DEFERRED_WITH_REASON | `L0206-D001` (`#100`), by Owner decision K1. WP-13.2's independence witness is merged (`#101`) |
| Promise scheduling | NOT_APPLICABLE | No new await point |
| `AbortSignal` | NOT_APPLICABLE | Unchanged certified Layer-06/09 behavior |
| timers | NOT_APPLICABLE | None |
| Node/libuv error mapping | NOT_APPLICABLE | None on this path |
| filesystem access semantics | NOT_APPLICABLE | Only the WP-13.2-gated edit writes a file |
| platform paths | NOT_APPLICABLE | None |
| external package versions | AUDITED | Node 22.15.1, typebox 1.3.7 (SRI-checked), and Pi source hashes (`pi_sources.sha256`) |

### 4. Concurrency / order matrix

`NOT_APPLICABLE`: no async behavior is added; a value is carried through the existing certified seam.

### 5. Neighborhood expansion record

| Family | Members probed | Pi observation source | New rows / findings |
|---|---|---|---|
| F2 JS String / UTF-16 | All 20 Owner-decision members; positions (nested, array, two strings); keys (lone high, lone low, pair, reversed, empty); 8 schema kinds; observers (`beforeToolCall`, `execute`, `afterToolCall`, same object); projections (UTF-8, `JSON.stringify`); raw decoding (`parseStreamingJson`); provider-outbound `sanitizeSurrogates` | `authority.mjs` over sliced `agent-loop.ts`, `validation.ts` and `edit.ts`; source audit of `json-parse.ts`, `sanitize-unicode.ts`, providers | Key-domain rows; replacement row; `L0506-D002-Q001` (raw domain); F2 members added to `process/hazard-families.md` (`minion-agent-docs#204`) |
| F5 Error / coercion projection | Pi diagnostic serialization; `TOOL-003` producibility | `diagnostic/lone-surrogates` | Contract: producing the rejection MUST NOT fail for any string |
| F6 ECMAScript object order | Key enumeration of prepared objects | pass 1 K1 | Deferred to `L0206-D001` (Owner decision K1) |

### 6. Verdict

```text
FEASIBILITY
    READY for the L0506-D002 scope: every row AUDITED / NOT_APPLICABLE / DEFERRED_WITH_REASON.
    The Rust "NO" rows are WP132-RUST-C001 itself, resolved by the extension the Owner decision authorizes.
    Outside the scope, with owners: L0206-D001 (key order, #100) and L0506-D002-Q001 (raw domain, Owner question).
```

## Decisions made in the draft (for the independent review)

1. **Observers.**
   - Pinned Pi's `afterToolCall` also receives the prepared `args` (the same object). Minion's certified `tools/post-execute` carries no arguments, so no Minion observer exists there, and this delta does not add one.
   - The hook replacement (`Proceed(arguments=...)`) is Minion's extension. Its 4 cases carry contract expectations, labelled as such in the document's `authority`.
2. **Keys share the domain.** Pinned Pi's keys are JS strings with the same code-unit behavior. Excluding them would leave a Rust hole of the same root cause (§7 of the decision: characterize visible holes now).
3. **Diagnostic text stays each binding's own** (as `L0506-D001-R001`). The only new rule is that producing it cannot fail for any prepared string.
4. **Raw domain is not folded in** (`L0506-D002-Q001`). Decision §1 keeps "the raw/wire JSON domain unchanged". The characterization shows Pi's raw `ToolCall.arguments` can carry an unpaired surrogate (provider `JSON.parse`), Python's Layer 02 can, and Rust's `serde_json::Value` cannot. This is raised with the Owner, like K1. It does not block this delta: D002's gate uses custom shims and the WP-13.2 edit path, neither of which needs a raw lone surrogate.

## Reviewer checklist

1. Reproduce `data/l0506-d002/out/authority.json` and the scenario directory byte for byte (README).
2. Check the characterization: the 160 validation cells (especially code-point length, Unicode-mode `pattern` and code-unit `const`/`enum`), the same-object observation, the key cases, and the diagnostic.
3. Check the scope: the raw arguments, `tool_execution_*` arguments and serializations are unchanged; there is no whole-layer reopen; and D001 is untouched.
4. Check decisions 1–4 above, especially Q001's classification as outside the delta.
5. Check the negative-control list against the Owner decision §6, and that Python kills each (`test_prepared_string_negative_controls.py`).
6. Check Rust feasibility (§2): a lossless string and key representation, and code-unit-aware validation.

## Status

- `L0506-D002` contract: READY FOR INDEPENDENT CONTRACT REVIEW.
- Python: conforms with no production change (173 + 20 cases, negative controls), PENDING contract review.
- Rust: NOT_IMPLEMENTED.
- `WP-13.2` (#49) Rust stays blocked on this delta.
