#!/bin/bash
# Linux pinned-Pi run of rm-replace-probe.mjs (L12D007-I002 witness). Host mounts are all read-only and inside
# the project root, each proven by the reviewed guard before launch; output goes to stdout; work in tmpfs /tmp.
set -eu
R=E:/AI/Projects/OpenMinds/Minions/Minion-Agent
DATA=$R/review-worktrees/l12d007-docs/assurance/layers/data/l12-d007
PI=$R/ref-repos/pi
NODE=$R/.tmp/cache/node-22.15.1-linux
node --input-type=module -e 'import {pathToFileURL} from "node:url"; const g = await import(pathToFileURL(process.argv[1]).href); for (const p of process.argv.slice(2)) g.proveReferentAbs(p);' "$DATA/fs-guard/fs-guard.mjs" "$DATA" "$PI" "$NODE"
MSYS_NO_PATHCONV=1 docker run --rm --tmpfs /tmp:exec,size=1g \
  --mount "type=bind,source=$DATA,target=/data,readonly" \
  --mount "type=bind,source=$PI,target=/pi,readonly" \
  --mount "type=bind,source=$NODE,target=/node,readonly" \
  python:3.13 sh -ec 'mkdir -p /tmp/guard-root/scratch; cp /node/node /tmp/node; chmod +x /tmp/node; cd /data; FS_GUARD_ROOT=/tmp/guard-root /tmp/node --experimental-strip-types --no-warnings rm-replace-probe.mjs /pi /tmp/guard-root/scratch'
