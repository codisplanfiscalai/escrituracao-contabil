"""Synthetic checks for distribution integrity and GHCR visibility policies."""
from contextlib import redirect_stdout
import io
import hashlib
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from urllib.error import HTTPError

from check_ghcr_visibility import check
from verify_icons import ASSETS, read_ico, verify_assets
from verify_artifacts import verify


class CombinedReleaseTests(unittest.TestCase):
    def test_container_manifest_does_not_replace_or_add_a_windows_architecture(self):
        sha = "a" * 40
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for architecture, machine in (("x86", 0x14C), ("x64", 0x8664)):
                executable = bytearray(256)
                executable[:2] = b"MZ"
                struct.pack_into("<I", executable, 0x3C, 0x80)
                executable[0x80:0x84] = b"PE\0\0"
                struct.pack_into("<H", executable, 0x84, machine)
                struct.pack_into("<H", executable, 0x80 + 24 + 68, 2)
                files = {"EscrituracaoContabil.exe": bytes(executable)}
                files.update({"_internal/src/web/assets/" + p.name: p.read_bytes()
                              for p in ASSETS.iterdir() if p.is_file()})
                name = f"escritura-windows-{architecture}"
                manifest = {
                    "name": name, "source_sha": sha, "architecture": architecture,
                    "smoke_test": "passed", "windows_subsystem": "GUI",
                    "identity": {"name": "Escritura", "embedded_pe_icons": "verified",
                                 "icon_sha256": hashlib.sha256((ASSETS / "icon.ico").read_bytes()).hexdigest(),
                                 "icons_manifest_sha256": hashlib.sha256((ASSETS / "icons-manifest.json").read_bytes()).hexdigest()},
                    "files": [{"path": path, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                              for path, data in files.items()],
                }
                content = json.dumps(manifest)
                (root / f"{name}.manifest.json").write_text(content, encoding="utf-8")
                archive = root / f"{name}.zip"
                with zipfile.ZipFile(archive, "w") as zipped:
                    for path, data in files.items():
                        zipped.writestr("EscrituracaoContabil/" + path, data)
                    zipped.writestr("EscrituracaoContabil/manifest.json", content)
                (root / f"{name}.sha256").write_text(
                    hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name,
                    encoding="ascii")
            (root / "container.manifest.json").write_text('{"image": "synthetic"}')
            with redirect_stdout(io.StringIO()):
                verify(root, sha)
            (root / "unexpected.manifest.json").write_text("{}")
            with self.assertRaisesRegex(AssertionError, "exactly two"):
                verify(root, sha)
            (root / "unexpected.manifest.json").unlink()
            (root / "escritura-windows-x86.manifest.json").unlink()
            with self.assertRaisesRegex(AssertionError, "exactly two"):
                verify(root, sha)


class PackageGateTests(unittest.TestCase):
    def test_explicit_public_repository_policy_returns_actual_visibility(self):
        for visibility in ("private", "public", "internal", None):
            with self.subTest(visibility=visibility), patch("check_ghcr_visibility.urlopen", return_value=io.BytesIO(json.dumps({"visibility": visibility}).encode())), redirect_stdout(io.StringIO()):
                if visibility in ("private", "public"):
                    self.assertEqual(check("owner/repo", "User", "synthetic-token", allowed_visibilities=("private", "public")), visibility)
                else:
                    with self.assertRaisesRegex(ValueError, "not allowed"):
                        check("owner/repo", "User", "synthetic-token", allowed_visibilities=("private", "public"))

    def test_changed_visibility_is_rejected_by_post_push_policy(self):
        for before, after in (("private", "public"), ("public", "private")):
            with self.subTest(before=before), patch("check_ghcr_visibility.urlopen", return_value=io.BytesIO(json.dumps({"visibility": after}).encode())):
                with self.assertRaisesRegex(ValueError, "not allowed"):
                    check("owner/repo", "User", "synthetic-token", allowed_visibilities=(before,))

    def test_invalid_visibility_policy_never_sends_request(self):
        with patch("check_ghcr_visibility.urlopen") as request:
            for allowed in ((), ("internal",), ("public", "unknown")):
                with self.assertRaises(ValueError):
                    check("owner/repo", "User", "synthetic-token", allowed_visibilities=allowed)
            request.assert_not_called()

    def test_private_only_and_account_route(self):
        for owner_type, prefix in (("User", "users"), ("Organization", "orgs")):
            for visibility in ("private", "public", "internal", None):
                with self.subTest(owner=owner_type, visibility=visibility):
                    with patch("check_ghcr_visibility.urlopen", return_value=io.BytesIO(json.dumps({"visibility": visibility}).encode())) as request:
                        with redirect_stdout(io.StringIO()):
                            if visibility == "private":
                                check("OWNER/REPO", owner_type, "synthetic-token")
                            else:
                                with self.assertRaisesRegex(ValueError, "private"):
                                    check("OWNER/REPO", owner_type, "synthetic-token")
                        self.assertEqual(request.call_args.args[0].full_url,
                                         f"https://api.github.com/{prefix}/owner/packages/container/repo")

    def test_absence_allowed_only_before_push_and_errors_stop(self):
        for code in (401, 403, 404, 429, 500):
            for allow_missing in (False, True):
                with self.subTest(code=code, allow_missing=allow_missing):
                    error = HTTPError("https://api.github.com/", code, "synthetic", {}, None)
                    with patch("check_ghcr_visibility.urlopen", side_effect=error):
                        with redirect_stdout(io.StringIO()):
                            if code == 404 and allow_missing:
                                check("owner/repo", "User", "synthetic-token", allow_missing=True)
                            else:
                                with self.assertRaisesRegex(RuntimeError, "If a push already completed"):
                                    check("owner/repo", "User", "synthetic-token", allow_missing=allow_missing)

    def test_invalid_repository_or_owner_never_sends_a_request(self):
        with patch("check_ghcr_visibility.urlopen") as request:
            for repository, owner_type in (("owner/repo?other=1", "User"), ("owner/repo", "unknown")):
                with self.assertRaises(ValueError):
                    check(repository, owner_type, "synthetic-token")
            request.assert_not_called()


class IconIntegrityTests(unittest.TestCase):
    def test_committed_identity_and_seven_ico_images(self):
        self.assertEqual(set(verify_assets()), {16, 24, 32, 48, 64, 128, 256})

    def test_ico_offsets_and_png_crc_corruption_are_rejected(self):
        original = (ASSETS / "icon.ico").read_bytes()
        for offset in (18, len(original) - 1):
            broken = bytearray(original)
            broken[offset] ^= 1
            with self.assertRaises((AssertionError, struct.error)):
                read_ico(bytes(broken))

    def test_altered_generated_asset_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            assets = Path(folder) / "assets"
            shutil.copytree(ASSETS, assets)
            png = assets / "icon-32.png"
            png.write_bytes(png.read_bytes() + b"synthetic corruption")
            with self.assertRaisesRegex(AssertionError, "Changed output"):
                verify_assets(assets)


if __name__ == "__main__":
    unittest.main()
