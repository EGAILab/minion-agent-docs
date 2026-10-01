# WP-13.2 evidence: pinned-Pi authority, corpus negative controls, queue traces

This directory is the evidence that `spec/tools.md` WP-13.2 "Witnesses and differential evidence" requires before implementation approval (`minion-agent#49`). Every expectation comes from pinned Pi, executed unmodified. Neither binding is an authority.

All files here are byte-exact (`.gitattributes`: `-text`). The hashes below hold on every checkout.

## Pins

| Pin | Value |
|---|---|
| Pi | `b7bb00b936dbe21b8e160b3e89efdec361846699`; the source files are checked against `harness/pi_sources.sha256` and `file-mutation-queue.ts` sha256 `33cb06ac9bcdf32c8b84d9d12e33be44c503a7670f668e003a3262cd34294d11` |
| Runtime | `node:22.15.1-alpine`. Node v22.15.1, V8 12.4.254.21-node.24, ICU 76.1, Unicode 16.0; checked at start, recorded in `out/runtime.txt` |
| `diff` | 8.0.4, fetched with `npm pack`; its SHA-512 must equal the integrity in pinned Pi's `package-lock.json`: `sha512-DPi0FmjiSU5EvQV0++GFDOJ9ASQUVFh5kD+OzOnYdi7n3Wpm9hWWGfB/O2blfHcMVTL5WkQXSnRiK9makhrcnw==` |
| Corpus | `cases.json`, regenerated deterministically by `harness/make_cases.py` (seeded). Its sha256 must equal `cases.sha256`: `4fd3578ca1d5264cc0fe23fb9bbdde11bceccded7bd478eb893c4d01c93c18c7` |

## Reproduce

These commands need a pinned Pi checkout at `b7bb00b9` (LF line endings) and Docker. Nothing is installed on the host.

```sh
docker run --rm -v <pi>:/pi:ro -v <this directory>:/evid:ro -v <out>:/out node:22.15.1-alpine sh /evid/harness/run_authority.sh
docker run --rm -v <pi>:/pi:ro -v <this directory>:/evid:ro -v <out>:/out node:22.15.1-alpine sh /evid/harness/queue/run_queue.sh
python harness/make_scenarios.py cases.json out/authority.json out/queue_authority.json <minion-agent>/conformance/agent/builtin-mutation
```

- The first run writes `authority.json` and `mutants.json`.
- The second writes `queue_authority.json`.
- All three must be byte-identical to `out/`.
- The third regenerates the canonical scenarios, which must be byte-identical to the code repository's.

## 1. Edit/write authority (`harness/edit_authority.mjs`)

`edit_authority.mjs` runs pinned Pi's own code:
- **`edit-diff.ts`**: `applyEditsToNormalizedContent`, `detectLineEnding`, `normalizeToLF`, `restoreLineEndings`, `normalizeForFuzzyMatch`, `generateDiffString` and `generateUnifiedPatch`.
- **`utils/text.ts`**: `splitBom`.
- **`diff` 8.0.4**, underneath those functions.

Pi's own source files are never modified.

The glue between those functions is `edit.ts`'s and `write.ts`'s `execute` bodies, verbatim apart from I/O:
- file bytes come from the case;
- the written bytes are returned instead of written.

`prepareEditArguments` and `validateEditInput` are copied verbatim, because `edit.ts` imports the TUI. For prepare cases, the prepared value is checked against `edit.ts`'s TypeBox schema. Only the verdict is recorded: the rejection text is Layer 06's.

**Corpus: 380 cases.**

| Kind | Cases | What they exercise |
|---|---|---|
| edit, curated | 60 | spec rules; see below |
| edit, seeded random | 300 | differential breadth |
| `prepareEditArguments` coercions | 10 | argument preparation, including a JSON number beyond binary64 (`L13-WP132-I002`) |
| write | 5 | written length and bytes |
| `normalizeForFuzzyMatch` | 5 | fuzzy normalization |

The curated edit cases cover:
- exact and fuzzy matching, and fuzzy mode spreading to every edit in the call;
- duplicates counted in fuzzy space, including the empty-normalized `split("")` count over astral text;
- overlapping and adjacent edits;
- `NO_CHANGE` in both singular and plural forms;
- CRLF/LF/lone-CR mixtures, BOM files, and files without a final newline;
- trailing whitespace, quotes, dashes and special spaces;
- NFKC composition, U+1CCD6 (Unicode 16.0 vs 15.1) and U+A7F1 (Unicode 17.0, must stay unchanged);
- the JavaScript whitespace set against NEL and U+001C;
- line groups, astral characters in every position, and large Myers diffs.

**Outcomes reached** (each of the 375 non-fuzzy cases counted once; the singular/plural split follows the templates):

| Outcome | Count |
|---|---|
| edit success | 143 |
| write success | 5 |
| `OVERLAP` | 57 |
| `NOT_FOUND` | 13 singular + 44 plural |
| `DUPLICATE` | 25 + 73 |
| `EMPTY` | 1 + 4 |
| `NO_CHANGE` | 1 + 1 |
| INTERNAL (range) | 1: an empty file whose `oldText` is only whitespace |
| INTERNAL (line count) | 2: see finding below |
| empty `edits` (`validateEditInput`) | 1 |
| prepared value fails the schema | 4 |

**Finding (recorded for the contract, no contract change): the line-count INTERNAL guard IS reachable in pinned Pi.**
- Under fuzzy mode, a final whitespace-only line without `"\n"` trims to nothing. `lines()` drops an empty final segment, so the base has one line fewer than the original.
- Cases `internal-line-count-whitespace-only-last-line` and `internal-line-count-crlf-whitespace-last-line` show this. Each is a benign edit (a smart quote forces fuzzy mode) that Pi rejects with `"Cannot preserve unchanged lines because the base content has a different line count."`.
- The contract already reproduces both INTERNAL texts "if reached". These cases pin that they are.
- Separately, NFKC under the pinned runtime never changes the number of `"\n"` at any code point (checked over all 1,112,064 scalar values). This source of a line-count mismatch is therefore excluded.

## 2. Corpus negative controls (`harness/mutants.mjs`, `out/mutants.json`)

Each control is a single-point mutant of a COPY of the pinned sources, run over the same corpus. A mutant is killed when it changes at least one result. **13/13 killed:**

| Mutant | Source | Cases changed |
|---|---|---|
| exact-only uniqueness counting | `edit-diff.ts` `countOccurrences` | 56 |
| fuzzy only when every edit needs it (not per call) | `edit-diff.ts` | 18 |
| trailing-whitespace trim of space/tab only | `edit-diff.ts` | 2 |
| NFC instead of NFKC | `edit-diff.ts` | 40 |
| line endings never restored | `edit-diff.ts` `restoreLineEndings` | 30 |
| lone CR not normalized | `edit-diff.ts` `normalizeToLF` | 2 |
| unchanged lines not preserved under fuzzy | `edit-diff.ts` | 24 |
| adjacent edits treated as overlapping | `edit-diff.ts` | 7 |
| BOM dropped on write | `edit.ts` glue | 7 |
| write reports UTF-8 bytes | `write.ts` glue | 3 |
| Myers tie-break `<=` | `diff/libesm/diff/base.js` | 7 |
| patch context joining at `< 2*context` | `diff/libesm/patch/create.js` | 1 |
| no `\ No newline at end of file` marker | `diff/libesm/patch/create.js` | 62 |

The remaining controls are binding-level, so they are run against each implementation at its own review. The spec's list names:
- Unicode 15.1/17.0 NFKC, killed by U+1CCD6 and U+A7F1;
- the binding's native whitespace set, killed by NEL, U+001C and U+FEFF;
- a non-serialized registration;
- a queue without provider scoping;
- abort-listener release;
- a two-probe access check.

## 3. Queue authority (`harness/queue/`, `out/queue_authority.json`)

Pinned `file-mutation-queue.ts` runs unmodified, under `--experimental-strip-types`. A loader hook (`loader.mjs`) gives that one module a `node:fs/promises` whose `realpath` is scripted per invocation (`fs_shim.mjs`). Everything else is re-exported unchanged.

Each scenario gates `realpath` answers and critical sections, and records the exact event trace. There are 9 scenarios:

| Scenario | What the trace shows |
|---|---|
| same-target registration in call order | B's `realpath` starts only after A's settles |
| slow failing registration | B's `realpath` starts only after A's `EACCES` settles, then B proceeds |
| different keys | the two critical sections run concurrently |
| release after a throw | the next call on the key proceeds |
| `ENOENT` fallback key | calls serialize on the fallback key |
| `ENOTDIR` fallback key | calls serialize on the fallback key |
| another error | the call fails registration and leaves no entry |
| symlink and target | they share one queue |
| FIFO of three | calls on one key run in order |

Every queue scenario in the code repository cites the trace whose ordering it asserts.

## 4. Canonical scenarios (`harness/make_scenarios.py`)

These live in `minion-agent` `conformance/agent/builtin-mutation/` and use the shape `conformance/schema/builtin-mutation-scenario.schema.json`. There are 26 documents:
- 8 corpus documents with 374 cases (the non-object `prepare-not-an-object` input stays prepare-helper evidence, `L13-WP132-R005`);
- 7 hand-authored case documents with 43 cases;
- 11 queue scenarios.

**Corpus scenarios** (`builtin-edit-corpus-*`, `builtin-write-corpus`) are mechanical conversions of §1. Each case gets:
- its own fixture file;
- the raw arguments;
- pinned Pi's result text, final file bytes and details, verbatim.

A prepare case whose prepared value fails the schema expects Layer 06's argument-validation failure.

The two cases with unpaired surrogates are flagged `unpaired_surrogate_arguments`. This is the Layer 02/05 hazard the spec records.

**Hand-authored scenarios** follow pinned Pi's `write.ts`/`edit.ts` control flow and the contract's templates. They cover:
- write's success and parent creation;
- every write and edit error site;
- the EXEC-009 FALLBACK in both forms;
- cancellation checkpoints for both tools;
- 11 queue scenarios.

The queue scenarios cover:
- R001 call order;
- FIFO;
- different keys;
- R003 settle-then-proceed with no lingering entry;
- release after an error and after an abort;
- the abort-holds-lock case;
- symlink sharing;
- provider scoping;
- the not_found fallback;
- the not_directory fallback, which is NOT `resolve()`;
- write and edit sharing one queue.

**`conformance/agent/fixtures/wp132-fuzzy-normalize/fuzzy_normalize.json`** holds the 5 `normalizeForFuzzyMatch` results. Each binding replays them against its own `fuzzy_normalize`.
