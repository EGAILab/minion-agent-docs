# CE-L13-SCOPE-01 — independent checkpoint re-challenge

Mode: targeted convergence-checkpoint re-review only. No Python or Rust implementation was
authorized or performed.

## Exact target

```text
coordination issue: EGAILab/minion-agent#47
candidate PR:       EGAILab/minion-agent-docs#124
candidate SHA:      ca32ea2c2b7d44ea7cf952c759cc0be4c240fa4a
checkpoint:         assurance/layers/13-scope-ce-l13-scope-01-shell-config-checkpoint-v2.md
prior challenge PR: EGAILab/minion-agent-docs#128
prior challenge:    177c2c844dff4dd04629919b0191185516c2ff63
pinned Pi:          b7bb00b936dbe21b8e160b3e89efdec361846699
```

The candidate was fetched from its GitHub pull-request ref and matched issue #47. The issue was
open, assigned `NEXT_OWNER = Codex`, and requested a targeted re-challenge of CE-L13-C001 through
CE-L13-C003. Implementation remained explicitly unauthorized.

## Targeted results

### CE-L13-C001 — custom-path truthiness

**RESOLVED.** Revision 2 now states the actual `if (customShellPath)` condition and explicitly
records `""` as a negative control that proceeds to platform-default selection.

### CE-L13-C002 — legacy-path matcher reachability

**RESOLVED.** Revision 2 correctly distinguishes passing through the matcher from necessarily
matching it. Every successfully resolved path string is passed to the common matcher; the literal
`sh` fallback bypasses it. Unix `which` output is trusted without a path-shape check and is no
longer declared source-guaranteed incapable of matching.

### CE-L13-C003 — `spawnSync` failure mechanisms

**STILL OPEN (`CONTRACT_ASSURANCE_DEFECT`).** The main correction is directionally right:
unsuccessful returned results and actually thrown exceptions are distinct paths that converge on
the final `null`. Revision 2 nevertheless gives “the probe command cannot be spawned at all” as
its example of the thrown/catch path. Node's synchronous child-process API reports an ordinary
spawn failure such as a missing executable in the returned object (`result.error` set,
`result.status === null`); it does not throw for that case. Pi ignores `result.error`, fails the
`status === 0 && stdout` condition, and reaches the ordinary final `null`.

Minimal discriminating probe used during this review:

```js
const { spawnSync } = require("node:child_process");
const r = spawnSync("__definitely_missing_shell_probe__", [], {
  encoding: "utf8",
  timeout: 5000,
});
// observed: no throw; r.status === null; r.error.code === "ENOENT"
```

**Required correction:** remove the false missing-executable example from the catch path. State
that spawn failure, timeout, non-zero exit, missing/empty stdout, empty first line, and Windows
`existsSync` rejection all settle through unsuccessful-result fall-through; `catch` covers only a
genuine synchronous exception thrown by `spawnSync` (for example invalid invocation/options), if
one occurs. The externally observable result remains `null` in either case.

## Checkpoint verdict

```text
CHECKPOINT REVIEW
    REJECTED

CE-L13-C001
    RESOLVED

CE-L13-C002
    RESOLVED

CE-L13-C003
    STILL OPEN

CONVERGENCE EPISODE
    CE-L13-SCOPE-01 remains active

IMPLEMENTATION AUTHORIZED
    NO
```

The remaining correction is documentary and does not reopen Layer 12 or authorize Layer 13
implementation. Publish a narrowly revised checkpoint and return it for targeted review.
