# Layer 12 targeted convergence closure review — `L12-R015`–`L12-R017`

**Mode:** independent Rust-side contract review only  
**Workflow step:** `agent-workflow.md` §11.8.7  
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`  
**Code candidate:** `0b573c653e641fdd8242656e0fbbcee133b99f20` (`minion-agent#40`)  
**Docs candidate:** `134d246f0b710099aee6b96c8de9d5ac68fae6c0` (`minion-agent-docs#110`)  
**Convergence agreement:** `29dbefa2e1ffef3cb25585cd2f7bbb086624ff5b` (`minion-agent-docs#116`)  
**Prior final-review evidence:** `2b5f333ce28662bc156ecf56879779d4a61d6b20` (`minion-agent-docs#114`)  

The candidate and agreement SHAs were fetched and verified remote-reachable before review. Issue
`EGAILab/minion-agent#39` named Codex as `NEXT_OWNER` and requested this targeted review. PRs #40,
#110, #114, and #116 were open and unmerged. This review did not modify either candidate branch,
Python, Rust, the normative contract, or Layer 13.

## Authority and scope

The review re-read pinned Pi before the convergence agreement and remediation:

- `packages/agent/src/harness/types.ts`
- `packages/agent/src/harness/tools/file-mutation-queue.ts`
- `packages/agent/src/harness/env/nodejs.ts`
- `packages/agent/test/harness/nodejs-env.test.ts`

It then checked the affected design/spec/manifest passages and their semantic dependencies. The
scope was the three open convergence findings, not a substitute final complete review.

## Finding ledger

### `L12-R015` — result/exception boundary

**Result:** `PROVISIONALLY CLOSED @ code 0b573c653e641fdd8242656e0fbbcee133b99f20 / docs 134d246f0b710099aee6b96c8de9d5ac68fae6c0`

`EXEC-001` now distinguishes operational/environmental failures from broken invariants,
impossible states, assertions, and programming errors. Unexpected operational failures without a
narrower mapping normalize to `unknown`; provider bugs may raise/panic. This agrees with
`spec/execution.md` §2, the corrected frozen design, and pinned Pi's `toFileError` fallback.

**Negative control:** `NOT_APPLICABLE — documentary/traceability-only`. The rejected
`88cf0b4564262cddf2aa5fe1a2de66cbe5dfa99e` row contained both a universal never-raises sentence
and an adjacent escaping-provider-bug exception, so two readers could reach opposite outcomes.
The candidate removes that contradiction.

### `L12-R016` — `FsTarget`, exact fallback, and `resolve()` cancellation

**Result:** `PROVISIONALLY CLOSED @ code 0b573c653e641fdd8242656e0fbbcee133b99f20 / docs 134d246f0b710099aee6b96c8de9d5ac68fae6c0`

The frozen design now describes resolved-location identity rather than underlying-file identity;
it covers relative/absolute aliases, symlink/target aliases, rename, hard links, and missing-path
lexical identity. The spec and `EXEC-003` now reproduce pinned Pi's exact queue-key algorithm:
canonical success wins; only `not_found` and `not_supported` fall back to `absolute_path`; any
other canonicalization failure propagates. `resolve(signal?)` accepts but does not inspect the
signal, consistently with its constituent operations.

The parenthetical list of propagating failures omits `aborted`, but the binding universal phrase
“any OTHER `canonical_path` failure” includes it. Because `resolve()` does not itself inspect the
provided signal, this omission does not create a second conforming interpretation.

**Negative control:** `NOT_APPLICABLE — documentary/traceability-only`. The rejected design/spec
permitted same-resource identity and fallback after every canonicalization failure; the candidate
explicitly rejects both readings and fixes the missing cancellation rule.

### `L12-R017` — local-provider classification and cleanup settlement

**Result:** `STILL OPEN — PI_PARITY_DEFECT`

The candidate correctly closes two parts:

1. `ctx.fs` and `ctx.shell` local providers are direct Pi mappings, while `ctx.subprocess` remains
   a Minion extension; and
2. active command tracking/killing belongs to `ctx.shell.cleanup()`, not `ctx.fs.cleanup()` or a
   new provider-wide subprocess cleanup.

The settlement rule remains incorrect. Pinned Pi does not state that every cleanup-killed child
has a null exit code. Its production code receives `code: number | null` from
`waitForChildProcess(child)` and returns:

```ts
exitCode: code ?? 0
```

Therefore the observable rule is: use the direct child's observed numeric exit code when one is
present, and substitute `0` only when the exit code is absent/null. The Pi test only asserts that
cleanup termination settles `ok: true`; it does not prove the returned code is universally null
or universally zero across platforms and process-close modes.

The candidate instead normatively says every cleanup-killed command returns
`Ok({..., exit_code: 0})`, repeatedly describing cleanup termination as necessarily
signal-terminated/null-exit-code. That erases the non-null branch which pinned Pi deliberately
preserves. An independent Rust implementation following the candidate would be required to throw
away a real numeric child status and return zero, while one following Pi would preserve it.

**Refined discriminating witness:** use an execution backend/process test double whose cleanup
kills the active process tree and whose completion reports numeric exit code `K` (for example
`K = 137`), with no timeout, external abort, or callback failure. Pi's source rule yields
`Ok({stdout, stderr, exit_code: K})`; the candidate's current unconditional-zero rule yields
`Ok({stdout, stderr, exit_code: 0})`. A null/absent completion code remains the companion case and
must yield zero. Both cases remain successful results, not `aborted` or `timeout` errors.

**Minimal correction required:** revise the `L12-R017` agreement, `spec/execution.md`, and
`EXEC-004` to preserve Pi's actual conditional rule: cleanup kills every tracked active command
tree; the command settles through ordinary exit handling; its numeric child exit code is retained
when present and defaults to zero only when absent/null. Remove claims that cleanup necessarily
produces a null code or unconditionally produces zero. Add the two-case documentary/executable
acceptance witness above.

## Affected regression check

No regression was found in the previously settled provider split, filesystem cleanup ownership,
subprocess extension disposition, location-key model, or operational-vs-invariant error boundary.
The candidate changes remain contract-only; Layer 12 has no Python or Rust implementation yet.

## Fresh gates

Run against the exact candidate worktrees:

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

git diff --check (both candidate deltas)
    PASS
```

Green gates do not override the remaining source/contract mismatch.

## Verdict and handoff

```text
L12-R015
    PROVISIONALLY CLOSED

L12-R016
    PROVISIONALLY CLOSED

L12-R017
    STILL OPEN — PI_PARITY_DEFECT

CE-L12-01-03 targeted closure
    NOT COMPLETE

shared Layer-12 contract
    REJECTED FOR RUST IMPLEMENTATION

Rust Layer 12
    BLOCKED / NOT IMPLEMENTED

Layer 12 cross-language
    NOT CLOSED

Layer 13
    NOT STARTED
```

Return only the refined `L12-R017` settlement rule to the shared-contract owner. Keep the
coordination state in `CONTRACT_CONVERGENCE`, set `NEXT_OWNER = Claude`, and perform another
targeted §11.8.7 review after a remote-reachable remediation. Do not run the final complete review
until every finding in `CE-L12-01-03` is provisionally closed.
