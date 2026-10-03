#!/bin/sh
BAD="$(printf 'a\377b')" python3 -c '
import os, subprocess, json
v = os.environ["BAD"]
child = subprocess.run(["sh","-c","printf %s \"$BAD\" | od -An -tx1"], env=dict(os.environ), capture_output=True, text=True).stdout.strip()
print(json.dumps({"python": os.sys.version.split()[0], "parentRepr": ascii(v), "childBytesDictEnviron": child}))'
