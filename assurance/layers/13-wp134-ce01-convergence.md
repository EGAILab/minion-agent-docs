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
