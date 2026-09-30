#!/bin/sh
# WP-13.2 pinned-Pi authority run, inside a disposable node:22.15.1-alpine container:
#   docker run --rm -v <pi checkout @ b7bb00b9, LF>:/pi:ro -v <this directory>:/evid:ro -v <out>:/out \
#       node:22.15.1-alpine sh /evid/harness/run_authority.sh
# diff 8.0.4 is fetched with `npm pack` and checked against the integrity in pinned Pi's package-lock.json.
# cross-spawn (imported by utils/child-process.ts, never called on this path) is a throwing stub; no Pi file changes.
set -eu
H=/evid/harness
S=/tmp/s
PINNED_PI=b7bb00b936dbe21b8e160b3e89efdec361846699
SRI="sha512-DPi0FmjiSU5EvQV0++GFDOJ9ASQUVFh5kD+OzOnYdi7n3Wpm9hWWGfB/O2blfHcMVTL5WkQXSnRiK9makhrcnw=="
die() { echo "FAIL: $*"; exit 1; }

echo "== runtime pins"
[ "$(node -p process.version)" = "v22.15.1" ] || die "node"
[ "$(node -p process.versions.v8)" = "12.4.254.21-node.24" ] || die "v8"
[ "$(node -p process.versions.icu)" = "76.1" ] || die "icu"
[ "$(node -p process.versions.unicode)" = "16.0" ] || die "unicode"
node -p '"node " + process.version + ", v8 " + process.versions.v8 + ", icu " + process.versions.icu + ", unicode " + process.versions.unicode' | tee /out/runtime.txt

echo "== pinned Pi sources"
apk add -q --no-progress git python3 >/dev/null
git config --global --add safe.directory /pi
[ "$(git -C /pi rev-parse HEAD)" = "$PINNED_PI" ] || die "Pi checkout is not $PINNED_PI"
[ -z "$(git -C /pi status --porcelain -- packages/coding-agent/src)" ] || die "Pi checkout has local changes"
grep -A3 '"node_modules/diff"' /pi/package-lock.json | grep -qF "$SRI" || die "lockfile SRI for diff"
mkdir -p $S/a/pi/core/tools $S/a/pi/utils $S/a/node_modules/diff $S/a/node_modules/cross-spawn
for f in core/tools/edit-diff.ts core/tools/path-utils.ts utils/text.ts utils/paths.ts utils/child-process.ts; do
  cp /pi/packages/coding-agent/src/$f $S/a/pi/$f
done
(cd $S/a/pi && sed 's/ \*/  /' $H/pi_sources.sha256 | sha256sum -c -)

echo "== pinned diff 8.0.4"
(cd $S && npm pack --silent diff@8.0.4 >/dev/null)
got="sha512-$(node -e 'process.stdout.write(require("crypto").createHash("sha512").update(require("fs").readFileSync(process.argv[1])).digest("base64"))' $S/diff-8.0.4.tgz)"
[ "$got" = "$SRI" ] || die "diff tarball integrity $got"
tar -xzf $S/diff-8.0.4.tgz -C $S && cp -r $S/package/. $S/a/node_modules/diff/
printf '{"name":"cross-spawn","version":"0.0.0-authority-stub","main":"index.js"}' > $S/a/node_modules/cross-spawn/package.json
printf 'module.exports = function () { throw new Error("cross-spawn stub: not used by the WP-13.2 authority path"); };\nmodule.exports.sync = module.exports;\n' > $S/a/node_modules/cross-spawn/index.js
echo '{"type":"module"}' > $S/a/package.json
cp $H/edit_authority.mjs $S/a/

echo "== cases (deterministic regeneration)"
python3 $H/make_cases.py $S/cases.json
sha256sum $S/cases.json | cut -d' ' -f1 > /out/cases.sha256
cmp /out/cases.sha256 /evid/cases.sha256 || die "cases differ from the recorded hash"

echo "== authority"
cd $S/a && node --experimental-strip-types --no-warnings edit_authority.mjs $S/cases.json /out/authority.json
echo "== done"
echo "== corpus discrimination (Pi-source mutants)"
cd $S/a && cp $H/mutants.mjs /tmp/mutants.mjs && node /tmp/mutants.mjs
