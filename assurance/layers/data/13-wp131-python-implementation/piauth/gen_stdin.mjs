import { readText } from "./read_text.mjs";
let raw = ""; process.stdin.on("data", (d) => (raw += d)); process.stdin.on("end", () => {
  const out = JSON.parse(raw).map((c) => {
    const buf = Buffer.from(c.content_b64, "base64");
    try {
      // JSON null stands for an absent argument (Pi: undefined).
      const r = readText(buf, c.path, c.offset ?? undefined, c.limit ?? undefined);
      const t = r.details?.truncation;
      return { id: c.id, is_error: false, text: r.text, details: t ? { truncation: {
        truncated: t.truncated, truncated_by: t.truncatedBy, total_lines: t.totalLines,
        total_bytes: t.totalBytes, first_line_exceeds_limit: t.firstLineExceedsLimit } } : {} };
    } catch (e) { return { id: c.id, is_error: true, text: e.message }; }
  });
  process.stdout.write(JSON.stringify(out));
});
