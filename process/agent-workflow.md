# Minion Agent — Coding Agent Workflow

**Canonical location:** `minion-agent-docs/process/agent-workflow.md`

**Workspace layout:**

```text
Minions/Minion-Agent/
├── .claude/CLAUDE.md
├── .agents/AGENTS.md
├── minion-agent/          # code + conformance + parity manifest
└── minion-agent-docs/     # design + spec + process + assurance
```

`CLAUDE.md` and `AGENTS.md` are role-specific entry points. This file is the shared persistent workflow for both coding agents.

This file contains the persistent project rules shared by the Python/Claude Code and Rust/Codex workflows. `CLAUDE.md` and `AGENTS.md` add role-specific ownership rules.

## 1. Project goal

Minion Agent is one product with one language-neutral semantic contract and two first-class implementations.

For Pi-derived behavior, reproduce Pi's observable semantics as closely as practical. Do not replace Pi behavior with a cleaner, more generalized, or more abstract design merely because it is easier to implement. Minion's plugin/runtime architecture may change ownership, registration, lifecycle, composition, and implementation mechanics; it does not by itself justify changing Pi-visible behavior.

The adopted Pi revision is recorded by the frozen master design. At the time this file was introduced it is:

`b7bb00b936dbe21b8e160b3e89efdec361846699`

If the frozen design later adopts a different Pi baseline, the frozen design wins over this literal SHA.

## 2. Read these before substantive work

Always use the current repository contents, not remembered state.

1. `minion-agent-docs/design/2026-08-20-minion-agent-design.md`
2. `minion-agent-docs/process/implementation-conformance-workflow.md`
3. the current layer's `spec/**` and `assurance/layers/**` artifacts
4. `/pi-parity-manifest.yaml`
5. the applicable canonical scenarios under `/conformance/**`
6. the adopted Pi source for the symbols being implemented or reviewed

Do not assume old prompt SHAs, test counts, scenario counts, file names, or layer status are still current. Fetch first and record actual HEADs.

## 3. Semantic authority

For Pi-derived behavior:

`adopted Pi source -> parity manifest -> normative spec -> canonical conformance -> implementations`

The frozen master design defines architecture, scope, and the mandatory Pi-fidelity goal. Canonical conformance is the executable oracle for the finite examples it covers. The language-neutral spec governs the general rule and behavior outside those examples. Assurance records evidence and release status; it does not create semantics.

Python is never the behavioral oracle for Rust. Rust is never the behavioral oracle for Python.

A contradiction among the frozen design, normative spec, and applicable canonical conformance is a release-blocking contract defect. Do not silently choose one side.

## 4. Standard layer workflow

Unless the task explicitly narrows the pass further, use this sequence:

1. Fetch both repos, inspect status, record actual starting HEADs, preserve unrelated work.
2. Read the current layer assurance/handoff and exact scope/exclusions.
3. Audit the relevant adopted Pi source first.
4. Build or verify the Pi-to-Minion behavior/ownership mapping.
5. Repair shared contract/evidence before implementing around a bad contract.
6. Implement only the current layer through real existing seams.
7. Add focused language tests and applicable language-neutral canonical evidence.
8. Run the full language gates plus regressions for previously certified layers.
9. Perform the required independent cross-language review/implementation handoff.
10. Certify/freeze only when the layer's gate is satisfied.
11. Stop. Do not automatically start the next layer.

Python may lead Rust by roughly half to one layer as allowed by the normative workflow. `NOT_IMPLEMENTED` in the lagging language is a valid state and is not itself a defect.

## 5. Scope discipline

The current task's layer boundary is binding.

- Do not implement a later layer to make the current layer easier to test.
- It is fine to inspect later-layer code/callsites to understand a boundary; do not certify that later behavior accidentally.
- Do not start providers, built-in tools, harness durability, cancellation, orchestration, or other future work unless the current task explicitly owns it.
- Reuse already-certified lower-layer seams. Do not duplicate Session, Runtime scope/lifecycle, ToolRegistry, message transformation, or other existing authorities in a new layer.
- A higher layer may project or compose lower-layer state without changing the lower layer's observable contract. Do not reopen a certified lower layer merely because it lacks a convenience API.

## 6. Finding taxonomy

Every material issue must use exactly one established classification:

- `PI_BEHAVIOR_UNCERTAIN`: Pi behavior is not sufficiently known. Stop the semantic decision, inspect adopted Pi, then update contract/evidence.
- `PI_PARITY_DEFECT`: Minion differs from known adopted Pi-visible behavior. Fix before certification unless an intentional divergence is explicitly approved.
- `CONTRACT_ASSURANCE_DEFECT`: spec/conformance/manifest/evidence is incomplete, contradictory, or insufficient for independent implementation. Repair before certification; this is not risk debt.
- `PARITY_NEUTRAL_HARDENING`: internal quality improvement that preserves observable semantics. Normally fix in the current phase.
- `PARITY_CONSTRAINED_RISK`: fixing the issue would change Pi-visible behavior. Preserve the Pi-compatible baseline and record the risk unless governance explicitly approves a divergence.

Do not invent softer labels to avoid a blocker.

## 7. Contract-quality rule

Contract stability is not a goal in itself. If implementation evidence shows that the observable contract is incomplete, contradictory, or forces a semantically artificial design, reopen the affected contract and repair spec/conformance/traceability before certification.

But do not change the contract merely because another implementation is cleaner. If the better implementation preserves the observable contract, use it without changing semantics.

Warning signs include:

- a conformance runner simulating missing library semantics;
- the same normative rule reimplemented in multiple layers;
- special cases needed only to preserve underspecification;
- errors swallowed or distorted to fit the contract;
- bypassing an already-certified abstraction;
- two reasonable independent implementations being forced to choose observably different behavior because the boundary is undefined.

## 8. Shared artifacts and dispositions

Shared semantic artifacts are single-source and must not be forked by language:

- `/pi-parity-manifest.yaml`
- `/conformance/**`
- `minion-agent-docs/spec/**`
- frozen design/process documents
- assurance documents as historical evidence

Every relevant manifest row must have an explicit disposition:

- `adopted`
- `deferred parity`
- `intentional divergence`

Silence is not a valid disposition.

A useful manifest row traces:

`Pi path + symbol -> Minion rule -> canonical scenario or explicit language test -> Python evidence -> Rust evidence/planned phase -> disposition`

Preserve review/remediation history. Do not rewrite a historical rejection into an approval; add later remediation/re-review evidence.

## 9. Canonical conformance

There are exactly three canonical behavior families:

- `conformance/runtime`
- `conformance/session`
- `conformance/agent`

`conformance/schema` is support infrastructure, not a fourth behavior family.

Canonical data is language-neutral. Language-specific runners must be thin adapters:

`parse scenario -> construct typed inputs -> invoke real Minion seam -> normalize observations`

A runner MUST NOT implement the semantics it is supposed to test. In particular it must not fabricate queue behavior, ordering, shadowing, message transforms, tool execution semantics, lifecycle, reset behavior, or expected results.

Valid mocking uses a scripted provider/tool through the real Minion seam. Invalid mocking has the runner itself simulate missing runtime/agent behavior.

Do not force a canonical scenario through an unfinished later layer. If behavior is not independently observable at the current layer, document the boundary and use explicit language evidence or a justified deferred scenario until the real seam exists.

Discover scenario counts dynamically. Do not hard-code old counts.

## 10. Cross-language contract hazards

Review these explicitly whenever relevant:

- missing vs `null`/`None` vs `false` vs empty values;
- required vs optional fields;
- exact enum/string serialization and snake_case canonical form;
- integer width/sign behavior;
- deterministic ordering;
- arbitrary JSON/schema round-tripping at dynamic boundaries;
- message-role unions and variant coverage;
- IDs and identity rules;
- timestamps and generated values;
- async/cancellation/callback semantics;
- lifecycle/disposal ownership;
- whether an implementation-specific mechanism has leaked into the shared contract.

Implement the semantic contract, not the other language's mechanics.


## 11. GitHub coordination model

GitHub is the shared coordination surface for all parties. Use three distinct remote objects:

```text
Layer coordination issue = active workflow/control state
Open PR(s)              = current durable candidate / handoff object
Default branches        = latest accepted project milestone
```

Assurance artifacts explain why a milestone is accepted. Chat/local working state must not substitute for these remote objects.

### 11.1 One coordination issue per layer

Create one coordination issue in `minion-agent` for each active layer, for example `Layer 08 — Agent Loop`.

Keep this state block current:

```text
STATUS
    PYTHON_SHARED | RUST_CONTRACT_REVIEW | PYTHON_REMEDIATION |
    RUST_IMPLEMENTATION | CLOSURE_REVIEW | CLOSED

CODE PR
    #N @ <remote head SHA> | none

DOCS PR
    #N @ <remote head SHA> | none

NEXT_OWNER
    Claude | Codex | Owner | none

NEXT_ACTION
    exactly one concrete next process step
```

There must be exactly one `NEXT_OWNER` and one `NEXT_ACTION` while a layer is active. Do not rely on chat history to determine ownership or progress.

### 11.2 PRs are candidate and handoff objects

Every substantive pass must be pushed to a remote branch and represented by a PR before another agent is asked to review or continue it.

Use short-lived branches named by layer and purpose, not permanent agent branches, for example:

```text
layer/08-python-shared
review/08-rust-contract
remediate/08-python-pass2
layer/08-rust-implementation
closure/08
```

When a layer changes both repositories, use paired PRs and cross-link them. Each PR description should identify the layer, companion PR, coordination issue, exact candidate head SHA, pass type, and stop condition.

### 11.3 Exact-SHA review invariant

An independent review approves the exact remote candidate SHA(s) it reviewed.

```text
candidate head changed
    -> previous approval is stale
    -> re-review required
```

A reviewer must fetch and verify the referenced remote SHA before starting. Do not approve prose descriptions of unavailable/local-only state.

### 11.4 Standard ownership flow

```text
Claude
    audit + shared contract + Python candidate
        ↓
Codex
    independent Rust contract review
        ↓
Claude
    shared/Python remediation if rejected
        ↓
Codex
    re-review until approved
        ↓
merge approved shared/Python candidate
        ↓
Codex
    Rust implementation + certification candidate
        ↓
Claude
    final cross-language/closure verification
        ↓
merge closure state
        ↓
Layer CLOSED
        ↓
workflow retrospective
```

Rust implementation starts from the merged approved shared contract, not from an unapproved Python candidate branch.

### 11.5 Default branches are accepted milestones

Use `minion-agent/main` and `minion-agent-docs/master` as accepted milestone branches, not ordinary work branches.

A layer is not globally/cross-language `CLOSED` merely because implementation exists on a feature branch or PR. Closure must be durably represented in default-branch state and assurance evidence.

### 11.6 Merge policy

Follow the repository ruleset. Intended policy: PR required, conversation resolution required, squash merge, linear history, force pushes blocked, and default-branch deletion blocked.

Formal GitHub approval count may remain `0` while Claude/Codex do not have reliably distinct GitHub identities. Procedural independence is still mandatory.

### 11.7 Owner role

The repository owner is governance authority, not the routine merge bottleneck.

Escalate to the owner for intentional Pi divergence, Pi-baseline changes, genuine lower-layer reopen decisions, unresolved Claude/Codex disagreement, master-design/layer-boundary changes, destructive history operations/ruleset bypass, and release-level governance decisions.


## 12. Repository and remote-state discipline

### 12.1 GitHub remote is the durable project state

The GitHub repositories are the **shared durable system of record for implementation progress, review handoffs, and milestone status** because all project participants can inspect them.

This does **not** change semantic authority: Pi/spec/conformance still determine behavior. GitHub determines which project state is durably available to all parties.

Treat local working trees, local branches, and local-only commits as execution state, not durable project state.

A pass that changes code, shared artifacts, or assurance is not ready for cross-party handoff until the relevant commits are reachable from the GitHub remote.

### 12.2 Start every pass from remote reality

At the start of every pass:

- run `git fetch --all --prune` (or the repository-equivalent fetch);
- identify the repository's actual default branch and its remote HEAD;
- record local HEAD and remote/default-branch HEAD separately when they differ;
- inspect `git status`;
- inspect local/remote divergence before editing;
- preserve unrelated modifications and untracked work;
- never reset/overwrite unrelated work merely to match an old instruction SHA.

Do not infer current project progress from chat history, stale handoff text, or local-only commits when the remote repository says otherwise.

### 12.3 Commit and push every completed pass

Before reporting a pass as completed, reviewed, remediated, approved, certified, or ready for another agent:

1. run the required tests/gates;
2. review the final diff;
3. commit all task-owned changes in semantically coherent commit(s);
4. leave unrelated working-tree changes untouched;
5. push the task commit(s) to the GitHub remote;
6. verify that every SHA referenced in the final report is remote-reachable;
7. report the remote branch/ref and exact remote-reachable SHA(s).

Do not hand another agent a SHA that exists only locally.

Do not describe a local-only commit as the project candidate without explicitly marking:

`REMOTE_SYNC_BLOCKED / LOCAL_ONLY`

and explaining why it could not be pushed.

If remote push fails because of credentials, permissions, network, branch protection, or tooling:

- do not claim durable completion;
- preserve the local commits;
- report the exact failure and local SHA(s);
- mark the pass `REMOTE_SYNC_BLOCKED`;
- stop at the handoff boundary unless the current task explicitly authorizes an alternative.

Never force-push or rewrite shared remote history unless explicitly authorized.

### 12.4 Branches, PRs, and milestone visibility

Follow the repository's current branch/PR policy.

If work is done on a feature/review branch, pushing the branch is sufficient to make a **candidate/review state** durable, but the final report must state:

- remote branch name;
- remote commit SHA;
- PR number/link if one exists;
- whether the change is merged into the default branch.

For project milestone checks, prefer the remote default branches plus current assurance artifacts.

A layer must not be described as globally/cross-language `CLOSED` merely because an implementation exists on an unmerged branch. Closure should be reflected in the shared remote state intended as the project's durable milestone record.

### 12.5 Commit discipline

Prefer small, reviewable, semantically coherent commits. Keep review-only evidence separate from implementation/remediation when practical.

Shared semantic changes should be coordinated explicitly. Evidence-only updates must not silently change semantic rules.

Historical rejection/remediation/re-review evidence must remain reachable from remote history.

## 13. Certification gate

Do not certify a layer merely because tests pass.

Certification requires, as applicable:

- Pi audit complete;
- manifest/spec/conformance complete and mutually consistent;
- implemented-language tests green;
- applicable canonical scenarios green through real seams;
- assurance evidence recorded;
- every finding classified;
- no active `PI_BEHAVIOR_UNCERTAIN`;
- no active `PI_PARITY_DEFECT`;
- no active `CONTRACT_ASSURANCE_DEFECT`;
- no unapproved observable divergence;
- deferred parity/risk explicitly owned and tracked;
- all task-owned certification/assurance commits pushed and verified remote-reachable;
- milestone status represented on the appropriate remote branch/default branch according to repository policy.

Approval of a shared contract is not implementation certification. A language layer is not cross-language closed until the required implementations and assurance are complete and the closure state is durably available on GitHub.

## 14. Workflow improvement and periodic retrospective

The workflow itself is versioned project infrastructure and should be reviewed regularly rather than treated as permanently correct.

### 14.1 When to review the workflow

Perform a lightweight workflow retrospective at least:

- after each cross-language layer closes;
- after any repeated rejection/remediation cycle;
- after any handoff failure, stale-state incident, remote-sync problem, duplicated work, or unclear ownership boundary;
- when a coding agent repeatedly needs instructions that are not already captured here;
- when a new language, tool, provider, CI system, or collaboration pattern materially changes how work is performed.

A deeper process review SHOULD happen every few layers even when no obvious failure occurred.

### 14.2 What to look for

Ask:

- Which instructions were repeated manually and should become persistent project guidance?
- Which rule was ambiguous enough that two agents interpreted it differently?
- Did any agent rely on local/chat state instead of remote durable state?
- Did review discover a contract defect only after implementation that could have been caught earlier?
- Did a conformance runner or test accidentally duplicate production semantics?
- Did an ownership boundary cause unnecessary blocking or duplicate work?
- Are any checks ceremonial, stale, redundant, or missing?
- Are any status labels, handoff states, or stop conditions ambiguous?
- Did the workflow encourage overlong prompts that can now be shortened?
- Can the same assurance strength be achieved with a simpler, more automated, or more deterministic process?

### 14.3 Improvement rule

When a reusable process improvement is found:

1. distinguish a **workflow/process improvement** from a **semantic-contract change**;
2. update the appropriate persistent project guidance (`AGENT_WORKFLOW.md`, `CLAUDE.md`, `AGENTS.md`, or normative process docs);
3. keep semantic rules in spec/conformance rather than coding-agent instruction files;
4. add or update automation/CI where a repeated manual check can be made deterministic;
5. commit and push the workflow change so all agents receive the same rule;
6. record significant process changes in an assurance/process-history artifact when they materially affect certification or handoff behavior.

Do not wait for the next failure once a generalizable improvement is known.

### 14.4 Do not let process review destabilize active semantics

Workflow improvement must not silently reopen certified semantics.

If a retrospective reveals a semantic defect, classify it using the normal finding taxonomy and use the established contract-reopen path.

If it reveals only a better way to coordinate, test, review, report, or persist state, update the workflow without changing the semantic contract.

### 14.5 Preferred outcome

The persistent workflow should absorb recurring boilerplate so layer-specific instructions get progressively shorter and more focused.

A healthy trend is:

`long repeated prompt -> recurring rule identified -> persistent workflow updated -> future prompt only states layer-specific deltas`

The coding-agent project files are therefore expected to evolve as the project learns.

## 15. Standard final report

Unless the task specifies another format, finish with a concise report containing:

1. `STARTING STATE` — actual code/docs HEADs and Pi baseline.
2. `PI AUDIT` — symbols audited and any uncertainty.
3. `FINDINGS` — grouped by the established taxonomy.
4. `CHANGES` — shared and language-specific files changed.
5. `CANONICAL / TEST GATES` — exact fresh results, dynamically discovered.
6. `CROSS-LAYER IMPACT` — whether certified lower layers need a delta.
7. `ASSURANCE / VERDICT` — precise layer status; do not overclaim.
8. `REMOTE STATE` — coordination issue, remote branch/ref, remote-reachable code/docs SHAs, paired PRs, and merge state.
9. `NEW CANDIDATE` — resulting remote-reachable commit SHAs/artifacts.
10. `NEXT ACTION` — exactly one next process step.

Respect the stop condition in the current task. Never continue automatically into the next review, implementation, or layer.
