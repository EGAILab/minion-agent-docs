#!/bin/sh
# L0206-D001 (K1) boundary authority: validation / hook mutation / execute / edit preparation / diagnostic key order
# (k1_probe.mjs), and the canonical-case authority over every argument boundary (make_cases.py + k1_boundaries.mjs).
#   host:      PI_DIR=<pi> OUT_DIR=<out> [TYPEBOX_TGZ=<typebox-1.3.7.tgz>] sh harness/run.sh
#   container: docker run --rm -v <pi>:/pi:ro -v <evid>:/evid:ro -v <out>:/out node:22.15.1-alpine sh /evid/harness/run.sh
set -eu
H=$(cd "$(dirname "$0")" && pwd)
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
(cd "$S" && sed 's/ \*/  /' "$H/pi_sources.sha256" | sha256sum -c -)
. "$H/acquire_npm_pinned.sh"
git -c safe.directory='*' -C "$PI" show "$PIN:package-lock.json" > "$S/pinned-package-lock.json" || die "pinned package-lock.json"
acquire_npm_pinned typebox 1.3.7 "$S/pinned-package-lock.json" "$S/node_modules/typebox" "$S/acquire"
echo '{"type":"module"}' > "$S/package.json"
cp "$H/k1_probe.mjs" "$H/k1_boundaries.mjs" "$S/"
command -v "${PYTHON:-python3}" >/dev/null 2>&1 || { command -v apk >/dev/null 2>&1 && apk add -q --no-progress python3 >/dev/null 2>&1; } || die "python missing"
"${PYTHON:-python3}" "$H/make_cases.py" "$OUT/cases.json"
cd "$S" && node --experimental-strip-types --no-warnings k1_probe.mjs "$OUT/k1.json"
node --experimental-strip-types --no-warnings k1_boundaries.mjs "$OUT/cases.json" "$OUT/k1-boundaries.json"
