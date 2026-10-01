# L0506-D002: prepared JavaScript string domain (characterization, pass 1)

- **Coordination:** `minion-agent#99` (SCOPING).
- **Governance:** the Owner decision on WP132-RUST-C001, Option 1 (`minion-agent#49` comment `5924605017`).
- **Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`.

This is characterization evidence, not a contract. No candidate exists yet.

## Method

`data/l0506-d002-characterization/` is pinned Pi's unmodified `validateToolArguments` (`typebox` 1.3.7, SRI-checked) and `edit.ts` `prepareEditArguments`, extracted verbatim from the source with only the erased TypeScript annotations stripped. It runs under `node:22.15.1-alpine`, with source hashes checked by `pi_sources.sha256`.

- **Encoding.** Strings travel in `cases.json` as arrays of UTF-16 code units, so lone surrogates survive the case file.
- **Size.** 186 cases: 20 string-neighborhood members × 8 schemas through a custom `prepareArguments` shim, the same 20 through the real `edit` inner `JSON.parse`, and 6 object-key cases.
- **Observations per case:**
  - the verdict;
  - the prepared value's code units, as handed to the hook and `execute`;
  - **separately**, the two projection boundaries: `JSON.stringify` (Pi's failure diagnostic and any JSON serialization) and UTF-8 bytes (`Buffer.from(s, "utf8")`, which is what `edit.ts`' `fs.writeFile(path, s, "utf-8")` does).

**Hashes (SHA-256):**
- `cases.json`: `5dfb3e01592588d166fd6fa452a3371999fa2dafc9112378bbc0aa4f8b4e411b`
- `out/pi.json`: `368888b39ef662ce52c5a1cc9e356570db2e7348c8e6a2e5a0160dd565a5b854`

**Neighborhood** (Owner decision §2): ASCII, BMP, a valid pair, lone high (start/middle/end/only), lone low (start/middle/end/only), adjacent highs, adjacent lows, high followed by a non-low, low followed by high, a pair followed by a lone high, a lone low followed by a pair, the empty string, NUL, and NUL in the middle.

**Schemas:** undeclared, `{type: string}`, `minLength: 2`, `maxLength: 1`, `pattern: "^.$"`, `pattern: "^..$"`, `const` (a surrogate pair), `enum` (a lone high).

## Findings

### S1: the prepared value is the exact UTF-16 code-unit sequence

All 20 members keep their exact code units, through both the shim path and the real `edit` path. No member is normalized, replaced or rejected at preparation. Every member validates as `{type: string}`.

### S2: string keywords count code points; `pattern` is Unicode-mode

- **Length.** `minLength` / `maxLength` count **code points**: a valid surrogate pair counts as 1, and each lone surrogate counts as 1. For example, the pair passes `maxLength: 1`, and adjacent highs fail it.
- **Pattern.** `pattern` is Unicode-mode: `.` matches a pair as one character, and a lone surrogate as one.
- **Equality.** `const` / `enum` compare exact code units: the pair matches only the pair, and the lone high only the lone high.

### S3: projection boundaries are separate from the prepared value

- **UTF-8** (filesystem, `edit.ts` write path): each lone surrogate code unit becomes `EF BF BD`. Adjacent highs give two replacements, and low-then-high gives two. A valid pair becomes its 4-byte UTF-8, and NUL becomes `00`.
- **`JSON.stringify`:** a lone surrogate is escaped as `\udXXX` (well-formed JSON.stringify), NUL as `\u0000`, and a valid pair is emitted as the character itself. On the success path no prepared value is serialized (L0506-D001), so this boundary is reachable only through Pi's failure diagnostic, which Minion's TOOL-003 renders in its own text.
- **Where replacement happens:** U+FFFD replacement happens **only** at the UTF-8 encoding boundary, never at preparation (Owner decision §5).

### S4: the key domain

- Keys reached through `JSON.parse` carry the same string domain: a lone-surrogate key and a pair key keep their code units.
- `"__proto__"` becomes an **own** property and survives preparation.
- A duplicate key resolves to the **last** value.
- The empty key is kept.

### K1: object key ENUMERATION order (another hole, now visible)

`JSON.parse('{"oldText":"a","newText":"b","b":1,"2":2,"1":3,"a":4}')` enumerates `1, 2, oldText, newText, b, a`. This is ECMAScript own-property order: array-index keys first in ascending numeric order, then the other keys in insertion order. Pi's prepared object, as seen by the hook and `execute`, enumerates in that order.

`spec/auth.md` already records this hazard for auth JSON rendering. Nothing records it for tool arguments.

## Cross-language comparison

**Python** (merged main `53290de4`, real `PreparedArgumentsValidator`, `prepare_edit_arguments`, `encode_utf8`):
- On **all 180 string cells** it matches Pi: verdict, prepared code units (its canonical `str`, with JSON pairs combined and lone surrogates kept) and UTF-8 projection.
- The **only** difference is K1: Python's dict enumerates in pure insertion order (`oldText, newText, b, 2, 1, a`).

**Rust** (certified `PreparedValue`):
- `String(String)` cannot hold S1's lone-surrogate members: that is WP132-RUST-C001, and it covers every lone-surrogate member, high or low, at any position.
- `Object(BTreeMap)` enumerates keys **sorted** (`1, 2, a, b, newText, oldText`), which differs from Pi on K1.

## Architecture question (Owner decision §7)

Does the prepared-value architecture now cover the complete known JS primitive domain on the certified preparation paths?
- **Numbers:** covered by L0506-D001.
- **Strings:** covered once D002 adds a UTF-16-capable string.
- **Booleans and null:** trivial.
- **Arrays:** ordered in all three.
- **Objects:** have a remaining **ordering** dimension (K1). It is not a primitive, but it is part of the JS object value the hook observes, and **both bindings** currently differ from Pi.
- **`undefined`:** not reachable through `JSON.parse`. A shim can produce it in Pi; it is not characterized here.

## Open questions for the contract

**K1's scope is not decided here.** It is an observable Pi behavior (hook/`execute` enumeration) outside D002's string mandate.
- If it matters for **prepared** arguments, it equally concerns the **raw** `ToolCall` arguments (Layer 02 decoding).
- It may also concern every serialization of them, for example tool-execution events and session persistence, where Pi's `JSON.stringify` emits array-index keys first.
- Deciding whether certified Layers 02/03 must reproduce ECMAScript key order is a governance question (Owner-only under #75). It is raised with the Owner and not folded silently into D002.
