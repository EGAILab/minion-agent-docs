# Layer 14 WP-14.1 — Python implementation record

**Status:** Python candidate, for independent implementation review.

**Coordination:** `minion-agent#158` (`PYTHON_IMPLEMENTATION` → `IMPLEMENTATION_REVIEW`).

**Contract:** `spec/harness.md` WP-14.1, approved at the contract checkpoint and merged at docs
`0edad98a`, code `2a21bc0d`. The contract delta for **DIV-006** is in this docs PR and needs review
with it.

**Owner decisions:**
- `minion-agent#158` issuecomment-6051472129 (PP-14-*);
- `minion-agent#158` issuecomment-6054403282 (WP141-I001 → DIV-006; WP141-I002 → the Layer 12
  correction L12-D004).

## 1. Candidate

- **Code:** PR `#161`, branch `layer/14-wp141-python`. It is **stacked on L12-D004** (`#162`, issue
  `#163`), which is merged into this branch, so its diff shows the L12-D004 change until `#162`
  merges. `#161` depends on `#162`: `c01` fails on Linux without it.
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

| Platform | Result |
|---|---|
| Windows, pinned ICU 78.3 | **5,196 passed, 42 skipped, 21 xfailed**; coverage **100%** (9,072 statements, including `skills`); ruff clean; mypy clean (113 files) |
| Linux (`python:3.13`, pinned ICU volume, search engines mounted) | **5,143 passed, 0 failed, 97 skipped, 19 xfailed** |

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
