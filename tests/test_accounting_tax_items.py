"""Joint item-effect/accounting contracts on the exact PR #10 code base."""
from copy import deepcopy
from decimal import Decimal
import unittest

import test_work_application as work
import test_tax_items as items
from src.module_closure import CHECKS
from src.work_reports import accounting_report
from test_persistence import fake_xml


class AccountingTaxItemsTests(unittest.TestCase):
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

    def report(self, kind='balancete'):
        return accounting_report(self.s, self.c, self.cycle['id'], self.plan, report=kind)

    def test_mixed_item_effects_preserve_header_assessment_and_explicit_ledger(self):
        self.rule(key='debit', rate='2.5', item_treatment='D', calculation=self.calc(reduction_percent='10'))
        self.rule(key='credit', rate='7', effect='credito', item_treatment='C', calculation=self.calc())
        original = self.operation([self.item(total='60.00', treatment='D'), self.item('B','40.30', treatment='C')])
        original_entries = deepcopy(original['payload']['entries'])
        preview, result = self.apply(original)
        calculated = result['operation']
        self.assertEqual(preview['snapshot']['profile'], 'tributacao-itens-v2')
        self.assertEqual(calculated['payload']['fiscal']['icms_amount'], '4.17')
        self.assertEqual([(r['amount'],r['effect']) for r in preview['snapshot']['lines']],
                         [('1.35','debito'),('2.82','credito')])
        self.assertEqual(calculated['payload']['entries'], original_entries)
        posted = self.post(calculated)
        changes = self.s.db.total_changes
        for kind in ('diario','razao','balancete'):
            report = self.report(kind)
            self.assertEqual(report['totals']['debit'], '100.30')
            self.assertEqual(report['entry_count'], 2)
        self.assertEqual(self.s.db.total_changes, changes)
        assessment = self.s.preview_tax_assessment(self.c, self.cycle['id'])['snapshot']
        self.assertEqual(assessment['totals'][0]['saldo_aritmetico'], '-1.47')
        self.assertEqual([line['item_id'] for line in assessment['lines']], ['A','B'])
        self.assertEqual(self.s.get_work_operation(self.c,posted['operation_id'])['payload']['tax_calculation'],
                         calculated['payload']['tax_calculation'])

    def test_special_components_and_two_retentions_never_net_titles_or_postings(self):
        self.rule(key='st', tax='ICMS_ST', rate='10', calculation=self.calc('st', margin_percent='50',deduction_field='st_deduction',negative_policy='bloquear'))
        self.rule(key='difal', tax='ICMS_DIFAL', rate='12', calculation=self.calc('difal',origin_rate='4',negative_policy='bloquear'))
        for code,rate in [('A','2'),('B','3')]:
            self.rule(key='ret-'+code, tax='RETENCAO',rate=rate,effect='informativo',calculation=self.calc('retencao',component_code=code))
        original = self.operation([self.item(taxes=['ICMS_ST','ICMS_DIFAL','RETENCAO:A','RETENCAO:B'],
                                             values={'total':'100.30','st_deduction':'5.00'})])
        preview, result = self.apply(original)
        self.assertEqual(preview['snapshot']['output'], {})
        expected = {'ICMS_ST':'10.05','ICMS_DIFAL':'8.02','RETENCAO:A':'2.01','RETENCAO:B':'3.01'}
        self.assertEqual({r['component_key']:r['amount'] for r in result['operation']['payload']['tax_components']}, expected)
        self.assertEqual(result['operation']['payload']['finance'], original['payload']['finance'])
        posted = self.post(result['operation'])
        report = self.report()
        self.assertEqual(report['totals']['debit'], '100.30')
        self.assertEqual(report['entry_count'], 2)
        self.assertEqual(sum((Decimal(t['amount']) for t in posted['titles']), Decimal(0)), Decimal('100.30'))
        assessment = self.s.preview_tax_assessment(self.c,self.cycle['id'])['snapshot']
        self.assertEqual({g.get('component_key',g['tax']) for g in assessment['totals']}, set(expected))
        self.assertEqual({g['component_key']:g['informativo'] for g in assessment['totals'] if g['tax']=='RETENCAO'},
                         {'RETENCAO:A':'2.01','RETENCAO:B':'3.01'})

    def test_item_only_adjustment_is_fiscal_locked_and_closed_period_reports_are_readable(self):
        self.opening()
        self.rule(tax='ICMS_DIFAL',rate='12',calculation=self.calc('difal',origin_rate='4',negative_policy='bloquear'))
        _, result = self.apply(self.operation([self.item(taxes=['ICMS_DIFAL'])]))
        self.post(result['operation'])
        preview = self.s.preview_tax_assessment(self.c,self.cycle['id'])
        row = self.s.create_tax_assessment(self.c,self.cycle['id'],preview['snapshot_hash'],'items-assessed','Conferido')
        self.s.validate_tax_assessment(self.c,self.cycle['id'],row['id'],row['snapshot_hash'],'Conferido',True)
        before = self.report()
        for module in ('fiscal','contabil'):
            state = self.s.module_period_overview(self.c,self.cycle['id'],module)
            self.s.transition_module_period(self.c,self.cycle['id'],module,'encerrada',state['snapshot_hash'],
                                             'Fechamento sintético',{k:True for k in CHECKS[module]},'Memória sintética')
        self.assertEqual(self.report(), before)
        payload = self.s.prepare_work_operation(self.c,self.cycle['id'],operation='ajuste')
        payload.update(reference='Tentativa sem cabeçalho tributário',tax_items=[self.item(taxes=['ICMS_DIFAL'])])
        payload['fiscal'].update(total='100.30',posting_date='2026-09-20')
        with self.assertRaisesRegex(ValueError,'encerrado'):
            self.save(payload)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_movements').fetchone()[0], 2)

    def test_special_reversal_and_linked_adjustment_keep_separate_accounting_events(self):
        self.rule(tax='ICMS_DIFAL',rate='12',calculation=self.calc('difal',origin_rate='4',negative_policy='bloquear'))
        _, result = self.apply(self.operation([self.item(taxes=['ICMS_DIFAL'])]))
        original = self.post(result['operation'])
        reverse = self.s.reverse_work_operation(self.c,original['operation_id'],self.cycle['id'],'2026-09-20',
                                                 original['snapshot_hash'],'Estorno sintético','items-reverse')
        self.post(reverse)
        self.assertTrue(self.s.preview_tax_assessment(self.c,self.cycle['id'])['snapshot']['blockers'])
        self.rule(key='adjust',tax='ICMS_DIFAL',rate='12',operation='ajuste',model='',effect='credito',
                  calculation=self.calc('difal',origin_rate='4',negative_policy='bloquear'))
        payload = self.s.prepare_work_operation(self.c,self.cycle['id'],operation='ajuste')
        payload.update(reference='Ajuste explícito de item',tax_adjustment_of=original['operation_id'],
                       tax_adjustment_reason='Cobertura sintética explícita',tax_items=[self.item(taxes=['ICMS_DIFAL'])])
        payload['fiscal'].update(total='100.30',posting_date='2026-09-20')
        payload['entries'] = [dict(account_id=self.ids[code],side=side,date='2026-09-20',amount='100.30',
                                  group='principal',memo='Ajuste explícito') for code,side in [('1.1.1','D'),('2.1','C')]]
        _, adjusted = self.apply(self.save(payload),key='items-adjusted')
        self.post(adjusted['operation'])
        assessment = self.s.preview_tax_assessment(self.c,self.cycle['id'])['snapshot']
        self.assertEqual(assessment['blockers'], [])
        self.assertEqual(assessment['totals'][0]['saldo_aritmetico'], '0.00')
        report = self.report('diario')
        self.assertEqual(report['entry_count'], 6)
        self.assertEqual(report['totals']['debit'], '300.90')
        self.assertEqual(len({r['operation_id'] for r in report['rows']}), 3)

    def test_document_v1_and_item_v2_memories_coexist_in_one_accounting_book(self):
        self.rule()
        original = self.save(self.document())
        _, v1 = self.apply(original,key='document-v1')
        self.post(v1['operation'])
        self.rule(version=1,state='inativa')
        self.rule(key='item',rate='7',calculation=self.calc())
        source = self.s.receive_sources(self.c,[{'filename':'SegundoSintetico.xml','content':fake_xml(number=2)}],
                                         'second-item-source')['items'][0]
        document = self.s.organize_source(self.c,source['input_id'],self.cycle['id'],source['snapshot_hash'],'Conferido')['evidence']['document_ids'][0]
        payload = self.s.prepare_work_operation(self.c,self.cycle['id'],document,policy_id=self.policy['id'])
        payload['tax_items'] = [self.item()]
        _, v2 = self.apply(self.save(payload),key='item-v2')
        self.post(v2['operation'])
        self.assertNotEqual(v1['calculation']['snapshot']['profile'], v2['calculation']['snapshot']['profile'])
        self.assertEqual(self.report()['totals']['debit'], '200.60')
        self.assertEqual(self.report()['entry_count'], 4)
        self.assertEqual(self.s.db.execute('SELECT version FROM schema_version').fetchone()[0],17)
