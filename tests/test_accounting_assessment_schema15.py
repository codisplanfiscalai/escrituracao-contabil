"""Assessment-only effects never become implicit accounting or financial posts."""
from copy import deepcopy
import unittest
import test_work_application as work
import test_tax_engine as tax
import test_tax_items as items
import test_tax_balances as balances
import test_tax_fcp_grossup as grossup
from src.persistence import AccountingStore
from src.module_closure import CHECKS
from src.work_reports import accounting_report


class AccountingAssessmentSchema15Tests(unittest.TestCase):
    setUp = work.WorkApplicationTests.setUp
    save = work.WorkApplicationTests.save
    post = work.WorkApplicationTests.post
    document = work.WorkApplicationTests.document
    opening = work.WorkApplicationTests.opening
    rule = tax.TaxEngineTests.rule
    calc = items.TaxItemTests.calc
    item = items.TaxItemTests.item
    apply = items.TaxItemTests.apply
    operation = grossup.FCPGrossupTests.operation
    fcp = grossup.FCPGrossupTests.fcp
    inside = grossup.FCPGrossupTests.inside
    group_rules = grossup.FCPGrossupTests.group_rules
    spec = balances.TaxBalanceTests.spec
    adjust = balances.TaxBalanceTests.apply
    assess = balances.TaxBalanceTests.assess
    lock = balances.TaxBalanceTests.lock
    cancel = balances.TaxBalanceTests.cancel

    def report(self, cycle=None):
        return accounting_report(self.s,self.c,cycle or self.cycle['id'],self.plan)

    def lock_accounting(self, cycle=None):
        cycle = cycle or self.cycle['id']
        state = self.s.module_period_overview(self.c,cycle,'contabil')
        return self.s.transition_module_period(self.c,cycle,'contabil','encerrada',state['snapshot_hash'],
                                             'Conferência sintética',{k:True for k in CHECKS['contabil']},'Saldos sintéticos')

    def grossed(self):
        self.group_rules()
        return self.apply(self.operation([self.item(total='125.00',taxes=['ICMS','FCP:TESTE'],
                                                    values={'total':'125.00','net_base':'100.00'})]))[1]

    def test_manual_assessment_and_cancellation_preserve_ledger_titles_and_source_hash(self):
        self.rule(rate='10')
        _,result = self.apply(self.save(self.document()))
        self.post(result['operation'])
        self.assess(key='before-adjustment')
        before = self.report()
        titles = deepcopy(self.s.list_finance_titles(self.c))
        movements = [tuple(r) for r in self.s.db.execute('SELECT revision_id,line,payload FROM work_movements ORDER BY revision_id,line')]
        adjustment = self.adjust(self.spec(amount='3.00'))
        assessment = self.s.preview_tax_assessment(self.c,self.cycle['id'])['snapshot']
        self.assertEqual(assessment['profile'],'apuracao-parametrizada-v2')
        self.assertEqual(assessment['totals'][0]['saldo_antes_ajustes'],'10.03')
        self.assertEqual(assessment['totals'][0]['ajustes_credito'],'3.00')
        self.assertEqual(assessment['totals'][0]['saldo_aritmetico'],'7.03')
        self.assertFalse(self.s.tax_assessment_readiness(self.c,self.cycle['id'])['ready'])
        self.assertEqual(self.report(),before)
        self.cancel(adjustment)
        self.assertEqual(self.report(),before)
        self.assertEqual(self.s.list_finance_titles(self.c),titles)
        self.assertEqual([tuple(r) for r in self.s.db.execute('SELECT revision_id,line,payload FROM work_movements ORDER BY revision_id,line')],movements)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_operations').fetchone()[0],1)

    def test_balance_transfer_and_reservation_cancellation_do_not_create_accounting_openings(self):
        self.opening()
        self.adjust()
        source = self.assess()
        self.lock()
        source_report = self.report()
        destination = self.s.save_work_cycle(self.c,'2026-09','2026-10',self.plan,'Teste')['id']
        spec = self.spec(kind='transporte',date='2026-10-15',amount='60.00',
                         source_assessment_id=source['id'],source_assessment_hash=source['snapshot_hash'])
        original = deepcopy(self.s.tax_assessments(self.c,self.cycle['id']))
        transferred = self.adjust(spec,destination,'transfer')
        self.assess(destination,'destination')
        balance = self.s.tax_balance_sources(self.c,destination)[0]
        self.assertEqual((balance['reserved'],balance['available']),('60.00','40.00'))
        before = self.report(destination)
        self.assertEqual(before['entry_count'],0)
        self.assertEqual(before['totals']['opening'],'0.00')
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM finance_titles').fetchone()[0],0)
        self.lock_accounting(destination)
        with self.assertRaisesRegex(ValueError,'transportes'):
            self.lock(target='aberta')
        self.cancel(transferred,destination)
        self.assertEqual(self.report(destination),before)
        self.assertEqual(self.report(),source_report)
        self.assertEqual(self.s.tax_assessments(self.c,self.cycle['id']),original)
        self.assertEqual(self.s.tax_balance_sources(self.c,destination)[0]['available'],'100.00')
        self.assertEqual(self.s.module_period_state(self.c,'2026-10','contabil')['state'],'encerrada')

    def test_schema14_to15_preserves_grossup_fcp_memory_reports_and_module_locks(self):
        self.opening()
        result = self.grossed()
        posted = self.post(result['operation'])
        self.assess();self.lock();self.lock_accounting()
        before = self.report()
        self.assertEqual(before['totals']['debit'],'125.00')
        memory = result['operation']['payload']['tax_calculation']
        self.assertEqual(memory['memory']['profile'],'tributacao-itens-v3')
        self.assertEqual(memory['memory']['grossup_groups'][0]['residual'],'0.00')
        originals = [tuple(r) for r in self.s.db.execute('SELECT id,sha256,original FROM files ORDER BY id')]
        calculations = [tuple(r) for r in self.s.db.execute('SELECT id,snapshot,snapshot_hash FROM tax_calculations ORDER BY id')]
        assessments = [tuple(r) for r in self.s.db.execute('SELECT id,snapshot,snapshot_hash FROM tax_assessment_versions ORDER BY id')]
        with self.s.db:
            self.s.db.execute('DROP TABLE tax_calculation_batches')
            self.s.db.execute('DROP TABLE tax_assessment_adjustment_versions')
            self.s.db.execute('UPDATE schema_version SET version=14')
        self.s.close()
        self.s = AccountingStore(self.path,actor='operador-sintetico')
        self.addCleanup(self.s.close)
        self.assertEqual(self.s.db.execute('SELECT version FROM schema_version').fetchone()[0],16)
        self.assertEqual(self.report(),before)
        self.assertEqual([tuple(r) for r in self.s.db.execute('SELECT id,sha256,original FROM files ORDER BY id')],originals)
        self.assertEqual([tuple(r) for r in self.s.db.execute('SELECT id,snapshot,snapshot_hash FROM tax_calculations ORDER BY id')],calculations)
        self.assertEqual([tuple(r) for r in self.s.db.execute('SELECT id,snapshot,snapshot_hash FROM tax_assessment_versions ORDER BY id')],assessments)
        self.assertEqual(self.s.get_work_operation(self.c,posted['operation_id'])['payload']['tax_calculation'],memory)
        self.assertEqual(self.s.tax_assessment_adjustments(self.c),[])
        self.assertTrue(all(self.s.module_period_state(self.c,'2026-09',m)['state']=='encerrada' for m in ('fiscal','contabil')))
        self.assertEqual(self.s.db.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_assessment_adjustments_cannot_replace_linked_reversal_coverage(self):
        result = self.grossed()
        original = self.post(result['operation'])
        reverse = self.s.reverse_work_operation(self.c,original['operation_id'],self.cycle['id'],'2026-09-20',
                                                 original['snapshot_hash'],'Estorno sintético','grossup-reverse')
        self.post(reverse)
        self.adjust(self.spec(component_key='ICMS',amount='22.50'),key='manual-own')
        self.adjust(self.spec(component_key='FCP:TESTE',amount='2.50'),key='manual-fcp')
        assessment = self.s.preview_tax_assessment(self.c,self.cycle['id'])['snapshot']
        self.assertTrue(any('ajuste fiscal explícito vinculado' in message for message in assessment['blockers']))
        with self.assertRaises(ValueError):self.assess()
        report = self.report()
        self.assertEqual(report['entry_count'],4)
        self.assertEqual(report['totals']['debit'],'250.00')
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_operations').fetchone()[0],2)
