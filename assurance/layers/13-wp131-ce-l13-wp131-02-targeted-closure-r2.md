# WP-13.1 CE-L13-WP131-02 — targeted closure review, round 2

Verdict: **L13-WP131-I001 and L13-WP131-C012 PROVISIONALLY CLOSED** at the exact candidate pair below. This is the mandatory §11.8.7 review, **not** final WP-13.1 approval, implementation certification, or merge authorization.

| Authority | Exact revision |
| --- | --- |
| Pinned Pi | `b7bb00b936dbe21b8e160b3e89efdec361846699` |
| Code PR #60 | `c2b9990fa9441567c337dd985bbabf0c0186ee11` |
| Docs PR #162 | `b9bd356f275a0e106d54ea94b2727497b580f5f2` |
| Certified EXEC-008 code baseline | `6dbec20a8e2a524f8c55ea9f137fe9edcfb9f960` |
| Certified EXEC-008 docs baseline | `e1d9b817096de2797df00b17f354c2ca1451629a` |
| Agreed convergence checkpoint, revision 6 | `8dff413867a4c10dc4de123c7c74acb9023d984e` |

Both candidate heads were fetched and verified equal to the open, ready, unmerged remote PR heads. This review used detached worktrees, leaving both candidate branches untouched. Authority order was pinned Pi (`packages/coding-agent/src/core/tools/read.ts`, `ls.ts`), the approved `spec/tools.md` and certified `spec/execution.md` §12, manifest and canonical scenarios, then the candidate implementation and assurance. Python implementation was evaluated against those authorities, not used as its own oracle.

## Finding closure

### L13-WP131-I001 — abort/settlement order

**PROVISIONALLY CLOSED @ code `c2b9990f` / docs `b9bd356f`.** The production `race_abort` settles the work against the signal at the work's completion point. If abort precedes settlement, `Operation aborted` wins even when work subsequently succeeds or fails; if work settled first, later abort does not rewrite it. The in-flight provider task is not forcibly cancelled. This covers both `read` and `ls`; no runner-owned abort ordering was introduced.

Permanent witnesses: `test_read_access_and_abort_order.py` W-I1, W-I2, W-I3 (success and failure), W-I4, plus the affected built-in canonical scenarios. Independent negative controls in a disposable worktree:

| Known-bad mutation | Expected and observed failure | Candidate pass |
| --- | --- | --- |
| Replace `_settle(work, signal)` with bare `work` in `race_abort` | W-I1 returned `hello`, W-I2 returned `a.txt`, and W-I3 returned `Cannot read` instead of `Operation aborted`: **3 failed, 1 passed** in the four-witness subset. | Four witnesses passed after restoration. |
| Recheck `signal.aborted` after an already-settled task (`if task.done() and not signal.aborted`) | W-I4 raised `Operation aborted` instead of retaining the settled result. | W-I4 passed after restoration. |

The W-I2 control was repeated with pinned PyICU 2.16.2 and ICU4C 78.3 loaded; thus its failure was not a missing-collation-dependency false positive.

### L13-WP131-C012 — read error-site provenance

**PROVISIONALLY CLOSED @ code `c2b9990f` / docs `b9bd356f`.** `check_readable` is called without signal. Its ordinary failure belongs to `Cannot access`; `not_supported` enters the explicitly disclosed G2 fallback. The common post-check abort checkpoint applies in both modes. The subsequent single `read_binary_file` call is also without signal: every normal-mode failure belongs to `Cannot read`, regardless of `FsErrorCode`; fallback classification retains the approved limited G2 rule. The read path does not consult `file_info`, `canonical_path`, or EXEC-007. `spec/execution.md` §12.5, `spec/tools.md`, manifest evidence and canonical expectations agree.

Permanent witnesses: W-G1..W-G16, including W-G15 for fallback checkpoint and W-G16 for no `file_info`/`canonical_path` dependency. Independent negative controls:

| Known-bad mutation | Expected and observed failure | Candidate pass |
| --- | --- | --- |
| Project a normal `read_binary_file` failure through fallback site classification | `read-after-access-not_found` produced `Cannot access` instead of expected `Cannot read`. | Canonical scenario passed after restoration. |
| Skip the common abort checkpoint in fallback mode | Direct scripted-provider probe observed extra `read_binary_file a.txt` and `absolute_path a.txt` after `check_readable a.txt`; candidate observed only `check_readable a.txt`. The canonical mutation also failed on Windows, although its failure was accompanied by a temporary-file lock during teardown; the direct probe establishes the semantic discrimination independently. | W-G15 canonical passed after restoration. |
| Insert `file_info` before read | W-G16 canonical failed on an unexpected `file_info a.txt` call. | W-G16 passed after restoration. |

All mutations were applied only to the disposable review worktree and restored; `git diff --ignore-space-at-eol` against both production files was empty afterward. The candidate's own `mutants-r6.log` records 32/32 detected controls; the table above is independent replay of the controls material to this targeted closure, not adoption of that self-report.

## Fresh targeted gates and scope

With the pinned ICU runtime available, the focused read/order and built-in canonical run completed **55 passed, 0 failed**. Schema/manifest validation completed **259 passed, 0 failed**. No full work-package release gate is claimed here: §11.8.8 requires freezing this exact candidate pair, running complete gates, and then a separate final independent review. The docs delta includes the certified EXEC-008 default-branch integration; that is a dependency, not a Layer-13 redesign.

No active blocker remains in this convergence episode at the reviewed pair. Prior checkpoint findings CE13-C005/C006 remain closed. No Rust WP-13.1 implementation, merge, or Layer 14 work is authorized by this verdict.
