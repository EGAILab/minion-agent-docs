# Layer 11 — L11-R006 targeted-closure remediation (round 3): permanent typing fixture

## Review target rejected (partially) by this remediation

```text
code PR #25
    f7a754038063f35be7aa87641a29d883243475f1

docs PR #54
    8883ce6c29396d3fb0f25899aa706055c9fc63f8

review PR #58
    bc6560abf834435c0c23a426b1e70f4eccab5ff4

verdict
    L11-R008  PROVISIONALLY CLOSED
    L11-R009  PROVISIONALLY CLOSED
    L11-R010  PROVISIONALLY CLOSED
    L11-R006  STILL OPEN -- CONTRACT_ASSURANCE_DEFECT (assurance gap only)
```

## Trigger check (agent-workflow.md §11.8, mandatory)

`L11-R006` has now been raised across FOUR independent review rounds (docs PR #55, #56, #57, #58),
far past the two-repeat trigger. This is still the SAME convergence episode opened in
`11-auth-foundation-r006-r008-convergence-agreement.md`; the round-3 review confirms the
IMPLEMENTATION and its normative documentation are now correct -- "The L11-R006 implementation and
annotations are now correct, and the exact ad-hoc mypy probe passes" -- so no further
characterization/challenge/agreement cycle or owner escalation is needed. What remained open was
purely an EVIDENCE-PERMANENCE gap, not a semantic or implementation defect.

## What round 3 found

The review's own ad-hoc probe (constructing the exact mypy commands by hand and running them)
confirmed `credential.env["NEW"] = "v"` and the equivalent `extra`/scalar-field operations all
type-check correctly at the exact candidate. But: the project's CONFIGURED, PERMANENTLY-RUN gates
are `pytest` (runtime only -- Python does not enforce dataclass field types at runtime, so a
runtime test cannot distinguish `dict[str, str]` from `Mapping[str, str]`) and the default `mypy`
gate, which is scoped to `src/minion_agent` only (`pyproject.toml`'s own `[tool.mypy] files =
["src/minion_agent"]`) and therefore never type-checks anything under `tests/`. Reverting `env`/
`extra` back to a read-only `Mapping`, or re-adding `frozen=True` to either credential dataclass,
would leave EVERY one of those permanently-run, permanently-reported gates green -- the review's
own probe was correct, but it is not itself a permanent artifact anyone re-runs on a future PR.

## Remediation

New `tests/typing/valid_auth_credential_mutation.py`, following the exact established convention
`tests/typing/valid_message_construction.py`/`valid_tool_construction.py` already set: a module
mypy-checks, never imported or executed by pytest, whose only job is to fail `mypy` if any of the
covered constructions ever stop type-checking. Covers all four operations the review named:

1. `ApiKeyCredential.env` top-level key assignment (after an explicit `is not None` narrowing,
   the ordinary way a caller proves an optional field holds an actual mapping before indexing it).
2. `OAuthCredential.extra` top-level key assignment, both a flat string value and a nested JSON
   value (proving the field's own open-recursive-JSON domain is still writable, not merely
   readable).
3. `ApiKeyCredential` scalar-field reassignment (`credential.key = "B"`).
4. `OAuthCredential` scalar-field reassignment (`access`, `refresh`, `expires`, all three).

**Independently confirmed discriminating before being committed** (not merely asserted): the
credential module was temporarily reverted to `Mapping[str, str] | None`/`Mapping[str, JsonValue]`
and separately to `frozen=True`, and `mypy src/minion_agent tests/typing/
valid_auth_credential_mutation.py` was run against each reverted state:

```text
env/extra reverted to Mapping
    error: Unsupported target for indexed assignment ("Mapping[str, str]")
    error: Unsupported target for indexed assignment ("Mapping[str, JsonValue]")  (x2)

ApiKeyCredential re-frozen
    error: Property "key" defined in "ApiKeyCredential" is read-only
```

Both reverted states were then restored to the exact committed state (confirmed via `git diff`
showing zero delta) before this remediation was finalized -- the revert-and-confirm was evidence-
gathering only, never left in place.

`pi-parity-manifest.yaml`'s `PROV-006` row updated to cite the new fixture explicitly as
"permanent static-type evidence, mypy-checked only," matching the citation style already used for
`valid_tool_construction.py` elsewhere in the same manifest, including the exact run command and a
note that its discriminating power was independently confirmed rather than assumed.

## Fresh quality gates

- `pytest` (full suite, with coverage): 1278 passed, 19 xfailed (pre-existing, unrelated), 65
  skipped, 0 failed -- unchanged from round 2, confirming the new file is genuinely inert to
  pytest (never imported, does not match `test_*.py` discovery).
- Coverage: 100.00% (`TOTAL` 3127 statements, 0 missed) -- unchanged, since no `src/` file changed.
- `ruff check .`: clean, including the new fixture file.
- `ruff format --check .`: the new fixture file is itself correctly formatted; the same
  pre-existing 7-file drift elsewhere is unchanged.
- `mypy` (default gate, `src/minion_agent` only): clean, 66 source files.
- `mypy src/minion_agent tests/typing/valid_auth_credential_mutation.py`: clean, 67 source files
  -- the new permanent gate itself, passing.
- `mypy` against all three `tests/typing/*.py` fixtures together: clean, 69 source files.
- `tests/conformance/test_manifest_validation.py`: 8/8.
- `tests/test_layering.py`: 5/5 (unaffected -- no package boundary touched).
- Manual secret scan of the new fixture file: clean, no credential-shaped literal at all.

## Next action

Push the new fixture and manifest update to the same candidate branches, updating PRs #25/#54 in
place. `STATUS = RUST_CONTRACT_REVIEW` (targeted closure re-requested for `L11-R006` only --
`L11-R008`/`L11-R009`/`L11-R010` are already provisionally closed and untouched by this pass).
`NEXT_OWNER = Codex`. If `L11-R006` is provisionally closed and no other blocker remains, perform
the one final complete §11.8.8 review before any certification. Do not implement Rust yet.
