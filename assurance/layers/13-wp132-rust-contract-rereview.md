# WP-13.2 independent Rust contract re-review

**Verdict: APPROVED as a contract draft/checkpoint at the exact SHAs below.** This is a targeted re-review of `L13-WP132-R001`–`R003`, not Python or Rust implementation certification. The planned differential corpus and canonical witnesses remain gates before implementation authorization.

## Exact target and authority

- Coordination: `EGAILab/minion-agent#49`, `CONTRACT_REVIEW`, `NEXT_OWNER = Codex`.
- Code PR `#81`: `79e7e82f7e6ac2b14f62cd8a61db284feb24e50f` (open, ready, mergeable, remote-reachable).
- Docs PR `#178`: `03463945f5ea1fecb1e30c2ee4fa8178fa4c5d31` (open, ready, mergeable, remote-reachable).
- Earlier rejected target: code `0495df69dd977224da1c79012b9ea09f89c3769e`, docs `b8f899ad7a304bf8cfa2accd7cb9843190413b56`; rejection evidence: docs PR `#180` at `ee6cf21472a2cf6771abc0e02ef6d8ae4184322d`.
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`.
- Accepted defaults at re-review start: code `main` `ada1032644d3da701f4ad319a7d5e1402aafcf4d`, docs `master` `41374e7953fc4d1f8eab9bd879a186048b69c609`. These are not substituted for the PR heads being reviewed.

I re-read Pi `packages/coding-agent/src/core/tools/write.ts:208-233`, `edit.ts:330-366`, `file-mutation-queue.ts:5-64`, the candidate `spec/tools.md` path pipeline, mutation queue, write/edit algorithms and error table, and the candidate `TOOL-026` manifest row. The change from the rejected target touches only `spec/tools.md` and `pi-parity-manifest.yaml`; `git diff --check` passed. Python implementation was not used as the authority.

## Finding closure

| Finding | Result | Source and discriminating rule |
| --- | --- | --- |
| `L13-WP132-R001` | **CLOSED** | Pi synchronously computes `resolveToCwd` and `dirname` before calling `withFileMutationQueue`; there is no pre-registration await. The revised contract places Minion's extra async `fs.absolute_path` inside the mutation lock, after the first abort check, gives its fallible site the `Cannot resolve <path>: <cause>` projection, and requires a witness checking that B's key lookup and write cannot overtake delayed A. It also specifies the abort checkpoint after `create_dir`, matching the in-lock await boundary. |
| `L13-WP132-R002` | **CLOSED** | The revised `TOOL-026` rule explicitly separates shared preprocessing steps 1–4 from read/ls-specific step 5. Write/edit consume only the preprocessed path and never invoke read-only dispatch. A new-file write whose `check_readable` would fail is no longer ambiguous. Existing certified read/ls dispatch remains unchanged. |
| `L13-WP132-R003` | **CLOSED** | Pi's global `registrationQueue` awaits each registration, then uses both fulfillment and rejection handlers to let the chain progress. The revised contract states that a pending A temporarily delays B's key lookup even if A ultimately fails, but failure leaves no per-key entry. The required witness and two negative controls distinguish early B registration and lingering-entry defects. |

The adjacent zero-length range-witness correction now identifies the reachable empty-base case and does not change the approved edit algorithm. No new blocker arose from the changed text.

## Boundary and next gate

The draft remains independently implementable with certified typed Rust filesystem and tool seams; it does not prescribe Python control-flow mechanics or alter lower-layer semantics. `TOOL-029`–`TOOL-033` are **contracted, not implemented**. The proposed queue interleavings, `diff@8.0.4` and Unicode/ICU differential corpus, canonical `builtin_tool` scenarios, and their negative controls are still plans rather than executed evidence. They must be completed and independently reviewed before WP-13.2 implementation authorization. In particular, this re-review does not certify the candidate or approve Rust implementation.

**Final status:** `L13-WP132-R001`–`R003` closed at the exact candidate SHAs. Shared WP-13.2 contract draft **APPROVED FOR CHECKPOINT PROGRESSION**; Python WP-13.2 **NOT_IMPLEMENTED**; Rust WP-13.2 **NOT_IMPLEMENTED**; cross-language **NOT CLOSED**. Return to the shared/Python owner for the remaining contract-first evidence and ordinary workflow progression.
