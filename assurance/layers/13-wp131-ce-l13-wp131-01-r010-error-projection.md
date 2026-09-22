# CE-L13-WP131-01 — Lane E: `R010` (filesystem error projection)

Mode: §11.8 sub-checkpoint characterization, Lane E, `R010` only, per the `CE-L13-WP131-01 --
Owner Process Decision` lane decomposition. **No Python or Rust implementation performed or
authorized. No Layer 12 production change.** `R003`/`R004`/`R008` remain frozen
`CHECKPOINT-READY`; `R002`/`R005` remain `OWNER_DECISION_RESOLVED`; `R006-A`/`R006-B` remain
`RESOLVED`, `R006-C` remains `FEASIBILITY_BLOCKED` (paused); `R007` is `OWNER_DECISION_RESOLVED`
(`R007-b`, its own isolated Layer-12 extension work package tracked separately at
`minion-agent#53`). This lane does not discuss or re-review `R006` or `R007`.

This is the last of the five lanes `CE-L13-WP131-01`'s lane decomposition named
(`R004`/`R005` -> Lane A, `R002` -> Lane B, `R006` -> Lane C, `R007` -> Lane D, `R010` -> this
lane). `R010`'s underlying source-citation work (`minion-agent-docs#132`'s pre-lane-decomposition
`13-wp131-ce-l13-wp131-01-characterization.md`, Part 4) was never identified as containing an
invalid witness or a wrong-reference-function error, and remains accurate. **Revision 1 of this
document, however, incorrectly treated `R010` as needing only a single proposed resolution rather
than owner governance** -- independent review (`minion-agent-docs#152`) correctly rejected that
framing: Pi's tool-level error TEXT is model-visible, and replacing it is exactly the kind of
observable divergence `R006`/`R007` required owner governance for. `R010` is, as of this revision,
understood to require the SAME kind of owner decision matrix as `R006`/`R007` (§4), not a
characterization-only resolution.

## 1. Pi's own error text is a genuine mix of hand-authored and raw-propagated -- not one uniform rule

### `ls.ts` (`ls.ts:132-152`, re-verified directly this lane against the currently pinned source)

```text
!(await ops.exists(dirPath))         -> reject(new Error(`Path not found: ${dirPath}`))     (line 134)
!stat.isDirectory()                  -> reject(new Error(`Not a directory: ${dirPath}`))     (line 141)
readdir() throws (caught explicitly) -> reject(new Error(`Cannot read directory: ${e.message}`))
                                         (line 150)
```

`ops.stat(dirPath)` itself (line 139, between the `exists` check and the `isDirectory` check) is
confirmed, directly against the current source, to have **no wrapping `try`/`catch` at that call
site** -- the only `try`/`catch` inside the outer `try` block (which starts at line 128) is the one
immediately around `ops.readdir` (lines 147-152). If `ops.stat` throws (a permission-denied stat,
or a TOCTOU race where the path is removed between the `exists` check and this call), that raw
exception propagates to the function's own outer `catch`, producing a bare `reject(e)` with
**Node's raw error object and message**, not a hand-authored string. This is a fourth,
undocumented-in-Pi's-own-comments, distinguishable `ls` error shape.

### `read.ts` (`read.ts:243-249`, re-verified directly this lane against the currently pinned source)

```js
try {
    const absolutePath = await resolveReadPathAsync(path, cwd);
    if (aborted) return;
    // Check if file exists and is readable.
    await ops.access(absolutePath);          // line 248 -- no wrapping try/catch at this call site
    if (aborted) return;
    ...
```

Confirmed: **no hand-authored message at all** for the existence/readability check. `ops.access`'s
failure (missing file, permission denied, etc.) propagates as Node's raw `fs` error straight to
whatever outer `catch` this async block eventually reaches, unmodified. `read` therefore has zero
hand-authored existence/permission error text -- its entire "distinguishable error" claim rests on
whatever raw OS error text/code happens to surface, which is itself platform-dependent in exact
wording (though not in `.code`).

### Live-verified raw error shapes (this lane; WSL Ubuntu, Node v24.14.0 -- the original
characterization described this claim from source reading alone; this revision demonstrates it
with a real run)

```text
$ node -e 'fs.promises.access("/tmp/does_not_exist_r010").catch(e =>
    console.log(JSON.stringify({message: e.message, code: e.code})))'
{"message":"ENOENT: no such file or directory, access '/tmp/does_not_exist_r010'","code":"ENOENT"}

$ node -e 'fs.promises.stat("/tmp/does_not_exist_r010_stat").catch(e =>
    console.log(JSON.stringify({message: e.message, code: e.code})))'
{"message":"ENOENT: no such file or directory, stat '/tmp/does_not_exist_r010_stat'","code":"ENOENT"}

$ node -e 'fs.promises.readdir("/root/no_permission_dir_r010").catch(e =>
    console.log(JSON.stringify({message: e.message, code: e.code})))'
{"message":"EACCES: permission denied, scandir '/root/no_permission_dir_r010'","code":"EACCES"}
```

Confirms directly: Node's raw `fs` error messages embed the syscall name (`access`, `stat`,
`scandir`) and the addressed path in a fixed template, distinct in both wording and shape from
`ls.ts`'s own three hand-authored strings (`"Path not found: ..."`, `"Not a directory: ..."`,
`"Cannot read directory: ..."`) -- confirming the "genuine mix," not merely asserting it.

## 2. Mapping onto Layer 12's `FsErrorCode` (already-certified, closed set)

**Revision 4 of this section** (independent review `minion-agent-docs#152`, `#153`, then `#154`,
`L13-WP131-R010-B` then `L13-WP131-R010-D` twice): revision 1's table collapsed `ls`'s raw `stat`
and hybrid `readdir` branches to only `permission_denied`/`unknown` (fixed in revision 2);
revision 2's "full taxonomy" claim then still omitted `not_supported` from every row, including the
whole-operation `list_dir_raw -> not_supported` outcome the already-approved `R007-b`/`WP-12.E1`
contract explicitly permits (fixed in revision 3); revision 3's own newly-added general rule was
then applied everywhere EXCEPT the later `read_text_file`/`read_binary_file` content-read site,
which remained collapsed to `is_directory` alone (fixed here -- split into the specific
is-a-directory subcase and the general later-read-failure site).

```text
FsErrorCode: aborted, not_found, permission_denied, not_directory,
             is_directory, invalid, not_supported, unknown
```

(`spec/execution.md` §2.1, unchanged, already certified -- this lane does not modify it.)

**General rule (binding; the enumeration below is illustrative completeness, not itself the
rule):** for every Pi error site that is HAND-AUTHORED (a fixed, stable string Pi always produces
for that specific branch, regardless of platform), the classification is the SPECIFIC certified
code that branch's own condition represents -- exactly one code per hand-authored site, never a
range. For every Pi error site that is RAW, HYBRID, or a WHOLE-OPERATION outcome of a Layer-12
operation Layer 13 consumes (the underlying OS/provider error reaches the caller unmodified,
wrapped with the raw message still embedded, or reported as a whole-call `Result` error by the
Layer-12 operation itself), the classification is the EXACT underlying certified `FsErrorCode`
Layer 12 already computes for that failure, drawn from the FULL §2.1 taxonomy -- never collapsed
to a narrower subset merely because the site is "the stat call," "the readdir call," or "a local
filesystem, so `not_supported` doesn't apply here." `not_supported` is reachable at EVERY site in
this table whenever the underlying provider cannot supply the certified operation being called --
this is a property of the PROVIDER, not of any specific local-filesystem errno, and is therefore
never excludable from a site's reachable set purely because a Node-local reference implementation
happens not to trigger it.

| Scenario | Pi's own text | Site kind | Reachable `FsErrorCode`(s) |
|---|---|---|---|
| `ls`: path missing (`!ops.exists()`) | hand-authored `"Path not found: <path>"` | hand-authored | `not_found` (exactly one; this is what the check itself represents) |
| `ls`: not a directory (`!stat.isDirectory()`) | hand-authored `"Not a directory: <path>"` | hand-authored | `not_directory` (exactly one) |
| any tool: aborted mid-operation | hand-authored `"Operation aborted"` (uniform across both tools) | hand-authored | `aborted` (exactly one) |
| `ls`: `stat` fails after `exists` (the unwrapped call, §1) | raw, unwrapped exception, Node's own message/code | raw | `not_found` (ENOENT -- the exists-then-stat TOCTOU race); `permission_denied` (EACCES/EPERM); `not_directory` (ENOTDIR -- a path component stopped being a directory between checks); `invalid` (EINVAL); `not_supported` (a provider that cannot supply this classification step at all); `unknown` (any other errno). `is_directory`/`aborted` are NOT reachable from this specific call (a `stat` failure cannot itself represent "is a directory," and this call passes no cancellation signal). |
| `ls`: `readdir` fails (hybrid wrapper, §1) | hand-authored PREFIX `"Cannot read directory: "` + raw embedded underlying message | hybrid | Same reachable set as the `stat` branch above (`not_found`, `permission_denied`, `not_directory`, `invalid`, `not_supported`, `unknown`) -- the WRAPPER text is fixed and hand-authored, but the classification is still driven by the embedded raw cause, not the wrapper's own fixed prefix. |
| `read`: `ops.access` fails (§1) | raw, unwrapped exception, Node's own message/code | raw | `not_found` (ENOENT); `permission_denied` (EACCES/EPERM); `not_directory` (ENOTDIR -- a path component is not a directory); `invalid` (EINVAL); `not_supported` (a provider that cannot supply this check); `unknown` (any other errno). `is_directory` is NOT reachable here: `access()` succeeds on a directory (it checks permission bits, not entry kind) -- the directory case surfaces later, below. |
| `read`: path is a directory, specifically (`access` succeeds, the LATER content-read step fails because the addressed path IS a directory) | raw `EISDIR`-class error from that later read, not from `access` itself | raw, specific subcase | `is_directory` (exactly one for THIS specific subcase -- the addressed-path-is-a-directory condition, and only that condition, maps here) |
| `read`: the LATER `read_text_file`/`read_binary_file` operation fails for any OTHER reason (`access` succeeds; corrected this revision, independent review `minion-agent-docs#154`, `L13-WP131-R010-D`) | raw, unwrapped exception/`FsError` from the certified, provider-neutral `read_text_file(path, signal?)`/`read_binary_file(path, signal?)` operations (`spec/execution.md` §3) -- NOT restricted to Node-local `readFile` errno examples | raw | `not_found` (ENOENT -- TOCTOU removal between `access` and the read); `permission_denied` (EACCES/EPERM); `not_directory` (ENOTDIR); `invalid` (EINVAL); `not_supported` (a provider that supports the earlier access/existence check but cannot supply content reading itself -- a real, certified-interface-permitted case, not merely a Node-local hypothetical); `unknown` (any other errno/provider error). This is the GENERAL later-read-failure site; the `is_directory` row immediately above is its own narrower, specific subcase, not a substitute for this general enumeration. |
| `ls`, built on the approved `R007-b`/`WP-12.E1` extension: `list_dir_raw(path)` itself returns an error `Result` (`spec/execution.md` §11.3, §11.6's `not_supported` witness) | no Pi-authored text exists for this outcome -- it is a Minion-specific enumeration entry point Pi's own `ls.ts` has no equivalent call site for | whole-operation | `not_found`, `permission_denied`, `not_directory`, `invalid`, `not_supported` (the case the approved contract's own witness names explicitly), `unknown` -- same taxonomy as any other raw/hybrid site, drawn from the SAME `list_dir_raw` error mapping §11.3 already certifies. **This is a WHOLE-OPERATION failure**: enumeration cannot begin at all, so `ls`'s entire tool call fails -- R010 MUST project this as tool-level error text, exactly like the `stat`/`readdir` raw/hybrid rows above, not as a silently-skipped per-entry outcome (contrast the next row). |
| `ls`, built on `R007-b`/`WP-12.E1`: an individual `probe_dir_entry(name)` call (§11.5's required consumption loop) returns an error `Result` for ONE entry | no Pi-authored text (Pi's OWN `ls.ts` per-entry `catch { continue }` is likewise silent for the analogous case, §1) | per-entry, SKIPPED | **Not applicable -- this NEVER becomes tool-level error text at all.** The already-approved `R007-b` consumption pattern (`spec/execution.md` §11.5, step 3b) requires the CALLER to skip a `probe_dir_entry` error and continue to the next name, exactly reproducing Pi's own per-entry silent-skip. `R010`'s error-PROJECTION question (this document) does not apply to this row at all -- there is no message to select a template for, because no tool-level error is ever produced by this specific outcome. Listed here only to make the contrast with the row above explicit, not because it needs its own `FsErrorCode` mapping. |

## 3. Characterization conclusion

Pi's own text is **not** a single, coherent, literally-reproducible contract -- it mixes
hand-authored strings, raw OS-errno text, and one hybrid (custom-prefix-plus-embedded-raw-suffix)
across just two tools, with at least one internally undocumented gap (`ls`'s unwrapped `stat`
call). But **"mixed" does not mean "non-contractual"** (independent review `minion-agent-docs#152`,
correcting revision 1's own framing, count corrected this revision per `minion-agent-docs#153`,
`L13-WP131-R010-E`): Pi's FOUR hand-authored sites (three `ls`-specific plus the abort template
shared by both tools) are stable, deterministic,
platform-independent strings -- coherent, specified behavior, not merely incidental. Layer 12's
`FsErrorCode` vocabulary is already a clean, closed, already-certified classification that every
one of Pi's scenarios maps onto without loss of the *distinguishing information* (§2's corrected,
complete table). What Layer 12's normalization does NOT automatically settle is a SEPARATE
question: whether Layer 13's tool-level error TEXT (the string a model actually sees in a failed
tool call's result) should literally reproduce Pi's own mixed hand-authored/raw/hybrid wording, or
adopt its own portable vocabulary. That text is model-visible -- part of the observable tool
contract, not an internal implementation detail Layer 12's own normalization precedent settles by
itself.

## 4. Owner decision: tool-level error TEXT, not merely classification (revision 2 of this section
-- independent review `minion-agent-docs#152`, `L13-WP131-R010-A`, rejected revision 1's framing
as a single automatic resolution)

Revision 1 proposed a single resolution and argued no owner decision was needed, reasoning that
`FsErrorCode` was already Layer 12's own settled answer. The independent review correctly rejected
this: `FsErrorCode` is an internal Layer-12 capability-seam classification; it does not by itself
authorize Layer 13 to change what TEXT a model observes when a tool call fails. Pi's four
hand-authored strings are themselves stable, specified, model-visible behavior -- replacing them is
an observable divergence requiring the same owner governance `R006`/`R007` required, not something
`TOOL-025`/`TOOL-026`/`TOOL-028`'s own `adopted` disposition already covers by implication.

**`R010-A` -- preserve Pi's exact structure.** Layer 13 reproduces Pi's four hand-authored
templates VERBATIM, citing the addressed path the same way Pi does (`"Path not found: <path>"`,
`"Not a directory: <path>"`, `"Cannot read directory: <underlying message>"`, `"Operation
aborted"`), and on every raw/hybrid site, surfaces the underlying provider's own raw message text
(Python's `OSError.strerror`-equivalent, Rust's `io::Error`'s own `Display` text) embedded the same
way Pi embeds Node's raw text. **Fidelity**: maximal literal string-level match to Pi, including on
the stable hand-authored sites. **Cost, disclosed honestly**: on raw/hybrid sites, Minion's own
tool-error text becomes platform/OS-dependent -- not a Minion-introduced non-determinism, but an
inherited one, since Pi's own raw/hybrid text is equally platform-dependent on the SAME sites. A
canonical cross-platform test corpus cannot assert one fixed string for these specific branches
under this option, only that the classification (§2) is correct and the wrapper/prefix structure
(where one exists) is present.

**`R010-B` -- closed Layer-13 vocabulary on raw/hybrid sites only, Pi's exact wording preserved on
hand-authored sites (corrected this revision, independent review `minion-agent-docs#153`,
`L13-WP131-R010-C`).** Layer 13 reproduces Pi's four hand-authored templates VERBATIM (identical to
`R010-A` there -- there is no portability cost to preserving them, since they are already
platform-independent), but on raw/hybrid sites, replaces the embedded raw provider text with a
closed, Layer-13-authored, deterministic template per `FsErrorCode` value (e.g. `"Cannot access
<path>: permission denied"` for `permission_denied`, regardless of the underlying OS's exact
wording).

**Corrected architecture (revision 3 of this claim):** the certified cross-language tool-error seam
has NO structured-data channel at the FINAL tool-result level to carry alongside a generated
failure -- confirmed directly, `spec/tools.md:512`: pinned Pi's `createErrorToolResult` sets
`details: {}` (empty, not absent) UNCONDITIONALLY for any generated execution error, and Python's
`text_result(..., is_error=True)` and Rust's `ToolCapabilityError`/`immediate_error` all preserve
that same empty-`details` shape -- there is no field in the certified, already-established result
type either language could attach a structured `FsErrorCode` to. Revision 2's claim that each
template "supplements, not replaces" the underlying cause by carrying it as structured OUTPUT data
was therefore architecturally wrong: it promised a channel the certified seam does not have, and
closing that gap would itself require a separate, explicitly-scoped lower-layer tool-result delta
-- not something this lane is authorized to open, and not necessary to resolve `R010` itself.

**`R010-B`'s actual, implementable mechanism**: the underlying certified `FsErrorCode` is used
PURELY INTERNALLY, as Layer 13's own dispatch key for SELECTING which fixed, closed-vocabulary
message template to emit -- it is never itself attached to, or recoverable from, the final
tool-level result as separate structured data. The final result's `details` remains the SAME
certified `{}` shape every generated tool error already uses, under both `R010-A` and `R010-B`
alike; the two options differ only in which STRING gets selected for that result's message content
on raw/hybrid sites, never in the result's own shape. No information is claimed to be preserved
beyond what the message string itself conveys -- this is an explicit, disclosed LOSS of the exact
raw OS wording (though not of the CLASSIFICATION, since a caller's fixed knowledge of which
template maps to which code is itself the "structure," carried by convention/documentation, not by
a runtime field). This is still an explicit, disclosed, **`MINION_ARCHITECTURAL_MAPPING` /
intentional divergence**, model-visible on the raw/hybrid sites specifically, requiring the SAME
owner sign-off `R006`/`R007` required -- not auto-adopted merely because it consumes an
already-adopted lower-layer code. **Fidelity**: full on hand-authored sites; disclosed divergence
on raw/hybrid sites. **Benefit**: fully deterministic, portable, canonical-scenario-testable text
on every site, including the ones `R010-A` cannot pin down.

Neither option is selected here. `TOOL-025`/`TOOL-026`/`TOOL-028` cannot encode a specific
error-text disposition for this dimension until the owner chooses.

## 5. Status (this revision)

```text
R010 source citations: re-verified directly (ls.ts:132-152, read.ts:243-249), live-verified
      raw-error-text shapes (WSL, Node v24.14.0) -- unchanged since revision 1, confirmed accurate
      by all independent review rounds to date
R010-A / R010-B (owner decision structure, minion-agent-docs#152's L13-WP131-R010-A): RESOLVED --
      genuine two-option matrix in place since revision 2, unchanged this revision
R010 FsErrorCode mapping (§2, minion-agent-docs#152's L13-WP131-R010-B): RESOLVED at revision 2
R010-C (minion-agent-docs#153): RESOLVED at revision 3, confirmed by minion-agent-docs#154 -- R010-B
      now uses FsErrorCode purely as Layer 13's own internal template-selection key, never as
      recoverable structured output; details remains {} under both options
R010-D (minion-agent-docs#153, then minion-agent-docs#154): RESOLVED for list_dir_raw ->
      not_supported and the whole-operation-vs-skipped-probe distinction at revision 3; the later
      read_text_file/read_binary_file content-read site remained collapsed to is_directory alone
      (PARTIALLY_RESOLVED_BLOCKING per minion-agent-docs#154) -- FIXED this revision by splitting
      that site into its specific is_directory subcase and a general later-read-failure row
      covering not_found/permission_denied/not_directory/invalid/not_supported/unknown
R010-E (minion-agent-docs#153): RESOLVED at revision 3, confirmed by minion-agent-docs#154 -- the
      template count is consistently four throughout
R010 overall: OWNER_DECISION_REQUIRED (R010-A vs. R010-B)
```

No Layer 12 change. No `minion-agent-python`/`minion-agent-rust` code touched. `R006`/`R007` not
discussed or reopened.
