import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

CI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CI))
from version import bump, build_version, parse, read_version, set_version, validate_build
from cleanup import select_caches, local_candidates
from release import verify_container, verify_release_files, digest, publish
from github_api import pages


class VersionTests(unittest.TestCase):
    def test_semver(self):
        self.assertEqual(parse('0.2.1'), (0, 2, 1))
        for value in ('v1.2.3', '1.02.3', '1.2', '1.2.3-dev.1', '1.2.3\n', '-1.2.3'):
            with self.subTest(value=value), self.assertRaises(ValueError): parse(value)
    def test_bumps(self):
        self.assertEqual([bump('1.2.3', kind) for kind in ('patch', 'minor', 'major')], ['1.2.4', '1.3.0', '2.0.0'])
    def test_prerelease_has_base_run_and_attempt(self):
        self.assertEqual(build_version('0.2.1', 'develop', '123', '2'), '0.2.1-dev.123.2')
        self.assertEqual(build_version('0.2.1', 'stable'), '0.2.1')
        for run in ('0', '01', '2;echo', '-1'):
            with self.assertRaises(ValueError): build_version('0.2.1', 'develop', run)
    def test_build_rejects_cross_version_and_tag_injection(self):
        for value in ('0.3.0', '0.2.1;echo', '0.2.1-dev.1.01', '../../0.2.1'):
            with self.assertRaises(ValueError): validate_build(value, '0.2.1')
        self.assertEqual(validate_build('0.2.1-dev.7.1', '0.2.1'), '0.2.1-dev.7.1')
    def test_version_files_stay_together(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'pyproject.toml').write_text('[project]\nversion = "0.1.0"\n')
            set_version('1.2.3', root); self.assertEqual(read_version(root), '1.2.3')
            (root/'VERSION').write_text('1.2.4')
            with self.assertRaises(ValueError): read_version(root)
    def test_rejects_multiple_version_assignments_without_writing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); p = root/'pyproject.toml'; original='version = "1.0.0"\nversion = "2.0.0"\n'; p.write_text(original)
            with self.assertRaises(ValueError): set_version('3.0.0', root)
            self.assertEqual(p.read_text(), original)


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 4, tzinfo=timezone.utc)
        self.rows = [dict(id=1,key='escritura-windows-x64-deps-a',ref='refs/heads/main',last_accessed_at='2026-09-01T00:00:00Z'),dict(id=2,key='escritura-windows-x64-deps-b',ref='refs/heads/main',last_accessed_at='2026-11-03T00:00:00Z'),dict(id=3,key='other-a',ref='refs/pull/7/merge',last_accessed_at='2026-09-01T00:00:00Z'),dict(id=4,key='escritura-windows-x64-deps-a',ref='refs/pull/7/merge',last_accessed_at='2026-11-03T00:00:00Z'),dict(id=5,key='escritura-windows-x86-deps-a',ref='refs/heads/main',last_accessed_at='2026-09-01T00:00:00Z')]
    def test_only_stale_owned_cache_and_preserves_newest_per_platform(self):
        self.assertEqual([r['id'] for r in select_caches(self.rows,self.now,14)], [1])
    def test_pr_scope_is_exact(self):
        self.assertEqual([r['id'] for r in select_caches(self.rows,self.now,14,7)], [4])
        self.assertEqual(select_caches(self.rows,self.now,14,70), [])
    def test_invalid_pr_or_retention(self):
        with self.assertRaises(ValueError): select_caches(self.rows,self.now,0)
        with self.assertRaises(ValueError): select_caches(self.rows,self.now,14,'../main')
    def test_pagination_is_complete(self):
        with patch('github_api.api', side_effect=[{'actions_caches':list(range(100))},{'actions_caches':[100]}]) as request:
            self.assertEqual(len(list(pages('repos/owner/repo/actions/caches','actions_caches'))),101)
            self.assertIn('page=2',request.call_args.args[0])
    def test_local_never_selects_private_data(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name in ('build','data','private','src/__pycache__'): (root/name).mkdir(parents=True)
            with patch('cleanup.subprocess.check_output',return_value='src/app.py\n'):
                self.assertEqual({p.relative_to(root).as_posix() for p in local_candidates(root)}, {'build','src/__pycache__'})
    def test_tracked_output_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'build').mkdir()
            with patch('cleanup.subprocess.check_output',return_value='build/important.py\n'), self.assertRaises(ValueError): local_candidates(root)
    @unittest.skipIf(sys.platform=='win32', 'Symlink creation requires privileges on Windows')
    def test_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'private').mkdir();(root/'build').symlink_to(root/'private',target_is_directory=True)
            with patch('cleanup.subprocess.check_output',return_value=''), self.assertRaises(ValueError): local_candidates(root)


class ArtifactTests(unittest.TestCase):
    def test_completed_release_is_idempotent_for_public_and_private_repositories(self):
        for private in (False, True):
            with self.subTest(private=private), patch('release.repository', return_value='owner/repo'), patch('release.read_version', return_value='0.2.1'), patch('release.api', side_effect=[{'private': private, 'archived': False}, {'object': {'sha': 'a'*40}}, {'status': 'identical'}]), patch('release.existing_release', return_value=({}, True)), patch('release.run') as command:
                publish(Path('unused'), '0.2.1', 'a'*40, 'stable', 'User')
                command.assert_not_called()
    def test_archived_repository_cannot_publish(self):
        with patch('release.repository', return_value='owner/repo'), patch('release.read_version', return_value='0.2.1'), patch('release.api', return_value={'archived': True}), patch('release.run') as command:
            with self.assertRaises(ValueError): publish(Path('unused'), '0.2.1', 'a'*40, 'stable', 'User')
            command.assert_not_called()
    def test_container_corruption_source_and_version(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); file=root/'container.tar.gz';file.write_bytes(b'synthetic')
            meta={'source_sha':'a'*40,'version':'0.2.1','smoke_test':'passed','file':file.name,'sha256':digest(file),'size':file.stat().st_size,'image':'escritura-build:0.2.1','image_id':'sha256:'+'b'*64}
            (root/'container.manifest.json').write_text(json.dumps(meta))
            self.assertEqual(verify_container(root,'a'*40,'0.2.1'),meta)
            for sha,version in [('c'*40,'0.2.1'),('a'*40,'0.2.2')]:
                with self.assertRaises(ValueError):verify_container(root,sha,version)
            file.write_bytes(b'corrupted')
            with self.assertRaises(ValueError):verify_container(root,'a'*40,'0.2.1')
    def test_release_traversal_and_checksum(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);file=root/'file.zip';file.write_bytes(b'synthetic')
            manifest={'source_sha':'a'*40,'version':'0.2.1','files':[{'name':file.name,'sha256':digest(file),'size':9}]}
            verify_release_files(root,manifest,'a'*40,'0.2.1')
            manifest['files'][0]['name']='../file.zip'
            with self.assertRaises(ValueError):verify_release_files(root,manifest,'a'*40,'0.2.1')



if __name__=='__main__':unittest.main()
