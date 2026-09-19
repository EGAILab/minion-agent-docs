# Layer 12 WP-12.1 - second final complete independent Rust contract review

## Verdict

```text
shared Layer-12 WP-12.1 contract
    REJECTED

Python Layer 12
    NOT_IMPLEMENTED / BLOCKED

Rust Layer 12
    NOT_IMPLEMENTED / BLOCKED

Layer 12 cross-language
    NOT CLOSED

Layer 13
    NOT STARTED
```

This is the mandatory `agent-workflow.md` section 11.8.8 complete review after
the targeted closure of `CE-L12-01-02`. It is review evidence only. It does
not implement Python or Rust and does not repair the shared semantic candidate.

The exact candidate is rejected on three contract-assurance defects. Two are
residual contradictions on root-cause surfaces previously treated as settled
(`L12-R004` and `L12-R005`); the third concerns the observable ownership of
local-provider cleanup after splitting Pi's combined `ExecutionEnv`. They
invalidate prior convergence matrices rather than forming one isolated point
fix. This is section 11.8.8 **Case B** and requires a new convergence episode.

## Exact frozen target and remote control state

- Code PR `EGAILab/minion-agent#40` @
  `88cf0b4564262cddf2aa5fe1a2de66cbe5dfa99e`
- Docs PR `EGAILab/minion-agent-docs#110` @
  `a4eb07c764ea8006c867f574475779c9fcfa78ae`
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Review-evidence PR `EGAILab/minion-agent-docs#114`, predecessor head:
  `27f8161b3be93e0283dbba40a2d2f963b1cb0443`
- Settled predecessor episode: `CE-L12-01-02`
- New episode required by this review: `CE-L12-01-03`

At review start, issue `EGAILab/minion-agent#39` was open with
`STATUS = FINAL_CONTRACT_REVIEW`, `NEXT_OWNER = Codex`, no open convergence
findings, the exact candidate pair above, valid governance provenance, and no
quarantine derivation. PRs #40, #110, and #114 were open, Ready for Review,
unmerged, mergeable, and remote-reachable. Their heads matched the issue.

The code and docs candidate working trees contained only unrelated untracked
review/coverage directories, which were preserved. Neither candidate branch
was modified by this review.

## Authority and evidence audited

The review used the required order:

1. pinned Pi source;
2. frozen design and normative `spec/execution.md`;
3. manifest rows `EXEC-001` through `EXEC-006`;
4. the candidate's predicted witness matrix and current canonical inventory;
5. certified Rust architecture through Layer 11;
6. historical assurance, convergence, and handoff evidence;
7. no Python Layer-12 implementation exists to use as secondary evidence.

Pinned Pi source independently re-read included:

- `packages/agent/src/harness/types.ts`: `Result`, `FileErrorCode`,
  `ExecutionErrorCode`, `FileSystem`, `ShellExecOptions`, `Shell`, and
  `ExecutionEnv`;
- `packages/agent/src/harness/env/nodejs.ts`: `resolvePath`, `toFileError`,
  shell discovery/environment/timeout helpers, `waitForChildProcess`,
  `NodeExecutionEnv.exec`, all filesystem operations, and `cleanup`;
- `packages/agent/src/harness/tools/file-mutation-queue.ts`, especially
  `getMutationQueueKey`;
- `packages/agent/src/harness/session/jsonl/types.ts`;
- the relevant harness regression tests.

No executable Layer-12 canonical scenarios exist yet because this remains a
contract-first candidate. The predicted matrix is useful contract evidence but
is not implementation certification.

## Requirement ledger

| Row | Subject | Disposition | Result |
|---|---|---|---|
| `EXEC-001` | fs/shell Result boundary and taxonomies | adopted | **blocked by L12-R015** |
| `EXEC-002` | filesystem seam | adopted | no new independent blocker; affected by the shared result-boundary correction |
| `EXEC-003` | `FsTarget` bridge | intentional divergence | **blocked by L12-R016** |
| `EXEC-004` | shell seam | adopted | **blocked by L12-R017** |
| `EXEC-005` | subprocess seam | intentional divergence | **blocked by L12-R017's disposition correction** |
| `EXEC-006` | execution-world compatibility | intentional divergence | coherent; `L12-R013` remains provisionally closed |

Manifest structure is valid: 101 rows, 101 unique IDs. The defects are in
semantic consistency/completeness, not YAML shape or row uniqueness.

## Findings

### L12-R015 - CONTRACT_ASSURANCE_DEFECT - `EXEC-001` retains the exact universal error-boundary contradiction previously removed elsewhere

The frozen design and `spec/execution.md` section 2 now choose one coherent
boundary:

```text
expected operational/environmental failures
    -> typed Result error

provider/framework invariant violations and programming errors
    -> exception/panic
```

They also make the provider responsible for translating native operational
backend failures into the seam vocabulary; a filesystem backend failure with
no narrower mapping becomes `unknown` rather than escaping raw.

Current manifest row `EXEC-001`, however, still says every operation never
raises/rejects **including for unexpected backend failures**, then lists “an
unnormalized backend exception escaping a seam” as an exception/provider bug.
Those statements permit two incompatible readings of the same failure. This is
the same semantic contradiction `L12-R004` previously found in the frozen
design, now surviving in another semantic authority that its closure review did
not recheck.

Pinned Pi resolves the operational side: the `FileSystem` contract requires
filesystem failures, including unexpected backend failures, to be returned,
and `toFileError` maps an otherwise-unrecognized backend failure to `unknown`.
That does not turn an impossible provider state, assertion, or programming bug
into a caller-handleable I/O result.

Minimal correction:

1. make `EXEC-001` use the design/spec boundary verbatim;
2. distinguish an unexpected **operational backend failure** (normalize to
   `unknown`) from a broken provider invariant/programming failure
   (exception/panic);
3. add a documentary negative control showing the current universal sentence
   fails while the corrected distinction passes.

This successor finding invalidates the documentary closure matrix for
`L12-R004`; it is not a harmless evidence-pointer issue.

### L12-R016 - CONTRACT_ASSURANCE_DEFECT - the `FsTarget` contract is still contradictory and incomplete across design/spec/manifest

The frozen design's live Layer-12 architecture says:

```text
resolve(path) -> FsTarget returns an opaque target_key.
The same file reached by different paths yields the same key.
process_path(target) returns the canonical path ...
```

The current spec and `EXEC-003` instead deliberately settled on **location
identity**:

- rename changes the key even though the underlying file is the same;
- two hard links to the same underlying file have different canonical paths
  and therefore different keys;
- deleting and recreating the same location reuses the key;
- a missing path uses a lexical absolute-path fallback, which is not a
  canonical path.

These cannot all be true alongside the frozen design's resource-identity and
canonical-`process_path` wording. The prior `L12-R005` closure audited the
spec/manifest algorithm but did not bring the frozen design into alignment.

The algorithm is also incomplete in the current normative text. Pinned Pi's
actual `getMutationQueueKey` falls back from `canonicalPath` to `absolutePath`
**only** for `not_found` and `not_supported`; every other error propagates.
The candidate merely says “canonical path if it exists, else absolute path” or
“when canonicalization fails,” allowing all of these mutually different Rust
implementations:

```text
fallback on not_found only
fallback on not_found or not_supported       # pinned Pi
fallback on every canonicalization failure
```

Finally, `resolve(path, signal?)` is a public operation but no rule says whether
it inspects cancellation. That is observable on a pre-aborted signal. The two
Pi operations from which the chosen mechanism is composed (`absolutePath` and
`canonicalPath`) are in the accepted-but-not-inspected group, but the Minion
mapping must state its own result rather than require Rust to infer it.

Minimal convergence matrix/witnesses:

1. hard-link and rename witnesses distinguishing resource identity from the
   selected location identity, with the frozen design corrected accordingly;
2. stub-provider witnesses for `canonical_path` returning `not_found`,
   `not_supported`, `permission_denied`, and `unknown`; only the first two use
   the absolute fallback under the Pi-derived algorithm;
3. a pre-aborted `resolve(path, signal)` witness selecting one explicit
   cancellation behavior;
4. one consistent `process_path` description that also covers a target created
   from the missing-path fallback without falsely calling that lexical path
   canonical.

This invalidates the settled `L12-R005` matrix and is independently sufficient
for section 11.8.8 Case B.

### L12-R017 - CONTRACT_ASSURANCE_DEFECT - split local-provider ownership and parity classification are not coherent

`spec/execution.md` section 8 says local providers are
“**DIRECT_PI_PARITY** for observable behavior (§3-§6 above, each already citing
the harness-tier reference implementation).” Section 6 and `EXEC-005` correctly
say the opposite for `ctx.subprocess`: it is a `MINION_EXTENSION` with no direct
Pi seam and an `intentional divergence` disposition. The local subprocess
provider cannot acquire direct-Pi status merely because its primitive set was
informed by Pi's combined shell implementation.

The same split-provider mapping loses a real observable cleanup rule. Pinned
Pi's combined `NodeExecutionEnv.cleanup()` kills every tracked active child
process and clears the tracking set; its test suite exercises cleanup while an
`exec()` is active. The candidate:

- describes that behavior only in filesystem section 3.8, while acknowledging
  it is actually process-owned;
- gives shell `cleanup()` only “best-effort, must not raise” and never requires
  active shell commands to be terminated;
- gives `ctx.subprocess` caller-owned `wait`/`terminate` semantics, with no
  provider cleanup operation.

A no-op local-shell `cleanup()` and a kill-all-active-commands implementation
therefore both satisfy the current shell prose, while only the latter preserves
Pi's observable behavior. The mapping must assign the combined Pi behavior to
one concrete Minion owner rather than merely mentioning it beside `ctx.fs`.

Minimal correction/witnesses:

1. classify local `ctx.subprocess` behavior as the same Minion extension owned
   by section 6/`EXEC-005`; reserve direct Pi parity for fs/shell behaviors that
   actually have Pi seams;
2. assign tracked active shell-command cleanup to the local shell provider and
   state the pending `exec()` observation (absent a higher-precedence
   callback/timeout/abort condition, Pi settles the killed command as success
   with `exit_code = 0` because a null exit is normalized with `code ?? 0`);
3. witness that `shell.cleanup()` terminates an active command tree, settles
   the call, leaves no tracked process, and never raises;
4. keep filesystem cleanup, subprocess caller disposal, and shell cleanup as
   separate ownership rules rather than importing the combined
   `NodeExecutionEnv` cleanup into the wrong split provider.

## Previously provisionally closed findings

The review re-ran the full source/spec/manifest audit rather than limiting
itself to `L12-R013`/`L12-R014`.

- `L12-R001`-`R003`, `L12-R006`-`R014` remain provisionally closed for their
  exact prior objections.
- `L12-R004` and `L12-R005` do not silently reopen under their old IDs; the new
  exact residuals are recorded as successor findings `L12-R015` and
  `L12-R016`, preserving history.
- No active `PI_BEHAVIOR_UNCERTAIN` remains. The relevant Pi behavior is
  source-resolved.

## Rust implementability and lower-layer impact

```text
Rust can implement WP-12.1 without guessing observable semantics
    NO

Certified lower-layer semantic delta required
    NO

Python Layer-12 implementation exists
    NO

Rust Layer-12 implementation modified
    NO

Shared semantic candidate modified by reviewer
    NO
```

Rust already has the typed runtime service/context, async/future,
cancellation, ownership, and error patterns needed to implement the settled
contract idiomatically. These findings require only a coherent Layer-12 shared
contract/evidence correction; Layers 01-11 need not reopen.

## Contract-quality answers

```text
Does a runner simulate Layer-12 production semantics?
    NO -- no Layer-12 runner exists yet.

Could Python and Rust satisfy the written contract while differing observably?
    YES -- result/exception classification, FsTarget fallback/cancellation,
    and shell cleanup permit incompatible choices.

Does a lower certified layer prevent a faithful implementation?
    NO.

Would Rust need to consult Python mechanics to choose these rules?
    YES under the current candidate, which is why approval is blocked.

Has Layer 13 leaked into WP-12.1?
    NO -- built-in tools and mutation serialization remain out of scope.
```

## Fresh gates

Run against the exact candidate:

```text
uv run pytest --no-cov -ra
    1504 passed, 19 xfailed

uv run ruff check .
    PASS

uv run mypy
    Success: no issues found in 71 source files

uv run pytest --no-cov \
    tests/conformance/test_manifest_validation.py \
    tests/conformance/test_schema_validation.py -q
    213 passed

manifest rows / unique IDs
    101 / 101

git diff --check (both candidates)
    PASS
```

An exploratory non-repository mypy invocation over all tests produced expected
out-of-scope test-typing errors; the configured repository gate is bare
`uv run mypy` (`README.md`) and passed as reported above. Green structural
gates do not override the semantic blockers.

## Section 11.8.8 classification and next action

```text
CASE
    B - successor findings invalidate settled convergence matrices

NEW CONVERGENCE EPISODE
    CE-L12-01-03

ROOT-CAUSE SURFACE
    Cross-artifact execution-seam ownership and authority: typed-result versus
    exception boundary; location-key/FsTarget derivation; split local-provider
    parity classification and cleanup ownership.

OPEN FINDINGS
    L12-R015
    L12-R016
    L12-R017

NEXT_OWNER
    Claude

NEXT_ACTION
    Perform the section 11.8.3 characterization/challenge/checkpoint flow for
    CE-L12-01-03, then one coherent shared-contract remediation with the
    witnesses above. Return the exact candidate for targeted closure review.
    Do not implement Python or Rust Layer 12 and do not start Layer 13.
```
