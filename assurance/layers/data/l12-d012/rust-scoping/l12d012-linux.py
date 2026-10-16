"""Scoping-only Linux observer. All writes are proven under private /tmp or /logs."""
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

ROOT = Path('/tmp/l12d012')

def checked(path, boundary=ROOT):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or path == boundary or not path.is_relative_to(boundary):
        raise RuntimeError('outside sandbox: ' + str(path))
    for ancestor in [*reversed(path.parents), path]:
        try:
            m = ancestor.lstat()
        except FileNotFoundError:
            break
        if stat.S_ISLNK(m.st_mode):
            raise RuntimeError('link: ' + str(ancestor))
    if not path.resolve(strict=False).is_relative_to(boundary.resolve(strict=True)):
        raise RuntimeError('outside real sandbox')
    return path

def mkdir(path, boundary=ROOT):
    path = checked(path, boundary)
    missing = []
    current = path
    while True:
        try:
            current.lstat()
            break
        except FileNotFoundError:
            missing.append(current)
            current = current.parent
    for item in reversed(missing):
        checked(item, boundary).mkdir()

def copy_tree(src, dst):
    for directory, dirs, files in os.walk(src, followlinks=False):
        for name in list(dirs):
            if name in ('.git', 'target'):
                dirs.remove(name)
            elif not stat.S_ISDIR((Path(directory) / name).lstat().st_mode):
                raise RuntimeError('source link/directory')
        target = dst / Path(directory).relative_to(src)
        mkdir(target)
        for name in files:
            original = Path(directory) / name
            if not stat.S_ISREG(original.lstat().st_mode):
                raise RuntimeError('source not regular')
            shutil.copyfile(original, checked(target / name)) # Fresh mtime, never copy2.

if ROOT.exists():
    raise RuntimeError('fresh tmpfs required')
mkdir(ROOT, Path('/tmp'))
mkdir(ROOT / 'bin')
shutil.copyfile('/node', checked(ROOT / 'bin/node'))
os.chmod(checked(ROOT / 'bin/node'), 0o755)
env = dict(os.environ)
env.update({
    'CARGO_HOME': '/cargo-home', 'CARGO_TARGET_DIR': '/target', 'CARGO_BUILD_JOBS': '4',
    'RUSTUP_HOME': '/cargo-home/rustup', 'RUSTUP_TOOLCHAIN': '1.97.1',
    'RUST_ICU_MAJOR_VERSION_NUMBER': '78', 'RUSTFLAGS': '-L native=/build/icu/lib',
    'MINION_AGENT_ICU_IDENTITY': '/build/icu-identity.txt', 'LD_LIBRARY_PATH': '/build/icu/lib',
    'MINION_SEARCH_ENGINE_ARTIFACTS': '/search-artifacts',
    'TMP': str(ROOT), 'TEMP': str(ROOT), 'TMPDIR': str(ROOT),
    'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPYCACHEPREFIX': '/cargo-home/pycache',
    'NODE_COMPILE_CACHE': '/cargo-home/node-cache', 'XDG_CACHE_HOME': '/cargo-home/xdg',
    'PATH': str(ROOT / 'bin') + ':/cargo-home/rustup/toolchains/1.97.1-x86_64-unknown-linux-gnu/bin:' + os.environ['PATH'],
})
bins = []
for variant in ('main', 'draft'):
    src = Path('/' + variant)
    work = ROOT / variant
    copy_tree(src / 'minion-agent-rust', work / 'minion-agent-rust')
    copy_tree(src / 'conformance', work / 'conformance')
    for relative in (
        'pi-parity-manifest.yaml',
        'minion-agent-python/tests/skills/data/frontmatter-corpus.json',
        'minion-agent-python/tests/skills/data/ignore-corpus.json',
        'minion-agent-python/tests/execution/data/r002_ada_oracle/systematic_ada292.txt',
    ):
        target = work / relative
        mkdir(target.parent)
        shutil.copyfile(src / relative, checked(target))
    print('START BUILD', variant, flush=True)
    buildlog = checked(Path('/logs') / (variant + '-build.jsonl'), Path('/logs'))
    with buildlog.open('w') as output:
        result = subprocess.run(['cargo', 'test', '--locked', '-p', 'minion-agent', '--lib', '--no-run', '--message-format=json'],
            cwd=work / 'minion-agent-rust', env=env, stdout=output)
    checked(Path('/logs') / (variant + '-build.exit'), Path('/logs')).write_text(str(result.returncode) + '\n')
    if result.returncode:
        raise SystemExit(result.returncode)
    records = [json.loads(line) for line in buildlog.read_text().splitlines() if line.startswith('{')]
    executable = [r['executable'] for r in records if r.get('executable') and r['target']['name'] == 'minion_agent' and r['profile']['test']]
    if len(executable) != 1:
        raise RuntimeError('artifact count')
    binary = checked(ROOT / 'bin' / (variant + '-observer'))
    shutil.copyfile(executable[0], binary)
    os.chmod(checked(binary), 0o755)
    bins.append(str(binary))
    print('END BUILD', variant, flush=True)

output = checked(Path('/logs/observations.json'), Path('/logs'))
with output.open('w') as handle:
    result = subprocess.run(['node', '--no-warnings', '/scripts/l12d012-characterize.mjs', 'run', '/pi', '/matrix', *bins],
        cwd=ROOT, env=env, stdout=handle)
checked(Path('/logs/observations.exit'), Path('/logs')).write_text(str(result.returncode) + '\n')
if result.returncode:
    raise SystemExit(result.returncode)
print('L12D012 LINUX OBSERVATIONS COMPLETE', flush=True)
