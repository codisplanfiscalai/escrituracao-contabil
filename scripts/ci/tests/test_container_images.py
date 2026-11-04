import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from container_images import inspect, load_lock, image_ref, mirror, verify


class ImageSupplyTests(unittest.TestCase):
    def setUp(self):
        self.item = load_lock()['images']['python']

    def test_lock_rejects_unpinned_origin_and_foreign_destination(self):
        for field, value in [('upstream', 'python:latest'), ('mirror', 'ghcr.io/other/python:tag'), ('digest', 'sha256:short')]:
            data = load_lock()
            data['images']['python'][field] = value
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'lock.json'
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError): load_lock(path)

    def test_registry_auth_network_errors_are_never_treated_as_missing(self):
        for error in (b'unauthorized: 401', b'denied: 403', b'connection refused', b'not found: 404'):
            with patch('container_images.subprocess.run', return_value=subprocess.CompletedProcess([], 1, b'', error)):
                with self.assertRaises(RuntimeError): inspect(self.item['mirror'], allow_missing=True)
        with patch('container_images.subprocess.run', return_value=subprocess.CompletedProcess([], 1, b'', b'manifest unknown')):
            self.assertIsNone(inspect(self.item['mirror'], allow_missing=True))

    def test_digest_is_hash_of_exact_registry_bytes(self):
        raw = b'{"synthetic":"manifest"}\n'
        with patch('container_images.subprocess.run', return_value=subprocess.CompletedProcess([], 0, raw, b'')):
            self.assertEqual(inspect(self.item['upstream']), 'sha256:' + hashlib.sha256(raw).hexdigest())
        with patch('container_images.inspect', return_value='sha256:' + '0' * 64):
            with self.assertRaises(ValueError): verify(self.item, 'ghcr')

    def test_no_authorization_or_existing_conflict_never_writes(self):
        with patch('container_images.inspect', return_value='sha256:' + '0' * 64), patch('container_images.subprocess.run') as run:
            with self.assertRaises(ValueError): mirror(self.item)
            with self.assertRaises(ValueError): mirror(self.item, publish=True)
            run.assert_not_called()

    def test_existing_matching_version_is_read_only(self):
        with patch('container_images.inspect', return_value=self.item['digest']), patch('container_images.subprocess.run') as run:
            mirror(self.item, publish=True)
            run.assert_not_called()

    def test_copy_keeps_all_platforms_and_checks_destination(self):
        with patch('container_images.inspect', side_effect=[None, self.item['digest'], self.item['digest'], self.item['digest']]), patch('container_images.subprocess.run') as run:
            mirror(self.item, publish=True)
            run.assert_called_once_with(['skopeo', 'copy', '--all', '--preserve-digests', 'docker://' + self.item['upstream'], 'docker://' + self.item['mirror']], check=True)
        self.assertIn('@sha256:', image_ref(self.item, 'ghcr'))
        with self.assertRaises(ValueError): image_ref(self.item, 'automatic')


class PublishedImageTests(unittest.TestCase):
    def test_remote_mismatch_cannot_reach_smoke(self):
        from container_smoke import published_smoke
        with patch('container_smoke.subprocess.run') as command, patch('container_smoke.subprocess.check_output', return_value='sha256:wrong'), patch('container_smoke.smoke') as smoke:
            with self.assertRaises(ValueError): published_smoke('registry/image@sha256:expected', 'sha256:expected')
            command.assert_called_once_with(['docker', 'pull', 'registry/image@sha256:expected'], check=True)
            smoke.assert_not_called()

    def test_remote_smoke_uses_pulled_digest(self):
        from container_smoke import published_smoke
        with patch('container_smoke.subprocess.run'), patch('container_smoke.subprocess.check_output', return_value='sha256:expected\n'), patch('container_smoke.smoke') as smoke:
            published_smoke('registry/image@sha256:immutable', 'sha256:expected')
            smoke.assert_called_once_with('registry/image@sha256:immutable')

    def test_defaults_agree_with_lock(self):
        root = Path(__file__).resolve().parents[3]
        images = load_lock()['images']
        self.assertIn(images['python']['upstream'], (root / 'Dockerfile').read_text())
        self.assertIn(images['caddy']['upstream'], (root / 'deploy/compose.yaml').read_text())
        self.assertIn(image_ref(images['caddy'], 'ghcr'), (root / 'deploy/compose.ghcr.yaml').read_text())


if __name__ == '__main__': unittest.main()
