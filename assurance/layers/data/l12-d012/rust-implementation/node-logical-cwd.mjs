// Observation only. No file writes or fixture paths. Both argument roles are JS strings.
import path from 'node:path';
import {homedir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {stripTypeScriptTypes} from 'node:module';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';

if (process.version !== 'v22.15.1') throw new Error('Node pin');
const pin = 'b7bb00b936dbe21b8e160b3e89efdec361846699';
const root = process.argv[2];
const sourcePath = 'packages/agent/src/harness/env/nodejs.ts';
const expected = execFileSync('git', ['rev-parse', `${pin}:${sourcePath}`], {cwd:root, encoding:'utf8'}).trim();
const bytes = execFileSync('git', ['show', `${pin}:${sourcePath}`], {cwd:root});
const blob = createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex');
if (blob !== expected) throw new Error('pinned Pi source blob');
const source = bytes.toString('utf8');
const start = source.indexOf('function resolvePath(cwd: string, path: string): string {');
const end = source.indexOf('function fileKindFromStats(', start);
if (start < 0 || end <= start) throw new Error('Pi function slice');
const body = stripTypeScriptTypes(source.slice(start, end));
const units = value => Array.from({length:value.length}, (_, i) => value.charCodeAt(i));
const rows = [];
for (const platform of ['win32', 'linux']) {
  const api = platform === 'win32' ? path.win32 : path.posix;
  // The import bindings select Node's declared path algorithm. These absolute
  // logical bases need neither a native cwd nor a per-drive environment read.
  const resolve = new Function('homedir', 'join', 'fileURLToPath', 'isAbsolute', 'resolve', 'process',
    body + '\nreturn resolvePath;')(homedir, api.join, fileURLToPath, api.isAbsolute, api.resolve, process);
  for (const [label, tail] of [['ascii','plain'], ['high','x\uD800y'], ['low','x\uDE00y'],
                              ['pair','x\uD83D\uDE00y'], ['bom','\uFEFFx']]) {
    const cwd = (platform === 'win32' ? 'C:\\logical\\' : '/logical/') + tail;
    const input = 'leaf';
    rows.push({platform, label, cwd:units(cwd), input:units(input), node:units(resolve(cwd, input))});
  }
}
console.log(JSON.stringify({node:process.version, host:process.platform, pi:pin, blob,
  source:'Unmodified pinned Pi resolvePath with Node win32/posix path imports; absolute logical cwd, no native reads', rows}, null, 1));
