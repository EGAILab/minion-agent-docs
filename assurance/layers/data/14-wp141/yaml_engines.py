"""Compare candidate Python YAML engines with the pinned yaml@2.9.0 oracle (yaml-oracle.json) on
Pi's observable projection: accept/reject, then string-typed name/description and `=== true`
disable-model-invocation. Usage: python yaml_engines.py yaml-oracle.json"""

from __future__ import annotations

import io
import json
import sys


def project(fm):
    if not isinstance(fm, dict):
        fm = {}
    name, description = fm.get("name"), fm.get("description")
    return {
        "name": name if isinstance(name, str) else None,
        "description": description if isinstance(description, str) else None,
        "disable": fm.get("disable-model-invocation") is True,
    }


def pyyaml_safe(src):
    import yaml

    return yaml.safe_load(src)


def ruamel_safe_12(src):
    from ruamel.yaml import YAML

    y = YAML(typ="safe", pure=True)
    y.version = (1, 2)
    y.allow_duplicate_keys = False
    return y.load(io.StringIO(src))


def ruamel_rt(src):
    from ruamel.yaml import YAML

    y = YAML(typ="rt")
    y.allow_duplicate_keys = False
    return y.load(io.StringIO(src))


ENGINES = {"pyyaml-safe (1.1)": pyyaml_safe, "ruamel-safe-pure-1.2": ruamel_safe_12, "ruamel-rt": ruamel_rt}


def main() -> None:
    oracle = json.load(open(sys.argv[1], encoding="utf-8"))
    report = {}
    for label, engine in ENGINES.items():
        mismatches = []
        for case in oracle:
            try:
                got = {"ok": True, "observed": project(engine(case["src"]))}
            except Exception as e:  # noqa: BLE001 - classification only
                got = {"ok": False, "error": type(e).__name__}
            want_ok = case["ok"]
            if got["ok"] != want_ok or (want_ok and got["observed"] != case["observed"]):
                mismatches.append({"src": case["src"], "pi": case.get("observed", case.get("message")), "engine": got.get("observed", got.get("error"))})
        report[label] = {"agree": len(oracle) - len(mismatches), "total": len(oracle), "mismatches": mismatches}
        print(f"{label}: {len(oracle) - len(mismatches)}/{len(oracle)} agree")
        for m in mismatches:
            print(f"    {json.dumps(m['src'])[:60]:<62} pi={json.dumps(m['pi'], ensure_ascii=False)[:70]}  engine={json.dumps(m['engine'], ensure_ascii=False)[:70]}")
    json.dump(report, open("yaml-engines-report.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)


main()
