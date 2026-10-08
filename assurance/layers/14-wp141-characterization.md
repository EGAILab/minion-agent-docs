# Layer 14 WP-14.1 — Skill discovery: characterization and feasibility

Mode: contract-draft evidence (`CONTRACT_DRAFT`, `minion-agent#158`). **IMPLEMENTATION AUTHORIZED:
NO.** This record is derivation evidence (`process/agent-workflow.md` §9.3). It is not the
normative contract, which is `spec/harness.md` WP-14.1. §1–§6 record the pre-decision
characterization as reviewed. §7 records the evidence for the contract drafted after the Owner
decision.

## 1. Baselines and authority

```text
code main:    dcb1efed2e18d203dfab35f19774a85009d2ad80
docs master:  2dac1b7e7b81b66fed80a145f3fd9be6060426e2   (approved Layer 14 scoping merged)
pinned Pi:    b7bb00b936dbe21b8e160b3e89efdec361846699
```

- **Authority:** `AUTH-14-1`. Scoping artifact
  `assurance/layers/14-prompt-assembly-skills-scoping.md`, approved at `minion-agent-docs#253`
  issuecomment-6049683660.
- **Requirements:** `HAR-001`, `HAR-010`..`HAR-013`.

## 2. Harness (`assurance/layers/data/14-wp141/`)

- **What it runs.** `run.mjs` runs the **byte-copied pinned** harness loader (`pinned/skills.ts`)
  over **pinned `NodeExecutionEnv`** (`pinned/env/nodejs.ts`) on a real filesystem.
- **Pinned copies.** All four copied files are byte-identical to
  `ref-repos/pi/packages/agent/src/harness/` at the pin, checked with `cmp`.
- **Dependencies.** `yaml@2.9.0` and `ignore@7.0.5`, whose lockfile integrity matches Pi's root
  `package-lock.json`.
- **Procedure.** Each scenario materializes a fixture tree in a fresh directory, calls
  `loadSkills(env, roots)`, and records:
  - skills: name, description, content, path relative to `<base>`, disable flag;
  - diagnostics: code, message, path;
  - or the rejection.
- **Command.** `node --experimental-strip-types --no-warnings run.mjs <out.json>`.

| Platform | Runtime | Result |
|---|---|---|
| Windows 11 (NTFS) | Node v22.15.1, ICU 76.1 | `out-win32.json`: 42 scenarios, 35 run, 7 POSIX-only skipped |
| Linux (`python:3.13` image, Node 22.15.1 mounted at `/node`, work dir `/tmp`) | Node v22.15.1, ICU 76.1 | `out-linux.json`: 42 run |

**Cross-platform result.** All 35 shared scenarios are **identical** once path separators are
normalized.

**Setup lesson.** In a first run, two scenarios differed only because Windows' case-insensitive
filesystem merged the `b`/`B` and `node_modules`/`Node_Modules` fixture directories. The
case-variant entries were moved into POSIX-only scenarios `d05p`/`d06p`; that run is not credited.
Windows itself cannot hold such a pair, so the case-variant rows are POSIX-only by nature.

`cycle.mjs` → `cycle-{win32,linux}.txt` characterizes a symlink cycle (§3).

`yaml-oracle.mjs` → `yaml-oracle.json` runs 95 frontmatter sources through `yaml@2.9.0` and records
Pi's **observable projection**:

- accept or reject;
- `typeof name === "string"` and `typeof description === "string"`, with their values;
- `disable-model-invocation === true`.

## 3. Characterized rules

These are confirmations and refinements of scoping §5. Scenario IDs are those in `scenarios.mjs`.

### Traversal

- **d02, d03 (S-9).** A `SKILL.md` short-circuits even when it yields no skill (d03:
  `description is required`, and the nested `inner/SKILL.md` is never visited).
- **d04.** An *ignored* `SKILL.md` does not short-circuit.
- **d05 (S-10).** Child order is
  `_x, -y, a, a_b, a-b, a10, a9, b, e, é, Z`: raw `localeCompare`, not numeric, with
  punctuation before letters.
- **d05p (S-10, POSIX).** Case pairs order lowercase first: `a, A, b, B, e, E, é, É`.
- **d06 / d06p (S-11).**
  - Dotfiles and dot-directories are skipped.
  - The skip is the exact name `node_modules`: `Node_Modules` on POSIX **is** traversed.
- **d07 (S-15).** Direct `.md` loads only at the root; `sub/nested.md` does not, while
  `sub/deeper/SKILL.md` does.
- **d08.** Skipped silently:
  - a root `.md` with no frontmatter;
  - a blank description;
  - a non-`.md` extension, including `.MD` (case-sensitive `endsWith`);
  - a non-declared file whose YAML is invalid.
- **d09 (S-28).** The root-`.md` name quirk is confirmed. `noname.md` takes the root folder's name
  `skills` and gets no warning; `other.md` loads with `name "other" does not match parent
  directory "skills"`.
- **d10 (S-1..S-3, S-30).** Roots are processed in input order. A missing root is silent. A *file*
  root is silent (not loaded). The same root given twice yields duplicate skills.
- **d11.** Depth is unlimited. A parent `SKILL.md` hides a nested one.
- **d12, d13 (S-25).** A symlinked skill directory loads, as does a symlinked `SKILL.md` file. The
  addressed path, not the target, is the `filePath`. A dangling symlink is silent. A symlinked root
  works.
- **d14 (S-30).** Duplicate names are kept, in traversal order.

### Validation

- **v01, v02 (S-27, S-28).**
  - An invalid name loads with warnings.
  - All five name messages appear in the specified order, with UTF-16 lengths (`name exceeds 64
    characters (75)`).
- **v03.**
  - 1024 code units → no warning.
  - 1023 + one astral character = 1025 code units → `description exceeds 1024 characters (1025)`.
  - 512 astral characters = 1024 code units → no warning.
- **v04.** `description is required`, with no skill, for:
  - whitespace only (including `\t`);
  - a number, a list, `~`, or no description at all;
  - **U+3000**, and **U+FEFF** (JS `trim()` removes both).
- **v05.** A YAML `name: 123`, `name: ''` or `name: true` → falls back to the directory name.
- **v06.** `disable-model-invocation`:
  - **only** YAML 1.2 core booleans `true`/`True`/`TRUE` disable;
  - `yes`, `on`, `'true'`, `1` and `false` do not.
- **v07.** A description is stored **untrimmed** (`"  padded  "`).

### Frontmatter extraction

- **f01.** CRLF and lone CR are normalized, and the body is trimmed.
- **f02.** A BOM-prefixed `SKILL.md` has no frontmatter → `description is required`.
- **f03:**
  - unclosed frontmatter, or an indented ` ---` → no frontmatter;
  - `---x` opens frontmatter (the `x` is dropped);
  - a `----` closer → body `-\nBody`;
  - a `---foo` closer → body `foo\nBody`;
  - `---\n---` → empty YAML → `{}`;
  - no body → `content: ""`.
- **f04.** `parse_failed` (only for `SKILL.md`), with the message = the YAML library's first line,
  for:
  - duplicate keys;
  - tab indentation;
  - a `...` document end followed by more content;
  - an unterminated quote;
  - a directive-only document.

  An over-indented `  - x` continuation is **accepted** as a plain multi-line scalar (`d - x`).
- **f05.** Value semantics:
  - a date stays a string;
  - `!!str 123` → `"123"`;
  - aliases resolve;
  - a merge key `<<` does **not** merge (description missing);
  - a flow mapping works;
  - a scalar document has no fields;
  - a folded or literal block scalar **keeps a trailing newline** (`"one two\n"`), because Pi's
    slice omits the final newline and `yaml@2.9.0` still clips to one;
  - `0o17` is a number → description missing;
  - complex keys are stringified;
  - a `__proto__` key is an own property, with no prototype leak (oracle).
- **f06.** A non-declared `.md` with invalid YAML is silent.

### Ignore files

- **i01.**
  - A dir-only pattern works.
  - A glob plus negation re-includes `keep-tmp`.
- **i02.** Nested `.gitignore` patterns are prefixed with their directory:
  - `inner` under `group/` does not affect the root `inner/`;
  - `/anchored` matches only `group/anchored`.
- **i03.**
  - `#` comments and blank lines are dropped.
  - `\#hash` ignores `#hash`.
  - **Finding (Pi quirk):** `\!bang` does **not** ignore `!bang`. `prefixIgnorePattern` strips the
    backslash and passes `!bang` to `ignore`, which reads it as a *negation*. Pi-exact behaviour
    reproduces this.
- **i04.** Matching is case-insensitive.
- **i05.** Patterns accumulate across all three files in order: `.gitignore` → `.ignore` →
  `.fdignore`. `!c` in `.ignore` re-includes `c`, which `.gitignore` excluded.
- **i06.** A directory named `.gitignore` is silent. A **symlinked** `.ignore` is not read
  (`kind !== "file"`).
- **i07.** `**/drop` matches at depth, and `*.md` / `!keep.md` apply to root files.
- **i08.** CRLF ignore files are handled.
- **i09 (POSIX).** An unescaped trailing space is discarded (`plain ` ignores `plain`). An escaped
  one is literal (`esc\ ` ignores `esc `).

### Symlink cycle (`PP-14-3`, `cycle.mjs` → `cycle-{win32,linux}.txt`)

Fixture: `skills/a/loop -> ..`, with and without a root `b.md` skill.

- **Pi terminates on both platforms** with exactly **one** `file_info_failed` diagnostic. Its
  message is `ELOOP: too many symbolic links encountered, …`, raised by `canonicalPath` in
  `resolveKind`.
- Skills found elsewhere (`b.md`) are kept, and nothing else is reported.
- **The depth is host-defined:** the diagnostic path has **64** `loop` segments on Windows (NTFS)
  and **41** on Linux.
- The cycle therefore needs **no divergence** for termination or the outcome shape. Only the
  diagnostic `path` and `message` are host-defined, and `PP-14-8` already makes fs-error messages
  non-normative.

### Whole-discovery rejection (S-33, POSIX)

- **r01.** A leading-backslash file rejects the call. The sibling `-a` is collected first.
- **r02.** A leading-backslash directory → `RangeError … got "/d/"`.
- **r03.** A rejection in the second root **loses the first root's skills**.
- **r04.** An inner backslash loads normally.

## 4. Cross-language feasibility (template `process/templates/cross-language-feasibility-matrix.md`)

### 4.1 Value-domain carriers

| Carrier | Pi repr | Python | Rust | Owning seam | Lossless? |
|---|---|---|---|---|---|
| Fixture file names and paths (`FileInfo.name/path`) | JS string from Node fs (UTF-16; WTF-16 on Windows) | Layer 12 path domain | Layer 12 path domain | Layer 12 `ctx.fs` (certified) | within Layer 12's certified domain; NUL and non-Unicode stay excluded (#133) |
| Skill `name`/`description`/`content` | JS string: YAML-decoded, may hold lone surrogates (`"\ud800"` oracle row) | `str` (code points): holds lone surrogates directly, but **length must count UTF-16 units** and any UTF-8 encoding needs explicit handling | **`String` cannot hold lone surrogates** | WP-14.1 (new) | **NO for Rust `String`.** It needs the certified JS-string representation (F2 / `L0506-D002`) for these carriers, or a governed rule. This is a finding for the contract checkpoint. |
| Diagnostic `message` from Pi's own strings | fixed templates + JS `.length` | exact | exact | WP-14.1 | yes |
| Diagnostic `message` from fs errors (`file_info_failed`/`list_failed`/`read_failed`) | Node `err.message` (`EACCES: permission denied, …`) | Layer 12 `FsError.message`, **not certified text** | same | Layer 12 | **NO** → `PP-14-8` |
| Diagnostic `message` from YAML errors (`parse_failed`) | `yaml@2.9.0` `YAMLParseError.message` | engine-specific | engine-specific | WP-14.1 | **NO** → `PP-14-1` |
| The disable flag | `=== true` on the YAML value | `is True` on a YAML 1.2 core boolean | same | WP-14.1 | yes, given a matching engine |

### 4.2 Lower-layer capability matrix

| Operation | Layer | Seam | Exact Pi semantics? | Extension needed? |
|---|---|---|---|---|
| `fileInfo`/`listDir`/`canonicalPath`/`joinPath`/`readTextFile` and their codes | 12 | `ctx.fs` | codes yes; message text no | none (`PP-14-8` instead) |
| `not_found` vs other-code silence | 12 | `FsErrorCode` | yes; the Windows code map is #69 (open, not a prerequisite) | none |
| Raw `localeCompare` on names | 13 | `TOOL-040` pinned ICU (en-001, ICU 78.3) | Pi uses host Node ICU 76.1 under the host locale; mapped onto pinned en-001 / ICU 78.3 | **additive** raw-compare accessor, plus its own skill-collation disposition and evidence (re-review note) |
| YAML 1.2 core parsing, as `yaml@2.9.0` | none | none | see §4.3 | new, WP-14.1-owned |
| `ignore@7.0.5` matching | none | none | see §4.4 | new, WP-14.1-owned |

### 4.3 YAML engine (`yaml_engines.py` → `yaml-engines-report.json`)

These are Pi-observable projection agreements over the 95-source oracle:

| Python engine | Agrees | Main disagreements |
|---|---|---|
| PyYAML 6.0.3 `safe_load` (YAML 1.1) | 72/95 | `yes`/`no`/`on`/`off` become booleans; dates are resolved; `0o17` is not an int; duplicate keys are accepted; merge keys merge; block scalars lack the trailing newline |
| ruamel.yaml 0.18.15 safe, pure, `version=(1,2)`, no duplicate keys | 84/95 | timestamps; `1_000`; unknown tags rejected; merge keys merge; **block scalars lack the trailing newline**; `\t`-only values; C0/C1 control characters |
| ruamel.yaml 0.18.15 round-trip | 83/95 | similar |

The block-scalar difference is model-visible and **realistic**: multi-line `description: >` is
common. Feeding ruamel `src + "\n"` fixes folded and literal scalars but breaks `>+` keep-chomping
(85/95).

**Conclusion:** no stock Python engine reaches exact parity. The two feasible options, which need a
decision under `PP-14-2`:

- **A.** A Minion-owned frontmatter reader for a **defined YAML subset**, with a deterministic
  `parse_failed` for anything outside it.
- **B.** A configured YAML 1.2 engine with a custom resolver that removes timestamps, merge keys and
  `_` integers and keeps unknown tags as plain values, plus chomping alignment, witnessed on the
  corpus, with residual cases governed.

Rust has the same question for `saphyr`/`yaml-rust2`. It is for the Rust-side contract checkpoint;
no Rust probe was run here.

### 4.4 `ignore@7.0.5` matcher

- The package is a single 784-line, dependency-free file that compiles gitignore patterns to
  regular expressions.
- Python `pathspec` and the Rust `ignore` crate differ in case-sensitivity, negation and the
  trailing-space rules (i04, i09).
- **Feasible:** a direct port in both languages, verified on a generated pattern × path corpus.
  The corpus is a contract-checkpoint obligation.

### 4.5 Hazard checklist (applicable families)

- **F2 JS String/UTF-16:** `AUDITED`, with §4.1 findings: UTF-16 lengths (v03), the `trim()`
  whitespace set (v04), lone surrogates in YAML-decoded strings.
- **Unicode/ICU:** `AUDITED` (d05, d05p), mapped through `TOOL-040`.
- **Error/coercion projection (F5):** `AUDITED`. Message text from external errors is `PP-14-1` and
  `PP-14-8`.
- **Async/order (F4):** `NOT_APPLICABLE` for the observable output. Pi's loader awaits
  sequentially, and the order is defined by traversal.
- **JS Number (F1):** `NOT_APPLICABLE`. Numbers only make a field non-string.
- **ECMAScript object order:** `NOT_APPLICABLE`. Only the `name`/`description`/disable keys are
  read.

## 5. Owner decisions needed before WP-14.1 contract freeze

| ID | Decision | Evidence | Recommendation |
|---|---|---|---|
| `PP-14-1` | `parse_failed` message text: the exact `yaml@2.9.0` text, or Minion-defined | §4.1, f04 | **Minion-defined message.** Code, path, order and the accept/reject decision stay exact. |
| `PP-14-2` | YAML engine strategy: A (subset reader + deterministic `parse_failed`) or B (configured engine + governed residue) | §4.3 | **A.** A defined subset covering block mappings, plain, quoted and block scalars (with Pi's chomping), flow mappings and sequences, aliases, and comments, matching `yaml@2.9.0` exactly on it. Everything else → `parse_failed`, a governed divergence for the unrealistic constructs (tags, merge keys, directives, complex keys). |
| `PP-14-3` | Symlink cycles | §3 symlink cycle (characterized) | **No divergence.** Adopt Pi's outcome shape: termination, one non-`not_found` fs failure diagnostic from `ctx.fs`, and other skills kept. The cycle depth, and so the diagnostic `path`, is **host-defined** and non-normative. Its message falls under `PP-14-8`. Canonical cases assert the shape only. |
| `PP-14-7` | Whole-discovery rejection (S-33) | r01–r03 | Owner's choice. The default is **Pi-exact** (reject). The alternative is a `invalid_path` diagnostic with the entry skipped. |
| `PP-14-8` (new) | fs-error diagnostic message text (`file_info_failed`/`list_failed`/`read_failed`) | §4.1 | **Code, path and order exact; message = the `ctx.fs` `FsError.message`, non-normative**, as Layer 12 already treats message text. |
| collation | The skill sort is mapped from host Node ICU 76.1 onto pinned `en-001` / ICU 78.3 | d05/d05p, re-review note | Adopt `TOOL-040`'s pinned collation for skills as a recorded mapping, with its own evidence (d05/d05p rows re-run on the pinned collator). |

## 6. Next

1. Owner decisions (§5).
2. Draft the normative WP-14.1 section in `spec/harness.md`, manifest rows `HAR-001`/`HAR-010`..`013`,
   the canonical scenario schema, and cases generated from this corpus.
3. Independent contract checkpoint (`CONTRACT_REVIEW`).

No production code.

## 7. Contract-draft evidence after the Owner decision (`minion-agent#158` issuecomment-6051472129)

**Decisions taken:**
- **PP-14-1:** approved; the `parse_failed` message is Minion-defined.
- **PP-14-2:** Option A, with **DIV-004**.
- **PP-14-3:** approved; no divergence.
- **PP-14-7:** the resilient alternative, **DIV-005**.
- **PP-14-8:** approved.
- **Skill collation:** approved as a `TOOL-040` mapping.

This section records the evidence for the normative WP-14.1 text in `spec/harness.md`. That text
supersedes the recommendations in §5.

### 7.1 The Minion YAML subset (DIV-004)

**Reference reader (non-normative evidence):** `subset-reader.mjs`, which implements `spec/harness.md`
HAR-010 rules 1–7.

| Check | Command | Result |
|---|---|---|
| **Soundness:** whenever the subset accepts, `yaml@2.9.0` accepts with an identical value tree (strings, booleans, null, the number class, nested mappings and sequences) | `subset-diff.mjs 300000 <seed>`, seeds 1–5 (generator `subset-gen.mjs`) | **0 violations in 1,500,000 inputs** (`fuzz-final.txt`); about 70.6k accepted per 300k |
| **Negative controls:** each one a single-rule mutation of the reader that the fuzzer must detect, killed only if *every* seed (21, 22, 23 × 50k) finds a violation | `fuzz-controls.mjs` | **9/9 killed**, minimum 181 violations (`fuzz-controls.txt`) |
| **Realistic acceptance:** 25 skill-frontmatter shapes, covering folded and literal descriptions, `>-`, nested `metadata:`, both sequence indents, wrapped plain descriptions, comments, quoted colons, escapes and trailing spaces | `subset-realistic.mjs` | **25/25 accepted, values identical to Pi** (`subset-realistic.json`) |

The nine controls are:
- clip drops the final newline;
- keep drops one newline;
- `: ` accepted inside a plain scalar;
- `-`/`?`/`:` accepted as a lead before anything;
- a duplicate key accepted;
- `yes` read as a boolean;
- a comment allowing a continuation;
- tab indentation accepted;
- folded text joined with LF.

**Defects the fuzzer found while the grammar was drafted.** Each one is fixed in the grammar, and
each fix has a control. None of them reached the contract text:
- a tab-led line after a block scalar;
- keep chomping over-counting when `T` ends in LF;
- whitespace-only block lines beyond the content indent;
- a comment followed by a continuation.

**Narrowing found by the model diff (§7.3).** A plain scalar may start with `-`, `?` or `:` when a
non-space follows. Without that rule, the subset rejected Pi's `name: -A--…` row (v02).

**Setup failures, disclosed and not credited:**
- **Line-number mutations.** The first control harness patched the reader by line number. After the
  reader changed, the patched mutants failed to compile, and that run was discarded. The controls
  now patch exact content, and a mutation that does not apply is reported.
- **Generator refactor.** The refactor that moved the document generator into `subset-gen.mjs`
  first changed the order of RNG calls, and that let one control survive. The original order was
  restored, and the controls run on three seeds so that one stream cannot hide a gap.

### 7.2 Skill collation (mapping)

- `collation-names.json` is a 71-name neighbourhood covering case, accents, combining marks,
  punctuation, digits, `ß`/`ss`, dotless and dotted i, CJK, kana, Greek, Cyrillic, an emoji and
  canonical equivalents.
- Sorted by Node v22.15.1 / ICU 76.1 `localeCompare` (Pi), and by the `TOOL-040` pinned collator
  compared raw under ICU 78.3 (`minion_agent.tools.builtin.collation`), the two orders are
  **identical** (`collation-evidence.json`).

### 7.3 The Minion model and the canonical expectations

**Model.** `make-minion-model.mjs` derives `model/skills.ts` from the byte-copied pinned
`skills.ts`. It applies exactly the approved departures as asserted single-occurrence patches:
- the frontmatter goes through the subset, with the Minion `parse_failed` text;
- the `invalid_path` guard is placed before both ignore checks.

**Runs.** The corpus (`scenarios.mjs`, now **86 scenarios**) ran through the pinned loader
(`out-*.json`) and through the model (`model-*.json`), each on win32 and Linux. The corpus now also
includes:
- every `yaml-oracle` source and every realistic shape as a `SKILL.md`;
- a 300-input boundary sample from the fuzzer's generator;
- a 40-scenario seeded ignore pattern × path corpus;
- the symlink cycle.

**`compare.mjs`.** Separators are normalized in path fields only.

| Comparison | Result |
|---|---|
| Pi win32 vs Pi Linux | structurally identical except `c01-symlink-cycle` (host cycle depth, PP-14-3) |
| Model win32 vs model Linux | structurally identical except `c01-symlink-cycle` |
| Pi vs model (Linux) | **8 scenarios differ, every one by an approved departure:** `v04`, `f04`, `f05`, `y01` and `y03` (DIV-004, plus PP-14-1 where Pi had `parse_failed`) and `r01`–`r03` (DIV-005). `y02` (realistic) and every other scenario are **identical** |

**Generation.** `gen-canonical.mjs` writes the 86 canonical scenarios from the model's Linux
results, so the POSIX-only rows are included.
- It labels `divergences` by comparing with Pi's own result: masked `parse_failed` text → `PP-14-1`;
  any other difference → `DIV-004`, or `DIV-005` for the `r` rows.
- The cycle row asserts only the PP-14-3 shape.

**Hand check of the divergent rows.**
- **DIV-005:** `r01` keeps `-a` and adds one `invalid_path` for `\x.md`; `r02` gives one
  `invalid_path` for `\d`; `r03` keeps `first/a`. Pi rejects all three.
- **DIV-004:** each newly `parse_failed` file uses an excluded construct:
  - flow collections: `list`, `flow`, `proto`;
  - alias and anchor: `alias`;
  - tag: `tagged`;
  - merge key: `merge`;
  - complex key: `complexkey`;
  - scalar document: `scalar`;
  - an escape producing U+FEFF: `bomws`;
  - a `-`-led continuation line: `badindent`.

### 7.4 PP-14-3 implementation note (for the checkpoint)

Node's `realpath` reports ELOOP, so Pi fails at canonicalization. A host whose `canonical_path`
resolves component by component (for example Python's `os.path.realpath`) may instead canonicalize
every level successfully, and fail later at the OS path-length limit, in `file_info` or `list_dir`.

The normative shape therefore allows either fs-origin code, and leaves the depth host-defined. The
shape is: termination, exactly one fs-origin diagnostic within the cycle, other skills retained.
Each implementation must show this shape on both platforms.

## 8. Remediation record: contract checkpoint review 1

- **Review:** Codex, at code `0e1b5627` / docs `5d360f32`, published verbatim on `minion-agent-docs#255`.
- **Verdict:** CHANGES REQUESTED.

§7 is kept as it was reviewed. This section supersedes its numbers.

### 8.1 `WP141-C001`: the reference reader stripped supported scalar content

- **Defect.** `sameLineScalar` removed continuation indentation with JS `trimStart()`. That also
  strips U+00A0, U+2003, U+3000 and similar characters, which pinned `yaml@2.9.0` keeps as content
  (`description: a` / `   b` → Pi `"a  b"`).
- **Fix.** Indentation is now leading **SP only**; TAB was already rejected globally. The spec
  states it explicitly, in HAR-010 rule 5 "Whitespace" and in the continuation rule.
- **Witness.** Canonical `f07-unicode-whitespace-in-continuation`: NBSP, EM SPACE and IDEOGRAPHIC
  SPACE continuations, and a leading NBSP. It runs through the real loader and **matches Pi**.
- **Input space.** The generator now emits these characters (`subset-gen.mjs`).
- **Control.** `continuation-strips-unicode-whitespace`, killed on all three seeds.

### 8.2 `WP141-C002`: no DIV-005 witness after the invalid entry

- **Witness.** Canonical `r05-skills-before-and-after-invalid-entry` (POSIX): `-a/SKILL.md`,
  `\x.md`, `z/SKILL.md` → skills `-a` and `z`, plus one `invalid_path`.
- **Controls** (`model-controls.mjs`, on Linux):
  - *stops walking the directory after the invalid entry* is killed by `r05` **alone**;
  - *skips without a diagnostic* is killed by `r01`, `r02`, `r03` and `r05`.

### 8.3 Self-found evidence defect: the fuzz generator cycled

While analysing why the C001 control first survived, I found that the generator's LCG multiplied
in IEEE doubles past 2^53. It lost precision and cycled.
- **Impact.** Each "300,000-input" seed in §7.1 generated only **291–456 distinct documents**. The
  claimed 1.5M-input soundness evidence therefore covered about 2,000 distinct inputs. The
  reviewer's independent replay used the same generator, so it inherits this.
- **Fix.** Both generators (`subset-gen.mjs`, and the ignore corpus in `scenarios.mjs`) now use
  mulberry32 with exact 32-bit arithmetic.
- **Measured** (`fuzz-uniqueness.json`): about 279,300 distinct per 300k seed, and **1,374,031
  distinct across the five seeds**. The 40 ignore-corpus fixtures are all distinct.

**A real grammar defect, found at once by the diverse generator** (it did not reach any canonical
expectation):
- keep chomping (`+`) counted a whitespace-only final line of `T` that no LF terminates. That
  happens when an indented blank line precedes the closing `---`.
- `yaml@2.9.0` counts no line break for it.
- **Fixed** in rule 7: `E` counts only empty lines followed by an LF in `T`.
- **Witness:** canonical `f08-block-chomping-at-frontmatter-end` (keep, clip and strip over a
  whitespace line and over a blank line before the closer) **matches Pi**.
- **Control:** `unterminated-final-blank-counts`, killed on all three seeds (minimum 4).

### 8.4 Fresh evidence after remediation

| Check | Result |
|---|---|
| Soundness fuzz, seeds 1–5 × 300,000 | **0 violations**; 1,374,031 distinct inputs; about 72.5k accepted per seed (`fuzz-final.txt`) |
| Fuzz negative controls, 11, each over seeds 21–23 × 50k | **11/11 killed on every seed** (`fuzz-controls.txt`) |
| Model negative controls, 2 | **2/2 killed by their intended witness** (`model-controls.txt`) |
| Realistic shapes | **25/25 accepted, identical** |
| Corpus | **89 scenarios**: Pi and model on win32 and Linux |
| Pi win32 vs Pi Linux, model win32 vs model Linux | identical except `c01-symlink-cycle` (PP-14-3) |
| Pi vs model (Linux) | **9 differ, every one by an approved departure:** `v04`, `f04`, `f05`, `y01`, `y03` (DIV-004, plus PP-14-1 where Pi had `parse_failed`) and `r01`, `r02`, `r03`, `r05` (DIV-005). The new `f07` and `f08` are **identical to Pi** (`compare.txt`) |
| Canonical scenarios | 89, regenerated by `gen-canonical.mjs` |

The `y03` boundary sample changed, because the generator changed.

### 8.5 Feasibility summary (current; supersedes the open items of §4)

- **YAML.** The Minion subset (DIV-004) replaces any general engine. Python and Rust implement
  HAR-010 rules 1–7 as small readers. No YAML API is exposed. Accepted file-text values are Unicode
  scalar strings in both languages.
- **Ignore matching.** A port of `ignore@7.0.5`, verified on the canonical pattern × path corpus.
- **Collation.** Reuse the certified `TOOL-040` pinned collator internally, compared **raw**. `ls`'s
  lowercase-key facade is **not** the skill comparator. There is no public comparator API.
- **Carriers.** Filesystem-derived names and paths use Layer 12's certified lossless path and
  JS-string carriers. Accepted file-text values are scalar strings. Source values stay opaque or
  generic.
- **PP-14-3.** Each implementation shows the cycle shape through its real certified `ctx.fs`
  provider on both platforms. The §7.4 note on component-wise canonicalization stands.
