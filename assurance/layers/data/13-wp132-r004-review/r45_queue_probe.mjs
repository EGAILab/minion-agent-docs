import {readFileSync, writeFileSync, mkdirSync} from 'node:fs';
import {resolve} from 'node:path';
import assert from 'node:assert/strict';
const source = readFileSync('/pi/packages/coding-agent/src/core/tools/file-mutation-queue.ts', 'utf8');
const deferred = () => {let resolve, reject; const p = new Promise((a,b)=>{resolve=a;reject=b;}); return {p,resolve,reject};};
const flush = async () => {for(let i=0;i<20;i++) await new Promise(r=>setImmediate(r));};
for (const mutant of [false, true]) {
  const trace = [];
  let lookup = 0;
  globalThis.probeRealpath = async (path) => {
    const name = ['f.txt','./f.txt','sub/../f.txt'][lookup++];
    trace.push(`p canonical_path ${name} #1 ok`);
    return '/w/f.txt';
  };
  const abortB = deferred();
  globalThis.probeAbort = path => path === './f.txt' ? abortB.p : new Promise(()=>{});
  let body = source.replace('import { realpath } from "node:fs/promises";', 'const realpath = globalThis.probeRealpath;');
  if (mutant) body = body.replace('await currentQueue;', `try { await Promise.race([currentQueue, globalThis.probeAbort(filePath)]); }
    catch (e) { releaseNext(); if (fileMutationQueues.get(key) === chainedQueue) fileMutationQueues.delete(key); throw e; }`);
  const file = `/tmp/queue-probe-${mutant}.ts`;
  writeFileSync(file, body);
  const {withFileMutationQueue} = await import(file);
  const gate = deferred();
  let aborted = false;
  let finalFile = 'original\n';
  const calls = [
    withFileMutationQueue('f.txt', async () => {
      trace.push('p write_file f.txt #1 start'); await gate.p;
      trace.push('p write_file f.txt #1 permission_denied'); throw new Error('Cannot write f.txt: permission denied');
    }),
    withFileMutationQueue('./f.txt', async () => {
      if (aborted) throw new Error('Operation aborted');
      trace.push('p absolute_path ./f.txt #1 start'); return 'B';
    }),
    withFileMutationQueue('sub/../f.txt', async () => {
      trace.push('p absolute_path sub/../f.txt #1 start'); finalFile = 'C'; return 'Successfully wrote 1 bytes to sub/../f.txt';
    }),
  ].map((p,i)=>p.then(value=>{trace.push(`result ${'ABC'[i]}`);return value;}, error=>{trace.push(`result ${'ABC'[i]}`);return error.message;}));
  await flush(); aborted = true;
  if(mutant) abortB.reject(new Error('Operation aborted'));
  await flush(); gate.resolve(); await flush();
  const results = await Promise.all(calls);
  const expectedOrders = [
    ['p canonical_path ./f.txt #1 ok', 'result A'],
    ['p write_file f.txt #1 permission_denied', 'p absolute_path sub/../f.txt #1 start'],
  ];
  const currentAssertionsPass = expectedOrders.every(([a,b])=>trace.includes(a) && (!trace.includes(b)||trace.indexOf(a)<trace.indexOf(b)))
    && !trace.includes('p absolute_path ./f.txt #1 start')
    && JSON.stringify(results) === JSON.stringify(['Cannot write f.txt: permission denied','Operation aborted','Successfully wrote 1 bytes to sub/../f.txt'])
    && finalFile === 'C';
  const requiredLockTiming = trace.indexOf('p write_file f.txt #1 permission_denied')<trace.indexOf('result B');
  assert.equal(currentAssertionsPass, true);
  assert.equal(requiredLockTiming, !mutant);
  console.log(JSON.stringify({mutant,trace,currentAssertionsPass,requiredLockTiming}));
}
