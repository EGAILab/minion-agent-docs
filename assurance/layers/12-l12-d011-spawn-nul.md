# L12-D011 — a NUL-containing spawn input fails with pinned Node's literal diagnostic

Status: **contract APPROVED for implementation** (Codex review 3, #224 issuecomment-6145618255) and merged (code #225 → `be02f9f3`, docs #301 → `a080af46`). **Python: implementation candidate, remediation 1** (§9), for independent implementation review 2. Rust: NOT_IMPLEMENTED. Cross-language: NOT CLOSED. *(Earlier status: implementation candidate §8; implementation review 1 CHANGES REQUESTED; earlier still: contract draft, revision 1.)*
Coordination: `minion-agent#224`. Provenance: `#195`. Requirements: `EXEC-013` (new); `EXEC-005`, `TOOL-034`, `TOOL-036`, `TOOL-037`.

**Owner decisions** (each recorded verbatim on the issue):
- `#195` issuecomment-6137514688 (sha256 `3d2cd6ce8473babd72d12b5cd92032de6ab4332f7c43a950508376a11300ddf6`): APPROVE OPTION 1, PINNED PI LITERAL NUL-SPAWN DIAGNOSTIC.
- `#224` issuecomment-6137796390 (sha256 `3b4d4f0ab37fd76f5abac79b94ca0efdf4d0fc3c608fb6610ca4469483b2f0d2`): APPROVE OPTION 1, VALIDATE ALL RETAINED ENTRIES (the Windows case-collision boundary).
- `#224` issuecomment-6141307443:
  - F2: APPROVE OPTION 1, OVERLAY-FIRST POSIX ENVIRONMENT ORDER;
  - C003: APPROVE OPTION 1, VALIDATE EFFECTIVE RESOLVED CWD.

**Normative contract:** `spec/execution.md` §21. Manifest: `EXEC-013`. Canonical: `conformance/agent/spawn-nul/spawn-nul.json`.

## 1. Authority and characterization

- **Pins:** Node v22.15.1, read at tag `v22.15.1` and cited by **symbol** (review 1 found line citations unreliable):
  - `lib/child_process.js` `normalizeSpawnArguments`, `validateArgumentNullCheck`, `validateArgumentsNullCheck`;
  - `lib/internal/errors.js` `E('ERR_INVALID_ARG_VALUE', …)`;
  - `lib/internal/util/inspect.js` `inspectDefaultOptions`, `meta`, `addQuotes`, `strEscape`, `formatPrimitive`;
  - `lib/internal/fs/utils.js` `getValidatedPath`, for the `options.cwd` reason text.
- **Pinned Pi** `b7bb00b9`:
  - `coding-agent/src/core/tools/find.ts` (`spawn(fdPath, args, …)`, in `execute`'s `try`);
  - `grep.ts` (`spawn(rgPath, args, …)`, whose `catch (err)` rejects with `err`);
  - `bash.ts` (`createLocalBashOperations` `exec`: `spawn(shellConfig.shell, […shellConfig.args, command])`);
  - `agent/src/harness/env/nodejs.ts` `resolvePath` (the effective cwd).

**Measured** in two host windows granted by Codex, Windows then Linux (the `python:3.13` image, Node 22.15.1 linux-x64). The probes and raw outputs are in `data/l12-d011/characterization/`. 38 pinned rows and 12 Minion-Python rows were measured on each platform, and no NUL case started a process. The results are summarized on #224 (issuecomment-6137690586):

- **Message:** the message, kind, names and `cwd` reason text match §21.2.
- **Precedence:** `file`, then `args` in order (first invalid only), then `options.cwd`, then `options.argv0` (unused by Minion), then the environment, name before value.
- **Environment order:**
  - Windows sorts by UTF-16 code unit and drops `toUpperCase` duplicates, keeping the first: `A` beats `Z`, `10` beats `2`, `K` beats `k`;
  - Linux uses ECMAScript property order: `2` before `10` before `Z`, and `k` before `K` when `k` was inserted first.
- **Inspect:** every rule in §21.2 was observed on both platforms, including NBSP kept, the backtick choice, the `' +\n  '` split, the 127/128/129 boundary, a surrogate pair cut at 128, and the 10000-unit trailer.
- **Tools:** `find` pattern `args[7]` and path `args[8]`; `bash` command `args[1]`.
  - On Windows, the path in a `find` message is the resolved native path, with its backslashes escaped.
  - Pre-aborted: the pipeline answers `Operation aborted`, as already certified.
- **Minion Python today:** `LocalSubprocess.spawn` raises `ValueError` for a NUL in the file, argv, cwd, an environment name or an environment value. The text is `embedded null character` on Windows and `embedded null byte` on Linux. The tools surface that text through the pipeline catch-all (`tools/execute.py:844`).
- **Minion Rust today** (read only): `Command::spawn` returns `InvalidInput`, which becomes `spawn_error` with the OS text. `find` and `grep` add `Failed to run fd:` / `Failed to run ripgrep:`, and `bash` its start-failure text.
- **`grep` is included in scope.** Its pattern and glob reach `rg`'s argv, and Pi surfaces the throw (`grep.ts:369`). #195 noted only that `grep`'s NUL **path** fails earlier, at the directory probe. The same rule therefore applies to `grep`.

## 2. Contract summary

See `spec/execution.md` §21. In brief:
- the rule (21.1);
- the diagnostic and the `inspect` subset (21.2);
- the effective-environment order (21.3);
- the Windows collision boundary (21.4);
- the tool boundary with its narrow distinction (21.5);
- what is unchanged (21.6);
- the evidence (21.7).

**Scope:**
- **The effective cwd** is checked, by Owner decision C003 (§21.1). It is the same pre-spawn surface, with Node's own reason text. At tool level a NUL cwd is rejected earlier, by the existing checks.
- **`grep`** is included, as described in §1. Review 1 found this coherent: the same spawn rejection seam, with its earlier path probe unchanged.

## 3. Cross-language feasibility matrix (kit template, WORKFLOW §4.1.1)

Pinned Pi `b7bb00b9`. Author: Claude. Independent checkpoint reviewer: Codex.

### 3.1 Runtime value-domain matrix

The carrier audit covers every input the check reads: argv, the effective cwd, environment names and values, and the diagnostic carried to the tool result (review 1).

| Value | Pi runtime | Python | Rust today | Canonical | Lossless? | Witness |
|---|---|---|---|---|---|---|
| spawn `file` / `args[j]` | JS string (UTF-16; lone surrogates possible from tool input) | `str` (lone surrogates representable) | seam argv `&[String]` (scalar only); tool inputs are `JsString` but projected by `to_utf8_lossy` **before** spawning | `{"utf16": …}` | **NO for Rust today, F1**; mapping in §3.6 | `fmt/lone-*`, `len/surrogate-pair-straddles-128` |
| effective cwd (supplied raw → resolved; or the provider default) | JS string through `resolvePath` | `str` | `Option<PathBuf>` raw, then `resolved_cwd` (`PathBuf`) | `{"utf16": …}` per platform | **NO for Rust today, F1** (a lone surrogate in a resolved cwd); mapping in §3.6 | `cwd/unicode-lossless` |
| env name / value | own properties of a JS object | `dict[str, str]` (insertion order kept; lone surrogates representable) | `BTreeMap<String, String>` (scalar; caller insertion order **lost**) | ordered `[[name, value], …]` | **NO for Rust today**: values F1, order F2 | `env/order-*`, `env/collision-*`, `env/proto-name-own-property` |
| diagnostic message | JS string; may hold a raw NUL (in a name) and a lone high surrogate (the 128 cut) | `str` | `SubprocessError.message: String` | `{"utf16": …}` | **NO for Rust today, F1** | `len/surrogate-pair-straddles-128`, `env/name` |
| tool error result text | JS string | `str` | `ToolCapabilityError.message` is a lossless **`ResultString`**, as is the result text (review 1 corrected this row) | `{"utf16": …}` | **YES** once the diagnostic reaches it losslessly | tool cases |

The other items in the template's checklist:
- **NOT_APPLICABLE**, with no numeric values on this surface: binary64, ±0, ±Infinity, NaN, the 2^53 boundary, `JSON.stringify` projection.
- **AUDITED:** undefined/null (`cwd` null = not supplied, so the provider default; `baseline` null = the live baseline; `env` null = no overlay); UTF-16 code units; a valid pair; lone high and low surrogates.
- **NOT_APPLICABLE:** Unicode normalization and Unicode version. No case mapping is involved, because §21.4 performs no arbitration; the §15.5 consumer arbitration is unchanged and already certified.

**Value-domain carriers:**
- **RAW INPUT** (tool arguments): JS string, Python `str`, Rust `JsString`. Lossless.
- **PREPARED:** the same.
- **SCHEMA:** NOT_APPLICABLE, since no schema change is involved.
- **TOOL RESULT:** lossless in every binding (`ResultString` in Rust), provided the diagnostic reaches it losslessly. That is F1's mapping.
- **PERSISTENCE / PROVIDER:** the existing projections are unchanged.

**Canonical-case audit:** every string is `{"utf16": …}`. The cases outside the scalar domain are:
- the two lone-surrogate formatting cases;
- `cwd/unicode-lossless`;
- the straddle case's expected message.

Rust runs them through the lossless entry point in §3.6.

### 3.2 Lower-layer capability matrix

| Operation | Lower layer | Certified seam | Exact Pi semantics? | Python sufficient? | Rust sufficient? | Additive extension? | Reopen? |
|---|---|---|---|---|---|---|---|
| pre-spawn NUL check with Node's message | EXEC-005 / new EXEC-013 | `ctx.subprocess.spawn` → `Err(spawn_error)` | yes, through the existing `spawn_error` code with the specified message | yes | via the additive lossless entry point (F1) | **yes, additive for Rust** (F1); none for Python | none |
| effective cwd check | EXEC-005 §6 (`absolute_path`'s `resolvePath`) | the existing resolver | yes for supplied cwds (Pi's resolver); a Minion mapping for the provider default (Owner C003) | yes | via F1's lossless cwd | the same additive entry point | none (the resolver is unchanged) |
| tool-level passthrough without the wrapper | Layer 13 (TOOL-034/036/037) | tool `execute` and the engine spawn | yes | a binding-internal mark on the error (§21.5) | the typed rejection mark, then `ToolCapabilityError` with the `ResultString` diagnostic | none beyond F1 | no |
| effective-environment check order | EXEC-005 / EXEC-010 / §15.3 | the composed environment | Windows: Owner retained-entry rule; POSIX: Owner F2 overlay-first rule (§21.3), deterministic and independent of snapshot order | yes (dict order; explicit UTF-16 sort key; integer-index test) | an ordered overlay carrier, additive and shared with F1; the legacy `BTreeMap` stays with its map order disclosed | **yes, additive for Rust** | none (Owner F2: §15.3 preserved) |

### 3.3 Cross-runtime hazard checklist

| Hazard | State | Evidence / reason |
|---|---|---|
| `JSON.parse` | NOT_APPLICABLE | no JSON on the surface; canonical strings are code-unit arrays |
| `JSON.stringify` | NOT_APPLICABLE | the same |
| `Number` conversion | NOT_APPLICABLE | the only numbers are lengths and indices, all integers |
| `Math` semantics | NOT_APPLICABLE | none |
| negative zero | NOT_APPLICABLE | none |
| non-finite | NOT_APPLICABLE | none |
| `String.length` / UTF-16 | AUDITED | the 128 cut, the 76 / 16 / 10000 thresholds and `N` are all in code units (§21.2); `len/*` cases |
| `RegExp` | AUDITED | `strEscape` regex and loop paths; `fmt/over-100-*` prove they agree |
| Unicode / ICU version | NOT_APPLICABLE | no case mapping in §21; §15.5 is unchanged |
| Array ordering | AUDITED | Windows sorts names by UTF-16 code units (JS default sort); Python and Rust need an explicit UTF-16 key |
| Object property ordering | AUDITED | Node's own POSIX selection follows JS insertion history. Minion's order is Owner F2's deterministic mapping (§21.3): `env/order-integer-index-names`, `env/order-non-index-controls`, both baseline presentations, overlay ownership, and `env/proto-name-own-property` (environment objects are built with own properties only) |
| Promise scheduling | NOT_APPLICABLE | Node's throw is synchronous; Minion's check precedes any await on the native spawn |
| `AbortSignal` | AUDITED | pre-abort precedes the check (`abort/pre-aborted-before-nul`, `abort/pre-aborted-before-cwd`; the tool-level pipeline controls) |
| timers | NOT_APPLICABLE | none |
| Node/libuv error mapping | AUDITED | `ERR_INVALID_ARG_VALUE` text; the non-NUL `ENOENT` control keeps the OS text |
| filesystem access semantics | NOT_APPLICABLE | the check precedes any filesystem access by `spawn` |
| URL / path resolution | AUDITED | the effective cwd uses pinned Pi `resolvePath` (`file://` decoding once, the malformed-URL literal fallback, lexical resolution): `cwd/*` cases |
| platform path handling | AUDITED | `find`'s resolved Windows path is escaped (`tool/find/nul-absolute-search-path` uses a short absolute path per platform for a deterministic cut) |
| external package versions | AUDITED | Node 22.15.1, Pi `b7bb00b9`, fd 10.4.2, ripgrep 15.2.0 (TOOL-038 pins) |

### 3.4 Concurrency / order matrix

`spawn`:
1. start;
2. abort check (`Err(aborted)`);
3. **the NUL check, synchronous, before any native call**;
4. the native spawn.

No lock, no await between 2 and 4, and no cleanup, since nothing is created.

| Ordering guarantee | Realistic wrong implementation | Witness that kills it |
|---|---|---|
| the NUL check before any native spawn | checking after `create_subprocess_exec` / `Command::spawn` raises (catch-and-map) | the spy at the native spawn: zero calls |
| the abort before the NUL check | the NUL check first | `abort/pre-aborted-before-nul` |
| file → args → cwd → env | checking the env first, or the args after cwd | the `precedence/*` cases |
| the first invalid argument wins | the last, or all joined | `precedence/args-first-invalid-wins` |
| name before value | value first | `env/name-before-value-same-entry` |
| the resolved, not raw, cwd | checking the raw string (misses `%00`, false-positive on nothing); decoding twice (`%2500`) | `cwd/file-url-percent-00`, `cwd/file-url-percent-2500-control` |
| the provider default is checked | checking only a supplied cwd | `cwd/provider-default-nul` |
| overlay-first POSIX order | baseline-first; sort-all; naive integer detection; reporting a superseded baseline value | the `env/order-*` cases; `env/superseded-baseline-value-control`; the merge self-test controls |
| the tool passes the raw diagnostic | keeping `Failed to run fd:` | the tool cases |
| a narrow tool distinction | string-matching `"The argument"`, which mislabels a genuine engine message | binding witness: a non-NUL spawn failure whose OS text starts with "The " still gets the wrapper |

### 3.5 Neighborhood expansion record

| Family | Members probed | Source | New rows / findings |
|---|---|---|---|
| F2-like value domains (UTF-16) | lone high, lone low, pair, BMP, a straddle at the cut | the probe and generator | F1 |
| F3 Unicode / case | case-colliding env names on Windows | the probe (`env-case-dupe-win`) | Owner decision on #224 |
| F5 ordering | env order on both platforms, integer-like names | the probe | F2 |
| F7 carriers | argv, cwd, env, message, tool text | source reading | F1, F2 |

### 3.6 Verdict

```text
FEASIBILITY (revision 1)
    READY FOR RE-REVIEW, pending Codex's independent check of the mappings below:
      L12D011-F1 (open, mapping recorded): an additive lossless spawn entry point in Rust.
        The request carries argv, the supplied cwd and the ordered env overlay as JsString
        (javascript::JsString / the prepared-string vocabulary).
        The existing `spawn(&[String], SpawnOptions)` forwards to it: String -> JsString is exact,
        and the BTreeMap overlay is taken in its map order.
        One validator checks the logical units BEFORE the §15.5 "Strings to OS" projection,
        including the cwd resolved by the certified resolver.
        A rejection is SubprocessError(spawn_error) carrying:
          - a lossless diagnostic (UTF-16; no new message semantics), and
          - a narrow typed rejection mark.
        Tools assemble their argv as JsString, call the lossless entry point, and on the typed
        rejection return ToolCapabilityError with the diagnostic as its ResultString. Every other
        spawn failure keeps its wrapper. Filesystem and shell errors are not changed.
        Python: str already carries every value; the same single validator and typed mark.
        Witnesses: exact-unit diagnostics, plus an unrelated-InvalidInput control.
      L12D011-F2 (open, Owner-resolved): Owner decision #224 6141307443.
        §21.3 is the POSIX overlay-first order; §15.3 is preserved.
        Rust: the ordered overlay carrier of F1; the legacy BTreeMap order is disclosed, not
        claimed as insertion order.
        Witnesses: the env/order cases, plus Rust ordered-vs-legacy carrier witnesses.
    No non-additive reopen is required.
```

## 4. Evidence plan

- **Generation:** `data/l12-d011/gen/`, run by `run-gen.mjs`:
  - `spawn_nul_cases.mjs` holds the single input definition;
  - `gen_spawn_nul.mjs` runs on each platform. It records Node's literal diagnostic for each NUL input **in isolation**, the effective cwd through pinned Pi's `resolvePath`, and Node's own whole-call outcome; it runs Pi's sliced `find`, `grep` and `bash`;
  - `merge_spawn_nul.mjs` applies the §21.1/§21.3 selection and writes `conformance/agent/spawn-nul/spawn-nul.json`. Its `--self-test` holds the C002 and F2 controls.
- **Containment (C001):** every computed write is in `io.mjs`, behind the reviewed fs-guard (`../l12-d007/fs-guard`): `makeRun`, `writeOutput`, and `transfer`, the container's one host-bound write to `/out`. Every other container write is a fixed private-tmpfs literal. `containment-controls.mjs` runs those exact statements with mutations intercepted, and mechanically inventories every `gen/` script, shell included (§6, §7).
- **Canonical runners:** both bindings get a thin `spawn-nul` runner. It constructs the real provider (`provider_cwd`, and the configured `baseline` as a fixture), calls the real `spawn` once or the real tool through the pipeline, and compares.
- **Binding witnesses:** listed in spec §21.7.
- **Negative controls:** the §3.4 wrong implementations.

## 5. History

- 2026-10-13: #195 characterized and the options packet posted. The Owner decided Option 1, and #224 was opened.
- Characterized on Windows and Linux. The Owner decided the Windows collision boundary.
- This contract draft written.
- Contract candidate 1: code #225 `064e0214` / docs #301 `030da24f`.
- 2026-10-13: independent contract review 1 (Codex, issuecomment-6139260011): CHANGES REQUESTED, findings F1, F2, C001, C002 and C003. The Owner decided F2 and C003 (issuecomment-6141307443). Revision 1 follows (§6).

## 6. Review 1 and revision 1

Review 1 (issuecomment-6139260011) is accepted in full.

- **L12D011-C001, containment.**
  - Every computed mutation of the launcher, the generator and the merge now lives in `gen/io.mjs`. Each one immediately follows the reviewed fs-guard proof:
    - `makeRun`: one plain name component, then `makeSandbox`'s ancestry proof **before** its mkdir, then `assertInside` for `cwd/`;
    - `writeOutput`: `assertOutput` on the **final** output entry, immediately before the write.
  - `run-gen.mjs`, which replaces `run-gen.ps1`, proves every Docker bind source with `proveReferentAbs`.
  - The container writes only fixed literal paths in its private tmpfs, with the guard rooted at `/tmp/guard-root`.
  - `containment-controls.mjs` runs the real statements with mkdir and write intercepted and the inspections steered in memory. These are refused with **zero** mutation attempts:
    - names `../escape`, `a/../../b`, `/abs`, `C:x`, `\\srv\share`, `a\b` and the empty name;
    - an outward-link ancestor and an inspection-failure ancestor;
    - an escaping output tail, a foreign absolute output, an outward **final** output entry and an inspection-failure parent.
  - A legitimate output makes exactly one attempt, and nothing is written natively.
  - Both proof-removed mutants are caught, and a static check confirms no generation script mutates the filesystem outside `io.mjs`. 20/20 pass.
  - The four characterization scripts are kept as the historical record of what ran once, but now begin with a hard stop.
- **L12D011-C002, contrast attribution.**
  - The merge validates each raw Node observation: either a diagnostic, or an asynchronous error **with** a code. Anything else is rejected.
  - Node's contrast now records exactly what Node did: "node passed NUL validation and failed asynchronously with ENOENT", or "node selected a different input: …". It is never "spawned".
  - `merge_spawn_nul.mjs --self-test` checks that:
    - a fabricated `spawned` or `started` outcome is rejected, and so is an async error without a code;
    - an ENOENT is attributed as such.
  - The Minion expectation for the collision cases is unchanged.
- **L12D011-C003, effective cwd** (Owner decision): see §21.1.
  - The resolved effective cwd, or the provider default, is checked after `args` and before the environment.
  - Its received value is the resolved logical path.
  - New cases cover literal relative and absolute cwds, `%00`, the `%2500` control, the malformed-URL fallback, a NUL provider default and a normal one, Unicode, and the precedence pairs including pre-abort.
- **L12D011-F2** (Owner decision): §21.3 is the overlay-first POSIX order, preserving §15.3.
  - Overlay-owned names are checked with their effective value.
  - New cases: both overlay orders, both baseline presentations of identical entries (review 1's witness), overlays of baseline names, baseline-only names in both presentations, mixed, integer-index names `2` and `10`, the `01` / `4294967295` controls, UTF-16-versus-UTF-8 names, and the superseded-value control.
  - The merge self-test also kills baseline-first ordering, sort-all ordering and naive integer detection.
- **L12D011-F1:** the end-to-end lossless mapping is recorded (§3.6), following review 1's proposal. The Rust tool text row is corrected to `ResultString`.
- **Non-blocking items:**
  - citations are now by symbol;
  - the bash `-c` transport assumption is stated in §21.5, with a stdin-transport binding witness;
  - environment objects in the generator are built with own properties only, plus the `__proto__` case.
- **Canonical regeneration.** It ran in two Owner/Codex-coordinated host windows, into new contained run dirs, through `run-gen.mjs`.
  - **First run (`gen-r1`): not credited.** Post-run validation found 2 schema errors on `env/proto-name-own-property`. The generator had stored per-entry diagnostics in a plain object, so the `__proto__` name set its prototype: the very hazard the case exists for. The generator now records an ordered pair list, and the merge rejects plain-object records and malformed selections (self-test 16/16).
  - **Rerun (`gen-r2`): credited.** It produced 57 spawn cases and 7 tool cases, and its partials are in `gen/out/revision-1/`; candidate 1's are kept in `gen/out/candidate-1/`. The schema check has 0 errors. The targeted schema and manifest tests pass: 939, including 18 for `spawn-nul`. Containment controls 20/20.

## 7. Review 2 and revision 2

Review 2 (issuecomment-6144836852) closed F1, F2, C002 and C003 at contract level. It refined **L12D011-C001** to one residual writer: the Linux recipe's last line, `cp /tmp/guard-root/w/linux-partial.json /out/linux-partial.json`. That copy had no proof of the final host-bound entry, and the controls' writer inventory omitted the shell recipe. Section 6's universal writer claim was therefore broader than the code established.

**Route (trigger A, RT-6).** C001 survived two reviews on the same surface. The counters are recorded in `history.routes` on #224, and the Owner was notified with the default route, CONTRACT_CONVERGENCE. The route taken is the **narrow targeted-fix exception**, on a finite, enumerable dimension:
- the generation evidence's writers are exactly `io.mjs` plus fixed private-tmpfs shell literals;
- the residual is one statement;
- a mechanical inventory now closes the dimension.

If C001 survives the next review, the route is CONTRACT_CONVERGENCE with no further point fix.

**Fix:**
- `io.transfer(guard, source, destination)` performs the container's **one** host-bound write through `writeOutput`, so `assertOutput` proves the **final** `/out/linux-partial.json` entry (`FS_GUARD_OUTPUT=/out`) immediately before the write. `transfer.mjs` is its container entry point; it accepts exactly that source and destination.
- `gen-linux.sh` no longer copies to `/out`.

**Controls (`containment-controls.mjs`, 33/33):**
- **The real `io.transfer`**, run under a guard instance whose two roots emulate the container's (an empty fixture made and removed only through `makeSandbox` / `cleanupSandbox`), with the write intercepted:
  - the legitimate `/out` destination makes **one** attempt;
  - an outward **final** entry, an outward `/out` ancestor and an inspection-failure `/out` ancestor are each refused with **zero** attempts;
  - the proof-removed mutant is caught.
- **The complete inventory:**
  - every `gen/*.mjs` except `io.mjs` and the controls file makes no filesystem mutation;
  - every write target in every `gen/*.sh` (`mkdir`, `tar -C`, `cp`/`mv`/…, `chmod`/`chown`, redirections) is a `/tmp/` literal, and `/out` appears only as `transfer.mjs`'s argument;
  - inventory controls flag the review-2 bare `cp`, and a redirect or an extraction into `/out`.

**Claims corrected:** spec §21.7 and record §4 now name the transfer, and the private-tmpfs literals, explicitly.

**Evidence.** The canonical content is unchanged: the transfer copies the same bytes.
- **End-to-end rerun (`gen-r3`)** of the revised recipe, in the host window Codex granted after Memory's batch-done. The container's guarded transfer printed `TRANSFER DONE`, and the merge completed.
- **Byte-identical:** both partials and `spawn-nul.json` equal `gen-r2`'s (`cmp`; the code worktree is unchanged). The committed partials in `gen/out/revision-1/` therefore stand for both runs.

## 8. Python implementation (candidate)

Review 3 (issuecomment-6145618255) **APPROVED** the contract for implementation at code `387b81fb` / docs `fb68cde0`, with C001 closed. It was merged by guarded exact-head merges: code #225 → `be02f9f3`, docs #301 → `a080af46`. The Python candidate is on `layer/12-d011-python`.

**The seam:**
- `execution/spawn_nul.py` holds Node's `util.inspect` string subset, the §21.2 diagnostic, the §21.3 check order (Windows: UTF-16 sort of every retained name; POSIX: integer-index names, then overlay names, then baseline-only names in UTF-16 order) and **one** validator.
- `LocalSubprocess.spawn` reads the baseline once, composes the effective environment as before, then checks argv, the effective cwd (the certified resolver, or the provider default) and the effective entries (name before value). This happens after the pre-abort check and before any native call.
- A rejection is `Err(SubprocessError(spawn_error, <diagnostic>, nul_input=True))`. `nul_input` is a new optional field, `False` by default, and the narrow distinction of §21.5.

**The tools:**
- `_search.spawn_engine` (`find`, `grep`) and `bash` check their **unprojected** assembled argv with the same validator, immediately before the certified WP-13.3 scalar projection (`WP133-AUD-R001`). The diagnostic therefore shows the JavaScript-string value, including `\udXXX`, while the certified projection of non-NUL spawns is unchanged.
- A marked seam rejection (cwd or environment) is surfaced unchanged; every other failure keeps `Failed to run …` / `Failed to start the shell …`.
- A stdin-transported `bash` command is not argv and is not checked.

**Witnesses (`tests/execution/test_spawn_nul.py`, `tests/conformance/test_spawn_nul_conformance.py`):**
- the 57 spawn and 7 tool canonical cases, run through a thin runner (a configured `baseline` is installed as a fixture);
- the pure functions, on **both** platforms;
- a native-spawn spy proving zero calls for every rejected input;
- an unrelated `ValueError` still propagating;
- the tools' narrow distinction: a non-NUL OS message starting with "The " keeps its prefix, and a marked rejection does not;
- the diagnostic showing the unprojected lone surrogate;
- stdin transport not checked;
- the §15.5 consumer arbitration dropping the colliding entry before the check.

**Changed existing test (disclosed):** the WP-12.E4 control `test_control_changing_inherit_env_false_fails` patched `_effective_env` with a two-argument lambda. `_effective_env` now receives the baseline the provider read once, so the control takes the third argument and supplies the real baseline. Its intent and witness are unchanged.

**Negative controls (`scripts/l12_d011_negative_controls.py`, 14):** each runs the spawn-NUL suites against a mutated copy of `src` in a NEW work directory. Every target is proven inside the project root, with no link or reparse ancestor and its real path inside, before each mkdir and write; nothing is deleted. Each mutant must be killed by its **intended** witness:
- check after the native spawn;
- baseline-first POSIX order;
- sort-all POSIX order;
- naive integer index;
- the superseded baseline value;
- the raw, unresolved cwd;
- double URL decoding;
- the default cwd unchecked;
- cwd before args;
- a cut at 128 or above;
- quote selection;
- the tool string-matching;
- the tool checking the projected argv;
- `bash` checking the stdin command.

**Gates.** Host window granted by Codex, Windows then Linux, logs in `data/l12-d011/python-implementation/`:

| Gate | Windows (head `1a887464`) | Linux (`python:3.13`, uid 1000, pinned ICU 78.3) |
|---|---|---|
| pytest | **6428 passed**, 43 skipped, 19 xfailed, 0 failed | **6254 passed**, 204 skipped, 19 xfailed, 0 failed |
| coverage | **100%** | 96.89%: the platform-only branches, none in this change's lines (`spawn_nul.py` and `_search.py` 100%; the remaining lines are the Windows `taskkill` path, the Windows error mapping and a bash cleanup branch) |
| mypy | clean (118 files) | the 15 pre-existing platform/stub errors (Windows APIs, `jsonschema` stubs, unused ignores) |
| ruff | clean; changed files formatted (whole-tree format drift of 7 untouched files is pre-existing, informational) | clean |
| negative controls | **14/14 killed** | **14/14 killed** |

The first Windows run, at `7d8612eb`, is not credited: it had 1 failure, the E4 control above. It was fixed in `1a887464`, and the Windows gates were rerun in full. The head adds `70573a53`, a manifest status line only, which passes manifest validation (8/8).

## 9. Implementation review 1 and remediation 1

**Review 1** (Codex, #224 issuecomment-6146503957, round 4) was CHANGES REQUESTED against code `70573a53` / docs `1e924c2d`. The contract stays approved and unchanged.
- **L12D011-I001** (blocking): `_is_index` converted the whole decimal name with `int(name)` before comparing it with the index bound. A POSIX baseline or overlay name of more than 4300 digits therefore hit Python's integer-string conversion limit, and the spawn raised `ValueError` instead of ordering the name as an ordinary one.
- **L12D011-I002** (blocking): the negative-control driver credited a kill by node name only. It ran no unmutated baseline, did not validate the pytest exit code or error lines, and did not check that the failure was the witness's discriminating reason. Under workflow §9.7 its 14/14 was not creditable.
- **L12D011-N001** (non-blocking): the Linux gate table reported the platform limitations without the commands' exit codes or a comparison with the base commit.

**Route (RT-6).** Convergence trigger C fired: three rejected complete events on this work package (rounds 1, 2 and 4). Triggers A and B did not fire. The counters and the route are recorded in the #224 state (`history.routes`), and the Owner was notified with the default route, CONTRACT_CONVERGENCE. The route taken is the narrow targeted-fix exception. Both findings are implementation and evidence defects against an approved, unchanged contract, and each has a finite dimension: I001 is one predicate, and I002 is the driver's credit rules. If either survives review 2, the route becomes CONTRACT_CONVERGENCE with no further point fix.

**Remediation (code `0bc99fb`, `705d57af`):**
- **I001.** `_is_index(name)` now requires the length to be at most 10 **before** converting: `len(name) <= 10 and fullmatch("0|[1-9][0-9]*") and int(name) <= 4294967294`. The ASCII-only `[0-9]` class already excludes non-ASCII digits. Two new witnesses:
  - `test_index_domain_neighborhood_and_long_names` (pure, both platforms) covers a 4301-digit name, the maximum index `4294967294`, the first excluded value `4294967295`, 10 and 11 digits, a 12-digit name, `0`, a leading zero (`007`) and Arabic-Indic digits;
  - `test_long_numeric_env_name_is_an_ordinary_name_at_the_provider` drives the real `LocalSubprocess.spawn` on its POSIX branch with a 4301-digit overlay name. Its spy at the native boundary proves that the call reaches the OS ordered as an ordinary name. The discriminating message is `LONG NAME CONVERTED`.
- **I002.** `scripts/l12_d011_negative_controls.py` now applies the §9.7 credit rules:
  - an **unmutated baseline** runs first, and must exit 0 with every intended witness node `PASSED` (`-rA` report). Otherwise every control is INVALID;
  - each mutant's text is compiled in memory before it is written, and an anchor must match exactly once;
  - a kill is credited only for **pytest exit 1** with **no ERROR line**, and only when an **intended** witness `FAILED` with a message matching that witness's **discriminating reason** regex. Exits 0/2/3/4/5, a timeout, collection or setup errors, a counterfeit reason and a witness missing from the baseline are each NOT KILLED or INVALID;
  - the report records each mutant's pytest exit, error count and observed witness reasons (`705d57af`), so the credit can be checked from the evidence alone;
  - `--self-test` exercises these rules on 14 counterfeit outcomes;
  - a 15th control, `unbounded-index-conversion`, restores the I001 defect;
  - the witnesses carry discriminating assertion messages (`PREFIX LOST`, `PROJECTED DIAGNOSTIC`, `INDEX DOMAIN`, `LONG NAME CONVERTED`, `native spawn reached`);
  - containment is unchanged: every target is proven inside the project root (lexical, no link or reparse ancestor, real path) before each write, in a NEW work directory, and nothing is deleted.
- **N001.** The Linux gate records every command's exit code and runs the same pytest/coverage and mypy commands on base `be02f9f3` (the merge-base) in the same container.

**Gates at `705d57af`** (host window granted by Codex, Windows then Linux; evidence in `data/l12-d011/python-implementation/remediation-1/{windows,linux}`, each with a `gates-summary.txt`):

| Gate | Windows | Linux (`python:3.13`, uid 1000, pinned ICU 78.3): candidate | Linux: base `be02f9f3` |
|---|---|---|---|
| pytest | **6430 passed**, 43 skipped, 19 xfailed, 0 failed; exit 0 | **6256 passed**, 204 skipped, 19 xfailed, 0 failed; exit 1 (coverage only) | 6171 passed, 204 skipped, 19 xfailed, 0 failed; exit 1 (coverage only) |
| coverage | **100%** (9748 statements) | 96.89%: 303 missed | 96.85%: 303 missed |
| mypy | clean (118 files); exit 0 | 15 errors in 5 files; exit 1 | the same 15 errors (two `unused-ignore` lines in `subprocess.py` shifted by +2); exit 1 |
| ruff | clean; the 10 changed files formatted (whole-tree drift of 7 untouched files, informational) | clean; exit 0 | — |
| driver self-test | PASSED (14 checks) | PASSED; exit 0 | — |
| negative controls | baseline GREEN (exit 0, 85 passed); **15/15 KILLED**; every mutant exit 1, 0 errors | baseline GREEN (exit 0, 85 passed); **15/15 KILLED**; every mutant exit 1, 0 errors; exit 0 | — |

**Linux limitations.** The Linux limitations are equal to base. The per-file missed-line counts are identical between candidate and base. In this change's files they are the same Windows-only constructs, shifted by the inserted lines:
- `subprocess.py` 174-182 and 201 (base 172-180 and 199): the `taskkill` path and the helper settle;
- `errors.py` 135 (base 132): the Windows error mapping;
- `bash.py` 397 (base 386): a cancellation branch.

`spawn_nul.py` and `_search.py` are at 100% on Linux.

**Runs not credited** (disclosed):
- the Windows run at `0bc99fb` (green, 15/15). It was superseded when `705d57af` added the per-mutant exit to the report;
- a Linux run at `0bc99fb`, stopped by Claude during package installation.

Both platforms were rerun in full at `705d57af`.
