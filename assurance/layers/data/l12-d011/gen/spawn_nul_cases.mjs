// L12-D011 canonical inputs, one definition for the generator and the merge. A ctx.subprocess.spawn case:
//   argv          argv[0] is the executable (each element a string, or {linux, win32})
//   cwd           null = not supplied; else the RAW supplied cwd (string or {linux, win32})
//   provider_cwd  the provider's own cwd ({linux, win32}); every case names one, so a resolved cwd is deterministic
//   baseline      null = the provider's live baseline (an OS environment holds no NUL); else a CONFIGURED baseline,
//                 ORDERED pairs in the given presentation order
//   env           null = no overlay; else the call's overlay, ORDERED pairs in insertion order
//   inherit_env, pre_aborted, control (no NUL reaches validation: the OS's own failure for a nonexistent executable)
// Every non-control argv[0] is a NONEXISTENT executable, so even a binding that skipped validation could never
// start a process. Owner decisions: #195 6137514688; #224 6137796390 (Windows retained entries), 6141307443 (F2
// POSIX order, C003 effective cwd).
const N = "\u0000";
const X = "minion-d011-nonexistent";
const P = (linux, win32) => ({ linux, win32 });
const PROV = P("/x", "C:\\x");
const a = (k) => "a".repeat(k);
const c = (id, argv, extra = {}) => ({ id, argv, cwd: null, provider_cwd: PROV, baseline: null, env: null,
  inherit_env: true, pre_aborted: false, control: false, ...extra });
const envOnly = (id, env, extra = {}) => c(id, [X, "ok"], { env, inherit_env: false, ...extra });
const withBase = (id, baseline, env, extra = {}) => c(id, [X, "ok"], { baseline, env, inherit_env: true, ...extra });

export const CASES = [
  // names and precedence
  c("name/file", ["x" + N + "y"]),
  c("name/args-first-argument", [X, "a" + N]),
  c("precedence/args-first-invalid-wins", [X, "ok", "b" + N, "c" + N]),
  c("precedence/file-before-args", ["x" + N, "a" + N]),
  c("precedence/args-before-env", [X, "a" + N], { env: [["K", "v" + N]], inherit_env: false }),
  // effective cwd (C003)
  c("cwd/literal-relative", [X, "ok"], { cwd: "d" + N }),
  c("cwd/literal-absolute", [X, "ok"], { cwd: P("/a" + N + "b", "C:\\a" + N + "b") }),
  c("cwd/file-url-percent-00", [X, "ok"], { cwd: P("file:///a%00b", "file:///C:/a%00b") }),
  c("cwd/file-url-percent-2500-control", [X, "ok"], { cwd: P("file:///a%2500b", "file:///C:/a%2500b"), control: true }),
  c("cwd/malformed-file-url-literal-fallback", [X, "ok"], { cwd: P("file:///a%2Fb" + N, "file:///C:/a%2Fb" + N) }),
  c("cwd/provider-default-nul", [X, "ok"], { provider_cwd: P("/x" + N + "y", "C:\\x" + N + "y") }),
  c("cwd/provider-default-control", [X, "ok"], { control: true }),
  c("cwd/unicode-lossless", [X, "ok"], { cwd: "d\u00e9\ud800" + N }),
  c("precedence/file-before-cwd", ["x" + N, "ok"], { cwd: "d" + N }),
  c("precedence/args-before-cwd", [X, "a" + N], { cwd: "d" + N }),
  c("precedence/cwd-before-env", [X, "ok"], { cwd: "d" + N, env: [["K", "v" + N]], inherit_env: false }),
  c("abort/pre-aborted-before-cwd", [X, "ok"], { cwd: "d" + N, pre_aborted: true }),
  // environment: names, values, Windows retained entries
  envOnly("env/value", [["K", "v" + N]]),
  envOnly("env/name", [["A" + N + "B", "v"]]),
  envOnly("env/name-before-value-same-entry", [["A" + N, "v" + N]]),
  envOnly("env/collision-valid-upper-nul-lower", [["K", "ok"], ["k", "bad" + N]]),
  envOnly("env/collision-nul-lower-valid-upper", [["k", "bad" + N], ["K", "ok"]]),
  envOnly("env/collision-nul-upper-valid-lower", [["K", "bad" + N], ["k", "ok"]]),
  envOnly("env/collision-both-valid-control", [["K", "ok"], ["k", "ok"]], { control: true }),
  // environment order (F2)
  envOnly("env/order-overlay-Z-then-A", [["Z", "z" + N], ["A", "a" + N]]),
  envOnly("env/order-overlay-A-then-Z", [["A", "a" + N], ["Z", "z" + N]]),
  withBase("env/order-baseline-ZA-overlay-ZA", [["Z", "ok"], ["A", "ok"]], [["Z", "z" + N], ["A", "a" + N]]),
  withBase("env/order-baseline-AZ-overlay-ZA", [["A", "ok"], ["Z", "ok"]], [["Z", "z" + N], ["A", "a" + N]]),
  withBase("env/order-baseline-only-ZA", [["Z", "z" + N], ["A", "a" + N]], null),
  withBase("env/order-baseline-only-AZ", [["A", "a" + N], ["Z", "z" + N]], null),
  withBase("env/order-mixed-overlay-and-baseline-only", [["A", "a" + N]], [["Z", "z" + N]]),
  withBase("env/superseded-baseline-value-control", [["K", "bad" + N]], [["K", "ok"]], { control: true }),
  envOnly("env/order-integer-index-names", [["Z", "z" + N], ["01", "zero-one" + N], ["4294967295", "max" + N], ["10", "ten" + N], ["2", "two" + N]]),
  envOnly("env/order-non-index-controls", [["Z", "ok"], ["4294967295", "max" + N], ["01", "zero-one" + N]]),
  withBase("env/order-baseline-only-utf16-vs-utf8", [["\uff5e", "fullwidth" + N], ["\u{10000}", "astral" + N]], null),
  envOnly("env/order-overlay-utf16-vs-utf8", [["\uff5e", "fullwidth" + N], ["\u{10000}", "astral" + N]]),
  envOnly("env/proto-name-own-property", [["__proto__", "p" + N]]),
  // formatting of the received value (as args[0])
  ...[
    ["fmt/single-quote", "it's" + N],
    ["fmt/single-and-double", "it's \"q\"" + N],
    ["fmt/single-double-backtick", "it's \"q\" `b`" + N],
    ["fmt/single-double-dollar-brace", "it's \"q\" ${x}" + N],
    ["fmt/backslash", "C:\\dir\\f" + N],
    ["fmt/controls", "\b\t\n\v\f\r\x01\x1f\x7f\x80\x9f\u00a0" + N],
    ["fmt/lone-high-surrogate", "\ud800" + N],
    ["fmt/lone-low-surrogate", "\udc00" + N],
    ["fmt/pair-and-bmp", "\u{1F600}\u00e9\u4e2d" + N],
    ["fmt/over-100-units-escape-path", "\t" + "z".repeat(99) + N],
    ["fmt/over-100-units-quote", "'" + "z".repeat(105) + N],
    ["len/inspected-127", a(121) + N],
    ["len/inspected-128", a(122) + N],
    ["len/inspected-129", a(123) + N],
    ["len/surrogate-pair-straddles-128", a(126) + "\u{1F600}" + N],
    ["len/newline-split-over-76", "line1\n" + "x".repeat(80) + N],
    ["len/newline-not-split-under-77", "l\n" + "x".repeat(10) + N],
    ["len/over-max-string-length", "y".repeat(10001) + N],
  ].map(([id, value]) => c(id, [X, value])),
  // pre-abort precedence and controls
  c("abort/pre-aborted-before-nul", [X, "a" + N], { pre_aborted: true }),
  c("control/no-nul-nonexistent-executable", [X, "ok"], { control: true }),
];

export const TOOL_CASES = [
  { id: "tool/find/nul-pattern", tool: "find", arguments: { any: { pattern: "a" + N + "b" } } },
  { id: "tool/find/nul-absolute-search-path", tool: "find",
    arguments: { linux: { pattern: "*", path: "/x" + N + "y" }, win32: { pattern: "*", path: "C:\\x" + N + "y" } } },
  { id: "tool/find/nul-pattern-pre-aborted", tool: "find", arguments: { any: { pattern: "a" + N + "b" } }, pre_aborted: true },
  { id: "tool/grep/nul-pattern", tool: "grep", arguments: { any: { pattern: "a" + N + "b" } } },
  { id: "tool/grep/nul-glob", tool: "grep", arguments: { any: { pattern: "a", glob: "*" + N } } },
  { id: "tool/bash/nul-command", tool: "bash", arguments: { any: { command: "echo a" + N + "b" } } },
  { id: "tool/bash/nul-command-pre-aborted", tool: "bash", arguments: { any: { command: "echo a" + N + "b" } }, pre_aborted: true },
];

export const pick = (v, platform) => (v !== null && typeof v === "object" && !Array.isArray(v) ? v[platform] : v);
