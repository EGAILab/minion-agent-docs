# L05-D001: runtime-validation schema string domain (characterization, pass 1)

- **Coordination:** `minion-agent#104` (SCOPING).
- **Governance:** the Owner decision on `L0506-D002-R001`, Option 1 (`minion-agent#99` comment `5926416181`).
- **Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`.
- **Python measured at:** `minion-agent` main `365ea754`.

This is characterization evidence, not a contract.

## Method (`data/l05-d001-schema-domain/`)

`harness/schema_probe.mjs` runs pinned Pi's unmodified `validateToolArguments` (`typebox` 1.3.7, SRI-checked; `validation.ts` hash-checked) under `node:22.15.1-alpine`.
- **Cases** (`harness/make_cases.py`): 729, which is 9 schema-string roles × 9 schema members × 9 instance members. Strings are written as UTF-16 code units.
- **Members** (decision §4): ASCII, BMP, a valid pair, a lone high, a lone low, a pair followed by a lone high, U+FFFD (the discriminator), and the high and low halves of the pair on their own.
- **Roles** (decision §2, plus every other validator-consumed string slot found):

| Role | Schema | Instance |
|---|---|---|
| `properties-required` | `properties: {S: string}, required: [S]` | `{I: "x"}` |
| `additional-properties-false` | `properties: {S: string}, additionalProperties: false` | `{I: "x"}` |
| `const` | `properties: {t: {const: S}}` | `{t: I}` |
| `enum` | `properties: {t: {enum: [S]}}` | `{t: I}` |
| `pattern` | `pattern: "^" + S + "$"` | `{t: I}` |
| `pattern-unanchored` | `pattern: S` | `{t: I}` |
| `pattern-properties` | `patternProperties: {"^" + S + "$": number}` | `{I: "x"}` |
| `property-names-const` | `propertyNames: {const: S}` | `{I: 1}` |
| `dependent-required` | `dependentRequired: {S: ["a"]}` | `{I: 1}` |

**Python** (`harness/py_probe.py`): the same 729 cases go through the real Layer-06 `execute_call`. The schema is a raw JSON-Schema `ToolDefinition.parameters`; the instance is the raw arguments of a tool without `prepare_arguments`.

**Hashes (SHA-256):**
- `cases.json`: `3881e9b886ea91b8c51a3abc5bda04b5c951be9d0c5b9b63aa41eddd6a6c6ae6`
- `out/schema.json`: `de31477d1c0dbfc1cdf5a551d7c6a01dafb331405bc81c1a6a3b80dd9a1867d7`
- `out/python.json`: `a57e50e3ce07fb3ffb09760dc67cf9d4cfdc53b1030e16d0034fbb60b7659e85`

`harness/summary.py` prints each role's schema × instance matrix.

## Findings

**SD1. No schema-string role ever errors.** Every member, including lone surrogates and a mixed pair + lone, is accepted by Pi as a property name, `required` entry, `const`/`enum` literal, `pattern` source, `patternProperties` key, `propertyNames` constant or `dependentRequired` key. Pi tells a schema error apart from a validation failure, and none occurred.

**SD2. Name and equality roles are exact UTF-16 identity.** For `properties-required`, `additional-properties-false`, `const`, `enum`, `property-names-const` (and, inverted, `dependent-required`), the schema × instance matrix is the identity: S matches I exactly when they are the same code-unit sequence.
- A lone high never matches U+FFFD, a lone low, or the high half of a pair.
- The pair's halves never match the pair.

**SD3. `pattern` is a Unicode-mode RegExp, not code-unit equality** (decision §3).
- **Anchored** `^S$`: identity, as in SD2.
- **Unanchored** `S`, which is a search:
  - `pair` and `lone-high` match inside `pair-then-lone-high`. That instance contains the pair, then a genuinely unpaired high.
  - `pair-high-half` (`\uD83D`) does **not** match inside `pair` or inside `pair-then-lone-high`. In Unicode mode the pair is one code point, so its half is not a substring.
  - A code-unit search would match there, so this is the discriminating cell set for any binding.
- **`patternProperties`** is the anchored rule applied to keys. Inverted: a matching key's string value fails the `number` constraint.

**SD4. Python matches pinned Pi on all 729 cells**, Unicode-mode pattern search included, through the real validator path. Python's `dict` schema holds every member. No Python production change is indicated; permanent witnesses follow with the contract (decision §9).

**SD5. Rust (feasibility).** The certified `ToolDefinition.parameters` is `JsonSchemaObject(Map<String, serde_json::Value>)`, and `serde_json` cannot hold an unpaired surrogate as a key or a string value (Codex's `L0506-D002-R001` probe, serde_json 1.0.140). The lone-high, lone-low and mixed members, as schema strings, are unrepresentable in every role. The contract review decides the representation (decision §8). Whatever it is must also implement SD3's Unicode-mode pattern semantics over code units.

## Out of scope (decision §§2, 10)

- **Documentary fields** (`title`, `description`, `examples`) are not consumed by `validateToolArguments` for validation, so they are excluded. A pass-0 check found no certified observable for them on this path.
- **Provider/wire schema transport** stays with its owning surfaces. Pi's providers do not sanitize tool schemas, and `JSON.stringify` escapes an unpaired surrogate as `\udXXX`, but this delta does not certify it.
- **`default`:** not filled in by Pi's validator on this path (D002 Remediation-1 probe). No observable.

## WP-13.2 (decision §7)

Independent. The `write`/`edit` schemas are ASCII-named `Type.String` slots with no `const`, `enum` or `pattern` (recorded on #104 and in D002's Remediation 1).

## Next

- Draft the contract:
  - the schema value domain per role, SD2/SD3 semantics stated per role;
  - the runtime-validation schema authority (`ToolDefinition.parameters` as validation consumes it), distinct from provider/wire schema authority;
  - canonical cases generated from this probe, keeping the discriminating `pattern-unanchored` cells;
  - Python witnesses and negative controls:
    - a lone schema literal rejected at registration;
    - one replaced with U+FFFD;
    - a code-unit (non-Unicode) pattern search;
    - property-name normalization.
- Feasibility matrix with the four domains, then Codex contract review.

## Pass 1 addendum: unanchored `patternProperties` (`L05-D001-R001`) and key capture

- **New role.** `pattern-properties-unanchored` (`patternProperties: {S: number}`, instance `{I: "x"}`) is 81 cells, for 810 in all.
  - Pinned Pi treats the key as a Unicode-mode RegExp **search**. Neither `pair-high-half` nor `pair-low-half` matches a key holding the pair (accept).
  - `lone-high` matches inside `pair-then-lone-high`, where it is genuinely unpaired (reject: the guard).
  - Python matches pinned Pi on all 810 cells.
- **Key capture fixed.** `schema_probe.mjs` used `Array.from(k, …)`, which iterates code points, so astral keys lost code units. It now uses `Array.from({length: k.length}, …)`. That field is auxiliary: no verdict or canonical expectation consumes it.
- **History.** The earlier authority output (`out/schema.json` `de31477d…`, 729 results) is preserved in this branch's history at `17b15015`.
- **Hashes (SHA-256):**
  - `cases.json`: `602bdb06e3a86e30fb759c5edb707e5770121b3c77aaf7c42728d01bee431c1f`
  - `out/schema.json`: `ad7976793de2e9f508e53b0e16e06d15be149fc9a8d895965761b84e1d0cf244`
  - `out/python.json`: `74bb907803ec3a04d5c2b4bec41ca99b60fb89d439f1807ea7b7cbdacf545f2c`
