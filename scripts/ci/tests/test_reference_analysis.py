"""PE parser fixtures are invented byte arrays, never supplied executables."""
import struct
import unittest
from scripts.analyze_reference_pe import analyze_bytes, outside_repository, ROOT


def fixture():
    data = bytearray(1024)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 60, 64)
    data[64:68] = b'PE\x00\x00'
    struct.pack_into('<HHIIIHH', data, 68, 0x14c, 1, 0, 0, 0, 224, 0x102)
    struct.pack_into('<H', data, 88, 0x10b)
    struct.pack_into('<I', data, 88 + 60, 512)
    struct.pack_into('<H', data, 88 + 68, 2)
    struct.pack_into('<I', data, 88 + 92, 16)
    struct.pack_into('<II', data, 88 + 104, 0x1000, 40)
    struct.pack_into('<8sIIIIIIHHI', data, 312, b'.idata', 512, 0x1000, 512, 512, 0, 0, 0, 0, 0)
    struct.pack_into('<IIIII', data, 512, 0, 0, 0, 0x1050, 0)
    data[592:605] = b'MSVBVM60.DLL\x00'
    return bytes(data)


class ReferenceAnalysisTests(unittest.TestCase):
    def test_native_imports_and_no_execution_or_source_claim(self):
        result = analyze_bytes(fixture())
        self.assertEqual(result['format'], 'PE32')
        self.assertEqual(result['imported_dlls'], ['MSVBVM60.DLL'])
        self.assertEqual(result['technology_hints'][0]['technology'], 'Visual Basic runtime')
        self.assertFalse(result['execution_performed'])
        self.assertFalse(result['source_code_recovered'])

    def test_truncated_and_unmapped_inputs_are_refused(self):
        with self.assertRaises(ValueError):
            analyze_bytes(fixture()[:600])
        bad = bytearray(fixture())
        struct.pack_into('<I', bad, 60, 0xffffffff)
        with self.assertRaises(ValueError):
            analyze_bytes(bytes(bad))
        struct.pack_into('<I', bad, 60, 64)
        struct.pack_into('<I', bad, 512 + 12, 0xffffff00)
        with self.assertRaises(ValueError):
            analyze_bytes(bytes(bad))

    def test_no_private_analysis_output_inside_git_tree(self):
        with self.assertRaises(ValueError):
            outside_repository(ROOT / 'docs' / 'private-analysis.json')


if __name__ == '__main__':
    unittest.main()
