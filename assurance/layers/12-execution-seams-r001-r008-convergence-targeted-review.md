# Layer 12 WP-12.1 — convergence targeted closure review

## Exact review target

- Code PR `EGAILab/minion-agent#40` @
  `2e925792b0ff4ccd54e538c42917561974e2d2ce`
- Docs PR `EGAILab/minion-agent-docs#110` @
  `e202076fc0c78471b96aa3838f18545ac66b0b95`
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Convergence episode: `CE-L12-01-01`
- Agreed convergence checkpoint: docs PR #113,
  `assurance/layers/12-execution-seams-r001-r008-convergence-agreement.md` @
  `1c00ad0de990bb53d884103a9cbf71b2c8ad373e`
- Known-bad predecessor: code
  `1572bda4bb35a4bf4382e0aaea29b6fafd24ad4a`, docs
  `89da9afde11e183d5c4ed7ee19893a819d1cd55b`
- Prior independent re-review: docs PR #112,
  `assurance/layers/12-execution-seams-rust-contract-rereview.md` @
  `89d826e101310c07a59eddd072f4d80cd7384ef0`

Issue `EGAILab/minion-agent#39` was open and its current-state block named
`status: CONTRACT_CONVERGENCE`, `next_owner: Codex`, the exact candidate SHAs
above, and valid owner-authored scope provenance. PRs #40, #110, and #113 were
open, Ready for Review, unmerged, mergeable, and remote-reachable. The handoff
was valid under `agent-workflow.md` section 11.11.

This is the mandatory targeted closure review required by section 11.8.7. It
is deliberately limited to `L12-R001` through `L12-R008` and their semantic
dependencies. It is not the final complete review required by section 11.8.8.
No Python, Rust, shared semantic, canonical, or Layer-13 implementation file
was modified.

## Authority and evidence checked

The review re-used no implementation as a semantic oracle. It checked the
candidate against:

1. pinned Pi `FileSystem`, `NodeExecutionEnv`, shell settlement, and
   `getMutationQueueKey` source;
2. the frozen design;
3. `spec/execution.md`;
4. `EXEC-001` through `EXEC-006` in `pi-parity-manifest.yaml`;
5. the independently agreed convergence behavior matrix and witnesses.

The targeted pass also repeated the symlink probes and the path-key reasoning
that discriminate the settled rules. Structural validation remains necessary
but does not override the three semantic contradictions below.

## Closure ledger

| Finding | Candidate result | Classification | Targeted status |
|---|---|---|---|
| `L12-R001` | The per-operation behavior table is present, but the public operation inventory and witness still accept `signal?` for methods the same section says do not accept a signal | `CONTRACT_ASSURANCE_DEFECT` | **STILL OPEN (refined)** |
| `L12-R002` | Rename/remove now operate on the symlink directory entry; the full matrix is coherent | — | **PROVISIONALLY CLOSED** |
| `L12-R003` | Frozen design and spec now state the same narrower Pi-consumer claim | — | **PROVISIONALLY CLOSED** |
| `L12-R004` | The stale error codes are removed, but the design still says every failure, including unexpected backend failures, becomes a typed value before separately exempting invariant/provider failures | `CONTRACT_ASSURANCE_DEFECT` | **STILL OPEN (refined)** |
| `L12-R005` | Location identity is selected, but the canonical-or-absolute algorithm changes key across missing-to-created under a symlinked ancestor and the prose also says all different paths have unequal keys | `CONTRACT_ASSURANCE_DEFECT` | **STILL OPEN (refined)** |
| `L12-R006` | One spawn signal, process-exit-only wait, and explicit wait/terminate ownership are now unambiguous | — | **PROVISIONALLY CLOSED** |
| `L12-R007` | The exact nominal 100 ms, reset-on-post-exit-data, and early end/close rule are now binding | — | **PROVISIONALLY CLOSED** |
| `L12-R008` | `EXEC-002` now contains one coherent adopted subject: Pi's actual per-method behavior | — | **PROVISIONALLY CLOSED** |

## Findings that remain open

### L12-R001 — accepted-but-ignored versus not-accepted signal is contradictory

The candidate correctly lists the ten concrete Pi methods that do not inspect
the signal. It does not settle their public typed API shape consistently:

- `spec/execution.md` section 3's operation inventory declares `signal?` on
  all sixteen operations, including `file_info(path, signal?)`;
- section 3.1 says the ten methods “do not accept or check a signal at all”;
- the permanent witness calls `file_info(path, signal)` and expects success.

Pinned Pi explains why this distinction was easy to blur: the `FileSystem`
interface declares an optional signal everywhere, while JavaScript permits the
concrete method to receive an extra argument that it ignores. An independent
typed Rust API cannot implement both “does not accept” and “accepts and
ignores” at once.

**Refined discriminating witness**

```text
setup
    existing file; pre-aborted signal; value typed as the public FileSystem seam

call
    file_info(path, signal)

required observation
    the call is representable through the public typed API and returns FileInfo;
    the signal is ignored

candidate contradiction
    the signature and witness require the call to compile, while the binding
    table says file_info does not accept the argument

negative control
    a Rust trait omitting the signal parameter fails at compile time; a trait
    accepting it but returning aborted fails behaviorally
```

This is a new, narrower witness than the prior pre-abort behavior finding. The
minimal correction is to use one phrase consistently, most naturally
“accepts the interface's optional signal but does not inspect it,” or else to
remove the argument from both the inventory and witness and explicitly govern
that cross-language API mapping.

### L12-R004 — frozen-design error rule still contradicts itself

The coherent pass correctly removed `non-zero process exit`, `stale version`,
and `remote unavailable` from the design's Values row. The design still says:

```text
execution-seam operations never raise; every failure, including unexpected
backend failures, returns a typed error value
```

and, immediately below, says provider invariant violations, broken provider
implementations, assertion failures, and programming errors remain exceptions.
The latter rule matches `spec/execution.md`; the former universal statement
does not. “Unexpected backend failure” can itself be a broken-provider or
invariant failure under the next paragraph, so the two current authoritative
sentences permit opposite Rust implementations.

**Refined documentary witness**

```text
setup
    provider violates an internal invariant and throws/panics before producing
    an operational FsError/ShellError/SubprocessError

reader A
    follows “every failure, including unexpected backend failures” and converts it

reader B
    follows the adjacent exceptions table and lets the invariant failure escape

required observation
    only reader B matches spec/execution.md section 2 and the agreed boundary
```

The minimal correction is documentary: scope the first sentence to expected
operational/environmental failures and leave the adjacent exception rule
intact. No semantic expansion is needed.

### L12-R005 — the target-key algorithm is unstable through create under a symlinked ancestor

The candidate selects the agreed location identity and correctly rejects
inode/content-hash identity. Its specified algorithm is nevertheless not
closed over the agreed missing-to-create and symlink dimensions:

```text
target_key = canonical_path(path) if it exists, else absolute_path(path)
```

For a missing `link/new.txt` where `link` is a symlink to `real`, the first
resolution falls back to the lexical absolute `.../link/new.txt`. After the
file is created, canonicalization succeeds and returns `.../real/new.txt`.
The key changes even though the candidate says missing-to-created is stable
and a symlinked path and its target always share one key.

**Executable refined witness run during this review**

```text
setup
    mkdir real
    symlink link -> real
    new path = link/new.txt (initially absent)

before create
    canonicalization fails; fallback key = absolute(link/new.txt)

after create through link
    canonical key = realpath(real/new.txt)

observed
    keys are unequal
```

The Node probe produced:

```json
{"before":"...\\link\\new.txt","after":"...\\real\\new.txt","equal":false}
```

This is a realistic negative control for the exact candidate algorithm, not a
new implementation preference. The contract must choose a coherent
location-key derivation for missing descendants of symlinked existing
ancestors (for example, resolving the nearest existing ancestor and appending
the unresolved suffix), or explicitly revise one of the claimed invariants.
It must accurately label any stronger-than-Pi missing-path normalization as a
Minion architectural mapping rather than saying it mirrors Pi's fallback
exactly.

The same section also says “two resolve calls for different paths produce
unequal keys,” which directly contradicts the required symlink/target equality
for two different paths. The sentence must say different **resolved
locations**, not merely different paths.

## Provisional closures and negative-control gates

### L12-R002 — PROVISIONALLY CLOSED

The known-bad docs SHA grouped `rename_file` with follow-target content I/O and
omitted `remove`. The exact candidate separates both as directory-entry
operations. The prior direct Node probes are discriminating: renaming a link
moves the link while preserving the target; recursively removing a directory
link removes only the link. Known-bad text fails both; the candidate rule
passes both. The finding is provisionally closed for these exact SHAs.

### L12-R003 — PROVISIONALLY CLOSED

The known-bad design said no Pi consumer takes `FileSystem` alone. The exact
candidate names `JsonlSessionRepoFileSystem` as the counterexample and narrows
the combined-environment statement to Pi's execution tools. Design section 7
and spec section 1 now agree. This inherently documentary negative control
fails on the known-bad docs SHA and passes on the candidate.

### L12-R006 — PROVISIONALLY CLOSED

The known-bad candidate exposed independently abortable spawn and wait signals,
left wait versus stream EOF unsettled, and promised implicit drop safety. The
exact candidate has one spawn signal, `wait()` has no signal and settles on
direct process exit independently of streams, explicit `terminate()` without
spawn abort maps to `Ok(exit_code: None)`, and implicit drop is expressly
undefined/caller error. The agreed two-signal and inherited-pipe negative
controls are no longer ambiguous. The finding is provisionally closed.

### L12-R007 — PROVISIONALLY CLOSED

The known-bad candidate allowed any “short” grace. The exact candidate pins
nominal 100 ms, resets after post-exit stdout/stderr data, and settles earlier
when both streams end/close. The +80 ms data witness distinguishes this from a
fixed timer: candidate settles about +180 ms, known-bad text permits +100 ms.
The finding is provisionally closed.

### L12-R008 — PROVISIONALLY CLOSED

The original disposition defect was the mixture of actual Pi behavior and an
interface-over-reference divergence under one adopted row. The candidate now
adopts the actual concrete per-method Pi behavior and contains no intentional
cancellation divergence. Manifest structure reports one adopted disposition.
R001's remaining signature wording must still be repaired, but it does not
re-create the original mixed-disposition defect. The finding is provisionally
closed.

## Rust implementability

Rust can implement the provisionally closed symlink, process, shell, and
manifest rules idiomatically using typed traits, futures, explicit ownership,
and existing Runtime signal primitives. No certified lower layer needs a
semantic delta.

Rust still cannot implement the exact candidate without guessing:

1. whether ten `FileSystem` methods accept-and-ignore an optional signal or
   omit it from the typed API;
2. which design sentence governs invariant/backend failures;
3. how a missing path under a symlinked existing ancestor retains one
   `target_key` through creation.

Those are shared-contract questions, not Rust implementation preferences.

## Structural gate

Fresh checks against the exact candidate:

- `uv run pytest tests/conformance/test_manifest_validation.py --no-cov -q`:
  `8 passed`;
- manifest inventory: `101` rows, `101` unique IDs;
- `EXEC-001` through `EXEC-006` are present;
- no Layer-12 Python or Rust implementation exists, as expected at this
  contract checkpoint.

These checks confirm artifact structure only. They do not close the three
semantic contradictions above.

## Verdict

```text
targeted convergence closure
    REJECTED

provisionally closed
    L12-R002
    L12-R003
    L12-R006
    L12-R007
    L12-R008

still open
    L12-R001
    L12-R004
    L12-R005

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
`2e925792b0ff4ccd54e538c42917561974e2d2ce` and docs
`e202076fc0c78471b96aa3838f18545ac66b0b95`.

## Next action

Claude performs a coherent, narrowly scoped remediation of the refined
`L12-R001`, `L12-R004`, and `L12-R005` witnesses. The five provisional
closures remain valid only while their settled rules and candidate evidence
are not disturbed. Any new candidate requires another section 11.8.7 targeted
closure review of the remaining open findings and affected dependencies.

Do not begin Python or Rust Layer 12 implementation. Do not start Layer 13.
The section 11.8.8 final complete review remains unavailable until every
finding in `CE-L12-01-01` is provisionally closed.
