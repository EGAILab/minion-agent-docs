// Observation only: all colon-bearing paths are values, never OS targets.
import fs from 'node:fs';
import path from 'node:path';
import {homedir} from 'node:os';
import {spawnSync} from 'node:child_process';
import {stripTypeScriptTypes} from 'node:module';
import {fileURLToPath} from 'node:url';
const [mode, piRoot, matrix, mainBin, draftBin] = process.argv.slice(2);
if (process.version !== 'v22.15.1') throw new Error('Node pin');
const providerCwd=process.platform==='win32'?'C:\\x':'/x';
const units=s=>Array.from({length:s.length},(_,i)=>s.charCodeAt(i));
const readResolve=()=>{
  const src=fs.readFileSync(path.join(piRoot,'packages/agent/src/harness/env/nodejs.ts'),'utf8');
  const a=src.indexOf('function resolvePath(cwd: string, path: string): string {');
  const b=src.indexOf('function fileKindFromStats(',a);
  if(a<0||b<=a) throw new Error('authority slice');
  return new Function('homedir','join','fileURLToPath','isAbsolute','resolve','process',
    stripTypeScriptTypes(src.slice(a,b))+'\nreturn resolvePath;')(
    homedir,path.join,fileURLToPath,path.isAbsolute,path.resolve,process);
};
if(mode==='oracle') {
  const inputs=JSON.parse(process.env.L12D012_INPUTS);
  const resolve=readResolve();
  console.log(JSON.stringify({cwd:process.cwd(),hidden_env:['=E:','=A:','=X:'].map(n=>[n,process.env[n]??null]),
    rows:inputs.map(input=>({input,result:units(resolve(providerCwd,input))}))}));
} else {
  if(mode!=='run') throw new Error('mode');
  const inputs=JSON.parse(fs.readFileSync(matrix,'utf8')).rows.map(r=>r.input);
  if(inputs.length!==23) throw new Error('matrix count');
  const base=Object.fromEntries(Object.entries(process.env).filter(([n])=>!n.startsWith('=')));
  const run=(binary,args,env)=>{
    const p=spawnSync(binary,args,{env,encoding:'utf8',timeout:60000});
    if(p.error||p.status!==0) throw new Error('child: '+p.status+' '+p.stderr+' '+p.stdout);
    return p.stdout;
  };
  const observe=(label,values,env)=>{
    env={...env,L12D012_INPUTS:JSON.stringify(values)};
    const oracle=JSON.parse(run(process.execPath,['--no-warnings',fileURLToPath(import.meta.url),'oracle',piRoot],env));
    const bindings={};
    for(const [name,binary] of [['certified_main',mainBin],['draft_224',draftBin]]) {
      const output=run(binary,['execution::l12d012_scoping::characterize','--exact','--nocapture'],env);
      const matches=output.match(/^SCOPING_JSON (.+)$/gm);
      if(matches?.length!==1) throw new Error('one Rust observation required '+output);
      const observed=JSON.parse(matches[0].slice('SCOPING_JSON '.length));
      if(JSON.stringify(observed.hidden_env)!==JSON.stringify(oracle.hidden_env)) throw new Error('Rust hidden environment differs');
      if(observed.rows.length!==values.length) throw new Error('Rust rows incomplete');
      bindings[name]={...observed,comparisons:observed.rows.map((r,i)=>Object.fromEntries(
        ['absolute_path','logical','native_scalar','draft_lossless'].map(k=>[k,r[k]===null?null:JSON.stringify(r[k])===JSON.stringify(oracle.rows[i].result)])))};
    }
    return {label,oracle,bindings};
  };
  const observations=[observe('baseline-23',inputs,base)];
  if(process.platform==='win32') {
    const variants=[null,'','D:\\deep','d:\\deep','D:/deep','D:rel','D:','X:\\other','X:/other','X:other',
      'X:','relative','\\deep','/deep','\\\\srv\\share','r'];
    for(const drive of ['E','A']) for(const value of variants) {
      const v=value===null?null:value.replaceAll('D:',drive+':').replaceAll('d:',drive.toLowerCase()+':');
      observations.push(observe(`${drive}:${JSON.stringify(v)}`,[drive.toLowerCase()+':leaf'],
        v===null?base:{...base,['='+drive+':']:v}));
    }
  } else {
    observations.push(observe('posix-drive-spellings-not-host-state',['e:leaf','a:leaf'],base));
  }
  console.log(JSON.stringify({node:process.version,platform:process.platform,
    pi:'b7bb00b936dbe21b8e160b3e89efdec361846699',
    certified_main:'f12d129eb00a18a82a90a18d980d0d2b14a80519',
    draft_224:'1790d36fd0f428bbdfb7528c6ab433d2b57a3942',observations},null,2));
}
