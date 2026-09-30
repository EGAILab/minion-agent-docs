# WP-13.2 — targeted I002 closure, remediation 2

**APPROVED for targeted closure only.** I002 PROVISIONALLY CLOSED. I001/I003 remain provisionally closed. Final complete implementation review is the next gate, not waived.

Exact code #87: `60278e6ce444005dd61128dd7633d374d209bc17`.
Exact docs #191: `da81a9f2ef0fc73dd307f837e6b2a8cc289e4c9a`.
Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`.
Prior targeted rejection: docs #193 `7403dcaf0dd8eb294a99bcaa00aef1ebeaefe0e1`, preserved unchanged.

Fetched/pruned both repositories and exact PR heads; verified issue #49 IMPLEMENTATION_REVIEW / NEXT_OWNER Codex, open ready PRs, remote reachability and isolated clean worktrees. No candidate edits. Accepted contract remains code `97d7c6bd98f2f07027e6ab1d057b3c7e6adab345` / docs `59eba17bd71888d874d85c203c3b4dc646ce3ebc`.

Independently compared pinned `edit.ts::prepareEditArguments` / JSON.parse with the normative preparation rule, then candidate `_js_integer`. The correction retains negative zero as float -0.0 rather than int 0, while preserving binary64 rounding/overflow and rejection of non-JSON constants. The representation exception is documented. No lower-layer semantic delta.

Fresh Windows CPython 3.13.5, exact candidate editable install, pinned PyICU/ICU environment:

- `python -m pytest tests/tools/builtin/test_wp132_mutation_tools.py tests/conformance/test_builtin_mutation_conformance.py -q -o addopts=`: **65 passed**.
- In-memory reversion to the exact prior `_js_integer` behavior; `-k 'sign_of_zero or negative_zero_reaches'`: **2 failed, 4 passed, 31 deselected**, as intended. Integer `-0` direct sign assertion and real TOOLS_PRE_EXECUTE hook assertion fail; -0.0/-0e0/0/0.0 controls remain passing. Clean processes restore the untouched candidate automatically.
- Independent prior-review probe now observes `-0 float -0.0 sign -1.0`, the same sign for -0.0/-0e0, and **real Layer-06 hook sign -1.0**, successful edit to `b`, agreeing with pinned Node 22.15.1 / Pi.

The source/test/doc delta is bounded to sign preservation. Previous huge-number/rounding tests, valid-surrogate witnesses, virtual-clock timer controls and all canonical documents pass. I002's previously recorded trigger-A/narrow-point-fix exception has discriminating closure, not another unresolved pass. R001–R005 remain closed; I001/I003 remain provisionally closed.

Advance issue #49 to FINAL_CONTRACT_REVIEW / NEXT_OWNER Codex for the same exact pair, with complete semantic round-trip verification. No merge, certification, Rust implementation or next work package is authorized by this targeted verdict alone.
