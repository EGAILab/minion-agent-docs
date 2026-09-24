# CE-L13-WP131-01 — Lane C revision 5: `R006-C` Correction 3c executed

Mode: §11.8 sub-checkpoint evidence, Lane C, `R006-C` only. Revisions 1–4 stand unchanged as the
historical record. This revision changes no candidate definition, corpus, option mapping, or pass
criterion from revision 4. It records that the differential run revision 4 left open (Correction
3c) has now executed, and its result.

## What changed since revision 4

Revision 4 left Correction 3c open. The 2026-09-22 owner ruling
(`data/13-wp131-ce-l13-wp131-01/r006-c-differential-probe-feasibility-blocked.txt`) then set R006-C
to `FEASIBILITY_BLOCKED` until a disposable CI/container/VM could build the exact pinned tuple, and
forbade host-level tooling changes. That environment was already on the host: Docker with a running
Linux engine. The run used only throwaway `docker run --rm` containers. Nothing was installed on the
host, and the Docker volume and image the run used were removed afterwards.

## Result

Full record: `data/13-wp131-ce-l13-wp131-01/r006-c-differential/RECORD.txt`, with the harness and
raw outputs alongside it.

```text
tuple        PyICU 2.16.2 + rust_icu_ucol 5.8.0 (all rust_icu_* crates 5.8.0),
             both linked to ONE build of icu4c-78.3-sources.tgz
             (SHA-512 verified against the release's SHASUM512.txt)
             ldd-verified: both engines resolve ICU only from that build
locale       en-001; STRENGTH=TERTIARY, NUMERIC_COLLATION=OFF, CASE_FIRST=OFF
             (effective attributes read back and identical in both engines)
corpus       the 24-name Part 6 witness set; raw and harness-lowercased modes
comparisons  576 ordered pairs per mode + stable sort order
result       0 disagreements in either mode; sort orders identical  -> PASS
controls     NUMERIC_COLLATION=ON in Rust -> FAIL on exactly file10/file2;
             one flipped matrix cell -> FAIL
```

One finding came out of the build rather than the comparison. The container image shipped Debian's
`libicu-dev` 72.1, and PyICU's link line resolved `-licui18n` to it ahead of the pinned build. That
is the exact skew Correction 3b guards against. The harness now removes the system ICU dev files and
fails outright if either engine resolves ICU from anywhere other than the pinned build. Any
implementation that adopts R006-C needs the same guard in its own build.

## Lane-C status (this revision)

```text
R006-A: RESOLVED (unchanged)
R006-B: RESOLVED (unchanged)
R006-C: Correction 3c differential run EXECUTED -- PASS.
        Pending independent replay. Not RESOLVED or owner-selected by this revision.
R006:   OWNER_DECISION_REQUIRED -- the owner still chooses among A/B/C. R006-C is no
        longer blocked on feasibility once the independent replay confirms this result.
```

No Python or Rust implementation, no `spec/tools.md` or manifest change, no WP-13.1 implementation,
no reopening of any closed lane, no Layer 14.
