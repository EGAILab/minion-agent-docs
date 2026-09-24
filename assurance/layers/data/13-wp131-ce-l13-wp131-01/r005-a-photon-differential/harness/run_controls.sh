#!/usr/bin/env bash
# R005-A negative controls: every control must be DETECTED (comparison exits non-zero / host refuses).
set -u
cd "$(dirname "$0")"
PY=venv/Scripts/python.exe; [ -x "$PY" ] || PY=venv/bin/python
RS=rs_target/release/photon-replay; WASM=pkg/package/photon_rs_bg.wasm
mkdir -p controls_out; fail=0
detected() { echo "CONTROL $1: DETECTED — $2"; }
missed() { echo "CONTROL $1: NOT DETECTED"; fail=1; }
for c in $($PY -c "import sys; sys.path.insert(0,'py_host'); import controls; print(' '.join(controls.CONTROLS))"); do
  rm -f controls_out/$c.json
  if ! R005A_CONTROL=$c $PY py_host/run_python.py $WASM corpus/files authority.json core_cases.json controls_out/$c.json >/dev/null 2>controls_out/$c.err; then
    echo "CONTROL $c: HARNESS ERROR (run crashed; not counted as detection)"; fail=1; continue; fi
  if out=$($PY compare.py authority.json controls_out/$c.json "$c"); then missed "$c"
  else detected "$c" "$(echo "$out" | tail -1 | sed 's/^VERDICT [^:]*: //'); first: $(echo "$out" | grep -m1 MISMATCH | cut -c1-150)"; fi
done
# Integrity: one flipped byte in the WASM must be refused by both hosts before execution.
$PY -c "import sys; b=bytearray(open('$WASM','rb').read()); b[len(b)//2]^=1; open('controls_out/mutated.wasm','wb').write(b)"
if $PY py_host/run_python.py controls_out/mutated.wasm corpus/files authority.json core_cases.json controls_out/x.json >/dev/null 2>controls_out/py_integrity.err; then missed python_wasm_integrity
else detected python_wasm_integrity "$(tail -1 controls_out/py_integrity.err | cut -c1-120)"; fi
if $RS controls_out/mutated.wasm trace >/dev/null 2>controls_out/rs_integrity.err; then missed rust_wasm_integrity
else detected rust_wasm_integrity "$(tail -1 controls_out/rs_integrity.err | cut -c1-120)"; fi
# Rust replay discrimination: the same recorded expectations, but every resize issued with Triangle.
rm -rf controls_out/trace_triangle && mkdir -p controls_out/trace_triangle && cp -r trace/blobs controls_out/trace_triangle/
$PY -c "
import json; t=json.load(open('trace/trace.json'))
for e in t:
    if e['op']=='resize': e['args'][3]=2
json.dump(t, open('controls_out/trace_triangle/trace.json','w'))"
if out=$($RS $WASM controls_out/trace_triangle); then missed rust_filter_triangle
else detected rust_filter_triangle "$(echo "$out" | tail -1)"; fi
exit $fail
