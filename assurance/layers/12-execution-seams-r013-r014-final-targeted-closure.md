# Layer 12 WP-12.1 - R013/R014 final targeted convergence closure

## Exact target

- Code PR `EGAILab/minion-agent#40` @
  `88cf0b4564262cddf2aa5fe1a2de66cbe5dfa99e`
- Docs PR `EGAILab/minion-agent-docs#110` @
  `a4eb07c764ea8006c867f574475779c9fcfa78ae`
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Episode: `CE-L12-01-02`
- Prior targeted evidence: docs PR #114 @
  `ed5a5a6eda2cf3daab9bcf6e1dd49810aba3bb2a`
- Known-bad candidate: code
  `8201e611a01d5849da4afdb612ef1134452be313`, docs
  `f12b7e2f58983905248ff4a4411db35913ce3d44`

Issue `EGAILab/minion-agent#39` was open with
`STATUS = CONTRACT_CONVERGENCE`, `NEXT_OWNER = Codex`, and the exact new
candidate above. Both candidate heads were open, Ready for Review, unmerged,
and remote-reachable.

This is the final section 11.8.7 targeted closure pass for `L12-R013` and
`L12-R014`. It is not the mandatory section 11.8.8 final complete review and
does not authorize implementation.

## Scope

The candidate changes only:

- `spec/execution.md` section 7 and its compatibility witness (`R013`);
- `spec/execution.md` section 4 and its `process_path` witness (`R014`);
- matching `EXEC-006`/`EXEC-003` manifest prose and remediation history.

`EXEC-002`, `EXEC-004`, `EXEC-005`, Python source, Rust source, and all other
shared semantic files are unchanged. The provisional closures for
`L12-R001` through `L12-R012` therefore remain undisturbed.

## L12-R013 - PROVISIONALLY CLOSED

The previous candidate permitted a broader compatibility relation but did not
define symmetry or how one-sided declarations combine. The repaired rule is
now total and language-neutral:

```text
compatible(a, b) := (a == b)
```

No broader declaration mechanism remains. Equality is symmetric, so provider
order cannot affect `compatible` or `validate`. The witness now checks both
argument orders and both validation-list permutations for unequal identities.

### Negative-control record

```text
finding ID
    L12-R013

method
    exact known-bad/candidate documentary comparison using the permutation
    witness

known-bad SHA
    docs f12b7e2f58983905248ff4a4411db35913ce3d44

expected/observed failure
    explicitly permitted one-sided broader compatibility without choosing
    mutual, either-side, or directional semantics; validate([A,B]) and
    validate([B,A]) could differ

candidate SHA / observed pass
    docs a4eb07c764ea8006c867f574475779c9fcfa78ae
    equality-only relation makes compatible(A,B) == compatible(B,A) and both
    validate permutations identical by construction
```

## L12-R014 - PROVISIONALLY CLOSED

The prior candidate simultaneously classified foreign-provider
`process_path` as undefined and required `FsError(invalid)` when provenance was
detectable. The repaired rule chooses exactly one classification:

```text
foreign-provider process_path call
    outside contract / caller bug / no required Result

optional provider hardening
    MAY detect and return invalid, but callers cannot rely on it
```

This is coherent with the producing-provider-only rule. `resolve` and
`process_path` occur on the producing filesystem provider; only the resulting
path string crosses to a compatible shell/subprocess provider.

### Negative-control record

```text
finding ID
    L12-R014

method
    exact known-bad/candidate documentary comparison

known-bad SHA
    docs f12b7e2f58983905248ff4a4411db35913ce3d44

expected/observed failure
    live normative prose simultaneously said undefined and MUST return
    FsError(invalid); its own witness said the MUST was wrong

candidate SHA / observed pass
    docs a4eb07c764ea8006c867f574475779c9fcfa78ae
    every current normative/evidence statement uses one rule: undefined;
    invalid is explicitly optional best-effort behavior only
```

## Regression and gates

The narrow diff does not touch any prior closed finding's rule. Searches of the
live spec/manifest find no remaining broader-compatibility allowance and no
foreign-provider `process_path` `MUST return invalid` requirement.

Fresh gates:

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

## Settled episode and next action

```text
CE-L12-01-02

PROVISIONALLY CLOSED
    L12-R009 @ prior targeted evidence retained
    L12-R010 @ prior targeted evidence retained
    L12-R011 @ prior targeted evidence retained
    L12-R012 @ prior targeted evidence retained
    L12-R013 @ code 88cf0b4564262cddf2aa5fe1a2de66cbe5dfa99e /
               docs a4eb07c764ea8006c867f574475779c9fcfa78ae
    L12-R014 @ same candidate

OPEN FINDINGS
    none

shared WP-12.1 contract
    NOT YET FINALLY APPROVED

Rust Layer 12
    NOT_IMPLEMENTED

NEXT ACTION
    Freeze this exact candidate and perform one mandatory section 11.8.8
    complete independent contract review. Do not implement Python/Rust Layer
    12 and do not start Layer 13 before that review approves and merges the
    settled contract.
```
