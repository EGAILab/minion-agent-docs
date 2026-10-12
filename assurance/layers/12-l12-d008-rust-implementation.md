# L12-D008 Rust implementation — DIV-008

Status: L12D008-RR001 remediation complete; independent Rust closure re-review pending.
Not certified. Coordination: minion-agent#215; provenance: #127.

## Baselines and authority

- Code baseline: `e925266b8e3999d4fb3ed392e077bf2451739f35` (merged #216).
- Docs baseline: `4eba7f6a61889aa249d270203c5764dc9e11d27b` (merged #294).
- Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`.
- Node v22.15.1 `internal/fs/rimraf`, `_rmchildren`: starts all siblings;
  reports the first callback failure; remaining siblings drain; final rmdir
  runs only after all children succeed. Executed source inspection through
  `process.binding('natives')` at Node v22.15.1.
- Contract: spec/execution.md §19.5 rule 4 and §20; DIV-008; EXEC-002-DIV-008.
- Owner amendment: #215 issuecomment-6118734550, “Continue siblings”.

Python is not the Rust oracle. Rust retains the authorized sequential selection
and timing divergence, while requiring parity with Pi's drained extent.

## Implementation

The existing explicit `Work` stack remains the traversal authority. Each step
returns its own terminal `FsError`. The outer loop retains the first error and
continues processing the remaining work. A monotonically increasing terminal
failure counter is captured when children are pushed. A directory's final-rmdir
frame runs only if that counter has not changed during its subtree. Earlier
sibling errors do not suppress an otherwise successful later subtree.

No sorting, recursion, new mapper, or alternative remove provider is introduced.
Target validation, missing-entry acceptance, fresh classification, directory
routing and Windows EPERM recovery are unchanged. Non-entered subtrees are never
scheduled. The first error's code and origin remain unchanged.

## Real-provider evidence

`rimraf/tests/div008.rs` invokes the real `LocalFileSystem.remove` with the
existing private native-operation seam. Its trace records actual native calls,
injected settlements, and native failures. It never determines terminality from
an opcode. The shared comparator v3 remains the selection/extent oracle.

The shared matrix and Pi Windows/Linux JSONL are copied as test data. The default
test executes 25 controlled rows; `DIV008_NATURAL=1` additionally executes the
two Linux permission rows ten times each, requiring an unprivileged caller.
Permanent witnesses also distinguish first-vs-last failure and subtree-local
failure propagation. Controls are compiled in a disposable `control-code` copy
and credit only their intended witness's assertion after a passing baseline.

Fresh complete gates, probe/comparator outputs, intended-control results and
remote candidate heads are recorded below. Draft milestones remain history.

### Windows development evidence

- Three permanent Rust witnesses passed; the matrix witness executed all 25
  controlled rows with every injection fired and Pi's drained extent preserved.
- Shared comparator v3: 20 MATCH + 5 DIV-008, 0 FAIL/INVALID; comparator self-test
  23/23 and real-row control replay 9/9 passed.
- Four compiled Rust controls killed at their intended named assertions, with
  selected/passing baselines and a passing restored baseline: stop-at-first
  (`continue siblings, retaining only`), report-last (`first terminal origin,
  not last`), global-error suppression of a successful later subtree (`continue
  siblings, retaining only`), and final-rmdir after a failed descendant (`no final
  rmdir of failed subtree`). No compile/setup failures are credited as kills.
- The named subtree-local witness scripts its enumeration dependency's order to
  place a failed subtree before a successful one. The matrix probe and production
  walk never sort native enumeration.
- Full Windows G3 and Linux evidence are still pending at this draft milestone.

## Development setup failures (not evidence credits)

The first focused Windows build omitted `RUST_ICU_MAJOR_VERSION_NUMBER` and
failed compiling rust_icu_sys. A subsequent attempt supplied the version but
omitted the established RUSTFLAGS native library directory and failed linking
ICU symbols. Both were investigated as launcher setup errors; neither is a
passing test or a credited gate. The corrected command uses the established
version, native library path, identity file and DLL PATH with four Cargo jobs.

The initial matrix assertion incorrectly assumed every injected fault was
terminal; B2 correctly succeeded after recovery and rejected that assertion. The
test now compares success versus failure against Pi's actual result. No product
change was required for this test defect. The corrected three-witness run passed.

The first PowerShell G3 launcher stopped on Cargo's normal stderr progress because
PowerShell's `NativeCommandError` interacted with `ErrorActionPreference=Stop`.
It was replaced with hidden `Start-Process`, separate stdout/stderr capture and an
explicit exit-code check. That interrupted launcher is not G3 evidence.

The Start-Process launcher subsequently did not return after Cargo had exited.
Only that verified owned launcher was stopped, with no Cargo/rustc still active;
no other process was stopped. Its captured 678 passing tests were preserved but
not credited as complete G3 without a confirmed native exit. A revised
Start-Process wait exposed a null ExitCode and failed closed at native-fs-check.
The final Windows launcher uses Python subprocess execution with regular-file
stdout/stderr capture and a separate recorded native return code per gate.
That rerun confirmed exit 0 for every gate (678 passed, 0 failed, 0 ignored).

### Manifest-check containment incident

The first optional manifest-check command used `pytest -c NUL --noconftest`.
Pytest inferred a device-path root, attempted cache creation below
`\\.\NUL\.pytest_cache`, and Windows refused those attempts with error 87.
Collection also performed a read-only stat outside the project (`E:\WpSystem`),
which failed with error 1337. This was an uncontained cache-write attempt in the
launcher, not an executed test or a credited result. The cache creation failures
are explicit in the captured output; no outside cache creation succeeded.

The check was stopped and investigated. The corrected recipe uses a real config
file under project scratch and explicit project-local `--rootdir`, `cache_dir`
and `--basetemp`; these paths are proven before execution. Never use a Windows
device (`NUL`) as a pytest configuration file. Linux has not started at this point.

The corrected contained manifest check passed **8/8** before the Linux batch.
No cache was created at a device path. The final Linux batch ran afterwards,
sequentially, and exited 0.

## Fresh complete gates and acceptance

Frozen code candidate: minion-agent PR **#219**,
`856cab3df3f5f810ea1513d0406f7f0383d14a75`, branch `layer/12-d008-rust`.
Companion docs PR: **#296**, branch `assurance/12-d008-rust`; the exact final
assurance SHA is recorded in the SHA-bound handoff on #215. No shared rule,
canonical expectation, or Python production file changes in this pair.

Windows completed before Linux started. The host reservation excluded other
gate/build batches; the unrelated long-lived pgvector container was not a gate.
Linux container `b34d8feecae6` exited **0** and was removed before batch-done.

| Gate / witness | Windows | Linux |
|---|---|---|
| `cargo check -p minion-agent-native-fs` | exit 0 | exit 0 |
| `cargo fmt --all -- --check` | exit 0 | exit 0 |
| strict workspace/all-target/all-feature clippy | exit 0 | exit 0 |
| workspace/all-feature tests | **678 passed, 0 failed, 0 ignored** | **670 passed, 0 failed, 1 ignored** |
| warning-strict rustdoc, workspace/no-deps | exit 0 | exit 0 |
| xtask conformance verify | exit 0 | exit 0 |
| focused removal regressions | 12 passed | 10 passed |
| real-provider matrix probe | 25 controlled rows | 45 rows, uid/gid 1000 (25 controlled + 20 natural) |
| shared comparator v3 | 20 MATCH + 5 DIV-008; 0 FAIL/INVALID | 19 MATCH + 26 DIV-008; 0 FAIL/INVALID |
| comparator self-test | 23/23 | 23/23 |
| real-row comparator controls | 9/9 | 15/15 |
| compiled Rust controls | **4/4 KILLED**, restored baseline green | **4/4 KILLED**, restored baseline green |
| shared manifest validation | 8 passed | same manifest; no separate Python validation claimed |

All planned binding injections fired. The probe compares every expected
`(id, run)` with the matrix and refuses omissions/duplicates; the comparator
checks trace readiness/completeness, declared terminality against Pi, unchanged
selected code/origin, and exact drained extent. No partial, failed, setup-error or
unfired run is credited. The four Rust mutant assertions and baseline recipes are
the same on both platforms (`scripts/div008-negative-controls.py`). The controls
compile their mutations; source-anchor failures, compilation failures, absent
witnesses or unrelated assertions are INVALID, not kills.

The Linux ignored full-suite test is the real POSIX permission witness
`recursive_remove_single_failure_reports_the_inner_native_call`; it was rerun
explicitly as uid/gid 1000 and passed **1/1**. The permission-sensitive
`fs_path_domain_conformance` and `fs_remove_readonly_conformance` binaries also
passed unprivileged (**2/2** each). Their caught containment-test panics in raw
`--nocapture` logs are intended rejecting witnesses, not failures. The 41 CE-02
routing/recovery/validation rows, directory-link rows, concurrent-disappearance
and explicit-stack witnesses remain covered by the focused/full regressions.

Raw probe, comparator, full-test and intended-control logs are committed in
`data/l12-d008/rust/`. Earlier L12-D007 mutation scripts are historical,
source-anchored evidence; this pass does not claim they were rerun unchanged
against the refactored step function.

## Environment and reproduction

Windows: Windows 11 Pro x86-64, build 26200; Rust 1.97.1; Node v22.15.1;
pinned ICU4C 78.3, official search-engine artifacts. Dot-source the project's
`.agents/project-environment.ps1` in each shell and run `gate-preflight.ps1`
before the batch. Four Cargo jobs; the shared Windows target/home remain on E:.
Set `RUST_ICU_MAJOR_VERSION_NUMBER=78`,
`RUSTFLAGS=-L native=<project>/.toolchain/icu-78.3-src/icu/lib64`,
`RUSTDOCFLAGS=-D warnings -L native=<same directory>`, ICU `bin64` on PATH,
`MINION_AGENT_ICU_IDENTITY=<project>/.toolchain/icu-78.3-src/pinned-icu-identity.txt`,
and `MINION_SEARCH_ENGINE_ARTIFACTS=<project>/.toolchain/search-engines/dl`.
Run the seven Cargo commands above sequentially and capture native return codes.
The pre-existing ICU LIBCMT/LNK4098 linker warning is disclosed, not suppressed.

Run `python scripts/div008-probe.py --tree <Rust workspace> --data <approved
docs data/l12-d008> --logs <project-local fresh log directory>` for the Windows
probe/comparator/controls. Run `python scripts/div008-negative-controls.py
--tree <project-local disposable control-code/minion-agent-rust> --logs <fresh
contained logs>` for compiled controls. Copy the tracked Rust/conformance trees
and the same three Python fixture stores named in the Linux recipe; prove each
copy destination, and never mutate the candidate or shared targets.

Linux: cached `rust:1.97.1-trixie`, image
`sha256:b1b3c9c0d921d7fa0a6d1f9ec7e4eab87f8c8ec97644c3d791450f131dec813f`;
Debian 13.6 x86-64, Python 3.13.5, Rust 1.97.1, Node v22.15.1;
kernel `6.18.40.1-microsoft-standard-WSL2`. No privileged mode or added capability.
Exact container recipe: `scripts/div008-linux-gates.sh` at the frozen code head.
The launcher uses a read-only container root, private executable `--tmpfs /tmp`
(6 GiB), and resolved/real-path-proven project-root bind sources immediately
before Docker: source/data/ICU/Node/search artifacts read-only, Linux Cargo
home/target and logs writable. No named volumes. The source is copied to private
tmpfs and CR stripped from `*.sh`. Four Cargo jobs and
`RUSTFLAGS/RUSTDOCFLAGS -L native=/build/icu/lib`, with Node on PATH.
The uid-1000 probe executes Cargo's built test binary via `--binary --natural`,
with supplementary groups cleared; no root permission result stands in for it.

The byte-copied shared data matched the approved docs worktree SHA-256 values:

- `div008-matrix.json`: `de25c7953fbcb50815bc157a971b42f4b5399c3debda6afbc52a7b8b9eec5da6`.
- `div008-pi-win32.jsonl`: `200e041f543f7e3763e161aaddcc633f143b10852b7d7cc63fdf9175e97f0d10`.
- `div008-pi-linux.jsonl`: `49ee131340fdeecac0bef0d52165730cc6f35d5f0fbfd8de6c5cd9183b6a38d4`.

## Handoff and exclusions

Rust implementation candidate only: **not certified**, independent closure review
pending. Python/shared baseline is approved and merged; cross-language L12-D008
and provenance #127 are **not closed** by this author record. No new divergence
is proposed; only approved DIV-008 selection/timing differs from Pi. Extent parity
is required and observed. The existing exotic reparse-point gap (#207 / L12-D010)
and native-name decoding #133-F2 are not expanded or repaired here.

Next action: Claude's independent Rust closure review at the exact pushed pair.

## Closure review 1 and L12D008-RR001 remediation

Claude's independent review (#215 issuecomment-6126355394) rejected the pair
`856cab3d` / `9f781d0d`: the production walk and the committed comparator outputs
were sound, but 11 certified L12-D007 control anchors were stranded by the
`step()` extraction. The earlier disclosure that those controls were not rerun
is history, not an acceptance of this assurance regression. No production,
shared-contract, canonical-expectation or Python change is made in this repair.

The read-only review audit found each of the following old anchors once at
`e925266b` and zero times at the rejected head. The repaired control script
resolves the equivalent branches in `step()`:

| Control | Old anchor / mutation site | New anchor / mutation site (same intended defect) |
| --- | --- | --- |
| N1 | Directory terminal `Err` before `FinalDirectory` | Same terminal `Err` before the new guarded `FinalDirectory(_, before)`; attempt unlink after directory failure |
| N2 | Same old Directory terminal `Err` | Same new Directory terminal `Err`; retry rmdir after directory failure |
| N3 | Entry unlink terminal `Err` before Directory | Same Entry unlink terminal `Err` at `step` indentation; swallow failure, keep descent return intact |
| N4 | Same Entry unlink terminal `Err`, origin `path` | Same terminal `Err`, origin `root_path`; thread the original remove target into `step` in this mutant only |
| N5 | Indented `Work::Directory(p, original)` arm | Same arm in `step`; enumerate before first rmdir |
| N6 | Classification EPERM, `recover(..., &mut stack); continue` | Classification EPERM, `recover(..., stack); return Ok(())`; skip recovery |
| N11 | Entry arm with in-scope `recursive` and `path` | After validation, before the stack is constructed; nonrecursive file goes straight to unlink and bypasses shared routing |
| child-vanish-windows-only | Missing classification `continue` | Missing classification `return Ok(())`; accept only on Windows and report not_found off Windows |
| readdir-missing-is-error | Missing readdir `continue` | Missing readdir `return Ok(())`; report not_found instead |
| first-rmdir-missing-is-error | Missing first rmdir at old indentation | Same missing branch in Directory; report not_found instead |
| final-rmdir-missing-is-error | `Work::FinalDirectory(p)` | `Work::FinalDirectory(p, _)`; report not_found instead |

The read-only audit's other literal anchors still matched. A further scope audit
found that N13's cached `validation` value is now in `remove()` but its replacement
classification expression is in `step()`. Merely retaining its old literals
would compile-fail, an INVALID control rather than a kill. That mutant now
threads the cached value into `step()` and reuses it for classification, retaining
its original wrong behavior. This argument exists only in the mutated scratch
source, never in production. N4 likewise retains the original *target* origin,
not an easier-to-detect immediate-parent variant.

`error-codes-negative-controls.py --tree <Rust workspace> --check-anchors` is a
read-only gate: it applies every registered mutation to in-memory source text,
including platform-inapplicable controls and helper mutations with several
anchors. Each exact replacement must match once and change the source. It exits
before log-directory creation, Cargo or source writes. The ordinary batch also
runs this check before any baseline or mutation. Both committed
`div008-windows-gates.py` and `div008-linux-gates.sh` run it before Cargo G3.
Static result: **27/27 mutations uniquely resolved**, on all-platform source.

The new Windows launcher captures native exits in regular files, uses the
project's shared four-job target, and runs both the full certified L12-D007
control batch and the four DIV-008 controls in a disposable copy. The Linux
recipe does the same, sequentially after G3 and uid-1000 corpora/probes; its
L12-D007 control copy is under private `/tmp/l12d007`. Control path proofs use
throwing no-follow lstat from the drive/root, reject reparse points and unknown
inspection errors, and check lexical and real containment before every write.

### Fresh remediation evidence at the frozen code head

Code: `b8c96b5f64b9e6dc82e407e0bf923a14f5cab0ce` (#219). Docs: #296,
the exact pushed head is recorded in the coordination handoff after this
evidence commit. The crates, canonical data and shared rules are byte-unchanged
from the rejected code head: only the control/gate scripts changed. Exact old
and new source-anchor literals are preserved in the code diff
`git diff 856cab3d b8c96b5 -- minion-agent-rust/scripts/error-codes-negative-controls.py`.

Claude explicitly granted the isolated #215 RR001 host window. Windows finished
before the Linux container started. Four Cargo jobs; project-local cache/target,
source/temp and logs only; private container tmpfs; no named volume or shared
target cleanup. The Windows preflight had 28.13 GB free, no active builds and
1218 GB free on E:. The Linux preflight had 28.11 GB free, no active builds and
1219 GB free on E:. Only the unrelated pgvector container remained after the
Linux batch exited. All native gate/control launchers exited **0**.

| Fresh gate | Windows | Linux |
| --- | --- | --- |
| Full `cargo test --workspace --all-features` | 678 passed / 0 failed / 0 ignored | 670 passed / 0 failed / 1 ignored |
| Native-fs package check, fmt, clippy, rustdoc, xtask | all exit 0 | all exit 0 |
| Focused real removal regressions | 12 passed | 10 passed |
| Static anchor precheck | 27/27 all-platform mutations resolved | 27/27 all-platform mutations resolved |
| Full L12-D007 intended-control batch | 26/26 KILLED; 26 selected/passing baselines | 14/14 KILLED; 14 selected/passing baselines |
| DIV-008 compiled controls | 4/4 KILLED | 4/4 KILLED |
| Restored baselines (both control runners) | green | green |

Windows-only correction/raw-handle/directory-link controls are explicitly
NOT_APPLICABLE on Linux. The child-vanishing Windows-only-gate regression is
explicitly NOT_APPLICABLE on Windows and **KILLED on Linux** by its real walk
witness. No setup, compile, unmatched anchor, wrong-witness or unexpected unfired-injection
failure was credited. The N6/N8/N11/N13 intended interruption allowances already
specified by L12-D007's certified driver are retained, not broadened.

Linux's ignored permission witness was explicitly run as uid 1000: **1/1 passed**.
The uid-1000 path-domain and read-only-removal corpora each passed **2/2**. The
fresh uid-1000 DIV-008 external probe executed **45 rows**: comparator v3
**19 MATCH + 26 DIV-008**, zero FAIL/INVALID; comparator self-test **23/23**;
real-row controls **15/15**. The unchanged Windows unit matrix and all 41
L12-D007 routing rows ran through the real seam again in the fresh suite and
focused run. The previously committed Windows external probe/comparator output
is preserved as historical evidence, not relabelled as a new external replay.

Fresh manifest validation: **8/8** on Windows with the real project-local config,
explicit root/cache/basetemp. An earlier optional invocation selected the
nonexistent `test_manifest_ids.py` and collected no tests (exit 4); it is INVALID
setup evidence and not a credit. Inspection identified the actual
`test_manifest_validation.py`; the corrected selection passed.

Reproduction: source `.agents/project-environment.ps1`, run the preflight,
make a fresh containment-proven disposable copy containing Rust/conformance and
the three fixture stores described above. Windows Python **3.12.8**:
`python scripts/div008-windows-gates.py --logs <fresh E: log directory>
--control-tree <project-local control-code/minion-agent-rust>`. The launcher
sets the pinned ICU/version/identity and captures each native return code.
Linux uses the same pinned image/environment and bind setup described above,
with the amended `scripts/div008-linux-gates.sh`; it copies the tree into private
tmpfs and runs controls under `/tmp/l12d007` and `/tmp/l12d008`, never in the
candidate checkout. Raw native logs, baseline/mutant assertion output and
comparator observations are committed under `data/l12-d008/rust-rr001/`.

RR001 remains an independent-review finding until Claude closes it at the new
exact pair. No provisional closure, self-certification or merge is claimed.
