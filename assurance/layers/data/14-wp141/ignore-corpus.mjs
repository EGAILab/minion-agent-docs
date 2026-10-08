// ignore@7.0.5 differential corpus for the Python/Rust ports (HAR-011). Each case is a pattern
// list and paths, with pinned ignore's `ignores()` result per path, or the error it throws.
// Deterministic (mulberry32). Run: node ignore-corpus.mjs <count> <out.json>
import { writeFileSync } from "node:fs";
import ignore from "ignore";

const count = Number(process.argv[2] ?? 5000);
let s = 20260808 >>> 0;
const rand = () => {
	s = (s + 0x6d2b79f5) >>> 0;
	let t = s;
	t = Math.imul(t ^ (t >>> 15), t | 1);
	t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
	return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};
const pick = (xs) => xs[Math.floor(rand() * xs.length)];

const ATOMS = [
	"a", "b", "c", "A", "B", "x", "y", "z", "ab", "foo", "Foo", "bar", "1", "9", "-", "_", ".", "~",
	"*", "**", "?", "/", "!", "#", "\\", "\\*", "\\?", "\\!", "\\#", "\\ ", " ", "  ", "\t",
	"[", "]", "[a-c]", "[!a]", "[^a]", "[z-a]", "[~-a]", "[a-\\d]", "[\\]]", "[ab", "{", "}", "(", ")",
	"|", "+", "$", "^", ".", "K", "k", "K", "ſ", "s", "S", "ß", "SS", "İ", "ı",
	"i", "I", "é", "É", "\u{1F600}", " ", "　", "﻿", "\\d", "\\w", "\\s", "\\b",
	"\\x41", "\\u0041", "\\1", "\\8", "\\q", "\\c", "\\cA", "\r",
];
const SEGMENTS = [
	"a", "b", "c", "A", "ab", "foo", "Foo", "bar", "x", "1", "9", "~", "-", "_", "#x", "!x", "a b",
	"a ", "k", "K", "K", "s", "ſ", "S", "ß", "ss", "SS", "i", "I", "İ", "ı",
	"é", "É", "\u{1F600}", "a\u{1F600}", "x.y", "x\ty", "[a]", "{x}", "(x)", "a+b", "$",
	"^", "a b",
];

function pattern() {
	let p = "";
	for (let i = 0, n = 1 + Math.floor(rand() * 4); i < n; i++) p += pick(ATOMS);
	if (rand() < 0.15) p = `!${p}`;
	if (rand() < 0.1) p = `/${p}`;
	if (rand() < 0.1) p += "/";
	return p;
}
function path() {
	const parts = [];
	for (let i = 0, n = 1 + Math.floor(rand() * 3); i < n; i++) parts.push(pick(SEGMENTS));
	let p = parts.join("/");
	if (rand() < 0.3) p += "/";
	return p;
}

const cases = [];
for (let i = 0; i < count; i++) {
	const patterns = Array.from({ length: 1 + Math.floor(rand() * 3) }, pattern);
	const paths = Array.from({ length: 3 }, path).filter((p) => !/^\.{0,2}\/|^\.{1,2}$/.test(p));
	const ig = ignore().add(patterns);
	const results = paths.map((p) => {
		try {
			return { path: p, ignored: ig.ignores(p) };
		} catch (e) {
			return { path: p, error: e.name };
		}
	});
	cases.push({ patterns, results });
}
writeFileSync(process.argv[3] ?? "ignore-corpus.json", `${JSON.stringify({ ignore: "7.0.5", node: process.version, platform: process.platform, cases })}\n`);
const errors = cases.flatMap((c) => c.results).filter((r) => r.error).length;
console.log(`${cases.length} cases, ${cases.reduce((n, c) => n + c.results.length, 0)} checks, ${errors} throw`);
