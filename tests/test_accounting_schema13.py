"""Accounting/tax/closing contracts introduced in 13, checked on schema 17."""
from copy import deepcopy
import unittest

import test_work_application as work
import test_tax_engine as tax
from src.module_closure import CHECKS
from src.persistence import AccountingStore
from src.work_reports import accounting_report
from test_persistence import fake_xml


class AccountingSchema13Tests(unittest.TestCase):
    setUp = work.WorkApplicationTests.setUp
    save = work.WorkApplicationTests.save
    post = work.WorkApplicationTests.post
    document = work.WorkApplicationTests.document
    opening = work.WorkApplicationTests.opening
    rule = tax.TaxEngineTests.rule
    calculate = tax.TaxEngineTests.calculate

    def report(self, report='balancete'):
        return accounting_report(self.s, self.c, self.cycle['id'], self.plan, report=report)

    def change(self, module, target='encerrada'):
        preview = self.s.module_period_overview(self.c, self.cycle['id'], module)
        return self.s.transition_module_period(
            self.c, self.cycle['id'], module, target, preview['snapshot_hash'],
            'Conferência sintética integrada', {key: True for key in CHECKS[module]},
            'Evidência inteiramente sintética')

    def adjustment(self, amount='10.00'):
        p = self.s.prepare_work_operation(self.c, self.cycle['id'], operation='ajuste')
        p['reference'] = 'Ajuste contábil sintético'
        p['fiscal'].update(total=amount, posting_date='2026-09-20')
        for entry, code in zip(p['entries'], ['1.1.1', '2.1']):
            entry.update(account_id=self.ids[code], amount=amount,
                         date='2026-09-20', memo='Partida explícita sintética')
        return p

    def assessment(self):
        preview = self.s.preview_tax_assessment(self.c, self.cycle['id'])
        row = self.s.create_tax_assessment(self.c, self.cycle['id'], preview['snapshot_hash'],
                                           'joint-assessment', 'Revisão sintética')
        return self.s.validate_tax_assessment(self.c, self.cycle['id'], row['id'],
                                              row['snapshot_hash'], 'Conferido', True)

    def test_tax_calculation_preserves_explicit_postings_and_read_only_reports(self):
        original, _, applied = self.calculate()
        entries = deepcopy(original['payload']['entries'])
        self.assertEqual(applied['operation']['payload']['entries'], entries)
        posted = self.post(applied['operation'])
        self.assertEqual(posted['payload']['fiscal']['icms_amount'], '2.51')
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_movements').fetchone()[0], 2)
        raw = self.s.db.execute('SELECT snapshot,snapshot_hash FROM tax_calculations').fetchone()
        previous = tuple(raw)
        changes = self.s.db.total_changes
        for kind in ('diario', 'razao', 'balancete'):
            report = self.report(kind)
            self.assertEqual(report['totals']['debit'], '100.30')
            self.assertEqual(report['totals']['credit'], '100.30')
            self.assertEqual(report['entry_count'], 2)
        self.assertEqual(self.s.db.total_changes, changes)
        self.assertEqual(tuple(self.s.db.execute('SELECT snapshot,snapshot_hash FROM tax_calculations').fetchone()), previous)
        book = self.s.work_books(self.c, self.cycle['id'])
        self.assertEqual(book['fiscal_book'][0]['icms_amount'], '2.51')
        self.assertEqual(self.s.get_work_operation(self.c, posted['operation_id'])['payload']['tax_calculation'],
                         applied['operation']['payload']['tax_calculation'])
        self.assertEqual(self.s.db.execute('SELECT version FROM schema_version').fetchone()[0], 17)

    def test_independent_closing_keeps_reports_readable_and_receipt_cannot_bypass(self):
        self.opening()
        _, _, applied = self.calculate()
        self.post(applied['operation'])
        with self.assertRaisesRegex(ValueError, 'apuração parametrizada'):
            self.change('fiscal')
        self.assessment()
        before = self.report()
        self.change('fiscal')
        self.assertEqual(self.report(), before)
        self.assertEqual(self.s.module_period_state(self.c, '2026-09', 'contabil')['state'], 'aberta')
        self.post(self.save(self.adjustment()))
        self.assertEqual(self.report()['totals']['debit'], '110.30')
        self.change('contabil')
        closed = self.report()
        count = self.s.db.execute('SELECT COUNT(*) FROM work_movements').fetchone()[0]
        with self.assertRaisesRegex(ValueError, 'contabil encerrado'):
            self.save(self.adjustment())
        source = self.s.receive_sources(self.c, [{'filename':'NovaSintetica.xml','content':fake_xml(number=2)}],
                                        'receipt-after-joint-close')['items'][0]
        with self.assertRaisesRegex(ValueError, 'fiscal encerrado'):
            self.s.organize_source(self.c, source['input_id'], self.cycle['id'], source['snapshot_hash'], 'Teste')
        self.assertEqual(self.s.source_original(self.c, source['input_id'])['content'], fake_xml(number=2))
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_movements').fetchone()[0], count)
        self.assertEqual(self.report(), closed)

    def test_accounting_closed_fiscal_open_blocks_mixed_calculated_values(self):
        self.opening()
        self.change('contabil')
        self.rule()
        payload = self.document()
        payload['fiscal'].update(icms_base='100.30', icms_amount='2.51')
        count = self.s.db.execute('SELECT COUNT(*) FROM work_operations').fetchone()[0]
        with self.assertRaisesRegex(ValueError, 'contabil encerrado'):
            self.save(payload)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_operations').fetchone()[0], count)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_movements').fetchone()[0], 0)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM tax_calculations').fetchone()[0], 0)
        self.assertEqual(self.s.module_period_state(self.c, '2026-09', 'fiscal')['state'], 'aberta')
        self.assertEqual(self.report()['totals']['debit'], '0.00')

    def test_linked_tax_adjustment_is_preserved_without_implicit_accounting_netting(self):
        _, _, applied = self.calculate()
        original = self.post(applied['operation'])
        self.rule(key='explicit-adjustment', operation='ajuste', model='', effect='credito', base_field='icms_base')
        payload = self.adjustment('2.51')
        payload.update(tax_adjustment_of=original['operation_id'],
                       tax_adjustment_reason='Vínculo explícito sintético, sem inferência legal')
        payload['fiscal']['icms_base'] = '100.30'
        saved = self.save(payload)
        preview = self.s.preview_operation_tax(self.c, saved['operation_id'])
        result = self.s.apply_operation_tax(self.c, saved['operation_id'], preview['snapshot_hash'],
                                            'joint-adjustment', 'Ajuste conferido')
        adjusted = self.post(result['operation'])
        report = self.report('diario')
        self.assertEqual(report['totals']['debit'], '102.81')
        self.assertEqual(report['entry_count'], 4)
        self.assertEqual({row['operation_id'] for row in report['rows']},
                         {original['operation_id'], adjusted['operation_id']})
        stored = self.s.get_work_operation(self.c, adjusted['operation_id'])['payload']
        self.assertEqual(stored['tax_adjustment_of'], original['operation_id'])
        self.assertEqual(stored['tax_calculation'], result['operation']['payload']['tax_calculation'])
        assessment = self.s.preview_tax_assessment(self.c, self.cycle['id'])
        self.assertEqual(assessment['snapshot']['blockers'], [])
        self.assertEqual(assessment['snapshot']['totals'][0]['saldo_aritmetico'], '0.00')

    def test_future_tax_rule_does_not_recalculate_posted_accounting_history(self):
        _, _, applied = self.calculate()
        posted = self.post(applied['operation'])
        before = self.report()
        self.rule(version=1, rate='9', valid_from='2026-10-01', valid_to='2026-10-31')
        self.assertEqual(self.report(), before)
        self.assertEqual(self.s.get_work_operation(self.c, posted['operation_id'])['payload']['fiscal']['icms_amount'], '2.51')

    def test_schema10_upgrade_preserves_originals_ledger_and_report_hashes(self):
        self.opening()
        self.post(self.save(self.document()))
        before = self.report()
        originals = [tuple(row) for row in self.s.db.execute('SELECT id,sha256,original FROM files ORDER BY id')]
        postings = [tuple(row) for row in self.s.db.execute('SELECT revision_id,line,payload FROM work_movements ORDER BY revision_id,line')]
        self.s.db.execute('PRAGMA foreign_keys=OFF')
        with self.s.db:
            for table in ('document_preparation_batches','tax_calculation_batches','tax_assessment_adjustment_versions',
                          'tax_catalog_import_applications','tax_catalog_scopes','tax_catalog_imports',
                          'tax_assessment_versions','tax_calculations','tax_template_versions','tax_rule_versions',
                          'tax_catalog_versions','module_period_versions','client_profile_versions','user_organization_versions'):
                self.s.db.execute('DROP TABLE '+table)
            self.s.db.execute('UPDATE schema_version SET version=10')
        self.s.close()
        self.s = AccountingStore(self.path, actor='operador-sintetico')
        self.addCleanup(self.s.close)
        self.assertEqual(self.s.db.execute('SELECT version FROM schema_version').fetchone()[0], 17)
        self.assertEqual([tuple(row) for row in self.s.db.execute('SELECT id,sha256,original FROM files ORDER BY id')], originals)
        self.assertEqual([tuple(row) for row in self.s.db.execute('SELECT revision_id,line,payload FROM work_movements ORDER BY revision_id,line')], postings)
        self.assertEqual(self.report(), before)
        self.assertEqual(self.s.db.execute('PRAGMA foreign_key_check').fetchall(), [])
