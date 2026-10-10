# Workflow retrospective: Layers 11–14 and the Minion-Memory adoption — towards Minion-Process, a reusable process kit

**Status:** DIRECTION APPROVED by the Owner (chat, 2026-10-11; record in §7.1), awaiting independent
process review. Process-only. It reopens no semantic finding, no certification and no
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

The process is reliable where it matters: every HIGH-value semantic finding in Layers 11–13 was caught
by independent review before certification, and the Layer 13 retrospective already moved the two big
costs (late semantic discovery, hand-executed mechanics) into the feasibility matrix, hazard families,
gate tiers, lean state and `minion-process`. Those changes are correct and should be kept.

The remaining cost is coordination volume. Six weeks of Layers 11–14 produced 1,274 GitHub comments
(about 0.9 M tokens), 192 of them Claude relaying Codex's verdicts verbatim because Codex cannot write
to GitHub, 131 review-record PRs of which 44 were bulk-closed as stale, and 39 PRs that only flipped
status strings. Four costs explain most of it, and all four showed up again when the process was
transplanted to Minion-Memory:

1. **The process is not proportional to the kind of work.** The convergence protocol, designed for
   Pi-parity semantics, was applied with full force to its own tooling: `CE-PROC-L13-01` took five
   checkpoint revisions, one §11.8.10 invalidation and four targeted closures to harden a YAML loader
   for an issue body; Minion-Memory's `WP-P01` (process hardening, zero product requirements) took
   three complete reviews, a 688-row characterization matrix, two Owner-routed fix passes and a day of
   both agents before any Layer-01 contract existed. Process tooling needs tests, not convergence.
2. **The process is a document, not a product.** Reuse was copy-and-adapt: Minion-Memory adopted
   `agent-workflow.md` "by reference" to a pinned SHA, re-derived the taxonomy, the hazard families and
   the state schema, and forked the CLI (`mneme-process` alongside `minion-process`). Two
   implementations of one state machine now exist and will drift. Nothing in Minion-Agent's later
   fixes reaches Minion-Memory without a manual pin bump and re-adaptation.
3. **Routing still goes through the Owner.** In Minion-Memory the Owner answered four routing
   questions in nine hours (`G-018`, `G-019`, `G-024`, `G-027`): all were "how should I proceed?"
   questions whose answers the convergence protocol already prescribes. Warp's foreman model puts
   routing in policy and reserves the human for spec approval, genuine ambiguity and merge. Minion
   should do the same, and reserve the Owner for path-C semantic choices, scope, and risk acceptance.
4. **The control plane is only half writable.** The workflow assumes agent-to-agent hand-off through
   GitHub, but Codex's session has no GitHub write path, so every Codex verdict is a Claude relay
   with a file hash, and Owner decisions are transcribed into comments (118 times, some triplicated,
   nine damaged in transit). Minion-Memory avoided this by using state files and git as the control
   plane; Minion-Agent should either do the same or give Codex a working write path.

The proposal (§6) is a versioned **process kit** with a per-project **profile**, work-package
**kinds** with a route per kind, generated hand-offs, metrics collected by the tool, and a lessons
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

331 files in total. Layer 14's count is the first evidence that Phase A worked: two WPs, two deltas,
no convergence episode, closed inside two weeks.

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

Both episodes found real defects, and §11.8 behaved exactly as written. The question this
retrospective asks is whether a workflow validator deserves the same assurance route as a
Pi-parity semantic surface. It does not: the validator's failure mode is a refused or mis-shaped
state write that the round-trip check and the next reader catch, not a shipped behavioral divergence.

### 2.4 Owner routing questions in Minion-Memory (2026-10-10)

| Record | Question asked | Already prescribed by |
|---|---|---|
| `G-018` | "Survived three reviews, how should I route it?" | §11.8 trigger A/C: enter convergence |
| `G-019` | "Start WP-01 in parallel?" | §11.15 parallel work with dependency edges |
| `G-024` | "Targeted closure found 5 defects, how should I proceed?" | §11.4 remediation → targeted closure |
| `G-027` | "One regression remains, how should I proceed?" | same |

Each answer was the process default. The cause is the delegation text (`G-009`) listing *acceptance*
and *status* but not *routing*, so the agent escalated to stay inside its authority. The fix is in
§6.4.

### 2.5 GitHub interaction volume (read-only `gh` survey, 2026-10-11)

| Signal | Measurement |
|---|---|
| Comments | 1,274 (811 code repo, 463 docs repo), about 3.69 M characters, roughly 0.9 M tokens of coordination text |
| Comment length | issue comments: median 1,669 chars, p90 8,024, max 17,390; 235 of 577 exceed 3,000 chars |
| Codex text relayed by Claude | 192 comments are "posted by Claude on Codex's behalf, verbatim" with a file hash, because Codex's session cannot reach GitHub (MCP approval policy, connection refused); 13 `REMOTE_SYNC_BLOCKED` |
| Review-record PRs in the docs repo | 131 of 286 PRs are `review/*` records; 81 merged, **44 bulk-closed as stale on 2026-10-10 by Owner direction** |
| Status-only PRs | 24 code + 15 docs PRs exist only to flip status strings |
| Formal GitHub reviews | 3 in total; every verdict lives in comments |
| Owner decisions | 118 comments are Owner decisions transcribed verbatim by an agent; some posted three times across issues (17,390 chars each); 9 arrived truncated or collapsed |
| Errata | 12 explicit correction comments (wrong SHA, drafts called ready, duplicate posts, a wrongful quarantine) |
| Heaviest issues | `#29` (L11 Pass 2): 66 comments, 24 Claude→Codex and 24 Codex→Claude transitions in 2.9 days; `#48` (WP-13.1): 66 comments, 34 negative verdicts, 7.5 days, body 71.8 KB; `#199` (L12-D007, open): 5 checkpoint reviews + 2 targeted closures in 3 hours on 2026-10-10 |
| Process-change PRs | 22 docs + 2 code; nearly every rule landed within 48 hours of the incident that motivated it |
| Layer wall-clock | L11 ≈ 4.5 d; WP-12.1 2.3 d; Layer 13 16.6 d; Layer 14 1.1 and 1.6 d per WP |

Layer 14 is the first layer run end to end under the feasibility matrix and gate tiers, and it is the
fastest since Layer 10. The per-item review-round count has not fallen, however: `#199` ran nine
review events in one evening.

### 2.6 Reliability incidents, 2026-09 to 2026-10

| Incident | Root cause class | Fixed by |
|---|---|---|
| Fork subagent fabricated an Owner decision, pushed branches, opened PRs | side effects available to a read-only role | §11.9–§11.12 |
| PowerShell flattened a coordination body | transport round trip unchecked | §11.1.1 commit rule, `minion-process apply` |
| `minion_process apply ... \| tail && gh issue close` closed an issue on a refused write | dependent action not gated on the tool's exit status | interim operator rule; composite verbs proposed |
| Stale "PRs are ready" claim written before the command ran | statement ahead of state | lesson recorded |
| Probe resolved `..` chain to `E:\` and removed recursively | destructive op without containment check | outside-root hook, `fs-guard.mjs` |
| herdr prompt stalls; Codex budget exhausted mid-pass | harness limits | §11.17 completion notification, resumable checkpoints |
| Reviewer sandbox lost Docker/npm; two final reviews withheld | authority execution coupled to live network | `authority-dependencies.md` |
| Linux launcher bound `C:\Users\erick` into Docker as a writable cargo home (2026-10-10, `#194`) | mount path not containment-checked | same class as the probe incident; §6.7 |
| 2026-10-10 `E:\` deletion incident | recorded in `CLAUDE.md` only, not on GitHub | §6.9 lessons annex gives incidents one durable home |

The common root is that a side-effecting action (publish, close, merge, delete, dispatch) was executed
by prompt discipline. Every fix moved it behind a guard. §6.6 finishes that move.

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
- the standing delegation (`#75`) and the filesystem-containment rule.

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
exact-SHA, negative-control and convergence rules are stronger and are the reason Layers 11–13 shipped
without escaped parity defects. Warp optimizes PR throughput; Minion optimizes certified semantic
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
| RW-11 | The "agent-to-agent GitHub control plane" is half true: Codex cannot write to GitHub | 192 verbatim relays, 13 `REMOTE_SYNC_BLOCKED`, hash-of-file provenance in comments; Minion-Memory sidestepped it with a state-file backend and git | efficiency (every Codex verdict costs a Claude turn), reliability (transcription errata) | §6.8 |
| RW-12 | Review records as PRs | 131 `review/*` PRs, 44 bulk-closed stale, 54 closed unmerged overall; §11.2.1 already says a PR per review event is not required | efficiency | §6.8 |
| RW-13 | Owner decisions transcribed by agents into comments | 118 transcriptions, triplicates of 17 KB, 9 damaged in transit | reliability (governance provenance), efficiency | §6.8 |
| RW-14 | Rules accrete reactively | 22 process PRs, most within 48 h of an incident; the normative text grew from 1,548 to 1,893 lines in three weeks | efficiency (read cost), reliability (two agents weighting different paragraphs) | §6.9 |

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
agents:
  claude: {roles: [coordinator, shared-contract-owner, implementer:python], harness: claude-code, pane: w1:p1}
  codex:  {roles: [reviewer, implementer:rust], harness: codex, pane: w1:p2}
taxonomy_aliases: {IMPLEMENTATION_DEFECT: PI_PARITY_DEFECT}   # empty for generic names
hazard_families: [python, rust, json, yaml, sqlite, fs, unicode, async]
gates:
  python: {g0: "...", g1: "...", g2: "...", g3: "..."}
  rust:   {g0: "...", g3: "..."}
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

Triage assigns one **kind** at intake, recorded in the state block. Each kind has its own legal route;
the transition table is per kind instead of one table with exceptions.

| Kind | Examples | Route | Convergence | Feasibility matrix | Reviews |
|---|---|---|---|---|---|
| `semantic` | a layer WP owning product requirements | full §11.4 | yes (§11.8) | mandatory when high-risk | complete + targeted + final |
| `delta` | post-certification delta on a certified layer (`L0506-D00x`) | contract delta → impl → targeted → closure | yes, scoped to the delta | mandatory | targeted first; complete only if blast radius recorded |
| `process` | kit/tool/workflow hardening (`PROC-L13`, `WP-P01`) | draft → one review → remediation → targeted closure → CLOSED | **no**; after 2 rejected rounds: Owner picks accept-with-tests or continue | no | ≤ 2 complete rounds by default |
| `scoping` | read-only scoping (`WP-14.SCOPE`) | `SCOPING → CLOSED` on approved artifact | no | no | one |
| `status` | registry/status sync, documentary | tool-validated; no review | no | no | none; `minion-process` checks consistency |

The `process` kind encodes a **proportionality rule**: a workflow helper is validated by its tests,
its negative controls and one independent review. Findings on it are ordinary bugs with regression
tests. A reviewer who believes a tooling defect is a real assurance hole states that in one line and
the Owner decides whether to convert the WP to `semantic` treatment. This would have ended
`CE-PROC-L13-01` after revision 2 and `CE-P01-01` after the first targeted closure, keeping every
witness that was written and dropping the checkpoint ceremony.

### 6.3 Stage skipping (RW-01)

Warp's foreman skips Triage and Planning when a request is already well defined. Minion's equivalent:
a `delta` whose contract delta is one additive row, with the feasibility matrix rows already
`AUDITED` by the parent WP, goes straight to implementation review. The kit records the skip and its
reason in the state block (`skipped: [CONTRACT_REVIEW], reason: ...`). The exact-SHA and negative-control
rules are unchanged; only stages that add no discriminating step are skipped.

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
| `process`-kind WP rejected twice | ask the Owner once: accept-with-tests or continue |

Owner-only questions become a closed list in the kit: path-C semantic choices, scope and layer-order
changes, intentional divergence, risk acceptance, authority changes, remote creation, destructive
history, and amending the delegation itself. Each Owner question is filed with its options packet and
the default the process would otherwise take, so the Owner can answer "default" in one word.

### 6.5 Generated hand-offs and dispatch (RW-04)

`minion-process handoff <wp> --type <review-type>` renders the hand-off prompt from the state block,
the profile and the kit template: exact SHAs, scope and non-scope, requirement IDs, artifacts to read,
gate tier and commands, allowed verdicts, the record path to write, the completion-notification
instruction with the sender's pane, and the independence clause. The author adds only the WP-specific
semantic notes. `minion-process dispatch <wp>` sends it to the receiving pane, confirms the prompt was
accepted (re-sends on `agent_prompt_stalled`), and records the dispatch in history. Codex's role file
tells it to run `minion-process handoff-check` first and to refuse a prompt that disagrees with the
state block.

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
  prune worktrees older than the profile's retention (default 7 days, detached only), and print the
  WPs the current agent may progress. This replaces the §12.2 checklist and Minion-Memory's
  clone-fresh workaround.
- Probes and controls that write or delete use the kit's `fs-guard` (Node) or a Python equivalent;
  `minion-process` refuses to register a control recipe that does not call it.
- The kit ships an **incident replay suite**: each `lessons/<id>.md` has a test that reproduces the
  mechanics of the incident against the tool (flattened body, `\| tail &&`, fabricated governance
  source, drive-root target, stale ready claim) and must fail closed. This is Warp's benchmark idea
  applied to the process itself; `minion-process` already has historical-replay tests for `#49`, `#79`
  and `#88`, so this generalizes an existing pattern.

### 6.8 Control plane: one writable surface for both agents (RW-11, RW-12, RW-13)

The control plane must be writable by every agent that holds a verdict, or every verdict costs a
relay turn and a transcription risk. Two options, selectable in the profile:

- **`state-file` backend (Minion-Memory's choice).** Current state lives in `process/state/<WP>.yaml`
  on a control branch of the docs repo; review records are files committed by the reviewer; the
  commit rule's round trip is a git object comparison instead of a re-fetch. Both agents write with
  plain git, which Codex can do. GitHub stays the mirror and the PR surface for merges.
- **`github-issue` backend (Minion-Agent today).** Keep it only if Codex gets a working `gh` path.
  Otherwise the 192-relay pattern continues.

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

Each rule in `WORKFLOW.md` is one paragraph plus a `lesson:` reference. The Layer-08/09/11/12/13 case
histories now embedded in §7, §9.1, §9.2, §9.3, §9.4, §9.7, §9.8, §10, §11.8.4, §11.8.10 and §11.8.11
move to `lessons/L09-R015.md`, `lessons/PROV-010.md` and so on, with the same text preserved. The
normative core should fit in about 400 lines; the rationale stays one click away and keeps growing
without making every read longer. Role files (`CLAUDE.md`, `AGENTS.md`) shrink to ownership and the
environment rule, and point at the profile for everything else.

A new rule enters `WORKFLOW.md` only with a `lessons/` record **and** a replay test in the kit
(§6.7) where the rule is mechanical. A rule that cannot be tested stays a one-paragraph judgement rule.
This turns the current reactive accretion (22 process PRs in six weeks) into the Warp
self-improvement shape: an incident produces a small PR against the kit, with evidence attached, and
the normative text stops growing with every incident.

---

## 7. Owner decisions

1. **Create the kit as a separate repository** (`EGAILab/minion-process`, project name Minion-Process) seeded from
   `minion-agent-docs/process/**` and `process/tools/`, with Minion-Agent as its first consumer and
   Minion-Memory as the second. The alternative, keeping the kit inside `minion-agent-docs` and
   having other projects pin a path, keeps the current copy-and-adapt cost.
2. **Adopt work-package kinds and the proportionality rule for `process`-kind WPs** (§6.2). This is
   the one change that reduces review rounds, so it needs an explicit decision that tooling is
   validated by tests plus one independent review rather than by convergence.
3. **Extend the standing delegations** (`minion-agent#75`, Minion-Memory `G-009`) to cover routing
   per the kit's routing table (§6.4), and confirm the closed Owner-only list.
4. **Unify the two CLIs** into the kit's `minion_process` with `github-issue` and `state-file`
   backends; retire `mneme-process` once the kit passes Minion-Memory's existing tool tests.
5. **Choose Minion-Agent's control-plane backend** (§6.8): give Codex a working GitHub write path,
   or move Minion-Agent's current state and review records to the `state-file` backend as
   Minion-Memory already does. Either choice ends the verbatim-relay pattern; leaving it as is does not.

Everything else in §6 is process mechanics under the existing delegations and can proceed as reviewed
PRs once the decisions above are recorded.

### 7.1 Decision record

**Owner, in chat, 2026-10-11**, replying to the summary of §1–§8 above (quoted verbatim):

> Approve the direction, project name preferred Minion-Process, unless you have better suggestions

What this settles, and what it does not:

- The direction of §6 is approved as a whole. Decisions 1–4 proceed under that approval; each
  phase in §8 is still a reviewed `process`-kind PR, and nothing here reopens a semantic finding,
  a certification or an existing governance decision.
- The project is named **Minion-Process**. Repository slug `EGAILab/minion-process` (lower-case,
  matching `minion-agent` and `minion-agent-docs`); local directory `Minions/Minion-Process` beside
  `Minion-Agent` and `Minion-Memory`; the CLI keeps its existing name `minion-process`, so the
  repository ships the tool of the same name. Claude raised no counter-suggestion: the name already
  matches the tool and the two consumers' naming.
- **Decision 5 is still open.** "Approve the direction" does not choose between giving Codex a
  GitHub write path and moving Minion-Agent to the `state-file` backend. Claude's recommendation is
  the `state-file` backend: it is already proven in Minion-Memory, it needs no credential handling
  in Codex's session, and GitHub keeps the roles it is good at (PRs, merges, the certification
  registry). The Owner's choice is recorded here when made.
- Creating the repository and its local checkout is outside the Minion-Agent project root, so P1
  starts only with the Owner's explicit confirmation under the filesystem-containment rule.

---

## 8. Migration plan

| Phase | Content | Depends on |
|---|---|---|
| P0 (this PR) | this retrospective; `process-history.md` entry | independent process review |
| P1 | `EGAILab/minion-process` created and seeded from current `process/**` and `process/tools/`; `profile.yaml` for Minion-Agent; `WORKFLOW.md` split into core + lessons with text preserved; `profile validate` | decision 1 (approved); Owner confirmation for the repository and the `Minions/Minion-Process` checkout (§7.1) |
| P2 | WP kinds in the state schema and transitions table; routing table; delegation amendments recorded | decisions 2, 3 |
| P3 | structured review-record header; `metrics` and `convergence counters`; composite verbs; `session start`; `handoff`/`dispatch` | P1 |
| P4 | Minion-Memory re-adopts by profile; `mneme-process` retired; incident replay suite seeded from both projects' lessons | decision 4, P3 |

Each phase is a `process`-kind WP under the new rules, which is also the first test of the
proportionality rule.

---

## 9. Metrics to watch after adoption

Per WP, emitted by the tool (§6.6), compared with the Layer 12–14 baselines above:

- review events to contract approval, and complete vs targeted rounds;
- semantic dimensions discovered after implementation started (the metric §14.6 already names as the
  one to drive down);
- Owner questions per WP, split into routing vs semantic;
- hand-off prompt bytes written by hand;
- wall-clock from `SCOPING` to `CLOSED`, by kind;
- escaped defects found after certification (must not rise).

A `process`-kind WP that still needs more than two review rounds, or a `semantic` WP whose late
discoveries do not fall, is the signal to revisit this proposal rather than add another rule.
