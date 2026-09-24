#!/usr/bin/env bash
set -euo pipefail
exec > >(tee /work/out/norm_probe.log) 2>&1
PREFIX=/opt/icu-78.3
apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends python3 python3-dev python3-venv pkg-config >/dev/null 2>&1
DEBIAN_FRONTEND=noninteractive apt-get purge -y -qq libicu-dev >/dev/null 2>&1 || true
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig" LD_LIBRARY_PATH="$PREFIX/lib" PATH="$PREFIX/bin:$PATH"
python3 -m venv /venv && /venv/bin/pip install -q --no-cache-dir --no-binary pyicu "pyicu==2.16.2" 2>&1 | grep -v DEPRECATION || true
ldd /venv/lib/python3*/site-packages/icu/_icu_*.so | awk '/icu/{print "  "$1" => "$3}'
/venv/bin/python - <<'PY'
import icu, json
print("PyICU", icu.VERSION, "ICU", icu.ICU_VERSION, "Unicode", icu.UNICODE_VERSION)
A, V = icu.UCollAttribute, icu.UCollAttributeValue
def coll(norm):
    c = icu.Collator.createInstance(icu.Locale("en-001"))
    c.setAttribute(A.STRENGTH, V.TERTIARY); c.setAttribute(A.NUMERIC_COLLATION, V.OFF); c.setAttribute(A.CASE_FIRST, V.OFF)
    c.setAttribute(A.NORMALIZATION_MODE, V.ON if norm else V.OFF)
    return c
pairs = [("ậ", "ậ"), ("é", "é"), ("ḍ̇", "ḍ̇"), ("q̣̇", "q̣̇")]
for norm in (False, True):
    c = coll(norm)
    print("NORMALIZATION", "ON " if norm else "OFF", [(ascii(a), ascii(b), c.compare(a, b)) for a, b in pairs])
root = icu.Locale.getRoot()
for s in ["ΟΔΟΣ", "İ", "ẞ", "Straße", "APPLE"]:
    low = str(icu.UnicodeString(s).toLower(root))
    print("ICU root toLower", ascii(s), "->", [hex(ord(ch)) for ch in low])
PY
