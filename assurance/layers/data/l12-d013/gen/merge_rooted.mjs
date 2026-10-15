// L12-D013: append the rooted Windows and Linux partials to the existing canonical path-resolution document (stdout
// only; the launcher writes it). The existing 80 L12-D012 cases are carried over unchanged and in order.
//   node merge_rooted.mjs <existing path-resolution.json> <win32 partial> <linux partial>
import { readFileSync } from "node:fs";
import { isDeepStrictEqual } from "node:util";

const [basePath, winPath, linPath] = process.argv.slice(2);
const base = JSON.parse(readFileSync(basePath, "utf8"));
const win = JSON.parse(readFileSync(winPath, "utf8"));
const lin = JSON.parse(readFileSync(linPath, "utf8"));
const PI = "b7bb00b936dbe21b8e160b3e89efdec361846699";
for (const [p, want] of [[win, "win32"], [lin, "linux"]]) {
  if (p.platform !== want || p.node !== "v22.15.1" || p.pi !== PI) throw new Error(`bad partial: ${p.platform} ${p.node} ${p.pi}`);
}
const old = base.path_resolution.cases;
if (old.length !== 80 || base.pi_revision !== PI) throw new Error("the base must be the merged 80-case L12-D012 corpus");
const count = (cs, prefix) => cs.filter((c) => c.id.startsWith(prefix)).length;
if (count(win.cases, "baseline/rooted-") !== 4 || count(win.cases, "host/rooted/") !== 9
  || count(win.cases, "host/rooted-extended/") !== 2 || win.cases.length !== 15) throw new Error("win32 partial shape");
if (lin.cases.length !== 4 || lin.cases.some((c) => c.host !== null)) throw new Error("linux partial shape");
const added = [...win.cases.map((c) => ({ ...c, id: `win32/${c.id}` })), ...lin.cases.map((c) => ({ ...c, id: `linux/${c.id}` }))];
const cases = [...old, ...added];
if (new Set(cases.map((c) => c.id)).size !== cases.length) throw new Error("duplicate case id");
const doc = {
  ...base,
  authority: base.authority.replace(/\(L12-D012, minion-agent#229\)$/, "(L12-D012, minion-agent#229); rooted "
    + "drive-less and UNC-root cases by assurance/layers/data/l12-d013/gen (L12-D013, minion-agent#235)"),
  notes: base.notes + " L12-D013 (record 12-l12-d013-rooted.md): host cases may name cwd_form; 'extended' runs the "
    + "child with cwd \\\\?\\ + the ordinary sandbox path, and every template part is filled from the ORDINARY "
    + "sandbox path.",
  path_resolution: { cases },
};
if (!doc.authority.includes("L12-D013")) throw new Error("authority suffix not found");
if (!isDeepStrictEqual(doc.path_resolution.cases.slice(0, 80), old)) throw new Error("existing cases changed");
console.log(JSON.stringify(doc, null, 1));
