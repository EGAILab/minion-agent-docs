"""After Windows gates exit: replay only the in-memory 48-row observer.

Binary is selected from the gate's Cargo artifact, never the mutation cache.
New exclusive captures, no timeouts, no deletes, no global cwd/env changes.
"""
import sys
sys.dont_write_bytecode = True
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import hashlib

ROOT=Path('E:/AI/Projects/OpenMinds/Minions/Minion-Agent')
TREE=ROOT/'review-worktrees/codex-l12d013-rust-impl/minion-agent-rust'
LOGS=ROOT/'.tmp/codex-scratch/d013-rust-runs/win2'
RUN=ROOT/'.tmp/codex-scratch/d013-rust-characterization1'
spec=importlib.util.spec_from_file_location('safety',TREE/'scripts/cargo-cache-safety.py')
safety=importlib.util.module_from_spec(spec)
spec.loader.exec_module(safety)
head=subprocess.check_output(['git','-C',str(TREE.parent),'rev-parse','HEAD'],text=True).strip()
assert head=='1c0a1783a8109b85d2679eb7a294b1ada640010a'
assert not subprocess.check_output(['git','-C',str(TREE.parent),'status','--porcelain'],text=True).strip()
assert (LOGS/'complete.exit').read_text().strip()=='0'
events=[json.loads(line) for line in (LOGS/'observer-build.log').read_text().splitlines() if line.startswith('{')]
artifacts=[r for r in events if r.get('executable') and r.get('target',{}).get('name')=='minion_agent']
assert len(artifacts)==1
binary=safety.checked(Path(artifacts[0]['executable']),ROOT)
assert binary.is_file() and binary.is_relative_to(ROOT/'.tmp/cache/cargo-target/windows')
assert not RUN.exists()
safety.checked(RUN,ROOT).mkdir()
os.environ['PATH']=str(ROOT/'.toolchain/icu-78.3-src/icu/bin64')+os.pathsep+os.environ['PATH']
with safety.checked(RUN/'observe.log',ROOT).open('x',encoding='utf-8') as log:
    result=subprocess.run([str(binary),'execution::div009_tests::extended_provider_48_observations_not_certification','--exact','--nocapture'],cwd=TREE,stdout=log,stderr=subprocess.STDOUT)
with safety.checked(RUN/'observe.exit',ROOT).open('x',encoding='ascii') as out:
    out.write(str(result.returncode)+'\n')
assert result.returncode==0
prefix='EXTENDED_PROVIDER_OBSERVATIONS '
rows=[json.loads(line[len(prefix):]) for line in (RUN/'observe.log').read_text(encoding='utf-8').splitlines() if line.startswith(prefix)]
assert len(rows)==1 and len(rows[0])==48
assert len({(r['input'],r['entry']) for r in rows[0]})==48
oracle=json.loads((TREE/'crates/minion-agent/tests/data/node_read_domain.json').read_text())['rows']
oracle={(r['input'],r['entries']):r for r in oracle if r['platform']=='win32' and r['provider']=='\\\\?\\C:\\base'}
assert len(oracle)==48
differences=[]
for row in rows[0]:
    expected=oracle[(row['input'],row['entry'])]
    encoded=expected['value'].encode('utf-16-le','surrogatepass')
    expected_units=[int.from_bytes(encoded[i:i+2],'little') for i in range(0,len(encoded),2)]
    expected_entries=[value.upper() for value in expected['envReads']]
    row['envReadCount']=len(row['envReads'])
    row['oracle']={'value':expected_units,'cwdReads':expected['cwdReads'],
                   'envReadCount':len(expected_entries),'envReads':expected_entries}
    row['differs']=(row['value'],row['cwdReads'],row['envReads'])!=(expected_units,expected['cwdReads'],expected_entries)
    if row['differs']: differences.append((row['input'],row['entry']))
assert set(differences)=={(input,entry) for input in ('c:leaf','leaf','') for entry in ('absent','empty','same','other')}
payload={'code':head,'binary':str(binary),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
         'scope':'observations only, not certification; expected twelve differences tracked in #241; env read names case-normalized',
         'same':36,'different':12,'rows':rows[0]}
with safety.checked(RUN/'observations.json',ROOT).open('x',encoding='utf-8',newline='\n') as out:
    json.dump(payload,out,ensure_ascii=True,indent=1);out.write('\n')
print('48 observations captured from gate binary',binary)
