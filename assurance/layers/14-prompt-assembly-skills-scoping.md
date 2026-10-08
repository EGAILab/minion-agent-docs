# Layer 14 — Prompt Assembly + Skills scoping

Mode: scoping / read-only audit. **IMPLEMENTATION AUTHORIZED: NO.**

Owner authorization (this session, 2026-10-08): "Start Layer 14 scoping: AUTHORIZED." Scope: prompt
assembly and skills. Practical-parity policy applies from scoping (`process/agent-workflow.md` §1,
§6.1; `assurance/pi-divergences.md`). Production implementation is not authorized by this
artifact. Layer 15 (compaction) has not started.

## 1. Starting state

```text
code main:    dcb1efed2e18d203dfab35f19774a85009d2ad80
docs master:  217d1969edfb7f88cb781d5980a05931e690b359
pinned Pi:    b7bb00b936dbe21b8e160b3e89efdec361846699
```

`ref-repos/pi` was confirmed at the pin by `git rev-parse HEAD`, with a clean tree. Pi's pinned
dependency versions come from `packages/agent/package.json` and the root `package-lock.json`:

- `yaml` **2.9.0**
- `ignore` **7.0.5**

The premise probes in §6 ran against exactly those versions, under Node v22.15.1 / ICU 76.1. That
is the same runtime pin Layer 13 used (`TOOL-040`).

## 2. Authority decision: which Pi implementation

Pinned Pi has **two independent** skill/prompt implementations:

| | `packages/agent/src/harness/` | `packages/coding-agent/src/core/` |
|---|---|---|
| Skill loader | `skills.ts` (386 lines), over the abstract `ExecutionEnv` | `skills.ts` (507 lines), over Node `fs` |
| Prompt helper | `system-prompt.ts::formatSkillsForSystemPrompt` | `skills.ts::formatSkillsForPrompt` |
| System-prompt composer | none: `AgentHarnessOptions.systemPrompt?: string \| (() => string \| Promise<string>)` is application-supplied | `system-prompt.ts::buildSystemPrompt` (162 lines), the Pi product prompt |
| Child traversal order | `entries.sort((a, b) => a.name.localeCompare(b.name))` | raw `readdirSync` order (unsorted, host-dependent) |
| Diagnostics | typed codes (`file_info_failed`, `list_failed`, `read_failed`, `parse_failed`, `invalid_metadata`) | no codes; adds `collision` |
| Name checks | includes "does not match parent directory" | no parent-directory check |
| BOM | not stripped | stripped (`stripBom`) |
| Duplicate names | all kept | first wins, plus a canonical-path dedupe and collision diagnostics |
| `Skill.content` | yes, the body is read at discovery | no; the file is re-read at `/skill:` expansion |
| Prompt wording | "Read the full skill file when the task matches its description." | "Use the read tool to load a skill's file …", with a leading `\n\n` |

**Proposed decision: `AUTH-14-1`.** For skills, the authority is the **harness** implementation
(`packages/agent/src/harness/{skills,system-prompt,types}.ts`). The reasons:

1. Manifest rows `HAR-001`/`HAR-002` already cite the harness package.
2. The frozen master's "System prompt and skills" section matches the harness, not the
   coding-agent:
   - "missing input directories are skipped";
   - "deterministic traversal/order";
   - "read the full matching skill file".
3. The harness runs over `ExecutionEnv`, which is exactly Minion's certified `ctx.fs` seam (Layer 12).
4. Its order is deterministic; the coding-agent's `readdirSync` order is not.

The coding-agent skill loader is recorded as a **divergent sibling, not adopted**. Each row of the
table above is a known non-adoption, so it can be cited if a later reviewer asks why Minion's
behaviour differs from the Pi CLI.

This is the opposite choice from Layer 13, which audited `coding-agent/src/core/tools/` because the
harness tool set was a strict subset. Here the two are not subset/superset; they disagree, and the
manifest and master already chose.

**Proposed decision: `AUTH-14-2`.** For **system-prompt composition**, pinned Pi's harness has *no*
composer. The `systemPrompt` option is an application string or callback. Every `AgentHarness` run
operation (`prompt`, `skill`, `promptFromTemplate`, …) rejects with `HarnessNotImplemented` at the
pin, so *when* the harness would resolve the callback is **`PI_BEHAVIOR_UNCERTAIN`** — it is
unobservable at the pin.

Minion's `ctx.system_prompt` section assembly (master §3, "Plugins may contribute prompt
sections") is therefore a **Minion mapping**, not direct Pi parity. The only Pi composition
reference is the coding-agent's `buildSystemPrompt`. It is used solely as the reference for:

- section *ordering*;
- section *gating*;
- tool-metadata *rendering*.

It is used only for the sections Minion adopts (§8, `PP-14-4`/`PP-14-5`), and never for its
Pi-product text.

## 3. Pinned-Pi source map

Every file below was read in full unless marked partial.

| Source | Symbols | Observable rules (§5) |
|---|---|---|
| `agent/src/harness/skills.ts` (386) | `loadSkills`, `loadSourcedSkills`, `loadSkillsFromDirInternal`, `addIgnoreRules`, `prefixIgnorePattern`, `loadSkillFromFile`, `validateName`, `validateDescription`, `parseFrontmatter`, `resolveKind`, `dirnameEnvPath`, `relativeEnvPath`, `formatSkillInvocation`; constants `MAX_NAME_LENGTH = 64`, `MAX_DESCRIPTION_LENGTH = 1024`, `IGNORE_FILE_NAMES` | S-1..S-30 |
| `agent/src/harness/system-prompt.ts` (34) | `formatSkillsForSystemPrompt`, `escapeXml` | P-1..P-6 |
| `agent/src/harness/types.ts` (315) | `Skill`, `PromptTemplate`, `AgentHarnessResources`, `FileSystem`, `FileInfo`, `FileKind`, `FileError` | S-* inputs |
| `agent/src/harness/agent-harness.ts` (508) | `AgentHarnessOptions.{tools, activeToolNames, systemPrompt, resources}`, `HarnessTool = AgentTool & {replay?}`, `getTools`/`setTools`, `getResources`/`setResources` (copying), `getActiveTools`/`setActiveTools`, `unavailable(...)` on every run operation | T-1..T-4 |
| `agent/src/harness/prompt-templates.ts` (partial, 1-80) | `loadPromptTemplates`, `loadSourcedPromptTemplates` | excluded, §11 |
| `agent/src/agent.ts` (partial) | `createMutableAgentState` (`systemPrompt` default `""`), `createContextSnapshot` (systemPrompt + copied messages/tools per run), `prepareNextTurn`/`prepareNextTurnWithContext` | T-5 |
| `agent/src/agent-loop.ts` (partial, 220-300) | `streamAssistantResponse` builds `Context{systemPrompt, messages, tools}` per request; `prepareNextTurn` at `:232` | T-5, T-6 |
| `agent/src/types.ts` (partial, 320-420) | `AgentTool` (`label`, `prepareArguments`, `execute`, `executionMode`), `AgentContext`, `AgentToolResult.addedToolNames` | §7 |
| `ai/src/types.ts:514-519` | `Tool{name, description, parameters, constrainedSampling?}` | §7 |
| `coding-agent/src/core/skills.ts` (507) | divergent sibling (§2) | non-adoption list |
| `coding-agent/src/core/system-prompt.ts` (162) | `buildSystemPrompt`, `BuildSystemPromptOptions` | C-1..C-12 |
| `coding-agent/src/core/agent-session.ts` (partial: 540-560, 895-1090, 1235-1345, 2400-2415, 2600-2680) | `_installAgentNextTurnRefresh`, `setActiveToolsByName`, `_normalizePromptSnippet`, `_normalizePromptGuidelines`, `_rebuildSystemPrompt`, `_runAgentPrompt` (override reset), `before_agent_start` handling, `_expandSkillCommand`, `parseSkillBlock`, tool-definition registry refresh | C-*, T-* |
| `coding-agent/src/core/extensions/types.ts` (partial: 430-520, 700-740, 1110-1130) | `ToolDefinition.{promptSnippet, promptGuidelines, constrainedSampling, renderShell, renderCall, renderResult}`, `BeforeAgentStartEvent{systemPrompt, systemPromptOptions}`, `BeforeAgentStartEventResult.systemPrompt` (chained) | §7 |
| `coding-agent/src/core/tools/tool-definition-wrapper.ts` (partial, 1-60) | `wrapToolDefinition` drops `promptSnippet`/`promptGuidelines`/renderers when building the runtime `AgentTool` | §7 |
| `coding-agent/src/core/tools/{bash,edit,find,grep,ls,read}.ts` (grep) | `*ToolSystemPromptContribution{snippet, guidelines}` | §7 |
| `coding-agent/src/core/resource-loader.ts` (partial: 60-110, 660-720, grep) | `loadContextFileFromDir` (`AGENTS.override.md`, `AGENTS.md`, `AGENTS.MD`, `CLAUDE.md`, `CLAUDE.MD`), `SYSTEM.md`/`APPEND_SYSTEM.md` discovery, `updateSkillsFromPaths` | §11 (owned elsewhere / excluded) |
| `coding-agent/src/utils/frontmatter.ts` (40) | coding-agent `parseFrontmatter` (with `stripBom`) | non-adoption list |
| `agent/test/harness/{skills,system-prompt}.test.ts` (titles) | Pi's own coverage: SKILL.md via env, symlinked directories, source info, root-only direct markdown, undeclared root docs, ordered and disabled formatting, empty string, XML escaping | cross-check only |

## 4. Current Minion audit (existing-code rule)

- **Python:** `minion_agent/` has no `skills/` or `system_prompt/` package at `dcb1efed`. The
  master's target layout (§2) names both; neither exists.
- **Rust:** status only; Rust is not inspected as an oracle. No Rust skills/prompt module is
  claimed by the manifest (`rust: Phase 7 skills`).

**Relevant existing seams**, all certified, consumed and not redefined:

- `AgentInstance.system_prompt` — mutable per-instance current value (Layer 07, `AG-014`).
- Layer 08 driver (`agent_loop/driver.py`):
  - The run snapshot `RunContext(system_prompt=instance.system_prompt, messages=…,
    tools=tools.visible_from(scope))` is taken at run start.
  - The per-request `record_header(... {"system_base": decision.system_override or
    context.system_prompt}, tools=schemas)` is recorded on each request.
  - The certified `prepare_next_turn` context replacement.
- `ctx.tools` registry (`TOOL-010`): "ctx.system_prompt describes tools textually but never
  owns/registers a schema". `ToolDefinition` (`tools/definition.py`) has no prompt-snippet or
  guideline fields today.
- Content-addressed request header (`MINION-003`, `session/request_header.py`,
  `EventKind.REQUEST_HEADER`).
- Pinned ICU collation (`tools/builtin/collation.py`, `R006-C`/`TOOL-040`): `en-001`, tertiary,
  numeric off, case-first off, normalization on. Its `key()` lowercases for `ls`; skill traversal
  needs the **raw** comparison (no lowercasing, §5 S-9). This is an additive accessor, not a
  change to Layer 13.

## 5. Behaviour inventory (harness authority)

### Discovery: `loadSkills(env, dirs)`

- **S-1.** Input is a string or a list of strings. Roots are processed in input order; results
  are concatenated.
- **S-2.** Root `fileInfo` fails with `not_found` → skipped silently. Any other code →
  `file_info_failed` (path = the root as given) and skipped.
- **S-3.** A root that resolves (S-25) to a non-directory is skipped silently. A file root is
  **not** loaded as a skill — unlike the coding-agent, which loads explicit `.md` file paths.
- **S-4.** Each root gets a fresh ignore matcher. The root itself is `rootInfo.path`, the addressed
  path, which is not canonicalized.
- **S-5.** `loadSourcedSkills(env, [{path, source}], mapSkill?)`: same per input, with the source
  attached to every skill and diagnostic. Source values are opaque. `mapSkill` is application
  code: a throw from it propagates and is not a diagnostic. Contract drafting decides how to treat
  it; it is not assumed here.

### Per directory: `loadSkillsFromDirInternal(dir, includeRootFiles, ig, root)`

- **S-6.** `fileInfo(dir)`:
  - `not_found` → nothing;
  - any other failure → `file_info_failed`;
  - a kind not resolving to a directory → nothing.
- **S-7.** Ignore rules for `dir` are added **before** listing (S-17..S-20).
- **S-8.** `listDir` failure → `list_failed` (path = dir), and the directory contributes nothing.
- **S-9.** **SKILL.md short-circuit.** In listing order, the first entry named exactly `SKILL.md`
  that resolves to a file and is not ignored (path relative to the root) is loaded, and the
  directory **returns**: no sibling or child is visited. It returns even when that `SKILL.md`
  yields no skill (for example, a missing description). An ignored or non-file `SKILL.md` does not
  short-circuit.
- **S-10.** Otherwise the entries are sorted by `a.name.localeCompare(b.name)`:
  - full names, not lowercased;
  - the host default locale; Node ICU 76.1 under `en-001`/`en-US` gives identical results in §6;
  - probe output: `_x -y a b B e é Z`.
- **S-11.** Skipped: names starting with `.`, and `node_modules`.
- **S-12.** An entry whose kind cannot be resolved (S-25) is skipped. Diagnostics are emitted only
  for non-`not_found` failures.
- **S-13.** Ignore check:
  - the relative path is from the **root** (S-32);
  - directories are checked with a trailing `/`.
- **S-14.** Directories are recursed with `includeRootFiles = false` and the same matcher, which
  accumulates.
- **S-15.** `.md` files load only when `includeRootFiles` is set, i.e. only at the root. Files
  without the `.md` suffix (case-sensitive `endsWith`) never load.
- **S-16.** Within a directory, skills and diagnostics are emitted in traversal order, depth-first:
  a child directory's results are spliced in at its sorted position.

### Ignore files

- **S-17.** Files read, in order: `.gitignore`, `.ignore`, `.fdignore`.
  - A failure from `joinPath` → `file_info_failed` (path = dir).
  - `fileInfo` `not_found` → silent; another failure → `file_info_failed` (path = the ignore file).
  - A non-file → silent. Symlinked ignore files are **not** followed: the check is
    `info.kind !== "file"`.
  - A failure from `readTextFile` → `read_failed`.
- **S-18.** Lines are split on `/\r?\n/`. Per line:
  - the trimmed text is blank → dropped;
  - the trimmed text starts with `#` but not `\#` → dropped;
  - otherwise the **untrimmed** line is used;
  - a leading `!` → negated and stripped; `\!` → the backslash is stripped;
  - one leading `/` is stripped;
  - the prefix `relativeDir + "/"` is prepended (none at the root);
  - `!` is re-added.
- **S-19.** Patterns are evaluated by `ignore@7.0.5` (`ig.ignores(path)`). Probed properties (§6):
  - **case-insensitive by default**;
  - a dir-only pattern `build/` matches `build/` and its descendants, but not the bare `build`;
  - negation works;
  - a nested-prefix `sub/*.md` does not match `sub/deep/a.md`;
  - Pi passes the **untrimmed** line (S-18), but the matcher then **discards an unescaped trailing
    space**: `foo ` ignores `foo`, not `foo `. An escaped trailing space is literal: `foo\ `
    ignores `foo `, not `foo` (remediation probe, §6);
  - `\#x` matches `#x`;
  - `**/tmp` matches at any depth;
  - empty, `../`, `/` and `./` paths **throw**. This **is reachable** through the real loader:
    see S-33.
- **S-20.** The `ignore` package's path-side backslash handling is **platform-dependent**: path
  `a\b` against pattern `a\b` gives `true` on win32 and `false` on Linux (§6). Pi never passes a
  backslash on the path side, because `relativeEnvPath` converts `\` to `/` first. A POSIX
  filename containing an *inner* literal backslash is therefore matched as if it had a separator
  (risk R-8). A *leading* or bare backslash name is S-33.

- **S-33.** **Uncaught discovery rejection** (`L14-SCOPE-R002`). On POSIX, an entry whose name
  starts with `\` (for example `\x.md` or a directory `\d`), or is exactly `\`, yields a
  relative path that `ignore` rejects:
  - `/x.md` or `/d/` → `RangeError: path should be a \`path.relative()\`d string, but got "/x.md"`;
  - a bare `\` file → `""` → `TypeError: path must not be empty`;
  - a bare `\` directory → `/` → `RangeError`.

  Pi does not catch it. The **whole** `loadSkills` call rejects, discarding skills and
  diagnostics already collected from earlier roots and siblings. No diagnostic is produced.
  Names starting with `.` (for example `.\x.md`) never reach the check (S-11), and an inner
  backslash (`a\b.md`) loads normally. All of this was established through the byte-copied
  pinned loader with a scripted environment, identical on win32 and Linux (§6 remediation probe).
  Preserving the rejection is the Pi baseline. Converting it into a diagnostic or skip is
  practical-parity candidate `PP-14-7`, which needs governance and is not an automatic hardening.

### File loading: `loadSkillFromFile(path, parentDirName)`

- **S-21.** `isDeclaredSkill` means the last segment, split on `/` or `\` after stripping trailing
  separators, is exactly `SKILL.md`.
- **S-22.** A `readTextFile` failure → `read_failed`. The text is UTF-8, as decoded by the
  `ctx.fs` seam (Layer 12).
- **S-23.** `parseFrontmatter`:
  - CRLF then CR are normalized to LF.
  - If the text does not start with `---`, or has no `\n---` at or after index 3 → the frontmatter
    is `{}` and the body is the whole normalized text, **untrimmed**.
  - Otherwise the YAML is `slice(4, endIndex)` and the body is `slice(endIndex + 4).trim()`.
  - The YAML goes to `yaml@2.9.0` `parse`; a `null` result → `{}`.
  - **No BOM strip:** a `U+FEFF`-prefixed file has no frontmatter.
  - `---x` on the first line also opens frontmatter (only `startsWith("---")` is checked), and
    `slice(4)` then drops the character after `---`.
  - The closing delimiter is the first `\n---` anywhere, so a `----` or `---foo` line also closes,
    and the remainder of that line becomes part of the body.
- **S-24.** A YAML throw:
  - declared skill → `parse_failed`, with the message = the YAML library's error message;
  - non-declared file → silent.
  - In both cases no skill is loaded.
- **S-25.** `resolveKind`:
  - `file`/`directory` → as is;
  - a `symlink` → `canonicalPath`, then `fileInfo(canonical)`;
  - `not_found` at either step → silent and unresolved;
  - another failure → `file_info_failed` (path = the entry);
  - a target that is neither file nor directory → unresolved.
- **S-26.** `description` = `frontmatter.description` only if it is a JS `string`. A non-declared
  file whose description is absent, not a string, or blank after `trim()` is skipped silently,
  before any validation.
- **S-27.** Validation emits `invalid_metadata` warnings, in this exact order:
  1. Description messages:
     - `description is required`, for an absent, empty or whitespace-only description;
     - otherwise `description exceeds 1024 characters (N)`.
  2. Name messages. The name is `frontmatter.name` if it is a non-empty string; otherwise the
     **scanned directory's** `FileInfo.name`. Messages, in order:
     - `name "X" does not match parent directory "Y"`;
     - `name exceeds 64 characters (N)`;
     - `name contains invalid characters (must be lowercase a-z, 0-9, hyphens only)`, for a failed
       `/^[a-z0-9-]+$/`;
     - `name must not start or end with a hyphen`;
     - `name must not contain consecutive hyphens`.

  Lengths are **UTF-16 code units** (JS `.length`).
- **S-28.** Name problems do **not** block loading; only a missing or blank description does. So
  for a direct root `.md` file, `parentDirName` is the root directory's own name: any root `.md`
  whose frontmatter name differs from the root folder's name loads **with** a mismatch warning.
  This is a Pi quirk, adopted as is; no practical-parity candidate is proposed.
- **S-29.** The skill record is:
  - `{name, description, content: body, filePath: entry.path (addressed, not canonical),
    disableModelInvocation: fm["disable-model-invocation"] === true}`;
  - YAML 1.2 core booleans only: `true`/`True`/`TRUE`, never `yes`/`on` (§6).
- **S-30.** No deduplication: duplicate names and the same file reached twice (through symlinks or
  overlapping roots) are all kept, in order.

### Path helpers (string-based)

- **S-31.** `dirnameEnvPath`:
  - strip trailing `/` and `\`;
  - take the last separator of either kind;
  - a drive root `X:\…` at index 2 → `X:\`;
  - an index `<= 0` → `/`.
- **S-32.** `relativeEnvPath`:
  - `\` → `/`;
  - strip trailing `/`;
  - equal paths → `""`;
  - a prefix match → the remainder;
  - otherwise strip leading `/`.

### Model-visible formatting (harness `system-prompt.ts`)

- **P-1.** `formatSkillsForSystemPrompt(skills)` filters `disableModelInvocation` (truthy). With
  none left → `""` (the empty string, not omitted whitespace).
- **P-2.** Lines, joined by `\n`, with no leading or trailing newline:

  ```text
  The following skills provide specialized instructions for specific tasks.
  Read the full skill file when the task matches its description.
  When a skill file references a relative path, resolve it against the skill directory (parent of SKILL.md / dirname of the path) and use that absolute path in tool commands.

  <available_skills>
    <skill>
      <name>…</name>
      <description>…</description>
      <location>…</location>
    </skill>
  </available_skills>
  ```
- **P-3.** Input order is preserved; there is no sorting or deduplication.
- **P-4.** `escapeXml` is applied to `name`, `description` and `location`, in this order: `&`,
  `<`, `>`, `"`, `'` → `&amp;`, `&lt;`, `&gt;`, `&quot;`, `&apos;`. Nothing else is escaped:
  control characters, newlines inside a description and lone surrogates pass through. `]]>`
  becomes `]]&gt;` through the general `>` rule (`N001`).
- **P-5.** `location` is `skill.filePath` exactly: the addressed path, with native separators.
- **P-6.** `formatSkillInvocation(skill, extra?)` produces
  `<skill name="${name}" location="${filePath}">\nReferences are relative to ${dirnameEnvPath(filePath)}.\n\n${content}\n</skill>`,
  plus `\n\n${extra}` when `extra` is truthy. It applies **no escaping**. Pi's coding-agent
  `parseSkillBlock` regex shows this is the persisted user-message shape. At the pin, the harness
  `skill()` operation that would send it is unimplemented.

### Composition reference (coding-agent `buildSystemPrompt`, used only per §2 `AUTH-14-2`)

- **C-1.** The prompt is either `customPrompt` or Pi's product default ("You are an expert coding
  assistant operating inside pi …", plus the Pi documentation block). The default is Pi-product
  text and **is not adopted**. The discriminator is **truthiness**: an empty `customPrompt`
  selects the default branch. Any adopted analogue keeps that discriminator explicit.
- **C-2.** Then the append section: `\n\n${append}` when non-empty.
- **C-3.** Then, if there are context files:

  ```text
  \n\n<project_context>\n\nProject-specific instructions and guidelines:\n\n
  ```

  then, per file, `<project_instructions path="${path}">\n${content}\n</project_instructions>\n\n`,
  then `</project_context>\n`. The path is **not escaped**.
- **C-4.** Then the skills block, **only if `read` is among the selected tools**. With a custom
  prompt, `!selectedTools` also counts as having `read`.
- **C-5.** Then `\nCurrent working directory: ${cwd with \ → /}`. The custom path ends with a
  trailing `\n`; the default path does not.
- **C-6.** Default path only: `Available tools:` lists a tool `- name: snippet` **only if it has a
  snippet**, in selected-tool order; with none → `(none)`.
- **C-7.** Default path only, guidelines:
  - a conditional "Use bash for file operations like ls, rg, find" (bash without
    grep/find/ls);
  - then the tool guidelines, trimmed, non-empty, deduplicated by exact string, first wins;
  - then the two fixed bullets;
  - rendered as `- ${g}`.
- **C-8.** Snippet normalization: `[\r\n]+` → space, `\s+` → space, trim; empty → none.
- **C-9.** Guideline normalization: per tool, trim, drop empty, deduplicate within the tool in
  order.
- **C-10.** Only tools that are active and in the registry contribute snippets and guidelines.
- **C-11.** The base prompt is rebuilt eagerly on any change to the active tools, the tool
  registry or the resources. The per-turn refresh installs
  `systemPrompt = override ?? base, tools = state.tools`.
- **C-12.** `before_agent_start` handlers may replace the system prompt for one prompt. They chain
  in handler order, see the base prompt plus its structured options, and the override is reset in
  `_runAgentPrompt`'s `finally`.

### Timing and ownership (Pi core)

- **T-1.** `setTools`/`setResources` and the getters copy the **arrays** only (`L14-SCOPE-R003`).
  Collection *membership* is isolated: pushing onto a returned array does not change the
  harness. The `Skill`, `PromptTemplate` and tool **records** are shared by identity: mutating
  `getResources().skills[0].description` is visible to the next `getResources()` (Codex reviewer
  probe on the pinned harness). `createContextSnapshot` likewise copies the tool and message
  arrays, not their elements. T-1 therefore does **not** establish that model-visible skill state
  changes only through replacement.
- **T-2.** Active tool names default to all tool names, in order.
- **T-3.** The harness sends no tool metadata other than `AgentTool`/`Tool` fields to the model.
- **T-4.** `HarnessTool.replay` belongs to the durable harness (`HAR-009`, deferred).
- **T-5.** The system prompt and tools are snapshotted **per run** (`createContextSnapshot`) and
  replaceable **per turn** (`prepareNextTurn`, certified Layer 08).
- **T-6.** The provider request carries `systemPrompt` (text) and `tools` (schemas) as **separate
  fields** of one `Context`. Tool schemas never enter the system-prompt string.

## 6. Premise probes (executed, not assumed)

**Remediation probe** (`L14-SCOPE-R001`/`R002`), `remediation1_probe.mjs`:
- sha256 `399c6ea4…b458`;
- run with `node --experimental-strip-types`;
- outputs `remediation1-{win32,linux}.txt`, identical on both platforms.

It drives the **byte-copied pinned** `pinned/skills.ts` and `pinned/types.ts`. Both are
byte-identical to `ref-repos/pi/packages/agent/src/harness/` at the pin (checked with `cmp`).
The environment is a scripted POSIX-style `ExecutionEnv`, and nothing in the loader or matcher
is replicated. A first run failed to import because the probe package defaulted to CommonJS. That
setup failure was fixed with `pinned/package.json` (`"type": "module"`) and is not credited as
evidence.

**Original premise probe:**

Evidence, per workflow lesson 1 (`minion-agent#75`): `assurance/layers/data/14-scope/`.

- `premise_probe.js` (sha256 `78e40697…fc32`), with `package.json`/`package-lock.json` pinning
  `yaml@2.9.0` and `ignore@7.0.5`.
- Outputs: `premise-win32.txt` (Windows host) and `premise-linux.txt` (`python:3.13` container,
  with the same Node v22.15.1 / ICU 76.1 tree mounted).
- The two outputs differ in **exactly** two lines: the `ignore` backslash row (S-20) and the
  reported default locale (`en-001` vs `en-US`), which leaves the collation output identical.

Findings that change the contract hypothesis:

| Premise | Result |
|---|---|
| `disable-model-invocation: yes` / `on` | string → **not** disabled (YAML 1.2 core) |
| `disable-model-invocation: True` | boolean `true` → disabled |
| duplicate frontmatter key | **throws** (`Map keys must be unique`) → `parse_failed` |
| tab indentation | **throws** |
| multi-document frontmatter | **throws** |
| `description: 2001-12-14` | string (no timestamp type), unlike PyYAML/YAML 1.1 |
| `description: ~` | `null` → treated as missing |
| `name: 123` | number → `typeof` is not string → falls back to the directory name |
| merge key `<<` | **not** merged; kept as a literal key |
| scalar or empty document | a non-object or `null` frontmatter → no fields |
| `ignore` case | `Foo` ignores `foo` (**case-insensitive**) |
| `ignore` with a non-relative path | throws; **reachable** through a leading-backslash or bare-backslash POSIX name, rejecting the whole discovery (S-33) |
| unescaped vs escaped trailing pattern space | `foo ` matches `foo` only; `foo\ ` matches `foo ` only (remediation probe) |
| `"😀".length` | 2 (UTF-16), so the 1024 description limit is counted in code units |

## 7. Tool prompt metadata classification

| Field (Pi) | Where it is model-visible in Pi | Classification | Minion owner |
|---|---|---|---|
| `name`, `description`, `parameters` | provider request `tools` (`Context.tools`) | **tool-schema** (earlier layer) | Layer 05 `ToolDefinition` / `ctx.tools` (`TOOL-010`) |
| `constrainedSampling` | provider request tool entry | **tool-schema** (earlier layer) + provider enforcement | Layer 05 `TOOL-008`; Layer 11 enforcement |
| `promptSnippet` | coding-agent **default** prompt only, `Available tools:` (C-6). Absent with a custom prompt and in the harness. | **model-visible, product-prompt only** | **Layer 14 candidate**, `PP-14-5` (Owner) |
| `promptGuidelines` | coding-agent **default** prompt only, `Guidelines:` (C-7); also `getAllTools()` introspection | **model-visible, product-prompt only** + runtime-only introspection | **Layer 14 candidate**, `PP-14-5` (Owner) |
| `label` | none | **UI-only** | Layer 05 (already present) |
| `renderCall`, `renderResult`, `renderShell` | none (TUI) | **UI-only** | not adopted |
| `prepareArguments`, `executionMode`, `execute` | none | **runtime-only** | Layers 05/06 |
| `HarnessTool.replay` | none | **runtime-only** (durable harness) | **deferred** (`HAR-009`) |
| `AgentToolResult.addedToolNames` | affects which schemas a later request carries | **runtime-only** (dynamic tools) | Layers 06/08 |

`wrapToolDefinition` drops `promptSnippet`/`promptGuidelines` when it builds the runtime
`AgentTool`. In Pi these fields live only on the coding-agent's definition-side registry.

**Ownership rule, Owner directive:** `ctx.tools` owns executable tools and schemas. Prompt assembly
reads `ctx.tools`' *visible-tool snapshot* for any textual tool section. There is no second
registry, no copied schema, and no tool execution in Layer 14. If `PP-14-5` is adopted, snippet and
guidelines become optional fields **on the `ctx.tools` definition** — an additive Layer 05 field
extension, disclosed as a lower-layer dependency (§10) — and are never a separate prompt-side
table.

## 8. Practical-parity candidates (for Owner governance; none approved)

Each was assessed against §6.1's three questions:

- **(a)** Is it Pi's intentional abstraction?
- **(b)** Is it realistic in normal use?
- **(c)** Does exact parity need disproportionate architecture?

Each candidate approved later needs its own `DIV-` entry and a permanent witness.

| ID | Candidate | (a)/(b)/(c) | Recommendation |
|---|---|---|---|
| `PP-14-1` | **YAML engine.** `parse_failed` messages equal `yaml@2.9.0` error text. Exact text needs a byte-faithful port of the library's error reporter in both languages. | no / rare (only for malformed frontmatter) / yes | **Divergence:** match the *accept/reject decision and parsed value* of `yaml@2.9.0` exactly over a characterized corpus (the §6 rows plus a generated corpus), keep the code and path exact, and make the **message** Minion-defined. Needs a witness pairing every corpus case with Pi's accept/reject decision. |
| `PP-14-2` | **YAML constructs outside the characterized corpus.** Examples are tags (`!!str`), complex keys and flow collections. "Exotic" is a screening label, not proof that a construct is unreachable: ordinary aliases already work (§6). | no / rare / yes for full YAML 1.2 fidelity | A finite corpus is evidence, not a definition of library equivalence. The contract must define a **deterministic** treatment for every unsupported construct, for example `parse_failed`, and obtain governance for it. It must not treat unknown behaviour as certified residual agreement. **Decision deferred to the WP-14.1 feasibility matrix.** |
| `PP-14-7` | **Whole-discovery rejection** (S-33): one leading or bare backslash POSIX name rejects all of `loadSkills` | no (an incidental `ignore` precondition) / rare / no | **Owner decision** before the WP-14.1 contract freezes. Either keep it (Pi-exact) or convert it to a defined diagnostic with the entry skipped (a divergence with a witness). The default without a decision is Pi-exact. |
| `PP-14-3` | **Symlink cycles.** Pi recursion through a directory cycle has no guard. It descends `a/loop/loop/…` until a platform path or loop limit, with diagnostics that depend on that limit (`PI_BEHAVIOR_UNCERTAIN`; characterization is a WP-14.1 obligation). | no / rare / yes (host-limit-dependent output) | **Divergence:** stop at a directory whose canonical path is already on the current descent stack, with a defined diagnostic. To be characterized first. |
| `PP-14-4` | **Section composition.** Pi has no harness composer. Proposed Minion mapping: `ctx.system_prompt` sections in a specified deterministic order: base, append, plugin sections, then the skills block. The skills block is gated as in C-4 only if the Owner adopts the gate. | mapping, not a divergence | Label it a **MINION mapping**. Adopt C-2/C-4's order and the C-4 `read` gate as the Pi-compatible reference. Do **not** adopt C-1 product text, C-3 context files or C-5's cwd line (see `PP-14-6`). |
| `PP-14-5` | **Tool snippet/guideline rendering** (C-6..C-10). It is model-visible only in Pi's *product default* prompt. | no (product text) / yes for coding agents / no | **Owner decision.** Option A: defer entirely, and `promptSnippet`/`promptGuidelines` are not modeled. Option B (**recommended**): additive optional fields on the `ctx.tools` definition, with the C-8/C-9 normalization, and an opt-in "tools" section that renders the C-6/C-7 lines exactly. The Pi product preamble and the bash-only conditional bullet are excluded unless the Owner says otherwise. |
| `PP-14-6` | **Context files** (`AGENTS.md`/`CLAUDE.md` discovery, C-3), `SYSTEM.md`/`APPEND_SYSTEM.md`, and the cwd line. These are coding-agent *product resource loading*, not harness behaviour. | no / yes for coding agents / no | Recommend **excluding them from Layer 14**, recorded as a future candidate (a plugin-contributed section). Not a divergence; out of scope. |

## 9. Manifest-row audit (hypotheses)

**`HAR-001`.**

- `pi` is correct: harness `skills.ts`.
- The rule is **incomplete**. It is silent on:
  - the S-9 short-circuit, and the dotfile and `node_modules` skips;
  - symlink resolution (S-25);
  - the collation authority for "deterministic" (S-10 needs the pinned ICU, `TOOL-040`);
  - the `ignore@7.0.5` semantics, including case-insensitivity (S-19);
  - YAML 1.2 core per `yaml@2.9.0` (§6);
  - the BOM non-strip;
  - the exact diagnostic codes, messages and order (S-27), and UTF-16 lengths;
  - the parent-directory mismatch quirk (S-28);
  - multi-root concatenation without dedupe (S-1, S-30).
- The tests are placeholders.
- `rust: Phase 7 skills` is stale wording.
- **Proposed:** keep `HAR-001` as the umbrella row and split it into the requirement IDs in §10.

**`HAR-002`.**

- The `pi` field names the **wrong file**. `formatSkillsForSystemPrompt` lives in
  `harness/system-prompt.ts`, not `skills.ts`.
- The rule omits:
  - the exact instructional lines (P-2) and `""` when there is no visible skill (P-1);
  - that order is the input order (P-3);
  - that escaping covers exactly five characters on three fields (P-4).
- The explicit invocation format (P-6) has no row at all.
- **Proposed:** correct the `pi` field, refine the rule, and add a row for invocation.

**Not Layer 14.** `HAR-003`/`HAR-004` (compaction, Layer 15), `HAR-005` (message projections) and
`HAR-009` (durable harness, deferred) are excluded.

## 10. Proposed requirement IDs, WP split and dependencies

New IDs start at `HAR-010`, after the highest existing row `HAR-009`. `HAR-006..008` are unused
in the manifest and are left unused, so no new row sorts between existing ones.

| ID | Requirement | WP |
|---|---|---|
| `HAR-001` (umbrella, refined) | Discovery traversal over `ctx.fs` (S-1..S-16, S-25, S-30..S-33) | 14.1 |
| `HAR-010` | Frontmatter extraction and YAML semantics (S-23, S-24, S-26, S-29, §6; `PP-14-1`/`PP-14-2`) | 14.1 |
| `HAR-011` | Ignore files and matching (S-17..S-20, S-33; `ignore@7.0.5` corpus, including trailing-space and invalid-path cases) | 14.1 |
| `HAR-012` | Validation and diagnostics: codes, message text, order, UTF-16 lengths, the mismatch quirk (S-27, S-28) | 14.1 |
| `HAR-013` | Sourced loading and skill record shape (S-5, S-29; `Skill{name, description, content, filePath, disableModelInvocation}`) | 14.1 |
| `HAR-002` (refined) | Available-skills block (P-1..P-5) | 14.2 |
| `HAR-014` | Explicit skill invocation text (P-6, including `dirnameEnvPath`) | 14.2 |
| `HAR-015` | `ctx.system_prompt` section composition: order, gating, separator bytes, empty-section handling (`PP-14-4`; MINION mapping) | 14.2 |
| `HAR-016` | Snapshot timing and consistency: the prompt is evaluated at the same points where the request snapshot is taken (run start; each `prepare_next_turn`; the override per T-5/C-12); the textual tool section and the request tool schemas derive from **one** `ctx.tools` visible-tool snapshot; skill-set **membership** changes only by an explicit replace (T-1). Whether a mutation of a retained, shared skill or tool record is seen, and when, is a **Minion composition choice** under `AUTH-14-2`; it is not a consequence of T-1. Any value-isolation rule is proposed through the contract and governance path, without freezing, deep-copying or reopening Layers 07/08 here. | 14.2 |
| `HAR-017` | Request reconstruction: the assembled prompt's model-visible bytes are reconstructable from content-addressed header components (`MINION-003`); the decomposition is a storage detail, the bytes are normative | 14.2 |
| `HAR-018` | Tool prompt metadata (`PP-14-5`, only if the Owner adopts Option B) | 14.2 |

**WP split, proposed and final after review:**

- **WP-14.1 — skill discovery and diagnostics** (`HAR-001`, `HAR-010`..`HAR-013`). A pure function
  over `ctx.fs` with no prompt or loop involvement. Its characterization obligations are the YAML
  corpus, the ignore corpus, symlink cycles (`PP-14-3`), and Windows/Linux path spelling.
- **WP-14.2 — prompt assembly and model-visible metadata** (`HAR-002`, `HAR-014`..`HAR-018`). It
  consumes WP-14.1's skill record only.

Dependency graph:

```text
Layer 12 ctx.fs ─┐
TOOL-040 ICU ────┼─> WP-14.1 ──(Skill record only)──> WP-14.2 <── Layer 05 ctx.tools (TOOL-010)
yaml/ignore      │                                     ^  ^
corpora ─────────┘                                     |  └── Layer 07 AgentInstance.system_prompt
                                                       └───── Layer 08 run/turn snapshot +
                                                              prepare_next_turn + override;
                                                              Layer 03 request header (MINION-003)
```

WP-14.2 *contract drafting* may proceed in parallel with WP-14.1 once the `HAR-013` record shape
is frozen. Its *implementation* follows WP-14.1's certification.

**Lower-layer dependencies (consumed, not reopened):**

- **Layer 12** — `fileInfo`, `listDir`, `canonicalPath`, `joinPath`, `readTextFile`:
  - the error codes (`not_found` silence depends on it);
  - the error **messages**, which become diagnostic text;
  - the addressed-path spelling, which becomes the model-visible `<location>`;
  - JS-string path scoping (`fs-path-jsstring-scoping.md`) for lone surrogates.
- **`TOOL-040`** — the pinned ICU collator. It needs an additive raw-compare accessor; `key()` is
  unchanged. Reusing the build is **not** by itself a skill-collation disposition. Pi's sort uses
  host Node's ICU 76.1 under the host default locale. The WP-14.1 contract must carry that
  host-sensitive mapping, onto pinned `en-001`/ICU 78.3, with its own evidence. `TOOL-040`'s `ls`
  disclosure does not silently extend to skills.
- **Layer 05** — `ToolDefinition`. An additive optional-field extension, only under `PP-14-5`
  Option B.
- **Layers 07/08/03** — as in the graph. No change is expected.
- **If any lower-layer gap is found,** it is raised as a delta finding against that layer, not
  patched inside Layer 14.

## 11. Exclusions and components owned elsewhere

- Compaction and branch summarization, including `SUMMARIZATION_SYSTEM_PROMPT` (`HAR-003`/`004`):
  Layer 15.
- Layers 16–18.
- Message projections (`HAR-005`) and the durable harness (`HAR-009`).
- Prompt templates (`harness/prompt-templates.ts`): an explicit-invocation resource, not a
  system-prompt component, with no manifest row. Excluded and recorded as a future candidate. A
  reviewer may challenge this.
- Coding-agent product resources: context files, `SYSTEM.md`/`APPEND_SYSTEM.md`, the cwd line, Pi
  documentation text, and `/skill:` command parsing (`PP-14-6`).
- The provider-side placement of the system prompt (for example the Codex `instructions` field):
  Layers 10/11. Target-model transformation of messages: Layer 04.
- UI-only tool renderers (§7).
- The old follow-up backlog (#125–#133, #65–#70). None of it is a Layer 14 prerequisite:
  - `L12-D001`/#133 (NUL and non-Unicode names) touches skill paths only for names already
    outside Layer 12's certified domain;
  - Layer 14 inherits that domain unchanged.

## 12. Risk map

| # | Risk | Severity | Mitigation / evidence obligation |
|---|---|---|---|
| R-1 | **Filesystem discovery:** silent-vs-diagnostic classification depends on exact Layer 12 error codes on each platform (#69 `L12-WINDOWS-ERROR-MAP` is open) | high | Canonical fixture trees per platform. Any Windows code difference is traced to #69, not re-mapped in Layer 14. |
| R-2 | **Ordering:** `localeCompare` is host-locale and ICU dependent; Pi's skill sort is the raw compare, not `ls`'s lowercase key | high | The pinned ICU collator with a raw-compare accessor. Canonical order cases with case, accent, punctuation and digits, generated from pinned Node. |
| R-3 | **Duplicate skills:** Pi keeps duplicates (S-30), and `available_skills` then lists both | medium | Adopt exactly as Pi does. A canonical duplicate case. Collision policy is an application concern (§2 non-adoption). |
| R-4 | **Malformed frontmatter:** YAML 1.1 vs 1.2 (`yes`/`on`, timestamps), duplicate keys, tabs, multi-document; Python and Rust YAML libraries differ from `yaml@2.9.0` | **critical** | `PP-14-1`/`PP-14-2`. Corpus oracle from pinned `yaml@2.9.0`, and a feasibility matrix for the engine choice per language. |
| R-5 | **Unicode:** UTF-16 `.length` limits, JS `trim()` whitespace set (includes U+FEFF and U+3000; Python's `str.strip` differs), lone surrogates in names | high | JS-string semantics reused from Layer 12 scoping. Canonical cases at 1024/1025 code units with astral characters, and trim edge characters. |
| R-6 | **XML escaping and prompt injection:** only five characters are escaped; descriptions may contain newlines and fake `</available_skills>` text (escaped `<`, so not structural); P-6 invocation and C-3 paths are unescaped | high | Adopt as Pi does, with canonical injection cases showing exact bytes. Do not "harden" silently: any stricter escaping is a divergence needing the Owner. |
| R-7 | **Dynamic registration:** a tool or skill change mid-run must reach the prompt and the schemas at the same snapshot point | high | `HAR-016`, with one-snapshot consistency witnesses: a tool registered between turns shows in both, or in neither. Add **retained-record mutation** witnesses: a shared skill or tool record mutated after it was supplied (T-1, `L14-SCOPE-R003`), observed at each snapshot point under whatever rule the contract adopts. |
| R-8 | **Exclusion flags:** the `disable-model-invocation` strict `=== true`, the dotfile and `node_modules` skips, ignore case-insensitivity, a literal backslash in POSIX names (S-20) | medium | Canonical cases for each, including the inner-backslash name on Linux. |
| R-9 | **Path projection and cross-platform paths:** `<location>` is the addressed path with native separators; `dirnameEnvPath`'s drive-root rule; `relativeEnvPath`'s backslash conversion | high | Per-platform expected outputs. The addressed-path spelling comes from Layer 12, never re-normalized in Layer 14. |
| R-10 | **Request reconstruction and persistence:** splitting the prompt into header components must not change model-visible bytes; the override replaces the whole prompt | medium | `HAR-017` round-trip witnesses over the real header and artifact store (`MINION-003`). |
| R-11 | **Symlink cycles:** Pi's output is host-limit dependent | medium | `PP-14-3`, characterize first. |
| R-12 | **Engine-library premise errors** (lesson 1) | medium | Every library premise gets an executed probe (§6), extended in WP-14.1. |
| R-13 | **Whole-discovery rejection** (S-33): a leading or bare backslash POSIX name rejects the entire `loadSkills` call, losing every other skill | high | WP-14.1 witnesses for `\x.md`, `\d/`, a bare `\` file and directory, and a sibling-loss case; nearest-case characterization before contract freeze; `PP-14-7` if Minion wants a diagnostic instead. |
| R-14 | **Trailing-space matcher semantics** (`L14-SCOPE-R001`): the raw line is kept, the matcher drops an unescaped trailing space | medium | `HAR-011` corpus with unescaped, escaped and mixed trailing-space patterns. Never trim raw lines as a "fix". |

## 13. Python / Rust feasibility notes

**YAML.**

- Python: PyYAML is YAML 1.1 and is unsuitable. `ruamel.yaml` is YAML 1.2, but it honours merge
  keys and resolves timestamps, both of which `yaml@2.9.0` core does not.
- Rust: `saphyr`/`yaml-rust2` are YAML 1.2; their duplicate-key behaviour needs checking.
- Likely outcome: a configured engine plus a post-parse guard, verified on the corpus.
- A per-language feasibility matrix (`process/templates/cross-language-feasibility-matrix.md`) is
  required before the WP-14.1 contract freezes.

**Ignore matching.**

- Python's `pathspec` (gitwildmatch) and Rust's `ignore` crate both differ from npm `ignore@7.0.5`
  (case-insensitivity, dir-only and negation details).
- Likely outcome: a small port of the npm matcher's regex construction in both languages, verified
  on a generated corpus (patterns × paths × platform).
- It is feasible: the package is small and dependency-free.

**Collation.** Both languages already carry the pinned ICU (`TOOL-040`). This is an additive
raw-compare accessor.

**JS string semantics.**

- `trim()`'s whitespace set, `.length` in code units, and `/^[a-z0-9-]+$/` (ASCII) are
  implementable directly.
- Python strings are code-point based, so lengths must count UTF-16 units.
- Rust `str` cannot hold lone surrogates. Layer 12 scopes this for **filesystem paths** only.
  The skill name, description, content and invocation strings are separate carriers. Where they
  can hold lone surrogates, they must reuse the certified JS-string representations, not ordinary
  `str`. This belongs in the WP feasibility matrices.

**Filesystem.** Everything runs over the certified `ctx.fs` in both languages. Symlink handling
follows S-25 exactly; there is no `os.walk` or `read_dir` shortcut.

**Prompt assembly.** These are pure string functions with no platform risk beyond path spelling
(R-9).

## 14. Requested review

Independent review (Codex) of this scoping artifact:

- authority decisions `AUTH-14-1`/`AUTH-14-2`;
- the behaviour inventory's accuracy against the pinned source;
- the §7 classification;
- the manifest audit;
- the requirement set;
- the WP split and dependency graph;
- the risk map;
- the `PP-14-*` candidates.

Expected verdict vocabulary, as in Layer 13 scoping:
`LAYER 14 SCOPE APPROVED / CHANGES REQUESTED; WORK-PACKAGE SPLIT …; REQUIREMENT SET …;
IMPLEMENTATION AUTHORIZED NO`.

Owner decisions are needed before the WP-14.2 contract freezes: `PP-14-4` (mapping confirmation)
and `PP-14-5` (Option A or B). Before the WP-14.1 contract freezes: `PP-14-1`, `PP-14-2`, `PP-14-7` and
`PP-14-3`, informed by the feasibility matrix and characterization. None blocks the scoping review.

## 15. Remediation record (scoping review 1)

Review: Codex @ `06f146b9`, published verbatim at `minion-agent-docs#253` issuecomment-6049513540.

- **Verdict:**
  - LAYER 14 SCOPE CHANGES REQUESTED;
  - WORK-PACKAGE SPLIT APPROVED;
  - REQUIREMENT SET CHANGES REQUESTED;
  - IMPLEMENTATION AUTHORIZED NO.

| Finding | Change |
|---|---|
| `L14-SCOPE-R001` (medium): the trailing-space premise was wrong | S-19 now separates raw-line preservation (S-18, unchanged) from matcher semantics: an unescaped trailing space is discarded, an escaped one is literal. Evidence is the executed remediation probe (§6). Added R-14 and the `HAR-011` corpus obligation. |
| `L14-SCOPE-R002` (medium): invalid ignore paths are reachable | Withdrew "Pi never produces one". Added S-33, the uncaught whole-discovery rejection, reproduced through the byte-copied pinned loader for leading-backslash files and directories and a bare `\` file and directory, with sibling loss and the dotfile and inner-backslash controls. Added R-13 and `PP-14-7` (Pi-exact by default). |
| `L14-SCOPE-R003` (medium): `HAR-016` overstated what T-1 guarantees | T-1 now separates copied membership from shared records. `HAR-016` limits replace-only to membership and names retained-record visibility as a Minion composition choice under `AUTH-14-2`. R-7 adds retained-record mutation witnesses. Layers 07/08 are not reopened. |
| `N001`: the `]]>` example | P-4 corrected: `]]>` becomes `]]&gt;`. |
| Reviewer notes, non-blocking | Carried into S-5 (a `mapSkill` throw), C-1 (truthiness discriminator), §10 (the host-sensitive skill-collation mapping is not implied by `TOOL-040`), §13 (non-path JS-string carriers), and `PP-14-2` (deterministic treatment, corpus ≠ equivalence). |

The WP split and the requirement numbering are unchanged. No production code, manifest or spec was
modified.
