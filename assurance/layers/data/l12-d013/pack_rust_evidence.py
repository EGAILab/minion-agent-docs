"""Mechanical evidence transfer: new destination, no cleanup, every write guarded.

Run after all gate processes exit. No source/candidate file is modified.
Copies fixed gate-log directories only (not fixture or control-code trees).
Text captures are normalized to LF; ledger hashes those committed spellings.
"""
import sys
sys.dont_write_bytecode = True
import hashlib
import importlib.util
from pathlib import Path
import re

ROOT = Path('E:/AI/Projects/OpenMinds/Minions/Minion-Agent')
CODE = ROOT / 'review-worktrees/codex-l12d013-rust-impl/minion-agent-rust'
DOCS = ROOT / 'review-worktrees/codex-l12d013-rust-cert'
OUT = DOCS / 'assurance/layers/data/l12-d013/rust-1'
spec = importlib.util.spec_from_file_location('safety', CODE / 'scripts/cargo-cache-safety.py')
safety = importlib.util.module_from_spec(spec)
spec.loader.exec_module(safety)
assert not OUT.exists(), 'new evidence package required'
safety.checked(OUT, ROOT).mkdir()
records = []


def put(relative, content):
    assert all(re.fullmatch(r'[a-zA-Z0-9_.-]+', p) and p not in ('.', '..')
               for p in relative.parts)
    target = OUT / relative
    pending = []
    parent = target.parent
    while not parent.exists():
        pending.append(parent)
        parent = parent.parent
    for folder in reversed(pending):
        safety.checked(folder, ROOT).mkdir()
    data = content.replace(b'\r\n', b'\n')
    with safety.checked(target, ROOT).open('xb') as output:
        output.write(data)
    records.append((relative.as_posix(), hashlib.sha256(data).hexdigest()))


def logs(source, label):
    source = safety.checked(source, ROOT)
    assert source.is_dir()
    for file in sorted(source.iterdir()):
        if file.is_file() and file.suffix in ('.log', '.exit', '.json', '.txt'):
            assert not file.is_symlink()
            put(Path(label) / file.name, safety.checked(file, ROOT).read_bytes())
        elif file.name == 'control-details' and file.is_dir():
            logs(file, label + '/control-details')


logs(ROOT / '.tmp/codex-scratch/d013-rust-runs/win2', 'windows')
logs(ROOT / '.tmp/codex-scratch/d013-rust-runs/linux1/run', 'linux')
put(Path('linux/host-preflight.log'), safety.checked(
    ROOT / '.tmp/codex-scratch/d013-rust-runs/linux1/preflight.log', ROOT).read_bytes())
logs(ROOT / '.tmp/codex-scratch/d013-rust-schema1', 'schema')
logs(ROOT / '.tmp/codex-scratch/d013-rust-characterization1', 'extended-provider')
for run in ('focused1', 'focused2', 'focused3', 'focused4', 'focused5','win1'):
    logs(ROOT / '.tmp/codex-scratch/d013-rust-runs' / run, 'development/' + run)
for name in ('d013-rust-schema-check.py', 'd013-rust-characterize.py',
             'd013-rust-verify-package.py'):
    source = safety.checked(ROOT / '.tmp/codex-scratch' / name, ROOT)
    put(Path('launchers') / name, source.read_bytes())
ledger = ''.join(digest + '  ' + name + '\n' for name, digest in sorted(records))
with safety.checked(OUT / 'SHA256SUMS', ROOT).open('xb') as output:
    output.write(ledger.encode('ascii'))
print('PACKAGED', len(records), 'files', OUT)
