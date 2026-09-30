// Node module customization hook: when the pinned Pi file-mutation-queue.ts imports node:fs/promises, it gets
// fs_shim.mjs instead. No Pi file is modified; every other importer gets the real module.
import { register } from "node:module";

register(
  "data:text/javascript," +
    encodeURIComponent(`
export async function resolve(specifier, context, next) {
  if (specifier === "node:fs/promises" && context.parentURL && context.parentURL.endsWith("/file-mutation-queue.ts")) {
    return next(new URL("./fs_shim.mjs", ${JSON.stringify(import.meta.url)}).href, context);
  }
  return next(specifier, context);
}`),
);
