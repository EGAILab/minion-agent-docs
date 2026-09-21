# Layer 12 Python convergence targeted closure review 8

Mode: targeted finding-closure review (`agent-workflow.md` section 11.8.7)

Verdict: **APPROVED - L12-PY-R002 PROVISIONALLY CLOSED**

## Exact target

- Python implementation PR: `EGAILab/minion-agent#44`
- reviewed Python SHA: `b9c04e00aa2803304b7e9c1f5462e15eb524a709`
- approved root-characterization checkpoint PR: `EGAILab/minion-agent-docs#121`
- reviewed/approved checkpoint SHA: `00afd5178d5c1bed4ec5175eea873061a9928fb1`
- checkpoint approval evidence PR: `EGAILab/minion-agent-docs#120`
- checkpoint approval evidence SHA: `5b26d36ca18a3fe7f936ec4f980957e469144d5f`
- known-bad implementation SHA used for the negative control:
  `1848873fc9626b699990a29b1f35c7baba78cc34`
- certified Rust baseline, read-only: `2b309ee8cecbc333a7965781087677bd6cbba46b`
- last Rust implementation touch: `429368cd91ba8c3c9857d44b4d9807bb3269206f`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`

The coordination issue was open and valid, recorded `STATUS = CONTRACT_CONVERGENCE` and
`NEXT_OWNER = Codex`, and named the same remote-reachable candidate/checkpoint SHAs. PR #44 and
PR #121 were open, ready for review, mergeable, and unmerged. The candidate declares that it is
not derived from a quarantined artifact and carries the existing durable Layer-12 governance
source. This review modified no Python, shared semantic, canonical, or Rust implementation file.
Layer 13 was not started.

## Scope

Per section 11.8.7, this review is limited to:

```text
L12-PY-R002
    agreed Ada-2.9.2 root-characterization implementation

semantic dependencies touched by the fix
    Python dependency pin/lock
    file:// host validation and Punycode-to-Unicode conversion
    committed differential corpus and permanent pytest gate
    EXEC-002 implementation/evidence history

high-risk regressions affected by the fix
    existing filesystem/file-URL language tests
```

`L12-PY-R004-A` remains provisionally closed and was not reopened. This is not the final complete
review required by section 11.8.8. Rust's three identified surfaces remain
`REVALIDATE_REQUIRED` and were not reviewed as closed here.

## Checkpoint-to-implementation verification

| Agreed checkpoint requirement | Independent observation | Result |
|---|---|---|
| Exact dependency pin | `pyproject.toml` contains `ada-url==1.15.3`; `uv.lock` resolves exactly `1.15.3` | PASS |
| No version floor/range | no `>=`, `~=`, or compatible range remains for `ada-url` | PASS |
| Remove rejected mixed-version composition | production imports/calls neither third-party `idna` nor `unicodedata`; `_relaxed_punycode_label` and `_relaxed_codepoint_ok` are absent | PASS |
| Delegate decode to Ada | `_domain_to_unicode` is a one-line call to `ada_url.idna_to_unicode` | PASS |
| Validate through the same Ada version | `_file_url_to_path` constructs `ada_url.URL` before decoding and retains the agreed unchanged-`xn--` rejection convention | PASS |
| Permanent 8,246-case gate | the new pytest loads committed inputs/expected outputs and invokes the real `_file_url_to_path` seam for every row | PASS |
| Gate stays thin | the test contains no IDNA/Punycode/host-validation implementation; it only loads, dispatches, and compares | PASS |
| Corpus copied verbatim | both corpus files have the exact same Git blob IDs as checkpoint SHA `00afd517...` | PASS |
| Required named witnesses | `xn--3pc` and `xn--8g0n` occur literally in both committed datasets and are executed by the gate | PASS |
| Existing finite regression corpus | focused filesystem tests pass unchanged at the observable seam | PASS |
| History preserved | EXEC-002 appends the final root-cause/resolution record rather than rewriting prior failed approaches | PASS |
| Rust untouched | candidate diff contains no `minion-agent-rust/**` path; last Rust touch remains `429368c...` | PASS |

The `idna` distribution remains present transitively through `httpx`, but it is no longer a direct
project dependency and no Layer-12 filesystem production path imports or uses it. That is
consistent with the checkpoint, which eliminated its role in this decode responsibility rather
than requiring unrelated transitive dependency removal.

## Real-seam and corpus evidence

The code-side copies are byte-identical to the approved checkpoint evidence:

```text
systematic_corpus.txt
    code blob b2fe1a66d74c02d102a81a2a51e81adb6923bc23
    docs blob b2fe1a66d74c02d102a81a2a51e81adb6923bc23

systematic_ada292.txt
    code blob 8c9f23a747c4bf6e137cb3f12d85e83013d914c6
    docs blob 8c9f23a747c4bf6e137cb3f12d85e83013d914c6
```

The gate verifies 8,246 inputs, checks the committed corpus count and cross-file key-set equality,
then invokes production `_file_url_to_path` for each input. On Windows it compares the returned
UNC path or rejection with the direct Ada-2.9.2 oracle output. It does not reconstruct expected
host conversion in the runner.

The two required witnesses are genuinely discriminating:

```text
file://xn--3pc/share
    oracle/candidate: accepted as UNC host U+0C3C TELUGU SIGN NUKTA
    known-bad 1848873f: rejected

file://xn--8g0n/share
    oracle/candidate: rejected
    known-bad 1848873f: accepted as U+2EBF0 and returned as a UNC path
```

## Section 11.8.7.1 negative control

```text
finding ID
    L12-PY-R002

negative-control method
    execute the same committed 8,246-case corpus/oracle comparison against the real
    _file_url_to_path imported from the exact known-bad prior implementation worktree

known-bad SHA
    1848873fc9626b699990a29b1f35c7baba78cc34

expected failure
    at least one differential mismatch, including both xn--3pc and xn--8g0n

observed failure
    1,059 / 8,246 mismatches
    xn--3pc rejected instead of accepted
    xn--8g0n accepted instead of rejected

candidate SHA
    b9c04e00aa2803304b7e9c1f5462e15eb524a709

observed pass
    permanent differential pytest gate passes all 8,246 cases
    focused filesystem suite passes
```

This satisfies the mandatory negative-control gate. It demonstrates that the permanent witness
detects the rejected mixed-version implementation rather than merely passing on the candidate.

## Fresh gates

Run from a clean detached worktree of exact candidate SHA
`b9c04e00aa2803304b7e9c1f5462e15eb524a709`:

```text
uv run pytest
    1724 passed, 4 skipped, 19 xfailed
    100.00% coverage

uv run pytest --no-cov \
    tests/execution/test_filesystem_r002_ada_oracle_gate.py \
    tests/execution/test_filesystem.py -q
    PASS

uv run ruff check .
    PASS

uv run mypy
    PASS - 79 source files

uv run pytest --no-cov tests/conformance/test_manifest_validation.py -v
    8 passed

manifest inventory
    101 rows / 101 unique IDs
```

The first focused invocation without `--no-cov` produced passing focused tests but correctly
failed the repository-wide 100% coverage threshold because only the filesystem subset had been
selected. It was rerun with `--no-cov` for the focused semantic result; the complete `uv run
pytest` invocation independently satisfied the actual 100% coverage gate.

## Findings

```text
PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    none active in this targeted scope

CONTRACT_ASSURANCE_DEFECT
    none active in this targeted scope

PARITY_NEUTRAL_HARDENING
    none required

PARITY_CONSTRAINED_RISK
    none new
```

## Verdict

```text
L12-PY-R002
    PROVISIONALLY CLOSED @ b9c04e00aa2803304b7e9c1f5462e15eb524a709

L12-PY-R004-A
    PROVISIONALLY CLOSED - retained from review 6

CE-L12-PY-01-01 open findings
    none

Python Layer 12
    NOT YET CERTIFIED - final complete review remains required

Rust affected surfaces
    REVALIDATE_REQUIRED

Layer 12 cross-language
    NOT CLOSED

Layer 13
    NOT STARTED
```

The candidate is eligible to transition from settled `CONTRACT_CONVERGENCE` to
`FINAL_CONTRACT_REVIEW` under sections 11.8.8 and coordination-state section 6. The convergence
record must remain attached with an empty `open_findings` list and this provisional closure
record. This targeted approval is exact-SHA-bound and is not final certification, Rust
revalidation, or authorization to begin Layer 13.

## Next action

Freeze the exact code/checkpoint pair above, update the current coordination state to
`FINAL_CONTRACT_REVIEW` while preserving convergence provenance, and perform one separate
complete independent section 11.8.8 review. Do not merge the candidate, revalidate/modify Rust,
or start Layer 13 in this targeted-review pass.
