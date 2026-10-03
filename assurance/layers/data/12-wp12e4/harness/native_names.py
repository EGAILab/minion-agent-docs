# WP-12.E4 (WP12E4-CON-R002), Windows: a NATIVE environment block holding names that differ only by a non-ASCII case
# distinction (Q<U+00DF>/Qss, Q<U+0131>/QI). CPython supplies the block to a pinned Node child via CreateProcessW (no
# Node explicit-env arbitration). The child reports what it enumerates and what an ASCII-name process.env lookup reads.
#   python native_names.py <node> <out.json>
import json
import os
import subprocess
import sys

node, out = sys.argv[1], sys.argv[2]
env = {"SystemRoot": os.environ["SYSTEMROOT"], "Qß": "sharp", "Qss": "ss", "Qı": "dotless", "QI": "ascii"}
js = r"""
const u=(s)=>[...Array(s.length).keys()].map(i=>s.charCodeAt(i).toString(16).padStart(4,'0')).join(' ');
const listed=Object.keys(process.env).filter(k=>/^q/i.test(k)).sort().map(k=>[u(k),process.env[k]]);
process.stdout.write(JSON.stringify({runtime:process.version,listed,lookupQSS:process.env.QSS??null,lookupqi:process.env.qi??null,
  lookupSharp:process.env['Qß']??null,lookupDotless:process.env['Qı']??null}));
"""
r = subprocess.run([node, "-e", js], env=env, capture_output=True, text=True, encoding="utf-8")
data = json.loads(r.stdout)
open(out, "w", encoding="utf-8").write(json.dumps(data, indent=1) + "\n")
print(json.dumps(data))
