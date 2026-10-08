# Layer 14 WP-14.2 — Python implementation record

**Status:** Python candidate, for independent implementation review. Rust: NOT_IMPLEMENTED.
Cross-language: NOT CLOSED.

**Coordination:** `minion-agent#159`.

**Contract:** merged at code `622298f0` (`#167`) and docs `90a6ac16` (`#261`); approved by Codex
contract re-review 2.

**Owner authorizations** (`#159`):
- PP-14-4, PP-14-5 Option B, PP-14-9 Option A, WP142-R001 (scalar-value strings);
- implementation authorized conditionally on WP-14.1 and L08-D001 Python. Both are now approved
  and merged: `#161` → `97ec5687`, `#168` → `db63adcf`.

## 1. Candidate

**Package:** `minion-agent-python/src/minion_agent/system_prompt/`.

| Module | Contents |
|---|---|
| `formatting.py` | `HAR-002` `format_skills_block`; `HAR-014` `format_skill_invocation` (`dirname` on UTF-16 code units); `HAR-018` `normalize_snippet`, `normalize_guidelines`, `format_tools_section` |
| `composer.py` | `HAR-015` `compose_prompt`; `HAR-016` `PromptConfiguration` (whole value, membership copied, records shared) and `PromptComposer` (the `L08-D001` assembler) |

**Layer 05 additive fields:** `ToolDefinition.prompt_snippet: str | None` and
`prompt_guidelines: tuple[str, ...] | None`, both defaulting to `None`. They are metadata only, and
`schema()` is unchanged (witnessed).

**Layering:** `system_prompt` imports no session, telemetry, agent or `agent_loop` code. The driver
reaches it only through the generic `L08-D001` seam. The layering test gains this rule, and the
coverage source gains `system_prompt`.

**JS semantics:**
- the JS whitespace set is exactly what `js_trim` removes, reused per character;
- `dirname` indexes UTF-16 code units;
- the domain is scalar-value strings (WP142-R001).

## 2. Evidence

**Canonical:** `tests/conformance/test_prompt_assembly_conformance.py` runs the 66 documents. Each
first passes the schema's normative preflight (no unpaired surrogate). The thin runner only builds
records and calls the real functions. Result: **66/66 pass**.

**Unit witnesses** (`tests/system_prompt/test_formatting.py`):
- the UTF-16 `dirname` edge. Pinned Pi (Node v22.15.1, `data/14-wp141/pinned/skills.ts`) gives
  `😀:\b.md` → `😀:`, where a code-point implementation would give `😀:\`;
- the `disable_model_invocation` filter;
- snippet and guideline normalization edges;
- the empty section;
- cross-tool deduplication order;
- metadata never reaching the schema.

**Integration witnesses** (`tests/system_prompt/test_integration.py`), through the real
`AgentLoop`, header and session log, with the composer installed as the `L08-D001` assembler. These
cover Owner WP142-R001 item 8 and HAR-016:

| Witness | Shows |
|---|---|
| header persistence and reconstruction | an astral-character prompt reconstructs byte-identically |
| exact provider-visible prompt | equals `compose_prompt(...)` over the request's tool snapshot |
| persisted invocation message | survives the session log and reload, and is the provider's message text byte-for-byte |
| `read` gate and tools section | a `read` tool registered mid-run is in neither that run's prompt nor its schemas; the next run sees it in both |
| configuration replaced mid-run | applies whole at the next request, never mixed |
| retained-record mutation | visible from the next request |
| a supplied sequence mutated afterwards | changes nothing (membership copied) |
| the per-step override | bypasses the composer, and the header records the override |

**Kill controls** (`data/14-wp142/python-controls.py`, disposable copy). All 8 are valid kills,
exit 0, each by its intended witnesses:

| Mutant | Killed by |
|---|---|
| `&` escaped last | `b07` |
| case-insensitive `read` gate | `c12` |
| guidelines deduplicated per tool only | `t04`, `t08`, `t09`, `t16`, and the unit dedupe test |
| `dirname` on code points | the astral `dirname` witness |
| empty sections kept | `c01`, `c04`, `c05`, … |
| Pi's `(none)` line rendered | `t03`, `t08`, `t09`, … |
| configuration read once | the provider-prompt, mid-run replacement and record-mutation witnesses |
| skill records copied | the record-mutation witness |

**Gates (code `3456f88c`):**

| Platform | Result |
|---|---|
| Windows, pinned ICU 78.3 | **5,403 passed, 48 skipped, 21 xfailed**; coverage **100%** (9,246 statements, `system_prompt` included); ruff clean; mypy clean (116 files) |
| Linux (`python:3.13`, pinned ICU, search engines mounted) | **5,356 passed, 0 failed, 97 skipped, 19 xfailed** |

## 3. Limitations

- **Plugin sections:** there is no registration API for plugin-contributed sections. The
  `sections` list is application-supplied (contract HAR-016, "Not adopted").
- **Mutation model:** retained-record mutation and configuration replacement are supported from the
  agent's own execution context only (contract concurrency model).
- **Rust:** not implemented. It needs the Rust L08-D001 seam first.
