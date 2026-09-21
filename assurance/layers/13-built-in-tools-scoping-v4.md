# Layer 13 — Built-in Tools scoping (revision 4)

Mode: scoping / read-only audit. **IMPLEMENTATION AUTHORIZED: NO.**

Folds the independently approved `CE-L13-SCOPE-01` convergence checkpoint
(`minion-agent-docs#124` @ `0519d1a99011831fd6cdeea5c0a25b3e7369e79f`, approval evidence
`minion-agent-docs#130` @ `7b3c23749fbcd0660184aff80dce70db3f0fcafc`: `CHECKPOINT REVIEW
APPROVED`, `CE-L13-C001`/`C002`/`C003` all `RESOLVED`, `CONVERGENCE CHARACTERIZATION AGREED`)
into scoping revision 3 (`minion-agent-docs#124` @ `7a26c635923253e563d2a6b929d1c0b865c2d20f`),
replacing revision 3's incorrect shell-selection error characterization with the fully-approved
checkpoint text. This closes `L13-S002` and the `CE-L13-SCOPE-01` convergence episode. Revisions
1 through 3 and all four checkpoint revisions are left unmodified as historical reviewed records;
this file is the complete, current scoping artifact -- everything from revisions 1-3 not revised
below is carried forward unchanged.

## Starting state (unchanged)

```text
code main:    92aa4be168dc82111832467922089206e858a9c4
docs master:  ec36ed92a9a57f5fc8db4f76103a2d202cb82cbc
pinned Pi:    b7bb00b936dbe21b8e160b3e89efdec361846699
```

## `bash` -- shell-selection order (supersedes revision 3's paragraph of the same name)

`utils/shell.ts:getShellConfig`, `getBashShellConfig`, `isLegacyWslBashPath`, and
`findBashOnPath` read in full and independently re-verified across four review rounds
(`CE-L13-SCOPE-01`, closed). Complete decision order:

```text
1. customShellPath is truthy (a non-empty string; undefined/null/"" are all
   falsy and behave identically to "not supplied")?
     yes -> exists on disk (existsSync)?
            yes -> return getBashShellConfig(customShellPath)
            no  -> THROW: `Custom shell path not found: ${customShellPath}`
                   (this exact branch and this exact message only -- no
                   location list, no setup guidance; checked before any
                   platform branch, so it applies identically on every OS)
     no  -> continue to platform branch

2. process.platform === "win32"?
   yes -> 2a. %ProgramFiles%\Git\bin\bash.exe exists?          -> resolve
          2b. else %ProgramFiles(x86)%\Git\bin\bash.exe exists? -> resolve
          2c. else findBashOnPath() [Windows: `where bash.exe`,
              first line, existsSync-reverified] succeeds?      -> resolve
          2d. else -> THROW the multi-line "No bash shell found. Options:
              ... Searched Git Bash in: ..." message (locations list has
              0-2 lines depending on which ProgramFiles* env vars were set;
              an unset var contributes no line, not an "unset" placeholder)

   no  (Unix) -> 3a. /bin/bash exists?                          -> resolve
                 3b. else findBashOnPath() [Unix: `which bash`,
                     first line, trusted without existsSync recheck]
                     succeeds?                                   -> resolve
                 3c. else -> return {shell: "sh", args: ["-c"]}
                             (silent degrade -- NO error thrown,
                             unlike the Windows 2d branch)
```

Every "resolve" outcome above (branches 1/2a/2b/2c/3a/3b) passes its result through the identical
`isLegacyWslBashPath` matcher (`getBashShellConfig`): the string is separator-normalized and
lowercased, then matched against `^[a-z]:\\windows\\(?:system32|sysnative)\\bash\.exe$`
(anchored, any drive letter, either `system32` or `sysnative`, no extra path segments). A match
selects `{shell, args: ["-s"], commandTransport: "stdin"}` (command written to the spawned
shell's stdin, then closed); no match selects `{shell, args: ["-c"]}` (argv transport, the
default `bash.ts` treats as command-appended-to-argv). This matcher exposure is *not*
source-guaranteed to be a closed set restricted to Windows paths: branches 2a/2b/3a can never
match by construction (their exact string shapes are fixed and are not that pattern), but 1
(caller-supplied) and 2c/3b (`where`/`which`-sourced) are only *environmentally* unlikely to
match, not prevented from matching by anything `getShellConfig` itself checks -- only branch 3c
(the literal `"sh"` fallback, which never calls `getBashShellConfig` at all) is structurally
exempt from the matcher.

`findBashOnPath`'s own failure handling: both its Windows and Unix branches wrap a `spawnSync`
call (`timeout: 5000` in both) in a `try`/`catch`, but the `catch` block is defensive against
exception classes -- `TypeError` for an invalid argument type, `RangeError` for an out-of-range
option value -- that cannot actually occur given the fixed, valid literal arguments
(`"where"`/`["bash.exe"]` or `"which"`/`["bash"]`, and a fixed valid options object) this function
always passes; neither varies at runtime. `spawnSync` does **not** throw for OS-level spawn
failures: a missing probe executable, a timeout, or a non-zero exit all surface through the
*returned result object* (`result.status`, `result.error`, empty `result.stdout`), which
`findBashOnPath` never inspects beyond its `if (result.status === 0 && result.stdout)` success
check -- any of those failure modes simply fails that check and falls through to the function's
ordinary final `return null;`, the same statement the (in-practice-unreachable) `catch` block also
reaches. The externally observable behavior is uniform regardless of internal mechanism: any probe
failure of any kind silently yields `null` from `findBashOnPath`, which `getShellConfig` then
treats as "not found" and proceeds to its next fallback branch (or the terminal throw/silent-`sh`
outcome for that platform).

## Requirement-scope impact

Unchanged from revision 2/3: `TOOL-034` (bash: argument schema, no-default-timeout,
shell-selection order, argv-vs-stdin command transport) is the correct home for this entire
matrix; no new requirement ID or work-package change is introduced by this revision. `TOOL-034`'s
shell-selection scope is now the complete, checkpoint-approved matrix above.

## Everything else (unchanged from revision 3)

The `L13-S001` acquisition-matrix correction, all of `L13-S002`'s other completed corrections
(`read`/`grep`/`find`/`ls`), the `L13-S003` mutation-queue atomicity/provider-scoping requirement,
the `L13-S004` four-package split (`WP-13.1` `read`/`ls`, narrowly governance-blocked on
`TOOL-027`'s unresolved disposition; `WP-13.2` `write`/`edit`+queue; `WP-13.3` `bash`; `WP-13.4`
`find`/`grep`, blocked on the engine-pinning owner decision), the `L13-S005` non-colliding
`TOOL-025`..`038` ID range (14 entries, the `TOOL-008`+`009` -> `TOOL-031` consolidation stated
explicitly), and every section not named in this revision (Mutation queue characterization, Path
resolution, Truncation constants, Parity classification, Semantic authority, High-risk surfaces,
Acceptance-oracle strategy, Cross-language impact, Open questions) are unchanged and remain in
force.

## Finding status

```text
L13-S001   RESOLVED (revision 2, confirmed docs PR #126)
L13-S002   RESOLVED (this revision, confirmed docs PR #130 -- convergence episode
           CE-L13-SCOPE-01 CLOSED after four checkpoint rounds)
L13-S003   RESOLVED (revision 2, confirmed docs PR #126)
L13-S004   RESOLVED (revision 2 structural split; revision 3 readiness-label
           correction, confirmed docs PR #126 and #127)
L13-S005   RESOLVED (revision 2, confirmed docs PR #126)
L13-S006   RESOLVED (revision 3, confirmed docs PR #127)
L13-S007   RESOLVED (revision 3, confirmed docs PR #127)
```

## Implementation authorized

```text
NO
```
