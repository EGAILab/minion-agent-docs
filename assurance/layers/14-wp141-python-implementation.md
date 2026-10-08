# Layer 14 WP-14.1 — Python implementation record

**Status:** Python candidate, remediation 1 (`WP141-R001`, `WP141-R002`; §5) for independent
re-review.

**Coordination:** `minion-agent#158` (`PYTHON_IMPLEMENTATION` → `IMPLEMENTATION_REVIEW`).

**Contract:** `spec/harness.md` WP-14.1, approved at the contract checkpoint and merged at docs
`0edad98a`, code `2a21bc0d`. The contract delta for **DIV-006** is in this docs PR and needs review
with it.

**Owner decisions:**
- `minion-agent#158` issuecomment-6051472129 (PP-14-*);
- `minion-agent#158` issuecomment-6054403282 (WP141-I001 → DIV-006; WP141-I002 → the Layer 12
  correction L12-D004).

## 1. Candidate

- **Code:** PR `#161`, branch `layer/14-wp141-python`, head `5ba6973a`. It depends on L12-D004
  (`#162`, issue `#163`, now CLOSED), whose correction `c01` needs on Linux. This branch is merged up
  to `main`, so its diff is WP-14.1 only.
- **Gated tree:** the gates below ran on `e4a128f2`.
  - `5ba6973a` differs from that tree only in `pi-parity-manifest.yaml` `EXEC-002`'s `python` text,
    which came from `main` (L12-D004 certification, `#164`).
  - Manifest and schema validation on the review head: **762 passed**.
- **Package:** `minion-agent-python/src/minion_agent/skills/`.

| Module | What it is |
|---|---|
| `discovery.py` | Pi's harness loader over the certified `ctx.fs`, and the records |
| `_frontmatter.py` | Pi's extraction on UTF-16 code units, and the Minion subset reader, HAR-010 rules 1–7 |
| `_ignore.py` | A port of `ignore@7.0.5` `ignores()`, plus DIV-006's `add_valid` |

- **Reuse:**
  - `TOOL-040`'s pinned collator, compared raw. There is no new public API.
  - The shared `js_trim`.
  - `_utf16` helpers.
- **Coverage and layering:** the coverage source gains `skills`, and the layering test gains the
  `skills` rule: no `session`, `telemetry`, `agent` or `agent_loop`.

## 2. How the JavaScript semantics are reproduced

- **Ignore matching.**
  - The `REPLACERS` chain is reproduced on code-unit strings, with JavaScript `\s`, `.` and `$`.
  - The generated JavaScript RegExp source is translated to Python:
    - Annex B escapes: legacy octal, `\c`, identity escapes;
    - classes expanded to code-unit sets;
    - `$` → `\Z`.
  - The `i` flag is **ECMAScript `Canonicalize`** (non-Unicode mode), using `toUpperCase` at Unicode
    16.0 via the pinned ICU (`upper_unicode16`). Unlike `re.IGNORECASE`, U+212A KELVIN SIGN never
    matches `k`.
  - Matching runs on canonicalized code units. Rule order, the skip conditions and parent-first
    `_t` caching follow the package.
  - An invalid RegExp raises `InvalidIgnorePattern` lazily in `ignores()`, exactly where Pi throws.
    Discovery instead uses `add_valid`, which compiles eagerly (DIV-006).
- **Frontmatter.** Extraction slices code units. For example, `---😀` splits the pair as Pi does,
  and the subset then refuses the lone surrogate.
- **Validation.** Lengths are counted in UTF-16 units, and `trim` uses the JS whitespace set.

## 3. Evidence

### Differential correctness (permanent tests in `tests/skills/test_differential_corpora.py`)

| Check | Result |
|---|---|
| `ignore` port vs pinned `ignore@7.0.5`. Corpus generator `data/14-wp141/ignore-corpus.mjs` (Node v22.15.1); win32 and Linux outputs identical | **0 mismatches** in **18,000** committed checks (6,000 pattern sets; 1,044 of them throwing). One-off: **0** in **90,000** (seed 7, 30,000 sets; 5,093 throwing) |
| Python frontmatter reader vs the reviewed reference reader (`frontmatter-corpus.mjs`) | **0 mismatches** in **8,000** committed cases (1,936 accepted). One-off: **0** in **50,000** (10,637 accepted) |

**Port defects found by the corpus and fixed, before any review:**
- `\c` not followed by a control letter is a literal backslash (Annex B).
- An unterminated class (`[ab/x`) is a JavaScript `SyntaxError`.

### Canonical scenarios

The runner is `tests/conformance/skill_discovery_runner.py`. It is thin: it materializes the
fixture, calls the real `load_skills` over the real `LocalFileSystem`, and maps addressed paths
back for comparison. The scenarios are all **92** in `conformance/agent/skill-discovery/`.

| Platform | Result |
|---|---|
| Windows | 82 passed, 10 POSIX-only skipped |
| Linux | 92/92 passed, including `c01-symlink-cycle` (with L12-D004) and the POSIX-only DIV-005 rows |

### Negative controls

| Control | Killed by |
|---|---|
| DIV-006, Python: *drops without a diagnostic* | `i10`, `i11`, and `test_invalid_patterns_are_reported_per_pattern_in_file_order` |
| DIV-006, Python: *stops at the first invalid pattern* | `i10`, and the three `add_valid` unit tests |
| Model: early return after an invalid entry | `r05` alone |
| Model: invalid entry without a diagnostic | `r01`, `r02`, `r03`, `r05` |
| Model: invalid pattern without a diagnostic | `i10`, `i11` |
| Model: invalid pattern stops the file | `i10` |
| The 11 subset-reader fuzz controls | every seed (characterization §8) |

### Full gates on the candidate (`#161` with L12-D004)

The gates were rerun on `#161` @ `e4a128f`, which includes L12-D004 remediation 1 (`L12D004-R001`, code `#162` @ `32287fa5`).

| Platform | Result |
|---|---|
| Windows, pinned ICU 78.3 | **5,200 passed, 42 skipped, 21 xfailed**; coverage **100%** (9,075 statements, including `skills`); ruff clean; mypy clean (113 files) |
| Linux (`python:3.13`, pinned ICU volume, search engines mounted) | **5,147 passed, 0 failed, 97 skipped, 19 xfailed**; skill-discovery conformance 93 passed |

On the earlier head `4676a51b` (before remediation 1): Windows 5,196 passed; Linux 5,143 passed, 0 failed.

The 21 Windows xfails are the 19 existing ones plus L12-D004's two strict Windows xfails (`#69`).

## 4. Disclosed changes and limitations

1. **Fixture rename.** Canonical `v04` used the directory `skills/nul`, a reserved device name on
   Windows. Node could create it only through libuv's `\\?\` paths. It is renamed
   `skills/tilde-null`, and the Pi and model results were re-derived. Only `v04` changed: the
   rename, plus the order of the two entries.
2. **DIV-006** (`HAR-011-DIV-006`): an invalid ignore pattern is dropped with one
   `invalid_ignore_pattern` diagnostic, and the valid ones are kept in order. There are three new
   canonical rows: `i10` and `i11` (DIV-006), and `i12` (positive control, identical to Pi). Every
   previously Pi-identical scenario, including the 40-row ignore corpus, is still identical to Pi.
3. **The Layer 12 correction (L12-D004):** a separate delta under review (`#162` / `#163`). Without
   it, `c01` emits 4 diagnostics on Linux.
4. **The pre-existing Windows classification gap** (`#69`): Windows `canonical_path` reports
   `invalid` where Pi reports `unknown` (ELOOP) for a self-loop or cycle, and `not_found` for
   over-long names. This is out of scope. WP-14.1 is unaffected, because any non-`not_found` code
   gives the one diagnostic. It was returned to the Owner in L12-D004 §4.
5. **Pre-existing formatting.** Eight files outside this WP fail `ruff format --check` on `main`,
   with the review environment's ruff. They are untouched.
6. **Rust:** WP-14.1 is not implemented in Rust. The contract and the canonical scenarios are the
   handoff.

## 5. Remediation 1 (Codex implementation review 1)

**Review:** Codex, **CHANGES REQUESTED** on code `#161` @ `5ba6973a` / docs `#258` @ `3a33a691`. It is
posted verbatim at `minion-agent#158` issuecomment-6058014898. The DIV-006 shared-contract delta was
**APPROVED** at that docs SHA. The two findings follow.

### `WP141-R001` (medium, `PI_PARITY_DEFECT`): the public records were frozen

- **Defect:** the six public records (`Skill`, `SkillDiagnostic`, `LoadedSkills`, `SourcedSkill`,
  `SourcedSkillDiagnostic`, `LoadedSourcedSkills`) were frozen dataclasses. Pinned Pi's records are
  ordinary writable objects, and `loadSourcedSkills` hands the loaded `Skill` itself to `mapSkill`.
  So a mapper that edits the skill and returns it worked in Pi but raised `FrozenInstanceError`
  here. That rejected the whole call.
- **Correction:** all six public records are writable (`@dataclass(slots=True)`), and the result
  containers stay lists. Private parser value objects are unchanged. The contract had never stated
  immutability, so there is no contract change.
- **Witnesses** (`tests/skills/test_discovery.py`):
  - `test_map_skill_may_edit_the_loaded_skill_and_return_it`: the same object comes back, with
    edited fields and the opaque source identity unchanged;
  - `test_loaded_records_and_their_lists_are_writable`.

### `WP141-R002` (medium, `PI_PARITY_DEFECT`): deep nesting escaped as `RecursionError`

- **Defect:** frontmatter nested about 1,200 levels deep exhausted the recursive subset reader. The
  `RecursionError` escaped the loader and lost every later root. Pinned Pi contains its parser's
  failure as `parse_failed` and continues.
- **Correction:** `read_subset` converts the reader's stack exhaustion into `FrontmatterError`. The
  file therefore takes the ordinary HAR-010 parse outcome: one `parse_failed`, with the Minion
  message, for a declared `SKILL.md`; a silent skip for an undeclared `.md`. Discovery continues.
  - The process recursion limit is not changed.
  - No depth limit is added to the grammar.
- **Contract clarification** (`spec/harness.md` HAR-010, "Resource exhaustion"): the depth at which
  exhaustion happens is a host limit, in Pi and in each binding, and is **not normative**. Only the
  outcome shape is. This follows the PP-14-3 precedent for host-limit-dependent symlink cycles. It
  is submitted for the reviewer's judgment: if it needs governance, it goes to the Owner.
- **Pi cross-check** (`data/14-wp141/r002-probe.mjs`, pinned loader, Node v22.15.1):
  - **Depth 1200:** skills `[ok]`, diagnostics `[parse_failed @ bad/bad/SKILL.md]`; the undeclared
    `root/deep.md` is skipped silently.
  - **Depth 500:** everything loads normally.
- **Witnesses:**
  - `test_deep_nesting_is_one_parse_failed_and_later_roots_still_load` (depth 1200);
  - `test_deep_nesting_in_an_undeclared_root_file_is_skipped_silently`;
  - `test_shallower_nesting_still_loads[100|500]` (controls).

### Known-bad check

The two remediated modules from `5ba6973a` were restored in a disposable copy:
- **Fail there:** the four new R001/R002 witnesses, with `FrozenInstanceError` and an escaping
  `RecursionError`.
- **Pass there:** the two shallow controls.

On the candidate, every witness passes.

### Fresh gates (code `#161` @ `8f2bd8c9`)

| Platform | Result |
|---|---|
| Windows, pinned ICU 78.3 | **5,206 passed, 42 skipped, 21 xfailed**; coverage **100%** (9,078 statements); ruff clean; mypy clean (113 files) |
| Linux (`python:3.13`, pinned ICU, search engines mounted) | **5,153 passed, 0 failed, 97 skipped, 19 xfailed** |

**Unchanged by this remediation:** the DIV-006 delta (approved), the 92 canonical scenarios, both
differential corpora and their controls.
