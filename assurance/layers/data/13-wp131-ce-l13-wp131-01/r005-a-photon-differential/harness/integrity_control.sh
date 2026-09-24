#!/usr/bin/env bash
# Harness self-check: run_all.sh must FAIL when committed evidence is tampered with. Each control runs
# on a scratch COPY of this evidence directory; the committed files are never modified.
#
#   PYTHON=<CPython 3.13.5> bash harness/integrity_control.sh <scratch-root> <pi-checkout-at-b7bb00b9>
set -uo pipefail
R=$(mkdir -p "$1" && cd "$1" && pwd); PI=$2
E=$(cd "$(dirname "$0")/.." && pwd)
fail=0

tampered_run() {  # tampered_run <label> <relative-file> <expected FAIL text>
  local label=$1 rel=$2 expect=$3 copy=$R/$1/evidence
  rm -rf "$R/$label"; mkdir -p "$copy"; cp -r "$E/." "$copy/"
  "${PYTHON:-python3}" -c "import sys; p=sys.argv[1]; b=bytearray(open(p,'rb').read()); b[len(b)//2]^=1; open(p,'wb').write(b)" "$copy/$rel"
  out=$(bash "$copy/harness/run_all.sh" "$R/$label/scratch" "$PI" 2>&1); code=$?
  if [ $code -ne 0 ] && grep -qF "FAIL: $expect" <<<"$out" && ! grep -q "R005-A REPRODUCTION: PASS" <<<"$out"; then
    echo "CONTROL $label: FAILED THE RUN as required — FAIL: $expect"
  else
    echo "CONTROL $label: NOT CAUGHT (exit $code)"; fail=1
  fi
}

tampered_run tampered_corpus_file corpus/png_small_rgb.png "corpus differs from SHA256SUMS"
tampered_run tampered_committed_result results/python.json "python.json differs from committed"
exit $fail
