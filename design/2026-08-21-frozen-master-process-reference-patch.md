# Proposed Frozen-Master Governance Reference

**Updated:** 2026-08-22  
**Status:** Governance-only patch proposal; not a semantic redesign.

This replaces the earlier 2026-08-21 proposal, which predates the assurance framework and referred
to an obsolete nested `docs/process/...` path.

Recommended insertion in `2026-08-20-minion-agent-design.md`, near the normative-authority /
development-cycle sections:

```markdown
### Implementation, conformance, and assurance governance

All Minion Agent implementations MUST follow
`process/implementation-conformance-workflow.md` in the companion
`minion-agent-docs` repository.

That process document governs how the shared Pi parity manifest, normative spec, canonical
conformance, Python implementation, Rust implementation, and assurance evidence are evolved
together. Python may lead implementation, but neither Python nor Rust is a behavioral oracle.

Pi at the adopted revision, the normative language-neutral spec, and applicable canonical
conformance remain the semantic authority defined by this design. The canonical machine-readable
Pi parity manifest lives at `/pi-parity-manifest.yaml` in the Minion Agent code monorepo.

For Pi-derived behavior, the project workflow is:

`Pi audit -> parity manifest -> spec -> conformance -> implementation -> implementation tests -> assurance audit -> remediation/risk registration -> layer certification -> phase freeze`

Affected implementation layers MUST be audited according to
`assurance/fidelity-assurance-method.md` before certification/freeze.

Assurance is an evidence and release-discipline layer. It MUST NOT redefine or override frozen
semantic behavior. Security, reliability, observability, performance, documentation, and other
production-quality findings may be corrected immediately when doing so is Pi-semantics-neutral.
A finding whose correction would change Pi-visible behavior MUST be explicitly dispositioned and
deferred to the post-parity hardening process unless the normal design/spec/conformance governance
path approves an intentional divergence.

New cross-language observable behavior discovered during implementation MUST be verified against
the adopted Pi source and promoted into the shared parity manifest/spec/conformance before another
implementation treats it as required behavior.

A phase MUST NOT freeze until its applicable semantic-contract, implementation, conformance, and
assurance gates are satisfied.

The process and assurance documents may evolve as engineering workflow improves, but neither may
redefine frozen semantic behavior. Any workflow or hardening change that would alter Minion-visible
semantics requires the normal design/spec/conformance governance path.
```

## Application rule

Because `2026-08-20-minion-agent-design.md` is already FROZEN, apply this only as an explicitly
reviewed governance-only edit (or incorporate it into the next master revision).

The change establishes a governance reference chain:

```text
Frozen master
    -> process/implementation-conformance-workflow.md
        -> assurance/fidelity-assurance-method.md
```

It does not change the frozen Pi-compatible semantic contract.
