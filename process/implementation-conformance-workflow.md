# Minion Agent — Implementation, Conformance & Assurance Workflow

**Status:** Normative project process  
**Applies to:** Python and Rust implementations, shared spec, Pi parity manifest, canonical conformance, assurance, CI, and implementation planning  
**Authority relationship:** The frozen master design requires this process to be followed. This document governs *how* implementations are developed, synchronized, audited, certified, and frozen; it does not redefine Minion Agent semantics.

---

## 1. Core principle

Minion Agent is one project with one semantic contract and multiple first-class implementations.

```text
                 Pi source
                    │
                    ▼
            parity manifest
                    │
                    ▼
             normative spec
                    │
                    ▼
          canonical conformance
             │             │
             ▼             ▼
          Python          Rust
       implementation  implementation
             │             │
             └──────┬──────┘
                    ▼
              assurance audit
                    │
                    ▼
             layer certification
                    │
                    ▼
                phase freeze
```

Python and Rust are independent implementations of the same contract.

Neither implementation is a behavioral oracle for the other.

> **Python may lead implementation; it MUST NOT become the behavioral oracle.**

When Pi-derived behavior is uncertain, the adopted Pi source revision is inspected first. The resulting behavior is expressed through the parity manifest, normative spec, and canonical conformance before either implementation is treated as authoritative.

Assurance adds evidence and release discipline. It does not create an alternative semantic authority.

---

## 2. Repository ownership model

Shared semantic artifacts have exactly one canonical project-level location.

The current Minion Agent monorepo uses:

```text
minion-agent/
├── conformance/
│   ├── agent/
│   ├── runtime/
│   ├── schema/
│   └── session/
├── minion-agent-python/
├── minion-agent-rust/
└── pi-parity-manifest.yaml
```

The documentation repository contains the corresponding governance and normative documents:

```text
minion-agent-docs/
├── design/
├── spec/
├── process/
├── assurance/
├── plans/
└── reference/
```

The canonical Pi parity manifest currently lives at:

```text
/pi-parity-manifest.yaml
```

The following are shared project artifacts and MUST NOT be independently forked by language:

```text
design/
spec/
process/
assurance/                 # governance/evidence, not semantic authority
/pi-parity-manifest.yaml
/conformance/
```

Python and Rust may have language-specific runners and implementation-specific tests, but both consume the same canonical conformance data.

---

## 3. Semantic authority

For Pi-derived behavior:

```text
Pi at the adopted revision
    -> parity manifest
    -> normative spec
    -> canonical conformance
    -> implementations
```

The frozen master design defines the project's mandatory Pi-fidelity goal and architecture.

The normative spec defines the general semantic rules.

Canonical conformance defines executable finite examples.

The parity manifest provides traceability from Pi source to rule, scenario, implementation, and disposition.

Assurance documents provide evidence that the implementation, tests, failure behavior, security review, observability, reliability, and documentation have been audited. Assurance does **not** override Pi/spec/conformance semantics.

Python behavior is never accepted as proof that Rust should behave the same way, and Rust behavior is never accepted as proof that Python should behave the same way.

If an implementation conflicts with Pi/spec/conformance, the implementation is corrected unless an intentional divergence is explicitly approved and recorded through the normal design/spec/conformance governance path.

---

## 4. Fidelity versus hardening

During the current Pi-alignment program, **Pi behavioral fidelity remains the primary semantic objective**.

Security, reliability, observability, performance, operability, documentation, and production-quality reviews are mandatory, but they do not independently authorize observable divergence from Pi.

Use this classification order for every assurance finding:

```text
For a Pi-derived behavior, is Pi behavior uncertain?
    -> PI_BEHAVIOR_UNCERTAIN

Does Minion differ from known adopted Pi-visible behavior?
    -> PI_PARITY_DEFECT

Is Minion's frozen contract/spec/conformance/traceability/evidence incomplete or inconsistent?
    -> CONTRACT_ASSURANCE_DEFECT

Otherwise, does remediation preserve Pi-visible behavior?
    YES -> PARITY_NEUTRAL_HARDENING
    NO  -> PARITY_CONSTRAINED_RISK
```

`CONTRACT_ASSURANCE_DEFECT` is an evidence/contract-integrity classification, not a new source of
semantic authority. It is especially important for Minion-owned architectural surfaces such as the
plugin/runtime layer, where a defect may be real even though there is no corresponding Pi runtime
behavior to mismatch.

### 4.1 Pi parity defect

If Minion differs from the adopted Pi behavior:

```text
classification:
    PI_PARITY_DEFECT

action:
    fix before certification
```

### 4.2 Contract-assurance defect

If the frozen Minion contract or its required evidence is incomplete or internally inconsistent:

```text
classification:
    CONTRACT_ASSURANCE_DEFECT

action:
    repair spec / conformance / traceability / evidence before certification
```

Examples include a normative rule without executable evidence, a missing spec for a frozen
Minion-owned layer, inconsistent contract references, or a requirement with no explicit evidence
disposition.

A contract-assurance defect is not accepted risk debt and does not go into
`assurance/risk-register.md`.

### 4.3 Parity-neutral hardening

If the issue can be corrected without changing Pi-visible behavior:

```text
classification:
    PARITY_NEUTRAL_HARDENING

action:
    normally fix during the current phase
```

Examples include secret redaction, internal type safety, resource-leak fixes, documentation correction, and diagnostic improvements that do not alter observable semantics.

### 4.4 Parity-constrained risk

If remediation would change Pi-visible behavior:

```text
classification:
    PARITY_CONSTRAINED_RISK

action:
    preserve Pi-compatible baseline
    record in assurance/risk-register.md
    defer semantic decision to post-parity hardening
```

Unless the normal governance path explicitly approves an intentional divergence.

### 4.5 Pi behavior uncertain

If Pi behavior is not known with sufficient confidence:

```text
classification:
    PI_BEHAVIOR_UNCERTAIN

action:
    stop the semantic implementation decision
    inspect adopted Pi source
    update manifest/spec/conformance
    then continue
```

Do not infer Pi behavior from generic best practice.

### 4.6 Contract stability and implementation quality

Contract stability is important, but it is not an objective that overrides implementation quality.

A frozen or currently stable contract MUST NOT force an implementation into an unnecessarily
fragile, duplicated, contorted, or semantically artificial design when new implementation evidence
shows that the contract itself is incomplete or incorrect.

Use this rule:

```text
A better implementation is discovered
    ↓
Would it preserve the existing observable contract?
    ├─ YES
    │   -> use the better implementation
    │   -> no shared-contract change is required
    │
    └─ NO
        ↓
      Why does the observable behavior need to change?
        ├─ the existing contract is incomplete, contradictory,
        │  or prevents a coherent implementation
        │
        │   -> CONTRACT_ASSURANCE_DEFECT
        │   -> reopen the affected shared contract deliberately
        │   -> update spec/conformance/traceability as required
        │   -> review all reached implementations
        │
        └─ the alternative is merely preferable, cleaner,
           or potentially more effective
            -> preserve the current compatible baseline
            -> record the alternative for post-parity hardening
               or intentional-divergence review
```

Do not optimize for contract stability at the expense of architecture.

Warning signs that SHOULD trigger a contract-quality review include:

```text
runner or adapter code must simulate library semantics
the same normative rule must be reimplemented in multiple layers
special cases exist primarily to preserve an underspecified contract
errors must be swallowed, distorted, or hidden to maintain compatibility
state/queue/flag machinery exists only to reproduce an accidental ambiguity
the implementation must bypass the abstraction that nominally owns the behavior
two conforming implementations are forced to make observably different choices
because the shared contract does not define a required semantic boundary
```

These signs do not automatically authorize a contract change. They require an explicit review of
whether the problem is implementation-local or a `CONTRACT_ASSURANCE_DEFECT`.

Conversely, a contract MUST NOT be reopened merely because another implementation would be cleaner,
more idiomatic, or easier to build.

The governing principle is:

> **Make the contract deliberately hard to change, but never preserve it merely because it is
> already stable when implementation evidence shows that it is wrong or materially incomplete.**

Certification does not require zero architectural alternatives. It requires confidence that:

```text
the shared contract is sufficiently specified
the implementation satisfies it without semantic workarounds
the implementation is structurally sound for its language
known contract limitations have explicit dispositions
```

A layer MUST NOT be certified if its apparent conformance depends on architectural workarounds that
mask a known `CONTRACT_ASSURANCE_DEFECT`.

---

## 5. Per-phase development workflow

Every semantic phase follows this sequence:

```text
1. Audit relevant Pi source at the adopted revision
2. Update /pi-parity-manifest.yaml
3. Update normative spec
4. Add or update canonical conformance
5. Run conformance against implementation(s) that have reached the layer
6. Implement or realign Python and/or Rust
7. Add or repair implementation-specific tests
8. Run the applicable assurance audit
9. Remediate Pi parity defects
10. Remediate contract-assurance defects
11. Remediate parity-neutral hardening findings
12. Record parity-constrained risks
13. Make all applicable canonical conformance green
14. Complete layer certification
15. Complete phase review
16. Freeze phase
```

Assurance should follow implementation closely enough to inspect real code and tests, but must occur before certification/freeze.

### 5.1 Audit Pi first

Before implementing Pi-derived behavior, inspect the exact Pi source paths and symbols owned by the phase.

Do not design from a generalized abstraction first and check Pi afterward.

### 5.2 Update the parity manifest

Every newly discovered Pi-visible surface must have exactly one disposition:

```text
adopted
deferred parity
intentional divergence
```

Silence is not a valid disposition.

Each manifest row should map:

```text
Pi source path + symbol
    -> spec rule
    -> canonical scenario(s) or explicit language-specific test
    -> Python location
    -> Rust location / planned phase
    -> disposition
```

### 5.3 Update spec before or with implementation

If behavior is cross-language and externally observable, its general rule belongs in the normative spec.

Implementation code must not become the first or only place where that behavior is defined.

### 5.4 Add or update canonical conformance

Concrete observable examples should be executable before, or in the same change as, the implementation that fixes or introduces them.

A conformance scenario may legitimately expose a known divergence in an existing implementation or pin already-correct behavior so it cannot regress.

### 5.5 Implement

Implementation follows the contract. It must not alter canonical expected behavior merely to make the current language implementation easier.

### 5.6 Perform assurance audit

Affected layers MUST be audited according to:

```text
assurance/fidelity-assurance-method.md
```

Use:

```text
assurance/layer-certification-template.md
```

to produce or update:

```text
assurance/layers/<layer>.md
```

The audit covers, as applicable:

```text
requirement traceability
existing-test validity
failure behavior
security
reliability / operations
observability
performance / complexity
public API / serialization
documentation accuracy
known production risks
```

The process document deliberately does not duplicate the detailed audit procedure; the assurance method owns that detail.

### 5.7 Finding flow

Every assurance finding must be classified.

```text
PI_PARITY_DEFECT
    -> fix now

CONTRACT_ASSURANCE_DEFECT
    -> repair contract/spec/conformance/traceability/evidence before certification
    -> do not defer to the risk register

PARITY_NEUTRAL_HARDENING
    -> normally fix now

PARITY_CONSTRAINED_RISK
    -> record in assurance/risk-register.md
    -> preserve Pi-compatible baseline

PI_BEHAVIOR_UNCERTAIN
    -> stop semantic decision
    -> source-audit Pi
```

A finding may not remain unclassified.

### 5.8 Layer certification

A layer certification is evidence that the layer is ready for the current Pi-compatible baseline.

Certification requires the applicable contract, conformance, implementation tests, assurance review, and finding disposition to be complete.

Certification does **not** mean every post-parity production improvement has already been implemented.

### 5.9 Freeze gate

A phase cannot freeze until:

- relevant Pi parity manifest rows are complete;
- relevant spec rules are present;
- applicable canonical conformance is defined;
- every implementation that has reached the phase is green against applicable canonical conformance;
- implementation-specific tests are green;
- affected assurance layer reports are complete;
- all findings have a disposition;
- no unresolved `PI_BEHAVIOR_UNCERTAIN` remains;
- no unresolved Pi parity defect remains;
- no unresolved `CONTRACT_ASSURANCE_DEFECT` remains;
- parity-constrained risks are recorded in `assurance/risk-register.md`;
- the affected layer certification gate is satisfied;
- known deferred parity is explicitly recorded.

A phase does **not** require later, not-yet-implemented language layers to exist merely for the current implementation to certify.

---

## 6. Bottom-up foundation audit order

During the current realignment, use the dependency-aware audit order:

```text
0. Shared contract / conformance / audit infrastructure
1. Runtime kernel
2. LLM semantic vocabulary
3. Session + artifacts
4. Target-model transformation
5. Tool model + registry
6. Tool execution pipeline
7. Agent public state + inbox/queues
8. Agent run/turn state machine
9. Cancellation across Agent / LLM / tools
10. Provider abstraction + mock adapter
11. Real providers
12. Execution seams
13. Built-in tools
14. Prompt assembly + skills
15. Full compaction behavior
16. Telemetry + diagnostics + invariants
17. Integrated foundation
18. Model-backed evals
```

LLM vocabulary precedes session projection because session projection/reconstruction depends on the public message/content schema.

The audit order distinguishes implementation state:

```text
IMPLEMENTED
NOT_IMPLEMENTED
DEFERRED
NOT_APPLICABLE
```

A planned layer is not a certification failure merely because its implementation phase has not started.

---

## 7. Python-leading development

Python may remain ahead of Rust by approximately half a phase to one phase.

Recommended cadence:

```text
time ──────────────────────────────────────────────>

Python:
contract N -> implementation N -> assurance/certification N
                         contract N+1 -> implementation N+1 -> ...

Rust:
                  implementation N -> assurance/certification N
                                              implementation N+1 -> ...
```

Recommended project invariant:

```text
Python phase = N
Rust phase   = N or N-1
```

Large multi-phase drift should be avoided because it weakens Rust's role as an independent validation of the shared contract.

### 7.1 What Python is allowed to lead

Python may lead:

- implementation;
- discovery of engineering edge cases;
- first execution of new canonical conformance;
- implementation-specific engineering decisions;
- first layer assurance against the shared contract.

Python does **not** lead semantic authority.

### 7.2 New behavior discovered during Python implementation

If Python implementation work reveals a new cross-language observable Pi semantic:

```text
discover behavior
    -> verify in Pi
    -> update parity manifest
    -> update spec
    -> add/update conformance
    -> implement/fix Python
    -> certify Python layer
    -> Rust consumes the same shared contract later
```

Do not silently implement behavior only in Python and ask Rust to copy it.

### 7.3 Certification while Rust is behind

The project tracks separate statuses:

```text
shared contract status
Python implementation/certification status
Rust implementation/certification status
```

Example:

```text
LLM layer

shared contract: CERTIFIED
Python:          CERTIFIED
Rust:            NOT_IMPLEMENTED — planned Phase 2
```

This is a valid state.

When Rust later reaches the layer, it must run the same canonical conformance and complete its own implementation-specific assurance evidence.

---

## 8. Rust implementation workflow

Rust consumes the same shared semantic contract.

Normal Rust flow:

```text
parity manifest row
    -> normative spec
    -> canonical scenario
    -> Rust implementation
    -> Rust-specific tests
    -> applicable conformance green
    -> assurance review
    -> Rust layer certification
```

Rust may read Python code for Minion package boundaries, plugin ownership, naming, engineering techniques, and already-solved non-semantic implementation issues.

For semantic questions, Rust should consult Pi/spec/conformance rather than infer required behavior from Python.

Rust implementation status for a layer must be recorded as one of:

```text
IMPLEMENTED
NOT_IMPLEMENTED
DEFERRED
NOT_APPLICABLE
```

---

## 9. Conformance runner rule

Python and Rust may each implement a language-specific conformance runner.

A runner may:

- deserialize canonical scenario data;
- construct typed public inputs;
- call real public implementation APIs;
- normalize returned values to canonical JSON;
- compare actual vs expected observable output.

A runner MUST NOT implement semantic behavior that belongs in the library.

Forbidden examples include:

- implementing `transformMessages`;
- deciding tool termination semantics;
- reordering steering/follow-up;
- performing session derivation;
- fusing a stream because the library does not;
- converting tool-hook exceptions into error results outside the real tool pipeline.

If a runner can make an incorrect implementation pass by supplying missing semantics itself, the runner is invalid.

A mock provider/tool swapped in through the library's own real plugin/service seam is not covered
by this rule — that is the mechanism scenario scripts (`provider_script:`, `tools:`) rely on, not a
violation of it. The dividing line: if a real provider, unmodified, would exercise the same code
path as the mock, it's a seam. If the runner's own code decides the "correct" outcome instead of
asking the library, that's the library's job leaking into the runner.

---

## 10. Canonical conformance ownership

Canonical conformance lives once at repository root:

```text
conformance/
    runtime/
    session/
    agent/
    schema/
```

The canonical parity manifest is separate at repository root:

```text
/pi-parity-manifest.yaml
```

Do not maintain separate Python and Rust copies.

Language-specific runners live with the implementations, for example:

```text
minion-agent-python/tests/conformance/
minion-agent-rust/.../tests/conformance/
```

Both consume the same root-level canonical scenarios.

### 10.1 Scenario schema format and placeholder scenarios

`conformance/schema/` may hold more than one scenario schema shape at once during a realignment.
Legacy per-family schemas may coexist with the newer unified scenario shape while older cases are
progressively migrated. A scenario's own top-level `family` key selects the unified schema when
present.

A newly scaffolded scenario MAY contain string values beginning with `TO_BE_` as a structurally
valid placeholder. Both language-specific runners and CI MUST detect such values recursively from
the document itself and mark the case expected-failure/`xfail` with a reason referencing this
policy. They MUST NOT silently skip it or hardcode a list of placeholder scenario names.

Migration of legacy scenarios should occur with the phase that owns the behavior, not as an
unrelated bulk mechanical rewrite.

---

## 11. Implementation-specific tests

Use canonical conformance for:

- cross-language observable semantics;
- Pi-visible behavior;
- serialized contract shape;
- deterministic compatibility cases.

Use implementation-specific tests for:

- internal data structures;
- Tokio/asyncio mechanics;
- language-specific error plumbing;
- provider wire-parser fragmentation;
- memory ownership;
- type-level guarantees;
- defensive branches;
- language-specific performance details.

Existing tests are not automatically trusted merely because they pass.

During assurance, each relevant existing test should be evaluated against the current normative contract and classified as:

```text
KEEP
STRENGTHEN
MOVE TO CONFORMANCE
REWRITE
DELETE
```

A passing test that asserts superseded semantics is not evidence of correctness.

Python's existing 100% configured line-coverage floor is a quality floor, not proof of semantic completeness or Pi parity.

---

## 12. Assurance ownership

The active assurance framework is maintained under:

```text
assurance/
    README.md
    2026-08-22-foundation-fidelity-assurance-charter.md
    fidelity-assurance-method.md
    layer-certification-template.md
    risk-register.md
    foundation-release-gate.md
    layers/
```

Responsibilities are separated:

```text
process/
    when assurance happens
    what blocks certification/freeze
    how findings flow

assurance/
    how the audit is performed
    evidence for each layer
    risk register
    final foundation release gate
```

The process document MUST NOT duplicate or redefine detailed assurance methodology.

The assurance documents MUST NOT redefine frozen semantic behavior.

---

## 13. Risk register

Use:

```text
assurance/risk-register.md
```

for production-quality risks that require explicit lifecycle management.

A parity-constrained risk may remain through the Pi-compatible baseline only when:

```text
Pi-compatible behavior is understood
AND
the risk is documented
AND
the reason for deferral is explicit
AND
the future decision/remediation path is recorded
```

`PI_BEHAVIOR_UNCERTAIN` is not acceptable risk-register debt; the Pi behavior must first be resolved.

A Pi parity defect is also not accepted risk debt; it must be fixed before certification.

A `CONTRACT_ASSURANCE_DEFECT` is likewise not risk-register debt. Missing/inconsistent
spec/conformance/traceability/evidence must be repaired before certification.

After the Pi-compatible foundation is complete, the risk register becomes a primary input to the post-parity hardening phase.

---

## 14. Pull request strategy

Prefer short-lived branches and trunk-based development. Do not maintain long-lived `python-dev` and `rust-dev` branches.

Recommended branch shapes:

```text
feat/pi-agent-turn-order
feat/python-phase4-tools
feat/rust-phase4-tools
fix/conformance-terminate
audit/runtime-foundation
```

### 14.1 Semantic change PR

Where practical, one PR should make a semantic change atomic across:

```text
/pi-parity-manifest.yaml
spec
conformance
Python
Rust where implemented/reached
assurance evidence when the layer is affected
```

### 14.2 Python-leading split PR

When Python leads, split PRs are acceptable:

```text
PR 1
    parity manifest
    spec
    conformance
    Python implementation
    Python assurance evidence

PR 2
    Rust implementation
    Rust-specific tests
    same canonical conformance
    Rust assurance evidence
```

The Rust PR should reference the same manifest IDs and canonical scenarios.

### 14.3 Implementation-only PR

A language-specific implementation-only change must not alter observable semantics.

If it does, it must be reclassified as a semantic change and update the shared contract artifacts.

### 14.4 Assurance-only PR

An assurance-only PR may:

- add audit evidence;
- classify findings;
- document risk;
- correct stale documentation;
- strengthen tests without semantic changes.

If assurance discovers a semantic mismatch, the remediation PR must follow the normal Pi/spec/conformance workflow.

---

## 15. PR classification

PR templates should distinguish at least:

```text
[ ] implementation only
[ ] Pi parity correction
[ ] spec change
[ ] conformance change
[ ] assurance/audit change
[ ] parity-neutral hardening
[ ] intentional divergence
[ ] deferred parity update
```

For semantic changes, record:

```text
Pi source:
Parity manifest ID:
Spec section:
Conformance scenario(s):
Assurance layer:
Python status:
Rust status:
```

For parity-constrained findings, also record:

```text
Risk register ID:
Why remediation changes Pi-visible behavior:
Post-parity action:
```

**Shared-contract reviewer rule (adopted, see
`process/shared-contract-reviewer-policy-proposal.md`).** Changes under `conformance/**`, `spec/**`, or
`/pi-parity-manifest.yaml` MUST receive explicit semantic-owner approval before merge. Where
independent Python and Rust implementation maintainers exist, such changes SHOULD also receive
review from the affected implementation owners. Promote this to CODEOWNERS/branch-protection
enforcement once those ownership roles are staffed.

---

## 16. Parallel coding agents and Git worktrees

When Codex, Claude Code, or multiple developers work concurrently, prefer separate Git worktrees rather than sharing one mutable checkout.

Example:

```text
minion-agent/                   main / review
minion-agent-contract-work/     spec + conformance
minion-agent-python-work/       Python implementation
minion-agent-rust-work/         Rust implementation
minion-agent-assurance-work/    layer audit + evidence
```

Example commands:

```bash
git worktree add ../minion-agent-contract-work feat/phase3-contract
git worktree add ../minion-agent-python-work feat/python-phase3
git worktree add ../minion-agent-rust-work feat/rust-phase3
git worktree add ../minion-agent-assurance-work audit/phase3
```

Shared semantic files should be merged to `main` early so implementation and assurance work consume the same contract revision.

Avoid auditing one contract revision while implementation work has silently moved to another.

---

## 17. CI gates

Recommended CI decomposition:

```text
contract
    schema validation
    /pi-parity-manifest.yaml validation
    conformance fixture validation

python
    unit tests
    property tests
    Python conformance runner
    coverage floor
    type/lint gates

rust
    unit tests
    property tests
    Rust conformance runner
    language-specific static/quality gates

cross-language
    verify both runners consume the same canonical cases
    compare canonical serialized outputs where appropriate

assurance
    validate required layer reports exist for gated phases
    validate finding/risk references where machine-checkable
    validate no unresolved gate-blocking status for a freeze/release candidate
```

Path-sensitive policy should reflect the current repository layout.

Changes under:

```text
conformance/**
spec/**
/pi-parity-manifest.yaml
```

change the shared contract and require the semantic gates for every implementation that has reached the affected layer.

A language that has not yet implemented that layer records `NOT_IMPLEMENTED`; it is not required to invent an implementation merely to satisfy a contract-only PR.

**Provider wire-fixture verification is never a CI gate.** Recorded/sanitized fixtures and pure
codec tests may run in ordinary CI; live credentialed provider verification remains manual and
non-gating.

---

## 18. Compatibility and assurance status

Generate compatibility status from machine-readable sources where possible rather than maintaining a hand-written compatibility matrix.

Inputs should include:

```text
/pi-parity-manifest.yaml
+
conformance runner results
```

Assurance certification is separate evidence and may initially remain document-based:

```text
assurance/layers/*.md
+
assurance/risk-register.md
+
assurance/foundation-release-gate.md
```

Over time, stable status fields may be machine-validated, but automation must not become a second semantic implementation.

---

## 19. Documentation drift

Documentation is part of the implementation assurance surface.

A phase review should verify that:

- repository status claims match actual implemented packages;
- planned vs implemented layers are clearly distinguished;
- public API documentation matches the code;
- conformance/manifest paths are current;
- stale design assumptions are not presented as active semantics.

Documentation corrections that do not change Pi-visible behavior are parity-neutral hardening and should normally be fixed during the current phase.

---

## 20. Model-backed evals

Model-backed evals are not semantic correctness authority.

They answer questions such as:

```text
Does the agent perform well on real tasks?
Did a prompt/tool/skill/plugin/configuration improve behavior?
What changed in cost/latency/tool trajectory?
```

They do **not** decide:

```text
What does Pi semantics require?
Is a conformance mismatch acceptable?
Should a known Pi behavior be changed?
```

If eval results suggest that a non-Pi behavior performs better, record it as a potential post-parity improvement. Do not silently replace the Pi-compatible baseline.

---

## 21. Pi drift workflow

Do not continuously mix upstream Pi changes into an in-progress baseline realignment.

For a new candidate Pi revision:

```text
1. complete current baseline alignment
2. identify old adopted Pi revision
3. identify candidate new revision
4. diff phase-owned Pi source paths
5. enumerate observable semantic changes
6. give every change a disposition
7. update parity manifest/spec/conformance
8. realign Python/Rust
9. update affected assurance evidence
10. certify affected layers
11. freeze the new baseline
```

A new Pi revision is a source-diff exercise, not permission to reopen unrelated architecture.

---

## 22. Post-parity hardening workflow

After the Pi-compatible foundation baseline is approved:

```text
assurance/risk-register.md
    ↓
post-parity review
    ↓
decide:
    preserve Pi
    or
    intentionally diverge
```

Any intentional observable divergence follows:

```text
risk finding
    -> design decision
    -> explicit divergence
    -> parity manifest disposition
    -> spec update
    -> conformance update
    -> Python/Rust implementation
    -> assurance update
    -> compatibility/migration review
```

A production-hardening cleanup must never create accidental semantic divergence.

---

## 23. Project invariants

1. **One semantic contract.**
2. **One canonical conformance suite.**
3. **One canonical parity manifest at `/pi-parity-manifest.yaml`.**
4. **Python and Rust are first-class implementations.**
5. **Python may lead implementation but is never the behavioral oracle.**
6. **Rust must not blindly copy Python semantics.**
7. **Pi-derived semantic questions go back to Pi/spec/conformance.**
8. **Cross-language observable discoveries are promoted into manifest/spec/conformance.**
9. **Conformance stays slightly ahead of implementation, not many phases ahead.**
10. **Assurance is mandatory before layer certification and phase freeze.**
11. **Assurance does not redefine semantic authority.**
12. **All assurance findings receive an explicit classification/disposition.**
13. **Contract-assurance defects must be repaired before certification and are not deferred risk debt.**
14. **Contract stability must not force inferior architecture when implementation evidence exposes a materially incomplete or incorrect contract.**
15. **Parity-neutral hardening should normally be fixed in the current phase.**
16. **Parity-constrained risk is documented and deferred unless divergence is formally approved.**
17. **Pi behavior uncertainty blocks semantic decision-making until source audit resolves it.**
18. **A phase freezes only when its applicable contract, implementation, and assurance gates are satisfied.**
19. **A language not yet at a layer may remain `NOT_IMPLEMENTED`; another implementation may still certify against the shared contract.**
20. **Implementation-only changes may not silently change observable behavior.**
21. **Documentation accuracy is part of assurance.**
22. **Model-backed evals measure effectiveness, not Pi semantic correctness.**
23. **Later Pi revisions are handled through explicit drift audits.**

---

## 24. Working summary

```text
Pi audit
    ↓
/pi-parity-manifest.yaml
    ↓
spec
    ↓
canonical conformance
    ↓
implementation
    ↓
implementation-specific tests
    ↓
assurance audit
    ├── parity defects -> fix
    ├── contract-assurance defects -> repair contract/evidence
    ├── parity-neutral hardening -> fix
    ├── parity-constrained risks -> risk register
    └── Pi uncertainty -> source audit
    ↓
applicable conformance green
    ↓
layer certification
    ↓
phase review
    ↓
phase freeze
```

Python may reach an implementation stage first.

Rust may follow one phase behind.

**The shared contract must reach both first, and assurance must certify what each implementation actually claims to have completed.**
