// Non-normative reference reader for the proposed WP-14.1 Minion frontmatter subset (DIV-004).
// Input: Pi's frontmatter YAML text T (CR-normalized). Output: {ok: true, value} or {ok: false, why}.
// Values: string | null | boolean | {number: string} | {map: [[key, value]...]} | {seq: [value...]}.
// This file is derivation evidence for the contract grammar, not an implementation.

const KEY = /^[A-Za-z_][A-Za-z0-9_.-]*$/;
const RESERVED_KEYS = new Set(["null", "Null", "NULL", "true", "True", "TRUE", "false", "False", "FALSE"]);
const NULL_RE = /^(?:~|[Nn]ull|NULL)?$/;
const BOOL_RE = /^(?:[Tt]rue|TRUE|[Ff]alse|FALSE)$/;
const NUMBER_RES = [
	/^0o[0-7]+$/,
	/^[-+]?[0-9]+$/,
	/^0x[0-9a-fA-F]+$/,
	/^(?:[-+]?\.(?:inf|Inf|INF)|\.nan|\.NaN|\.NAN)$/,
	/^[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)[eE][-+]?[0-9]+$/,
	/^[-+]?(?:\.[0-9]+|[0-9]+\.[0-9]*)$/,
];
// Plain scalars may not start with these (YAML indicators); `-`, `?`, `:` only when followed by
// space/EOL, but the subset rejects them as first characters unconditionally.
const PLAIN_FIRST_FORBIDDEN = new Set([..."-?:,[]{}#&*!|>'\"%@`"]);

// Whether T ends with LF (set per readSubset call): its last line is then terminated.
let lastLineTerminated = false;

class Reject extends Error {}
const reject = (why) => {
	throw new Reject(why);
};

// Characters the subset refuses anywhere in T and in any decoded value.
function forbiddenChar(cp) {
	return (
		(cp < 0x20 && cp !== 0x09 && cp !== 0x0a) ||
		cp === 0x7f ||
		(cp >= 0x80 && cp <= 0x9f) ||
		cp === 0x2028 ||
		cp === 0x2029 ||
		cp === 0xfeff ||
		(cp >= 0xd800 && cp <= 0xdfff)
	);
}

function resolvePlain(text) {
	if (NULL_RE.test(text)) return null;
	if (BOOL_RE.test(text)) return text[0] === "t" || text[0] === "T";
	if (NUMBER_RES.some((re) => re.test(text))) return { number: text };
	return text;
}

const indentOf = (line) => line.length - line.replace(/^ +/, "").length;
const isBlank = (line) => /^[ \t]*$/.test(line);
const isComment = (line) => /^[ \t]*#/.test(line);
const isBlankOrComment = (line) => isBlank(line) || isComment(line);

// Split a same-line plain scalar from a trailing comment and trailing whitespace.
function plainLine(raw) {
	const m = /[ \t]#/.exec(raw);
	const text = (m ? raw.slice(0, m.index) : raw).replace(/[ \t]+$/, "");
	return text;
}

function checkPlainSegment(text, first) {
	if (text.length === 0) reject("empty plain segment");
	// `-`, `?` and `:` may start a plain scalar when a non-whitespace character follows (YAML
	// ns-plain-first); every other indicator may not start one at all.
	const safeLead = "-?:".includes(text[0]) && text.length > 1 && !/[ \t]/.test(text[1]);
	if (PLAIN_FIRST_FORBIDDEN.has(text[0]) && !(first && safeLead)) {
		reject(`${first ? "plain scalar" : "continuation"} starts with indicator ${text[0]}`);
	}
	if (/:[ \t]/.test(text) || text.endsWith(":")) reject("plain scalar contains ': ' or ends with ':'");
	if (text.includes("\t")) reject("tab inside plain scalar");
}

function decodeDouble(body) {
	let out = "";
	for (let i = 0; i < body.length; i++) {
		const c = body[i];
		if (c !== "\\") {
			out += c;
			continue;
		}
		const e = body[++i];
		const simple = { "\\": "\\", '"': '"', "/": "/", t: "\t", n: "\n" };
		if (e in simple) {
			out += simple[e];
			continue;
		}
		const width = { x: 2, u: 4, U: 8 }[e];
		if (!width) reject(`unsupported escape \\${e ?? "EOL"}`);
		const hex = body.slice(i + 1, i + 1 + width);
		if (!new RegExp(`^[0-9A-Fa-f]{${width}}$`).test(hex)) reject("bad hex escape");
		const cp = Number.parseInt(hex, 16);
		if (cp > 0x10ffff || forbiddenChar(cp)) reject("escape outside the subset character set");
		out += String.fromCodePoint(cp);
		i += width;
	}
	return out;
}

// Same-line value after `key: ` (or `- `). Returns [value, consumedExtraLines].
function sameLineScalar(rest, allowContinuation, lines, i, n) {
	if (rest[0] === '"') {
		let j = 1;
		while (j < rest.length && rest[j] !== '"') j += rest[j] === "\\" ? 2 : 1;
		if (j >= rest.length) reject("unterminated or multi-line double-quoted scalar");
		const after = rest.slice(j + 1);
		if (!/^([ \t]+(#.*)?)?$/.test(after)) reject("content after double-quoted scalar");
		return [decodeDouble(rest.slice(1, j)), 0];
	}
	if (rest[0] === "'") {
		let j = 1;
		let out = "";
		for (;;) {
			if (j >= rest.length) reject("unterminated or multi-line single-quoted scalar");
			if (rest[j] === "'") {
				if (rest[j + 1] === "'") {
					out += "'";
					j += 2;
					continue;
				}
				break;
			}
			out += rest[j++];
		}
		const after = rest.slice(j + 1);
		if (!/^([ \t]+(#.*)?)?$/.test(after)) reject("content after single-quoted scalar");
		return [out, 0];
	}
	const first = plainLine(rest);
	checkPlainSegment(first, true);
	// a comment ends a plain scalar: no continuation may follow it
	if (!allowContinuation || /[ \t]#/.test(rest)) {
		if (nextContentIndent(lines, i + 1) > n) reject("continuation not allowed here");
		return [resolvePlain(first), 0];
	}
	// Multi-line plain scalar: following lines with indent > n.
	let text = first;
	let blanks = 0;
	let j = i + 1;
	for (; j < lines.length; j++) {
		const line = lines[j];
		if (isBlank(line)) {
			blanks++;
			continue;
		}
		if (indentOf(line) <= n) break;
		if (/^ *\t/.test(line)) reject("tab in continuation indentation");
		if (isComment(line)) reject("comment inside multi-line plain scalar");
		// Indentation is SP only (TAB is rejected globally). Any other whitespace -- U+00A0, U+2003,
		// U+3000 and the like -- is scalar content, as in yaml@2.9.0 (WP141-C001).
		const stripped = line.replace(/^ +/, "");
		const seg = plainLine(stripped);
		if (seg !== stripped.replace(/[ \t]+$/, "")) reject("comment after continuation line");
		checkPlainSegment(seg, false);
		text += blanks === 0 ? ` ${seg}` : "\n".repeat(blanks);
		if (blanks !== 0) text += seg;
		blanks = 0;
	}
	// trailing blank lines are not part of the scalar; rewind to the last consumed content line
	let last = j - 1;
	while (last > i && isBlank(lines[last])) last--;
	return [resolvePlain(text), last - i];
}

function nextContentIndent(lines, from) {
	for (let j = from; j < lines.length; j++) if (!isBlankOrComment(lines[j])) return indentOf(lines[j]);
	return -1;
}

function blockScalar(header, lines, i, n) {
	const m = /^([|>])([+-]?)([ \t]+#.*)?$/.exec(header);
	if (!m) reject("unsupported block scalar header");
	const [, style, chomp] = m;
	// Region: following lines until the first non-blank line indented <= n.
	let j = i + 1;
	while (j < lines.length && (isBlank(lines[j]) || indentOf(lines[j]) > n)) j++;
	const region = lines.slice(i + 1, j);
	const firstText = region.find((l) => !isBlank(l));
	const contentIndent = firstText === undefined ? -1 : indentOf(firstText);
	const content = [];
	for (const line of region) {
		if (isBlank(line)) {
			// an empty line: only spaces, and no more of them than the content indentation
			if (line.includes("\t")) reject("tab in a whitespace-only block scalar line");
			if (contentIndent === -1 ? line.length > 0 : line.length > contentIndent) {
				reject("whitespace-only block scalar line beyond the content indentation");
			}
			content.push(null);
			continue;
		}
		const ind = indentOf(line);
		if (ind < contentIndent) reject("under-indented block scalar line");
		const text = line.slice(contentIndent);
		if (style === ">" && /^[ \t]/.test(text)) reject("more-indented line in folded scalar");
		content.push(text);
	}
	// trailing blank lines belong to the block scalar's chomping region; each counts only if a line
	// break follows it in T -- the unterminated final line of T contributes none
	let trailing = 0;
	while (content.length && content[content.length - 1] === null) {
		content.pop();
		trailing++;
	}
	if (trailing > 0 && j === lines.length && !lastLineTerminated) trailing--;
	const consumed = j - 1 - i;
	if (content.length === 0) return [chomp === "+" ? "\n".repeat(trailing) : "", consumed];
	let body = "";
	if (style === "|") {
		body = content.map((l) => l ?? "").join("\n");
	} else {
		let pendingBlank = 0;
		content.forEach((l, k) => {
			if (l === null) {
				pendingBlank++;
				return;
			}
			if (k > 0) body += pendingBlank === 0 ? " " : "\n".repeat(pendingBlank);
			body += l;
			pendingBlank = 0;
		});
	}
	if (chomp === "-") return [body, consumed];
	if (chomp === "+") return [body + "\n" + "\n".repeat(trailing), consumed];
	return [`${body}\n`, consumed];
}

function sequence(lines, i, m) {
	const items = [];
	let j = i;
	for (; j < lines.length; j++) {
		const line = lines[j];
		if (isBlankOrComment(line)) continue;
		const ind = indentOf(line);
		if (ind < m) break;
		if (ind > m) reject("unexpected deeper content in sequence");
		const body = line.slice(m);
		if (!body.startsWith("- ")) break;
		const rest = body.slice(2).replace(/^[ \t]+/, "");
		if (rest.length === 0 || rest[0] === "#") reject("empty or nested sequence item");
		const [value] = sameLineScalar(rest, false, lines, j, m);
		items.push(value);
	}
	return [{ seq: items }, j - 1 - i];
}

function mapping(lines, i, n) {
	const entries = [];
	const seen = new Set();
	let j = i;
	while (j < lines.length) {
		const line = lines[j];
		if (isBlankOrComment(line)) {
			j++;
			continue;
		}
		const ind = indentOf(line);
		if (ind < n) break;
		if (ind > n) reject("unexpected indentation");
		const body = line.slice(n);
		if (body[0] === "\t") reject("tab indentation");
		const km = /^([^:\s]+):(?=[ \t]|$)/.exec(body);
		if (!km) reject("line is not a mapping entry");
		const key = km[1];
		if (!KEY.test(key) || RESERVED_KEYS.has(key)) reject(`unsupported key ${key}`);
		if (seen.has(key)) reject(`duplicate key ${key}`);
		seen.add(key);
		let rest = body.slice(key.length + 1);
		if (rest.length > 0 && rest[0] !== " ") reject("separator after ':' must start with a space");
		rest = rest.replace(/^[ \t]+/, "");
		let value;
		let consumed = 0;
		if (rest.length === 0 || rest[0] === "#") {
			const next = nextContentIndent(lines, j + 1);
			let k = j + 1;
			while (k < lines.length && isBlankOrComment(lines[k])) k++;
			if (next > n && /^[^:\s]+:(?=[ \t]|$)/.test(lines[k].slice(next))) {
				[value, consumed] = mapping(lines, k, next);
				consumed += k - j;
			} else if (next >= n && next !== -1 && lines[k].slice(next).startsWith("- ")) {
				[value, consumed] = sequence(lines, k, next);
				consumed += k - j;
			} else if (next > n) {
				reject("value on the following line is outside the subset");
			} else {
				value = null;
			}
		} else if (rest[0] === "|" || rest[0] === ">") {
			[value, consumed] = blockScalar(rest, lines, j, n);
		} else {
			[value, consumed] = sameLineScalar(rest, true, lines, j, n);
		}
		entries.push([key, value]);
		j += consumed + 1;
	}
	return [{ map: entries }, j - 1 - i];
}

export function readSubset(text) {
	try {
		for (const ch of text) if (forbiddenChar(ch.codePointAt(0))) reject("forbidden character");
		const lines = text.split("\n");
		// a final line break terminates the last line; it does not start another one
		lastLineTerminated = lines.length > 1 && lines[lines.length - 1] === "";
		if (lastLineTerminated) lines.pop();
		for (const line of lines) if (/^ *\t/.test(line)) reject("tab in leading whitespace");
		let k = 0;
		while (k < lines.length && isBlankOrComment(lines[k])) k++;
		if (k === lines.length) return { ok: true, value: null };
		if (indentOf(lines[k]) !== 0) reject("top-level mapping must start at column 0");
		const [value, consumed] = mapping(lines, k, 0);
		for (let j = k + consumed + 1; j < lines.length; j++) if (!isBlankOrComment(lines[j])) reject("trailing content");
		return { ok: true, value };
	} catch (e) {
		if (e instanceof Reject) return { ok: false, why: e.message };
		throw e;
	}
}

// Convert a yaml@2.9.0 JS value into the same shape for comparison.
export function fromYaml(v) {
	if (v === null || v === undefined) return null;
	if (typeof v === "string" || typeof v === "boolean") return v;
	if (typeof v === "number") return { number: true };
	if (Array.isArray(v)) return { seq: v.map(fromYaml) };
	if (typeof v === "object") return { map: Object.entries(v).map(([k, x]) => [k, fromYaml(x)]) };
	return { other: String(v) };
}

export function normalizeSubset(v) {
	if (v === null || typeof v === "string" || typeof v === "boolean") return v;
	if ("number" in v) return { number: true };
	if ("seq" in v) return { seq: v.seq.map(normalizeSubset) };
	return { map: v.map.map(([k, x]) => [k, normalizeSubset(x)]) };
}
