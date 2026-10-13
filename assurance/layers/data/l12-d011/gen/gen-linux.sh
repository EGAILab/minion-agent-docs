#!/bin/sh
# Linux half of the L12-D011 generation, in a private container (python:3.13 image + the pinned Node binary).
# Read-only: /pi, /node, /artifacts (pinned fd/rg archives), /gen (this directory). Writable: /out only.
# Runs as uid 1000 in the private tmpfs; writes /out/linux-partial.json.
set -eu
mkdir -p /tmp/w/cwd /tmp/fd /tmp/rg /tmp/home
tar -xzf /artifacts/fd-v10.4.2-x86_64-unknown-linux-gnu.tar.gz -C /tmp/fd
tar -xzf /artifacts/ripgrep-15.2.0-x86_64-unknown-linux-musl.tar.gz -C /tmp/rg
FD=$(find /tmp/fd -name fd -type f | head -1); RG=$(find /tmp/rg -name rg -type f | head -1)
cp /node /tmp/node && chmod +x /tmp/node
cp -r /gen /tmp/gen
chown -R 1000:1000 /tmp/w /tmp/home /tmp/gen
setpriv --reuid=1000 --regid=1000 --clear-groups env HOME=/tmp/home TMPDIR=/tmp PATH=/tmp:/usr/local/bin:/usr/bin:/bin \
  /tmp/node --experimental-strip-types --no-warnings /tmp/gen/gen_spawn_nul.mjs /pi "$FD" "$RG" /tmp/w /tmp/w/linux-partial.json
cp /tmp/w/linux-partial.json /out/
echo "GEN LINUX DONE"
