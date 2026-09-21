# CE-L13-SCOPE-01 — pinned-Pi `getShellConfig` convergence checkpoint (revision 2, proposed)

Mode: §11.8 characterization/checkpoint only. **No Python or Rust implementation performed or
authorized. No Layer 13 semantic contract adopted. This checkpoint requires independent
Codex challenge/approval before being folded into the Layer 13 scoping artifact.**

Targeted remediation of the independent checkpoint challenge (`minion-agent-docs#128` @
`177c2c844dff4dd04629919b0191185516c2ff63`, verdict `REJECTED`, three findings `CE-L13-C001`
through `CE-L13-C003`) against checkpoint revision 1 (`minion-agent-docs#124` @
`e806fbfe16443e50328bc5e2d745fe80f34981f9`). Revision 1 is left unmodified as the historical
reviewed record. The challenge confirmed revision 1's core corrections -- the separated
explicit-path-missing vs. Windows-search-exhausted errors, the Unix silent-`sh`-fallback, the
Windows-recheck-vs-Unix-trust distinction, and the legacy-WSL regex/transport rule -- as
correctly characterized; only the three items below are revised.

## CE-L13-C001 — `customShellPath` branch condition is truthiness, not presence

Pinned source (`getShellConfig`, line 69): `if (customShellPath) { ... }` -- a plain JavaScript
truthiness check, not an "is a value present" check. An empty string is falsy in JavaScript, so
`customShellPath = ""` does **not** enter the explicit-path branch at all; it falls straight
through to the platform-default search (Windows Git-Bash/PATH search, or Unix `/bin/bash`/`which`/
`sh` fallback) exactly as if no `customShellPath` had been passed.

**Corrected branch 1 of the decision order:**

```text
1. customShellPath is truthy (non-empty string)?
   yes -> exists on disk (existsSync)?
          yes -> return getBashShellConfig(customShellPath)
          no  -> THROW: `Custom shell path not found: ${customShellPath}`
   no  (customShellPath is undefined, null, or "" -- all falsy) ->
          continue to platform branch, exactly as if unset
```

`customShellPath = ""` is recorded as an explicit negative-control case: it is observably
different from both "a real path was given" and "nothing was given" only insofar as the caller's
intent differs, but `getShellConfig` itself treats it identically to "nothing was given."

## CE-L13-C002 — the legacy-WSL-transport-reachable branch set is not source-enforced on Unix

Revision 1 stated Unix branches "can never produce a path matching" the legacy-WSL regex, framing
it as a closed set guaranteed by source. That framing is corrected: it is true only by convention
(real Unix `which bash` output is a Unix-shaped path), not because Pi's source validates or
constrains the string in any way. `findBashOnPath`'s Unix branch (lines 45-57) takes the first
stdout line from `spawnSync("which", ["bash"], ...)` and returns it as-is -- no `existsSync`
re-check (unlike the Windows branch), no path-shape validation, no platform-appropriate-separator
check. That string is then passed unmodified into `getBashShellConfig` → `isLegacyWslBashPath`,
the same matcher every other branch's result passes through. If `which` (a system command Pi does
not control) were shadowed, aliased, or otherwise returned a string shaped like
`C:\Windows\System32\bash.exe`, Unix branch 3b would select stdin transport exactly as the
Windows legacy-WSL branch does.

**Corrected statement (replaces revision 1's "closed set" claim):** every branch that returns a
resolved shell path -- 1 (explicit), 2a/2b (Git Bash locations), 2c (Windows `where`), 3a
(`/bin/bash`), 3b (Unix `which`) -- passes that string through the identical `isLegacyWslBashPath`
matcher with no branch-specific exemption; only branch 3c (the literal `"sh"` fallback, which
never calls `getBashShellConfig` at all) is structurally incapable of reaching the matcher. Which
of branches 1/2a/2b/2c/3a/3b can *in practice* produce a matching string depends on the
environment (what `where`/`which` actually return, what the caller passes as `customShellPath`),
not on anything `getShellConfig` itself enforces. Revision 1's practical observation --
Git-Bash-under-ProgramFiles and `/bin/bash` literal paths cannot match, since their exact string
shape is fixed by `getShellConfig` itself and is not that pattern -- remains correct and is
retained; only the claim that 3b (`which`-sourced) is similarly source-guaranteed-unreachable is
withdrawn.

## CE-L13-C003 — `findBashOnPath`'s two distinct return-`null` mechanisms

Revision 1 attributed all not-found outcomes, including a timeout, to the `catch` block. Pinned
source shows two mechanistically distinct paths to the same `null` result, and `findBashOnPath`
never inspects `result.error`:

```text
Windows (lines 27-42) / Unix (lines 46-56), same shape:
  try {
    const result = spawnSync(<probe command>, <args>, {..., timeout: 5000});
    if (result.status === 0 && result.stdout) {
      <extract first line, Windows also re-checks existsSync>
      if <extraction succeeded> return <path>;
    }
    // falls through here -- NOT a throw, NOT the catch block --
    // whenever result.status !== 0, result.stdout is empty/absent,
    // the first line is empty, or (Windows only) existsSync fails.
    // spawnSync itself does not throw for a command that runs but
    // times out or exits non-zero; timeout is one of the ways
    // result.status can end up non-zero / result can be otherwise
    // unsuccessful here, not something the catch block handles.
  } catch {
    // Ignore errors -- reached only if spawnSync ITSELF throws
    // (e.g. the probe binary cannot be spawned at all).
  }
  return null;   // <- both the natural fall-through above AND the
                 //    catch block reach this same final line.
```

**Corrected statement (replaces revision 1's "any exception ... including the 5s timeout ... is
caught and silently treated as not found"):** `findBashOnPath` returns `null` via two distinct
mechanisms that happen to converge on the same value: (a) the ordinary, non-throwing path, when
the `if` condition's success checks (`status === 0`, non-empty `stdout`, a non-empty first line,
and, on Windows, `existsSync` on that line) are not all satisfied -- this is the path a timeout or
a non-zero exit ordinarily takes, since `spawnSync` reports those as an unsuccessful result rather
than throwing; and (b) the `catch` block, reached only if `spawnSync` itself throws (a much
narrower case, e.g. the probe command cannot be spawned at all). The externally observable
behavior -- any probe failure of any kind silently yields `null`, never a thrown error out of
`findBashOnPath` -- is unchanged and correct; only the internal mechanism description is
corrected.

## Everything else (unchanged from revision 1)

The complete decision-order table's branches 2/3 (platform search order), the two distinguishable
thrown-error shapes for branches 1 (corrected above for the truthy/falsy distinction only) and 2d
(Windows exhausted), the Unix silent-degrade-to-`sh` branch (3c, still the only branch with no
matcher exposure), the exact quoted error message text for both throw sites, and the proposed
`TOOL-034` requirement-scope impact are all unchanged from revision 1 and remain in force.

## Convergence status

```text
episode:                  CE-L13-SCOPE-01
checkpoint_status:        PROPOSED FOR APPROVAL (revision 2)
open_findings:
  - L13-S002
next_action:               independent Codex challenge/approval of this exact characterization
implementation_authorized: NO
```
