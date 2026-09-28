"""#74 hardening corpus: deterministic, standard-library only (struct + zlib), no image library.

    python make_corpus.py <out-dir> <png_small_rgb.png from the committed R005-A corpus>

Every file is a function of fixed parameters and a fixed LCG seed, so regeneration is byte-identical.
"""

import struct
import sys
import zlib
from pathlib import Path


def lcg_bytes(n, seed):
    out = bytearray(n)
    s = seed & 0xFFFFFFFF
    for i in range(n):
        s = (s * 1103515245 + 12345) & 0xFFFFFFFF
        out[i] = (s >> 16) & 0xFF
    return bytes(out)


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def png(width, height, bit_depth, color_type, rows):
    raw = b"".join(b"\x00" + r for r in rows)
    ihdr = struct.pack(">IIBBBBB", width, height, bit_depth, color_type, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def bmp_1bit(width, height, seed):
    stride = ((width + 31) // 32) * 4
    pixels = lcg_bytes(stride * height, seed)
    palette = b"\x00\x00\x00\x00" + b"\xff\xff\xff\x00"
    offset = 14 + 40 + len(palette)
    size = offset + len(pixels)
    header = b"BM" + struct.pack("<IHHI", size, 0, 0, offset)
    dib = struct.pack("<IiiHHIIiiII", 40, width, height, 1, 1, 0, len(pixels), 2835, 2835, 2, 2)
    return header + dib + palette + pixels


def insert_after_ihdr(data, extra):
    end = 8 + 8 + 13 + 4  # signature + IHDR chunk
    return data[:end] + extra + data[end:]


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    small = Path(sys.argv[2]).read_bytes()
    files = {}
    # A/C: 1-bit noise BMP wider than 2000 px -> PNG conversion -> Lanczos resize yields high-entropy
    # grayscale whose PNG candidate exceeds the ceiling, so a JPEG candidate wins.
    files["bmp1_noise_2100x2100.bmp"] = bmp_1bit(2100, 2100, 0x74A)
    # C without conversion: the same idea from a 1-bit grayscale PNG source.
    w = 2100
    stride = (w + 7) // 8
    noise = lcg_bytes(stride * 2100, 0x74C)
    files["png1_noise_2100x2100.png"] = png(w, 2100, 1, 0, [noise[i * stride:(i + 1) * stride] for i in range(2100)])
    # B: toFixed(2) near-ties at a 2000 target width (scale = W/2000 has an inexact binary value).
    for width in (2150, 2650, 3050):
        rows = [bytes((x * 7 + y * 13) & 0xFF for x in range(width * 3)) for y in range(4)]
        files[f"png_rgb_{width}x4.png"] = png(width, 4, 8, 2, rows)
    # D: the no-resize fast path is taken iff ceil(n/3)*4 < 4,718,592, i.e. n <= 3,538,941.
    for n in (3538941, 3538942, 3538944):
        files[f"png_small_rgb_padded_{n}.png"] = small + b"\x00" * (n - len(small))
    # E: an acTL chunk before the first IDAT makes the sniff reject the file; after IDAT it does not.
    actl = chunk(b"acTL", struct.pack(">II", 1, 0))
    files["apng_actl_before_idat.png"] = insert_after_ihdr(small, actl)
    idat = small.index(b"IDAT") - 4
    files["png_actl_after_idat.png"] = small[:idat] + small[idat:small.index(b"IEND") - 4] + actl + small[small.index(b"IEND") - 4:]
    for name, data in files.items():
        (out / name).write_bytes(data)
    print("\n".join(f"{len(d):>9} {n}" for n, d in files.items()))


main()
