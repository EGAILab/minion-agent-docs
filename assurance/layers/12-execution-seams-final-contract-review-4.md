# Layer 12 mandatory final contract review — fourth complete review

**Verdict:** `APPROVED FOR RUST IMPLEMENTATION`  
**Mode:** independent Rust-side contract review only  
**Workflow step:** `agent-workflow.md` §11.8.8  
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`  
**Approved code candidate:** `fa0078cbb7443efdc86eac660860a40be54a33af` (`minion-agent#40`)  
**Approved docs candidate:** `f51b386d635ad81fdb8e4ce9e89d467a293ec096` (`minion-agent-docs#110`)  
**Settled targeted review:** `590718f6bc227d6e473cb90c6f46e24171a4c20f`
(`minion-agent-docs#114`)  

## Starting state

The exact PR heads were fetched and verified remote-reachable, open, Ready for Review, unmerged,
and identical to issue #39. The issue validly recorded `STATUS = FINAL_CONTRACT_REVIEW`,
`NEXT_OWNER = Codex`, no open convergence findings, and the exact candidate above. The
`CE-L12-01-04` governance record names and scopes the owner-approved narrowing of the `FsTarget`
alias guarantee. No candidate or implementation file was modified during review.

## Independent authority audit

Review order:

1. pinned Pi `types.ts`, `env/nodejs.ts`, `file-mutation-queue.ts`, and harness tests;
2. complete `spec/execution.md`;
3. manifest `EXEC-001`–`EXEC-006`;
4. complete witness matrix;
5. certified Rust Runtime/service/error architecture;
6. convergence/assurance history.

Python implementation was not used as a semantic oracle; Layer 12 has no implementation yet.

## Complete row verdict

| Row | Surface | Disposition | Result |
|---|---|---|---|
| `EXEC-001` | shared Result/exception boundary | adopted | PASS |
| `EXEC-002` | filesystem seam and local provider | adopted | PASS |
| `EXEC-003` | `FsTarget` bridge | intentional divergence | PASS |
| `EXEC-004` | shell seam and local provider | adopted | PASS |
| `EXEC-005` | raw subprocess seam and local provider | intentional divergence | PASS |
| `EXEC-006` | execution-world compatibility | intentional divergence | PASS |

### Filesystem

The contract accounts for every pinned `FileSystem` operation, exact cancellation checkpoints,
path and symlink behavior, error codes, temporary-resource creation, and cleanup. The uniform
optional signal API is separated correctly from the ten operations that accept but do not inspect
it. The local provider can be implemented without inventing semantics.

### `FsTarget`

The bridge is now internally coherent and governance-backed: canonicalization success unifies
aliases; `not_found` and `not_supported` use lexical absolute fallback; all other canonicalization
errors propagate. A non-canonicalizing provider explicitly cannot promise symlink/target alias
unification. Provider scoping, opacity, equality/hashing, missing-target behavior, `process_path`,
and execution-world transfer are sufficiently specified for independent Rust implementation.

### Shell

Shell discovery, cwd/environment behavior, timeout boundary, pre/post-spawn precedence, process-
tree termination, callback failure, idle-grace settlement, non-zero exit success, cleanup, and
conditional `code ?? 0` normalization match pinned Pi and are implementable independently.

### Subprocess

The Minion extension defines argv-direct spawn, stdio modes, byte streams, cwd/environment,
single-signal cancellation, repeated/concurrent wait, termination, disposal obligations, pipe
errors, and tree termination without importing shell semantics. It is complete enough to support
the local shell provider while remaining a distinct capability.

### Execution worlds

Identity compatibility is equality-only and consumer-triggered. `ExecutionWorldError` now has one
normative ordered payload, deterministic input-index pair ordering, a unique-label precondition,
and non-normative human text. Rust can expose typed vectors/structs without consulting Python.

## Prior findings and new-finding check

`L12-R001`–`L12-R019` remain provisionally closed for their exact findings. The complete review
found no active `PI_PARITY_DEFECT`, `CONTRACT_ASSURANCE_DEFECT`, `PI_BEHAVIOR_UNCERTAIN`, or
unapproved observable divergence. No lower-layer reopen is required.

## Rust feasibility

The certified Rust crate provides suitable typed errors, service ownership, synchronization, and
async foundations. Layer 12 can introduce typed filesystem/shell/subprocess service traits,
`FsTarget`, execution-world identity/validation, and local providers without duplicating a lower-
layer authority or reading Python mechanics. Canonical evidence can be added through real Rust
seams during the separate implementation pass.

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

git diff --check (complete candidate deltas)
    PASS
```

## Formal verdict

```text
shared Layer-12 contract
    APPROVED FOR RUST IMPLEMENTATION

approved exact candidate
    code fa0078cbb7443efdc86eac660860a40be54a33af
    docs f51b386d635ad81fdb8e4ce9e89d467a293ec096

Python Layer 12
    NOT IMPLEMENTED

Rust Layer 12
    NOT IMPLEMENTED

Layer 12 cross-language
    NOT CLOSED

Layer 13
    NOT STARTED
```

Approval is exact-SHA-bound. Merge the approved shared candidate and durable review/convergence
evidence through the repository's squash-merge gate, verify the resulting default-branch commits,
then transition issue #39 to `RUST_IMPLEMENTATION`, `NEXT_OWNER = Codex`. Stop after that
transition. Rust implementation is a separate pass; Layer 13 remains out of scope.
