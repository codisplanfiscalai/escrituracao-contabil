"""Fictitious evidence exports; no external accounting format or real data."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import csv
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import threading
import unittest
from unittest.mock import patch

import test_accounting
from test_persistence import fake_xml
from src.accounting_store import digest, dump
from src.evidence_export import PROFILE, CSV_TEXT_COLUMNS, build_artifacts
from src.persistence import AccountingStore


class EvidenceExportTests(unittest.TestCase):
    setUp = test_accounting.AccountingTests.setUp
    decision = test_accounting.AccountingTests.decision
    lines = test_accounting.AccountingTests.lines
    batch = test_accounting.AccountingTests.batch
    close = test_accounting.AccountingTests.close

    def closed(self):
        self.decision()
        return self.close(self.batch())

    def export(self, batch):
        return self.s.create_evidence_export(self.c,batch['id'],batch['snapshot_hash'],'Evidência fictícia para auditoria local')

    def read_all(self, export):
        return {row['name']:self.s.read_evidence_artifact(self.c,export['id'],row['name'])['content'] for row in export['artifacts']}

    def test_manifest_hashes_snapshot_lineage_totals_and_own_profile(self):
        batch=self.closed();export=self.export(batch);files=self.read_all(export)
        self.assertEqual(export['profile'],PROFILE)
        self.assertFalse(export['duplicate'])
        self.assertEqual(set(files),{'manifest.json','evidence.json','postings.csv'})
        manifest=json.loads(files['manifest.json']);evidence=json.loads(files['evidence.json'])
        self.assertEqual(hashlib.sha256(files['manifest.json']).hexdigest(),export['manifest_sha256'])
        for artifact in export['artifacts']:
            content=files[artifact['name']]
            self.assertEqual(artifact['sha256'],hashlib.sha256(content).hexdigest())
            self.assertEqual(artifact['size'],len(content))
        for artifact in manifest['artifacts']:
            self.assertEqual(artifact['sha256'],hashlib.sha256(files[artifact['name']]).hexdigest())
        self.assertFalse(manifest['prosoft_compatible']);self.assertFalse(manifest['efd_compatible'])
        self.assertFalse(evidence['externally_posted'])
        self.assertEqual(evidence['snapshot'],batch['snapshot'])
        self.assertEqual(digest(evidence['snapshot']),batch['snapshot_hash'])
        self.assertEqual(evidence['closure_audit']['details']['batch_id'],batch['id'])
        self.assertEqual(evidence['batch']['review_actor'],'operador-ficticio')
        self.assertEqual(manifest['line_count'],2)
        self.assertEqual(manifest['totals'],{'debit':'100.30','credit':'100.30'})
        self.assertTrue(files['evidence.json'].endswith(b'\n'))
        self.assertTrue(files['postings.csv'].startswith(b'\xef\xbb\xbf'))
        lines=list(csv.DictReader(io.StringIO(files['postings.csv'].decode('utf-8-sig'),newline='')))
        self.assertEqual([row['side'] for row in lines],['D','C'])
        self.assertEqual(lines[0]['source_file_id'],str(self.file))
        self.assertEqual(lines[0]['document_review_id'],str(batch['snapshot']['documents'][0]['id']))
        self.assertEqual(lines[0]['mapping_id'],str(self.maps[0]))
        self.assertEqual(lines[0]['amount'],'100.30')
        self.assertEqual(lines[0]['document_business_key'][1:],batch['snapshot']['documents'][0]['snapshot']['business_key'])

    def test_preview_and_reviewed_without_close_are_refused(self):
        self.decision();batch=self.batch()
        with self.assertRaisesRegex(ValueError,'fechado'):self.export(batch)
        self.s.review_accounting_batch(self.c,batch['id'],batch['snapshot_hash'],'Revisão fictícia')
        with self.assertRaisesRegex(ValueError,'fechado'):self.export(batch)
        self.assertEqual(self.s.list_evidence_exports(self.c),[])

    def test_missing_review_or_closure_audit_is_refused(self):
        batch=self.closed()
        with self.s.db:self.s.db.execute('UPDATE accounting_batches SET reviewed_at=NULL WHERE id=?',(batch['id'],))
        with self.assertRaisesRegex(ValueError,'revisão'):self.export(batch)
        with self.s.db:
            self.s.db.execute('UPDATE accounting_batches SET reviewed_at=? WHERE id=?',(batch['reviewed_at'],batch['id']))
            self.s.db.execute("DELETE FROM audit WHERE action='lote_contabil_fechado'")
        with self.assertRaisesRegex(ValueError,'evento auditado'):self.export(batch)
        self.assertEqual(self.s.list_evidence_exports(self.c),[])

    def test_foreign_company_batch_export_and_file_are_isolated(self):
        batch=self.closed();export=self.export(batch)
        other=self.s.create_company('Outra fictícia','O','O')['id']
        self.assertEqual(self.s.list_evidence_exports(other),[])
        for action in (
            lambda:self.s.create_evidence_export(other,batch['id'],batch['snapshot_hash'],'Teste fictício'),
            lambda:self.s.list_evidence_exports(other,batch['id']),
            lambda:self.s.read_evidence_artifact(other,export['id'],'evidence.json')):
            with self.assertRaisesRegex(ValueError,'empresa'):action()

    def test_hash_confirmation_and_reason_required(self):
        batch=self.closed()
        with self.assertRaisesRegex(ValueError,'hash informado'):
            self.s.create_evidence_export(self.c,batch['id'],'stale','Teste fictício')
        with self.assertRaises(ValueError):self.s.create_evidence_export(self.c,batch['id'],batch['snapshot_hash'],'')
        self.assertEqual(self.s.list_evidence_exports(self.c),[])

    def test_repeat_and_reopen_preserve_bytes_and_record_each_attempt(self):
        batch=self.closed();first=self.export(batch);original=self.read_all(first)
        self.s.close();self.s=AccountingStore(self.path,actor='outro-operador-ficticio')
        repeated=self.export(batch)
        self.assertEqual(repeated['id'],first['id']);self.assertTrue(repeated['duplicate'])
        self.assertEqual(repeated['created_at'],first['created_at'])
        self.assertEqual(original,self.read_all(repeated))
        self.assertEqual(len(self.s.list_evidence_exports(self.c,batch['id'])),1)
        actions=[row['action'] for row in self.s.list_audit(self.c)]
        self.assertEqual(actions.count('evidencia_contabil_criada'),1)
        self.assertEqual(actions.count('evidencia_contabil_repetida'),1)
        self.assertEqual(actions.count('evidencia_contabil_disponibilizada'),6)
        self.assertEqual(self.s.list_audit(self.c)[0]['actor'],'outro-operador-ficticio')

    def test_new_sources_mappings_reviews_and_correction_preserve_historical_evidence(self):
        batch=self.closed();first=self.export(batch);original=self.read_all(first)
        self.s.import_file(self.c,self.p,'nova-ficticia.xml',fake_xml(wrapper=False),'XML')
        self.decision()
        new=self.s.save_mapping(self.c,self.plan,'origem-0','1.1.1','2026-09',state='aprovado',reason='Nova versão fictícia')['id']
        lines=self.lines();lines[0]['mapping_id']=new
        correction=self.batch('correcao-ficticia',lines,batch['id'])
        self.assertTrue(self.s.list_accounting_batches(self.c)[1]['current_blockers'])
        self.assertEqual(self.read_all(self.export(batch)),original)
        with self.assertRaisesRegex(ValueError,'fechado'):self.export(correction)
        self.assertEqual(self.s._batch(self.c,batch['id']),batch)

    def test_first_export_after_sources_change_still_uses_the_closed_snapshot(self):
        batch=self.closed()
        closure=next(row for row in self.s.list_audit(self.c) if row['action']=='lote_contabil_fechado')
        expected=build_artifacts(batch,closure)
        self.s.import_file(self.c,self.p,'nova-ficticia.xml',fake_xml(wrapper=False),'XML')
        self.decision()
        self.s.save_mapping(self.c,self.plan,'origem-0','1.1.1','2026-09',state='inativo',reason='Inativado fictício')
        self.assertEqual(self.read_all(self.export(batch)),expected)

    def test_concurrent_exports_share_one_persisted_set(self):
        batch=self.closed();barrier=threading.Barrier(2)
        def export(_):
            with AccountingStore(self.path) as store:
                barrier.wait()
                return store.create_evidence_export(self.c,batch['id'],batch['snapshot_hash'],'Teste fictício')
        with ThreadPoolExecutor(max_workers=2) as executor:
            result=list(executor.map(export,range(2)))
        self.assertEqual(result[0]['id'],result[1]['id'])
        self.assertEqual(sorted(row['duplicate'] for row in result),[False,True])
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM accounting_evidence_artifacts').fetchone()[0],3)

    def test_csv_does_not_execute_formulas_and_json_preserves_original_text(self):
        self.decision();lines=self.lines()
        lines[0]['memo']='=HYPERLINK("https://example.invalid","fictício")'
        lines[1]['memo']="'texto com apóstrofo, vírgula e ç"
        for line in lines:line['group']='+grupo fictício'
        batch=self.close(self.batch(entries=lines));files=self.read_all(self.export(batch))
        rows=list(csv.DictReader(io.StringIO(files['postings.csv'].decode('utf-8-sig'),newline='')))
        for row in rows:
            for column in CSV_TEXT_COLUMNS:self.assertTrue(row[column].startswith("'"),column)
        self.assertEqual(rows[0]['memo'][1:],lines[0]['memo'])
        self.assertEqual(rows[1]['memo'][1:],lines[1]['memo'])
        self.assertEqual(json.loads(files['evidence.json'])['snapshot']['entries'][0]['memo'],lines[0]['memo'])

    def test_corrupt_snapshot_hash_and_internal_lineage_are_refused(self):
        batch=self.closed()
        with self.s.db:self.s.db.execute("UPDATE accounting_batches SET snapshot_hash='bad' WHERE id=?",(batch['id'],))
        with self.assertRaisesRegex(ValueError,'hash do snapshot'):
            self.s.create_evidence_export(self.c,batch['id'],'bad','Teste fictício')
        snapshot=batch['snapshot'];snapshot['entries'][0]['observation_id']=999999
        with self.s.db:self.s.db.execute('UPDATE accounting_batches SET snapshot=?,snapshot_hash=? WHERE id=?',(dump(snapshot),digest(snapshot),batch['id']))
        with self.assertRaisesRegex(ValueError,'rastreabilidade'):
            self.s.create_evidence_export(self.c,batch['id'],digest(snapshot),'Teste fictício')

    def test_independent_total_validation_rejects_rehashed_inconsistent_snapshot(self):
        batch=self.closed();snapshot=batch['snapshot'];snapshot['totals']['debit']='999.00'
        with self.s.db:self.s.db.execute('UPDATE accounting_batches SET snapshot=?,snapshot_hash=? WHERE id=?',(dump(snapshot),digest(snapshot),batch['id']))
        with self.assertRaisesRegex(ValueError,'totalizadores'):
            self.s.create_evidence_export(self.c,batch['id'],digest(snapshot),'Teste fictício')
        self.assertEqual(self.s.list_evidence_exports(self.c),[])

    def test_corrupt_or_missing_artifact_stops_delivery_and_repeat(self):
        batch=self.closed();export=self.export(batch)
        with self.s.db:self.s.db.execute("UPDATE accounting_evidence_artifacts SET content=? WHERE export_id=? AND name='postings.csv'",(b'corrompido',export['id']))
        with self.assertRaisesRegex(ValueError,'hash/tamanho'):self.s.read_evidence_artifact(self.c,export['id'],'evidence.json')
        with self.assertRaisesRegex(ValueError,'hash/tamanho'):self.export(batch)
        with self.s.db:self.s.db.execute("DELETE FROM accounting_evidence_artifacts WHERE export_id=? AND name='postings.csv'",(export['id'],))
        with self.assertRaisesRegex(ValueError,'incompleto'):self.s.read_evidence_artifact(self.c,export['id'],'manifest.json')

    def test_invalid_artifact_names_and_audit_failure_have_no_delivery_or_partial_effect(self):
        batch=self.closed()
        with patch.object(self.s,'_audit',side_effect=RuntimeError('Falha fictícia')):
            with self.assertRaises(RuntimeError):self.export(batch)
        self.assertEqual(self.s.list_evidence_exports(self.c),[])
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM accounting_evidence_artifacts').fetchone()[0],0)
        export=self.export(batch);audit_count=len(self.s.list_audit(self.c))
        for name in ('../evidence.json','/evidence.json','postings.csv/','prosoft.txt',None,[]):
            with self.assertRaises(ValueError):self.s.read_evidence_artifact(self.c,export['id'],name)
        with patch.object(self.s,'_audit',side_effect=RuntimeError('Falha fictícia')):
            with self.assertRaises(RuntimeError):self.s.read_evidence_artifact(self.c,export['id'],'evidence.json')
            with self.assertRaises(RuntimeError):self.export(batch)
        self.assertEqual(len(self.s.list_audit(self.c)),audit_count)
        self.assertFalse(self.s.list_accounting_batches(self.c)[0]['ready_for_export'])

    def test_schema3_migration_preserves_closed_snapshot_and_rollback(self):
        batch=self.closed();before=self.s.db.execute('SELECT snapshot FROM accounting_batches').fetchone()[0]
        original=bytes(self.s.db.execute('SELECT original FROM files').fetchone()[0])
        # Reconstruct a v3 database by dropping only the newly added empty tables.
        with self.s.db:
            self.s.db.execute('DROP TABLE accounting_evidence_artifacts')
            self.s.db.execute('DROP TABLE accounting_evidence_exports')
            self.s.db.execute('UPDATE schema_version SET version=3')
        self.s.close()
        with patch('src.persistence.EVIDENCE_SCHEMA','CREATE TABLE failed_evidence(id INTEGER); INVALID SQL;'):
            with self.assertRaises(sqlite3.OperationalError):AccountingStore(self.path)
        with closing(sqlite3.connect(self.path)) as db, db:
            self.assertEqual(db.execute('SELECT version FROM schema_version').fetchone()[0],3)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='failed_evidence'").fetchone())
            self.assertEqual(db.execute('SELECT snapshot FROM accounting_batches').fetchone()[0],before)
        self.s=AccountingStore(self.path)
        self.assertEqual(self.s.db.execute('SELECT version FROM schema_version').fetchone()[0],13)
        self.assertEqual(self.s.db.execute('SELECT snapshot FROM accounting_batches').fetchone()[0],before)
        self.assertEqual(bytes(self.s.db.execute('SELECT original FROM files').fetchone()[0]),original)
        self.assertEqual(self.s._batch(self.c,batch['id']),batch)
        self.export(batch)
