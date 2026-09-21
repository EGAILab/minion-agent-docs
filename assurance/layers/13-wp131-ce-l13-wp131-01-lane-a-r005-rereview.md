# CE-L13-WP131-01 Lane A R005 independent re-review

**Mode:** convergence sub-checkpoint review only. No Python or Rust implementation was performed
or authorized. No Layer-12 or Layer-14 work was performed.

## Exact target

```text
coordination issue:  EGAILab/minion-agent#48
status:              CONTRACT_CONVERGENCE
next owner:          Codex
docs PR:             EGAILab/minion-agent-docs#132
docs head:           9f50d3b77c5a0de520d95541a24494af85eb4820
manifest PR:         EGAILab/minion-agent#52
manifest head:       cca8d8b325bb159be549e10c8321b3468f043e7f (frozen)
docs base:           master @ 0bbd737fab8c1360995f4efff2b41c1c5531a9c3
code base:           main @ 92aa4be168dc82111832467922089206e858a9c4
pinned Pi:           b7bb00b936dbe21b8e160b3e89efdec361846699
episode:             CE-L13-WP131-01
artifact:            assurance/layers/13-wp131-ce-l13-wp131-01-read-projection-v2.md
scope:               R005 revision only
prior lane review:   minion-agent-docs#136 @
                     a801a9208cc7d9ec40bbca918b121fb98b5107a4
```

The issue-recorded heads matched the open remote PR heads and were remote-reachable. The issue
carried a valid owner process decision for the lane review. Shared normative spec and manifest
files remained frozen as claimed. The candidate was not derived from quarantined work.

The review independently re-read pinned Pi's `image-process.ts`, `image-resize-core.ts`,
`image-resize.ts`, `image-convert.ts`, `exif-orientation.ts`, `mime.ts`, and `read.ts`. R003,
R004, R008, and all other lanes remained out of scope.

## Result

```text
L13-WP131-R005:       OWNER_DECISION_READY
checkpoint agreement:NOT YET — governance choice remains open
implementation:      NOT AUTHORIZED
```

## Independent verification

The revised call sequence is accurate:

1. `normalizeImage` returns original bytes directly for PNG/JPEG/GIF/WebP, but calls
   Photon-backed `convertImageBytesToPng` for BMP.
2. With default `autoResizeImages=true`, every successfully normalized format is then passed to
   `resizeImage` unconditionally.
3. `resizeImageInProcess` loads Photon, decodes the bytes, applies the supported EXIF orientation,
   and reads oriented dimensions before evaluating the no-resize fast path.
4. A failure before or during that precondition returns `null`, and `processImage` exposes the
   same text-only resize-failure result used when no encoding candidate fits.
5. BMP therefore has two sequential Photon-dependent stages with distinguishable failure text:
   conversion failure first, then resize-path decode/search failure. Other sniffed formats have
   the resize-path stage only under the default configuration.

The corrected tier statements are properly conditional rather than unconditional:

- Tier 1 guarantees original bytes/MIME only after successful Photon decode/orientation and
  satisfaction of the fast-path limits.
- Tier 2 guarantees PNG/logical output only after successful BMP conversion, successful re-decode,
  and fast-path entry; byte-identical PNG encoding is a separate governance choice.
- Tier 3 retains the accurately characterized Photon-specific ordered candidate search, whose
  encoder sizes influence MIME, dimensions, data, and success/failure.

The matrix is sufficiently complete and neutral for owner governance:

- **R005-A:** use Photon or a genuinely byte/decode-compatible engine and version strategy for
  maximum Pi fidelity;
- **R005-B:** explicitly approve decoder-acceptance, encoding, and Tier-3 observable differences;
- **R005-C:** choose one shared non-Photon Minion engine for Python/Rust consistency and explicitly
  accept divergence from Pi.

Each option states its parity consequence. No option is silently selected. Feasibility and exact
version/binding evidence remain implementation/checkpoint consequences of whichever option the
owner chooses, not missing characterization that prevents the owner from choosing.

The artifact correctly scopes its universal Photon-precondition statement to
`autoResizeImages=true`, the default used by `read`; disabling auto-resize remains a distinct
configuration path and does not contradict the characterization.

## Contract-quality answers

```text
Pinned call sequence accurate?                         YES
Tier guarantees correctly conditional?                YES
Photon-dependent success boundary covers Tiers 1–3?  YES
BMP's two distinct failure stages accounted for?      YES
Options complete enough for owner decision?           YES
Any option selected by the artifact?                  NO
Normative spec/manifest prematurely changed?          NO
Layer 12 reopened?                                     NO
Frozen findings contradicted?                          NO
```

## Verdict and next action

```text
R005:                     OWNER_DECISION_READY
Lane A:                   waiting for owner governance on R005
Implementation authorized:NO
Python WP-13.1:           NOT_IMPLEMENTED / NOT AUTHORIZED
Rust WP-13.1:             NOT_IMPLEMENTED / BLOCKED
Layer 13 cross-language:  NOT CLOSED
Layer 14:                 NOT STARTED
```

Request the owner's explicit choice among R005-A/R005-B/R005-C (or an explicitly scoped
alternative) and record the exact governance source. Do not infer a choice from a recommendation,
silence, or this approval. After the owner decision, Lane A may be converted into a proposed
implementation checkpoint consistent with that decision; implementation is not authorized by
this review itself.
