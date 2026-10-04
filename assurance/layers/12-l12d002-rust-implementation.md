# L12-D002 Rust implementation candidate — EXEC-012

Coordination: [minion-agent#144](https://github.com/EGAILab/minion-agent/issues/144).
Code candidate: `0e16d4aeaf692df87457b51243ce30868427e6a1`
on `layer/12-d002-rust`, [PR #145](https://github.com/EGAILab/minion-agent/pull/145)
(unmerged; independent review pending).
Authority: accepted code `c06e1c7a642f25fb4e1882690efda6d9cabc1fcb`, accepted docs
`ac5bd045b5b9733de31478feaf4e0c702e9cbea3`, spec/execution.md §§6 and 16,
and [Owner Option A](https://github.com/EGAILab/minion-agent/issues/144#issuecomment-5975624637).
Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`;
`packages/coding-agent/src/utils/child-process.ts::waitForChildProcess` destroys
read streams at its consumer settlement. The generic close seam is the approved
MINION_EXTENSION, not a new claim that Pi exposes this API.

## Implementation

`ReadableStream` gains async `close(&self)`. Each local reader owns an optional
Tokio pipe and an independent watch channel. Close first publishes EOF and wakes
pending/queued readers; it then takes and drops this reader only. A separate async
permit serializes reads, but the mutex guarding the OS reader is held only during
each nonblocking AsyncRead poll, never across Pending. Close does not acquire the
serialization permit: even a parked, unpolled read cannot block it. No process
signal, sibling operation, output draining, detached cleanup task, or polling
timer is introduced. Natural EOF also takes/drops the reader. A retained public
Arc does not retain the closed OS pipe.

The existing shared exit monitor and `wait()` are unchanged. Cancelling a waiter
drops only its receiver future. `terminate()` snapshots settlement without holding
a channel borrow across an await; on an already-settled process it closes stdout,
stderr and stdin. Live tree termination and first-claim/exit-code classification
remain unchanged. No Python, canonical scenario, shared rule or disposition changes.
The manifest change is solely the EXEC-012 Rust evidence pointer.

## Permanent witnesses and controls

`tests/execution_stream_close.rs` uses the test executable itself as a child and
descendant fixture. Stdin handshakes—not sleeps or assertion retries—control late
writes and exit. A parent exits while its descendant holds both readable pipes;
wait settles, and output is still read afterward. Tests cover natural EOF,
pending/later reads, repeated close, buffered-output abandonment, both sibling
directions, live-child survival, descendant survival with a broken write after
local handle release, cancelled waiters, and wait-then-terminate with retained
stream Arcs. Close is awaited while an already-polled Pending read is parked;
only afterward is that read polled again to observe EOF. A timeout is a failure
bound, not the scheduling mechanism.

`scripts/l12-d002-negative-controls.py` changes only disposable workspace copies,
checks unique source anchors, forces package rebuilding, and requires an actual
one-test assertion failure; compilation/setup failures never count as kills.
Controls: wait joins pipes; wait closes pipes; close deadlocks behind a read;
close keeps the OS handle; closed reads report pipe_error; close affects the
sibling; close kills the child; cancelling a waiter poisons the process result;
and settled terminate keeps handles. All nine are run separately on each OS.

Owner witness 12 and the two bash-specific controls remain WP-13.3 work. This pass
does not implement or certify the bash consumer. Rust has no Python destructor
warning mechanism; actual handle release is discriminated by a surviving
descendant's failed write and by retained stream objects yielding EOF.

## Gate record

Fresh counts and exact pushed candidate heads are recorded with the handoff.
Toolchain: Rust 1.97.1; pinned ICU4C 78.3 with the verified library identity.
Windows cargo target is on C:, not E:. Linux runs in `rust:1.97.1-bookworm`, using
the separately built pinned ICU and its hash-checked identity.

- Windows: all 544 workspace unit/integration tests pass, including 7/7 in the
  new test binary (six behavior witnesses and the fixture entry). Four doctests
  pass after supplying rustdoc's native ICU library path; combined result 548/0.
- Linux: the same new binary passes 7/7. The nine controls are killed 9/9 on
  Windows and 9/9 on Linux, with actual test failures (not compiler failures).
- Shared manifest/schema validation: 404/404; manifest 119 unique rows.
- Docs process tests: 336/336 (no process files changed).
- `cargo fmt --all -- --check`: PASS.
- `cargo clippy --workspace --all-targets --all-features -- -D warnings`: PASS.
- `cargo doc --workspace --no-deps` with `RUSTDOCFLAGS=-D warnings` plus the
  pinned ICU native-library search path: PASS.
- `cargo run -p xtask -- conformance verify`: PASS.

Gate execution note: the Windows `cargo test --workspace --all-features` run
passed every unit/integration binary, then two positive doctests could not link
`icudt.lib`: `RUSTFLAGS` is not rustdoc's native-library search configuration.
The complete workspace doctest suite was re-executed with
`RUSTDOCFLAGS=-L native=<the pinned ICU lib64 directory>` and passed 4/4.
These are reported separately rather than calling the original command a zero
exit. No source or dependency change was made to fix that environment.

An earlier development run shared its target directory with a control run,
allowing a mutant executable to replace the candidate executable before Cargo
launched it. That run was invalidated, not used as candidate evidence. All final
controls and positive gates are serialized per target; the final candidate was
rebuilt after the controls. The permanent script explicitly documents this
prerequisite. Local detailed logs are under `.tmp/l12d002-review/`.

## Disclosed pre-existing Linux termination defect

Classification: PI_PARITY_DEFECT in existing EXEC-005 termination behavior,
outside the new EXEC-012 operation. Separate remediation/triage is required;
neither a green Linux full regression nor a new divergence is claimed here.

On both accepted `c06e1c7a` and this candidate, the Debian container's existing
`execution_process` suite has 4 passes / 2 failures:
`explicit_termination_is_success_with_the_os_reported_exit_code` observes Some(0)
instead of None, and `spawn_signal_controls_pre_and_post_spawn_cancellation`
times out. `execution_shell` has 7 passes / 1 failure:
`cleanup_terminates_active_commands_without_classifying_abort` times out.
These are not claimed green or explained away as environment-only noise.

The unchanged `kill_process_tree` passes `-KILL` and a negative group id to the
external `kill` utility without `--`. A separate controlled process-group probe
on this container reports that the process remains alive; adding the utility's
argument separator in the probe allows cleanup. This is a pre-existing
lower-layer termination defect exposed by regression checking, not an EXEC-012
change. It is disclosed for separate triage; this candidate does not remediate it
or redefine the certified terminate semantics. The new Linux close witnesses and
their controls are tested independently of these failing regression binaries.

## Handoff boundary

Rust implementation: candidate, NOT independently certified. I002 cross-language
closure remains reserved under Owner §13. Independent closure review must verify
the exact paired heads, new close/disposal evidence, and the baseline comparison
above. No merge or next-layer work is performed by this implementation pass.
