Node 22.15.1 helpers that produce expected values from PINNED Pi code (b7bb00b9), never from the
Minion implementation. Before running, copy these unmodified from the pinned checkout
(packages/coding-agent/src/) into this directory and check them against ../pi_sources.sha256:

  core/tools/truncate.ts            (read_text.mjs, trunc_stdin.mjs)
  utils/mime.ts                     (probe_bytes.mjs)
  utils/exif-orientation.ts         (probe_bytes.mjs, via exif_probe.ts below)

  exif_probe.ts = exif-orientation.ts + one appended line: `export { getExifOrientation };`
  (exposes the internal function; its code is unchanged).

read_text.mjs is read.ts lines 273-322 (the text branch) verbatim apart from I/O, over Pi's own
truncate.ts. Run with `node --experimental-strip-types --no-warnings <script>`.
