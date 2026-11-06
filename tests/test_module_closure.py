"""Independent module locks with synthetic documents and accounting fixtures."""
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import test_work_application as fixtures
from src.module_closure import CHECKS
from src.persistence import AccountingStore
from test_persistence import fake_xml


class ModulePeriodTests(unittest.TestCase):
    setUp = fixtures.WorkApplicationTests.setUp
    save = fixtures.WorkApplicationTests.save
    post = fixtures.WorkApplicationTests.post
    document = fixtures.WorkApplicationTests.document
    opening = fixtures.WorkApplicationTests.opening

    def change(self, module, target='encerrada', cycle=None, **overrides):
        cycle = cycle or self.cycle
        preview = self.s.module_period_overview(self.c, cycle['id'], module)
        args = dict(company_id=self.c, cycle_id=cycle['id'], module=module, target=target,
                    expected_hash=preview['snapshot_hash'], reason='Conferência sintética',
                    checks={key: True for key in CHECKS[module]}, evidence_reference='Referência sintética conferida externamente')
        args.update(overrides)
        return self.s.transition_module_period(**args)

    def test_fiscal_accounting_company_and_month_are_independent(self):
        self.change('fiscal')
        self.assertEqual(self.s.module_period_state(self.c, '2026-09', 'fiscal')['state'], 'encerrada')
        self.assertEqual(self.s.module_period_state(self.c, '2026-09', 'contabil')['state'], 'aberta')
        self.assertEqual(self.s.module_period_state(self.other, '2026-09', 'fiscal')['state'], 'aberta')
        self.opening()  # Pure accounting opening remains possible with fiscal closed.
        self.change('contabil')
        self.change('fiscal', target='aberta')
        self.assertEqual(self.s.module_period_state(self.c, '2026-09', 'contabil')['state'], 'encerrada')
        october = self.s.save_work_cycle(self.c, '2026-08', '2026-10', self.plan, 'Outro mês')
        self.assertEqual(self.s.module_period_overview(self.c, october['id'], 'contabil')['state']['state'], 'aberta')
        with AccountingStore(self.path) as reopened:
            self.assertEqual(reopened.module_period_state(self.c, '2026-09', 'contabil')['state'], 'encerrada')

    def test_receipt_remains_available_but_organization_and_new_fiscal_writes_are_blocked(self):
        self.change('fiscal')
        receipt = self.s.receive_sources(self.c, [{'filename':'Nova.xml', 'content':fake_xml()}], 'after-close')
        source = receipt['items'][0]
        self.assertTrue(self.s.source_original(self.c, source['input_id'])['content'])
        with self.assertRaisesRegex(ValueError, 'fiscal encerrado'):
            self.s.organize_source(self.c, source['input_id'], self.cycle['id'], source['snapshot_hash'], 'Tentativa')
        payload = self.s.prepare_work_operation(self.c, self.cycle['id'], operation='entrada')
        with self.assertRaisesRegex(ValueError, 'fiscal encerrado'):
            self.save(payload)
        self.assertEqual(self.s.list_documents(self.c), [])
        self.assertEqual(self.s.work_operations(self.c, self.cycle['id']), [])

    def test_accounting_lock_blocks_mixed_operation_and_parameters_without_closing_fiscal(self):
        self.opening()
        self.change('contabil')
        payload = self.document()
        with self.assertRaisesRegex(ValueError, 'contabil encerrado'):
            self.save(payload)
        with self.assertRaisesRegex(ValueError, 'contabil encerrado'):
            self.s.save_work_cycle(self.c, '2026-08', '2026-09', self.plan, 'Parâmetros', self.cycle['version'])
        self.assertEqual(self.s.module_period_state(self.c, '2026-09', 'fiscal')['state'], 'aberta')

    def test_pending_operations_stale_preview_and_manual_checks_are_required(self):
        with self.assertRaisesRegex(ValueError, 'Confirme'):
            self.change('fiscal', checks={})
        with self.assertRaisesRegex(ValueError, 'referência'):
            self.change('fiscal', evidence_reference='')
        before = self.s.module_period_overview(self.c, self.cycle['id'], 'fiscal')
        payload = self.document()
        with self.assertRaisesRegex(ValueError, 'alterada'):
            self.change('fiscal', expected_hash=before['snapshot_hash'])
        row = self.save(payload)
        with self.assertRaisesRegex(ValueError, 'pendentes'):
            self.change('fiscal')
        self.post(row)
        self.change('fiscal')
        # Idempotent POST reads the prior result; it creates no extra movement.
        posted = self.s.get_work_operation(self.c, row['operation_id'])
        count = self.s.db.execute('SELECT COUNT(*) FROM work_movements').fetchone()[0]
        self.s.post_work_operation(self.c, row['operation_id'], posted['snapshot_hash'], 'Repetição')
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_movements').fetchone()[0], count)

    def test_draft_tabs_cannot_be_a_backdoor_and_module_history_is_audited(self):
        self.change('fiscal')
        payload = self.s.prepare_work_operation(self.c, self.cycle['id'], operation='entrada')
        with self.assertRaisesRegex(ValueError, 'fiscal encerrado'):
            self.s.save_work_tab(self.c, self.cycle['id'], 'Tentativa', {'payload':payload})
        self.change('fiscal', target='aberta')
        rows = self.s.db.execute('SELECT version,state FROM module_period_versions WHERE company_id=? AND module=? ORDER BY version', (self.c, 'fiscal')).fetchall()
        self.assertEqual([tuple(r) for r in rows], [(1,'encerrada'),(2,'aberta')])
        self.assertEqual(sum(r['action'].startswith('modulo_') for r in self.s.list_audit(self.c)), 2)

    def test_schema_11_upgrade_preserves_client_identity_and_profile(self):
        self.s.save_client_profile(self.c, {'basic':{'trade_name':'Sintético'}}, 0, 'Teste')
        self.s.db.execute('DROP TABLE module_period_versions')
        self.s.db.execute('UPDATE schema_version SET version=11')
        self.s.db.commit()
        with AccountingStore(self.path) as reopened:
            self.assertEqual(reopened.db.execute('SELECT version FROM schema_version').fetchone()[0], 15)
            self.assertEqual(reopened.client_profile(self.c)['data']['basic']['trade_name'], 'Sintético')
            self.assertEqual(reopened.module_period_state(self.c, '2026-09', 'fiscal')['state'], 'aberta')

    def test_concurrent_close_and_new_operation_cannot_both_commit(self):
        preview = self.s.module_period_overview(self.c, self.cycle['id'], 'fiscal')
        payload = self.s.prepare_work_operation(self.c, self.cycle['id'], operation='entrada')
        barrier = Barrier(2)
        def attempt(close):
            with AccountingStore(self.path) as store:
                barrier.wait(timeout=5)
                try:
                    if close:
                        store.transition_module_period(self.c, self.cycle['id'], 'fiscal', 'encerrada', preview['snapshot_hash'], 'Fechamento concorrente', {k:True for k in CHECKS['fiscal']}, 'Referência sintética')
                    else:
                        store.save_work_operation(self.c, self.cycle['id'], payload, 'Lançamento concorrente', 'concurrent-1')
                    return 'ok'
                except ValueError:
                    return 'blocked'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, [True, False]))
        self.assertEqual(sorted(results), ['blocked', 'ok'])

    def test_legacy_global_reopening_does_not_remove_independent_lock(self):
        self.opening()
        self.change('fiscal')
        overview = self.s.work_overview(self.c, self.cycle['id'])
        self.s.transition_work_cycle(self.c, self.cycle['id'], 'encerrada', overview['snapshot_hash'], 'Fechamento global sintético')
        overview = self.s.work_overview(self.c, self.cycle['id'])
        self.s.transition_work_cycle(self.c, self.cycle['id'], 'aberta', overview['snapshot_hash'], 'Reabertura global sintética')
        self.assertEqual(self.s.module_period_state(self.c, '2026-09', 'fiscal')['state'], 'encerrada')


if __name__ == '__main__':
    unittest.main()
