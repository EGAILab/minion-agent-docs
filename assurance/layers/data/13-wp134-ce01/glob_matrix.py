"""CE-L13-WP134-01 (WP134-IMPL-R002) behaviour matrix for the Windows full-path rewrite.

Standalone (Python 3.12+, no Minion import); runs on either platform against the pinned fd.

- Linux (the DIV-002 target): fd with the effective pattern exactly as Pi passes it on Linux.
- Windows: fd with, per row,
    pi        Pi's text, `replaceAll("/", "[/\\]")`;
    candidate the reviewed candidate's text (minion-agent#153 @ f97906ca, `_windows_full_path`),
              when its source file is given as the optional third argument;
    rejected  a local substitution decided on the ORIGINAL pattern (rejected design: it breaks the
              class constructs Pi's rewrite reshapes);
    proposal  the proposed rule (PROPOSAL below), decided on Pi's text as fd lexes it.

    python glob_matrix.py <fd binary> <out.json> [<candidate find.py>]

Recorded design evidence (not a column): an empty alternative such as `{,**[/\\]}` is accepted by
the pinned fd but never matches the empty string, so a zero-directory form cannot be written that
way; it was tried and rejected during characterization.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SEP = "[/\\\\]"  # Pi's String.raw`[/\\]`
FILES = ["src/b.spec.ts", "src/sub/b.spec.ts", "src/sub/deep/b.spec.ts", "src/a/b.spec.ts", "lib/b.spec.ts",
         "x/b", "x/q/b", "x/c", "x/q/c", "xb", "x/ab", "x/bc",
         # checkpoint review 1 (C001): mixed recursive / Pi-scope witnesses
         "src/a.ts", "src/sub/a.ts", "src/a/sub/b.ts", "src/x/b.ts", "src/q/r/x/b.ts", "src/q/r/x/s/b.ts",
         # checkpoint review 2 (C002): literal comma vs alternative separator
         "x,b", "x,q/b"]
PATTERNS = [
    # genuine recursive components
    "src/**/b.spec.ts", "src/**/**/b.spec.ts", "{src/**/b.spec.ts,none}", "{src,lib}/**/b.spec.ts",
    "src/**/{deep/**/b,b}.spec.ts", "src/**/*/**/b.spec.ts", "src/a**/**/b.spec.ts", "src/***/**/b.spec.ts",
    "src/[a-]/**/b.spec.ts", "src/{a,{b}}/**/b.spec.ts", "src/{}/**/b.spec.ts", "src/[/]/**/b.spec.ts",
    "src/[]]/**/b.spec.ts",
    # alternative-start **
    "x/{**/b,c}", "x/{c,**/b}", "x/{**/b}", "x/{a,{**/b}}", "x/{**/**/b,c}", "x/{q,{**/b}}/c",
    "x/{**/b,c}/**/c", "x{**/b,c}", "x{**/b}", "x/a{**/b,c}", "x/{a,b{**/c}}", "{**/b,c}", "**/{**/b,c}",
    # ** that is not a recursive component, and Pi-scope constructs
    "{x/**,y}/b", "x/{q/**,nope}/b", "x/{**}/b", "x/{a**/b,c}", "src/**", "src/*.spec.ts", "x/**b", "x/b**/c",
    "src/[]/**/b.spec.ts", "src/[!]/**/b.spec.ts", "src/[/**/b.spec.ts", "x\\/**/b",
    # engine-rejected syntax
    "src/[z-a]/**/b.spec.ts", "src/{a/**/b.spec.ts", "src/a}/**/b.spec.ts",
    # mixed: a recursive component composed with a retained Pi-scope construct (C001)
    "src/**/a*.ts", "{src/**/a*.ts,none}", "src/**/x/*.ts", "src/[!]/**/x/**/b.ts", "src/**/[!]/b.ts",
    "src/*/**/b.ts", "src/**/**b.ts", "src/{**/a*.ts,none}",
    # literal comma outside braces vs a comma or "{" that begins an alternative (C002)
    "x,**/b", "x,{**/b}", "x,**/b{a,b}", "{x,**/b}", "x}/**/b",
]

# Recursive components per row, counted BY HAND from rule 4 (independent of the finder below):
# the pattern-initial `**/` never counts; a class can absorb Pi's "[/\\]"; "," and "}" are
# syntax only inside braces.
EXPECTED_COMPONENTS = {
    "src/**/b.spec.ts": 1, "src/**/**/b.spec.ts": 2, "{src/**/b.spec.ts,none}": 1,
    "{src,lib}/**/b.spec.ts": 1, "src/**/{deep/**/b,b}.spec.ts": 2, "src/**/*/**/b.spec.ts": 2,
    "src/a**/**/b.spec.ts": 1, "src/***/**/b.spec.ts": 1, "src/[a-]/**/b.spec.ts": 1,
    "src/{a,{b}}/**/b.spec.ts": 1, "src/{}/**/b.spec.ts": 1, "src/[/]/**/b.spec.ts": 1,
    "src/[]]/**/b.spec.ts": 1,
    "x/{**/b,c}": 1, "x/{c,**/b}": 1, "x/{**/b}": 1, "x/{a,{**/b}}": 1, "x/{**/**/b,c}": 2,
    "x/{q,{**/b}}/c": 1, "x/{**/b,c}/**/c": 2, "x{**/b,c}": 1, "x{**/b}": 1, "x/a{**/b,c}": 1,
    "x/{a,b{**/c}}": 1, "{**/b,c}": 1, "**/{**/b,c}": 1,
    "{x/**,y}/b": 0, "x/{q/**,nope}/b": 0, "x/{**}/b": 0, "x/{a**/b,c}": 0, "src/**": 0,
    "src/*.spec.ts": 0, "x/**b": 0, "x/b**/c": 0, "src/[]/**/b.spec.ts": 0, "src/[!]/**/b.spec.ts": 0,
    "src/[/**/b.spec.ts": 0, "x\\/**/b": 1,
    "src/[z-a]/**/b.spec.ts": 1, "src/{a/**/b.spec.ts": 1, "src/a}/**/b.spec.ts": 1,
    "src/**/a*.ts": 1, "{src/**/a*.ts,none}": 1, "src/**/x/*.ts": 1, "src/[!]/**/x/**/b.ts": 1,
    "src/**/[!]/b.ts": 1, "src/*/**/b.ts": 1, "src/**/**b.ts": 1, "src/{**/a*.ts,none}": 1,
    "x,**/b": 0, "x,{**/b}": 1, "x,**/b{a,b}": 0, "{x,**/b}": 1, "x}/**/b": 1,
}


def recursive_components(e: str) -> list[int]:
    """Indices in the effective pattern `e` of each recursive component's `**` (rule 4: read on
    Pi's rewritten text as the pinned fd lexes it; a `**` followed by a separator and preceded by a
    separator or an alternative start; the pattern-initial `**` excluded). Positions map back to
    `e` because Pi's rewrite replaces each "/" by a fixed five-character token."""
    pi_text, origin = [], []
    for index, char in enumerate(e):
        piece = SEP if char == "/" else char
        pi_text.append(piece)
        origin.extend([index] * len(piece))
    text = "".join(pi_text)
    tokens, starts, index = [], [], 0
    for kind, value in lex(text):
        tokens.append((kind, value))
        starts.append(index)
        index += len(value)

    def is_sep(k: int) -> bool:
        return 0 <= k < len(tokens) and tokens[k] == ("class", SEP)

    found = []
    for k in range(1, len(tokens) - 2):
        two = tokens[k][0] == "star" and tokens[k + 1][0] == "star"
        alone = tokens[k - 1][0] != "star" and (k + 2 >= len(tokens) or tokens[k + 2][0] != "star")
        if two and alone and is_sep(k + 2) and (is_sep(k - 1) or tokens[k - 1][0] in ("open", "comma")):
            found.append(origin[starts[k]])
    return found


def oracle(fd: str, e: str, root: Path) -> dict[str, object]:
    """The composition rule's expected Windows outcome, derived from Pi's own rewrite only: if fd
    rejects Pi's text, Pi's outcome; otherwise the union, over every keep/remove choice of each
    recursive component (removing exactly its `**/`), of Pi's Windows result for that pattern."""
    pi = run(fd, e.replace("/", SEP), root)
    if pi["exit"] != 0:
        return {"variants": [e], **pi}
    components = recursive_components(e)
    variants, results = [], set()
    for mask in range(1 << len(components)):
        drop = {components[b] for b in range(len(components)) if mask >> b & 1}
        variant = "".join(ch for i, ch in enumerate(e)
                          if not any(start <= i < start + 3 for start in drop))
        variants.append(variant)
        r = run(fd, variant.replace("/", SEP), root)
        if r["exit"] != 0:
            return {"variants": variants, "exit": r["exit"], "results": [], "stderr": "variant rejected: " + r["stderr"]}
        results.update(r["results"])  # type: ignore[arg-type]
    return {"variants": variants, "exit": 0, "results": sorted(results), "stderr": ""}


def effective(pattern: str) -> str:
    if pattern.startswith("/") or pattern.startswith("**/") or pattern == "**":
        return pattern
    return "**/" + pattern


def lex(text: str) -> list[tuple[str, str]]:
    """Glob text as the pinned fd lexes it on Windows (no backslash escape): a class is "[", an
    optional "!" or "^", a leading "]" taken as a member, then up to the next "]" (an unclosed
    "[" is a literal); "{" and "*" are syntax; "," and "}" are syntax only inside an open brace
    group (checkpoint review 2, C002) -- outside braces they are ordinary characters; anything else
    is a literal character."""
    tokens: list[tuple[str, str]] = []
    index, depth = 0, 0
    while index < len(text):
        char = text[index]
        if char == "[":
            j = index + 1
            if j < len(text) and text[j] in "!^":
                j += 1
            if j < len(text) and text[j] == "]":
                j += 1
            end = text.find("]", j)
            if end != -1:
                tokens.append(("class", text[index : end + 1]))
                index = end + 1
                continue
        if char == "{":
            kind, depth = "open", depth + 1
        elif char == "}" and depth:
            kind, depth = "close", depth - 1
        elif char == "," and depth:
            kind = "comma"
        else:
            kind = "star" if char == "*" else "lit"
        tokens.append((kind, char))
        index += 1
    return tokens


def proposal(e: str) -> str:
    """PROPOSAL. Lex Pi's text. A recursive component is `**` (exactly two adjacent star tokens)
    followed by a SEP token and preceded by a SEP token or by "{" / "," (an alternative start); the
    pattern-initial `**` is left alone. Adjacent components collapse. `SEP ** SEP` becomes
    `{SEP,SEP**SEP}`; an alternative-start `** SEP rest` becomes `** SEP rest,rest` (the alternative
    duplicated without it). Everything else is Pi's text, character for character."""
    tokens = lex(e.replace("/", SEP))
    n = len(tokens)

    def is_sep(k: int) -> bool:
        return 0 <= k < n and tokens[k] == ("class", SEP)

    def dstar(k: int) -> bool:
        return (k + 1 < n and tokens[k][0] == "star" and tokens[k + 1][0] == "star"
                and (k + 2 >= n or tokens[k + 2][0] != "star") and (k == 0 or tokens[k - 1][0] != "star"))

    def alt_end(k: int) -> int | None:
        depth, j = 0, k
        while j < n:
            kind = tokens[j][0]
            if kind == "open":
                depth += 1
            elif kind == "close":
                if depth == 0:
                    return j
                depth -= 1
            elif kind == "comma" and depth == 0:
                return j
            j += 1
        return None

    def render(lo: int, hi: int) -> str:
        out: list[str] = []
        i = lo
        while i < hi:
            if dstar(i) and is_sep(i + 2) and i > 0 and (is_sep(i - 1) or tokens[i - 1][0] in ("open", "comma")):
                j = i + 3
                while j + 2 <= hi and dstar(j) and is_sep(j + 2):
                    j += 3
                if is_sep(i - 1):
                    out[-1:] = ["{" + SEP + "," + SEP + "**" + SEP + "}"]
                    i = j
                    continue
                end = alt_end(i)
                if end is not None and end <= hi:
                    rest = render(j, end)
                    out.append("**" + SEP + rest + "," + rest)
                    i = end
                    continue
            out.append(tokens[i][1])
            i += 1
        return "".join(out)

    return render(0, n)


def rejected(e: str) -> str:
    """Rejected design: local substitution decided on the ORIGINAL pattern's classes."""
    parts, index, plain = [], 0, []
    while index < len(e):
        if e[index] == "[":
            end = e.find("]", index + 2)
            if end != -1:
                parts.append(("".join(plain), False))
                plain = []
                parts.append((e[index : end + 1], True))
                index = end + 1
                continue
        plain.append(e[index])
        index += 1
    parts.append(("".join(plain), False))
    out = []
    for text, is_class in parts:
        if is_class:
            out.append(text.replace("/", SEP))
            continue
        while "/**/**/" in text:
            text = text.replace("/**/**/", "/**/")
        out.append("\0".join(piece.replace("/", SEP) for piece in text.split("/**/")))
    return "".join(out).replace("\0", "{" + SEP + "," + SEP + "**" + SEP + "}")


def run(fd: str, glob: str, root: Path) -> dict[str, object]:
    r = subprocess.run([fd, "--glob", "--color=never", "--hidden", "--no-require-git", "--max-results", "1000",
                        "--full-path", "--", glob, str(root)], capture_output=True)
    lines = sorted(os.path.relpath(line.strip(), root).replace("\\", "/")
                   for line in r.stdout.decode("utf-8", "replace").splitlines() if line.strip())
    stderr = r.stderr.decode("utf-8", "replace").strip().replace(str(root), "<ROOT>")
    return {"exit": r.returncode, "results": lines, "stderr": stderr}


def main() -> None:
    fd, out_path = sys.argv[1], sys.argv[2]
    candidate = None
    if len(sys.argv) > 3:
        spec = importlib.util.spec_from_file_location("candidate_find", sys.argv[3])
        if spec and spec.loader:
            try:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                candidate = module._windows_full_path
            except ImportError:  # the candidate module needs the package; import it from there
                sys.path.insert(0, str(Path(sys.argv[3]).parents[3]))
                from minion_agent.tools.builtin.find import _windows_full_path as candidate
    root = Path(tempfile.mkdtemp(prefix="ce01-matrix-")).resolve()
    for rel in FILES:
        p = root.joinpath(*rel.split("/"))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x\n")
    windows = os.name == "nt"
    out: dict[str, object] = {
        "platform": "win32" if windows else "linux",
        "fd": subprocess.run([fd, "--version"], capture_output=True).stdout.decode().strip(),
        "corpus": FILES, "rows": {}}
    rows: dict[str, object] = out["rows"]  # type: ignore[assignment]
    for pattern in PATTERNS:
        e = effective(pattern)
        if not windows:
            rows[pattern] = {"text": e, "linux": run(fd, e, root)}
            continue
        texts = {"pi": e.replace("/", SEP), "rejected": rejected(e), "proposal": proposal(e)}
        if candidate is not None:
            texts["candidate"] = candidate(e)
        rows[pattern] = {name: {"text": text, **run(fd, text, root)} for name, text in texts.items()}
        rows[pattern]["oracle"] = oracle(fd, e, root)  # type: ignore[index]
        found = len(recursive_components(e))
        rows[pattern]["components"] = {  # type: ignore[index]
            "expected_by_hand": EXPECTED_COMPONENTS[pattern], "found": found,
            "agree": found == EXPECTED_COMPONENTS[pattern]}
    Path(out_path).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


main()
