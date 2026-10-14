// L12-D012 scoping: does win32.resolve of a drive-relative path on ANOTHER drive depend on the hidden per-drive
// cwd variable (=X:)? Pure computation; mutates only this process's own environment.
import path from "node:path";

const show = (label) => console.log(label, JSON.stringify(path.win32.resolve("C:\\x", "a::/b")),
  JSON.stringify(path.win32.resolve("C:\\x", "x:y:z/w")), JSON.stringify(path.win32.resolve("C:\\x", "c:d")));
show("no =X: vars:");
process.env["=A:"] = "A:\\deep";
process.env["=X:"] = "X:\\q";
process.env["=C:"] = "C:\\other";
show("with =A:, =X:, =C: set:");
