"""Build inputs and worker trust boundaries; real PE tests run on Windows CI."""
import base64
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_native_archives import extract
from src.archive_reader import archive_members, native_library
from src.archive_worker import main as worker_main


class NativeBoundaryTests(unittest.TestCase):
    def test_source_archives_cannot_escape_or_create_links(self):
        for name, kind in [('../escape',tarfile.REGTYPE), ('/escape',tarfile.REGTYPE),('dir/link',tarfile.SYMTYPE)]:
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory); source=root/'source.tar'
                with tarfile.open(source,'w') as tar:
                    info=tarfile.TarInfo(name); info.type=kind; info.linkname='/outside'
                    tar.addfile(info)
                with self.assertRaises(ValueError): extract(source, root/'out')

    def test_windows_loader_uses_no_path_search_and_frozen_ignores_dev_override(self):
        with patch('src.archive_reader.sys.platform','win32'), patch('src.archive_reader.sys.frozen',True,create=True), patch.dict('os.environ',{'ESCRITURA_LIBARCHIVE_DIR':'/untrusted'}), patch.object(Path,'is_file',return_value=True), patch('src.archive_reader.ctypes.util.find_library') as finder:
            path=Path(native_library())
            self.assertEqual(path.parts[-3:], ('src','native','archive.dll'))
            self.assertNotIn('untrusted',path.parts)
            finder.assert_not_called()

    def test_no_native_decoder_runs_if_os_limits_cannot_be_applied(self):
        with patch('src.archive_limits.apply_limits',side_effect=OSError('synthetic denial')), patch('src.archive_reader._native_members') as decode:
            self.assertEqual(worker_main(['RAR','absent','absent']),1)
            decode.assert_not_called()

    def test_child_output_is_validated_again_before_import(self):
        cases=[b'not json\n', json.dumps({'name':'../escape','content':'eA=='}).encode()+b'\n',
               json.dumps({'name':'safe.xml','content':'@@'}).encode()+b'\n',
               json.dumps({'name':'safe.xml','content':'eA==','extra':'bad'}).encode()+b'\n',
               json.dumps({'name':'safe.xml','content':base64.b64encode(b'x'*10001).decode()}).encode()+b'\n']
        for content in cases:
            def child(command, **kwargs):
                Path(command[-1]).write_bytes(content)
                return subprocess.CompletedProcess(command,0)
            with self.subTest(case=content[:30]), patch('src.archive_reader.subprocess.run',side_effect=child):
                with self.assertRaises(ValueError): archive_members(b'x'*100,'RAR')

    def test_blocked_worker_creation_is_an_explicit_rejection(self):
        with patch('src.archive_reader.subprocess.run', side_effect=OSError('synthetic policy denial')):
            with self.assertRaisesRegex(ValueError, 'indisponível'): archive_members(b'synthetic','RAR')

    def test_worker_is_not_given_archive_names_as_output_paths(self):
        def child(command, **kwargs):
            self.assertEqual(command[-3],'RAR')
            self.assertEqual(Path(command[-2]).name,'input')
            self.assertEqual(Path(command[-1]).name,'output')
            self.assertEqual(Path(command[-2]).read_bytes(),b'synthetic')
            Path(command[-1]).write_bytes(b'{"name":"safe.txt","content":"eA=="}\n')
            return subprocess.CompletedProcess(command,0)
        with patch('src.archive_reader.subprocess.run',side_effect=child):
            self.assertEqual(archive_members(b'synthetic','RAR'),[{'name':'safe.txt','content':b'x'}])


if __name__=='__main__':unittest.main()
