# L12-D008 Rust implementation — DIV-008

Status: implementation in progress; independent Rust closure review pending.
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

## Evidence under construction

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
remote candidate heads will be appended before the independent-review handoff.

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
