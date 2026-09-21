# CE-L13-WP131-01 Lane A independent review

**Mode:** convergence sub-checkpoint review only. No Python or Rust implementation was performed
or authorized. No Layer-12 or Layer-14 work was performed.

## Exact target

```text
coordination issue:  EGAILab/minion-agent#48
status:              CONTRACT_CONVERGENCE
next owner:          Codex
docs PR:             EGAILab/minion-agent-docs#132
docs head:           0015cb0763e4eda5ff904d434f196cc80f4b522f
manifest PR:         EGAILab/minion-agent#52
manifest head:       cca8d8b325bb159be549e10c8321b3468f043e7f (intentionally frozen)
docs base:           master @ 0bbd737fab8c1360995f4efff2b41c1c5531a9c3
code base:           main @ 92aa4be168dc82111832467922089206e858a9c4
pinned Pi:           b7bb00b936dbe21b8e160b3e89efdec361846699
episode:             CE-L13-WP131-01
lane artifact:       assurance/layers/13-wp131-ce-l13-wp131-01-read-projection.md
scope:               R004 and R005 only
```

The issue-recorded docs/manifest heads matched the open remote PR heads and were remote-reachable.
The issue carried an explicit owner process decision authorizing lane decomposition and this
isolated review. The candidate was not derived from quarantined work. Shared normative spec and
manifest files were unchanged as claimed.

The review independently re-read pinned Pi's `read.ts`, `truncate.ts`, `image-process.ts`,
`image-resize-core.ts`, `image-resize.ts`, `image-convert.ts`, `exif-orientation.ts`, and
`photon.ts`, then the Lane-A artifact. R003/R008 and other convergence lanes were not reopened.

## Result

```text
L13-WP131-R004:  CHECKPOINT-READY
L13-WP131-R005:  CHANGES REQUIRED
Lane A:          NOT YET AGREED
Implementation: NOT AUTHORIZED
```

## L13-WP131-R004 — CHECKPOINT-READY

The `formatSize` algorithm is quoted accurately and its threshold probes reproduce pinned Node,
including the discriminating `1048575 -> "1024.0KB"` result. The artifact correctly distinguishes
the formatted 50 KiB value (`50.0KB`) from the raw `head -c 51200` integer and supplies the four
model-visible continuation/diagnostic templates plus the closed two-value `processImage` failure
message set.

The previously accepted eleven-field `TruncationResult`, branch order, details-presence rules,
and outer image-result structure remain unchanged. No contradictory evidence was found.

Permanent implementation evidence must exercise the stated thresholds and literal strings, but
the semantic characterization is complete enough for independent implementation.

## L13-WP131-R005 — CHANGES REQUIRED

The deeper Photon candidate-search analysis is useful and the Tier-3 conclusion is correct:
encoder output size controls the winning MIME type, shrink count/dimensions, data, and potentially
success versus failure. Narrowing the owner decision to Tier 3 only is not defensible, however.

### Tier 1 still has a Photon-dependent success boundary

Pinned `resizeImageInProcess` does this before evaluating its fast-path condition:

```text
loadPhoton()
PhotonImage.new_from_byteslice(inputBytes)
applyExifOrientation(...)
read oriented width/height
then test dimensions/base64 size for the no-resize fast path
```

Therefore “no resize needed” does not mean Photon is bypassed. If Photon cannot load, its decoder
rejects a sniff-accepted image, or orientation processing throws, Pi returns `null`, which
`processImage` exposes as the text-only resize-failure result. A different implementation that
simply checks dimensions and passes the original bytes through can succeed on the same input.

Conditional on Pi reaching the fast path, the returned encoded bytes are indeed the original
bytes and are deterministic. But the branch's success/failure boundary remains Photon-specific,
so Tier 1 as a whole is not fully pinnable without the same library strategy or a governed
equivalence/divergence rule.

**Discriminating witness:** use a file that passes the MIME sniffer and the configured size/
dimension limits but that Photon's decoder rejects (or run with Photon unavailable). Pinned Pi
returns one text block containing the resize-failure message. A “Tier-1 passthrough before decode”
implementation returns text plus the original image block.

### Tier 2 also retains decoder/converter-dependent behavior

BMP normalization calls Photon before the later resize fast path. The successful case has a
deterministic output MIME (`image/png`) and intended dimensions, while encoded PNG bytes need not
be identical. But acceptance of sniff-valid BMP variants, decoded pixel/color behavior, and the
conversion success/failure boundary are still Photon-decoder/encoder-specific. Calling failures
an “environment/robustness question” does not make their different public result shape
non-observable.

**Discriminating witness:** a BMP satisfying the shallow `isBmp` header check but rejected by
Photon yields Pi's conversion-failure text-only result. Another decoder may accept it and return a
PNG image block. Both cannot satisfy one supposedly fully pinned Tier-2 outcome without a rule for
the accepted input/decoder domain.

### Required correction

Retain the useful conditional guarantees:

```text
Tier 1, on successful Photon decode/orientation and fast-path entry:
    original encoded bytes and MIME are returned unchanged.

Tier 2, on successful BMP conversion and no subsequent resize:
    PNG MIME and the defined logical image/dimensions are required;
    byte-identical PNG encoding is not required if governance permits that equivalence.

Tier 3:
    Photon candidate-search outcomes described by the artifact.
```

Then expand the owner-decision matrix to cover the Photon-dependent decode/orientation/conversion
success boundary shared by all default `autoResizeImages=true` tiers, plus Tier 3's additional
candidate-search outcomes. Options may still distinguish conditional output guarantees by tier,
but they cannot label Tiers 1–2 wholly checkpoint-ready while their observable failure boundary
is unresolved.

## Contract-quality answers

```text
R004 Pi mapping accurate?                                      YES
R004 exact enough for independent Rust implementation?        YES
R005 Photon search characterization accurate?                 YES
R005 Tier-3-only governance scope accurate?                    NO
Observable library dependence exists before Tier-3 resize?    YES
Normative spec/manifest prematurely changed?                  NO
Layer 12 reopened?                                             NO
Frozen R003/R008 contradicted?                                 NO
```

## Verdict

```text
Lane-A checkpoint review: REJECTED (R005 only)
R004:                     CHECKPOINT-READY
R005:                     CHANGES REQUIRED
Owner decision ready:     NO, until R005 covers the shared Photon-dependent success boundary
Implementation authorized:NO
Python WP-13.1:           NOT_IMPLEMENTED / NOT AUTHORIZED
Rust WP-13.1:             NOT_IMPLEMENTED / BLOCKED
Layer 13 cross-language:  NOT CLOSED
Layer 14:                 NOT STARTED
```

Return only Lane A's R005 characterization for revision. Preserve R004 as checkpoint-ready and do
not reopen R003/R008 or other lanes absent concrete contradictory evidence. Do not implement
Python or Rust WP-13.1, change Layer 12, or start Layer 14.
