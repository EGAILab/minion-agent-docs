// L12-D001 (minion-agent#123) alias / collision and mutation-queue-key evidence (Owner decision FSP-Q001 sections
// 6-8): pinned Pi b7bb00b9's getMutationQueueKey (coding-agent core/tools/file-mutation-queue.ts, sliced unmodified)
// and Node's fs, for three spellings of one projected name. Strings are rendered as UTF-16 code units.
//   node alias_probe.mjs <pi checkout> <out.json>
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import * as fsp from "node:fs/promises";
import { tmpdir } from "node:os";
import * as path from "node:path";
import { stripTypeScriptTypes } from "node:module";

const [piDir, outPath] = process.argv.slice(2);
const q = readFileSync(`${piDir}/packages/coding-agent/src/core/tools/file-mutation-queue.ts`, "utf8");
const sliced = stripTypeScriptTypes(q.slice(q.indexOf("function isMissingPathError("), q.indexOf("/**\n * Serialize")));
const getMutationQueueKey = new Function("realpath", "resolve", sliced + "\nreturn getMutationQueueKey;")(
  fsp.realpath, path.resolve);

const U = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));
const HI = String.fromCharCode(0xd800), LO = String.fromCharCode(0xdc00), RC = String.fromCharCode(0xfffd);
const read = async (p) => { try { return { ok: true, content: await fsp.readFile(p, "utf8") }; }
                            catch (e) { return { ok: false, code: e.code }; } };
const rel = (base, p) => U(path.relative(base, p));

const out = { platform: process.platform, node: process.versions.node, positions: {} };
for (const position of ["file", "dir"]) {
  const root = mkdtempSync(path.join(tmpdir(), `alias-${position}-`));
  const spell = (c) => position === "file" ? path.join(root, `a${c}`) : path.join(root, `d${c}`, "f.txt");
  const A = spell(HI), B = spell(LO), C = spell(RC);
  const r = {};
  // Missing target: the queue key falls back to the RAW resolved path, so spellings differ.
  r.missing_keys = { A: rel(root, await getMutationQueueKey(A)), B: rel(root, await getMutationQueueKey(B)),
                     C: rel(root, await getMutationQueueKey(C)) };
  r.missing_keys_A_equals_B = (await getMutationQueueKey(A)) === (await getMutationQueueKey(B));
  // Write through alias A (parents created), then read through every spelling.
  await fsp.mkdir(path.dirname(A), { recursive: true });
  await fsp.writeFile(A, "first");
  r.read_after_write_A = { A: await read(A), B: await read(B), C: await read(C) };
  // Existing target: the key is realpath = the PROJECTED name, shared by all spellings.
  r.existing_keys = { A: rel(root, await getMutationQueueKey(A)), B: rel(root, await getMutationQueueKey(B)),
                      C: rel(root, await getMutationQueueKey(C)) };
  r.existing_keys_all_equal = new Set([await getMutationQueueKey(A), await getMutationQueueKey(B),
                                       await getMutationQueueKey(C)]).size === 1;
  // A second write through alias B overwrites the same file.
  await fsp.mkdir(path.dirname(B), { recursive: true });
  await fsp.writeFile(B, "second");
  r.read_after_write_B = { A: await read(A), B: await read(B), C: await read(C) };
  r.listing = (await fsp.readdir(root)).map(U);
  r.realpath = { A: rel(root, await fsp.realpath(A)), B: rel(root, await fsp.realpath(B)),
                 C: rel(root, await fsp.realpath(C)) };
  out.positions[position] = r;
}
writeFileSync(outPath, JSON.stringify(out, null, 1) + "\n");
console.log(`alias probe: ${process.platform} node ${process.versions.node}`);
