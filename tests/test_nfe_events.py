"""Synthetic processed events; no real authorization or automatic fiscal effects."""
import copy
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import unittest
import xml.etree.ElementTree as ET
from test_persistence import fake_xml,fictitious_key,ISSUER,NS
import test_work_application as fixtures
from src.persistence import AccountingStore
from src.nfe_events import parse_nfe_event


def event_xml(*,kind='110111',sequence='1',code='135',environment='1',key=None,text=None):
    key=key or fictitious_key(1,'2609')
    root=ET.Element('{'+NS+'}procEventoNFe',{'versao':'1.00'})
    def group(parent,name,values,attrs=None):
        node=ET.SubElement(parent,'{'+NS+'}'+name,attrs or {})
        for field,value in values.items():ET.SubElement(node,'{'+NS+'}'+field).text=value
        return node
    pedido=group(root,'evento',{}, {'versao':'1.00'})
    info=group(pedido,'infEvento',{'cOrgao':'35','tpAmb':environment,'CNPJ':ISSUER,'chNFe':key,'dhEvento':'2026-09-16T10:00:00-03:00',
        'tpEvento':kind,'nSeqEvento':sequence,'verEvento':'1.00'},{'Id':'ID'+kind+key+sequence.zfill(2)})
    values={'descEvento':'Cancelamento','nProt':'1'*15,'xJust':text or 'Justificativa inteiramente sintética'} if kind=='110111' else {
        'descEvento':'Carta de Correcao','xCorrecao':text or 'Texto de correção inteiramente sintético','xCondUso':'Condições sintéticas preservadas sem validação legal'}
    group(info,'detEvento',values,{'versao':'1.00'})
    retorno=group(root,'retEvento',{}, {'versao':'1.00'})
    group(retorno,'infEvento',{'tpAmb':environment,'verAplic':'TESTE','cOrgao':'35','cStat':code,'xMotivo':'Resultado sintético informado',
        'chNFe':key,'tpEvento':kind,'xEvento':'Resultado sintético','nSeqEvento':sequence,'dhRegEvento':'2026-09-16T10:01:00-03:00','nProt':'2'*15})
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)


def document_xml():
    root=ET.fromstring(fake_xml());ide=root.find('.//{'+NS+'}ide');ET.SubElement(ide,'{'+NS+'}tpAmb').text='1'
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)


class EventReaderTests(unittest.TestCase):
    def test_cancellation_preserves_protocols_paths_and_declared_status_only(self):
        parsed=parse_nfe_event(event_xml(text='  Justificativa sintética com espaços  '))
        self.assertFalse(parsed['authorization_verified']);self.assertEqual(parsed['event_protocol'],'2'*15)
        self.assertEqual(parsed['fields']['procEventoNFe/evento/infEvento/detEvento/nProt']['value'],'1'*15)
        self.assertEqual(parsed['fields']['procEventoNFe/evento/infEvento/detEvento/xJust']['raw'],'  Justificativa sintética com espaços  ')
        self.assertEqual(parsed['reported_result'],'registro_vinculado_informado')
        for code,expected in [('136','registro_sem_vinculo_informado'),('573','outro_status_informado')]:
            self.assertEqual(parse_nfe_event(event_xml(code=code))['reported_result'],expected)

    def test_correction_is_free_text_not_replacement_and_nfce_is_unsupported(self):
        text='Onde consta valor 100.30 manter texto para conferência individual'
        parsed=parse_nfe_event(event_xml(kind='110110',sequence='2',text=text))
        self.assertEqual(parsed['text'],text);self.assertEqual(parsed['sequence'],2)
        key=fictitious_key(1,'2609');key=key[:20]+'65'+key[22:]
        self.assertTrue(parse_nfe_event(event_xml(kind='110110',key=key))['issues'])
        self.assertTrue(parse_nfe_event(event_xml(kind='110110',sequence='21'))['issues'])

    def test_mismatch_ambiguous_scalars_and_unsupported_roots_are_rejected(self):
        for mode in ('key','environment','id','duplicate','root','version','type','date','empty'):
            root=ET.fromstring(event_xml());info=root.find('.//{'+NS+'}infEvento');ret=root.find('.//{'+NS+'}retEvento/{'+NS+'}infEvento')
            if mode=='key':ret.find('{'+NS+'}chNFe').text=fictitious_key(2,'2609')
            if mode=='environment':ret.find('{'+NS+'}tpAmb').text='2'
            if mode=='id':info.set('Id','ID-invalido')
            if mode=='duplicate':info.append(copy.deepcopy(info.find('{'+NS+'}chNFe')))
            if mode=='root':root.tag='{'+NS+'}envEvento'
            if mode=='version':root.set('versao','9.99')
            if mode=='type':info.find('{'+NS+'}tpEvento').text='110112'
            if mode=='date':info.find('{'+NS+'}dhEvento').text='2026-09-16T10:00:00'
            if mode=='empty':info.find('{'+NS+'}detEvento/{'+NS+'}xJust').text='curto'
            with self.subTest(mode=mode):
                with self.assertRaises(ValueError):parse_nfe_event(ET.tostring(root))
        with self.assertRaises(ValueError):parse_nfe_event(b'<!DOCTYPE x [<!ENTITY y SYSTEM "file:///etc/passwd">]><x/>')
        with self.assertRaises(ValueError):parse_nfe_event(b'X'*(10*1024*1024+1))

    def test_incomplete_return_is_observed_but_blocks_keeping_flow(self):
        root=ET.fromstring(event_xml());ret=root.find('.//{'+NS+'}retEvento/{'+NS+'}infEvento')
        for name in ('chNFe','nProt','dhRegEvento'):ret.remove(ret.find('{'+NS+'}'+name))
        parsed=parse_nfe_event(ET.tostring(root));self.assertGreaterEqual(len(parsed['issues']),2)


class EventWorkflowTests(unittest.TestCase):
    setUp=fixtures.WorkApplicationTests.setUp
    save=fixtures.WorkApplicationTests.save
    post=fixtures.WorkApplicationTests.post
    opening=fixtures.WorkApplicationTests.opening

    def receive(self,content=None,key='event'):
        return self.s.receive_sources(self.c,[{'filename':'evento.xml','content':content or event_xml()}],key)['items'][0]

    def document(self):
        received=self.s.receive_sources(self.c,[{'filename':'documento.xml','content':document_xml()}],'document')['items'][0]
        organized=self.s.organize_source(self.c,received['input_id'],self.cycle['id'],received['snapshot_hash'],'Teste')
        return organized['evidence']['document_ids'][0]

    def operation(self):
        document=self.document();payload=self.s.prepare_work_operation(self.c,self.cycle['id'],document,policy_id=self.policy['id'])
        return self.save(payload)

    def review(self,source,decision='manter_fluxo',key='review',preview=None):
        preview=preview or self.s.nfe_event_preview(self.c,source['input_id'])
        return self.s.review_nfe_event(self.c,source['input_id'],preview['snapshot_hash'],decision,'Conferência sintética','Referência externa sintética',key,True)

    def test_receipt_and_search_before_document_do_not_open_cycles_or_post(self):
        self.s.db.execute('DELETE FROM work_cycles');self.s.db.commit()
        source=self.receive();self.assertEqual(source['evidence']['state'],'evento_pendente')
        preview=self.s.nfe_event_preview(self.c,source['input_id']);self.assertIsNone(preview['snapshot']['document'])
        self.assertEqual(self.s.nfe_event_queue(self.c)['total'],1)
        self.assertEqual(self.s.search_sources(self.c,query=fictitious_key(1,'2609'))['total'],1)
        self.assertEqual(self.s.source_original(self.c,source['input_id'])['content'],event_xml())
        with self.assertRaises(ValueError):self.review(source)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_cycles').fetchone()[0],0)

    def test_event_blocks_existing_review_but_review_decision_never_changes_payload_or_titles(self):
        op=self.operation();reviewed=self.s.review_work_operation(self.c,op['operation_id'],op['snapshot_hash'],'Teste')
        source=self.receive()
        with self.assertRaises(ValueError):self.s.post_work_operation(self.c,op['operation_id'],reviewed['snapshot_hash'],'Teste')
        before=self.s.get_work_operation(self.c,op['operation_id'])['payload']
        receipt=self.review(source)
        self.assertEqual(receipt['snapshot']['decision'],'manter_fluxo')
        after=self.s.get_work_operation(self.c,op['operation_id'])
        self.assertTrue(after['validation']['ready']);self.assertEqual(after['payload'],before)
        for table in ('work_movements','finance_titles'):self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)
        self.s.post_work_operation(self.c,op['operation_id'],after['snapshot_hash'],'Decisão explícita posterior')
        proof=self.s.nfe_event_posting_proof(self.c,op['operation_id'])
        self.assertEqual(proof['snapshot']['reviews'][0]['snapshot_hash'],receipt['snapshot_hash'])
        self.review(source,'suspender',key='later')
        self.assertEqual(self.s.nfe_event_posting_proof(self.c,op['operation_id']),proof)

    def test_free_correction_text_does_not_change_any_document_field(self):
        op=self.operation();source=self.receive(event_xml(kind='110110',text='Alterar descrição textual sem interpretação automática'))
        document=self.s._owned('documents',self.c,op['document_id']);before=dict(document)
        self.review(source)
        self.assertEqual(dict(self.s._owned('documents',self.c,op['document_id'])),before)
        self.assertEqual(self.s.get_work_operation(self.c,op['operation_id'])['payload'],op['payload'])

    def test_same_bytes_are_copies_and_new_conflicting_origin_invalidates_review(self):
        self.document();first=self.receive();self.review(first)
        self.receive(key='copy')
        context=self.s.nfe_event_preview(self.c,first['input_id'])['snapshot']
        self.assertEqual(context['duplicate_copies'],1);self.assertTrue(context['review_current']);self.assertFalse(context['blocking'])
        self.receive(event_xml(text='Justificativa divergente inteiramente sintética'),key='conflict')
        context=self.s.nfe_event_preview(self.c,first['input_id'])['snapshot']
        self.assertFalse(context['review_current']);self.assertTrue(context['blocking'])
        with self.assertRaises(ValueError):self.review(first,key='bad-conflict')

    def test_new_sequence_does_not_replace_previous_correction(self):
        doc=self.document();first=self.receive(event_xml(kind='110110'));self.review(first)
        second=self.receive(event_xml(kind='110110',sequence='2'),key='second')
        self.assertTrue(self.s.nfe_document_events(self.c,doc)['blocking'])
        self.review(second,key='second-review')
        self.assertFalse(self.s.nfe_document_events(self.c,doc)['blocking'])
        self.assertEqual(self.s.nfe_event_queue(self.c)['total'],2)

    def test_mismatch_environment_and_incomplete_returns_remain_blocked(self):
        self.document();source=self.receive(event_xml(environment='2'))
        with self.assertRaises(ValueError):self.review(source)
        root=ET.fromstring(event_xml());ret=root.find('.//{'+NS+'}retEvento/{'+NS+'}infEvento');ret.remove(ret.find('{'+NS+'}chNFe'))
        source=self.receive(ET.tostring(root),key='incomplete')
        with self.assertRaises(ValueError):self.review(source,key='incomplete-review')

    def test_nfce_cancellation_is_observed_and_reviewed_without_creating_movements(self):
        from test_fiscal_ledger import nfce
        from src.persistence import parse_nfe
        root=ET.fromstring(nfce());ET.SubElement(root.find('.//{'+NS+'}ide'),'{'+NS+'}tpAmb').text='1'
        content=ET.tostring(root);key=parse_nfe(content)['key']
        self.s.db.execute('UPDATE companies SET cnpj=? WHERE id=?',(ISSUER,self.c));self.s.db.commit()
        source=self.s.receive_sources(self.c,[{'filename':'nfce.xml','content':content}],'nfce')['items'][0]
        doc=self.s.organize_source(self.c,source['input_id'],self.cycle['id'],source['snapshot_hash'],'Teste')['evidence']['document_ids'][0]
        received=self.receive(event_xml(key=key));self.assertTrue(self.s.nfe_document_events(self.c,doc)['blocking'])
        self.review(received);self.assertFalse(self.s.nfe_document_events(self.c,doc)['blocking'])
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_movements').fetchone()[0],0)

    def test_discard_and_original_tampering_cannot_bypass_event_control(self):
        doc=self.document();source=self.receive()
        self.s.discard_source(self.c,source['input_id'],source['snapshot_hash'],'Retirada sintética')
        self.assertTrue(self.s.nfe_document_events(self.c,doc)['blocking'])
        self.s.db.execute('UPDATE source_inputs SET content=? WHERE id=?',(b'tamper',source['input_id']));self.s.db.commit()
        with self.assertRaises(ValueError):self.review(source)

    def test_closed_posted_books_remain_identical_after_receipt_and_annotation(self):
        self.opening();op=self.operation();self.post(op)
        self.s.db.execute("UPDATE work_cycles SET state='encerrada' WHERE id=?",(self.cycle['id'],));self.s.db.commit()
        before=self.s.work_books(self.c,self.cycle['id'])
        source=self.receive();self.review(source,'suspender')
        self.assertEqual(self.s.work_books(self.c,self.cycle['id']),before)
        self.assertEqual(self.s.get_work_operation(self.c,op['operation_id'])['payload'],op['payload'])
        self.assertEqual(self.s.nfe_event_history(self.c,source['input_id'])[0]['snapshot']['decision'],'suspender')

    def test_closure_preview_changes_and_fiscal_closure_is_blocked_by_event(self):
        self.opening();op=self.operation();self.post(op)
        before=self.s.module_period_overview(self.c,self.cycle['id'],'fiscal')
        self.receive()
        after=self.s.module_period_overview(self.c,self.cycle['id'],'fiscal')
        self.assertNotEqual(before['snapshot_hash'],after['snapshot_hash'])
        self.assertTrue(any('eventos' in b for b in after['blockers']))
        overview=self.s.work_overview(self.c,self.cycle['id'])
        with self.assertRaisesRegex(ValueError,'eventos'):self.s.transition_work_cycle(self.c,self.cycle['id'],'encerrada',overview['snapshot_hash'],'Teste',True)

    def test_confirmation_scope_staleness_and_known_retry(self):
        self.document();source=self.receive();preview=self.s.nfe_event_preview(self.c,source['input_id'])
        with self.assertRaises(ValueError):self.s.nfe_event_preview(self.other,source['input_id'])
        for confirmed in (False,1,'true'):
            with self.assertRaises(ValueError):self.s.review_nfe_event(self.c,source['input_id'],preview['snapshot_hash'],'manter_fluxo','Teste','Teste','bad',confirmed)
        first=self.review(source,preview=preview);again=self.review(source,preview=preview)
        self.assertTrue(again['duplicate']);self.assertEqual(first['snapshot'],again['snapshot'])
        with self.assertRaises(ValueError):self.review(source,'suspender',preview=preview)
        with self.assertRaisesRegex(ValueError,'alterada'):self.review(source,key='stale',preview=preview)

    def test_concurrent_known_retry_preserves_one_decision(self):
        self.document();source=self.receive();preview=self.s.nfe_event_preview(self.c,source['input_id'])
        def apply(_):
            with AccountingStore(self.path) as store:return store.review_nfe_event(self.c,source['input_id'],preview['snapshot_hash'],'manter_fluxo','Teste','Teste','race',True)
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(apply,range(2)))
        self.assertEqual(sorted(r['duplicate'] for r in results),[False,True]);self.assertEqual(results[0]['id'],results[1]['id'])

    def test_receipt_index_failure_rolls_back_everything(self):
        before=self.s.db.execute('SELECT COUNT(*) FROM source_receipts').fetchone()[0]
        with patch.object(self.s,'_index_nfe_event',side_effect=ValueError('Falha sintética')):
            with self.assertRaises(ValueError):self.receive()
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM source_receipts').fetchone()[0],before)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM nfe_event_observations').fetchone()[0],0)

    def test_posting_failure_rolls_back_event_proof_with_movements(self):
        op=self.operation();source=self.receive();self.review(source)
        self.s.review_work_operation(self.c,op['operation_id'],op['snapshot_hash'],'Teste')
        original=self.s._record_nfe_event_posting
        def fail(*args):
            original(*args)
            raise ValueError('Falha após vínculo de eventos')
        with patch.object(self.s,'_record_nfe_event_posting',side_effect=fail):
            with self.assertRaises(ValueError):self.s.post_work_operation(self.c,op['operation_id'],op['snapshot_hash'],'Teste')
        self.assertIsNone(self.s.nfe_event_posting_proof(self.c,op['operation_id']))
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_movements').fetchone()[0],0)
        self.assertEqual(self.s._work_revision(self.c,op['operation_id'])['state'],'revisado')

    def test_genuine_17_to_18_migration_preserves_postings_originals_and_closed_cycle(self):
        self.opening();op=self.operation();self.post(op)
        self.s.db.execute("UPDATE work_cycles SET state='encerrada' WHERE id=?",(self.cycle['id'],))
        before=self.s.work_books(self.c,self.cycle['id']);originals=[tuple(r) for r in self.s.db.execute('SELECT id,original,sha256 FROM files')]
        self.s.db.execute('DROP TABLE nfe_event_posting_proofs');self.s.db.execute('DROP TABLE nfe_event_reviews');self.s.db.execute('DROP TABLE nfe_event_observations');self.s.db.execute('UPDATE schema_version SET version=17');self.s.db.commit()
        with AccountingStore(self.path) as store:
            self.assertEqual(store.db.execute('SELECT version FROM schema_version').fetchone()[0],18)
            self.assertEqual(store.work_books(self.c,self.cycle['id']),before)
            self.assertEqual([tuple(r) for r in store.db.execute('SELECT id,original,sha256 FROM files')],originals)
            self.assertEqual(store._work_cycle(self.c,self.cycle['id'])['state'],'encerrada')
            self.assertEqual(store.nfe_event_queue(self.c)['total'],0)
            self.assertEqual(store.db.execute('PRAGMA foreign_key_check').fetchall(),[])


if __name__=='__main__':unittest.main()
