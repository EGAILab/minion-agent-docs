import json, struct
def tiff_le(orient=6, ifd_off=8, count=1, tag=0x0112, extra=b""):
    t = b"II*\x00" + struct.pack("<I", ifd_off)
    t += struct.pack("<H", count) + struct.pack("<HHI", tag, 3, 1) + struct.pack("<H", orient) + b"\x00\x00"
    return t + extra
def tiff_be(orient=3):
    return b"MM\x00*" + struct.pack(">I", 8) + struct.pack(">H", 1) + struct.pack(">HHI", 0x0112, 3, 1) + struct.pack(">H", orient) + b"\x00\x00"
def app1(payload): return b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload
J = b"\xff\xd8"
cases = {
 "jpeg-soi-only": J,
 "jpeg-3-bytes": b"\xff\xd8\xff",
 "jpeg-ls-f7": b"\xff\xd8\xff\xf7" + b"\x00" * 8,
 "jpeg-exif-le-6": J + app1(b"Exif\x00\x00" + tiff_le(6)),
 "jpeg-exif-be-3": J + app1(b"Exif\x00\x00" + tiff_be(3)),
 "jpeg-fill-bytes-before-app1": J + b"\xff\xff" + app1(b"Exif\x00\x00" + tiff_le(8)),
 "jpeg-non-marker-byte": J + b"\x00\x11\x22\x33",
 "jpeg-app1-without-exif-header": J + app1(b"Abcdef" + tiff_le(6)),
 "jpeg-app1-truncated": J + b"\xff\xe1\x00",
 "jpeg-app1-short-header": J + b"\xff\xe1\x00\x08Exi",
 "jpeg-other-segment-then-eof": J + b"\xff\xdb\x00\x04\x01\x02",
 "jpeg-other-segment-truncated-length": J + b"\xff\xdb\x00",
 "jpeg-other-segment-then-exif": J + b"\xff\xdb\x00\x04\x01\x02" + app1(b"Exif\x00\x00" + tiff_le(5)),
 "tiff-too-short": J + app1(b"Exif\x00\x00" + b"II*\x00\x08"),
 "tiff-ifd-beyond-data": J + app1(b"Exif\x00\x00" + b"II*\x00" + struct.pack("<I", 4000)),
 "tiff-entries-beyond-data": J + app1(b"Exif\x00\x00" + b"II*\x00" + struct.pack("<I", 8) + struct.pack("<H", 5) + b"\x00" * 12),
 "tiff-no-orientation-tag": J + app1(b"Exif\x00\x00" + tiff_le(6, tag=0x0100)),
 "tiff-orientation-0": J + app1(b"Exif\x00\x00" + tiff_le(0)),
 "tiff-orientation-9": J + app1(b"Exif\x00\x00" + tiff_le(9)),
 "tiff-orientation-7": J + app1(b"Exif\x00\x00" + tiff_le(7)),
 "tiff-le-signed-negative-ifd-offset": J + app1(b"Exif\x00\x00" + b"II*\x00" + struct.pack("<I", 0xFFFFFFF8) + b"\x00" * 24),
 "tiff-be-high-bit-ifd-offset": J + app1(b"Exif\x00\x00" + b"MM\x00*" + struct.pack(">I", 0xFFFFFFF8) + b"\x00" * 24),
}
def riff(chunks): 
    body = b"WEBP" + chunks
    return b"RIFF" + struct.pack("<I", len(body)) + body
def chunk(cid, data, size=None):
    s = len(data) if size is None else size
    return cid + struct.pack("<I", s) + data + (b"\x00" if len(data) % 2 else b"")
cases.update({
 "webp-exif-with-header": riff(chunk(b"VP8 ", b"\x00" * 10) + chunk(b"EXIF", b"Exif\x00\x00" + tiff_le(6))),
 "webp-exif-raw-tiff": riff(chunk(b"EXIF", tiff_le(8))),
 "webp-odd-chunk-then-exif": riff(chunk(b"ICCP", b"\x01\x02\x03") + chunk(b"EXIF", tiff_le(2))),
 "webp-exif-size-beyond-data": riff(chunk(b"EXIF", tiff_le(6), size=5000)),
 "webp-no-exif": riff(chunk(b"VP8 ", b"\x00" * 10)),
 "webp-tiny-exif-chunk": riff(chunk(b"EXIF", b"Exi")),
 "riff-not-webp": b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 8,
})
png = b"\x89PNG\r\n\x1a\n"
def pchunk(t, data): return struct.pack(">I", len(data)) + t + data + b"\x00" * 4
ihdr = pchunk(b"IHDR", b"\x00" * 13)
cases.update({
 "png-signature-only": png,
 "png-wrong-ihdr-length": png + struct.pack(">I", 12) + b"IHDR" + b"\x00" * 16,
 "png-actl-before-idat": png + ihdr + pchunk(b"acTL", b"\x00" * 8) + pchunk(b"IDAT", b"\x00"),
 "png-idat-before-actl": png + ihdr + pchunk(b"IDAT", b"\x00") + pchunk(b"acTL", b"\x00" * 8),
 "png-chunk-runs-past-buffer": png + ihdr + struct.pack(">I", 99999) + b"tEXt" + b"\x00" * 4,
 "png-huge-chunk-length": png + ihdr + struct.pack(">I", 0xFFFFFFF0) + b"tEXt",
 "gif": b"GIF89a" + b"\x00" * 6,
 "gif-3-bytes": b"GIF",
})
def bmp(file_size=100, offset=54, dib=40, planes=1, bpp=24, total=60):
    head = b"BM" + struct.pack("<I", file_size) + b"\x00" * 4 + struct.pack("<I", offset) + struct.pack("<I", dib)
    if dib == 12:
        head += b"\x00" * 4 + struct.pack("<HH", planes, bpp)
    else:
        head += b"\x00" * 8 + struct.pack("<HH", planes, bpp)
    return (head + b"\x00" * total)[:max(total, 0)] if total else head
cases.update({
 "bmp-valid-40": bmp(total=60),
 "bmp-valid-core-12": bmp(dib=12, offset=26, total=40),
 "bmp-zero-declared-size": bmp(file_size=0, total=60),
 "bmp-too-short": b"BM" + b"\x00" * 20,
 "bmp-declared-size-under-26": bmp(file_size=20, total=60),
 "bmp-offset-under-header": bmp(offset=30, total=60),
 "bmp-offset-past-declared-size": bmp(file_size=60, offset=70, total=60),
 "bmp-unknown-dib-size": bmp(dib=20, offset=40, total=60),
 "bmp-40-but-29-bytes": bmp(total=29),
 "bmp-two-planes": bmp(planes=2, total=60),
 "bmp-3-bits": bmp(bpp=3, total=60),
 "bmp-32-bits": bmp(bpp=32, total=60),
 "text": b"hello world",
 "empty": b"",
})
print(json.dumps({k: v.hex() for k, v in cases.items()}))
