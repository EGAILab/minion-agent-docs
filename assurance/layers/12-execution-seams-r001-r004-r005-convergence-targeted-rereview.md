# Layer 12 WP-12.1 — convergence targeted closure re-review

## Exact target

- Code PR `EGAILab/minion-agent#40` @
  `71a341802349e0c6f706d599648f8566153318eb`
- Docs PR `EGAILab/minion-agent-docs#110` @
  `dc187d0f061ae80f89699f9e97d755bf3253ecd9`
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Convergence episode: `CE-L12-01-01`
- Prior targeted review: docs PR #114,
  `assurance/layers/12-execution-seams-r001-r008-convergence-targeted-review.md`
  @ `1644536aa70c53d26d1f47d3292cd4d99f9e2755`
- Known-bad predecessor: code
  `2e925792b0ff4ccd54e538c42917561974e2d2ce`, docs
  `e202076fc0c78471b96aa3838f18545ac66b0b95`

Issue `EGAILab/minion-agent#39` was open and named `NEXT_OWNER: Codex`,
the exact remote-reachable heads above, valid scope provenance, and a targeted
section 11.8.7 review of only `L12-R001`, `L12-R004`, and `L12-R005` plus
confirmation that the five prior provisional closures remained undisturbed.
Both candidate PRs were open, Ready for Review, and unmerged.

This is not a final section 11.8.8 review. No implementation was performed.

## Targeted result

| Finding | Independent result | Status |
|---|---|---|
| `L12-R001` | The main table and manifest now consistently say accept-but-ignore, but live section 3.4 still says `append_file` “does not accept” the signal | **STILL OPEN (further refined)** |
| `L12-R004` | The frozen design now scopes typed results to expected operational/environmental failures and preserves invariant/provider/programming exceptions | **PROVISIONALLY CLOSED** |
| `L12-R005` | The contract now accurately exposes Pi's symlinked-ancestor exception and uses resolved-location equality consistently | **PROVISIONALLY CLOSED** |

The existing provisional closures of `L12-R002`, `L12-R003`, `L12-R006`,
`L12-R007`, and `L12-R008` remain valid for these exact candidate heads.

## Remaining finding

### L12-R001 — one live subsection still contradicts the uniform typed signature

The remediation correctly establishes the intended rule in the operation
inventory, section 3.1, its witnesses, and `EXEC-002`:

```text
all FileSystem operations accept signal?
ten concrete operations accept it but do not inspect it
```

Pinned Pi's `FileSystem` interface independently confirms that both
`appendFile` and `fileInfo` carry the optional abort signal. The concrete
reference implementation's omission becomes accept-and-ignore at the uniform
Minion typed boundary.

However, live normative section 3.4 still says:

```text
append_file does not accept or check signal at all
```

That preserves the exact typed-API contradiction the remediation was meant to
remove, now limited to one operation-specific paragraph.

**Refined documentary/type witness**

```text
setup
    value typed as the public ctx.fs seam; any optional signal

call
    append_file(path, content, signal)

section 3.1 / EXEC-002 outcome
    call type-checks; signal is ignored

section 3.4 outcome
    call cannot be represented because append_file does not accept signal

required correction
    section 3.4 must say append_file accepts the uniform optional signal but
    does not inspect it, matching section 3.1 and EXEC-002
```

**Negative control:** the known-bad docs SHA and this exact candidate both
contain the “does not accept” section 3.4 sentence. Therefore the candidate
does not yet pass the refined witness and `L12-R001` cannot close.

Classification: `CONTRACT_ASSURANCE_DEFECT`.

## Provisional closures

### L12-R004 — PROVISIONALLY CLOSED

The known-bad design universally said every failure, including unexpected
backend failures, returned a typed value. The candidate now limits that rule to
expected operational/environmental failures and explicitly preserves
framework/provider invariant and programming exceptions. The adjacent table,
frozen design summary, and `spec/execution.md` section 2 now select one result.
The known-bad documentary witness fails; this candidate passes.

### L12-R005 — PROVISIONALLY CLOSED

Pinned Pi's `getMutationQueueKey` was re-read directly: canonical path is used
when available and absolute path is the `not_found`/`not_supported` fallback.
The candidate now states the actual consequence rather than promising an
impossible stronger invariant:

- ordinary missing-to-created paths without a symlinked ancestor remain
  stable;
- missing-to-created paths beneath a symlinked ancestor may change from the
  lexical absolute key to the canonical key;
- equality is defined by resolved location, so existing symlink/target paths
  still share a key;
- the stronger exception is disclosed as behavior inherited from Pi's real
  mechanism, while `FsTarget` remains a Minion architectural shape.

The known-bad candidate asserted equality for the symlinked-ancestor witness;
the exact candidate requires inequality and therefore passes the executable
negative control. This is coherent with the owner-scoped requirement: before
creation there is no underlying resource, while equivalent paths to an
existing resource still canonicalize to one key.

## Previously closed findings remain undisturbed

The remediation diff is restricted to:

- the R001 public-signature clarification in `spec/execution.md` and
  `EXEC-002`;
- the R004 frozen-design sentence;
- the R005 target-key clarification in `spec/execution.md` and `EXEC-003`.

The settled rename/remove symlink matrix (`R002`), Pi-consumer rationale
(`R003`), subprocess lifecycle (`R006`), 100 ms shell grace (`R007`), and
manifest disposition structure (`R008`) were not changed. The R001 wording
defect does not recreate R008's former mixed-disposition problem: the intended
row subject and disposition are coherent; one live spec paragraph is stale.

## Structural evidence

- `uv run pytest tests/conformance/test_manifest_validation.py --no-cov -q`:
  `8 passed`.
- No Python or Rust Layer-12 implementation exists.
- No certified lower-layer semantic delta is required.

## Verdict

```text
targeted convergence closure
    REJECTED

newly provisionally closed
    L12-R004
    L12-R005

previous provisional closures retained
    L12-R002
    L12-R003
    L12-R006
    L12-R007
    L12-R008

still open
    L12-R001

workflow state
    CONTRACT_CONVERGENCE (CE-L12-01-01)

shared Layer-12 WP-12.1 contract
    NOT APPROVED FOR IMPLEMENTATION

Python Layer 12
    NOT_IMPLEMENTED / BLOCKED

Rust Layer 12
    NOT_IMPLEMENTED / BLOCKED

Layer 12 cross-language
    NOT CLOSED

Layer 13
    NOT STARTED
```

This verdict applies only to code
`71a341802349e0c6f706d599648f8566153318eb` and docs
`dc187d0f061ae80f89699f9e97d755bf3253ecd9`.

## Next action

Claude performs a one-sentence normative repair to section 3.4 so
`append_file` accepts-but-does-not-inspect the uniform optional signal. Search
the current normative document for any other non-historical “does not accept”
claim before handoff. Preserve all seven provisional closures.

The next pass is another targeted section 11.8.7 closure review of only
`L12-R001` and affected dependencies. Do not begin Python or Rust Layer 12
implementation and do not start Layer 13. A section 11.8.8 final review is not
available until `L12-R001` is provisionally closed.
