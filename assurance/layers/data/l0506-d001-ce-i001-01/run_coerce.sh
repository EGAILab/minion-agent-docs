#!/bin/sh
set -eu
apk add -q --no-progress git >/dev/null; git config --global --add safe.directory /pi
[ "$(git -C /pi rev-parse HEAD)" = "b7bb00b936dbe21b8e160b3e89efdec361846699" ]
SRI="sha512-meKuifc33Pccx0O6PdIzYMq3Og8zvP4TIi/a+Bw3AEMZMxOD0+RHGQvpglEe6Zdy3wZ8nqn/j95h8LUZLk/6Hg=="
S=/tmp/s; mkdir -p $S/pi/ai/src/utils $S/node_modules/typebox
cp /pi/packages/ai/src/utils/validation.ts $S/pi/ai/src/utils/
echo "460786b57dead200e411b9afec916a5049c96ebcff4da082096456ac06d44fb7  $S/pi/ai/src/utils/validation.ts" | sha256sum -c -
(cd /tmp && npm pack --silent typebox@1.3.7 >/dev/null)
got="sha512-$(node -e 'process.stdout.write(require("crypto").createHash("sha512").update(require("fs").readFileSync(process.argv[1])).digest("base64"))' /tmp/typebox-1.3.7.tgz)"
[ "$got" = "$SRI" ]
tar -xzf /tmp/typebox-1.3.7.tgz -C /tmp && cp -r /tmp/package/. $S/node_modules/typebox/
echo '{"type":"module"}' > $S/package.json; cp /evid/authority.mjs $S/
cp /evid/coerce_probe.mjs $S/ && cd $S && node --experimental-strip-types --no-warnings coerce_probe.mjs
