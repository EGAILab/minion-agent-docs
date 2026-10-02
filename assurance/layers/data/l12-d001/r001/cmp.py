import json,sys
a={r["id"]:r["observed"][-1] for r in json.load(open(sys.argv[1]))["results"]}
b={r["id"]:r["observed"][-1] for r in json.load(open(sys.argv[2]))["results"]}
def s(p): return None if p is None else "/".join("".join(chr(c) if c<0xD800 or c>0xDFFF else f"<{c:X}>" for c in comp).replace("�","<FFFD>") for comp in p)
n=0
for k in a:
    x,y=a[k],b[k]
    kx=(x.get("error"),s(x.get("path"))) if "error" in x else "OK"; ky=(y.get("error"),s(y.get("path"))) if "error" in y else "OK"
    if kx!=ky: n+=1; print(f"{k:50} pi={kx}  py={ky}")
print(n,"differ of",len(a))
