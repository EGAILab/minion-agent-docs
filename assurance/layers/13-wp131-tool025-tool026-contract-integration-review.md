# Layer 13 WP-13.1 — TOOL-025/TOOL-026 contract-integration review

**Mode:** independent Rust-side contract review only. No Python or Rust implementation.

**Verdict:** **REJECTED** — the integration does not faithfully encode the already-approved
R002-A/R005-A/R010-B decisions. This verdict does not reopen their approved characterizations.

## Exact target

```text
docs PR #132
    cfbb087f93721a239486ec6fddeabfaa286f10a3

manifest PR #52
    5673c723bfef9674380680a0f81b35b59a3af1e5

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

Both candidate SHAs were fetched and verified remote-reachable before review. The coordination
issue was open, named `NEXT_OWNER = Codex`, and restricted this pass to whether the normative
integration faithfully represents already-approved convergence decisions.

## Authority/evidence checked

- owner governance source for R005-A:
  `minion-agent#48` comment `5760619717`;
- Lane A R005 characterization:
  `assurance/layers/13-wp131-ce-l13-wp131-01-read-projection-v2.md`;
- owner governance source for R002-A:
  `minion-agent#48` comment `5769645809`;
- Lane B R002 characterization revisions 2/3:
  `assurance/layers/13-wp131-ce-l13-wp131-01-r002-path-errors-v2.md` and `-v3.md`;
- owner governance source for R010-B:
  `minion-agent#48` comment `5785874487`;
- approved Lane E characterization:
  `assurance/layers/13-wp131-ce-l13-wp131-01-r010-error-projection.md` and its independent
  approval in docs PR #155 at `198aed33d48e7da5af903f359126d5a47ea675bc`;
- the complete candidate diff and surrounding normative `spec/tools.md` text;
- the complete candidate manifest diff and the unchanged TOOL-027/TOOL-028 row boundaries.

The Pi behavior behind those decisions was not re-characterized or re-litigated in this narrow
pass.

## Findings

### L13-WP131-INT-R001 — R005-A is claimed integrated while the rejected pre-decision image rule remains

**Classification:** `CONTRACT_ASSURANCE_DEFECT` (blocking)

R005-A makes pinned Photon 0.3.4 (and its corresponding WASM artifact) the semantic authority for
the full Photon-dependent observable surface: decode acceptance/rejection, orientation, BMP
conversion, the resize-path second decode, fast-path boundary, candidate search, success/failure,
MIME, dimensions, `wasResized`, and encoded data. Visual similarity or merely producing a valid
image is expressly insufficient.

The candidate nevertheless retains the opposite normative rule at `spec/tools.md:786-792`: the
exact algorithm remains `MINION_EXTENSION`/implementation-delegated, byte-identical output is not
required, and reproducing Photon exactly is said never to have been a reasonable target. The
TOOL-025 manifest row repeats the same contradiction at `pi-parity-manifest.yaml:6423-6427` while
claiming R005-A is integrated.

**Failure mode:** an independent implementation could use an unrelated decoder/encoder and still
claim conformance under the candidate text, contrary to the owner decision.

**Minimal correction:** replace the stale scope-boundary rule in both spec and manifest with the
R005-A Photon authority, version/artifact discipline, differential-corpus precondition, and
stop/return-to-owner feasibility rule. Do not describe this surface as implementation-delegated or
non-byte-authoritative where the owner decision makes exact Photon output authoritative.

### L13-WP131-INT-R002 — R002-A is conflated with R002-B and contradicts the pipeline itself

**Classification:** `CONTRACT_ASSURANCE_DEFECT` (blocking)

The approved R002-A mechanism is to call the already-certified `_file_url_to_path` conversion
directly and unwrapped so a malformed URL conversion remains a distinguishable rejection before
ordinary provider filesystem access. The platform-dependent Windows `INVALID` / POSIX `NOT_FOUND`
result belongs to R002-B's retained-literal fall-through alternative, which the owner did not
select.

The candidate correctly names the direct, unwrapped converter at `spec/tools.md:643-650`, then
immediately attaches R002-B's platform-dependent literal-path outcomes at lines 652-670. The
manifest repeats that conflation at lines 6468-6479 and even plans the two R002-B platform
scenarios. Separately, the normative pipeline at `spec/tools.md:595-606` still says all
`file://` conversion happens inside the eventual provider call through `resolve_local_path`, which
contradicts the newly-added direct pre-provider conversion rule.

**Failure mode:** two implementers can follow different candidate passages: reject at the strict
converter boundary, or suppress/fall through and classify an OS path error. Those are observably
different operations and error paths.

**Minimal correction:** make the shared pipeline explicitly perform R002-A's direct unwrapped
conversion at the decided point, remove R002-B's platform fall-through outcomes and planned tests
from the R002-A contract, and specify the R010-B projection for the actual strict-conversion
failure without routing it through an ordinary provider filesystem lookup.

### L13-WP131-INT-R003 — R010-B intentional divergence is recorded under `adopted`

**Classification:** `CONTRACT_ASSURANCE_DEFECT` (blocking)

The owner explicitly classified replacement of raw/hybrid provider text as a model-visible
`MINION_ARCHITECTURAL_MAPPING` / intentional divergence. Both modified manifest rows retain
`disposition: adopted` (`TOOL-025` at line 6448 and `TOOL-026` at line 6485) while embedding
R010-B inside their rules.

**Failure mode:** traceability reports the divergent text rule as adopted Pi behavior, defeating
the purpose of the explicit owner disposition and making later parity audits ambiguous.

**Minimal correction:** give the R010-B text mapping its own manifest row with `intentional
divergence` (or another manifest structure that unambiguously keeps it separate from the adopted
TOOL-025/TOOL-026 behaviors). Preserve the exact governance-source permalink, internal-only
`FsErrorCode` dispatch, and generated `details: {}` rule.

### L13-WP131-INT-R004 — the partial integration normatively reaches into frozen TOOL-028

**Classification:** `CONTRACT_ASSURANCE_DEFECT` (blocking)

The mechanical diff does leave the TOOL-028 section and manifest row unchanged. However, the new
TOOL-025 text says its cause vocabulary is “shared with `TOOL-028` below”
(`spec/tools.md:814-815`), and the shared TOOL-026 text assigns final error text through
TOOL-025's mapping without restricting that statement to the currently integrated `read` use.
Those are normative cross-references that partially decide TOOL-028 despite the same candidate's
status banner and coordination scope saying TOOL-028 remains frozen and `PENDING_R006`.

**Failure mode:** TOOL-028 is simultaneously “not integrated” and subject to a newly-integrated
error vocabulary, so later R006 completion cannot identify which parts of its contract were
actually frozen.

**Minimal correction:** scope the current R010-B normative text to TOOL-025/read and the
TOOL-026 behavior currently needed by that integrated surface. Defer every TOOL-028 application,
including its wrapper/template selection, until TOOL-028's own post-R006 integration.

## Checks that passed

- Candidate changes are confined to `spec/tools.md` and `pi-parity-manifest.yaml`.
- TOOL-027 and TOOL-028 manifest row boundaries are mechanically unchanged.
- R003/R004/R008 rule bodies were not rewritten by this pass.
- The manifest validator passes: `8 passed`.
- No Python or Rust implementation was added.

These checks do not override the four normative integration defects above.

## Verdict

```text
TOOL-025/TOOL-026 INTEGRATION
    REJECTED

R002-A / R005-A / R010-B characterizations
    REMAIN APPROVED

R006-C
    FEASIBILITY_BLOCKED / unchanged

Python WP-13.1 implementation
    NOT AUTHORIZED / NOT STARTED

Rust WP-13.1 implementation
    NOT AUTHORIZED / NOT STARTED

Layer 12 / WP-12.E1
    UNCHANGED

Layer 14
    NOT STARTED
```

Return only the four narrow integration repairs above to the shared-contract owner. The approved
characterizations must not be reopened, and no implementation may begin from these rejected exact
SHAs.
