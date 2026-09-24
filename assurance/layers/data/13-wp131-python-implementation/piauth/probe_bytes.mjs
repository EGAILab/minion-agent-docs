import { getExifOrientation } from "./exif_probe.ts";
import { detectSupportedImageMimeType } from "./mime.ts";
let raw = ""; process.stdin.on("data", (d) => (raw += d)); process.stdin.on("end", () => {
  const out = JSON.parse(raw).map((h) => {
    const b = new Uint8Array(Buffer.from(h, "hex"));
    return { hex: h, orientation: getExifOrientation(b), mime: detectSupportedImageMimeType(b) };
  });
  process.stdout.write(JSON.stringify(out));
});
