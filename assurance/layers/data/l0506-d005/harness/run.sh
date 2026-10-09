#!/bin/sh
# L0506-D005 (minion-agent#129): raw/validated tool-argument isolation in pinned Pi (pi_isolation.mjs), on the K1
# staging (Pi sources checked against ../../l0206-d001-k1/harness/pi_sources.sha256; typebox 1.3.7 from the pinned lock),
# then the canonical oracle (../gen/pi_oracle.mjs over ../gen/cases.json -> pi-oracle.json).
#   container: docker run --rm -v <pi>:/pi:ro -v <assurance/layers/data>:/evid:ro -v <out>:/out node:22.15.1-alpine \
#                sh /evid/l0506-d005/harness/run.sh
set -eu
H=$(cd "$(dirname "$0")" && pwd)
K1=$H/../../l0206-d001-k1/harness
PI=${PI_DIR:-/pi}
OUT=${OUT_DIR:-/out}
S=${STAGE_DIR:-$(mktemp -d)}
PIN=b7bb00b936dbe21b8e160b3e89efdec361846699
die() { echo "FAIL: $*"; exit 1; }
[ "$(node -p process.version)" = "v22.15.1" ] || die "node"
command -v git >/dev/null 2>&1 || { command -v apk >/dev/null 2>&1 && apk add -q --no-progress git >/dev/null 2>&1; } || die "git missing"
[ "$(git -c safe.directory='*' -C "$PI" rev-parse HEAD)" = "$PIN" ] || die "Pi checkout"
[ -z "$(git -c safe.directory='*' -C "$PI" status --porcelain -- packages)" ] || die "Pi checkout has local changes"
mkdir -p "$S/pi/agent/src" "$S/pi/ai/src/utils" "$S/pi/coding-agent/src/core/tools" "$OUT"
cp "$PI/packages/agent/src/agent-loop.ts" "$S/pi/agent/src/"
cp "$PI/packages/ai/src/utils/validation.ts" "$S/pi/ai/src/utils/"
cp "$PI/packages/coding-agent/src/core/tools/edit.ts" "$S/pi/coding-agent/src/core/tools/"
(cd "$S" && sed 's/ \*/  /' "$K1/pi_sources.sha256" | sha256sum -c -)
. "$K1/acquire_npm_pinned.sh"
git -c safe.directory='*' -C "$PI" show "$PIN:package-lock.json" > "$S/pinned-package-lock.json" || die "pinned package-lock.json"
acquire_npm_pinned typebox 1.3.7 "$S/pinned-package-lock.json" "$S/node_modules/typebox" "$S/acquire"
echo '{"type":"module"}' > "$S/package.json"
cp "$H/pi_isolation.mjs" "$S/"
cd "$S" && node --experimental-strip-types --no-warnings pi_isolation.mjs "$OUT/pi-isolation.json"
cp "$H/../gen/pi_oracle.mjs" "$S/"
node --experimental-strip-types --no-warnings pi_oracle.mjs "$H/../gen/cases.json" "$OUT/pi-oracle.json"
