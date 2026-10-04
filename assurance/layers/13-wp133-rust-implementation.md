# WP-13.3 bash: Rust implementation candidate

Coordination: minion-agent#50. Requirements: TOOL-034, TOOL-034-DIV-001,
TOOL-035. This is implementation evidence, not an independent closure verdict.
Python is already approved and merged. Rust and cross-language closure remain
pending the independent exact-SHA review by Claude.

## Authority and scope

The shared contract is `spec/tools.md`, WP-13.3, including CE-WP133-01 and
CE-WP133-02, and `spec/execution.md` §16.4. Its merged origin is docs
`a805f6edaece2843daae060de69fd0c1d61acf8e`. Pinned Pi is
`b7bb00b936dbe21b8e160b3e89efdec361846699`, clean; Node is `v22.15.1`.
Audited source: bash.ts, shell.ts, child-process.ts, output-accumulator.ts and
truncate.ts. The practical-parity decision and DIV-001 remain unchanged.

Code starts from accepted main
`59cab4aa4efccfca6f9f0b3d757c1ec137fca22b`: Python WP-13.3 plus the accepted
Rust L12-D003 process-group-kill correction. Docs starts from accepted master
`9c57b075235d8902bfa98d316fc3946566eee991`, including that closure and the
Owner-authorized workflow lessons (#244). No quarantined work is used.

Only Rust implementation/test/control files and the three manifest `rust:`
evidence fields change in the code candidate. No Python, semantic rule,
disposition, canonical expectation, shared schema or lower-layer implementation
is changed. No merge is performed by this pass.

## Design and real seams

- `create_bash_tool` takes compatible `FileSystem` and `Subprocess` capabilities
  and typed `BashToolOptions`. It exposes the exact adopted definition/schema;
  there is no UI, prefix, queue or partial-update implementation.
- One per-call `base_env` snapshot feeds certified EXEC-010 composition and
  TOOL-042 context injection. Command text uses the certified UTF-16 primitive;
  USV projection is at the argv/stdin OS boundary, not validation.
- `bash_shell.rs` separates shell discovery from command execution. Followed
  existence uses `probe_dir_entry`; Windows cwd access uses `file_info`, POSIX
  uses `probe_dir_entry`. Legacy WSL stdin writes are concurrent with reads,
  exit observation and the timeout.
- Command settlement observes the real process's exit and both pipes, or the
  100 ms post-exit idle grace reset by each received chunk. A whole-millisecond
  timer begins after spawn. Abort is classified before timeout. Both read ends
  are closed at settlement without terminating descendants to release pipes.
- Lookup has its own 5 s timer and combined 1,048,576 raw-byte budget. It keeps
  the crossing stdout chunk, waits for exit plus EOF (no command idle grace),
  requests certified tree termination only while unexited, and preserves the
  final real status, including a natural zero racing best-effort termination.
  This is the approved DIV-001, not a direct-child SIGTERM implementation.
- `bash_output.rs` owns one incremental UTF-8 decoder across merged stdout and
  stderr, one leading-BOM decision, whole-stream counters, rolling tail and Pi
  truncation metadata/notices. Raw bytes, not decoded text, feed persistence.
- An ordered writer future consumes accepted chunks independently of intake.
  Settlement freezes the timeout/abort outcome before joining all accepted
  writes. There is no persistence latency cap. The writer is not spawned:
  dropping the tool future drops it, so a pending write cannot outlive the call.
  Full-output errors terminate the process and use the adopted own-error text.

The existing Layer-06 executor supplies error conversion and runtime delivery;
the runner does not reproduce production execution or replace provider results.

## Permanent evidence

`tests/builtin_bash_conformance.rs` discovers every shared builtin-bash YAML
document and executes the real tool through Layer 06 with real local fs and
subprocess providers. The 36 documents assert the platform's expected error,
text/UTF-16 head/tail, metadata, and raw full-output length/SHA-256. Only cwd and
full-output path are normalized; temporary output is removed by the harness.

A second real-provider witness synchronizes on a detached child's IPC readiness
before its parent exits. It proves settlement despite inherited pipes and checks
the child is still alive afterward. Harness cleanup kills that PID only after
the observation; no arbitrary sleep is used as a readiness discriminator.

Twenty-six focused library witnesses use controlled streams, exit futures,
virtual time, write-start gates and owned live-write counters. They cover
precheck order; positive/negative/fractional/maximum/Infinity timeout; grace
reset and pipe release; context/environment and disabled exposure; argv/stdin
surrogates; slow/failed/cancelled persistence; merged decoding; lookup budget,
status, crossing chunk and EOF; exact prerequisite/spawn/file errors; and zero
partial updates. Both fake Windows and POSIX capability worlds are exercised.

The output witnesses additionally cover ten pinned rolling-boundary rows,
incomplete EOF BOM prefixes, a BOM split across chunks, repeated BOMs, replacement
and UTF-8 byte thresholds, line limits, and JS positive-halfway size formatting.

### Fresh pinned-Pi boundary replay

Executed unchanged on Node v22.15.1:

```powershell
node --experimental-strip-types --no-warnings --expose-internals `
  assurance/layers/data/13-wp133/harness/boundary_probe.mjs `
  <clean-pinned-pi> <output.json>
```

Replay SHA-256:
`03c1221900c12f8da25acfccf67826adbd46e3a1dcbe40f74f640f3eac1d141b`.
This equals the committed authority bytes after converting the Windows checkout's
CRLF back to canonical LF. The CRLF checkout itself hashes to
`ae4bb389e61f2a5a7a5055a7d38b50a110398157f72c46b39cb608117825b502`;
those are not claimed to be raw-byte identical. The Rust fixture stores the same
canonical JSON and checks exact content hashes and complete metadata on all ten
rolling rows.

## Negative-control discipline

`minion-agent-rust/scripts/bash-negative-controls.py` copies sources and shared
fixtures to an isolated temporary workspace. It initially cleans only the tested
crate, rewrites the actual Rust source per control, compiles it, and executes the
compiler-artifact-identified library test binary. Build failure, zero tests,
unrelated failure or setup panic is not credited. Each credited result names the
intended failing witness and retains its assertion diagnostic.

The 49 controls cover precheck/classification, settlement/pipe release,
decoder/BOM/cross-stream state, persistence ordering/join/cancellation, line
dropping and whole-stream truncation, timer truncation/clamping, combined lookup
budget versus genuinely separate per-stream budgets, crossing chunks, lookup
exit/EOF/interruption/status, followed existence and Windows cwd access,
environment injection/removal/snapshot, signal delegation, command surrogate
projection, failure text and forbidden updates. Source anchors and intended
witnesses are the committed control inventory.

During development, two controls initially reached unchecked test access rather
than the intended assertion (missing truncation metadata; a removed lowercase
environment key). Neither was counted as killed. The permanent witnesses now
assert metadata presence and compare the optional environment value explicitly.
The decoder-per-stream and per-chunk-BOM witnesses were also strengthened before
the final control replay. A Windows timer-through-finalization control initially
survived because its expired timer raced the released write inside `select!`.
The witness now polls while the write is still gated, after advancing virtual
time beyond expiry, so the mutant must fail before the gate is released. The
entire final control replay uses that deterministic witness. No mutant remains
applied to the candidate.

A final precheck-neighborhood audit found and corrected the spawn checkpoint:
an abort arriving during discovery/cwd probing is `Command aborted`, not
`Failed to start the shell`. The permanent fake provider applies the certified
pre-spawn signal check; its filesystem probe changes the signal after the tool's
initial precheck. The witness proves both checks were reached but no command was
created. The new control removes only that abort-specific error mapping and
must assert the wrong spawn-failure text. Ordinary spawn failure, invalid timeout
versus pre-abort, delegated post-spawn abort and grace-period classification were
rechecked alongside it. The contract is unchanged.

Final replay results are recorded beside this assurance as
`data/13-wp133/rust/control-results-{win32,linux}.json`; they retain control name,
intended witness, exit status and observed assertion diagnostic.

## G3 environment and reproducible commands

### Windows

Windows 11 Pro 10.0.26200 x86_64, Rust/Cargo 1.97.1, Node v22.15.1. Use the verified ICU4C 78.3
Windows build, its `pinned-icu-identity.txt`, `icu/lib64` and `icu/bin64`:

```powershell
$env:CARGO_TARGET_DIR = 'C:/Users/erick/.codex/tmp/wp133-final-target'
$env:RUST_ICU_MAJOR_VERSION_NUMBER = '78'
$env:RUSTFLAGS = '-L native=<icu>/icu/lib64'
$env:RUSTDOCFLAGS = '-L native=<icu>/icu/lib64'
$env:MINION_AGENT_ICU_IDENTITY = '<icu>/pinned-icu-identity.txt'
$env:PATH = '<icu>/icu/bin64;' + $env:PATH
cd minion-agent-rust
cargo fmt --all -- --check
cargo test --workspace --all-features
cargo clippy --workspace --all-targets --all-features -- -D warnings
$env:RUSTDOCFLAGS = '-D warnings -L native=<icu>/icu/lib64'
cargo doc --workspace --no-deps
cargo run -p xtask -- conformance verify
uv run --no-project python scripts/bash-negative-controls.py
```

The actual ICU root is
`E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.toolchain/icu-78.3-src`.
The Cargo target is deliberately on C:, not the project drive.
The controls use a separate target `C:/Users/erick/.codex/tmp/l12-d003-target`;
neither control cleanup nor compilation modifies the running full suite's target.
An obsolete pre-fix full run initially still held a Windows test executable
while the final head rebuilt it, producing LNK1104. That obsolete run was stopped
and the complete final gates restarted without overlapping full runs. The failed
build is not counted as passing evidence. The pre-existing static-ICU LNK4098
CRT warning is non-fatal; strict clippy and rustdoc are separate required gates.
The first complete Windows test attempt passed its 572 unit/integration checks
but failed the two linkable doctests because `RUSTDOCFLAGS` omitted the ICU library
search path (LNK1181, `icudt.lib`); it is not a passing full gate. The final recipe
above supplies that path to doctests and applies `-D warnings` to `cargo doc`, as
required, rather than imposing it on the doctest linker. The complete suite is
rerun with that environment, not credited from the incomplete attempt.

### Linux

Docker `rust:1.97.1-bookworm`, digest
`rust@sha256:0e2bcaef56d041a486784e54104a81aebe0da44bd03019bd70bc0401e42e4a97`,
Debian 12 x86_64, procps `2:4.0.2-3`, Rust 1.97.1, mounted Node v22.15.1.
Docker's normal capability/seccomp configuration was used (no privileged mode).
The actual named volume `claude-l12r-build` holds the offline Cargo cache and the
verified Linux ICU build. ICU identity uses source SHA-512
`04a49455e1489030c520a4bfd2664fa2171e7938d08f2acdbbcb1fda976639fd8b1f0704f2eec89ba59a7b6d118ceaab6ec5a096e40d9085a0895d91ce225245`
and loaded icuuc/icui18n/icudata hashes
`77846ad3a9f2034cd965375dfb314e3f8cb74a346887b73ff32ced29486bc506`,
`e42fdc1c4da05162cbd4cba2fff4a95016ec5302035cac54a8ed009619760225`,
`561e8aa42852b1cbe491254b4549213172eecc3e812e05bbd1e555db3442d173`.

```powershell
docker run --rm -v claude-l12r-build:/build `
  -v <code-worktree>:/src -v <node-v22.15.1-linux>:/usr/local/bin/node:ro `
  -w /src/minion-agent-rust -e CARGO_HOME=/build/cargo-home `
  -e CARGO_TARGET_DIR=/build/l12d003-target -e RUST_ICU_MAJOR_VERSION_NUMBER=78 `
  -e 'RUSTFLAGS=-L native=/build/icu/lib' `
  -e 'RUSTDOCFLAGS=-D warnings -L native=/build/icu/lib' `
  -e LD_LIBRARY_PATH=/build/icu/lib `
  -e MINION_AGENT_ICU_IDENTITY=/build/icu-identity.txt `
  rust:1.97.1-bookworm sh -c 'cargo fmt --all -- --check && cargo test --workspace --all-features --offline && cargo clippy --workspace --all-targets --all-features --offline -- -D warnings && cargo doc --workspace --no-deps --offline && cargo run --offline -p xtask -- conformance verify'
```

For controls, the same mounts/environment are used with a separate target
`/build/wp133-controls-target` and `python3 scripts/bash-negative-controls.py`.
The controls additionally set `RUSTUP_TOOLCHAIN=1.97.1`; they do not invoke fmt
or clippy. The full-gate command deliberately lets the repository's toolchain
file install the pinned rustfmt/clippy components; selecting the image's bare
toolchain without installing those components initially failed the environment
prerequisite and was not counted as a gate pass.
This avoids deleting regression-suite binaries during isolated control builds.
The code mount is the actual Windows checkout; Rust reads it directly. Only the
authority hash comparison above normalizes checkout line endings.

### Results

Final exact-candidate Windows: 576 passed (572 unit/integration plus four
doctests), zero failed/ignored. Linux: 575 passed (571 unit/integration plus four
doctests), zero failed/ignored. On both platforms fmt, strict clippy, strict
rustdoc and xtask conformance verification passed. Both
platforms killed all 49 intended negative controls at code
`6df5a91a19af10bc030b237f01b9b60c855ec734`; both real-provider canonical adapters
pass all 36 documents and the readiness-synchronized descendant witness.

Docs process regression suite: 336 passed; no process implementation changed.

Shared schema/manifest validation: 441 passed, freshly run against this candidate
with `pytest -o addopts= -q tests/conformance/test_schema_validation.py
tests/conformance/test_manifest_validation.py`. No Python production change or
Python recertification is claimed.

## Handoff and boundaries

The paired candidate heads and remote reachability are recorded in issue #50 and
the local handoff `.tmp/wp133-review/RUST.md`. NEXT_OWNER is Claude for independent
complete closure review. Author-run G3 evidence is not certification. This pass
does not merge, close #50, change DIV-001, implement another work package or start
Layer 14.
