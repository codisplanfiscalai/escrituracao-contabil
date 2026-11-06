"""Synthetic catalogues exercise provenance, namespace and transaction boundaries."""
import copy
from datetime import date
import hashlib
import json
import unittest
import test_work_application as fixtures
from src.persistence import AccountingStore
from src.module_closure import CHECKS


def record(code='1102', **extra):
    return {'code':code,'description':'Código inteiramente sintético','valid_from':'2026-01-01','valid_to':'',**extra}


def meta(kind='cfop', **extra):
    return {'kind':kind,'system':{'cfop':'CFOP','ncm':'NCM','revenue':'DARF','service':'LC116'}[kind],
            'jurisdiction':'BR','publisher':'Órgão fictício para teste','source_url':'https://example.invalid/catalogo',
            'edition':'Edição sintética 1','retrieved_on':date.today().isoformat(),'coverage':'parcial',
            'transformation_reference':'Arquivo de teste criado no padrão; sem validade oficial',**extra}


def json_bytes(rows):
    return json.dumps({'profile':'cadastro-fiscal-v1','records':rows},ensure_ascii=False).encode()


class TaxCatalogImportTests(unittest.TestCase):
    setUp=fixtures.WorkApplicationTests.setUp
    save=fixtures.WorkApplicationTests.save
    document=fixtures.WorkApplicationTests.document

    def receive(self, rows=None, metadata=None, key='receive-1', company=None, raw=None, filename='cadastro.json'):
        return self.s.receive_catalog_import(company or self.c,filename,raw if raw is not None else json_bytes(rows or [record()]),
                                             metadata or meta(),key,'Recepção sintética')['import']

    def preview(self, receipt, codes=None, day='2026-09-01', company=None):
        return self.s.preview_catalog_application(company or self.c,receipt['id'],codes or ['1102'],day)

    def apply(self, receipt, preview=None, codes=None, day='2026-09-01', key='apply-1', company=None, **extra):
        company=company or self.c;codes=codes or ['1102'];preview=preview or self.preview(receipt,codes,day,company)
        return self.s.apply_catalog_import(company,receipt['id'],codes,day,preview['snapshot_hash'],key,'Aplicação sintética','Revisão sintética do conteúdo e do escopo',True,**extra)

    def test_receipt_preserves_bytes_hashes_and_does_not_require_period_or_activate(self):
        original=b'\xef\xbb\xbfcode;description;valid_from;valid_to\r\n1102;Sintetico;2026-01-01;\r\n'
        received=self.receive(company=self.other,raw=original,filename='../origem.csv')
        self.assertEqual(received['raw_sha256'],hashlib.sha256(original).hexdigest())
        download=self.s.catalog_import_original(self.other,received['id'])
        self.assertEqual(download['content'],original)
        self.assertEqual(download['name'],f'cadastro-{received["id"]}.csv')
        self.assertEqual(self.s.tax_catalog(self.other),[])
        self.assertEqual(self.s.work_cycles(self.other),[])
        self.assertEqual(received['metadata']['coverage'],'parcial')
        self.assertTrue(any('não autenticam' in text for text in received['limits']))

    def test_reviewed_application_versions_codes_and_preserves_source_dates(self):
        receipt=self.receive([record('1102'),record('2102')])
        preview=self.preview(receipt,['2102','1102'])
        self.assertEqual(preview['snapshot']['blockers'],[])
        result=self.apply(receipt,preview,['2102','1102'])
        self.assertEqual(len(result['snapshot']['versions']),2)
        self.assertEqual(result['snapshot']['raw_sha256'],receipt['raw_sha256'])
        self.assertEqual(result['snapshot']['versions'][0]['data']['import_origin']['edition'],'Edição sintética 1')
        row=self.s.resolve_tax_code(self.c,'cfop','1102','2026-09-01')
        self.assertEqual(row['data']['valid_from'],'2026-09-01')
        origin=row['data']['import_origin']
        self.assertEqual(origin['source_valid_from'],'2026-01-01')
        self.assertEqual(origin['raw_sha256'],receipt['raw_sha256'])
        self.assertEqual(origin['authority_status'],'origem_declarada_na_importacao')
        self.assertEqual(origin['jurisdiction'],'BR')
        with AccountingStore(self.path) as reopened:
            self.assertEqual(reopened.catalog_applications(self.c,receipt['id'])[0]['snapshot_hash'],result['snapshot_hash'])
            self.assertEqual(reopened.catalog_import_original(self.c,receipt['id'])['content'],json_bytes([record('1102'),record('2102')]))

    def test_repeated_receipt_and_application_are_idempotent_including_selection_order(self):
        raw=json_bytes([record('1102'),record('2102')]);receipt=self.receive(raw=raw)
        again=self.s.receive_catalog_import(self.c,'cadastro.json',raw,meta(),'receive-1','Recepção sintética')
        self.assertTrue(again['duplicate']);self.assertEqual(again['import']['id'],receipt['id'])
        preview=self.preview(receipt,['1102','2102']);first=self.apply(receipt,preview,['1102','2102'])
        repeated=self.apply(receipt,preview,['2102','1102'])
        self.assertEqual(repeated['id'],first['id'])
        self.assertEqual(len(self.s.tax_catalog(self.c)),2)
        with self.assertRaisesRegex(ValueError,'outro conteúdo'):
            self.s.receive_catalog_import(self.c,'cadastro.json',json_bytes([record(description='Alterado')]),meta(),'receive-1','Recepção sintética')

    def test_preview_staleness_and_legacy_scope_require_explicit_review(self):
        receipt=self.receive()
        preview=self.preview(receipt)
        data={'description':'Legado sintético','valid_from':'2026-01-01','valid_to':'','source_reference':'Manual'}
        self.s.save_tax_code(self.c,'cfop','1102',data,'ativo',0,'Teste')
        with self.assertRaisesRegex(ValueError,'alterados'):self.apply(receipt,preview)
        preview=self.preview(receipt)
        self.assertEqual(preview['snapshot']['legacy_count'],1)
        with self.assertRaisesRegex(ValueError,'legados'):self.apply(receipt,preview)
        self.apply(receipt,preview,acknowledge_legacy=True)
        versions=self.s.tax_catalog(self.c)
        self.assertEqual([r['version'] for r in versions],[2,1])
        self.assertNotIn('import_origin',versions[1]['data'])

    def test_namespaces_and_municipal_jurisdictions_cannot_be_mixed(self):
        first=self.receive([record('010101')],meta('service',system='NFSE_NACIONAL'))
        self.apply(first,codes=['010101'])
        other=self.receive([record('010101')],meta('service',system='SERVICO_MUNICIPAL',jurisdiction='MUN:0000000'),key='municipal')
        preview=self.preview(other,['010101'])
        self.assertTrue(any('Sistema/jurisdição' in x for x in preview['snapshot']['blockers']))
        with self.assertRaises(ValueError):self.apply(other,preview,['010101'],key='municipal-apply')
        self.assertEqual(len(self.s.tax_catalog(self.c)),1)
        # Other companies own independent namespace choices.
        own=self.receive([record('010101')],meta('service',system='SERVICO_MUNICIPAL',jurisdiction='MUN:0000000'),company=self.other)
        self.apply(own,codes=['010101'],company=self.other)

    def test_distinct_codes_from_different_systems_can_coexist_without_mapping(self):
        federal=self.receive([record('0000')],meta('revenue'))
        self.apply(federal,codes=['0000'])
        state=self.receive([record('SYN-2')],meta('revenue',system='RECEITA_ESTADUAL',jurisdiction='UF:SP'),key='state')
        self.apply(state,codes=['SYN-2'],key='state-apply')
        current={r['code']:r for r in self.s.tax_catalog(self.c)}
        self.assertEqual(current['0000']['data']['import_origin']['system'],'DARF')
        self.assertEqual(current['SYN-2']['data']['import_origin']['jurisdiction'],'UF:SP')

    def test_concurrent_activation_only_one_preview_can_commit(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        receipt=self.receive();preview=self.preview(receipt);barrier=Barrier(2)
        def activate(index):
            with AccountingStore(self.path,actor='synthetic-'+str(index)) as store:
                barrier.wait(timeout=10)
                try:
                    store.apply_catalog_import(self.c,receipt['id'],['1102'],'2026-09-01',preview['snapshot_hash'],'race-'+str(index),'Teste','Revisão sintética',True)
                    return 'committed'
                except ValueError as error:
                    return str(error)
        with ThreadPoolExecutor(max_workers=2) as executor:results=list(executor.map(activate,[1,2]))
        self.assertEqual(results.count('committed'),1,results)
        self.assertTrue(any('alterados' in r for r in results),results)
        self.assertEqual(len(self.s.tax_catalog(self.c)),1)
        self.assertEqual(len(self.s.catalog_applications(self.c,receipt['id'])),1)

    def test_missing_codes_are_not_deactivated_and_new_edition_keeps_history(self):
        first=self.receive([record('1102'),record('2102')]);self.apply(first,codes=['1102','2102'])
        second=self.receive([record('1102',description='Edição sintética 2')],meta(edition='Edição sintética 2'),key='edition-2')
        self.apply(second,key='apply-2',day='2026-10-01')
        self.assertEqual(self.s.resolve_tax_code(self.c,'cfop','2102','2026-10-01')['state'],'ativo')
        self.assertEqual(self.s.resolve_tax_code(self.c,'cfop','1102','2026-09-01')['version'],1)
        self.assertEqual(self.s.resolve_tax_code(self.c,'cfop','1102','2026-10-01')['version'],2)
        self.assertEqual(len(self.s.catalog_imports(self.c)),2)

    def test_fiscal_closure_blocks_activation_but_allows_receipt_and_future_cut(self):
        state=self.s.module_period_overview(self.c,self.cycle['id'],'fiscal')
        self.s.transition_module_period(self.c,self.cycle['id'],'fiscal','encerrada',state['snapshot_hash'],'Teste',{k:True for k in CHECKS['fiscal']},'Conferência sintética')
        receipt=self.receive()
        preview=self.preview(receipt)
        self.assertTrue(preview['snapshot']['blockers'])
        with self.assertRaisesRegex(ValueError,'encerrado'):self.apply(receipt,preview)
        self.assertEqual(self.s.tax_catalog(self.c),[])
        self.apply(receipt,day='2026-10-01')
        self.assertEqual(self.s.module_period_state(self.c,'2026-09','fiscal')['state'],'encerrada')

    def test_atomic_failure_rolls_back_all_codes_scope_and_application(self):
        receipt=self.receive([record('1102'),record('2102')]);preview=self.preview(receipt,['1102','2102'])
        original=self.s._audit
        def fail(company,action,details):
            if action=='codigo_tributario_versionado' and details['code']=='2102':raise ValueError('Falha sintética')
            return original(company,action,details)
        self.s._audit=fail
        with self.assertRaisesRegex(ValueError,'Falha sintética'):self.apply(receipt,preview,['1102','2102'])
        self.s._audit=original
        self.assertEqual(self.s.tax_catalog(self.c),[])
        self.assertEqual(self.s.catalog_applications(self.c,receipt['id']),[])
        self.assertIsNone(self.s._catalog_scope(self.c,'cfop','1102'))
        self.apply(receipt,preview,['1102','2102'])

    def test_selection_dates_review_and_company_scope_are_enforced(self):
        receipt=self.receive([record(valid_to='2026-09-30')])
        for codes in ([],['1102','1102'],['9999'],[1102],['1102']*501):
            with self.assertRaises(ValueError):self.s.preview_catalog_application(self.c,receipt['id'],codes,'2026-09-01')
        expired=self.preview(receipt,day='2026-10-01')
        self.assertTrue(any('sem vigência' in b for b in expired['snapshot']['blockers']))
        with self.assertRaises(ValueError):self.apply(receipt,expired,day='2026-10-01')
        for method in (self.s.catalog_import_detail,self.s.catalog_import_original,self.s.catalog_applications):
            with self.assertRaises(ValueError):method(self.other,receipt['id'])
        preview=self.preview(receipt)
        with self.assertRaises(ValueError):self.s.apply_catalog_import(self.c,receipt['id'],['1102'],'2026-09-01',preview['snapshot_hash'],'no-review','Teste','',False)

    def test_invalid_files_do_not_create_receipts_or_silently_infer_native_layouts(self):
        invalid=[(b'{}','x.json'),(json.dumps([record()]).encode(),'x.json'),(b'{"profile":"cadastro-fiscal-v1","profile":"cadastro-fiscal-v1","records":[]}','x.json'),
                 (json_bytes([record(),record()]),'x.json'),(json_bytes([record(code=1102)]),'x.json'),
                 (json_bytes([record(valid_from='01/01/2026')]),'x.json'),(json_bytes([record(valid_to='2025-01-01')]),'x.json'),
                 (b'Codigo;Descricao\n1102;teste','x.csv'),(b'"unclosed','x.csv'),(b'\xff','x.csv'),(b'not a table','x.pdf')]
        for raw,name in invalid:
            with self.subTest(name=name,raw=raw[:30]):
                with self.assertRaises(ValueError):self.receive(raw=raw,filename=name)
        self.assertEqual(self.s.catalog_imports(self.c),[])

    def test_leading_zero_codes_and_paginated_search_are_preserved(self):
        rows=[record(f'{n:08d}',description=f'Item sintético {n}') for n in range(105)]
        receipt=self.receive(rows,meta('ncm'))
        self.assertEqual(receipt['total_records'],105);self.assertEqual(len(receipt['records']),100)
        last=self.s.catalog_import_detail(self.c,receipt['id'],offset='100')
        self.assertEqual(len(last['records']),5)
        found=self.s.catalog_import_detail(self.c,receipt['id'],query='00000001')
        self.assertEqual([r['code'] for r in found['records']],['00000001'])
        self.apply(receipt,codes=['00000001'])
        self.assertEqual(self.s.tax_catalog(self.c)[0]['code'],'00000001')

    def test_active_catalog_pages_are_bounded_and_history_remains_accessible(self):
        rows=[record(f'{n:08d}') for n in range(105)];receipt=self.receive(rows,meta('ncm'))
        self.apply(receipt,codes=[r['code'] for r in rows])
        config=self.s.tax_configuration(self.c)
        self.assertEqual(len(config['catalog']),100)
        self.assertEqual(config['catalog_page']['total'],105)
        self.assertEqual(len(self.s.tax_code_page(self.c,kind='ncm',offset='100')['items']),5)
        found=self.s.tax_code_page(self.c,kind='ncm',query='00000001')
        self.assertEqual(len(found['items']),1)
        row=found['items'][0]
        self.s.save_tax_code(self.c,'ncm','00000001',{key:row['data'][key] for key in ('description','valid_from','valid_to','source_reference')},'ativo',1,'Revisão manual')
        history=self.s.tax_code_page(self.c,kind='ncm',code='00000001')
        self.assertEqual([r['version'] for r in history['items']],[2,1])
        self.assertIn('import_origin',history['items'][1]['data'])

    def test_metadata_cannot_claim_completeness_or_implicit_jurisdiction(self):
        for changes in ({'source_url':'http://example.invalid'},{'source_url':'https://user:pass@example.invalid'},
                        {'coverage':'completa'},{'jurisdiction':'SP'},{'retrieved_on':'9999-01-01'},{'system':'NFSE_NACIONAL'}):
            with self.assertRaises(ValueError):self.receive(metadata=meta(**changes))
        with self.assertRaises(ValueError):self.receive([record('1.01')],meta('service',system='SERVICO_MUNICIPAL'))

    def test_storage_tampering_is_detected(self):
        receipt=self.receive()
        self.s.db.execute('UPDATE tax_catalog_imports SET raw_bytes=? WHERE id=?',(b'changed',receipt['id']));self.s.db.commit()
        with self.assertRaisesRegex(ValueError,'alterado'):self.s.catalog_import_original(self.c,receipt['id'])

    def test_migration_13_to_14_preserves_tax_versions_and_module_lock(self):
        self.s.save_tax_code(self.c,'cfop','1102',{'description':'Manual sintético','valid_from':'2026-01-01','valid_to':'','source_reference':'Teste'},'ativo',0,'Teste')
        before=self.s.tax_catalog(self.c)
        state=self.s.module_period_overview(self.c,self.cycle['id'],'fiscal')
        self.s.transition_module_period(self.c,self.cycle['id'],'fiscal','encerrada',state['snapshot_hash'],'Teste',{k:True for k in CHECKS['fiscal']},'Conferência sintética')
        for table in ('tax_catalog_import_applications','tax_catalog_scopes','tax_catalog_imports'):self.s.db.execute('DROP TABLE '+table)
        self.s.db.execute('UPDATE schema_version SET version=13');self.s.db.commit()
        with AccountingStore(self.path) as reopened:
            self.assertEqual(reopened.db.execute('SELECT version FROM schema_version').fetchone()[0],16)
            self.assertEqual(reopened.tax_catalog(self.c),before)
            self.assertEqual(reopened.module_period_state(self.c,'2026-09','fiscal')['state'],'encerrada')
            self.assertEqual(reopened.catalog_imports(self.c),[])
            self.assertEqual(reopened.db.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_calculation_memory_carries_import_provenance_and_changed_catalog_requires_recalculation(self):
        receipt=self.receive();self.apply(receipt)
        self.s.save_tax_rule(self.c,'synthetic','Regra sintética',{'tax':'ICMS','rate':'2.5','base_field':'total','effect':'debito','operation':'entrada','cfop':'1102',
            'valid_from':'2026-09-01','rounding':'meio_para_cima','validation_reference':'Teste'},'aprovada',0,'Teste')
        payload=self.document();payload['fiscal']['cfop']='1102'
        operation=self.save(payload);preview=self.s.preview_operation_tax(self.c,operation['operation_id'])
        applied=self.s.apply_operation_tax(self.c,operation['operation_id'],preview['snapshot_hash'],'calc-from-import','Teste')
        reference=applied['calculation']['snapshot']['lines'][0]['rule']['catalog_references']['cfop']['data']['import_origin']
        self.assertEqual(reference['raw_sha256'],receipt['raw_sha256'])
        self.assertEqual(reference['edition'],'Edição sintética 1')
        self.s.save_tax_code(self.c,'cfop','1102',{'description':'Correção manual','valid_from':'2026-09-01','valid_to':'','source_reference':'Revisão manual explícita'},'ativo',1,'Teste')
        current=self.s.get_work_operation(self.c,operation['operation_id'])
        self.assertFalse(current['validation']['ready'])
        self.assertEqual(applied['calculation']['snapshot']['lines'][0]['rule']['catalog_references']['cfop']['data']['import_origin'],reference)


if __name__=='__main__':unittest.main()
