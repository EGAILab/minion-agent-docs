# Layer 12 mandatory final contract review — third complete review

**Mode:** independent Rust-side contract review only  
**Workflow step:** `agent-workflow.md` §11.8.8  
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`  
**Code candidate:** `997d22ba52b2040cf190fa3e9515c6db738aad1b` (`minion-agent#40`)  
**Docs candidate:** `d0ab7b53cf16d3da17360ea5faa633a235ee8e7a` (`minion-agent-docs#110`)  
**Settled targeted-review evidence:** `8512e40399af4be85ca0d0486cc82e202e5a349b`
(`minion-agent-docs#114`)  

## Starting state and independence

The exact PR heads were fetched and verified remote-reachable, Ready for Review, open, unmerged,
and identical to issue #39's frozen candidate. Issue #39 recorded
`STATUS = FINAL_CONTRACT_REVIEW` and `NEXT_OWNER = Codex`. Candidate worktrees contained only
pre-existing unrelated untracked worktree/temp directories, which were not modified.

Review authority order:

1. pinned Pi source;
2. normative `spec/execution.md`;
3. `EXEC-001`–`EXEC-006` manifest rows;
4. the contract witness matrix;
5. existing certified Rust architecture;
6. assurance/history.

There is no Layer-12 Python implementation, Rust implementation, or canonical runner to use as an
oracle. No Layer-12 implementation or Layer-13 work was performed.

Pinned Pi sources re-read include:

- `packages/agent/src/harness/types.ts`
- `packages/agent/src/harness/env/nodejs.ts`
- `packages/agent/src/harness/tools/file-mutation-queue.ts`
- `packages/agent/test/harness/nodejs-env.test.ts`

## Whole-contract result

The previously open `L12-R017` remains correctly provisionally closed. Its conditional
`code ?? 0` rule is source-faithful. The complete review found two new contract defects elsewhere.

### Row audit

| Row | Subject | Final-review result |
|---|---|---|
| `EXEC-001` | shared operational-result vs invariant-exception boundary | coherent |
| `EXEC-002` | filesystem vocabulary, cancellation, local provider | coherent |
| `EXEC-003` | `FsTarget`/`target_key`/`process_path` bridge | **blocked by `L12-R018`** |
| `EXEC-004` | shell execution/local provider | coherent, including refined cleanup settlement |
| `EXEC-005` | Minion subprocess extension | coherent and independently implementable |
| `EXEC-006` | execution-world compatibility | **blocked by `L12-R019`** |

The per-seam dispositions are otherwise coherent: direct Pi filesystem/shell behavior is adopted;
the Minion-only bridge, subprocess seam, and compatibility primitive are intentional divergences.

## New findings

### `L12-R018` — `not_supported` fallback contradicts unconditional symlink identity

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`  
**Severity:** blocking  
**Affected:** `spec/execution.md` §4, `EXEC-003`, frozen-design §7 bridge invariant, witness matrix

The candidate binds both of these rules:

1. when `canonical_path(path)` returns `not_supported`, `resolve()` MUST use lexical
   `absolute_path(path)` as the key; and
2. a symlink and its target MUST always share one `target_key`, for every provider, with no
   provider choice.

They cannot both hold. Consider one valid filesystem provider whose `canonical_path` operation is
unsupported and therefore returns `FsError(not_supported)` for every path:

```text
absolute_path("link")   -> /root/link
absolute_path("target") -> /root/target
canonical_path(...)     -> Err(not_supported)
```

The mandatory fallback produces unequal keys even when `link` points to `target`. That satisfies
the exact fallback algorithm but violates the unconditional identity guarantee. The contradiction
is repeated in the manifest: `EXEC-003` states the `not_supported` fallback and then says symlink
identity “falls out of the derivation for free.” It does not fall out when canonicalization is
unsupported.

This is not a hypothetical Rust implementation preference. `not_supported` is part of the adopted
`FsError` vocabulary, and the exact fallback deliberately treats it as a valid provider outcome.
Two readers cannot implement one contract: one must preserve the fallback and expose unequal keys;
the other must invent another alias-resolution mechanism to preserve equality despite the provider
declaring canonicalization unsupported.

**Required remediation:** settle one coherent rule and synchronize the frozen design, §4,
`EXEC-003`, and witnesses. The source-faithful minimal option is to preserve Pi's exact
`not_found | not_supported` lexical fallback and narrow the symlink/target equality guarantee to
cases where canonicalization succeeds; explicitly state that a provider returning
`not_supported` cannot promise alias unification. Because the unconditional same-resource/
equivalent-path guarantee was part of the recorded owner scope decision, narrowing it requires a
traceable governance decision under §11.10. Alternatively, retain the unconditional guarantee only
with a fully specified implementable mechanism that does not contradict `not_supported`.

**Discriminating witness:** a stub provider returns `not_supported` from `canonical_path` for both a
symlink path and its target while returning their distinct lexical absolute paths. The repaired
contract must state one unambiguous expected equality result and disposition for this exact case.

### `L12-R019` — `ExecutionWorldError` public shape remains undefined

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`  
**Severity:** blocking  
**Affected:** `spec/execution.md` §7, `EXEC-006`, witness matrix

The candidate improved the compatibility relation to equality-only and introduced:

```text
validate(list[(name, identity)]) -> Result[None, ExecutionWorldError]
```

but never defines the typed error's public data shape. It requires only that the error “name every
pairwise-incompatible provider.” It does not say whether pairs are structured fields or prose,
whether pair order follows input order or another order, how duplicate labels are handled, or
whether the diagnostic message itself is normative.

Consequently two independently conforming implementations can expose incompatible public APIs:

```text
Python: ExecutionWorldError("fs incompatible with shell; fs incompatible with subprocess; ...")
Rust:   ExecutionWorldError { incompatible_pairs: HashSet<(String, String)> }
```

Both “name every pair,” but callers and canonical normalization cannot consume them in the same
language-neutral way. Rust would have to consult Python mechanics or invent observable semantics.

**Required remediation:** define a minimal language-neutral error payload and ordering. One
straightforward contract is an ordered `incompatible_pairs` collection of `{left, right}` labels,
enumerated by input index with `i < j`; require caller-supplied labels to be unique (or define
duplicate-label behavior); state whether human-readable message text is non-normative. Equivalent
precise wording is acceptable.

**Discriminating witness:** validate ordered inputs `[("fs", A), ("shell", B), ("subprocess", C)]`
with three unequal identities. Assert the exact structured payload and pair order. Add a duplicate-
label case or an explicit unique-label precondition.

## Previously settled findings

`L12-R001`–`L12-R017` remain provisionally closed for their specific findings. The new findings do
not invalidate the refined cancellation checkpoints, error boundary, location-key rename/hard-link
rules, shell precedence and timeout ceiling, subprocess lifecycle, local-provider split, or
conditional cleanup exit-code settlement. `L12-R018` exposes a new combination absent from the
prior matrices: canonicalization unsupported *and* symlink aliasing. `L12-R019` exposes the still-
missing typed diagnostic shape after the compatibility predicate itself was fixed.

## Rust independent implementability

The certified Rust architecture has suitable Runtime service ownership and typed-error patterns,
and the filesystem, shell, subprocess, and `FsTarget` APIs can otherwise be implemented
idiomatically without copying Python. No lower-layer reopen is required.

Rust cannot implement the current complete Layer-12 contract without guessing:

- whether the `not_supported` fallback or unconditional alias-key invariant wins; and
- the public representation/order of `ExecutionWorldError`.

Therefore implementation must remain blocked.

## Fresh gates

Run against the exact candidate:

```text
uv run pytest --no-cov -ra
    1504 passed, 19 xfailed

uv run ruff check .
    PASS

uv run mypy
    PASS — 71 source files

uv run pytest --no-cov \
    tests/conformance/test_manifest_validation.py \
    tests/conformance/test_schema_validation.py -q
    PASS — 213 tests

manifest inventory
    101 rows / 101 unique IDs

git diff --check (candidate remediation deltas)
    PASS
```

Green gates cannot resolve contradictory or missing contract semantics.

## Verdict

```text
mandatory §11.8.8 final complete review
    REJECTED — Case B

new convergence episode
    CE-L12-01-04

open findings
    L12-R018 CONTRACT_ASSURANCE_DEFECT
    L12-R019 CONTRACT_ASSURANCE_DEFECT

shared Layer-12 contract
    REJECTED FOR RUST IMPLEMENTATION

Python Layer 12
    NOT IMPLEMENTED

Rust Layer 12
    BLOCKED / NOT IMPLEMENTED

Layer 12 cross-language
    NOT CLOSED

Layer 13
    NOT STARTED
```

Per §11.8.8 Case B, open convergence episode `CE-L12-01-04`. The shared-contract owner must first
characterize/challenge the two findings, obtain the required governance decision for any narrowing
of the owner-approved alias invariant, record an agreed checkpoint, then apply one coherent fix.
The resulting remote-reachable candidate requires targeted §11.8.7 closure before another final
complete review. Do not implement Layer 12 or begin Layer 13.
