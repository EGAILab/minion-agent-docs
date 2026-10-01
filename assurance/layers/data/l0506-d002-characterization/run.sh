#!/bin/sh
# L0506-D001 pinned-Pi authority, in a disposable node:22.15.1-alpine container:
#   docker run --rm -v <pi @ b7bb00b9, LF>:/pi:ro -v <evidence dir>:/evid:ro -v <out>:/out node:22.15.1-alpine sh /evid/harness/run_authority.sh
set -eu
H=/evid
S=/tmp/s
die() { echo "FAIL: $*"; exit 1; }
[ "$(node -p process.version)" = "v22.15.1" ] || die "node"
apk add -q --no-progress git python3 >/dev/null
git config --global --add safe.directory /pi
[ "$(git -C /pi rev-parse HEAD)" = "b7bb00b936dbe21b8e160b3e89efdec361846699" ] || die "Pi checkout"
[ -z "$(git -C /pi status --porcelain -- packages)" ] || die "Pi checkout has local changes"
SRI="sha512-meKuifc33Pccx0O6PdIzYMq3Og8zvP4TIi/a+Bw3AEMZMxOD0+RHGQvpglEe6Zdy3wZ8nqn/j95h8LUZLk/6Hg=="
grep -A3 '"node_modules/typebox"' /pi/package-lock.json | grep -qF "$SRI" || die "lockfile SRI for typebox"
mkdir -p $S/pi/ai/src/utils $S/pi/coding-agent/src/core/tools $S/node_modules/typebox
cp /pi/packages/ai/src/utils/validation.ts $S/pi/ai/src/utils/
cp /pi/packages/coding-agent/src/core/tools/edit.ts $S/pi/coding-agent/src/core/tools/
(cd $S && sed 's/ \*/  /' $H/pi_sources.sha256 | sha256sum -c -)
(cd /tmp && npm pack --silent typebox@1.3.7 >/dev/null)
got="sha512-$(node -e 'process.stdout.write(require("crypto").createHash("sha512").update(require("fs").readFileSync(process.argv[1])).digest("base64"))' /tmp/typebox-1.3.7.tgz)"
[ "$got" = "$SRI" ] || die "typebox tarball integrity $got"
tar -xzf /tmp/typebox-1.3.7.tgz -C /tmp && cp -r /tmp/package/. $S/node_modules/typebox/
echo '{"type":"module"}' > $S/package.json
cp $H/cases.json $S/cases.json

cp $H/probe.mjs $S/
cd $S && node --experimental-strip-types --no-warnings probe.mjs $S/cases.json /out/pi.json
