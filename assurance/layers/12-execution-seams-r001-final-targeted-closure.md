# Layer 12 WP-12.1 — final targeted convergence closure

## Exact target

- Code PR `EGAILab/minion-agent#40` @
  `71a341802349e0c6f706d599648f8566153318eb`
- Docs PR `EGAILab/minion-agent-docs#110` @
  `1279c0287d03a3ba42fa32d3ee6b25fc42b04e8a`
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Convergence episode: `CE-L12-01-01`
- Prior targeted closure evidence: docs PR #114 @
  `1644536aa70c53d26d1f47d3292cd4d99f9e2755` and
  `6bb5222158dace4f4b24bb7cea5d06a515aa12ae`
- Known-bad docs SHA for this witness:
  `dc187d0f061ae80f89699f9e97d755bf3253ecd9`

Issue `EGAILab/minion-agent#39` was open, assigned `NEXT_OWNER: Codex`, and
named the exact remote-reachable candidate above. Code PR #40 was unchanged
from the prior targeted review; docs PR #110 changed only one normative
sentence in `spec/execution.md` section 3.4.

This is the final section 11.8.7 targeted closure pass for `L12-R001`. It is
not the section 11.8.8 final complete review and does not approve
implementation.

## L12-R001 — PROVISIONALLY CLOSED

The settled rule is now consistent throughout current normative artifacts:

```text
public typed shape
    every ctx.fs operation accepts signal?

ten concrete non-inspecting operations
    accept the optional signal but do not inspect it

append_file
    is one of those ten operations
```

The exact remediation changes section 3.4 from “does not accept or check” to
“accepts signal ... but does not inspect it,” matching section 3.1, the
operation inventory, the witness matrix, and `EXEC-002`.

Pinned Pi was rechecked at
`packages/agent/src/harness/types.ts`: the `FileSystem.appendFile` and
`FileSystem.fileInfo` interface methods both declare an optional abort signal.
The concrete reference implementation's lack of inspection is represented at
the uniform Minion typed boundary as accept-and-ignore.

### Negative-control record

```text
finding
    L12-R001

method
    exact documentary/type-contract comparison

known-bad SHA
    dc187d0f061ae80f89699f9e97d755bf3253ecd9

known-bad expected/observed failure
    section 3.1 and EXEC-002 require append_file(path, content, signal) to
    type-check and ignore signal, while live section 3.4 says append_file does
    not accept signal; one typed Rust API cannot satisfy both

candidate SHA
    1279c0287d03a3ba42fa32d3ee6b25fc42b04e8a

candidate observed pass
    section 3.4 now says append_file accepts the uniform signal and does not
    inspect it; no current normative Minion rule says otherwise
```

The remaining search hits are not contradictory current requirements:

- section 3.1's source characterization says pinned Pi's concrete
  `NodeExecutionEnv` does not itself accept/check those arguments;
- the remediation/history section records the old contradiction as history.

Neither overrides the explicit current Minion public API rule.

## Regression confirmation

The one-sentence docs diff does not touch the settled rules behind
`L12-R002` through `L12-R008`. Their provisional closures remain valid at
this exact candidate pair.

Fresh structural evidence:

- `uv run pytest tests/conformance/test_manifest_validation.py --no-cov -q`:
  `8 passed`;
- code PR #40 is unchanged at the previously reviewed SHA;
- no Python or Rust Layer-12 implementation exists;
- Layer 13 remains not started.

## Settled convergence record

```text
CE-L12-01-01

PROVISIONALLY CLOSED
    L12-R001 @ code 71a341802349e0c6f706d599648f8566153318eb /
               docs 1279c0287d03a3ba42fa32d3ee6b25fc42b04e8a
    L12-R002 @ prior targeted evidence retained
    L12-R003 @ prior targeted evidence retained
    L12-R004 @ prior targeted evidence retained
    L12-R005 @ prior targeted evidence retained
    L12-R006 @ prior targeted evidence retained
    L12-R007 @ prior targeted evidence retained
    L12-R008 @ prior targeted evidence retained

OPEN FINDINGS
    none
```

## Verdict and next action

```text
targeted convergence closure
    PASSED

shared Layer-12 WP-12.1 contract
    NOT YET APPROVED FOR IMPLEMENTATION

workflow transition
    CONTRACT_CONVERGENCE -> FINAL_CONTRACT_REVIEW

Python Layer 12
    NOT_IMPLEMENTED / BLOCKED PENDING FINAL REVIEW

Rust Layer 12
    NOT_IMPLEMENTED / BLOCKED PENDING FINAL REVIEW

Layer 12 cross-language
    NOT CLOSED

Layer 13
    NOT STARTED
```

Freeze the exact code/docs candidate pair above and perform one complete,
independent section 11.8.8 contract review. Do not begin Python or Rust Layer
12 implementation and do not start Layer 13 in this targeted closure pass.
