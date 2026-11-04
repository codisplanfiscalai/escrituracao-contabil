"""Validate generated PNG/ICO identity bytes; optionally check Windows PE resources."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib

SIZES = (16, 24, 32, 48, 64, 128, 256)
ASSETS = Path(__file__).resolve().parents[1] / "src" / "web" / "assets"


def png_dimensions(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "Invalid PNG signature"
    offset = 8
    dimensions = None
    ended = False
    while offset < len(data):
        length, kind = struct.unpack_from(">I4s", data, offset)
        payload = data[offset + 8:offset + 8 + length]
        crc = struct.unpack_from(">I", data, offset + 8 + length)[0]
        assert zlib.crc32(kind + payload) == crc, "PNG chunk checksum mismatch"
        if kind == b"IHDR":
            assert dimensions is None and length == 13
            dimensions = struct.unpack_from(">II", payload)
            assert payload[8:10] == bytes((8, 6)), "Expected RGBA 8-bit PNG"
        if kind == b"IEND":
            assert length == 0
            ended = True
        offset += length + 12
        if ended:
            break
    assert ended and offset == len(data) and dimensions, "Truncated or extra PNG content"
    return dimensions


def read_ico(data):
    assert struct.unpack_from("<HHH", data) == (0, 1, len(SIZES)), "Expected seven ICO images"
    images = {}
    cursor = 6 + 16 * len(SIZES)
    for i, expected_size in enumerate(SIZES):
        width, height, colors, reserved, planes, bits, length, offset = struct.unpack_from("<BBBBHHII", data, 6 + 16 * i)
        size = width or 256
        assert size == (height or 256) == expected_size
        assert (colors, reserved, planes, bits) == (0, 0, 1, 32)
        assert offset == cursor and length > 0, "ICO payloads must be contiguous"
        png = data[offset:offset + length]
        assert len(png) == length and png_dimensions(png) == (size, size)
        images[size] = png
        cursor += length
    assert cursor == len(data), "Unexpected ICO trailing bytes"
    return images


def verify_assets(assets=ASSETS):
    manifest = json.loads((assets / "icons-manifest.json").read_text(encoding="utf-8"))
    expected = {f"icon-{size}.png" for size in (*SIZES, 512)} | {"icon.ico", "symbol-512.png"}
    assert set(manifest["outputs"]) == expected
    assert set(manifest["sources"]) == {"icon.svg", "symbol.svg"}
    for name, digest in manifest["sources"].items():
        canonical = (assets / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(canonical).hexdigest() == digest, f"Changed SVG source: {name}"
    for name, digest in manifest["outputs"].items():
        assert hashlib.sha256((assets / name).read_bytes()).hexdigest() == digest, f"Changed output: {name}"
    for size in (*SIZES, 512):
        assert png_dimensions((assets / f"icon-{size}.png").read_bytes()) == (size, size)
    assert png_dimensions((assets / "symbol-512.png").read_bytes()) == (512, 512)
    images = read_ico((assets / "icon.ico").read_bytes())
    for size, data in images.items():
        assert data == (assets / f"icon-{size}.png").read_bytes(), "ICO image differs from PNG source"
    return images


def verify_pe(executable, images):
    # pefile is already a pinned PyInstaller build dependency on Windows.
    import pefile
    with pefile.PE(str(executable)) as pe:
        icon_payloads = {}
        groups = []
        for resource_type in pe.DIRECTORY_ENTRY_RESOURCE.entries:
            if resource_type.id not in (3, 14):
                continue
            for resource in resource_type.directory.entries:
                for language in resource.directory.entries:
                    entry = language.data.struct
                    data = pe.get_data(entry.OffsetToData, entry.Size)
                    if resource_type.id == 3:
                        icon_payloads[resource.id] = data
                    else:
                        groups.append(data)
        assert groups, "Executable lacks RT_GROUP_ICON"
        matched = False
        for group in groups:
            if struct.unpack_from("<HHH", group) != (0, 1, len(SIZES)):
                continue
            sizes = set()
            for index in range(len(SIZES)):
                width, height, _, _, planes, bits, length, icon_id = struct.unpack_from("<BBBBHHIH", group, 6 + index * 14)
                size = width or 256
                assert size == (height or 256) and (planes, bits) == (1, 32)
                assert size in images and length == len(images[size])
                assert icon_payloads[icon_id] == images[size], "PE icon bytes differ from reviewed ICO"
                sizes.add(size)
            matched = sizes == set(SIZES)
            if matched:
                break
        assert matched, "Executable lacks the complete Escritura icon set"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", type=Path, default=ASSETS)
    parser.add_argument("--executable", type=Path)
    args = parser.parse_args()
    images = verify_assets(args.assets)
    if args.executable:
        verify_pe(args.executable, images)
    print("PASS: Escritura PNG/ICO dimensions, CRCs, source/output hashes" + (" and embedded PE icon resources" if args.executable else ""))
