// WP-13.3 contract review 1 (CON-R002, CON-R003): the pinned OutputAccumulator rolling-tail trim, and Node's
// timer scheduling normalization.  node --experimental-strip-types --expose-internals boundary_probe.mjs <pi checkout> <out.json>
import { createHash } from "node:crypto";
import { writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
const [piDir, outPath] = process.argv.slice(2);
const { OutputAccumulator } = await import(pathToFileURL(`${piDir}/packages/coding-agent/src/core/tools/output-accumulator.ts`).href);
const sha = (s) => createHash("sha256").update(s, "utf8").digest("hex");
const show = (s) => (s.length <= 16 ? s : `${s.slice(0, 6)}...${s.slice(-6)}`);

// Each case is a list of chunks (strings, UTF-8 encoded).  The summary keeps the observables, not the 50 KB text.
const rolling = async (chunks) => {
  const a = new OutputAccumulator({ tempFilePrefix: "wp133-boundary" });
  for (const c of chunks) a.append(Buffer.from(c, "utf8"));
  a.finish();
  const s = a.snapshot();
  await a.closeTempFile();
  const { content, ...truncation } = s.truncation;
  return { content: { length: s.content.length, utf8Bytes: Buffer.byteLength(s.content), edges: show(s.content), sha256: sha(s.content) },
    truncationContentEqualsContent: content === s.content, truncation, lastLineBytes: a.getLastLineBytes() };
};
const rep = (ch, n) => ch.repeat(n);
const cases = {
  // no newline anywhere in the retained tail: Pi keeps the whole retained tail (no partial-line drop)
  singleLineOneChunk: [rep("a", 250000)],
  singleLineManyChunks: Array(5).fill(rep("a", 50000)),
  singleLineMultibyte: [rep("€", 70000)],
  // the trim cuts mid-line and a newline follows: the partial first line is dropped
  cutMidLineNewlineLater: [rep("a", 150000) + "\n" + rep("b", 60000)],
  // the trim lands right after a newline: the tail starts at a line boundary, nothing is dropped
  cutAfterNewline: [rep("a", 110000) + "\n" + rep("b", 102400)],
  // a later chunk carries the newline after a mid-line cut (state persists across appends)
  cutMidLineNewlineInLaterChunk: [rep("a", 250000), "\n" + rep("b", 1000)],
  // at the trigger, no trim (204800 is not above 4 * 51200)
  atTriggerNoTrim: [rep("a", 204800)],
};
const out = { node: process.version, rolling: {}, timers: [] };
for (const [name, chunks] of Object.entries(cases)) out.rolling[name] = await rolling(chunks);

// The timer: setTimeout(fn, timeout * 1000).  Timeout clamps non-[1, TIMEOUT_MAX] to 1; insert() keys the timer
// list by MathTrunc(msecs), the duration actually scheduled.  Read both from Node's own internals.
const { timerListMap } = createRequire(import.meta.url)("internal/timers");
for (const seconds of [0.0005, 0.000999, 0.001, 0.0019, 0.0025, 0.25, 1.5, 2147483.647]) {
  const ms = seconds * 1000;
  const before = new Set(Object.keys(timerListMap));
  const t = setTimeout(() => {}, ms);
  const added = Object.keys(timerListMap).filter((k) => !before.has(k));
  const scheduled = added.length === 1 ? Number(added[0]) : t._idleTimeout === Math.trunc(t._idleTimeout) && timerListMap[t._idleTimeout] ? t._idleTimeout : null;
  out.timers.push({ seconds, binary64Ms: ms, idleTimeout: t._idleTimeout, scheduledMs: scheduled, rule: Math.max(1, Math.trunc(ms)) });
  clearTimeout(t);
}
writeFileSync(outPath, JSON.stringify(out, null, 1) + "\n");
console.log(JSON.stringify(out, null, 1));
