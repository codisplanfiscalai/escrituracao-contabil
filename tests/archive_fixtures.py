"""Synthetic archives, generated locally or from the official libarchive test corpus.
RAR5 integer sequence: libarchive 3.8.11, test_read_format_rar5_compressed.rar.uu.
Source tar SHA-256: 900fe9fc7237c2b04f090f3c3648de8fe597525771f5035016537ce2d667d12b.
The source test's BSD-2-Clause notice is preserved in docs/archive-fixture-license.txt.
"""
import base64
import ctypes
import stat
import struct
import zlib
from src.archive_reader import native_library

def stored_rar(name, content):
    """Create a tiny RAR4 stored member from documented binary header fields."""
    def header(raw):
        return struct.pack('<H', zlib.crc32(raw) & 0xffff) + raw
    encoded = name.encode('ascii')
    main = header(struct.pack('<BHHHI', 0x73, 0, 13, 0, 0))
    file = header(struct.pack('<BHHIIBIIBBHI', 0x74, 0x8000, 32 + len(encoded), len(content), len(content),
                              3, zlib.crc32(content), 0, 20, 0x30, len(encoded), stat.S_IFREG | 0o600) + encoded)
    end = header(struct.pack('<BHH', 0x7b, 0, 7))
    return b'Rar!\x1a\x07\x00' + main + file + content + end


def seven_zip(name, content):
    """Create a 7z in memory with libarchive; the application only reads it."""
    lib = ctypes.CDLL(native_library())
    ptr = ctypes.c_void_p
    def bind(name, result, *args):
        fn = getattr(lib, name); fn.restype=result; fn.argtypes=args; return fn
    archive = bind('archive_write_new', ptr)()
    entry = bind('archive_entry_new', ptr)()
    output = ctypes.create_string_buffer(1024 * 1024)
    used = ctypes.c_size_t()
    try:
        assert bind('archive_write_set_format_7zip', ctypes.c_int, ptr)(archive) == 0
        assert bind('archive_write_open_memory', ctypes.c_int, ptr, ptr, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t))(archive, output, len(output), ctypes.byref(used)) == 0
        bind('archive_entry_set_pathname', None, ptr, ctypes.c_char_p)(entry, name.encode())
        bind('archive_entry_set_size', None, ptr, ctypes.c_int64)(entry, len(content))
        bind('archive_entry_set_filetype', None, ptr, ctypes.c_uint)(entry, stat.S_IFREG)
        bind('archive_entry_set_perm', None, ptr, ctypes.c_int)(entry, 0o600)
        assert bind('archive_write_header', ctypes.c_int, ptr, ptr)(archive, entry) == 0
        data=ctypes.create_string_buffer(content)
        assert bind('archive_write_data', ctypes.c_ssize_t, ptr, ptr, ctypes.c_size_t)(archive, data, len(content)) == len(content)
        assert bind('archive_write_close', ctypes.c_int, ptr)(archive) == 0
        return output.raw[:used.value]
    finally:
        bind('archive_entry_free', None, ptr)(entry)
        bind('archive_write_free', ctypes.c_int, ptr)(archive)


def compressed_rar5():
    return base64.b64decode('UmFyIRoHAQDz4YLrCwEFBwAGAQGAgIAAicZf2iYCAwvpAgSwCaSDAs1wynyABQEIdGVzdC5iaW4KAxOLV6xb+BitHsr0ZQEnZWBUH1V2Xb+UknHJz2WWWQxw2WWTGMWSE4ZCSSThkJCSSSQk45JJIQhJJCEJJJCSSEISEs21b3t9Mw6AfR0Drj+eup/3Qf732vfdea86X+gAQAEAyCCfn49vX08vHv7uzr6uno5+Xk4+Lh4N/d3NrZ19bV1NPS0M/NzMrJyMfGxcTDwb+9vLu5uLe2tbSzsrGvrq2rqqmnpaSjoqGgn52cm5mXlpSTSyUjIR6FAfjoyKiYc6cNmoaEgoB+fHt6eHZ0c3Jxb21raWdlY2FfXVtZV1VTITf1/I/QJT6JTn+ESXRYowZ5YXajgppimUF+ZC0XadRjLDOMCoR/+glMZpCl9lUKxWVguLAZFoNy4HdeEGwA8xBIyCeZhWNAumoZbYN5uHg4Bgcg+uYROgpnYYDwNt6Hu9h1fQjfxYQI0YMecKHk0Jg2L44OY6HCIEqeGFFjtjQ/nxUIBsIQ0IhNIxnJAvJQAdd1ZRAwUEAA==')

def rar5_data():
    return b"".join(struct.pack("<I", max(0, k*k - 3*k + 1)) for k in range(1, 301))


def compressed_rar4():
    # Official synthetic LZSS regression: test_read_format_rar3_lowdist_reset.rar.uu.
    return base64.b64decode('UmFyIRoHAM+QcwAADQAAAAAAAABqUXQAgDEA6gEAAEAAAAAD3Dj4bwAAAAAdNREAIAAAAGxvd2Rpc3QtcmVzZXQuYmluERERERERFVVVVWIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZVVVmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmREREREREREVUREVVVVVVVVVVVVVVVVAAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8gISIjJCUmJ/IcvkO/1YBERERERERVVVVViIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiImZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmVVVZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZkRERERERERFVERFVVVVVVVVVVVVVVVfIcBQUlRWWFpcXmBiZGZoam3VMQ9ewBABwA=')

def rar4_data():
    return bytes(range(40)) + bytes((2,3,4,5,6,7,13,14,15)) + bytes(range(40,55))
