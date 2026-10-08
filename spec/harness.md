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
- **DIV-006:** an invalid ignore pattern is dropped with a diagnostic and does not abort discovery
  (Owner decision `minion-agent#158` issuecomment-6054403282, §1).
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
  code: file_info_failed | list_failed | read_failed | parse_failed | invalid_metadata | invalid_path
        | invalid_ignore_pattern,
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

**Invalid patterns (DIV-006).** Pinned `ignore@7.0.5` builds each rule's JavaScript RegExp lazily
(`makeRegexPrefix`, then the trailing-wildcard rule, flag `i`). When that RegExp is invalid, for
example an out-of-order character range such as `[~-a]` or an unterminated class such as `[ab/c`,
the first evaluation of the rule throws `SyntaxError`, and Pi's whole `loadSkills` rejects. Whether
it throws depends on rule order and on the path being checked. Minion instead:
- **Classifies the pattern when its ignore file is read.** A prefixed pattern (step 5) is *invalid*
  exactly when pinned `ignore@7.0.5` would reject the RegExp it builds for that pattern. The
  canonical pattern×path corpus fixes which patterns those are. A pattern that `ignore` itself
  skips (a blank line, a `#` line, or an invalid trailing backslash) is neither added nor invalid,
  as in Pi.
- **Drops each invalid pattern** with exactly one diagnostic `{code: invalid_ignore_pattern, path:
  <the ignore file's path>, message: "ignore pattern is not valid and was dropped"}`. The
  diagnostics are emitted in line order, right after that ignore file is read: after any earlier
  ignore-file diagnostic of the same directory, and before the next ignore file and the listing.
- **Keeps the valid patterns,** adding them in their original order. Discovery continues. With no
  invalid pattern, behaviour is identical to Pi.

A directory name can make every prefixed pattern of its own ignore file invalid (for example a
directory named `[~-a]`). Each of those patterns is dropped with its diagnostic.

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
- the `parse_failed`, `invalid_path` and `invalid_ignore_pattern` texts (Minion's own, quoted above).

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
