"""Derive the contained abort-trigger probe from the WP-13.3 pinned-Pi bash probe (scratch).

Changes, each asserted to apply exactly once:
- sandbox: fs-guard makeSandbox inside the project root instead of mkdtemp(tmpdir()) (Owner containment rule);
- cases: only the abort cases -- the original 400 ms timer and the new output-event trigger (`abortOnOutput`);
- trigger: onUpdate aborts the signal the first time an update's text contains the marker;
- repeat: each case runs `repeat` times so timing sensitivity is visible.
"""
import subprocess
from pathlib import Path

ROOT = Path("E:/AI/Projects/OpenMinds/Minions/Minion-Agent")
src = subprocess.run(
    ["git", "-C", str(ROOT / "minion-agent-docs"), "show", "origin/master:assurance/layers/data/13-wp133/harness/bash_probe.mjs"],
    capture_output=True, text=True, encoding="utf-8", check=True).stdout


def once(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, old
    return text.replace(old, new)


src = once(src, "//   node --experimental-strip-types bash_probe.mjs <pi checkout> <out.json>",
           "// Derived for TEST-BASH-ABORT-TIMING (minion-agent#197): only the abort cases, with the output-event trigger\n"
           "// `abortOnOutput` beside the original timer; sandboxes inside the project root through the reviewed fs-guard.\n"
           "//   node --experimental-strip-types abort_trigger_probe.mjs <pi checkout> <scratch dir in the project> <out.json> [repeat]")
src = once(src, 'import { tmpdir } from "node:os";\n',
           'import { makeSandbox, cleanupSandbox } from "../l12-d007/fs-guard/fs-guard.mjs";\n')
src = once(src, "const [piDir, outPath] = process.argv.slice(2);",
           "const [piDir, scratch, outPath, repeatArg = \"5\"] = process.argv.slice(2);\nconst REPEAT = Number(repeatArg);")
start = src.index("const CASES = [")
end = src.index("];\n", start) + 3
src = src[:start] + (
    "const CASES = [\n"
    "  [\"abort/during-timer-400ms\", \"printf 'before\\\\n'; sleep 5\", { abortAfterMs: 400 }],\n"
    "  [\"abort/during-on-output\", \"printf 'before\\\\n'; sleep 5\", { abortOnOutput: \"before\" }],\n"
    "];\n") + src[end:]
src = once(src, "for (const [id, command, opt = {}] of CASES) {\n  const base = realpathSync(mkdtempSync(join(tmpdir(), \"wp133-\")));",
           "for (const [id, command, opt = {}] of CASES) for (let run = 1; run <= REPEAT; run++) {\n"
           "  const base = realpathSync(makeSandbox(join(scratch, `wp133-abort-${process.pid}-${id.replace('/', '-')}-${run}`)));")
src = once(src, "  const onUpdate = (u) => updates.push({ text: u.content[0]?.text ?? null, hasDetails: u.details !== undefined });",
           "  const onUpdate = (u) => {\n"
           "    updates.push({ text: u.content[0]?.text ?? null, hasDetails: u.details !== undefined });\n"
           "    if (opt.abortOnOutput && (u.content[0]?.text ?? \"\").includes(opt.abortOnOutput)) controller.abort();\n"
           "  };")
src = once(src, "  const out = { id, command,", "  const out = { id, run, command,")
src = once(src, "  results.push(out);\n}", "  results.push(out);\n  if (!cleanupSandbox(base)) process.exitCode = 1;\n}")
out = ROOT / ".tmp/claude-scratch/wp133d/abort_trigger_probe.mjs"
out.write_text(src, encoding="utf-8", newline="\n")
print(f"wrote {out} ({len(src)} chars)")
