// L12-D012 C001 characterization: how Node v22.15.1 win32.resolve reads the per-drive cwd entry. Prints the
// relevant source of the RUNNING Node's path.win32.resolve, then evaluates key spellings in this process only.
import path from "node:path";

const src = path.win32.resolve.toString();
const at = src.indexOf("process.env");
console.log("source:", src.slice(Math.max(0, at - 200), at + 420).replace(/\s+/g, " "));
const r = () => [path.win32.resolve("C:\\x", "a::/b"), path.win32.resolve("C:\\x", "x:y:z/w")];
console.log("inherited =A:/=a:/=X:/=x: present:", ["=A:", "=a:", "=X:", "=x:"].map((k) => k in process.env));
console.log("baseline", JSON.stringify(r()));
for (const key of ["=A:", "=a:"]) {
  process.env[key] = "A:\\deep";
  console.log(`set ${key}: env lookup =a: ->`, JSON.stringify(process.env["=a:"]), JSON.stringify(r()));
  delete process.env[key];
}
