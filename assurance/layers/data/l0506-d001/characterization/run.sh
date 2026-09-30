#!/bin/sh
# docker run --rm -v <pi @ b7bb00b9>:/pi:ro -v <this dir>:/evid:ro node:22.15.1-alpine sh /evid/run.sh
set -eu
[ "$(node -p process.version)" = "v22.15.1" ] || { echo "node"; exit 1; }
apk add -q --no-progress git >/dev/null
git config --global --add safe.directory /pi
[ "$(git -C /pi rev-parse HEAD)" = "b7bb00b936dbe21b8e160b3e89efdec361846699" ] || { echo "pi"; exit 1; }
SRI="sha512-meKuifc33Pccx0O6PdIzYMq3Og8zvP4TIi/a+Bw3AEMZMxOD0+RHGQvpglEe6Zdy3wZ8nqn/j95h8LUZLk/6Hg=="
grep -A3 '"node_modules/typebox"' /pi/package-lock.json | grep -qF "$SRI" || { echo "lockfile SRI"; exit 1; }
S=/tmp/s && mkdir -p $S/pi/ai/src/utils $S/node_modules/typebox
cp /pi/packages/ai/src/utils/validation.ts $S/pi/ai/src/utils/
sha256sum $S/pi/ai/src/utils/validation.ts
(cd /tmp && npm pack --silent typebox@1.3.7 >/dev/null)
got="sha512-$(node -e 'process.stdout.write(require("crypto").createHash("sha512").update(require("fs").readFileSync(process.argv[1])).digest("base64"))' /tmp/typebox-1.3.7.tgz)"
[ "$got" = "$SRI" ] || { echo "typebox tarball integrity $got"; exit 1; }
tar -xzf /tmp/typebox-1.3.7.tgz -C /tmp && cp -r /tmp/package/. $S/node_modules/typebox/
echo '{"type":"module"}' > $S/package.json
cp /evid/probe.mjs $S/
cd $S && node --experimental-strip-types --no-warnings probe.mjs
