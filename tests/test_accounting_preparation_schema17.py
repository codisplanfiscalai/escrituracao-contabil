"""XML draft evidence and tax memories enter books only through explicit posts."""
from copy import deepcopy
import unittest

import test_document_preparation as preparation
import test_tax_batch as batches
import test_tax_balances as balances
import test_work_application as work
from src.module_closure import CHECKS
from src.persistence import AccountingStore
from src.work_reports import accounting_report


class AccountingPreparationSchema17Tests(unittest.TestCase):
    setUp = work.WorkApplicationTests.setUp
    save = work.WorkApplicationTests.save
    post = work.WorkApplicationTests.post
    opening = work.WorkApplicationTests.opening
    document = preparation.DocumentPreparationTests.document
    config = preparation.DocumentPreparationTests.config
    prepare = preparation.DocumentPreparationTests.apply
    rule = preparation.DocumentPreparationTests.rule
    operation = batches.TaxBatchTests.operation
    setup_batch = batches.TaxBatchTests.setup_batch
    batch_apply = batches.TaxBatchTests.apply
    assess = balances.TaxBalanceTests.assess
    spec = balances.TaxBalanceTests.spec
    adjust = balances.TaxBalanceTests.apply

    def report(self, kind='balancete'):
        return accounting_report(self.s, self.c, self.cycle['id'], self.plan, report=kind)

    def close(self, module):
        preview = self.s.module_period_overview(self.c, self.cycle['id'], module)
        self.s.transition_module_period(self.c, self.cycle['id'], module, 'encerrada',
            preview['snapshot_hash'], 'Conferência sintética',
            {key: True for key in CHECKS[module]}, 'Evidência sintética')

    def item_draft(self, number=1):
        docs = [self.document(number)]
        config = self.config(item_mode='propor_itens_xml', total_source='vProd', copy_bases=['icms_base'])
        preview = self.s.preview_document_preparation(self.c, self.cycle['id'], docs, config)
        result = self.prepare(docs, config, key='prepare-'+str(number))
        row = result['operations'][0]
        payload = deepcopy(row['payload'])
        for item in payload['tax_items']:
            item['taxes'] = ['ICMS']
        return self.save(payload, row['operation_id'], row['version']), docs, config, preview, result

    def item_rule(self):
        self.rule(key='item', calculation={'scope':'item','method':'percentual',
            'reduction_percent':'0','base_rounding':'centavos_antes_da_taxa'})

    def test_xml_v4_only_enters_books_after_post_and_history_survives_new_source(self):
        self.opening()
        row, docs, config, preview, result = self.item_draft()
        evidence = deepcopy(row['payload']['xml_item_evidence'])
        entries = deepcopy(row['payload']['entries'])
        originals = [tuple(r) for r in self.s.db.execute('SELECT id,original,sha256 FROM files')]
        self.item_rule()
        calculated = self.s.preview_operation_tax(self.c, row['operation_id'])
        self.assertEqual(calculated['snapshot']['profile'], 'tributacao-itens-v4')
        applied = self.s.apply_operation_tax(self.c, row['operation_id'], calculated['snapshot_hash'],
            'xml-calculation', 'Conferência sintética')['operation']
        self.assertEqual(applied['payload']['entries'], entries)
        for kind in ('diario','razao','balancete'):
            self.assertEqual(self.report(kind)['entry_count'], 0)
        self.assertEqual(self.s.list_finance_titles(self.c), [])
        posted = self.post(applied)
        reports = {kind:self.report(kind) for kind in ('diario','razao','balancete')}
        for report in reports.values():
            self.assertEqual(report['totals']['debit'], '100.00')
            self.assertEqual(report['totals']['credit'], '100.00')
            self.assertEqual(report['entry_count'], 2)
        self.assertEqual({r['document_id'] for r in reports['diario']['rows']}, {docs[0]['document_id']})
        self.assess(); self.close('fiscal'); self.close('contabil')
        source = self.s.source_inbox(self.c)[0]
        revised = deepcopy(source['evidence']); revised['issues'].append('Observação sintética posterior')
        with self.s.db:
            self.s._append_source_revision(self.c, source['input_id'], revised, 'Teste')
        historical = self.s.get_work_operation(self.c, row['operation_id'])
        self.assertEqual(historical['payload'], posted['payload'])
        self.assertEqual(historical['payload']['xml_item_evidence'], evidence)
        for kind, report in reports.items():
            self.assertEqual(self.report(kind), report)
        retry = self.s.apply_document_preparation(self.c, self.cycle['id'], docs, config,
            preview['snapshot_hash'], 'prepare-1', 'Teste', 'Conferência sintética', True)
        self.assertTrue(retry['duplicate']); self.assertEqual(retry['snapshot'], result['snapshot'])
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_movements').fetchone()[0], 2)
        self.assertEqual([tuple(r) for r in self.s.db.execute('SELECT id,original,sha256 FROM files')], originals)

    def test_mixed_xml_v2_v4_tax_batch_keeps_individual_memories_and_explicit_entries(self):
        first = self.prepare([self.document()], key='header-evidence')['operations'][0]
        second, *_ = self.item_draft(2)
        self.s.save_tax_code(self.c, 'cfop', '1101', {'description':'Código sintético',
            'valid_from':'2026-09-01','valid_to':'','source_reference':'Fixture'}, 'ativo', 0, 'Teste')
        self.rule(key='document', cfop='1101')
        self.item_rule()
        payload = deepcopy(first['payload']); payload['fiscal']['cfop'] = '1101'
        first = self.save(payload, first['operation_id'], first['version'])
        ids = [first['operation_id'], second['operation_id']]
        preview = self.s.preview_tax_batch(self.c, self.cycle['id'], ids)
        result = self.batch_apply(ids, preview)
        self.assertEqual([r['snapshot']['profile'] for r in result['calculations']],
            ['tributacao-parametrizada-v2','tributacao-itens-v4'])
        self.assertEqual(self.report()['entry_count'], 0)
        self.assertEqual(self.s.list_finance_titles(self.c), [])
        for operation_id in ids:
            self.post(self.s.get_work_operation(self.c, operation_id))
        report = self.report('diario')
        self.assertEqual(report['totals']['debit'], '200.00')
        self.assertEqual(report['entry_count'], 4)
        self.assertEqual({r['operation_id'] for r in report['rows']}, set(ids))
        for memory in result['calculations']:
            self.assertIn('xml_item_evidence', memory['snapshot'])
        with self.assertRaises(ValueError):
            self.s.document_preparation_detail(self.other, self.s.document_preparations(self.c, self.cycle['id'])[0]['id'])
        with self.assertRaises(ValueError):
            accounting_report(self.s, self.other, self.cycle['id'], self.plan)

    def test_accounting_lock_blocks_preparation_but_observation_and_receipt_remain_available(self):
        self.opening()
        docs = [self.document()]
        config = self.config()
        preview = self.s.preview_document_preparation(self.c, self.cycle['id'], docs, config)
        before = self.report()
        self.close('contabil')
        with self.assertRaisesRegex(ValueError, 'contabil encerrado'):
            self.s.apply_document_preparation(self.c, self.cycle['id'], docs, config,
                preview['snapshot_hash'], 'blocked', 'Teste', 'Teste', True)
        source = self.s._work_source(self.c, docs[0]['document_id'])
        self.assertEqual(len(self.s.document_item_values(self.c, docs[0]['document_id'], source['observations'][0]['id'])['snapshot']['values']['items']), 2)
        self.s.receive_sources(self.c, [{'filename':'depois.xml','content':preparation.item_xml(2)}], 'after-close')
        self.assertEqual(self.report(), before)
        self.assertEqual(self.s.module_period_state(self.c, '2026-09', 'fiscal')['state'], 'aberta')
        self.assertEqual(self.s.document_preparations(self.c, self.cycle['id']), [])

    def test_schema16_to17_preserves_tax_batch_originals_books_and_locks(self):
        self.opening()
        _, ids, preview = self.setup_batch()
        batch = self.batch_apply(ids, preview)
        for operation_id in ids:
            self.post(self.s.get_work_operation(self.c, operation_id))
        self.adjust(self.spec(amount='3.00'))
        self.assess(); self.close('fiscal'); self.close('contabil')
        before = self.report()
        tables = ('files','work_movements','tax_calculations','tax_calculation_batches',
            'tax_assessment_adjustment_versions','tax_assessment_versions','module_period_versions')
        preserved = {t:[tuple(r) for r in self.s.db.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in tables}
        with self.s.db:
            self.s.db.execute('DROP TABLE document_preparation_batches')
            self.s.db.execute('UPDATE schema_version SET version=16')
        self.s.close()
        self.s = AccountingStore(self.path, actor='operador-sintetico')
        self.addCleanup(self.s.close)
        self.assertEqual(self.s.db.execute('SELECT version FROM schema_version').fetchone()[0], 17)
        self.assertEqual(self.report(), before)
        for table, rows in preserved.items():
            self.assertEqual([tuple(r) for r in self.s.db.execute('SELECT * FROM '+table+' ORDER BY rowid')], rows)
        self.assertEqual(self.s.tax_batch_detail(self.c, batch['id'])['snapshot'], batch['snapshot'])
        self.assertEqual(self.s.document_preparations(self.c, self.cycle['id']), [])
        self.assertEqual(self.s.db.execute('PRAGMA foreign_key_check').fetchall(), [])
