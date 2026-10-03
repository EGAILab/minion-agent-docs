import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
print(d["platform"], d["shell"])
def t(v):
    if isinstance(v, dict): return f"<len {v['length']}> ...{''.join(map(chr, v['tail']))[-160:]!r}"
    return repr("".join(map(chr, v)))[:220]
for r in d["results"]:
    det = r["details"]["truncation"] if r["details"] else None
    tr = f" trunc={det['truncatedBy']} lines={det['totalLines']} out={det['outputLines']} partial={det['lastLinePartial']}" if det else ""
    fo = f" full={r['full_output']['size']}B" if r.get("full_output") else ""
    print(f"{r['id']:42} err={r['is_error']!s:5} upd={r['update_count']}{tr}{fo}\n    {t(r['text'])}")
    if "updates" in r: print("    updates:", [("".join(map(chr,u['text'])) if u['text'] is not None else None) for u in r["updates"]])
