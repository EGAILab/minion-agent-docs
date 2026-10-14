// L12-D012 C001: does an INHERITED per-drive cwd entry reach a child's win32.resolve? The parent launches this
// same script as a child (pure computation in the child; no files) with and without the entries in its
// environment block, then reports both. Run from inside the project root.
import { spawnSync } from "node:child_process";
import path from "node:path";

if (process.argv[2] === "child") {
  const keys = Object.keys(process.env).filter((k) => k.startsWith("="));
  console.log(JSON.stringify({ keys, a: path.win32.resolve("C:\\x", "a::/b"), x: path.win32.resolve("C:\\x", "x:y:z/w"),
    sameDriveAsCwd: path.win32.resolve("C:\\x", "e:leaf"), cwd: process.cwd() }));
} else {
  const base = Object.fromEntries(Object.entries(process.env).filter(([k]) => !k.startsWith("=")));
  for (const [label, extra] of [["without", {}], ["with =A: =X:", { "=A:": "A:\\deep", "=X:": "X:\\q" }]]) {
    const out = spawnSync(process.execPath, [process.argv[1], "child"], { env: { ...base, ...extra }, encoding: "utf8" });
    console.log(label, out.status, out.stdout.trim());
  }
}
