// Merge the per-platform generator partials into conformance/agent/spawn-nul/spawn-nul.json, applying the CONTRACT's
// selection (spec/execution.md section 21.1, 21.3, 21.4) to Node's literal per-input diagnostics:
//   pre-abort -> file -> args in order -> effective cwd -> effective environment entries in the platform order:
//     win32: every retained entry, ascending UTF-16 code units of the name (Owner, #224 6137796390);
//     linux: integer-index names ascending, then overlay-owned names in overlay insertion order, then baseline-only
//            names in ascending UTF-16 code units (Owner F2, #224 6141307443).
// Node's own whole-call outcome is recorded as `node_contrast` only where it differs, exactly as observed (an
// async error is an async error with its code -- never "spawned"; L12D011-C002). Strings are {"utf16": [...]}.
//   node merge_spawn_nul.mjs <win32 partial> <linux partial> <out.json>
//   node merge_spawn_nul.mjs --self-test          (controls: fabricated or unexpected raw outcomes, wrong orders)
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { CASES, TOOL_CASES, pick } from "./spawn_nul_cases.mjs";
import { writeOutput } from "./io.mjs";

const N = "\u0000";
const S = (s) => ({ utf16: Array.from({ length: s.length }, (_, i) => s.charCodeAt(i)) });
const units = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));
const same = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);
const isIndex = (k) => /^(0|[1-9][0-9]*)$/.test(k) && Number(k) <= 4294967294;
const utf16Less = (a, b) => (a < b ? -1 : a > b ? 1 : 0); // JavaScript string comparison IS UTF-16 code-unit order

export function envOrder(c, platform) {
  const entries = new Map();
  if (c.inherit_env && c.baseline) for (const [k] of c.baseline) entries.set(k, "baseline");
  const overlay = c.env ? c.env.map(([k]) => k) : [];
  for (const k of overlay) entries.set(k, "overlay");
  const names = [...entries.keys()];
  if (platform === "win32") return names.sort(utf16Less);
  const index = names.filter(isIndex).sort((a, b) => Number(a) - Number(b));
  const ownedOverlay = [...new Set(overlay)].filter((k) => !isIndex(k));
  const baselineOnly = names.filter((k) => !isIndex(k) && entries.get(k) === "baseline").sort(utf16Less);
  return [...index, ...ownedOverlay, ...baselineOnly];
}

function checkRaw(r, id, platform) {
  if (!r || typeof r !== "object") throw new Error(`${platform} ${id}: missing raw observation`);
  if (r.outcome === "nul_diagnostic" && Array.isArray(r.message) && r.message.length > 0) return;
  if (r.outcome === "async_error" && typeof r.code === "string" && r.code.length > 0) return;
  throw new Error(`${platform} ${id}: unexpected raw outcome ${JSON.stringify(r).slice(0, 120)}`);
}

export function expectFor(c, platform, rec) {
  if (c.pre_aborted) return { code: "aborted" };
  let selected = null;
  if (rec.file) selected = rec.file;
  if (!selected) for (let j = 1; j < c.argv.length; j++) if (rec.args[j]) { selected = rec.args[j]; break; }
  if (!selected && rec.cwd) selected = rec.cwd;
  if (!Array.isArray(rec.env)) throw new Error(`${platform} ${c.id}: env diagnostics must be an ordered pair list`);
  const envDiag = new Map(rec.env);
  if (!selected) for (const k of envOrder(c, platform)) if (envDiag.has(k)) { selected = envDiag.get(k); break; }
  if (selected !== null && !(Array.isArray(selected) && selected.length > 0 && selected.every(Number.isInteger))) {
    throw new Error(`${platform} ${c.id}: malformed selected diagnostic ${JSON.stringify(selected).slice(0, 80)}`);
  }
  checkRaw(rec.node_whole_call, c.id, platform);
  const node = rec.node_whole_call;
  if (!selected) {
    if (!c.control) throw new Error(`${platform} ${c.id}: no diagnostic for a non-control case`);
    if (node.outcome !== "async_error") throw new Error(`${platform} ${c.id}: control, but Node rejected the call`);
    return { code: "spawn_error", message: "os" };
  }
  if (c.control) throw new Error(`${platform} ${c.id}: control case produced a diagnostic`);
  const out = { code: "spawn_error", message: { utf16: selected } };
  if (node.outcome === "async_error") {
    out.node_contrast = `node passed NUL validation and failed asynchronously with ${node.code}`;
  } else if (!same(node.message, selected)) {
    out.node_contrast = "node selected a different input: " + String.fromCharCode(...node.message);
  }
  return out;
}

function build(parts) {
  for (const [p, d] of Object.entries(parts)) if (d.platform !== p || d.node !== "22.15.1") throw new Error(`bad partial ${p}`);
  const both = (fn) => ({ win32: fn("win32"), linux: fn("linux") });
  const cases = CASES.map((c) => ({
    id: c.id,
    argv: c.argv.map((v) => (typeof v === "string" ? S(v) : { linux: S(v.linux), win32: S(v.win32) })),
    cwd: c.cwd === null ? null : typeof c.cwd === "string" ? S(c.cwd) : { linux: S(c.cwd.linux), win32: S(c.cwd.win32) },
    provider_cwd: { linux: S(c.provider_cwd.linux), win32: S(c.provider_cwd.win32) },
    baseline: c.baseline === null ? null : c.baseline.map(([k, v]) => [S(k), S(v)]),
    env: c.env === null ? null : c.env.map(([k, v]) => [S(k), S(v)]),
    inherit_env: c.inherit_env,
    pre_aborted: c.pre_aborted,
    expect: both((p) => expectFor(c, p, parts[p].cases[c.id] ?? (() => { throw new Error(`missing ${p} ${c.id}`); })())),
  }));
  const tools = TOOL_CASES.map((t) => {
    const args = both((p) => Object.fromEntries(Object.entries(t.arguments[p] ?? t.arguments.any).map(([k, v]) => [k, S(v)])));
    const expect = both((p) => {
      if (t.pre_aborted) return { is_error: true, text: S("Operation aborted") };
      const r = parts[p].tools[t.id];
      if (!r || r.outcome !== "error" || r.code !== "ERR_INVALID_ARG_VALUE") throw new Error(`tool ${t.id} ${p}: ${JSON.stringify(r).slice(0, 160)}`);
      return { is_error: true, text: { utf16: r.text } };
    });
    return { id: t.id, tool: t.tool, arguments: args, pre_aborted: !!t.pre_aborted, expect };
  });
  return {
    name: "spawn-nul",
    family: "agent",
    authority: "Node v22.15.1 child_process.spawn normalizeSpawnArguments / ERR_INVALID_ARG_VALUE / util.inspect (each NUL input's literal diagnostic, in isolation), pinned Pi b7bb00b9 agent/src/harness/env/nodejs.ts resolvePath (effective cwd) and coding-agent core/tools/find.ts, grep.ts, bash.ts execute (sliced unmodified); selection per spec/execution.md section 21; Windows 11 and Linux (python:3.13 image, Node 22.15.1 linux-x64)",
    pi_revision: "b7bb00b936dbe21b8e160b3e89efdec361846699",
    requirements: ["EXEC-013", "EXEC-005", "TOOL-034", "TOOL-036", "TOOL-037"],
    witnesses: ["spawn_nul_node_diagnostic"],
    platforms: ["linux", "win32"],
    notes: "L12-D011 (minion-agent#224; provenance #195). A NUL in the executable, an argument, the effective (resolved or provider-default) cwd or an effective environment entry fails ctx.subprocess.spawn with spawn_error and pinned Node's literal ERR_INVALID_ARG_VALUE message for the input selected by spec section 21, before any process starts; find, grep and bash surface it unchanged. `message: \"os\"` marks a control whose text is the OS's own (unchanged). `node_contrast` records Node's own whole-call outcome where it differs (Owner decisions: Windows retained entries, POSIX overlay-first order, effective cwd). Pre-aborted tool expectations are the certified pipeline result (builtin-bash-abort-before-spawn). GENERATED by assurance/layers/data/l12-d011/gen; do not edit.",
    spawn_nul: { cases, tools },
  };
}

function selfTest() {
  let failed = 0;
  const check = (ok, text) => { failed += !ok; console.log(`${ok ? "PASS" : "FAIL"} ${text}`); };
  const msg = (s) => units(s);
  const base = { id: "t", argv: ["x", "ok"], cwd: null, provider_cwd: { linux: "/x", win32: "C:\\x" }, baseline: null,
    env: null, inherit_env: false, pre_aborted: false, control: false };
  const rec = (extra) => ({ effective_cwd: [], file: null, args: {}, cwd: null, env: [], ...extra });
  const throws = (fn) => { try { fn(); return false; } catch { return true; } };
  // C002: raw outcomes are validated; a fabricated "started"/"spawned" outcome or an unexpected one is rejected.
  check(throws(() => expectFor(base, "win32", rec({ args: { 1: msg("m") }, node_whole_call: { outcome: "spawned" } }))),
    "C002: a fabricated 'spawned' whole-call outcome is rejected");
  check(throws(() => expectFor(base, "win32", rec({ args: { 1: msg("m") }, node_whole_call: { outcome: "started", pid: 1 } }))),
    "C002: a 'started' outcome is rejected");
  check(throws(() => expectFor(base, "win32", rec({ args: { 1: msg("m") }, node_whole_call: { outcome: "async_error" } }))),
    "C002: an async error without a code is rejected");
  const enoent = expectFor(base, "win32", rec({ args: { 1: msg("m") }, node_whole_call: { outcome: "async_error", code: "ENOENT" } }));
  check(enoent.node_contrast === "node passed NUL validation and failed asynchronously with ENOENT" && !/spawned|started/.test(enoent.node_contrast),
    "C002: an async ENOENT is attributed as an async ENOENT, never as a started process");
  // A name such as __proto__ is data: the diagnostics are a pair list, and a malformed selection is rejected.
  const proto = { ...base, env: [["__proto__", "p\u0000"]] };
  const pr = expectFor(proto, "linux", rec({ env: [["__proto__", msg("P")]], node_whole_call: { outcome: "nul_diagnostic", message: msg("P") } }));
  check(pr.message.utf16.length === 1 && pr.message.utf16[0] === 80, "__proto__ is selected as an ordinary own name");
  check(throws(() => expectFor(proto, "linux", rec({ env: { __proto__: msg("P") }, node_whole_call: { outcome: "nul_diagnostic", message: msg("P") } }))),
    "control: a plain-object env record (prototype hazard) is rejected");
  check(throws(() => expectFor(proto, "linux", rec({ env: [["__proto__", {}]], node_whole_call: { outcome: "nul_diagnostic", message: msg("P") } }))),
    "control: a malformed selected diagnostic is rejected");
  // F2 order and the Windows order.
  const o = (env, baseline, inherit = baseline !== null) => ({ ...base, env, baseline, inherit_env: inherit });
  check(envOrder(o([["Z"], ["A"]], null, false), "linux").join() === "Z,A", "F2: overlay insertion order on linux");
  check(envOrder(o([["Z"], ["A"]], null, false), "win32").join() === "A,Z", "win32: UTF-16 order");
  check(envOrder(o([["Z"], ["A"]], [["A"], ["Z"]]), "linux").join() === "Z,A" && envOrder(o([["Z"], ["A"]], [["Z"], ["A"]]), "linux").join() === "Z,A",
    "F2: baseline presentation order never changes the overlay-owned order");
  check(envOrder(o(null, [["Z"], ["A"]]), "linux").join() === "A,Z", "F2: baseline-only names in UTF-16 order");
  check(envOrder(o([["Z"], ["01"], ["4294967295"], ["10"], ["2"]], null, false), "linux").join() === "2,10,Z,01,4294967295",
    "F2: integer-index names first; 01 and 4294967295 are not indices");
  check(envOrder(o(null, [["\uff5e"], ["\u{10000}"]]), "linux")[0] === "\u{10000}", "F2: UTF-16, not UTF-8, order");
  // Negative controls: realistic wrong orders are distinguishable on the committed cases.
  const baselineFirst = (c) => [...(c.baseline ?? []).map(([k]) => k), ...(c.env ?? []).map(([k]) => k)];
  const sortAll = (c) => envOrder(c, "win32");
  const ZA = o([["Z"], ["A"]], [["A"], ["Z"]]);
  check(baselineFirst(ZA)[0] !== envOrder(ZA, "linux")[0], "control: baseline-first ordering is killed (A vs Z)");
  check(sortAll(o([["Z"], ["A"]], null, false))[0] !== envOrder(o([["Z"], ["A"]], null, false), "linux")[0],
    "control: sort-all ordering on linux is killed");
  const naiveIndex = (k) => /^[0-9]+$/.test(k);
  check(naiveIndex("01") !== isIndex("01") && naiveIndex("4294967295") !== isIndex("4294967295"),
    "control: naive integer detection is killed by 01 and 4294967295");
  console.log(failed ? `MERGE SELF-TEST FAILED (${failed})` : "MERGE SELF-TEST PASSED");
  process.exitCode = failed ? 1 : 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (process.argv[2] === "--self-test") selfTest();
  else {
    const here = path.dirname(fileURLToPath(import.meta.url));
    const guard = await import(pathToFileURL(path.join(here, "../../l12-d007/fs-guard/fs-guard.mjs")).href);
    const [winPath, linuxPath, outPath] = process.argv.slice(2);
    const parts = { win32: JSON.parse(readFileSync(winPath, "utf8")), linux: JSON.parse(readFileSync(linuxPath, "utf8")) };
    const doc = build(parts);
    writeOutput(guard, outPath, JSON.stringify(doc, null, 1) + "\n");
    console.log(`spawn-nul.json: ${doc.spawn_nul.cases.length} spawn cases, ${doc.spawn_nul.tools.length} tool cases`);
  }
}
