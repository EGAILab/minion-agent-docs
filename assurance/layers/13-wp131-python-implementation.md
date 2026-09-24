# WP-13.1 — Python implementation pass (`read`, `ls`)

Coordination: `minion-agent#48` (status `PYTHON_IMPLEMENTATION`). Authorization: the owner's
decision transcribed at `minion-agent#48` comment `5813022280` ("authorize merging #161 and WP-13.1
Python implementation"). Rust implementation and Layer 14 are NOT authorized and were not touched
(nothing under `minion-agent-rust/**` changed).

Baselines: code `minion-agent` main `cb8ed1c1` (manifest `TOOL-025`..`TOOL-028`, `TOOL-039`,
`TOOL-040`); docs `minion-agent-docs` master `f46051fb` (WP-13.1 contract `b1ed1530` + R005-A evidence
`#161`); pinned Pi `b7bb00b936dbe21b8e160b3e89efdec361846699`. The exact candidate SHAs are the
paired PR heads recorded on `minion-agent#48`.

Status wording: `Python WP-13.1: IMPLEMENTED, PENDING INDEPENDENT IMPLEMENTATION_REVIEW`;
`shared WP-13.1 contract: REPAIRED (IMPL-C001..C011), PENDING REVIEW WITH THE IMPLEMENTATION`;
`Rust WP-13.1: NOT_IMPLEMENTED / NOT AUTHORIZED`; `WP-13.1 cross-language: NOT CLOSED`.

## 1. Pi audit

Pinned files read in full (sha256 in `data/13-wp131-python-implementation/pi_sources.sha256`):
`core/tools/read.ts` (schema 21-25, execute 223-334), `core/tools/ls.ts`, `core/tools/truncate.ts`
(`truncateHead`, `formatSize`), `core/tools/path-utils.ts` (`resolveToCwd`, `pathExists`),
`utils/paths.ts` (`normalizePath`, `normalizeWindowsShellPath`, `resolvePath`), `utils/mime.ts`,
`utils/exif-orientation.ts`, `utils/image-process.ts`, `utils/image-convert.ts`,
`utils/image-resize.ts` (worker with in-process fallback, `formatDimensionNote`),
`utils/image-resize-core.ts`.

## 2. Findings

### Shared contract (`CONTRACT_ASSURANCE_DEFECT`, repaired in `spec/tools.md`)

| ID | Defect | Discriminating witness | Repair |
|---|---|---|---|
| IMPL-C001 | The non-vision note needs the requesting model's image support; Minion tools get no model context and no registry maps `ModelId` to it. The exact note text was not stated. | `builtin-read-image-success-includes-image-for-non-vision-model` (+ vision / unknown companions) | Optional model-capability provider evaluated per call; only `false` adds the note (Pi: `!model` -> none). `MINION_ARCHITECTURAL_MAPPING`. Exact text quoted. |
| IMPL-C002 | Step 5 named `file_info` for `read`; it is `lstat`-based (no symlink following, no readability), unlike Pi's `access(R_OK)`. | `...r010b-closed-vocabulary...`: `dangling-symlink-fails-the-access-check`, `read-permission-denied-reported-at-access-site`, `directory-is-directory` | Existence = `probe_dir_entry` (follows symlinks); directory -> "Cannot read <path>: is a directory"; read-time `permission_denied` reported at the access site. |
| IMPL-C003 | `<path>` undefined for `read` errors and the R002-A rejection; the first-line diagnostic cites the raw argument. | `...first-line-exceeds-byte-limit` (`raw-path-quoted`), `...malformed-file-url...` | `<path>` = `absolute_path(step-5 string)`; R002-A cites the step-4 input; diagnostic cites the raw `path`. |
| IMPL-C004 | The image pipeline was not normatively specified (sniff, processImage, resize core, EXIF, texts). | image scenarios; `tests/tools/builtin/test_byte_parsers.py`, `test_image.py` | New normative subsection from the pinned source + R005-A findings F1-F3. |
| IMPL-C005 | Text decoding unstated. | `builtin-read-text-decoding-matches-node-utf8` (BOM, CR, CRLF, 4 malformed sequences) | Node `Buffer.toString("utf-8")`, no newline translation. Python == Node on 25 malformed cases (probe). |
| IMPL-C006 | Number rendering in `read` notices unstated (stated for `ls` only). | `...fractional-and-negative-numeric-inputs` | ECMAScript `Number::toString` everywhere. |
| IMPL-C007 | "details ABSENT" vs a host result type that defaults `details` to `{}`. | all scenarios assert `details` keys | ABSENT = no `truncation`/`entry_limit_reached` keys (Layer 06 rule). |
| IMPL-C008 | Spec said a negative `limit` always yields an empty range; `slice` counts a negative end from the end. | `offset-None-limit--3` (lines 1-7, "[13 more lines ... offset=-2 ...]", from Pi under Node) | Prose corrected with Pi-computed examples. |
| IMPL-C009 | "data: base64 string (NOT raw bytes)" conflicts with Layer 02's byte-carrying `ImageBlock`. | image scenarios compare sha256/length of the bytes | The block carries the bytes whose base64 is Pi's `data`. |
| IMPL-C010 | Fractional offset + over-long first selected line: Pi throws Node's `TypeError` (`allLines[1.5]` is `undefined`). | `fractional-offset-undefined-line` (Node-produced text) | Pinned as that exact error text. |
| IMPL-C011 | Spec quoted the BMP hint as "bmp to png"; Pi emits "image/bmp to image/png". | `builtin-read-image-bmp-converts-and-resizes`; R005-A authority (4 occurrences) | Text corrected. |

### Lower layer (escalated, NOT changed here)

**L12 `PI_PARITY_DEFECT` (Python):** certified `LocalFileSystem.read_text_file` opens the file in text
mode without `newline=""`, so Python translates newlines: bytes `a\r\nb\rc\n` read as `'a\nb\nc\n'`,
while Node's `readFileSync(path, "utf8")` returns `"a\r\nb\rc\n"` (verified live). Reopening a
certified layer is an owner decision (`agent-workflow.md` §11.7); it is recorded for that decision.
WP-13.1 does not depend on it: `read` needs the bytes for image sniffing anyway and decodes them
itself (`IMPL-C005`).

### Implementation hazards (not contract defects; handled)

- The Windows SDK ships `icuuc.lib`/`icuin.Lib` for the system ICU on the default library path; a
  bare-name link of PyICU silently picks them. `scripts/pinned-icu/build.sh` links the pinned build by
  absolute path; `collation.py` verifies PyICU 2.16.2, the compiled ICU and the runtime-loaded ICU
  (`u_getVersion_78` from the loaded `icuuc78`) and fails closed.
- JS `/[a-z]/i` (no `u` flag) folds ASCII only (Python `re.I` also matches U+017F, U+212A); JS `.`
  stops at `\r`, U+2028, U+2029; JS `$` is end of input. All three are reproduced (`re.ASCII`, a
  negated class, `\Z`) and tested.
- `Math.round` is exact (`floor(x + 0.5)` misrounds 0.49999999999999994); `toFixed` rounds the exact
  binary value half away from zero, prints `-0` as `0.00` and keeps a sign on a negative that rounds
  to zero. All checked against Node.

## 3. Implementation (`minion-agent-python/src/minion_agent/tools/builtin/`)

`read.py`, `ls.py`, `paths.py` (TOOL-026 steps 1-4, R010-B vocabulary), `mime.py`, `image.py`,
`photon/` (vendored `photon_rs_bg.wasm`, sha256-checked on load, Apache-2.0 license, provenance),
`collation.py`, `truncate.py`, `_js.py` (ECMAScript number semantics), `_signal.py` (abort race),
`plugin.py` (`builtin-fs-query-tools`, injects `fs`/`tools`). Layer 12 gains only
`execution.file_url_to_path`, the certified strict conversion under a public name (R002-A step 4,
which the contract anticipated); no behavior change. New pinned dependencies: `wasmtime==49.0.0`,
`pyicu==2.16.2` (built from the lock-hashed sdist against the pinned ICU; `scripts/pinned-icu/`).

## 4. Evidence

- **Canonical:** 40 `builtin_tool` scenarios, `conformance/agent/builtin-*.yaml`, new schema
  `conformance/schema/builtin-tool-scenario.schema.json`, thin runner
  `tests/conformance/builtin_tool_runner.py` (fixture on disk + scripted provider responses over the
  REAL `LocalFileSystem`, real tools, real Layer 06 `execute_call`; it computes no tool output).
  They cover every WP-13.1 manifest witness (manifest `tests:` entries now name the files) plus
  `read_text_decoding_matches_node_utf8`, `read_image_auto_resize_disabled` and a
  post-Unicode-15.1 case-pair witness. Expected values come from pinned-Pi authorities only
  (`data/13-wp131-python-implementation/README.md`). The image fixtures are the committed R005-A
  corpus (every file <= 1 MiB).
- **Python tests** (`tests/tools/builtin/`): 20 R005-A core cases against pinned Pi's
  `resizeImageInProcess` results (candidate order, strict `<`, custom quality, shrink loop,
  exhaustion, zero-size trap); 52 EXIF/MIME byte cases (plus the 4100-byte sniff cutoff) against
  pinned Pi's own `mime.ts` / `exif-orientation.ts` under Node; JS-number tables from Node; abort race; fail-closed ICU
  loading; plugin mount/unmount.
- **Negative controls:** `data/13-wp131-python-implementation/mutants.log`, 23/23 single-point
  wrong implementations detected by the canonical suite: trimmed path, all `@` stripped, malformed
  URL falling through, Python `round` in resize, `%.2f`, smallest candidate, EXIF ignored, short
  conversion-hint names, note for unknown models, `lstat`-based access, permission at the read
  site, newline translation, Python slicing, details on a caller limit, resolved path in the sed
  hint, cap after probe, rounded limit, failed entry listed, not_supported as not-found, host
  lowercase keys, normalization off, code-point sort, unstable ties. The host-lowercase mutant was
  first MISSED; the post-Unicode-15.1 witness was added because of it.
- **Gates (fresh, candidate tree):** `pytest` 1987 passed, 4 skipped, 19 xfailed; coverage 100.00%
  (one `pragma: no cover` on Pi's unreachable "shrink made no progress" guard, with the proof in the
  comment); `ruff check` clean; `mypy --strict` clean (91 files); schema and manifest validation
  pass inside the suite.

## 5. Divergences and residual risk

- Disclosed architectural mappings: the model-capability provider (`IMPL-C001`); existence via
  `probe_dir_entry` and read-time readability (`IMPL-C002`); fresh Photon instance per operation
  (no observable effect, R005-A F4). Owner-decided divergences unchanged: `TOOL-039` (R010-B text),
  `TOOL-040` (pinned collation), `TOOL-027` (not adopted).
- Pre-aborted calls are answered by the Layer 06 pipeline before `execute` (as in Pi's agent
  loop); the tools' own start check is covered by direct Python tests.
- The three R005-A corpus files over 1 MiB (JPEG candidate path at read level) are exercised by the
  merged R005-A evidence, not by canonical scenarios; the candidate search itself is covered by the
  core-case tests.
- Evidence ran on Windows x86-64 (real symlinks available). ICU/PyICU provisioning on Linux is
  scripted but was not executed in this pass.

## 6. Review request (Codex, `IMPLEMENTATION_REVIEW`)

Independent exact-SHA review of the paired PR heads recorded on `minion-agent#48`: the IMPL-C001..
C011 contract repairs (are they faithful to pinned Pi and to the owner decisions?), the Python
implementation against the contract, the canonical scenario shape and runner (thin? portable to
Rust?), the negative controls, and whether the Layer 12 finding is correctly scoped out. Stop
condition: accept or reject with findings. Accepting does NOT authorize merge, Rust
implementation or Layer 14; after acceptance #48 returns to the owner for merge authorization.
