# Minion Agent — Rust Monorepo History Import

**Date:** 2026-08-21
**Status:** COMPLETE (2026-08-21). Verified against the actual `minion-agent` monorepo: source head
`041b9975b87a5a9e79180c4229cabee8a10d4bc5` is a reachable ancestor of `main`
(`git merge-base --is-ancestor` succeeds), no `minion-agent-rust/conformance/` directory exists in
the checked-out tree, and exactly one root `conformance/`/`pi-parity-manifest.yaml` pair exists.
Retained as the historical record of the executed migration strategy, not as a pending plan.
**Applies to:** `minion-agent-rust/` and `minion-agent/`

## Goal

Move the standalone Rust implementation into the shared code monorepo at
`minion-agent/minion-agent-rust/` while preserving its complete Git ancestry and aligning it with
the repository-ownership rules in `implementation-conformance-workflow.md`.

The resulting code repository is:

```text
minion-agent/
├── conformance/                 # single canonical suite
├── pi-parity-manifest.yaml      # single canonical manifest
├── minion-agent-python/
└── minion-agent-rust/
```

`minion-agent-docs/` remains a separate repository.

## Starting state

- Destination: `minion-agent`, branch `main`, currently rooted in the history-preserving Python
  import and subsequent shared-contract commits.
- Source: `minion-agent-rust`, branch `feat/rust-plan-1`, head
  `041b9975b87a5a9e79180c4229cabee8a10d4bc5`.
- The source has 19 commits and 51 tracked files.
- Both source and destination working trees must be clean before import.
- `minion-agent/minion-agent-rust/` does not yet exist.
- The source's vendored `conformance/` snapshot is obsolete. It differs from the newer canonical
  root suite and must not survive as a second active copy.

## History-import strategy

Use a non-squashed Git subtree import under the prefix `minion-agent-rust/`.

The import must retain the source commits as reachable ancestors with their original object IDs.
The monorepo receives an explicit join commit connecting its existing history to the Rust history.
No force-push, history rewrite of the destination branch, or squashed snapshot import is allowed.

The source repository's ownership warning is handled with a command-scoped `safe.directory`
setting or an intermediate Git bundle. Do not add an unnecessary global Git trust exception.

## Canonical-conformance consolidation

The imported current tree initially contains the historical Rust snapshot at:

```text
minion-agent-rust/conformance/
```

Remove that active copy in a follow-up integration commit. Historical commits may still contain
the snapshot because preserving history is intentional; the checked-out monorepo tree must have
only the root canonical suite.

Retire the obsolete snapshot model:

- remove `minion-agent-rust/conformance/SOURCE.json` and the nested scenario files;
- remove or replace `xtask conformance sync` behavior that copies from a sibling repository;
- update Rust conformance tooling/tests to resolve the monorepo root `conformance/` directly;
- ensure runners remain thin adapters over real Rust APIs;
- do not copy semantic behavior into `xtask` or test runners.

The root `pi-parity-manifest.yaml` remains the sole machine-readable parity manifest.

## Repository and build boundaries

`minion-agent-rust/` remains an independent nested Cargo workspace. The monorepo root does not gain
an artificial Cargo workspace merely to contain both implementations.

Rust commands run from `minion-agent/minion-agent-rust/`. Python continues to run from
`minion-agent/minion-agent-python/`. Both implementations consume the canonical files owned by the
monorepo root.

No semantic Phase 2+ implementation is introduced by this migration. Existing Rust Phase 1 code is
preserved subject to the frozen design and revised canonical runtime cases. Superseded Rust Phase
2+ plans remain superseded.

## Commit structure

Use two logical commits:

1. History-preserving non-squashed subtree import.
2. Monorepo integration: remove the private conformance snapshot and adapt Rust tooling/tests to the
   root canonical suite.

If Git's subtree machinery creates the first commit automatically, retain it as generated. Do not
combine the integration changes into a history rewrite.

## Verification

Before import:

- confirm source and destination are clean;
- record source branch, head, root commit, commit count, and tracked-file count;
- confirm the destination prefix is absent;
- create a recoverable source bundle or equivalent reference before joining histories.

After import:

- `git merge-base --is-ancestor 041b9975b87a5a9e79180c4229cabee8a10d4bc5 HEAD` succeeds;
- all 19 source commits remain reachable;
- source file history is inspectable through the subtree join;
- the checked-out tree contains no `minion-agent-rust/conformance/`;
- exactly one root `conformance/` and one root `pi-parity-manifest.yaml` exist;
- Rust tooling resolves the root suite without a sibling repository;
- Python's canonical-conformance paths remain valid;
- formatting, strict Clippy, full Rust tests, Rust documentation, layering, coverage when supported,
  and conformance verification are run from the new location;
- relevant Python contract/conformance checks are run to detect path regressions;
- the final monorepo worktree is clean after commits.

An outer test timeout may detect hangs; sleeps do not establish correctness.

## Recovery and source checkout

Do not delete or mutate the original standalone `minion-agent-rust/` checkout during the import. It
remains a recoverable backup until the project owner separately authorizes removal. The migration
is considered complete when the monorepo contains and verifies the imported history, not when the
old working directory is deleted.

## Rejected alternatives

### Rewrite with `git filter-repo`

This gives every historical commit the destination prefix, but rewrites all Rust commit IDs and the
tool is not currently installed. It provides less provenance than the non-squashed subtree import
for this repository.

### Squashed subtree or file copy

These preserve only a snapshot, not the requested Git history, and are therefore unacceptable.

### Retain vendored Rust conformance

This contradicts the normative ownership workflow and risks Python/Rust semantic forks. Only the
root suite may be active after migration.

## Completion condition

The migration is complete only when the Rust ancestry is reachable from the monorepo, the Rust
implementation builds and tests from `minion-agent/minion-agent-rust/`, and both implementations
consume the same root canonical contract without a private Rust snapshot.
