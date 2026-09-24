#!/usr/bin/env bash
# R005-A Photon differential: reproduce everything from pinned inputs into a throwaway directory.
#
#   bash harness/run_all.sh <scratch-dir> <pi-checkout-at-b7bb00b9>
#
# Needs on PATH: node 22.15.1 (V8 12.4.254.21-node.24), npm, rustc/cargo 1.97.1, and CPython 3.13.5
# given as $PYTHON (default: python3). These versions are checked exactly before anything runs; any
# other runtime fails with RUNTIME_PIN_MISMATCH (exit 3) and no differential step executes.
# Nothing is installed outside <scratch-dir>: the photon-node tarball is fetched
# with `npm pack` and extracted (no npm install), Python packages go into a venv there, and cargo
# uses a CARGO_HOME there. Delete <scratch-dir> afterwards to leave no residue.
set -euo pipefail
S=$(mkdir -p "$1" && cd "$1" && pwd); PI=$(cd "$2" && pwd)
E=$(cd "$(dirname "$0")/.." && pwd); H=$E/harness
PYTHON=${PYTHON:-python3}
PINNED_PI=b7bb00b936dbe21b8e160b3e89efdec361846699
PINNED_TGZ_SRI="sha512-bnly4BKB3KDTFxrUIcgCLbaeVVS8lrAkri1pEzskpmxu9MdfGQTy8b8EgcD83ywD3RPMsIulY8xJH5Awa+t9fA=="
PINNED_WASM=10468181565c56004c867f3a4af96f89a0ef5a63a72f2b5fb12c1f1992a3615c
step() { echo; echo "== $*"; }
# `a && echo ok` does not stop a `set -e` script when `a` fails, so every check fails explicitly.
die() { echo "FAIL: $*"; exit 1; }

# Behavior-affecting runtime tuple (R005A-E001): checked exactly, before anything else runs.
PINNED_NODE="v22.15.1"
PINNED_V8="12.4.254.21-node.24"
PINNED_CPYTHON="3.13.5"
PINNED_RUSTC="rustc 1.97.1 (8bab26f4f 2026-07-14)"
PINNED_CARGO="cargo 1.97.1 (c980f4866 2026-06-30)"
pin() {  # pin <name> <expected> <actual>
  if [ "$2" != "$3" ]; then echo "RUNTIME_PIN_MISMATCH $1: expected '$2', got '$3'"; exit 3; fi
  echo "$1: $3" | tee -a "$S/runtime.txt"
}
step "runtime pins (exact)"
: > "$S/runtime.txt"
pin node "$PINNED_NODE" "$(node -p process.version)"
pin v8 "$PINNED_V8" "$(node -p process.versions.v8)"
pin cpython "$PINNED_CPYTHON" "$("$PYTHON" -c 'import platform; print(platform.python_version())')"
pin rustc "$PINNED_RUSTC" "$(rustc -V)"
pin cargo "$PINNED_CARGO" "$(cargo -V)"

step "pinned Pi source"
[ "$(git -C "$PI" rev-parse HEAD)" = "$PINNED_PI" ] || { echo "Pi checkout is not $PINNED_PI"; exit 1; }
grep -q "\"@silvia-odwyer/photon-node\": \"0.3.4\"" "$PI/packages/coding-agent/package.json"
grep -A3 '"node_modules/@silvia-odwyer/photon-node"' "$PI/package-lock.json" | grep -qF "$PINNED_TGZ_SRI"
mkdir -p "$S/authority/pi_utils"
for f in $(awk '{print $2}' "$H/pi_utils.sha256" | tr -d '*'); do cp "$PI/packages/coding-agent/src/utils/$f" "$S/authority/pi_utils/"; done
(cd "$S/authority/pi_utils" && sha256sum -c "$H/pi_utils.sha256")
echo "Pi $PINNED_PI; lockfile pins photon-node 0.3.4 with $PINNED_TGZ_SRI"

step "pinned photon-node 0.3.4 artifact"
(cd "$S" && npm pack --silent @silvia-odwyer/photon-node@0.3.4 >/dev/null)
got="sha512-$(openssl dgst -sha512 -binary "$S/silvia-odwyer-photon-node-0.3.4.tgz" | base64 -w0)"
[ "$got" = "$PINNED_TGZ_SRI" ] || { echo "tarball integrity $got != $PINNED_TGZ_SRI"; exit 1; }
mkdir -p "$S/pkg" "$S/authority/node_modules/@silvia-odwyer/photon-node"
tar -xzf "$S/silvia-odwyer-photon-node-0.3.4.tgz" -C "$S/pkg"
cp -r "$S/pkg/package/." "$S/authority/node_modules/@silvia-odwyer/photon-node/"
echo "$PINNED_WASM  $S/pkg/package/photon_rs_bg.wasm" | sha256sum -c
cp "$H/authority/package.json" "$H/authority/run_authority.mjs" "$S/authority/"

step "python venv (pinned)"
"$PYTHON" -m venv "$S/venv"
VPY=$S/venv/Scripts/python.exe; [ -x "$VPY" ] || VPY=$S/venv/bin/python
"$VPY" -m pip install -q --disable-pip-version-check -r "$H/requirements.txt"
pin venv-cpython "$PINNED_CPYTHON" "$("$VPY" -c 'import platform; print(platform.python_version())')"
pin venv-packages "$(tr -d '\r' < "$H/requirements.txt" | sort | paste -sd' ')"   "$("$VPY" -m pip freeze --disable-pip-version-check | tr -d '\r' | sort | paste -sd' ')"

step "corpus: committed files + deterministic regeneration, all sha256-verified"
mkdir -p "$S/corpus/files"
cp "$E"/corpus/* "$S/corpus/files/"; rm "$S/corpus/files/SHA256SUMS"
"$VPY" "$H/make_corpus.py" "$S/regen" >/dev/null
(cd "$S/regen" && sha256sum -c --quiet "$E/corpus/SHA256SUMS") || die "generator output differs from SHA256SUMS"
echo "generator reproduces all $(wc -l < "$E/corpus/SHA256SUMS") files bit-identically"
for f in $(awk '{print $2}' "$E/corpus/SHA256SUMS"); do [ -f "$S/corpus/files/$f" ] || cp "$S/regen/$f" "$S/corpus/files/"; done
cmp "$S/regen/manifest.json" "$S/corpus/files/manifest.json"
(cd "$S/corpus/files" && sha256sum -c --quiet "$E/corpus/SHA256SUMS") || die "corpus differs from SHA256SUMS"
echo "corpus verified"

step "harness files"
mkdir -p "$S/py_host" "$S/rs_host/src"
cp "$H"/py_host/*.py "$S/py_host/"; cp "$H/rs_host/Cargo.toml" "$H/rs_host/Cargo.lock" "$S/rs_host/"
cp "$H/rs_host/src/main.rs" "$S/rs_host/src/"
cp "$H/compare.py" "$H/run_controls.sh" "$H/core_cases.json" "$H/wasm_surface.py" "$S/"

step "WASM import/export surface"
"$VPY" "$S/wasm_surface.py" "$S/pkg/package/photon_rs_bg.wasm" > "$S/wasm_surface.txt"; head -3 "$S/wasm_surface.txt"

step "authority: pinned Pi source + photon-node on node $(node -v)"
(cd "$S/authority" && node --experimental-strip-types --no-warnings run_authority.mjs ../corpus/files ../core_cases.json ../authority.json)

step "python host (wasmtime-py) end-to-end vs authority"
(cd "$S" && "$VPY" py_host/run_python.py pkg/package/photon_rs_bg.wasm corpus/files authority.json core_cases.json python.json trace)
(cd "$S" && "$VPY" compare.py authority.json python.json python)

step "rust host (wasmtime crate) replay of every Photon call"
(cd "$S/rs_host" && CARGO_HOME="$S/cargo_home" CARGO_TARGET_DIR="$S/rs_target" cargo build --release --locked -q)
(cd "$S" && rs_target/release/photon-replay pkg/package/photon_rs_bg.wasm trace)

step "negative controls"
(cd "$S" && bash run_controls.sh)

step "fresh results == committed results"
for f in authority.json python.json; do cmp "$S/$f" "$E/results/$f" || die "$f differs from committed"; echo "$f identical to committed"; done
cmp "$S/trace/trace.json" "$E/results/trace.json" || die "trace.json differs from committed"
echo "trace.json identical to committed"
diff <(tr -d '\r' < "$S/runtime.txt") <(tr -d '\r' < "$E/results/runtime.txt") || die "runtime tuple differs from committed"
echo "runtime tuple identical to committed"
echo; echo "R005-A REPRODUCTION: PASS"
