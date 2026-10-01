# Layer 13 process-friction retrospective (WP-13.1, WP-13.2, WP-12.E3, L0506-D001)

**Status:** PROPOSED. Pending independent process review (`process/agent-workflow.md` §14).

**Scope.** This is a workflow/process retrospective. It does not reopen, reclassify or re-decide any semantic finding, and every finding cited keeps its recorded taxonomy and disposition. The purpose is to decide which mechanisms become permanent workflow, harness or automation improvements. It does not grade Claude or Codex.

**Evidence base** (all on GitHub, fetched 2026-10-01):
- **Coordination issues:**
  - `minion-agent#48` (WP-13.1): 66 comments, 14 rejection events, 2026-09-21 to 2026-09-28;
  - `#49` (WP-13.2): 13 comments, 5 rejections;
  - `#79` (WP-12.E3 / EXEC-009): 11 comments, 1 rejection;
  - `#88` (L0506-D001): 20 comments on 2026-09-30 alone, 5 rejections, then 3 convergence checkpoint revisions and a final-review blocker on 2026-10-01.
- **Assurance records:** `assurance/layers/13-*`, `12-wp12e3-*`, `l0506-d001-*`.
- **Size:** the coordination issue bodies measured 24,458 characters / 421 lines (`#49`) and 34,759 characters / 605 lines (`#88`). The owner's delegation record (`#75`) is 5,928 characters.
- **Scripts:** one Claude session accumulated more than 150 single-use scratch scripts for issue-body patches, guarded merges and byte-checked comments (`wp_state.py`, `postcheck.py`, `guarded_merge.py` and ~150 per-transition patch files). These are hand-written workflow mechanics.

## 1. The two sequences, as they actually happened

**WP-13.2** (`write`, `edit`, mutation queue):
1. Contract review → R001–R003, then remediation and targeted re-review.
2. Complete contract review → R004/R005 (canonical entry boundary; non-object raw arguments cannot enter the Rust pipeline).
3. R005 closed; R004 partially resolved, then targeted closure, then the final contract review, which APPROVED.
4. The contract needed a combined read+write access check that no lower layer had. That became a separate lower-layer extension, WP-12.E3 / `EXEC-009` (#79). Its review raised C001 (accepted) and C002 (disputed and withdrawn: the reviewer's libuv citation was wrong).
5. Python implementation → I001 (a quiescence settle window instead of firing timers), I002 (JSON numbers are doubles), I003 (a surrogate pair held as two characters).
6. Remediation → the I002 refinement for `-0` → final review → I004. Pi's `edit` preparation can produce a runtime ±Infinity that the before-hook observes, and Rust's certified argument type cannot hold it.
7. Owner decision (Option 1) → Layer-05/06 post-certification delta L0506-D001 (#88). WP-13.2 is blocked on it.

**L0506-D001** (prepared runtime numeric domain):
1. Contract review → R001 (diagnostic serialization), R002 (grammar mutations).
2. Targeted closure → final contract review → R003 (a dependency cycle with the WP-13.2 edit gate).
3. R003 closure → Python implementation → C001 (the finite-only `number` check was missing).
4. Implementation review → I001: pydantic nullable/opaque fields bypass the check.
5. The first remediation, a walker, survived as I001: union branches were lost. That triggered convergence CE-L0506-D001-I001-01.
6. The rev-1 checkpoint was rejected (C001 validator replay, C002 after-validator output). Rev 2 was rejected (C002 refined: a malformed sibling exempts its neighbour). Rev 3 was APPROVED.
7. Integration → targeted closure → final review → I002: a numeric-looking string was coerced by the check's own lax float.
8. Rev 4 APPROVED → integration → targeted closure → final review APPROVED → merge.
9. Rust implementation began. Codex's budget ran out mid-pass.

WP-13.1 had the same shape one layer earlier:
- `R002` path errors went through 3 characterization versions.
- `R006` `ls` collation went through 5 versions, ending in the `R006-C` pinned-ICU profile, then `L13-WP131-FR003` (R006-C not enforced).
- `R005-A` pinned photon-node image processing.
- Three rejected checkpoint revisions of CE-L13-WP131-02.
- A documentary status-sync PR pair after closure (`minion-agent#73` / `minion-agent-docs#172`), and the same pattern again after L0506-D001 (`#93` / `#202`).

## 2. Classification of each meaningful delay

Assurance value is **HIGH** when the event found or prevented a real parity/contract defect, **MEDIUM** when it forced useful precision, and **LOW** when it was mechanics or re-verification with no semantic yield.

| # | Delay / event | Root cause | Category | Assurance value | Avoidable | Reusable improvement |
|---|---|---|---|---|---|---|
| 1 | WP-13.2 I004: runtime ±Infinity found at *final implementation review*, forcing an owner decision and a lower-layer delta that blocked the WP | The value domain was never tabulated. JSON-domain values were assumed equal to JS-runtime values across Layer 05/06 | PROCESS | HIGH (a real defect) | YES, pre-contract | **Cross-Language Feasibility Matrix §2.1**: runtime value-domain matrix, mandatory before `AGREED FOR IMPLEMENTATION` |
| 2 | I002 huge integer → I002-refinement `-0` → I004 Infinity, found in three separate review cycles | Each fix closed one point of the JS-Number family instead of the family | PROCESS | HIGH per point; the serialization was LOW | YES | **Semantic-neighborhood expansion rule**, plus the reusable **JS-Number hazard family** |
| 3 | I003 surrogate pair held as two characters | UTF-16 semantics not enumerated for an edit/diff surface | PROCESS / MODEL_REASONING | HIGH | YES | **JS-String/UTF-16 hazard family**, required by the feasibility matrix whenever strings are compared, sliced or counted |
| 4 | I001: a settle window instead of firing timers (queue witness weakness) | The concurrency-order matrix did not list timer-delayed completion or require a negative control per ordering guarantee before implementation | PROCESS | HIGH | PARTLY | **Feasibility matrix §2.4** (concurrency/order), with a wrong-implementation idea per guarantee; **Async/order hazard family** |
| 5 | EXEC-009 (WP-12.E3) found missing only after the WP-13.2 contract was drafted: a separate lower-layer extension WP with its own full review cycle | No systematic check that each required operation has a certified lower-layer seam | PROCESS | HIGH | YES, at scoping | **Feasibility matrix §2.2**, the lower-layer capability matrix |
| 6 | L0506-D001 I001 → walker (branch-lossy) → rev-1/rev-2 rejections (validator replay, malformed sibling) | A Python-only mapping (pydantic callbacks, unions) with no reusable characterization of "complete-value union" and "callback output"; each revision found the next dimension | MODEL_REASONING / PROCESS | HIGH (all real) | PARTLY | Neighborhood expansion at the first finding (union × order × callback × sibling × coercion), plus the **error/coercion projection family**. The convergence protocol worked, but it started one cycle late |
| 7 | L0506-D001 I002: numeric-looking string coerced by the check's own lax float, found at *final* review after rev-3 agreement | The rev-3 characterization never asked "what else maps to the same error code?" | MODEL_REASONING | HIGH | YES | **Error-projection family** ("same error code from multiple sources"); **JS-Number family** ("numeric-looking string") |
| 8 | CE-L13-WP131-02 checkpoint rejected three times; R006 collation v1–v5 | Unicode/ICU version and collation semantics were discovered empirically, one probe at a time | PROCESS | HIGH | PARTLY | **Unicode hazard family** (pinned runtime Unicode/ICU version, normalization/collation drift), audited in the feasibility matrix §2.3 |
| 9 | R005-A photon pin: the image path's external package version was not pinned until review | External runtime/package versions are not a checklist item | PROCESS | HIGH | YES | Cross-runtime hazard checklist §2.3, "external package/runtime versions" |
| 10 | C002 (WP-12.E3): a blocker filed on an incorrect libuv source citation, disputed with content-addressed evidence, then withdrawn | The reviewer did not fetch the exact version/symbol before filing | PROCESS | LOW (net negative: a full dispute cycle) | YES | **Reviewer factual-evidence rule** (§9.2.1): fetch exact version, locate symbol, record content-addressed link before filing |
| 11 | Documentary status-only PR pairs after closure (`#73`/`#172`, `#93`/`#202`) | Mutable certification status lives in normative spec prose and the manifest `rule`/`python`/`rust` fields | PROCESS | LOW | YES | **Certification registry** as the single status source; spec prose carries semantics only |
| 12 | Coordination bodies grew to 24–35K characters; each read/write moved the whole remediation history | The current-state block accumulated history (every old SHA, test count and remediation narrative) | PROCESS / HARNESS | LOW | YES | **Lean current-state schema** plus a history index pointing at assurance; size budget |
| 13 | ~150 single-use patch scripts; several near-miss mechanics (stale `docs.sha` reconciled by the reviewer three times in #88; an invalid status value `BLOCKED` corrected once) | The state machine is enforced by prose and per-agent scripts, not a tool | TOOLING/AUTOMATION | MEDIUM (it caught real mistakes, but manually) | YES | **`minion-process`** CLI: validate, transition legality, round-trip write, handoff check, guarded merge |
| 14 | Full 2,300+ test suite re-run for every witness-only remediation | Every gate treated as release-level | PROCESS | LOW for small diffs | PARTLY | **Gate tiers G0–G3** mapped to workflow stages, with a recorded reason when escalating |
| 15 | Claude idle while Codex reviewed (and when Codex's budget ran out), although WP-13.3/13.4 characterization was independent | Workflow text implied one active WP at a time | PROCESS | none lost; latency only | YES | **Parallel-work policy**: one owner per WP, not one active WP; dependency edges recorded |
| 16 | WP-13.2 grouped `write`+`edit`+the mutation queue; the queue ordering, the edit numeric domain and the access check each carried independent high risk | Slicing by source folder rather than by semantic-risk surface | PROCESS | MEDIUM | PARTLY (future only) | **Semantic-risk map at scoping**: split before contract drafting when independent high-risk surfaces are combined |
| 17 | herdr prompt submissions stalling (`agent_prompt_stalled`), Codex usage limits mid-pass | Harness/tooling limits outside the workflow | HARNESS/PROMPT | n/a | PARTLY | Record partial state on the coordination issue before stopping; the resumable-checkpoint convention Codex already used for Rust L0506 |
| 18 | Long role prompts restating the §11 state machine in every handoff | Deterministic rules live only in prose | HARNESS/PROMPT | LOW | YES, once tooling exists | Move mechanical rules into `minion-process` and schema validation; prompts keep semantics, ownership and independence |
| 19 | Found by dogfooding the new validator on live issues: the documented legal-transition table (`coordination-state.md` §10) did not cover practice. #49 used `CONTRACT_REVIEW→REMEDIATION→CONTRACT_REVIEW` and the non-status `BLOCKED`; #79 used `RUST_IMPLEMENTATION→IMPLEMENTATION_REVIEW→CLOSED`; #88's contract-first path `CONTRACT_REVIEW→FINAL_CONTRACT_REVIEW→PYTHON_IMPLEMENTATION` was outside the table | The state machine was prose, and nothing checked transitions at write time | TOOLING/AUTOMATION | MEDIUM (it hid drift; no semantic harm found) | YES | Reconciled table (`coordination-state.md` §10.1), enforced by `minion-process apply`/`transition-check`, with historical-replay tests |
| 20 | Also found by dogfooding: `open_findings` held a mapping (ID → rule/scope prose) in #49/#88, a list elsewhere; state blocks carried `remediations`/`review_history` | No container-shape validation of coordination state (the §8 rule existed for the manifest only) | TOOLING/AUTOMATION | LOW | YES | Lean schema v2 (`coordination-state.md` §13): IDs only; the legacy mapping is accepted with a warning until migrated |
| 21 | WP132-RUST-C001 (2026-10-01): the inner `JSON.parse` in `prepareEditArguments` turns an escaped `\ud800` into a lone UTF-16 surrogate that Pi keeps through hooks/execute (file bytes `efbfbd`); certified Rust `PreparedValue::String(String)` cannot hold it. Found at **Rust implementation**, one delta after L0506-D001 settled the *numeric* half of the same prepared-runtime domain | L0506-D001's characterization covered the JS Number family only; the JS String / UTF-16 family of the same wire-vs-runtime boundary was never enumerated | PROCESS | HIGH (real gap) | YES | The Owner decision (#49 comment `5924605017`) opens L0506-D002 and requires exactly the proposed mechanisms: a Cross-Language Feasibility Matrix over the full string neighborhood (`process/hazard-families.md` F2) and explicit comparison of the Pi JS String / Python / Rust string domains, wire serialization and encoding boundaries before any string-bearing contract checkpoint |

## 3. What the table says

- **The dominant cost was late semantic discovery, not review strictness.** Rows 1–9 are all HIGH-value findings. The problem is *when* they were found: at implementation or final review instead of scoping or contract. Each would have been cheaper as a row in a matrix that had to be filled before contract freeze.
- **Most late discoveries belong to a small number of recurring runtime hazard classes:** JS Number, UTF-16, Unicode/ICU, async ordering and error/coercion projection. Today each class is rediscovered per work package. The harness should remember the class.
- **The second cost was mechanics:** state-body bloat, per-transition scripts, status-only PRs and full-suite re-runs. None of it found defects. It should move to tooling and a single status source.
- **Nothing here argues for weaker review.** Every HIGH row was caught by independent review. The improvements move the same checks earlier and make the mechanical parts deterministic.

## 4. Replay against the historical incidents (§15 of the improvement brief)

For each incident: would the new process have discovered or prevented it earlier, at which gate, what enforces it, and does assurance get weaker anywhere?

| Incident | Earlier? | Gate | Enforcing artifact/tool | Assurance weaker? |
|---|---|---|---|---|
| WP-13.1 stale status needing `#73`/`#172` | Prevented: status is no longer in spec/manifest prose | Merge (registry update is part of the merge transition) | Certification registry + `minion-process validate-status` (Phase B) | No. The status becomes single-sourced and validated |
| WP-13.2 missing EXEC-009 | Yes, at scoping | Feasibility matrix §2.2 must be filled before `AGREED FOR IMPLEMENTATION` | `process/templates/cross-language-feasibility-matrix.md`; the checkpoint reviewer rejects an empty or "N/A" row without a reason | No |
| WP-13.2 huge-number / `-0` / Infinity chain | Yes, at contract. The matrix §2.1 value-domain rows for JSON-derived numbers must list every JS-Number family member, and the first finding triggers neighborhood expansion | Contract checkpoint (G1 characterization) | Feasibility matrix §2.1 + `process/hazard-families.md` JS-Number + §9.4 neighborhood rule | No |
| WP-13.2 UTF-16 surrogate pair | Yes, at contract | Checklist §2.3 "String.length / UTF-16" must be AUDITED for any string slicing/diffing surface | Feasibility matrix §2.3 + the UTF-16 family | No |
| WP-13.2 queue-order witness weakness (I001) | Yes, at contract | Matrix §2.4 requires a wrong-implementation idea per ordering guarantee, including "timer beyond naive polling interval" | Feasibility matrix §2.4 + the async/order family | No |
| L0506-D001 pydantic union semantics | Partly: one cycle earlier | Neighborhood expansion at the *first* I001 finding: union order × container × callback × sibling | §9.4 + the error/coercion projection family | No |
| L0506-D001 numeric-looking transformed strings (I002) | Yes, at the rev-3 checkpoint | The JS-Number family includes "numeric-looking string", and the projection family asks "same error code from multiple sources" | `process/hazard-families.md`, required at the convergence checkpoint | No |
| R005-A photon pin | Yes, at scoping | Checklist §2.3 "external package/runtime versions" must be AUDITED | Feasibility matrix §2.3 | No |
| R006-C ICU semantics | Yes, at scoping, and fewer revisions | Checklist §2.3 "Unicode / ICU version" + the Unicode family (collation, drift) | Feasibility matrix §2.3 + the Unicode family | No |
| C002-style incorrect source-citation review | Prevented | Before filing: the reviewer factual-evidence rule | §9.2.1; the review record must carry the content-addressed link | No. It is stronger, since unverified blockers are rejected |
| WP132-RUST-C001 lone-surrogate prepared string (added 2026-10-01) | Yes, at L0506-D001's contract checkpoint: the value-domain matrix §2.1 must list `UTF-16 code units` / `lone surrogate` for every prepared value crossing Layer 05/06, and the F2 family would have been expanded alongside F1 | Feasibility matrix §2.1 + `process/hazard-families.md` F2 + §9.4 neighborhood rule | No |

**No row relies on "think harder".** Each lesson is encoded in one of: a template that must be filled before a checkpoint, a reusable probe family, a reviewer-evidence rule with a required record field, or a tool check.

## 5. Improvements adopted by this change (see `process-history.md`)

| Phase | Improvement | Where |
|---|---|---|
| A | Cross-Language Feasibility Matrix (mandatory for high-risk WPs before `AGREED FOR IMPLEMENTATION`) | `process/agent-workflow.md` §4.1.1; `process/templates/cross-language-feasibility-matrix.md` |
| A | Reusable hazard families | `process/hazard-families.md`; workflow §9.5 |
| A | Semantic-neighborhood expansion | workflow §9.4 |
| A | Reviewer factual-evidence rule | workflow §9.2.1 |
| A | Gate tiers G0–G3 | `process/gate-tiers.md`; workflow §13.1 |
| A | Lean current-state guidance | `process/coordination-state.md` §13; workflow §11.1.4 |
| A | Parallel-work policy and dependency edges | workflow §11.15 |
| A | Semantic-risk map at scoping | workflow §4.2 |
| A | Process metrics | workflow §14.6 |
| B | Certification registry (design) | `process/certification-registry-design.md` |
| C | `minion-process` CLI (design + first implementation), transition-table reconciliation | `process/minion-process-cli-design.md`; `process/tools/minion_process/`; `coordination-state.md` §10.1; workflow §11.16, §12.7 |

Phase B migrations (registry, lean-schema migration of the open issues #49/#88) are designed here, and they proceed separately after independent approval. No existing issue body is rewritten by this change.

---

## Remediation 1: independent process review (Codex), CHANGES REQUIRED at `e5fe80e2`

Review: `minion-agent-docs#204`, published verbatim on Codex's behalf (comment `5922990518`). All four findings are accepted:

- **PROC-L13-R001.** The candidate checks failed open. A PR without a SHA skipped its side, and any `merged_sha` disabled the PR checks. My own test had codified the first hole.
  - **Fix:** a PR reference now requires the exact SHA. `merged_sha` is shape-validated, and it is *verified* (PR merged, merge commit equal, head equal, on the default branch); it never switches checks off.
  - A side with no candidate at all is still not checked.
- **PROC-L13-R002.** A resume from `BLOCKED_FOR_OWNER` committed without provenance.
  - **Fix:** `apply` refuses before writing unless a non-empty `governance_source` is recorded. The tool checks presence only; agents still validate authority, decision and scope (§11.10).
- **PROC-L13-R003.** Malformed control data validated.
  - **Fix:** supported `schema_version` values only; string-typed control fields; element-level validation after the container check; mixed v1/v2 candidate forms rejected.
- **PROC-L13-R004.** The gate-stage wording contradicted itself.
  - **Fix:** G3 is author-run certification *evidence*, consumed by the separate independent complete review. Complete-review hand-offs need G3 evidence; targeted finding-closure hand-offs follow the stage table, which is authoritative.

**Evidence.**
- Codex's `reviewer_probes.py` witnesses are now permanent tests.
- Every probe is now caught: the three validator cases error, both handoff holes report failures, and the governance-less resume is refused with zero writes.
- Tool: 93 tests, 100% statement coverage, ruff and strict mypy clean.
- Live issues #35, #49, #50, #51 and #95 still validate.
