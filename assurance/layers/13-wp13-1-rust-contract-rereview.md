# Layer 13 WP-13.1 independent Rust contract re-review

**Mode:** review only. No Python or Rust Layer-13 implementation was performed.

## Exact candidate

```text
coordination:       EGAILab/minion-agent#48 (OPEN, CONTRACT_REVIEW, NEXT_OWNER Codex)
docs PR:            EGAILab/minion-agent-docs#132
docs head:          1dca05e822ef7c316867ab7b7e0067186e1dbe20
docs base:          master @ 0bbd737fab8c1360995f4efff2b41c1c5531a9c3
manifest PR:        EGAILab/minion-agent#52
manifest head:      cca8d8b325bb159be549e10c8321b3468f043e7f
manifest base:      main @ 92aa4be168dc82111832467922089206e858a9c4
first review:       minion-agent-docs#133 @
                    e9a54080db58be1d3347e787143749a75d6e8f74
pinned Pi:          b7bb00b936dbe21b8e160b3e89efdec361846699
```

Both candidate heads were remote-reachable, Ready for Review, open, and unmerged. This verdict
applies only to those exact heads.

The review independently re-read the pinned `read.ts`, `ls.ts`, `path-utils.ts`, `utils/paths.ts`,
`truncate.ts`, `mime.ts`, `image-process.ts`, `image-resize-core.ts`, and the harness
`nodejs.ts` resolver, then the remediated spec/manifest, certified Layer-12 contract/architecture,
and prior review. Python was not used as the semantic oracle.

## Closure ledger

| Finding | Result | Independent result |
|---|---|---|
| `L13-WP131-R001` | **RESOLVED** | Mandatory trim is gone and the exact Unicode-space set/order is stated. |
| `L13-WP131-R002` | **PARTIALLY_RESOLVED_BLOCKING** | The FsTarget misuse is corrected, but the malformed-`file://` observable divergence is declared accepted without owner governance and remains bundled into an `adopted` row. |
| `L13-WP131-R003` | **STILL OPEN** | Number schemas are restored, but the specified negative/fractional semantics are factually wrong/incomplete. |
| `L13-WP131-R004` | **PARTIALLY_RESOLVED_BLOCKING** | Ordered content blocks and the two line counts are restored, but the observable truncation-details shape and exact result variants remain incomplete. |
| `L13-WP131-R005` | **PARTIALLY_RESOLVED_BLOCKING** | Base64/block ordering is restored, but exact image rules contain a wrong conversion hint and non-implementable approximations. |
| `L13-WP131-R006` | **STILL OPEN** | The candidate correctly discloses the unresolved locale-dependent collation question; no governed contract exists yet. |
| `L13-WP131-R007` | **STILL OPEN** | Several cap rules are fixed, but fractional details, simultaneous cap+byte truncation, and the Layer-12 listing abstraction contradict the proposed witness. |
| `L13-WP131-R008` | **STILL OPEN** | The abort contract omits and contradicts `read`'s final post-processing `aborted` checkpoint. |
| `L13-WP131-R009` | **PARTIALLY_RESOLVED_BLOCKING** | Rows are present and structurally valid, but adopted rows bundle known divergences and planned scenarios are not current executable evidence. |

## Detailed blocking results

### R002 — correct operation, ungoverned observable divergence

The correction from `ctx.fs.resolve()`/`FsTarget` to direct read-only filesystem operations is
correct and Layer 12 does not need reopening for that correction. However, malformed `file://`
behavior is observably different: Pi's coding-agent resolver throws during URL parsing; the
Layer-12-backed Minion path reaches an ordinary filesystem `Result` error. The candidate calls this
an "accepted divergence" without an owner governance source and leaves `TOOL-026` as `adopted`.
General authorization to consume `ctx.fs` does not silently approve every newly discovered
observable consequence.

**Witness:** `path = "file:///%E0%A4%A"`. Pinned coding-agent `resolvePath` throws from unguarded
`fileURLToPath`; the drafted Minion path retains the literal and reports an operational filesystem
error.

**Required correction:** obtain explicit governance and put the difference in a coherent
`intentional divergence` subject/row, or reproduce Pi's parse-error behavior at the Layer-13 input
boundary without duplicating the rest of Layer-12 resolution.

### R003 — negative and fractional numbers are still specified incorrectly

Restoring `number` is correct, but the draft says a negative `limit` produces an end before the
start and an empty slice. At the default start, JavaScript negative slice indices are relative to
the array end: for four lines and `limit=-1`, Pi computes `end=-1`, and `slice(0,-1)` returns the
first three lines. Pi then appends the nonsensical-but-observable continuation
`[5 more lines in file. Use offset=0 to continue.]`.

The `ls` half is also incomplete: a positive fractional limit behaves like a ceiling in the loop
(`limit=1.5` accepts two entries before the next check), and `details.entryLimitReached` stores the
original fractional value `1.5`, contradicting the draft's `integer` type.

**Executed negative control:** Node produced:

```text
read limit=-1, start=0 -> slice [L1,L2,L3], nextOffset=0
ls limit=1.5           -> 2 results, entryLimitReached=1.5
```

**Required correction:** state `ToIntegerOrInfinity`/negative-index slice behavior and all derived
notice arithmetic language-neutrally; make `entry_limit_reached` a number and specify positive
fraction behavior. Add these exact witnesses.

### R004 — truncation result remains incomplete

The draft now correctly restores one text content block, continuation text, the two line-count
meanings, and absence of details for caller-limit-only continuation. But Pi's observable
`TruncationResult` also contains `totalBytes`, `outputLines`, `outputBytes`, `lastLinePartial`,
`maxLines`, and `maxBytes`; the draft lists only a subset and therefore permits Rust to omit values
Python may expose. It also describes message templates rather than pinning every exact variant
(line-vs-byte continuation and size formatting).

**Required correction:** specify the complete existing `TruncationResult` projection and exact
model-visible templates/absence rules, with scenarios that distinguish line truncation, byte
truncation, first-line overflow, and caller limit.

### R005 — image contract still contains factual/precision defects

The base64 representation and text-before-image order are corrected. Two binding claims remain
wrong or non-implementable:

- Pi sniffs exactly 4100 bytes, not "~4100"; the rejected JPEG case is exactly fourth byte `0xF7`,
  and PNG chunk rules are source algorithms, not an unspecified "specific malformed pattern".
- Pi's BMP hint is exactly `[Image converted from image/bmp to image/png.]`, because
  `conversionHint` receives full MIME strings. The draft states `[Image converted from bmp to
  png.]`.

The row also calls non-byte-identical resize behavior a `MINION_EXTENSION` while keeping the whole
subject `adopted`, without a separate disposition or governance source.

**Witness:** a valid BMP must return the full-MIME conversion hint followed by any dimension hint,
then a base64 image block. A Rust implementation following the current literal spec emits the wrong
text.

**Required correction:** pin exact sniff constants/conditions and hint strings. Describe permitted
implementation variance as a non-observable implementation choice, or separately govern and
disposition any observable resize divergence.

### R006 — collation remains open

The characterization is useful and correctly refuses to pretend that default-locale
`localeCompare` is deterministic. It is nevertheless an active `PI_BEHAVIOR_UNCERTAIN`; an open
question cannot pass a contract gate. The proposed ordinal case-insensitive + exact-string tie
break would be an intentional observable divergence and requires owner governance.

**Required decision:** either approve a named deterministic comparator and record it as an
intentional divergence with discriminating ASCII/case-tie/non-ASCII scenarios, or define a pinned
locale/collator/runtime strategy that reproduces an explicitly chosen Pi environment. Silence is
not approval.

### R007 — `ls` details and Layer-12 composition remain contradictory

Pi may set both `details.entryLimitReached` and `details.truncation` in one result: entry capping
happens first, then byte truncation of the collected listing. The draft says
`entry_limit_reached` is present only when the cap was hit "BEFORE the byte ceiling," implying a
mutually exclusive priority that does not exist. As R003 shows, the field may also be fractional.

More fundamentally, the proposed witness "limit=1, second sorted entry would fail classification,
cap reported before the second stat" cannot be implemented through `ctx.fs.list_dir()`: that
Layer-12 operation performs enumeration/classification before returning and exposes only surviving
`FileInfo` values (or a whole-call error). With only one surviving returned entry, Layer 13 cannot
know an unreturned second raw name existed and therefore cannot reproduce Pi's pre-stat cap signal.
The draft simultaneously mandates Pi's timing and discloses a seam that erases the information
needed to implement it.

**Required correction:** choose explicitly between (a) an owner-approved, separately-dispositioned
Layer-12 architectural divergence for listing/cap behavior or (b) an additive lower-layer delta/
other real seam that exposes sufficient raw enumeration information. Do not keep an unexecutable
Pi witness beside a contract that mandates `list_dir()` only. Specify simultaneous cap+byte details.

### R008 — `read` has a third explicit abort checkpoint

Pinned `read.ts` checks `aborted` after resolution, after readability access, and again at line 325
after all text/image read and processing work but immediately before successful resolution. The
draft names only the first two and states that an abort after processing does not discard the
result. If the abort event fires before the final check, Pi's promise is already rejected and the
processed result is not returned.

**Witness:** pause immediately before the final success check after image processing, fire abort,
then resume. Pi rejects `Operation aborted`; the drafted rule permits success.

**Required correction:** specify all three checkpoints and distinguish abort before final
settlement from abort after the promise has already settled.

### R009 — traceability exists, but dispositions are incoherent

Fresh validation confirms 105 rows / 105 unique IDs, four new rows, list-shaped `tests`, and eight
manifest validator tests passing with `--no-cov`. Planned scenario strings are honestly labelled
planned and are not falsely reported as passing.

However:

- `TOOL-026 adopted` bundles the known malformed-URL divergence;
- `TOOL-025 adopted` bundles a claimed observable resize `MINION_EXTENSION`;
- `TOOL-028 adopted` bundles broken-symlink/per-entry-error divergences and an unresolved
  `PI_BEHAVIOR_UNCERTAIN` collation rule.

One subject cannot simultaneously be adopted, intentionally divergent, and unresolved. Split
coherent subjects or revise the disposition after valid governance. Planned scenarios are a plan,
not certification evidence; real schema/scenarios/runners remain required before implementation
certification.

## New finding

### L13-WP131-R010 — built-in filesystem error projection is undefined

**Classification:** `CONTRACT_ASSURANCE_DEFECT`

The draft says missing, non-directory, unreadable, and enumeration failures are "distinguishable"
but never defines how Layer-12 `FsError{code,message,path}` becomes the Layer-06 tool failure seen
by the model. Pi uses concrete thrown messages (`Path not found: ...`, `Not a directory: ...`,
`Cannot read directory: ...`, raw read/access failures). Two conforming implementations may expose
different codes/text/content while satisfying "distinguishable."

**Witness:** invoke `ls` on (1) missing path, (2) regular file, and (3) unreadable directory, and
observe the finalized tool-result text/error classification. The current draft permits arbitrary,
cross-language-different projections.

**Required correction:** define the language-neutral error variants and exact model-visible
projection (including path/message normalization), then add discriminating scenarios through the
real Layer-06 seam.

## Layer-12 impact

```text
Layer-12 contract defect found?                         NO
Original FsTarget misuse corrected without reopening?  YES
Strict Pi ls pre-stat semantics implementable through
current list_dir result alone?                          NO
Decision required:                                     govern a Layer-13 divergence OR
                                                       open a narrow additive dependency delta
Layer-12 status now:                                    remains historically CLOSED;
                                                       no reopen initiated by this review
```

## Convergence trigger

R002/R003/R004/R005/R007/R008/R009 survived this independent re-review in blocking form. Under
`agent-workflow.md` section 11.8, another ordinary point-fix pass is not valid; WP-13.1 must enter
`CONTRACT_CONVERGENCE`. The convergence characterization must unify:

1. exact JavaScript numeric/slice/limit behavior;
2. complete text/image/details/error projections;
3. the information actually available through Layer-12 `list_dir`;
4. every known architectural divergence and its governance/disposition;
5. R006's deterministic collation owner decision.

## Verdict

```text
WP-13.1 shared contract:  CHANGES REQUIRED
Layer-12 boundary:        CLEAR as a certified layer, but WP-13.1 has an unresolved
                          dependency/divergence choice for exact ls behavior
Python WP-13.1:           NOT_IMPLEMENTED / NOT AUTHORIZED
Rust WP-13.1:             NOT_IMPLEMENTED / BLOCKED
Layer 13 cross-language:  NOT CLOSED
WP-13.2/13.3/13.4:        NOT STARTED BY THIS REVIEW
```

Only `L13-WP131-R001` is fully resolved. `R010` is new. No candidate/shared/Python/Rust
implementation file was modified; this review artifact is the sole task-owned change.

## Next action

Enter a WP-13.1 convergence characterization/checkpoint covering the surviving findings and R010.
Do not implement either language. Owner governance must resolve R006 and any proposed observable
Layer-12-mapping divergence before the checkpoint can be agreed for implementation.
