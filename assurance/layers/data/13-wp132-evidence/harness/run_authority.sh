#!/bin/sh
# WP-13.2 pinned-Pi authority run. One runner, two execution environments (process/authority-dependencies.md):
#   container: docker run --rm -v <pi checkout @ b7bb00b9, LF>:/pi:ro -v <this directory>:/evid:ro -v <out>:/out \
#                node:22.15.1-alpine sh /evid/harness/run_authority.sh
#   host:      PI_DIR=<pi checkout> OUT_DIR=<out> [PYTHON=<python3>] sh <this directory>/harness/run_authority.sh
# diff 8.0.4 comes from DIFF_TGZ=<diff-8.0.4.tgz> (offline) or `npm pack` (network); either way acquire_npm_pinned.sh
# verifies the bytes against pinned Pi's package-lock.json before anything runs.
# cross-spawn (imported by utils/child-process.ts, never called on this path) is a throwing stub; no Pi file changes.
set -eu
H=$(cd "$(dirname "$0")" && pwd)
EVID=$(cd "$H/.." && pwd)
PI=${PI_DIR:-/pi}
OUT=${OUT_DIR:-/out}
S=${STAGE_DIR:-/tmp/s}
PYTHON=${PYTHON:-python3}
PINNED_PI=b7bb00b936dbe21b8e160b3e89efdec361846699
die() { echo "FAIL: $*"; exit 1; }
export STAGE_DIR=$S OUT_DIR=$OUT  # mutants.mjs reads the same layout

echo "== runtime pins"
[ "$(node -p process.version)" = "v22.15.1" ] || die "node"
[ "$(node -p process.versions.v8)" = "12.4.254.21-node.24" ] || die "v8"
[ "$(node -p process.versions.icu)" = "76.1" ] || die "icu"
[ "$(node -p process.versions.unicode)" = "16.0" ] || die "unicode"
mkdir -p "$OUT"
node -p '"node " + process.version + ", v8 " + process.versions.v8 + ", icu " + process.versions.icu + ", unicode " + process.versions.unicode' | tee "$OUT/runtime.txt"

echo "== pinned Pi sources"
# OS tools (not authority inputs): installed only when missing. A fully OFFLINE container needs an image that
# already has git and python3 (or use host mode); apk cannot fetch them without network.
if ! command -v git >/dev/null 2>&1 || ! command -v "$PYTHON" >/dev/null 2>&1; then
  command -v apk >/dev/null 2>&1 && apk add -q --no-progress git python3 >/dev/null 2>&1 ||
    die "git/$PYTHON missing and not installable offline: use host mode or an image providing them"
fi
[ "$(git -c safe.directory='*' -C "$PI" rev-parse HEAD)" = "$PINNED_PI" ] || die "Pi checkout is not $PINNED_PI"
[ -z "$(git -c safe.directory='*' -C "$PI" status --porcelain -- packages/coding-agent/src)" ] || die "Pi checkout has local changes"
rm -rf "${S:?}" && mkdir -p "$S/a/pi/core/tools" "$S/a/pi/utils" "$S/a/node_modules/cross-spawn"
for f in core/tools/edit-diff.ts core/tools/path-utils.ts utils/text.ts utils/paths.ts utils/child-process.ts; do
  cp "$PI/packages/coding-agent/src/$f" "$S/a/pi/$f"
done
(cd "$S/a/pi" && sed 's/ \*/  /' "$H/pi_sources.sha256" | sha256sum -c -)

echo "== pinned diff 8.0.4"
. "$H/acquire_npm_pinned.sh"
# PROC-AUTHDEP-R001: the pinned lockfile is read from the VERIFIED pinned commit, never the working tree (a
# coherently edited working-tree lockfile could otherwise select its own digest).
git -c safe.directory='*' -C "$PI" show "$PINNED_PI:package-lock.json" > "$S/pinned-package-lock.json" || die "pinned package-lock.json"
acquire_npm_pinned diff 8.0.4 "$S/pinned-package-lock.json" "$S/a/node_modules/diff" "$S/acquire"
printf '{"name":"cross-spawn","version":"0.0.0-authority-stub","main":"index.js"}' > "$S/a/node_modules/cross-spawn/package.json"
printf 'module.exports = function () { throw new Error("cross-spawn stub: not used by the WP-13.2 authority path"); };\nmodule.exports.sync = module.exports;\n' > "$S/a/node_modules/cross-spawn/index.js"
echo '{"type":"module"}' > "$S/a/package.json"
cp "$H/edit_authority.mjs" "$S/a/"

echo "== cases (deterministic regeneration)"
"$PYTHON" "$H/make_cases.py" "$S/cases.json"
sha256sum "$S/cases.json" | cut -d' ' -f1 > "$OUT/cases.sha256"
cmp "$OUT/cases.sha256" "$EVID/cases.sha256" || die "cases differ from the recorded hash"

echo "== authority"
cd "$S/a" && node --experimental-strip-types --no-warnings edit_authority.mjs "$S/cases.json" "$OUT/authority.json"
echo "== done"
echo "== corpus discrimination (Pi-source mutants)"
cd "$S/a" && cp "$H/mutants.mjs" "$S/mutants.mjs" && node "$S/mutants.mjs"
