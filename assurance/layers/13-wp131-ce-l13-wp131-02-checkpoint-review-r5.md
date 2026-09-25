# CE-L13-WP131-02 — independent checkpoint review, revision 5

**Verdict: REJECTED** for implementation checkpoint only. This is not a complete WP-13.1 contract or Python implementation review.

## Exact review state

- Docs candidate: `minion-agent-docs#162` @ `90dddb7ea35911d339fe44037d32991e7f35778d`, open and remote-reachable.
- Frozen code candidate: `minion-agent#60` @ `61f40e4d030d09cc8ab372b6c21826733aa5ad36`, open and unchanged.
- Accepted defaults: docs `master` @ `e1d9b817096de2797df00b17f354c2ca1451629a`; code `main` @ `6dbec20a8e2a524f8c55ea9f137fe9edcfb9f960`.
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`.
- Source checked: `packages/coding-agent/src/core/tools/read.ts` (especially the abort checks at 246/249 and access/read at 248/254), `ls.ts` (abort and settlement); owner G1 decision, issue #48 comment `5822609576`; certified EXEC-008, `spec/execution.md` §12.2–12.5; current candidate `spec/tools.md` and revision-5 checkpoint.

R-G1 (failure provenance), R-G2 (directory), R-G3 (genuine capability fallback), and R-G4 (call ownership) match the owner-selected G1 structure and the certified EXEC-008 seam. W-G1..W-G14 and the listed negative controls cover the principal provenance, directory, optional capability, cancellation, and call-order distinctions. W-1..W-3 and F-1 are explicitly disclosed. I001's R-I1..R-I4 remain consistent with the Pi abort/settlement ordering; the checkpoint preserves W-I1..W-I5. These judgments are **checkpoint-only**, not provisional implementation closure.

Two live normative contradictions remain outside revision 5's proposed delta list. An independent implementation could obey one live paragraph and fail the other, so the checkpoint cannot yet become `AGREED FOR IMPLEMENTATION`.

## CE13-C005 — `CONTRACT_ASSURANCE_DEFECT` (blocking)

**Affected text:** accepted `spec/execution.md` §12.5 versus revision 5's R-G4/I001 checkpoint-249 rule and its “Normative deltas” list.

§12.5 says `Err(not_supported) -> ... go to step 3 in FALLBACK mode`, while only the `Ok` branch explicitly visits the `read.ts:249` abort checkpoint. Revision 5 instead requires that checkpoint after the completed `check_readable` call **including** its `not_supported` answer. This is an observable branch distinction, not wording alone.

**Discriminating witness:** a provider returns `Err(not_supported)` from `check_readable`; abort the signal after that answer but before `read_binary_file`. Revision 5 requires `Operation aborted` and zero content-read calls. A literal §12.5 implementation can advance directly to fallback step 3 and read content. Pinned Pi checks `aborted` after its access call returns, before MIME sniff/read (`read.ts:248–250`), supporting revision 5's placement.

**Minimal correction:** add `spec/execution.md` §12.5 to the checkpoint's normative-delta inventory and require one common checkpoint after both `Ok` and `Err(not_supported)`, before normal/fallback content work. Keep existing EXEC-008 operation semantics and certification unchanged. Pin the fallback-abort witness and a negative control in the implementation evidence plan.

## CE13-C006 — `CONTRACT_ASSURANCE_DEFECT` (blocking)

**Affected text:** current candidate `spec/tools.md`, TOOL-026 path pipeline step 5, versus revision 5 R-G4 and its “Normative deltas” list.

The path pipeline still says `file_info then read_binary_file for read`, “core operations only.” Revision 5 says the only access/content calls are `check_readable` then `read_binary_file`, and explicitly forbids `file_info`. Its delta list replaces the later “read: operation mapping” and site paragraphs but does not identify this upstream path-pipeline instruction. Leaving both live gives two inconsistent call sequences.

**Discriminating witness:** a conforming provider supports `check_readable` and `read_binary_file` but returns `not_supported` from `file_info`. Revision 5 reads normally; a literal path-pipeline implementation calls `file_info` and fails or changes the trace. W-G13 would catch the wrong call only if this normative contradiction is resolved first.

**Minimal correction:** include the path pipeline's step 5 in the normative-delta inventory and replace its `read` call sequence with `check_readable` then `read_binary_file`, leaving `ls` and the TOOL-026 path transformations unchanged. Search the active `spec/tools.md` text for any other live `file_info`-as-read-access wording while applying this correction; preserve historical assurance narrative.

## Outcome and boundary

Revision 5 remains **PROPOSED FOR IMPLEMENTATION**, not agreed. Only these narrow checkpoint/spec-inventory corrections are requested. Do not repair or merge the frozen Python implementation on this verdict; Rust WP-13.1 and Layer 14 remain unauthorized. Return the revised exact docs SHA for another §11.8.5 checkpoint review.
