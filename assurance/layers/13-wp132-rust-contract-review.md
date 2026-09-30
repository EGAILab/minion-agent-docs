# WP-13.2 independent Rust contract review — first candidate

**Verdict: CHANGES REQUIRED.** This is a contract review only; no Python or Rust implementation is approved by this record.

## Exact review target and authority

- Reviewer: Codex, independent Rust contract reviewer.
- Coordination: `EGAILab/minion-agent#49`, `CONTRACT_REVIEW`, `NEXT_OWNER = Codex` at review start.
- Code PR `EGAILab/minion-agent#81`: `0495df69dd977224da1c79012b9ea09f89c3769e` (open, ready, remote-reachable).
- Docs PR `EGAILab/minion-agent-docs#178`: `b8f899ad7a304bf8cfa2accd7cb9843190413b56` (open, ready, remote-reachable).
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`, verified in the local content-addressed checkout.
- Pinned dependency: `diff@8.0.4`; npm-reported integrity matches the contract's `sha512-DPi0FmjiSU5EvQV0++GFDOJ9ASQUVFh5kD+OzOnYdi7n3Wpm9hWWGfB/O2blfHcMVTL5WkQXSnRiK9makhrcnw==`. Node 22.15.1 reports ICU 76.1 / Unicode 16.0.
- Accepted defaults had advanced to code `main` `5ad1b9ed5734ae892b7e864133e982e9efe8b015` and docs `master` `57bc24933b820f15fc167e7c0cd4859768bc8e84`; the candidate heads remain the review target. The intervening `EXEC-009` additions do not overlap the candidate's changed docs file and add a distinct manifest row.

Read independently: Pi `write.ts`, `edit.ts`, `edit-diff.ts`, `file-mutation-queue.ts`, `path-utils.ts`, `utils/text.ts`; the pinned `diff` line tokenizer; the current frozen design and workflow; `spec/tools.md` and `spec/execution.md`; manifest rows `TOOL-026`, `TOOL-029`–`TOOL-033`, `TOOL-039`; the certified Rust `FileSystem` trait; owner decisions O1/O2 at issue #49 comment `5881558193`. Python was not used as the semantic oracle. `git diff --check` passed for both candidate diffs.

## Blocking findings

### L13-WP132-R001 — pre-registration asynchronous parent lookup can reverse write order

**Taxonomy:** `PI_PARITY_DEFECT` in the proposed contract. **Severity:** blocking.

Pi `write.ts:208-210` computes `absolutePath = resolveToCwd(path, cwd)` and `dir = dirname(absolutePath)` synchronously, then calls `withFileMutationQueue`. Pi `file-mutation-queue.ts:32-49` registers calls through one promise chain in the order they reach registration, serializing key derivation and tail-linking. The draft's `write` algorithm instead requires `dir = parent(fs.absolute_path(p))` *before* `with_mutation_queue(fs, p)`. Certified `FileSystem::absolute_path` is an async, fallible provider operation. A first write can therefore suspend there while a second write reaches and registers in the queue first, even when both address the same key. The draft simultaneously requires FIFO in call order; the two rules cannot both hold.

**Discriminating witness:** call write A and then write B for the same target. The provider delays only A's preliminary `absolute_path`, allows B's lookup to settle, and makes subsequent `canonical_path` calls return the same key. The draft permits B's write to finish before A's; pinned Pi registers A before B. A pre-aborted A can similarly be delayed or fail at this extra provider operation before reaching the mandated post-queue abort check. An `absolute_path` error at this preliminary site has no specified message projection in the error table.

**Minimal correction:** specify an ordering-preserving way to derive the parent without a reorderable pre-registration await, and define the extra lookup's failure/abort site if it remains. The witness must assert actual provider-call and write ordering, not just final queue contents. Do not repair this with runner-owned serialization.

### L13-WP132-R002 — `TOOL-026` is not a total shared pipeline for mutation tools as written

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`. **Severity:** blocking.

The certified `TOOL-026` pipeline in `spec/tools.md` steps 1–4 preprocess a path, but step 5 expressly dispatches the result to an “appropriate READ-ONLY ctx.fs operation” and lists only `read`/`ls` operations. The new `TOOL-026` manifest extension says `write` and `edit` use “this same pipeline,” while their algorithms treat `TOOL-026 pipeline(path)` as returning a path before their own operations. Applied literally, step 5 cannot serve a new-file `write` or an `edit` access stage. Applied as only steps 1–4, the phrase “same pipeline” excludes a certified step without saying so.

**Discriminating witness:** write a new path on a provider whose `check_readable` reports `not_found` but `create_dir`/`write_file` succeed. A five-step reading rejects; a preprocessing-only reading succeeds. Both can plausibly claim the current wording.

**Minimal correction:** factor/name the shared preprocessing steps 1–4 and make step 5 explicitly tool-specific. Keep the certified `read`/`ls` dispatch unchanged; specify that `write`/`edit` consume the shared preprocessed path without any read-only dispatch.

### L13-WP132-R003 — failed registration's temporary global blocking is misdescribed

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`. **Severity:** blocking because the proposed queue witness expects the wrong scheduler trace.

Pi `file-mutation-queue.ts:33-49` waits for each registration promise, including async `getMutationQueueKey`, before beginning the next registration. Its rejection handler allows progress *after* a failed registration settles. The draft correctly describes one global critical section, but also says a failed registration “never blocks ... any other call's registration,” and requests a witness that it is “neither blocking nor reordering others.” A slow key lookup that will ultimately fail **does temporarily block** a later registration; it simply leaves no persistent key entry and does not block it permanently.

**Discriminating witness:** A enters registration and its `canonical_path` remains pending before rejecting; B enters afterward for another key. Pi does not invoke B's key lookup until A's rejection settles. After that, B proceeds. A runner or implementation following the draft's “never blocks” wording could begin B early.

**Minimal correction:** distinguish temporary registration serialization from absence of a lingering per-key queue entry after failure. Make the canonical witness assert both halves.

## Row-by-row review and dependencies

| Row | Result at these SHAs |
| --- | --- |
| `TOOL-026` | **Blocked by R002.** The malformed-`file://` R002-A rejection and existing `read`/`ls` semantics otherwise remain intact. |
| `TOOL-029` | Definition, UTF-16 success count, UTF-8 encoding, mkdir/write/abort checkpoints and O1 failure wrappers trace to Pi or disclosed mapping. **Blocked by R001/R002.** |
| `TOOL-030` | `prepareEditArguments`, one combined access operation (`EXEC-009`), fallback disclosure, matching/diagnostics, and result construction are coherent with the inspected Pi source. **Blocked by R002** for path-pipeline ownership. `EXEC-009` remains a separate certification dependency. |
| `TOOL-031` | BOM, first-line-ending selection, LF normalization, per-call fuzzy mode, fuzzy-space occurrence count, line preservation, and Unicode/UTF-16 hazards are specified. The proposed ICU filtered-normalizer and diff corpus still require the promised differential evidence before implementation approval. |
| `TOOL-032` | Canonical path / `ENOENT` / `ENOTDIR` fallback, provider-scoped key, and global registration intent are appropriate. **Blocked by R001/R003.** |
| `TOOL-033` | Cooperative abort after awaited work and lock retention match Pi's intended boundary. **Blocked by R001** where the new prequeue await changes the abort/failure trace. |
| `TOOL-039` | O1's intentional divergence is cited and confined to `ctx.fs`-derived raw/hybrid text. Stable Pi templates and WP-13.1 certification are preserved. The preliminary `absolute_path` failure from R001 needs an explicit site if retained. |

The proposed algorithm authority corpus, canonical `builtin_tool` scenarios, and negative controls are **plans, not executed evidence**. No `builtin-write`/`builtin-edit` canonical scenario is present at the reviewed code SHA, and manifest `tests` fields explicitly say “to be generated.” This is accurately disclosed for a contract draft; it must not be counted as passing conformance or as implementation authorization. In particular, source-executed `diff@8.0.4` output, Unicode 16.0 normalization, Myers tie-breaks, queue interleavings, and negative controls remain future gates.

## Contract-quality and boundary judgment

- A Rust implementation can use typed `FileSystem`, `ToolRegistry` and Layer-06 seams without copying Python mechanics, once R001–R003 are corrected.
- The candidate does not itself introduce Layer-14 prompt/UI behavior or production implementation.
- O1 and O2 governance is traceable; no new owner decision is required for the narrow corrections above.
- The candidate branches should not be repaired by the reviewer. Any changed head requires a new exact-SHA review per workflow §11.3.

**Final verdict:** `CHANGES REQUIRED` / shared WP-13.2 contract **REJECTED at the exact SHAs above**. Rust WP-13.2: **NOT_IMPLEMENTED**. WP-13.2 cross-language: **NOT CLOSED**. Return the three narrow contract findings to the shared/Python owner; do not begin implementation.
