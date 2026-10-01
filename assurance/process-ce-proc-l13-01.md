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

---

## Remediation 1 of the implementation: PROC-L13-R003 refined (Codex targeted closure at `290677bd`)

- **Review:** `#204` comment `5924612862`, published verbatim on Codex's behalf.
- **Results:** R001 is PROVISIONALLY CLOSED. R002 and R004 stay provisionally closed.
- **Accepted:** R003's refined witness. A **valid fence containing invalid YAML syntax** let PyYAML's `ParserError` escape every read command, `apply` and restore-only repair. So repair could not restore this common kind of corruption.
- **Why it was missed:** my witnesses used only a missing or broken fence, and the totality property generated only *serializable objects*. Neither reached the raw-syntax dimension.

**Fix:** at the shared body boundary, `model.split_body` contains `yaml.YAMLError` and raises the declared `BodyFormatError`. Every caller already handles that controlled error:
- read commands give a diagnostic and exit 1;
- `apply` refuses with zero writes;
- repair treats malformed current YAML as invalid and restores a valid same-issue revision;
- a malformed baseline revision is a controlled refusal.

GitHub errors and caller patch exceptions are still not caught (rule 9).

**Witnesses** (permanent):
- 7 YAML syntax failures: Codex's exact unclosed `[`, plus an unterminated quote, tab indentation, bad indentation, a `!!python/object` tag, an undefined alias, and a mixed sequence/mapping;
- each is run × the body boundary, the 4 read commands, `apply` + restore, and baseline refusal;
- plus a **raw-body-text totality property**: arbitrary text inside the fence, run against every entry point.

**Negative control:** at `290677bd`, **50 of the 50** new witnesses fail; all pass here.

**Gates:** 250 tool tests pass, coverage 100%, ruff and strict mypy clean. The totality properties pass at 3000 examples each.

**Convergence accounting:** this is the first targeted closure after the agreed revision-3 checkpoint, so §11.8.10 has not fired (as Codex noted).

---

## Checkpoint invalidation and revision 4 (`agent-workflow.md` §11.8.10)

- **Trigger.** PROC-L13-R003 failed **two** targeted closures after the revision-3 `AGREED FOR IMPLEMENTATION` checkpoint:
  1. at `290677bd`: invalid YAML inside a valid fence;
  2. at `e574d9f5` (`#204` comment `5924841709`): PyYAML's native scalar constructors raise a plain `ValueError`, e.g. `updated_reason: 2026-02-30` and `!!int not-an-int`.
- **Consequence.** The checkpoint is presumed inadequate. Implementation stopped. This revision returns to characterization and challenge, identifies the unmodeled root abstraction, and requests a new, explicit `AGREED FOR IMPLEMENTATION` before any more code. R001, R002 and R004 stay provisionally closed.

### Unmodeled root abstraction

Revisions 1–3 treated `yaml.safe_load` as a *parser* that fails only with `yaml.YAMLError` and yields JSON-like data. It is really a **constructor pipeline**:
- a resolver assigns implicit tags (YAML 1.1);
- per-tag constructors run arbitrary conversion code;
- the result can be any Python value those constructors produce.

Each review found one more class at that one boundary. The boundary itself was never modeled.

### Characterization: PyYAML 6.0.3 `SafeLoader`, constructor table and resolver

Probed directly, over every `SafeConstructor` tag (`null`, `bool`, `int`, `float`, `binary`, `timestamp`, `omap`, `pairs`, `set`, `str`, `seq`, `map`) plus the implicit resolvers:

| Class | Example | `safe_load` outcome |
|---|---|---|
| **E1: non-`YAMLError` exception** | `2026-02-30` (implicit timestamp), `!!int not-an-int`, `!!float abc` | `ValueError` |
| | `!!bool maybe` | `KeyError` |
| | 5000-deep `[[[…]]]` | `RecursionError` |
| **E2: non-JSON value** | `2026-02-28`, `2026-02-28 10:00:00` | `datetime.date` / `datetime.datetime` |
| | `!!binary aGk=`; `!!binary '@@@'` | `bytes`; invalid base64 **silently** yields `b''` |
| | `!!set {a: null}` | `set` |
| | `!!omap [a: 1]`, `!!pairs [a: 1]` | a list of `tuple`s |
| | `yes: 1`, `1: a`, `~: a` | non-string keys (`True`, `1`, `None`) |
| **E3: silent YAML 1.1 reinterpretation** | `x: no`; `x: 1:30`; `b: {<<: *A}` | `False`; `90` (sexagesimal); a merge-key splice |
| *(controlled already)* | unknown tag, a bad `!!omap`/merge/`!!str` on a map | `yaml.YAMLError` (`ConstructorError`) |

### Rules added to 1–9 (they replace nothing; rule 4 is made precise)

- **L1: the loader is total.** Any `Exception` raised while loading the fenced text is malformed **content** and becomes `BodyFormatError` with a diagnostic. `safe_load` runs no remote call and no caller patch, so rule 9's carve-outs cannot occur inside it. `BaseException`s that are not `Exception`s (`KeyboardInterrupt`, `SystemExit`) are not caught.
- **L2: the tree is closed over the JSON domain.** A loaded state must be, recursively, a mapping with **string keys**, a list, a string, an int, a float, a bool, or null. Anything else (date, datetime, bytes, set, tuple, or a non-string key) is a `BodyFormatError` naming the path and the type.
- **L3: no implicit YAML 1.1 reinterpretation.** The state block is loaded with a resolver restricted to the YAML 1.2 core / JSON schema:
  - **kept:** `null`/`~`/empty, `true`/`false`, decimal ints, floats (including `.inf`/`.nan`);
  - **not kept:** `yes`/`no`/`on`/`off`/`y`/`n` booleans, sexagesimal numbers, implicit timestamps, and the `<<` merge key. Those load as plain strings, or for `<<`, as a literal key.

  Explicit tags still construct their types, and then L2 rejects the non-JSON ones.

  This changes nothing for any body the tool writes: `yaml.safe_dump` quotes every string that YAML 1.1 would reinterpret. The live issues #35, #49, #50, #51, #95, #99 and #100 must still load to identical objects, and that is checked.
- **L4: write-side symmetry.** The existing pre-write round trip (`apply` refuses a state YAML cannot carry unchanged) runs with the same restricted loader, so what is written is exactly what is read.

### Acceptance witnesses, revision 4

All are RED at `e574d9f5` unless marked positive:
- **E1, every class:** each invalid-payload tag (`!!int`, `!!float`, `!!bool`, `!!timestamp`) and the implicit timestamp, plus deep nesting (`RecursionError`). Each is run × the body boundary, the 4 read commands, `apply` with that current state, repair of that current state (restoring a valid revision), and repair *to* that baseline (refused). Codex's exact witnesses are `2026-02-30` and `!!int not-an-int`.
- **E2, every non-JSON constructor result:** date, datetime, `!!binary` (including the silently decoded garbage), `!!set`, `!!omap`/`!!pairs`, and non-string keys (`yes:`, `1:`, `~:`, as top-level keys and nested). Each is run × the same entry points.
- **E3:** `no`/`yes`/`on`/`off`, `1:30` and an unquoted date load as **strings**, and `<<` is a literal key. A body using them in a control field, e.g. `next_owner: no`, therefore gets a string-shape diagnostic, not a silent bool.
- **Positive controls:**
  - every live issue body (#35 #49 #50 #51 #95 #99 #100) loads to an object identical to the previous loader's;
  - YAML anchors/aliases, as in #49's `&id001`, keep working;
  - quoted dates and quoted `"yes"` stay strings;
  - `.inf`/`.nan` floats load.
- **A grammar-based property** (Hypothesis): YAML text generated from a grammar mixing implicit scalars (date-like `DDDD-DD-DD`, `N:N`, yes/no/on/off, ints, floats, nulls), explicit tags from the full constructor table over random payloads, random keys of the same forms, nested sequences/maps up to large depth, and anchors/aliases. **Every** entry point stays total; whenever a load succeeds, the tree is JSON-domain (L2).
- **Discrimination:** the new witnesses run against `e574d9f5`, which must fail them, and the record will state the RED count.

### Checkpoint, revision 4

```text
CONVERGENCE CHECKPOINT
    PROPOSED FOR IMPLEMENTATION (revision 4, after section 11.8.10 invalidation)

OPEN FINDINGS
    PROC-L13-R003

ROOT ABSTRACTION ADDED
    the YAML load boundary as a constructor pipeline: L1 totality, L2 JSON-domain closure,
    L3 YAML 1.2 core resolver, L4 write/read symmetry

ACCEPTANCE WITNESSES
    E1/E2/E3 class tables x every entry point; live-body identity; grammar-based property; RED at e574d9f5

NORMATIVE DELTAS
    coordination-state.md section 13.5 gains L1-L4; minion-process-cli-design.md section 1.1 gains L1-L4

NEXT_OWNER
    Codex (checkpoint review; no implementation before APPROVED)
```

---

## Checkpoint revision 5: response to C-PROC-L13-01-04 / -05 (Codex, REJECTED at `8e73c8b5`)

- **Review:** `#204` comment `5925419210`, published verbatim on Codex's behalf.
- **Accepted:** both findings.
- **Unchanged:** the revision-4 root abstraction (the loader is a constructor pipeline) and L1/L3/L4, except where stated below.

### Missing dimension 1 (C-04), expanded to its neighborhood

The loaded **value**, not just the load, is part of the boundary. A successful load can yield a **cyclic graph**: `workflow: &W {history: *W}`, or `{history: &H [*H]}`. Expanding to every *recursive consumer* the tool runs **after** a load, probed directly:
- `copy.deepcopy` and `yaml.safe_dump` survive cycles (memoization), but raise `RecursionError` on a legal, *acyclic* 3000-level structure;
- the validator walk recurses;
- comparing two distinct cyclic graphs (the round-trip equality check) recurses without end.

So both **cycles** and **depth** are part of the boundary.

### Rules (replacing revision 4's L2; L1 extended)

- **L1′: controlled totality** covers loading **and** the post-load domain/graph check. Any `Exception` from either is a `BodyFormatError` with a diagnostic. Remote errors, caller patch exceptions and non-`Exception` `BaseException`s stay outside, as in rule 9.
- **L2′: an acyclic, depth-bounded JSON graph.** A loaded state is accepted only if it is an **acyclic** graph of JSON-domain nodes (mappings with string keys, lists, strings, ints, floats, bools, null) whose nesting depth is at most **`MAX_DEPTH = 64`**.
  - The check is **iterative**: an explicit stack, with no recursion of its own.
  - **Cycles:** a node reached again *on its own ancestor path* is a cycle and is rejected.
  - **Shared aliases:** a node shared across siblings (acyclic sharing, such as #49's `&id001`) is accepted.
  - **Why the bound is safe:** every recursive consumer the tool runs afterwards (`deepcopy`, `safe_dump`, the validator, equality) is then safe by construction. 64 exceeds any real state block's depth (live maximum: 6) with a wide margin.
- **L3 is unchanged:** a resolver restricted to the YAML 1.2 core / JSON schema. Its **consequences are now stated as outcomes**; see the split table.
- **L4 is unchanged:** write/read symmetry. The pre-write round trip also runs L2′, so no state deeper than 64 or cyclic is ever written.

### Witness table, split (C-05)

**Historical characterization (old `SafeLoader`; evidence only, not acceptance instruction):** see revision 4's E1/E2/E3 table.

**Intended outcomes under L1′–L4:**

| Input | Load outcome | Workflow validation | Repair: current state | Repair: as baseline |
|---|---|---|---|---|
| `updated_reason: 2026-02-30` (implicit) | **string** `"2026-02-30"` | valid (an optional string) | current is valid → repair refused; normal `apply` works | valid baseline → restorable |
| `work_package: 2026-02-30` | string | valid | as above | as above |
| `next_owner: no` | **string** `"no"` | **workflow error** (unknown owner) | current invalid → restorable from a valid revision | invalid baseline → refused |
| `yes: 1` (top-level key) | **string key** `"yes"` | valid (an extra key) | current valid → repair refused | valid → restorable |
| `x: 1:30` / `<<: …` | string `"1:30"` / literal key `"<<"` | valid if in a free field | as for valid | as for valid |
| `!!timestamp 2026-02-30` | **`BodyFormatError`** (E1: `ValueError` contained) | — | restorable from a valid revision | refused (does not parse) |
| `!!timestamp 2026-02-28` | **`BodyFormatError`** (L2′: date) | — | restorable | refused |
| `!!int not-an-int`, `!!float abc`, `!!bool maybe` | `BodyFormatError` (E1) | — | restorable | refused |
| `!!binary aGk=`, `!!binary '@@@'`, `!!set`, `!!omap`, `!!pairs` | `BodyFormatError` (L2′: bytes / set / tuple) | — | restorable | refused |
| `!!int 1: a`, `!!bool true: a`, `!!null '': a` (tagged keys) | `BodyFormatError` (L2′: non-string key) | — | restorable | refused |
| `workflow: &W {history: *W}` (self-map) | `BodyFormatError` (L2′: cycle) | — | restorable | refused |
| `workflow: {history: &H [*H]}` (self-list) | `BodyFormatError` (cycle) | — | restorable | refused |
| indirect cycle `a: &A {b: {c: *A}}` | `BodyFormatError` (cycle) | — | restorable | refused |
| acyclic shared alias `a: &A {x: 1}` + `b: *A` (and #49's real body) | **loads** (sharing accepted) | valid / as #49 | not repairable (valid) | restorable |
| depth 65 (acyclic) | `BodyFormatError` (L2′: depth) | — | restorable | refused |
| depth 64 (acyclic) | loads | valid if well-formed | — | — |
| 5000-deep `[[[…]]]` | `BodyFormatError` (L1′: `RecursionError` contained) | — | restorable | refused |
| an invalid YAML syntax class (revision-3 witnesses) | `BodyFormatError` | — | restorable | refused |

**For every row:**
- the read commands give a diagnostic and exit 1 when load or validation fails, and never a traceback;
- `apply` on a failing current state makes zero writes;
- the CLI `repair` exit codes match the table.

**The grammar-based property** keeps aliases, cycles and depth as explicit generator dimensions: it generates YAML with anchors and back-references, including self-, indirect and shared references, and depths around 64. The assertions are totality at every entry point, plus L2′ on every successful load.

**Negative control:** the record will report results **per intended outcome**, each row × entry point against `e574d9f5`, not as one collective count. Rows whose intended outcome the old candidate already met, e.g. a valid implicit-date string as `updated_reason`, are reported as such: they are regressions guarding L3, not RED witnesses.

### Checkpoint, revision 5

```text
CONVERGENCE CHECKPOINT
    PROPOSED FOR IMPLEMENTATION (revision 5)

OPEN FINDINGS
    PROC-L13-R003

ROOT ABSTRACTION
    load boundary = constructor pipeline (rev 4) + the loaded value is a graph:
    L1' totality over load AND post-load check; L2' acyclic, depth <= 64, JSON-domain, iterative check;
    L3 YAML 1.2 core resolver; L4 symmetry

ACCEPTANCE WITNESSES
    the split intended-outcome table x every entry point; graph/depth generator dimensions;
    per-outcome results against e574d9f5

NEXT_OWNER
    Codex (checkpoint review; no implementation before APPROVED)
```

---

## Implementation of revision 5 (after AGREED FOR IMPLEMENTATION, Codex `#204` comment `5925476157`)

**Mechanism** (`process/tools/minion_process/model.py`): `load_state` is now the single YAML entry, used by `split_body`, and through it by every read command, `apply` (current, intended, pre-write and remote) and repair (current and baseline).
- **L1′:** any `Exception` from loading or from the graph check becomes `BodyFormatError`.
- **L2′:** `_check_graph` is iterative, uses an explicit stack, and is memoized per node:
  - a cycle is a node met again on its own ancestor path;
  - string keys only, and JSON scalar types only;
  - container depth ≤ `MAX_DEPTH = 64`, counted from the root mapping as 1;
  - children are visited in document order.
- **L3:** `_StateLoader` uses only the YAML 1.2 core implicit resolvers, each a subset of the YAML 1.1 pattern `safe_dump` quotes against.
- **L4:** the pre-write round trip goes through the same loader.

**Live compatibility:** all seven live state bodies (#35 #49 #50 #51 #95 #99 #100) load to objects **identical** to the previous loader's, and round-trip.

### Two same-root additions, flagged for the targeted closure

Both were found by applying the neighborhood rule to the agreed post-load graph boundary. Codex may reject either as outside the checkpoint.

1. **Expanded-size bound** (`MAX_NODES = 100 000`, each shared alias counted per reference).
   - **The hazard:** an *acyclic* "alias bomb" loads instantly because PyYAML shares nodes, and `deepcopy`/`safe_dump` survive it through memoization. But **equality between two independently loaded graphs** (the remote round-trip check) walks the expansion. Measured on 9-way sharing: 6 levels take 0.0005 s, 8 levels 0.04 s, and 10 levels 3.55 s, about ×9 per level, so 14 levels would take hours.
   - **The bound:** it is computed from the memoized subtree sizes, in linear time. Live bodies expand to at most 362 nodes.
2. **A shared alias counts at its deepest reference.** A deep node anchored shallowly and referenced deeper exceeds the depth bound only through the memoized height, because the walk never re-descends it. The rule and its witness pin that L2′ is enforced on **every** path, not only the first one walked.

### Correction requested by the checkpoint review (non-blocking)

Revision 5's negative-control paragraph wrongly gave "a valid implicit-date string as `updated_reason`" as a row the old candidate already met. It did not: at `e574d9f5` the exact `2026-02-30` row raises `ValueError`, and an ordinary implicit date constructs a `date`. The classification below is **measured**, not taken from that example.

### Witnesses and per-outcome negative control

`process/tools/tests/test_ce_proc_l13_01_rev5.py`: 33 tests, all GREEN here. Against `e574d9f5`, using a scratch copy where `load_state` is routed through the old `split_body`:

| Outcome at `e574d9f5` | Rows / tests |
|---|---|
| **RED (24)** | `implicit-date-in-updated_reason`, `implicit-date-as-work_package-string` (old: `ValueError`); `tagged-invalid-timestamp`, `tagged-valid-timestamp`, `tagged-bad-int`, `tagged-bad-float`, `tagged-bad-bool`; `binary`, `binary-garbage`, `set`, `omap`, `pairs`; `tagged-int-key`, `tagged-bool-key`, `tagged-null-key`; `self-map-cycle`, `self-list-cycle`, `indirect-cycle`; `depth-65`, `deep-5000`; the depth convention; the alias-bomb bound; a shared alias at its deepest reference; the grammar-based property |
| **Regression guards: same observable outcome at both SHAs (9)** | `depth-64`, `shared-acyclic-alias`, `unclosed-flow` (already fixed at `e574d9f5`). Four L3 rows where the old loader's different *value* is not observable through any entry point: `yes-top-level-string-key` (a `True` key outside `workflow`), `sexagesimal-string` and `leading-zero-string` (ints in an unchecked field), and `merge-literal-key` (quoted). Plus `no-as-next_owner-string` (old `False`, new `"no"`: both invalid owners), and live-body compatibility |

**Gates:** 283 tool tests pass, statement coverage 100%, ruff and strict mypy clean. The grammar property and the alias tests also pass at 2000 examples.

**Status:** PROC-L13-R003 is REMEDIATED against the revision-5 agreement, pending Codex §11.8.7 targeted closure. R001, R002 and R004 stay provisionally closed. One §11.8.8 final complete review of #204 follows.
