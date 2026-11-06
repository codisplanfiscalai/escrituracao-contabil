"""Fictitious document review and explicit accounting regression coverage."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
from contextlib import closing
import tempfile
import threading
import unittest
from unittest.mock import patch

from src.persistence import AccountingStore, SCHEMA
from src.reconciliation_store import RECONCILIATION_SCHEMA
from src.reconciliation import SPED_PROFILE
from test_persistence import fake_accounts, fake_xml, edit_xml, ISSUER
from test_reconciliation import fake_sped


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'ficticio.sqlite3'
        self.s = AccountingStore(self.path, actor='operador-ficticio')
        self.addCleanup(lambda: self.s.close())
        self.c = self.s.create_company('Fictícia', 'T', 'T', ISSUER)['id']
        self.p = self.s.create_period(self.c, '2026-08', '2026-09')['id']
        self.plan = self.s.import_plan(self.c, 'Plano fictício', fake_accounts())['id']
        self.maps = [self.s.save_mapping(self.c, self.plan, 'origem-'+str(i), code, '2026-09', state='aprovado', reason='Teste fictício')['id'] for i,code in enumerate(('1.1.1','2.1'))]
        self.file = self.s.import_file(self.c,self.p,'ficticio.xml',fake_xml(),'XML')['id']
        self.doc = self.s.list_reconciliation(self.c)[0]['document_id']
        self.obs = self.s.list_reconciliation(self.c)[0]['sources'][0]['id']

    def decision(self, chosen=None):
        row = next(row for row in self.s.list_reconciliation(self.c) if row['document_id']==self.doc)
        return self.s.save_document_review(self.c,self.doc,self.p,chosen or self.obs,row['source_fingerprint'],'Conferência fictícia explícita')

    def lines(self):
        return [dict(document_id=self.doc,observation_id=self.obs,group='documental',date='2026-09-15',side=side,amount='100.30',mapping_id=mapping,memo='Histórico fictício') for side,mapping in zip(('D','C'),self.maps)]

    def batch(self,key='ficticio-1',entries=None,previous=None):
        return self.s.create_accounting_batch(self.c,self.p,self.plan,key,self.lines() if entries is None else entries,'Prévia fictícia',previous)

    def close(self,batch):
        self.s.review_accounting_batch(self.c,batch['id'],batch['snapshot_hash'],'Revisão fictícia')
        return self.s.close_accounting_batch(self.c,batch['id'],batch['snapshot_hash'],'Fechamento local fictício')

    def test_review_versions_source_choice_differences_and_no_export(self):
        self.s.import_file(self.c,self.p,'ficticio.sped',fake_sped(total='101,30'),'SPED',SPED_PROFILE)
        self.decision()
        first=self.s.list_document_reviews(self.c)[0]
        row=self.s.list_reconciliation(self.c)[0]
        self.assertTrue(row['differences'])
        self.assertTrue(row['readiness_for_accounting'])
        self.assertFalse(row['ready_for_export'])
        sped=next(x for x in row['sources'] if x['source_kind']=='SPED')
        self.decision(sped['id'])
        history=self.s.list_document_reviews(self.c,self.doc)
        self.assertEqual([x['version'] for x in history],[2,1])
        self.assertFalse(history[1]['current'])
        self.assertEqual(history[1]['snapshot'],first['snapshot'])
        self.assertEqual(self.s.list_documents(self.c)[0]['payload']['total'],'100.30')
        with self.assertRaisesRegex(ValueError,'escolhida'):self.batch()

    def test_review_stale_after_new_source_reanalysis_or_removal(self):
        self.decision()
        batch=self.batch()
        old=self.s.list_reconciliation(self.c)[0]['source_fingerprint']
        extra=self.s.import_file(self.c,self.p,'ficticio2.xml',fake_xml(wrapper=False),'XML')['id']
        self.assertFalse(self.s.list_reconciliation(self.c)[0]['review']['valid'])
        with self.assertRaisesRegex(ValueError,'desatualizada'):
            self.s.save_document_review(self.c,self.doc,self.p,self.obs,old,'Motivo fictício')
        with self.assertRaisesRegex(ValueError,'caduca'):
            self.s.review_accounting_batch(self.c,batch['id'],batch['snapshot_hash'],'Revisão fictícia')
        self.decision()
        preview=self.s.deletion_preview(self.c,extra)
        self.s.delete_file(self.c,extra,'Remoção fictícia',True,preview['preview_token'])
        self.assertFalse(self.s.list_reconciliation(self.c)[0]['review']['valid'])
        self.assertEqual(self.s._batch(self.c,batch['id'])['snapshot'],batch['snapshot'])

    def test_missing_review_and_ambiguous_billing_cannot_be_resolved_by_source_selection(self):
        with self.assertRaisesRegex(ValueError,'Revisão documental'):self.batch()
        self.s.import_file(self.c,self.p,'ambiguo.xml',edit_xml(fake_xml(),'cobr/fat/nFat','OUTRO-FICTICIO'),'XML')
        status=self.decision()
        self.assertTrue(status['review']['valid'])
        self.assertFalse(status['readiness_for_accounting'])
        self.assertIn('duplicidade',';'.join(status['accounting_blockers']))
        with self.assertRaisesRegex(ValueError,'identidade'):self.batch()

    def test_isolation_period_and_origin_validation(self):
        other=self.s.create_company('Outra fictícia','O','O',ISSUER)['id']
        with self.assertRaises(ValueError):self.s.save_document_review(other,self.doc,self.p,self.obs,'x','Teste')
        self.decision()
        lines=self.lines();lines[0]['observation_id']=self.obs+1
        with self.assertRaises(ValueError):self.batch(entries=lines)
        period=self.s.create_period(self.c,'2026-07','2026-09')['id']
        with self.assertRaises(ValueError):self.s.save_document_review(self.c,self.doc,period,self.obs,'x','Teste')
        batch=self.batch()
        with self.assertRaises(ValueError):self.s.review_accounting_batch(other,batch['id'],batch['snapshot_hash'],'Teste')
        self.assertEqual(self.s.list_accounting_batches(other),[])

    def test_decimal_exact_split_groups_and_totals(self):
        self.decision();lines=[]
        for group,value in (('a','0.10'),('b','0.20'),('c','100.00')):
            for line in self.lines():
                line.update(group=group,amount=value);lines.append(line)
        batch=self.batch(entries=lines)
        self.assertEqual(batch['snapshot']['totals'],{'debit':'100.30','credit':'100.30'})
        self.assertEqual(len(batch['snapshot']['groups']),3)
        self.assertEqual(self.close(batch)['status'],'fechado')

    def test_reject_floats_nonfinite_precision_zero_and_unbalanced_or_untraced_values(self):
        self.decision()
        for value in (100.3,True,'NaN','Infinity','0','-1','0.001','1e2','10000000000000000.00'):
            with self.subTest(value=value):
                lines=self.lines();lines[0]['amount']=value
                with self.assertRaises(ValueError):self.batch(entries=lines)
        lines=self.lines();lines[0]['amount']='100.29'
        with self.assertRaisesRegex(ValueError,'equilibrar'):self.batch(entries=lines)
        lines=self.lines();lines[0]['amount']=lines[1]['amount']='100.00'
        with self.assertRaisesRegex(ValueError,'fonte escolhida'):self.batch(entries=lines)
        lines=self.lines();lines[0]['group']='outro'
        with self.assertRaisesRegex(ValueError,'equilibrar'):self.batch(entries=lines)
        self.assertEqual(self.s.list_accounting_batches(self.c),[])

    def test_dates_and_mapping_version_approval_validity_plan_and_analytic_target(self):
        self.decision()
        for day in ('2026-08-15','2026-09-31','20260915'):
            lines=self.lines();lines[0]['date']=day
            with self.assertRaises(ValueError):self.batch(entries=lines)
        plan=self.s.import_plan(self.c,'Outro plano fictício',fake_accounts())['id']
        wrong=self.s.save_mapping(self.c,plan,'x','1.1.1','2026-09',state='aprovado',reason='Teste')['id']
        lines=self.lines();lines[0]['mapping_id']=wrong
        with self.assertRaisesRegex(ValueError,'plano'):self.batch(entries=lines)
        with self.assertRaisesRegex(ValueError,'analítica'):self.s.save_mapping(self.c,self.plan,'x','1','2026-09',state='aprovado',reason='Teste')
        for start,end,state in (('2026-10',None,'aprovado'),('2026-07','2026-08','aprovado'),('2026-09',None,'rascunho')):
            new=self.s.save_mapping(self.c,self.plan,'x','1.1.1',start,valid_to=end,state=state,reason='Teste')['id']
            lines=self.lines();lines[0]['mapping_id']=new
            with self.assertRaisesRegex(ValueError,'vigente'):self.batch(entries=lines)
        batch=self.batch()
        self.s.save_mapping(self.c,self.plan,'origem-0','1.1.1','2026-09',state='inativo',reason='Teste')
        with self.assertRaisesRegex(ValueError,'vigente'):self.s.review_accounting_batch(self.c,batch['id'],batch['snapshot_hash'],'Teste')

    def test_idempotence_reservation_independent_of_group_mapping_and_period(self):
        self.decision();batch=self.batch()
        self.assertEqual(self.batch()['id'],batch['id'])
        self.assertEqual(self.s.list_audit(self.c)[0]['action'],'lote_contabil_repetido')
        with self.assertRaisesRegex(ValueError,'conteúdo diferente'):self.batch(entries=list(reversed(self.lines())))
        with self.assertRaisesRegex(ValueError,'reservado'):self.batch('novo')
        new=self.s.save_mapping(self.c,self.plan,'origem-0','1.1.1','2026-09',state='aprovado',reason='Teste')['id']
        lines=self.lines();lines[0]['mapping_id']=new
        for line in lines:line['group']='rótulo-novo'
        with self.assertRaisesRegex(ValueError,'reservado'):self.batch('nova-versao',lines)

    def test_concurrent_previews_reserve_one_event(self):
        self.decision();barrier=threading.Barrier(2);entries=self.lines()
        def attempt(key):
            with AccountingStore(self.path) as store:
                barrier.wait()
                try:return store.create_accounting_batch(self.c,self.p,self.plan,key,entries,'Teste')['id']
                except ValueError:return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(attempt,['concurrente-a','concorrente-b']))
        self.assertEqual(sum(value is not None for value in results),1)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM accounting_events').fetchone()[0],1)

    def test_review_required_hash_and_revalidation_at_close(self):
        self.decision();batch=self.batch()
        with self.assertRaisesRegex(ValueError,'revisão explícita'):self.s.close_accounting_batch(self.c,batch['id'],batch['snapshot_hash'],'Teste')
        with self.assertRaisesRegex(ValueError,'Hash'):self.s.review_accounting_batch(self.c,batch['id'],'errado','Teste')
        self.s.review_accounting_batch(self.c,batch['id'],batch['snapshot_hash'],'Teste')
        self.decision() # even same source with a new decision requires a new snapshot
        with self.assertRaisesRegex(ValueError,'Snapshot desatualizado'):self.s.close_accounting_batch(self.c,batch['id'],batch['snapshot_hash'],'Teste')

    def test_corrections_preserve_history_and_closed_reservation(self):
        self.decision();first=self.batch();second=self.batch('versao-2',previous=first['id'])
        self.assertEqual(second['version'],2)
        self.assertEqual(self.s._batch(self.c,first['id'])['status'],'substituido')
        self.assertEqual(self.s._batch(self.c,first['id'])['snapshot'],first['snapshot'])
        closed=self.close(second)
        third=self.batch('versao-3',previous=closed['id'])
        self.s.review_accounting_batch(self.c,third['id'],third['snapshot_hash'],'Teste')
        with self.assertRaisesRegex(ValueError,'estorno'):self.s.close_accounting_batch(self.c,third['id'],third['snapshot_hash'],'Teste')
        self.assertEqual(self.s._batch(self.c,closed['id']),closed)
        self.assertEqual(self.s.db.execute('SELECT batch_id FROM accounting_events').fetchone()[0],closed['id'])
        self.s.close();self.s=AccountingStore(self.path)
        self.assertEqual(self.s._batch(self.c,closed['id']),closed)

    def test_closed_sources_cannot_be_removed_and_new_sources_do_not_change_history(self):
        self.decision();batch=self.close(self.batch())
        preview=self.s.deletion_preview(self.c,self.file)
        self.assertEqual(preview['closed_batch_ids'],[batch['id']])
        with self.assertRaisesRegex(ValueError,'fechado'):self.s.delete_file(self.c,self.file,'Teste',True,preview['preview_token'])
        self.s.import_file(self.c,self.p,'fonte-nova.xml',fake_xml(wrapper=False),'XML')
        self.assertEqual(self.s._batch(self.c,batch['id']),batch)
        self.assertTrue(self.s.list_accounting_batches(self.c)[0]['current_blockers'])

    def test_mutations_roll_back_with_audit_failure(self):
        row=self.s.list_reconciliation(self.c)[0]
        with patch.object(self.s,'_audit',side_effect=RuntimeError('Falha fictícia')):
            with self.assertRaises(RuntimeError):self.s.save_document_review(self.c,self.doc,self.p,self.obs,row['source_fingerprint'],'Teste')
        self.assertEqual(self.s.list_document_reviews(self.c),[])
        self.decision()
        with patch.object(self.s,'_audit',side_effect=RuntimeError('Falha fictícia')):
            with self.assertRaises(RuntimeError):self.batch()
        self.assertEqual(self.s.list_accounting_batches(self.c),[])
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM accounting_events').fetchone()[0],0)
        batch=self.batch()
        with patch.object(self.s,'_audit',side_effect=RuntimeError('Falha fictícia')):
            with self.assertRaises(RuntimeError):self.batch('correcao',previous=batch['id'])
            with self.assertRaises(RuntimeError):self.s.review_accounting_batch(self.c,batch['id'],batch['snapshot_hash'],'Teste')
        self.assertEqual(self.s._batch(self.c,batch['id'])['status'],'previa')
        self.assertEqual(self.s.db.execute('SELECT batch_id FROM accounting_events').fetchone()[0],batch['id'])

    def test_late_mapping_or_source_change_blocks_close_without_mutating_snapshot(self):
        self.decision();batch=self.batch()
        self.s.review_accounting_batch(self.c,batch['id'],batch['snapshot_hash'],'Teste')
        self.s.save_mapping(self.c,self.plan,'origem-0','1.1.1','2026-10',state='aprovado',reason='Futuro fictício')
        self.assertEqual(self.s.list_accounting_batches(self.c)[0]['current_blockers'],[])
        self.s.save_mapping(self.c,self.plan,'origem-0','1.1.1','2026-09',state='rascunho',reason='Rascunho fictício')
        with self.assertRaisesRegex(ValueError,'vigente'):
            self.s.close_accounting_batch(self.c,batch['id'],batch['snapshot_hash'],'Teste')
        self.assertEqual(self.s._batch(self.c,batch['id'])['snapshot'],batch['snapshot'])
        self.assertEqual(self.s._batch(self.c,batch['id'])['status'],'revisado')

    def test_different_context_and_unindexed_legacy_sources_remain_blocked(self):
        other_period=self.s.create_period(self.c,'2026-07','2026-09')['id']
        self.s.import_file(self.c,other_period,'ficticio.xml',fake_xml(wrapper=False),'XML')
        self.assertFalse(self.decision()['readiness_for_accounting'])
        with self.assertRaisesRegex(ValueError,'Contextos'):self.batch()
        # Simulate a preserved legacy linked source without implicit indexing.
        unindexed=self.s.import_file(self.c,self.p,'legado.sped',fake_sped(),'SPED')['id']
        with self.s.db:
            self.s.db.execute('INSERT INTO document_sources(document_id,file_id) VALUES(?,?)',(self.doc,unindexed))
        state=self.s.list_reconciliation(self.c)[0]
        self.assertFalse(state['readiness_for_accounting'])
        self.assertIn('Fonte vinculada ainda não analisada',state['accounting_blockers'])
        with self.assertRaisesRegex(ValueError,'Observação'):
            self.s.save_document_review(self.c,self.doc,self.p,999999,state['source_fingerprint'],'Teste')

    def test_multi_document_batch_balances_each_document_and_preserves_all_origins(self):
        self.decision();first_doc=self.doc;first_obs=self.obs;lines=self.lines()
        self.s.import_file(self.c,self.p,'segundo.xml',fake_xml(number=2),'XML')
        row=next(row for row in self.s.list_reconciliation(self.c) if row['document_id']!=first_doc)
        self.doc=row['document_id'];self.obs=row['sources'][0]['id'];self.decision()
        lines+=self.lines()
        invalid=[dict(line) for line in lines]
        invalid[0]['amount']='101.30';invalid[2]['amount']='99.30'
        with self.assertRaisesRegex(ValueError,'equilibrar'):self.batch(entries=invalid)
        batch=self.batch(entries=lines)
        self.assertEqual(batch['snapshot']['totals']['debit'],'200.60')
        self.assertEqual({line['observation_id'] for line in batch['snapshot']['entries']},{first_obs,self.obs})
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM accounting_events').fetchone()[0],2)
        self.close(batch)

    def test_schema2_migration_and_failed_migration_are_atomic(self):
        legacy=Path(self.temp.name)/'legacy.sqlite3'
        with closing(sqlite3.connect(legacy)) as db, db:
            db.executescript(SCHEMA+RECONCILIATION_SCHEMA)
            db.execute('INSERT INTO schema_version VALUES(2)')
            db.execute("INSERT INTO companies VALUES(1,'Empresa fictícia','T','T',?,'instante-ficticio')",(ISSUER,))
        with patch('src.persistence.ACCOUNTING_SCHEMA','CREATE TABLE temporary_migration(id INTEGER); INVALID SQL;'):
            with self.assertRaises(sqlite3.OperationalError):AccountingStore(legacy)
        with closing(sqlite3.connect(legacy)) as db, db:
            self.assertEqual(db.execute('SELECT version FROM schema_version').fetchone()[0],2)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='temporary_migration'").fetchone())
        with AccountingStore(legacy) as store:
            self.assertEqual(store.db.execute('SELECT version FROM schema_version').fetchone()[0],15)
            self.assertEqual(store.list_companies()[0]['created_at'],'instante-ficticio')

    def test_fiscal_revision_invalidates_open_accounting_and_preserves_closed(self):
        self.decision();batch=self.batch()
        seed=self.s.fiscal_seed(self.c,self.p,self.doc)
        row=self.s.save_fiscal_entry(self.c,self.p,{**seed['data'],'posting_date':'2026-09-15'},'Escrituração fictícia','fiscal-test',document_id=self.doc,expected_source_hash=seed['source_hash'])
        with self.assertRaises(ValueError):self.close(batch)
        self.s.review_fiscal_entry(self.c,row['entry_id'],row['snapshot_hash'],'Conferido',True)
        self.decision()
        correction=self.batch('corrigido',previous=batch['id']);closed=self.close(correction)
        old_snapshot=closed['snapshot']
        seed=self.s.fiscal_seed(self.c,self.p,self.doc)
        with self.assertRaisesRegex(ValueError,'fechados'):
            self.s.save_fiscal_entry(self.c,self.p,{**seed['data'],'posting_date':'2026-09-15','total':'200.00'},'Correção','fiscal-edit',1,row['entry_id'],self.doc,seed['source_hash'])
        proposed=self.s.save_fiscal_entry(self.c,self.p,{**seed['data'],'posting_date':'2026-09-15','total':'200.00'},'Correção','fiscal-proposal',1,row['entry_id'],self.doc,seed['source_hash'],True)
        self.assertEqual(proposed['state'],'retificacao_pendente')
        self.assertEqual(self.s._batch(self.c,closed['id'])['snapshot'],old_snapshot)

    def test_fiscal_total_edit_is_not_silently_ignored_by_accounting(self):
        seed=self.s.fiscal_seed(self.c,self.p,self.doc)
        row=self.s.save_fiscal_entry(self.c,self.p,{**seed['data'],'posting_date':'2026-09-15','total':'200.00'},'Correção fictícia','fiscal-total',document_id=self.doc,expected_source_hash=seed['source_hash'])
        self.s.review_fiscal_entry(self.c,row['entry_id'],row['snapshot_hash'],'Conferido',True)
        self.decision()
        with self.assertRaisesRegex(ValueError,'diverge'):self.batch()
