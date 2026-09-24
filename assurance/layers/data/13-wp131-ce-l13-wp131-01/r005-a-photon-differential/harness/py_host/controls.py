"""R005-A discriminating negative controls.

Each control injects ONE plausible-but-wrong implementation choice into the Python evidence host and
reruns the full corpus; the comparison against the Node/Pi authority must then report a mismatch.
A control that still compares IDENTICAL means the corpus cannot tell that mistake apart from Pi.
"""

from __future__ import annotations

import io
import math

import pi_pipeline as pp
import photon_host as ph


def _pillow_encoders() -> None:
    """'Visually equivalent' encoding: same Photon pixels, encoded by Pillow instead of Photon."""
    from PIL import Image

    def pixels(host, img):
        w, h = host.get_width(img), host.get_height(img)
        if w == 0 or h == 0:  # Photon's encoders trap on an empty image; keep that branch Pi-identical
            raise ph.PhotonTrap("empty image")
        return Image.frombytes("RGBA", (w, h), host.get_raw_pixels(img))

    def get_bytes(self, img):
        buf = io.BytesIO(); pixels(self, img).save(buf, "PNG"); return buf.getvalue()

    def get_bytes_jpeg(self, img, quality):
        buf = io.BytesIO(); pixels(self, img).convert("RGB").save(buf, "JPEG", quality=quality); return buf.getvalue()

    ph.PhotonHost.get_bytes, ph.PhotonHost.get_bytes_jpeg = get_bytes, get_bytes_jpeg


def _resize_variant(select=None, compare=None, filter_=None, round_=None, qualities=None):
    """Re-derive resize_image_in_process with one decision replaced (default = Pi's)."""
    select = select or (lambda cands, limit: next(((e, m) for e, m in cands if compare(len(e), limit)), None))
    compare = compare or (lambda n, limit: n < limit)
    filter_ = ph.LANCZOS3 if filter_ is None else filter_
    round_ = round_ or pp.js_round
    qualities = qualities or (lambda o: list(dict.fromkeys([o["jpegQuality"], 85, 70, 55, 40])))

    def resize_image_in_process(host, data, mime, options=None):
        opts = {**pp.DEFAULTS, **(options or {})}
        input_b64_size = math.ceil(len(data) / 3) * 4
        image = None
        try:
            raw = host.new_from_byteslice(data)
            image = pp.apply_exif_orientation(host, raw, data)
            if image != raw:
                host.free(raw)
            ow, oh = host.get_width(image), host.get_height(image)
            fmt = mime.split("/")[1] if "/" in mime else "png"
            if ow <= opts["maxWidth"] and oh <= opts["maxHeight"] and input_b64_size < opts["maxBytes"]:
                return {"data": pp.b64(data), "mimeType": mime or f"image/{fmt}", "originalWidth": ow,
                        "originalHeight": oh, "width": ow, "height": oh, "wasResized": False}
            tw, th = ow, oh
            if tw > opts["maxWidth"]:
                th = round_((th * opts["maxWidth"]) / tw); tw = opts["maxWidth"]
            if th > opts["maxHeight"]:
                tw = round_((tw * opts["maxHeight"]) / th); th = opts["maxHeight"]
            qs = qualities(opts)
            cw, ch = tw, th
            while True:
                resized = host.resize(image, cw, ch, filter_)
                try:
                    cands = [(pp.b64(host.get_bytes(resized)), "image/png")]
                    cands += [(pp.b64(host.get_bytes_jpeg(resized, q)), "image/jpeg") for q in qs]
                finally:
                    host.free(resized)
                hit = select(cands, opts["maxBytes"])
                if hit:
                    return {"data": hit[0], "mimeType": hit[1], "originalWidth": ow, "originalHeight": oh,
                            "width": cw, "height": ch, "wasResized": True}
                if cw == 1 and ch == 1:
                    break
                nw = 1 if cw == 1 else max(1, math.floor(cw * 0.75))
                nh = 1 if ch == 1 else max(1, math.floor(ch * 0.75))
                if nw == cw and nh == ch:
                    break
                cw, ch = nw, nh
            return None
        except ph.PhotonTrap:
            return None
        finally:
            if image is not None:
                try:
                    host.free(image)
                except ph.PhotonTrap:
                    pass

    pp.resize_image_in_process = resize_image_in_process


def _smallest(cands, limit):
    under = [c for c in cands if len(c[0]) < limit]
    return min(under, key=lambda c: len(c[0])) if under else None


CONTROLS = {
    "filter_triangle_not_lanczos3": lambda: _resize_variant(filter_=2),
    "filter_catmullrom_not_lanczos3": lambda: _resize_variant(filter_=3),
    "smallest_candidate_not_first_under_limit": lambda: _resize_variant(select=_smallest),
    "less_or_equal_not_strict_less": lambda: _resize_variant(compare=lambda n, limit: n <= limit),
    "python_round_half_even_not_math_round": lambda: _resize_variant(round_=round),
    "jpeg_quality_option_ignored": lambda: _resize_variant(qualities=lambda o: [80, 85, 70, 55, 40]),
    "python_format_not_js_toFixed": lambda: setattr(pp, "js_to_fixed_2", lambda x: f"{x:.2f}"),
    "exif_orientation_ignored": lambda: setattr(pp, "get_exif_orientation", lambda data: 1),
    "pillow_encoders_visually_equivalent": _pillow_encoders,
}


def apply(name: str) -> None:
    CONTROLS[name]()
