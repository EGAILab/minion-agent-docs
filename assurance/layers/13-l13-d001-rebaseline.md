# L13-D001 — WP-13.1 (`read`, `ls`) re-baseline on the current Layer-12 tree

Status: **CONTRACT CANDIDATE 1** for independent contract review (§6). Scoping 1 was approved by Codex scoping
review 1 (`#244` issuecomment-6228470708). *(Earlier: SCOPING 1, PROPOSED for independent scoping review.)*
Coordination: `minion-agent#244`. Class: `delta`, governing, CP-6. Requirements: `TOOL-025`, `TOOL-026`, `TOOL-028`,
`TOOL-039`, `TOOL-040`.

This record is appended. The reviewed Layer-13 scoping records (`13-built-in-tools-scoping*.md`,
`13-built-in-tools-scope-final-closure.md`) and the certified WP-13.1 contract history stay unedited. Where they are
now stale, this record states the correction.

## 1. Baseline and authority

| Item | Value |
|---|---|
| Docs | master `2d29aeb45a8d01bb52371357d69cd3f6fc0add06` |
| Code | main `be07d20c4afcae909f5991759a2784f0a2297e75` |
| Pinned Pi | `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged) |
| Certified WP-13.1 | `minion-agent#48` CERTIFIED_CLOSED 2026-09-28: docs `74094467`, code `32fe82d2`; hardened by `#74` at docs `2f097fc6`, code `8a359d0e` |
| Governance | `#75` issuecomment-6222791583 item 5 (cut-over); Owner Q1/Q2 decision `#244` issuecomment-6228334676 |

**Baseline check.** The full read-only check is in
[`data/l13-d001/baseline-check.md`](data/l13-d001/baseline-check.md), also posted as `#244`
issuecomment-6227388888. It was run against docs `4dd294c0` and code `91a4ddef`. Between those refs and this
baseline:
- `spec/`, `conformance/` and `minion-agent-python/` are unchanged.
- The manifest changed only through the L12-D013 status sync (code #243). That sync sits above the TOOL rows and
  moves each of them down by 14 lines: TOOL-025 is now at 7477, TOOL-026 at 7569, TOOL-027 at 7628, TOOL-028 at
  7652, TOOL-039 at 8011 and TOOL-040 at 8081.
- Rust L12-D013 is merged (code #242 → `24dfe1ea`).

The citations below are at this record's baseline.

## 2. Premise

WP-13.1 is **not** a pending package. It was contracted, implemented and certified in both languages after the
Layer-13 scope closed. All four Layer-13 packages and both Layer-14 packages are closed.

So the question here is not whether WP-13.1 may start. It is whether certified WP-13.1 still holds on today's
lower layers, and which of its statements have gone stale. Neither binding's `read`/`ls` source changed after
certification except through Layer 05/06/12 domain deltas (baseline check §2.3). Every movement is inherited.

## 3. What changed underneath WP-13.1

Baseline check §2.2 classifies each post-certification change. The ones that matter here:

| Change | Effect on WP-13.1 |
|---|---|
| L12-D007 (`#199`), pinned Pi's literal error codes | **Invalidates** the `read` disclosures W-2/W-3 (`spec/tools.md:1571-1575`). On Windows, a readable directory now reads `Cannot read <path>: is a directory`, and a link loop is `unknown`. Both moved toward Pi. Python's binding test `test_read_access_and_abort_order.py::test_w_g11` was updated in `51e53ba`; no shared case pins the Windows outcome yet. |
| L12-D013 + DIV-009 (`#235`, CLOSED) | **Refines** targets and `<path>` text for rooted and UNC-root inputs on win32; both bindings now match Pi. DIV-009 makes `ctx.fs.absolute_path` fallible. That exposes a wording gap (§4, S13). |
| L12-D012 (`#229`, CLOSED) | **Refines** the targets for drive-relative and colon-bearing inputs on win32. A bare `file:` without `//` is not intercepted by TOOL-026 step 4 (`spec/tools.md:1123`), so it reaches the resolver. Pi's `normalizePath` also converts only `file://`, which makes this DIRECT_PI_PARITY, but no builtin case witnesses it. |
| L12-D001 (`#123`), JavaScript-string path domain; L12-D006 (`#194`), NUL paths | **Refines** the input domain and the NUL outcome at the tool boundary. Both are certified and witnessed in the Layer-12 corpora; WP-13.1 inherits them. |
| `#115` (EXEC-002-R1-PY-STR), Python `read_text_file` decoding | Makes the parenthetical at `spec/tools.md:1579-1581` historical. `read` still decodes `read_binary_file` itself. |
| Layer 05/06 domain deltas | **Refine** the argument domains at the tool boundary. The WP-13.1 section cites none of them. |

No change since certification touches `read`/`ls` semantics in a way that leaves either binding away from Pi.

## 4. Proposed delta (contract candidate after this scoping is agreed)

All of it is documentary or wording, plus witnesses. **No Python or Rust semantic change is proposed.**

1. **Status and dependency restatement**, in this record (S1–S7, S9, S11, S14 in baseline check §3):
   - the certified 5-row set, with TOOL-027 NOT_ADOPTED_CORE;
   - the two pinned engine dependencies: Photon 0.3.4 WASM (R005-A) and ICU4C 78.3 (R006-C);
   - the Layer-12 requirements WP-13.1 consumes: EXEC-002 §3.2 as amended by L12-D012/D013 and DIV-009,
     EXEC-007, EXEC-008, `read_binary_file`, `file_url_to_path`, §2.1 as corrected by L12-D007, the §14
     JavaScript-string domain and the §18 NUL boundary.
2. **Retire W-2/W-3** in `spec/tools.md` as closed by L12-D007. The text is appended, and the earlier wording is
   kept as history. Add one Windows-gated shared `builtin-read` case for a readable directory
   (`Cannot read <path>: is a directory`).
3. **S13 wording.** In `ls` step 2 (`spec/tools.md:1714-1717`), add "if that call itself fails, the step-5 string",
   mirroring `read` (`:1548-1549`). Classification: `CONTRACT_ASSURANCE_DEFECT`, behaviour-neutral. Both bindings
   already comply (`ls.py:53-54`, `ls.rs:42-44` at `be07d20c`). Add a binding witness in each language: an
   injected `absolute_path` failure, then `ls` answers `Path not found: <step-5 string>`.
4. **Bare `file:` witness.** One builtin case: a `file:`-prefixed path without `//` reaches the resolver unchanged.
5. **No-parity markers.** Each means: no parity claimed, Layer 13 inherits the current per-binding Layer-12
   behaviour, and no Layer-13 case uses the surface. A case that cannot avoid it is marked against its source.

   | Surface | Source | Where the marker goes |
   |---|---|---|
   | Home-directory source of `~` | `#236` (frozen) | TOOL-026 (its `pi:` cites the `~` branch, `disposition: adopted`), TOOL-025/028 resolution text, `spec/tools.md:1135-1139` |
   | Extended `\\?\` provider cwd (Rust) | `#241` (frozen) | TOOL-026, TOOL-028 (default `"."`), `spec/tools.md:1131-1139`, `:1714-1717` |
   | Relative or empty provider cwd | `spec/execution.md` §22.1 observation (`:3645`), §22.5; Owner Q1 | TOOL-026, `spec/tools.md:1131-1139` |
   | Windows exotic reparse entries | `#207`; Owner Q1 | TOOL-028 (`probe_dir_entry` kind: `/` suffix or skip) |
   | Non-Unicode native names in `ls` | `#133`-F2 (RECORDED); Owner Q2 | TOOL-028, TOOL-040 |

   Today no `builtin-read-*` or `builtin-ls-*` document, `fs-path-tools.json` or Python builtin test uses any of
   these surfaces (baseline check §4), so there is nothing to re-mark.
6. **Documentary sync (S12).** Update the `ls` status line `spec/tools.md:1678` ("CONTRACT_INTEGRATED, pending …")
   to certified. Make the newline parenthetical at `:1579-1581` historical. Correct the stale TOOL-026 tail in
   the manifest ("WP-13.2 … not yet certified"; WP-13.2 is CLOSED, `#49`).
7. **Revalidation run.** Evidence only, no expected behaviour change. Run the WP-13.1 canonical suites (50
   `builtin-read-*`/`builtin-ls-*` documents plus `fs-path-tools`, plus the new cases) and the binding tests, in
   both languages, at the exact candidate heads, on Windows and Linux. Windows runs go through Codex's host queue
   (`#209`). For Rust, the run also confirms that the L12-D001 tool changes (non-scalar paths accepted, no `"."`
   substitution) are on the certified tool paths.

**Not reopened:** any certified WP-13.1 rule; TOOL-027 NOT_ADOPTED_CORE; R002-A, R005-A, R006-C, R010-B, C012-A, G1;
any Layer-12 rule.

**Also noted, no action:** the L12-D004 record lists TOOL-025 as a downstream consumer of `canonical_path`
(`12-l12-d004-canonical-path.md:111`), but certified `read` never calls it (`spec/tools.md:1544-1545`; witness
`builtin-read-does-not-depend-on-file-info-or-canonical-path`).

## 5. Ownership, route and stop condition

| Item | Owner |
|---|---|
| Shared contract, manifest, canonical cases, Python witness | Claude |
| Rust witness for S13, and the Rust half of the revalidation run | Codex |

**Route.** Agreed scoping → contract candidate (docs and code, paired PRs) → independent contract review →
witnesses in both bindings → exact-head revalidation through `#209` → closure review → merge and status sync →
CLOSED.

**Feasibility.** The delta adds no new behaviour, so the feasibility rows are the five new witnesses, measured
against pinned Pi where Pi is the authority:
- the Windows directory read (Node `EISDIR` through Pi's read site);
- the bare `file:` input (Pi `normalizePath`);
- the two S13 binding witnesses;
- the marker texts, which are documentary.

**Stop.** This scoping stops at Codex's independent scoping review. Nothing is implemented before it is agreed.
Process rollout takes priority, and this work yields at the next safe boundary.

## 6. Contract candidate 1

**Review 1.** Codex scoping review 1 (`#244` issuecomment-6228470708) **APPROVED** scoping 1 at docs #319 `23eb3e54`
for bounded contract and witness drafting. It found no blocking finding and confirmed delta / governing / CP-6. It
required that:
- the S13 wording maps the existing fallback, with no early return, extra read or reordered call;
- the real-directory witness reaches the real content read, never an earlier access failure;
- the bare `file:` witness passes steps 1–4 without strict conversion and is paired with the malformed `file://`
  rejection;
- each S13 witness uses its binding's real `ls` seam, observes the preprocessed fallback and the following probe,
  and fails under a removed or wrong fallback;
- the L12-D001 JavaScript-string input domain stays distinct from `#133`-F2's native entry names.

**The pair.**
- **Code #245:** canonical cases, the manifest and the Python witness. The window evidence below is at `3fb6c9a1`.
- **Docs #319:** this record, the spec text and the evidence.
- No production source changed, and the `builtin_tool` schema is unchanged.

| Item | Where | What it pins |
|---|---|---|
| Real-directory read | `conformance/agent/builtin-read-real-directory-fails-the-read-as-is-a-directory.yaml` | an unscripted directory: `check_readable` passes, `read_binary_file` fails, giving `Cannot read <path>: is a directory`; call order check, read, absolute. It retires W-3 on every platform. |
| Bare `file:`, `read` | `conformance/agent/builtin-read-bare-file-colon-input-reaches-the-resolver-unconverted.yaml` | `file:missing` reaches `check_readable` as given, giving `Cannot access <abs>: no such file or directory`. The path is missing on purpose, because on NTFS `file:x` names an alternate data stream. |
| Bare `file:`, `ls` | `conformance/agent/builtin-ls-bare-file-colon-input-reaches-the-resolver-unconverted.yaml` | `absolute_path` then `probe_dir_entry` on `file:missing`, giving `Path not found: <abs>` |
| S13, Python | `minion-agent-python/tests/tools/builtin/test_tools.py::test_ls_falls_back_to_the_pipeline_path_when_absolute_path_fails` | a failing `absolute_path`, so `<path>` is the step-5 string (`@no such` becomes `no such`), with the probe after it on that string; a file input gives `Not a directory: a file`; the real `absolute_path` is the positive |
| S13, Rust | Codex, at the agreed contract stage | the same obligations through Rust's real `ls` seam |
| Manifest | `TOOL-025`, `026`, `028`, `039`, `040` | one appended L13-D001 paragraph and the new tests each; no existing rule or test changed (checked by `rows(old) ⊂ rows(new)` with every other row equal) |
| Spec | `spec/tools.md` WP-13.1 | the re-baseline subsection (inherited Layer 12 and the five-row no-parity table); W-2/W-3 retired; the newline parenthetical made historical; the `ls` status line; the `ls` step-2 fallback sentence. Earlier text is kept. |

**Windows evidence.** All three windows were granted by Codex under `#209`, run once each from Claude's worktree,
and used the ri001 venv's Python with the pinned ICU 78.3 runtime. The evidence is in
[`data/l13-d001/contract-1/`](data/l13-d001/contract-1/), with 98 files in its `SHA256SUMS` ledger.

| Window | Launcher | Code | Result |
|---|---|---|---|
| 1 | `l13-gates-1.py` rev 2 `6790c5ac` | `ed6c2ee3` | **Stopped at the gates.** ruff RUF001: literal U+202F in the S13 test, a candidate defect fixed in `3fb6c9a1`. mypy and pytest: launcher environment defects (mypy on a test file outside the configured gate; the ICU runtime not set, so 19 `ls` tests failed with `PinnedIcuError`). No control ran. |
| 2 | `l13-gates-2.py` rev 3 `4c410fb9` | `3fb6c9a1` | Gates as in window 3. **Refused closed** at the first control's copy: the CRLF working copy did not match the `\n` anchor. No control was credited, and a partial copy is kept. |
| 3 | `l13-gates-3.py` rev 4 `c9df005c` | `3fb6c9a1` | **Exit 0.** icu-load 0, project ruff 0, changed-file format 0, configured mypy 0, focused pytest 0 (junit 1041 tests, 0 failures, 0 errors, 0 skipped). **Controls 5/5 KILLED.** |

The project-wide `ruff format --check` exited 1 in windows 2 and 3. It reports the same **7 inherited files**,
none of them a candidate file. It is recorded as-is and is neither fixed nor credited.

**Controls (window 3).** Each control copies the bound source with a link-refusing walker and applies exactly one
mutation in the file's own line-ending form, with its import origin proven. It counts as KILLED only when all three
hold:
- its witness passes on the unmodified source;
- on the mutated copy, the witness fails with exactly 1 test, 1 failure, 0 errors and 0 skips, and its intended
  observable appears in the failure text;
- the witness passes again on the unmodified source.

| Control | Mutation | Witness | Observable |
|---|---|---|---|
| K1 | `ls` fallback = the caller's raw path | S13 | `Path not found: @no` |
| K2 | `ls` fallback = a fabricated `"/" + working` | S13 | `Path not found: /no such` |
| K3-read | step 4 converts any `file:` prefix | bare `file:` `read` case | `bare-file-colon: ` (the case's own assertion) |
| K3-ls | the same | bare `file:` `ls` case | `bare-file-colon: ` |
| K4 | Windows directory read raises `PermissionError` (W-3's old outcome) | real-directory case | `real-directory: text` |

**What this evidence is, and is not.** It is targeted Windows gate and control evidence for the contract candidate.
It is not an all-project green or a full G3 run. Linux, the full suites in both bindings and the Rust S13 witness
belong to the revalidation run (§4 item 7).

**Next.** Codex's independent contract review of the exact pair. After agreement come the Rust S13 witness, then
the revalidation through `#209`, then the closure review.

## 7. Rust test-only completion (Codex, 2026-10-18)

Code #245 now includes `d223ec10b7e79848fec6c3b69efcab9092fa0308`, based on the agreed `3fb6c9a1`.
Contract review 2 is `#244` issuecomment-6229086993. No production Rust/Python source, shared rule, canonical
expectation or schema changed. This is test-only completion, not independent closure or a merge request.

`builtin_tool_conformance.rs` adds an injectable `absolute_path` provider fault and three permanent S13 witnesses.
They invoke the public `create_ls_tool` through the real Layer-06 `execute_tool_calls` path:
- failed `absolute_path`, a preprocessed `@no\u{202f}such` input, `Path not found: no such`, then the exact
  `absolute_path no such` / `probe_dir_entry no such` trace;
- the same fault with a file-kind probe: `Not a directory: a file`, with the same preprocessing/order;
- successful real local `absolute_path`, then a scripted not-found probe: the diagnostic retains that absolute
  result, never the fallback.

Provider results are scripted at the existing filesystem seam; the new S13 witnesses do not mutate native files.
The existing canonical adapter remains thin and discovers all **53 documents / 166 cases** (the former 50 plus
the three agreed cases). The three independent binding witnesses are not included in that canonical case count.

**Fresh targeted Windows evidence.** The host window began at 2026-10-18 04:18:34 +11 after the absolute-path
project preflight (35.32 GiB free memory; no active builds; E: 1075 GiB free). Every child finished by 04:23:57;
the closing inventory found no cargo/rustc process. Jobs 4, pinned ICU78.3 and search artifacts, shared Windows
gate cache and disjoint Windows-controls cache; no cleanup, signals or gate retry. The initial formatting-only
command's relative preflight path failed; the absolute-path preflight passed before any compilation or gate.

The committed reproducible entry point is `minion-agent-rust/scripts/l13-d001-gates.py --logs <fresh path>`, after
the project environment/preflight and setting `MINION_CONTROL_CARGO_TARGET` to the disjoint controls target.
Captured logs/exits and `summary.json` are in [`data/l13-d001/rust-test-1/`](data/l13-d001/rust-test-1/), with a
SHA256 ledger. They correspond to the code bytes committed at `d223ec10`; no source content changed after testing.

| Step | Result |
|---|---|
| `cargo fmt --all -- --check` | exit0 |
| `cargo test --locked --offline -p minion-agent --features conformance --test builtin_tool_conformance -- --nocapture` | exit0, **5 passed**: the 3 new S13 witnesses, existing abort witness, and canonical test (53 documents /166 cases) |
| targeted `cargo clippy --locked --offline -p minion-agent --all-features --test builtin_tool_conformance -- -D warnings` | exit0 |
| control-cache unmutated S13 baseline | 3 passed,0 failed |
| K1: production fallback substituted with the caller's raw `path.clone()` in a contained copy | exit101, the two intended failure-path tests fail at `L13-S13: fallback message`, raw `@...` diagnostic observed; positive stays passing |
| K1 restored | 3 passed,0 failed |
| K2: fallback substituted with fabricated `"/" + working` | exit101, the same two intended tests fail at that assertion, `/no such` / `/a file` observed; positive stays passing |
| K2 restored | 3 passed,0 failed |

Both controls compile and execute; neither import/compile failures nor unrelated suite failures are credited.
Every gate/control refreshes workspace-source mtimes, and no mutant writes the gate cache. The test-link log has
the known MSVC LNK4098 warning; it is not claimed warning-free. Source copies, targets and logs are retained.

**Remaining gate boundary.** This is targeted development/discriminating-control evidence and the full WP-13.1
canonical slice on Windows, not full workspace G3 or Linux evidence. Exact-head Windows/Linux revalidation in both
bindings, shared schema/manifest validation, and independent closure review still precede merge/status sync/close.
The manifest's historical pending witness pointer is left for the coordinated post-closure documentary sync.
No new certification, finding closure, parity claim on frozen surfaces, or later-layer authorization is made.
