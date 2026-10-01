# L0506-D003 characterization: tool-result runtime value domain

Record: `assurance/layers/l0506-d003-characterization.md`. Coordination: `minion-agent#112`.

- `harness/make_cases.py` writes `cases.json` (145 cases, tagged value form; sha256 in `out/cases.sha256`).
- `harness/run.sh` is the pinned-Pi authority (Node v22.15.1, Pi `b7bb00b9`, typebox 1.3.7, diff 8.0.4), and writes `out/result.json`. It runs in two modes:
  - **Container:** `docker run --rm -v <pi>:/pi:ro -v <this dir>:/evid:ro -v <out>:/out node:22.15.1-alpine sh /evid/harness/run.sh`
  - **Host:** `PI_DIR=<pi> OUT_DIR=<out> [TYPEBOX_TGZ=… DIFF_TGZ=…] [PYTHON=…] sh harness/run.sh`. With the `*_TGZ` variables set, it needs no network (`process/authority-dependencies.md`).
- `harness/py_probe.py` exercises certified Python's real seams: `PYTHONPATH=<minion-agent-python>/src python py_probe.py cases.json out/py.json`, pinned ICU environment required.
- `harness/compare.py out/result.json out/py.json` compares Python with Pi, boundary by boundary.
