import { truncateHead } from "./truncate.ts";
let raw = ""; process.stdin.on("data", (d) => (raw += d)); process.stdin.on("end", () => {
  process.stdout.write(JSON.stringify(truncateHead(JSON.parse(raw).content, { maxLines: Number.MAX_SAFE_INTEGER })));
});
