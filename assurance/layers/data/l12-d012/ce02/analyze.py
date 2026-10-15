"""Audit recorded arrays. This models native decoding only, never path resolution.

Negative controls here test the characterization's boundary observations; they
are not implementation-closure credit. Compiled production mutants wait for an
AGREED checkpoint and a corrected green baseline.
"""
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

ROOT = Path('E:/AI/Projects/OpenMinds/Minions/Minion-Agent')
DOCS = ROOT / '.tmp/codex-scratch/l12d012-rust-docs'
OUT = DOCS / 'assurance/layers/data/l12-d012/ce02'
spec = importlib.util.spec_from_file_location('safety', ROOT/'review-worktrees/codex-l12d012-rust/minion-agent-rust/scripts/cargo-cache-safety.py')
safety = importlib.util.module_from_spec(spec)
spec.loader.exec_module(safety)


def view(raw):
    result = []
    i = 0
    while i < len(raw):
        unit = raw[i]
        if 0xd800 <= unit <= 0xdbff and i+1 < len(raw) and 0xdc00 <= raw[i+1] <= 0xdfff:
            result += raw[i:i+2]
            i += 2
            continue
        result += [0xfffd]*3 if 0xd800 <= unit <= 0xdfff else [unit]
        i += 1
    return result


def cwd_trim(raw):
    return raw[:-1] if raw and raw[-1] == 92 and not (len(raw) == 3 and raw[1] == 58) else raw[:]


def strip(raw):
    if raw[:8] == [92,92,63,92,85,78,67,92]:
        return [92,92] + raw[8:]
    if raw[:4] == [92,92,63,92]:
        return raw[4:]
    return raw[:]


def write(name, value):
    target = safety.checked(OUT/name, ROOT)
    assert not target.exists()
    safety.checked(target, ROOT).write_text(json.dumps(value,ensure_ascii=True,indent=2)+'\n',encoding='utf8')


def main():
    data = json.loads((OUT/'native-r3/native-win32.json').read_bytes())
    rows = data['report']
    mismatch = Counter()
    cwd_bad = []
    c1, c2, c3, c4 = [], [], [], []
    for index,row in enumerate(rows):
        raw = row['rust']['raw_getcwd_paired_child']
        assert raw == row['rust']['cwd']['raw']
        node = row['node']['cwd']
        assert node == view(cwd_trim(raw)), ('cwd boundary prediction',index)
        entry = row['entry_arg']
        assert row['node']['entries'][0]['view'] == (None if entry is None else view(entry))
        assert row['rust']['entries'][0]['selected_view'] == row['node']['entries'][0]['view']
        if row['rust']['cwd']['actual_cwd_view'] != node:
            cwd_bad.append(index)
        for input_index,match in enumerate(row['matches']):
            if not match:
                mismatch[(row['cwd_class'],input_index)] += 1
        # One source-prediction mutation per boundary rule, with exact failing row identities.
        if view(strip(cwd_trim(raw))) != node:
            c1.append(index)
        if view(raw) != node:
            c2.append(index)
        if entry is not None and view(strip(entry)) != row['node']['entries'][0]['view']:
            c3.append(index)
        if entry is not None and view(cwd_trim(entry)) != row['node']['entries'][0]['view']:
            c4.append(index)
    controls = []
    for name,fired in [('prefix-strip',c1),('cwd-trim-omitted',c2),('entry-prefix-strip',c3),('entry-cwd-trim',c4)]:
        assert fired, f'characterization control did not discriminate: {name}'
        controls.append({'id':name,'status':'CAUGHT_AT_CHARACTERIZATION_BOUNDARY','bad_rows':fired,
            'baseline':'196/196 Node cwd views and 196/196 Node+Rust inherited views agree with the source-predicted native boundary',
            'credit':'data-model audit only; NOT a compiled production-control kill'})
    summary = {'states':len(rows),'children':len(rows)*3,'resolver_observations':len(rows)*len(data['inputs']),
        'resolver_mismatches':sum(mismatch.values()),'raw_os_equals_rust_std':len(rows),
        'node_cwd_equals_source_boundary':len(rows),'node_entry_equals_rust_native_view':len(rows),
        'rejected_cwd_callback_mismatch_rows':cwd_bad,
        'resolver_mismatches_by_cwd_and_input':[{'cwd':cwd,'input_index':i,'count':n} for (cwd,i),n in mismatch.items()],
        'characterization_controls':controls}
    write('analysis.json',summary)
    p=safety.checked(OUT/'analyze.py',ROOT)
    assert not p.exists()
    safety.checked(p,ROOT).write_bytes(Path(__file__).read_bytes())
    print(json.dumps(summary,ensure_ascii=True))


if __name__ == '__main__':
    main()
