# WP-12.E3 / EXEC-009 — independent Rust contract review

Verdict: **REJECTED** for this exact contract candidate; no Python or Rust implementation is authorized by this review.

| Artifact | Exact reviewed remote head | Base |
|---|---|---|
| `minion-agent#80` | `08907afd51648fb9d08dbac44499a7efaa1ae1a2` | `main` `8a359d0e085d4c3f03227648bbbfcd0c297ce9fb` |
| `minion-agent-docs#176` | `9f30cb91ef898fc7d207cf1be1780fbbfbf417a3` | `master` `2f097fc60c20f61485f2cb32b1f59e628c8ccd84` |

Both PRs were open, Ready for Review, mergeable, and remote-reachable at review start. Issue `minion-agent#79` was open at `CONTRACT_REVIEW / NEXT_OWNER: Codex`, with these exact SHAs, the owner decision `minion-agent#49` comment `5881558193`, and no quarantine flag. The main local worktrees contained unrelated untracked material and were left untouched. Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`.

## Authority and architecture audit

Read pinned `packages/coding-agent/src/core/tools/edit.ts` (`EditOperations.access`, `defaultEditOperations.access`, and the access-before-read call at lines 347–356), Node 22.15.1/libuv 1.49.2 `uv_fs_access`/`fs__access`, the owner decision, accepted `spec/execution.md` §§2–3 and 12, candidate §13, manifest `EXEC-009`, and the existing certified Python/Rust `check_readable` provider seams. The candidate is additive and correctly distinguishes a single combined access decision from sequential read and write probes. Its POSIX `access(R_OK|W_OK)`, Windows ACL-aware divergence, not-supported capability response, no-content rule, cancellation non-inspection, and Layer-13 fallback architecture are broadly coherent. No production code or canonical scenarios changed in these two PRs; `git diff --check` passed.

## Blocking findings

### WP12E3-C001 — `CONTRACT_ASSURANCE_DEFECT`: directory success has incompatible definitions

**Affected:** candidate `spec/execution.md` §13.3 (the directory `read+write accessible` definition), §13.4 (the exact Windows access mask), §13.6 (the read+write-but-not-search witness), and manifest `EXEC-009.rule`.

The contract says `Ok(None)` on a directory means the caller may list it **and create or remove entries**. The same paragraph correctly requires `Ok(None)` for a POSIX directory with mode `0666`, no search permission, because `access(R_OK|W_OK)` succeeds. But that caller cannot create or remove an entry by pathname without search permission. I reproduced the distinction as a non-root user in disposable `node:22.15.1-alpine`: a mode-0666 directory passed read/write access tests, while creating `directory/child` returned `Permission denied`. Pinned Pi specifies the access call, not a guarantee that a later mutation can succeed.

The Windows half has the same overclaim: the mandated single `CreateFileW(FILE_READ_DATA|FILE_WRITE_DATA, ...)` checks `FILE_LIST_DIRECTORY|FILE_ADD_FILE` for directories. `FILE_DELETE_CHILD` is a different right (`0x40`), not requested. [Microsoft's file-access-rights table](https://learn.microsoft.com/en-us/windows/win32/fileio/file-access-rights-constants) explicitly separates these rights. A directory granting list+add-file but denying delete-child can pass the specified probe without granting removal. Thus one conforming implementation could follow the exact syscall/mask while another follows the prose's stronger removal guarantee and return a different result. The witness is observational at the public `check_read_write` boundary.

**Minimal correction:** make the exact combined access predicate authoritative. State explicitly that `Ok(None)` on a directory is **not** a promise that a later create/removal operation succeeds. For Windows, name the rights actually checked (list + add-file), not delete-child; do not add a second probe or broaden the access mask merely to satisfy the overclaim. Align `EXEC-009.rule` and the directory witness prose. This does not change the approved owner decision or certified lower-layer behavior.

### WP12E3-C002 — `CONTRACT_ASSURANCE_DEFECT`: source-line citations do not identify the cited libuv operations

**Affected:** candidate `spec/execution.md` §13.4 and `EXEC-009.pi`.

The candidate cites libuv 1.49.2 `src/unix/fs.c:1713` for `access(2)` and `src/win/fs.c:2272` for `fs__access`. In the exact tagged [Unix source](https://github.com/libuv/libuv/blob/v1.49.2/src/unix/fs.c#L1696), `uv_fs_access` starts at line 1696 and dispatches to `access(req->path, req->flags)` at line 1619; line 1713 belongs to `uv_fs_chmod`. In the exact tagged [Windows source](https://github.com/libuv/libuv/blob/v1.49.2/src/win/fs.c#L2119), `fs__access` starts at line 2119 and uses `GetFileAttributesW`; line 2272 is in the time-update implementation. The source behavior described by the contract is correct, but its precise evidence pointers are false.

**Minimal correction:** replace the stale line numbers in both current normative locations with verified tagged symbol/line citations (or symbol-anchored references that do not claim those wrong lines). No semantic redesign is needed.

## Gate and disposition

These are narrow contract/evidence defects, not a request to modify either implementation or to reopen EXEC-008. The owner-approved Windows divergence remains valid. Candidate heads must change for remediation, so this verdict cannot be reused as approval of later SHAs. Neither finding is a Pi-behavior uncertainty: the pinned edit source, exact libuv implementation, and documented Windows access-right bitmasks resolve the relevant behavior.

Required handoff: `minion-agent#79` → `CONTRACT_DRAFT / NEXT_OWNER: Claude` for the two corrections only, then a new exact-SHA independent review. `WP-13.2` remains contract draft and cannot claim final edit certification before EXEC-009 closes. No Layer-12 implementation, WP-13.2 implementation, or Layer 14 work was performed.
