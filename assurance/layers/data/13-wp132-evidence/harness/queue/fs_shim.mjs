// Stand-in for node:fs/promises, loaded ONLY for the pinned file-mutation-queue.ts (see loader.mjs).
// Everything is re-exported unchanged except realpath, whose answer (and its trace) each scenario scripts through
// globalThis.__queueHarness. No timers -- every interleaving is decided by the script.
export * from "node:fs/promises";

export async function realpath(path) {
  return globalThis.__queueHarness.realpath(path);
}
