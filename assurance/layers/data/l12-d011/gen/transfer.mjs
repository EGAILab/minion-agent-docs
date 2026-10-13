// Container-only entry point for io.transfer (L12D011-C001): copies the generator's private output to the host-bound
// /out through the reviewed fs-guard. Run with FS_GUARD_ROOT=/tmp/guard-root and FS_GUARD_OUTPUT=/out; the destination
// must be exactly /out/linux-partial.json and the source exactly the generator's private output.
//   node transfer.mjs /tmp/guard-root/w/linux-partial.json /out/linux-partial.json
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { transfer } from "./io.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const guard = await import(pathToFileURL(path.join(here, "../../l12-d007/fs-guard/fs-guard.mjs")).href);
const [source, destination] = process.argv.slice(2);
if (source !== "/tmp/guard-root/w/linux-partial.json" || destination !== "/out/linux-partial.json") {
  throw new Error(`transfer: unexpected source/destination ${JSON.stringify([source, destination])}`);
}
if (process.env.FS_GUARD_OUTPUT !== "/out") throw new Error("transfer: FS_GUARD_OUTPUT must be /out");
transfer(guard, source, destination);
console.log("TRANSFER DONE");
