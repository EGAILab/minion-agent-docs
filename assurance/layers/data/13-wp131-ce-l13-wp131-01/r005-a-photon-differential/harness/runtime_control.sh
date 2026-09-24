#!/usr/bin/env bash
# R005A-E001 negative controls: run_all.sh must refuse a wrong runtime BEFORE any differential step.
#
#   bash harness/runtime_control.sh <scratch-root> <pi-checkout-at-b7bb00b9> <wrong-cpython>
#
# <wrong-cpython> is a real interpreter of another version (the review witness was CPython 3.12.8).
# Node/rustc/cargo mismatches are simulated with PATH shims that report a different version.
set -uo pipefail
R=$(mkdir -p "$1" && cd "$1" && pwd); PI=$2; WRONG_PY=$3
H=$(cd "$(dirname "$0")" && pwd)
GOOD_PY=${PYTHON:-python3}
fail=0

expect_refusal() {  # expect_refusal <label> <pin-name> <scratch> <env...>
  local label=$1 pin=$2 s=$3; shift 3
  out=$(env "$@" bash "$H/run_all.sh" "$s" "$PI" 2>&1); code=$?
  produced=$(cd "$s" && ls -d authority.json python.json trace pkg venv 2>/dev/null | paste -sd' ')
  if [ $code -eq 3 ] && grep -q "^RUNTIME_PIN_MISMATCH $pin:" <<<"$out" && [ -z "$produced" ]; then
    echo "CONTROL $label: REFUSED before differential — $(grep -m1 '^RUNTIME_PIN_MISMATCH' <<<"$out")"
  else
    echo "CONTROL $label: NOT REFUSED (exit $code; produced: ${produced:-nothing})"; fail=1
  fi
}

shim() {  # shim <dir> <tool> <script-body>
  mkdir -p "$1"; printf '#!/usr/bin/env bash\n%s\n' "$3" > "$1/$2"; chmod +x "$1/$2"
}

expect_refusal wrong_cpython cpython "$R/wrong_cpython" PYTHON="$WRONG_PY"

REAL_NODE=$(command -v node)
shim "$R/shim_node" node "case \"\$*\" in *process.version) echo v22.15.0;; *) exec \"$REAL_NODE\" \"\$@\";; esac"
expect_refusal wrong_node node "$R/wrong_node" PYTHON="$GOOD_PY" PATH="$R/shim_node:$PATH"

shim "$R/shim_v8" node "case \"\$*\" in *process.versions.v8) echo 12.4.254.20-node.24;; *) exec \"$REAL_NODE\" \"\$@\";; esac"
expect_refusal wrong_v8 v8 "$R/wrong_v8" PYTHON="$GOOD_PY" PATH="$R/shim_v8:$PATH"

shim "$R/shim_rustc" rustc 'echo "rustc 1.96.0 (00000000 2026-05-28)"'
expect_refusal wrong_rustc rustc "$R/wrong_rustc" PYTHON="$GOOD_PY" PATH="$R/shim_rustc:$PATH"

shim "$R/shim_cargo" cargo 'echo "cargo 1.96.0 (00000000 2026-05-20)"'
expect_refusal wrong_cargo cargo "$R/wrong_cargo" PYTHON="$GOOD_PY" PATH="$R/shim_cargo:$PATH"

exit $fail
