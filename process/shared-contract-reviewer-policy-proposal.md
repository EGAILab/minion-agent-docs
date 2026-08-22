# Minion Agent — Shared-Contract Reviewer Policy Proposal

**Status:** ADOPTED (2026-08-22). Applied to `process/implementation-conformance-workflow.md`,
replacing the prior open-item paragraph.
**Purpose:** Resolve the open reviewer-ownership item in `implementation-conformance-workflow.md`
without inventing a two-team approval requirement that a single-maintainer project cannot satisfy.

## Problem

Changes under the shared semantic contract can reinterpret behavior for both implementations:

```text
spec/**
conformance/**
/pi-parity-manifest.yaml
```

The current workflow defines PR shape and CI gates but intentionally leaves required reviewer
ownership unresolved.

## Proposed current-stage rule

```text
Shared-contract changes MUST receive explicit semantic-owner approval before merge.
```

For the current project, this may be the same human who owns the overall Minion Agent semantic
contract.

Where independent implementation maintainers exist:

```text
shared-contract changes SHOULD also receive review from the affected Python and Rust
implementation owners before merge.
```

The semantic-owner approval is mandatory. Separate Python/Rust reviewer approval becomes enforceable
when the project actually has independent maintainers.

## Future enforcement

When team structure supports it, promote this policy to CODEOWNERS / branch-protection rules.

Conceptually:

```text
/pi-parity-manifest.yaml    semantic owner + Python owner + Rust owner
conformance/**              semantic owner + Python owner + Rust owner
spec/**                     semantic owner + Python owner + Rust owner
```

Exact GitHub usernames/groups should be configured only when those ownership roles exist.

## Why this proposal

It prevents unilateral semantic reinterpretation now without imposing an impossible "two different
people must approve" rule on a project that may currently have one owner.

## If approved

Replace the open-item paragraph in `process/implementation-conformance-workflow.md` with the adopted
rule and, when applicable, add CODEOWNERS / branch-protection enforcement.
