# Layer 13 WP-13.1 — TOOL-025/TOOL-026 contract-integration targeted re-review

**Mode:** independent Rust-side targeted contract re-review only. No implementation.

**Verdict:** **REJECTED** — `INT-R001`, `INT-R002`, and `INT-R004` are resolved. `INT-R003`
remains blocking.

## Exact target

```text
docs PR #132
    65aa09ddeab127a809d20157fddb1f73d6bcd5cd

manifest PR #52
    461f307137b28df4175238d13022838af85489d7

prior review evidence
    minion-agent-docs#156
    b5d17051ef5c33e374c7432a4501d041f2720bd3

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

Both new candidate SHAs were fetched and verified remote-reachable. Issue #48 was open and named
`NEXT_OWNER = Codex`. This pass checked only the four prior integration findings; it did not
re-characterize R002-A, R005-A, or R010-B.

## Closure ledger

### L13-WP131-INT-R001 — R005-A Photon authority

**Result: RESOLVED.**

The stale implementation-delegated/non-byte-authoritative rule is removed. Both spec and manifest
now bind the complete Photon-dependent observable surface to pinned
`@silvia-odwyer/photon-node 0.3.4`/`photon_rs_bg.wasm`, require version/artifact and differential
corpus evidence before implementation, reject mere visual equivalence, and carry the mandatory
stop/return-to-owner feasibility rule.

### L13-WP131-INT-R002 — R002-A/R002-B conflation

**Result: RESOLVED.**

The shared pipeline now performs the approved direct, unwrapped strict conversion before any
`ctx.fs` access. The selected R002-A path is an immediate `invalid` rejection; R002-B's
platform-dependent literal fall-through is clearly marked not selected and is no longer used by
the normative path or planned canonical evidence. The former pipeline contradiction is removed.

### L13-WP131-INT-R003 — R010-B manifest disposition

**Result: STILL OPEN (`CONTRACT_ASSURANCE_DEFECT`, blocking).**

The remediation adds prose inside each `rule` saying R010-B is an intentional divergence “not
covered” by that row's `adopted` disposition, but both rows still have only one machine-readable
disposition and it is still:

```yaml
disposition: adopted
```

That does not satisfy the finding. A manifest row's disposition must describe the semantics the row
contains; prose disclaiming part of the same row from its own disposition leaves traceability
structurally mixed and requires every consumer to override the machine-readable field by parsing
free text. It also permits manifest automation to report the R010-B behavior as adopted Pi parity.

**Minimal remaining correction:** split the R010-B raw/hybrid text mapping into its own manifest row
with `disposition: intentional divergence`, carrying the exact owner-governance permalink and the
scope to TOOL-025 plus the currently-integrated TOOL-026 rejection. Leave TOOL-025/TOOL-026's core
Pi-compatible behavior in their existing `adopted` rows. An equivalently machine-readable split is
acceptable; an explanatory sentence inside an adopted row is not.

### L13-WP131-INT-R004 — TOOL-028 scope leakage

**Result: RESOLVED.**

The broad “shared with TOOL-028 below” cross-reference is removed. The candidate scopes the current
R010-B vocabulary to TOOL-025/read and the already-integrated shared TOOL-026 step-4 rejection,
while explicitly deferring TOOL-028's own raw/hybrid sites and wrapper/template selection. The
TOOL-028 normative section and manifest row remain mechanically unchanged.

## Gates

```text
manifest validation
    8 passed

candidate file scope
    spec/tools.md
    pi-parity-manifest.yaml

TOOL-027/TOOL-028 manifest row hunks
    none

Python/Rust implementation changes
    none
```

## Verdict

```text
TOOL-025/TOOL-026 INTEGRATION
    REJECTED

INT-R001
    RESOLVED

INT-R002
    RESOLVED

INT-R003
    STILL OPEN — BLOCKING

INT-R004
    RESOLVED

R006-C
    FEASIBILITY_BLOCKED / unchanged

Python/Rust WP-13.1 implementation
    NOT AUTHORIZED / NOT STARTED
```

Return only the manifest-disposition split to the shared-contract owner. Do not reopen the three
resolved integration findings or any approved characterization.
