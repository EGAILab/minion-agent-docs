# L12-D012 — pre-fix Rust scoping characterization

This is observation evidence, not a correction, contract freeze, review approval or certification.
F001 and F002 stay OPEN. The affected Rust path surface and Windows Python surface stay
REVALIDATE_REQUIRED. No canonical expectation changes.

## 1. Remote sources and observer boundary

- Coordination: minion-agent#229, SCOPING / NEXT_OWNER Codex at the start of this pass.
- Reviewed scoping proposal: docs PR #304 at `6422f55842111bc09d9bac7574ea67e9b22568b6`.
- Certified main code: `f12d129eb00a18a82a90a18d980d0d2b14a80519`.
- Separately labelled, unmerged #224 draft: code PR #228 at
  `1790d36fd0f428bbdfb7528c6ab433d2b57a3942`.
- Authority: Pi `b7bb00b936dbe21b8e160b3e89efdec361846699`,
  `packages/agent/src/harness/env/nodejs.ts:51-65`, with native Node `v22.15.1`.
- Assurance branch starts from docs master `aa06a61b2a36685cf50edf5b1a39b320aa627cf0`.

Both Rust sources are fresh, separate detached worktrees. The only tracked instrumentation is a
three-line cfg(test) module registration in `execution/mod.rs`; the new module is the observer in
`data/l12-d012/rust-scoping/l12d012-observer.rs`. Neither resolver implementation is modified.
The draft variant changes only the observer's `DRAFT_ENTRY` to call the existing draft function.
The production crate's `forbid(unsafe_code)` stays in force.

The observer invokes the real `LocalFileSystem::absolute_path` provider method used by the fs
service, the existing logical `path::resolve`, and the existing scalar native
`filesystem::resolve_local_path`. It additionally invokes the draft `path::resolve_logical`,
labelled **draft_224**, not as certified behavior. This is lexical provider/resolver characterization,
not a complete tool-context or subprocess execution test. The paths are only strings; no colon
path is ever passed to an OS filesystem operation or used as a child cwd.

## 2. Inputs and native host-state partition

The baseline is all 23 inputs in #304's `scope-node.json`. The archived `matrix.json` was checked
for full parsed equality against that exact remote blob; it is source characterization, not new
canonical expectations. The provider cwd is `C:\x` on Windows and `/x` on Linux.

Windows adds all 32 classes of the approved partition: 16 selected-entry values on drives E and A.
These include absence, empty, matching absolute with either case/separator, drive-relative/short,
wrong-device absolute with each separator, wrong-device relative/short, plain relative, rooted with
each separator, UNC, and a single character. Node creates actual child environment blocks carrying
the `=E:` / `=A:` entry. Each Pi and Rust child is launched under the same environment and real cwd.
The Rust observer reads the hidden entries with the OS-backed `std::env::var_os`; the collector
requires exact equality to the Node child's observed entries before accepting any row.

Linux additionally observes `e:leaf` and `a:leaf` as ordinary POSIX spellings. Windows inherited
per-drive cwd is NOT_APPLICABLE there, not simulated or credited as 32 Linux host-state rows.

All outputs are explicit UTF-16 code-unit arrays. The collector compares each Rust seam to fresh
pinned-Pi results in its matching native child environment. It records mismatches instead of
asserting parity. Each observer test finishing successfully means collection completed, not that
its resolver conforms.

## 3. Results

Windows collected 23 baseline rows plus 32 host-state rows for each Rust source. The two sources'
existing seams have identical values on these inputs, while the draft lossless seam is reported
separately. See `windows-observations.json` for every input, oracle, observed value and comparison.

| Windows seam | Baseline matches | Controlled host-state matches |
|---|---:|---:|
| main absolute_path | 9/23 | 10/32 |
| main logical | 9/23 | 10/32 |
| main native scalar | 9/23 | 10/32 |
| draft absolute_path | 9/23 | 10/32 |
| draft logical | 9/23 | 10/32 |
| draft native scalar | 9/23 | 10/32 |
| draft lossless | 9/23 | 10/32 |

Equal totals do not imply equal matching sets: the native scalar seam agrees on some inputs where
the logical seam disagrees, and vice versa. The raw per-row arrays are the evidence.

Linux collected all 23 baseline rows and two ordinary drive-looking spellings per source.
See `linux-observations.json` for every result. Its previously certified main native scalar resolver
agrees on all baseline rows; the logical provider resolver does not. This bounds the correction:
POSIX scalar agreement is regression evidence, not a reason to change its behavior to mirror the
broken logical resolver.

| Linux seam | Baseline matches | Extra POSIX spellings |
|---|---:|---:|
| main absolute_path | 13/23 | 2/2 |
| main logical | 13/23 | 2/2 |
| main native scalar | 23/23 | 2/2 |
| draft absolute_path | 13/23 | 2/2 |
| draft logical | 13/23 | 2/2 |
| draft native scalar | 23/23 | 2/2 |
| draft lossless | 13/23 | 2/2 |

For example, `file:///C:/a%2Fb` remains a literal malformed-file-URL fallback. Windows Pi gives
`C:\x\file:\C:\a%2Fb`, while the main logical/provider resolver gives `C:\x\file:C:a%2Fb`
and the scalar resolver gives `C:a%2Fb`. Linux Pi gives `/x/file:/C:/a%2Fb`; the scalar resolver
matches, while the logical/provider resolver gives `/x/file:C:a%2Fb`. The draft lossless resolver
has the same logical defect. These are direct source-bound observations, not selected Python results.

## 4. Reproduction and containment

The archived observer and launchers reproduce the collection, using fresh worktrees at the two
exact code SHAs above. Windows uses Rust/Cargo 1.97.1, four Cargo jobs, the project environment,
ICU 78.3 library/identity, the project search artifacts and the shared Windows target. The script
installs only test instrumentation, refreshes workspace source mtimes, and builds one lib-test
executable per source. Preserve each executable before building the next source in the shared
target. The replay launcher now performs that copy itself; in this run the main executable was
preserved by a separate observer watcher before the draft build finished. This packaging change
does not change the observed Rust module or any production source.

Windows collection command (after the fresh observer builds):

```powershell
node --no-warnings .tmp/codex-scratch/l12d012-characterize.mjs run ref-repos/pi `
  review-worktrees/codex-l12d012-scoping-docs/assurance/layers/data/l12-d012/scoping/scope-node.json `
  .tmp/codex-scratch/l12d012-main-observer.exe .tmp/codex-scratch/l12d012-draft-observer.exe
```

Set the ICU bin64 directory on PATH for the Windows executables. Captured Windows stdout (the build
JSONL and observations) was transcoded to UTF-8 for the archive; the JSON code units are unchanged.
The evidence directory has `-text` attributes so its recorded bytes survive Git transport; the
whitespace check permits captured CRLF with `core.whitespace=blank-at-eol,space-before-tab,cr-at-eol`.
Windows executable SHA-256:
main `d9bd3f601939f7e499738259cff97d2e831121c57c0aa09abe413a89f3e37b00`,
draft `96e1be47663f83f1f9ae6c2859cbac82ceee3e0d550f542f91a9adc672bf578f`.

Linux uses the cached image
`sha256:b1b3c9c0d921d7fa0a6d1f9ec7e4eab87f8c8ec97644c3d791450f131dec813f`,
private `/tmp` tmpfs, E:-contained bind mounts, separate Linux cargo home/target, ICU 78 and Node
22.15.1. Both sources are copied with fresh mtimes into private tmpfs; no `cp -p` or `copy2`.
Builds and observations run sequentially as root in the private container (not uid-1000 evidence).
The launcher proves every resolved bind source immediately
before Docker. Python proves every copy, mkdir, chmod and log-write target lexically and through
no-follow ancestors before the operation. No cleanup, target cleaning, install or process killing.
No use of Claude's reviewer targets.

The host reservation was isolated after the Minion-Process batch ended. Preflight reported no active
builds, over 29 GB free memory and over 1 TB free E: space. Both Windows builds and both Linux builds
exited 0; both collectors exited 0. The Linux container exited and was removed before batch-done.
No full G3 gate is claimed or needed for
this pre-fix scoping collection. No mutation-control kill or finding closure is claimed.

## 5. Next boundary

Hand this pre-fix evidence to Claude for shared generation and independent case review. The shared
cases and cross-language feasibility matrix are not frozen yet. Rust correction comes only after
the agreed shared-case stage; #224 remains blocked by #229 for its final hand-back. There is no
runner workaround, no expectation substitution and no narrowed other-drive contract.
