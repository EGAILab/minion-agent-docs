// CE-L12D012-01: freeze the three Node-observed partitions into the binding's test fixture. Reads the committed
// characterization outputs only (no process, no Node resolution); writes the fixture JSON to stdout.
//   node build_fixture.mjs > <candidate>/minion-agent-python/tests/execution/data/node_selected_value.json
import { readFileSync } from "node:fs";

const read = (name) => JSON.parse(readFileSync(new URL(`./${name}`, import.meta.url), "utf8"));
const entry = read("unit-partition-win32.json");
const cwd = read("cwd-partition-win32.json");
const logical = read("logical-partition-win32.json");
if (!logical.all_predictions_confirmed) throw new Error("the logical oracle did not confirm every prediction");

const last = (units) => {
  const s = String.fromCharCode(...units);
  const name = s.slice(s.lastIndexOf("\\") + 1);
  return Array.from({ length: name.length }, (_, i) => name.charCodeAt(i));
};
const cwdNames = [];
for (const r of cwd.rows) {
  if (cwdNames.some((n) => n.label === r.cwd_label)) continue;
  cwdNames.push({ label: r.cwd_label, name: last(r.binding_cwd), node_view: last(r.node_cwd) });
}
const out = {
  source: "minion-agent-docs assurance/layers/data/l12-d012/ce01 (CE-L12D012-01): Node v22.15.1, pinned Pi b7bb00b9",
  entry_rows: entry.rows.map((r) => ({ label: r.label, entry: r.entry, node_entry: r.node_entry, node: r.node })),
  cwd_names: cwdNames,
  logical_rows: logical.rows.map((r) => ({ label: r.label, entry: r.entry, node_entry: r.node_entry,
    logical: r.logical, node: r.node })),
};
console.log(JSON.stringify(out, null, 1));
