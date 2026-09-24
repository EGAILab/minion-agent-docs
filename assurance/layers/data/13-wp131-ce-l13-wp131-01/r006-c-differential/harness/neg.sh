#!/usr/bin/env bash
set -uo pipefail
exec > >(tee /work/out/negative_control.log) 2>&1
PREFIX=/opt/icu-78.3
apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends python3 pkg-config clang libclang-dev >/dev/null 2>&1
DEBIAN_FRONTEND=noninteractive apt-get purge -y -qq libicu-dev >/dev/null 2>&1 || true
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig" LD_LIBRARY_PATH="$PREFIX/lib"
cd /work/rust_neg && CARGO_TARGET_DIR=/tmp/t cargo build -q --release 2>/dev/null
echo "== negative control: Rust engine with NUMERIC_COLLATION=ON vs unmodified PyICU output"
/tmp/t/release/r006c_rust_engine /work/corpus.json > /tmp/neg.json
python3 /work/compare.py /work/corpus.json /work/out/python.json /tmp/neg.json; echo "compare exit code: $?"
echo "== negative control 2: single flipped matrix cell (synthetic)"
python3 - <<'PY'
import json; r = json.load(open("/work/out/rust.json")); r["raw"]["matrix"][14][15] *= -1 or 1
if r["raw"]["matrix"][14][15] == 0: r["raw"]["matrix"][14][15] = 1
json.dump(r, open("/tmp/flip.json", "w"))
PY
python3 /work/compare.py /work/corpus.json /work/out/python.json /tmp/flip.json | grep -E "FAIL|VERDICT"; echo "compare exit code: ${PIPESTATUS[0]}"
