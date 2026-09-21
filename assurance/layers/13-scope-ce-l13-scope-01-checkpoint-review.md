# CE-L13-SCOPE-01 — independent checkpoint challenge

Mode: independent convergence-checkpoint review only. No Python or Rust implementation was
authorized or performed.

## Exact target

```text
coordination issue: EGAILab/minion-agent#47
candidate PR:       EGAILab/minion-agent-docs#124
candidate SHA:      e806fbfe16443e50328bc5e2d745fe80f34981f9
checkpoint:         assurance/layers/13-scope-ce-l13-scope-01-shell-config-checkpoint.md
prior review PR:    EGAILab/minion-agent-docs#127
prior review SHA:   54184816b0fbfa0416a16f519af2c232c7ed47dd
pinned Pi:          b7bb00b936dbe21b8e160b3e89efdec361846699
```

The candidate was fetched from the GitHub pull-request ref and matched issue #47. The issue was
open, assigned `NEXT_OWNER = Codex`, carried convergence episode `CE-L13-SCOPE-01`, and explicitly
withheld Layer 13 implementation authorization.

The challenge independently re-read pinned `packages/coding-agent/src/utils/shell.ts`, including
`getShellConfig`, `findBashOnPath`, `getBashShellConfig`, and `isLegacyWslBashPath`, before
assessing the proposed matrix.

## Correctly characterized surface

The checkpoint now correctly separates the missing explicit-path error from Windows automatic-
search exhaustion; records the Windows and ordinary Unix search order; records Unix's silent
`sh -c` fallback; captures Windows's recheck of `where` output versus Unix's trust of `which`
output; and accurately states the anchored, case-insensitive legacy-WSL path regex and resulting
stdin transport.

## Challenge findings

### CE-L13-C001 — “provided” is not the branch condition

**Classification:** `CONTRACT_ASSURANCE_DEFECT`

The decision table asks whether `customShellPath` was “provided” and sends every provided value
through `existsSync`. Pinned Pi actually uses JavaScript truthiness:

```ts
if (customShellPath) { ... }
```

Therefore `customShellPath = ""` follows the platform-default search, not the explicit-path
missing error. This missing/empty distinction is observable and is a standard cross-language
hazard.

**Required correction:** say “truthy/non-empty customShellPath” and add the empty-string case to
the matrix as a negative control that proceeds to platform selection.

### CE-L13-C002 — the claimed closed set of stdin-capable branches is too narrow

**Classification:** `CONTRACT_ASSURANCE_DEFECT`

The checkpoint says Unix branches can *never* produce a string matching the legacy-WSL regex.
That conclusion is not guaranteed by Pi source. Unix `findBashOnPath` trusts the first stdout line
from the externally resolved `which` command without `existsSync`, normalization, or a Unix-path-
shape check, and passes that string directly to `getBashShellConfig`. A nonstandard/shadowed
`which` can therefore return `C:\Windows\System32\bash.exe`, causing Unix branch 3b to select
stdin transport. Normal Unix `which` output will be a Unix path, but Pi does not enforce that.

**Required correction:** distinguish normal expected path shapes from source-enforced behavior.
The source-enforced set is: every successful branch except the literal `sh` fallback passes its
returned string through the same matcher; any matching string selects stdin transport.

### CE-L13-C003 — probe failure is broader than caught exceptions

**Classification:** `CONTRACT_ASSURANCE_DEFECT`

The checkpoint says a timeout is an exception caught by `findBashOnPath`. `spawnSync` can report a
timeout/spawn failure in its returned result (for example via `result.error` and a non-success
status) rather than throwing. Pi does not inspect `result.error`; it returns `null` whenever the
success/status/stdout/first-line checks fail, while its `catch` separately converts actually
thrown exceptions to the same `null` outcome.

The observable fallback-to-null conclusion is correct, but the proposed “exact” mechanism and
failure characterization is not.

**Required correction:** characterize both paths: unsuccessful/missing/empty/untrusted result
checks return `null`, and thrown probe exceptions are also caught and return `null`. Do not claim
all timeout behavior is handled specifically by the catch block.

## Checkpoint verdict

```text
CHECKPOINT REVIEW
    REJECTED

CONVERGENCE EPISODE
    CE-L13-SCOPE-01 remains active

OPEN FINDING
    L13-S002

IMPLEMENTATION AUTHORIZED
    NO
```

The corrections remain narrow and documentary. They do not require Layer 12 reopening, a new
manifest requirement, or implementation work. Publish a revised checkpoint covering these three
dimensions and return it for another independent checkpoint review.
