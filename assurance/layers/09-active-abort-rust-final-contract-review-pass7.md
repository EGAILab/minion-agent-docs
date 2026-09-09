# Layer 09 active abort — final independent Rust contract review (PASS 7)

## Verdict

**REJECTED FOR RUST IMPLEMENTATION.**

The exact candidate reviewed was:

- code PR `EGAILab/minion-agent#17` at `ef23829a9a7acf4033df7a9186a810c41433ad64`;
- docs PR `EGAILab/minion-agent-docs#26` at `633f6a82822e82705a5fe956dad28bd4c0ce4acb`;
- pinned Pi at `b7bb00b936dbe21b8e160b3e89efdec361846699`.

Both candidate commits were fetched from GitHub and reviewed in detached worktrees. Issue
`EGAILab/minion-agent#16` recorded those exact heads, `STATUS = RUST_CONTRACT_REVIEW`, and
`NEXT_OWNER = Codex`. Both PRs were open, ready for review, and unmerged when this review
began. Historical convergence and targeted-review evidence remains separately preserved in
docs PR #32 at `e7557739cb99c08168d8f9b8344ad01f54348cce`.

This is the workflow §11.8.8 final complete review. It does not modify either candidate,
Python, shared semantics, or Rust production.

## Authority and source audit

The review used the required order: pinned Pi, normative specification, parity manifest,
canonical evidence, certified Rust architecture, assurance, then Python only as secondary
implementation evidence.

Pinned Pi files and symbols inspected directly:

- `packages/agent/src/agent.ts`: `ActiveRun`, `Agent.signal`, `abort`, `prompt`, `continue`,
  `runWithLifecycle`, `handleRunFailure`, `finishRun`, and `processEvents`;
- `packages/agent/src/agent-loop.ts`: loop continuation, context transformation, assistant
  streaming, sequential and parallel tool execution, preflight, execution updates, and
  after-tool hooks;
- `packages/agent/src/types.ts`: abort-aware request, hook, tool, and lifecycle types;
- relevant pinned tests for active signal identity, abort, prompt/continue, and
  `prepareNextTurn`/`shouldStopAfterTurn` signal delivery.

The Pi source confirms the already-agreed core contract:

- one controller is installed before streaming status is published and one read-only signal
  is observed for the run;
- only `Agent.abort()` owns cancellation authority;
- abort is cooperative and every consumer may ignore it;
- transform-context, provider stream, before/after tool hooks, tool execution,
  `prepareNextTurn`, and `shouldStopAfterTurn` observe the same run signal;
- tool preflight priority and sequential/parallel abort polling follow the checkpoint rules;
- failure settlement uses the signal state at settlement and the live persistent Agent model;
- final cleanup occurs after failure/event settlement.

## Prior finding ledger

| Finding | Final-review result | Evidence |
|---|---|---|
| L09-C001 | CLOSED | Sequential and parallel batch algorithms remain separately specified and implemented. |
| L09-C002 | CLOSED | Six-way preflight outcome priority remains aligned with Pi. |
| L09-C003 | CLOSED | Consumer matrix, ignored-signal rule, and terminal distinctions remain present. |
| L09-R001 | CLOSED | Tool listener helpers and raw seams receive authoritative signal metadata. |
| L09-R002 | CLOSED | Failure stop reason is selected from the live signal at settlement. |
| L09-R003 | CLOSED | All four tool update/signal capability combinations remain representable. |
| L09-R004 | CLOSED | Consumers receive a read-only signal; active authority is retained by the Agent. |
| L09-R005 | CLOSED | Transform-context has an abort-aware, run-local seam. |
| L09-R006 | CLOSED | Signal is restored as authoritative metadata at affected waterfall boundaries. |
| L09-R007 | **REOPENED BY L09-R013** | The agreed failed-entry exactly-once guarantee is violated by a re-entrant observer that claims and then throws. |
| L09-R008 | CLOSED | Recommended after-tool helper can deliver the signal without breaking legacy hooks. |
| L09-R009 | CLOSED | Superseded signal-authority prose is clearly historical in the repaired locations. |
| L09-R010 | CLOSED | The unrestricted public restoration operation was removed. |
| L09-R011 | CLOSED AS WRITTEN | Exact-prefix verification prevents the original unrelated-front deletion witness, but does not close the distinct partial-prefix duplication in L09-R014. |
| L09-R012 | **STILL OPEN** | AG-011's current manifest rule still says removal is “by count from the front,” contradicting current code and spec. |

## Requirement and traceability audit

| Row | Pi/shared rule | Evidence status | Rust ownership / result |
|---|---|---|---|
| AI-027 | Request carries cooperative signal | Python language evidence; placeholder canonical not counted | Additive typed LLM request field; independently feasible. |
| AG-007 | One signal per run, abort authority, settlement, consumer propagation | Extensive Python language evidence | Typed controller/view and run lifecycle; feasible, but candidate blocked below. |
| AG-023 | Failed RUNNING notification is atomic and entering input remains exactly once | Python evidence is incomplete for destructive re-entrancy | **FAIL: L09-R013/L09-R014.** |
| AG-011 | Inbox queue and claim invariants | Canonical and language evidence | **FAIL: manifest rule contradicts current invariant.** |
| TOOL-024 | Authoritative signal through hooks and execution | Python language evidence | Existing Rust Layer-06 signal seam is suitable. |
| TOOL-009 | Tool capability vocabulary | Existing lower-layer evidence | Current prose is stale after Layer 09; see L09-R016. |
| TOOL-018 | Execution signal boundary reserved in Layer 06 | Existing Rust evidence | Layer 09 can activate it without redesign. |
| PROV-004 | Transport-level cancellation deferred | Explicit defer | Correctly remains later provider work. |

The manifest parses as 79 rows with 79 unique requirement IDs. Structural validity does not
override the semantic contradictions described below.

## Canonical evidence

The three Layer-09 canonical files remain explicitly unfilled placeholders:

- `active-abort-tool.yaml`;
- `active-abort-provider.yaml`;
- `abort-settles-before-idle.yaml`.

Neither manifest nor assurance improperly counts them as executed evidence. The candidate
instead relies on explicit Python language tests for listener-driven behavior. That evidence
policy was previously accepted and is not itself a blocker. No canonical runner was found
simulating abort semantics.

## New blocking findings

### L09-R013 — failed-entry re-entrant claim loses selected input

Classification: **CONTRACT_ASSURANCE_DEFECT**.

The agreed convergence rule says a failing RUNNING-status notification does not lose or
duplicate the input inspected for entry, and a later attempt observes that input exactly
once. PASS 6 changed entry from destructive claim-and-restore to peek-then-commit, but the
observer itself retains public access to destructive `Inbox.claim()`.

Executable witness against the exact code candidate:

1. queue steering envelopes A then B;
2. configure the entering claim as `ALL`;
3. a RUNNING status observer claims A with `ONE_AT_A_TIME`, then raises;
4. `continue_()` propagates that exception;
5. after rollback, A is absent and only B remains.

Observed result: `A_retained = false`, `B_retained = true`, pending queue `[B]`.

The observer's destructive re-entrancy occurs before the run is validly entered, yet the
outer rollback cannot restore it. This contradicts the approved failure-atomicity contract
and reopens L09-R007's observable guarantee.

Required remediation: define and implement a private linear reservation/transaction (or an
equivalent mechanism) that covers destructive re-entrant queue mutation during entry. A
failing entry must retain every inspected envelope exactly once, preserve identity/order,
and must not expose an unrestricted public restore/insertion capability.

### L09-R014 — partial-prefix re-entrancy duplicates selected input

Classification: **CONTRACT_ASSURANCE_DEFECT**.

PASS 7 correctly prevents deleting an unrelated envelope when the queue's complete front no
longer exactly matches the peeked batch. That all-or-nothing check creates the complementary
duplication defect when only a prefix of the selected batch was consumed re-entrantly.

Executable real-Inbox witness:

1. queue A, B;
2. peek `ALL`, selecting A and B for the entering run;
3. the observer claims only A;
4. commit the peeked A/B selection;
5. exact-prefix verification removes nothing because A is no longer at the front;
6. B remains queued even though the current run admits both A and B.

Observed result: selected envelope B remains eligible for later processing. In a real driver
run this makes B observable once in the current run and again on a later claim.

Required remediation: specify and enforce the language-neutral invariant across partial
prefix mutation: every selected envelope is admitted at most once, already-consumed selected
prefixes are not recreated, still-queued selected suffixes are committed, and unrelated
replacement input is never removed. Add a real-driver terminal-response witness so an
ordinary post-turn poll cannot mask the defect.

### L09-R015 — prepare-next-turn waterfall can replace signal authority

Classification: **PI_PARITY_DEFECT**.

Pinned Pi wraps `prepareNextTurn` for one Agent and supplies that Agent's `this.signal`; one
listener cannot redirect the next listener to a different Agent/signal. The shared consumer
matrix likewise requires the current run signal.

Python's `AGENT_PREPARE_NEXT_TURN` waterfall passes the Agent instance as ordinary replaceable
payload and has no normalization boundary. An executable two-listener witness against the
exact candidate does this:

1. listener A invokes the waterfall continuation with a forged Agent-like instance whose
   `signal` is `"forged"`;
2. listener B reads `instance.signal`;
3. listener B observes `"forged"`, not the original run signal.

Observed result: downstream signal authority is replaceable (`is_original = false`).

Required remediation: treat Agent identity and its run signal as immutable authoritative
metadata at every `prepareNextTurn` listener boundary. Only the intended run configuration
decision may waterfall. Add redirect and drop witnesses with at least two listeners.

### L09-R012 — AG-011 manifest rule remains contradictory

Classification: **CONTRACT_ASSURANCE_DEFECT**.

The `python:` pointer was repaired, but AG-011's current `rule:` still states that
`Inbox._commit_claim` removes “by count from the front.” Current code/spec instead require an
identity-sensitive commit, and PASS 7 assurance incorrectly says the rule prose was fixed.

Required remediation: replace the current rule with the final language-neutral queue
reservation/commit invariant after L09-R013/R014 are resolved, and correct the assurance
claim without erasing history.

### L09-R016 — current lower-layer signal prose is stale

Classification: **CONTRACT_ASSURANCE_DEFECT**.

Current `spec/tools.md` Layer-05 prose and TOOL-009 manifest wording say the cancellation
signal half remains open and Python has no AbortSignal-equivalent. The exact candidate now
implements Layer 09's `RunSignal`. This is present-tense normative/traceability text, not an
unmistakably historical statement. In addition, the current `_execute_and_finalize`
docstring describes signal delivery only for a fourth-parameter tool, contradicting the
approved signal-only capability.

Required remediation: preserve the historical Layer-05 defer while making current text
explicit that Layer 09 realizes it; correct the production docstring's capability matrix.

## Contract-quality answers

- Does a canonical runner simulate production behavior? **No.**
- Does Python contain an implementation workaround because the written contract is
  incomplete? **Yes:** peek plus all-or-nothing identity commit does not define or preserve
  the selected set across destructive re-entrancy.
- Could Python and Rust satisfy the current prose while differing observably? **Yes:** the
  selected suffix disposition under partial-prefix mutation is not coherently captured, and
  the manifest still specifies removal by count.
- Is signal authority immutable at every required listener boundary? **No:**
  `prepareNextTurn` permits Agent/signal replacement.
- Does an earlier certified layer prevent the repair? **No.** The issue is higher-layer
  reservation and listener-metadata design, not a lower-layer semantic conflict.
- Can Rust implement the intended cooperative signal design idiomatically? **Yes**, using a
  private controller/read-only signal, typed request fields, authoritative listener metadata,
  and a private reservation protocol. Rust must not implement against the contradictory
  current candidate.
- Has transport cancellation leaked into Layer 09? **No.** PROV-004 remains deferred.

## Existing Rust architecture feasibility

Certified Rust already provides `ToolExecutionSignal`, `ToolExecutionRequest.signal`, typed
Agent/Inbox/LLM request structures, typed lifecycle events, and a typed
`prepare_next_turn` event specification. Layer 09 requires additive activation and a private
queue-entry reservation mechanism; it does not require redesign or reopening of Layers
01–08. No Rust implementation was performed during this review.

## Fresh evidence gates

Executed at the exact code candidate:

- full Python suite: PASS, 1114 passed and 19 expected failures, 100% statement coverage
  (2821/2821 statements);
- `uv run ruff check .`: PASS;
- `uv run mypy src`: PASS (58 source files);
- schema validation: PASS, 185 tests;
- manifest integrity: PASS structurally, 79 rows / 79 unique IDs;
- targeted PASS-7 tests: PASS, 57 tests.

The semantic witnesses above were executed through the real candidate Inbox/driver/event
seams. Green aggregate gates therefore do not close the missing cases.

## Taxonomy and final status

Active findings:

- `PI_PARITY_DEFECT`: L09-R015;
- `CONTRACT_ASSURANCE_DEFECT`: L09-R012, L09-R013, L09-R014, L09-R016;
- `PI_BEHAVIOR_UNCERTAIN`: none;
- blocking `PARITY_CONSTRAINED_RISK`: none;
- `PARITY_NEUTRAL_HARDENING`: none required for the verdict.

Final status:

```text
shared Layer-09 contract
    REJECTED FOR RUST IMPLEMENTATION

Python Layer 09
    REOPENED

Rust Layer 09
    BLOCKED / NOT_IMPLEMENTED

Layer 09 cross-language
    NOT CLOSED

Layer 10
    NOT STARTED
```

The narrow remediation is limited to the five findings above. Any changed candidate SHA
requires a new exact-SHA review under the coordination workflow. Rust implementation must
not begin from this candidate.
