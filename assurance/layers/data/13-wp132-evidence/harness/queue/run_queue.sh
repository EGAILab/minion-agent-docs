#!/bin/sh
# WP-13.2 queue authority: pinned Pi b7bb00b9 file-mutation-queue.ts, unmodified, under Node 22.15.1.
#   docker run --rm -v <pi checkout @ b7bb00b9>:/pi:ro -v <evidence dir>:/evid:ro -v <out>:/out \
#       node:22.15.1-alpine sh /evid/harness/queue/run_queue.sh
set -eu
Q=/evid/harness/queue
S=/tmp/q
die() { echo "FAIL: $*"; exit 1; }
[ "$(node -p process.version)" = "v22.15.1" ] || die "node"
apk add -q --no-progress git >/dev/null
git config --global --add safe.directory /pi
[ "$(git -C /pi rev-parse HEAD)" = "b7bb00b936dbe21b8e160b3e89efdec361846699" ] || die "Pi checkout"
[ -z "$(git -C /pi status --porcelain -- packages/coding-agent/src)" ] || die "Pi checkout has local changes"
mkdir -p $S/pi/core/tools
cp /pi/packages/coding-agent/src/core/tools/file-mutation-queue.ts $S/pi/core/tools/
echo "33cb06ac9bcdf32c8b84d9d12e33be44c503a7670f668e003a3262cd34294d11  $S/pi/core/tools/file-mutation-queue.ts" | sha256sum -c -
cp $Q/fs_shim.mjs $Q/loader.mjs $Q/queue_authority.mjs $S/
echo '{"type":"module"}' > $S/package.json
cd $S && node --experimental-strip-types --no-warnings --import ./loader.mjs queue_authority.mjs /out/queue_authority.json
