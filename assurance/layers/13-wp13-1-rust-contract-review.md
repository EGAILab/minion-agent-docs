# Layer 13 WP-13.1 independent Rust contract review

**Mode:** independent Rust-side contract review only. No Python or Rust implementation was
performed.

## Exact review target

```text
coordination issue:  EGAILab/minion-agent#48 (OPEN)
status:              CONTRACT_REVIEW
next owner:          Codex
code baseline:       92aa4be168dc82111832467922089206e858a9c4
docs PR:             EGAILab/minion-agent-docs#132
docs candidate:      46ac12c7919637cfa06b9a9836b3404962bb63c2
docs base:           master @ 0bbd737fab8c1360995f4efff2b41c1c5531a9c3
pinned Pi:           b7bb00b936dbe21b8e160b3e89efdec361846699
```

The issue state was valid, the exact candidate SHA was remote-reachable, PR #132 was Ready for
Review, open, unmerged, and mergeable, and its sole changed file was `spec/tools.md`. The approval
target did not move during review. Existing unrelated/untracked local files were not modified.

## Authority and sources audited

The review used the required order: pinned Pi, normative spec, manifest, applicable conformance,
certified Rust/Layer-12 architecture, scoping/assurance, and no Python implementation as a semantic
oracle.

Pinned Pi source inspected at the exact SHA:

- `packages/coding-agent/src/core/tools/read.ts`
- `packages/coding-agent/src/core/tools/ls.ts`
- `packages/coding-agent/src/core/tools/path-utils.ts`
- `packages/coding-agent/src/core/tools/truncate.ts`
- `packages/coding-agent/src/utils/paths.ts`
- `packages/coding-agent/src/utils/mime.ts`
- `packages/coding-agent/src/utils/image-process.ts`
- `packages/coding-agent/src/utils/image-resize.ts`
- `packages/agent/src/harness/env/nodejs.ts`
- relevant pinned tests in `packages/coding-agent/test/tools.test.ts`, `path-utils.test.ts`, and
  `paths.test.ts`

Project artifacts inspected:

- `spec/tools.md` at the candidate SHA
- `spec/execution.md` on the reviewed base
- `pi-parity-manifest.yaml` on code `origin/main`
- `assurance/layers/13-built-in-tools-scoping-v4.md`
- current certified Rust/Python Layer-12 filesystem surface as a structural check only

## Requirement ledger

| Requirement | Result | Review conclusion |
|---|---|---|
| `TOOL-025` (`read`) | CHANGES REQUIRED | Input domain, public result shape, text notices, line-count meanings, first-line overflow, image result/failure behavior, and cancellation are not correctly or completely specified. |
| `TOOL-026` (path preprocessing) | CHANGES REQUIRED | The draft adds a trim step Pi does not use, leaves the Unicode set open-ended, and calls the wrong Layer-12 seam. |
| `TOOL-027` (macOS fallback) | CHANGES REQUIRED (traceability only) | Excluding the behavior from core matches the recorded owner decision, but `NOT_ADOPTED_CORE` is not a permitted manifest disposition and no manifest row records the governed divergence/reservation. No implementation of the fallback is requested. |
| `TOOL-028` (`ls`) | CHANGES REQUIRED | Input domain, model-visible result/notices, empty/limit behavior, sorting determinism, read-directory error, and cancellation are incomplete or wrong. |

## Findings

### L13-WP131-R001 — `TOOL-026` path preprocessing does not match pinned Pi

**Classification:** `PI_PARITY_DEFECT`
**Blocking:** yes

Pinned Pi's tools call `resolvePath(..., {normalizeUnicodeSpaces: true, stripAtPrefix: true})`.
`normalizePath` trims only when `options.trim` is true; these callers never set it
(`path-utils.ts:40-49`, `utils/paths.ts:75-84`). The candidate instead makes trimming mandatory and
then claims the option sequence mirrors Pi exactly. It also describes the normalized Unicode set
with an ellipsis, while Pi uses the closed set `U+00A0`, `U+2000..U+200A`, `U+202F`, `U+205F`, and
`U+3000`.

**Minimal discriminating witness:** create two files named `" report.txt"` and `"report.txt"`.
Call Pi `read` with `path=" report.txt"`. Pi retains the leading ASCII space and selects the first
file. The candidate pipeline trims it and selects the second. The two implementations are
observably different before filesystem access.

**Minimal correction:** remove the trim step; state the exact closed Unicode replacement set and
the exact order `normalize Unicode spaces -> strip one leading @ -> Windows-only shell-path
normalization`. Preserve leading/trailing ordinary ASCII whitespace.

### L13-WP131-R002 — the draft calls the wrong certified Layer-12 seam

**Classification:** `CONTRACT_ASSURANCE_DEFECT`
**Blocking:** yes

The candidate directs every path through `ctx.fs.resolve(path)` and describes that call as the
place where tilde, `file://`, absolute, and cwd-relative lexical resolution happens. In the
certified Layer-12 contract, however, `FileSystem.resolve()` is the `EXEC-003` `FsTarget` bridge:
it performs canonical-if-existing / absolute-if-missing target identity derivation and returns an
opaque `FsTarget`, not the path string consumed by `read_text_file`, `read_binary_file`, `file_info`,
or `list_dir`. The draft neither calls `process_path()` nor explains how an `FsTarget` reaches those
filesystem operations. Using this bridge would also add canonicalization/failure behavior absent
from Pi's `read`/`ls` path setup.

The architectural intent—Layer 13 preprocesses only the tool-specific syntax and delegates the
rest to `ctx.fs`—is sound, but the named operation and observable sequence are not implementable as
written. There is also an acknowledged lower-layer source difference that the draft hides: coding-
agent `utils/paths.ts` throws while parsing a malformed `file://` URL, whereas the adopted Layer-12
resolver deliberately retains a malformed URL as an ordinary path and later returns an operational
filesystem error.

**Minimal discriminating witness:** use an existing symlink path and a provider whose
`canonical_path` is observable, then compare (a) passing the preprocessed string directly to
`read_text_file` with (b) `resolve -> process_path -> read_text_file`. Route (b) canonicalizes before
the read; route (a), like Pi's normal read, addresses the supplied lexical path and lets ordinary
content I/O follow it. The draft currently mandates (b) in name while specifying (a)'s rationale.

**Minimal correction:** define the actual Layer-12 operation sequence. For an fs-only built-in,
pass the preprocessed string to the appropriate certified `ctx.fs` operation (whose own provider
owns lexical path resolution), or explicitly justify and completely specify a different sequence.
Do not call the `FsTarget` bridge a lexical string resolver. Disclose and disposition the malformed
`file://` mapping difference rather than claiming direct Pi equivalence.

**Layer-12 impact:** no Layer-12 delta is required. The defect is entirely in how WP-13.1 names and
consumes the already-certified seam.

### L13-WP131-R003 — `read` and `ls` input schemas are narrowed without governance

**Classification:** `PI_PARITY_DEFECT`
**Blocking:** yes

Pinned Pi uses unconstrained TypeBox `Type.Number` for `read.offset`, `read.limit`, and `ls.limit`
(`read.ts:21-25`, `ls.ts:14-17`), not an integer/minimum-constrained schema. Fractional, zero, and
negative JSON numbers therefore validate and reach JavaScript's arithmetic/slice/comparison rules.
The candidate changes all three fields to `integer` without an approved intentional-divergence
record or a definition of the affected edge behavior. `ls` also uses `path || "."`, so an explicit
empty string selects cwd; the draft only states an omitted default.

**Minimal discriminating witnesses:** (1) validate `{path:"x", offset:1.5}` against Pi's emitted
schema—it is valid; it is invalid under the draft. (2) In a non-empty directory, call `ls` with
`limit:0`: Pi returns the literal empty-directory result because the loop reaches the cap before
adding an entry. (3) Call `ls` with `path:""`: Pi lists cwd. These distinguish the actual domain
from the drafted one.

**Minimal correction:** either specify the full Pi `number` domain and its observable coercion/
comparison behavior, or obtain and cite owner governance for a separate intentional-divergence row
that restricts each field. State empty-string path behavior explicitly.

### L13-WP131-R004 — the text result contract replaces Pi-visible output and conflates line counts

**Classification:** `PI_PARITY_DEFECT`
**Blocking:** yes

Pinned Pi returns an `AgentToolResult` whose model-visible `content` is an ordered list of content
blocks. Text reads include exact continuation notices in the text block; `details.truncation` is
present only for automatic truncation. The draft instead defines a new structured record
`content/truncated/truncated_by/total_lines/...` and calls Pi's literal notices rendering concerns.
No approved architectural mapping authorizes this provider-visible change.

The proposed fields are also internally wrong:

- Pi's `totalFileLines = allLines.length` is the whole-file count used in continuation text;
- `details.truncation.totalLines` counts the selected content passed to `truncateHead`, after both
  offset and any caller limit;
- a user `limit` that stops early produces a continuation notice but no truncation details;
- when the first line exceeds 50 KiB, `details.truncation.content` is empty, but the returned text
  block is not: it contains Pi's actionable `[Line ... Use bash: sed ... | head ...]` diagnostic.

One drafted `total_lines` field cannot represent both Pi counts, and the statement that returned
`content` is empty on first-line overflow contradicts `read.ts:297-301`.

**Minimal discriminating witness:** use a 100-line file, `offset=41`, `limit=20`. Pi returns lines
41-60 plus `[40 more lines in file. Use offset=61 to continue.]` and `details === undefined`.
The draft requires a structured truncation-shaped result and does not define the exact observable
text. A second witness with one line over 50 KiB returns Pi's diagnostic text, not empty content.

**Minimal correction:** specify the real ordered `AgentToolResult.content` blocks and the complete
`details.truncation` shape/absence rules; retain exact model-visible continuation/overflow notices
or obtain explicit governance for a separately-dispositioned divergence. Give the whole-file and
selected-content line counts distinct names and meanings.

### L13-WP131-R005 — the image branch is incomplete and uses the wrong data representation

**Classification:** `CONTRACT_ASSURANCE_DEFECT`
**Blocking:** yes

The draft calls image `data` "bytes" while Pi's `ImageContent.data` is a base64 string. It omits the
ordered leading text block, exact supported/sniffed formats, BMP-to-PNG conversion, invalid/
animated-PNG fallthrough to text, processing-failure-as-text-success outcomes, conversion/resize
hints, and the distinction between a failed processing result and a filesystem error. Stating only
"MIME-sniffed" plus "2000x2000" does not let Rust independently implement the accepted formats or
observable block order.

**Minimal discriminating witness:** read a valid BMP. Pi returns text first (`Read image file
[image/png]` plus conversion hint) and then an image block whose `data` is base64 PNG text. A
candidate returning raw bytes or only the image-shaped record satisfies the draft but differs from
Pi. A malformed image that sniffed as an image but cannot be converted returns a text block saying
the image was omitted; it does not raise a read error.

**Minimal correction:** specify the ordered content-block contract, base64 representation, closed
sniff/normalization behavior, processing-failure result, and hint/non-vision-note ordering. If image
processing is to be a separately owned helper, name that requirement and its evidence rather than
leaving behavior implicit.

### L13-WP131-R006 — `ls` ordering is not language-neutral

**Classification:** `PI_BEHAVIOR_UNCERTAIN`
**Blocking:** yes

`a.toLowerCase().localeCompare(b.toLowerCase())` is not fully captured by "case-insensitive": the
draft does not define locale/collation, equal-fold tie behavior, or a language-neutral ordering a
Rust implementation can reproduce. This is genuine unresolved Pi behavior for non-ASCII and
case-tied names, not a Rust implementation preference.

**Minimal discriminating witness:** list entries `A`, `a`, and at least one non-ASCII case pair and
record Pi's order under the supported runtime/locale. Plausible ordinal, Unicode-casefold/ordinal,
and locale collation implementations need not agree.

**Minimal correction:** characterize the supported Pi runtime's observable comparator and adopt a
deterministic language-neutral production order (with governance if it intentionally differs), then
add tied/non-ASCII discriminating witnesses.

### L13-WP131-R007 — `ls` cap, empty, error, and output semantics are incomplete or wrong

**Classification:** `PI_PARITY_DEFECT`
**Blocking:** yes

The draft changes or omits observable behavior:

- Pi's zero-result output is literally the text block `"(empty directory)"`; it is not merely UI
  rendering and is sent to the model.
- Pi checks `results.length >= effectiveLimit` before statting the next sorted entry. Thus a reached
  cap is reported when an unvisited entry exists even if that entry would later have failed stat.
- a zero/negative limit on a non-empty directory takes the early zero-result branch and returns no
  `entryLimitReached` details;
- entry-limit and byte-limit notices are appended to the already-truncated listing text and are
  model-visible; the byte ceiling applies to the raw joined listing, not to the final text after
  notices;
- a `readdir` failure has its own `Cannot read directory: ...` outcome, absent from the draft.

**Minimal discriminating witness:** use `limit=1` where the second sorted entry's stat would fail. Pi
accepts the first entry, stops before statting the second, sets `entryLimitReached=1`, and appends
the exact limit notice. A conforming Rust implementation cannot infer this from the current prose.

**Minimal correction:** specify the real content block/details/notices including edge limits,
pre-stat cap timing, empty-result behavior, and read-directory failure.

### L13-WP131-R008 — tool cancellation behavior is absent

**Classification:** `CONTRACT_ASSURANCE_DEFECT`
**Blocking:** yes

Both pinned tools accept the Layer-09/Layer-06 signal and reject `"Operation aborted"` when already
aborted or when it fires during the operation (`read.ts:223-241`, `ls.ts:111-125`). `read` also has
explicit post-await `aborted` checkpoints after path resolution and readability access and refuses
late success after an abort. The draft contains no signal rule, despite built-in tool execution
being the first layer where each concrete tool's cooperative behavior is chosen.

**Minimal discriminating witness:** use a pending filesystem operation, start `read`/`ls`, then
abort before it settles. Pi's returned promise rejects with `Operation aborted`; a candidate that
ignores the signal can return a successful listing/read and still satisfy the current draft.

**Minimal correction:** specify each tool's observable pre-abort/live-abort settlement and the
required cooperative checkpoints language-neutrally, reusing Layer 09's signal authority without
redefining it.

### L13-WP131-R009 — requirement dispositions and discriminating contract evidence do not exist

**Classification:** `CONTRACT_ASSURANCE_DEFECT`
**Blocking:** yes

The current code default branch contains no `TOOL-025`, `TOOL-026`, `TOOL-027`, or `TOOL-028`
manifest rows, and this candidate changes only `spec/tools.md`. Consequently none of the four
requirements has the required Pi path -> rule -> evidence -> language ownership -> disposition
chain. `NOT_ADOPTED_CORE` is a useful owner scope decision, but it is not one of the manifest's
allowed dispositions (`adopted`, `deferred parity`, `intentional divergence`). The exclusion of
`TOOL-027` must be represented using the established taxonomy and cite its governance source.

No canonical scenario or explicit planned-language witness matrix currently discriminates the
high-risk rules above (path preprocessing, numeric edge inputs, two kinds of line count, first-line
overflow, image block order, `ls` collation/cap/skip interactions, and cancellation).

**Minimal correction:** add coherent manifest rows using only established dispositions and add a
language-neutral witness matrix/canonical plan sufficient for independent implementation. Do not
count placeholders as evidence and do not implement runner semantics.

## Contract-quality answers

```text
Does the draft reimplement certified Layer-12 semantics?
    It intends not to, but names the FsTarget bridge as a lexical resolver and is therefore
    architecturally ambiguous/wrong as written.

Does the Layer-12 contract require reopening?
    NO. Its operations and FsTarget bridge are already sufficient; WP-13.1 must consume the
    correct operation.

Could Python and Rust both satisfy the draft while differing observably?
    YES -- output block/text shape, line counts, image data representation, ls collation,
    numeric edge inputs, and cancellation all permit or require different choices.

Does the draft leak into WP-13.2/13.3/13.4 or Layer 05/06?
    No implementation scope leak was found. Mentioning the existing bash fallback text in Pi's
    read output is not implementation of WP-13.3; it is part of read's observable output.

Is TOOL-027 correctly absent from core behavior?
    YES semantically, subject to recording that owner decision under an allowed manifest
    disposition. No macOS fallback implementation is requested.
```

## Verdict

```text
WP-13.1 shared contract:  CHANGES REQUIRED
Layer-12 boundary:        CLEAR; no Layer-12 reopen required
Python WP-13.1:           NOT_IMPLEMENTED / NOT AUTHORIZED
Rust WP-13.1:             NOT_IMPLEMENTED / BLOCKED
Layer 13 cross-language:  NOT CLOSED
WP-13.2/13.3/13.4:        NOT REVIEWED OR STARTED BY THIS PASS
```

Active blockers:

```text
PI_PARITY_DEFECT
    L13-WP131-R001, R003, R004, R007

CONTRACT_ASSURANCE_DEFECT
    L13-WP131-R002, R005, R008, R009

PI_BEHAVIOR_UNCERTAIN
    L13-WP131-R006 (locale/case-tie ordering)
```

No candidate/shared/Python/Rust implementation file was modified. The only task-owned change is
this independent review artifact on a separate review branch.

## Next action

Return the nine narrowly scoped findings to the WP-13.1 shared-contract owner. Remediate the
contract and evidence only, then submit the new exact SHAs for a fresh independent review. Do not
implement Python or Rust WP-13.1 and do not start another Layer-13 work package from this review.
