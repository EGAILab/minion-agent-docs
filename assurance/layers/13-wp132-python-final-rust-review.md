# WP-13.2 — final complete Python implementation review

Verdict: **CHANGES REQUIRED — cross-layer readiness blocked**. No new Python parity defect was found. I001/I002/I003 remain provisionally closed; new I004 requires a narrow lower-layer delta decision before Rust-readiness approval. No merge or Rust implementation is authorized by this review.

## Exact target and authority

- Code PR #87: `60278e6ce444005dd61128dd7633d374d209bc17`.
- Docs PR #191: `da81a9f2ef0fc73dd307f837e6b2a8cc289e4c9a`.
- Accepted contract: code `97d7c6bd98f2f07027e6ab1d057b3c7e6adab345`, docs `59eba17bd71888d874d85c203c3b4dc646ce3ebc`.
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`.
- Targeted I002 closure: [review record](13-wp132-python-rust-rereview-2.md), commit `9d7752daccdfcda93b5d43d56bc7c84eb4b731dc`. Prior #192/#193 review records preserved unchanged.

Fetched/pruned both repositories, verified remote-reachable exact heads, OPEN/ready PRs and issue #49 ownership. Used isolated exact-SHA worktrees. Read pinned write.ts, edit.ts, edit-diff.ts, file-mutation-queue.ts and utils/text.ts before reviewing normative tools rules, manifest, canonical evidence, certified Rust seams, assurance and Python implementation. No candidate production/semantic files were edited.

## Complete audit ledger

| Surface | Independent result |
|---|---|
| TOOL-026 shared preprocessing | Approved preprocessing/path rules retained; no new read-specific admission into write/edit. |
| TOOL-029 write | Registration/lock ordering, abort checkpoints, parent creation, UTF-8 conversion, size and result projection agree with the adopted contract. Valid surrogate pairs encode correctly. |
| TOOL-030 edit preparation/exact matching | JSON.parse binary64 rounding, overflow and signed zero now agree on Python; legacy/string/object preparation, extra fields, validation and exact-match ambiguity audited. Runtime overflow exposes I004 below. |
| TOOL-031 fuzzy/BOM/line endings/diff | Unicode-16 filtered NFKC, whitespace/punctuation normalization, one fuzzy-mode decision for the call, touched-line rewriting, BOM/line-ending restoration and pinned diff behavior agree. |
| TOOL-032 queue | Provider scope plus canonical/fallback key, serialized registration, failed registration, FIFO release on error/abort and cross-path behavior agree. Runner virtual-clock quiescence is explicit, not a production queue substitute. |
| TOOL-033 cancellation | Layer-06 preflight distinguished from execute-time registration/lock checks; waiting abort does not answer before earlier write settles. |
| TOOL-039 errors | Owner O1 mapping retained; hand-authored Pi templates and deterministic raw/hybrid site wrappers remain distinct. |
| EXEC-009 dependency | Certified combined access capability and owner O2 fallback consumed; no change to existing filesystem semantics. |
| Manifest/canonical | Seven Python evidence-field changes, no new Rust implementation claim or disposition change. Scenario and schema additions are consistent with the adopted rules. |

R001–R005 prior closures and O1/O2 governance remain intact. I001 timer-aware quiescence, I002 integer precision/overflow/negative zero, and I003 valid-surrogate encoding do not regress. The exact earlier integer conversion kills the two new negative-zero witnesses (2 failures, four controls passing). This does not prove the whole cross-language seam is representable.

## Fresh evidence

Windows CPython 3.13.5; editable install explicitly verified against the exact candidate. PyICU 2.16.2 / verified pinned ICU4C 78.3 environment.

| Gate | Fresh result |
|---|---|
| Full pytest | 2230 passed, 16 skipped, 19 pre-existing xfailed, zero failed; 100% coverage, 6483 statements |
| Focused production/canonical WP-13.2 | 65 passed |
| Schema/manifest validation | 292 passed |
| Ruff check | Clean |
| Mypy | Clean, 97 source files |
| Candidate-scoped format check | 22 files formatted |
| Whole-project format check | Nine unchanged pre-existing files would reformat; 239 formatted; no candidate-changed file flagged |

Linux counts in the candidate assurance are not presented as independently rerun here. Existing issue #86 remains separate; its POSIX test and source are unchanged.

Replayed actual candidate authority harness in pinned `node:22.15.1-alpine`, verifying Pi file hashes and diff 8.0.4 SRI: **380 authority cases, 13/13 mutants killed, nine queue traces**. Generated outputs byte-identical to candidate:

```
authority 76fddb31e56a0d3443ff182853ca7bc5ec164a2cf51785766f1766cb9ed802fd
mutants   109d3b45967937f7943dd6b5fca28e7718b931027e264d51a9cda84171fcd53e
queue     c197ca69c3035ed9f0c2125ac21042118c4c09067540456102872f1f2fa216f0
```

Regenerated **26/26 canonical scenario Git blobs and the fuzzy-normalization fixture byte for byte** from candidate evidence. Inventory: 374 corpus cases, 43 hand-authored cases, 11 queue scenarios and five fuzzy probes. Canonical adapters dispatch real Layer-06/tools/queue operations; they do not implement those algorithms themselves.

## L13-WP132-I004 — prepared arguments exceed certified Rust runtime value domain

**Taxonomy:** CONTRACT_ASSURANCE_DEFECT. **Severity:** blocking cross-language implementation readiness. **Affected seam:** Layer-05 preparation and Layer-06 validation/pre-execution hook arguments, as consumed by TOOL-030.

Valid outer ToolCall arguments contain `edits` as a JSON **string**. That string can contain an otherwise irrelevant numeric extra field with 5000 decimal digits (or `1e999`). Pi's `prepareEditArguments` uses JSON.parse, producing runtime positive Infinity, retaining the extra field. The hook sees the prepared object. Python now does this correctly: the independently executed real Layer-06 hook reports `inf`, `math.isinf=True`, and edit succeeds changing `a` to `b`.

This is not invalid outer Layer-02 JSON, a bare non-JSON Infinity input, or merely a serialization preference. Infinity is created *after* admitted string input is prepared.

Certified Rust source at the exact code candidate:

- `crates/minion-agent/src/tools/definition.rs:72–73`: `PrepareArguments = Arc<dyn Fn(Value) -> Result<Value, ToolCapabilityError> ...>`.
- The execution request parameters are also `Value`.
- `crates/minion-agent/src/tools/execution.rs:160`: `BeforeToolCallContext.arguments: Value`; other hook contexts likewise use `Value`.
- Lines 804–849: prepared parameters pass into certified schema validation and then hooks through that same domain.
- Locked serde_json version: **1.0.140**.

The isolated Rust probe with that exact dependency produces:

```
same valid edits JSON: number out of range at line 1 column 5037
Infinity as serde_json::Number: None
negative zero as serde_json::Number: Some(Number(-0.0))
```

Thus the signed-zero fix is representable, but the overflow value is not. Substituting null/string, dropping the extra, rejecting the call, or bypassing preparation/hook dispatch changes observable Pi semantics. A runner-only workaround would mask the defect. Arbitrary-precision raw-number retention alone would not establish an IEEE-754 Infinity runtime hook value either.

Review probes are preserved under [data/13-wp132-final-review](data/13-wp132-final-review/README.md). The Pi authority's new huge-integer case corroborates successful execution; the source-derived preparation probe additionally verifies `extra === Infinity`, and the Python real-hook probe verifies visibility at the actual lower-layer boundary.

### Minimal required next action

Escalate under workflow §11.7 for the **narrow affected Layer-05/06 prepared runtime argument-domain delta**. Characterize input versus prepared/runtime number domains and authorize a coherent, typed cross-language seam capable of preserving the already-adopted Pi value through preparation, validation and hooks. Do not change Python back to rejection/null or erase the canonical overflow witness to fit Rust.

The post-certification delta trigger in `implementation-conformance-workflow.md` §4 applies: historical certification is preserved; only affected semantics require delta audit, independent reproduction and revalidation. This is not permission to restart all lower-layer audits, alter Layer-02 admitted input, or begin an opportunistic Rust API rewrite. Owning-layer delta IDs and scoped remediation must be established through that process. No such implementation is authorized here.

## Contract quality / convergence / outcome

- Runners do not replace production algorithms; quiescence is bounded and disclosed.
- No new Python workaround or event-order projection mismatch was identified.
- Independent Rust cannot preserve the required overflow hook value through its existing certified public seam. Two implementations using the currently specified/certified boundary can differ observably. This is the blocker, not a demand to port Python mechanics.
- Existing package convergence trigger history remains in force. I002's bounded sign-loss exception has discriminatory closure. I004 is **not** another sign-loss point fix; the lower-layer domain needs a characterization/challenge checkpoint after the owner resolves the genuine lower-layer governance question.
- No PI_PARITY_DEFECT or PI_BEHAVIOR_UNCERTAIN newly found. One active CONTRACT_ASSURANCE_DEFECT: I004.

Record issue #49 as **BLOCKED_FOR_OWNER**, with exact candidate pair and review evidence, pending the scoped lower-layer decision. I001/I002/I003 remain provisionally closed, not relitigated. No candidate merge, Rust WP-13.2 implementation, cross-language certification or later work-package start.
