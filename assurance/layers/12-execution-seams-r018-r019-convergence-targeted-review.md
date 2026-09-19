# Layer 12 targeted convergence closure review — `L12-R018`–`L12-R019`

**Mode:** independent Rust-side contract review only  
**Workflow step:** `agent-workflow.md` §11.8.7  
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`  
**Code candidate:** `fa0078cbb7443efdc86eac660860a40be54a33af` (`minion-agent#40`)  
**Docs candidate:** `f51b386d635ad81fdb8e4ce9e89d467a293ec096` (`minion-agent-docs#110`)  
**Convergence agreement:** `7394575ee9009d16d49b1f66d5960cd97bc63632`
(`minion-agent-docs#117`)  
**Prior final review:** `aee3912fef830b42e60f301a51213a6c97d2bd1e`
(`minion-agent-docs#114`)  

The issue and PR heads were fetched and verified remote-reachable, open, Ready for Review, and
identical to the coordination record. Issue #39 named Codex as `NEXT_OWNER` and requested this
targeted review. The governance record in PR #117 names the exact owner decision and exact scope
for narrowing the bridge invariant, satisfying workflow §11.10. No implementation work was
authorized or performed.

## `L12-R018` — canonicalization-unavailable alias identity

**Result:** `PROVISIONALLY CLOSED @ code fa0078cbb7443efdc86eac660860a40be54a33af / docs f51b386d635ad81fdb8e4ce9e89d467a293ec096`

The frozen design, `spec/execution.md` §4, and `EXEC-003` now state one coherent rule:

- if canonicalization succeeds, syntactic aliases resolving to the same location—including a
  symlink and its target—share a key;
- if canonicalization returns `not_supported`, `resolve()` uses lexical `absolute_path`, and a
  symlink and its target are not required to share a key;
- repeated resolution of the same lexical path remains stable.

This preserves the already-settled exact Pi-derived fallback while removing the impossible
unconditional guarantee. The limitation is explicitly visible to future Layer-13 consumers.

**Negative control:** documentary/source-rule comparison against docs
`d0ab7b53cf16d3da17360ea5faa633a235ee8e7a` and code
`997d22ba52b2040cf190fa3e9515c6db738aad1b`. Those candidates simultaneously required lexical
fallback on `not_supported` and equal symlink/target keys, and therefore fail the stub-provider
witness. The reviewed candidate gives the required unequal result for that witness while retaining
equal keys when canonicalization succeeds.

## `L12-R019` — concrete compatibility-error payload

**Result:** `PROVISIONALLY CLOSED @ code fa0078cbb7443efdc86eac660860a40be54a33af / docs f51b386d635ad81fdb8e4ce9e89d467a293ec096`

`spec/execution.md` §7 and `EXEC-006` now define:

```text
ExecutionWorldError
    incompatible_pairs: ordered list of {left: str, right: str}
```

For inputs at indices `i < j`, incompatible pairs appear as `{left: name[i], right: name[j]}` in
input-index enumeration order. Caller labels must be unique; duplicate labels are an explicit
precondition violation. Human-readable message text is non-normative. Rust can therefore expose a
typed ordered vector without consulting Python mechanics, and both languages can normalize the
same payload.

**Negative control:** documentary/type comparison against the same prior candidate. It permitted
a prose-only error, unordered set, or differently ordered structured collection. Such alternatives
fail the new ordered three-provider witness; the reviewed candidate permits only the specified
payload and order.

## Regression scope

The code candidate changes only `EXEC-003` and `EXEC-006`. The docs candidate changes only the
corresponding design/spec passages and remediation/witness history. No filesystem operation,
cancellation checkpoint, shell rule, subprocess rule, cleanup rule, disposition, Python source,
Rust source, canonical schema, or canonical scenario changed. `L12-R001`–`L12-R017` remain
provisionally closed for their recorded findings.

## Fresh gates

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

git diff --check (both remediation deltas)
    PASS
```

## Workflow result

```text
L12-R018
    PROVISIONALLY CLOSED

L12-R019
    PROVISIONALLY CLOSED

CE-L12-01-04 targeted closure
    COMPLETE

shared Layer-12 contract
    NOT YET APPROVED FOR RUST IMPLEMENTATION

Rust Layer 12
    BLOCKED / NOT IMPLEMENTED

Layer 13
    NOT STARTED
```

All findings in `CE-L12-01-04` are provisionally closed. This is not final contract approval. Per
§11.8.8, issue #39 may transition to `FINAL_CONTRACT_REVIEW`, `NEXT_OWNER = Codex`, for exactly one
later complete independent review of the frozen candidate above. Do not perform that final review
in this targeted-closure pass, implement Layer 12, or begin Layer 13.
