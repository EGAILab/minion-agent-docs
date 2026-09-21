# CE-L13-WP131-01 independent convergence challenge

**Mode:** contract/evidence challenge only. No Python or Rust implementation was performed or
authorized. No Layer-12 production or contract change was made. No owner choice was made for any
governance question.

## Exact target

```text
coordination issue:  EGAILab/minion-agent#48
status:              CONTRACT_CONVERGENCE
next owner:          Codex
docs PR:             EGAILab/minion-agent-docs#132
docs head:           f873217f35c142b0177bddb80e8934ddf2eac2d9
manifest PR:         EGAILab/minion-agent#52
manifest head:       cca8d8b325bb159be549e10c8321b3468f043e7f
docs base:           master @ 0bbd737fab8c1360995f4efff2b41c1c5531a9c3
code base:           main @ 92aa4be168dc82111832467922089206e858a9c4
pinned Pi:           b7bb00b936dbe21b8e160b3e89efdec361846699
episode:             CE-L13-WP131-01
checkpoint artifact: assurance/layers/13-wp131-ce-l13-wp131-01-characterization.md
```

Both candidate PRs were open, Ready for Review, mergeable, and their issue-recorded heads matched
their remote heads. Both heads were remote-reachable. The issue carried a valid, scoped
governance source authorizing characterization and challenge only. The candidate is not derived
from a quarantined artifact.

The challenge independently re-read pinned Pi's coding-agent `read.ts`, `ls.ts`, `path-utils.ts`,
`truncate.ts`, `mime.ts`, `image-process.ts`, and image-resize types/implementation; Pi's
tool-argument validation path; the certified Layer-12 `FileSystem` contract and both language
architectures; the two prior Rust review artifacts; the current manifest/spec; and the checkpoint
plus its numeric/collation probe evidence. Python was not used as the semantic oracle.

## Requested result

```text
R006 CHARACTERIZATION:                 REJECTED
R007 CHARACTERIZATION:                 REJECTED
R002:                                  CHANGES REQUIRED
R003:                                  CHECKPOINT-READY
R004:                                  CHANGES REQUIRED
R005:                                  CHANGES REQUIRED
R008:                                  CHECKPOINT-READY
R009:                                  CHANGES REQUIRED
R010:                                  CHANGES REQUIRED
OWNER DECISION READY:                  NO
IMPLEMENTATION AUTHORIZED:             NO
```

## Findings challenge

### L13-WP131-R002 — CHANGES REQUIRED

The checkpoint correctly says the malformed-`file://` difference needs governance, but it does
not actually characterize that finding. `R002` has no source/probe section, behavior matrix,
minimal witness, or neutral choice between reproducing Pi's unguarded `fileURLToPath` parse
failure and approving the Layer-12-backed operational-error result. It appears only in the
manifest-coherence discussion.

The episode's own rule requires every open finding to have an observable rule and acceptance
witness. Add the already-established malformed URL witness and make this a third explicit owner
decision. A future `TOOL-026` row cannot be `adopted` while carrying that unapproved difference.

### L13-WP131-R003 — CHECKPOINT-READY

The source mapping and direct probes are correct. In particular:

- optional `null` is normalized to omission by Pi's tool-argument validator before execution;
- `read` retains fractional intermediate arithmetic but `slice` applies
  `ToIntegerOrInfinity`;
- a negative end index at start zero is relative to the array end;
- `ls` compares the integer result count directly with the unrounded numeric limit and records
  the raw numeric limit in details;
- non-finite values are outside the real JSON tool-call domain.

The permanent contract/evidence pass must include the negative and fractional witnesses rather
than only the probe transcript.

### L13-WP131-R004 — CHANGES REQUIRED

The eleven-field `TruncationResult` correction is accurate, and the branch ordering is accurate.
The claimed "exact" model-visible table is still not exact enough to implement independently:
the first-line and byte-limit messages depend on Pi's `formatSize`, but the checkpoint leaves
`<size>`/`<limit>` placeholders and never states the formatting rule (`<1024 -> N B`,
`<1 MiB -> (bytes/1024).toFixed(1) KB`, otherwise `(bytes/1 MiB).toFixed(1) MB`). It also does
not enumerate the two distinct `processImage` failure strings needed by the image-side result
matrix.

Add the formatting algorithm and exact literals/absence rules to the proposed normative delta,
with witnesses that distinguish the thresholds and messages. A Rust implementation must not
need to inspect Pi or Python to fill placeholders in model-visible text.

### L13-WP131-R005 — CHANGES REQUIRED

The checkpoint correctly fixes the 4100-byte sniff size, `0xF7` JPEG rejection, PNG rules, full
MIME conversion hint, base64 representation, and content-block order. It does not resolve the
disposition problem.

`ImageContent.data` is sent to the provider/model and is observable. A different resize/re-encode
algorithm can change encoded bytes, dimensions, MIME output, and even success versus the
text-only failure branch. It therefore cannot be declared "out of contract scope" merely by
analogy to filesystem bytes. Either the contract must define a sufficiently constrained
observable equivalence class, or the remaining observable variance needs an explicit, governed
divergence subject. The checkpoint also needs the two exact Pi processing-failure messages, not
the placeholder `processed.message`.

This is another owner/governance dimension unless the next revision proves the allowed
implementation variance is non-observable under the public result contract.

### L13-WP131-R006 — CHARACTERIZATION REJECTED

The source facts are correct: Pi lowercases each name, calls `localeCompare` without a locale,
and relies on stable sort for equal comparisons. The probe honestly establishes only one
Windows/Node/ICU environment.

The option matrix is not yet neutral or implementable:

1. `R006-A` says Python `locale.strxfrm` or a Rust ICU binding with no pinned locale preserves
   Pi's environment-sensitive semantics. Those mechanisms do not share Node/V8's default-locale
   resolution, Unicode lowercase tables, ICU version, or collator defaults. They can disagree on
   the same host. This is at best a best-effort Minion mapping, not literal preservation of
   "whatever Pi would do on this same machine," and its divergence/evidence burden must be
   disclosed.
2. `R006-B` uses "simple case-folded" while Pi uses ECMAScript `toLowerCase`. Cross-language
   case-folding terminology is not equivalent (full case fold can expand `ß` to `ss`), and the
   proposed tie-break changes Pi's stable-enumeration tie behavior. Pin the exact normalization
   operation, Unicode/version policy, primary comparison units, and tie-break. A probe of the
   checkpoint corpus confirms that locale order and ordinal-lower-plus-exact-tie order differ;
   the latter is a governed divergence, not merely a deterministic spelling of Pi.
3. `R006-C` correctly identifies that a pinned collation profile needs a common implementation,
   but it is not decision-ready until feasibility identifies at least one concrete shared
   locale/ruleset/version strategy and its versioning/evidence burden.

Revise the options so each describes an actually implementable cross-language rule and its true
parity status. Codex does not choose among them.

### L13-WP131-R007 — CHARACTERIZATION REJECTED

The high-level information-loss claim is sound: `FileSystem.list_dir()` returns only classified
`FileInfo` survivors (or a whole-call `FsError`) after complete enumeration, so Layer 13 cannot
derive Pi's pre-next-stat cap flag from that result alone. `list_dir_raw` is a plausible minimal
additive capability; a fully eager `list_dir_with_failures` cannot reproduce Pi's provider-call
trace because it still touches entries Pi may never stat.

The checkpoint's concrete witness is invalid against the certified LocalFileSystem behavior it
cites. A permission-denied/deleted `lstat` is an `OSError`; `_list_dir_sync` catches only
`_UnsupportedFileType`, so that failure becomes a whole-call `FsError`, not silent omission and
`Ok([e1,e2])`. Pinned Pi's Layer-12 `NodeExecutionEnv.listDir` likewise returns a whole-call error
for `lstat` failure. The written trace therefore does not reproduce the claimed same-output/
different-cap observation.

Use a valid indistinguishable-world witness. For example, contrast a directory containing only
two classifiable entries with one containing those entries plus a third unsupported special-file
kind: certified Layer 12 may return the same two `FileInfo` survivors in both worlds, while Pi's
coding-agent `ls` reaches the cap before statting the third raw name and reports the cap. State
separately that Pi coding-agent `ls` would include a stat-successful non-directory special entry
if it were reached; the witness works precisely because the cap prevents that observation.

Also correct the consequence table: choosing `list_dir_raw` is a narrow additive Layer-12
contract/implementation delta that requires Python and Rust implementation plus revalidation.
It does not invalidate historical certification, but it is still a lower-layer delta, not
"Layer 12 change: none" for the episode's resulting work.

### L13-WP131-R008 — CHECKPOINT-READY

The checkpoint now accurately distinguishes the abort event listener (which rejects the promise)
from the three post-start guards that prevent later work/success publication, including the final
post-processing guard. Permanent evidence should control the settlement window rather than depend
on an unrepeatable timing race, but the semantic characterization is complete.

### L13-WP131-R009 — CHANGES REQUIRED

It is correct not to edit the manifest before governance settles the affected subjects. The
proposed disposition plan remains incomplete because:

- `TOOL-026` needs the R002 governance decision;
- `TOOL-025` cannot discard observable resize/re-encode variance as non-semantic without the R005
  resolution;
- `TOOL-028` depends on corrected R006/R007 characterizations and their later owner decisions;
- R010's tool-error projection needs its own coherent mapping/divergence disposition.

After checkpoint agreement, each manifest row must have one semantic subject and one defensible
disposition. Planned scenarios remain plans, not passing evidence.

### L13-WP131-R010 — CHANGES REQUIRED

The Pi error-source table is useful, but the proposed resolution is not a complete contract and
is not automatically authorized by Layer 12.

Layer 12 normalizes filesystem operations to `FsError`; it does not decide the model-visible text
or Layer-06 tool result emitted by a built-in tool. Replacing Pi's observable hand-authored/raw/
hybrid messages with new Layer-13-authored templates is an observable change. Calling it
`MINION_ARCHITECTURAL_MAPPING` does not remove the governance requirement.

The proposal is also only illustrative (`e.g.`): it does not define exact variants/templates,
path rendering, whether underlying messages are included, the Layer-06 `is_error`/content shape,
or mappings for all eight `FsErrorCode` values (`INVALID`, `NOT_SUPPORTED`, and `UNKNOWN` are
especially omitted). Two independent implementations can still differ while satisfying it.

Add a complete Pi-to-`FsErrorCode`-to-tool-result matrix, exact normalized model-visible
projections, and the real Layer-06 seam witnesses. Present literal Pi-shaped projection versus a
governed deterministic Minion projection as an owner decision rather than assuming Layer 12
already made it.

## Contract-quality answers

```text
Does the checkpoint encode implementation mechanics as semantics?       YES, in R006-A's
                                                                        suggested runtime mappings.
Does it silently reopen Layer 12?                                       NO.
Does it identify a possible additive Layer-12 dependency delta?         YES, but R007's witness
                                                                        and consequence wording
                                                                        need correction.
Can Python and Rust implement every proposed rule independently?        NO, not yet for R004,
                                                                        R005, R006, R010.
Could conforming implementations still differ observably?               YES, image bytes/results,
                                                                        collation, and error
                                                                        projection remain open.
Are all prior findings represented by valid acceptance criteria?        NO, R002 is missing and
                                                                        R007's witness is invalid.
Did spec/manifest encode a guessed R006/R007 outcome in this pass?       NO.
Is Layer 12 historically reopened or uncertified by this challenge?     NO.
```

## Verdict and next action

```text
checkpoint review:          REJECTED
owner decision ready:       NO
implementation authorized: NO
Python WP-13.1:             NOT_IMPLEMENTED / NOT AUTHORIZED
Rust WP-13.1:               NOT_IMPLEMENTED / BLOCKED
Layer 13 cross-language:    NOT CLOSED
Layer 14:                   NOT STARTED
```

Return `CE-L13-WP131-01` to characterization. The narrow required revision is:

1. add full R002 characterization and governance options;
2. complete R004's exact formatting/literal projection;
3. treat R005's observable resize/re-encode variance honestly and govern it if divergent;
4. make R006's choices concrete, implementable, and accurately dispositioned;
5. replace R007's invalid permission/deletion witness and correct the additive-delta wording;
6. make R010 a complete model-visible result matrix and owner decision;
7. derive R009's eventual row split/dispositions from those corrected decisions.

Do not implement Python or Rust WP-13.1, change Layer 12, or start Layer 14 during that revision.
