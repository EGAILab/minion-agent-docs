# Harness Semantics

Phase 6-7 parity includes execution seams, built-in tools, prompt assembly, skills, compaction, and
built-in harness message projections.

Skill behavior follows pinned Pi discovery, validation, diagnostics, deterministic traversal, and
available-skills XML/escaping. `disable-model-invocation` skills are excluded from model-visible
available-skills output.

Compaction defaults: reserve_tokens=16384, keep_recent_tokens=20000. Context estimate finds the most
recent usable assistant usage, ignores error/aborted/zero usage, prefers total_tokens, otherwise uses
component sum, then estimates trailing messages; with no usable usage it estimates the full history.
Summary calls use no prompt-cache retention and a fresh session identity.

Durable AgentHarness lanes/operations/suspend-resume/replay/navigation/pending writes remain explicit
`deferred parity` for Phase 9.

---

## WP-14.1 — Skill discovery and diagnostics (`HAR-001`, `HAR-010`..`HAR-013`)

**Status (`minion-agent#158`):** CONTRACT_DRAFT. Python: NOT_IMPLEMENTED. Rust: NOT_IMPLEMENTED.

**Authority:** pinned Pi `b7bb00b936dbe21b8e160b3e89efdec361846699`,
`packages/agent/src/harness/{skills,types}.ts`. This is the *harness* loader, `AUTH-14-1` in
`assurance/layers/14-prompt-assembly-skills-scoping.md`. The coding-agent sibling
`packages/coding-agent/src/core/skills.ts` is **not adopted**.

**Owner decision:** `minion-agent#158` issuecomment-6051472129.

**Approved departures from pinned Pi:**
- **DIV-004:** the frontmatter YAML subset.
- **DIV-005:** an invalid entry does not abort discovery.
- **PP-14-1:** the `parse_failed` message text is Minion-defined.
- **PP-14-8:** the text of filesystem-origin messages is non-normative.

**Approved mappings:**
- **PP-14-3:** symlink cycles keep Pi's outcome shape.
- **Collation:** the deterministic profile of `TOOL-040`.

Everything else in this section is direct Pi parity.

**Evidence:** `assurance/layers/14-wp141-characterization.md`, with the data in
`assurance/layers/data/14-wp141/`.

### HAR-013 — Records

```text
Skill{
  name: string,
  description: string,
  content: string,
  file_path: string,                 # the addressed path ctx.fs listed (never canonicalized)
  disable_model_invocation: bool,
}

SkillDiagnostic{
  type: "warning",
  code: file_info_failed | list_failed | read_failed | parse_failed | invalid_metadata | invalid_path,
  message: string,
  path: string,
}

load_skills(fs, roots: string | [string]) -> {skills: [Skill], diagnostics: [SkillDiagnostic]}

load_sourced_skills(fs, [{path, source}], map_skill?)
    -> {skills: [{skill, source}], diagnostics: [SkillDiagnostic + {source}]}
```

- `fs` is the certified `ctx.fs` (`spec/execution.md` §3). Discovery uses only `file_info`,
  `list_dir`, `canonical_path`, `join_path` and `read_text_file`.
- `source` values are opaque. They are attached unchanged to every skill and diagnostic from that
  input.
- `map_skill` is application code. A failure raised by it propagates to the caller and is **not** a
  diagnostic, as in Pi.
- **Strings:** every string that comes from file *text* is a Unicode scalar-value string:
  - YAML-decoded `name` and `description`: the subset (HAR-010) refuses every construct that could
    produce a lone surrogate or a control character;
  - `content`: `read_text_file` produces only scalar values.

  Names and paths that come from the filesystem (`file_path`, a directory-name fallback for `name`,
  a diagnostic `path`) are within Layer 12's certified path domain. Non-Unicode native names stay
  excluded, as they already are (`minion-agent#133`). This is why the carriers are lossless in both
  languages (feasibility §4.1).
- **Lengths:** wherever this section measures a length, it counts **UTF-16 code units**, as JS
  `.length` does.

### HAR-001 — Discovery

`load_skills` processes `roots` in input order and concatenates the results. Duplicates are never
removed: the same file reached twice, or two skills with one name, both appear in order.

**Per root `r`:**
1. Call `file_info(r)`.
   - `not_found` → skip `r` silently.
   - Any other error → `file_info_failed`, with path `r` as given.
2. Resolve the kind (below). A root that is not a directory is skipped silently. In particular, a
   **file root is never loaded as a skill**.
3. Call `walk(info.path, include_root_files = true, matcher = new, root = info.path)`.

**Kind resolution, `resolve_kind(info)`:**
- `file` and `directory` are returned as they are.
- `symlink` → call `canonical_path(info.path)`, then `file_info` on the result. The kind is that
  target's kind if it is a file or directory; otherwise the entry is unresolved.
- At either step, `not_found` is silent and unresolved.
- Any other error → `file_info_failed` (path = the entry's addressed path), and the entry is
  unresolved.

**`walk(dir, include_root_files, matcher, root)`:**
1. Call `file_info(dir)`.
   - `not_found` → contribute nothing.
   - Any other error → `file_info_failed` (path `dir`).
   - A dir that does not resolve to a directory → contribute nothing.
2. Add the ignore rules of `dir` to `matcher` (HAR-011), **before** listing.
3. Call `list_dir(dir)`. An error → `list_failed` (path `dir`), and the directory contributes
   nothing.
4. **`SKILL.md` short-circuit.** Scan the entries in `list_dir` order. Take the first entry whose
   name is exactly `SKILL.md` and that resolves to a file and is not ignored, with the entry path
   relative to `root` (HAR-011).
   - Load it (HAR-010), and **stop**: no sibling or descendant of `dir` is visited.
   - This happens even when that file yields no skill.
   - An ignored or non-file `SKILL.md` does not short-circuit.
5. Otherwise, take the entries sorted by name (**Collation**, below). For each entry, in order:
   1. Skip names starting with `.`, and the exact name `node_modules` (case-sensitive).
   2. Resolve the kind; skip an unresolved entry.
   3. Check it against the ignore rules (HAR-011). A directory is checked as `relative + "/"`. An
      ignored entry is skipped.
   4. A directory → `walk(entry.path, false, matcher, root)`. The matcher is the same one, and it
      accumulates.
   5. A file whose name ends with `.md` (case-sensitive) is loaded only if `include_root_files` is
      set (HAR-010). Every other file is skipped.

Skills and diagnostics are emitted in this depth-first order. A child directory's results are
spliced in at its sorted position.

**Collation (mapping, Owner-approved).**
- Pi sorts with `a.name.localeCompare(b.name)` under the host's Node, ICU build and locale.
- Minion sorts with a **stable** sort that compares the raw names with the pinned collator of
  `spec/tools.md` WP-13.1 "Collation" (`TOOL-040`): `en-001`, tertiary strength, numeric off,
  case-first off, normalization on, ICU 78.3.
- The comparison is **without** `ls`'s lowercase key.
- Ties (compare = 0) keep `list_dir` order.
- Evidence: on the characterized 71-name neighbourhood, the pinned profile reproduces Node v22.15.1
  / ICU 76.1 exactly (`collation-evidence.json`).
- This is an internal reuse of the `TOOL-040` collator. It adds no new public comparator API.

**Symlink cycles (PP-14-3, no divergence).** A directory cycle reached through symlinks must
satisfy all of the following:
- discovery **terminates**;
- it emits **exactly one** filesystem-origin diagnostic for the cycle (`file_info_failed` or
  `list_failed`), whose path lies within the traversed cycle and is the path of the `ctx.fs`
  operation that failed;
- skills found elsewhere are retained;
- there is no other diagnostic for the cycle.

These are **not** normative:
- **Depth:** where the host's filesystem reports the cycle. Pi measured 64 levels on Windows and 41
  on Linux.
- **Code:** which of the two codes it carries. That depends on whether the host fails the
  canonicalization first or the listing first.

Canonical cases assert only the shape.

**Invalid entry (DIV-005).**
- **Trigger:** the path checked against the ignore rules is empty, or starts with `/`. This is the
  root-relative path, with `/` appended for a directory.
- **Reachability:** names starting with `.` are skipped earlier, so this happens only for POSIX
  names that start with `\` or consist only of `\`.
- **Effect:** emit one diagnostic `{code: invalid_path, path: <entry addressed path>, message:
  "entry path cannot be matched against ignore rules"}`, skip the entry, and **continue**.
- **What is retained:** skills found before and after it, and in other roots.
- Pi instead rejects the whole `loadSkills` call.

### HAR-011 — Ignore files and matching

**Reading the ignore files.** For each walked directory, read `.gitignore`, `.ignore` and
`.fdignore` from it, in that order. For each name:
- `join_path` fails → `file_info_failed` (path = the directory).
- `file_info`:
  - `not_found` → silent;
  - any other error → `file_info_failed` (path = the ignore file);
  - a kind other than `file` → silent (a **symlinked or directory** ignore file is not read).
- `read_text_file` fails → `read_failed`.

**Turning lines into patterns.** Split the text on `\r?\n`. Each line becomes a pattern as follows:
1. Trim it. If the trimmed text is empty, or starts with `#` but not `\#` → drop the line.
2. Otherwise continue with the **untrimmed** line.
3. A leading `!` → a negation; strip the `!`. A leading `\!` → strip **the backslash only**. The
   pattern then starts with `!`, and the matcher reads it as a negation (Pi quirk, adopted: `\!x`
   does not ignore `!x`).
4. Strip one leading `/`.
5. Prefix the pattern with the directory's root-relative path and `/` (nothing at the root). Re-add
   `!` for a negation.

**Matching.**
- **Authority:** `ignore@7.0.5` `ignores()` with default options, the version Pi pins.
- **Relative path:** the path is computed as a string from the addressed paths:
  1. replace every `\` with `/`;
  2. strip trailing `/`;
  3. equal paths → the empty string;
  4. if the path starts with `root + "/"` → the remainder;
  5. otherwise → the path with any leading `/` stripped.
- **Observable rules** (characterization §3):
  - case-**insensitive** matching;
  - dir-only patterns (`build/`) match the directory and its contents, but not a file `build`;
  - negation re-includes;
  - `**` matches at any depth;
  - patterns accumulate across all three files and the nested directories;
  - an unescaped trailing space is discarded and an escaped one (`\ `) is literal;
  - CRLF ignore files work.
- **Conformance:** the canonical pattern×path corpus.

Implementations port the matcher. A host gitignore library is not an authority unless it passes the
corpus.

### HAR-010 — Frontmatter extraction and the Minion YAML subset

**Extraction (direct Pi parity).**
- Normalize CRLF, then CR, to LF. A leading U+FEFF is **not** stripped.
- If the text does not start with `---`, or contains no `\n---` at index 3 or later, the
  frontmatter is empty and the body is the whole normalized text, **untrimmed**.
- Otherwise:
  - `T = text[4 : endIndex]`;
  - `body = text[endIndex + 4 :]`, trimmed with JS `String.prototype.trim` (its whitespace set
    includes U+FEFF and U+3000).
- **Consequences:**
  - text after `---` on the opening line is kept, minus its first character;
  - a `----` or `---foo` closer leaves `-` or `foo` at the start of the body.

**The subset (DIV-004).** `T` is read by the grammar below. Every input it rejects is
`parse_failed`, never partially interpreted. Within the subset, the value is identical to
`yaml@2.9.0`.

Evidence:
- a differential fuzz of 1,500,000 generated inputs (1,374,031 distinct): whenever the subset
  accepts, `yaml@2.9.0` accepts with an
  identical value tree;
- eleven negative controls, each killed on all three seeds;
- 25/25 realistic skill frontmatters accepted with identical values.

The grammar:

1. **Characters.**
   - `T` must not contain:
     - U+0000–U+0008 or U+000B–U+001F;
     - U+007F or U+0080–U+009F;
     - U+2028, U+2029 or U+FEFF;
     - any surrogate.
   - TAB and LF are allowed.
2. **Lines.**
   - Split `T` on LF. If the last piece is empty and is not the only piece, drop it: a final LF ends
     a line rather than starting one.
   - A line whose leading run of spaces is followed by a TAB is rejected.
   - A *blank* line holds only SP and TAB.
   - A *comment* line holds optional SP or TAB, then `#`.
3. **Document.**
   - If every line is blank or a comment, the frontmatter is empty: no fields, as with Pi's
     `parse(...) ?? {}`.
   - Otherwise, the first other line must have indentation 0. It starts `Mapping(0)`. After that
     mapping, only blank or comment lines may remain.
4. **`Mapping(n)`.** Blank and comment lines are skipped.
   - A line indented less than `n` ends the mapping. A line indented more than `n` is rejected.
   - An entry line is `KEY ":"`, followed by end of line or a SP, then the value text.
   - `KEY` matches `[A-Za-z_][A-Za-z0-9_.-]*` and is not one of `null`, `Null`, `NULL`, `true`,
     `True`, `TRUE`, `false`, `False`, `FALSE`.
   - A TAB right after the `:` is rejected.
   - A duplicate key in the same mapping is rejected.
   - The value text has leading SP and TAB removed, and is then one of:
     - **empty, or starting with `#`** → look at the next non-blank, non-comment line, at
       indentation `m`:
       - `m > n` and it is an entry line → a nested `Mapping(m)`;
       - `m >= n` and it starts with `- ` → `Sequence(m)`;
       - any other `m > n` → rejected;
       - otherwise → `null`.
     - **`|` or `>`** → a block scalar (rule 7).
     - **anything else** → a same-line scalar (rule 5), with plain continuation allowed.
5. **Same-line scalars.**
   - **Double-quoted.**
     - It must close on the same line. Only SP or TAB, optionally followed by a `#` comment, may
       follow the closing quote.
     - Escapes: `\\`, `\"`, `\/`, `\t`, `\n`, `\xHH`, `\uHHHH` and `\UHHHHHHHH`. A numeric escape's
       code point must be at most U+10FFFF, and not a character rule 1 forbids.
     - Any other escape is rejected.
     - The value is always a string.
   - **Single-quoted.**
     - `''` stands for `'`; there are no other escapes.
     - It must close on the same line, with the same trailing rule.
     - The value is always a string.
   - **Plain.**
     - **Whitespace.** Only SP and TAB are YAML whitespace here. Every other whitespace character
       (U+00A0, U+2003, U+3000, and the like) is scalar content: it is never indentation, never
       stripped, and never a comment separator (`WP141-C001`).
     - **The text.** A comment starts at the first SP or TAB followed by `#`. The text is
       everything before the comment, with trailing SP and TAB removed. It must:
       - be non-empty;
       - not contain TAB;
       - not contain `:` followed by SP or TAB, and not end with `:`;
       - not start with any of `` - ? : , [ ] { } # & * ! | > ' " % @ ` ``. The exception is
         `-`, `?` or `:` followed by a non-SP, non-TAB character (for example `-x`).
     - **Continuation.** A mapping value may continue only if its first line has no comment. The
       continuation lines are the following lines up to the first non-blank line indented `<= n`.
       Each one is either blank, or a text line under these rules:
       - a comment line is rejected;
       - the line is taken without its indentation, which is its leading SP characters only;
       - it may contain no comment;
       - its text follows the same rules, except that it may not start with any of those
         characters at all.
     - **Folding.** Folding joins consecutive text lines with a SP. Where `k >= 1` blank lines
       separate two text lines, they are joined with `k` LF instead. Trailing blank lines are not
       part of the scalar.
     - **Resolving the folded text** (`yaml@2.9.0` core schema):
       - `null` for `~`, `null`, `Null`, `NULL`;
       - a boolean for `true`, `True`, `TRUE`, `false`, `False`, `FALSE`;
       - a number for any of:
         - `0o[0-7]+`;
         - `[-+]?[0-9]+`;
         - `0x[0-9a-fA-F]+`;
         - `[-+]?\.(inf|Inf|INF)` and `\.(nan|NaN|NAN)`;
         - `[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)[eE][-+]?[0-9]+`;
         - `[-+]?(\.[0-9]+|[0-9]+\.[0-9]*)`;
       - otherwise a **string**. So `yes`, `on`, `1_000` and `2001-12-14` are strings.
6. **`Sequence(m)`.** Blank and comment lines are skipped.
   - A line indented less than `m`, or one at indentation `m` not starting with `- `, ends the
     sequence. A line indented more than `m` is rejected.
   - An item is `- ` followed by a same-line quoted or plain scalar, **without** continuation. An
     empty item, or one that is only a comment, is rejected.
7. **Block scalars.**
   - **Header:** `[|>][+-]?`, optionally followed by SP or TAB and a `#` comment. Explicit
     indentation digits, and anything else, are rejected.
   - **Region:** the following lines up to the first non-blank line indented `<= n`.
   - **Content indentation `I`:** that of the region's first non-blank line.
   - **Blank lines in the region:** a blank line must contain no TAB and at most `I` spaces. In a
     region with no content line, a blank line containing any space at all is rejected. It is an
     *empty line*.
   - **Content lines:** a content line indented less than `I` is rejected. Its text is the line
     without its first `I` characters. In `>`, a text starting with SP or TAB (a more-indented
     line) is rejected.
   - **Body:**
     - `|` joins the text and empty lines with LF.
     - `>` joins consecutive text lines with a SP, and with `k` LF across `k` empty lines.
   - **Chomping,** where `E` is the number of empty lines after the last text line in the region
     that are **followed by an LF in `T`**. The unterminated final line of `T` (`T` does not end in
     LF) contributes no line break even when it is whitespace-only: for example, an indented blank
     line just before the closing `---`.
     - clip (no indicator) → `body + LF`;
     - strip (`-`) → `body`;
     - keep (`+`) → `body + LF + LF×E`.

     With no text line at all: keep gives `LF×E`, and clip and strip give the empty string.
   - Block scalars are always strings.

   This reproduces Pi's trailing newline: `description: >` over `one` / `two` gives `"one two\n"`,
   even at the end of `T`, which itself never ends in LF.

**Constructs outside the subset**, all rejected as `parse_failed`, with Pi's own `yaml@2.9.0`
behaviour recorded as the DIV-004 witness:
- flow collections (`[...]`, `{...}`);
- anchors, aliases and tags (`&`, `*`, `!`);
- merge keys (`<<`) and complex or quoted keys;
- directives (`%`) and document markers (`...`);
- multi-line quoted scalars;
- explicit block indentation, and more-indented folded lines;
- a plain value that starts on the line after its key;
- a scalar or sequence document;
- tab indentation;
- the characters forbidden by rule 1, including escapes that produce them.

Pi's other parse failures (duplicate keys, an unterminated quote) are `parse_failed` in both.

**Using the frontmatter.** Loading a file, `load_file(path, parent_dir_name)` — direct parity,
except the `parse_failed` message:
- **Declared:** the file is *declared* when its path's last segment, splitting on `/` or `\` after
  stripping trailing separators, is exactly `SKILL.md`.
- **Read:** `read_text_file` fails → `read_failed`.
- **Parse failure:** a declared file → `{code: parse_failed, message: "frontmatter is not valid in
  the supported YAML subset"}` (PP-14-1); a non-declared file → silent. Either way, no skill is
  loaded.
- **Fields:**
  - `description` = the frontmatter's `description` if it is a string, otherwise absent;
  - `name` = the frontmatter's `name` if it is a non-empty string, otherwise `parent_dir_name`.
    That is the `FileInfo.name` of the directory being walked, so for a root `.md` it is the
    **root's** name.
- **Disable flag:** `disable_model_invocation` = whether the frontmatter's
  `disable-model-invocation` is the boolean `true`.
- **Missing description, non-declared:** a non-declared file whose description is absent or blank
  after JS `trim()` is skipped silently, before validation.

### HAR-012 — Validation and diagnostics

**Order.** For a candidate file, the `invalid_metadata` warnings come in this order:
1. **Description:** `description is required`, when it is absent or blank after `trim()`.
   Otherwise, `description exceeds 1024 characters (N)` when it is longer than 1024.
2. **Name:**
   1. `name "X" does not match parent directory "Y"`;
   2. `name exceeds 64 characters (N)`;
   3. `name contains invalid characters (must be lowercase a-z, 0-9, hyphens only)`, when the name
      does not match `^[a-z0-9-]+$`;
   4. `name must not start or end with a hyphen`;
   5. `name must not contain consecutive hyphens`.

`N` is a length in UTF-16 code units.

**Effect.** Name warnings never block loading. A missing or blank description does: there is no
skill. The skill's `description` keeps its exact, **untrimmed** value.

**What is normative**, for every diagnostic:
- code, path and order;
- the `invalid_metadata` texts (Pi's own);
- the `parse_failed` and `invalid_path` texts (Minion's own, quoted above).

For `file_info_failed`, `list_failed` and `read_failed`, the message is the `ctx.fs`
`FsError.message`, and is **non-normative** (PP-14-8). Layer 12 is not reopened to reproduce Node's
prose.

**Layer 12 note:** the open Python issue `minion-agent#66` (`read_text_file` translating newlines)
is unobservable here, because extraction normalizes CR to LF itself.

### Conformance evidence (WP-14.1)

**Canonical scenarios:** `conformance/agent/skill-discovery/*.json`, schema
`conformance/schema/skill-discovery-scenario.schema.json`.
- They are generated from the characterization corpus, using each scenario's expected values.
- Rows that diverge from pinned Pi are labelled with their `DIV-` ID. Their Pi observation is kept
  in the evidence data.
- POSIX-only rows: backslash names, case-variant names, trailing-space names. `r05` is the DIV-005
  continuation witness, with a successful skill both before and after the invalid entry
  (`WP141-C002`).

**Frontmatter subset:** the subset cases are fixture rows (one `SKILL.md` each), through the real
loader. No YAML API is exposed (Owner decision §6).

**Ignore matcher:** the pattern×path corpus, through the real loader.

---

## WP-14.2 — Prompt assembly and model-visible skill/tool metadata (`HAR-002`, `HAR-014`..`HAR-018`)

**Status (`minion-agent#159`):** CONTRACT_DRAFT. `HAR-016` depends on the Layer 08 delta `L08-D001`
(`minion-agent#166`), which is under its own contract review. Python: NOT_IMPLEMENTED. Rust:
NOT_IMPLEMENTED.

**Authority:** pinned Pi `b7bb00b936dbe21b8e160b3e89efdec361846699`.
- `packages/agent/src/harness/{system-prompt,skills}.ts` for the skills block and skill invocation
  (`AUTH-14-1`).
- `packages/coding-agent/src/core/{system-prompt,agent-session}.ts` **only** as the reference for
  section order, the `read` gate and tool-metadata rendering (`AUTH-14-2`). Its Pi-product text is
  not adopted.

**Owner decisions:** `minion-agent#159` issuecomment-6051472443, §15–§20 (`PP-14-4` mapping; `PP-14-5`
Option B); issuecomment-6057640884 (`PP-14-9` Option A, `HAR-016`).

**Input record:** WP-14.1's `Skill` (`HAR-013`), unchanged: `name`, `description`, `content`,
`file_path`, `disable_model_invocation`. Records are values; a change to the skill set is a
replacement (see `HAR-016`).

**Strings.** Every rule below operates on JavaScript strings (UTF-16 code units), as in WP-14.1. The
"JS whitespace set" is ECMA-262 `WhiteSpace` ∪ `LineTerminator`: the set `String.prototype.trim` and
the RegExp class `\s` use.

### HAR-002 — Available-skills block (`DIRECT_PI_PARITY`)

`format_skills_block(skills)`:
1. **Filter:** keep the skills whose `disable_model_invocation` is not `true`, in input order. There
   is no sorting and no deduplication.
2. **None left** → the empty string `""`.
3. **Otherwise** these lines, joined by `\n`, with no leading or trailing newline:

   ```text
   The following skills provide specialized instructions for specific tasks.
   Read the full skill file when the task matches its description.
   When a skill file references a relative path, resolve it against the skill directory (parent of SKILL.md / dirname of the path) and use that absolute path in tool commands.

   <available_skills>
     <skill>
       <name>{esc(name)}</name>
       <description>{esc(description)}</description>
       <location>{esc(file_path)}</location>
     </skill>
   </available_skills>
   ```

   There is one `<skill>` element per kept skill, indented exactly as shown (2 and 4 spaces).
4. **`esc`** replaces, in this order, `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`, `"` → `&quot;`,
   `'` → `&apos;`. Nothing else is escaped: newlines, control characters and lone surrogates pass
   through.
5. **`location`** is `file_path` exactly: the addressed path, native separators, never
   re-normalized.

### HAR-014 — Explicit skill invocation (`DIRECT_PI_PARITY`)

`format_skill_invocation(skill, additional_instructions?)` returns:

```text
<skill name="{name}" location="{file_path}">\nReferences are relative to {dirname(file_path)}.\n\n{content}\n</skill>
```

- **No escaping** of any field.
- **Additional instructions:** when present and non-empty, append `\n\n{additional_instructions}`.
  An absent or empty value appends nothing.
- **`dirname(path)`**, on code units:
  1. strip every trailing `/` and `\`;
  2. `i` = the last index of either `/` or `\`;
  3. if `i == 2` and the unit at index 1 is `:` → the first 3 units (for example `C:\`);
  4. otherwise, if `i <= 0` (including no separator at all) → `/`;
  5. otherwise → the first `i` units.

This is the persisted user-message text of an explicit invocation. *Sending* it as a message is an
application action. No run operation is added here.

### HAR-018 — Tool prompt metadata (`MINION_EXTENSION`, `PP-14-5` Option B)

**Fields.** Two optional, additive fields on the Layer 05 tool definition (`ctx.tools`):
- `prompt_snippet`: a string, or absent;
- `prompt_guidelines`: a sequence of strings, or absent.

They are model-visible metadata only. They never change the tool schema, identity, execution,
argument validation, registry lookup or permission semantics, and they never enter the request's
tool schemas.

**Normalization** (Pi `_normalizePromptSnippet` / `_normalizePromptGuidelines`):
- **Snippet:**
  1. absent or `""` → none;
  2. replace each run of `\r`/`\n` with one space;
  3. replace each run of JS-whitespace characters with one space;
  4. JS-trim;
  5. an empty result → none.
- **Guidelines:**
  1. JS-trim each entry;
  2. drop empty entries;
  3. keep the first occurrence of each exact string, in order.

**Tools section.** It is **opt-in**: it is rendered only when enabled for the assembly. Over the
assembly's tool snapshot (`HAR-016`), in snapshot order:
- **Available tools:** `Available tools:` then, for each tool with a snippet, `- {name}: {snippet}`.
  The block is omitted when no tool has a snippet. Pi's `(none)` line is **not** rendered.
- **Guidelines:** `Guidelines:` then `- {g}` for each guideline, concatenated in tool order. Across
  tools, only the first occurrence of an exact string is kept. The block is omitted when there are
  none.
- **Joining:** each block's lines are joined by `\n`, and the two blocks by `\n\n`.
- **Empty:** with both blocks omitted, or with the section disabled, the section is `""` and is
  absent from the prompt (never synthetic).
- **Not adopted** (Pi product text):
  - the Pi preamble;
  - "In addition to the tools above, …";
  - the bash-only bullet;
  - the two fixed bullets "Be concise in your responses" and "Show file paths clearly when working
    with files".

### HAR-015 — Section composition (`MINION_ARCHITECTURAL_MAPPING`, `PP-14-4`)

The assembled system prompt is a fixed, ordered list of sections. Each section is a string, and an
empty string means the section is absent.

1. **`base`:** the agent's base prompt text.
2. **`tools`:** `HAR-018`'s section (opt-in).
3. **`contributed`:** the prompt configuration's `sections`, in order (`HAR-016`). Pi's
   `appendSystemPrompt` maps here.
4. **`skills`:** `HAR-002`'s block, included **only if** the tool snapshot contains a tool named
   exactly `read` (the C-4 gate). Pi's custom-prompt `!selectedTools` clause has no analogue: a
   Minion assembly always has a tool snapshot.

**Bytes:** the non-empty sections in this order, joined by `\n\n`, with no leading or trailing
separator. No cwd line, context files, `SYSTEM.md` or Pi documentation text is added (`PP-14-6`
exclusions).

**Pi reference** (custom-prompt path): `customPrompt` + `\n\n` + append + `\n\n` + skills block.
Minion keeps that order and those separators. It places the opt-in tools section where Pi's default
prompt carries "Available tools"/"Guidelines", directly after the base.

### HAR-017 — Request reconstruction

- **Recorded bytes:** the assembled prompt's exact bytes are what the request header records and
  what the model receives, through the certified `MINION-003` header and `assemble_system`
  (Layer 03, unchanged).
- **Storage:** the assembled prompt is carried as the request's `system_base` component, or as the
  certified per-step override. Splitting it into several header components is a storage detail,
  not adopted here. Content addressing already stores an unchanged prompt once.
- **Witness:** reconstructing the header yields byte-identical model-visible text.

### HAR-016 — Snapshot timing and consistency (`MINION_ARCHITECTURAL_MAPPING`; Owner `PP-14-9` Option A)

**Mechanism.** The Layer 14 composer is installed as the driver's prompt assembler (`L08-D001`,
`minion-agent#166`; `spec/agent.md`, Layer 08, "Optional prompt assembler"). Its contract is that
seam's, unchanged.
- **When it runs:** once for every provider request without a per-step system override, while that
  request is built.
- **What it receives:**
  - `base`: the run-local `RunContext.system_prompt`, which is `AgentInstance.system_prompt` at run
    start unless a `prepareNextTurn` replacement supplied another;
  - `tools`: the request's own tool snapshot, whose schemas that request carries.
- **The rule this gives:** the `tools` section (`HAR-018`), the `read` gate (`HAR-015`) and the
  request's tool schemas therefore derive from **one** snapshot, by construction. The composer never
  reads `ctx.tools`.

**Prompt configuration.** The composer holds one **prompt configuration** value:
- `skills`: an ordered sequence of WP-14.1 `Skill` records;
- `tools_section`: a boolean, default `false`;
- `sections`: an ordered sequence of strings, the `contributed` sections in order.

**How it changes.**
- **By whole-value replacement only.** Supplying a configuration copies its membership: a caller
  mutating its own sequence afterwards changes nothing (T-1 membership isolation).
- **Records are immutable values** in both bindings, so there is no retained-record mutation to
  observe (`L14-SCOPE-R003` reduces to "a change is a replacement").
- **When a replacement takes effect:** at the next request build that starts after it. A request
  being built uses exactly one configuration value. This is atomic: there is never a mix of an old
  and a new value.

**Override.** A per-step system override replaces the whole prompt, and the composer is not called
(`L08-D001`). This matches the scoping record, under which the override replaces the whole prompt
(C-12).

**Errors.** The composer is total over valid inputs, so it does not raise for any configuration or
tool snapshot. Any failure is the seam's failure rule: nothing is sent, and the run settles through
`handleRunFailure`.

**Not adopted:**
- a registration API for plugin-contributed sections;
- per-scope section visibility;
- section names.

The `contributed` list is an ordered value an application supplies. A later plugin mechanism would
be a separate, governed extension (Owner decision §16: no prompt framework).

### Conformance evidence (planned; WP-14.2)

**Canonical byte cases** (`conformance/agent/prompt-assembly/`):
- **`HAR-002`:**
  - zero, one and many skills;
  - every skill disabled, giving `""`;
  - `disable_model_invocation` exactly `true` vs other values;
  - order preserved and duplicates kept;
  - the five escapes and the `]]>` case;
  - newlines, control characters and lone surrogates passing through;
  - Windows and POSIX `location` spelling.
- **`HAR-014`:**
  - every `dirname` branch: trailing separators, mixed separators, drive root, root, no separator;
  - no escaping;
  - additional instructions present, empty and absent.
- **`HAR-018`:**
  - normalization edge cases (CRLF, NBSP, U+FEFF, U+3000, empty-after-trim);
  - per-tool and cross-tool deduplication;
  - snapshot order with shadowing;
  - section disabled; no metadata, giving `""`; snippet-only; guidelines-only.
- **`HAR-015`:** every subset of empty and non-empty sections, the `read` gate, and the separators.

**Pi oracle.** Every `DIRECT_PI_PARITY` case is generated from the byte-copied pinned harness
functions. The tools section is generated from pinned `buildSystemPrompt`'s normalization and
rendering, with the non-adopted product lines removed by a documented, asserted patch (as for the
WP-14.1 model).

**Driver-level witnesses (`HAR-016`/`HAR-017`)**, through the real driver with the composer
installed (`L08-D001`):
- a tool registered after run start appears in neither the prompt nor the schemas of that run;
- a `prepareNextTurn` replacement of the tools is reflected in both, and so is `added_tool_names`
  growth;
- `read` gating follows the snapshot;
- a configuration replaced mid-run takes effect at the next request, atomically;
- the override bypasses the composer;
- the header's `system_base` round-trips byte-identically.
