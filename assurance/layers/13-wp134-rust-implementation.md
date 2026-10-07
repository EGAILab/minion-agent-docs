# WP-13.4 — Rust implementation

Coordination: EGAILab/minion-agent#51. Implementation owner: Codex.
Independent closure owner: Claude. This record does not certify the candidate.

## Authority and scope

Accepted starting code: `01ec8339ba69fbac33e785f9692dad21cccbfbf9`.
Accepted starting docs: `26a4bbf87bf5401d3dd7955fe0d6a01a8490db65`.
Rust handoff: #51 comment 6038163683. Pinned Pi:
`b7bb00b936dbe21b8e160b3e89efdec361846699`, Node v22.15.1.
Normative authority: spec/tools.md WP-13.4, including CE-L13-WP134-01,
TOOL-036/037/038, DIV-002 and DIV-003. No Python, shared contract, canonical
expectation or dependency/lockfile changes are included.

## Implementation

- Typed factories consume the certified filesystem/subprocess/world/signal
  seams and the existing lossless prepared/result vocabularies.
- `SearchEngineStore` carries all four exact official artifact/member/binary
  pins. Tools resolve and hash the installed binary before every spawn,
  including the Pi-text diagnostic rerun. No implicit download or PATH fallback.
- Explicit provisioning verifies the artifact before extraction, extracts only
  the recorded member using the host archive utility (`tar`, provisioning only),
  verifies the extracted binary, stages inside the store, sets POSIX executable
  permissions and atomically renames. Valid installations are not rewritten.
  `UncertifiedSearchEngines` is an explicit selection, never a managed fallback.
- Windows full-path composition reads Pi's rewritten token stream, respects
  class and brace context and preserves non-recursive Pi scope. Engine-rejected
  generated patterns rerun Pi's text through a freshly verified binary.
- Streaming UTF-8 replacement/readline, match counting before collection,
  unmerged context windows and fractional numbers follow the wrapper contract.
  UTF-16 line cuts and lossless result text retain split surrogate pairs.
- Completion requires own exit plus both EOFs. Abort classification freezes
  before stream disposal and before joining a limit-stop acknowledgement.
  Find observes the early window; grep ignores pre-registration aborts.
- Logical path comparison and the `.git` walk retain UTF-16 until the native
  call. A logical lone surrogate is not equated with its U+FFFD OS projection.

## Permanent evidence

`tests/builtin_search_conformance.rs` runs the real managed engines through
the real Layer-06 execution and certified local providers. It constructs the
shared corpus, observes results and applies exact/multiset/sub-multiset/per-file
comparisons. Truncation content must equal the returned body. There is no search
implementation in the adapter. All 219 documents are enumerated: 218 apply on
each host, with the platform-specific documents jointly covering all 219.
`MINION_SEARCH_CASE` selects one document for an intended-witness control and
must run exactly one case (zero is an error).

Binding witnesses in `search_run.rs` cover the 14 abort cells, exit-before-EOF
and held limit-stop acknowledgement with event-driven synchronization. The
remaining search modules cover argv, unsorted output, duplicates, raw emptiness,
uncollected matches, diagnostic rerun verification, UTF-16 truncation, logical
path identity, store refusal/idempotence and publication only after staging.

`scripts/search-negative-controls.py` mutates only a disposable copy. Compiler
artifact events identify the exact executable; build/collection/setup failures
do not count. Each control runs its named permanent witness, requiring a semantic
assertion failure there. The Windows-only dangling-junction control is explicitly
not applicable on Linux.

## Gate state

Required Windows/Linux evidence is complete, as recorded below. This is a
review-ready implementation candidate, not author certification. Independent
closure remains required at the exact pushed code/docs heads recorded on #51.

## Neighborhood checks after the progress checkpoint

The actual find/grep factories now independently exercise all 14 abort partition
cells, in addition to the shared stream seam. The held limit-stop witness covers
three modes: no abort, an abort while the stop acknowledgement is held, and an
abort during subsequent stream disposal. Synchronization is event-driven; the
timeout is a deadlock safety guard, not an assertion sleep.

A Windows path-comparison check found that Rust 1.97.1's native Unicode lowercase
does not reproduce Node 22.15.1's Unicode 16 mappings (U+A7CE, U+A7D2 and U+16EA0
are discriminators). The implementation now uses an exhaustive pinned-Node
lowercase/property table and the contextual Final_Sigma rule, retaining unpaired
UTF-16 units. No ICU dependency or new runtime prerequisite is introduced.
`scripts/search-node-lower-table.mjs` checks Node/Unicode versions and regenerates
the exact bytes of `search_node_lower.json`:

```text
Node v22.15.1; Unicode 16.0
29228 bytes (LF-terminated committed artifact)
SHA-256 423cf36e0e4bd149e83993eb67fea7941bb781032fb00c783d2e8be4ce9cab7c
```

The discriminator also covers contextual sigma, U+0130 expansion and an unpaired
surrogate between cased characters. A native-Rust-lowercase control must fail
that permanent witness. This is implementation fidelity to the existing path
contract, not a shared semantic amendment.

The same path neighborhood check also confirmed Node's UNC distinction: paths
on two shares of the same server are relative (`..\\b\\x`), whereas paths on
different servers retain the absolute UNC target. The implementation and a
permanent discriminator now cover both. The `unc-share-forced-absolute` control
restores the rejected implementation rule and must fail that discriminator.

## Reproduction environment and commands

The final implementation/control head is code commit
`9ccae76ccaee833541508e61e66f7b6c263af8dc`, based on the accepted merged code
`01ec8339ba69fbac33e785f9692dad21cccbfbf9`. Rust is 1.97.1
(`8bab26f4f68e0e26f0bb7960be334d5b520ea452`), Cargo 1.97.1. Windows is x86-64
build 26200. Linux runs in `rust:1.97.1-bookworm`, repository digest
`rust@sha256:0e2bcaef56d041a486784e54104a81aebe0da44bd03019bd70bc0401e42e4a97`.
The Linux source tree is copied into the container filesystem; CR is stripped
from copied shell scripts. The previously verified ICU4C 78.3 environment is
used on both platforms. Host worktrees, targets, temporary directories and
transcripts are on E:. Linux compilation uses the existing isolated
`claude-l12r-build` volume, target `/build/target-wp134`.

From `minion-agent-rust`, with the pinned ICU bin/library/identity environment:

```sh
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace --all-features
RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps
cargo run -p xtask -- conformance verify
python scripts/search-negative-controls.py
```

The ICU library search path is also supplied to rustdoc on these hosts.
`MINION_SEARCH_ENGINE_ARTIFACTS` names the directory containing all four official
pinned archives. Each archive and extracted binary is verified by the candidate;
no previously installed executable or claimed result substitutes for this.
Shared manifest/scenario schema validation is separately run with:

```sh
python -m pytest -q -o addopts='' tests/conformance/test_manifest_validation.py tests/conformance/test_schema_validation.py
```

Fresh shared validation: **661 passed**. Fresh Linux Rust gates: **592 passed,
0 failed, 1 ignored** (including four doctests). The ignored pre-existing
permission-sensitive recursive-remove witness was explicitly run as UID 65534
against the same compiled candidate: **1 passed**. Formatting, strict clippy,
warning-strict rustdoc and conformance verification passed. All **43 applicable
controls were killed by their intended witnesses**, with four Windows-only
production-branch controls explicitly N/A. See
`data/13-wp134-rust/gates-linux.json` for the named witnesses and actual failure
diagnostics. Final Windows results are recorded below.

The pinned-Pi abort partition was freshly replayed, unchanged, on Node v22.15.1
on both platforms. All 14 outputs agree with the previously committed authority
and the actual Rust factory witness. The replay outputs are preserved beside
the gate transcript summaries. Pi HEAD was clean at
`b7bb00b936dbe21b8e160b3e89efdec361846699`; the Linux replay copied the same five
source files from that checkout (find, grep, truncate, path-utils, utils/paths),
not a rewritten implementation.

## Final Windows evidence and failed-attempt accounting

Windows: **589 unit/integration tests passed**, followed by **4 doctests passed**
(593 total, zero product failures). Formatting, strict clippy, warning-strict
rustdoc and `xtask conformance verify` passed. All **46 applicable controls were
killed by their intended witnesses**; the Linux-only production-branch control
is explicitly N/A. See `data/13-wp134-rust/gates-win32.json`.

The complete `cargo test --workspace --all-features` invocation passed every
unit/integration test but initially failed two doctests at link setup:
`LNK1181: cannot open input file 'icudt.lib'`. No test or production repair was
made. The pinned ICU native-library search path was supplied in `RUSTDOCFLAGS`,
and **all** workspace/all-feature doctests were rerun successfully. The reported
593 count includes that successful four-doctest run once, not the initial failed
attempt or the two compile-fail snippets from that attempt. RUSTDOCFLAGS must
contain the ICU search path for **cargo test**, as well as cargo doc, on Windows.
The observed MSVC `LNK4098` default-library warning is disclosed; test linking is
not claimed warning-free. Earlier parallel-build paging/linker failures and a
misconfigured control-launch attempt receive no gate credit.

One added control initially survived because its mutation targeted the
alternative-start branch while its selected scenario exercised separator-led
recursion. It was corrected to reinstate the actual rejected empty-alternative
rule at that branch. The intended existing canonical witness then failed.
The final complete batches were rerun on both hosts. Rust stdout/stderr capture
is explicitly UTF-8; the earlier Windows default decoding's mojibake diagnostics
are not the committed final transcripts.

The complete Rust source, tests, assets, manifest and Cargo inputs are identical
between the positive G3 source `a014176b64089131a754adbb55a3ff47bd7722ac`
and final `9ccae76ccaee833541508e61e66f7b6c263af8dc`. Their only difference is
the negative-control runner's corrected mutation anchor and diagnostic encoding.
The final 47-control batches use the latter head. Final formatting/clippy/doc/
conformance checks also passed at that head.

Canonical search: **218 applicable documents passed on each host**, all 219
inventory documents covered jointly. The platform-specific document is not
silently counted as executed on the other host. The real engines, result
comparison modes and comparator rejection controls run inside the full suite.

Status: Rust WP-13.4 **IMPLEMENTED / INDEPENDENT CLOSURE PENDING**. Python/shared
approval is the accepted baseline; this record does not recertify it or close
the cross-language work package. No subsequent work package is authorized here.

## Rust closure review 1 and R001 remediation (2026-10-08)

Claude's independent closure review of code `9ccae76ccaee833541508e61e66f7b6c263af8dc`
and docs `41697277b9b9c8538421c59df1c4f1f1653db558` is **CHANGES REQUIRED**:
[durable review](https://github.com/EGAILab/minion-agent/pull/154#issuecomment-6044281181).
That rejection remains history; the earlier implementation evidence is not an
approval. This remediation does not certify or merge the implementation.

**WP134-RUST-R001 — PI_PARITY_DEFECT, high.** The rule-5 diagnostic retry lost
find's abort listener: its first run completed the shared window and the retry
received no signal. Independently re-reading pinned Pi `find.ts` confirmed
`onAbort -> stopChild -> settle` and the close handler's signal check. Pi's
single diagnostic-producing run retains the listener until its own close.
The approved rule-5 composition and completion rule therefore retain the
window through the completion of the run whose outcome stands.

Trigger check: this is R001's first Rust independent review (A has not fired)
and has no Rust successor findings (B has not fired). The historical shared/
Python rejected-review threshold was already handled by CE-L13-WP134-01; that
episode remains settled. The reviewer and current handoff prescribe narrow
Rust mechanism remediation against the unchanged agreed contract, not a new
convergence semantic choice.

Remediation code: `ce89793f352901c187a6fe29cc5f6519b0894645`.
- `search_run::run_with_completion` decides synchronously at exit + both EOFs
  whether that outcome stands. `find` computes the existing retry predicate
  there. A retry keeps the **same** window active, without a close/reopen gap.
- Both runs receive the original signal. Checks before verification and after
  verification prevent another spawn when cancellation lands between runs.
- Find's outer race observes a latched abort as well as an active-window signal,
  so aborted completion settles without joining a held termination acknowledgement.
- When no retry follows, including the final diagnostic, the window still closes
  before stop-acknowledgement/stream cleanup. Grep uses the original always-final
  completion policy. No certified lower-layer seam or shared semantic rule changed.
- The synchronous line-collection mutex is not held across lower-layer awaits.

### Permanent discriminators and known-bad evidence

`search_tests.rs` uses scripted Windows engines on **both** hosts; both spawns
reject a corrected full-path pattern. The tests invoke the real find factory.

| Witness | Required observation |
|---|---|
| `diagnostic_rerun_abort_during_wait_settles_before_stop_ack` | Abort in the second wait returns `Operation aborted`; termination is observed while its acknowledgement is still held |
| `diagnostic_rerun_abort_between_runs_prevents_spawn` | Abort in the second engine verification returns `Operation aborted`; there is no second spawn |
| `diagnostic_rerun_without_abort_keeps_diagnostic` | No abort retains the exact Pi diagnostic and both spawns |
| `diagnostic_rerun_completion_excludes_disposal_abort` | A real signal fired during the final run's stream close is ignored; exact diagnostic retained |

Windows known-bad check: before production remediation, the permanent during-
and between-run abort witnesses were run with the **unchanged** rejected
`9ccae76c` production sources. Both failed their exact message assertion:
actual `error parsing glob: Pi diagnostic`, expected `Operation aborted`.
The no-abort control and pre-existing retry-verification test passed (2 failed,
2 passed). A no-abort control is deliberately green on both versions, not
claimed as a negative-control killer.

The first local mechanism fix exposed a second part of the same R001 surface:
the shared stream seam latched abort but completed the window while awaiting
the held termination acknowledgement, and the outer race considered only
`active`. The held-ack witness failed its deadlock safety timeout. Observing
the latched abort fixed this before the candidate gates; that failed attempt
gets no pass credit. Candidate focused retry evidence: all five tests passed.

Four additional controls in `scripts/search-negative-controls.py` restore:
first-run window closure; omission of the retry signal; omission of the
between-run abort checks; and ignoring the latched abort while stop acknowledgement
is held. Each runs only its named permanent witness. The last control's expected
failure is the named witness's bounded deadlock guard, not a setup failure.

### Neighborhood, environment and scope

The unchanged pinned-Pi partition was freshly executed and asserted equal to
`abort-partition-pi.json` on Windows and Linux: **14/14** each. The actual Rust
factory partition, exit+both-EOF seam, held-limit-stop modes, diagnostic
verification and no-abort/post-completion retry controls remain regression gates.
The R002 rewrite and R003 comparison modes/canonical corpus are unchanged.

The Linux invocation uses the previously recorded `rust:1.97.1-bookworm` image
and verified ICU volume, copies the checkout into `/work`, and strips CR from
the copied shell scripts. In particular, **both** compiler and rustdoc get the
native ICU library path, and Node v22.15.1 is on PATH:

```sh
export CARGO_HOME=/build/cargo-home CARGO_TARGET_DIR=/build/target-wp134
export RUST_ICU_MAJOR_VERSION_NUMBER=78
export RUSTFLAGS='-L native=/build/icu/lib'
export RUSTDOCFLAGS='-D warnings -L native=/build/icu/lib'
export LD_LIBRARY_PATH=/build/icu/lib
export MINION_AGENT_ICU_BIN=/build/icu/bin
export MINION_AGENT_ICU_IDENTITY=/build/icu-identity.txt
export MINION_SEARCH_ENGINE_ARTIFACTS=/artifacts
export PATH=/build/icu/bin:/usr/local/bin:$PATH
# /usr/local/bin/node is the pinned v22.15.1 Linux binary.
```

Fresh shared manifest/schema validation: **661 passed**. The permission-sensitive
Linux recursive-remove witness was independently run as UID 65534 against the
candidate-compiled binary: **1 passed**. Platform counts below are fresh at
code `ce89793f352901c187a6fe29cc5f6519b0894645`; deliberately RED mutation
runs are excluded from positive test totals.

Linux's complete G3 gates passed at the remediation source: **596 passed,
0 failed, 1 ignored**, plus the UID-65534 witness above. All **47 applicable
controls** were killed by their intended witnesses; four Windows-only production
branches are explicitly N/A. Afterward a disposable container copy's `find.rs`
and `search_run.rs` were replaced with a `git archive` export of rejected
`9ccae76c`, keeping the candidate's permanent tests. Exactly the two abort
assertions failed with the diagnostic instead of `Operation aborted`; the
no-abort, disposal and prior verification tests passed (**3 passed, 2 failed**).
That deliberately RED check is not part of the positive suite count. The
candidate worktree was never reverted or mutated by this replay. See
`data/13-wp134-rust/r001-gates-linux.json` for every named control and diagnostic.

Windows's complete G3 gates passed: **597 passed, 0 failed, 0 ignored**.
All **50 applicable controls** were killed by their intended witnesses; the
Linux-only production branch is explicitly N/A. Formatting, strict clippy,
warning-strict rustdoc and canonical verification passed on both platforms.
The unchanged search adapter covers 218 applicable documents per host and
219 jointly. See `data/13-wp134-rust/r001-gates-win32.json` for the named
controls and actual diagnostics. The existing MSVC LIBCMT linker warning
remains a disclosed environment warning, not a test failure.

**WP134-CON-R005 remains separate and pending.** Shared-owner docs PR #250 is not
approved at this pass's eligibility check. Non-local-world error text has not
been changed, and this candidate is offered for **R001 targeted closure only**.
R005 alignment must follow its own approved contract; full certification remains
blocked by the remaining findings. No Python, shared contract, canonical data,
engine pin or Rust manifest semantics were changed in this remediation.

## WP134-CON-R005 alignment (2026-10-08)

Shared-owner docs PR #250 was independently APPROVED at
`ed8216bc41059eb9a7146f687b99ae34542b64fd` and merged into master
`801d6eed2aec7742c038704d7e7e8c99eb9d415c`. The earlier R001 handoff's
pending status above is historical, not the current R005 disposition.
This branch merges the accepted master without modifying its contract.

Rust alignment source: `75e7408603194e41d6b43d13e79eb0f96b6e702c`.
`SearchEngineStore::resolve` rejects a non-local world before platform pin
selection or any binary verification/read. It renders the exact unavailable-
platform template with the world's identity and literal suffix. Local platform,
provisioning, hash verification and explicitly uncertified overrides are unchanged.
The only execution-world plumbing is a crate-private borrowed identity accessor;
opaque public Debug output and world compatibility remain unchanged.

The permanent `non_local_world_has_exact_text_without_store_consultation` test
checks fd and rg separately for exact text and zero verification calls. A
test-only per-store counter observes the real verification entry; a local lookup
then increments it, preventing a vacuous zero-count assertion. There is no
production counter, callback or alternate resolver authority.

Known-bad replay substitutes the exact rejected `ce89793f` production resolver
implementation into a disposable source copy, retaining the witness and its
test-only instrumentation. It must reach the intended exact-text assertion and
report the old `is not provisioned` result; compilation/setup failure is rejected.
Two permanent controls independently replace the non-local template with
provisioning wording and introduce a store verification/read before rejection.
Each must fail this named witness for its intended assertion. The existing
call-time provisioning control's anchor is updated to the unchanged local
verification branch; its semantic mutation and killing witness are unchanged.

R001's listener/retry implementation, DIV-002, comparison modes, canonical
corpus and pinned engine artifacts are untouched. R001's independent review
continues at the earlier detached pair, not implicitly at this successor.
The first text control was too broad: its source replacement also changed the
witness's expected literal, and it survived. No kill was credited. A control-only
commit `e52fe98a7e627b75cd196149e994f6881978df2a` restricts that replacement to
the production return expression. All Rust crate sources and Cargo.lock are
byte-identical to `75e74086`; the full control batch was rerun, not just the
new control. Author alignment is not independent closure.

Linux positive gates: **597 passed, 0 failed, 1 root-only ignored**, plus the
ignored recursive-remove permission witness independently **1 passed** as UID
65534. Formatting, strict clippy, warning-strict rustdoc and canonical verification
passed with the same pinned ICU/Node/container recipe above. All **49 applicable
controls** were killed, **4 Windows-only N/A**. The exact `ce89793f` resolver
substituted into a disposable copy failed the intended message assertion with
`is not provisioned` instead of the certified non-local text. The candidate
itself was not modified by controls or the known-bad replay. Fresh shared
manifest/schema validation: **661 passed**. Full named control diagnostics are
in `data/13-wp134-rust/r005-gates-linux.json`.

Windows clean G3 gates passed: **598 passed, 0 failed, 0 ignored**; formatting,
strict clippy, warning-strict rustdoc and canonical verification passed. All
**52 applicable controls** were killed, **1 Linux-only N/A**. The exact old
`ce89793f` resolver failed the intended exact-text assertion on Windows too.
See `data/13-wp134-rust/r005-gates-win32.json` for every named control and actual
diagnostic. All evidence is at `e52fe98a7e627b75cd196149e994f6881978df2a` (the
Linux positive crate sources are byte-identical as disclosed above).

Initial
attempts shared `.tmp/claude-rust-target` with the parallel detached review:
two links failed with LNK1104 while that review ran the same executables, and
another search-conformance run observed the exact `context-bom-dropped` mutant
behavior despite unchanged candidate grep source. These are not credited as
positive evidence or treated as a product fix. Verification was moved to a
dedicated E: `.tmp/wp134-r005-target`, with only copied dependency caches and
freshly built test executables. The first isolated run repeated the BOM control
because the cache seed had also imported Minion's own library/fingerprints.
`cargo clean -p minion-agent` in the task-only target removed 20.8 GiB of
reproducible outputs; rebuilding the unchanged source then passed the exact
BOM case. Thus no product BOM change was made. All positive gates and the
full controls are rerun from that clean package build. No reviewer processes
or files were modified, and no source/history was deleted. None of the
contaminated runs is credited as passing evidence.

For reproducibility, use the Windows environment recorded above, but set
`CARGO_TARGET_DIR=E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.tmp/wp134-r005-target`.
Use an exclusive target, and clean Minion's own package before a positive run
if that cache has seen mutation tests; imported crate fingerprints can otherwise
reuse an earlier mutant. Commands are the full fmt/clippy/test/doc/xtask gates,
then `python scripts/search-negative-controls.py` (all 53 entries). The known-bad
check keeps the new test-only counter and substitutes only the old production
`impl SearchEngines for SearchEngineStore`, not a proxy of its behavior.
The unchanged adapter passes 218 applicable search documents per host, 219
jointly. Existing manifest Rust pointers already identify this source/test file,
control script and assurance record; no manifest rule/disposition update is needed.

This candidate is ready for independent **R005 targeted closure**. R001 is already
closed by Claude at the earlier detached pair according to issue #51; its
implementation is unchanged here. Author does not self-close R005, certify or
merge WP-13.4. No Python or unapproved shared semantics were changed.
