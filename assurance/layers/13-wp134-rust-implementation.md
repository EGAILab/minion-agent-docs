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
