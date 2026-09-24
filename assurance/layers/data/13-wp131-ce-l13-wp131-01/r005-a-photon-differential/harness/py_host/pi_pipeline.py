"""Evidence-only transliteration of pinned Pi's image pipeline (b7bb00b9) onto the Python Photon host.

Mirrors packages/coding-agent/src/utils/{image-process,image-convert,image-resize-core,
exif-orientation}.ts line for line, including the JavaScript semantics a naive port would get wrong:
Math.round (halves up), Number.prototype.toFixed (exact ties up), signed 32-bit little-endian reads,
out-of-range byte reads acting as 0, and JS remainder signs. Not production code.
"""

from __future__ import annotations

import base64
import math
from decimal import ROUND_HALF_UP, Decimal

from photon_host import LANCZOS3, PhotonHost, PhotonTrap

DEFAULT_MAX_BYTES = 4.5 * 1024 * 1024
DEFAULTS = {"maxWidth": 2000, "maxHeight": 2000, "maxBytes": DEFAULT_MAX_BYTES, "jpegQuality": 80}


# ---- JavaScript semantics --------------------------------------------------------------------------
def js_round(x: float) -> int:
    return math.floor(x + 0.5)


def js_to_fixed_2(x: float) -> str:
    return str(Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


class _Bytes:
    """Uint8Array indexing: out-of-range reads are `undefined`, which bitwise ops treat as 0."""

    def __init__(self, data: bytes) -> None:
        self.d, self.length = data, len(data)

    def get(self, i: int):
        return self.d[i] if 0 <= i < self.length else None

    def bit(self, i: int) -> int:
        v = self.get(i)
        return 0 if v is None else v


def _int32(v: int) -> int:
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v >= 0x80000000 else v


# ---- exif-orientation.ts ---------------------------------------------------------------------------
def _read_orientation_from_tiff(b: _Bytes, tiff_start: int) -> int:
    if tiff_start + 8 > b.length:
        return 1
    le = ((b.bit(tiff_start) << 8) | b.bit(tiff_start + 1)) == 0x4949

    def read16(p):
        return (b.bit(p) | (b.bit(p + 1) << 8)) if le else ((b.bit(p) << 8) | b.bit(p + 1))

    def read32(p):
        if le:
            return _int32(b.bit(p) | (b.bit(p + 1) << 8) | (b.bit(p + 2) << 16) | (b.bit(p + 3) << 24))
        return ((b.bit(p) << 24) | (b.bit(p + 1) << 16) | (b.bit(p + 2) << 8) | b.bit(p + 3)) & 0xFFFFFFFF

    ifd_start = tiff_start + read32(tiff_start + 4)
    if ifd_start + 2 > b.length:
        return 1
    for i in range(read16(ifd_start)):
        entry = ifd_start + 2 + i * 12
        if entry + 12 > b.length:
            return 1
        if read16(entry) == 0x0112:
            value = read16(entry + 8)
            return value if 1 <= value <= 8 else 1
    return 1


def _has_exif_header(b: _Bytes, o: int) -> bool:
    return [b.get(o + k) for k in range(6)] == [0x45, 0x78, 0x69, 0x66, 0x00, 0x00]


def _find_jpeg_tiff_offset(b: _Bytes) -> int:
    offset = 2
    while offset < b.length - 1:
        if b.get(offset) != 0xFF:
            return -1
        marker = b.get(offset + 1)
        if marker == 0xFF:
            offset += 1
            continue
        if marker == 0xE1:
            if offset + 4 >= b.length:
                return -1
            seg = offset + 4
            if seg + 6 > b.length or not _has_exif_header(b, seg):
                return -1
            return seg + 6
        if offset + 4 > b.length:
            return -1
        offset += 2 + ((b.bit(offset + 2) << 8) | b.bit(offset + 3))
    return -1


def _find_webp_tiff_offset(b: _Bytes) -> int:
    offset = 12
    while offset + 8 <= b.length:
        chunk_id = bytes(b.bit(offset + k) for k in range(4))
        size = _int32(b.bit(offset + 4) | (b.bit(offset + 5) << 8) | (b.bit(offset + 6) << 16) | (b.bit(offset + 7) << 24))
        data_start = offset + 8
        if chunk_id == b"EXIF":
            if data_start + size > b.length:
                return -1
            return data_start + 6 if size >= 6 and _has_exif_header(b, data_start) else data_start
        offset = data_start + size + int(math.fmod(size, 2))  # JS % keeps the dividend's sign
    return -1


def get_exif_orientation(data: bytes) -> int:
    b = _Bytes(data)
    tiff = -1
    if b.length >= 2 and b.get(0) == 0xFF and b.get(1) == 0xD8:
        tiff = _find_jpeg_tiff_offset(b)
    elif b.length >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        tiff = _find_webp_tiff_offset(b)
    return 1 if tiff == -1 else _read_orientation_from_tiff(b, tiff)


def _rotate90(host: PhotonHost, img: int, dst_index) -> int:
    w, h = host.get_width(img), host.get_height(img)
    src = host.get_raw_pixels(img)
    dst = bytearray(len(src))
    for y in range(h):
        for x in range(w):
            s, d = (y * w + x) * 4, dst_index(x, y, w, h) * 4
            dst[d:d + 4] = src[s:s + 4]
    return host.new(bytes(dst), h, w)


def apply_exif_orientation(host: PhotonHost, img: int, original: bytes) -> int:
    o = get_exif_orientation(original)
    if o == 1:
        return img
    if o == 2:
        host.fliph(img); return img
    if o == 3:
        host.fliph(img); host.flipv(img); return img
    if o == 4:
        host.flipv(img); return img
    if o == 5:
        r = _rotate90(host, img, lambda x, y, _w, h: x * h + (h - 1 - y)); host.fliph(r); return r
    if o == 6:
        return _rotate90(host, img, lambda x, y, _w, h: x * h + (h - 1 - y))
    if o == 7:
        r = _rotate90(host, img, lambda x, y, w, h: (w - 1 - x) * h + y); host.fliph(r); return r
    if o == 8:
        return _rotate90(host, img, lambda x, y, w, h: (w - 1 - x) * h + y)
    return img


# ---- image-resize-core.ts --------------------------------------------------------------------------
def resize_image_in_process(host: PhotonHost, data: bytes, mime: str, options: dict | None = None):
    opts = {**DEFAULTS, **(options or {})}
    input_b64_size = math.ceil(len(data) / 3) * 4
    image = None
    try:
        raw = host.new_from_byteslice(data)
        image = apply_exif_orientation(host, raw, data)
        if image != raw:
            host.free(raw)
        ow, oh = host.get_width(image), host.get_height(image)
        fmt = mime.split("/")[1] if "/" in mime else "png"
        if ow <= opts["maxWidth"] and oh <= opts["maxHeight"] and input_b64_size < opts["maxBytes"]:
            return {"data": b64(data), "mimeType": mime or f"image/{fmt}", "originalWidth": ow, "originalHeight": oh,
                    "width": ow, "height": oh, "wasResized": False}
        tw, th = ow, oh
        if tw > opts["maxWidth"]:
            th = js_round((th * opts["maxWidth"]) / tw); tw = opts["maxWidth"]
        if th > opts["maxHeight"]:
            tw = js_round((tw * opts["maxHeight"]) / th); th = opts["maxHeight"]
        qualities = list(dict.fromkeys([opts["jpegQuality"], 85, 70, 55, 40]))
        cw, ch = tw, th
        while True:
            resized = host.resize(image, cw, ch, LANCZOS3)
            try:
                cands = [(b64(host.get_bytes(resized)), "image/png")]
                cands += [(b64(host.get_bytes_jpeg(resized, q)), "image/jpeg") for q in qualities]
            finally:
                host.free(resized)
            for enc, m in cands:
                if len(enc) < opts["maxBytes"]:
                    return {"data": enc, "mimeType": m, "originalWidth": ow, "originalHeight": oh,
                            "width": cw, "height": ch, "wasResized": True}
            if cw == 1 and ch == 1:
                break
            nw = 1 if cw == 1 else max(1, math.floor(cw * 0.75))
            nh = 1 if ch == 1 else max(1, math.floor(ch * 0.75))
            if nw == cw and nh == ch:
                break
            cw, ch = nw, nh
        return None
    except PhotonTrap:
        return None
    finally:
        if image is not None:
            try:
                host.free(image)
            except PhotonTrap:
                pass


# ---- image-convert.ts / image-process.ts -----------------------------------------------------------
def convert_image_bytes_to_png(host: PhotonHost, data: bytes):
    try:
        raw = host.new_from_byteslice(data)
        image = apply_exif_orientation(host, raw, data)
        if image != raw:
            host.free(raw)
        try:
            return host.get_bytes(image)
        finally:
            host.free(image)
    except PhotonTrap:
        return None


_SUPPORTED = {"image/png": "image/png", "image/jpeg": "image/jpeg", "image/jpg": "image/jpeg",
              "image/gif": "image/gif", "image/webp": "image/webp"}


def _base_mime(m: str) -> str:
    return m.split(";")[0].strip().lower()


def format_dimension_note(r: dict):
    if not r["wasResized"]:
        return None
    scale = r["originalWidth"] / r["width"]
    return (f"[Image: original {r['originalWidth']}x{r['originalHeight']}, displayed at {r['width']}x{r['height']}. "
            f"Multiply coordinates by {js_to_fixed_2(scale)} to map to original image.]")


def process_image(main_host: PhotonHost, fresh_host, data: bytes, mime: str) -> dict:
    """`main_host`: the long-lived main-thread instance (conversions). `fresh_host()`: a new instance
    per resize, as Pi's worker path loads Photon afresh for each call."""
    normalized = _SUPPORTED.get(_base_mime(mime))
    converted_from = None
    if normalized:
        nbytes = data
    else:
        nbytes = convert_image_bytes_to_png(main_host, data)
        if nbytes is None:
            return {"ok": False, "message": "[Image omitted: could not be converted to a supported inline image format.]"}
        normalized, converted_from = "image/png", _base_mime(mime)
    resized = resize_image_in_process(fresh_host(), nbytes, normalized)
    if resized is None:
        return {"ok": False, "message": "[Image omitted: could not be resized below the inline image size limit.]"}
    hints = []
    if converted_from and converted_from != resized["mimeType"]:
        hints.append(f"[Image converted from {converted_from} to {resized['mimeType']}.]")
    note = format_dimension_note(resized)
    if note:
        hints.append(note)
    return {"ok": True, "data": resized["data"], "mimeType": resized["mimeType"], "hints": hints}
