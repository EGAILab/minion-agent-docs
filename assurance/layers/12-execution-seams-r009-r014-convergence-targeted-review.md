# Layer 12 WP-12.1 - CE-L12-01-02 targeted closure review

## Exact target

- Code PR `EGAILab/minion-agent#40` @
  `8201e611a01d5849da4afdb612ef1134452be313`
- Docs PR `EGAILab/minion-agent-docs#110` @
  `f12b7e2f58983905248ff4a4411db35913ce3d44`
- Convergence agreement PR `EGAILab/minion-agent-docs#115` @
  `9c1171e6e427c0b709fceae00b82f04d04bbb697`
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Episode: `CE-L12-01-02`
- Known-bad candidate: code
  `71a341802349e0c6f706d599648f8566153318eb`, docs
  `1279c0287d03a3ba42fa32d3ee6b25fc42b04e8a`

Issue `EGAILab/minion-agent#39` was open with
`STATUS = CONTRACT_CONVERGENCE`, `NEXT_OWNER = Codex`, the candidate heads
above, and an instruction to perform the mandatory section 11.8.7 targeted
closure review. All three referenced PR heads were remote-reachable. Candidate
PRs #40/#110 were open, Ready for Review, and unmerged.

This is review evidence only. It does not implement Layer 12, modify the
candidate, approve a final contract, or start Layer 13.

## Scope and authority

Review scope was limited to `L12-R009` through `L12-R014`, their semantic
dependencies, and high-risk rules touched by the coherent fix. The review
rechecked pinned Pi's relevant `nodejs.ts` methods before comparing the spec,
manifest, agreement, and witness matrix. No Python Layer-12 implementation
exists and none was used as an oracle.

Candidate changes are confined to:

- `pi-parity-manifest.yaml`: `EXEC-002` through `EXEC-006` rule text;
- `spec/execution.md`: the agreed cancellation, shell, subprocess,
  compatibility, `process_path`, remediation-history, and witness sections.

No certified Layer 01-11 code/contract and no Layer-13 surface changed.

## Closure ledger

| Finding | Targeted result | Reason |
|---|---|---|
| `L12-R009` | **PROVISIONALLY CLOSED** | Complete Pi checkpoint/order table now distinguishes `read_text_lines`, `list_dir`, and `write_file`. |
| `L12-R010` | **PROVISIONALLY CLOSED** | Exact Pi pre-spawn sequence now puts shell discovery before cwd existence. |
| `L12-R011` | **PROVISIONALLY CLOSED** | Exact `2_147_483_647ms` multiplication boundary is normative. |
| `L12-R012` | **PROVISIONALLY CLOSED** | Subprocess omitted/relative cwd and both environment modes are now defined. |
| `L12-R013` | **STILL OPEN (refined)** | Broader-than-equality compatibility is permitted without a symmetric/direction-independent relation or declaration model. |
| `L12-R014` | **STILL OPEN (refined)** | Foreign-provider `process_path` is simultaneously undefined and required to return `FsError(invalid)` when detectable. |

The prior `L12-R001` through `L12-R008` provisional closures remain
undisturbed. Because two episode findings remain open, this candidate is not
eligible for another final complete review.

## L12-R009 - PROVISIONALLY CLOSED

Pinned Pi was rechecked at `nodejs.ts:502-633`. Current section 3.1 and
`EXEC-002` now bind all relevant phase boundaries:

- single underlying signal-aware read for text/binary reads;
- `write_file`: pre-check, uninterruptible parent mkdir, explicit post-mkdir
  check, signal-aware write;
- `read_text_lines`: pre-check, signal-aware stream, each-iteration check,
  post-loop check;
- `list_dir`: pre-check and each-entry check, no post-loop check;
- `rename_file`: pre-check only.

### Negative-control record

```text
finding ID
    L12-R009

method
    exact known-bad/candidate documentary contract comparison against pinned
    source; executable implementation does not yet exist

known-bad SHA
    docs 1279c0287d03a3ba42fa32d3ee6b25fc42b04e8a

expected/observed failure
    grouped read_text_lines with list_dir and omitted the former's post-loop
    check; grouped write_file under generic mid-I/O wording and omitted the
    explicit post-mkdir checkpoint

candidate SHA / observed pass
    docs f12b7e2f58983905248ff4a4411db35913ce3d44
    exact operations/checkpoints and discriminating witnesses are present in
    spec and EXEC-002
```

## L12-R010 - PROVISIONALLY CLOSED

Pinned Pi's source order remains exactly:

```text
pre-abort -> timeout validation -> lexical cwd resolution -> shell discovery
-> cwd existence check -> spawn
```

Section 5.4 and `EXEC-004` now say that explicitly, including the combined
nonexistent-shell/nonexistent-cwd outcome (`shell_unavailable`).

### Negative-control record

```text
finding ID
    L12-R010

method
    exact known-bad/candidate documentary comparison

known-bad SHA / observed failure
    docs 1279c0287d03a3ba42fa32d3ee6b25fc42b04e8a
    combined cwd/shell step permitted cwd-first spawn_error

candidate SHA / observed pass
    docs f12b7e2f58983905248ff4a4411db35913ce3d44
    separate ordered steps and combined-invalidity witness require
    shell_unavailable
```

## L12-R011 - PROVISIONALLY CLOSED

The candidate now states the actual Pi rule, not an approximation:

```text
reject iff timeout * 1000 > 2_147_483_647
2147483.647 seconds accepted
2147483.648 seconds rejected
```

The immediately-next IEEE-754 value above `2147483.647` also multiplies above
the ceiling, so the stated boundary does not hide a representable float gap.

### Negative-control record

```text
finding ID
    L12-R011

method
    known-bad/candidate documentary comparison plus IEEE-754 boundary probe

known-bad SHA / observed failure
    docs 1279c0287d03a3ba42fa32d3ee6b25fc42b04e8a
    "roughly 2^31/1000" permits 2147483.648

candidate SHA / observed pass
    docs f12b7e2f58983905248ff4a4411db35913ce3d44
    exact multiplication rule and boundary pair are normative
```

## L12-R012 - PROVISIONALLY CLOSED

Section 6 and `EXEC-005` now define:

- omitted cwd -> provider cwd;
- relative cwd -> lexical resolution against provider cwd using the shared
  filesystem rule;
- `inherit_env=true` -> provider base environment overlaid by call `env`;
- `inherit_env=false` -> exactly call `env` (empty if omitted).

These are Minion-extension rules, correctly not attributed to Pi.

### Negative-control record

```text
finding ID
    L12-R012

method
    exact known-bad/candidate documentary comparison

known-bad SHA / observed failure
    docs 1279c0287d03a3ba42fa32d3ee6b25fc42b04e8a
    declared cwd/env fields with no default/resolution/merge behavior

candidate SHA / observed pass
    docs f12b7e2f58983905248ff4a4411db35913ce3d44
    all four observable choices and child-observation witnesses are explicit
```

## L12-R013 - STILL OPEN (refined)

The candidate is improved: it defines an identity, `compatible(a,b)`,
`validate(...)`, equality as sufficient, and a typed error. But it also permits
a provider to declare compatibility with selected *other* identities without
defining how that declaration participates in the free compatibility function
or whether compatibility is symmetric.

That omission is observable. Suppose unequal identity `A` declares `B`
compatible, while `B` does not declare `A`. All of these remain plausible:

```text
compatible(A, B) = true; compatible(B, A) = false
compatible(A, B) = compatible(B, A) = true   # either-side opt-in
compatible(A, B) = compatible(B, A) = false  # mutual opt-in required
```

`validate([("a", A), ("b", B)])` can consequently depend on input order or
implementation choice. The current acceptance matrix tests only equal
identities and unequal non-family identities, so it does not discriminate this
explicitly-permitted broader-relation case.

### Refined discriminating witness

```text
setup
    two unequal identities A/B; only A declares B compatible

exercise
    compatible(A,B), compatible(B,A), validate([a,b]), validate([b,a])

required property
    both compatible calls and both validation permutations must have the same
    outcome under one explicitly-defined symmetric rule

current candidate failure
    does not choose the outcome or define the declaration representation/
    combination rule
```

Minimal correction: either make compatibility equality-only, or define a
symmetric broader relation (for example mutual declaration or shared family)
and bind the permutation witness. Do not leave provider order observable.

## L12-R014 - STILL OPEN (refined)

The candidate removed the compatible-provider success allowance, but replaces
it with two incompatible rules in the same live bullet:

```text
calling process_path on any non-producing provider
    OUTSIDE contract / undefined

provider detects it did not produce target
    MUST return FsError(invalid)
```

The witness matrix compounds the contradiction by saying a candidate requiring
a specific error is wrong, while the normative bullet requires that exact
error when detection is possible. One implementation may type/provenance-gate
the call as unrepresentable/undefined; another may accept the call and return
`invalid`. Both cannot be the one contract.

### Refined discriminating witness

```text
setup
    target produced by provider A; call provider B.process_path(target), with
    B able to recognize A's foreign provenance

implementation 1
    rejects with FsError(invalid), following the live MUST

implementation 2
    treats the call as outside the contract, with no required Result,
    following the live undefined rule and witness matrix

current candidate failure
    simultaneously authorizes/requires both classifications
```

Minimal correction: choose one rule. Either (a) foreign calls are outside the
contract and all normative `MUST return invalid` language is removed, or (b)
foreign calls are defined and always return `invalid`, with enough private
provenance to make that total. Keep spec, `EXEC-003`, and the witness matrix
identical.

## Fresh gates

```text
uv run pytest --no-cov
    1504 passed, 19 xfailed

uv run ruff check .
    PASS

uv run pytest --no-cov \
    tests/conformance/test_manifest_validation.py \
    tests/conformance/test_schema_validation.py -q
    213 passed

candidate diffs
    git diff --check PASS (code and docs)
```

Green structural gates do not close `L12-R013`/`L12-R014`.

## Verdict and next action

```text
CE-L12-01-02

PROVISIONALLY CLOSED
    L12-R009 @ code 8201e611a01d5849da4afdb612ef1134452be313 /
               docs f12b7e2f58983905248ff4a4411db35913ce3d44
    L12-R010 @ same candidate
    L12-R011 @ same candidate
    L12-R012 @ same candidate

STILL OPEN (refined)
    L12-R013
    L12-R014

shared WP-12.1 contract
    REJECTED / CONTRACT_CONVERGENCE

Rust Layer 12
    BLOCKED / NOT_IMPLEMENTED

NEXT_OWNER
    Claude

NEXT_ACTION
    Remediate only the refined R013 compatibility symmetry/declaration gap
    and R014 undefined-vs-invalid contradiction, synchronize spec/manifest/
    witnesses, and return the exact remote candidate for another targeted
    closure review. Do not implement Python/Rust Layer 12 and do not start
    Layer 13.
```
