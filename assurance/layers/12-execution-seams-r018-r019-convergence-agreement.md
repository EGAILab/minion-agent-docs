# Layer 12, WP-12.1 — `L12-R018`–`L12-R019` convergence characterization challenge and agreement

**Episode:** `CE-L12-01-04`
**Trigger:** `agent-workflow.md` §11.8.8 Case B — the third mandatory final complete review
(`minion-agent-docs#114` @ `aee3912fef830b42e60f301a51213a6c97d2bd1e`,
`assurance/layers/12-execution-seams-final-contract-review-3.md`) found two new blockers.
**This document performs:** the §11.8.4 challenge pass against that review's own characterization,
records the §11.10 governance-decision provenance required for `L12-R018`, and records the §11.8.5
`AGREED FOR IMPLEMENTATION` checkpoint for `CE-L12-01-04`.
**Candidate this episode is about:** code `997d22ba52b2040cf190fa3e9515c6db738aad1b` (PR #40), docs
`d0ab7b53cf16d3da17360ea5faa633a235ee8e7a` (PR #110) — REJECTED at the final-review stage; neither
is changed by this document. The coherent fix pass (§11.8.6) is a separate, later step. `L12-R001`
through `L12-R017` remain historically/provisionally closed for the exact issues they addressed;
this episode concerns only the two new findings.

---

## 1. Independent re-verification of the characterization

Every claim in the review was independently re-checked against pinned Pi source
(`b7bb00b936dbe21b8e160b3e89efdec361846699`) and the actual candidate text before being accepted.
Both are confirmed correct.

- **`L12-R018` `not_supported` fallback vs. unconditional symlink/target identity**: independently
  re-read `spec/execution.md` §4 directly. Confirmed it binds both (1) `absolute_path` fallback
  when `canonical_path` fails with `not_found` OR `not_supported`, and (2) "a symlink and its
  target therefore always share one `target_key`, for every provider, with no per-provider
  choice." For a hypothetical provider whose `canonical_path` is unsupported for every path,
  `resolve("link")` and `resolve("target")` both fall back to their own DISTINCT lexical
  `absolute_path` values -- unequal keys, directly contradicting (2). Independently re-checked
  `EXEC-003`'s own text: it states the identical fallback and then separately claims symlink
  identity "falls out of the derivation for free" -- confirmed it does NOT fall out when
  canonicalization is unsupported; this is a real, not merely stated, defect. Independently
  re-checked whether the LOCAL reference implementation this row actually certifies can ever
  produce `not_supported`: read `toFileError` (`nodejs.ts:97-121`) in full -- its `switch` covers
  `ABORT_ERR`/`ENOENT`/`EACCES`/`EPERM`/`ENOTDIR`/`EISDIR`/`EINVAL`, falling through to `unknown`
  for anything else; `not_supported` is NEVER produced. Confirmed: `not_supported` is part of the
  ABSTRACT `FileErrorCode` vocabulary (`types.ts:132-140`) that the concrete Node reference
  implementation never emits -- the contradiction is real for the WRITTEN contract (which must
  hold for any future provider, not only today's local one) but does not manifest in this row's
  own local-provider conformance evidence.
- **`L12-R019` `ExecutionWorldError` undefined public shape**: independently re-read
  `spec/execution.md` §7's `validate()` description. Confirmed it requires only that the error
  "name every pairwise-incompatible provider," with no stated field shape, no stated pair
  ordering, and no stated duplicate-label handling. `ExecutionWorldError` has no Pi source at all
  (`ExecutionWorldIdentity`/`compatible`/`validate` are all `MINION_EXTENSION`, confirmed in §7's
  own opening line) -- this is purely a shared-contract completeness gap, not a fresh Pi-behavior
  question.

No part of the characterization is rejected. Both findings are confirmed as characterized.

## 2. Challenge pass (`agent-workflow.md` §11.8.4)

**Is the Pi source mapping correct?** N/A for `L12-R018`'s SPECIFIC contradiction (an internal
spec-consistency defect, not a Pi-source claim) but the supporting fact (local provider never
produces `not_supported`) is independently confirmed above. N/A for `L12-R019` (no Pi source at
all, confirmed above).

**Is the behavior matrix complete enough to distinguish realistic wrong implementations?** Yes --
the review's own stub-provider witness for `L12-R018` and the ordered-triple witness for `L12-R019`
each name a concrete, executable discriminator.

**Are any cases implementation mechanics rather than observable semantics?** No -- both concern an
OBSERVABLE outcome (whether two `target_key` values are equal; what shape/order a validation error
exposes), not language-specific mechanics.

**Does any proposed fix silently reopen a lower certified layer?** No. Confined to
`spec/execution.md` §§4/7, `EXEC-003`/`EXEC-006`, and (for `L12-R018` only, per the governance
decision below) a narrow clarification to `design/2026-08-20-minion-agent-design.md` §7's own
bridge bullet.

**Can both Python and Rust implement the rule idiomatically?** Yes for both -- a documented
provider limitation and a structured, ordered error payload are ordinary typed-code patterns in
both languages.

**Does the defect's root cause depend on an extensibility point one language's certified lower
layer exposes and the other does not?** No -- same footing in both languages.

**Are all previous review findings represented by an executable or documentary acceptance
criterion?** Yes -- §5 below states one for each of `L12-R018`/`L12-R019`.

## 3. Governance-decision provenance (`agent-workflow.md` §11.10) — required for `L12-R018`

The review correctly flagged that narrowing the symlink/target identity guarantee touches
territory the owner's own frozen design text originates ("the same file reached by different
paths yields the same key," `design/2026-08-20-minion-agent-design.md` §7, 2026-08-20) and that no
existing governance record scoped this specific narrowing before this episode. Per §11.10, this
was NOT asserted as pre-existing owner approval. Instead, the two available options (narrow the
guarantee, source-faithful and matching Pi's own real mechanism's own always-conditional nature;
or invent a new Minion-specific alias-resolution mechanism with no Pi precedent to preserve an
unconditional promise) were presented to the owner directly in the controlling conversation, with
an explicit recommendation and reasoning (Pi's own real `getMutationQueueKey` was never
unconditional either; the "unconditional, no exception" framing was Claude's own elaboration
during the `L12-R005`/`CE-L12-01-01` remediation, not literally present in the owner's own original,
vaguer 2026-08-20 wording).

```text
GOVERNANCE_SOURCE
    Direct owner decision in the controlling Claude Code conversation, session
    https://claude.ai/code/session_01SCAEN7BDLUyZijiFfDaBFa, durably recorded here per
    agent-workflow.md section 11.10's second provenance category (an assurance-file/convergence-
    agreement record that clearly names and scopes the decision).
DECISION
    Narrow the FsTarget symlink/target target_key identity guarantee: it holds ONLY when
    canonicalization succeeds. A provider whose canonical_path is unsupported for a path is
    explicitly NOT required to alias-unify a symlink with its target -- this is a documented
    provider limitation, not a contract violation, and does not affect any current (local)
    provider, since the reference implementation never produces not_supported.
SCOPE
    Layer 12 / WP-12.1 -- spec/execution.md section 4, EXEC-003, and the corresponding frozen-
    design section 7 bridge bullet (narrow clarification only, not a re-opening of the bridge
    mechanism itself, which remains unchanged and owner-approved).
```

## 4. Design decisions

### 4.1 `L12-R018` — symlink/target identity holds when canonicalization succeeds

**Decision (per the governance record above):** the "Symlink identity is fixed, not
provider-discretionary" rule (`spec/execution.md` §4) is narrowed: `resolve(path)` and
`resolve(target_of_path)` share one `target_key` WHEN `canonical_path` succeeds for both (the
normal case for every provider this row certifies). When a provider's `canonical_path` returns
`not_supported`, `target_key` falls back to lexical `absolute_path` per the already-settled exact
fallback condition (`L12-R016`) -- a symlink and its target, being different lexical paths, get
DIFFERENT `target_key` values in that case. This is an explicit, documented LIMITATION of a
non-canonicalizing provider (it cannot alias-unify symlinks), not a contract violation -- a future
Layer 13 consumer relying on alias unification for correctness must document that it requires a
canonicalization-capable provider. `EXEC-003`'s "falls out of the derivation for free" claim is
corrected to state this conditionally. `design.md` §7's own bridge bullet gains a one-clause
clarification (narrow, matching the governance scope above): the "same resolved location" guarantee
assumes a canonicalization-capable provider, exactly as `spec/execution.md` §4 now states in full.

### 4.2 `L12-R019` — `ExecutionWorldError` concrete payload

**Decision:** `MINION_EXTENSION`, no Pi source. A minimal, ordered, structured payload:

```text
ExecutionWorldError
    incompatible_pairs: ordered list of {left: str, right: str}
        -- one entry per pairwise-incompatible combination found among the providers passed to
           validate(), enumerated in the SAME relative order the caller supplied them: for input
           index i < j, an incompatible pair appears as {left: name[i], right: name[j]} (never the
           reversed order) -- deterministic, independent of implementation or provider order
           beyond what the caller itself supplied
    -- caller-supplied labels (the "name" in each (name, identity) tuple passed to validate()) MUST
       be unique within one validate() call; a duplicate label is a caller precondition violation
       (undefined behavior for this primitive), not a case ExecutionWorldError itself represents
    -- any human-readable message text a provider or runtime attaches is NON-NORMATIVE --
       implementations MAY include one for diagnostics, but callers and canonical normalization
       MUST NOT depend on its exact wording; incompatible_pairs is the sole normative payload
```

## 5. Acceptance witnesses (one per finding, discriminating)

```text
L12-R018  setup: a stub provider whose canonical_path returns Err(not_supported) for every path;
          resolve("link") and resolve("target") (link a symlink to target, by the provider's own
          semantics, though this provider cannot canonicalize to prove it)
          expected: target_key("link") != target_key("target") -- UNEQUAL, explicitly documented
          as this provider's own limitation, not a contract violation
          second setup: same stub provider; resolve("link") called twice for the identical path
          expected: EQUAL target_key both times -- stability for repeated resolution of the SAME
          path still holds even without canonicalization (this was never in question)
          negative control: a candidate asserting target_key("link") == target_key("target") for
          a not_supported provider is WRONG under this agreement; a candidate asserting a
          canonicalization-capable provider's own symlink/target keys may legitimately differ is
          ALSO wrong -- the guarantee still holds unconditionally for canonicalization-capable
          providers, which is every provider this row certifies today

L12-R019  setup: validate([("fs", A), ("shell", B), ("subprocess", C)]) with A/B incompatible,
          A/C incompatible, B/C compatible
          expected: Err(ExecutionWorldError{incompatible_pairs: [{left:"fs",right:"shell"},
          {left:"fs",right:"subprocess"}]}) -- exactly these two entries, in input-index order
          second setup: validate([("a", X), ("a", Y)]) -- duplicate label "a"
          expected: undefined behavior (caller precondition violation) -- not a case this
          primitive is required to represent in its own Result
          negative control: an implementation returning only a human-readable string, or an
          unordered set, or pairs in a different order than input-index i<j, fails this witness
```

## 6. Normative deltas required (coherent fix pass, next step -- not performed by this document)

```text
design/2026-08-20-minion-agent-design.md section 7
    -- one-clause clarification only (per the governance record above): the "same resolved
       location" bridge bullet gains an explicit "for a canonicalization-capable provider"
       qualifier, matching spec/execution.md section 4's own full statement.

spec/execution.md
    -- section 4: narrow the symlink/target identity guarantee to the canonicalization-succeeds
       case, per section 4.1 above;
    -- section 7: add the concrete ExecutionWorldError payload shape from section 4.2 above;
    -- section 9: add a round-5/CE-L12-01-04 remediation record entry;
    -- section 10: extend the witness matrix with section 5 above's entries.

pi-parity-manifest.yaml
    -- EXEC-003: rule text narrowed to the canonicalization-succeeds-conditional symlink/target
       guarantee (section 4.1 above);
    -- EXEC-006: rule text updated with the concrete ExecutionWorldError payload (section 4.2
       above).
```

## 7. Convergence contract

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION

EPISODE
    CE-L12-01-04

OPEN FINDINGS
    L12-R018 L12-R019

ACCEPTANCE WITNESSES
    section 5 above (one per finding)

GOVERNANCE
    section 3 above (required for, and satisfied for, L12-R018 only)

NORMATIVE DELTAS
    design/2026-08-20-minion-agent-design.md section 7 (one-clause clarification only)
    spec/execution.md sections 4, 7, 9, 10
    pi-parity-manifest.yaml EXEC-003, EXEC-006

NEXT_OWNER
    Claude (coherent fix pass, agent-workflow.md section 11.8.6)
```

This checkpoint means the remaining observable surface is sufficiently characterized for one
coherent implementation-of-the-contract pass -- it is NOT final contract approval. A targeted
closure review (`agent-workflow.md` §11.8.7) of the resulting exact candidate, with the negative-
control evidence required by §11.8.7.1, remains mandatory before another `FINAL_CONTRACT_REVIEW`.
No Python or Rust Layer 12 implementation, and no Layer 13 work, is authorized by this document.
