"""Internal worker for Python and the windowed executable; never starts the GUI."""
import base64
import json
from pathlib import Path
import sys


def main(args):
    try:
        from src.archive_limits import apply_limits, OUTPUT_BYTES
        from src.archive_reader import ARCHIVE_TIMEOUT, MAX_MEMBER_BYTES, _native_members
        if len(args) != 3 or args[0] not in {'7Z', 'RAR'}:
            return 1
        apply_limits(ARCHIVE_TIMEOUT)
        with Path(args[1]).open('rb') as handle:
            source = handle.read(MAX_MEMBER_BYTES + 1)
        if len(source) > MAX_MEMBER_BYTES:
            return 1
        written = 0
        # Parent creates this empty file exclusively, in a private temporary directory.
        with Path(args[2]).open('wb') as output:
            for member in _native_members(source, args[0]):
                value = {'name': member['name'], 'content': base64.b64encode(member['content']).decode('ascii')}
                line = (json.dumps(value, ensure_ascii=True) + '\n').encode('ascii')
                written += len(line)
                if written > OUTPUT_BYTES: return 1
                output.write(line)
        return 0
    except Exception:
        return 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
