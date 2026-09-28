// #74 item E: pinned Pi's read.ts text branch (read_text.mjs, verbatim apart from I/O) over each listed file.
// Pinned Pi only takes this branch when detectSupportedImageMimeType returns null; that is asserted here.
import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { detectSupportedImageMimeType } from "./pi_utils/mime.ts";
import { readText } from "./read_text.mjs";

const [corpusDir, outPath, ...files] = process.argv.slice(2);
const results = [];
for (const file of files) {
  const buffer = readFileSync(`${corpusDir}/${file}`);
  const sniffed = detectSupportedImageMimeType(new Uint8Array(buffer));
  if (sniffed !== null) throw new Error(`${file}: sniffed ${sniffed}, not the text branch`);
  const { text, details } = readText(buffer, file, undefined, undefined);
  results.push({ file, input_sha256: createHash("sha256").update(buffer).digest("hex"), sniffed_mime: sniffed, text,
                 details: details ?? null });
}
writeFileSync(outPath, JSON.stringify({ engine: "node+pi-read-text-branch", node: process.versions.node,
  v8: process.versions.v8, results }, null, 1));
console.log(`text authority: ${results.length} files`);
