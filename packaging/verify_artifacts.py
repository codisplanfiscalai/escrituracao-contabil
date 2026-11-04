"""Check downloaded release ZIPs against manifests and the tested source SHA."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct
import zipfile

from verify_icons import read_ico


def verify(directory, source_sha):
    manifests = sorted(file for file in directory.glob("*.manifest.json")
                       if file.name != "container.manifest.json")
    assert len(manifests) == 2, "Expected exactly two architecture manifests"
    architectures = set()
    for file in manifests:
        manifest = json.loads(file.read_text(encoding="utf-8"))
        assert manifest["source_sha"] == source_sha, "Unexpected source commit"
        assert manifest["smoke_test"] == "passed"
        architectures.add(manifest["architecture"])
        name = file.name.removesuffix(".manifest.json")
        assert manifest["name"] == name
        assert manifest["architecture"] in {"x86", "x64"}
        archive = directory / f"{name}.zip"
        checksum = (directory / f"{name}.sha256").read_text(encoding="ascii").split()
        assert checksum == [hashlib.sha256(archive.read_bytes()).hexdigest(), archive.name]
        with zipfile.ZipFile(archive) as zipped:
            names = zipped.namelist()
            assert len(names) == len(set(names)), "Duplicate ZIP entries"
            for entry in names:
                path = PurePosixPath(entry)
                assert not path.is_absolute() and ".." not in path.parts and "\\" not in entry
                assert path.parts[0] == "EscrituracaoContabil", "Unexpected ZIP root"
            expected = {"EscrituracaoContabil/" + entry["path"] for entry in manifest["files"]}
            assert len(expected) == len(manifest["files"]), "Duplicate manifest entries"
            expected.add("EscrituracaoContabil/manifest.json")
            assert {entry.filename for entry in zipped.infolist() if not entry.is_dir()} == expected, "Unlisted ZIP content"
            assert json.loads(zipped.read("EscrituracaoContabil/manifest.json")) == manifest
            for entry in manifest["files"]:
                data = zipped.read("EscrituracaoContabil/" + entry["path"])
                assert len(data) == entry["size"]
                assert hashlib.sha256(data).hexdigest() == entry["sha256"]
            executable = zipped.read("EscrituracaoContabil/EscrituracaoContabil.exe")
            assert executable[:2] == b"MZ", "Invalid DOS executable header"
            offset = struct.unpack_from("<I", executable, 0x3C)[0]
            assert executable[offset:offset + 4] == b"PE\0\0", "Invalid PE signature"
            machine = struct.unpack_from("<H", executable, offset + 4)[0]
            assert machine == {"x86": 0x14C, "x64": 0x8664}[manifest["architecture"]], "Wrong PE architecture"
            assert struct.unpack_from("<H", executable, offset + 24 + 68)[0] == 2, "Console executable is not allowed"
            assert manifest.get("windows_subsystem") == "GUI"
            identity = manifest["identity"]
            assert identity["name"] == "Escritura" and identity["embedded_pe_icons"] == "verified"
            assets = "EscrituracaoContabil/_internal/src/web/assets/"
            icon = zipped.read(assets + "icon.ico")
            assert hashlib.sha256(icon).hexdigest() == identity["icon_sha256"]
            icon_manifest = zipped.read(assets + "icons-manifest.json")
            assert hashlib.sha256(icon_manifest).hexdigest() == identity["icons_manifest_sha256"]
            icon_manifest = json.loads(icon_manifest)
            for name, digest in icon_manifest["outputs"].items():
                assert hashlib.sha256(zipped.read(assets + name)).hexdigest() == digest
            for name, digest in icon_manifest["sources"].items():
                assert hashlib.sha256(zipped.read(assets + name).replace(b"\r\n", b"\n")).hexdigest() == digest
            for size, data in read_ico(icon).items():
                assert data == zipped.read(assets + f"icon-{size}.png")
    assert architectures == {"x86", "x64"}, "Both native architectures are required"
    print(f"PASS: two complete ZIP manifests, SHA-256 checksums, Escritura identity and source {source_sha}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    verify(args.directory, args.source_sha)
