#!/bin/sh
# Linux half of the L12-D011 generation, in a private container (python:3.13 image + the pinned Node binary), with a
# read-only root. Read-only binds: /pi, /node, /artifacts (pinned fd/rg archives), /data (assurance/layers/data, so the
# generator's relative fs-guard import resolves). Writable bind: /out (the run directory, proven by run-gen.mjs).
# Every other write below is to a FIXED literal inside the private tmpfs /tmp (container-internal, Owner 2026-10-10);
# containment-controls.mjs checks that inventory mechanically. The generator runs as uid 1000 with the reviewed
# fs-guard rooted at /tmp/guard-root (FS_GUARD_ROOT) and writes its private output through assertOutput there; the
# host-bound /out/linux-partial.json is then written ONLY by transfer.mjs (io.transfer), whose guard proves that final
# entry inside FS_GUARD_OUTPUT=/out immediately before the write (L12D011-C001, review 2).
set -eu
mkdir -p /tmp/guard-root/w/cwd /tmp/fd /tmp/rg /tmp/home
tar -xzf /artifacts/fd-v10.4.2-x86_64-unknown-linux-gnu.tar.gz -C /tmp/fd
tar -xzf /artifacts/ripgrep-15.2.0-x86_64-unknown-linux-musl.tar.gz -C /tmp/rg
FD=$(find /tmp/fd -name fd -type f | head -1); RG=$(find /tmp/rg -name rg -type f | head -1)
cp /node /tmp/node && chmod +x /tmp/node
chown -R 1000:1000 /tmp/guard-root /tmp/home
setpriv --reuid=1000 --regid=1000 --clear-groups env HOME=/tmp/home TMPDIR=/tmp FS_GUARD_ROOT=/tmp/guard-root \
  PATH=/tmp:/usr/local/bin:/usr/bin:/bin \
  /tmp/node --experimental-strip-types --no-warnings /data/l12-d011/gen/gen_spawn_nul.mjs /pi "$FD" "$RG" \
  /tmp/guard-root/w /tmp/guard-root/w/linux-partial.json
# The ONE host-bound write: the guarded transfer (io.transfer -> writeOutput -> assertOutput on the final /out entry).
FS_GUARD_ROOT=/tmp/guard-root FS_GUARD_OUTPUT=/out /tmp/node --no-warnings /data/l12-d011/gen/transfer.mjs \
  /tmp/guard-root/w/linux-partial.json /out/linux-partial.json
echo "GEN LINUX DONE"
