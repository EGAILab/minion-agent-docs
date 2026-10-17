# L13-D001 — WP-13.1 (`read`, `ls`) re-baseline on the current Layer-12 tree

Status: **SCOPING 1, PROPOSED** for independent scoping review. Coordination: `minion-agent#244`. Class: `delta`,
governing, CP-6. Requirements: `TOOL-025`, `TOOL-026`, `TOOL-028`, `TOOL-039`, `TOOL-040`.

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
