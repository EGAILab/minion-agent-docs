# Layer 10 — second final complete independent Rust contract re-review

**Review mode:** mandatory workflow §11.8.8 complete exact-SHA review after `L10-R008`
remediation.

## Exact review target

- code PR #20: `a7d05f26b22e1168c58578f5423d9a5c6f2ed0e3`
- docs PR #45: `7c8d8ed68d0c903b8262e82aca80537bd2267ed8`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- prior final complete review: docs PR #47 at
  `dc5b6a48eed12269a2c13f6a8bb6c008c0aa03e5`

The candidate PR heads matched coordination issue #19, were Ready for Review, open, unmerged, and
mergeable. The verdict applies only to these exact SHAs. Candidate branches, Rust production, and
Layer 11 were not modified.

## Independent authority audit

The complete review order remained pinned Pi, normative spec, manifest, canonical evidence,
certified Rust architecture, assurance, then Python as secondary evidence. The prior review's
source conclusions were rechecked against the unchanged pinned files:

- `types.ts`: `StreamFunction`, required `ProviderStreams.stream`/`streamSimple`, optional deferred
  operations, options, and handles;
- `models.ts`: `ModelsImpl` request boundaries, `MutableModels`, `createProvider`, `apiFor`,
  capability synthesis, and dispatch;
- `compat.ts`: generic API registry and `registerFauxProvider`;
- `providers/faux.ts`: registration handle and stream/deferred reference behavior;
- `api/lazy.ts`: deferred capability wrappers.

No Pi-source interpretation or normative semantic text changed in this candidate.

## Complete finding ledger

| Finding | Result |
|---|---|
| `L10-R001` | **CLOSED.** `streamSimple` is required and explicitly deferred with a public-callable Layer-11 criterion. |
| `L10-R002` | **CLOSED.** Stream, resolution, registry, and deferred subjects have coherent individual dispositions. |
| `L10-R003` | **OPEN RUST-ONLY IMPLEMENTATION DEFECT, correctly disclosed.** Rust's eager adapter-start result remains the later implementation target. |
| `L10-R004` | **CLOSED.** Schema, runner, direct canonical seam, handle grammar, and owner observation are coherent. |
| `C10-C005` | **CLOSED.** Registration-call ownership and repeatable withdrawal are implemented and evidenced. |
| `L10-R005` | **CLOSED.** Three Pi registry surfaces and scoped owner-approved Minion divergence are accurately represented. |
| `L10-R006` | **CLOSED.** `AI-032` records all four deferred operation boundaries without fabricated evidence. |
| `L10-R007` | **CLOSED.** The hidden cap is removed, directly evidenced, and now linked from `AI-028`. |
| `L10-R008` | **PARTIALLY RESOLVED — BLOCKING.** Current data is repaired, but the new permanent validator does not enforce that `tests` itself is a list. |

## Requirement and disposition audit

The current `AI-012`, `AI-028`, `AI-029`, `AI-030`, `AI-031`, and `AI-032` rules remain
Pi-grounded or explicitly mapped/deferred exactly as the previous complete review established:

- `AI-012` / `AI-028`: adopted never-raises returned-stream and adapter `stream` contract;
- `AI-029`: owner-authorized eager full-identity resolution divergence;
- `AI-030`: owner-authorized full-identity registry divergence, truthfully compared against
  `MutableModels`, compat's generic registry, and faux per-call unregister;
- `AI-031`: required `streamSimple` deferred to a public Layer-11 operation;
- `AI-032`: optional capability operations deferred with distinct low-level, Models-facing,
  mixed-API, and supported-faux outcomes.

No row counts a placeholder as satisfied evidence. Rust's open `AI-028`/`AI-030` obligations are
explicit rather than misreported as complete.

**Semantic result:** PASS.

## Canonical review

All seven Layer-10 scenarios remain language-neutral and use the real Python
`LlmService`/`MockAdapter` seam. The schema and semantic fixture validator retain exact operation,
handle, observation, and conditional behavior constraints. The runner does not implement registry
or stream semantics.

The scenario-derived call bound remains non-predictive, all nine repeated calls settle `ok`, and
`AI-028.tests` now contains `llm-service-more-than-eight-calls-settle-ok`.

**Canonical behavior and traceability result:** PASS.

## Rust architecture and implementability

The typed Rust `ModelIdentity`, `LlmRequest`, `LlmAdapter`, `AssistantStream`, `ScriptedAdapter`,
and `LlmService` remain a coherent implementation base. Rust can remove the eager expected
adapter-start channel, add repeatable per-call withdrawal/introspection, and wire the seven
scenarios without duplicating Python's token or runner mechanics. No lower certified semantic
layer must reopen. Deferred provider operations remain Layer 11.

**Rust contract implementability:** PASS.

## L10-R008 re-review

The candidate successfully repairs the observed data:

```text
manifest rows / unique ids             84 / 84
non-string or empty tests entries       0
nine-call scenario owning row           AI-028
```

It also adds five manifest tests. However, the claimed invariant is “every `tests` field is a list
of non-empty strings.” The implementation validates only members obtained by iterating
`row["tests"]`; it never asserts that the container is a list. The separate non-empty test only
uses truthiness. A scalar string therefore passes both checks because iteration yields non-empty
one-character strings.

Direct discriminating probe against the exact candidate:

```text
_load_rows -> [{"id": "X", "tests": "evidence"}]
test_every_tests_entry_is_a_non_empty_string()  PASS (wrong)
test_every_row_has_at_least_one_tests_entry()   PASS (wrong)
```

This is the same `L10-R008` `CONTRACT_ASSURANCE_DEFECT`, partially resolved rather than a new
finding. The current manifest happens to be clean, but the permanent gate explicitly requested by
the prior review does not enforce the structural contract it claims and permits the adjacent
malformation to recur silently.

**Narrow required repair:** assert `isinstance(row["tests"], list)` before iterating it, and add a
negative witness proving a scalar string container fails. Retain the existing non-empty-list and
non-empty-string checks. No manifest content, production behavior, canonical semantics, spec,
disposition, governance, or Rust change is otherwise required.

## Contract-quality answers

```text
Pi mapping correct?                                      YES
spec and manifest semantic rules agree?                  YES
canonical runner thin and language-neutral?              YES
Python behavior matches the approved Minion mapping?     YES
Rust can implement without consulting Python mechanics?  YES
lower certified layer reopen required?                   NO
manifest current contents structurally valid?            YES
permanent manifest gate enforces declared structure?     NO — L10-R008
```

## Fresh gates

```text
Python full suite                         1168 passed, 19 xfailed, 0 failed
coverage                                  100.00%
ruff                                      PASS
mypy                                      PASS, 58 source files
conformance                               334 passed, 19 xfailed, 0 failed
manifest validation module                5 passed
manifest rows / unique IDs                84 / 84
manifest malformed current entries        0
scalar tests-container negative probe      ACCEPTED incorrectly
targeted current Rust LLM tests            6 passed
```

Green current-data and behavior suites do not satisfy the incomplete permanent structural gate.

## Findings and impact

```text
PI_BEHAVIOR_UNCERTAIN       none
PI_PARITY_DEFECT             L10-R003 (current Rust only; disclosed implementation target)
CONTRACT_ASSURANCE_DEFECT   L10-R008 (partially resolved, blocking)
PARITY_CONSTRAINED_RISK     none
```

Layers 01–09 require no semantic delta. Layer 10 needs one test-only assurance correction. Layer
11 remains not started.

## Verdict

```text
shared Layer-10 contract    REJECTED @ code a7d05f2 / docs 7c8d8ed
Python Layer 10             REOPENED FOR ASSURANCE ONLY
Rust Layer 10               BLOCKED / NOT_IMPLEMENTED
Layer 10 cross-language     NOT CLOSED
Layer 11                    NOT STARTED
```

## Next action

Return to the shared/Python owner for the single `L10-R008` validator correction and its scalar-
container negative witness. Because the candidate SHA will change, another complete exact-SHA
review is required. Do not implement Rust Layer 10 and do not start Layer 11.
