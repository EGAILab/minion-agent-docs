import json, os, subprocess, sys
CHILD = r'''
import ctypes, json
k = ctypes.windll.kernel32
k.GetEnvironmentStringsW.restype = ctypes.c_void_p
p = k.GetEnvironmentStringsW()
out, i = [], 0
while True:
    s = ctypes.wstring_at(p + i * 2)
    if not s: break
    out.append(s); i += len(s) + 1
print(json.dumps([e for e in out if e.lower().startswith(("xk=", "programfiles"))]))
'''
def run(pairs):
    env = {"SystemRoot": os.environ["SYSTEMROOT"]}
    for k, v in pairs: env[k] = v
    r = subprocess.run([sys.executable, "-c", CHILD], env=env, capture_output=True, text=True)
    return json.loads(r.stdout) if r.stdout else r.stderr[-200:]
print(json.dumps({
 "pyEnvironKeys": [k for k in os.environ if "PROGRAMFILES" in k.upper()],
 "upperFirst": run([("XK","upper"),("xk","lower")]),
 "lowerFirst": run([("xk","lower"),("XK","upper")]),
 "lowerThenxK": run([("xk","l"),("xK","m")]),
 "pfExact": run([("ProgramFiles","C:/PF")]),
}))
