"""Synthetic checks for distribution integrity and the private GHCR gate."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from check_ghcr_visibility import check
from verify_icons import ASSETS, read_ico, verify_assets


class PrivatePackageGateTests(unittest.TestCase):
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
