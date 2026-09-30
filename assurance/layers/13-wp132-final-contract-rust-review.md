# WP-13.2 final complete independent Rust contract review

## Exact-SHA verdict

**APPROVED — CONTRACT CHECKPOINT: AGREED FOR IMPLEMENTATION.** This is the complete contract-and-evidence review requested by issue #49 after targeted closure, not another R004-only review. No active blocking finding remains. It is not implementation certification or cross-language closure.

| Authority/control object | Verified value |
|---|---|
| Code PR #81 | `61b18f377c926bb09df97994ce91901cad37ed68` |
| Docs PR #178 | `2e520b19b2b33885def09246861178f89946fadc` |
| Pinned Pi | `b7bb00b936dbe21b8e160b3e89efdec361846699` |
| Coordination on entry | minion-agent#49: CONTRACT_REVIEW / NEXT_OWNER Codex |
| Fetched code/main | `d3c591a83759caf3cff26c62f1690781d2b08439` |
| Fetched docs/master | `148e71938ce3f1558eaf3155049a710a2b393c7a` |

Both candidates were fetched from their remote PR refs and verified open, Ready for Review and unchanged. Primary local HEADs (`4301816d6ba66f3be1d5f5b4b48fdeb46f939ac0`, `631aaabbf07891af7f7d65c1b303f5c440d925a0`) and unrelated untracked work were preserved; candidates were inspected in isolated worktrees. No candidate branch was modified.

## Independent source and contract audit

Re-read pinned `write.ts`, `edit.ts`, `edit-diff.ts`, `file-mutation-queue.ts`, `path-utils.ts`, `utils/text.ts`, and the certified tool-preflight boundary. Reviewed the complete current WP-13.2 spec, TOOL-026/029–033/039, schema, generator, hand-authored case and queue expectations, authority glue, mutation controls, current assurance and prior review history. Checked Rust's typed ToolCall, prepare/schema/preflight execution and filesystem/built-in composition seams. Neither language implementation was used as the edit/diff oracle.

| Rule | Complete review result |
|---|---|
| TOOL-029 write | Definition strings/schema, preprocessing, registration before provider awaits, in-lock absolute path, parent creation, UTF-16 length, WHATWG encoding, error provenance and abort checkpoints coherent. R001 mapping preserved. |
| TOOL-030 edit | Preparation coercions, object-valued entry, empty-edit guard, combined EXEC-009 access, disclosed unsupported-provider fallback, read/match/write order, diagnostic templates and exact diff/patch details coherent. |
| TOOL-031 normalization | Unicode 16.0 NFKC authority, exact ECMAScript whitespace, fuzzy spreading and uniqueness, UTF-16 indices, stable ordering, unchanged-line overlay, BOM/endings and both reachable INTERNAL guards match Pi. |
| TOOL-032 queue | Globally serialized registration until settlement, failure leaves no tail, provider-scoped per-key FIFO, canonical/lexical fallback set, cross-key concurrency and finally-release coherent. No Layer-12 resolve substitution. |
| TOOL-033 cancellation | Direct execute registers/waits before checking; real Layer-06 preflight handles already-aborted calls without execute. In-flight operations retain the lock; access failure checks abort first, read/write failures preserve their own error. |
| TOOL-026 / TOOL-039 | Shared preprocessing steps 1–4 retained; read-only dispatch not reused by mutations. O1 authorizes deterministic raw/hybrid site wrappers while Pi-authored stable text stays exact. Prior WP-13.1 semantics unchanged. |

Governance was independently retrieved: O1/O2 at issue #49 comment 5881558193 and standing delegation #75. Provider scoping, unsupported-provider fallback and Windows semantic access policy are disclosed architectural mappings, not universal Pi-host identity. EXEC-009 is now cross-language closed; #78 resolve behavior remains outside this work package. No new owner decision or lower-layer reopen is required.

Manifest summaries describing tool-local pre-abort behavior are read with their explicit normative TOOL-033 reference and direct execute source surface; they do not override the spec/schema's separate Layer-06 preflight rule. CONTRACT_DRAFT / not-implemented labels describe the unmerged candidate and must be synchronized through the normal accepted-milestone process, not treated as certification evidence.

## Fresh executable replay

Executed the README commands against this exact docs candidate, with read-only evidence/Pi mounts and a new output directory:

```text
docker run --rm -v <pi>:/pi:ro -v <candidate-evidence>:/evid:ro -v <fresh-output>:/out node:22.15.1-alpine sh /evid/harness/run_authority.sh
docker run --rm -v <pi>:/pi:ro -v <candidate-evidence>:/evid:ro -v <fresh-output>:/out node:22.15.1-alpine sh /evid/harness/queue/run_queue.sh
python harness/make_scenarios.py cases.json <fresh-output>/authority.json <fresh-output>/queue_authority.json <fresh-output>/scenarios
PYTHONPATH=<candidate>/minion-agent-python/src python -m pytest tests/conformance/test_schema_validation.py tests/conformance/test_manifest_validation.py -q -o addopts=
```

Runtime pins verified: Node 22.15.1, V8 12.4.254.21-node.24, ICU 76.1, Unicode 16.0; pinned source hashes and diff 8.0.4 lockfile SHA-512 integrity passed. Cases regenerate to the recorded hash `aa4d57db6998ffc078a89e26ae1141f363337c72439d08d268eb552518f2141f`.

| Fresh evidence | Result |
|---|---|
| Authority corpus | 379 results; byte-identical |
| Corpus mutants | 13/13 killed; byte-identical mutant output |
| Queue authority | 9 traces; byte-identical |
| Runtime and cases hash files | byte-identical |
| Canonical regeneration | 26/26 committed Git blobs byte-identical; 416 integration cases (373 corpus + 43 hand-authored), 11 queue documents |
| Fuzzy normalization | five-case fixture byte-identical |
| New schema | schema itself valid; all 26 documents validate |
| Shared schema/manifest tests | 292 passed, 0 failures |
| R004 refined queue probe | pinned PASS; early-answer abort-race mutant FAIL against actual candidate order assertions |

Output SHA-256: authority `e35b317e46eb4e5f72e81882eb3372f9bd9d49244de4e6808154b70e191fd941`; mutants `109d3b45967937f7943dd6b5fca28e7718b931027e264d51a9cda84171fcd53e`; queue `c197ca69c3035ed9f0c2125ac21042118c4c09067540456102872f1f2fa216f0`. Compared Git blobs, not CRLF-translated checkout bytes.

These are contract/evidence gates, not execution of an implemented write/edit library. Binding-level negative controls (filtered Unicode, native whitespace, registration/provider identity, lock retention, combined access) remain mandatory implementation evidence; this review does not pretend they have run against nonexistent production tools.

## Canonical entry and deterministic Rust runner

Rechecked all seven hand-authored case groups and eleven queue scenarios against source/site templates. Validated registration/access/read/write error ownership, abort precedence, fallback sequences, successful-result bytes and gate-forced ordering. Pre-aborted cases now require zero filesystem calls; post-preflight aborts require real registration/wait. Non-object preparation stays standalone helper evidence, not a fabricated ToolCall/schema outcome.

Rust can implement the protocol idiomatically through actual Layer-06 execution, typed ToolCall arguments and real production tools over wrapped filesystem providers. Start/poll calls in source order; drive runnable futures and outstanding provider I/O to quiescence; apply releases/aborts; require final settlement. Counted wakes/provider-operation tracking can distinguish gated waits from runnable I/O without fixed sleeps. The runner must not own FIFO/keying, perform edits, fabricate errors, or fake cancellation. Queue order assertions are gate-forced, not promises of JavaScript microtask-count identity. The new R004 pair orders A's write settlement before B's result without unnecessarily prescribing result A versus result B scheduling.

Lone-surrogate arguments remain the explicitly owned Layer-02/05 representability hazard: bindings that cannot carry them prove rejection before execute, never count an invented tool result as a pass. No change to those certified vocabularies is needed for the object-valued cases.

## Findings, closure and quality

R001–R003 remain CLOSED (registration timing, preprocessing split, failed-registration settlement). R004 is CLOSED (preflight/direct-execute distinction and discriminating early-answer control). R005 is CLOSED (object-valued ToolCall entry, helper evidence separated). Prior rejection artifacts #187/#188 and closure #189 remain historical and untouched.

Active PI_PARITY_DEFECT: none. Active CONTRACT_ASSURANCE_DEFECT: none. Active PI_BEHAVIOR_UNCERTAIN: none. No new unapproved divergence or blocking PARITY_CONSTRAINED_RISK. No semantic changes were made by this reviewer.

Contract-quality answers: no runner is authorized to simulate production semantics; no lower-layer authority is bypassed; no Python-specific mechanics are prescribed; normal/failure/cancellation entry seams are explicit; both languages can implement the contract independently. Exact diff algorithms and Unicode authority—not merely visually similar output—remain binding.

Retrospective: the repeated R004 gap illustrates why standalone helper/direct-execute authority must be checked against real guarded entry seams, and why lock retention needs an explicit result-settlement assertion rather than queue-content evidence alone. This is covered by existing thin-runner and discriminating-witness workflow rules; no new process or semantic patch is needed here.

## Handoff

**WP-13.2 complete contract + evidence: APPROVED / AGREED FOR IMPLEMENTATION at the exact pair above.** Return #49 to Claude for routine exact-head contract merges under standing delegation, verify accepted default-branch state, then Python implementation against that merged checkpoint. Any candidate-head change invalidates this final approval and requires review before merge.

Python WP-13.2: NOT_IMPLEMENTED. Rust WP-13.2: NOT_IMPLEMENTED; not authorized to start from these unmerged branches. WP-13.2 cross-language: NOT CLOSED. No merges, production implementation, subsequent work-package implementation or Layer 14 work performed in this pass.
