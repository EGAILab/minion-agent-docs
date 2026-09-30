# Remediation-1 review probes

Use a fresh Python 3.13 environment installed against code #87 at `28a5938da93dd4b4c7205d3dffcdc8bc82227684`, with its test dependencies and pinned ICU build/environment. Confirm `minion_agent.__file__` before testing. Set `PYTHONPATH` to the candidate `minion-agent-python` directory and this probe directory (platform path-list separator). Run commands from candidate `minion-agent-python`.

```text
python <probe-directory>/negative_zero.py
python -m pytest tests/tools/builtin/test_wp132_mutation_tools.py -k "abort_listener or json_numbers or huge_json_integer or encodes_surrogates" -p revert_plugin -q -o addopts= --tb=short
```

The latter is an intentionally RED in-memory reversion run: 7 failed / 6 passed / 18 deselected. Run without the plugin to restore the untouched actual candidate; do not use the revert plugin during normal certification.

For Pi, mount the pinned Pi checkout at `/pi` and `negative_zero.mjs` at `/probe.mjs` in `node:22.15.1-alpine` and run `node /probe.mjs`. It extracts the actual preparation function and strips TypeScript-only annotations; all three spellings are negative zero in Pi.

Observed Python:

```text
-0 int 0 sign 1.0
-0.0 float -0.0 sign -1.0
-0e0 float -0.0 sign -1.0
real Layer-06 hook sign 1.0
pipeline is_error False file b
```

Observed Pi:

```text
-0 negativeZero true reciprocal -Infinity
-0.0 negativeZero true reciprocal -Infinity
-0e0 negativeZero true reciprocal -Infinity
```
