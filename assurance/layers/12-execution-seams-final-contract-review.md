# Layer 12 WP-12.1 - final complete independent Rust contract review

## Verdict

```text
shared Layer-12 WP-12.1 contract
    REJECTED

Rust Layer 12
    BLOCKED / NOT_IMPLEMENTED

Layer 12 cross-language
    NOT CLOSED

Layer 13
    NOT STARTED
```

This is the mandatory `agent-workflow.md` section 11.8.8 complete review. It
does not implement Python or Rust and does not repair shared semantic files.

The final review found six blocking gaps. They are coupled to, and in several
cases invalidate, the settled behavior matrices for filesystem cancellation,
shell failure precedence, subprocess lifecycle, the `FsTarget` bridge, and
execution-world compatibility. This is section 11.8.8 **Case B**, requiring a
new convergence episode rather than a sequence of isolated point fixes.

## Exact frozen target

- Code PR `EGAILab/minion-agent#40` @
  `71a341802349e0c6f706d599648f8566153318eb`
- Docs PR `EGAILab/minion-agent-docs#110` @
  `1279c0287d03a3ba42fa32d3ee6b25fc42b04e8a`
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Prior convergence evidence PR `EGAILab/minion-agent-docs#114` @
  `e2e2475c0ff0ba0b440c3f14c8eb78765ab835c5`
- Prior convergence episode: `CE-L12-01-01`
- New episode required by this review: `CE-L12-01-02`

At review start, issue `EGAILab/minion-agent#39` was open with
`STATUS = FINAL_CONTRACT_REVIEW`, `NEXT_OWNER = Codex`, and the exact candidate
pair above. Both candidate PRs and the evidence PR were open, Ready for Review,
unmerged, mergeable, and remote-reachable. Their heads did not move during the
review. The candidate declares it is not derived from quarantined work and no
contrary remote evidence was found.

## Authority and evidence read

The review followed the required order:

1. pinned Pi source;
2. normative `spec/execution.md`;
3. `EXEC-001` through `EXEC-006` in `pi-parity-manifest.yaml`;
4. candidate witness/evidence descriptions (there are no executable Layer-12
   canonical scenarios yet because this is a contract checkpoint);
5. certified Rust Runtime/LLM/Session/Tool/Agent/Auth architecture;
6. prior review/convergence evidence;
7. no Python Layer-12 implementation exists to use as secondary evidence.

Pinned source inspected included:

- `packages/agent/src/harness/types.ts`:
  `FileErrorCode`, `ExecutionErrorCode`, `FileSystem`, `ShellExecOptions`,
  `Shell`, `ExecutionEnv`;
- `packages/agent/src/harness/env/nodejs.ts`:
  `resolveTimeoutMs`, `resolvePath`, `getShellConfig`, `getShellEnv`,
  `waitForChildProcess`, `NodeExecutionEnv.exec`, and every filesystem method;
- `packages/agent/src/harness/tools/file-mutation-queue.ts`;
- the JSONL session filesystem-only consumer;
- relevant pinned harness tests, including shell completion behavior.

The certified Rust architecture has the necessary typed service/context,
async/future, cancellation, error, and ownership primitives. No lower-layer
reopen is currently required. The blocker is that this contract would force a
Rust implementer to choose observable semantics the shared artifacts do not
settle.

## Requirement ledger

| Row | Subject | Disposition | Final-review result |
|---|---|---|---|
| `EXEC-001` | fs/shell Result boundary and error taxonomies | adopted | coherent; no new blocker |
| `EXEC-002` | filesystem capability | adopted | **blocked by L12-R009** |
| `EXEC-003` | `FsTarget` bridge | intentional divergence | **blocked by L12-R014** |
| `EXEC-004` | shell capability | adopted | **blocked by L12-R010/R011** |
| `EXEC-005` | subprocess capability | intentional divergence | **blocked by L12-R012** |
| `EXEC-006` | execution-world identity/compatibility | intentional divergence | **blocked by L12-R013** |

The six rows remain structurally separate and their dispositions are coherent.
Manifest validation reports 101 rows and 101 unique IDs. The blockers concern
the completeness/accuracy of the rules inside five rows, not row identity or
disposition bundling.

## Findings

### L12-R009 - PI_PARITY_DEFECT - filesystem cancellation checkpoints are incomplete

Affected current rules:

- `spec/execution.md` section 3.1;
- manifest `EXEC-002`;
- the convergence cancellation witness matrix.

Pinned Pi does more than the current per-operation prose states:

- `readTextLines` checks before opening, passes the signal into the underlying
  stream, checks at each loop iteration, **and checks once more after the loop
  before returning success** (`nodejs.ts:513-540`);
- `writeFile` checks before work, awaits recursive parent `mkdir`, performs an
  explicit **after-mkdir** check, then passes the signal into the actual write
  (`nodejs.ts:555-571`).

The candidate says only "pre + each loop" for `read_text_lines`, and groups
`write_file` under generic pre/mid-I/O wording. It therefore permits realistic
wrong implementations that omit Pi-observable phase boundaries while still
satisfying the prose.

Minimal correction/witnesses:

1. abort `read_text_lines` after the last yielded line but before successful
   iterator completion; result must be `aborted`, not success;
2. abort `write_file` after parent-directory creation completes but before the
   write starts; result must be `aborted` and no content write may start;
3. state the underlying stream/write signal threading separately from the
   explicit checkpoints.

This invalidates the prior convergence matrix's claim to cover cancellation
"between multi-step phases" and is independently sufficient for Case B.

### L12-R010 - PI_PARITY_DEFECT - shell pre-spawn order still groups two distinguishable failures

Affected current rules:

- `spec/execution.md` section 5.4, step 3;
- manifest `EXEC-004`.

The candidate calls its matrix the "EXACT order" but combines `cwd/shell
resolution` into one step. Pinned Pi's actual sequence is:

```text
pre-abort
timeout validation
lexical cwd resolution
shell discovery
cwd existence check
spawn
```

`getShellConfig()` completes before `access(cwd)` (`nodejs.ts:371-390`). That
order is observable when both are invalid. With a configured nonexistent shell
and a nonexistent cwd, Pi returns `shell_unavailable`; a cwd-first
implementation returns `spawn_error`.

Minimal correction: split step 3 into the exact source order and add the
combined-invalidity witness above.

### L12-R011 - PI_PARITY_DEFECT - shell timeout's exact upper boundary is not specified

Affected current rules:

- `spec/execution.md` section 5.4;
- manifest `EXEC-004`.

The spec says a timeout exceeding "roughly `2^31/1000` seconds" is invalid.
Pi is exact: `MAX_TIMEOUT_MS = 2_147_483_647`; timeout is rejected when
`timeout * 1000 > 2_147_483_647` (`nodejs.ts:35-48`). A typed cross-language
contract cannot use "roughly" at the accept/reject boundary.

Minimal correction/witnesses:

- `2147483.647` seconds is accepted;
- a finite positive value whose multiplication by 1000 exceeds
  `2147483647` is rejected as `timeout` before shell/cwd resolution and spawn.

### L12-R012 - CONTRACT_ASSURANCE_DEFECT - `SpawnOptions` cwd/environment semantics are missing

Affected current rules:

- `spec/execution.md` section 6;
- manifest `EXEC-005`.

`ctx.subprocess` is a Minion extension, so Pi cannot fill these gaps. The shape
declares `cwd?`, `env?`, and `inherit_env=true` but never states:

- the default cwd when omitted;
- the base against which a relative cwd is resolved;
- what environment is inherited;
- whether call `env` overlays that base when `inherit_env=true`;
- whether `inherit_env=false` means exactly the supplied map.

Those choices change child-observable cwd/environment and are not Rust
mechanics. The nearby assertion that defaults match `ctx.shell` only explains
stdio defaults. Independent Python and Rust implementations can conform to the
text while producing different child processes.

Minimal correction: define provider default cwd/base environment and the exact
relative-cwd and environment merge rules, with direct child-observation
witnesses for omitted/relative cwd and both `inherit_env` values.

### L12-R013 - CONTRACT_ASSURANCE_DEFECT - execution-world compatibility promises a primitive but does not define one

Affected current rules:

- `spec/execution.md` section 7;
- manifest `EXEC-006`.

The owner decision requires WP-12.1 to own a reusable compatibility vocabulary
and validation mechanism. The candidate says an opaque identity exists and a
consumer validates it, then claims the row owns "the comparison/validation
primitive a consumer calls," but gives no type shape, operation, compatibility
relation, or typed failure result. It does not even explicitly settle whether
compatibility is identity equality or may be a broader relation.

Minimal correction: define a language-neutral identity/comparison-validation
API, state the compatibility relation, and define the failure observation
(including how provider names enter the diagnostic). Witness at least:

- equal/compatible local identities pass;
- incompatible identities fail and name both providers;
- mixed worlds remain legal until a same-resource consumer invokes validation.

### L12-R014 - CONTRACT_ASSURANCE_DEFECT - `process_path` foreign-provider allowance contradicts target scoping

Affected current rules:

- `spec/execution.md` section 4;
- manifest `EXEC-003`.

The candidate correctly says `target_key` is opaque and meaningful only within
the producing provider instance, and that execution-world compatibility does
not establish cross-provider resource identity. It then permits
`process_path(target)` on either the producing provider **or another merely
world-compatible provider**, while allowing a provider unable to detect a
foreign key not to reject it. World compatibility does not give a second
filesystem provider authority or information to decode the first provider's
opaque key. The rules therefore permit both rejection and a guessed path for
the same observable call.

Minimal correction: either require `process_path` to be called on the producing
filesystem provider (the returned path is then consumed by a validated-
compatible shell/subprocess provider), or define a real transferable target
representation/protocol. Mere world compatibility is insufficient.

## Whole-contract audit results

The final review also rechecked the previously-settled high-risk areas:

- error domains and expected-failure-vs-invariant-exception boundary;
- uniform filesystem `signal?` API and accept-but-ignore operations;
- lexical/canonical/lstat/content-I/O symlink behavior;
- location-based `target_key` derivation and the symlinked-ancestor exception;
- shell resolution, environment merge, callback errors, whole-tree kill, and
  the 100ms resettable idle-grace completion rule;
- subprocess argv-direct execution, stdio modes, raw byte chunks, one-signal
  model, wait/terminate classification, wait/stdio independence, idempotence,
  disposal obligation, pipe-error independence, and whole-tree termination;
- local-provider split and Layer-13 boundary;
- all six manifest dispositions and evidence placeholders.

No additional blocker was found in those areas. `L12-R001` through `L12-R008`
remain historically/provisionally closed for the exact issues they addressed;
the new findings are successor gaps exposed only by the mandatory whole-surface
review.

No active `PI_BEHAVIOR_UNCERTAIN` remains: the Pi-side behavior underlying
`L12-R009` through `L12-R011` is source-resolved. `L12-R012` through
`L12-R014` are shared-contract completeness/consistency defects on explicitly
Minion-owned surfaces.

## Rust implementability and lower-layer impact

```text
Rust can implement WP-12.1 without guessing observable semantics
    NO

Certified lower-layer reopen required
    NO

Rust Layer-12 code modified
    NO

Python Layer-12 code modified
    NO

Shared semantic candidate modified by reviewer
    NO
```

Rust already has appropriate typed service registration, cancellation handles,
async execution, ownership, and typed-error patterns. The findings require
shared Layer-12 contract/evidence changes, not changes to certified Layers
01-11.

## Fresh gates

Run against the exact candidate:

```text
uv run pytest --no-cov
    1504 passed, 19 xfailed

uv run ruff check .
    PASS

uv run pytest --no-cov \
    tests/conformance/test_manifest_validation.py \
    tests/conformance/test_schema_validation.py -q
    213 passed

manifest rows / unique IDs
    101 / 101
```

An initial narrow schema invocation omitted `--no-cov` and therefore hit the
repository's expected 100%-coverage guard with no production modules imported;
the corrected validation command above passed. This invocation error is not a
candidate failure and is disclosed rather than hidden.

Green structural gates do not override the semantic blockers above.

## Section 11.8.8 classification and next action

```text
CASE
    B - coupled/new semantic surface; prior convergence matrices invalidated

NEW CONVERGENCE EPISODE
    CE-L12-01-02

OPEN FINDINGS
    L12-R009
    L12-R010
    L12-R011
    L12-R012
    L12-R013
    L12-R014

NEXT_OWNER
    Claude

NEXT_ACTION
    Characterize and challenge the six findings as one execution-seam
    behavior matrix, record an agreed CE-L12-01-02 checkpoint, then perform
    one coherent shared-contract remediation pass with discriminating
    witnesses. Return for targeted closure; do not begin Python/Rust Layer-12
    implementation and do not start Layer 13.
```
