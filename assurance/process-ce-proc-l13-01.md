# CE-PROC-L13-01 — fail-closed control-data handling in `minion-process` (convergence episode)

- **Coordination:** `minion-agent#95`, state `CONTRACT_CONVERGENCE`.
- **Candidate under convergence:** docs #204 @ `cc44a13b2a34b4024ad51ed8b68d9d02f65df8a4`.
- **Trigger check** (`agent-workflow.md` §11.8):
  - **A fired:** PROC-L13-R001 and PROC-L13-R003 each survived two independent reviews (Codex: the review at `e5fe80e2`, then targeted closure at `cc44a13b`, `#204` comments `5922990518` and `5923085782`).
  - **B fired:** both refined findings are successors on one root-cause surface.
  - **C has not fired:** one rejected complete review.
- **No point-fix exception is claimed.** Another point patch on this surface would likely produce a third successor, which is what convergence exists to stop.
- **Status:** CHARACTERIZATION → **PROPOSED FOR IMPLEMENTATION**, pending Codex checkpoint review (§11.8.5). R002 and R004 stay PROVISIONALLY CLOSED and are untouched.

## Root cause

The tool validates a **chosen subset** of fields at a **chosen depth**. It then *consumes* control data along paths the validator never covered:
- a merged claim on a PR-less side;
- a malformed `current_candidate` treated as absent;
- nested `convergence.open_findings` joined before validation;
- `cli status` dereferencing a malformed `code`/`docs`.

Each review found the next unvalidated consumption path. The missing invariant is **totality plus consumption coverage**: every value the tool reads is shape-validated before use, and no supplied value is ever silently reinterpreted as absent.

## Characterization: consumed field × malformation class

The fields are enumerated mechanically from every `.get` / `[]` read in `process/tools/minion_process/*.py`, plus the validator's own loops. The malformation classes are:
- **A**, absent;
- **N**, null;
- **C**, wrong container;
- **E**, wrong element/scalar type or format;
- **M**, a mixed or ambiguous form;
- **Z**, empty where content is required.

| Field | Shape (rule) | A / N meaning | C, E, M, Z must → |
|---|---|---|---|
| `workflow` | mapping | A → body error | C → error |
| `schema_version` | int ∈ {1, 2} | A → 1 | E (other int, string) → error |
| `status` | enum §3.1 | A/N → error | E → error |
| `next_owner` | string ∈ owners, or null | null only where §4 allows | E (non-string, unknown) → error; Z when active → error |
| `next_action` | non-empty string, or null | null only where §4 allows | E (non-string) → error; Z when active → error |
| `updated_by`, `updated_reason` | string or null | optional | E → error |
| `requirements` | list of strings | optional | C → error; E (element) → error |
| `open_findings`, `provisionally_closed` (top level) | v2: list of finding IDs; v1: also an ID → mapping | optional | C → error; E (element) → error; v1 mapping in v2 → error |
| `current_candidate` (v2) | mapping with only the keys `code` / `docs` | A → v1 form used | **C → error, never fall back to v1**; unknown key → error; **M** (also top-level `code`/`docs`) → error |
| `code`, `docs` (either form) | mapping, or null (= no candidate) | A/N → side absent | C → error |
| `….pr` | int | optional | E → error |
| `….sha` | 40-hex | **required when `pr` or `merged_sha` is present** | E → error; A with `pr`/`merged_sha` → error |
| `….merged_sha` | 40-hex, **only together with `pr`** (a PR-backed accepted baseline; no other baseline form exists) | optional | E → error; **present without `pr` → error**; when present, verified remotely (merged, merge oid, head, default containment) |
| `….base` | string | optional | E → error |
| `convergence` | mapping | optional (required in `CONTRACT_CONVERGENCE`) | C → error |
| `convergence.episode` | non-empty string | required in `CONTRACT_CONVERGENCE` | E/Z → error |
| `convergence.open_findings` | list of finding IDs | optional | C → error; **E (element) → error, before any use** |
| `convergence.provisionally_closed` | list of (finding ID, or mapping `{finding: ID, …}` per §6) | optional | C → error; E → error |
| `convergence.checkpoint` | string | optional | E → error |
| `governance_source` | mapping or non-empty string, or null | optional; on resume from `BLOCKED_FOR_OWNER`, required non-empty (R002) | E → error |
| `deferred_trigger` | mapping or non-empty string, or null | required in `WAITING_FOR_TRIGGER` | E → error |
| `quarantine` | mapping; `derived_from_quarantined_artifact` is bool | optional | C → error; E (non-bool flag) → error |
| `dependencies` (v2) | mapping name → mapping `{issue: int, relation ∈ {blocked_by, independent_of, shares_artifact}, …}` | optional | C/E → error |
| `history` (v2) | mapping; `assurance_index` string | optional | C/E → error |

## Rules proposed for the checkpoint

1. **Consumption coverage.** Every field the tool reads anywhere (validator, `ops`, `cli`) has a row above, and the validator enforces that row. A new read without a row is a defect.
2. **No silent reinterpretation.** A *supplied* malformed value is an error. It is never treated as absent, never defaulted, and never routes to another form. Absent and null are valid only where the row says so.
3. **Element after container.** Every list or mapping is validated as a container first, then per element, before it is joined, iterated or used. This applies at every nesting depth.
4. **Totality.** `validate_workflow` returns diagnostics and never raises, for any JSON-representable value. The read-only operations (`candidate_report`, `handoff_report`, `cli status`/`validate`) never raise on a malformed state either: they report `HANDOFF_BLOCKED` / `INVALID` instead. `commit_state` raises only `CheckFailed` / `BodyFormatError`.
5. **Fail closed on invalid state.** `handoff_report` and `candidate_report` refuse (failed check) whenever `validate_workflow` reports an error. They never proceed with a partially understood candidate.
6. **Merged baseline.** `merged_sha` requires `pr` and `sha`, and it is verified remotely. An unverifiable merged claim fails. A SHA-only side (no `pr`, no `merged_sha`) is still a valid reachability-checked reference.

## Acceptance witnesses (to become permanent tests)

**Codex's refined witnesses**, each RED at `cc44a13b`:
- a merged claim with no PR;
- `current_candidate: "not a mapping"`;
- `convergence.open_findings: [null]` in `FINAL_CONTRACT_REVIEW`.

**The row table as a parametrized test.** For every row and every applicable class: a malformed value → an error at that path. The documented valid values → no error.

**Totality property test** (Hypothesis, already a dev dependency of the repo's Python projects). Generate arbitrary JSON-like values, substitute them at each consumed path of a valid workflow, then assert that:
- `validate_workflow` never raises;
- `handoff_report` (FakeGitHub) never raises;
- whenever validation reports no error, the candidate checks see only well-formed entries;
- when validation errors, the handoff fails.

**`cli status` on a malformed state:** a diagnostic, never a traceback.

**Positive controls:**
- a verified merged baseline;
- a SHA-only side;
- an absent side;
- the v1 legacy finding mapping (warning only);
- the §6 `provisionally_closed` mapping form;
- valid v1 and v2 forms.

**Negative control:** the new tests run against `cc44a13b`'s `validate.py` / `ops.py` / `model.py` / `cli.py` must fail. The record will state the RED count.

## Out of scope

- Remote/GitHub response shapes. `gh` output is trusted as an authority response, as before.
- Semantic validation of governance content (an agent's duty, §11.10).
- Phase C2 commands.
- Any product semantics.

## Checkpoint

```text
CONVERGENCE CHECKPOINT
    PROPOSED FOR IMPLEMENTATION

OPEN FINDINGS
    PROC-L13-R001, PROC-L13-R003

ACCEPTANCE WITNESSES
    the three refined witnesses; the row-table parametrized test; the totality property test;
    cli status robustness; the positive controls; RED at cc44a13b

NORMATIVE DELTAS
    coordination-state.md §13 gains the field-shape table (this one, as normative);
    minion-process-cli-design.md states rules 1-6

NEXT_OWNER
    Codex (checkpoint review; only its APPROVED makes this AGREED FOR IMPLEMENTATION)
```

---

## Checkpoint revision 2: response to C-PROC-L13-01-01 / -02 (Codex, REJECTED at `9c603495`)

- **Review:** `#204` comment `5923147284`, published verbatim on Codex's behalf.
- **Accepted:** the core directions above. Both gaps are accepted. Revision 1 stays as written.
- **Neighborhood expansion** (`agent-workflow.md` §9.4, proposed). Both gaps share a shape: an *entry point* or *field* that rev 1's enumeration missed. So rev 2 enumerates **entry points** as well as fields, mechanically from the source, and closes the partition, not just the two witnesses.

### Added field rows

| Field | Shape (rule) | A / N meaning | C, E, Z must → |
|---|---|---|---|
| `work_package` | non-empty string (the canonical WP identity, `coordination-state.md` §2) | **required**: A/N → error | E (non-string, e.g. `[None]`) → error; Z → error |
| `title` | string | optional | E → error |
| `layer` | string | optional | E → error |

### Entry-point table

Every function or command that consumes coordination state:

| Entry point | Consumes | Rule |
|---|---|---|
| `validate_workflow` | the whole object | total: diagnostics only, never raises |
| `candidate_report` | candidates (via `candidates()`) | validates first; any validation error → a failed check, and the candidate is not consumed further |
| `handoff_report` | issue state, the whole object | as `candidate_report`; `HANDOFF_BLOCKED` on invalid state |
| `commit_state`, **current** state | `status` (transition lookup), the whole object | **validates the current state before any use.** If invalid → `CheckFailed` ("current state invalid"), zero writes, and the transition lookup is never fed invalid data. **Exception: explicit repair mode** (`apply --repair`, `agent-workflow.md` §11.1.1 failed-commit repair). Transition legality is not evaluated against an invalid current status. The intended state must fully validate. The result is reported as `REPAIRED (current state was invalid)`, and the agent records the last-known-good source |
| `commit_state`, **intended** state | the whole object, transition | validated before writing; `CheckFailed`, zero writes (as today) |
| `commit_state`, **remote** state | the whole object | validated after writing; a failed state commit (as today) |
| `cli status` | `work_package`, `status`, candidates, findings, owner/action, convergence | prints **validated** values. Candidates come through the single `candidates()` accessor, so v1 and v2 are read identically. An invalid state prints the diagnostics and exits 1, never a traceback |
| `cli validate` / `candidate-check` / `handoff-check` | as their operations | diagnostics, non-zero exit, no traceback |
| `cli apply` | as `commit_state` | `CheckFailed` / `BodyFormatError` → message and exit 1 |
| `merge`, `comment` | arguments plus remote PR/comment data only | out of this surface (no coordination state); unchanged |

### Rules added to 1–6

7. **Entry-point coverage.** Every entry point above validates the state it consumes before consuming it, including `commit_state`'s **current** state. A new entry point without a row is a defect.
8. **One accessor.** Every consumer reads candidates through `candidates()`, after validation. No consumer reads top-level `code`/`docs` directly. A valid v2 `current_candidate` is observed exactly as recorded.
9. **Controlled-exception scope.** For **malformed coordination data**, `commit_state` raises only `CheckFailed` / `BodyFormatError`, before any write. Remote/network failures (`GitHubError`) and exceptions raised by a caller's own patch code are **out of scope**: they propagate as they are, and they are not described as malformed data.

### Acceptance witnesses added

All are RED at `cc44a13b` unless marked positive.
- **Malformed identity:** `work_package: [None]`, `work_package` absent, and `work_package: ""` → validation errors.
- **`cli status` positives, v1 and v2:** with real recorded `code`/`docs` PRs and SHAs, the output contains the exact PR numbers and SHAs (not just exit 0). With the v2 form, `PR None sha None` must not appear.
- **`cli status` on malformed state:** diagnostics and exit 1, no traceback.
- **Mutation boundary, current state:**
  - `status: ["IMPLEMENTATION_REVIEW"]` patched to a valid status → `CheckFailed`, zero writes, transition lookup never reached;
  - the same with a malformed `current_candidate`;
  - the same with `work_package: [None]`.
- **Mutation boundary, intended state:** a patch writing each malformed class → `CheckFailed`, zero writes.
- **Repair mode** (positive): an invalid current state plus `repair=True` and a fully valid intended state → committed and round-trip verified. With `repair=True` and an invalid intended state → refused.
- **Bounded Hypothesis totality** over every listed entry point: `validate_workflow`, `candidate_report`, `handoff_report`, `cli status`/`validate`, and `commit_state` with a substituted current or intended value. Arbitrary JSON-like values substituted at each consumed path → only the allowed outcomes, i.e. diagnostics, failed checks, `CheckFailed` / `BodyFormatError`, with zero writes on refusal. The search is bounded (`max_examples` per path), not a Cartesian product.
- **Scope control:** a patch function that raises its own `RuntimeError` still propagates as `RuntimeError` (rule 9), and a `GitHubError` from the fake propagates unchanged.

### Checkpoint, revision 2

```text
CONVERGENCE CHECKPOINT
    PROPOSED FOR IMPLEMENTATION (revision 2)

OPEN FINDINGS
    PROC-L13-R001, PROC-L13-R003

ACCEPTANCE WITNESSES
    rev 1 witnesses + the witnesses added above (identity, v1/v2 status positives,
    mutation-boundary current/intended, repair mode, bounded entry-point totality, scope controls)

NORMATIVE DELTAS
    coordination-state.md §13: the field table (rev 1 + the added rows) and the entry-point table;
    minion-process-cli-design.md: rules 1-9 and `apply --repair`

NEXT_OWNER
    Codex (checkpoint review)
```

---

## Checkpoint revision 3: response to C-PROC-L13-01-03 (Codex, REJECTED at `a3ca3848`)

- **Review:** `#204` comment `5923270178`, published verbatim on Codex's behalf.
- **Agreed at checkpoint level:** C-PROC-L13-01-01 and -02 are CLOSED. This revision changes **only** the repair-mode rows.
- **Accepted finding.** Rev 2's repair mode let a corrupted current body stand in for an authority. A shape-valid intended state could make an illegal transition (`SCOPING` → `RUST_IMPLEMENTATION`) or resume from `BLOCKED_FOR_OWNER` without a governance source.

### Repair mode, redefined: restore only, never transition

`apply --repair --revision <id>` (replacing rev 2's `apply --repair`) does exactly one thing: it **restores the issue body, byte for byte, to an earlier revision of that same issue's body.** That revision is identified in, and fetched from, GitHub's own edit history for the issue (`userContentEdits`), which is the §11.1.1 "last known-good remote canonical state".

1. **Baseline authority is GitHub, not the caller.** The tool fetches the revision itself; the caller passes only its id. A caller-supplied file or body is never a baseline.
2. **The baseline must validate.** The restored revision must parse and pass `validate_workflow` with no errors. Otherwise the tool refuses with zero writes.
3. **No transition, no delta.** Repair writes the baseline unchanged. It is not a transition: the restored `status`, owner/action and governance fields are exactly the baseline's. So legal-transition and governance guards are neither evaluated nor bypassed, because no new state is created.
4. **The only precondition is that the current state is invalid.** Repair is refused when the current body is *valid*: a valid state must use a normal checked `apply`. It is also refused when the revision id is unknown, or the history cannot be fetched. Both are controlled diagnostics with zero writes. Chronology or authority uncertainty is returned to the agent, not guessed.
5. **Then a normal checked `apply`.** Any intended change after restoration (the "intended delta" of §11.1.1) is a separate, ordinary `apply` from the restored baseline, with every guard: ALLOWED keys, legal transition, governance-on-resume, intended-state validation and the remote round trip.
6. **Round trip.** The restoration is verified like any commit: re-fetch, then parse, validate and byte-compare against the restored revision. It is reported as `RESTORED <revision id> (current state was invalid)`.

### Acceptance witnesses (repair rows; they replace rev 2's repair witnesses)

**Positive:**
- a corrupted current body (`status: ["SCOPING"]`) plus the id of the earlier valid revision → the body is restored byte-identically, then validated;
- a following `apply` making a **legal** transition succeeds.

**Negative**, each refused with zero writes:
- a restore followed by `apply` to an **illegal** target: Codex's witness, last known-good `SCOPING` → `RUST_IMPLEMENTATION`. The `apply` is refused by the transition guard, and restoring never touches status;
- a restored `BLOCKED_FOR_OWNER` baseline followed by a resume `apply` with no governance source → refused (R002);
- an unknown revision id;
- a history fetch failure;
- a revision that does not validate;
- a repair attempted while the current state is valid;
- a caller-supplied body or file offered as a baseline (no such input exists, a structural witness at the CLI).

### Checkpoint, revision 3

```text
CONVERGENCE CHECKPOINT
    PROPOSED FOR IMPLEMENTATION (revision 3)

OPEN FINDINGS
    PROC-L13-R001, PROC-L13-R003

ACCEPTANCE WITNESSES
    rev 1 + rev 2 witnesses (C-01 and C-02 agreed), with the repair rows above replacing rev 2's

NORMATIVE DELTAS
    coordination-state.md §13: the field and entry-point tables;
    minion-process-cli-design.md: rules 1-9 and `apply --repair --revision <id>` (restore only)

NEXT_OWNER
    Codex (checkpoint review)
```

---

## Implementation (after AGREED FOR IMPLEMENTATION at `fb2b1e8e`, Codex `#204` comment `5923479469`)

The agreed revisions 1–3 are implemented in `process/tools/minion_process/{validate,ops,model,github,cli}.py`.

**Witnesses:** `process/tools/tests/test_ce_proc_l13_01.py`, 107 tests:
- the field × class table (35 + 9 v2 rows), with 9 documented-valid positive forms;
- Codex's three refined witnesses, each across validation, handoff and the candidate check;
- the CLI status v1/v2 positives (exact PR/SHA printed; no `PR None`), and malformed/unparseable state → exit 1 for every read command;
- the mutation boundary: current invalid → refused before any use; intended invalid → refused; zero writes each time;
- scope controls: a patch's own `RuntimeError` and a `GitHubError` propagate;
- restore-only repair:
  - positive: a byte-identical restore, then a legal `apply`;
  - refusals: an illegal follow-up (`SCOPING` → `RUST_IMPLEMENTATION`); an owner-blocked resume without provenance; an unknown revision; a history-fetch failure; an unparseable or invalid revision; a valid current state; a CLI patch/body baseline;
- bounded Hypothesis totality over 30 consumed paths × every entry point (read-only and `commit_state` current/intended).

**Found by the totality search** (3000 examples per property; each pinned as a regression):
1. A mapping key containing U+0085 (YAML NEL) validated, was written, and only then failed the remote round trip. `apply` now refuses before writing any state that does not survive YAML serialization unchanged.
2. `pr: 0` passed as an integer and reached a remote lookup. PR and issue numbers must now be positive, and a failed PR lookup is a failed check, not an exception.

**Negative control:** the new witnesses run against the characterized implementation `cc44a13b` (scratch copy; repair witnesses fail there because `restore_revision` did not exist): **68 failed / 39 passed**. All three refined witnesses are RED there and GREEN here. The 39 that pass there are positive controls and pre-existing checks.

**Gates:** 200 tool tests passed, statement coverage 100%, ruff clean, strict mypy clean. The live issues #35, #49, #50, #51 and #95 still validate.

**Housekeeping:** `cc44a13b` had accidentally committed `__pycache__/` files and `.coverage`. They are untracked here, and `process/tools/.gitignore` is added.

**Normative deltas:** `coordination-state.md` §13.5, and `minion-process-cli-design.md` §1.1 (rules 1–9, restore-only repair).

**Status:** PROC-L13-R001 and R003 are REMEDIATED, pending Codex §11.8.7 targeted closure. R002 and R004 stay provisionally closed. The §11.8.8 final complete review of #204 follows closure.
