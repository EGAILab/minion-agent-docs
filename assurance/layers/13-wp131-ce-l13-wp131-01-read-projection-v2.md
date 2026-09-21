# CE-L13-WP131-01 — Lane A revision 2: `R005` only

Mode: §11.8 sub-checkpoint characterization, Lane A, `R005` revision only. **No Python or Rust
implementation performed or authorized. No Layer 12 change. Review this revision's `R005` section
only -- `R004` is frozen `CHECKPOINT-READY` (`minion-agent-docs#136`) and is not restated or
revised here; do not reopen it, `R003`/`R008`, or any other lane unless this revision presents
concrete contradictory evidence.**

Targeted remediation of the independent Lane A review (`minion-agent-docs#136` @
`a801a9208cc7d9ec40bbca918b121fb98b5107a4`, verdict: `R004 CHECKPOINT-READY`, `R005 CHANGES
REQUIRED`) against Lane A revision 1 (`minion-agent-docs#132` @
`0015cb0763e4eda5ff904d434f196cc80f4b522f`). Revision 1's `R004` section and its `R005` section's
correct parts (the Tier 3 candidate-search characterization itself) are preserved; only the
governance-scope error is corrected below.

## The confirmed correction

Revision 1 claimed Tiers 1-2 ("no resize needed" / "BMP conversion only, no resize needed") were
fully deterministic and `CHECKPOINT-READY`, with only Tier 3 (resize actually triggered) needing
owner governance. This was wrong: **Photon governs image decoding itself, before the fast-path
check that would decide whether resize is even needed.**

### Re-read in full, both `image-process.ts` and `image-resize-core.ts`, tracing the exact call
sequence for every format

```text
processImage(bytes, mimeType, {autoResizeImages: true})   <- default is true;
                                                               read.ts never overrides it
  1. normalizeImage(bytes, mimeType):
     - mimeType is png/jpeg/gif/webp (normalizeSupportedImageMimeType
       returns non-null): returns {bytes, mimeType} IMMEDIATELY --
       Photon/convertImageBytesToPng is NEVER called for these 4 formats
       at this step (image-process.ts:50-52, re-verified this revision).
     - mimeType is bmp (the only sniffed format not in that set):
       calls convertImageBytesToPng(bytes) -- Photon decode +
       EXIF-orientation + re-encode to PNG. FAILS (Photon unavailable,
       decode throws, or orientation throws) -> normalizeImage returns
       null -> processImage returns {ok:false, message:
       "[Image omitted: could not be converted to a supported inline
       image format.]"} -- this is BMP's OWN, EARLIER, independent
       Photon decode opportunity.
  2. If normalizeImage succeeded (immediately for the 4 formats, or via
     successful BMP conversion) AND autoResizeImages is true (default):
     resizeImage(normalized.bytes, normalized.mimeType, ...) is called
     UNCONDITIONALLY -- for EVERY format, regardless of whether the
     image's dimensions/size will turn out to need resizing at all.
  3. Inside resizeImage -> resizeImageInProcess (image-resize-core.ts:59-93,
     re-verified this revision): the VERY FIRST actions, before the
     fast-path dimension/size check, are:
       loadPhoton()
       photon.PhotonImage.new_from_byteslice(inputBytes)   <- A FRESH
                                                                decode,
                                                                independent
                                                                of step 1's
                                                                BMP decode
       applyExifOrientation(photon, rawImage, inputBytes)
       read oriented width/height
     ONLY THEN does the fast-path check run:
       if (width<=maxWidth && height<=maxHeight && base64Size<maxBytes)
         return {..., wasResized: false}   <- Tier 1's "success" case
     If Photon fails to load, the decode throws, or orientation throws
     ANYWHERE in this sequence -> the whole try block's catch fires ->
     resizeImageInProcess returns null -> processImage returns
     {ok:false, message: "[Image omitted: could not be resized below the
     inline image size limit.]"} -- REGARDLESS of whether the image's
     actual dimensions/size would ever have required resizing.
```

**BMP therefore has two independent, sequential Photon-decode opportunities to fail** (one inside
`convertImageBytesToPng`, a second, separate one inside `resizeImageInProcess` on the
already-converted PNG bytes), each surfacing a **different** message depending on which step
failed. **The four directly-supported formats have exactly one** Photon-decode opportunity (inside
`resizeImageInProcess` only), surfacing exactly one message on failure, **regardless of whether
that failure happens because decode/orientation itself failed or because no candidate ever got
under `maxBytes`** -- `processImage` cannot distinguish these two causes from `resizeImage`'s
`null` return alone; both produce the identical text.

**Discriminating witnesses (both confirmed as valid, unrebutted, by the reviewer):**

1. A file that passes the MIME sniffer and would already satisfy the dimension/byte fast-path
   condition, but that Photon's decoder rejects (or Photon is unavailable) -> pinned Pi returns
   the text-only `"...could not be resized..."` failure. An implementation that checks dimensions
   directly from file metadata and passes the original bytes through without ever attempting a
   decode would instead succeed -- an observable divergence that has nothing to do with resize
   logic at all.
2. A BMP that satisfies the shallow `isBmp()` header sniff but that Photon's decoder rejects ->
   pinned Pi returns the text-only `"...could not be converted..."` failure. A different
   decoder library may accept the same bytes and return a PNG image block.

## Corrected characterization

### Shared precondition (all formats, `autoResizeImages = true`, the default)

```text
Every sniffed-as-image file, of EVERY format, is passed through at least
one Photon decode+EXIF-orientation step before ANY tier's outcome is
decided -- there is no format or size/dimension combination that
bypasses Photon entirely under the default configuration. BMP passes
through TWO such steps (conversion, then the resize-path's own re-decode
of the converted bytes); the other four formats pass through exactly one
(inside the resize path only). Failure at any of these steps is
UNCONDITIONAL -- it does not depend on, and is not limited to, whether
resize would otherwise have been needed.
```

### Conditional guarantees (corrected wording, matching the reviewer's own proposed structure)

```text
Tier 1, CONDITIONAL on successful Photon decode/orientation for the
image's own bytes AND the fast-path dimension/byte-size condition being
met: the returned data/mimeType are the ORIGINAL bytes/mimeType,
unchanged -- deterministic, DIRECT_PI_PARITY, IF this precondition holds.

Tier 2, CONDITIONAL on successful BMP-to-PNG Photon conversion AND (per
Tier 1's own precondition, since the converted bytes are then re-fed
through the SAME resize path) successful re-decode AND the fast-path
condition being met: PNG mimeType and the source's own (orientation-
corrected) dimensions are required; byte-identical PNG encoding is not
required, subject to owner governance approving that pixel-equivalence
(not byte-identity) class.

Tier 3 (unchanged from Lane A revision 1): the Photon priority-ordered
multi-candidate resize/re-encode search, whose final mimeType,
dimensions, wasResized flag, success/failure boundary, and encoded bytes
are all Photon-candidate-search-outcome-dependent.
```

None of these three tiers' outcomes -- including Tier 1's "unchanged passthrough" -- is reachable
without first surviving the shared Photon decode/orientation precondition above. **No tier is
`CHECKPOINT-READY` as an unconditional claim**; each is `CHECKPOINT-READY` only as the
CONDITIONAL statement above, and the precondition itself (does this specific image successfully
decode via Photon at all) is exactly as owner-governance-dependent as Tier 3's candidate-search
outcome.

## Expanded owner-decision matrix (supersedes Lane A revision 1's Tier-3-only framing)

**`R005-A` -- adopt Photon (or a byte/decode-compatible equivalent) in Python and Rust.** Achieves
exact parity for the shared decode/orientation precondition AND Tier 3's candidate-search outcome,
since the same concrete decoder/encoder engine is used everywhere. Highest implementation cost
(WASM/FFI bindings in two additional languages, keeping the bound version in lockstep across all
three); highest fidelity.

**`R005-B` -- governed, disclosed divergence.** Accept and document that: (1) which specific
image files successfully decode at all (the shared precondition) may differ between Photon and
whatever decoder Python/Rust use -- some files Photon accepts, another decoder might reject, and
vice versa; (2) for files that DO decode successfully in both, Tier 1/2's format/dimensions are
still exactly reproducible (this part is genuinely deterministic, GIVEN successful decode); (3)
Tier 3's exact mimeType/dimensions/success-boundary/bytes remain divergent as already described in
revision 1. This narrows the "same as revision 1's Tier 3 governance" scope while being honest
that it now also covers the decode-success boundary shared by every tier.

**`R005-C` -- a different shared library, adopted identically by Python and Rust (not
necessarily Photon).** Diverges from Pi/Photon specifically (accepting that Minion's own
cross-language consistency is the goal, not exact Pi parity for this surface), but keeps Python
and Rust mutually consistent with each other. Feasibility (a single image-processing library with
mature, actively maintained Python and Rust bindings covering decode/EXIF/resize/re-encode for all
five sniffed formats) not yet assessed in this revision.

No option is selected. `R005`/`TOOL-025`'s image-handling scope cannot proceed to
contract-review-ready status until the owner picks one (or specifies another option this
characterization did not anticipate).

## Lane A status (this revision)

```text
R004:  CHECKPOINT-READY (frozen, unchanged, minion-agent-docs#136)
R005:  OWNER_DECISION_REQUIRED (shared decode/orientation precondition +
       Tier 3 candidate-search outcome, both -- not merely Tier 3 alone)
```
