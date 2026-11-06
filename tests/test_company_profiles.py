"""Synthetic registration and search: no reference binaries or real company data."""
import tempfile
import unittest
from pathlib import Path

from src.persistence import AccountingStore
from src.company_profiles import empty_profile
from test_persistence import BUYER, ISSUER, fake_xml


class CompanyProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'synthetic.sqlite3'
        self.store = AccountingStore(self.path, actor='synthetic-operator')
        self.addCleanup(lambda: self.store.close())
        self.company = self.store.create_company('Cliente sintético', cnpj=BUYER)['id']
        self.other = self.store.create_company('Outro cliente sintético')['id']

    def test_registration_versions_are_separate_and_survive_restart(self):
        data = empty_profile()
        data['basic'].update(trade_name='Fantasia sintética', state='SP', postal_code='00000000', start_date='2026-01-01')
        data['fiscal']['tax_regime'] = 'Declaração sintética sem cálculo'
        data['labor'].update(fap='1,0000', rat='2')
        result = self.store.save_client_profile(self.company, data, 0, 'Cadastro sintético')
        org = self.store.save_user_organization({'name': 'Escritório sintético', 'cnpj': ISSUER, 'profile': empty_profile()}, 0, 'Registro próprio')
        self.assertEqual(result['version'], 1)
        self.assertEqual(org['version'], 1)
        self.assertEqual(self.store.client_profile(self.other)['version'], 0)
        self.assertEqual(len(self.store.list_companies()), 2)
        self.assertEqual(self.store.work_cycles(self.company), [])
        with AccountingStore(self.path) as reopened:
            self.assertEqual(reopened.client_profile(self.company)['data'], data)
            self.assertEqual(reopened.user_organization()['data']['name'], 'Escritório sintético')
            self.assertEqual(reopened.client_profile_history(self.company)[0]['actor'], 'synthetic-operator')
            self.assertEqual(len(reopened.user_organization_history()), 1)

    def test_stale_registration_and_invalid_fields_do_not_change_history(self):
        self.store.save_client_profile(self.company, {}, 0, 'Primeiro')
        with AccountingStore(self.path) as concurrent:
            with self.assertRaisesRegex(ValueError, 'alterado'):
                concurrent.save_client_profile(self.company, {}, 0, 'Desatualizado')
        for invalid in ({'unknown': {}}, {'basic': {'unknown': 'x'}}, {'basic': {'state': 'abc'}}, {'labor': {'fap': 1.2}}, {'basic': {'start_date': '2026-02-30'}}):
            with self.assertRaises(ValueError):
                self.store.save_client_profile(self.company, invalid, 1, 'Inválido')
        for version in (True, '1', -1, 1.0):
            with self.assertRaises(ValueError):
                self.store.save_client_profile(self.company, {}, version, 'Versão inválida')
        self.assertEqual(len(self.store.client_profile_history(self.company)), 1)
        self.assertEqual(self.store.client_profile_history(self.other), [])

    def test_organization_conflict_and_tampered_history(self):
        data = {'name': 'Escritório sintético', 'cnpj': '', 'profile': {}}
        self.store.save_user_organization(data, 0, 'Primeiro')
        with self.assertRaises(ValueError):
            self.store.save_user_organization(data, 0, 'Conflito')
        self.store.db.execute("UPDATE user_organization_versions SET data='{}'")
        self.store.db.commit()
        with self.assertRaisesRegex(ValueError, 'alterado'):
            self.store.user_organization()

    def test_search_before_any_cycle_and_other_client_isolation(self):
        self.store.receive_sources(self.company, [{'filename': 'Compra-Sintetica.xml', 'content': fake_xml()}], 'receipt-1')
        self.store.receive_sources(self.other, [{'filename': 'Outro.xml', 'content': fake_xml(number=2)}], 'receipt-2')
        self.assertEqual(self.store.work_cycles(self.company), [])
        result = self.store.search_sources(self.company, query='compra', direction='entrada', issued_from='2026-09-01', issued_to='2026-09-30')
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['items'][0]['filename'], 'Compra-Sintetica.xml')
        self.assertEqual(self.store.search_sources(self.company, direction='saida')['total'], 0)
        self.assertEqual(self.store.search_sources(self.company, query='Outro')['total'], 0)
        self.assertEqual(self.store.search_sources(self.company, issued_from='2026-10-01')['total'], 0)
        self.assertEqual(self.store.search_sources(self.company, query=ISSUER)['total'], 1)
        for filters in ({'issued_from':'2026-09-30', 'issued_to':'2026-09-01'}, {'issued_from':'invalid'}, {'direction':'ambos'}, {'kind':'PDF'}):
            with self.assertRaises(ValueError):
                self.store.search_sources(self.company, **filters)
        self.assertEqual(self.store.work_cycles(self.company), [])

    def test_additive_migration_from_10_preserves_sources_and_companies(self):
        self.store.receive_sources(self.company, [{'filename':'Original.xml', 'content':fake_xml()}], 'before-migration')
        source = self.store.source_inbox(self.company)[0]
        original = self.store.source_original(self.company, source['input_id'])
        companies = self.store.list_companies()
        self.store.db.execute('DROP TABLE client_profile_versions')
        self.store.db.execute('DROP TABLE user_organization_versions')
        self.store.db.execute('UPDATE schema_version SET version=10')
        self.store.db.commit()
        with AccountingStore(self.path) as reopened:
            self.assertEqual(reopened.db.execute('SELECT version FROM schema_version').fetchone()[0], 16)
            self.assertEqual(reopened.list_companies(), companies)
            self.assertEqual(reopened.source_original(self.company, source['input_id']), original)
            self.assertEqual(reopened.user_organization()['version'], 0)
            self.assertEqual(reopened.client_profile(self.company)['version'], 0)


if __name__ == '__main__':
    unittest.main()
