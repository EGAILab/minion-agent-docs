# Layer 13 built-in tools — independent Rust-side scope review

Mode: independent scope review only. No Python or Rust implementation was authorized or
performed.

## Exact review target

```text
coordination issue: EGAILab/minion-agent#47
candidate PR:       EGAILab/minion-agent-docs#124
candidate SHA:      ee2e2403b1d905dcfcd2cd41d2108dfc4b428d9c
candidate base:     ec36ed92a9a57f5fc8db4f76103a2d202cb82cbc
code baseline:      92aa4be168dc82111832467922089206e858a9c4
pinned Pi:          b7bb00b936dbe21b8e160b3e89efdec361846699
```

The candidate head was fetched from `refs/pull/124/head`, matched the issue-recorded SHA, was
Ready for Review, open, unmerged, and remote-reachable. The issue assigned `NEXT_OWNER = Codex`
and explicitly stated that implementation was not authorized.

## Authority order and material inspected

The review used the required order: pinned Pi first; then the candidate scope artifact; then the
already-certified Layer 12 contract and Rust architecture. No Python built-in-tool implementation
exists and none was used as an oracle.

Pinned Pi source inspected at the exact pin included:

- `packages/coding-agent/src/core/tools/{index,bash,read,write,edit,edit-diff,find,grep,ls}.ts`;
- `packages/coding-agent/src/core/tools/{file-mutation-queue,truncate,path-utils}.ts`;
- `packages/coding-agent/src/utils/{paths,tools-manager}.ts`.

Existing certified Minion seams inspected included `spec/execution.md`, Python `FsTarget`/
`FileSystem.resolve()` as secondary architecture evidence, and Rust `FsTarget`, `TargetKey`,
`FileSystem::resolve()`, and `FileSystem::process_path()`.

## Source-grounded conclusions that are correct

The candidate correctly identifies the product-level inventory as `read`, `bash`, `edit`,
`write`, `grep`, `find`, and `ls`; correctly keeps concrete built-in tools separate from the
already-certified generic registry/execution framework; correctly assigns path/file/process
primitives to Layer 12; and correctly treats Layer 13 as a consumer of those seams.

The core edit characterization is accurate: all edits match the original content, any fuzzy
match moves the entire call into normalized matching space, uniqueness and non-overlap are
enforced, and only touched line ranges are rewritten while untouched lines retain their original
bytes. The mutation queue also really does serialize key derivation/registration globally, run
different keys concurrently, and release in `finally`.

No evidence requires reopening Layer 12. Its `FsTarget`, target-key, `process_path`, filesystem,
and subprocess surfaces are sufficient dependencies for a correct Layer 13 contract.

## Blocking findings

### L13-S001 — external search-engine acquisition is materially mischaracterized

**Classification:** `CONTRACT_ASSURANCE_DEFECT`

The candidate repeatedly states that Pi prefers a system `PATH` binary and otherwise downloads
the latest release, and therefore calls both engines simply unpinned/floating. Pinned
`tools-manager.ts` has a three-stage order:

1. an already-managed binary in Pi's own tools directory;
2. a system `PATH` binary (`fd`/`fdfind` or `rg`);
3. a download chosen at installation time.

Downloads normally query GitHub's latest release, but `fd` on Darwin x64 is explicitly forced to
version `10.3.0`. The overall conclusion remains that pinned Pi does not define one universal
`fd`/`rg` semantic version across all installations, but the acquisition matrix and the scope of
the floating behavior are not what the candidate says. This matters because the proposed owner
decision and acceptance-oracle options are built on that characterization.

**Minimal correction:** replace every “PATH first, else latest; both unpinned” statement with the
complete precedence/platform matrix. Re-evaluate the proposed engine strategy against that exact
matrix without pretending the Darwin x64 exception supplies a universal pin.

### L13-S002 — the Pi audit is explicitly incomplete and already contains observable mistakes

**Classification:** `CONTRACT_ASSURANCE_DEFECT`

The candidate admits that `grep.ts` and `ls.ts` were only partially read and that shell selection
was not audited, yet it proposes requirements and a work-package boundary for those surfaces.
That is insufficient for a scope approval whose requested gate includes Pi-audit completeness.

The incompleteness has already produced concrete errors:

- a successful image read still returns the image block at the tool-result boundary even when
  the current model is non-vision; Pi adds a note saying a later request projection will omit it.
  The candidate instead says the read tool returns the note *instead* and omits image content;
- `grep` does not pass a context-lines flag to `rg`. It collects match events, then rereads files
  and constructs context blocks itself. The exact behavior therefore belongs partly to Pi source,
  not wholly to delegated ripgrep behavior;
- the default `find` path delegates matching to `fd`, but the public definition also has a custom
  `FindOperations.glob` path. “Delegates all glob matching” is too broad unless expressly scoped
  to the default local implementation;
- `ls` has already-auditable observable rules omitted from the draft: case-insensitive
  `toLowerCase().localeCompare()` ordering, directory `/` suffixes, per-entry stat failures being
  skipped, and empty-directory text.

**Minimal correction:** complete the source audit before freezing scope: read all of `grep.ts`,
`ls.ts`, the shell-selection helpers used by `bash`, and the result-shaping helpers that are meant
to be contractual. Correct the image, grep-context, find-default/custom, and ls descriptions.
Then regenerate the requirement inventory from the completed behavior matrix rather than merely
adding prose patches around the current list.

### L13-S003 — the queue proposal preserves the key but not Pi's call-order guarantee

**Classification:** `CONTRACT_ASSURANCE_DEFECT`

Reusing Layer 12's `FsTarget.target_key` is directionally correct, but it is not sufficient.
Pinned Pi's global `registrationQueue` serializes *both* asynchronous key derivation and linking
the operation onto the per-key tail. That is what makes FIFO follow calls into
`withFileMutationQueue`, rather than filesystem-resolution completion order.

A Minion implementation could satisfy the current draft by calling `fs.resolve()` concurrently,
then entering a per-key queue after each resolve finishes. Two same-target calls could therefore
be enqueued in reverse call order even though both eventually use the correct `target_key`.
The draft's prose notices Pi's registration gate, but TOOL-010 and the proposed implementation
mapping do not bind the atomic ordering rule.

The scope also needs to state where queue ownership lives. A raw target-key value alone is not a
cross-provider namespace in Python, while Rust's full `FsTarget` includes provider identity but
its exposed `TargetKey` does not. A per-filesystem/provider queue or an explicitly provider-scoped
composite identity avoids unrelated providers accidentally serializing coincidentally identical
opaque key values.

**Minimal correction:** require the Layer 13 queue's reservation/registration critical section to
preserve call order across target resolution plus per-key tail insertion, while keeping execution
outside the global registration lock. Define queue ownership/provider scoping. Continue to consume
Layer 12 `resolve()`/`FsTarget`; do not duplicate canonicalization. This requires no Layer 12
semantic change.

### L13-S004 — the proposed work-package split couples unblocked tools to the blocking decision

**Classification:** `CONTRACT_ASSURANCE_DEFECT`

The proposed WP-13.1 combines `read`/`ls` with `find`/`grep`, while the same artifact says the
external-engine decision blocks `find`/`grep` implementation and calls it the highest-risk owner
decision. That prevents the unblocked `read`/`ls` surface from being independently certified and
contradicts the stated rationale that this package carries the lowest convergence risk and can
close first.

This does not meet the workflow definition of a work package as an independently certifiable,
coherent surface.

**Minimal correction:** either resolve the engine governance decision before approving the split,
or separate native filesystem query tools (`read`/`ls`) from delegated search tools
(`find`/`grep`). Keep `write`/`edit`/queue together and `bash` separate unless the completed audit
finds a stronger dependency.

### L13-S005 — the proposed requirement IDs collide with existing certified rows

**Classification:** `CONTRACT_ASSURANCE_DEFECT`

The parity manifest already contains certified `TOOL-001` through `TOOL-021`, plus `TOOL-023`
and `TOOL-024`. The candidate proposes new meanings for `TOOL-001` through `TOOL-015`. Calling
the list provisional does not make duplicate requirement identities safe: those identifiers
already refer to tool model, registry, execution, hook, and cancellation contracts.

**Minimal correction:** inventory the existing manifest namespace and allocate non-colliding IDs
(for example, a separately approved built-in-tool namespace or unused IDs after the current
range). Preserve every existing row and reference. Re-run uniqueness validation before presenting
the requirement set for approval.

## Work-package and requirement assessment

The dependency shape supports keeping mutation tools plus their queue together and keeping bash
separate. It does not support placing a governance-blocked delegated-search surface in the same
certification unit as native `read`/`ls` merely because all four are non-mutating.

The proposed requirement subjects are a useful first inventory, but the set cannot be approved
until the full source audit is complete and IDs no longer collide. The replacement set should
also account explicitly for the read image boundary, grep's Pi-owned context reconstruction, ls
ordering/skipping/formatting, default-vs-custom operations where observable, and the queue
registration atomicity rule.

## Layer 12 boundary

```text
Layer 12 boundary: CLEAR
Layer 12 reopen required: NO
```

Layer 13 can consume `FileSystem::resolve`/`FsTarget`, filesystem operations, execution-world
validation, and subprocess primitives. The missing queue rule belongs to Layer 13 coordination
around those operations, not to Layer 12.

## Formal verdict

```text
LAYER 13 SCOPE
    CHANGES REQUIRED

WORK-PACKAGE SPLIT
    CHANGES REQUIRED

REQUIREMENT SET
    CHANGES REQUIRED

LAYER-12 BOUNDARY
    CLEAR

IMPLEMENTATION AUTHORIZED
    NO
```

Required next action is targeted scoping remediation only. Complete and correct the Pi audit,
repair the engine-acquisition matrix, bind queue registration ordering/provider scope, revise the
work-package split, and allocate non-colliding requirement IDs. Do not implement Python or Rust
Layer 13 during that remediation.
