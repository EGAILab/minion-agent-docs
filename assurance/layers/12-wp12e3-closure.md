# WP-12.E3 / EXEC-009 — cross-language closure

**Status:**
- `EXEC-009`: CERTIFIED in both languages.
- `WP-12.E3`: CERTIFIED_CLOSED (`minion-agent#79`).

**Governance source:**

```text
GOVERNANCE_SOURCE
    standing_delegation: minion-agent#75
    delegated_decision: this record and the #79 closure comment (Claude, under #75)
    scope: WP-12.E3 / EXEC-009 merges #185, #84, #83, #184; CERTIFIED_CLOSED declaration; #79 closure
```

The work package itself was authorized by owner decision `L13-WP132-O2` (`minion-agent#49` comment `5881558193`).

## Accepted artifacts

| Artifact | PR | Exact head | Merge |
|---|---|---|---|
| Contract, `spec/execution.md` §13 | docs #176 | — | `f70a7149` |
| Contract manifest row | code #80 | — | `5ad1b9ed` |
| Contract review records | docs #177, #179 | — | `37e49374`, `57bc2493` |
| Python implementation | code #82 | `7438caab` | main `ada10326` |
| Python assurance and review | docs #181, #182 | — | `2ce54bd8`, `41374e79` |
| §13.4 sharing-violation correction (`WP12E3-R001`) | docs #185 | `0245ea2a` | `afdf0865` |
| Python sharing witness | code #84 | `dc2b06d8` | main `266d17f5` |
| Rust implementation | code #83 | `6b4222d1` | main `8a2a3948` |
| Rust assurance | docs #184 | `4b1b4d5b` | master `6bbfccf6` |

## Review trail

**Contract.**
- Codex review 1 rejected the contract with two findings:
  - `C001` (directory Ok overclaimed create/remove): accepted and corrected;
  - `C002` (libuv citations): disputed with content-addressed evidence and withdrawn.
- The re-review approved it.

**Python.**
- Codex's implementation review approved it at `7438caab`.

**Rust** (Claude's reviews of #83):

| Review | Head | Verdict | Details |
|---|---|---|---|
| 1 | `309737a0` | CHANGES_REQUIRED | Missing witness for the new §13.6 sharing-violation row. Review 1 also found `WP12E3-R001` in the shared contract: §13.4 had called a Windows sharing conflict `permission_denied`, but pinned libuv maps it to `EBUSY`, which is §2.1's `unknown`. The fix was docs #185 plus Python witness #84, both approved Rust-side by Codex. |
| 2 | `0b234fdb` | witness accepted; `WP12E3-RR002` | The sharing-remap mutant was killed. `cargo fmt --check` failed. |
| 3 | `6b4222d1` | APPROVED | Formatting only. |

## Default-branch verification

These were run on `minion-agent/main` `8a2a39481f3613d3caea7d23048b518e05931bc0`, after all merges, with the pinned ICU 78.3 environment:

| Gate | Result |
|---|---|
| Python full suite | **2137 passed**, 16 skipped, 19 xfailed; coverage 100% |
| Rust workspace suite | **420 passed, 0 failed** (53 result groups) |
| `xtask conformance verify` | PASS |

## Cross-language note

The sharing-violation value differs by binding: Python gives `permission_denied`, Rust gives `unknown`, and pinned Pi/libuv gives `unknown`.

That is an instance of the existing Layer-12 mapper divergence `minion-agent#69`, which already carries this row. §13.4/§13.6 require only that each binding classify through its own shared mapper, and both bindings witness that relation. No new divergence is introduced.

## Downstream

WP-13.2's `edit` access stage consumes `EXEC-009` (§13.5). The dependency that blocked WP-13.2's final `edit` certification is now satisfied.
