# Cross-Language Feasibility Matrix — `L12-D006`: a NUL-containing path fails as `unknown`

**Required by:** `process/agent-workflow.md` §4.1.1. This delta touches strings and paths at the Layer 12 seam and Layer 13 tools.
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`. **Author:** Claude. **Independent checkpoint reviewer:** Codex.
**Candidate:** the exact SHAs are on #194.

**Transitive path audited:**

```text
tool argument / ctx.fs caller
  -> resolvePath(cwd, path)   (lexical; the NUL is kept)
  -> fs.promises call(s)      (Node validates every path argument: ERR_INVALID_ARG_VALUE, no err.path)
  -> toFileError(e, fallback) (unknown + fallback)
  -> tool rendering           (Minion R010-B cause phrase; Pi raw message)
```

## 1. Runtime value-domain matrix

| Observable value / field | Pi wire/source repr | Pi runtime repr | Python repr | Rust repr | Canonical/wire serialization | Lossless across all? | Risk / witness needed |
|---|---|---|---|---|---|---|---|
| path argument containing U+0000 | JSON string | JS string | `str` | `String` / `OsString` (the L12-D001 projection) | `{utf16:[units]}` | YES. The operation sees the string unchanged | Canonical: 6 NUL positions |
| `file://` URL whose `%00` decodes to U+0000 (`L12D006-C001`) | URL string | the decoded string (Pi `resolvePath`, `fileURLToPath`) | `resolve_local_path` (L12-D001) | the same | `{file_url_tail}` | YES. Containment must test the **resolved** arguments | Canonical `url-*` cases, URL controls; control `argument-only-containment` |
| path argument with a lone surrogate **and** a NUL | JSON string (`\ud800`) | JS string | `str` (surrogatepass) | `JsString` (UTF-16) | units | YES for the error path, which is logical and never projected. The projection applies only to the native argument | Canonical `lone-surrogate-and-nul`; control `projected-fallback-path` |
| error `code` | `FileError.code` | `"unknown"` | `FsErrorCode.UNKNOWN` | `FsErrorCode::Unknown` | `error` | YES | Canonical: every case; control `nul-mapped-to-invalid` |
| error `path` (fallback) | — | the resolved logical string; the **source** for rename; absent for temp dir | `FsError.path` (`str` or `None`) | `Option<…>` | components or `null` | YES | Canonical (rename-destination); binding (temp) |
| `exists` result on a NUL path | — | `Err(unknown)` | `Err` | `Err` | error | YES | Canonical `*/exists` |
| side effect: parent created before the failing write | — | directory | directory | directory | follow-up `exists new` | YES | Canonical `under-new-parent/write_file`, `append_file`; control `premature-nul-validation` |
| message text | — | Node's message (`…without null bytes…`) | CPython's message | Rust's message | — | NOT_APPLICABLE | Messages are non-normative (§7 rule); tools render the cause phrase |

The other members of the JS-number family are NOT_APPLICABLE: no number is on the path.

### 1.1 Value-domain carriers

| Carrier | Pi repr | Python repr | Rust repr | Owning seam | Lossless across all? |
|---|---|---|---|---|---|
| RAW INPUT (tool arguments) | JS string | `str` | `String` | Layer 02/05 | YES. Unchanged |
| PREPARED / VALIDATED | — | — | — | Layer 06 | NOT_APPLICABLE. No change to argument values |
| SCHEMA | — | — | — | Layer 05 | NOT_APPLICABLE |
| TOOL RESULT (`content` text) | Pi raw message | the R010-B phrase (Minion mapping, certified) | the same | Layer 13 | YES within the certified mapping. The NUL-bearing path inside the text is carried unchanged |
| PERSISTENCE / PROVIDER | — | — | — | — | NOT_APPLICABLE. Unchanged |

**The Owner's six questions, for the `FsError` carrier:**
1. **Pi produces:** code `unknown` with the logical string, which may contain NUL and lone surrogates.
2. **Python:** yes, `str` with surrogatepass.
3. **Rust:** yes; the error path is a logical string.
4. **Hooks and events:** tools render it; events carry tool results.
5. **Serialization:** the result text is JSON-escaped like any string.
6. **Lossy projection allowed:** none in the error path. Only the native argument is projected (L12-D001).

## 2. Lower-layer capability matrix

| Required semantic operation | Owning lower layer | Existing certified seam/API | Expresses exact Pi semantics? | Python repr sufficient? | Rust repr sufficient? | New additive extension required? | Non-additive reopen required? |
|---|---|---|---|---|---|---|---|
| Detect a host rejection of a NUL argument at the native call | Layer 12 provider | none (the defect) | — | YES (`ValueError` "embedded null", plus a NUL in the argument) | YES (`std` `InvalidInput` from an interior NUL; distinct from other `InvalidInput`) | NO | YES. Owner-authorized (#65 + #133-F1) |
| Keep the logical fallback path | Layer 12 | `resolve_local_path` (logical) | YES | YES | YES | NO | covered by the same authorization |
| `realpath` validates its whole argument first | Layer 12 `canonical_path` | the component walk (Linux) | NO, before the fix | YES (a pre-check that mirrors `realpath`'s own argument validation) | to be audited by the Rust owner | NO | the same |
| Spawn with a NUL argument | Layer 12 `ctx.subprocess` | — | — | — | — | — | DEFERRED_WITH_REASON. Separate surface #195; Owner: do not bundle |

## 3. Cross-runtime hazard checklist

| Hazard | State | Evidence / reason |
|---|---|---|
| `JSON.parse` | NOT_APPLICABLE | Paths come in as strings; nothing is parsed on this path |
| `JSON.stringify` | NOT_APPLICABLE | No serialization on the path |
| `Number` conversion | NOT_APPLICABLE | No numbers |
| `Math` | NOT_APPLICABLE | — |
| negative zero | NOT_APPLICABLE | — |
| non-finite values | NOT_APPLICABLE | — |
| `String.length` / UTF-16 | AUDITED | The NUL is one code unit. Lone surrogates are carried in the logical error path (canonical, control) |
| `RegExp` | NOT_APPLICABLE | — |
| Unicode / ICU version | NOT_APPLICABLE | No normalization or collation; `ls` collation is not reached on an error |
| Array ordering | NOT_APPLICABLE | — |
| Object property ordering | NOT_APPLICABLE | — |
| Promise scheduling | NOT_APPLICABLE | The failing call is the same one Node's is; await order is unchanged |
| `AbortSignal` | AUDITED | Abort precedence: 8 canonical abort cases; `premature-nul-validation` killed by `nul/aborted/read_text_file` |
| timers | NOT_APPLICABLE | — |
| Node/libuv error mapping | AUDITED | `ERR_INVALID_ARG_VALUE` has no `err.path`, so `toFileError` gives `unknown` + fallback (oracle-asserted for the Minion-only operations) |
| filesystem access semantics | AUDITED | Side effects (parent creation) are observed by follow-up steps; `force` does not swallow the error |
| platform-specific path handling | AUDITED | Pi is identical on Windows and Linux (the generator enforces it). The Python Linux walk difference is a defect fixed here |
| external package / runtime versions | AUDITED | Node v22.15.1 on both platforms (`node:22.15.1-bookworm-slim`, Windows host) |

## 4. Concurrency / order matrix

| Operation | Start | Registration point | Lock acquisition | Await points | Abort checkpoints | Failure points | Settle point | Cleanup / release | Observable completion ordering |
|---|---|---|---|---|---|---|---|---|---|
| `write_file` / `append_file` | resolve | — | — | `mkdir(parent)`, write | before (both); after `mkdir` (`write_file`) | `mkdir` if the parent has the NUL, else the write | the result | — | the parent exists after a final-component NUL |
| `create_temp_file` | — | — | — | `mkdtemp`, write | — | the write | the result | the directory remains (Pi) | the directory exists |

| Ordering guarantee | Realistic wrong implementation | Witness that kills it |
|---|---|---|
| The NUL fails at the native call that receives it (no universal pre-check) | reject at entry | `premature-nul-validation`: `under-new-parent/write_file` (no `new/`), `read_text_lines-max0`, `aborted/read_text_file` |
| `canonical_path` rejects before walking components | walk first, so a missing earlier component gives `not_found` | `canonical-path-walks-first` (Linux) |
| Rename names the source | name the destination | `rename-names-the-destination` |

## 5. Neighborhood expansion record

| Family | Members probed | Pi observation source | New rows / findings |
|---|---|---|---|
| JS String/UTF-16 | NUL at 5 positions; NUL plus a lone surrogate | `characterization/pi-nul-probe.mjs`, `gen/pi_oracle.mjs` | the projected fallback (Windows Python) |
| Error/coercion projection | `toFileError` fallback, per operation | `nodejs.ts` | rename source; temp directory without a path |
| (subprocess) | `find`'s `spawn` | `find.ts:269` | #195 (DEFERRED_WITH_REASON) |

## 6. Verdict

```text
FEASIBILITY
    READY  -- every row AUDITED / NOT_APPLICABLE / DEFERRED_WITH_REASON; the one deferral (#195, the subprocess
              spawn surface) is outside the Owner's scope by direction.
```
