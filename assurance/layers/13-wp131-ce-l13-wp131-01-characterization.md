# CE-L13-WP131-01 — convergence characterization checkpoint (proposed)

Mode: §11.8 characterization/checkpoint only. **No Python or Rust implementation performed or
authorized. No Layer 12 production change. This checkpoint requires independent Codex challenge
before any owner-governance request or implementation authorization.**

## Trigger

Findings `L13-WP131-R002`-`R010` survived a second independent review round
(`minion-agent-docs#134` @ `a4bf418ca60129847a622cc3c3620a3d70d32954`, rejecting docs candidate
`minion-agent-docs#132` @ `1dca05e822ef7c316867ab7b7e0067186e1dbe20` and manifest candidate
`minion-agent#52` @ `cca8d8b325bb159be549e10c8321b3468f043e7f`). Per `agent-workflow.md` §11.8,
this mandates `CONTRACT_CONVERGENCE` (episode `CE-L13-WP131-01`, recorded in `minion-agent#48`)
rather than a third untracked point-fix cycle.

This checkpoint does not select outcomes for `R006`/`R007` -- both require owner governance and
are presented as neutral decision matrices at the end. It characterizes `R002`-`R005`/`R008`-`R010`
completely enough for an independent reviewer to judge whether they are now checkpoint-ready.

## Method note

Every claim below is either (a) a direct quotation/citation of pinned-Pi source at
`b7bb00b936dbe21b8e160b3e89efdec361846699`, or (b) a directly executed Node/ICU probe run in this
session (commands and raw output are reproduced, not paraphrased). Nothing is asserted from
memory of the prior (rejected) drafts.

---

## Part 1 — `R002`/`R003`: exact JavaScript numeric/slice semantics for `read`

### `read`'s exact algorithm (`read.ts:277-322`, quoted)

```js
const startLine = offset ? Math.max(0, offset - 1) : 0;
const startLineDisplay = startLine + 1;
if (startLine >= allLines.length) {
  throw new Error(`Offset ${offset} is beyond end of file (${allLines.length} lines total)`);
}
let selectedContent, userLimitedLines;
if (limit !== undefined) {
  const endLine = Math.min(startLine + limit, allLines.length);
  selectedContent = allLines.slice(startLine, endLine).join("\n");
  userLimitedLines = endLine - startLine;
} else {
  selectedContent = allLines.slice(startLine).join("\n");
}
```

Note `offset ? ... : 0`: this is a truthiness test, not a presence test -- `offset === 0` and
`offset === undefined` and `offset === null` all take the `: 0` branch identically (same class of
truthiness pitfall this convergence's sibling episode, `CE-L13-SCOPE-01`, already found in
`getShellConfig`'s `customShellPath` check).

### Direct probe (executed this session; `allLines = ['L1','L2','L3','L4','L5']`)

```text
{}                          -> startLine=0,  content="L1,L2,L3,L4,L5"
{limit:-1}                  -> startLine=0,  content="L1,L2,L3,L4"      (slice(0,-1): drops LAST element)
{limit:0}                   -> startLine=0,  content=""                 userLimitedLines=0
{limit:1}                   -> startLine=0,  content="L1"
{limit:1.5}                 -> startLine=0,  content="L1"                userLimitedLines=1.5 (!)
{limit:-1.5}                -> startLine=0,  content="L1,L2,L3,L4"      (ToIntegerOrInfinity(-1.5)=-1 -> slice(0,4))
{offset:1}                  -> startLine=0,  content="L1,L2,L3,L4,L5"
{offset:0}                  -> startLine=0,  content="L1,L2,L3,L4,L5"   (truthiness: 0 -> same as omitted)
{offset:-1}                 -> startLine=0,  content="L1,L2,L3,L4,L5"   (Math.max(0,-2)=0)
{offset:1.5}                -> startLine=0.5, content="L1,L2,L3,L4,L5"  (slice(0.5) -> ToIntegerOrInfinity(0.5)=0 -> slice(0))
{offset:2.9}                -> startLine=1.9, content="L2,L3,L4,L5"     (slice(1.9) -> trunc to 1 -> slice(1))
{offset:-2}                 -> startLine=0,  content="L1,L2,L3,L4,L5"
{offset:3, limit:-1}        -> startLine=2,  content=""                 (slice(2,1): non-negative start>end -> empty)
{offset:3, limit:-100}      -> startLine=2,  content=""
{offset:1, limit:Infinity}  -> startLine=0,  content="L1,L2,L3,L4,L5"   userLimitedLines=5
{offset:Infinity}           -> error: "Offset Infinity is beyond end of file (5 lines total)"
```

Exact commands executed and raw output are in this checkpoint's companion evidence
(`assurance/layers/data/13-wp131-ce-l13-wp131-01/read-numeric-probe.txt`).

### Characterization (supersedes the rejected draft's simplified claim)

1. **JS numeric coercion, not integer semantics.** `offset`/`limit` undergo whatever arithmetic
   JS performs on the raw `number` -- `Math.max`, `Math.min`, and `Array.prototype.slice`'s own
   `ToIntegerOrInfinity` argument coercion (which **truncates toward zero**, not floors). A
   fractional `offset`/`limit` is not rejected and not rounded the way a naive reader might guess;
   it silently truncates at the point JS's slice machinery consumes it -- which may be a
   *different* point than where it is first computed (`startLine` itself can be held as a
   fraction, e.g. `0.5`, and only truncates when later passed to `.slice()`).
2. **Negative `limit`'s behavior depends on `startLine`.** When `startLine = 0` (the common case:
   `offset` omitted, `0`, or negative), a negative `limit` produces `slice(0, negativeNumber)`,
   which JS interprets as "up to N-from-the-end" -- i.e. it **drops elements from the end**, the
   opposite of an empty/error result. Once `startLine` is nonzero and `startLine + limit` is
   itself still non-negative, the same negative `limit` instead produces a `slice(start, smaller-
   or-equal-non-negative-end)`, which **is** empty. The two cases are not the same rule; a
   language-neutral implementation must reproduce the actual two-argument `slice` semantics, not a
   single "negative limit = X" rule.
3. **`userLimitedLines` can itself be fractional** (`endLine - startLine` where either operand was
   fractional), and is used verbatim in the continuation-notice arithmetic (`R004`'s "N more lines
   .. offset=" message) -- producing an observably fractional line count and a fractional next
   `offset` suggestion in that message, even though the actually-selected content has an integer
   number of lines. This is a real, reproducible Pi quirk, not a translation error.
4. **`NaN`/`Infinity` are not reachable via the tool's own JSON-schema boundary** (JSON has no
   `NaN`/`Infinity` literal), so while `Infinity` was probed above for completeness (and does
   reach the "beyond end of file" error, since `startLine` becomes `Infinity`), this is not an
   input a real tool call can carry -- noted for completeness, not part of the contractual input
   domain.

### `ls`'s exact algorithm and probe (`ls.ts:159-165`, quoted; `entries=['a','b','c','d','e']`)

```js
const effectiveLimit = limit ?? DEFAULT_LIMIT;   // DEFAULT_LIMIT = 500
for (const entry of entries) {
  if (results.length >= effectiveLimit) { entryLimitReached = true; break; }
  ...
  results.push(entry + suffix);
}
```

```text
limit=undefined -> 5 results, entryLimitReached=false
limit=0         -> 0 results, entryLimitReached=true, value=0
limit=-1        -> 0 results, entryLimitReached=true, value=-1
limit=-0.5      -> 0 results, entryLimitReached=true, value=-0.5
limit=1         -> 1 result,  entryLimitReached=true, value=1
limit=1.5       -> 2 results, entryLimitReached=true, value=1.5   (!! fractional, and NOT integer-truncated:
                                                                      results.length>=1.5 first true at length 2)
limit=2.9       -> 3 results, entryLimitReached=true, value=2.9
```

`limit ?? DEFAULT_LIMIT` is nullish coalescing (only `null`/`undefined` replaced), unlike
`offset`'s truthiness check above -- `limit: 0` is honored literally (0 results), it does **not**
fall back to 500. `entry_limit_reached`, when present, stores the **raw, possibly-fractional**
`effectiveLimit` value verbatim -- not `results.length`, not a rounded/integer count.

**Interaction with the empty-result branch (verified against `ls.ts:180-183`):** the function's
own zero-results short-circuit --

```js
if (results.length === 0) {
  resolve({ content: [{ type: "text", text: "(empty directory)" }], details: undefined });
  return;
}
```

-- runs **before** any `details` object (containing `entryLimitReached`/`truncation`) is
constructed. So for `limit=0`/`-1`/`-0.5` above, the loop-computed `entryLimitReached=true` value
is **discarded entirely** -- the actual tool result is `"(empty directory)"` with `details:
undefined`, indistinguishable from a genuinely empty directory. This is unchanged from, and
confirms, the prior draft's claim for the zero-results case specifically; what was missing was the
**non-integer** `entry_limit_reached` value for the *non-zero*-results cases above.

### Corrected contract text (supersedes `TOOL-025`/`TOOL-028`'s numeric-domain sections)

```text
offset, limit (read); limit (ls): Pi's own unconstrained JSON `number` schema.
A language-neutral implementation MUST reproduce, not merely "unconstrained
input accepted":
  - truthiness-vs-presence for `offset` (0/null/undefined all behave as
    "start at line 1"), nullish-coalescing for ls's `limit` (0 is honored
    literally, only null/undefined fall back to the default);
  - JS's two-argument Array.slice semantics EXACTLY, including negative
    end-index "distance from array end" interpretation, and
    ToIntegerOrInfinity truncation-toward-zero for fractional inputs at
    the point slice() consumes them (which may not be the same point the
    value was first computed, i.e. an intermediate fractional value can
    flow through unchanged before truncating);
  - that continuation-notice arithmetic (read) and entry_limit_reached
    (ls) may themselves be fractional, verbatim, not rounded;
  - that NaN/Infinity are outside the real input domain (unreachable via
    JSON) and need not be handled as first-class contractual inputs.
```

This is `DIRECT_PI_PARITY` -- reproducing Pi's actual arithmetic, not "equivalent" arithmetic in
another language's native numeric-slicing rules. A Python implementation must therefore implement
this specific coercion/slice algorithm directly (e.g. a small shared helper), not delegate to
Python's own native slice semantics, which differ (Python has no `ToIntegerOrInfinity`
truncation-toward-zero float-index behavior at all -- a native Python slice raises `TypeError` for
a float index).

**Status: `CHARACTERIZED_PENDING_CHECKPOINT_REVIEW`.**

---

## Part 2 — `R004`: complete text/image projection

### Complete `TruncationResult` (quoted in full, `truncate.ts:15-38` -- corrects the prior draft's
partial field list)

```ts
interface TruncationResult {
  content: string;
  truncated: boolean;
  truncatedBy: "lines" | "bytes" | null;
  totalLines: number;      // whole SELECTED-RANGE line count (pre-truncation)
  totalBytes: number;      // whole SELECTED-RANGE byte count (pre-truncation)
  outputLines: number;     // line count actually returned in `content`
  outputBytes: number;     // byte count actually returned in `content`
  lastLinePartial: boolean;     // tail-truncation only; always false for read (head truncation)
  firstLineExceedsLimit: boolean;
  maxLines: number;        // the ceiling actually applied (DEFAULT_MAX_LINES unless overridden)
  maxBytes: number;        // the ceiling actually applied (DEFAULT_MAX_BYTES unless overridden)
}
```

All eleven fields are part of the real, observable result whenever `details.truncation` is
present -- the prior draft's four-field subset (`truncated`/`truncated_by`/`total_lines`/
`first_line_exceeds_limit`) under-specified the contract; a conforming Rust implementation could
omit fields Python happens to expose (the review's exact objection).

### Complete outcome table (`read.ts:294-322`, all four branches quoted and traced)

```text
Branch                          | content_blocks[0].text                              | details.truncation
---------------------------------+-------------------------------------------------------+--------------------
firstLineExceedsLimit            | "[Line <n> is <size>, exceeds <limit> limit.          | present, all 11
                                  |  Use bash: sed -n '<n>p' <path> | head -c <limit>]"   | fields, content=""
truncated (lines)                | <content> + "\n\n[Showing lines A-B of <totalFileLines>| present, all 11
                                  |  . Use offset=<next> to continue.]"                   | fields
truncated (bytes)                | <content> + "\n\n[Showing lines A-B of <totalFileLines>| present, all 11
                                  |  (<limit> limit). Use offset=<next> to continue.]"    | fields
userLimitedLines, more remains   | <content> + "\n\n[<remaining> more lines in file.     | ABSENT
                                  |  Use offset=<next> to continue.]"                     |
none of the above                | <content> exactly, no notice                          | ABSENT
```

`totalFileLines` (whole-file line count, used ONLY in the two truncated-branch notice strings
above) remains distinct from `details.truncation.total_lines`/`.totalLines` (the selected-range
count) -- unchanged from the prior remediation, reconfirmed against source line-by-line here, not
merely re-asserted.

### Image projection -- `ImageContent`, verified against `pi-ai`'s actual type (`packages/ai/src/
types.ts:366-370`, quoted in full)

```ts
export interface ImageContent {
  type: "image";
  data: string; // base64 encoded image data
  mimeType: string; // e.g., "image/jpeg", "image/png"
}
```

Confirms `data` is base64 text, not raw bytes, at the type-authority level, not merely inferred
from a call site. `resizeImage`'s own return type (`image-resize-core.ts:10-18`) independently
confirms the same: `data: string // base64`. The non-resize path constructs it explicitly:
`Buffer.from(normalized.bytes).toString("base64")` (`image-process.ts:115`).

Complete branch table for a sniffed-as-image file (`read.ts:254-270`, `image-process.ts` full):

```text
Branch                              | content_blocks
--------------------------------------+---------------------------------------------------
processImage ok=false (convert/      | [0] text: "Read image file [<sniffed mime>]\n
resize failure)                      |     <processed.message>" (+ non-vision note if any)
                                      | -- NO [1], this is a text-only SUCCESS, not an error
processImage ok=true                 | [0] text: "Read image file [<final mime>]" +
                                      |     hints.join("\n") if any hints + non-vision note
                                      |     if any
                                      | [1] image: {data: base64, mimeType: <final mime>}
```

`hints` construction, exact strings (verified against `image-process.ts:67-118`):

```text
conversionHint(from, to):
  from undefined or from === to -> no hint
  else -> `[Image converted from ${from} to ${to}.]`
  -- from/to are FULL mime strings ("image/bmp"), not short names ("bmp") --
  corrects the prior draft's "[Image converted from bmp to png.]" (WRONG:
  the real string is "[Image converted from image/bmp to image/png.]")

formatDimensionNote(result) (image-resize-core.ts / image-resize.ts):
  result.wasResized === false -> no hint
  else -> `[Image: original ${ow}x${oh}, displayed at ${w}x${h}. Multiply
           coordinates by ${scale.toFixed(2)} to map to original image.]`
```

Sniff-detection exact constants (`mime.ts`, quoted): `IMAGE_TYPE_SNIFF_BYTES = 4100` (exactly
4100, not "~4100"); JPEG rejection is exactly `buffer[3] === 0xf7`; PNG validity requires
`isPng()` (16-byte IHDR-chunk check) **and** `!isAnimatedPng()` (an `acTL` chunk found before any
`IDAT` chunk marks it animated -> sniffs as not-an-image); GIF/WEBP/BMP via their own signature
checks. Closed 5-value sniff set: `image/jpeg`, `image/png` (non-animated only), `image/gif`,
`image/webp`, `image/bmp`; anything else sniffs as `null` (not an image at all, `read` falls
through to the plain-text branch and attempts UTF-8 decoding).

Resize defaults (`image-resize-core.ts:1-27`, quoted): `maxWidth: 2000, maxHeight: 2000,
maxBytes: 4.5 * 1024 * 1024` (4.5 MiB of **base64 payload**, not raw bytes), `jpegQuality: 80`.
EXIF orientation is applied before measuring/resizing (`applyExifOrientation`, imported at
`image-resize-core.ts:1`).

**Scope boundary (unchanged from the first remediation, reconfirmed):** the actual resize/re-encode
pixel algorithm runs through a WASM library (Photon) in a worker thread with an in-process
fallback; this is `MINION_EXTENSION`/implementation-delegated. Byte-identical resized pixel output
was never a reasonable parity target; the *observable metadata contract* above (closed sniff set,
base64 representation, exact hint strings, exact thresholds, failure-is-still-success) is.

**Status: `CHARACTERIZED_PENDING_CHECKPOINT_REVIEW`.**

---

## Part 3 — `read` cancellation: all three checkpoints (`R008`)

Full quoted structure (`read.ts:230-332`):

```js
return new Promise((resolve, reject) => {
  if (signal?.aborted) { reject(new Error("Operation aborted")); return; }   // CHECKPOINT 0
  let aborted = false;
  const onAbort = () => { aborted = true; reject(new Error("Operation aborted")); };
  signal?.addEventListener("abort", onAbort, { once: true });
  (async () => {
    try {
      const absolutePath = await resolveReadPathAsync(path, cwd);
      if (aborted) return;                                                   // CHECKPOINT 1
      await ops.access(absolutePath);
      if (aborted) return;                                                   // CHECKPOINT 2
      /* ... image OR text read/processing, unbounded duration ... */
      if (aborted) return;                                                   // CHECKPOINT 3 (line 325)
      signal?.removeEventListener("abort", onAbort);
      resolve({ content, details });
    } catch (error) {
      signal?.removeEventListener("abort", onAbort);
      if (!aborted) reject(error);
    }
  })();
});
```

**Corrected characterization (the prior draft named only checkpoints 1 and 2):**

- Checkpoint 0: an already-aborted signal at call start rejects synchronously before any work.
- The actual **rejection** happens via the `onAbort` **event listener callback**, which can fire
  at literally any wall-clock moment once registered -- it is not gated by these `if (aborted)`
  checks. The moment `abort` fires, the promise is REJECTED immediately by `onAbort` itself,
  regardless of what the async IIFE is doing at that instant.
- Checkpoints 1/2/3 are **not** the rejection mechanism -- they are defensive guards so the async
  code does not ALSO call `resolve()` after the promise has already settled (rejected) via
  `onAbort`. Calling `resolve()` on an already-rejected promise is a silent no-op in JS regardless,
  but the explicit checks avoid doing further unnecessary work (e.g., checkpoint 3 avoids
  publishing a fully-computed result after settlement).
- **Checkpoint 3 (line 325, previously omitted from the contract) is the material correction**: it
  occurs AFTER the entire image-processing-or-text-truncation pipeline has already run to
  completion. If `abort` fires (and `onAbort` rejects) at any point **before** this checkpoint is
  reached -- including after all the expensive work (image resize, full-file read) has already
  finished -- the tool's observable outcome is still `"Operation aborted"` rejection; the
  already-computed result is discarded, never published. The prior draft's claim ("an abort that
  fires after content has been fully read and processed does not retroactively discard that
  result") is **wrong** and is withdrawn.

**Discriminating witness:** start `read` on a large image requiring resize; fire abort
immediately after the resize work completes but before the promise settles (a timing window that
exists because `onAbort` and the async IIFE's own continuation are two independent execution
paths racing on the same signal). Correct behavior: the tool rejects `"Operation aborted"`; the
fully-processed image result is never returned. A conforming implementation must therefore treat
completion of the underlying I/O/processing as **necessary but not sufficient** for a successful
result -- final settlement is still abort-gated.

`ls`'s cancellation (`ls.ts:118-125`, reconfirmed, unchanged from the first remediation): same
`onAbort`-rejects-immediately mechanism; `ls` has no analog of `read`'s multi-checkpoint structure
since its own work (enumerate + per-entry classify) is a single interruptible span with no
distinct "read vs. process" phases.

**Status: `CHARACTERIZED_PENDING_CHECKPOINT_REVIEW`.**

---

## Part 4 — `R010`: filesystem error projection

### Pi's own error text is a genuine mix of hand-authored and raw-propagated -- not one uniform rule

**`ls.ts`** (`ls.ts:130-152`, quoted): three explicit hand-authored messages --

```text
!(await ops.exists(dirPath))         -> reject(new Error(`Path not found: ${dirPath}`))
!stat.isDirectory()                  -> reject(new Error(`Not a directory: ${dirPath}`))
readdir() throws (caught explicitly) -> reject(new Error(`Cannot read directory: ${e.message}`))
```

But `ops.stat(dirPath)` itself (the call between the `exists` check and the `isDirectory` check)
is **not** wrapped in its own `try`/`catch` at that call site -- if it throws (e.g. a
permission-denied stat, or a TOCTOU race where the path is removed between the `exists` check and
this call), that raw exception propagates to the function's own outer `catch`, which does a bare
`reject(e)` with **Node's raw error object and message** (e.g. `Error: EACCES: permission denied,
stat '<path>'`), not a hand-authored string. This is a **fourth**, previously undocumented,
distinguishable `ls` error shape.

**`read.ts`** (`read.ts:244-249`, quoted): **no hand-authored messages at all** for the
existence/readability check --

```js
const absolutePath = await resolveReadPathAsync(path, cwd);
if (aborted) return;
await ops.access(absolutePath);     // no wrapping try/catch here
if (aborted) return;
```

`ops.access`'s failure (missing file, permission denied, etc.) propagates as Node's **raw** `fs`
error (e.g. `Error: ENOENT: no such file or directory, access '<path>'`, `.code = "ENOENT"`)
straight to the outer `catch` -> `reject(error)`, unmodified. `read` therefore has **zero**
hand-authored existence/permission error text -- its entire "distinguishable error" claim rests on
whatever raw OS error text/code happens to surface, which is itself platform-dependent (Node's
own `ENOENT`/`EACCES`/`EISDIR` codes are POSIX-errno-derived and can differ in exact wording,
though not in `.code`, across platforms).

### Mapping onto Layer 12's `FsErrorCode` (already-certified, closed set)

```text
FsErrorCode: ABORTED, NOT_FOUND, PERMISSION_DENIED, NOT_DIRECTORY,
             IS_DIRECTORY, INVALID, NOT_SUPPORTED, UNKNOWN
```

| Scenario | Pi's own text | Classification |
|---|---|---|
| `read`: path missing | raw `ENOENT` (no custom text) | exactly representable -> `NOT_FOUND` |
| `read`: permission denied | raw `EACCES` (no custom text) | exactly representable -> `PERMISSION_DENIED` |
| `read`: path is a directory (access succeeds, later read fails) | raw `EISDIR`-class error from the subsequent `readFile` | exactly representable -> `IS_DIRECTORY`, but note this fires at a DIFFERENT step (during content read, not the access check) than `ls`'s equivalent |
| `ls`: path missing | hand-authored `"Path not found: <path>"` | exactly representable -> `NOT_FOUND`, but Pi's literal STRING is hand-authored, not raw-OS-derived |
| `ls`: not a directory | hand-authored `"Not a directory: <path>"` | exactly representable -> `NOT_DIRECTORY` |
| `ls`: `stat` fails after `exists` (race/permission) | raw, unwrapped exception | exactly representable -> `PERMISSION_DENIED`/`UNKNOWN` depending on cause, but Pi's text here is raw-OS, inconsistent with the two hand-authored messages immediately adjacent to it in the same function |
| `ls`: `readdir` fails | hand-authored `"Cannot read directory: <e.message>"` (embeds the raw underlying message inside a custom wrapper) | exactly representable -> `PERMISSION_DENIED`/`UNKNOWN`, text is a HYBRID (custom prefix + embedded raw suffix) |
| any: aborted mid-operation | `"Operation aborted"` (uniform across both tools) | exactly representable -> `ABORTED` |

### Characterization conclusion

Pi's own text is **not** a single, coherent, literally-reproducible contract -- it mixes
hand-authored strings, raw OS-errno text, and one hybrid (custom-prefix-plus-embedded-raw-suffix)
across just two tools, with at least one internally undocumented gap (`ls`'s unwrapped `stat`
call). Layer 12's `FsErrorCode` vocabulary is already a clean, closed, already-certified
classification that every one of Pi's scenarios maps onto without loss of the *distinguishing
information* (which broad category of failure occurred). Attempting literal text-string parity
with Pi would mean reproducing inconsistent, partially-platform-dependent raw OS message text,
which is not a coherent target and was never actually a single specification even within Pi's own
source.

**Proposed resolution (characterization only -- not a governance question, since Layer 12 already
established this exact pattern for the underlying seam):** Layer 13 defines its own closed,
`FsErrorCode`-driven set of distinguishable tool-level error variants (e.g. `not_found`,
`not_a_directory`, `permission_denied`, `enumeration_failed`, `aborted`), each carrying a
Layer-13-authored message template (not a literal reproduction of Pi's mixed raw/custom text) and
citing the addressed path. This is `MINION_ARCHITECTURAL_MAPPING`, consistent with -- not a new
divergence from -- Layer 12's own already-established precedent of defining a clean `Result`/
`FsError` system instead of reproducing every raw Node `fs` exception shape. Distinguishability
(the review's actual requirement) is fully preserved; literal Pi string reproduction, which was
never a coherent single target, is not attempted.

**Status: `CHARACTERIZED_PENDING_CHECKPOINT_REVIEW`** (proposed resolution above; independent
reviewer should confirm this is not, in fact, a third governance question).

---

## Part 5 — `R009`: manifest/contract coherence

The rejected candidate's `TOOL-025`/`TOOL-026`/`TOOL-028` rows were each marked `adopted` while
their own `rule:` text simultaneously described a disclosed divergence (`TOOL-026`'s malformed-
`file://` behavior), an implementation-delegated boundary (`TOOL-025`'s resize algorithm), or an
explicitly open, unresolved question (`TOOL-028`'s collation). The review is correct that a single
subject cannot coherently be `adopted` while also carrying an ungoverned divergence or an active
`PI_BEHAVIOR_UNCERTAIN`.

**Characterization, not yet applied to the manifest (the actual row edits are deferred to the
post-checkpoint remediation, once `R006`/`R007` are owner-decided, so as not to encode a guessed
outcome now):**

- `TOOL-025`: the resize-algorithm delegation is not an "adopted, but partially delegated" note --
  it should be split: the observable metadata contract (sniff set, base64, hints, thresholds,
  failure-as-success) is `adopted`; the exact resize pixel algorithm is out of contract scope
  entirely (not a manifest subject at all, the same way Layer 12 never manifested the exact
  bytes-on-disk of a written file).
- `TOOL-026`: the malformed-`file://` divergence needs its own explicit governance record before
  `TOOL-026` can be `adopted` as currently worded -- until decided, this row should read
  `CHARACTERIZED_PENDING_CHECKPOINT_REVIEW`, not `adopted`.
- `TOOL-028`: cannot be `adopted` while `R006` (collation) and `R007` (cap-timing/list_dir
  information loss) are both open owner decisions -- this row must remain explicitly pending
  until both are resolved; a guessed disposition would misrepresent the manifest's own
  authority.
- `TOOL-027`: unaffected by this convergence episode; its `intentional divergence` disposition
  and rule text (already correctly reflecting the owner's `NOT_ADOPTED_CORE` decision) stand.

**Status: `CHARACTERIZED_PENDING_CHECKPOINT_REVIEW`** for the characterization above; the manifest
file itself is intentionally NOT edited in this checkpoint pass, since `TOOL-026`/`TOOL-028`'s
final disposition depends on owner decisions not yet made (editing now would risk encoding a
guessed outcome, which this pass is explicitly not authorized to do).

---

## Part 6 — `R006` owner decision: `ls` collation semantics

### Factual characterization (source + direct probes, this session)

Pinned source (`ls.ts:154-155`, quoted): `entries.sort((a, b) => a.toLowerCase().localeCompare
(b.toLowerCase()))`. No locale argument is passed to `localeCompare` anywhere in this call chain --
this is a source-level fact independent of any single test environment.

Environment resolved in this session: `Node v22.15.1`, `ICU 76.1`, `platform win32`,
`new Intl.Collator().resolvedOptions().locale === "en-001"`.

Full probe corpus and sorted result (executed this session; corpus deliberately includes ASCII
case pairs, accented Latin, a case-folding edge case, numeric-looking names, punctuation, composed/
decomposed Unicode, and non-Latin names):

```text
input (enumeration order):
  apple, Apple, APPLE, banana, Banana, café, cafe, Café, straße, strasse,
  STRASSE, file1, file10, file2, a-b, a_b, a.b, "a b", e+combining-acute,
  é(composed), 日本語, にほんご, Straße, strasse2

sorted (this session's default locale):
  "a b", a_b, a-b, a.b, apple, Apple, APPLE, banana, Banana, cafe, café,
  Café, é, é, file1, file10, file2, strasse, STRASSE, straße, Straße,
  strasse2, にほんご, 日本語
```

Key direct findings:

1. **Stable-sort tie preservation, proven both directions.** Sorting `["apple","Apple","APPLE"]`
   (already in that order) and `["APPLE","Apple","apple"]` (reverse order) both return their INPUT
   order unchanged -- `localeCompare` on two strings that are identical after `.toLowerCase()`
   returns exactly `0`, and `Array.prototype.sort` has been a stable sort since ES2019, so
   case-tied names' relative order is **whatever order they were enumerated in**, which is itself
   filesystem/OS-dependent, not alphabetical.
2. **Composed vs. decomposed Unicode tie under default collation**:
   `'é'.toLowerCase().localeCompare('é'.toLowerCase())` returns `0` -- `localeCompare`
   performs canonical-equivalence-aware comparison, so NFC/NFD forms of the same character compare
   equal (and are therefore also subject to the stable-sort tie-preservation above).
3. **Genuine ICU collation rules apply, not codepoint order**: `straße` sorts adjacent to
   `strasse` under both the `en-US` and explicit `de` collators (`Intl.Collator('en-US').compare
   ('straße','strasse') === 1`, `Intl.Collator('de').compare(...) === 1`) -- U+00DF (ß) is treated
   as collation-equivalent-ish to "ss" by ICU's default collation rules, far from its raw codepoint
   position, which would sort it after every ASCII letter under a naive ordinal comparison.
4. **Environment-override attempt and its honest negative result**: setting `LANG=de_DE.UTF-8`,
   `LANG=ja_JP.UTF-8`, and `LC_ALL=fr_FR.UTF-8` via the shell before invoking Node, on this
   specific Windows/Node build, produced **no change** to the resolved default locale (`en-001` in
   all cases) -- Windows does not derive Node's `Intl` default from POSIX `LANG`/`LC_ALL`
   variables the way Linux/macOS builds typically do. This session could not mechanically
   demonstrate a *second*, concretely different resolved locale on different real hardware; the
   environment-dependency claim rests on the SOURCE-LEVEL fact (no explicit locale is ever pinned)
   plus Node/ICU's documented behavior (default locale is derived from OS-level locale
   configuration through a platform-specific mechanism), not on a locally-reproduced two-machine
   counterexample. This is reported honestly as a verified-by-source-reading, not
   verified-by-cross-machine-reproduction, claim.

### Decision options (neutral; no option is recommended over another here)

**`R006-A` -- preserve Pi's environment-sensitive semantics.** Minion's `ls` calls the equivalent
of `localeCompare` with no explicit locale in each target language (Python: locale-aware
comparison via the platform's own collation, e.g. ICU bindings or `locale.strxfrm`; Rust: an
ICU-backed crate with no pinned locale). Highest literal behavioral similarity to "whatever Pi
would do on this same machine." Weakest cross-language/cross-platform reproducibility: Python and
Rust's own default-locale-resolution mechanisms are not guaranteed to agree with each other or
with Node's, even given the same OS locale settings, since each language/runtime has its own ICU
integration and default-resolution algorithm. A conformance test asserting one fixed expected
order would be inherently machine-dependent and could not be a portable canonical scenario.

**`R006-B` -- deterministic Minion ordering (intentional divergence).** Define and pin an explicit,
language-neutral comparator -- e.g. primary key: Unicode-codepoint-ordinal comparison of each
name's simple case-folded (not locale-sensitive) form; tie-break: the exact original (byte- or
codepoint-) string, so no two distinct names ever tie. Fully cross-language reproducible (every
language has an ordinal/codepoint string comparison and a standard case-folding operation) and
fully testable (a single expected order is portable across every platform/environment). Observably
diverges from Pi on at least: non-ASCII collation-rule-driven orderings (the `straße`/`strasse`
case above would NOT be adjacent under ordinal comparison, since `ß` = U+00DF sorts by raw
codepoint value, nowhere near "s"/"ss"), and on any environment where Pi's own locale differs from
whatever "reference" behavior a canonical scenario might assume.

**`R006-C` -- pinned locale/runtime profile.** Choose and pin one specific collation locale/ruleset
(e.g. explicitly `Intl.Collator('en-001')`-equivalent in each language, or a fixed Unicode
Collation Algorithm (UCA) default-table configuration) as the certified behavior, documented as an
intentional, versioned dependency (mirroring `WP-13.4`'s eventual exact `fd`/`rg` version pin, but
for a collation library/table version instead of an external binary). Requires verifying that
Python and Rust each have a library capable of reproducing the SAME pinned collation rules/version
(e.g. both binding the same ICU version, or both implementing the same UCA table version) --
feasibility and operational burden (keeping three language runtimes' collation libraries in sync
on one pinned rule/version) not yet assessed in this pass; flagged as the open question this option
would need answered before being adopted.

No option is selected. `TOOL-028`/`ls` cannot proceed to contract-review-ready status until the
owner picks one (or specifies another option this characterization did not anticipate).

---

## Part 7 — `R007` owner decision: `ls` enumeration/cap semantics vs. current Layer-12 capability

### A. Pi's exact pipeline (`ls.ts:145-176`, already quoted in Part 1; restated as a sequence)

```text
1. entries = readdir(dirPath)                         -- ALL raw names, unfiltered, in
                                                           OS-enumeration order
2. entries.sort(...)                                    -- see R006
3. for each sorted entry, IN ORDER:
   3a. if results.length >= effectiveLimit: set
       entryLimitReached=true, BREAK -- the CURRENT
       entry is never examined at all once this fires
   3b. else: attempt file_info-equivalent stat() on
       this entry
       - stat() throws -> silently skip (continue to
         next entry; this entry counts against NEITHER
         results NOR the cap)
       - stat() succeeds -> push classified entry to
         results
4. loop ends (array exhausted OR step 3a fired)
```

The cap check (3a) is evaluated **before** attempting the entry that would trigger it -- so
`entryLimitReached=true` can be set **without Pi ever knowing** whether the entry that would have
come next (had the cap not fired) would itself have succeeded or failed classification. This is
the crux of the reviewer's claim.

### B. Minion Layer-12's exact pipeline (`filesystem.py:712-729`, `_list_dir_sync` at `:443-461`,
both quoted in full; already read in the first remediation, re-confirmed here)

```python
def _list_dir_sync(path, signal):
    infos = []
    with os.scandir(path) as entries:
        for entry in entries:
            if signal aborted: raise
            try:
                infos.append(_file_info_sync(entry.path))   # os.lstat-based
            except _UnsupportedFileType:
                continue                                      # skip, matches Pi's spirit
    return infos                                              # ALL survivors, no cap concept
```

`list_dir()` has **no limit/cap parameter or concept at all** -- it always enumerates the ENTIRE
directory and returns every entry that survived classification (skipping only
kind-unclassifiable entries, e.g. sockets/FIFOs/devices). There is no operation in the certified
`FileSystem` Protocol that exposes raw, pre-classification entry names, a partial/streamed
enumeration, or a per-entry classification-failure signal distinct from silent omission.

### C. Minimal discriminating witness (constructed and traced by hand against both pipelines above;
not merely asserted)

Directory with three raw entries in enumeration order: `e1` (classifies successfully), `e2`
(classifies successfully), `e3` (classification FAILS, e.g. permission-denied `lstat`).
`limit = 2`.

**Pi's exact trace:**

```text
iter e1: cap check 0>=2? no.  stat e1 ok.  results=[e1]
iter e2: cap check 1>=2? no.  stat e2 ok.  results=[e1,e2]
iter e3: cap check 2>=2? YES. entryLimitReached=true. BREAK.
         (e3's own classification outcome is NEVER EXAMINED by Pi)
```

Pi's observable result: `entries=[e1,e2]`, `entryLimitReached=true` (value `2`) -- the model is
told "there may be more; increase limit to see them."

**Minion `ctx.fs.list_dir()`-then-cap composition's exact trace:**

```text
list_dir() unconditionally enumerates ALL THREE raw entries (it has no
cap concept): e1 ok, e2 ok, e3 FAILS classification (silently skipped,
matching Pi's OWN skip-on-unsupported-kind spirit -- but Pi's ls.ts
never actually reached e3 to apply this skip itself, per the trace above)
  -> list_dir() returns survivors = [e1, e2]        (length 2)
Layer 13 then applies limit=2 to this ALREADY-COMPLETE survivor list:
  len(survivors) = 2, is 2 > limit(2)?  NO.
  -> entry_limit_reached = FALSE
```

**Result: `entryLimitReached` genuinely differs -- `true` (Pi) vs. `false` (Layer-12-composed) --
for the identical underlying directory and identical `limit`.** This is not a difference in which
entries are shown (both show `[e1,e2]`); it is a difference in the **truthfulness of the
"there may be more" signal itself**. Pi's signal is a conservative "iteration was cut short before
verifying what follows" flag, set the instant the cap is reached regardless of what (if anything)
comes after. Layer-12's full-enumeration-then-cap composition can only produce a **definitive**
signal computed after every raw entry's fate is already known -- collapsing Pi's "maybe more"
into a factual "there were/weren't more valid entries," which are not the same claim whenever a
raw entry beyond the cap boundary would itself have failed classification.

**This proves genuine information loss, not merely that the prior draft chose the wrong
algorithm**: no re-composition of `list_dir()`'s OWN output (which already reflects e3's fate)
can recover what Pi's signal actually means, because by the time Layer 13 receives ANY result from
`list_dir()`, e3 has unconditionally already been examined -- Pi's own defining property (the cap
can fire *without* examining the next entry) is structurally impossible to reconstruct from an
operation that always examines every entry as a precondition of returning at all.

### D. Falsification attempt: can existing certified operations be composed to reproduce Pi exactly?

The certified `FileSystem` Protocol's only relevant operations are `list_dir` (as characterized
above: full-scan, all-survivors-or-whole-call-error, no cap concept, no raw pre-classification
names) and `file_info` (single-path classification). Composing them --
e.g. "call some raw-name-listing operation, then call `file_info` one entry at a time until the
cap is reached" -- would require a raw-name-listing primitive that **does not exist** in the
certified surface; every path from "a directory path" to "a list of names" in the current Protocol
is `list_dir()` itself, which is already the full-scan operation under test. No composition of
`list_dir` with `file_info`, `resolve`, or any other certified operation can obtain UNCLASSIFIED
raw names, because none of them expose that intermediate state -- `list_dir` performs
enumeration-and-classification as one atomic, non-decomposable step from Layer 13's vantage point.

**The impossibility claim is confirmed, not merely asserted:** given the currently certified
Layer-12 `FileSystem` Protocol exactly as defined, Layer 13 cannot reproduce Pi's pre-stat cap
timing. This is a structural property of the certified interface, not an implementation gap in a
particular provider.

### Additive-capability options (characterization only; none implemented or selected here)

**`R007-a` -- accept the observable divergence, governed.** Record that `TOOL-028`'s
`entry_limit_reached` signal means "the Layer-12-visible survivor count exceeded the limit" (a
definitive claim), not Pi's "iteration was cut short" (a conservative claim), as an explicit,
owner-approved `intentional divergence`. No Layer 12 change. Lowest implementation cost; the
`WP-13.1` contract as already drafted (using `list_dir()` directly) already produces this behavior
without modification -- this option only requires a governance record, not new code, once decided.

**`R007-b` -- additive Layer-12 capability, smallest candidates:**

```text
(i)   list_dir_raw(path) -> Result[list[str], FsError]
      Raw entry NAMES in provider enumeration order, no classification
      attempted at all. Smallest possible addition; Layer 13 would then
      call file_info() itself, per-entry, in a loop mirroring Pi's own
      cap-before-stat structure exactly -- full reproduction possible.
      Existing list_dir()'s own behavior, callers, and EXEC requirements
      are UNCHANGED -- this is purely additive, not a modification of any
      already-certified operation.

(ii)  enumerate_dir(path) -> a lazy/streamed entry iterator
      Same information as (i) but streamed rather than collected eagerly;
      more implementation machinery (an async generator/iterator
      contract) for no additional information over (i) given ls's own
      synchronous-style cap-then-stop usage pattern -- likely more
      capability than the minimal need justifies.

(iii) list_dir_with_failures(path) -> Result[list[FileInfo | FailedEntry],
      FsError]
      A richer list_dir returning BOTH survivors and per-entry failure
      markers, still as one complete, uncapped enumeration. This does NOT
      solve the actual problem: it still requires examining EVERY entry
      (including e3, unconditionally) before returning, so it still
      cannot expose Pi's "the cap fired before e3 was ever touched"
      property -- ruled out as insufficient, not merely non-minimal.
```

`(i)` is the smallest candidate that actually closes the gap; `(ii)` is unnecessary machinery for
this specific need; `(iii)` does not solve the problem at all despite initial appeal. If this
option is chosen, the correct process framing is a **narrow, backward-compatible Layer-12
extension** (a new operation added to the Protocol; every existing certified operation, caller,
and `EXEC-*` requirement unchanged) requiring its own narrow revalidation on both languages -- NOT
a reopening or invalidation of Layer 12's existing historical certification. This pass does not
create, implement, or certify that extension; it only characterizes it as a candidate.

**Consequences summary (neutral, for owner decision):**

```text
                    R007-a (accept)      R007-b(i) (additive list_dir_raw)
Layer 12 change     none                 additive only, existing ops unchanged
Python impact       none beyond WP-13.1  new method + WP-13.1 consumes it
Rust impact         none beyond WP-13.1  new method + WP-13.1 consumes it
New evidence needed governance record    new operation's own conformance
                    only                 evidence + WP-13.1's consumption of it
Implementation cost lowest               moderate (new Layer-12 surface + revalidation)
Observable result   diverges from Pi     exact Pi parity achievable
```

No option is selected. `TOOL-028`/`ls` cannot proceed to contract-review-ready status until the
owner picks one.

---

## Convergence status

```text
episode:                   CE-L13-WP131-01
checkpoint_status:         PROPOSED FOR CHALLENGE
findings characterized:    R002, R003, R004, R005, R008, R009, R010
                            (status: CHARACTERIZED_PENDING_CHECKPOINT_REVIEW)
findings requiring owner
governance (NOT resolved
by this checkpoint):       R006 (ls collation), R007 (ls cap/enumeration
                            vs. current Layer-12 capability)
next_action:                independent Codex challenge of this exact
                            characterization
implementation_authorized: NO
layer_12_change:            NONE (R007-b, if chosen, would be a future,
                            separate, narrow additive work package -- not
                            performed, proposed, or authorized here)
```

This checkpoint does not itself close `R002`-`R005`/`R008`-`R010` -- that requires the independent
reviewer's own targeted confirmation, per `agent-workflow.md`'s own convergence discipline. It
proposes their characterization as complete and internally coherent; the reviewer may still find
gaps.
