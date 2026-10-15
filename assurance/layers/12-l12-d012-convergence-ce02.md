# L12-D012 Rust native reads — CE-L12D012-02

Status: **AGREED FOR IMPLEMENTATION of exactly R1–R5**, independent checkpoint
review [issuecomment-6183538250](https://github.com/EGAILab/minion-agent/issues/229#issuecomment-6183538250).
The characterization below remains evidence at rejected code
`0389a29c59e56f9934f66bf9e13927858c5a65fc`, not corrected-head gate credit.
Implementation and fresh verification are complete at the candidate in §7.2;
independent targeted closure and complete review are still required. Rust F001 and
`L12D012-RUST-I001` remain open; cross-language is NOT CLOSED. #228 waits.

## 1. Authority and rejected candidate

Coordination: minion-agent#229. Independent closure review 1 is
[issuecomment-6183035989](https://github.com/EGAILab/minion-agent/issues/229#issuecomment-6183035989).
Trigger C took the default characterization route, episode CE-L12D012-02. The
coordination status remains RUST_IMPLEMENTATION because the adopted state machine
has no CLOSURE_REVIEW-to-CONTRACT_CONVERGENCE transition. This is not permission
to fix before the checkpoint is independently AGREED.

Authority order: pinned Pi `b7bb00b936dbe21b8e160b3e89efdec361846699`
`packages/agent/src/harness/env/nodejs.ts:51–65`; execution spec §§2, 3.2, 15;
Node v22.15.1 and its bundled libuv 1.49.2; canonical 80; certified Rust seams;
then assurance. Python is not an oracle. No canonical expectation changes.

The reviewer supplied a four-observation acceptance pair: provider `C:\x`,
`=E:` absent, existing plain cwd versus its extended `\\?\` spelling, inputs
`e:leaf` and `\leaf`. In the extended child, Pi gives `e:leaf` and
`\\?\E:\leaf`; the rejected Rust gives a fully expanded ordinary path and
`E:\leaf`. Both ordinary-cwd observations match.

Reviewer artifacts (read-only originals): `xprefix_probe.py`, SHA-256
`29b405a9a067f4d35a2b5a7fabaec13dacfd54c7adc0541628b702fc0a52d2c2`;
`xprefix-probe-2.json`, SHA-256
`d493617bd4ef6b5233556bc4513a8bfdbe1ddf29d34e4441cb3d9189dbe8efba`.

## 2. Native-read inventory and mapping audit

These are distinct authorities, not interchangeable path codecs:

| Input/read | Rejected Rust pipeline | Required boundary / disposition |
|---|---|---|
| Logical provider cwd | `native_units` then `without_extended_prefix` at the OS-path convenience adapter; lossless logical entry stays raw | Preserve existing provider adapter; do not reuse it for a native read |
| Logical caller path | raw FsPath UTF-16 through the lexical resolver | No native decode, scalar replacement or prefix stripping |
| Inherited `=D:` | `var_os` → raw native units → `native_view` | Native section-15 view only; absent and empty retain their distinct carrier values, then selection uses truthiness |
| Process cwd, selected-drive branch | `current_dir` → `logical_provider_path` → `native_view` | Wrong: drops extended prefix. Use the cwd-specific native boundary below |
| Process cwd, empty-device/rooted drive-less branch | Same callback as above | Same rule, independently exercised; never substitute provider cwd's drive |
| Native filesystem-result/display | `from_native`: scalar replacement plus prefix mapping | Preserve certified mapping; not an operand reader |
| Logical path sent to OS | `native`: one replacement per unpaired surrogate | Preserve certified outgoing projection, distinct from section-15 native decoding |
| Home expansion | HOME before USERPROFILE, then `from_native` | Pre-existing separate home-source/mapping question, §6; not silently repaired here |

The lexical selected-drive test is unchanged: choose the nonempty inherited
view, otherwise read process cwd lazily; compare the first two **UTF-16 units**
with the pinned lowercase operation, and test unit 2. The empty-device branch
reads process cwd directly. Existing lazy-read/error witnesses remain required.
[Node's exact resolver source](https://github.com/nodejs/node/blob/v22.15.1/lib/path.js#L185-L210).

The cwd boundary must preserve all raw units and prefixes, except the following
cwd-specific operation: remove **one** final backslash if present, unless the
whole raw value has exactly three units and unit 1 is a colon. Then apply the
section-15 native string view (valid pairs unchanged; each unpaired surrogate
becomes three U+FFFD; BOM retained). Do not trim a forward slash, repeatedly
trim, strip a namespace, canonicalize, resolve or use display/provider mapping.
The ordinary root `E:\` is preserved; the extended root `\\?\E:\` loses its
last backslash. The inherited entry has **no** such cwd trim.
[Bundled libuv cwd source](https://github.com/nodejs/node/blob/v22.15.1/deps/uv/src/win/util.c#L135-L194).

Successful raw reads and failed reads form separate classes. This proposal does
not guess a cwd on an error. Existing typed FsError/ShellError/SubprocessError
behavior is the **spec §2 architectural error-boundary mapping**; pinned Pi's
resolvePath sits outside its try blocks and can throw here. It is not a claim
that Node returns a typed Result.

## 3. Characterization safety and provenance

The observer lives only in a fresh detached scratch worktree of rejected code
0389a29c. Its patch adds a cfg(test, windows) module; no production expression
is replaced. A separate read-only ctypes child records GetCurrentDirectoryW;
the Rust observer records raw std::env::current_dir units,
provider/display/raw-view/actual-cwd-view mappings, inherited raw/view values,
and both the real LocalFileSystem.absolute_path and logical resolver outputs.
The raw OS child receives the identical cwd/environment; its units must equal
the Rust std read. The crate's `forbid(unsafe_code)` remains intact.
Injected mapping strings are values, never filesystem targets.

The launcher checks Node v22.15.1, the Pi source blob against the pin and the
scratch checkout head. Children use only existing directories: retained plain
and Unicode fixtures, their extended/trailing spellings, and the existing E:
root. No fixture mkdir, write, rename or delete; no network shares are touched.
All evidence publication is NEW-only and guarded immediately by the existing
lexical/no-follow/real containment helper. Tool caches remain under the project
root; no installation, cleaning, signal or process kill. Four Cargo jobs, fresh
workspace sources and read-only memory preflight precede the observer build.
This is focused characterization, not a new G3 certification run.

## 4. Observed partition

`data/l12-d012/ce02/native-r3/native-win32.json` records **196 states**, each
with three synchronous children (Pi/Node, unchanged Rust plus observer, raw OS
reader): **588 children**, **980 resolver observations**. Every child exited.
The source-predicted cwd boundary agrees with Node **196/196**; raw OS cwd
equals Rust std cwd **196/196**; the inherited-entry view equals Node's view
**196/196**. Thus the source-specific boundary, not the raw OS read, is wrong.
The compiled observer calls the existing `view_native_cwd_read` and both real
resolver seams; it does not inject a corrected resolver.

| Dimension | Executed classes |
|---|---|
| Existing child cwd | plain; plain + final backslash; extended; extended + final backslash; ordinary drive root; extended drive root; pair / lone high / lone low / embedded high, each ordinary and extended: **14** |
| Inherited `=E:` | absent; empty; matching; matching + final backslash; other drive; drive-relative; extended; extended root; UNC; extended UNC; pair; lone high; lone low; BOM: **14** |
| Inputs, provider `C:\x` | `e:leaf` (selected E drive); `\leaf` (empty device); `E:\absolute` (absolute positive); `leaf` (provider positive); `a:leaf` (different selected drive, `=A:` absent): **5** |
| Injected mapping values (not OS cwd fixtures) | ordinary and extended directory/root; UNC and extended UNC; lone high; extended lone high; pair; BOM; device namespace; forward separators: **12** |

The rejected resolver gives **770 MATCH / 210 mismatches**. All mismatches
are in the seven extended cwd classes: `e:leaf` differs with absent/empty E
entry (14 observations), `\leaf` differs for every entry (98), and `a:leaf`
differs for every entry (98). Both no-native-cwd positive inputs match in all
196 states. The reviewer's four acceptance observations reproduce exactly.
The rejected callback's own cwd-view field differs in **98/196** states.

The ordinary drive root's raw/std/Node value is `E:\`. The extended root's
raw/std value is `\\?\E:\`, while Node reports `\\?\E:`. Omitting that
trim is detected by the **native-view** observation in all 14 extended-root
states; final lexical path normalization masks it in this matrix. This is why
we distinguish operand observations from final resolver results, and do not
claim that those 14 rows reveal a second independent final-path defect.

`analysis.json` and `analyze.py` verify the archived arrays without computing a
path resolution. Four one-rule source-prediction controls have nonempty exact
failure sets against the green Node/native-boundary baseline: prefix stripping
(98 states), omitted cwd trim (14), entry prefix stripping (42), and applying
cwd trim to an inherited entry (28). These are **characterization-model
controls, not compiled production-mutant KILLED credit**. The production-fired
controls proposed below remain mandatory after agreement and a corrected green
baseline. No fix is smuggled into the characterization to obtain such a baseline.

**Disclosures.** The first build omitted the pinned ICU settings and failed.
The second attempted to read Win32 cwd directly inside the observer, and the
crate's `forbid(unsafe_code)` correctly rejected it. Neither ran native rows or
gets evidence credit. Both build logs and observer sources remain in `ce02/`
and `ce02/native-r2/`. The final safe observer and paired read-only ctypes child
are in `native-r3/`; its build and collector succeeded. Its children disable
Node compile caching and Python bytecode writes. The host window is released,
and BATCH-DONE was sent after all children and analysis exited. No Linux run,
G3 refresh, compiled-control kill, closure or certification is claimed here.

Integrity: **19 evidence blobs** are sealed in `ce02/evidence-sha256.json`,
whose SHA-256 is
`f1b146bb87c902507288ffb86d7cc8a9c80732b01f2791a083b98ef1a759d502`.
Every staged evidence blob and the ledger were independently re-read from
Git's index and hashed; all match the captured bytes. The `-text` attribute
preserves native log/JSON line endings; CRLF is not rewritten as a cleanup.

## 5. Proposed checkpoint (subject to independent agreement)

Historical proposal as reviewed. Exactly R1–R5 below were subsequently agreed
in issuecomment-6183538250; the original proposed-state block is retained as
history, not a current pending-review instruction. Current handback is §7.2.

R1. Native entry reads use section-15 view only. Native cwd reads use the exact
cwd trim in §2 followed by that view, with **no** display/provider mapping. Both
lexical fallback branches consume the same cwd operand. Logical input/provider
semantics, root parsing, lazy selection and errors remain unchanged.

R2. Permanent witnesses freeze Node observations for the reviewer's four rows,
ordinary/extended drive roots, trailing separators, plain/pair/lone-high/lone-low/
embedded-high cwd values, and absent/empty/truthy inherited entries. Exercise
the selected-drive and empty-device branches separately. Include ordinary
absolute and provider-relative positives that do not consume native cwd.
Native raw reads, the cwd view and final real-seam results are separate assertions.

R3. A finite predicate table tests the cwd helper over raw UTF-16 values:
last unit backslash or not × exact three-unit/colon-at-unit-1 exception or not ×
ordinary/extended/UNC/extended-UNC/device forms × scalar/pair/unpaired/BOM.
Include a forward-slash ending, two final backslashes, and a three-unit value
whose first unit is not a drive letter: the exception is a literal predicate,
not a drive-letter validator.
These injected rows are mapping-unit witnesses, not claims that every spelling
is a reachable host cwd. Native child rows establish reachability separately.
Inherited mapping rows assert no cwd-only trim. Native failure remains fallible.

R4. After a green corrected baseline, execute named controls on production
paths, each with a binding-side FIRED marker and an exact intended observation:

| Control | Deliberate wrong behavior | Required kill / positive boundary |
|---|---|---|
| CE02-C1 | Reinsert the provider/display prefix strip at process-cwd view, retaining the correct cwd trim and section-15 view | Both extended reviewer rows fail; their ordinary pairs remain green |
| CE02-C2 | Omit the cwd-only final-backslash operation | Extended-root/native-view and injected trim rows fail; ordinary drive root remains green |
| CE02-C3 | Apply display/provider prefix mapping to inherited entry | Exact entry-view assertions fail on extended entries; extended drive-entry final paths also fail; plain-entry pairs remain green |
| CE02-C4 | Apply cwd trimming to inherited entries | Exact inherited-view assertions fail for trailing-entry rows, no-trailing rows remain green |

C2/C4 need the native-view assertion: lexical normalization can hide a wrong
intermediate operand. A failed build, unfired control, unrelated failure or
missing baseline is INVALID, never KILLED. The existing 15 controls and their
named observations must remain runnable and green before new mutations.
These controls are proposed, not yet implementation-closure credit; no resolver
fix or compiled mutant is run before AGREED.

R5. Implementation is limited to the private native-read seam, permanent
witnesses/controls and thin recipes. Re-run full Windows then Linux Rust gates,
lower-layer regressions, canonical/native observers and controls with fresh
sources, separate gate/control targets and the §209 queue policy. Preserve all
old evidence as history. Return a new exact pushed code/docs pair for targeted
closure, then complete independent review; do not self-certify.

```text
CONVERGENCE CHECKPOINT  PROPOSED FOR IMPLEMENTATION
OPEN FINDINGS          L12D012-RUST-I001; parent L12D012-F001 remains open
ACCEPTANCE WITNESSES    reviewer four-row pair; native-r3/native-win32.json;
                       source-boundary and mapping predicate table above
NEGATIVE CONTROLS      CE02-C1..C4, compiled / named / production FIRED after
                       a green corrected baseline; old 15 controls retained
NORMATIVE DELTAS       NONE: spec, manifest dispositions and canonical80 unchanged
NEXT_OWNER             Claude, independent checkpoint review of R1–R5 exactly
```

## 6. Scope inventory: home and rooted Python

Home expansion's HOME-first choice and `from_native` use already exist at the
merged baseline `6fab91d99a39821358bc51fc0c233a3a8eff35f8`; they were not
introduced by this candidate. Node's Windows home source checks USERPROFILE
first and otherwise queries the account; it does not implement Rust's HOME-first
fallback. Empty/short-present USERPROFILE is also not the absent case.
[Bundled libuv home source](https://github.com/nodejs/node/blob/v22.15.1/deps/uv/src/win/util.c#L873-L909).
Classification: **separate pre-existing authority-parity question**, outside
this checkpoint's cwd/drive-entry correction. Report to the shared owner for
§11.8.11(c) triage and a separately bounded characterization; no home fix, new
expectation or implicit risk acceptance here. Native source selection, Unicode
decode and namespace/display mapping all belong in that inventory.

The merged Python rooted drive-less mismatch is likewise separate (Claude's
L12-D013, #235), not repaired or certified by this Rust checkpoint. The Rust branch
is nevertheless included in CE02 because it consumes the same defective cwd
callback. The shared contract is not reopened.

## 7. Agreed implementation boundary

The independent approval above authorizes R1–R5 only. The private native cwd
read now preserves the raw namespace, performs libuv's single final-separator
operation, then applies the section-15 native string view. The inherited-entry
reader applies only that view. Provider/display mappings and outgoing OS
projection are unchanged, as are the lexical resolver and canonical 80.

**POSIX operand.** This is not an unreachable fallback: a relative logical
provider cwd can cause the POSIX right-to-left resolver to request process cwd.
Node's bundled [unix uv_cwd](https://github.com/nodejs/node/blob/v22.15.1/deps/uv/src/unix/core.c#L708-L743)
reads `getcwd`, returns errors rather than guessing, and removes one final `/`
only when the byte length exceeds one. Rust's `std::env::current_dir` supplies
the native cwd; `native_units` replacement-decodes the POSIX bytes, and the
private helper retains `/` while removing one final slash from a longer value.
`getcwd` returns no final slash except for the root `/`, so this explicit trim
does not change a reachable successful POSIX read. Rust's `to_string_lossy`
and Node's UTF-8 decoder use the same maximal-subpart replacement on invalid
byte sequences; the subsequent UTF-16 native view preserves those U+FFFDs.
It does not treat a backslash as a POSIX separator. The mapping test includes
root, trailing slash, double final slash, backslash, BOM and (on Unix) an
injected invalid-byte native read. Injected spellings are values only, not
claims that getcwd naturally emits a trailing slash. Native read errors remain
fallible with their existing typed boundary mapping.

`node_native_operand.json` freezes the archived Node cwd and inherited-entry
observations. Its 196 native states parameterize only the old fixture prefix;
no resolver recomputes expected paths. The native adapter separately asserts
raw cwd, native cwd view, raw and viewed entries, and both real filesystem and
logical results. A 107-row raw-unit table checks the literal libuv predicate,
including non-drive-letter three-unit/colon roots, forward slashes, two final
backslashes, extended/UNC/device forms, valid pairs, unpaired units and BOM.
These source-derived rows are distinguished from native Node observations.

The original 15 controls retain their wrong behaviors and named witnesses.
Three anchors are mechanically reattached at the refactored read seam:
raw-native-entry now bypasses `inherited_native_view`; raw-native-cwd bypasses
the cwd view at the read callback (its named plain/lone-high witness remains
the same); cwd-read-error-panics unwraps that same callback. All other old
anchors are unchanged. CE02-C1–C4 follow those 15, never replace them.

The new controls compare exact failure sets against a green named baseline:
C1 preserves trim/decode while stripping the namespace; C2 removes only cwd
trim; C3 strips only inherited-entry namespaces; C4 applies cwd trim only to
entries. Windows runs native paired positives/negatives. On Linux, C2 is
executed on the real POSIX helper's trailing-slash witness; C1/C3/C4 target
Windows-only native branches and are NOT_APPLICABLE there, not credited kills.
Successful builds and production FIRED markers remain mandatory. Old evidence
and ledgers are preserved unchanged. No home change or Python correction is
included. Fresh gate results and the exact handback pair will be recorded below.

### 7.1 Development disclosures

The first implementation build (`83bb39e`) stopped in strict Clippy because
the test observer placed an array `.map` directly inside `json!`; the fields
were moved outside the macro. The next run (`3418ec0`) reached tests but two
new tests refused the JSON fixture: its descriptive labels contained unpaired
surrogates, which `serde_json` correctly rejects in a JSON string. Labels were
made ASCII-safe; the numeric UTF-16 operands and expectations were unchanged.
No native replay or control ran in either failed gate. Both logs are retained
as uncredited development evidence. A pre-control audit also completed C1's
five-input failure set with the `a:leaf` fallback; this was not a control kill.
At corrected head `666e7365aea2ce216a65e37662da2879273c0945`, the focused path
tests passed 9/0/1 ignored before the fresh full gate. The early chat statement
that the new tests passed in the second run was corrected immediately after
reading its final log; it is not evidence credit.

### 7.2 Exact-head implementation handback

Code #234: **`666e7365aea2ce216a65e37662da2879273c0945`**, source clean. The
code/docs pair's pushed docs SHA is bound on #229 by the kit handoff, avoiding
a self-referential docs commit. No shared expectation or normative contract
changed. Rust I001 and parent F001 remain OPEN pending independent review.

| Fresh final-head verification | Windows | Linux |
|---|---|---|
| fmt, native-fs check, strict Clippy | exit 0 each | exit 0 each |
| full workspace/all features | **696 passed, 0 failed, 1 ignored** | **688 passed, 0 failed, 2 ignored** |
| strict rustdoc, conformance verify | exit 0 each | exit 0 each |
| existing native replay | **95 MATCH + 3 REFUSED** with zero observations on each refusal | **25 MATCH** |
| CE02 frozen native replay | **196 states / 980 resolver observations**, zero mismatches; raw cwd, cwd view, raw/viewed entries and both real seams checked separately | Windows native domain, NOT_APPLICABLE; explicit POSIX source/operator witnesses instead |
| old controls, before CE02 mutations | **15/15 KILLED**, intended witnesses and FIRED | **12/12 applicable KILLED**, intended witnesses and FIRED; 3 Windows-only NOT_APPLICABLE |
| new controls | **CE02-C1..C4: 4/4 KILLED**, exact intended failure sets and FIRED | **CE02-C2 KILLED** on `posix-cwd/trailing`; C1/C3/C4 Windows-only NOT_APPLICABLE |
| restored library | **220 passed, 0 failed, 1 ignored** | **214 passed, 0 failed, 1 ignored** |
| restored native replay | existing 95 MATCH + 3 REFUSED, then full CE02 196/980 MATCH | 25 MATCH |
| uid-1000 replays | not applicable | path-domain corpus 2 passed; readonly-removal corpus 2 passed; explicit ignored permission witness 1 passed |

Schema/manifest validation: **954 passed**, exit 0, on the same code head.
This is shape validation, not a full Python implementation-gate claim. The
default ignored observer and Linux permission witness are executed explicitly;
their additional results are not folded into default full-suite counts.

C1 fails only the extended cwd view and final selected-drive/rooted/different-
drive rows; ordinary pairs and absolute/provider positives remain green. C2's
sole native failure is the extended-root cwd-view assertion, not a final-path
failure. C3 fails the extended inherited view plus the selected-drive final
paths; its matching plain entry stays green. C4 fails only the trailing entry
view; final normalization masks the difference and the no-trailing entry is
green. Each compiled mutation ran after its own green baseline. Source bytes
were restored exactly; restored runs contain no FIRED marker. Setup or build
failures were never credited as kills.

The new native replay is one Rust child per state against the **frozen Node
observations**, not a claim to have rerun the original three-child oracle
characterization. Only the archived fixture prefix is substituted. The
original 19-file characterization ledger and earlier implementation evidence
are unchanged, historical evidence at their stated heads.

Reproduction uses the committed parameterized `path-resolution-gates.py`
(Windows `--phase gates`, then `--phase controls`, NEW logs for each) and
`path-resolution-linux.ps1` (`-Phase all`, NEW logs). Targets are separate per
platform and disjoint between gates and controls; reviewers supply reviewer-only
targets. Four Cargo jobs, fresh workspace-source mtimes before every gate,
preflight, pinned Node 22.15.1/Rust 1.97.1/ICU 78.3, private executable tmpfs and
the existing pinned Linux image apply. No cache cleaning or process signal.
The pre-existing MSVC LNK4098 warning remains disclosed; all credited gate exits
are zero. Both platforms finished sequentially, the Linux container exited,
and BATCH-DONE released the host before evidence packaging.

Evidence: `data/l12-d012/ce02/implementation/`, **248 sealed files**, excluding
`SHA256SUMS` itself. Ledger SHA-256:
`7aaa607470539e80890e072265e3440730a4df42b2e7fed349600b41d389aaeb`.
The ledger is verified against staged Git blobs, not merely working copies.
`input-provenance.json` binds the clean code head and canonical/frozen fixture
hashes. Native logs are copied byte-for-byte under the existing `-text` rule.
Uncredited development logs are in separately named directories. Empty cwd
fixtures remain contained and retained; no case path is accessed as an I/O target.

NEXT_OWNER: **Claude**, independent RUST-I001 targeted closure (§11.8.7), then
the complete exact-pair review (§11.8.8). **No self-certification, merge, finding
closure or #228 rebase is authorized by these author results.**
