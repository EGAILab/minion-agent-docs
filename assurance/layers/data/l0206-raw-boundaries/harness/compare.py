import json
import sys

pi = {r["id"]: r for r in json.load(open(sys.argv[1], encoding="utf-8"))["results"]}
py = {r["id"]: r for r in json.load(open(sys.argv[2], encoding="utf-8"))["results"]}


def norm(o):
    """Python tokens carry a type suffix; compare by Pi's Number::toString value."""
    if "n" in o:
        t = o["n"]
        if "(" in t:
            value, kind = t[:-1].split("(")
            num = float(value) if kind == "float" else int(value)
            if kind == "int" and abs(num) > 2**53:
                return {"n": t}  # an exact big int: no Pi equivalent
            f = float(num)
            if f == int(f) and abs(f) < 1e21:
                return {"n": str(int(f))}
            return {"n": repr(f).replace("e+", "e+")}
        return o
    if "a" in o:
        return {"a": [norm(x) for x in o["a"]]}
    if "o" in o:
        return {"o": [[k, norm(v)] for k, v in o["o"]]}
    return o


def keys(o):
    return [k for k, _ in o["o"]] if "o" in o else None


for cid, p in pi.items():
    q = py[cid]
    ref = norm(q["reference_json_loads"]) if isinstance(q["reference_json_loads"], dict) else q["reference_json_loads"]
    pipe = q["pipeline"]
    rows = []
    same_keys = keys(ref) == keys(p["decode"]) if isinstance(ref, dict) else False
    perm = isinstance(ref, dict) and sorted(map(str, keys(ref) or [])) == sorted(map(str, keys(p["decode"]) or []))
    label = "SAME" if ref == p["decode"] else ("KEY-ORDER" if perm and not same_keys else f"VALUE {ref} vs pi {p['decode']}")
    rows.append("decode(json.loads ref)=" + label)
    if q.get("session_append") != "ok":
        rows.append("session=" + q["session_append"])
    else:
        rows.append("replay=" + ("SAME-as-live" if norm(q["replay"]) == ref else f"DIFF {q['replay']}"))
        rows.append("pi_replay=" + ("=live" if p["replay"] == p["decode"] else "PROJECTED"))
    for k in ("execution_start", "hook", "execute"):
        if k in pipe:
            rows.append(k + "=" + ("ok" if norm(pipe[k]) == ref else "DIFF"))
        else:
            rows.append(k + "=MISSING")
    if pipe["is_error"]:
        rows.append("ERROR " + pipe["text"][:80])
    print(f"{cid:32} " + "  ".join(rows))
