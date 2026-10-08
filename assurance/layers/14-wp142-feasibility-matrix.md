# Cross-Language Feasibility Matrix — WP-14.2: prompt assembly and model-visible skill/tool metadata

**Required by:** `process/agent-workflow.md` §4.1.1. The finding that called for it is `WP142-R001`.
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`. **Author:** Claude (shared contract).
**Independent checkpoint reviewer:** Codex.
**Owner decision:** WP142-R001 Option 1, recorded verbatim at `minion-agent#159`. The WP-14.2 string
domain is **Unicode scalar-value strings** (U+0000..U+D7FF, U+E000..U+10FFFF). Unpaired surrogates
are outside the supported domain: WP-14.2 makes no behavioural guarantee for them and adds no
rejection API. No lossy replacement, sanitization, surrogatepass encoding or carrier widening is
used. Layers 03, 07 and 08 are not reopened.

## 1. Runtime value-domain matrix

Every string here is a scalar-value string by the Owner decision. Pi's JS strings may also hold
unpaired surrogates. That behaviour is recorded only as out-of-domain characterization, in
`data/14-wp142/out-of-domain.json`.

| Observable value / field | Pi repr | Python repr | Rust repr | Canonical/wire | Lossless across all? | Witness |
|---|---|---|---|---|---|---|
| `Skill.name`, `.description`, `.content`, `.file_path` (WP-14.1 records, consumed) | JS string | `str` (scalar values: WP-14.1 HAR-013 "Strings") | `String` | JSON string | **YES** in the domain. WP-14.1 already guarantees scalar values (subset rule 1; `read_text_file`; Layer 12 path domain, `#133` exclusion) | canonical `b*`, `v*`, `c*` |
| `Skill.disable_model_invocation` | boolean (`truthy` filter) | `bool` | `bool` | JSON boolean | **YES**. The `not true` rule equals JS truthiness on the boolean domain; no wider mistyped input is claimed (Codex checkpoint 1) | `b05`, `b06`, `v93` |
| base prompt (`RunContext.system_prompt`) | JS string | `str` | `String` (`agent_loop/context.rs`) | JSON string | **YES** in the domain | `c*` |
| contributed sections | JS strings (`appendSystemPrompt`) | `str` | `String` | JSON strings | **YES** in the domain | `c02`, `c08`, `c11` |
| tool `prompt_snippet` / `prompt_guidelines` (Layer 05 additive fields) | JS strings | `str` / sequence of `str` | `String` / `Vec<String>` | JSON strings | **YES** in the domain | `t*` |
| `additional_instructions` (HAR-014) | JS string | `str` | `String` | JSON string | **YES** in the domain | `v91`, `v92` |
| assembled prompt (HAR-015 output) | JS string | `str` | `String` | JSON string | **YES** in the domain | `c*`; integration witnesses (§2) |
| invocation text (HAR-014 output) | JS string, persisted as user-message text | `str` → `TextBlock.text` | `String` → `TextBlock.text: String` | JSON string | **YES** in the domain | `v*`; invocation-message integration witness (§2) |
| lone surrogate in any of the above | representable | representable in `str`, but **not** storable (strict UTF-8 `ArtifactStore`) | **not representable** (`String`) | `\uD8xx` escape | **NO**, so outside the domain (Owner) | out-of-domain characterization only; preflight negative controls |

**UTF-16 code-unit semantics inside the domain.** These are the JS operations whose results depend
on code units:
- the HAR-014 `dirname` index rules: the last `/` or `\` and the `i == 2` drive check;
- JS `trim` and `\s` (the WhiteSpace and LineTerminator set);
- exact-string deduplication.

On scalar-value strings these are well-defined in both bindings:
- **Python:** encode to UTF-16 code units (the existing `_utf16` helpers) or reason on code points
  where the answer is the same. Separators and `:` are BMP, so an astral character before index 2
  shifts code-unit indices, and the binding must index in code units.
- **Rust:** `str::encode_utf16`.

Valid astral characters are preserved; canonical `b08`, `v94` and `c13` carry U+1F600.

### 1.1 Value-domain carriers

| Carrier | Pi repr | Python repr | Rust repr | Owning seam | Lossless across all? |
|---|---|---|---|---|---|
| RAW INPUT VALUE DOMAIN | — | — | — | not consumed | NOT_APPLICABLE: WP-14.2 consumes no provider tool-call arguments |
| PREPARED VALUE DOMAIN | — | — | — | not consumed | NOT_APPLICABLE |
| SCHEMA VALUE DOMAIN | tool schemas | unchanged | unchanged | Layer 05 | NOT_APPLICABLE: tool prompt metadata never enters schemas (HAR-018) |
| TOOL RESULT VALUE DOMAIN | — | — | — | not consumed | NOT_APPLICABLE |
| PERSISTENCE PROJECTION | session JSON | `ArtifactStore` (strict UTF-8, content-addressed) for header components; session log for invocation messages | the binding's equivalent stores | Layer 03 (`MINION-003`) | **YES** in the domain (UTF-8 is lossless for scalar values); unpaired surrogates excluded |
| PROVIDER PROJECTION | `Context.systemPrompt` string | `Request.system: str` | `LlmContext.system_prompt: Option<String>` | Layers 02/04/11 | **YES** in the domain |

## 2. Lower-layer capability matrix

| Required semantic operation | Owning lower layer | Existing certified seam | Exact Pi semantics? | Python sufficient? | Rust sufficient? | Additive extension? | Non-additive reopen? |
|---|---|---|---|---|---|---|---|
| prompt and schemas from one tool snapshot | Layer 08 | `L08-D001` optional prompt assembler (approved and merged) | MINION mapping | yes | yes (Codex contract review: a synchronous fallible collaborator over an ordered `Arc<ToolDefinition>` slice) | `L08-D001` (in implementation, `#166`) | no |
| record and reconstruct the assembled prompt | Layer 03 | `record_header` / `reconstruct_header`, `system_base` component | MINION | yes (scalar values) | yes | no | no |
| persist invocation text as a user message | Layers 03/07 | existing `TextBlock` user message, session log | Pi persisted-message shape | yes | yes | no | no |
| optional tool prompt metadata | Layer 05 | `ToolDefinition` | MINION extension (PP-14-5) | yes | yes | **yes**: two optional fields, additive and governed by PP-14-5 Option B | no |
| JS whitespace and trim sets | shared | `js_trim` (Python), the Rust equivalent | yes | yes | yes | no | no |

**Integration witnesses**, required by the Owner decision, item 8. They run through the real
driver, `ArtifactStore` and session log at implementation:
- **Header persistence and reconstruction:** a request assembled by the HAR-015 composer is recorded,
  and `reconstruct_header` yields byte-identical text, including an astral character.
- **Explicit invocation message text:** `format_skill_invocation` output is sent as a user message,
  persisted, reloaded from the log, and is byte-identical.
- **Exact model-visible prompt preservation:** the provider request's system text equals the composer
  output exactly, with no normalization on the way.

## 3. Cross-runtime hazard checklist

| Hazard | State | Evidence / reason |
|---|---|---|
| `JSON.parse` | AUDITED | Canonical documents are plain JSON strings. The normative preflight rejects unpaired surrogate escapes, so serde and Python agree (`WP142-R003`) |
| `JSON.stringify` | NOT_APPLICABLE | no numeric or `undefined` projection in WP-14.2 outputs |
| `Number` conversion | NOT_APPLICABLE | none |
| `Math` semantics | NOT_APPLICABLE | none |
| negative zero | NOT_APPLICABLE | none |
| non-finite values | NOT_APPLICABLE | none |
| `String.length` / UTF-16 code units | AUDITED | `dirname` indices in code units; preserved astral witnesses `b08`, `v94`, `c13`; lone surrogates excluded by the Owner |
| `RegExp` | AUDITED | Pi uses `/[\r\n]+/g` and `/\s+/g` (non-`u` mode). On scalar-value strings `\s` is exactly the WhiteSpace and LineTerminator set; witnesses `t05`, `t06` (U+2028, U+3000, U+FEFF, NBSP) |
| Unicode / ICU version | AUDITED | the `\s` membership is fixed by ECMA-262 for these code points; no case mapping or collation in WP-14.2 |
| Array ordering | AUDITED | input order kept (no sort); dedupe keeps the first occurrence (`b03`, `b04`, `t09`, `t15`, `t16`) |
| Object property ordering | AUDITED | Pi's `toolSnippets` record is read in selected-tool order, never key order; the Minion section iterates the snapshot |
| Promise scheduling | AUDITED | the assembly is synchronous (`L08-D001`); there are no awaits between the snapshot and the assembled text |
| `AbortSignal` | NOT_APPLICABLE | assembly is not cancellable and holds no resources |
| timers | NOT_APPLICABLE | none |
| Node/libuv error mapping | NOT_APPLICABLE | no filesystem operation in WP-14.2 |
| filesystem access | NOT_APPLICABLE | none (WP-14.1 owns discovery) |
| platform path handling | AUDITED | `location` and `dirname` treat the addressed path as text; Windows and POSIX spellings are covered (`b09`, `v08`..`v22`) |
| external package versions | NOT_APPLICABLE | no library at runtime; the oracles use pinned Pi source only |

## 4. Concurrency / order matrix

| Operation | Start | Registration point | Lock | Await points | Abort checkpoints | Failure points | Settle point | Cleanup | Observable ordering |
|---|---|---|---|---|---|---|---|---|---|
| assemble (per request) | request build in the driver (`L08-D001`) | the composer is installed on the driver | none | **none** | none | the composer raising or returning a non-string → `handleRunFailure` | the assembled text returned | none | before `record_header` and before the provider request |
| replace the prompt configuration | application | whole-value replacement | none | — | — | none | immediate | — | takes effect at the next request build that starts after it |
| mutate a retained skill record | application | — | none | — | — | — | — | — | visible from the next request build that starts after it |

**Concurrency model.** This answers checkpoint 1's note that synchrony is not a cross-thread
guarantee.
- **Where mutation may happen:** a retained record, or the configuration, may be mutated or
  replaced only from the execution context that drives the agent, **between** request builds:
  - Python: the agent's event-loop thread;
  - Rust: the configuration's owner, through `&mut` or by replacing an `Arc`ed value. Rust
    therefore expresses a record "mutation" as a replacement.
- **Why that is enough:** the assembly never awaits, so no other task on that context can run during
  it.
- **Outside the contract:** a mutation from another OS thread concurrent with an assembly. The
  contract makes no data-race or atomicity guarantee for it; this is declared, not inferred from
  synchrony.

| Ordering guarantee | Realistic wrong implementation | Witness that kills it |
|---|---|---|
| prompt and schemas from one snapshot | the composer reads the live registry | `L08-D001` kill control "live-registry assembly" (`#166`); the WP-14.2 driver witness |
| configuration replacement is atomic per request | reading `skills` and `sections` from different configuration values | WP-14.2 driver witness: replace mid-run and assert one value per request |
| assembly before publication | header recorded before assembly | `L08-D001` kill control "header published before assembly" |

## 5. Neighborhood expansion record

| Family | Members probed | Pi observation source | New rows / findings |
|---|---|---|---|
| F7 value-domain carriers | each consumed and emitted string carrier (§1, §1.1) | pinned harness and coding-agent source; Codex checkpoint 1 probes (`ArtifactStore`, Rust `String`) | `WP142-R001` → Owner decision (scalar-value domain) |
| UTF-16 / Unicode | lone high, lone low, valid pair, astral before a separator | `out-of-domain.json` (Pi); preflight controls | none open |
| text partitioning | blank lines inside guidelines | `tools-oracle.mjs` with `t14`..`t16`; the blank-line extractor control | `WP142-R002` fixed |

## 6. Verdict

```text
FEASIBILITY
    READY    every row AUDITED / NOT_APPLICABLE; WP142-R001 resolved by Owner decision (scalar-value
             domain); no open finding pending the contract re-review
```
