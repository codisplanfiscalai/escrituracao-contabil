"""Exercise the frozen graphical executable's archive worker, using synthetic data."""
import argparse
import hashlib
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
from src.archive_reader import archive_members
from archive_fixtures import seven_zip, stored_rar, compressed_rar5, rar5_data, compressed_rar4, rar4_data


def run(executable):
    data = b'Escritura synthetic archive test\n' * 30
    fixtures = [('7Z', seven_zip('folder/synthetic.txt', data), data),
                ('RAR', stored_rar('synthetic.txt', data), data),
                ('RAR', compressed_rar5(), rar5_data()),
                ('RAR', compressed_rar4(), rar4_data())]
    with patch('src.archive_reader.sys.executable', str(executable.resolve())), patch('src.archive_reader.sys.frozen', True, create=True):
        for kind, packed, expected in fixtures:
            members = archive_members(packed, kind)
            assert len(members) == 1 and members[0]['content'] == expected, kind
            print(f'PASS frozen {kind}: SHA256 {hashlib.sha256(expected).hexdigest()}')
        for kind, packed in [('RAR', stored_rar('../escape.xml', b'x')), ('7Z', b'corrupt'), ('RAR', b'corrupt')]:
            try: archive_members(packed, kind)
            except ValueError: pass
            else: raise AssertionError('Unsafe/corrupt archive accepted')
    print('PASS: frozen GUI worker, real 7z LZMA, RAR4 stored/compressed LZSS, RAR5 compressed, unsafe/corrupt rejection')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--executable', type=Path, required=True)
    run(parser.parse_args().executable)
