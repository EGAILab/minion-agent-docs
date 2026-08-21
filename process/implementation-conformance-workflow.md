# Minion Agent — Implementation & Conformance Workflow

**Status:** Normative project process  
**Applies to:** Python and Rust implementations, shared spec, parity manifest, canonical conformance, CI, and implementation planning  
**Authority relationship:** The frozen master design requires this process to be followed. This document governs *how* implementations are developed and synchronized; it does not redefine Minion Agent semantics.

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
```

Python and Rust are independent implementations of the same contract.

Neither implementation is a behavioral oracle for the other.

> **Python may lead implementation; it MUST NOT become the behavioral oracle.**

When Pi-derived behavior is uncertain, the adopted Pi source revision is inspected first. The resulting behavior is expressed through the parity manifest, normative spec, and canonical conformance before either implementation is treated as authoritative.

---

## 2. Repository ownership model

Shared semantic artifacts have exactly one canonical location, split across two repositories:

```text
minion-agent-docs/              (separate repo — design/spec/process/plans)
├── design/
├── spec/
├── process/
│   └── implementation-conformance-workflow.md
└── plans/
    ├── python/
    └── rust/

minion-agent/                   (separate repo — the shared code monorepo)
├── pi-parity-manifest.yaml
├── conformance/
│   ├── schema/
│   ├── runtime/
│   ├── session/
│   └── agent/
│
├── minion-agent-python/
│   ├── src/
│   └── tests/
│
├── minion-agent-rust/
│   ├── crates/
│   └── tests/
│
└── .github/
    └── workflows/
```

`minion-agent-docs/` and `minion-agent/` are separate repositories today, not nested directories of one
another — this reflects the project's actual established layout, not an aspirational restructuring.
Folding `minion-agent-docs/` into the code monorepo (for atomic cross-cutting commits touching design and
code together) is a legitimate option some projects take, but it is a distinct decision with real
tradeoffs (it also loses the lighter-weight, code-free repo a non-engineering stakeholder might want
access to) and has not been made. Do not assume it and do not execute it as a side effect of following
this document.

`minion-agent-python/` and `minion-agent-rust/` keep their established names (matching their GitHub
repo names and, for Python, git history preserved via a history-preserving move into the monorepo) rather
than being renamed to generic `python/`/`rust/`.

The following are shared project artifacts and MUST NOT be independently forked by language:

```text
minion-agent-docs/design/
minion-agent-docs/spec/
minion-agent-docs/process/
minion-agent/conformance/
minion-agent/pi-parity-manifest.yaml
```

Python and Rust may have language-specific runners and tests, but both consume the same canonical conformance data.

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

Python behavior is never accepted as proof that Rust should behave the same way, and Rust behavior is never accepted as proof that Python should behave the same way.

If an implementation conflicts with Pi/spec/conformance, the implementation is corrected unless an intentional divergence is explicitly approved and recorded.

---

## 4. Per-phase development workflow

Every semantic phase follows this sequence:

```text
1. Audit relevant Pi source at the adopted revision
2. Update parity manifest
3. Update normative spec
4. Add or update canonical conformance
5. Run conformance against existing implementation(s)
6. Implement or realign Python and/or Rust
7. Add implementation-specific tests
8. Make all applicable canonical conformance green
9. Complete phase review
10. Freeze phase
```

### 4.1 Audit first

Before implementing Pi-derived behavior, inspect the exact Pi source paths and symbols owned by the phase.

Do not design from a generalized abstraction first and check Pi afterward.

### 4.2 Update the parity manifest

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

### 4.3 Update spec before or with implementation

If the behavior is cross-language and externally observable, its general rule belongs in the normative spec.

Implementation code must not become the first or only place where that behavior is defined.

### 4.4 Add or update canonical conformance

Concrete observable examples should be executable before, or in the same change as, the implementation that fixes or introduces them.

A conformance scenario may legitimately expose a known divergence in an existing implementation or pin already-correct behavior so it cannot regress.

### 4.5 Implement

Implementation follows the contract. It must not alter canonical expected behavior merely to make the current language implementation easier.

### 4.6 Freeze gate

A phase cannot freeze until:

- relevant parity-manifest rows are complete;
- relevant spec rules are present;
- applicable canonical conformance is defined;
- every implementation that has reached that phase is green against the applicable canonical conformance;
- known deferred parity is explicitly recorded.

---

## 5. Python-leading development

Python may remain ahead of Rust by approximately half a phase to one phase.

Recommended cadence:

```text
time ──────────────────────────────────────────────>

Python:
Phase N audit/spec/conformance -> implementation -> green
                             Phase N+1 audit/spec/conformance -> ...

Rust:
                     Phase N implementation -> green
                                               Phase N+1 ...
```

Recommended project invariant:

```text
Python phase = N
Rust phase   = N or N-1
```

Large multi-phase drift should be avoided because it weakens Rust's role as an independent validation of the shared contract.

**OPEN ITEM — no stated backstop for when this invariant is already exceeded.** As of this document's
review, it is: Rust retains only completed Phase 1 runtime per the frozen master's own "Existing
implementation realignment" section, while Python's pre-realignment code reached Phase 4-5 territory.
This document names a target gap but not what happens once the actual gap exceeds it — pause new Python
semantic PRs, escalate to a named owner, accept the debt explicitly and track it, or something else.
Needs an explicit decision from the project owner, not an invented policy.

### 5.1 What Python is allowed to lead

Python may lead implementation, discovery of engineering edge cases, first execution of new canonical conformance, and implementation-specific design decisions.

Python does **not** lead semantic authority.

### 5.2 New behavior discovered during Python implementation

If Python implementation work reveals a new cross-language observable Pi semantic:

```text
discover behavior
    -> verify in Pi
    -> update parity manifest
    -> update spec
    -> add/update conformance
    -> implement/fix Python
    -> Rust consumes the same contract
```

Do not silently implement the behavior only in Python and ask Rust to copy it later.

---

## 6. Rust implementation workflow

Rust consumes the same shared semantic contract.

Normal Rust implementation flow:

```text
parity manifest row
    -> normative spec
    -> canonical scenario
    -> Rust implementation
    -> conformance green
```

Rust may read Python code for Minion package boundaries, plugin ownership, naming, engineering techniques, and already-solved non-semantic implementation issues.

For semantic questions, Rust should consult Pi/spec/conformance rather than infer required behavior from Python.

---

## 7. Conformance runner rule

Python and Rust may each implement a language-specific conformance runner.

A runner may deserialize canonical scenario data, construct typed public inputs, call real public implementation APIs, normalize returned values to canonical JSON, and compare actual vs expected observable output.

A runner MUST NOT implement semantic behavior that belongs in the library.

Forbidden examples include implementing `transformMessages`, deciding tool termination semantics, reordering steering/follow-up, performing session derivation, fusing a stream because the library does not, or converting tool-hook exceptions into error results outside the real tool pipeline.

If a runner can make an incorrect implementation pass by supplying missing semantics itself, the runner is invalid.

**A mock provider/tool swapped in through the library's own real plugin/service seam is not covered by
this rule and is expected.** Scenario scripts (`provider_script:`, `tools:`) drive the real library
through its real public entry points with a scripted LLM/tool backend standing in for a live one — that
is the whole mechanism this suite relies on, not a violation of it. The rule targets a runner that steps
*around* the seam to hand-simulate loop/transform/termination/derivation behavior itself. The dividing
line: if replacing the mock backend with a real provider, unmodified, would still exercise the same code
path, it's a seam. If the runner's own code decides what the "correct" observable outcome is instead of
asking the library, it's the library's job that leaked into the runner.

---

## 8. Canonical conformance ownership

Canonical conformance lives once at the `minion-agent/` repository root, alongside the parity manifest
as a sibling (not nested inside `conformance/`):

```text
minion-agent/
    pi-parity-manifest.yaml
    conformance/
        runtime/
        session/
        agent/
        schema/
```

Do not maintain separate Python and Rust copies.

Language-specific runners live with the implementations, for example:

```text
minion-agent-python/tests/conformance/
minion-agent-rust/tests/conformance/
```

Both read the same root-level canonical scenarios.

### 8.1 Scenario schema format and migration

`conformance/schema/` may hold more than one scenario schema shape at once during a realignment — this
is expected, not an error state to resolve immediately. Concretely: a legacy per-family schema shape
(`{name, provider_script, tools, steps, expect_*}`, one JSON Schema file per family,
`additionalProperties: false`) may coexist with a newer unified shape
(`{name, family, status, authority, pi_revision, given, when, expect}`) while older scenarios are
progressively rewritten into the newer shape.

Rules while both shapes coexist:

- Every scenario file states which shape it uses unambiguously (the presence/absence of `family` as a
  top-level key is sufficient; do not require guessing from file location or naming).
- A scenario validates against the schema matching its own shape, not the newest schema unconditionally.
  A conformance-schema-validation test must select the schema per scenario, not assume one schema file
  per family.
- Migrating an old-shape scenario to the new shape is done when the phase that owns its behavior is
  implemented against the realigned contract — not as a bulk mechanical rewrite disconnected from actual
  implementation work, and not left permanently on the old shape once its owning phase has landed.
- A newly scaffolded scenario for behavior that has no implementation yet MAY exist as a structurally
  valid placeholder (e.g. explicit `TO_BE_FILLED`/`TO_BE_BOUND`/`TO_BE_PINNED` sentinel values) so its
  name and intended family are trackable before its content is written, provided the schema, the runner,
  and CI all treat placeholder scenarios as expected-not-yet-executable rather than silently skipped or
  treated as passing.

---

## 9. Implementation-specific tests

Use canonical conformance for cross-language observable semantics, Pi-visible behavior, serialized contract shape, and deterministic compatibility cases.

Use implementation-specific tests for internal data structures, Tokio/asyncio mechanics, language-specific error plumbing, provider wire-parser fragmentation, memory ownership, type-level guarantees, performance details, and defensive branches that do not define shared semantics.

---

## 10. Pull request strategy

Prefer short-lived branches and trunk-based development. Do not maintain long-lived `python-dev` and `rust-dev` branches.

Recommended branch shapes:

```text
feat/pi-agent-turn-order
feat/python-phase4-tools
feat/rust-phase4-tools
fix/conformance-terminate
```

### 10.1 Semantic change PR

Where practical, one PR should make a semantic change atomic across:

```text
parity manifest
spec
conformance
Python
Rust
```

### 10.2 Python-leading split PR

When Python leads, two PRs are acceptable:

```text
PR 1
    parity manifest
    spec
    conformance
    Python implementation

PR 2
    Rust implementation against the same manifest/spec/conformance
```

The Rust PR should reference the same manifest IDs and canonical scenarios.

### 10.3 Implementation-only PR

A language-specific implementation-only change must not alter observable semantics. If it does, it must be reclassified as a semantic change and update the shared contract artifacts.

---

## 11. PR classification

PR templates should distinguish at least:

```text
[ ] implementation only
[ ] Pi parity correction
[ ] spec change
[ ] conformance change
[ ] intentional divergence
[ ] deferred parity update
```

For semantic changes, record:

```text
Pi source:
Parity manifest ID:
Spec section:
Conformance scenario(s):
Python status:
Rust status:
```

**OPEN ITEM — no stated required-reviewer rule for shared-contract changes.** This section defines PR
*shape*, not who must approve one. Nothing here requires a change under `conformance/**`, `spec/**`, or
`pi-parity-manifest.yaml` to be reviewed by an owner on both the Python and Rust side before merge — the
standard safeguard against one side unilaterally reinterpreting the shared contract in a polyglot
monorepo. Needs a named owner/policy decision (e.g. a CODEOWNERS entry mapping those paths to both
teams), not an invented rule.

---

## 12. Parallel coding agents and Git worktrees

When Codex, Claude Code, or multiple developers work concurrently, prefer separate Git worktrees rather than sharing one mutable checkout.

Example:

```text
minion-agent/                   main / review
minion-agent-contract-work/     spec + conformance
minion-agent-python-work/       Python implementation
minion-agent-rust-work/         Rust implementation
```

Example commands:

```bash
git worktree add ../minion-agent-contract-work feat/phase3-contract
git worktree add ../minion-agent-python-work feat/python-phase3
git worktree add ../minion-agent-rust-work feat/rust-phase3
```

Shared semantic files should be merged to `main` early so both implementation worktrees consume the same contract.

---

## 13. CI gates

Recommended CI decomposition:

```text
contract
    schema validation
    parity-manifest validation
    conformance fixture validation

python
    unit tests
    property tests
    Python conformance runner

rust
    unit tests
    property tests
    Rust conformance runner

cross-language
    verify both runners consume the same canonical cases
    compare canonical serialized outputs where appropriate
```

Changes under `minion-agent/conformance/**`, `minion-agent-docs/spec/**`, or `minion-agent/pi-parity-manifest.yaml` require both Python and Rust semantic gates because the shared contract changed.

**Provider wire-fixture verification is never a CI gate.** Real-provider wire fixtures (recorded,
sanitized captures from real providers) are covered separately by the real-providers design amendment's
testing philosophy: pure codec tests and replayed sanitized fixtures run in ordinary CI; live,
credentialed verification against a real provider is manual, non-gating, and used only to refresh
fixtures or detect provider drift. No CI job in the decomposition above holds live provider credentials
or makes live provider calls.

---

## 14. Compatibility status

Generate compatibility status from machine-readable sources rather than maintaining a hand-written matrix.

Inputs should come from:

```text
pi-parity-manifest.yaml
+
conformance runner results
```

---

## 15. Pi drift workflow

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
9. freeze the new baseline
```

---

## 16. Project invariants

1. **One semantic contract.**
2. **One canonical conformance suite.**
3. **One canonical parity manifest.**
4. **Python and Rust are first-class implementations.**
5. **Python may lead implementation but is never the behavioral oracle.**
6. **Rust must not blindly copy Python semantics.**
7. **Pi-derived semantic questions go back to Pi/spec/conformance.**
8. **Cross-language observable discoveries are promoted into manifest/spec/conformance.**
9. **Conformance stays slightly ahead of implementation, not many phases ahead.**
10. **A phase freezes only when its applicable contract and implementation gates are satisfied.**
11. **Implementation-only changes may not silently change observable behavior.**
12. **Later Pi revisions are handled through explicit drift audits.**

---

## 17. Working summary

```text
Pi audit
    ↓
parity manifest
    ↓
spec
    ↓
conformance
    ↓
┌───────────────┐
│ implementation│
│ Python + Rust │
└───────┬───────┘
        ↓
both applicable runners green
        ↓
phase freeze
```

Python can reach each implementation stage first.

**The contract must reach it first.**
