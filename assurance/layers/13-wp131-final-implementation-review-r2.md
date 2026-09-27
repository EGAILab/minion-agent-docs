# WP-13.1 final complete independent implementation review — round 2

**Verdict: APPROVED at the exact candidate pair below.** This is the separate complete review required by `agent-workflow.md` §11.8.8 after provisional closure of `L13-WP131-FR003`. It does not merge either PR, authorize Rust WP-13.1, or start Layer 14.

| Authority | Exact revision |
|---|---|
| Code PR [#60](https://github.com/EGAILab/minion-agent/pull/60) | `03012577cb9ab6ddb24d18111858a09068c0c304` |
| Docs PR [#162](https://github.com/EGAILab/minion-agent-docs/pull/162) | `ccaa37847fc71fc33f31700a9c46b14536d63897` |
| Pinned Pi | `b7bb00b936dbe21b8e160b3e89efdec361846699` |
| Prior rejected review | docs PR #168, `360603959f0a8f1fa5ab26d836ddfd2abab83acd` |

At review start both candidate PRs were open, ready, mergeable and remote-reachable at these heads. Issue #48 had `FINAL_CONTRACT_REVIEW`, `NEXT_OWNER: Codex`, an empty convergence finding list, and the same frozen pair. Review used detached exact-SHA worktrees and did not modify the candidates.

## Independent authority and whole-surface audit

I re-read pinned Pi `packages/coding-agent/src/core/tools/{read,ls,truncate,path-utils,utils/paths,utils/mime,utils/image-process,utils/image-resize-core}.ts` before evaluating implementation details. I compared those to the accepted `spec/tools.md`, `spec/execution.md`, manifest rows `TOOL-025/026/027/028/039/040`, the canonical schema/scenarios, certified Layer-12 `FileSystem`/`EXEC-007/008` seams, and then the Python production code and runner.

| Surface | Final result |
|---|---|
| `read` path, access and content | `R002-A` strict `file://` conversion before `ctx.fs`; path error projection and single readability checkpoint use the real certified filesystem seam. An absent `EXEC-008` capability takes the disclosed fallback without changing existing Layer-12 operations. |
| Text `read` | UTF-8 replacement decoding, offset/limit JavaScript-number behavior, first-line byte overflow, head truncation, continuation notices and `details` distinctions agree with the contract and discriminating canonical cases. |
| Image `read` | MIME sniff, EXIF/BMP/second decode, fast path and candidate search use the pinned Photon WASM. Typed `ImageBlock.data` contains decoded bytes, not base64 text (`FR002` closed). Model vision support changes only the note, not image attachment. |
| `ls` | Uses real `list_dir_raw` and `probe_dir_entry`: raw enumeration, pinned sort, lazy per-entry probes, per-entry error skip and cap check before the next probe. Directory symlinks, broken links, special entries and `not_supported` have distinct evidence. |
| Collation | `R006-C` uses PyICU 2.16.2, ICU4C 78.3, `en-001`, normalization ON and the approved stable lowercase-key sorting. The runtime rejects missing, foreign or unlisted loaded ICU libraries against the verified build identity. `FR003` remains closed, including Windows lookup failure/truncation and unreadable-instance fail-closed paths. |
| Errors and lifecycle | Stable Pi templates remain verbatim; raw/hybrid provider wording uses the owner-approved `R010-B` deterministic `FsErrorCode` projection. Generated details remain `{}`. Cancellation is a cooperative/raced operation, without altering Layer-09 signal authority. |
| Registration and runner | Real `ToolDefinition`/Layer-06 `execute_call` and real `ctx.fs` calls own semantics. The canonical adapter only builds fixtures, scripts provider responses, dispatches and compares; it does not implement `read`/`ls` logic. `TOOL-027` remains `NOT_ADOPTED_CORE`. |

The R005-A differential corpus contains valid PNG/JPEG/GIF/WebP/BMP, malformed sniff-positive/rejected inputs, boundary dimensions/sizes, EXIF orientations, BMP conversion success/failure, no-resize and resize paths, and candidate search. Committed authority/Python results and negative controls are in `assurance/layers/data/13-wp131-ce-l13-wp131-01/r005-a-photon-differential/`; the pinned candidate WASM hashes to SHA-256 `10468181565c56004c867f3a4af96f89a0ef5a63a72f2b5fb12c1f1992a3615c`. Controls reject visually equivalent alternate encoding, a changed WASM and a changed resize filter. R006-C differential evidence and the CE03 Windows/Linux identity controls were also checked. The later `mutants-ce03b.log` records 40/40 detected; the preceding targeted review independently ran the path-lookup negative control at this exact pair.

## Fresh gates

On Windows against code `03012577` with the pinned ICU identity and candidate source on `PYTHONPATH`:

| Gate | Result |
|---|---|
| Full `python -m pytest -q` (configured coverage) | Exit 0, 100.00% coverage (5,842 statements, 0 missed) |
| Full `python -m pytest -q --no-cov -o addopts=''` | 2,077 passed, 11 skipped, 19 expected failures |
| `ruff check .` | Clean |
| Configured `mypy` | Clean, 91 source files |
| Built-in canonical + schema + manifest tests | 305 passed; 46 collected in the built-in file (45 scenarios plus existence check), 259 schema/manifest tests |
| Manifest | 109 unique rows; relevant Layer-13 rows preserve the accepted dispositions |

An initial isolated canonical command lacked `PYTHONPATH` and failed collection; it was rerun with the configured environment and passed. This was a review-environment setup error, not a candidate failure. Existing lower-layer regressions ran as part of the full suite. No Rust implementation or lower-layer semantic edit is in the candidate.

## Findings and certification boundary

`L13-WP131-FR001`, `FR002`, and `FR003` remain **CLOSED**. No new `PI_PARITY_DEFECT`, `CONTRACT_ASSURANCE_DEFECT`, or `PI_BEHAVIOR_UNCERTAIN` was found. Accepted `R010-B` and `R006-C` deviations retain their explicit owner-governed intentional-divergence dispositions; neither is silently claimed as universal host-for-host Pi identity.

One nonblocking traceability nit remains: `TOOL-025`'s manifest rule retains the historical phrase “integration re-review pending” inside its review-history parenthetical. The same row opens `CONTRACT_INTEGRATED`, the accepted spec/issue provide the current state, and the phrase prescribes no conflicting behavior. It should be tidied in a later evidence/status sync, not by mutating this frozen candidate or reopening semantic review.

**Approval is limited to code `03012577cb9ab6ddb24d18111858a09068c0c304` and docs `ccaa37847fc71fc33f31700a9c46b14536d63897`.** The WP-13.1 Python/shared candidate is implementation-review approved. Merge remains a separate exact-SHA/owner-authorized action. Rust WP-13.1 is not implemented or authorized; Layer 14 is not started.
