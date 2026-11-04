"""Check downloaded release ZIPs against manifests and the tested source SHA."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct
import zipfile


def verify(directory, source_sha):
    manifests = sorted(directory.glob("*.manifest.json"))
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
    assert architectures == {"x86", "x64"}, "Both native architectures are required"
    print(f"PASS: two complete ZIP manifests, SHA-256 checksums and source {source_sha}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    verify(args.directory, args.source_sha)
