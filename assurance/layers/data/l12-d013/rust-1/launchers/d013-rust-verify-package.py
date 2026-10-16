"""Read-only check of the committed evidence ledger, never CRLF worktree bytes."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
import re
import subprocess

DOCS = 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/review-worktrees/codex-l12d013-rust-cert'
CODE = 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/review-worktrees/codex-l12d013-rust-impl'
CODE_HEAD = '1c0a1783a8109b85d2679eb7a294b1ada640010a'
PREFIX = 'assurance/layers/data/l12-d013/rust-1/'
assert len(sys.argv) == 2 and re.fullmatch('[0-9a-f]{40}', sys.argv[1])
head = subprocess.check_output(['git', '-C', DOCS, 'rev-parse', 'HEAD'], text=True).strip()
assert head == sys.argv[1]


def blob(relative):
    return subprocess.check_output(['git', '-C', DOCS, 'show', head + ':' + PREFIX + relative])


seen = set()
for line in blob('SHA256SUMS').decode('ascii').splitlines():
    match = re.fullmatch(r'([0-9a-f]{64})  ([a-zA-Z0-9_.\-/]+)', line)
    assert match, line
    digest, name = match.groups()
    assert name not in seen and all(p not in ('', '.', '..') for p in name.split('/'))
    seen.add(name)
    assert hashlib.sha256(blob(name)).hexdigest() == digest, name
assert seen
print('COMMITTED BLOB LEDGER VERIFIED', len(seen), 'entries at', head)


def source_json(repo, sha, path):
    return json.loads(subprocess.check_output(['git', '-C', repo, 'show', sha + ':' + path]))


fixtures = 'minion-agent-rust/crates/minion-agent/tests/data/'
assert source_json(CODE, CODE_HEAD, fixtures + 'node_read_domain.json') == source_json(
    DOCS, '4dd294c03c2c1311dfaa27051ab0930c122cbcfe',
    'assurance/layers/data/l12-d013/ce01/rd-1/node.out')
assert source_json(CODE, CODE_HEAD, fixtures + 'node_rooted_cwd.json') == source_json(
    CODE, '91a4ddef22ed707fc710da8b38588d404381d2a6',
    'minion-agent-python/tests/execution/data/node_rooted_cwd.json')
print('BOTH NODE-ONLY FIXTURES MATCH THEIR FROZEN SOURCE OBJECTS')
