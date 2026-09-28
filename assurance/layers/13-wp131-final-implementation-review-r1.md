# WP-13.1 — independent final complete review, round 1

**Verdict: CHANGES REQUIRED.** This is the mandatory §11.8.8 complete review after CE-L13-WP131-02 targeted closure, not a re-litigation of its provisionally closed I001/C012 witnesses. Approval is bound only to the exact remote heads below; neither candidate is approved for merge or Rust implementation.

| Item | Exact SHA / state |
| --- | --- |
| Code PR `EGAILab/minion-agent#60` | `c2b9990fa9441567c337dd985bbabf0c0186ee11`, open, ready, unmerged |
| Docs PR `EGAILab/minion-agent-docs#162` | `b9bd356f275a0e106d54ea94b2727497b580f5f2`, open, ready, unmerged |
| Pinned Pi | `b7bb00b936dbe21b8e160b3e89efdec361846699` |
| Accepted code `main` / docs `master` | `6dbec20a8e2a524f8c55ea9f137fe9edcfb9f960` / `e1d9b817096de2797df00b17f354c2ca1451629a` |
| Targeted closure | docs review PR #167 @ `ef986d0591a8a0fd3d6d2453b63996d624d66c1a`: I001/C012 provisionally closed |

Both PR refs were freshly fetched into clean detached review worktrees. Pi checkout was verified at the pinned SHA. I read Pi's `core/tools/read.ts`, `ls.ts`, `truncate.ts`, `utils/paths.ts`, and the image MIME/EXIF/process/resize source, then the approved spec, manifest, canonical schema/scenarios, certified Layer-12 capabilities, candidate code, and assurance. Python was implementation evidence, not semantic authority. The merged R005-A Photon evidence remains the accepted direct differential checkpoint; the candidate's vendored WASM SHA-256 independently equals `10468181565c56004c867f3a4af96f89a0ef5a63a72f2b5fb12c1f1992a3615c`, and pinned Pi's lock names `@silvia-odwyer/photon-node` 0.3.4.

## Whole-surface audit

| Surface | Result |
| --- | --- |
| `TOOL-025` typed `read`, text offsets/limits, truncation, Node UTF-8, model-visible result shapes | Candidate code/canonical tests conform to current `spec/tools.md`; **manifest conflict FR002 below**. |
| R005-A image sniff, EXIF, BMP conversion, resize/candidate ordering, Photon bytes | Source and canonical corpus align with the approved Photon mapping; pinned WASM integrity verified. |
| `TOOL-026` path preprocessing, strict R002-A malformed-URL rejection, provider routing | Code/spec align; **manifest conflict FR001 below**. |
| `TOOL-027` | Correctly not adopted as core behavior; no filename-fallback probing added. |
| `TOOL-028` raw enumeration, stable collation, lazy cap, symlink/OTHER/probe-error behavior, notices | Code and canonical evidence align with EXEC-007 and the approved algorithm; **runtime artifact-authority gap FR003 below**. |
| `TOOL-039` R010-B messages and read operation-site provenance | Current code/spec align. I001/C012 negative controls were independently replayed in targeted review #167; no regression observed here. |
| `TOOL-040` owner-selected R006-C | Comparator options, root lowercase and stable sort are present; the build-identity/fail-closed claim is not established by the implementation (FR003). |
| Canonical adapter and lower layers | 45 `builtin_tool` scenarios run through real tools, `LocalFileSystem` plus a scripted provider, and real Layer-06 `execute_call`; the runner parses/records/normalizes, not computes the result. No Rust files or Layer 14 work changed. |

## Fresh gates

On Windows/Python 3.13.5 with PyICU 2.16.2 and pinned ICU4C 78.3 loaded, from the exact code worktree:

- `python -m pytest -q -o addopts=''`: **2046 passed, 11 skipped, 19 xfailed**, 0 failed.
- `python -m pytest -q --cov --cov-report=term --cov-fail-under=100`: PASS, **5737/5737 measured statements, 100.00%**.
- `python -m ruff check .`: PASS.
- `python -m mypy`: PASS, **91 source files**. The disposable reviewer venv initially lacked the lockfile's `types-jsonschema`; after installing exactly `4.26.0.20260518`, mypy passed. That setup error is not a candidate finding.
- Schema/manifest validation: **259 passed**, 0 failed.
- No `TO_BE_FILLED` placeholder appears in the 45 built-in canonical scenarios.

Passing execution gates do not resolve the three blockers below.

## Blocking findings

### L13-WP131-FR001 — `CONTRACT_ASSURANCE_DEFECT` — stale `TOOL-026` operation list

`pi-parity-manifest.yaml`'s active `TOOL-026.rule` still instructs a Rust reader to pass the preprocessed path to `(read_text_file/read_binary_file/file_info/list_dir)` (around line 6712). The approved `spec/tools.md` step 5 (lines 608–612) instead requires `check_readable` then `read_binary_file` for `read`, and `probe_dir_entry`/`list_dir_raw` for `ls`. The candidate actually implements the latter. This is not merely historical narration: the stale list sits in the current rule of an adopted manifest row and offers a second, observably different lower-layer composition. **Minimal correction:** replace that list with the current approved operation sequence; do not change production behavior or the owner decisions.

### L13-WP131-FR002 — `CONTRACT_ASSURANCE_DEFECT` — image data domain contradiction

The same manifest's active `TOOL-025.rule` says image `data` is “base64-encoded text, not raw bytes” (around line 6638). Current `spec/tools.md` (around line 746, IMPL-C009) explicitly maps Pi's base64 string to the already-certified Layer-02 `ImageBlock` carrying **bytes**. The candidate `read.py` constructs `ImageBlock(data=base64.b64decode(...))`, and `llm/content.py` types `data: bytes | None`. Both descriptions can be made accurate only by naming their respective boundaries: Pi's serialized `ImageContent.data` is base64; Minion's typed `ImageBlock.data` is bytes. As written, an independent Rust implementation could follow the manifest and expose the wrong typed domain. **Minimal correction:** distinguish Pi wire representation from Minion's Layer-02 typed representation in `TOOL-025.rule`; retain current code/spec/canonical behavior.

### L13-WP131-FR003 — `CONTRACT_ASSURANCE_DEFECT` — ICU artifact identity not fail-closed

Owner-selected R006-C requires Python and Rust to use **one verified ICU4C 78.3 build**, rejecting linkage/loading of any other distribution ICU (`spec/tools.md` Collation; `TOOL-040.rule`, around lines 6888–6889). The Python build script verifies the *source tarball* and supplies preferred link paths, but does not verify which binaries the built extension actually linked or loaded. `collation.py` (lines 32–38, 76–97) checks only PyICU version and compiled/runtime ICU **version strings**. A different ICU build that also reports `78.3` passes all three checks. A disposable stand-in module reporting `PyICU=2.16.2`, compiled/runtime `ICU=78.3` but sorting `a,b` backwards was accepted by `pinned_collation()` and returned `[b,a]`; that is a negative control of the identity gate, **not** a claim that the reviewed host actually loaded a wrong ICU. The current host did load the pinned build and ordinary tests passed, but the explicit fail-closed invariant remains unenforced/unevidenced. **Minimal correction:** provide an implementation/build gate that verifies the actual linked and loaded ICU libraries are the single verified build (not merely version-equal), rejects a same-version foreign build, and records a discriminating negative control. Do not change the selected collation tuple or substitute a different engine.

## Disposition and next route

These findings do not reopen I001/C012 or invalidate their convergence witness matrix. FR001/FR002 are manifest consistency corrections; FR003 is an enforcement/evidence gap in the separately owner-settled R006-C build rule. Treat as §11.8.8 **Case A**: `FINAL_CONTRACT_REVIEW -> REMEDIATION -> targeted IMPLEMENTATION_REVIEW -> FINAL_CONTRACT_REVIEW`. Claude/shared-Python owner should make the narrow corrections and return changed exact remote SHA(s); Codex must independently review those SHAs. Preserve the previous review artifacts. No merge, Rust WP-13.1 implementation, or Layer 14 work is authorized by this rejected candidate.
