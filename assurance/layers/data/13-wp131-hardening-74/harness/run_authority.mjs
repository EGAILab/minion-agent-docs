// Authority run: pinned Pi source (b7bb00b9) + @silvia-odwyer/photon-node 0.3.4, executed as-is.
import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { detectSupportedImageMimeType } from "./pi_utils/mime.ts";
import { processImage } from "./pi_utils/image-process.ts";
import { resizeImageInProcess } from "./pi_utils/image-resize-core.ts";

const [corpusDir, casesPath, outPath] = process.argv.slice(2);
const manifest = JSON.parse(readFileSync(`${corpusDir}/manifest.json`, "utf8"));
const coreCases = JSON.parse(readFileSync(casesPath, "utf8"));
const sha = (buf) => createHash("sha256").update(buf).digest("hex");
const summarize = (b64) => {
  const d = Buffer.from(b64, "base64");
  return { data_sha256: sha(d), data_bytes: d.length, data_base64_len: b64.length };
};

const read_level = [];
for (const entry of manifest) {
  const bytes = new Uint8Array(readFileSync(`${corpusDir}/${entry.file}`));
  const mime = detectSupportedImageMimeType(bytes);
  const rec = { file: entry.file, input_sha256: sha(bytes), sniffed_mime: mime };
  if (mime) {
    const r = await processImage(bytes, mime);
    Object.assign(rec, r.ok ? { ok: true, mime: r.mimeType, hints: r.hints, ...summarize(r.data) } : { ok: false, message: r.message });
  }
  read_level.push(rec);
}

const core_level = [];
for (const c of coreCases) {
  const bytes = new Uint8Array(readFileSync(`${corpusDir}/${c.file}`));
  const r = await resizeImageInProcess(bytes, c.mime, c.options);
  core_level.push({ id: c.id, file: c.file, options: c.options, result: r === null ? null : {
    mime: r.mimeType, originalWidth: r.originalWidth, originalHeight: r.originalHeight,
    width: r.width, height: r.height, wasResized: r.wasResized, ...summarize(r.data) } });
}

writeFileSync(outPath, JSON.stringify({ engine: "node+pi+photon-node-0.3.4", node: process.versions.node,
  v8: process.versions.v8, read_level, core_level }, null, 1));
console.log(`authority: ${read_level.length} read-level, ${core_level.length} core-level`);
