"""Atomic draft tax batches preserve explicit individual accounting effects."""
from copy import deepcopy
from unittest.mock import patch
import unittest
import test_work_application as work
import test_tax_batch as batches
import test_tax_items as items
import test_tax_balances as balances
from src.persistence import AccountingStore
from src.module_closure import CHECKS
from src.work_reports import accounting_report


class AccountingBatchSchema16Tests(unittest.TestCase):
    setUp = work.WorkApplicationTests.setUp
    save = work.WorkApplicationTests.save
    post = work.WorkApplicationTests.post
    opening = work.WorkApplicationTests.opening
    operation = batches.TaxBatchTests.operation
    rule = batches.TaxBatchTests.rule
    setup_batch = batches.TaxBatchTests.setup_batch
    batch_apply = batches.TaxBatchTests.apply
    calc = items.TaxItemTests.calc
    item = items.TaxItemTests.item
    spec = balances.TaxBalanceTests.spec
    adjust = balances.TaxBalanceTests.apply
    assess = balances.TaxBalanceTests.assess

    def report(self):
        return accounting_report(self.s,self.c,self.cycle['id'],self.plan)

    def close_modules(self):
        self.assess()
        for module in ('fiscal','contabil'):
            state=self.s.module_period_overview(self.c,self.cycle['id'],module)
            self.s.transition_module_period(self.c,self.cycle['id'],module,'encerrada',state['snapshot_hash'],
                                             'Conferência sintética',{k:True for k in CHECKS[module]},'Memória sintética')

    def test_batch_drafts_enter_books_only_after_individual_posting_and_retry_never_duplicates(self):
        self.opening()
        rows,ids,preview=self.setup_batch()
        original={r['operation_id']:deepcopy(r['payload']['entries']) for r in rows}
        self.assertEqual(self.report()['entry_count'],0)
        result=self.batch_apply(ids,preview)
        self.assertEqual(self.report()['entry_count'],0)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_movements').fetchone()[0],0)
        for operation_id in ids:
            current=self.s.get_work_operation(self.c,operation_id)
            self.assertEqual(current['state'],'rascunho')
            self.assertEqual(current['payload']['entries'],original[operation_id])
        self.post(self.s.get_work_operation(self.c,ids[0]))
        self.assertEqual(self.report()['totals']['debit'],'100.30')
        self.post(self.s.get_work_operation(self.c,ids[1]))
        self.assertEqual(self.report()['totals']['debit'],'300.30')
        self.close_modules()
        before=self.report()
        repeated=self.batch_apply(list(reversed(ids)),preview)
        self.assertTrue(repeated['duplicate'])
        self.assertEqual(repeated['snapshot'],result['snapshot'])
        self.assertEqual(self.report(),before)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_movements').fetchone()[0],4)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM tax_calculations').fetchone()[0],2)

    def test_partial_failure_leaves_existing_book_and_all_new_drafts_unchanged(self):
        self.rule()
        previous=self.operation(1)
        preview=self.s.preview_operation_tax(self.c,previous['operation_id'])
        applied=self.s.apply_operation_tax(self.c,previous['operation_id'],preview['snapshot_hash'],'previous-calc','Conferido')
        self.post(applied['operation'])
        rows=[self.operation(2,'50.00'),self.operation(3,'75.00')]
        ids=[r['operation_id'] for r in rows]
        preview=self.s.preview_tax_batch(self.c,self.cycle['id'],ids)
        before=self.report()
        tables=('work_revisions','work_requests','work_movements','finance_titles','tax_calculations','tax_calculation_batches','audit')
        counts={t:self.s.db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in tables}
        original=self.s.apply_operation_tax
        calls=0
        def fail_second(*args,**kwargs):
            nonlocal calls
            calls+=1
            if calls==2:raise ValueError('Falha sintética no segundo cálculo')
            return original(*args,**kwargs)
        with patch.object(self.s,'apply_operation_tax',side_effect=fail_second):
            with self.assertRaisesRegex(ValueError,'segundo cálculo'):
                self.batch_apply(ids,preview)
        self.assertEqual(self.report(),before)
        self.assertEqual({t:self.s.db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in tables},counts)
        self.assertEqual([self.s.get_work_operation(self.c,i)['version'] for i in ids],[1,1])
        self.batch_apply(ids,preview)
        self.assertEqual(self.report(),before)
        for operation_id in ids:self.post(self.s.get_work_operation(self.c,operation_id))
        self.assertEqual(self.report()['totals']['debit'],'225.30')

    def test_mixed_memory_profiles_are_preserved_without_batch_accounting_aggregation(self):
        self.s.save_tax_code(self.c,'cfop','1101',{'description':'Código sintético','valid_from':'2026-09-01','valid_to':'','source_reference':'Fixture'},'ativo',0,'Teste')
        self.rule(key='document',cfop='1101')
        self.rule(key='item',item_treatment='D',calculation=self.calc())
        self.rule(key='credit',rate='3',effect='credito',item_treatment='C',calculation=self.calc())
        self.rule(key='fcp',tax='FCP',base_field='fcp_base',rate='2',item_treatment='FCP',
                  calculation=self.calc('fcp',component_code='TESTE',base_mode='declarada'))
        rows=[self.operation(n) for n in (1,2,3)]
        for index,row in enumerate(rows):
            payload=deepcopy(row['payload'])
            if index==0:payload['fiscal']['cfop']='1101'
            elif index==1:payload['tax_items']=[self.item('A','50.15',treatment='D'),self.item('B','50.15',treatment='C')]
            else:payload['tax_items']=[self.item(treatment='FCP',taxes=['FCP:TESTE'],values={'total':'100.30','fcp_base':'100.30'})]
            self.save(payload,row['operation_id'],row['version'])
        ids=[r['operation_id'] for r in rows]
        preview=self.s.preview_tax_batch(self.c,self.cycle['id'],ids)
        result=self.batch_apply(ids,preview)
        self.assertEqual([c['snapshot']['profile'] for c in result['calculations']],
                         ['tributacao-parametrizada-v1','tributacao-itens-v2','tributacao-itens-v3'])
        self.assertEqual(self.report()['entry_count'],0)
        for operation_id in ids:self.post(self.s.get_work_operation(self.c,operation_id))
        report=self.report()
        self.assertEqual(report['entry_count'],6)
        self.assertEqual(report['totals']['debit'],'300.90')
        detail=self.s.tax_batch_detail(self.c,result['id'])
        self.assertEqual(detail['snapshot'],result['snapshot'])
        self.assertEqual({r['operation_id'] for r in self.s.work_books(self.c,self.cycle['id'])['diary']},set(ids))

    def test_schema15_to16_preserves_posted_memories_adjustments_locks_and_report_hash(self):
        self.opening()
        _,ids,preview=self.setup_batch()
        for item in preview['snapshot']['items']:
            result=self.s.apply_operation_tax(self.c,item['operation_id'],item['memory_hash'],'single-'+str(item['operation_id']),'Conferido')
            self.post(result['operation'])
        self.adjust(self.spec(amount='3.00'))
        self.close_modules()
        before=self.report()
        preserved={t:[tuple(r) for r in self.s.db.execute('SELECT * FROM '+t+' ORDER BY id')]
                   for t in ('files','tax_calculations','tax_assessment_adjustment_versions','tax_assessment_versions')}
        with self.s.db:
            self.s.db.execute('DROP TABLE document_preparation_batches')
            self.s.db.execute('DROP TABLE tax_calculation_batches')
            self.s.db.execute('UPDATE schema_version SET version=15')
        self.s.close()
        self.s=AccountingStore(self.path,actor='operador-sintetico')
        self.addCleanup(self.s.close)
        self.assertEqual(self.s.db.execute('SELECT version FROM schema_version').fetchone()[0],17)
        self.assertEqual(self.report(),before)
        for table,rows in preserved.items():
            self.assertEqual([tuple(r) for r in self.s.db.execute('SELECT * FROM '+table+' ORDER BY id')],rows)
        self.assertEqual(self.s.tax_batches(self.c,self.cycle['id'])['items'],[])
        self.assertTrue(all(self.s.module_period_state(self.c,'2026-09',m)['state']=='encerrada' for m in ('fiscal','contabil')))
        self.assertEqual(self.s.db.execute('PRAGMA foreign_key_check').fetchall(),[])
