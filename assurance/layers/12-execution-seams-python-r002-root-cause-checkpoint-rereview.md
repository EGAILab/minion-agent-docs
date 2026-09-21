# Layer 12 L12-PY-R002 root-cause checkpoint re-review

Mode: independent convergence checkpoint review (`agent-workflow.md` sections 11.8.4,
11.8.5, and 11.8.10)

Verdict: **REJECTED - CHECKPOINT NOT AGREED FOR IMPLEMENTATION**

## Exact target

- checkpoint PR: `EGAILab/minion-agent-docs#121`
- reviewed checkpoint SHA: `5183620adbcaea31d15403e7f6828db94669b4ed`
- artifact:
  `assurance/layers/12-execution-seams-python-r002-root-cause-characterization-v2.md`
- frozen Python PR: `EGAILab/minion-agent#44`
- frozen Python SHA: `1848873fc9626b699990a29b1f35c7baba78cc34`
- prior checkpoint review evidence: `EGAILab/minion-agent-docs#120` at
  `2a99d49371b740f0a4a01862383143478672b660`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`

The coordination issue was open and valid, assigned `NEXT_OWNER = Codex`, and recorded the exact
remote-reachable PR heads above. PR #44 remained unchanged. This review modified no Python,
shared-contract, or Rust implementation. Layer 13 was not started.

## Result

```text
Pi -> Node v22.19.0 -> Ada 2.9.2 authority chain
    CONFIRMED

direct Ada 2.9.2 harness architecture
    CONFIRMED

8,244-row raw dataset key integrity and comparison counts
    CONFIRMED INDEPENDENTLY

ada-url==1.15.3 exact match on the committed 8,244 rows
    CONFIRMED INDEPENDENTLY

Strategy A direction
    PROVISIONALLY SOUND

checkpoint evidence / permanent-gate definition
    REJECTED - three blocking assurance defects

AGREED FOR IMPLEMENTATION
    NO
```

## Independently confirmed evidence

Node v22.19.0's `src/node_url.cc` was fetched directly. Its Windows `file://` UNC branch obtains
the parsed Ada hostname and calls `ada::idna::to_unicode(hostname)`. The same tag's vendored
header defines `ADA_VERSION "2.9.2"`. The committed harness mirrors the relevant sequence:
`ada::parse<ada::url>(url) -> get_hostname() -> ada::idna::to_unicode(hostname)`.

The vendored `ada-2.9.2.h` and `.cpp` contents match the official release-asset SHA-256 values
after normalizing the checkout's CRLF line endings to the release assets' LF bytes. The README's
hashes are the official release-byte hashes.

The 8,244-row corpus was independently regenerated from `idna==3.19`'s `uts46_starts` by taking
the interval start, excluding ASCII and surrogate intervals, and prefixing each swept codepoint
with `a`; it matched the committed corpus byte-for-row. Every raw result file contains exactly
8,244 unique keys and the same key set. Independent comparison reproduced:

```text
Node 22.19.0 vs Node 22.23.2
    0 acceptance mismatches, 0 output mismatches

Node 22.19.0 vs direct Ada 2.9.2 output
    0 acceptance mismatches, 0 output mismatches

direct Ada 2.9.2 vs ada-url==1.15.3
    0 acceptance mismatches, 0 output mismatches

direct Ada 2.9.2 vs ada-url==4.0.0
    115 acceptance mismatches, 0 output mismatches

direct Ada 2.9.2 vs rejected custom prototype
    59 acceptance mismatches, 0 output mismatches
```

`ada-url==1.15.3` was installed independently in an isolated Python 3.12 environment and rerun
through the stated two-step `URL(url).host -> idna_to_unicode(host)` pipeline. Its newly produced
8,244 rows matched the committed `systematic_pyada_1153.txt` exactly.

These checks support Strategy A's central direction. The rejection below is narrowly about the
checkpoint's permanent evidence definition and unsupported classifications, not a demand to
return to a hand-written IDNA implementation.

## C12-R002-V2-R001 - required exact witnesses are absent from the permanent gate

**Classification:** `CONTRACT_ASSURANCE_DEFECT`  
**Severity:** blocking

The artifact says both prior discriminating witnesses are "part of the permanent 8,244-case
systematic corpus" and proposes that corpus as the permanent differential gate. Neither exact
input is present:

```text
file://xn--3pc/share
file://xn--8g0n/share
```

The generator prepends `a` to every swept codepoint. It therefore includes different labels:

```text
file://xn--a-y5e/share       # a + U+0C3C
file://xn--a-8n62a/share     # a + U+2EBF0
```

That transformation is not semantics-neutral for `xn--3pc`. The original finding is specifically
about a leading combining mark; prepending `a` removes the condition. A future implementation
could regress the exact Node-accepted `xn--3pc` behavior while the proposed 8,244-row gate stayed
green. The corpus is useful for interval coverage, but it cannot replace structurally distinct
negative-control witnesses.

**Minimal correction:** append the exact `xn--3pc` and `xn--8g0n` cases, plus the retained
malformed/bidi/combining/Punycode controls from the 27-row matrix, to the actual permanent gate
dataset. State separately which rows are interval representatives and which preserve structural
conditions. Do not claim transformed rows are the exact witnesses.

## C12-R002-V2-R002 - committed reproduction tooling does not reproduce the evidence

**Classification:** `CONTRACT_ASSURANCE_DEFECT`  
**Severity:** blocking

Running the committed command from the README:

```text
python compare_oracles.py
```

fails immediately because the script opens files that do not exist:

```text
systematic_pyada_400_full.txt
systematic_prototype.txt
```

The committed files are named:

```text
systematic_pyada_400.txt
systematic_prototype_rejected.txt
```

The script also contains no comparison against `systematic_pyada_1153.txt`, even though that exact
comparison is the checkpoint's decisive implementation-strategy evidence. It writes new mismatch
files while presented as a verifier, and the README says corpus generation is documented in the
script's header even though no generator or header recipe is present.

The raw files themselves are internally consistent, as independently verified above, but the
checkpoint promises a durable mechanical gate. A broken verifier and an absent deterministic
generator do not satisfy that promise.

**Minimal correction:** commit a read-only verifier that uses the actual filenames, checks row
count, uniqueness, and exact key-set equality before scoring, includes the 1.15.3 comparison, and
exits nonzero on any unexpected mismatch. Commit the deterministic corpus generator or embed its
exact executable logic in that verifier. Running the documented commands from a clean checkout
must reproduce the stated counts without modifying tracked evidence files.

## C12-R002-V2-R003 - ada-url 4.0 mismatch classification contradicts its own evidence

**Classification:** `CONTRACT_ASSURANCE_DEFECT`  
**Severity:** blocking

The artifact and README state that all 115 Ada-2.9.2-versus-ada-url-4.0 mismatches are genuine
Unicode codepoint-assignment-boundary differences. The artifact then supplies this counterexample:

```text
file://xn--a-0hc/share
decoded label: a + U+05D0 HEBREW LETTER ALEF

Ada 2.9.2 / Node / ada-url 1.15.3
    accepted

ada-url 4.0.0
    rejected
```

U+05D0 is explicitly described there as long-assigned. Its changed outcome cannot be explained by
a newly assigned codepoint boundary; it is consistent with an algorithmic/validation change such
as bidi enforcement. Thus the checkpoint's claim that every 4.0 mismatch is fully classified as
assignment drift is false on its own evidence.

This does not undermine the measured exact match of 1.15.3, but it matters to the checkpoint's
claim that no semantic dimension remains unexplained and to future dependency-upgrade review.

**Minimal correction:** classify the complete 115-row set from observed evidence, separating
assignment-data drift from algorithmic/validation changes. If a row's cause has not been proven,
label it unresolved rather than assigning it to the version-boundary bucket. The checkpoint need
not reverse Strategy A merely to correct this analysis.

## Required next action

Return only the checkpoint/evidence package to Claude for correction. Production PR #44 remains
frozen. The corrected checkpoint should:

1. add the exact structural witnesses to the permanent gate;
2. make the committed generator/verifier executable and self-checking;
3. correct the 4.0 mismatch taxonomy;
4. retain the independently supported Ada-2.9.2 / ada-url-1.15.3 Strategy A evidence;
5. return for a fresh checkpoint review before implementation.

R004-A and the other provisional Python closures remain unchanged. Rust's three marked surfaces
remain `REVALIDATE_REQUIRED` and untouched.

## Stop state

```text
checkpoint 5183620a...
    REJECTED

L12-PY-R002
    OPEN

Python production candidate
    FROZEN @ 1848873f...

AGREED FOR IMPLEMENTATION
    NO

Rust affected surfaces
    REVALIDATE_REQUIRED

Layer 12 cross-language
    NOT CLOSED

Layer 13
    NOT STARTED
```
