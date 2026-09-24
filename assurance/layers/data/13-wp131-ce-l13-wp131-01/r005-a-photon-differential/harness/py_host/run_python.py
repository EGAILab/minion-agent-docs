"""Run the Python Photon host over the same corpus/call order as the authority run."""

import base64
import hashlib
import json
import os
import sys
from pathlib import Path

import pi_pipeline as pp
from photon_host import PhotonHost, Tracer

wasm_path, corpus_dir, authority_path, cases_path, out_path = sys.argv[1:6]
trace_dir = sys.argv[6] if len(sys.argv) > 6 else None
if trace_dir:
    PhotonHost.tracer = Tracer(f"{trace_dir}/blobs")
if os.environ.get("R005A_CONTROL"):
    import controls
    controls.apply(os.environ["R005A_CONTROL"])
compiled = PhotonHost.compile(Path(wasm_path).read_bytes())
main_host = PhotonHost(compiled)
fresh_hosts = []


def fresh():
    h = PhotonHost(compiled)
    fresh_hosts.append(h)
    return h


def summarize(b64s):
    d = base64.b64decode(b64s)
    return {"data_sha256": hashlib.sha256(d).hexdigest(), "data_bytes": len(d), "data_base64_len": len(b64s)}


authority = json.loads(Path(authority_path).read_text())
read_level = []
for a in authority["read_level"]:
    data = (Path(corpus_dir) / a["file"]).read_bytes()
    rec = {"file": a["file"], "input_sha256": hashlib.sha256(data).hexdigest(), "sniffed_mime": a["sniffed_mime"]}
    if a["sniffed_mime"]:
        r = pp.process_image(main_host, fresh, data, a["sniffed_mime"])
        rec.update({"ok": True, "mime": r["mimeType"], "hints": r["hints"], **summarize(r["data"])} if r["ok"]
                   else {"ok": False, "message": r["message"]})
    read_level.append(rec)

core_level = []
for c in json.loads(Path(cases_path).read_text()):
    data = (Path(corpus_dir) / c["file"]).read_bytes()
    r = pp.resize_image_in_process(main_host, data, c["mime"], c["options"])
    core_level.append({"id": c["id"], "file": c["file"], "options": c["options"], "result": None if r is None else {
        "mime": r["mimeType"], "originalWidth": r["originalWidth"], "originalHeight": r["originalHeight"],
        "width": r["width"], "height": r["height"], "wasResized": r["wasResized"], **summarize(r["data"])}})

unexpected = sorted({n for h in [main_host, *fresh_hosts] for n in h.unexpected_imports})
Path(out_path).write_text(json.dumps({"engine": "python+wasmtime+photon_rs_bg.wasm", "unexpected_imports": unexpected,
                                      "read_level": read_level, "core_level": core_level}, indent=1), newline="\n")
print(f"python: {len(read_level)} read-level, {len(core_level)} core-level, unexpected imports: {unexpected}")
if trace_dir:
    Path(f"{trace_dir}/trace.json").write_text(json.dumps(PhotonHost.tracer.events), newline="\n")
    ops = [e["op"] for e in PhotonHost.tracer.events]
    print(f"trace: {len(ops)} events, {sum(1 for e in PhotonHost.tracer.events if 'trap' in e)} traps, "
          f"{ops.count('instantiate')} instances, ops={sorted(set(ops))}")
