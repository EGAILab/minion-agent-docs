// Preload for the CE-L12D007-01 synthetic controls (node --import ./synthetic.mjs ...).
// Under the virtual root SYN_ROOT, which lies inside the project and is never created on disk,
// lstat / readlink / realpath / readdir are answered from an in-memory tree that the control installs
// with globalThis.__syn.set(tree). EVERY filesystem mutation and every execFileSync is RECORDED and
// never reaches the OS: inside SYN_ROOT the tree is updated; anywhere else the call throws.
// Paths outside SYN_ROOT are inspected for real (read-only).
import fs from "node:fs";
import path from "node:path";
import cp from "node:child_process";
import { syncBuiltinESMExports } from "node:module";

const ROOT = path.resolve(process.env.SYN_ROOT);
const fold = (p) => (process.platform === "win32" ? p.toLowerCase() : p);
const project = (s) => String(s).toWellFormed(); // section 14.1, as Node's binding does it
let tree = new Map(); // rel (projected, "/"-joined) -> { type: "dir"|"file"|"link", text?, err?, readlinkErr? }
const calls = [];
globalThis.__syn = {
  root: ROOT,
  set(spec, limits = {}) { tree = new Map(Object.entries(spec).map(([k, v]) => [project(k), v])); calls.length = 0; globalThis.__syn.limits = limits; },
  calls,
};
const rel = (p) => {
  const abs = path.resolve(project(p));
  const r = path.relative(fold(ROOT), fold(abs));
  if (r === "") return "";
  if (r.startsWith("..") || path.isAbsolute(r)) return null;
  return path.relative(ROOT, abs).split(path.sep).join("/");
};
const err = (code, p) => Object.assign(new Error(`${code}: synthetic, '${p}'`), { code, path: p });
function entry(p) {
  const r = rel(p);
  if (r === null) return undefined; // not virtual
  if (r === "") return { type: "dir" };
  const parts = r.split("/");
  for (let i = 1; i < parts.length; i++) {
    const pre = tree.get(parts.slice(0, i).join("/"));
    if (pre === undefined) throw err("ENOENT", p);
    if (pre.err) throw err(pre.err, p);
    if (pre.type === "file") throw err("ENOTDIR", p);
    if (pre.type === "link") throw err("ENOENT", p); // a real lstat would never be asked this
  }
  const e = tree.get(r);
  if (e === undefined) throw err("ENOENT", p);
  if (e.err) throw err(e.err, p);
  return e;
}
const statOf = (e) => ({ isSymbolicLink: () => e.type === "link", isDirectory: () => e.type === "dir", isFile: () => e.type === "file", mode: 0o700 });

const real = { lstatSync: fs.lstatSync, readlinkSync: fs.readlinkSync, realpathNative: fs.realpathSync.native, readdirSync: fs.readdirSync };
fs.lstatSync = (p, ...a) => { const e = entry(p); return e === undefined ? real.lstatSync(p, ...a) : statOf(e); };
fs.statSync = (p, ...a) => { const e = entry(p); return e === undefined ? real.lstatSync(p, ...a) : statOf(e); };
fs.readlinkSync = (p, ...a) => {
  const e = entry(p);
  if (e === undefined) return real.readlinkSync(p, ...a);
  if (e.type !== "link") throw err("EINVAL", p);
  if (e.readlinkErr) throw err(e.readlinkErr, p);
  return e.text;
};
const realpathNative = (p, ...a) => (rel(p) === null ? real.realpathNative(p, ...a) : path.resolve(project(p)));
fs.realpathSync.native = realpathNative;
fs.readdirSync = (p, ...a) => {
  const r = rel(p);
  if (r === null) return real.readdirSync(p, ...a);
  calls.push({ op: "readdir", paths: [path.resolve(project(p))] });
  const e = entry(p);
  if (e.type !== "dir") throw err("ENOTDIR", p);
  const prefix = r === "" ? "" : r + "/";
  return [...tree.keys()].filter((k) => k.startsWith(prefix) && !k.slice(prefix.length).includes("/") && k !== r).map((k) => k.slice(prefix.length));
};
function mutation(name, indexes, effect) {
  return (...args) => {
    const targets = indexes.map((i) => (args[i] === undefined ? undefined : path.resolve(project(args[i]))));
    calls.push({ op: name, paths: targets });
    if (targets.some((t) => t !== undefined && rel(t) === null)) throw err("EOUTSIDE_SYNTHETIC", targets.join(" "));
    effect?.(targets, args);
  };
}
const drop = ([t]) => tree.delete(rel(t));
Object.assign(fs, {
  writeFileSync: mutation("writeFileSync", [0]), appendFileSync: mutation("appendFileSync", [0]),
  mkdirSync: mutation("mkdirSync", [0], ([t]) => tree.set(rel(t), { type: "dir" })), chmodSync: mutation("chmodSync", [0]),
  unlinkSync: mutation("unlinkSync", [0], drop), rmdirSync: mutation("rmdirSync", [0], drop), rmSync: mutation("rmSync", [0], drop),
  renameSync: mutation("renameSync", [0, 1]), symlinkSync: mutation("symlinkSync", [1]), truncateSync: mutation("truncateSync", [0]),
  openSync: mutation("openSync", [0]), copyFileSync: mutation("copyFileSync", [1]),
});
// `getconf NAME|PATH_MAX <dir>` answers come from globalThis.__syn.limits ("error" throws; any other
// value is printed as is, e.g. -1, "undefined", "abc"); every other program is recorded and returns "".
cp.execFileSync = (file, args = []) => {
  calls.push({ op: `exec:${file}`, args: args.map(String) });
  if (file === "getconf") {
    const v = globalThis.__syn.limits?.[args[0]];
    if (v === undefined || v === "error") throw err("EGETCONF", args.join(" "));
    return `${v}\n`;
  }
  return "";
};
syncBuiltinESMExports();
