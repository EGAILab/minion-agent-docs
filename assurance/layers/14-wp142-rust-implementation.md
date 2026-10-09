# WP-14.2 — Rust implementation candidate

Status: Rust implementation candidate; independent Claude closure review pending.
Python WP-14.2 is certified by the previously recorded independent review and
merges. Rust is not certified by this implementation record; cross-language
WP-14.2 is NOT CLOSED. Coordination: minion-agent#159.

## Authority and provenance

Behavioral authority is pinned Pi
`b7bb00b936dbe21b8e160b3e89efdec361846699`, harness
`packages/agent/src/harness/{system-prompt,skills}.ts`. The coding-agent
`{system-prompt,agent-session}.ts` files are reference only for the adopted
normalizers, rendering order and read gate; their product text is not adopted.
The merged `spec/harness.md` WP-14.2 section governs HAR-002 and HAR-014..018,
including the scalar-value string domain and the Owner's architectural mappings.
Python production code was not used as an implementation oracle.

The short-lived Rust branch starts from remote main
`584ca1a79e196f6f59385754d9030f1158469d08` (approved L08-D001 Rust), then
integrates main's L08-D001 certification status sync `232dd8ef`. The assurance
branch starts from remote master `797cf1ac8273b982d65ef7ccc32dc6ed4ebb0026`.
Both contain the approved WP-14.2 contract and Python merges, certified WP-14.1,
L08-D002 and the L08-D001 implementation. Authorization/handoff is
minion-agent#159 issuecomment-6080034533.

## Mechanism and boundaries

- `system_prompt` exports the three formatters and a small configuration/composer.
  It does not read a registry or filesystem, execute tools, add a YAML API, invent
  a prompt DSL or include Pi's unadopted product text.
- Skills keep input order and duplicates. The disabled filter, five XML escapes,
  exact fixed lines, unescaped invocation, additional-instruction rule and dirname
  branches are literal implementations of the adopted harness semantics.
- `dirname` uses the certified FsPath's UTF-16 units. In particular the astral
  `😀:\b.md` witness distinguishes a code-unit index from a scalar index.
  Within the supported scalar domain FsPath display preserves addressed spelling;
  no OS projection, normalization, lossy replacement or carrier widening occurs.
- Additive ToolDefinition `prompt_snippet` / `prompt_guidelines` remain optional
  private fields with builders/accessors. They do not enter ToolSchema or change
  execution, identity, lookup, validation or permissions. Normalization uses the
  existing certified ECMAScript trim set, not Rust's broader whitespace set.
- `SystemPromptComposer` implements the certified L08-D001 PromptAssembler, using
  only its base and ordered Arc<ToolDefinition> slice. Thus metadata, exact `read`
  gating, provider schemas and header schemas use the driver's one snapshot.
  The driver production implementation is unchanged.
- Configuration supply copies list membership. Skills are retained writable
  `Arc<RwLock<Skill>>` handles. Whole-value replacement publishes one Arc, captured
  once at assembly entry; locks are not held across lower-layer calls. Records are
  read during assembly, so between-request edits are visible next time. Concurrent
  mutation by another OS thread remains outside the shared contract.
- The composer is synchronous and total over valid inputs. The existing driver
  handles overrides (including empty overrides), header publication and failure
  through its certified assembler seam, without a second registry or authority.

## Canonical and integration evidence

`tests/prompt_assembly_conformance.rs` is a thin typed adapter over all 66 JSON
documents: skills block 10, invocation 27, tools section 16, composition 13.
It schema-validates and compares exact strings returned by the real Rust APIs.
The adapter's initial serde_json parse rejects unpaired surrogate escapes anywhere
in a document (including ignored pi_reference fields and keys), combines valid
pairs and accepts literal astral characters. Preflight does not sanitize input.

Three real-driver witnesses in `agent_loop/driver.rs` cover:

1. Exact composed prompt including astral text, metadata/schema isolation,
   membership isolation, retained writable skill mutation, whole-configuration
   replacement, real ArtifactStore/header reconstruction, invocation message
   serialization/reload and typed Session derive_messages.
2. Registration after run start excluded from prompt and schemas; real
   added_tool_names growth included in both; run-local base/tool replacement.
3. Real prepareNextTurn replacement of base, tools and configuration before the
   next provider request; read gate follows that same replacement. Header and
   provider system bytes and schemas remain identical; the Agent base is unchanged.

The existing L08-D001 empty-override and failure witnesses and L08-D002 header
tests remain in the complete suite; their 9 and 11 intended-witness controls are
replayed with the new composer alongside the WP-14.2 controls.

## Negative controls (workflow §9.7)

`scripts/prompt-assembly-negative-controls.py` only mutates a disposable full code
copy. It first requires every exact intended test to be selected and pass. A kill
requires exit 101, that test's FAILED result and its assertion panic; compilation,
selection, setup and unrelated failures are INVALID. Every source is restored in
finally. Positive and mutant Cargo targets are separate.

The 18 controls cover schema contamination by metadata, preflight sanitization,
disabled visibility, ampersand escaping, drive-root and astral dirname indexing,
empty additional instructions, invocation escaping, Rust whitespace/trim,
guideline duplicates, forced tools section, missing read gate/contributed sections,
empty-section joining, copying retained records, ignoring replacement and reading
the live registry instead of the request snapshot. The script names the intended
canonical partition or direct driver/unit witness for each control.

## Validation and reproducibility

Fresh platform results and the exact sequential recipes are recorded below after
the gate batches finish. No incomplete run or environment-invalid control is
counted as a pass. All Windows storage (TMP/TEMP/TMPDIR, caches, Cargo home/target,
worktrees, copies and logs) is inside the E: project root. Linux uses E: bind mounts
for source, Cargo home/target and logs, and tmpfs for temporary POSIX fixtures; no
writable Docker named volume is used.

Windows positive G3 passed: **638 passed / 0 failed / 0 ignored**, including
4 doctests, across 89 result blocks. Formatting, strict workspace/all-target/
all-feature Clippy, warning-strict rustdoc and `xtask conformance verify` passed.
The pre-existing ICU LIBCMT linker warning remains; no new warning was introduced.
The initial wrapper's relative control-script path was invalid after the positive
recipe changed working directory. Controls did not start in that wrapper; they
were launched separately with an absolute path. This is not credited as a complete
combined exit-zero batch. The individual positive gate commands were all green.

Windows controls passed **18/18 WP-14.2 + 9/9 assembler + 11/11 header** valid
intended-witness kills, zero invalid controls or survivors. The control-only
resource settings were `CARGO_PROFILE_DEV_DEBUG=0`, `CARGO_PROFILE_TEST_DEBUG=0`
and `CARGO_INCREMENTAL=0`; optimization and debug assertions retain their default
test settings. Candidate production and canonical files were never mutated.
Shared manifest/schema validation passed **856** tests; docs process tests passed
**363** tests.

Fresh Node v22.15.1 replay ran the unchanged `oracle-gen.mjs`, `tools-oracle.mjs`
against pinned Pi's core source, then `gen-canonical.mjs`. All **66 scenario files**
and `oracle.json`, `tools-oracle.json`, `out-of-domain.json` were byte-identical to
the committed Git blobs (`git hash-object --no-filters` versus the corresponding
HEAD blob). The tools oracle's asserted naive blank-line extractor control was
killed by t14/t15/t16 only. The harness `skills.ts` / `system-prompt.ts` copies
were also checked directly against the pin: no source difference. This replay
reused the prior local yaml@2.9.0 / ignore@7.0.5 dependency copy; no new dependency
acquisition or integrity claim is made. Python was not an expected-value oracle.

### Reproduction setup

Committed recipes are in `assurance/layers/data/14-wp142-rust/`. They describe
the environment actually used, with the fixed Owner project root
`E:/AI/Projects/OpenMinds/Minions/Minion-Agent`. Place the code task worktree at
`review-worktrees/wp142-rust`. Copy the four gate/control/launcher recipes into
`.tmp/wp142-rust/`, and create `.tmp/wp142-rust/logs-linux` before the Docker run.
The committed `project-environment.ps1` is an exact copy of the local sourced
configuration: if the project's `.agents/project-environment.ps1` is absent,
place that copy there (it resolves its parent as the project root). It changes
only process-local environment variables, not user/system settings.

Run from the project root, **sequentially**:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .tmp/wp142-rust/gates-windows.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .tmp/wp142-rust/controls-windows.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .tmp/wp142-rust/run-linux.ps1
```

Windows: amd64, Windows build `10.0.26200.0`, Rust/Cargo 1.97.1, Node v22.15.1.
Linux: amd64 `rust:1.97.1-trixie`, inspected RepoDigest
`rust@sha256:b1b3c9c0d921d7fa0a6d1f9ec7e4eab87f8c8ec97644c3d791450f131dec813f`.
Node v22.15.1 is the existing Linux binary at `.tmp/wp141-node-linux`, mounted
read-only, copied/chmodded in tmpfs and placed on PATH. Both platforms consume
the existing certified ICU4C 78.3 build for their platform, with identity checks;
source SHA-512 is
`04a49455e1489030c520a4bfd2664fa2171e7938d08f2acdbbcb1fda976639fd8b1f0704f2eec89ba59a7b6d118ceaab6ec5a096e40d9085a0895d91ce225245`.
The recipes give exact native link, identity and runtime-library paths and the
official pinned search-artifact directory required by lower-layer regressions.

The Docker root is read-only; source/Node/ICU/artifact mounts are read-only.
Cargo home, positive/control targets and logs are E: binds. `/tmp` is a 16 GiB
executable tmpfs. The source is copied there and `*.sh` line endings are normalized
only in that copy; the launcher also normalizes its mounted gate script first.
No source/canonical content is otherwise rewritten. Default container seccomp and
capabilities were used. No other gate batch ran concurrently; the positive and
control phases, and Windows then Linux, were sequential.

Shared validation commands (the existing project Python venv, with candidate
`minion-agent-python/src` or docs `process/tools` on PYTHONPATH):

```text
python -m pytest -q -o addopts='' tests/conformance/test_manifest_validation.py tests/conformance/test_schema_validation.py
python -m pytest -q -o addopts='' process/tools/tests
```

These are schema/manifest and process gates, not a new Python certification claim.

## Scope and handoff

No Python, shared contract, canonical expected value or dependency version change.
Manifest changes are Rust evidence pointers only, pending independent review.
HAR-016 consumes rather than modifies AG-024/AG-025/MINION-003. The scalar domain,
WP-14.1 records and approved exclusions are unchanged. Layer 15 is not started.
The implementer does not certify its own candidate. The paired exact remote heads
are handed to Claude for independent CLOSURE_REVIEW after fresh gates.
