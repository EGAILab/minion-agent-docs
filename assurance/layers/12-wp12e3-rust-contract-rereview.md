# WP-12.E3 / EXEC-009 — independent Rust contract re-review

Verdict: **APPROVED FOR PYTHON IMPLEMENTATION**, limited to the exact candidate pair below. Rust WP-12.E3 remains **NOT_IMPLEMENTED**; cross-language WP-12.E3 remains **NOT CLOSED**. This is contract review only, not implementation certification.

| Artifact | Exact reviewed remote head | Base |
|---|---|---|
| `minion-agent#80` | `46595472f5f35a7d56073883f5f7a4245f053f38` | `main` `8a359d0e085d4c3f03227648bbbfcd0c297ce9fb` |
| `minion-agent-docs#176` | `18c5e9da67118a44d56f1c2a4af056f071ac6b0b` | `master` `2f097fc60c20f61485f2cb32b1f59e628c8ccd84` |

Both PRs were fetched, remote-reachable, open, Ready for Review and mergeable; issue `minion-agent#79` was `CONTRACT_REVIEW / NEXT_OWNER: Codex` and named these heads. Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`. Prior rejected exact heads and review remain preserved in `assurance/layers/12-wp12e3-rust-contract-review.md` (review PR `minion-agent-docs#177` @ `04da3d63af32b51726dde4cf85ebd5aa4d3dbc4a`). Neither candidate changes production code or an existing certified Layer-12 operation.

## Finding closure

### WP12E3-C001 — CLOSED

The corrected §13.3 defines success solely by the **one combined access predicate**: POSIX `access(R_OK|W_OK)` or the specified Windows read-data+write-data open. It explicitly denies that success promises a later create, removal, read or write will succeed. The mode-0666 POSIX directory witness now distinguishes access success from failed child creation; a new Windows ACL witness distinguishes list+add-file from delete-child. §13.4 states the exact access bits and does not add a second probe. Manifest `EXEC-009.rule` agrees. This implements the Owner's C001 direction (`minion-agent#79` comment `5883362380`) without changing the owner-selected POSIX/Windows policy or EXEC-008.

### WP12E3-C002 — CLOSED; prior reviewer assertion withdrawn

I independently fetched the exact files through GitHub's contents API, not the candidate's prose:

| File | libuv `v1.49.2` blob | Node `v22.15.1` bundled blob | Verified access location |
|---|---|---|---|
| `src/unix/fs.c` | `239ecda16a7eb9b40453502cf0362ae66366cf72` | same | `uv__fs_work`: `X(ACCESS, access(req->path, req->flags))` at **1713**; `uv_fs_access` at 1792–1801 |
| `src/win/fs.c` | `f2215bb3082178193d37f8429536bfe7b707dd0d` | same | `fs__access` at **2272–2295**; `GetFileAttributesW` at 2273 |

Node 22.15.1 reports libuv 1.49.2. The candidate now records tag commits, blob IDs, symbols and exact lines in §13.4 and `EXEC-009.pi`. The first review's C002 claim that Unix line 1713 and Windows line 2272 pointed to unrelated operations was **factually wrong**; I withdraw it. That claim resulted from relying on a web-rendered source response that did not match the exact content-addressed blob. The direct GitHub blob/API check is decisive. This is an evidence correction, not a semantic dispute or a new Owner decision. The original review stays in history; this record is its explicit erratum.

## Contract result and gates

Pinned Pi `packages/coding-agent/src/core/tools/edit.ts` still supplies one default `fs.promises.access(path, R_OK|W_OK)` before `readFile`; the candidate preserves that POSIX operation. The Owner-approved Windows ACL-aware mapping remains an explicit intentional divergence. The new `ctx.fs` operation is typed and additive; absent-capability `not_supported`, path resolution, symlink following, error taxonomy, cancellation non-inspection, and the disclosed Layer-13 fallback remain coherent with certified EXEC-001–008. No canonical runner simulates this not-yet-implemented operation; §13.6 supplies predicted, discriminating language witnesses for implementation. `git diff --check` passed on both candidate diffs; the code candidate's manifest-validation suite passed **8/8**.

Active `PI_BEHAVIOR_UNCERTAIN`: none. Active `PI_PARITY_DEFECT`: none. Active `CONTRACT_ASSURANCE_DEFECT`: none. No additional governance decision is required for C001/C002.

The exact pair is **APPROVED FOR PYTHON IMPLEMENTATION** after routine exact-SHA contract merge authorization/integration under standing delegation `minion-agent#75`. A changed candidate head invalidates this approval. Claude owns that merge and the Python pass; Codex does not implement Rust in this review. WP-13.2 `edit` cannot claim final certification before EXEC-009 cross-language closes. Layer 14 remains NOT AUTHORIZED.
