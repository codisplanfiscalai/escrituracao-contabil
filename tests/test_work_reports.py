"""Synthetic accounting report filters, continuity, integrity and tenant scope."""
import json
from pathlib import Path
import tempfile
import unittest

from src.accounting_store import digest
from src.persistence import AccountingStore
from src.work_reports import accounting_report, report_from_request
from test_persistence import fake_accounts


class WorkReportsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "synthetic.sqlite3"
        self.s = AccountingStore(self.path, actor="operador-sintetico")
        self.addCleanup(lambda: self.s.close())
        self.company = self.s.create_company("Empresa sintética")['id']
        self.other = self.s.create_company("Outra sintética")['id']
        self.plan = self.s.import_plan(self.company, "Plano sintético", fake_accounts())['id']
        self.ids = {a['code']: a['id'] for a in self.s.list_accounts(self.company, self.plan)}
        self.cycle = self.s.save_work_cycle(self.company, "2026-08", "2026-09", self.plan, "Teste")
        self.serial = 0

    def movement(self, day="2026-09-15", amount="100.30", cycle=None, opening=False, post=True):
        cycle = cycle or self.cycle
        p = self.s.prepare_work_operation(self.company, cycle['id'], operation="abertura" if opening else "ajuste")
        p['reference'] = "Movimento inteiramente sintético"
        p['fiscal'].update(total=amount, posting_date=day)
        p['entries'] = [dict(account_id=self.ids[code], side=side, date=day,
                             amount=amount, group='principal', memo='Histórico sintético')
                        for side, code in [('D', '1.1.1'), ('C', '2.1')]]
        self.serial += 1
        o = self.s.save_work_operation(self.company, cycle['id'], p, "Teste", f"report-{self.serial}")
        if post:
            self.s.review_work_operation(self.company, o['operation_id'], o['snapshot_hash'], "Conferido")
            o = self.s.post_work_operation(self.company, o['operation_id'], o['snapshot_hash'], "Escriturado")
        return o

    def report(self, **kwargs):
        return accounting_report(self.s, self.company, self.cycle['id'], self.plan, **kwargs)

    def test_default_reports_share_canonical_book_and_hash(self):
        self.movement()
        before = self.s.db.total_changes
        for report in ('diario', 'razao', 'balancete'):
            r = self.report(report=report)
            self.assertEqual(r['entry_count'], 2)
            self.assertEqual(r['totals']['debit'], '100.30')
            self.assertEqual(r['totals']['credit'], '100.30')
            self.assertFalse(r['opening_declared'])
            self.assertEqual(r['book_snapshot_hash'], self.s.work_books(self.company, self.cycle['id'])['snapshot_hash'])
            self.assertEqual(r['snapshot_hash'], digest({k:v for k,v in r.items() if k != 'snapshot_hash'}))
            self.assertFalse(r['statutory_book'])
        self.assertEqual(self.s.db.total_changes, before)

    def test_subperiod_carries_prior_movements_and_excludes_future_days(self):
        self.movement('2026-09-02', '0.10')
        self.movement('2026-09-15', '0.20')
        self.movement('2026-09-25', '7.00')
        r = self.report(report='razao', start_date='2026-09-10', end_date='2026-09-20', account_code='1')
        self.assertEqual(r['totals']['opening'], '0.10')
        self.assertEqual(r['totals']['debit'], '0.20')
        self.assertEqual(r['totals']['closing'], '0.30')
        self.assertFalse(r['totals']['balanced_in_selection'])
        self.assertEqual(r['rows'][0]['balance'], '0.30')
        self.assertEqual(r['rows'][0]['balance_side'], 'D')
        credit = self.report(account_code='2.1', start_date='2026-09-10', end_date='2026-09-20')
        self.assertEqual(credit['rows'][0]['opening'], '-0.10')
        self.assertEqual(credit['rows'][0]['closing_side'], 'C')

    def test_declared_opening_and_prior_competence_are_preserved(self):
        self.movement('2026-09-01', '100.00', opening=True)
        self.movement('2026-09-15', '10.00')
        r = self.report()
        self.assertTrue(r['opening_declared'])
        self.assertEqual(r['accounts'][0]['opening'], '100.00')
        self.assertEqual(r['accounts'][0]['closing'], '110.00')
        october = self.s.save_work_cycle(self.company, '2026-09', '2026-10', self.plan, 'Teste')
        r = accounting_report(self.s, self.company, october['id'], self.plan)
        self.assertEqual(r['accounts'][0]['opening'], '110.00')
        self.assertEqual(r['entry_count'], 0)

    def test_rollup_uses_explicit_parent_not_code_prefix_and_does_not_double_totals(self):
        self.movement()
        r = self.report(level='sintetico')
        self.assertEqual([a['code'] for a in r['rows']], ['1', '1.1', '2'])
        self.assertEqual([a['debit'] for a in r['rows']], ['100.30', '100.30', '0.00'])
        self.assertEqual(r['totals']['debit'], '100.30')
        custom = [dict(code='ROOT', description='Sintética', kind='sintetica', nature='devedora'),
                  dict(code='ZZ', parent_code='ROOT', description='Analítica', kind='analitica', nature='devedora')]
        plan = self.s.import_plan(self.company, 'Sem prefixos', custom)['id']
        r = accounting_report(self.s, self.company, self.cycle['id'], plan, level='sintetico', include_zero=True)
        self.assertEqual(r['rows'][0]['code'], 'ROOT')
        self.assertEqual(r['rows'][0]['closing'], '0.00')
        empty = self.s.import_plan(self.company, 'Grupo vazio', custom[:1])['id']
        r = accounting_report(self.s, self.company, self.cycle['id'], empty, level='sintetico', include_zero=True)
        self.assertEqual([row['code'] for row in r['rows']], ['ROOT'])

    def test_empty_chart_rows_optional_and_plans_never_merge_by_code(self):
        self.movement()
        other_plan = self.s.import_plan(self.company, 'Outra versão', fake_accounts())['id']
        r = accounting_report(self.s, self.company, self.cycle['id'], other_plan)
        self.assertEqual(r['rows'], [])
        self.assertEqual(r['totals']['debit'], '0.00')
        r = accounting_report(self.s, self.company, self.cycle['id'], other_plan, include_zero=True)
        self.assertEqual(len(r['rows']), 2)

    def test_scope_invalid_filters_and_unsupported_cost_center_fail_closed(self):
        with self.assertRaises(ValueError):
            accounting_report(self.s, self.other, self.cycle['id'], self.plan)
        other_plan = self.s.import_plan(self.other, 'Isolado', fake_accounts())['id']
        with self.assertRaises(ValueError):
            accounting_report(self.s, self.company, self.cycle['id'], other_plan)
        for params in [dict(report='inventado'), dict(level='inventado'), dict(include_zero='false'),
                       dict(account_code='inexistente'), dict(start_date='20260901'),
                       dict(start_date='2026-09-31'), dict(start_date='2026-08-01'),
                       dict(start_date='2026-09-20', end_date='2026-09-10')]:
            with self.subTest(params=params), self.assertRaises(ValueError):
                self.report(**params)
        data = dict(company_id=self.company, cycle_id=self.cycle['id'], plan_id=self.plan)
        for extra in [dict(cost_center='1'), dict(include_zero='yes'), dict(grouping='consolidado')]:
            with self.assertRaises(ValueError):
                report_from_request(self.s, {**data, **extra})

    def test_drafts_do_not_enter_reports_and_same_day_lines_remain_distinct(self):
        self.movement(post=False)
        self.assertEqual(self.report()['entry_count'], 0)
        self.movement(amount='0.10')
        self.movement(amount='0.20')
        r = self.report(report='diario')
        self.assertEqual(r['entry_count'], 4)
        self.assertEqual(len({(row['operation_id'], row['sequence']) for row in r['rows']}), 4)
        self.assertEqual(r['totals']['debit'], '0.30')

    def test_corrupt_posted_movements_are_rejected(self):
        self.movement()
        row = self.s.db.execute('SELECT rowid,payload FROM work_movements LIMIT 1').fetchone()
        altered = json.loads(row['payload']); altered['amount'] = '0.01'
        with self.s.db:
            self.s.db.execute('UPDATE work_movements SET payload=? WHERE rowid=?', (json.dumps(altered), row['rowid']))
        with self.assertRaisesRegex(ValueError, 'Movimentos'):
            self.report()

    def test_reports_preserve_callers_transaction_on_success_and_error(self):
        self.s.db.execute('BEGIN')
        self.s.db.execute("UPDATE companies SET name='Alteração pendente' WHERE id=?", (self.company,))
        self.report()
        self.assertTrue(self.s.db.in_transaction)
        with self.assertRaises(ValueError):
            self.report(account_code='ausente')
        self.assertTrue(self.s.db.in_transaction)
        self.s.db.rollback()
        self.assertEqual(self.s._company(self.company)['name'], 'Empresa sintética')

    def test_restart_determinism_and_no_schema_migration(self):
        self.movement()
        r = self.report()
        version = self.s.db.execute('SELECT version FROM schema_version').fetchone()[0]
        self.s.close()
        self.s = AccountingStore(self.path, actor='outro-operador')
        self.assertEqual(self.report(), r)
        self.assertEqual(self.s.db.execute('SELECT version FROM schema_version').fetchone()[0], version)
