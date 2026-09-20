import { fileURLToPath } from "node:url";
import { readFileSync } from "node:fs";
const lines = readFileSync(process.argv[2], "utf-8").split("\n").filter(Boolean);
for (const c of lines) {
  try {
    console.log(c + "\t" + JSON.stringify(fileURLToPath(c, {windows: true})));
  } catch (e) {
    console.log(c + "\tPARSE_ERROR");
  }
}
