"""Catalogue contracts introduced in 14 remain immutable on schema 16."""
import unittest
import test_work_application as work
import test_tax_items as items
import test_tax_catalog_import as catalog
from src.module_closure import CHECKS
from src.persistence import AccountingStore
from src.work_reports import accounting_report


class AccountingCatalogSchema14Tests(unittest.TestCase):
    setUp = work.WorkApplicationTests.setUp
    save = work.WorkApplicationTests.save
    post = work.WorkApplicationTests.post
    document = work.WorkApplicationTests.document
    opening = work.WorkApplicationTests.opening
    rule = items.TaxItemTests.rule
    calc = items.TaxItemTests.calc
    item = items.TaxItemTests.item
    operation = items.TaxItemTests.operation
    apply = items.TaxItemTests.apply
    receive = catalog.TaxCatalogImportTests.receive
    preview = catalog.TaxCatalogImportTests.preview
    catalog_apply = catalog.TaxCatalogImportTests.apply

    def report(self):
        return accounting_report(self.s,self.c,self.cycle['id'],self.plan)

    def calculated(self):
        receipt = self.receive()
        self.catalog_apply(receipt)
        self.rule(key='debit',cfop='1102',rate='2.5',item_treatment='D',calculation=self.calc(reduction_percent='10'))
        self.rule(key='credit',cfop='1102',rate='7',effect='credito',item_treatment='C',calculation=self.calc())
        operation = self.operation([self.item(total='60.00',cfop='1102',treatment='D'),
                                    self.item('B','40.30',cfop='1102',treatment='C')])
        _, result = self.apply(operation)
        return receipt,result

    def close_modules(self):
        preview = self.s.preview_tax_assessment(self.c,self.cycle['id'])
        row = self.s.create_tax_assessment(self.c,self.cycle['id'],preview['snapshot_hash'],'catalog-assess','Conferido')
        self.s.validate_tax_assessment(self.c,self.cycle['id'],row['id'],row['snapshot_hash'],'Conferido',True)
        for module in ('fiscal','contabil'):
            state = self.s.module_period_overview(self.c,self.cycle['id'],module)
            self.s.transition_module_period(self.c,self.cycle['id'],module,'encerrada',state['snapshot_hash'],
                                             'Conferência sintética',{k:True for k in CHECKS[module]},'Memória sintética')

    def test_import_provenance_item_effects_and_future_activation_preserve_closed_books(self):
        self.opening()
        receipt,result = self.calculated()
        posted = self.post(result['operation'])
        proof = result['operation']['payload']['tax_calculation']
        origins = [line['rule']['catalog_references']['cfop']['data']['import_origin']
                   for line in proof['memory']['lines']]
        self.assertTrue(all(o['raw_sha256']==receipt['raw_sha256'] and o['edition']=='Edição sintética 1' for o in origins))
        self.assertEqual(self.s.preview_tax_assessment(self.c,self.cycle['id'])['snapshot']['totals'][0]['saldo_aritmetico'],'-1.47')
        self.close_modules()
        before = self.report()
        self.assertEqual(before['totals']['debit'],'100.30')
        received = self.receive([catalog.record(description='Edição futura sintética')],
                                catalog.meta(edition='Edição sintética 2'),key='future-receipt')
        with self.assertRaisesRegex(ValueError,'encerrado'):
            self.catalog_apply(received,key='closed-activation')
        self.catalog_apply(received,key='future-activation',day='2026-10-01')
        self.assertEqual(self.report(),before)
        self.assertEqual(self.s.get_work_operation(self.c,posted['operation_id'])['payload']['tax_calculation'],proof)
        with self.assertRaises(ValueError):
            self.s.catalog_import_original(self.other,receipt['id'])
        self.assertEqual(self.s.module_period_state(self.c,'2026-09','fiscal')['state'],'encerrada')
        self.assertEqual(self.s.module_period_state(self.c,'2026-09','contabil')['state'],'encerrada')

    def test_changed_catalog_blocks_posting_until_recalculation_without_partial_accounting(self):
        _,result = self.calculated()
        preserved = result['operation']['payload']['tax_calculation']
        received = self.receive([catalog.record(description='Correção sintética revista')],
                                catalog.meta(edition='Edição sintética 2'),key='revised-receipt')
        self.catalog_apply(received,key='revised-activation')
        with self.assertRaises(ValueError):
            self.post(self.s.get_work_operation(self.c,result['operation']['operation_id']))
        self.assertEqual(self.report()['entry_count'],0)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_movements').fetchone()[0],0)
        self.assertEqual(self.s.list_finance_titles(self.c),[])
        current = self.s.get_work_operation(self.c,result['operation']['operation_id'])
        _,recalculated = self.apply(current,key='catalog-recalculation')
        self.post(recalculated['operation'])
        self.assertEqual(self.report()['totals']['debit'],'100.30')
        self.assertEqual(self.report()['entry_count'],2)
        self.assertEqual(preserved['memory']['lines'][0]['rule']['catalog_references']['cfop']['data']['import_origin']['edition'],'Edição sintética 1')
        self.assertEqual(recalculated['operation']['payload']['tax_calculation']['memory']['lines'][0]['rule']['catalog_references']['cfop']['data']['import_origin']['edition'],'Edição sintética 2')

    def test_schema13_upgrade_preserves_item_memories_originals_movements_and_both_locks(self):
        self.opening()
        self.rule(calculation=self.calc())
        _,result = self.apply(self.operation([self.item()]))
        posted = self.post(result['operation'])
        self.close_modules()
        before = self.report()
        originals = [tuple(r) for r in self.s.db.execute('SELECT id,sha256,original FROM files ORDER BY id')]
        movements = [tuple(r) for r in self.s.db.execute('SELECT revision_id,line,payload FROM work_movements ORDER BY revision_id,line')]
        calculations = [tuple(r) for r in self.s.db.execute('SELECT id,snapshot,snapshot_hash FROM tax_calculations ORDER BY id')]
        with self.s.db:
            for table in ('tax_calculation_batches','tax_assessment_adjustment_versions',
                          'tax_catalog_import_applications','tax_catalog_scopes','tax_catalog_imports'):
                self.s.db.execute('DROP TABLE '+table)
            self.s.db.execute('UPDATE schema_version SET version=13')
        self.s.close()
        self.s = AccountingStore(self.path,actor='operador-sintetico')
        self.addCleanup(self.s.close)
        self.assertEqual(self.s.db.execute('SELECT version FROM schema_version').fetchone()[0],16)
        self.assertEqual(self.report(),before)
        self.assertEqual([tuple(r) for r in self.s.db.execute('SELECT id,sha256,original FROM files ORDER BY id')],originals)
        self.assertEqual([tuple(r) for r in self.s.db.execute('SELECT revision_id,line,payload FROM work_movements ORDER BY revision_id,line')],movements)
        self.assertEqual([tuple(r) for r in self.s.db.execute('SELECT id,snapshot,snapshot_hash FROM tax_calculations ORDER BY id')],calculations)
        self.assertEqual(self.s.get_work_operation(self.c,posted['operation_id'])['payload']['tax_calculation'],result['operation']['payload']['tax_calculation'])
        self.assertTrue(all(self.s.module_period_state(self.c,'2026-09',module)['state']=='encerrada' for module in ('fiscal','contabil')))
        self.assertEqual(self.s.catalog_imports(self.c),[])
        self.assertEqual(self.s.db.execute('PRAGMA foreign_key_check').fetchall(),[])
