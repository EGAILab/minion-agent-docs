# Layer 04 — Third-Pass Re-Review Package (`XFORM-R001` complete, `XFORM-R002`, regression only)

**Prepared:** 2026-08-24
**Prepared by:** Claude (Python/shared-contract owner, per the adopted workflow)
**Why this exists:** the second Rust re-review
(`04-target-model-transformation-rust-r001-r004-rereview.md`, docs `c64880d`) again returned:

```text
LAYER 04 XFORM SHARED CONTRACT
    REJECTED — PI_PARITY_DEFECT
```

with `XFORM-R001` still open (root cause: the certified Layer-02 `UserMessage.content` type itself,
not the transform function), `XFORM-R002` still open (a `usage`-requiredness gap the review's own
independent probing found), `XFORM-R003` confirmed `APPROVED` (unchanged), and `XFORM-R004` still
open (stale scenario-count arithmetic). **Review this package last**, after
`02-llm-delta-rust-handoff-llm-f012.md` and `03-session-artifacts-delta-rust-handoff-ses-f009.md`
are both `APPROVED` — `XFORM-R001`'s complete fix and this package's own regression confirmations
both depend on the upstream layers' fixes landing first.

**Reviewed commits (delta candidate):**

```text
minion-agent        4ed360d   conformance/schema/agent-transform-scenario.schema.json (usage/cost
                               requiredness), tests/conformance/transform_runner.py (fabrication
                               removed), 13 conformance/agent/*.yaml scenarios (complete usage
                               objects added), pi-parity-manifest.yaml (AI-004) -- same push as
                               LLM-F012/SES-F009
minion-agent-docs   f610e8b   assurance/layers/04-target-model-transformation.md (§0.6-§0.10),
                               this handoff
```

**Pinned Pi revision:** `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged).

**Do not modify Rust in response to this package without first recording a verdict.** Rust
implementation timing is still not adjudicated by this package.

---

## 1. `XFORM-R001` — verify the complete fix, not just the runtime branch

**What changed:** nothing in `transform_messages.py`'s own logic (the runtime string-preservation
branch from the first remediation was already correct and remains unchanged). The fix landed
upstream: `LLM-F012` (Layer 02) retyped `UserMessage.content: str | tuple[UserContentBlock, ...]`,
so `UserMessage(content="hello", timestamp=1)` is now statically valid, not merely
runtime-permitted. `transform_runner.py`'s decoder helpers were simplified accordingly (no change
in behavior, only in what the type checker now confirms).

**Verify directly, do not trust the upstream packages' own reports:**
1. Confirm `mypy src/minion_agent tests/typing/valid_message_construction.py` (run from
   `minion-agent-python/`) passes clean, and that this file includes
   `UserMessage(content="hello", timestamp=1)` with no `type: ignore`.
2. Re-run the exact static probe the second review used to reject this finding:
   `UserMessage(content="hello", timestamp=1)` — confirm mypy no longer reports
   `Argument "content" ... incompatible type "str"`.
3. Re-run the runtime probe matrix from the first re-review (still expected unchanged):
   `"hello"`/`""`/`"   "`/the placeholder-literal string, each under a vision and a non-vision
   target, all preserved exactly.

## 2. `XFORM-R002` — verify `usage` requiredness end-to-end

**What changed:** `agent-transform-scenario.schema.json`'s `usage`/`cost` `$defs` gained `required`
lists matching every non-optional member (`spec/llm.md`: only `cache_write_1h`/`reasoning` carry
`?`); both assistant `required` lists (input and output shapes) gained `usage`.
`transform_runner.py::_usage()` now reads every field directly (`raw["input"]`, not
`raw.get("input", 0)`) — no fabrication for a required-and-therefore-always-present field.
`ToolResultMessage.usage` remains genuinely optional at its own call site.

**Reproduce this exact matrix directly, do not reuse this document's reported results:**

```text
Assistant missing usage                REJECT
Assistant usage={}                     REJECT
Assistant usage missing input          REJECT
Assistant usage missing output         REJECT
Assistant usage missing cache_read     REJECT
Assistant usage missing cache_write    REJECT
Assistant usage missing total_tokens   REJECT
Assistant usage missing cost           REJECT
Cost missing any mandatory member      REJECT
Assistant with complete usage          ACCEPT
ToolResult without usage               ACCEPT
ToolResult with complete usage         ACCEPT
ToolResult with incomplete usage       REJECT
```

Also re-confirm the full first-re-review matrix is unchanged (string content, empty target
identity, rich fields, `expect: {}`, role-content legality — all still correct).

**Verdict question specific to this finding:** is `Usage`/`Cost`'s requiredness already correctly
expressed in Rust's own typed vocabulary (a non-`Option` field for every non-optional member)? If
so, this finding requires no Rust code change at all — it was purely a shared-schema/Python-runner
gap.

## 3. `XFORM-R003` — unchanged, not reopened

Still `APPROVED`. No new evidence this pass. Do not re-review unless independently discovered
evidence contradicts the existing disposition.

## 4. `XFORM-R004` — verify the count arithmetic is now fully consistent

Search `assurance/layers/04-target-model-transformation.md` end to end for every occurrence of
`12` and `13`. Every current-state inventory claim (§2's normative-sources list, §10's
implementation-inventory table, §16's gate output, §18's freeze gate) must now say `13`
consistently; only genuinely historical references (e.g. "12 pre-existing scenarios" describing
what existed *before* a specific remediation step, or rule/section numbers that happen to be "12")
may still say `12`. Confirm no remaining internal contradiction.

## 5. Regression check — everything already approved, re-confirm unchanged

```text
same-model redacted thinking            unchanged
thinking compatibility matrix           unchanged
placeholder-dedup mechanics             unchanged
image capability gate                   unchanged
frozen target identity triple           unchanged (non-empty-enforced, from the first re-review)
injected ID-normalization callback      unchanged
cross-model signature stripping         unchanged
orphan synthesis ordering               unchanged
error/aborted exclusion                 unchanged
Session -> XFORM composition            unchanged
runner thinness                         unchanged
Phase-5 production-wiring boundary      unchanged
```

## 6. Canonical inventory, freshly re-enumerate

```text
XFORM canonical: 13 (string-user-content-survives-transformation.yaml is the +1 vs. the first
  candidate's 12; not changed again this pass)
Session canonical: 19 total, 19 current-layer executable, 0 deferred, 0 placeholders
  (string-user-message-round-trip.yaml is the new +1 for SES-F009)
```

## 7. Explicitly out of scope for this package

- `LLM-F012` (Layer 02) and `SES-F009` (Layer 03) — reviewed in their own packages, gate this one.
- Rust implementation timing adjudication — still not this package's job.
- Layer 05.

## 8. Expected outcome

```text
LAYER 04 XFORM SHARED CONTRACT
    APPROVED
```

or a precise rejection. If approved — and only once `LLM-F012`/`SES-F009` are also `APPROVED` —
consolidated Rust implementation remediation and Rust Layer-04 implementation-timing adjudication
may both begin, per the certification ordering: Layer 02 final closure, then Layer 03, then Layer
04's own shared-contract/implementation gates.
