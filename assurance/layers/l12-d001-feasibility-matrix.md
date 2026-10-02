# Cross-Language Feasibility Matrix — `L12-D001`: filesystem path JavaScript-string domain

**Required by:** `process/agent-workflow.md` §4.1.1 and Owner decision FSP-Q001 §18 (`minion-agent#123` comment `5943405192`).
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`. **Author:** Claude. **Independent checkpoint reviewer:** Codex.
**Evidence:**
- authority `assurance/layers/data/l12-d001/`, from Pi's REAL harness `NodeExecutionEnv` plus `getMutationQueueKey`, Node v22.15.1, identical on Linux and Windows;
- characterization `fs-path-jsstring-scoping.md` §1–§9;
- spec `spec/execution.md` §14.

Rust is inspected **for feasibility only**; its type design is Rust-owned.

## 1. Runtime value-domain matrix (decision §18 grid)

The columns are the decision's dimensions. "Logical" means the JS string unchanged; "projected" means each unpaired surrogate is U+FFFD and pairs are kept.

| Dimension | Pi (observed) | Python today | Python with L12-D001 | Rust today | Rust required |
|---|---|---|---|---|---|
| logical JS path representation | JS String | `str` (lossless) | `str` (lossless) | `&str` (cannot hold) | lossless JS-string path |
| Layer-12 path parameter | string | `str` | `str` | `&str` | JS-string type |
| path preprocessing (§3.2, TOOL-026) | units unchanged | unchanged | unchanged | n/a (refused) | unchanged |
| native projection | at the fs binding, Linux = Windows | none (Linux: raises; Windows: raw passthrough) | `native_path` at every OS call | none | at the OS call only |
| `canonical_path` | projected | Linux raises; Windows raw | projected | n/a | projected |
| missing-path fallback | raw logical | (unreachable on Linux) | raw logical | n/a | raw logical |
| `target_key` existing / missing | projected / raw | — | projected / raw | n/a | projected / raw |
| directory listing names | projected | raw (Windows) | projected | n/a | projected |
| filesystem error path | projected (Node `err.path`) | — | projected (OS errors); logical (abort / non-OS) | n/a | the same split |
| tool-authored result text | path as given (logical) | logical | logical | refused / wrong target (`ls`) | logical |
| `file://` conversion | scalar-value input, then parse; invalid percent-encoding fails | raw surrogate raises | scalar-value input, then ada | `&str` | scalar-value input |
| platform differences | none observed (Linux, Windows); macOS DEFERRED | Linux ≠ Windows | none | — | none |

**Case coverage** (canonical corpus `conformance/agent/fs-path-domain/`, 56 `ctx.fs` + 5 tool cases):

| Decision §18 case | Covered by |
|---|---|
| ordinary BMP | `file/bmp`, `dir/bmp`, `missing/*/bmp` |
| valid astral pair | `*/pair`, `file-url/raw-pair`, `file-url/pct-astral`, `tools/pair` |
| lone high surrogate | `*/lone-high-{start,middle,end}`, `file-url/raw-lone-high` |
| lone low surrogate | `*/lone-low-{start,middle,end}`, `file-url/raw-lone-low` |
| mixed sequence | `*/mixed-pair-then-lone`, `*/low-then-high`, `file-url/raw-mixed`, `tools/mixed-pair-then-lone` |
| colliding high/low spellings | `alias/file`, `alias/dir` |
| explicit U+FFFD spelling | `*/explicit-fffd`, the alias C spelling, every read via the U+FFFD spelling, `file-url/pct-fffd` |
| directory-component surrogate | `dir/*`, `missing/dir/*`, `alias/dir`, `tools/*` |
| final-component surrogate | `file/*`, `missing/file/*`, `alias/file` |
| existing target | `file/*`, `dir/*` (after write), the alias post-write steps |
| missing target | `missing/*`, the alias pre-write steps |

### 1.1 Value-domain carriers (template §1.1)

| Carrier | Disposition |
|---|---|
| RAW INPUT VALUE DOMAIN | the source of the path string (`L0206-D002`, certified). NOT_APPLICABLE beyond that |
| PREPARED VALUE DOMAIN | `L0506-D002` (certified): the tools receive the prepared path. NOT_APPLICABLE beyond that |
| SCHEMA VALUE DOMAIN | NOT_APPLICABLE: no schema string is involved |
| TOOL RESULT VALUE DOMAIN | tool text interpolates the logical path; `L0506-D003` (certified) carries it losslessly |
| PERSISTENCE PROJECTION | NOT_APPLICABLE: no persistence on this seam |
| **FILESYSTEM PROJECTION** (this delta) | the native projection, at the OS call only |
| PROVIDER PROJECTION | NOT_APPLICABLE |

## 2. Lower-layer capability matrix

| Required semantic operation | Owning layer | Existing certified seam | Python sufficient? | Rust sufficient? | Additive extension? | Non-additive reopen? |
|---|---|---|---|---|---|---|
| accept a JS-string path at every `ctx.fs` operation | 12 | `FileSystem` protocol / trait | YES (`str`) | **NO** (`&str`) | YES: L12-D001 (a Rust path type) | no |
| native projection at the OS call | 12 | `LocalFileSystem` | **NO** (host codec) | **NO** | YES: L12-D001 | no |
| `target_key` (canonical, or fallback) | 12 (§4) | `resolve()` | YES once canonicalization sees the native path | needs the path type | inside L12-D001 | no |
| `file://` scalar-value input | 12 (§3.2) | `file_url_to_path` | **NO** (raises) | **NO** (`&str`) | YES: inside L12-D001, `L12-R002` unchanged | no |
| tools pass the path through | 13 | TOOL-026 pipeline | YES | **NO** (refuse; `ls` → `"."`) | mechanical consumption | no (WP-13.1/13.2 exclusions stand) |

## 3. Cross-runtime hazard checklist

| Hazard | State | Evidence / reason |
|---|---|---|
| `JSON.parse` | NOT_APPLICABLE | no decode on this seam |
| `JSON.stringify` | NOT_APPLICABLE | no serialization |
| `Number` conversion | NOT_APPLICABLE | none |
| `Math` semantics | NOT_APPLICABLE | none |
| negative zero | NOT_APPLICABLE | none |
| non-finite values | NOT_APPLICABLE | none |
| `String.length` / UTF-16 | AUDITED | paths observed as code units at every operation |
| `RegExp` | NOT_APPLICABLE | none in path handling |
| Unicode / ICU version | NOT_APPLICABLE | no normalization; Pi's NFD variant is `resolveReadPath`-only, not used by the harness seam |
| Array ordering | AUDITED | listings compared sorted by code units (enumeration order is EXEC-007 / Layer 13's) |
| Object property ordering | NOT_APPLICABLE | none |
| Promise scheduling | DEFERRED_WITH_REASON | the queue-key race of decision §8 is documented, not redesigned (the WP-13.2 queue is unchanged) |
| `AbortSignal` | AUDITED | the abort error path is logical (Pi `abortResult(signal, resolved)`); cancellation is unchanged |
| timers | NOT_APPLICABLE | none |
| Node/libuv error mapping | AUDITED | OS error path projected (Node `err.path`); §2.1 code mapping unchanged |
| filesystem access semantics | AUDITED | aliasing / overwrite / realpath across spellings (authority `alias/*`) |
| platform-specific path handling | AUDITED | Linux and Windows identical; macOS DEFERRED_WITH_REASON (decision §13) |
| external package / runtime versions | AUDITED | Node v22.15.1; Pi sources hash-pinned (`harness/pi_sources.sha256`); no npm dependency |

## 4. Concurrency / order matrix

NOT_APPLICABLE for new operations: L12-D001 changes no operation, lock or ordering. Its one ordering consequence is the §7/§8 queue-key rule:

| Ordering guarantee | Realistic wrong implementation | Witness that kills it |
|---|---|---|
| a missing target's key is the raw logical path; spellings differ | always-project-before-`target_key` | `missing/*` and `alias/*` target_key steps (34 cases fail) |
| an existing target's key is projected, shared by all spellings | never-project-before-`target_key` | `alias/*`, `file/*`, `dir/*` (18 cases fail) |

## 5. Neighborhood expansion record

| Family | Members probed | Source | Result |
|---|---|---|---|
| F7 carriers (filesystem projection) | 11 names × {final, directory} component × {existing, missing}; 3-spelling alias; 10 `file://` inputs | `l12_probe.mjs` (harness NodeExecutionEnv) | the §14 rule; `file_info` reports the logical name (a discriminating detail) |
| `file://` | raw high/low/pair/mixed; percent-encoded U+FFFD / astral / lone high / lone low / truncated / overlong | `url_probe.mjs`, `l12_probe.mjs` | scalar-value input; percent-encoded invalid sequences fail (literal at the seam, rejection at TOOL-026) |
| platforms | Linux, Windows | both | identical; macOS deferred |

## 6. Verdict

```text
FEASIBILITY
    READY for the contract checkpoint. Every row AUDITED / NOT_APPLICABLE / DEFERRED_WITH_REASON.
    The Python and Rust gaps are additive and inside the authorized delta. Deferred: macOS observation (decision
    section 13); the section-8 queue race (Pi parity, documented).
```

## 7. Addendum: contract review 1 (`L12-D001-R001`)

This addendum supersedes three rows above, which are kept as history: the "filesystem error path" row of §2, and the "Node/libuv error mapping" and "platform-specific path handling" rows of §3.

| Dimension | Pi (observed) | Python with L12-D001 (remediated) | Rust required |
|---|---|---|---|
| filesystem error path | the native path **of the native call that failed** (Node `err.path`): the recursive-`mkdir` walk position, a rename's source, otherwise the argument. Where Node's error names no path, the logical fallback: a read of a directory, a Windows append to a directory, `remove`'s directory refusal, abort | the same (`_node_mkdirp`; logical fallback for path-less failures) | the same; reproduce Node's walk |
| platform differences | path domain: none. Error origin: Node differs (walk position, codes); each platform is pinned | matches each platform, except the recorded code findings `#67` and `#125` | matches each platform |

| JS/runtime row | Status | Note |
|---|---|---|
| Node/libuv error mapping | AUDITED | `toFileError`'s path choice per failing call (§14.8). Node's recursive `mkdir` is audited at source (`node_file.cc` blob `49816349…`). §2.1 code mapping is unchanged; the code differences found are recorded (`#67`, `#125`) |
| platform-specific path handling | AUDITED | path domain: Linux = Windows. Error origin: per platform, from Node itself. macOS: DEFERRED_WITH_REASON |

**Neighborhood expansion (F7, error origin).**
- 39 failure programs × {ordinary, unpaired-surrogate} name, on both platforms (`r001/probe.mjs`).
- 33 programs per name are canonical (66 cases).
- The rest are already pinned elsewhere, or are the `#125` code (`l12-d001-contract.md` §7.3).

**Verdict.** READY for contract re-review. Every row is AUDITED, NOT_APPLICABLE or DEFERRED_WITH_REASON. The remediation stays inside the authorized additive delta: it specifies `FsError.path`, which no scalar certification had specified.
