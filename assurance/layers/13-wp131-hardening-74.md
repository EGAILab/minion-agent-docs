# WP-13.1 post-closure assurance hardening (`minion-agent#74`)

Mode: shared canonical-evidence candidate (Claude, shared/Python owner), for independent exact-SHA review by Codex. It hardens evidence only. WP-13.1 semantics are unchanged, and changing them is not authorized.

## Authority

- **Scope and constraints.** Owner closure decision `minion-agent#48` comment `5870661040`, section 8:
  - a post-closure follow-up, not a WP-13.1 closure gate;
  - no semantic change;
  - item D is characterized first;
  - no fabricated image-output result.
- **Governance source for executing it.**

  ```text
  GOVERNANCE_SOURCE
      standing_delegation: https://github.com/EGAILab/minion-agent/issues/75
      delegated_decision: this record and the minion-agent#74 coordination state
      scope: minion-agent#74 items A-E (canonical witnesses for existing TOOL-025 rules)
  ```

- **Origin of the gaps.** The independent Rust WP-13.1 review (`minion-agent#72` comment `5853528408`, RW-F001/RW-F002 and mutants M13/M14/M19): the WP-13.1 canonical tree had no scenario that discriminates these five existing rules.
- **Baselines.** Pinned Pi `b7bb00b9`; code `main` `32fe82d2`; docs `master` `ed72c96f`.

## Evidence method

All evidence is in `assurance/layers/data/13-wp131-hardening-74/`.

1. **Corpus.**
   - `harness/make_corpus.py` builds the fixtures deterministically, with the standard library only (`struct` + `zlib`, fixed LCG seeds, no image library).
   - The only external input is the committed R005-A fixture `png_small_rgb.png` (sha256 `dd2696b1…`).
   - `corpus.sha256` records every file, and two independent regenerations were byte-identical.
2. **Authority.** `harness/run_authority.sh` runs in a disposable `node:22.15.1-alpine` container and checks:
   - Node `v22.15.1` / V8 `12.4.254.21-node.24`;
   - the Pi checkout is exactly `b7bb00b9` with no local changes;
   - Pi's image utilities against the R005-A `pi_utils.sha256`;
   - `truncate.ts` against its pinned hash;
   - photon-node 0.3.4 via `npm pack` against the SRI recorded in pinned Pi's `package-lock.json`;
   - the WASM against sha256 `10468181…3615c`;
   - the corpus is regenerated and required to match `corpus.sha256`.

   It then runs:
   - pinned Pi's `processImage` over the image files (`results/authority.json`, the same `run_authority.mjs` as R005-A);
   - pinned Pi's `read.ts` text branch (`read_text.mjs`, verbatim apart from I/O) over the APNG, after asserting that Pi's sniff returns `null` (`results/text_authority.json`).
3. **Scenarios.** `harness/gen_scenarios.py` writes the five canonical documents only from those two authority files. It hash-checks every fixture it copies into `conformance/agent/fixtures/h74-wp131-hardening/`.

## Items

| Item | Rule (existing) | Discriminating fixture and pinned-Pi result |
|---|---|---|
| A | The conversion hint names the **final** MIME after resize (`image-process.ts` `conversionHint(from, resized.mimeType)`) | `bmp1_noise_2100x2100.bmp`, 1-bit noise, 554,462 bytes. Photon's Lanczos resize makes high-entropy grayscale whose 2000x2000 PNG candidate (16,003,288 bytes) exceeds the ceiling. The result is `image/jpeg`, 2,724,365 bytes, with `[Image converted from image/bmp to image/jpeg.]` |
| B | The scale hint is ECMAScript `toFixed(2)` of the exact binary64 value | `png_rgb_{2150,2650,3050}x4.png`. Each W/2000 is a decimal half-cent tie whose double lies below the tie, giving `1.07`, `1.32`, `1.52`. Rounding binary64(scale*100) would give `1.08`, `1.33`, `1.53` |
| C | The **first** candidate whose base64 length is strictly below the ceiling wins, in the order PNG, JPEG 80, 85, 70, 55, 40 | `png1_noise_2100x2100.png`. The PNG candidate is too large, and JPEG 80 (2,723,660) and 85 (3,017,636) both fit, so the exact bytes are quality 80 |
| D | The no-resize fast path requires `ceil(n/3)*4` **strictly** below 4,718,592 | The same 8x5 PNG padded with trailing zeros. At 3,538,941 bytes the base64 length is 4,718,588: the input passes through unchanged, with no hint. At 3,538,942 bytes it is 4,718,592: the image is re-encoded at 8x5 (181 bytes) with `displayed at 8x5 … 1.00`. The owner's 3,538,944 behaves like 3,538,942 (authority run; not a separate scenario) |
| E | `acTL` before the first `IDAT` means the sniff returns `null` | `apng_actl_before_idat.png` is read through the text branch (Node utf-8 decoding, no image block). The same chunk after `IDAT` (`png_actl_after_idat.png`) is still `image/png` |

**Item D characterization.**
- The fast-path boundary is realizable with a real, Photon-decodable fixture, so it has a real canonical witness.
- Git stores the zero padding compressed; each padded file is about 3.4 MiB in a working tree.
- A different boundary, a **resize candidate** whose encoded size is exactly the ceiling (mutant M21 in the Rust review), still has no practical real fixture: it would need an encoder output of exactly 3,538,942–3,538,944 bytes. It remains the accepted non-blocking limit recorded at WP-13.1 closure, and is not re-characterized here.

## Results

- **New canonical documents** (`conformance/agent/`, requirement `TOOL-025`, witnesses appended to the manifest `TOOL-025` `tests:` list):
  - `builtin-read-image-bmp-conversion-hint-names-final-mime-after-jpeg-resize`
  - `builtin-read-image-scale-hint-to-fixed-rounds-exact-binary-value`
  - `builtin-read-image-first-eligible-jpeg-quality-wins`
  - `builtin-read-image-no-resize-fast-path-exact-base64-cutoff`
  - `builtin-read-animated-png-control-chunk-before-idat-is-not-an-image`
- **Python, unchanged production code:**
  - full suite 2090 passed, 11 skipped, 19 xfailed;
  - coverage 100.00%;
  - conformance 458 passed;
  - builtin + serialization + schema + manifest 318 passed.
- **Rust, unchanged production code:** in a throwaway copy of `main` with only the runner's pinned document count raised from 45 to 50, the canonical runner passes 50 documents / 163 cases against this tree. The count bump is Rust-owned (see Handoff).
- **`xtask conformance verify`:** PASS.
- **Negative controls** (Python binding, one mutant at a time, file restored after each):

  | Mutant | Killed by |
  |---|---|
  | A: hint names the intermediate PNG | A |
  | B: `toFixed` via binary64 `x*100` | B |
  | C: JPEG quality 85 before 80 | C (and A) |
  | D: fast path `<=` | D |
  | E: `acTL` ignored | E |

  No pre-existing canonical scenario caught any of the five. The gaps were real and are now closed.

## Handoff

- The Rust runner `crates/minion-agent/tests/builtin_tool_conformance.rs` asserts exactly 45 WP-13.1 documents. With this candidate it must assert 50.
- That one-line change is Rust-owned (Codex). It must land with, or before, this candidate so `main` never has a failing Rust gate.
- Requested from Codex:
  1. an independent exact-SHA review of the paired candidate;
  2. the runner count update as its own Rust PR.

No merge happens before approval.
