"""Synthetic bulk calculations preserve individual proof, locks and atomicity."""
import copy
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import unittest
import test_work_application as fixtures
import test_tax_engine as taxes
from test_persistence import fake_xml
from src.persistence import AccountingStore
from src.module_closure import CHECKS


class TaxBatchTests(unittest.TestCase):
    setUp=fixtures.WorkApplicationTests.setUp
    rule=taxes.TaxEngineTests.rule
    save=fixtures.WorkApplicationTests.save
    post=fixtures.WorkApplicationTests.post

    def operation(self, number=1, total='100.30'):
        receipt=self.s.receive_sources(self.c,[{'filename':f'synthetic-{number}.xml','content':fake_xml(number=number,total=total,billing=False)}],f'receipt-{number}')['items'][0]
        organized=self.s.organize_source(self.c,receipt['input_id'],self.cycle['id'],receipt['snapshot_hash'],'Teste')
        doc=organized['evidence']['document_ids'][0]
        payload=self.s.prepare_work_operation(self.c,self.cycle['id'],doc,policy_id=self.policy['id'])
        return self.save(payload)

    def setup_batch(self):
        self.rule()
        rows=[self.operation(1),self.operation(2,total='200.00')]
        ids=[r['operation_id'] for r in rows]
        return rows,ids,self.s.preview_tax_batch(self.c,self.cycle['id'],ids)

    def apply(self, ids, preview, key='batch'):
        return self.s.apply_tax_batch(self.c,self.cycle['id'],ids,preview['snapshot_hash'],key,'Conferência sintética',True)

    def test_preview_does_not_mutate_and_application_only_creates_draft_versions(self):
        rows,ids,preview=self.setup_batch()
        self.assertTrue(preview['snapshot']['ready'])
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM tax_calculations').fetchone()[0],0)
        result=self.apply(ids,preview)
        self.assertFalse(result['duplicate']);self.assertEqual(len(result['snapshot']['items']),2)
        self.assertEqual({r['snapshot']['output']['icms_amount'] for r in result['calculations']},{'2.51','5.00'})
        for original in rows:
            current=self.s.get_work_operation(self.c,original['operation_id'])
            self.assertEqual(current['state'],'rascunho');self.assertEqual(current['version'],2)
            for key in ('entries','finance'):self.assertEqual(current['payload'][key],original['payload'][key])
        for table in ('work_movements','finance_titles'):
            self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)
        self.assertEqual(self.s.tax_batches(self.c,self.cycle['id'])['total'],1)

    def test_any_blocker_prevents_the_entire_application(self):
        _,ids,_=self.setup_batch()
        current=self.s.get_work_operation(self.c,ids[1]);payload=copy.deepcopy(current['payload']);payload['fiscal']['total']=''
        self.save(payload,ids[1],current['version'])
        preview=self.s.preview_tax_batch(self.c,self.cycle['id'],ids)
        self.assertFalse(preview['snapshot']['ready'])
        self.assertEqual([bool(r['blockers']) for r in preview['snapshot']['items']],[False,True])
        with self.assertRaisesRegex(ValueError,'nenhuma operação'):self.apply(ids,preview)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM tax_calculations').fetchone()[0],0)
        self.assertEqual(self.s.get_work_operation(self.c,ids[0])['version'],1)

    def test_runtime_failure_rolls_back_versions_memories_requests_receipt_and_audit(self):
        _,ids,preview=self.setup_batch()
        counts={table:self.s.db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('work_revisions','work_requests','audit','tax_calculations','tax_calculation_batches')}
        original=self.s.apply_operation_tax
        calls=0
        def fail_second(*args,**kwargs):
            nonlocal calls
            calls+=1
            if calls==2:raise ValueError('Falha sintética após o primeiro cálculo')
            return original(*args,**kwargs)
        with patch.object(self.s,'apply_operation_tax',side_effect=fail_second):
            with self.assertRaisesRegex(ValueError,'Falha sintética'):self.apply(ids,preview)
        for table,count in counts.items():self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],count)
        self.assertFalse(self.s.db.in_transaction)
        self.assertEqual(len(self.apply(ids,preview)['snapshot']['items']),2)

    def test_changed_rule_or_input_requires_a_new_whole_batch_preview(self):
        _,ids,preview=self.setup_batch();self.rule(version=1,rate='3')
        with self.assertRaisesRegex(ValueError,'Prévia do lote alterada'):self.apply(ids,preview)
        current=self.s.preview_tax_batch(self.c,self.cycle['id'],ids)
        row=self.s.get_work_operation(self.c,ids[1]);payload=copy.deepcopy(row['payload']);payload['notes']='Correção sintética'
        self.save(payload,ids[1],row['version'])
        with self.assertRaisesRegex(ValueError,'alterada'):self.apply(ids,current)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM tax_calculations').fetchone()[0],0)

    def test_idempotency_returns_original_versions_even_after_posting(self):
        _,ids,preview=self.setup_batch();result=self.apply(ids,preview)
        for operation_id in ids:self.post(self.s.get_work_operation(self.c,operation_id))
        again=self.apply(list(reversed(ids)),preview)
        self.assertTrue(again['duplicate']);self.assertEqual(again['snapshot'],result['snapshot'])
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM tax_calculations').fetchone()[0],2)
        with self.assertRaisesRegex(ValueError,'outro conteúdo'):
            self.s.apply_tax_batch(self.c,self.cycle['id'],ids,preview['snapshot_hash'],'batch','Outro motivo',True)

    def test_simultaneous_retries_create_one_batch_and_one_version_per_operation(self):
        _,ids,preview=self.setup_batch()
        def apply(_):
            with AccountingStore(self.path) as store:
                return store.apply_tax_batch(self.c,self.cycle['id'],ids,preview['snapshot_hash'],'race','Teste',True)
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(apply,range(2)))
        self.assertEqual(sorted(r['duplicate'] for r in results),[False,True])
        self.assertEqual(results[0]['id'],results[1]['id'])
        self.assertEqual(self.s.tax_batches(self.c,self.cycle['id'])['total'],1)
        self.assertEqual([self.s.get_work_operation(self.c,i)['version'] for i in ids],[2,2])

    def test_selection_limits_duplicates_and_confirmation_are_explicit(self):
        _,ids,preview=self.setup_batch()
        for selection in ([],ids*2,[ids[0],str(ids[0])],list(range(1,102)),True,[False]):
            with self.subTest(selection=selection):
                with self.assertRaises(ValueError):self.s.preview_tax_batch(self.c,self.cycle['id'],selection)
        for confirmed in (False,1,'true'):
            with self.assertRaises(ValueError):self.s.apply_tax_batch(self.c,self.cycle['id'],ids,preview['snapshot_hash'],'bad','Teste',confirmed)
        with self.assertRaisesRegex(ValueError,'transação ativa'):
            self.s.apply_operation_tax(self.c,ids[0],preview['snapshot']['items'][0]['memory_hash'],'direct','Teste',_in_transaction=True)

    def test_company_period_and_posted_operation_boundaries(self):
        _,ids,preview=self.setup_batch();result=self.apply(ids[:1],self.s.preview_tax_batch(self.c,self.cycle['id'],ids[:1]))
        self.post(self.s.get_work_operation(self.c,ids[0]))
        self.assertFalse(self.s.preview_tax_batch(self.c,self.cycle['id'],ids)['snapshot']['ready'])
        other_cycle=self.s.save_work_cycle(self.other,'2026-08','2026-09',None,'Teste')['id']
        other=self.s.preview_tax_batch(self.other,other_cycle,ids)
        self.assertTrue(all(i['blockers'] and 'reference' not in i for i in other['snapshot']['items']))
        with self.assertRaises(ValueError):self.s.tax_batch_detail(self.other,result['id'])
        later=self.s.save_work_cycle(self.c,'2026-09','2026-10',self.plan,'Teste')['id']
        self.assertFalse(self.s.preview_tax_batch(self.c,later,ids)['snapshot']['ready'])

    def test_closed_fiscal_global_or_accounting_module_blocks_new_batch(self):
        _,ids,preview=self.setup_batch()
        self.s.db.execute("UPDATE work_cycles SET state='encerrada' WHERE id=?",(self.cycle['id'],));self.s.db.commit()
        with self.assertRaisesRegex(ValueError,'encerrada'):self.apply(ids,preview)
        self.s.db.execute("UPDATE work_cycles SET state='aberta' WHERE id=?",(self.cycle['id'],));self.s.db.commit()
        # Synthetic lock state without fabricating a successful operational closure.
        from src.accounting_store import dump,digest
        for module in ('fiscal','contabil'):
            self.s.db.execute('DELETE FROM module_period_versions')
            self.s.db.execute('INSERT INTO module_period_versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(self.c,'2026-09',module,1,'encerrada',dump({}),digest({}),dump({}),'Teste','Teste','Teste',self.s._now()));self.s.db.commit()
            if module=='fiscal':
                with self.assertRaisesRegex(ValueError,'encerrado'):self.apply(ids,preview)
            else:self.assertFalse(self.s.preview_tax_batch(self.c,self.cycle['id'],ids)['snapshot']['ready'])
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM tax_calculations').fetchone()[0],0)

    def test_corrupt_original_blocks_before_any_calculation(self):
        _,ids,_=self.setup_batch()
        self.s.db.execute("UPDATE files SET original=? WHERE id=(SELECT MIN(id) FROM files)",(b'corrupt',));self.s.db.commit()
        preview=self.s.preview_tax_batch(self.c,self.cycle['id'],ids)
        self.assertFalse(preview['snapshot']['ready'])
        self.assertTrue(any('Integridade' in b for item in preview['snapshot']['items'] for b in item['blockers']))
        with self.assertRaises(ValueError):self.apply(ids,preview)

    def test_changed_source_revision_invalidates_documental_batch_before_writing(self):
        _,ids,preview=self.setup_batch()
        source=self.s.source_inbox(self.c)[0]
        evidence=copy.deepcopy(source['evidence']);evidence['issues'].append('Conferência adicional sintética')
        with self.s.db:self.s._append_source_revision(self.c,source['input_id'],evidence,'Teste')
        with self.assertRaisesRegex(ValueError,'Prévia do lote alterada'):self.apply(ids,preview)
        current=self.s.preview_tax_batch(self.c,self.cycle['id'],ids)
        self.assertFalse(current['snapshot']['ready'])
        self.assertTrue(any('Fonte documental' in b for item in current['snapshot']['items'] for b in item['blockers']))
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM tax_calculations').fetchone()[0],0)

    def test_receipt_and_calculation_tampering_are_detected(self):
        _,ids,preview=self.setup_batch();result=self.apply(ids,preview)
        self.s.db.execute('UPDATE tax_calculation_batches SET reason=? WHERE id=?',('alterado',result['id']));self.s.db.commit()
        with self.assertRaisesRegex(ValueError,'Manifesto'):self.s.tax_batch_detail(self.c,result['id'])
        self.s.db.execute('UPDATE tax_calculation_batches SET reason=? WHERE id=?',('Conferência sintética',result['id']))
        self.s.db.execute("UPDATE tax_calculations SET snapshot='{}' WHERE id=?",(result['snapshot']['items'][0]['calculation_id'],));self.s.db.commit()
        with self.assertRaisesRegex(ValueError,'alterada'):self.s.tax_batch_detail(self.c,result['id'])

    def test_preview_size_and_history_pagination_are_bounded(self):
        _,ids,_=self.setup_batch()
        with patch('src.tax_batch.MAX_PREVIEW_BYTES',200):
            with self.assertRaisesRegex(ValueError,'8 MiB'):self.s.preview_tax_batch(self.c,self.cycle['id'],ids)
        for index in range(22):self.apply(ids,self.s.preview_tax_batch(self.c,self.cycle['id'],ids),'batch-'+str(index))
        first=self.s.tax_batches(self.c,self.cycle['id']);last=self.s.tax_batches(self.c,self.cycle['id'],20)
        self.assertEqual((first['total'],len(first['items']),len(last['items'])),(22,20,2))
        for bad in (True,-1,'abc'):
            with self.assertRaises(ValueError):self.s.tax_batches(self.c,self.cycle['id'],bad)

    def test_migration_15_to_16_preserves_existing_calculations_and_locks(self):
        _,ids,preview=self.setup_batch()
        for item in preview['snapshot']['items']:self.s.apply_operation_tax(self.c,item['operation_id'],item['memory_hash'],'single-'+str(item['operation_id']),'Teste')
        before=[tuple(r) for r in self.s.db.execute('SELECT * FROM tax_calculations ORDER BY id')]
        from src.accounting_store import dump,digest
        self.s.db.execute('INSERT INTO module_period_versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(self.c,'2026-09','fiscal',1,'encerrada',dump({}),digest({}),dump({}),'Teste','Teste','Teste',self.s._now()))
        self.s.db.execute('DROP TABLE tax_calculation_batches');self.s.db.execute('UPDATE schema_version SET version=15');self.s.db.commit()
        with AccountingStore(self.path) as reopened:
            self.assertEqual(reopened.db.execute('SELECT version FROM schema_version').fetchone()[0],16)
            self.assertEqual([tuple(r) for r in reopened.db.execute('SELECT * FROM tax_calculations ORDER BY id')],before)
            self.assertEqual(reopened.tax_batches(self.c,self.cycle['id'])['items'],[])
            self.assertEqual(reopened.module_period_state(self.c,'2026-09','fiscal')['state'],'encerrada')
            self.assertEqual(reopened.db.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_document_v1_item_v2_and_fcp_v3_share_batch_without_changing_memory_profiles(self):
        from test_tax_items import TaxItemTests
        self.s.save_tax_code(self.c,'cfop','1101',{'description':'Código sintético','valid_from':'2026-09-01','valid_to':'','source_reference':'Fixture'},'ativo',0,'Teste')
        self.rule(key='document',cfop='1101')
        self.rule(key='item',item_treatment='OLD',calculation=TaxItemTests.calc(self))
        self.rule(key='credit',rate='3',effect='credito',item_treatment='CREDIT',calculation=TaxItemTests.calc(self))
        self.rule(key='fcp',tax='FCP',base_field='fcp_base',rate='2',item_treatment='FCP',
                  calculation=TaxItemTests.calc(self,'fcp',component_code='TESTE',base_mode='declarada'))
        rows=[self.operation(n) for n in (1,2,3)]
        for index,row in enumerate(rows):
            payload=copy.deepcopy(row['payload'])
            if index==0:payload['fiscal']['cfop']='1101'
            elif index==1:
                payload['tax_items']=[TaxItemTests.item(self,'A','50.15',treatment='OLD'),TaxItemTests.item(self,'B','50.15',treatment='CREDIT')]
            else:
                payload['tax_items']=[TaxItemTests.item(self,treatment='OLD' if index==1 else 'FCP',taxes=['ICMS'] if index==1 else ['FCP:TESTE'],
                    values={'total':'100.30',**({'fcp_base':'100.30'} if index==2 else {})})]
            self.save(payload,row['operation_id'],row['version'])
        ids=[row['operation_id'] for row in rows];preview=self.s.preview_tax_batch(self.c,self.cycle['id'],ids)
        self.assertTrue(preview['snapshot']['ready'])
        result=self.apply(ids,preview)
        self.assertEqual([c['snapshot']['profile'] for c in result['calculations']],['tributacao-parametrizada-v1','tributacao-itens-v2','tributacao-itens-v3'])
        self.assertEqual(preview['snapshot']['items'][2]['components'][0]['effect'],'debito')
        self.assertEqual(preview['snapshot']['items'][1]['components'][0]['effect'],'credito, debito')
        self.assertEqual(preview['snapshot']['items'][1]['components'][0]['amount'],'2.75')
        self.assertNotIn('grossup_groups',result['calculations'][1]['snapshot'])

    def test_competing_new_batches_cannot_reuse_the_same_stale_preview(self):
        _,ids,preview=self.setup_batch()
        def apply(index):
            with AccountingStore(self.path) as store:
                try:
                    store.apply_tax_batch(self.c,self.cycle['id'],ids,preview['snapshot_hash'],'competing-'+str(index),'Teste',True)
                    return True
                except ValueError:return False
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(apply,range(2)))
        self.assertEqual(sorted(results),[False,True])
        self.assertEqual(self.s.tax_batches(self.c,self.cycle['id'])['total'],1)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM tax_calculations').fetchone()[0],2)


if __name__=='__main__':unittest.main()
