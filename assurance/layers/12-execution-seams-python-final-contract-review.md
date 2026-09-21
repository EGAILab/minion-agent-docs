# Layer 12 WP-12.1 Python implementation — final complete independent review

Verdict: **APPROVED — exact-SHA shared/Python candidate may merge**

## Exact frozen target

- code candidate: `EGAILab/minion-agent#44` @
  `b9c04e00aa2803304b7e9c1f5462e15eb524a709`
- checkpoint/docs candidate: `EGAILab/minion-agent-docs#121` @
  `00afd5178d5c1bed4ec5175eea873061a9928fb1`
- review-evidence PR: `EGAILab/minion-agent-docs#120`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- merged Rust Layer-12 baseline reviewed for implementability/delta impact:
  `minion-agent/main` @ `2b309ee8cecbc333a7965781087677bd6cbba46b`

Before review, all three PR heads were fetched and verified remote-reachable. PRs #44, #121, and
#120 were open, Ready for Review, unmerged, and mergeable. Coordination issue
`EGAILab/minion-agent#39` was open with `status: FINAL_CONTRACT_REVIEW`, `next_owner: Codex`, the
same frozen candidate SHAs, an empty convergence `open_findings` list, and the settled
`CE-L12-PY-01-01` provenance.

This is the one complete independent review required by `process/agent-workflow.md` section
11.8.8 after targeted closure. It is not a targeted re-review of only `L12-PY-R002`.

## Authority and evidence audited

The review used the required order:

1. pinned Pi `packages/agent/src/harness/types.ts` and
   `packages/agent/src/harness/env/nodejs.ts`, including `resolvePath`, `toFileError`,
   `waitForChildProcess`, `NodeExecutionEnv.exec`, every filesystem method, and cleanup;
2. the complete current `spec/execution.md` contract;
3. manifest rows `EXEC-001` through `EXEC-006`;
4. direct language evidence and the committed Ada/Node differential corpus;
5. the merged certified Rust execution architecture;
6. the complete review/convergence lineage in docs PR #120 and checkpoint provenance in docs PR
   #121;
7. Python implementation source only after those authorities were established.

The candidate changes no Rust file and adds no Layer-13 built-in tool or mutation-serialization
behavior.

## Complete requirement ledger

| Row | Disposition | Independent result |
|---|---|---|
| `EXEC-001` | `adopted` | **PASS.** The expected operational/environmental failures are normalized through typed `Result` values; invariant/programming failures are not indiscriminately swallowed. The Pi `FsErrorCode` and `ShellErrorCode` vocabularies and mappings are represented. |
| `EXEC-002` | `adopted` | **PASS.** The complete filesystem operation set, per-operation signal inspection table, path/join/text/binary/symlink/temp/cleanup rules, and direct Node `fileURLToPath` behavior are implemented through the real provider. The exact `ada-url==1.15.3` pin and permanent 8,246-case differential gate reproduce the pinned Ada 2.9.2 engine. |
| `EXEC-003` | `intentional divergence` | **PASS.** `FsTarget` is an opaque provider-scoped bridge; resolve selects canonical identity for existing resources and lexical absolute identity only for `not_found`/`not_supported`; `process_path` returns that exact key and rejects a foreign provider target. No second resource-identity authority exists. |
| `EXEC-004` | `adopted` | **PASS.** Shell preflight order, exact timeout ceiling, environment/cwd behavior, decoded streaming callbacks, failure precedence, nonzero-exit success, 100 ms resettable post-exit idle grace, process-tree termination, and cleanup settlement match the contract and pinned Pi. Shell delegates process ownership to the mounted `Subprocess` seam. |
| `EXEC-005` | `intentional divergence` | **PASS.** The Minion-only typed subprocess vocabulary is coherent and complete: argv-direct spawn, stdio modes and typed byte streams, one spawn-time signal, deterministic first-claim classification, idempotent/concurrent wait, explicit termination, exit-only settlement, and caller-owned disposal. Python does not duplicate shell completion policy inside `Process.wait()`. |
| `EXEC-006` | `intentional divergence` | **PASS.** Execution-world identity is equality-only, validation is consumer-owned, incompatible pairs are complete and deterministically input-ordered, and the three local providers share one world by construction. |

All 101 manifest rows parse with 101 unique IDs. The Layer-12 dispositions remain internally
coherent: direct Pi surfaces are `adopted`; the `FsTarget`, subprocess, and execution-world
Minion architecture rows are `intentional divergence`. No placeholder is counted as evidence.

## Complete implementation audit

### Filesystem and `FsTarget`

- Every public operation has the contract's typed optional signal parameter.
- Only the six Pi-observed operation paths inspect it; the ten non-inspecting methods accept but
  ignore it as specified.
- Blocking read/write work is raced against cancellation for prompt caller-visible settlement
  without pretending Python can forcibly interrupt an OS worker thread.
- Addressed symlink identity and content-following/non-following operations match the normative
  matrix.
- Error conversion is narrow to operational `OSError` failures.
- `resolve()` delegates to the real canonical/absolute operations and `process_path()` consumes
  the real target; tests do not simulate either rule.

### Shell and subprocess

- `LocalShell` depends on the abstract Runtime-mounted `Subprocess`, not a hidden duplicate
  process provider.
- Process cause is claimed before kill dispatch and is never re-derived from a later signal
  state. `wait()` awaits only the target process's exit; kill-helper confirmation is decoupled.
- Stdio remains readable after ordinary `wait()`; EOF and explicit termination perform scoped,
  best-effort transport cleanup.
- Shell owns the higher-level idle-grace and classification policy, so the lower-level process
  seam remains independently usable.
- No lock is held across subprocess, callback, filesystem, or Runtime service calls.

### Runtime/plugin and execution-world integration

- The three capability protocols have independent service names and one-plugin/one-service
  wiring.
- The shell plugin resolves the mounted subprocess service through the real Runtime context.
- Compatibility validation is an explicit consumer operation; mounting unrelated providers is
  not globally rejected.

## Prior Python finding closure

| Finding | Final result |
|---|---|
| `L12-PY-R001` — filesystem cancellation checkpoints | **RESOLVED** |
| `L12-PY-R002` — path/text and `file://` fidelity | **RESOLVED** |
| `L12-PY-R003` — capability/service and world abstraction | **RESOLVED** |
| `L12-PY-R004` — deterministic process cause classification | **RESOLVED** |
| `L12-PY-R005` — decoded shell callback payloads | **RESOLVED** |
| `L12-PY-R006` — pre-spawn abort classification | **RESOLVED** |
| `L12-PY-R007` — process/resource cleanup without breaking post-wait drain | **RESOLVED** |

The final review found no regression in any provisionally closed finding and no new
`PI_PARITY_DEFECT`, `CONTRACT_ASSURANCE_DEFECT`, or `PI_BEHAVIOR_UNCERTAIN`.

## R002 oracle evidence

The committed comparison harness was rerun from docs PR #121:

```text
corpus sources                         6
keys per source                        8,246
Node 22.19.0 vs Node 22.23.2           0 acceptance / 0 output mismatches
Node 22.19.0 vs direct Ada 2.9.2       0 acceptance / 0 output mismatches
direct Ada 2.9.2 vs ada-url 1.15.3     0 acceptance / 0 output mismatches
```

The candidate's permanent test drives all 8,246 rows through production
`_file_url_to_path`, not a test-local reimplementation. The preceding targeted review also
demonstrated the required negative control against known-bad code SHA
`1848873fc9626b699990a29b1f35c7baba78cc34`: 1,059/8,246 mismatches, including both named
`xn--3pc`/`xn--8g0n` witnesses. The candidate passes every row.

## Canonical and runner-quality result

Layer 12 adds no dynamic canonical runner family. Its finite, platform-sensitive
filesystem/process behaviors are evidenced through direct typed language tests, while the
cross-language rules live in the normative spec and manifest. No canonical runner simulates
FIFO, cancellation, path identity, process settlement, or provider composition on behalf of
production code.

## Rust impact and next-pass boundary

The current shared/Python candidate is independently implementable in Rust and does not require a
lower-layer semantic reopen. The previously certified Rust implementation remains untouched in
this review, but the post-certification characterization leaves three explicit, narrow Rust-owned
obligations before cross-language closure:

1. revalidate/remediate `EXEC-002`/`EXEC-003` file-URL conversion with the same direct Ada 2.9.2
   8,246-case oracle rather than using Python as oracle;
2. add discriminating revalidation for R004-A causal states 7, 9, and 10;
3. remediate R004-B: Rust `Process::wait()` must settle on the target process's own exit and must
   not await unbounded external kill-helper completion.

Item 3 is a known Rust implementation defect against an already-settled rule, not an active
shared/Python contract defect or an alternative policy choice. Therefore it blocks current
cross-language closure, but it does not block merging this approved shared/Python milestone.

## Fresh gates

Run against exact code SHA `b9c04e00aa2803304b7e9c1f5462e15eb524a709`:

```text
python -m pytest
    1724 passed, 4 skipped, 19 xfailed
    100.00% coverage

python -m pytest -W error --no-cov tests/execution
    220 passed, 4 skipped

ruff check .
    PASS

mypy src
    PASS — 79 source files

pytest --no-cov tests/conformance/test_manifest_validation.py
    8 passed

pytest --no-cov tests/conformance/test_schema_validation.py tests/test_layering.py
    210 passed

uv lock --check
    PASS

manifest
    101 rows / 101 unique IDs

git diff --check
    PASS for code and docs candidates
```

`ruff format --check .` is not a configured certification gate for this repository and reports
nine formatting-only files (seven pre-existing plus two Layer-12 files). This is recorded as
non-blocking `PARITY_NEUTRAL_HARDENING`; lint, type, test, coverage, lock, manifest, schema, and
whitespace gates are green, and no semantic observation depends on that formatting.

## Findings taxonomy

```text
PI_PARITY_DEFECT
    none

CONTRACT_ASSURANCE_DEFECT
    none

PI_BEHAVIOR_UNCERTAIN
    none

PARITY_CONSTRAINED_RISK
    none in the shared/Python candidate

PARITY_NEUTRAL_HARDENING
    optional formatting normalization for the two new files reported by ruff format --check
```

## Formal verdict

```text
shared Layer-12 WP-12.1 contract
    APPROVED / IMPLEMENTED at the exact candidate SHAs above

Python Layer 12 WP-12.1
    CERTIFIED

Rust Layer 12 WP-12.1
    PREVIOUS CERTIFICATION REQUIRES NARROW REVALIDATION/REMEDIATION

Layer 12 cross-language
    NOT CLOSED

Layer 13
    NOT STARTED

Rust implementation modified
    NO
```

The exact code/docs candidates are approved for squash merge. After merge, coordination should
move to `RUST_IMPLEMENTATION` with Codex owning the separate narrow Rust revalidation/remediation
pass. This review does not itself authorize Layer 13 and does not perform the Rust changes.
