"""Generate the R005-A differential corpus.

Inputs only: the generator is not a semantic authority. Every file is committed with its sha256, so
the evidence does not depend on regenerating it bit-identically.
"""

import io
import json
import random
import struct
import sys
import zlib
from pathlib import Path

from PIL import Image

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
rng = random.Random(20260924)
MANIFEST = []
MAX_B64 = int(4.5 * 1024 * 1024)  # Pi DEFAULT_MAX_BYTES (base64 payload)


def add(name, data, category, intent):
    (OUT / name).write_bytes(data)
    MANIFEST.append({"file": name, "category": category, "intent": intent, "bytes": len(data)})


def gradient(w, h, mode="RGB"):
    img = Image.new("RGB", (w, h))
    img.putdata([((x * 7) % 256, (y * 5) % 256, ((x + y) * 3) % 256) for y in range(h) for x in range(w)])
    return img.convert(mode) if mode != "RGB" else img


def noise(w, h, mode="RGB"):
    return Image.frombytes(mode, (w, h), rng.randbytes(w * h * len(mode)))


def enc(img, fmt, **kw):
    b = io.BytesIO()
    img.save(b, fmt, **kw)
    return b.getvalue()


def png_chunk(t, d):
    return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)


def pad_png_to(data, total):
    """Insert a private ancillary chunk before IEND so the file is exactly `total` bytes."""
    iend = data.rindex(b"IEND") - 4
    need = total - len(data) - 12
    assert need >= 0, (total, len(data))
    return data[:iend] + png_chunk(b"prVt", b"\x00" * need) + data[iend:]


def exif_bytes(orientation, big_endian=False):
    if big_endian:
        tiff = b"MM\x00\x2a" + struct.pack(">I", 8) + struct.pack(">H", 1) + struct.pack(">HHII", 0x0112, 3, 1, orientation << 16) + b"\x00\x00\x00\x00"
    else:
        tiff = b"II\x2a\x00" + struct.pack("<I", 8) + struct.pack("<H", 1) + struct.pack("<HHII", 0x0112, 3, 1, orientation) + b"\x00\x00\x00\x00"
    return b"Exif\x00\x00" + tiff


def jpeg_with_app1(img, app1_payload, quality=92):
    base = enc(img, "JPEG", quality=quality)
    seg = b"\xff\xe1" + struct.pack(">H", len(app1_payload) + 2) + app1_payload
    return base[:2] + seg + base[2:]


# ---- PNG ------------------------------------------------------------------------------------------
add("png_small_rgb.png", enc(gradient(8, 5), "PNG"), "png", "no-resize fast path")
rgba = gradient(64, 48, "RGBA"); rgba.putalpha(Image.linear_gradient("L").resize((64, 48)))
add("png_rgba_alpha.png", enc(rgba, "PNG"), "png", "alpha channel, no-resize")
add("png_gray.png", enc(gradient(40, 30, "L"), "PNG"), "png", "grayscale decode")
add("png_palette.png", enc(gradient(40, 30).convert("P", palette=Image.ADAPTIVE, colors=16), "PNG"), "png", "palette decode")
add("png_gray16.png", enc(gradient(40, 30, "L").convert("I;16"), "PNG"), "png", "16-bit grayscale decode")
add("png_2000x2000.png", enc(Image.new("RGB", (2000, 2000), (10, 120, 200)), "PNG", optimize=True), "boundary", "exactly max dimensions: no resize")
add("png_2001x40.png", enc(gradient(2001, 40), "PNG"), "boundary", "width 1 over max: resize by width")
add("png_40x2001.png", enc(gradient(40, 2001), "PNG"), "boundary", "height 1 over max: resize by height")
add("png_4000x1001.png", enc(gradient(4000, 1001), "PNG"), "js-semantics", "Math.round(500.5)=501 target height")
add("png_8001x2.png", enc(gradient(8001, 2), "PNG"), "js-semantics", "extreme aspect: target height round(0.4998)=0 -> Photon traps on zero dimension -> resize fails")
add("png_2250x100.png", enc(gradient(2250, 100), "PNG"), "js-semantics", "scale 1.125: toFixed(2) -> 1.13 in the dimension hint")
small_noise = enc(noise(300, 300), "PNG")
below = MAX_B64 // 4 * 3 - 3  # ceil(n/3)*4 == MAX_B64 - 4 < MAX_B64
add("png_size_just_below.png", pad_png_to(small_noise, below), "boundary", "base64 size just below maxBytes: no resize")
add("png_size_at_limit.png", pad_png_to(small_noise, below + 1), "boundary", "base64 size == maxBytes: resize path at same dimensions")
add("png_noise_2600.png", enc(noise(2600, 2600), "PNG", compress_level=1), "candidates", "resize to 2000x2000; PNG candidate too large, JPEG chosen")
add("png_noise_256.png", enc(noise(256, 256), "PNG"), "candidates", "core-level candidate-search cases (small maxBytes)")

# ---- JPEG -----------------------------------------------------------------------------------------
add("jpeg_small.jpg", enc(gradient(33, 17), "JPEG", quality=90), "jpeg", "baseline decode, no-resize")
add("jpeg_progressive.jpg", enc(gradient(33, 17), "JPEG", quality=90, progressive=True), "jpeg", "progressive decode")
add("jpeg_gray.jpg", enc(gradient(33, 17, "L"), "JPEG", quality=90), "jpeg", "grayscale decode")
add("jpeg_cmyk.jpg", enc(gradient(33, 17, "CMYK"), "JPEG", quality=90), "jpeg", "CMYK decode behavior")
add("jpeg_2600x40.jpg", enc(gradient(2600, 40), "JPEG", quality=90), "jpeg", "JPEG resize path")
exif_src = gradient(7, 3)
for o in range(1, 9):
    add(f"jpeg_exif_o{o}.jpg", enc(exif_src, "JPEG", quality=95, exif=exif_bytes(o)), "exif", f"EXIF orientation {o} (little-endian TIFF)")
add("jpeg_exif_o6_be.jpg", jpeg_with_app1(exif_src, exif_bytes(6, big_endian=True)), "exif", "EXIF orientation 6 (big-endian TIFF)")
add("jpeg_exif_o9.jpg", enc(exif_src, "JPEG", quality=95, exif=exif_bytes(9)), "exif", "invalid orientation 9 treated as 1")
add("jpeg_exif_o6_2600.jpg", enc(gradient(2600, 40), "JPEG", quality=90, exif=exif_bytes(6)), "exif", "rotation before resize")

# ---- WebP / GIF -----------------------------------------------------------------------------------
add("webp_lossy.webp", enc(gradient(33, 17), "WEBP", quality=80), "webp", "lossy decode")
add("webp_lossless.webp", enc(gradient(33, 17), "WEBP", lossless=True), "webp", "lossless decode")
add("webp_alpha.webp", enc(rgba, "WEBP", lossless=True), "webp", "alpha decode")
add("webp_exif_o6.webp", enc(exif_src, "WEBP", lossless=True, exif=exif_bytes(6)), "exif", "WebP EXIF orientation 6")
frames = [gradient(20, 10), gradient(20, 10).transpose(Image.FLIP_LEFT_RIGHT)]
add("webp_animated.webp", enc(frames[0], "WEBP", save_all=True, append_images=frames[1:], duration=100, lossless=True), "webp", "animated WebP behavior")
add("webp_2600x40.webp", enc(gradient(2600, 40), "WEBP", quality=80), "webp", "WebP resize path")
add("gif_static.gif", enc(gradient(33, 17).convert("P"), "GIF"), "gif", "static GIF decode")
add("gif_animated.gif", enc(frames[0].convert("P"), "GIF", save_all=True, append_images=[frames[1].convert("P")], duration=100, loop=0), "gif", "animated GIF behavior")
tg = gradient(33, 17).convert("P"); add("gif_transparent.gif", enc(tg, "GIF", transparency=0), "gif", "transparency decode")

# ---- BMP ------------------------------------------------------------------------------------------
add("bmp_24.bmp", enc(gradient(33, 17), "BMP"), "bmp", "BMP -> PNG conversion success")
add("bmp_32.bmp", enc(gradient(33, 17, "RGBA"), "BMP"), "bmp", "32-bit BMP conversion")
add("bmp_8bit.bmp", enc(gradient(33, 17).convert("P"), "BMP"), "bmp", "palette BMP conversion")
add("bmp_2100x20.bmp", enc(gradient(2100, 20), "BMP"), "bmp", "conversion then resize: converted hint + dimension note")
good_bmp = enc(gradient(33, 17), "BMP")
add("bmp_truncated.bmp", good_bmp[: len(good_bmp) // 2], "bmp-failure", "truncated pixel data: conversion failure message")
add("bmp_header_only.bmp", good_bmp[:54], "bmp-failure", "headers only: conversion failure message")

# ---- sniff-positive malformed ---------------------------------------------------------------------
add("bad_png_signature_garbage.png", b"\x89PNG\r\n\x1a\n" + rng.randbytes(200), "malformed", "PNG magic + garbage")
good_png = enc(gradient(64, 64), "PNG")
add("bad_png_truncated.png", good_png[: len(good_png) // 2], "malformed", "truncated PNG")
add("bad_jpeg_soi_garbage.jpg", b"\xff\xd8\xff" + rng.randbytes(200), "malformed", "JPEG SOI + garbage")
good_jpg = enc(gradient(64, 64), "JPEG", quality=90)
add("bad_jpeg_truncated.jpg", good_jpg[: len(good_jpg) // 2], "malformed", "truncated JPEG")
add("bad_gif_header_only.gif", b"GIF89a" + b"\x10\x00\x10\x00\x00\x00\x00", "malformed", "GIF header only")
add("bad_webp_garbage.webp", b"RIFF" + struct.pack("<I", 204) + b"WEBPVP8 " + rng.randbytes(196), "malformed", "RIFF/WEBP magic + garbage")

(OUT / "manifest.json").write_text(json.dumps(MANIFEST, indent=1))
print(len(MANIFEST), "corpus files")
