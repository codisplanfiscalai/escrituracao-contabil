"""Reviewed NF-e events control new posts without rewriting accounting history."""
from copy import deepcopy
from unittest.mock import patch
import unittest

import test_nfe_events as events
import test_work_application as work
import test_accounting_preparation_schema17 as preparation
from src.module_closure import CHECKS
from src.persistence import AccountingStore
from src.work_reports import accounting_report


class AccountingEventsSchema18Tests(unittest.TestCase):
    setUp = work.WorkApplicationTests.setUp
    save = work.WorkApplicationTests.save
    post = work.WorkApplicationTests.post
    opening = work.WorkApplicationTests.opening
    receive = events.EventWorkflowTests.receive
    review = events.EventWorkflowTests.review
    document = preparation.AccountingPreparationSchema17Tests.document
    config = preparation.AccountingPreparationSchema17Tests.config
    prepare = preparation.AccountingPreparationSchema17Tests.prepare
    rule = preparation.AccountingPreparationSchema17Tests.rule
    item_draft = preparation.AccountingPreparationSchema17Tests.item_draft
    item_rule = preparation.AccountingPreparationSchema17Tests.item_rule
    assess = preparation.AccountingPreparationSchema17Tests.assess

    def operation(self):
        doc = events.EventWorkflowTests.document(self)
        payload = self.s.prepare_work_operation(self.c, self.cycle['id'], doc, policy_id=self.policy['id'])
        return self.save(payload)

    def reports(self):
        return {kind:accounting_report(self.s, self.c, self.cycle['id'], self.plan, report=kind)
                for kind in ('diario','razao','balancete')}

    def close(self, module):
        state = self.s.module_period_overview(self.c, self.cycle['id'], module)
        return self.s.transition_module_period(self.c, self.cycle['id'], module, 'encerrada',
            state['snapshot_hash'], 'Conferência sintética', {key:True for key in CHECKS[module]},
            'Evidência sintética sem autorização legal')

    def test_pending_review_posting_proof_and_later_suspension_preserve_closed_reports(self):
        self.opening()
        op = self.operation()
        reviewed = self.s.review_work_operation(self.c, op['operation_id'], op['snapshot_hash'], 'Teste')
        before = self.reports()
        source = self.receive()
        with self.assertRaises(ValueError):
            self.s.post_work_operation(self.c, op['operation_id'], reviewed['snapshot_hash'], 'Teste')
        self.assertEqual(self.reports(), before)
        decision = self.review(source)
        self.assertEqual(self.s.get_work_operation(self.c, op['operation_id'])['payload'], op['payload'])
        self.assertEqual(self.reports(), before)
        self.s.post_work_operation(self.c, op['operation_id'], reviewed['snapshot_hash'], 'Escrituração explícita')
        proof = self.s.nfe_event_posting_proof(self.c, op['operation_id'])
        self.assertEqual(proof['snapshot']['reviews'][0]['snapshot_hash'], decision['snapshot_hash'])
        after = self.reports()
        for report in after.values():
            self.assertEqual(report['totals']['debit'], '100.30')
            self.assertEqual(report['totals']['credit'], '100.30')
            self.assertEqual(report['entry_count'], 2)
        titles = deepcopy(self.s.list_finance_titles(self.c))
        self.close('fiscal'); self.close('contabil')
        self.review(source, 'suspender', key='later')
        self.assertEqual(self.reports(), after)
        self.assertEqual(self.s.nfe_event_posting_proof(self.c, op['operation_id']), proof)
        self.assertEqual(self.s.list_finance_titles(self.c), titles)
        self.assertTrue(all(self.s.module_period_state(self.c, '2026-09', m)['state']=='encerrada'
                            for m in ('fiscal','contabil')))
        with self.assertRaises(ValueError):
            self.s.nfe_event_posting_proof(self.other, op['operation_id'])

    def test_correction_does_not_rewrite_posted_book_and_accounting_closure_is_independent(self):
        self.opening()
        op = self.post(self.operation())
        before = self.reports()
        input_id = self.s.source_inbox(self.c)[0]['input_id']
        original = self.s.source_original(self.c, input_id)['content']
        source = self.receive(events.event_xml(kind='110110', text='Descrição textual sintética, sem substituir campos'))
        fiscal = self.s.module_period_overview(self.c, self.cycle['id'], 'fiscal')
        self.assertTrue(any('eventos' in item for item in fiscal['blockers']))
        self.close('contabil')
        self.assertEqual(self.s.module_period_state(self.c, '2026-09', 'fiscal')['state'], 'aberta')
        self.review(source)
        self.assertEqual(self.reports(), before)
        self.assertEqual(self.s.get_work_operation(self.c, op['operation_id'])['payload'], op['payload'])
        self.assertIsNone(self.s.nfe_event_posting_proof(self.c, op['operation_id']))
        self.assertEqual(self.s.source_original(self.c, input_id)['content'], original)
        self.close('fiscal')

    def test_failed_proof_creation_rolls_back_book_titles_and_proof_together(self):
        op = self.operation()
        source = self.receive(); self.review(source)
        reviewed = self.s.review_work_operation(self.c, op['operation_id'], op['snapshot_hash'], 'Teste')
        before = self.reports()
        original = self.s._record_nfe_event_posting
        def fail(*args):
            original(*args)
            raise ValueError('Falha sintética após prova de eventos')
        with patch.object(self.s, '_record_nfe_event_posting', side_effect=fail):
            with self.assertRaisesRegex(ValueError, 'Falha sintética'):
                self.s.post_work_operation(self.c, op['operation_id'], reviewed['snapshot_hash'], 'Teste')
        self.assertEqual(self.reports(), before)
        self.assertIsNone(self.s.nfe_event_posting_proof(self.c, op['operation_id']))
        self.assertEqual(self.s.list_finance_titles(self.c), [])
        self.s.post_work_operation(self.c, op['operation_id'], reviewed['snapshot_hash'], 'Nova tentativa explícita')
        self.assertEqual(self.reports()['diario']['entry_count'], 2)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM nfe_event_posting_proofs').fetchone()[0], 1)

    def test_schema17_to18_preserves_preparation_v4_books_and_locks_without_reinterpretation(self):
        self.opening()
        row, *_ = self.item_draft()
        self.item_rule()
        preview = self.s.preview_operation_tax(self.c, row['operation_id'])
        calculated = self.s.apply_operation_tax(self.c, row['operation_id'], preview['snapshot_hash'],
            'before-events-schema', 'Teste')['operation']
        self.post(calculated); self.assess(); self.close('fiscal'); self.close('contabil')
        before = self.reports()
        tables = ('files','source_revisions','work_movements','tax_calculations',
            'document_preparation_batches','tax_assessment_versions','module_period_versions')
        preserved = {t:[tuple(r) for r in self.s.db.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in tables}
        with self.s.db:
            for table in ('nfe_event_posting_proofs','nfe_event_reviews','nfe_event_observations'):
                self.s.db.execute('DROP TABLE '+table)
            self.s.db.execute('UPDATE schema_version SET version=17')
        self.s.close()
        self.s = AccountingStore(self.path, actor='operador-sintetico')
        self.addCleanup(self.s.close)
        self.assertEqual(self.s.db.execute('SELECT version FROM schema_version').fetchone()[0], 18)
        self.assertEqual(self.reports(), before)
        for table, rows in preserved.items():
            self.assertEqual([tuple(r) for r in self.s.db.execute('SELECT * FROM '+table+' ORDER BY rowid')], rows)
        self.assertEqual(self.s.nfe_event_queue(self.c)['total'], 0)
        self.assertIsNone(self.s.nfe_event_posting_proof(self.c, row['operation_id']))
        self.assertEqual(self.s.db.execute('PRAGMA foreign_key_check').fetchall(), [])
