// L12-D012: Node v22.15.1 path.win32.resolve observations for the Python port's unit witnesses (root parsing, UNC,
// normalization incl. '..' above a non-absolute root). Pure computation; stdout only.
//   rows with "base": port(paths=[input], process_cwd=base) must equal path.win32.resolve(base, input) -- the base
//     is absolute with a device, so Node consults neither the per-drive entry nor the process cwd;
//   rows with "entry": a drive-relative input on drive A: in a CHILD whose environment block carries exactly
//     =A:=<entry> (and whose own cwd is not on A:), so the selected base is that entry.
import { spawnSync } from "node:child_process";
import path from "node:path";

if (process.argv[2] === "child") {
  console.log(JSON.stringify(path.win32.resolve("C:\\x", process.argv[3])));
} else {
  const BASES = ["E:\\w\\v", "\\\\srv\\share\\d"];
  const INPUTS = ["a/../b", "..\\..\\..\\up", ".\\.\\x\\.", "x//y\\\\z", "x\\..", "...\\x", "..x\\y", "x\\..\\..\\y",
    "\\rooted\\x", "/", "\\", "a", "\\\\srv\\share", "\\\\srv", "\\\\srv\\", "\\\\srv\\share\\x\\..\\..", "//a/b/c",
    "\\\\\\x", "C:", "e:", "E:rel\\..\\..", "e:\\abs\\..", "z:\\q", "", "x/./y/../z/"];
  const rows = [];
  // A drive-relative input on another device than the base makes Node consult host state: excluded here
  // (the port tests call the port with host lookups that FAIL if consulted).
  const dev = (p) => (/^[A-Za-z]:/.test(p) ? p.slice(0, 2).toLowerCase() : /^[\\/]{2}[^\\/]+[\\/]+[^\\/]+/.test(p) ? "unc" : "");
  const consults = (b, i) => /^[A-Za-z]:(?![\\/])/.test(i) && dev(i) !== dev(b);
  for (const base of BASES) for (const input of INPUTS) {
    if (!consults(base, input)) rows.push({ base, input, out: path.win32.resolve(base, input) });
  }
  const base = Object.fromEntries(Object.entries(process.env).filter(([k]) => !k.startsWith("=")));
  for (const [entry, input] of [["relative", "a:..\\..\\leaf"], ["relative\\x", "a:..\\..\\..\\leaf"], ["..\\up", "a:leaf\\."],
    ["\\\\srv\\share", "a:x"], ["r", "a:"], ["A:", "a:..\\leaf"], ["A:rel\\..\\..", "a:leaf"]]) {
    const r = spawnSync(process.execPath, [process.argv[1], "child", input], { env: { ...base, "=A:": entry }, encoding: "utf8" });
    if (r.status !== 0) throw new Error(r.stderr);
    rows.push({ entry, input, out: JSON.parse(r.stdout) });
  }
  // normalizeString(p, allowAboveRoot = true) directly: for a relative, device-free p that does not end in a separator
  // and normalizes to a non-empty string, path.win32.normalize(p) returns exactly that.
  for (const input of ["a\\b\\..\\c", "..\\x\\..\\..\\y", "x\\.", "a/b", "..", "a\\..\\..", "...", "x/.\\y"]) {
    rows.push({ normalize: input, out: path.win32.normalize(input) });
  }
  if (process.cwd()[0].toUpperCase() === "A" || process.cwd()[0].toUpperCase() === "C") throw new Error("cwd must not be on A: or C:");
  console.log(JSON.stringify({ node: process.version, platform: process.platform, rows }, null, 1));
}
