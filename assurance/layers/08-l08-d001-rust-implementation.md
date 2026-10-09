# L08-D001 Rust optional prompt assembler

Status: implementation candidate; independent closure review pending. NOT CERTIFIED.

## Authority and integration

AG-024 and spec/agent.md "Optional prompt assembler" are unchanged. This is a
MINION_EXTENSION, not an invented Pi composer. Pi's agent-loop.ts constructs
the provider context from the current context's systemPrompt and tools; the
coding-agent rebuild/refresh is reference context, not an API to reproduce.

The preserved #169/#264 checkpoint is integrated with accepted code main
`c99be8e28ae8f9a54dd868d0563f11d80f36f6bb` and docs master
`db3c8934ad1015c813ba75806630d6bd424b1a08`. The separate L08-D002 correction
resolves L08D001-RUST-C001 under the Owner's Option 1 decision (#166
issuecomment-6068630928). No-assembler compatibility is against that corrected
baseline. The historical blocker record remains intact.

## Mechanism

`PromptAssembler` is a synchronous, fallible Send+Sync collaborator over
`&[Arc<ToolDefinition>]`. At most one is installed on a driver. Override presence
(including the empty string) bypasses it. Otherwise it receives the run-local
base and ordered tool snapshot; no live registry read and no lock across the
callback. The assembled owned String is computed before fallible schema capture
and `Session::record_header`. Header and provider share that system capture and
the one owned schema vector; transform_context happens after publication.

`PromptAssemblyError` is distinct from eager model lookup errors and enters the
existing run-failure settlement. A first-request failure publishes no header or
request; a later failure retains only prior headers. A non-string result is
unrepresentable through the Rust trait's `Result<String, PromptAssemblyError>`;
panic is not the error-return protocol.

## Binding witnesses

The driver tests cover absent assembler, first snapshot/order, a late registry
addition, unchanged persistent/base prompt, empty override bypass, first and later
failure, byte-identical header reconstruction and schema equality, context
replacement on a seven-request real run, and registry churn from another Tokio
task at each transform suspension. The prepareNextTurn listener retains the
unassembled base and replaces tools in alternating orders; all seven captures,
headers and provider requests agree. The existing real tool-call growth witness
also drives provider requests before/after added_tool_names and checks the newly
introduced tool appears in both assembled text and schemas.

## Controls and gates

Fresh G3 gates on the completed code candidate: Windows **624 language tests +
4 doc tests = 628 passed, 0 failed**; Linux **624 language tests + 4 doc tests =
628 passed, 0 failed, 1 existing ignored case**. Both platforms pass fmt,
workspace/all-target/all-feature clippy with `-D warnings`, strict rustdoc, and
`xtask conformance verify`. The complete canonical agent suite includes the
eight request-header documents through the real driver. No scenario count is
hard-coded by this delta.
Shared manifest/schema validation on this candidate: **856 passed**.

The nine assembler source controls and eleven existing request-header source
controls are **9/9 + 11/11 KILLED on each platform** by their intended witness
and expected assertion signature. Each batch first proves every intended
witness is selected and passing. The scripts refuse missing compile fixtures,
missing/ambiguous source anchors, compiler failures and unrelated failures;
source restoration is in `finally`. The assembler controls cover omitted
assembly, live registry use, reverse order, wrong base, stale first result,
ignored override, absent/empty confusion, ignored growth and assembly after
header publication. The last control uses the later-request failure witness.
Request-header controls revalidate publication timing, count, ordered complete
schemas, override, and schema-failure isolation after integration.

Setup failures were not counted: an initial scratch copy omitted compile-time
fixtures, and an earlier control baseline lacked the search-artifact environment.
The valid rerun added fixture preflight checks. A subsequent Windows positive
run accidentally reused a compiled schema-suppression mutant because the scratch
and candidate shared a Cargo target. Candidate source was unchanged/correct;
cleaning that crate's generated artifacts and rerunning the complete positive
gate yielded the counts above, including the schema-failure witness passing.
Linux positive and mutant targets are separate. Never reuse a control target
for candidate certification without a clean positive rebuild.

Reproduction: use Rust 1.97.1, the verified pinned ICU4C 78.3 build and identity,
Node v22.15.1 on PATH, and `MINION_SEARCH_ENGINE_ARTIFACTS` pointing at the
official artifact directory. Run the repository Rust gates, then the two
`scripts/*-negative-controls.py` runners against a complete disposable tree
(including conformance and Python compile fixtures). The Linux evidence used
`rust:1.97.1-trixie`, E:-backed Cargo/toolchain/target/log mounts, a read-only
container root and executable tmpfs `/tmp` for source/fixtures. Its minimal
toolchain's rustfmt/clippy components were installed into the E:-backed cache.

The accepted AG-025 status sync (`main 877dcde3d1d77c0e39cd37e7ef99a6246276e170`)
is also integrated. No Python or normative contract changes are included.
Python remains certified by prior approval; Rust is **NOT CERTIFIED** and this
candidate is handed to Claude for independent exact-SHA closure review.

All writable cache, target, temp and scratch locations are inside the E: project.
Linux source and mutant copies are on Docker tmpfs /tmp; target and CARGO_HOME
are E: bind mounts, not Docker named volumes.
