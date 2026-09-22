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
lane). Unlike `R007`, `R010`'s original combined-checkpoint text (`minion-agent-docs#132`'s
pre-lane-decomposition `13-wp131-ce-l13-wp131-01-characterization.md`, Part 4) was never
identified as containing an invalid witness or a wrong-reference-function error by any independent
review round -- the original checkpoint's own framing already listed `R010` among the findings
"characterized completely enough for an independent reviewer to judge whether they are now
checkpoint-ready" (as opposed to `R006`/`R007`, both explicitly flagged as requiring owner
governance). This document re-verifies that prior characterization's source citations directly
(not by assumption) and repackages it as its own standalone, independently-reviewable lane
artifact, adding live-executed evidence for the raw-error-text claims that the original text
described but did not itself demonstrate with a live run.

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

```text
FsErrorCode: aborted, not_found, permission_denied, not_directory,
             is_directory, invalid, not_supported, unknown
```

(`spec/execution.md` §2.1, unchanged, already certified -- this lane does not modify it.)

| Scenario | Pi's own text | Classification |
|---|---|---|
| `read`: path missing | raw `ENOENT` (no custom text) | exactly representable -> `not_found` |
| `read`: permission denied | raw `EACCES` (no custom text) | exactly representable -> `permission_denied` |
| `read`: path is a directory (access succeeds, later read fails) | raw `EISDIR`-class error from the subsequent read | exactly representable -> `is_directory`, but fires at a DIFFERENT step (during content read, not the access check) than `ls`'s equivalent |
| `ls`: path missing | hand-authored `"Path not found: <path>"` | exactly representable -> `not_found`, but Pi's literal STRING is hand-authored, not raw-OS-derived |
| `ls`: not a directory | hand-authored `"Not a directory: <path>"` | exactly representable -> `not_directory` |
| `ls`: `stat` fails after `exists` (race/permission) | raw, unwrapped exception | exactly representable -> `permission_denied`/`unknown` depending on cause, but Pi's text here is raw-OS, inconsistent with the two hand-authored messages immediately adjacent to it in the same function |
| `ls`: `readdir` fails | hand-authored `"Cannot read directory: <e.message>"` (embeds the raw underlying message inside a custom wrapper) | exactly representable -> `permission_denied`/`unknown`, text is a HYBRID (custom prefix + embedded raw suffix) |
| any: aborted mid-operation | `"Operation aborted"` (uniform across both tools) | exactly representable -> `aborted` |

## 3. Characterization conclusion

Pi's own text is **not** a single, coherent, literally-reproducible contract -- it mixes
hand-authored strings, raw OS-errno text, and one hybrid (custom-prefix-plus-embedded-raw-suffix)
across just two tools, with at least one internally undocumented gap (`ls`'s unwrapped `stat`
call). Layer 12's `FsErrorCode` vocabulary is already a clean, closed, already-certified
classification that every one of Pi's scenarios maps onto without loss of the *distinguishing
information* (which broad category of failure occurred). Attempting literal text-string parity
with Pi would mean reproducing inconsistent, partially-platform-dependent raw OS message text,
which is not a coherent target and was never actually a single specification even within Pi's own
source.

## 4. Proposed resolution (characterization only -- not a governance question, since Layer 12
already established this exact pattern for the underlying seam)

Layer 13 defines its own closed, `FsErrorCode`-driven set of distinguishable tool-level error
variants (e.g. `not_found`, `not_a_directory`, `permission_denied`, `enumeration_failed`,
`aborted`), each carrying a Layer-13-authored message template (not a literal reproduction of Pi's
mixed raw/custom text) and citing the addressed path. This is `MINION_ARCHITECTURAL_MAPPING`,
consistent with -- not a new divergence from -- Layer 12's own already-established precedent of
defining a clean `Result`/`FsError` system instead of reproducing every raw Node `fs` exception
shape. Distinguishability (the review's actual requirement, per `TOOL-025`/`TOOL-026`/`TOOL-028`'s
own manifest rows citing error-shape fidelity) is fully preserved; literal Pi string reproduction,
which was never a coherent single target even within Pi's own two tools, is not attempted.

This is not offered as a two-or-three-way owner decision matrix the way `R006`/`R007` were: there
is no disclosed divergence here requiring the owner to choose between competing fidelity/cost
tradeoffs -- `FsErrorCode` already IS Layer 12's own chosen answer to exactly this question for the
underlying seam, and this lane finds no reason `TOOL-025`/`TOOL-026`/`TOOL-028` should re-litigate
it at the tool level. Presented as a single proposed resolution for the independent reviewer to
confirm or reject, not as a menu.

## 5. Status (this revision)

```text
R010: characterized, source citations re-verified directly (ls.ts:132-152, read.ts:243-249),
      raw-error-text claim now also live-verified (this lane) rather than resting on source
      reading alone
Proposed resolution: single (not a decision matrix) -- Layer 13 defines its own closed,
      FsErrorCode-driven tool-level error vocabulary with Layer-13-authored message templates,
      consistent with Layer 12's own established precedent
R010 overall: CHARACTERIZATION_SUBMITTED, pending independent review
```

No Layer 12 change. No `minion-agent-python`/`minion-agent-rust` code touched. `R006`/`R007` not
discussed or reopened.
