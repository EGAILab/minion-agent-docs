"""#74: generate the five hardening scenarios (A-E) from the pinned-Pi authority outputs only.

    python gen_scenarios.py <minion-agent worktree> <this evidence dir> <regenerated corpus dir>

Expected values come from results/authority.json (pinned Pi processImage + photon-node 0.3.4) and
results/text_authority.json (pinned Pi read.ts text branch); never from an implementation under test.
"""

import base64
import hashlib
import json
import shutil
import sys
from pathlib import Path

import yaml

CODE = Path(sys.argv[1])
EVID = Path(sys.argv[2])
CORPUS = Path(sys.argv[3])
AGENT = CODE / "conformance" / "agent"
FIXDIR = "h74-wp131-hardening"
FIX = AGENT / "fixtures" / FIXDIR
PI = "b7bb00b936dbe21b8e160b3e89efdec361846699"
AUTH = "minion-agent-docs spec/tools.md WP-13.1 (master ed72c96f); pinned-Pi authority run of minion-agent#74"

auth = {r["file"]: r for r in json.loads((EVID / "results" / "authority.json").read_text("utf-8"))["read_level"]}
text_auth = {r["file"]: r for r in json.loads((EVID / "results" / "text_authority.json").read_text("utf-8"))["results"]}
sums = dict(reversed(line.split("  ")) for line in (EVID / "corpus.sha256").read_text("utf-8").splitlines())


def corpus_bytes(name):
    data = (CORPUS / name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == sums[name], name
    return data


def image_expect(a):
    size = a["data_bytes"]
    assert a["data_base64_len"] == 4 * ((size + 2) // 3), a["file"]
    return {"mime_type": a["mime"], "sha256": a["data_sha256"], "bytes": size, "base64_len": a["data_base64_len"],
            "canonical_base64": True}


def image_case(name, cid=None):
    a = auth[name]
    assert a["ok"], name
    return {"id": cid or name, "arguments": {"path": name}, "expect": {
        "is_error": False, "text": f"Read image file [{a['mime']}]" + "".join("\n" + h for h in a["hints"]),
        "image": image_expect(a), "details": {}}}


def fixture_file(name):
    FIX.mkdir(parents=True, exist_ok=True)
    (FIX / name).write_bytes(corpus_bytes(name))
    return {"path": name, "file": {"fixture_file": f"{FIXDIR}/{name}"}}


def inline(name):
    return {"path": name, "file": {"base64": base64.b64encode(corpus_bytes(name)).decode()}}


def write(name, witnesses, notes, cases, fixture):
    doc = {"name": name, "family": "agent", "authority": AUTH, "pi_revision": PI, "requirements": ["TOOL-025"],
           "witnesses": witnesses, "notes": notes,
           "builtin_tool": {"tool": "read", "fixture": fixture, "cases": cases}}
    (AGENT / f"{name}.yaml").write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=False, width=100),
                                        encoding="utf-8", newline="\n")
    print("wrote", name)


def main():
    if FIX.exists():
        shutil.rmtree(FIX)
    # A -- conversion hint names the FINAL MIME after resize (image-process.ts conversionHint(from, resized.mimeType)).
    a = image_case("bmp1_noise_2100x2100.bmp")
    assert a["expect"]["image"]["mime_type"] == "image/jpeg"
    assert "[Image converted from image/bmp to image/jpeg.]" in a["expect"]["text"]
    write("builtin-read-image-bmp-conversion-hint-names-final-mime-after-jpeg-resize",
          ["read_image_bmp_conversion_hint_names_final_mime_after_jpeg_resize"],
          "A 1-bit noise BMP wider than 2000 px converts to PNG; Lanczos resizing to 2000x2000 turns it into "
          "high-entropy grayscale whose PNG candidate exceeds the base64 ceiling, so a JPEG candidate wins. Pinned "
          "Pi's conversion hint names the FINAL MIME ('to image/jpeg'), not the intermediate PNG "
          "(image-process.ts: conversionHint(normalized.convertedFrom, resized.mimeType)). #74 item A.",
          [a], [fixture_file("bmp1_noise_2100x2100.bmp")])
    # B -- toFixed(2) rounds the exact binary64 value (W/2000 lies below the decimal tie).
    b_names = ["png_rgb_2150x4.png", "png_rgb_2650x4.png", "png_rgb_3050x4.png"]
    b_cases = [image_case(n) for n in b_names]
    for c, want in zip(b_cases, ("1.07", "1.32", "1.52")):
        assert f"Multiply coordinates by {want} " in c["expect"]["text"], c["id"]
    write("builtin-read-image-scale-hint-to-fixed-rounds-exact-binary-value",
          ["read_image_scale_hint_to_fixed_rounds_exact_binary_value"],
          "Widths 2150, 2650 and 3050 resize to width 2000; the scale W/2000 is a decimal half-cent tie whose "
          "binary64 value lies just BELOW the tie, so ECMAScript toFixed(2) rounds DOWN: 1.07, 1.32, 1.52 (not "
          "1.08, 1.33, 1.53, which rounding binary64(scale * 100) would give). #74 item B.",
          b_cases, [inline(n) for n in b_names])
    # C -- the FIRST eligible candidate wins in order PNG, JPEG 80, 85, 70, 55, 40.
    c = image_case("png1_noise_2100x2100.png")
    assert c["expect"]["image"]["mime_type"] == "image/jpeg"
    write("builtin-read-image-first-eligible-jpeg-quality-wins",
          ["read_image_first_eligible_jpeg_quality_wins"],
          "A 1-bit noise PNG wider than 2000 px resizes to 2000x2000 high-entropy grayscale: the PNG candidate "
          "exceeds the base64 ceiling while BOTH JPEG quality 80 and 85 fit, so the exact bytes are the quality-80 "
          "candidate -- the first eligible in pinned Pi's order [80, 85, 70, 55, 40], not the smallest and not "
          "another order. #74 item C (a BMP source reaching the same path is item A).",
          [c], [fixture_file("png1_noise_2100x2100.png")])
    # D -- the no-resize fast path requires ceil(n/3)*4 STRICTLY below 4,718,592.
    d_names = ["png_small_rgb_padded_3538941.png", "png_small_rgb_padded_3538942.png"]
    d_cases = [image_case(n) for n in d_names]
    assert d_cases[0]["expect"]["image"]["bytes"] == 3538941 and d_cases[0]["expect"]["text"] == "Read image file [image/png]"
    assert "displayed at 8x5" in d_cases[1]["expect"]["text"]
    write("builtin-read-image-no-resize-fast-path-exact-base64-cutoff",
          ["read_image_no_resize_fast_path_exact_base64_cutoff"],
          "The same 8x5 PNG padded with trailing zeros (Photon decodes it). At 3,538,941 bytes the base64 length "
          "4,718,588 is below the 4.5 MiB ceiling: the INPUT bytes pass through unchanged, no hint. At 3,538,942 "
          "bytes it equals 4,718,592 (not strictly below): the image is re-encoded at the same size, "
          "wasResized, with the dimension hint 'displayed at 8x5 ... 1.00'. #74 item D (the owner's 3,538,944 "
          "also takes the resize branch; recorded in the authority run).",
          d_cases, [fixture_file(n) for n in d_names])
    # E -- acTL before the first IDAT: not a supported image, so read takes the TEXT branch.
    t = text_auth["apng_actl_before_idat.png"]
    assert t["sniffed_mime"] is None and t["details"] is None
    e_after = image_case("png_actl_after_idat.png")
    assert e_after["expect"]["image"]["mime_type"] == "image/png"
    write("builtin-read-animated-png-control-chunk-before-idat-is-not-an-image",
          ["read_animated_png_control_chunk_before_idat_is_not_an_image"],
          "mime.ts isAnimatedPng: an acTL chunk BEFORE the first IDAT makes the sniff return null, so pinned Pi "
          "reads the file through the TEXT branch (Node utf-8 decoding of the raw bytes, no image block). The "
          "same chunk AFTER IDAT is not seen by the walk, which stops at IDAT: still image/png. #74 item E.",
          [{"id": "actl-before-idat", "arguments": {"path": "apng_actl_before_idat.png"},
            "expect": {"is_error": False, "text": t["text"], "image": None, "details": {}}},
           e_after],
          [inline("apng_actl_before_idat.png"), inline("png_actl_after_idat.png")])


main()
