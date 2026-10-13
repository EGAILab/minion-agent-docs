// L12-D011 canonical inputs (one definition for the generator and the merge). A ctx.subprocess.spawn case:
// argv (argv[0] is the executable), cwd (null = the provider's), env (null = no overlay; else ORDERED [key, value]
// pairs), inherit_env, pre_aborted. Every non-control argv uses a NONEXISTENT executable, so even a binding that
// skipped validation could never start a process. `minion_offending_entry`: the Owner's Windows raw-subprocess
// exception (#224 issuecomment-6137796390) -- Minion reports that retained entry where Node may drop it.
const N = "\u0000";
const X = "minion-d011-nonexistent";
const a = (k) => "a".repeat(k);
const c = (id, argv, extra = {}) => ({ id, argv, cwd: null, env: null, inherit_env: true, pre_aborted: false, ...extra });
const envOnly = (id, pairs, extra = {}) => c(id, [X, "ok"], { env: pairs, inherit_env: false, ...extra });

export const CASES = [
  // names and precedence
  c("name/file", ["x" + N + "y"]),
  c("name/args-first-argument", [X, "a" + N]),
  c("precedence/args-first-invalid-wins", [X, "ok", "b" + N, "c" + N]),
  c("precedence/file-before-args", ["x" + N, "a" + N]),
  c("name/cwd", [X, "ok"], { cwd: "d" + N }),
  c("precedence/args-before-cwd", [X, "a" + N], { cwd: "d" + N }),
  c("precedence/cwd-before-env", [X, "ok"], { cwd: "d" + N, env: [["K", "v" + N]], inherit_env: false }),
  c("precedence/args-before-env", [X, "a" + N], { env: [["K", "v" + N]], inherit_env: false }),
  // environment
  envOnly("env/value", [["K", "v" + N]]),
  envOnly("env/name", [["A" + N + "B", "v"]]),
  envOnly("env/name-before-value-same-entry", [["A" + N, "v" + N]]),
  envOnly("env/order-two-names", [["Z", "z" + N], ["A", "a" + N]]),
  envOnly("env/order-integer-like-names", [["Z", "z" + N], ["10", "ten" + N], ["2", "two" + N]]),
  c("env/overlay-on-inherited", [X, "ok"], { env: [["MINION_D011_OVERLAY", "v" + N]], inherit_env: true }),
  // Windows case collisions (Owner decision); Linux names are exact, so these are ordinary there.
  envOnly("env/collision-valid-upper-nul-lower", [["K", "ok"], ["k", "bad" + N]], { minion_offending_entry: ["k", "bad" + N] }),
  envOnly("env/collision-nul-lower-valid-upper", [["k", "bad" + N], ["K", "ok"]], { minion_offending_entry: ["k", "bad" + N] }),
  envOnly("env/collision-nul-upper-valid-lower", [["K", "bad" + N], ["k", "ok"]]),
  envOnly("env/collision-both-valid-control", [["K", "ok"], ["k", "ok"]], { control: true }),
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
