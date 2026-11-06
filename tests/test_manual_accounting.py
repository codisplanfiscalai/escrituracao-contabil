"""Cenários inteiramente sintéticos: nenhuma escrita em sistema contábil externo."""
from concurrent.futures import ThreadPoolExecutor
import csv
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from src.persistence import AccountingStore
from test_persistence import fake_accounts, ISSUER


class ManualAccountingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'ficticio.sqlite3'
        self.s = AccountingStore(self.path,actor='operador-ficticio'); self.addCleanup(lambda:self.s.close())
        self.c = self.s.create_company('Empresa fictícia','TESTE','TESTE',ISSUER)['id']
        self.other = self.s.create_company('Outra empresa fictícia','OUTRA','OUTRA')['id']
        self.p = self.s.create_period(self.c,'2026-08','2026-09')['id']
        self.plan = self.s.import_plan(self.c,'Plano fictício',fake_accounts())['id']
        self.accounts = {row['code']:row['id'] for row in self.s.list_accounts(self.c,self.plan)}

    def lines(self, value='100.30'):
        return [dict(date='2026-09-15',group='ficticio',side=side,amount=value,account_id=self.accounts[code],memo='Histórico fictício')
                for side,code in (('D','1.1.1'),('C','2.1'))]

    def save(self,key='tentativa-1',lines=None,journal_id=None,version=0):
        return self.s.save_manual_journal(self.c,self.p,self.plan,self.lines() if lines is None else lines,
            'Referência fictícia','Conferência fictícia',key,journal_id,version)

    def close(self,revision):
        for target in ('revisado','fechado'):
            revision = self.s.transition_manual_journal(self.c,revision['journal_id'],revision['snapshot_hash'],'Conferência fictícia',target)
        return revision

    def books(self):
        return self.s.accounting_books(self.c,self.p,self.plan)

    def test_manual_without_document_or_mapping_and_reopen(self):
        revision = self.save()
        self.assertEqual(revision['snapshot']['totals'],{'debit':'100.30','credit':'100.30'})
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM documents').fetchone()[0],0)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM mappings').fetchone()[0],0)
        self.assertEqual(self.books()['diary'],[])
        closed = self.close(revision)
        with AccountingStore(self.path) as reopened:
            self.assertEqual(reopened.list_manual_journals(self.c)[0],closed)
            self.assertEqual(len(reopened.accounting_books(self.c,self.p,self.plan)['diary']),2)

    def test_edit_version_preserves_old_snapshot_and_expires_review(self):
        first = self.save()
        self.s.transition_manual_journal(self.c,first['journal_id'],first['snapshot_hash'],'Revisão fictícia','revisado')
        second = self.save('tentativa-2',self.lines('110.30'),first['journal_id'],1)
        self.assertEqual((second['version'],second['status']),(2,'previa'))
        history = self.s.list_manual_journals(self.c,journal_id=first['journal_id'])
        self.assertEqual(history[1]['snapshot'],first['snapshot'])
        self.assertEqual(history[1]['status'],'substituido')
        self.assertIsNone(second['reviewed_at'])
        with self.assertRaisesRegex(ValueError,'Hash'):
            self.s.transition_manual_journal(self.c,first['journal_id'],first['snapshot_hash'],'Teste','fechado')
        with self.assertRaisesRegex(ValueError,'desatualizada'):
            self.save('tentativa-3',journal_id=first['journal_id'],version=1)
        self.close(second)
        with self.assertRaisesRegex(ValueError,'fechado'):
            self.save('tentativa-4',journal_id=first['journal_id'],version=2)

    def test_exact_decimal_split_and_large_values(self):
        lines = self.lines('0.30')
        lines[0]['amount']='0.10'
        lines.insert(1,{**lines[0],'amount':'0.20'})
        self.assertEqual(self.close(self.save(lines=lines))['snapshot']['totals']['debit'],'0.30')
        large = self.close(self.save('grande',self.lines('9999999999999999.99')))
        self.assertEqual(large['snapshot']['totals']['credit'],'9999999999999999.99')
        self.assertEqual(self.books()['totals']['debit'],'10000000000000000.29')

    def test_invalid_amount_date_side_group_account_rejected_atomically(self):
        changes = [('amount',0.1),('amount','NaN'),('amount','1e2'),('amount','0.00'),('amount','-1.00'),
                   ('amount','1.001'),('amount','100,30'),('date','2026-09-31'),('date','2026-08-15'),
                   ('side','X'),('group',''),('memo','\x00'),('account_id',True),('account_id',99999),('account_id',self.accounts['1'])]
        for key,value in changes:
            with self.subTest(key=key,value=value):
                lines = self.lines(); lines[0][key]=value
                with self.assertRaises(ValueError):self.save(lines=lines)
        # Equal totals across different days do not form a balanced daily event.
        lines=self.lines();lines[0]['date']='2026-09-16'
        with self.assertRaisesRegex(ValueError,'data e grupo'):self.save(lines=lines)
        self.assertEqual(self.s.list_manual_journals(self.c),[])
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM manual_journal_requests').fetchone()[0],0)

    def test_company_plan_period_and_identifier_scope(self):
        other_plan = self.s.import_plan(self.other,'Outro plano',fake_accounts())['id']
        other_account = self.s.list_accounts(self.other,other_plan)[0]['id']
        lines=self.lines();lines[0]['account_id']=other_account
        with self.assertRaisesRegex(ValueError,'Conta'):self.save(lines=lines)
        with self.assertRaises(ValueError):self.s.save_manual_journal(self.other,self.p,self.plan,self.lines(),'Ref','Motivo','K')
        revision=self.save()
        with self.assertRaises(ValueError):self.s.transition_manual_journal(self.other,revision['journal_id'],revision['snapshot_hash'],'Motivo','revisado')
        with self.assertRaises(ValueError):self.s.list_manual_journals(self.other,journal_id=revision['journal_id'])
        with self.assertRaises(ValueError):self.s.accounting_books(self.other,self.p,self.plan)
        for version in (-1,True,'0',None):
            with self.assertRaises(ValueError):self.save('invalido',version=version)

    def test_explicit_review_hash_and_integrity(self):
        first=self.save()
        with self.assertRaisesRegex(ValueError,'revisão'):self.s.transition_manual_journal(self.c,first['journal_id'],first['snapshot_hash'],'Motivo','fechado')
        with self.assertRaisesRegex(ValueError,'Hash'):self.s.transition_manual_journal(self.c,first['journal_id'],'x','Motivo','revisado')
        with self.assertRaises(ValueError):self.s.transition_manual_journal(self.c,first['journal_id'],first['snapshot_hash'],'','revisado')
        closed=self.close(first)
        with self.s.db:self.s.db.execute("UPDATE manual_journal_revisions SET snapshot_hash='x' WHERE id=?",(closed['id'],))
        with self.assertRaisesRegex(ValueError,'Hash'):self.books()

    def test_idempotent_request_never_reposts_old_version(self):
        first=self.save()
        self.assertEqual(self.save()['id'],first['id'])
        with self.assertRaisesRegex(ValueError,'outro conteúdo'):self.save(lines=self.lines('200.30'))
        second=self.save('editado',self.lines('120.30'),first['journal_id'],1)
        self.assertEqual(self.save()['id'],first['id'])
        self.assertEqual(self.s.list_manual_journals(self.c)[0]['id'],second['id'])
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM manual_journals').fetchone()[0],1)

    def test_transaction_rollback_preserves_review_after_failed_edit(self):
        first=self.save()
        with patch.object(self.s,'_audit',side_effect=RuntimeError('Falha sintética')):
            with self.assertRaises(RuntimeError):self.save('edicao-falha',self.lines('200.00'),first['journal_id'],1)
        self.assertEqual(self.s.list_manual_journals(self.c)[0],first)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM manual_journal_requests').fetchone()[0],1)

    def test_concurrent_creation_idempotency_and_optimistic_edit(self):
        barrier=threading.Barrier(2)
        lines=self.lines()
        def save(expected=None):
            with AccountingStore(self.path) as store:
                barrier.wait(timeout=10)
                try:
                    return store.save_manual_journal(self.c,self.p,self.plan,lines,'Ref','Teste',
                        'concorrente' if expected is None else threading.current_thread().name,
                        None if expected is None else expected['journal_id'],0 if expected is None else 1)['id']
                except ValueError:return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(save,[None,None]))
        self.assertEqual(len(set(results)),1)
        first=self.s.list_manual_journals(self.c)[0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(save,[first,first]))
        self.assertEqual(results.count(None),1)
        self.assertEqual(self.s.list_manual_journals(self.c)[0]['version'],2)

    def test_reversal_is_linked_exact_opposite_reviewed_and_once(self):
        first=self.close(self.save())
        with self.assertRaisesRegex(ValueError,'anteceder'):self.s.reverse_manual_journal(self.c,first['journal_id'],self.p,'2026-09-14','Motivo',first['snapshot_hash'])
        reversal=self.s.reverse_manual_journal(self.c,first['journal_id'],self.p,'2026-09-16','Motivo',first['snapshot_hash'])
        self.assertEqual(reversal['reversal_of'],first['journal_id'])
        self.assertEqual([line['side'] for line in reversal['snapshot']['entries']],['C','D'])
        self.assertEqual(len(self.books()['diary']),2)
        self.assertEqual(self.s.reverse_manual_journal(self.c,first['journal_id'],self.p,'2026-09-16','Motivo',first['snapshot_hash'])['id'],reversal['id'])
        with self.assertRaisesRegex(ValueError,'outros parâmetros'):self.s.reverse_manual_journal(self.c,first['journal_id'],self.p,'2026-09-17','Motivo',first['snapshot_hash'])
        with self.assertRaises(ValueError):self.save('editar-estorno',journal_id=reversal['journal_id'],version=1)
        self.close(reversal)
        self.assertEqual(len(self.books()['diary']),4)
        self.assertTrue(all(row['movement_balance']=='0.00' for row in self.books()['trial_balance_movements']))
        self.assertEqual(self.s._manual_revision(self.c,first['journal_id']),first)

    def test_reversal_next_period_preserves_original_book(self):
        first=self.close(self.save())
        old=self.books()
        period=self.s.create_period(self.c,'2026-09','2026-10')['id']
        reversal=self.s.reverse_manual_journal(self.c,first['journal_id'],period,'2026-10-01','Estorno fictício',first['snapshot_hash'])
        self.close(reversal)
        self.assertEqual(self.books(),old)
        next_book=self.s.accounting_books(self.c,period,self.plan)
        self.assertEqual(next_book['trial_balance_movements'][0]['movement_balance'],'-100.30')

    def test_book_snapshot_export_hashes_csv_injection_and_preservation(self):
        lines=self.lines();lines[0]['memo']='=1+1';lines[1]['memo']='@SUM(1;1)'
        first=self.close(self.save(lines=lines));books=self.books()
        self.assertFalse(books['opening_balances_included'])
        self.assertFalse(books['prosoft_validated']);self.assertFalse(books['pva_validated'])
        export=self.s.create_book_export(self.c,self.p,self.plan,books['book_hash'],'Exportação fictícia')
        contents={row['name']:self.s.read_book_artifact(self.c,export['id'],row['name'])['content'] for row in export['artifacts']}
        rows=list(csv.DictReader(io.StringIO(contents['diario.csv'].decode('utf-8-sig'))))
        self.assertEqual(rows[0]['memo'],"'=1+1")
        self.assertEqual(json.loads(contents['books.json'])['diary'][0]['memo'],'=1+1')
        self.close(self.save('novo'))
        for name,content in contents.items():self.assertEqual(self.s.read_book_artifact(self.c,export['id'],name)['content'],content)
        with self.assertRaisesRegex(ValueError,'alterados'):self.s.create_book_export(self.c,self.p,self.plan,books['book_hash'],'Teste')
        with self.assertRaises(ValueError):self.s.read_book_artifact(self.other,export['id'],'books.json')
        with self.assertRaises(ValueError):self.s.read_book_artifact(self.c,export['id'],'../books.json')
        self.assertEqual(first['snapshot_hash'],books['sources'][0]['snapshot_hash'])

    def test_export_replay_corruption_and_atomicity(self):
        with self.assertRaisesRegex(ValueError,'Nenhum'):self.s.create_book_export(self.c,self.p,self.plan,self.books()['book_hash'],'Teste')
        self.close(self.save());books=self.books()
        with patch.object(self.s,'_audit',side_effect=RuntimeError('Falha sintética')):
            with self.assertRaises(RuntimeError):self.s.create_book_export(self.c,self.p,self.plan,books['book_hash'],'Teste')
        self.assertEqual(self.s.list_book_exports(self.c),[])
        first=self.s.create_book_export(self.c,self.p,self.plan,books['book_hash'],'Teste')
        replay=self.s.create_book_export(self.c,self.p,self.plan,books['book_hash'],'Teste')
        self.assertEqual(first['id'],replay['id']);self.assertTrue(replay['duplicate'])
        with self.s.db:self.s.db.execute("UPDATE accounting_book_artifacts SET content=x'00' WHERE name='razao.csv'")
        with self.assertRaisesRegex(ValueError,'Hash'):self.s.read_book_artifact(self.c,first['id'],'books.json')
        with self.assertRaisesRegex(ValueError,'Hash'):self.s.create_book_export(self.c,self.p,self.plan,books['book_hash'],'Teste')

    def test_schema6_migration_is_additive_and_failure_rolls_back(self):
        first=self.save()
        with self.s.db:self.s.db.execute('UPDATE schema_version SET version=6')
        with patch('src.persistence.BOOKS_SCHEMA','THIS IS NOT SQL'):
            with self.assertRaises(sqlite3.Error):AccountingStore(self.path)
        self.assertEqual(self.s.db.execute('SELECT version FROM schema_version').fetchone()[0],6)
        with AccountingStore(self.path) as reopened:
            self.assertEqual(reopened.db.execute('SELECT version FROM schema_version').fetchone()[0],17)
            self.assertEqual(reopened.list_manual_journals(self.c)[0],first)


if __name__ == '__main__':unittest.main()
