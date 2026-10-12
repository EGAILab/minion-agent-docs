#!/bin/bash
# WP133-D001 (#217) on Linux: the pinned-Pi abort-trigger probe, as uid 1000. Host mounts are read-only and inside the
# project root (proven by the reviewed guard first); the output is printed to stdout; work happens in the container's
# private tmpfs /tmp.
# Usage: bash run-linux-abort.sh [repeat]
set -eu
R=E:/AI/Projects/OpenMinds/Minions/Minion-Agent
DATA=$R/review-worktrees/wp133d-docs/assurance/layers/data
GUARD=$R/review-worktrees/l12d008-docs/assurance/layers/data/l12-d007/fs-guard
PI=$R/ref-repos/pi
NODE=$R/.tmp/cache/node-22.15.1-linux
node --input-type=module -e 'import {pathToFileURL} from "node:url"; const g = await import(pathToFileURL(process.argv[1]).href); for (const p of process.argv.slice(2)) g.proveReferentAbs(p);' "$GUARD/fs-guard.mjs" "$DATA" "$GUARD" "$PI" "$NODE"
MSYS_NO_PATHCONV=1 docker run --rm --tmpfs /tmp:exec,size=1g \
  --mount "type=bind,source=$DATA/13-wp133-abort-trigger,target=/probe,readonly" \
  --mount "type=bind,source=$GUARD,target=/guard,readonly" \
  --mount "type=bind,source=$PI,target=/pi,readonly" \
  --mount "type=bind,source=$NODE,target=/node,readonly" \
  -e REPEAT="${1:-5}" \
  python:3.13 sh -ec '
    mkdir -p /tmp/guard-root/scratch /tmp/home /tmp/w/l12-d007/fs-guard /tmp/w/13-wp133-abort-trigger
    cp -r /guard/. /tmp/w/l12-d007/fs-guard/ && cp /probe/abort_trigger_probe.mjs /tmp/w/13-wp133-abort-trigger/
    cp /node/node /tmp/node && chmod +x /tmp/node
    chown -R 1000:1000 /tmp/guard-root /tmp/home /tmp/w
    cd /tmp/w/13-wp133-abort-trigger
    setpriv --reuid=1000 --regid=1000 --clear-groups env HOME=/tmp/home TMPDIR=/tmp FS_GUARD_ROOT=/tmp/guard-root \
      /tmp/node --experimental-strip-types --no-warnings abort_trigger_probe.mjs /pi /tmp/guard-root/scratch /tmp/w/out.json "$REPEAT" >&2
    cat /tmp/w/out.json
  '
