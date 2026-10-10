#!/bin/sh
# L12-D007 Linux oracle run (inside node:22.15.1-bookworm-slim, uid 1000). Mounts:
#   /pi   pinned Pi checkout (read-only)      /data  assurance/layers/data/l12-d007 (read-only)
#   /out  the only writable host mount (inside the project root)
# Every sandbox lives in the container's private tmpfs /tmp (FS_GUARD_ROOT).
set -eu
export FS_GUARD_ROOT=/tmp/guard-root
export FS_GUARD_OUTPUT=/out
export HOME=/tmp/home
mkdir -p "$FS_GUARD_ROOT" "$HOME"
cp -r /data /tmp/data
cd /tmp/data/gen
node --experimental-strip-types --no-warnings pi_oracle.mjs /pi cases.json /out/oracle-linux.json
