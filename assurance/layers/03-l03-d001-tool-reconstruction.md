# L03-D001: request-header tool reconstruction preserves `constrained_sampling`

Layer 03 delta. Coordination issue: minion-agent#174.

**Governance.** Owner decision on `L08D002-R002`, Option 1, a separate Layer 03 delta. Recorded verbatim at
minion-agent#171 issuecomment-6071887505. It authorizes a narrowly scoped correction of certified Python behaviour.
This is not a new feature and not a Pi divergence. No unrelated Layer 03 change is authorized.

**Requirements.** `SES-009`, `SES-015`, `MINION-003`. The contract text is `spec/session.md`, "Request-header tool
reconstruction (`L03-D001`)".

## 1. The defect

`minion_agent.session.reconstruct_tools` rebuilds each `ToolSchema` from `name`, `description` and `parameters`
only. It never reads `constrained_sampling`. The tools artifact itself is correct: `record_header` stores
`ToolSchema.as_json()`, which carries the field. Only the read side loses it.

Codex found this in the L08-D002 contract review (`L08D002-R002`). A tool registered with
`constrained_sampling=False` is sent and stored as `false`, but reconstructed as absent.

## 2. Characterization (Python, unchanged `main` @ `b355bf92`)

`data/03-l03-d001/probe_python.py` drives only real seams: `record_header` into a real `ArtifactStore` and
`SessionLog`, the stored artifact bytes, and `reconstruct_tools`. It covers all eight certified states. The output
is `data/03-l03-d001/python-baseline.json`.

| State | Stored artifact equals recorded | Reconstructed equals recorded | Reconstructed `constrained_sampling` |
|---|---|---|---|
| absent | yes | yes | `null` |
| `false` | yes | **no** | `null` |
| json_schema prefer | yes | **no** | `null` |
| json_schema require | yes | **no** | `null` |
| grammar, `openai_lark` only | yes | **no** | `null` |
| grammar, `openai_regex` only | yes | **no** | `null` |
| grammar, both | yes | **no** | `null` |
| grammar, neither (`variants: {}`) | yes | **no** | `null` |

Storage is correct in all eight. Reconstruction is correct only when there was nothing to lose.

**Why the certified evidence missed it:**

- The Session canonical runner observed only `name`, `description` and `parameters` of a reconstructed tool.
- Every Session scenario and unit test used tools without `constrained_sampling`.
- `tests/agent_loop/test_request_tools.py` compares full `ToolSchema` equality, but only for a tool with the
  default state.

**History of the stored form.**

- `de2a977` (2026-08-19) added tool schemas to the header.
- `d9054fe` (2026-08-25, Layer 05) added `constrained_sampling` to `as_json`.
- So a header recorded between those dates stores tool entries without the member. The contract keeps them
  readable.

## 3. Contract

The normative text is in `spec/session.md`. In summary:

1. **Full fidelity.** Reconstruction returns every recorded model-facing field, in recorded order, each schema
   equal to the one recorded. All four `constrained_sampling` states come back. Absent and `false` stay distinct,
   and a grammar keeps exactly its formats.
2. **Historical headers.** A tool entry with no `constrained_sampling` member reconstructs as absent.
3. **No lossy reading.** A stored value outside the four states fails reconstruction. It is never normalized or
   read as absent.
   - The error kind is binding-defined.
   - So is any tolerance for extra members inside an otherwise valid config object.
   - Both are binding-defined because artifact bytes are binding-private (`MINION-003`): only the binding's own
     `record_header` writes them, and no canonical case can construct one.
4. **Storage unchanged.** The write side, stored byte form, field names and artifact hashes stay as they are. No
   new header format, store or public Session API.

This contract makes one disclosed change to error handling. Before it, Python ignored the stored member
entirely, so even a corrupt value reconstructed as absent. Under it, a corrupt value is an error. Reading it as
absent would be the lossy normalization the Owner's item 6 forbids. Every other malformed-artifact error path is
unchanged (item 8).

## 4. Canonical evidence

The Session scenario schema's `toolStub` gains an optional `constrained_sampling`. It uses the same four-state input
domain as the tool-registry schema: absent omits the key, and explicit `null` is not an alias (`L05-R006`). The
expected reconstruction uses the same form, so a lost field shows up as a missing key.

| Scenario | What it pins |
|---|---|
| `request-header-tools-constrained-sampling-states` | One header with eight tools, one per state, nested parameters, distinct descriptions. Reconstruction returns all eight, in order, unchanged. Two artifacts. |
| `request-header-tools-sampling-false-is-not-absent` | The same tool recorded absent and then `false`: two distinct tool artifacts, three in all. The later header reconstructs `false`. |

The Python runner stays observational:

- **Input:** it builds the real `ToolSchema` from the scenario input.
- **Output:** it reports the reconstructed schema's own `as_json()`, dropping only a `null` sampling to match the
  input form.

Contract-stage status in Python: both cases are `xfail(strict=True)` against unchanged `reconstruct_tools`. They
pass, as a strict XPASS, with the planned correction applied in a scratch copy. The marker is removed in the
implementation candidate.

## 5. Discrimination at the contract stage

> **Superseded recipe** (`L03D001-R001`). As first committed, this section omitted how the strict xfail
> markers were bypassed: in the scratch copy they had been removed by hand. Section 9 gives the corrected,
> self-checking recipe and its fresh results. The table below is kept as first recorded.

`data/03-l03-d001/controls.py`, run with `--contract-stage` against a scratch copy that has the planned
correction applied. It used Python 3.13 on Windows; logs stayed under `.tmp`.

| Control | Mutation | Witness | Result |
|---|---|---|---|
| field-dropped | reconstruction ignores the member again | states case | KILLED |
| false-read-as-absent | `false` decoded as absent | false-is-not-absent case | KILLED |
| absent-read-as-false | absent decoded as `false` | states case | KILLED |
| strict-prefer-replaced | `prefer` decoded as `require` | states case | KILLED |
| grammar-formats-swapped | `openai_lark` read from `openai_regex` | states case | KILLED |
| grammar-format-dropped | `openai_regex` discarded | states case | KILLED |
| tool-order-reversed | entries reconstructed in reverse | states case | KILLED |

Three controls are deferred to the implementation candidate, whose witnesses do not exist yet:

- **historical-entry-rejected:** a header with no member must still reconstruct.
- **malformed-read-as-absent:** an out-of-domain value must fail.
- **request-witness-blind:** the real provider-request integration witness.

## 6. Rust feasibility (read-only; no Rust change in this candidate)

Rust's `ToolSchema` (`llm/vocabulary.rs`) carries `constrained_sampling: Option<ConstrainedSampling>`.

- **Serde:** a custom serde form covers `false`, `json_schema` and `grammar`. `GrammarVariants` uses
  `deny_unknown_fields`, and `true` is rejected.
- **Storage:** `Session::record_header` stores the serde form of the tool vector.
- **Reconstruction:** `Session::reconstruct_header` deserializes it back to typed schemas, so every state
  round-trips already.
- **Byte form:** Rust's stored bytes differ from Python's (compact separators; an absent field omitted rather than
  `null`). That is allowed, because artifact bytes are binding-private. This contract does not change either form.

Rust's canonical Session runner (`tests/session_conformance.rs`):

- builds tools by deserializing the scenario input;
- compares `json!({"components", "tools"})` of the reconstruction, which uses the same input form;
- asserts an exact executed-scenario count of 20.

So the expected Rust work is test-only: the count becomes 22. Section 7 records the feasibility execution.

## 7. Rust feasibility execution

**What was run.** A disposable copy under `.tmp` of the candidate's `minion-agent-rust/` and `conformance/`, from the
unmodified Rust tree at the candidate base. Two lines changed in `tests/session_conformance.rs`: the file count and
the executed count, each from 20 to 22. Command: `cargo test -p minion-agent --test session_conformance` on
Windows, MSVC, pinned ICU 78.3.

**Result.** 1 test passed. All 22 Session scenarios executed, including both new L03-D001 cases, against the real
typed Rust `Session`.

Rust therefore conforms without a production change. The only Rust work is the count bump in its canonical runner,
which is test code the Rust owner makes.

No Rust file in the candidate is modified; the edit existed only in the scratch copy.

## 8. Implementation plan (after contract approval)

- **The fix:** a private decoder in `session/request_header.py`, the inverse of `as_json`'s `constrained_sampling`,
  used by `reconstruct_tools`. `null` or a missing member means absent. Anything outside the four states raises
  `ValueError`. No public API.
- **Unit witnesses:**
  - each state round-trips, by both `ToolSchema` equality and `as_json` equality;
  - a historical entry with no member;
  - each malformed shape raises, among them `true`, an unknown type, a bad `strict`, an extra member, an unknown
    format, non-string format text and non-object variants;
  - the stored bytes and artifact hash for a fixed schema are pinned to the pre-change `main` values.
- **Integration witness:** a real `AgentLoop` run with registered tools in every state. The header reconstructs
  exactly the schemas the provider request carried.
- **Regressions:** the full Python suite, including Session, artifact, header, fork, compaction and Layer 08 driver
  tests. Remove the strict xfail and run all ten controls.

## 9. Contract review 1 and remediation 1

**Review.** Codex, independent contract review 1, at code #175 @ `a2dd9996` / docs #268 @ `17982fee`. Recorded
verbatim at minion-agent#174 issuecomment-6072300545. Verdict CHANGES REQUESTED, with one finding. Accepted as
written:
- the contract semantics;
- the binding-defined malformed-value and extra-member clause;
- the canonical form and observational runner;
- the Rust feasibility claim: no production change, and the runner counts go from 20 to 22.

**`L03D001-R001`** (medium, blocking, `CONTRACT_ASSURANCE_DEFECT`). The committed `controls.py` passed no
`--runxfail`, and the candidate marks the intended witnesses `xfail(strict=True)`.
- Run as documented, every mutant's failure was reported as XFAIL, with exit 0: 0/7 kills.
- A correctly fixed baseline is a strict XPASS, so the baseline was not green either.
- The script also never established a positive baseline, or checked which assertion failed.
- Section 5's 7/7 had come from a scratch copy whose markers I removed by hand without recording it.

**Remediation 1** (`data/03-l03-d001/controls.py`):
- every pytest run passes `--runxfail`, and `PYTEST_ADDOPTS` is cleared;
- before any mutant, the selected controls' witnesses must pass unmutated, with exit 0, no error and no XPASS.
  Otherwise the run stops as INVALID;
- a kill needs pytest exit 1, failures and no errors, no XPASS, **and** the control's intended-failure
  signature in the output. For the canonical controls that signature is the scenario's
  `assert outcome["reconstructed_header"] == document["expect_reconstructed_header"]`. For the deferred
  controls it is the expected exception (`KeyError: 'constrained_sampling'`), `DID NOT RAISE`, or the
  integration witness's `assert reconstruct_tools(`;
- exit 0 is SURVIVED, and anything else is INVALID;
- the candidate itself keeps its strict xfail markers, unchanged.

**Recipe** (contract stage):
1. Copy the contract candidate's `minion-agent-python/` (without `.venv` or caches), `conformance/` and
   `pi-parity-manifest.yaml` into one scratch directory on E:.
2. In the copy, replace `src/minion_agent/session/request_header.py` with the planned correction from section
   8. Change nothing else; the strict markers stay.
3. Run `python controls.py <python> <copy>/minion-agent-python <scratch-logs> --contract-stage`.

**Fresh results** (Windows, Python 3.13, scratch on E:):
- **Planned correction applied:** `BASELINE 2 passed`; field-dropped, false-read-as-absent, absent-read-as-false,
  strict-prefer-replaced, grammar-formats-swapped, grammar-format-dropped and tool-order-reversed all
  **KILLED**, each by `1 failed` carrying the canonical assertion signature. The three implementation-stage
  controls are DEFERRED, and the run exits 0.
- **Negative check, the unchanged candidate:** `INVALID baseline: witnesses not green unmutated (2 failed)`,
  exit 1. The recipe cannot report kills against a defective baseline.

The three deferred controls, and their witnesses, remain mandatory for implementation approval.
