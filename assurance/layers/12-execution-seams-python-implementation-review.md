# Layer 12 Python implementation independent review

Mode: independent implementation review

Verdict: **REJECTED**

## Exact review target

- Python candidate: `EGAILab/minion-agent` PR #44 at
  `849d4ea5aba12090ad663f5e16ece4bf1a369990`
- candidate base: `2b309ee8cecbc333a7965781087677bd6cbba46b`
- current docs baseline: `3da25015383c4ff6bda956b34d91e05b25f49660`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- approved Rust implementation evidence:
  `assurance/layers/12-execution-seams-rust-implementation.md`

The candidate SHA was fetched from GitHub and reviewed in a clean detached worktree. PR #44 was
open, ready for review, and mergeable at that exact SHA. The coordination issue was reconciled to
open/`IMPLEMENTATION_REVIEW` before substantive review. This verdict applies only to the exact
candidate above.

## Authority order and scope

The review used the required order:

1. pinned Pi `harness/types.ts`, `harness/env/nodejs.ts`, relevant tests, and the file-mutation
   queue;
2. `spec/execution.md`;
3. `pi-parity-manifest.yaml` (`EXEC-001` through `EXEC-006`);
4. existing certified Rust execution architecture;
5. the Python assurance/handoff;
6. Python implementation and tests as secondary implementation evidence.

This was review-only. No Python, Rust, normative spec, manifest rule, or canonical scenario was
modified. Layer 13 was not started.

## Requirement ledger

| Row | Result | Independent review |
|---|---|---|
| `EXEC-001` | PASS | Error/result vocabulary and basic no-operational-exception shape are present, subject to the `read_text_file` exception defect in R002. |
| `EXEC-002` | FAIL | Cancellation checkpoints, path joining/file-URL behavior, and UTF-8 text decoding are not Pi-compatible. See R001 and R002. |
| `EXEC-003` | PASS | `FsTarget` exists and carries provider provenance. The larger service/world integration is covered by R003. |
| `EXEC-004` | FAIL | Shell callbacks expose bytes instead of decoded strings and an abort race is misclassified as `spawn_error`. See R005 and R006. |
| `EXEC-005` | FAIL | The public subprocess capability/service seam and causal abort classification are incomplete. See R003 and R004. |
| `EXEC-006` | FAIL | Providers neither expose execution-world identity nor integrate as the named Runtime services required by the contract. See R003. |

## Findings

### L12-PY-R001 — filesystem cancellation checkpoints are incomplete

**Taxonomy:** `PI_PARITY_DEFECT`  
**Severity:** blocking

Pinned Pi threads the abort signal through the underlying text/binary read and write operations,
checks write cancellation before work and again after parent creation, and checks directory-listing
cancellation before enumeration and during entry processing. The approved contract pins those
operation-specific checkpoints.

The candidate uses blocking `asyncio.to_thread(...read/write...)` calls that cannot settle promptly
when cancellation arrives mid-operation. `list_dir` has no pre-enumeration abort check. A
pre-aborted empty directory therefore returns `Ok([])`, and a deliberately blocked read remained
pending after cancellation and eventually returned `Ok` after the blocking read was released.

Minimal correction: implement every approved checkpoint, including prompt mid-read/mid-write
settlement and the list pre-check/per-entry checks, without forced task cancellation or a second
filesystem authority. Add permanent witnesses that fail when each checkpoint is removed.

### L12-PY-R002 — path and text semantics diverge from pinned Pi

**Taxonomy:** `PI_PARITY_DEFECT`  
**Severity:** blocking

Independent probes found three distinct observable mismatches:

- `join_path([])` returns `Ok("")`; Node `path.join()` and the certified Rust implementation return
  `"."`.
- Windows joining treats a later rooted component as replacement (`["a", "\\b"] -> "\\b"`),
  whereas pinned Node joining produces `"a\\b"`.
- malformed `file:` URLs are silently converted to unrelated paths instead of retaining the
  literal input after `fileURLToPath` fails.
- invalid UTF-8 causes `read_text_file` to raise `UnicodeDecodeError`; pinned Node decoding returns
  replacement text (`"�"`). This also violates the operation's typed-result error boundary.

The candidate's malformed-file-URL test only asserts that the result is a string and therefore
does not discriminate the wrong path.

Minimal correction: reproduce the approved Node path/file-URL and UTF-8 replacement semantics,
including resolved-path error reporting, and add exact-output witnesses for empty joins, rooted
later segments, malformed file URLs, and invalid UTF-8.

### L12-PY-R003 — the execution capability/service and world-identity abstraction is missing

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`  
**Severity:** blocking

The contract requires `ctx.fs`, `ctx.shell`, and `ctx.subprocess` as independently swappable
capabilities; every provider declares an opaque execution-world identity; the three local
providers share one identity by construction; and Runtime service names are `fs`, `shell`, and
`subprocess`.

The candidate's `LocalFileSystem`, `LocalShell`, and `LocalSubprocess` expose no
`execution_world`. The public filesystem/shell protocols omit it, there is no public `Subprocess`
protocol, and `LocalShell` depends on concrete `LocalSubprocess`. No execution capability exposes
the Runtime `__service_name__` needed by `Context.require(...)`. Consequently this implementation
does not provide the contracted `ctx.*` seams or permit independent provider substitution and
compatibility validation.

Minimal correction: add typed filesystem, shell, and subprocess capability/service abstractions
with their exact names and execution-world identity; make local providers share one world; and
have shell depend on the subprocess abstraction rather than the concrete local class. Reuse the
certified Runtime registry rather than creating another service authority.

### L12-PY-R004 — process wait attributes abort from current state rather than exit cause

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`  
**Severity:** blocking

The Minion subprocess contract permits `Err(aborted)` only when the process was killed because the
spawn-supplied signal fired. Natural exit and explicit `terminate()` retain their actual successful
exit status.

`Process.wait()` instead checks whether the signal is currently aborted when settlement is
observed. A process that exited naturally before a later abort was reported as aborted. An
explicitly terminated process followed by a signal abort was also reported as aborted. The
candidate docstring describes this non-causal behavior, but the approved contract does not.

Minimal correction: record the actual termination cause at the point the process is killed and
classify `wait()` from that cause. Add the two discriminating late-abort witnesses above.

### L12-PY-R005 — shell callback payloads expose raw bytes instead of decoded text

**Taxonomy:** `PI_PARITY_DEFECT`  
**Severity:** blocking

Pinned Pi's shell callbacks receive decoded string chunks after UTF-8 stream decoding. The
contract also explicitly distinguishes shell text callbacks from raw subprocess byte streams.
The candidate's public `Shell.exec` and `LocalShell.exec` types are
`Callable[[bytes], None]`, and a live probe observed `bytes` payloads.

Minimal correction: perform incremental UTF-8 decoding across chunk boundaries and invoke shell
callbacks with strings while keeping raw bytes confined to the subprocess seam. Add a split
multibyte-character witness, not only an ASCII type assertion.

### L12-PY-R006 — the shell spawn/abort race is misclassified

**Taxonomy:** `PI_PARITY_DEFECT`  
**Severity:** blocking

When the signal aborts after shell's first check but before subprocess spawn, the subprocess seam
correctly reports `aborted`. The candidate maps every spawn error to shell `spawn_error`. A
deterministic signal that flips between those two checks reproduced
`Err(ShellErrorCode.SPAWN_ERROR, "aborted")`; the contract requires shell `aborted`.

Minimal correction: preserve the subprocess abort classification through shell spawn and add a
deterministic race witness.

### L12-PY-R007 — Windows process-tree cleanup leaks subprocess resources

**Taxonomy:** `PARITY_NEUTRAL_HARDENING`  
**Severity:** blocking quality defect

The ordinary full suite passes but emits an unraisable-exception warning for an unclosed Proactor
pipe transport. With resource/unraisable warnings promoted to errors, the execution suite fails.
The Windows `_kill_process_tree` helper starts `taskkill` through `subprocess.Popen` and discards
the process handle without waiting for or otherwise settling it, producing additional
`ResourceWarning: subprocess ... is still running` failures.

Minimal correction: settle/close the helper process and all owned pipe transports on every path,
without weakening cancellation or tree-termination behavior. Add a resource-warning-clean
execution-suite gate.

## Discriminating observations

The following observations were reproduced against the exact candidate:

```text
pre-aborted list_dir(empty directory)  -> Ok([])            # expected aborted
mid-read abort prompt settlement       -> timed out          # expected prompt aborted
mid-read final result after release    -> Ok("x")            # expected aborted
join_path([])                          -> Ok("")             # expected "."
invalid UTF-8 read_text_file           -> UnicodeDecodeError # expected replacement text
LocalFileSystem.execution_world        -> absent
LocalShell.execution_world             -> absent
LocalSubprocess.execution_world        -> absent
natural exit, then abort, then wait    -> Err(aborted)       # expected actual exit
terminate, then abort, then wait       -> Err(aborted)       # expected actual exit
shell callback payload type            -> bytes              # expected str
abort between shell check and spawn    -> spawn_error        # expected aborted
```

These are implementation witnesses, not alternate contract interpretations.

## Fresh gates

Run from the exact candidate's `minion-agent-python/` directory:

```text
uv run pytest
    PASS: 1657 passed, 1 skipped, 19 xfailed
    coverage: 100% (4588 statements)
    warning: PytestUnraisableExceptionWarning for an unclosed Proactor transport

uv run ruff check .
    PASS

uv run ruff format --check .
    FAIL: 7 pre-existing files would be reformatted; none is part of this candidate

uv run mypy
    PASS: 78 source files

uv run pytest tests/conformance/test_schema_validation.py \
              tests/conformance/test_manifest_validation.py --no-cov -q
    PASS: 213 tests

uv run pytest tests/execution --no-cov \
              -W error::pytest.PytestUnraisableExceptionWarning \
              -W error::ResourceWarning
    FAIL: 9 tests plus 1 teardown error from leaked subprocess/pipe resources
```

Green aggregate tests do not override the reproduced semantic defects.

## Contract-quality answers

- Does the Python implementation reproduce the approved contract independently? **No.**
- Does it reuse the contracted Runtime/capability model? **No; the named capability/service and
  execution-world seams are absent.**
- Is the subprocess abort result causally grounded? **No.**
- Are shell and filesystem Pi semantics complete? **No.**
- Did this review identify a defect in the approved shared contract? **No.** The failures are in
  the Python implementation/evidence; the certified Rust design demonstrates that the contract is
  implementable without the identified shortcuts.
- Was any runner found simulating Layer-12 behavior? **No Layer-12 canonical runner exists.** The
  approved contract intentionally uses direct language evidence for this work package.

## Verdict and state

```text
shared Layer-12 contract
    APPROVED / unchanged

Rust Layer 12
    CERTIFIED

Python Layer 12
    NOT CERTIFIED

Layer 12 cross-language
    NOT CLOSED

Layer 13
    NOT STARTED
```

PR #44 at `849d4ea5aba12090ad663f5e16ece4bf1a369990` is rejected. Return only the
seven narrow findings above to the Python owner. Any updated candidate SHA requires the workflow's
ordinary targeted implementation re-review before a final complete review. No convergence trigger
is active from this first implementation review.
