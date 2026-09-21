# CE-L13-SCOPE-01 — pinned-Pi `getShellConfig` convergence checkpoint (revision 3, proposed)

Mode: §11.8 characterization/checkpoint only. **No Python or Rust implementation performed or
authorized. No Layer 13 semantic contract adopted. This checkpoint requires independent
Codex challenge/approval before being folded into the Layer 13 scoping artifact.**

Targeted remediation of the independent checkpoint re-challenge (`minion-agent-docs#129` @
`bb2fe8f5c5ad4955815d14567724b0ad595f6aa4`, verdict `REJECTED`, one remaining finding
`CE-L13-C003`) against checkpoint revision 2 (`minion-agent-docs#124` @
`ca32ea2c2b7d44ea7cf952c759cc0be4c240fa4a`). Revision 2 is left unmodified as the historical
reviewed record. The re-challenge confirmed `CE-L13-C001` and `CE-L13-C002` fully resolved; both
are unchanged and not revisited. Only the single item below is revised.

## CE-L13-C003 (remainder) — `catch`-reachable scenario corrected

Revision 2 gave "the probe command cannot be spawned at all" as its example of a case reaching
`findBashOnPath`'s `catch` block. That example is itself wrong: a missing executable does not
make `spawnSync` throw. Verified directly (independently reproduced, not merely taken from the
review):

```js
const { spawnSync } = require("node:child_process");
const r = spawnSync("__definitely_missing_shell_probe__", [], { encoding: "utf8", timeout: 5000 });
// observed: does NOT throw; r.status === null; r.error.code === "ENOENT"
```

A missing/unspawnable executable is reported through the *returned result object*
(`result.error` set, `result.status === null`), which `findBashOnPath` never inspects -- it falls
through the `if (result.status === 0 && result.stdout)` check exactly like a non-zero exit or a
timeout, reaching the ordinary final `return null;`, not the `catch` block.

**What genuinely throws synchronously, verified directly:** `spawnSync` throws only for
programmer-error-class argument problems -- invalid argument *types* or *out-of-range option
values* -- not for OS-level spawn failures:

```js
spawnSync(null)                                  // throws TypeError: the "file" argument must be
                                                  // of type string
spawnSync("where", ["bash.exe"], {timeout: -1})  // throws RangeError: timeout must be an
                                                  // unsigned integer
```

`findBashOnPath` always calls `spawnSync` with fixed, valid literal arguments -- `"where"`/
`["bash.exe"]` or `"which"`/`["bash"]`, and a fixed valid `{encoding: "utf-8", timeout: 5000}`
options object; none of these ever vary at runtime, and none can produce a `TypeError`/
`RangeError` given the literals actually passed.

**Corrected statement (replaces revision 2's wrong example):** the `catch` block is defensive
code against exception classes (`TypeError`/`RangeError` from `spawnSync`'s own argument
validation) that cannot actually occur given the fixed, valid argument literals `findBashOnPath`
always passes -- it is not reachable by any external/environmental condition (a missing probe
binary, a timeout, a non-zero exit, permission errors, and similar OS-level failures all settle
through the ordinary unsuccessful-result fall-through instead, exactly as `CE-L13-C003`'s original
correction established). The externally observable behavior is unchanged from every prior
revision: any probe failure of any kind, by either path, silently yields `null` from
`findBashOnPath`, never a thrown error.

## Everything else (unchanged from revision 2)

`CE-L13-C001`'s corrected truthiness-based branch-1 decision, `CE-L13-C002`'s corrected
matcher-reachability statement (every resolved-path branch passes through the same matcher; only
the literal `"sh"` fallback branch is structurally exempt), the complete decision-order table for
branches 2/3, both distinguishable thrown-error message texts, the Unix silent-degrade-to-`sh`
branch, and the proposed `TOOL-034` requirement-scope impact are all unchanged and remain in
force.

## Convergence status

```text
episode:                  CE-L13-SCOPE-01
checkpoint_status:        PROPOSED FOR APPROVAL (revision 3)
open_findings:
  - L13-S002
next_action:               independent Codex challenge/approval of this exact characterization
implementation_authorized: NO
```
