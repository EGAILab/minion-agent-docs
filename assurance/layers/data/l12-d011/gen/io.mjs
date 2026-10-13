// L12-D011 generation: EVERY computed filesystem mutation of the launcher, generator and merge happens here, each
// immediately after its reviewed fs-guard proof (CE-L12D007-01; L12D011-C001). The guard instance is passed in, so the
// containment controls (containment-controls.mjs) run these exact statements with mutations intercepted.
//   makeRun:     REFERENT proof of the run directory's whole ancestry (makeSandbox) BEFORE its mkdir, then REFERENT
//                proof of `cwd` before its mkdir. A run name is one plain component; anything else refuses first.
//   writeOutput: REFERENT proof of the final output entry (assertOutput) immediately before the write.
// Nothing is ever deleted.
import fs from "node:fs";
import path from "node:path";

const RUN_NAME = /^[a-z0-9][a-z0-9-]{0,40}$/;

export function makeRun(guard, scratchBase, name) {
  if (typeof name !== "string" || !RUN_NAME.test(name)) throw new Error(`run name must be one plain component: ${JSON.stringify(name)}`);
  const run = guard.makeSandbox(path.join(scratchBase, name));
  if (fs.readdirSync(run).length !== 0) throw new Error(`run directory is not new: ${run}`);
  fs.mkdirSync(guard.assertInside(run, "cwd"));
  return run;
}

export function writeOutput(guard, file, data) {
  fs.writeFileSync(guard.assertOutput(file), data);
}

// The container's ONE host-bound write (L12D011-C001, review 2): the generator's private-tmpfs output is transferred to
// the host-bound output through writeOutput, so the FINAL destination entry is proven (assertOutput, with the guard's
// FS_GUARD_OUTPUT naming the bind root) immediately before the write. Reading the private source needs no proof.
export function transfer(guard, source, destination) {
  writeOutput(guard, destination, fs.readFileSync(source));
}
