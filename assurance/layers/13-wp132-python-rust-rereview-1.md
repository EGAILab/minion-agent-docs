# WP-13.2 Python implementation — targeted remediation-1 re-review

**Verdict: CHANGES REQUIRED.** I001 and I003 provisionally closed; I002 partially resolved, still blocking. The conditional final complete implementation review was **not started**, because targeted closure is incomplete.

## Exact candidate and provenance

- Code #87: `28a5938da93dd4b4c7205d3dffcdc8bc82227684`.
- Docs #191: `7af0e694694ce766f202db75d1685d8f679573d7`.
- Previous rejected implementation pair: code `d81872a07b1ff83914f973e945b1469badf9f8f4`, docs `940c815c1aa91d2c5bc40da33775b02ce5e6bee3`.
- Prior review: docs #192, `6383bdaff6ab537813f51f5ab6a1637a9faa2523`; preserved unchanged.
- Accepted contract: code `97d7c6bd98f2f07027e6ab1d057b3c7e6adab345`, docs `59eba17bd71888d874d85c203c3b4dc646ce3ebc`.
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`.

Fetched/pruned both repositories and fetched both PR refs. Open, ready-for-review PR heads match the exact requested pair, and issue #49 is IMPLEMENTATION_REVIEW / NEXT_OWNER Codex with that pair. Used clean detached candidate worktrees; installed the exact code worktree into the review environment and verified `minion_agent.__file__`. No production or candidate changes made. Unrelated local/untracked work preserved.

Local primary code/docs HEADs remain `4301816d6ba66f3be1d5f5b4b48fdeb46f939ac0` / `631aaabbf07891af7f7d65c1b303f5c440d925a0`; fetched defaults at start were code `97d7c6bd98f2f07027e6ab1d057b3c7e6adab345` / docs `44858bc4abf7ff78786ab4c421db462883f78b1e`. These stale local branches were not used as candidate authority or reset.

Reviewed pinned Pi's actual `edit.ts::prepareEditArguments` and JSON.parse, the agreed string/queue/tool-prepare rules in `spec/tools.md`, builtin_mutation schema and scenarios, and then the candidate delta. Read `process/agent-workflow.md` and coordination-state rules. Scope is the three findings and their affected dependencies, not a second whole-package audit.

## Closure ledger

| Finding | Source and correction | Independent evidence | Disposition |
|---|---|---|---|
| I001 | Real queue remains production-owned; runner replaces 50 ms quiet window with a dedicated virtual-clock loop and fires timers within the disclosed 60 s horizon before gate steps | Both actual abort-listener negative controls killed at 10 ms, 500 ms and 10 s; reverting the runner observation to the prior implementation makes all four longer-timer runs fail their mutant-killing assertions | PROVISIONALLY CLOSED |
| I002 | JSON.parse numbers must be binary64; `parse_int=_js_integer` fixes huge-integer acceptance and rounding | Original 5000-digit and 9007199254740993 probes fixed; permanent tests discriminate on reversion; updated 380-case authority matches. **Integer `-0` still loses its sign** | PARTIALLY RESOLVED, STILL OPEN |
| I003 | WHATWG UTF-8 encoding combines valid high/low pairs, replaces only unpaired units | Five real-Layer-06 witnesses pass; reverting encoder makes valid-pair byte assertion fail, while unpaired/wrong-order/ordinary-astral controls still pass | PROVISIONALLY CLOSED |

The virtual runner still delegates FIFO, queue release and abort semantics to the real tool/queue implementation. It changes scheduler observation, not production behavior. Rust may use its own controlled scheduler; it must not copy CPython heap internals or the superseded wall-clock-window rule. The virtual horizon is explicit in the runner, and the updated schema states timer-aware observation. No additional queue rule or production timer is introduced by this closure.

## I002 refinement — negative zero remains observably wrong

Taxonomy: **PI_PARITY_DEFECT**. Severity: blocking. Same root finding (JSON.parse numeric decoding), not a successor ID.

Affected: `src/minion_agent/tools/builtin/edit.py::_js_integer` (lines 88–95). It reads `float(text)` correctly, then unconditionally converts every finite result to `int`. For JSON integer token `-0`, this changes negative zero to positive zero. JSON fractions/exponents use the separate float parser, so `-0.0` and `-0e0` retain the negative sign. Pi does not make that distinction.

Independent reproduction uses the actual pinned preparation function (only TypeScript annotations removed), running under Node 22.15.1:

```text
token    pinned Pi Object.is(extra, -0)   Python sign
-0       true                            +1.0 (int 0)
-0.0     true                            -1.0 (float -0.0)
-0e0     true                            -1.0 (float -0.0)
```

The Python probe also runs the real `execute_call` pipeline with a registered edit tool, valid JSON-string edits and a `TOOLS_PRE_EXECUTE` listener. That listener sees **positive** zero for integer `-0`; the edit itself succeeds and writes `b`. This is therefore an observable prepared-argument difference, not merely Python's display formatting. Extra edit keys are explicitly accepted and retained, and the already-certified pre-execution hook sees prepared validated arguments. Negative zero is representable as a Python float, as the two controls already prove. No lower-layer reopening is needed: the token arrives inside a string and is first decoded by this new preparation helper.

Minimal correction: preserve the negative sign when an integer JSON token decodes to negative zero, retaining the existing binary64 rounding/overflow behavior and constant rejection. Add a permanent direct and real-hook witness for `-0`, with `-0.0`, `-0e0`, positive zero and existing huge/rounded-number controls. An equality-only assertion is insufficient (`0 == -0.0`); assert sign or another discriminating negative-zero observation. Document the representation exception if the helper/assurance continues claiming all finite integral results become `int`.

Executable review-only probes are in `data/13-wp132-python-rereview-1/`. `negative_zero.py` reads the candidate and reports the actual Layer-06 hook value. `negative_zero.mjs` extracts the pinned preparation function and reports its result. No reference Python implementation is used as authority.

## Fresh gates and discrimination

Environment: Windows, CPython 3.13.5; exact candidate editable install, pinned PyICU 2.16.2 / ICU4C 78.3 environment. Node Docker `node:22.15.1-alpine`, source hash checks and diff 8.0.4 SRI verification.

- `python -m pytest tests/tools/builtin/test_wp132_mutation_tools.py tests/conformance/test_builtin_mutation_conformance.py -q -o addopts=`: **59 passed**. All 26 canonical documents execute through the real Layer-06 seam.
- Reversion control: load `revert_plugin.py` with `-p revert_plugin` and select `-k 'abort_listener or json_numbers or huge_json_integer or encodes_surrogates'`: **7 failed, 6 passed, 18 deselected**, as intended. Reversions are in-memory only: previous `_quiesce`, previous JSON parser, previous encoder. Failures are exactly the four longer-timer controls, two JSON tests and valid-pair encoding case. A clean process restores the actual candidate automatically.
- `python -m pytest tests/conformance/test_schema_validation.py tests/conformance/test_manifest_validation.py -q -o addopts=`: **292 passed**.
- `python -m ruff check .`: clean.
- `python -m mypy`: clean, **97 source files**.
- Pinned authority: **380 cases**, **13/13 corpus mutants killed**, **9 queue traces**. Fresh outputs are byte-identical to candidate docs' recorded outputs. SHA-256: authority `76fddb31e56a0d3443ff182853ca7bc5ec164a2cf51785766f1766cb9ed802fd`; mutants `109d3b45967937f7943dd6b5fca28e7718b931027e264d51a9cda84171fcd53e`; queue `c197ca69c3035ed9f0c2125ac21042118c4c09067540456102872f1f2fa216f0`.

Full-suite Windows/Linux counts in candidate assurance are not reported as freshly reproduced here. A final complete review is conditional on all targeted blockers closing; it is not appropriate to claim that review completed while I002 is open. Issue #86 remains unrelated. No Rust gates are claimed for a Python targeted review.

## Workflow and next action

Trigger A now fires for I002: the same JSON-number fidelity finding survives two independent reviews. Prior package history also records A/C and the earlier narrow exception. **Focused point-fix exception is explicitly justified**: the exact sign-loss conversion is established by pinned execution and a real-hook witness; the required behavior and available representation are settled; no unbounded semantic characterization or architectural decision remains. This is one numerical boundary correction, not permission to bypass convergence for an unresolved broader issue. If that correction requires changing the contract or another certified layer, stop and enter the applicable convergence/delta process.

Return issue #49 to **REMEDIATION / NEXT_OWNER Claude**, preserving R001–R005 closures, accepted contract, governance and history. I001/I003 are provisionally closed at this exact pair. Request targeted I002 correction with discriminating evidence and affected regressions; only after it closes may the final complete exact-SHA implementation review proceed. No merge, Rust WP-13.2 implementation, WP-13.3 or Layer 14 work is authorized by this review.
