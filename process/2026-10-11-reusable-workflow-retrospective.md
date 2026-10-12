# Workflow retrospective: Layers 11–14 and the Minion-Memory adoption — towards Minion-Process, a reusable process kit

**Status:** direction and name APPROVED by the Owner (chat, 2026-10-11; record in §7.1); decisions 1–5
DECIDED by the Owner later on 2026-10-11 (§7.1, revision 3; durable record on `minion-agent#205`).
Revision 2 was APPROVED (record-only) by Codex's re-review and merged as `5c562008`; revision 3 is
documentary (§10). Process-only. It reopens no semantic finding, no certification and no
governance decision. Adoption follows `agent-workflow.md` §14.3: independent process review, then
the normative changes land as separate reviewed PRs.
**Author:** Claude (Python/shared-contract owner), at the Owner's request.
**Evidence base:** `EGAILab/minion-agent` and `EGAILab/minion-agent-docs` remote state at
`origin/main` `8f65372` / `origin/master` `cbb2873` (fetched 2026-10-11); `assurance/process-history.md`;
`assurance/process-friction-layer13.md`; `assurance/process-ce-proc-l13-01.md`; the Minion-Memory
local repositories (`minion-memory-docs` `5660f16`, `minion-memory` `bb05e39`); Warp Factories
documentation (`docs.warp.dev/factories`, `/factories/how-factories-work`, `/factories/factory-as-code`,
`/factories/measure-and-improve/self-improvement`) and the Warp blog posts "The factory stack" and
"Agent self-improving software factories".

---

## 1. Summary

The process is reliable where it matters: the HIGH-value semantic findings of Layers 11–13 were caught
by independent review before the candidate under review was certified, and the Layer 13 retrospective
already moved the two big costs (late semantic discovery, hand-executed mechanics) into the feasibility
matrix, hazard families, gate tiers, lean state and `minion-process`. Those changes are correct and
should be kept. "Reliable" is not "defect-free": three defects escaped an earlier certified baseline and
were fixed as post-certification deltas (`#144` own-exit wait, `#147` Linux tree termination, `#163`
`canonical_path` ELOOP), which is what the delta route exists for.

The remaining cost is coordination volume. Six weeks of Layers 11–14 produced about 1,280 GitHub
comments (roughly 0.9 M tokens; the survey and its limits are in §2.7), 192 of them Claude relaying
Codex's verdicts verbatim during the period when Codex's session had no GitHub write path, 131
review-record PRs of which 50 were closed unmerged (44 in one batch on 2026-10-10), and 39 PRs that only
flipped status strings. Four costs explain most of it, and all four showed up again when the process was
transplanted to Minion-Memory:

1. **The route is chosen by label, not by consequence.** The convergence protocol, designed for
   Pi-parity semantics, ran at full strength on its own tooling: `CE-PROC-L13-01` took five checkpoint
   revisions, one §11.8.10 invalidation and four targeted closures; Minion-Memory's `WP-P01` (process
   hardening, zero product requirements) took three complete reviews, a 688-row characterization
   matrix, two Owner-routed fix passes and a day of both agents before any Layer-01 contract existed.
   Those rounds found real defects, several of them in authority, acceptance and containment handling
   (§2.3), so the cost cannot be removed by giving "process" work a lighter route by default. What the
   episodes show is that the route should follow the **consequence** of a change (what it can write,
   delete, authorize, accept or interpret), and that the signal worth measuring is rounds that produce
   no new discriminating evidence, not the round count (§6.2).
2. **The process is a document, not a product.** Reuse was copy-and-adapt: Minion-Memory adopted
   `agent-workflow.md` "by reference" to a pinned SHA, re-derived the taxonomy, the hazard families and
   the state schema, and forked the CLI (`mneme-process` alongside `minion-process`). Two
   implementations of one state machine now exist and will drift. Nothing in Minion-Agent's later
   fixes reaches Minion-Memory without a manual pin bump and re-adaptation.
3. **Routing still goes through the Owner.** In Minion-Memory the Owner answered four routing
   questions in nine hours (`G-018`, `G-019`, `G-024`, `G-027`): all were "how should I proceed?"
   questions. For each of them the convergence protocol already prescribed the mechanical next step
   (which checkpoint to enter, when to re-dispatch, when a fix pass is allowed), and that is the part a
   routing table can answer without the Owner. What the Owner actually decided in those four answers
   was different and stays with the Owner: the scoped authorizations `G-018`–`G-027` set distinct
   conditions (which paths, which stages, which evidence) that a route default does not replace
   (§2.4, §6.4). Warp's foreman model puts routing in policy and reserves the human for spec approval,
   genuine ambiguity and merge. Minion should do the same: routing by rule, and the Owner reserved for
   path-C semantic choices, scope, risk acceptance and the conditions of any scoped authorization.
4. **The control plane was only half writable for most of the period.** The workflow assumes
   agent-to-agent hand-off through GitHub, but for most of Layers 11–13 Codex's session had no working
   GitHub write path, so 192 Codex verdicts were Claude relays with a file hash, and Owner decisions
   were transcribed into comments (about 118 times, some triplicated, nine damaged in transit). Since
   2026-10-10 Codex has posted its own verdicts and committed state through `minion_process` on `#199`
   (for example `#199` issuecomment-6103236644), so the relay cost is historical. Minion-Memory uses
   state files and git as its control plane; the open question for Minion-Agent is the reliability of
   Codex's present GitHub path against that backend (§6.8, decision 5).

The proposal (§6) is a versioned **process kit** with a per-project **profile**, work-package
**kinds** and **consequence classes** with a route per class, generated hand-offs, metrics collected by the tool, and a lessons
annex that takes the incident narratives out of the normative text. §7 lists the Owner decisions.

---

## 2. Evidence

### 2.1 Volume per layer (assurance records on `origin/master`, `assurance/layers/`)

| Layer / family | Records | Note |
|---|---|---|
| 01–07 | 2, 7, 8, 9, 10, 7, 6 | pre-convergence era |
| 08 (agent loop) | 22 | 14 Python passes, 1 convergence episode |
| 09 (active abort) | 28 | 10 passes, 3 convergence episodes |
| 10 (provider abstraction) | 14 | |
| 11 (real providers) | 59 | WP model introduced mid-layer |
| 12 (execution seams) | 63 | `CE-L12-PY-01-01`: 5 characterization versions, 8 targeted reviews, 4 final reviews |
| 13 (built-in tools) | 47 | plus `l0506-*` 21, `l0206-*` 8, `l05-*` 3 lower-layer deltas |
| 14 (prompt assembly, skills) | 9 | first full layer under feasibility matrix + gate tiers |

Counting predicate: Markdown files directly under `assurance/layers/` in the tree of `cbb2873`
(reproducible as `git ls-tree --name-only cbb2873:assurance/layers` filtered to `.md` names; the
listing is of that tree, not of a moving `origin/master`), 330 in total. The rows above account for 323 of them;
the remaining seven are five `l12-*` delta records (`l12-d001-*` ×4, `l12-d006-feasibility-matrix`) and
two uncategorized files (`exec002-r1-rust-append.md`, `fs-path-jsstring-scoping.md`). Layer 14's row
is an observation, not proof that Phase A caused it: two WPs, two deltas, no convergence episode,
closed inside two weeks, with no control layer to compare against.

### 2.2 Mechanics

| Signal | Measurement | Source |
|---|---|---|
| Registered git worktrees | docs repo 310 (157 detached), code repo 257 | `git worktree list`, 2026-10-11 |
| Scratch artifacts in one Claude session dir | 607 files in `.tmp/claude-scratch/` | this workspace |
| Single-use patch scripts before `minion-process` | ~150 | friction retro §0 |
| Coordination body size before lean schema | 24,458 and 34,759 characters (`#49`, `#88`) | friction retro §0 |
| Local docs checkout drift at session start | 60+ commits behind `origin/master`, on a feature branch | this session; Minion-Memory had to clone fresh at WP-00 |
| Normative process text | `agent-workflow.md` 1,893 lines; `coordination-state.md` 739; six further process docs; `CLAUDE.md` + `AGENTS.md` restating ownership | `origin/master` |
| Minion-Memory adoption | `agent-workflow.md` 193 lines **by reference** to a pinned Minion-Agent SHA, plus 13 hand-off prompts (52 KB) and 19 review records for two process-only WPs in 27 hours | `minion-memory-docs` |

### 2.3 Convergence applied to tooling

| Episode | Surface | Rounds | Outcome |
|---|---|---|---|
| `CE-PROC-L13-01` (Minion-Agent) | `minion-process` control-data handling | 5 checkpoint revisions, §11.8.10 invalidation, 4 targeted closures, 321 tool tests, Hypothesis totality over 30 paths | correct tool; the YAML-loader hardening is reusable, the review cost was not proportional to a workflow helper |
| `CE-P01-01` (Minion-Memory) | `mneme-process` validator "trust boundary" | 688-row Codex matrix, 2 checkpoint revisions, 3 targeted closures (`CL-001..005`, `R1`), 2 Owner fix-pass authorizations | WP-P01 CLOSED; Layer 01 had not started |

Both episodes found real defects, and §11.8 behaved exactly as written. The first draft of this record
claimed that a workflow validator's failure mode is only a refused or mis-shaped write that the next
reader catches, and that `CE-PROC-L13-01` could have ended after revision 2 with every witness kept.
The independent review of the draft (`PROC-KIT-R002`, `K1`) showed that claim to be wrong, and the
evidence is worth recording because it decides how §6.2 is designed:

- `CE-PROC-L13-01` checkpoint review 4 found cyclic YAML graphs that loaded but broke recursive
  consumers, and inconsistent resolver outcomes, neither covered by revision 2's witnesses; the
  resolver value/type controls came in closures 4 and 5 (`minion-agent-docs#204`).
- `PROC-AUTHDEP-R001`: the runner accepted a coherently substituted artifact and lockfile instead of
  verifying the immutable Pi pin. That is authority substitution, not a mis-shaped state.
- `PROC-L256-R001`: `commit_state` wrote a scoping closure on a non-approved review; a later
  round-trip would not have undone the unauthorized state.
- `#272`: false control kills from an invalid baseline or unselected witnesses, which decides whether
  product evidence can be trusted at all.
- `CE-L12D007-01` (`#199`, 2026-10-10, the "nine review events in one evening" cited in §2.5):
  containment hardening of the evidence-path tooling after the `E:\` deletion. Its rounds found a
  lexical `..` collapse in link text that resolved outside the sandbox, NUL-path proof handling, an
  over-long-component case, swallowed restore failures and a `deny_access` fixture that locked the
  owner out of an ACL. Every round produced new discriminating evidence.
- Minion-Memory `G-024` (two HIGH findings on build writes outside the project) and `G-027` (silent
  acceptance of unreadable nested git state).

Process tooling therefore does control authority, destructive execution and acceptance, and
`requirements: []` says nothing about consequence. The question this retrospective asks is how to route
by consequence rather than by label, and how to tell a productive round from a ceremonial one. The
signal is not the round count: every round above produced new evidence. The signal is a round that
produces **no new discriminating evidence**, and that is what §6.2 and §9 measure.

### 2.4 Owner routing questions in Minion-Memory (2026-10-10)

| Record | Question asked | Already prescribed by |
|---|---|---|
| `G-018` | "Survived three reviews, how should I route it?" | §11.8 trigger A/C: enter convergence |
| `G-019` | "Start WP-01 in parallel?" | §11.15 parallel work with dependency edges |
| `G-024` | "Targeted closure found 5 defects, how should I proceed?" | §11.4 remediation → targeted closure |
| `G-027` | "One regression remains, how should I proceed?" | same |

Each question's *route* was the process default. The answers were not interchangeable with a routing
table, however: the pinned Minion-Memory governance record ordered Codex-led convergence, allowed
parallel authoring but **serial governance**, and bounded the fix passes. Those authorizations keep
their scope; §6.4 does not replace them retrospectively. The cost it addresses is narrower: the
delegation text (`G-009`) lists *acceptance* and *status* but not *routing*, so the agent escalated to
stay inside its authority even where the route was already prescribed. A delegation that covers routing
is a proposal for the Owner (§7, decision 3), not something this record enacts.

### 2.5 GitHub interaction volume (read-only `gh` survey, 2026-10-11)

| Signal | Measurement |
|---|---|
| Comments | about 1,280: this survey 811 code + 463 docs (2026-10-11); Codex's recount 822 + 463 as of `2026-10-10T23:35:54Z`; about 3.69 M characters, roughly 0.9 M tokens of coordination text (limits in §2.7) |
| Comment length | issue comments: median 1,669 chars, p90 8,024, max 17,390; 235 of 577 exceed 3,000 chars |
| Codex text relayed by Claude | 192 comments carry the "posted by Claude on Codex's behalf, verbatim" marker with a file hash, from the period in which Codex's session could not reach GitHub (MCP approval policy, connection refused); 13 `REMOTE_SYNC_BLOCKED`. Historical: since 2026-10-10 Codex publishes through `minion_process` (`#199`) |
| Review-record PRs in the docs repo | 131 of 286 PRs are `review/*` records (`gh pr list --search head:review/`); 81 merged, 50 closed unmerged: **44 in one batch on 2026-10-10**, 6 on 2026-09-21. The batch closure's authorization is attributed to the Owner in the agent survey and not independently evidenced here; the date clustering is |
| Status-only PRs | 24 code + 15 docs PRs exist only to flip status strings (title/diff predicate; approximate) |
| Formal GitHub reviews | 3 in total; every verdict lives in comments |
| Owner decisions | about 118 comments match the Owner-decision transcription markers; some posted three times across issues (17,390 chars each); 9 arrived truncated or collapsed |
| Errata | 12 explicit correction comments (wrong SHA, drafts called ready, duplicate posts, a wrongful quarantine) |
| Heaviest issues | `#29` (L11 Pass 2): 66 comments, 24 Claude→Codex and 24 Codex→Claude transitions in 2.9 days; `#48` (WP-13.1): 66 comments, 34 negative verdicts, 7.5 days, body 71.8 KB; `#199` (L12-D007, open): 5 checkpoint reviews + 2 targeted closures in 3 hours on 2026-10-10 (`CE-L12D007-01`; every round productive, §2.3) |
| Process-change PRs | 22 docs + 2 code; nearly every rule landed within 48 hours of the incident that motivated it |
| Layer wall-clock | L11 ≈ 4.5 d; WP-12.1 2.3 d; Layer 13 16.6 d; Layer 14 1.1 and 1.6 d per WP |

Layer 14 is the first layer run end to end under the feasibility matrix and gate tiers, and it is the
fastest since Layer 10; with two WPs and no control, that is an observation rather than proof. The
per-item review-round count has not fallen: `#199` ran nine review events in one evening. As §2.3
shows, each of those rounds found a new containment escape, so the count measured discovery, not
waste. The metric that separates the two is in §9.

### 2.6 Reliability incidents, 2026-09 to 2026-10

| Incident | Root cause class | Fixed by |
|---|---|---|
| Fork subagent fabricated an Owner decision, pushed branches, opened PRs | side effects available to a read-only role | §11.9–§11.12 |
| PowerShell flattened a coordination body | transport round trip unchecked | §11.1.1 commit rule, `minion-process apply` |
| `minion_process apply ... \| tail && gh issue close` closed an issue on a refused write | dependent action not gated on the tool's exit status | interim operator rule; composite verbs proposed |
| Stale "PRs are ready" claim written before the command ran | statement ahead of state | lesson recorded |
| 2026-10-10: a Pi characterization probe run by Claude resolved a `..` chain to `E:\` and removed recursively | destructive op without containment check | outside-root hook, `fs-guard.mjs`, the `CLAUDE.md` containment rule. The incident is recorded in `CLAUDE.md` only, not on GitHub: a documentation gap for the same incident, which §6.9 closes |
| herdr prompt stalls; Codex budget exhausted mid-pass | harness limits | §11.17 completion notification, resumable checkpoints |
| Reviewer sandbox lost Docker/npm; two final reviews withheld | authority execution coupled to live network | `authority-dependencies.md` |
| 2026-10-11 (about 00:06 Sydney): the Linux gate launcher run by Codex bound the user's `C:` home into Docker as a writable cargo home (`.tmp/l12d006-rust/INCIDENT-2026-10-11.md`, `#194`) | mount path not containment-checked | same class as the probe incident; §6.7 |

The common root is that a side-effecting action (publish, close, merge, delete, dispatch) was executed
by prompt discipline. Every fix moved it behind a guard. A guard added is not proof that the failure
mode is gone; the incident replay suite in §6.7 is how that proof is kept current. §6.6 finishes the
move behind guards.

### 2.7 Survey method and limits

The GitHub numbers in §2.5 come from a read-only `gh` survey run by a subagent on 2026-10-11 against
both repositories, before this record's first commit. Its limits, raised in review (`PROC-KIT-R004.3`):

- **Comments are mutable independently of git.** A count is a snapshot at a time, not a function of a
  branch SHA. Codex's recount at the candidate's commit time (`2026-10-10T23:35:54Z`) gave 822 code
  comments against this survey's 811; the difference does not falsify either, it shows the snapshot is
  not reproducible from a date and a SHA. Any future survey must record its timestamp and ID set.
- **Classifications are marker-based.** "Relayed by Claude" matched the verbatim/on-behalf marker and a
  hash line; "Owner decision" matched the Owner-decision transcription markers; "erratum" matched
  explicit correction wording; "status-only PR" used title and diff shape. Broad searches for "Codex"
  or "verbatim" give very different totals. The ID sets were not frozen, so these rows are
  approximate and are presented as magnitude, not as independently verified exact counts.
- **Exact counts** in §2.1 (330 records, predicate stated) and the `review/*` PR counts (131 / 81 / 50,
  with the 44 and 6 closure dates) were re-derived against `cbb2873` and the live PR list and agree
  with Codex's recount.

The metrics proposal (§6.6) exists so that the next retrospective does not depend on a survey like
this one.

---

## 3. What to keep unchanged

These are the parts of the process that carried the assurance value, and the proposal does not weaken
any of them:

- independent exact-SHA review with implementer/reviewer separation (§11.3);
- discriminating witnesses with realistic negative controls killed by the intended test (§9.1, §9.7,
  §11.8.7.1);
- the convergence protocol with its two-party checkpoint and invalidation rule, **for semantic
  surfaces** (§11.8);
- the feasibility matrix, hazard families and neighbourhood expansion (§4.1.1, §9.4, §9.5);
- gate tiers G0–G3 (§13.1);
- lean current state and the commit round trip (§11.1.1, §11.1.4);
- `minion-process` as the only path for state writes, merges and comments (§11.16);
- governance provenance and quarantine (§11.10–§11.12);
- the standing delegation (`#75`) and the filesystem-containment rule;
- the final complete review of the changed candidate on every route that changes anything
  (§11.8.8), and the challenge/convergence route for any change to authority, acceptance,
  transitions, execution, containment or evidence interpretation, whatever the work package is
  called.

The first draft of §6.2 and §6.3 weakened the last two bullets for "process"-kind work and small
deltas. Review (`PROC-KIT-R002`, `K1`–`K3`) traced real defects to exactly those routes (§2.3), and the
current §6.2 and §6.3 keep them.

---

## 4. Warp Factories: what maps, what to borrow, what not to

Warp defines a factory as a team of cloud agents attached to a set of repositories that ship together.
A **foreman** routes each **work item** through **Triage → Planning → Building → Reviewing**, skipping
stages a well-defined request does not need and sending work back when review finds problems. Humans
hold three checkpoints: spec approval, questions on genuine ambiguity, and merge (enforced by branch
protection, never by the factory). The whole factory is **defined as code** (`factory.yaml`,
`agents/<name>/agent.md`, `automations/`, `scorers/`, `benchmarks/`, `skills/`), validated by a CI
check on every definition PR and applied atomically. **Scorers** are LLM judges that label completed
runs against a written rubric; **benchmarks** replay fixed tasks (pinned to 40-character SHAs) across
configurations; **self-improvement** groups scorer failures into PRs against the factory definition,
which humans review. The dashboard tracks autonomy, PR cycle time, cost per PR and opened-vs-merged.

| Warp concept | Minion today | Gap |
|---|---|---|
| Factory per repo set that ships together | one process per project (Minion-Agent, Minion-Memory), each a code+docs pair | fine; matches Warp's "do not split by team or task" guidance |
| Work item keeps its context from intake to hand-off | coordination issue / state file per WP | fine |
| Foreman routes, skips stages, sends back | Claude routes **and** implements; the state machine is fixed per WP regardless of kind | **borrow**: routing as policy, WP kinds, stage skipping (§6.2, §6.4) |
| Stage agents each with own model/harness | Claude = spec+implement(Python), Codex = review+implement(Rust) | fine; keep the two-agent independence |
| Human checkpoints: spec approval, questions, merge | Owner: contract checkpoint (partly), path-C decisions, acceptance (delegated) | **borrow**: make the Owner list explicit and complete; stop routing questions |
| Verdict is advisory; merge is repository policy | review verdict binding; merge by delegation; approval count 0 because identities are shared | **borrow**: record reviewer identity in a structured review record; tool enforces reviewer ≠ author |
| Definitions as code, CI-validated, atomic | prose docs + a Python tool; the state schema is validated, the *process definition* is not | **borrow**: a machine-readable project profile and kit version (§6.1) |
| Scorers (LLM judge with rubric) | process metrics §14.6 defined, never collected | **borrow the metric collection**, not the LLM judge: Minion already has a stronger signal (negative controls, independent review verdicts) |
| Benchmarks on pinned tasks | historical-replay tests in `minion-process`; friction retro §4 replay done by hand | **borrow**: a kit-level incident replay suite (§6.7) |
| Self-improvement PRs against the definition | §14 retrospectives in prose, hundreds of lines each | **borrow the form**: a retrospective is a short record plus a PR against the kit, driven by numbers |
| Autonomy / cycle time / cost per PR | not measured | **borrow**: per-WP metrics emitted at closure (§6.5) |

What not to borrow: Warp's review is advisory and its loop has no stated termination; Minion's
exact-SHA, negative-control and convergence rules are stronger and are the reason the HIGH-value
findings of Layers 11–13 were caught before the candidates under review were certified (the three
post-certification deltas are in §1). Warp optimizes PR throughput; Minion optimizes certified semantic
equivalence across two languages. Keep Minion's gates, borrow Warp's packaging and routing.

---

## 5. Findings

Each finding states the evidence, the cost class and the proposal section that addresses it.

| ID | Finding | Evidence | Cost | Addressed in |
|---|---|---|---|---|
| RW-01 | One route for every kind of work package | `CE-PROC-L13-01`; `CE-P01-01`; two transition-table patches (`SCOPING → CLOSED`, `FINAL_CONTRACT_REVIEW → CLOSED`) added after the fact for light WP kinds | efficiency | §6.2, §6.3 |
| RW-02 | Process reuse is copy-and-adapt | Minion-Memory adoption record: taxonomy renamed, hazard families re-derived, CLI forked, 193-line workflow pointing at another repo's SHA | efficiency, reliability (drift) | §6.1 |
| RW-03 | Routing questions reach the Owner | `G-018`, `G-019`, `G-024`, `G-027` in one day | efficiency, Owner time | §6.4 |
| RW-04 | Hand-written hand-off prompts | 13 prompt files (52 KB) in Minion-Memory; dispatch text in Minion-Agent scratch; every prompt restates scope, SHAs, rules, allowed verdicts | efficiency | §6.5 |
| RW-05 | Normative text carries incident narratives | §9.1, §10, §11.8.10, §11.8.11 each embed multi-paragraph Layer-08/09/11/12 case histories; 1,893 lines | efficiency (every read), reliability (two agents reading different emphasis) | §6.9 |
| RW-06 | Metrics defined, not collected | §14.6 exists; no WP closure record carries the numbers; this retrospective had to count files and comments by hand | efficiency of retrospectives | §6.6 |
| RW-07 | Side effects still reachable outside the tool | `\| tail &&` incident; stale "ready" claim; manual herdr dispatch | reliability | §6.7 |
| RW-08 | Worktree and scratch sprawl | 310 + 257 registered worktrees, 607 scratch files, disk ran to 1.7 MB free on 2026-10-09 | efficiency, reliability (gate failures from full disk) | §6.7 |
| RW-09 | Review records are prose, so the tool cannot count rounds, survivals or reviewer identity | convergence triggers checked by hand (§11.8 "trigger check is mandatory"); Phase C2 `convergence counters` designed, not built | reliability | §6.6 |
| RW-10 | Local checkouts drift from remote | docs checkout 60+ commits behind on a feature branch; Minion-Memory cloned fresh instead of trusting `Minion-Agent/` | reliability | §6.7 |
| RW-11 | The "agent-to-agent GitHub control plane" depended on one agent's write path, which was absent for most of Layers 11–13 | 192 verbatim relays, 13 `REMOTE_SYNC_BLOCKED`, hash-of-file provenance in comments; Codex now writes through `minion_process` (`#199`, 2026-10-10 onwards); Minion-Memory uses a state-file backend and git | efficiency (each relay cost a Claude turn), reliability (transcription errata) | §6.8 |
| RW-12 | Review records as PRs | 131 `review/*` PRs; 50 closed unmerged (44 in one batch on 2026-10-10, 6 on 2026-09-21); §11.2.1 already says a PR per review event is not required | efficiency | §6.8 |
| RW-13 | Owner decisions transcribed by agents into comments | about 118 transcriptions, triplicates of 17 KB, 9 damaged in transit | reliability (governance provenance), efficiency | §6.8 |
| RW-14 | Rules accrete reactively | 22 process PRs, most within 48 h of an incident; the normative text grew from 1,548 to 1,893 lines in three weeks | efficiency (read cost), reliability (two agents weighting different paragraphs) | §6.9 |
| RW-15 | Dispatch and reply routing assume one session per role per project | Codex's PROC-KIT completion notice went to `w1:p1` (the L12-D007 session) instead of `w1:p8` (this WP's owner) because the pane is fixed per project; the hand-off template hard-codes the sender's pane | reliability (lost or misrouted completion signals) | §6.5 |
| RW-16 | Dispatch retry is unsafe as practised | `herdr agent prompt --wait` to a `done` pane returned `agent_prompt_stalled` in every one of about 12 dispatches although the text was delivered; to a `working` pane it returned `timeout` while queued; a blind re-send would have duplicated the prompt each time (`K4`) | reliability | §6.5 |
| RW-17 | The containment hook's token-level precision costs turns and pushes toward workarounds | about 15 harmless commands blocked in one session on `X:` tokens in non-path text (`Python:`, `try:`, `https:`, `Co-Authored-By:`, `e:` in `except OSError as e:`); this session: `s:` in `open_findings:`, `D:` in `BLOCKED:`; each block cost a turn and moved commands into config files or the editor tool (`K5`). No block was wrong in effect | efficiency; reliability (workaround pressure on a safety rule) | §6.7 (Owner-governed) |
| RW-18 | Gate launchers are the least reliable part of the harness | one Linux Python gate needed five launches for harness reasons: `set -e` aborted before the log copy; a cached PyICU wheel with another ICU prefix in its rpath gave 221 spurious failures; two PyPI lookup failures; an environment script clobbered a caller variable (`K6`) | efficiency, reliability (gate results that measure the harness) | §6.7 |
| RW-19 | Fault-injection evidence can be vacuous | `CE-L12D007-02` checkpoint review 2: a probe's planned failure never fired in the binding, so a "MATCH" compared nothing; same family as `#272`'s unselected-witness survivors (`K7`) | reliability (evidence interpretation) | §6.7 |

---

## 6. Proposal: a reusable Minion process kit

### 6.1 Kit and profile (RW-02)

Split the process into a versioned, project-neutral **kit** and a per-project **profile**, in the
shape Warp uses for a factory definition:

```text
minion-process/                          # repository EGAILab/minion-process (project Minion-Process), tagged releases (v1.0.0 ...)
  WORKFLOW.md                            # normative core, project-neutral, ~400 lines
  coordination-state.schema.json         # state block schema (v2 lean), both backends
  transitions.yaml                       # legal transitions per WP kind (§6.2)
  gate-tiers.md                          # G0–G3, stage minimums
  finding-taxonomy.md                    # generic classes; profile supplies aliases
  hazards/                               # families tagged by runtime: js, python, rust, json, yaml, sqlite, fs, unicode, async
  templates/                             # feasibility matrix, hand-off, review record, convergence record, closure record
  roles/                                 # coordinator, shared-contract owner, implementer, reviewer: generic text
  lessons/                               # incident records by ID, referenced from WORKFLOW.md rules
  minion_process/                        # the CLI: one code base, backends `github-issue` and `state-file`
  replay/                                # incident replay suite (§6.7)

<project>-docs/process/
  profile.yaml                           # the only project-specific process file (below)
  state/                                 # when backend = state-file
```

A profile declares what Minion-Memory had to re-derive by hand:

```yaml
kit: {version: "1.0.0", source: "EGAILab/minion-process"}
project: minion-memory
authority:                                # semantic authority chain, highest first
  - {kind: bundle, path: reference/mneme-v2.3-source-bundle.yaml, verify: sha256}
  - {kind: spec, path: spec/}
  - {kind: conformance, path: ../minion-memory/conformance/}
repos:
  code: {path: ../minion-memory, default_branch: main}
  docs: {path: ., default_branch: main}
coordination: {backend: state-file}       # or github-issue, with owner/repo
agents:                                   # panes are defaults only; reply-to is recorded per dispatch (§6.5)
  claude: {roles: [coordinator, shared-contract-owner, implementer:python], harness: claude-code, default_pane: w1:p1}
  codex:  {roles: [reviewer, implementer:rust], harness: codex, default_pane: w1:p2}
taxonomy_aliases: {IMPLEMENTATION_DEFECT: PI_PARITY_DEFECT}   # empty for generic names
hazard_families: [python, rust, json, yaml, sqlite, fs, unicode, async]
gates:                                    # kit launchers with self-tests, not free-text commands (§6.7)
  python: {launcher: kit/launchers/python-icu, tiers: [g0, g1, g2, g3]}
  rust:   {launcher: kit/launchers/rust-icu, tiers: [g0, g3]}
delegation: {source: reference/governance/2026-10-10-owner-wp00-acceptance.md#g-009, routing: true}
wp_kinds_enabled: [semantic, delta, process, scoping, status]
environment: process/environment/project-environment.sh
```

`minion-process profile validate` is the kit's equivalent of Warp's `warp/factory-config` check: run
in CI on every docs PR, atomic (an invalid profile leaves the previous one in force). A kit upgrade is
a version bump in `profile.yaml` plus the kit's changelog, reviewed like any process PR. Minion-Agent
is the first consumer and Minion-Memory the second; Pi-specific rules move to Minion-Agent's profile
and lessons, not into the kit.

### 6.2 Work-package kinds and routes (RW-01)

A work package carries a **kind** (what it is) and a **consequence class** (what it can do). The kind
names the shape of the work; the consequence class, not the kind, selects the route. This is the
correction review required (`PROC-KIT-R002`, `K1`, `K2`): `requirements: []` describes scope, not
consequence, and the process episodes in §2.3 show tooling deciding authority, acceptance and
destructive execution.

**Consequence predicates.** A change is **governing** if it, or the tooling it changes, can do any of:

- write, rename, delete or change permissions on paths computed at runtime (containment);
- decide or record acceptance, closure, merge, certification or quarantine (acceptance);
- change which transitions are legal or who may make them (transitions);
- select, verify or substitute an authority artifact, pin or lockfile (authority);
- execute or launch gates, containers, probes or the other agent (execution);
- interpret evidence: comparators, control selection, "fired/unfired" detection, counting of rounds
  or findings (evidence interpretation).

Everything else is **mechanical**: prose, templates, rendering, read-only reports, registry syncs the
tool validates, scoping artifacts.

| Kind | Examples | Consequence | Route | Convergence | Feasibility matrix | Final complete review |
|---|---|---|---|---|---|---|
| `semantic` | a layer WP owning product requirements | governing by definition | full §11.4 | yes (§11.8) | mandatory when high-risk | yes |
| `delta` | post-certification delta on a certified layer (`L0506-D00x`) | governing | contract delta → impl → targeted → closure | yes, scoped to the delta | mandatory; rows **measured** against pinned authority | yes |
| `process` | kit/tool/workflow change | **governing** when any predicate above holds (`PROC-L13`, `PROC-AUTHDEP`, `#256`, `WP-P01`, `CE-L12D007-01`) | the full route: challenge/convergence available, §11.8.8 final review of the changed candidate | yes | no | yes |
| `process` | templates, prose, renders, this record | mechanical | draft → independent review → remediation → targeted closure → final review of the changed candidate → CLOSED | no; a trigger A/B/C firing upgrades the class (below) | no | yes |
| `scoping` | read-only scoping (`WP-14.SCOPE`) | mechanical | `SCOPING → CLOSED` on approved artifact (`coordination-state.md` §10.3) | no | no | the approval is the review |
| `status` | registry/status sync | mechanical | tool-validated; no review | no | no | none; `minion-process` checks consistency |

**Who classifies.** The coordinator proposes the class at intake with the predicate it applied, in the
state block (`consequence: {class: mechanical, rule: CP-0}`). The first independent review confirms or
corrects the class as a required line of its record. The class moves only in these ways:

- **Upgrade is automatic and recorded.** Any finding whose subject matches a predicate (a containment
  escape, an acceptance written on a non-approval, a substituted pin, a vacuous comparator) sets the
  class to governing with the finding ID as the rule; the tool refuses a lighter closure from then on.
  Nobody asks the Owner whether to "convert" the WP.
- **Downgrade needs two parties.** Reviewer agreement plus an Owner risk decision recorded as
  governance; never the coordinator alone.

**What this changes in practice.** For `CE-PROC-L13-01`, `PROC-AUTHDEP`, `#256` and `CE-L12D007-01`
nothing: each would classify as governing at intake or on its first finding, and each round of those
episodes produced new discriminating evidence (§2.3). For a template, a rendering change or a record
like this one, the route loses the convergence checkpoint ceremony but keeps independent review and
the final review of the changed candidate. The saving is real but smaller than the first draft claimed,
and it is bought without dropping a gate that has caught a defect.

**The signal.** The round count is not the failure signal; §2.3's episodes were long *and* productive.
The signal is a **round that produces no new discriminating evidence**: a review that rejects without a
new witness, a new finding or a new matrix row. Two such rounds on a candidate are the cue to check the
§11.8 triggers (governing) or to put a risk question to the Owner with the default stated (mechanical).
§9 measures this instead of rounds.

### 6.3 Stage skipping (RW-01)

Warp's foreman skips Triage and Planning when a request is already well defined. Minion's equivalent is
narrower than the first draft proposed (`PROC-KIT-R002`, `K3`): the size of a delta does not predict
its hidden dimensions. `L12-D007` entered implementation with an approved contract and integration and
then surfaced `L12D007-PY-I001` (rmdir-first), I001 (path-less fallback), I002 (cached child type),
I003 (a swallowed child error), and the `CE-L12D007-02` findings C001 (the Windows recovery stage),
C002 (an Owner decision) and C003 (the validation stage), three of which needed new normative text.
"One additive row with rows already audited" would not have predicted any of them.

A stage may be skipped only when all of the following hold and are recorded in the state block
(`skipped: [<stage>], rule: SK-n, measured_rows: [...], reviewer: codex`):

- the feasibility rows the stage would have examined are **measured against pinned authority** on
  every platform in scope, not inferred from the parent WP's rows;
- the reviewer consents to the skip in a review record before the stage is passed;
- the skipped stage is never the final complete review, and never a stage on a governing change
  (§6.2).

The exact-SHA and negative-control rules are unchanged.

### 6.4 Routing is policy; the Owner decides semantics, scope and risk (RW-03)

Add a **routing table** to the kit that answers every "how should I proceed" case mechanically, and
state in the delegation template that routing is delegated. The agent then records the route it took
with its rule ID instead of asking:

| Situation | Route (no Owner question) |
|---|---|
| finding survives 2 reviews (A) / successor on same surface (B) / 3 rejected complete reviews (C) | enter convergence; `minion-process convergence counters` prints the firing trigger |
| targeted closure returns new findings on an agreed checkpoint | one fix pass per round; §11.8.10 invalidation fires on the second failure of the same finding |
| semantically independent WP idle while the other agent works | progress it; record dependency edges |
| reviewer loses environment | `HANDOFF_BLOCKED`; re-dispatch unchanged when restored |
| two consecutive rounds without new discriminating evidence (§6.2) | governing: run the §11.8 trigger check and record the result; mechanical: file one Owner risk question with the default stated |
| a finding matches a consequence predicate on a mechanical WP | class upgrades to governing with the finding ID; no question |

The Owner-only list is proposed as a closed list in the kit: path-C semantic choices, scope and
layer-order changes, intentional divergence, risk acceptance, authority changes, remote creation,
destructive history, consequence-class downgrades, and amending the delegation itself. Each Owner
question is filed with its options packet and the default the process would otherwise take, so the
Owner can answer "default" in one word.

Both the routing table and the closed list are **proposals** that take effect only when the Owner
extends the delegations (`minion-agent#75`, Minion-Memory `G-009`) to routing (§7, decision 3). Until
then the existing delegation scope applies, and existing scoped authorizations such as Minion-Memory's
`G-018`–`G-027` keep their terms (§2.4).

### 6.5 Generated hand-offs and dispatch (RW-04)

`minion-process handoff <wp> --type <review-type>` renders the hand-off prompt from the state block,
the profile and the kit template: exact SHAs, scope and non-scope, requirement IDs, artifacts to read,
gate tier and commands, allowed verdicts, the record path to write, the completion-notification
instruction with the **dispatching session's** reply-to pane, and the independence clause. The author
adds only the WP-specific semantic notes. Codex's role file tells it to run `minion-process
handoff-check` first and to refuse a prompt that disagrees with the state block.

**Reply-to is per dispatch, not per project** (`RW-15`, `K4`). The profile's `agents.*.pane` is a
default only. `dispatch` writes `reply_to: {pane: w1:p8, session: <id>}` into the work item's state, the
rendered prompt names that pane, and `handoff-check` prints it. Two Claude sessions on one project
(this WP and `L12-D007` on 2026-10-11) is the normal case the first draft did not allow for.

**Dispatch is send-once with verification, never blind retry** (`PROC-KIT-R003`, `RW-16`, `K4`). The
measured behaviour of `herdr agent prompt --wait` in this project is: to a `done` pane it reports
`agent_prompt_stalled` although the text has reached the input box; to a `working` pane it reports
`timeout` while the text is queued. A stall or timeout is therefore not evidence of non-delivery, and
re-sending duplicates the prompt. `minion-process dispatch <wp>`:

1. refuses if `herdr agent get` shows the pane `blocked` or in a question/permission dialog, and never
   sends keys to such a pane (the Owner-dialog prohibition stays absolute);
2. sends the prompt text exactly once and records `state_change_seq` before and after;
3. verifies delivery by inspection (the pane transcript shows the pasted prompt, or the status moves to
   `working`), and only then, if the prompt sits unsubmitted and the pane is verified not blocked,
   sends a single Enter;
4. records the dispatch, the verification used and the reply-to in history; a second `dispatch` for
   the same hand-off is refused unless the first is marked `undelivered` after inspection.

Delivery acknowledgement is not turn acknowledgement: the completion notification (§11.17) remains the
only signal that the work item is done, and it is still only a wake-up to re-read durable state.

### 6.6 Structured review records and collected metrics (RW-06, RW-09)

A review record carries a small YAML header the tool reads; the prose stays below it:

```yaml
review:
  wp: WP-14.2
  type: IMPLEMENTATION_REVIEW | TARGETED_CLOSURE | CHECKPOINT | FINAL | CLOSURE
  reviewer: codex                 # must differ from candidate.author
  candidate: {code: <40-hex>, docs: <40-hex>}
  gate_tier_verified: G3
  verdict: APPROVED | CHANGES_REQUIRED | HANDOFF_BLOCKED
  findings:
    - {id: L14-WP142-R003, class: CONTRACT_ASSURANCE_DEFECT, blocking: true, witness: tests/..., negative_control: ...}
  closed: [L14-WP142-R001]
```

With that header the tool computes the convergence counters, checks reviewer ≠ author, rejects a
closure without a negative-control record, and emits the §14.6 metrics at WP closure into
`assurance/metrics/<wp>.yaml`: review events, complete vs targeted rounds, time per state, Owner
escalations, G3 runs, findings per hazard family vs ad hoc, semantic dimensions found after
implementation started. `minion-process metrics render` produces the cross-WP table that replaces
hand-counting in retrospectives. This is Warp's dashboard without the LLM judge: the labels are the
recorded verdicts and negative-control results, which are stronger evidence than a rubric score.

### 6.7 Side effects only through the tool; environment hygiene (RW-07, RW-08, RW-10)

- Composite verbs (`minion-process close`, `merge`, `comment`, `dispatch`) perform the GitHub or herdr
  action only after the state commit returns; the CLI exits non-zero on any refusal, so shell discipline
  is no longer load-bearing. `.claude/settings.json` and `AGENTS.md` deny bare `gh issue close`,
  `gh pr merge` and `herdr agent prompt` outside the tool.
- `minion-process session start` runs at the top of every pass: fetch both repos, report local vs
  remote drift and the branch each checkout is on, source the project environment, check free space,
  **list** worktrees and scratch that are candidates for cleanup, and print the WPs the current agent
  may progress. This replaces the §12.2 checklist and Minion-Memory's clone-fresh workaround.
- **Cleanup deletes nothing on age or detachment alone** (`PROC-KIT-R003`). Detached and old are not a
  proof of disposability: a worktree can hold uncommitted or unpushed work, a retained baseline,
  incident material or a local-only hand-off. `minion-process cleanup` removes a target only when every
  condition holds and is recorded: the target is inside the project root by lexical and real path
  (`fs-guard`); it is a registered worktree or a scratch directory the tool created; `git status` is
  clean and every local commit is reachable from a remote ref; the path is not referenced by any open
  WP's state, any incident record or the pinned-authority cache. Anything that fails a condition is
  reported, not removed. The tool refuses `..` chains, drive-relative forms, bare drives, UNC and
  absolute targets exactly as the `CLAUDE.md` rule requires.
- Probes and controls that write or delete use the kit's `fs-guard` (Node) or a Python equivalent;
  `minion-process` refuses to register a control recipe that does not call it.
- **Containment guard precision, Owner-governed** (`RW-17`, `K5`). The outside-root hook is the
  Owner's safety rule and this record proposes no weakening of it. The proposal is for the kit to
  ship a guard that tokenizes the shell command, tracks `cd`, and classifies only path-like arguments
  of mutating commands, so that `https:`, `try:`, `Co-Authored-By:` or `s:` inside a word stop costing
  a turn each; and to keep every real incident shape blocking through the replay suite below (the
  2026-10-10 `a\..\..` recursive remove, the writable `C:` home bind mount, drive-relative `X:foo`, UNC
  paths, junction escapes). Precision changes are accepted only with those replays green, and only by
  the Owner.
- **Verified gate launchers** (`RW-18`, `K6`). The profile's `gates:` entries reference launchers the
  kit ships per runtime (container recipe, cached and compiled-here native dependencies, fail-loud log
  capture with exit codes preserved, no caller-variable clobbering), each with a self-test, instead of
  free-text commands. The E:-only containment of Docker bind mounts lives here too.
- **Fault injection must prove it fired** (`RW-19`, `K7`). The feasibility-matrix and control-recipe
  templates carry the `CE-L12D007-02` rule: every planned fault or selection reports `fired` or
  `unfired`; the comparator never credits a row whose planned call the binding never made; a call the
  pinned authority itself never makes on a platform is "not applicable" and its outcomes are still
  compared. This generalizes `#272`'s baseline rule and gets a replay test rather than per-layer
  rediscovery.
- The kit ships an **incident replay suite**: each `lessons/<id>.md` has a test that reproduces the
  mechanics of the incident against the tool (flattened body, `\| tail &&`, fabricated governance
  source, drive-root target, writable home mount, stale ready claim, duplicated dispatch, vacuous
  comparator) and must fail closed. This is Warp's benchmark idea applied to the process itself;
  `minion-process` already has historical-replay tests for `#49`, `#79` and `#88`, so this generalizes
  an existing pattern.

### 6.8 Control plane: one writable surface for both agents (RW-11, RW-12, RW-13)

The control plane must be writable by every agent that holds a verdict, or every verdict costs a
relay turn and a transcription risk. For most of Layers 11–13 Codex's session had no GitHub write path
and 192 verdicts were relayed (§2.5). That constraint is historical (`PROC-KIT-R004.4`, `K9`): on
2026-10-10 and 2026-10-11 Codex posted its own verdicts and committed `#199` state through
`minion_process` (issuecomments 6102670593, 6102913331, 6103008491, 6103179882, 6103236644, each
followed by a verified commit). Two options, selectable in the profile:

- **`state-file` backend (Minion-Memory's choice).** Current state lives in `process/state/<WP>.yaml`
  on a control branch of the docs repo; review records are files committed by the reviewer; the
  commit rule's round trip is a git object comparison instead of a re-fetch. Both agents write with
  plain git. GitHub stays the mirror and the PR surface for merges.
- **`github-issue` backend (Minion-Agent today).** Both agents write through `minion_process`, as
  Codex now does. The question is reliability under the harness's approval policy and network, not
  capability.

Decision 5 (§7) is therefore framed on current evidence: the measured reliability of Codex's present
GitHub path (dispatches that end in `REMOTE_SYNC_BLOCKED` or a relay, per WP) against the state-file
backend's cost of a second surface to keep in sync. The relay count stays in this record as historical
cost, not as a present constraint.

In both backends:

- **Review records are files on the candidate branch, not PRs.** The reviewer commits
  `assurance/reviews/<wp>-<type>-<n>.md` with the §6.6 header and pushes (or hands Claude the file
  with its hash, as today, as a fallback only). The §11.2.1 rule becomes the default, which ends the
  review-PR sprawl and the bulk-close cleanups.
- **Owner decisions are governance files, written once.** `minion-process governance record` writes
  `reference/governance/<date>-<topic>.md` verbatim from the Owner's text, computes its hash, and
  every citation is a link plus hash. No decision is pasted into three issues again, and a truncated
  transcription fails the hash check instead of becoming provenance.
- **Status is registry-only** (`certification-registry-design.md`, which Minion-Memory adopted from
  day one): the 39 status-only PRs disappear.

### 6.9 Lessons annex (RW-05, RW-14)

Each rule in `WORKFLOW.md` is one paragraph: the rule, a **one-sentence rationale**, and links to its
`lessons/<id>.md` record **and** its replay test (`K8`). The Layer-08/09/11/12/13 case histories now
embedded in §7, §9.1, §9.2, §9.3, §9.4, §9.7, §9.8, §10, §11.8.4, §11.8.10 and §11.8.11 move to
`lessons/L09-R015.md`, `lessons/PROV-010.md` and so on, with the same text preserved. The normative core
should fit in about 400 lines; agents read it under time pressure, so the discriminating context stays
one sentence in the core and one hop away in full. Role files (`CLAUDE.md`, `AGENTS.md`) shrink to
ownership and the environment rule, and point at the profile for everything else.

A new rule enters `WORKFLOW.md` only with a `lessons/` record **and**, where the rule is mechanical, a
replay test in the kit (§6.7). `profile validate` (or a kit lint) fails when a rule marked mechanical
has no replay test, so the core cannot drift from its evidence. A rule that cannot be tested stays a
one-paragraph judgement rule and is marked as such.
This turns the current reactive accretion (22 process PRs in six weeks) into the Warp
self-improvement shape: an incident produces a small PR against the kit, with evidence attached, and
the normative text stops growing with every incident.

---

## 7. Owner decisions

Each item below is a separate decision. The Owner's 2026-10-11 message (§7.1) approved the
**direction** of this record and the **project name**; it did not decide any item individually, and
none of them is enacted by this record. Each lands, if at all, through the existing review and
authorization gates: a reviewed process PR for mechanics, an explicit recorded Owner decision for
anything that changes authority, acceptance or a delegation.

1. **Create the kit as a separate repository** (`EGAILab/minion-process`, project name Minion-Process)
   seeded from `minion-agent-docs/process/**` and `process/tools/`, with Minion-Agent as its first
   consumer and Minion-Memory as the second. The alternative, keeping the kit inside
   `minion-agent-docs` and having other projects pin a path, keeps the current copy-and-adapt cost.
   *Status: DECIDED 2026-10-11, "go, a new project" (§7.1). Creating the repository and the
   `Minions/Minion-Process` checkout are outside-root actions and still need the Owner's explicit
   confirmation at execution time under the filesystem-containment rule; P1 starts after `#199` is
   CLOSED.*
2. **Adopt work-package kinds with consequence classes** (§6.2) and the measured stage-skip rule
   (§6.3). As revised, this changes no route for governing work and removes only the convergence
   checkpoint ceremony for mechanical work, with independent review and the final review of the
   changed candidate kept. It still needs an explicit decision because it adds a classification step to
   the state schema and makes the class upgrade automatic. *Status: DECIDED 2026-10-11, "adopt as
   revised" (§7.1); lands through the P2 process PR on the full route.*
3. **Extend the standing delegations** (`minion-agent#75`, Minion-Memory `G-009`) to cover routing per
   the kit's routing table (§6.4), and confirm the closed Owner-only list. *Status: DECIDED 2026-10-11
   in three parts (§7.1): routing delegated for five of the six §6.4 rows, with the convergence-trigger
   row as a notify-and-proceed carve-out; the Owner-only list stays open-ended and gains four items,
   closing it is revisited after P2 and P3; Minion-Memory `G-009` decides separately in P4. Until the
   `#75` amendment is confirmed by the Owner, the current delegation scope and all existing scoped
   authorizations apply unchanged.*
4. **Unify the two CLIs** into the kit's `minion_process` with `github-issue` and `state-file` backends;
   retire `mneme-process` once the kit passes Minion-Memory's existing tool tests. *Status: DECIDED
   2026-10-11, "unify" (§7.1); mechanics under the existing delegations, after P3.*
5. **Choose Minion-Agent's control-plane backend** (§6.8), framed on current evidence: the measured
   reliability of Codex's present GitHub write path through `minion_process` against the `state-file`
   backend Minion-Memory uses. *Status: DECIDED 2026-10-11, "stay on GitHub issues" (§7.1); the
   `github-issue` backend remains Minion-Agent's control plane and no second surface is adopted.*

### 7.1 Decision record

**Owner, in chat, 2026-10-11**, replying to the summary of §1–§8 of the first draft (quoted verbatim):

> Approve the direction, project name preferred Minion-Process, unless you have better suggestions

**Owner, in chat, later on 2026-10-11**, after Codex's and the second reviewer's verdicts on the draft
(quoted verbatim):

> Claude will drive the review and apply the process change for minion agent, and will send the
> feedback later

**Owner sequencing decision, 2026-10-11**, relayed by the Claude session in `w1:p1` (quoted as relayed):

> Wrap up #199 first before process changes (a clean cut)

What these settle, and what they do not (the first draft of this section claimed more, and
`PROC-KIT-R001` corrected it):

- **Settled: the direction and the name.** The record's analysis and the shape of §6 are the agreed
  direction for Minion-Process. The project is named **Minion-Process**: repository slug
  `EGAILab/minion-process` (lower-case, matching `minion-agent` and `minion-agent-docs`), local
  directory `Minions/Minion-Process` beside `Minion-Agent` and `Minion-Memory`, and the CLI keeps its
  existing name `minion-process`. Claude raised no counter-suggestion.
- **Settled: who drives what, and when.** The Claude session in `w1:p1` (the L12-D007 Python/shared
  owner) drives the review and the Minion-Agent process changes after this record is agreed, and will
  send feedback later; it starts only after `L12-D007` (`#199`) is closed. This record (P0) stays with
  the session that authored it (`w1:p8`). Codex remains the independent reviewer.
- **Not settled: decisions 1–5.** "Approve the direction" does not adopt the consequence classes, the
  automatic upgrade, the routing table, the Owner-only list, a delegation amendment, the CLI merger or
  a backend. Each remains subject to the gates named at the top of §7. In particular, nothing in this
  record supersedes a prior convergence decision or an existing scoped authorization, and §8's phases
  do not use the rules they would introduce to approve their own adoption.
- **Not settled: P1's outside-root actions.** Creating the repository and its local checkout is
  outside the Minion-Agent project root and happens only with the Owner's explicit confirmation under
  the filesystem-containment rule. *(Settled 2026-10-12, recorded on `minion-agent#205`: repository
  "public is fine"; checkout "Option 3 is ok", a second allowed root `Minions/Minion-Process` in the
  guard hook, literal path; ownership "I want you to be the owner of the process repo and main
  driver", with `w1:p1` as the consumer that pulls each release into Minion-Agent; sequencing "get all
  new/improved process in before starting other Minion-Agent work".)*
- Claude's recommendation on decision 5, for the Owner to accept or reject: measure first. One or two
  WPs of Codex posting through `minion_process` under the github-issue backend, counted per §9, decide
  whether a second surface is worth its sync cost. *(Superseded the same day: the Owner chose "stay on
  GitHub issues" below.)*

The bullets above are the state as of revision 2. The decisions were taken later on 2026-10-11, after
revision 2 was approved and merged; they are recorded below and durably on `minion-agent#205`.

**Owner, in chat, 2026-10-11**, after Claude listed the five open decisions one by one with their
options (quoted verbatim; durable record: `minion-agent#205` issuecomment-6104625203):

> Decision 1: go, a new project; Decision 2: adopt as revised; Decision 3: need further clarify and
> discussion; Decision 4: unify; Decision 5: stay on GitHub issues

**Owner, in chat, 2026-10-11**, on decision 3, after Claude split it into three parts and gave a
recommendation for each (quoted verbatim; durable record: `minion-agent#205` issuecomment-6104953933):

> What's your suggestions

> As you suggested

What these settle:

- **Decision 1 — go.** Minion-Process is a new project (`EGAILab/minion-process`,
  `Minions/Minion-Process`). The decision does not substitute for the containment confirmation: the
  repository creation and the local checkout are outside-root actions and each is confirmed by the
  Owner at execution time. P1 starts after `#199` is CLOSED.
- **Decision 2 — adopt as revised.** §6.2 and §6.3 as written in revision 2: five kinds; governing vs
  mechanical by consequence predicate; reviewer-confirmed class; automatic recorded upgrade; two-party
  downgrade; the final review of the changed candidate on every route; stage skip only with measured
  rows and reviewer consent. Lands through the P2 process PR on the full route.
- **Decision 3 — as Claude recommended, in three parts.**
  - *3.1 Routing by rule: extend, with one carve-out.* Five of the six §6.4 rows are delegated under
    `minion-agent#75`, each route recorded by its rule ID: the targeted-closure fix pass with §11.8.10
    invalidation; progressing a semantically independent WP; `HANDOFF_BLOCKED` with unchanged
    re-dispatch; the mechanical-WP risk question filed with a stated default after two rounds without
    new discriminating evidence; and the automatic class upgrade (which only adds review). The
    convergence-trigger row (A/B/C triggers and the governing-WP §11.8 trigger check) is **not** a
    silent route: when it fires, Claude records the counters, notifies the Owner with the default route,
    and proceeds on that default unless the Owner objects within the round. Rationale: §2.3 and §9; the
    Layer 12–14 long episodes were productive in every round, so a counted trigger is a signal, not
    proof that review has stalled.
  - *3.2 Owner-only list: not closed yet.* `#75`'s list stays open-ended (its item 10 is kept). Four
    items are added rather than substituted: consequence-class downgrades, remote creation, risk
    acceptance, and amending the delegation itself. Closing the list is revisited after P2 and P3 have
    shipped, using the §9 metric "Owner questions per WP, split into routing vs semantic vs risk".
  - *3.3 Minion-Memory `G-009`: separate, later.* No change to `G-009` or `G-018`–`G-027` now;
    Minion-Memory decides its own extension when it re-adopts the kit in P4.
- **Decision 4 — unify.** One `minion_process` with `github-issue` and `state-file` backends;
  `mneme-process` retired after the kit passes Minion-Memory's tool tests. Mechanics after P3.
- **Decision 5 — stay on GitHub issues.** The `github-issue` backend remains Minion-Agent's control
  plane; no second surface is adopted; Claude's measure-first recommendation is withdrawn; the §9
  metrics are still collected as data.
- **What remains Owner-only here.** The `#75` amendment that enacts 3.1 and 3.2 is edited or confirmed
  by the Owner (only the Owner amends the delegation); the driving session (`w1:p1`) prepares its exact
  text. Until that amendment is in `#75`, the current delegation scope applies unchanged.

Sequencing and ownership are unchanged by these decisions: nothing in P1–P4 starts before `#199` is
CLOSED; Claude `w1:p1` drives; Codex is the independent reviewer. The Owner asked on 2026-10-11 for this
revision (the §7.1 record and Codex's two editorial notes) to be made ahead of that cut; it is a
documentary change to the record and introduces none of the P1–P4 mechanics.

---

## 8. Migration plan

| Phase | Content | Depends on |
|---|---|---|
| P0 (this PR) | this retrospective; `process-history.md` entry | independent process review (Codex), second review (`w1:p1`), final review of the changed candidate |
| P1 | `EGAILab/minion-process` created and seeded from current `process/**` and `process/tools/`; `profile.yaml` for Minion-Agent; `WORKFLOW.md` split into core + lessons with text preserved; `profile validate` | decision 1 enacted; Owner confirmation for the repository and the `Minions/Minion-Process` checkout; `#199` closed (Owner sequencing). **DONE 2026-10-12:** kit 0.1.0 (`minion-process#1` APPROVED by Codex at `645d9120`, merged `0876e11d`, tag `v0.1.0`; coordination `minion-agent#211`); Minion-Agent profile and pin in `process/profile.yaml`; `agent-workflow.md` stays in force until the P2 cut-over |
| P2 | consequence classes and kinds in the state schema and transitions table; routing table; delegation amendments | Owner decisions 2 and 3 (recorded, §7.1); the `#75` amendment text confirmed by the Owner before or with the PR; `#199` closed. **DONE 2026-10-12:** `#75` Amendment 2 posted by the Owner (issuecomment-6115715796); kit 0.2.0 (`minion-process#2` APPROVED by Codex at `f026ea1c`, merged `38c2845d`, tag `v0.2.0`; coordination `minion-agent#212`); Minion-Agent cut over: `process/profile.yaml` pin 0.2.0 with `routing: true`, process files are pointers to the kit, `process/tools` retired |
| P3 | structured review-record header; `metrics` and `convergence counters`; composite verbs; `session start` and `cleanup`; `handoff`/`dispatch` with reply-to; launchers; fault-fired rule | P1 |
| P4 | Minion-Memory re-adopts by profile; `mneme-process` retired; incident replay suite seeded from both projects' lessons | decision 4, P3 |

Every phase runs under the **current** rules of `agent-workflow.md` and `coordination-state.md`, not
under the rules it proposes. P1, P3 and P4 change tooling that writes state, merges, dispatches and
deletes, so they are governing changes (§6.2) and take the full route, including convergence if a
trigger fires. P2 changes transitions and delegations and additionally needs the Owner decisions first.
The first measurement of the §6.2 signal is taken on these phases, as data, not as a rule in force.

---

## 9. Metrics to watch after adoption

Per WP, emitted by the tool (§6.6), compared with the Layer 12–14 baselines above:

- review events to contract approval, and complete vs targeted rounds;
- **rounds without new discriminating evidence** (a rejection that adds no witness, finding or matrix
  row), per WP and per consequence class; this replaces "review rounds" as the waste signal, because
  §2.3's long episodes were productive in every round;
- semantic dimensions discovered after implementation started (the metric §14.6 already names as the
  one to drive down);
- Owner questions per WP, split into routing vs semantic vs risk;
- hand-off prompt bytes written by hand; dispatches that needed inspection or were misrouted;
- `REMOTE_SYNC_BLOCKED` and relayed verdicts per WP (decision 5's evidence);
- gate launches per gate result (harness failures vs real failures);
- wall-clock from `SCOPING` to `CLOSED`, by kind and class;
- escaped defects found after certification (must not rise).

A mechanical WP that accumulates rounds without new evidence, or a `semantic` WP whose late discoveries
do not fall, is the signal to revisit this proposal rather than add another rule. A long episode whose
every round found something is not.

---

## 10. Revision history

### Revision 5 (2026-10-12): P2 complete; Minion-Agent cut over to the kit

Documentary. §8 P2 row marked DONE: the Owner posted `minion-agent#75` Amendment 2 (routing by rule
`RT-1`–`RT-6`, Owner-only additions 11–14, list open-ended); kit 0.2.0 landed kinds, consequence
classes, measured stage skips, the routing table and the trigger-notification rule (`minion-process#2`
@ `f026ea1c`, merged `38c2845d`, tag `v0.2.0`; coordination `minion-agent#212`). Companion changes in
this PR: `process/profile.yaml` (pin 0.2.0, `routing: true`), `process/agent-workflow.md` and the other
process files become pointers to the kit (full text at `4dd10da5`), `process/tools/` retired in favour
of the kit CLI, and the process-history entry. This record itself stays in this repository as history.

### Revision 4 (2026-10-12): P1 complete; ownership, repository and checkout decisions recorded

Documentary. §8 P1 row marked DONE with the kit release (`minion-process#1` @ `645d9120`, merged
`0876e11d`, tag `v0.1.0`; coordination `minion-agent#211`, Codex review 1 CHANGES REQUESTED
`PROC-KIT-P1-R001`–`R003`, re-review APPROVED). §7.1 outside-root bullet annotated with the 2026-10-12
Owner decisions (`minion-agent#205`). Companion changes in this PR: `process/profile.yaml` (the live
Minion-Agent profile, kit pin 0.1.0), the kit paragraph in `agent-workflow.md`'s header, and the
process-history entry.

### Revision 3 (2026-10-11): Owner decisions recorded; Codex's editorial notes

Documentary revision after revision 2 was APPROVED (record-only) by Codex's re-review at `5cda5347` and
merged as `5c562008`. No normative or proposal text changes.

| Item | Change in this revision |
|---|---|
| Owner decisions 1–5 (chat, 2026-10-11; durable on `minion-agent#205`, issuecomments 6104625203 and 6104953933) | §7.1 appended with the two Owner messages quoted verbatim and what each decision settles; §7 status lines; §8 P2 dependency row; status line; `process-history.md` entry |
| Codex re-review editorial note 1: §1 item 3 compressed | item 3 expanded with the §2.4/§6.4 qualification that route defaults do not replace the conditions of the scoped authorizations `G-018`–`G-027` |
| Codex re-review editorial note 2: §2.1 counting command | the illustrative `origin/master` listing replaced by the reproducible recipe `git ls-tree --name-only cbb2873:assurance/layers` filtered to `.md`, which gives 330 |

### Revision 2 (2026-10-11): remediation of review 1 on `minion-agent-docs#287` @ `e54335da`

Reviews: Codex (`PROC-KIT-R001`–`R004`, CHANGES REQUESTED) and a second independent Claude session
(`w1:p1`, `K1`–`K9`, CHANGES REQUESTED), both published verbatim on the PR. Both supported the direction.

| Finding | Change in this revision |
|---|---|
| R001 approval scope overstated | §7 reframed: each decision open, gates named; §7.1 rewritten around what the three Owner messages settle and do not; §8 phases run under current rules and do not use the proposed rules to approve themselves; history entry aligned; status line |
| R002 process-kind route drops assurance; §6.3 skip | §2.3 counterfactual removed and the defect evidence recorded; §6.2 redesigned around consequence predicates with the full route for governing changes and the final review kept everywhere; §6.3 requires measured rows, reviewer consent, never the final review; §3 bullets added; §6.4 table rows replaced |
| R003 blind re-send; age-based pruning | §6.5 send-once/verify/no-retry protocol with the blocked-pane prohibition; §6.7 cleanup conditions, report-not-delete |
| R004.1 330 records | §2.1 predicate and residual seven files |
| R004.2 50 closed-unmerged, authorization | §2.5 row, RW-12, §1 |
| R004.3 unfrozen survey | §2.5 rows qualified; new §2.7 method and limits |
| R004.4 Codex write path | §1 item 4, §2.5, §6.8, RW-11, decision 5 reframed |
| R004.5 incident dates and attribution | §2.6 rows rewritten (2026-10-11 launcher by Codex; probe by Claude; one `E:\` incident plus a documentation gap); safeguards-not-proof sentence |
| R004.6 G-018..G-027 scope | §2.4 rewritten; §6.4 closing paragraph |
| R004.7 escaped defects; Layer 14 causality | §1 first paragraph (`#144`, `#147`, `#163`); §2.1 and §2.5 observation wording; §4 |
| K1 consequence decides the route; round count is not the signal | §2.3 `CE-L12D007-01` evidence; §6.2 predicates and signal; §9 metric replaced |
| K2 self-assigned kind | §6.2 "Who classifies": reviewer confirmation, automatic recorded upgrade, two-party downgrade |
| K3 delta size does not predict dimensions | §6.3 rewritten with the `L12-D007` evidence |
| K4 reply-to per dispatch; measured stall behaviour | §6.1 profile (`default_pane`), §6.5, RW-15, RW-16 |
| K5 containment-hook precision | §6.7 Owner-governed proposal with replay conditions; RW-17 |
| K6 verified gate launchers | §6.1 `gates:`, §6.7; RW-18 |
| K7 fault injection must prove it fired | §6.7 template rule; RW-19 |
| K8 lesson and replay test one hop away | §6.9 |
| K9 Codex posts through `minion_process` | §6.8, §7 decision 5, §7.1 recommendation |
