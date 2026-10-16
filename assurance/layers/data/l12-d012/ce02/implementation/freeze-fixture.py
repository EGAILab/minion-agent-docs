"""Print an apply_patch payload; never write the generated fixture directly.

Native rows come only from the sealed Node observations. Predicate rows are
explicit source-operator witnesses, not claims of reachable OS cwd spellings.
Only the old fixture prefix is parameterized, without recomputing resolution.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path('E:/AI/Projects/OpenMinds/Minions/Minion-Agent')
archive = ROOT / '.tmp/codex-scratch/l12d012-rust-docs/assurance/layers/data/l12-d012/ce02/native-r3/native-win32.json'
source = json.loads(archive.read_bytes())
prefix = str(ROOT / '.tmp/codex-scratch/l12d012-rust-windows-io-final/probe-fixture').replace('/', '\\')

def units(s):
    b = s.encode('utf-16-le', 'surrogatepass')
    return [int.from_bytes(b[i:i+2], 'little') for i in range(0, len(b), 2)]

def view(raw):
    # A test-data operator only. No resolver calls or expected paths computed.
    out = []
    i = 0
    while i < len(raw):
        u = raw[i]
        if 0xD800 <= u <= 0xDBFF and i+1 < len(raw) and 0xDC00 <= raw[i+1] <= 0xDFFF:
            out += raw[i:i+2]
            i += 2
            continue
        out += [0xFFFD]*3 if 0xD800 <= u <= 0xDFFF else [u]
        i += 1
    return out

values = []
def intern(raw):
    if raw is None:
        return None
    parts = []
    remaining = raw[:]
    # Include the lowercase-drive prefix that Node's final result may carry.
    while remaining:
        found = []
        for kind, p in [('upper', prefix), ('lower', prefix[0].lower()+prefix[1:])]:
            needle = units(p)
            for i in range(len(remaining)-len(needle)+1):
                if remaining[i:i+len(needle)] == needle:
                    found.append((i, kind, len(needle)))
                    break
        if not found:
            parts.append(remaining)
            break
        i, kind, length = min(found)
        if i:
            parts.append(remaining[:i])
        parts.append({'fixture': kind})
        remaining = remaining[i+length:]
    if parts not in values:
        values.append(parts)
    return values.index(parts)

cwd_rows = []
entry_rows = []
native_rows = []
seen_cwd = set()
seen_entry = set()
for row in source['report']:
    if row['cwd_class'] not in seen_cwd:
        seen_cwd.add(row['cwd_class'])
        cwd_rows.append({'label':row['cwd_class'], 'raw':row['rust']['cwd']['raw'], 'node':row['node']['cwd']})
    if row['entry_class'] not in seen_entry and row['entry_arg'] is not None:
        seen_entry.add(row['entry_class'])
        entry_rows.append({'label':row['entry_class'], 'raw':row['entry_arg'], 'node':row['node']['entries'][0]['view']})
    native_rows.append({'cwd_class':row['cwd_class'], 'entry_class':row['entry_class'],
        'cwd_arg':intern(row['cwd_arg']), 'raw':intern(row['rust']['cwd']['raw']),
        'cwd_view':intern(row['node']['cwd']), 'entry':intern(row['entry_arg']),
        'entry_view':intern(row['node']['entries'][0]['view']),
        'expected':[intern(x) for x in row['node']['rows']]})

predicate_rows = []
forms = [('ordinary','E:\\deep'), ('extended','\\\\?\\E:\\deep'),
    ('unc','\\\\server\\share'), ('extended-unc','\\\\?\\UNC\\server\\share'),
    ('device','\\\\.\\E:\\deep')]
tails = [('scalar',[]), ('pair',[0xD83D,0xDE00]), ('high',[0xD800]), ('low',[0xDC00]), ('bom',[0xFEFF])]
for name, base in forms:
    for tail_name, tail in tails:
        for end_name, ending in [('none',[]), ('backslash',[92]), ('forward',[47]), ('double',[92,92])]:
            raw = units(base)+tail+ending
            trimmed = raw[:-1] if raw[-1:] == [92] and not (len(raw)==3 and raw[1]==58) else raw
            predicate_rows.append({'label':f'{name}/{tail_name}/{end_name}', 'raw':raw, 'expected':view(trimmed)})
for label, raw in [('ordinary-root',units('E:\\')), ('extended-root',units('\\\\?\\E:\\')),
    ('nonletter-root',[63,58,92]), ('surrogate-root',[0xD800,58,92]),
    ('two-unit',[58,92]), ('three-noncolon',[65,65,92]), ('empty',[])]:
    trimmed = raw[:-1] if raw[-1:] == [92] and not (len(raw)==3 and raw[1]==58) else raw
    predicate_rows.append({'label':label, 'raw':raw, 'expected':view(trimmed)})
fixture = {'provenance':{'node':'22.15.1','pi':source['pin'], 'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
    'cwd_and_entry_rows':'frozen native Node observations; absolute strings are values only',
    'predicate_rows':'source-derived libuv raw-unit operator, including non-reachable strings',
    'templates':'only the archived fixture prefix replaced; no path expectations recomputed'},
    'cwd_rows':cwd_rows,'entry_rows':entry_rows,'predicate_rows':predicate_rows,
    'inputs':source['inputs'],'values':values,'native_rows':native_rows}
assert len(cwd_rows)==14 and len(entry_rows)==13 and len(native_rows)==196
def ascii_labels(value):
    if isinstance(value, str):
        return value.encode('ascii', 'backslashreplace').decode('ascii')
    if isinstance(value, list):
        return [ascii_labels(item) for item in value]
    if isinstance(value, dict):
        return {key:ascii_labels(item) for key,item in value.items()}
    return value
fixture=ascii_labels(fixture)
target=ROOT/'review-worktrees/codex-l12d012-rust/minion-agent-rust/crates/minion-agent/tests/data/node_native_operand.json'
# Compact per top-level field, keeping output under the tool transport limit.
body='{\n'+',\n'.join('  '+json.dumps(k)+': '+json.dumps(v,ensure_ascii=True,separators=(',',':')) for k,v in fixture.items())+'\n}\n'
if target.exists():
    print('*** Begin Patch\n*** Update File: '+str(target).replace('\\','/')+'\n@@\n'+''.join('-'+line+'\n' for line in target.read_text().splitlines())+''.join('+'+line+'\n' for line in body.splitlines())+'*** End Patch')
else:
    print('*** Begin Patch\n*** Add File: '+str(target).replace('\\','/')+'\n'+''.join('+'+line+'\n' for line in body.splitlines())+'*** End Patch')
