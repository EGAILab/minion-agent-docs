# Cross-Language Feasibility Matrix — `WP-13.4`: `find`, `grep`

**Required by:** `process/agent-workflow.md` §4.1.1. `find` and `grep` cross the Layer 05/06 boundary, are string-, number- and path-heavy, delegate matching to external engines, and rest on Layer 12 seams.
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`, Node v22.15.1. **Author:** Claude. **Independent checkpoint reviewer:** Codex.
**Inputs:**
- characterization `13-wp134-search-characterization.md`, with its executable evidence in `data/13-wp134/`;
- the binding `TOOL-038` decision (#51 state block);
- Owner Q1–Q3 (#51 comment `5988502021`);
- the certified Layer 12 contract (`spec/execution.md` §§3, 6, 7, 11.4, 16) and the certified tool deltas `L0206-D002`, `L0506-D001`, `L0506-D002`, `L0506-D003`, `R003` and `TOOL-026`, read for representation only.

**Verdict (§6): FEASIBLE.** No lower-layer capability gap is open. One scoping rule (§2, "engine platform") is written into the contract. Every row is `AUDITED`, `NOT_APPLICABLE` or `DEFERRED_WITH_REASON`.

---

## 1. Runtime value-domain matrix

| Observable value / field | Pi wire/source repr | Pi runtime repr | Python repr | Rust repr | Canonical serialization | Lossless across all? | Risk / witness needed |
|---|---|---|---|---|---|---|---|
| `pattern` (`find`, `grep`), `glob` (`grep`) arguments | JSON string | JS string (unpaired surrogates possible, `L0206-D002`) | `str` (`L0206-D002` domain) | per `L0206-D002` | JSON string | **AUDITED**: the raw carrier is certified | — |
| `pattern` / `glob` / search path **on argv** | — | Node replaces every unpaired surrogate with U+FFFD before the OS boundary (characterized for `spawn` argv in WP-13.3, `WP133-AUD-R001`) | `subprocess` argv `str` would pass `D800` on Windows, or surrogateescape on POSIX | `&[String]` cannot hold one | child argv | **AUDITED, rule**: the scalar projection before argv, exactly as WP-13.3's `command` | lone high, lone low and reversed pair in `pattern` reach the engine as U+FFFD; a valid pair is kept |
| `path` | JSON string | `resolveToCwd` | `TOOL-026` pipeline | `TOOL-026` pipeline | — | **AUDITED**: the certified shared pipeline (`@` strip, `~`, Unicode spaces) | `@src`, an absolute path, `.` (characterized) |
| `limit` (`find`) | JSON number, optional | JS number; `limit ?? 1000`; `String(L)` on argv; `L`, `2L` in the notice | `float`/`int`, `None` | `Option<f64>` (`R003`) | argv text; notice text | **AUDITED**: `Number::toString` is the shared JS-number formatter (F1, WP-13.1 `ls`). `0` → `--max-results 0`, which is unlimited, plus Pi's "0 results" notice. `-1` and `2.5` → `fd` usage errors. `-0` → `"0"`. Overflowing JSON input (±Infinity, `L0506-D001`) → `"Infinity"` and an `fd` usage error | `0`, `-1`, `2.5`, `-0` and `1e999` cases |
| `limit` (`grep`) | JSON number, optional | `Math.max(1, limit ?? 100)` | as above | as above | notice text, `details.matchLimitReached` | **AUDITED**: `0`, `-1` → 1; `2.5` → 3 collected and a "2.5 ... limit=5" notice; `+Infinity` → never reached | characterized cases plus `1e999` |
| `context` (`grep`) | JSON number, optional | `context && context > 0 ? context : 0`; a JS-number loop | as above | as above | line labels | **AUDITED**: a fractional `C` gives fractional labels rendered with `Number::toString` (`ctx.txt-1.5-`) and `""` text (a non-integer index is absent). `-0`/negative → 0. `+Infinity` → the whole file | characterized `1.5` and `-1`; `-0` and `1e999` |
| `ignoreCase`, `literal` | JSON boolean, optional | JS truthiness | `bool`/`None` | `Option<bool>` | — | **AUDITED**: the schema admits only booleans; truthiness = `true` | — |
| engine stdout bytes → lines | raw bytes | Node `readline` over the default UTF-8 `StringDecoder`: WHATWG replacement; lines end at LF, CRLF **or CR** | incremental `utf-8` decoder with replacement plus a readline-equivalent splitter | the same | text | **AUDITED, rule** (spec `find` step 7) | a CR-only line from an engine (synthetic), invalid UTF-8 in an `fd` name (Linux `raw-name`) |
| `rg --json` events | NDJSON | `JSON.parse` per line; `data.path.text`, `data.line_number`, `data.lines.text`; the `bytes` variants leave `text` absent | `json.loads` | `serde_json` | — | **AUDITED**: integers are small, and no big-number or `__proto__` concern applies to the fields read. The **count/collect split** for an absent `text` is the rule | Linux `raw-name`: empty text |
| context file bytes → text | file bytes | `fs.readFile(p, "utf-8")`: WHATWG replacement, **BOM kept** | `read_binary_file` + `decode("utf-8", "replace")` (no BOM strip) | `read_binary_file` + `String::from_utf8_lossy` (maximal subparts, BOM kept) | text | **AUDITED** | `bom-context` (U+FEFF kept), `bad-utf8-context` |
| `truncateLine` | — | `line.length > 500` → `slice(0, 500)`, measured in **UTF-16 code units**, so a cut can split a surrogate pair | needs UTF-16 measurement (the WP-13.2 `_utf16` helpers) | needs UTF-16 measurement over a JS-string-capable text (`L0506-D003`) | result text | **AUDITED**: the result text may then hold a lone high surrogate, which `L0506-D003` (CERTIFIED_CLOSED) carries losslessly in both bindings | an astral character straddling code unit 500: `...` + lone `D83D` + `... [truncated]`; a line of 499 units plus a pair |
| result text, `details` | — | strings; `details` keys `resultLimitReached`/`matchLimitReached` (JS numbers, possibly fractional), `truncation` (`TruncationResult`), `linesTruncated` | per `L0506-D003` | per `L0506-D003` | JSON | **AUDITED**: the camelCase keys are Pi's verbatim, as bash does; `TruncationResult` is the certified `truncateHead` result | `details` equality, compared as a key set |
| relativized `find` entries | — | Node `path.relative` / `path.sep` for the **platform**; `win32.relative` is case-insensitive and returns the absolute `to` across drives | needs Node-exact `path.win32`/`posix` functions (`ntpath.relpath` differs) | the same | text | **AUDITED, rule** (spec "Path functions") | case-differing root on Windows; trailing separators (`/` and `\`); a **leading**-space basename is kept, because it is inside the absolute path and not at the trim boundary (` lead.ts`); a **trailing**-space collision gives a duplicate entry (`edges`, **revised `WP134-CON-R002`**) |

### 1.1 Value-domain carriers (F7)

| Carrier | Pi repr | Python repr | Rust repr | Owning seam | Lossless across all? |
|---|---|---|---|---|---|
| RAW INPUT VALUE DOMAIN | `JSON.parse` value | `L0206-D002` | `L0206-D002` | Layer 02 | **AUDITED** |
| PREPARED VALUE DOMAIN | the instance itself (no `prepareArguments`) | `L0506-D001`/`D002` | the same | Layer 06 | **AUDITED** |
| SCHEMA VALUE DOMAIN | TypeBox objects with ASCII names and no `const`/`enum`/`pattern` | dict | the same | Layer 05 | **AUDITED** |
| TOOL RESULT VALUE DOMAIN | text that may hold a lone surrogate (`truncateLine`); `details` with JS numbers | `L0506-D003` | `L0506-D003` | Layer 05/06 | **AUDITED** |
| PERSISTENCE PROJECTION | `JSON.stringify` | certified | certified | Layer 08 | **AUDITED** (no new kind) |
| PROVIDER PROJECTION | `sanitizeSurrogates` | Layer 11 | Layer 11 | Layer 11 | **NOT_APPLICABLE** here: the future-boundary obligation already recorded with `L0506-D003` |

## 2. Lower-layer capability matrix

| Required semantic operation | Owning lower layer | Existing certified seam/API | Expresses exact Pi semantics? | Python sufficient? | Rust sufficient? | New additive extension? | Non-additive reopen? |
|---|---|---|---|---|---|---|---|
| resolve `path` | Layer 13 (`TOOL-026`) | the shared path pipeline | yes | yes | yes | no | no |
| `.git` existence walk (`access F_OK`) (**revised, `WP134-CON-R001`**) | Layer 12 | WINDOWS: `ctx.fs.file_info` (§3, non-following); POSIX: `ctx.fs.probe_dir_entry` (§11.4, following). `Ok` means exists | yes: WP-13.3's `CE-WP133-01` mapping. A dangling junction exists on Windows, as `access` says (`edges` witness) | yes | yes | no | no |
| `grep` directory check (`fs.stat().isDirectory()`, following) | Layer 12 | `probe_dir_entry`: `directory` / `symlink_to_directory` | yes; any `Err` → "Path not found" | yes | yes | no | no |
| context re-read (`readFile utf-8`) | Layer 12 | `read_binary_file` + decode | yes (row above) | yes | yes | no | no |
| spawn the engine with argv; null stdin; piped stdout/stderr; inherited env | Layer 12 | `ctx.subprocess.spawn` (§6, `EXEC-010` §15) | yes | yes | yes | no | no |
| read until exit **and** EOF (Pi's `close`) | Layer 12 | `wait` + `read_chunk` to EOF; streams released with `close()` (§16) | yes: no idle grace, as WP-13.3's lookup | yes | yes | no | no |
| stop the engine on limit or abort (Pi `child.kill()`, SIGTERM to the direct child) | Layer 12 | `terminate()` (tree hard kill) | **AUDITED, equivalent**: neither engine traps signals or has children. Pi ignores the exit code when killed for the limit or on abort, so SIGTERM and hard kill are indistinguishable here. Not a divergence | yes | yes | no | no |
| verify the engine binary's hash at use time | Layer 12 + binding | `read_binary_file` of the store path + SHA-256 (`hashlib` / `sha2`, both present) | Minion rule (`DIV-003`) | yes | yes | no | no |
| engine platform identity | — | **local world only**: host OS and architecture (spec "Platforms") | Minion rule (`DIV-003`) | yes (`sys.platform`, `platform.machine()`) | yes (`cfg!(target_os, target_arch)`) | no: Layer 12 deliberately has no OS family or architecture; non-local worlds are NOT_CERTIFIED | no |
| explicit provisioning: download, verify, extract, atomic install | binding (installer operation, not a tool call) | — | Minion rule (`DIV-003`) | yes: stdlib `zipfile`, `tarfile`, `hashlib`; `httpx` already a dependency | yes: `reqwest` and `sha2` present; **zip and tar/gzip extraction crates to be added** (a binding dependency, Rust owner's choice) | no (binding-level) | no |

## 3. Cross-runtime hazard checklist

| Hazard | State | Evidence / reason |
|---|---|---|
| `JSON.parse` (number precision, duplicate keys, `__proto__`) | AUDITED | `rg` events: the fields read are a small integer and strings; NDJSON from a pinned engine |
| `JSON.stringify` | AUDITED | `details` follow `L0506-D003`; no new kind |
| `Number` conversion / numeric coercion | AUDITED | `String(L)` on argv, and notices through `Number::toString` (§1) |
| `Math` semantics | AUDITED | `Math.max(1, x)` (`NaN` is unreachable from JSON; ±Infinity covered); `Math.min`/`max` for context bounds over JS numbers |
| negative zero | AUDITED | `-0` limit → `"0"`; `-0` context is falsy |
| non-finite values | AUDITED | `1e999` → `+Infinity` for `limit` and `context` (§1); witnesses required |
| `String.length` / UTF-16 code units | AUDITED | `truncateLine`; the result domain is `L0506-D003` |
| `RegExp` | AUDITED | the wrapper uses only literal-class replaces (`\r\n`, `\r`, `\n$`, `^`-less) with no flags beyond `g`; the search regex is `rg`'s (delegated) |
| Unicode / ICU version | AUDITED | the wrapper uses ECMAScript `trim()` (the shared `js_trim`), with no case mapping; engine case folding (`--ignore-case`, `fd` smart case) is delegated to the pinned engines |
| Array ordering | AUDITED | no sort anywhere (Owner Q2); per-file order is the engine's |
| Object property ordering | AUDITED | `details` compared as a key set (K1) |
| Promise scheduling | AUDITED | `grep` formats after `close`, sequentially (one awaited read per uncached file); `find` settles on `close`; no observable interleaving |
| `AbortSignal` | AUDITED | `find`: an abort settles immediately and kills the child; `grep`: kills, then settles on `close`; both pre-check; `find` re-checks after engine resolution |
| timers | NOT_APPLICABLE | neither tool has a timer |
| Node/libuv error mapping | AUDITED, mapping | the spawn failure is `Failed to run fd: <cause>`, with the Layer-12 spawn error message as `<cause>` (Pi uses Node's `error.message`). It is unreachable on the certified path except in a provisioning race. Engine stderr is verbatim, from the pinned engine |
| filesystem access semantics | AUDITED | following probes (§2); neither engine follows symlinks (characterized) |
| platform-specific path handling | AUDITED | Node `path.win32`/`posix` (§1); Windows `[/\\]` acceptance and `DIV-002`; native separators in engine error text (F-6) |
| external package / runtime versions | AUDITED | `fd 10.4.2` and `ripgrep 15.2.0`, artifact and binary SHA-256 (`engines.json`); verified at use time (`DIV-003`) |

## 4. Concurrency / order matrix

| Operation | Start | Registration point | Lock acquisition | Await points | Abort checkpoints | Failure points | Settle point | Cleanup / release | Observable completion ordering |
|---|---|---|---|---|---|---|---|---|---|
| `find` | execute | the abort listener, before any await | none (no queue) | engine resolution; each `.git` probe; spawn; exit + EOF | pre-check; after engine resolution; listener (immediate settle); after `close` | engine unavailable; `fd` exit ≠ 0 with empty output; spawn | `close`, or the abort listener | terminate on abort; `close()` streams | engine order (unspecified) |
| `grep` | execute | the abort listener, after spawn | none | engine resolution; directory probe; spawn; exit + EOF; one read per uncached file | pre-check; listener (kill); after `close` | engine unavailable; path not found; exit ∉ {0, 1} unless killed for the limit; spawn | after `close` and formatting | terminate on limit or abort; `close()` streams | per-file contiguous, ascending lines; files unspecified |

| Ordering guarantee | Realistic wrong implementation | Witness that kills it |
|---|---|---|
| `grep` checks the engine before the path | path first | missing path with an unprovisioned engine gives the engine text |
| a `find` abort settles at once | waiting for `close` | an abort with a slow `fd` (a held process) settles before exit |
| collection stops at `L`, and the count includes uncollected matches | counting only collected matches | Linux `raw-name` gives empty text, not "No matches found" |
| formatting happens after the engine exits; blocks are never merged | merged windows / streaming formatting | `context-overlap` |
| an exit code is ignored when killed for the limit | treating the kill as an error | `limit-3` on many matches |
| notices in Pi's order | reordered notices | bulk limits + truncation + `linesTruncated` |
| no sort (**revised, `WP134-CON-R003`**) | a sort flag; a post-collection sort; deduplication | the recording-argv witness (sort flags); the scripted unsorted-stream witness (`z.ts` then `a.ts`, compared exactly); the trailing-space duplicate plus multiset comparison (deduplication) |

## 5. Neighborhood expansion record

| Family | Members probed | Pi observation source | New rows / findings |
|---|---|---|---|
| F1 JS Number | `0`, `-1`, `2.5` (both limits), `1.5`, `-1` (context); `-0`, `1e999` added as witnesses | `search_probe.mjs` | §1 rows; F-4 |
| F2 JS String/UTF-16 | `truncateLine` cut at 500; lone surrogate in `pattern` | `truncate.ts`; WP-13.3 argv projection | §1 rows (witnesses required) |
| F3 Unicode | Unicode names and directories, `café`/`CAFÉ` ignore-case, smart case, BOM, invalid UTF-8, non-UTF-8 name | `search_probe.mjs` | F-4; BOM/raw-name rules |
| F4 Async/order | abort pre/during/after; limit kill; formatting after close | `find.ts`/`grep.ts` | §4 |
| F5 Error projection | `fd`/`rg` stderr, Pi texts, Minion `DIV-003` texts | probe; spec table | errors table |
| F6 Object order | `details` keys | — | key-set comparison |
| F7 Value domains | §1.1 | — | — |

## 6. Verdict

```text
FEASIBILITY
    READY    every row AUDITED / NOT_APPLICABLE / DEFERRED_WITH_REASON; no open finding.
             Binding-level note: Rust adds archive-extraction crates for provisioning only (DIV-003 scope).
```
