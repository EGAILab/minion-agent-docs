# CE-L13-WP134-01: WP-13.4 Python convergence episode

- **Coordination:** `minion-agent#51`, status `CONTRACT_CONVERGENCE`.
- **Governance:** `standing_delegation: minion-agent#75`. This episode stays inside the Owner WP-13.4 decision (Q1 = A `DIV-002`, Q2 = A, Q3 = B) and proposes no new divergence.
- **Entry:** workflow §11.8 trigger A. `WP134-IMPL-R001` and `WP134-IMPL-R002` each survived two independent reviews:
  - implementation review 1 @ `5caed2f6`;
  - re-review 1 @ `f97906ca` (`minion-agent#153` issuecomment-5992624087).
- **Trigger B:** not separately fired; both refinements are the same-root neighbours named by the reviewer.
- **Trigger C:** not fired (no rejected complete contract review).
- **Characterization owner:** Claude, as the re-review returned the episode to the shared/Python owner (§11.8.3: "characterize those partitions and establish the checkpoint").
- **Independent checkpoint reviewer:** Codex.
- **Reviewed candidate (unchanged during characterization):** code `f97906ca279b551a6f1cc9ae1d3a902637a51e31`. No implementation code was written in this episode before the checkpoint.

## OPEN FINDINGS
| ID | Severity / taxonomy | State |
|---|---|---|
| `WP134-IMPL-R001` | high, `PI_PARITY_DEFECT` | OPEN: the abort observation window extends past engine completion |
| `WP134-IMPL-R002` | medium, `PI_PARITY_DEFECT` | OPEN: the Windows rewrite changes model-visible behaviour outside genuine recursive components |
| `WP134-IMPL-R003` | medium, `CONTRACT_ASSURANCE_DEFECT` | PROVISIONALLY CLOSED @ `f97906ca` (reviewer) |

## ROOT-CAUSE SURFACE
1. **R001: the completion boundary.**
   - Pi decides a search call's abort outcome at the child's `close` event: exit and both stdio ends.
   - `find` and `grep` remove their listener there. `find` settles synchronously; `grep` formats asynchronously with no listener.
   - The candidate decides after the asynchronous release of its local stream resources. That is a point Pi has no counterpart for, so an abort during release is reported as an abort.
   - This applies to **both tools**. The reviewer's witness covered `grep`; the characterization below shows `find` has the identical gap (§9.4 neighbourhood).
2. **R002: the wrong reading of the pattern.**
   - The candidate decides recursive components on the **original** pattern and distributes braces itself.
   - That rested on a false premise, recorded in the implementation record: "fd's glob has no nested alternation".
   - The pinned fd 10.4.2 accepts nested alternation, and on Windows it parses **Pi's rewritten text**, in which Pi's `[/\\]` can be absorbed into a user's class.
   - So the candidate:
     - corrects tokens fd never treats as recursive (`{x/**,y}/b`, `x/{**}/b`);
     - misses the alternative-start components fd does treat as recursive (`x/{a,{**/b}}`, `x{**/b}`);
     - turns Pi's errors into successes (`src/a}/**/…`);
     - exposes its own generated text in diagnostics (`src/[z-a]/**/…`).

## PI SYMBOLS / TESTS AUDITED
- `packages/coding-agent/src/core/tools/grep.ts` @ `b7bb00b9`:
  - `execute` pre-check at 163-166;
  - `ensureTool` / `isDirectory` awaits before spawn;
  - `spawn` at 226;
  - `cleanup` at 236-239, which removes the listener;
  - `onAbort` at 246-250, registered after spawn;
  - the `close` handler at 303-307: cleanup first, then the latched `aborted`;
  - async formatting after close at 321+.
- `packages/coding-agent/src/core/tools/find.ts` @ `b7bb00b9`:
  - pre-check at 142-145;
  - the listener at 156-160, registered before any await;
  - `settle` removes it;
  - the close handler: cleanup, `signal?.aborted`, then a synchronous settle;
  - the Windows `replaceAll("/", String.raw`[/\\]`)` (full-path branch).
- **Pinned fd 10.4.2 glob reading on Windows:**
  - no backslash escape;
  - class lexing (a leading `]` as a member, `!`/`^`);
  - nested alternation accepted;
  - an empty alternative never matches the empty string;
  - recursive `**` recognition. On Linux this is a `**` after a separator or at an alternative start, followed by a separator.

## OBSERVABLE RULES (normative text: `spec/tools.md`, WP-13.4, marked CE-L13-WP134-01)
1. **Engine completion:** the process has exited AND stdout and stderr have both reached end of input.
2. **`find`:**
   - an abort from the call's start (after the pre-check) until completion terminates the engine and settles `Operation aborted` at once;
   - the outcome is decided at completion, before any asynchronous stream release;
   - an abort after completion is not observed.
3. **`grep`:**
   - an abort before the listener exists (before spawn returns) is not observed, and rg is not stopped;
   - an abort from spawn's return until completion stops rg, and the call settles `Operation aborted` at completion, overriding a limit stop, exit code or matches;
   - an abort after completion (formatting, context re-reads) is not observed.
4. **Windows full-path `find`:** the pattern is judged as the pinned fd reads Pi's rewritten text.
   - A **recursive component** is a `**` (exactly two `*`) followed by a separator and preceded by a separator or by `{`/`,`. The pattern-initial one is excluded.
   - Recursive components keep the zero-or-more meaning, so the results equal Linux's (`DIV-002`).
   - Everything else keeps Pi's Windows meaning: F-2 crossing, non-component `**`, class constructs Pi's rewrite reshapes, no escapes.
5. **Engine-rejected Windows patterns:** the result is fd's diagnostic for Pi's own rewritten text, verbatim. Generated text never appears.

## BEHAVIOR MATRIX

### R001: abort point x tool
Evidence:
- `data/13-wp134-ce01/abort-partition-pi.json`: pinned Pi, the unmodified execute bodies via the committed harness prefix, a scripted Node child;
- `abort-partition-candidate-f97906ca.json`: the candidate, with a scripted Minion process.

| Abort point | Pi `find` | Pi `grep` | Candidate `find` | Candidate `grep` |
|---|---|---|---|---|
| during spawn (before grep's registration) | aborted | **result** | aborted | result |
| after the result line | aborted | aborted | aborted | aborted |
| after stdout EOF | aborted | aborted | aborted | aborted |
| after stderr EOF (not exited) | aborted | aborted | aborted | aborted |
| after exit, before `close` | aborted | aborted | aborted | aborted |
| after completion: stdout release | **result** | **result** | aborted ✗ | aborted ✗ |
| after completion: stderr release | **result** | **result** | aborted ✗ | aborted ✗ |

There is one more row, documentary from source:

| Abort point | Pi `find` | Pi `grep` | Candidate |
|---|---|---|---|
| during `grep` context re-reads / formatting | n/a | result (listener removed at 304) | result |

### R002: pattern x platform
Evidence: `data/13-wp134-ce01/glob_matrix.py`, run on Windows and Linux with the pinned fd over a 12-file corpus, giving `glob-matrix-{win32,linux}.json`. It has 41 rows, with these columns:
- Linux, Pi's text as passed on Linux;
- Pi Windows;
- the candidate @ `f97906ca`;
- the rejected design (recursive components decided on the original pattern);
- the proposal (rule 4, decided on Pi's text).

| Outcome | Rows |
|---|---|
| proposal = Linux (`DIV-002` applies or Pi = Linux already) | 35 |
| proposal = Pi Windows only, the Pi-scope rows: `src/*.spec.ts`, `x/**b`, `src/[]/**/…`, `src/[!]/**/…`, `src/[/**/…`, `x\/**/b` | 6 |
| proposal outcome class differs from both | 0 |
| rejected rows whose diagnostic text differs from Pi's (`[z-a]`, `{a/**/…`, `a}/**/…`) | 3, closed by rule 5 |
| **candidate @ `f97906ca` wrong** (result or diagnostic) | **11** |

The 11 candidate failures:
- missed recursive components:
  - `src/{a,{b}}/**/b.spec.ts`;
  - `x/{a,{**/b}}`;
  - `x{**/b,c}`;
  - `x{**/b}`;
  - `x/a{**/b,c}`;
  - `x/{a,b{**/c}}`;
- over-corrected non-components: `{x/**,y}/b`, `x/{q/**,nope}/b`, `x/{**}/b`;
- generated text in a diagnostic: `src/[z-a]/**/b.spec.ts`;
- error turned into success: `src/a}/**/b.spec.ts`.

The rejected design breaks the three class-reshaped rows. It is recorded so the checkpoint can see why rule 4 reads Pi's text.

**Canonical authority.** The harness `components` mode gained 14 classified cases over the plain corpus, giving 19 in all, run on both platforms into `out/components-{win32,linux}.json`:
- 5 alternative-start forms;
- `***`;
- 2 non-component `**` forms;
- 3 class-reshaped forms;
- 3 engine-rejected forms.

Each new case carries `expectWin32: "div002" | "pi"`.

## MINIMAL EXECUTABLE WITNESSES (to become permanent with the implementation)
1. **R001, both bindings.**
   - One witness per cell of the R001 matrix for `find` and `grep`: 14 cells, with expectations taken from `abort-partition-pi.json`.
   - Each uses a scripted in-process engine whose stream and wait operations abort the call at the named point.
   - The after-completion cells are the discriminating ones. The candidate fails all four.
2. **R002, shared canonical.**
   - The 19 `components` scenarios, with Windows expectations per classification: `div002` takes the Linux result, `pi` takes Pi's Windows result or diagnostic.
   - This needs a generator rule keyed on `expectWin32`; the first five keep today's rule.
3. **R002, binding.** The rewrite helper's unit witness over the full 41-row matrix's Windows texts: `proposal` outcome, or Pi text where rule 4 keeps it.

## NEGATIVE CONTROLS (to be added to `wp134_search_negative_controls.py`, each killed only by its intended witness)

| Control | Intended witness |
|---|---|
| decide `find`'s outcome after stream release (the candidate's shape) | `find` after-completion cells |
| decide `grep`'s outcome after stream release (the candidate's shape) | `grep` after-completion cells |
| `grep` observes an abort before its registration | `grep` "during spawn" cell |
| recursive components decided on the original pattern (rejected design) | `class-reshaped-negated` (Windows) |
| alternative-start `**` not recursive | `alt-start-doublestar` |
| diagnostics produced from the generated text | `rejected-invalid-range` (Windows) |
| zero-directory form written as an empty alternative | `brace-alternative-doublestar` |
| literal-wrapping an unmatched `}` (the candidate's shape) | `rejected-unopened-brace` (Windows) |

The existing 24 controls remain, re-anchored as needed.

## CURRENT CANDIDATE FAILURES (`f97906ca`)
- R001: 4 of 14 partition cells (both tools, after completion).
- R002: 11 of 41 matrix rows on Windows.
- R003: none; it stays provisionally closed.

## SPEC / MANIFEST / CONFORMANCE DELTAS
- **`spec/tools.md` WP-13.4 (in this docs head):**
  - find step 6: the abort window and the completion boundary;
  - grep step 7: the three-way abort partition;
  - "Recursive components and Pi-scope constructs";
  - extra `DIV-002` required witnesses;
  - the errors-table row for engine-rejected Windows patterns.
- **Harness:** `data/13-wp134/harness/search_probe.mjs` `components` cases, plus outputs. The default run is unchanged.
- **Manifest (with the implementation):**
  - `TOOL-036` / `TOOL-036-DIV-002` tests lists name the new scenarios and this episode;
  - `TOOL-037` names the abort-partition witnesses.
  No rule text change beyond referencing CE-L13-WP134-01.
- **Conformance (with the implementation):**
  - the generator reads `expectWin32`;
  - 14 new scenarios, about 210 in total;
  - the scenario `notes` record Pi's Windows result for `div002` rows.

## IMPLEMENTATION CONSTRAINTS (language-neutral)
- **Completion boundary.** The completion boundary is observable to the tool's decision logic before stream release. Neither tool consults the signal for its outcome after completion. Stream release stays unconditional (spec/execution.md §16) and is not otherwise changed. No Layer-12 contract is reopened.
- **`find` immediate settle.** `find`'s immediate settle on abort applies only inside its window. A binding that races the abort must stop racing at completion.
- **Reading Pi's text.** The rewrite reads Pi's text with the pinned fd's lexing on Windows. It may use any construction fd evaluates to the Linux result for rule-4 components, for example:
  - `SEP ** SEP` → `{SEP,SEP**SEP}`;
  - an alternative-start `** SEP rest` → `**SEP rest,rest`.
  An empty alternative must not be relied on.
- **Rule 5.** Rule 5 may be met by re-running fd with Pi's text when the corrected text is rejected (non-zero exit with no output), or by any equivalent that yields the identical result.
  - The characterized constructions keep fd's accept/reject outcome identical to Pi's text in all 41 rows.
  - A re-run on a non-pattern failure (for example, a search path that is not a directory) reproduces the same error.
- **Expansion size.** Alternative-start duplication doubles that alternative's text per nested alternative-start level. No bound is proposed; pathological nesting depth is out of scope.

## OUT-OF-SCOPE / DEFERRED
- Escape semantics (`x\/**/b`): Windows has none; Linux does. This is a platform fact governed by Pi's Windows text, not `DIV-002`.
- `bash` (WP-13.3) settlement: certified, separate surface, not reopened.
- Rust: begins only after the shared/Python contract is approved and merged (§11.8.9).

## CONVERGENCE CHECKPOINT

```text
CONVERGENCE CHECKPOINT
    PROPOSED FOR IMPLEMENTATION

EPISODE
    CE-L13-WP134-01

OPEN FINDINGS
    WP134-IMPL-R001, WP134-IMPL-R002   (WP134-IMPL-R003 PROVISIONALLY CLOSED @ f97906ca, unaffected)

ACCEPTANCE WITNESSES
    data/13-wp134-ce01/abort-partition-pi.json         (14 cells; binding witnesses per cell, both tools)
    data/13-wp134-ce01/glob-matrix-{win32,linux}.json  (41 rows; rewrite helper witness)
    data/13-wp134/out/components-{win32,linux}.json    (19 classified canonical cases)
    the negative controls listed above

NORMATIVE DELTAS
    spec/tools.md WP-13.4 (CE-L13-WP134-01 passages, this docs head)
    harness components mode (this docs head)
    manifest TOOL-036/TOOL-036-DIV-002/TOOL-037 tests lists and the conformance generator (with the implementation)

NEXT_OWNER
    Codex (checkpoint review of exactly this proposal)
```

---

## Checkpoint review 1 (Codex): REJECTED

- **Reviewed proposal:** docs `a7acf903`.
- **Verdict:** published verbatim on `minion-agent-docs#248` (issuecomment-5992972939).
- **Missing dimension, `CE-L13-WP134-01-C001`** (medium, `CONTRACT_ASSURANCE_DEFECT`): the composition of a recursive component with a retained Pi-scope construct in one pattern.
  - Rule 4 said both "the Windows result equals Linux's" and "everything else keeps Pi's meaning". For `src/**/a*.ts` these cannot both hold.
  - A `div002` selector that copies the whole Linux result cannot express the composition, and expectations must not come from the proposal's own construction.
- **Confirmed by the reviewer:**
  - R001: the partition, both tools, with all 14 cells and the 4 candidate failures reproduced;
  - R002: the lexical characterization and the diagnostic rule, with the 41-row and 19-case outputs reproduced exactly;
  - no lower layer is reopened.

## Revision 1 (C001)

**Composition rule (component-local).** Every recursive component keeps its zero-or-more meaning, and nothing else changes.
- The Windows result is the **union**, over every keep/remove choice of each recursive component (removing exactly its `**/`), of **Pi's own Windows result** for the resulting pattern.
- It equals Linux's result exactly when no retained Pi-scope construct is composed with a component.
- This is the reading the Owner's DIV-002 scope already states ("only the zero-directory meaning of `**/` changes; every other construct keeps exactly Pi's Windows meaning"). It needs no new Owner decision.
- The spec and the DIV-002 disclosure now state it explicitly (`spec/tools.md` WP-13.4; `assurance/pi-divergences.md` DIV-002 "Composition").

**Independent oracle.** `data/13-wp134-ce01/glob_matrix.py` gained an `oracle` column, derived from Pi's rewrite only:
- if fd rejects Pi's text, the outcome is Pi's;
- otherwise it is the union of fd's results for Pi's rewrite of every keep/remove variant.

Components are located by rule 4. Results never come from the construction.

The matrix now has **49 rows**: 8 mixed rows, including the reviewer's exact three-file witness `src/**/a*.ts` and `src/[!]/**/x/**/b.ts`, plus 6 corpus files.

| Measure (fresh, both platforms) | Result |
|---|---|
| proposal outcome = oracle | **49 / 49** (the 3 rejected rows' raw diagnostics differ, which rule 5 closes: Pi's diagnostic) |
| oracle = Linux | 37; the 12 others are the 6 Pi-scope rows and the 6 mixed rows |
| reviewer witness `src/**/a*.ts` | Pi Windows `src/sub/a.ts`; oracle = proposal `src/a.ts`, `src/a/sub/b.ts`, `src/sub/a.ts`; Linux `src/a.ts`, `src/sub/a.ts` |
| candidate `f97906ca` != oracle (results or diagnostics) | 11, as before; it passes the mixed rows, being component-local itself |

**Canonical authority (harness `components` mode).**
- The 25 cases run over the plain corpus plus `COMPONENT_FILES` (5 files) and are keyed `components/<name>`.
- Each non-`pi` case lists its keep/remove variants **by hand**. On Windows the harness records the union of pinned Pi's results for them (`windowsUnion`), and `linux: true|false` states the expected relation to Linux.
- All 25 relations hold on the fresh Windows and Linux runs. There are 6 mixed cases:
  - star crossing, in a brace, at an alternative start, and after a component;
  - class then component;
  - component then class.
- **Generator delta (with the implementation):**
  - a `pi` case uses Pi's Windows observation;
  - a union case uses `windowsUnion` for unlimited results;
  - the generator asserts `windowsUnion == linux` where `linux: true`;
  - a new corpus kind `components` = plain + `COMPONENT_FILES`.

**Controls added to the plan.** Both of the reviewer's plausible wrong choices are killed by `components/mixed-star-crossing` (Windows):

| Control | Wrong result |
|---|---|
| zero-directory left broken (Pi's text) | `src/sub/a.ts` only |
| whole-pattern Linux conversion | `src/a.ts`, `src/sub/a.ts`, missing `src/a/sub/b.ts` |

## CONVERGENCE CHECKPOINT (revision 1)

```text
CONVERGENCE CHECKPOINT
    PROPOSED FOR IMPLEMENTATION   (revision 1, superseding the proposal at a7acf903)

EPISODE
    CE-L13-WP134-01

OPEN FINDINGS
    WP134-IMPL-R001, WP134-IMPL-R002 (incl. CE-L13-WP134-01-C001)   (WP134-IMPL-R003 PROVISIONALLY CLOSED @ f97906ca)

ACCEPTANCE WITNESSES
    data/13-wp134-ce01/abort-partition-pi.json            (14 cells; binding witnesses per cell, both tools)
    data/13-wp134-ce01/glob-matrix-{win32,linux}.json     (49 rows incl. the independent oracle column)
    data/13-wp134/out/components-{win32,linux}.json       (25 classified canonical cases, 6 mixed; windowsUnion)
    negative controls: the earlier plan plus "zero-directory left broken" and "whole-pattern Linux conversion"

NORMATIVE DELTAS
    spec/tools.md WP-13.4 CE-L13-WP134-01 passages incl. the composition rule (this docs head)
    assurance/pi-divergences.md DIV-002 "Composition" clarification (this docs head)
    harness components mode with hand-written union variants (this docs head)
    manifest tests lists and the conformance generator / corpus kind (with the implementation)

NEXT_OWNER
    Codex (checkpoint review of exactly this revision)
```

---

## Checkpoint review 2 (Codex): REJECTED

- **Reviewed proposal:** revision 1 @ docs `eb486836`.
- **Verdict:** published verbatim on `minion-agent-docs#248` (issuecomment-5993144178).
- **C001 (composition):** resolved for checkpoint purposes, within Owner Q1 / DIV-002.
- **Missing dimension, `CE-L13-WP134-01-C002`** (medium, `CONTRACT_ASSURANCE_DEFECT`): a literal comma outside braces versus a comma that begins a brace alternative.
  - The oracle's component finder took every `,` as an alternative start.
  - For `x,**/b` it unioned the unauthorized branch `x,b`, while Pi, Linux and the construction all give `x,q/b`.
  - Its independence from the construction was sufficient for the submitted cases but did not validate the component predicate itself.

## Revision 2 (C002)
- **Context-aware lexing.** `,` and `}` are syntax only inside an open brace group; outside braces they are ordinary characters. This applies to `glob_matrix.py` `lex`, which both the oracle's finder and the proposal construction use.
- **Spec.** The recursive-component definition now says it explicitly, with the `x,**/b` / `x,{**/b}` pair.
- **Independent validation of the finder.** `EXPECTED_COMPONENTS` gives every matrix row's recursive-component count, counted **by hand** from rule 4 and not by the finder. Each row records `components: {expected_by_hand, found, agree}`. All 54 rows agree.
  - The pre-revision finder disagrees on `x,**/b` and `x,**/b{a,b}` (1 instead of 0). That is the reviewer's failure.
- **Matrix.** It has 54 rows: the comma witnesses `x,**/b`, `x,{**/b}`, `x,**/b{a,b}`, `{x,**/b}` and `x}/**/b`, plus the corpus files `x,b` and `x,q/b`.

  | Measure (fresh, both platforms) | Result |
  |---|---|
  | proposal outcome = oracle | **54 / 54**. The rejected rows' raw diagnostics differ; rule 5 closes them with Pi's diagnostic |
  | oracle = Linux | 42; the 12 others are the 6 Pi-scope and 6 mixed rows |
  | finder = hand counts | 54 / 54 |
  | `x,**/b` | Pi = Linux = proposal = oracle = `x,q/b` |
  | `x,{**/b}` | Pi `x,q/b`; Linux = proposal = oracle = `x,b`, `x,q/b` |

- **Canonical authority.** The harness `components` mode has 28 cases. The new ones are:
  - `comma-literal` (`pi`);
  - `comma-literal-before-brace` (`pi`);
  - `comma-then-brace-alt-start` (union `x,{**/b}`, `x,{b}`; equals Linux).

  `COMPONENT_FILES` gains `x,b` and `x,q/b`. All 28 relations hold on fresh Windows and Linux runs.
- **Control added to the plan:** "every comma is an alternative start". It is killed by `components/comma-literal` on Windows: the construction or oracle adds `x,b`.

## CONVERGENCE CHECKPOINT (revision 2)

```text
CONVERGENCE CHECKPOINT
    PROPOSED FOR IMPLEMENTATION   (revision 2, superseding revision 1 at eb486836)

EPISODE
    CE-L13-WP134-01

OPEN FINDINGS
    WP134-IMPL-R001, WP134-IMPL-R002 (incl. C001 resolved-for-checkpoint, C002)
    (WP134-IMPL-R003 PROVISIONALLY CLOSED @ f97906ca)

ACCEPTANCE WITNESSES
    data/13-wp134-ce01/abort-partition-pi.json            (14 cells; binding witnesses per cell, both tools)
    data/13-wp134-ce01/glob-matrix-{win32,linux}.json     (54 rows; independent oracle; hand-counted components)
    data/13-wp134/out/components-{win32,linux}.json       (28 classified canonical cases; windowsUnion)
    negative controls: the earlier plan + "zero-directory left broken", "whole-pattern Linux conversion",
                       "every comma is an alternative start"

NORMATIVE DELTAS
    spec/tools.md WP-13.4 CE-L13-WP134-01 passages (composition rule; brace-alternative context)
    assurance/pi-divergences.md DIV-002 "Composition" clarification
    harness components mode
    manifest tests lists, conformance generator and corpus kind (with the implementation)

NEXT_OWNER
    Codex (checkpoint review of exactly this revision)
```

---

## Checkpoint review 3 (Codex): APPROVED; AGREED FOR IMPLEMENTATION

- **Reviewed proposal:** revision 2 @ docs `e985a008`.
- **Verdict:** published verbatim on `minion-agent-docs#248` (issuecomment-5993289268).
- **Outcome:** C001 and C002 resolved for checkpoint purposes. The control record became `CONVERGENCE CONTRACT — AGREED FOR IMPLEMENTATION` (workflow §11.8.5 step 3, recorded on `#51`).
- **Non-blocking wording note:** "`,` or `}` outside any brace group is an ordinary character" overstated the case for an unmatched `}`, which the pinned fd rejects. Fixed in `spec/tools.md` (this head): a literal `,` is ordinary; an unmatched `}` is engine-rejected, so the rejected-pattern rule gives Pi's diagnostic.

## Convergence implementation (§11.8.6)
- **Candidate:** code `minion-agent#153` @ `5730ff101ee377bc67302d3ed923666abf50e876`. The docs head is this PR's next head.

**R001: the abort window ends at engine completion.**
- `_search.AbortWindow` models Pi's listener lifetime. `EngineRun.run(on_line, on_complete)` calls `on_complete` at exit plus EOF on both pipes, synchronously and before the asynchronous release of the streams. The window latches there.
- **`find`:**
  - its window opens at the call's start, after the pre-check;
  - its own race (`_race_window`) answers an in-window abort at once, leaving the work to stop the engine;
  - it stops racing once the window has closed.
- **`grep`:** its window opens at spawn's return. An abort before that is never observed.
- `race_abort` (WP-13.1 `read`/`ls`, certified) is untouched.

**R002: the Windows rewrite reads Pi's text as fd does.**
- `find._lex` is context-aware:
  - classes may absorb Pi's `[/\\]`;
  - `,` and `}` are syntax only inside braces;
  - there is no backslash escape.
- `find._windows_full_path` changes only recursive components:
  - `SEP ** SEP` → `{SEP,SEP**SEP}`, with adjacent components collapsing;
  - an alternative-start `** SEP rest` → `** SEP rest,rest`.
- **Rule 5:** when the corrected pattern is rejected (non-zero exit, no output), fd runs again with Pi's text, and that outcome stands. The abort window spans both runs.
- On all 54 matrix rows the implementation's text equals the agreed construction's (byte for byte), and its outcome equals the independent oracle.
- **Bug found and fixed before review:** the first wiring keyed the re-run on the abort window being open, so a call **without a signal** never re-ran. The re-run decision is now recorded at completion independently of the window. Witness: `test_a_rejected_corrected_pattern_reports_pis_diagnostic`, which calls without a signal.

**Conformance.**
- The generator reads the harness `components` cases with their classification: a `pi` case keeps Pi's Windows observation; a union case takes `windowsUnion`. Where `linux: true` it asserts the union equals Linux; where `linux: false`, that it does not.
- 28 scenarios in corpus kind `components` (the plain corpus plus `COMPONENT_FILES`), 219 scenarios in all. 15 `components` scenarios carry `TOOL-036-DIV-002` with Pi's Windows result in `notes`.

**Negative-control evidence (§11.8.7.1).**
- Method: `scripts/wp134_search_negative_controls.py` at `5730ff10`.
- Controls: 32 single-point mutants, 12 of them new or re-targeted for this episode.
- A control counts only when its intended witness fails, with collection and setup errors rejected.
- Results: `data/13-wp134-ce01/controls-{win32,linux}-5730ff10.json`.

| Finding | Control (known-bad mutation) | Expected failure | Observed (Windows / Linux) |
|---|---|---|---|
| R001 | `find_decides_after_release` | `find` after-completion cells give `Operation aborted` | killed by `partition[stdout_close-find]`, `[stderr_close-find]` / same |
| R001 | `grep_decides_after_release` | `grep` after-completion cells give `Operation aborted` | killed by `partition[stdout_close-grep]`, `[stderr_close-grep]` / same |
| R001 | `grep_latch_lost_at_completion` | an in-window abort unseen by the poller gives the match | killed by `test_grep_keeps_an_abort_…`, `partition[stdout_data-grep]` / same |
| R001 | `grep_observes_pre_registration_abort` | an abort during spawn aborts | killed by `partition[spawn-grep]`, `test_grep_ignores_…` / same |
| R002 | `zero_directory_left_broken` (Pi's text) | `src/**/a*.ts` misses two files | killed by the unit witness and the `mixed-star-crossing` and `full-path-spec` scenarios / unit |
| R002 C001 | `whole_pattern_linux_conversion` | `src/a/sub/b.ts` dropped | killed by `mixed-star-crossing` / n/a (Windows-only witness) |
| R002 | `alt_start_not_recursive` | `src/{**/b.spec.ts,none}` misses the direct file | killed by the unit witness and `alt-start-doublestar` / unit |
| R002 | `adjacent_components_not_collapsed` | wrong text for `**/**/` | killed by the unit witness / unit |
| R002 | `empty_alternative_zero_form` | the direct file is missed | killed by the unit witness and `brace-alternative-doublestar` / unit |
| R002 | `lex_original_pattern` (the rejected design) | the reshaped class is corrected | killed by the unit witness / unit |
| R002 rule 5 | `diagnostics_from_corrected_text` | generated text in the diagnostic | killed by `test_a_rejected_corrected_…` and `rejected-invalid-range` / unit |
| R002 | `literal_brace_wrapping` (the `f97906ca` shape) | an unmatched `}` turns Pi's error into a success | killed by `rejected-unopened-brace` / n/a |

- **Known-bad SHA check.** The same witnesses run against `f97906ca`'s source fail exactly on the 4 after-completion partition cells (R001). Against that source the R002 matrix rows already recorded in this episode fail: 13 of 54.
- **"Every comma is an alternative start".** This mutation is **not observable in the binding.** The construction rewrites an alternative-start component only when the alternative closes at depth 0, so a stray comma is never rewritten. Its discriminating witness is the characterization's hand-counted `EXPECTED_COMPONENTS` check of the oracle finder. The reviewer's checkpoint-3 replay of the rejected revision-1 source showed it failing there. The canonical `comma-literal` scenarios guard the binding's outcome.

**Fresh gates at `5730ff10`.**

| Gate | Result |
|---|---|
| Windows full suite, warning-strict, pinned ICU 78.3, engines provisioned | 4973 passed, 31 skipped, 19 xfailed; 100.00% coverage |
| Linux full suite (`python:3.13`, tree copied into the container), warning-strict | 4907 passed, 97 skipped, 19 xfailed |
| `ruff check .` / `mypy src tests/typing` | clean / clean (113 source files) |
| Negative controls | Windows 32/32 killed by the intended witness; Linux 29/29, with 3 not applicable (Windows-only witnesses) |
| Abort partition, all 14 cells | equal to pinned Pi (`abort-partition-pi.json`) |
| Glob matrix, 54 rows (`glob_matrix.py` with the candidate column) | outcome = oracle 54/54; text = agreed construction 54/54 |

**Previously closed findings re-run (§11.8.6).**
- R003's comparator controls pass at `5730ff10`.
- The earlier 20 controls (R001-R003 and the original WP-13.4 list) are all killed.

## Status
- `WP134-IMPL-R001` and `WP134-IMPL-R002`: implemented at `5730ff10`; ready for targeted convergence closure review (§11.8.7).
- `WP134-IMPL-R003`: PROVISIONALLY CLOSED @ `f97906ca`; unaffected.
- Rust WP-13.4: NOT_IMPLEMENTED. Cross-language: NOT CLOSED.
