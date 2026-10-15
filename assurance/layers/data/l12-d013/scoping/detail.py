"""Print detail rows from a rooted-probe-2 output. Read-only."""
import json
import sys

d = json.load(open(sys.argv[1], encoding="utf-8"))
inputs = d["inputs"]


def show(form, provider, indexes):
    r = [x for x in d["report"] if x["cwd_form"] == form and x["entries"] == "absent" and x["provider"] == provider][0]
    print("==", form, provider, "node cwd:", r["node"]["cwd_text"])
    for i in indexes:
        print("  ", repr(inputs[i]).ljust(22), repr(r["node"]["rows"][i]["text"]).ljust(42), "py",
              repr(r["python"]["rows"][i].get("text", r["python"]["rows"][i].get("error"))))


show("plain", "E:\\y", range(19, 25))
show("plain", "E:\\y", [0, 11])
show("unc_admin", "C:\\x", [0, 1, 2, 8, 11, 19, 20, 24])
show("extended", "C:\\x", [0, 19, 20])
