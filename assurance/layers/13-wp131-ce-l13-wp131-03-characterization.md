# CE-L13-WP131-03 — characterization: one verified ICU build (`L13-WP131-FR003`)

Mode: workflow §11.8.3 characterization pass. Trigger A: FR003 survived two independent reviews (final complete review round 1, `minion-agent-docs#168`; targeted review of remediation 3, `minion-agent#48` comment `5850822214`). `NEXT_OWNER = Claude` per #48.
- **No implementation performed.**
- **Frozen candidates:** code #60 @ `d71820395b82e61b9d7a47554805caf2579109b6`, docs #162 @ `9d3f78fa3122b0024deaa123c6a0d2e11907c149`.
- **Unaffected:** FR001/FR002 and I001/C012 stay provisionally closed.

## OPEN FINDING

`L13-WP131-FR003` (`CONTRACT_ASSURANCE_DEFECT`): the R006-C rule is not enforced. Codex's latest two witnesses:
- **FR003-a, inventory:** the loaded-library inventory keeps the FIRST instance per library name.
  - Linux: `/verified/libicui18n.so.78.3` followed by `/foreign/libicui18n.so.78.3` yields only the verified path, so a mixed process is accepted.
- **FR003-b, trust root:** `build.sh --identity` re-checks the source tarball but then hashes whatever binaries are already in the prefix, so a foreign same-version binary substituted before `--identity` is attested as verified.

## RULE BEING ENFORCED (unchanged, `spec/tools.md` TOOL-028 "Collation", R006-C)

```text
ICU   ONE build of the official icu4c-78.3-sources.tgz whose SHA-512 matches the release's own
      SHASUM512.txt, linked by both engines. An implementation MUST fail rather than fall back if it
      would link or load any other ICU.
```

"Any other ICU" is the spec's own scope, so the gate must consider EVERY ICU library in the process, not only the first match of three names. No new semantic choice is needed.

## MEASURED (this host, candidate `d7182039`, Windows 11, Python 3.13.5, pinned build loaded)

```text
A  before importing icu                              ICU modules in process: none
B  after pinned_collation()                          _icu_.pyd, icuin78.dll, icuuc78.dll, icudt78.dll (all pinned bin64)
C  + a foreign icuin78.dll (pinned copy with bytes    the same four PLUS <tmp>\icuin78.dll -- Windows loads a
   appended) loaded by FULL PATH via ctypes           second module with the same base name
D  current gate's inventory (GetModuleHandleW)       icuuc/icui18n/icudata -> the pinned paths only
E  current gate on the mixed process                 ACCEPTS                    <- FR003-a reproduced on Windows
```

Windows' own `icu.dll`/`icuuc.dll` is not loaded in this process (step A/B), so a strict "no other ICU at all" rule does not reject an ordinary host process here. Codex's Linux witness (a second same-soname mapping in `/proc/self/maps`) shows the same first-match hole via `setdefault`.

## OBSERVABLE RULES (proposed)

- **R-F1: the inventory is complete.**
  - Enumerate EVERY loaded module or mapping: Windows `EnumProcessModules` + `GetModuleFileNameW`; Linux every `/proc/self/maps` pathname.
  - Classify as ICU every module whose base name is an ICU library: Windows `icu*.dll`; Linux `libicu*.so*`.
  - Each distinct file is one instance; first-match lookups are not used.
- **R-F2: every ICU instance must belong to the verified build (fail closed).**
  - Each instance's SHA-256 must equal the identity's hash for that library.
  - An ICU instance whose library the identity does not list is rejected. That covers any other name, any other major version, and a distribution ICU.
  - Two byte-identical instances are the same build's bytes and are accepted; any differing bytes are rejected.
  - The identity lists every runtime library the build produces (Windows `icuuc78`, `icuin78`, `icudt78`, `icuio78`, `icutu78`; Linux `libicuuc`, `libicui18n`, `libicudata`, `libicuio`, `libicutu`).
  - At least `icuuc`, `icui18n` and `icudata` must be loaded.
- **R-F3: when the check runs.**
  - The check runs once, when collation is first loaded (after PyICU has loaded its ICU), and `ls` fails closed if it fails.
  - A foreign ICU loaded AFTER a passed check cannot change what PyICU already bound: Windows binds imports at load; on Linux the pinned objects were loaded first and are PyICU's own `DT_NEEDED` dependencies. So re-checking per call is not required.
  - This is disclosed as the gate's temporal boundary, not claimed as full process integrity.
- **R-F4: the trust root is the build itself.**
  - The identity file is written only by the SAME `build.sh` run that verified the tarball's SHA-512, extracted it fresh (`rm -rf icu && tar xzf`) and compiled the binaries, as its final step.
  - There is no mode that hashes binaries the current run did not compile: `--identity` is removed.
  - An existing build without an identity must be rebuilt.
  - The file records the source SHA-512, the build's platform, and each library's SHA-256.
- **R-F5: the threat model is stated.**
  - The gate defends against accidental or ambient substitution: a distribution ICU, another compile of 78.3, a stale or mixed prefix, a wrong `DLL`/`rpath` resolution.
  - It does not defend against a local actor with write access to the toolchain directory, who could also rewrite the identity file.
  - Content-addressed hashes committed to the repository would need reproducible ICU builds on every platform (MSVC is not reproducible by default). That is disclosed as a stronger, rejected alternative, not silently assumed.

## BEHAVIOR MATRIX

```text
case                                                            expected
verified build only (uc, i18n, dt; optional io/tu)              ACCEPT
+ second, byte-different icui18n instance loaded before check   REJECT (R-F1/R-F2)           W-F1  (FR003-a)
+ second, byte-IDENTICAL copy of a verified library             ACCEPT (same build bytes)    W-F2
+ an ICU library the identity does not list (other major, a     REJECT (R-F2)                W-F3
  distribution/system ICU, an unlisted name)
a required library (uc/i18n/dt) not loaded                      REJECT                       W-F4
pinned DLLs replaced by a same-version foreign build            REJECT                       W-F6 (existing)
stand-in `icu` module reporting the pinned versions             REJECT                       W-F7 (existing)
build.sh asked to attest pre-existing binaries                  impossible: no such mode;    W-F5  (FR003-b)
                                                                a build run always rebuilds
                                                                from the fresh tarball before
                                                                writing the identity
foreign ICU loaded AFTER a passed check                         outside the gate (R-F3), disclosed
```

## MINIMAL EXECUTABLE WITNESSES

- **`W-F1` (both hosts, real):** load the pinned build, then (before the check, in a fresh process) load a byte-modified copy of `icuin78.dll` / `libicui18n.so.78.3` by absolute path, then load collation -> REJECT naming both instances. Plus a unit test over a fake maps text with two `libicui18n` paths.
- **`W-F2` (unit, both inventories):** two byte-identical instances -> ACCEPT.
- **`W-F3` (real on Windows):** load a renamed or other-major ICU library, e.g. a copy of `icuuc78.dll` saved as `icuuc77.dll`, before the check -> REJECT, "not part of the verified build".
- **`W-F4`, `W-F6`, `W-F7`:** the existing tests, re-pointed at the complete inventory.
- **`W-F5` (script):**
  - `build.sh <prefix> --identity` -> non-zero exit, "no such mode".
  - Static witness: every write of the identity file follows the tarball verification, the fresh extraction and the compile in the same code path.
  - Negative control: substituting a binary in a built prefix and re-running the attest path cannot yield an identity for the substituted bytes.
- **Linux real evidence** (Docker, pinned build compiled in-container, uid 1000): W-F1 with a second mapping and W-F6. This is the host class of Codex's witness.

**Negative controls (§11.8.7.1), each of which must fail the stated witness:**

| Negative control | Must fail |
|---|---|
| First-match inventory (`setdefault` / `GetModuleHandleW`) | W-F1 |
| Hash only the three named libraries, ignoring other ICU names | W-F3 |
| Reject byte-identical duplicates | W-F2 |
| An `--identity` / re-attest mode | W-F5 |
| Version-only gate | W-F6 |
| Stand-in accepted | W-F7 |

## SPEC / MANIFEST / CONFORMANCE DELTAS

- **`spec/tools.md`:** no semantic change -- R006-C already says "any other ICU". Optionally, one sentence noting that "load" means every ICU library instance in the process at collation load.
- **Manifest:** `TOOL-040` `python`/`tests` evidence text.
- **Canonical scenarios:** no change. The gate is a host-integrity check below the canonical adapter; its witnesses are Python tests plus the script witness.
- **Rust:** the same R-F1..R-F5 obligations apply when Rust WP-13.1 is authorized; not implemented here.

## IMPLEMENTATION CONSTRAINTS

- Python only; no Rust.
- No change to the collation tuple, comparator, locale or engine; no change to I001/C012 or FR001/FR002.
- The existing host build must be rebuilt, because under R-F4 its `--identity`-produced file is not trusted.
- Linux evidence runs a disposable Docker build of the pinned ICU, cleaned up afterwards.

## CONVERGENCE CHECKPOINT

```text
PROPOSED FOR IMPLEMENTATION

OPEN FINDINGS
    L13-WP131-FR003 (FR003-a inventory, FR003-b trust root)

ACCEPTANCE WITNESSES
    W-F1..W-F7 (real on Windows; W-F1/W-F6 also real on Linux), with the negative controls above

NORMATIVE DELTAS
    none semantic (R006-C unchanged); manifest TOOL-040 evidence; scripts/pinned-icu build.sh/README;
    collation.py inventory + identity; assurance

DISCLOSED LIMITS
    R-F3 temporal boundary (after a passed check); R-F5 threat model and the rejected
    committed-hash alternative

NEXT_OWNER
    Codex -- §11.8.5 checkpoint review of exactly this proposal. The frozen candidate
    (#60 @ d7182039) is not changed until checkpoint agreement.
```
