# CE-L13-WP131-01 — Lane A: `read` result and image projection (`R004`/`R005`)

Mode: §11.8 sub-checkpoint characterization, Lane A only. **No Python or Rust implementation
performed or authorized. No Layer 12 change. Review this lane only -- do not reopen `R003`/`R008`
(frozen `CHECKPOINT-READY`, `minion-agent-docs#135`) or any other lane unless this lane presents
concrete contradictory evidence.**

Parent episode: `CE-L13-WP131-01` (`minion-agent#48`). This lane supersedes the combined checkpoint
(`minion-agent-docs#132` @ `f873217f35c142b0177bddb80e8934ddf2eac2d9`)'s `R004`/`R005` sections
only; that file's `R002`/`R003`/`R006`-`R010` sections are addressed in separate lanes (`R003`/
`R008` frozen; `R002`/`R006`/`R007`/`R010` in their own upcoming lane artifacts) and are not
restated or revised here.

---

## `R004` — complete model-visible formatting

### `formatSize` -- exact algorithm and verified thresholds

Quoted in full (`truncate.ts:58-68`):

```js
export function formatSize(bytes) {
  if (bytes < 1024) return `${bytes}B`;
  else if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  else return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}
```

No space between the number and unit; unit suffixes are exactly `B`/`KB`/`MB`. Directly executed
(this session):

```text
0        -> "0B"
1        -> "1B"
1023     -> "1023B"
1024     -> "1.0KB"
1025     -> "1.0KB"
51200    -> "50.0KB"     (DEFAULT_MAX_BYTES itself formats as "50.0KB")
1048575  -> "1024.0KB"   (!! one byte under 1 MiB still displays as "1024.0KB", not "1.0MB" --
                             1048575/1024 = 1023.999..., which .toFixed(1) rounds to "1024.0",
                             and the >= 1 MiB branch is not taken since 1048575 < 1048576)
1048576  -> "1.0MB"
1048577  -> "1.0MB"
4718592  -> "4.5MB"      (the image resize maxBytes threshold formats as "4.5MB")
```

The `1048575 -> "1024.0KB"` case is a genuine, reproducible display artifact of the exact
threshold-then-round algorithm, not a hypothetical edge case -- any conforming implementation must
reproduce this exact non-monotonic-looking formatting, not a "sensible" rounding that jumps to MB
one byte early.

### Complete literal template set (supersedes the prior checkpoint's placeholder text)

```text
first_line_exceeds_limit:
  "[Line {startLineDisplay} is {formatSize(firstLineBytes)}, exceeds
   {formatSize(DEFAULT_MAX_BYTES)} limit. Use bash: sed -n '{startLineDisplay}p'
   {path} | head -c {DEFAULT_MAX_BYTES}]"
  -- note the LAST placeholder is the raw integer DEFAULT_MAX_BYTES (51200),
  not a formatSize()-formatted string -- verified against read.ts:300
  (`head -c ${DEFAULT_MAX_BYTES}`, no formatSize call on that occurrence)

truncated, truncatedBy === "lines":
  "{content}\n\n[Showing lines {A}-{B} of {totalFileLines}. Use offset={next}
   to continue.]"

truncated, truncatedBy === "bytes":
  "{content}\n\n[Showing lines {A}-{B} of {totalFileLines} ({formatSize(DEFAULT_MAX_BYTES)}
   limit). Use offset={next} to continue.]"

userLimitedLines, more remains:
  "{content}\n\n[{remaining} more lines in file. Use offset={next} to continue.]"

image processing failure (processed.ok === false), exactly two literal
messages, verified against image-process.ts:81/89 (no others exist):
  conversion failure:  "[Image omitted: could not be converted to a supported
                         inline image format.]"
  resize failure:      "[Image omitted: could not be resized below the inline
                         image size limit.]"
  -- these are NOT a placeholder `processed.message` field; they are the
  literal, complete, closed 2-value set of everything processImage() can
  return as its own failure message.
```

**Status: `CHECKPOINT-READY`.**

---

## `R005` — image resize/re-encode observable equivalence

### Three-tier determinism analysis (re-read `image-resize-core.ts` and `image-convert.ts` in full,
not partially, for this lane)

Both the BMP-conversion path (`image-convert.ts:convertImageBytesToPng`) and the resize path
(`image-resize-core.ts:resizeImageInProcess`) are Photon (Rust/WASM image library, loaded via
`loadPhoton()`)-backed. This is deeper than the parent checkpoint characterized. Three
observably distinct tiers, not one uniform "resize is implementation-delegated" claim:

**Tier 1 -- no resize needed** (`image-resize-core.ts:83-93`, exact quoted condition):

```js
if (originalWidth <= opts.maxWidth && originalHeight <= opts.maxHeight
    && inputBase64Size < opts.maxBytes) {
  return { data: <original bytes, re-base64'd, UNCHANGED>, mimeType: <unchanged>,
           width: originalWidth, height: originalHeight, wasResized: false };
}
```

`inputBase64Size = Math.ceil(inputBytes.byteLength / 3) * 4` -- the exact base64-expansion
formula, itself pure arithmetic, deterministic. **Fully deterministic and exactly pinnable**:
given the same source bytes/dimensions, every conforming implementation produces byte-identical
output, because no re-encoding happens at all in this branch -- the original bytes pass through
unchanged. `DIRECT_PI_PARITY`, `CHECKPOINT-READY`.

**Tier 2 -- BMP-to-PNG conversion, no resize needed** (`image-convert.ts`, quoted in full above):
format (always PNG) and dimensions (unchanged) are deterministic; EXIF orientation correction is a
standardized, reproducible algorithm (any correct implementation produces the same *logical*
up/down orientation). The encoded PNG **bytes** are Photon-encoder-specific and not
byte-reproducible by a different PNG encoder (different compressors choose different filter/
compression-level tradeoffs for the "same" pixels, all still valid, decodable PNG). Success/
failure is near-deterministic (fails only if Photon itself is unavailable or the input is
malformed enough that decoding throws -- an environment/robustness question, not a search/
heuristic one).

**Tier 3 -- resize actually triggered** (`image-resize-core.ts:94-156`, the full iterative
algorithm, quoted): this is NOT a single deterministic transform. It is a **priority-ordered
multi-candidate search**:

```text
1. Compute target dimensions (aspect-preserving, Math.round -- deterministic
   arithmetic, exactly reproducible).
2. At the current dimensions, resize via Photon's Lanczos3 filter, then build
   CANDIDATES IN THIS FIXED ORDER: [PNG, JPEG@jpegQuality(default 80),
   JPEG@85, JPEG@70, JPEG@55, JPEG@40] (`Array.from(new Set([80,85,70,55,40]))`
   -- note 80 is tried BEFORE 85 despite being numerically smaller, since Set
   preserves insertion order and 80 is listed first).
3. Return the FIRST candidate (in that fixed order) whose encoded size is
   under maxBytes -- NOT the smallest, NOT the highest quality; whichever
   comes first in the fixed [PNG, 80, 85, 70, 55, 40] priority list that
   happens to fit.
4. If none fit at the current dimensions, shrink both dimensions by 25%
   (`Math.floor(current * 0.75)`, floored, each independently, not
   aspect-locked further after the initial target computation) and retry
   step 2 at the new (smaller) dimensions.
5. Repeat until either a candidate fits, or dimensions reach 1x1 with
   nothing fitting (-> resize failure, Tier-2-style text-only outcome).
```

**Every one of the following is genuinely implementation-dependent, not just the final encoded
bytes**, because WHICH candidate wins depends on Photon's own PNG/JPEG encoder's actual
compression efficiency at each step, which a different image library will not reproduce exactly:

```text
- final mimeType         (PNG vs JPEG depends on which candidate first fits)
- final width/height     (depends on how many 25%-shrink iterations were
                          needed before some candidate fit, which itself
                          depends on encoder compression efficiency)
- wasResized              (true whenever Tier 1's fast-path condition was not
                          met, but the DIMENSIONS reported alongside it depend
                          on the above)
- success vs. failure     (whether ANY candidate ever gets under maxBytes
                          before reaching 1x1 depends on encoder efficiency;
                          a less-efficient encoder could plausibly fail to
                          compress an image below threshold where Photon
                          succeeds, or vice versa)
- encoded data            (irreducibly encoder-specific)
```

This is qualitatively different from Tier 1/2: it is not "same logical image, different bytes" --
a different implementation can produce a **different observable content-block shape entirely**
(text-only failure vs. text+image success), a **different mimeType**, and **different reported
dimensions**, all from the identical source image and identical `maxWidth`/`maxHeight`/`maxBytes`/
`jpegQuality` parameters.

### Characterization conclusion (answers the parent challenge's Option A/B/C directly)

**Option A (exact Pi semantics) is not achievable without embedding Photon itself** (or a
byte-compatible drop-in: the same Lanczos3 implementation and the same PNG/JPEG encoders at the
same effective settings) in every target language -- there is no image-processing library
"equivalent" to Photon in the sense required for exact reproduction of this specific multi-
candidate search's outcome.

**Option B (a precise, mechanically-defined equivalence class) is fully achievable for Tiers 1 and
2**, and partially achievable for Tier 3:

```text
ALWAYS pinnable, any tier (equivalence class, not byte-identity):
  - content-block shape: [text] on failure, [text, image] on success --
    exact structural shape, DIRECT_PI_PARITY
  - text hint STRING TEMPLATES (verbatim, per Part R004 above and the
    conversion/dimension-note templates already fixed in the prior
    checkpoint) -- DIRECT_PI_PARITY
  - Tier 1: byte-identical output required (no re-encoding occurs at all)
  - Tier 2: PNG format + unchanged dimensions + orientation-corrected pixel
    content required; encoded byte identity NOT required (any correct PNG
    encoder producing the same logical pixels is equivalent)

NOT pinnable to a single equivalence class without further owner input,
Tier 3 only:
  - final mimeType (PNG vs JPEG choice)
  - final width/height (post-shrink-loop)
  - the success/failure boundary itself for images near the maxBytes
    threshold after the target-dimension resize
  - encoded bytes (accepted as non-pinnable even under Option B, same as
    Tier 2, PROVIDED the above three are pinned -- but they cannot be
    pinned without picking a specific encoder/algorithm, which is exactly
    the governance question)
```

**This is `R005: OWNER_DECISION_REQUIRED`, narrowed specifically to Tier 3** (the
resize-actually-triggered case) -- not the whole image contract, which is mostly
`CHECKPOINT-READY` as characterized above. The decision is: for images requiring resize, does
Minion (a) also adopt Photon (via WASM/FFI bindings) in Python and Rust to achieve exact Tier-3
parity, (b) accept a governed, disclosed divergence where Tier-3 outputs (mimeType, dimensions,
and the success/failure boundary itself) may differ from Pi's, documented as `intentional
divergence`, or (c) some other resolution (e.g. a different shared resize library adopted
identically by all three implementations, accepting divergence from Pi specifically rather than
divergence between Python/Rust). No option is selected here.

---

## Lane-A status

```text
R004:  CHECKPOINT-READY
R005:  Tiers 1-2 CHECKPOINT-READY; Tier 3 (resize-triggered case only)
       OWNER_DECISION_REQUIRED
```
