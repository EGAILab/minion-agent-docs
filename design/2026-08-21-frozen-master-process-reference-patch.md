# Proposed Frozen-Master Process Reference

This is a governance reference patch, not a semantic redesign.

Recommended insertion in `2026-08-20-minion-agent-design.md`, near the normative-authority / development-cycle sections:

```markdown
### Implementation and conformance governance

All Minion Agent implementations MUST follow
`docs/process/implementation-conformance-workflow.md`.

That process document governs how the shared Pi parity manifest, normative spec, canonical
conformance, Python implementation, and Rust implementation are evolved together. Python may lead
implementation, but neither Python nor Rust is a behavioral oracle. Pi at the adopted revision,
the normative spec, and applicable canonical conformance remain the semantic authority defined by
this design.

For Pi-derived behavior, each implementation phase follows:

`Pi audit -> parity manifest -> spec -> conformance -> implementation -> applicable conformance green`

New cross-language observable behavior discovered during implementation MUST be promoted into the
shared parity manifest/spec/conformance before another implementation treats it as required
behavior. A phase MUST NOT freeze until its applicable semantic-contract and conformance gates are
satisfied.

The process document may evolve as engineering workflow improves, but it MUST NOT redefine or
override frozen semantic behavior. Any workflow change that would alter Minion-visible semantics
requires the normal design/spec/conformance governance path.
```

Because the current master is already FROZEN, apply this as an explicitly reviewed governance-only edit (or include it in the next master revision) rather than silently changing frozen semantic content.
