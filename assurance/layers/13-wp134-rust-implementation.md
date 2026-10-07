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

Full final Windows/Linux gates and the complete control batches are in progress.
The candidate is not yet handed off for independent closure. Final fresh counts,
exact heads, reproducible commands and control transcripts will be appended only
after those runs finish. Earlier green runs are not substituted for final gates.

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
