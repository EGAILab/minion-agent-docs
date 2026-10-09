# Layer 14 WP-14.1 — Rust handoff (skill discovery and diagnostics)

**From:** Claude (shared-contract owner). **To:** Codex (Rust owner). **Coordination:**
`minion-agent#158`, status `RUST_IMPLEMENTATION`.

**Scope:** implement WP-14.1 in `minion-agent-rust` against the **merged shared contract**. Python
is not an oracle: verify against the contract, the pinned Pi source and the canonical evidence below.

## 1. Exact baselines

| Item | Value |
|---|---|
| Pinned Pi | `b7bb00b936dbe21b8e160b3e89efdec361846699` (`packages/agent/src/harness/skills.ts`, `types.ts`); deps `yaml@2.9.0`, `ignore@7.0.5`; Node v22.15.1 / ICU 76.1 |
| Shared contract (base) | docs `0edad98a`, code `2a21bc0d` (contract checkpoint, approved) |
| Shared contract (current, with DIV-006 and DIV-007) | docs master `6ec91692`, code main `97ec5687` |
| Python | CERTIFIED at code `97ec5687` (`#161`); not a semantic authority for Rust |

## 2. Requirements and normative text

`spec/harness.md`, section "WP-14.1 — Skill discovery and diagnostics", which is the authority:

| Requirement | Subject |
|---|---|
| `HAR-013` | records: `Skill`, `SkillDiagnostic`, sourced variants. String domains are in the "Strings" bullet |
| `HAR-001` | discovery and traversal: roots in input order; `fileInfo` → kind (a symlink via `canonicalPath`); ignore files; listing; `SKILL.md` short-circuit; raw-collation-sorted children; dotfile and `node_modules` skips; root-only `.md` candidates; addressed paths, never canonicalized |
| `HAR-011` | ignore files (`.gitignore`, `.ignore`, `.fdignore`) and `ignore@7.0.5` matching, including case-insensitive JS Canonicalize |
| `HAR-010` | frontmatter extraction and the Minion YAML subset, grammar rules 1–7 |
| `HAR-012` | validation and diagnostics: codes, normative messages, UTF-16 lengths, order |

The manifest rows mirror these: `HAR-001`, `HAR-001-DIV-005`, `HAR-010`, `HAR-010-DIV-004`,
`HAR-010-DIV-007`, `HAR-011`, `HAR-011-DIV-006`, `HAR-012` and `HAR-013`.

## 3. Approved departures and mappings

`assurance/pi-divergences.md` holds DIV-004 to DIV-007.

| ID | Rule |
|---|---|
| DIV-004 | the frontmatter is read by the Minion YAML subset; anything outside it is `parse_failed`, and within it values equal `yaml@2.9.0` |
| DIV-005 | an entry whose root-relative path `ignore` refuses gets one `invalid_path` diagnostic and is skipped, instead of aborting discovery |
| DIV-006 | an ignore pattern whose pinned-`ignore` RegExp is invalid is dropped, with one `invalid_ignore_pattern` diagnostic per pattern in line order; valid patterns keep their order |
| DIV-007 | block collections nest at most **64** deep (the root mapping is 1, and each nested mapping or sequence one more); deeper is `parse_failed` |
| PP-14-1 | the `parse_failed` message is Minion's own fixed text |
| PP-14-3 | symlink cycles keep Pi's outcome shape (one non-`not_found` diagnostic, other skills kept); the host depth is not normative |
| PP-14-8 | filesystem-origin message text is not normative; code, path and order are |
| Collation | the `TOOL-040` pinned profile (en-001, ICU 78.3), raw compare (Owner); no new public API |

## 4. Hazards found during the Python passes

These are not instructions to copy Python. Each was a real defect in one binding; check that Rust
does not repeat it.

- **Writable, identity-preserving records (`WP141-R001`).** `map_skill` receives the loaded
  `Skill` and may edit it and return it. In Rust this is ownership: pass the owned record and keep
  whatever is returned.
- **No stack-bound traversal (`WP141-R004`).** A finite acyclic directory tree 1,050 deep (and one
  with a leaf `.gitignore`, which clears the matcher cache) must load as in Pi. Both the directory
  walk and `ignore`'s parent-path evaluation (`_t`) must be independent of call-stack depth.
- **Frontmatter depth.** DIV-007 bounds the reader at 64. A reader that could still exhaust its
  stack must contain that as `parse_failed`, never panic or abort.
- **Strings (HAR-013 "Strings").** YAML-decoded `name` and `description` are scalar values (subset
  rule 1 forbids surrogates), and `content` comes from `read_text_file`, so Rust `String` is
  lossless for every record field. Lengths are UTF-16 code units, and `trim` is JS `trim`.
- **`ignore` port.** Use JS RegExp semantics:
  - non-`u` mode, matching on code units, with Canonicalize for the `i` flag (U+212A does not
    match `k`);
  - Annex B escapes (`\c`, legacy octal);
  - an invalid RegExp is DIV-006 when its ignore file is read, and `SyntaxError` otherwise.

## 5. Canonical evidence

- **Scenarios:** `conformance/agent/skill-discovery/*.json`, **96** documents, against the schema
  `conformance/schema/skill-discovery-scenario.schema.json`.
  - A runner materializes the fixture on the real filesystem, calls the binding's real loader over
    the real `ctx.fs`, maps addressed paths back, and compares.
  - `posix_only` rows are skipped on Windows.
  - `c01` uses the PP-14-3 shape: `code_one_of` and `path_within`.
- **Differential corpora** (language-neutral JSON data, under `minion-agent-python/tests/skills/data/`):
  - `ignore-corpus.json`: 6,000 pattern sets and 18,000 path checks, from pinned `ignore@7.0.5`;
  - `frontmatter-corpus.json`: 8,000 cases with the reference reader's accept/reject and value.

  Both are reusable for a Rust differential test. Their generators are in
  `assurance/layers/data/14-wp141/` (`ignore-corpus.mjs`, `frontmatter-corpus.mjs`).
- **Pi and model outputs:** `assurance/layers/data/14-wp141/out-{win32,linux}.json` and
  `model-{win32,linux}.json`.
- **Deep-structure witnesses** to reproduce in Rust (not canonical documents): a 1,050-deep
  acyclic tree, plain and with a leaf `.gitignore`, plus a later root, loads `[a, good]` with no
  diagnostics. Codex's probe for this is `deep_ignore.mjs`.

## 6. Out of scope and open

- `#69`: the Windows Layer 12 classification map (unchanged).
- `#133`: NUL and non-Unicode names (excluded).
- WP-14.2 (`#159`): prompt assembly. Its contract is merged and its implementation is separate.

## 7. Stop condition

A Rust implementation candidate meeting every requirement above, with:
- the 96 canonical scenarios passing on Windows and Linux;
- the corpora differential;
- the deep-structure witnesses;
- negative controls for DIV-005, DIV-006 and DIV-007;
- Rust gates green.

Then hand it to Claude for the independent Rust review. Report any contract defect
(`CONTRACT_ASSURANCE_DEFECT`) back rather than coding around it.
