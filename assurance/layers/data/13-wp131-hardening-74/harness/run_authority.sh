#!/bin/sh
# #74 pinned-Pi authority run, inside a disposable node:22.15.1-alpine container:
#   docker run --rm -v <pi checkout @ b7bb00b9>:/pi:ro -v <this directory>:/evid:ro -v <out>:/out \
#       node:22.15.1-alpine sh /evid/harness/run_authority.sh
# Nothing is installed outside the container. photon-node is fetched with `npm pack` and checked
# against the integrity recorded in pinned Pi's own package-lock.json; its WASM against the R005-A pin.
set -eu
H=/evid/harness
S=/tmp/s
PINNED_PI=b7bb00b936dbe21b8e160b3e89efdec361846699
SRI="sha512-bnly4BKB3KDTFxrUIcgCLbaeVVS8lrAkri1pEzskpmxu9MdfGQTy8b8EgcD83ywD3RPMsIulY8xJH5Awa+t9fA=="
WASM=10468181565c56004c867f3a4af96f89a0ef5a63a72f2b5fb12c1f1992a3615c
die() { echo "FAIL: $*"; exit 1; }

echo "== runtime pins"
[ "$(node -p process.version)" = "v22.15.1" ] || die "node $(node -p process.version)"
[ "$(node -p process.versions.v8)" = "12.4.254.21-node.24" ] || die "v8 $(node -p process.versions.v8)"
node -p '"node " + process.version + ", v8 " + process.versions.v8' | tee /out/runtime.txt

echo "== pinned Pi sources"
apk add -q --no-progress git python3 >/dev/null
git config --global --add safe.directory /pi
[ "$(git -C /pi rev-parse HEAD)" = "$PINNED_PI" ] || die "Pi checkout is not $PINNED_PI"
[ -z "$(git -C /pi status --porcelain -- packages/coding-agent/src)" ] || die "Pi checkout has local changes"
grep -q '"@silvia-odwyer/photon-node": "0.3.4"' /pi/packages/coding-agent/package.json || die "photon-node pin"
grep -A3 '"node_modules/@silvia-odwyer/photon-node"' /pi/package-lock.json | grep -qF "$SRI" || die "lockfile SRI"
mkdir -p $S/authority/pi_utils $S/authority/node_modules/@silvia-odwyer/photon-node
for f in $(awk '{print $2}' $H/pi_utils.sha256 | tr -d '*'); do cp /pi/packages/coding-agent/src/utils/$f $S/authority/pi_utils/; done
(cd $S/authority/pi_utils && sed 's/ \*/  /' $H/pi_utils.sha256 | sha256sum -c -)
cp /pi/packages/coding-agent/src/core/tools/truncate.ts $S/authority/
echo "104e61ea602c7f7894097b2771dad8c68de75c5a10ea6222e615c4ad144451c7  $S/authority/truncate.ts" | sha256sum -c -

echo "== pinned photon-node 0.3.4"
(cd $S && npm pack --silent @silvia-odwyer/photon-node@0.3.4 >/dev/null)
got="sha512-$(node -e 'process.stdout.write(require("crypto").createHash("sha512").update(require("fs").readFileSync(process.argv[1])).digest("base64"))' $S/silvia-odwyer-photon-node-0.3.4.tgz)"
[ "$got" = "$SRI" ] || die "tarball integrity $got"
mkdir -p $S/pkg && tar -xzf $S/silvia-odwyer-photon-node-0.3.4.tgz -C $S/pkg
cp -r $S/pkg/package/. $S/authority/node_modules/@silvia-odwyer/photon-node/
echo "$WASM  $S/pkg/package/photon_rs_bg.wasm" | sha256sum -c -
echo '{"type":"module"}' > $S/authority/package.json
cp $H/run_authority.mjs $H/text_authority.mjs $H/read_text.mjs $S/authority/
# read_text.mjs imports ./truncate.ts; pi_utils holds the image sources.

echo "== corpus (deterministic regeneration)"
python3 $H/make_corpus.py $S/corpus /evid/png_small_rgb.png > /out/corpus.txt
(cd $S/corpus && sha256sum * | sort -k2) > /out/corpus.sha256
cmp /out/corpus.sha256 /evid/corpus.sha256 || die "corpus differs from the recorded SHA256SUMS"
node -e '
const fs = require("fs");
const files = fs.readdirSync(process.argv[1]).filter((f) => f !== "apng_actl_before_idat.png").sort();
fs.writeFileSync(process.argv[1] + "/manifest.json", JSON.stringify(files.map((file) => ({ file }))));' $S/corpus
echo "[]" > $S/core_cases.json

echo "== authority"
cd $S/authority
node --experimental-strip-types --no-warnings run_authority.mjs $S/corpus $S/core_cases.json /out/authority.json
node --experimental-strip-types --no-warnings text_authority.mjs $S/corpus /out/text_authority.json apng_actl_before_idat.png
echo "== done"
