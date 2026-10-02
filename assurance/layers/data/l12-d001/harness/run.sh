#!/bin/sh
# L12-D001 pinned-Pi authority (minion-agent#123). One runner, two execution environments:
#   container: docker run --rm -v <pi @ b7bb00b9>:/pi:ro -v <evidence dir>:/evid:ro -v <out>:/out \
#                node:22.15.1-alpine sh /evid/harness/run.sh
#   host:      PI_DIR=<pi checkout> OUT_DIR=<out> [PYTHON=<python3>] sh <evidence dir>/harness/run.sh
# No npm dependency: the probe imports Pi's harness NodeExecutionEnv directly (its other imports are type-only).
# Run on BOTH Linux and Windows; make_scenarios.py refuses to generate unless the two outputs agree.
set -eu
H=$(cd "$(dirname "$0")" && pwd)
PI=${PI_DIR:-/pi}
OUT=${OUT_DIR:-/out}
PYTHON=${PYTHON:-python3}
PIN=b7bb00b936dbe21b8e160b3e89efdec361846699
die() { echo "FAIL: $*"; exit 1; }
[ "$(node -p process.version)" = "v22.15.1" ] || die "node"
if ! command -v git >/dev/null 2>&1 || ! command -v "$PYTHON" >/dev/null 2>&1; then
  command -v apk >/dev/null 2>&1 && apk add -q --no-progress git python3 >/dev/null 2>&1 ||
    die "git/$PYTHON missing and not installable offline: use host mode or an image providing them"
fi
[ "$(git -c safe.directory='*' -C "$PI" rev-parse HEAD)" = "$PIN" ] || die "Pi checkout"
[ -z "$(git -c safe.directory='*' -C "$PI" status --porcelain -- packages)" ] || die "Pi checkout has local changes"
(cd "$PI" && sha256sum -c "$H/pi_sources.sha256")
mkdir -p "$OUT"
"$PYTHON" "$H/make_cases.py" "$OUT/cases.json"
node --experimental-strip-types --no-warnings "$H/l12_probe.mjs" "$PI" "$OUT/cases.json" "$OUT/pi-$(node -p process.platform).json"
