"""Generate WP-13.1 builtin_tool canonical scenarios.

Expected values come from pinned-Pi authorities, never from the implementation under test:
- read text: pinned Pi read.ts text branch + Pi's own truncate.ts, executed by Node (piauth/);
- read images: the R005-A differential's Pi authority.json (pinned Pi + photon-node 0.3.4);
- ls truncation: Pi's own truncateHead (Node); collation order: R006-C v2 icu_lowercased order;
- fixed templates: quoted from pinned Pi source / spec/tools.md (R010-B, R002-A).
"""

import base64
import functools
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

CODE = Path(sys.argv[1])  # wp131-code worktree
DOCS = Path(sys.argv[2])  # wp131-docs worktree
PIAUTH = Path(sys.argv[3])  # node helper dir
AGENT = CODE / "conformance" / "agent"
FIX = AGENT / "fixtures" / "r005a-photon"
EVID = DOCS / "assurance/layers/data/13-wp131-ce-l13-wp131-01"
R005 = EVID / "r005-a-photon-differential"
PI = "b7bb00b936dbe21b8e160b3e89efdec361846699"
AUTH = "minion-agent-docs spec/tools.md WP-13.1 (master f46051fb)"


def content_bytes(spec):
    if "text" in spec:
        return spec["text"].encode("utf-8")
    if "base64" in spec:
        return base64.b64decode(spec["base64"])
    if "lines" in spec:
        t, n = spec["lines"]["template"], spec["lines"]["count"]
        return "\n".join(t.replace("{n}", str(i)) for i in range(1, n + 1)).encode()
    if "repeat" in spec:
        return (spec["repeat"]["unit"] * spec["repeat"]["times"]).encode()
    return (AGENT / "fixtures" / spec["fixture_file"]).read_bytes()


def node(script, payload):
    out = subprocess.run(
        ["node", "--experimental-strip-types", "--no-warnings", script, "-"],
        input=json.dumps(payload), capture_output=True, text=True, cwd=PIAUTH, check=True, encoding="utf-8",
    )
    return json.loads(out.stdout)


def pi_read_text(fixture, cases):
    """Expected read text/details from pinned Pi's read.ts text branch."""
    files = {e["path"]: content_bytes(e["file"]) for e in fixture if "file" in e}
    payload = [
        {"id": c["id"], "content_b64": base64.b64encode(files[c["file"]]).decode(),
         "path": c["path"], "offset": c.get("offset"), "limit": c.get("limit")}
        for c in cases
    ]
    return {r["id"]: r for r in node("gen_stdin.mjs", payload)}


def expectation(text, **extra):
    exp = {"is_error": extra.pop("is_error", False)}
    if len(text) > 4000:
        exp["text_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        exp["text_tail"] = text[-300:]
    else:
        exp["text"] = text
    exp.update(extra)
    return exp


def write(name, requirements, witnesses, notes, tool, cases, fixture=None, provider=None, options=None):
    doc = {"name": name, "family": "agent", "authority": AUTH, "pi_revision": PI,
           "requirements": requirements, "witnesses": witnesses, "notes": notes,
           "builtin_tool": {"tool": tool}}
    if fixture:
        doc["builtin_tool"]["fixture"] = fixture
    if provider:
        doc["builtin_tool"]["provider"] = provider
    if options:
        doc["builtin_tool"]["options"] = options
    doc["builtin_tool"]["cases"] = cases
    (AGENT / f"{name}.yaml").write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=False, width=100), encoding="utf-8", newline="\n")


def read_text_scenario(name, requirements, witnesses, notes, fixture, calls):
    pi = pi_read_text(fixture, calls)
    cases = []
    for c in calls:
        r = pi[c["id"]]
        args = {"path": c["path"]}
        for k in ("offset", "limit"):
            if c.get(k) is not None:
                args[k] = c[k]
        if r["is_error"]:
            exp = {"is_error": True, "text": r["text"], "details": {}}
        else:
            exp = expectation(r["text"], image=None, details=r["details"])
        cases.append({"id": c["id"], "arguments": args, "expect": exp})
    write(name, requirements, witnesses, notes, "read", cases, fixture=fixture)


# ---------------------------------------------------------------------------------------------
def main():
    # corpus fixtures (committed R005-A corpus: every file <= 1 MiB)
    if FIX.exists():
        shutil.rmtree(FIX)
    FIX.mkdir(parents=True)
    for f in sorted((R005 / "corpus").iterdir()):
        if f.name not in ("SHA256SUMS", "manifest.json"):
            shutil.copy(f, FIX / f.name)
    (FIX / "SOURCE.txt").write_text(
        "Copied unmodified from minion-agent-docs assurance/layers/data/13-wp131-ce-l13-wp131-01/\n"
        "r005-a-photon-differential/corpus/ (merged f46051fb; sha256 in its SHA256SUMS). The three\n"
        "files over 1 MiB are not committed there and are not used here.\n", encoding="utf-8", newline="\n")

    # ---- TOOL-025 read: text ------------------------------------------------------------------
    f100 = {"path": "data100.txt", "file": {"lines": {"count": 100, "template": "line {n}"}}}
    f3000 = {"path": "data3000.txt", "file": {"lines": {"count": 3000, "template": "row {n}"}}}
    wide = {"path": "wide.txt", "file": {"lines": {"count": 1000, "template": "x" * 100}}}
    read_text_scenario(
        "builtin-read-offset-limit-then-truncation-ordering", ["TOOL-025"],
        ["read_offset_limit_then_truncation_ordering"],
        "offset/limit select BEFORE head truncation. A caller limit that stops early appends Pi's "
        "'more lines' notice with NO details.truncation; automatic truncation (lines, then bytes) "
        "appends the 'Showing lines' notice and details.truncation, whose total_lines is the "
        "SELECTED range (2500), not the file (3000). Expected values: pinned Pi read.ts + truncate.ts.",
        [f100, f3000, wide],
        [{"id": "caller-limit-stops-early", "file": "data100.txt", "path": "data100.txt", "offset": 41, "limit": 20},
         {"id": "limit-reaches-eof-no-notice", "file": "data100.txt", "path": "data100.txt", "offset": 91, "limit": 20},
         {"id": "whole-file-no-notice", "file": "data100.txt", "path": "data100.txt"},
         {"id": "selected-range-then-line-truncation", "file": "data3000.txt", "path": "data3000.txt", "offset": 41, "limit": 2500},
         {"id": "byte-truncation", "file": "wide.txt", "path": "wide.txt"}])
    big_first = {"path": "big.txt", "file": {"text": "x" * 51201 + "\ntail\n"}}
    big_second = {"path": "second.txt", "file": {"text": "head\n" + "y" * 60000 + "\nz"}}
    read_text_scenario(
        "builtin-read-first-line-exceeds-byte-limit", ["TOOL-025"], ["read_first_line_exceeds_byte_limit"],
        "A selected first line over 50 KiB yields Pi's sed/head diagnostic (NOT empty content) and "
        "details.truncation.first_line_exceeds_limit = true. The diagnostic quotes the RAW path "
        "argument, not the resolved path (read.ts:300). A fractional offset makes read.ts:299 "
        "measure allLines[<fraction>] = undefined, and Node throws its own TypeError (IMPL-C010).",
        [big_first, big_second],
        [{"id": "first-line-over-limit", "file": "big.txt", "path": "big.txt"},
         {"id": "raw-path-quoted", "file": "big.txt", "path": "./big.txt"},
         {"id": "offset-selects-huge-line", "file": "second.txt", "path": "second.txt", "offset": 2},
         {"id": "fractional-offset-undefined-line", "file": "second.txt", "path": "second.txt", "offset": 2.5}])
    read_text_scenario(
        "builtin-read-offset-out-of-bounds", ["TOOL-025"], ["read_offset_out_of_bounds"],
        "An offset at or past the line count (after the Math.max(0, offset - 1) coercion) is the one "
        "rejected offset: Pi's 'Offset N is beyond end of file (M lines total)' with N rendered by "
        "Number::toString. A trailing newline makes an empty last line, which IS addressable.",
        [{"path": "three.txt", "file": {"text": "a\nb\n"}}],
        [{"id": "last-empty-line-addressable", "file": "three.txt", "path": "three.txt", "offset": 3},
         {"id": "past-end", "file": "three.txt", "path": "three.txt", "offset": 4},
         {"id": "fractional-past-end", "file": "three.txt", "path": "three.txt", "offset": 5.5},
         {"id": "fractional-inside", "file": "three.txt", "path": "three.txt", "offset": 3.5}])
    ten = {"path": "ten.txt", "file": {"lines": {"count": 10, "template": "L{n}"}}}
    read_text_scenario(
        "builtin-read-fractional-and-negative-numeric-inputs", ["TOOL-025"],
        ["read_fractional_and_negative_numeric_inputs"],
        "offset/limit are unconstrained JSON numbers with JS arithmetic: a falsy offset (0) starts at "
        "line 1; a negative offset clamps to 0; Array.prototype.slice truncates fractions and counts "
        "a NEGATIVE end from the end of the array (limit=-3 selects lines 1-7, IMPL-C008); notices "
        "render fractional values with Number::toString.",
        [ten],
        [{"id": f"offset-{o}-limit-{l}", "file": "ten.txt", "path": "ten.txt", "offset": o, "limit": l}
         for o, l in [(2.5, -1), (None, -3), (2.5, -5), (3, 2.5), (0, -100), (-5, 2), (0, 3), (None, 0)]])
    read_text_scenario(
        "builtin-read-text-decoding-matches-node-utf8", ["TOOL-025"], ["read_text_decoding_matches_node_utf8"],
        "Text is Node's Buffer.toString('utf-8'): every maximal invalid subpart becomes one U+FFFD, a "
        "BOM is kept, and CR/CRLF are NOT translated (IMPL-C005). Line splitting is on '\\n' only.",
        [{"path": "mixed.bin", "file": {"base64": base64.b64encode(
            b"\xef\xbb\xbfone\r\ntwo\rthree\n\xe2\x82 \xf0\x80\x80A \xed\xa0\x80 \xc3\xa9\xff").decode()}}],
        [{"id": "decode", "file": "mixed.bin", "path": "mixed.bin"},
         {"id": "decode-offset", "file": "mixed.bin", "path": "mixed.bin", "offset": 2}])

    # ---- TOOL-025 read: images ---------------------------------------------------------------
    auth = json.loads((R005 / "results" / "authority.json").read_text(encoding="utf-8"))
    by_file = {r["file"]: r for r in auth["read_level"]}
    committed = {p.name for p in FIX.iterdir()}

    def image_case(fname, note=None, cid=None):
        a = by_file[fname]
        if not a["sniffed_mime"]:
            return None
        if a["ok"]:
            text = f"Read image file [{a['mime']}]" + "".join("\n" + h for h in a["hints"])
            if note:
                text += "\n" + note
            exp = {"is_error": False, "text": text,
                   "image": {"mime_type": a["mime"], "sha256": a["data_sha256"], "bytes": a["data_bytes"]},
                   "details": {}}
        else:
            text = f"Read image file [{a['sniffed_mime']}]\n{a['message']}"
            if note:
                text += "\n" + note
            exp = {"is_error": False, "text": text, "image": None, "details": {}}
        return {"id": cid or fname, "arguments": {"path": fname}, "expect": exp}

    NOTE = "[Current model does not support images. The image will be omitted from this request.]"
    fx = lambda *names: [{"path": n, "file": {"fixture_file": f"r005a-photon/{n}"}} for n in names]
    write("builtin-read-image-success-includes-image-for-non-vision-model", ["TOOL-025"],
          ["read_image_success_includes_image_for_non_vision_model"],
          "A model known NOT to accept images gets the non-vision note appended to the text AND the "
          "image block (never a substitution). A vision model, and a tool with no model knowledge "
          "(Pi: ctx.model undefined), get no note (IMPL-C001). Image bytes from pinned Pi (R005-A).",
          "read", [image_case("png_small_rgb.png", NOTE, "non-vision-model")],
          fixture=fx("png_small_rgb.png"), options={"model_supports_images": False})
    write("builtin-read-image-vision-or-unknown-model-no-note", ["TOOL-025"],
          ["read_image_success_includes_image_for_non_vision_model"],
          "Companion to the non-vision scenario: a vision model gets no note.",
          "read", [image_case("png_small_rgb.png", None, "vision-model")],
          fixture=fx("png_small_rgb.png"), options={"model_supports_images": True})
    write("builtin-read-image-unknown-model-no-note", ["TOOL-025"],
          ["read_image_success_includes_image_for_non_vision_model"],
          "Companion: no model knowledge at all (Pi's `!model` branch) gets no note.",
          "read", [image_case("png_small_rgb.png", None, "unknown-model")],
          fixture=fx("png_small_rgb.png"))
    write("builtin-read-image-bmp-converts-and-resizes", ["TOOL-025"], ["read_image_bmp_converts_and_resizes"],
          "A BMP wider than 2000 px converts to PNG, then resizes: the conversion hint (base MIME "
          "types, IMPL-C011) precedes the dimension hint (toFixed(2) scale). Bytes from pinned Pi.",
          "read", [image_case("bmp_2100x20.bmp")], fixture=fx("bmp_2100x20.bmp"))
    write("builtin-read-image-processing-failure-is-text-only-success", ["TOOL-025"],
          ["read_image_processing_failure_is_text_only_success"],
          "Sniff-positive inputs Photon cannot process are a TEXT-ONLY SUCCESS, not a tool error: a "
          "BMP conversion failure, an undecodable PNG, and an 8001x2 PNG whose resize target is 2000x0 "
          "(Math.round(0.4999)) so Photon's encode traps. The sniffed MIME is quoted and the "
          "non-vision note still appends.",
          "read", [image_case(n, NOTE) for n in ("bmp_truncated.bmp", "bad_png_truncated.png",
                                                  "png_8001x2.png", "bad_jpeg_soi_garbage.jpg")],
          fixture=fx("bmp_truncated.bmp", "bad_png_truncated.png", "png_8001x2.png", "bad_jpeg_soi_garbage.jpg"),
          options={"model_supports_images": False})
    corpus_names = sorted(n for n in by_file if n in committed)
    image_cases = [c for c in (image_case(n) for n in corpus_names) if c]
    write("builtin-read-image-differential-corpus-matches-pinned-photon-0-3-4", ["TOOL-025"],
          ["read_image_differential_corpus_matches_pinned_photon_0_3_4"],
          "Every sniff-positive file of the committed R005-A corpus, read through the real tool: text "
          "(MIME, hints or failure message) and image bytes must equal pinned Pi + photon-node 0.3.4 "
          "exactly (authority.json). The three corpus files over 1 MiB are exercised by the R005-A "
          "evidence itself, not here.",
          "read", image_cases, fixture=fx(*[c["id"] for c in image_cases]))
    write("builtin-read-image-auto-resize-disabled", ["TOOL-025"], ["read_image_auto_resize_disabled"],
          "autoResizeImages=false: no resize, no dimension hint; a BMP still converts (hint kept). "
          "png_2001x40 passes through unchanged (its own bytes); bmp_24's PNG equals Pi's conversion "
          "output (pinned Pi returned it unresized).",
          "read",
          [{"id": "png-unresized", "arguments": {"path": "png_2001x40.png"}, "expect": {
              "is_error": False, "text": "Read image file [image/png]",
              "image": {"mime_type": "image/png",
                        "sha256": hashlib.sha256((FIX / "png_2001x40.png").read_bytes()).hexdigest(),
                        "bytes": (FIX / "png_2001x40.png").stat().st_size}, "details": {}}},
           {"id": "bmp-converted", "arguments": {"path": "bmp_24.bmp"}, "expect": {
              "is_error": False, "text": "Read image file [image/png]\n[Image converted from image/bmp to image/png.]",
              "image": {"mime_type": "image/png", "sha256": by_file["bmp_24.bmp"]["data_sha256"],
                        "bytes": by_file["bmp_24.bmp"]["data_bytes"]}, "details": {}}}],
          fixture=fx("png_2001x40.png", "bmp_24.bmp"), options={"auto_resize_images": False})
    write("builtin-read-operation-aborted-template-preserved-verbatim", ["TOOL-025"],
          ["read_operation_aborted_template_preserved_verbatim"],
          "An already-aborted signal rejects with Pi's exact 'Operation aborted' before ANY ctx.fs call.",
          "read", [{"id": "pre-aborted", "signal": "pre_aborted", "arguments": {"path": "a.txt"},
                    "expect": {"is_error": True, "text": "Operation aborted", "details": {}, "fs_calls": []}}],
          fixture=[{"path": "a.txt", "file": {"text": "x"}}])

    # ---- TOOL-026 path pipeline ---------------------------------------------------------------
    write("builtin-read-leading-ascii-space-not-trimmed", ["TOOL-026"], ["read_leading_ascii_space_not_trimmed"],
          "No trim: ' x.txt' addresses the space-prefixed file. Exactly one leading '@' is stripped, so "
          "'@x.txt' reads x.txt and '@@x.txt' addresses the missing '@x.txt'.",
          "read",
          [{"id": "space-prefixed", "arguments": {"path": " x.txt"}, "expect": {"is_error": False, "text": "space", "details": {}}},
           {"id": "plain", "arguments": {"path": "x.txt"}, "expect": {"is_error": False, "text": "plain", "details": {}}},
           {"id": "at-stripped", "arguments": {"path": "@x.txt"}, "expect": {"is_error": False, "text": "plain", "details": {}}},
           {"id": "only-one-at-stripped", "arguments": {"path": "@@x.txt"}, "expect": {
               "is_error": True, "text": "Cannot access {abs:@x.txt}: no such file or directory", "details": {}}}],
          fixture=[{"path": " x.txt", "file": {"text": "space"}}, {"path": "x.txt", "file": {"text": "plain"}}])
    write("builtin-read-unicode-space-normalized", ["TOOL-026"], ["read_unicode_space_normalized"],
          "The closed Unicode space set (U+00A0, U+2000-U+200A, U+202F, U+205F, U+3000) becomes an ASCII "
          "space before resolution.",
          "read",
          [{"id": f"U+{ord(ch):04X}", "arguments": {"path": f"a{ch}b.txt"}, "expect": {"is_error": False, "text": "ok", "details": {}}}
           for ch in [" ", " ", " ", " ", " ", "　"]]
          + [{"id": "U+200B-not-in-set", "arguments": {"path": "a​b.txt"}, "expect": {
              "is_error": True, "text": "Cannot access {abs:a​b.txt}: no such file or directory", "details": {}}}],
          fixture=[{"path": "a b.txt", "file": {"text": "ok"}}])
    for tool in ("read", "ls"):
        write(f"builtin-{tool}-malformed-file-url-rejected-before-ctx-fs-access-as-invalid", ["TOOL-026", "TOOL-039"],
              ["malformed_file_url_rejected_before_ctx_fs_access_as_invalid"],
              "R002-A: a malformed file:// URL is rejected by the strict conversion at pipeline step 4, "
              "before ANY ctx.fs call, as 'Cannot access <path>: invalid path' where <path> is the "
              "step-4 input string (IMPL-C003).",
              tool, [{"id": u, "arguments": {"path": u}, "expect": {
                  "is_error": True, "text": f"Cannot access {u}: invalid path", "details": {}, "fs_calls": []}}
                  for u in ["file:///%ZZ", "file:///a%2Fb"]])

    # ---- TOOL-039 read error vocabulary --------------------------------------------------------
    phrases = {"not_found": "no such file or directory", "permission_denied": "permission denied",
               "not_directory": "not a directory", "is_directory": "is a directory", "invalid": "invalid path",
               "not_supported": "not supported by this provider", "unknown": "unknown filesystem error"}
    access_codes = ["not_found", "permission_denied", "not_directory", "invalid", "not_supported", "unknown"]
    read_codes = ["not_found", "not_directory", "invalid", "not_supported", "unknown"]
    fixture = [{"path": f"acc_{c}.txt", "file": {"text": "x"}} for c in access_codes]
    fixture += [{"path": f"rd_{c}.txt", "file": {"text": "x"}} for c in read_codes + ["permission_denied", "is_directory"]]
    fixture += [{"path": "sub", "dir": True}, {"path": "dangling", "symlink": "missing-target"}]
    cases = [{"id": f"access-{c}", "arguments": {"path": f"acc_{c}.txt"}, "expect": {
        "is_error": True, "text": f"Cannot access {{abs:acc_{c}.txt}}: {phrases[c]}", "details": {}}} for c in access_codes]
    read_site = lambda c: "Cannot read" if c in ("is_directory", "not_supported") else "Cannot access"
    cases += [{"id": f"read-{c}", "arguments": {"path": f"rd_{c}.txt"}, "expect": {
        "is_error": True, "text": f"{read_site(c)} {{abs:rd_{c}.txt}}: {phrases[c]}", "details": {}}}
        for c in read_codes + ["permission_denied", "is_directory"]]
    cases += [
              {"id": "directory-is-directory", "arguments": {"path": "sub"}, "expect": {
                  "is_error": True, "text": "Cannot read {abs:sub}: is a directory", "details": {}}},
              {"id": "real-missing-file", "arguments": {"path": "missing.txt"}, "expect": {
                  "is_error": True, "text": "Cannot access {abs:missing.txt}: no such file or directory", "details": {}}},
              {"id": "dangling-symlink-fails-the-access-check", "arguments": {"path": "dangling"}, "expect": {
                  "is_error": True, "text": "Cannot access {abs:dangling}: no such file or directory", "details": {}}}]
    write("builtin-read-error-text-matches-r010b-closed-vocabulary-per-fserrorcode", ["TOOL-039", "TOOL-025"],
          ["read_error_text_matches_r010b_closed_vocabulary_per_fserrorcode"],
          "R010-B: each FsErrorCode maps to its closed cause phrase. The access step (file_info) is "
          "the 'Cannot access' site. A failed content read is 'Cannot read' only for is_directory and "
          "not_supported; any other code is reported at the access site, because Pi's "
          "symlink-following access(R_OK) would have failed first (L13-WP131-C012). A directory is "
          "'Cannot read <path>: is a directory'; a dangling symlink is 'Cannot access ... no such file "
          "or directory'. <path> is the resolved absolute path (IMPL-C003). details stays {}.",
          "read", cases, fixture=fixture,
          provider={"file_info": [{"path": f"acc_{c}.txt", "error": c} for c in access_codes],
                    "read_binary_file": [{"path": f"rd_{c}.txt", "error": c} for c in read_codes + ["permission_denied", "is_directory"]]})
    write("builtin-read-provider-without-exec-007-reads-normally", ["TOOL-025"],
          ["read_does_not_require_exec_007"],
          "L13-WP131-C012: read uses only core ctx.fs operations (file_info, read_binary_file), so a "
          "provider that reports not_supported for the additive EXEC-007 extension still reads text "
          "and images normally; ls, which needs EXEC-007, reports its own not_supported text.", "read",
          [{"id": "text", "arguments": {"path": "a.txt"}, "expect": {"is_error": False, "text": "hello", "details": {},
                                                                    "fs_calls": ["file_info a.txt", "read_binary_file a.txt"]}},
           image_case("png_small_rgb.png")],
          fixture=[{"path": "a.txt", "file": {"text": "hello"}}] + fx("png_small_rgb.png"),
          provider={"without_exec_007": True})

    # ---- TOOL-028 ls ------------------------------------------------------------------------
    files = lambda *names: [{"path": n, "file": {"text": "x"}} for n in names]
    write("builtin-ls-lazy-cap-never-probes-beyond-limit", ["TOOL-028"], ["ls_lazy_cap_never_probes_beyond_limit"],
          "EXEC-007 lazy cap: sorted [a_ok, z_slow], limit=1 -> only a_ok is probed.", "ls",
          [{"id": "cap", "arguments": {"limit": 1}, "expect": {
              "is_error": False, "text": "a_ok\n\n[1 entries limit reached. Use limit=2 for more]",
              "details": {"entry_limit_reached": 1}, "probed_entries": [".", "a_ok"]}}],
          fixture=files("z_slow", "a_ok"), provider={"list_dir_raw": [{"path": ".", "names": ["z_slow", "a_ok"]}]})
    write("builtin-ls-entry-limit-checked-before-next-probe", ["TOOL-028"], ["ls_entry_limit_checked_before_next_probe"],
          "The cap is checked BEFORE each probe: with limit=1 the cap is reported even though the next "
          "entry's own probe would have failed (it is never probed).", "ls",
          [{"id": "cap-before-probe", "arguments": {"limit": 1}, "expect": {
              "is_error": False, "text": "a\n\n[1 entries limit reached. Use limit=2 for more]",
              "details": {"entry_limit_reached": 1}, "probed_entries": [".", "a"]}}],
          fixture=files("a", "b"), provider={"probe_dir_entry": [{"path": "b", "error": "not_found"}]})
    write("builtin-ls-zero-limit-on-nonempty-dir-no-details", ["TOOL-028"], ["ls_zero_limit_on_nonempty_dir_no_details"],
          "limit <= 0 on a non-empty directory: the cap fires before any entry, zero results -> "
          "'(empty directory)' with no details (Pi returns before building details).", "ls",
          [{"id": f"limit-{l}", "arguments": {"limit": l}, "expect": {
              "is_error": False, "text": "(empty directory)", "details": {}}} for l in (0, -1)]
          + [{"id": "empty-dir", "arguments": {"path": "empty"}, "expect": {
              "is_error": False, "text": "(empty directory)", "details": {}}}],
          fixture=files("a", "b") + [{"path": "empty", "dir": True}])
    write("builtin-ls-fractional-limit-verbatim", ["TOOL-028"], ["ls_fractional_limit_verbatim"],
          "limit=1.5 lists 2 entries; entry_limit_reached and both notice numbers are rendered verbatim "
          "(1.5 and 3), never rounded, never the listed count.", "ls",
          [{"id": "fractional", "arguments": {"limit": 1.5}, "expect": {
              "is_error": False, "text": "a\nb\n\n[1.5 entries limit reached. Use limit=3 for more]",
              "details": {"entry_limit_reached": 1.5}}}],
          fixture=files("a", "b", "c"))
    write("builtin-ls-broken-symlink-entry-skipped", ["TOOL-028"], ["ls_broken_symlink_entry_skipped"],
          "A broken symlink fails its (symlink-following) probe and is skipped, not counted.", "ls",
          [{"id": "skipped", "arguments": {}, "expect": {"is_error": False, "text": "a\nz", "details": {}}}],
          fixture=files("a", "z") + [{"path": "dangling", "symlink": "missing-target"}])
    write("builtin-ls-symlinked-entries-follow-target-kind", ["TOOL-028"], ["ls_symlinked_entries_follow_target_kind"],
          "A symlink to a directory is listed 'name/'; a symlink to a file is listed 'name'.", "ls",
          [{"id": "follow", "arguments": {}, "expect": {"is_error": False, "text": "d/\nf\nld/\nlf", "details": {}}}],
          fixture=[{"path": "d", "dir": True}, {"path": "f", "file": {"text": "x"}},
                   {"path": "ld", "symlink": "d"}, {"path": "lf", "symlink": "f"}])
    write("builtin-ls-special-entry-listed-without-slash", ["TOOL-028"], ["ls_special_entry_listed_without_slash"],
          "An entry whose probe kind is `other` (a FIFO or other special file; a provider stand-in "
          "here) is listed without '/'.", "ls",
          [{"id": "other", "arguments": {}, "expect": {"is_error": False, "text": "a\nfifo", "details": {}}}],
          fixture=files("a", "fifo"), provider={"probe_dir_entry": [{"path": "fifo", "kind": "other"}]})
    write("builtin-ls-path-symlink-to-directory-is-listed", ["TOOL-028"], ["ls_path_symlink_to_directory_is_listed"],
          "`path` naming a symlink to a directory lists the target's entries.", "ls",
          [{"id": "alias", "arguments": {"path": "alias"}, "expect": {"is_error": False, "text": "x\ny", "details": {}}}],
          fixture=[{"path": "real", "dir": True}, {"path": "real/x", "file": {"text": "1"}},
                   {"path": "real/y", "file": {"text": "2"}}, {"path": "alias", "symlink": "real"}])
    write("builtin-ls-missing-path-and-broken-link-path-not-found", ["TOOL-028"],
          ["ls_missing_path_and_broken_link_path_not_found"],
          "A missing path and a path that is a broken symlink both report Pi's 'Path not found: <path>' "
          "with the resolved absolute path.", "ls",
          [{"id": "missing", "arguments": {"path": "nope"}, "expect": {"is_error": True, "text": "Path not found: {abs:nope}", "details": {}}},
           {"id": "broken-link", "arguments": {"path": "dangling"}, "expect": {"is_error": True, "text": "Path not found: {abs:dangling}", "details": {}}}],
          fixture=[{"path": "dangling", "symlink": "missing-target"}])
    write("builtin-ls-file-path-not-a-directory", ["TOOL-028"], ["ls_file_path_not_a_directory"],
          "A regular file path reports Pi's 'Not a directory: <path>'.", "ls",
          [{"id": "file", "arguments": {"path": "f"}, "expect": {"is_error": True, "text": "Not a directory: {abs:f}", "details": {}}}],
          fixture=files("f"))
    write("builtin-ls-enumeration-failure-cannot-read-directory", ["TOOL-028", "TOOL-039"],
          ["ls_enumeration_failure_cannot_read_directory"],
          "A list_dir_raw failure is Pi's 'Cannot read directory: ' wrapper with the R010-B cause phrase "
          "in place of Node's raw message.", "ls",
          [{"id": c, "arguments": {"path": f"d_{c}"}, "expect": {
              "is_error": True, "text": f"Cannot read directory: {phrases[c]}", "details": {}}}
           for c in ("permission_denied", "not_found", "unknown")],
          fixture=[{"path": f"d_{c}", "dir": True} for c in ("permission_denied", "not_found", "unknown")],
          provider={"list_dir_raw": [{"path": f"d_{c}", "error": c} for c in ("permission_denied", "not_found", "unknown")]})
    write("builtin-ls-provider-without-extension-not-supported", ["TOOL-028", "TOOL-039"],
          ["ls_provider_without_extension_not_supported"],
          "A provider lacking EXEC-007 is reported with the R010-B vocabulary, not disguised as a "
          "missing path.", "ls",
          [{"id": "no-ext", "arguments": {}, "expect": {
              "is_error": True, "text": "Cannot access {abs:.}: not supported by this provider", "details": {}}}],
          fixture=files("a"), provider={"without_exec_007": True})
    write("builtin-ls-pre-aborted-signal", ["TOOL-028"], ["ls_pre_aborted_signal"],
          "An already-aborted signal rejects with 'Operation aborted' before any ctx.fs call.", "ls",
          [{"id": "pre-aborted", "signal": "pre_aborted", "arguments": {}, "expect": {
              "is_error": True, "text": "Operation aborted", "details": {}, "fs_calls": []}}],
          fixture=files("a"))

    # byte truncation: 300 names of 180 chars; expected listing via Pi's own truncateHead
    names = [f"n{i:03d}" + "x" * 176 for i in range(300)]
    trunc = node("trunc_stdin.mjs", {"content": "\n".join(names)})
    listing = trunc["content"]
    trunc_details = {"truncated": True, "truncated_by": trunc["truncatedBy"], "total_lines": trunc["totalLines"],
                     "total_bytes": trunc["totalBytes"], "first_line_exceeds_limit": trunc["firstLineExceedsLimit"]}
    write("builtin-ls-byte-truncation-then-notice", ["TOOL-028"], ["ls_byte_truncation_then_notice"],
          "A listing over 50 KiB is head-truncated (whole lines, no line ceiling) and gets "
          "'[50.0KB limit reached]' plus details.truncation. Expected listing: Pi's own truncateHead.",
          "ls", [{"id": "bytes", "arguments": {}, "expect": expectation(
              listing + "\n\n[50.0KB limit reached]", details={"truncation": trunc_details})}],
          fixture=files(*names))
    capped = names[:290]
    trunc2 = node("trunc_stdin.mjs", {"content": "\n".join(capped)})
    d2 = {"truncated": True, "truncated_by": trunc2["truncatedBy"], "total_lines": trunc2["totalLines"],
          "total_bytes": trunc2["totalBytes"], "first_line_exceeds_limit": trunc2["firstLineExceedsLimit"]}
    write("builtin-ls-both-notices-in-order", ["TOOL-028"], ["ls_both_notices_in_order"],
          "Entry cap and byte ceiling both hit: notices joined by '. ' in that order inside one bracket.",
          "ls", [{"id": "both", "arguments": {"limit": 290}, "expect": expectation(
              trunc2["content"] + "\n\n[290 entries limit reached. Use limit=580 for more. 50.0KB limit reached]",
              details={"entry_limit_reached": 290, "truncation": d2})}],
          fixture=files(*names))

    # collation (R006-C): scripted raw enumeration and probes, so every name is portable
    v2 = json.loads((EVID / "r006-c-differential-v2/harness/corpus2.json").read_text(encoding="utf-8"))["strings"]
    matrix = json.loads((EVID / "r006-c-differential-v2/results/python2.json").read_text(encoding="utf-8"))["icu_lowercased"]["matrix"]

    def collation(name, witnesses, notes, runs):
        cases = []
        for cid, raw in runs:
            idx = [v2.index(n) for n in raw]
            # stable sort of THIS enumeration by the recorded pinned-ICU comparison matrix
            expected = sorted(range(len(raw)), key=functools.cmp_to_key(lambda i, j: matrix[idx[i]][idx[j]]))
            cases.append({"id": cid, "arguments": {"path": "d"}, "expect": {
                "is_error": False, "text": "\n".join(raw[i] for i in expected), "details": {}}})
        names_all = sorted({n for _, raw in runs for n in raw})
        write(name, ["TOOL-028", "TOOL-040"], witnesses, notes, "ls", cases,
              fixture=[{"path": "d", "dir": True}],
              provider={"list_dir_raw": [{"path": "d", "names": runs[0][1]}],
                        "probe_dir_entry": [{"path": f"d/{n}", "kind": "file"} for n in names_all]})

    collation("builtin-ls-collation-r006c-corpus-order", ["ls_collation_r006c_corpus_order"],
              "The 24-name Part 6 corpus in its recorded enumeration order sorts to the R006-C order "
              "(pinned PyICU/ICU 78.3, en-001, TERTIARY, NUMERIC off, CASE_FIRST off, NORMALIZATION on, "
              "ICU root lowercase keys; r006-c-differential-v2 icu_lowercased).",
              [("corpus", v2[:24])])
    # case ties need a separate listing per enumeration order
    for cid, raw in [("order-a", ["apple", "Apple", "APPLE"]), ("order-b", ["APPLE", "apple", "Apple"])]:
        collation(f"builtin-ls-collation-case-ties-keep-enumeration-order-{cid}",
                  ["ls_collation_case_ties_keep_enumeration_order"],
                  "Keys that compare equal (apple/Apple/APPLE lowercase identically) keep list_dir_raw "
                  "order: the sort is stable.", [(cid, raw)])
    for cid, raw in [("order-a", ["ậ", "ậ"]), ("order-b", ["ậ", "ậ"])]:
        collation(f"builtin-ls-collation-canonical-equivalents-tie-{cid}", ["ls_collation_canonical_equivalents_tie"],
                  "A non-FCD canonically-equivalent pair compares equal only with NORMALIZATION_MODE on, so "
                  "it keeps enumeration order.", [(cid, raw)])
    collation("builtin-ls-lowercase-key-uses-pinned-icu-root-mapping", ["ls_lowercase_key_uses_pinned_icu_root_mapping"],
              "Case-mapping witnesses (final sigma in two positions, U+0130, U+1E9E, U+01C5, U+01C4) among "
              "ASCII neighbours sort by the pinned ICU root lowercase keys (R006-C v2).",
              [("case-mapping", v2[30:36] + ["strasse", "file1", "apple"])])


def pinned_icu_order(names):
    """Expected order straight from the pinned engine (PyICU 2.16.2 / ICU 78.3, R006-C settings)."""
    import os
    if os.environ.get("MINION_AGENT_ICU_BIN"):
        os.add_dll_directory(os.environ["MINION_AGENT_ICU_BIN"])
    import icu
    assert (icu.VERSION, icu.ICU_VERSION) == ("2.16.2", "78.3")
    A, V = icu.UCollAttribute, icu.UCollAttributeValue
    c = icu.Collator.createInstance(icu.Locale("en-001"))
    for attr, val in ((A.STRENGTH, V.TERTIARY), (A.NUMERIC_COLLATION, V.OFF), (A.CASE_FIRST, V.OFF), (A.NORMALIZATION_MODE, V.ON)):
        c.setAttribute(attr, val)
    root = icu.Locale.getRoot()
    keys = [str(icu.UnicodeString(n).toLower(root)) for n in names]
    order = sorted(range(len(names)), key=functools.cmp_to_key(lambda i, j: int(c.compare(keys[i], keys[j]))))
    return [names[i] for i in order]


def post_unicode_15_scenario():
    raw = ["a", "Ɤ", "ɤ", "𐵐", "𐵰", "Ᲊ", "ᲊ"]
    write("builtin-ls-lowercase-key-post-unicode-15-mappings", ["TOOL-028", "TOOL-040"],
          ["ls_lowercase_key_uses_pinned_icu_root_mapping"],
          "Discriminating witness for the key function: case pairs added after Unicode 15.1 (U+A7CB/"
          "U+0264, Garay U+10D50/U+10D70, U+1C89/U+1C8A) lowercase to the SAME key only with ICU 78.3 "
          "(Unicode 17), so each pair ties and keeps enumeration order; a host-language lowercase "
          "that predates them sorts them apart. Expected order computed by the pinned PyICU/ICU 78.3 "
          "engine itself.", "ls",
          [{"id": "post-15-pairs", "arguments": {"path": "d"}, "expect": {
              "is_error": False, "text": chr(10).join(pinned_icu_order(raw)), "details": {}}}],
          fixture=[{"path": "d", "dir": True}],
          provider={"list_dir_raw": [{"path": "d", "names": raw}],
                    "probe_dir_entry": [{"path": f"d/{n}", "kind": "file"} for n in raw]})


if __name__ == "__main__":
    post_unicode_15_scenario()
    main()
