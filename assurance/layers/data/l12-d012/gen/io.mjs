// L12-D012 generation: EVERY computed filesystem mutation of the launcher and generator happens here, each immediately
// after its reviewed fs-guard proof (CE-L12D007-01; pattern of l12-d011/gen/io.mjs). The guard instance is passed in.
//   makeRun:     REFERENT proof of the run directory's whole ancestry (makeSandbox) BEFORE its mkdir, then a proof of
//                each of the two child cwd directories (`cwd-a`, `cwd-b`) before its mkdir. One plain run-name component.
//   writeOutput: REFERENT proof of the final output entry (assertOutput) immediately before the write.
// Nothing is ever deleted. The child cwd directories stay empty: the resolver is lexical and nothing is written there.
import fs from "node:fs";
import path from "node:path";

const RUN_NAME = /^[a-z0-9][a-z0-9-]{0,40}$/;

export function makeRun(guard, scratchBase, name) {
  if (typeof name !== "string" || !RUN_NAME.test(name)) throw new Error(`run name must be one plain component: ${JSON.stringify(name)}`);
  const run = guard.makeSandbox(path.join(scratchBase, name));
  if (fs.readdirSync(run).length !== 0) throw new Error(`run directory is not new: ${run}`);
  for (const dir of ["cwd-a", "cwd-b"]) fs.mkdirSync(guard.assertInside(run, dir));
  return run;
}

export function writeOutput(guard, file, data) {
  fs.writeFileSync(guard.assertOutput(file), data);
}

export function transfer(guard, source, destination) {
  writeOutput(guard, destination, fs.readFileSync(source));
}
