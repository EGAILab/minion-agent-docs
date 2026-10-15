"""Read-only native children; guarded NEW evidence files, no cleanup or resolver fix.

All child cwd values are EXISTING directories. Every arbitrary path case is a
string value only: it is never a filesystem target. This launcher creates no cwd
fixtures. E:\\ is used only as an existing read-only child cwd, with all caches
and output files under the fixed project root. No subprocess timeout/kill.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path('E:/AI/Projects/OpenMinds/Minions/Minion-Agent')
TREE = ROOT / 'review-worktrees/codex-l12d012-ce02/minion-agent-rust'
DOCS = ROOT / '.tmp/codex-scratch/l12d012-rust-docs'
OUT = DOCS / 'assurance/layers/data/l12-d012/ce02/native-r3'
PI = ROOT / 'ref-repos/pi'
PIN = 'b7bb00b936dbe21b8e160b3e89efdec361846699'
PI_FILE = 'packages/agent/src/harness/env/nodejs.ts'
NODE = 'C:/Program Files/nodejs/node.exe'
spec = importlib.util.spec_from_file_location('safety', TREE / 'scripts/cargo-cache-safety.py')
safety = importlib.util.module_from_spec(spec)
spec.loader.exec_module(safety)


def write(name, data):
    path = safety.checked(OUT / name, ROOT)
    assert not path.exists(), f'NEW evidence only: {path}'
    if not OUT.exists():
        safety.checked(OUT, ROOT).mkdir()
    safety.checked(path, ROOT).write_bytes(data if isinstance(data, bytes) else data.encode('utf8'))


def units(s):
    b = s.encode('utf-16-le', 'surrogatepass')
    return [int.from_bytes(b[i:i+2], 'little') for i in range(0, len(b), 2)]


NODE_CHILD = r'''
import {readFileSync} from 'node:fs';
import {homedir} from 'node:os';
import path from 'node:path';
import {stripTypeScriptTypes} from 'node:module';
import {fileURLToPath} from 'node:url';
const u=s=>Array.from({length:s.length},(_,i)=>s.charCodeAt(i));
const t=u=>String.fromCharCode(...u);
const payload=JSON.parse(process.env.CE02_INPUT);
const src=readFileSync(process.argv[1], 'utf8');
const body=stripTypeScriptTypes(src.slice(src.indexOf('function resolvePath(cwd: string, path: string): string {'),src.indexOf('function fileKindFromStats(')))+'\nreturn resolvePath;';
const resolvePath=new Function('homedir','join','fileURLToPath','isAbsolute','resolve','process',body)(homedir,path.join,fileURLToPath,path.isAbsolute,path.resolve,process);
console.log(JSON.stringify({cwd:u(process.cwd()),entries:['E:','A:','X:'].map(d=>({device:d,view:process.env['='+d]===undefined?null:u(process.env['='+d])})),home:u(homedir()),rows:payload.inputs.map(i=>u(resolvePath(t(payload.provider),t(i))))}));
'''

RAW_CHILD = r'''
import ctypes, json
k = ctypes.WinDLL('kernel32', use_last_error=True)
get = k.GetCurrentDirectoryW
get.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
get.restype = ctypes.c_uint32
size = get(0, None)
while True:
    assert size, ctypes.get_last_error()
    b = ctypes.create_string_buffer(size * 2)
    count = get(size, b)
    assert count, ctypes.get_last_error()
    if count < size:
        raw = b.raw[:count * 2]
        print(json.dumps([int.from_bytes(raw[i:i+2], 'little') for i in range(0,len(raw),2)]))
        break
    size = count
'''


def run(args, **kw):
    result = subprocess.run(args, capture_output=True, **kw)
    if result.returncode:
        raise RuntimeError((args, result.returncode, result.stdout[-2000:], result.stderr[-2000:]))
    return result.stdout


def main():
    assert sys.platform == 'win32'
    assert run([NODE, '--version']).strip() == b'v22.15.1'
    pinned = run(['git','-C',str(PI),'rev-parse',f'{PIN}:{PI_FILE}']).strip()
    assert run(['git','-C',str(PI),'hash-object',PI_FILE]).strip() == pinned
    assert run(['git','-C',str(TREE),'rev-parse','HEAD']).strip() == b'0389a29c59e56f9934f66bf9e13927858c5a65fc'
    assert run(['git','-C',str(TREE),'diff','--numstat']).decode().strip().endswith('crates/minion-agent/src/execution/path.rs')
    write('observer.rs', (TREE / 'crates/minion-agent/src/execution/ce02_observer.rs').read_bytes())
    write('observer.patch', run(['git','-C',str(TREE),'diff','--','crates/minion-agent/src/execution/path.rs']))
    write('launcher.py', Path(__file__).read_bytes())
    safety.refresh(TREE)
    environment = dict(os.environ, CARGO_BUILD_JOBS='4', PYTHONDONTWRITEBYTECODE='1',
        RUST_ICU_MAJOR_VERSION_NUMBER='78',
        RUSTFLAGS='-L native='+str(ROOT / '.toolchain/icu-78.3-src/icu/lib64').replace('\\','/'),
        MINION_AGENT_ICU_IDENTITY=str(ROOT / '.toolchain/icu-78.3-src/pinned-icu-identity.txt'),
        MINION_SEARCH_ENGINE_ARTIFACTS=str(ROOT / '.toolchain/search-engines/dl'),
        NODE_DISABLE_COMPILE_CACHE='1',
        PATH=str(ROOT / '.toolchain/icu-78.3-src/icu/bin64')+os.pathsep+os.environ['PATH'])
    environment.pop('NODE_COMPILE_CACHE', None)
    build = subprocess.run(['cargo','test','--locked','-p','minion-agent','--lib','--no-run','--message-format=json'], cwd=TREE, env=environment, capture_output=True)
    write('observer-build.stdout.jsonl', build.stdout)
    write('observer-build.stderr.txt', build.stderr)
    assert build.returncode == 0, build.stderr[-4000:]
    artifacts = [json.loads(line) for line in build.stdout.decode().splitlines() if line.startswith('{')]
    binaries = [x['executable'] for x in artifacts if x.get('reason') == 'compiler-artifact' and x.get('executable') and x['target']['name']=='minion_agent']
    assert len(binaries) == 1, binaries
    binary = binaries[0]
    fixture = ROOT / '.tmp/codex-scratch/l12d012-rust-windows-io-final/probe-fixture'
    plain = str(fixture / 'plain')
    assert Path(plain).is_dir() and plain.startswith('E:')
    cwds = [('plain',plain),('plain-trailing',plain+'\\'),('extended','\\\\?\\'+plain),('extended-trailing','\\\\?\\'+plain+'\\'),('drive-root','E:\\'),('extended-root','\\\\?\\E:\\')]
    for p in sorted(fixture.iterdir()):
        if p.name != 'plain':
            assert p.is_dir() and not p.is_symlink()
            cwds += [('unicode-'+p.name, str(p)), ('unicode-extended-'+p.name,'\\\\?\\'+str(p))]
    entries = [('absent',None),('empty',''),('matching','E:\\deep'),('matching-trailing','E:\\deep\\'),('other-drive','A:\\deep'),('drive-relative','E:deep'),('extended','\\\\?\\E:\\deep'),('extended-root','\\\\?\\E:\\'),('unc','\\\\server\\share\\deep'),('extended-unc','\\\\?\\UNC\\server\\share\\deep'),('pair','E:\\pair\U0001f600'),('high','E:\\high\ud800'),('low','E:\\low\udc00'),('bom','E:\\\ufeffdeep')]
    inputs = ['e:leaf','\\leaf','E:\\absolute','leaf','a:leaf']
    maps = ['E:\\','E:\\deep\\','\\\\?\\E:\\','\\\\?\\E:\\deep\\','\\\\server\\share\\','\\\\?\\UNC\\server\\share\\','E:\\x\ud800','\\\\?\\E:\\x\ud800','E:\\x\U0001f600','E:\\\ufeffx','\\\\.\\E:\\','e:/deep/']
    payload = json.dumps({'provider':units('C:\\x'),'inputs':list(map(units,inputs)),'mapping_inputs':list(map(units,maps))})
    report = []
    for label,cwd in cwds:
        # Existing read-only cwd. No child writes; Windows drive roots are not output targets.
        assert os.path.isdir(cwd)
        for entry_label, entry in entries:
            env = {k:v for k,v in environment.items() if not k.startswith('=')}
            env['CE02_INPUT'] = payload
            if entry is not None:
                env['=E:'] = entry
            node = json.loads(run([NODE,'--no-warnings','--input-type=module','-e',NODE_CHILD,str(PI/PI_FILE)],cwd=cwd,env=env))
            rustout = run([binary,'execution::path::ce02_observer::observe','--exact','--ignored','--nocapture'],cwd=cwd,env=env)
            lines = [line[5:] for line in rustout.decode().splitlines() if line.startswith('CE02 ')]
            assert len(lines) == 1
            rust = json.loads(lines[0])
            assert rust['entries'][0]['raw'] == (None if entry is None else units(entry))
            raw_cwd = json.loads(run([sys.executable,'-c',RAW_CHILD],cwd=cwd,env=env))
            assert raw_cwd == rust['cwd']['raw'], 'raw GetCurrentDirectoryW and Rust std disagree'
            rust['raw_getcwd_paired_child'] = raw_cwd
            matches = [r['absolute_path']==n and r['logical']==n for r,n in zip(rust['rows'],node['rows'],strict=True)]
            report.append({'cwd_class':label,'cwd_arg':units(cwd),'entry_class':entry_label,'entry_arg':None if entry is None else units(entry),'node':node,'rust':rust,'matches':matches})
    write('native-win32.json', json.dumps({'pin':PIN,'node':'22.15.1','code':'0389a29c59e56f9934f66bf9e13927858c5a65fc','inputs':list(map(units,inputs)),'report':report},ensure_ascii=True,indent=1)+'\n')
    print(json.dumps({'children':len(report)*3,'states':len(report),'observations':len(report)*len(inputs),'mismatches':sum(not m for row in report for m in row['matches'])}))


if __name__ == '__main__':
    main()
