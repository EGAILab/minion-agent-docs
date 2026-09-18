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
3. `minion-agent-docs/process/coordination-state.md` — the machine-checkable coordination-state schema referenced throughout §11
4. the current work package's `spec/**` and `assurance/layers/**` artifacts
5. `/pi-parity-manifest.yaml`
6. the applicable canonical scenarios under `/conformance/**`
7. the adopted Pi source for the symbols being implemented or reviewed

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

### 4.1 Contract-first checkpoint for high-risk semantics

For a layer or semantic slice with substantial concurrency, async scheduling, callback/listener ordering, cancellation, failure recovery, lifecycle interleaving, provider/tool interaction, or another behavior where small ordering differences are observable, front-load independent contract work before a large implementation pass.

Preferred flow:

```text
Claude Pi audit + draft behavior matrix/spec/conformance
                    ↓
Codex independent Pi audit of the same semantic slice
                    ↓
resolve contract/evidence findings
                    ↓
CONTRACT CHECKPOINT
                    ↓
Python implementation
                    ↓
independent implementation-readiness review
```

The checkpoint is not cross-language certification and does not authorize Rust implementation. It exists to move semantic discovery earlier so the implementation review is not used as the primary contract-discovery mechanism.

A contract checkpoint SHOULD be used when any of the following is true:

- the surface depends on scheduler or callback timing;
- the surface has several interacting dimensions whose cross-product matters;
- prior layers have shown repeated late semantic discoveries in similar code;
- the same rule would be expensive to repeatedly rewrite after implementation;
- a reviewer cannot state a finite discriminating behavior matrix before implementation.

### 4.2 Work-package slicing

A large assurance layer MAY be divided into smaller **work packages** without changing the architectural layer boundary.

A work package is the smallest unit that has all of the following:

- a bounded semantic surface;
- an explicit set of parity-manifest requirement IDs;
- a coherent contract/evidence set;
- a single coordination state;
- a clear certification or deferred-parity outcome.

Example:

```text
Layer 11 — Real Providers
    WP-11.1 Auth Foundation
    WP-11.2 Codex Account Projection
    WP-11.3 Provider/Auth Interaction Vocabulary
    WP-11.4 Codex OAuth Network Integration
    WP-11.D1 Generic Auth Orchestration — DEFERRED
```

A work package SHOULD be organized around observable semantic ownership, not implementation modules.

A work package is not independently certified as the whole layer. Slicing a layer into work packages is a work-management technique that lets the shared contract and evidence for one tightly-coupled behavior settle before unrelated behavior is added; a layer is complete for the current baseline only when every in-scope requirement is `CERTIFIED`/`ADOPTED`, `DEFERRED PARITY` with an explicit closure trigger, or `INTENTIONAL DIVERGENCE` with valid governance provenance (see §11.1 and §11.13).

Do not use "Pass" as a semantic or certification level. Review rounds are events within a work package, not additional project hierarchy.

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
- two reasonable independent implementations being forced to choose observably different behavior because the boundary is undefined;
- new normative prose that is true in isolation but contradicts an already-certified section elsewhere in the SAME document (fixing one finding's own narrow claim without re-checking whether a general-sounding phrase like "fixed," "never changes," or "set once" holds once other certified sections covering the same field/value are accounted for).

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

Machine validation of traceability artifacts must validate each field's container shape before
validating or iterating its contents. An iterable scalar or mapping must not accidentally satisfy
a required list field. Keep negative probes for plausible malformed container shapes alongside the
validator.

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

When canonical observations convert an unordered or implementation-defined collection into an
ordered list, the shared contract must specify the canonicalization key, including field
precedence. Keep that evidence-only ordering distinct from any production API return-order rule.
The canonical evidence should contain at least two entries chosen to distinguish plausible but
different sort keys; single-entry observations cannot certify ordering agreement.

### 9.1 Discriminating evidence

Evidence must distinguish the claimed semantic rule from plausible incorrect implementations.

A test that proves only a weaker neighboring condition does not close a review finding.

Examples:

```text
required rule:
    prompt lifecycle completes before steering is claimed

insufficient evidence:
    turn_start happens before steering is claimed
```

For callback, listener, scheduler, failure, and concurrency semantics, tests SHOULD cover the smallest cross-product necessary to distinguish the rule. Typical dimensions include:

```text
listener count       0 | 1 | 2+
listener behavior    synchronous | suspending/async
listener result      success | throw/reject
execution mode       sequential | parallel
event stage          start | update | end
state timing         before listener | during listener | after listener
completion timing    callback return | work continuation | event join
```

Do not test every theoretical combination mechanically. Select the combinations that distinguish the adopted rule from realistic incorrect implementations.

For an authority-protection fix on a multi-field payload (a listener must not redirect or drop one or more protected fields for a later listener), enumerate EACH protected field's own redirect and omission separately, not one shared witness assumed to cover all of them. Two protected fields on opposite sides of the transformable region are a distinct failure mode from either one alone: a delegation shorter than the full payload can be genuinely ambiguous about WHICH field was omitted, and a fix that resolves the redirect case correctly can still leave one field's own omission case silently wrong (Layer 09: `L09-R006` closed signal-redirect; `L09-R015` later found the same event's own instance-omission case still open; `L09-R018` then found that closing BOTH single-field omissions independently was still incomplete once the payload had two protected fields, because a shortened delegation could not say which one was missing).

A witness asserting "a listener omits field X when delegating" must construct a delegation that is genuinely shorter than the full payload with X specifically absent -- not a bare, argument-less continuation call. A dispatch primitive's own no-argument continuation is typically defined as "forward the current values unchanged," a different code path from "forward a replacement that is missing one specific field," and a witness using the former cannot discriminate a real omission-handling defect no matter how its own name and docstring describe it (Layer 09, `L09-R015`: two "drop" tests both called the argument-less continuation form and passed against a candidate that could not actually handle true omission, because that form never reaches the omission-handling code path at all).

### 9.2 Reviewer witness rule

Every blocking `PI_PARITY_DEFECT`, `CONTRACT_ASSURANCE_DEFECT`, or `PI_BEHAVIOR_UNCERTAIN` discovered in independent review MUST include a minimal discriminating witness when the behavior is executable or observable.

The witness must state:

```text
finding ID
Pi/source basis
minimal setup
expected observable trace/state
candidate observed trace/state
why the difference is discriminating
```

When practical, the reviewer SHOULD provide an executable probe using the pinned Pi source and/or the real Minion seam.

The remediation owner MUST turn the exact discriminating observation into permanent regression evidence before handing the finding back for closure.

A prose-only finding is acceptable only when the defect is inherently documentary/traceability-only and no executable distinction exists.

If the review states that existing code already satisfies a new witness (a prose-only/contract-assurance finding, not a behavior defect), the remediation owner MUST run that exact witness against the UNCHANGED candidate and confirm it directly before relying on the claim -- report the confirmation, not merely the review's own assertion. A "no code change" remediation still needs the full discriminating-evidence treatment: the new regression test is what closes the contract ambiguity, even when no production line changes.

### 9.3 Pinned-Pi characterization probes

For subtle observable behavior that depends on language runtime mechanics, it is acceptable and encouraged to maintain development-only Pi characterization probes against the pinned Pi revision.

A suggested location is:

```text
reference/pi-characterization/<surface>/
```

or another clearly non-normative reference/test-support location.

A characterization probe may normalize observable traces such as:

```text
listener_1_enter
tool_continues
listener_2_enter
listeners_joined
tool_end
```

Rules:

- the pinned Pi source remains the semantic source;
- the normative spec and canonical conformance remain the project contract;
- characterization output is derivation/debugging evidence, not a new semantic authority;
- do not make production Minion depend on the Pi harness;
- pin the Pi revision used by the probe;
- prefer deterministic, minimal examples;
- when a probe reveals a semantic rule, express that rule in the normal manifest/spec/conformance/evidence chain.

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
- whether an implementation-specific mechanism has leaked into the shared contract;
- floating-point special values (`NaN`/`+Infinity`/`-Infinity`) and language-specific numeric coercion (e.g. JS `Math.max`/`Math.min` propagating `NaN` vs Python's non-propagating, order-dependent `max()`/`min()`; JS `Math.floor`/arithmetic never throwing on non-finite input vs Python's `math.floor` raising);
- whether a test double's own timing/clock simulation can manufacture floating-point drift a real clock would never produce, and whether a fix for that drift has been confined to the test double rather than leaked into production arithmetic reachable by genuine public input.

Implement the semantic contract, not the other language's mechanics.

For async/callback semantics, describe observable scheduling boundaries language-neutrally. Do not encode JavaScript, Python, or Rust implementation primitives into the contract unless the primitive itself is part of the observable API.

**Floating-point tolerance must never be added to production arithmetic to compensate for a test double's own drift, no matter how narrowly the call site is scoped.** A derived value (e.g. `deadline - now()`) can be, on one code path, a drift-affected internal quantity, and on another reachable code path (e.g. a first computation before any prior sleep), an EXACT, unmodified copy of a genuine caller-supplied input -- the same expression, evaluated at different points in a loop's own lifetime, does not reliably belong to one category or the other. Narrowing WHERE a tolerance is applied (a more specific call site, a differently-named helper) cannot fix this if the underlying value itself is ambiguous; only removing the tolerance from production arithmetic entirely, and instead correcting the test double that manufactures the drift (e.g. rounding a fake clock's own accumulated `elapsed` after each increment, since a real monotonic clock is read directly and never accumulates by summing many small durations), resolves it without risking a silent, unapproved divergence on a genuine public input. Before adding ANY epsilon/tolerance fix, explicitly enumerate every reachable code path that produces the value being tolerated, not just the one the current failing test exercises -- "no currently-tested input is affected" is not the same claim as "no possible public input is affected," and only the second one licenses adding tolerance to shared or production code (Layer 11 Pass 1, `PROV-010`: `L11-R019` added a global epsilon to a shared truncation helper serving every delay in the module, including genuine caller-supplied ones -- rejected by `L11-R020` for silently rounding a genuine near-boundary public delay the wrong direction; `L11-R020`'s own narrower fix moved the SAME epsilon to a helper applied only to `poll_device_code_flow`'s own deadline remainder, reasoning that value was always "internally derived" -- rejected again by `L11-R021`, because on a first-computation code path with no prior sleep, that exact same remainder is arithmetic-identical to the caller's own supplied expiry value, with zero drift; only removing the tolerance from production code entirely and fixing the two fake-clock test doubles' own `elapsed` accumulation resolved the underlying test-infrastructure problem without ever touching a value a genuine caller could supply).

## 11. GitHub coordination model

GitHub is the shared coordination surface for all parties. Use three distinct remote objects:

```text
Layer coordination issue = active workflow/control state
Open PR(s)              = current durable candidate / handoff object
Default branches        = latest accepted project milestone
```

Assurance artifacts explain why a milestone is accepted. Chat/local working state must not substitute for these remote objects.

### 11.1 Coordination issue per active work package

Create one coordination issue in `minion-agent` for each **active work package** (§4.2), not necessarily one issue for the entire architectural layer.

A layer MAY also have one umbrella/index issue whose only purpose is to summarize work-package disposition.

Examples:

```text
Layer 11 — Real Providers                    # umbrella/index
WP-11.1 — Auth Foundation                    # operational issue
WP-11.2 — Codex Account Projection           # operational issue
WP-11.4 — Codex OAuth Network Integration    # operational issue
WP-11.D1 — Generic Auth Orchestration        # deferred tracking
```

The operational issue contains one machine-readable current-state block, using the **exact canonical schema** defined in `process/coordination-state.md` -- there is only one normative current-state shape; do not use a flattened or otherwise divergent variant:

```yaml
workflow:
  schema_version: 1
  layer: "11"
  work_package: "WP-11.4"
  title: "Codex OAuth Network Integration"
  status: CONTRACT_CONVERGENCE

  requirements:
    - PROV-012
    - PROV-016

  code:
    pr: 33
    sha: "<remote SHA>"
    base: "main"

  docs:
    pr: 92
    sha: "<remote SHA>"
    base: "master"

  pinned_pi: "<pinned Pi SHA>"

  convergence:
    episode: "CE-L11-04-02"
    open_findings:
      - L11-SC-R025
      - L11-SC-R027

  next_owner: Claude
  next_action: >
    Implement the agreed convergence surface and return the exact
    candidate for targeted closure review.

  governance_source: null
  deferred_trigger: null

  quarantine:
    derived_from_quarantined_artifact: false
```

This block is the **current control state**.

Comments and assurance records are historical event/evidence records. They MUST NOT be treated as the primary source of current ownership/status when the state block exists.

The coding agents SHOULD hand off directly through this GitHub control plane. The repository owner or an external coordinator does not need to translate routine review feedback between agents.

A receiving agent is expected to fetch the coordination issue, candidate PRs, review comments, and review assurance artifact directly.

#### 11.1.1 Current-state update rule

Whenever any of the following changes:

- `status`;
- current code/docs candidate SHA;
- open finding set;
- `next_owner`;
- `next_action`;
- governance dependency;
- deferred closure trigger;

the coordination issue's current-state block MUST be updated.

Do not leave a stale issue body and rely on a later comment to override it.

#### 11.1.2 Exactly one active owner

For active states, there must be exactly one `next_owner` and one concrete `next_action`. Do not rely on chat history to determine ownership or progress.

For the passive deferred state `WAITING_FOR_TRIGGER`, `next_owner` and `next_action` MAY be `none`; `deferred_trigger` MUST be present and binding (§11.13).

#### 11.1.3 Work-package states

Allowed `status` values:

```text
SCOPING
CONTRACT_DRAFT
CONTRACT_REVIEW
PYTHON_IMPLEMENTATION
IMPLEMENTATION_REVIEW
REMEDIATION
CONTRACT_CONVERGENCE
FINAL_CONTRACT_REVIEW
RUST_IMPLEMENTATION
CLOSURE_REVIEW
WAITING_FOR_TRIGGER
CLOSED
INCIDENT
INVALID_UNAUTHORIZED
BLOCKED_FOR_OWNER
```

State intent:

`SCOPING`
: Read-only audit and boundary definition. No implementation authorization is implied.

`CONTRACT_DRAFT`
: Shared contract/evidence is being authored before implementation.

`CONTRACT_REVIEW`
: Independent review of the proposed semantic contract.

`PYTHON_IMPLEMENTATION`
: The shared/Python owner is implementing an approved/checkpointed contract.

`IMPLEMENTATION_REVIEW`
: Independent review of implementation plus permanent evidence.

`REMEDIATION`
: Narrow correction of review findings before convergence has triggered.

`CONTRACT_CONVERGENCE`
: Repeated/coupled semantic defects are being characterized and closed through the convergence protocol (§11.8).

`FINAL_CONTRACT_REVIEW`
: The candidate changed since the first `IMPLEMENTATION_REVIEW` (an ordinary remediation re-review, or a convergence episode whose findings are all provisionally closed); one complete exact-SHA review of that changed candidate is pending. Not used for a clean first review with no blocking findings (§11.4).

`RUST_IMPLEMENTATION`
: Rust implementation against the merged approved shared contract.

`CLOSURE_REVIEW`
: Cross-language closure verification.

`WAITING_FOR_TRIGGER`
: Deferred parity is valid and no implementation is authorized until a named event occurs (§11.13).

`CLOSED`
: The work package is durably complete for its disposition.

`INCIDENT`
: Coordination object is retained for process/forensic history and is not actionable implementation state.

`INVALID_UNAUTHORIZED`
: Artifact was created or mutated outside valid authorization and is governed by quarantine semantics (§11.12).

`BLOCKED_FOR_OWNER`
: A governance decision is required before work may proceed (§11.7, §11.10).

### 11.2 PRs are candidate and handoff objects

Every substantive pass must be pushed to a remote branch and represented by a PR before another agent is asked to review or continue it.

Use short-lived branches named by layer and purpose, not permanent agent branches, for example:

```text
layer/08-python-shared
review/08-rust-contract
remediate/08-python-pass2
converge/08-agent-events
layer/08-rust-implementation
closure/08
```

When a layer changes both repositories, use paired PRs and cross-link them. Each PR description should identify the layer, companion PR, coordination issue, exact candidate head SHA, pass type, and stop condition.

Work-in-progress implementation/remediation PRs SHOULD remain Draft. Mark them Ready for Review when ownership transfers to an independent reviewer.

#### 11.2.1 Review evidence packaging

A separate docs PR is **not required for every review event**.

A work package SHOULD prefer:

```text
one candidate PR pair
+
one durable review ledger / assurance record
+
coordination issue event comments
```

over creating a new branch/PR solely to store each individual review round.

Create a separate assurance PR when at least one of the following is true:

- normative/process/assurance source files are intentionally changed;
- the review artifact itself must become part of the accepted default-branch milestone;
- a convergence agreement/checkpoint needs durable repository content before implementation;
- repository policy requires the evidence to be merged as a file.

Otherwise, a SHA-bound review record attached to the coordination issue/PR is sufficient intermediate evidence, provided it contains:

```text
reviewer role
candidate code/docs SHA
pinned Pi revision
scope
findings
discriminating witness links/details
verdict
next transition
```

At certification, material intermediate evidence SHOULD be summarized into the final assurance record rather than requiring every review event to remain a standalone merged document.

Do not reduce evidence quality; reduce redundant repository objects.

### 11.3 Exact-SHA review invariant

An independent **final approval** approves the exact remote candidate SHA(s) it reviewed.

```text
candidate head changed
    -> previous final approval is stale
    -> final re-review required
```

A reviewer must fetch and verify the referenced remote SHA before starting. Do not approve prose descriptions of unavailable/local-only state.

Intermediate targeted finding closure is allowed under the convergence protocol in §11.8. It is not final layer approval and does not waive the exact-SHA invariant for the final complete review.

### 11.4 Standard work-package ownership flow

```text
SCOPING
   ↓
CONTRACT_DRAFT
   ↓
independent CONTRACT_REVIEW
   ↓
checkpoint / approval for implementation
   ↓
PYTHON_IMPLEMENTATION
   ↓
IMPLEMENTATION_REVIEW
   ↓
┌────────────────────────────────────┐
│ no blocking findings                │
│     ↓                               │
│ approved clean exact-SHA candidate  │
│     ↓                               │
│ merge approved shared/Python        │
└────────────────────────────────────┘
              │
              └── blocking findings
                         ↓
                    REMEDIATION
                         ↓
                 trigger §11.8 (A/B/C)?
                   /          \
                 no            yes
                 ↓              ↓
       IMPLEMENTATION_REVIEW   CONTRACT_CONVERGENCE
          (re-review)                ↓
                 │           characterize + challenge
                 │                    ↓
                 │                checkpoint
                 │                    ↓
                 │            coherent fix pass
                 │                    ↓
                 │       negative-control witness gate
                 │                    ↓
                 │              TARGETED REVIEW
                 │                    ↓
                 │        all blockers provisionally
                 │                  closed
                 ↓                    ↓
                 └──── targeted closure reached ────┘
                                 ↓
                       FINAL_CONTRACT_REVIEW
                                 ↓
                       ONE complete exact-SHA
                           independent review
                                 ↓
                               merge
                                 ↓
                       RUST_IMPLEMENTATION
                                 ↓
                         CLOSURE_REVIEW
                                 ↓
                               CLOSED
                                 ↓
                       workflow retrospective
```

If an ordinary `IMPLEMENTATION_REVIEW` re-review still finds blocking issues, return to `REMEDIATION` and re-check triggers A, B, and C again against the finding's now-larger review history before starting another remediation pass; do not merge from a re-review that still has blocking findings, and do not treat a still-open re-review as itself a `FINAL_CONTRACT_REVIEW`.

After ordinary `REMEDIATION`, the following `IMPLEMENTATION_REVIEW` is normally a **targeted finding-closure review**, scoped to:

- the blocking findings being remediated;
- semantic dependencies touched by the fix;
- previously-closed high-risk regressions affected by the change.

It SHOULD NOT repeat a complete work-package review unless the reviewer records a concrete semantic blast-radius reason requiring one. Once the remediation findings are closed, `FINAL_CONTRACT_REVIEW` performs the one complete independent exact-SHA review of the changed candidate. The intended pattern is therefore:

```text
initial complete review
    -> findings
    -> remediation
    -> targeted closure
    -> one final complete review
```

Convergence's own stricter mandatory targeted-closure rules (§11.8.7) are unchanged by this -- this section only extends the same targeted-scope discipline to ORDINARY, non-convergence remediation. Neither path weakens independent review or the exact-SHA approval requirement (§11.3).

Rust implementation starts from the merged approved shared contract, never from an unapproved Python candidate branch.

A work package MUST NOT transition directly from `CONTRACT_CONVERGENCE` to a complete final review while a known convergence finding remains open.

`FINAL_CONTRACT_REVIEW` is the final complete review of a candidate that CHANGED after the first `IMPLEMENTATION_REVIEW` -- either through ordinary remediation requiring re-review, or through a convergence episode whose findings have all been provisionally closed. It is not a second complete review of an unchanged clean candidate: a truly clean first `IMPLEMENTATION_REVIEW` (no blocking findings at all) merges directly, without a second full review of the same content.

### 11.5 Default branches are accepted milestones

Use `minion-agent/main` and `minion-agent-docs/master` as accepted milestone branches, not ordinary work branches.

A layer is not globally/cross-language `CLOSED` merely because implementation exists on a feature branch or PR. Closure must be durably represented in default-branch state and assurance evidence.

### 11.6 Merge policy

Follow the repository ruleset. Intended policy: PR required, conversation resolution required, squash merge, linear history, force pushes blocked, and default-branch deletion blocked.

Formal GitHub approval count may remain `0` while Claude/Codex do not have reliably distinct GitHub identities. Procedural independence is still mandatory.

### 11.7 Owner role

The repository owner is governance authority, not the routine merge bottleneck.

Escalate to the owner for intentional Pi divergence, Pi-baseline changes, genuine lower-layer reopen decisions, unresolved Claude/Codex disagreement, master-design/layer-boundary changes, destructive history operations/ruleset bypass, and release-level governance decisions.

Routine review/remediation handoff SHOULD proceed agent-to-agent through GitHub without requiring owner relay.

### 11.8 Contract convergence protocol

The normal remediation/re-review loop is intentionally strict, but it MUST NOT become an unbounded semantic-discovery loop.

Enter `CONTRACT_CONVERGENCE` automatically when **any** of the following occurs:

```text
A. the same material finding survives two independent reviews;

B. the same semantic root-cause surface produces two successor findings
   after remediation, even when the finding IDs differ;

C. the work package accumulates three rejected complete contract reviews;

D. the reviewer and implementation owner agree that the remaining blockers
   form one tightly-coupled semantic surface that is more efficiently
   characterized together.
```

These triggers are evaluated separately:

- trigger A is finding-specific;
- trigger B is root-cause/surface-specific;
- trigger C is work-package-wide;
- trigger D is an early opt-in.

Do not reinterpret a work-package-wide trigger as finding-specific or vice versa.

Entering convergence is a workflow/process decision. It does not weaken Pi fidelity, reopen certified semantics by itself, or change the finding taxonomy.

**Trigger check is mandatory, not advisory.** Before starting a new ordinary remediation pass, the remediation owner MUST explicitly check triggers A, B, and C against the finding's own review history, its root-cause surface, and the work package's own rejected-review count (not general impressions) and state the result, for example:

```text
L12-R003 has survived one independent review, so trigger A has not fired.
No successor finding has yet appeared on the same root-cause surface, so B
has not fired.
The work package has one rejected complete review, so C has not fired.
Proceeding with ordinary remediation.
```

Trigger A fires as soon as the SAME material finding has survived two independent reviews -- being at two is already fired, not "approaching" a threshold:

```text
If the same material finding has survived two independent reviews,
trigger A HAS fired.
```

If a trigger condition is already met, entering convergence is the default; proceeding with another ordinary point-fix pass instead requires stating why (e.g. the reviewer's own evidence already narrowed the remaining surface to something a single targeted fix can close, as opposed to genuine unresolved semantic breadth). A Layer-08 remediation cycle went through three full rejection/re-review rounds on the same finding ID before this check was applied retroactively, and a separate finding on the same layer reached the two-repeat threshold without the check being applied at all -- in both cases the trigger was real and simply was not checked, not judged and declined. Do not rely on writing a retrospective note after the fact to substitute for checking the trigger before the fact. Do not weaken these thresholds to make an ordinary point-fix pass easier to justify.

#### 11.8.1 Convergence objective and episode tracking

The objective is to stop discovering one semantic edge per implementation pass.

During convergence:

- freeze unrelated implementation work;
- define the remaining semantic surface completely enough to implement once;
- convert every open finding into discriminating acceptance evidence;
- agree the contract/evidence before another large implementation pass;
- use targeted finding closure until all blockers are provisionally closed;
- then perform one final complete exact-SHA contract review.

Each convergence episode receives a stable ID, for example:

```text
CE-L11-04-01
```

The episode record accumulates, across the episode's full lifetime (including any successor findings folded in under trigger B):

```text
OPEN FINDINGS
ROOT-CAUSE SURFACE
PI SYMBOLS / TESTS AUDITED
OBSERVABLE RULES
BEHAVIOR MATRIX
MINIMAL EXECUTABLE WITNESSES
NEGATIVE CONTROLS
CURRENT CANDIDATE FAILURES
SPEC / MANIFEST / CONFORMANCE DELTAS
IMPLEMENTATION CONSTRAINTS
OUT-OF-SCOPE / DEFERRED BEHAVIOR
```

New findings discovered inside the same root-cause surface are added to the existing episode instead of automatically starting another complete-review loop. §11.8.3 describes how the first characterization pass populates this record; this episode record is the accumulating artifact, not a one-time snapshot.

#### 11.8.2 Coordination state

Update the active **work-package coordination issue** (§11.1) using the machine-readable state defined by `process/coordination-state.md`, not a separate free-form format:

```yaml
workflow:
  status: CONTRACT_CONVERGENCE

  convergence:
    episode: CE-L12-01-01
    root_cause_surface: "<semantic surface>"
    open_findings:
      - L12-R001

  next_owner: Claude
  next_action: >
    Perform the agreed convergence implementation and return the
    exact candidate for targeted closure review.
```

The existing `code`/`docs` PR and SHA fields remain current.

Do not introduce a second competing coordination format for convergence; the `convergence.episode`/`convergence.open_findings` fields of the same current-state block carry this information.

Exactly one owner acts at a time. Convergence is collaboration through durable artifacts, not simultaneous editing of the same shared files.

#### 11.8.3 Characterization pass

Normally the independent reviewer who discovered the repeated defect performs the first characterization pass.

Produce a compact convergence artifact containing:

```text
OPEN FINDINGS
PI SYMBOLS / TESTS AUDITED
OBSERVABLE RULES
BEHAVIOR MATRIX
MINIMAL EXECUTABLE WITNESSES
CURRENT CANDIDATE FAILURES
SPEC / MANIFEST / CONFORMANCE DELTAS NEEDED
IMPLEMENTATION CONSTRAINTS
OUT-OF-SCOPE / DEFERRED BEHAVIOR
```

For concurrency/async/callback surfaces, explicitly enumerate the discriminating dimensions rather than relying on one happy-path example.

Where practical, add pinned-Pi characterization probes as described in §9.3.

This pass is contract/evidence characterization, not Rust implementation.

#### 11.8.4 Challenge pass

The implementation/shared-contract owner independently reviews the characterization before coding.

The challenge should ask:

- Is the Pi source mapping correct?
- Is the behavior matrix complete enough to distinguish realistic wrong implementations?
- Are any cases implementation mechanics rather than observable semantics?
- Does any proposed fix silently reopen a lower certified layer?
- Can both Python and Rust implement the rule idiomatically?
- Does the defect's own ROOT CAUSE depend on an extensibility point (a synchronous listener hook, a reentrant callback, a mutable shared handle) that one language's own already-certified lower layers expose and the other does not? If so, say which side actually needs the fix and which side may need nothing at all -- a "yes, idiomatically implementable" answer can still hide that the mechanism itself is a one-language-only cost the other language's own architecture never introduced (Layer 09: five Python passes and a convergence cycle defended against a reentrant `on_status_change` observer that had no Rust counterpart, because Rust's own Layer-08 architecture never exposed a synchronous status-observer hook at all -- this was only discovered at Rust-closure time, not during characterization).
- Are all previous review findings represented by an executable or documentary acceptance criterion?

Disagreements should be resolved against pinned Pi and the existing semantic-authority chain. Escalate to the owner only for the normal governance cases in §11.7.

#### 11.8.5 Convergence contract checkpoint

Before implementation resumes, record an explicit checkpoint:

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION

OPEN FINDINGS
    <IDs>

ACCEPTANCE WITNESSES
    <paths / probe IDs / tests>

NORMATIVE DELTAS
    <spec/manifest/conformance paths>

NEXT_OWNER
    <implementation owner>
```

This is not final contract approval. It means both agents agree that the remaining observable surface is sufficiently characterized for another implementation attempt.

#### 11.8.6 Implementation pass

The implementation owner then remediates the agreed surface in one coherent pass.

Requirements:

- implement against the agreed behavior matrix, not only the latest prose comment;
- convert reviewer witnesses into permanent regression evidence;
- keep shared spec/manifest/conformance synchronized with the implementation;
- rerun directly affected previously-closed findings;
- avoid unrelated cleanup unless necessary for correctness;
- push the candidate and update exact remote SHAs.

#### 11.8.7 Targeted convergence closure is mandatory

After a convergence implementation pass, the independent reviewer MUST perform a targeted finding-closure review.

The review scope is:

```text
open convergence finding(s)
+
semantic dependencies touched by the fix
+
previously-closed high-risk regressions affected by the change
```

A complete release-level work-package review MUST NOT be substituted for this targeted closure step merely because the candidate SHA changed.

A complete review is permitted before all convergence findings are provisionally closed only when the reviewer records a concrete reason that the remediation changed semantic surface outside the convergence checkpoint.

A successful targeted review records:

```text
Lxx-Ryyy
    PROVISIONALLY CLOSED @ <candidate SHA>
```

`PROVISIONALLY CLOSED` means the specific finding has discriminating evidence at that candidate, per §11.8.7.1. It is not final layer approval.

If a finding remains open, the reviewer MUST provide a new/refined discriminating witness. Do not simply restate the prior finding.

##### 11.8.7.1 Negative-control gate for discriminating witnesses

Before a blocking executable finding can be marked `PROVISIONALLY CLOSED`, its permanent witness must demonstrate both:

```text
known-bad behavior -> FAIL
candidate behavior -> PASS
```

The negative control MAY be established by:

- reverting the specific fix in a temporary worktree;
- executing the witness against a known-bad prior SHA;
- substituting a deliberately incorrect implementation at the relevant seam;
- another deterministic mutation that reproduces the reported defect.

The evidence record MUST state:

```text
finding ID
negative-control method
known-bad mutation/SHA
expected failure
observed failure
candidate SHA
observed pass
```

A test that passes only on the candidate but has not been shown to fail against a realistic incorrect implementation is supporting evidence, not a discriminating closure witness.

For documentary-only findings where no executable distinction exists, record:

```text
NEGATIVE_CONTROL
    NOT_APPLICABLE — documentary/traceability-only
```

with the reason.

#### 11.8.8 One final complete review per settled convergence episode

Once every blocking finding in the active convergence episode is provisionally closed:

1. freeze the candidate to one exact remote code/docs SHA pair;
2. run all complete gates;
3. transition to `FINAL_CONTRACT_REVIEW`;
4. perform **one** complete independent contract review of that exact candidate;
5. if approved, apply the normal exact-SHA merge gate.

If the final complete review discovers a new blocker:

**Case A — narrow, independent blocker.** If the blocker is demonstrably outside the settled convergence root-cause surface and can be closed without changing the wider contract, use only existing states:

```text
FINAL_CONTRACT_REVIEW
    -> REMEDIATION
    -> IMPLEMENTATION_REVIEW      # targeted closure scope only
    -> FINAL_CONTRACT_REVIEW
```

Do not automatically re-run the entire convergence characterization.

**Case B — coupled/new semantic surface.** If the blocker exposes another coupled semantic surface or invalidates the prior convergence matrix, open a new convergence episode with a new episode ID.

The existence of a changed candidate SHA alone is **not** sufficient reason to perform a complete review before targeted closure is finished.

#### 11.8.9 No weakening of independence

Convergence does not mean one agent dictates semantics to the other.

- Pi remains the source.
- Shared spec/conformance remain language-neutral.
- Python does not become Rust's oracle.
- Rust review does not prescribe Python mechanics.
- Final approval remains independent and exact-SHA-bound.
- Rust implementation still begins only after the shared/Python contract is approved and merged.

The improvement is that semantic characterization happens before repeated implementation attempts, not that review strictness is reduced.

### 11.9 Subagent and background-agent capability boundary

`READ_ONLY AGENT MEANS READ_ONLY CAPABILITY.`

A subagent, fork, or background research agent assigned read-only work MUST NOT be given, and MUST NOT exercise, authority to:

```text
create/update/close a GitHub issue
create/update/close a pull request
push a branch
commit a project change
edit spec, manifest, or assurance content
change NEXT_OWNER / NEXT_ACTION or any coordination status field
emit a handoff label or signal to another agent
merge anything
claim certification
claim owner approval
```

Prompt-level "read only" wording is NOT sufficient as an authorization boundary by itself. Where the launching environment permits it, a read-only agent MUST be launched without GitHub write credentials, git push credentials, or any other repository-mutation capability. If technical isolation is not available, the launching agent MUST tell the subagent explicitly that any write capability it happens to still have is UNUSABLE for that task, and the launching agent remains fully responsible for independently verifying, after the subagent returns, that no writes occurred (issues, PRs, branches, commits, comments) before treating any part of its output as authoritative.

A subagent's own self-report that it stayed within scope is not evidence. The launching agent must check the actual remote/local state.

### 11.10 Governance-decision provenance

Extends §11.7's escalation list with a provenance requirement for citing that escalation's outcome. An agent may state that something is "owner approved," "owner decided," "per owner decision," or "governance approved" ONLY when it can cite an existing, explicit governance record for that exact decision. Valid provenance is one of:

- an explicit message from the owner in the currently-authorized controlling conversation, once that message has been durably recorded into project coordination/assurance evidence; or
- an already-existing governance record in the project's own artifacts (an issue comment, an assurance file, a convergence agreement) that clearly names and scopes the decision being cited.

When citing owner governance, record:

```text
GOVERNANCE_SOURCE
    <artifact / issue / assurance record>
    <exact decision>
    <exact scope>
```

If no such source exists, the agent MUST NOT assert approval. It must instead report:

```text
STATUS
    BLOCKED_FOR_OWNER
NEXT_OWNER
    Owner
```

An agent MUST NOT infer owner approval from: its own or another agent's prior recommendation; an existing architectural preference; the mere existence of an implementation or a draft branch; another agent's own unverified statement that the owner approved something; silence; or the word "Recommended" attached to one option in a menu of choices presented to the owner.

A question that asks the owner to choose among semantic, architectural, parity, scope, or divergence options does not become a decision until the owner actually answers it. Marking one option "Recommended" is a recommendation, not approval — no agent, and no subagent it launches, may act on the recommended option before the owner's own explicit answer is received and durably recorded.

### 11.11 Handoff validation

Before treating a coordination issue, PR, or candidate SHA as eligible for review, implementation, or handoff to another agent, verify:

```text
coordination issue is OPEN and valid
STATUS is not INVALID_UNAUTHORIZED / INCIDENT / BLOCKED_FOR_OWNER
NEXT_OWNER is present
NEXT_ACTION is present
referenced PR(s) are open/current where the status claims they are
candidate SHA(s) are remote-reachable
any governance-dependent choice cited carries a valid GOVERNANCE_SOURCE (§11.10)
the candidate is not built on or derived from a quarantined artifact (§11.12)
```

If any check fails:

```text
HANDOFF_BLOCKED
```

and no next-agent review or implementation may begin from that handoff. This check applies to every agent-to-agent handoff described in §11.4, and to any future automated PR/issue-triggered handoff between Claude and Codex.

### 11.12 Quarantine semantics

An artifact (branch, PR, issue, commit) produced outside its author's actual authorization, or otherwise found to rest on a false governance claim, is `QUARANTINED_ARTIFACT`:

```text
may be preserved for forensic/incident history
must not be merged
must not be reviewed as a candidate
must not be cherry-picked into a valid candidate
must not satisfy manifest/spec/assurance evidence
must not be used for certification
must not be used as the base for a new implementation branch
```

Mark a quarantined issue/PR's title and body with an explicit governance-correction notice, preserving the original content below it for the record, then close it without merging. Preserve the underlying branch(es) until the incident retrospective and any resulting workflow hardening have landed; deletion is then a separate, explicit cleanup decision.

If a quarantined artifact appears to contain a genuinely useful factual observation, it must be RE-DERIVED independently from authoritative sources (pinned Pi, the accepted default branches, current project artifacts) before being relied on for anything. Do not assume prose or code inside a quarantined artifact is correct merely because it reads as well-reasoned.

### 11.13 Deferred parity and trigger-based work

A parity row may legitimately remain deferred when its real integration seam does not yet exist.

Use:

```text
STATUS
    WAITING_FOR_TRIGGER
```

when all of the following are true:

- the row has an explicit `deferred parity` disposition;
- the reason for deferral is architectural/integration readiness, not unresolved semantic uncertainty;
- a concrete closure trigger is recorded;
- no production implementation is currently authorized.

Required state:

```yaml
status: WAITING_FOR_TRIGGER
next_owner: null
next_action: null
deferred_trigger:
  type: architecture_event
  description: >
    A real provider/auth composition surface exists that requires
    Models-equivalent orchestration.
```

`WAITING_FOR_TRIGGER` is not active implementation work and is excluded from the active-state rule requiring a next owner/action (§11.1.2).

When the trigger fires:

1. create or reactivate a normal active work package;
2. fetch current default-branch reality;
3. perform a fresh contract-first Pi audit;
4. do not resume implementation directly from the historical deferred audit;
5. consume already-certified lower/vocabulary requirements normally.

### 11.14 Current state versus historical event log

GitHub coordination has two distinct data classes:

```text
CURRENT STATE
    issue state block / machine-readable coordination record

HISTORY / EVIDENCE
    comments
    review records
    assurance artifacts
    PR timeline
    commits
```

Rules:

- Current state is mutable and MUST be kept current.
- Historical evidence is append-only; do not rewrite prior rejection into approval.
- A later comment MUST NOT silently supersede a stale current-state block.
- Automation and receiving agents MUST read current state first, then use the history to validate it.
- Historical assurance remains durable evidence even after the current-state block advances.

This separation prevents a coordination issue from becoming an event log pretending to be a state store.

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

### 12.6 Machine validation of coordination state

The coordination state defined by `process/coordination-state.md` SHOULD be validated automatically.

At minimum, automation should reject:

- unknown workflow states;
- active states with no `next_owner`;
- active states with no `next_action`;
- `WAITING_FOR_TRIGGER` without `deferred_trigger`;
- `INVALID_UNAUTHORIZED` or `INCIDENT` states attempting a handoff;
- candidate SHAs that are not remote-reachable;
- changed candidate SHA paired with a stale final approval;
- governance-dependent decisions without `governance_source`;
- a candidate derived from a quarantined artifact;
- reject transition to `FINAL_CONTRACT_REVIEW` if any of the following is true:

  - the candidate did not change since the original `IMPLEMENTATION_REVIEW` (§11.4);
  - the candidate carries convergence provenance and the convergence episode still has open findings;
  - the candidate carries convergence provenance and any finding in that episode has not reached `PROVISIONALLY_CLOSED`;
  - the candidate follows the ordinary-remediation route and the preceding targeted `IMPLEMENTATION_REVIEW` still has blocking findings;
  - the candidate follows neither a valid settled-convergence route nor a valid ordinary-remediation route.

  These are invalid states that must reject the transition -- not, as an earlier revision of this section stated, alternative "valid routes" in their own right. A candidate reaching `FINAL_CONTRACT_REVIEW` through ordinary remediation is not required to carry a `convergence` object. A candidate reaching `FINAL_CONTRACT_REVIEW` through convergence retains its settled convergence record (`coordination-state.md` §6) so the validator can verify that targeted closure completed before final review -- route detection uses whether that record exists, never whether the episode is still "active" (`coordination-state.md` §11);
- transition to Rust implementation before shared/Python contract approval/merge;
- a claimed provisional closure without required discriminating negative-control evidence (§11.8.7.1).

The validator enforces workflow structure only. It does not decide semantics.

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

`PROVISIONALLY CLOSED` findings from §11.8 do not satisfy this gate by themselves. Final certification still requires one complete independent review of the exact final candidate.

## 14. Workflow improvement and periodic retrospective

The workflow itself is versioned project infrastructure and should be reviewed regularly rather than treated as permanently correct.

### 14.1 When to review the workflow

Perform a lightweight workflow retrospective at least:

- after each cross-language layer closes;
- after any repeated rejection/remediation cycle;
- immediately when the `CONTRACT_CONVERGENCE` trigger in §11.8 fires;
- after any handoff failure, stale-state incident, remote-sync problem, duplicated work, or unclear ownership boundary;
- immediately after any unauthorized agent action or other authorization-control failure (a subagent exceeding its assigned capability, a false governance/approval claim, an out-of-scope write) — see §11.9-§11.12;
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
- Did a remediation test prove the exact review observation, or only a weaker nearby condition?
- Did the reviewer provide a discriminating witness that the remediation owner could directly turn into a regression test?
- Should semantic characterization have happened before implementation?
- Did repeated full re-reviews add assurance value, or would targeted provisional closure plus one final full review have been stronger and cheaper?
- Did the chosen work-package boundary match the actual independently certifiable semantic surface?
- Did the work package create more coordination/review artifacts than the assurance value justified?
- After convergence fired, were targeted closure reviews used until every blocker was provisionally closed?
- Did any final review re-open a previously settled root-cause surface because the convergence matrix was incomplete?
- Did every executable closure witness demonstrate a realistic negative control?
- Did the current-state block remain synchronized with comments/PR state?
- Should any deferred work have been represented as `WAITING_FOR_TRIGGER` instead of active/open workflow?

### 14.3 Improvement rule

When a reusable process improvement is found:

1. distinguish a **workflow/process improvement** from a **semantic-contract change**;
2. update the appropriate persistent project guidance (`agent-workflow.md`, `CLAUDE.md`, `AGENTS.md`, or normative process docs);
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

For repeated semantic-review cycles, the healthier trend is:

```text
rejection
-> discriminating witness
-> contract convergence
-> provisional finding closure
-> one final complete review
```

rather than:

```text
rejection
-> broad implementation pass
-> complete review
-> newly discovered adjacent edge
-> repeat indefinitely
```

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

When in `CONTRACT_CONVERGENCE`, also report:

- current `OPEN_SURFACE`;
- agreed behavior-matrix / witness artifact;
- provisional finding-closure status;
- whether the candidate is ready for final complete review.

Respect the stop condition in the current task. Never continue automatically into the next review, implementation, or layer.
