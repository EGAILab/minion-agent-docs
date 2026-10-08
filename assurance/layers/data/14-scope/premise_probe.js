// Layer 14 scoping premise probes against Pi's pinned dependency versions (yaml 2.9.0, ignore 7.0.5).
const { parse } = require("yaml");
const ignore = require("ignore");

function y(label, src) {
	try {
		const v = parse(src);
		console.log(`yaml ${label}: ${JSON.stringify(v)} (${typeof (v && v["disable-model-invocation"])})`);
	} catch (e) {
		console.log(`yaml ${label}: THROWS ${e.name}: ${e.message.split("\n")[0]}`);
	}
}

y("bool true", "disable-model-invocation: true");
y("bool yes (1.1 style)", "disable-model-invocation: yes");
y("bool True", "disable-model-invocation: True");
y("bool on", "disable-model-invocation: on");
y("duplicate key", "name: a\nname: b");
y("scalar doc", "just a string");
y("empty", "");
y("numeric name", "name: 123\ndescription: x");
y("tab indent", "name: a\n\tdescription: x");
y("anchor/alias", "a: &x foo\ndescription: *x");
y("merge key", "base: &b {description: d}\n<<: *b");
y("multi-doc", "a: 1\n---\nb: 2");
y("timestamp", "description: 2001-12-14");
y("null", "description: ~");

function ig(label, patterns, paths) {
	const m = ignore().add(patterns);
	for (const p of paths) {
		try {
			console.log(`ignore ${label}: ${JSON.stringify(p)} -> ${m.ignores(p)}`);
		} catch (e) {
			console.log(`ignore ${label}: ${JSON.stringify(p)} -> THROWS ${e.name}: ${e.message}`);
		}
	}
}

ig("dir-only", ["build/"], ["build", "build/", "a/build/", "build/x.md"]);
ig("negation", ["*.md", "!keep.md"], ["x.md", "keep.md"]);
ig("prefixed nested", ["sub/*.md"], ["sub/a.md", "sub/deep/a.md", "a.md"]);
ig("trailing space kept", ["foo "], ["foo", "foo "]);
ig("escaped hash", ["\\#x"], ["#x"]);
ig("double star", ["**/tmp"], ["tmp/", "a/b/tmp/"]);
ig("case", ["Foo"], ["foo", "Foo"]);
ig("non-relative paths", ["x"], ["", "../x", "/x", "./x"]);
ig("backslash on posix", ["a\\b"], ["a\\b", "a/b"]);

// JS semantics the bindings must reproduce
console.log("trim BOM:", JSON.stringify("﻿desc　".trim()), "py-like differs if U+FEFF kept");
console.log("length UTF-16:", "😀".length, "a".repeat(1023).concat("😀").length);
console.log("localeCompare:", ["b", "B", "a", "_x", "-y", "Z", "é", "e"].sort((a, b) => a.localeCompare(b)).join(" "));
console.log("Intl default locale:", Intl.DateTimeFormat().resolvedOptions().locale);
