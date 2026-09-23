# WP-12.E1 raw-directory/probe independent contract review

**Mode:** independent Rust-side contract review only. No Python or Rust implementation was
performed or authorized. WP-13.1 Lane E and Layer 14 were not touched.

## Exact target

```text
coordination issue:  EGAILab/minion-agent#53
status:              CONTRACT_CONVERGENCE
next owner:          Codex
docs PR:             EGAILab/minion-agent-docs#147
docs head:           0c18555d324bd6ee44d98bc6dba70ca5ed44c736
docs base:           master @ 0bbd737fab8c1360995f4efff2b41c1c5531a9c3
code baseline:       main @ 92aa4be168dc82111832467922089206e858a9c4
pinned Pi:           b7bb00b936dbe21b8e160b3e89efdec361846699
governance source:   EGAILab/minion-agent#48 issuecomment-5771291305
artifact:            spec/execution.md section 11
scope:               list_dir_raw, probe_dir_entry, DirEntryProbe only
```

The issue-recorded docs SHA matched the open, Ready-for-Review, mergeable PR head and was
remote-reachable. The handoff carried valid owner governance and was not derived from quarantined
work. Existing Layer-12 operations were inspected only to verify additive consistency; their
certified semantics were not reopened.

## Result

```text
WP-12.E1 CONTRACT:  REJECTED
IMPLEMENTATION:     NOT AUTHORIZED
```

## Independently confirmed foundation

The selected architecture is coherent and faithful to the owner decision:

- `list_dir_raw` exposes raw provider-order names without per-entry classification;
- Layer 13 can sort before any probe;
- `probe_dir_entry` is one caller-controlled, symlink-following per-entry operation;
- the `[z_slow, a_ok]`, limit-one witness structurally avoids probing `z_slow`;
- existing `list_dir`, `file_info`, `FileInfo`, and `FileKind` remain behaviorally unchanged;
- the new probe vocabulary can represent ordinary files/directories, symlink-to-file/directory,
  and other accessible filesystem kinds without forcing a new existing `FileKind` variant.

These points do not need redesign. The blockers are contract integration and underspecified public
surface details.

## Blocking findings

### WP12E1-R001 — `CONTRACT_ASSURANCE_DEFECT`

The draft creates public `ctx.fs` operations while deliberately leaving the normative operation
inventory in section 3 unchanged until implementation. That produces two simultaneous contracts:

```text
section 3 authoritative inventory: no list_dir_raw / probe_dir_entry
section 11 draft:                  both operations are public FileSystem capabilities
```

An implementation pass must not be asked to edit shared normative semantics merely to discover
whether methods belong to the trait/protocol. "Existing semantics unchanged" requires preserving
the old operation rules, not preserving an obsolete exhaustive inventory.

Required correction: add the two signatures to section 3's `ctx.fs` inventory now, explicitly
marked additive and linked to section 11. Do not alter any existing line's semantics.

### WP12E1-R002 — `CONTRACT_ASSURANCE_DEFECT`

The coordination issue has `requirements: []`, and the candidate adds no parity-manifest row or
disposition for the owner-approved surface. Consequently there is no traceability chain from the
governance decision and pinned Pi source to normative rules, planned Python/Rust evidence, and a
disposition.

The operation is not itself a direct Pi harness method: it is a Minion architectural mapping that
exposes enough of the product `ls.ts` operations to reproduce Pi at Layer 13 while preserving the
existing harness-derived Layer-12 API. That subject needs an explicit requirement ID and coherent
manifest disposition; it cannot remain an untracked appendix.

Required correction: create the narrow manifest requirement row(s), state the architectural
mapping/disposition precisely, and list planned discriminating evidence. Update issue #53's
requirements list to the assigned ID(s). Do not modify existing Layer-12 row semantics.

### WP12E1-R003 — `CONTRACT_ASSURANCE_DEFECT`

`DirEntryProbe` is declared as `{name, path, kind}` but only `kind` is normatively defined. Two
independent implementations can observably disagree on:

- whether `name` is the basename of the input, the raw name from `list_dir_raw`, or provider
  canonical display text;
- whether `path` preserves the caller's lexical input, returns the provider-resolved absolute
  path, or canonicalizes through symlinks;
- whether those fields refer to the link itself or resolved target for symlink probes.

Layer 13 needs only the kind for its current rendering, but public extra fields still require one
meaning. Otherwise they should not be in the type.

Required correction: either remove `name`/`path` from `DirEntryProbe`, or define their exact
lexical/resolution semantics and add witnesses. In all cases specify that probing a symlink does
not silently replace the addressed entry identity with its target identity.

### WP12E1-R004 — `CONTRACT_ASSURANCE_DEFECT`

Cancellation is described by analogy to existing harness operations but is not classified as the
new architectural mapping it actually is:

- product `ls.ts`'s `LsOperations.readdir/stat` do not accept a signal; the surrounding tool's
  abort listener owns observable tool cancellation;
- the new uniform Layer-12 signatures accept `signal`;
- `list_dir_raw` adds a pre-abort check;
- `probe_dir_entry` accepts but ignores the signal, following harness `file_info` precedent.

Those choices may be reasonable, but "mirrors ops.readdir exactly" and "matching file_info"
source different Pi surfaces. The contract must make the ownership boundary explicit so Layer 13
R008 remains responsible for prompt tool-level cancellation and Rust is not forced to infer
whether the operations themselves race an in-flight provider call.

Required correction: classify both direct-operation cancellation rules as the approved Minion
Layer-12 mapping, state that neither operation provides native in-flight cancellation, and state
that Layer 13 owns any outer abort race/checkpoints required by its separately settled tool
contract. Add direct-operation witnesses for pre-aborted `list_dir_raw` and ignored-signal
`probe_dir_entry` behavior.

### WP12E1-R005 — `CONTRACT_ASSURANCE_DEFECT`

The predicted evidence matrix covers the lazy cap, FIFO/`other`, and broken-symlink error cases,
but not the rest of the new public contract. Missing discriminating evidence includes:

```text
list_dir_raw returns raw provider order and performs zero probes
plain file and plain directory classifications
symlink_to_file and symlink_to_directory classifications
symlink-to-other collapses to other as disclosed
provider not_supported behavior
name/path identity if those fields remain
the two direct-operation cancellation rules
existing list_dir/file_info behavior remains unchanged
```

Required correction: add planned canonical or explicit language witnesses for every new enum
variant and boundary above. Full implementation is not required in this contract pass, but the
evidence plan must be sufficient to certify the surface independently in both languages.

## Verdict

```text
shared WP-12.E1 contract: REJECTED
Python WP-12.E1:          NOT_IMPLEMENTED / NOT AUTHORIZED
Rust WP-12.E1:            NOT_IMPLEMENTED / BLOCKED
Layer-12 extension:       NOT CLOSED
WP-13.1 dependency:       NOT READY
Layer 14:                 NOT STARTED
```

Return only issue #53 to the shared-contract owner. Preserve existing Layer-12 semantics and keep
WP-13.1 Lane E isolated under issue #48.
