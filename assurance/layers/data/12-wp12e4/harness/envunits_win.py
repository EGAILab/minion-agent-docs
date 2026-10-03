# WP-12.E4 audit 2 (WP12E4-AUD-R002), Windows: pinned Node's view of a native UTF-16 environment holding lone
# surrogates (supplied here as the explicit UTF-16 environment block CPython passes to CreateProcessW for the
# Node child -- not through _wputenv), and what a grandchild receives when Node passes an explicit env.
#   python envunits_win.py <node> <out.json>
import json, os, subprocess, sys
node, out = sys.argv[1], sys.argv[2]
env = dict(os.environ)
env["W_LONE"] = "a\ud800b"
env["W_PAIR"] = "a\U0001F600b"
env["W_N\udc80"] = "name-lone"
js = r"""
const {spawnSync}=require('child_process');
const u=(s)=>[...Array(s.length).keys()].map(i=>s.charCodeAt(i).toString(16).padStart(4,'0'));
const ks=Object.keys(process.env).filter(k=>/^w_/i.test(k)).sort();
const view={}; for(const k of ks) view[u(k).join(' ')]=u(process.env[k]);
const grand=spawnSync(process.execPath,['-e',"const u=(s)=>[...Array(s.length).keys()].map(i=>s.charCodeAt(i).toString(16).padStart(4,'0'));const o={};for(const k of Object.keys(process.env).filter(k=>/^w_/i.test(k)).sort())o[u(k).join(' ')]=u(process.env[k]);process.stdout.write(JSON.stringify(o))"],{env:{...process.env},encoding:'utf8'}).stdout;
process.stdout.write(JSON.stringify({runtime:process.version,nodeView:view,grandchildViaExplicitEnv:JSON.parse(grand)}));
"""
r = subprocess.run([node, "-e", js], env=env, capture_output=True, text=True, encoding="utf-8")
data = json.loads(r.stdout)
open(out, "w").write(json.dumps(data, indent=1) + "\n")
print(json.dumps(data))
