"""Synthetic adjustment/reservation controls; no statutory credit entitlement."""
import copy
from concurrent.futures import ThreadPoolExecutor
import unittest
import test_work_application as fixtures
from src.persistence import AccountingStore
from src.module_closure import CHECKS


class TaxBalanceTests(unittest.TestCase):
    setUp=fixtures.WorkApplicationTests.setUp

    def spec(self, **values):
        return {'kind':'manual','date':'2026-09-15','component_key':'ICMS','revenue_code':'','effect':'credito',
                'amount':'100.00','description':'Ajuste inteiramente sintético','reference':'Conferência sintética; sem validade legal',**values}

    def apply(self, spec=None, cycle=None, key='manual'):
        cycle=cycle or self.cycle['id'];spec=spec or self.spec()
        preview=self.s.preview_assessment_adjustment(self.c,cycle,spec)
        return self.s.apply_assessment_adjustment(self.c,cycle,spec,preview['snapshot_hash'],key,'Teste','Conferência sintética',True)

    def assess(self, cycle=None, key='assessment'):
        cycle=cycle or self.cycle['id']
        preview=self.s.preview_tax_assessment(self.c,cycle)
        row=self.s.create_tax_assessment(self.c,cycle,preview['snapshot_hash'],key,'Teste')
        return self.s.validate_tax_assessment(self.c,cycle,row['id'],row['snapshot_hash'],'Conferência',True)

    def lock(self, cycle=None, target='encerrada'):
        cycle=cycle or self.cycle['id'];state=self.s.module_period_overview(self.c,cycle,'fiscal')
        return self.s.transition_module_period(self.c,cycle,'fiscal',target,state['snapshot_hash'],'Teste',{k:True for k in CHECKS['fiscal']},'Conferência sintética')

    def source(self, **values):
        self.apply(self.spec(**values));assessment=self.assess();self.lock()
        destination=self.s.save_work_cycle(self.c,'2026-09','2026-10',self.plan,'Teste')['id']
        spec=self.spec(kind='transporte',date='2026-10-15',effect=values.get('effect','credito'),component_key=values.get('component_key','ICMS'),
                       revenue_code=values.get('revenue_code',''),source_assessment_id=assessment['id'],source_assessment_hash=assessment['snapshot_hash'])
        return assessment,destination,spec

    def cancel(self, row, cycle=None, key='cancel'):
        return self.s.cancel_assessment_adjustment(self.c,cycle or self.cycle['id'],row['id'],row['snapshot_hash'],key,'Teste','Conferência sintética',True)

    def test_manual_adjustments_are_separate_traceable_and_do_not_post_movements(self):
        initial=self.s.preview_tax_assessment(self.c,self.cycle['id'])
        self.assertEqual(initial['snapshot']['profile'],'apuracao-parametrizada-v1')
        row=self.apply();preview=self.s.preview_tax_assessment(self.c,self.cycle['id'])
        snapshot=preview['snapshot'];group=snapshot['totals'][0]
        self.assertEqual(snapshot['profile'],'apuracao-parametrizada-v2')
        self.assertEqual(group['saldo_antes_ajustes'],'0.00');self.assertEqual(group['ajustes_credito'],'100.00')
        self.assertEqual(group['saldo_aritmetico'],'-100.00');self.assertEqual(snapshot['lines'][0]['adjustment_id'],row['id'])
        self.assertFalse(self.s.tax_assessment_readiness(self.c,self.cycle['id'])['ready'])
        for table in ('work_operations','work_movements','finance_titles'):
            self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)
        assessment=self.assess();self.assertEqual(assessment['snapshot'],snapshot)
        self.lock()
        self.assertEqual(self.s.module_period_state(self.c,'2026-09','contabil')['state'],'aberta')

    def test_transfer_reserves_same_component_and_preserves_origin_bytes(self):
        source,destination,spec=self.source();original=copy.deepcopy(self.s.tax_assessments(self.c,self.cycle['id']))
        row=self.apply({**spec,'amount':'60.00'},destination,'carry')
        balance=self.s.tax_balance_sources(self.c,destination)[0]
        self.assertEqual(balance['available'],'40.00');self.assertEqual(balance['reserved'],'60.00')
        self.assertEqual(self.s.tax_assessments(self.c,self.cycle['id']),original)
        self.assertEqual(row['snapshot']['source']['assessment_hash'],source['snapshot_hash'])
        snapshot=self.assess(destination,'destination')['snapshot']
        self.assertEqual(snapshot['totals'][0]['saldo_aritmetico'],'-60.00')
        self.assertEqual(snapshot['lines'][0]['origin'],'ajuste_apuracao_transporte')

    def test_reservations_across_destinations_block_overuse_and_stale_previews(self):
        _,october,spec=self.source();november=self.s.save_work_cycle(self.c,'2026-10','2026-11',self.plan,'Teste')['id']
        novspec={**spec,'date':'2026-11-15','amount':'50.00'}
        stale=self.s.preview_assessment_adjustment(self.c,november,novspec)
        first=self.apply({**spec,'amount':'60.00'},october,'carry')
        with AccountingStore(self.path) as second:
            with self.assertRaisesRegex(ValueError,'disponível'):
                second.apply_assessment_adjustment(self.c,november,novspec,stale['snapshot_hash'],'overuse','Teste','Teste',True)
        spec40={**novspec,'amount':'40.00'};pre=self.s.preview_assessment_adjustment(self.c,november,spec40)
        self.cancel(first,october)
        with self.assertRaisesRegex(ValueError,'alterada'):
            self.s.apply_assessment_adjustment(self.c,november,spec40,pre['snapshot_hash'],'stale','Teste','Teste',True)
        self.apply(spec40,november,'valid')
        self.assertEqual(self.s.tax_balance_sources(self.c,november)[0]['available'],'60.00')

    def test_reopening_source_requires_canceling_reservations_and_closed_destination_is_protected(self):
        _,destination,spec=self.source();row=self.apply(spec,destination,'carry')
        self.assess(destination,'dest');self.lock(destination)
        with self.assertRaisesRegex(ValueError,'transportes'):self.lock(target='aberta')
        with self.assertRaisesRegex(ValueError,'encerrado'):self.cancel(row,destination)
        self.lock(destination,'aberta');cancelled=self.cancel(row,destination)
        self.assertEqual(cancelled['state'],'cancelada')
        self.assertFalse(self.s.tax_assessment_readiness(self.c,destination)['ready'])
        self.lock(target='aberta')
        self.assertEqual(self.s.module_period_state(self.c,'2026-09','fiscal')['state'],'aberta')

    def test_origin_effect_component_company_period_and_hash_cannot_be_reassigned(self):
        _,destination,spec=self.source()
        invalid=[{'effect':'debito'},{'component_key':'PIS'},{'revenue_code':'OTHER'},{'source_assessment_hash':'a'*64},{'source_assessment_id':999999}]
        for change in invalid:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):self.s.preview_assessment_adjustment(self.c,destination,{**spec,**change})
        other=self.s.save_work_cycle(self.other,'2026-09','2026-10',None,'Teste')['id']
        with self.assertRaisesRegex(ValueError,'empresa'):self.s.preview_assessment_adjustment(self.other,other,spec)
        with self.assertRaises(ValueError):self.s.preview_assessment_adjustment(self.c,self.cycle['id'],{**spec,'date':'2026-09-15'})
        self.lock(target='aberta')
        with self.assertRaisesRegex(ValueError,'encerrado'):self.s.preview_assessment_adjustment(self.c,destination,spec)

    def test_cancel_is_append_only_idempotent_and_has_compare_and_swap(self):
        row=self.apply();pre=self.s.preview_tax_assessment(self.c,self.cycle['id'])
        repeated=self.s.apply_assessment_adjustment(self.c,self.cycle['id'],self.spec(),row['snapshot']['preview_hash'],'manual','Teste','Conferência sintética',True)
        self.assertEqual(row,repeated)
        with self.assertRaises(ValueError):self.s.apply_assessment_adjustment(self.c,self.cycle['id'],self.spec(amount='99.00'),row['snapshot']['preview_hash'],'manual','Teste','Conferência sintética',True)
        cancelled=self.cancel(row);self.assertEqual(cancelled['snapshot']['cancels_hash'],row['snapshot_hash'])
        self.assertEqual(cancelled,self.cancel(row))
        with self.assertRaisesRegex(ValueError,'cancelado'):self.cancel(row,key='cancel-again')
        current=self.s.preview_tax_assessment(self.c,self.cycle['id'])
        self.assertNotEqual(current['snapshot_hash'],pre['snapshot_hash']);self.assertEqual(current['snapshot']['totals'],[])
        rows=self.s.tax_assessment_adjustments(self.c,self.cycle['id']);self.assertEqual(len(rows),2)
        self.assertEqual(rows[1]['snapshot'],row['snapshot']);self.assertFalse(rows[1]['current'])

    def test_bad_parameters_and_missing_review_never_mutate(self):
        for change in ({'kind':[]},{'amount':0.5},{'amount':'0'},{'amount':'-1'},{'amount':'1.001'},{'component_key':'CBS'},{'component_key':'FCP:CBS'},
                       {'component_key':'RETENCAO:IBS'},{'effect':'informativo'},{'date':'2026-10-01'},{'reference':''},{'formula':'eval()'}):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):self.s.preview_assessment_adjustment(self.c,self.cycle['id'],self.spec(**change))
        preview=self.s.preview_assessment_adjustment(self.c,self.cycle['id'],self.spec())
        for confirmed in (False,'true',1):
            with self.assertRaises(ValueError):self.s.apply_assessment_adjustment(self.c,self.cycle['id'],self.spec(),preview['snapshot_hash'],'bad','Teste','Teste',confirmed)
        self.assertEqual(self.s.tax_assessment_adjustments(self.c),[])

    def test_separate_components_and_receipts_never_net_against_each_other(self):
        for index,(component,effect,amount) in enumerate([('ICMS','debito','10'),('PIS','credito','10'),('FCP:A','credito','2'),('FCP:B','debito','2')]):
            self.apply(self.spec(component_key=component,effect=effect,amount=amount),key=str(index))
        groups=self.s.preview_tax_assessment(self.c,self.cycle['id'])['snapshot']['totals']
        self.assertEqual(len(groups),4)
        self.assertEqual({g.get('component_key',g['tax']):g['saldo_aritmetico'] for g in groups},{'ICMS':'10.00','PIS':'-10.00','FCP:A':'-2.00','FCP:B':'2.00'})
        data={'description':'Receita sintética','valid_from':'2026-09-01','valid_to':'','source_reference':'Teste'}
        for code in ('0000','0001'):
            self.s.save_tax_code(self.c,'revenue',code,data,'ativo',0,'Teste')
            self.apply(self.spec(revenue_code=code,effect='credito',amount='3.00'),key=code)
        groups=self.s.preview_tax_assessment(self.c,self.cycle['id'])['snapshot']['totals']
        self.assertEqual(len(groups),6)
        self.assertEqual({g['revenue_code'] for g in groups if g['tax']=='ICMS'},{'','0000','0001'})

    def test_code_versions_are_part_of_proof_and_invalidate_open_assessment(self):
        code={'description':'Receita sintética','valid_from':'2026-09-01','valid_to':'','source_reference':'Teste'}
        self.s.save_tax_code(self.c,'revenue','0000',code,'ativo',0,'Teste')
        self.apply(self.spec(revenue_code='0000'));self.assess()
        self.s.save_tax_code(self.c,'revenue','0000',{**code,'description':'Nova conferência'},'ativo',1,'Teste')
        current=self.s.preview_tax_assessment(self.c,self.cycle['id'])
        self.assertTrue(any('Cadastro' in b for b in current['snapshot']['blockers']))
        self.assertFalse(self.s.tax_assessment_readiness(self.c,self.cycle['id'])['ready'])

    def test_closed_destination_and_global_cycle_block_new_adjustments(self):
        self.apply();self.assess();self.lock()
        with self.assertRaises(ValueError):self.apply(key='closed')
        self.lock(target='aberta')
        self.s.db.execute("UPDATE work_cycles SET state='encerrada' WHERE id=?",(self.cycle['id'],));self.s.db.commit()
        with self.assertRaisesRegex(ValueError,'encerrada'):self.apply(key='global')

    def test_positive_balance_keeps_debit_and_does_not_create_payment(self):
        _,destination,spec=self.source(effect='debito')
        self.apply(spec,destination,'carry')
        group=self.s.preview_tax_assessment(self.c,destination)['snapshot']['totals'][0]
        self.assertEqual(group['saldo_aritmetico'],'100.00');self.assertEqual(group['credito'],'0.00')
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_movements').fetchone()[0],0)

    def test_migration_14_to_15_preserves_assessment_and_closed_origin(self):
        assessment=self.assess();self.lock()
        # Genuine old profile, no adjustments: migrate without rewriting evidence.
        before=self.s.db.execute('SELECT snapshot,snapshot_hash FROM tax_assessment_versions WHERE id=?',(assessment['id'],)).fetchone()
        self.s.db.execute('DROP TABLE tax_assessment_adjustment_versions');self.s.db.execute('UPDATE schema_version SET version=14');self.s.db.commit()
        with AccountingStore(self.path) as reopened:
            self.assertEqual(reopened.db.execute('SELECT version FROM schema_version').fetchone()[0],17)
            self.assertEqual(tuple(reopened.db.execute('SELECT snapshot,snapshot_hash FROM tax_assessment_versions WHERE id=?',(assessment['id'],)).fetchone()),tuple(before))
            self.assertEqual(reopened.module_period_state(self.c,'2026-09','fiscal')['state'],'encerrada')
            self.assertEqual(reopened.tax_assessment_adjustments(self.c),[])
            self.assertTrue(reopened.tax_assessment_readiness(self.c,self.cycle['id'])['ready'])
            self.assertEqual(reopened.db.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_tampering_with_history_is_detected(self):
        row=self.apply();self.s.db.execute("UPDATE tax_assessment_adjustment_versions SET state='cancelada' WHERE id=?",(row['id'],));self.s.db.commit()
        with self.assertRaisesRegex(ValueError,'alterado'):self.s.preview_tax_assessment(self.c,self.cycle['id'])

    def test_simultaneous_destinations_cannot_reserve_the_same_capacity_twice(self):
        _,october,spec=self.source();november=self.s.save_work_cycle(self.c,'2026-10','2026-11',self.plan,'Teste')['id']
        requests=[]
        for cycle,month in ((october,'10'),(november,'11')):
            value={**spec,'date':'2026-'+month+'-15','amount':'60.00'}
            preview=self.s.preview_assessment_adjustment(self.c,cycle,value)
            requests.append((cycle,value,preview['snapshot_hash']))
        def apply(request):
            cycle,value,hash_value=request
            with AccountingStore(self.path) as store:
                try:
                    store.apply_assessment_adjustment(self.c,cycle,value,hash_value,'race-'+str(cycle),'Teste','Conferência sintética',True)
                    return True
                except ValueError:return False
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(apply,requests))
        self.assertEqual(sorted(results),[False,True])
        self.assertEqual(self.s.tax_balance_sources(self.c,november)[0]['available'],'40.00')

    def test_global_reopen_keeps_fiscal_lock_and_accounting_independence(self):
        _,destination,spec=self.source();self.apply(spec,destination,'carry')
        self.s.db.execute("UPDATE work_cycles SET state='encerrada' WHERE id=?",(self.cycle['id'],));self.s.db.commit()
        overview=self.s.work_overview(self.c,self.cycle['id'])
        self.s.transition_work_cycle(self.c,self.cycle['id'],'aberta',overview['snapshot_hash'],'Reabrir recorte contábil')
        self.assertEqual(self.s.module_period_state(self.c,'2026-09','fiscal')['state'],'encerrada')
        self.assertEqual(self.s.module_period_state(self.c,'2026-09','contabil')['state'],'aberta')
        with self.assertRaisesRegex(ValueError,'transportes'):self.lock(target='aberta')

    def test_document_totals_and_adjustment_subtotals_remain_distinguishable(self):
        from test_tax_engine import TaxEngineTests
        TaxEngineTests.rule(self,rate='10')
        operation=fixtures.WorkApplicationTests.save(self,fixtures.WorkApplicationTests.document(self))
        preview=self.s.preview_operation_tax(self.c,operation['operation_id'])
        operation=self.s.apply_operation_tax(self.c,operation['operation_id'],preview['snapshot_hash'],'document-tax','Teste')['operation']
        fixtures.WorkApplicationTests.post(self,operation)
        self.apply(self.spec(amount='3'))
        group=self.s.preview_tax_assessment(self.c,self.cycle['id'])['snapshot']['totals'][0]
        self.assertEqual(group['saldo_antes_ajustes'],'10.03')
        self.assertEqual(group['ajustes_credito'],'3.00');self.assertEqual(group['saldo_aritmetico'],'7.03')
        self.assertEqual(group['debito'],'10.03')


if __name__=='__main__':unittest.main()
