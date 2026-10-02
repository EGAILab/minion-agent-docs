import { spawnSync } from "node:child_process";
const bash = "C:\\Program Files\\Git\\bin\\bash.exe";
const env = { SystemRoot: process.env.SystemRoot, ProgramFiles: "C:\\PF", "ProgramFiles(x86)": "C:\\PF86", Minion_Session_Id: "stale", Path: process.env.PATH };
const r = spawnSync(bash, ["-c", "env | grep -iE '^(programfiles|minion|path=)' | sed 's/=.*//' | sort"], { env, encoding: "utf8" });
console.log(r.error ? String(r.error) : JSON.stringify(r.stdout.trim().split("\n")), r.stderr || "");
