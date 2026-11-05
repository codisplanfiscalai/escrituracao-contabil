"""Synthetic archives only: no issued documents, binary fixtures or private data."""
import base64
import ctypes
import ctypes.util
import hashlib
import io
import json
import sqlite3
import stat
import struct
import subprocess
import unittest
from unittest.mock import patch
import zipfile
import zlib

from src.archive_reader import archive_members, safe_member, _native_members
from src.local_app import dispatch, APIError
from src.persistence import AccountingStore
from src.reconciliation import SPED_PROFILE
from test_persistence import ISSUER, fake_xml
from test_reconciliation import fake_sped


def zip_bytes(entries, compression=zipfile.ZIP_DEFLATED):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression) as archive:
        for name, content in entries:
            archive.writestr(name, content)
    return stream.getvalue()


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
    lib = ctypes.CDLL(ctypes.util.find_library('archive'))
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


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.store=AccountingStore(':memory:')
        self.addCleanup(self.store.close)
        self.company=self.store.create_company('Empresa fictícia', '1', '1', ISSUER)['id']
        self.period=self.store.create_period(self.company, '2026-09', '2026-09')['id']
        self.other=self.store.create_company('Outra fictícia', '2', '2')['id']

    def batch(self, inputs, key='tentativa-ficticia', **kwargs):
        return self.store.import_batch(self.company, self.period, inputs, key, **kwargs)

    def test_mixed_batch_originals_member_errors_and_retry(self):
        original=fake_xml()
        packed=zip_bytes([('sub/pedido.xml',original),('invalido.xml',b'<broken'),('anexo.pdf',b'not a pdf')])
        inputs=[{'filename':'pacote.ZIP','content':packed},{'filename':'repetido.xml','content':original},{'filename':'estrutura.txt','content':b'|0000|TESTE|'}]
        batch=self.batch(inputs)
        self.assertEqual(batch['status'],'concluido')
        self.assertEqual(batch['counts']['rejeitado'],2)
        self.assertEqual(len(self.store.list_documents(self.company)),1)
        package=batch['items'][0]
        members=[i for i in batch['items'] if i['parent_id']==package['id']]
        self.assertEqual(len(members),3)
        self.assertEqual(self.store.read_import_original(self.company,package['id'])['content'],packed)
        good=next(i for i in members if i['filename'].endswith('pedido.xml'))
        self.assertEqual(good['sha256'],hashlib.sha256(original).hexdigest())
        self.assertEqual(self.store.read_import_original(self.company,good['id'])['content'],original)
        repeated=next(i for i in batch['items'] if i['filename']=='repetido.xml')
        self.assertTrue(repeated['details']['duplicate'])
        self.assertEqual(good['file_id'],repeated['file_id'])
        again=self.batch(inputs)
        self.assertTrue(again['duplicate'])
        self.assertEqual(again['items'],batch['items'])
        with self.assertRaisesRegex(ValueError,'outro conteúdo'):
            self.batch([{'filename':'novo.xml','content':original}])

    def test_ownership_and_period_guards(self):
        batch=self.batch([{'filename':'a.xml','content':fake_xml()}])
        with self.assertRaises(ValueError):self.store.import_batch_result(self.other,batch['id'])
        with self.assertRaises(ValueError):self.store.read_import_original(self.other,batch['items'][0]['id'])
        with self.assertRaises(ValueError):self.store.import_batch(self.other,self.period,[{'filename':'a.xml','content':fake_xml()}],'outro')
        self.assertEqual(self.store.list_import_batches(self.other),[])

    def test_empty_unknown_and_corrupt_inputs_do_not_stop_siblings(self):
        batch=self.batch([{'filename':'vazio.xml','content':b''},{'filename':'nada.bin','content':b'abc'},
                          {'filename':'ruim.zip','content':b'PK broken'},{'filename':'bom.xml','content':fake_xml()}])
        self.assertEqual(batch['counts']['rejeitado'],3)
        self.assertEqual(len(self.store.list_documents(self.company)),1)
        self.assertEqual(self.store.read_import_original(self.company,batch['items'][0]['id'])['content'],b'')

    def test_nested_duplicate_and_unsafe_members(self):
        inner=zip_bytes([('a.xml',fake_xml())])
        packed=zip_bytes([('../escape.xml',fake_xml()),('pasta\\..\\escape.xml',b'x'),('/absoluto.xml',b'x'),
                          ('C:\\drive.xml',b'x'),('nested.zip',inner),('a.xml',fake_xml()),('./a.xml',fake_xml())])
        batch=self.batch([{'filename':'pacote.zip','content':packed}])
        self.assertEqual(batch['counts']['rejeitado'],6)
        self.assertEqual(len(self.store.list_documents(self.company)),1)
        self.assertEqual(self.store.read_import_original(self.company,batch['items'][0]['id'])['content'],packed)

    def test_zip_symlink_and_encryption_are_rejected(self):
        output=io.BytesIO()
        info=zipfile.ZipInfo('link.xml');info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16
        with zipfile.ZipFile(output,'w') as archive:archive.writestr(info,'/etc/passwd')
        members=archive_members(output.getvalue(),'ZIP')
        self.assertIn('error',members[0])
        packed=bytearray(zip_bytes([('a.xml',fake_xml())],zipfile.ZIP_STORED))
        central=packed.index(b'PK\x01\x02');packed[central+8]|=1
        self.assertIn('error',archive_members(bytes(packed),'ZIP')[0])

    def test_zip_bombs_and_entry_count_are_rejected(self):
        packed=zip_bytes([('muito.xml',b'x'*(2*1024*1024))])
        result=self.batch([{'filename':'bomba.zip','content':packed},{'filename':'bom.xml','content':fake_xml()}])
        self.assertEqual(result['items'][0]['status'],'rejeitado')
        self.assertEqual(len(self.store.list_documents(self.company)),1)
        many=zip_bytes([(f'{n}.txt',b'x') for n in range(501)])
        with self.assertRaises(ValueError):archive_members(many,'ZIP')

    def test_limits_and_no_partial_transaction_on_database_failure(self):
        with self.assertRaises(ValueError):self.batch([{'filename':'x.xml','content':b'x'}]*501)
        with self.assertRaises(ValueError):self.batch([{'filename':'../x.xml','content':b'x'}])
        with patch.object(self.store,'import_file',side_effect=sqlite3.OperationalError('synthetic failure')):
            with self.assertRaises(sqlite3.OperationalError):self.batch([{'filename':'a.xml','content':fake_xml()}])
        self.assertEqual(self.store.list_import_batches(self.company),[])
        self.assertEqual(self.store.list_files(self.company),[])

    def test_file_savepoint_rolls_back_failed_normalization_and_keeps_siblings(self):
        original=self.store._index_source
        def failing(company,period,file_row,*args,**kwargs):
            if file_row['filename']=='falha.xml':
                self.store._audit(company['id'],'provisorio_ficticio',{})
                raise ValueError('Falha sintética na normalização')
            return original(company,period,file_row,*args,**kwargs)
        with patch.object(self.store,'_index_source',side_effect=failing):
            batch=self.batch([{'filename':'primeiro.xml','content':fake_xml()},
                              {'filename':'falha.xml','content':fake_xml(number=2)},
                              {'filename':'ultimo.xml','content':fake_xml(number=3)}])
        self.assertEqual(batch['counts']['rejeitado'],1)
        self.assertEqual(len(self.store.list_files(self.company)),2)
        self.assertEqual(len(self.store.list_documents(self.company)),2)
        self.assertFalse(any(a['action']=='provisorio_ficticio' for a in self.store.list_audit(self.company)))
        failed=next(i for i in batch['items'] if i['filename']=='falha.xml')
        self.assertIsNone(failed['file_id'])
        self.assertEqual(self.store.read_import_original(self.company,failed['id'])['content'],fake_xml(number=2))

    def test_sped_profile_is_explicit_and_base64_api_is_strict(self):
        content=fake_sped()
        body={'company_id':self.company,'period_id':self.period,'request_key':'api-ficticia','inputs':[
            {'filename':'a.txt','content_base64':base64.b64encode(content).decode()}],'sped_profile':SPED_PROFILE}
        receipt=dispatch(self.store,'POST','source-receive',body)
        source=receipt['items'][0]
        self.store.organize_source(self.company,source['input_id'],self.store.save_work_cycle(self.company,'2026-09','2026-09',None,'Teste')['id'],source['snapshot_hash'],'Teste',SPED_PROFILE)
        self.assertTrue(self.store.list_files(self.company)[0]['analyses'])
        self.assertEqual(dispatch(self.store,'GET','source-inbox',{'company_id':self.company})[0]['input_id'],source['input_id'])
        body['inputs'][0]['content_base64']='@@@'
        with self.assertRaises(APIError):dispatch(self.store,'POST','source-receive',body)

    @unittest.skipUnless(ctypes.util.find_library('archive'),'libarchive unavailable')
    def test_real_7z_and_stored_rar4(self):
        original=fake_xml()
        for suffix,packed in [('7z',seven_zip('pasta/a.xml',original)),('rar',stored_rar('a.xml',original))]:
            with self.subTest(suffix=suffix):
                self.assertEqual(list(_native_members(packed, '7Z' if suffix=='7z' else 'RAR'))[0]['content'],original)
                batch=self.batch([{'filename':'pacote.'+suffix,'content':packed}],key=suffix)
                self.assertEqual(batch['items'][0]['status'],'expandido',batch)
                child=batch['items'][1]
                self.assertEqual(self.store.read_import_original(self.company,child['id'])['content'],original)
        self.assertEqual(len(self.store.list_documents(self.company)),1)

    def test_native_backend_timeout_absence_and_corruption_are_explicit(self):
        with patch('src.archive_reader.subprocess.run',side_effect=subprocess.TimeoutExpired('reader',20)):
            with self.assertRaisesRegex(ValueError,'20 segundos'):archive_members(b'bad','7Z')
        with patch('src.archive_reader.subprocess.run',return_value=subprocess.CompletedProcess([],1)):
            with self.assertRaisesRegex(ValueError,'indisponível'):archive_members(b'bad','RAR')
        for kind in ('7Z','RAR'):
            with self.assertRaises(ValueError):archive_members(b'bad',kind)
        with patch('src.archive_reader.sys.frozen',True,create=True):
            with self.assertRaisesRegex(ValueError,'executável'):archive_members(b'bad','7Z')

    def test_zip_crc_forged_directory_and_size_limits(self):
        packed=bytearray(zip_bytes([('a.xml',fake_xml())],zipfile.ZIP_STORED))
        local_name,local_extra=struct.unpack_from('<2H',packed,26)
        packed[30+local_name+local_extra] ^= 1
        self.assertIn('error',archive_members(bytes(packed),'ZIP')[0])
        many=bytearray(zip_bytes([(str(n)+'.xml',b'x') for n in range(501)]))
        end=many.rfind(b'PK\x05\x06')
        struct.pack_into('<2H',many,end+8,1,1)
        with self.assertRaises(ValueError):archive_members(bytes(many),'ZIP')
        packed=zip_bytes([('a.xml',b'12345')],zipfile.ZIP_STORED)
        with patch('src.archive_reader.MAX_MEMBER_BYTES',4):
            self.assertIn('error',archive_members(packed,'ZIP')[0])
        with patch('src.batch_import.MAX_EXPANDED_BYTES',10):
            with self.assertRaises(ValueError):self.batch([{'filename':'a.xml','content':fake_xml()}])
        with patch('src.archive_reader.ctypes.util.find_library',return_value=None):
            with self.assertRaisesRegex(ValueError,'indisponível'):list(_native_members(b'bad','RAR'))
        with self.assertRaises(ValueError):list(_native_members(stored_rar('../unsafe.xml',b'x'),'RAR'))

    def test_batch_time_budget_preserves_remaining_inputs(self):
        with patch('src.batch_import.time.monotonic',side_effect=[0,61,61]):
            batch=self.batch([{'filename':'a.xml','content':fake_xml()},{'filename':'a.zip','content':zip_bytes([('a.xml',fake_xml())])}])
        self.assertEqual(batch['counts']['rejeitado'],2)
        self.assertTrue(all('Tempo máximo' in item['details']['error'] for item in batch['items']))
        self.assertEqual(self.store.read_import_original(self.company,batch['items'][0]['id'])['content'],fake_xml())

    def test_safe_names(self):
        for name in ('../a','/a','\\\\host\\a','C:a','a/../b','a\0.xml'):
            with self.subTest(name=name),self.assertRaises(ValueError):safe_member(name)
        self.assertEqual(safe_member('a\\b.xml'),'a/b.xml')
        self.assertEqual(safe_member('./a.xml'),'a.xml')


if __name__=='__main__':unittest.main()
