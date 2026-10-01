#!/bin/sh
# L05-D001 schema-domain characterization: pinned-Pi authority. One runner, two execution environments
# (process/authority-dependencies.md):
#   container: docker run --rm -v <pi @ b7bb00b9>:/pi:ro -v <evidence dir>:/evid:ro -v <out>:/out \
#                node:22.15.1-alpine sh /evid/harness/run.sh
#   host:      PI_DIR=<pi checkout> OUT_DIR=<out> [PYTHON=<python3>] sh <evidence dir>/harness/run.sh
# typebox 1.3.7 comes from TYPEBOX_TGZ=<typebox-1.3.7.tgz> (offline) or `npm pack` (network); either way
# acquire_npm_pinned.sh verifies the bytes against pinned Pi's lockfile before anything runs.
set -eu
H=$(cd "$(dirname "$0")" && pwd)
PI=${PI_DIR:-/pi}
OUT=${OUT_DIR:-/out}
S=${STAGE_DIR:-$(mktemp -d)}
PYTHON=${PYTHON:-python3}
PIN=b7bb00b936dbe21b8e160b3e89efdec361846699
die() { echo "FAIL: $*"; exit 1; }
[ "$(node -p process.version)" = "v22.15.1" ] || die "node"
# OS tools (not authority inputs): installed only when missing. A fully OFFLINE container needs an image that
# already has git and python3 (or use host mode); apk cannot fetch them without network.
if ! command -v git >/dev/null 2>&1 || ! command -v "$PYTHON" >/dev/null 2>&1; then
  command -v apk >/dev/null 2>&1 && apk add -q --no-progress git python3 >/dev/null 2>&1 ||
    die "git/$PYTHON missing and not installable offline: use host mode or an image providing them"
fi
[ "$(git -c safe.directory='*' -C "$PI" rev-parse HEAD)" = "$PIN" ] || die "Pi checkout"
[ -z "$(git -c safe.directory='*' -C "$PI" status --porcelain -- packages)" ] || die "Pi checkout has local changes"
mkdir -p "$S/pi/ai/src/utils" "$OUT"
cp "$PI/packages/ai/src/utils/validation.ts" "$S/pi/ai/src/utils/"
(cd "$S" && sed 's/ \*/  /' "$H/pi_sources.sha256" | sha256sum -c -)
. "$H/acquire_npm_pinned.sh"
# PROC-AUTHDEP-R001: the pinned lockfile is read from the VERIFIED pinned commit, never the working tree.
git -c safe.directory='*' -C "$PI" show "$PIN:package-lock.json" > "$S/pinned-package-lock.json" || die "pinned package-lock.json"
acquire_npm_pinned typebox 1.3.7 "$S/pinned-package-lock.json" "$S/node_modules/typebox" "$S/acquire"
echo '{"type":"module"}' > "$S/package.json"
"$PYTHON" "$H/make_cases.py" "$S/cases.json"
sha256sum "$S/cases.json" | cut -d' ' -f1 > "$OUT/cases.sha256"
cp "$H/schema_probe.mjs" "$S/"
cd "$S" && node --experimental-strip-types --no-warnings schema_probe.mjs "$S/cases.json" "$OUT/schema.json"
