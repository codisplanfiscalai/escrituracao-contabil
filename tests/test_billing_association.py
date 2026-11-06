"""Explicit fictitious XML billing associations, never inferred new titles."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import sqlite3
import threading
import unittest
from unittest.mock import patch

import test_accounting
from test_persistence import fake_xml, edit_xml
from src.persistence import AccountingStore


class BillingAssociationTests(unittest.TestCase):
    setUp = test_accounting.AccountingTests.setUp
    decision = test_accounting.AccountingTests.decision
    lines = test_accounting.AccountingTests.lines
    batch = test_accounting.AccountingTests.batch
    close = test_accounting.AccountingTests.close

    def ambiguous_source(self,content=None):
        if content is None:
            content=edit_xml(fake_xml(),'cobr/fat/nFat','TITULO-ALTERNATIVO-FICTICIO')
            content=edit_xml(content,'cobr/dup/nDup','PARCELA-ALTERNATIVA-FICTICIA')
        return self.s.import_file(self.c,self.p,'associacao-ficticia.xml',content,'XML')['id']

    def proposal(self,file_id):
        invoice=self.s.db.execute('SELECT id FROM invoices WHERE document_id=?',(self.doc,)).fetchone()[0]
        source=[row for row in self.s.list_observations(self.c) if row['file_id']==file_id and row['entity_kind']=='parcela']
        targets=[row[0] for row in self.s.db.execute('SELECT id FROM installments WHERE invoice_id=? ORDER BY id',(invoice,))]
        return dict(company_id=self.c,document_id=self.doc,period_id=self.p,file_id=file_id,invoice_id=invoice,
                    installment_links=[dict(observation_id=row['id'],installment_id=target) for row,target in zip(source,targets)])

    def save(self,proposal,preview=None):
        preview=preview or self.s.preview_billing_association(**proposal)
        return self.s.save_billing_association(**proposal,expected_fingerprint=preview['expected_fingerprint'],reason='Conferência fictícia dos mesmos valores e vencimentos',confirmed=True)

    def originals(self):
        return {table:[tuple(row) for row in self.s.db.execute('SELECT * FROM '+table+' ORDER BY id')] for table in ('files','documents','invoices','installments','source_observations')}

    def test_complete_invoice_and_installments_association_preserves_originals_and_issues(self):
        file=self.ambiguous_source();proposal=self.proposal(file);before=self.originals()
        preview=self.s.preview_billing_association(**proposal)
        self.assertEqual(len(preview['installments']),2)
        self.assertIsNone(preview['invoice']['source']['invoice_id'])
        self.assertEqual(preview['invoice']['target']['id'],proposal['invoice_id'])
        decision=self.save(proposal,preview)
        self.assertTrue(decision['valid']);self.assertTrue(decision['current'])
        self.assertEqual(decision['version'],1)
        self.assertEqual(self.originals(),before)
        reconciliation=self.s.list_reconciliation(self.c)[0]
        associated=[row for row in reconciliation['sources'] if row['file_id']==file and row['entity_kind'] in ('fatura','parcela')]
        self.assertTrue(all(row.get('billing_resolution') for row in associated))
        self.assertTrue(all(row['invoice_id'] is None for row in associated))
        self.assertTrue(all(row['issues'] for row in associated))
        self.assertTrue(all(row['resolved_messages'] for row in reconciliation['issues']))
        self.assertTrue(any(row.get('entity')=='fatura' and row['field']=='nFat' for row in reconciliation['differences']))
        self.assertEqual(len(reconciliation['invoices'][0]['sources']),2)
        self.assertFalse(reconciliation['ready_for_export'])
        self.assertFalse(reconciliation['readiness_for_accounting'])
        self.assertTrue(self.decision()['readiness_for_accounting'])
        batch=self.close(self.batch())
        self.assertEqual(batch['snapshot']['documents'][0]['snapshot']['billing_associations'][0]['id'],decision['id'])

    def test_installment_identifier_only_keeps_known_links_and_resolves_missing_one(self):
        file=self.ambiguous_source(edit_xml(fake_xml(),'cobr/dup/nDup','003'))
        proposal=self.proposal(file);self.save(proposal)
        result=self.s.list_reconciliation(self.c)[0]
        source=[row for row in result['sources'] if row['file_id']==file and row['entity_kind']=='parcela']
        self.assertIsNone(source[0]['installment_id']);self.assertIsNotNone(source[1]['installment_id'])
        self.assertTrue(self.decision()['readiness_for_accounting'])

    def test_identity_unchanged_requires_no_association(self):
        with self.assertRaisesRegex(ValueError,'nenhum identificador'):self.s.preview_billing_association(**self.proposal(self.file))

    def test_confirmation_reason_and_preview_fingerprint_are_required(self):
        proposal=self.proposal(self.ambiguous_source());preview=self.s.preview_billing_association(**proposal)
        for change in ({'confirmed':False},{'confirmed':'true'},{'reason':''},{'expected_fingerprint':'old'}):
            data=dict(**proposal,expected_fingerprint=preview['expected_fingerprint'],reason='Fictício',confirmed=True)
            data.update(change)
            with self.assertRaises(ValueError):self.s.save_billing_association(**data)
        self.assertEqual(self.s.list_billing_associations(self.c),[])

    def test_one_to_one_complete_coverage_and_exact_amount_date_are_enforced(self):
        proposal=self.proposal(self.ambiguous_source())
        for links in ([],proposal['installment_links'][:1],proposal['installment_links']*2,
                      [proposal['installment_links'][0],proposal['installment_links'][0]],
                      [dict(observation_id=link['observation_id'],installment_id=proposal['installment_links'][0]['installment_id']) for link in proposal['installment_links']],
                      [dict(observation_id=link['observation_id'],installment_id=other['installment_id']) for link,other in zip(proposal['installment_links'],reversed(proposal['installment_links']))]):
            with self.subTest(links=links):
                with self.assertRaises(ValueError):self.s.preview_billing_association(**{**proposal,'installment_links':links})
        self.assertEqual(self.s.list_billing_associations(self.c),[])

    def test_altered_values_due_dates_and_internal_arithmetic_remain_blocked(self):
        base=edit_xml(fake_xml(),'cobr/fat/nFat','TITULO-DIVERGENTE-FICTICIO')
        variants=[edit_xml(base,'cobr/fat/vDesc','0.01'),edit_xml(base,'cobr/dup/vDup','40.11'),edit_xml(base,'cobr/dup/dVenc','2026-10-16')]
        # Balanced but different canonical values still cannot be associated.
        changed=edit_xml(base,'cobr/fat/vOrig','101.30');changed=edit_xml(changed,'cobr/fat/vLiq','101.30');changed=edit_xml(changed,'cobr/dup/vDup','41.10');variants.append(changed)
        for content in variants:
            proposal=self.proposal(self.ambiguous_source(content))
            with self.assertRaises(ValueError):self.s.preview_billing_association(**proposal)
        self.assertFalse(self.decision()['readiness_for_accounting'])

    def test_missing_and_duplicate_identifiers_do_not_get_fabricated(self):
        base=edit_xml(fake_xml(),'cobr/fat/nFat','TITULO-FICTICIO-NOVO')
        for content in (edit_xml(fake_xml(),'cobr/fat/nFat',remove=True),edit_xml(base,'cobr/dup/nDup',remove=True),edit_xml(base,'cobr/dup/nDup','002')):
            proposal=self.proposal(self.ambiguous_source(content))
            with self.assertRaises(ValueError):self.s.preview_billing_association(**proposal)
        self.assertEqual(self.s.list_billing_associations(self.c),[])
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM invoices').fetchone()[0],1)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM installments').fetchone()[0],2)

    def test_company_document_period_and_observation_scope_are_isolated(self):
        proposal=self.proposal(self.ambiguous_source())
        other=self.s.create_company('Outra fictícia','O','O')['id']
        period=self.s.create_period(self.c,'2026-07','2026-09')['id']
        self.s.import_file(self.c,self.p,'outro-doc.xml',fake_xml(number=2),'XML')
        other_doc=next(row for row in self.s.list_documents(self.c) if row['id']!=self.doc)['id']
        other_invoice=self.s.db.execute('SELECT id FROM invoices WHERE document_id=?',(other_doc,)).fetchone()[0]
        for change in ({'company_id':other},{'period_id':period},{'document_id':other_doc},{'invoice_id':other_invoice},
                       {'installment_links':[{'observation_id':99999,'installment_id':link['installment_id']} for link in proposal['installment_links']]}):
            with self.assertRaises(ValueError):self.s.preview_billing_association(**{**proposal,**change})
        self.assertEqual(self.s.list_billing_associations(other),[])
        with self.assertRaises(ValueError):self.s.list_billing_associations(other,self.doc)

    def test_excluded_source_and_no_active_canonical_evidence_are_refused(self):
        file=self.ambiguous_source();proposal=self.proposal(file)
        preview=self.s.deletion_preview(self.c,self.file)
        self.s.delete_file(self.c,self.file,'Remoção fictícia',True,preview['preview_token'])
        with self.assertRaisesRegex(ValueError,'evidência XML ativa'):self.s.preview_billing_association(**proposal)
        preview=self.s.deletion_preview(self.c,file)
        self.s.delete_file(self.c,file,'Remoção fictícia',True,preview['preview_token'])
        with self.assertRaisesRegex(ValueError,'fonte XML ativa'):self.s.preview_billing_association(**proposal)

    def test_new_source_and_deletion_expire_decision_and_require_new_preview(self):
        file=self.ambiguous_source();proposal=self.proposal(file);preview=self.s.preview_billing_association(**proposal)
        first=self.save(proposal,preview);self.decision();batch=self.batch()
        extra=self.s.import_file(self.c,self.p,'extra-ficticio.xml',fake_xml(wrapper=False),'XML')['id']
        self.assertFalse(self.s.list_billing_associations(self.c)[0]['valid'])
        with self.assertRaisesRegex(ValueError,'desatualizada'):self.save(proposal,preview)
        self.assertFalse(self.s.list_reconciliation(self.c)[0]['review']['valid'])
        with self.assertRaises(ValueError):self.s.review_accounting_batch(self.c,batch['id'],batch['snapshot_hash'],'Teste')
        current=self.save(proposal)
        self.assertEqual(current['version'],2)
        self.assertFalse(self.s.list_billing_associations(self.c)[1]['current'])
        deletion=self.s.deletion_preview(self.c,extra)
        self.s.delete_file(self.c,extra,'Remoção fictícia',True,deletion['preview_token'])
        self.assertFalse(self.s.list_billing_associations(self.c)[0]['valid'])
        self.assertEqual(self.s._batch(self.c,batch['id'])['snapshot'],batch['snapshot'])
        self.assertEqual(self.s.list_billing_associations(self.c)[1]['snapshot'],first['snapshot'])

    def test_new_decision_version_invalidates_document_review_without_source_change(self):
        proposal=self.proposal(self.ambiguous_source());first=self.save(proposal);self.decision();batch=self.batch()
        second=self.save(proposal)
        self.assertEqual(second['source_fingerprint'],first['source_fingerprint'])
        self.assertEqual(second['version'],2)
        self.assertFalse(self.s.list_reconciliation(self.c)[0]['review']['valid'])
        with self.assertRaises(ValueError):self.s.review_accounting_batch(self.c,batch['id'],batch['snapshot_hash'],'Teste')
        self.assertTrue(self.decision()['readiness_for_accounting'])

    def test_multiple_files_decisions_remain_applicable_with_same_raw_source_set(self):
        proposal_a=self.proposal(self.ambiguous_source())
        proposal_b=self.proposal(self.ambiguous_source(edit_xml(fake_xml(),'cobr/fat/nFat','OUTRO-IDENTIFICADOR-FICTICIO')))
        self.save(proposal_a);self.save(proposal_b)
        self.assertTrue(all(row['valid'] for row in self.s.list_billing_associations(self.c)))
        self.assertTrue(self.decision()['readiness_for_accounting'])

    def test_atomic_rollback_and_concurrent_confirmation(self):
        proposal=self.proposal(self.ambiguous_source());preview=self.s.preview_billing_association(**proposal)
        with patch.object(self.s,'_audit',side_effect=RuntimeError('Falha fictícia')):
            with self.assertRaises(RuntimeError):self.save(proposal,preview)
        self.assertEqual(self.s.list_billing_associations(self.c),[])
        barrier=threading.Barrier(2)
        def attempt(_):
            with AccountingStore(self.path) as store:
                barrier.wait()
                try:
                    return store.save_billing_association(**proposal,expected_fingerprint=preview['expected_fingerprint'],reason='Teste fictício',confirmed=True)['id']
                except ValueError as exc:
                    self.assertIn('desatualizada',str(exc));return None
        with ThreadPoolExecutor(max_workers=2) as executor:results=list(executor.map(attempt,range(2)))
        self.assertEqual(sum(result is not None for result in results),1)
        self.assertEqual(len(self.s.list_billing_associations(self.c)),1)

    def test_closed_snapshot_and_export_bytes_survive_later_billing_decisions(self):
        self.decision();closed=self.close(self.batch())
        export=self.s.create_evidence_export(self.c,closed['id'],closed['snapshot_hash'],'Evidência fictícia')
        before={row['name']:self.s.read_evidence_artifact(self.c,export['id'],row['name'])['content'] for row in export['artifacts']}
        self.save(self.proposal(self.ambiguous_source()))
        self.assertEqual(self.s._batch(self.c,closed['id']),closed)
        self.assertEqual(self.s.create_evidence_export(self.c,closed['id'],closed['snapshot_hash'],'Repetição fictícia')['manifest_sha256'],export['manifest_sha256'])
        for name,content in before.items():self.assertEqual(self.s.read_evidence_artifact(self.c,export['id'],name)['content'],content)
        self.assertTrue(self.s.list_accounting_batches(self.c)[0]['current_blockers'])
        self.s.close();self.s=AccountingStore(self.path)
        self.assertEqual(len(self.s.list_billing_associations(self.c)),1)
        self.assertEqual(self.s._batch(self.c,closed['id']),closed)

    def test_preview_binds_the_exact_mapping_even_when_values_and_due_dates_tie(self):
        import xml.etree.ElementTree as ET
        from test_persistence import NS
        root=ET.fromstring(fake_xml(number=2))
        for part in root.findall(f'.//{{{NS}}}dup'):
            part.find(f'{{{NS}}}vDup').text='50.15'
            part.find(f'{{{NS}}}dVenc').text='2026-10-15'
        canonical=ET.tostring(root)
        self.s.import_file(self.c,self.p,'iguais-ficticio.xml',canonical,'XML')
        self.doc=next(row['id'] for row in self.s.list_documents(self.c) if row['id']!=self.doc)
        alternate=edit_xml(canonical,'cobr/fat/nFat','OUTRO-TITULO-FICTICIO')
        proposal=self.proposal(self.ambiguous_source(alternate))
        original_preview=self.s.preview_billing_association(**proposal)
        links=proposal['installment_links']
        swapped={**proposal,'installment_links':[dict(observation_id=left['observation_id'],installment_id=right['installment_id']) for left,right in zip(links,reversed(links))]}
        alternate_preview=self.s.preview_billing_association(**swapped)
        self.assertNotEqual(original_preview['expected_fingerprint'],alternate_preview['expected_fingerprint'])
        with self.assertRaisesRegex(ValueError,'desatualizada'):self.save(swapped,original_preview)
        self.assertTrue(self.save(swapped,alternate_preview)['valid'])
        # Native links cannot be overridden even when monetary evidence ties.
        installment_only=self.proposal(self.ambiguous_source(edit_xml(canonical,'cobr/dup/nDup','OUTRA-PARCELA-FICTICIA')))
        links=installment_only['installment_links']
        installment_only['installment_links']=[dict(observation_id=left['observation_id'],installment_id=right['installment_id']) for left,right in zip(links,reversed(links))]
        with self.assertRaisesRegex(ValueError,'vínculo de parcela existente'):
            self.s.preview_billing_association(**installment_only)

    def test_associated_snapshot_and_resolution_survive_reopen_and_export(self):
        proposal=self.proposal(self.ambiguous_source());association=self.save(proposal);self.decision();closed=self.close(self.batch())
        export=self.s.create_evidence_export(self.c,closed['id'],closed['snapshot_hash'],'Evidência fictícia')
        content=self.s.read_evidence_artifact(self.c,export['id'],'evidence.json')['content']
        self.s.close();self.s=AccountingStore(self.path)
        self.assertTrue(self.s.list_billing_associations(self.c)[0]['valid'])
        self.assertTrue(self.s.list_reconciliation(self.c)[0]['readiness_for_accounting'])
        self.assertEqual(self.s._batch(self.c,closed['id']),closed)
        self.assertEqual(self.s.read_evidence_artifact(self.c,export['id'],'evidence.json')['content'],content)
        import json
        evidence=json.loads(content)
        self.assertEqual(evidence['snapshot']['documents'][0]['snapshot']['billing_associations'][0]['id'],association['id'])

    def test_schema4_migration_preserves_originals_reviews_and_closed_evidence(self):
        self.decision();closed=self.close(self.batch());export=self.s.create_evidence_export(self.c,closed['id'],closed['snapshot_hash'],'Fictício')
        before=self.originals();review=self.s.list_document_reviews(self.c)[0]
        with self.s.db:
            self.s.db.execute('DROP TABLE billing_associations')
            self.s.db.execute('UPDATE schema_version SET version=4')
        self.s.close()
        with patch('src.persistence.BILLING_ASSOCIATION_SCHEMA','CREATE TABLE failed_billing(id INTEGER); INVALID SQL;'):
            with self.assertRaises(sqlite3.OperationalError):AccountingStore(self.path)
        with closing(sqlite3.connect(self.path)) as db,db:
            self.assertEqual(db.execute('SELECT version FROM schema_version').fetchone()[0],4)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='failed_billing'").fetchone())
        self.s=AccountingStore(self.path)
        self.assertEqual(self.s.db.execute('SELECT version FROM schema_version').fetchone()[0],17)
        self.assertEqual(self.originals(),before)
        self.assertEqual(self.s.list_document_reviews(self.c)[0],review)
        self.assertEqual(self.s._batch(self.c,closed['id']),closed)
        self.assertEqual(self.s.create_evidence_export(self.c,closed['id'],closed['snapshot_hash'],'Fictício')['manifest_sha256'],export['manifest_sha256'])
