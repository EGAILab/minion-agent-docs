import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
const repo=process.argv[2], rel='assurance/layers/data/l12-d012/rust-scoping';
const hash=b=>createHash('sha256').update(b).digest('hex');
for(const row of fs.readFileSync(path.join(repo,rel,'sha256.txt'),'utf8').trim().split('\n')) {
  const [sha,name]=row.split('  ');
  if(hash(fs.readFileSync(path.join(repo,rel,name)))!==sha) throw new Error('disk ledger '+name);
  const blob=execFileSync('git',['-C',repo,'show',':'+rel+'/'+name]);
  if(hash(blob)!==sha) throw new Error('staged blob ledger '+name);
}
for(const [file,groups,total] of [['windows-observations.json',33,55],['linux-observations.json',2,25]]) {
  const j=JSON.parse(fs.readFileSync(path.join(repo,rel,file),'utf8'));
  if(j.observations.length!==groups) throw new Error('groups');
  if(j.observations.reduce((n,o)=>n+o.oracle.rows.length,0)!==total) throw new Error('rows');
  for(const o of j.observations) for(const [name,b] of Object.entries(o.bindings)) {
    if(JSON.stringify(b.hidden_env)!==JSON.stringify(o.oracle.hidden_env)) throw new Error('hidden environment');
    for(let i=0;i<b.rows.length;i++) for(const key of ['absolute_path','logical','native_scalar','draft_lossless']) {
      const value=b.rows[i][key], expected=o.oracle.rows[i].result;
      if(value!==null && (!Array.isArray(value)||value.some(n=>!Number.isInteger(n)||n<0||n>65535))) throw new Error('units');
      const match=value===null?null:JSON.stringify(value)===JSON.stringify(expected);
      if(match!==b.comparisons[i][key]) throw new Error('comparison');
      if(name==='certified_main'&&key==='draft_lossless'&&value!==null) throw new Error('draft credit on main');
    }
  }
}
console.log('LEDGER staged blobs PASS; 55 Windows + 25 Linux per source; all comparisons recomputed PASS');
