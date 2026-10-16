# L12-D013 Rust revalidation: provider entry-point contract block

Diagnostic code: minion-agent PR #240 at
`447b7dfaf9c75d625b644da87228273f908345ed`.

Status: **IMPLEMENTATION STOPPED — CONTRACT_ASSURANCE_DEFECT**.
Finding: **L12D013-RUST-C001**. This is an implementation discovery, not an
independent closure review or a new certification. Python's merged approval
remains history; Rust stays REVALIDATE_REQUIRED, cross-language NOT CLOSED.

## Entry and authority

Started from remote-reachable code main
`91a4ddef22ed707fc710da8b38588d404381d2a6` and docs master
`c311119cc82c3c2a59ae2f4074256422818ed9c0`, after checked #235 handoff
issuecomment-6218754488. Pinned Pi remains
`b7bb00b936dbe21b8e160b3e89efdec361846699`, `nodejs.ts:51-65`.
No Python implementation was used as the oracle.

The handoff's B.1 requires every CE01 N cell through Rust's real seams. CE01
section 2 says Rust reads in exactly Node's cells. However, approved
`12-l12-d012-convergence-ce02.md` section 2 explicitly requires preserving the
OS-path convenience provider adapter (`native_units` then
`without_extended_prefix`); only the lossless logical entry stays raw. D013
section 22.1 forbids adding or moving a read, and section 22.5 preserves the
existing successful resolver behavior outside the rooted correction.

Those entry points do not have the same read domain.

## Minimal discriminating witness

Windows, provider `\\?\C:\base`, caller `c:leaf`, inherited `=C:` absent:

| Entry point | Cwd-reader injection | Observation |
|---|---|---|
| Raw logical resolver, provider units unchanged | native error 2 | one read, error |
| `LocalFileSystem::new` with the same PathBuf spelling, real `absolute_path` | same native error 2 | zero reads, `Ok(c:\base\leaf)` |
| Ordinary `C:\base` provider, `c:leaf` | same injection | zero reads, `Ok(c:\base\leaf)` (paired no-read positive) |
| Complete UNC provider `\\srv\share\base`, `c:leaf` | same injection | one read, not_found (paired read positive) |

The existing Node capture `data/l12-d013/ce01/rd-1/node.out` already records
the raw extended-provider `c:leaf` row with **one read**, for both absent and
empty entry states. With successful injected cwd `E:\proc`, its value is
`c:\leaf`. No new Node run is claimed here.

The real Rust provider strips the extended prefix into `C:\base` before the
root scan; that supplies a complete matching-drive root. The lexical resolver
therefore stops before either inherited-entry selection or process-cwd read.
The raw logical entry parses `\\?\C:` as a different device, reaches the
drive selection and invokes the reader. This is a pre-existing adapter effect,
not the expected DIV-009 caller-path fix.

No real cwd/environment was changed; no witness path was accessed, created,
deleted or used as a child cwd. Injected errors are ordinary `io::Error`s.

## Reproduction and limits

The code companion is a **draft diagnostic only**, not a Rust certification
candidate. It adds an instance-owned native-read dependency, using the exact
old callbacks in production, and tests through the real LocalFileSystem seam.
It does not remove prefix mapping, add a cwd read, change selection or implement
the DIV-009 production fix. An unfinished local fix was withdrawn after the
contract conflict was confirmed, before any implementation candidate was
published.

From the companion `minion-agent-rust` directory, after sourcing the project
environment and preflight (jobs=4, existing pinned ICU):

```text
cargo test --locked -p minion-agent --lib execution::div009_tests -- --nocapture
cargo test --locked -p minion-agent --lib execution::div009_tests::extended_provider_read_domain_matches_the_checkpoint -- --exact --ignored --nocapture
```

The counterexample is explicitly ignored in ordinary test runs because it
asserts the disputed checkpoint expectation, not accepted behavior. It is
executed explicitly in the diagnostic window; its failure is evidence of the
block, never a claimed green suite or negative-control closure.

Diagnostic 1 stopped at compilation: two existing test initializers needed the
new injected field. No witness ran. After that setup correction, diagnostic 2
ran two tests: the initial caller-path fix witness passed; the extended-provider
checkpoint assertion failed, reporting `Ok(c:\base\leaf)`. The partial fix was
then removed. Diagnostic 3 formats and verifies the final diagnostic source:
two paired positives, then the explicit checkpoint counterexample. Logs and
their exact exits are retained in `data/l12-d013/rust-block/`.

Diagnostic 3 ran on 2026-10-17 02:51:01.659279–02:51:24.695279 +11:00:
formatter exit 0; paired positives exit 0 (2 passed, 1 deliberately ignored);
explicit contract assertion exit 101 (1 failed at its intended observation).
Every process exited and the #209 reservation was released. Diagnostic 2 ran
02:48:35.050748–02:49:43.482571 +11:00; diagnostic 1 ran
02:38:02.349704–02:39:06.586244 +11:00. The committed log copies normalize
line endings to LF and trim terminal blank lines; original captures remain
under `.tmp/codex-scratch/d013-rust-diagnostic-{1,2,3}`.

No Linux, canonical/native corpus, K1-K13, full Windows gates, or certification
is claimed. A linker LNK4098 warning appeared during these diagnostic test
builds; it is disclosed, not treated as a green clippy/doc gate.

## Required next action

Claude/shared-contract owner: reconcile the read-domain requirement by entry
point before further Rust production work. The narrow preservation route is
to inventory both raw logical and OS-path-adapted provider inputs, distinguish
the extended-provider cells, and state which matrix each seam must satisfy.
If instead the provider adapter is to change, that is an explicit shared
semantic decision with the appropriate reopen/approval and regressions, not
an incidental Rust fix or a runner workaround.

Do not silently erase the raw logical N row, strip a prefix at a native read,
or force an eager read at the provider seam. Preserve the ordinary/read paired
positives and the absent/empty entry distinction. Account separately for
successful values and read counts when qualifying the matrix.

This block does not request a reversal of DIV-009, does not reopen its Owner
decision, and does not close any Rust finding. #235's approved merged
`current_candidate` remains unchanged. The second-language work stops here
for a checked shared-contract response; no self-certification or merge.
