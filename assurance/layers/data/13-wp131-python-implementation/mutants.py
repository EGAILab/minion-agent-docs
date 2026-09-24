"""WP-13.1 negative controls: each mutant injects ONE plausible wrong implementation into the real
modules; the builtin_tool canonical suite must fail for every one. Run inside the code worktree:

    python mutants.py <minion-agent-python dir>
"""

import os
import subprocess
import sys
from pathlib import Path

PY = Path(sys.argv[1])
MUTANTS = {
    "path_trimmed": ("paths.py", "    working = _UNICODE_SPACES.sub(\" \", path)\n",
                     "    working = _UNICODE_SPACES.sub(\" \", path).strip()\n"),
    "at_prefix_all_stripped": ("paths.py", "    if working.startswith(\"@\"):\n        working = working[1:]\n",
                               "    working = working.lstrip(\"@\")\n"),
    "file_url_falls_through": ("paths.py", "        except (ValueError, OSError) as exc:\n            raise BuiltinToolError(",
                               "        except (ValueError, OSError) as exc:\n            return working\n            raise BuiltinToolError("),
    "python_round_in_resize": ("image.py", "            target_height = math_round(", "            target_height = round("),
    "naive_to_fixed": ("image.py", "Multiply coordinates by {to_fixed(scale, 2)}", "Multiply coordinates by {scale:.2f}"),
    "smallest_candidate": ("image.py", "            for encoded, candidate_mime in candidates:\n",
                           "            for encoded, candidate_mime in sorted(candidates, key=lambda c: len(c[0])):\n"),
    "exif_ignored": ("image.py", "    orientation = get_exif_orientation(original)\n", "    orientation = 1\n"),
    "conversion_hint_short_names": ("image.py", 'return (f"[Image converted from {converted_from} to {to}.]",)',
                                    'return (f"[Image converted from {converted_from.split(\'/\')[-1]} to {to.split(\'/\')[-1]}.]",)'),
    "non_vision_note_always": ("read.py", "note = NON_VISION_IMAGE_NOTE if supports is not None and supports() is False else None",
                               "note = NON_VISION_IMAGE_NOTE if supports is None or supports() is False else None"),
    "newline_translation": ("read.py", 'all_lines = data.decode("utf-8", "replace").split("\\n")',
                            'all_lines = data.decode("utf-8", "replace").replace("\\r\\n", "\\n").replace("\\r", "\\n").split("\\n")'),
    "python_slice": ("read.py", "        selected = \"\\n\".join(js_slice(all_lines, start_line, end_line))",
                     "        selected = \"\\n\".join(all_lines[int(start_line):max(int(end_line), int(start_line))])"),
    "details_on_caller_limit": ("read.py", "            f\"offset={number_to_string(next_offset)} to continue.]\"\n        )\n    else:",
                                "            f\"offset={number_to_string(next_offset)} to continue.]\"\n        )\n        details = {\"truncation\": truncation.details()}\n    else:"),
    "resolved_path_in_sed_hint": ("read.py", "sed -n '{display}p' {path} | head", "sed -n '{display}p' {path.lstrip('./')} | head"),
    "cap_after_probe": ("ls.py", "        if len(results) >= effective_limit:\n            entry_limit_reached = True\n            break\n        joined",
                        "        joined"),
    "limit_rounded": ("ls.py", "            f\"{number_to_string(effective_limit)} entries limit reached. \"",
                      "            f\"{number_to_string(round(effective_limit))} entries limit reached. \""),
    "failed_entry_listed": ("ls.py", "        if isinstance(entry, Err):\n            continue\n", "        if isinstance(entry, Err):\n            results.append(name)\n            continue\n"),
    "not_supported_as_not_found": ("ls.py", "        if probe.error.code == FsErrorCode.NOT_SUPPORTED:", "        if False:"),
    "python_lower_keys": ("collation.py", "        return str(self._unicode_string(name).toLower(self._root))", "        return name.lower()"),
    "normalization_off": ("collation.py", "attribute.NORMALIZATION_MODE, value.ON", "attribute.NORMALIZATION_MODE, value.OFF"),
    "codepoint_sort": ("collation.py", "        keyed.sort(key=functools.cmp_to_key(by_key))", "        keyed.sort(key=lambda kv: kv[0])"),
    "reverse_on_ties": ("collation.py", "            return self.compare(a[0], b[0])", "            return self.compare(a[0], b[0]) or (1 if a[1] < b[1] else -1 if a[1] > b[1] else 0)"),
}
MUTANTS.update({
    "access_via_exec_007_probe": ("read.py", "        info = await self._fs.file_info(working)\n        if isinstance(info, Err):",
                                  "        info = await self._fs.probe_dir_entry(working)\n        if isinstance(info, Err):"),
    "every_read_failure_at_read_site": ("read.py", '    return "Cannot access"\n', '    return "Cannot read"\n'),
})
PYTHON_WITNESS_MUTANTS = {
    # timing is not expressible in canonical YAML; these run the Python witness tests instead
    "cancel_in_flight": ("_signal.py", "    _ABANDONED.add(task)\n", "    task.cancel()\n    _ABANDONED.add(task)\n"),
    "signal_passed_to_fs": ("read.py", "        info = await self._fs.file_info(working)\n",
                            "        info = await self._fs.file_info(working, signal)\n"),
}
BUILTIN = PY / "src" / "minion_agent" / "tools" / "builtin"
env = dict(os.environ)
results = {}
ALL = [(n, v, "tests/conformance/test_builtin_tool_conformance.py") for n, v in MUTANTS.items()]
ALL += [(n, v, "tests/tools/builtin/test_tools.py tests/tools/builtin/test_helpers.py") for n, v in PYTHON_WITNESS_MUTANTS.items()]
for name, (fname, old, new), target in ALL:
    path = BUILTIN / fname
    original = path.read_text(encoding="utf-8")
    fixed_old = old if old in original else old.replace("value.NORMALIZATION_MODE", "attribute.NORMALIZATION_MODE")
    assert original.count(fixed_old) == 1, (name, "anchor not found exactly once")
    path.write_text(original.replace(fixed_old, new), encoding="utf-8")
    try:
        run = subprocess.run(
            [str(PY / ".venv/Scripts/python.exe"), "-m", "pytest", *target.split(),
             "-q", "-p", "no:cacheprovider", "--no-cov", "--color=no"],
            cwd=PY, capture_output=True, text=True, env=env)
        failed = [l.split("::", 1)[1].split(" ")[0] for l in run.stdout.splitlines() if l.startswith("FAILED")]
        results[name] = failed
        print(f"MUTANT {name}: {'DETECTED' if failed else 'NOT DETECTED'} ({len(failed)} scenario(s)){': ' + ', '.join(failed[:3]) if failed else ''}", flush=True)
    finally:
        path.write_text(original, encoding="utf-8")
missed = [n for n, f in results.items() if not f]
print(f"\n{len(results) - len(missed)}/{len(results)} mutants detected" + (f"; MISSED: {missed}" if missed else ""))
sys.exit(1 if missed else 0)
