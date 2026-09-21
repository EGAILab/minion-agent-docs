# CE-L13-SCOPE-01 — pinned-Pi `getShellConfig` convergence checkpoint (proposed)

Mode: §11.8 characterization/checkpoint only. **No Python or Rust implementation performed or
authorized. No Layer 13 semantic contract adopted. This checkpoint requires independent
Codex challenge/approval before being folded into the Layer 13 scoping artifact.**

## Trigger

`L13-S002` survived two independent review rounds on the same root-cause surface (`utils/
shell.ts:getShellConfig`'s selection/transport/error behavior) -- first as an incompleteness
finding (`minion-agent-docs#125` @ `8aa47e478dc91e029420ae0ce34df041acd5a668`), then, after the
audit was completed, as a residual factual error in the error-text characterization
(`minion-agent-docs#127` @ `54184816b0fbfa0416a16f519af2c232c7ed47dd`, rejecting revision 3 at
`7a26c635923253e563d2a6b929d1c0b865c2d20f`). Per `agent-workflow.md` §11.8 trigger A, this
mandates entering `CONTRACT_CONVERGENCE` (episode `CE-L13-SCOPE-01`, recorded in
`minion-agent#47`) rather than a further untracked point-fix.

## Root-cause surface

Unlike Layer 12/R002 (a compiled, delegated, third-party binary requiring an executable oracle),
this surface is Pi's own readable TypeScript, fully inspectable at the pin. The correct
convergence method here is a complete, branch-by-branch characterization directly against source
-- not an executable oracle -- because there is no external engine to differentially test against
and no ambiguity a compiled binary could hide. The prior errors were characterization mistakes
(conflating two distinct error branches; leaving an audit gap open while claiming completion), not
uncertainty about what the source actually does.

## Complete characterization

Source: `packages/coding-agent/src/utils/shell.ts`, functions `isLegacyWslBashPath` (lines
15-18), `getBashShellConfig` (20-22), `findBashOnPath` (24-58), `getShellConfig` (67-120) -- the
entire file region relevant to shell selection, read and quoted verbatim below, at the pinned SHA
`b7bb00b936dbe21b8e160b3e89efdec361846699`.

### Decision order (exact, as written -- `getShellConfig`, lines 67-120)

```text
1. customShellPath argument provided?
   yes -> exists on disk (existsSync)?
          yes -> return getBashShellConfig(customShellPath)   [see Transport below]
          no  -> THROW: `Custom shell path not found: ${customShellPath}`
                 (this exact branch and this exact message -- nothing else,
                 no location list, no setup guidance; checked before any
                 platform branch, so it applies identically on every OS)
   no  -> continue to platform branch

2. process.platform === "win32"?
   yes -> 2a. %ProgramFiles%\Git\bin\bash.exe exists?
              yes -> return getBashShellConfig(thatPath)
          2b. else %ProgramFiles(x86)%\Git\bin\bash.exe exists?
              yes -> return getBashShellConfig(thatPath)
          2c. else findBashOnPath() [Windows variant] succeeds?
              yes -> return getBashShellConfig(thatPath)
          2d. else -> THROW the multi-line message below

   no  (Unix) -> 3a. /bin/bash exists?
                     yes -> return getBashShellConfig("/bin/bash")
                 3b. else findBashOnPath() [Unix variant] succeeds?
                     yes -> return getBashShellConfig(thatPath)
                 3c. else -> return {shell: "sh", args: ["-c"]}
                             (silent degrade -- NO error thrown, unlike Windows)
```

### `findBashOnPath()` (lines 24-58) -- exact per-platform probe, and its own failure mode

```text
Windows: spawnSync("where", ["bash.exe"], {timeout: 5000, windowsHide: true})
         -> take the FIRST line of stdout if the process exited 0 and produced
            output, THEN re-verify with existsSync (because `where` itself can
            report a stale/nonexistent path) -- only then return it.
         -> ANY exception during the spawnSync call (including the 5s timeout
            firing) is caught and silently treated as "not found" (returns
            null), never propagated as a thrown error.

Unix:    spawnSync("which", ["bash"], {timeout: 5000})
         -> take the FIRST line of stdout if the process exited 0 and produced
            output -- trusted as-is, NOT re-verified with existsSync (the
            source comment explicitly says this is deliberate, "handles Termux
            and special filesystems").
         -> same silent-catch-to-null failure mode as the Windows branch.
```

### Transport selection -- `getBashShellConfig`/`isLegacyWslBashPath` (lines 15-22)

```text
Every resolved shell path (from ANY of branches 1/2a/2b/2c/3a/3b above -- this
function is the single common exit point for every "found a bash" branch, so
there is exactly one transport-selection rule for all of them) is passed
through isLegacyWslBashPath:

  normalize: replace all "/" with "\", lowercase
  match against: ^[a-z]:\\windows\\(?:system32|sysnative)\\bash\.exe$
  (anchored full-string match; ANY drive letter; either "system32" or
  "sysnative" subdirectory; no additional path segments permitted)

  MATCH    -> {shell: <path>, args: ["-s"], commandTransport: "stdin"}
              (command is written to the spawned shell's stdin, then closed)
  NO MATCH -> {shell: <path>, args: ["-c"]}
              (commandTransport left undefined; bash.ts treats undefined as
              argv transport -- command is appended to argv)

In practice, given the decision order above, the ONLY branches that can ever
produce a path matching this pattern are: (1) an explicit customShellPath the
caller deliberately points at that exact location, or (2c) Windows'
findBashOnPath() `where bash.exe` result, if a legacy WSL bash shim happens to
be first on PATH. Branches 2a/2b (Git Bash under ProgramFiles) and 3a/3b/3c
(Unix) can never produce a matching path, since none of their path shapes fit
the anchored Windows-drive-letter pattern.
```

### Distinguishable thrown/returned outcomes -- complete enumeration

```text
A. Custom path set, missing          -> throw "Custom shell path not found: <path>"
                                         (identical on every platform; checked first)
B. Windows, all four sub-branches exhausted (2a-2c all fail)
                                      -> throw multi-line message:
                                         "No bash shell found. Options:\n"
                                         "  1. Install Git for Windows: https://git-scm.com/download/win\n"
                                         "  2. Add your bash to PATH (Cygwin, MSYS2, etc.)\n"
                                         "  3. Set shellPath in settings.json\n\n"
                                         "Searched Git Bash in:\n"
                                         "  <path>\n"        (repeated once per
                                                               ProgramFiles*
                                                               env var that was
                                                               actually set --
                                                               0, 1, or 2 lines;
                                                               an unset env var
                                                               contributes no
                                                               line at all, it
                                                               is not listed as
                                                               "unset")
C. Unix, both sub-branches exhausted (3a/3b fail)
                                      -> NO throw; returns {shell:"sh",args:["-c"]}
D. Any successful resolution (1-match, 2a, 2b, 2c, 3a, 3b)
                                      -> returns a ShellConfig per the Transport
                                         rule above; no error, no message
```

Outcomes A and B are the only two distinguishable *thrown* error shapes in this entire function,
and they are never interchangeable: A fires only for an explicit, caller-supplied path that does
not exist, before any platform-specific search ever runs; B fires only on Windows, only after
every automatic Git-Bash-location and PATH search has already been exhausted, and only names
locations this function itself searched (never the custom path, which by definition was never
searched automatically). Revision 3 of the Layer 13 scoping artifact incorrectly attributed B's
message text to A's branch; that is corrected here and must be corrected in the next scoping
revision.

## Proposed requirement-scope impact

`TOOL-034` (bash: argument schema, no-default-timeout, shell-selection order, argv-vs-stdin
command transport) is the correct home for this entire matrix; no new requirement ID or work-
package change is proposed. The corrected scope for `TOOL-034`'s shell-selection portion is:
the four-branch platform-dependent search order (A/B/C/D above, decision order tables above),
the two distinguishable failure shapes (A and B, never conflated), the silent Unix degrade-to-`sh`
(C, no error), the WSL-legacy-path transport switch (`isLegacyWslBashPath`, and the closed set of
branches that can actually reach it), and `findBashOnPath`'s silent-catch-to-null failure mode on
both platforms (a probe failure is never itself surfaced as an error -- it always falls through to
the next branch in the decision order).

## Convergence status

```text
episode:                 CE-L13-SCOPE-01
checkpoint_status:       PROPOSED FOR APPROVAL
open_findings:
  - L13-S002
next_action:              independent Codex challenge/approval of this exact characterization
implementation_authorized: NO
```

This checkpoint proposes a *characterization*, not an implementation plan -- there is no
"AGREED FOR IMPLEMENTATION" gate here because no implementation is being proposed. The gate this
checkpoint requires is agreement that the matrix above is a complete and accurate description of
pinned Pi's `getShellConfig` behavior. Once approved, it will be folded into a new Layer 13
scoping revision (revision 4) replacing revision 3's incorrect error-branch statement; revisions
1 through 3 remain unmodified as historical reviewed records.
