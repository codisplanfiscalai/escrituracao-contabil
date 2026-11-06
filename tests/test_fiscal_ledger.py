"""Fictitious fiscal records, revisions, period protection and participants."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET
from src.persistence import AccountingStore, parse_nfe
from src.reconciliation import XML_PROFILE, SPED_PROFILE, parse_sped
from test_persistence import fake_xml, edit_xml, ISSUER, BUYER, NS, fictitious_key
from test_reconciliation import fake_sped


def nfce():
    root = ET.fromstring(fake_xml(billing=False))
    info = root.find('.//{'+NS+'}infNFe')
    key = fictitious_key()[:20] + '65' + fictitious_key()[22:43]
    dv = 11 - sum(int(d)*(2+i%8) for i,d in enumerate(reversed(key))) % 11
    key += str(0 if dv >= 10 else dv)
    info.set('Id','NFe'+key)
    info.find('{'+NS+'}ide/{'+NS+'}mod').text='65'
    info.find('{'+NS+'}ide/{'+NS+'}cDV').text=key[-1]
    info.remove(info.find('{'+NS+'}dest'))
    return ET.tostring(root)


class FiscalLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'fictitious.sqlite3'
        self.s=AccountingStore(self.path,'operador-ficticio');self.addCleanup(self.s.close)
        self.c=self.s.create_company('Fictícia','TEST','TEST',BUYER)['id']
        self.p=self.s.create_period(self.c,'2026-08','2026-09')['id']
        self.seq=0

    def fields(self):
        return dict(model='55',number='1',series='1',key='',operation='entrada',issued_date='2026-08-15',entry_date='2026-09-01',posting_date='2026-09-02',issuer=ISSUER,buyer=BUYER,total='100.30',notes='Somente dados fictícios')

    def save(self,data=None,**kwargs):
        self.seq+=1
        return self.s.save_fiscal_entry(self.c,self.p,data or self.fields(),'Motivo fictício',kwargs.pop('request_key',f'try-{self.seq}'),**kwargs)

    def review(self,r):
        return self.s.review_fiscal_entry(self.c,r['entry_id'],r['snapshot_hash'],'Conferência fictícia',True)

    def transition(self,target,**kwargs):
        state=self.s.fiscal_period_status(self.c,self.p)
        return self.s.change_fiscal_period(self.c,self.p,target,state['token'],'Motivo fictício',True,**kwargs)

    def test_manual_history_review_and_restart(self):
        one=self.save();self.assertTrue(one['warnings']);self.review(one)
        two=self.save({**self.fields(),'total':'130.00'},entry_id=one['entry_id'],expected_version=1)
        self.assertEqual(two['state'],'rascunho')
        with AccountingStore(self.path) as reopened:
            rows=reopened.list_fiscal_entries(self.c,self.p)
            self.assertEqual(rows[0]['current']['version'],2)
            self.assertEqual(rows[0]['history'][1]['data']['total'],'100.30')
            self.assertEqual(rows[0]['history'][1]['state'],'revisado')

    def test_exact_attempt_idempotence_and_concurrency(self):
        one=self.save(request_key='same')
        repeat=self.save(request_key='same');self.assertEqual(one['id'],repeat['id'])
        with self.assertRaisesRegex(ValueError,'conteúdo'):self.save({**self.fields(),'total':'9.00'},request_key='same')
        with AccountingStore(self.path) as other:
            other.save_fiscal_entry(self.c,self.p,self.fields(),'Outra decisão','other',1,one['entry_id'])
        with self.assertRaisesRegex(ValueError,'alterada'):self.save(entry_id=one['entry_id'],expected_version=1)

    def test_closed_exported_proposals_preserve_current_and_no_reopen_export(self):
        one=self.save()
        with self.assertRaisesRegex(ValueError,'Revise'):self.transition('fechado')
        self.review(one);self.transition('fechado')
        with self.assertRaisesRegex(ValueError,'proposta'):self.save(entry_id=one['entry_id'],expected_version=1)
        proposed=self.save({**self.fields(),'total':'20.00'},entry_id=one['entry_id'],expected_version=1,as_proposal=True)
        self.assertEqual(proposed['state'],'retificacao_pendente')
        self.assertEqual(self.s.list_fiscal_entries(self.c)[0]['current']['data']['total'],'100.30')
        self.transition('exportado',reference='REFERENCIA-EXTERNA-FICTICIA')
        with self.assertRaisesRegex(ValueError,'retificação'):self.transition('aberto')
        self.assertEqual(len(self.s.fiscal_period_status(self.c,self.p)['history']),2)

    def test_period_scope_cannot_be_bypassed_by_other_base(self):
        r=self.save();self.review(r);self.transition('fechado')
        alternate=self.s.create_period(self.c,'2026-07','2026-09')['id']
        with self.assertRaisesRegex(ValueError,'fechado'):
            self.s.save_fiscal_entry(self.c,alternate,self.fields(),'Motivo','alternate')
        self.transition('aberto')
        self.assertEqual(self.s.fiscal_period_status(self.c,alternate)['state'],'aberto')

    def test_no_identity_fabrication_and_structural_validation(self):
        for field,value in [('total',1.2),('total','-1.00'),('posting_date','2026-08-01'),('key','1'*44),('issued_date','2026-02-30')]:
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):self.save({**self.fields(),field:value})
        one=self.save();two=self.save()
        self.assertTrue(any('coincidência' in w for w in two['warnings']))
        self.assertEqual(one['data']['key'],'')

    def test_source_edits_leave_bytes_and_canonical_payload_intact(self):
        content=fake_xml(issued='2026-08-15T10:00:00-03:00')
        f=self.s.import_file(self.c,self.p,'ficticio.xml',content,'XML')
        doc=self.s.list_documents(self.c)[0];seed=self.s.fiscal_seed(self.c,self.p,doc['id'])
        data={**seed['data'],'posting_date':'2026-09-03','total':'110.30'}
        r=self.save(data,document_id=doc['id'],expected_source_hash=seed['source_hash'])
        self.review(r)
        self.assertEqual(self.s.list_documents(self.c)[0]['payload']['total'],'100.30')
        self.assertEqual(bytes(self.s.db.execute('SELECT original FROM files WHERE id=?',(f['id'],)).fetchone()[0]),content)
        with self.assertRaisesRegex(ValueError,'já possui'):self.save(data,document_id=doc['id'],expected_source_hash=seed['source_hash'])
        self.s.import_file(self.c,self.p,'outra-origem.xml',fake_xml(issued='2026-08-15T10:00:00-03:00',wrapper=False),'XML')
        self.assertFalse(self.s.list_fiscal_entries(self.c)[0]['source_current'])
        with self.assertRaisesRegex(ValueError,'Fontes alteradas'):self.save(data,entry_id=r['entry_id'],expected_version=1,expected_source_hash=seed['source_hash'])

    def test_nfce_without_buyer_and_sped_dates_and_model(self):
        company=self.s.create_company('Emitente fictício','E','E',ISSUER)['id'];period=self.s.create_period(company,'2026-08','2026-09')['id']
        f=self.s.import_file(company,period,'nfce.xml',nfce(),'XML');self.assertEqual(f['status'],'validado')
        payload=parse_nfe(nfce());self.assertEqual(payload['model'],'65');self.assertEqual(payload['buyer'],'')
        sped=fake_sped(key=payload['key']).replace(b'|55|00|',b'|65|00|')
        rows,_=parse_sped(sped,ISSUER,'2026-09');self.assertEqual(next(r for r in rows if r['record']=='C100')['normalized']['model'],'65')
        rows,_=parse_sped(fake_sped(emitted='15082026',key=fictitious_key(month='2608')),ISSUER,'2026-09')
        self.assertEqual(next(r for r in rows if r['record']=='C100')['normalized']['issued_date'],'2026-08-15')

    def test_legacy_rejection_can_be_reassessed_without_erasing_evidence(self):
        f=self.s.import_file(self.c,self.p,'antigo.xml',fake_xml(issued='2026-08-15T10:00:00-03:00'),'XML')
        with self.s.db:
            self.s.db.execute('DELETE FROM source_observations WHERE file_id=?',(f['id'],))
            self.s.db.execute('DELETE FROM file_indexings WHERE file_id=?',(f['id'],))
            self.s.db.execute("UPDATE files SET status='rejeitado',metadata=? WHERE id=?",(json.dumps({'error':'Competência antiga'}),f['id']))
        result=self.s.index_file(self.c,f['id'],XML_PROFILE)
        self.assertNotIn('error',result['metadata'])
        row=self.s._file(self.c,f['id']);self.assertEqual(row['status'],'pendente')
        self.assertIn('previous_validation',row['metadata'])

    def test_isolation_audit_rollback_and_review_hash(self):
        one=self.save();other=self.s.create_company('Outra','O','O',BUYER)['id']
        with self.assertRaises(ValueError):self.s.review_fiscal_entry(other,one['entry_id'],one['snapshot_hash'],'Motivo',True)
        with self.assertRaises(ValueError):self.s.review_fiscal_entry(self.c,one['entry_id'],'stale','Motivo',True)
        with self.assertRaisesRegex(ValueError,'avisos'):self.s.review_fiscal_entry(self.c,one['entry_id'],one['snapshot_hash'],'Motivo')
        with patch.object(self.s,'_audit',side_effect=RuntimeError('audit failed')):
            with self.assertRaises(RuntimeError):self.save(entry_id=one['entry_id'],expected_version=1)
        self.assertEqual(len(self.s.list_fiscal_entries(self.c)[0]['history']),1)

    def test_service_and_participant_review(self):
        a=self.s.save_participant(self.c,ISSUER,'Fornecedor fictício','fornecedor','Cadastro fictício')
        b=self.s.save_participant(self.c,ISSUER,'Outro nome fictício','prestador','Outra origem')
        self.assertEqual(a['id'],b['id']);self.assertEqual(b['name'],a['name']);self.assertTrue(b['pending'])
        reviewed=self.s.review_participant(self.c,b['id'],b['version'],b['observations'][0]['id'],'Conferido')
        self.assertFalse(reviewed['pending']);self.assertEqual(reviewed['name'],'Outro nome fictício')
        r=self.save({**self.fields(),'model':'SERVICO','operation':'servico_tomado','number':'SERV-1','series':'','participant_id':str(a['id']),'service_code':'INFORMADO','iss_base':'100.30','iss_amount':'5.00'})
        self.assertEqual(r['data']['iss_amount'],'5.00');self.assertTrue(r['source_snapshot']['participant'])
        self.assertTrue(any('sem cálculo' in w for w in r['warnings']))

    def test_import_participants_no_duplicates_names_preserved_and_anonymous_skipped(self):
        xml=fake_xml();self.s.import_file(self.c,self.p,'um.xml',xml,'XML')
        self.s.import_file(self.c,self.p,'dois.xml',edit_xml(xml,'emit/xNome','Novo nome fictício'),'XML')
        parties=self.s.list_participants(self.c);self.assertEqual(len(parties),1);self.assertTrue(parties[0]['pending'])
        self.assertEqual(parties[0]['name'],'Emitente inteiramente fictício')
        self.assertEqual(parties[0]['roles'],['fornecedor'])

    def test_workspace_tabs_persist_and_are_private_to_actor(self):
        a=self.s.save_fiscal_workspace(self.c,self.p,'Entrada',{'data':{'number':'1'}},'tab1')
        b=self.s.save_fiscal_workspace(self.c,self.p,'Serviço',{'data':{'number':'2'}},'tab2')
        with AccountingStore(self.path,'operador-ficticio') as s:
            self.assertEqual(len(s.list_fiscal_workspaces(self.c,self.p)),2)
        with AccountingStore(self.path,'outro-operador') as s:
            self.assertEqual(s.list_fiscal_workspaces(self.c,self.p),[])
            with self.assertRaises(ValueError):s.save_fiscal_workspace(self.c,self.p,'Tentativa',{},'other',a['id'],a['version'])
        updated=self.s.save_fiscal_workspace(self.c,self.p,'Entrada',{'data':{'number':'3'}},'tab1',a['id'],a['version'])
        with self.assertRaises(ValueError):self.s.save_fiscal_workspace(self.c,self.p,'Entrada',{},'tab1',a['id'],a['version'])
        self.s.save_fiscal_workspace(self.c,self.p,'Entrada',updated['data'],'tab1',a['id'],updated['version'],True)
        self.assertEqual(self.s.list_fiscal_workspaces(self.c,self.p)[0]['id'],b['id'])

    def test_manual_key_can_explicitly_link_later_import_without_duplicate(self):
        data={**self.fields(),'key':fictitious_key(month='2608')}
        r=self.save(data)
        self.s.import_file(self.c,self.p,'chegou-depois.xml',fake_xml(issued='2026-08-15T10:00:00-03:00'),'XML')
        doc=self.s.list_documents(self.c)[0];seed=self.s.fiscal_seed(self.c,self.p,doc['id'])
        linked=self.save(data,entry_id=r['entry_id'],expected_version=1,document_id=doc['id'],expected_source_hash=seed['source_hash'])
        rows=self.s.list_fiscal_entries(self.c)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['document_id'],doc['id'])
        self.assertEqual(rows[0]['history'][1]['source_snapshot'],{})
        self.assertTrue(linked['source_snapshot'])
        with self.assertRaisesRegex(ValueError,'já possui'):
            self.save(data,document_id=doc['id'],expected_source_hash=seed['source_hash'])

    def test_closed_fiscal_source_cannot_be_removed(self):
        f=self.s.import_file(self.c,self.p,'origem.xml',fake_xml(),'XML')
        doc=self.s.list_documents(self.c)[0];seed=self.s.fiscal_seed(self.c,self.p,doc['id'])
        r=self.save({**seed['data'],'posting_date':'2026-09-03'},document_id=doc['id'],expected_source_hash=seed['source_hash'])
        self.review(r);self.transition('fechado')
        preview=self.s.deletion_preview(self.c,f['id'])
        self.assertEqual(preview['protected_fiscal_entry_ids'],[r['entry_id']])
        with self.assertRaisesRegex(ValueError,'fiscal protegido'):
            self.s.delete_file(self.c,f['id'],'Motivo',True,preview['preview_token'])
        self.assertNotEqual(self.s._file(self.c,f['id'])['status'],'excluido')

    def test_participant_review_refuses_unseen_observation(self):
        a=self.s.save_participant(self.c,ISSUER,'Primeiro nome','fornecedor','Teste')
        b=self.s.save_participant(self.c,ISSUER,'Segundo nome','fornecedor','Teste')
        with self.assertRaisesRegex(ValueError,'alterado'):
            self.s.review_participant(self.c,a['id'],a['version'],a['observations'][0]['id'],'Teste')
        self.assertTrue(b['pending'])

    def test_sped_known_issuer_without_name_is_pending_not_fabricated(self):
        self.s.import_file(self.c,self.p,'origem.sped',fake_sped(company=BUYER).replace(b'|C100|1|0|',b'|C100|0|1|'),'SPED',sped_profile=SPED_PROFILE)
        parties=self.s.list_participants(self.c)
        self.assertEqual(len(parties),1)
        self.assertEqual(parties[0]['identifier_value'],ISSUER)
        self.assertEqual(parties[0]['name'],'')
        self.assertTrue(parties[0]['pending'])

    def test_migration_from_five_preserves_business_rows(self):
        f=self.s.import_file(self.c,self.p,'origem.xml',fake_xml(),'XML')
        with self.s.db:
            for table in ('participant_observations','participants','fiscal_workspaces','fiscal_revisions','fiscal_entries','fiscal_period_history','fiscal_period_states'):
                self.s.db.execute('DROP TABLE '+table)
            self.s.db.execute('UPDATE schema_version SET version=5')
        with AccountingStore(self.path) as reopened:
            self.assertEqual(reopened.db.execute('SELECT version FROM schema_version').fetchone()[0],11)
            self.assertEqual(bytes(reopened.db.execute('SELECT original FROM files WHERE id=?',(f['id'],)).fetchone()[0]),fake_xml())
            self.assertEqual(reopened.list_fiscal_entries(self.c),[])
            self.assertEqual(reopened.list_participants(self.c),[])


if __name__=='__main__':unittest.main()
