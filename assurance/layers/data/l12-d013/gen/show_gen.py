"""Show the 19 L12-D013 cases of a path-resolution corpus and validate the whole document. Read-only."""
import json
import sys

from jsonschema import Draft202012Validator

corpus, schema = sys.argv[1:3]
doc = json.load(open(corpus, encoding="utf-8"))
errors = list(Draft202012Validator(json.load(open(schema, encoding="utf-8"))).iter_errors(doc))
print("schema errors:", len(errors))
for e in errors[:5]:
    print("  ", e.message[:200])


def text(v):
    if "utf16" in v:
        return b"".join(u.to_bytes(2, "little") for u in v["utf16"]).decode("utf-16-le", "surrogatepass")
    return "".join(text(p) if "utf16" in p else "<%s>" % ("DRIVE" if p.get("cwd_drive") == "upper"
                                                          else "drive" if "cwd_drive" in p else "TAIL")
                   for p in v["parts"])


cases = doc["path_resolution"]["cases"]
print("cases:", len(cases))
for c in cases:
    if "rooted" in c["id"]:
        form = (c["host"] or {}).get("cwd_form", "-")
        print(c["id"].ljust(30), form.ljust(9), repr(text(c["input"])).ljust(22), "->", repr(text(c["expect"])),
              c["preconditions"])
